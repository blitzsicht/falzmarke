"""Der HTML-Emitter setzt denselben Baum wie der Typst-Emitter.

Zwei Sorten Prüfung stehen hier. Die eine hält den Wortlaut fest, damit ein
späterer Eingriff nicht unbemerkt anders setzt. Die andere hält die Grenze aus
ADR 0034 — und die hat ihre Gegenproben in `test_gegenbeweis.py`, weil eine
Grenze, die nie anschlägt, keine ist.
"""

from __future__ import annotations

import re

import pytest

from falzmarke import baum
from falzmarke import emit_html as html
from falzmarke import markdown as md
from conftest import BEISPIELE, BEISPIELE_10


def _setze(quelle: str) -> str:
    return html.setze(md.lies(quelle))


# ── Der Wortlaut bleibt ─────────────────────────────────────────────────────

@pytest.mark.parametrize("quelle, erwartet", [
    ("Ein Satz.\n", "Ein Satz."),
    ("Ein **fetter** Satz.\n", "Ein <strong>fetter</strong> Satz."),
    ("Ein *betonter* Satz.\n", "Ein <em>betonter</em> Satz."),
])
def test_absatz_setzt_wie_erwartet(quelle, erwartet):
    ausgabe = _setze(quelle)
    # `class=` steht seit dem dunklen Farbschema davor — ohne sie bliebe der
    # Absatz hell, weil der Inline-Stil gegen die Medienabfrage gewinnt.
    assert ausgabe.startswith("<p class=") and " style=" in ausgabe
    assert f'">{erwartet}</p>' in ausgabe


def test_liste_und_nummerierung():
    assert "<ul style=" in _setze("- eins\n- zwei\n")
    nummeriert = _setze("1. eins\n2. zwei\n")
    assert "<ol style=" in nummeriert, "start=1 ist die Vorgabe und gehört nicht in den Quelltext"
    assert '<ol start="3"' in _setze("3. drei\n4. vier\n")


def test_verschachtelte_liste_steckt_im_punkt():
    """Eine Unterliste gehört in ihren `<li>`, nicht daneben — sonst zeigt sie
    kein Mail-Client eingerückt an."""
    ausgabe = _setze("- eins\n- zwei\n\n  - tiefer\n  - noch\n")
    assert re.search(r"<li[^>]*>zwei<ul", ausgabe), ausgabe


def test_tabelle_traegt_ausrichtung_und_rahmen():
    ausgabe = _setze("| A | B |\n|:--|--:|\n| 1 | 2 |\n")
    assert "<th class=" in ausgabe and "font-weight: 600" in ausgabe
    assert "text-align: left" in ausgabe and "text-align: right" in ausgabe
    assert f"1px solid {html.RAHMEN}" in ausgabe


# ── Die Sicherheitsgrenze ───────────────────────────────────────────────────

def test_sonderzeichen_werden_escaped():
    """`<` und `>` lehnt der Dialekt schon ab; `&` und Anführungszeichen nicht.

    Das Escaping ist deshalb die zweite Sperre, nicht die einzige — und es muss
    greifen, auch wenn die erste hält.
    """
    ausgabe = _setze("Weber & Sohn, a > b.\n")
    assert "&amp;" in ausgabe and "&gt;" in ausgabe
    assert " & " not in ausgabe


def test_html_aus_der_quelle_kommt_gar_nicht_erst_an():
    with pytest.raises(md.MarkdownFehler):
        md.lies("Ein <b>Versuch</b>.\n")


def test_stil_steht_an_jedem_block_nicht_nur_am_container():
    """Mehrere Clients hängen den Rumpf in ihre eigene Umgebung; was nur am
    Container steht, ist dann weg."""
    ausgabe = _setze("Ein Satz.\n\n- eins\n- zwei\n")
    bloecke = re.findall(r"<(?:p|ul|ol|li|table|th|td)\b[^>]*>", ausgabe)
    assert bloecke, "keine Blockelemente gefunden — der Test misst nichts"
    ohne = [b for b in bloecke if html.SCHRIFTSTAPEL not in b]
    assert not ohne, f"ohne eigenen Stil: {ohne}"


def test_dokument_hat_sprache_und_farbschema():
    seite = html.dokument(_setze("Ein Satz.\n"))
    assert '<html lang="de">' in seite
    assert '<meta name="color-scheme" content="light dark">' in seite
    assert f"max-width: {html.BREITE_MAX}" in seite


@pytest.mark.parametrize("beispiel", BEISPIELE_10, ids=lambda p: p.stem)
def test_beispiele_setzen_ohne_verstoss(beispiel):
    quelle = beispiel.read_text(encoding="utf-8").split("---", 2)[2]
    seite = html.dokument(html.setze(md.lies(quelle)))
    assert html.verstoesse(seite) == []


# ── Vollständigkeit ─────────────────────────────────────────────────────────

def test_emitter_kennt_jeden_knoten():
    """Wächst `baum.KNOTEN`, wird dieser Test rot — nicht die Mail still leer.

    Dasselbe Muster wie in `test_baum.py`; es steht doppelt, weil ein zweiter
    Emitter dieselbe Lücke haben kann wie der erste.
    """
    beispiele = {
        baum.Text: baum.Text("x"),
        baum.Umbruch: baum.Umbruch(),
        baum.Stark: baum.Stark((baum.Text("x"),)),
        baum.Betont: baum.Betont((baum.Text("x"),)),
        baum.Absatz: baum.Absatz((baum.Text("x"),)),
        baum.Liste: baum.Liste(((baum.Text("a"),), (baum.Text("b"),))),
        baum.Tabelle: baum.Tabelle((((baum.Text("a"),),),), (None,)),
    }
    fehlend = [k.__name__ for k in baum.KNOTEN
               if k not in beispiele and k not in baum.NUR_BRIEF]
    assert not fehlend, f"Diese Prüfung kennt {fehlend} nicht — baum.KNOTEN ist gewachsen"

    inline = (baum.Text, baum.Umbruch, baum.Stark, baum.Betont)
    for klasse, knoten in beispiele.items():
        gesetzt = html._inline(knoten) if klasse in inline else html._block(knoten)
        assert gesetzt.strip(), f"{klasse.__name__} ergibt nichts"


def test_unbekannter_knoten_bricht_ab():
    class Erfunden:
        pass

    with pytest.raises(TypeError, match="HTML-Emitter"):
        html._block(Erfunden())
