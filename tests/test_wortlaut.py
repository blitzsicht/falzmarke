"""Blockzitate und wortgetreue Auszüge — und die Grenze, die sie sicher macht.

Ein Codeblock enthält per Definition Zeichen, die anderswo Bedeutung tragen.
Würde er als Markup gesetzt, führte Typst sie aus — mit Dateizugriff auf dem
Rechner des Setzenden. Diese Datei belegt, dass er es nicht wird, und zwar auf
zwei Ebenen: an der **erzeugten Ausgabe** (steht dort ein Aufruf oder eine
Zeichenkette?) und am **fertigen PDF** (ist etwas ausgewertet worden?).

Die zweite Ebene allein genügte nicht — ein Bild sieht gleich aus, ob der Text
zufällig harmlos war oder ob die Grenze hält. Die erste allein auch nicht: Sie
prüft eine Zeichenkette, nicht das Verhalten des Satzsystems.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from falzmarke import baum, emit
from falzmarke.markdown import MarkdownFehler, konvertiere, lies
from conftest import REPO, SKILL

KOPF = """---
profil: example
dialekt: "1.1"
empfaenger: [Muster GmbH, Musterstraße 1, 12345 Musterstadt]
datum: 2026-08-28
betreff: Probe
anrede: Sehr geehrte Damen und Herren,
---
"""

#: Anweisungen, die Typst ausführen würde, käme der Inhalt als Markup an.
#: `#eval` ist der Beleg, an dem sich das MESSEN lässt: Wird es ausgewertet,
#: steht das Ergebnis im PDF statt der Zeile.
GEFAEHRLICH = [
    '#import "/etc/passwd": *',
    '#read("/etc/hosts")',
    '#eval("6*7")',
    "#let x = sys.inputs",
    "#set page(width: 5mm)",
]


# ── Was gesetzt wird ────────────────────────────────────────────────────────

@pytest.mark.parametrize("quelle,erwartet", [
    ("> Ein Zitat.\n", "#zitat["),
    ("> Erste Ebene.\n>\n> > Zweite Ebene.\n", "#zitat[#par"),
    ("> Zitat mit Liste:\n>\n> - eins\n> - zwei\n", "#list("),
    ("Ein `Stück` im Satz.\n", '#raw("Stück")'),
    ("```\nzeile\n```\n", "#codeblock(raw("),
    ("    eingerückt\n", "#codeblock(raw("),
])
def test_wird_in_fassung_11_gesetzt(quelle, erwartet):
    ergebnis = konvertiere(quelle, dialekt="1.1")
    assert erwartet in ergebnis, f"{erwartet!r} fehlt in:\n{ergebnis}"


@pytest.mark.parametrize("quelle", [
    "> Ein Zitat.\n",
    "Ein `Stück` im Satz.\n",
    "```\nzeile\n```\n",
    "    eingerückt\n",
])
def test_bleibt_in_fassung_10_ein_fehler(quelle):
    """Die Gegenrichtung. Ohne sie belegte der Test darüber nicht, dass das
    Feld `dialekt` überhaupt etwas entscheidet."""
    with pytest.raises(MarkdownFehler) as fehler:
        konvertiere(quelle, dialekt="1.0")
    assert "dialekt: 1.1" in str(fehler.value)


def test_zitat_bis_zwei_ebenen():
    konvertiere("> eins\n>\n> > zwei\n", dialekt="1.1")


def test_drittes_zitat_bricht_ab():
    with pytest.raises(MarkdownFehler) as fehler:
        konvertiere("> eins\n>\n> > zwei\n> >\n> > > drei\n", dialekt="1.1")
    assert "wer wen wiedergibt" in str(fehler.value)


def test_sprachangabe_wird_gemeldet_statt_still_ignoriert():
    """Wer ```python schreibt, erwartet Einfärbung. Sie kommt nicht — und
    stillschweigend nichts zu tun wäre die teuerste Antwort darauf."""
    hinweise: list = []
    konvertiere("```python\nx = 1\n```\n", dialekt="1.1", hinweise=hinweise)
    assert len(hinweise) == 1
    assert "python" in hinweise[0].meldung


def test_ohne_sprachangabe_keine_meldung():
    hinweise: list = []
    konvertiere("```\nx = 1\n```\n", dialekt="1.1", hinweise=hinweise)
    assert hinweise == []


# ── Der Wortlaut bleibt Wortlaut ────────────────────────────────────────────

def test_typografie_greift_im_auszug_nicht():
    """Ein Auszug, in dem aus `"` ein „ und aus `--` ein – wird, ist keiner."""
    ergebnis = konvertiere('```\nsagte "so" -- und ging\n```\n', dialekt="1.1")
    assert '\\"so\\"' in ergebnis, ergebnis
    assert "--" in ergebnis
    assert "„" not in ergebnis and "–" not in ergebnis


