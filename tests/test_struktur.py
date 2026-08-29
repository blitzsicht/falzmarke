"""Was im PDF steht, muss auch als das ausgezeichnet sein, was es ist (#138).

Teilvorgang 4 von #26 fragt nicht mehr, ob ein Element gesetzt wird — das prüfen
die Teile davor. Er fragt, ob es im **Strukturbaum** des PDF ankommt. Eine
Überschrift, die dort ein gewöhnlicher Absatz ist, ist für einen Screenreader
keine Überschrift; ein Zitat, das nur eingerückt dasteht, ist kein Zitat.

Der Unterschied ist unsichtbar. Genau deshalb braucht er eine Messung: Am Bild
sieht man ihn nie, und jede Sichtprüfung geht daran vorbei.

Gemessen wird mit pypdf am `/StructTreeRoot` — dort steht, was das PDF über sich
selbst behauptet. Der Gegenbeweis dazu liefert veraPDF im CI: Es prüft die
Behauptung gegen PDF/UA-1, und das ist die Instanz, die nicht dem Haus gehört.

## Was hier gefunden wurde

Beim ersten Lauf am 29.08.2026 fehlten zwei von vierzehn Auszeichnungen:

* **`/BlockQuote`** — `zitat()` setzte einen `block`, und ein Block hat im PDF
  keine Bedeutung. Behoben mit `#quote(block: true)`; die Gestaltung liegt jetzt
  in einer show-Regel und der Tag überlebt sie.
* **`/TH`** — die Kopfzeile einer Tabelle war *fett gesetzt* und sonst nichts.
  Fett ist eine Aussage über das Aussehen. Behoben mit `table.header()`.

Beides fiel erst hier auf, weil bis dahin niemand in den Strukturbaum gesehen
hat: `verify` misst Ränder und Abstände, veraPDF lief nur gegen PDF/A-2b, und
A-2b verlangt keine Tags.
"""

from __future__ import annotations

import pytest

import pypdf

from conftest import REPO

#: Ein Brief, der jedes Element aus Dialekt 1.1 genau einmal enthält.
#:
#: Bewusst hier und nicht in `examples/`: Dort steht jeder Brief für einen
#: Anlass, den jemand wirklich schreibt. Dieser steht für die Elemente selbst —
#: er soll nichts erzählen, sondern alles auslösen.
ALLES = """---
profil: example
dialekt: "1.1"
empfaenger: [Muster GmbH, Musterstraße 1, 12345 Musterstadt]
datum: 2026-08-29
betreff: Jedes Element genau einmal
anrede: Sehr geehrte Damen und Herren,
---
# Erste Ebene

Ein Absatz mit **fett**, *kursiv* und `Code im Satz`.

## Zweite Ebene

* Erster Punkt
* Zweiter Punkt
  * Untereintrag eins
  * Untereintrag zwei

1. Nummeriert eins
2. Nummeriert zwei

### Dritte Ebene

> Ein Blockzitat mit einem Satz.
>
> * Erster Punkt im Zitat
> * Zweiter Punkt im Zitat

#### Vierte Ebene

```
Ein wortgetreuer Auszug
```

| Spalte A | Spalte B |
|---|---|
| Wert 1 | Wert 2 |
"""

#: Was der Strukturbaum tragen muss — je Element aus Dialekt 1.1 einer.
#:
#: `/Lbl` und `/LBody` stehen nicht dabei: Sie sind Innenteile einer Liste, und
#: `/L` mit `/LI` sagt bereits, dass eine Liste da ist. Was hier steht, ist die
#: Menge, deren Fehlen jemand merken würde.
PFLICHT = (
    "/H1", "/H2", "/H3", "/H4",      # vier Überschriftebenen
    "/L", "/LI",                     # Aufzählung
    "/BlockQuote",                   # Zitat
    "/Code",                         # wortgetreuer Auszug
    "/Table", "/TR", "/TH", "/TD",   # Tabelle samt Kopfzeile
    "/Strong", "/Em",                # Hervorhebungen
)


def strukturtypen(pdf) -> set[str]:
    """Alle `/S`-Werte im Strukturbaum eines PDF.

    Die Tiefenschranke ist eine Schleifensicherung, kein Messwert: Ein
    Strukturbaum ist ein gerichteter Graph, und ein fehlerhaftes PDF kann darin
    einen Kreis haben. 20 liegt weit über allem, was hier entsteht (gemessen:
    die tiefste Verschachtelung im Probebrief braucht 9).
    """
    gefunden: set[str] = set()

    def geh(knoten, tiefe: int) -> None:
        if tiefe > 20:
            return
        try:
            objekt = knoten.get_object()
        except Exception:                                  # noqa: BLE001
            return
        if isinstance(objekt, list):
            for eintrag in objekt:
                geh(eintrag, tiefe)
            return
        if not hasattr(objekt, "get"):
            return
        art = objekt.get("/S")
        if art:
            gefunden.add(str(art))
        kinder = objekt.get("/K")
        if kinder is not None:
            geh(kinder, tiefe + 1)

    wurzel = pypdf.PdfReader(str(pdf)).trailer["/Root"]
    if "/StructTreeRoot" not in wurzel:
        return gefunden
    geh(wurzel["/StructTreeRoot"], 0)
    return gefunden


