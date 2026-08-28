"""Der Briefkörper bleibt auf jeder Seite im Satzspiegel (Issue #35).

WAS HIER GEPRÜFT WIRD, UND WARUM ES VORHER FEHLTE

Die Geometrieprüfung mass bis hierher den **Vordruck**: Anschriftfeld,
Falzmarken, Informationsblock. Für den Text gab es genau zwei Messungen, und
beide liefen auf `dokument.pages[0]` — `pruefe()` setzt `seite = pages[0]` und
misst alles daran. Ein mehrseitiger Brief konnte ab Seite 2 beliebig aus dem
Satzspiegel laufen und trotzdem „Maße eingehalten" melden.

Das ist kein theoretischer Fall. `ueberlauf-auf-seite-zwei.md` ist genau das:
Seite 1 sitzt sauber bei 190,00 mm, Seite 2 läuft auf 190,88 — und vor dieser
Änderung schlug **keine einzige** Prüfung an.

WARUM DIE PRÜFUNG KEINE AUSNAHMEN KENNT

Sie misst alle Spans jeder Seite, ohne Briefkopf oder Fusszeile auszunehmen.
Das ist gemessen, nicht angenommen: In allen neun Beispielbriefen liegen
sämtliche Spans auf sämtlichen Seiten exakt zwischen 25,00 und 190,00 mm. Eine
Ausnahmeliste wäre ein zweiter Ort, an dem sich ein Layoutfehler verstecken
könnte.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from falzmarke import geometrie
from conftest import REPO

FIXTURES = REPO / "tests" / "fixtures" / "satzspiegel"


def _rendere(quelle: Path, ziel: Path) -> Path:
    """Rendert ohne Prüfung — die Prüfung ist hier der Gegenstand, nicht das Mittel."""
    lauf = subprocess.run(
        [sys.executable, str(REPO / "skill" / "scripts" / "falzmarke.py"),
         "render", str(quelle), "-o", str(ziel)],
        capture_output=True, text=True,
    )
    # Der Renderer meldet den Fehlschlag der Prüfung mit eigenem Exit-Code; das
    # PDF entsteht trotzdem. Genau darauf zielen die Fixtures.
    assert ziel.exists(), f"kein PDF entstanden: {lauf.stderr[:300]}"
    return ziel


def _befunde(pdf: Path) -> list:
    return [p for p in geometrie.pruefe(pdf, "B").pruefungen if not p.bestanden]


# ── die Beispiele bleiben sauber ────────────────────────────────────────────

@pytest.mark.parametrize("brief", sorted((REPO / "examples").glob("*.md")), ids=lambda p: p.stem)
def test_beispiele_bleiben_im_satzspiegel(brief, tmp_path):
    """Jeder Beispielbrief, jede Seite.

    Ohne diesen Test wüsste die Suite nur, dass die Prüfung bei kaputten Briefen
    anschlägt — nicht, dass sie bei richtigen schweigt. Ein Prüfmittel, das
    immer rot ist, wäre genauso wertlos wie eines, das nie rot wird.
    """
    pdf = _rendere(brief, tmp_path / f"{brief.stem}.pdf")
    satzspiegel = [p for p in _befunde(pdf) if p.name.startswith("Seite ")]
    assert not satzspiegel, [f"{p.name}: {p.ist}" for p in satzspiegel]


# ── und schlagen bei den kaputten an ────────────────────────────────────────

def test_zu_breite_tabelle_wird_gefangen(tmp_path):
    """AC3 des Issues, wörtlich: eine zu breite Tabelle muss rot werden."""
    pdf = _rendere(FIXTURES / "tabelle-zu-breit.md", tmp_path / "breit.pdf")
    befunde = _befunde(pdf)
    assert any(p.name == "Seite 1, rechter Rand" for p in befunde), \
        [p.name for p in befunde]


def test_ueberschrift_ohne_trennstelle_wird_gefangen(tmp_path):
    """Der erste Fall aus Dialekt 1.1 — und ein anderer, als hier stand.

    Der README dieses Ordners hielt fest, ein langes Wort laufe nicht ueber:
    Typst bricht es um. Das stimmt **im Absatz**, nachgemessen. In einer
    Ueberschrift stimmt es nicht — dort steht das Wort am Zeilenanfang, es gibt
    keinen vorangehenden Umbruchpunkt, und Typst laesst es durchlaufen.
    Gemessen: 359,35 mm statt hoechstens 190,00.

    Genau dafuer war Issue #35 die Vorbedingung von #26.
    """
    pdf = _rendere(FIXTURES / "ueberschrift-ohne-trennstelle.md", tmp_path / "kopf.pdf")
    befunde = _befunde(pdf)
    assert any(p.name == "Seite 1, rechter Rand" for p in befunde), \
        [p.name for p in befunde]


def test_zu_lange_codezeile_wird_gefangen(tmp_path):
    """Der zweite Fall aus Dialekt 1.1.

    Ein wortgetreuer Auszug darf nicht umbrochen werden — sonst waere er nicht
    mehr wortgetreu. Also laeuft er ueber, und das muss auffallen. Gemessen:
    ein Auszug fasst 68 Zeichen je Zeile (Inline-Code 70, ihm fehlt der Einzug
    des Blocks); ab 69 steht Text ausserhalb. Der Wert gilt fuer die
    Festbreitenschrift, die `falzmarke.typ` waehlt — eine andere weicht ab.
    """
    pdf = _rendere(FIXTURES / "codezeile-zu-lang.md", tmp_path / "code.pdf")
    befunde = _befunde(pdf)
    assert any(p.name == "Seite 1, rechter Rand" for p in befunde), \
        [p.name for p in befunde]


def test_ueberlauf_auf_seite_zwei_wird_gefangen(tmp_path):
    """Der eigentliche Grund für Issue #35.

    Vor dieser Änderung war dieser Brief grün: Die einzige Prüfung des rechten
    Randes hiess `Textblock, x-rechts` und las `dokument.pages[0]`.
    """
    pdf = _rendere(FIXTURES / "ueberlauf-auf-seite-zwei.md", tmp_path / "seite2.pdf")
    befunde = _befunde(pdf)
    namen = [p.name for p in befunde]
    assert "Seite 2, rechter Rand" in namen, namen


def test_nur_die_betroffene_seite_wird_gemeldet(tmp_path):
    """Sonst wäre die Meldung wertlos: Seite 1 ist in dieser Datei in Ordnung.

    Eine Prüfung, die bei einem Fehler auf Seite 2 auch Seite 1 anschwärzt,
    schickt beim Suchen auf die falsche Seite.
    """
    pdf = _rendere(FIXTURES / "ueberlauf-auf-seite-zwei.md", tmp_path / "seite2.pdf")
    namen = [p.name for p in _befunde(pdf)]
    assert "Seite 1, rechter Rand" not in namen, namen


def test_bericht_nennt_seite_und_element(tmp_path):
    """AC4: „ausserhalb" allein sagt niemandem, wo er suchen soll."""
    pdf = _rendere(FIXTURES / "ueberlauf-auf-seite-zwei.md", tmp_path / "seite2.pdf")
    treffer = next(p for p in _befunde(pdf) if p.name == "Seite 2, rechter Rand")
    assert "Seite 2" in treffer.name
    assert "1234567" in treffer.ist, treffer.ist   # der Zelleninhalt, der übersteht
    assert "190" in treffer.ist


