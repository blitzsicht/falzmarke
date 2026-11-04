"""Die Pflicht-Checks des Rulesets stammen aus den Workflow-Dateien, nicht aus einem Lauf.

WARUM ES DAS GIBT

Bis zum 30.08.2026 leitete `scripts/repo-einstellungen.sh` die Status-Checks
des Rulesets `main` aus dem letzten CI-Lauf ab (`gh run list` + `gh api
.../jobs`, nur Jobs mit `conclusion=="success"`). Am selben Tag lief die CI auf
main noch, als das Ruleset scharf gestellt wurde: `frischklon` (`needs:
tests`) war noch nicht fertig, fiel aus der Liste, und das Ruleset verlor
einen Pflicht-Check, den es vorher hatte. Welche Checks am Ende im Ruleset
stehen, hing damit vom Zeitpunkt des Aufrufs ab statt vom Workflow selbst
(Issue #196).

`scripts/pflicht_checks.py` ersetzt das: Es liest nur die Dateien in
`STANDARD_WORKFLOWS`, `ci.yml` und seit #437 `pr-angaben.yml`. Diese Tests halten fest, dass die Liste ausschließlich vom
Dateiinhalt abhängt, dass der berechtigte Teil der alten Logik (Jobs, die nur
auf main laufen, gehören nicht in die PR-Pflicht-Checks) erhalten bleibt, und
dass der *angezeigte* Name verwendet wird — nicht der Jobschlüssel, der bei
`pdf-konformitaet` einen für immer blockierten Branch bedeutet hätte.
"""

from __future__ import annotations

import sys
import textwrap

import pytest
import yaml

from conftest import REPO

sys.path.insert(0, str(REPO / "scripts"))

import pflicht_checks                                            # noqa: E402

CI = REPO / ".github" / "workflows" / "ci.yml"
PR_ANGABEN = REPO / ".github" / "workflows" / "pr-angaben.yml"
SKRIPT = REPO / "scripts" / "repo-einstellungen.sh"

# Die Pflicht-Checks des Rulesets `main`. Der Job `tests` hat eine Matrix mit
# drei Betriebssystemen, also drei Checks; die übrigen Jobs haben keine Matrix
# und ergeben je einen.
#
# Am 30.08.2026 waren es sechs, von Hand gesetzt (Issue #196, Zwischenstand).
# Wer hier einen Job ergänzt, ergänzt auch diese Liste und fährt danach
# `bash scripts/repo-einstellungen.sh` — sonst verlangt das Ruleset weiter die
# alte Menge, und der neue Check läuft, ohne etwas zu verhindern.
ERWARTET = [
    "tests (ubuntu-latest)",
    "tests (macos-latest)",
    "tests (windows-latest)",
    "frischklon",
    "skill-paket",
    # Seit Issue #237: Das Dockerfile, das die MCP-Verzeichnisse bauen, wird
    # bei jedem Push wirklich gebaut und der Dienst darin angesprochen — sonst
    # fiele ein Fehler darin erst dem Verzeichnis auf. Die Reihenfolge dieser
    # Liste folgt ci.yml, nicht dem Datum der Aufnahme.
    "MCP-Dienst im Container",
    "PDF-Konformität (veraPDF, fremdes Werkzeug)",
    # Seit Issue #118: das Gegenstück zu veraPDF für E-Rechnungen. Ohne eine
    # fremde Prüfung wäre jede Aussage über ZUGFeRD eine, die falzmarke über
    # sich selbst macht.
    "E-Rechnung (Mustang, fremdes Werkzeug)",
    # Ab hier pr-angaben.yml, das zweite Element von STANDARD_WORKFLOWS (#437):
    # Die beiden Jobs lesen den PR, nicht den Code, und starten darum auch bei
    # `edited` und `labeled`. Ein Job in einem Workflow, der dort fehlt, wäre
    # gelaufen, aber nie im Ruleset gelandet.
    #
    # Seit Issue #229: ein Vorgang ohne Punkt im Verlauf lässt sich nicht mergen.
    "Changelog-Eintrag",
    # Seit Issue #268: „Schließt #N“ schließt bei GitHub nichts.
    "Closing-Keyword",
]


