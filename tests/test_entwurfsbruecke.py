"""Das Thunderbird-Add-on selbst (ADR 0054): was es kann, und was nie.

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
#: Alles, was in Thunderbird läuft: das Experiment und der Hintergrund (ADR 0055).
ALLE_JS = "\n".join(p.read_text(encoding="utf-8") for p in sorted(ADDON.glob("*.js")))

#: Was das Add-on nie aufrufen darf: senden, löschen, verschieben, Flags setzen,
#: den Inhalt des Fensters ändern. `sendMessage` deckt auch `runtime.sendMessage`
#: ab; das Add-on braucht keine Nachrichten zwischen seinen Teilen.
VERBOTEN = (
    "SendMsg", "sendMessage", "GenericSendMessage", "nsIMsgCompDeliverMode",
    "SendMessageFile", "deleteMessages", "DeleteMessages", "StoreImapFlags",
    "storeImapFlags", "copyMessages", "CopyMessages", "moveMessages", "expunge",
    "emptyTrash", "deleteSelf", "saveMessage", "setComposeDetails",
    "messages.delete", "messages.move", "messages.copy", "messages.update",
    "messages.archive", "messages.import",
)

#: Genau diese Rechte, keines mehr: Fenster lesen, gesendete Mails lesen, Konten lesen.
RECHTE = ["compose", "messagesRead", "accountsRead"]


def verbotene_aufrufe(text: str) -> list[str]:
    return [wort for wort in VERBOTEN if re.search(rf"\b{re.escape(wort)}\b", text)]


def fremde_rechte(manifest: dict) -> list:
    return [r for r in manifest.get("permissions", []) if r not in RECHTE]


def befehle(text: str) -> set[str]:
    return set(re.findall(r'case "(\w+)":', text))


def test_das_add_on_kennt_nur_seine_vier_befehle():
    assert befehle(QUELLTEXT) == {"ping", "entwurf_oeffnen", "fenster", "protokoll"}


def test_das_add_on_ruft_nichts_auf_was_sendet_oder_loescht():
    assert {p.name for p in ADDON.glob("*.js")} == {
        "implementation.js", "background.js", "vergleich.js"}
    assert verbotene_aufrufe(ALLE_JS) == []


@pytest.mark.parametrize("probe", [
    "gMsgCompose.SendMsg(Ci.nsIMsgCompDeliverMode.Now, id, null, null, null);",
    "folder.deleteMessages([hdr], null, true, false, null, false);",
    "imapFolder.StoreImapFlags(0x0008, true, [key], null);",
    "await browser.compose.sendMessage(tab.id);",
    "await browser.compose.saveMessage(tab.id);",
    "browser.runtime.sendMessage({});",
    "await browser.messages.delete([id], true);",
    "await browser.compose.setComposeDetails(tab.id, { to: [] });",
])
def test_gegenprobe_ein_sendender_aufruf_faellt_auf(probe):
    assert verbotene_aufrufe(ALLE_JS + "\n" + probe)


def test_die_sperre_waehlt_nicht_senden_vor():
    """Escape und das Schließen des Dialogs liefern bei `confirmEx` Knopf 1.
    Deshalb ist Knopf 1 „Nicht senden“ und vorgewählt; nur Knopf 0 sendet."""
    assert sperre_haelt_im_zweifel(QUELLTEXT)


@pytest.mark.parametrize(("alt", "neu"), [
    ("P.BUTTON_POS_1_DEFAULT", "P.BUTTON_POS_0_DEFAULT"),
    ('"Trotzdem senden",\n    "Nicht senden",', '"Nicht senden",\n    "Trotzdem senden",'),
    ("return wahl === 0;", "return wahl !== 0;"),
])
def test_gegenprobe_eine_sperre_die_im_zweifel_sendet_faellt_auf(alt, neu):
    assert QUELLTEXT.count(alt) == 1
    assert not sperre_haelt_im_zweifel(QUELLTEXT.replace(alt, neu))


def sperre_haelt_im_zweifel(text: str) -> bool:
    knoepfe = re.search(r'"(Trotzdem senden|Nicht senden)",\s*"(Trotzdem senden|Nicht senden)",',
                        text)
    return bool(knoepfe and knoepfe.groups() == ("Trotzdem senden", "Nicht senden")
                and "P.BUTTON_POS_1_DEFAULT" in text and "BUTTON_POS_0_DEFAULT" not in text
                and "return wahl === 0;" in text)


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
    assert manifest["permissions"] == RECHTE
    # Erst der Vergleich, dann der Hintergrund, der ihn braucht.
    assert manifest["background"]["scripts"] == ["vergleich.js", "background.js"]


@pytest.mark.parametrize("recht", ["compose.send", "compose.save", "messagesDelete",
                                   "messagesMove", "messagesModify", "<all_urls>"])
def test_gegenprobe_ein_weiteres_recht_faellt_auf(recht):
    manifest = json.loads((ADDON / "manifest.json").read_text(encoding="utf-8"))
    assert fremde_rechte(manifest) == []
    manifest["permissions"].append(recht)
    assert fremde_rechte(manifest) == [recht]


def test_das_experiment_bietet_genau_vier_funktionen():
    (schema,) = json.loads((ADDON / "schema.json").read_text(encoding="utf-8"))
    assert {f["name"] for f in schema["functions"]} == {"starten", "tagebuch", "kennung",
                                                         "fragen"}


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
