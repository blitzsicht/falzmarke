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
    """Bis #243 fiel dieser Fall als „Bild von aussen" auf — die Quellenregel
    war der erste Zaun, die 1×1-Messung der zweite dahinter. Seit `email.logo`
    fremde Adressen annimmt, ist der erste weg, und diese Probe misst wirklich
    die Messung am Empfaenger."""
    seite = _seite_mit_sabotiertem_emitter(
        monkeypatch, "absatz",
        lambda inhalt: f"<p>{inhalt}</p>"
                       '<img src="https://example.invalid/p.gif" alt="" width="1">',
    )
    verstoesse = _html.verstoesse(seite)
    assert any("Zählpixel" in v for v in verstoesse), verstoesse


def test_ein_zweites_bild_faellt_auf(monkeypatch):
    """Die Grenze, die seit #243 haelt, was die Quellenregel nebenbei mittrug.
    Ohne sie waeren drei Bilder mit `cid:` anstandslos durchgegangen — gemessen
    hat das vorher niemand."""
    seite = _seite_mit_sabotiertem_emitter(
        monkeypatch, "absatz",
        lambda inhalt: f"<p>{inhalt}</p>"
                       '<img src="cid:a" alt="a" width="8" height="8">',
    )
    verstoesse = _html.verstoesse(seite)
    assert any("Bilder" in v for v in verstoesse), verstoesse


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


# ── Die Signatur-Fixture: sabotierte Quellzeile, nicht sabotiertes Ergebnis ──
#
# #221 verlangt: „Eine verfälschte Zeile in `signatur_bloecke()` macht mindestens
# einen Eintrag rot — eine Fixture, die jede Fassung durchwinkt, wäre keine."
#
# Verfälscht wird deshalb die **Quellzeile**, nicht das Ergebnis. Ein Wrapper um
# die echte Funktion, der hinterher etwas anhängt, belegte nur, dass `!=`
# funktioniert: Er beweist nichts über die Zweige, und genau die sind der Grund
# für die Fixture.

FIXTURE_SIGNATUR = REPO / "tests" / "golden" / "email" / "signatur-faelle.json"


def _eml_mit_geaenderter_zeile(tmp_path: Path, alt: str, neu: str):
    """`eml.py` als eigenes Modul, mit genau einer geänderten Zeile."""
    import importlib.util

    quelle = REPO / "skill" / "falzmarke" / "eml.py"
    inhalt = quelle.read_text(encoding="utf-8")
    assert inhalt.count(alt) == 1, (
        f"Anker {alt!r} steht {inhalt.count(alt)}× in eml.py — eine Sabotage, "
        "die mehrere Stellen trifft, sagt nicht, welche gemessen wurde")
    kopie = tmp_path / "eml_sabotiert.py"
    kopie.write_text(inhalt.replace(alt, neu, 1), encoding="utf-8")

    spezifikation = importlib.util.spec_from_file_location("eml_sabotiert", kopie)
    modul = importlib.util.module_from_spec(spezifikation)
    spezifikation.loader.exec_module(modul)
    return modul


def _abweichende_faelle(bloecke) -> list[str]:
    """Welche Einträge der Fixture passen nicht zu dieser Rechnung?"""
    import json

    eintraege = json.loads(FIXTURE_SIGNATUR.read_text(encoding="utf-8"))
    assert eintraege, "die Fixture ist leer — dann belegt hier nichts etwas"
    return [e["name"] for e in eintraege
            if bloecke(e["profil"], e["kopf"]) != e["bloecke"]]


def test_unsabotierte_signatur_passt_zur_fixture():
    """Die Kontrollprobe. Ohne sie misst jede Sabotage unten nur die Kopie."""
    from falzmarke import eml as _eml

    assert _abweichende_faelle(_eml.signatur_bloecke) == []


#: Je Sabotage eine Zeile aus `signatur_bloecke()` und die Fälle, die sie
#: treffen MUSS. Die Erwartung ist absichtlich namentlich und nicht „mindestens
#: einer": Eine Sabotage, die plötzlich andere Fälle trifft, hat einen anderen
#: Zweig erwischt als gedacht, und das soll auffallen.
SIGNATUR_SABOTAGEN = [
    # Die trennschärfste der drei: Der Rückgriff auf den **Kopf** entfällt, und
    # es fallen genau zwei Fälle aus. `karg` ist dabei, weil sein Profil keinen
    # eigenen `unterzeichner` trägt — ohne die Kopf-Stufe bleibt der Name leer
    # und der Person-Block verschwindet ganz. Die Menge war beim Schreiben auf
    # `{"ohne-anzeigename"}` geraten; gemessen sind es zwei.
    ('name = email_teil.get("anzeigename") or kopf.get("unterzeichner") '
     'or profil.get("unterzeichner")',
     'name = email_teil.get("anzeigename") or profil.get("unterzeichner")',
     {"ohne-anzeigename", "karg"}),
    # Das Leitwort vor der Telefonnummer — jeder Fall mit Telefon, also alle
    # außer `karg`. Belegt, dass die Fixture auch die Schreibweise hält, nicht
    # nur die Auswahl der Zeilen.
    ('kontakt.append(f"Telefon {telefon}")',
     'kontakt.append(f"Tel. {telefon}")',
     {"fusszeile", "pflichtangaben-liste", "doppelte-zeile-in-zwei-bloecken",
      "ohne-pflichtangaben", "telefon-eigen", "ohne-anzeigename",
      "name-aus-dem-profil"}),
    # Die Weiche zwischen Fußzeile und `absender:`, umgedreht. Sie trifft ALLE
    # acht Fälle: Der Basisfall bekommt den Block, den er überspringen müsste,
    # jeder andere verliert ihn. Damit belegt sie, DASS die Fixture misst — aber
    # nicht, welchen Zweig. Diesen Unterschied leisten die beiden Proben oben
    # und die Entdoppelung darunter, und deshalb stehen sie daneben und nicht
    # statt ihr.
    ('if pflicht != "fusszeile":',
     'if pflicht == "fusszeile":',
     {"fusszeile", "pflichtangaben-liste", "doppelte-zeile-in-zwei-bloecken",
      "ohne-pflichtangaben", "telefon-eigen", "ohne-anzeigename",
      "name-aus-dem-profil", "karg"}),
]


