"""Eine Mail-Adresse, Domain oder URL wird im Brief nicht getrennt.

Anlass, an versendeten Briefen beobachtet:

- 14.10.2026: „servus@blitzsicht.com“ stand als „ser-“ am Zeilenende und
  „vus@blitzsicht.com“ in der nächsten Zeile.
- 14.10.2026: „blitzsicht.com/da-“ / „tenschutz“ — eine URL mit Pfad.
- 17.10.2026: wieder „ser-vus@…“ und „daten-schutz“ in einer URL.

`verify` meldete jedes Mal grün: Alle Maße stimmten. Diese Datei hält fest,
dass der Emitter jedes Wort mit Adresse unteilbar setzt
(`emit.as_text`, `netzadressen.zerlege`), dass normaler Text weiter getrennt
wird, und dass `verify` eine getrennte Adresse im fertigen PDF findet
(`netzadressen.getrennt`, Prüfung „Netzadressen ungetrennt“).

Der Satz wird an `tests/fixtures/trennung/adressen.md` gemessen, und zwar
zweimal: mit dem Schutz und ohne. Ohne Schutz müssen alle vier Adressen
getrennt sein — sonst belegte das grüne Ergebnis mit Schutz nur, dass die
Adressen zufällig nicht am Zeilenende stehen. Die Sabotage für `verify` steht
in `tests/test_gegenbeweis.py`.
"""

from __future__ import annotations

from pathlib import Path

import pdfplumber
import pytest

from falzmarke import cli, emit, geometrie, netzadressen
from conftest import REPO, URKUNDE_BEISPIELE

QUELLE = REPO / "tests" / "fixtures" / "trennung" / "adressen.md"

#: Was in der Quelle steht und im PDF in EINER Zeile stehen muss.
ADRESSEN = (
    "servus@blitzsicht.com",               # Mail-Adresse
    "blitzsicht.com/datenschutz",          # Domain mit Pfad
    "https://blitzsicht.com/datenschutz",  # URL mit Schema
    "muster-sanierungen.de",               # Domain mit eigenem Bindestrich
)

PRUEFUNG = "Netzadressen ungetrennt"


def _zeilen(pdf: Path) -> list[list[str]]:
    """Je Seite die Textzeilen, so wie pdfplumber sie liest."""
    with pdfplumber.open(str(pdf)) as dokument:
        return [(seite.extract_text() or "").splitlines() for seite in dokument.pages]


def _ohne_schutz(text: str) -> list[tuple[str, bool]]:
    """Der Stand vor dem Fix: kein Wort gilt als Adresse."""
    return [(text, False)]


@pytest.fixture(scope="module")
def gesetzt(tmp_path_factory) -> dict[str, Path]:
    """Die Probe einmal mit und einmal ohne Schutz gesetzt."""
    ziel = tmp_path_factory.mktemp("netzadressen")
    mit, _ = cli.rendere(QUELLE, ziel / "mit.pdf")
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(netzadressen, "zerlege", _ohne_schutz)
        ohne, _ = cli.rendere(QUELLE, ziel / "ohne.pdf")
    return {"mit": mit, "ohne": ohne}


# ── Die Probe trennt ohne Schutz wirklich ───────────────────────────────────

def test_ohne_schutz_ist_jede_adresse_getrennt(gesetzt):
    """Gegenprobe zur Probe: Sie reproduziert alle vier Fälle.

    Mail-Adresse und URL-Pfad per Silbentrennung, die URL mit Schema ohne
    Strich am Punkt, die Domain an ihrem eigenen Bindestrich.
    """
    befunde = [t for seite in _zeilen(gesetzt["ohne"]) for t in netzadressen.getrennt(seite)]
    gefunden = {(t.ende, t.anfang, t.art) for t in befunde}
    assert gefunden == {
        ("ser-", "vus@blitzsicht.com", "trennstrich"),
        ("blitzsicht.com/daten-", "schutz", "trennstrich"),
        ("https://blitzsicht.", "com/datenschutz.", "umbruch"),
        ("muster-", "sanierungen.de", "trennstrich"),
    }, befunde


