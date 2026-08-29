"""Der Messfilm — zeigt er, was er behauptet?

Anlass (Issue #157). Ein Film über eine Messung hat drei Arten, still falsch zu
werden, und keine davon sieht man ihm an:

1. **Die Zahlen veralten.** Jemand ändert einen Sollwert, baut den Film nicht
   neu, und die Linie hält weiter bei einer Zahl, die es nicht mehr gibt.
   Dagegen steht `messfilm.json` neben den Dateien und wird hier gegen einen
   frischen Messlauf gehalten.

2. **Die Linie hält an der falschen Stelle.** Der Film sieht dann genauso
   ordentlich aus. Dagegen wird nachgerechnet, ob die gezeichnete Bildzeile zu
   dem Millimeterwert passt, den der Bericht meldet — und zur Gegenprobe an
   einem Wert, der absichtlich daneben liegt.

3. **Er wird nie rot.** Ein Film, der auch bei kaputtem Layout „eingehalten"
   zeigt, ist Zierde, kein Nachweis. Dagegen wird derselbe Film aus einem
   absichtlich verschobenen Layout gebaut: dort MUSS der betroffene Halt eine
   Abweichung melden.

Der dritte Punkt ist der teuerste — er rendert ein zweites Mal — und zugleich
der einzige, der die Behauptung des Films wirklich stützt.
"""

from __future__ import annotations

import json
import sys

import pytest

from conftest import REPO

sys.path.insert(0, str(REPO / "scripts"))

import messfilm                                                      # noqa: E402

#: Das Fertigkriterium je Dateiformat. Ein abgeschnittener Film ist an der
#: Größe nicht zu erkennen — GIF endet auf das Semikolon, WebP trägt seine
#: Länge im RIFF-Kopf.
DATEIEN = ("messfilm.gif", "messfilm.webp", "messfilm.json",
           "messfilm-9x16.webp")


@pytest.fixture(scope="module")
def gebaut():
    """Ein Lauf für alle Prüfungen — er rendert und misst einmal."""
    return messfilm.baue()


@pytest.fixture(scope="module")
def sabotiert():
    """Derselbe Film aus einem Layout, in dem die Falzmarke verschoben ist."""
    return messfilm.baue(sabotiert=True)


# ── 1. Sind die Zahlen aktuell? ─────────────────────────────────────────────

def test_zahlen_im_film_stammen_aus_dem_lauf(gebaut):
    """Der Beleg neben dem Film muss zum heutigen Messlauf passen."""
    beleg = messfilm.BELEG
    assert beleg.is_file(), (
        f"{beleg.relative_to(REPO)} fehlt — einmal `python3 scripts/messfilm.py` laufen lassen"
    )
    gespeichert = json.loads(beleg.read_text(encoding="utf-8"))
    frisch = messfilm.beleg(gebaut)
    assert gespeichert == frisch, (
        "Der Film zeigt Zahlen, die zum heutigen Lauf nicht mehr passen.\n"
        "Neu bauen: python3 scripts/messfilm.py"
    )


def test_die_dateien_liegen_vollstaendig_im_repo():
    """Ein abgebrochener Schreibvorgang ist an der Dateigröße nicht zu sehen."""
    for name in DATEIEN:
        pfad = messfilm.ZIEL_DIR / name
        assert pfad.is_file(), f"{pfad.relative_to(REPO)} fehlt"
        assert pfad.stat().st_size > 0, f"{pfad.relative_to(REPO)} ist leer"
    gif = (messfilm.ZIEL_DIR / "messfilm.gif").read_bytes()
    assert gif.endswith(b";"), "messfilm.gif ist abgeschnitten — kein GIF-Endzeichen"
    webp = (messfilm.ZIEL_DIR / "messfilm.webp").read_bytes()
    assert webp[:4] == b"RIFF" and webp[8:12] == b"WEBP", "messfilm.webp ist kein WebP"
    laenge = int.from_bytes(webp[4:8], "little") + 8
    assert laenge == len(webp), (
        f"messfilm.webp meldet {laenge} Bytes, hat aber {len(webp)} — abgeschnitten"
    )


def test_webfassung_bleibt_im_bildbudget():
    """Die Website warnt ab 200 KB je Bild (cw-core Perf-Budget-Guard)."""
    kb = (messfilm.ZIEL_DIR / "messfilm.webp").stat().st_size / 1024
    assert kb <= 200, (
        f"messfilm.webp misst {kb:.0f} KB. Über 200 KB meldet der Guard der "
        "Website es an. Stellschrauben in dieser Reihenfolge: BREITE, "
        "FAHRT_BILDER, quality."
    )


# ── 2. Hält die Linie an der richtigen Stelle? ─────────────────────────────

