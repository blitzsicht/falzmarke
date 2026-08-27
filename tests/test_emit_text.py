"""Der Text-Emitter und die Faltung nach RFC 3676.

Die Faltung wird nicht als Ausgabe geprüft, sondern gegen ihre Umkehrung: Erst
der Rundlauf zeigt, ob die Faltmarken tragen. Dass der Rundlauf überhaupt etwas
misst, steht als eigene Prüfung darunter — ein Rundlauf über Text, der nie
gefaltet wurde, ist trivial grün.
"""

from __future__ import annotations

import pytest

from falzmarke import baum
from falzmarke import emit_text as text
from falzmarke import markdown as md
from conftest import BEISPIELE


def _setze(quelle: str) -> str:
    return text.setze(md.lies(quelle))


def _brieftext(pfad) -> str:
    return pfad.read_text(encoding="utf-8").split("---", 2)[2]


# ── Der Wortlaut bleibt ─────────────────────────────────────────────────────

@pytest.mark.parametrize("quelle, erwartet", [
    ("Ein Satz.\n", "Ein Satz.\n"),
    ("Ein **fetter** Satz.\n", "Ein fetter Satz.\n"),
    ("Ein *betonter* Satz.\n", "Ein betonter Satz.\n"),
    ("- eins\n- zwei\n", "- eins\n- zwei\n"),
    ("3. drei\n4. vier\n", "3. drei\n4. vier\n"),
])
def test_setzt_ohne_markup(quelle, erwartet):
    """Fett und kursiv verschwinden ersatzlos — ein Sternchen im Klartext ist
    keine Auszeichnung, sondern ein Zeichen, das jemand mitliest."""
    assert _setze(quelle) == erwartet


def test_verschachtelte_liste_wird_eingerueckt():
    ausgabe = _setze("- eins\n- zwei\n\n  - tiefer\n  - noch\n")
    assert "\n  - tiefer" in ausgabe, ausgabe


def test_tabelle_richtet_aus_und_trennt_den_kopf():
    ausgabe = _setze("| Ware | Preis |\n|:--|--:|\n| Stift | 1,20 |\n")
    zeilen = ausgabe.rstrip("\n").split("\n")
    assert zeilen[0].startswith("Ware "), zeilen
    assert set(zeilen[1]) <= set("-|"), "unter dem Kopf fehlt die Strichzeile"
    assert zeilen[2].endswith("1,20"), "rechtsbündige Spalte ist nicht ausgerichtet"
    assert len({len(z) for z in zeilen}) == 1, "Spalten stehen nicht untereinander"


# ── Faltung: geprüft gegen ihre Umkehrung ───────────────────────────────────

@pytest.mark.parametrize("delsp", [True, False], ids=["delsp=yes", "delsp=no"])
@pytest.mark.parametrize("beispiel", BEISPIELE, ids=lambda p: p.stem)
def test_rundlauf_ueber_alle_beispiele(beispiel, delsp):
    klar = _setze(_brieftext(beispiel))
    gefaltet = text.falte(klar, delsp=delsp)
    assert text.entfalte(gefaltet, delsp=delsp) == klar


def test_der_rundlauf_misst_ueberhaupt_etwas():
    """Gegenprobe zum Rundlauf: Wenn nichts gefaltet wurde, ist er trivial grün.

    Mindestens ein Beispiel muss also tatsächlich eine Faltmarke bekommen —
    sonst prüft die Parametrisierung oben nur, dass `entfalte` den Text
    durchreicht.
    """
    gefaltet = [
        text.falte(_setze(_brieftext(b))) for b in BEISPIELE
    ]
    marken = sum(z.endswith(" ") for g in gefaltet for z in g.split("\n"))
    assert marken > 0, "kein einziger weicher Umbruch — der Rundlauf belegt nichts"


