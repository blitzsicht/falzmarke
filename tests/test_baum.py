"""Der Baum zwischen Markdown und Ausgabe.

Vorher gab `markdown.py` fertigen Typst-Code zurück und rief `emit` mitten in
der Prüfung auf. Damit ließ sich keine zweite Ausgabeform daneben stellen, ohne
die Prüfung zu verdoppeln — und eine verdoppelte Prüfung ist eine, die
auseinanderläuft.

Zwei Eigenschaften tragen den Umbau, und beide werden hier gehalten:

1. **Der Baum kennt keine Zielsprache.** Steht Typst darin, ist die Trennung
   nur behauptet.
2. **Der Emitter übergeht nichts.** Ein Knoten, den er nicht kennt, muss
   auffallen — sonst landet er als Lücke in einem Brief, den jemand abschickt.

Dass der Umbau die Ausgabe nicht verändert hat, ist beim Bauen gegen alle zehn
Beispiele geprüft worden: byteidentisch. `test_alle_konstrukte_setzen_wie_zuvor`
hält den Wortlaut für die Konstrukte des Dialekts fest, damit es so bleibt.
"""

from __future__ import annotations

import sys

import pytest

from conftest import REPO

sys.path.insert(0, str(REPO / "skill"))

from falzmarke import baum, emit                                 # noqa: E402
from falzmarke import markdown as md                             # noqa: E402


# ── Der Baum ────────────────────────────────────────────────────────────────

def test_lies_gibt_knoten_zurueck_keine_zeichenketten():
    knoten = md.lies("Ein **Satz**.\n")
    assert isinstance(knoten, tuple) and knoten
    assert isinstance(knoten[0], baum.Absatz), type(knoten[0])


def test_im_baum_steht_kein_typst():
    """Sonst wäre die Trennung nur behauptet.

    Geprüft wird an einem Text, der alle Konstrukte benutzt: Fände sich
    irgendwo `#text(`, `#par[` oder `#table(`, hätte ein Teil der Umsetzung den
    Emitter doch noch im Bauch.
    """
    quelle = (
        "Ein **fetter** und *betonter* Satz.\n\n"
        "- erster Punkt\n- zweiter Punkt\n\n"
        "| a | b |\n|---|---|\n| 1 | 2 |\n"
    )
    text = repr(md.lies(quelle))
    for spur in ("#text(", "#par[", "#strong[", "#emph[", "#list(", "#table("):
        assert spur not in text, f"Typst-Spur im Baum: {spur}"


def test_der_weiche_umbruch_bleibt_von_der_typografie_verschont():
    """Ein weicher Umbruch ist ein Leerzeichen — kein typografisches Zeichen."""
    knoten = md.lies("erste Zeile\nzweite Zeile\n")
    texte = [k for k in knoten[0].kinder if isinstance(k, baum.Text)]
    weich = [t for t in texte if t.inhalt == " "]
    assert weich, "kein weicher Umbruch im Baum"
    assert weich[0].typografie is False


def test_die_ablehnung_geschieht_beim_lesen_nicht_beim_setzen():
    """Wer den Baum bekommt, hat eine geprüfte Quelle.

    Sonst müsste jeder Emitter dieselben Ablehnungen noch einmal treffen — und
    der zweite würde eine davon vergessen.
    """
    with pytest.raises(md.MarkdownFehler):
        md.lies("# Überschrift\n")
    with pytest.raises(md.MarkdownFehler):
        md.lies("> Zitat\n")


# ── Der Emitter ─────────────────────────────────────────────────────────────

def test_der_emitter_uebergeht_keinen_unbekannten_knoten():
    """Gegenprobe: Ein stilles Übergehen wäre eine Lücke im fertigen Brief.

    Ohne diese Prüfung könnte jemand baum.py um einen Knoten erweitern, den
    emit.py nicht kennt — und der Brief käme ohne diesen Absatz heraus, ohne
    dass irgendetwas rot würde.
    """
    class Fremd:
        pass

    with pytest.raises(TypeError) as fehler:
        emit.setze((Fremd(),))
    assert "Fremd" in str(fehler.value)


def test_jeder_knoten_aus_baum_wird_vom_emitter_gesetzt():
    """baum.KNOTEN ist die Liste des Erlaubten — der Emitter muss sie abdecken."""
    beispiele = {
        baum.Text: baum.Text("x"),
        baum.Umbruch: baum.Umbruch(),
        baum.Stark: baum.Stark((baum.Text("x"),)),
        baum.Betont: baum.Betont((baum.Text("x"),)),
        baum.Absatz: baum.Absatz((baum.Text("x"),)),
        baum.Ueberschrift: baum.Ueberschrift(1, (baum.Text("x"),)),
        baum.Liste: baum.Liste(((baum.Text("a"),), (baum.Text("b"),))),
        baum.Tabelle: baum.Tabelle((((baum.Text("a"),),),), (None,)),
    }
    fehlend = [k.__name__ for k in baum.KNOTEN if k not in beispiele]
    assert not fehlend, f"Diese Prüfung kennt {fehlend} nicht — baum.KNOTEN ist gewachsen"

    for klasse, knoten in beispiele.items():
        gesetzt = emit._inline(knoten) if klasse in (
            baum.Text, baum.Umbruch, baum.Stark, baum.Betont) else emit._block(knoten)
        assert gesetzt.strip(), f"{klasse.__name__} ergibt nichts"


# ── Der Wortlaut bleibt ─────────────────────────────────────────────────────

@pytest.mark.parametrize("quelle, erwartet", [
    ("Ein Satz.\n", '#par[#text("Ein Satz.")]\n'),
    ("Ein **fetter** Satz.\n",
     '#par[#text("Ein ")#strong[#text("fetter")]#text(" Satz.")]\n'),
    ("Ein *betonter* Satz.\n",
     '#par[#text("Ein ")#emph[#text("betonter")]#text(" Satz.")]\n'),
    ("- eins\n- zwei\n", '#list([#text("eins")], [#text("zwei")])\n'),
    ("1. eins\n2. zwei\n", '#enum(start: 1, [#text("eins")], [#text("zwei")])\n'),
])
def test_alle_konstrukte_setzen_wie_zuvor(quelle, erwartet):
    """Der Umbau war eine Umstellung der Struktur, keine der Ausgabe.

    Beim Bauen gegen alle zehn Beispiele geprüft: byteidentisch. Diese Prüfung
    hält den Wortlaut für die einzelnen Konstrukte fest, damit eine künftige
    Änderung am Emitter nicht unbemerkt anders setzt.
    """
    assert md.konvertiere(quelle) == erwartet


def test_konvertiere_ist_lesen_und_setzen():
    quelle = "Ein **Satz** mit *Betonung*.\n\n- eins\n- zwei\n"
    assert md.konvertiere(quelle) == emit.setze(md.lies(quelle))