def test_stopps_liegen_auf_dem_blatt(gebaut):
    """Jeder Halt muss eine Höhe auf einem 297 mm hohen Blatt sein."""
    halte = gebaut["stopps"]
    assert halte, "keine Halte — dann zeigt der Film nichts"
    for stopp in halte:
        assert 0.0 < stopp["y_mm"] <= messfilm.BLATT_MM[1], (
            f"„{stopp['name']}“ liegt bei {stopp['y_mm']} mm, also neben dem Blatt"
        )


def test_stopps_stehen_in_der_reihenfolge_der_seite(gebaut):
    """Die Linie fährt von oben nach unten und springt nicht zurück."""
    hoehen = [s["y_mm"] for s in gebaut["stopps"]]
    assert hoehen == sorted(hoehen), (
        f"Die Halte stehen nicht der Reihe nach: {hoehen}. Der Film liefe dann "
        "auf und ab, und der Eindruck einer Abtastung wäre geschauspielert."
    )


def test_bildzeile_folgt_dem_millimeterwert(gebaut):
    """Die gezeichnete Zeile muss der gemessenen Höhe entsprechen.

    Gegenprobe im selben Test: derselbe Wert plus 20 mm MUSS auf eine andere
    Zeile fallen. Ohne sie hieße „stimmt überein" nur, dass zwei Formeln
    dieselbe Konstante teilen.
    """
    for stopp in gebaut["stopps"]:
        y = stopp["y_mm"]
        gezeichnet = messfilm._y_pixel(y)
        erwartet = messfilm.KOPF + round(y / messfilm.BLATT_MM[1] * messfilm.BLATT_HOEHE)
        assert gezeichnet == erwartet, f"„{stopp['name']}“: {gezeichnet} statt {erwartet}"

        daneben = messfilm._y_pixel(min(y + 20.0, messfilm.BLATT_MM[1]))
        assert daneben != gezeichnet, (
            f"20 mm weiter unten kommt dieselbe Bildzeile heraus ({gezeichnet}). "
            "Die Umrechnung von Millimetern in Pixel ist dann keine."
        )


def test_ein_wert_neben_dem_blatt_wird_abgelehnt():
    """Ein Halt außerhalb des Blattes muss den Lauf abbrechen, nicht durchrutschen."""
    kaputt = {"pruefungen": [
        {"name": "Erfundene Marke, y", "soll": "400.00", "ist": "400.00",
         "toleranz": "±0.3", "bestanden": True},
    ]}
    with pytest.raises(SystemExit, match="nicht auf einem"):
        messfilm.stopps(kaputt)


def test_ohne_hoehenmasse_bricht_der_lauf_ab():
    """Heißen die Prüfungen eines Tages anders, darf kein leerer Film entstehen."""
    ohne = {"pruefungen": [
        {"name": "Schriften eingebettet", "soll": "alle", "ist": "alle",
         "toleranz": "—", "bestanden": True},
    ]}
    with pytest.raises(SystemExit, match="Keine Prüfung mit einer Höhe"):
        messfilm.stopps(ohne)


# ── 3. Kann der Film rot werden? ────────────────────────────────────────────

def test_das_ausgelieferte_layout_haelt_seine_masse(gebaut):
    """Vorbedingung für die Gegenprobe: heute ist alles grün."""
    assert gebaut["bericht"]["ok"], (
        "Das ausgelieferte Layout hält seine Maße nicht ein. Dann sagt die "
        "Gegenprobe unten nichts — sie vergliche zwei kaputte Zustände."
    )
    for stopp in gebaut["stopps"]:
        assert stopp["bestanden"], f"„{stopp['name']}“ ist schon ohne Sabotage rot"


def test_verschobenes_layout_macht_den_film_rot(gebaut, sabotiert):
    """Der eigentliche Nachweis: 2 mm daneben, und der Halt meldet es.

    Ohne diesen Test hieße „alle Halte eingehalten" nur, dass der Film das Wort
    „eingehalten" zeichnen kann.
    """
    betroffen = [s for s in sabotiert["stopps"] if s["name"] == "Falzmarke 1, y"]
    assert betroffen, (
        "„Falzmarke 1, y“ steht nicht mehr unter den Halten — die Sabotage in "
        "messfilm.SABOTAGE_MM greift dann ins Leere."
    )
    stopp = betroffen[0]
    assert not stopp["bestanden"], (
        f"Die Falzmarke sitzt bei {stopp['y_mm']} mm statt bei "
        f"{[s['y_mm'] for s in gebaut['stopps'] if s['name'] == 'Falzmarke 1, y'][0]} mm, "
        "und der Film meldet trotzdem „eingehalten“. Dann ist er kein Nachweis."
    )
    assert abs(stopp["y_mm"] - messfilm.SABOTAGE_MM) < 0.5, (
        f"Die sabotierte Marke misst {stopp['y_mm']} mm, erwartet waren "
        f"{messfilm.SABOTAGE_MM} mm. Die Sabotage hat etwas anderes getroffen."
    )


