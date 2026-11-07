"""Beispiele, Goldens und Gegenproben für die Rechnungsfassung (#119).

Brief und E-Mail haben beide ihre Beispielsuite mit byteweisem Golden
(`tests/test_email_beispiele.py`). Die Rechnung bekommt hier dieselbe Zusage:
jedes Beispiel läuft in der CI, wird gegen ein eingefrorenes Golden gehalten,
und jede neue Prüfung trägt eine Gegenprobe, die belegt, dass sie anschlägt.

## Was schon da ist — nicht hier verdoppelt

Ein Teil der in #119 verlangten Gegenproben existiert bereits aus #116/#118 und
ist bewusst nicht noch einmal geschrieben:

- **„Ein Betrag nur im PDF“**: `tests/test_rechnung_treue.py::test_ein_betrag_nur_im_pdf_faellt_auf`.
- **„Eine fehlende Pflichtangabe“**: `scripts/erechnung_ohne_referenz.py` entfernt
  die Käuferreferenz (BT-10) aus einer Kopie der XRechnung; `erechnung_pruefen.py`
  und `erechnung_kosit.py` verlangen in der CI, dass Mustang bzw. der
  KoSIT-Validator genau an `BR-DE-15` scheitern (siehe `.github/workflows/ci.yml`,
  Job „E-Rechnung (Mustang, fremdes Werkzeug)“ und „E-Rechnung (KoSIT-Validator)“).
- **„Eine Rechnung mit Leitweg-ID für einen öffentlichen Auftraggeber“**:
  `examples/xrechnung.md`.

## Was hier neu ist

- Zwei Beispiele fehlen noch: eine Rechnung mit mehreren Steuersätzen und eine
  Kleinbetragsrechnung (§ 33 UStDV, Gesamtbetrag höchstens 250 €).
- Es gibt noch kein byteweises Golden für PDF oder XML einer Rechnung.
- **„Ein Steuersatz nur in der XML“** und **„ein unzulässiger Codelistenwert“**
  waren bis #119 echte, unsabotierte Lücken — kein Monkeypatch nötig, um sie
  zu zeigen:

  - Die Positionstabelle im PDF zeigt nie den Steuersatz einer einzelnen
    Position (`cli.py:_positionstabelle`, Spalten Position/Menge/Einzelpreis/
    Betrag) — nur die Sammelzeilen aus `summen.steuer` als „Umsatzsteuer NN %“.
    Trägt eine Position einen Satz, für den `summen.steuer` keine Zeile hat,
    verlässt dieser Satz die Quelle nur in Richtung XML. Vor #119 meldete
    `falzmarke.linte()` für eine Rechnung mit Positionen zu 19 % und 7 %, aber
    `summen.steuer` nur für 19 %, nichts, obwohl die eingebettete XML
    `RateApplicablePercent` 7.00 trägt.
  - `land:` — sowohl `rechnung.land` im Profil als auch
    `empfaenger_anschrift.land` — wurde nur auf Vorhandensein geprüft
    (`lint.py`, `EMPFAENGER_ANSCHRIFT_PFLICHT`), nie auf einen gültigen
    ISO-3166-1-Alpha-2-Code. Vor #119 blieb `land: Deutschland`
    unbeanstandet und landet unverändert als `<ram:CountryID>Deutschland</...>`
    in der XML — ein Empfänger-Validator lehnt das ab, falzmarke sagt nichts.

## Der PDF-Golden-Vorbehalt (Abnahme 1, #119)

„Beim PDF gilt dieselbe Vorsicht wie bei der Mahnungs-Mail mit Anlage: Ein
zweiter Renderlauf derselben Quelle liefert andere Bytes.“ Das trifft zu:
Gemessen am 13.09.2026 tragen zwei Läufe über `examples/rechnung.md` im Abstand
von zwei Sekunden verschiedene `/CreationDate`. Eingefroren wird deshalb wie bei
der `.eml` über `SOURCE_DATE_EPOCH`; alles andere am PDF entsteht bei jedem Lauf
neu und muss trotzdem bytegleich sein. Ohne die Variable bleibt die Rechnerzeit
im PDF — die Erstellungszeit einer Datei ist nicht das Briefdatum.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pypdf
import pytest

from falzmarke import cli as falzmarke
from conftest import (GOLDEN_VERSION, REPO, PROFILE, RECHNUNG_BEISPIELE,
                      TypstMaskeGreiftNicht, ohne_typografiehinweise, ohne_typst_kennung)

GOLDEN = REPO / "tests" / "golden" / "rechnung"

#: Derselbe Zeitpunkt wie in `scripts/golden_rechnung.py`.
EPOCH = "1788134400"

IDS = dict(ids=lambda p: p.stem)


@pytest.fixture(autouse=True)
def _feste_zeit(monkeypatch):
    monkeypatch.setenv("SOURCE_DATE_EPOCH", EPOCH)
    monkeypatch.setattr(falzmarke, "VERSION", GOLDEN_VERSION)


def _setze(beispiel: Path, tmp_path: Path) -> Path:
    pdf, _ = falzmarke.rendere(beispiel, tmp_path / f"{beispiel.stem}.pdf",
                               profil_verzeichnis=PROFILE)
    return pdf


def _xml_bytes(pdf: Path) -> bytes:
    wurzel = pypdf.PdfReader(str(pdf)).trailer["/Root"]
    datei = wurzel["/AF"][0].get_object()["/EF"]["/F"]
    return bytes(datei.get_object().get_data())


def _kopie(beispiel: Path, tmp_path: Path, alt: str, neu: str) -> Path:
    """Wie in `test_email_beispiele.py`: eine Kopie ändern, das Original bleibt unberührt."""
    quelle = beispiel.read_text(encoding="utf-8")
    assert alt in quelle, f"die Sabotage findet „{alt}“ nicht — sie kann nicht greifen"
    pfad = tmp_path / beispiel.name
    pfad.write_text(quelle.replace(alt, neu, 1), encoding="utf-8")
    assert pfad.read_text(encoding="utf-8") != quelle, "Sabotage wirkungslos"
    return pfad


# ── Es gibt überhaupt etwas zu messen ───────────────────────────────────────

def test_es_gibt_rechnungsbeispiele():
    assert RECHNUNG_BEISPIELE, "keine Beispiele mit `typ: rechnung` unter examples/"


def test_es_gibt_mindestens_vier_rechnungsbeispiele():
    """Drei Fälle verlangt die Abnahme namentlich (mehrere Steuersätze,
    Leitweg-ID, Kleinbetrag) — plus die ursprüngliche EN-16931-Rechnung aus
    #116 macht vier. Am 13.09.2026 gibt es zwei: `rechnung.md`, `xrechnung.md`."""
    assert len(RECHNUNG_BEISPIELE) >= 4, [p.name for p in RECHNUNG_BEISPIELE]


