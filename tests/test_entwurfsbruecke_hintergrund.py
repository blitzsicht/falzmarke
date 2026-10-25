"""Sperre und Tagebuch des Add-ons (ADR 0055), in node gegen ein nachgebautes Thunderbird.

`background.js` sieht nur die MailExtension-API: Verfassen-Fenster, gesendete
Mails, das Experiment. Hier steht an ihrer Stelle eine Attrappe, die aufzeichnet,
was das Add-on ins Tagebuch schreibt und wann es fragt. So lässt sich prüfen,
dass die Sperre hält, wo sie halten soll, schweigt, wo nicht, und bei einem
Fehler senden lässt statt aufzuhalten — ohne Thunderbird.

Was die Attrappe nicht beweist: dass Thunderbird die API so liefert. Das zeigt
erst die Probe am echten Thunderbird mit einem Entwurf an die eigene Adresse.
"""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timedelta, timezone

import pytest
from conftest import REPO
from falzmarke import entwurfsbuch
from test_vergleich_js import _node

ADDON = REPO / "thunderbird" / "entwurfsbruecke"
HINTERGRUND = ADDON / "background.js"

LAEUFER = r"""
const fs = require("fs");
const vm = require("vm");
const eingabe = JSON.parse(fs.readFileSync(0, "utf8"));
const fall = eingabe.fall;
globalThis.FalzmarkeVergleich = require(eingabe.vergleich);
globalThis.setTimeout = (f) => { f(); return 0; };
console.log = (...teile) => console.error(...teile);
const hoerer = {};
const tagebuch = [];
const fragen = [];
const abfragen = [];
const ereignis = (name) => ({ addListener(f) { hoerer[name] = f; } });
const gesendet = fall.gesendet.map((m, i) => ({ id: 1000 + i, ...m, date: new Date(m.date) }));
globalThis.browser = {
  entwurfsbruecke: {
    starten: async () => ({ laeuft: true }),
    tagebuch: async (e) => { tagebuch.push(JSON.parse(JSON.stringify(e))); return true; },
    kennung: async (id) => (fall.kennung && id in fall.kennung ? fall.kennung[id] : null),
    fragen: async (tabId, titel, text) => {
      fragen.push({ tabId, titel, text });
      if (fall.fragen_wirft) { throw new Error("kein Fenster"); }
      return fall.trotzdem;
    },
    fassungen: async () => {
      if (fall.fassungen_wirft) { throw new Error("Tagebuch nicht lesbar"); }
      return fall.fassungen || [];
    },
  },
  compose: {
    getComposeDetails: async () => fall.details,
    listAttachments: async () => {
      if (fall.anhaenge_wirft) { throw new Error("keine Anhangliste"); }
      return (fall.anhaenge || []).map((name, i) => ({ id: i + 1, name }));
    },
    onBeforeSend: ereignis("vorSenden"),
    onAfterSend: ereignis("nachSenden"),
    onAfterSave: ereignis("nachSpeichern"),
  },
  messages: {
    getFull: async (id) => {
      if (id === fall.details.relatedMessageId) { return fall.entwurf_voll; }
      return gesendet.find((m) => m.id === id).voll;
    },
    query: async (q) => {
      abfragen.push({ folderId: q.folderId, fromDate: q.fromDate.toISOString() });
      return { id: null, messages: gesendet.filter((m) => m.date >= q.fromDate) };
    },
    continueList: async () => ({ id: null, messages: [] }),
  },
  accounts: { list: async () => [{ id: "account5", name: "order", identities: [{ id: "id5" }] }] },
  folders: {
    query: async (q) => (fall.ohne_gesendet ? [] : [{ id: "sent5", accountId: q.accountId }]),
  },
  tabs: { onCreated: ereignis("neu"), onRemoved: ereignis("zu"), query: async () => [] },
};
vm.runInThisContext(fs.readFileSync(eingabe.hintergrund, "utf8"), { filename: "background.js" });
const ruhe = async () => {
  for (let i = 0; i < 20; i++) { await new Promise((r) => setImmediate(r)); }
};
(async () => {
  const tab = { id: 7, type: "messageCompose" };
  hoerer.neu(tab);
  let ergebnis = null;
  if (!fall.ohne_senden) {
    ergebnis = await hoerer.vorSenden(tab, fall.details);
    if (ergebnis && ergebnis.cancel) {
      // So meldet Thunderbird ein angehaltenes Senden (gemessen 25.10.2026).
      await hoerer.nachSenden(tab, { mode: "sendNow",
                                     error: "Send aborted by an onBeforeSend event" });
    } else if (fall.nach_senden) {
      await hoerer.nachSenden(tab, fall.nach_senden);
    }
  }
  if (fall.speichern) { await hoerer.nachSpeichern(tab, fall.speichern); }
  hoerer.zu(tab.id);
  await ruhe();
  process.stdout.write(JSON.stringify({ ergebnis, tagebuch, fragen, abfragen }));
})().catch((e) => { console.error(e && e.stack || e); process.exit(3); });
"""

