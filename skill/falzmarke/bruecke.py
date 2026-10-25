"""Zuruf an die Entwurfsbrücke in Thunderbird (ADR 0054).

Das Add-on unter `thunderbird/entwurfsbruecke/` lauscht auf einem
Unix-Socket im Thunderbird-Profil (ADR 0059) und öffnet einen Entwurf aus dem Entwürfe-Ordner eines Kontos so, wie es
„Entwurf bearbeiten“ tut: als Verfassen-Fenster, das auf die Nachricht im
Ordner zeigt. Nach dem Senden räumt Thunderbird diesen Entwurf selbst weg —
gemessen am 25.10.2026, gegengeprüft per IMAP im Gesendet-Ordner. Eine `.eml`
mit `X-Unsent: 1` öffnet dagegen nur eine Kopie; der Entwurf bliebe liegen.

Dieses Modul ist die Gegenseite: eine Zeile JSON hin, eine zurück, beides
ASCII. Bis 0.3.0 lief das über 127.0.0.1:1994 — ein Port, den jeder Prozess
jedes Benutzers erreicht und den jeder vor Thunderbird belegen kann. Jetzt
entscheiden die Rechte am Socket (0600) darüber, wer zuruft. Kein `subprocess` (das bleibt in `oeffnen.py`, ADR 0038 Punkt 5), kein
`imaplib`. Der MCP-Dienst lädt es nicht; `cli.py` und `oeffnen.py` holen es
erst, wenn ein Fenster aufgehen soll.

Die Brücke kann nicht senden. Sie kennt `ping`, `entwurf_oeffnen`, `fenster`
und `protokoll` — `tests/test_entwurfsbruecke.py` hält das am Quelltext des
Add-ons fest.
"""

from __future__ import annotations

import json
import os
import socket
import unicodedata
from collections.abc import Mapping
from pathlib import Path
from typing import NamedTuple

#: Der Name des Sockets im Thunderbird-Profil. Kurz, weil `sun_path` auf
#: macOS nur 104 Byte fasst: Gemessen am 25.10.2026 ist der Profilordner
#: dieses Rechners 74 Byte lang, mit `falzmarke-entwurfsbruecke.sock` wären
#: es 105 Byte gewesen — eins zu viel. Mit diesem Namen sind es 87.
SOCKET_DATEI = "bruecke.sock"

#: Mehr Byte fasst `sun_path` nicht (macOS 104, Linux 108). Darüber wirft
#: `connect` ein nacktes `OSError`; die Meldung hier sagt stattdessen, was
#: zu tun ist.
MAX_SOCKETPFAD = 104

#: Was das Add-on als `name` melden muss. Antwortet etwas anderes auf dem
#: Socket, ist es nicht die Brücke — und seine Angaben sind keine Aussage
#: über Thunderbird.
NAME = "entwurfsbruecke"

#: Wie verbunden wird. `None` heißt `_verbinde_unix`, zur Laufzeit
#: nachgeschlagen — so greift der Wächter in `tests/conftest.py` auch dann,
#: wenn ein Test die Attrappe vergisst. Der Wächter legt `_verbinde_unix`
#: selbst um, nicht diese Weiche: Ein Test, der die Attrappe vergisst, soll
#: am ausgeführten Weg scheitern und nicht an einem Vergleich.
VERBINDEN = None

#: Länger ist keine Antwort des Add-ons; was darüber liegt, ist nicht von ihm.
#: Seit 0.3.0 meldet `fenster` den Text jedes offenen Fensters mit, bis zu
#: 20.000 Zeichen, als ASCII-Escape bis zu sechsmal so lang (ADR 0056).
MAX_ANTWORT = 1024 * 1024

FRIST_PING_S = 3
#: Das Add-on lädt den Ordner bis zu 15 s nach, wartet bis zu 20 s auf das
#: Fenster und noch einmal bis zu 20 s auf den Entwurf darin; dazu kommt der Weg.
FRIST_OEFFNEN_S = 65