# ── Gegenprobe: misst die Prüfung wirklich, oder läuft sie nur? ─────────────

def test_gegenprobe_die_pruefung_haengt_am_gemessenen_wert(tmp_path, monkeypatch):
    """Der Nachweis, dass die Prüfung trennt statt nur zu laufen.

    Verschoben wird die Schwelle, nicht der Brief: Bei einem rechten Rand von
    100 mm muss ein Brief, der eben noch bestand, durchfallen — und zwar mit
    genau der Meldung, die auch im Ernstfall käme. Eine Prüfung, die das nicht
    tut, misst etwas anderes als den Wert, den sie im Bericht nennt.

    Eine reine Arithmetik-Behauptung („190,31 ist grösser als 190,3") stand hier
    zuerst. Sie hätte auch dann bestanden, wenn `_satzspiegel` gar nicht
    aufgerufen würde.
    """
    brief = REPO / "examples" / "brief-form-b.md"
    pdf = _rendere(brief, tmp_path / "sauber.pdf")
    assert not [p for p in _befunde(pdf) if p.name.startswith("Seite ")], \
        "Voraussetzung verletzt: dieser Brief muss vorher sauber sein"

    monkeypatch.setattr(geometrie, "RAND_RECHTS", 100.0)
    befunde = [p for p in _befunde(pdf) if p.name == "Seite 1, rechter Rand"]
    assert befunde, "verschobene Schwelle blieb folgenlos — die Prüfung liest sie nicht"
    assert "190" in befunde[0].ist


def test_pruefung_deckt_alle_seiten_ab(tmp_path):
    """Zählt nach, statt zu vertrauen.

    Bei zwei Seiten müssen sechs Satzspiegel-Prüfungen entstehen — drei je
    Seite. Fiele die Schleife auf `pages[0]` zurück, wären es drei, und die
    Suite oben bliebe trotzdem grün, weil Seite 1 in Ordnung ist.
    """
    pdf = _rendere(FIXTURES / "ueberlauf-auf-seite-zwei.md", tmp_path / "seite2.pdf")
    bericht = geometrie.pruefe(pdf, "B")
    je_seite = [p for p in bericht.pruefungen
                if p.name.startswith("Seite 1, ") or p.name.startswith("Seite 2, ")]
    assert len(je_seite) == 6, [p.name for p in je_seite]


# ── die Zahl im README altert nicht mehr still ──────────────────────────────


def test_readme_nennt_die_zahl_die_wirklich_gemessen_wird(tmp_path):
    """Die Zahl im README wird gemessen, nicht gepflegt.

    Sie stand auf 30 und war schon vorher ungenau: Ein einseitiger Brief kam auf
    29 Geometrieprüfungen plus die PDF/A-Prüfung der CLI, ein mehrseitiger auf
    mehr. Solche Zahlen altern still, weil sie niemandem auffallen — genau die
    Fehlerart, die `evidence-strength.md` als Anlagerung beschreibt.

    Dieser Test bindet sie an einen echten Lauf. Wer eine Prüfung hinzufügt,
    sieht Rot und muss die Zahl mitziehen, statt sie zu vergessen.
    """
    import re

    pdf = _rendere(REPO / "examples" / "brief-form-b.md", tmp_path / "b.pdf")
    # +1 für die PDF/A-Prüfung, die die CLI anhängt und die nicht in geometrie
    # entsteht — die CLI meldet die Summe, und die steht im README.
    gemessen = len(geometrie.pruefe(pdf, "B").pruefungen) + 1

    readme = (REPO / "README.md").read_text(encoding="utf-8")
    treffer = re.findall(r"(\d+) Maße", readme)
    assert treffer, "im README steht keine Maßzahl mehr"
    for zahl in treffer:
        assert int(zahl) == gemessen, (
            f"README nennt {zahl} Maße, gemessen sind {gemessen} an "
            f"examples/brief-form-b.md. Eine der beiden Zahlen ist gealtert."
        )