def test_der_rote_halt_sieht_anders_aus(gebaut, sabotiert):
    """Und er muss im Bild ankommen, nicht nur in den Daten.

    Verglichen wird das Einzelbild desselben Halts aus beiden Läufen. Zur
    Gegenprobe daneben das erste Bild beider Filme: dort ist die Linie noch
    über der Falzmarke, und der Unterschied MUSS deutlich kleiner sein — sonst
    misst der Vergleich nicht den Halt, sondern zwei verschiedene Renders.
    """
    from PIL import ImageChops

    def unterschied(links, rechts) -> int:
        diff = ImageChops.difference(links.convert("L"), rechts.convert("L"))
        return sum(n for wert, n in enumerate(diff.histogram()) if wert >= 40)

    index = next(i for i, s in enumerate(gebaut["stopps"]) if s["name"] == "Falzmarke 1, y")
    bild_nummer = (index + 1) * (messfilm.FAHRT_BILDER + 1) - 1

    am_halt = unterschied(gebaut["frames"][bild_nummer], sabotiert["frames"][bild_nummer])
    am_anfang = unterschied(gebaut["frames"][0], sabotiert["frames"][0])

    assert am_halt > 500, (
        f"Nur {am_halt} Pixel unterscheiden das Bild am Halt „Falzmarke 1, y“ vom "
        "sabotierten. Der Film zeigt die Abweichung also nicht."
    )
    assert am_halt > am_anfang * 3, (
        f"Am Halt unterscheiden sich {am_halt} Pixel, im ersten Bild schon "
        f"{am_anfang}. Der Vergleich misst dann nicht den Halt, sondern einen "
        "allgemeinen Unterschied zwischen den beiden Renders."
    )


# ── 4. Steht im README, was der Film zeigt? ─────────────────────────────────

def test_alt_text_nennt_die_gemessenen_werte():
    """Der Alt-Text im README nennt Zahlen — sie dürfen nicht veralten.

    Er ist die einzige Fassung des Films für alle, die ihn nicht sehen. Nennt
    er 105,00 mm, während gemessen 107,00 herauskäme, ist er keine
    Beschreibung mehr, sondern eine falsche Behauptung — und niemand merkt es,
    weil der Text im Bild gar nicht vorkommt.
    """
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    zeilen = [z for z in readme.splitlines() if "messfilm.gif" in z]
    assert len(zeilen) == 1, (
        f"{len(zeilen)} Einbindungen von messfilm.gif im README — erwartet genau eine"
    )
    alt = zeilen[0]

    beleg = json.loads(messfilm.BELEG.read_text(encoding="utf-8"))
    for stopp in beleg["stopps"]:
        wert = str(stopp["ist"]).replace(".", ",")
        assert wert in alt, (
            f"Der Alt-Text nennt {wert} nicht, obwohl der Film bei "
            f"„{stopp['name']}“ genau diesen Wert zeigt.\n"
            "Entweder den Alt-Text nachziehen oder den Wert dort weglassen."
        )
    assert beleg["schlusszeile"] in alt, (
        f"Der Alt-Text nennt die Schlusszeile „{beleg['schlusszeile']}“ nicht."
    )


def test_alt_text_nennt_keine_werte_die_es_nicht_gibt():
    """Gegenprobe: eine erfundene Zahl im Alt-Text müsste auffallen.

    Ohne sie hieße der Test oben nur „alle acht Werte kommen vor" — er sähe
    nicht, wenn zusätzlich ein neunter, veralteter Wert dort stehen bliebe.
    """
    import re

    readme = (REPO / "README.md").read_text(encoding="utf-8")
    alt = next(z for z in readme.splitlines() if "messfilm.gif" in z)
    beleg = json.loads(messfilm.BELEG.read_text(encoding="utf-8"))

    erlaubt = {str(s["ist"]).replace(".", ",") for s in beleg["stopps"]}
    erlaubt |= {w for w in re.findall(r"\d+,\d+", beleg["schlusszeile"])}
    gefunden = set(re.findall(r"\d+,\d+", alt))
    ueberzaehlig = gefunden - erlaubt
    assert not ueberzaehlig, (
        f"Der Alt-Text nennt {sorted(ueberzaehlig)}, aber der Film zeigt diese "
        "Werte nicht. Vermutlich ein Rest aus einer früheren Fassung."
    )


