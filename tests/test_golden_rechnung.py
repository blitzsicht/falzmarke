"""`scripts/golden_rechnung.py` darf an der Maske nicht scheitern (Review #568).

Das Skript vergleicht PDF-Goldens durch `conftest.ohne_typst_kennung` (#533). Die
Maske bricht ab, wenn typst sein XMP umbaut oder die Kennung anders oft schreibt.
Bis zum Review von #568 brach sie damit auch das Neu-Erzeugen ab, also genau den
Lauf, mit dem man auf eine solche typst-Fassung reagiert. Ohne `--pruefen` wird
deshalb roh verglichen und geschrieben, eine Zeile je Datei auf stderr sagt, warum,
und der Lauf endet mit Exit 2 statt 0 (Review #575). Mit `--pruefen` zählt eine
Datei, an der die Maske nicht greift, als Abweichung samt Grund. Der Lauf vergleicht
die übrigen Goldens weiter und endet mit der Zusammenfassung und Exit 1; bis zum
Review von #575 brach er beim ersten PDF mit einem Traceback ab.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

from conftest import REPO, RECHNUNG_BEISPIELE, ohne_typst_kennung
from test_rechnung_beispiele import GOLDEN, _andere_typst_fassung

sys.path.insert(0, str(REPO / "scripts"))

import golden_rechnung                                           # noqa: E402


def ohne_kennung(pdf: bytes) -> bytes:
    """Dasselbe PDF, dessen XMP kein `CreatorTool` von typst trägt: Die Maske greift nicht."""
    ohne = pdf.replace(b"<xmp:CreatorTool>Typst ", b"<xmp:CreatorTool>Tipst ", 1)
    assert ohne != pdf, "die Störung greift nicht — das Golden trägt kein CreatorTool"
    return ohne


def golden_und_ohne_kennung() -> tuple[bytes, bytes]:
    """Ein echtes PDF-Golden und dasselbe PDF, dessen XMP kein `CreatorTool` von typst trägt."""
    golden = (GOLDEN / f"{RECHNUNG_BEISPIELE[0].stem}.pdf").read_bytes()
    return golden, ohne_kennung(golden)


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


def test_mit_pruefen_zaehlt_eine_maske_die_nicht_greift_als_abweichung(ziel, capsys):
    """Laut heißt hier: als Abweichung samt Grund, nicht als Traceback (Review #575)."""
    golden, neu = golden_und_ohne_kennung()
    ziel.write_bytes(golden)
    assert golden_rechnung._aktualisiere(ziel, neu, True, maske=ohne_typst_kennung) is True, \
        "mit --pruefen gilt eine Datei, an der die Maske nicht greift, als „gleich“"
    assert ziel.read_bytes() == golden, "--pruefen hat geschrieben"
    fehler = capsys.readouterr().err
    assert f"weicht ab  {ziel.name} — Maske greift nicht: keine typst-Kennung im XMP" \
        in fehler, fehler


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


# ── Der ganze Lauf: `main` über mehrere Goldens (Review #575) ────────────────

def _lauf(wurzel: Path, monkeypatch):
    """`main` über zwei Beispiele, gegen Kopien ihrer Goldens unter `wurzel`.

    `erzeuge` rendert nicht, sondern gibt das echte Golden durch eine Störung zurück:
    Gemessen wird das Skript, nicht typst. Zurück kommen das Zielverzeichnis, die
    Beispiele und `fahre(argv, stoerung)`, das `main` mit dieser Störung aufruft.
    Kein Fixture, damit die Gegenproben in `test_gegenbeweis` es selbst aufbauen."""
    beispiele = RECHNUNG_BEISPIELE[:2]
    assert len(beispiele) == 2, "zu wenige Rechnungsbeispiele für einen Lauf über mehrere"
    ziel = wurzel / "tests" / "golden" / "rechnung"
    ziel.mkdir(parents=True)
    for beispiel in beispiele:
        for endung in (".pdf", ".xml"):
            shutil.copyfile(GOLDEN / f"{beispiel.stem}{endung}", ziel / f"{beispiel.stem}{endung}")
    monkeypatch.setattr(golden_rechnung, "REPO", wurzel)
    monkeypatch.setattr(golden_rechnung, "ZIEL", ziel)
    monkeypatch.setattr(golden_rechnung, "RECHNUNG_BEISPIELE", beispiele)

    def fahre(argv: list[str], stoerung) -> int:
        monkeypatch.setattr(golden_rechnung, "erzeuge", lambda quelle: (
            stoerung((GOLDEN / f"{quelle.stem}.pdf").read_bytes()),
            (GOLDEN / f"{quelle.stem}.xml").read_bytes()))
        return golden_rechnung.main(argv)

    return ziel, beispiele, fahre


@pytest.fixture
def lauf(tmp_path, monkeypatch):
    return _lauf(tmp_path, monkeypatch)


def _relativ(beispiel, endung: str) -> str:
    """Der Pfad, wie das Skript ihn meldet: relativ zu `REPO`, mit dem Trenner des Systems."""
    return str(Path("tests", "golden", "rechnung", f"{beispiel.stem}{endung}"))


def _bestand(ziel: Path) -> dict[str, bytes]:
    return {p.name: p.read_bytes() for p in sorted(ziel.iterdir())}


def test_mit_pruefen_laeuft_ein_maskenfehler_bis_zur_zusammenfassung(lauf, capsys):
    """Bis zum Review von #575 endete `--pruefen` am ersten PDF mit einem Traceback: Die
    übrigen Goldens wurden nie verglichen, die Schlusszeile fehlte."""
    ziel, beispiele, fahre = lauf
    vorher = _bestand(ziel)
    code = fahre(["--pruefen"], ohne_kennung)
    aus = capsys.readouterr()
    for beispiel in beispiele:
        assert (f"weicht ab  {_relativ(beispiel, '.pdf')} — Maske greift nicht: "
                "keine typst-Kennung im XMP") in aus.err, aus.err
        assert f"gleich     {_relativ(beispiel, '.xml')}" in aus.out, aus.out
    assert "2 Golden-Datei(en) nicht auf Stand" in aus.err, aus.err
    assert code == 1, f"--pruefen endete mit {code} statt 1"
    assert _bestand(ziel) == vorher, "--pruefen hat geschrieben"


def test_ohne_pruefen_endet_ein_roher_vergleich_mit_exit_2(lauf, capsys):
    """Entscheidung des Operators (Review #575): Das Skript schreibt weiter roh, endet
    dann aber mit Exit 2 statt 0, und eine Zusammenfassung auf stderr sagt, wie viele
    Dateien roh verglichen sind und warum."""
    ziel, beispiele, fahre = lauf
    code = fahre([], ohne_kennung)
    aus = capsys.readouterr()
    for beispiel in beispiele:
        soll = ohne_kennung((GOLDEN / f"{beispiel.stem}.pdf").read_bytes())
        assert (ziel / f"{beispiel.stem}.pdf").read_bytes() == soll, \
            f"{beispiel.stem}.pdf wurde nicht roh geschrieben"
        assert f"erneuert   {_relativ(beispiel, '.pdf')}" in aus.out, aus.out
        assert (f"  {_relativ(beispiel, '.pdf')} (geschrieben): "
                "keine typst-Kennung im XMP") in aus.err, aus.err
    assert "2 PDF-Golden(s) roh verglichen, weil die Maske nicht griff" in aus.err, aus.err
    assert "echte Änderung" in aus.err, aus.err
    assert code == 2, f"der rohe Vergleich endete mit Exit {code} statt 2"


def test_greift_die_maske_endet_der_lauf_mit_0(lauf, capsys):
    """Kontrolle: Exit 1 und 2 oben kommen vom Maskenfehler, nicht vom Lauf selbst. Eine
    Fassung, die nur typsts Kennung ändert, ergibt mit und ohne `--pruefen` Exit 0 und
    schreibt nichts."""
    ziel, _, fahre = lauf
    vorher = _bestand(ziel)
    assert fahre([], _andere_typst_fassung) == 0, "ohne --pruefen nicht Exit 0"
    assert fahre(["--pruefen"], _andere_typst_fassung) == 0, "mit --pruefen nicht Exit 0"
    assert _bestand(ziel) == vorher, "eine bloß andere typst-Fassung wurde geschrieben"
    assert "roh verglichen" not in capsys.readouterr().err
