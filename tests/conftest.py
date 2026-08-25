"""Gemeinsame Fixtures. Die Beispiele werden einmal je Testlauf gerendert."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SKILL = REPO / "skill"
sys.path.insert(0, str(SKILL / "scripts"))

BEISPIELE = sorted((REPO / "examples").glob("*.md"))


@pytest.fixture(scope="session")
def gerendert(tmp_path_factory) -> dict[str, tuple[Path, str]]:
    """Name des Beispiels -> (PDF-Pfad, Form)."""
    import normbrief

    ziel = tmp_path_factory.mktemp("renders")
    ergebnis = {}
    for quelle in BEISPIELE:
        pdf, form = normbrief.rendere(quelle, ziel / f"{quelle.stem}.pdf")
        ergebnis[quelle.stem] = (pdf, form)
    return ergebnis


@pytest.fixture(scope="session")
def beispiel_pfade() -> list[Path]:
    return BEISPIELE
