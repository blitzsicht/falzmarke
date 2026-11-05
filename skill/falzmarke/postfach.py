"""Das Postfach des Absenders — gelesen über den lokalen IMAP-Proxy (ADR 0051).

Zwei Dinge braucht `email --oeffnen` aus dem Postfach, und nur diese:

* **lesen**, was in den letzten Stunden gesendet wurde und welche Entwürfe
  liegen — mit `EXAMINE` (nur lesend) und `BODY.PEEK` (setzt kein `\\Seen`);
* **einen Entwurf ablegen** — `APPEND` mit `\\Draft \\Seen` in den
  Entwürfe-Ordner. Das ist der einzige schreibende Befehl in diesem Modul.

Es gibt hier kein `STORE`, `EXPUNGE`, `COPY`, `MOVE` oder `DELETE`, und keinen
Versandweg: IMAP kann nicht senden, und `smtplib` ist nicht importiert.
`tests/test_postfach.py` liest das am Syntaxbaum nach. Nachrichten bewegen
`falzmarke.ablage` (Eingang → Ablage, ADR 0061) und `falzmarke.entwurfsablage`
(überholte Entwürfe → Papierkorb, ADR 0062): zwei eigene Module, je ein `UID
MOVE`, damit die Zusage hier wahr bleibt.

**Der Weg:** unverschlüsselt an einen Proxy auf dem eigenen Rechner (Vorgabe
`127.0.0.1:1993`, `FALZMARKE_GESENDET_IMAP`), Benutzer ist die Absenderadresse,
das Kennwort ist ein Platzhalter — der Proxy tauscht die Anmeldung gegen OAuth
und spricht TLS mit dem Server. So läuft es beim Betreiber mit `emailproxy`
für die Microsoft-Konten. Ein Konto, das der Proxy nicht kennt (Gmail), lehnt
er ab, ohne den Server zu fragen; dann heißt es „nicht geprüft“, mit seiner
Meldung als Grund.

Kein `subprocess`: Die Regel „genau ein Modul startet fremde Programme“
(ADR 0038, Punkt 5) bleibt unberührt — eine Socket-Verbindung startet nichts.
"""

from __future__ import annotations

import base64
import email
import imaplib
import re
import time
from collections.abc import Mapping
from datetime import date, datetime, timezone
from email import policy
from email.utils import getaddresses, parsedate_to_datetime
from typing import NamedTuple
from urllib.parse import unquote, urlsplit

#: Die Klasse, die verbindet. Eine Modulkonstante, damit die Tests sie durch
#: die Attrappe ersetzen können — und `conftest.py` sie für alle anderen
#: Tests durch eine, die jede Verbindung ablehnt.
IMAP_KLASSE = imaplib.IMAP4

ZIEL_VORGABE = "127.0.0.1:1993"

#: Zeitlimit der Gesendet-Prüfung, für die ganze Sitzung — nicht je Befehl.
#: Ein hängender Proxy darf `--oeffnen` nicht länger aufhalten als das. Bis
#: #441 waren es 5 s. Anmeldung und LIST am Proxy dauerten am 30.10.2026
#: einmal 20,6 s, einmal 18,1 s und einmal 3,6 s, und die Prüfung endete oft
#: in „GESENDET NICHT GEPRÜFT“, obwohl der Proxy gesund war.
FRIST_S = 30

#: Der Proxy nimmt jedes Kennwort; sein Kennwort ist das OAuth-Token. Derselbe
#: Platzhalter wie im Mailarchiv des Betreibers (`zaehler.imap_zaehlung`).
KENNWORT = "dummy"

#: Höchstens so viele Nachrichten werden je Ordner angesehen, die neuesten.
#: Ein Entwürfe-Ordner mit Jahren an Resten soll die Prüfung nicht ausbremsen.
GRENZE = 500

#: So viele Teiltreffer holt `suche_kennung` höchstens nach. Eine Message-ID in
#: spitzen Klammern trifft eine Nachricht; eine ohne (die `kennungen` roh
#: durchreicht) ist eine Teilkette und kann in einem alten Eingang tausendfach
#: treffen. Ohne Grenze holte der kopflose `aufraeumen`-Lauf dann jeden dieser
#: Köpfe (Nachreview von #479). Die Kappung steht in `suchkappungen`, nicht in
#: `gekappt`: Gekappt ist dann die Trefferliste, nicht der Ordner (Nachreview
#: von #492, Befund 1).
SUCHGRENZE = 4 * GRENZE

