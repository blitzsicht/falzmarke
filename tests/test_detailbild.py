"""Die Schaufensterbilder der Falzmarke — zeigen sie, was sie behaupten?

Anlass (Issue #13): Auf keinem Vorschaubild war die Falzmarke zu erkennen. Ein
Bild, das sie zeigen soll, hat zwei Arten, still falsch zu werden:

1. Die Zahl darauf veraltet, weil jemand den Sollwert aendert und das Bild
   nicht neu baut. Dagegen steht `detailbild.json` neben den PNGs und wird hier
   gegen einen frischen Messlauf gehalten.
2. Der Ausschnitt zeigt gar nichts — er liegt neben der Marke, ist zu klein
   oder zu blass. Ein solches Bild sieht genauso ordentlich aus wie ein
   richtiges. Dagegen steht die Gegenprobe: Derselbe Ausschnitt wird aus einem
   absichtlich verschobenen Layout geschnitten und muss sich messbar
   unterscheiden.

Und weil eine Pruefung, die nie rot werden kann, kein Nachweis ist, misst
`test_unterschied_kommt_von_der_marke` dieselbe Differenz an einer leeren
Stelle des Blattes. Dort MUSS sie verschwinden — sonst zaehlte sie nur
Rauschen, und die Gegenprobe waere gruen, ohne je die Marke gesehen zu haben.
"""

from __future__ import annotations

import json
import re
import sys

import pytest

from conftest import REPO

sys.path.insert(0, str(REPO / "scripts"))

import detailbild                                                # noqa: E402

BILDER = {
    "falzmarke-detail.png": "detail",
    "falzmarke-gegenprobe.gif": "wechsel",
}

#: Das Fertigkriterium je Dateiformat. Ein abgeschnittenes Bild ist an der
#: Groesse nicht zu erkennen — PNG endet auf IEND, GIF auf das Semikolon.
SCHLUSS = {
    ".png": bytes.fromhex("0000000049454e44ae426082"),
    ".gif": b";",
}


@pytest.fixture(scope="module")
def gebaut():
    """Ein Lauf fuer alle Pruefungen — er rendert zweimal bei 600 ppi."""
    return detailbild.baue()


def _markenzeile(bild) -> int:
    """Die Bildzeile der Falzmarke, gemessen innerhalb des Ausschnittrahmens.

    Zwei Fallen, beide beim ersten Anlauf hineingetappt: Die **Rahmenlinien**
    des Ausschnitts sind über die volle Breite dunkel und schlagen jede Marke;
    die **Überschrift** darüber ebenso. Gesucht wird deshalb nur zwischen den
    beiden durchgehenden Linien, und nur nach fast schwarzen Pixeln — die
    Marke ist Tinte (Grauwert um 28), Rahmen und grüne Schrift liegen darüber.
    """
    grau = bild.convert("L")
    breite, hoehe = grau.size
    werte = list(grau.tobytes())

    def dunkel(y: int, schwelle: int) -> int:
        return sum(1 for x in werte[y * breite:(y + 1) * breite] if x < schwelle)

    # Die Rahmenlinien: durchgehend, also fast so breit wie das Bild.
    linien = [y for y in range(hoehe) if dunkel(y, 130) > breite * 0.8]
    assert len(linien) >= 2, "kein Ausschnittrahmen gefunden — misst der Test das richtige Bild?"
    oben, unten = linien[0] + 2, linien[-1] - 2

    innen = range(oben, unten)
    treffer = max(innen, key=lambda y: dunkel(y, 60))
    assert dunkel(treffer, 60) > 50, "im Rahmen ist keine Marke zu finden"
    return treffer


def _abweichende_pixel(links, rechts, schwelle: int = 40) -> int:
    """Wie viele Pixel unterscheiden sich sichtbar?"""
    from PIL import ImageChops

    unterschied = ImageChops.difference(links.convert("L"), rechts.convert("L"))
    return sum(anzahl for wert, anzahl in enumerate(unterschied.histogram())
               if wert >= schwelle)


def test_zahl_im_bild_stammt_aus_dem_lauf(gebaut):
    """Der Wert neben den Bildern muss der gemessene sein, nicht ein erinnerter."""
    beleg = detailbild.BELEG
    assert beleg.is_file(), (
        f"{beleg.relative_to(REPO)} fehlt — einmal `python3 scripts/detailbild.py` laufen lassen"
    )
    gespeichert = json.loads(beleg.read_text(encoding="utf-8"))
    frisch = detailbild.beleg(gebaut["mess"])
    assert gespeichert == frisch, (
        "Die Bilder zeigen eine Zahl, die zum heutigen Lauf nicht mehr passt.\n"
        "Neu bauen: python3 scripts/detailbild.py"
    )


def test_ausschnitt_zeigt_die_verschobene_marke(gebaut):
    """Die Gegenprobe: verschobene Marke, sichtbar anderer Ausschnitt."""
    abweichend = _abweichende_pixel(gebaut["ausschnitt_richtig"], gebaut["ausschnitt_falsch"])
    flaeche = gebaut["ausschnitt_richtig"].width * gebaut["ausschnitt_richtig"].height
    assert abweichend > 500, (
        f"Nur {abweichend} von {flaeche} Pixeln unterscheiden sich, obwohl die Marke um "
        f"{detailbild.SABOTAGE_MM - gebaut['mess']['soll']:.0f} mm verschoben ist.\n"
        "Der Ausschnitt zeigt die Marke also nicht — er liegt daneben oder ist zu klein."
    )


