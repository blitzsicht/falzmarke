"""Zuruf an die Entwurfsbrücke in Thunderbird (ADR 0052).

Das Add-on unter `thunderbird/entwurfsbruecke/` lauscht auf 127.0.0.1 und
öffnet einen Entwurf aus dem Entwürfe-Ordner eines Kontos so, wie es
„Entwurf bearbeiten“ tut: als Verfassen-Fenster, das auf die Nachricht im
Ordner zeigt. Nach dem Senden räumt Thunderbird diesen Entwurf selbst weg —
gemessen am 25.10.2026, gegengeprüft per IMAP im Gesendet-Ordner. Eine `.eml`
mit `X-Unsent: 1` öffnet dagegen nur eine Kopie; der Entwurf bliebe liegen.

Dieses Modul ist die Gegenseite: eine Zeile JSON hin, eine zurück, beides
ASCII. Kein `subprocess` (das bleibt in `oeffnen.py`, ADR 0038 Punkt 5), kein
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
from collections.abc import Mapping
from typing import NamedTuple

#: Der Port, auf dem das Add-on lauscht. In Thunderbird umzustellen über die
#: Einstellung `falzmarke.entwurfsbruecke.port`, hier über
#: `FALZMARKE_BRUECKE_PORT`.
PORT = 1994

#: Wie verbunden wird. `None` heißt `socket.create_connection`, zur Laufzeit
#: nachgeschlagen — so greift der Wächter in `tests/conftest.py` auch dann,
#: wenn ein Test die Attrappe vergisst.
VERBINDEN = None

#: Länger ist keine Antwort des Add-ons; was darüber liegt, ist nicht von ihm.
MAX_ANTWORT = 65536

FRIST_PING_S = 3
#: Das Add-on lädt den Ordner bis zu 15 s nach und wartet bis zu 20 s auf das
#: Fenster; dazu kommt der Weg.
FRIST_OEFFNEN_S = 45

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


def abgeschaltet(umgebung: Mapping[str, str] | None = None) -> str:
    """Der Grund, warum die Brücke nicht gerufen wird — oder leer."""
    umgebung = os.environ if umgebung is None else umgebung
    if (umgebung.get("FALZMARKE_BRUECKE") or "").strip().lower() == "nie":
        return "FALZMARKE_BRUECKE=nie ist gesetzt"
    return ""


def port(umgebung: Mapping[str, str] | None = None) -> int:
    umgebung = os.environ if umgebung is None else umgebung
    wert = (umgebung.get("FALZMARKE_BRUECKE_PORT") or "").strip()
    return int(wert) if wert.isdigit() else PORT


def rufe(anfrage: Mapping, *, umgebung: Mapping[str, str] | None = None,
         frist: float = FRIST_PING_S) -> dict:
    """Schickt eine Anfrage und gibt die Antwort zurück; wirft `BrueckenFehler`."""
    ziel = port(umgebung)
    zeile = (json.dumps(dict(anfrage), ensure_ascii=True) + "\n").encode("ascii")
    verbinden = VERBINDEN or socket.create_connection
    daten = b""
    abgeschickt = False
    try:
        with verbinden(("127.0.0.1", ziel), timeout=frist) as verbindung:
            verbindung.sendall(zeile)
            abgeschickt = True
            while not daten.endswith(b"\n"):
                stueck = verbindung.recv(4096)
                if not stueck:
                    break
                daten += stueck
                if len(daten) > MAX_ANTWORT:
                    raise BrueckenFehler(f"die Antwort auf 127.0.0.1:{ziel} ist länger als "
                                         f"{MAX_ANTWORT} Byte — das ist nicht das Add-on")
    except ConnectionRefusedError:
        raise BrueckenFehler(f"auf 127.0.0.1:{ziel} antwortet nichts — Thunderbird ist zu "
                             "oder das Add-on Entwurfsbrücke fehlt") from None
    except TimeoutError:
        raise BrueckenFehler(f"keine Antwort in {frist:g} Sekunden",
                             ungewiss=abgeschickt) from None
    except OSError as fehler:
        raise BrueckenFehler(f"Verbindung zu 127.0.0.1:{ziel}: {fehler}",
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
    return antwort


def ping(*, umgebung: Mapping[str, str] | None = None) -> dict:
    """Name, Fassung und Thunderbird-Version — oder `BrueckenFehler`."""
    return rufe({"befehl": "ping"}, umgebung=umgebung, frist=FRIST_PING_S)


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
        kennung = str(antwort.get("fehler") or "")
        text = FEHLERTEXTE.get(kennung, f"das Add-on meldet „{kennung or 'unbekannt'}“")
        meldung = str(antwort.get("meldung") or "")
        return Oeffnung("fehler", grund=f"{text} ({meldung})" if meldung else text)
    zustand = str(antwort.get("zustand") or "")
    betreff = str(antwort.get("betreff") or "")
    if zustand in ("geoeffnet", "schon_offen"):
        return Oeffnung(zustand, betreff=betreff)
    if zustand == "fenster_ohne_entwurf":
        return Oeffnung("ungewiss", grund="ein Fenster ging auf, aber der Entwurf kam nicht "
                                          "hinein — in Thunderbird nachsehen")
    return Oeffnung("ungewiss", grund="Thunderbird hat den Auftrag angenommen, ein Fenster "
                                      "war in 20 Sekunden nicht zu sehen")
