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
const quelle = fs.readFileSync(eingabe.hintergrund, "utf8");
// Nur der Nachlauf nach dem Schließen (NACHLAUF_MS) wird sofort ausgelöst,
// sonst wartete jeder Fall drei Sekunden. Jede andere Uhr läuft echt: Löste
// auch die Prüffrist sofort aus, lief jede Prüfung in ihre eigene Frist, und
// die Sperre hielte nie an — gemessen am 25.10.2026, 14 Fälle auf einmal rot.
const nachlauf = Number(/const NACHLAUF_MS = (\d+);/.exec(quelle)[1]);
const echteUhr = setTimeout;
globalThis.setTimeout = (f, ms) => (ms === nachlauf ? (f(), 0) : echteUhr(f, ms));
console.log = (...teile) => console.error(...teile);
const hoerer = {};
const tagebuch = [];
const fragen = [];
const abfragen = [];
let rufe = 0;
const ereignis = (name) => ({ addListener(f) { hoerer[name] = f; } });
const gesendet = fall.gesendet.map((m, i) => ({ id: 1000 + i, ...m, date: new Date(m.date) }));
globalThis.browser = {
  entwurfsbruecke: {
    starten: async () => ({ laeuft: true }),
    tagebuch: async (e) => { tagebuch.push(JSON.parse(JSON.stringify(e))); return true; },
    // Zwei Wege zur UID (ADR 0060): `fall.kennung` ist der Kopf der Nachricht,
    // `fall.draft_id` die draftId des Fensters. Welcher Grund dabei fällt,
    // entscheidet in Thunderbird die chrome-Seite; hier steht nur, was
    // `background.js` davon sieht.
    entwurfskennung: async (id, tabId) => {
      if (fall.kennung_wirft) { throw new Error("kein Kopf"); }
      // `stumm_bis` stellt ein Fenster nach, das beim Öffnen noch nichts
      // hergibt und vor dem Senden schon: Bis zum n-ten Aufruf schweigen
      // beide Wege.
      rufe += 1;
      if (fall.stumm_bis && rufe < fall.stumm_bis) {
        return { uid: null, quelle: "", grund: "kein_draft_id",
          uid_kennung: null, uid_draft_id: null };
      }
      const kopf = fall.kennung && id in fall.kennung ? fall.kennung[id] : null;
      const fenster = fall.draft_id && tabId in fall.draft_id ? fall.draft_id[tabId] : null;
      const quelle = kopf !== null ? "kennung" : fenster !== null ? "draft_id" : "";
      const gruende = [];
      if (kopf === null) { gruende.push(id ? "kennung_null" : "kein_related"); }
      if (fenster === null) {
        gruende.push(tabId === null || tabId === undefined ? "kein_fenster" : "kein_draft_id");
      }
      return { uid: kopf !== null ? kopf : fenster, quelle,
        grund: quelle === "kennung" ? "" : gruende.join(" · "),
        uid_kennung: kopf, uid_draft_id: fenster };
    },
    fragen: async (tabId, titel, text) => {
      fragen.push({ tabId, titel, text });
      if (fall.fragen_wirft) { throw new Error("kein Fenster"); }
      return fall.trotzdem;
    },
    // Der Auszug trägt die Form des Tagebuchs. `fall.fassungen` ist die
    // Kurzform für gesendete Mails, `fall.auszug` sind Zeilen im Original —
    // die Kette (`gespeichert` → `neu_uid`) braucht sie so.
    tagebuchauszug: async () => {
      if (fall.auszug_wirft) { throw new Error("Tagebuch nicht lesbar"); }
      const kurz = (fall.fassungen || []).map((f) => ({
        art: "gesendet", zeit: new Date().toISOString(), message_id: f.message_id,
        neu_uid: null,
        ursprung: { konto: "order@example.de", uid: null, fassung: f.fassung } }));
      return [...kurz, ...(fall.auszug || [])];
    },
  },
  compose: {
    // Zwei Fenster haben zwei Ständen: Tab 8 ist das zweite (#413).
    getComposeDetails: async (tabId) =>
      (fall.zweites && tabId === 8 ? fall.zweites.details : fall.details),
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
      if (fall.zweites && id === fall.zweites.details.relatedMessageId) {
        return fall.zweites.entwurf_voll || fall.entwurf_voll;
      }
      // Eine Mail, die sich nicht lesen lässt — im Postfach kommt das vor.
      if ((fall.unlesbar || []).includes(id)) { throw new Error("Mail nicht lesbar"); }
      return gesendet.find((m) => m.id === id).voll;
    },
    query: async (q) => {
      abfragen.push({ folderId: q.folderId, fromDate: q.fromDate.toISOString() });
      // Eine Abfrage, die nie zurückkommt. Ohne Frist hielte sie das Fenster
      // für immer auf; mit Frist muss die Mail hinausgehen.
      if (fall.haengt) { await new Promise(() => {}); }
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
vm.runInThisContext(quelle, { filename: "background.js" });
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
  // Das zweite Fenster steht noch offen, während das erste gesendet hat: der
  // Ablauf aus #413. Was dort hinausging, ist im Gesendet-Ordner noch nicht
  // zu finden — `fall.gesendet` bleibt absichtlich leer.
  let zweites = null;
  if (fall.zweites) {
    const tab2 = { id: 8, type: "messageCompose" };
    hoerer.neu(tab2);
    zweites = await hoerer.vorSenden(tab2, fall.zweites.details);
    if (zweites && zweites.cancel) {
      await hoerer.nachSenden(tab2, { mode: "sendNow",
                                      error: "Send aborted by an onBeforeSend event" });
    } else if (fall.zweites.nach_senden) {
      await hoerer.nachSenden(tab2, fall.zweites.nach_senden);
    }
    hoerer.zu(tab2.id);
  }
  hoerer.zu(tab.id);
  await ruhe();
  process.stdout.write(JSON.stringify({ ergebnis, zweites, tagebuch, fragen, abfragen }));
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


def _lauf(fall, hintergrund=HINTERGRUND, *, frist_s=60) -> dict:
    fertig = _lauf_roh(fall, hintergrund, frist_s=frist_s)
    assert fertig.returncode == 0, fertig.stderr
    return json.loads(fertig.stdout)


def _lauf_roh(fall, hintergrund=HINTERGRUND, *, frist_s=60):
    """Wie `_lauf`, ohne Urteil über den Ausgang — für die Probe, die hängt."""
    eingabe = {"fall": fall, "hintergrund": str(hintergrund),
               "vergleich": str(ADDON / "vergleich.js")}
    return subprocess.run([_node(), "-e", LAEUFER], input=json.dumps(eingabe),
                          capture_output=True, encoding="utf-8", timeout=frist_s, check=False)


def _kurze_frist(wert: int = 50) -> str:
    """`background.js` mit kurzer Prüffrist — zehn Sekunden sind kein Testlauf."""
    quelle = HINTERGRUND.read_text(encoding="utf-8")
    alt = "const FRIST_PRUEFUNG_MS = 10000;"
    assert quelle.count(alt) == 1, "die Prüffrist steht nicht genau einmal in background.js"
    return quelle.replace(alt, f"const FRIST_PRUEFUNG_MS = {wert};")


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
    # Der ganze Ursprung, Feld für Feld: Beide Wege zur UID stehen drin, auch der,
    # der nichts lieferte (ADR 0060). `uid_draft_id` ist None, weil das Fenster der
    # Attrappe keine draftId hat — eine Angabe, die die Fassungen bis 0.3.6 gar
    # nicht machen konnten.
    assert gesperrt["ursprung"] == {"typ": "draft", "konto": "order@example.de",
                                    "betreff": "Auftrag S1", "uid": 219249,
                                    "fassung": "abc123def456", "uid_quelle": "kennung",
                                    "uid_grund": "", "uid_kennung": 219249,
                                    "uid_draft_id": None, "fassung_quelle": "kopf"}


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
    aus = _lauf(_fall(_gesendet(), auszug_wirft=True))
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


# ── Die eigene Blindkopie zählt nicht mit (ADR 0058) ────────────────────────
#
# Vier Profile tragen eine Archivadresse in Bcc. Stand sie in den eigenen
# Empfängern, teilte **jede** gesendete Mail eine Adresse mit **jeder** neuen,
# und der Vorfilter in `befund` lief leer. `gesendet.py` macht es umgekehrt:
# eigene Seite aus An und Cc (`mit_bcc=False`), gesendete Mail aus An, Cc und
# Bcc (`mit_bcc=True`). Beide Richtungen bekommen hier ihre Probe.

ARCHIV = "archiv@example.de"


def test_die_eigene_blindkopie_zaehlt_nicht_als_gemeinsamer_empfaenger():
    """Gleicher Text, aber nur das Archiv ist gemeinsam — kein Dialog.

    Der Text ist absichtlich derselbe: So entscheidet allein der Vorfilter.
    Zählte die eigene Bcc mit, hielte die Sperre hier an.
    """
    fall = _fall(_gesendet(an=("alt@example.com",)), typ="new")
    fall["details"]["to"] = ["Neu <neu@example.com>"]
    fall["details"]["bcc"] = [ARCHIV]
    fall["gesendet"][0]["bccList"] = [ARCHIV]
    aus = _lauf(fall)
    assert aus["ergebnis"] == {}
    assert aus["fragen"] == []
    assert _arten(aus) == ["geoeffnet", "geschlossen"]


def test_eine_fremde_blindkopie_zaehlt_weiter():
    """Ging die Mail damals nur per Bcc an diesen Empfänger, gilt sie trotzdem."""
    fall = _fall(_gesendet(an=()))
    fall["gesendet"][0]["bccList"] = ["erika@example.com"]
    aus = _lauf(fall)
    assert aus["ergebnis"] == {"cancel": True}
    assert aus["tagebuch"][1]["an"] == ["erika@example.com"]


def test_die_blindkopie_steht_trotzdem_im_tagebuch():
    """Nicht verglichen heißt nicht ungemeldet (ADR 0056)."""
    fall = _fall(nach_senden={"mode": "sendNow", "headerMessageId": "z@example.de"})
    fall["details"]["bcc"] = [ARCHIV]
    aus = _lauf(fall)
    (eintrag,) = [e for e in aus["tagebuch"] if e["art"] == "gesendet"]
    assert eintrag["blindkopie"] == [ARCHIV]


# ── Eine Prüfung, die hängt, hält niemanden auf (ADR 0055, Punkt 5) ─────────

def test_eine_haengende_abfrage_laesst_die_mail_hinaus(tmp_path):
    kaputt = tmp_path / "background.js"
    kaputt.write_text(_kurze_frist(), encoding="utf-8")
    aus = _lauf(_fall(_gesendet(), haengt=True), kaputt)
    assert aus["ergebnis"] == {}, "die Mail wurde von einer hängenden Prüfung aufgehalten"
    (fehler,) = [e for e in aus["tagebuch"] if e["art"] == "pruefung_fehlgeschlagen"]
    assert "frist_abgelaufen" in fehler["fehler"]


def test_gegenprobe_ohne_frist_faellt_das_urteil_nie(tmp_path):
    """Die Probe muss anschlagen: ohne `mitFrist` gibt der Hörer nichts zurück.

    Gemessen am 25.10.2026: Der Knoten endet dabei mit 0 und **leerem** stdout —
    ein offenes Versprechen hält die Ereignisschleife nicht am Leben, also
    stirbt der Lauf, ohne je ein Urteil zu fällen. In Thunderbird entspricht
    das dem Fenster, das auf eine Antwort wartet, die nicht kommt; hier ist das
    fehlende Urteil der Beleg. Mit `mitFrist` steht an derselben Stelle `{}`.
    """
    quelle = _kurze_frist()
    alt = "await mitFrist(befund(details, eigen, tab.id), FRIST_PRUEFUNG_MS)"
    assert quelle.count(alt) == 1
    kaputt = tmp_path / "background.js"
    kaputt.write_text(quelle.replace(alt, "await befund(details, eigen, tab.id)"),
                      encoding="utf-8")
    fertig = _lauf_roh(_fall(_gesendet(), haengt=True), kaputt, frist_s=20)
    assert fertig.stdout.strip() == "", (
        "ohne Frist kam doch ein Urteil — dann belegt der Test nebenan nichts")
    # Und mit Frist, derselbe Fall, dieselbe Attrappe: ein Urteil kommt.
    heil = tmp_path / "heil.js"
    heil.write_text(quelle, encoding="utf-8")
    assert _lauf_roh(_fall(_gesendet(), haengt=True), heil, frist_s=20).stdout.strip() != ""


# ── Eine unlesbare Mail überspringt die Prüfung, bricht sie nicht ab ───────

def test_eine_unlesbare_mail_haelt_die_pruefung_nicht_auf():
    """Der Treffer liegt hinter der unlesbaren Mail und wird trotzdem gefunden."""
    aus = _lauf(_fall(_gesendet(text="egal, nicht lesbar", vor=timedelta(days=1),
                                message_id="kaputt@example.de"),
                      _gesendet(vor=timedelta(days=2)), unlesbar=[1000]))
    assert aus["ergebnis"] == {"cancel": True}
    (teil,) = [e for e in aus["tagebuch"] if e["art"] == "pruefung_teilweise"]
    assert teil["uebersprungen"] == 1


def test_gegenprobe_ohne_das_ueberspringen_bricht_die_pruefung_ab(tmp_path):
    quelle = HINTERGRUND.read_text(encoding="utf-8")
    alt = """    let voll;
    try {
      voll = await browser.messages.getFull(kopf.id);
    } catch (fehler) {
      uebersprungen += 1;
      continue;
    }"""
    assert quelle.count(alt) == 1
    kaputt = tmp_path / "background.js"
    kaputt.write_text(quelle.replace(alt, "    const voll = await browser.messages.getFull("
                                          "kopf.id);"), encoding="utf-8")
    fall = _fall(_gesendet(text="egal, nicht lesbar", vor=timedelta(days=1),
                           message_id="kaputt@example.de"),
                 _gesendet(vor=timedelta(days=2)), unlesbar=[1000])
    aus = _lauf(fall, kaputt)
    assert aus["ergebnis"] == {}, "ohne das Überspringen müsste die Prüfung abbrechen"
    assert "pruefung_fehlgeschlagen" in _arten(aus)


# ── Zwei Fenster in derselben Sitzung (#413) ────────────────────────────────

RAUS = {"mode": "sendNow", "headerMessageId": "<erste@example.de>"}


def _zweites(*, text=TEXT, betreff="Auftrag S1", an=AN, typ="draft", **mehr):
    """Das zweite Fenster. `fall.gesendet` bleibt leer: Der Gesendet-Ordner hat
    die erste Mail noch nicht, genau darum ging sie bisher ungefragt hinaus."""
    zweites = {
        "details": {"type": typ, "from": "Paul <order@example.de>", "to": [an], "cc": [],
                    "bcc": [], "subject": betreff, "plainTextBody": text, "body": "",
                    "identityId": "id5", "relatedMessageId": 77},
        # Eine eigene Fassung. Teilten beide Fenster dieselbe, entschiede schon
        # `eigen.fassung === fremd.fassung`, und der Textvergleich käme nie dran.
        "entwurf_voll": {"contentType": "text/plain", "body": text,
                         "headers": {"x-falzmarke-fassung": ["99zzz888yyy7"]}},
    }
    zweites.update(mehr)
    return zweites


def test_das_zweite_fenster_derselben_sitzung_haelt_an():
    aus = _lauf(_fall(nach_senden=RAUS, zweites=_zweites()))
    assert aus["ergebnis"] == {}, "die erste Mail geht hinaus, es gibt noch nichts zu finden"
    assert aus["zweites"] == {"cancel": True}
    assert [f["titel"] for f in aus["fragen"]] == ["Diese Mail ging schon hinaus"]
    assert aus["fragen"][0]["tabId"] == 8
    gesperrt = [e for e in aus["tagebuch"] if e["art"] == "gesperrt"]
    assert [e["grund"] for e in gesperrt] == ["gleicher_text"]
    assert gesperrt[0]["an"] == ["erika@example.com"]


def test_die_sitzung_wird_vor_dem_gesendet_ordner_gefragt():
    """Die Abnahme verlangt die Reihenfolge, nicht nur das Urteil: Das zweite
    Fenster fragt das Postfach gar nicht mehr — und hielte auch an, wenn es
    dort keinen Ordner „Gesendet“ gäbe und das Tagebuch schwiege."""
    aus = _lauf(_fall(nach_senden=RAUS, zweites=_zweites(),
                      ohne_gesendet=True, auszug_wirft=True))
    assert aus["zweites"] == {"cancel": True}
    assert aus["abfragen"] == [], "ohne Ordner kommt keine Abfrage zustande"
    # Die ganze Kette: Dem ersten Fenster scheitert die Prüfung am fehlenden
    # Ordner, es sendet trotzdem (ADR 0055, Punkt 5) — und genau diese Sendung
    # hält das zweite an, ohne Ordner und ohne Tagebuch.
    assert _arten(aus) == ["geoeffnet", "pruefung_fehlgeschlagen", "gesendet",
                           "geoeffnet", "gesperrt", "geschlossen"]


def test_das_zweite_fenster_mit_demselben_betreff_fragt_anders():
    aus = _lauf(_fall(nach_senden=RAUS,
                      zweites=_zweites(text="Hallo Erika,\n\nganz andere Sache.\n")))
    assert aus["zweites"] == {"cancel": True}
    assert [f["titel"] for f in aus["fragen"]] == ["Eine Mail mit diesem Betreff ging schon hinaus"]
    assert [e["grund"] for e in aus["tagebuch"] if e["art"] == "gesperrt"] == ["gleicher_betreff"]


def test_ein_anderer_empfaenger_in_derselben_sitzung_wird_nicht_gefragt():
    aus = _lauf(_fall(nach_senden=RAUS, zweites=_zweites(an="Udo <udo@example.net>")))
    assert aus["zweites"] == {} and aus["fragen"] == []


def test_eine_antwort_mit_demselben_betreff_fragt_auch_in_der_sitzung_nicht():
    aus = _lauf(_fall(nach_senden=RAUS,
                      zweites=_zweites(text="Hallo Erika,\n\nganz andere Sache.\n", typ="reply")))
    assert aus["zweites"] == {} and aus["fragen"] == []


def test_gescheitertes_senden_haelt_die_naechste_sendung_nicht_auf():
    """Die erste Mail ging **nicht** hinaus. Dann darf sie die zweite, gleiche
    nicht aufhalten — sonst sperrt die Sitzungsliste genau den zweiten Anlauf,
    den der Mensch nach einem Fehler braucht."""
    aus = _lauf(_fall(nach_senden={"mode": "sendNow", "error": "SMTP nicht erreichbar"},
                      zweites=_zweites(), ohne_gesendet=True))
    assert "senden_fehlgeschlagen" in _arten(aus)
    assert aus["zweites"] == {}, "die zweite Sendung wurde von einer gescheiterten aufgehalten"
    assert aus["fragen"] == []


def test_gesperrt_merkt_sich_nichts():
    """Das erste Fenster wurde angehalten, die Mail ging nie hinaus. Das zweite
    darf daran nicht hängen: Es findet den alten Gesendet-Eintrag, nicht zwei."""
    aus = _lauf(_fall(_gesendet(), zweites=_zweites()))
    assert aus["ergebnis"] == {"cancel": True} and aus["zweites"] == {"cancel": True}
    gesperrt = [e for e in aus["tagebuch"] if e["art"] == "gesperrt"]
    assert [e["grund"] for e in gesperrt] == ["gleicher_text", "gleicher_text"]
    # Beide Male war der Fund die gesendete Mail von vor zwei Tagen, nicht die
    # angehaltene von gerade: deren Zeit wäre „heute“.
    frueher = {e["frueher"][:10] for e in gesperrt}
    assert frueher == {(JETZT - timedelta(days=2)).date().isoformat()}


def test_trotzdem_gesendetes_haelt_die_naechste_sendung_an():
    """Wer „Trotzdem senden“ geklickt hat, hat gesendet. Die Mail steht noch
    nicht im Ordner, die Sitzung weiß es aber — also wird im zweiten Fenster
    noch einmal gefragt. Die Attrappe klickt beide Male durch, darum geht die
    zweite Mail hinaus; der Beleg ist die zweite Frage, nicht das Anhalten."""
    aus = _lauf(_fall(_gesendet(), trotzdem=True, nach_senden=RAUS, zweites=_zweites()))
    assert _arten(aus)[:2] == ["geoeffnet", "trotzdem"]
    assert [(f["tabId"], f["titel"]) for f in aus["fragen"]] == [
        (7, "Diese Mail ging schon hinaus"), (8, "Diese Mail ging schon hinaus")]
    assert [e["art"] for e in aus["tagebuch"] if e["art"] == "trotzdem"] == ["trotzdem"] * 2


def test_gegenprobe_ohne_die_sitzungsrunde_geht_die_zweite_mail_hinaus(tmp_path):
    """Die Probe muss anschlagen: Fällt die Runde über `hinaus` weg, ist der
    Fall wieder der aus #413 — zwei gleiche Mails, keine Rückfrage."""
    quelle = HINTERGRUND.read_text(encoding="utf-8")
    anfang = "  for (const frueher of hinaus) {"
    ende = "  const bekannt = fassungenAus(await auszug());"
    assert quelle.count(anfang) == 1 and quelle.count(ende) == 1
    schnitt = quelle[quelle.index(anfang):quelle.index(ende)]
    assert "V.vergleiche(eigen, frueher.merkmale)" in schnitt, "der Schnitt trifft die Runde nicht"
    kaputt = tmp_path / "background.js"
    kaputt.write_text(quelle.replace(schnitt, ""), encoding="utf-8")
    fall = _fall(nach_senden=RAUS, zweites=_zweites())
    aus = _lauf(fall, kaputt)
    assert aus["zweites"] == {}, "ohne die Sitzungsrunde müsste die zweite Mail hinausgehen"
    assert aus["fragen"] == []
    # Und mit der Runde, derselbe Fall, dieselbe Attrappe: die Rückfrage kommt.
    heil = tmp_path / "heil.js"
    heil.write_text(quelle, encoding="utf-8")
    assert _lauf(fall, heil)["zweites"] == {"cancel": True}


def test_die_blindkopie_der_ersten_sendung_zaehlt_in_der_sitzung_mit():
    """Die erste Mail ging per Blindkopie auch an Udo. Dieselbe Nachricht an Udo
    direkt ist dieselbe Mail an denselben Menschen, also muss die Sitzung sie
    finden — wie im Postfach, wo `bccList` sie mitliefert. Die andere Richtung
    bleibt wie in ADR 0058: Als Sender zählt die eigene Blindkopie nicht mit,
    sonst teilte jede Mail mit Archivadresse eine Adresse mit jeder anderen."""
    fall = _fall(nach_senden=RAUS, zweites=_zweites(an="Udo <udo@example.net>"))
    fall["details"]["bcc"] = ["Udo <udo@example.net>"]
    aus = _lauf(fall)
    assert aus["ergebnis"] == {}, "die erste Mail geht hinaus, es gibt nichts zu finden"
    assert aus["zweites"] == {"cancel": True}
    assert [e["an"] for e in aus["tagebuch"] if e["art"] == "gesperrt"] == [["udo@example.net"]]


# ── Der Anker der Zuordnung (#420, ADR 0060) ────────────────────────────────
#
# ANLASS: Ein von Thunderbird selbst gespeicherter Entwurf kam beim Öffnen ohne
# UID und ohne Fassung ins Tagebuch. Damit hing die Versandzeile an keinem
# Eintrag im Entwurfsbuch — `status` zeigte die Mail ohne „Ging an …“ und ohne
# BELEGT. Gemessen am 26.10.2026 an einem von 118 Fensterpaaren; weil der Fall
# selten ist, messen die Fassungen ab 0.3.7 **beide** Wege bei jedem Öffnen.

FASSUNG = "abc123def456"


def _ohne_kopfzeile(fall: dict) -> dict:
    """Wie ein Entwurf, den Thunderbird gespeichert hat: `X-Falzmarke-Fassung`
    ist beim Speichern weggefallen."""
    fall["entwurf_voll"] = {"contentType": "text/plain", "body": TEXT, "headers": {}}
    return fall


def _gespeichert_unter(alt, neu, *, konto="order@example.de", fassung=FASSUNG) -> dict:
    """Eine Zeile `gespeichert` im Tagebuch: der Entwurf `alt` liegt jetzt unter `neu`."""
    return {"art": "gespeichert", "zeit": JETZT.isoformat(), "message_id": "",
            "neu_uid": [neu], "ursprung": {"konto": konto, "uid": alt, "fassung": fassung}}


def _ursprung_von(aus, art="geoeffnet") -> dict:
    return next(e["ursprung"] for e in aus["tagebuch"] if e["art"] == art)


def test_schweigt_der_kopf_kommt_die_uid_aus_dem_fenster():
    aus = _lauf(_fall(ohne_senden=True, kennung={}, draft_id={"7": 1214}))
    ursprung = _ursprung_von(aus)
    assert (ursprung["uid"], ursprung["uid_quelle"]) == (1214, "draft_id")
    assert ursprung["uid_grund"] == "kennung_null"
    assert (ursprung["uid_kennung"], ursprung["uid_draft_id"]) == (None, 1214)


def test_beide_wege_stehen_auch_dann_im_tagebuch_wenn_der_erste_traegt():
    """Der Fall aus #420 trat in 258 Zeilen einmal auf. Stünde nur der Weg da,
    der getragen hat, belegte ein gewöhnlicher Lauf über den zweiten nichts."""
    aus = _lauf(_fall(ohne_senden=True, draft_id={"7": 219249}))
    ursprung = _ursprung_von(aus)
    assert (ursprung["uid"], ursprung["uid_quelle"]) == (219249, "kennung")
    assert (ursprung["uid_kennung"], ursprung["uid_draft_id"]) == (219249, 219249)
    assert ursprung["uid_grund"] == "", "Weg 1 hat getragen, es gibt nichts zu melden"


def test_gegenprobe_ohne_beide_wege_bleibt_die_uid_leer_und_die_mail_geht_hinaus():
    """Der Zustand aus #420, jetzt mit Grund. Und das Wichtigere: Eine Diagnose,
    die nichts findet, hält niemanden auf (ADR 0055, Punkt 5)."""
    aus = _lauf(_fall(kennung={}, nach_senden=RAUS))
    ursprung = _ursprung_von(aus)
    assert ursprung["uid"] is None and ursprung["uid_quelle"] == ""
    assert ursprung["uid_grund"] == "kennung_null · kein_draft_id"
    assert aus["ergebnis"] == {} and aus["fragen"] == []


def test_fehlt_die_related_id_steht_das_als_grund_da():
    """Die erste offene Frage aus #420 war, ob `relatedMessageId` überhaupt
    gesetzt ist. Künftig steht die Antwort im Tagebuch statt in einer Vermutung."""
    fall = _fall(ohne_senden=True, kennung={}, draft_id={"7": 1214})
    fall["details"]["relatedMessageId"] = None
    assert _ursprung_von(_lauf(fall))["uid_grund"] == "kein_related"


def test_die_uid_wird_vor_dem_senden_nachgeholt():
    """Gibt das Fenster beim Öffnen noch nichts her, zählt der Eintrag
    `gesendet`: Über ihn ordnet `status` die Mail ihrem Entwurf zu."""
    aus = _lauf(_fall(stumm_bis=2, nach_senden=RAUS))
    assert _ursprung_von(aus, "geoeffnet")["uid"] is None
    nachgeholt = _ursprung_von(aus, "gesendet")
    assert (nachgeholt["uid"], nachgeholt["uid_quelle"]) == (219249, "kennung")


def test_gegenprobe_ohne_den_zweiten_anlauf_bleibt_der_eintrag_gesendet_leer(tmp_path):
    """Die Sabotage muss genau diese Probe treffen und keine andere."""
    quelle = HINTERGRUND.read_text(encoding="utf-8")
    alt = "      await ankern(stand.ursprung, tab.id, details.relatedMessageId);"
    assert quelle.count(alt) == 1
    kaputt = tmp_path / "background.js"
    kaputt.write_text(quelle.replace(alt, ""), encoding="utf-8")
    aus = _lauf(_fall(stumm_bis=2, nach_senden=RAUS), kaputt)
    assert _ursprung_von(aus, "gesendet")["uid"] is None, (
        "ohne den zweiten Anlauf müsste der Eintrag `gesendet` ohne UID bleiben")


def test_die_fassung_kommt_aus_der_kette():
    """Thunderbird wirft `X-Falzmarke-Fassung` beim Speichern weg. Die Kette
    `gespeichert` → `neu_uid` führt zurück auf den Entwurf, den falzmarke
    angelegt hat — dort steht sie noch (#420)."""
    aus = _lauf(_ohne_kopfzeile(_fall(ohne_senden=True,
                                      auszug=[_gespeichert_unter(150, 219249)])))
    ursprung = _ursprung_von(aus)
    assert (ursprung["fassung"], ursprung["fassung_quelle"]) == (FASSUNG, "kette")


def test_am_geraet_gemessen_zeigt_kennung_aufs_buch_und_draft_id_auf_die_lebende():
    """Gerätelauf 28.10.2026: Nach zwei Speicherungen lebte im Postfach nur noch
    UID 1220, das Entwurfsbuch kannte 1218, und die Kette verband beide. Die zwei
    Wege tragen also **nicht** dieselbe Zahl, sobald Thunderbird neu angelegt hat
    — und der Vorrang auf `kennung` ist genau darum richtig: Er trifft die UID,
    unter der falzmarke ablegte, also den Eintrag, an dem `status` die Zeile
    aufhängt. Hier nachgestellt mit 219249 (Buch) gegen 219270 (lebend).

    GRENZE: Den Vorrang entscheidet `entwurfskennung` in `implementation.js`, und
    die Attrappe baut ihn nach — dieser Test deckt also, dass `ankern` die Felder
    unverfälscht ins Tagebuch trägt und die Kette greift, nicht den Vorrang selbst.
    Der ist allein am Gerät belegt (28.10.2026, UID 1218/1220); im Chrome-Kontext
    kann kein Test der Suite laufen (wie ADR 0059, Punkt 3 für den Transport)."""
    aus = _lauf(_ohne_kopfzeile(_fall(ohne_senden=True, draft_id={"7": 219270},
                                      auszug=[_gespeichert_unter(219249, 219270)])))
    ursprung = _ursprung_von(aus)
    assert ursprung["uid_kennung"] != ursprung["uid_draft_id"], "sonst prüft der Fall nichts"
    assert (ursprung["uid"], ursprung["uid_quelle"]) == (219249, "kennung")
    assert (ursprung["uid_kennung"], ursprung["uid_draft_id"]) == (219249, 219270)
    assert ursprung["fassung_quelle"] == "kette", "die Kopfzeile ist beim Speichern weg"


def test_die_kette_traegt_auch_ueber_zwei_speicherungen():
    aus = _lauf(_ohne_kopfzeile(_fall(ohne_senden=True, auszug=[
        _gespeichert_unter(150, 160),
        _gespeichert_unter(160, 219249, fassung=""),
    ])))
    assert _ursprung_von(aus)["fassung"] == FASSUNG


def test_gegenprobe_die_kette_eines_anderen_kontos_zaehlt_nicht():
    """Eine UID gilt je Ordner: Ohne den Konto-Filter käme die Fassung aus einem
    fremden Entwurf, und die Sperre verglich zwei Mails, die nichts verbindet."""
    aus = _lauf(_ohne_kopfzeile(_fall(
        ohne_senden=True,
        auszug=[_gespeichert_unter(150, 219249, konto="fremd@example.de")])))
    ursprung = _ursprung_von(aus)
    assert (ursprung["fassung"], ursprung["fassung_quelle"]) == ("", "")


def test_gegenprobe_dieselbe_uid_unter_fremdem_konto_zaehlt_nicht():
    """Der Fall, den die Kette allein nicht abfängt: Die fremde Zeile trägt
    **dieselbe** UID wie unser Entwurf — das Startglied prüft `V.kette` nicht,
    es ist ja die Frage. Ohne den Konto-Filter beim Nachschlagen käme hier die
    Fassung eines fremden Postfachs heraus, und die Sperre verglich zwei Mails,
    die nichts verbindet."""
    aus = _lauf(_ohne_kopfzeile(_fall(ohne_senden=True, auszug=[
        {"art": "geoeffnet", "zeit": JETZT.isoformat(), "message_id": "", "neu_uid": None,
         "ursprung": {"konto": "fremd@example.de", "uid": 219249, "fassung": "fremde000000"}},
    ])))
    ursprung = _ursprung_von(aus)
    assert (ursprung["fassung"], ursprung["fassung_quelle"]) == ("", "")


def test_gegenprobe_die_kopfzeile_geht_vor():
    """Liegt die Kopfzeile vor, wird das Tagebuch nicht gebraucht — und die
    Herkunft steht trotzdem da."""
    aus = _lauf(_fall(ohne_senden=True, auszug=[_gespeichert_unter(150, 219249,
                                                                  fassung="fremde000000")]))
    ursprung = _ursprung_von(aus)
    assert (ursprung["fassung"], ursprung["fassung_quelle"]) == (FASSUNG, "kopf")


# Die Mail aus dem Fenster und die gesendete teilen weder Text noch Betreff;
# allein die Fassung verbindet sie. Ohne die Kette fragt die Sperre dort nicht.
ANDERER_BETREFF = "Ganz andere Sache"


def _nur_ueber_die_fassung(**mehr) -> dict:
    return _ohne_kopfzeile(_fall(
        _gesendet(text=GEAENDERT, betreff=ANDERER_BETREFF, vor=timedelta(days=3)),
        fassungen=[{"message_id": "m1@example.de", "fassung": FASSUNG}], **mehr))


def test_die_sperre_greift_ueber_die_fassung_aus_der_kette():
    aus = _lauf(_nur_ueber_die_fassung(auszug=[_gespeichert_unter(150, 219249)]))
    assert aus["ergebnis"] == {"cancel": True}
    assert aus["tagebuch"][1]["grund"] == "gleicher_text"


def test_gegenprobe_ohne_die_kette_fragt_die_sperre_dort_nicht():
    aus = _lauf(_nur_ueber_die_fassung())
    assert aus["ergebnis"] == {} and aus["fragen"] == []


def test_gespeichert_nimmt_das_fenster_nur_bei_einer_nachricht():
    """Die `draftId` des Fensters zeigt auf genau einen Entwurf. Bei mehreren
    gespeicherten Nachrichten wäre nicht zu sagen, auf welchen — dann bleibt
    nur der Kopf."""
    fall = _fall(ohne_senden=True, kennung={},
                 draft_id={"7": 1214},
                 speichern={"mode": "draft", "messages": [{"id": 77}, {"id": 78}]})
    gespeichert = next(e for e in _lauf(fall)["tagebuch"] if e["art"] == "gespeichert")
    assert gespeichert["neu_uid"] == [None, None], (
        "ohne Kopf und ohne eindeutiges Fenster gibt es keine neue UID")