def test_unterschied_kommt_von_der_marke(gebaut):
    """Gegenbeweis zur Gegenprobe: an leerer Stelle darf nichts anschlagen.

    Dasselbe Fenster, nur 60 mm weiter oben — dort liegt im Heftrand keine
    Marke. Faende die Messung auch hier einen Unterschied, waere
    `test_ausschnitt_zeigt_die_verschobene_marke` gruen, ohne etwas zu belegen.
    """
    x, y, breite, hoehe = detailbild.FENSTER_MM
    leer = (x, y - 60.0, breite, hoehe)
    seite, seite_falsch = gebaut["seiten"]
    zielhoehe = gebaut["ausschnitt_richtig"].height
    abweichend = _abweichende_pixel(
        detailbild._ausschnitt(seite, leer, zielhoehe)[0],
        detailbild._ausschnitt(seite_falsch, leer, zielhoehe)[0],
    )
    assert abweichend == 0, (
        f"{abweichend} Pixel unterscheiden sich an einer Stelle ohne Marke "
        f"(y {leer[1]:.0f}–{leer[1] + hoehe:.0f} mm). Die Gegenprobe misst dann "
        "nicht die Marke, sondern Rauschen."
    )


def test_die_bilder_liegen_vollstaendig_im_repo():
    """Ein abgeschnittenes PNG ist an der Dateigroesse nicht zu erkennen.

    Der IEND-Chunk ist das Fertigkriterium, nicht die Byte-Zahl — der Grund
    steht in scripts/marke.sh, wo Chrome einmal vor dem Laden der Bilder
    ausgeloest hat und die Groessenpruefung zufrieden war.
    """
    for name in BILDER:
        pfad = REPO / "docs" / "assets" / "demo" / name
        assert pfad.is_file(), f"{name} fehlt — python3 scripts/detailbild.py"
        schluss = SCHLUSS[pfad.suffix]
        assert pfad.read_bytes()[-len(schluss):] == schluss, (
            f"{name} endet nicht auf das Schlusszeichen seines Formats — "
            "die Datei ist unvollständig."
        )


def test_beide_bilder_stehen_mit_alternativtext_in_der_readme():
    """Ein Bild ohne Alternativtext ist fuer einen Teil der Leser gar nicht da."""
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    for name in BILDER:
        # Der Pfad ist absolut (…/raw/main/…), damit er auf PyPI nicht ins Leere
        # zeigt — tests/test_readme_auf_pypi.py hält das fest.
        treffer = re.search(r"!\[([^\]]*)\]\([^)]*" + re.escape(name) + r"\)", readme)
        assert treffer, f"{name} wird in der README nicht eingebunden"
        assert len(treffer.group(1)) >= 20, (
            f"{name} hat nur den Alternativtext „{treffer.group(1)}“ — zu kurz, um das "
            "Bild zu ersetzen."
        )


# ── Der Wechsel ─────────────────────────────────────────────────────────────

def test_das_gif_hat_zwei_bilder_und_sie_unterscheiden_sich():
    """Ein GIF mit einem Bild ist ein PNG mit Umweg, eines mit zwei gleichen ein Standbild."""
    from PIL import Image, ImageSequence

    pfad = REPO / "docs" / "assets" / "demo" / "falzmarke-gegenprobe.gif"
    gif = Image.open(pfad)
    assert gif.n_frames == 2, f"{gif.n_frames} Bilder statt zwei"
    erst, zweit = (b.convert("RGB") for b in ImageSequence.Iterator(gif))
    abweichend = _abweichende_pixel(erst, zweit)
    assert abweichend > 500, (
        f"Nur {abweichend} Pixel unterscheiden die beiden Bilder — der Wechsel zeigt nichts."
    )


def test_der_richtige_zustand_steht_zuerst():
    """Wer nur das erste Bild sieht, soll die Marke auf der Sollinie sehen.

    Manche Oberflächen spielen ein GIF nicht ab, sondern zeigen den ersten
    Frame. Stünde dort der Fehlerfall, bewürbe das Bild das Gegenteil dessen,
    was das Werkzeug leistet.

    Gemessen wird die Marke selbst, nicht die Zahl darunter: die Bildzeile mit
    den meisten dunklen Pixeln. Im richtigen Zustand liegt sie höher als im
    verschobenen — der erste Anlauf dieses Tests prüfte `size[0] > 0` und hätte
    nie rot werden können.
    """
    from PIL import Image, ImageSequence

    pfad = REPO / "docs" / "assets" / "demo" / "falzmarke-gegenprobe.gif"
    zeilen = [_markenzeile(b.convert("RGB"))
              for b in ImageSequence.Iterator(Image.open(pfad))]
    assert zeilen[0] < zeilen[1], (
        f"Die Marke liegt im ersten Bild bei Zeile {zeilen[0]}, im zweiten bei {zeilen[1]} — "
        "der Fehlerfall steht damit vorn."
    )
    assert zeilen[1] - zeilen[0] > 20, (
        f"Nur {zeilen[1] - zeilen[0]} Pixel Unterschied — der Sprung ist nicht zu sehen."
    )


def test_die_masszahl_im_bild_stimmt_mit_dem_fenster():
    """Gerundete Masszahlen behaupten einen Ausschnitt, den es nicht gibt.

    Belegt am 27.08.2026: Nach einer Aenderung des Zuschnitts stand
    „6 × 5 mm" im Bild, waehrend das Fenster 5,5 mm breit war — `:.0f` hatte
    gerundet. Die Zahl im Bild ist das Einzige, woran ein Leser den Massstab
    festmachen kann.
    """
    breite, hoehe = detailbild.FENSTER_MM[2], detailbild.FENSTER_MM[3]
    for wert in (breite, hoehe):
        gezeigt = detailbild._mass(wert)
        zurueck = float(gezeigt.replace(",", "."))
        assert abs(zurueck - wert) < 0.01, (
            f"Das Bild zeigt „{gezeigt}“, das Fenster misst {wert} mm."
        )
