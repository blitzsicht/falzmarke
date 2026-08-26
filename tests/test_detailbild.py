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
    "falzmarke-gegenprobe.png": "gegenprobe",
}


@pytest.fixture(scope="module")
def gebaut():
    """Ein Lauf fuer alle Pruefungen — er rendert zweimal bei 600 ppi."""
    return detailbild.baue()


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
        assert pfad.is_file(), f"{name} fehlt — bash scripts/demobilder.sh"
        assert pfad.read_bytes()[-12:] == bytes.fromhex("0000000049454e44ae426082"), (
            f"{name} endet nicht auf IEND — die Datei ist unvollständig."
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
