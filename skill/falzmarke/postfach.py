"""Das Postfach des Absenders — gelesen über den lokalen IMAP-Proxy (ADR 0051).

Zwei Dinge braucht `email --oeffnen` aus dem Postfach, und nur diese:

* **lesen**, was in den letzten Stunden gesendet wurde und welche Entwürfe
  liegen — mit `EXAMINE` (nur lesend) und `BODY.PEEK` (setzt kein `\\Seen`);
* **einen Entwurf ablegen** — `APPEND` mit `\\Draft \\Seen` in den
  Entwürfe-Ordner. Das ist der einzige schreibende Befehl in diesem Modul.

Es gibt hier kein `STORE`, `EXPUNGE`, `COPY`, `MOVE` oder `DELETE`, und keinen
Versandweg: IMAP kann nicht senden, und `smtplib` ist nicht importiert.
`tests/test_postfach.py` liest das am Syntaxbaum nach.

**Der Weg:** unverschlüsselt an einen Proxy auf dem eigenen Rechner (Vorgabe
`127.0.0.1:1993`, `FALZMARKE_GESENDET_IMAP`), Benutzer ist die Absenderadresse,
das Kennwort ist ein Platzhalter — der Proxy tauscht die Anmeldung gegen OAuth
und spricht TLS mit dem Server. So läuft es beim Betreiber mit `emailproxy`
für die Microsoft-Konten. Ein Konto, das der Proxy nicht kennt (Gmail), lehnt
er ab, ohne den Server zu fragen; dann heißt es „nicht geprüft", mit seiner
Meldung als Grund.

Kein `subprocess`: Die Regel „genau ein Modul startet fremde Programme"
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
#: Ein hängender Proxy darf `--oeffnen` nicht länger aufhalten als das.
FRIST_S = 5

#: Der Proxy nimmt jedes Kennwort; sein Kennwort ist das OAuth-Token. Derselbe
#: Platzhalter wie im Mailarchiv des Betreibers (`zaehler.imap_zaehlung`).
KENNWORT = "dummy"

#: Höchstens so viele Nachrichten werden je Ordner angesehen, die neuesten.
#: Ein Entwürfe-Ordner mit Jahren an Resten soll die Prüfung nicht ausbremsen.
GRENZE = 500

#: Die Kopfzeilen, die je Nachricht gelesen werden — nie der ganze Inhalt,
#: bevor feststeht, dass der Empfänger passt.
KOPFZEILEN = ("DATE", "TO", "CC", "BCC", "SUBJECT", "IN-REPLY-TO", "X-FALZMARKE-FASSUNG")


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


def _zitiert(name: str) -> str:
    """Ein Ordnername als IMAP-Zeichenkette — immer in Anführungszeichen.

    `Gesendete Elemente` hat ein Leerzeichen; unzitiert wären es zwei Argumente.
    """
    return '"' + name.replace("\\", "\\\\").replace('"', '\\"') + '"'


# ── Ziel ────────────────────────────────────────────────────────────────────

def ziel(umgebung: Mapping[str, str]) -> tuple[str, int]:
    """Host und Port aus `FALZMARKE_GESENDET_IMAP`, Vorgabe `127.0.0.1:1993`."""
    wert = (umgebung.get("FALZMARKE_GESENDET_IMAP") or ZIEL_VORGABE).strip()
    host, _, port = wert.rpartition(":")
    if not host or not port.isdigit():
        raise PostfachFehler(f"FALZMARKE_GESENDET_IMAP={wert} ist kein host:port")
    return host, int(port)


# ── Kopfzeilen ──────────────────────────────────────────────────────────────

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


def _adressen(nachricht, *felder: str) -> tuple[str, ...]:
    werte = [str(w) for feld in felder for w in nachricht.get_all(feld, [])]
    gesehen: list[str] = []
    for _, adresse in getaddresses(werte):
        adresse = adresse.strip().lower()
        if adresse and adresse not in gesehen:
            gesehen.append(adresse)
    return tuple(gesehen)


def kopf_aus(roh: bytes, uid: str, ankunft: datetime | None) -> Kopf:
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
    return Kopf(uid=uid, datum=datum or ankunft, an=_adressen(nachricht, "To", "Cc", "Bcc"),
                betreff=betreff, fassung=str(nachricht.get("X-Falzmarke-Fassung") or "").strip(),
                antwort_auf=str(nachricht.get("In-Reply-To") or "").strip())


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


def _ankunft(meta: bytes) -> datetime | None:
    treffer = _ANKUNFT.search(meta)
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
        except (imaplib.IMAP4.error, OSError) as fehler:
            raise PostfachFehler(f"{was}: {_kurz(fehler)}") from None
        if typ != "OK":
            raise PostfachFehler(f"{was}: {_kurz(daten)}")
        return daten

    def sonderordner(self, kennzeichen: str) -> str | None:
        """Der Ordner, den der Server mit `\\Sent`, `\\Drafts` … kennzeichnet (RFC 6154)."""
        daten = self._befehl("LIST", self._v.list, '""', "*")
        muster = re.compile(r'\(([^)]*)\)\s+(?:"[^"]*"|NIL)\s+(.*)$')
        for eintrag in daten or []:
            if isinstance(eintrag, tuple):
                eintrag = eintrag[0] + b" " + eintrag[1]
            zeile = eintrag.decode("utf-8", "replace") if isinstance(eintrag, bytes) else str(eintrag)
            treffer = muster.match(zeile.strip())
            if not treffer:
                continue
            if kennzeichen.lower() in treffer.group(1).lower().split():
                name = treffer.group(2).strip()
                if len(name) >= 2 and name[0] == name[-1] == '"':
                    name = name[1:-1].replace('\\"', '"').replace("\\\\", "\\")
                return name
        return None

    def _waehle(self, ordner: str) -> None:
        """`EXAMINE` — nur lesend. Ein `SELECT` gibt es in diesem Modul nicht."""
        self._befehl(f"Ordner „{utf7_dekodieren(ordner)}“ nicht lesbar",
                     self._v.select, _zitiert(ordner), readonly=True)

    def koepfe(self, ordner: str, seit: date | None = None, *,
               grenze: int | None = None) -> list[Kopf]:
        """Die Kopfzeilen der Nachrichten im Ordner, seit einem Tag oder alle.

        `SINCE` ist tagesgenau und richtet sich nach der Ankunft; die genaue
        Grenze zieht der Aufrufer am `datum` des Kopfs.
        """
        self._waehle(ordner)
        kriterien = ("SINCE", seit.strftime("%d-%b-%Y")) if seit else ("ALL",)
        daten = self._befehl("SEARCH", self._v.uid, "SEARCH", *kriterien)
        uids = [u.decode() for u in ((daten[0] or b"").split() if daten else [])]
        grenze = GRENZE if grenze is None else grenze
        if len(uids) > grenze:
            self.gekappt[ordner] = (len(uids), grenze)
            uids = uids[-grenze:]
        if not uids:
            return []
        teile = "(UID INTERNALDATE BODY.PEEK[HEADER.FIELDS (" + " ".join(KOPFZEILEN) + ")])"
        daten = []
        # Je Befehl höchstens GRENZE UIDs, sonst wird die Befehlszeile zu lang.
        for start in range(0, len(uids), GRENZE):
            stueck = ",".join(uids[start:start + GRENZE])
            daten.extend(self._befehl("FETCH", self._v.uid, "FETCH", stueck, teile) or [])
        koepfe = []
        for eintrag in daten:
            if not isinstance(eintrag, tuple) or len(eintrag) < 2:
                continue
            meta, roh = eintrag[0], eintrag[1]
            uid = _UID.search(meta)
            if uid is None:
                continue
            koepfe.append(kopf_aus(roh or b"", uid.group(1).decode(), _ankunft(meta)))
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
    """
    import os

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
                         verbindung.login, adresse, KENNWORT)
    except PostfachFehler:
        postfach.abmelden()
        raise
    return postfach