def _kopf(beispiel: Path) -> dict:
    import yaml

    frontmatter = beispiel.read_text(encoding="utf-8").split("---", 2)[1]
    return yaml.safe_load(frontmatter)


def test_ein_beispiel_hat_mehrere_positionen_und_steuersaetze():
    """Die Abnahme verlangt ausdrücklich „mehrere Positionen und verschiedene
    Steuersätze“ — nicht nur mehrere Positionen. `rechnung.md` und
    `xrechnung.md` haben zwei Positionen, beide zu 19 %."""
    treffer = [
        b for b in RECHNUNG_BEISPIELE
        if len({p.get("steuersatz") for p in (_kopf(b).get("positionen") or [])}) >= 2
    ]
    assert treffer, "kein Rechnungsbeispiel hat Positionen mit verschiedenen Steuersätzen"


def test_ein_beispiel_ist_eine_kleinbetragsrechnung():
    """§ 33 UStDV: Gesamtbetrag höchstens 250 € (`docs/recht.md`)."""
    treffer = [
        b for b in RECHNUNG_BEISPIELE
        if (_kopf(b).get("summen") or {}).get("brutto", 10**9) <= 250
    ]
    assert treffer, "kein Rechnungsbeispiel bleibt unter der Kleinbetragsgrenze von 250 €"


# ── Das byteweise Golden je Ergebnis (Abnahme 1) ────────────────────────────

def test_zu_jedem_beispiel_ein_pdf_golden():
    fehlend = [b.stem for b in RECHNUNG_BEISPIELE if not (GOLDEN / f"{b.stem}.pdf").exists()]
    assert not fehlend, f"ohne PDF-Golden: {fehlend}"