#: Die Kopfzeilen, die je Nachricht gelesen werden — nie der ganze Inhalt,
#: bevor feststeht, dass der Empfänger passt.
KOPFZEILEN = ("DATE", "FROM", "TO", "CC", "BCC", "SUBJECT", "IN-REPLY-TO", "X-FALZMARKE-FASSUNG",
              "MESSAGE-ID")


class PostfachFehler(Exception):
    """Ein Grund in einem Satz — er wandert unverändert in die Ausgabe."""


# ── Ordnernamen ─────────────────────────────────────────────────────────────

_UTF7 = re.compile(r"&([A-Za-z0-9+,]*)-")


def utf7_dekodieren(name: str) -> str:
    """Modified UTF-7 (RFC 3501, 5.1.3) in Klartext: `Entw&APw-rfe` → `Entwürfe`."""
    def ersetze(treffer: re.Match[str]) -> str:
        teil = treffer.group(1)
        if not teil:
            return "&"
        teil = teil.replace(",", "/")
        teil += "=" * (-len(teil) % 4)
        return base64.b64decode(teil).decode("utf-16-be")

    return _UTF7.sub(ersetze, name)


def utf7_kodieren(name: str) -> str:
    """Klartext in modified UTF-7: `Entwürfe` → `Entw&APw-rfe`, `&` → `&-`.

    Druckbares ASCII bleibt stehen; jede Folge anderer Zeichen wird als
    UTF-16 in base64 ohne Auffüllung geschrieben, mit `,` statt `/`.
    """
    aus: list[str] = []
    fremd: list[str] = []

    def schliesse() -> None:
        if fremd:
            kodiert = base64.b64encode("".join(fremd).encode("utf-16-be")).decode("ascii")
            aus.append("&" + kodiert.rstrip("=").replace("/", ",") + "-")
            fremd.clear()

    for zeichen in name:
        if 0x20 <= ord(zeichen) <= 0x7E:
            schliesse()
            aus.append("&-" if zeichen == "&" else zeichen)
        else:
            fremd.append(zeichen)
    schliesse()
    return "".join(aus)


def ordner_aus_url(url: str) -> tuple[str, str] | None:
    """Konto und IMAP-Ordnername aus einer Ordneradresse in Thunderbirds `prefs.js`.

    `imap://joe%40example.org@outlook.office365.com/Entw&APw-rfe` ergibt
    `("joe@example.org", "Entw&APw-rfe")`. Thunderbird schreibt den
    Namen meist schon kodiert, für Gmail aber im Klartext
    (`[Google Mail]/Entwürfe`, gemessen am 21.10.2026) — ein Name mit
    Nicht-ASCII wird deshalb kodiert, einer ohne bleibt, wie er ist.
    """
    teile = urlsplit(url or "")
    if teile.scheme != "imap" or not teile.path.strip("/"):
        return None
    name = unquote(teile.path.lstrip("/"))
    if any(ord(z) > 0x7E for z in name):
        name = utf7_kodieren(name)
    return unquote(teile.username or ""), name


#: Zeichen, die in einem IMAP-Argument nichts zu suchen haben. Derselbe Satz
#: wie `imaplib._control_chars` — hier aber selbst geprüft, weil es diese
#: Prüfung in `imaplib.IMAP4._command` erst ab Python 3.14 gibt.
_STEUERZEICHEN = re.compile(r"[\x00\r\n]")

#: Eine Message-ID in spitzen Klammern. `[^<>\s]` statt `.`, damit zwei
#: Kennungen in einer Zeile nicht zu einer verschmelzen.
_KENNUNG = re.compile(r"<[^<>\s]+>")


def _zitiert(name: str) -> str:
    """Ein Ordnername oder Suchwert als IMAP-Zeichenkette — in Anführungszeichen.

    `Gesendete Elemente` hat ein Leerzeichen; unzitiert wären es zwei Argumente.

    Ein Umbruch oder Nullbyte wird **abgelehnt**, nicht entschärft: In IMAP
    trennt `\r\n` zwei Befehle. Ein Wert, der von außen kommt — die
    `Message-ID` fremder Post, über `In-Reply-To` einer Antwort — stünde dann
    als eigener Befehl in einer Sitzung, die verschieben darf. `imaplib` fängt
    das erst ab Python 3.14 ab; auf 3.12.9 und 3.13.12 gehen zwei Zeilen auf
    die Leitung (gemessen am 29.10.2026 mit abgefangenem `send`, #438), und die
    CI fährt 3.12.

    Gerufen wird es für die frei belegten Argumente von `LOGIN`, `SELECT`,
    `UID SEARCH HEADER`, `APPEND` und `UID MOVE`. Nicht hindurch gehen `FETCH`
    und `LIST`: Dort stehen nur UIDs und feste Wörter.
    """
    if _STEUERZEICHEN.search(name or ""):
        raise PostfachFehler(
            "ein Umbruch oder Nullbyte in einem IMAP-Argument wird nicht gesendet — "
            "er würde dort einen zweiten Befehl beginnen")
    return '"' + name.replace("\\", "\\\\").replace('"', '\\"') + '"'