@pytest.fixture(scope="module")
def getaggt(tmp_path_factory):
    """Der Probebrief als PDF/UA-1 — die Fassung mit Strukturbaum."""
    from falzmarke import cli

    ordner = tmp_path_factory.mktemp("struktur")
    brief = ordner / "alles.md"
    brief.write_text(ALLES, encoding="utf-8")
    pdf, _ = cli.rendere(brief, ordner / "alles.pdf", pdfua=True,
                         profil_verzeichnis=REPO / "skill" / "falzmarke" / "typst" / "profiles")
    return pdf


# ── Der Baum ist überhaupt da ───────────────────────────────────────────────

def test_die_ua_fassung_hat_einen_strukturbaum(getaggt):
    wurzel = pypdf.PdfReader(str(getaggt)).trailer["/Root"]
    assert "/StructTreeRoot" in wurzel, "kein Strukturbaum — dann sagt das PDF gar nichts über sich"
    # `bool(...)`, nicht `is True`: pypdf gibt ein `BooleanObject` zurueck.
    # Es ist gleich `True`, aber nicht dasselbe Objekt — `is True` schlaegt fehl
    # und die Meldung lautet dann „assert True is True", was niemandem hilft.
    assert bool(wurzel["/MarkInfo"]["/Marked"]) is True
    assert str(wurzel["/Lang"]).startswith("de"), wurzel.get("/Lang")


def test_die_tags_stehen_auch_in_der_gewoehnlichen_fassung(tmp_path):
    """Gemessen, nicht angenommen: `--pdfua` schaltet die Tags NICHT ein.

    Diese Prüfung stand hier zuerst mit der umgekehrten Erwartung — die Tags
    kämen von der Option, und ohne sie sei der Baum leer. Sie wurde beim ersten
    Lauf rot, und das war der Befund: Typst taggt in beiden Fassungen. Was
    `--pdfua` ändert, ist allein die **Deklaration** im XMP; die Struktur, auf
    die sie sich beruft, ist ohnehin da.

    Das ist die günstigere Lage, aber sie gehört gemessen und nicht gehofft.
    Fiele sie weg, wäre jeder ohne `--pdfua` erzeugte Brief still nicht mehr
    vorlesbar, und die vierzehn Prüfungen darüber sähen es nicht: Sie messen
    die UA-Fassung.
    """
    from falzmarke import cli

    brief = tmp_path / "alles.md"
    brief.write_text(ALLES, encoding="utf-8")
    pdf, _ = cli.rendere(brief, tmp_path / "ohne.pdf", pdfua=False,
                         profil_verzeichnis=REPO / "skill" / "falzmarke" / "typst" / "profiles")
    vorhanden = strukturtypen(pdf)
    fehlend = [a for a in PFLICHT if a not in vorhanden]
    assert not fehlend, f"ohne --pdfua fehlen: {fehlend}"

    # Und der Unterschied, den die Option wirklich macht — er steht im XMP:
    xmp = pdf.read_bytes()
    assert b"pdfuaid:part" not in xmp, "ohne --pdfua darf sich das PDF nicht als UA ausgeben"


# ── Und er trägt jedes Element ──────────────────────────────────────────────

@pytest.mark.parametrize("art", PFLICHT)
def test_jedes_element_ist_ausgezeichnet(getaggt, art):
    vorhanden = strukturtypen(getaggt)
    assert art in vorhanden, (
        f"{art} fehlt im Strukturbaum. Das Element wird gesetzt, aber das PDF sagt "
        f"nicht, was es ist.\nGefunden: {sorted(vorhanden)}")


def test_die_pruefung_wuerde_ein_fehlendes_element_bemerken(getaggt):
    """Gegenprobe: eine Auszeichnung, die es nicht gibt, muss auffallen.

    Ohne diese Zeile belegt die Liste oben nur, dass `strukturtypen` etwas
    zurückgibt — nicht, dass sie zwischen da und nicht da unterscheidet.
    """
    assert "/Figure" not in strukturtypen(getaggt), \
        "der Probebrief hat kein Bild — findet die Messung eines, misst sie nicht den Baum"