#: Was die Fehlerkennungen des Add-ons in einem Satz heißen.
FEHLERTEXTE = {
    "konto_fehlt": "Thunderbird kennt kein Konto mit dieser Adresse",
    "uid_ungueltig": "die Kennung des Entwurfs ist keine gültige UID",
    "entwurfsordner_fehlt": "Thunderbird findet den Entwürfe-Ordner dieses Kontos nicht",
    "oeffnen_fehlgeschlagen": "Thunderbird hat das Öffnen abgelehnt",
    "befehl_unbekannt": "das Add-on kennt den Befehl nicht (zu alte Fassung?)",
    "kein_json": "das Add-on hat die Anfrage nicht verstanden",
    "zeile_zu_lang": "die Anfrage war zu lang",
    "intern": "im Add-on ist ein Fehler aufgetreten",
}

#: Kein Profil, kein Socket. Beides heißt: Es gibt hier nichts zu rufen.
OHNE_PROFIL = "Thunderbird hat auf diesem Rechner kein Standardprofil"


class BrueckenFehler(Exception):
    """Die Brücke war nicht zu erreichen oder antwortete unbrauchbar.

    `ungewiss` heißt: Die Anfrage ist abgeschickt, die Antwort fehlt. Ob in
    Thunderbird ein Fenster aufging, weiß dann niemand — wer jetzt ein zweites
    Mal ruft, öffnet womöglich zwei.
    """

    def __init__(self, meldung: str, *, ungewiss: bool = False) -> None:
        super().__init__(meldung)
        self.ungewiss = ungewiss


class Oeffnung(NamedTuple):
    """Was aus dem Versuch wurde, einen Entwurf zu öffnen.

    `zustand`:

    - `geoeffnet`, `schon_offen` — das Fenster steht, `betreff` ist der aus
      dem Fenster gelesene Betreff
    - `ungewiss` — angestoßen, aber kein Fenster gesehen, oder die Antwort fehlt
    - `fehler` — nichts angestoßen, `grund` sagt warum
    - `aus` — abgeschaltet (`FALZMARKE_BRUECKE=nie`)
    """

    zustand: str
    betreff: str = ""
    grund: str = ""

    @property
    def offen(self) -> bool:
        return self.zustand in ("geoeffnet", "schon_offen")


def _zahm(wert: str, *, mehrzeilig: bool = False) -> str:
    """Text aus der Antwort, bereinigt um Steuerzeichen.

    Was aus dem Socket kommt, geht in `print` — und `json.loads` lässt echte
    ESC-Sequenzen durch. Ein Betreff darf deshalb kein Steuerzeichen tragen,
    auch keinen Zeilenumbruch; der Text eines Fensters darf Umbruch und
    Tabulator behalten, sonst stünde er als eine Zeile da. Unsichtbare
    Formatzeichen (Kategorie Cf, darunter die Bidi-Umschalter) fallen in
    beiden Fällen weg — was sie anrichten, steht in ADR 0052.
    """
    erlaubt = "\n\t" if mehrzeilig else ""
    return "".join(z for z in wert
                   if z in erlaubt or unicodedata.category(z)[0] != "C")


def abgeschaltet(umgebung: Mapping[str, str] | None = None) -> str:
    """Der Grund, warum die Brücke nicht gerufen wird — oder leer."""
    umgebung = os.environ if umgebung is None else umgebung
    if (umgebung.get("FALZMARKE_BRUECKE") or "").strip().lower() == "nie":
        return "FALZMARKE_BRUECKE=nie ist gesetzt"
    return ""


def socketpfad(umgebung: Mapping[str, str] | None = None) -> str:
    """Der Socket im Thunderbird-Profil — oder leer, wenn es keines gibt.

    `FALZMARKE_BRUECKE_SOCKET` sticht; dann wird der Pfad genommen, wie er
    dasteht. Geworfen wird nichts: Ein fehlendes Profil ist kein Fehler
    dieses Moduls, sondern die Antwort „hier gibt es nichts zu rufen", und
    sie fällt beim Verbinden mit einem Satz heraus.
    """
    umgebung = os.environ if umgebung is None else umgebung
    wert = (umgebung.get("FALZMARKE_BRUECKE_SOCKET") or "").strip()
    if wert:
        return str(Path(wert).expanduser())
    # Erst hier, damit `bruecke` ohne `oeffnen` ladbar bleibt (ADR 0038).
    from falzmarke import oeffnen

    profil = oeffnen.thunderbird_standardprofil(oeffnen.THUNDERBIRD_ORDNER)
    return "" if profil is None else str(profil / SOCKET_DATEI)


