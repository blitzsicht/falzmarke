"""Der Briefkörper steht auf dem 12-pt-Raster (Issue #140).

Bis hierher war das eine Zusage von `falzmarke.typ` und sonst nichts. Gemessen
beim Einbau der Überschriften: Ein Abstand von `leer(n) + 2,6 mm` verändert das
PDF messbar — von 53.245 auf 53.300 Byte — und **alle vierzig Prüfungen blieben
grün**. Die Geometrieprüfung misst Ränder, Zonen und den untersten Text, nicht
die Lage der Zeilen.

Ein Rasterversatz ist die Fehlerart, die man auf einem Ausdruck nicht sieht und
auf zwei nebeneinandergelegten Blättern sofort. Er summiert sich: zwei
Millimeter je Überschrift sind nach vier Abschnitten fast eine Zeile.
"""

from __future__ import annotations

import re
import shutil
import tempfile
from pathlib import Path

import pytest

from falzmarke import geometrie
from falzmarke import cli as falzmarke
from conftest import BEISPIELE, REPO

TYPST = REPO / "skill" / "falzmarke" / "typst" / "falzmarke.typ"


def _rendere_mit(alt: str, neu: str, beispiel: str = "brief-form-b"):
    """Rendert mit einer an genau einer Stelle geänderten Satzdatei."""
    tmp = Path(tempfile.mkdtemp())
    shutil.copytree(REPO / "skill" / "falzmarke" / "typst", tmp / "typst")
    pfad = tmp / "typst" / "falzmarke.typ"
    inhalt = pfad.read_text(encoding="utf-8")
    assert alt in inhalt, f"Ankertext fehlt: {alt[:50]!r}"
    pfad.write_text(inhalt.replace(alt, neu, 1), encoding="utf-8")

    original = falzmarke.TYPST_DIR
    falzmarke.TYPST_DIR = tmp / "typst"
    try:
        pdf, form = falzmarke.rendere(REPO / "examples" / f"{beispiel}.md",
                                      tmp / "x.pdf",
                                      profil_verzeichnis=tmp / "typst" / "profiles")
    finally:
        falzmarke.TYPST_DIR = original
    bericht = geometrie.pruefe(pdf, form)
    return {p.name for p in bericht.pruefungen if not p.bestanden}, pdf


# ── Die Zahl steht an zwei Stellen ──────────────────────────────────────────

def test_die_grundzeile_stimmt_mit_dem_satz_ueberein():
    """`GRUNDZEILE` hier und `#let zeile` dort — zwei Orte, eine Zahl."""
    quelle = TYPST.read_text(encoding="utf-8")
    treffer = re.search(r"#let zeile = ([\d.]+)mm", quelle)
    assert treffer, "`#let zeile` nicht gefunden — der Test misst nichts"
    assert abs(float(treffer.group(1)) - geometrie.GRUNDZEILE) < 0.0001


# ── Alle Beispiele halten das Raster ────────────────────────────────────────

@pytest.mark.parametrize("name", [p.stem for p in BEISPIELE])
def test_beispiel_steht_auf_dem_raster(gerendert, name):
    pdf, form = gerendert[name]
    bericht = geometrie.pruefe(pdf, form)
    schiefe = [p for p in bericht.pruefungen
               if "Zeilenraster" in p.name and not p.bestanden]
    assert not schiefe, [f"{p.name}: {p.ist}" for p in schiefe]


def test_die_pruefung_misst_ueberhaupt_etwas(gerendert):
    """Gegenprobe: Über null Abständen wäre der Test darüber immer grün.

    Der Bericht nennt die Zahl der gemessenen Abstände — sie muss deutlich über
    null liegen, sonst hat die Auswahl (11 pt, oberhalb des Fußbereichs, ausser
    Tabellen) alles weggeschnitten.
    """
    pdf, form = gerendert["brief-form-b"]
    bericht = geometrie.pruefe(pdf, form)
    raster = [p for p in bericht.pruefungen if "Zeilenraster" in p.name]
    assert raster, "keine Rasterprüfung im Bericht"
    # Der Bericht sagt „15× eingehalten". Die Zahl davor ist die Zahl der
    # gemessenen Abstände; die Formulierung wurde gekürzt, damit die Zeile in
    # das Terminal der GIF-Aufnahme passt (tests/test_tape.py).
    treffer = re.search(r"(\d+)×", raster[0].ist)
    assert treffer, raster[0].ist
    assert int(treffer.group(1)) >= 8, raster[0].ist