def sendbar(kennung: str) -> bool:
    """Lässt sich dieser Wert als IMAP-Suchbegriff senden?

    Eine Kennung kommt aus einer Mail, also von außen. `_zitiert` lehnt
    Umbruch und Nullbyte ab, `imaplib` kodiert Argumente mit ASCII: Beides
    beendet die Sitzung, und mit ihr den Lauf für das ganze Konto (#442). Der
    Aufrufer überspringt deshalb, was hier durchfällt, und nennt es im Bericht.
    """
    return kennung.isascii() and not _STEUERZEICHEN.search(kennung)


def kennungen(wert: str) -> tuple[str, ...]:
    """Die Message-IDs eines rohen Feldwerts, einzeln und ohne Doppelte.

    `In-Reply-To` und `References` tragen nach RFC 5322 eine **Liste**, und ein
    langer Wert liegt über mehrere Zeilen gefaltet in der Nachricht. Beides
    heißt: Der Feldwert, wie `kopf_aus` ihn liefert, ist kein Suchbegriff — es
    ist einer je Kennung (#438).

    Ohne spitze Klammern bleibt der zu einer Zeile zusammengezogene Wert die
    einzige Kennung. Ein Programm, das sie ohne Klammern schreibt, soll nicht
    stillschweigend aus der Zuordnung fallen.
    """
    roh = str(wert or "")
    gefunden = tuple(dict.fromkeys(_KENNUNG.findall(roh)))
    if gefunden:
        return gefunden
    eine = " ".join(roh.split())
    return (eine,) if eine else ()


def gleiche_kennung(gesucht: str, kopfwert: str) -> bool:
    """Trägt die Kopfzeile genau diese Kennung, nicht nur einen Teil von ihr?

    `SEARCH HEADER` ist nach RFC 3501 eine Teilkettensuche: Ohne spitze Klammern
    trifft `123` jede Message-ID, die `123` enthält, und die Treffer gehen mit
    `--machen` in `UID MOVE` (#442). Die Klammern zählen nicht mit, damit ein
    Programm, das sie weglässt, seine eigene Nachricht weiter findet. Groß und
    klein zählen: Im Zweifel bleibt die Mail im Eingang liegen.

    Abgenommen wird genau **ein** Paar, und nur ein vollständiges. `strip("<>")`
    nahm jede Klammer an jedem Ende, auch einzeln und doppelt: `abc@x>` oder
    `<<abc@x>>` galten als `<abc@x>`, und das in der Richtung, in der zu viel
    verschoben wird (Review von #457).
    """
    return any(_ohne_klammerpaar(k) == _ohne_klammerpaar(gesucht) for k in kennungen(kopfwert))


def _ohne_klammerpaar(kennung: str) -> str:
    """`<abc@x>` → `abc@x`; alles andere bleibt, wie es ist."""
    if len(kennung) >= 2 and kennung.startswith("<") and kennung.endswith(">"):
        return kennung[1:-1]
    return kennung


# ── Ziel ────────────────────────────────────────────────────────────────────

def ziel(umgebung: Mapping[str, str]) -> tuple[str, int]:
    """Host und Port aus `FALZMARKE_GESENDET_IMAP`, Vorgabe `127.0.0.1:1993`."""
    wert = (umgebung.get("FALZMARKE_GESENDET_IMAP") or ZIEL_VORGABE).strip()
    host, _, port = wert.rpartition(":")
    if not host or not port.isdigit():
        raise PostfachFehler(f"FALZMARKE_GESENDET_IMAP={wert} ist kein host:port")
    return host, int(port)


# ── Kopfzeilen ──────────────────────────────────────────────────────────────