def test_die_checks_aus_den_echten_workflows():
    """Keine Zahl im Namen: Sie stand bis #237 auf „acht“ und war mit dem
    neunten Check falsch, ohne dass jemand den Namen gelesen hätte."""
    assert pflicht_checks.STANDARD_WORKFLOWS == (CI, PR_ANGABEN)
    assert pflicht_checks.pflicht_checks() == ERWARTET


def test_ohne_pr_angaben_fehlen_genau_die_beiden_checks():
    """Die Gegenprobe zur Liste oben: ci.yml allein trägt die beiden nicht mehr."""
    assert pflicht_checks.pflicht_checks(CI) == ERWARTET[:-2]
    assert pflicht_checks.pflicht_checks(PR_ANGABEN) == ERWARTET[-2:]


def test_zweimal_derselbe_aufruf_liefert_dieselbe_liste():
    """Determinismus als Funktionsaufruf: kein Netz, kein Lauf, kein Zustand.

    Das ist die Gegenprobe zur alten Logik: Eine Funktion, die nur einen
    Dateipfad entgegennimmt, kann nicht von einem *Zeitpunkt* abhängen. Der
    Vorfall vom 30.08.2026 — derselbe Aufruf, verschiedene Ergebnisse je
    nachdem ob CI gerade lief — kann hier grundsätzlich nicht auftreten,
    weil kein CI-Lauf mehr abgefragt wird.
    """
    assert pflicht_checks.pflicht_checks() == pflicht_checks.pflicht_checks()


def _schreibe(tmp_path, jobs_yaml: str):
    """`jobs_yaml` beginnt bei Spalte 0 (dedented) und wird hier unter `jobs:`
    eingerückt — sonst stünden die Jobs als eigene Top-Level-Schlüssel neben
    `jobs:` statt darin."""
    pfad = tmp_path / "ci.yml"
    pfad.write_text(
        "on:\n  push:\n    branches: [main]\n  pull_request:\njobs:\n"
        + textwrap.indent(jobs_yaml, "  "),
        encoding="utf-8",
    )
    return pfad


def test_job_nur_auf_main_bleibt_ausgeschlossen(tmp_path):
    """Der berechtigte Teil der alten Logik (Issue-Text, Abschnitt 'Das Anliegen dahinter')."""
    pfad = _schreibe(tmp_path, textwrap.dedent("""\
        veroeffentlichen:
          if: github.ref == 'refs/heads/main'
          runs-on: ubuntu-latest
          steps: []
        tests:
          runs-on: ubuntu-latest
          steps: []
    """))
    assert pflicht_checks.pflicht_checks(pfad) == ["tests"]


def test_gegenprobe_ohne_if_erscheint_der_job(tmp_path):
    """Ohne diese Gegenprobe würde der Test oben nur belegen, dass `tests` da ist —
    nicht, dass die `if`-Bedingung wirklich der Grund für den Ausschluss war."""
    pfad = _schreibe(tmp_path, textwrap.dedent("""\
        veroeffentlichen:
          runs-on: ubuntu-latest
          steps: []
        tests:
          runs-on: ubuntu-latest
          steps: []
    """))
    assert pflicht_checks.pflicht_checks(pfad) == ["veroeffentlichen", "tests"]


def test_angezeigter_name_statt_jobschluessel(tmp_path):
    """Die Namensfalle aus dem Issue: `pdf-konformitaet` heißt angezeigt
    'PDF-Konformität (veraPDF, fremdes Werkzeug)'. Der Jobschlüssel als Check
    einzutragen würde jeden Pull Request dauerhaft blockieren, weil GitHub nie
    einen Check mit diesem Namen meldet."""
    pfad = _schreibe(tmp_path, textwrap.dedent("""\
        pdf-konformitaet:
          name: "PDF-Konformität (veraPDF, fremdes Werkzeug)"
          runs-on: ubuntu-latest
          steps: []
    """))
    assert pflicht_checks.pflicht_checks(pfad) == ["PDF-Konformität (veraPDF, fremdes Werkzeug)"]


