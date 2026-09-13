"""Beispiele, Goldens und Gegenproben für die Rechnungsfassung (#119).

Brief und E-Mail haben beide ihre Beispielsuite mit byteweisem Golden
(`tests/test_email_beispiele.py`). Die Rechnung bekommt hier dieselbe Zusage:
jedes Beispiel läuft in der CI, wird gegen ein eingefrorenes Golden gehalten,
und jede neue Prüfung trägt eine Gegenprobe, die belegt, dass sie anschlägt.

## Was schon da ist — nicht hier verdoppelt

Ein Teil der in #119 verlangten Gegenproben existiert bereits aus #116/#118 und
ist bewusst nicht noch einmal geschrieben:

- **„Ein Betrag nur im PDF"**: `tests/test_rechnung_treue.py::test_ein_betrag_nur_im_pdf_faellt_auf`.
- **„Eine fehlende Pflichtangabe"**: `scripts/erechnung_ohne_referenz.py` entfernt
  die Käuferreferenz (BT-10) aus einer Kopie der XRechnung; `erechnung_pruefen.py`
  und `erechnung_kosit.py` verlangen in der CI, dass Mustang bzw. der
  KoSIT-Validator genau an `BR-DE-15` scheitern (siehe `.github/workflows/ci.yml`,
  Job „E-Rechnung (Mustang, fremdes Werkzeug)" und „E-Rechnung (KoSIT-Validator)").
- **„Eine Rechnung mit Leitweg-ID für einen öffentlichen Auftraggeber"**:
  `examples/xrechnung.md`.

## Was hier neu ist

- Zwei Beispiele fehlen noch: eine Rechnung mit mehreren Steuersätzen und eine
  Kleinbetragsrechnung (§ 33 UStDV, Gesamtbetrag höchstens 250 €).
- Es gibt noch kein byteweises Golden für PDF oder XML einer Rechnung.
- **„Ein Steuersatz nur in der XML"** und **„ein unzulässiger Codelistenwert"**
  sind am 13.09.2026 echte, unsabotierte Lücken — kein Monkeypatch nötig, um sie
  zu zeigen:

  - Die Positionstabelle im PDF zeigt nie den Steuersatz einer einzelnen
    Position (`cli.py:_positionstabelle`, Spalten Position/Menge/Einzelpreis/
    Betrag) — nur die Sammelzeilen aus `summen.steuer` als „Umsatzsteuer NN %".
    Trägt eine Position einen Satz, für den `summen.steuer` keine Zeile hat,
    verlässt dieser Satz die Quelle nur in Richtung XML. ✓ VERIFIZIERT: Für
    eine Rechnung mit Positionen zu 19 % und 7 %, aber `summen.steuer` nur für
    19 %, meldet `falzmarke.linte()` nichts (`bericht.befunde == []`), obwohl
    die eingebettete XML `RateApplicablePercent` 7.00 trägt.
  - `land:` — sowohl `rechnung.land` im Profil als auch
    `empfaenger_anschrift.land` — wird nur auf Vorhandensein geprüft
    (`lint.py`, `EMPFAENGER_ANSCHRIFT_PFLICHT`), nie auf einen gültigen
    ISO-3166-1-Alpha-2-Code. ✓ VERIFIZIERT: `land: Deutschland` bleibt
    unbeanstandet und landet unverändert als `<ram:CountryID>Deutschland</...>`
    in der XML — ein Empfänger-Validator lehnt das ab, falzmarke sagt nichts.

## Der PDF-Golden-Vorbehalt (Abnahme 1, #119)

„Beim PDF gilt dieselbe Vorsicht wie bei der Mahnungs-Mail mit Anlage: Ein
zweiter Renderlauf derselben Quelle liefert andere Bytes." — geprüft, bevor
hier ein Golden entsteht: ✓ VERIFIZIERT am 13.09.2026, zwei Renderläufe je
`examples/rechnung.md` und `examples/xrechnung.md` sind bytegleich (kein
Zeitstempel, keine UUID, kein `SOURCE_DATE_EPOCH` nötig — anders als bei der
`.eml`). Ein Golden-Byte-Vergleich ist damit ohne zusätzliche Einfriertechnik
tragfähig.
"""

from __future__ import annotations

from pathlib import Path

import pypdf
import pytest

from falzmarke import cli as falzmarke
from conftest import REPO, PROFILE, RECHNUNG_BEISPIELE

GOLDEN = REPO / "tests" / "golden" / "rechnung"