class Empfaenger(NamedTuple):
    """An, Cc und Bcc einer Nachricht, je für sich, als reine Adressen, klein.

    Der Maßstab für das Verfassen-Fenster (#464), in derselben Form wie bei
    `eml.entwurfsfelder`: `_asdict()` ist, was `oeffnen.empfaenger_pruefen` liest.
    """

    an: tuple[str, ...]
    kopie: tuple[str, ...]
    blindkopie: tuple[str, ...]


class Kopf(NamedTuple):
    """Was aus den Kopfzeilen einer Nachricht gebraucht wird."""

    uid: str
    #: Aus `Date`, sonst die Ankunft im Ordner (INTERNALDATE). Zeitzonenbewusst.
    datum: datetime | None
    #: To, Cc und Bcc als reine Adressen, klein geschrieben, in dieser Reihenfolge.
    an: tuple[str, ...]
    betreff: str
    fassung: str
    antwort_auf: str
    #: Die `Message-ID` der Nachricht, roh.
    kennung: str = ""
    #: To, Cc und Bcc getrennt (#481); `an` ist ihre Vereinigung ohne Doppelte.
    #: `None` heißt: nicht aus Kopfzeilen gelesen, sondern von Hand gebaut. Das
    #: ist etwas anderes als ein Entwurf ohne Empfänger.
    empfaenger: Empfaenger | None = None
    #: Die Adresse aus `From`, klein, ohne Anzeigenamen; leer, wenn keine dasteht.
    #: Der Maßstab für den Absender im Verfassen-Fenster (#482).
    von: str = ""
    #: Die Ankunft im Ordner (INTERNALDATE), für sich. `datum` nimmt sie nur,
    #: wenn `Date` fehlt; das Jahr in `email.ablage: Archiv/{jahr}` richtet sich
    #: nach ihr allein (#478).
    ankunft: datetime | None = None
    #: Die Flags der Nachricht, klein geschrieben (`\\seen`, `\\flagged` …).
    #: `None` heißt: Der Server hat keine genannt, nicht „keine gesetzt“ (#478).
    fahnen: tuple[str, ...] | None = None
    #: Jede Adresse aus `From`, klein, in der Reihenfolge der Kopfzeile. `von`
    #: ist nur die erste; ob eine Mail von außerhalb kommt, hängt an allen
    #: (`gesendet.fremder_absender`, wie `fremderAbsender` in der Brücke, #506).
    absender: tuple[str, ...] = ()


def _adressen(nachricht, *felder: str) -> tuple[str, ...]:
    werte = [str(w) for feld in felder for w in nachricht.get_all(feld, [])]
    gesehen: list[str] = []
    for _, adresse in getaddresses(werte):
        adresse = adresse.strip().lower()
        if adresse and adresse not in gesehen:
            gesehen.append(adresse)
    return tuple(gesehen)


def kopf_aus(roh: bytes, uid: str, ankunft: datetime | None,
             fahnen: tuple[str, ...] | None = None) -> Kopf:
    """Ein `Kopf` aus den Bytes der Kopfzeilen (oder der ganzen Nachricht)."""
    nachricht = email.message_from_bytes(roh, policy=policy.compat32)
    datum = None
    if nachricht.get("Date"):
        try:
            datum = parsedate_to_datetime(str(nachricht["Date"]))
        except (TypeError, ValueError, IndexError):
            datum = None
        if datum is not None and datum.tzinfo is None:
            datum = datum.replace(tzinfo=timezone.utc)
    betreff = _dekodiert(nachricht.get("Subject"))
    empfaenger = Empfaenger(*(_adressen(nachricht, feld) for feld in ("To", "Cc", "Bcc")))
    absender = _adressen(nachricht, "From")
    return Kopf(uid=uid, datum=datum or ankunft,
                an=tuple(dict.fromkeys(empfaenger.an + empfaenger.kopie + empfaenger.blindkopie)),
                betreff=betreff, fassung=str(nachricht.get("X-Falzmarke-Fassung") or "").strip(),
                antwort_auf=str(nachricht.get("In-Reply-To") or "").strip(),
                kennung=str(nachricht.get("Message-ID") or "").strip(),
                empfaenger=empfaenger,
                von=next(iter(absender), ""),
                ankunft=ankunft, fahnen=fahnen, absender=absender)


def _dekodiert(wert) -> str:
    """Eine Kopfzeile mit `=?utf-8?…?=` als Klartext."""
    if wert is None:
        return ""
    from email.header import decode_header, make_header

    try:
        return str(make_header(decode_header(str(wert)))).strip()
    except (UnicodeError, LookupError, ValueError):
        return str(wert).strip()


