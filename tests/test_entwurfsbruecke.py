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
import subprocess
import zipfile

import pytest
from conftest import REPO
from falzmarke import bruecke
from test_vergleich_js import _node

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
    "emptyTrash", "deleteSelf", "saveMessage", "setComposeDetails", "SetComposeDetails",
    "CompFields2Recipients",
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
        "implementation.js", "background.js", "vergleich.js", "zeichennamen.js"}
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
    "fenster.SetComposeDetails({ to: null });",
    "fenster.CompFields2Recipients(felder);",
])
def test_gegenprobe_ein_sendender_aufruf_faellt_auf(probe):
    assert verbotene_aufrufe(ALLE_JS + "\n" + probe)


#: `onBeforeSend` darf mit `details` das Fenster ändern, wie `setComposeDetails`.
#: Das Add-on hält höchstens an (`{ cancel: true }`), es schreibt nichts zurück,
#: auch nicht die Fassungs-Kopfzeile (ADR 0056).
RUECKSCHREIBEN = re.compile(r"return\s*\{[^}]*\bdetails\b")


def test_vor_dem_senden_wird_nichts_zurueckgeschrieben():
    assert not RUECKSCHREIBEN.search(ALLE_JS)


def test_gegenprobe_ein_rueckschreiben_faellt_auf():
    probe = 'return { details: { customHeaders: [{ name: "X-Falzmarke-Fassung", value: f }] } };'
    assert RUECKSCHREIBEN.search(ALLE_JS + "\n" + probe)


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


def test_der_socket_gehoert_nur_dem_eigenen_konto():
    """Gegenprobe am 25.10.2026: Auf dem Port kam ein fremder Prozess ohne
    jedes Geheimnis an eine vollständige `ping`-Antwort. Am Socket mit 0600
    entscheiden die Dateirechte (ADR 0059)."""
    assert re.search(r"server\.initWithFilename\(\s*datei\s*,\s*SOCKET_RECHTE\s*,\s*-1\s*\)",
                     QUELLTEXT)
    assert "const SOCKET_RECHTE = 0o600;" in QUELLTEXT


def _ohne_kommentare(quelle: str) -> str:
    """Nur der Code. Geschnitten werden Blockkommentare und reine `//`-Zeilen.

    Eine Suche über den ganzen Quelltext trifft die eigene Begründung: Der
    Kommentar, der den Umzug auf den Socket erklärt, nennt `127.0.0.1:1994`
    — und ließ die Prüfung darunter am 25.10.2026 anschlagen. Nicht
    geschnitten wird ein `//` mitten in einer Zeile: Dort stehen URLs in
    Zeichenketten (`imap-message://…`), und sie wegzuschneiden hieße, Code zu
    verlieren, den die Prüfung sehen soll.
    """
    ohne = re.sub(r"/\*.*?\*/", "", quelle, flags=re.S)
    return "\n".join(z for z in ohne.splitlines() if not z.lstrip().startswith("//"))


def test_kein_teil_des_add_ons_lauscht_auf_einem_port():
    """Die Rücknahme ist erst fertig, wenn der alte Weg nirgends mehr steht."""
    code = _ohne_kommentare(ALLE_JS)
    assert len(code) < len(ALLE_JS), "der Kommentarschnitt hat nichts geschnitten"
    assert "nsIServerSocket" in code, "der Schnitt hat auch Code verloren"
    for was in ("server.init(", "127.0.0.1", "STANDARD_PORT", "PREF_PORT", "1994"):
        assert was not in code, f"„{was}“ steht noch im Code des Add-ons"


def test_eine_verbindung_ohne_daten_wird_getrennt():
    """Sonst bleibt sie für immer in `verbindungen` stehen — und mit ihr das
    Fenster, auf das sie zeigt."""
    assert "const FRIST_LEERLAUF_MS = 10000;" in QUELLTEXT
    anfang = QUELLTEXT.index("const leerlauf = setTimeout(")
    ende = QUELLTEXT.index("}, FRIST_LEERLAUF_MS);", anfang)
    assert "trennen();" in QUELLTEXT[anfang:ende], "die Frist trennt die Verbindung nicht"
    # Und wer eine vollständige Zeile schickt, wird nicht mitten im Dienst getrennt.
    assert "clearTimeout(leerlauf);" in QUELLTEXT


#: Uhr-Funktionen, die es im Experiment nicht als globale Namen gibt. Eine davon
#: ohne Import wirft erst zur Laufzeit; am 26.10.2026 brach so jede Anfrage an
#: 0.3.2 ohne Antwort ab, während alle Quelltextproben grün waren.
UHREN = ("setTimeout", "clearTimeout", "setInterval", "clearInterval")


def ungeladene_uhren(text: str) -> list[str]:
    geladen = re.search(r"var \{([^}]*)\} = ChromeUtils\.importESModule\(\s*"
                        r'"resource://gre/modules/Timer\.sys\.mjs"', text)
    namen = {n.strip() for n in geladen.group(1).split(",")} if geladen else set()
    return [u for u in UHREN if re.search(rf"\b{u}\(", text) and u not in namen]


