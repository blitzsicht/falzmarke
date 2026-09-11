#!/usr/bin/env python3
"""Die Themen (Topics) des Repositories — eine Zeile je Eintrag.

Warum eine eigene Datei und keine Schleife im Setz-Skript: Bis heute stand die
Liste als Aufzählung in `scripts/repo-einstellungen.sh` und nannte zehn Themen,
auf dem Repository lagen fünfzehn. Aufgefallen ist das nie, weil `gh repo edit
--add-topic` nur hinzufügt: Ein Thema, das im Skript fehlt, bleibt trotzdem
stehen, und ein Thema, das im Skript steht, aber nie gesetzt wurde, fällt
ebenfalls nicht auf. Die Themen waren damit der einzige Repo-Sollwert ohne
Wächter — Homepage, Ruleset-Durchsetzung und Pflicht-Check-Liste sind alle drei
schon abgedriftet (#196, #199, #201).

Jetzt lesen beide Seiten dieselbe Liste: `repo-einstellungen.sh` setzt sie,
`repo_pruefung.py` vergleicht gegen sie. Zwei Kopien wären zwei Fassungen —
dieselbe Begründung, aus der `RULESET_NAMEN` in `repo_pruefung.py` nur noch an
einer Stelle steht.

    python3 scripts/topics.py        # eine Zeile je Thema

Verwendet von scripts/repo-einstellungen.sh und scripts/repo_pruefung.py.
"""

from __future__ import annotations

import sys

#: GitHub nimmt höchstens 20 Themen je Repository an. Das 21. wird still
#: verworfen — kein Fehler, keine Meldung, das Thema ist einfach nicht da.
#: `tests/test_topics.py` hält die Liste darunter, damit ein neuer Eintrag
#: nicht einen alten unbemerkt hinauswirft.
HOECHSTZAHL = 20

#: Die Themen in Gruppen, damit ein neuer Eintrag eine Stelle hat.
#:
#: `mcp`, `mcp-server` und `model-context-protocol` sind seit #237 dabei: Das
#: Paket bringt einen MCP-Server über stdio mit (`falzmarke mcp`,
#: `skill/falzmarke/dienst.py`), aber kein Verzeichnis fand ihn — gemessen am
#: 03.09. und noch einmal am 07.09.2026 enthielten die fünfzehn Themen keines
#: der drei. Alle drei Schreibweisen, weil die Verzeichnisse verschieden
#: suchen und ein Thema nichts kostet.
TOPICS = (
    # Das Werkzeug selbst
    "falzmarke",
    "din5008",
    "din-5008",
    "geschaeftsbrief",
    "brief",
    "normbrief",
    "letter",
    # Technik und Ausgabeformate
    "typst",
    "pdf",
    "pdfa",
    "pdfua",
    "markdown",
    # Wie es benutzt wird
    "claude-skill",
    "agent-skills",
    "mcp",
    "mcp-server",
    "model-context-protocol",
    # Sprache des Gegenstands
    "german",
)


def main() -> int:
    if len(TOPICS) > HOECHSTZAHL:
        print(f"FEHLER: {len(TOPICS)} Themen, GitHub nimmt höchstens "
              f"{HOECHSTZAHL} — ein Eintrag ginge still verloren.", file=sys.stderr)
        return 1
    if len(set(TOPICS)) != len(TOPICS):
        doppelt = sorted({t for t in TOPICS if TOPICS.count(t) > 1})
        print(f"FEHLER: doppelte Themen: {', '.join(doppelt)}", file=sys.stderr)
        return 1
    for thema in TOPICS:
        print(thema)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
