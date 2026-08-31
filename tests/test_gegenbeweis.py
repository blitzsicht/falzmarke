"""Gegenprobe: Ein Prüfmittel, das nie rot werden kann, ist kein Nachweis.

Jeder Test hier sabotiert das Layout an genau einer Stelle und verlangt, dass
die zugehörige Prüfung anschlägt — und nur sie. Ohne diese Datei wüsste die
Testsuite nur, dass sie grün ist, nicht dass sie misst.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

from falzmarke import geometrie
from falzmarke import cli as falzmarke
from falzmarke import lint as _lint
from falzmarke import regeln as _regeln
from conftest import REPO

BEISPIEL = REPO / "examples" / "brief-form-b.md"


def _sabotiere(tmp_path: Path, datei: str, alt: str, neu: str) -> Path:
    """Legt eine Kopie des typst-Verzeichnisses an und ändert dort eine Stelle."""
    ziel = tmp_path / "typst"
    shutil.copytree(REPO / "skill" / "falzmarke" / "typst", ziel)
    pfad = ziel / datei
    inhalt = pfad.read_text(encoding="utf-8")
    assert alt in inhalt, f"Ankertext nicht gefunden in {datei}: {alt!r}"
    pfad.write_text(inhalt.replace(alt, neu, 1), encoding="utf-8")
    return ziel


def _rendere_mit(tmp_path: Path, typst_dir: Path) -> tuple[Path, str]:
    original = falzmarke.TYPST_DIR
    falzmarke.TYPST_DIR = typst_dir
    try:
        return falzmarke.rendere(BEISPIEL, tmp_path / "sabotiert.pdf",
                                 profil_verzeichnis=typst_dir / "profiles")
    finally:
        falzmarke.TYPST_DIR = original


def _gescheitert(pdf: Path, form: str) -> set[str]:
    bericht = geometrie.pruefe(pdf, form)
    return {p.name for p in bericht.pruefungen if not p.bestanden}


def test_unveraendert_ist_gruen(tmp_path):
    """Kontrollprobe: ohne Sabotage darf nichts anschlagen. Sonst misst die
    Sabotage nur die Kopie, nicht die Verschiebung."""
    kopie = _sabotiere(tmp_path, "falzmarke.typ", "#let zeile = 4.2333mm",
                       "#let zeile = 4.2333mm  // unveraendert")
    pdf, form = _rendere_mit(tmp_path, kopie)
    assert _gescheitert(pdf, form) == set()


def test_verschobene_falzmarke_faellt_auf(tmp_path):
    kopie = _sabotiere(
        tmp_path, "vendor/letter-pro-v3.0.0.typ",
        "folding-mark-1-pos: 105mm", "folding-mark-1-pos: 112mm",
    )
    pdf, form = _rendere_mit(tmp_path, kopie)
    assert "Falzmarke 1, y" in _gescheitert(pdf, form)


def test_verschobene_lochmarke_faellt_auf(tmp_path):
    kopie = _sabotiere(
        tmp_path, "vendor/letter-pro-v3.0.0.typ", "dy: 148.5mm", "dy: 152mm",
    )
    pdf, form = _rendere_mit(tmp_path, kopie)
    assert "Lochmarke, y" in _gescheitert(pdf, form)


def test_zu_tiefer_betreff_faellt_auf(tmp_path):
    """Der teure Fehler: der Betreff rutscht in den Text."""
    kopie = _sabotiere(
        tmp_path, "falzmarke.typ", "let soll = unterkante + 2 * zeile",
        "let soll = unterkante + 3 * zeile",
    )
    pdf, form = _rendere_mit(tmp_path, kopie)
    assert "Betreff, y-Oberkante" in _gescheitert(pdf, form)


def test_verschobene_anschrift_faellt_auf(tmp_path):
    """Ein um 10 mm verschobenes Anschriftfeld ist im Fensterumschlag nicht
    mehr lesbar — das muss die Messung fangen."""
    kopie = _sabotiere(
        tmp_path, "vendor/letter-pro-v3.0.0.typ",
        "#let recipient-box(content) = {\n  set text(size: 10pt)\n  set align(top)\n  \n  pad(left: 5mm, content)",
        "#let recipient-box(content) = {\n  set text(size: 10pt)\n  set align(top)\n  \n  pad(left: 15mm, content)",
    )
    pdf, form = _rendere_mit(tmp_path, kopie)
    assert "Anschrift, x-links" in _gescheitert(pdf, form)


def test_zu_kleiner_unterrand_faellt_auf(tmp_path):
    """Die vierzeilige Fußzeile lief beim 20-mm-Standardrand aus dem Blatt."""
    kopie = _sabotiere(
        tmp_path, "falzmarke.typ",
        'profil.at("rand_unten_mm", default: 42)', "20",
    )
    original = falzmarke.baue_profil_daten

    def ohne_randberechnung(profil, pfad, arbeit):
        daten = original(profil, pfad, arbeit)
        daten.pop("rand_unten_mm", None)
        return daten

    falzmarke.baue_profil_daten = ohne_randberechnung
    try:
        pdf, form = _rendere_mit(tmp_path, kopie)
    finally:
        falzmarke.baue_profil_daten = original
    assert "Unterster Text, Abstand zur Blattkante" in _gescheitert(pdf, form)


# ── Dialekt 1.1: Ueberschriften ─────────────────────────────────────────────
#
# Das Ueberschriften-Layout haelt das 12-pt-Raster ein und bleibt im
# Satzspiegel. Beides waere ohne Gegenprobe nur eine Behauptung: Die
# Satzspiegelpruefung ist auch dann gruen, wenn sie den Briefkoerper gar nicht
# erreicht — und das Raster faellt bei einer Abweichung von einem Millimeter
# nicht auf, wenn niemand danach sieht.

SCHRIFTSATZ = REPO / "examples" / "brief-schriftsatz.md"

#: Die Zeile in falzmarke.typ, an der das Ueberschriften-Layout haengt.
HEADING_ANKER = '"1": (weight: "bold", style: "normal", davor: 2),'


def _rendere_schriftsatz(tmp_path: Path, typst_dir: Path) -> tuple[Path, str]:
    original = falzmarke.TYPST_DIR
    falzmarke.TYPST_DIR = typst_dir
    try:
        return falzmarke.rendere(SCHRIFTSATZ, tmp_path / "sabotiert.pdf",
                                 profil_verzeichnis=typst_dir / "profiles")
    finally:
        falzmarke.TYPST_DIR = original


def test_der_schriftsatz_ist_unsabotiert_gruen(tmp_path):
    """Kontrollprobe. Ohne sie misst die Sabotage unten nur die Kopie."""
    kopie = _sabotiere(tmp_path, "falzmarke.typ", HEADING_ANKER, HEADING_ANKER)
    pdf, form = _rendere_schriftsatz(tmp_path, kopie)
    assert _gescheitert(pdf, form) == set()


def test_ueberschrift_ausserhalb_des_satzspiegels_faellt_auf(tmp_path):
    """Eine Ueberschrift, die nach links aus dem Satzspiegel gezogen wird.

    Das ist der Fall, gegen den Issue #35 gebaut wurde, angewandt auf das neue
    Element: Der Vordruck sitzt weiter richtig, nur der Text steht falsch. Vor
    #35 waere dieser Brief gruen gewesen.
    """
    kopie = _sabotiere(
        tmp_path, "falzmarke.typ",
        "    block(\n      above: leer(stil.davor),",
        "    block(\n      inset: (left: -12mm),\n      above: leer(stil.davor),",
    )
    pdf, form = _rendere_schriftsatz(tmp_path, kopie)
    gescheitert = _gescheitert(pdf, form)
    assert any(n.endswith("linker Rand") or n == "Textblock, x-links"
               for n in gescheitert), gescheitert


# Hier stand eine dritte Gegenprobe: ein krummer Abstand ueber der Ueberschrift
# muesste das 12-pt-Raster verschieben und auffallen. Sie ist entfernt, weil sie
# **nicht anschlug** — und zwar nicht, weil die Sabotage wirkungslos gewesen
# waere: Das PDF aendert sich messbar (53.245 gegen 53.300 Byte bei
# `above: leer(n) + 2,6mm`). Die Geometriepruefung misst Raender, Zonen und den
# untersten Text, aber nicht, ob die Textzeilen auf dem Raster liegen.
#
# Ein Test, der das trotzdem behauptet haette, waere schlimmer als keiner. Die
# Luecke steht als Issue #140; die Rasterzusage in `falzmarke.typ` nennt sich
# seitdem eine Zusage und keine Messung.

def test_verschobener_infoblock_faellt_auf(tmp_path):
    kopie = _sabotiere(
        tmp_path, "vendor/letter-pro-v3.0.0.typ",
        "pad(top: 5mm, information-box)", "pad(top: 12mm, information-box)",
    )
    pdf, form = _rendere_mit(tmp_path, kopie)
    assert "Infoblock, y-Oberkante" in _gescheitert(pdf, form)


def test_bild_ohne_alternativtext_wird_von_pdfua_abgelehnt(tmp_path):
    """Ein Logo im Briefkopf ist für PDF/UA-1 nur zulässig, wenn es beschrieben
    ist. Ohne den alt-Text bricht Typst den Satz ab — genau das soll er.

    Anlass: Beim Aktivieren des Beispielprofils mit Logo scheiterte `--pdfua`
    mit 'missing alt text'. Ohne diesen Test wüsste die Suite nur, dass der
    alt-Text heute dasteht, nicht dass er gebraucht wird.
    """
    kopie = _sabotiere(
        tmp_path, "falzmarke.typ",
        'alt: k.at("logo_alt", default: profil.absender.name),', "",
    )
    original = falzmarke.TYPST_DIR
    falzmarke.TYPST_DIR = kopie
    try:
        with pytest.raises(falzmarke.Eingabefehler) as fehler:
            falzmarke.rendere(BEISPIEL, tmp_path / "ohne-alt.pdf",
                              profil_verzeichnis=kopie / "profiles", pdfua=True)
    finally:
        falzmarke.TYPST_DIR = original
    assert "alt text" in str(fehler.value).lower(), (
        f"Erwartet wurde eine PDF/UA-Beschwerde über den fehlenden alt-Text, "
        f"bekommen: {fehler.value}"
    )


# ── Die Grenze des HTML-Emitters (ADR 0034, Punkt 4) ────────────────────────
#
# Die Sabotagen hier setzen nicht am fertigen Text an, sondern am Emitter: Sie
# lassen ihn erzeugen, was er nicht erzeugen darf. Ein Detektor, der nur gegen
# handgeschriebene Beispielzeichenketten geprüft wird, belegt nicht, dass er
# eine echte Ausgabe des Werkzeugs beanstanden würde.

from falzmarke import emit_html as _html                       # noqa: E402
from falzmarke import markdown as _md                          # noqa: E402


def _seite_mit_sabotiertem_emitter(monkeypatch, name, ersatz) -> str:
    """Ersetzt eine Funktion des Emitters und lässt ihn einen Brief setzen."""
    quelle = BEISPIEL.read_text(encoding="utf-8").split("---", 2)[2]
    vorher = _html.dokument(_html.setze(_md.lies(quelle)))
    monkeypatch.setattr(_html, name, ersatz)
    nachher = _html.dokument(_html.setze(_md.lies(quelle)))
    assert nachher != vorher, (
        f"Die Sabotage an {name} hat die Ausgabe nicht verändert — "
        "ein grünes Ergebnis würde hier nichts belegen"
    )
    return nachher


def test_unsabotierter_emitter_ist_gruen():
    """Kontrollprobe. Ohne sie misst die Sabotage nur die Kopie."""
    quelle = BEISPIEL.read_text(encoding="utf-8").split("---", 2)[2]
    seite = _html.dokument(_html.setze(_md.lies(quelle)))
    assert _html.verstoesse(seite) == []


def test_externes_stylesheet_faellt_auf(monkeypatch):
    seite = _seite_mit_sabotiertem_emitter(
        monkeypatch, "absatz",
        lambda inhalt: '<link rel="stylesheet" href="https://example.invalid/m.css">'
                       f"<p>{inhalt}</p>",
    )
    assert "externes Stylesheet oder externe Ressource" in _html.verstoesse(seite)


def test_zaehlpixel_faellt_auf(monkeypatch):
    seite = _seite_mit_sabotiertem_emitter(
        monkeypatch, "absatz",
        lambda inhalt: f"<p>{inhalt}</p>"
                       '<img src="https://example.invalid/p.gif" alt="" width="1">',
    )
    verstoesse = _html.verstoesse(seite)
    assert any("Zählpixel" in v for v in verstoesse), verstoesse


def test_bild_ohne_alternativtext_faellt_auf(monkeypatch):
    seite = _seite_mit_sabotiertem_emitter(
        monkeypatch, "absatz",
        lambda inhalt: f'<p>{inhalt}</p><img src="cid:logo">',
    )
    assert "Bild ohne Alternativtext" in _html.verstoesse(seite)


def test_style_block_faellt_auf(monkeypatch):
    """Der naheliegendste Rückfall beim Erweitern: den Stil aus den Elementen
    in einen `<style>`-Block ziehen, weil das HTML kürzer wird. Gmail entfernt
    ihn, und die Mail käme unformatiert an.

    Seit dem dunklen Farbschema ist genau EIN Block zulässig — der des
    Werkzeugs, Zeichen für Zeichen verglichen (ADR 0034, Ergänzung vom
    28.08.2026). Jeder weitere fällt auf, und das ist hier der Gegenstand.
    """
    seite = _seite_mit_sabotiertem_emitter(
        monkeypatch, "absatz",
        lambda inhalt: f"<style>p {{ color: #000 }}</style><p>{inhalt}</p>",
    )
    befunde = _html.verstoesse(seite)
    assert any("Style-Block" in b or "Style-Blöcke" in b for b in befunde), befunde


# ── Dialekt 1.1: der wortgetreue Auszug ─────────────────────────────────────
#
# `tests/test_wortlaut.py` belegt, dass im PDF `#eval("6*7")` steht und nicht
# `42`. Für sich genommen belegt das wenig: Es könnte auch heissen, dass Typst
# solche Anweisungen ohnehin nie ausführt, oder dass die Zeile gar nicht erst
# ankommt. Erst dieser Test zeigt, dass die Grenze etwas VERHINDERT — mit einem
# Emitter, der Markup statt einer Zeichenkette erzeugt, erscheint `42` wirklich.

from falzmarke import emit as _emit                             # noqa: E402

AUSWERTBAR = '#eval("6*7")'
ERGEBNIS = "42"

AUSZUGSBRIEF = """---
profil: example
dialekt: "1.1"
empfaenger: [Muster GmbH, Musterstraße 1, 12345 Musterstadt]
datum: 2026-08-28
betreff: Auswertungsprobe
anrede: Sehr geehrte Damen und Herren,
---
der Auszug lautet:

