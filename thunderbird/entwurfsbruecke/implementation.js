/* falzmarke Entwurfsbrücke
 *
 * Öffnet einen Entwurf aus dem Entwurfsordner eines Kontos so, wie es
 * „Entwurf bearbeiten“ tut: als Verfassen-Fenster vom Typ Draft, dessen
 * draftId auf die Nachricht im Ordner zeigt. Beim Senden räumt Thunderbird
 * diesen Entwurf dann selbst weg. Eine .eml-Datei mit X-Unsent dagegen
 * öffnet nur eine Kopie, und der Entwurf bliebe nach dem Senden liegen.
 *
 * Der Zuruf kommt über einen Port, der nur auf 127.0.0.1 lauscht. Eine
 * Anfrage ist genau eine Zeile JSON, die Antwort auch, beides ASCII.
 * Eine Zeile, die nicht mit „{“ beginnt, wird abgewiesen: So kann ein
 * Browser, der eine Webseite an localhost schicken lässt, nichts auslösen,
 * denn seine erste Zeile ist immer „GET …“ oder „POST …“.
 *
 * Senden kann die Brücke nicht. Über den Port gibt es nur „ping“,
 * „entwurf_oeffnen“, „fenster“ und „protokoll“. Dem Hintergrund (background.js)
 * gibt sie drei Dinge, die eine MailExtension allein nicht kann: einen Eintrag
 * ins Tagebuch im Profilordner schreiben, die UID eines Entwurfs nennen und
 * vor dem Senden nachfragen (ADR 0053). Anhalten kann sie das Senden, auslösen nie.
 */
"use strict";

var { ExtensionCommon } = ChromeUtils.importESModule(
  "resource://gre/modules/ExtensionCommon.sys.mjs"
);
var { MailServices } = ChromeUtils.importESModule(
  "resource:///modules/MailServices.sys.mjs"
);
var { MailUtils } = ChromeUtils.importESModule(
  "resource:///modules/MailUtils.sys.mjs"
);
var { NetUtil } = ChromeUtils.importESModule(
  "resource://gre/modules/NetUtil.sys.mjs"
);
var { setTimeout } = ChromeUtils.importESModule(
  "resource://gre/modules/Timer.sys.mjs"
);

const STANDARD_PORT = 1994;
const PREF_PORT = "falzmarke.entwurfsbruecke.port";
const MAX_ZEILE = 4096;
// So lange darf das Nachladen des Entwurfsordners dauern, bevor die Brücke
// es ohne lokalen Kopf versucht.
const FRIST_ORDNER_MS = 15000;
// So lange wartet die Brücke auf das neue Verfassen-Fenster.
const FRIST_FENSTER_MS = 20000;
// So lange bleibt eine Verbindung nach der Antwort offen, damit der Kopierer
// des Transports die Antwort sicher ausliefert, auch wenn der Aufrufer nicht
// selbst schließt.
const NACHLAUF_MS = 3000;
const PROTOKOLL_MAX = 60;
// Liegt im Profilordner, damit `falzmarke status` es auch bei geschlossenem
// Thunderbird lesen kann. Eine Zeile JSON je Ereignis.
const TAGEBUCH_DATEI = "entwurfsbruecke-tagebuch.jsonl";

let dienst = null;
// Einträge nacheinander schreiben, sonst verschränken sich zwei Zeilen.
let schreibkette = Promise.resolve();
// Offene Verbindungen festhalten, sonst räumt der Garbage Collector sie weg.
const verbindungen = new Set();
const protokoll = [];

function notiere(was, angaben = {}) {
  protokoll.push({ zeit: new Date().toISOString(), was, ...angaben });
  while (protokoll.length > PROTOKOLL_MAX) {
    protokoll.shift();
  }
}

function ascii(antwort) {
  return (
    JSON.stringify(antwort).replace(
      /[\u007f-\uffff]/g,
      (z) => "\\u" + z.charCodeAt(0).toString(16).padStart(4, "0")
    ) + "\n"
  );
}

function warten(pruefen, frist) {
  const ende = Date.now() + frist;
  return new Promise((fertig) => {
    const runde = () => {
      let wert = null;
      try {
        wert = pruefen();
      } catch (e) {
        wert = null;
      }
      if (wert) {
        fertig(wert);
      } else if (Date.now() >= ende) {
        fertig(null);
      } else {
        setTimeout(runde, 250);
      }
    };
    runde();
  });
}

