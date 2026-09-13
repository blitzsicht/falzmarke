"""Die Gegenprobe für XRechnung entsteht zählbar (#117)."""

from __future__ import annotations

import sys

from conftest import REPO

sys.path.insert(0, str(REPO / "scripts"))
import erechnung_ohne_referenz as eor  # noqa: E402

from falzmarke import emit_xml  # noqa: E402

XML = ('<rsm:CrossIndustryInvoice xmlns:rsm="{rsm}" xmlns:ram="{ram}"><rsm:SupplyChainTradeTransaction>'
       '<ram:ApplicableHeaderTradeAgreement>{ref}<ram:SellerTradeParty/></ram:ApplicableHeaderTradeAgreement>'
       '</rsm:SupplyChainTradeTransaction></rsm:CrossIndustryInvoice>')


def _datei(tmp_path, ref):
    pfad = tmp_path / "ein.xml"
    pfad.write_text(XML.format(rsm=eor.RSM, ram=eor.RAM, ref=ref), encoding="utf-8")
    return pfad


def test_die_referenz_ist_danach_weg(tmp_path):
    ziel = tmp_path / "aus.xml"
    assert eor.main([str(_datei(tmp_path, "<ram:BuyerReference>04011000-12345-03</ram:BuyerReference>")), str(ziel)]) == 0
    text = ziel.read_text(encoding="utf-8")
    assert "BuyerReference" not in text and "SellerTradeParty" in text


def test_ohne_referenz_in_der_quelle_entsteht_keine_gegenprobe(tmp_path):
    """Gäbe es nichts zu entfernen, wäre die „Gegenprobe" ein gültiges Dokument."""
    ziel = tmp_path / "aus.xml"
    assert eor.main([str(_datei(tmp_path, "")), str(ziel)]) == 1
    assert not ziel.exists()


def test_die_namensraeume_stimmen_mit_dem_emitter_ueberein():
    assert (eor.RSM, eor.RAM, eor.UDT, eor.QDT) == (emit_xml.RSM, emit_xml.RAM, emit_xml.UDT, emit_xml.QDT)
