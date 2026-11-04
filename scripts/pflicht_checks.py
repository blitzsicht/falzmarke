#!/usr/bin/env python3
"""Pflicht-Checks für das Ruleset `main` — aus den Workflow-Dateien, nicht aus einem Lauf.

Ein Check, der aus dem letzten CI-Lauf abgeleitet wird, kommt bei jedem Aufruf
anders heraus: Ein Job, der zum Zeitpunkt der Ableitung noch läuft, fehlt in
der Liste, ohne dass sich am Workflow etwas geändert hätte — genau das ist am
30.08.2026 passiert (Issue #196). Diese Datei liest stattdessen nur die
Workflow-Definition. Das Ergebnis hängt ausschließlich vom Dateiinhalt ab, nie
vom Zeitpunkt des Aufrufs oder vom Stand eines laufenden CI-Laufs.

Gelesen werden genau die Dateien in `STANDARD_WORKFLOWS`, seit #437 zwei. Ein
Job in einem dritten Workflow liefe zwar, landete aber nie im Ruleset und
verhinderte nichts. Wer einen Pflicht-Workflow ergänzt, trägt ihn dort ein.

Die übrigen Workflows im Verzeichnis werden seit #493 nur auf Namensgleichheit
gelesen: Ein Job dort mit dem Anzeigenamen eines Pflicht-Checks meldet einen
zweiten Check-Run gleichen Namens, und das Ruleset nimmt den jüngsten. Ein
grüner oder übersprungener Lauf des Nachbarn überdeckte dann ein rotes
Ergebnis des Pflicht-Checks, ohne dass jemand es sähe.

    python3 scripts/pflicht_checks.py                       # eine Zeile je Check
    python3 scripts/pflicht_checks.py --workflow pfad.yml    # andere Workflows (mehrfach)
    python3 scripts/pflicht_checks.py --nachbar pfad.yml     # statt der übrigen Dateien im Verzeichnis

Verwendet von scripts/repo-einstellungen.sh.
"""

from __future__ import annotations

import argparse
import itertools
import sys
from collections import Counter
from collections.abc import Iterable
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
WORKFLOWS = REPO / ".github" / "workflows"

#: Die Workflows, deren Jobs Pflicht-Checks sind. `ci.yml` prüft den Code und
#: startet nur bei neuem Code. `pr-angaben.yml` prüft, was am Pull Request steht
#: (Rumpf, Labels, Dateiliste), und startet darum auch bei `edited` und
#: `labeled` (#437). Beides in einer Datei hieße: jede korrigierte Beschreibung
#: startet die ganze Testmatrix, oder die teuren Jobs melden `skipped`, und ein
#: übersprungener Job gilt GitHub als erfüllt.
STANDARD_WORKFLOWS = (WORKFLOWS / "ci.yml", WORKFLOWS / "pr-angaben.yml")

#: Was GitHub für `pull_request` ohne `types:` einsetzt (Dokumentation „Events
#: that trigger workflows“, Abschnitt pull_request; an PR #432 bestätigt: nach
#: `gh pr edit` lief nichts neu). Ein Pflicht-Workflow muss mindestens bei diesen
#: starten: Ohne `synchronize` bekäme ein neuer Commit seinen Check nie, und
#: main wartete auf etwas, das nicht kommt.
VORGABE_TYPEN = ("opened", "synchronize", "reopened")


class Workflowfehler(ValueError):
    """Ein Pflicht-Workflow, aus dem sich keine verlässliche Liste ableiten lässt."""


#: Ein `pull_request`-Auslöser mit einem dieser Filter startet nicht bei jedem
#: PR. Ein PR außerhalb des Filters bekäme seine Checks nie, und main wartete auf
#: sie — dieselbe Falle wie ein fehlendes `synchronize` (Nachreview von #483).
FILTER = ("branches", "branches-ignore", "paths", "paths-ignore")


def ausloeser(daten: dict) -> dict[str, dict]:
    """Der `on:`-Block als Wörterbuch Ereignis → Einstellungen, in jeder Schreibweise.

    GitHub erlaubt `on: push`, `on: [push, pull_request]` und den Block; PyYAML
    liest den Schlüssel `on` nach YAML 1.1 obendrein als True.
    """
    block = daten["on"] if "on" in daten else daten.get(True)
    if isinstance(block, str):
        block = {block: None}
    elif isinstance(block, list):
        block = dict.fromkeys(block)
    if not isinstance(block, dict):
        return {}
    return {str(ereignis): (einstellungen or {}) for ereignis, einstellungen in block.items()}


