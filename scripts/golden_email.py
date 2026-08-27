#!/usr/bin/env python3
"""Erneuert die Golden-Dateien der Mail-Beispiele.

Ein Golden ist die Byte-für-Byte festgehaltene Ausgabe. Es faellt auf, wenn
sich an der `.eml` etwas aendert, das niemand angesagt hat — eine
Kopfzeilenreihenfolge, eine Kodierung, ein Trennstring. Damit das ueberhaupt
moeglich ist, muss die Ausgabe deterministisch sein: die Trennstrings kommen
aus dem Quellenhash (eml.py) und `Date` nur aus `SOURCE_DATE_EPOCH`.

    python3 scripts/golden_email.py            # schreibt die Goldens neu
    python3 scripts/golden_email.py --pruefen  # meldet nur Abweichungen

Nach einer *gewollten* Aenderung am Emitter: einmal ohne Schalter laufen
lassen und den Diff der Goldens im PR mitlesen. Er ist der eigentliche
Befund — nicht laestige Nacharbeit.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "skill"))

#: Fester Zeitpunkt fuer `Date`. Derselbe Wert wie in tests/test_eml.py — zwei
#: verschiedene Zeitpunkte in einem Repo waeren zwei Wahrheiten.
EPOCH = "1788134400"

QUELLEN = sorted((REPO / "examples" / "email").glob("*.md"))
ZIEL = REPO / "tests" / "golden" / "email"


def erzeuge(quelle: Path) -> bytes:
    """Die `.eml` zu einem Beispiel, als Bytes."""
    from falzmarke import cli

    alt = os.environ.get("SOURCE_DATE_EPOCH")
    os.environ["SOURCE_DATE_EPOCH"] = EPOCH
    try:
        arbeit = Path(tempfile.mkdtemp(prefix="falzmarke-golden-"))
        try:
            eml, _ = cli.setze_email(quelle, arbeit / quelle.stem)
            return eml.read_bytes()
        finally:
            shutil.rmtree(arbeit, ignore_errors=True)
    finally:
        if alt is None:
            del os.environ["SOURCE_DATE_EPOCH"]
        else:
            os.environ["SOURCE_DATE_EPOCH"] = alt


def main(argv: list[str]) -> int:
    if not QUELLEN:
        print("keine Beispiele unter examples/email/ — nichts zu tun", file=sys.stderr)
        return 1

    nur_pruefen = "--pruefen" in argv
    ZIEL.mkdir(parents=True, exist_ok=True)
    abweichungen = 0

    for quelle in QUELLEN:
        golden = ZIEL / f"{quelle.stem}.eml"
        neu = erzeuge(quelle)
        alt = golden.read_bytes() if golden.exists() else None
        if alt == neu:
            print(f"gleich     {golden.relative_to(REPO)}")
            continue
        abweichungen += 1
        if nur_pruefen:
            grund = "fehlt" if alt is None else "weicht ab"
            print(f"{grund:10} {golden.relative_to(REPO)}", file=sys.stderr)
        else:
            golden.write_bytes(neu)
            print(f"{'neu' if alt is None else 'erneuert':10} {golden.relative_to(REPO)}")

    if nur_pruefen and abweichungen:
        print(f"\n{abweichungen} Golden-Datei(en) nicht auf Stand — "
              "`python3 scripts/golden_email.py` laeuft dagegen.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
