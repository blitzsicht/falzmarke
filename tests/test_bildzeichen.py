"""Das Bildzeichen und der Favicon-Satz (Issue #82).

Zwei Behauptungen stehen im Erscheinungsbild, und beide altern still, wenn
niemand sie prüft:

1. Das Bildzeichen ist aus `logo.svg` **abgeleitet**, nicht neu gezeichnet —
   Wortmarke weg, sonst nichts geändert.
2. Das ICO trägt **größenspezifische** Bilder. Wäre die 16er-Bitmap die
   heruntergerechnete 32er, dann wäre `bildzeichen-klein.svg` wirkungslos und
   der ganze Aufwand dahinter umsonst — ohne dass irgendetwas rot würde.
"""

from __future__ import annotations

from PIL import Image

from conftest import REPO

MARKE = REPO / "docs" / "assets" / "brand"
LOGO = MARKE / "logo.svg"
ZEICHEN = MARKE / "bildzeichen.svg"
KLEIN = MARKE / "bildzeichen-klein.svg"
ICO = MARKE / "favicon.ico"

#: Die Farben der Marke. Ein Bildzeichen, das umgefärbt wurde, ist keins mehr.
FARBEN = ("#121E2F", "#3EB057", "#FFFFFF")

#: Das Element, das die Wortmarke trägt. Auf das ELEMENT prüfen, nicht auf den
#: Namen: Die Dateiköpfe erwähnen ihn, weil sie sagen, was entfernt wurde.
WORTMARKE = '<g id="falzmarke_x5F_font"'


def _text(pfad):
    return pfad.read_text(encoding="utf-8")


def _dunkle_pixel(bild: Image.Image) -> int:
    """Kräftig dunkle, deckende Pixel — das Maß für Lesbarkeit im Kleinen."""
    roh = bild.convert("RGBA").tobytes()
    # Über die Rohbytes statt getdata(): Das ist über Pillow-Fassungen hinweg
    # stabil, und der Test soll nicht an einer Umbenennung sterben.
    return sum(1 for i in range(0, len(roh), 4)
               if roh[i + 3] > 200 and roh[i] + roh[i + 1] + roh[i + 2] < 260)


# ── Abgeleitet, nicht neu gezeichnet ────────────────────────────────────────

def test_das_bildzeichen_traegt_keine_wortmarke():
    assert WORTMARKE not in _text(ZEICHEN)
    assert WORTMARKE not in _text(KLEIN)


def test_gegenprobe_das_logo_traegt_sie_sehr_wohl():
    """Ohne diese Zeile prüfte der Test darüber nur, dass eine Zeichenkette
    fehlt — auch in einer leeren Datei fehlt sie."""
    assert WORTMARKE in _text(LOGO)


def test_die_farben_sind_unveraendert():
    """Nicht umfärben, nicht verzerren, das Haken-Grün bleibt."""
    for datei in (ZEICHEN, KLEIN):
        inhalt = _text(datei)
        for farbe in FARBEN:
            assert farbe in inhalt, f"{farbe} fehlt in {datei.name}"


def test_die_kleine_fassung_ist_die_grosse_plus_kontur():
    """Sie darf sich in genau einer Sache unterscheiden: der Kontur.

    Wer sie neu zeichnet statt abzuleiten, fällt hier auf — dann stimmen die
    Pfaddaten nicht mehr überein.
    """
    import re

    pfade = lambda s: re.findall(r'\sd="([^"]+)"', s)
    assert pfade(_text(KLEIN)) == pfade(_text(ZEICHEN)), \
        "die Pfade weichen ab — die kleine Fassung ist nicht mehr abgeleitet"
    assert "stroke-width" in _text(KLEIN)
    assert "stroke-width" not in _text(ZEICHEN)


# ── Der Favicon-Satz ────────────────────────────────────────────────────────

def test_das_ico_traegt_drei_groessen():
    with Image.open(ICO) as bild:
        assert sorted(bild.info["sizes"]) == [(16, 16), (32, 32), (48, 48)]


def test_die_16er_bitmap_ist_nicht_die_verkleinerte_32er():
    """Der Kern von #82.

    Die Marken sind bei 16 px 0,70 px breit — unter einem Pixel. Deshalb trägt
    das ICO dort eine eigens gezeichnete Fassung. Wäre es die skalierte 32er,
    sähe man den Unterschied nirgends im Code, nur im Browser-Tab.
    """
    with Image.open(ICO) as bild:
        bild.size = (16, 16)
        klein = bild.convert("RGBA")
        bild.size = (32, 32)
        gross = bild.convert("RGBA")

    verkleinert = gross.resize((16, 16), Image.LANCZOS)
    assert klein.tobytes() != verkleinert.tobytes(), \
        "die 16er-Bitmap ist die heruntergerechnete 32er — die kleine Fassung wirkt nicht"

    # Und sie ist die kräftigere, nicht bloss eine andere.
    assert _dunkle_pixel(klein) > _dunkle_pixel(verkleinert), (
        f"die 16er ist nicht kräftiger: {_dunkle_pixel(klein)} gegen "
        f"{_dunkle_pixel(verkleinert)} kräftig dunkle Pixel"
    )


def test_die_16er_bitmap_hat_genug_masse():
    """Gemessen beim Bauen: 12 kräftig dunkle Pixel gegen 3 bei der
    originalgetreuen Fassung. Fällt der Wert, ist die Kontur verlorengegangen."""
    with Image.open(ICO) as bild:
        bild.size = (16, 16)
        assert _dunkle_pixel(bild.convert("RGBA")) >= 10


def test_die_abgeleiteten_bilder_liegen_bei():
    for name, groesse in (("apple-touch-icon.png", 180), ("icon-512.png", 512)):
        pfad = MARKE / name
        assert pfad.exists(), f"{name} fehlt"
        with Image.open(pfad) as bild:
            assert bild.size == (groesse, groesse)