def pull_request_typen(daten: dict) -> tuple[str, ...] | None:
    """Die Ereignisarten, bei denen der Workflow für einen Pull Request startet.

    `None`, wenn er bei `pull_request` gar nicht startet.
    """
    pull_request = ausloeser(daten).get("pull_request")
    if pull_request is None:
        return None
    typen = pull_request.get("types")
    if typen is None:
        return VORGABE_TYPEN
    return (typen,) if isinstance(typen, str) else tuple(typen)

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


def _matrix_include_ohne_achsen(job: dict) -> list[dict]:
    """Eine Matrix ohne eigene Achsen, die nur über `include` definiert ist —
    das Standard-Muster für heterogene Kombinationen, z. B.
    `include: [{os: ubuntu-latest, python: '3.11'}, ...]`. GitHub führt dafür
    einen eigenen Job je Eintrag aus, mit einem aus dessen Werten
    abgeleiteten Checknamen. Ohne diese Sonderbehandlung trüge `analysiere()`
    nur den nackten Jobnamen ein — einen Check, den GitHub nie meldet, weil
    es tatsächlich einen je Eintrag gibt (Issue #196)."""
    matrix = ((job.get("strategy") or {}).get("matrix")) or {}
    return [e for e in (matrix.get("include") or []) if isinstance(e, dict)]


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


def nachbarn_von(workflows: Iterable[Path], verzeichnis: Path = WORKFLOWS) -> tuple[Path, ...]:
    """Die übrigen Workflow-Dateien im Verzeichnis, ohne die Pflicht-Workflows selbst."""
    eigene = {Path(w).resolve() for w in workflows}
    return tuple(sorted(
        datei for muster in ("*.yml", "*.yaml") for datei in verzeichnis.glob(muster)
        if datei.resolve() not in eigene
    ))


def analysiere(workflows: Path | Iterable[Path] = STANDARD_WORKFLOWS,
               nachbarn: Iterable[Path] | None = None,
               ) -> tuple[list[str], list[str]]:
    """(Pflicht-Checks, wegen `if:` ausgeschlossene Jobs) — nur aus den Dateien.

    Wirft `Workflowfehler`, wenn ein Workflow nicht lesbar ist, nicht bei jedem
    Pull Request startet oder ein Checkname zweimal vorkommt. Zwei Jobs gleichen Namens
    melden zwei Check-Runs, und für das Ruleset zählt der jüngste: Ein grüner
    Lauf des einen überdeckte dann einen roten des anderen.

    `nachbarn` sind die Workflows, die keine Pflicht-Checks liefern, deren Jobs
    aber auch keinen Namen eines Pflicht-Checks tragen dürfen (#493). `None`
    heißt: alle übrigen Dateien im Verzeichnis `WORKFLOWS`. Tests mit Dateien
    unter `tmp_path` geben `nachbarn=()` an, sonst lesen sie das echte Verzeichnis.
    """
    if isinstance(workflows, Path):
        workflows = (workflows,)
    workflows = tuple(workflows)
    checks: list[str] = []
    ausgeschlossen: list[str] = []
    herkunft: dict[str, Path] = {}
    for workflow in workflows:
        c, a = _analysiere_einen(workflow)
        checks += c
        ausgeschlossen += a
        herkunft.update((name, workflow) for name in c)
    doppelt = sorted(name for name, n in Counter(checks).items() if n > 1)
    if doppelt:
        raise Workflowfehler("Checkname mehrfach vergeben: " + ", ".join(doppelt))
    kollisionen = [
        f"{name} in {herkunft[name].name} und {nachbar.name}"
        for nachbar in (nachbarn_von(workflows) if nachbarn is None else nachbarn)
        for name in nachbar_namen(nachbar) if name in herkunft
    ]
    if kollisionen:
        raise Workflowfehler("Checkname auch in einem Nachbar-Workflow: " + "; ".join(kollisionen))
    return checks, ausgeschlossen


