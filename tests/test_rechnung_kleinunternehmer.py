"""Rechnungen von Kleinunternehmern (#317, ADR 0041).

Die lint-Regeln mit Kontrolle und Sabotage stehen in `tests/test_gegenbeweis.py`.

Kategorie E, Satz 0, Steuer 0, der Hinweis aus dem Profil als BT-120 und BT-33
und im PDF unter der Tabelle. Dass Mustang und der KoSIT-Validator die Datei
annehmen und die Gegenproben an BR-E-10 und BR-E-05 scheitern, prüft die CI;
hier steht, was ohne fremdes Werkzeug messbar ist — und je Regel die Stelle,
an der sie anschlägt.
"""

from __future__ import annotations

import copy
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pypdf
import pytest
import yaml

from falzmarke import cli as falzmarke
from falzmarke import emit_xml
from conftest import REPO, PROFILE

RAM = emit_xml.RAM
QUELLE = REPO / "examples" / "rechnung-kleinunternehmer.md"
PROFIL_DATEI = REPO / "examples" / "profiles" / "example-kleinunternehmer.yaml"
HINWEIS = "Steuerfreie Kleinunternehmerleistung nach § 19 UStG."


def _profil() -> dict:
    return yaml.safe_load(PROFIL_DATEI.read_text(encoding="utf-8"))


def _kopf() -> dict:
    return yaml.safe_load(QUELLE.read_text(encoding="utf-8").split("---", 2)[1])


def _baum(kopf=None, profil=None) -> ET.Element:
    return ET.fromstring(emit_xml.erzeuge(kopf or _kopf(), profil or _profil()))


# ── Die XML ─────────────────────────────────────────────────────────────────

def test_jede_steuerangabe_traegt_kategorie_e_und_satz_null():
    baum = _baum()
    steuern = baum.findall(f".//{{{RAM}}}ApplicableTradeTax")
    assert len(steuern) == len(_kopf()["positionen"]) + 1
    assert {s.findtext(f"{{{RAM}}}CategoryCode") for s in steuern} == {"E"}
    assert {s.findtext(f"{{{RAM}}}RateApplicablePercent") for s in steuern} == {"0.00"}


def test_die_aufschluesselung_traegt_steuer_null_und_den_hinweis():
    baum = _baum()
    kopf = baum.find(f".//{{{RAM}}}ApplicableHeaderTradeSettlement/{{{RAM}}}ApplicableTradeTax")
    assert kopf.findtext(f"{{{RAM}}}CalculatedAmount") == "0.00"
    assert kopf.findtext(f"{{{RAM}}}BasisAmount") == "370.00"
    assert kopf.findtext(f"{{{RAM}}}ExemptionReason") == HINWEIS
    # Kein VATEX-Code: Die Liste kennt keinen passenden (ADR 0041, Entscheidung 1).
    assert kopf.find(f"{{{RAM}}}ExemptionReasonCode") is None


def test_der_hinweis_steht_auch_als_bt33_beim_verkaeufer():
    baum = _baum()
    assert baum.findtext(f".//{{{RAM}}}SellerTradeParty/{{{RAM}}}Description") == HINWEIS
    assert baum.find(f".//{{{RAM}}}BuyerTradeParty/{{{RAM}}}Description") is None


def test_gesamtbetraege_ohne_steuer():
    summe = _baum().find(f".//{{{RAM}}}SpecifiedTradeSettlementHeaderMonetarySummation")
    werte = {k.tag.split("}")[1]: k.text for k in summe}
    assert werte["TaxTotalAmount"] == "0.00"
    assert werte["TaxBasisTotalAmount"] == werte["GrandTotalAmount"] == werte["DuePayableAmount"] == "370.00"


def test_ohne_status_bleibt_es_eine_regelsatz_rechnung():
    """Kontrollprobe: Das mitgelieferte Profil ist kein Kleinunternehmer — die
    bestehende Rechnung behält Kategorie S, keinen Hinweis, keine BT-33."""
    profil = yaml.safe_load((PROFILE / "example.yaml").read_text(encoding="utf-8"))
    kopf = yaml.safe_load((REPO / "examples" / "rechnung.md").read_text(encoding="utf-8").split("---", 2)[1])
    baum = ET.fromstring(emit_xml.erzeuge(kopf, profil))
    assert {s.findtext(f"{{{RAM}}}CategoryCode") for s in baum.iter(f"{{{RAM}}}ApplicableTradeTax")} == {"S"}
    assert baum.find(f".//{{{RAM}}}ExemptionReason") is None
    assert baum.find(f".//{{{RAM}}}SellerTradeParty/{{{RAM}}}Description") is None


