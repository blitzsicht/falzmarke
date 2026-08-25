"""Gemeinsame Fixtures. Die Beispiele werden einmal je Testlauf gerendert.

Wo Tests die CLI über `subprocess` aufrufen, steht dort `encoding="utf-8"`.
Ohne das liest Python die Ausgabe unter Windows in cp1252, und jeder Vergleich
mit einem Text, der `—` oder `ß` enthält, scheitert an Mojibake statt an der
Sache. Das Programm selbst schreibt seit v0.2.0 immer UTF-8.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SKILL = REPO / "skill"
# Der Skill-Ordner ist zugleich das Paketverzeichnis.
sys.path.insert(0, str(SKILL))

BEISPIELE = sorted((REPO / "examples").glob("*.md"))


@pytest.fixture(scope="session")
def gerendert(tmp_path_factory) -> dict[str, tuple[Path, str]]:
    """Name des Beispiels -> (PDF-Pfad, Form)."""
    from normbrief import cli as normbrief

    ziel = tmp_path_factory.mktemp("renders")
    ergebnis = {}
    for quelle in BEISPIELE:
        pdf, form = normbrief.rendere(quelle, ziel / f"{quelle.stem}.pdf")
        ergebnis[quelle.stem] = (pdf, form)
    return ergebnis


@pytest.fixture(scope="session")
def beispiel_pfade() -> list[Path]:
    return BEISPIELE
