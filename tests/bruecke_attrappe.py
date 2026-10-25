"""Die Entwurfsbrücke im Speicher — die Attrappe für `falzmarke.bruecke` (ADR 0052).

Sie steht für `socket.create_connection` und antwortet so, wie das Add-on es
tut: eine Zeile JSON, ASCII, mit `\\n` am Ende. Wer eine Antwort braucht, die
das Add-on nie gäbe (abgerissen, zu lang, kein JSON), reicht `roh` herein.
"""

from __future__ import annotations

import json


class BrueckenAttrappe:
    """Aufrufen wie `socket.create_connection`, danach `anfragen` lesen."""

    def __init__(self, antwort=None, *, roh: bytes | None = None,
                 fehler: BaseException | None = None,
                 fehler_beim_lesen: BaseException | None = None) -> None:
        #: Eine feste Antwort (dict) oder eine Funktion Anfrage → Antwort.
        self.antwort = antwort
        self.roh = roh
        self.fehler = fehler
        self.fehler_beim_lesen = fehler_beim_lesen
        self.anfragen: list[dict] = []
        self.zeilen: list[bytes] = []
        self.adressen: list[tuple] = []

    def __call__(self, adresse, timeout=None):
        self.adressen.append(tuple(adresse))
        if self.fehler is not None:
            raise self.fehler
        return _Verbindung(self)

    def oeffnungen(self) -> list[tuple[str, int]]:
        return [(a["konto"], a["uid"]) for a in self.anfragen
                if a.get("befehl") == "entwurf_oeffnen"]


def _standard(anfrage: dict) -> dict:
    if anfrage.get("befehl") == "ping":
        return {"ok": True, "name": "entwurfsbruecke", "version": "0.1.1",
                "thunderbird": "158.0.1"}
    if anfrage.get("befehl") == "entwurf_oeffnen":
        return {"ok": True, "zustand": "geoeffnet", "betreff": "aus dem Fenster"}
    return {"ok": False, "fehler": "befehl_unbekannt"}


class _Verbindung:
    def __init__(self, attrappe: BrueckenAttrappe) -> None:
        self.attrappe = attrappe
        self.ausgang = b""

    def __enter__(self):
        return self

    def __exit__(self, *_a):
        return False

    def sendall(self, daten: bytes) -> None:
        self.attrappe.zeilen.append(daten)
        anfrage = json.loads(daten.decode("ascii"))
        self.attrappe.anfragen.append(anfrage)
        if self.attrappe.roh is not None:
            self.ausgang = self.attrappe.roh
            return
        antwort = self.attrappe.antwort
        if antwort is None:
            antwort = _standard(anfrage)
        elif callable(antwort):
            antwort = antwort(anfrage)
        self.ausgang = (json.dumps(antwort, ensure_ascii=True) + "\n").encode("ascii")

    def recv(self, anzahl: int) -> bytes:
        if self.attrappe.fehler_beim_lesen is not None:
            raise self.attrappe.fehler_beim_lesen
        stueck, self.ausgang = self.ausgang[:anzahl], self.ausgang[anzahl:]
        return stueck
