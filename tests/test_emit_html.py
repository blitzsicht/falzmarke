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
    # Die Hülle trägt seit #289 `fm-t` wie jeder andere Block — daran erkennt
    # die Prüfung, was von hier stammt und was aus fremdem HTML.
    assert '<ul class="fm-t" style=' in _setze("- eins\n- zwei\n")
    nummeriert = _setze("1. eins\n2. zwei\n")
    assert '<ol class="fm-t" style=' in nummeriert, \
        "start=1 ist die Vorgabe und gehört nicht in den Quelltext"
    assert '<ol class="fm-t" start="3"' in _setze("3. drei\n4. vier\n")


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


def _kursiv_im_klassischen_outlook(stapel: str) -> bool:
    return "segoe ui" in stapel.lower()


def test_die_schriftfolge_meidet_segoe_ui():
    """#307: Im klassischen Outlook für Mac setzt der Editor „Segoe UI" durch
    einen kursiven Schnitt — die Schrift ist auf dem Mac nicht installiert.
    Gemessen am 13.09.2026 in einem Entwurf mit vier Schriftfolgen: beide mit
    Segoe kursiv, beide ohne normal."""
    assert not _kursiv_im_klassischen_outlook(html.SCHRIFTSTAPEL), html.SCHRIFTSTAPEL


def test_gegenprobe_die_pruefung_erkennt_segoe():
    assert _kursiv_im_klassischen_outlook("-apple-system, 'Segoe UI', Arial, sans-serif")


def test_dokument_hat_sprache_und_farbschema():
    seite = html.dokument(_setze("Ein Satz.\n"))
    assert '<html lang="de">' in seite
    assert '<meta name="color-scheme" content="light dark">' in seite
    # Seit #289 deckelt nichts mehr die Breite — weder der Umschlag (#264) noch
    # der Absatz. Die 640 px hatten keine Quelle.
    assert "max-width" not in seite, seite


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


# ── Der Abstand unter einer Liste (#322, Befund 5) ──────────────────────────
#
# Am 14.09.2026 stand in beiden Kundenmails zwischen dem letzten Listenpunkt und
# dem nächsten Absatz etwa der Platz von zwei Leerzeilen. Vermutet war der Emitter;
# gemessen ist hier, was er SELBST an Abstand unter das Listenende setzt.
#
# **Was gemessen wird und was nicht.** Gemessen wird der Wert im gesetzten HTML:
# der untere Abstand des letzten `<li>` plus der der Liste. Ein Browser fasst die
# beiden zusammen (der größere gilt), die Word-Engine des klassischen Outlook
# addiert sie — dass sie das tut, ist hier NICHT gemessen (? ungeprüft, kein
# Outlook in der Prüfumgebung). Der Test verlangt deshalb das, was in beiden
# Fällen stimmt: Unter dem Listenende steht nicht mehr Platz als unter einem
# Absatz — auch dann nicht, wenn ein Client die Ränder addiert.
#
# Wer stattdessen zeigt, dass der Abstand gewollt ist, und ihn mit Messwert
# dokumentiert (AC 5 lässt beides zu), löscht diesen Test mit der Begründung im
# Commit — und lässt ihn nicht stillschweigend rot stehen.

def _unten(tag: str) -> float:
    """Der untere Außenabstand aus dem `style` eines Tags, in Pixeln.

    Versteht `margin-bottom` und die Kurzform mit ein bis vier Werten. Fehlt die
    Angabe, ist es 0 — der Standardwert der Mail-Clients ist hier ohne Belang,
    weil der Emitter an jedem Block ausdrücklich `margin` setzt.
    """
    stil = re.search(r'style="([^"]*)"', tag).group(1)
    einzeln = re.search(r"(?:^|;)\s*margin-bottom:\s*([\d.]+)", stil)
    if einzeln:
        return float(einzeln.group(1))
    kurz = re.search(r"(?:^|;)\s*margin:\s*([^;]+)", stil)
    if not kurz:
        return 0.0
    werte = [float(w) for w in re.findall(r"[\d.]+", kurz.group(1))]
    if not werte:
        return 0.0
    return werte[{1: 0, 2: 0, 3: 2, 4: 2}[min(len(werte), 4)]]


def _platz_unter_der_liste(ausgabe: str, huelle: str) -> float:
    """Was unter dem letzten Punkt steht: sein Abstand plus der der Liste."""
    liste = re.findall(rf"<{huelle}\b[^>]*>", ausgabe)[0]
    letzter_punkt = re.findall(r"<li\b[^>]*>", ausgabe)[-1]
    return _unten(liste) + _unten(letzter_punkt)


@pytest.mark.parametrize("huelle, quelle", [
    ("ul", "- eins\n- zwei\n- drei\n"),
    ("ol", "1. eins\n2. zwei\n3. drei\n"),
], ids=["Aufzählung", "Nummerierung"])
def test_unter_dem_listenende_steht_nicht_mehr_platz_als_unter_einem_absatz(huelle, quelle):
    ausgabe = _setze(quelle)

    # Kontrollen zuerst: Die Messung muss zwei Dinge können, sonst sagt ihr Wert
    # nichts. Sie muss einen Absatz mit seinem tatsächlichen Abstand lesen
    # (positiv, und nicht 0 nur weil die Regex ins Leere greift), und sie muss
    # die Kurz- und Langform unterscheiden.
    absatz = re.findall(r"<p\b[^>]*>", _setze("Ein Satz.\n"))[0]
    assert _unten(absatz) == float(html.ABSTAND_UNTEN.removesuffix("px")) > 0
    assert _unten('<li style="margin: 0 0 4px;">') == 4
    assert _unten('<li style="margin: 0;">') == 0
    assert _unten('<li style="margin: 3px 5px;">') == 3
    assert _unten('<li style="margin-bottom: 7px;">') == 7

    platz = _platz_unter_der_liste(ausgabe, huelle)
    erlaubt = _unten(absatz)
    assert platz <= erlaubt, (
        f"Unter dem letzten Punkt stehen {platz:g} px (Punkt + Liste), unter einem "
        f"Absatz {erlaubt:g} px — in einem Client, der die Ränder addiert, ist das "
        "mehr Leerraum als zwischen zwei Absätzen")

    # Und nicht dadurch erkauft, dass der Abstand zwischen den Punkten verschwindet:
    # Nur der LETZTE Punkt gibt den seinen ab.
    punkte = re.findall(r"<li\b[^>]*>", ausgabe)
    assert len(punkte) == 3
    assert all(_unten(p) > 0 for p in punkte[:-1]), (
        "die Punkte untereinander haben keinen Abstand mehr")