@pytest.mark.parametrize("alt, neu, erwartet", SIGNATUR_SABOTAGEN,
                         ids=["name-rueckgriff", "telefon-leitwort", "fusszeilen-weiche"])
def test_eine_verfaelschte_zeile_faellt_an_der_fixture_auf(tmp_path, alt, neu, erwartet):
    modul = _eml_mit_geaenderter_zeile(tmp_path, alt, neu)
    abweichend = set(_abweichende_faelle(modul.signatur_bloecke))
    assert abweichend, (
        "Die Sabotage hat keinen Eintrag rot gemacht — dann winkt die Fixture "
        "diese Fassung durch und belegt für diesen Zweig nichts")
    assert abweichend == erwartet, (
        f"andere Fälle als erwartet: {sorted(abweichend)} statt {sorted(erwartet)}")


def test_die_entdoppelung_haengt_an_ihrem_eigenen_fall(tmp_path):
    """Block-lokal statt über alle Blöcke — die Sabotage, für die es den Fall
    `doppelte-zeile-in-zwei-bloecken` überhaupt gibt.

    Sie steht einzeln, weil `gesehen` an zwei Stellen vorkommt und der Anker
    deshalb der Schleifenkopf ist, nicht die Zuweisung.
    """
    modul = _eml_mit_geaenderter_zeile(
        tmp_path,
        "    for block in (person, kontakt, recht):\n        einmalig = []",
        "    for block in (person, kontakt, recht):\n        gesehen = set()\n"
        "        einmalig = []")
    abweichend = set(_abweichende_faelle(modul.signatur_bloecke))
    assert abweichend == {"doppelte-zeile-in-zwei-bloecken"}, sorted(abweichend)


# ── Die Warnstufe des Berichts (#292) ───────────────────────────────────────
#
# Bis #292 kannte `geometrie.Bericht` nur wahr und falsch, und jede Prüfung der
# fertigen `.eml` wirkte als Fehler. Die Stufe kommt jetzt aus dem Regelkatalog.
#
# Gemessen werden hier BEIDE Richtungen. Eine allein belegt nichts: Dass ein
# Lauf grün ist, kann daran liegen, dass die Herabstufung greift — oder daran,
# dass die Prüfung gar nicht angeschlagen hat.

from falzmarke import pruefung_eml as _eml_pruefung                   # noqa: E402
from falzmarke import regeln as _regeln                              # noqa: E402


def _eml_ohne_sprache(tmp_path: Path) -> Path:
    """Eine echte Nachricht, der das `lang`-Attribut fehlt.

    Über den echten Erzeuger und dann sabotiert — nicht von Hand gebaut: Eine
    selbst geschriebene `.eml` bestünde die übrigen 24 Prüfungen nicht, und dann
    wäre nicht zu sehen, welche den Exit-Code bestimmt.
    """
    import yaml

    from falzmarke import eml as _eml
    from falzmarke import markdown as _markdown

    quelle = "wie besprochen erhalten Sie das Angebot.\n"
    profil = yaml.safe_load(
        (REPO / "skill" / "falzmarke" / "typst" / "profiles" / "example.yaml")
        .read_text(encoding="utf-8"))
    kopf = {"an": "a@example.de", "betreff": "Probe", "anrede": "Hallo,",
            "unterzeichner": "Erika Muster"}
    roh = _eml.baue(kopf, profil, quelle, _markdown.lies(quelle)).as_string()

    kaputt = roh.replace('<html lang=3D"de">', "<html>", 1)
    assert kaputt != roh, (
        "Die Sabotage hat nichts verändert — dann belegt dieser Test nichts")
    pfad = tmp_path / "ohne-sprache.eml"
    pfad.write_text(kaputt, encoding="utf-8", newline="")
    return pfad


def test_eine_fehlerregel_macht_den_bericht_rot(tmp_path):
    """Die Kontrollprobe, und der heutige Stand: `eml.sprache` ist `werkzeug`."""
    assert _regeln.deckel_von_pruefung("sprache") == _regeln.DECKEL_FEHLER, \
        "der Ausgangszustand ist nicht mehr `fehler` — dann misst dieser Test etwas anderes"
    bericht = _eml_pruefung.pruefe(_eml_ohne_sprache(tmp_path))
    assert not bericht.ok
    assert not bericht.warnungen, "ein Fehler darf nicht als Warnung erscheinen"


