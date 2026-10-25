"""Das Thunderbird-Add-on selbst (ADR 0052): was es kann, und was nie.

Das Add-on läuft in Thunderbird mit vollen Rechten — eine Experiment-API, die
Fenster öffnen darf, dürfte technisch auch senden oder löschen. Die Zusage
„die Brücke kann nicht senden“ steht deshalb hier als Prüfung am Quelltext,
mit Gegenprobe, wie `test_postfach.py` es für die IMAP-Befehle tut.
"""

from __future__ import annotations

import importlib.util
import json
import re
import zipfile

import pytest
from conftest import REPO
from falzmarke import bruecke

ADDON = REPO / "thunderbird" / "entwurfsbruecke"
QUELLTEXT = (ADDON / "implementation.js").read_text(encoding="utf-8")

#: Was das Add-on nie aufrufen darf: senden, löschen, verschieben, Flags setzen.
VERBOTEN = (
    "SendMsg", "sendMessage", "GenericSendMessage", "nsIMsgCompDeliverMode",
    "SendMessageFile", "deleteMessages", "DeleteMessages", "StoreImapFlags",
    "storeImapFlags", "copyMessages", "CopyMessages", "moveMessages", "expunge",
    "emptyTrash", "deleteSelf",
)


def verbotene_aufrufe(text: str) -> list[str]:
    return [wort for wort in VERBOTEN if re.search(rf"\b{wort}\b", text)]


def befehle(text: str) -> set[str]:
    return set(re.findall(r'case "(\w+)":', text))


def test_das_add_on_kennt_nur_seine_vier_befehle():
    assert befehle(QUELLTEXT) == {"ping", "entwurf_oeffnen", "fenster", "protokoll"}


def test_das_add_on_ruft_nichts_auf_was_sendet_oder_loescht():
    assert verbotene_aufrufe(QUELLTEXT) == []


@pytest.mark.parametrize("probe", [
    "gMsgCompose.SendMsg(Ci.nsIMsgCompDeliverMode.Now, id, null, null, null);",
    "folder.deleteMessages([hdr], null, true, false, null, false);",
    "imapFolder.StoreImapFlags(0x0008, true, [key], null);",
])
def test_gegenprobe_ein_sendender_aufruf_faellt_auf(probe):
    assert verbotene_aufrufe(QUELLTEXT + "\n" + probe)


def test_gegenprobe_ein_neuer_befehl_faellt_auf():
    assert befehle(QUELLTEXT + '\n    case "senden":') != befehle(QUELLTEXT)


def test_der_port_lauscht_nur_auf_127_0_0_1():
    assert re.search(r"server\.init\(\s*port\s*,\s*true\s*,", QUELLTEXT)


def test_eine_browser_anfrage_wird_abgewiesen():
    """Eine Webseite kann den Browser an localhost schicken lassen. Ihre erste
    Zeile ist immer „GET …“ oder „POST …“ — das Add-on nimmt nur Zeilen, die
    mit „{“ beginnen."""
    assert 'if (!zeile.startsWith("{"))' in QUELLTEXT


def test_falzmarke_kennt_jede_fehlerkennung_des_add_ons():
    kennungen = set(re.findall(r'fehler: "(\w+)"', QUELLTEXT))
    assert kennungen and kennungen <= set(bruecke.FEHLERTEXTE)


def test_das_manifest():
    manifest = json.loads((ADDON / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["manifest_version"] == 2
    assert manifest["browser_specific_settings"]["gecko"]["id"] == "entwurfsbruecke@falzmarke"
    api = manifest["experiment_apis"]["entwurfsbruecke"]
    assert (ADDON / api["schema"]).is_file()
    assert (ADDON / api["parent"]["script"]).is_file()
    assert "permissions" not in manifest, "es braucht keine Berechtigung außer dem Experiment"


def _packer():
    spec = importlib.util.spec_from_file_location("falzmarke_xpi_packen",
                                                  REPO / "scripts" / "xpi_packen.py")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def test_das_paket_ist_vollstaendig_und_reproduzierbar(tmp_path):
    packer = _packer()
    erstes = packer.packe(ziel=tmp_path / "a")
    zweites = packer.packe(ziel=tmp_path / "b")
    assert erstes.read_bytes() == zweites.read_bytes()
    version = json.loads((ADDON / "manifest.json").read_text(encoding="utf-8"))["version"]
    assert erstes.name == f"entwurfsbruecke-{version}.xpi"
    with zipfile.ZipFile(erstes) as archiv:
        assert archiv.namelist() == list(packer.DATEIEN)
        assert archiv.read("implementation.js") == (ADDON / "implementation.js").read_bytes()
