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
# Bewusst quer ueber den Brief gestreut, nicht dreimal dieselbe Zone: Von den
# rund 30 Pruefungen betreffen nur sechs die Falz- und Lochmarken. Der Name des
# Werkzeugs legt nahe, es messe nur die Marke am Rand — gemessen wird das ganze
# Blatt, und genau das soll im Bild stehen.
GEZEIGT = [
    "Anschrift, erste Zeile y",
    "Infoblock, x-links",
    "Betreff, y-Oberkante",
    "Abstand Betreff → Anrede (2 Leerzeilen)",
    "Textblock, x-rechts",
    "Falzmarke 1, y",
]

# Die Zonen, die im Film am Blatt markiert werden. Werte in Millimetern, alle aus
# demselben Lauf — nichts hier ist geschaetzt oder aus der Norm abgetippt.
ZONEN = {
    "ruecksendeangabe": ["Rücksendeangabe, y-Oberkante", "Rücksendeangabe, x"],
    "anschrift": ["Anschrift, x-links", "Anschrift, erste Zeile y",
                  "Anschrift, letzte Zeile Unterkante"],
    "infoblock": ["Infoblock, x-links", "Infoblock, x-rechts", "Infoblock, y-Oberkante"],
    "betreff": ["Betreff, x-links", "Betreff, y-Oberkante"],
    "textblock": ["Textblock, x-links", "Textblock, x-rechts"],
    "marken": ["Falzmarke 1, y", "Lochmarke, y", "Falzmarke 2, y"],
}


def brieftext() -> dict:
    """Empfaenger, Betreff und Anrede aus dem Frontmatter des Musterbriefs.

    Die Szene, die zeigt, wie derselbe Brief in .txt, .docx und .pdf jedes Mal
    anders aussieht, braucht einen Brieftext. Der wird nicht in die Szene
    getippt: Aendert sich examples/brief-mahnung.md, aendert sich das Bild mit.
    Dasselbe Prinzip wie bei den Messzeilen.
    """
    import yaml

    roh = BRIEF.read_text(encoding="utf-8")
    if not roh.startswith("---"):
        raise SystemExit(f"{BRIEF.name} hat kein Frontmatter")
    kopf = yaml.safe_load(roh.split("---", 2)[1])
    return {
        "empfaenger": kopf["empfaenger"],
        "betreff": kopf["betreff"],
        "anrede": kopf["anrede"],
    }


def _zahl(wert) -> float:
    """Aus '62.69' oder '≥ 62.7' die Zahl. Der Bericht schreibt Sollwerte auch
    mit Vergleichszeichen; fuer die Zeichnung zaehlt der gemessene Ist-Wert."""
    import re

    treffer = re.search(r"-?\d+(?:[.,]\d+)?", str(wert))
    if not treffer:
        raise SystemExit(f"Kein Zahlenwert in {wert!r}")
    return float(treffer.group(0).replace(",", "."))


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
    verlangt = list(GEZEIGT) + [p for gruppe in ZONEN.values() for p in gruppe]
    fehlend = [n for n in dict.fromkeys(verlangt) if n not in nach_name]
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
        "brieftext": brieftext(),
        "ok": roh["ok"],
        "gesamt": len(roh["pruefungen"]),
        "bestanden": sum(1 for p in roh["pruefungen"] if p["bestanden"]),
        "zonen": {
            name: [_zahl(nach_name[p]["ist"]) for p in pruefungen if p in nach_name]
            for name, pruefungen in ZONEN.items()
        },
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