def test_dieselbe_regel_als_warnung_laesst_den_bericht_gruen(tmp_path, monkeypatch):
    """Die Gegenrichtung, und der eigentliche Gegenstand von #292.

    Derselbe Befund, dieselbe Datei — nur die Stufe aus dem Katalog ist eine
    andere. Dass er SICHTBAR bleibt, wird mitgeprüft: Eine Warnung, die im
    knappen Bericht fehlt, ist im grünen Lauf keine.
    """
    monkeypatch.setattr(_regeln, "deckel_von_pruefung",
                        lambda name: (_regeln.DECKEL_WARNUNG if name == "sprache"
                                      else _regeln.DECKEL_FEHLER))
    bericht = _eml_pruefung.pruefe(_eml_ohne_sprache(tmp_path))
    assert bericht.ok, bericht.als_text()
    assert len(bericht.warnungen) == 1, bericht.als_text()

    knapp = bericht.als_text()
    assert "WARN" in knapp and "Sprache ausgezeichnet" in knapp, knapp
    assert "1 Warnung" in knapp, knapp


# ── Der Knopf als Anker in einer mitgebrachten Signatur (#322) ──────────────
#
# Zwei Proben, nicht eine. Dass die Prüfung bei `<a style="display:inline-block;
# padding:6px">` rot wird, sagt allein nur, dass sie manchmal anschlägt — nicht,
# dass sie unterscheidet. Ein Prüfer, der jede Signatur mit Knopf beanstandet,
# besteht die erste Probe ebenso. Erst die zweite, dieselbe Signatur im
# Tabellengerüst, zeigt, dass es am Aufbau liegt und nicht am Knopf.
#
# Beide Signaturen tragen außerdem den Google-Knopf aus `blitzsicht.html`, der
# in Outlook seine Form hält (`signatur_knopf.TABELLENKNOPF_BEWERTEN`): Was der
# Prüfer an ihm findet, wäre der Fehlalarm — er steht in der grünen Probe mit
# darin und bleibt dort ohne Befund.

from signatur_knopf import eml_mit_signatur, html_der_eml, signatur    # noqa: E402

#: Der Anker aus der Aufgabe, wörtlich — ohne `href`. Ein Anker ohne Ziel bleibt
#: ein Anker: Auch der zerfällt in Outlook, und eine Prüfung, die nur Anker MIT
#: `href` findet, ließe genau den Fall der Aufgabe durch.
ANKER_WOERTLICH = '<a style="display:inline-block;padding:6px">Termin vereinbaren</a>'

#: Dasselbe Aussehen in dem Gerüst, das dort nachweislich hält.
TABELLE_WOERTLICH = (
    '<table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>'
    '<td style="padding:6px"><a>Termin vereinbaren</a></td></tr></table>')


def _rot(tmp_path: Path, knopf: str) -> set[str]:
    """Die Namen der Prüfungen, die an einer Nachricht mit diesem Knopf anschlagen.

    Es wird kein Regelname vorausgesetzt: Gemessen wird, ob IRGENDEINE Prüfung
    anschlägt, und die Kontrolle unten sagt, dass es dieselbe eine ist.
    """
    pfad = eml_mit_signatur(tmp_path, signatur(knopf))
    return {p.name for p in _eml_pruefung.pruefe(pfad).pruefungen if not p.bestanden}


def test_der_anker_als_knopf_macht_die_pruefung_rot(tmp_path):
    """Erste Probe. Die Sabotage muss in der fertigen Datei stehen — sonst ist
    ein rotes Ergebnis hier ein anderer Fehler und kein Beleg."""
    pfad = eml_mit_signatur(tmp_path, signatur(ANKER_WOERTLICH))
    assert "display:inline-block" in html_der_eml(pfad), \
        "der Anker steht nicht in der Datei — die Probe misst nichts"
    bericht = _eml_pruefung.pruefe(pfad)
    rot = [p for p in bericht.pruefungen if not p.bestanden]
    assert len(rot) == 1, bericht.als_text(ausfuehrlich=True)


def test_dasselbe_geruest_als_tabelle_laesst_die_pruefung_gruen(tmp_path):
    """Zweite Probe, und sie trägt den Nachweis (AC 4): Ohne sie wäre offen, ob
    die Prüfung nur immer rot meldet.

    Mit der Vorbedingung vorweg: Ein Grün ist nur dann eines, wenn es dieselbe
    Prüfung ist, die eben noch rot wurde. Ohne sie bestünde diese Probe auch
    dort, wo es die Prüfung gar nicht gibt.
    """
    (tmp_path / "schlecht").mkdir()
    assert len(_rot(tmp_path / "schlecht", ANKER_WOERTLICH)) == 1, \
        "die Vorbedingung fehlt: die Prüfung wird an der ersten Probe nicht rot"

    pfad = eml_mit_signatur(tmp_path, signatur(TABELLE_WOERTLICH))
    html = html_der_eml(pfad)
    assert "inline-block" not in html, "der Anker ist noch da — die Probe misst nichts"
    assert "Termin vereinbaren" in html and "<td" in html
    bericht = _eml_pruefung.pruefe(pfad)
    assert not [p for p in bericht.pruefungen if not p.bestanden], \
        bericht.als_text(ausfuehrlich=True)
    assert not bericht.warnungen, bericht.als_text()