def test_die_ueberschriftebenen_stehen_in_der_richtigen_reihenfolge(getaggt):
    """Vier Ebenen, und keine übersprungen.

    PDF/UA-1 verlangt eine lückenlose Gliederung: Auf `/H1` darf `/H2` folgen,
    aber nicht `/H3`. Der Dialekt lässt vier Ebenen zu — dass sie im Baum auch
    als vier aufeinanderfolgende ankommen, ist die Aussage hier.
    """
    ebenen = sorted(a for a in strukturtypen(getaggt) if a.startswith("/H") and a[2:].isdigit())
    assert ebenen == ["/H1", "/H2", "/H3", "/H4"], ebenen


# ── Was der Bestand behält ──────────────────────────────────────────────────

def test_der_schriftsatz_traegt_seine_gliederung(tmp_path):
    """Nicht der Probebrief, sondern ein echtes Beispiel aus `examples/`.

    Der Probebrief oben ist für die Messung gebaut. Dieser hier ist es nicht —
    er steht für einen Anlass, den jemand wirklich schreibt, und muss dieselbe
    Auszeichnung tragen.
    """
    from falzmarke import cli

    pdf, _ = cli.rendere(REPO / "examples" / "brief-schriftsatz.md",
                         tmp_path / "schriftsatz.pdf", pdfua=True)
    vorhanden = strukturtypen(pdf)
    for art in ("/H1", "/H2", "/H3", "/H4", "/L", "/LI", "/BlockQuote", "/Code"):
        assert art in vorhanden, f"{art} fehlt in brief-schriftsatz.pdf"


# ── Verwaiste Überschrift am Seitenende (#138, AK 5) ────────────────────────
#
# Der Vorgang verlangt eine Entscheidung: verhindert oder ausdrücklich
# zugelassen, mit Begründung. Sie lautet **verhindert** — und das Werkzeug tut
# dafür nichts, weil Typst es schon tut: `heading` steht per Vorgabe in einem
# Block mit `sticky: true`, der nicht ohne den folgenden Absatz umbricht.
#
# Das ist eine Zusage einer fremden Fassung, keine eigene. Deshalb steht sie
# hier als Messung: Zieht Typst sie zurück, wird dieser Test rot statt dass es
# jemand ein halbes Jahr später an einem Ausdruck sieht.

WAISENPROBE = """#set page(height: 60mm, width: 100mm, margin: 5mm)
#set text(size: 9pt)
{regeln}
#lorem(90)

= Überschrift

Text danach.
"""


def _seiten_von(quelle: str, tmp_path) -> tuple[list[int], list[int]]:
    """Auf welchen Seiten stehen Überschrift und Folgeabsatz?"""
    import pdfplumber
    import typst

    typ = tmp_path / "probe.typ"
    typ.write_text(quelle, encoding="utf-8")
    pdf = tmp_path / "probe.pdf"
    typst.compile(str(typ), output=str(pdf))
    with pdfplumber.open(str(pdf)) as dokument:
        seiten = [(s.extract_text() or "") for s in dokument.pages]
    return ([i + 1 for i, s in enumerate(seiten) if "Überschrift" in s],
            [i + 1 for i, s in enumerate(seiten) if "Text danach" in s])


def test_eine_ueberschrift_bleibt_bei_ihrem_absatz(tmp_path):
    ueberschrift, text = _seiten_von(WAISENPROBE.format(regeln=""), tmp_path)
    assert ueberschrift == text, (
        f"die Überschrift steht auf Seite {ueberschrift}, ihr Absatz auf {text} — "
        "sie ist verwaist")


def test_und_ohne_den_zusammenhalt_verwaist_sie(tmp_path):
    """Gegenprobe. Ohne sie belegt der Test darüber nur, dass der Text auf eine
    Seite passt — und nicht, dass irgendetwas ihn zusammenhält."""
    ueberschrift, text = _seiten_von(
        WAISENPROBE.format(regeln="#show heading: set block(sticky: false)"), tmp_path)
    assert ueberschrift != text, (
        "auch ohne `sticky` bleiben beide zusammen — dann misst der Test darüber "
        "die Seitenaufteilung und nicht den Zusammenhalt")


# ── Ein Auszug über den Seitenwechsel (#168) ────────────────────────────────
#
# #138 nennt ihn als Fall und lässt ihn offen; #168 hat ihn nachgereicht. Der
# Punkt ist nicht, DASS ein Brief zwei Seiten hat — das können mehrere
# Beispiele. Der Punkt ist, dass ein wortgetreuer Auszug den Wechsel überlebt,
# **und zwar als ein Element**: Zerfiele er in zwei, wäre er für ein
# Bildschirmleseprogramm auf Seite 2 kein Auszug mehr, sondern gewöhnlicher Text
# in einer anderen Schrift.

