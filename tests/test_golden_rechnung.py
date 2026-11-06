"""`scripts/golden_rechnung.py` darf an der Maske nicht scheitern (Review #568).

Das Skript vergleicht PDF-Goldens durch `conftest.ohne_typst_kennung` (#533). Die
Maske bricht ab, wenn typst sein XMP umbaut oder die Kennung anders oft schreibt.
Bis zum Review von #568 brach sie damit auch das Neu-Erzeugen ab, also genau den
Lauf, mit dem man auf eine solche typst-Fassung reagiert. Ohne `--pruefen` wird
deshalb roh verglichen und geschrieben, und eine Zeile auf stderr sagt, warum.
Mit `--pruefen` scheitert der Lauf laut, statt „gleich“ zu melden.
"""

from __future__ import annotations

import sys

import pytest

from conftest import REPO, RECHNUNG_BEISPIELE, TypstMaskeGreiftNicht, ohne_typst_kennung
from test_rechnung_beispiele import GOLDEN, _andere_typst_fassung

sys.path.insert(0, str(REPO / "scripts"))

import golden_rechnung                                           # noqa: E402


def golden_und_ohne_kennung() -> tuple[bytes, bytes]:
    """Ein echtes PDF-Golden und dasselbe PDF, dessen XMP kein `CreatorTool` von typst trägt."""
    golden = (GOLDEN / f"{RECHNUNG_BEISPIELE[0].stem}.pdf").read_bytes()
    ohne = golden.replace(b"<xmp:CreatorTool>Typst ", b"<xmp:CreatorTool>Tipst ", 1)
    assert ohne != golden, "die Störung greift nicht — das Golden trägt kein CreatorTool"
    return golden, ohne


@pytest.fixture
def ziel(tmp_path, monkeypatch):
    """Ein Golden-Pfad unter `tmp_path`. `REPO` zeigt dorthin, weil das Skript relativ meldet."""
    monkeypatch.setattr(golden_rechnung, "REPO", tmp_path)
    return tmp_path / "rechnung.pdf"


def test_eine_maske_die_nicht_greift_haelt_das_schreiben_nicht_auf(ziel, capsys):
    golden, neu = golden_und_ohne_kennung()
    ziel.write_bytes(golden)
    assert golden_rechnung._aktualisiere(ziel, neu, False, maske=ohne_typst_kennung) is True
    assert ziel.read_bytes() == neu, "das neue Golden wurde nicht geschrieben"
    fehler = capsys.readouterr().err
    assert "Maske griff nicht" in fehler and "keine typst-Kennung im XMP" in fehler, fehler


def test_mit_pruefen_scheitert_eine_maske_die_nicht_greift_laut(ziel):
    golden, neu = golden_und_ohne_kennung()
    ziel.write_bytes(golden)
    with pytest.raises(TypstMaskeGreiftNicht, match="keine typst-Kennung im XMP"):
        golden_rechnung._aktualisiere(ziel, neu, True, maske=ohne_typst_kennung)
    assert ziel.read_bytes() == golden, "--pruefen hat geschrieben"


def test_eine_greifende_maske_laesst_eine_andere_typst_fassung_durch(ziel, capsys):
    """Kontrolle: Der Ausweg oben schaltet die Maske nicht ab. Greift sie, bleibt eine
    Fassung, die nur typsts Kennung ändert, „gleich“, und es wird nichts geschrieben."""
    golden, _ = golden_und_ohne_kennung()
    ziel.write_bytes(golden)
    assert golden_rechnung._aktualisiere(ziel, _andere_typst_fassung(golden), False,
                                         maske=ohne_typst_kennung) is False, \
        "eine andere typst-Fassung gilt als Abweichung — die Maske greift nicht mehr"
    assert ziel.read_bytes() == golden
    assert "Maske griff nicht" not in capsys.readouterr().err