def test_beide_proben_unterscheiden_sich_nur_im_knopf(tmp_path):
    """Die Kontrolle über beiden: Was zwischen den Läufen anders ist, ist genau
    die eine Prüfung — dieselbe Zahl an Prüfungen, dieselben Namen, ein
    Unterschied. Sonst hätte die zweite Probe einen anderen Grund für ihr Grün
    als die erste für ihr Rot."""
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    schlecht = eml_mit_signatur(tmp_path / "a", signatur(ANKER_WOERTLICH))
    gut = eml_mit_signatur(tmp_path / "b", signatur(TABELLE_WOERTLICH))
    namen_schlecht = [p.name for p in _eml_pruefung.pruefe(schlecht).pruefungen]
    namen_gut = [p.name for p in _eml_pruefung.pruefe(gut).pruefungen]
    assert namen_schlecht == namen_gut, "die Läufe prüfen nicht dasselbe"
    assert len(_rot(tmp_path / "a", ANKER_WOERTLICH)) == 1
    assert _rot(tmp_path / "b", TABELLE_WOERTLICH) == set()


def test_die_briefmasse_bleiben_fehler(tmp_path):
    """Der Default trägt: Die Maße des Briefes kennen den Katalog nicht.

    Ohne diesen Test hätte die Änderung den PDF-Pfad stillschweigend aufweichen
    können — dieselbe Berichtsklasse misst beides.
    """
    # Derselbe Anker wie in `test_verschobene_falzmarke_faellt_auf` — ein
    # eigener waere eine zweite Fassung derselben Sabotage.
    typst = _sabotiere(tmp_path, "vendor/letter-pro-v3.0.0.typ",
                       "folding-mark-1-pos: 105mm", "folding-mark-1-pos: 112mm")
    pdf, form = _rendere_mit(tmp_path, typst)
    bericht = geometrie.pruefe(pdf, form)
    assert not bericht.ok, "ein verschobenes Maß muss ein Fehler bleiben"
    assert not bericht.warnungen, "kein Briefmaß darf zur Warnung geworden sein"
    assert all(p.stufe == geometrie.STUFE_FEHLER for p in bericht.pruefungen)


# ── Der Abschnitt `rechnung:` im Profil (#116) ──────────────────────────────
#
# `tests/test_rechnung_profil.py` hält beide Richtungen fest: was melden muss
# und was schweigen muss. Was dort fehlt, ist die Frage, die nur hier gestellt
# wird — kann die Feldliste überhaupt rot werden? Ohne diese Probe wüsste man
# von ihr nur, dass sie durchlässt, was sie kennt.

def _rechnungsprofil(rechnung: dict) -> dict:
    import copy

    import yaml

    from conftest import PROFILE

    profil = copy.deepcopy(
        yaml.safe_load((PROFILE / "example.yaml").read_text(encoding="utf-8")))
    profil["rechnung"] = rechnung
    return profil


def _profilregeln(profil: dict) -> set:
    bericht = _lint.Bericht()
    _lint.pruefe_rechnung_profil(profil, bericht)
    return {befund.regel for befund in bericht.befunde}


def test_der_tippfehler_im_profilfeld_faellt_unsabotiert_auf():
    """Kontrollprobe. Ohne sie belegte die Sabotage unten nichts: Ein Befund,
    der nie kam, kann durch keine Sabotage verschwinden."""
    regeln = _profilregeln(_rechnungsprofil({"ust_idnrr": "DE123456789", "land": "DE"}))
    assert "rechnung.aussteller" in regeln


def test_eine_aufgeweichte_feldliste_meldet_den_tippfehler_nicht_mehr(monkeypatch):
    """Sabotage an genau einer Stelle: Steht der Tippfehler in der Feldliste,
    gilt er als bekanntes Feld und bleibt stumm.

    Die Prüfung auf die fehlende Steuerangabe bleibt davon unberührt — sie
    misst etwas anderes, und genau das soll die Probe zeigen: Die Sabotage
    trifft die Feldliste und nicht pauschal die ganze Funktion.
    """
    monkeypatch.setattr(
        _lint, "PROFIL_RECHNUNG_FELDER",
        frozenset({"ust_idnr", "ust_idnrr", "steuernummer", "land"}))
    regeln = _profilregeln(_rechnungsprofil({"ust_idnrr": "DE123456789", "land": "DE"}))
    assert "rechnung.aussteller" not in regeln, \
        "die Feldliste ist nicht die Stelle, an der der Tippfehler auffällt"
    assert "rechnung.steuernummer" in regeln, \
        "die Sabotage hat mehr getroffen als die Feldliste"


# ── Die E-Rechnung: kommen Name und Schema wirklich von uns? (#116) ─────────
#
# Beide Größen sehen im fertigen PDF richtig aus. Diese Proben zeigen, dass sie
# nicht zufällig richtig sind: Wird die Quelle verstellt, ändert sich das
# Ergebnis. Ohne sie wüsste man nicht, ob Typst das Factur-X-Schema nicht
# ohnehin selbst schreibt — gemessen hat es das am 12.09.2026 NICHT.

RECHNUNG_QUELLE = REPO / "examples" / "rechnung.md"