def test_ohne_schutz_meldet_verify_die_trennung(gesetzt):
    bericht = geometrie.pruefe(gesetzt["ohne"], "B")
    pruefung = next(p for p in bericht.pruefungen if p.name == PRUEFUNG)
    assert not pruefung.bestanden
    assert "ser- ⏎ vus@blitzsicht.com" in pruefung.ist
    assert "(+3 weitere)" in pruefung.ist
    assert not bericht.ok


# ── Mit Schutz: keine Adresse getrennt, normaler Text schon ─────────────────

def test_mit_schutz_ist_keine_adresse_getrennt(gesetzt):
    befunde = [t for seite in _zeilen(gesetzt["mit"]) for t in netzadressen.getrennt(seite)]
    assert befunde == []


@pytest.mark.parametrize("adresse", ADRESSEN)
def test_mit_schutz_steht_jede_adresse_in_einer_zeile(gesetzt, adresse):
    """Nicht nur „kein Befund“: Jede Adresse steht ganz in einer Zeile, so oft wie in der Quelle."""
    zeilen = [z for seite in _zeilen(gesetzt["mit"]) for z in seite]
    quelle = QUELLE.read_text(encoding="utf-8").split("\n---\n", 1)[1]
    erwartet = quelle.count(adresse)
    assert erwartet > 0
    assert sum(z.count(adresse) for z in zeilen) == erwartet


def test_mit_schutz_wird_normaler_text_weiter_getrennt(gesetzt):
    """Der Schutz gilt der Adresse, nicht dem Absatz: „Daten-“ / „schutz“ bleibt."""
    for seite in _zeilen(gesetzt["mit"]):
        for oben, unten in zip(seite, seite[1:]):
            if oben.endswith("im Daten-") and unten.startswith("schutz unter"):
                return
    pytest.fail("Das Wort „Datenschutz“ im Fließtext ist nicht mehr getrennt — "
                "der Schutz greift über die Adresse hinaus.")


def test_mit_schutz_besteht_verify(gesetzt):
    bericht = geometrie.pruefe(gesetzt["mit"], "B")
    pruefung = next(p for p in bericht.pruefungen if p.name == PRUEFUNG)
    assert pruefung.bestanden, pruefung
    assert pruefung.ist == "keine"
    assert bericht.ok, [p for p in bericht.pruefungen if not p.bestanden]


def test_die_urkunde_misst_dasselbe():
    """Auch die Urkunde setzt ihren Text über `emit` — sie wird ebenso gemessen."""
    assert URKUNDE_BEISPIELE
    pdf, _ = cli.rendere(URKUNDE_BEISPIELE[0], None)
    namen = {p.name for p in geometrie.pruefe(pdf, "").pruefungen}
    assert PRUEFUNG in namen


# ── Der Emitter ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("wort", [
    "servus@blitzsicht.com",
    "blitzsicht.com",
    "muster-sanierungen.de",
    "blitzsicht.com/datenschutz",
    "https://blitzsicht.com/datenschutz",
    "www.example.de",
    "bäckerei-zink.de",
])
def test_ein_wort_mit_adresse_ist_unteilbar(wort):
    assert emit.as_text(f"Bitte an {wort} schreiben.") == (
        f'#text("Bitte an ")#box(text(hyphenate: false, "{wort}"))#text(" schreiben.")')


def test_satzzeichen_bleiben_an_der_adresse():
    """Ein Komma oder eine Klammer darf nicht allein am nächsten Zeilenanfang stehen."""
    assert emit.as_text("(servus@blitzsicht.com), danach") == (
        '#box(text(hyphenate: false, "(servus@blitzsicht.com),"))#text(" danach")')


@pytest.mark.parametrize("text", [
    "Fragen gern an mich.",
    "z. B. 5 kg, Nr. 3.5 und u. a. m.",
    "Ende.Die nächste Zeile",          # fehlender Leerschritt, keine Domain
    "Version 1.2.3 und 3.14 Euro",
    "",
])
def test_text_ohne_adresse_wird_gesetzt_wie_bisher(text):
    """Byte für Byte die Ausgabe von vorher: ein einziges `#text(…)`."""
    assert emit.as_text(text, typografie_anwenden=False) == f"#text({emit.zeichenkette(text)})"


