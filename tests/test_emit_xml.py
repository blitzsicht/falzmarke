"""Die Rechnung als XML nach EN 16931 (#116).

Der Emitter setzt den geprüften Kopf, nicht den Brieftext. Was hier geprüft
wird, ist deshalb nicht das Aussehen, sondern die Treue: Steht in der XML
dasselbe wie in der Quelle, und fehlt sichtbar, was fehlt?

**Die Struktur stammt nicht aus diesem Test.** Sie ist an `EN16931_Einfach.pdf`
aus dem Mustang-Testmaterial abgelesen, das derselbe Prüfer als gültig
bestätigt hat. Dieser Test hält fest, was der Emitter daraus macht; ob das
Ergebnis gilt, sagt der fremde Prüfer in der CI — nicht wir selbst.
"""

from __future__ import annotations

import copy
import xml.etree.ElementTree as ET

import pytest
import yaml

from falzmarke import emit_xml
from conftest import PROFILE

RAM = emit_xml.RAM
RSM = emit_xml.RSM
UDT = emit_xml.UDT

KOPF = {
    "typ": "rechnung", "profil": "example", "datum": "2026-09-11",
    "rechnungsnummer": "2026-0042",
    "leistungsdatum": "2026-10-03", "zahlungsziel": "2026-10-31",
    "empfaenger_anschrift": {
        "name": "Muster GmbH", "strasse": "Musterstraße 1",
        "plz": "12345", "ort": "Musterstadt", "land": "DE"},
    "positionen": [
        {"bezeichnung": "Technik und Aufbau", "menge": 1,
         "einzelpreis": 1240.00, "steuersatz": 19, "betrag": 1240.00},
        {"bezeichnung": "Bestuhlung", "menge": 120, "einheit": "Stück",
         "einzelpreis": 3.00, "steuersatz": 19, "betrag": 360.00},
    ],
    "summen": {"netto": 1600.00, "brutto": 1904.00,
               "steuer": [{"satz": 19, "betrag": 304.00, "basis": 1600.00}]},
}


