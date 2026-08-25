#!/usr/bin/env python3
"""Schreibt echte Messwerte fuer den Erklaerfilm.

Der Film zeigt in der Szene „Pruefen" Zeilen aus dem Messbericht. Sie werden
nicht abgetippt, sondern hier aus einem wirklichen Lauf gezogen: rendern,
`verify --json` lesen, die gezeigten Pruefungen herausschreiben.

    python3 scripts/bericht.py            # schreibt die Datei neu
    python3 scripts/bericht.py --pruefen  # meldet nur, ob sie zum Lauf passt

Wer eine Zeile im Film sehen will, die es im Bericht nicht gibt, faellt hier auf.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CLI = REPO / "skill" / "scripts" / "falzmarke.py"
BRIEF = REPO / "examples" / "brief-mahnung.md"
ZIEL = REPO / "docs" / "marke" / "video" / "erklaerfilm" / "src" / "bericht.json"

# Die Pruefungen, die der Film zeigt. Namen wie in geometrie.py — steht einer
# davon nicht mehr im Bericht, bricht dieses Skript ab, statt still eine
# Behauptung ins Video zu lassen.
GEZEIGT = [
    "Falzmarke 1, y",
    "Falzmarke 2, y",
    "Lochmarke, y",
    "Anschrift, x-links",
    "Infoblock, x-links",
    "Abstand Betreff → Anrede (2 Leerzeilen)",
]


def messwerte() -> dict:
    with tempfile.TemporaryDirectory(prefix="falzmarke-bericht-") as tmp:
        pdf = Path(tmp) / "mahnung.pdf"
        bau = subprocess.run(
            [sys.executable, str(CLI), "render", str(BRIEF), "-o", str(pdf)],
            capture_output=True, text=True, encoding="utf-8",
        )
        if bau.returncode != 0:
            raise SystemExit(f"Render scheiterte:\n{bau.stderr}")
        lauf = subprocess.run(
            [sys.executable, str(CLI), "verify", str(pdf), "--json"],
            capture_output=True, text=True, encoding="utf-8",
        )
        if lauf.returncode != 0:
            raise SystemExit(f"verify scheiterte:\n{lauf.stderr}")
        roh = json.loads(lauf.stdout)

    nach_name = {p["name"]: p for p in roh["pruefungen"]}
    fehlend = [n for n in GEZEIGT if n not in nach_name]
    if fehlend:
        raise SystemExit(
            "Diese Pruefungen sollen im Film erscheinen, stehen aber nicht mehr\n"
            "im Bericht:\n  " + "\n  ".join(fehlend) +
            "\n\nEntweder GEZEIGT in scripts/bericht.py anpassen oder die Szene aendern."
        )

    return {
        "hinweis": "Erzeugt aus einem echten verify-Lauf — nicht von Hand aendern. "
                   "Neu bauen: python3 scripts/bericht.py",
        "brief": BRIEF.name,
        "ok": roh["ok"],
        "gesamt": len(roh["pruefungen"]),
        "bestanden": sum(1 for p in roh["pruefungen"] if p["bestanden"]),
        "zeilen": [
            {
                "name": nach_name[n]["name"],
                "soll": str(nach_name[n]["soll"]),
                "ist": str(nach_name[n]["ist"]),
                "bestanden": nach_name[n]["bestanden"],
            }
            for n in GEZEIGT
        ],
    }


def main() -> int:
    neu = json.dumps(messwerte(), ensure_ascii=False, indent=2) + "\n"
    if "--pruefen" in sys.argv:
        alt = ZIEL.read_text(encoding="utf-8") if ZIEL.exists() else None
        if alt != neu:
            print(f"VERALTET  {ZIEL.relative_to(REPO)}", file=sys.stderr)
            print("Neu bauen: python3 scripts/bericht.py", file=sys.stderr)
            return 1
        print("OK  Messwerte im Film stammen aus dem aktuellen Lauf")
        return 0
    ZIEL.parent.mkdir(parents=True, exist_ok=True)
    ZIEL.write_text(neu, encoding="utf-8")
    print(f"OK  geschrieben: {ZIEL.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
