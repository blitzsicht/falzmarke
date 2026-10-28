/* falzmarke Entwurfsbrücke
 *
 * Öffnet einen Entwurf aus dem Entwurfsordner eines Kontos so, wie es
 * „Entwurf bearbeiten“ tut: als Verfassen-Fenster vom Typ Draft, dessen
 * draftId auf die Nachricht im Ordner zeigt. Beim Senden räumt Thunderbird
 * diesen Entwurf dann selbst weg. Eine .eml-Datei mit X-Unsent dagegen
 * öffnet nur eine Kopie, und der Entwurf bliebe nach dem Senden liegen.
 *
 * Der Zuruf kommt über einen Unix-Socket im Profilordner, Rechte 0600 — nur
 * das Konto, das Thunderbird fährt, kommt daran (ADR 0059). Eine Anfrage ist
 * genau eine Zeile JSON, die Antwort auch, beides ASCII. Eine Zeile, die
 * nicht mit „{“ beginnt, wird abgewiesen.
 *
 * Senden kann die Brücke nicht. Über den Socket gibt es nur „ping“,
 * „entwurf_oeffnen“, „fenster“ und „protokoll“. „fenster“ meldet je offenem
 * Verfassen-Fenster, was es jetzt hinausschicken würde (ADR 0056). Dem
 * Hintergrund (background.js) gibt sie vier Dinge, die eine MailExtension
 * allein nicht kann: einen Eintrag ins Tagebuch im Profilordner schreiben, die
 * Fassungen gesendeter Mails daraus lesen, die UID eines Entwurfs nennen und
 * vor dem Senden nachfragen (ADR 0055). Anhalten kann sie das Senden, auslösen nie.
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
var { MsgUtils } = ChromeUtils.importESModule(
  "resource:///modules/MimeMessageUtils.sys.mjs"
);
var { NetUtil } = ChromeUtils.importESModule(
  "resource://gre/modules/NetUtil.sys.mjs"
);
var parserUtils = Cc["@mozilla.org/parserutils;1"].getService(Ci.nsIParserUtils);
// Im Experiment gibt es keine Uhr-Funktionen als globale Namen. Jede, die der
// Code ruft, muss hier stehen: 0.3.1 und 0.3.2 riefen clearTimeout ohne Import
// und brachen jede Anfrage ohne Antwort ab (gemessen 26.10.2026).
var { clearTimeout, setTimeout } = ChromeUtils.importESModule(
  "resource://gre/modules/Timer.sys.mjs"
);

// Der Zuruf kommt über einen Unix-Socket im Profilordner, nicht mehr über
// 127.0.0.1:1994 (ADR 0059). Zwei Gründe, beide gemessen: Ein Port auf
// 127.0.0.1 nimmt jeden Prozess *jedes* Benutzers an — ein fremder `ping`
// bekam am 25.10.2026 eine vollständige Antwort —, und wer zuerst lauscht,
// besitzt den Port, also kann ein fremder Dienst sich als Brücke ausgeben.
// Beim Socket entscheiden die Dateirechte, und die gelten für das Konto, das
// Thunderbird fährt. Der Name ist kurz, weil `sun_path` auf macOS nur 104
// Byte fasst: Gemessen am 25.10.2026 ist der Profilordner dieses Rechners
// 74 Byte lang — mit `falzmarke-entwurfsbruecke.sock` wären es 105 Byte
// gewesen, eins zu viel. Mit diesem Namen sind es 87.
const SOCKET_DATEI = "bruecke.sock";
const SOCKET_RECHTE = 0o600;
// So lange darf eine Verbindung ohne vollständige Zeile offen bleiben. Ohne
// diese Frist blieb eine Verbindung, die nichts schickt, für immer in
// `verbindungen` stehen.
const FRIST_LEERLAUF_MS = 10000;
// Mehr gleichzeitige Verbindungen nimmt die Brücke nicht an; falzmarke stellt
// immer genau eine.
const MAX_VERBINDUNGEN = 8;
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
// So viel Text je Fenster meldet `fenster`. Eine Mail, die länger ist, wird
// gekürzt gemeldet (`text_gekuerzt`), nicht gar nicht.
const MAX_TEXT = 20000;
// So weit zurück liest `fassungen` das Tagebuch, wie die Sperre zurücksieht.
const FASSUNGEN_TAGE = 14;
// Liegt im Profilordner, damit `falzmarke status` es auch bei geschlossenem
// Thunderbird lesen kann. Eine Zeile JSON je Ereignis.
const TAGEBUCH_DATEI = "entwurfsbruecke-tagebuch.jsonl";
// Liegt neben dem Tagebuch, weil es etwas anderes führt: das Tagebuch, was mit
// einer Mail geschah, diese Datei nur, was am Add-on selbst schiefging. Sie muss
// auf Platte, denn `protokoll` steht im Speicher und ist allein über den Socket
// lesbar — also über genau den Kanal, der im Fehlerfall ausfällt (#421).
const FEHLER_DATEI = "entwurfsbruecke-fehler.jsonl";
// Mehr Zeilen behält die Datei nicht; die älteste fällt heraus.
const FEHLER_MAX = 200;
// Nur diese Arten bedeuten, dass eine Anfrage nicht beantwortet wurde. Die
// normalen Vorgänge bleiben im Speicher: die Datei ist ein Fehlerprotokoll,
// kein zweites Tagebuch. „fehlerdatei_gescheitert“ steht bewusst nicht hier —
// sonst riefe der Fehler beim Schreiben sich selbst.
const FEHLER_ARTEN = new Set([
  "altes_socket",
  "annehmen_gescheitert",
  "antwort_gescheitert",
  "ausgang_schliessen",
  "leerlauf",
  "schreiben_fehlgeschlagen",
  "tagebuch_fehlgeschlagen",
  "zu_viele_verbindungen",
]);
// Mehr als diese Felder geht nie hinein: keine Betreffe, keine Adressen, keine
// UIDs, kein Mailtext. Eine Positivliste, keine Streichliste — damit ein neues
// Feld in `notiere` nicht aus Versehen auf Platte landet.
const FEHLER_FELDER = ["fehler", "offen", "status"];

let dienst = null;
// Steht hier und nicht nur in `dienst`, weil `starten()` schon vor dem Dienst
// protokolliert (altes_socket) und jede Fehlerzeile ihre Fassung tragen soll.
let fassung = null;
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
  if (FEHLER_ARTEN.has(was)) {
    insFehlerdatei(was, angaben);
  }
}

// Rein und ohne Platte, damit der Deckel gemessen werden kann und nicht nur
// behauptet ist: Text und neue Zeile hinein, gedeckelter Text hinaus.
function fehlerzeilen(alt, zeile) {
  const zeilen = String(alt || "")
    .split("\n")
    .filter((z) => z.length > 0);
  zeilen.push(zeile);
  while (zeilen.length > FEHLER_MAX) {
    zeilen.shift();
  }
  return zeilen.join("\n") + "\n";
}

function insFehlerdatei(was, angaben) {
  const eintrag = { zeit: new Date().toISOString(), was, version: fassung };
  for (const feld of FEHLER_FELDER) {
    if (angaben[feld] !== undefined) {
      eintrag[feld] = String(angaben[feld]);
    }
  }
  const zeile = JSON.stringify(eintrag);
  const pfad = PathUtils.join(PathUtils.profileDir, FEHLER_DATEI);
  // Über dieselbe Kette wie das Tagebuch: Lesen, Ändern und Schreiben darf sich
  // mit keinem anderen Schreiber verschränken, sonst verliert der Deckel Zeilen.
  const schritt = schreibkette.then(async () => {
    let alt = "";
    try {
      alt = await IOUtils.readUTF8(pfad);
    } catch (e) {
      // Beim ersten Fehler gibt es die Datei noch nicht.
      alt = "";
    }
    await IOUtils.writeUTF8(pfad, fehlerzeilen(alt, zeile));
  });
  schreibkette = schritt.catch(() => {});
  return schritt.then(
    () => true,
    (e) => {
      // Diese Art steht nicht in FEHLER_ARTEN: ein Fehler beim Schreiben der
      // Fehlerdatei darf nicht in die Fehlerdatei wollen.
      notiere("fehlerdatei_gescheitert", { fehler: String(e) });
      return false;
    }
  );
}

// Eine Ausnahme in einem Rückruf des Transports reißt still ab: der Aufrufer
// sieht nur EOF, und der Grund steht allein in Thunderbirds Fehlerkonsole.
// Genau so brachen 0.3.1 und 0.3.2 jede Anfrage ab, während alle Quelltext-
// proben grün waren (#421). Darum liegt jeder Rückruf in dieser Hülle.
function sicher(was, fn, aufraeumen = null) {
  return function (...args) {
    try {
      return fn(...args);
    } catch (e) {
      notiere(was, { fehler: String(e) });
      if (aufraeumen) {
        try {
          aufraeumen();
        } catch (e2) {}
      }
      return undefined;
    }
  };
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

function adressenAus(kopf) {
  if (!kopf) {
    return [];
  }
  return MailServices.headerParser
    .parseDecodedHeader(kopf)
    .map((a) => String(a.email || "").trim().toLowerCase())
    .filter(Boolean);
}

// Der Klartext so, wie ihn `compose.getComposeDetails` als `plainTextBody`
// liefert (Thunderbird 158, ext-compose.js, convertComposeDetails).
function klartextVon(fenster) {
  const editor = fenster.GetCurrentEditor();
  const html = editor.outputToString("text/html", Ci.nsIDocumentEncoder.OutputRaw);
  if (fenster.IsHTMLEditor()) {
    return MsgUtils.convertToPlainText(html, true);
  }
  return parserUtils.convertToPlainText(html, Ci.nsIDocumentEncoder.OutputLFLineBreak, 0);
}

// Was das Fenster jetzt hinausschicken würde: Absender, Empfänger, Anhänge,
// Text (#407). `GetComposeDetails` überträgt dafür den Fensterinhalt nach
// `compFields`, dieselbe Funktion, die auch `compose.getComposeDetails`
// aufruft. Am Fenster selbst ändert das nichts. Geht es nicht, bleibt es bei
// dem, was `fensterStand` liest, mit `live: false`.
function fensterInhalt(fenster) {
  const stand = fensterStand(fenster);
  if (typeof fenster.GetComposeDetails !== "function") {
    return { ...stand, live: false, fehler: "GetComposeDetails fehlt" };
  }
  try {
    const felder = fenster.GetComposeDetails();
    const text = klartextVon(fenster);
    return {
      ...stand,
      betreff: felder.subject || "",
      live: true,
      identitaet: adressenAus(felder.from)[0] || "",
      an: adressenAus(felder.to),
      kopie: adressenAus(felder.cc),
      blindkopie: adressenAus(felder.bcc),
      anhaenge: (felder.attachments || []).map((a) => String(a.name || "")),
      text: text.slice(0, MAX_TEXT),
      text_gekuerzt: text.length > MAX_TEXT,
    };
  } catch (e) {
    return { ...stand, live: false, fehler: String(e) };
  }
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
      // Kein vorholen: Der Fokus wird nur geholt, wenn das Fenster in diesem
      // Aufruf entstand (#415). Dass es schon stand, sagt `schon_offen` dem
      // Aufrufer — der Befehl schreibt „war schon offen“ dazu.
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
      return { ok: true, fenster: verfassenFenster().map(fensterInhalt) };
    case "protokoll":
      return { ok: true, protokoll };
    default:
      return { ok: false, fehler: "befehl_unbekannt" };
  }
}

function annehmen(transport) {
  try {
    verbindungAnnehmen(transport);
  } catch (e) {
    notiere("annehmen_gescheitert", { fehler: String(e) });
    try {
      transport.close(Cr.NS_ERROR_ABORT);
    } catch (e2) {}
  }
}

function verbindungAnnehmen(transport) {
  if (verbindungen.size >= MAX_VERBINDUNGEN) {
    notiere("zu_viele_verbindungen", { offen: verbindungen.size });
    try {
      transport.close(Cr.NS_ERROR_ABORT);
    } catch (e) {}
    return;
  }
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
  // Wer nichts schickt, wird nach der Leerlauffrist getrennt.
  const leerlauf = setTimeout(() => {
    if (!fertig) {
      notiere("leerlauf", {});
      trennen();
    }
  }, FRIST_LEERLAUF_MS);
  const pumpe = Cc["@mozilla.org/network/input-stream-pump;1"].createInstance(
    Ci.nsIInputStreamPump
  );
  pumpe.init(eingang, 0, 0, true);
  pumpe.asyncRead({
    onStartRequest: sicher("annehmen_gescheitert", () => {}),
    onDataAvailable: sicher("annehmen_gescheitert", (_anfrage, strom, _versatz, anzahl) => {
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
      clearTimeout(leerlauf);
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
        })
        .catch((e) => {
          // Wirft schon das Bauen der Antwort, bliebe die Verbindung ohne
          // dieses Netz offen stehen, bis die Gegenseite aufgibt.
          notiere("antwort_gescheitert", { fehler: String(e) });
          schliessen();
        });
    }, trennen),
    onStopRequest: sicher("annehmen_gescheitert", () => {
      if (fertig) {
        // Der Aufrufer hat geschlossen; er schließt erst nach der ganzen
        // Antwortzeile, oder er wartet gar nicht mehr.
        trennen();
      } else {
        schliessen();
      }
    }, trennen),
  });
}

function socketdatei() {
  // Über den Verzeichnisdienst, nicht über `PathUtils`: Der ist in jedem
  // privilegierten Kontext da, und `nsIServerSocket.initWithFilename` will
  // ohnehin ein `nsIFile`.
  const datei = Services.dirsvc.get("ProfD", Ci.nsIFile);
  datei.append(SOCKET_DATEI);
  return datei;
}

function starten(version) {
  fassung = version;
  if (dienst) {
    return { laeuft: true, socket: dienst.pfad };
  }
  const datei = socketdatei();
  const pfad = datei.path;
  const server = Cc["@mozilla.org/network/server-socket;1"].createInstance(
    Ci.nsIServerSocket
  );
  try {
    // Ein Socket aus einem abgebrochenen Lauf belegt den Namen; initWithFilename
    // legt ihn nicht über eine bestehende Datei.
    if (datei.exists()) {
      datei.remove(false);
    }
  } catch (e) {
    notiere("altes_socket", { fehler: String(e) });
  }
  try {
    // Die Rechte liegen am Socket selbst: 0600, also nur das Konto, das
    // Thunderbird fährt.
    server.initWithFilename(datei, SOCKET_RECHTE, -1);
  } catch (e) {
    return { laeuft: false, socket: pfad, fehler: String(e) };
  }
  server.asyncListen({
    onSocketAccepted(_server, transport) {
      annehmen(transport);
    },
    onStopListening() {},
  });
  dienst = { server, pfad, version };
  return { laeuft: true, socket: pfad };
}

function stoppen() {
  if (dienst) {
    try {
      dienst.server.close();
    } catch (e) {}
    try {
      // Sonst bleibt ein Name liegen, an dem nichts horcht, und der nächste
      // Start müsste ihn für sich wegräumen.
      const datei = socketdatei();
      if (datei.exists()) {
        datei.remove(false);
      }
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

// Message-ID und Fassung jeder Mail, die laut Tagebuch in den letzten 14 Tagen
// hinausging (#407). Thunderbird übernimmt `X-Falzmarke-Fassung` beim Senden
// nicht in die gesendete Mail (gemessen 25.10.2026); das Tagebuch kennt sie
// noch aus dem Entwurf. Fehlt das Tagebuch, ist die Liste leer.
async function fassungen() {
  const pfad = PathUtils.join(PathUtils.profileDir, TAGEBUCH_DATEI);
  let inhalt = "";
  try {
    inhalt = await IOUtils.readUTF8(pfad);
  } catch (e) {
    return [];
  }
  const grenze = Date.now() - FASSUNGEN_TAGE * 24 * 60 * 60 * 1000;
  const aus = [];
  for (const zeile of inhalt.split("\n")) {
    let eintrag;
    try {
      eintrag = JSON.parse(zeile);
    } catch (e) {
      continue; // eine halb geschriebene letzte Zeile
    }
    const fassung = eintrag?.ursprung?.fassung;
    if (eintrag?.art !== "gesendet" || !eintrag.message_id || !fassung) {
      continue;
    }
    if (!(Date.parse(eintrag.zeit) >= grenze)) {
      continue;
    }
    aus.push({ message_id: String(eintrag.message_id), fassung: String(fassung) });
  }
  return aus;
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
        async fassungen() {
          return fassungen();
        },
      },
    };
  }
};