@pytest.fixture(scope="module")
def profil() -> dict:
    return yaml.safe_load((PROFILE / "example.yaml").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def baum(profil) -> ET.Element:
    return ET.fromstring(emit_xml.erzeuge(KOPF, profil))


def _ohne(**ersetzt) -> dict:
    kopf = copy.deepcopy(KOPF)
    for schluessel, wert in ersetzt.items():
        if wert is None:
            kopf.pop(schluessel, None)
        else:
            kopf[schluessel] = wert
    return kopf


def _finde(baum, pfad: str) -> str | None:
    knoten = baum.find(pfad)
    return None if knoten is None else knoten.text


# ── Was in der XML steht, steht auch in der Quelle ──────────────────────────

def test_das_profil_ist_en16931_und_nicht_xrechnung(baum):
    """`…#compliant#…xrechnung` wäre das Profil aus #117, nicht dieses."""
    pfad = (f"{{{RSM}}}ExchangedDocumentContext/"
            f"{{{RAM}}}GuidelineSpecifiedDocumentContextParameter/{{{RAM}}}ID")
    assert _finde(baum, pfad) == "urn:cen.eu:en16931:2017"


def test_die_rechnungsnummer_kommt_unveraendert_an(baum):
    assert _finde(baum, f"{{{RSM}}}ExchangedDocument/{{{RAM}}}ID") == "2026-0042"


def test_es_ist_eine_rechnung_und_keine_gutschrift(baum):
    assert _finde(baum, f"{{{RSM}}}ExchangedDocument/{{{RAM}}}TypeCode") == "380"


def test_das_datum_steht_im_format_102(baum):
    """`2026-09-11` wird `20260911` — nicht ISO, das Format steht in der Referenz."""
    pfad = (f"{{{RSM}}}ExchangedDocument/{{{RAM}}}IssueDateTime/"
            f"{{{UDT}}}DateTimeString")
    knoten = baum.find(pfad)
    assert knoten.text == "20260911"
    assert knoten.get("format") == "102"


def test_die_ust_idnr_traegt_das_schema_va(baum, profil):
    """`VA` ist die USt-IdNr., `FC` die Steuernummer — beides aus der Referenz."""
    treffer = baum.findall(f".//{{{RAM}}}SellerTradeParty/"
                           f"{{{RAM}}}SpecifiedTaxRegistration/{{{RAM}}}ID")
    schemata = {k.get("schemeID"): k.text for k in treffer}
    assert schemata == {"VA": profil["rechnung"]["ust_idnr"]}


def test_die_steuernummer_traegt_das_schema_fc(profil):
    eigen = copy.deepcopy(profil)
    eigen["rechnung"] = {"steuernummer": "244/107/01234", "land": "DE"}
    baum = ET.fromstring(emit_xml.erzeuge(KOPF, eigen))
    treffer = baum.findall(f".//{{{RAM}}}SellerTradeParty/"
                           f"{{{RAM}}}SpecifiedTaxRegistration/{{{RAM}}}ID")
    assert {k.get("schemeID"): k.text for k in treffer} == {"FC": "244/107/01234"}


def test_jede_position_wird_eine_zeile(baum):
    zeilen = baum.findall(f".//{{{RAM}}}IncludedSupplyChainTradeLineItem")
    assert len(zeilen) == len(KOPF["positionen"])
    namen = [z.find(f"{{{RAM}}}SpecifiedTradeProduct/{{{RAM}}}Name").text for z in zeilen]
    assert namen == [p["bezeichnung"] for p in KOPF["positionen"]]


def test_der_positionsbetrag_wird_uebernommen_nicht_gebildet(baum):
    """1240.00 steht in der Quelle. Menge mal Einzelpreis wäre dasselbe — und
    genau deshalb taugt diese Position nicht als Beleg; die zweite schon:
    120 × 3,00 wäre 360,00, aber gebildet wird nichts (ADR 0039)."""
    betraege = [k.text for k in baum.findall(
        f".//{{{RAM}}}SpecifiedTradeSettlementLineMonetarySummation/"
        f"{{{RAM}}}LineTotalAmount")]
    assert betraege == ["1240.00", "360.00"]


def test_eine_bekannte_einheit_wird_zum_code(baum):
    mengen = baum.findall(f".//{{{RAM}}}BilledQuantity")
    assert [m.get("unitCode") for m in mengen] == ["C62", "H87"]


def test_die_summen_kommen_aus_der_quelle(baum):
    gesamt = baum.find(f".//{{{RAM}}}SpecifiedTradeSettlementHeaderMonetarySummation")
    assert gesamt.find(f"{{{RAM}}}LineTotalAmount").text == "1600.00"
    assert gesamt.find(f"{{{RAM}}}GrandTotalAmount").text == "1904.00"
    assert gesamt.find(f"{{{RAM}}}DuePayableAmount").text == "1904.00"


# ── Was fehlt, fehlt sichtbar ───────────────────────────────────────────────

def test_ohne_empfaengeranschrift_entsteht_keine_datei(profil):
    """Aus den freien Zeilen von `empfaenger:` wird nicht geraten."""
    with pytest.raises(emit_xml.RechnungUnvollstaendig, match="empfaenger_anschrift"):
        emit_xml.erzeuge(_ohne(empfaenger_anschrift=None), profil)


def test_ohne_bemessungsgrundlage_entsteht_keine_datei(profil):
    """EN 16931 verlangt sie je Steuersatz; summiert wird nicht (ADR 0039)."""
    summen = copy.deepcopy(KOPF["summen"])
    summen["steuer"][0].pop("basis")
    with pytest.raises(emit_xml.RechnungUnvollstaendig, match="basis"):
        emit_xml.erzeuge(_ohne(summen=summen), profil)


def test_ohne_summen_entsteht_keine_datei(profil):
    with pytest.raises(emit_xml.RechnungUnvollstaendig, match="summen"):
        emit_xml.erzeuge(_ohne(summen=None), profil)


def test_eine_unbekannte_einheit_wird_gemeldet_statt_geraten(profil):
    """Ein selbstgewählter Code läuft durch und scheitert beim Empfänger."""
    positionen = copy.deepcopy(KOPF["positionen"])
    positionen[0]["einheit"] = "Sack"
    with pytest.raises(emit_xml.RechnungUnvollstaendig, match="Sack"):
        emit_xml.erzeuge(_ohne(positionen=positionen), profil)


def test_ein_profil_ohne_steuerangabe_entsteht_nicht(profil):
    eigen = copy.deepcopy(profil)
    eigen["rechnung"] = {"land": "DE"}
    with pytest.raises(emit_xml.RechnungUnvollstaendig, match="ust_idnr"):
        emit_xml.erzeuge(KOPF, eigen)


def test_ein_kaputtes_datum_wird_gemeldet(profil):
    with pytest.raises(emit_xml.RechnungUnvollstaendig, match="kein Datum"):
        emit_xml.erzeuge(_ohne(datum="11.09.2026"), profil)


# ── Übertragen statt bilden: der Steuergesamtbetrag (Review von #116) ───────
#
# Bis zum 13.09.2026 bildete der Emitter `TaxTotalAmount` per `sum()`. Die Tests
# darüber sahen es nicht: Die Beispielrechnung hat einen Steuersatz, und die Summe
# eines einzelnen Werts ist dieser Wert.

ZWEI_SAETZE = {"netto": 1600.00, "brutto": 1832.00,
               "steuer": [{"satz": 19, "basis": 1000.00, "betrag": 190.00},
                          {"satz": 7, "basis": 600.00, "betrag": 42.00}]}


def _steuergesamt(baum) -> str:
    return baum.find(f".//{{{RAM}}}TaxTotalAmount").text


def test_bei_einem_steuersatz_wird_sein_betrag_uebernommen(baum):
    assert _steuergesamt(baum) == "304.00"


def test_mehrere_saetze_ohne_steuer_gesamt_brechen_ab(profil):
    with pytest.raises(emit_xml.RechnungUnvollstaendig, match="steuer_gesamt"):
        emit_xml.erzeuge(_ohne(summen=copy.deepcopy(ZWEI_SAETZE)), profil)


def test_steuer_gesamt_wird_uebernommen_auch_wenn_es_abweicht(profil):
    """Die Trennschärfe. Die Einzelbeträge ergeben 232,00; in der Quelle steht 233,00.

    Ein Test mit passender Zahl bewiese nichts — er wäre auch grün, wenn der Emitter
    wieder summierte. Nur ein abweichender Wert zeigt, dass übertragen wird.
    """
    summen = copy.deepcopy(ZWEI_SAETZE)
    summen["steuer_gesamt"] = 233.00
    baum = ET.fromstring(emit_xml.erzeuge(_ohne(summen=summen), profil))
    assert _steuergesamt(baum) == "233.00"


def test_ohne_steuereintrag_entsteht_keine_datei(profil):
    """Die Kategorie ist fest `S`; eine steuerfreie Rechnung wäre falsch ausgezeichnet."""
    summen = copy.deepcopy(KOPF["summen"])
    summen["steuer"] = []
    with pytest.raises(emit_xml.RechnungUnvollstaendig, match="§ 19"):
        emit_xml.erzeuge(_ohne(summen=summen), profil)


# ── Keine stille Rundung, kein Traceback ────────────────────────────────────

def test_ein_betrag_mit_drei_nachkommastellen_wird_nicht_gerundet(profil):
    positionen = copy.deepcopy(KOPF["positionen"])
    positionen[0]["betrag"] = 1240.005
    with pytest.raises(emit_xml.RechnungUnvollstaendig, match=r"positionen\[1\]\.betrag"):
        emit_xml.erzeuge(_ohne(positionen=positionen), profil)


def test_text_statt_zahl_ergibt_eine_meldung_und_keinen_traceback(profil):
    """Vorher erreichte `abc` ein nacktes `float()` — ein `ValueError`, den die CLI
    nicht fängt."""
    summen = copy.deepcopy(KOPF["summen"])
    summen["netto"] = "abc"
    with pytest.raises(emit_xml.RechnungUnvollstaendig, match="summen.netto"):
        emit_xml.erzeuge(_ohne(summen=summen), profil)