def test_eine_ueberlange_adresse_bekommt_nur_keine_silbentrennung():
    """Als Box bräche sie in sich um, und das Wort danach rutschte neben ihre erste Zeile.

    Ohne Box darf Typst sie umbrechen, aber nicht mit Trennstrich trennen —
    und bricht sie, meldet es `verify` (`test_verify_meldet_jeden_umbruch_der_langen_url`).
    """
    lang = "https://example.de/" + "a" * netzadressen.UNTEILBAR_BIS
    gesetzt = emit.as_text(f"Siehe {lang} dort")
    assert f'#text(hyphenate: false, "{lang}")' in gesetzt
    assert "#box(" not in gesetzt
    grenze = "https://example.de/" + "a" * (netzadressen.UNTEILBAR_BIS - len("https://example.de/"))
    assert len(grenze) == netzadressen.UNTEILBAR_BIS
    assert f'#box(text(hyphenate: false, "{grenze}"))' in emit.as_text(f"Siehe {grenze} dort")


def test_die_typografie_laeuft_weiter_ueber_den_ganzen_text():
    """Anführungszeichen um eine Adresse werden als Paar erkannt und mit ihr zusammengehalten."""
    assert emit.as_text('Siehe "blitzsicht.com" dort') == (
        '#text("Siehe ")#box(text(hyphenate: false, "„blitzsicht.com“"))#text(" dort")')


# ── Die Erkennung ───────────────────────────────────────────────────────────

def test_zerlege_haelt_den_text_vollstaendig():
    text = "Fragen an servus@blitzsicht.com, oder (blitzsicht.com/datenschutz). Danke"
    teile = netzadressen.zerlege(text)
    assert "".join(t for t, _ in teile) == text
    assert [t for t, adresse in teile if adresse] == [
        "servus@blitzsicht.com,", "(blitzsicht.com/datenschutz)."]


@pytest.mark.parametrize("zeilen, erwartet", [
    # Die beobachteten Fälle, einmal wie pdftotext sie liest (weiches
    # Trennzeichen), einmal wie pdfplumber (Bindestrich).
    (["unter ser­", "vus@blitzsicht.com oder"], "trennstrich"),
    (["unter ser-", "vus@blitzsicht.com oder"], "trennstrich"),
    (["unter blitzsicht.com/da-", "tenschutz und"], "trennstrich"),
    (["auf https://blitzsicht.", "com/datenschutz."], "umbruch"),
    (["auf https://", "blitzsicht.com/datenschutz."], "umbruch"),
    (["an servus@blitzsicht.", "com schreiben"], "umbruch"),
    (["mehr unter muster-", "sanierungen.de und"], "trennstrich"),
    (["an info@muster-", "sanierungen.de schreiben"], "trennstrich"),
    # Über 60 Zeichen, also ohne Box: nach „/“, mitten im Wort, nach „www.x.“
    # (gerendert in `lange-url.md`).
    (["unter https://www.blitzsicht.com/leistungen/handwerksbetriebe/",
      "regensburg/preisliste nachlesen."], "ueberlang"),
    (["unter https://www.blitzsicht.com/leistungen/handwerk",
      "sbetriebe/regensburg/preisliste nachlesen."], "ueberlang"),
    (["unter https://www.blitzsicht.", "com/leistungen/handwerksbetriebe/regensburg/preisliste"],
     "ueberlang"),
])
def test_eine_getrennte_adresse_wird_gefunden(zeilen, erwartet):
    befunde = netzadressen.getrennt(zeilen)
    assert [t.art for t in befunde] == [erwartet]
    assert befunde[0].zeile == 0