_UID = re.compile(rb"\bUID (\d+)")
_ANKUNFT = re.compile(rb'INTERNALDATE "([^"]+)"')
_FAHNEN = re.compile(rb"\bFLAGS \(([^)]*)\)")


def _fahnen(*teile: bytes) -> tuple[str, ...] | None:
    """Die Flags aus der FETCH-Antwort, klein; `None`, wenn keine Liste dasteht.

    Gesucht wird in der Kopfzeile der Antwort **und** im Rest nach dem
    Literal: RFC 3501 legt die Reihenfolge der Antwortteile nicht fest, und
    ein Server darf `FLAGS (…)` hinter `BODY[…] {n}` schicken. `imaplib`
    liefert diesen Rest als eigenes Element nach dem Tupel (#478).
    """
    for teil in teile:
        treffer = _FAHNEN.search(teil or b"")
        if treffer:
            return tuple(treffer.group(1).decode("utf-8", "replace").lower().split())
    return None


def _uid(*teile: bytes) -> str | None:
    """Die UID aus der FETCH-Antwort, vor oder hinter dem Literal.

    Aus demselben Grund wie bei `_fahnen`: Die Reihenfolge der Antwortteile
    ist frei, und `UID 42` darf hinter `BODY[…] {n}` stehen. Bis zum
    Nachreview von #494 las nur die Kopfzeile, und eine solche Mail fiel
    stumm aus der Liste (Befund 2).
    """
    for teil in teile:
        treffer = _UID.search(teil or b"")
        if treffer:
            return treffer.group(1).decode()
    return None


def _ankunft(*teile: bytes) -> datetime | None:
    """INTERNALDATE als UTC, vor oder hinter dem Literal; `None`, wenn es fehlt."""
    treffer = None
    for teil in teile:
        treffer = _ANKUNFT.search(teil or b"")
        if treffer:
            break
    if not treffer:
        return None
    zeit = imaplib.Internaldate2tuple(b'INTERNALDATE "' + treffer.group(1) + b'"')
    if zeit is None:
        return None
    return datetime.fromtimestamp(time.mktime(zeit), tz=timezone.utc)


# ── Die Sitzung ─────────────────────────────────────────────────────────────