PROTOKOLL = REPO / "examples" / "brief-protokollauszug.md"


def _code_element(pdf):
    """Das eine `/Code`-Element im Strukturbaum — oder None."""
    def suche(knoten, tiefe=0):
        try:
            objekt = knoten.get_object()
        except Exception:                                  # noqa: BLE001
            return None
        if isinstance(objekt, list):
            for eintrag in objekt:
                treffer = suche(eintrag, tiefe)
                if treffer is not None:
                    return treffer
            return None
        if not hasattr(objekt, "get"):
            return None
        if str(objekt.get("/S", "")) == "/Code":
            return objekt
        if objekt.get("/K") is not None and tiefe < 18:
            return suche(objekt["/K"], tiefe + 1)
        return None

    return suche(pypdf.PdfReader(str(pdf)).trailer["/Root"]["/StructTreeRoot"])


def _zeilen_je_seite(pdf) -> dict[int, int]:
    """Wie viele Zeilen des Auszugs auf welcher Seite stehen.

    Über die Objektnummer der Seite, nicht über `id()`: `get_object()` kann
    jedes Mal ein neues Python-Objekt liefern, und der Vergleich ginge dann
    immer daneben — beim ersten Anlauf hier gemessen, er ergab „?" für jede
    Zeile.
    """
    leser = pypdf.PdfReader(str(pdf))
    nummern = {s.indirect_reference.idnum: i + 1 for i, s in enumerate(leser.pages)}
    code = _code_element(pdf)
    assert code is not None, "kein /Code im Strukturbaum"
    gezaehlt: dict[int, int] = {}
    for kind in code["/K"]:
        objekt = kind.get_object()
        try:
            seite = nummern.get(objekt.raw_get("/Pg").idnum)
        except Exception:                                  # noqa: BLE001
            continue
        if seite:
            gezaehlt[seite] = gezaehlt.get(seite, 0) + 1
    return gezaehlt


@pytest.fixture(scope="module")
def protokoll(tmp_path_factory):
    from falzmarke import cli

    ordner = tmp_path_factory.mktemp("protokoll")
    pdf, _ = cli.rendere(PROTOKOLL, ordner / "protokoll.pdf", pdfua=True)
    return pdf


def test_das_beispiel_gibt_es():
    assert PROTOKOLL.is_file(), "examples/brief-protokollauszug.md fehlt"


def test_der_auszug_laeuft_wirklich_ueber_den_seitenwechsel(protokoll):
    """Die Gegenprobe zum Test darunter — und sie steht bewusst zuerst.

    Ein zweiseitiger Brief mit einem Auszug irgendwo darin würde die Prüfung
    unten ebenfalls bestehen, ohne den Fall auszulösen, für den es sie gibt.
    """
    verteilung = _zeilen_je_seite(protokoll)
    assert len(verteilung) >= 2, (
        f"der Auszug steht ganz auf einer Seite: {verteilung} — "
        "das Beispiel löst den Fall nicht mehr aus")
    assert min(verteilung.values()) >= 3, verteilung


def test_und_bleibt_dabei_ein_einziges_element(protokoll):
    """Zerfiele er in zwei, wäre er auf Seite 2 kein Auszug mehr."""
    leser = pypdf.PdfReader(str(protokoll))

    def zaehle(knoten, tiefe=0):
        try:
            objekt = knoten.get_object()
        except Exception:                                  # noqa: BLE001
            return 0
        if isinstance(objekt, list):
            return sum(zaehle(e, tiefe) for e in objekt)
        if not hasattr(objekt, "get"):
            return 0
        eigen = 1 if str(objekt.get("/S", "")) == "/Code" else 0
        if objekt.get("/K") is not None and tiefe < 18:
            return eigen + zaehle(objekt["/K"], tiefe + 1)
        return eigen

    assert zaehle(leser.trailer["/Root"]["/StructTreeRoot"]) == 1


def test_und_der_brief_haelt_alle_masse(tmp_path):
    """Die Abnahme aus #168: Er besteht die Maßprüfung vollständig.

    Ein Auszug wird nicht umbrochen — er läuft ab 68 Zeichen je Zeile aus dem
    Satzspiegel. Die Zeilen dieses Protokolls liegen darunter, und das ist kein
    Zufall, sondern die Bedingung dafür, dass er nach `examples/` gehört.
    """
    from falzmarke import cli, geometrie

    pdf, form = cli.rendere(PROTOKOLL, tmp_path / "p.pdf")
    bericht = geometrie.pruefe(pdf, form)
    gescheitert = [p.name for p in bericht.pruefungen if not p.bestanden]
    assert not gescheitert, gescheitert