function identitaet(konto) {
  const ziel = String(konto || "").trim().toLowerCase();
  if (!ziel) {
    return null;
  }
  for (const id of MailServices.accounts.allIdentities) {
    if ((id.email || "").toLowerCase() === ziel) {
      return id;
    }
  }
  return null;
}

function lokalerKopf(ordner, schluessel) {
  try {
    const db = ordner.msgDatabase;
    if (db && db.containsKey(schluessel)) {
      return db.getMsgHdrForKey(schluessel);
    }
  } catch (e) {
    // Ohne Datenbank gibt es keinen lokalen Kopf; das ist kein Fehler.
  }
  return null;
}

function ohneAnfrage(uri) {
  return String(uri || "").split("?")[0];
}

function verfassenFenster() {
  return [...Services.wm.getEnumerator("msgcompose")];
}

function fensterStand(fenster) {
  const felder = fenster.gMsgCompose?.compFields;
  return {
    titel: fenster.document?.title || "",
    betreff: felder?.subject || "",
    draft_id: felder?.draftId || "",
    original: fenster.gMsgCompose?.originalMsgURI || "",
  };
}

function vorholen(fenster) {
  try {
    Cc["@mozilla.org/widget/macdocksupport;1"]
      .getService(Ci.nsIMacDockSupport)
      .activateApplication(true);
  } catch (e) {
    // Nur auf macOS vorhanden.
  }
  try {
    fenster.focus();
  } catch (e) {
    // Das Fenster ist schon wieder zu.
  }
}

async function entwurfOeffnen(anfrage) {
  const id = identitaet(anfrage.konto);
  if (!id) {
    return { ok: false, fehler: "konto_fehlt", konto: String(anfrage.konto || "") };
  }
  const uid = Number(anfrage.uid);
  if (!Number.isInteger(uid) || uid <= 0 || uid > 0xffffffff) {
    return { ok: false, fehler: "uid_ungueltig" };
  }
  const ordnerUri = id.draftsFolderURI;
  const ordner = ordnerUri
    ? MailServices.folderLookup.getFolderForURL(ordnerUri)
    : null;
  if (!ordner) {
    return { ok: false, fehler: "entwurfsordner_fehlt", ordner: ordnerUri || "" };
  }

  // Ist der Kopf nicht in der lokalen Datenbank, den Ordner einmal nachladen.
  // Danach läuft alles wie beim Doppelklick in der Liste.
  let kopf = lokalerKopf(ordner, uid);
  let nachgeladen = false;
  if (!kopf) {
    try {
      await Promise.race([
        MailUtils.updateFolderAsync(ordner),
        new Promise((fertig) => setTimeout(fertig, FRIST_ORDNER_MS)),
      ]);
      nachgeladen = true;
    } catch (e) {
      nachgeladen = false;
      notiere("nachladen_fehlgeschlagen", { fehler: String(e) });
    }
    kopf = lokalerKopf(ordner, uid);
  }
  notiere("entwurf", { konto: id.email, uid, kopf_lokal: Boolean(kopf), nachgeladen });

  const nachricht = ordner.generateMessageURI(uid);

  for (const fenster of verfassenFenster()) {
    const offen = fenster.gMsgCompose?.compFields?.draftId;
    if (offen && ohneAnfrage(offen) === nachricht) {
      vorholen(fenster);
      return {
        ok: true,
        zustand: "schon_offen",
        betreff: fenster.gMsgCompose.compFields.subject || "",
        nachricht,
      };
    }
  }

  const vorher = new Set(verfassenFenster());
  const hauptfenster = Services.wm.getMostRecentWindow("mail:3pane");
  try {
    MailServices.compose.OpenComposeWindow(
      null,
      kopf,
      nachricht,
      Ci.nsIMsgCompType.Draft,
      Ci.nsIMsgCompFormat.Default,
      id,
      null,
      hauptfenster?.msgWindow ?? null
    );
  } catch (e) {
    notiere("oeffnen_fehlgeschlagen", { nachricht, fehler: String(e) });
    return { ok: false, fehler: "oeffnen_fehlgeschlagen", meldung: String(e), nachricht };
  }

  const fenster = await warten(
    () => verfassenFenster().find((f) => !vorher.has(f)) || null,
    FRIST_FENSTER_MS
  );
  if (!fenster) {
    notiere("kein_neues_fenster", { nachricht, offen: verfassenFenster().map(fensterStand) });
    return {
      ok: true,
      zustand: "ungewiss",
      kopf_lokal: Boolean(kopf),
      nachgeladen,
      nachricht,
    };
  }
  const felder = await warten(
    () => (fenster.gMsgCompose?.compFields?.draftId ? fenster.gMsgCompose.compFields : null),
    FRIST_FENSTER_MS
  );
  vorholen(fenster);
  notiere(felder ? "geoeffnet" : "fenster_ohne_entwurf", { nachricht, ...fensterStand(fenster) });
  return {
    ok: true,
    zustand: felder ? "geoeffnet" : "fenster_ohne_entwurf",
    betreff: felder ? felder.subject || "" : "",
    draft_id: felder ? felder.draftId : "",
    kopf_lokal: Boolean(kopf),
    nachgeladen,
    nachricht,
  };
}