def _sockel(pfad: str, timeout: float):
    """Nur das Verbinden — die Stelle, an der `tests/conftest.py` den Riegel legt.

    Getrennt von `_verbinde_unix`, damit die Prüfungen dort auch im Testlauf
    wirklich laufen: Ein Riegel über der ganzen Funktion hätte sie
    mitgenommen, und ein Prüfmittel, das nie rot werden kann, ist keines.
    """
    verbindung = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    verbindung.settimeout(timeout)
    try:
        verbindung.connect(pfad)
    except BaseException:
        verbindung.close()
        raise
    return verbindung


def _verbinde_unix(pfad: str, timeout: float):
    """Eine Verbindung zum Socket der Brücke. Wirft `BrueckenFehler`."""
    if not pfad:
        raise BrueckenFehler(OHNE_PROFIL)
    if len(pfad.encode("utf-8")) > MAX_SOCKETPFAD:
        raise BrueckenFehler(
            f"der Pfad zum Socket ist länger als {MAX_SOCKETPFAD} Byte — so weit reicht "
            "kein Unix-Socket. Mit FALZMARKE_BRUECKE_SOCKET einen kürzeren Pfad setzen "
            "(dieselbe Einstellung braucht dann das Add-on)")
    return _sockel(pfad, timeout)


def rufe(anfrage: Mapping, *, umgebung: Mapping[str, str] | None = None,
         frist: float = FRIST_PING_S) -> dict:
    """Schickt eine Anfrage und gibt die Antwort zurück; wirft `BrueckenFehler`."""
    ziel = socketpfad(umgebung)
    zeile = (json.dumps(dict(anfrage), ensure_ascii=True) + "\n").encode("ascii")
    verbinden = VERBINDEN or _verbinde_unix
    daten = b""
    abgeschickt = False
    try:
        with verbinden(ziel, timeout=frist) as verbindung:
            verbindung.sendall(zeile)
            abgeschickt = True
            while not daten.endswith(b"\n"):
                stueck = verbindung.recv(4096)
                if not stueck:
                    break
                daten += stueck
                if len(daten) > MAX_ANTWORT:
                    raise BrueckenFehler(f"die Antwort der Entwurfsbrücke ist länger als "
                                         f"{MAX_ANTWORT} Byte — das ist nicht das Add-on")
    except (ConnectionRefusedError, FileNotFoundError):
        raise BrueckenFehler("am Socket im Thunderbird-Profil antwortet nichts — "
                             "Thunderbird ist zu oder das Add-on Entwurfsbrücke fehlt") from None
    except TimeoutError:
        raise BrueckenFehler(f"keine Antwort in {frist:g} Sekunden",
                             ungewiss=abgeschickt) from None
    except OSError as fehler:
        raise BrueckenFehler(f"Verbindung zur Entwurfsbrücke: {fehler}",
                             ungewiss=abgeschickt) from None
    if not daten.endswith(b"\n"):
        raise BrueckenFehler("die Verbindung ging ohne vollständige Antwort zu",
                             ungewiss=abgeschickt)
    try:
        antwort = json.loads(daten.decode("ascii"))
    except (UnicodeDecodeError, ValueError):
        raise BrueckenFehler("die Antwort ist kein JSON — das ist nicht das Add-on",
                             ungewiss=abgeschickt) from None
    if not isinstance(antwort, dict):
        raise BrueckenFehler("die Antwort ist kein JSON-Objekt", ungewiss=abgeschickt)
    # Wer sich nicht als Brücke ausweist, ist keine. Die Rechte am Socket
    # machen das unwahrscheinlich, nicht unmöglich: `FALZMARKE_BRUECKE_SOCKET`
    # zeigt, wohin man es stellt.
    gemeldet = antwort.get("name")
    if gemeldet is not None and str(gemeldet) != NAME:
        raise BrueckenFehler(
            f"am Socket antwortet \u201e{_zahm(str(gemeldet))}\u201c, nicht die "
            "Entwurfsbrücke", ungewiss=abgeschickt)
    return antwort


def ping(*, umgebung: Mapping[str, str] | None = None) -> dict:
    """Name, Fassung und Thunderbird-Version — oder `BrueckenFehler`."""
    return rufe({"befehl": "ping"}, umgebung=umgebung, frist=FRIST_PING_S)