@pytest.mark.parametrize("wert", ["ja", "true", 1, "yes"])
def test_nur_ein_echtes_true_macht_den_status(wert):
    profil = _profil()
    profil["rechnung"]["kleinunternehmer"] = wert
    assert not emit_xml.ist_kleinunternehmer(profil)


# ── Der Emitter setzt die Regeln selbst durch (der MCP-Dienst ruft kein lint) ─

@pytest.mark.parametrize("aenderung, wortlaut", [
    (lambda k, p: p["rechnung"].pop("kleinunternehmer_hinweis"), "kleinunternehmer_hinweis"),
    (lambda k, p: k["positionen"][0].__setitem__("steuersatz", 19), "steuersatz"),
    (lambda k, p: k["summen"].__setitem__("steuer", [{"satz": 19, "basis": 370, "betrag": 70.3}]),
     "steuer"),
    (lambda k, p: k["summen"].__setitem__("brutto", 440.30), "brutto"),
])
def test_der_emitter_bricht_ab(aenderung, wortlaut):
    kopf, profil = copy.deepcopy(_kopf()), _profil()
    aenderung(kopf, profil)
    with pytest.raises(emit_xml.RechnungUnvollstaendig, match=wortlaut):
        emit_xml.erzeuge(kopf, profil)


def test_ohne_status_und_ohne_steuerzeile_nennt_die_meldung_das_profilfeld():
    profil = _profil()
    profil["rechnung"]["kleinunternehmer"] = False
    kopf = copy.deepcopy(_kopf())
    for position in kopf["positionen"]:
        position["steuersatz"] = 19
    with pytest.raises(emit_xml.RechnungUnvollstaendig, match="kleinunternehmer: true"):
        emit_xml.erzeuge(kopf, profil)


# ── Das PDF, und dass es dasselbe sagt wie die XML ──────────────────────────

@pytest.fixture(scope="module")
def gesetzt(tmp_path_factory):
    ziel = tmp_path_factory.mktemp("ku") / "rechnung.pdf"
    return falzmarke.rendere(QUELLE, ziel, profil_verzeichnis=PROFILE)[0]


def _pdftext(pdf) -> str:
    import pdfplumber

    with pdfplumber.open(str(pdf)) as dokument:
        return "\n".join(seite.extract_text() or "" for seite in dokument.pages)


def _eingebettet(pdf) -> ET.Element:
    wurzel = pypdf.PdfReader(str(pdf)).trailer["/Root"]
    datei = wurzel["/AF"][0].get_object()["/EF"]["/F"]
    return ET.fromstring(datei.get_object().get_data().decode("utf-8"))


def test_das_pdf_zeigt_keine_steuer_und_keine_doppelte_nettozeile(gesetzt):
    text = _pdftext(gesetzt)
    assert "Gesamtbetrag 370,00 EUR" in text
    # Die Tabellenzeilen, nicht das Wort: Der Brieftext sagt selbst „keine Umsatzsteuer".
    assert not re.search(r"^Summe netto ", text, re.M), text
    assert not re.search(r"^Umsatzsteuer [\d,.]+ %", text, re.M), text


def test_der_hinweis_steht_im_pdf_im_wortlaut_der_xml(gesetzt):
    """Treue: gemessen am fertigen Dokument, PDF-Text gegen eingebettete XML."""
    grund = _eingebettet(gesetzt).findtext(f".//{{{RAM}}}ExemptionReason")
    assert grund == HINWEIS
    assert grund in _pdftext(gesetzt)


def test_ein_hinweis_nur_in_der_xml_faellt_auf(tmp_path, monkeypatch):
    """Gegenprobe zur Treue: Fehlt der Hinweis im PDF, muss die Prüfung oben rot werden."""
    original = falzmarke._positionstabelle
    monkeypatch.setattr(falzmarke, "_positionstabelle",
                        lambda kopf, profil=None: original(kopf, None))
    pdf = falzmarke.rendere(QUELLE, tmp_path / "ohne.pdf", profil_verzeichnis=PROFILE)[0]
    grund = _eingebettet(pdf).findtext(f".//{{{RAM}}}ExemptionReason")
    assert grund == HINWEIS
    assert grund not in _pdftext(pdf)


def test_das_beispielprofil_ist_das_mitgelieferte_bis_auf_zwei_stellen():
    """Ein abgeleitetes Profil, das still vom Original wegdriftet, prüfte am Ende
    etwas anderes als das, was Nutzer bekommen."""
    original = yaml.safe_load((PROFILE / "example.yaml").read_text(encoding="utf-8"))
    abgeleitet = _profil()
    for schluessel in set(original) | set(abgeleitet):
        if schluessel in ("rechnung", "fusszeile"):
            continue
        assert original.get(schluessel) == abgeleitet.get(schluessel), schluessel