def _rechnung_anhaenge(pdf):
    import pypdf

    wurzel = pypdf.PdfReader(str(pdf)).trailer["/Root"]
    return [str(e.get_object().get("/F")) for e in wurzel.get("/AF", [])]


def test_die_unsabotierte_rechnung_traegt_factur_x(tmp_path):
    """Kontrollprobe. Ohne sie belegten die beiden Sabotagen nichts."""
    from falzmarke import geometrie

    pdf, _ = falzmarke.rendere(RECHNUNG_QUELLE, tmp_path / "gut.pdf",
                               profil_verzeichnis=REPO / "skill" / "falzmarke"
                               / "typst" / "profiles")
    assert _rechnung_anhaenge(pdf) == ["factur-x.xml"]
    assert "urn:factur-x" in geometrie.xmp_lesen(pdf)


def test_ein_verstellter_dateiname_landet_wirklich_im_pdf(tmp_path, monkeypatch):
    """Der Name kommt aus `RECHNUNG_XML_NAME` und nicht daher, dass Typst ihn
    zufällig so vergibt — sonst wäre die Konstante wirkungslos und niemand
    merkte es, solange sie richtig steht."""
    monkeypatch.setattr(falzmarke, "RECHNUNG_XML_NAME", "verstellt.xml")
    pdf, _ = falzmarke.rendere(RECHNUNG_QUELLE, tmp_path / "sabotiert.pdf",
                               profil_verzeichnis=REPO / "skill" / "falzmarke"
                               / "typst" / "profiles")
    assert _rechnung_anhaenge(pdf) == ["verstellt.xml"], \
        "der Dateiname stammt nicht aus RECHNUNG_XML_NAME"


def test_ohne_den_nachlauf_fehlt_das_factur_x_schema(tmp_path, monkeypatch):
    """Die wichtigste der drei: Sie belegt, dass das Erweiterungsschema von
    `_fx_schema_ergaenzen` kommt. Schriebe Typst es ohnehin, bliebe das XMP hier
    vollständig — und die ganze Funktion wäre eine Zeile Aufwand ohne Wirkung."""
    from falzmarke import geometrie

    monkeypatch.setattr(falzmarke, "_fx_schema_ergaenzen", lambda pdf: None)
    pdf, _ = falzmarke.rendere(RECHNUNG_QUELLE, tmp_path / "ohne-schema.pdf",
                               profil_verzeichnis=REPO / "skill" / "falzmarke"
                               / "typst" / "profiles")
    xmp = geometrie.xmp_lesen(pdf)
    assert "urn:factur-x" not in xmp, \
        "Typst schreibt das Schema offenbar selbst — dann ist der Nachlauf überflüssig"
    # Die Beilage selbst ist trotzdem da: Nur das Schema fehlt, und genau das
    # macht den Unterschied zwischen „Datei im PDF" und „erkennbare Rechnung".
    assert _rechnung_anhaenge(pdf) == ["factur-x.xml"]


# ── Die Fassungszeile im Messbericht liest die Datei (#117) ─────────────────
#
# Bis #117 gab die Zeile „E-Rechnung" Profil und Fassung aus Konstanten aus und
# prüfte nur, ob irgendein Factur-X-Schema im XMP stand. Eine Rechnung mit
# falscher Guideline-ID hätte dieselbe grüne Zeile bekommen. Jetzt liest sie
# die eingebettete XML und das XMP — und vergleicht mit einer eigenen Tabelle,
# nicht mit der Konstante des Emitters (sonst prüfte der Sollwert sich selbst).

def _rechnung_gerendert(tmp_path, name):
    pdf, _ = falzmarke.rendere(RECHNUNG_QUELLE, tmp_path / name,
                               profil_verzeichnis=REPO / "skill" / "falzmarke"
                               / "typst" / "profiles")
    return pdf


def test_die_fassungszeile_liest_die_eingebettete_rechnung(tmp_path):
    """Kontrollprobe."""
    from falzmarke import emit_xml

    gelesen = falzmarke.rechnung_im_pdf(_rechnung_gerendert(tmp_path, "gut.pdf"))
    assert gelesen["guideline"] == emit_xml.GUIDELINE
    assert gelesen["datei"] == "factur-x.xml"
    ok, text = falzmarke.rechnung_befund(gelesen)
    assert ok, text
    assert "EN 16931" in text
    assert gelesen["fassung"] == "1.0" and "Factur-X 1.0" in text


def test_eine_falsche_guideline_macht_die_fassungszeile_rot(tmp_path, monkeypatch):
    from falzmarke import emit_xml

    monkeypatch.setattr(emit_xml, "GUIDELINE", "urn:sabotiert:0")
    pdf = _rechnung_gerendert(tmp_path, "sabotiert.pdf")
    gelesen = falzmarke.rechnung_im_pdf(pdf)
    assert gelesen["guideline"] == "urn:sabotiert:0", "die Sabotage griff nicht"
    ok, text = falzmarke.rechnung_befund(gelesen)
    assert not ok, text


def test_ein_falsches_profil_im_xmp_macht_die_fassungszeile_rot(tmp_path, monkeypatch):
    monkeypatch.setitem(falzmarke.FX_WERTE, "ConformanceLevel", "BASIC")
    gelesen = falzmarke.rechnung_im_pdf(_rechnung_gerendert(tmp_path, "basic.pdf"))
    assert gelesen["profil"] == "BASIC", "die Sabotage griff nicht"
    ok, _ = falzmarke.rechnung_befund(gelesen)
    assert not ok