JETZT = datetime.now(timezone.utc)
AN = "Erika <erika@example.com>"
TEXT = ("Hallo Erika,\n\nbitte die Stickdatei für S1 in Gold anlegen, alle Formate neu, "
        "und das Farbblatt auch in Gold.\n\nViele Grüße\nPaul\n")


def _voll(text, *, html=False, anhang=False):
    teile = []
    if anhang:
        teile.append({"contentType": "text/plain", "body": "ganz anderer Anhang",
                      "headers": {"content-disposition": ["attachment; filename=a.txt"]}})
    art = "text/html" if html else "text/plain"
    teile.append({"contentType": art, "body": text, "headers": {}})
    return {"contentType": "multipart/mixed", "headers": {}, "parts": teile}


def _gesendet(*, text=TEXT, an=("erika@example.com",), betreff="Auftrag S1", vor=timedelta(days=2),
              html=False, anhang=False, message_id="m1@example.de"):
    return {"recipients": list(an), "ccList": [], "bccList": [], "subject": betreff,
            "date": (JETZT - vor).isoformat(), "voll": _voll(text, html=html, anhang=anhang),
            "headerMessageId": message_id}


def _fall(*gesendet, typ="draft", text=TEXT, betreff="Auftrag S1", **mehr):
    fall = {
        "details": {"type": typ, "from": "Paul <order@example.de>", "to": [AN], "cc": [],
                    "bcc": [], "subject": betreff, "plainTextBody": text, "body": "",
                    "identityId": "id5", "relatedMessageId": 55},
        "entwurf_voll": {"contentType": "text/plain", "body": text,
                         "headers": {"x-falzmarke-fassung": ["abc123def456"]}},
        "kennung": {"55": 219249, "77": 219260},
        "gesendet": list(gesendet),
        "trotzdem": False,
    }
    fall.update(mehr)
    return fall


def _lauf(fall, hintergrund=HINTERGRUND) -> dict:
    eingabe = {"fall": fall, "hintergrund": str(hintergrund),
               "vergleich": str(ADDON / "vergleich.js")}
    fertig = subprocess.run([_node(), "-e", LAEUFER], input=json.dumps(eingabe),
                            capture_output=True, encoding="utf-8", timeout=60, check=False)
    assert fertig.returncode == 0, fertig.stderr
    return json.loads(fertig.stdout)


def _arten(aus) -> list[str]:
    return [e["art"] for e in aus["tagebuch"]]


# ── Die Sperre ──────────────────────────────────────────────────────────────

def test_derselbe_text_an_denselben_empfaenger_haelt_an():
    aus = _lauf(_fall(_gesendet()))
    assert aus["ergebnis"] == {"cancel": True}
    assert [f["titel"] for f in aus["fragen"]] == ["Diese Mail ging schon hinaus"]
    assert "erika@example.com" in aus["fragen"][0]["text"]
    assert _arten(aus) == ["geoeffnet", "gesperrt", "geschlossen"]
    gesperrt = aus["tagebuch"][1]
    assert gesperrt["grund"] == "gleicher_text" and gesperrt["an"] == ["erika@example.com"]
    assert gesperrt["ursprung"] == {"typ": "draft", "konto": "order@example.de",
                                    "betreff": "Auftrag S1", "uid": 219249,
                                    "fassung": "abc123def456"}


def test_trotzdem_senden_laesst_hinaus_und_steht_im_tagebuch():
    aus = _lauf(_fall(_gesendet(), trotzdem=True,
                      nach_senden={"mode": "sendNow", "headerMessageId": "<x@example.de>"}))
    assert aus["ergebnis"] == {}
    assert _arten(aus) == ["geoeffnet", "trotzdem", "gesendet"]
    assert aus["tagebuch"][-1]["message_id"] == "<x@example.de>"


def test_ein_anderer_empfaenger_wird_nicht_gefragt():
    aus = _lauf(_fall(_gesendet(an=("jemand@example.net",))))
    assert aus["ergebnis"] == {} and aus["fragen"] == []


def test_aelter_als_vierzehn_tage_zaehlt_nicht():
    aus = _lauf(_fall(_gesendet(vor=timedelta(days=20))))
    assert aus["ergebnis"] == {} and aus["fragen"] == []
    (abfrage,) = aus["abfragen"]
    seit = datetime.fromisoformat(abfrage["fromDate"].replace("Z", "+00:00"))
    assert abs((JETZT - seit) - timedelta(days=14)) < timedelta(minutes=5)
    assert abfrage["folderId"] == ["sent5"]