```
%s
```
""" % AUSWERTBAR


def _pdf_text(tmp_path: Path, name: str) -> str:
    import pdfplumber

    brief = tmp_path / f"{name}.md"
    brief.write_text(AUSZUGSBRIEF, encoding="utf-8")
    pdf, _ = falzmarke.rendere(brief, tmp_path / f"{name}.pdf",
                               profil_verzeichnis=falzmarke.TYPST_DIR / "profiles")
    with pdfplumber.open(str(pdf)) as dokument:
        return dokument.pages[0].extract_text()


def test_der_echte_emitter_wertet_nicht_aus(tmp_path):
    """Kontrollprobe."""
    text = _pdf_text(tmp_path, "echt")
    assert AUSWERTBAR in text.replace("\n", ""), text[:300]
    assert ERGEBNIS not in text


def test_ein_emitter_ohne_zeichenkette_wertet_wirklich_aus(tmp_path, monkeypatch):
    """Die Gefahr ist real, nicht theoretisch.

    Ohne diesen Nachweis wäre `raw(zeichenkette(...))` eine Vorsichtsmassnahme
    gegen etwas, das vielleicht nie passiert wäre — und niemand wüsste, ob sie
    nötig ist, wenn jemand sie später „vereinfacht".
    """
    monkeypatch.setattr(_emit, "wortlaut",
                        lambda inhalt, block: f"#codeblock[{inhalt}]")
    text = _pdf_text(tmp_path, "sabotiert")
    assert ERGEBNIS in text, (
        "Der sabotierte Emitter hat NICHT ausgewertet — dann belegt die "
        "Kontrollprobe oben nicht, dass die Zeichenkette etwas verhindert.\n"
        + text[:300]
    )
    assert AUSWERTBAR not in text.replace("\n", "")


# ── Lint-Regeln: die Prüfung selbst sabotiert (Issue #197) ──────────────────
#
# Die Sabotagen oben brechen ein ERZEUGNIS (Typst-Vorlage, HTML-Emitter) und
# verlangen, dass eine zweite, unabhängige Messung es bemerkt. Für die
# Schreibregeln im Linter gibt es diese zweite Messung nicht — Eingabe und
# Prüfung laufen an derselben Stelle. `test_lint.py`s Positiv-/Negativtests
# zeigen deshalb nur, dass die UNVERÄNDERTE Prüfung bei präparierter Eingabe
# meldet; eine invertierte Bedingung oder ein verstellter Schwellwert bliebe
# grün, weil kein Test je gegen eine sabotierte Prüfung läuft.
#
# Sabotiert wird hier deshalb die Prüfung selbst — eine Konstante, an der die
# Regel hängt —, nicht ihr Ergebnis. Erste Staffel: die Regeln mit
# `wirkung: fehler`, die aus mehrfach belegten Quellen stammen (sie dürfen
# laut `deckel()` überhaupt Fehler sein und wiegen deshalb am schwersten).

LINT_KOPF = """profil: example
empfaenger: [Muster GmbH, Musterstraße 1, 12345 Musterstadt]
datum: 2026-08-25
betreff: Ein Betreff
anrede: Sehr geehrte Damen und Herren,
"""


def _linte(tmp_path: Path, kopf: str) -> _lint.Bericht:
    brief = tmp_path / "brief.md"
    brief.write_text(f"---\n{kopf}---\nText des Briefes.\n", encoding="utf-8")
    return falzmarke.linte(brief, profil_verzeichnis=falzmarke.TYPST_DIR / "profiles")


def _fehlerregeln(bericht: _lint.Bericht) -> set[str]:
    return {b.regel for b in bericht.befunde if b.schwere == _lint.FEHLER}


def _sabotiere_konstante(monkeypatch, name: str, alt, neu) -> None:
    """Ersetzt eine Konstante von `lint` für die Dauer des Tests.

    Derselbe Anker-Check wie bei `_sabotiere()` oben, nur für eine
    Python-Konstante statt für eine Typst-Datei: Ohne ihn würde ein
    inzwischen anders lautender Wert stillschweigend etwas anderes
    sabotieren, als der Test behauptet.
    """
    wert = getattr(_lint, name)
    assert wert == alt, f"Ankerwert veraltet: lint.{name} ist {wert!r}, erwartet {alt!r}"
    monkeypatch.setattr(_lint, name, neu)


def _sabotiere_regex(monkeypatch, name: str, alt: str, neu: str) -> None:
    """Wie `_sabotiere_konstante`, aber für ein kompiliertes Suchmuster.

    Zwei gleich kompilierte `re.Pattern` sind in Python nicht `==`
    (Objektidentität) — verglichen wird deshalb der Quelltext des Musters.
    """
    wert = getattr(_lint, name)
    assert wert.pattern == alt, f"Ankerwert veraltet: lint.{name} ist {wert.pattern!r}"
    monkeypatch.setattr(_lint, name, re.compile(neu))


#: Lint-Regeln, für die es unten eine Sabotage-Gegenprobe gibt. Wächst mit
#: jeder weiteren Staffel aus Issue #197 — `test_lint_gegenbeweis_deckung`
#: hält die Zahl gegen die Kandidatenmenge, damit die Abdeckung nicht still
#: veraltet.
LINT_REGELN_MIT_GEGENBEWEIS = {"vermerke", "datum"}


def test_lint_gegenbeweis_deckung():
    """Wie viele der Regeln, die überhaupt Fehler sein dürfen, eine Sabotage-
    Gegenprobe haben. Ohne diese Zählung altert die Lücke aus Issue #197
    still weiter, statt beim Wachsen der Regeldatei aufzufallen."""
    kandidaten = {
        r["lint"] for r in _regeln.alle()
        if r.get("lint") and r.get("wirkung") == "fehler"
        and r.get("herkunft") == _regeln.MEHRFACH
    }
    unbekannt = LINT_REGELN_MIT_GEGENBEWEIS - kandidaten
    assert not unbekannt, (
        f"Gegenprobe für Regel(n), die es als Kandidat so nicht (mehr) gibt: {unbekannt}")
    print(
        f"\nLint-Gegenbeweis-Abdeckung: {len(LINT_REGELN_MIT_GEGENBEWEIS)}/{len(kandidaten)} "
        "Regeln mit wirkung: fehler aus mehrfach belegten Quellen "
        f"(offen: {sorted(kandidaten - LINT_REGELN_MIT_GEGENBEWEIS)})."
    )


def test_lint_unsabotiert_ist_gruen(tmp_path):
    """Kontrollprobe: Die bekannt schlechte Eingabe wird OHNE Sabotage erkannt.

    Ohne sie würden die Sabotage-Tests unten nichts beweisen — ein Befund, der
    von Anfang an nie kam, kann durch die Sabotage nicht verschwinden.
    """
    bericht = _linte(tmp_path, LINT_KOPF + "vermerke: [Eins, Zwei, Drei, Vier]\n")
    assert "vermerke" in _fehlerregeln(bericht)
    bericht = _linte(tmp_path, LINT_KOPF.replace("datum: 2026-08-25", "datum: 20260825"))
    assert "datum" in _fehlerregeln(bericht)


def test_verstellter_vermerke_schwellwert_faellt_nicht_mehr_auf(tmp_path, monkeypatch):
    """Der Schwellwert IST die Regel `text.vermerke_max_3` — wird er
    verstellt, darf das nur diese eine Prüfung merken, sonst nichts."""
    _sabotiere_konstante(monkeypatch, "VERMERKE_MAX_ZEILEN", 3, 99)
    bericht = _linte(tmp_path, LINT_KOPF + "vermerke: [Eins, Zwei, Drei, Vier]\n")
    assert "vermerke" not in _fehlerregeln(bericht), (
        "Die Sabotage hat nicht gewirkt — vier Vermerke wären mit dem "
        "verstellten Schwellwert nicht mehr zu beanstanden"
    )
    assert bericht.ok, (
        "Die Sabotage hat mehr als die eine Regel getroffen:\n" + bericht.als_text("brief.md")
    )


def test_verstelltes_iso_datum_faellt_nicht_mehr_auf(tmp_path, monkeypatch):
    """`ISO_DATUM` erzwingt Bindestriche, obwohl `date.fromisoformat` seit
    Python 3.11 auch das Basisformat `20260825` annähme (Kommentar bei
    `pruefe_datum`, `lint.py:407`). Wird das Muster durchlässig, rutscht genau
    dieser eine Fall durch die Prüfung."""
    _sabotiere_regex(
        monkeypatch, "ISO_DATUM", r"^\d{4}-\d{2}-\d{2}$", r"^\d{4}-?\d{2}-?\d{2}$")
    bericht = _linte(tmp_path, LINT_KOPF.replace("datum: 2026-08-25", "datum: 20260825"))
    assert "datum" not in _fehlerregeln(bericht), (
        "Die Sabotage hat nicht gewirkt — 20260825 ohne Bindestriche wäre mit "
        "dem durchlässigen Muster nicht mehr zu beanstanden"
    )
    assert bericht.ok, (
        "Die Sabotage hat mehr als die eine Lücke getroffen:\n" + bericht.als_text("brief.md")
    )

    # Ein Datum, das auch `date.fromisoformat` ablehnt, bleibt erkannt — die
    # Sabotage trifft nur die eine Lücke, nicht die ganze Prüfung.
    bericht = _linte(tmp_path, LINT_KOPF.replace("datum: 2026-08-25", "datum: morgen"))
    assert "datum" in _fehlerregeln(bericht)