XRECHNUNG_QUELLE = REPO / "examples" / "xrechnung.md"


def test_die_xrechnung_im_pdf_traegt_ihr_eigenes_profil(tmp_path):
    """Kontrollprobe (#117): Guideline XRechnung 3.0 und `XRECHNUNG` im XMP."""
    pdf, _ = falzmarke.rendere(XRECHNUNG_QUELLE, tmp_path / "xr.pdf",
                               profil_verzeichnis=REPO / "skill" / "falzmarke"
                               / "typst" / "profiles")
    gelesen = falzmarke.rechnung_im_pdf(pdf)
    assert gelesen["profil"] == "XRECHNUNG"
    ok, text = falzmarke.rechnung_befund(gelesen)
    assert ok, text


def test_ohne_die_xrechnung_stufe_im_xmp_wird_die_zeile_rot(tmp_path, monkeypatch):
    """Die Stufe kommt aus dem Aufruf mit `"XRECHNUNG"` — nicht zufällig aus dem
    XMP. Wird sie verschluckt, passen Guideline und Profil nicht mehr zusammen."""
    echt = falzmarke._fx_schema_ergaenzen
    monkeypatch.setattr(falzmarke, "_fx_schema_ergaenzen", lambda pdf, stufe=None: echt(pdf))
    pdf, _ = falzmarke.rendere(XRECHNUNG_QUELLE, tmp_path / "xr-sabotiert.pdf",
                               profil_verzeichnis=REPO / "skill" / "falzmarke"
                               / "typst" / "profiles")
    gelesen = falzmarke.rechnung_im_pdf(pdf)
    assert gelesen["profil"] == "EN 16931", "die Sabotage griff nicht"
    ok, _ = falzmarke.rechnung_befund(gelesen)
    assert not ok


# ── Keine stille Rundung: kommt die Stellenzahl wirklich aus BETRAG_STELLEN? ─
#
# Eine Quelle für beide Seiten: Emitter und `lint` lesen dieselbe Konstante. Die
# Sabotage verstellt sie und verlangt, dass BEIDE denselben Betrag durchlassen —
# liefe `lint` auf einer eigenen Zahl, bliebe sein Befund stehen.

LINT_ROH = "positionen:\n"


def _stellenbefund(betrag) -> set:
    kopf = {"rechnungsnummer": "1", "positionen": [
        {"bezeichnung": "A", "menge": 1, "steuersatz": 19, "betrag": betrag}]}
    bericht = _lint.Bericht()
    _lint.pruefe_rechnungsfelder(kopf, LINT_ROH, bericht)
    return {b.regel for b in bericht.befunde}


def test_drei_nachkommastellen_fallen_unsabotiert_auf():
    """Kontrollprobe: ohne sie belegte die Sabotage nichts."""
    from falzmarke import emit_xml

    with pytest.raises(emit_xml.RechnungUnvollstaendig):
        emit_xml._betrag(1240.005, "betrag")
    assert "rechnung.betrag_stellen" in _stellenbefund(1240.005)


def test_mit_verstellter_stellenzahl_geht_derselbe_betrag_durch(monkeypatch):
    from falzmarke import emit_xml

    monkeypatch.setattr(emit_xml, "BETRAG_STELLEN", 3)
    emit_xml._betrag(1240.005, "betrag")           # darf jetzt nicht mehr werfen
    assert "rechnung.betrag_stellen" not in _stellenbefund(1240.005), \
        "lint prüft gegen eine eigene Stellenzahl, nicht gegen die des Emitters"


# ── Rechnung: Steuersatz ohne Summenzeile und Ländercode (#119) ─────────────
#
# Beide Regeln sind neu. Die Sabotage verändert je genau eine Stelle eines
# echten Beispiels; die Kontrollprobe davor zeigt, dass dasselbe Beispiel
# unverändert frei von genau diesem Befund ist.

RECHNUNG_PROFILE = REPO / "skill" / "falzmarke" / "typst" / "profiles"
STEUERSAETZE_QUELLE = REPO / "examples" / "rechnung-steuersaetze.md"
SIEBEN_PROZENT_ZEILE = "    - satz: 7\n      basis: 100.00\n      betrag: 7.00\n"


def _rechnungsregeln(tmp_path: Path, quelle: Path, alt: str | None = None,
                     neu: str = "") -> set[str]:
    text = quelle.read_text(encoding="utf-8")
    if alt is not None:
        assert text.count(alt) == 1, f"Anker „{alt.strip()}“ nicht genau einmal in {quelle.name}"
        text = text.replace(alt, neu)
    pfad = tmp_path / quelle.name
    pfad.write_text(text, encoding="utf-8")
    return _fehlerregeln(falzmarke.linte(pfad, profil_verzeichnis=RECHNUNG_PROFILE))


def test_zwei_steuersaetze_mit_je_einer_summenzeile_sind_kein_befund(tmp_path):
    assert "rechnung.steuersatz" not in _rechnungsregeln(tmp_path, STEUERSAETZE_QUELLE)


def test_eine_fehlende_summenzeile_faellt_auf(tmp_path):
    regeln = _rechnungsregeln(tmp_path, STEUERSAETZE_QUELLE, SIEBEN_PROZENT_ZEILE)
    assert "rechnung.steuersatz" in regeln, regeln