def test_der_text_aus_html_zaehlt_und_ein_anhang_nicht():
    html = "<p>" + TEXT.replace("\n\n", "</p><p>").replace("\n", "<br>") + "</p>"
    aus = _lauf(_fall(_gesendet(text=html, html=True, anhang=True)))
    assert aus["ergebnis"] == {"cancel": True}


def test_gleicher_betreff_anderer_text_binnen_eines_tages_fragt():
    aus = _lauf(_fall(_gesendet(text="Hallo Erika,\n\nganz andere Sache.\n",
                                vor=timedelta(hours=2))))
    assert [f["titel"] for f in aus["fragen"]] == ["Eine Mail mit diesem Betreff ging schon hinaus"]
    assert aus["tagebuch"][1]["grund"] == "gleicher_betreff"


def test_gleicher_betreff_vor_zwei_tagen_fragt_nicht():
    aus = _lauf(_fall(_gesendet(text="Hallo Erika,\n\nganz andere Sache.\n")))
    assert aus["fragen"] == []


def test_eine_antwort_mit_demselben_betreff_fragt_nicht():
    aus = _lauf(_fall(_gesendet(text="Hallo Erika,\n\nganz andere Sache.\n",
                                vor=timedelta(hours=2)), typ="reply"))
    assert aus["fragen"] == []


def test_gleicher_text_haelt_auch_bei_einer_antwort():
    aus = _lauf(_fall(_gesendet(), typ="reply"))
    assert aus["ergebnis"] == {"cancel": True}


# ── Die Fassung aus dem Tagebuch (ADR 0056) ─────────────────────────────────

GEAENDERT = "Hallo Erika,\n\nganz andere Sache, im Fenster umgeschrieben.\n"


def test_fassung_aus_dem_tagebuch_erkennt_den_geaenderten_text():
    # Die gesendete Mail trägt keine Kopfzeile (Thunderbird wirft sie weg), das
    # Tagebuch kennt ihre Fassung noch, mit Klammern um die Message-ID.
    aus = _lauf(_fall(_gesendet(text=GEAENDERT, vor=timedelta(days=3)),
                      fassungen=[{"message_id": "<m1@example.de>", "fassung": "abc123def456"}]))
    assert aus["ergebnis"] == {"cancel": True}
    assert aus["tagebuch"][1]["grund"] == "gleicher_text"


def test_gegenprobe_ohne_tagebuchtreffer_kein_gleicher_text():
    for fassungen in ([], [{"message_id": "m2@example.de", "fassung": "abc123def456"}],
                      [{"message_id": "m1@example.de", "fassung": "fremde000000"}]):
        aus = _lauf(_fall(_gesendet(text=GEAENDERT, vor=timedelta(days=3)), fassungen=fassungen))
        assert aus["ergebnis"] == {} and aus["fragen"] == []


def test_ist_das_tagebuch_nicht_lesbar_prueft_die_sperre_ueber_den_text():
    aus = _lauf(_fall(_gesendet(), fassungen_wirft=True))
    assert aus["ergebnis"] == {"cancel": True}
    assert "pruefung_fehlgeschlagen" not in _arten(aus)


# ── Scheitert die Prüfung, wird gesendet ─────────────────────────────────────

def test_ohne_gesendet_ordner_wird_gesendet_und_es_steht_im_tagebuch():
    aus = _lauf(_fall(_gesendet(), ohne_gesendet=True))
    assert aus["ergebnis"] == {} and aus["fragen"] == []
    (fehler,) = [e for e in aus["tagebuch"] if e["art"] == "pruefung_fehlgeschlagen"]
    assert "Gesendet" in fehler["fehler"]


def test_kann_der_dialog_nicht_aufgehen_wird_gesendet():
    aus = _lauf(_fall(_gesendet(), fragen_wirft=True))
    assert aus["ergebnis"] == {}
    assert "pruefung_fehlgeschlagen" in _arten(aus)


# ── Das Tagebuch ────────────────────────────────────────────────────────────

def test_ohne_senden_geschlossen():
    aus = _lauf(_fall(ohne_senden=True))
    assert _arten(aus) == ["geoeffnet", "geschlossen"]


def test_gesendet_ohne_fund():
    aus = _lauf(_fall(nach_senden={"mode": "sendNow", "headerMessageId": "<y@example.de>"}))
    assert _arten(aus) == ["geoeffnet", "gesendet"]


def _mit_empfaengern(**mehr):
    fall = _fall(nach_senden={"mode": "sendNow", "headerMessageId": "y@example.de"},
                 anhaenge=["Angebot.pdf"], **mehr)
    fall["details"]["cc"] = ["Eva <EVA@example.org>"]
    fall["details"]["bcc"] = ["dms@example.de"]
    return fall


