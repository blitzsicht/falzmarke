#!/usr/bin/env python3
"""Zeigt die Falzmarke — vergroessert, vermessen und gegengeprueft.

Anlass (Issue #13): Das Werkzeug heisst falzmarke, und auf keinem Vorschaubild
war eine Falzmarke zu erkennen. Sie ist auf jedem Render da, aber letter-pro
zeichnet sie mit 0,25 pt Strichstaerke — bei den 110 ppi der CI-Renders sind das
0,38 Pixel. Auf einem echten Brief ist diese Zurueckhaltung richtig; im
Schaufenster fuehrt sie dazu, dass das namensgebende Merkmal unsichtbar bleibt.

Erzeugt zwei Bilder aus einem echten Render bei 600 ppi:

  falzmarke-detail.png      Uebersicht des Blattes, daneben der Ausschnitt mit
                            der Sollinie und der gemessenen Ist-Position.
  falzmarke-gegenprobe.png  Derselbe Ausschnitt zweimal: einmal aus dem
                            richtigen Layout, einmal aus einem absichtlich
                            verschobenen. Ein Ausschnitt, der beide Faelle gleich
                            zeigt, zeigt nichts — das ist hier nachweisbar.

    python3 scripts/detailbild.py            # schreibt die Bilder neu
    python3 scripts/detailbild.py --pruefen  # meldet nur, ob die Zahlen passen

Die Zahl im Bild wird nicht abgetippt, sondern aus `verify --json` gezogen —
dasselbe Prinzip wie scripts/bericht.py fuer die Zahlen im Erklaerfilm. Wer den
Sollwert aendert, ohne das Bild neu zu bauen, faellt in tests/test_detailbild.py
auf.

Pillow kommt ueber pdfplumber mit und ist damit in jeder Installation da; das
Skript braucht deshalb kein ImageMagick und laeuft auch dort, wo demobilder.sh
mangels `magick` nicht kann.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CLI = REPO / "skill" / "scripts" / "falzmarke.py"
BRIEF = REPO / "examples" / "brief-form-b.md"
ZIEL_DIR = REPO / "docs" / "assets" / "demo"
BELEG = ZIEL_DIR / "detailbild.json"

# Form B faltet bei 105 mm. Der Wert steht nicht hier, sondern wird aus dem
# Bericht gelesen — diese Konstante nennt nur die Pruefung, um die es geht.
PRUEFUNG = "Falzmarke 1, y"

# 600 ppi statt der 110 der CI-Renders: erst dort ist die 0,25-pt-Linie ueber
# zwei Pixel hoch und ueberlebt die Rasterung. Gemessen am 26.08.2026: bei
# 600 ppi liegen die drei Marken auf y 2479–2481, 3506–3508 und 4959–4961 px,
# also auf 104,94–105,02 / 148,41–148,49 / 209,92–210,00 mm.
PPI = 600

# Ausschnittfenster in Millimetern (x-links, y-oben, Breite, Hoehe). Beide
# Bilder benutzen dasselbe — was hier zu sehen ist, soll dort dasselbe bedeuten.
#
# Die Breite von 9 mm ist der Kern der Sache: Die Marke ist 0,088 mm stark
# (0,25 pt), also zeigt jedes Bild sie so dick, wie das Fenster schmal ist. Auf
# 9 mm Fensterbreite wird daraus in der README-Darstellung gut ein halbes
# Dutzend Pixel; auf den 210 mm des ganzen Blattes bleibt weniger als eines
# uebrig — genau der Grund, aus dem sie auf den Vorschaubildern verschwand.
# Die Hoehe von 7 mm ist die Untergrenze, bei der die verschobene Marke der
# Gegenprobe noch im Bild liegt.
FENSTER_MM = (0.0, 102.0, 9.0, 7.0)

# Verschiebung fuer die Gegenprobe, in Millimetern.
# tests/test_gegenbeweis.py verschiebt die Marke auf 112 mm — dort ist der
# grosse Sprung richtig, weil nur zaehlt, ob die Pruefung anschlaegt. Fuer ein
# Bild waeren 7 mm unehrlich gross: Sie zeigten einen Fehler, den man ohne jedes
# Werkzeug sieht. 2 mm sind das Siebenfache der Toleranz von +/- 0,3 mm und
# damit sicher ein Fehler — und zugleich so wenig, dass die Frage „faellt das
# ueberhaupt auf?" ihre Berechtigung behaelt.
SABOTAGE_MM = 107.0

# docs/marke/erscheinungsbild.md — vier Farben, kein zweiter Akzent. Die
# Abweichung wird deshalb durch Zahl und Zeichen markiert, nicht durch Rot.
TINTE = (18, 30, 47)
GRUEN = (62, 176, 87)
GRUEN_TEXT = (47, 134, 66)
GRAU = (91, 100, 112)
PAPIER = (255, 255, 255)

SCHRIFT = REPO / "docs" / "marke" / "fonts" / "Montserrat-SemiBold.ttf"
SCHRIFT_FETT = REPO / "docs" / "marke" / "fonts" / "Montserrat-ExtraBold.ttf"


# ── Rendern und Messen ──────────────────────────────────────────────────────

def _falzmarke_modul():
    sys.path.insert(0, str(REPO / "skill"))
    from falzmarke import cli
    return cli


def sabotiere(ziel: Path, datei: str, alt: str, neu: str) -> Path:
    """Kopiert das Typst-Verzeichnis und ersetzt darin genau eine Stelle.

    Gleiche Mechanik wie tests/test_gegenbeweis.py. Die Vorlage selbst bleibt
    unangetastet — sie ist pruefsummengesichert (tests/test_vendor.py).
    """
    kopie = ziel / "typst"
    if kopie.exists():
        shutil.rmtree(kopie)
    shutil.copytree(REPO / "skill" / "falzmarke" / "typst", kopie)
    pfad = kopie / datei
    text = pfad.read_text(encoding="utf-8")
    if alt not in text:
        raise SystemExit(
            f"{datei}: „{alt}“ steht dort nicht mehr.\n"
            "Die Gegenprobe griffe ins Leere — erst hier nachziehen, dann bauen."
        )
    pfad.write_text(text.replace(alt, neu, 1), encoding="utf-8")
    return kopie


def rendere(brief: Path, ziel: Path, *, typst_dir: Path | None = None) -> tuple[Path, Path]:
    """Setzt den Brief einmal als PDF (zum Messen) und einmal als PNG (zum Zeigen)."""
    falzmarke = _falzmarke_modul()
    original = falzmarke.TYPST_DIR
    if typst_dir is not None:
        falzmarke.TYPST_DIR = typst_dir
    try:
        pdf, _ = falzmarke.rendere(brief, ziel / "brief.pdf")
        png, _ = falzmarke.rendere(brief, ziel / "brief.png", format_name="png", ppi=PPI)
    finally:
        falzmarke.TYPST_DIR = original
    return pdf, png


def _zahl(wert) -> float:
    treffer = re.search(r"-?\d+(?:[.,]\d+)?", str(wert))
    if not treffer:
        raise SystemExit(f"Kein Zahlenwert in {wert!r}")
    return float(treffer.group(0).replace(",", "."))


def messe(pdf: Path) -> dict:
    """Soll und Ist der Falzmarke aus dem Bericht — nicht aus dieser Datei."""
    lauf = subprocess.run(
        [sys.executable, str(CLI), "verify", str(pdf), "--json"],
        capture_output=True, text=True, encoding="utf-8",
    )
    if lauf.returncode != 0:
        raise SystemExit(f"verify scheiterte:\n{lauf.stderr}")
    bericht = json.loads(lauf.stdout)
    nach_name = {p["name"]: p for p in bericht["pruefungen"]}
    if PRUEFUNG not in nach_name:
        raise SystemExit(
            f"Die Pruefung „{PRUEFUNG}“ steht nicht mehr im Bericht.\n"
            "Entweder PRUEFUNG hier anpassen oder das Bild aufgeben."
        )
    pruefung = nach_name[PRUEFUNG]
    return {
        "soll": _zahl(pruefung["soll"]),
        "ist": _zahl(pruefung["ist"]),
        "bestanden": pruefung["bestanden"],
    }


# ── Zeichnen ────────────────────────────────────────────────────────────────

def _bild(pfad: Path):
    from PIL import Image
    return Image.open(pfad).convert("RGB")


def _schrift(groesse: int, fett: bool = False):
    from PIL import ImageFont
    datei = SCHRIFT_FETT if fett else SCHRIFT
    if not datei.is_file():
        raise SystemExit(f"Schrift fehlt: {datei}")
    return ImageFont.truetype(str(datei), groesse)


def _ausschnitt(seite, fenster_mm: tuple[float, float, float, float], zielhoehe: int):
    """Schneidet ein Fenster in Millimetern aus dem Render und vergroessert es."""
    from PIL import Image

    px_pro_mm = seite.width / 210.0
    x, y, breite, hoehe = fenster_mm
    kasten = (round(x * px_pro_mm), round(y * px_pro_mm),
              round((x + breite) * px_pro_mm), round((y + hoehe) * px_pro_mm))
    roh = seite.crop(kasten)
    faktor = zielhoehe / roh.height
    # LANCZOS statt NEAREST: Die Marke ist im Original drei Pixel hoch, davon
    # zwei durch Antialiasing grau. NEAREST wuerde daraus je nach Rundung zwei
    # oder vier harte Pixel machen und die Linie mal dicker, mal duenner zeigen,
    # als sie ist. Das Bild soll vergroessern, nicht verschoenern.
    return roh.resize((round(roh.width * faktor), zielhoehe), Image.LANCZOS), faktor


def _y_im_ausschnitt(mm: float, fenster_mm, zielhoehe: int) -> float:
    """Millimeter auf dem Blatt -> Pixelzeile im vergroesserten Ausschnitt."""
    _, oben, _, hoehe = fenster_mm
    return (mm - oben) / hoehe * zielhoehe


# Die Marke beginnt 5 mm vom Blattrand und ist 2,5 mm lang — letter-pro setzt
# sie so (vendor/letter-pro-v3.0.0.typ, `dx: 5mm`, `length: 2.5mm`).
MARKE_X_MM = (5.0, 7.5)


def _sollinie(zeichner, y: float, breite: int, ausschnitt_mm, beschriftung, schrift) -> None:
    """Gestrichelte Hilfslinie auf der Sollposition, links neben der Marke.

    Sie laeuft bewusst nur bis an die Marke heran und nicht durch sie hindurch:
    Eine deckende Linie ueber der Marke verdeckt genau das, was das Bild zeigen
    soll — im ersten Entwurf war die richtig sitzende Marke deshalb schlechter
    zu sehen als die falsch sitzende. Gestrichelt, damit niemand sie fuer einen
    Strich auf dem Brief haelt.
    """
    x_links, _, fenster_breite, _ = ausschnitt_mm
    bis = round((MARKE_X_MM[0] - x_links) / fenster_breite * breite) - 8
    x = 0
    while x < bis:
        zeichner.line([(x, y), (min(x + 16, bis), y)], fill=GRUEN, width=3)
        x += 30
    zeichner.text((0, y + 14), beschriftung, font=schrift, fill=GRUEN_TEXT)


def _uebersicht(seite, zielhoehe: int, fenster_mm):
    """Das ganze Blatt klein, mit einem Rahmen um die vergroesserte Stelle."""
    from PIL import Image, ImageDraw

    faktor = zielhoehe / seite.height
    klein = seite.resize((round(seite.width * faktor), zielhoehe), Image.LANCZOS)
    zeichner = ImageDraw.Draw(klein)
    px_pro_mm = klein.width / 210.0
    x, y, breite, hoehe = fenster_mm
    zeichner.rectangle(
        [(round(x * px_pro_mm), round(y * px_pro_mm)),
         (round((x + breite) * px_pro_mm), round((y + hoehe) * px_pro_mm))],
        outline=GRUEN, width=3,
    )
    zeichner.rectangle([(0, 0), (klein.width - 1, klein.height - 1)], outline=GRAU, width=1)
    return klein


BREITE = 1240          # wie docs/assets/demo/hero.png — die README-Bilder sollen
RAND = 44              # nebeneinander nicht unterschiedlich breit wirken.


def zeichne_detail(seite, mess: dict):
    """Uebersicht des Blattes, daneben der vergroesserte Ausschnitt."""
    from PIL import Image, ImageDraw

    hoehe_bild = 480
    uebersicht = _uebersicht(seite, hoehe_bild, FENSTER_MM)
    ausschnitt, _ = _ausschnitt(seite, FENSTER_MM, hoehe_bild)

    oben = 124
    tafel = Image.new("RGB", (BREITE, oben + hoehe_bild + 136), PAPIER)
    zeichner = ImageDraw.Draw(tafel)

    x_uebersicht = RAND
    x_ausschnitt = BREITE - RAND - ausschnitt.width

    y_soll = _y_im_ausschnitt(mess["soll"], FENSTER_MM, hoehe_bild)
    _sollinie(ImageDraw.Draw(ausschnitt), y_soll, ausschnitt.width, FENSTER_MM,
              f"Soll {mess['soll']:.2f} mm".replace(".", ","), _schrift(22))

    tafel.paste(uebersicht, (x_uebersicht, oben))
    tafel.paste(ausschnitt, (x_ausschnitt, oben))
    zeichner.rectangle(
        [(x_ausschnitt, oben),
         (x_ausschnitt + ausschnitt.width - 1, oben + hoehe_bild - 1)],
        outline=GRAU, width=1,
    )

    # Lupenlinien. Sie setzen erst an der rechten Blattkante an, nicht am
    # Rahmen selbst: Der Ausschnitt liegt am linken Blattrand, eine Linie von
    # dort zoege quer ueber den ganzen Brief und sähe aus wie ein Kratzer.
    px_pro_mm = uebersicht.width / 210.0
    _, y_fenster, _, hoehe_fenster = FENSTER_MM
    for kante, ziel in ((y_fenster, 0), (y_fenster + hoehe_fenster, hoehe_bild)):
        zeichner.line(
            [(x_uebersicht + uebersicht.width, oben + round(kante * px_pro_mm)),
             (x_ausschnitt, oben + ziel)],
            fill=GRAU, width=1,
        )

    zeichner.text((RAND, 34), "Die Falzmarke, aus der Nähe",
                  font=_schrift(34, fett=True), fill=TINTE)
    zeichner.text(
        (RAND, 90),
        f"Ausschnitt am linken Blattrand, {FENSTER_MM[2]:.0f} × {FENSTER_MM[3]:.0f} mm",
        font=_schrift(20), fill=GRAU,
    )

    ist = f"{mess['ist']:.2f} mm".replace(".", ",")
    zeichner.text((x_ausschnitt, oben + hoehe_bild + 32),
                  f"gemessen: {ist}", font=_schrift(30, fett=True), fill=TINTE)
    zeichner.text((x_ausschnitt, oben + hoehe_bild + 78),
                  "aus falzmarke verify — nicht abgetippt",
                  font=_schrift(20), fill=GRAU)
    return tafel


def zeichne_gegenprobe(seite, seite_sabotiert, mess: dict):
    """Derselbe Ausschnitt aus dem richtigen und aus dem verschobenen Layout."""
    from PIL import Image, ImageDraw

    fuge = 64
    spalte = (BREITE - 2 * RAND - fuge) // 2
    hoehe_bild = round(spalte / FENSTER_MM[2] * FENSTER_MM[3])

    oben = 128
    tafel = Image.new("RGB", (BREITE, oben + hoehe_bild + 142), PAPIER)
    zeichner = ImageDraw.Draw(tafel)
    zeichner.text((RAND, 34), "Zeigt der Ausschnitt überhaupt etwas?",
                  font=_schrift(34, fett=True), fill=TINTE)
    zeichner.text((RAND, 90),
                  "Derselbe Ausschnitt aus dem ausgelieferten Layout und aus einem, "
                  "in dem die Marke absichtlich verschoben ist.",
                  font=_schrift(20), fill=GRAU)

    y_soll = _y_im_ausschnitt(mess["soll"], FENSTER_MM, hoehe_bild)
    versatz = SABOTAGE_MM - mess["soll"]
    faelle = (
        (seite, f"{mess['ist']:.2f} mm".replace(".", ","), "so wird ausgeliefert"),
        (seite_sabotiert, f"{SABOTAGE_MM:.2f} mm".replace(".", ","),
         f"{versatz:.0f} mm zu tief — verify schlägt an"),
    )
    for nummer, (quelle, kopf, fuss) in enumerate(faelle):
        ausschnitt, _ = _ausschnitt(quelle, FENSTER_MM, hoehe_bild)
        _sollinie(ImageDraw.Draw(ausschnitt), y_soll, ausschnitt.width, FENSTER_MM,
                  f"Soll {mess['soll']:.2f} mm".replace(".", ","), _schrift(22))
        x = RAND + nummer * (spalte + fuge)
        tafel.paste(ausschnitt, (x, oben))
        zeichner.rectangle(
            [(x, oben), (x + ausschnitt.width - 1, oben + ausschnitt.height - 1)],
            outline=GRAU, width=1,
        )
        zeichner.text((x, oben + hoehe_bild + 32), kopf,
                      font=_schrift(30, fett=True), fill=TINTE)
        zeichner.text((x, oben + hoehe_bild + 78), fuss, font=_schrift(20), fill=GRAU)
    return tafel


# ── Ablauf ──────────────────────────────────────────────────────────────────

def baue() -> dict:
    """Rendert beide Faelle und gibt Messwerte, Tafeln und Ausschnitte zurueck.

    Die rohen Ausschnitte stehen mit im Ergebnis, weil tests/test_detailbild.py
    an ihnen misst, ob der Ausschnitt die verschobene Marke ueberhaupt zeigt.
    An den fertigen Tafeln ginge das nicht: Dort steht unter jedem Ausschnitt
    eine andere Zahl, und die allein macht die Haelften schon verschieden — der
    Vergleich waere gruen, ohne je das Papier angesehen zu haben.
    """
    with tempfile.TemporaryDirectory(prefix="falzmarke-detail-") as tmp:
        arbeit = Path(tmp)
        richtig = arbeit / "richtig"
        falsch = arbeit / "falsch"
        richtig.mkdir()
        falsch.mkdir()

        pdf, png = rendere(BRIEF, richtig)
        mess = messe(pdf)
        if not mess["bestanden"]:
            raise SystemExit(
                f"„{PRUEFUNG}“ ist im ausgelieferten Layout nicht bestanden "
                f"(soll {mess['soll']}, ist {mess['ist']}).\n"
                "Erst den Fehler beheben — ein Schaufensterbild eines kaputten "
                "Layouts waere die teuerste Art, ihn zu verstecken."
            )

        typst_kaputt = sabotiere(
            falsch, "vendor/letter-pro-v3.0.0.typ",
            "folding-mark-1-pos: 105mm", f"folding-mark-1-pos: {SABOTAGE_MM:.0f}mm",
        )
        _, png_falsch = rendere(BRIEF, falsch, typst_dir=typst_kaputt)

        seite = _bild(png)
        seite_falsch = _bild(png_falsch)
        hoehe = round((BREITE - 2 * RAND - 64) // 2 / FENSTER_MM[2] * FENSTER_MM[3])
        return {
            "mess": mess,
            "detail": zeichne_detail(seite, mess),
            "gegenprobe": zeichne_gegenprobe(seite, seite_falsch, mess),
            "ausschnitt_richtig": _ausschnitt(seite, FENSTER_MM, hoehe)[0],
            "ausschnitt_falsch": _ausschnitt(seite_falsch, FENSTER_MM, hoehe)[0],
            "seiten": (seite, seite_falsch),
        }


def beleg(mess: dict) -> dict:
    return {
        "hinweis": "Erzeugt aus einem echten Render — nicht von Hand aendern. "
                   "Neu bauen: python3 scripts/detailbild.py",
        "brief": BRIEF.name,
        "pruefung": PRUEFUNG,
        "soll_mm": mess["soll"],
        "ist_mm": mess["ist"],
        "sabotage_mm": SABOTAGE_MM,
        "ppi": PPI,
        "fenster_mm": list(FENSTER_MM),
    }


def main() -> int:
    zerleger = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    zerleger.add_argument("--pruefen", action="store_true",
                          help="nur melden, ob die Zahlen im Repo zum Lauf passen")
    args = zerleger.parse_args()

    gebaut = baue()
    mess = gebaut["mess"]
    neu = json.dumps(beleg(mess), ensure_ascii=False, indent=2) + "\n"

    if args.pruefen:
        if not BELEG.is_file():
            print(f"FEHLT  {BELEG.relative_to(REPO)} — einmal ohne --pruefen laufen lassen")
            return 1
        alt = BELEG.read_text(encoding="utf-8")
        if alt != neu:
            print(f"VERALTET  {BELEG.relative_to(REPO)} passt nicht zum Lauf.\n"
                  "Die Bilder zeigen dann eine Zahl, die es so nicht mehr gibt.\n"
                  "Neu bauen: python3 scripts/detailbild.py")
            return 1
        print(f"OK  Bilder und Messwerte stimmen überein ({PRUEFUNG}: "
              f"{mess['ist']:.2f} mm)")
        return 0

    ZIEL_DIR.mkdir(parents=True, exist_ok=True)
    for schluessel, name in (("detail", "falzmarke-detail.png"),
                             ("gegenprobe", "falzmarke-gegenprobe.png")):
        bild = gebaut[schluessel]
        pfad = ZIEL_DIR / name
        bild.save(pfad, optimize=True)
        print(f"  {pfad.relative_to(REPO)}  {bild.width}x{bild.height}")
    BELEG.write_text(neu, encoding="utf-8")
    print(f"  {BELEG.relative_to(REPO)}  {PRUEFUNG}: {mess['ist']:.2f} mm")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