def test_falsche_faltmarke_faellt_im_rundlauf_auf():
    """Gegenprobe: eine Faltung, die bei delsp die zweite Marke vergisst, muss
    den Rundlauf brechen. Sonst misst der Rundlauf die Marke gar nicht."""
    klar = _setze("Wort " * 40 + "Ende.\n")
    gefaltet = text.falte(klar, delsp=True)
    assert "  \n" in gefaltet, "die Sabotage kann nicht greifen — es gibt keine delsp-Marke"
    sabotiert = gefaltet.replace("  \n", " \n")
    assert sabotiert != gefaltet, "Sabotage wirkungslos"
    assert text.entfalte(sabotiert, delsp=True) != klar


def test_feste_zeilen_werden_nicht_gefaltet():
    """Tabellen und Listenpunkte tragen ihre Bedeutung in der Form. Eine weiche
    Marke darin würde beim Entfalten die Ausrichtung in den Satz ziehen."""
    lang = "| " + " | ".join(f"Spalte{n}" for n in range(12)) + " |"
    quelle = ("| " + " | ".join(f"Spalte{n}" for n in range(12)) + " |\n"
              + "|" + "--|" * 12 + "\n"
              + "| " + " | ".join(str(n) for n in range(12)) + " |\n")
    gefaltet = text.falte(_setze(quelle))
    for zeile in gefaltet.split("\n"):
        if " | " in zeile:
            assert len(zeile) > text.BREITE, "der Fall misst nichts — die Zeile ist zu kurz"
            assert not zeile.endswith(" "), f"Tabellenzeile wurde gefaltet: {zeile!r}"


def test_space_stuffing_und_seine_umkehrung():
    """Eine Zeile, die mit Leerzeichen oder '>' beginnt, sähe sonst wie ein
    Zitat aus. Das gestuffte Leerzeichen muss beim Entfalten wieder weg."""
    klar = "- eins\n- zwei\n\n  - tiefer\n  - noch\n"
    gefaltet = text.falte(klar)
    assert "   - tiefer" in gefaltet, "nicht gestufft"
    assert text.entfalte(gefaltet) == klar


def test_breite_wird_eingehalten():
    klar = _setze("Wort " * 60 + "Ende.\n")
    for zeile in text.falte(klar).split("\n"):
        assert len(zeile.rstrip()) <= text.BREITE, repr(zeile)


# ── Vollständigkeit ─────────────────────────────────────────────────────────

def test_emitter_kennt_jeden_knoten():
    beispiele = {
        baum.Text: baum.Text("x"),
        baum.Umbruch: baum.Umbruch(),
        baum.Stark: baum.Stark((baum.Text("x"),)),
        baum.Betont: baum.Betont((baum.Text("x"),)),
        baum.Absatz: baum.Absatz((baum.Text("x"),)),
        baum.Liste: baum.Liste(((baum.Text("a"),), (baum.Text("b"),))),
        baum.Tabelle: baum.Tabelle((((baum.Text("a"),),),), (None,)),
    }
    fehlend = [k.__name__ for k in baum.KNOTEN if k not in beispiele]
    assert not fehlend, f"Diese Prüfung kennt {fehlend} nicht — baum.KNOTEN ist gewachsen"

    inline = (baum.Text, baum.Umbruch, baum.Stark, baum.Betont)
    for klasse, knoten in beispiele.items():
        gesetzt = text._inline(knoten) if klasse in inline else text._block(knoten)
        # Nicht `.strip()` wie bei Typst und HTML: Im Klartext ist der Umbruch
        # ein Zeilenumbruch und sonst nichts — er würde weggestrippt und der
        # Test bestünde auf einer Ausgabe, die es hier nicht geben kann.
        assert gesetzt != "", f"{klasse.__name__} ergibt nichts"


def test_unbekannter_knoten_bricht_ab():
    class Erfunden:
        pass

    with pytest.raises(TypeError, match="Text-Emitter"):
        text._block(Erfunden())