def test_gesendet_nennt_absender_empfaenger_bcc_und_anhaenge():
    aus = _lauf(_mit_empfaengern())
    gesendet = aus["tagebuch"][-1]
    assert gesendet["art"] == "gesendet" and gesendet["message_id"] == "y@example.de"
    assert gesendet["identitaet"] == "order@example.de"
    assert gesendet["an"] == ["erika@example.com"]
    assert gesendet["kopie"] == ["eva@example.org"]
    assert gesendet["blindkopie"] == ["dms@example.de"]
    assert gesendet["anhaenge"] == ["Angebot.pdf"]


def test_gegenprobe_ohne_bcc_steht_keines_im_eintrag():
    fall = _mit_empfaengern()
    fall["details"]["bcc"] = []
    assert _lauf(fall)["tagebuch"][-1]["blindkopie"] == []


def test_scheitert_die_anhangliste_wird_trotzdem_gesendet():
    aus = _lauf(_mit_empfaengern(anhaenge_wirft=True))
    assert aus["ergebnis"] == {}
    gesendet = aus["tagebuch"][-1]
    assert gesendet["art"] == "gesendet" and "anhaenge" not in gesendet
    assert "keine Anhangliste" in gesendet["anhaenge_fehler"]
    assert gesendet["blindkopie"] == ["dms@example.de"]


def test_senden_scheitert():
    aus = _lauf(_fall(nach_senden={"mode": "sendNow", "error": "SMTP 550"}))
    assert _arten(aus) == ["geoeffnet", "senden_fehlgeschlagen", "geschlossen"]


def test_gespeichert_nennt_die_neue_uid_und_behaelt_den_ursprung():
    aus = _lauf(_fall(ohne_senden=True, speichern={"mode": "draft", "messages": [{"id": 77}]}))
    gespeichert = aus["tagebuch"][1]
    assert gespeichert["art"] == "gespeichert" and gespeichert["neu_uid"] == [219260]
    assert gespeichert["ursprung"]["uid"] == 219249


def test_python_kennt_jede_art_aus_dem_tagebuch():
    arten = set(re.findall(r'eintragen\(\s*"(\w+)"', HINTERGRUND.read_text(encoding="utf-8")))
    assert arten == set(entwurfsbuch.TAGEBUCH_WORTE)


def test_tagebuch_datei_hat_auf_beiden_seiten_denselben_namen():
    quelltext = (ADDON / "implementation.js").read_text(encoding="utf-8")
    assert f'const TAGEBUCH_DATEI = "{entwurfsbuch.TAGEBUCH}";' in quelltext


# ── Gegenproben: eine kaputte Sperre fällt auf ──────────────────────────────

@pytest.mark.parametrize(("alt", "neu", "fall"), [
    ("return { cancel: true };", "return {};", lambda: _fall(_gesendet())),
    ("const FRIST_GLEICH_MS = 14 * TAG_MS;", "const FRIST_GLEICH_MS = 40 * TAG_MS;",
     lambda: _fall(_gesendet(vor=timedelta(days=20)))),
    ('const mitBetreff = details.type === "draft" || details.type === "new";',
     "const mitBetreff = true;",
     lambda: _fall(_gesendet(text="Hallo Erika,\n\nganz andere Sache.\n",
                             vor=timedelta(hours=2)), typ="reply")),
    ('kopfwert(voll, "x-falzmarke-fassung") || bekannt.get(V.kennung(kopf.headerMessageId)) || ""',
     'kopfwert(voll, "x-falzmarke-fassung")',
     lambda: _fall(_gesendet(text=GEAENDERT, vor=timedelta(days=3)),
                   fassungen=[{"message_id": "m1@example.de", "fassung": "abc123def456"}])),
])
def test_gegenprobe(tmp_path, alt, neu, fall):
    quelltext = HINTERGRUND.read_text(encoding="utf-8")
    assert quelltext.count(alt) == 1
    kaputt = tmp_path / "background.js"
    kaputt.write_text(quelltext.replace(alt, neu), encoding="utf-8")
    # Nur, was die Sperre entscheidet: Die Abfragezeit ist in jedem Lauf eine
    # andere, mit ihr könnte die Gegenprobe nie rot werden.
    assert _urteil(_lauf(fall(), kaputt)) != _urteil(_lauf(fall()))


def test_gegenprobe_unveraendert_urteilt_gleich():
    assert _urteil(_lauf(_fall(_gesendet()))) == _urteil(_lauf(_fall(_gesendet())))


def _urteil(aus) -> tuple:
    return aus["ergebnis"], [f["titel"] for f in aus["fragen"]], _arten(aus)


def test_gegenprobe_eine_neue_art_faellt_auf():
    arten = set(re.findall(r'eintragen\(\s*"(\w+)"',
                           HINTERGRUND.read_text(encoding="utf-8") + '\neintragen("neu", 1);'))
    assert arten != set(entwurfsbuch.TAGEBUCH_WORTE)