def test_typografie_greift_daneben_weiterhin():
    """Gegenprobe: Der Pass ist nicht global abgeschaltet."""
    ergebnis = konvertiere('Er sagte "so" -- und ging.\n', dialekt="1.1")
    assert "„" in ergebnis and "–" in ergebnis


# ── Die Sicherheitsgrenze, Ebene 1: die erzeugte Ausgabe ────────────────────

@pytest.mark.parametrize("zeile", GEFAEHRLICH, ids=[z[:22] for z in GEFAEHRLICH])
def test_anweisung_wird_zur_zeichenkette_nicht_zum_aufruf(zeile):
    """Der Nachweis am Emitter-Output, nicht am Bild.

    Entscheidend ist die Form: Der Inhalt steht **innerhalb** von `raw("…")`.
    Stünde er in einem Markup-Block `[…]`, wäre er Code.
    """
    ergebnis = konvertiere(f"```\n{zeile}\n```\n", dialekt="1.1")
    assert ergebnis.startswith("#codeblock(raw(\""), ergebnis
    assert "#codeblock[" not in ergebnis, "Markup-Block statt Zeichenkette"


@pytest.mark.parametrize("zeile", GEFAEHRLICH, ids=[z[:22] for z in GEFAEHRLICH])
def test_dasselbe_inline(zeile):
    ergebnis = konvertiere(f"Der Text `{zeile}` im Satz.\n", dialekt="1.1")
    assert "#raw(\"" in ergebnis
    assert "#raw[" not in ergebnis


def test_anfuehrungszeichen_und_backslash_werden_geschuetzt():
    """Die zwei Zeichen, die die Zeichenkette selbst begrenzen könnten.

    Ohne diesen Schutz endete die Zeichenkette mitten im Inhalt, und der Rest
    wäre wieder Code — die Lücke, gegen die die ganze Konstruktion gebaut ist.
    """
    ergebnis = emit.wortlaut('ende" #eval("6*7") \\ x', block=True)
    assert '\\"' in ergebnis
    assert "\\\\" in ergebnis
    # Nach dem Schutz steht kein unmaskiertes Anführungszeichen mehr im Inhalt.
    innen = ergebnis[len('#codeblock(raw("'):-len('", block: true))')]
    assert '"' not in innen.replace('\\"', "")


def test_gegenprobe_der_pruefung_oben():
    """Ein Emitter, der Markup erzeugt, MUSS durch die Prüfungen fallen.

    Ohne diesen Test belegte `test_anweisung_wird_zur_zeichenkette…` nur, dass
    irgendein String vorkommt.
    """
    unsicher = f"#codeblock[{GEFAEHRLICH[2]}]"
    assert not unsicher.startswith('#codeblock(raw("')
    assert "#codeblock[" in unsicher


# ── Die Sicherheitsgrenze, Ebene 2: das fertige PDF ─────────────────────────