def offene_entwuerfe(*, umgebung: Mapping[str, str] | None = None) -> list[dict]:
    """Die offenen Verfassen-Fenster — oder `BrueckenFehler`.

    Je Fenster Titel, Betreff und `draft_id`, ab Add-on 0.3.0 dazu, was es jetzt
    hinausschicken würde: `identitaet`, `an`, `kopie`, `blindkopie`, `anhaenge`,
    `text` (ADR 0056). `live` ist falsch, wenn das Add-on das nicht lesen konnte.

    `draft_id` ist die Adresse der Nachricht im Entwürfe-Ordner, auf die das
    Fenster zeigt (`imap-message://…#<UID>`); `falzmarke status` erkennt daran,
    welcher Entwurf gerade offen ist (ADR 0055).
    """
    grund = abgeschaltet(umgebung)
    if grund:
        raise BrueckenFehler(grund)
    antwort = rufe({"befehl": "fenster"}, umgebung=umgebung, frist=FRIST_PING_S)
    if not antwort.get("ok") or not isinstance(antwort.get("fenster"), list):
        # Sonst hieße eine Fassung, die `fenster` nicht kennt, „kein Fenster offen“.
        kennung = _zahm(str(antwort.get("fehler") or "keine Fensterliste"))
        raise BrueckenFehler(FEHLERTEXTE.get(kennung, f"das Add-on meldet „{kennung}“"))
    return [_zahmes_fenster(f) for f in antwort["fenster"] if isinstance(f, dict)]


#: Diese Felder eines Fensters dürfen Umbrüche tragen, alle anderen nicht.
MEHRZEILIG = ("text",)


def _zahmes_fenster(fenster: Mapping) -> dict:
    """Ein Fenster aus der Antwort, Steuerzeichen heraus (ADR 0059)."""
    zahm = {}
    for schluessel, wert in fenster.items():
        mehrzeilig = schluessel in MEHRZEILIG
        if isinstance(wert, str):
            zahm[schluessel] = _zahm(wert, mehrzeilig=mehrzeilig)
        elif isinstance(wert, list):
            zahm[schluessel] = [_zahm(e, mehrzeilig=mehrzeilig) if isinstance(e, str) else e
                                for e in wert]
        else:
            zahm[schluessel] = wert
    return zahm


def entwurf_oeffnen(konto: str, uid: str | int, *,
                    umgebung: Mapping[str, str] | None = None) -> Oeffnung:
    """Öffnet den Entwurf `uid` im Entwürfe-Ordner von `konto`.

    Geworfen wird nichts: Wer hierher kommt, hat seinen Entwurf schon im
    Postfach, und ein fehlendes Fenster ist ein Hinweis, kein Abbruch.
    """
    grund = abgeschaltet(umgebung)
    if grund:
        return Oeffnung("aus", grund=grund)
    try:
        schluessel = int(str(uid))
    except ValueError:
        return Oeffnung("fehler", grund=FEHLERTEXTE["uid_ungueltig"])
    try:
        antwort = rufe({"befehl": "entwurf_oeffnen", "konto": konto, "uid": schluessel},
                       umgebung=umgebung, frist=FRIST_OEFFNEN_S)
    except BrueckenFehler as fehler:
        return Oeffnung("ungewiss" if fehler.ungewiss else "fehler", grund=str(fehler))
    if not antwort.get("ok"):
        kennung = _zahm(str(antwort.get("fehler") or ""))
        text = FEHLERTEXTE.get(kennung, f"das Add-on meldet „{kennung or 'unbekannt'}“")
        meldung = _zahm(str(antwort.get("meldung") or ""))
        return Oeffnung("fehler", grund=f"{text} ({meldung})" if meldung else text)
    zustand = str(antwort.get("zustand") or "")
    betreff = _zahm(str(antwort.get("betreff") or ""))
    if zustand in ("geoeffnet", "schon_offen"):
        return Oeffnung(zustand, betreff=betreff)
    if zustand == "fenster_ohne_entwurf":
        return Oeffnung("ungewiss", grund="ein Fenster ging auf, aber der Entwurf kam nicht "
                                          "hinein — in Thunderbird nachsehen")
    return Oeffnung("ungewiss", grund="Thunderbird hat den Auftrag angenommen, ein Fenster "
                                      "war in 20 Sekunden nicht zu sehen")
