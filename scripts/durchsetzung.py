#!/usr/bin/env python3
"""Der Sollwert der Ruleset-Durchsetzung — die eine Stelle (Issue #212).

Bis zum 01.09.2026 stand dieser Wert zweimal im Repository: als
`DURCHSETZUNG="active"` in `repo-einstellungen.sh`, wo er gesetzt wird, und
als `SOLL_ENFORCEMENT = "active"` in `repo_pruefung.py`, wogegen der Wächter
prüft. Sie waren gleich; nichts hielt sie gleich. Eine Sabotage am ersten Wert
blieb stumm — `--pruefen` macht in `repo-einstellungen.sh` ein `exec` auf den
Prüfer, die Zeile wird dabei nie erreicht.

Dieselbe Fehlerklasse wie #196, #199 und #201 — diesmal innerhalb des
Werkzeugs, das gegen genau diese Klasse gebaut wurde. Homepage und
Pflicht-Checks machen es seit jeher richtig: ein Modul je Sollwert, aus dem
sowohl der Setz-Lauf als auch der Wächter liest. Das hier ist das dritte.

    python3 scripts/durchsetzung.py           # der geltende Sollwert
    python3 scripts/durchsetzung.py --grund   # dazu, warum er gilt

Verwendet von scripts/repo-einstellungen.sh und scripts/repo_pruefung.py.
"""

from __future__ import annotations

import argparse
import os
from typing import Mapping

#: Der Normalfall seit #201. Vorher war "evaluate" der Default, weil noch offen
#: war, ob die Regeln zum Ablauf passen. Sie passen — und ein gewöhnlicher Lauf
#: ohne Umgebungsvariablen hätte main sonst still entwaffnet.
STANDARD = "active"

#: Der begründungspflichtige Sonderfall: main nur beobachtend fahren.
BEOBACHTEND = "evaluate"

#: Die Variable, die #201 eigens geschaffen hat, um den Sonderfall zu wählen.
UMGEBUNGSVARIABLE = "FALZMARKE_RULESET_EVALUATE"


def beobachtend_gewuenscht(umgebung: Mapping[str, str] | None = None) -> bool:
    """Hat jemand den Sonderfall ausdrücklich gewählt?

    `umgebung` ist injizierbar, damit der Test nicht `os.environ` verbiegen
    muss — dieselbe Machart wie `pruefen` in homepage.py und `api` in
    repo_pruefung.py.
    """
    quelle = os.environ if umgebung is None else umgebung
    return quelle.get(UMGEBUNGSVARIABLE, "0") == "1"


#: Das einzige Ruleset, das der Sonderfall betrifft. `release-tags` schützt
#: veröffentlichte Tags vor Löschung und Überschreiben; es beobachtend zu
#: fahren hiesse, den Schutz aufzugeben, ohne dass jemand danach gefragt hat.
#: `repo-einstellungen.sh` setzt es deshalb seit jeher fest auf STANDARD — und
#: der Wächter darf nichts anderes erwarten, sonst meldet er eine Abweichung
#: gegen einen Wert, den der Setz-Lauf nie schreibt.
BEOBACHTBARES_RULESET = "main"


def soll(ruleset: str = BEOBACHTBARES_RULESET,
         umgebung: Mapping[str, str] | None = None) -> str:
    """Der Wert, den der Setz-Lauf schreibt und der Wächter erwartet.

    Beide fragen hier — das ist der ganze Zweck des Moduls. Dass der Wächter
    den Sonderfall mitträgt, ist Absicht: Stufte jemand main bewusst herab und
    verlangte der Wächter weiter `active`, meldete er von da an dauerhaft eine
    Abweichung für einen Zustand, den der Maintainer gewählt hat. Ein Wächter,
    der grundlos anschlägt, wird abgeschaltet — dieselbe Falle wie #210.

    Stillschweigend darf das nicht geschehen. `grund()` liefert den Satz, den
    `repo_pruefung.py` dann ausgibt: Eine Ausnahme, die niemand sieht, ist der
    stille Ausfall, gegen den dieses ganze Vorhaben gerichtet ist.

    `ruleset` ist kein Beiwerk: Der Sonderfall gilt nur für main. Ohne diese
    Unterscheidung erwartete der Wächter bei gesetzter Variable auch von
    `release-tags` ein `evaluate` — und meldete eine Abweichung, die der
    Setz-Lauf gar nicht herstellen kann.
    """
    if ruleset != BEOBACHTBARES_RULESET:
        return STANDARD
    return BEOBACHTEND if beobachtend_gewuenscht(umgebung) else STANDARD


def grund(umgebung: Mapping[str, str] | None = None) -> str | None:
    """Warum der Sollwert vom Normalfall abweicht — sonst None."""
    if not beobachtend_gewuenscht(umgebung):
        return None
    return (f"{UMGEBUNGSVARIABLE}=1 gesetzt — für Ruleset "
            f"{BEOBACHTBARES_RULESET!r} ist der Sollwert deshalb {BEOBACHTEND!r} statt "
            f"{STANDARD!r}. Andere Rulesets bleiben bei {STANDARD!r}; ohne die "
            f"Variable gilt wieder überall {STANDARD!r}.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ruleset", default=BEOBACHTBARES_RULESET,
                        help=f"für welches Ruleset (Vorgabe: {BEOBACHTBARES_RULESET})")
    parser.add_argument("--standard", action="store_true",
                        help="den strengen Wert ausgeben, ohne jeden Sonderfall")
    parser.add_argument("--grund", action="store_true",
                        help="zusätzlich die Begründung auf stderr, falls der Sonderfall gilt")
    args = parser.parse_args()
    if args.standard:
        print(STANDARD)
        return 0
    if args.grund and (text := grund()):
        import sys
        print(f"  {text}", file=sys.stderr)
    print(soll(args.ruleset))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