def test_zu_jedem_beispiel_ein_xml_golden():
    fehlend = [b.stem for b in RECHNUNG_BEISPIELE if not (GOLDEN / f"{b.stem}.xml").exists()]
    assert not fehlend, f"ohne XML-Golden: {fehlend}"


@pytest.mark.parametrize("beispiel", RECHNUNG_BEISPIELE, **IDS)
def test_das_pdf_entspricht_seinem_golden(beispiel, tmp_path):
    """Byteweise bis auf typsts eigene Kennung (`conftest.ohne_typst_kennung`, #533)."""
    pdf = _setze(beispiel, tmp_path)
    soll = GOLDEN / f"{beispiel.stem}.pdf"
    assert ohne_typst_kennung(pdf.read_bytes()) == ohne_typst_kennung(soll.read_bytes()), (
        f"{beispiel.name} rendert andere Bytes als sein Golden — bei einer gewollten "
        "Änderung das Golden neu erzeugen und den Diff mitlesen.")


def _andere_typst_fassung(pdf: bytes) -> bytes:
    """Dasselbe PDF, als hätte es eine andere typst-Fassung gleicher Namenslänge
    geschrieben: letzte Ziffer der Fassung und InstanceID an allen Stellen gedreht."""
    fassung = re.search(rb"<xmp:CreatorTool>Typst ([^<]+)<", pdf)[1]
    instanz = re.search(rb"<xmpMM:InstanceID>([^<]+)<", pdf)[1]
    andere = fassung[:-1] + (b"8" if fassung[-1:] == b"9" else b"9")
    gedreht = instanz[1:] + instanz[:1]
    assert gedreht != instanz, "die InstanceID lässt sich so nicht drehen"
    for alt, neu in ((b"Typst " + fassung, b"Typst " + andere),
                     (fassung.replace(b".", rb"\056"), andere.replace(b".", rb"\056")),
                     (instanz, gedreht), (instanz.hex().encode(), gedreht.hex().encode())):
        assert alt in pdf, f"„{alt!r}“ fehlt im Golden — die Nachbildung greift nicht"
        pdf = pdf.replace(alt, neu)
    return pdf


@pytest.mark.parametrize("beispiel", RECHNUNG_BEISPIELE, **IDS)
def test_eine_andere_typst_fassung_kippt_kein_golden(beispiel):
    """typst 0.15.2 kippte alle sechs Goldens über seine Kennung allein (#533). Eine
    Fassung, die nur die Kennung ändert, muss der Vergleich oben durchlassen."""
    golden = (GOLDEN / f"{beispiel.stem}.pdf").read_bytes()
    andere = _andere_typst_fassung(golden)
    assert andere != golden, "die Nachbildung ändert nichts — so belegt der Test nichts"
    assert ohne_typst_kennung(andere) == ohne_typst_kennung(golden), (
        f"{beispiel.stem}: die Maske deckt die typst-Kennung nicht ganz ab")


def test_ein_pdf_ohne_typst_kennung_bricht_den_vergleich_ab():
    """Trifft die Maske nichts mehr, etwa weil typst sein XMP umbaut, soll sie laut
    scheitern statt still den rohen Vergleich zurückzubringen. Die eine Ausnahme ist
    das Neu-Erzeugen in `scripts/golden_rechnung.py`: Es fängt den Fehler und vergleicht
    roh, aber nicht still, sondern mit einer Zeile je Datei und Exit 2 (Review #575)."""
    golden = (GOLDEN / f"{RECHNUNG_BEISPIELE[0].stem}.pdf").read_bytes()
    ohne = golden.replace(b"<stEvt:softwareAgent>Typst ", b"<stEvt:softwareAgent>Tipst ")
    assert ohne != golden
    with pytest.raises(TypstMaskeGreiftNicht, match="typst-Kennung in xmp:CreatorTool und "
                                                    "stEvt:softwareAgent: 1-mal statt 2-mal"):
        ohne_typst_kennung(ohne)