class Postfach:
    """Eine angemeldete Sitzung. Als Kontextmanager: Abmelden geschieht immer."""

    def __init__(self, verbindung, adresse: str, frist: float):
        self._v = verbindung
        self.adresse = adresse
        self.frist = frist
        self._bis = time.monotonic() + frist
        #: Ordner, in denen `koepfe` mehr fand, als es ansah: (gefunden, angesehen).
        self.gekappt: dict[str, tuple[int, int]] = {}
        #: Kennungssuchen, die mehr Teiltreffer fanden, als sie verglichen:
        #: (ordner, kennung, gefunden, verglichen). Getrennt von `gekappt`, denn
        #: der Ordner selbst wurde dabei nicht gekappt, und ein zweiter Eintrag
        #: unter demselben Ordnernamen überschriebe eine echte Ordnerkappung.
        self.suchkappungen: list[tuple[str, str, int, int]] = []
        #: Die UIDVALIDITY je Ordner, wie das **erste** `EXAMINE` der Sitzung
        #: sie nannte; `None`, wenn der Server keine nannte (#495). Die erste,
        #: weil die UIDs eines Laufs ab dort gesammelt werden: Wechselt der Wert
        #: später, weicht er von diesem ab, und `ablage.verschiebe` sieht es.
        self.uidvalidity: dict[str, str | None] = {}

    def __enter__(self) -> "Postfach":
        return self

    def __exit__(self, *_a) -> None:
        self.abmelden()

    def _rest(self) -> None:
        """Die verbleibende Zeit auf den Socket legen — oder abbrechen."""
        rest = self._bis - time.monotonic()
        if rest <= 0:
            raise PostfachFehler(f"Zeitlimit von {self.frist:g} s überschritten")
        sock = getattr(self._v, "sock", None)
        if sock is not None:
            sock.settimeout(rest)

    def _befehl(self, was: str, aufruf, *args, **kwargs):
        self._rest()
        try:
            typ, daten = aufruf(*args, **kwargs)
        except (imaplib.IMAP4.error, OSError, ValueError) as fehler:
            # `ValueError`: `imaplib` kodiert Argumente mit ASCII
            # (`UnicodeEncodeError`) und lehnt ab 3.14 Umbruch und Nullbyte ab
            # („NUL, CR and LF not allowed“). Beides wirft, bevor etwas gesendet
            # ist, und ist kein IMAP-Fehler. Entkäme es hier, stünde ein
            # Traceback da, und `verbinde` meldete nicht ab (Review von #460).
            raise PostfachFehler(f"{was}: {_kurz(fehler)}") from None
        if typ != "OK":
            raise PostfachFehler(f"{was}: {_kurz(daten)}")
        return daten

    def ordner_liste(self) -> list[tuple[str, tuple[str, ...]]]:
        """Alle Ordner als `(name, kennzeichen)` — ein `LIST`, nur lesend.

        Die Kennzeichen sind die Attribute aus RFC 3501/6154, klein
        geschrieben: `\\hasnochildren`, `\\sent`, `\\drafts` … Ein Ordner, den
        der Server nicht kennzeichnet, hat trotzdem einen Namen — genau
        deshalb gibt es diese Liste neben `sonderordner`.
        """
        daten = self._befehl("LIST", self._v.list, '""', "*")
        muster = re.compile(r'\(([^)]*)\)\s+(?:"[^"]*"|NIL)\s+(.*)$')
        ordner: list[tuple[str, tuple[str, ...]]] = []
        for eintrag in daten or []:
            if isinstance(eintrag, tuple):
                eintrag = eintrag[0] + b" " + eintrag[1]
            zeile = eintrag.decode("utf-8", "replace") if isinstance(eintrag, bytes) else str(eintrag)
            treffer = muster.match(zeile.strip())
            if not treffer:
                continue
            name = treffer.group(2).strip()
            if len(name) >= 2 and name[0] == name[-1] == '"':
                name = name[1:-1].replace('\\"', '"').replace("\\\\", "\\")
            ordner.append((name, tuple(treffer.group(1).lower().split())))
        return ordner

    def sonderordner(self, kennzeichen: str) -> str | None:
        """Der Ordner, den der Server mit `\\Sent`, `\\Drafts` … kennzeichnet (RFC 6154).

        `None` heißt „nicht gekennzeichnet“, nicht „gibt es nicht“: An den
        Microsoft-Konten des Betreibers liegt ein Ordner „Archiv“, und
        `\\Archive` kennzeichnet ihn trotzdem keiner (gemessen 28.10.2026).
        """
        gesucht = kennzeichen.lower()
        for name, kennzeichen_des_ordners in self.ordner_liste():
            if gesucht in kennzeichen_des_ordners:
                return name
        return None

    def _waehle(self, ordner: str) -> None:
        """`EXAMINE` — nur lesend. Ein `SELECT` gibt es in diesem Modul nicht."""
        self._befehl(f"Ordner „{utf7_dekodieren(ordner)}“ nicht lesbar",
                     self._v.select, _zitiert(ordner), readonly=True)
        self.uidvalidity.setdefault(ordner, self._lies_uidvalidity())

    def _lies_uidvalidity(self) -> str | None:
        """Die UIDVALIDITY aus der Antwort auf das letzte `EXAMINE` oder `SELECT`.

        Eine UID gilt nur zusammen mit diesem Wert (RFC 3501, 2.3.1.1). Der
        Server nennt ihn als Antwortcode `[UIDVALIDITY n]`, `imaplib` legt ihn
        unter `untagged_responses` ab, und `response()` liest ihn aus. Nennt der
        Server keinen oder keinen ganzzahligen, kommt `None` zurück: unbekannt,
        nicht „gleich“ (#495).
        """
        lesen = getattr(self._v, "response", None)
        if lesen is None:
            return None
        _, werte = lesen("UIDVALIDITY")
        wert = next((w for w in reversed(werte or []) if w is not None), None)
        if isinstance(wert, bytes):
            wert = wert.decode("ascii", "replace")
        try:
            zahl = int(str(wert).strip())
        except (TypeError, ValueError):
            return None
        return str(zahl) if zahl > 0 else None

    def _suche_kopfzeile(self, ordner: str, feld: str, wert: str) -> list[str]:
        """Die UIDs im Ordner, deren Kopfzeile `feld` den `wert` **enthält**.

        `UID SEARCH HEADER` — nur lesend, und es lässt den Server suchen,
        statt alle Köpfe zu holen: Ein Eingang mit Jahren an Post würde sonst
        an `GRENZE` gekappt, und gerade die ältere Nachricht ist die gesuchte.
        Am Microsoft-Konto gegengeprüft (28.10.2026): dieselben Treffer wie
        ein Kopfvergleich von Hand, und eine erfundene Message-ID findet
        nichts.

        Privat, weil das Ergebnis eine Teilkettensuche ist: `123` findet auch
        `<x123y@…>`. Bis #468 war sie öffentlich, und nur ein Satz hier verlangte
        den Nachvergleich. Ein Aufrufer, der ihn vergaß, hätte #442 zurückgeholt.
        Von außen geht es über `suche_kennung`.
        """
        self._waehle(ordner)
        daten = self._befehl("SEARCH", self._v.uid, "SEARCH", "HEADER", feld, _zitiert(wert))
        return [u.decode() for u in ((daten[0] or b"").split() if daten else [])]

    def suche_kennung(self, ordner: str, kennung: str) -> list[Kopf]:
        """Die Köpfe im Ordner, deren Message-ID genau `kennung` ist (#442, #468).

        Suche, Abruf und exakter Vergleich in einem Schritt. Die Teiltreffer des
        Servers werden bis `SUCHGRENZE` **alle** geholt, nicht die neuesten
        `GRENZE`: Bei einer kurzen Kennung können es mehr sein, und gekappt vor
        dem Vergleich fiele gerade die ältere, echte Nachricht heraus. Der
        Grenz-Hinweis erschiene dann obendrein, ausgelöst nur von fremden
        Treffern. `koepfe` holt sie in Stücken zu höchstens `GRENZE` UIDs je
        Befehl.

        Gekappt wird hier, nicht in `koepfe`, und vermerkt in `suchkappungen`.
        Bis zum Nachreview von #492 kappte `koepfe` und schrieb nach `gekappt`;
        dann hieß es „nur die neuesten 2000 von N Mails angesehen“ über einen
        Ordner, der gar nicht gekappt war (Befund 1).
        """
        uids = self._suche_kopfzeile(ordner, "Message-ID", kennung)
        if not uids:
            return []
        grenze = SUCHGRENZE
        if len(uids) > grenze:
            # Je Ordner und Kennung ein Eintrag: Beantworten drei Antworten dieselbe
            # Kennung, stand derselbe Satz sonst dreimal im Bericht (#515, Befund 2).
            if not any((o, k) == (ordner, kennung) for o, k, *_ in self.suchkappungen):
                self.suchkappungen.append((ordner, kennung, len(uids), grenze))
            uids = uids[-grenze:]
        return [kopf for kopf in self.koepfe(ordner, uids=uids, grenze=grenze)
                if gleiche_kennung(kennung, kopf.kennung)]

    def koepfe(self, ordner: str, seit: date | None = None, *,
               grenze: int | None = None, uids: list[str] | None = None) -> list[Kopf]:
        """Die Kopfzeilen der Nachrichten im Ordner, seit einem Tag oder alle.

        `SINCE` ist tagesgenau und richtet sich nach der Ankunft; die genaue
        Grenze zieht der Aufrufer am `datum` des Kopfs. Mit `uids` wird nicht
        gesucht, sondern genau diese Nachrichten geholt.
        """
        self._waehle(ordner)
        if uids is None:
            kriterien = ("SINCE", seit.strftime("%d-%b-%Y")) if seit else ("ALL",)
            daten = self._befehl("SEARCH", self._v.uid, "SEARCH", *kriterien)
            uids = [u.decode() for u in ((daten[0] or b"").split() if daten else [])]
        uids = list(uids)
        grenze = GRENZE if grenze is None else grenze
        if len(uids) > grenze:
            self.gekappt[ordner] = (len(uids), grenze)
            uids = uids[-grenze:]
        if not uids:
            return []
        # FLAGS liest nur: `BODY.PEEK` setzt kein `\Seen`, und FLAGS ohne STORE
        # ändert nichts. Gebraucht für das Fähnchen in `ablage` (#478).
        teile = ("(UID INTERNALDATE FLAGS BODY.PEEK[HEADER.FIELDS ("
                 + " ".join(KOPFZEILEN) + ")])")
        daten = []
        # Je Befehl höchstens GRENZE UIDs, sonst wird die Befehlszeile zu lang.
        for start in range(0, len(uids), GRENZE):
            stueck = ",".join(uids[start:start + GRENZE])
            daten.extend(self._befehl("FETCH", self._v.uid, "FETCH", stueck, teile) or [])
        koepfe = []
        for nummer, eintrag in enumerate(daten):
            if not isinstance(eintrag, tuple) or len(eintrag) < 2:
                continue
            meta, roh = eintrag[0], eintrag[1]
            # Hinter einem Literal liefert `imaplib` immer den Rest **derselben**
            # Antwortzeile als eigenes Element, mindestens `)`. Die nächste
            # Antwort beginnt erst danach.
            rest = daten[nummer + 1] if nummer + 1 < len(daten) else b""
            rest = rest if isinstance(rest, bytes) else b""
            uid = _uid(meta, rest)
            if uid is None:
                continue
            koepfe.append(kopf_aus(roh or b"", uid, _ankunft(meta, rest),
                                   _fahnen(meta, rest)))
        return koepfe

    def nachricht(self, ordner: str, uid: str) -> bytes:
        """Die ganze Nachricht, byte-gleich — ohne `\\Seen` zu setzen."""
        self._waehle(ordner)
        daten = self._befehl("FETCH", self._v.uid, "FETCH", str(uid), "(BODY.PEEK[])")
        for eintrag in daten or []:
            if isinstance(eintrag, tuple) and len(eintrag) >= 2:
                return bytes(eintrag[1] or b"")
        raise PostfachFehler(f"FETCH: Nachricht {uid} kam nicht zurück")

    def ablegen(self, ordner: str, roh: bytes) -> None:
        """Legt die Bytes als gelesenen Entwurf in den Ordner. Der einzige schreibende Befehl."""
        self._befehl(f"APPEND in „{utf7_dekodieren(ordner)}“", self._v.append,
                     _zitiert(ordner), "(\\Draft \\Seen)",
                     imaplib.Time2Internaldate(time.time()), roh)

    def abmelden(self) -> None:
        try:
            self._v.logout()
        except Exception:  # noqa: BLE001 — eine Abmeldung, die scheitert, ändert nichts mehr
            pass