@pytest.mark.parametrize("zeilen", [
    ["die Neuge-", "staltung Ihrer Seite"],              # normale Silbentrennung
    ["Fragen gern unter", "servus@blitzsicht.com oder"],  # Umbruch VOR der Adresse
    ["unter servus@blitzsicht.com", "oder telefonisch"],  # Umbruch NACH der Adresse
    ["Siehe https://blitzsicht.com.", "Die Seite"],       # ganze URL, Satzende
    # Eine ganze URL mit Schrägstrich am Ende, dann ein neues Wort. Gedruckt
    # sieht ein Umbruch nach „/“ genauso aus; dass es keiner ist, steht nur
    # über die Länge fest: 35 Zeichen hätte der Emitter als Box gesetzt.
    ["Siehe https://blitzsicht.com/", "finden Sie"],
    # Über der Grenze, aber das nächste Wort beginnt groß: neuer Satz, neuer
    # Absatz oder ein Substantiv — keine Fortsetzung der URL.
    ["unter https://www.blitzsicht.com/leistungen/handwerksbetriebe/regensburg/preisliste.",
     "Mit freundlichen Grüßen"],
    ["unter https://www.blitzsicht.com/leistungen/handwerksbetriebe/regensburg/preisliste",
     "Die Seite"],
    ["das ist z. B.", "die Frage"],
    ["ca.", "drei Wochen"],
    ["und/", "oder"],
    ["die E-Mail-", "Adresse"],
    ["Ihre Website -", "servus@blitzsicht.com"],          # Strich als Gedankenstrich
    ["", "servus@blitzsicht.com"],
])
def test_richtig_umbrochener_text_ist_kein_befund(zeilen):
    assert netzadressen.getrennt(zeilen) == []


# ── Review von #397 ─────────────────────────────────────────────────────────
#
# Jede Probe ist so gebaut, dass sie den Fall wirklich herstellt; die
# Gegenprobe steht jeweils daneben oder in `tests/test_gegenbeweis.py`.

FIXTURES = REPO / "tests" / "fixtures" / "trennung"


def _bericht(pdf: Path, form: str = "B"):
    bericht = geometrie.pruefe(pdf, form)
    return bericht, next(p for p in bericht.pruefungen if p.name == PRUEFUNG)


def _alle_befunde(pdf: Path, unteilbar_bis: int = netzadressen.UNTEILBAR_BIS) -> set:
    with pdfplumber.open(str(pdf)) as dokument:
        return {(t.ende.replace("­", "-"), t.anfang, t.art)
                for seite in dokument.pages
                for zeilen, grenze in geometrie._textfluesse(seite, unteilbar_bis)
                for t in netzadressen.getrennt(zeilen, grenze)}


# Der Ort im Satz entscheidet über die Box ─────────────────────────────────

ORTE = """|   |   |
|---|---|
| E-Mail | servus@blitzsicht.com |

## Fragen an servus@blitzsicht.com

- an servus@blitzsicht.com
- oder per Post

> an servus@blitzsicht.com

| Stelle | Kontakt |
|---|---|
| Vertrieb | servus@blitzsicht.com |
"""

BOX = '#box(text(hyphenate: false, "servus@blitzsicht.com"))'
OHNE_BOX = '#text(hyphenate: false, "servus@blitzsicht.com")'


def test_eine_box_gibt_es_nur_im_fliesstext():
    """Überschrift, Liste, Zitat: Box. Gerahmte Tabelle und Angaben: keine.

    In einer Zelle mit `auto`-Breite bricht eine Box in sich um, und der Text
    dahinter landet neben ihrer ersten Zeile (`test_text_nach_der_adresse_*`).
    In Überschrift, Liste und Zitat ist am 17.10.2026 eine Adresse aus 59
    Zeichen gerendert worden: Sie rückt als Ganzes in die nächste Zeile und
    endet bei 139 mm, weit vor dem rechten Rand.
    """
    from falzmarke import markdown

    gesetzt = emit.setze(markdown.lies(ORTE, dialekt="1.2"))
    bloecke = gesetzt.split("\n\n")
    assert [BOX in b for b in bloecke] == [False, True, True, True, False], bloecke
    assert OHNE_BOX in bloecke[0] and OHNE_BOX in bloecke[4]


def test_im_blocksatz_gilt_die_kleinere_grenze():
    from falzmarke import markdown

    adresse = "info@" + "x" * 30 + "-regensburg.de"
    assert netzadressen.UNTEILBAR_BIS_BLOCKSATZ < len(adresse) <= netzadressen.UNTEILBAR_BIS
    bloecke = markdown.lies(f"Bitte an {adresse} schreiben.")
    assert "#box(" in emit.setze(bloecke)
    assert "#box(" not in emit.setze(bloecke, blocksatz=True)
    assert f'#text(hyphenate: false, "{adresse}")' in emit.setze(bloecke, blocksatz=True)


# Tabellenzelle: kein verschobener Text, und die Trennung wird gemeldet ─────

