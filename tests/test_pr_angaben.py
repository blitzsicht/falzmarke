"""Die Checks auf die Angaben am Pull Request starten bei jeder Änderung, die sie prüfen (#437).

Bis #437 standen `Changelog-Eintrag` und `Closing-Keyword` in ci.yml und
starteten nur bei neuem Code. Wer den Rumpf korrigierte oder das Label setzte,
behob den Befund, und der rote Lauf blieb stehen. Jetzt haben sie einen eigenen
Workflow, `.github/workflows/pr-angaben.yml`, mit eigenem Trigger.

Was diese Datei festhält: Jede Angabe, die ein Job per `gh pr view --json` liest,
hat ein Ereignis im Trigger, das sie ändert. Kein Job lässt sich überspringen.
Und beide Checks landen weiter im Ruleset, unter demselben Namen.
"""

from __future__ import annotations

import re
import sys

import yaml

from conftest import REPO

sys.path.insert(0, str(REPO / "scripts"))

import pflicht_checks                                            # noqa: E402

PR_ANGABEN = REPO / ".github" / "workflows" / "pr-angaben.yml"
CI = REPO / ".github" / "workflows" / "ci.yml"

#: Je Feld von `gh pr view --json` die Ereignisse, bei denen es sich ändert.
#: Eine leere Menge heißt: Das Feld ändert sich am offenen PR nicht.
#:
#: `author` steht fest, sobald der PR offen ist. `files` ändert sich nur mit
#: einem Commit (`synchronize`). Ein Feld, das hier fehlt, meldet der Test,
#: statt es stillschweigend für unveränderlich zu halten.
AUSLOESER = {
    "files": {"synchronize"},
    "body": {"edited"},
    "labels": {"labeled", "unlabeled"},
    "author": set(),
}

#: Die Pflicht-Checks, die in diesem Workflow stehen, unter ihrem `name:`.
CHECKS = ["Changelog-Eintrag", "Closing-Keyword"]

_JSON_FELDER = re.compile(r"gh pr view\b[^\n]*?(?:\\\n[^\n]*?)*--json\s+([a-z_,]+)")


def _lade(pfad=None) -> dict:
    return yaml.safe_load((pfad or PR_ANGABEN).read_text(encoding="utf-8"))


def gelesene_felder(job: dict) -> set[str]:
    """Die Felder, die die Schritte eines Jobs per `gh pr view --json` holen."""
    felder: set[str] = set()
    for schritt in job.get("steps") or []:
        for treffer in _JSON_FELDER.findall(schritt.get("run") or ""):
            felder |= set(treffer.split(","))
    return felder


def fehlende_ausloeser(daten: dict) -> list[str]:
    """Je Job und Feld die Ereignisse, die das Feld ändern und nicht im Trigger stehen."""
    typen = set(pflicht_checks.pull_request_typen(daten) or ())
    befunde = []
    for job_id, job in daten["jobs"].items():
        felder = gelesene_felder(job)
        assert felder, f"{job_id}: liest keine Angabe per gh pr view --json — Muster veraltet?"
        for feld in sorted(felder):
            assert feld in AUSLOESER, (
                f"{job_id} liest „{feld}“, AUSLOESER kennt das Feld nicht: nachtragen, "
                "bei welchem Ereignis es sich ändert")
            for typ in sorted(AUSLOESER[feld] - typen):
                befunde.append(f"{job_id}: {feld} ändert sich bei „{typ}“, der Trigger fehlt")
    return befunde


def ueberspringbares(daten: dict) -> list[str]:
    """Was einen Job dieses Workflows `skipped` melden lassen könnte."""
    ausloeser = daten["on"] if "on" in daten else daten[True]
    befunde = [f"Auslöser „{a}“ neben pull_request" for a in ausloeser if a != "pull_request"]
    befunde += [f"{job_id} trägt if: {job['if']}"
                for job_id, job in daten["jobs"].items() if "if" in job]
    return befunde


def test_jede_gelesene_angabe_hat_ihren_ausloeser():
    assert fehlende_ausloeser(_lade()) == []


def test_kein_job_laesst_sich_ueberspringen():
    """Ein übersprungener Job gilt GitHub als erfüllt, und der jüngste Check-Run
    je Name zählt. Ein `workflow_dispatch` oder ein `if:` hier würde ein rotes
    Gate durch ein grünes `skipped` ersetzen (Kopfkommentar in ci.yml)."""
    assert ueberspringbares(_lade()) == []


def test_beide_checks_stehen_hier_und_im_ruleset():
    """Ein Prüfer ohne Aufrufer prüft nichts, und ein Job, den
    `scripts/pflicht_checks.py` nicht liest, landet nie im Ruleset."""
    daten = _lade()
    assert sorted(job["name"] for job in daten["jobs"].values()) == CHECKS
    skripte = yaml.dump(daten["jobs"])
    assert "scripts/changelog_pflicht.py" in skripte
    assert "scripts/closing_keyword.py" in skripte
    assert PR_ANGABEN in pflicht_checks.STANDARD_WORKFLOWS
    assert pflicht_checks.pflicht_checks(PR_ANGABEN) == CHECKS
    alle = pflicht_checks.pflicht_checks()
    assert set(CHECKS) <= set(alle)


def test_ci_yml_startet_weiter_nur_bei_neuem_code():
    """Die Gegenseite: Die teure Matrix startet nicht bei einer Textänderung.

    Das war der Grund für den eigenen Workflow (#437, Weg 1 verworfen).
    """
    typen = pflicht_checks.pull_request_typen(_lade(CI))
    assert set(typen) == set(pflicht_checks.VORGABE_TYPEN), typen