def test_jede_gerufene_uhr_ist_importiert():
    assert ungeladene_uhren(QUELLTEXT) == []
    assert "clearTimeout(" in QUELLTEXT, "die Probe hat nichts zu prüfen"


def test_gegenprobe_eine_uhr_ohne_import_faellt_auf():
    ohne = QUELLTEXT.replace("var { clearTimeout, setTimeout }", "var { setTimeout }")
    assert ohne != QUELLTEXT
    assert ungeladene_uhren(ohne) == ["clearTimeout"]


def test_mehr_als_acht_verbindungen_nimmt_die_bruecke_nicht_an():
    """falzmarke stellt immer genau eine."""
    assert "const MAX_VERBINDUNGEN = 8;" in QUELLTEXT
    assert "verbindungen.size >= MAX_VERBINDUNGEN" in QUELLTEXT


def test_ein_altes_socket_blockiert_den_start_nicht():
    """Nach einem Abbruch liegt der Name noch da; `initWithFilename` legt sich
    nicht darüber. Beim Stoppen wird er weggeräumt."""
    assert QUELLTEXT.count("datei.remove(false);") == 2


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
    # Erst die Tabelle, dann der Vergleich, der sie braucht, dann der
    # Hintergrund, der ihn braucht (ADR 0057).
    assert manifest["background"]["scripts"] == [
        "zeichennamen.js", "vergleich.js", "background.js"]


@pytest.mark.parametrize("recht", ["compose.send", "compose.save", "messagesDelete",
                                   "messagesMove", "messagesModify", "<all_urls>"])
def test_gegenprobe_ein_weiteres_recht_faellt_auf(recht):
    manifest = json.loads((ADDON / "manifest.json").read_text(encoding="utf-8"))
    assert fremde_rechte(manifest) == []
    manifest["permissions"].append(recht)
    assert fremde_rechte(manifest) == [recht]


def test_das_experiment_bietet_genau_fuenf_funktionen():
    (schema,) = json.loads((ADDON / "schema.json").read_text(encoding="utf-8"))
    assert {f["name"] for f in schema["functions"]} == {"starten", "tagebuch", "kennung",
                                                         "fragen", "fassungen"}


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


def test_die_erzeugte_tabelle_wird_vor_dem_vergleich_geladen():
    """`vergleich.js` holt sie über `require` oder aus `globalThis` — beides.

    Im Add-on gibt es kein `require`; dort lädt das Manifest die Tabelle als
    eigenes Hintergrundskript, und sie steht als `globalThis`-Eigenschaft da.
    Im Testlauf lädt node sie über `require`. Fiele einer der beiden Wege weg,
    liefe die Prüfung in genau der Umgebung ins Leere, in der sie nicht
    gemessen wird (ADR 0057).
    """
    quelle = (ADDON / "vergleich.js").read_text(encoding="utf-8")
    assert 'require("./zeichennamen.js")' in quelle
    assert "globalThis.FalzmarkeZeichennamen" in quelle
    tabelle = (ADDON / "zeichennamen.js").read_text(encoding="utf-8")
    assert "wurzel.FalzmarkeZeichennamen = api;" in tabelle
    assert "module.exports = api;" in tabelle


# ── Die Fehlerdatei im Profil (#421) ────────────────────────────────────────
#
# Das Protokoll im Speicher ist allein über den Socket lesbar. Als der Socket
# am 26.10.2026 schwieg, stand der Grund nur in Thunderbirds Fehlerkonsole —
# der Abend ging dafür hin. Defekte gehen deshalb zusätzlich auf Platte.


def _js_funktion(quelle: str, name: str) -> str:
    """Eine Funktion aus dem Quelltext schneiden, über Klammerstände.

    Nicht über einen Ausdruck: der bliebe an der ersten Zeile mit `}` hängen
    und schnitte den halben Körper ab, ohne das zu sagen.
    """
    anfang = quelle.index(f"function {name}(")
    tiefe = 0
    for stelle in range(quelle.index("{", anfang), len(quelle)):
        if quelle[stelle] == "{":
            tiefe += 1
        elif quelle[stelle] == "}":
            tiefe -= 1
            if tiefe == 0:
                return quelle[anfang : stelle + 1]
    raise AssertionError(f"die Funktion {name} ist im Quelltext nicht geschlossen")


def _deckel_lauf(funktion: str, zeilen: list[str], max_: int) -> list[str]:
    """Den Deckel wirklich fahren, nicht im Quelltext nachlesen."""
    laeufer = (
        f"const FEHLER_MAX = {max_};\n"
        + funktion
        + "\nconst zeilen = JSON.parse(require('fs').readFileSync(0, 'utf8'));\n"
        + "let text = '';\nfor (const z of zeilen) { text = fehlerzeilen(text, z); }\n"
        + "process.stdout.write(text);\n"
    )
    fertig = subprocess.run([_node(), "-e", laeufer], input=json.dumps(zeilen),
                            capture_output=True, encoding="utf-8", timeout=60, check=False)
    assert fertig.returncode == 0, fertig.stderr
    return [z for z in fertig.stdout.split("\n") if z]