# ── Und sie kann rot werden ─────────────────────────────────────────────────

SABOTAGEN = [
    ("Absatzabstand um 2,6 mm verschoben",
     "block(above: leer(1), below: 0pt, body)",
     "block(above: leer(1) + 2.6mm, below: 0pt, body)"),
    ("Absatzabstand um 1,0 mm verschoben",
     "block(above: leer(1), below: 0pt, body)",
     "block(above: leer(1) + 1.0mm, below: 0pt, body)"),
    ("Zeilenabstand um 0,4 mm verschoben",
     "set par(justify: false, leading: durchschuss, spacing: leer(1))",
     "set par(justify: false, leading: durchschuss + 0.4mm, spacing: leer(1))"),
    ("Signaturhöhe zurück auf 2,5 Zeilen",
     "height: 3 * zeile - durchschuss,",
     "height: 2.5 * zeile,"),
]


@pytest.mark.parametrize("was,alt,neu", SABOTAGEN, ids=[s[0][:28] for s in SABOTAGEN])
def test_ein_rasterversatz_faellt_auf(was, alt, neu):
    """Ohne diese Fälle wüsste die Prüfung nur, dass sie grün ist."""
    gescheitert, _ = _rendere_mit(alt, neu)
    assert any("Zeilenraster" in name for name in gescheitert), \
        f"{was} blieb unbemerkt; rot war: {gescheitert or 'nichts'}"


def test_die_kontrollprobe_ist_gruen():
    """Ohne Änderung darf nichts anschlagen — sonst misst die Sabotage nur die
    Kopie des Verzeichnisses."""
    gescheitert, _ = _rendere_mit("#let zeile = 4.2333mm", "#let zeile = 4.2333mm")
    assert gescheitert == set()


def test_die_signaturhoehe_war_der_grund(gerendert):
    """Sechs Beispiele standen wegen des Signaturbildes daneben.

    Ein Bild hat keinen Zeilenkasten, also greift die Kompensation nicht, die
    `leer(n)` für Textblöcke einrechnet. `2.5 * zeile` ergab 5,58 Rasterzeilen
    zwischen Gruß und Unterzeichner statt eines ganzen Vielfachen.
    """
    quelle = TYPST.read_text(encoding="utf-8")
    assert "height: 3 * zeile - durchschuss," in quelle
    assert "height: 2.5 * zeile," not in quelle


# ── Tabellen sind ausgenommen, und zwar erkannt ─────────────────────────────

def test_tabellen_werden_an_ihren_linien_erkannt(gerendert):
    pdf, _ = gerendert["brief-tabelle"]
    dokument = geometrie._oeffne(pdf)
    bereiche = geometrie._tabellenbereiche(dokument.pages[0])
    assert bereiche, "kein Tabellenbereich gefunden — die Ausnahme greift ins Leere"
    a, b = bereiche[0]
    assert b - a > 10, f"Bereich zu schmal: {a:.1f}–{b:.1f} mm"


def test_ein_brief_ohne_tabelle_hat_keinen_tabellenbereich(gerendert):
    """Gegenprobe: Die Erkennung darf nicht überall anschlagen — sonst wäre der
    halbe Brief ausgenommen, ohne dass es jemandem auffiele."""
    pdf, _ = gerendert["brief-kuendigung"]
    dokument = geometrie._oeffne(pdf)
    assert geometrie._tabellenbereiche(dokument.pages[0]) == []


def test_falzmarken_gelten_nicht_als_tabelle(gerendert):
    """Sie sind waagerechte Linien, liegen aber im Heftrand — und es sind zwei,
    keine drei."""
    pdf, _ = gerendert["brief-kuendigung"]
    dokument = geometrie._oeffne(pdf)
    seite = dokument.pages[0]
    waagerecht = [l for l in seite.lines if abs(l["y0"] - l["y1"]) < 0.3]
    assert waagerecht, "keine Linien — der Test misst nichts"
    assert geometrie._tabellenbereiche(seite) == []
