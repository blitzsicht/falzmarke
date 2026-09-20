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
import tabellenmessung

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


# ── Die Ausnahme steht dokumentiert (#151) ──────────────────────────────────
#
# Beschlossen am 20.09.2026: Die Lesbarkeit gewinnt, der Innenabstand bleibt bei
# 1,4 mm, und Tabellen bleiben von der Rasterprüfung ausgenommen. Die Begründung
# steht an EINER Stelle — im Docstring von `geometrie._tabellenbereiche`, dem
# Ort, an dem die Ausnahme greift. Die Referenz sagt nur, DASS es so ist.

REFERENZ = REPO / "skill" / "references" / "markdown.md"


def _komma(wert: float) -> str:
    return f"{wert:.2f}".replace(".", ",")


def _docstring() -> str:
    doc = geometrie._tabellenbereiche.__doc__
    assert doc, "`_tabellenbereiche` hat keinen Docstring — die Begründung fehlt"
    return doc


def test_die_tabellenausnahme_steht_in_der_referenz():
    """Sie stand nur im Regelwerk und im Code-Kommentar.

    Ein Nutzer, der die Referenz liest, erfuhr nichts davon — und wunderte sich,
    warum unterhalb seiner Tabelle alles verschoben ist. #151 verlangt für den
    Fall „bleibt wie es ist" ausdrücklich, dass es dokumentiert steht „statt
    still zu gelten". Die Messwerte stehen dort nicht mehr, siehe unten.
    """
    text = REFERENZ.read_text(encoding="utf-8")
    assert "Tabellen sind davon ausgenommen" in text


def test_die_referenz_nennt_die_frage_nicht_mehr_als_offen():
    """Die Abwägung ist getroffen. Stünde dort weiter „ob es dabei bleibt, ist
    offen", widerspräche die Referenz dem Beschluss — und läse sich wie ein
    Zwischenstand, den niemand mehr abschließt."""
    text = REFERENZ.read_text(encoding="utf-8")
    assert "Ob es dabei bleibt" not in text
    assert "ist offen" not in text[text.index("Eine Tabelle steht nicht auf dem Zeilenraster"):]


def test_der_docstring_traegt_die_entscheidung():
    """AC 1: gewollt, mit dem Innenabstand und dem Preis der Alternative."""
    doc = _docstring()
    assert "gewollt" in doc, "die Ausnahme ist nicht als gewollt benannt"
    assert "1,4 mm" in doc, "der Innenabstand, um den es geht, fehlt"
    assert "9 mm" in doc, "der Preis des rastertreuen Wegs fehlt (fünfzeilige Tabelle +9 mm)"
    assert "20.09.2026" in doc, "ohne Datum ist nicht zu sehen, wann und ob sie noch gilt"


def test_der_docstring_nennt_die_frage_nicht_mehr_als_offen():
    """Bis zum Beschluss stand dort: „gehört entschieden, nicht von einer
    Prüfung erzwungen". Nach dem Beschluss ist der Satz falsch."""
    doc = _docstring()
    assert "gehört entschieden" not in doc
    assert "ist offen" not in doc


def test_die_dokumentierten_zahlen_sind_die_gemessenen(gerendert):
    """Eine Zahl in einem Docstring altert still — dieser Test liest sie gegen
    das PDF. Ändert sich die Zeilenhöhe, stimmt die Dokumentation nicht mehr,
    und das fällt hier auf statt erst, wenn jemand nachmisst.

    Gemessen wird in Rasterzeilen (Höhe / Grundzeile), so wie der Vorgang die
    Werte nennt: 1,58 innerhalb, 2,33 an den beiden Übergängen.
    """
    pdf, _ = gerendert["brief-tabelle"]
    doc = _docstring()

    zeile = tabellenmessung.zeilenhoehen_mm(pdf)[0] / geometrie.GRUNDZEILE
    eintritte, austritte = tabellenmessung.uebergaenge_mm(pdf)
    assert eintritte and austritte, "keine Übergänge gemessen — der Test misst nichts"
    eintritt = eintritte[0] / geometrie.GRUNDZEILE
    austritt = austritte[0] / geometrie.GRUNDZEILE

    gemessen = {"Tabellenzeile": _komma(zeile), "Eintritt": _komma(eintritt),
                "Austritt": _komma(austritt)}
    # Erst die Sollwerte des Vorgangs: Stimmte die Messung selbst nicht, käme
    # der Docstring nie auf eine richtige Zahl — und der Fehler läge hier.
    assert gemessen == {"Tabellenzeile": "1,58", "Eintritt": "2,33", "Austritt": "2,33"}, gemessen
    fehlen = {name: zahl for name, zahl in gemessen.items() if zahl not in doc}
    assert not fehlen, f"gemessen, aber im Docstring nicht zu finden (Rasterzeilen): {fehlen}"


