#!/usr/bin/env python3
"""Spricht MCP über stdio mit einem gestarteten Server — und misst nach, was kommt.

WOFÜR

Ein Verzeichniseintrag verlangt, dass der Server „startet und auf
Introspektion antwortet". Das allein ist die Prüfung, die nie rot wird: Ein
Server, der startet und ein leeres Werkzeugverzeichnis meldet, bestünde sie.
Dieses Skript verlangt deshalb drei Dinge nacheinander:

    1. `initialize` wird beantwortet
    2. `tools/list` nennt **jeden** erwarteten Werkzeugnamen
    3. `tools/call brief_rendern` liefert wirklich ein PDF, und der
       mitgelieferte Messbericht endet ohne Fehler

Schritt 3 ist der Unterschied zwischen „der Container läuft" und „der Dienst
tut, wofür es ihn gibt". Ohne ihn belegte ein grüner Lauf nur, dass Python im
Container startet.

    python3 scripts/mcp_handschlag.py -- docker run --rm -i falzmarke-mcp
    python3 scripts/mcp_handschlag.py --ohne-render -- falzmarke mcp

Exit 0: alles wie erwartet. Exit 1: der Server antwortet nicht wie verlangt.
Der Aufrufbefehl steht hinter `--`, damit seine eigenen Optionen nicht hier
geparst werden.
"""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys

#: Die Werkzeuge, die der Dienst anmeldet. Kein Zählwert, sondern die Namen:
#: Eine Zahl in einer Doku altert still, ein fehlender Name fällt auf.
#: Abgeglichen gegen `dienst.WERKZEUGE` in tests/test_dienst_werkzeuge.py.
ERWARTETE_WERKZEUGE = ("brief_rendern", "email_setzen", "brief_pruefen", "profile_auflisten")

PROTOKOLL = "2025-06-18"

#: Ein Brief, der ohne Profildatei auskommt: Das Absenderprofil steht als
#: Objekt im Aufruf. Genau der Weg, den ein Client ohne Zugriff auf das
#: Dateisystem des Servers gehen muss — und im Container ist jeder Client so
#: einer.
BRIEF = """---
form: B
empfaenger:
  - Musterfirma GmbH
  - Musterstraße 1
  - 12345 Musterstadt
# Fest, nicht das Tagesdatum: Sonst hinge das Ergebnis dieser Prüfung davon ab,
# an welchem Tag sie läuft — und ein Unterschied wäre nicht mehr zuzuordnen.
datum: 2026-01-15
betreff: Handschlag aus der Prüfung
---

Sehr geehrte Damen und Herren,

dieser Brief entsteht im Container, damit die Prüfung nicht nur belegt, dass
der Dienst antwortet, sondern dass er setzt und misst.

Mit freundlichen Grüßen
"""

PROFIL = {
    "absender": {
        "name": "Prüfstelle",
        "strasse": "Prüfweg 2",
        "plz": "12345",
        "ort": "Musterstadt",
    },
    "ruecksendeangabe": "Prüfstelle · Prüfweg 2 · 12345 Musterstadt",
    "briefkopf": {"zeilen": ["Prüfstelle", "Prüfweg 2 · 12345 Musterstadt"]},
    "fusszeile": [["Prüfstelle", "Prüfweg 2", "12345 Musterstadt"]],
    "gruss": "Mit freundlichen Grüßen",
    "unterzeichner": "Prüfstelle",
}


class Handschlagfehler(RuntimeError):
    pass


class Verbindung:
    """Newline-getrennte JSON-RPC-Nachrichten über stdin/stdout des Prozesses."""

    def __init__(self, befehl: list[str]) -> None:
        self.prozess = subprocess.Popen(
            befehl, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding="utf-8", bufsize=1,
        )
        self._id = 0

    def _senden(self, nachricht: dict) -> None:
        assert self.prozess.stdin is not None
        self.prozess.stdin.write(json.dumps(nachricht) + "\n")
        self.prozess.stdin.flush()

    def _lesen(self, erwartete_id: int) -> dict:
        """Bis zur Antwort mit dieser id lesen.

        Serverseitige Benachrichtigungen (Logmeldungen, Fortschritt) tragen
        keine id und dürfen dazwischenkommen; sie zu überspringen ist kein
        Nachlassen der Prüfung, sondern das Protokoll.
        """
        assert self.prozess.stdout is not None
        while True:
            zeile = self.prozess.stdout.readline()
            if not zeile:
                fehler = (self.prozess.stderr.read() if self.prozess.stderr else "").strip()
                raise Handschlagfehler(
                    "Der Server hat die Verbindung geschlossen, ohne zu antworten."
                    + (f"\n  stderr: {fehler[-800:]}" if fehler else ""))
            try:
                nachricht = json.loads(zeile)
            except json.JSONDecodeError:
                continue          # z. B. eine Startmeldung auf stdout
            if nachricht.get("id") == erwartete_id:
                return nachricht

    def rufe(self, methode: str, parameter: dict | None = None) -> dict:
        self._id += 1
        self._senden({"jsonrpc": "2.0", "id": self._id, "method": methode,
                      "params": parameter or {}})
        antwort = self._lesen(self._id)
        if "error" in antwort:
            raise Handschlagfehler(f"{methode}: {antwort['error']}")
        return antwort.get("result", {})

    def melde(self, methode: str) -> None:
        self._senden({"jsonrpc": "2.0", "method": methode, "params": {}})

    def schliessen(self) -> None:
        if self.prozess.stdin:
            self.prozess.stdin.close()
        try:
            self.prozess.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.prozess.kill()


