"""Der eigene Quelltext übersetzt sich ohne Warnung (#248).

WARUM ES DAS GIBT

Seit dem 21.08.2026 meldete jeder Testlauf eine `SyntaxWarning`: Ein Docstring
in `test_vollstaendigkeit.py` erklärte die Escape-Behandlung und schrieb dabei
`\\*` in einen gewöhnlichen String. Python warnt darüber und wird es in einer
späteren Fassung als **Fehler** behandeln.

Bemerkt hat es zwei Wochen lang niemand, und das hat einen Grund, der wichtiger
ist als der Fehler selbst: **Die Warnung erscheint nur beim Kompilieren.** Liegt
die `.pyc` bereits vor, bleibt sie stumm. Wer die Suite zweimal fährt, sieht sie
beim zweiten Mal nicht mehr — und wer sie nie leert, nie.

Ein Test, der sich auf pytest-Warnfilter verließe, hätte dieselbe Schwäche: Er
sähe die Warnung nur, wenn das Modul in genau diesem Lauf übersetzt wird. Diese
Datei übersetzt deshalb **selbst**, unabhängig von jedem Cache.

Der Preis ist gering: `compile()` über den Quelltext führt nichts aus, es baut
nur den Syntaxbaum. Kein Import, keine Nebenwirkung.
"""

from __future__ import annotations

import warnings

import pytest

from conftest import REPO

#: Wo nicht hingesehen wird. `.git` ist offensichtlich; die übrigen sind
#: Fremdcode oder Erzeugnisse, für die dieses Repo nicht einsteht.
AUSGENOMMEN = {".git", "node_modules", "__pycache__", ".venv", "venv", "build", "dist"}


def _quelldateien() -> list:
    return sorted(
        p for p in REPO.rglob("*.py")
        if not AUSGENOMMEN & set(p.relative_to(REPO).parts)
    )


def test_es_gibt_ueberhaupt_quelldateien():
    """Ohne diese Prüfung wäre die Parametrisierung bei leerem Glob grün.

    Eine leere Menge gegen eine leere Menge belegt nichts — der häufigste Weg,
    auf dem ein Prüfmittel still wirkungslos wird.
    """
    dateien = _quelldateien()
    assert len(dateien) > 50, [p.name for p in dateien]


@pytest.mark.parametrize("pfad", _quelldateien(), ids=lambda p: str(p.relative_to(REPO)))
def test_die_datei_uebersetzt_ohne_warnung(pfad):
    """`compile()` statt Import: Der Syntaxbaum entsteht, sonst nichts."""
    with warnings.catch_warnings(record=True) as gesammelt:
        warnings.simplefilter("always")
        compile(pfad.read_text(encoding="utf-8"), str(pfad), "exec")
    syntax = [w for w in gesammelt if issubclass(w.category, SyntaxWarning)]
    assert not syntax, [f"Zeile {w.lineno}: {w.message}" for w in syntax]


def test_die_pruefung_kann_rot_werden(tmp_path):
    """Gegenprobe. Ohne sie belegte der Test darüber nur, dass eine Liste leer
    ist — und das wäre auch dann so, wenn `catch_warnings` nichts sammelte."""
    kaputt = tmp_path / "mit_warnung.py"
    # Genau der Fall aus #248: eine ungültige Escape-Sequenz in einem
    # gewöhnlichen String. Zusammengesetzt, damit diese Datei ihn nicht selbst
    # enthält und ihre eigene Prüfung auslöst.
    kaputt.write_text('x = "' + chr(92) + 'q"\n', encoding="utf-8")
    with warnings.catch_warnings(record=True) as gesammelt:
        warnings.simplefilter("always")
        compile(kaputt.read_text(encoding="utf-8"), str(kaputt), "exec")
    assert any(issubclass(w.category, SyntaxWarning) for w in gesammelt), \
        "die Sabotage löste keine Warnung aus — dann misst der Test darüber nichts"