def _fehler_arten(text: str) -> set[str]:
    block = re.search(r"const FEHLER_ARTEN = new Set\(\[(.*?)\]\);", text, re.S)
    return set(re.findall(r'"(\w+)"', block.group(1))) if block else set()


def test_die_fehlerdatei_laeuft_nicht_ueber():
    """250 Zeilen hinein, 200 heraus — und die ältesten 50 sind weg."""
    max_ = int(re.search(r"const FEHLER_MAX = (\d+);", QUELLTEXT).group(1))
    assert max_ == 200
    zeilen = [f'{{"nr":{i}}}' for i in range(max_ + 50)]
    behalten = _deckel_lauf(_js_funktion(QUELLTEXT, "fehlerzeilen"), zeilen, max_)
    assert len(behalten) == max_
    assert behalten[0] == zeilen[50], "die älteste Zeile ist nicht herausgefallen"
    assert behalten[-1] == zeilen[-1], "die neueste Zeile fehlt"


def test_gegenprobe_ohne_deckel_laeuft_die_datei_ueber():
    funktion = _js_funktion(QUELLTEXT, "fehlerzeilen")
    ohne = funktion.replace("  while (zeilen.length > FEHLER_MAX) {\n    zeilen.shift();\n  }\n", "")
    assert ohne != funktion, "der Deckel steht nicht da, wo die Probe ihn sucht"
    zeilen = [f'{{"nr":{i}}}' for i in range(250)]
    assert len(_deckel_lauf(ohne, zeilen, 200)) == 250


def test_nur_defekte_gehen_auf_platte():
    """Die Datei ist ein Fehlerprotokoll, kein zweites Tagebuch."""
    arten = _fehler_arten(QUELLTEXT)
    gerufen = set(re.findall(r'notiere\("(\w+)"', QUELLTEXT))
    assert arten, "die Liste der Arten ist leer"
    assert arten <= gerufen, f"nie gemeldet: {sorted(arten - gerufen)}"
    assert "annehmen_gescheitert" in arten
    for alltag in ("entwurf", "geoeffnet", "gesperrt", "geschlossen"):
        assert alltag not in arten
    # Sonst ruft der Fehler beim Schreiben sich selbst.
    assert "fehlerdatei_gescheitert" in gerufen
    assert "fehlerdatei_gescheitert" not in arten


def test_in_die_fehlerdatei_geht_kein_mailinhalt():
    """Gebaut aus einer Positivliste. Eine Spreizung von `angaben` schriebe
    Betreff, Adressen und UID mit — die stehen in denselben Aufrufen."""
    koerper = _js_funktion(QUELLTEXT, "insFehlerdatei")
    assert "...angaben" not in koerper
    assert "for (const feld of FEHLER_FELDER)" in koerper
    felder = re.search(r"const FEHLER_FELDER = \[(.*?)\];", QUELLTEXT, re.S)
    assert set(re.findall(r'"(\w+)"', felder.group(1))) == {"fehler", "offen", "status"}


def test_gegenprobe_eine_spreizung_der_angaben_faellt_auf():
    koerper = _js_funktion(QUELLTEXT, "insFehlerdatei")
    mit = koerper.replace("const eintrag = { zeit:", "const eintrag = { ...angaben, zeit:")
    assert mit != koerper
    assert "...angaben" in mit


def test_jeder_rueckruf_des_transports_liegt_in_der_huelle():
    """0.3.1 und 0.3.2 starben in `onDataAvailable`, unsichtbar für jede Probe
    und für den Aufrufer, der nur ein EOF sah."""
    koerper = _js_funktion(QUELLTEXT, "verbindungAnnehmen")
    for ruf in ("onStartRequest", "onDataAvailable", "onStopRequest"):
        assert re.search(rf"{ruf}: sicher\(", koerper), f"{ruf} liegt nicht in der Hülle"
    assert not re.search(r"onStartRequest\(\)|onStopRequest\(\)", koerper), \
        "ein Rückruf steht noch als Methode da"
    assert 'notiere("annehmen_gescheitert"' in _js_funktion(QUELLTEXT, "annehmen"), \
        "ein Wurf beim Annehmen selbst wird nicht gemeldet"


def test_gegenprobe_ein_rueckruf_ohne_huelle_faellt_auf():
    koerper = _js_funktion(QUELLTEXT, "verbindungAnnehmen")
    ohne = koerper.replace('onStopRequest: sicher("annehmen_gescheitert", () => {',
                           "onStopRequest() {")
    assert ohne != koerper
    assert not re.search(r"onStopRequest: sicher\(", ohne)
    assert re.search(r"onStopRequest\(\)", ohne)