def test_ein_pdf_ganz_ohne_xmp_meldet_die_fehlende_kennung():
    """Fehlt die Kennung ganz, kommt die Meldung, kein `TypeError` aus `fassung[1]`."""
    with pytest.raises(TypstMaskeGreiftNicht, match="keine typst-Kennung im XMP"):
        ohne_typst_kennung(b"%PDF-1.7\n%%EOF\n")


#: Die Datei, aus der die Probe unter `python -O` die Maske lädt. Die Gegenprobe
#: setzt hier eine sabotierte Kopie ein.
KONFTEST = REPO / "tests" / "conftest.py"

_UNTER_O = """\
import importlib.util, sys
if __debug__:
    sys.exit("läuft nicht unter -O")
spez = importlib.util.spec_from_file_location("conftest_unter_o", sys.argv[1])
modul = importlib.util.module_from_spec(spez)
spez.loader.exec_module(modul)
try:
    modul.ohne_typst_kennung(open(sys.argv[2], "rb").read())
except Exception as fehler:
    print(type(fehler).__name__, fehler)
    sys.exit(3)
"""


def test_die_maske_prueft_auch_unter_python_O(tmp_path):
    """Unter `python -O` fällt jedes `assert` weg (Review #568). Die Prüfungen der
    Maske dürfen deshalb keine sein, sonst verdeckte sie dort still eine Änderung."""
    golden = (GOLDEN / f"{RECHNUNG_BEISPIELE[0].stem}.pdf").read_bytes()
    pdf = tmp_path / "ohne.pdf"
    pdf.write_bytes(golden.replace(b"<stEvt:softwareAgent>Typst ",
                                   b"<stEvt:softwareAgent>Tipst "))
    lauf = subprocess.run([sys.executable, "-O", "-c", _UNTER_O, str(KONFTEST), str(pdf)],
                          capture_output=True, text=True, encoding="utf-8", timeout=120,
                          check=False, env={**os.environ, "PYTHONUTF8": "1",
                                            # Sonst landet `conftest.*.opt-1.pyc` im Repo.
                                            "PYTHONDONTWRITEBYTECODE": "1"})
    ausgabe = lauf.stdout + lauf.stderr
    assert lauf.returncode in (0, 3), f"die Probe lief nicht: {ausgabe!r}"
    assert lauf.returncode == 3 and "TypstMaskeGreiftNicht" in lauf.stdout \
        and "1-mal statt 2-mal" in lauf.stdout, (
            f"unter python -O blieb die Maske still: {ausgabe!r}")


@pytest.mark.parametrize("beispiel", RECHNUNG_BEISPIELE, **IDS)
def test_die_eingebettete_xml_entspricht_ihrem_golden(beispiel, tmp_path):
    pdf = _setze(beispiel, tmp_path)
    soll = GOLDEN / f"{beispiel.stem}.xml"
    assert _xml_bytes(pdf) == soll.read_bytes(), (
        f"die aus {beispiel.name} eingebettete XML weicht von ihrem Golden ab.")


def test_der_pdf_vergleich_kann_rot_werden(tmp_path):
    """Gegenprobe: eine geänderte Quelle darf nicht zum alten Golden passen — auch
    nicht durch die Maske, mit der der Vergleich oben arbeitet."""
    beispiel = RECHNUNG_BEISPIELE[0]
    sabotiert = _kopie(beispiel, tmp_path, "betreff: ", "betreff: Nachtrag — ")
    ist = _setze(sabotiert, tmp_path).read_bytes()
    soll = (GOLDEN / f"{beispiel.stem}.pdf").read_bytes()
    assert ohne_typst_kennung(ist) != ohne_typst_kennung(soll)


def test_zwei_laeufe_ueber_dasselbe_beispiel_sind_bytegleich(tmp_path):
    """Ohne Determinismus wäre der Golden-Vergleich oben ein Zufallsgenerator.
    Regressionswächter: Zieht außer der Zeit etwas Veränderliches ein, etwa eine
    UUID, fällt es hier auf, statt jedes PDF-Golden still altern zu lassen."""
    beispiel = RECHNUNG_BEISPIELE[0]
    erst = _setze(beispiel, tmp_path / "a").read_bytes()
    zweit = _setze(beispiel, tmp_path / "b").read_bytes()
    assert erst == zweit