def _zellentext(pdf: Path) -> str:
    """Der Text der Zelle mit der Adresse, Zeile für Zeile aneinandergehängt."""
    with pdfplumber.open(str(pdf)) as dokument:
        for zeilen, _ in geometrie._textfluesse(dokument.pages[0], netzadressen.UNTEILBAR_BIS):
            text = " ".join(zeilen)
            if "Schreiben Sie" in text:
                return text
    raise AssertionError("Zelle mit der Adresse nicht gefunden")


@pytest.fixture(scope="module")
def zelle(tmp_path_factory) -> dict[str, Path]:
    """Die Probe einmal wie gesetzt und einmal mit Box in der Zelle (Sabotage)."""
    ziel = tmp_path_factory.mktemp("zelle")
    mit, _ = cli.rendere(FIXTURES / "tabelle-zelle.md", ziel / "ohne-box.pdf")
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(emit, "_IN_DER_ZELLE", netzadressen.UNTEILBAR_BIS)
        box, _ = cli.rendere(FIXTURES / "tabelle-zelle.md", ziel / "box.pdf")
    return {"ohne_box": mit, "box": box}


def test_text_nach_der_adresse_steht_hinter_ihr(zelle):
    assert "regensburg.de oder rufen Sie an." in _zellentext(zelle["ohne_box"])


def test_text_nach_der_adresse_rutscht_mit_box_neben_sie(zelle):
    """Sabotage: Box in der Zelle.

    Gemessen: „…sanierungen- oder“ / „regensburg.de“ / „rufen Sie an.“
    """
    text = _zellentext(zelle["box"])
    assert "regensburg.de oder" not in text
    assert "oder regensburg.de" in text


def test_in_der_zelle_meldet_verify_die_getrennte_adresse(zelle):
    bericht, pruefung = _bericht(zelle["ohne_box"])
    assert not pruefung.bestanden
    assert pruefung.ist == "Seite 1: „vertrieb-nord@muster- ⏎ sanierungen-regensburg.de“"
    assert {p.name for p in bericht.pruefungen if not p.bestanden} == {PRUEFUNG}


# Spalten: kein Fehlalarm über Zellgrenzen ──────────────────────────────────

def test_spalten_alte_paarung_schlaegt_falsch_an(tmp_path):
    """Gegenprobe: Die Probe stellt den Fehlalarm wirklich her, wenn ganze Höhen gepaart werden."""
    pdf, _ = cli.rendere(FIXTURES / "tabelle-spalten.md", tmp_path / "spalten.pdf")
    with pdfplumber.open(str(pdf)) as dokument:
        zeilen = [" ".join(s.text for s in sorted(z, key=lambda s: s.x0))
                  for z in geometrie._zeilen_gruppieren(geometrie._spans(dokument.pages[0]))]
    assert [str(t) for t in netzadressen.getrennt(zeilen)] == [
        "„Leistungsbeschrei- ⏎ servus@blitzsicht.com“"]


def test_spalten_ohne_fehlalarm(tmp_path):
    pdf, form = cli.rendere(FIXTURES / "tabelle-spalten.md", tmp_path / "spalten.pdf")
    bericht, pruefung = _bericht(pdf, form)
    assert pruefung.bestanden, pruefung
    assert bericht.ok, [p for p in bericht.pruefungen if not p.bestanden]


def _span(text, x0, x1):
    return geometrie.Span(text=text, x0=x0, y0=100.0, x1=x1, y1=104.0, groesse=11.0,
                          fett=False, font="Probe")


@pytest.mark.parametrize("luecken, abschnitte", [
    ([1.1, 1.1, 1.1], 1),         # Fließtext
    ([3.6, 3.5, 3.6, 3.5], 1),    # Blocksatz, weit ausgetrieben: keine Spalte
    ([1.1, 60.0, 1.1], 2),        # Anschrift | Informationsblock
    ([4.0], 2),                   # Angaben: Bezeichnung | Wert
    ([4.0, 1.1, 1.2, 1.1], 2),
])
def test_abschnitte_trennt_an_spaltenluecken(luecken, abschnitte):
    spans, x = [], 25.0
    for nummer, luecke in enumerate([0.0, *luecken]):
        x += luecke
        spans.append(_span(f"w{nummer}", x, x + 10.0))
        x += 10.0
    assert len(geometrie._abschnitte(spans)) == abschnitte