async function beantworten(zeile) {
  if (zeile === null) {
    return { ok: false, fehler: "zeile_zu_lang" };
  }
  if (!zeile.startsWith("{")) {
    return { ok: false, fehler: "kein_json" };
  }
  let anfrage;
  try {
    anfrage = JSON.parse(zeile);
  } catch (e) {
    return { ok: false, fehler: "kein_json" };
  }
  if (anfrage === null || typeof anfrage !== "object") {
    return { ok: false, fehler: "kein_json" };
  }
  switch (anfrage.befehl) {
    case "ping":
      return {
        ok: true,
        name: "entwurfsbruecke",
        version: dienst ? dienst.version : "",
        thunderbird: Services.appinfo.version,
      };
    case "entwurf_oeffnen":
      return entwurfOeffnen(anfrage);
    case "fenster":
      return { ok: true, fenster: verfassenFenster().map(fensterStand) };
    case "protokoll":
      return { ok: true, protokoll };
    default:
      return { ok: false, fehler: "befehl_unbekannt" };
  }
}

function annehmen(transport) {
  const eingang = transport.openInputStream(0, 0, 0);
  const ausgang = transport.openOutputStream(Ci.nsITransport.OPEN_BLOCKING, 0, 0);
  const verbindung = { transport };
  verbindungen.add(verbindung);
  let puffer = "";
  let fertig = false;
  let zu = false;
  const trennen = () => {
    if (zu) {
      return;
    }
    zu = true;
    try {
      transport.close(Cr.NS_OK);
    } catch (e) {}
    verbindungen.delete(verbindung);
  };
  // Erst den Ausgang schließen: Der Transport puffert über eine Pipe, und
  // ein sofortiges transport.close() verwirft, was noch nicht kopiert ist.
  // Den Transport trennt der Aufrufer mit seinem Schließen oder der Nachlauf.
  const schliessen = () => {
    try {
      ausgang.close();
    } catch (e) {
      notiere("ausgang_schliessen", { fehler: String(e) });
    }
    setTimeout(trennen, NACHLAUF_MS);
  };
  const pumpe = Cc["@mozilla.org/network/input-stream-pump;1"].createInstance(
    Ci.nsIInputStreamPump
  );
  pumpe.init(eingang, 0, 0, true);
  pumpe.asyncRead({
    onStartRequest() {},
    onDataAvailable(_anfrage, strom, _versatz, anzahl) {
      const stueck = NetUtil.readInputStreamToString(strom, anzahl);
      if (fertig) {
        return;
      }
      puffer += stueck;
      const ende = puffer.indexOf("\n");
      if (ende < 0 && puffer.length <= MAX_ZEILE) {
        return;
      }
      fertig = true;
      const zeile =
        ende < 0 || ende > MAX_ZEILE ? null : puffer.slice(0, ende).replace(/\r$/, "");
      beantworten(zeile)
        .catch((e) => ({ ok: false, fehler: "intern", meldung: String(e) }))
        .then((antwort) => {
          const text = ascii(antwort);
          try {
            ausgang.write(text, text.length);
          } catch (e) {
            notiere("schreiben_fehlgeschlagen", { fehler: String(e) });
          }
          schliessen();
        });
    },
    onStopRequest() {
      if (fertig) {
        // Der Aufrufer hat geschlossen; er schließt erst nach der ganzen
        // Antwortzeile, oder er wartet gar nicht mehr.
        trennen();
      } else {
        schliessen();
      }
    },
  });
}