# ── 5. Das Hochformat ───────────────────────────────────────────────────────
#
# Es gibt es, weil Facebook, Instagram und WhatsApp den Querformat-Film als
# Video behandeln und auf 9:16 beschneiden — nachgesehen am 29.08.2026 an einer
# echten Facebook-Vorschau: links fiel „Jedes Maß" weg, rechts
# „Infoblock, y-Oberkan…".

def test_hochformat_hat_das_masz_das_die_dienste_erwarten(gebaut):
    """1080 × 1920. Ein anderes Verhältnis wird wieder beschnitten."""
    erstes = gebaut["hoch_frames"][0]
    assert (erstes.width, erstes.height) == (messfilm.HOCH_BREITE, messfilm.HOCH_HOEHE)
    assert erstes.height / erstes.width == pytest.approx(16 / 9, abs=0.01), (
        f"{erstes.width}×{erstes.height} ist nicht 9:16 — Story und Status "
        "schneiden dann wieder etwas weg."
    )


def test_beide_formate_zeigen_dieselben_zahlen(gebaut):
    """Der eigentliche Grund, sie zusammen zu bauen.

    Zwei Fassungen, von denen eine nachgezogen werden müsste, laufen genau dann
    auseinander, wenn es keiner merkt — und die eine, die niemand ansieht, zeigt
    dann alte Zahlen. Hier wird geprüft, dass beide aus demselben Bericht
    stammen: gleiche Bildzahl, gleiche Standzeiten.
    """
    assert len(gebaut["hoch_frames"]) == len(gebaut["frames"]), (
        "Die Formate haben verschieden viele Bilder — dann halten sie an "
        "verschieden vielen Maßen."
    )
    assert gebaut["hoch_dauern"] == gebaut["dauern"], (
        "Die Standzeiten unterscheiden sich; die Filme laufen verschieden lang "
        "durch dieselben Halte."
    )


def test_hochformat_haelt_an_denselben_hoehen(gebaut):
    """Die Umrechnung mm → Pixel ist im Hochformat eine andere, die Höhen sind dieselben.

    Gegenprobe im selben Test: 20 mm weiter unten MUSS eine andere Bildzeile
    herauskommen. Ohne sie hieße „stimmt überein" nur, dass zwei Formeln
    dieselbe Konstante teilen.
    """
    for stopp in gebaut["stopps"]:
        y = stopp["y_mm"]
        gezeichnet = messfilm._hoch_y(y)
        erwartet = messfilm.HOCH_KOPF + round(
            y / messfilm.BLATT_MM[1] * messfilm.HOCH_BLATT_HOEHE)
        assert gezeichnet == erwartet, f"„{stopp['name']}“: {gezeichnet} statt {erwartet}"
        daneben = messfilm._hoch_y(min(y + 20.0, messfilm.BLATT_MM[1]))
        assert daneben != gezeichnet, (
            f"20 mm weiter unten kommt dieselbe Bildzeile heraus ({gezeichnet})."
        )


def test_der_beleg_nennt_beide_formate():
    """messfilm.json hält fest, was tatsächlich entstanden ist."""
    beleg = json.loads(messfilm.BELEG.read_text(encoding="utf-8"))
    assert "formate" in beleg, "Der Beleg nennt die Formate nicht"
    assert beleg["formate"]["hoch"] == [messfilm.HOCH_BREITE, messfilm.HOCH_HOEHE]


# ── 6. Bezeichner tragen keine Umlaute ──────────────────────────────────────

def test_kein_bezeichner_traegt_einen_umlaut():
    """Deutsche Prosa mit Umlauten, Bezeichner ohne.

    Am 28.08.2026 hat eine pauschale Umlaut-Ersetzung hier Variablen- und
    Parameternamen mitgenommen (`höhe`, `feld_höhe`, `höhen`) und dabei auch
    JSON-Schlüssel getroffen — `bericht["prüfungen"]` warf einen KeyError. Die
    damalige Prüfung lief über ein Textmuster und sah Parameternamen nicht.
    Diese hier geht über den Syntaxbaum und sieht jeden Bezeichner.

    Python erlaubt Umlaute in Namen; das ist nicht der Punkt. Der Punkt ist,
    dass sie hier nie Absicht waren.
    """
    import ast

    for name in ("scripts/messfilm.py", "tests/test_messfilm.py"):
        baum = ast.parse((REPO / name).read_text(encoding="utf-8"))
        treffer = {
            getattr(knoten, feld)
            for knoten in ast.walk(baum)
            for feld in ("name", "arg", "id", "attr")
            if isinstance(getattr(knoten, feld, None), str)
            and any(z in getattr(knoten, feld) for z in "äöüÄÖÜß")
        }
        assert not treffer, f"{name}: Bezeichner mit Umlaut — {sorted(treffer)}"