def _lies(workflow: Path) -> dict:
    """Die Workflow-Datei als Wörterbuch, sonst `Workflowfehler`."""
    try:
        return yaml.safe_load(workflow.read_text(encoding="utf-8")) or {}
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as fehler:
        # Auch das ist der dritte Zustand: Bis zum Nachreview von #492 ging eine
        # fehlende oder kaputte Datei als Traceback durch `main()` und riss den
        # Wächter ab, obwohl beide `Workflowfehler` längst abfangen.
        grund = (str(fehler).splitlines() or [type(fehler).__name__])[0]
        raise Workflowfehler(f"{workflow.name} nicht lesbar: {grund}") from fehler


def nachbar_namen(workflow: Path) -> list[str]:
    """Alle Checknamen, die ein Nachbar-Workflow melden kann.

    Auch die seiner Jobs mit `if:`: Ein übersprungener Check-Run trägt denselben
    Namen und gilt dem Ruleset als erfüllt (#493).
    """
    return _checknamen(_lies(workflow), alle=True)[0]


def _analysiere_einen(workflow: Path) -> tuple[list[str], list[str]]:
    daten = _lies(workflow)
    typen = pull_request_typen(daten)
    if typen is None:
        raise Workflowfehler(f"{workflow.name} startet nicht bei pull_request: "
                             "seine Jobs kämen in keinem PR, das Ruleset wartete ewig")
    fehlend = [t for t in VORGABE_TYPEN if t not in typen]
    if fehlend:
        raise Workflowfehler(f"{workflow.name} startet nicht bei {', '.join(fehlend)}: "
                             "ein PR bekäme seine Checks dann nicht für jeden Commit")
    filter_schluessel = [f for f in FILTER if f in ausloeser(daten).get("pull_request", {})]
    if filter_schluessel:
        raise Workflowfehler(f"{workflow.name} startet bei pull_request nur mit "
                             f"{', '.join(filter_schluessel)}: ein PR außerhalb des Filters "
                             "bekäme seine Checks nie")
    return _checknamen(daten)


def _checknamen(daten: dict, *, alle: bool = False) -> tuple[list[str], list[str]]:
    """(Checknamen, wegen `if:` ausgeschlossene Job-IDs) eines gelesenen Workflows.

    Mit `alle` zählt jeder Job, auch einer, der nur auf main läuft.
    """
    checks: list[str] = []
    ausgeschlossen: list[str] = []
    for job_id, job in (daten.get("jobs") or {}).items():
        job = job or {}
        if not alle and _laeuft_nur_auf_main(job):
            ausgeschlossen.append(job_id)
            continue
        anzeige = _anzeigename(job_id, job)
        achsen = _matrix_achsen(job)
        if not achsen:
            include_kombis = _matrix_include_ohne_achsen(job)
            if not include_kombis:
                checks.append(anzeige)
                continue
            for kombi in include_kombis:
                anzeige_werte = ", ".join(str(w) for w in kombi.values())
                checks.append(f"{anzeige} ({anzeige_werte})")
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


def pflicht_checks(workflows: Path | Iterable[Path] = STANDARD_WORKFLOWS,
                   nachbarn: Iterable[Path] | None = None) -> list[str]:
    return analysiere(workflows, nachbarn)[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflow", type=Path, action="append",
                        help="statt der Standard-Workflows, mehrfach möglich")
    parser.add_argument("--nachbar", type=Path, action="append",
                        help="Workflows, deren Jobs keinen Namen eines Pflicht-Checks tragen "
                             "dürfen; ohne Angabe alle übrigen Dateien unter .github/workflows")
    args = parser.parse_args()
    try:
        checks, ausgeschlossen = analysiere(args.workflow or STANDARD_WORKFLOWS, args.nachbar)
    except Workflowfehler as fehler:
        # Eine Meldung statt eines Tracebacks: Das Skript wird aus
        # repo-einstellungen.sh gerufen, und dort zählt der Exit-Code.
        print(f"FEHLER  {fehler}", file=sys.stderr)
        return 1
    for job_id in ausgeschlossen:
        print(f"  übersprungen (läuft nur auf main): {job_id}", file=sys.stderr)
    for check in checks:
        print(check)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