def test_ohne_feste_zeit_traegt_das_pdf_die_rechnerzeit(tmp_path, monkeypatch):
    """Gegenprobe zum Test darüber: Er belegt nur etwas, wenn die Zeit wirklich
    das Veränderliche ist. Ohne `SOURCE_DATE_EPOCH` muss ein anderes
    `/CreationDate` als das festgenagelte im PDF stehen."""
    beispiel = RECHNUNG_BEISPIELE[0]
    fest = _setze(beispiel, tmp_path / "fest").read_bytes()
    monkeypatch.delenv("SOURCE_DATE_EPOCH")
    frei = _setze(beispiel, tmp_path / "frei").read_bytes()
    # Typst schreibt den Doppelpunkt nach `D` als Oktal-Escape `\072`.
    erstellt = re.compile(rb"/CreationDate\s*\(D(?::|\\072)(\d{8})")
    assert erstellt.search(fest)[1] == b"20260831", "das Epoch 1788134400 (31.08.2026) fehlt"
    assert erstellt.search(frei)[1] != b"20260831" and fest != frei


def _fassung(pdf: Path) -> tuple[str, str]:
    meta = pypdf.PdfReader(str(pdf)).metadata
    return meta["/Producer"], meta["/falzmarke_Version"]


@pytest.mark.parametrize("beispiel", RECHNUNG_BEISPIELE, **IDS)
def test_das_golden_traegt_die_feste_fassung(beispiel):
    """Bis 0.11.2 stand hier die Paketversion, und jedes Release erzeugte sechs
    Binär-Diffs ohne inhaltliche Änderung (#467). Wer die durchwinkt, winkt
    irgendwann auch einen echten durch."""
    from falzmarke import __version__

    assert GOLDEN_VERSION != __version__, "die feste Fassung darf keine echte sein"
    assert _fassung(GOLDEN / f"{beispiel.stem}.pdf") == (
        f"falzmarke {GOLDEN_VERSION}", GOLDEN_VERSION)


def test_ohne_feste_fassung_traegt_das_pdf_die_paketversion(tmp_path, monkeypatch):
    """Gegenprobe zur festen Fassung, wie oben zur festen Zeit: Außerhalb der
    Goldens schreibt falzmarke weiter die echte Version ins PDF, und genau
    dieser Unterschied ist es, den die Fixture wegnimmt."""
    from falzmarke import __version__

    beispiel = RECHNUNG_BEISPIELE[0]
    monkeypatch.setattr(falzmarke, "VERSION", falzmarke.VERSION_PAKET)
    pdf = _setze(beispiel, tmp_path)
    assert _fassung(pdf) == (f"falzmarke {__version__}", __version__)
    assert pdf.read_bytes() != (GOLDEN / f"{beispiel.stem}.pdf").read_bytes()


# ── „Ein Steuersatz nur in der XML“ (Abnahme 2 und 3) ───────────────────────
#
# Die Positionstabelle im PDF zeigt nie den Steuersatz einer einzelnen Position
# — nur `summen.steuer` als Sammelzeile „Umsatzsteuer NN %“. Ein Positions-Satz
# ohne passende Sammelzeile verließe die Quelle nur Richtung XML.

STEUERSATZ_OHNE_SUMMENZEILE = """---
typ: rechnung
profil: example
empfaenger:
  - Muster GmbH
  - Musterstraße 1
  - 12345 Musterstadt
empfaenger_anschrift:
  name: Muster GmbH
  strasse: Musterstraße 1
  plz: "12345"
  ort: Musterstadt
  land: DE
datum: 2026-09-11
betreff: Rechnung mit zwei Steuersätzen
rechnungsnummer: "2026-0099"
leistungsdatum: 2026-10-03
positionen:
  - bezeichnung: Beratung
    menge: 1
    einzelpreis: 100.00
    steuersatz: 19
    betrag: 100.00
  - bezeichnung: Buch
    menge: 1
    einzelpreis: 50.00
    steuersatz: 7
    betrag: 50.00
summen:
  netto: 150.00
  steuer:
    - satz: 19
      basis: 100.00
      betrag: 19.00
  brutto: 169.00
anrede: Sehr geehrte Damen und Herren,
---
Probetext.
"""


