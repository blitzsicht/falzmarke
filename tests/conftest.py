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

# Die Mail-Beispiele liegen bewusst eine Ebene tiefer. `examples/*.md` wird in
# der CI und oben in BEISPIELE als **Brief** gerendert; eine Datei mit
# `typ: email` bricht dort absichtlich ab (cli.py, `rendere`). Der Glob ist
# nicht rekursiv — der Unterordner ist damit die Trennung, nicht eine
# Ausnahmeliste, die jemand pflegen muesste.
EMAIL_BEISPIELE = sorted((REPO / "examples" / "email").glob("*.md"))


def _fassung(pfad: Path) -> str:
    """Die Dialektfassung eines Beispiels, ohne YAML zu laden.

    Reicht für die Auswahl unten und hält conftest frei von Abhängigkeiten.
    """
    for zeile in pfad.read_text(encoding="utf-8").split("\n---", 1)[0].splitlines():
        if zeile.startswith("dialekt:"):
            return zeile.split(":", 1)[1].strip().strip("\"'")
    return "1.0"


#: Beispiele in Fassung 1.0. Nur sie taugen als Eingang für die E-Mail-Emitter:
#: Was 1.1 braucht, lehnt `markdown.py` bei `ziel="email"` ab, solange der
#: HTML-Teil es nicht setzt.
#:
#: Bewusst eine eigene Liste statt eines `skipif` im Test: Eine übersprungene
#: Prüfung sieht aus wie eine bestandene. So steht die Zahl daneben, und
#: `tests/test_dialekt.py` hält fest, dass die Auswahl weder leer noch
#: vollständig ist.
BEISPIELE_10 = [p for p in BEISPIELE if _fassung(p) == "1.0"]
BEISPIELE_11 = [p for p in BEISPIELE if _fassung(p) != "1.0"]


@pytest.fixture(scope="session")
def gerendert(tmp_path_factory) -> dict[str, tuple[Path, str]]:
    """Name des Beispiels -> (PDF-Pfad, Form)."""
    from falzmarke import cli as falzmarke

    ziel = tmp_path_factory.mktemp("renders")
    ergebnis = {}
    for quelle in BEISPIELE:
        pdf, form = falzmarke.rendere(quelle, ziel / f"{quelle.stem}.pdf")
        ergebnis[quelle.stem] = (pdf, form)
    return ergebnis


@pytest.fixture(scope="session")
def beispiel_pfade() -> list[Path]:
    return BEISPIELE