def test_ein_amtlicher_laendercode_ist_kein_befund(tmp_path):
    assert "rechnung.land" not in _rechnungsregeln(tmp_path, RECHNUNG_QUELLE)


def test_ein_ausgeschriebenes_land_faellt_auf(tmp_path):
    regeln = _rechnungsregeln(tmp_path, RECHNUNG_QUELLE, "  land: DE\n", "  land: Deutschland\n")
    assert "rechnung.land" in regeln, regeln


def test_lint_prueft_gegen_die_liste_des_emitters(tmp_path, monkeypatch):
    """Nimmt die Liste des Emitters „DEUTSCHLAND“ auf, muss lint schweigen —
    sonst prüft lint gegen eine eigene Liste, und beide könnten auseinanderlaufen."""
    from falzmarke import emit_xml

    monkeypatch.setattr(emit_xml, "LAENDERCODES", emit_xml.LAENDERCODES | {"DEUTSCHLAND"})
    regeln = _rechnungsregeln(tmp_path, RECHNUNG_QUELLE, "  land: DE\n", "  land: Deutschland\n")
    assert "rechnung.land" not in regeln, "lint prüft nicht gegen emit_xml.LAENDERCODES"


# ── Rechnung eines Kleinunternehmers (#317, ADR 0041) ───────────────────────
#
# Je Regel: das Beispiel ist frei davon, und genau eine Änderung an Quelle oder
# Profil lässt genau diese Regel anschlagen. Quelle und Profil liegen als Kopie
# nebeneinander, das Profil in `profiles/` neben dem Schreiben.

KU_QUELLE = REPO / "examples" / "rechnung-kleinunternehmer.md"
KU_PROFIL = REPO / "examples" / "profiles" / "example-kleinunternehmer.yaml"
KU_HINWEIS = "Steuerfreie Kleinunternehmerleistung nach § 19 UStG."


def _ku_regeln(tmp_path: Path, quelle_alt: str | None = None, quelle_neu: str = "",
               profil_alt: str | None = None, profil_neu: str = "") -> set[str]:
    text = KU_QUELLE.read_text(encoding="utf-8")
    profil = KU_PROFIL.read_text(encoding="utf-8")
    if quelle_alt is not None:
        assert text.count(quelle_alt) == 1, f"Anker „{quelle_alt.strip()}“ nicht genau einmal"
        text = text.replace(quelle_alt, quelle_neu)
    if profil_alt is not None:
        assert profil.count(profil_alt) == 1, f"Anker „{profil_alt.strip()}“ nicht genau einmal"
        profil = profil.replace(profil_alt, profil_neu)
    (tmp_path / "profiles").mkdir()
    (tmp_path / "profiles" / KU_PROFIL.name).write_text(profil, encoding="utf-8")
    pfad = tmp_path / KU_QUELLE.name
    pfad.write_text(text, encoding="utf-8")
    return _fehlerregeln(falzmarke.linte(pfad, profil_verzeichnis=RECHNUNG_PROFILE))


def test_die_kleinunternehmer_rechnung_ist_unsabotiert_frei(tmp_path):
    regeln = _ku_regeln(tmp_path)
    assert not regeln, regeln


def test_ein_fehlender_hinweis_faellt_auf(tmp_path):
    regeln = _ku_regeln(tmp_path, profil_alt=f"  kleinunternehmer_hinweis: {KU_HINWEIS}\n")
    assert "rechnung.kleinunternehmer_hinweis" in regeln, regeln


def test_ein_steuersatz_trotz_status_faellt_auf(tmp_path):
    regeln = _ku_regeln(tmp_path, "    einzelpreis: 40.00\n",
                        "    einzelpreis: 40.00\n    steuersatz: 19\n")
    assert "rechnung.kleinunternehmer_steuer" in regeln, regeln


def test_brutto_ungleich_netto_faellt_auf(tmp_path):
    regeln = _ku_regeln(tmp_path, "  brutto: 370.00\n", "  brutto: 440.30\n")
    assert "rechnung.kleinunternehmer_summe" in regeln, regeln


def test_ein_status_als_text_faellt_auf(tmp_path):
    regeln = _ku_regeln(tmp_path, profil_alt="  kleinunternehmer: true\n",
                        profil_neu="  kleinunternehmer: ja\n")
    assert "rechnung.kleinunternehmer" in regeln, regeln


def test_ohne_status_fehlen_steuersatz_und_steuerzeile(tmp_path):
    regeln = _ku_regeln(tmp_path, profil_alt="  kleinunternehmer: true\n", profil_neu="")
    assert {"rechnung.position", "rechnung.steuer"} <= regeln, regeln


def test_lint_prueft_gegen_die_maengelliste_des_emitters(tmp_path, monkeypatch):
    """Meldet der Emitter nichts, muss lint schweigen — sonst hielte lint eine
    eigene Liste, und beide könnten Verschiedenes verlangen."""
    from falzmarke import emit_xml

    monkeypatch.setattr(emit_xml, "kleinunternehmer_maengel", lambda kopf, profil: [])
    regeln = _ku_regeln(tmp_path, "  brutto: 370.00\n", "  brutto: 440.30\n")
    assert "rechnung.kleinunternehmer_summe" not in regeln, regeln


