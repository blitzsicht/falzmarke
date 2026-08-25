"""Die zugelassene Markdown-Teilmenge und ihre Grenzen."""

from __future__ import annotations

import pytest

from markdown_typst import NBSP, MarkdownFehler, konvertiere


def test_absaetze_bleiben_absaetze():
    assert konvertiere("Erster Absatz.\n\nZweiter Absatz.") == "Erster Absatz.\n\nZweiter Absatz.\n"


def test_fett_und_kursiv():
    assert konvertiere("**fett** und *kursiv*").strip() == "*fett* und _kursiv_"


def test_listen():
    assert konvertiere("- eins\n- zwei").strip() == "- eins\n- zwei"
    assert konvertiere("1. eins\n2. zwei").strip() == "+ eins\n+ zwei"


def test_harter_umbruch():
    assert konvertiere("Zeile eins\\\nZeile zwei").strip() == "Zeile eins \\\nZeile zwei"


def test_tabelle():
    ergebnis = konvertiere("| A | B |\n|---|---|\n| 1 | 2 |")
    assert "#table(" in ergebnis and "columns: 2" in ergebnis
    assert "[*A*], [*B*]" in ergebnis


@pytest.mark.parametrize(
    "zeichen", ["#", "_", "@", "<", ">", "$", "\\", "~", "`", "[", "]"]
)
def test_typst_sonderzeichen_werden_escaped(zeichen):
    """Ungeschützt würde Typst '#' als Codebeginn lesen — der Brief sähe still
    falsch aus."""
    ergebnis = konvertiere(f"Text mit {zeichen} darin")
    assert "\\" + zeichen in ergebnis


def test_einzelnes_sternchen_bricht_mit_erklaerung_ab():
    """Ein einzelnes '*' ist Kursiv-Markup, kein Literal. Statt es still zu
    verschlucken oder Typst durcheinanderzubringen, wird es benannt."""
    with pytest.raises(MarkdownFehler) as fehler:
        konvertiere("Rechnung 5 * 3 Stunden")
    assert "Sternchen" in str(fehler.value)


def test_geschuetzte_leerzeichen_nach_din():
    assert f"z.{NBSP}B." in konvertiere("etwa z. B. dieses")
    assert f"i.{NBSP}A." in konvertiere("gezeichnet i. A. Muster")


@pytest.mark.parametrize(
    "eingabe,erwartet",
    [
        ("## Überschrift", "Überschriften"),
        ("> Zitat", "Blockzitate"),
        ("```python\ncode\n```", "Codeblöcke"),
        ("![Bild](x.png)", "Bilder"),
        ("[Text](https://example.de)", "Links"),
        ("---", "Trennlinien"),
    ],
)
def test_nicht_zugelassenes_bricht_ab(eingabe, erwartet):
    with pytest.raises(MarkdownFehler) as fehler:
        konvertiere(eingabe)
    assert erwartet in str(fehler.value)


def test_fehler_nennt_die_zeile_der_originaldatei():
    with pytest.raises(MarkdownFehler) as fehler:
        konvertiere("Text\n\n## Titel", zeilenversatz=18)
    assert "Zeile 21" in str(fehler.value)


def test_tabelle_mit_falscher_spaltenzahl():
    with pytest.raises(MarkdownFehler) as fehler:
        konvertiere("| A | B |\n|---|---|\n| 1 |")
    assert "Zellen" in str(fehler.value)