IDS = dict(ids=lambda p: p.stem)


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
    Steuersätze" — nicht nur mehrere Positionen. `rechnung.md` und
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
    pdf = _setze(beispiel, tmp_path)
    soll = GOLDEN / f"{beispiel.stem}.pdf"
    assert pdf.read_bytes() == soll.read_bytes(), (
        f"{beispiel.name} rendert andere Bytes als sein Golden — bei einer gewollten "
        "Änderung das Golden neu erzeugen und den Diff mitlesen.")


@pytest.mark.parametrize("beispiel", RECHNUNG_BEISPIELE, **IDS)
def test_die_eingebettete_xml_entspricht_ihrem_golden(beispiel, tmp_path):
    pdf = _setze(beispiel, tmp_path)
    soll = GOLDEN / f"{beispiel.stem}.xml"
    assert _xml_bytes(pdf) == soll.read_bytes(), (
        f"die aus {beispiel.name} eingebettete XML weicht von ihrem Golden ab.")


def test_der_pdf_vergleich_kann_rot_werden(tmp_path):
    """Gegenprobe: eine geänderte Quelle darf nicht zum alten Golden passen."""
    beispiel = RECHNUNG_BEISPIELE[0]
    sabotiert = _kopie(beispiel, tmp_path, "betreff: ", "betreff: Nachtrag — ")
    ist = _setze(sabotiert, tmp_path).read_bytes()
    soll = (GOLDEN / f"{beispiel.stem}.pdf").read_bytes()
    assert ist != soll


def test_zwei_laeufe_ueber_dasselbe_beispiel_sind_bytegleich(tmp_path):
    """Ohne Determinismus wäre der Golden-Vergleich oben ein Zufallsgenerator.

    ✓ VERIFIZIERT (siehe Modul-Docstring) — hier als Regressionswächter: Sollte
    ein künftiger Zeitstempel oder eine UUID einziehen, fällt es hier auf, statt
    stumm jedes PDF-Golden altern zu lassen.
    """
    beispiel = RECHNUNG_BEISPIELE[0]
    erst = _setze(beispiel, tmp_path / "a").read_bytes()
    zweit = _setze(beispiel, tmp_path / "b").read_bytes()
    assert erst == zweit


# ── „Ein Steuersatz nur in der XML" (Abnahme 2 und 3) ───────────────────────
#
# Die Positionstabelle im PDF zeigt nie den Steuersatz einer einzelnen Position
# — nur `summen.steuer` als Sammelzeile „Umsatzsteuer NN %". Ein Positions-Satz
# ohne passende Sammelzeile verlässt die Quelle nur Richtung XML.

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
    assert not bericht.befunde, [b.als_zeile("rechnung.md") for b in bericht.befunde]


def test_ein_steuersatz_ohne_summenzeile_wird_gemeldet(tmp_path):
    """Der teure Fall aus #119: Ein Positions-Steuersatz, der in `summen.steuer`
    keine Entsprechung hat, bleibt heute stumm — im PDF steht nur „Umsatzsteuer
    19 %", in der XML zusätzlich `RateApplicablePercent` 7.00.
    """
    pfad = tmp_path / "gemischt.md"
    pfad.write_text(STEUERSATZ_OHNE_SUMMENZEILE, encoding="utf-8")
    bericht = falzmarke.linte(pfad, profil_verzeichnis=PROFILE)
    assert bericht.befunde, (
        "eine Position mit einem Steuersatz ohne passende `summen.steuer`-Zeile "
        "bleibt unbeanstandet — genau der stille Fall aus #119")


# ── „Ein unzulässiger Codelistenwert" (Abnahme 2 und 3) ─────────────────────
#
# `land:` wird nur auf Vorhandensein geprüft, nie auf einen gültigen
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
    """✓ VERIFIZIERT am 13.09.2026: `land: Deutschland` bleibt unbeanstandet und
    landet unverändert als `<ram:CountryID>Deutschland</ram:CountryID>` in der
    eingebetteten XML."""
    pfad = tmp_path / "unzulaessig.md"
    pfad.write_text(LAENDERCODE_UNGUELTIG, encoding="utf-8")
    bericht = falzmarke.linte(pfad, profil_verzeichnis=PROFILE)
    assert bericht.befunde, (
        "`land: Deutschland` ist kein ISO-3166-1-Alpha-2-Code und bleibt trotzdem "
        "unbeanstandet — die XML trägt ihn unverändert als CountryID weiter")
