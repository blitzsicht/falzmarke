"""Die Gegenprobe zu BR-CO-26 entsteht zählbar (#316)."""

from __future__ import annotations

import sys

from conftest import REPO

sys.path.insert(0, str(REPO / "scripts"))
import erechnung_ohne_kennung as eok  # noqa: E402

XML = ('<rsm:CrossIndustryInvoice xmlns:rsm="{rsm}" xmlns:ram="{ram}"><rsm:ExchangedDocument>'
       '<ram:ID>2026-0042</ram:ID></rsm:ExchangedDocument><rsm:SupplyChainTradeTransaction>'
       '<ram:ApplicableHeaderTradeAgreement><ram:SellerTradeParty>{kennung}<ram:Name>A</ram:Name>'
       '<ram:SpecifiedTaxRegistration><ram:ID schemeID="FC">244/107/01234</ram:ID>'
       '</ram:SpecifiedTaxRegistration></ram:SellerTradeParty></ram:ApplicableHeaderTradeAgreement>'
       '</rsm:SupplyChainTradeTransaction></rsm:CrossIndustryInvoice>')


def _datei(tmp_path, kennung):
    pfad = tmp_path / "ein.xml"
    pfad.write_text(XML.format(rsm=eok.RSM, ram=eok.RAM, kennung=kennung), encoding="utf-8")
    return pfad


def test_nur_die_kennung_ist_danach_weg(tmp_path):
    ziel = tmp_path / "aus.xml"
    quelle = _datei(tmp_path, "<ram:ID>244/107/01234</ram:ID>")
    assert eok.main([str(quelle), str(ziel)]) == 0
    text = ziel.read_text(encoding="utf-8")
    # Die Kennung ist weg; Rechnungsnummer und Steuernummer (BT-32) bleiben.
    assert text.count("244/107/01234") == 1 and 'schemeID="FC"' in text
    assert "2026-0042" in text


def test_ohne_kennung_in_der_quelle_entsteht_keine_gegenprobe(tmp_path):
    """Gäbe es nichts zu entfernen, wäre die „Gegenprobe" ein gültiges Dokument."""
    ziel = tmp_path / "aus.xml"
    assert eok.main([str(_datei(tmp_path, "")), str(ziel)]) == 1
    assert not ziel.exists()
