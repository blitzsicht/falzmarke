"""Kein Workflow dieses Repositories schreibt selbst auf `main`.

WARUM ES DAS GIBT

Bis zum 30.08.2026 taten es drei: `ci.yml` schrieb die PNG-Renders zurück,
`video.yml` die Aufzeichnung und `roadmap.yml` die erzeugte Seite. In den
letzten 30 Commits auf main standen dadurch 13 Bot-Commits, 12 davon aus
`video.yml`.

Solange das so war, konnte das Ruleset `main` nicht auf `active`: Ein Ruleset
gilt für **alle** Akteure ohne Bypass, das `GITHUB_TOKEN` eingeschlossen. Der
naheliegende Ausweg — die Actions-App in `bypass_actors` — wird von GitHub
abgewiesen:

    422  "Actor GitHub Actions integration must be part of the ruleset source
          or owner organization"

Sie ist keine *installierte* App (gemessen am 30.08.2026, Issue #188). Und ein
Bot-PR statt eines Bot-Pushes hilft nicht: Ein mit dem `GITHUB_TOKEN` erzeugter
PR löst keine Workflow-Läufe aus, bekäme also nie die Pflicht-Checks und bliebe
für immer offen.

Deshalb liefern die Jobs ihre Ergebnisse als Artefakt ab. Wer das Layout oder
die CLI-Ausgabe ändert, nimmt die neuen Dateien in seinen eigenen Pull Request
auf — so beschreibt es `CONTRIBUTING.md`.

WAS DIESER TEST NICHT KANN

Er sieht die Workflow-Dateien, nicht den Server. Ob das Ruleset wirklich
scharf steht, sagt nur ein abgewiesener Push gegen `main`; das steht in
`docs/recht.md` nicht und lässt sich hier nicht nachstellen. Dieser Test hält
die andere Hälfte fest: dass niemand die Push-Schritte versehentlich
zurückholt.
"""

from __future__ import annotations

import re

import pytest
import yaml

from conftest import REPO

WORKFLOWS = sorted((REPO / ".github" / "workflows").glob("*.yml"))

# `git push` und `git commit` in einer Befehlszeile — nicht in Prosa. Die
# Kommentare in ci.yml und video.yml erklaeren ausfuehrlich, warum frueher
# gepusht wurde und warum das aufgehoert hat; diese Begruendung soll stehen
# bleiben duerfen. Deshalb werden Kommentarzeilen vorher entfernt.
#
# Der Ausdruck faengt bewusst auch `if git push origin HEAD:main; then` — genau
# so stand der Push in ci.yml, und ein Anker am Zeilenanfang haette ihn
# uebersehen.
SCHREIBBEFEHL = re.compile(r"\bgit\s+(push|commit)\b")

# `contents: write` ohne Push. release.yml legt ein Release an und haengt ein
# Asset daran — das braucht das Recht, erzeugt aber keinen Commit auf main.
# Die Ausnahme ist benannt und nicht generisch: Wer einen zweiten Workflow
# eintraegt, muss diesen Kommentar lesen.
SCHREIBRECHT_ERLAUBT = {"release.yml"}


def _befehlszeilen(text: str) -> list[tuple[int, str]]:
    """Alle Zeilen ohne Kommentaranteil, mit ihrer Nummer."""
    zeilen = []
    for nr, zeile in enumerate(text.splitlines(), 1):
        ohne_kommentar = re.sub(r"#.*$", "", zeile)
        if ohne_kommentar.strip():
            zeilen.append((nr, ohne_kommentar))
    return zeilen


def test_es_gibt_ueberhaupt_workflows_zu_pruefen():
    """Eine leere Menge gegen eine leere Menge belegt nichts.

    Ohne diese Zusicherung waeren alle Pruefungen unten auch dann gruen, wenn
    der Glob ins Leere liefe — etwa nach einer Umbenennung des Verzeichnisses.
    """
    assert len(WORKFLOWS) >= 5, f"nur {len(WORKFLOWS)} Workflows gefunden — Glob kaputt?"


@pytest.mark.parametrize("pfad", WORKFLOWS, ids=lambda p: p.name)
def test_kein_workflow_committet_oder_pusht(pfad):
    treffer = [
        f"{pfad.name}:{nr}: {zeile.strip()}"
        for nr, zeile in _befehlszeilen(pfad.read_text(encoding="utf-8"))
        if SCHREIBBEFEHL.search(zeile)
    ]
    assert not treffer, (
        "Workflow schreibt selbst ins Repository — das blockiert das Ruleset "
        "auf main (Issue #188):\n  " + "\n  ".join(treffer)
    )


@pytest.mark.parametrize("pfad", WORKFLOWS, ids=lambda p: p.name)
def test_schreibrecht_nur_wo_es_begruendet_ist(pfad):
    inhalt = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    fundstellen = []

    def sammle(rechte, wo):
        if isinstance(rechte, dict) and rechte.get("contents") == "write":
            fundstellen.append(wo)

    sammle(inhalt.get("permissions"), f"{pfad.name} (Workflow-Ebene)")
    for name, job in (inhalt.get("jobs") or {}).items():
        sammle((job or {}).get("permissions"), f"{pfad.name}, Job „{name}“")

    if pfad.name in SCHREIBRECHT_ERLAUBT:
        # Kein Skip: Eine uebersprungene Pruefung belegt nichts, und eine
        # Ausnahmeliste, die niemand nachmisst, ueberlebt den Grund, aus dem
        # sie angelegt wurde. Hier wird die Ausnahme deshalb POSITIV geprueft —
        # faellt das Schreibrecht in release.yml eines Tages weg, faellt der
        # Name aus dieser Liste mit, statt still darin liegen zu bleiben.
        assert fundstellen, (
            f"{pfad.name} steht in SCHREIBRECHT_ERLAUBT, fordert aber gar kein "
            "contents: write mehr — Eintrag entfernen."
        )
        return

    assert not fundstellen, (
        "contents: write ohne Grund — wer nicht schreibt, braucht es nicht:\n  "
        + "\n  ".join(fundstellen)
    )