@pytest.mark.parametrize("zeile,verraeter", [
    ('#eval("6*7")', "42"),
])
def test_am_pdf_wird_nichts_ausgewertet(tmp_path, zeile, verraeter):
    """Der eigentliche Beweis: Typst bekommt die Datei und tut nichts damit.

    Gegenprobe dazu steht in `test_gegenbeweis.py` — dort wird der Emitter
    sabotiert, und dann erscheint `42` wirklich. Ohne sie wüsste dieser Test
    nur, dass 42 nicht dasteht.
    """
    import pdfplumber

    brief = tmp_path / "b.md"
    brief.write_text(f"{KOPF}der Auszug lautet:\n\n```\n{zeile}\n```\n", encoding="utf-8")
    lauf = subprocess.run(
        [sys.executable, str(SKILL / "scripts" / "falzmarke.py"),
         "render", str(brief), "-o", str(tmp_path / "b.pdf")],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert (tmp_path / "b.pdf").exists(), lauf.stderr[:400]
    with pdfplumber.open(str(tmp_path / "b.pdf")) as dokument:
        text = dokument.pages[0].extract_text()
    assert zeile in text.replace("\n", ""), f"die Zeile fehlt im PDF:\n{text[:400]}"
    assert verraeter not in text, f"ausgewertet! {verraeter!r} steht im PDF"


# ── Was der Satz mit einer zu langen Zeile tut (Issue #173) ─────────────────

def test_eine_zu_lange_auszugszeile_wird_vom_satz_umbrochen(tmp_path):
    """Der unbequeme Befund, festgehalten statt behauptet.

    Bis Issue #173 stand an vier Stellen im Repository, ein wortgetreuer Auszug
    werde nicht umbrochen. Das gilt nur für eine Zeile OHNE Leerzeichen: Die
    läuft aus dem Satzspiegel, und `verify` meldet sie. Hat die Zeile ein
    Leerzeichen, bricht Typst sie dort um — still, und das PDF hält danach alle
    Maße ein.

    Acht Wege, Typst das abzugewöhnen, sind an #173 gemessen; nur geschützte
    Leerzeichen wirken, und die ändern die Zeichen selbst. Der Umbruch bleibt
    also — gemeldet wird er von `lint.pruefe_body()`, vor dem Rendern.

    Dieser Test hält fest, was das Satzsystem heute tut. Bringt eine spätere
    Fassung von Typst es fertig, fällt er auf, statt dass die Prüfung an der
    Quelle unbemerkt überflüssig wird.
    """
    import pdfplumber

    protokoll = ("06:14:02 anlage=4711 status=betriebsbereit ok "
                 "last=0.62 temperatur=21.4 druck=4.8")
    assert len(protokoll) == 81

    brief = tmp_path / "b.md"
    brief.write_text(f"{KOPF}der Auszug lautet:\n\n```\n{protokoll}\n```\n",
                     encoding="utf-8")
    subprocess.run(
        [sys.executable, str(SKILL / "scripts" / "falzmarke.py"),
         "render", str(brief), "-o", str(tmp_path / "b.pdf")],
        capture_output=True, text=True, encoding="utf-8",
    )
    with pdfplumber.open(str(tmp_path / "b.pdf")) as dokument:
        zeilen = dokument.pages[0].extract_text().splitlines()

    assert protokoll not in zeilen, (
        "die Zeile steht ungeteilt im PDF — dann bricht Typst nicht mehr um, "
        "und die Prüfung in lint.pruefe_body() beschreibt einen Fall, den es "
        "nicht mehr gibt")
    assert any(z.startswith("temperatur=") for z in zeilen), (
        f"erwartet war ein Umbruch vor „temperatur=“:\n{zeilen}")


def test_dieselbe_laenge_ohne_leerzeichen_bleibt_eine_zeile(tmp_path):
    """Das Gegenstück: ohne Umbruchstelle bleibt die Zeile ganz — und läuft
    dafür aus dem Satzspiegel, wo `verify` sie fängt. Ohne diesen Fall wüsste
    der Test oben nicht, ob das Leerzeichen den Unterschied macht."""
    import pdfplumber

    zeile = "x" * 81
    brief = tmp_path / "b.md"
    brief.write_text(f"{KOPF}der Auszug lautet:\n\n```\n{zeile}\n```\n", encoding="utf-8")
    subprocess.run(
        [sys.executable, str(SKILL / "scripts" / "falzmarke.py"),
         "render", str(brief), "-o", str(tmp_path / "b.pdf")],
        capture_output=True, text=True, encoding="utf-8",
    )
    with pdfplumber.open(str(tmp_path / "b.pdf")) as dokument:
        zeilen = dokument.pages[0].extract_text().splitlines()
    assert zeile in zeilen, f"die Zeile steht nicht ungeteilt im PDF:\n{zeilen}"