def test_gegenprobe_ohne_name_erscheint_der_jobschluessel(tmp_path):
    """Ohne diese Gegenprobe würde der Test oben nur belegen, dass der Anzeigename
    irgendwo herkommt — nicht, dass er wirklich aus `name:` gelesen wird."""
    pfad = _schreibe(tmp_path, textwrap.dedent("""\
        pdf-konformitaet:
          runs-on: ubuntu-latest
          steps: []
    """))
    assert pflicht_checks.pflicht_checks(pfad) == ["pdf-konformitaet"]


def test_matrix_mit_zwei_achsen_wird_zum_kartesischen_produkt(tmp_path):
    """Nicht durch das echte ci.yml abgedeckt (dort nur eine Achse `os`), aber Teil
    der implementierten Logik — ungetesteter Code für einen Fall, der beim
    nächsten Matrix-Job im Repo sofort gebraucht wird."""
    pfad = _schreibe(tmp_path, textwrap.dedent("""\
        tests:
          strategy:
            matrix:
              os: [ubuntu-latest, macos-latest]
              python: ["3.11", "3.12"]
          runs-on: ${{ matrix.os }}
          steps: []
    """))
    assert pflicht_checks.pflicht_checks(pfad) == [
        "tests (ubuntu-latest, 3.11)",
        "tests (ubuntu-latest, 3.12)",
        "tests (macos-latest, 3.11)",
        "tests (macos-latest, 3.12)",
    ]


def test_matrix_exclude_entfernt_die_kombination(tmp_path):
    """GitHub führt eine per `exclude` genannte Kombination nie aus. Landet sie
    trotzdem als Pflicht-Check im Ruleset, wartet main auf einen Check, den es
    nie geben wird — dieselbe Namensfalle wie bei `name:`, nur über `exclude`
    statt über den Anzeigenamen ausgelöst."""
    pfad = _schreibe(tmp_path, textwrap.dedent("""\
        tests:
          strategy:
            matrix:
              os: [ubuntu-latest, macos-latest]
              python: ["3.11", "3.12"]
              exclude:
                - os: macos-latest
                  python: "3.11"
          runs-on: ${{ matrix.os }}
          steps: []
    """))
    assert pflicht_checks.pflicht_checks(pfad) == [
        "tests (ubuntu-latest, 3.11)",
        "tests (ubuntu-latest, 3.12)",
        "tests (macos-latest, 3.12)",
    ]


def test_gegenprobe_ohne_exclude_erscheint_die_kombination_wieder(tmp_path):
    """Ohne diese Gegenprobe würde der Test oben nur belegen, dass irgendeine
    Kombination fehlt — nicht, dass wirklich `exclude` der Grund war."""
    pfad = _schreibe(tmp_path, textwrap.dedent("""\
        tests:
          strategy:
            matrix:
              os: [ubuntu-latest, macos-latest]
              python: ["3.11", "3.12"]
          runs-on: ${{ matrix.os }}
          steps: []
    """))
    assert "tests (macos-latest, 3.11)" in pflicht_checks.pflicht_checks(pfad)


