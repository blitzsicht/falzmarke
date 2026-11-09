"""Gegenprobe: Ein Prüfmittel, das nie rot werden kann, ist kein Nachweis.

Jeder Test hier sabotiert das Layout an genau einer Stelle und verlangt, dass
die zugehörige Prüfung anschlägt — und nur sie. Ohne diese Datei wüsste die
Testsuite nur, dass sie grün ist, nicht dass sie misst.
"""

from __future__ import annotations

import re
import sys
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from falzmarke import geometrie
from falzmarke import cli as falzmarke
from falzmarke import lint as _lint
from falzmarke import oeffnen as _oeffnen
from falzmarke import regeln as _regeln
from conftest import PROFILE, REPO
from sabotage import zeile_ersetzt as _zeile_ersetzt
from test_postfach_entwurf import oeffne_befehl                 # noqa: F401 — Fixture, siehe #481
from test_postfach_entwurf import befehl                        # noqa: F401 — Fixture, #549
from test_postfach_frist import schein                         # noqa: F401 — Fixture, Review #570

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
    """Bis #243 fiel dieser Fall als „Bild von aussen“ auf — die Quellenregel
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


def test_eine_schriftfarbe_im_rumpf_faellt_auf(monkeypatch):
    """Seit dem 15.10.2026 erbt der Rumpf Schrift- und Grundfarbe vom
    Mailprogramm. Der naheliegende Rückfall ist die alte Tinte am Absatz —
    `#1a1a1a`, die im Thunderbird-Entwurf dunkel auf dunkel stand.
    `nicht_umschaltbar` muss sie melden, auch mit der alten Klasse daran."""
    quelle = BEISPIEL.read_text(encoding="utf-8").split("---", 2)[2]
    assert _html.nicht_umschaltbar(_html.dokument(_html.setze(_md.lies(quelle)))) == [], \
        "Kontrollprobe: ohne Sabotage meldet die Prüfung schon etwas"
    seite = _seite_mit_sabotiertem_emitter(
        monkeypatch, "absatz",
        lambda inhalt: (f'<p class="{_html.KLASSE_TEXT}" style="{_html.TEXTSTIL} '
                        f'color: #1a1a1a;">{inhalt}</p>'),
    )
    befunde = _html.nicht_umschaltbar(seite)
    assert any("color:" in b for b in befunde), befunde


def test_eine_signatur_mit_ihren_farben_faellt_auf(monkeypatch, tmp_path):
    """Seit dem 15.10.2026 erbt auch die mitgebrachte Signatur ihre Farben.
    Sabotage: `fremdrumpf_ohne_farben` gibt den Rumpf unverändert zurück — die
    Farbmessung muss die Farben der Signatur dann in der Nachricht finden."""
    from farbmessung import farben_im_rumpf
    from falzmarke import eml as _eml

    muster = Path(__file__).parent / "fixtures" / "signatur" / "cw-core-muster.html"
    (tmp_path / "sig.html").write_text(muster.read_text(encoding="utf-8"), encoding="utf-8")
    daten = {"email": {"absender": "muster@example.de", "signatur_html": "sig.html"}}
    kopf = {"typ": "email", "an": "post@example.de", "betreff": "Probe"}

    def seite():
        sig = _eml.mitgebrachte_signatur(daten, tmp_path / "profil.yaml")
        return _eml.htmlteil(kopf, {}, _md.lies("Text.\n"), signatur=sig)

    assert farben_im_rumpf(seite()) == [], "Kontrollprobe: ohne Sabotage meldet die Messung"
    monkeypatch.setattr(_html, "fremdrumpf_ohne_farben", lambda rumpf: (rumpf, []))
    befunde = farben_im_rumpf(seite())
    assert any("#1f2a37" in b for b in befunde), befunde


def test_ein_grund_am_umschlag_faellt_auf(monkeypatch):
    """Der Zwischenstand vom 15.10.2026, vom Betreiber verworfen: ein weißer
    Grund am Umschlag, als Attribut. `nicht_umschaltbar` muss ihn melden."""
    echt = _html.dokument
    seite = _seite_mit_sabotiertem_emitter(
        monkeypatch, "dokument",
        lambda rumpf, **k: echt(rumpf, **k).replace(
            '<tr><td style="padding: 0;">', '<tr><td bgcolor="#ffffff" style="padding: 0;">', 1),
    )
    befunde = _html.nicht_umschaltbar(seite)
    assert any("bgcolor" in b for b in befunde), befunde


# ── Links in der E-Mail: die nackte Adresse (#424) ──────────────────────────
#
# Die Tests in `tests/test_links.py` belegen, dass eine nackte Adresse ein Link
# wird. Hier wird der Leser auf den Stand vor #424 zurückgesetzt, und genau der
# benannte Test muss rot werden. `_url_spannen` liefert dann nichts mehr: Der
# Text wird nicht geteilt, `_pruefe_felder` blendet nichts aus — Zeile für
# Zeile der Code von vorher, kein dritter Zustand.

def test_ohne_teilung_an_der_adresse_wird_test_1_aus_424_rot(monkeypatch):
    import test_links

    test_links.test_nackte_url_als_eigener_absatz_wird_ein_link()  # Kontrollprobe
    monkeypatch.setattr(_md, "_url_spannen", lambda text: [])
    with pytest.raises(AssertionError) as fehler:
        test_links.test_nackte_url_als_eigener_absatz_wird_ein_link()
    # Rot an der erwarteten Stelle: Die Meldung trägt das HTML, und darin steht
    # die Adresse als Text, ohne `<a`. Das ist der Befund aus #424.
    meldung = str(fehler.value)
    assert "https://sign.example.de/s/NB76qgP6sbHGFQ" in meldung and "<a " not in meldung, meldung


def test_ohne_teilung_kommt_der_fehlalarm_am_ausfuellfeld_zurueck(monkeypatch):
    """Der Fehlalarm vor #424: `https://x.de/a___b` brach eine 1.2-Mail ab."""
    import test_links

    test_links.test_unterstriche_in_der_adresse_werden_kein_ausfuellfeld()  # Kontrollprobe
    monkeypatch.setattr(_md, "_url_spannen", lambda text: [])
    with pytest.raises(_md.MarkdownFehler, match="Unterstrichkette"):
        test_links.test_unterstriche_in_der_adresse_werden_kein_ausfuellfeld()


def test_ohne_ausblenden_in_pruefe_felder_kommt_der_fehlalarm_zurueck(monkeypatch):
    """Die Teilung allein reicht nicht: Ohne die eine Zeile in `_pruefe_felder`
    zählt der Rohtext die Kette in der Adresse weiter mit."""
    import test_links

    test_links.test_unterstriche_in_der_adresse_werden_kein_ausfuellfeld()  # Kontrollprobe
    monkeypatch.setattr(_md, "_pruefe_felder", _zeile_ersetzt(
        _md, "_pruefe_felder", 'if lage.ziel == "email":', "if False:"))
    with pytest.raises(_md.MarkdownFehler, match="Unterstrichkette"):
        test_links.test_unterstriche_in_der_adresse_werden_kein_ausfuellfeld()


def test_ohne_im_link_wird_die_adresse_im_linktext_verschachtelt(monkeypatch):
    """`[https://x.de](https://x.de)` — ohne den Schalter `<a>` im `<a>`."""
    import test_links

    test_links.test_eine_adresse_als_linktext_wird_nicht_verschachtelt()  # Kontrollprobe
    monkeypatch.setattr(_md, "_inline", _zeile_ersetzt(
        _md, "_inline", "_inline(kind, lage, lauf, im_link=True)", "_inline(kind, lage, lauf)"))
    with pytest.raises(AssertionError):
        test_links.test_eine_adresse_als_linktext_wird_nicht_verschachtelt()


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
    nötig ist, wenn jemand sie später „vereinfacht“.
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
# Regel hängt —, nicht ihr Ergebnis. Erste Staffel: die Linter-Regeln aus
# Normquellen (`mehrfach_bestaetigt` oder `einzeln_belegt`). Bis #31 waren es die
# mit `wirkung: fehler` aus mehrfach belegten Quellen — `vermerke` und `datum`.
# Beide stehen seither auf Warnung, weil die zweite Quelle zu ihnen schweigt;
# die Prüfung selbst ist dieselbe und gehört weiter sabotiert.

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


def _gemeldet(bericht: _lint.Bericht) -> set[str]:
    """Jede Regel, die etwas gemeldet hat — als Fehler **oder** Warnung.

    Die Sabotagen unten fragen, ob eine Prüfung noch *anschlägt*, nicht, wie
    schwer. Seit #31 stehen `vermerke` und `datum` auf Warnung; eine Probe auf
    `_fehlerregeln` sähe sie weder vor noch nach der Sabotage und bewiese nichts.
    """
    return {b.regel for b in bericht.befunde}


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
    """Wie viele der Linter-Regeln aus Normquellen eine Sabotage-Gegenprobe
    haben. Ohne diese Zählung altert die Lücke aus Issue #197 still weiter,
    statt beim Wachsen der Regeldatei aufzufallen.

    Kandidat ist, was eine Quelle hat, die zur Norm etwas sagen soll — nicht
    mehr, was Fehler sein *darf*: Seit #31 ist das keine dieser Regeln mehr.
    """
    kandidaten = {
        r["lint"] for r in _regeln.alle()
        if r.get("lint") and r.get("herkunft") in (_regeln.MEHRFACH, _regeln.EINZELN)
    }
    unbekannt = LINT_REGELN_MIT_GEGENBEWEIS - kandidaten
    assert not unbekannt, (
        f"Gegenprobe für Regel(n), die es als Kandidat so nicht (mehr) gibt: {unbekannt}")
    print(
        f"\nLint-Gegenbeweis-Abdeckung: {len(LINT_REGELN_MIT_GEGENBEWEIS)}/{len(kandidaten)} "
        "Linter-Regeln aus Normquellen "
        f"(offen: {sorted(kandidaten - LINT_REGELN_MIT_GEGENBEWEIS)})."
    )


def test_lint_unsabotiert_ist_gruen(tmp_path):
    """Kontrollprobe: Die bekannt schlechte Eingabe wird OHNE Sabotage erkannt.

    Ohne sie würden die Sabotage-Tests unten nichts beweisen — ein Befund, der
    von Anfang an nie kam, kann durch die Sabotage nicht verschwinden.
    """
    bericht = _linte(tmp_path, LINT_KOPF + "vermerke: [Eins, Zwei, Drei, Vier]\n")
    assert "vermerke" in _gemeldet(bericht)
    bericht = _linte(tmp_path, LINT_KOPF.replace("datum: 2026-08-25", "datum: 20260825"))
    assert "datum" in _gemeldet(bericht)


def test_verstellter_vermerke_schwellwert_faellt_nicht_mehr_auf(tmp_path, monkeypatch):
    """Der Schwellwert IST die Regel `text.vermerke_max_3` — wird er
    verstellt, darf das nur diese eine Prüfung merken, sonst nichts."""
    _sabotiere_konstante(monkeypatch, "VERMERKE_MAX_ZEILEN", 3, 99)
    bericht = _linte(tmp_path, LINT_KOPF + "vermerke: [Eins, Zwei, Drei, Vier]\n")
    assert "vermerke" not in _gemeldet(bericht), (
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
    assert "datum" not in _gemeldet(bericht), (
        "Die Sabotage hat nicht gewirkt — 20260825 ohne Bindestriche wäre mit "
        "dem durchlässigen Muster nicht mehr zu beanstanden"
    )
    assert bericht.ok, (
        "Die Sabotage hat mehr als die eine Lücke getroffen:\n" + bericht.als_text("brief.md")
    )

    # Ein Datum, das auch `date.fromisoformat` ablehnt, bleibt erkannt — die
    # Sabotage trifft nur die eine Lücke, nicht die ganze Prüfung.
    bericht = _linte(tmp_path, LINT_KOPF.replace("datum: 2026-08-25", "datum: morgen"))
    assert "datum" in _gemeldet(bericht)


# ── Die Signatur-Fixture: sabotierte Quellzeile, nicht sabotiertes Ergebnis ──
#
# #221 verlangt: „Eine verfälschte Zeile in `signatur_bloecke()` macht mindestens
# einen Eintrag rot — eine Fixture, die jede Fassung durchwinkt, wäre keine.“
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
#: einer“: Eine Sabotage, die plötzlich andere Fälle trifft, hat einen anderen
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
    # macht den Unterschied zwischen „Datei im PDF“ und „erkennbare Rechnung“.
    assert _rechnung_anhaenge(pdf) == ["factur-x.xml"]


# ── Die Fassungszeile im Messbericht liest die Datei (#117) ─────────────────
#
# Bis #117 gab die Zeile „E-Rechnung“ Profil und Fassung aus Konstanten aus und
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
    —, nicht „irgendeine andere“. Eine Sabotage, die die Zeilen anders verstellt
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


# ── Urkunde: das Schriftstück ohne Anschriftfeld (ADR 0048) ─────────────────
#
# Jede Prüfung der Urkundenliste bekommt hier ihre Sabotage: Der Satz wird an
# genau einer Stelle verstellt, und erwartet wird NAMENTLICH, was daraufhin rot
# wird — die ganze Menge, nicht „mindestens eine“. Eine Sabotage, die mehr oder
# anderes trifft als gedacht, hat etwas anderes verstellt.
#
# Jede steht in einem eigenen Test und läuft für sich: Gebündelt ginge eine
# Prüfung, die nie rot wird, im Rot der anderen unter.

URKUNDE_VEREINBARUNG = REPO / "examples" / "urkunde" / "urkunde-vereinbarung.md"
URKUNDE_ERKLAERUNG = REPO / "examples" / "urkunde" / "urkunde-erklaerung.md"
URKUNDE_ZWEI_SEITEN = REPO / "tests" / "fixtures" / "urkunde" / "zwei-seiten-bei-einer.md"


def _rendere_urkunde(tmp_path: Path, typst_dir: Path, quelle: Path = URKUNDE_VEREINBARUNG) -> Path:
    original = falzmarke.TYPST_DIR
    falzmarke.TYPST_DIR = typst_dir
    try:
        return falzmarke.rendere(quelle, tmp_path / "urkunde.pdf",
                                 profil_verzeichnis=typst_dir / "profiles")[0]
    finally:
        falzmarke.TYPST_DIR = original


def _urkunde_gescheitert(pdf: Path) -> set[str]:
    assert geometrie.typ_aus_metadaten(pdf) == "urkunde", "gemessen würde die Briefliste"
    return {p.name for p in geometrie.pruefe(pdf, "").pruefungen if not p.bestanden}


@pytest.mark.parametrize("quelle", [URKUNDE_VEREINBARUNG, URKUNDE_ERKLAERUNG],
                         ids=lambda p: p.stem)
def test_urkunde_unsabotiert_ist_gruen(tmp_path, quelle):
    """Kontrollprobe: derselbe Weg über die Kopie, ohne wirksame Änderung."""
    kopie = _sabotiere(tmp_path, "falzmarke.typ", "#let unterschrift-linie = 65mm",
                       "#let unterschrift-linie = 65mm  // unverändert")
    assert _urkunde_gescheitert(_rendere_urkunde(tmp_path, kopie, quelle)) == set()


def test_urkunde_zweite_seite_bei_erlaubter_einer(tmp_path):
    """Abnahme, Sabotage 1: Die Quelle verlangt eine Seite und füllt zwei."""
    kopie = _sabotiere(tmp_path, "falzmarke.typ", "#let unterschrift-linie = 65mm",
                       "#let unterschrift-linie = 65mm  // unverändert")
    pdf = _rendere_urkunde(tmp_path, kopie, URKUNDE_ZWEI_SEITEN)
    assert _urkunde_gescheitert(pdf) == {"Seitenzahl"}


def test_urkunde_dieselben_zwei_seiten_sind_mit_grenze_zwei_gruen(tmp_path):
    """Die Kontrollprobe dazu: Nicht die zweite Seite ist der Fehler, sondern die Grenze."""
    quelle = tmp_path / "zwei.md"
    text = URKUNDE_ZWEI_SEITEN.read_text(encoding="utf-8")
    assert "seiten_max: 1" in text
    quelle.write_text(text.replace("seiten_max: 1", "seiten_max: 2"), encoding="utf-8")
    pdf, _ = falzmarke.rendere(quelle, tmp_path / "zwei.pdf")
    assert _urkunde_gescheitert(pdf) == set()


def test_urkunde_unterschriftsfeld_ausserhalb_des_satzspiegels(tmp_path):
    """Abnahme, Sabotage 2: Der Unterschriftsblock rutscht über den rechten Rand.

    Die rechte Linie endet dann bei 247,5 statt 177,5 mm. Die Wortmessung des
    Briefes sähe davon nichts — eine Linie trägt keine Wörter.
    """
    kopie = _sabotiere(
        tmp_path, "falzmarke.typ",
        "pad(bottom: 1mm, line(length: unterschrift-linie, stroke: 0.5pt))",
        "pad(bottom: 1mm, left: 70mm, line(length: unterschrift-linie, stroke: 0.5pt))")
    rot = _urkunde_gescheitert(_rendere_urkunde(tmp_path, kopie))
    assert rot == {"Unterschriftslinien, im Satzspiegel", "Seite 1, Linien im Satzspiegel",
                   "Unterschriftslinien, Name darunter"}, rot


def test_urkunde_linie_anderer_laenge_ist_keine_unterschriftslinie(tmp_path):
    kopie = _sabotiere(tmp_path, "falzmarke.typ", "#let unterschrift-linie = 65mm",
                       "#let unterschrift-linie = 64mm")
    rot = _urkunde_gescheitert(_rendere_urkunde(tmp_path, kopie))
    assert rot == {"Unterschriftslinien, Anzahl"}, rot


def test_urkunde_zu_wenig_raum_ueber_der_linie(tmp_path):
    """Eine Zeile statt dreier: Die Ort-Datum-Zeile steht im Raum der Unterschrift."""
    kopie = _sabotiere(
        tmp_path, "falzmarke.typ",
        "rows: if mit-rolle { (3 * zeile, zeile, letzte) } else { (3 * zeile, letzte) },",
        "rows: if mit-rolle { (1 * zeile, zeile, letzte) } else { (1 * zeile, letzte) },")
    rot = _urkunde_gescheitert(_rendere_urkunde(tmp_path, kopie))
    assert rot == {"Unterschriftslinien, Raum darüber"}, rot


def test_urkunde_linien_ohne_abstand(tmp_path):
    """Der Befund, mit dem der Vorgang begann: zwei Linien, die wie eine aussehen."""
    kopie = _sabotiere(
        tmp_path, "falzmarke.typ",
        "        columns: (1fr, 1fr),\n        column-gutter: 10mm,\n        rows: if mit-rolle",
        "        columns: (65mm, 65mm),\n        column-gutter: 2mm,\n        rows: if mit-rolle")
    rot = _urkunde_gescheitert(_rendere_urkunde(tmp_path, kopie))
    assert rot == {"Unterschriftslinien, Abstand"}, rot


def test_urkunde_linien_auf_verschiedener_hoehe(tmp_path):
    kopie = _sabotiere(
        tmp_path, "falzmarke.typ",
        "..range(2).map(i => if i < unterschriften.len() {\n"
        "          grid.cell(align: bottom + left, pad(bottom: 1mm,",
        "..range(2).map(i => if i < unterschriften.len() {\n"
        "          grid.cell(align: bottom + left, pad(bottom: 1mm + i * 3mm,")
    rot = _urkunde_gescheitert(_rendere_urkunde(tmp_path, kopie))
    assert rot == {"Unterschriftslinien, gleiche Höhe", "Unterschriftslinien, Name darunter"}, rot


def test_urkunde_titel_an_falscher_stelle(tmp_path):
    kopie = _sabotiere(tmp_path, "falzmarke.typ", "  heading(level: 1, daten.titel)",
                       "  v(2 * zeile)\n  heading(level: 1, daten.titel)")
    rot = _urkunde_gescheitert(_rendere_urkunde(tmp_path, kopie))
    assert rot == {"Titel, y-Oberkante"}, rot


def test_urkunde_titel_in_textgroesse(tmp_path):
    """Der Befund, mit dem die Rückmeldung zu #381 begann: ein Titel in 11 pt,
    der sich von den Abschnitten nicht abhebt."""
    kopie = _sabotiere(tmp_path, "falzmarke.typ", "#let urkunde-titel-pt = 16pt",
                       "#let urkunde-titel-pt = 11pt")
    rot = _urkunde_gescheitert(_rendere_urkunde(tmp_path, kopie))
    assert "Titel, Schriftgröße" in rot, rot
    assert rot <= {"Titel, Schriftgröße", "Seite 1, Zeilenraster"}, rot


def test_urkunde_ohne_trennlinie(tmp_path):
    kopie = _sabotiere(tmp_path, "falzmarke.typ",
                       "  block(above: zeile, below: 0pt, line(length: 100%, stroke: 0.5pt))",
                       "  block(above: zeile, below: 0pt, [])")
    rot = _urkunde_gescheitert(_rendere_urkunde(tmp_path, kopie))
    assert rot == {"Trennlinie unter dem Kopf"}, rot


def test_urkunde_parteien_in_textgroesse(tmp_path):
    kopie = _sabotiere(tmp_path, "falzmarke.typ", "#let urkunde-parteien-pt = 12pt",
                       "#let urkunde-parteien-pt = 11pt")
    rot = _urkunde_gescheitert(_rendere_urkunde(tmp_path, kopie))
    assert "Parteien, Schriftgröße" in rot, rot
    assert rot <= {"Parteien, Schriftgröße", "Seite 1, Zeilenraster"}, rot


URKUNDE_PARAPHEN = (
    "---\nprofil: example\ntyp: urkunde\ndialekt: \"1.2\"\ntitel: Probe\n"
    "parteien:\n  - name: Beispiel GmbH\n  - name: Max Muster\nparaphen: true\n---\n\n"
    "## 1. Füllung\n\n" + "\n\n".join(
        f"Absatz {i}: Dieser Text füllt die Seite, damit die Unterschriften auf die "
        "zweite rutschen und die erste ihre Paraphen trägt." for i in range(1, 26)) + "\n")


def test_urkunde_paraphe_fehlt_auf_der_ersten_seite(tmp_path):
    quelle = tmp_path / "paraphen.md"
    quelle.write_text(URKUNDE_PARAPHEN, encoding="utf-8")
    pdf, _ = falzmarke.rendere(quelle, tmp_path / "gut.pdf")
    assert _urkunde_gescheitert(pdf) == set()                    # Kontrollprobe
    kopie = _sabotiere(tmp_path, "falzmarke.typ",
                       '        let zahl = daten.at("unterschriften", default: ()).len()',
                       '        let zahl = daten.at("unterschriften", default: ()).len() - 1')
    rot = _urkunde_gescheitert(_rendere_urkunde(tmp_path, kopie, quelle))
    assert rot == {"Paraphen"}, rot


def test_urkunde_blocksatz_ohne_randschutz(tmp_path):
    """Ohne `overhang: false` hängt Typst Trennstriche in den Rand — gemessen 190,66 mm."""
    kopie = _sabotiere(tmp_path, "falzmarke.typ", "    set text(overhang: false)\n", "")
    rot = _urkunde_gescheitert(_rendere_urkunde(tmp_path, kopie))
    assert rot == {"Seite 1, rechter Rand"}, rot


def test_urkunde_mit_falzmarken_ist_ein_brief(tmp_path):
    """Die Urkunde bekommt die Marken des Briefes in den Seitenhintergrund."""
    kopie = _sabotiere(
        tmp_path, "falzmarke.typ",
        "    // Folgeseiten: der Titel als Kopfzeile, wie beim Brief der Betreff.",
        "    background: place(top + left, dx: 5mm, dy: 105mm, "
        "line(length: 2.5mm, stroke: 0.25pt + black)),")
    rot = _urkunde_gescheitert(_rendere_urkunde(tmp_path, kopie))
    assert rot == {"Keine Marken im Heftrand", "Seite 1, Linien im Satzspiegel"}, rot


def test_urkunde_ausfuellfeld_laeuft_aus_dem_satzspiegel(tmp_path):
    """Ein Feld von 20 Unterstrichen misst mit 9 mm je Strich 180 mm — breiter als der Satz.

    Das Feld steht am Ende des Absatzes, damit kein Wort hinter ihm mitwandert:
    Dann bleibt die Wortmessung stumm, und genau das ist der Grund, warum es
    die Linienprüfung gibt. (Am Musterdokument schlägt zusätzlich `rechter
    Rand` an — dort steht ein Punkt hinter dem Feld.)
    """
    quelle = tmp_path / "feld.md"
    quelle.write_text(
        "---\nprofil: example\ntyp: urkunde\ndialekt: \"1.2\"\ntitel: Probe\n---\n\n"
        "Eintrag: ____________________\n", encoding="utf-8")
    pdf, _ = falzmarke.rendere(quelle, tmp_path / "gut.pdf")
    assert _urkunde_gescheitert(pdf) == set()                    # Kontrollprobe
    kopie = _sabotiere(tmp_path, "falzmarke.typ", "#let feld-einheit = 2mm",
                       "#let feld-einheit = 9mm")
    rot = _urkunde_gescheitert(_rendere_urkunde(tmp_path, kopie, quelle))
    assert rot == {"Seite 1, Linien im Satzspiegel"}, rot


def test_urkunde_rasterfehler_unter_dem_unterschriftsblock(tmp_path):
    """Der Fehler, den die Rasterprüfung am ersten Musterdokument gefunden hat:
    Die letzte Gitterzeile misst 12 statt 11 pt, und der Anlagenvermerk steht
    2,08 statt 2,00 Zeilen tiefer."""
    kopie = _sabotiere(tmp_path, "falzmarke.typ", "let letzte = zeile - durchschuss",
                       "let letzte = zeile")
    rot = _urkunde_gescheitert(_rendere_urkunde(tmp_path, kopie))
    assert rot == {"Seite 1, Zeilenraster"}, rot


def test_urkunde_angabentabelle_ausserhalb_des_rasters(tmp_path):
    """Ohne Rahmen erkennt die Messung die Angabentabelle nicht als Tabelle —
    sie ist also nicht ausgenommen und muss das Raster selbst halten."""
    kopie = _sabotiere(tmp_path, "falzmarke.typ", "    row-gutter: durchschuss,",
                       "    row-gutter: 3pt,")
    rot = _urkunde_gescheitert(_rendere_urkunde(tmp_path, kopie, URKUNDE_ERKLAERUNG))
    assert rot == {"Seite 1, Zeilenraster"}, rot


def test_urkunde_leere_ort_datum_linie_ausserhalb_des_rasters(tmp_path):
    """Der zweite Fehler, den die Rasterprüfung gefunden hat: 2,63 statt 3,00 Zeilen."""
    quelle = tmp_path / "ohne.md"
    quelle.write_text(
        "---\nprofil: example\ntyp: urkunde\ndialekt: \"1.2\"\ntitel: Probe\n"
        "unterschriften:\n  - name: Erika Muster\n---\n\nEin Absatz.\n", encoding="utf-8")
    # Kontrollprobe im selben Test: Unverändert hält diese Quelle das Raster.
    pdf, _ = falzmarke.rendere(quelle, tmp_path / "gut.pdf")
    assert _urkunde_gescheitert(pdf) == set()
    kopie = _sabotiere(
        tmp_path, "falzmarke.typ",
        "block(above: 0pt, below: 0pt, height: zeile, align(bottom + left, feld(30)))",
        "block(above: 0pt, below: durchschuss, feld(30))")
    rot = _urkunde_gescheitert(_rendere_urkunde(tmp_path, kopie, quelle))
    assert rot == {"Seite 1, Zeilenraster"}, rot


# ── „Rechnung“ ist kein Kürzel (#386) ───────────────────────────────────────

RECHNUNG_APPLE = ("---\nprofil: example\nempfaenger: [Muster GmbH, Musterstraße 1, 12345 Musterstadt]\n"
                  "datum: 2026-10-07\nbetreff: Ein Betreff\nanrede: Sehr geehrte Damen und Herren,\n"
                  "---\nRechnung Apple\n")


def _rechnung_als_kuerzel(tmp_path: Path) -> list[str]:
    from falzmarke import typografie
    pfad = tmp_path / "brief.md"
    pfad.write_text(RECHNUNG_APPLE, encoding="utf-8")
    bericht = falzmarke.linte(pfad, profil_verzeichnis=PROFILE)
    regel = _regeln.fuer_typografie("_vor_angabe")["id"]
    return [b.meldung.replace(typografie.NBSP, " ") for b in bericht.befunde
            if b.regel == regel and "Rechnung" in b.meldung.replace(typografie.NBSP, " ")]


def test_rechnung_apple_ist_unsabotiert_still(tmp_path):
    assert _rechnung_als_kuerzel(tmp_path) == []


def test_rechnung_zurueck_in_der_kuerzelliste_meldet_rechnung_apple(tmp_path, monkeypatch):
    """Die Sabotage stellt den Stand vor #386 her. Die Probe, die
    `tests/test_vor_angabe_regel.py` fährt, muss dann anschlagen — sonst
    hielte sie den Fehlalarm nicht fest."""
    from falzmarke import typografie
    assert "Rechnung" not in typografie.VOR_ANGABE, "Vorbedingung: der Stand nach #386"
    monkeypatch.setattr(typografie, "VOR_ANGABE", [*typografie.VOR_ANGABE, "Rechnung"])
    meldungen = _rechnung_als_kuerzel(tmp_path)
    assert len(meldungen) == 1 and "Rechnung Apple" in meldungen[0], meldungen


# ── Thunderbird: alle Anhänge in EINEM Wert (ADR 0049) ──────────────────────
#
# Gemessen am 13.10.2026, Thunderbird 154.0: `-compose` nimmt mehrere Anhänge
# nur als einen Wert `attachment='a,b'` an; ein zweiter `attachment=`-Schlüssel
# wird verworfen — stillschweigend, mit Exit 0. Ein Exit-Code sieht das nie.
# Deshalb liest `_compose_stimmt` die Zeile vor dem Aufruf so zurück, wie
# Thunderbird sie liest, und hält sie gegen die Vorgabe. Hier wird der Aufbau
# an genau einer Stelle sabotiert — `anhang_paare` baut die naheliegende
# Fassung, ein Schlüssel je Datei —, und die Prüfung muss anschlagen.

_FELDER_TB = {"betreff": "Probe", "html": "<p>Text</p>", "an": ["a@example.org"],
              "kopie": [], "blindkopie": [], "absender": "absender@example.org",
              "anhaenge": [("a.pdf", b"a"), ("b.txt", b"b")]}
_PFADE = ["/tmp/a.pdf", "/tmp/b.txt"]


def test_unsabotiert_traegt_die_compose_zeile_beide_anhaenge():
    """Kontrollprobe: ohne Sabotage darf nichts anschlagen."""
    _, zeile = _oeffnen.compose_argumente(_FELDER_TB, _PFADE)
    assert zeile.count("attachment=") == 1
    assert _oeffnen._compose_stimmt(zeile, _FELDER_TB, _PFADE) is None


def _ein_schluessel_je_datei(pfade):
    return [("attachment", pfad) for pfad in pfade]


def test_zwei_anhangschluessel_fallen_auf(monkeypatch):
    monkeypatch.setattr(_oeffnen, "anhang_paare", _ein_schluessel_je_datei)
    _, zeile = _oeffnen.compose_argumente(_FELDER_TB, _PFADE)
    assert zeile.count("attachment=") == 2, "die Sabotage griff nicht"
    grund = _oeffnen._compose_stimmt(zeile, _FELDER_TB, _PFADE)
    assert grund and "Anhänge: 1 statt 2" in grund, grund


def test_die_sabotierte_zeile_erreicht_thunderbird_nicht(monkeypatch, tmp_path):
    """Der Weg bis zum Aufruf: Die Prüfung steht VOR dem Prozess, nicht danach."""
    monkeypatch.setattr(_oeffnen, "anhang_paare", _ein_schluessel_je_datei)
    aufrufe = []

    def nie(argv, **kwargs):
        aufrufe.append(argv)
        raise AssertionError("die sabotierte Zeile wurde übergeben")

    lage = _oeffnen.entwurf(_FELDER_TB, plattform="darwin", umgebung={"DISPLAY": ":0"},
                            laufen=nie, binaer=lambda: "/x/thunderbird", ablage=tmp_path)
    assert lage.programm is None and "Anhänge: 1 statt 2" in lage.grund
    assert aufrufe == []
    assert not list(tmp_path.iterdir()), "der Anhangordner blieb liegen"


# ── Thunderbird: das Logo reist als Data-URI mit (ADR 0049, Nachtrag) ──────
#
# Gemessen am 13.10.2026, 13:15: Im echten Entwurf stand statt des Logos ein
# kaputtes Bild mit Alt-Text — `-compose body=` kennt die `cid:`-Teile nicht.
# `eingebettet` ersetzt den Verweis durch das Bild; `_eingebettet_stimmt` hält
# den Rumpf vor dem Aufruf dagegen. Zwei Sabotagen, je an einer Stelle: die
# Umwandlung bleibt aus, und die Umwandlung nimmt den falschen Typ.

import base64 as _base64

_INLINE = [("falzmarke-logo", "image/png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 8)]
_FELDER_LOGO = {**_FELDER_TB, "anhaenge": [], "inline": _INLINE,
                "html": '<p>T</p><img src="cid:falzmarke-logo" alt="Logo">'}


def _nie(argv, **kwargs):
    raise AssertionError(f"ein Rumpf, der das Logo nicht trägt, wurde übergeben: {argv[:2]}")


def test_unsabotiert_traegt_der_rumpf_das_logo():
    """Kontrollprobe: ohne Sabotage darf nichts anschlagen."""
    html = _oeffnen.eingebettet(_FELDER_LOGO["html"], _INLINE)
    assert _oeffnen._eingebettet_stimmt(html, _INLINE) is None
    assert "cid:" not in html and html.count("data:image/png;base64,") == 1


def test_ohne_umwandlung_bleibt_cid_und_faellt_auf(monkeypatch):
    monkeypatch.setattr(_oeffnen, "eingebettet", lambda html, inline: html)
    lage = _oeffnen.entwurf(_FELDER_LOGO, plattform="darwin", umgebung={"DISPLAY": ":0"},
                            laufen=_nie, binaer=lambda: "/x/thunderbird")
    assert lage.programm is None and "cid:" in lage.grund, lage


def test_ein_falscher_mime_typ_faellt_auf(monkeypatch):
    def png_fuer_alles(html, inline):
        for kennung, _mime, daten in inline:
            html = html.replace(f"cid:{kennung}",
                                "data:image/png;base64," + _base64.b64encode(daten).decode())
        return html

    monkeypatch.setattr(_oeffnen, "eingebettet", png_fuer_alles)
    felder = {**_FELDER_LOGO, "inline": [("falzmarke-logo", "image/jpeg", b"j")]}
    lage = _oeffnen.entwurf(felder, plattform="darwin", umgebung={"DISPLAY": ":0"},
                            laufen=_nie, binaer=lambda: "/x/thunderbird")
    assert lage.programm is None and "image/jpeg" in lage.grund, lage


# ── Thunderbird: der Rumpf auf einer Zeile, ohne Hülle (ADR 0049, 2. Lauf) ──
#
# Gemessen am 13.10.2026 am echten Entwurf: Jeder Zeilenumbruch im `body=`-Wert
# wird ein Zeilenumbruch im Entwurf. Ein Tag über zwei Zeilen zerfällt, die
# Hülle wird Leerzeilen. Drei Sabotagen, je an einer Stelle: A und B fängt
# `_rumpf_stimmt`, C fängt `_eingebettet_stimmt` (die Umbrüche werden vorher zu
# Leerzeichen, und dann stimmt die URI nicht mehr mit den Bytes überein). Der
# Nachbau der Thunderbird-Lesart muss den Fehler zeigen.

_HUELLE = (
    '<!DOCTYPE html>\n<html>\n<head>\n<meta charset="utf-8">\n<style>\n.a{}\n</style>\n'
    '</head>\n<body style="margin: 0;">\n<p>Grüße</p>\n'
    '<table border="0"\n       style="border-collapse: collapse;">\n'
    '<tr><td><img src="cid:falzmarke-logo" alt="Logo"></td></tr></table>\n</body>\n</html>\n'
)
_FELDER_HUELLE = {**_FELDER_LOGO, "html": _HUELLE}


def _text_wie_thunderbird(rumpf: str) -> str:
    z = _oeffnen._Tagzaehler()
    z.feed(rumpf.replace("\n", "<br>"))
    z.close()
    return "".join(z.text)


def test_unsabotiert_vertraegt_der_rumpf_thunderbird():
    """Kontrollprobe: ohne Sabotage darf nichts anschlagen."""
    rumpf = _oeffnen.rumpf_fuer_compose(_oeffnen.eingebettet(_HUELLE, _INLINE))
    assert _oeffnen._rumpf_stimmt(rumpf) is None
    assert 'style="border-collapse' not in _text_wie_thunderbird(rumpf)


def test_sabotage_a_umbrueche_bleiben_das_tag_zerfaellt(monkeypatch):
    """Fehler A: Die Aufbereitung lässt die Umbrüche stehen."""
    monkeypatch.setattr(_oeffnen, "rumpf_fuer_compose", lambda html: html.strip())
    rumpf = _oeffnen.rumpf_fuer_compose(_HUELLE)
    assert 'style="border-collapse' in _text_wie_thunderbird(rumpf), "der Nachbau zeigt A nicht"
    lage = _oeffnen.entwurf(_FELDER_HUELLE, plattform="darwin", umgebung={"DISPLAY": ":0"},
                            laufen=_nie, binaer=lambda: "/x/thunderbird")
    assert lage.programm is None and "Zeilenumbruch" in lage.grund, lage


def test_sabotage_b_die_huelle_bleibt(monkeypatch):
    """Fehler B: Umbrüche weg, aber Hülle und Leerraum bleiben."""
    import re as _re
    monkeypatch.setattr(_oeffnen, "rumpf_fuer_compose",
                        lambda html: _re.sub(r"\s*\n\s*", " ", html))
    lage = _oeffnen.entwurf(_FELDER_HUELLE, plattform="darwin", umgebung={"DISPLAY": ":0"},
                            laufen=_nie, binaer=lambda: "/x/thunderbird")
    assert lage.programm is None and "Hülle" in lage.grund, lage


def test_sabotage_c_umbrueche_in_der_data_uri(monkeypatch):
    """Base64 mit Umbruch alle 76 Zeichen — so steht es in der .eml, und so
    darf es nicht in die Zeile."""
    def mit_umbruechen(html, inline):
        for kennung, mime, daten in inline:
            html = html.replace(f"cid:{kennung}",
                                f"data:{mime};base64," + _base64.encodebytes(daten).decode())
        return html

    monkeypatch.setattr(_oeffnen, "eingebettet", mit_umbruechen)
    felder = {**_FELDER_HUELLE, "inline": [("falzmarke-logo", "image/png", b"\x89PNG" * 40)]}
    roh = mit_umbruechen(_HUELLE, felder["inline"])
    assert "\n" in roh.split("data:image/png;base64,")[1].split('"')[0], "die Sabotage griff nicht"
    lage = _oeffnen.entwurf(felder, plattform="darwin", umgebung={"DISPLAY": ":0"},
                            laufen=_nie, binaer=lambda: "/x/thunderbird")
    assert lage.programm is None and "falzmarke-logo" in lage.grund, lage


# ── Die Signatur aus dem Profil verlässt den Thunderbird-Entwurf (ADR 0050) ──
#
# Trägt die Identität in Thunderbird eine Signatur, nimmt `ohne_signatur` die
# aus dem Profil aus dem HTML-Teil; `_ohne_signatur_stimmt` hält danach den
# fertigen `body=`-Wert gegen den alten: Es darf genau die Signatur fehlen, und
# sonst nichts. Sabotiert wird `ohne_signatur` — einmal schneidet es zu viel
# (die Grußformel mit), einmal gar nichts. Beide Male muss die Prüfung
# anschlagen, und der Entwurf behält die Signatur.

def _signaturfall(tmp_path):
    import test_thunderbird_signatur as tbs

    datei = tmp_path / "sig.html"
    datei.write_text("<p>Firma</p>", encoding="utf-8")
    _, felder, unterschrift = tbs._beispiel(tmp_path, "email-mahnung")
    ordner = tbs._attrappe(tmp_path, tbs._grundwerte(datei))
    return tbs, felder, unterschrift, ordner


def test_unsabotiert_fehlt_dem_entwurf_genau_die_signatur(tmp_path):
    """Kontrollprobe: ohne Sabotage keine Meldung, und die Signatur ist draußen."""
    tbs, felder, unterschrift, ordner = _signaturfall(tmp_path)
    lage, tb = tbs._entwurf(felder, ordner)
    assert lage.signatur.zustand == "thunderbird", lage.signatur
    assert tbs._signatur_im_rumpf(unterschrift, felder) not in tb.rumpf


def test_eine_zu_gierige_entnahme_faellt_auf(tmp_path, monkeypatch):
    tbs, felder, unterschrift, ordner = _signaturfall(tmp_path)
    echt = _oeffnen.ohne_signatur

    def mit_gruss(html, stueck):
        ohne = echt(html, stueck)
        return re.sub(r"<p[^>]*>Mit freundlichen Grüßen</p>", "", ohne)

    monkeypatch.setattr(_oeffnen, "ohne_signatur", mit_gruss)
    assert "Mit freundlichen Grüßen" not in mit_gruss(felder["html"], unterschrift), \
        "die Sabotage griff nicht"
    lage, tb = tbs._entwurf(felder, ordner)
    assert lage.signatur.zustand == "unbestimmt", lage.signatur
    assert "mehr als die Signatur" in lage.signatur.grund
    assert tbs._signatur_im_rumpf(unterschrift, felder) in tb.rumpf
    assert "Mit freundlichen Grüßen" in tb.rumpf


def test_eine_entnahme_ohne_wirkung_faellt_auf(tmp_path, monkeypatch):
    tbs, felder, unterschrift, ordner = _signaturfall(tmp_path)
    monkeypatch.setattr(_oeffnen, "ohne_signatur", lambda html, stueck: html)
    lage, tb = tbs._entwurf(felder, ordner)
    assert lage.signatur.zustand == "unbestimmt", lage.signatur
    assert "noch im Rumpf" in lage.signatur.grund
    assert tb.rumpf.count(tbs._signatur_im_rumpf(unterschrift, felder)) == 1


# ── Eine Adresse läuft nicht über das Zeilenende (14.10./17.10.2026) ───────
#
# Der Emitter setzt jedes Wort mit Mail-Adresse, Domain oder URL unteilbar
# (`netzadressen.zerlege`, `emit.as_text`); `verify` sucht im fertigen PDF nach
# einer, die trotzdem getrennt ist. Sabotiert wird der Schutz: Gilt kein Wort
# mehr als Adresse, setzt Typst die Probe wie vor dem Fix — und dann muss genau
# diese eine Prüfung anschlagen, keine andere. Die Probe ist so gebaut, dass
# ohne Schutz alle vier Adressen am Zeilenende stehen.

from falzmarke import netzadressen as _netzadressen               # noqa: E402

ADRESSPROBE = REPO / "tests" / "fixtures" / "trennung" / "adressen.md"


def test_adressprobe_unsabotiert_ist_gruen(tmp_path):
    """Kontrollprobe: Mit dem Schutz schlägt nichts an."""
    pdf, form = falzmarke.rendere(ADRESSPROBE, tmp_path / "adressen.pdf")
    assert _gescheitert(pdf, form) == set()


def test_ohne_schutz_faellt_die_getrennte_adresse_auf(tmp_path, monkeypatch):
    monkeypatch.setattr(_netzadressen, "zerlege", lambda text: [(text, False)])
    assert "#box(" not in _emit.as_text("an servus@blitzsicht.com"), "die Sabotage griff nicht"
    pdf, form = falzmarke.rendere(ADRESSPROBE, tmp_path / "adressen.pdf")
    assert _gescheitert(pdf, form) == {"Netzadressen ungetrennt"}


# ── Review von #397: Spalten und lange Adressen ─────────────────────────────
#
# Zwei Schutzstellen in `verify`, je mit ihrer Sabotage. Die erste hält einen
# Fehlalarm fern: Zeilen werden nur innerhalb ihrer Spalte gepaart. Die zweite
# findet einen Umbruch, den die Prüfung bis dahin übersah: eine URL über der
# Längengrenze, die ohne Strich nach „/“ oder mitten im Wort umbricht.

SPALTENPROBE = REPO / "tests" / "fixtures" / "trennung" / "tabelle-spalten.md"
LANGE_URL = REPO / "tests" / "fixtures" / "trennung" / "lange-url.md"


def _ganze_zeilen(seite, unteilbar_bis):
    """Die Paarung vor dem Review: eine Zeile ist alles auf derselben Höhe."""
    return [([" ".join(s.text for s in sorted(zeile, key=lambda s: s.x0))
              for zeile in geometrie._zeilen_gruppieren(geometrie._spans(seite))],
             unteilbar_bis)]


def test_spaltenprobe_unsabotiert_ist_gruen(tmp_path):
    pdf, form = falzmarke.rendere(SPALTENPROBE, tmp_path / "spalten.pdf")
    assert _gescheitert(pdf, form) == set()


def test_ohne_spalten_paart_verify_ueber_die_zellen_hinweg(tmp_path, monkeypatch):
    """Ende der rechten Zelle und Anfang der linken: „Leistungsbeschrei-“ / „servus@…“."""
    pdf, form = falzmarke.rendere(SPALTENPROBE, tmp_path / "spalten.pdf")
    monkeypatch.setattr(geometrie, "_textfluesse", _ganze_zeilen)
    bericht = geometrie.pruefe(pdf, form)
    assert {p.name for p in bericht.pruefungen if not p.bestanden} == {"Netzadressen ungetrennt"}
    pruefung = next(p for p in bericht.pruefungen if p.name == "Netzadressen ungetrennt")
    assert "Leistungsbeschrei- ⏎ servus@blitzsicht.com" in pruefung.ist


def test_lange_url_unsabotiert_faellt_auf(tmp_path):
    """Kontrollprobe andersherum: Die Probe ist ein Befund, und nur dieser."""
    pdf, form = falzmarke.rendere(LANGE_URL, tmp_path / "lange-url.pdf")
    assert _gescheitert(pdf, form) == {"Netzadressen ungetrennt"}


def test_ohne_laengenprobe_bleibt_die_lange_url_unbemerkt(tmp_path, monkeypatch):
    """Gilt jedes Wort als Box, war jeder Umbruch einer am Leerraum — und alles ist grün.

    Gesetzt wird vor der Sabotage: Sie trifft nur `verify`, nicht den Satz.
    """
    pdf, form = falzmarke.rendere(LANGE_URL, tmp_path / "lange-url.pdf")
    monkeypatch.setattr(_netzadressen, "UNTEILBAR_BIS", 10**6)
    assert _gescheitert(pdf, form) == set()


ZELLE_URL = REPO / "tests" / "fixtures" / "trennung" / "tabelle-url.md"
BLOCKSATZ_URL = REPO / "tests" / "fixtures" / "trennung" / "urkunde-blocksatz-url.md"


def test_ohne_zellen_gilt_die_grenze_des_fliesstexts(tmp_path, monkeypatch):
    """Erkennt `verify` die gerahmte Zelle nicht, ist der Umbruch nach „/“ dort unsichtbar."""
    import pdfplumber.page

    pdf, form = falzmarke.rendere(ZELLE_URL, tmp_path / "zelle.pdf")
    assert _gescheitert(pdf, form) == {"Netzadressen ungetrennt"}
    monkeypatch.setattr(pdfplumber.page.Page, "find_tables", lambda self, *a, **k: [])
    assert _gescheitert(pdf, form) == set()


def test_urkunde_mit_der_grenze_des_fliesstexts_uebersieht_den_umbruch(tmp_path, monkeypatch):
    pdf, form = falzmarke.rendere(BLOCKSATZ_URL, tmp_path / "urkunde.pdf")
    assert _gescheitert(pdf, form) == {"Netzadressen ungetrennt"}
    monkeypatch.setattr(_netzadressen, "UNTEILBAR_BIS_BLOCKSATZ", _netzadressen.UNTEILBAR_BIS)
    assert _gescheitert(pdf, form) == set()


def test_ohne_spalten_paart_verify_anschrift_und_informationsblock(monkeypatch):
    """Sabotage der Zerlegung: Die ganze Höhe ist wieder eine Zeile."""
    from test_netzadressen import ANSCHRIFT_UND_INFOBLOCK, _Seite

    seite = _Seite(ANSCHRIFT_UND_INFOBLOCK)
    def befunde():
        return [str(t) for z, g in geometrie._textfluesse(seite, 60)
                for t in _netzadressen.getrennt(z, g)]
    assert befunde() == []
    monkeypatch.setattr(geometrie, "_abschnitte", lambda zeile: [sorted(zeile, key=lambda s: s.x0)])
    assert befunde() == ["„Leistungsbeschrei- ⏎ servus@blitzsicht.com“"]


# ── Gesendet-Sperre und Postfach-Entwurf (ADR 0051) ─────────────────────────

def _eigene_mail(tmp_path: Path) -> Path:
    from test_gesendet import MAIL

    quelle = tmp_path / "antwort.md"
    quelle.write_text(MAIL, encoding="utf-8")
    pfad, _ = falzmarke.setze_email(quelle, tmp_path / "antwort", profil_verzeichnis=PROFILE)
    return pfad


def test_ohne_textvergleich_kommt_der_vorfall_durch(tmp_path, monkeypatch):
    """Der Vorfall vom 21.10.2026: anderer Betreff, derselbe Text. Nur der
    Textvergleich sieht ihn — fällt er aus, ist die Nachricht „frei“."""
    from falzmarke import gesendet as _gesendet_modul
    from test_gesendet import THUNDERBIRD_TEXT, ZITAT, _gesendet, _pruefe, _server

    eml_pfad = _eigene_mail(tmp_path)
    _server(monkeypatch, _gesendet(betreff="Re: Sommerfest - Planung und was wir brauchen",
                                   text=THUNDERBIRD_TEXT + ZITAT))
    assert _pruefe(eml_pfad).zustand == "gesendet"
    monkeypatch.setattr(_gesendet_modul, "gleicher_text", lambda eigen, fremd: False)
    assert _pruefe(eml_pfad).zustand == "frei"


def test_ohne_fassungsvergleich_bleibt_ein_umgeschriebener_text_frei(tmp_path, monkeypatch):
    """Trägt die gesendete Mail dieselbe Fassung, sperrt das auch bei anderem
    Text und Betreff — ohne den Vergleich nicht."""
    from falzmarke import eml as _eml
    from falzmarke import gesendet as _gesendet_modul
    from test_gesendet import ANDERER_TEXT, _gesendet, _pruefe, _server

    eml_pfad = _eigene_mail(tmp_path)
    fassung = str(_eml.entwurfsfelder(eml_pfad)["fassung"])
    _server(monkeypatch, _gesendet(betreff="Termin", text=ANDERER_TEXT,
                                   kopf={"X-Falzmarke-Fassung": fassung}))
    assert _pruefe(eml_pfad).zustand == "gesendet"
    echt = _gesendet_modul.vergleiche
    monkeypatch.setattr(_gesendet_modul, "vergleiche",
                        lambda eigen, fremd: echt(eigen._replace(fassung=""), fremd))
    assert _pruefe(eml_pfad).zustand == "frei"


def test_ohne_doppelprobe_entsteht_ein_zweiter_entwurf(tmp_path, monkeypatch):
    from falzmarke import eml as _eml
    from test_oeffnen import THUNDERBIRD_PFAD, Thunderbird
    from test_postfach_entwurf import _server as _entwuerfe
    from test_postfach_entwurf import _vorhanden

    felder = _eml.entwurfsfelder(_eigene_mail(tmp_path))
    felder["betreff"] = "AW: Sommerfest – Programm"
    felder["an"] = ["paula@example.org"]

    def anlegen():
        server = _entwuerfe(monkeypatch, [_vorhanden()])
        lage = _oeffnen.entwurf(felder, plattform="darwin", umgebung={"DISPLAY": ":0"},
                                laufen=Thunderbird(), binaer=lambda: THUNDERBIRD_PFAD)
        return lage, len(server.befehle("APPEND"))

    lage, abgelegt = anlegen()
    assert lage.schon_da and abgelegt == 0
    monkeypatch.setattr(_oeffnen, "_gleicher_entwurf", lambda kopf, felder: False)
    lage, abgelegt = anlegen()
    assert not lage.schon_da and abgelegt == 1


@pytest.fixture
def _email_befehl_441(tmp_path, monkeypatch):
    """`befehl` aus `test_postfach_entwurf.py`; Fixtures eines anderen Moduls
    sind hier nicht zu haben."""
    import functools

    from test_oeffnen import THUNDERBIRD_PFAD, Thunderbird
    from test_postfach_entwurf import MAIL

    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("FALZMARKE_OEFFNEN", raising=False)
    monkeypatch.setenv("DISPLAY", ":0")
    tb = Thunderbird()
    echt = _oeffnen.entwurf
    monkeypatch.setattr(_oeffnen, "entwurf", functools.partial(
        echt, plattform="darwin", umgebung={"DISPLAY": ":0"}, laufen=tb,
        binaer=lambda: THUNDERBIRD_PFAD))
    quelle = tmp_path / "antwort.md"
    quelle.write_text(MAIL, encoding="utf-8")

    def lauf(*extra):
        return falzmarke.main(["email", str(quelle), "--profiles", str(PROFILE), "--oeffnen",
                               *extra])
    lauf.tb, lauf.echt = tb, echt
    return lauf


def test_ohne_sperre_im_entwurf_geht_mit_kein_fenster_compose_auf(_email_befehl_441,
                                                                   monkeypatch, capsys):
    """#441, Abnahme 3: der Rückfall auf `-compose`, wie vor dem Fix."""
    import functools

    from test_oeffnen import THUNDERBIRD_PFAD
    from test_postfach_entwurf import (
        test_kein_fenster_ohne_proxy_oeffnet_nichts_und_endet_mit_exit_3 as probe)

    probe(_email_befehl_441, monkeypatch, capsys)                          # Kontrolle
    # Die Fixture hat `entwurf` schon durch ein `partial` ersetzt; gekippt wird
    # das Original, und es bekommt dieselben Attrappen.
    monkeypatch.setattr(_oeffnen, "entwurf", _email_befehl_441.echt)
    # Mit acht Leerzeichen: Seit dem Nachreview von #491 steht ein zweites
    # `if kein_fenster:` im Rumpf, eine Ebene höher, für den Outlook-Weg.
    kaputt = _zeile_ersetzt(_oeffnen, "entwurf", "        if kein_fenster:", "        if False:")
    monkeypatch.setattr(_oeffnen, "entwurf", functools.partial(
        kaputt, plattform="darwin", umgebung={"DISPLAY": ":0"},
        laufen=_email_befehl_441.tb, binaer=lambda: THUNDERBIRD_PFAD))
    with pytest.raises(AssertionError, match="-compose trotz --kein-fenster"):
        probe(_email_befehl_441, monkeypatch, capsys)


def test_ohne_sperre_im_befehl_geht_mit_kein_fenster_die_datei_auf(_email_befehl_441,
                                                                    monkeypatch, capsys):
    from test_postfach_entwurf import (
        test_kein_fenster_ohne_entwurfsweg_uebergibt_auch_die_datei_nicht as probe)

    probe(_email_befehl_441, monkeypatch, capsys)                          # Kontrolle
    monkeypatch.setattr(falzmarke, "befehl_email", _zeile_ersetzt(
        falzmarke, "befehl_email", "elif args.kein_fenster:", "elif False:"))
    with pytest.raises(AssertionError, match="die Datei ging trotz --kein-fenster auf"):
        probe(_email_befehl_441, monkeypatch, capsys)


@pytest.fixture
def _felder_505(tmp_path):
    """`felder` aus `test_postfach_entwurf.py`, hier nachgebaut wie `_email_befehl_441`."""
    from falzmarke import eml as _eml
    from test_postfach_entwurf import MAIL

    quelle = tmp_path / "antwort.md"
    quelle.write_text(MAIL, encoding="utf-8")
    pfad, _ = falzmarke.setze_email(quelle, tmp_path / "antwort", profil_verzeichnis=PROFILE)
    return _eml.entwurfsfelder(pfad)


import imaplib as _imaplib                                         # noqa: E402
import socket as _socket                                           # noqa: E402


@pytest.mark.parametrize("ziel, anker, ersatz, probe_name, args, meldung", [
    ("entwurf", '"FALZMARKE_ENTWURF=nie ist gesetzt", dauer=DAUERHAFT)',
     '"FALZMARKE_ENTWURF=nie ist gesetzt", dauer=VORUEBERGEHEND)',
     "test_abgeschaltet_ist_dauerhaft", ({"FALZMARKE_ENTWURF": "nie"}, "FALZMARKE_ENTWURF=nie"),
     "FALZMARKE_ENTWURF=nie: 'vorübergehend'"),
    ("_entwurf_postfach", '"gekennzeichnet", DAUERHAFT)', '"gekennzeichnet", VORUEBERGEHEND)',
     "test_ohne_entwuerfe_ordner_ist_dauerhaft", (), "kein Entwürfe-Ordner"),
    ("Postfach._befehl", "voruebergehend=_vergeht(fehler)) from None",
     "voruebergehend=True) from None",
     "test_eine_abgelehnte_anmeldung_ist_dauerhaft", (), "Anmeldung"),
    ("_vergeht", "return fehler.errno == socket.EAI_AGAIN", "return True",
     "test_ein_falsches_ziel_ist_dauerhaft", (_socket.gaierror(_socket.EAI_NONAME, "unbekannt"),),
     "keine Verbindung zu"),
    ("verbinde", "voruebergehend=_vergeht(fehler)) from None", "voruebergehend=True) from None",
     "test_ein_falsches_ziel_ist_dauerhaft", (_imaplib.IMAP4.error("* NO kein IMAP-Dienst"),),
     "keine Verbindung zu"),
], ids=["entwurf-abgeschaltet", "postfach-ohne-ordner", "postfach-anmeldung",
        "unbekannter-host", "begruessung-nein"])
def test_ein_dauerhafter_grund_als_voruebergehend_wird_rot(monkeypatch, _felder_505, ziel, anker,
                                                           ersatz, probe_name, args, meldung):
    """#505, Abnahme 2: Wer eine bleibende Ursache als vorübergehend markiert,
    schickt den Abholer in eine Schleife alle 180 s. Je Sabotage genau die Probe,
    die diese Stelle bewacht, rot mit ihrem eigenen Text."""
    import test_kein_entwurf_ursache as _probe_modul
    from falzmarke import postfach as _postfach

    probe = getattr(_probe_modul, probe_name)
    probe(monkeypatch, _felder_505, *args)                                      # Kontrolle
    if ziel == "Postfach._befehl":
        monkeypatch.setattr(_postfach.Postfach, "_befehl",
                            _zeile_ersetzt(_postfach, ziel, anker, ersatz))
    elif ziel in ("_vergeht", "verbinde"):
        monkeypatch.setattr(_postfach, ziel, _zeile_ersetzt(_postfach, ziel, anker, ersatz))
    else:
        monkeypatch.setattr(_oeffnen, ziel, _zeile_ersetzt(_oeffnen, ziel, anker, ersatz))
    with pytest.raises(AssertionError, match=meldung):
        probe(monkeypatch, _felder_505, *args)


#: Die Zeilen der Positivliste in `_vergeht` (Nachreview von #530) und davor
#: die eine Zeile, die bis dahin dort stand.
_VERGEHT_HEUTE = ("    if isinstance(fehler, (ConnectionError, TimeoutError, imaplib.IMAP4.abort)):\n"
                  "        return True\n"
                  "    return isinstance(fehler, OSError) and fehler.errno in _NETZ_WEG\n")
_VERGEHT_VOR_530 = "    return isinstance(fehler, (OSError, imaplib.IMAP4.abort))\n"


@pytest.mark.parametrize("weg", ["_vergeht", "verbinde"])
def test_jeder_oserror_als_voruebergehend_wird_rot(monkeypatch, _felder_505, weg):
    """Nachreview von #530: `_vergeht` nahm jeden `OSError` außer `gaierror` als
    vorübergehend, auch `PermissionError`. Die Sabotage setzt genau die alte
    Zeile zurück; die Probe am Helfer und die am Verbindungsaufbau werden rot,
    jede mit ihrem eigenen Text."""
    import errno as _errno

    import test_kein_entwurf_ursache as _probe_modul
    from falzmarke import postfach as _postfach

    fehler = PermissionError(_errno.EACCES, "Permission denied")
    if weg == "_vergeht":
        def probe():
            _probe_modul.test_ein_anderer_oserror_bleibt(fehler)
        meldung = re.escape(f"{fehler!r} gilt als vorübergehend")
    else:
        def probe():
            _probe_modul.test_ein_falsches_ziel_ist_dauerhaft(monkeypatch, _felder_505, fehler)
        meldung = rf"\[Errno {_errno.EACCES}\] Permission.*dauer='vorübergehend'"
    probe()                                                                     # Kontrolle
    monkeypatch.setattr(_postfach, "_vergeht", _zeile_ersetzt(
        _postfach, "_vergeht", _VERGEHT_HEUTE, _VERGEHT_VOR_530))
    with pytest.raises(AssertionError, match=meldung):
        probe()


def test_eine_zu_enge_positivliste_wird_rot(monkeypatch):
    """Nachreview von #530, die Gegenrichtung: Fehlt `ConnectionError` in der
    Liste, gälte eine zurückgesetzte Verbindung als bleibend, und der Abholer
    gäbe beim ersten Wackler auf."""
    import errno as _errno

    import test_kein_entwurf_ursache as _probe_modul
    from falzmarke import postfach as _postfach

    fehler = ConnectionResetError(_errno.ECONNRESET, "Connection reset by peer")
    _probe_modul.test_ein_bekannter_netzfehler_vergeht(fehler)                  # Kontrolle
    monkeypatch.setattr(_postfach, "_vergeht", _zeile_ersetzt(
        _postfach, "_vergeht", "(ConnectionError, TimeoutError,", "(TimeoutError,"))
    with pytest.raises(AssertionError, match="ConnectionResetError gilt als bleibend"):
        _probe_modul.test_ein_bekannter_netzfehler_vergeht(fehler)


@pytest.mark.parametrize("weg", ["verbinde", "_vergeht"])
def test_ein_abgelehnter_port_als_dauerhaft_wird_rot(monkeypatch, _felder_505, weg):
    """Nachreview von #569: Der Grenzfall aus #540 (ein vertippter Port, auf dem
    niemand lauscht, gilt als vorübergehend) hatte keine eigene Gegenprobe. Am
    Verbindungsaufbau entscheidet der Zweig `except ConnectionRefusedError` in
    `verbinde`, nach einem abgerissenen Befehl `_vergeht`. Beide Stellen werden
    je für sich auf „bleibt“ gedreht, und die passende Probe wird rot."""
    import errno as _errno

    import test_kein_entwurf_ursache as _probe_modul
    from falzmarke import postfach as _postfach

    fehler = ConnectionRefusedError(_errno.ECONNREFUSED, "Connection refused")
    if weg == "verbinde":
        def probe():
            _probe_modul.test_ein_proxy_der_nicht_antwortet_ist_voruebergehend(
                monkeypatch, _felder_505, fehler)
        alt = '(Verbindung abgelehnt)",\n                             voruebergehend=True)'
        neu = alt.replace("voruebergehend=True", "voruebergehend=False")
        meldung = "dauer='dauerhaft'"
    else:
        # Über den Befehlsweg (`Postfach._befehl`), nicht am Helfer allein: So
        # fiele auch ein `_befehl` auf, der `_vergeht` gar nicht mehr fragt
        # (Review von #572).
        def probe():
            _probe_modul.test_ein_abgerissener_befehl_vergeht_eine_absage_bleibt(fehler, True)
        alt = "    if isinstance(fehler, socket.gaierror):\n"
        neu = "    if isinstance(fehler, ConnectionRefusedError):\n        return False\n" + alt
        meldung = "ConnectionRefusedError nach einem Befehl: voruebergehend=False"
    probe()                                                                     # Kontrolle
    monkeypatch.setattr(_postfach, weg, _zeile_ersetzt(_postfach, weg, alt, neu))
    with pytest.raises(AssertionError, match=meldung):
        probe()


@pytest.mark.parametrize("alt, neu, probe_name, argumente", [
    ("not (port.isascii() and port.isdigit())", "not port.isdigit()",
     "test_nur_ascii_ziffern_sind_ein_port", ("²",)),
    ("if len(ziffern) <= 5 else 0", "if True else 0",
     "test_ein_ueberlanger_port_ist_ein_grund_kein_absturz", ()),
], ids=["nur-ascii", "laengengrenze"])
def test_ein_port_der_int_sprengt_wird_rot(monkeypatch, alt, neu, probe_name, argumente):
    """Review von #572: Ohne ASCII-Prüfung wirft `int('²')`, ohne Längengrenze
    `int` bei 5000 Ziffern einen `ValueError` statt eines Grundes."""
    import test_postfach as _probe_modul
    from falzmarke import postfach as _postfach

    probe = getattr(_probe_modul, probe_name)
    probe(*argumente)                                                           # Kontrolle
    monkeypatch.setattr(_postfach, "ziel", _zeile_ersetzt(_postfach, "ziel", alt, neu))
    with pytest.raises(ValueError):
        probe(*argumente)


def test_ein_port_ohne_bereichspruefung_wird_rot(monkeypatch):
    """Nachreview von #569: Ohne die Prüfung in `ziel` ginge `127.0.0.1:99999`
    durch und endete als scheinbar unbekannter Host."""
    import test_postfach as _probe_modul
    from falzmarke import postfach as _postfach

    probe = _probe_modul.test_ein_port_ausserhalb_des_bereichs_ist_ein_bleibender_grund
    probe("99999")                                                              # Kontrolle
    monkeypatch.setattr(_postfach, "ziel", _zeile_ersetzt(
        _postfach, "ziel", "    if not 1 <= nummer <= 65535:\n", "    if False:\n"))
    with pytest.raises(pytest.fail.Exception, match="DID NOT RAISE"):
        probe("99999")


@pytest.mark.parametrize("ersatz, probe_name, meldung", [
    ("if True:", "test_befehl_mit_abgeschaltetem_entwurf_meldet_dauerhaft",
     "URSACHE  vorübergehend"),
    ("if False:", "test_befehl_ohne_proxy_meldet_vorübergehend", "URSACHE  dauerhaft"),
], ids=["immer-voruebergehend", "nie-voruebergehend"])
def test_die_ursache_zeile_folgt_der_klasse(_email_befehl_441, monkeypatch, capsys, ersatz,
                                            probe_name, meldung):
    """#505: Die Zeile `URSACHE` druckt die Klasse der Lage, nicht einen festen Wert."""
    import test_kein_entwurf_ursache as _probe_modul

    probe = getattr(_probe_modul, probe_name)
    probe(_email_befehl_441, monkeypatch, capsys)                               # Kontrolle
    monkeypatch.setattr(falzmarke, "befehl_email", _zeile_ersetzt(
        falzmarke, "befehl_email", "if lage.dauer == oeffnen_modul.VORUEBERGEHEND:", ersatz))
    with pytest.raises(AssertionError, match=meldung):
        probe(_email_befehl_441, monkeypatch, capsys)


@pytest.mark.parametrize("alt, neu, erwartet", [
    ("import socket\n", "import socket\nsocket.create_connection(('smtp.example.org', 25))\n",
     "socket.create_connection"),
    ("import socket\n", "import socket as _netz\n", "import socket as _netz"),
    ("import socket\n", "from socket import create_connection\nimport socket\n",
     "from socket import create_connection"),
], ids=["verbindung", "alias", "from-import"])
def test_ein_netzweg_aus_socket_in_postfach_wird_rot(alt, neu, erwartet):
    """#505: `postfach` darf `socket` nur für zwei Fehlernamen lesen. Je ein
    Weg daran vorbei, und die Prüfung nennt genau ihn."""
    from falzmarke import postfach as _postfach
    from test_postfach import socket_ausser_fehlerklassen

    quelle = Path(_postfach.__file__).read_text(encoding="utf-8")
    assert socket_ausser_fehlerklassen(quelle) == set()                          # Kontrolle
    assert quelle.count(alt) == 1
    assert erwartet in socket_ausser_fehlerklassen(quelle.replace(alt, neu))


@pytest.fixture
def eigene_441(tmp_path) -> Path:
    return _eigene_mail(tmp_path)


def test_mit_der_alten_frist_wird_die_probe_zur_gesendet_pruefung_rot(eigene_441, monkeypatch):
    """#441, Abnahme 4: `verbinde` wieder mit 5 s Vorgabe."""
    from falzmarke import postfach as _postfach
    from test_gesendet import (
        test_die_gesendet_pruefung_wartet_laenger_als_die_langsamste_anmeldung as probe)

    probe(eigene_441, monkeypatch)                                         # Kontrolle
    monkeypatch.setattr(_postfach, "verbinde", _zeile_ersetzt(
        _postfach, "verbinde", "frist: float = FRIST_S", "frist: float = 5"))
    with pytest.raises(AssertionError, match=r"Frist 5 s, die Anmeldung dauerte 20\.6 s"):
        probe(eigene_441, monkeypatch)


def test_ohne_sperre_im_befehl_geht_ohne_proxy_die_datei_auf(_email_befehl_441,
                                                            monkeypatch, capsys):
    """Die Sperre in `entwurf` allein hielte `-compose` fern, aber die Datei ginge auf."""
    from test_postfach_entwurf import (
        test_kein_fenster_ohne_proxy_oeffnet_nichts_und_endet_mit_exit_3 as probe)

    probe(_email_befehl_441, monkeypatch, capsys)                          # Kontrolle
    monkeypatch.setattr(falzmarke, "befehl_email", _zeile_ersetzt(
        falzmarke, "befehl_email", "elif args.kein_fenster:", "elif False:"))
    with pytest.raises(AssertionError, match="die Datei ging trotz --kein-fenster auf"):
        probe(_email_befehl_441, monkeypatch, capsys)


def test_ohne_sperre_im_outlook_weg_geht_mit_kein_fenster_ein_fenster_auf(monkeypatch):
    """Nachreview von #491, Befund 1: der Outlook-Weg wie vor der Nacharbeit.

    Seit #522 (Punkt 12) sperrt es dreimal: `_kandidaten` lässt mit
    `kein_fenster` kein Programm mit Fenster zu, daraus folgen die Absage vor
    der Suche und der Filter in `entwurfsweg`; danach sperrt `entwurf` noch am
    Programm. Vor der Nacharbeit gab es keine davon, die Sabotage nimmt alle weg."""
    from test_oeffnen import (
        test_outlook_mit_kein_fenster_legt_nichts_an_und_oeffnet_nichts as probe)

    probe()                                                                # Kontrolle
    monkeypatch.setattr(_oeffnen, "_kandidaten", _zeile_ersetzt(
        _oeffnen, "_kandidaten",
        "\n                 and not (kein_fenster and programm.ohne_fenster_absage))", ")"))
    monkeypatch.setattr(_oeffnen, "entwurf", _zeile_ersetzt(
        _oeffnen, "entwurf", "\n    if kein_fenster:\n", "\n    if False:\n"))
    with pytest.raises(AssertionError, match=r"Outlook-Fenster trotz kein_fenster: \['oeffnen'\]"):
        probe()


def test_ohne_abweisung_im_befehl_geht_outlook_mit_kein_fenster_durch(_email_befehl_441,
                                                                     monkeypatch, capsys):
    """Nachreview von #491, Befund 1: Ohne die Abweisung landet die Kombination
    erst in `entwurf` und endet als „kein Entwurf“ statt als Eingabefehler."""
    from test_postfach_entwurf import test_kein_fenster_mit_outlook_wird_abgewiesen as probe

    probe(_email_befehl_441, monkeypatch, capsys)                          # Kontrolle
    monkeypatch.setattr(falzmarke, "befehl_email", _zeile_ersetzt(
        falzmarke, "befehl_email",
        "absage = oeffnen_modul.ohne_fenster_absage(args.programm)", "absage = None"))
    with pytest.raises(AssertionError,
                       match="--programm outlook --kein-fenster nicht abgewiesen"):
        probe(_email_befehl_441, monkeypatch, capsys)


def test_mit_eigener_fassung_im_outlook_weg_laufen_die_absagen_auseinander(monkeypatch):
    """#515, Befund 5: Schreibt `entwurf` seinen Satz wieder selbst, merkt es die
    Probe am Wortlaut, nicht erst ein Leser, der zwei Fassungen vergleicht."""
    from test_oeffnen import (
        test_outlook_mit_kein_fenster_legt_nichts_an_und_oeffnet_nichts as probe)

    probe()                                                                # Kontrolle
    monkeypatch.setattr(_oeffnen, "_ohne_fenster_abgesagt", _zeile_ersetzt(
        _oeffnen, "_ohne_fenster_abgesagt", 'f"{absage}; mit',
        'f"Outlook legt einen Entwurf nur mit Fenster an; mit'))
    with pytest.raises(AssertionError, match="eigene Fassung der Absage: Outlook legt"):
        probe()


def test_mit_eigener_fassung_im_befehl_laufen_die_absagen_auseinander(_email_befehl_441,
                                                                     monkeypatch, capsys):
    """#515, Befund 5, die andere Seite: Der Befehl schreibt seinen Satz wieder selbst."""
    from test_postfach_entwurf import test_kein_fenster_mit_outlook_wird_abgewiesen as probe

    probe(_email_befehl_441, monkeypatch, capsys)                          # Kontrolle
    monkeypatch.setattr(falzmarke, "befehl_email", _zeile_ersetzt(
        falzmarke, "befehl_email", '{womit}: {absage}"',
        '{womit}: Outlook legt einen Entwurf nur mit Fenster an"'))
    with pytest.raises(AssertionError, match="Abweisung mit eigener Fassung"):
        probe(_email_befehl_441, monkeypatch, capsys)


def _tabelle_mit(monkeypatch, alt: str, neu: str) -> None:
    """`Entwurfsprogramm` mit `alt` → `neu` übersetzt, und `ENTWURFSPROGRAMME`
    aus der neuen Klasse gebaut: Die Einträge der Tabelle sind Instanzen der
    alten, eine Eigenschaft daran lässt sich nur so sabotieren."""
    klasse = _zeile_ersetzt(_oeffnen, "Entwurfsprogramm", alt, neu)
    monkeypatch.setattr(_oeffnen, "Entwurfsprogramm", klasse)
    monkeypatch.setattr(_oeffnen, "ENTWURFSPROGRAMME",
                        tuple(klasse(*eintrag) for eintrag in _oeffnen.ENTWURFSPROGRAMME))


@pytest.mark.parametrize("probe_name", [
    "test_kein_fenster_mit_outlook_wird_abgewiesen",
    "test_die_absage_ohne_fenster_kommt_aus_der_programmtabelle",
])
def test_ohne_den_weg_aus_der_tabelle_geht_outlook_ohne_fenster_durch(
        _email_befehl_441, monkeypatch, capsys, probe_name):
    """#515, Befund 5: Fragt die Absage nicht nach dem Weg, gilt jedes Programm
    als fensterlos — der Befehl nimmt Outlook dann an. Seit #522 (Punkt 12)
    steht die Frage an `Entwurfsprogramm`, nicht mehr in `ohne_fenster_absage`."""
    import test_oeffnen
    import test_postfach_entwurf

    if probe_name == "test_kein_fenster_mit_outlook_wird_abgewiesen":
        def probe():
            test_postfach_entwurf.test_kein_fenster_mit_outlook_wird_abgewiesen(
                _email_befehl_441, monkeypatch, capsys)
        meldung = "--programm outlook --kein-fenster nicht abgewiesen"
    else:
        def probe():
            test_oeffnen.test_die_absage_ohne_fenster_kommt_aus_der_programmtabelle(
                "outlook", "Microsoft Outlook legt einen Entwurf nur mit Fenster an")
        meldung = "Absage für 'outlook': None"

    probe()                                                                # Kontrolle
    _tabelle_mit(monkeypatch, 'if self.weg == "compose":', "if True:")
    with pytest.raises(AssertionError, match=meldung):
        probe()


# #522, Punkt 12 (06.11.2026): je Befund der alte Zustand im neuen Code.

def test_ohne_den_filter_weicht_kein_fenster_auf_outlook_aus(monkeypatch):
    """12b: `_kandidaten` lässt mit `kein_fenster` wieder jedes Programm zu."""
    from test_oeffnen import test_kein_fenster_weicht_nicht_auf_ein_programm_mit_fenster_aus as probe

    probe(monkeypatch)                                                     # Kontrolle
    monkeypatch.setattr(_oeffnen, "_kandidaten", _zeile_ersetzt(
        _oeffnen, "_kandidaten",
        "\n                 and not (kein_fenster and programm.ohne_fenster_absage))", ")"))
    with pytest.raises(AssertionError,
                       match="mit kein_fenster nach einem Programm mit Fenster gesucht"):
        probe(monkeypatch)


def test_ohne_den_schalter_im_grund_raet_kein_fenster_zu_outlook():
    """Nachreview von #547: `_nicht_gefunden` wie vor dem Fix, ohne `kein_fenster`.
    Der Grund nennt dann `--programm outlook`, das der Befehl mit `--kein-fenster`
    abweist. Der Zwilling ohne Schalter hält die Probe vorher grün."""
    from test_oeffnen import (
        test_ohne_fenster_und_ohne_thunderbird_verweist_der_grund_nicht_auf_outlook as probe,
    )

    probe()                                                                # Kontrolle
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(_oeffnen, "_nicht_gefunden", _zeile_ersetzt(
            _oeffnen, "_nicht_gefunden",
            "    if kein_fenster:\n"
            '        grund += "; mit --kein-fenster geht nur der Postfach-Entwurf über Thunderbird"\n'
            "    elif wahl is None:\n",
            "    if wahl is None:\n"))
        with pytest.raises(AssertionError, match="mit kein_fenster ein Weg, den der Befehl "
                                                 "abweist: Thunderbird .*; Outlook nur auf "
                                                 "Wahl mit --programm outlook"):
            probe()


def test_ohne_absage_am_eintrag_steht_none_im_grund(monkeypatch):
    """12a: Fehlt die Absage am Eintrag, wie früher bei einer Suche über einen
    leeren `schluessel`, kommt die zweite Sperre in `entwurf` zum Zug und setzt
    „None“ in den Grund."""
    from test_oeffnen import test_ein_eintrag_ohne_schluessel_nennt_seine_absage as probe

    probe(monkeypatch)                                                     # Kontrolle
    _tabelle_mit(monkeypatch, 'return f"{self.name} legt einen Entwurf nur mit Fenster an"',
                 "return None")
    with pytest.raises(AssertionError, match="Absage ohne Schlüssel: None; mit --kein-fenster"):
        probe(monkeypatch)


def test_ohne_eigene_fassung_ohne_programm_nennt_der_befehl_programm_none(_email_befehl_441,
                                                                          monkeypatch, capsys):
    """12c: die Abweisung wie vor #522, mit `--programm {args.programm}` in jedem Fall."""
    from test_postfach_entwurf import (
        test_kein_fenster_ohne_programm_nennt_kein_programm_none as probe)

    probe(_email_befehl_441, monkeypatch, capsys)                          # Kontrolle
    monkeypatch.setattr(falzmarke, "befehl_email", _zeile_ersetzt(
        falzmarke, "befehl_email",
        '" if args.programm\n                     else "mit dem vorgegebenen Programm")', '")'))
    with pytest.raises(AssertionError, match="nennt eine Option, die keiner angab"):
        probe(_email_befehl_441, monkeypatch, capsys)


def test_ohne_pruefung_des_worts_geht_ein_unbekanntes_programm_ohne_fenster():
    """12d: Die Absage prüft das Wort nicht, wie vor #522: Was keinen Eintrag
    trifft, „geht ohne Fenster“, während der Weg einen Fehler wirft."""
    from test_oeffnen import test_ein_unbekanntes_programm_ist_fuer_absage_und_weg_derselbe_fehler as probe

    probe()                                                                # Kontrolle
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(_oeffnen, "ohne_fenster_absage", _zeile_ersetzt(
            _oeffnen, "ohne_fenster_absage", "    alle = _kandidaten(wahl)\n",
            "    if wahl not in {p.schluessel for p in ENTWURFSPROGRAMME} | {None}:\n"
            "        return None\n"
            "    alle = _kandidaten(wahl)\n"))
        with pytest.raises(AssertionError, match="„mail“ gilt der Absage als None"):
            probe()


def test_ohne_sperre_im_befehl_geht_bei_abgeschaltetem_entwurf_die_datei_auf(
        _email_befehl_441, monkeypatch, capsys):
    """Nachreview von #491, Befund 4: `FALZMARKE_ENTWURF=nie` mit `--kein-fenster`."""
    from test_postfach_entwurf import (
        test_kein_fenster_mit_abgeschaltetem_entwurf_endet_mit_exit_3 as probe)

    probe(_email_befehl_441, monkeypatch, capsys)                          # Kontrolle
    monkeypatch.setattr(falzmarke, "befehl_email", _zeile_ersetzt(
        falzmarke, "befehl_email", "elif args.kein_fenster:", "elif False:"))
    with pytest.raises(AssertionError, match="die Datei ging trotz --kein-fenster auf"):
        probe(_email_befehl_441, monkeypatch, capsys)


@pytest.mark.parametrize(("probe_name", "meldung"), [
    ("test_kein_fenster_ohne_oeffnen_legt_den_entwurf_ab",
     "--kein-fenster ohne --oeffnen legte keinen Entwurf ab"),
    ("test_kein_fenster_ohne_oeffnen_und_ohne_proxy_endet_mit_exit_3",
     "Exit 0: --kein-fenster ohne --oeffnen endete ohne KEIN ENTWURF"),
    ("test_kein_fenster_ohne_oeffnen_sperrt_die_schon_gesendete_mit_exit_4",
     "Exit 0: --kein-fenster ohne --oeffnen sperrte die gesendete Nachricht nicht"),
], ids=["abgelegt", "ohne-proxy", "schon-gesendet"])
def test_ohne_kopplung_tut_kein_fenster_ohne_oeffnen_nichts(tmp_path, monkeypatch, capsys,
                                                            probe_name, meldung):
    """#538: die Bedingung vor dem Entwurf wie vor dem Fix, ohne `--kein-fenster`.
    Dann schreibt der Befehl nur die `.eml` und endet mit Exit 0."""
    import test_postfach_entwurf

    probe = getattr(test_postfach_entwurf, probe_name)
    probe(tmp_path, monkeypatch, capsys)                                   # Kontrolle
    monkeypatch.setattr(falzmarke, "befehl_email", _zeile_ersetzt(
        falzmarke, "befehl_email", "or args.ersetzen or args.kein_fenster:",
        "or args.ersetzen:"))
    with pytest.raises(AssertionError, match=re.escape(meldung)):
        probe(tmp_path, monkeypatch, capsys)


def test_ohne_kopplung_in_der_hilfe_schweigt_kein_fenster_dazu(monkeypatch, capsys):
    """#538, Abnahme 3: der Hilfetext von `--kein-fenster` wie vor dem Fix. Der
    Parser entsteht in `main`; bei `--programm` steht der Satz weiter, die Probe
    liest aber nur den Abschnitt von `--kein-fenster`. Je Breite einzeln: Die
    Probe bräche sonst schon an der ersten ab, und ein Abschnitt, der bei einer
    späteren Breite bis `--programm` reicht, bliebe unbemerkt (Review #562)."""
    import test_befehl_email as modul

    probe = modul.test_die_hilfe_nennt_bei_kein_fenster_die_kopplung
    probe(monkeypatch, capsys)                                             # Kontrolle
    monkeypatch.setattr(falzmarke, "main", _zeile_ersetzt(
        falzmarke, "main", '"Nicht mit --programm outlook; schließt --oeffnen ein")',
        '"Nicht mit --programm outlook")'))
    for breite in modul.HILFE_BREITEN:
        monkeypatch.setattr(modul, "HILFE_BREITEN", (breite,))
        with pytest.raises(AssertionError, match=f"COLUMNS={breite}: --kein-fenster nennt "
                                                 "die Kopplung nicht: den Entwurf ablegen"):
            probe(monkeypatch, capsys)


def test_ohne_folgeoption_liest_der_hilfetest_den_satz_von_programm_nicht_mit(monkeypatch,
                                                                              capsys):
    """Nachreview #576, Befund 3: Der Hilfe-Test grenzt `--kein-fenster` an der
    nächsten Option ab, nicht am Ende der Hilfe. Sabotiert: Der Satz fehlt bei
    `--kein-fenster`, und jede Optionszeile danach steht eine Stelle tiefer, als
    wäre sie eine Folgezeile. Mit `\\Z` als Ausweg reichte der Abschnitt dann bis
    zum Schluss und läse den Satz von `--programm` mit: grün ohne Kopplung. Die
    alte Suche läuft deshalb mit und muss genau darauf hereinfallen, sonst prüfte
    die Sabotage nichts."""
    import contextlib
    import io

    import test_befehl_email as modul

    probe = modul.test_die_hilfe_nennt_bei_kein_fenster_die_kopplung
    probe(monkeypatch, capsys)                                             # Kontrolle
    ohne_satz = _zeile_ersetzt(
        falzmarke, "main", '"Nicht mit --programm outlook; schließt --oeffnen ein")',
        '"Nicht mit --programm outlook")')

    def tiefer_eingerueckt(argv):
        puffer = io.StringIO()
        try:
            with contextlib.redirect_stdout(puffer):
                return ohne_satz(argv)
        finally:
            print(re.sub(r"^  (?=-)(?!--kein-fenster\b)", "   ", puffer.getvalue(),
                         flags=re.MULTILINE), end="")
    monkeypatch.setattr(falzmarke, "main", tiefer_eingerueckt)
    for breite in modul.HILFE_BREITEN:
        monkeypatch.setenv("COLUMNS", str(breite))
        with pytest.raises(SystemExit):
            falzmarke.main(["email", "--help"])
        alt = re.search(r"^( +)--kein-fenster\b(.*?)(?=^\1-|\Z)", capsys.readouterr().out,
                        re.DOTALL | re.MULTILINE)
        assert alt and "schließt --oeffnen ein" in " ".join(alt.group(2).split()), \
            f"COLUMNS={breite}: die alte Suche fällt nicht herein, die Sabotage prüft nichts"
        monkeypatch.setattr(modul, "HILFE_BREITEN", (breite,))
        with pytest.raises(AssertionError,
                           match=f"COLUMNS={breite}: keine Folgeoption nach --kein-fenster"):
            probe(monkeypatch, capsys)


@pytest.mark.parametrize(("lage", "ort", "alt", "neu", "meldung"), [
    # Wie ohne Bildschirm: Der Gesendet-Ordner würde auch dann gefragt.
    ("oeffnen-nie", "befehl_email", "ohne_fenster = oeffnen_modul.kein_bildschirm()",
     "ohne_fenster = None", "oeffnen-nie: Exit 4 statt 3"),
    # `FALZMARKE_ENTWURF=nie` als Rechner ohne Bildschirm behandelt.
    ("entwurf-nie", "befehl_email", "ohne_fenster = oeffnen_modul.kein_bildschirm()",
     ("ohne_fenster = oeffnen_modul.kein_bildschirm() or ("
      'os.environ.get("FALZMARKE_ENTWURF") == "nie" and "FALZMARKE_ENTWURF=nie ist gesetzt")'),
     "entwurf-nie: Exit 3 statt 4"),
    # `DISPLAY` auf jeder Plattform verlangt, wie es die Doku bis #576 las.
    ("mac-ohne-display", "kein_bildschirm",
     'if plattform.startswith(("linux", "freebsd")) and not (', "if not (",
     "mac-ohne-display: Exit 3 statt 4"),
], ids=["oeffnen-nie", "entwurf-nie", "mac-ohne-display"])
def test_ohne_trennung_der_lagen_fragt_kein_fenster_den_gesendet_ordner_falsch(
        tmp_path, monkeypatch, capsys, lage, ort, alt, neu, meldung):
    """Nachreview #576, Befund 5: je Lage die eine Stelle, an der sie sich von den
    anderen trennt. Die Sabotage entsteht vor der Kontrolle: Die Probe ersetzt
    `kein_bildschirm` für den Mac, danach fände `_zeile_ersetzt` deren Quelltext."""
    from test_postfach_entwurf import pruefe_lage_ohne_entwurf as probe

    modul = falzmarke if ort == "befehl_email" else _oeffnen
    kaputt = _zeile_ersetzt(modul, ort, alt, neu)
    probe(tmp_path, monkeypatch, capsys, lage)                             # Kontrolle
    monkeypatch.setattr(modul, ort, kaputt)
    with pytest.raises(AssertionError, match=re.escape(meldung)):
        probe(tmp_path, monkeypatch, capsys, lage)


def test_ohne_signaturklasse_findet_die_pruefung_keine_signatur(tmp_path, monkeypatch):
    """Sabotage: Die Hülle der Signatur trägt eine andere Klasse. Dann findet
    die Prüfung aus `test_moz_signatur.py` kein Element mehr — und Thunderbirds
    Anhang-Erinnerung läse den Hinweis der Signatur wieder mit."""
    from conftest import EMAIL_BEISPIELE
    from falzmarke import eml as _eml
    from test_moz_signatur import _teile, signaturteile

    quelle = next(q for q in EMAIL_BEISPIELE if q.stem == "email-angebot")

    def elemente() -> int:
        pfad, _ = falzmarke.setze_email(quelle, tmp_path / f"a-{_eml.KLASSE_SIGNATUR}")
        return signaturteile(_teile(pfad)[1]).elemente

    assert elemente() == 1
    monkeypatch.setattr(_eml, "KLASSE_SIGNATUR", "fm-sabotage")
    assert elemente() == 0


def test_ohne_den_absenderfilter_sperrt_die_eingegangene_mail(tmp_path, monkeypatch):
    """#434, Abnahme 6: Die Mail des Kunden mit Paula in Cc und demselben Betreffkern
    gab `GEÄNDERTE FASSUNG`. Mit dem Filter ist sie frei, ohne ihn wieder nicht —
    und die eigene Mail (Kontrolle) sperrt vorher wie nachher."""
    from falzmarke import gesendet as _gesendet_modul
    from test_gesendet import _eingegangen, _gesendet, _profil, _pruefe, _server

    eml_pfad = _eigene_mail(tmp_path)
    ordner = _profil(tmp_path)

    def urteile() -> tuple[str, str]:
        _server(monkeypatch, _eingegangen())
        eingegangen = _pruefe(eml_pfad, thunderbird_ordner=ordner).zustand
        _server(monkeypatch, _gesendet())
        return eingegangen, _pruefe(eml_pfad, thunderbird_ordner=ordner).zustand

    assert urteile() == ("frei", "gesendet")
    monkeypatch.setattr(_gesendet_modul, "pruefe", _zeile_ersetzt(
        _gesendet_modul, "pruefe",
        "            if fremder_absender(kopf, eigene):\n", "            if False:\n"))
    assert urteile() == ("geaendert", "gesendet")


def test_ohne_den_absenderfilter_im_abgleich_ist_die_eingegangene_mail_schon_raus(monkeypatch,
                                                                                tmp_path):
    """Dieselbe Zusage für `status`: Der Filter steht in `abgleich`, vor `treffer`."""
    from falzmarke import entwurfsbuch as _buch
    from test_entwurfsbuch import (_eingegangen, _einziger, _mail, _postfach,
                                   _profil_des_kontos, _stand)

    _profil_des_kontos(monkeypatch, tmp_path)
    _postfach(monkeypatch, entwuerfe=[_mail()], gesendet=[_eingegangen()])
    assert _einziger(_stand()).art == "wartet"
    monkeypatch.setattr(_buch, "abgleich", _zeile_ersetzt(
        _buch, "abgleich",
        "            raus = behalten\n",
        "            raus = list(raus)\n"))
    assert _einziger(_stand()).art == "schon_raus"


def test_ohne_die_eigene_adresse_laesst_die_sperre_die_zweite_sendung_durch(tmp_path,
                                                                           monkeypatch):
    """#506, Befund 1: Das Profil nennt den Absender nicht. Mit der Ergänzung sperrt die
    eigene Mail, ohne sie gilt sie als fremd, und die Sperre meldet frei."""
    from falzmarke import gesendet as _gesendet_modul
    from test_gesendet import _gesendet, _profil_ohne_absender, _pruefe, _server

    eml_pfad = _eigene_mail(tmp_path)
    ordner = _profil_ohne_absender(tmp_path)
    _server(monkeypatch, _gesendet())
    assert _pruefe(eml_pfad, thunderbird_ordner=ordner).zustand == "gesendet"
    monkeypatch.setattr(_gesendet_modul, "pruefe", _zeile_ersetzt(
        _gesendet_modul, "pruefe",
        "        eigene = eigene | {absender.strip().lower()}\n", "        eigene = eigene\n"))
    assert _pruefe(eml_pfad, thunderbird_ordner=ordner).zustand == "frei"


def test_ohne_die_eigene_adresse_ist_die_eigene_sendung_im_abgleich_fremd(monkeypatch, tmp_path):
    """#506, Befund 2, dieselbe Zusage für `status`."""
    from falzmarke import entwurfsbuch as _buch
    from test_entwurfsbuch import (VON, _eingegangen, _einziger, _mail, _postfach,
                                   _profil_des_kontos, _stand)

    _profil_des_kontos(monkeypatch, tmp_path, mit_konto=False)
    _postfach(monkeypatch, entwuerfe=[_mail()], gesendet=[_eingegangen(von=VON)])
    assert _einziger(_stand()).art == "schon_raus"
    monkeypatch.setattr(_buch, "abgleich", _zeile_ersetzt(
        _buch, "abgleich",
        "                eigene = eigene | {adresse}\n",
        "                eigene = eigene\n"))
    assert _einziger(_stand()).art == "wartet"


def test_nach_dem_ersten_autor_gezaehlt_nennt_der_hinweis_die_eigene_mail(monkeypatch):
    """#506, Befund 7: der Ersatzhinweis vor #506, nachgebaut. Ohne Profil steht der
    Kunde vorn und die eigene Adresse dahinter: vorher kein Hinweis, mit der alten
    Zählung einer."""
    from falzmarke import entwurfsbuch as _buch
    from test_entwurfsbuch import KUNDE, VON, _eingegangen, _mail, _postfach, _stand

    def hinweise():
        _postfach(monkeypatch, entwuerfe=[_mail()],
                  gesendet=[_eingegangen(von=f"{KUNDE}, {VON}")])
        return [h for h in _stand().hinweise if h.startswith("Identitäten des Profils")]

    assert hinweise() == []
    monkeypatch.setattr(_buch, "abgleich", _zeile_ersetzt(
        _buch, "abgleich",
        "                andere = sum(gesendet.fremder_absender(k, frozenset({adresse})) "
        "for k in raus)\n",
        "                andere = sum(bool(k.von) and k.von != adresse for k in raus)\n"))
    assert len(hinweise()) == 1


def test_nur_der_erste_autor_laesst_die_zweite_sendung_durch(tmp_path, monkeypatch):
    """#506, Befund 4: `From` nennt den Kunden zuerst, die eigene Adresse danach. Mit allen
    Autoren sperrt die Mail, mit dem ersten allein (der Stand vor #506) gilt sie als fremd."""
    from falzmarke import gesendet as _gesendet_modul
    from test_gesendet import KUNDE, _gesendet, _profil, _pruefe, _server

    eml_pfad = _eigene_mail(tmp_path)
    ordner = _profil(tmp_path)
    _server(monkeypatch, _gesendet(von=f"{KUNDE}, muster@example.de"))
    assert _pruefe(eml_pfad, thunderbird_ordner=ordner).zustand == "gesendet"
    monkeypatch.setattr(_gesendet_modul, "fremder_absender", _zeile_ersetzt(
        _gesendet_modul, "fremder_absender",
        "    adressen = kopf.absender or ((kopf.von,) if kopf.von else ())\n",
        "    adressen = (kopf.von,) if kopf.von else ()\n"))
    assert _pruefe(eml_pfad, thunderbird_ordner=ordner).zustand == "frei"


def test_in_der_schleife_gezaehlt_fehlt_die_fremde_hinter_dem_treffer(tmp_path, monkeypatch):
    """#506, Befund 5: die Zählung vor #506, nachgebaut. Die ältere fremde Mail liegt hinter
    dem Treffer, die Schleife endet vorher, und die Zahl fällt von 1 auf 0."""
    from falzmarke import gesendet as _gesendet_modul
    from test_gesendet import _eingegangen, _gesendet, _profil, _pruefe, _server

    eml_pfad = _eigene_mail(tmp_path)
    ordner = _profil(tmp_path)
    _server(monkeypatch, _eingegangen(vor=timedelta(minutes=30)), _gesendet())
    assert _pruefe(eml_pfad, thunderbird_ordner=ordner).fremde == 1
    monkeypatch.setattr(_gesendet_modul, "pruefe", _zeile_ersetzt(
        _gesendet_modul, "pruefe",
        "        fremde = sum(fremder_absender(kopf, eigene) for kopf in koepfe)\n"
        "        for kopf in sorted(koepfe, key=lambda k: k.datum or jetzt, reverse=True):\n"
        "            if fremder_absender(kopf, eigene):\n"
        "                continue\n",
        "        fremde = 0\n"
        "        for kopf in sorted(koepfe, key=lambda k: k.datum or jetzt, reverse=True):\n"
        "            if fremder_absender(kopf, eigene):\n"
        "                fremde += 1\n"
        "                continue\n"))
    befund = _pruefe(eml_pfad, thunderbird_ordner=ordner)
    assert (befund.zustand, befund.fremde) == ("gesendet", 0)


# ── Die Frist gilt für die ganze Sitzung (Review von #570, ADR 0051) ───────

@pytest.mark.parametrize("verhalten", ["troepfelt", "langsam"])
def test_ohne_frist_am_socket_haelt_ein_haengender_server_die_sitzung(schein, monkeypatch,
                                                                      verhalten):
    """Der alte Stand genau nachgebaut: `imaplib` baut seinen Socket selbst, ohne
    Hülle. Dann zählt das Zeitlimit wieder je Empfang, und die Sitzung läuft über
    die Frist. Die Kontrolle davor zeigt dieselbe Probe mit Hülle unter der Frist."""
    import imaplib

    from falzmarke import imap_frist
    from test_postfach_frist import FRIST, SPIEL, _dauer

    dauer, _ = _dauer(schein(verhalten), mit_list=False)
    assert dauer < FRIST + SPIEL, f"Kontrolle: {dauer:.2f} s"
    monkeypatch.setattr(imap_frist.ImapMitFrist, "_create_socket",
                        imaplib.IMAP4._create_socket)
    dauer, _ = _dauer(schein(verhalten), mit_list=False)
    assert dauer >= FRIST + SPIEL, f"{verhalten} ohne Hülle: {dauer:.2f} s, die Probe trennt nicht"


def test_ohne_nachgestellte_restzeit_wartet_der_letzte_empfang_die_volle_frist(schein,
                                                                              monkeypatch):
    """Eine Zeile gekippt: Die Hülle prüft nur noch, ob die Frist um ist, und legt
    die Restzeit nicht mehr auf den Socket. Der Gruß kommt nach 0,6 s, danach
    wartet `CAPABILITY` wieder die volle Frist. Rot wird nur dieser Fall; die
    übrigen enden auch so knapp über der Frist (nachgerechnet am 06.11.2026)."""
    from falzmarke import imap_frist
    from test_postfach_frist import FRIST, SPIEL, _dauer

    dauer, _ = _dauer(schein("gruss_dann_stille"), mit_list=False)
    assert dauer < FRIST + SPIEL, f"Kontrolle: {dauer:.2f} s"
    monkeypatch.setattr(imap_frist._SocketMitFrist, "_restzeit", _zeile_ersetzt(
        imap_frist, "_SocketMitFrist._restzeit", "self._sock.settimeout(rest)", "pass"))
    dauer, _ = _dauer(schein("gruss_dann_stille"), mit_list=False)
    assert dauer >= FRIST + SPIEL, f"ohne Restzeit: {dauer:.2f} s, die Probe trennt nicht"


@pytest.mark.skipif(sys.version_info >= (3, 14),
                    reason="ab 3.14 ruft imaplib makefile weiter auf, liest aber über "
                           "sock.recv; ein durchgereichtes makefile ändert am Lesen nichts")
def test_ohne_eigenes_makefile_liest_imaplib_an_der_huelle_vorbei(schein, monkeypatch):
    """Bis 3.13 liest `imaplib` über `sock.makefile`. Reicht die Hülle das an den
    echten Socket durch, gilt dort wieder das Zeitlimit je Empfang. Ab 3.14 ruft
    `IMAP4.open` `makefile` zwar weiter auf, legt die Datei aber nur in `_file`
    ab (für die Eigenschaft `file` und für `shutdown`) und liest über
    `sock.recv`. Dort trennt diese Probe nicht, die Restzeit am Empfang deckt
    `test_ohne_nachgestellte_restzeit_wartet_der_letzte_empfang_die_volle_frist`."""
    from falzmarke import imap_frist
    from test_postfach_frist import FRIST, SPIEL, _dauer

    dauer, _ = _dauer(schein("troepfelt"), mit_list=False)
    assert dauer < FRIST + SPIEL, f"Kontrolle: {dauer:.2f} s"
    monkeypatch.setattr(imap_frist._SocketMitFrist, "makefile",
                        lambda self, mode="rb": self._sock.makefile(mode))
    dauer, _ = _dauer(schein("troepfelt"), mit_list=False)
    assert dauer >= FRIST + SPIEL, f"makefile vorbei: {dauer:.2f} s, die Probe trennt nicht"


def test_ohne_schliessen_nach_gescheitertem_logout_bleibt_die_verbindung_offen(schein,
                                                                              monkeypatch):
    """Nachreview von #574, Befund 1: Eine Zeile gekippt, und `abmelden` schließt
    nach einem gescheiterten `logout` nicht mehr. Das ist der Stand von #574:
    Nach abgelaufener Frist blieb der innere Socket offen. Die Kontrolle davor ist
    dieselbe Probe mit dem heutigen Code."""
    from falzmarke import postfach
    from test_postfach_frist import (
        test_nach_abgelaufener_frist_schliesst_das_abmelden_die_verbindung as probe,
    )

    probe(schein)                                                               # Kontrolle
    monkeypatch.setattr(postfach.Postfach, "abmelden", _zeile_ersetzt(
        postfach, "Postfach.abmelden", "self._v.shutdown()", "pass"))
    with pytest.raises(AssertionError, match="nach dem Abmelden ist die Verbindung noch offen"):
        probe(schein)


@pytest.mark.parametrize("alt, neu, erwartet", [
    # Jede Sabotage fügt hinzu und nimmt nichts weg: Die Anker der Prüfung
    # (`_create_socket`, `sendall`, `SocketIO`) bleiben stehen, sonst schlüge
    # einer von ihnen an statt der Regel, um die es geht.
    ("sock = super()._create_socket(timeout)\n",
     "sock = super()._create_socket(timeout)\n        self.store('1:*', '+FLAGS', 'x')\n",
     "'store'"),
    ("sock = super()._create_socket(timeout)\n",
     ("sock = super()._create_socket(timeout)\n"
      "        socket.create_connection(('smtp.example.org', 25))\n"),
     "'socket.create_connection'"),
    ("sock = super()._create_socket(timeout)\n",
     "sock = super()._create_socket(timeout)\n        socket.socket()\n",
     "'socket.socket(…)'"),
    ("return self._sock.sendall(*args)",
     "self._sock.connect(('smtp.example.org', 25))\n        return self._sock.sendall(*args)",
     "'.connect'"),
    ("sock = super()._create_socket(timeout)\n",
     "sock = super()._create_socket(timeout)\n        socket.create_server(('127.0.0.1', 0))\n",
     "'socket.create_server'"),
    ("import socket\n", "import socket as _netz\n", "'import socket as _netz'"),
    ("import socket\n", "from socket import create_connection\nimport socket\n",
     "'from socket import create_connection'"),
], ids=["aendernder-befehl", "verbindung", "eigener-socket", "connect", "create-server",
        "alias", "from-import"])
def test_ein_netzweg_oder_aendernder_befehl_in_der_socket_huelle_wird_rot(tmp_path, monkeypatch,
                                                                         alt, neu, erwartet):
    """Nachreview von #574, Befund 2: Die Prüfung liest `imap_frist`, nicht nur
    `postfach`. Sabotiert wird eine Kopie von `imap_frist.py`, auf die
    `imap_frist.__file__` zeigt. Läse die Prüfung ein anderes Objekt, bliebe sie
    grün. Die Kontrolle davor läuft gegen die echte Datei."""
    import re

    from falzmarke import imap_frist
    from test_postfach import (
        test_die_socket_huelle_kennt_keinen_aendernden_befehl_und_keinen_netzweg as probe,
    )

    probe()                                                                     # Kontrolle
    quelle = Path(imap_frist.__file__).read_text(encoding="utf-8")
    assert quelle.count(alt) == 1, f"Anker nicht genau einmal: {alt!r}"
    kopie = tmp_path / "imap_frist.py"
    kopie.write_text(quelle.replace(alt, neu), encoding="utf-8")
    monkeypatch.setattr(imap_frist, "__file__", str(kopie))
    with pytest.raises(AssertionError, match=re.escape(erwartet)):
        probe()


# ── Die Ablage je Konto (#431, ADR 0061) ───────────────────────────────────
#
# `tests/test_ablage.py` hält fest, was der Befehl tut. Hier steht die Frage,
# die nur hier gestellt wird: Können die drei Zusagen überhaupt rot werden —
# die Zielsperre, der fehlende Fallback und die Positivliste im Profil?
#
# Die vierte Zusage, „ohne --machen wird nichts bewegt“, braucht hier keine
# Sabotage: `test_der_trockenlauf_haelt_auch_an_einer_sperrenden_attrappe`
# läuft gegen eine Attrappe, die jedes Verschieben verbietet, und wird von
# selbst rot, sobald der Trockenlauf fällt.

def _ablage_sitzung(monkeypatch, sonder):
    from falzmarke import postfach

    from imap_attrappe import ImapAttrappe

    attrappe = ImapAttrappe({"INBOX": [], "Gesendete Elemente": []}, sonder=sonder)
    monkeypatch.setattr(postfach, "IMAP_KLASSE", attrappe)
    return postfach.verbinde("joe@example.org", umgebung={}, frist=30)


SONDER = {"INBOX": "", "Gesendete Elemente": "\\Sent", "Archiv": ""}


def test_die_zielsperre_faellt_unsabotiert_auf():
    """Kontrollprobe. Ohne sie belegte die Sabotage unten nichts: Ein Grund,
    der nie kam, kann durch keine Sabotage verschwinden."""
    from falzmarke import ablage as _ablage

    with pytest.MonkeyPatch.context() as mp:
        with _ablage_sitzung(mp, SONDER) as sitzung:
            ordner, grund = _ablage.ablageordner(sitzung, "Gesendete Elemente")
    assert ordner is None and "\\sent" in grund


def test_eine_geleerte_zielsperre_nimmt_den_gesendet_ordner_an(monkeypatch):
    """Sabotage an genau einer Stelle: Ohne die Kennzeichen in
    `VERBOTENE_ZIELE` wird der Gesendet-Ordner zur Ablage — genau das, was die
    Abnahme von #431 ausschließt.

    Der Fallback-Grund bleibt davon unberührt: Er misst etwas anderes, und das
    soll die Probe zeigen — die Sabotage trifft die Zielliste, nicht pauschal
    die ganze Funktion.
    """
    from falzmarke import ablage as _ablage

    assert set(_ablage.VERBOTENE_ZIELE) == {"\\sent", "\\drafts", "\\trash", "\\junk"}, \
        "Ankerwert veraltet: VERBOTENE_ZIELE hat andere Kennzeichen"
    monkeypatch.setattr(_ablage, "VERBOTENE_ZIELE", {})
    with _ablage_sitzung(monkeypatch, SONDER) as sitzung:
        ordner, grund = _ablage.ablageordner(sitzung, "Gesendete Elemente")
        ohne_wunsch = _ablage.ablageordner(sitzung, None)
    assert ordner == "Gesendete Elemente" and grund is None, \
        "die Kennzeichenliste ist nicht die Stelle, an der das Ziel abgelehnt wird"
    assert ohne_wunsch[0] is None and "`\\Archive`" in ohne_wunsch[1], \
        "die Sabotage hat mehr getroffen als die Zielliste"


def test_der_fehlende_archive_ordner_faellt_unsabotiert_auf():
    from falzmarke import ablage as _ablage

    with pytest.MonkeyPatch.context() as mp:
        with _ablage_sitzung(mp, SONDER) as sitzung:
            ordner, grund = _ablage.ablageordner(sitzung, None)
    assert ordner is None and "`\\Archive`" in grund


def test_ein_erfundener_archive_ordner_laesst_den_grund_verschwinden(monkeypatch):
    """Sabotage am Kennzeichen, nicht am Code: Liefert der Server plötzlich
    einen `\\Archive`-Ordner, wandert ohne Profilzeile etwas.

    Das ist die Probe auf den ausführenden Pfad — sie zeigt, dass der Grund
    wirklich am Kennzeichen des Servers hängt und nicht an einer Abfrage, die
    ohnehin immer zutrifft.
    """
    from falzmarke import ablage as _ablage

    mit_archiv = dict(SONDER, Archiv="\\Archive")
    with _ablage_sitzung(monkeypatch, mit_archiv) as sitzung:
        ordner, grund = _ablage.ablageordner(sitzung, None)
        gesperrt = _ablage.ablageordner(sitzung, "Gesendete Elemente")
    assert (ordner, grund) == ("Archiv", None)
    assert gesperrt[0] is None, "die Sabotage hat mehr getroffen als den Fallback"


def test_das_profilfeld_ablage_faellt_unsabotiert_auf():
    """Kontrollprobe zur Positivliste: Ein gepflegtes `ablage:` ist bekannt."""
    regeln = _email_profilregeln({"absender": "joe@example.org", "ablage": "Archiv"})
    assert "email.profil" not in regeln


def test_eine_feldliste_ohne_ablage_meldet_das_gepflegte_feld_als_unbekannt(monkeypatch):
    """Sabotage an genau einer Stelle: Fehlt `ablage` in der Positivliste,
    meldet `lint` ein korrekt gepflegtes Profil.

    Die Prüfung auf die fehlende Absenderadresse bleibt stehen — die Sabotage
    trifft die Feldliste und nicht die ganze Funktion.
    """
    _sabotiere_konstante(monkeypatch, "PROFIL_EMAIL_FELDER",
                         getattr(_lint, "PROFIL_EMAIL_FELDER"),
                         getattr(_lint, "PROFIL_EMAIL_FELDER") - {"ablage"})
    regeln = _email_profilregeln({"absender": "joe@example.org", "ablage": "Archiv"})
    assert "email.profil" in regeln, \
        "die Positivliste ist nicht die Stelle, an der ein Feld als bekannt gilt"
    assert "email.absender" not in regeln, \
        "die Sabotage hat mehr getroffen als die Feldliste"
    assert "email.absender" in _email_profilregeln({"ablage": "Archiv"}), \
        "die Sabotage hat die übrigen Prüfungen abgeschaltet"


def _email_profilregeln(abschnitt: dict) -> set:
    bericht = _lint.Bericht()
    _lint.pruefe_email_profil({"email": abschnitt}, bericht)
    return {befund.regel for befund in bericht.befunde}


# ── Das Konto hinter einem offenen Fenster (#410) ───────────────────────────
#
# Vier Sabotagen, jede an genau einer Stelle, jede mit einer eigenen Wirkung.
# Sie liegen hier und nicht nur in `test_entwurfsbuch.py`, weil die Zusagen
# **Abwesenheiten** sind: „das Konto wird nicht geraten“ und „es wird nicht das
# falsche Profil gelesen“. Eine Probe über eine Abwesenheit bleibt grün, solange
# der geprüfte Weg gar nicht beschritten wird — erst der Zwilling mit anderem
# Ergebnis zeigt, dass gemessen wurde.

_VON_410 = "order@example.de"
_URI_FREMD = "imap-message://m0123456@imap.example.de/Entw&APw-rfe#4711"
_URI_EIGEN = "imap-message://order%40example.de@127.0.0.1/Entw&APw-rfe#4711"


def _fenster_410(uri: str, **felder) -> dict:
    return {"titel": "Verfassen", "betreff": "Auftrag", "draft_id": uri, **felder}


def _uids_410(monkeypatch, *fenster) -> dict:
    """`_offene_uids` über die Attrappe — der Weg, den `status` wirklich geht."""
    from bruecke_attrappe import BrueckenAttrappe

    from falzmarke import bruecke as _bruecke
    from falzmarke import entwurfsbuch as _buch

    monkeypatch.setattr(_bruecke, "VERBINDEN",
                        BrueckenAttrappe({"ok": True, "fenster": list(fenster)}))
    uids, grund = _buch._offene_uids(_VON_410, {})
    assert not grund, grund
    return uids


def test_die_zuordnung_ist_unsabotiert_gruen(monkeypatch):
    """Kontrollprobe: Beide Fälle fallen ohne Sabotage richtig aus.

    Ohne sie wäre an den folgenden Tests nicht zu sehen, ob die Sabotage wirkt
    oder ob der Aufbau von sich aus das erwartete Ergebnis liefert.

    Seit #442 (N3) schließt eine fremde Meldung nicht mehr aus: Auch das
    zweite Fenster bekommt die UID, aber nur über die UID (`nur_uid`).
    """
    from falzmarke import entwurfsbuch as _buch

    eigen = _uids_410(monkeypatch, _fenster_410(_URI_FREMD, identitaet=_VON_410))
    fremd = _uids_410(monkeypatch, _fenster_410(_URI_EIGEN, identitaet="wer@example.net"))
    assert set(eigen) == {"4711"} and set(fremd) == {"4711"}
    assert not _buch.nur_uid(eigen["4711"], _VON_410) and _buch.nur_uid(fremd["4711"], _VON_410)


def test_eine_geratene_zuordnung_verliert_das_konto_mit_fremdem_login(monkeypatch):
    """Sabotage: wieder `adresse in ziel`, die Teilkette der IMAP-URI.

    Genau der Zustand vor #410: Der Login `m0123456` verliert sein Fenster.
    Die Gegenrichtung (ein fremd gemeldetes Fenster bekommt die UID) trennt
    seit #442 (N3) nicht mehr, denn das tut es jetzt auch unsabotiert.
    """
    from falzmarke import entwurfsbuch as _buch

    def geraten(fenster, adresse, kontoadressen=None):
        # `unquote` gehört dazu: Die URI trägt die Adresse prozentcodiert
        # (`order%40example.de`), und ohne das Entpacken träfe die Teilkette
        # auch im alten Code nie — der Nachbau wäre dann milder als das
        # Original und bewiese nichts.
        from urllib.parse import unquote

        aus = {}
        for eintrag in fenster:
            ziel = unquote(str(eintrag.get("draft_id") or "").split("?")[0]).lower()
            treffer = _buch.UID_AUS_URI.search(ziel)
            if treffer and adresse in ziel:
                aus[treffer.group(1)] = eintrag
        return aus

    monkeypatch.setattr(_buch, "fenster_des_kontos", geraten)
    assert _uids_410(monkeypatch, _fenster_410(_URI_FREMD, identitaet=_VON_410)) == {}


def _fremd_und_eigen_410():
    """Zwei Fenster derselben UID, das fremd gemeldete zuerst in der Liste."""
    return (_fenster_410(_URI_EIGEN, identitaet="wer@example.net", betreff="fremd"),
            _fenster_410(_URI_EIGEN, identitaet=_VON_410, betreff="eigen"))


def test_ohne_pruefung_der_identitaet_gewinnt_das_fremde_fenster(monkeypatch):
    """Sabotage: nur die UID, die gemeldete Identität wird nicht gelesen.

    Die Gegenrichtung zur vorigen Sabotage, und sie trennt den Fix von seiner
    Lockerung: Dass weder die Adresse noch eine fremde Meldung **ausschließt**,
    darf nicht heißen, dass die eigene Meldung nicht mehr **vorgeht**.
    """
    from falzmarke import entwurfsbuch as _buch

    def nur_uid(fenster, adresse, kontoadressen=None):
        aus = {}
        for eintrag in fenster:
            treffer = _buch.UID_AUS_URI.search(str(eintrag.get("draft_id") or ""))
            if treffer:
                aus.setdefault(treffer.group(1), eintrag)
        return aus

    assert _uids_410(monkeypatch, *_fremd_und_eigen_410())["4711"]["betreff"] == "eigen", \
        "Kontrollprobe: unsabotiert geht die eigene Meldung vor"
    monkeypatch.setattr(_buch, "fenster_des_kontos", nur_uid)
    assert _uids_410(monkeypatch, *_fremd_und_eigen_410())["4711"]["betreff"] == "fremd"


# ── Eine Zeile sabotiert, nicht die ganze Funktion (#442, N5) ───────────────
#
# Die beiden Sabotagen zu #410 oben ersetzen `fenster_des_kontos` als Ganzes.
# Das belegt, dass `_offene_uids` über das Modulattribut ruft und dass die
# Proben einen Nachbau des alten Codes erkennen — nicht, dass sie anschlagen,
# wenn im heutigen Code eine einzelne Zeile kippt. Dafür wird die Funktion
# hier aus ihrem eigenen Quelltext neu übersetzt, mit genau einer Änderung.

def test_unter_sabotage_zeigt_der_traceback_auf_die_gekippte_zeile():
    """#468: Bis dahin übersetzte der Helfer ab Zeile 1, und ein Fehler unter
    Sabotage stand im Traceback beim Modulkopf von `entwurfsbuch.py`."""
    import inspect
    import traceback

    from falzmarke import entwurfsbuch as _buch

    alt = "    if fenster is None:\n        return False\n"
    zeilen, erste = inspect.getsourcelines(_buch.nur_uid)
    soll = erste + "".join(zeilen)[:"".join(zeilen).index(alt)].count("\n")
    kaputt = _zeile_ersetzt(_buch, "nur_uid", alt, "    raise RuntimeError('gekippt')\n")
    with pytest.raises(RuntimeError) as fehler:
        kaputt(None, _VON_410)
    rahmen = traceback.extract_tb(fehler.tb)[-1]
    assert (Path(rahmen.filename).name, rahmen.lineno) == ("entwurfsbuch.py", soll)


def test_kippt_der_rang_der_fremden_meldung_geht_sie_vor_keiner(monkeypatch):
    """#442 (N3): Eine fremde Meldung steht hinter einem Fenster ohne Meldung."""
    from falzmarke import entwurfsbuch as _buch

    fenster = (_fenster_410(_URI_FREMD, identitaet="wer@example.net", betreff="fremd"),
               _fenster_410(_URI_FREMD, betreff="ohne"))
    assert _uids_410(monkeypatch, *fenster)["4711"]["betreff"] == "ohne", \
        "Kontrollprobe: unsabotiert geht das Fenster ohne Meldung vor"
    monkeypatch.setattr(_buch, "fenster_des_kontos", _zeile_ersetzt(
        _buch, "fenster_des_kontos",
        "rang = 0 if gemeldet == eigen else 1 if not gemeldet else 2",
        "rang = 0 if gemeldet == eigen else 1"))
    assert _uids_410(monkeypatch, *fenster)["4711"]["betreff"] == "fremd"


def test_kippt_der_vergleich_in_nur_uid_gilt_der_alias_als_sicher_zugeordnet(monkeypatch):
    """#442 (N3): `nur_uid` las bis 0.11.0 nur, ob eine Meldung da ist."""
    from falzmarke import entwurfsbuch as _buch

    fremd = _fenster_410(_URI_EIGEN, identitaet="wer@example.net")
    assert _buch.nur_uid(fremd, _VON_410), "Kontrollprobe: unsabotiert nur über die UID"
    monkeypatch.setattr(_buch, "nur_uid", _zeile_ersetzt(
        _buch, "nur_uid",
        'return str(fenster.get("identitaet") or "").strip().lower() != adresse.strip().lower()',
        'return not str(fenster.get("identitaet") or "").strip()'))
    assert not _buch.nur_uid(fremd, _VON_410)


# #466: Die Identitäten des Kontos aus dem Profil trennen Alias und fremdes
# Konto. Die Probe der einen Seite bleibt unter der Sabotage der anderen grün.

@pytest.mark.parametrize("identitaet", ["andere@example.org", "fremd@example.net"],
                         ids=["anderes-konto", "in-keinem-konto"])
def test_ohne_kontoadressen_haelt_ein_fremdes_fenster_wieder_offen(monkeypatch, tmp_path,
                                                                   identitaet):
    from falzmarke import entwurfsbuch as _buch
    from test_entwurfsbuch import (
        test_mit_profil_faellt_ein_fremdes_fenster_derselben_uid_heraus as probe,
        test_mit_profil_ist_der_alias_sicher_zugeordnet as alias)

    probe(monkeypatch, tmp_path / "k", identitaet)                         # Kontrolle
    monkeypatch.setattr(_buch, "_offene_uids", _zeile_ersetzt(
        _buch, "_offene_uids", 'return fenster_des_kontos(fenster, adresse, adressen), ""',
        'return fenster_des_kontos(fenster, adresse), ""'))
    with pytest.raises(AssertionError, match=f"ein Fenster von {identitaet} hält den "
                                             "Entwurf offen"):
        probe(monkeypatch, tmp_path / "s", identitaet)
    # Der Alias fällt auf den nachsichtigen Weg zurück: OFFEN, aber ohne Zuordnung.
    with pytest.raises(AssertionError, match="einer Identität desselben Kontos"):
        alias(monkeypatch, tmp_path / "a")


def test_ohne_alias_ausnahme_wartet_auch_der_alias(monkeypatch, tmp_path):
    from falzmarke import entwurfsbuch as _buch
    from test_entwurfsbuch import (
        test_mit_profil_faellt_ein_fremdes_fenster_derselben_uid_heraus as fremd,
        test_mit_profil_ist_der_alias_sicher_zugeordnet as alias)

    alias(monkeypatch, tmp_path / "k")                                     # Kontrolle
    monkeypatch.setattr(_buch, "fenster_des_kontos", _zeile_ersetzt(
        _buch, "fenster_des_kontos", "if gemeldet not in kontoadressen:", "if True:"))
    with pytest.raises(AssertionError, match="der Alias hält den Entwurf nicht offen"):
        alias(monkeypatch, tmp_path / "s")
    fremd(monkeypatch, tmp_path / "f", "andere@example.org")  # trägt den Fall nicht


def test_ohne_alias_marke_in_nur_uid_meldet_json_den_alias_als_uid_treffer(monkeypatch,
                                                                         tmp_path):
    from falzmarke import entwurfsbuch as _buch
    from test_entwurfsbuch import test_mit_profil_ist_der_alias_sicher_zugeordnet as alias

    alias(monkeypatch, tmp_path / "k")                                     # Kontrolle
    monkeypatch.setattr(_buch, "nur_uid", _zeile_ersetzt(
        _buch, "nur_uid", "if fenster.get(ALIAS_DES_KONTOS):", "if False:"))
    with pytest.raises(AssertionError, match="fenster_nur_uid am Alias"):
        alias(monkeypatch, tmp_path / "s")


# Nachreview #488 (04.11.2026): das Profil der Brücke, der Grund ohne
# Profilwissen, die nachsichtige Sperre vor dem Zug, `profiles.ini` außerhalb
# von UTF-8. Je eine Zeile gekippt, je eine Probe muss namentlich scheitern.

def test_mit_dem_standardprofil_statt_dem_der_bruecke_faellt_der_alias_heraus(monkeypatch,
                                                                             tmp_path):
    from falzmarke import entwurfsbuch as _buch
    from test_entwurfsbuch import test_die_aliasse_kommen_aus_dem_profil_der_bruecke as probe

    probe(monkeypatch, tmp_path / "k")                                     # Kontrolle
    monkeypatch.setattr(_buch, "kontoleser", _zeile_ersetzt(
        _buch, "kontoleser", "profil, grund = bruecken_profil(profilordner, umgebung)",
        "profil, grund = oeffnen.thunderbird_standardprofil(oeffnen.THUNDERBIRD_ORDNER), ''"))
    with pytest.raises(AssertionError, match="der Alias aus dem Profil der Brücke hält den "
                                             "Entwurf nicht offen"):
        probe(monkeypatch, tmp_path / "s")


def test_ohne_den_hinweis_verschweigt_status_den_grund(monkeypatch, tmp_path):
    from falzmarke import entwurfsbuch as _buch
    from test_entwurfsbuch import (
        test_ohne_profilwissen_sagt_status_warum_das_fremde_fenster_nur_ueber_die_uid_zaehlt
        as probe)

    probe(monkeypatch, tmp_path / "k")                                     # Kontrolle
    # Seit #500 schreibt `abgleich` den Hinweis, an den Entwürfen des Kontos.
    monkeypatch.setattr(_buch, "abgleich", _zeile_ersetzt(
        _buch, "abgleich", "if ohne_identitaeten and any(", "if False and any("))
    with pytest.raises(AssertionError, match="status verschweigt, warum das fremde Fenster"):
        probe(monkeypatch, tmp_path / "s")


def test_eine_strenge_sperre_vor_dem_zug_laesst_das_fenster_ausserhalb_des_kontos_durch(
        monkeypatch, tmp_path):
    """Die Entscheidung aus dem Nachreview: Wer `_ziehe` wieder streng macht,
    verliert den Entwurf unter einem Alias, den `prefs.js` noch nicht kennt."""
    from falzmarke import entwurfsablage as _ablage
    from test_entwurfsablage import (
        test_die_letzte_sperre_haelt_auch_ein_fenster_ausserhalb_des_kontos as probe)

    probe(monkeypatch, tmp_path / "k")                                     # Kontrolle
    monkeypatch.setattr(_ablage, "_ziehe", _zeile_ersetzt(
        _ablage, "_ziehe", "entwurfsbuch._offene_uids_nachsichtig(adresse, umgebung)",
        "entwurfsbuch._offene_uids(adresse, umgebung)"))
    with pytest.raises(AssertionError, match="das Fenster außerhalb des Kontos hält den Zug "
                                             "nicht"):
        probe(monkeypatch, tmp_path / "s")


def test_ohne_unicodedecodeerror_bricht_status_an_der_profiles_ini_ab(monkeypatch, tmp_path):
    from test_entwurfsbuch import (
        test_eine_profiles_ini_ausserhalb_von_utf8_bricht_status_nicht_ab as probe)

    probe(monkeypatch, tmp_path / "k")                                     # Kontrolle
    monkeypatch.setattr(_oeffnen, "thunderbird_standardprofil", _zeile_ersetzt(
        _oeffnen, "thunderbird_standardprofil",
        "except (configparser.Error, UnicodeDecodeError):", "except configparser.Error:"))
    with pytest.raises(UnicodeDecodeError):
        probe(monkeypatch, tmp_path / "s")


def test_ohne_zweiten_rang_gewinnt_die_reihenfolge_der_liste(monkeypatch):
    """Zwei Fenster ohne Meldung; das fremde steht zuerst in der Liste."""
    from falzmarke import entwurfsbuch as _buch

    fenster = (_fenster_410(_URI_FREMD, betreff="nur der Login"),
               _fenster_410(_URI_EIGEN, betreff="Adresse in der URI"))
    assert _uids_410(monkeypatch, *fenster)["4711"]["betreff"] == "Adresse in der URI", \
        "Kontrollprobe: unsabotiert gewinnt die Adresse"
    monkeypatch.setattr(_buch, "fenster_des_kontos", _zeile_ersetzt(
        _buch, "fenster_des_kontos", "key=lambda e: e[:2]", "key=lambda e: e[:1]"))
    assert _uids_410(monkeypatch, *fenster)["4711"]["betreff"] == "nur der Login"


# ── #468: Die Proben aus #461 werden selbst rot, nicht nur die Funktion ─────
#
# Die Sabotagen darüber prüfen, was die gekippte Funktion zurückgibt. Hier wird
# die Probe aus test_entwurfsbuch.py gerufen und muss namentlich scheitern.

def test_ohne_zweiten_rang_wird_die_probe_fremd_zuerst_rot(monkeypatch):
    from falzmarke import entwurfsbuch as _buch
    from test_entwurfsbuch import test_ohne_meldung_entscheidet_die_adresse_in_der_uri as probe

    probe(monkeypatch, "fremd-zuerst")  # Kontrollprobe: unsabotiert grün
    monkeypatch.setattr(_buch, "fenster_des_kontos", _zeile_ersetzt(
        _buch, "fenster_des_kontos", "key=lambda e: e[:2]", "key=lambda e: e[:1]"))
    with pytest.raises(AssertionError, match="das falsche Fenster gewann"):
        probe(monkeypatch, "fremd-zuerst")
    probe(monkeypatch, "eigen-zuerst")  # deshalb gibt es die zweite Reihenfolge


@pytest.mark.parametrize("identitaet", [None, _VON_410], ids=["ohne-meldung", "eigene-meldung"])
def test_ein_gelockertes_uid_muster_macht_die_probe_ohne_uid_rot(monkeypatch, identitaet):
    """Nimmt das Muster jede Zahl am Ende, gilt auch `…/4711` als UID."""
    import re

    from falzmarke import entwurfsbuch as _buch
    from test_entwurfsbuch import test_ein_fenster_ohne_uid_in_der_uri_zaehlt_nicht as probe

    probe(monkeypatch, identitaet)  # Kontrollprobe: unsabotiert grün
    monkeypatch.setattr(_buch, "UID_AUS_URI", re.compile(r"(\d+)$"))
    with pytest.raises(AssertionError, match="wartet"):
        probe(monkeypatch, identitaet)


def test_traegt_die_uid_nicht_allein_wird_nur_der_zwilling_ohne_meldung_rot(monkeypatch):
    """Der Stand vor #410: ein Fenster ohne Meldung fällt heraus. Der Zwilling
    mit eigener Identität bemerkt das nicht, deshalb gibt es den ohne."""
    from falzmarke import entwurfsbuch as _buch
    from test_entwurfsbuch import test_ein_fenster_ohne_uid_in_der_uri_zaehlt_nicht as probe

    probe(monkeypatch, None)  # Kontrollprobe: unsabotiert grün
    monkeypatch.setattr(_buch, "fenster_des_kontos", _zeile_ersetzt(
        _buch, "fenster_des_kontos",
        "rang = 0 if gemeldet == eigen else 1 if not gemeldet else 2",
        "if not gemeldet:\n            continue\n        rang = 0 if gemeldet == eigen else 2"))
    with pytest.raises(AssertionError, match="gar nicht OFFEN"):
        probe(monkeypatch, None)
    probe(monkeypatch, _VON_410)


def test_heisst_der_zustand_nicht_offen_wird_die_probe_zum_zweiten_rang_rot(monkeypatch):
    """Das Fenster hängt am Zustand auch dann, wenn `art` es nicht nutzt. Bis
    #468 prüfte die Probe nur den Betreff des Fensters und blieb hier grün."""
    from falzmarke import entwurfsbuch as _buch
    from test_entwurfsbuch import test_ohne_meldung_entscheidet_die_adresse_in_der_uri as probe

    probe(monkeypatch, "eigen-zuerst")  # Kontrollprobe: unsabotiert grün
    monkeypatch.setattr(_buch, "abgleich", _zeile_ersetzt(
        _buch, "abgleich",
        'art = ("schon_raus" if gleich else "offen" if fenster is not None else "wartet")',
        'art = ("schon_raus" if gleich else "wartet")'))
    with pytest.raises(AssertionError, match="nicht OFFEN, sondern wartet"):
        probe(monkeypatch, "eigen-zuerst")


# ── Die Empfänger im Fenster (#464) ─────────────────────────────────────────
#
# ANLASS (03.11.2026): Ein Verfassen-Fenster ging ohne An, Cc und Bcc auf, und
# `email --oeffnen` meldete `OK  Entwurf offen`. Seitdem vergleicht
# `oeffnen.empfaenger_pruefen` das Fenster mit der Nachricht. Die Zusage ist
# zweiseitig: Ein leeres `an` schlägt an, ein passendes bleibt still. Die
# Sabotage trifft genau die Zeile, die Soll und Ist vergleicht; danach muss der
# erste Fall kippen und der zweite bleiben — einmal an der Funktion, einmal am
# Weg, den `email --oeffnen` wirklich geht.

_SOLL_464 = {"an": ("paula@example.org",), "kopie": (), "blindkopie": ()}


def _fenster_464(*an: str):
    from falzmarke import bruecke as _bruecke

    return _bruecke.Oeffnung("geoeffnet", gelesen=True, an=tuple(an))


def _durchwinkend():
    return _zeile_ersetzt(_oeffnen, "empfaenger_pruefen", "if soll_menge == ist_menge:",
                          "if True:")


def test_ein_leeres_an_schlaegt_an_und_ein_passendes_bleibt_still():
    leer = _oeffnen.empfaenger_pruefen(_fenster_464(), _SOLL_464)
    passend = _oeffnen.empfaenger_pruefen(_fenster_464("Paula@example.org"), _SOLL_464)
    assert leer.geprueft and leer.abweichung == "An: fehlt paula@example.org"
    assert passend.geprueft and passend.abweichung == ""


def test_gegenprobe_ein_vergleich_der_alles_durchwinkt_macht_das_leere_fenster_still():
    sabotiert = _durchwinkend()
    assert sabotiert(_fenster_464(), _SOLL_464).abweichung == ""
    assert sabotiert(_fenster_464("paula@example.org"), _SOLL_464).abweichung == "", \
        "das passende Fenster bleibt still — sonst hätte die Probe oben nichts getrennt"


@pytest.fixture
def _email_oeffnen_464(tmp_path, monkeypatch):
    """`email --oeffnen` wie in `test_postfach_entwurf.py`, Fenster als Attrappe."""
    import functools

    from test_oeffnen import THUNDERBIRD_PFAD, Thunderbird
    from test_postfach_entwurf import MAIL, _bruecke, _server

    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("FALZMARKE_OEFFNEN", raising=False)
    monkeypatch.setenv("FALZMARKE_AUFRAEUMEN", "nie")
    monkeypatch.setenv("DISPLAY", ":0")
    monkeypatch.setattr(_oeffnen, "entwurf", functools.partial(
        _oeffnen.entwurf, plattform="darwin", umgebung={"DISPLAY": ":0"}, laufen=Thunderbird(),
        binaer=lambda: THUNDERBIRD_PFAD))
    quelle = tmp_path / "antwort.md"
    quelle.write_text(MAIL, encoding="utf-8")
    _server(monkeypatch)

    def lauf(antwort: dict) -> int:
        _bruecke(monkeypatch, antwort)
        return falzmarke.main(["email", str(quelle), "--profiles", str(PROFILE), "--oeffnen"])
    return lauf


_LEER_464 = {"ok": True, "zustand": "geoeffnet", "betreff": "x", "live": True,
             "identitaet": "muster@example.de", "an": [], "kopie": [], "blindkopie": []}


def test_email_oeffnen_warnt_am_echten_weg_vor_dem_leeren_fenster(_email_oeffnen_464, capsys):
    assert _email_oeffnen_464(_LEER_464) == falzmarke.EXIT_OK
    aus = capsys.readouterr()
    assert "EMPFÄNGER PRÜFEN" in aus.err and "OK  Entwurf offen" not in aus.out


def test_gegenprobe_am_echten_weg_macht_die_sabotage_das_leere_fenster_gruen(
        _email_oeffnen_464, monkeypatch, capsys):
    """Sonst wäre nicht belegt, dass `email --oeffnen` durch den Vergleich geht."""
    monkeypatch.setattr(_oeffnen, "empfaenger_pruefen", _durchwinkend())
    assert _email_oeffnen_464(_LEER_464) == falzmarke.EXIT_OK
    aus = capsys.readouterr()
    assert "EMPFÄNGER PRÜFEN" not in aus.err and "OK  Entwurf offen" in aus.out


# #481: Den Maßstab für `entwurf-oeffnen` liefert die erste Sitzung, aus den
# Kopfzeilen, die `koepfe` ohnehin holt. Zwei Rückbauten, je eine Zusage.

# Die Fixture `oeffne_befehl` kommt aus test_postfach_entwurf.py (Import oben):
# Eine importierte Fixture ist in diesem Modul nutzbar, eine Kopie war es bis zum
# Nachreview von #479.


@pytest.mark.parametrize("alt, neu, erwartet", [
    # Der Weg vor #481: noch eine Sitzung und darin die ganze Nachricht.
    ("soll = kopf.empfaenger._asdict() if kopf.empfaenger is not None else None",
     "with postfach.verbinde(adresse, frist=oeffnen_modul.FRIST_POSTFACH_S) as sitzung:\n"
     "        roh = sitzung.nachricht(ordner, kopf.uid)\n"
     "    soll = postfach.kopf_aus(roh, kopf.uid, None).empfaenger._asdict()",
     "2 Anmeldungen am Postfach"),
    # Eine Sitzung, aber trotzdem `BODY.PEEK[]`: Das fiele an der Anmeldung nicht auf.
    ("koepfe = sitzung.koepfe(ordner) if ordner else []",
     "koepfe = sitzung.koepfe(ordner) if ordner else []\n"
     "            [sitzung.nachricht(ordner, k.uid) for k in koepfe]",
     "ein Abruf ohne Feldliste holt die ganze Nachricht"),
], ids=["zweite-sitzung", "ganze-nachricht"])
def test_mit_dem_alten_abruf_wird_die_probe_rot(alt, neu, erwartet, oeffne_befehl,
                                                monkeypatch, capsys):
    from falzmarke import cli as _cli
    from test_postfach_entwurf import (
        test_entwurf_oeffnen_meldet_sich_einmal_an_und_holt_nur_kopfzeilen as probe)

    probe(oeffne_befehl, monkeypatch, capsys)                               # Kontrolle
    monkeypatch.setattr(_cli, "befehl_entwurf_oeffnen",
                        _zeile_ersetzt(_cli, "befehl_entwurf_oeffnen", alt, neu))
    with pytest.raises(AssertionError, match=erwartet):
        probe(oeffne_befehl, monkeypatch, capsys)


def test_mit_zusammengeworfenem_an_steht_die_kopie_unter_an(oeffne_befehl, monkeypatch,
                                                            capsys):
    """`Kopf.empfaenger.an` aus To, Cc und Bcc gebaut, wie `Kopf.an`."""
    from falzmarke import postfach as _postfach
    from test_postfach_entwurf import test_entwurf_oeffnen_sieht_ein_fehlendes_cc as probe

    probe(oeffne_befehl, monkeypatch, capsys)                               # Kontrolle
    monkeypatch.setattr(_postfach, "kopf_aus", _zeile_ersetzt(
        _postfach, "kopf_aus",
        'empfaenger = Empfaenger(*(_adressen(nachricht, feld) for feld in ("To", "Cc", "Bcc")))',
        'empfaenger = Empfaenger(_adressen(nachricht, "To", "Cc", "Bcc"), '
        '_adressen(nachricht, "Cc"), _adressen(nachricht, "Bcc"))'))
    with pytest.raises(AssertionError, match=r"An: fehlt archiv@example\.de, c@example\.org"):
        probe(oeffne_befehl, monkeypatch, capsys)


# #482: Der Absender im Fenster gegen den `From` des Entwurfs. Je eine Sabotage
# für den Vergleich, das Alias-Wissen aus dem Profil und jeden der beiden Aufrufer.

def test_ohne_vergleich_geht_die_fremde_identitaet_durch(oeffne_befehl, monkeypatch,
                                                         capsys, tmp_path):
    """Die Alias-Probe bleibt dabei grün: Sie darf den Fall nicht tragen."""
    from test_postfach_entwurf import (
        test_entwurf_oeffnen_unter_einem_alias_ist_gruen as alias,
        test_entwurf_oeffnen_unter_fremder_identitaet_ist_exit_3 as fremd)

    fremd(oeffne_befehl, monkeypatch, capsys, tmp_path / "k")             # Kontrolle
    monkeypatch.setattr(_oeffnen, "absender_pruefen", _zeile_ersetzt(
        _oeffnen, "absender_pruefen", "if ist in adressen:", "if True:"))
    with pytest.raises(AssertionError, match=r"assert 0 == 3"):
        fremd(oeffne_befehl, monkeypatch, capsys, tmp_path / "s")
    alias(oeffne_befehl, monkeypatch, capsys, tmp_path / "a")


def test_ohne_aliasse_aus_dem_profil_wird_der_alias_rot(oeffne_befehl, monkeypatch,
                                                        capsys, tmp_path):
    """`kontoadressen` nur mit der eigenen Adresse: der Fehlalarm aus #462."""
    from test_postfach_entwurf import test_entwurf_oeffnen_unter_einem_alias_ist_gruen as alias

    alias(oeffne_befehl, monkeypatch, capsys, tmp_path / "k")             # Kontrolle
    # Seit #515/6 steht die Schleife in `konto_in`, das beide Wege rufen.
    monkeypatch.setattr(_oeffnen, "konto_in", _zeile_ersetzt(
        _oeffnen, "konto_in", "adressen |= im_konto", "adressen |= im_konto & {adresse}"))
    with pytest.raises(AssertionError, match=r"assert 3 == 0"):
        alias(oeffne_befehl, monkeypatch, capsys, tmp_path / "s")


def test_ohne_aufruf_meldet_entwurf_oeffnen_die_fremde_identitaet_nicht(
        oeffne_befehl, monkeypatch, capsys, tmp_path):
    from falzmarke import cli as _cli
    from test_postfach_entwurf import (
        test_entwurf_oeffnen_unter_fremder_identitaet_ist_exit_3 as fremd)

    fremd(oeffne_befehl, monkeypatch, capsys, tmp_path / "k")             # Kontrolle
    monkeypatch.setattr(_cli, "befehl_entwurf_oeffnen", _zeile_ersetzt(
        _cli, "befehl_entwurf_oeffnen",
        "oeffnung = oeffnen_modul.absender_pruefen(oeffnung, kopf.von)",
        "pass"))
    with pytest.raises(AssertionError, match=r"assert 0 == 3"):
        fremd(oeffne_befehl, monkeypatch, capsys, tmp_path / "s")


def test_ohne_aufruf_meldet_email_oeffnen_die_fremde_identitaet_nicht(
        _email_oeffnen_464, monkeypatch, capsys, tmp_path):
    from test_postfach_entwurf import (
        test_email_oeffnen_unter_fremder_identitaet_warnt_mit_exit_0 as fremd)

    def befehl():
        return falzmarke.main(["email", str(tmp_path / "antwort.md"), "--profiles", str(PROFILE),
                               "--oeffnen"])

    fremd(befehl, monkeypatch, capsys, tmp_path / "k")                           # Kontrolle
    monkeypatch.setattr(_oeffnen, "_fenster_auf", _zeile_ersetzt(
        _oeffnen, "_fenster_auf",
        # Ein Fenster ist ein nicht leeres Tupel: `fenster or …` ruft die Prüfung nie.
        "return lage._replace(fenster=absender_pruefen(",
        "return lage._replace(fenster=fenster or absender_pruefen("))
    with pytest.raises(AssertionError, match="ABSENDER PRÜFEN"):
        fremd(befehl, monkeypatch, capsys, tmp_path / "s")


# Nachreview #487 (04.11.2026): das Konto des Fensters als Rückfall, das Profil
# der Brücke an beiden Aufrufern, die NICHT-GEPRÜFT-Zeile neben einem PRÜFEN.

def test_ohne_rueckfall_auf_das_konto_des_fensters_bleibt_es_bei_nicht_geprueft(
        oeffne_befehl, monkeypatch, capsys, tmp_path):
    """Der Zwilling (keine der beiden Adressen bekannt) bleibt dabei grün."""
    from test_postfach_entwurf import (
        test_absender_pruefen_fragt_auch_das_konto_des_fensters as probe,
        test_absender_pruefen_kennt_das_profil_keine_der_beiden_bleibt_es_ungeprueft as zwilling,
        test_entwurf_oeffnen_mit_from_ausserhalb_der_konten_ist_exit_3 as befehl)

    probe(monkeypatch, tmp_path / "k")                                     # Kontrolle
    monkeypatch.setattr(_oeffnen, "absender_pruefen", _zeile_ersetzt(
        _oeffnen, "absender_pruefen",
        "if adressen is None and konto(ist)[0] is not None:",
        "if False:"))
    with pytest.raises(AssertionError, match="nur NICHT GEPRÜFT, obwohl das Fenster"):
        probe(monkeypatch, tmp_path / "s")
    with pytest.raises(AssertionError, match=r"assert 0 == 3"):
        befehl(oeffne_befehl, monkeypatch, capsys, tmp_path / "b")
    zwilling(monkeypatch, tmp_path / "z")


def test_ohne_profil_der_bruecke_gilt_der_alias_bei_entwurf_oeffnen_als_fremd(
        oeffne_befehl, monkeypatch, capsys, tmp_path):
    from falzmarke import cli as _cli
    from test_postfach_entwurf import (
        test_entwurf_oeffnen_liest_die_aliasse_aus_dem_profil_der_bruecke as probe)

    probe(oeffne_befehl, monkeypatch, capsys, tmp_path / "k")             # Kontrolle
    monkeypatch.setattr(_cli, "befehl_entwurf_oeffnen", _zeile_ersetzt(
        # Seit #500 löst `absender_pruefen` das Profil auf; eine leere Umgebung
        # übergeht den Socket wie früher `profil = None`.
        _cli, "befehl_entwurf_oeffnen",
        "oeffnung = oeffnen_modul.absender_pruefen(oeffnung, kopf.von)",
        "oeffnung = oeffnen_modul.absender_pruefen(oeffnung, kopf.von, umgebung={})"))
    with pytest.raises(AssertionError, match="der Alias aus dem Profil der Brücke gilt als "
                                             "fremd"):
        probe(oeffne_befehl, monkeypatch, capsys, tmp_path / "s")


def test_ohne_profil_der_bruecke_gilt_der_alias_bei_email_oeffnen_als_fremd(monkeypatch,
                                                                            tmp_path):
    from test_postfach_entwurf import (
        test_email_oeffnen_liest_die_aliasse_aus_dem_profil_der_bruecke as probe)

    probe(monkeypatch, tmp_path / "k")                                     # Kontrolle
    monkeypatch.setattr(_oeffnen, "_fenster_auf", _zeile_ersetzt(
        _oeffnen, "_fenster_auf", "umgebung=umgebung))", "umgebung={}))"))
    with pytest.raises(AssertionError, match="email --oeffnen: der Alias aus dem Profil"):
        probe(monkeypatch, tmp_path / "s")


@pytest.mark.parametrize("fall, alt", [
    ("absender-prueft-empfaenger-offen",
     ("            if not fenster.geprueft:\n"
      "                _empfaenger_ungeprueft(fenster)\n"
      "            elif not fenster.abweichung:\n"
      "                _empfaenger_ok(fenster)\n")),
    ("empfaenger-prueft-absender-offen",
     ("            if not fenster.absender_geprueft and fenster.absender_hinweis:\n"
      "                _absender_ungeprueft(fenster)\n"
      "            elif fenster.absender_geprueft and not fenster.absender_abweichung:\n"
      "                _absender_ok(fenster)\n")),
], ids=["empfaengerzeile", "absenderzeile"])
def test_ohne_die_zeile_der_anderen_pruefung_verschweigt_pruefen_sie(monkeypatch, capsys, fall,
                                                                     alt):
    """Je Richtung eine Sabotage; die andere Richtung bleibt dabei grün.

    Baut den Stand vor #497 nach (#522, Punkt 9): Der PRÜFEN-Block kehrte ohne
    jede Zeile der anderen Prüfung zurück, die Sabotage streicht `if` und `elif`
    zusammen. Die früher gekippte Bedingung druckte stattdessen eine falsche
    OK-Zeile; die fängt `test_ohne_vergleich_steht_trotzdem_ok`."""
    from falzmarke import cli as _cli
    from test_postfach_entwurf import (
        test_neben_einem_pruefen_steht_was_die_andere_pruefung_nicht_verglich as probe)

    faelle = _faelle_der_anderen_pruefung()
    for werte in faelle.values():                                          # Kontrolle
        probe(*werte, capsys)
    monkeypatch.setattr(_cli, "_melde_fenster", _zeile_ersetzt(_cli, "_melde_fenster", alt, ""))
    with pytest.raises(AssertionError, match="neben .* PRÜFEN fehlt „NICHT GEPRÜFT"):
        probe(*faelle[fall], capsys)
    for anderer, werte in faelle.items():
        if anderer != fall:
            probe(*werte, capsys)


def _faelle_der_anderen_pruefung():
    from test_postfach_entwurf import (
        test_neben_einem_pruefen_steht_was_die_andere_pruefung_nicht_verglich as probe)

    marke = next(m for m in probe.pytestmark if m.name == "parametrize")
    return dict(zip(marke.kwargs["ids"], marke.args[1], strict=True))


@pytest.mark.parametrize("fall, alt, neu", [
    ("ohne-pruefen",
     "        if fenster.geprueft:\n            _empfaenger_ok(fenster)\n",
     "        if True:\n            _empfaenger_ok(fenster)\n"),
    ("absender-prueft",
     "            if not fenster.geprueft:\n                _empfaenger_ungeprueft(fenster)\n",
     "            if False:\n                _empfaenger_ungeprueft(fenster)\n"),
    ("empfaenger-prueft",
     "            elif fenster.absender_geprueft and not fenster.absender_abweichung:\n",
     "            elif not fenster.absender_abweichung:\n"),
], ids=["normalzweig", "pruefen-empfaenger", "pruefen-absender"])
def test_ohne_vergleich_steht_trotzdem_ok(monkeypatch, capsys, fall, alt, neu):
    """#522, Punkt 9: Je Zweig von `_melde_fenster` fällt die Bedingung weg, die
    ein OK an den Vergleich bindet. Nur der Fall dieses Zweigs wird rot."""
    from falzmarke import cli as _cli
    from test_postfach_entwurf import (
        test_was_nicht_verglichen_wurde_bekommt_nie_eine_ok_zeile as probe)

    marke = next(m for m in probe.pytestmark if m.name == "parametrize")
    faelle = dict(zip(marke.kwargs["ids"], marke.args[1], strict=True))
    for werte in faelle.values():                                          # Kontrolle
        probe(*werte, capsys)
    monkeypatch.setattr(_cli, "_melde_fenster", _zeile_ersetzt(_cli, "_melde_fenster", alt, neu))
    with pytest.raises(AssertionError, match=f"nicht verglichen, trotzdem .*{faelle[fall][1]}"):
        probe(*faelle[fall], capsys)
    for anderer, werte in faelle.items():
        if anderer != fall:
            probe(*werte, capsys)


# #500 (05.11.2026): der richtige Grund bei ABSENDER PRÜFEN, der Grund der Brücke
# bei NICHT GEPRÜFT, die OK-Zeile neben einem PRÜFEN, der Hinweis nur am eigenen Entwurf.

def test_mit_dem_festen_satz_nennt_absender_pruefen_das_gegenteil(oeffne_befehl, monkeypatch,
                                                                  capsys, tmp_path):
    """Seit #522 (Punkt 10) steht der Grund in der Abweichung, gesetzt in
    `absender_pruefen`. Dort setzt die Sabotage den festen Satz, wie ihn `cli`
    bis #500 für jede Abweichung nahm."""
    from test_postfach_entwurf import (
        test_from_ausserhalb_der_konten_nennt_den_richtigen_grund as probe)

    probe(oeffne_befehl, monkeypatch, capsys, tmp_path / "k")             # Kontrolle
    monkeypatch.setattr(_oeffnen, "absender_pruefen", _zeile_ersetzt(
        _oeffnen, "absender_pruefen",
        'f"{soll} gehört zu keinem Konto im Profil, {ist} schon: "',
        '"das Fenster schickt von einer Identität außerhalb des Kontos: "'))
    with pytest.raises(AssertionError, match="ABSENDER PRÜFEN verschweigt, dass die Nachricht"):
        probe(oeffne_befehl, monkeypatch, capsys, tmp_path / "s")


def test_mit_eigener_profilaufloesung_geht_der_grund_der_bruecke_verloren(monkeypatch, tmp_path):
    """Baut den Stand vor #500 nach: `oeffnen.kontoadressen` ohne Profil liest das
    Standardprofil und begründet mit dessen Fehlen, nicht mit dem Socket. Die
    Funktion ist mit #522 (Punkt 7) entfallen; die Sabotage schreibt aus, was sie tat."""
    from test_postfach_entwurf import (
        test_ohne_profil_am_socket_nennt_nicht_geprueft_den_grund_der_bruecke as probe)

    probe(monkeypatch, tmp_path / "k")                                     # Kontrolle
    monkeypatch.setattr(_oeffnen, "absender_pruefen", _zeile_ersetzt(
        _oeffnen, "absender_pruefen",
        "    konto = entwurfsbuch.kontoleser(umgebung)\n"
        "    adressen, grund = konto(soll)\n"
        "    if adressen is None and konto(ist)[0] is not None:",
        "    konto = lambda a: (lambda p: konto_in(thunderbird_einstellungen(p[0]), p[0].name, a)\n"
        "                       if p[0] else (None, p[1]))(_profil_aus(None, None))\n"
        "    adressen, grund = konto(soll)\n"
        "    if adressen is None and konto(ist)[0] is not None:"))
    with pytest.raises(AssertionError, match="kein Thunderbird-Profil unter"):
        probe(monkeypatch, tmp_path / "s")


@pytest.mark.parametrize("fall, alt", [
    ("absender-prueft-empfaenger-gleich",
     "            elif not fenster.abweichung:\n                _empfaenger_ok(fenster)\n"),
    ("empfaenger-prueft-absender-alias",
     ("            elif fenster.absender_geprueft and not fenster.absender_abweichung:\n"
      "                _absender_ok(fenster)\n")),
], ids=["empfaengerzeile", "absenderzeile"])
def test_ohne_die_ok_zeile_der_anderen_pruefung_verschweigt_pruefen_sie(monkeypatch, capsys,
                                                                        fall, alt):
    """Je Richtung eine Sabotage; die andere Richtung bleibt dabei grün."""
    from falzmarke import cli as _cli
    from test_postfach_entwurf import (
        test_neben_einem_pruefen_steht_was_die_andere_pruefung_bestand as probe)

    marke = next(m for m in probe.pytestmark if m.name == "parametrize")
    faelle = dict(zip(marke.kwargs["ids"], marke.args[1], strict=True))
    for werte in faelle.values():                                          # Kontrolle
        probe(*werte, capsys)
    monkeypatch.setattr(_cli, "_melde_fenster", _zeile_ersetzt(_cli, "_melde_fenster", alt, ""))
    with pytest.raises(AssertionError, match="neben .* PRÜFEN fehlt „OK  "):
        probe(*faelle[fall], capsys)
    for anderer, werte in faelle.items():
        if anderer != fall:
            probe(*werte, capsys)


def test_ueber_alle_fenster_gezaehlt_steht_der_hinweis_bei_jedem_konto(monkeypatch, tmp_path):
    """Baut den Stand vor #500 nach: irgendein fremdes Fenster genügte, ob seine UID
    hier liegt oder nicht. Der Zwilling mit der UID des Entwurfs bleibt grün."""
    from falzmarke import entwurfsbuch as _buch
    from test_entwurfsbuch import (
        test_ohne_profilwissen_sagt_status_warum_das_fremde_fenster_nur_ueber_die_uid_zaehlt
        as zwilling)
    from test_entwurfsbuch import (
        test_ohne_profilwissen_zaehlt_ein_fenster_ohne_entwurf_hier_nicht as probe)

    probe(monkeypatch, tmp_path / "k")                                     # Kontrolle
    monkeypatch.setattr(_buch, "abgleich", _zeile_ersetzt(
        _buch, "abgleich",
        "if ohne_identitaeten and any(fremde_identitaet(offen.get(k.uid), adresse)\n"
        "                                         for k in liegend):",
        "if ohne_identitaeten and any(fremde_identitaet(f, adresse)\n"
        "                                         for f in offen.values()):"))
    with pytest.raises(AssertionError, match="status zählt ein Fenster ohne Entwurf"):
        probe(monkeypatch, tmp_path / "s")
    zwilling(monkeypatch, tmp_path / "z")


# ── Das Profil, aus dem die Brücke antwortet (#410) ─────────────────────────

def _zwei_profile_410(tmp_path, *, in_a=True, in_b=True):
    """Thunderbird-Ordner, Profil A (Standard, ohne Socket), Profil B (mit Socket)."""
    import json as _json

    from falzmarke import bruecke as _bruecke
    from falzmarke import entwurfsbuch as _buch

    ordner = tmp_path / "Thunderbird"
    a, b = ordner / "Profiles" / "aaa.default-release", ordner / "Profiles" / "bbb.zweites"
    a.mkdir(parents=True)
    b.mkdir(parents=True)
    (ordner / "profiles.ini").write_text(
        "[Install1]\nDefault=Profiles/aaa.default-release\n", encoding="utf-8")
    for profil, da, woher in ((a, in_a, "A"), (b, in_b, "B")):
        (profil / "prefs.js").write_text("", encoding="utf-8")
        if da:
            (profil / _buch.TAGEBUCH).write_text(
                _json.dumps({"art": "geoeffnet", "zeit": "2026-10-25T11:00:00.000Z",
                             "ursprung": {"betreff": f"aus {woher}"}}) + "\n", encoding="utf-8")
    (b / _bruecke.SOCKET_DATEI).write_text("", encoding="utf-8")
    return ordner, a, b


def _woher_410(eintraege) -> list[str]:
    return [(e.get("ursprung") or {}).get("betreff", "") for e in eintraege]


def test_der_socket_entscheidet_das_profil_und_der_zwilling_zeigt_es(monkeypatch, tmp_path):
    """Zwillingsvergleich: derselbe Aufbau, einmal mit und einmal ohne Schalter.

    Ein einzelner Lauf könnte nicht belegen, dass der Socket das Profil
    bestimmt — er sähe genauso aus, wenn stets B gelesen würde. Erst die zwei
    verschiedenen Ergebnisse trennen die Fälle.
    """
    from falzmarke import bruecke as _bruecke
    from falzmarke import entwurfsbuch as _buch
    from falzmarke import oeffnen as _oeff

    ordner, _, b = _zwei_profile_410(tmp_path)
    monkeypatch.setattr(_oeff, "THUNDERBIRD_ORDNER", ordner)
    mit, _ = _buch.tagebuch(umgebung={"FALZMARKE_BRUECKE_SOCKET":
                                      str(b / _bruecke.SOCKET_DATEI)})
    ohne, _ = _buch.tagebuch(umgebung={})
    assert (_woher_410(mit), _woher_410(ohne)) == (["aus B"], ["aus A"])


def test_ein_standardprofil_statt_des_sockets_liest_die_falsche_datei(monkeypatch, tmp_path):
    """Sabotage: `bruecken_profil` nimmt wieder stur das Standardprofil.

    Dann steht im Bericht, was in Profil A liegt, während das Add-on aus B
    antwortet — und bei fehlendem Tagebuch in B meldete es nicht einmal etwas,
    weil A ja eines hat. Still falsch, nicht leer: der Kern von #410.
    """
    from falzmarke import bruecke as _bruecke
    from falzmarke import entwurfsbuch as _buch
    from falzmarke import oeffnen as _oeff

    ordner, _, b = _zwei_profile_410(tmp_path)
    monkeypatch.setattr(_oeff, "THUNDERBIRD_ORDNER", ordner)
    monkeypatch.setattr(_buch, "bruecken_profil",
                        lambda profilordner=None, umgebung=None:
                        (_oeff.thunderbird_standardprofil(
                            _oeff.THUNDERBIRD_ORDNER if profilordner is None
                            else Path(profilordner)), ""))
    eintraege, grund = _buch.tagebuch(
        umgebung={"FALZMARKE_BRUECKE_SOCKET": str(b / _bruecke.SOCKET_DATEI)})
    assert _woher_410(eintraege) == ["aus A"] and not grund


def test_der_hinweis_nennt_das_gelesene_profil_und_zwar_verschieden(monkeypatch, tmp_path):
    """Zwei Profile ohne Tagebuch, zwei Hinweise — und sie müssen sich unterscheiden.

    Ein fester Text „kein Tagebuch im Thunderbird-Profil“ könnte diese Probe
    nicht bestehen: Sie verlangt nicht, dass ein Name dasteht, sondern dass der
    **richtige** dasteht. Das ist der Unterschied zwischen einer Behauptung und
    einer Messung.
    """
    from falzmarke import bruecke as _bruecke
    from falzmarke import entwurfsbuch as _buch
    from falzmarke import oeffnen as _oeff

    ordner, a, b = _zwei_profile_410(tmp_path, in_a=False, in_b=False)
    monkeypatch.setattr(_oeff, "THUNDERBIRD_ORDNER", ordner)
    (a / _bruecke.SOCKET_DATEI).write_text("", encoding="utf-8")
    _, aus_b = _buch.tagebuch(umgebung={"FALZMARKE_BRUECKE_SOCKET":
                                        str(b / _bruecke.SOCKET_DATEI)})
    _, aus_a = _buch.tagebuch(umgebung={"FALZMARKE_BRUECKE_SOCKET":
                                        str(a / _bruecke.SOCKET_DATEI)})
    assert b.name in aus_b and a.name not in aus_b
    assert a.name in aus_a and b.name not in aus_a


# ── Die Ordner der Identität aus dem Profil der Brücke (#522, Punkt 6) ──────
#
# Eine Sabotage, der alte Code: `entwurfsbuch.thunderbird_ordner` liest wieder
# das Standardprofil, wie bis dahin alle vier Aufrufer. Jeder Weg hat seine
# eigene Probe, und jede muss mit ihrem eigenen Satz scheitern. Ein Weg, der
# grün bliebe, hinge nicht an dieser Stelle.

_ALTES_PROFIL_522 = (
    "profil, grund = bruecken_profil(profilordner, umgebung)",
    ("profil, grund = oeffnen.thunderbird_standardprofil("
     "oeffnen.THUNDERBIRD_ORDNER if profilordner is None else Path(profilordner)), \"\""))


def _altes_profil_522(monkeypatch):
    from falzmarke import entwurfsbuch as _buch

    monkeypatch.setattr(_buch, "thunderbird_ordner", _zeile_ersetzt(
        _buch, "thunderbird_ordner", *_ALTES_PROFIL_522))


def test_mit_dem_standardprofil_nennt_die_identitaet_den_falschen_ordner(monkeypatch, tmp_path):
    from test_entwurfsbuch import (
        test_die_ordner_der_identitaet_kommen_aus_dem_profil_der_bruecke as probe,
    )

    werte = ("draft_folder", "Entw&APw-rfe", "Alt-Entwuerfe")
    probe(monkeypatch, tmp_path / "k", *werte)                             # Kontrolle
    _altes_profil_522(monkeypatch)
    with pytest.raises(AssertionError, match="der Ordner kommt nicht aus dem Profil der Brücke"):
        probe(monkeypatch, tmp_path / "s", *werte)


def test_mit_dem_standardprofil_liest_abgleich_den_falschen_entwuerfe_ordner(monkeypatch,
                                                                           tmp_path):
    from test_entwurfsbuch import (
        test_abgleich_liest_die_entwuerfe_aus_dem_profil_der_bruecke as probe,
    )

    probe(monkeypatch, tmp_path / "k")                                     # Kontrolle
    _altes_profil_522(monkeypatch)
    with pytest.raises(AssertionError, match="abgleich liest den Entwürfe-Ordner am Profil"):
        probe(monkeypatch, tmp_path / "s")


def test_mit_dem_standardprofil_listet_entwurf_oeffnen_den_falschen_ordner(oeffne_befehl,
                                                                         monkeypatch, capsys,
                                                                         tmp_path):
    from test_postfach_entwurf import (
        test_entwurf_oeffnen_liest_den_ordner_aus_dem_profil_der_bruecke as probe,
    )

    probe(oeffne_befehl, monkeypatch, capsys, tmp_path / "k")             # Kontrolle
    _altes_profil_522(monkeypatch)
    with pytest.raises(AssertionError, match="entwurf-oeffnen liest den Entwürfe-Ordner"):
        probe(oeffne_befehl, monkeypatch, capsys, tmp_path / "s")


def test_mit_dem_standardprofil_legt_email_oeffnen_im_falschen_ordner_ab(monkeypatch, tmp_path):
    from falzmarke import eml as _eml
    from test_postfach_entwurf import MAIL
    from test_postfach_entwurf import (
        test_email_oeffnen_legt_in_den_ordner_aus_dem_profil_der_bruecke as probe,
    )

    quelle = tmp_path / "antwort.md"
    quelle.write_text(MAIL, encoding="utf-8")
    pfad, _ = falzmarke.setze_email(quelle, tmp_path / "antwort", profil_verzeichnis=PROFILE)
    felder = _eml.entwurfsfelder(pfad)
    probe(monkeypatch, felder, tmp_path / "k")                             # Kontrolle
    _altes_profil_522(monkeypatch)
    with pytest.raises(AssertionError, match="email --oeffnen legt am Profil der Brücke vorbei"):
        probe(monkeypatch, felder, tmp_path / "s")


def test_mit_dem_standardprofil_liest_die_sperre_den_falschen_gesendet_ordner(monkeypatch,
                                                                            tmp_path):
    from test_gesendet import test_der_gesendet_ordner_kommt_aus_dem_profil_der_bruecke as probe

    eigene = _eigene_mail(tmp_path)
    probe(eigene, monkeypatch, tmp_path / "k")                             # Kontrolle
    _altes_profil_522(monkeypatch)
    with pytest.raises(AssertionError, match="die Sperre liest den Gesendet-Ordner am Profil"):
        probe(eigene, monkeypatch, tmp_path / "s")


# Nachreview #534, Befund A: Der Wächter übersprang `entwurfsbuch.py` ganz, und
# gerade dort hatte `abgleich` den Ordner bis #522 selbst am Standardprofil
# gelesen. Je eine Sabotage im Quelltext, den der Wächter liest: der direkte
# Aufruf in `abgleich` und einer in `oeffnen`, wo die alte Regel galt. Jeder Fund
# muss Datei und Funktion nennen.

@pytest.mark.parametrize("datei, alt, neu, erwartet", [
    ("entwurfsbuch.py", "ordner_e = (thunderbird_ordner(",
     "ordner_e = (oeffnen.thunderbird_ordner(", r"entwurfsbuch\.py:\d+ in abgleich'"),
    ("oeffnen.py", '= entwurfsbuch.thunderbird_ordner(adresse, "draft_folder"',
     '= thunderbird_ordner(adresse, "draft_folder"', r"oeffnen\.py:\d+ in _entwurf_postfach'"),
], ids=["entwurfsbuch-abgleich", "oeffnen-entwurf-postfach"])
def test_der_ordnerwaechter_sieht_den_direkten_aufruf(datei, alt, neu, erwartet):
    from test_postfach_entwurf import _paketquellen, _pruefe_ordneraufrufe

    quellen = _paketquellen()
    _pruefe_ordneraufrufe(quellen)                                         # Kontrolle
    assert quellen[datei].count(alt) == 1, f"„{alt}“ steht nicht genau einmal in {datei}"
    sabotiert = {**quellen, datei: quellen[datei].replace(alt, neu)}
    with pytest.raises(AssertionError, match=erwartet):
        _pruefe_ordneraufrufe(sabotiert)


# Nachreview #534, Befund B: der alte Code, an die Schnittstelle mit Grund
# angepasst — `profil, _ =`, und ohne Profil kommt kein Grund mit.

_GRUND_VERWORFEN_534 = (
    ("profil, grund = bruecken_profil(profilordner, umgebung)\n"
     "    if profil is None:\n"
     "        return None, grund\n"),
    ("profil, _ = bruecken_profil(profilordner, umgebung)\n"
     "    if profil is None:\n"
     "        return None, \"\"\n"))


def test_ohne_den_grund_nennt_entwurf_oeffnen_die_falsche_ursache(oeffne_befehl, monkeypatch,
                                                                  capsys, tmp_path):
    from falzmarke import entwurfsbuch as _buch
    from test_postfach_entwurf import (
        test_entwurf_oeffnen_ohne_profil_der_bruecke_nennt_den_grund as probe,
    )

    probe(oeffne_befehl, monkeypatch, capsys, tmp_path / "k")             # Kontrolle
    monkeypatch.setattr(_buch, "thunderbird_ordner", _zeile_ersetzt(
        _buch, "thunderbird_ordner", *_GRUND_VERWORFEN_534))
    with pytest.raises(AssertionError,
                       match="entwurf-oeffnen verliert den Grund aus bruecken_profil"):
        probe(oeffne_befehl, monkeypatch, capsys, tmp_path / "s")


def test_mit_umgebung_als_positionsparameter_wird_die_signaturprobe_rot(monkeypatch, tmp_path):
    """Befund C: `umgebung` wieder als dritter Positionsparameter, wie bis dahin."""
    from falzmarke import entwurfsbuch as _buch
    from test_entwurfsbuch import (
        test_thunderbird_ordner_nimmt_umgebung_und_profilordner_nur_als_schluesselwort as probe,
    )

    probe(monkeypatch, tmp_path / "k")                                     # Kontrolle
    monkeypatch.setattr(_buch, "thunderbird_ordner", _zeile_ersetzt(
        _buch, "thunderbird_ordner", "art: str, *, umgebung", "art: str, umgebung"))
    with pytest.raises(AssertionError, match="nimmt die Umgebung als Positionsparameter"):
        probe(monkeypatch, tmp_path / "s")


# ── Die Review-Funde an der Ablage (#438) ──────────────────────────────────
#
# Vier Zusagen, die #435 nicht hatte, und zu jeder die Frage, ob sie rot werden
# kann. Jede Sabotage sitzt an **einer** Stelle; gebündelt wäre eine darunter,
# die nie anschlägt, nicht zu sehen.

_HEUTE_438 = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc)
#: Zwei Kennungen, deren Summe über 78 Zeichen liegt — `EmailMessage` faltet
#: die Zeile dann selbst, der Fall ist keiner von Hand gebaut.
_LANG_438 = "<kunde-mit-sehr-langer-nachrichtenkennung-aus-dem-fremdsystem-0001@example.org>"
_ZWEITE_438 = "<zweite-kennung@example.org>"


def _ablage_lage(monkeypatch, *, eingang, gesendet):
    """Eine Sitzung über einer Attrappe mit Eingang, Gesendet und „Archiv“."""
    from falzmarke import postfach as _postfach_modul

    from imap_attrappe import ImapAttrappe

    attrappe = ImapAttrappe(
        {"INBOX": list(eingang), "Gesendete Elemente": list(gesendet)},
        sonder={"INBOX": "", "Gesendete Elemente": "\\Sent", "Archiv": ""},
        verschieben_erlaubt=True)
    monkeypatch.setattr(_postfach_modul, "IMAP_KLASSE", attrappe)
    return attrappe, _postfach_modul.verbinde("joe@example.org", umgebung={}, frist=30)


def _eingang_438(kennung, betreff="Angebot"):
    from imap_attrappe import nachricht

    zeit = _HEUTE_438 - timedelta(days=5)
    return (nachricht(an="joe@example.org", von="kunde@example.org", betreff=betreff,
                      datum=zeit, kennung=kennung), zeit)


def _antwort_438(bezug, *, tage=1):
    """`roh_kopf`, nicht `kopf`: Die Policy von `EmailMessage` kodiert eine
    lange Message-ID auf Python 3.12 anders als auf 3.14, und die CI fährt
    3.12 — über die Policy gebaut, prüfte diese Probe dort etwas anderes."""
    from imap_attrappe import nachricht

    zeit = _HEUTE_438 - timedelta(days=tage)
    return (nachricht(an="kunde@example.org", betreff="AW: Angebot", datum=zeit,
                      kennung=f"<eigene-{tage}@example.org>",
                      roh_kopf={"In-Reply-To": bezug}), zeit)


def test_der_umbruch_wird_zweimal_gehalten_und_jede_linie_einzeln_belegt(monkeypatch):
    """Drei Filter stehen hier in Reihe, und das verdeckt jede einzelne
    Sabotage: `postfach.kennungen` zerlegt den Feldwert, `postfach.sendbar`
    überspringt, was sich nicht senden lässt (#442), und `postfach._zitiert`
    lehnt einen Umbruch ohnehin ab. Nur `_zitiert` kaputt zu machen bleibt grün
    — nicht weil die Prüfung wertlos ist, sondern weil der Fall sie nie erreicht.

    Deshalb vier Stufen in einem Durchgang, mit **vier verschiedenen**
    Ergebnissen:

    1. unsabotiert — ein Bericht, der gefaltete Bezug ist gefunden;
    2. ohne das Zerlegen — ein Bericht mit Hinweis, nichts gefunden: `sendbar` hält;
    3. auch ohne `sendbar` — `PostfachFehler`: `_zitiert` hält;
    4. ohne alle drei — der `ValueError` der Attrappe mit dem Wortlaut von
       `imaplib.IMAP4._command`, von `_befehl` seit dem Review von #460 als
       `PostfachFehler` weitergereicht. Von Stufe 3 trennt ihn der Wortlaut.
       Das ist der Zustand, in dem der Umbruch auf die Leitung geht; auf
       Python 3.12 und 3.13 lehnt `imaplib` ihn **nicht** ab, dort wären es
       zwei Befehle (gemessen 29.10.2026, #438). Die CI fährt 3.12 — ohne die
       Ablehnung in der Attrappe wäre diese Stufe dort stumm.
    """
    from falzmarke import ablage as _ablage
    from falzmarke import postfach as _postfach_modul

    lage = dict(eingang=[_eingang_438(_LANG_438)],
                gesendet=[_antwort_438(f"{_LANG_438}\r\n {_ZWEITE_438}")])

    def plane_einmal():
        with _ablage_lage(monkeypatch, **lage)[1] as sitzung:
            return _ablage.plane(sitzung, wunsch="Archiv", heute=_HEUTE_438.date())

    bericht = plane_einmal()
    assert [z.kennung for z in bericht.zuege] == [_LANG_438], \
        "Kontrollprobe: unsabotiert muss der gefaltete Bezug gefunden werden"

    # Stufe 2: ohne das Zerlegen trägt der Suchbegriff den Umbruch wieder.
    monkeypatch.setattr(_postfach_modul, "kennungen",
                        lambda wert: (str(wert or "").strip(),) if str(wert or "").strip() else ())
    bericht = plane_einmal()
    assert not bericht.zuege and any("übersprungen" in h for h in bericht.hinweise), bericht

    # Stufe 3: ohne `sendbar` erreicht er das Zitieren.
    monkeypatch.setattr(_postfach_modul, "sendbar", lambda kennung: True)
    with pytest.raises(_postfach_modul.PostfachFehler, match="Umbruch oder Nullbyte"):
        plane_einmal()

    # Stufe 4: und ohne die Ablehnung geht er hinaus.
    def nur_zitieren(name):
        return '"' + name.replace("\\", "\\\\").replace('"', '\\"') + '"'

    monkeypatch.setattr(_postfach_modul, "_zitiert", nur_zitieren)
    with pytest.raises(_postfach_modul.PostfachFehler, match="NUL, CR and LF"):
        plane_einmal()
    assert nur_zitieren("Gesendete Elemente") == '"Gesendete Elemente"', \
        "die Sabotage hat mehr getroffen als die Prüfung — das Zitieren selbst fiel"


def _antworten_442(schlecht: str):
    """Eine unsendbare Kennung und eine gesunde Antwort daneben, wie in #442."""
    gut = "<gut-442@example.org>"
    return dict(eingang=[_eingang_438(gut)],
                gesendet=[_antwort_438(schlecht, tage=2), _antwort_438(gut, tage=1)]), gut


@pytest.mark.parametrize("schlecht", ["<a\x01\x00b@example.org>", "<müller@example.org>"],
                         ids=["nullbyte", "nicht-ascii"])
def test_ohne_sendbar_kostet_eine_kennung_das_ganze_konto(monkeypatch, schlecht):
    """Zwillinge, derselbe Aufbau: Mit `sendbar` bleibt die gesunde Antwort.

    Ohne den Filter ist der Stand vor #442 wieder da: `_zitiert` wirft beim
    Nullbyte, und beim Nicht-ASCII wirft das Kodieren. Beides beendet `plane`,
    die gesunde Antwort wird nie angesehen.
    """
    from falzmarke import ablage as _ablage
    from falzmarke import postfach as _postfach_modul

    lage, gut = _antworten_442(schlecht)
    with _ablage_lage(monkeypatch, **lage)[1] as sitzung:
        bericht = _ablage.plane(sitzung, wunsch="Archiv", heute=_HEUTE_438.date())
    assert [z.kennung for z in bericht.zuege] == [gut]

    monkeypatch.setattr(_postfach_modul, "sendbar", lambda kennung: True)
    with pytest.raises((_postfach_modul.PostfachFehler, UnicodeEncodeError)):
        with _ablage_lage(monkeypatch, **lage)[1] as sitzung:
            _ablage.plane(sitzung, wunsch="Archiv", heute=_HEUTE_438.date())


def test_ohne_kontrolle_auf_prefs_verliert_ein_socket_ausserhalb_das_tagebuch(
        monkeypatch, tmp_path):
    """Derselbe Aufbau, zwei Wege, wie in #442 gemessen: 1 Eintrag gegen 0.

    Die Sabotage baut den Code aus #440 nach, `Path(sock).parent` ohne Prüfung.
    """
    from falzmarke import bruecke as _bruecke
    from falzmarke import entwurfsbuch as _buch
    from falzmarke import oeffnen as _oeff

    ordner, _, _ = _zwei_profile_410(tmp_path)
    monkeypatch.setattr(_oeff, "THUNDERBIRD_ORDNER", ordner)
    kurz = tmp_path / "s"
    kurz.mkdir()
    umgebung = {"FALZMARKE_BRUECKE_SOCKET": str(kurz / _bruecke.SOCKET_DATEI)}

    eintraege, grund = _buch.tagebuch(umgebung=umgebung)
    assert (_woher_410(eintraege), grund) == (["aus A"], "")

    monkeypatch.setattr(_buch, "bruecken_profil", lambda profilordner=None, umgebung=None: (
        Path(_bruecke.socketpfad(umgebung)).parent, ""))
    eintraege, grund = _buch.tagebuch(umgebung=umgebung)
    assert eintraege == [] and "Thunderbird-Profil „s“" in grund


def test_ohne_kontrolle_auf_prefs_gaelte_ein_profil_nicht_mehr(monkeypatch, tmp_path):
    """Die Kontrolle darf den Socket im Profil nicht entwerten: Dort liest B, nicht A."""
    from falzmarke import bruecke as _bruecke
    from falzmarke import entwurfsbuch as _buch
    from falzmarke import oeffnen as _oeff

    ordner, _, b = _zwei_profile_410(tmp_path)
    monkeypatch.setattr(_oeff, "THUNDERBIRD_ORDNER", ordner)
    umgebung = {"FALZMARKE_BRUECKE_SOCKET": str(b / _bruecke.SOCKET_DATEI)}
    assert _woher_410(_buch.tagebuch(umgebung=umgebung)[0]) == ["aus B"]
    (b / "prefs.js").unlink()
    assert _woher_410(_buch.tagebuch(umgebung=umgebung)[0]) == ["aus A"]


def test_ohne_das_zerlegen_fallen_zwei_kennungen_aus_der_zuordnung(monkeypatch):
    """Sabotage an genau einer Stelle: `kennungen` gibt den rohen Feldwert.

    Dann wird `<a@…> <b@…>` als eine Teilkette gesucht, trifft nichts — und die
    Antwort zählt als „längst weggeräumt“, während beide Nachrichten im Eingang
    liegen bleiben. Die Sabotage ist genau die Fassung, die #435 hatte.
    """
    from falzmarke import ablage as _ablage
    from falzmarke import postfach as _postfach_modul

    erste, zweite = "<a@example.org>", "<b@example.org>"
    lage = dict(eingang=[_eingang_438(erste, "Erstes"), _eingang_438(zweite, "Zweites")],
                gesendet=[_antwort_438(f"{erste} {zweite}")])
    with _ablage_lage(monkeypatch, **lage)[1] as sitzung:
        bericht = _ablage.plane(sitzung, wunsch="Archiv", heute=_HEUTE_438.date())
    assert len(bericht.zuege) == 2 and bericht.nicht_im_eingang == 0, \
        "Kontrollprobe: unsabotiert müssen beide Nachrichten gefunden werden"

    monkeypatch.setattr(_postfach_modul, "kennungen",
                        lambda wert: (str(wert or "").strip(),) if str(wert or "").strip() else ())
    attrappe, sitzung = _ablage_lage(monkeypatch, **lage)
    with sitzung:
        sabotiert = _ablage.plane(sitzung, wunsch="Archiv", heute=_HEUTE_438.date())
    assert sabotiert.zuege == () and sabotiert.nicht_im_eingang == 1, \
        "das Zerlegen ist nicht die Stelle, an der die Zuordnung entsteht"
    assert len(attrappe.ordner["INBOX"]) == 2, "die Sabotage hat Post bewegt"


def test_ohne_den_kappungshinweis_liest_sich_das_fenster_vollstaendig(monkeypatch):
    """Sabotage an genau einer Stelle: `_kappungen` gibt nichts zurück.

    Dann steht in beiden Darstellungen „0 von 2 Antworten seit …“, als wäre das
    Fenster ganz gelesen — und die dritte, ältere Antwort wird nie aufgeräumt.
    """
    from falzmarke import ablage as _ablage
    from falzmarke import postfach as _postfach_modul

    monkeypatch.setattr(_postfach_modul, "GRENZE", 2)
    lage = dict(eingang=[_eingang_438("<alt@example.org>", "Alt")],
                gesendet=[_antwort_438("<alt@example.org>", tage=3),
                          _antwort_438("<x@example.org>", tage=2),
                          _antwort_438("<y@example.org>", tage=1)])
    with _ablage_lage(monkeypatch, **lage)[1] as sitzung:
        bericht = _ablage.plane(sitzung, wunsch="Archiv", heute=_HEUTE_438.date())
    assert any("nur die neuesten 2 von 3" in h for h in bericht.hinweise), \
        "Kontrollprobe: unsabotiert muss die Kappung im Bericht stehen"
    assert bericht.zuege == (), "die Probe trifft nicht: die alte Antwort war doch dabei"

    monkeypatch.setattr(_ablage, "_kappungen", lambda sitzung: ())
    with _ablage_lage(monkeypatch, **lage)[1] as sitzung:
        stumm = _ablage.plane(sitzung, wunsch="Archiv", heute=_HEUTE_438.date())
    assert stumm.hinweise == (), "`_kappungen` ist nicht die Stelle, die den Hinweis setzt"
    assert _ablage.als_json(stumm)["hinweise"] == [] \
        and not [z for z in _ablage.zeilen(stumm) if z.startswith("HINWEIS")], \
        "ein zweiter Weg setzt den Hinweis — dann belegt die Sabotage ihn nicht"
    assert stumm.antworten == 2, "die Sabotage hat mehr getroffen als den Hinweis"


def test_ohne_den_grund_wandert_die_post_in_den_archive_ordner(monkeypatch, tmp_path, capsys):
    """Sabotage an genau einer Stelle: `ablage_aus_profil` meldet die
    Mehrdeutigkeit wieder als blankes `None`.

    Dann ist sie für `ablageordner` von „kein Profil nennt das Feld“ nicht zu
    unterscheiden, der Lauf nimmt `\\Archive` — und mit `--machen` liegt die
    Post in einem Ordner, den keines der beiden Profile verlangt hat. Genau
    diese Fassung hatte #435.
    """
    import json

    from falzmarke import cli as _cli
    from falzmarke import postfach as _postfach_modul

    for name, ziel in (("eins", "Archiv/A"), ("zwei", "Archiv/B")):
        (tmp_path / f"{name}.yaml").write_text(
            f"email:\n  absender: joe@example.org\n  ablage: {ziel}\n", encoding="utf-8")

    def lauf():
        from imap_attrappe import ImapAttrappe

        attrappe = ImapAttrappe(
            {"INBOX": [_eingang_438("<a@example.org>")],
             "Gesendete Elemente": [_antwort_438("<a@example.org>")]},
            sonder={"INBOX": "", "Gesendete Elemente": "\\Sent", "Archiv": "\\Archive"},
            verschieben_erlaubt=True)
        monkeypatch.setattr(_postfach_modul, "IMAP_KLASSE", attrappe)
        code = _cli.main(["aufraeumen", "--absender", "joe@example.org",
                          "--profiles", str(tmp_path), "--machen", "--json"])
        return attrappe, code, json.loads(capsys.readouterr().out)[0]

    attrappe, code, eintrag = lauf()
    assert code == _cli.EXIT_UMGEBUNG and eintrag["grund"], \
        "Kontrollprobe: unsabotiert muss die Mehrdeutigkeit ein Grund sein"
    assert len(attrappe.ordner["INBOX"]) == 1 and len(attrappe.ordner["Archiv"]) == 0

    echtes = _cli.ablage_aus_profil
    monkeypatch.setattr(_cli, "ablage_aus_profil",
                        lambda adresse, zusatz=None: (echtes(adresse, zusatz)[0], None))
    attrappe, code, eintrag = lauf()
    assert code == _cli.EXIT_OK and eintrag["grund"] is None, \
        "der Grund kommt nicht aus `ablage_aus_profil`"
    assert eintrag["ablage"] == "Archiv" and eintrag["verschoben"] == 1, \
        "ohne den Grund muss die Post nach `\\Archive` wandern — sonst hält sie etwas anderes"
    assert len(attrappe.ordner["Archiv"]) == 1


# ── #541: `aufraeumen --alle` — Konten aus den Profilen ─────────────────────
#
# `tests/test_ablage.py` hält fest, was der Lauf tut. Hier wird je Zusage eine
# Zeile des heutigen Codes gekippt, und die Probe muss dort anschlagen. Jede
# Probe läuft erst unsabotiert (Kontrollprobe), dann sabotiert.

def _alle_541(monkeypatch, tmp_path, capsys, *, profile, attrappen, argumente=("--json",)):
    """`aufraeumen --alle` über Profile in `tmp_path`; zurück kommen Exit und stdout.

    Die Verbindungen gehen der Reihe nach an `attrappen`. Ist keine mehr da, wird
    die Verbindung abgelehnt: Ein Konto, das gar nicht hätte geöffnet werden
    dürfen, taucht dann als `NICHT GEPRÜFT` auf, statt den Test mit einem
    `IndexError` zu beenden, den keine Zusicherung erklärt.
    """
    from falzmarke import cli as _cli
    from falzmarke import postfach as _postfach_modul

    from imap_attrappe import ImapAttrappe

    for name, (absender, ablage_wert) in profile.items():
        zeile = f"  ablage: {ablage_wert}\n" if ablage_wert else ""
        (tmp_path / f"{name}.yaml").write_text(
            f"email:\n  absender: {absender}\n{zeile}", encoding="utf-8")
    # Ohne diese Einengung reichte der Suchweg bis in `~/.config` des Rechners.
    monkeypatch.setattr(_cli, "profil_verzeichnisse", lambda *a, **kw: [tmp_path])
    rest = list(attrappen)
    abgelehnt = ImapAttrappe({}, verbindungsfehler=ConnectionRefusedError("abgelehnt"))
    monkeypatch.setattr(_postfach_modul, "IMAP_KLASSE",
                        lambda *a, **kw: (rest.pop(0) if rest else abgelehnt)(*a, **kw))
    code = _cli.main(["aufraeumen", "--alle", "--profiles", str(tmp_path), *argumente])
    return code, capsys.readouterr().out


def _konto_541(kennung, *, ordner=("Archiv",), verschieben=True):
    from datetime import datetime, timedelta, timezone

    from imap_attrappe import ImapAttrappe, nachricht

    jetzt = datetime.now(timezone.utc)
    ankunft, gesendet = jetzt - timedelta(days=5), jetzt - timedelta(days=1)
    return ImapAttrappe(
        {"INBOX": [(nachricht(an="a@example.de", von="kunde@example.de", betreff="Angebot S1",
                              datum=ankunft, kennung=kennung), ankunft)],
         "Gesendete Elemente": [(nachricht(an="kunde@example.de", betreff="AW: Angebot S1",
                                           datum=gesendet, kennung="<eigene@example.de>",
                                           kopf={"In-Reply-To": kennung}), gesendet)]},
        sonder={"INBOX": "", "Gesendete Elemente": "\\Sent", **{o: "" for o in ordner}},
        verschieben_erlaubt=verschieben)


def test_ohne_den_ablage_filter_wird_auch_das_konto_ohne_ablage_geoeffnet(
        monkeypatch, tmp_path, capsys):
    """Sabotage an genau einer Stelle: `konten_aus_profilen` zählt jede Adresse
    als „mit Ablage“. Dann wird das Konto, das absichtlich keine hat, geöffnet
    und fällt als `NICHT GEPRÜFT` auf, statt unter „übersprungen“ zu stehen."""
    import json

    from falzmarke import cli as _cli

    profile = {"eins": ("a@example.de", "Archiv"), "zwei": ("c@example.de", None)}

    def probe(unterverzeichnis):
        ziel = tmp_path / unterverzeichnis
        ziel.mkdir()
        code, aus = _alle_541(monkeypatch, ziel, capsys, profile=profile,
                              attrappen=[_konto_541("<a@example.de>")])
        bericht = json.loads(aus)
        assert code == _cli.EXIT_OK and bericht["uebersprungen"] == ["c@example.de"], \
            f"das Konto ohne `ablage` wurde nicht übersprungen: Exit {code}, {bericht}"

    probe("heil")
    monkeypatch.setattr(_cli, "konten_aus_profilen", _zeile_ersetzt(
        _cli, "konten_aus_profilen", "if isinstance(wert, str) and wert.strip():", "if True:"))
    with pytest.raises(AssertionError, match="nicht übersprungen"):
        probe("sabotiert")


def test_ohne_den_exit_code_bleibt_ein_nicht_geprueftes_konto_unbemerkt(
        monkeypatch, tmp_path, capsys):
    """Sabotage an genau einer Stelle: `befehl_aufraeumen` gibt immer 0 zurück.
    Dann sieht der Zeitplan nie, dass ein Konto nicht geprüft wurde."""
    from falzmarke import cli as _cli

    profile = {"eins": ("a@example.de", "Archiv/{jahr}"), "zwei": ("b@example.de", "Archiv")}

    def probe(unterverzeichnis):
        ziel = tmp_path / unterverzeichnis
        ziel.mkdir()
        code, _ = _alle_541(monkeypatch, ziel, capsys, profile=profile, attrappen=[
            _konto_541("<a@example.de>", ordner=("Archiv/1999",)), _konto_541("<b@example.de>")])
        assert code == _cli.EXIT_UMGEBUNG, f"Exit {code} trotz `NICHT GEPRÜFT`"

    probe("heil")
    monkeypatch.setattr(_cli, "befehl_aufraeumen", _zeile_ersetzt(
        _cli, "befehl_aufraeumen",
        "return EXIT_UMGEBUNG if any(b.grund for b in berichte) else EXIT_OK",
        "return EXIT_OK"))
    with pytest.raises(AssertionError, match="trotz `NICHT GEPRÜFT`"):
        probe("sabotiert")


def test_ohne_weiterlaufen_haelt_ein_nicht_geprueftes_konto_die_anderen_an(
        monkeypatch, tmp_path, capsys):
    """Sabotage an genau einer Stelle: Der Lauf bricht nach dem ersten Konto mit
    Grund ab. Dann bleibt die beantwortete Post der übrigen Konten liegen."""
    from falzmarke import cli as _cli

    profile = {"eins": ("a@example.de", "Archiv/{jahr}"), "zwei": ("b@example.de", "Archiv")}

    def probe(unterverzeichnis):
        ziel = tmp_path / unterverzeichnis
        ziel.mkdir()
        heil = _konto_541("<b@example.de>")
        _alle_541(monkeypatch, ziel, capsys, profile=profile, argumente=("--machen", "--json"),
                  attrappen=[_konto_541("<a@example.de>", ordner=("Archiv/1999",)), heil])
        assert len(heil.ordner["Archiv"]) == 1, "das zweite Konto hat nicht verschoben"

    probe("heil")
    monkeypatch.setattr(_cli, "befehl_aufraeumen", _zeile_ersetzt(
        _cli, "befehl_aufraeumen", "berichte.append(ablage_modul.raeume_auf(",
        "if any(b.grund for b in berichte):\n            break\n"
        "        berichte.append(ablage_modul.raeume_auf("))
    with pytest.raises(AssertionError, match="zweite Konto hat nicht verschoben"):
        probe("sabotiert")


def test_alle_mit_machen_im_trockenlauf_schlaegt_die_sperrende_attrappe_an(
        monkeypatch, tmp_path, capsys):
    """Sabotage an genau einer Stelle: `--alle` reicht `machen=True` weiter, auch
    ohne `--machen`. Die Attrappe, die jedes Verschieben verbietet, muss dann anschlagen."""
    from falzmarke import cli as _cli

    profile = {"eins": ("a@example.de", "Archiv")}

    def probe(unterverzeichnis):
        ziel = tmp_path / unterverzeichnis
        ziel.mkdir()
        return _alle_541(monkeypatch, ziel, capsys, profile=profile, argumente=("--json",),
                         attrappen=[_konto_541("<a@example.de>", verschieben=False)])

    code, _ = probe("heil")
    assert code == _cli.EXIT_OK
    monkeypatch.setattr(_cli, "befehl_aufraeumen", _zeile_ersetzt(
        _cli, "befehl_aufraeumen", "machen=args.machen,", "machen=True,"))
    with pytest.raises(AssertionError, match="readonly|UID MOVE"):
        probe("sabotiert")


def test_ohne_die_abweisung_laeuft_alle_mit_einem_einzelkonto_schalter(
        monkeypatch, tmp_path, capsys):
    """Sabotage an genau einer Stelle: Die Schalterliste wird nicht mehr geprüft."""
    from falzmarke import cli as _cli

    def probe(unterverzeichnis):
        ziel = tmp_path / unterverzeichnis
        ziel.mkdir()
        code, _ = _alle_541(monkeypatch, ziel, capsys, profile={"eins": ("a@example.de", "Archiv")},
                            argumente=("--trotz-faehnchen",), attrappen=[_konto_541("<a@example.de>")])
        assert code == _cli.EXIT_EINGABE, f"Exit {code}: --alle lief mit --trotz-faehnchen"

    probe("heil")
    monkeypatch.setattr(_cli, "befehl_aufraeumen", _zeile_ersetzt(
        _cli, "befehl_aufraeumen", "if gesetzt:", "if False:"))
    with pytest.raises(AssertionError, match="lief mit --trotz-faehnchen"):
        probe("sabotiert")


def test_ohne_die_leerpruefung_ist_ein_lauf_ohne_konten_gruen(monkeypatch, tmp_path, capsys):
    """Sabotage an genau einer Stelle: Die Prüfung auf „kein Konto gefunden“ entfällt.
    Ein Zeitplan, der nichts prüft, meldet dann Exit 0."""
    from falzmarke import cli as _cli

    def probe(unterverzeichnis):
        ziel = tmp_path / unterverzeichnis
        ziel.mkdir()
        code, _ = _alle_541(monkeypatch, ziel, capsys, profile={"eins": ("c@example.de", None)},
                            attrappen=[])
        assert code == _cli.EXIT_UMGEBUNG, f"Exit {code} ohne ein einziges geprüftes Konto"

    probe("heil")
    monkeypatch.setattr(_cli, "befehl_aufraeumen", _zeile_ersetzt(
        _cli, "befehl_aufraeumen", "if not adressen:", "if False:"))
    with pytest.raises(AssertionError, match="ohne ein einziges geprüftes Konto"):
        probe("sabotiert")


# ── Review #542: `--alle` gegen echte Profile ───────────────────────────────
#
# Jede Sabotage stellt an genau einer Stelle den Stand von #541 wieder her:
# Beispiele zählen mit, eine kaputte Datei bricht den Lauf ab, ein unlesbares
# Profil bleibt grün, der Text verschweigt die übersprungenen Adressen.

def test_ohne_den_beispielfilter_meldet_alle_das_musterkonto(monkeypatch, tmp_path, capsys):
    """Sabotage an genau einer Stelle: `_email_abschnitte` liest auch die
    mitgelieferten Beispiele. Dann steht `muster@example.de` im Bericht, wie im
    ersten Zeitplanlauf vom 05.11.2026."""
    import json

    from falzmarke import cli as _cli

    def probe(unterverzeichnis):
        wurzel = tmp_path / unterverzeichnis
        typst = wurzel / "typst"
        (typst / "profiles").mkdir(parents=True)
        (wurzel / "vorgang").mkdir()
        (typst / "profiles" / "example.yaml").write_text(
            "email:\n  absender: muster@example.de\n", encoding="utf-8")
        monkeypatch.setattr(_cli, "TYPST_DIR", typst)
        monkeypatch.setenv("XDG_CONFIG_HOME", str(wurzel / "xdg"))
        monkeypatch.delenv("FALZMARKE_PROFILES", raising=False)
        monkeypatch.chdir(wurzel / "vorgang")
        code = _cli.main(["aufraeumen", "--alle", "--json"])
        bericht = json.loads(capsys.readouterr().out)
        assert "muster@example.de" not in bericht["uebersprungen"], \
            f"das Beispielprofil zählt als Konto: {bericht}"
        assert code == _cli.EXIT_UMGEBUNG, "Kontrollprobe: ohne eigenes Profil kein Konto"

    probe("heil")
    monkeypatch.setattr(_cli, "_email_abschnitte", _zeile_ersetzt(
        _cli, "_email_abschnitte", "if pfad.parent.resolve() == beispiele:", "if False:"))
    with pytest.raises(AssertionError, match="Beispielprofil zählt als Konto"):
        probe("sabotiert")


def _alle_542_kaputt(monkeypatch, tmp_path, capsys, unterverzeichnis, datei, inhalt: bytes):
    """Ein heiles Konto und eine kaputte Datei daneben; zurück kommen Exit und Bericht."""
    import json

    ziel = tmp_path / unterverzeichnis
    ziel.mkdir()
    (ziel / datei).write_bytes(inhalt)
    code, aus = _alle_541(monkeypatch, ziel, capsys, profile={"eins": ("a@example.de", "Archiv")},
                          attrappen=[_konto_541("<a@example.de>")])
    return code, json.loads(aus)


def test_ohne_unicodedecodeerror_nennt_ein_latin1_profil_den_falschen_grund(
        monkeypatch, tmp_path, capsys):
    """Sabotage an genau einer Stelle: Das `except` fängt `UnicodeDecodeError`
    nicht mehr — wie in #541, wo nur `OSError` und `yaml.YAMLError` standen.

    Bis #551 brach der Lauf dann ab. Seitdem fängt der `ValueError`-Zweig auch
    `UnicodeDecodeError` (eine Unterklasse), und was bleibt, ist der Grund: Der
    Betreiber soll „kein UTF-8“ lesen, nicht „kein gültiges YAML“."""
    from falzmarke import cli as _cli

    latin = "email:\n  absender: jörg@example.de\n".encode("latin-1")

    def probe(unterverzeichnis):
        code, bericht = _alle_542_kaputt(monkeypatch, tmp_path, capsys, unterverzeichnis,
                                         "latin.yaml", latin)
        assert code == _cli.EXIT_UMGEBUNG, f"Kontrollprobe: Exit {code}"
        assert bericht["unlesbar"] == ["latin.yaml: kein UTF-8"], f"falscher Grund: {bericht}"

    probe("heil")
    monkeypatch.setattr(_cli, "_email_abschnitte", _zeile_ersetzt(
        _cli, "_email_abschnitte", "except UnicodeDecodeError:", "except LookupError:"))
    with pytest.raises(AssertionError, match="falscher Grund"):
        probe("sabotiert")


def test_ohne_den_abschnitt_waechter_bricht_ein_listenprofil_den_lauf_ab(
        monkeypatch, tmp_path, capsys):
    """Sabotage an genau einer Stelle: Die oberste Ebene wird nicht mehr geprüft —
    der Stand von `ablage_aus_profil` in #541. `list.get` bricht dann alles ab."""
    from falzmarke import cli as _cli

    liste = b"- a@example.de\n"
    code, bericht = _alle_542_kaputt(monkeypatch, tmp_path, capsys, "heil", "liste.yaml", liste)
    assert code == _cli.EXIT_UMGEBUNG and bericht["unlesbar"] == [
        "liste.yaml: oberste Ebene ist list, kein Abschnitt"], f"Kontrollprobe: {code}, {bericht}"
    monkeypatch.setattr(_cli, "_email_abschnitte", _zeile_ersetzt(
        _cli, "_email_abschnitte", "if not isinstance(profil, dict):", "if False:"))
    with pytest.raises(AttributeError, match="'list' object has no attribute 'get'"):
        _alle_542_kaputt(monkeypatch, tmp_path, capsys, "sabotiert", "liste.yaml", liste)


def test_ohne_die_unlesbar_sperre_bleibt_ein_unlesbares_profil_gruen(
        monkeypatch, tmp_path, capsys):
    """Sabotage an genau einer Stelle: Ein unlesbares Profil ändert den Exit-Code
    nicht. Dann meldet der Zeitplan grün, obwohl ein Konto fehlen kann.

    Bis #551 hing der Exit-Code an einer eigenen Abfrage in `befehl_aufraeumen`.
    Seitdem trägt jeder Bericht den Grund aus `ablage_aus_profil`; die Abfrage
    war tot und ist entfallen. Gekippt wird deshalb die Sperre selbst."""
    from falzmarke import cli as _cli

    def probe(unterverzeichnis):
        code, bericht = _alle_542_kaputt(monkeypatch, tmp_path, capsys, unterverzeichnis,
                                         "liste.yaml", b"- a@example.de\n")
        assert bericht["unlesbar"], f"Kontrollprobe: nichts als unlesbar gemeldet: {bericht}"
        assert code == _cli.EXIT_UMGEBUNG, f"Exit {code} trotz unlesbarem Profil"

    probe("heil")
    monkeypatch.setattr(_cli, "ablage_aus_profil", _zeile_ersetzt(
        _cli, "ablage_aus_profil", "    if unlesbar:", "    if False:"))
    with pytest.raises(AssertionError, match="trotz unlesbarem Profil"):
        probe("sabotiert")


def test_ohne_die_meldung_im_leeren_zweig_fehlen_die_uebersprungenen(
        monkeypatch, tmp_path, capsys):
    """Sabotage an genau einer Stelle: Der Zweig ohne Konto mit Ablage kehrt
    zurück, ohne die ÜBERSPRUNGEN-Zeilen zu schreiben — der Stand von #541."""
    from falzmarke import cli as _cli

    def probe_text(unterverzeichnis):
        ziel = tmp_path / unterverzeichnis
        ziel.mkdir()
        code, aus = _alle_541(monkeypatch, ziel, capsys,
                              profile={"drei": ("c@example.de", None)}, attrappen=[], argumente=())
        assert code == _cli.EXIT_UMGEBUNG, f"Kontrollprobe: Exit {code}"
        assert "ÜBERSPRUNGEN  c@example.de" in aus, f"ÜBERSPRUNGEN fehlt im Text: {aus!r}"

    probe_text("heil")
    monkeypatch.setattr(_cli, "befehl_aufraeumen", _zeile_ersetzt(
        _cli, "befehl_aufraeumen",
        "_melde_uebersprungen(uebersprungen, unlesbar)\n                sys.stdout.flush()",
        "pass\n                sys.stdout.flush()"))
    with pytest.raises(AssertionError, match="ÜBERSPRUNGEN fehlt im Text"):
        probe_text("sabotiert")


# ── Nachreview #546 (#551): unlesbar heißt nichts verschieben ──────────────
#
# Jede Sabotage stellt an genau einer Stelle den Stand von #546 wieder her.

def test_ohne_valueerror_bricht_ein_profil_mit_ungueltigem_datum_den_lauf_ab(
        monkeypatch, tmp_path, capsys):
    """Sabotage an genau einer Stelle: Das `except` fängt `ValueError` nicht mehr.
    `yaml.safe_load` wirft es bei `datum: 2026-02-30` nackt, nicht als `YAMLError`."""
    from falzmarke import cli as _cli

    datum = b"datum: 2026-02-30\n"
    code, bericht = _alle_542_kaputt(monkeypatch, tmp_path, capsys, "heil", "datum.yaml", datum)
    assert code == _cli.EXIT_UMGEBUNG and bericht["unlesbar"] == [
        "datum.yaml: kein gültiges YAML"], f"Kontrollprobe: {code}, {bericht}"
    monkeypatch.setattr(_cli, "_email_abschnitte", _zeile_ersetzt(
        _cli, "_email_abschnitte", "except (yaml.YAMLError, ValueError):",
        "except yaml.YAMLError:"))
    with pytest.raises(ValueError, match="out of range"):
        _alle_542_kaputt(monkeypatch, tmp_path, capsys, "sabotiert", "datum.yaml", datum)


def test_ohne_die_unlesbar_sperre_verschiebt_alle_trotz_verdecktem_profil(
        monkeypatch, tmp_path, capsys):
    """Sabotage an genau einer Stelle: `ablage_aus_profil` übergeht unlesbare
    Profile wieder — der Stand von #546. Dann verschiebt `--machen` das lesbare
    Konto, obwohl die Latin-1-Datei für dieselbe Adresse eine andere Ablage nennt."""
    import json

    from falzmarke import cli as _cli

    latin = "email:\n  absender: a@example.de\n  ablage: Jörg\n".encode("latin-1")

    def probe(unterverzeichnis):
        ziel = tmp_path / unterverzeichnis
        ziel.mkdir()
        (ziel / "latin.yaml").write_bytes(latin)
        code, aus = _alle_541(monkeypatch, ziel, capsys, profile={"eins": ("a@example.de", "Archiv")},
                              argumente=("--machen", "--json"),
                              attrappen=[_konto_541("<a@example.de>")])
        konto = json.loads(aus)["konten"][0]
        assert konto["verschoben"] == 0, f"verschoben trotz unlesbarem Profil: {konto}"
        assert "latin.yaml" in konto["grund"], f"Kontrollprobe: {code}, {konto}"

    probe("heil")
    monkeypatch.setattr(_cli, "ablage_aus_profil", _zeile_ersetzt(
        _cli, "ablage_aus_profil", "    if unlesbar:", "    if False:"))
    with pytest.raises(AssertionError, match="verschoben trotz unlesbarem Profil"):
        probe("sabotiert")


# ── #478: Fähnchen, benannte Mails, Jahresordner ────────────────────────────
#
# Jede Sabotage baut den Stand vor #478 an genau einer Stelle nach: Die Mail
# wandert, statt liegen zu bleiben, oder der Rest des Laufs geht still weiter.

def _lauf_478(monkeypatch, eingang, *, gesendet=(), ordner=("Archiv",), **optionen):
    """Ein Lauf mit `--machen` über einer frischen Attrappe; zurück kommt sie samt Bericht."""
    from falzmarke import ablage as _ablage
    from falzmarke import postfach as _postfach_modul

    from imap_attrappe import ImapAttrappe

    attrappe = ImapAttrappe(
        {"INBOX": list(eingang), "Gesendete Elemente": list(gesendet)},
        sonder={"INBOX": "", "Gesendete Elemente": "\\Sent", **{n: "" for n in ordner}},
        verschieben_erlaubt=True)
    monkeypatch.setattr(_postfach_modul, "IMAP_KLASSE", attrappe)
    wunsch = optionen.pop("wunsch", "Archiv")
    if "uids" in optionen:
        # Der Wert der Attrappe, wie die Anzeige ihn nennt: `raeume_auf` verlangt ihn
        # mit UIDs und `machen` (Nachreview #502, Befund 2).
        optionen.setdefault("uidvalidity", attrappe.uidvalidity)
    return attrappe, _ablage.raeume_auf("joe@example.org", wunsch=wunsch, machen=True,
                                        umgebung={}, **optionen)


def _bleibt_im_eingang_478(attrappe, bericht, anzahl):
    assert not attrappe.befehle("UID MOVE"), \
        f"UID MOVE gesendet: {attrappe.befehle('UID MOVE')}"
    assert len(attrappe.ordner["INBOX"]) == anzahl and bericht.verschoben == 0


def test_ohne_den_faehnchen_zweig_wandert_die_mail_mit_faehnchen(monkeypatch):
    from falzmarke import ablage as _ablage

    def probe():
        attrappe, bericht = _lauf_478(
            monkeypatch, [(*_eingang_438("<f@example.org>"), "\\Flagged")],
            gesendet=[_antwort_438("<f@example.org>")])
        _bleibt_im_eingang_478(attrappe, bericht, 1)

    probe()
    monkeypatch.setattr(_ablage, "_ziele_zuordnen", _zeile_ersetzt(
        _ablage, "_ziele_zuordnen", 'liegen.append(Liegt(zug, "Fähnchen"))', "gehen.append(zug)"))
    with pytest.raises(AssertionError, match="UID MOVE gesendet"):
        probe()


def test_ohne_den_zweig_fuer_unbekannte_flags_wandert_die_mail(monkeypatch):
    from falzmarke import ablage as _ablage
    from falzmarke import postfach as _postfach_modul

    from imap_attrappe import ImapAttrappe

    def probe():
        attrappe = ImapAttrappe(
            {"INBOX": [_eingang_438("<u@example.org>")],
             "Gesendete Elemente": [_antwort_438("<u@example.org>")]},
            sonder={"INBOX": "", "Gesendete Elemente": "\\Sent", "Archiv": ""},
            verschieben_erlaubt=True, ohne_flags=True)
        monkeypatch.setattr(_postfach_modul, "IMAP_KLASSE", attrappe)
        bericht = _ablage.raeume_auf("joe@example.org", wunsch="Archiv", machen=True,
                                     umgebung={})
        _bleibt_im_eingang_478(attrappe, bericht, 1)

    probe()
    monkeypatch.setattr(_ablage, "_ziele_zuordnen", _zeile_ersetzt(
        _ablage, "_ziele_zuordnen",
        'liegen.append(Liegt(zug, "Fähnchen unbekannt, der Server nannte keine Flags"))',
        "gehen.append(zug)"))
    with pytest.raises(AssertionError, match="UID MOVE gesendet"):
        probe()


def test_ohne_die_sperre_fuer_fehlende_uids_wandert_der_rest(monkeypatch):
    from falzmarke import ablage as _ablage

    def probe():
        attrappe, bericht = _lauf_478(monkeypatch, [_eingang_438("<b@example.org>")],
                                      uids=["101", "999"])
        _bleibt_im_eingang_478(attrappe, bericht, 1)
        assert "UID 999" in bericht.grund

    probe()
    monkeypatch.setattr(_ablage, "plane_benannt", _zeile_ersetzt(
        _ablage, "plane_benannt", "    elif fehlen:", "    elif False:"))
    with pytest.raises(AssertionError, match="UID MOVE gesendet"):
        probe()


def test_ohne_alles_oder_nichts_wandert_die_mail_mit_vorhandenem_jahresordner(monkeypatch):
    """Die naheliegende Fassung: Wer keinen Jahresordner hat, wird übergangen,
    der Rest wandert. Dann fehlt die Mail von 2025 sogar im Bericht."""
    from falzmarke import ablage as _ablage

    from imap_attrappe import nachricht

    alt = datetime(2025, 12, 10, 12, 0, tzinfo=timezone.utc)
    eingang = [(nachricht(an="joe@example.org", betreff="Alt", datum=alt,
                          kennung="<alt@example.org>"), alt),
               _eingang_438("<neu@example.org>", "Neu")]

    def probe():
        attrappe, bericht = _lauf_478(monkeypatch, eingang,
                                      gesendet=[_antwort_438("<alt@example.org>", tage=2),
                                                _antwort_438("<neu@example.org>", tage=1)],
                                      ordner=("Archiv/2026",), wunsch="Archiv/{jahr}")
        _bleibt_im_eingang_478(attrappe, bericht, 2)
        assert "„Archiv/2025“" in bericht.grund

    probe()
    monkeypatch.setattr(_ablage, "_ziele_zuordnen", _zeile_ersetzt(
        _ablage, "_ziele_zuordnen", "            fehlend.append(grund)",
        "            continue"))
    with pytest.raises(AssertionError, match="UID MOVE gesendet"):
        probe()


def test_ohne_den_zweig_fuer_fehlende_ankunft_bricht_jahr_den_lauf_ab(monkeypatch):
    """Ohne INTERNALDATE ist das Jahr nicht zu bestimmen. Der Zweig legt die Mail
    zu den liegenden; ohne ihn endet der Lauf in einem Traceback statt in einem Satz."""
    from falzmarke import ablage as _ablage
    from falzmarke import postfach as _postfach_modul

    monkeypatch.setattr(_postfach_modul, "_ankunft", lambda *teile: None)

    def probe():
        attrappe, bericht = _lauf_478(monkeypatch, [_eingang_438("<j@example.org>")],
                                      uids=["101"], ordner=("Archiv/2026",),
                                      wunsch="Archiv/{jahr}")
        _bleibt_im_eingang_478(attrappe, bericht, 1)
        ((_, grund),) = bericht.liegen
        assert grund.startswith("ohne Ankunftsdatum")

    probe()
    monkeypatch.setattr(_ablage, "_ziele_zuordnen", _zeile_ersetzt(
        _ablage, "_ziele_zuordnen", "        if zug.ankunft is None:", "        if False:"))
    with pytest.raises(AttributeError, match="astimezone"):
        probe()


def test_ohne_den_rest_der_antwortzeile_geht_das_faehnchen_hinter_dem_literal_verloren(
        monkeypatch):
    """Steht `FLAGS` hinter dem Literal, liest `postfach.koepfe` es aus dem
    Element danach. Ohne das ist das Fähnchen unbekannt — sicher, aber falsch:
    An einem solchen Server bliebe jede Mail liegen."""
    from falzmarke import postfach as _postfach_modul

    from imap_attrappe import ImapAttrappe

    def probe():
        attrappe = ImapAttrappe({"INBOX": [(*_eingang_438("<h@example.org>"), "\\Flagged")]},
                                flags_hinten=True)
        monkeypatch.setattr(_postfach_modul, "IMAP_KLASSE", attrappe)
        with _postfach_modul.verbinde("joe@example.org", umgebung={}, frist=30) as sitzung:
            (kopf,) = sitzung.koepfe("INBOX")
        assert kopf.fahnen == ("\\flagged",), f"Flags gelesen: {kopf.fahnen!r}"

    probe()
    monkeypatch.setattr(_postfach_modul.Postfach, "koepfe", _zeile_ersetzt(
        _postfach_modul, "Postfach.koepfe", "_fahnen(meta, rest)", "_fahnen(meta)"))
    with pytest.raises(AssertionError, match=r"Flags gelesen: None"):
        probe()


# Nachreview von #494: je Befund eine Sabotage, die den Stand vor der Nacharbeit
# an genau einer Stelle nachbaut.

def _kopf_hinter_dem_literal_494(monkeypatch):
    from falzmarke import postfach as _postfach_modul

    from imap_attrappe import ImapAttrappe

    attrappe = ImapAttrappe({"INBOX": [(*_eingang_438("<h@example.org>"), "\\Seen")]},
                            uid_hinten=True)
    monkeypatch.setattr(_postfach_modul, "IMAP_KLASSE", attrappe)
    with _postfach_modul.verbinde("joe@example.org", umgebung={}, frist=30) as sitzung:
        return sitzung.koepfe("INBOX")


def test_ohne_den_rest_der_antwortzeile_geht_die_uid_hinter_dem_literal_verloren(monkeypatch):
    """Befund 2: `UID` hinter dem Literal. Ohne den Rest fällt der Kopf stumm
    aus der Liste, und `--uid` meldet die Mail als nicht im Eingang."""
    from falzmarke import postfach as _postfach_modul

    def probe():
        koepfe = _kopf_hinter_dem_literal_494(monkeypatch)
        assert [k.uid for k in koepfe] == ["101"], f"Köpfe gelesen: {[k.uid for k in koepfe]}"

    probe()
    monkeypatch.setattr(_postfach_modul.Postfach, "koepfe", _zeile_ersetzt(
        _postfach_modul, "Postfach.koepfe", "_uid(meta, rest)", "_uid(meta)"))
    with pytest.raises(AssertionError, match=r"Köpfe gelesen: \[\]"):
        probe()


def test_ohne_den_rest_der_antwortzeile_geht_die_ankunft_hinter_dem_literal_verloren(
        monkeypatch):
    """Befund 2: `INTERNALDATE` hinter dem Literal. Ohne den Rest ist die
    Ankunft leer, und unter `{jahr}` bliebe jede Mail liegen."""
    from falzmarke import postfach as _postfach_modul

    def probe():
        (kopf,) = _kopf_hinter_dem_literal_494(monkeypatch)
        assert kopf.ankunft is not None, f"Ankunft gelesen: {kopf.ankunft}"

    probe()
    monkeypatch.setattr(_postfach_modul.Postfach, "koepfe", _zeile_ersetzt(
        _postfach_modul, "Postfach.koepfe", "_ankunft(meta, rest)", "_ankunft(meta)"))
    with pytest.raises(AssertionError, match="Ankunft gelesen: None"):
        probe()


@pytest.mark.parametrize(
    ("hinten", "sabotiert", "ersatz", "meldung"),
    [("uid", "_uid(meta, rest)", "_uid(meta)", r"UIDs gelesen: \[\]"),
     ("ankunft", "_ankunft(meta, rest)", "_ankunft(meta)", r"Ankunft gelesen: None")],
    ids=["uid-allein-hinten", "ankunft-allein-hinten"])
def test_ohne_den_rest_geht_je_ein_einzeln_verschobenes_feld_verloren(
        hinten, sabotiert, ersatz, meldung, monkeypatch):
    """#501, Befund 9: Die Attrappe verschiebt `UID` und `INTERNALDATE` auch
    einzeln. Die Sabotage trifft genau das Feld, das hinten steht."""
    from falzmarke import postfach as _postfach_modul
    from test_ablage import (
        test_uid_und_ankunft_werden_je_fuer_sich_hinter_dem_literal_gelesen as probe)

    probe(hinten)                                                          # Kontrolle
    monkeypatch.setattr(_postfach_modul.Postfach, "koepfe", _zeile_ersetzt(
        _postfach_modul, "Postfach.koepfe", sabotiert, ersatz))
    with pytest.raises(AssertionError, match=meldung):
        probe(hinten)


@pytest.mark.parametrize(
    ("hinten", "sabotiert", "ersatz"),
    [("uid", "_ankunft(meta, rest)", "_ankunft(meta)"),
     ("ankunft", "_uid(meta, rest)", "_uid(meta)")],
    ids=["uid-hinten-ankunft-sabotiert", "ankunft-hinten-uid-sabotiert"])
def test_das_vorn_stehende_feld_braucht_den_rest_nicht(
        hinten, sabotiert, ersatz, monkeypatch):
    """Gegenprobe dazu: Steht das andere Feld hinten, bleibt die Sabotage am vorn
    stehenden ohne Wirkung. Nur so trennt die Attrappe die beiden Suchen."""
    from falzmarke import postfach as _postfach_modul
    from test_ablage import (
        test_uid_und_ankunft_werden_je_fuer_sich_hinter_dem_literal_gelesen as probe)

    monkeypatch.setattr(_postfach_modul.Postfach, "koepfe", _zeile_ersetzt(
        _postfach_modul, "Postfach.koepfe", sabotiert, ersatz))
    probe(hinten)


def test_mit_der_alten_regel_gilt_ein_frueherer_jahreszug_als_gesendeter_rest(monkeypatch):
    """Befund 3: `zug_gesendet` wieder mit `or verschoben > 0`."""
    from falzmarke import ablage as _ablage
    from test_ablage import (
        test_bricht_der_zweite_jahreszug_vor_seinem_move_ab_ist_fuer_den_rest_nichts_gesendet
        as probe)

    probe(monkeypatch)                                                     # Kontrolle
    monkeypatch.setattr(_ablage, "raeume_auf", _zeile_ersetzt(
        _ablage, "raeume_auf", "zug_gesendet=isinstance(fehler, ZugAbgebrochen))",
        "zug_gesendet=isinstance(fehler, ZugAbgebrochen)\n"
        "                                    or verschoben > 0)"))
    with pytest.raises(AssertionError, match="zug_gesendet ohne gesendetes MOVE für den Rest"):
        probe(monkeypatch)


def test_mit_dem_alten_text_heisst_der_stand_des_rests_ungeprueft(monkeypatch):
    """Befund 3, die Textseite: ein Zweig für `verschoben`, egal ob gesendet."""
    from falzmarke import ablage as _ablage
    from test_ablage import (
        test_bricht_der_zweite_jahreszug_vor_seinem_move_ab_ist_fuer_den_rest_nichts_gesendet
        as probe)

    probe(monkeypatch)                                                     # Kontrolle
    monkeypatch.setattr(_ablage, "zeilen", _zeile_ersetzt(
        _ablage, "zeilen", "if bericht.verschoben and bericht.zug_gesendet:",
        "if bericht.verschoben:"))
    with pytest.raises(AssertionError, match="ob der Server vom Rest schon etwas bewegt hat"):
        probe(monkeypatch)


def test_ohne_die_sperre_fuer_liegende_benannte_mails_wandert_der_rest(monkeypatch):
    """Befund 5: Eine benannte Mail mit Fähnchen bleibt, die andere wanderte."""
    from falzmarke import ablage as _ablage

    def probe():
        attrappe, bericht = _lauf_478(
            monkeypatch, [_eingang_438("<b1@example.org>"),
                          (*_eingang_438("<b2@example.org>"), "\\Flagged")],
            uids=["101", "102"])
        _bleibt_im_eingang_478(attrappe, bericht, 2)
        assert "--trotz-faehnchen" in bericht.grund

    probe()
    monkeypatch.setattr(_ablage, "plane_benannt", _zeile_ersetzt(
        _ablage, "plane_benannt", "    elif liegen:", "    elif False:"))
    with pytest.raises(AssertionError, match="UID MOVE gesendet"):
        probe()


def test_mit_der_vorgabe_des_eingangs_gelten_bei_entwuerfe_dreissig_tage(monkeypatch):
    """#501, Befund 1: Wäre die 14 aus der 30 abgeleitet statt eigene Vorgabe,
    folgte sie ihr. Die Probe misst die 14 des Entwurfsbuchs, nicht die des Eingangs."""
    from falzmarke import ablage as _ablage
    from test_ablage import test_mit_entwuerfe_gelten_ohne_seit_vierzehn_tage as probe

    probe(monkeypatch)                                                     # Kontrolle
    monkeypatch.setattr(_ablage, "SEIT_TAGEN", 99)
    probe(monkeypatch)                    # die 14 darf der Eingangs-Vorgabe nicht folgen


def test_ohne_entwuerfe_bleiben_es_die_dreissig_des_eingangs(monkeypatch):
    """Gegenprobe zu Befund 1: Die 14 gilt nur mit `--entwuerfe`. Ohne den
    Schalter muss weiter die Vorgabe des Eingangs ankommen."""
    from falzmarke import ablage as _ablage

    angekommen = []
    monkeypatch.setattr(_ablage, "raeume_auf", lambda adresse, **kw: angekommen.append(
        kw["seit_tagen"]) or _ablage.Bericht(
            adresse=adresse, ziel="Archiv", grund="Attrappe", seit=None, antworten=0,
            nicht_im_eingang=0, zuege=(), verschoben=0))
    monkeypatch.setattr(falzmarke, "ablage_aus_profil", lambda adresse, zusatz: ("Archiv", None))
    falzmarke.main(["aufraeumen", "--absender", "a@example.org"])
    assert angekommen == [_ablage.SEIT_TAGEN] == [30], f"Tage im Eingang: {angekommen}"


def test_ohne_die_abweisung_wird_seit_mit_uid_still_uebergangen(monkeypatch, capsys):
    """Befund 6: `--seit 30 --uid 101` lief bis zum Profil weiter."""
    from test_ablage import test_uid_und_seit_schliessen_sich_aus as probe

    probe("30", capsys)                                                    # Kontrolle
    monkeypatch.setattr(falzmarke, "befehl_aufraeumen", _zeile_ersetzt(
        falzmarke, "befehl_aufraeumen",
        "if args.uid is not None and args.seit is not None:", "if False:"))
    with pytest.raises(AssertionError, match="--seit 30 mit --uid nicht abgewiesen"):
        probe("30", capsys)


def test_ohne_dekodieren_steht_der_jahresordner_im_grund_in_server_schreibweise(monkeypatch):
    """#501, Befund 3: Ohne die Dekodierung zeigt der Grund den rohen Namen."""
    from falzmarke import postfach as _postfach_modul
    from test_ablage import test_fehlt_der_jahresordner_nennt_der_grund_den_lesbaren_namen as probe

    probe()                                                                # Kontrolle
    monkeypatch.setattr(_postfach_modul, "utf7_dekodieren", lambda name: name)
    with pytest.raises(AssertionError, match=r"Lesbarer Name fehlt im Grund"):
        probe()


def test_ein_vorab_lesbarer_wunsch_kommt_auch_ohne_dekodieren_lesbar_an(monkeypatch):
    """Gegenprobe dazu: Mit lesbarem Wunsch und ohne Dekodierung zeigt der Grund
    weiter „Geschäft/2025“ — die Probe unterscheidet also Wunsch-Schreibweisen,
    statt jede Dekodierung zu verlangen."""
    from falzmarke import postfach as _postfach_modul
    from test_ablage import test_ein_lesbarer_wunsch_mit_jahr_bleibt_im_grund_lesbar as probe

    monkeypatch.setattr(_postfach_modul, "utf7_dekodieren", lambda name: name)
    probe()


def test_ohne_dekodieren_steht_das_jahresziel_in_server_schreibweise_im_json(monkeypatch):
    """Befund 8, das Ziel des Laufs: `_ziel_vorab` gibt den Wunsch roh zurück."""
    from falzmarke import ablage as _ablage
    from test_ablage import test_jahr_in_server_schreibweise_steht_lesbar_in_text_und_json as probe

    probe()                                                                # Kontrolle
    monkeypatch.setattr(_ablage, "_ziel_vorab", _zeile_ersetzt(
        _ablage, "_ziel_vorab", "return _lesbar(wunsch), None, None", "return wunsch, None, None"))
    with pytest.raises(AssertionError, match="Ablage im JSON: Gesch&AOQ-ft/{jahr}"):
        probe()


def test_ohne_dekodieren_steht_das_ziel_je_zug_in_server_schreibweise_im_json(monkeypatch):
    """Befund 8, das Ziel je Zug: `_ziele_zuordnen` setzt den rohen Namen."""
    from falzmarke import ablage as _ablage
    from test_ablage import test_jahr_in_server_schreibweise_steht_lesbar_in_text_und_json as probe

    probe()                                                                # Kontrolle
    monkeypatch.setattr(_ablage, "_ziele_zuordnen", _zeile_ersetzt(
        _ablage, "_ziele_zuordnen", "ziel=lesbar, ziel_server", "ziel=name, ziel_server"))
    with pytest.raises(AssertionError, match=r"Ziele im JSON: \['Gesch&AOQ-ft/2025'"):
        probe()


@pytest.mark.parametrize("ersatz, meldung", [
    ("return wunsch", r"Grenze verschoben: 'R&Dev-Team' → 'R&Dev-Team'"),
    (('return wunsch if __import__("re").search(r"&[^-]{9,}-", wunsch) '
      "else postfach.utf7_anzeige(wunsch)"),
     r"Grenze verschoben: 'A&Projektakte-B' → 'A&Projektakte-B'"),
], ids=["gar-nicht", "nur-bis-acht"])
def test_ohne_dekodieren_verschiebt_sich_die_grenze_von_lesbar(monkeypatch, ersatz, meldung):
    """#522, Punkt 1: Die Probe hält die gemessene Grenze fest, nicht nur `&-`.
    Dekodiert `_lesbar` gar nicht mehr, muss sie zuerst am Drei-Buchstaben-Fall anschlagen.
    „nur-bis-acht“ lässt Folgen ab neun Zeichen stehen, so weit reichte die erste
    Messung; die Probe muss am Fall mit elf anschlagen (Nachreview von #527, Befund 7)."""
    from falzmarke import ablage as _ablage
    from test_ablage import test_die_bekannte_grenze_von_lesbar as probe

    probe()                                                                # Kontrolle
    monkeypatch.setattr(_ablage, "_lesbar", _zeile_ersetzt(
        _ablage, "_lesbar", "return postfach.utf7_anzeige(wunsch)", ersatz))
    with pytest.raises(AssertionError, match=meldung):
        probe()


def test_ohne_listenkontext_raet_lint_zur_feldzeile(monkeypatch, tmp_path):
    """#544, AC 3: Ohne den Listenkontext kommt der alte Skalar-Rat `an: '…'`
    zurück. Die Probe muss daran anschlagen, bevor jemand ihn übernimmt und zwei
    Empfänger verliert."""
    from falzmarke import lint as _lint
    from test_adressen import test_komma_in_einer_liste_ersetzt_nur_diesen_eintrag as probe

    (tmp_path / "kontrolle").mkdir()
    probe(tmp_path / "kontrolle")                                          # Kontrolle
    monkeypatch.setattr(_lint, "pruefe_adressfeld", _zeile_ersetzt(
        _lint, "pruefe_adressfeld",
        'form = "flow" if roh.startswith("[") else "block"',
        'form = "skalar"'))
    (tmp_path / "sabotage").mkdir()
    with pytest.raises(AssertionError, match=r"kein Listeneintrag im Rat: .*im Frontmatter `an: "):
        probe(tmp_path / "sabotage")


def test_ohne_profilkontext_nennt_der_rat_das_frontmatter(monkeypatch, tmp_path):
    """#544, AC 2: Kippt die Unterscheidung nach Profil, nennt der Rat für
    `email.absender` wieder das Frontmatter. Seit der Nachreview von #571 sagt
    der Aufrufer den Ort; gekippt wird deshalb sein Aufruf."""
    from falzmarke import lint as _lint
    from test_adressen import test_komma_im_absender_nennt_das_profil as probe

    (tmp_path / "kontrolle").mkdir()
    probe(tmp_path / "kontrolle")                                          # Kontrolle
    monkeypatch.setattr(_lint, "pruefe_email_profil", _zeile_ersetzt(
        _lint, "pruefe_email_profil", 'ort="profil")', 'ort="frontmatter")'))
    (tmp_path / "sabotage").mkdir()
    with pytest.raises(AssertionError, match="Frontmatter"):
        probe(tmp_path / "sabotage")


@pytest.mark.parametrize("absender, meldung", [
    (["m@example.de"], r"assert 0 == 1"),
    (["Muster, Max <m@example.de>"], r"nimmt genau eine Adresse, im Profil steht eine Liste"),
], ids=["gueltig", "mit-komma"])
def test_ohne_einzelpruefung_geht_eine_absenderliste_durch(monkeypatch, tmp_path, absender, meldung):
    """Nachreview von #571, Befunde 1 und 2: Fällt die Prüfung „genau eine
    Adresse“ weg, geht `absender: [m@example.de]` ohne Befund durch, und der
    Versand machte daraus `str(list)`. Mit Komma kommt statt des Typ-Befunds der
    Listenrat zurück (Review an PR #573, Punkt 7)."""
    from falzmarke import lint as _lint
    from test_adressen import test_absender_als_liste_ist_ein_fehler as probe

    (tmp_path / "kontrolle").mkdir()
    probe(tmp_path / "kontrolle", absender)                                # Kontrolle
    monkeypatch.setattr(_lint, "pruefe_adressfeld", _zeile_ersetzt(
        _lint, "pruefe_adressfeld", 'if ort == "profil" and not isinstance(wert, str):', "if False:"))
    (tmp_path / "sabotage").mkdir()
    with pytest.raises(AssertionError, match=meldung):
        probe(tmp_path / "sabotage", absender)


def test_ohne_typpruefung_stuerzt_lint_an_cc_yes_ab(monkeypatch, tmp_path):
    """Nachreview von #571, Befund 4: Ohne die Typprüfung stürzt `lint` an
    `cc: yes` ab, wie vor #573, statt einen Befund zu melden."""
    from falzmarke import lint as _lint
    from test_adressen import test_kein_text_und_keine_liste_ist_ein_befund as probe

    fall = ("an: x@example.de\ncc: yes\n", "cc", "ein Wahrheitswert")
    (tmp_path / "kontrolle").mkdir()
    probe(tmp_path / "kontrolle", *fall)                                   # Kontrolle
    monkeypatch.setattr(_lint, "pruefe_adressfeld", _zeile_ersetzt(
        _lint, "pruefe_adressfeld", "if not isinstance(wert, (str, list)):", "if False:"))
    (tmp_path / "sabotage").mkdir()
    with pytest.raises(TypeError, match="'bool' object is not iterable"):
        probe(tmp_path / "sabotage", *fall)


def test_ohne_flow_erkennung_raet_lint_zur_blockzeile(monkeypatch, tmp_path):
    """Nachreview von #571, Befund 3: Hält `lint` jede Liste für eine Blockliste,
    steht in `an: [ … ]` wieder `- '…'`, und das YAML bricht."""
    from falzmarke import lint as _lint
    from test_adressen import test_komma_in_einer_flow_liste_ersetzt_nur_diesen_eintrag as probe

    (tmp_path / "kontrolle").mkdir()
    probe(tmp_path / "kontrolle")                                          # Kontrolle
    monkeypatch.setattr(_lint, "pruefe_adressfeld", _zeile_ersetzt(
        _lint, "pruefe_adressfeld",
        'form = "flow" if roh.startswith("[") else "block"',
        'form = "block"'))
    (tmp_path / "sabotage").mkdir()
    with pytest.raises(AssertionError, match="Blockzeile in einer Flow-Liste"):
        probe(tmp_path / "sabotage")


def test_ohne_listenrat_verliert_der_zwei_adressen_rat_den_eintrag(monkeypatch, tmp_path):
    """Nachreview von #571, Befund 5: Ohne den Listenzweig sagt der Rat bei zwei
    Adressen in einem Listeneintrag nicht mehr, dass nur dieser Eintrag ersetzt wird."""
    from falzmarke import lint as _lint
    from test_adressen import test_zwei_adressen_in_einer_blockliste_ersetzen_nur_diesen_eintrag as probe

    (tmp_path / "kontrolle").mkdir()
    probe(tmp_path / "kontrolle")                                          # Kontrolle
    monkeypatch.setattr(_lint, "_komma_abhilfe", _zeile_ersetzt(
        _lint, "_komma_abhilfe", 'if form != "skalar":', "if False:"))
    (tmp_path / "sabotage").mkdir()
    with pytest.raises(AssertionError, match="wird der Listenkopf"):
        probe(tmp_path / "sabotage")


def test_ohne_folgezeile_wird_die_flow_liste_zur_blockliste(monkeypatch, tmp_path):
    """Review an PR #573, Punkt 1: Sieht `_feldstelle` die Folgezeile nicht an,
    gilt `an:` mit `[ … ]` darunter als Blockliste, und der Rat `- '…'` bricht das YAML."""
    from falzmarke import lint as _lint
    from test_adressen import test_flow_liste_auf_der_folgezeile_ersetzt_nur_diesen_eintrag as probe

    (tmp_path / "kontrolle").mkdir()
    probe(tmp_path / "kontrolle")                                          # Kontrolle
    monkeypatch.setattr(_lint, "_feldstelle", _zeile_ersetzt(
        _lint, "_feldstelle", "if not rest:", "if False:"))
    (tmp_path / "sabotage").mkdir()
    with pytest.raises(AssertionError, match="Blockzeile in einer Flow-Liste"):
        probe(tmp_path / "sabotage")


@pytest.mark.parametrize("probe_name, meldung", [
    ("test_wahrheitswert_in_einem_listeneintrag_ist_ein_typbefund", "got 'bool'"),
    ("test_doppelpunkt_in_einem_listeneintrag_raet_zum_quoten", "got 'dict'"),
], ids=["wahrheitswert", "zuordnung"])
def test_ohne_eintragstyp_stuerzt_der_adressrat_ab(monkeypatch, tmp_path, probe_name, meldung):
    """Review an PR #573, Punkt 2: Ohne die Typprüfung je Eintrag laufen `- yes`
    und `- Firma: Muster <…>` in den Adressrat, und der stürzt an einem Nicht-Text ab."""
    import test_adressen
    from falzmarke import lint as _lint

    probe = getattr(test_adressen, probe_name)
    (tmp_path / "kontrolle").mkdir()
    probe(tmp_path / "kontrolle")                                          # Kontrolle
    monkeypatch.setattr(_lint, "pruefe_adressfeld", _zeile_ersetzt(
        _lint, "pruefe_adressfeld", "if not isinstance(eintrag, str):", "if False:"))
    (tmp_path / "sabotage").mkdir()
    with pytest.raises(TypeError, match=meldung):
        probe(tmp_path / "sabotage")


def test_mit_dem_alten_guard_bleibt_cc_no_still(monkeypatch, tmp_path):
    """Review an PR #573, Punkt 3: Mit `if kopf.get(feld):` fallen `cc: no` und
    `cc: 0` am Aufrufer durch und bekommen keinen Befund."""
    from falzmarke import lint as _lint
    from test_adressen import test_kein_text_und_keine_liste_ist_ein_befund as probe

    fall = ("an: x@example.de\ncc: no\n", "cc", "ein Wahrheitswert")
    (tmp_path / "kontrolle").mkdir()
    probe(tmp_path / "kontrolle", *fall)                                   # Kontrolle
    monkeypatch.setattr(_lint, "pruefe_email_frontmatter", _zeile_ersetzt(
        _lint, "pruefe_email_frontmatter", 'if kopf.get(feld) not in (None, ""):', "if kopf.get(feld):"))
    (tmp_path / "sabotage").mkdir()
    with pytest.raises(AssertionError, match=r"assert 0 == 1"):
        probe(tmp_path / "sabotage", *fall)


def test_ohne_listenkopf_fehlt_im_skalarrat_der_umbau(monkeypatch, tmp_path):
    """Review an PR #573, Punkt 6: Der Rat für `an: 'a, b'` sagte nicht, dass
    `an: …` erst zum Listenkopf `an:` wird."""
    from falzmarke import lint as _lint
    from test_adressen import test_zwei_adressen_im_skalar_nennen_den_listenkopf as probe

    (tmp_path / "kontrolle").mkdir()
    probe(tmp_path / "kontrolle")                                          # Kontrolle
    monkeypatch.setattr(_lint, "_komma_abhilfe", _zeile_ersetzt(
        _lint, "_komma_abhilfe",
        'return (f"zwei Adressen in einem Eintrag: aus `{feld}: …` wird der Listenkopf `{feld}:` "',
        'return (f"zwei Adressen in einem Eintrag: je Adresse eine Zeile der Liste unter `{feld}:` "'))
    (tmp_path / "sabotage").mkdir()
    with pytest.raises(AssertionError, match="wird der Listenkopf"):
        probe(tmp_path / "sabotage")


def test_mit_str_dict_verlieren_die_anlagen_ihre_namen(monkeypatch):
    """Review an PR #573, Punkt 5: Macht `_adressen` aus einer Zuordnung `str(dict)`,
    meldet die Anlagen-Prüfung „{'angebot.pdf': None}“ statt „angebot.pdf“."""
    from falzmarke import lint as _lint
    from test_adressen import test_anlagen_als_zuordnung_liefern_ihre_schluessel as probe

    probe()                                                                # Kontrolle
    monkeypatch.setattr(_lint, "_adressen", _zeile_ersetzt(
        _lint, "_adressen", "return [str(z) for z in (wert or [])]", "return [str(wert)]"))
    with pytest.raises(AssertionError, match=r"\{'angebot.pdf': None\}"):
        probe()


def test_ohne_den_gefundenen_ordner_raet_die_anzeige_je_zug(monkeypatch):
    """Nachreview von #527, Befund 3: der Stand von #527, Wort für Wort."""
    from falzmarke import ablage as _ablage
    from test_ablage import test_mit_jahr_zeigt_der_zug_den_gefundenen_ordner as probe

    probe()                                                                # Kontrolle
    monkeypatch.setattr(_ablage, "_ziele_zuordnen", _zeile_ersetzt(
        _ablage, "_ziele_zuordnen",
        "lesbar = postfach.utf7_anzeige(ordner) if ordner else _lesbar(name)",
        "lesbar = _lesbar(name)"))
    with pytest.raises(AssertionError, match=r"angezeigt: \['R\u0debTeam/2025'"):
        probe()


@pytest.mark.parametrize("funktion, probe_name, neu, alt", [
    ("ablageordner", "test_ungueltiger_servername_in_der_ordnerliste_bricht_den_grund_nicht_ab",
     'f"„{postfach.utf7_anzeige(n)}“" for n, _ in liste[:12]',
     'f"„{postfach.utf7_dekodieren(n)}“" for n, _ in liste[:12]'),
    ("ablageordner",
     "test_ungueltiger_servername_eines_gesperrten_ordners_bricht_den_grund_nicht_ab",
     'f"„{postfach.utf7_anzeige(name)}“ ({herkunft}) trägt "',
     'f"„{postfach.utf7_dekodieren(name)}“ ({herkunft}) trägt "'),
    ("_ziel_vorab", "test_ungueltiger_servername_als_ablage_wandert_und_steht_wie_geliefert",
     "return postfach.utf7_anzeige(ziel), ziel, None",
     "return postfach.utf7_dekodieren(ziel), ziel, None"),
    ("verschiebe", "test_ungueltiger_servername_als_ablage_wandert_und_steht_wie_geliefert",
     'f"MOVE nach „{postfach.utf7_anzeige(ziel)}“"', 'f"MOVE nach „{postfach.utf7_dekodieren(ziel)}“"'),
    ("_ziele_zuordnen", "test_mit_jahr_bricht_ein_ungueltiger_servername_den_lauf_nicht_ab",
     "lesbar = postfach.utf7_anzeige(ordner) if ordner else _lesbar(name)",
     "lesbar = postfach.utf7_dekodieren(ordner) if ordner else _lesbar(name)"),
    ("_kappungen", "test_ungueltiger_servername_im_kappungshinweis_steht_wie_geliefert",
     'f"„{postfach.utf7_anzeige(ordner)}“: nur die neuesten',
     'f"„{postfach.utf7_dekodieren(ordner)}“: nur die neuesten'),
    ("_kappungen", "test_ungueltiger_servername_im_kappungshinweis_steht_wie_geliefert",
     "in „{postfach.utf7_anzeige(ordner)}“: nur {verglichen}",
     "in „{postfach.utf7_dekodieren(ordner)}“: nur {verglichen}"),
], ids=["ordnerliste", "gesperrt", "ziel-vorab", "move", "je-zug", "kappung", "suchkappung"])
def test_ungueltiger_servername_ohne_rueckfall_endet_im_traceback(monkeypatch, funktion,
                                                                  probe_name, neu, alt):
    """Nachreview von #535, Befund 1: Jede Stelle bekommt einzeln die Zeile von
    vorher zurück, das blanke `utf7_dekodieren`. Am Ordner „AT&T-Rechnungen“ eines
    nicht konformen Servers endet der Lauf dann mit genau dem Traceback aus dem
    Review, nicht mit einer verfehlten Zusicherung."""
    import binascii

    import test_ablage
    from falzmarke import ablage as _ablage

    probe = getattr(test_ablage, probe_name)
    probe()                                                                # Kontrolle
    monkeypatch.setattr(_ablage, funktion, _zeile_ersetzt(_ablage, funktion, neu, alt))
    with pytest.raises(binascii.Error, match="Invalid base64-encoded string"):
        probe()


@pytest.mark.parametrize("datei, alt, neu, meldung", [
    ("postfach.py", "„{utf7_anzeige(ordner)}“\", self._v.append",
     "„{utf7_dekodieren(ordner)}“\", self._v.append", r"'postfach\.py:\d+ in ablegen'"),
    ("postfach.py", "„{utf7_anzeige(ordner)}“ nicht lesbar",
     "„{utf7_dekodieren(ordner)}“ nicht lesbar", r"'postfach\.py:\d+ in _waehle'"),
    ("gesendet.py", "anzeige = postfach.utf7_anzeige(ordner)",
     "anzeige = postfach.utf7_dekodieren(ordner)", r"'gesendet\.py:\d+ in pruefe'"),
    ("ablage.py", "return postfach.utf7_anzeige(wunsch)",
     "return postfach.utf7_dekodieren(wunsch)", r"'ablage\.py:\d+ in _lesbar'"),
    ("regeln/__init__.py", None, "\n_dekodiert = utf7_dekodieren\n",
     r"'regeln/__init__\.py:\d+ in <modul>'"),
    ("postfach.py", "        return utf7_dekodieren(name)\n", "        return name\n",
     "utf7_anzeige ruft utf7_dekodieren 0-mal, erwartet 1"),
], ids=["append", "examine", "gesendet", "lesbar", "unterpaket", "anzeige-ohne-dekodieren"])
def test_der_waechter_ueber_utf7_dekodieren_schlaegt_an(monkeypatch, datei, alt, neu, meldung):
    """Nachreview von #535, Befund 1: Der Wächter läuft unverändert, nur über
    sabotierten Quelltext. Jede Sabotage setzt an genau einer Stelle das blanke
    `utf7_dekodieren` zurück, und der Wächter muss genau diese Stelle nennen.
    Die Ausnahme gilt einer Funktion, nicht der Datei: Eine zweite Stelle in
    `postfach.py` wird gemeldet. „anzeige-ohne-dekodieren“ belegt die Zählung:
    Ruft `utf7_anzeige` nichts mehr, wäre ein leerer Fundbericht kein Beleg.

    Die Kontrolle läuft über dieselbe umgeleitete Quellenfunktion, ergänzt um
    einen Kommentar und einen Docstring, die `utf7_dekodieren` nennen: Prosa
    zählt nicht, gelesen wird über `ast`."""
    import test_postfach as tp

    echt = tp._paketquellen
    probe = tp.test_nur_utf7_anzeige_dekodiert_ordnernamen

    def mit(aenderung):
        def quellen(ordner=None):
            ergebnis = echt(ordner)
            if ordner is None:
                aenderung(ergebnis)
            return ergebnis
        return quellen

    def nur_prosa(quellen):
        quellen["cli.py"] += ('\n# utf7_dekodieren(ordner) steht hier nur im Kommentar\n'
                              '"""utf7_dekodieren(ordner) im Docstring"""\n')

    def sabotage(quellen):
        if alt is None:
            quellen[datei] += neu
            return
        assert quellen[datei].count(alt) == 1, f"die Sabotage findet „{alt.strip()}“ nicht"
        quellen[datei] = quellen[datei].replace(alt, neu)

    monkeypatch.setattr(tp, "_paketquellen", mit(nur_prosa))
    probe()                                                                # Kontrolle
    monkeypatch.setattr(tp, "_paketquellen", mit(sabotage))
    with pytest.raises(AssertionError, match=meldung):
        probe()


# #495: Eine UID gilt nur mit der UIDVALIDITY des Eingangs. Jede Sabotage baut
# den Stand vor #495 an genau einer Stelle nach, dazu die beiden Befunde aus
# dem Review von #496, die in `plane_benannt` lagen.

def test_ohne_den_vergleich_mit_der_anzeige_wandert_die_fremde_mail(monkeypatch):
    """Der Stand vor #495: `plane_benannt` sah nur die Zahl."""
    from falzmarke import ablage as _ablage
    from test_ablage import test_wechselt_die_uidvalidity_nach_der_anzeige_wandert_keine as probe

    probe()                                                                # Kontrolle
    monkeypatch.setattr(_ablage, "plane_benannt", _zeile_ersetzt(
        _ablage, "plane_benannt", "    if gewechselt:", "    if False:"))
    with pytest.raises(AssertionError, match="UID MOVE gesendet"):
        probe()


@pytest.mark.parametrize("benannt", [True, False], ids=["uid", "beantwortet"])
def test_ohne_den_vergleich_am_select_geht_das_move_trotz_wechsel_hinaus(monkeypatch, benannt):
    """Der Stand vor #495: `verschiebe` wählte den Eingang und schob."""
    from falzmarke import ablage as _ablage
    from test_ablage import (
        test_wechselt_die_uidvalidity_zwischen_plan_und_select_geht_kein_move_hinaus as probe)

    probe(benannt)                                                         # Kontrolle
    monkeypatch.setattr(_ablage, "verschiebe", _zeile_ersetzt(
        _ablage, "verschiebe", "    if jetzt != uidvalidity:",
        "    if False:"))
    with pytest.raises(AssertionError, match="UID MOVE gesendet"):
        probe(benannt)


def test_ohne_die_sperre_fuer_fehlenden_planwert_geht_das_move_ungeprueft_hinaus(monkeypatch):
    """Nachreview #502, Befund 1: Der Stand davor verglich nur, wenn der Plan einen Wert las."""
    from falzmarke import ablage as _ablage
    from test_ablage import test_ohne_uidvalidity_im_plan_geht_kein_move_hinaus as probe

    probe()                                                                # Kontrolle
    monkeypatch.setattr(_ablage, "verschiebe", _zeile_ersetzt(
        _ablage, "verschiebe", "    if uidvalidity is None:", "    if False:"))
    with pytest.raises(AssertionError, match="UID MOVE gesendet"):
        probe()


def test_ohne_die_pflicht_in_der_funktion_wandert_die_fremde_mail(monkeypatch):
    """Nachreview #502, Befund 2: Der Stand davor prüfte die Pflicht nur in `cli.py`."""
    from falzmarke import ablage as _ablage
    from test_ablage import (
        test_mit_uids_und_machen_verlangt_auch_die_funktion_die_uidvalidity as probe)

    probe()                                                                # Kontrolle
    monkeypatch.setattr(_ablage, "raeume_auf", _zeile_ersetzt(
        _ablage, "raeume_auf", "    if uids is not None and machen and uidvalidity is None:",
        "    if False:"))
    with pytest.raises(AssertionError, match="UID MOVE gesendet"):
        probe()


def test_ohne_die_pflicht_laeuft_uid_mit_machen_ohne_uidvalidity_durch(monkeypatch, capsys):
    """Der Stand vor #495: `--uid … --machen` ohne Wert der Anzeige."""
    from test_ablage import test_uid_mit_machen_verlangt_uidvalidity as probe

    probe(monkeypatch, capsys)                                             # Kontrolle
    monkeypatch.setattr(falzmarke, "befehl_aufraeumen", _zeile_ersetzt(
        falzmarke, "befehl_aufraeumen",
        "        if args.machen and args.uidvalidity is None:", "        if False:"))
    with pytest.raises(AssertionError, match="ohne --uidvalidity nicht abgewiesen"):
        probe(monkeypatch, capsys)


@pytest.mark.parametrize("argumente, anfang, zeile", [
    (["--uidvalidity", "1"], "FEHLER  --uidvalidity gilt nur mit --uid",
     '        if args.uid is None:\n            print("FEHLER  --uidvalidity gilt'),
    (["--uid", "101", "--uidvalidity", "0"], "FEHLER  --uidvalidity braucht eine Zahl ab 1",
     "        if args.uidvalidity < 1:"),
], ids=["ohne-uid", "null"])
def test_ohne_die_cli_pruefung_zu_uidvalidity_laeuft_der_befehl_weiter(
        monkeypatch, capsys, argumente, anfang, zeile):
    """#504, Befund 7: Beide Prüfungen in `cli.py` hatten keine Gegenprobe. Jede Sabotage
    kippt genau eine; der Befehl läuft dann weiter, hier gegen eine Attrappe statt gegen
    den Proxy, damit die Sabotage nie ein echtes Postfach erreicht."""
    from imap_attrappe import ImapAttrappe
    from falzmarke import postfach as _postfach

    def abgewiesen() -> str | None:
        code = falzmarke.main(["aufraeumen", "--absender", "joe@example.org", *argumente])
        fehler = capsys.readouterr().err
        if code == falzmarke.EXIT_EINGABE and fehler.startswith(anfang):
            return None
        return f"nicht abgewiesen: Exit {code}, {fehler!r}"

    monkeypatch.setattr(_postfach, "IMAP_KLASSE", ImapAttrappe(
        {"INBOX": [], "Gesendete Elemente": []},
        sonder={"INBOX": "", "Gesendete Elemente": "\\Sent", "Archiv": "\\Archive"}))
    assert abgewiesen() is None                                            # Kontrolle
    neu = zeile.replace("if args.uid is None:", "if False:").replace(
        "if args.uidvalidity < 1:", "if False:")
    monkeypatch.setattr(falzmarke, "befehl_aufraeumen", _zeile_ersetzt(
        falzmarke, "befehl_aufraeumen", zeile, neu))
    befund = abgewiesen()
    assert befund is not None and befund.startswith("nicht abgewiesen"), \
        "die Sabotage greift nicht: der Befehl wurde trotzdem abgewiesen"


def test_mit_der_alten_regel_verschwindet_der_grund_zum_jahresordner(monkeypatch):
    """Review von #496, Befund 1: Der Grund „bliebe liegen“ ersetzte den zum Jahresordner."""
    from falzmarke import ablage as _ablage
    from test_ablage import (
        test_fehlt_ein_jahresordner_steht_er_neben_der_liegenden_benannten_mail as probe)

    probe()                                                                # Kontrolle
    monkeypatch.setattr(_ablage, "plane_benannt", _zeile_ersetzt(
        _ablage, "plane_benannt", 'grund = f"{grund}; {jahr_grund}" if grund else jahr_grund',
        "grund = grund or jahr_grund"))
    with pytest.raises(AssertionError, match="Jahresordner fehlt im Grund"):
        probe()


def test_mit_der_alten_regel_raet_der_grund_zum_schon_gesetzten_schalter(monkeypatch):
    """Review von #496, Befund 2: der Rat ohne Blick auf `trotz_faehnchen`."""
    from falzmarke import ablage as _ablage
    from test_ablage import test_mit_trotz_faehnchen_raet_der_grund_nicht_zu_trotz_faehnchen as probe

    probe(monkeypatch)                                                     # Kontrolle
    monkeypatch.setattr(_ablage, "plane_benannt", _zeile_ersetzt(
        _ablage, "plane_benannt", "        if not trotz_faehnchen and any(", "        if any("))
    with pytest.raises(AssertionError, match="Rat trotz Schalter"):
        probe(monkeypatch)


# ── #549: Der Antwortentwurf setzt das Fähnchen an der Ursprungsmail ───────
#
# Jede Probe ist ein Test aus `test_postfach_entwurf.py`, der `email --oeffnen`
# ganz durchfährt. Gekippt wird je eine Zeile; die Probe muss mit ihrer
# eigenen Meldung anschlagen, nicht mit irgendeiner. Die Attrappe wirft bei
# einem falschen STORE, aber `faehnchen.setze` fängt jeden Fehler — deshalb
# prüfen die Proben das Protokoll der Attrappe, nie eine Ausnahme.

def test_ohne_den_aufruf_fehlt_das_faehnchen_an_der_antwort(befehl, monkeypatch, capsys):
    """Sabotage an genau einer Stelle: `_setze_faehnchen_mit` kehrt immer um."""
    from test_postfach_entwurf import test_befehl_setzt_das_faehnchen_an_der_beantworteten_mail \
        as probe

    probe(befehl, monkeypatch, capsys)                                      # Kontrolle
    monkeypatch.setattr(falzmarke, "_setze_faehnchen_mit", _zeile_ersetzt(
        falzmarke, "_setze_faehnchen_mit", "if not antwort_auf:", "if True:"))
    with pytest.raises(AssertionError, match="kein Fähnchen gesetzt"):
        probe(befehl, monkeypatch, capsys)


def test_ohne_die_erledigt_pruefung_setzt_es_das_faehnchen_trotzdem(
        befehl, monkeypatch, capsys, tmp_path):
    """Sabotage an genau einer Stelle: `erledigt: ja` wird übergangen."""
    from falzmarke import faehnchen as _faehnchen
    from test_postfach_entwurf import test_befehl_mit_erledigt_setzt_kein_faehnchen as probe

    probe(befehl, monkeypatch, capsys, tmp_path)                            # Kontrolle
    monkeypatch.setattr(_faehnchen, "setze", _zeile_ersetzt(
        _faehnchen, "setze", "if erledigt:", "if False:"))
    with pytest.raises(AssertionError, match="Fähnchen trotz `erledigt: ja`"):
        probe(befehl, monkeypatch, capsys, tmp_path)


def test_mit_einer_verrutschten_uid_trifft_das_faehnchen_die_falsche_mail(
        befehl, monkeypatch, capsys):
    """Sabotage an genau einer Stelle: Die UID des Treffers wird um eins
    verschoben. Das Nachlesen danach liest dieselbe falsche UID und meldet
    „gesetzt“ — nur das Protokoll zeigt den Fehler."""
    from falzmarke import faehnchen as _faehnchen
    from test_postfach_entwurf import test_befehl_setzt_das_faehnchen_an_der_beantworteten_mail \
        as probe

    probe(befehl, monkeypatch, capsys)                                      # Kontrolle
    monkeypatch.setattr(_faehnchen, "_setze_in", _zeile_ersetzt(
        _faehnchen, "_setze_in", "kopf = treffer[0]",
        "kopf = treffer[0]._replace(uid=str(int(treffer[0].uid) + 1))"))
    with pytest.raises(AssertionError, match="falsches STORE"):
        probe(befehl, monkeypatch, capsys)


def test_mit_einem_zweiten_flag_geht_mehr_als_das_faehnchen_hinaus(befehl, monkeypatch, capsys):
    """Sabotage an genau einer Stelle: `\\Seen` geht mit. Die Attrappe wirft,
    `setze` fängt es — rot wird die Probe am Protokoll."""
    from falzmarke import faehnchen as _faehnchen
    from test_postfach_entwurf import test_befehl_setzt_das_faehnchen_an_der_beantworteten_mail \
        as probe

    probe(befehl, monkeypatch, capsys)                                      # Kontrolle
    monkeypatch.setattr(_faehnchen, "_setze_in", _zeile_ersetzt(
        _faehnchen, "_setze_in", 'f"({FLAG})"', 'f"({FLAG} \\\\Seen)"'))
    with pytest.raises(AssertionError, match="falsches STORE"):
        probe(befehl, monkeypatch, capsys)


# Nachreview #553: Jede Schutzstelle in `faehnchen._setze_in` und `setze` und
# die Typprüfung in `lint` bekommen ihre eigene Probe. Die Proben fahren die
# Einzeltests aus `test_faehnchen.py` gegen die Attrappe; deren erste Zusicherung
# trägt die Meldung, auf die hier gewartet wird.

def _server_553(monkeypatch):
    """Die Fixture `server` aus `test_faehnchen.py`, hier ohne Fixture-Import."""
    from falzmarke import postfach as _postfach

    def setzen(attrappe):
        monkeypatch.setattr(_postfach, "IMAP_KLASSE", attrappe)
        return attrappe
    return setzen


@pytest.mark.parametrize("funktion, alt, neu, probe_name, meldung", [
    ("_setze_in", "if jetzt != geplant:", "if False:",
     "test_ein_wechsel_der_uidvalidity_verhindert_das_setzen",
     "STORE trotz gewechselter UIDVALIDITY"),
    ("_setze_in", "if len(treffer) > 1:", "if False:",
     "test_zwei_mails_mit_derselben_kennung_aendern_nichts",
     "STORE, obwohl zwei Mails dieselbe Kennung tragen"),
    ("_setze_in", 'if "\\\\flagged" not in fahnen:', "if False:",
     "test_ein_store_ohne_wirkung_wird_beim_nachlesen_entdeckt",
     "ein STORE ohne Wirkung als gesetzt gemeldet"),
    ("_setze_in", 'if kopf.fahnen is not None and "\\\\flagged" in kopf.fahnen:', "if False:",
     "test_ein_stehendes_faehnchen_bleibt_unberuehrt",
     "STORE an einem Fähnchen, das schon stand"),
    ("setze", "if not postfach.sendbar(kennung):", "if False:",
     "test_eine_kennung_ausserhalb_von_ascii_wird_nicht_gesucht",
     "Verbindung für eine Kennung, die nicht sendbar ist"),
], ids=["uidvalidity", "zwei_treffer", "nachlesen", "schon_da", "sendbar"])
def test_ohne_die_schutzstelle_aendert_das_faehnchen_zu_viel(
        monkeypatch, funktion, alt, neu, probe_name, meldung):
    """Sabotage an genau einer Stelle je Fall; die Probe muss mit ihrer eigenen
    Meldung anschlagen."""
    import test_faehnchen
    from falzmarke import faehnchen as _faehnchen

    probe = getattr(test_faehnchen, probe_name)
    probe(_server_553(monkeypatch))                                         # Kontrolle
    monkeypatch.setattr(_faehnchen, funktion, _zeile_ersetzt(_faehnchen, funktion, alt, neu))
    with pytest.raises(AssertionError, match=re.escape(meldung)):
        probe(_server_553(monkeypatch))


@pytest.mark.parametrize("alt, neu, wert", [
    # Der alte Fehler genau nachgebaut: `1 == True`, also galt `1` als gültig.
    ("if not (isinstance(erledigt, bool)", "if not (erledigt in (True, False)", "1"),
    # Der ganze zweite Zweig fällt weg.
    ("if not (isinstance(erledigt, bool)", "if False and (isinstance(erledigt, bool)", "vielleicht"),
], ids=["eins_als_bool", "zweig_weg"])
def test_ohne_die_typpruefung_bleibt_ein_falscher_erledigt_wert_still(
        monkeypatch, tmp_path, alt, neu, wert):
    from test_email_datenvertrag import test_erledigt_warnt_bei_jedem_wert_ausser_ja_und_nein \
        as probe

    probe(tmp_path, wert, False)                                            # Kontrolle
    monkeypatch.setattr(_lint, "pruefe_email_frontmatter", _zeile_ersetzt(
        _lint, "pruefe_email_frontmatter", alt, neu))
    with pytest.raises(AssertionError, match=re.escape(f"erledigt: {wert!r} — Warnung erwartet")):
        probe(tmp_path, wert, False)


# Code-Review #553: Das Fähnchen auch bei ungewissem Entwurf und beim Rückfall
# auf die Datei, und die Warnung für `erledigt` ohne `antwort_auf`.

@pytest.mark.parametrize("alt, probe_name, meldung", [
    ("            # wie ein Erfolg des Entwurfs.\n"
     "            _setze_faehnchen_mit(brief, felder)\n",
     "test_befehl_setzt_das_faehnchen_auch_bei_ungewissem_entwurf",
     "kein Fähnchen bei ungewissem Entwurf"),
    ("            # die Mail im Eingang (ADR 0063, Nachtrag).\n"
     "            _setze_faehnchen_mit(brief, felder)\n",
     "test_befehl_setzt_das_faehnchen_auch_beim_rueckfall_auf_die_datei",
     "kein Fähnchen beim Rückfall auf die Datei"),
], ids=["ungewiss", "datei"])
def test_ohne_den_aufruf_im_zweig_bleibt_die_ursprungsmail_ohne_faehnchen(
        befehl, monkeypatch, capsys, alt, probe_name, meldung):
    """Sabotage an genau einer Stelle je Zweig: Der Aufruf fällt weg."""
    import test_postfach_entwurf

    probe = getattr(test_postfach_entwurf, probe_name)
    probe(befehl, monkeypatch, capsys)                                      # Kontrolle
    neu = alt.replace("_setze_faehnchen_mit(brief, felder)", "pass")
    monkeypatch.setattr(falzmarke, "befehl_email", _zeile_ersetzt(
        falzmarke, "befehl_email", alt, neu))
    with pytest.raises(AssertionError, match=re.escape(meldung)):
        probe(befehl, monkeypatch, capsys)


def test_mit_dem_aufruf_im_exit_3_zweig_markiert_es_ohne_entwurf(befehl, monkeypatch, capsys):
    """Sabotage an genau einer Stelle: Der Zweig `--kein-fenster` ohne Entwurf
    ruft das Fähnchen doch (Review #563)."""
    from test_postfach_entwurf import \
        test_befehl_ohne_entwurf_mit_kein_fenster_setzt_kein_faehnchen as probe

    probe(befehl, monkeypatch, capsys)                                      # Kontrolle
    monkeypatch.setattr(falzmarke, "befehl_email", _zeile_ersetzt(
        falzmarke, "befehl_email", "        elif args.kein_fenster:\n",
        "        elif args.kein_fenster:\n            _setze_faehnchen_mit(brief, felder)\n"))
    with pytest.raises(AssertionError, match="Fähnchen, obwohl kein Entwurf entstand"):
        probe(befehl, monkeypatch, capsys)


def test_ohne_die_warnung_bleibt_erledigt_ohne_antwort_auf_still(monkeypatch, tmp_path):
    from test_email_datenvertrag import test_erledigt_ohne_antwort_auf_warnt as probe

    probe(tmp_path)                                                         # Kontrolle
    monkeypatch.setattr(_lint, "pruefe_email_frontmatter", _zeile_ersetzt(
        _lint, "pruefe_email_frontmatter", "        if not antwort:\n", "        if False:\n"))
    with pytest.raises(AssertionError, match=re.escape("`erledigt` ohne `antwort_auf` blieb still")):
        probe(tmp_path)


# ── #389: Eine leer gefüllte Anschriftzeile fällt weg ───────────────────────

@pytest.mark.parametrize("alt, neu, probe, meldung", [
    ("            continue\n", "            pass\n",
     "test_eine_leer_gefuellte_anschriftzeile_faellt_weg", "die Leerzeile blieb stehen"),
    ("PLATZHALTER.search(zeile) and ", "",
     "test_gegenprobe_fester_text_und_leerzeilen_der_vorlage_bleiben",
     "fester Text oder eine Leerzeile der Vorlage fiel weg"),
    # Nachreview #588: Leerraum zählt als leer, und ein ganz leerer Datensatz
    # meldet sich selbst, statt den Linter auf die Vorlage zeigen zu lassen.
    ("not gefuellt.strip():", "not gefuellt:",
     "test_eine_zeile_aus_leerraum_faellt_ebenso_weg", "die Zeile aus Leerraum blieb stehen"),
    ("        raise Seriefehler(LEERE_ANSCHRIFT)\n", "        pass\n",
     "test_sind_alle_anschriftzeilen_leer_nennt_die_meldung_die_daten",
     "kein Fehler für einen Datensatz ohne Anschrift"),
], ids=["weglassen", "nur_platzhalter", "leerraum", "leerer_datensatz"])
def test_ohne_die_stelle_bleibt_die_leerzeile_oder_faellt_zu_viel(monkeypatch, alt, neu, probe,
                                                                  meldung):
    """Sabotage an genau einer Stelle von `serie._fuelle_zeilen` (#389)."""
    import test_serie
    from falzmarke import serie as _serie

    getattr(test_serie, probe)()                                            # Kontrolle
    monkeypatch.setattr(_serie, "_fuelle_zeilen",
                        _zeile_ersetzt(_serie, "_fuelle_zeilen", alt, neu))
    with pytest.raises(AssertionError, match=re.escape(meldung)):
        getattr(test_serie, probe)()


# ── #566: --faehnchen-weg nimmt das Fähnchen vor dem Ablegen ab ─────────────
#
# Jede Probe ist ein Test aus `test_ablage.py`. Gekippt wird je eine Zeile in
# `faehnchen.nimm_weg`, `ablage` oder `cli`; die Probe muss mit ihrer eigenen
# Meldung anschlagen, nicht mit irgendeiner.

def _probe_566(name, monkeypatch, capsys):
    """Der Test `name` aus `test_ablage.py`, aufrufbar ohne seine Fixtures."""
    import inspect

    import test_ablage
    from falzmarke import postfach as _postfach

    # `test_ablage._postfach` setzt die Klasse ohne monkeypatch; dort räumt eine
    # autouse-Fixture auf, die hier nicht läuft.
    monkeypatch.setattr(_postfach, "IMAP_KLASSE", _postfach.IMAP_KLASSE, raising=False)
    if name == "nicht_sicher_ab":
        return lambda: test_ablage.test_steht_das_faehnchen_nicht_sicher_ab_wandert_keine_mail(
            {"store_wirkt": False}, "trägt UID 101 das Fähnchen noch")
    if name == "store_abgelehnt":
        return lambda: test_ablage.test_steht_das_faehnchen_nicht_sicher_ab_wandert_keine_mail(
            {"store_fehler": "Mailbox is read-only"}, "ob das Fähnchen an UID 101 schon weg ist")
    funktion = getattr(test_ablage, name)
    vorrat = {"monkeypatch": monkeypatch, "capsys": capsys}
    return lambda: funktion(**{k: vorrat[k] for k in inspect.signature(funktion).parameters})


@pytest.mark.parametrize("modul, funktion, alt, neu, probe_name, meldung", [
    ("faehnchen", "nimm_weg", "if jetzt != uidvalidity:", "if False:",
     "test_ein_wechsel_der_uidvalidity_laesst_kein_store_hinaus",
     "STORE trotz gewechselter UIDVALIDITY"),
    ("faehnchen", "nimm_weg", "if offen:", "if False:",
     "nicht_sicher_ab", "UID MOVE, obwohl das Fähnchen nicht sicher weg ist"),
    ("ablage", "raeume_auf", "            if faehnchen_weg:\n", "            if False:\n",
     "test_faehnchen_weg_nimmt_das_faehnchen_ab_und_legt_die_mail_ab",
     "kein STORE -FLAGS vor dem Ablegen"),
    ("ablage", "raeume_auf", "trotz_faehnchen=trotz_faehnchen or faehnchen_weg,",
     "trotz_faehnchen=trotz_faehnchen,",
     "test_faehnchen_weg_nimmt_das_faehnchen_ab_und_legt_die_mail_ab",
     "UID 101 bliebe liegen (Fähnchen)"),
    ("ablage", "raeume_auf",
     "                if not _kann_verschieben(sitzung):\n"
     "                    raise AblageFehler(_KEIN_MOVE)\n", "",
     "test_ohne_move_im_server_bleibt_auch_das_faehnchen",
     "STORE, obwohl der Server nicht verschieben kann"),
    ("ablage", "_mit_faehnchen", "return zug.fahnen is None or FAEHNCHEN in zug.fahnen",
     "return True", "test_eine_genannte_mail_ohne_faehnchen_bekommt_kein_store",
     "STORE an einer Mail ohne Fähnchen"),
    ("ablage", "raeume_auf", "            if bericht.faehnchen_entfernt:\n",
     "            if False:\n", "test_bricht_der_zug_nach_dem_entfernen_ab_sagt_der_grund_es",
     "der Grund verschweigt das entfernte Fähnchen"),
    ("ablage", "raeume_auf", "    if faehnchen_weg and uids is None:\n", "    if False:\n",
     "test_faehnchen_weg_ohne_uids_aendert_nichts", "faehnchen_weg ohne UIDs lief ohne Grund"),
    ("ablage", "_zugzeilen", "        elif bericht.faehnchen_weg and _mit_faehnchen(zug):\n",
     "        elif False:\n", "test_ohne_machen_zeigt_die_anzeige_welches_faehnchen_wegkaeme",
     "die Anzeige verschweigt das Fähnchen"),
    ("cli", "befehl_aufraeumen", "    if args.faehnchen_weg and args.uid is None:\n",
     "    if False:\n", "test_faehnchen_weg_ohne_uid_ist_ein_eingabefehler",
     "--faehnchen-weg lief ohne --uid"),
    ("faehnchen", "nimm_weg",
     'except postfach.PostfachFehler as fehler:\n        raise FaehnchenFehler(f"{fehler} — '
     'das Entfernen', 'except ZeroDivisionError as fehler:\n        raise FaehnchenFehler('
     'f"{fehler} — das Entfernen',
     "test_reisst_das_nachlesen_ab_sagt_der_grund_dass_das_store_hinausging",
     "der Grund verschweigt das gesendete STORE"),
    # Nachreview #585, Befund 3: der Fehlerzweig des STORE und die unbekannten Flags.
    ("faehnchen", "nimm_weg",
     'except postfach.PostfachFehler as fehler:\n        raise FaehnchenFehler(f"{fehler} — '
     'ob das Fähnchen', 'except ZeroDivisionError as fehler:\n        raise FaehnchenFehler('
     'f"{fehler} — ob das Fähnchen',
     "store_abgelehnt", "Grund ohne „ob das Fähnchen an UID 101 schon weg ist“"),
    ("faehnchen", "nimm_weg", 'nach.get(u) is None or "\\\\flagged" in nach[u]',
     '"\\\\flagged" in (nach.get(u) or ())',
     "test_unbekannte_flags_werden_abgenommen_aber_ohne_nachlesen_wandert_keine",
     "die Mail ohne bekannte Flags wanderte"),
    # Befund 1: der Teil, der das Fähnchen schon verlor.
    ("faehnchen", "nimm_weg", 'ohne Fähnchen im Eingang") if weg else ""',
     'ohne Fähnchen im Eingang") if False else ""',
     "test_bleibt_das_faehnchen_an_einer_von_zwei_mails_nennt_der_grund_die_andere",
     "der Grund verschweigt das entfernte Fähnchen an 101"),
    # Befund 4: ohne SELECT kein Schreiben; die Attrappe sieht das jetzt.
    ("faehnchen", "nimm_weg", "sitzung._v.select, zitiert(EINGANG))",
     "sitzung._v.select, zitiert(EINGANG), True)",
     "test_faehnchen_weg_nimmt_das_faehnchen_ab_und_legt_die_mail_ab", "READ-ONLY"),
    # Befund 9: nach welcher Nummerierung die UIDs zählen.
    ("ablage", "raeume_auf", 'f"; UIDs nach UIDVALIDITY {bericht.uidvalidity}: das Fähnchen an UID "',
     'f"; das Fähnchen an UID "',
     "test_bricht_der_zug_nach_dem_entfernen_ab_sagt_der_grund_es",
     "der Grund verschweigt die Nummerierung"),
], ids=["uidvalidity", "nachlesen", "aufruf", "liegen", "kein_move", "nur_mit_faehnchen",
        "grund_nach_abbruch", "ohne_uids", "anzeige", "cli_ohne_uid", "nachlesen_reisst_ab",
        "store_abgelehnt", "flags_unbekannt", "teil_entfernt", "schreibend",
        "nummerierung"])
def test_ohne_die_stelle_nimmt_faehnchen_weg_zu_viel_oder_schweigt(
        monkeypatch, capsys, modul, funktion, alt, neu, probe_name, meldung):
    """Sabotage an genau einer Stelle je Fall (#566)."""
    import importlib

    ziel = importlib.import_module(f"falzmarke.{modul}")
    _probe_566(probe_name, monkeypatch, capsys)()                           # Kontrolle
    monkeypatch.setattr(ziel, funktion, _zeile_ersetzt(ziel, funktion, alt, neu))
    with pytest.raises(AssertionError, match=re.escape(meldung)):
        _probe_566(probe_name, monkeypatch, capsys)()


# ── #454: Der Plugin-Ordner bleibt aus dem Skill-Paket ──────────────────────

def test_ohne_ausschluss_landet_der_plugin_ordner_im_skill_paket(tmp_path):
    if sys.platform.startswith("win"):
        pytest.skip("bash und Symlinks — der Nachweis läuft auf den anderen beiden Plattformen")
    from test_skillpaket import SKRIPT, schlankes_paket

    text = SKRIPT.read_text(encoding="utf-8")
    sabotiert = text.replace("rm -rf paket/falzmarke/.claude-plugin paket/falzmarke/README.md\n",
                             "", 1)
    assert sabotiert != text, "die Sabotage greift nicht"
    _, namen = schlankes_paket(tmp_path, sabotiert)
    assert {"falzmarke/README.md", "falzmarke/.claude-plugin/plugin.json"} <= namen, sorted(namen)


def test_ohne_dereferenzieren_loescht_das_packen_die_quelle(tmp_path):
    """`cp -r` bleibt unter macOS eine echte Kopie, unter GNU ein Symlink. `-RP`
    erzwingt das zweite Verhalten überall, sonst wäre diese Probe lokal grün."""
    if sys.platform.startswith("win"):
        pytest.skip("bash und Symlinks — der Nachweis läuft auf den anderen beiden Plattformen")
    from test_skillpaket import SKRIPT, schlankes_paket

    text = SKRIPT.read_text(encoding="utf-8")
    sabotiert = text.replace("cp -RL skill", "cp -RP skill", 1)
    assert sabotiert != text, "die Sabotage greift nicht"
    quelle, _ = schlankes_paket(tmp_path, sabotiert)
    assert not (quelle / "README.md").exists(), \
        "ohne -L trifft das `rm` die Quelle — sonst hielte -L nichts"


# ── #533: Die typst-Grenze steht an allen drei Stellen gleich ───────────────

#: Die heutige Grenze und ihre Sabotage: die Untergrenze vor #533. Genau dieser Fehler
#: blieb bis dahin grün, weil `test_abhaengigkeiten` nur Paketnamen verglich.
_TYPST_GRENZE = "typst>=0.15.2,<0.16"
_TYPST_GRENZE_ALT = "typst>=0.15,<0.16"
_GRENZ_STELLEN = {"PYPROJECT": "pyproject.toml",
                  "REQUIREMENTS": "skill/requirements.txt",
                  "BOOTSTRAP": "skill/scripts/bootstrap.py"}


def _grenzen_in_kopie(tmp_path, monkeypatch, sabotiert: str | None):
    """Alle drei Stellen als Kopie, an höchstens einer die Grenze zurückgesetzt."""
    import test_abhaengigkeiten

    tmp_path.mkdir(parents=True, exist_ok=True)
    for konstante, relativ in _GRENZ_STELLEN.items():
        text = (REPO / relativ).read_text(encoding="utf-8")
        assert text.count(_TYPST_GRENZE) == 1, (
            f"„{_TYPST_GRENZE}“ steht nicht genau einmal in {relativ} — "
            "wurde die Grenze gehoben, hier nachziehen")
        if konstante == sabotiert:
            text = text.replace(_TYPST_GRENZE, _TYPST_GRENZE_ALT, 1)
            assert _TYPST_GRENZE not in text, "die Sabotage greift nicht"
        ziel = tmp_path / relativ.replace("/", "_")
        ziel.write_text(text, encoding="utf-8")
        monkeypatch.setattr(test_abhaengigkeiten, konstante, ziel)
    return test_abhaengigkeiten.test_requirements_und_deps_tragen_dieselben_grenzen_wie_pyproject


_NEU, _ALT = "„<0.16,>=0.15.2“", "„<0.16,>=0.15“"


@pytest.mark.parametrize("stelle, zeilen", [
    ("REQUIREMENTS", [f"skill/requirements.txt: typst verlangt {_ALT}, pyproject.toml {_NEU}"]),
    ("BOOTSTRAP", [f"skill/scripts/bootstrap.py DEPS: typst verlangt {_ALT}, pyproject.toml {_NEU}"]),
    # Weicht die kanonische Quelle ab, weichen beide anderen von ihr ab — beide Zeilen.
    ("PYPROJECT", [f"skill/requirements.txt: typst verlangt {_NEU}, pyproject.toml {_ALT}",
                   f"skill/scripts/bootstrap.py DEPS: typst verlangt {_NEU}, pyproject.toml {_ALT}"]),
])
def test_eine_abweichende_typst_grenze_macht_den_abgleich_rot(tmp_path, monkeypatch,
                                                              stelle, zeilen):
    _grenzen_in_kopie(tmp_path / "kontrolle", monkeypatch, None)()           # Kontrolle
    probe = _grenzen_in_kopie(tmp_path, monkeypatch, stelle)
    # pytest rückt die Folgezeilen einer Meldung ein, daher `\n\s*` zwischen den Zeilen.
    with pytest.raises(AssertionError, match=r"\n\s*".join(map(re.escape, zeilen))):
        probe()


#: Je Lauf fehlt in pyproject.toml ein Teil der typst-Grenze. Der Abgleich der drei
#: Stellen bliebe dabei grün, wenn alle drei gleich sabotiert wären („leer gleich leer“).
@pytest.mark.parametrize("sabotage, meldung", [
    ("typst", "typst ohne Untergrenze in pyproject.toml: „ohne Grenze“"),
    ("typst<0.16", "typst ohne Untergrenze in pyproject.toml: „<0.16“"),
    ("typst>=0.15.2", "typst ohne echte Obergrenze in pyproject.toml: „>=0.15.2“"),
    ("typst>=0.15.2,<=0.16",
     "typst ohne echte Obergrenze in pyproject.toml: „<=0.16,>=0.15.2“"),
], ids=["ohne-grenze", "ohne-untergrenze", "ohne-obergrenze", "obergrenze-einschliessend"])
def test_eine_unvollstaendige_typst_grenze_ist_keine_echte_grenze(tmp_path, monkeypatch,
                                                                  sabotage, meldung):
    import test_abhaengigkeiten

    probe = test_abhaengigkeiten.test_die_typst_grenze_ist_eine_echte_grenze
    probe()                                                                   # Kontrolle
    text = test_abhaengigkeiten.PYPROJECT.read_text(encoding="utf-8")
    zeile = f'"{_TYPST_GRENZE}"'
    assert text.count(zeile) == 1, "die Sabotage findet ihre Zeile nicht"
    kopie = tmp_path / "pyproject.toml"
    kopie.write_text(text.replace(zeile, f'"{sabotage}"'), encoding="utf-8")
    monkeypatch.setattr(test_abhaengigkeiten, "PYPROJECT", kopie)
    with pytest.raises(AssertionError, match=re.escape(meldung)):
        probe()


def test_das_offline_wheel_fuer_python_38_macht_den_abgleich_rot(tmp_path, monkeypatch):
    """Der Wert vor #533. Mit ihm fand `pip download` ab typst 0.15.2 kein Wheel mehr."""
    import test_abhaengigkeiten

    probe = test_abhaengigkeiten.test_das_offline_wheel_wird_fuer_die_python_untergrenze_angefragt
    probe()                                                                   # Kontrolle
    text = test_abhaengigkeiten.PACKEN.read_text(encoding="utf-8")
    assert text.count('PYTHON_FASSUNG="3.11"') == 1, "die Sabotage findet ihre Zeile nicht"
    kopie = tmp_path / "skill_packen.sh"
    kopie.write_text(text.replace('PYTHON_FASSUNG="3.11"', 'PYTHON_FASSUNG="3.8"'),
                     encoding="utf-8")
    monkeypatch.setattr(test_abhaengigkeiten, "PACKEN", kopie)
    with pytest.raises(AssertionError, match=re.escape(
            "skill_packen.sh fragt das Wheel für Python 3.8 an, requires-python verlangt 3.11")):
        probe()


# ── #533: Die Maske deckt jede Stelle der typst-Kennung ─────────────────────
#
# Je Lauf fehlt der Maske genau eine der vier Stellen, so als wäre sie nie
# eingetragen worden. Dann muss der Nachweis, dass eine andere typst-Fassung kein
# Golden kippt, an genau dieser Lücke rot werden.

@pytest.mark.parametrize("stelle", ["xmp:CreatorTool und stEvt:softwareAgent",
                                    "/Creator", "InstanceID im XMP", "/ID"])
def test_eine_luecke_in_der_typst_maske_kippt_das_golden(monkeypatch, stelle):
    import conftest
    import test_rechnung_beispiele as _rb

    beispiel = _rb.RECHNUNG_BEISPIELE[0]
    _rb.test_eine_andere_typst_fassung_kippt_kein_golden(beispiel)          # Kontrolle
    monkeypatch.setattr(_rb, "ohne_typst_kennung", _zeile_ersetzt(
        conftest, "ohne_typst_kennung",
        '        pdf = pdf.replace(alt, b"#" * len(alt))',
        f'        pdf = pdf if wo == "{stelle}" else pdf.replace(alt, b"#" * len(alt))'))
    with pytest.raises(AssertionError, match=re.escape(
            f"{beispiel.stem}: die Maske deckt die typst-Kennung nicht ganz ab")):
        _rb.test_eine_andere_typst_fassung_kippt_kein_golden(beispiel)


# ── Review #568: Die Maske hält das Neu-Erzeugen nicht auf und prüft unter -O ──

def test_der_alte_vergleich_haelt_das_neu_erzeugen_an_der_maske_auf(tmp_path, monkeypatch,
                                                                     capsys):
    """Nachbau des Vergleichs vor Review #568: die Maske ohne Ausweg."""
    import conftest
    import test_golden_rechnung as _gr

    monkeypatch.setattr(_gr.golden_rechnung, "REPO", tmp_path)
    _gr.test_eine_maske_die_nicht_greift_haelt_das_schreiben_nicht_auf(
        tmp_path / "kontrolle.pdf", capsys)                                  # Kontrolle
    monkeypatch.setattr(_gr.golden_rechnung, "_gleich",
                        lambda alt, neu, maske, *_: (maske(alt) == maske(neu) if maske
                                                     else alt == neu))
    with pytest.raises(conftest.TypstMaskeGreiftNicht, match="keine typst-Kennung im XMP"):
        _gr.test_eine_maske_die_nicht_greift_haelt_das_schreiben_nicht_auf(
            tmp_path / "rechnung.pdf", capsys)


def test_ein_verschluckter_maskenfehler_meldet_mit_pruefen_gleich(tmp_path, monkeypatch,
                                                                   capsys):
    import test_golden_rechnung as _gr

    monkeypatch.setattr(_gr.golden_rechnung, "REPO", tmp_path)
    _gr.test_mit_pruefen_zaehlt_eine_maske_die_nicht_greift_als_abweichung(
        tmp_path / "kontrolle.pdf", capsys)                                  # Kontrolle
    monkeypatch.setattr(_gr.golden_rechnung, "_gleich", _zeile_ersetzt(
        _gr.golden_rechnung, "_gleich", "            return False\n", "            return True\n"))
    with pytest.raises(AssertionError, match=re.escape(
            "mit --pruefen gilt eine Datei, an der die Maske nicht greift, als „gleich“")):
        _gr.test_mit_pruefen_zaehlt_eine_maske_die_nicht_greift_als_abweichung(
            tmp_path / "rechnung.pdf", capsys)


def test_mit_pruefen_ohne_grund_nennt_die_zeile_die_maske_nicht(tmp_path, monkeypatch, capsys):
    """Review #575: Die Zeile einer Abweichung sagt, dass die Maske nicht griff."""
    import test_golden_rechnung as _gr

    monkeypatch.setattr(_gr.golden_rechnung, "REPO", tmp_path)
    _gr.test_mit_pruefen_zaehlt_eine_maske_die_nicht_greift_als_abweichung(
        tmp_path / "kontrolle.pdf", capsys)                                  # Kontrolle
    monkeypatch.setattr(_gr.golden_rechnung, "_aktualisiere", _zeile_ersetzt(
        _gr.golden_rechnung, "_aktualisiere",
        '        zusatz = f" — Maske greift nicht: {roh[pfad]}" if pfad in roh else ""\n',
        '        zusatz = ""\n'))
    with pytest.raises(AssertionError, match="weicht ab  rechnung.pdf\n"):
        _gr.test_mit_pruefen_zaehlt_eine_maske_die_nicht_greift_als_abweichung(
            tmp_path / "rechnung.pdf", capsys)


def test_ein_wieder_geworfener_maskenfehler_bricht_den_pruefen_lauf_ab(tmp_path, monkeypatch,
                                                                       capsys):
    """Nachbau von `_gleich` vor Review #575: Mit `--pruefen` wirft es den Maskenfehler
    neu, `main` fängt ihn nicht, und der Lauf endet am ersten PDF."""
    import conftest
    import test_golden_rechnung as _gr

    _gr.test_mit_pruefen_laeuft_ein_maskenfehler_bis_zur_zusammenfassung(
        _gr._lauf(tmp_path / "kontrolle", monkeypatch), capsys)               # Kontrolle
    monkeypatch.setattr(_gr.golden_rechnung, "_gleich", _zeile_ersetzt(
        _gr.golden_rechnung, "_gleich",
        "        roh[pfad] = str(fehler)\n        if nur_pruefen:\n            return False\n",
        "        if nur_pruefen:\n            raise\n"))
    with pytest.raises(conftest.TypstMaskeGreiftNicht, match="keine typst-Kennung im XMP"):
        _gr.test_mit_pruefen_laeuft_ein_maskenfehler_bis_zur_zusammenfassung(
            _gr._lauf(tmp_path / "sabotiert", monkeypatch), capsys)


def test_ein_roher_vergleich_mit_exit_0_faellt_auf(tmp_path, monkeypatch, capsys):
    """Nachbau von `main` vor Review #575: roh geschrieben, trotzdem Exit 0."""
    import test_golden_rechnung as _gr

    _gr.test_ohne_pruefen_endet_ein_roher_vergleich_mit_exit_2(
        _gr._lauf(tmp_path / "kontrolle", monkeypatch), capsys)               # Kontrolle
    monkeypatch.setattr(_gr.golden_rechnung, "main", _zeile_ersetzt(
        _gr.golden_rechnung, "main", "        return 2\n", "        return 0\n"))
    with pytest.raises(AssertionError, match="der rohe Vergleich endete mit Exit 0 statt 2"):
        _gr.test_ohne_pruefen_endet_ein_roher_vergleich_mit_exit_2(
            _gr._lauf(tmp_path / "sabotiert", monkeypatch), capsys)


def test_ein_lauf_der_immer_exit_2_meldet_faellt_auf(tmp_path, monkeypatch, capsys):
    """Die Kontrolle in `test_golden_rechnung` trennt: Endete jeder Lauf mit Exit 2,
    wäre auch einer mit greifender Maske nicht mehr Exit 0."""
    import test_golden_rechnung as _gr

    _gr.test_greift_die_maske_endet_der_lauf_mit_0(
        _gr._lauf(tmp_path / "kontrolle", monkeypatch), capsys)               # Kontrolle
    monkeypatch.setattr(_gr.golden_rechnung, "main", _zeile_ersetzt(
        _gr.golden_rechnung, "main", "    if roh:\n", "    if True:\n"))
    with pytest.raises(AssertionError, match="ohne --pruefen nicht Exit 0"):
        _gr.test_greift_die_maske_endet_der_lauf_mit_0(
            _gr._lauf(tmp_path / "sabotiert", monkeypatch), capsys)


def test_ohne_maske_gilt_eine_andere_typst_fassung_als_abweichung(tmp_path, monkeypatch,
                                                                   capsys):
    """Der Ausweg darf die Maske nicht ersetzen: Vergleicht `_gleich` immer roh, muss
    die Kontrolle in `test_golden_rechnung` rot werden."""
    import test_golden_rechnung as _gr

    monkeypatch.setattr(_gr.golden_rechnung, "REPO", tmp_path)
    _gr.test_eine_greifende_maske_laesst_eine_andere_typst_fassung_durch(
        tmp_path / "kontrolle.pdf", capsys)                                  # Kontrolle
    monkeypatch.setattr(_gr.golden_rechnung, "_gleich", _zeile_ersetzt(
        _gr.golden_rechnung, "_gleich", "        return maske(alt) == maske(neu)\n",
        "        return alt == neu\n"))
    with pytest.raises(AssertionError, match=re.escape(
            "eine andere typst-Fassung gilt als Abweichung — die Maske greift nicht mehr")):
        _gr.test_eine_greifende_maske_laesst_eine_andere_typst_fassung_durch(
            tmp_path / "rechnung.pdf", capsys)


def test_ohne_vorpruefung_wirft_ein_pdf_ohne_xmp_einen_typeerror(monkeypatch):
    """So lief die Maske vor Review #568 unter `python -O`: `fassung[1]` auf None."""
    import conftest
    import test_rechnung_beispiele as _rb

    _rb.test_ein_pdf_ganz_ohne_xmp_meldet_die_fehlende_kennung()             # Kontrolle
    monkeypatch.setattr(_rb, "ohne_typst_kennung", _zeile_ersetzt(
        conftest, "ohne_typst_kennung", "    if not (fassung and instanz):\n", "    if False:\n"))
    with pytest.raises(TypeError, match="'NoneType' object is not subscriptable"):
        _rb.test_ein_pdf_ganz_ohne_xmp_meldet_die_fehlende_kennung()


def test_mit_assert_bleibt_die_maske_unter_python_O_still(tmp_path, monkeypatch):
    """Nachbau der Maske vor Review #568: dieselben Prüfungen als `assert`, in einer
    Kopie der conftest, die die Probe in einem eigenen Prozess unter `-O` lädt."""
    import test_rechnung_beispiele as _rb

    (tmp_path / "kontrolle").mkdir()
    _rb.test_die_maske_prueft_auch_unter_python_O(tmp_path / "kontrolle")    # Kontrolle
    text = _rb.KONFTEST.read_text(encoding="utf-8")
    for alt, neu in (
            ("""    if not (fassung and instanz):
        raise TypstMaskeGreiftNicht(
            "keine typst-Kennung im XMP — hat typst das Format geändert?")
""", """    assert fassung and instanz, "keine typst-Kennung im XMP — hat typst das Format geändert?"
"""),
            ("""        if pdf.count(alt) != anzahl:
            raise TypstMaskeGreiftNicht(
                f"typst-Kennung in {wo}: {pdf.count(alt)}-mal statt {anzahl}-mal")
""", """        assert pdf.count(alt) == anzahl, (
            f"typst-Kennung in {wo}: {pdf.count(alt)}-mal statt {anzahl}-mal")
""")):
        assert text.count(alt) == 1, f"„{alt.strip()}“ steht nicht genau einmal in der conftest"
        text = text.replace(alt, neu)
    kopie = tmp_path / "conftest.py"
    kopie.write_text(text, encoding="utf-8")
    monkeypatch.setattr(_rb, "KONFTEST", kopie)
    with pytest.raises(AssertionError, match="unter python -O blieb die Maske still"):
        _rb.test_die_maske_prueft_auch_unter_python_O(tmp_path)


# ── #467: Der Handschlag verlangt eine Version in `serverInfo` ──────────────

def test_ein_server_ohne_version_faellt_beim_handschlag_durch(tmp_path):
    """Ein Server, der `initialize` ohne Version beantwortet, muss scheitern,
    und zwar an der Version: Er meldet gar keine Werkzeuge, also müsste ihn ohne
    die neue Prüfung erst `tools/list` aufhalten."""
    pytest.importorskip("mcp", reason="optionales Extra falzmarke[mcp]")
    import os
    import subprocess

    server = tmp_path / "ohne_version.py"
    server.write_text("from mcp.server import MCPServer\nMCPServer('falzmarke').run()\n",
                      encoding="utf-8")
    lauf = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "mcp_handschlag.py"), "--ohne-render", "--",
         sys.executable, str(server)],
        capture_output=True, text=True, encoding="utf-8", timeout=120, check=False,
        env={**os.environ, "PYTHONUTF8": "1"})
    ausgabe = lauf.stdout + lauf.stderr
    assert lauf.returncode == 1, ausgabe
    assert "meldet keine Version" in ausgabe and "tools/list" not in ausgabe, ausgabe


# ── #437: Die Checks auf die PR-Angaben starten, wenn die Angabe sich ändert ──

def _pr_angaben_mit(tmp_path, monkeypatch, alt: str, neu: str):
    """pr-angaben.yml mit genau einer Ersetzung, als PR_ANGABEN in test_pr_angaben."""
    import test_pr_angaben

    text = test_pr_angaben.PR_ANGABEN.read_text(encoding="utf-8")
    assert text.count(alt) == 1, f"„{alt.strip()}“ steht nicht genau einmal in pr-angaben.yml"
    datei = tmp_path / "pr-angaben.yml"
    datei.write_text(text.replace(alt, neu), encoding="utf-8")
    monkeypatch.setattr(test_pr_angaben, "PR_ANGABEN", datei)
    return test_pr_angaben


@pytest.mark.parametrize("typ, erwartet", [
    ("edited", "body ändert sich bei „edited“"),
    ("labeled", "labels ändert sich bei „labeled“"),
    ("unlabeled", "labels ändert sich bei „unlabeled“"),
    ("synchronize", "files ändert sich bei „synchronize“"),
], ids=["edited", "labeled", "unlabeled", "synchronize"])
def test_fehlt_ein_ausloeser_wird_die_angabe_gemeldet(typ, erwartet, tmp_path, monkeypatch):
    """Jedes Ereignis einzeln aus dem Trigger genommen. Ohne `synchronize`
    schlüge zuerst `pflicht_checks` an; hier zählt, dass auch die Probe es sieht."""
    alt = "types: [opened, synchronize, reopened, edited, labeled, unlabeled]"
    typen = [t for t in alt[len("types: ["):-1].split(", ") if t != typ]
    pa = _pr_angaben_mit(tmp_path, monkeypatch, alt, f"types: [{', '.join(typen)}]")
    with pytest.raises(AssertionError, match=erwartet):
        pa.test_jede_gelesene_angabe_hat_ihren_ausloeser()


def test_ein_unbekanntes_feld_wird_nicht_fuer_unveraenderlich_gehalten(tmp_path, monkeypatch):
    pa = _pr_angaben_mit(tmp_path, monkeypatch, "--json body,labels", "--json body,labels,title")
    with pytest.raises(AssertionError, match="liest „title“, AUSLOESER kennt das Feld nicht"):
        pa.test_jede_gelesene_angabe_hat_ihren_ausloeser()


@pytest.mark.parametrize("alt, neu, erwartet", [
    ("  pull_request:\n    types:", "  workflow_dispatch:\n  pull_request:\n    types:",
     "Auslöser „workflow_dispatch“"),
    ("    name: Closing-Keyword\n", "    name: Closing-Keyword\n    if: github.event.action != 'edited'\n",
     "closing-keyword trägt if"),
], ids=["workflow-dispatch", "if"])
def test_ein_weg_zum_skipped_wird_gemeldet(alt, neu, erwartet, tmp_path, monkeypatch):
    pa = _pr_angaben_mit(tmp_path, monkeypatch, alt, neu)
    with pytest.raises(AssertionError, match=erwartet):
        pa.test_kein_job_laesst_sich_ueberspringen()


def test_mit_edited_in_ci_yml_wird_die_gegenseite_rot(tmp_path, monkeypatch):
    """Weg 1 aus #437, der verworfen ist: die ganze Matrix bei jeder Textänderung."""
    import test_pr_angaben

    text = test_pr_angaben.CI.read_text(encoding="utf-8")
    alt = "\n  pull_request:\n"
    assert text.count(alt) == 1
    datei = tmp_path / "ci.yml"
    datei.write_text(text.replace(alt, f"{alt}    types: [opened, synchronize, reopened, edited]\n"),
                     encoding="utf-8")
    test_pr_angaben.test_ci_yml_startet_weiter_nur_bei_neuem_code()   # Kontrolle
    monkeypatch.setattr(test_pr_angaben, "CI", datei)
    with pytest.raises(AssertionError, match="edited"):
        test_pr_angaben.test_ci_yml_startet_weiter_nur_bei_neuem_code()


@pytest.mark.parametrize("funktion, alt, neu, probe", [
    ("analysiere", "    if doppelt:\n", "    if False:\n",
     "test_ein_checkname_in_zwei_workflows_ist_ein_fehler"),
    ("_analysiere_einen", "    fehlend = [t for t in VORGABE_TYPEN if t not in typen]\n",
     "    fehlend = []\n", "test_ein_workflow_ohne_synchronize_ist_ein_fehler"),
    ("_analysiere_einen", "    typen = pull_request_typen(daten)\n",
     "    typen = pull_request_typen(daten) or VORGABE_TYPEN\n",
     "test_ein_workflow_ohne_pull_request_ist_ein_fehler"),
    ("_analysiere_einen", "    if filter_schluessel:\n", "    if False:\n",
     "test_ein_workflow_mit_filter_ist_ein_fehler"),
    # #493: ohne die Nachbarprüfung, und mit Nachbarn, deren `if:`-Jobs nicht zählen.
    ("analysiere", "    if kollisionen:\n", "    if False:\n",
     "test_ein_nachbar_mit_gleichem_checknamen_ist_ein_fehler"),
    ("nachbar_namen", "    return _checknamen(_lies(workflow), alle=True)[0]\n",
     "    return _checknamen(_lies(workflow))[0]\n",
     "test_ein_per_if_ausgeschlossener_nachbar_job_zaehlt_trotzdem"),
], ids=["doppelt", "ohne-synchronize", "ohne-pull-request", "filter", "nachbar", "nachbar-mit-if"])
def test_ohne_die_pruefung_in_pflicht_checks_wird_die_probe_rot(funktion, alt, neu, probe,
                                                                 tmp_path, monkeypatch):
    """Je eine Prüfung zurückgebaut auf den Stand vor #437 (kannte keine davon) oder
    vor #493 (las keine Nachbarn): Die Liste kam dann ohne Fehler heraus."""
    sys.path.insert(0, str(REPO / "scripts"))
    import pflicht_checks
    import test_pflicht_checks

    monkeypatch.setattr(pflicht_checks, funktion,
                        _zeile_ersetzt(pflicht_checks, funktion, alt, neu))
    with pytest.raises(pytest.fail.Exception, match="DID NOT RAISE"):
        getattr(test_pflicht_checks, probe)(tmp_path)


def test_ohne_die_pruefung_eigener_main_jobs_wird_die_probe_rot(tmp_path, monkeypatch):
    """Nachreview #499, Befund 1, zurückgebaut: Ein main-Job im Pflicht-Workflow unter
    dem Namen eines Pflicht-Checks ging ohne Fehler durch."""
    sys.path.insert(0, str(REPO / "scripts"))
    import pflicht_checks
    import test_pflicht_checks

    probe = test_pflicht_checks.test_ein_main_job_unter_dem_namen_eines_pflicht_checks_ist_ein_fehler
    probe(tmp_path, "tests")                                               # Kontrolle
    monkeypatch.setattr(pflicht_checks, "analysiere", _zeile_ersetzt(
        pflicht_checks, "analysiere", "    if schatten:\n", "    if False:\n"))
    with pytest.raises(pytest.fail.Exception, match="DID NOT RAISE"):
        probe(tmp_path, "tests")


# ── Dependabot 07.11.2026: jede Action in den Workflows auf einem Commit-SHA ──

def _release_mit_publish_pin(tmp_path, monkeypatch, ersatz: str):
    """release.yml mit einem anderen Ziel hinter `pypa/gh-action-pypi-publish@`,
    als einzige Datei in test_aktion.PIN_DATEIEN."""
    import test_aktion

    text = (REPO / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    sabotiert, anzahl = re.subn(r"(pypa/gh-action-pypi-publish@)[0-9a-f]{40}",
                                lambda m: m.group(1) + ersatz, text)
    assert anzahl == 1, f"der Publish-Pin steht {anzahl}-mal in release.yml, erwartet 1"
    datei = tmp_path / "release.yml"
    datei.write_text(sabotiert, encoding="utf-8")
    monkeypatch.setattr(test_aktion, "PIN_DATEIEN", [datei])
    return test_aktion


@pytest.mark.parametrize("ersatz", ["v1.14.3", "7245906"], ids=["tag", "kurze-sha"])
def test_ein_publish_pin_ohne_volle_sha_wird_rot(ersatz, tmp_path, monkeypatch):
    """Der Stand vor dem 07.11.2026 (Tag) und ein abgekürzter SHA: beide verschiebbar
    bzw. mehrdeutig, beide muss die Prüfung beim Namen nennen."""
    import test_aktion

    test_aktion.test_jede_action_in_den_workflows_ist_auf_einen_commit_sha_gepinnt()  # Kontrolle
    probe = _release_mit_publish_pin(tmp_path, monkeypatch, ersatz)
    with pytest.raises(AssertionError,
                       match=rf"release\.yml:\d+: pypa/gh-action-pypi-publish@{re.escape(ersatz)}"):
        probe.test_jede_action_in_den_workflows_ist_auf_einen_commit_sha_gepinnt()


def test_ohne_workflows_wird_die_pin_pruefung_rot(monkeypatch):
    """Ein leerer Glob ließe nur action.yml übrig, und die Prüfung liefe über eine
    einzige Datei grün (Nachreview #580: action.yml zählt seither mit)."""
    import test_aktion

    monkeypatch.setattr(test_aktion, "PIN_DATEIEN", [test_aktion.AKTION])
    with pytest.raises(AssertionError, match="keine fremde Action in .github/workflows gefunden"):
        test_aktion.test_jede_action_in_den_workflows_ist_auf_einen_commit_sha_gepinnt()


def test_eine_yaml_datei_wird_mitgeprueft(tmp_path, monkeypatch):
    """GitHub führt auch `.github/workflows/*.yaml` aus. Ein Glob nur auf `*.yml`
    sähe einen ungepinnten Workflow dort nie (Nachreview #580)."""
    import test_aktion

    (tmp_path / "nachts.yaml").write_text(
        "jobs:\n  a:\n    steps:\n      - uses: fremd/aktion@v1\n", encoding="utf-8")
    monkeypatch.setattr(test_aktion, "PIN_DATEIEN", test_aktion._pin_dateien(tmp_path))
    with pytest.raises(AssertionError, match=r"nachts\.yaml:4: fremd/aktion@v1"):
        test_aktion.test_jede_action_in_den_workflows_ist_auf_einen_commit_sha_gepinnt()


def test_action_yml_wird_mitgeprueft(tmp_path, monkeypatch):
    """action.yml läuft in fremden Repositories; ein Tag dort muss die strenge
    Prüfung beim Namen nennen, nicht nur die ältere (Nachreview #580)."""
    import test_aktion

    text = test_aktion.AKTION.read_text(encoding="utf-8")
    sabotiert, anzahl = re.subn(r"(actions/setup-python@)[0-9a-f]{40}",
                                lambda m: m.group(1) + "v7.1.0", text, count=1)
    assert anzahl == 1, "kein setup-python-Pin in action.yml: Sabotage greift nicht"
    kopie = tmp_path / "action.yml"
    kopie.write_text(sabotiert, encoding="utf-8")
    monkeypatch.setattr(test_aktion, "AKTION", kopie)
    monkeypatch.setattr(test_aktion, "PIN_DATEIEN", test_aktion._pin_dateien(test_aktion.WORKFLOW_ORDNER))
    with pytest.raises(AssertionError, match=r"action\.yml:\d+: actions/setup-python@v7\.1\.0"):
        test_aktion.test_jede_action_in_den_workflows_ist_auf_einen_commit_sha_gepinnt()


def test_eine_beim_anheben_vergessene_stelle_wird_rot(tmp_path, monkeypatch):
    """Eine Stelle in release.yml bleibt auf setup-python 7.0.0 stehen, ci.yml ist
    angehoben: Beide SHAs sind voll, nur der Vergleich über die Dateien sieht es."""
    import test_aktion

    test_aktion.test_jede_action_steht_in_allen_dateien_auf_derselben_sha()  # Kontrolle
    text = (REPO / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    alt = "5fda3b95a4ea91299a34e894583c3862153e4b97"  # setup-python v7.0.0, vor #580
    sabotiert, anzahl = re.subn(r"(actions/setup-python@)[0-9a-f]{40}",
                                lambda m: m.group(1) + alt, text, count=1)
    assert anzahl == 1 and alt not in text, "Sabotage greift nicht"
    kopie = tmp_path / "release.yml"
    kopie.write_text(sabotiert, encoding="utf-8")
    monkeypatch.setattr(test_aktion, "PIN_DATEIEN", [test_aktion.CI, kopie])
    with pytest.raises(AssertionError, match=r"actions/setup-python: .*5fda3b95 in release\.yml:\d+"):
        test_aktion.test_jede_action_steht_in_allen_dateien_auf_derselben_sha()


# ── #480: Code im Changelog bleibt auf dem Weg ins README Code ──────────────

def _changelog():
    """Das Modul, wie test_changelog.py es geladen hat — der Pfad nach `scripts/` steht dort."""
    from test_changelog import changelog

    return changelog


def test_ohne_ausklammerung_wird_der_code_span_umgeschrieben(tmp_path, monkeypatch):
    """Die Ausklammerung in `_absolut` zurückgebaut: Der Code geht wieder ganz
    durch `RELATIV.sub`, wie vor #480. Rot werden muss der Auszug-Test und der
    Fragment-Test am Fragment aus #469 — dieser am PR des Fragments, nicht erst
    im Release-PR."""
    changelog = _changelog()
    import test_changelog

    fragment = tmp_path / "nackte-url-424.behoben.md"
    fragment.write_text(test_changelog.FRAGMENT_469, encoding="utf-8")
    test_changelog.test_code_bleibt_im_auszug_woertlich(tmp_path, monkeypatch)    # Kontrolle
    test_changelog.test_die_umschreibung_laesst_code_stehen_und_jeden_verweis_absolut(fragment)

    monkeypatch.setattr(changelog, "_absolut", _zeile_ersetzt(
        changelog, "_absolut", "for code in CODE.finditer(rumpf):", "for code in ():"))
    with pytest.raises(AssertionError, match=r"`\[Text\]\(https://github\.com/[^`]*/main/url\)`"):
        test_changelog.test_code_bleibt_im_auszug_woertlich(tmp_path, monkeypatch)
    with pytest.raises(AssertionError, match=r"nackte-url-424\.behoben\.md: \['Code verändert'\]"):
        test_changelog.test_die_umschreibung_laesst_code_stehen_und_jeden_verweis_absolut(fragment)


def test_ohne_umschreibung_meldet_der_fragment_test_den_relativen_verweis(tmp_path, monkeypatch):
    """Die andere Richtung: `_absolut` tut nichts, der Verweis bleibt relativ."""
    changelog = _changelog()
    import test_changelog

    fragment = tmp_path / "adr-480.behoben.md"
    fragment.write_text("- Siehe [ADR](docs/entscheidungen/0001.md) (#480).\n", encoding="utf-8")
    test_changelog.test_die_umschreibung_laesst_code_stehen_und_jeden_verweis_absolut(fragment)
    monkeypatch.setattr(changelog, "_absolut", lambda rumpf: rumpf)
    with pytest.raises(AssertionError, match=r"relativ geblieben: docs/entscheidungen/0001\.md"):
        test_changelog.test_die_umschreibung_laesst_code_stehen_und_jeden_verweis_absolut(fragment)


@pytest.mark.parametrize("alt, neu, probe, erwartet", [
    (r"|[-*+][ \t]", "", "listenpunkt", "zwei Listenpunkte"),
    (r"(?:\n|[-*+]", r"(?:[-*+]", "absatz", "zwei Absätze"),
    (r"(?<!`)(?P=lauf)(?!`)", "`+", "test_ein_backtick_lauf_schliesst_nur_mit_einem_gleich_langen",
     "schloss mit einem"),
    (r"|`{3,}|~{3,}", "", "zaun", "Codezaun"),
    (r"#{1,6}(?:[ \t]|$)", "#", "test_eine_raute_ohne_leerzeichen_beendet_keinen_code_span",
     "endete an #480"),
], ids=["listenpunkt", "leerzeile", "gleich-lang", "zaun", "rautenzeile"])
def test_jede_grenze_des_code_spans_traegt(alt, neu, probe, erwartet, tmp_path, monkeypatch):
    """Je eine Grenze aus `CODE` genommen. Jede schützt einen echten Verweis
    davor, für Code gehalten zu werden und relativ nach PyPI zu gehen — oder,
    bei der Rautenzeile, Code davor, für eine Überschrift gehalten zu werden.
    `probe` ist ein Fall aus `OFFENE_BACKTICKS` oder der Name eines Tests."""
    changelog = _changelog()
    import test_changelog

    muster = changelog.CODE.pattern
    assert muster.count(alt) == 1, f"„{alt}“ steht nicht genau einmal in CODE"

    def lauf():
        if probe in test_changelog.OFFENE_BACKTICKS:
            test_changelog.test_ein_offener_backtick_schuetzt_keinen_verweis(
                *test_changelog.OFFENE_BACKTICKS[probe], tmp_path, monkeypatch)
        else:
            getattr(test_changelog, probe)(tmp_path, monkeypatch)

    lauf()                                                                         # Kontrolle
    monkeypatch.setattr(changelog, "CODE", re.compile(muster.replace(alt, neu), re.MULTILINE))
    with pytest.raises(AssertionError, match=erwartet):
        lauf()


def test_mit_der_alten_textsuche_wird_code_zum_verweis(monkeypatch):
    """Die README-Prüfung vor #480 suchte `](ziel)` im ganzen Text. Mit ihr meldet
    die Probe den Code-Span als relativen Verweis — derselbe Fehlalarm, den
    `changelog.py` sonst erst ins README getragen hätte."""
    import test_readme_auf_pypi as pypi

    pypi.test_code_ist_kein_verweis()                                              # Kontrolle
    alt = re.compile(r'\]\((?!https?:|#|mailto:)([^)]+)\)|src="(?!https?:|#)([^"]+)"')
    monkeypatch.setattr(pypi, "verweisziele",
                        lambda text: [m.group(1) or m.group(2) for m in alt.finditer(text)])
    with pytest.raises(AssertionError,
                       match=r"als relativer Verweis gemeldet: \['url', 'b', 'docs/x\.md'"):
        pypi.test_code_ist_kein_verweis()


# ── Erklärfilm: Standbild-Frame innerhalb der Komposition ───────────────────

_ERKLAERFILM_DATEIEN = {
    "package.json": "PAKET",
    "texte.json": "TEXTE",
    "Erklaerfilm.tsx": "FILM_TSX",
    "index.tsx": "WURZEL_TSX",
    "README.md": "LIESMICH",
}


def _erklaerfilm_kopie(tmp_path, monkeypatch, datei: str, alt: str, neu: str, anzahl: int = 1):
    """Eine Datei des Erklärfilms nach tmp_path, mit `alt` an genau `anzahl` Stellen
    ersetzt; die übrigen Dateien bleiben die echten."""
    import test_erklaerfilm

    attribut = _ERKLAERFILM_DATEIEN[datei]
    text = getattr(test_erklaerfilm, attribut).read_text(encoding="utf-8")
    gefunden = text.count(alt)
    assert gefunden == anzahl, (
        f"„{alt}“ steht {gefunden}-mal in {datei}, erwartet {anzahl}: Sabotage trifft anders"
    )
    kopie = tmp_path / datei
    kopie.write_text(text.replace(alt, neu), encoding="utf-8")
    monkeypatch.setattr(test_erklaerfilm, attribut, kopie)
    return test_erklaerfilm


def test_ein_standbild_frame_hinter_dem_film_wird_rot(tmp_path, monkeypatch):
    """Der Stand vor der Korrektur: Frame 800 bei 780 Frames."""
    import test_erklaerfilm

    test_erklaerfilm.test_jeder_standbild_frame_liegt_in_der_komposition()  # Kontrolle
    probe = _erklaerfilm_kopie(tmp_path, monkeypatch, "package.json", "--frame=600", "--frame=800",
                               anzahl=2)
    with pytest.raises(AssertionError, match=r"\(0 bis 779\): bild-quer: 800, bild-hoch: 800"):
        probe.test_jeder_standbild_frame_liegt_in_der_komposition()


def test_ohne_standbild_frame_wird_die_pruefung_rot(tmp_path, monkeypatch):
    """Ohne einen einzigen `--frame` liefe die Prüfung über null Befehle grün."""
    probe = _erklaerfilm_kopie(tmp_path, monkeypatch, "package.json", " --frame=600", "", anzahl=2)
    with pytest.raises(AssertionError, match="kein `--frame` in package.json gefunden"):
        probe.test_jeder_standbild_frame_liegt_in_der_komposition()


def test_ein_standbild_ohne_frame_neben_einem_mit_frame_wird_rot(tmp_path, monkeypatch):
    """Nachreview #583: Solange ein anderes Skript `--frame` trägt, fing der Zählwert
    ein Standbild ohne Frame nicht. Remotion nähme dort still Frame 0."""
    probe = _erklaerfilm_kopie(tmp_path, monkeypatch, "package.json",
                               "erklaerfilm-9x16.png --frame=600", "erklaerfilm-9x16.png")
    with pytest.raises(AssertionError, match=r"(?m)Standbild ohne `--frame`: bild-hoch$"):
        probe.test_jeder_standbild_frame_liegt_in_der_komposition()


def test_ein_frame_mit_leerzeichen_statt_gleichheitszeichen_wird_mitgeprueft(tmp_path, monkeypatch):
    """Nachreview #583: `--frame 800` versteht Remotion genauso. Die erste Fassung las
    nur `--frame=` und meldete deshalb nur bild-quer, nie bild-hoch."""
    probe = _erklaerfilm_kopie(tmp_path, monkeypatch, "package.json",
                               "erklaerfilm-9x16.png --frame=600", "erklaerfilm-9x16.png --frame 800")
    with pytest.raises(AssertionError, match=r"(?m)\(0 bis 779\): bild-hoch: 800$"):
        probe.test_jeder_standbild_frame_liegt_in_der_komposition()


def test_ein_kuerzerer_film_macht_frame_600_ungueltig(tmp_path, monkeypatch):
    """Die Grenze kommt aus texte.json, nicht aus einer Zahl im Test: 20 s × 30 FPS
    sind 600 Frames, der höchste ist 599."""
    probe = _erklaerfilm_kopie(tmp_path, monkeypatch, "texte.json", '"dauer": 26,', '"dauer": 20,')
    with pytest.raises(AssertionError, match=r"\(0 bis 599\): bild-quer: 600, bild-hoch: 600"):
        probe.test_jeder_standbild_frame_liegt_in_der_komposition()


def test_die_grenze_rundet_halbe_frames_wie_math_round(tmp_path, monkeypatch):
    """Nachreview #583: 25,55 s × 30 sind 766,5 Frames. Math.round macht daraus 767,
    Pythons round() 766. Frame 766 ist im Film, Frame 767 nicht."""
    _erklaerfilm_kopie(tmp_path, monkeypatch, "texte.json", '"dauer": 26,', '"dauer": 25.55,')
    probe = _erklaerfilm_kopie(tmp_path, monkeypatch, "package.json", "--frame=600", "--frame=766",
                               anzahl=2)
    probe.test_jeder_standbild_frame_liegt_in_der_komposition()  # mit round() wäre das rot
    zweite = tmp_path / "zweite"
    zweite.mkdir()
    _erklaerfilm_kopie(zweite, monkeypatch, "package.json", "--frame=766", "--frame=767", anzahl=2)
    with pytest.raises(AssertionError, match=r"\(0 bis 766\): bild-quer: 767"):
        probe.test_jeder_standbild_frame_liegt_in_der_komposition()


def test_ein_film_ohne_laenge_nennt_die_dauer(tmp_path, monkeypatch):
    """Nachreview #583: Mit `dauer` 0 hieß die Meldung „(0 bis -1): bild-quer: 600“ und
    zeigte auf package.json statt auf texte.yaml."""
    probe = _erklaerfilm_kopie(tmp_path, monkeypatch, "texte.json", '"dauer": 26,', '"dauer": 0,')
    with pytest.raises(AssertionError, match=r"Film ohne Länge: dauer 0 in texte\.json"):
        probe.test_jeder_standbild_frame_liegt_in_der_komposition()


def test_eine_andere_laengenformel_in_erklaerfilm_tsx_wird_rot(tmp_path, monkeypatch):
    """Nachreview #583: Der Test rechnet die Formel nach. Ändert sie sich, gälte sonst
    weiter seine alte Grenze."""
    probe = _erklaerfilm_kopie(tmp_path, monkeypatch, "Erklaerfilm.tsx",
                               "Math.round(texte.dauer * FPS);", "Math.round((texte.dauer - 1) * FPS);")
    with pytest.raises(AssertionError, match="berechnet GESAMT_FRAMES nicht mehr"):
        probe.test_jeder_standbild_frame_liegt_in_der_komposition()


def test_eine_gekuerzte_komposition_wird_rot(tmp_path, monkeypatch):
    """Nachreview #583: Nur eine der beiden Kompositionen kürzt ihre Länge selbst."""
    import test_erklaerfilm

    test_erklaerfilm.test_jede_komposition_laeuft_ueber_den_ganzen_film()  # Kontrolle
    wurzel = test_erklaerfilm.WURZEL_TSX.read_text(encoding="utf-8")
    kopie = tmp_path / "index.tsx"
    kopie.write_text(wurzel.replace("durationInFrames={GESAMT_FRAMES}",
                                    "durationInFrames={GESAMT_FRAMES - 30}", 1), encoding="utf-8")
    assert kopie.read_text(encoding="utf-8").count("{GESAMT_FRAMES - 30}") == 1
    monkeypatch.setattr(test_erklaerfilm, "WURZEL_TSX", kopie)
    with pytest.raises(AssertionError,
                       match=r"nicht jede der 2 Kompositionen setzt durationInFrames=\{GESAMT_FRAMES\}"):
        test_erklaerfilm.test_jede_komposition_laeuft_ueber_den_ganzen_film()


def test_eine_veraltete_laenge_in_der_readme_wird_rot(tmp_path, monkeypatch):
    """Nachreview #583: Die README hieß „Sechzig Sekunden“, der Film lief 26."""
    import test_erklaerfilm

    test_erklaerfilm.test_die_readme_nennt_die_laenge_aus_texte_yaml()  # Kontrolle
    probe = _erklaerfilm_kopie(tmp_path, monkeypatch, "README.md", "26 Sekunden", "25 Sekunden")
    with pytest.raises(AssertionError, match="README nennt 25 Sekunden, texte.yaml 26"):
        probe.test_die_readme_nennt_die_laenge_aus_texte_yaml()


# ── #442 N2: Der abgebrochene Zug zeigt seinen Plan auch im Text ────────────

def test_ohne_zugzeilen_im_grund_verschweigt_der_text_den_plan(monkeypatch):
    """#442 (N2): Nachbau des alten `zeilen()` — mit Grund kam nur die eine Zeile.

    Sabotiert wird nur der Zweig mit Grund; der Lauf ohne Grund behält seine
    UIDs. So ist belegt, dass die Probe am abgebrochenen Zug hängt und nicht
    an der Ausgabe überhaupt.
    """
    from falzmarke import ablage as _ablage
    from test_ablage import _antwort, _eingegangen, _postfach

    _postfach(eingang=[_eingegangen()], gesendet=[_antwort()], faehigkeiten=("IMAP4REV1",))
    bericht = _ablage.raeume_auf("joe@example.org", wunsch="Archiv", machen=True, umgebung={})
    (zug,) = bericht.zuege
    marke = f"UID {zug.uid} "

    def zeigt_uid(b):
        return any(marke in z for z in _ablage.zeilen(b))

    assert zeigt_uid(bericht), "Kontrollprobe: unsabotiert steht die UID im Text"
    echte = _ablage._zugzeilen
    monkeypatch.setattr(_ablage, "_zugzeilen", lambda b: [] if b.grund else echte(b))
    assert not zeigt_uid(bericht), "die Sabotage greift nicht"
    assert zeigt_uid(bericht._replace(grund=None)), \
        "die Sabotage trifft auch den Lauf ohne Grund"


def test_haelt_jeder_abbruch_fuer_einen_gesendeten_zug_luegt_der_text(monkeypatch):
    """Review von #459: Nachbau des alten Verhaltens, jeder Abbruch zählt als Zug.

    Bis dahin stand „ob der Server … bewegt hat, ist nicht geprüft“ auch dort,
    wo `UID MOVE` nie hinausging. `ZugAbgebrochen` auf die Oberklasse gelegt,
    macht genau das: Jeder `AblageFehler` gilt dann als gesendeter Zug.
    """
    from falzmarke import ablage as _ablage
    from test_ablage import test_scheitert_der_zug_stehen_die_uids_auch_im_text as probe

    probe()  # Kontrollprobe: unsabotiert grün
    monkeypatch.setattr(_ablage, "ZugAbgebrochen", _ablage.AblageFehler)
    with pytest.raises(AssertionError, match="nichts bewegt"):
        probe()


def test_geht_nur_die_erste_zeile_auf_stderr_stehen_die_uids_allein(monkeypatch, capsys):
    """Review von #459: Nachbau der alten Weiche, die nur nach dem Zeilenanfang ging."""
    from falzmarke import cli as _cli
    from test_ablage import test_ein_abgebrochener_bericht_steht_ganz_auf_stderr as probe

    probe(monkeypatch, capsys)  # Kontrollprobe: unsabotiert grün
    monkeypatch.setattr(_cli, "befehl_aufraeumen", _zeile_ersetzt(
        _cli, "befehl_aufraeumen", "sys.stderr if bericht.grund\n                        or ",
        "sys.stderr if "))
    with pytest.raises(AssertionError, match="auf stdout gelandet"):
        probe(monkeypatch, capsys)


# ── #442 N1: Die Teilkette des Servers geht nicht in `UID MOVE` ─────────────

def _teilkette(monkeypatch):
    """Eine Antwort mit `123`, im Eingang eine fremde Mail, deren Kennung es enthält."""
    from falzmarke import ablage as _ablage
    from test_ablage import HEUTE, _antwort, _eingegangen, _postfach

    _, sitzung = _postfach(eingang=[_eingegangen("<x123y@example.org>")],
                           gesendet=[_antwort("123")])
    with sitzung:
        return _ablage.plane(sitzung, wunsch="Archiv", heute=HEUTE.date())


def test_ohne_nachvergleich_wandert_die_fremde_mail(monkeypatch):
    from falzmarke import postfach as _postfach_modul

    assert _teilkette(monkeypatch).zuege == (), "Kontrollprobe: unsabotiert kein Zug"
    monkeypatch.setattr(_postfach_modul, "gleiche_kennung", lambda gesucht, kopfwert: True)
    bericht = _teilkette(monkeypatch)
    assert [z.kennung for z in bericht.zuege] == ["123"] and bericht.nicht_im_eingang == 0


def test_ohne_message_id_im_fetch_trifft_gar_nichts_mehr(monkeypatch):
    """Der Nachvergleich braucht die Zeile im `FETCH`, sonst leert er jeden Plan."""
    from falzmarke import ablage as _ablage, postfach as _postfach_modul
    from test_ablage import HEUTE, _antwort, _eingegangen, _postfach


    def lauf():
        _, sitzung = _postfach(eingang=[_eingegangen()], gesendet=[_antwort()])
        with sitzung:
            return _ablage.plane(sitzung, wunsch="Archiv", heute=HEUTE.date())

    assert len(lauf().zuege) == 1, "Kontrollprobe: unsabotiert ein Zug"
    ohne = tuple(z for z in _postfach_modul.KOPFZEILEN if z != "MESSAGE-ID")
    assert ohne != _postfach_modul.KOPFZEILEN, "die Sabotage greift nicht"
    monkeypatch.setattr(_postfach_modul, "KOPFZEILEN", ohne)
    assert lauf().zuege == ()


def test_mit_strip_gilt_eine_einzelne_klammer_als_paar(monkeypatch):
    """Review von #457: Nachbau des alten Vergleichs mit `strip("<>")`."""
    from falzmarke import postfach as _postfach_modul
    from test_postfach import test_gleiche_kennung_nimmt_genau_ein_klammerpaar_ab as probe

    faelle = [("abc@x>", "<abc@x>", False), ("<<abc@x>>", "<abc@x>", False)]
    for fall in faelle:
        probe(*fall)  # Kontrollprobe: unsabotiert grün
    monkeypatch.setattr(_postfach_modul, "_ohne_klammerpaar", lambda k: k.strip("<>"))
    for fall in faelle:
        with pytest.raises(AssertionError):
            probe(*fall)
    probe("abc@x", "<abc@x>", True)  # die Sabotage trifft nicht den gewollten Fall


def test_vor_dem_vergleich_gekappt_faellt_die_echte_nachricht_heraus(monkeypatch):
    """#468: `suche_kennung` holt alle Teiltreffer bis `SUCHGRENZE`. Ohne das Argument
    gilt wieder `GRENZE`, und die ältere, echte Nachricht geht vor dem Vergleich verloren."""
    from falzmarke import postfach as _postfach_modul
    from test_ablage import test_viele_teiltreffer_verdraengen_die_echte_nachricht_nicht as probe

    probe(monkeypatch)  # Kontrollprobe: unsabotiert grün
    monkeypatch.setattr(_postfach_modul.Postfach, "suche_kennung", _zeile_ersetzt(
        _postfach_modul, "Postfach.suche_kennung",
        "uids=uids, grenze=grenze)", "uids=uids)"))
    with pytest.raises(AssertionError, match=r"\['echt'\]"):
        probe(monkeypatch)


def test_ohne_filter_liefert_suche_kennung_die_teilkette(monkeypatch):
    """#468: Der exakte Vergleich steht in `suche_kennung`, nicht mehr beim Aufrufer.
    Fehlt er dort, kommt die fremde Mail mit `<x123y@…>` zurück."""
    from falzmarke import postfach as _postfach_modul
    from test_ablage import test_eine_teilkette_der_kennung_ist_kein_treffer as probe

    probe()  # Kontrollprobe: unsabotiert grün
    monkeypatch.setattr(_postfach_modul.Postfach, "suche_kennung", _zeile_ersetzt(
        _postfach_modul, "Postfach.suche_kennung",
        "if gleiche_kennung(kennung, kopf.kennung)]", "]"))
    # pytest kürzt die Meldung in der Mitte: Mit jedem neuen Feld am Ende von
    # `Kopf` (#481, #482) rückte `kennung=` weiter in den gekürzten Teil.
    monkeypatch.setattr(_postfach_modul.Kopf, "__repr__",
                        lambda kopf: f"Kopf(kennung={kopf.kennung!r})")
    with pytest.raises(AssertionError, match=r"== \[\][\s\S]*kennung='<x123y@example.org>'"):
        probe()


def test_ohne_pruefung_vor_login_geht_der_umbruch_an_imaplib(monkeypatch):
    """#442 (N4): Ohne die Prüfung in `verbinde` erreicht der Umbruch `LOGIN`.

    Dort fängt ihn nur die Attrappe ab, so wie `imaplib` ab 3.14, mit
    `ValueError`. Den macht `_befehl` seit dem Review von #460 zu einem Grund.
    Auf 3.12 fängt ihn niemand, und der Umbruch ginge auf die Leitung.
    """
    import re

    from falzmarke import postfach as _postfach_modul
    from imap_attrappe import ImapAttrappe

    adresse = "joe@example.org\r\nA1 DELETE INBOX"
    attrappe = ImapAttrappe()
    monkeypatch.setattr(_postfach_modul, "IMAP_KLASSE", attrappe)
    with pytest.raises(_postfach_modul.PostfachFehler, match="Umbruch oder ein Nullbyte"):
        _postfach_modul.verbinde(adresse, umgebung={})
    assert attrappe.verbindungen == [], "Kontrollprobe: unsabotiert keine Verbindung"

    monkeypatch.setattr(_postfach_modul, "_STEUERZEICHEN", re.compile(r"(?!)"))
    with pytest.raises(_postfach_modul.PostfachFehler, match="NUL, CR and LF"):
        _postfach_modul.verbinde(adresse, umgebung={})
    assert len(attrappe.verbindungen) == 1, "die Sabotage greift nicht"
    assert attrappe.abgemeldet == 1


def test_ohne_zitat_geht_der_anmeldename_roh_an_login(monkeypatch):
    """Review von #460: Nachbau des alten `verbinde`, der Name ging unzitiert."""
    from falzmarke import postfach as _postfach_modul
    from imap_attrappe import ImapAttrappe

    def probe():
        attrappe = ImapAttrappe()
        monkeypatch.setattr(_postfach_modul, "IMAP_KLASSE", attrappe)
        _postfach_modul.verbinde("joe {5}@example.org", umgebung={}).abmelden()
        (befehl,) = [p for p in attrappe.protokoll if p[0] == "LOGIN"]
        return befehl[1]

    assert probe() == '"joe {5}@example.org"', "Kontrollprobe: unsabotiert zitiert"
    monkeypatch.setattr(_postfach_modul, "verbinde", _zeile_ersetzt(
        _postfach_modul, "verbinde", "anmeldename = _zitiert(adresse)",
        "anmeldename = adresse"))
    assert probe() == "joe {5}@example.org", "die Sabotage greift nicht"


def test_faengt_befehl_nur_unicodeencodeerror_entkommt_der_valueerror(monkeypatch):
    """Review von #460: Nachbau des alten `_befehl` mit dem engen `except`."""
    import inspect
    import textwrap

    from falzmarke import postfach as _postfach_modul
    from test_postfach import test_ein_valueerror_aus_imaplib_ist_ein_grund_und_meldet_ab as probe

    probe(monkeypatch)  # Kontrollprobe: unsabotiert grün
    quelle = textwrap.dedent(inspect.getsource(_postfach_modul.Postfach._befehl))
    alt, neu = "OSError, ValueError)", "OSError, UnicodeEncodeError)"
    assert quelle.count(alt) == 1, "die Sabotage greift nicht"
    raum: dict = {}
    exec(compile(quelle.replace(alt, neu), inspect.getsourcefile(_postfach_modul), "exec"),
         _postfach_modul.__dict__, raum)
    monkeypatch.setattr(_postfach_modul.Postfach, "_befehl", raum["_befehl"])
    with pytest.raises(ValueError, match="NUL, CR and LF"):
        probe(monkeypatch)


# ── Nachreview vom 04.11.2026, zweite Runde: #492 ────────────────────────────

@pytest.mark.parametrize("fall, erwartet", [("fehlt", FileNotFoundError), ("kaputt", yaml.YAMLError)])
def test_ohne_das_abfangen_in_lies_geht_der_lesefehler_durch(fall, erwartet, tmp_path,
                                                              monkeypatch):
    """`_lies` (bis #493 Teil von `_analysiere_einen`) wie vor dem Nachreview von #492:
    Lesen und Parsen ohne Schutz, der rohe Fehler geht an `main()` und am Wächter vorbei."""
    import test_pflicht_checks as tpc                      # legt scripts/ auf den Pfad
    import pflicht_checks

    (tmp_path / "k").mkdir()
    (tmp_path / "s").mkdir()
    tpc.test_eine_fehlende_oder_kaputte_datei_ist_ein_workflowfehler(tmp_path / "k", fall)  # Kontrolle
    monkeypatch.setattr(pflicht_checks, "_lies", _zeile_ersetzt(
        pflicht_checks, "_lies",
        "except (OSError, UnicodeDecodeError, yaml.YAMLError) as fehler:", "except () as fehler:"))
    with pytest.raises(erwartet):
        tpc.test_eine_fehlende_oder_kaputte_datei_ist_ein_workflowfehler(tmp_path / "s", fall)


def test_mit_dem_alten_relativ_wird_ein_grosses_protokoll_umgeschrieben(tmp_path, monkeypatch):
    """`RELATIV` wie vor dem Nachreview von #492: schreibungsabhängig, `HTTPS://` gilt
    als Pfad. Der Fragment-Test nennt dasselbe Ziel, er ist das zweite Netz."""
    changelog = _changelog()
    import test_changelog

    test_changelog.test_ein_gross_geschriebenes_protokoll_bleibt_absolut(
        "HTTPS://example.org/a", tmp_path, monkeypatch)                           # Kontrolle
    monkeypatch.setattr(changelog, "RELATIV", re.compile(r"\]\((?!https?:|#|mailto:)([^)]+)\)"))
    with pytest.raises(AssertionError, match="als relativer Verweis umgeschrieben"):
        test_changelog.test_ein_gross_geschriebenes_protokoll_bleibt_absolut(
            "HTTPS://example.org/a", tmp_path, monkeypatch)
    assert test_changelog.umschreibung_befunde("- Siehe [V](HTTPS://example.org/a).\n") == [
        "absolutes Ziel verändert: HTTPS://example.org/a"]


def test_ohne_das_zuruecklegen_entsteht_ein_zweites_modulobjekt(tmp_path, monkeypatch):
    """Das Aufräumen in test_durchsetzung wie vor dem Nachreview von #492: nur `pop`,
    kein Zurücklegen der Originale."""
    import test_durchsetzung as td

    gesichert = {name: sys.modules.get(name) for name in ("durchsetzung", "repo_pruefung")}
    try:
        td.test_nach_der_werkstatt_ist_repo_pruefung_wieder_das_eine_modul(
            tmp_path / "k", monkeypatch)                                          # Kontrolle
        monkeypatch.setattr(td, "test_die_pruef_richtung_folgt_der_quelle", _zeile_ersetzt(
            td, "test_die_pruef_richtung_folgt_der_quelle",
            "sys.modules[name] = modul", "sys.modules.pop(name, None)"))
        with pytest.raises(AssertionError, match="ein zweites Modulobjekt"):
            td.test_nach_der_werkstatt_ist_repo_pruefung_wieder_das_eine_modul(
                tmp_path / "s", monkeypatch)
    finally:
        # Sonst hinterließe die Sabotage genau die zweite Modulwelt, die sie zeigt.
        for name, modul in gesichert.items():
            if modul is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = modul


def test_mit_dem_alten_feldmuster_wird_ein_grosses_feld_abgeschnitten(monkeypatch):
    """`_JSON_FELDER` wie vor dem Nachreview von #483: nur `[a-z_,]+`. Die Gegenprobe
    fehlte in #492; der Workflow liest heute nur klein geschriebene Felder."""
    import test_pr_angaben as tpa

    tpa.test_gelesene_felder_lesen_auch_grossbuchstaben()                          # Kontrolle
    monkeypatch.setattr(tpa, "_JSON_FELDER", re.compile(
        r"gh pr view\b[^\n]*?(?:\\\n[^\n]*?)*--json\s+([a-z_,]+)"))
    with pytest.raises(AssertionError, match="abgeschnitten"):
        tpa.test_gelesene_felder_lesen_auch_grossbuchstaben()


# ── Nachreview vom 04.11.2026: #479, #483, #484 ──────────────────────────────

def test_mit_dem_alten_tiefer_wird_der_kommentar_im_codeblock_zur_ueberschrift(tmp_path,
                                                                                monkeypatch):
    """`_tiefer` wie vor dem Nachreview von #484: `re.sub` über den ganzen Rumpf, Code
    eingeschlossen."""
    changelog = _changelog()
    import test_changelog

    test_changelog.test_eine_raute_im_codeblock_bleibt_eine_raute(tmp_path, monkeypatch)  # Kontrolle
    monkeypatch.setattr(changelog, "_tiefer", lambda rumpf: re.sub(
        r"^(#{1,5}) ", r"#\1 ", rumpf, flags=re.MULTILINE))
    with pytest.raises(AssertionError, match="Aus dem Kommentar wurde eine Überschrift"):
        test_changelog.test_eine_raute_im_codeblock_bleibt_eine_raute(tmp_path, monkeypatch)


@pytest.mark.parametrize("name, alt, erwartet", [
    ("HTML_ZIEL", re.compile(r'(?:src|href)="([^"]*)"'), "einfachen Anführungszeichen"),
    ("OHNE_HERKUNFT", re.compile(r"(?!https?:|#|mailto:)"), "groß geschriebenes Protokoll"),
], ids=["anfuehrungszeichen", "grossschreibung"])
def test_die_alten_muster_der_readme_pruefung_werden_namentlich_rot(name, alt, erwartet,
                                                                    monkeypatch):
    """Je ein Muster aus test_readme_auf_pypi.py auf den Stand vor dem Nachreview
    von #484 zurückgesetzt: nur doppelte Anführungszeichen, nur Kleinschreibung."""
    import test_readme_auf_pypi as trp

    trp.test_gegenprobe_die_pruefung_faengt_einen_relativen_verweis()           # Kontrolle
    monkeypatch.setattr(trp, name, alt)
    with pytest.raises(AssertionError, match=erwartet):
        trp.test_gegenprobe_die_pruefung_faengt_einen_relativen_verweis()


def test_ohne_rglob_fehlen_die_unterpakete(monkeypatch, tmp_path):
    """`_paketquellen` wie vor dem Nachreview von #479: nur die oberste Ebene."""
    import test_postfach as tp

    tp.test_die_quellen_reichen_in_die_unterpakete(tmp_path / "k")               # Kontrolle
    monkeypatch.setattr(tp, "_paketquellen", _zeile_ersetzt(
        tp, "_paketquellen", "ordner.rglob(", "ordner.glob("))
    with pytest.raises(AssertionError, match="Unterpakete fehlen"):
        tp.test_die_quellen_reichen_in_die_unterpakete(tmp_path / "s")


def test_ohne_suchgrenze_holt_suche_kennung_jeden_teiltreffer(monkeypatch):
    """`suche_kennung` wie vor dem Nachreview von #479: `grenze=len(uids)`, nie gekappt."""
    from falzmarke import postfach as _postfach_modul
    from test_ablage import (
        test_mehr_teiltreffer_als_die_suchgrenze_werden_gekappt_und_gemeldet as probe)

    probe(monkeypatch)                                                            # Kontrolle
    # Seit dem Nachreview von #492 kappt `suche_kennung` selbst, mit `grenze`.
    monkeypatch.setattr(_postfach_modul.Postfach, "suche_kennung", _zeile_ersetzt(
        _postfach_modul, "Postfach.suche_kennung", "grenze = SUCHGRENZE", "grenze = len(uids)"))
    with pytest.raises(AssertionError, match="nicht gekappt"):
        probe(monkeypatch)


# Nachreview von #492, Befund 1: Die Suchkappung stand unter dem Ordnernamen in
# `gekappt`. Die Sabotage baut genau diese Zeile nach.
_SUCHKAPPUNG_492 = "self.suchkappungen.append((ordner, kennung, len(uids), grenze))"
_ALS_ORDNERKAPPUNG_492 = "self.gekappt[ordner] = (len(uids), grenze)"


def test_als_ordnerkappung_meldet_die_suche_einen_ungekappten_ordner(monkeypatch):
    from falzmarke import postfach as _postfach_modul
    from test_ablage import test_eine_gekappte_suche_meldet_die_kennung_nicht_den_ordner as probe

    probe(monkeypatch)                                                            # Kontrolle
    monkeypatch.setattr(_postfach_modul.Postfach, "suche_kennung", _zeile_ersetzt(
        _postfach_modul, "Postfach.suche_kennung", _SUCHKAPPUNG_492, _ALS_ORDNERKAPPUNG_492))
    with pytest.raises(AssertionError, match="Suchkappung als Ordnerkappung gemeldet"):
        probe(monkeypatch)


def test_als_ordnerkappung_ueberschreibt_die_suche_die_echte_kappung(monkeypatch):
    from falzmarke import postfach as _postfach_modul
    from test_ablage import test_eine_suche_ueberschreibt_die_kappung_des_ordners_nicht as probe

    probe(monkeypatch)                                                            # Kontrolle
    monkeypatch.setattr(_postfach_modul.Postfach, "suche_kennung", _zeile_ersetzt(
        _postfach_modul, "Postfach.suche_kennung", _SUCHKAPPUNG_492, _ALS_ORDNERKAPPUNG_492))
    with pytest.raises(AssertionError,
                       match=r"die Suche überschrieb die Ordnerkappung: \{'INBOX': \(5, 3\)\}"):
        probe(monkeypatch)


def test_ohne_eigenen_satz_bleibt_die_gekappte_suche_stumm(monkeypatch):
    from falzmarke import ablage as _ablage
    from test_ablage import test_eine_gekappte_suche_meldet_die_kennung_nicht_den_ordner as probe

    probe(monkeypatch)                                                            # Kontrolle
    monkeypatch.setattr(_ablage, "_kappungen", _zeile_ersetzt(
        _ablage, "_kappungen", "in sitzung.suchkappungen)", "in [])"))
    with pytest.raises(AssertionError, match="Suchkappung ohne Hinweis"):
        probe(monkeypatch)


# #522, Befund 3: je Kennung eine Suche in `ablage.plane`. Bis dahin entdoppelte
# eine Prüfung in `Postfach.suche_kennung` nur den Bericht (#515, Befund 2), die
# Suche lief je Antwort. Sie ist mit #522 entfallen, der Schutz liegt jetzt hier.
_EINMAL_522 = "if schluessel not in gesucht_je_kennung:"
_SCHLUESSEL_522 = "schluessel = postfach._ohne_klammerpaar(kennung)"


@pytest.mark.parametrize("anker, ersatz, probe_name, meldung", [
    (_EINMAL_522, "if True:",
     "test_drei_antworten_auf_eine_kennung_suchen_einmal", "3 Suchen für eine Kennung"),
    (_EINMAL_522, "if True:",
     "test_eine_gekappte_suche_steht_nur_einmal_im_bericht", "3-mal gemeldet"),
    (_SCHLUESSEL_522, "schluessel = kennung",
     "test_eine_kennung_mit_und_ohne_klammern_sucht_einmal", "2 Suchen für eine Message-ID"),
    (_SCHLUESSEL_522, 'schluessel = ""',
     "test_zwei_kennungen_suchen_zweimal", "gesucht: "),
    (_SCHLUESSEL_522, 'schluessel = ""',
     "test_eine_zweite_gekappte_kennung_bekommt_ihren_eigenen_satz", "456: 0-mal gemeldet"),
], ids=["ohne-merken-zaehlt", "ohne-merken-bericht", "roher-schluessel",
        "ein-schluessel-zaehlt", "ein-schluessel-bericht"])
def test_ohne_das_merken_je_kennung(monkeypatch, anker, ersatz, probe_name, meldung):
    """„ohne-merken“ baut den Stand vor #522 nach, ohne die Prüfung aus #515: Jede
    Antwort sucht neu, jede Kappung steht im Bericht. „roher-schluessel“ ist der
    Klammer-Befund (#522/11), „ein-schluessel“ eine Sperre, die jede weitere
    Kennung auf die erste Suche wirft (die Sabotage aus #515 „nur-der-ordner-zaehlt“)."""
    import test_ablage
    from falzmarke import ablage as _ablage
    probe = getattr(test_ablage, probe_name)

    probe(monkeypatch)                                                            # Kontrolle
    monkeypatch.setattr(_ablage, "plane", _zeile_ersetzt(_ablage, "plane", anker, ersatz))
    with pytest.raises(AssertionError, match=meldung):
        probe(monkeypatch)


# Nachreview von #524, Befund 1: gesucht wird mit dem Schlüssel, nicht mit der
# Form der ersten Antwort. „erste-form“ ist der Code aus #524 Wort für Wort.
_SUCHE_524 = "EINGANG, schluessel or kennung)"


@pytest.mark.parametrize("ersatz, probe_name, argumente, meldung", [
    ("EINGANG, kennung)",
     "test_eine_kopfzeile_ohne_klammern_findet_sich_in_jeder_reihenfolge", (True,),
     "Kopfzeile ohne Klammern nicht gefunden"),
    ("EINGANG, schluessel)",
     "test_leere_klammern_suchen_nicht_nach_nichts", (), "gesucht: "),
], ids=["erste-form", "leerer-schluessel"])
def test_ohne_die_suche_mit_dem_schluessel(monkeypatch, ersatz, probe_name, argumente, meldung):
    """„erste-form“ stellt #524 wieder her: `<abc@x>` zuerst, die Kopfzeile trägt
    `abc@x`, und die zweite Antwort erbt das leere Ergebnis. „leerer-schluessel“
    nimmt den Rückfall auf die rohe Kennung bei `<>` weg."""
    import test_ablage
    from falzmarke import ablage as _ablage
    probe = getattr(test_ablage, probe_name)

    probe(monkeypatch, *argumente)                                                # Kontrolle
    monkeypatch.setattr(_ablage, "plane", _zeile_ersetzt(_ablage, "plane", _SUCHE_524, ersatz))
    with pytest.raises(AssertionError, match=meldung):
        probe(monkeypatch, *argumente)


def test_ohne_das_abfangen_reisst_der_workflowfehler_den_waechter_ab(tmp_path, monkeypatch):
    """`_pruefe_pflicht_checks` wie vor dem Nachreview von #483: der Fehler geht durch.

    Das Modul kommt aus `trp`, nicht per `import`: `test_durchsetzung` wirft
    `repo_pruefung` aus `sys.modules`, danach liefert ein neuer Import ein zweites
    Modulobjekt, und die Sabotage träfe das falsche (gemessen am 04.11.2026, nur
    in der ganzen Suite rot).
    """
    import test_repo_pruefung as trp
    import pflicht_checks
    repo_pruefung = trp.repo_pruefung

    monkeypatch.setattr(repo_pruefung, "registry_namen", lambda name, **_: [name])  # kein Netz
    trp.test_ein_unbrauchbarer_pflicht_workflow_ist_ein_befund_kein_absturz(tmp_path)  # Kontrolle
    monkeypatch.setattr(repo_pruefung, "_pruefe_pflicht_checks", _zeile_ersetzt(
        repo_pruefung, "_pruefe_pflicht_checks",
        "except pflicht_checks.Workflowfehler as fehler:", "except () as fehler:"))
    with pytest.raises(pflicht_checks.Workflowfehler, match="startet nicht bei pull_request"):
        trp.test_ein_unbrauchbarer_pflicht_workflow_ist_ein_befund_kein_absturz(tmp_path)


def test_ohne_das_abfangen_endet_das_skript_mit_traceback(tmp_path, monkeypatch, capsys):
    """`main` wie vor dem Nachreview von #483: `Workflowfehler` statt Exit 1."""
    import test_pflicht_checks as tpc                      # legt scripts/ auf den Pfad
    import pflicht_checks

    tpc.test_das_skript_meldet_einen_unbrauchbaren_workflow_statt_abzustuerzen(
        tmp_path, monkeypatch, capsys)                                            # Kontrolle
    monkeypatch.setattr(pflicht_checks, "main", _zeile_ersetzt(
        pflicht_checks, "main", "except Workflowfehler as fehler:", "except () as fehler:"))
    with pytest.raises(pflicht_checks.Workflowfehler):
        tpc.test_das_skript_meldet_einen_unbrauchbaren_workflow_statt_abzustuerzen(
            tmp_path, monkeypatch, capsys)