def _text_der_antwort(ergebnis: dict) -> str:
    """Der Inhalt eines tools/call — als Text, wie ihn ein Client sieht."""
    if isinstance(ergebnis.get("structuredContent"), dict):
        return json.dumps(ergebnis["structuredContent"], ensure_ascii=False)
    teile = [t.get("text", "") for t in ergebnis.get("content", [])
             if isinstance(t, dict) and t.get("type") == "text"]
    return "\n".join(teile)


def handschlag(befehl: list[str], *, mit_render: bool = True) -> None:
    verbindung = Verbindung(befehl)
    try:
        ergebnis = verbindung.rufe("initialize", {
            "protocolVersion": PROTOKOLL,
            "capabilities": {},
            "clientInfo": {"name": "falzmarke-handschlag", "version": "1"},
        })
        name = (ergebnis.get("serverInfo") or {}).get("name", "?")
        print(f"OK    initialize — Server meldet sich als {name!r}")
        verbindung.melde("notifications/initialized")

        werkzeuge = [w.get("name") for w in verbindung.rufe("tools/list").get("tools", [])]
        fehlend = [w for w in ERWARTETE_WERKZEUGE if w not in werkzeuge]
        if fehlend:
            raise Handschlagfehler(
                "tools/list nennt nicht alle Werkzeuge.\n"
                f"  fehlt:    {', '.join(fehlend)}\n"
                f"  gemeldet: {', '.join(werkzeuge) or '(keines)'}")
        print(f"OK    tools/list — {len(werkzeuge)} Werkzeuge, alle erwarteten dabei: "
              f"{', '.join(werkzeuge)}")

        if not mit_render:
            return

        antwort = verbindung.rufe("tools/call", {
            "name": "brief_rendern",
            "arguments": {"brief": BRIEF, "profil": PROFIL, "als": "base64"},
        })
        if antwort.get("isError"):
            raise Handschlagfehler(f"brief_rendern meldet einen Fehler:\n  "
                                   f"{_text_der_antwort(antwort)[:800]}")
        text = _text_der_antwort(antwort)
        try:
            daten = json.loads(text)
        except json.JSONDecodeError as fehler:
            raise Handschlagfehler(
                f"brief_rendern antwortet nicht als JSON: {fehler}\n  {text[:400]}") from None

        roh = daten.get("pdf_base64") or daten.get("pdf") or ""
        if not roh:
            raise Handschlagfehler(
                "brief_rendern liefert kein PDF. Antwort:\n  "
                + json.dumps(daten, ensure_ascii=False)[:800])
        pdf = base64.b64decode(roh)
        if not pdf.startswith(b"%PDF-"):
            raise Handschlagfehler("Die Rückgabe beginnt nicht mit %PDF-.")
        print(f"OK    brief_rendern — {len(pdf)} Byte PDF aus dem Container")

        # Der Messbericht, an seinen eigenen Feldern gemessen — nicht an einer
        # Textsuche nach „FEHLER". Ein durchgefallenes Maß meldet `bestanden:
        # false` und schreibt das Wort nirgends hin; eine Textsuche bliebe
        # genau dann grün, wenn sie anschlagen müsste.
        bericht = daten.get("bericht") or {}
        pruefungen = bericht.get("pruefungen") or []
        if not pruefungen:
            raise Handschlagfehler(
                "Der Messbericht enthält keine einzige Prüfung. Ein leerer "
                "Bericht besteht jede Bedingung, die man an ihn stellt.")
        durchgefallen = [p for p in pruefungen if not p.get("bestanden")]
        if durchgefallen or not daten.get("bestanden") or not bericht.get("ok"):
            namen = ", ".join(p.get("name", "?") for p in durchgefallen) or "(keines benannt)"
            raise Handschlagfehler(
                f"Der Messbericht ist nicht bestanden: {namen}\n  "
                + str(daten.get("zusammenfassung", ""))[:400])
        print(f"OK    Messbericht — {len(pruefungen)} Prüfungen, alle bestanden: "
              + str(daten.get("zusammenfassung", "")).strip())
    finally:
        verbindung.schliessen()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ohne-render", action="store_true",
                        help="nur initialize und tools/list")
    parser.add_argument("befehl", nargs=argparse.REMAINDER,
                        help="hinter `--`: der Befehl, der den Server startet")
    args = parser.parse_args(argv)
    befehl = [a for a in args.befehl if a != "--"]
    if not befehl:
        parser.error("kein Befehl angegeben — erwartet: … -- docker run --rm -i IMAGE")
    try:
        handschlag(befehl, mit_render=not args.ohne_render)
    except Handschlagfehler as fehler:
        print(f"FEHL  {fehler}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