def test_matrix_nur_include_erzeugt_eine_kombination_je_eintrag(tmp_path):
    """Standard-GitHub-Actions-Muster: eine Matrix ohne eigene Achsen, die
    ausschließlich über `include` definiert ist. GitHub führt dafür zwei
    eigene Jobs mit je eigenem, aus den Werten abgeleiteten Checknamen aus —
    nicht den nackten Jobnamen `tests` einmal, wie es die alte Logik ohne
    Achsen getan hätte (Issue #196, über `include` statt über `name:`)."""
    pfad = _schreibe(tmp_path, textwrap.dedent("""\
        tests:
          strategy:
            matrix:
              include:
                - os: ubuntu-latest
                  python: "3.11"
                - os: macos-latest
                  python: "3.12"
          runs-on: ${{ matrix.os }}
          steps: []
    """))
    assert pflicht_checks.pflicht_checks(pfad) == [
        "tests (ubuntu-latest, 3.11)",
        "tests (macos-latest, 3.12)",
    ]


def test_gegenprobe_ohne_include_erscheint_nur_der_nackte_jobname(tmp_path):
    """Ohne diese Gegenprobe würde der Test oben nur belegen, dass irgendwie
    zwei Checks herauskommen — nicht, dass wirklich `include` dafür
    verantwortlich ist."""
    pfad = _schreibe(tmp_path, textwrap.dedent("""\
        tests:
          strategy:
            matrix: {}
          runs-on: ubuntu-latest
          steps: []
    """))
    assert pflicht_checks.pflicht_checks(pfad) == ["tests"]


def test_analysiere_meldet_ausgeschlossene_jobs_getrennt(tmp_path):
    pfad = _schreibe(tmp_path, textwrap.dedent("""\
        veroeffentlichen:
          if: github.ref == 'refs/heads/main'
          runs-on: ubuntu-latest
          steps: []
        tests:
          runs-on: ubuntu-latest
          steps: []
    """))
    checks, ausgeschlossen = pflicht_checks.analysiere(pfad)
    assert checks == ["tests"]
    assert ausgeschlossen == ["veroeffentlichen"]


def test_die_datei_ist_gueltiges_yaml_mit_pyyaml_lesbar():
    """Regressionsschutz: Der Test oben nimmt das echte ci.yml — bleibt es
    kaputt, wären alle anderen Tests hier bedeutungslos, weil sie mit
    synthetischen Dateien arbeiten."""
    daten = yaml.safe_load(CI.read_text(encoding="utf-8"))
    assert set(daten["jobs"]) == {"tests", "frischklon", "skill-paket",
                                 "pdf-konformitaet", "mcp-container", "e-rechnung"}
    daten = yaml.safe_load(PR_ANGABEN.read_text(encoding="utf-8"))
    assert set(daten["jobs"]) == {"changelog", "closing-keyword"}


# ── Was sich aus einem Workflow nicht ableiten lässt (#437) ────────────────

def _workflow(tmp_path, name: str, kopf: str, job: str = "tests"):
    pfad = tmp_path / name
    pfad.write_text(kopf + f"jobs:\n  {job}:\n    runs-on: ubuntu-latest\n    steps: []\n",
                    encoding="utf-8")
    return pfad


def test_ein_checkname_in_zwei_workflows_ist_ein_fehler(tmp_path):
    """Zwei Check-Runs gleichen Namens: Für das Ruleset zählt der jüngste, ein
    grüner des einen überdeckte einen roten des anderen."""
    a = _workflow(tmp_path, "a.yml", "on: pull_request\n")
    b = _workflow(tmp_path, "b.yml", "on: pull_request\n")
    assert pflicht_checks.pflicht_checks(a) == ["tests"]   # Kontrolle: einzeln gültig
    with pytest.raises(pflicht_checks.Workflowfehler, match="mehrfach vergeben: tests"):
        pflicht_checks.pflicht_checks((a, b))


def test_ein_workflow_ohne_pull_request_ist_ein_fehler(tmp_path):
    """Seine Jobs kämen in keinem PR: Das Ruleset wartete auf sie, bis jemand es ändert."""
    pfad = _workflow(tmp_path, "nur-push.yml", "on:\n  push:\n    branches: [main]\n")
    with pytest.raises(pflicht_checks.Workflowfehler, match="nur-push.yml startet nicht bei pull_request"):
        pflicht_checks.pflicht_checks(pfad)