# ── Der Innenabstand der Tabellenzellen (#151) ──────────────────────────────
#
# Die Rasterprüfung nimmt Tabellen aus, und damit ist ihr die Zeilenhöhe
# gleich: Wer `y: 1.4mm` in `emit.py` ändert, verschiebt alles unter der
# Tabelle und bekommt von ihr keinen roten Punkt. Gemessen wird das von
# `test_raster.py::test_eine_tabellenzeile_ist_so_hoch_wie_beschlossen`. Hier
# steht, dass diese Messung rot werden KANN — mit dem Innenabstand, an dem sie
# hängt, nicht mit einer Kopie davon.
#
# Sabotiert wird die Ausgabe des echten Emitters an genau einer Stelle, und die
# Sabotage muss ihren Anker finden: Stünde der Innenabstand dort nicht mehr so,
# verstellte sie nichts, und jede Probe unten wäre aus dem falschen Grund grün.

import tabellenmessung as _tabelle                                  # noqa: E402

TABELLE = REPO / "examples" / "brief-tabelle.md"
INNENABSTAND = "inset: (x: 2mm, y: 1.4mm),"

#: Texthöhe einer 11-pt-Zeile in mm. Die erwartete Zeilenhöhe der Sabotage ist
#: sie plus zweimal der verstellte Innenabstand: 3,88 + 2 · 1,4 = 6,68.
TEXTHOEHE_MM = 3.88


def _tabellen_pdf(tmp_path: Path, monkeypatch, y: str | None) -> tuple[Path, str]:
    if y is not None:
        echt = _emit.tabelle

        def sabotiert(zeilen, ausrichtungen):
            text = echt(zeilen, ausrichtungen)
            assert INNENABSTAND in text, (
                f"Anker „{INNENABSTAND}“ steht nicht mehr im Emitter — "
                "die Sabotage träfe nichts")
            return text.replace(INNENABSTAND, f"inset: (x: 2mm, y: {y}),")

        monkeypatch.setattr(_emit, "tabelle", sabotiert)
    return falzmarke.rendere(TABELLE, tmp_path / "tabelle.pdf")


def _weicht_ab(hoehen: list[float]) -> list[float]:
    return [h for h in hoehen
            if abs(h - _tabelle.ZEILENHOEHE_MM) > _tabelle.TOLERANZ_MM]


def test_die_tabelle_haelt_unsabotiert_die_sollhoehe(tmp_path, monkeypatch):
    """Kontrollprobe. Ohne sie misst jede Sabotage unten nur, dass die Messung
    schon im Ausgangszustand danebenlag."""
    pdf, _ = _tabellen_pdf(tmp_path, monkeypatch, None)
    hoehen = _tabelle.zeilenhoehen_mm(pdf)
    assert len(hoehen) >= 4, hoehen
    assert _weicht_ab(hoehen) == [], hoehen


@pytest.mark.parametrize("y", ["2.293mm", "0.176mm", "1.5mm"],
                         ids=["rastertreu-luftig", "rastertreu-eng", "eine-spur-mehr"])
def test_ein_veraenderter_innenabstand_macht_die_messung_rot(tmp_path, monkeypatch, y):
    """Je Wert einzeln gefahren: die beiden rastertreuen Wege aus dem Vorgang
    (2,293 mm: 2,00 Rasterzeilen; 0,176 mm: 1,00) und 0,1 mm mehr, die kleinste
    Änderung, die ein Mensch am Ausdruck nicht sähe.

    Erwartet wird die Höhe NAMENTLICH — Texthöhe plus zweimal der neue Abstand
    —, nicht „irgendeine andere". Eine Sabotage, die die Zeilen anders verstellt
    als gedacht, hat etwas anderes getroffen als den Innenabstand.
    """
    pdf, _ = _tabellen_pdf(tmp_path, monkeypatch, y)
    hoehen = _tabelle.zeilenhoehen_mm(pdf)
    erwartet = TEXTHOEHE_MM + 2 * float(y.removesuffix("mm"))

    assert _weicht_ab(hoehen) == hoehen, (
        f"y = {y}: die Messung bleibt bei {[round(h, 2) for h in hoehen]} grün")
    assert all(abs(h - erwartet) <= _tabelle.TOLERANZ_MM for h in hoehen), (
        f"y = {y}: erwartet {erwartet:.2f} mm je Zeile, gemessen "
        f"{[round(h, 2) for h in hoehen]} — die Sabotage hat etwas anderes verstellt")


def test_die_rasterpruefung_sieht_den_verstellten_innenabstand_nicht(tmp_path, monkeypatch):
    """Der Grund, warum es die Messung oben überhaupt braucht: Mit 2,293 mm
    verschwinden die Brüche INNERHALB der Tabelle, und die beiden Übergänge sind
    ausgenommen — `geometrie.pruefe` bleibt beim Zeilenraster stumm, obwohl die
    Tabelle um 9 mm gewachsen ist. Fiele die Prüfung hier an, wäre die neue
    Messung überflüssig, und niemand hätte es bemerkt."""
    pdf, form = _tabellen_pdf(tmp_path, monkeypatch, "2.293mm")
    gescheitert = _gescheitert(pdf, form)
    assert not [n for n in gescheitert if "Zeilenraster" in n], gescheitert