# Lange URL: der Umbruch nach „/“ und mitten im Wort ───────────────────────

LANGE_URL_BEFUNDE = {
    ("https://www.blitzsicht.com/leistungen/handwerksbetriebe/", "regensburg/preisliste",
     "ueberlang"),
    ("https://www.blitzsicht.com/leistungen/handwerk", "sbetriebe/regensburg/preisliste",
     "ueberlang"),
    ("https://www.blitzsicht.", "com/leistungen/handwerksbetriebe/regensburg/preisliste",
     "ueberlang"),
}


def test_die_lange_url_bricht_wirklich_um(tmp_path):
    """Gegenprobe zur Probe: Die URL (77 Zeichen) steht in keinem Absatz ganz in einer Zeile."""
    pdf, _ = cli.rendere(FIXTURES / "lange-url.md", tmp_path / "lange-url.pdf")
    url = "https://www.blitzsicht.com/leistungen/handwerksbetriebe/regensburg/preisliste"
    assert len(url) > netzadressen.UNTEILBAR_BIS
    assert sum(z.count(url) for seite in _zeilen(pdf) for z in seite) == 0
    assert _alle_befunde(pdf) == LANGE_URL_BEFUNDE


def test_verify_meldet_jeden_umbruch_der_langen_url(tmp_path):
    pdf, form = cli.rendere(FIXTURES / "lange-url.md", tmp_path / "lange-url.pdf")
    _, pruefung = _bericht(pdf, form)
    assert not pruefung.bestanden
    assert pruefung.ist.startswith(
        "Seite 1: „https://www.blitzsicht.com/leistungen/handwerksbetriebe/ ⏎ regensburg/")
    assert pruefung.ist.endswith("(+2 weitere)")


@pytest.mark.parametrize("zeilen", [
    ["Siehe https://blitzsicht.com/", "datenschutz"],
    ["Siehe https://blitzsicht.com/", "finden Sie"],
])
def test_in_der_zelle_ist_jeder_umbruch_nach_schraegstrich_ein_befund(zeilen):
    """In einer Zelle gibt es keine Box (Grenze 0), also auch keinen sicheren Umbruch nach „/“."""
    assert netzadressen.getrennt(zeilen) == []
    assert [t.art for t in netzadressen.getrennt(zeilen, 0)] == ["ueberlang"]


# Blocksatz: keine gestreckte Zeile vor der Adresse ─────────────────────────

BLOCKSATZ_ADRESSE = "ansprechpartnerin.vertrieb@muster-sanierungen-regensburg.de"


def _streckung(pdf: Path) -> float:
    """Die größte Wortlücke in der Zeile mit dem Anfang der Adresse und in der davor (mm)."""
    with pdfplumber.open(str(pdf)) as dokument:
        zeilen = [sorted(z, key=lambda s: s.x0)
                  for z in geometrie._zeilen_gruppieren(geometrie._spans(dokument.pages[0]))]
    nummer = next(i for i, z in enumerate(zeilen)
                  if any(s.text.startswith("ansprechpartnerin") for s in z))
    return max(b.x0 - a.x1 for z in zeilen[nummer - 1:nummer + 1] for a, b in zip(z, z[1:]))


@pytest.fixture(scope="module")
def blocksatz(tmp_path_factory) -> dict[str, Path]:
    """Die Urkunde im Blocksatz, einmal wie gesetzt und einmal mit der Grenze des Fließtexts."""
    ziel = tmp_path_factory.mktemp("blocksatz")
    mit, _ = cli.rendere(FIXTURES / "urkunde-blocksatz.md", ziel / "40.pdf")
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(netzadressen, "UNTEILBAR_BIS_BLOCKSATZ", netzadressen.UNTEILBAR_BIS)
        alt, _ = cli.rendere(FIXTURES / "urkunde-blocksatz.md", ziel / "60.pdf")
    return {"40": mit, "60": alt}


def test_im_blocksatz_streckt_die_adresse_keine_zeile(blocksatz):
    """Gemessen am 17.10.2026: 1,0 mm mit der Grenze 40, 10,9 mm mit der Grenze 60."""
    assert len(BLOCKSATZ_ADRESSE) == 59
    assert _streckung(blocksatz["40"]) < 2.5