def test_ein_uebereinstimmender_steuersatz_ist_kein_befund():
    """Kontrollprobe: `examples/rechnung.md` trägt nur 19 % — Position und
    Summe stimmen überein. Ohne sie belegte die Gegenprobe unten nur, dass der
    Linter IRGENDETWAS meldet."""
    bericht = falzmarke.linte(REPO / "examples" / "rechnung.md", profil_verzeichnis=PROFILE)
    # Ohne die Hinweise des Typografie-Passes (#330): „am 3. Oktober“ trägt
    # einen — das Beispiel meint die Steuersätze, nicht die Schreibweise.
    befunde = ohne_typografiehinweise(bericht)
    assert not befunde, [b.als_zeile("rechnung.md") for b in befunde]


def test_ein_steuersatz_ohne_summenzeile_wird_gemeldet(tmp_path):
    """Der teure Fall aus #119: Ein Positions-Steuersatz, der in `summen.steuer`
    keine Entsprechung hat, blieb stumm — im PDF steht nur „Umsatzsteuer
    19 %“, in der XML zusätzlich `RateApplicablePercent` 7.00.
    """
    pfad = tmp_path / "gemischt.md"
    pfad.write_text(STEUERSATZ_OHNE_SUMMENZEILE, encoding="utf-8")
    bericht = falzmarke.linte(pfad, profil_verzeichnis=PROFILE)
    assert "rechnung.steuersatz" in {b.regel for b in bericht.befunde}, (
        "eine Position mit einem Steuersatz ohne passende `summen.steuer`-Zeile "
        "bleibt unbeanstandet — genau der stille Fall aus #119")


# ── „Ein unzulässiger Codelistenwert“ (Abnahme 2 und 3) ─────────────────────
#
# `land:` wurde bis #119 nur auf Vorhandensein geprüft, nie auf einen gültigen
# ISO-3166-1-Alpha-2-Code — weder im Profil (`rechnung.land`) noch am Empfänger
# (`empfaenger_anschrift.land`).

LAENDERCODE_UNGUELTIG = """---
typ: rechnung
profil: example
empfaenger:
  - Muster GmbH
  - Musterstraße 1
  - 12345 Musterstadt
empfaenger_anschrift:
  name: Muster GmbH
  strasse: Musterstraße 1
  plz: "12345"
  ort: Musterstadt
  land: Deutschland
datum: 2026-09-11
betreff: Rechnung mit unzulässigem Ländercode
rechnungsnummer: "2026-0098"
leistungsdatum: 2026-10-03
positionen:
  - bezeichnung: Beratung
    menge: 1
    einzelpreis: 100.00
    steuersatz: 19
    betrag: 100.00
summen:
  netto: 100.00
  steuer:
    - satz: 19
      basis: 100.00
      betrag: 19.00
  brutto: 119.00
anrede: Sehr geehrte Damen und Herren,
---
Probetext.
"""


def test_ein_gueltiger_laendercode_ist_kein_befund(tmp_path):
    """Kontrollprobe: `DE` ist ein gültiger ISO-3166-1-Alpha-2-Code."""
    pfad = tmp_path / "gueltig.md"
    pfad.write_text(LAENDERCODE_UNGUELTIG.replace("land: Deutschland", "land: DE"),
                     encoding="utf-8")
    bericht = falzmarke.linte(pfad, profil_verzeichnis=PROFILE)
    assert not bericht.befunde, [b.als_zeile("gueltig.md") for b in bericht.befunde]


def test_ein_unzulaessiger_laendercode_wird_gemeldet(tmp_path):
    """Vor #119 blieb `land: Deutschland` unbeanstandet und
    landete unverändert als `<ram:CountryID>Deutschland</ram:CountryID>` in der
    eingebetteten XML."""
    pfad = tmp_path / "unzulaessig.md"
    pfad.write_text(LAENDERCODE_UNGUELTIG, encoding="utf-8")
    bericht = falzmarke.linte(pfad, profil_verzeichnis=PROFILE)
    assert "rechnung.land" in {b.regel for b in bericht.befunde}, (
        "`land: Deutschland` ist kein ISO-3166-1-Alpha-2-Code und bleibt trotzdem "
        "unbeanstandet — die XML trägt ihn unverändert als CountryID weiter")
