#!/usr/bin/env python3
"""Pflicht-Checks für das Ruleset `main` — aus .github/workflows/ci.yml, nicht aus einem Lauf.

Ein Check, der aus dem letzten CI-Lauf abgeleitet wird, kommt bei jedem Aufruf
anders heraus: Ein Job, der zum Zeitpunkt der Ableitung noch läuft, fehlt in
der Liste, ohne dass sich am Workflow etwas geändert hätte — genau das ist am
30.08.2026 passiert (Issue #196). Diese Datei liest stattdessen nur die
Workflow-Definition. Das Ergebnis hängt ausschließlich vom Dateiinhalt ab, nie
vom Zeitpunkt des Aufrufs oder vom Stand eines laufenden CI-Laufs.

    python3 scripts/pflicht_checks.py                       # eine Zeile je Check
    python3 scripts/pflicht_checks.py --workflow pfad.yml    # anderer Workflow

Verwendet von scripts/repo-einstellungen.sh.
"""

from __future__ import annotations

import argparse
import itertools
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
STANDARD_WORKFLOW = REPO / ".github" / "workflows" / "ci.yml"

# Ein Job mit einer dieser Bedingungen läuft bei einem Pull Request nie — als
# Pflicht-Check würde er jeden PR unbegrenzt warten lassen. Das ist der
# berechtigte Teil der alten, laufbasierten Logik und bleibt erhalten.
NUR_MAIN_MARKER = ("refs/heads/main", "event_name == 'push'")


def _laeuft_nur_auf_main(job: dict) -> bool:
    bedingung = str(job.get("if", ""))
    return any(marker in bedingung for marker in NUR_MAIN_MARKER)


def _anzeigename(job_id: str, job: dict) -> str:
    """Der Name, unter dem der Check im Ruleset erscheinen muss.

    Ein Job mit `name:` erscheint in der Check-Liste unter genau diesem Namen
    — `pdf-konformitaet` z. B. als "PDF-Konformität (veraPDF, fremdes
    Werkzeug)". Wer stattdessen den Jobschlüssel einträgt, verlangt einen
    Check, den GitHub nie meldet, und sperrt main dauerhaft.
    """
    return job.get("name") or job_id


def _matrix_achsen(job: dict) -> dict[str, list]:
    matrix = ((job.get("strategy") or {}).get("matrix")) or {}
    return {
        achse: werte for achse, werte in matrix.items()
        if achse not in ("include", "exclude") and isinstance(werte, list)
    }


def _matrix_ausschluesse(job: dict) -> list[dict]:
    matrix = ((job.get("strategy") or {}).get("matrix")) or {}
    return [e for e in (matrix.get("exclude") or []) if isinstance(e, dict)]


def _durch_exclude_ausgeschlossen(kombi: dict, ausschluesse: list[dict]) -> bool:
    """GitHub überspringt eine Kombination, sobald ein `exclude`-Eintrag in
    allen seinen Achsen mit ihr übereinstimmt — er muss nicht jede Achse der
    Matrix nennen. Ohne diese Prüfung landet eine Kombination, die GitHub nie
    ausführt, als Pflicht-Check im Ruleset und main wartet auf einen Check,
    den es nie geben wird."""
    return any(
        all(kombi.get(achse) == wert for achse, wert in ausschluss.items())
        for ausschluss in ausschluesse
    )


def analysiere(workflow: Path = STANDARD_WORKFLOW) -> tuple[list[str], list[str]]:
    """(Pflicht-Checks, wegen `if:` ausgeschlossene Jobs) — nur aus der Datei."""
    daten = yaml.safe_load(workflow.read_text(encoding="utf-8")) or {}
    checks: list[str] = []
    ausgeschlossen: list[str] = []
    for job_id, job in (daten.get("jobs") or {}).items():
        job = job or {}
        if _laeuft_nur_auf_main(job):
            ausgeschlossen.append(job_id)
            continue
        anzeige = _anzeigename(job_id, job)
        achsen = _matrix_achsen(job)
        if not achsen:
            checks.append(anzeige)
            continue
        schluessel = list(achsen.keys())
        ausschluesse = _matrix_ausschluesse(job)
        for werte in itertools.product(*(achsen[k] for k in schluessel)):
            kombi = dict(zip(schluessel, werte))
            if _durch_exclude_ausgeschlossen(kombi, ausschluesse):
                continue
            anzeige_werte = ", ".join(str(w) for w in werte)
            checks.append(f"{anzeige} ({anzeige_werte})")
    return checks, ausgeschlossen


def pflicht_checks(workflow: Path = STANDARD_WORKFLOW) -> list[str]:
    return analysiere(workflow)[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflow", type=Path, default=STANDARD_WORKFLOW)
    args = parser.parse_args()
    checks, ausgeschlossen = analysiere(args.workflow)
    for job_id in ausgeschlossen:
        print(f"  übersprungen (läuft nur auf main): {job_id}", file=sys.stderr)
    for check in checks:
        print(check)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