def test_mit_der_grenze_des_fliesstexts_klafft_die_zeile(blocksatz):
    """Sabotage: Die Box rückt in die nächste Zeile, und der Blocksatz treibt die davor aus."""
    assert _streckung(blocksatz["60"]) > 8.0


def test_im_blocksatz_meldet_verify_die_adresse_ueber_der_grenze(blocksatz):
    """Der Preis der kleineren Grenze: Die Adresse bricht am Bindestrich, und das ist ein Befund."""
    bericht, pruefung = _bericht(blocksatz["40"], "")
    assert pruefung.ist == (
        "Seite 1: „ansprechpartnerin.vertrieb@muster-sanierungen- ⏎ regensburg.de“")
    assert {p.name for p in bericht.pruefungen if not p.bestanden} == {PRUEFUNG}


# Urkunde: eine Adresse am Zeilenende ───────────────────────────────────────

def test_die_urkunde_haelt_eine_adresse_am_zeilenende_zusammen(tmp_path):
    quelle = FIXTURES / "urkunde-zeilenende.md"
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(netzadressen, "zerlege", _ohne_schutz)
        ohne, _ = cli.rendere(quelle, tmp_path / "ohne.pdf")
    assert _bericht(ohne, "")[1].ist == "Seite 1: „ser- ⏎ vus@blitzsicht.com“"

    mit, _ = cli.rendere(quelle, tmp_path / "mit.pdf")
    bericht, pruefung = _bericht(mit, "")
    assert geometrie.typ_aus_metadaten(mit) == "urkunde"
    assert pruefung.bestanden, pruefung
    assert bericht.ok, [p for p in bericht.pruefungen if not p.bestanden]
    assert sum(z.count("servus@blitzsicht.com") for seite in _zeilen(mit) for z in seite) == 1


# Betreff: vom Emitter nicht erreicht, von verify gefunden ──────────────────

def test_eine_getrennte_adresse_im_betreff_wird_gemeldet(tmp_path):
    pdf, form = cli.rendere(FIXTURES / "betreff.md", tmp_path / "betreff.pdf")
    with pdfplumber.open(str(pdf)) as dokument:
        fett = {s.text for s in geometrie._spans(dokument.pages[0]) if s.fett}
    assert "vus@blitzsicht.com" in fett, "die Adresse steht nicht im (fetten) Betreff"
    bericht, pruefung = _bericht(pdf, form)
    assert pruefung.ist == "Seite 1: „ser- ⏎ vus@blitzsicht.com“"
    assert {p.name for p in bericht.pruefungen if not p.bestanden} == {PRUEFUNG}


# Emitter: Escaping in der Box und was sonst als Adresse gilt ──────────────

def test_die_box_schuetzt_anfuehrungszeichen_backslash_und_raute(tmp_path):
    """`a"b\\c#x` im Pfad: In der Zeichenkette gilt nur `"` und `\\`, `#` ist dort harmlos."""
    import typst

    url = 'https://blitzsicht.com/a"b\\c#x'
    gesetzt = emit.as_text(f"Siehe {url} dort", typografie_anwenden=False)
    assert gesetzt == (
        '#text("Siehe ")#box(text(hyphenate: false, "https://blitzsicht.com/a\\"b\\\\c#x"))'
        '#text(" dort")')
    quelle = tmp_path / "probe.typ"
    quelle.write_text("#set page(width: 150mm, height: 30mm)\n" + gesetzt + "\n", encoding="utf-8")
    typst.compile(str(quelle), output=str(tmp_path / "probe.pdf"))
    with pdfplumber.open(str(tmp_path / "probe.pdf")) as dokument:
        assert (dokument.pages[0].extract_text() or "").split() == ["Siehe", url, "dort"]