# ── Die Doku sagt, was da ist ───────────────────────────────────────────────

def test_das_erscheinungsbild_beschreibt_die_dateien():
    text = (REPO / "docs" / "marke" / "erscheinungsbild.md").read_text(encoding="utf-8")
    for name in ("bildzeichen.svg", "bildzeichen-klein.svg", "favicon.ico",
                 "apple-touch-icon.png", "icon-512.png"):
        assert name in text, f"{name} steht nicht im Erscheinungsbild"


def test_der_offene_punkt_ist_weg():
    """Er stand unter „Offen" und ist mit dieser Arbeit erledigt."""
    text = (REPO / "docs" / "marke" / "erscheinungsbild.md").read_text(encoding="utf-8")
    assert "Kein Favicon" not in text


# ── Auf dunklem Grund ───────────────────────────────────────────────────────
#
# Die Tinte `#121E2F` hat auf dunklem Tab-Hintergrund ein Kontrastverhältnis
# von 1,01:1 — vom Zeichen bleibt das grüne Dreieck. Das SVG kehrt deshalb
# Tinte zu Papier um. Beide Farben stehen in der Palette; es kommt keine dazu.

TINTE, PAPIER = (0x12, 0x1E, 0x2F), (0xFF, 0xFF, 0xFF)
DUNKLER_TAB = (0x1E, 0x1E, 0x1E)


def _kontrast(vordergrund, hintergrund) -> float:
    """WCAG 2.2, Verhältnis relativer Leuchtdichten."""
    def leuchtdichte(farbe):
        werte = [x / 255 for x in farbe]
        werte = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in werte]
        return 0.2126 * werte[0] + 0.7152 * werte[1] + 0.0722 * werte[2]
    a, b = leuchtdichte(vordergrund), leuchtdichte(hintergrund)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def test_beide_svg_kehren_auf_dunklem_grund_um():
    for datei in (ZEICHEN, KLEIN):
        inhalt = _text(datei)
        assert "@media (prefers-color-scheme: dark)" in inhalt, datei.name
        dunkel = inhalt[inhalt.index("prefers-color-scheme: dark"):]
        dunkel = dunkel[:dunkel.index("}\n\t}")]
        assert "#FFFFFF" in dunkel, f"{datei.name} schaltet die Blattfarbe nicht um"


def _dunkelblock(inhalt: str) -> str:
    anfang = inhalt.index("@media (prefers-color-scheme: dark)")
    return inhalt[anfang:inhalt.index("\n\t}", anfang)]


def test_die_kontur_der_kleinen_fassung_schaltet_mit():
    """Sie stand einmal als Attribut da und wäre dunkel geblieben — dann hätte
    das Blatt umgeschaltet und die Marken nicht."""
    inhalt = _text(KLEIN)
    assert 'stroke="#121E2F"' not in inhalt, "Kontur als Attribut lässt sich nicht umschalten"
    assert "st-mark" in inhalt
    assert ".st-mark{stroke:#FFFFFF;}" in _dunkelblock(inhalt)


def test_die_helle_grundregel_steht_vor_der_medienabfrage():
    """CSS-Reihenfolge, und sie ist hier keine Formsache.

    Stünde `.st-mark{stroke:#121E2F;}` NACH dem @media-Block, gewänne sie bei
    gleicher Spezifität — das Blatt würde umschalten, die Kontur nicht. Genau
    so war es beim ersten Anlauf.
    """
    inhalt = _text(KLEIN)
    assert inhalt.index(".st-mark{stroke:#121E2F;}") < inhalt.index("@media")


def test_die_svg_sind_gueltiges_xml():
    """Der Fehler, den keine Textprüfung findet.

    Beim Anlegen der Kontur stand zeitweise ein zweites `class`-Attribut neben
    dem vorhandenen. Jede Prüfung auf Zeichenketten war grün; erst der Renderer
    sagte „Attribute class redefined" und gab kein Bild aus.
    """
    import xml.etree.ElementTree as ET

    for datei in (ZEICHEN, KLEIN, LOGO):
        ET.parse(datei)   # wirft bei ungültigem XML


def test_kein_element_traegt_zwei_klassen_attribute():
    """Dieselbe Sache, gezielt: `ET.parse` faellt darauf herein, wenn ein
    Parser nachsichtig ist. Diese Prüfung ist es nicht."""
    import re

    for datei in (ZEICHEN, KLEIN):
        for element in re.findall(r"<[a-z]+\s[^>]*>", _text(datei)):
            assert element.count("class=") <= 1, f"zwei class= in {datei.name}: {element[:80]}"


def test_die_umkehr_loest_das_problem_wirklich():
    """Die Zahl, wegen der es die Regel gibt — und die Gegenrichtung dazu.

    Ohne die zweite Zeile wüsste man nicht, ob 3,0:1 eine hohe Hürde ist oder
    eine, die auch die alte Farbe genommen hätte.
    """
    assert _kontrast(PAPIER, DUNKLER_TAB) >= 3.0
    assert _kontrast(TINTE, DUNKLER_TAB) < 3.0, \
        "die Tinte bestünde auch so — dann belegt die Regel nichts"


def test_das_erscheinungsbild_nennt_die_grenze_der_umschaltung():
    """Das ICO kann sie nicht — Bitmaps tragen keine Medienabfrage. Wer das
    nicht dazuschreibt, verspricht mehr, als die Dateien halten."""
    text = (REPO / "docs" / "marke" / "erscheinungsbild.md").read_text(encoding="utf-8")
    assert "prefers-color-scheme" in text
    assert "ICO" in text