def test_ein_workflow_ohne_synchronize_ist_ein_fehler(tmp_path):
    """Ein neuer Commit bekäme seinen Check nie. `edited` allein reicht nicht."""
    pfad = _workflow(tmp_path, "angaben.yml",
                     "on:\n  pull_request:\n    types: [opened, reopened, edited]\n")
    with pytest.raises(pflicht_checks.Workflowfehler, match="startet nicht bei synchronize"):
        pflicht_checks.pflicht_checks(pfad)
    voll = _workflow(tmp_path, "voll.yml",
                     "on:\n  pull_request:\n    types: [opened, synchronize, reopened, edited]\n")
    assert pflicht_checks.pflicht_checks(voll) == ["tests"]   # Gegenstück: mit ihm gültig


def test_ein_workflow_mit_filter_ist_ein_fehler(tmp_path):
    """Nachreview von #483: Ein `paths`- oder `branches`-Filter am `pull_request`
    lässt einen PR außerhalb des Filters ohne Checks, und main wartete auf sie."""
    pfade = _workflow(tmp_path, "gefiltert.yml", "on:\n  pull_request:\n    paths: ['src/**']\n")
    with pytest.raises(pflicht_checks.Workflowfehler,
                       match="gefiltert.yml startet bei pull_request nur mit paths"):
        pflicht_checks.pflicht_checks(pfade)
    zweige = _workflow(tmp_path, "zweige.yml",
                       "on:\n  pull_request:\n    branches-ignore: [docs]\n")
    with pytest.raises(pflicht_checks.Workflowfehler, match="nur mit branches-ignore"):
        pflicht_checks.pflicht_checks(zweige)
    frei = _workflow(tmp_path, "frei.yml", "on:\n  pull_request:\n")
    assert pflicht_checks.pflicht_checks(frei) == ["tests"]   # Gegenstück: ohne Filter gültig


def test_das_skript_meldet_einen_unbrauchbaren_workflow_statt_abzustuerzen(tmp_path, monkeypatch,
                                                                             capsys):
    """Nachreview von #483: Exit 1 mit einer Zeile, kein Traceback — das Skript
    wird aus repo-einstellungen.sh gerufen, und dort zählt der Exit-Code."""
    pfad = _workflow(tmp_path, "nur-push.yml", "on:\n  push:\n")
    monkeypatch.setattr(sys, "argv", ["pflicht_checks.py", "--workflow", str(pfad)])
    assert pflicht_checks.main() == 1
    aus = capsys.readouterr()
    assert "FEHLER  nur-push.yml startet nicht bei pull_request" in aus.err and aus.out == ""


# ── Das Skript ruft keinen CI-Lauf mehr ab ──────────────────────────────────

@pytest.mark.parametrize("verbotenes_muster", [
    "gh run list",
    "actions/runs",
    'conclusion=="success"',
])
def test_skript_fragt_keinen_ci_lauf_mehr_ab(verbotenes_muster):
    text = SKRIPT.read_text(encoding="utf-8")
    assert verbotenes_muster not in text, (
        f"repo-einstellungen.sh enthält wieder {verbotenes_muster!r} — die "
        "Pflicht-Checks würden erneut vom Zeitpunkt des Aufrufs abhängen "
        "(Issue #196)."
    )


def test_skript_ruft_pflicht_checks_auf():
    text = SKRIPT.read_text(encoding="utf-8")
    assert "python3 scripts/pflicht_checks.py" in text


def test_liste_wird_vor_dem_anwenden_gezeigt():
    """Trockenlauf-Anforderung aus dem Issue: Die Liste steht vor jeder
    Ruleset-Anwendung im Skriptablauf — nicht nur im Trockenlauf-Zweig."""
    text = SKRIPT.read_text(encoding="utf-8")
    ableitung = text.index("Status-Checks aus den Workflow-Dateien ableiten")
    anwendung = text.index('setze_ruleset "main"')
    assert ableitung < anwendung