def test_die_messwerte_stehen_an_einer_stelle():
    """AC 1: „An einer Stelle, nicht an zweien." Zwei Fassungen derselben Zahl
    laufen auseinander — die Referenz trug 1,58 schon, und der Docstring soll
    sie bekommen, ohne dass sie danach an zwei Orten stehen.

    Gesucht wird in allem, was Prosa oder Regelwerk ist: Quelltext des Pakets,
    Referenzen, Dokumentation, READMEs. Nicht in Changelog und Tests — ein
    Changelog-Eintrag nennt den Wert, ohne ihn zu begründen, und ein Test ist
    die Messung, nicht die Aussage.
    """
    kandidaten = [
        *(REPO / "skill").rglob("*.py"),
        *(REPO / "skill").rglob("*.md"),
        *(REPO / "skill").rglob("*.yaml"),
        *(REPO / "docs").rglob("*.md"),
        *REPO.glob("README*.md"),
    ]
    orte = sorted(p.relative_to(REPO).as_posix() for p in kandidaten
                  if "1,58" in p.read_text(encoding="utf-8"))
    assert orte == ["skill/falzmarke/geometrie.py"], (
        f"die Zeilenhöhe 1,58 steht an {len(orte)} Stellen: {orte}")


# ── Die Ausnahme wächst nicht (#151) ────────────────────────────────────────
#
# Die Rasterprüfung nimmt Tabellen aus — und damit ist ihr auch gleich, wie hoch
# eine Zeile ist. Wer den Innenabstand ändert, sieht keinen roten Test, obwohl
# alles unterhalb der Tabelle verrutscht. Diese Messung schließt das: Sie nimmt
# die Zeilenhöhe fest, statt sie zu erlauben.

def test_eine_tabellenzeile_ist_so_hoch_wie_beschlossen(gerendert):
    """AC 2: die tatsächliche Höhe im gerenderten PDF, Zeile für Zeile."""
    pdf, _ = gerendert["brief-tabelle"]
    hoehen = tabellenmessung.zeilenhoehen_mm(pdf)
    # Kopfzeile plus vier Zeilen. Eine kleinere Zahl hieße, dass Linien
    # verloren gingen, und die Schleife unten prüfte weniger, als sie sagt.
    assert len(hoehen) >= 4, f"zu wenige Zeilen gemessen: {hoehen}"
    for nummer, hoehe in enumerate(hoehen, start=1):
        assert abs(hoehe - tabellenmessung.ZEILENHOEHE_MM) <= tabellenmessung.TOLERANZ_MM, (
            f"Zeile {nummer}: {hoehe:.3f} mm statt {tabellenmessung.ZEILENHOEHE_MM} mm "
            f"— der Innenabstand der Zellen hat sich geändert (#151); alle: "
            f"{[round(h, 3) for h in hoehen]}")


def test_die_uebergaenge_sind_so_lang_wie_beschlossen(gerendert):
    """Die beiden Übergänge sind mit ausgenommen und messen sonst niemand:
    2,33 Rasterzeilen, nicht ganzzahlig, und beschlossen ist, dass es dabei
    bleibt."""
    pdf, _ = gerendert["brief-tabelle"]
    eintritte, austritte = tabellenmessung.uebergaenge_mm(pdf)
    assert len(eintritte) == 1 and len(austritte) == 1, (eintritte, austritte)
    assert abs(eintritte[0] - tabellenmessung.EINTRITT_MM) <= tabellenmessung.TOLERANZ_MM, eintritte
    assert abs(austritte[0] - tabellenmessung.AUSTRITT_MM) <= tabellenmessung.TOLERANZ_MM, austritte


def test_der_sollwert_stammt_nicht_aus_emit():
    """AC 3: Ein Sollwert aus derselben Konstante, gegen die er prüft, bliebe
    grün, wenn jemand den Innenabstand ändert. Gelesen wird der Quelltext als
    Syntaxbaum: Der Kommentar oben nennt `emit`, und eine Textsuche träfe ihn."""
    import ast

    baum = ast.parse((Path(__file__).parent / "tabellenmessung.py").read_text(encoding="utf-8"))
    eingebunden = set()
    for knoten in ast.walk(baum):
        if isinstance(knoten, ast.Import):
            eingebunden |= {a.name for a in knoten.names}
        elif isinstance(knoten, ast.ImportFrom):
            eingebunden.add(knoten.module or "")
            eingebunden |= {f"{knoten.module}.{a.name}" for a in knoten.names}
    assert eingebunden, "keine Importe gefunden — der Test misst nichts"
    assert not [name for name in eingebunden if name.split(".")[-1] == "emit"
                or name.startswith("falzmarke.emit")], eingebunden