@pytest.mark.parametrize("wort, box", [
    ("datei.pdf", True),           # Dateiname: liest sich wie eine Domain
    ("bericht_2026.docx", True),
    ("index.html", True),
    ("3.5mm", False),              # nach dem Punkt eine Ziffer: keine Endung
    ("Datei.PDF", False),          # Endung groß: siehe `_DOMAIN`
])
def test_was_sonst_als_adresse_gilt(wort, box):
    """Kein Fehler, sondern festgehalten: Ein Dateiname bekommt eine Box.

    Er wird dann nicht getrennt — für einen Dateinamen ebenso richtig wie für
    eine Adresse.
    """
    assert ("#box(" in emit.as_text(f"Siehe {wort} dort")) is box


# Grenze je Ort: Zelle 0, Urkunde 40 ────────────────────────────────────────

def test_in_der_zelle_meldet_verify_den_umbruch_nach_schraegstrich(tmp_path):
    """Eine kurze URL bricht in der Zelle ohne Box nach „/“.

    Die Zelle erkennt `verify` an ihrem Rahmen und misst sie mit der Grenze 0.
    """
    pdf, form = cli.rendere(FIXTURES / "tabelle-url.md", tmp_path / "tabelle-url.pdf")
    bericht, pruefung = _bericht(pdf, form)
    assert pruefung.ist == "Seite 1: „https://blitzsicht.com/ ⏎ datenschutz“"
    assert {p.name for p in bericht.pruefungen if not p.bestanden} == {PRUEFUNG}


def test_im_blocksatz_meldet_verify_den_umbruch_einer_url_ueber_40_zeichen(tmp_path):
    pdf, _ = cli.rendere(FIXTURES / "urkunde-blocksatz-url.md", tmp_path / "url.pdf")
    url = "https://blitzsicht.com/leistungen/handwerksbetriebe"
    assert netzadressen.UNTEILBAR_BIS_BLOCKSATZ < len(url) <= netzadressen.UNTEILBAR_BIS
    bericht, pruefung = _bericht(pdf, "")
    assert pruefung.ist == "Seite 1: „https://blitzsicht.com/leistungen/ ⏎ handwerksbetriebe“"
    assert {p.name for p in bericht.pruefungen if not p.bestanden} == {PRUEFUNG}


# Spalten ohne Rahmen: Anschrift neben Informationsblock ───────────────────

class _Seite:
    """Eine Seite aus Wörtern in mm, so wie `_spans` sie von pdfplumber liest."""

    def __init__(self, zeilen: list[list[tuple[float, str]]]):
        pt = geometrie.PT_PRO_MM
        self.woerter = [
            {"text": text, "x0": x * pt, "x1": (x + 2.0 * len(text)) * pt,
             "top": (50 + 4.2 * nummer) * pt, "bottom": (54 + 4.2 * nummer) * pt,
             "fontname": "Probe", "size": 10.0}
            for nummer, zeile in enumerate(zeilen) for x, text in zeile]

    def extract_words(self, **_):
        return self.woerter

    def find_tables(self):
        return []


#: Anschrift links ab 25 mm, Informationsblock rechts ab 125 mm. Ganze Höhen
#: gepaart, endet Zeile 1 auf „Leistungsbeschrei-“ (rechts) und beginnt Zeile 2
#: mit „servus@blitzsicht.com“ (links).
ANSCHRIFT_UND_INFOBLOCK = [
    [(25, "Muster"), (39, "GmbH"), (125, "Ihre"), (135, "Leistungsbeschrei-")],
    [(25, "servus@blitzsicht.com"), (125, "bungen")],
]


def test_anschrift_und_informationsblock_werden_nicht_gepaart():
    fluesse = geometrie._textfluesse(_Seite(ANSCHRIFT_UND_INFOBLOCK), netzadressen.UNTEILBAR_BIS)
    assert [z for z, _ in fluesse] == [
        ["Muster GmbH", "servus@blitzsicht.com"], ["Ihre Leistungsbeschrei-", "bungen"]]
    assert [t for z, grenze in fluesse for t in netzadressen.getrennt(z, grenze)] == []


def test_ganze_hoehen_gepaart_waere_es_ein_befund():
    """Gegenprobe: Ohne Zerlegung in Spalten schlägt die Probe an."""
    zeilen = [" ".join(text for _, text in zeile) for zeile in ANSCHRIFT_UND_INFOBLOCK]
    assert [str(t) for t in netzadressen.getrennt(zeilen)] == [
        "„Leistungsbeschrei- ⏎ servus@blitzsicht.com“"]
