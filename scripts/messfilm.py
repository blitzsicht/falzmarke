#!/usr/bin/env python3
"""Der Messfilm: eine Scanlinie fährt das Blatt ab und hält an jedem Höhenmaß.

Anlass (Issue #157): Die Schaufensterbilder zeigen EINEN Wert — die Falzmarke bei
105 mm. Nachgemessen werden 33. Was fehlte, war ein Bild für das, was das
Werkzeug eigentlich tut: das fertige PDF wieder einlesen und Maß für Maß
gegen den Sollwert halten.

Der Film zeigt die gesetzte Seite, eine Linie wandert darüber und hält an
jedem gemessenen Höhenmaß. Daneben stehen Prüfung, Soll, Ist und Toleranz.
Am Ende die echte Schlusszeile des Berichts.

    python3 scripts/messfilm.py            # schreibt den Film neu
    python3 scripts/messfilm.py --pruefen  # meldet nur, ob die Zahlen passen

## Warum keine gemalten Positionen

`Prüfung` (skill/falzmarke/geometrie.py) trägt name, soll, ist, toleranz und
bestanden — aber KEINE Koordinate. Eine Tabelle „Prüfungsname -> Höhe" von
Hand zu pflegen wäre genau die stille Veraltung, gegen die tests/test_detailbild.py
geschrieben wurde: Wer den Sollwert ändert, merkt nichts, und das Bild zeigt
weiter auf die alte Stelle.

Sie ist auch nicht nötig. Bei den Prüfungen, um die es hier geht, IST der
gemessene Wert die Position: „Falzmarke 1, y: ist 105.00" heißt, die Marke
sitzt auf 105,00 mm. Der Film hält also dort an, wo die Messung es sagt.

Die x-Maße (Ränder, Spaltenkanten) und die Wahrheitsprüfungen („Betreff ohne
Leitwort", „Schriften eingebettet") haben keine Höhe. Sie werden nicht
unterschlagen, sondern im Schlussbild mitgezählt.

## Kein nachgestelltes Terminal

docs/marke/video/readme.tape hält die Hausregel fest: „Ein GIF mit gruenen
OK-Zeilen wuerde etwas zeigen, das vor keinem echten Terminal je so aussieht."
Dieser Film ist deshalb ausdrücklich KEIN nachgestelltes Terminal, sondern eine
Zeichnung über einem echten Render — und er gibt sich auch als solche.

Pillow kommt über pdfplumber mit; das Skript braucht kein ImageMagick. Die
Render- und Sabotage-Mechanik teilt es sich mit scripts/detailbild.py.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from detailbild import (                                              # noqa: E402
    CLI,
    GRAU,
    GRUEN,
    GRUEN_TEXT,
    PAPIER,
    TINTE,
    _bild,
    _falzmarke_modul,
    _schrift,
    _zahl,
    sabotiere,
)

BRIEF = REPO / "examples" / "brief-form-b.md"
ZIEL_DIR = REPO / "docs" / "assets" / "demo"
BELEG = ZIEL_DIR / "messfilm.json"

# Blattmaße in Millimetern. Sie stehen hier nicht als Behauptung, sondern als
# Erwartung: `pruefe_blatt()` hält sie gegen den Bericht und bricht ab, wenn
# das Blatt ein anderes Format hat. Sonst zeichnete der Film eine A4-Seite über
# einen Render, der keine ist.
BLATT_MM = (210.0, 297.0)

# 150 ppi statt der 600 aus detailbild.py: Dort geht es um eine 0,25-pt-Linie im
# Ausschnitt, hier um das ganze Blatt. Bei 150 ppi ist die Seite 1240 x 1754 px
# und damit gut doppelt so groß wie die Fläche im Film — genug Reserve fürs
# Herunterskalieren, ohne dass jeder Frame eine 25-MB-Vorlage schleppt.
PPI = 150

# Welche Prüfungen eine Höhe auf dem Blatt tragen. Das Muster beschreibt die
# Benennung, nicht die Werte — die kommen aus dem Bericht. Findet es nichts,
# bricht `stopps()` ab: ein Film ohne Halt wäre ein hübsches Nichts.
HOEHENMASS = re.compile(r"(?:, y$|y-Oberkante|Zeile y$|Unterkante$)")

# Verschiebung für die Gegenprobe, in Millimetern. Dieselbe Zahl und derselbe
# Grund wie in detailbild.py: 2 mm sind das Siebenfache der Toleranz und damit
# sicher ein Fehler — und zugleich so wenig, dass die Frage „fällt das
# überhaupt auf?" ihre Berechtigung behält.
SABOTAGE_MM = 107.0

# Bildmaße. Anders als bei den Standbildern (detailbild.py: BREITE = 1240) ist
# hier jedes Pixel 65-mal da — der Film hat 65 Einzelbilder. Der erste Entwurf
# mass 1240 x 772 und ließ rechts neben der Textspalte ein Drittel der Fläche
# leer. Die Tafel ist deshalb auf das zusammengezogen, was etwas zeigt.
#
# Bei 940 war sie zu schmal: nachgemessen liefen zwei der acht Prüfungsnamen
# und alle vier Zeilen des Schlussbildes über den rechten Rand hinaus. Am
# Standbild fiel es nicht auf, weil zufällig ein kurzer Name sichtbar war.
# Dagegen steht jetzt `_zeile()`, das bei Überlauf abbricht statt abzuschneiden.
BREITE = 1080
RAND = 40
BLATT_HOEHE = 620                       # Höhe der gezeichneten Seite in Pixeln

# Wie lange ein Bild steht, in Millisekunden. An der fertigen Datei nachgestellt,
# nicht gerechnet — dieselbe Begründung wie bei BILDDAUER_MS in detailbild.py.
FAHRT_MS = 40                           # während die Linie wandert
HALT_MS = 900                           # während sie an einem Maß steht
SCHLUSS_MS = 2600                       # das letzte Bild

# Wie viele Zwischenbilder die Linie von einem Maß zum nächsten braucht.
# Weniger wäre ein Sprung, mehr kostet Dateigröße ohne Gewinn.
FAHRT_BILDER = 7

KOPF = 108                              # Höhe der Überschriftzeile in Pixeln

ROT = (163, 47, 47)                     # nur für die Gegenprobe, sonst nie


# ── Rendern und Messen ──────────────────────────────────────────────────────

def rendere(brief: Path, ziel: Path, *, typst_dir: Path | None = None) -> tuple[Path, Path]:
    """Setzt den Brief einmal als PDF (zum Messen) und einmal als PNG (zum Zeigen).

    Gleiche Mechanik wie detailbild.rendere, aber mit eigener Auflösung: dort
    hängt sie an der Modulkonstante 600 ppi für den Lupenausschnitt. Die hier
    zu erben hieße, für jedes Einzelbild eine 4960 x 7016 große Vorlage zu
    schleppen, von der 95 Prozent weggerechnet würden.
    """
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


#: Rückgabewerte der CLI (cli.py: EXIT_OK, EXIT_EINGABE, EXIT_GEOMETRIE,
#: EXIT_UMGEBUNG = 0, 1, 2, 3). Der Film nimmt 0 und 2 an: 2 heißt „gemessen,
#: aber ein Maß hält nicht" — genau das Ergebnis, das die Gegenprobe braucht.
#: 1 und 3 heißen, dass gar nicht gemessen wurde; daraus einen Film zu bauen
#: hieße, eine leere Messung als bestandene auszugeben.
VERIFY_GEMESSEN = (0, 2)


def messe(pdf: Path) -> dict:
    """Der ganze Bericht aus `verify --json` — keine Zahl aus dieser Datei."""
    lauf = subprocess.run(
        [sys.executable, str(CLI), "verify", str(pdf), "--json"],
        capture_output=True, text=True, encoding="utf-8",
    )
    if lauf.returncode not in VERIFY_GEMESSEN:
        raise SystemExit(
            f"verify brach mit Rückgabewert {lauf.returncode} ab — es wurde gar "
            f"nicht gemessen:\n{lauf.stderr or lauf.stdout}"
        )
    return json.loads(lauf.stdout)


def pruefe_blatt(bericht: dict) -> None:
    """Ist das überhaupt das Blatt, das der Film zeichnet?"""
    nach_name = {p["name"]: p for p in bericht["pruefungen"]}
    for name, erwartet in (("Seitenbreite", BLATT_MM[0]), ("Seitenhöhe", BLATT_MM[1])):
        if name not in nach_name:
            raise SystemExit(
                f"„{name}“ steht nicht mehr im Bericht — der Film kann das Blatt "
                "nicht mehr nachmessen. Erst hier nachziehen, dann bauen."
            )
        ist = _zahl(nach_name[name]["ist"])
        if abs(ist - erwartet) > 0.5:
            raise SystemExit(
                f"{name}: {ist} mm statt {erwartet} mm. Der Film zeichnet ein "
                "A4-Blatt; bei einem anderen Format säßen alle Linien falsch."
            )


def stopps(bericht: dict) -> list[dict]:
    """Die Prüfungen mit einer Höhe auf dem Blatt, von oben nach unten.

    Bricht ab, wenn keine übrig bleibt oder ein Wert neben dem Blatt liegt.
    Beides hieße, dass sich an der Benennung oder an der Messung etwas geändert
    hat — und ein Film, der das stillschweigend übergeht, zeigt eine Ordnung,
    die es nicht mehr gibt.
    """
    gefunden = []
    for p in bericht["pruefungen"]:
        if not HOEHENMASS.search(p["name"]):
            continue
        try:
            y = _zahl(p["ist"])
        except SystemExit:
            continue
        if not 0.0 < y <= BLATT_MM[1]:
            raise SystemExit(
                f"„{p['name']}“ misst {y} mm — das liegt nicht auf einem "
                f"{BLATT_MM[1]:.0f} mm hohen Blatt. Der Film zeichnete eine Linie "
                "ins Nichts."
            )
        gefunden.append({
            "name": p["name"],
            "soll": p["soll"],
            "ist": p["ist"],
            "toleranz": p["toleranz"],
            "bestanden": p["bestanden"],
            "y_mm": y,
        })
    if not gefunden:
        raise SystemExit(
            "Keine Prüfung mit einer Höhe gefunden. Entweder heißen sie jetzt "
            "anders (dann HOEHENMASS nachziehen) oder der Bericht misst keine "
            "Höhen mehr (dann hat der Film keinen Gegenstand)."
        )
    return sorted(gefunden, key=lambda s: s["y_mm"])


def schlusszeile(bericht: dict) -> str:
    """Die Zählung aus dem Bericht, nicht aus diesem Skript.

    „Prüfungen", nicht „Maße": `verify --json` liefert den Geometriebericht,
    und der zählt 33. Die CLI meldet nach einem `render` eine mehr, weil sie
    zusätzlich die PDF/A-Konformität prüft — die liegt auf keinem Millimeter
    und hat im Film nichts zu suchen. Das README nennt deshalb an anderer Stelle
    34, und tests/test_satzspiegel.py hält es dort fest. Beide Zahlen stimmen;
    sie zählen Verschiedenes.
    """
    gesamt = len(bericht["pruefungen"])
    bestanden = sum(1 for p in bericht["pruefungen"] if p["bestanden"])
    return f"{bestanden} von {gesamt} Prüfungen eingehalten"


# ── Zeichnen ────────────────────────────────────────────────────────────────

def _komma(text: str) -> str:
    """Deutsche Schreibweise für die Zahlen aus dem Bericht."""
    return str(text).replace(".", ",")


def _textspalte(seitenbreite: int) -> tuple[int, int]:
    """Wo die Textspalte beginnt und wie breit sie ist."""
    x = RAND + seitenbreite + 44
    return x, BREITE - x - RAND


def _umbrich(zeichner, text: str, schrift, platz: int) -> list[str]:
    """Bricht an Wortgrenzen um, damit lange Prüfungsnamen nicht abreißen."""
    zeilen, laufend = [], ""
    for wort in text.split(" "):
        versuch = f"{laufend} {wort}".strip()
        if laufend and zeichner.textlength(versuch, font=schrift) > platz:
            zeilen.append(laufend)
            laufend = wort
        else:
            laufend = versuch
    if laufend:
        zeilen.append(laufend)
    return zeilen


def _zeile(zeichner, xy, text: str, schrift, fill, platz: int) -> None:
    """Schreibt eine Zeile — und bricht ab, wenn sie nicht in die Spalte passt.

    Ein abgeschnittener Text sieht auf dem Standbild aus wie ein absichtlich
    kurzer. Genau so ist es am 28.08. passiert: die Tafel war 140 px zu schmal,
    im angesehenen Einzelbild stand zufällig „Falzmarke 1, y“, und die beiden
    langen Namen sowie das ganze Schlussbild liefen unbemerkt über den Rand.
    """
    breite = zeichner.textlength(text, font=schrift)
    if breite > platz:
        raise SystemExit(
            f"„{text}“ braucht {breite:.0f} px, die Spalte hat {platz}. "
            "Entweder BREITE erhöhen oder die Schrift verkleinern — "
            "abschneiden wäre die stillste Art, das Bild falsch zu machen."
        )
    zeichner.text(xy, text, font=schrift, fill=fill)


def _seitenbild(seite, höhe: int):
    """Der Render, auf die Filmhöhe gebracht."""
    from PIL import Image

    faktor = höhe / seite.height
    return seite.resize((round(seite.width * faktor), höhe), Image.LANCZOS)


def _grundbild(seitenbild, schlusstext: str):
    """Alles, was in jedem Bild gleich bleibt — einmal gezeichnet.

    Das ist nicht nur Ordnung, sondern Dateigröße: Die Frames unterscheiden
    sich dadurch nur an der Linie und im Textfeld, und genau das komprimiert
    ein animiertes WebP weg.
    """
    from PIL import Image, ImageDraw

    höhe = KOPF + BLATT_HOEHE + 84
    tafel = Image.new("RGB", (BREITE, höhe), PAPIER)
    z = ImageDraw.Draw(tafel)

    z.text((RAND, 32), "Jedes Maß am fertigen PDF", font=_schrift(34, fett=True), fill=TINTE)
    z.text((RAND, 82), "Die Linie hält dort, wo gemessen wurde — die Zahl ist die Stelle.",
           font=_schrift(20), fill=GRAU)

    tafel.paste(seitenbild, (RAND, KOPF))
    z.rectangle(
        [(RAND, KOPF), (RAND + seitenbild.width - 1, KOPF + seitenbild.height - 1)],
        outline=GRAU, width=1,
    )
    z.text((RAND, KOPF + BLATT_HOEHE + 30), schlusstext,
           font=_schrift(20), fill=GRAU)
    return tafel


def _y_pixel(mm: float) -> int:
    """Millimeter auf dem Blatt -> Pixelzeile im gezeichneten Blatt."""
    return KOPF + round(mm / BLATT_MM[1] * BLATT_HOEHE)


def _tafel(grund, seitenbreite: int, y_mm: float, stopp: dict | None, fortschritt: str):
    """Ein Einzelbild: Grundbild plus Linie plus, wenn gehalten wird, das Textfeld."""
    from PIL import ImageDraw

    bild = grund.copy()
    z = ImageDraw.Draw(bild)

    y = _y_pixel(y_mm)
    x0, x1 = RAND, RAND + seitenbreite
    farbe = GRUEN if (stopp is None or stopp["bestanden"]) else ROT

    # Die Linie läuft über das Blatt und ein Stück darüber hinaus, damit sie
    # als Werkzeug lesbar bleibt und nicht als Strich auf dem Brief.
    z.line([(x0 - 14, y), (x1 + 14, y)], fill=farbe, width=3)
    z.polygon([(x1 + 14, y - 7), (x1 + 26, y), (x1 + 14, y + 7)], fill=farbe)

    # Rechts die Maßangabe zur laufenden Linie, immer sichtbar.
    text_x, platz = _textspalte(seitenbreite)
    _zeile(z, (text_x, KOPF), fortschritt, _schrift(20), GRAU, platz)

    if stopp is not None:
        name_schrift = _schrift(28, fett=True)
        namenszeilen = _umbrich(z, stopp["name"], name_schrift, platz)
        feld_höhe = len(namenszeilen) * 36 + 150

        # Das Feld folgt der Linie, bleibt aber im Bild: ein Maß nahe der
        # Blattunterkante schöbe es sonst über den Rand, und die Angabe zum
        # letzten Halt wäre abgeschnitten.
        kopf_y = min(max(y - 58, KOPF + 40), bild.height - feld_höhe)

        for nummer, zeile in enumerate(namenszeilen):
            _zeile(z, (text_x, kopf_y + nummer * 36), zeile, name_schrift, TINTE, platz)
        unter_name = kopf_y + len(namenszeilen) * 36 + 12

        for nummer, zeile in enumerate((
            f"soll  {_komma(stopp['soll'])}",
            f"ist   {_komma(stopp['ist'])}",
            f"tol   {_komma(stopp['toleranz'])}",
        )):
            _zeile(z, (text_x, unter_name + nummer * 30), zeile, _schrift(24), TINTE, platz)

        _zeile(z, (text_x, unter_name + 104),
               "eingehalten" if stopp["bestanden"] else "ABWEICHUNG",
               _schrift(24, fett=True), GRUEN_TEXT if stopp["bestanden"] else ROT, platz)
    return bild


def _schlussbild(grund, seitenbreite: int, bericht: dict, halte: list[dict]):
    """Was der Film gezeigt hat — und was er nicht zeigen konnte."""
    from PIL import ImageDraw

    bild = grund.copy()
    z = ImageDraw.Draw(bild)
    text_x, platz = _textspalte(seitenbreite)

    for stopp in halte:
        y = _y_pixel(stopp["y_mm"])
        z.line([(RAND - 14, y), (RAND + seitenbreite + 14, y)], fill=GRUEN, width=2)

    ohne_hoehe = len(bericht["pruefungen"]) - len(halte)
    # 28 pt statt 32: „33 von 33 Prüfungen eingehalten" braucht bei 32 pt
    # 565 px und passt nicht in die 518 der Spalte. `_zeile` hat es gemeldet,
    # statt es abzuschneiden — dafür steht es dort.
    _zeile(z, (text_x, 150), schlusszeile(bericht), _schrift(28, fett=True), TINTE, platz)

    absaetze = (
        (f"{len(halte)} davon tragen eine Höhe auf dem Blatt —",
         "an ihnen hat die Linie gehalten."),
        (f"Die übrigen {ohne_hoehe} messen Breiten, Abstände",
         "und Eigenschaften ohne Ort auf der Seite."),
        ("Nichts davon ist abgetippt:",
         "jede Zahl kommt aus falzmarke verify."),
        ("Die CLI zählt eine Prüfung mehr: sie sieht",
         "auch die PDF/A-Konformität nach.",
         "Die liegt auf keinem Millimeter."),
    )
    y = 212
    for absatz in absaetze:
        for zeile in absatz:
            _zeile(z, (text_x, y), zeile, _schrift(22), GRAU, platz)
            y += 32
        y += 22
    return bild


def baue_film(seite, bericht: dict) -> tuple[list, list[int]]:
    """Die Einzelbilder des Films und ihre Standzeiten."""
    halte = stopps(bericht)
    seitenbild = _seitenbild(seite, BLATT_HOEHE)
    grund = _grundbild(seitenbild, "Beispielbrief, Form B — gesetzt und danach nachgemessen.")
    breite = seitenbild.width
    gesamt = len(halte)

    frames, dauern = [], []
    vorher = 0.0
    for nummer, stopp in enumerate(halte, start=1):
        fortschritt = f"Maß {nummer} von {gesamt} mit Höhe"
        # Anfahrt: die Linie wandert vom letzten Halt zum nächsten.
        for schritt in range(1, FAHRT_BILDER + 1):
            y = vorher + (stopp["y_mm"] - vorher) * schritt / FAHRT_BILDER
            frames.append(_tafel(grund, breite, y, None, fortschritt))
            dauern.append(FAHRT_MS)
        # Halt: dieselbe Zeile, jetzt mit dem Messwert daneben.
        frames.append(_tafel(grund, breite, stopp["y_mm"], stopp, fortschritt))
        dauern.append(HALT_MS)
        vorher = stopp["y_mm"]

    frames.append(_schlussbild(grund, breite, bericht, halte))
    dauern.append(SCHLUSS_MS)
    return frames, dauern


# ── Ablauf ──────────────────────────────────────────────────────────────────

def baue(sabotiert: bool = False) -> dict:
    """Rendert, misst und zeichnet. Mit `sabotiert` aus einem kaputten Layout."""
    with tempfile.TemporaryDirectory(prefix="falzmarke-messfilm-") as tmp:
        arbeit = Path(tmp)
        typst_dir = None
        if sabotiert:
            typst_dir = sabotiere(
                arbeit, "vendor/letter-pro-v3.0.0.typ",
                "folding-mark-1-pos: 105mm", f"folding-mark-1-pos: {SABOTAGE_MM:.0f}mm",
            )
        pdf, png = rendere(BRIEF, arbeit, typst_dir=typst_dir)
        bericht = messe(pdf)
        pruefe_blatt(bericht)
        halte = stopps(bericht)

        if not sabotiert and not bericht["ok"]:
            gescheitert = [p["name"] for p in bericht["pruefungen"] if not p["bestanden"]]
            raise SystemExit(
                "Das ausgelieferte Layout hält seine eigenen Maße nicht ein: "
                f"{', '.join(gescheitert)}.\n"
                "Erst den Fehler beheben — ein Schaufensterfilm eines kaputten "
                "Layouts wäre die teuerste Art, ihn zu verstecken."
            )

        frames, dauern = baue_film(_bild(png), bericht)
        return {"bericht": bericht, "stopps": halte, "frames": frames, "dauern": dauern}


def beleg(gebaut: dict) -> dict:
    return {
        "hinweis": "Erzeugt aus einem echten Render — nicht von Hand ändern. "
                   "Neu bauen: python3 scripts/messfilm.py",
        "brief": BRIEF.name,
        "ppi": PPI,
        "blatt_mm": list(BLATT_MM),
        "schlusszeile": schlusszeile(gebaut["bericht"]),
        "pruefungen_gesamt": len(gebaut["bericht"]["pruefungen"]),
        "sabotage_mm": SABOTAGE_MM,
        "stopps": [
            {"name": s["name"], "soll": s["soll"], "ist": s["ist"],
             "toleranz": s["toleranz"], "y_mm": s["y_mm"]}
            for s in gebaut["stopps"]
        ],
    }


def schreibe(gebaut: dict) -> None:
    frames, dauern = gebaut["frames"], gebaut["dauern"]
    ZIEL_DIR.mkdir(parents=True, exist_ok=True)

    gif = ZIEL_DIR / "messfilm.gif"
    frames[0].save(
        gif, save_all=True, append_images=frames[1:], duration=dauern,
        loop=0, optimize=True,
    )
    print(f"  {gif.relative_to(REPO)}  {frames[0].width}x{frames[0].height}  "
          f"{len(frames)} Bilder  {gif.stat().st_size / 1024:.0f} KB")

    # Die Webfassung muss unter das Bildbudget der Website (cw-core
    # Perf-Budget-Guard, 200 KB je Bild). Gemessen am 28.08.2026 an genau diesem
    # Film — 65 Bilder, 940 x 812, an den Bildern, die dieses Skript selbst
    # erzeugt:
    #
    #   quality  minimize_size   Größe
    #   72       aus             440 KB   übers Budget
    #   72       an              154 KB   <- gewählt
    #   60       an              141 KB
    #   50       an              132 KB
    #   40       an              122 KB
    #
    # Die Ersparnis kommt fast vollständig aus `minimize_size`, nicht aus der
    # Qualität: 440 auf 154 KB durch den Schalter, weitere 32 KB durch das
    # Absenken von 72 auf 40. Das passt zur Sache — teuer sind nicht die Details
    # des Briefes (ein Einzelbild kostet bei q=72 nur 24 KB), sondern die
    # 65 Bilder, und zwischen ihnen ändern sich nur Linie und Textfeld. Der
    # Film bleibt deshalb auf voller Qualität; den Brieftext weichzurechnen
    # hätte 20 KB gebracht und die Lesbarkeit gekostet.
    #
    # Eine frühere Fassung dieser Tabelle nannte 194 KB für q=50 und schloss
    # daraus, man müsse die Qualität senken. Sie maß am falschen Gegenstand:
    # an den aus dem GIF zurückgelesenen Bildern. Der GIF-Umweg quantisiert auf
    # 256 Farben und trägt Rauschen ein, das der WebP-Kodierer dann mitspeichert.
    webp = ZIEL_DIR / "messfilm.webp"
    frames[0].save(
        webp, save_all=True, append_images=frames[1:], duration=dauern,
        loop=0, quality=72, method=6, minimize_size=True,
    )
    kb = webp.stat().st_size / 1024
    print(f"  {webp.relative_to(REPO)}  {kb:.0f} KB"
          f"{'' if kb <= 200 else '   ÜBER dem 200-KB-Budget der Website'}")


def main() -> int:
    zerleger = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    zerleger.add_argument("--pruefen", action="store_true",
                          help="nur melden, ob die Zahlen im Repo zum Lauf passen")
    args = zerleger.parse_args()

    gebaut = baue()
    neu = json.dumps(beleg(gebaut), ensure_ascii=False, indent=2) + "\n"

    if args.pruefen:
        if not BELEG.is_file():
            print(f"FEHLT  {BELEG.relative_to(REPO)} — einmal ohne --pruefen laufen lassen")
            return 1
        if BELEG.read_text(encoding="utf-8") != neu:
            print(f"VERALTET  {BELEG.relative_to(REPO)} passt nicht zum Lauf.\n"
                  "Der Film zeigt dann Zahlen, die es so nicht mehr gibt.\n"
                  "Neu bauen: python3 scripts/messfilm.py")
            return 1
        print(f"OK  Film und Messwerte stimmen überein "
              f"({len(gebaut['stopps'])} Halte, {schlusszeile(gebaut['bericht'])})")
        return 0

    schreibe(gebaut)
    BELEG.write_text(neu, encoding="utf-8")
    print(f"  {BELEG.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