def _kurz(fehler) -> str:
    """Eine Server- oder Socketmeldung, lesbar und auf eine Zeile gekürzt."""
    if isinstance(fehler, list):
        fehler = b" ".join(f for f in fehler if isinstance(f, bytes)) or str(fehler)
    if isinstance(fehler, bytes):
        fehler = fehler.decode("utf-8", "replace")
    text = " ".join(str(fehler).split())
    return text[:200] or type(fehler).__name__


def verbinde(adresse: str, *, umgebung: Mapping[str, str] | None = None,
             frist: float = FRIST_S) -> Postfach:
    """Meldet sich als `adresse` am Proxy an — oder wirft `PostfachFehler` mit Grund.

    Die Frist gilt für die ganze Sitzung: Verbindungsaufbau, Anmeldung und
    jeder Befehl danach ziehen von derselben Zeit ab.

    Der Anmeldename geht durch `_zitiert`, vor dem Verbindungsaufbau.
    `imaplib.login` zitiert nur das Kennwort, den Namen setzt es roh in den
    Befehl. Ein Umbruch begänne dort einen zweiten Befehl (#442, N4), und ein
    Leerzeichen oder ein `{5}` am Ende würde als weiteres Argument oder als
    Literal gelesen (Review von #460). `emailproxy` nimmt die
    Anführungszeichen wieder ab (`OAuth2Helper.strip_quotes`, gelesen am
    03.11.2026 in der Fassung, die der laufende Proxy lädt).
    """
    import os

    try:
        anmeldename = _zitiert(adresse)
    except PostfachFehler:
        raise PostfachFehler(
            "die Absenderadresse enthält einen Umbruch oder ein Nullbyte — als Anmeldename "
            "begänne sie einen zweiten IMAP-Befehl, deshalb wird nicht angemeldet") from None
    umgebung = os.environ if umgebung is None else umgebung
    host, port = ziel(umgebung)
    wo = f"{host}:{port}"
    try:
        verbindung = IMAP_KLASSE(host, port, timeout=frist)
    except ConnectionRefusedError:
        raise PostfachFehler(f"kein IMAP-Proxy unter {wo} (Verbindung abgelehnt)") from None
    except TimeoutError:
        raise PostfachFehler(f"keine Antwort von {wo} in {frist:g} s") from None
    except (OSError, imaplib.IMAP4.error) as fehler:
        raise PostfachFehler(f"keine Verbindung zu {wo}: {_kurz(fehler)}") from None
    postfach = Postfach(verbindung, adresse, frist)
    try:
        postfach._befehl(f"Anmeldung als {adresse} an {wo} abgelehnt",
                         verbindung.login, anmeldename, KENNWORT)
    except PostfachFehler:
        postfach.abmelden()
        raise
    return postfach