function starten(version) {
  if (dienst) {
    return { laeuft: true, port: dienst.port };
  }
  const port = Services.prefs.getIntPref(PREF_PORT, STANDARD_PORT);
  const server = Cc["@mozilla.org/network/server-socket;1"].createInstance(
    Ci.nsIServerSocket
  );
  try {
    // true = nur 127.0.0.1, nie von außen erreichbar.
    server.init(port, true, -1);
  } catch (e) {
    return { laeuft: false, port, fehler: String(e) };
  }
  server.asyncListen({
    onSocketAccepted(_server, transport) {
      annehmen(transport);
    },
    onStopListening() {},
  });
  dienst = { server, port, version };
  return { laeuft: true, port };
}

function stoppen() {
  if (dienst) {
    try {
      dienst.server.close();
    } catch (e) {}
    dienst = null;
  }
}

function insTagebuch(version, eintrag) {
  const zeile =
    JSON.stringify({ ...eintrag, zeit: new Date().toISOString(), version }) + "\n";
  const pfad = PathUtils.join(PathUtils.profileDir, TAGEBUCH_DATEI);
  const schritt = schreibkette.then(() =>
    IOUtils.writeUTF8(pfad, zeile, { mode: "appendOrCreate" })
  );
  // Die Kette läuft weiter, auch wenn ein Eintrag scheitert.
  schreibkette = schritt.catch(() => {});
  return schritt.then(
    () => true,
    (e) => {
      notiere("tagebuch_fehlgeschlagen", { fehler: String(e) });
      return false;
    }
  );
}

// Die UID eines Entwurfs auf dem IMAP-Server: Bei IMAP-Ordnern ist der
// messageKey die UID. Ohne Kopf gibt es keine.
function kennung(context, nachrichtId) {
  try {
    const kopf = context.extension.messageManager.get(nachrichtId);
    return kopf ? kopf.messageKey : null;
  } catch (e) {
    return null;
  }
}

// Fragt vor dem Senden nach. Knopf 1 („Nicht senden“) ist vorgewählt, und
// Escape oder das Schließen des Dialogs zählen ebenfalls als Knopf 1:
// Nur ein Klick auf „Trotzdem senden“ lässt die Mail hinaus.
function fragen(context, tabId, titel, text) {
  let fenster = null;
  try {
    fenster = context.extension.tabManager.get(tabId).nativeTab;
  } catch (e) {
    fenster = null;
  }
  fenster = fenster || Services.wm.getMostRecentWindow("msgcompose");
  const P = Ci.nsIPromptService;
  const knoepfe =
    P.BUTTON_POS_0 * P.BUTTON_TITLE_IS_STRING +
    P.BUTTON_POS_1 * P.BUTTON_TITLE_IS_STRING +
    P.BUTTON_POS_1_DEFAULT;
  const wahl = Services.prompt.confirmEx(
    fenster,
    titel,
    text,
    knoepfe,
    "Trotzdem senden",
    "Nicht senden",
    null,
    null,
    {}
  );
  notiere("sperre", { titel, wahl });
  return wahl === 0;
}

var entwurfsbruecke = class extends ExtensionCommon.ExtensionAPI {
  onShutdown(isAppShutdown) {
    stoppen();
    if (!isAppShutdown) {
      // Sonst lädt Thunderbird nach einem Update die alte Fassung aus dem Cache.
      Services.obs.notifyObservers(null, "startupcache-invalidate");
    }
  }

  getAPI(context) {
    const version = context.extension.version;
    return {
      entwurfsbruecke: {
        async starten() {
          return starten(version);
        },
        async tagebuch(eintrag) {
          return insTagebuch(version, eintrag);
        },
        async kennung(nachrichtId) {
          return kennung(context, nachrichtId);
        },
        async fragen(tabId, titel, text) {
          return fragen(context, tabId, titel, text);
        },
      },
    };
  }
};
