/* falzmarke Entwurfsbrücke, Hintergrund (ADR 0054, ADR 0055, ADR 0056, ADR 0058, ADR 0060)
 *
 * Startet die Brücke und führt das Tagebuch: Für jedes Verfassen-Fenster hält
 * es fest, woher der Entwurf kam (Konto, UID, Fassung) und was aus ihm wurde,
 * also geöffnet, gespeichert, gesendet oder ohne Senden geschlossen. Beim
 * Senden stehen Absender, Empfänger samt Bcc und die Namen der Anhänge dabei.
 * `falzmarke status` liest das Tagebuch aus dem Profilordner, auch wenn
 * Thunderbird zu ist.
 *
 * Dazu die Sperre beim Senden. Sie fragt zuerst, was in dieser Sitzung schon
 * hinausging — der Gesendet-Ordner hat es erst Sekunden später (#413) —, dann
 * den Ordner selbst. Sie fragt nach, wenn derselbe Text in den
 * letzten 14 Tagen schon an einen dieser Empfänger ging, oder wenn in den
 * letzten 24 Stunden ein anderer Text mit demselben Betreff an sie ging und
 * das Fenster ein Entwurf oder eine neue Mail ist (Antworten teilen ihren
 * Betreff). Vorgewählt ist „Nicht senden“. Kann die Sperre nicht prüfen,
 * lässt sie senden und schreibt das ins Tagebuch: Eine Prüfung, die
 * scheitert, darf den Menschen nicht aufhalten.
 *
 * Welche Empfänger die Sperre vergleicht, ist nicht dasselbe wie das, was im
 * Tagebuch steht: Verglichen wird ohne die **eigene** Blindkopie, wie
 * `gesendet.py` es tut — eine Archivadresse in Bcc steht sonst auf jeder Mail
 * und hebt den Vorfilter auf. Ins Tagebuch kommt sie trotzdem (ADR 0056).
 *
 * Senden kann das Add-on nicht. Es hat die Berechtigung dazu nicht, und
 * `tests/test_entwurfsbruecke.py` prüft den Quelltext darauf.
 */
"use strict";

const V = globalThis.FalzmarkeVergleich;
const TAG_MS = 24 * 60 * 60 * 1000;
const FRIST_GLEICH_MS = 14 * TAG_MS;
const FRIST_BETREFF_MS = TAG_MS;
// Mehr gesendete Mails in 14 Tagen sind kein Postfach dieser Größe mehr; dann
// prüft die Sperre lieber gar nicht als nur einen Teil.
const MAX_GESENDET = 2000;
// So lange wartet das Tagebuch nach dem Schließen, ob das Senden noch gemeldet wird.
const NACHLAUF_MS = 3000;
// So viele Sendungen hält die Sitzung höchstens vor. Mehr sind in einer
// Sitzung kein Postfach dieser Größe mehr, und der Gesendet-Ordner hat sie
// bis dahin längst (#413).
const MAX_SITZUNG = 200;
// So lange darf die ganze Prüfung dauern. ADR 0055, Punkt 5 sagt zu: Eine
// Prüfung, die hängt, darf den Menschen nicht aufhalten — abgesichert war
// aber nur die Stückzahl (MAX_GESENDET) und der Fehlerfall. Eine einzige
// Abfrage, die nicht zurückkommt, hielt das Fenster für immer.
const FRIST_PRUEFUNG_MS = 10000;

// Je Verfassen-Fenster: woher der Entwurf kam und ob er hinausging.
const fenster = new Map();

// Was in dieser Sitzung hinausgegangen ist, in der Reihenfolge des Sendens.
// Der Gesendet-Ordner weiß davon erst, wenn Thunderbird die Mail dort
// abgelegt und abgeglichen hat — bei IMAP Sekunden später. Wer zwei Fenster
// kurz hintereinander sendet, kam in dieser Lücke ungefragt durch (#413);
// bis dahin ist diese Liste die einzige Quelle.
const hinaus = [];

browser.entwurfsbruecke.starten().then(
  (stand) => console.log("falzmarke Entwurfsbrücke", JSON.stringify(stand)),
  (fehler) => console.error("falzmarke Entwurfsbrücke", fehler)
);

function eintragen(art, tabId, mehr = {}) {
  const stand = fenster.get(tabId);
  return browser.entwurfsbruecke
    .tagebuch({ ...mehr, art, ursprung: stand ? stand.ursprung : null })
    .catch((fehler) => console.error("falzmarke Tagebuch", art, fehler));
}

function liste(wert) {
  if (Array.isArray(wert)) {
    return wert;
  }
  return wert ? [wert] : [];
}

function kopfwert(teil, name) {
  const werte = teil && teil.headers ? teil.headers[name] : null;
  return Array.isArray(werte) && werte.length ? String(werte[0]).trim() : "";
}

// Der Text einer Nachricht wie in gesendet.py: der Textteil, sonst der
// HTML-Teil ohne Auszeichnung. Anhänge zählen nicht.
function textVon(nachricht) {
  const teile = [];
  const sammeln = (teil) => {
    if (!teil) {
      return;
    }
    if (kopfwert(teil, "content-disposition").toLowerCase().startsWith("attachment")) {
      return;
    }
    if (typeof teil.body === "string") {
      teile.push(teil);
    }
    for (const unter of teil.parts || []) {
      sammeln(unter);
    }
  };
  sammeln(nachricht);
  const art = (teil) => String(teil.contentType || "").toLowerCase();
  const klar = teile.find((teil) => art(teil) === "text/plain");
  if (klar) {
    return klar.body;
  }
  const html = teile.find((teil) => art(teil) === "text/html");
  return html ? V.klartextAusHtml(html.body) : "";
}

async function ursprungVon(tabId) {
  const details = await browser.compose.getComposeDetails(tabId);
  const ursprung = {
    typ: details.type || "",
    konto: [...V.adressen(liste(details.from))][0] || "",
    betreff: details.subject || "",
    uid: null,
    fassung: "",
  };
  if (details.type === "draft") {
    await ankern(ursprung, tabId, details.relatedMessageId);
  }
  return ursprung;
}

// Setzt UID und Fassung des Entwurfs und hält fest, woher beide kommen
// (ADR 0060). An dieser Zahl hängt die ganze Zuordnung: Ohne sie findet
// `falzmarke status` zu der Versandzeile keinen Eintrag im Entwurfsbuch — kein
// „Ging an …“, kein BELEGT, und die Sperre kann den Entwurf nicht über die
// Fassung erkennen (#420).
//
// Gerufen wird auch **ohne** `relatedMessageId`: Dass sie fehlt, ist selbst
// einer der möglichen Gründe, und er soll im Tagebuch stehen statt vermutet zu
// werden. Ein zweites Mal gerufen wird die Funktion vor dem Senden, wenn beim
// Öffnen keine UID zu haben war.
async function ankern(ursprung, tabId, nachrichtId) {
  let kennung;
  try {
    kennung = await browser.entwurfsbruecke.entwurfskennung(nachrichtId || null, tabId);
  } catch (fehler) {
    kennung = { uid: null, quelle: "", grund: String(fehler) };
  }
  const zahl = (wert) => (wert === undefined || wert === null ? null : wert);
  ursprung.uid = zahl(kennung.uid);
  ursprung.uid_quelle = kennung.quelle || "";
  ursprung.uid_grund = kennung.grund || "";
  ursprung.uid_kennung = zahl(kennung.uid_kennung);
  ursprung.uid_draft_id = zahl(kennung.uid_draft_id);
  if (!ursprung.fassung && nachrichtId) {
    try {
      const voll = await browser.messages.getFull(nachrichtId);
      ursprung.fassung = kopfwert(voll, "x-falzmarke-fassung");
    } catch (e) {
      ursprung.fassung = "";
    }
  }
  ursprung.fassung_quelle = ursprung.fassung ? "kopf" : "";
  if (!ursprung.fassung && ursprung.uid !== null) {
    const ausKette = fassungAusKette(await auszug(), ursprung.konto, ursprung.uid);
    if (ausKette) {
      ursprung.fassung = ausKette;
      ursprung.fassung_quelle = "kette";
    }
  }
}

// Die Fassung eines Entwurfs, den Thunderbird selbst gespeichert hat (#420).
// Beim Speichern fällt `X-Falzmarke-Fassung` weg und die UID wechselt; die
// Kette `gespeichert` → `neu_uid` führt zurück auf den Entwurf, den falzmarke
// angelegt hat — der trägt sie im Tagebuch. Die jüngste Zeile der Kette
// gewinnt; getrennt werden zwei Entwürfe aus derselben Quelle über die UID,
// nicht über die Fassung (ADR 0055).
//
// Hat schon das **erste** Öffnen keine UID bekommen, findet auch die Kette
// nichts. Dann bleibt die Fassung leer und verglichen wird über Text und
// Betreff, wie bisher.
function fassungAusKette(eintraege, konto, uid) {
  const kette = V.kette(eintraege, konto, uid);
  let gefunden = "";
  for (const eintrag of eintraege) {
    const ursprung = eintrag.ursprung;
    if (!ursprung || String(ursprung.konto || "").toLowerCase() !== konto) {
      continue;
    }
    const fassung = String(ursprung.fassung || "");
    const uidHier = ursprung.uid === null || ursprung.uid === undefined
      ? "" : String(ursprung.uid);
    if (fassung && uidHier && kette.has(uidHier)) {
      gefunden = fassung;
    }
  }
  return gefunden;
}

function merken(tabId, neu) {
  let stand = fenster.get(tabId);
  if (!stand) {
    stand = { ursprung: null, gesendet: false };
    stand.bereit = ursprungVon(tabId)
      .then(
        (ursprung) => {
          stand.ursprung = ursprung;
        },
        (fehler) => {
          stand.ursprung = { fehler: String(fehler) };
        }
      )
      .then(() => (neu ? eintragen("geoeffnet", tabId) : null));
    fenster.set(tabId, stand);
  }
  return stand.bereit.then(() => stand);
}

// ── Die Sperre ──────────────────────────────────────────────────────────────

async function gesendetOrdner(identitaet) {
  const konten = await browser.accounts.list(false);
  const konto = konten.find((k) => (k.identities || []).some((i) => i.id === identitaet));
  if (!konto) {
    throw new Error(`kein Konto zur Identität ${identitaet}`);
  }
  const ordner = await browser.folders.query({ accountId: konto.id, specialUse: ["sent"] });
  if (!ordner.length) {
    throw new Error(`kein Ordner „Gesendet“ im Konto ${konto.name}`);
  }
  return ordner;
}

async function gesendeteSeit(ordner, seit) {
  const aus = [];
  let seite = await browser.messages.query({ folderId: ordner.map((o) => o.id), fromDate: seit });
  for (;;) {
    aus.push(...(seite.messages || []));
    if (aus.length > MAX_GESENDET) {
      throw new Error(`mehr als ${MAX_GESENDET} gesendete Mails in 14 Tagen`);
    }
    if (!seite.id) {
      return aus;
    }
    seite = await browser.messages.continueList(seite.id);
  }
}

// Die Zeilen des Tagebuchs aus den letzten 14 Tagen. Zwei Dinge kommen
// daraus: die Fassung einer gesendeten Mail (ADR 0056) und die Kette, über
// die ein von Thunderbird gespeicherter Entwurf seine Fassung zurückbekommt
// (ADR 0060). Schweigt das Tagebuch, vergleicht die Sperre wie bisher über
// Text und Betreff — eine Prüfung, die nicht alles weiß, darf den Menschen
// nicht aufhalten.
async function auszug() {
  try {
    return (await browser.entwurfsbruecke.tagebuchauszug()) || [];
  } catch (fehler) {
    console.error("falzmarke Tagebuch", fehler);
    return [];
  }
}

// Message-ID → Fassung (ADR 0056). Thunderbird übernimmt
// `X-Falzmarke-Fassung` beim Senden nicht; ohne das hier griffe der Vergleich
// über die Fassung bei keiner gesendeten Mail.
function fassungenAus(eintraege) {
  const bekannt = new Map();
  for (const eintrag of eintraege) {
    const fassung = (eintrag.ursprung && eintrag.ursprung.fassung) || "";
    const kennung = V.kennung(eintrag.message_id);
    if (eintrag.art === "gesendet" && kennung && fassung) {
      bekannt.set(kennung, fassung);
    }
  }
  return bekannt;
}

// Nach der Frist gewinnt die Grenze, und die Prüfung läuft ins Leere statt
// ins Fenster. `finally` räumt die Uhr ab, damit node nicht auf sie wartet.
function mitFrist(versprechen, frist) {
  let uhr;
  const grenze = new Promise((_ja, nein) => {
    uhr = setTimeout(() => nein(new Error("frist_abgelaufen")), frist);
  });
  return Promise.race([versprechen, grenze]).finally(() => clearTimeout(uhr));
}

// Die Merkmale der Nachricht im Fenster. `mitBcc` entscheidet die Richtung:
// Als **Sender** vergleicht sie ohne die eigene Blindkopie (siehe unten), als
// **gesendete Mail** zählt sie mit, wie `gesendet.py` es mit `mit_bcc=True`
// tut und wie der Gesendet-Ordner sie liefert (`bccList`).
function merkmaleVon(details, ursprung, mitBcc) {
  const empfaenger = V.adressen([
    ...liste(details.to),
    ...liste(details.cc),
    ...(mitBcc ? liste(details.bcc) : []),
  ]);
  return V.merkmale({
    empfaenger,
    betreff: details.subject || "",
    text: details.plainTextBody || V.klartextAusHtml(details.body || ""),
    fassung: (ursprung && ursprung.fassung) || "",
  });
}

// Eine Sendung, die hinausgeht, kommt in die Sitzungsliste — und zwar auf
// jedem Weg, der sie hinauslässt: ohne Fund, nach „Trotzdem senden“ und auch
// nach einer gescheiterten Prüfung. Der Rückgabewert `{}` ist die Antwort an
// Thunderbird; so kann kein Zweig das Merken vergessen (#413).
function hinausMerken(tabId, details, ursprung) {
  const jetzt = Date.now();
  hinaus.push({
    tabId,
    zeit: jetzt,
    betreff: details.subject || "",
    merkmale: merkmaleVon(details, ursprung, true),
  });
  // Alt genug, um auch im Gesendet-Ordner nicht mehr zu zählen.
  while (hinaus.length && jetzt - hinaus[0].zeit > FRIST_GLEICH_MS) {
    hinaus.shift();
  }
  while (hinaus.length > MAX_SITZUNG) {
    hinaus.shift();
  }
  return {};
}

// Eine Sendung, die doch nicht hinausging, darf die nächste nicht aufhalten.
function hinausVergessen(tabId) {
  for (let i = hinaus.length - 1; i >= 0; i -= 1) {
    if (hinaus[i].tabId === tabId) {
      hinaus.splice(i, 1);
      return;
    }
  }
}

async function befund(details, eigen, tabId) {
  // **Ohne die eigene Blindkopie.** `gesendet.py` bildet die eigenen
  // Empfänger aus An und Cc (`mit_bcc=False`) und die der gesendeten Mail
  // aus An, Cc und Bcc (`mit_bcc=True`). Hier stand die eigene Bcc mit drin,
  // und das hob den Vorfilter auf: Vier Profile tragen eine Archivadresse in
  // Bcc, also teilte jede gesendete Mail eine Adresse mit jeder neuen. Die
  // Folge war nicht eine schärfere Sperre, sondern eine, die bei „Rechnung"
  // an zwei verschiedene Kunden am selben Tag fragt — und wer dreißig Mal
  // umsonst gefragt wird, klickt beim einunddreißigsten weg.
  if (!eigen.empfaenger.size) {
    return null;
  }
  const jetzt = Date.now();
  const mitBetreff = details.type === "draft" || details.type === "new";
  let aehnlich = null;
  // Eine unlesbare Mail überspringt die Prüfung, statt sie abzubrechen: Der
  // echte Treffer kann zwei Kandidaten später liegen. Gemeldet wird das auf
  // *jedem* Weg hinaus — auch beim Treffer, denn „gesperrt, aber nicht alles
  // gesehen" ist eine andere Aussage als „gesperrt".
  let uebersprungen = 0;
  const melden = async () => {
    if (uebersprungen) {
      await eintragen("pruefung_teilweise", tabId, { uebersprungen });
    }
  };
  // Zuerst die eigene Sitzung, vor jeder Abfrage: Was gerade hinausging,
  // steht noch nicht im Gesendet-Ordner. Diese Runde braucht weder das
  // Tagebuch noch das Postfach und antwortet darum auch dann, wenn beide
  // schweigen (#413).
  for (const frueher of hinaus) {
    const gemeinsam = [...eigen.empfaenger].filter(
      (adresse) => frueher.merkmale.empfaenger.has(adresse));
    if (!gemeinsam.length) {
      continue;
    }
    const urteil = V.vergleiche(eigen, frueher.merkmale);
    const fund = { zeit: frueher.zeit, an: gemeinsam, betreff: frueher.betreff };
    if (urteil === "gesendet") {
      await melden();
      return { ...fund, grund: "gleicher_text" };
    }
    if (urteil === "geaendert" && mitBetreff && !aehnlich
        && jetzt - frueher.zeit <= FRIST_BETREFF_MS) {
      aehnlich = { ...fund, grund: "gleicher_betreff" };
    }
  }
  const bekannt = fassungenAus(await auszug());
  const ordner = await gesendetOrdner(details.identityId);
  const gesendete = await gesendeteSeit(ordner, new Date(jetzt - FRIST_GLEICH_MS));
  for (const kopf of gesendete) {
    const an = V.adressen([
      ...liste(kopf.recipients),
      ...liste(kopf.ccList),
      ...liste(kopf.bccList),
    ]);
    const gemeinsam = [...eigen.empfaenger].filter((adresse) => an.has(adresse));
    if (!gemeinsam.length) {
      continue;
    }
    const zeit = new Date(kopf.date).getTime();
    let voll;
    try {
      voll = await browser.messages.getFull(kopf.id);
    } catch (fehler) {
      uebersprungen += 1;
      continue;
    }
    const fremd = V.merkmale({
      empfaenger: an,
      betreff: kopf.subject || "",
      text: textVon(voll),
      fassung:
        kopfwert(voll, "x-falzmarke-fassung") || bekannt.get(V.kennung(kopf.headerMessageId)) || "",
    });
    const urteil = V.vergleiche(eigen, fremd);
    const fund = { zeit, an: gemeinsam, betreff: kopf.subject || "" };
    if (urteil === "gesendet") {
      await melden();
      return { ...fund, grund: "gleicher_text" };
    }
    if (urteil === "geaendert" && mitBetreff && !aehnlich && jetzt - zeit <= FRIST_BETREFF_MS) {
      aehnlich = { ...fund, grund: "gleicher_betreff" };
    }
  }
  await melden();
  return aehnlich;
}

function wann(zeit) {
  return new Date(zeit).toLocaleString("de-DE", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function frage(fund) {
  const an = fund.an.join(", ");
  if (fund.grund === "gleicher_text") {
    return [
      "Diese Mail ging schon hinaus",
      `Derselbe Text ging am ${wann(fund.zeit)} schon an ${an}:\n„${fund.betreff}“\n\n` +
        "Sie liegt in „Gesendete Elemente“. Noch einmal senden?",
    ];
  }
  return [
    "Eine Mail mit diesem Betreff ging schon hinaus",
    `Am ${wann(fund.zeit)} ging eine Mail mit demselben Betreff an ${an}, ` +
      `aber mit anderem Text:\n„${fund.betreff}“\n\n` +
      "Ist das die Korrektur, dann „Trotzdem senden“.",
  ];
}

// Wohin die Mail geht und was sie mitnimmt, für den Eintrag „gesendet“ (ADR 0056).
// Scheitert das Lesen der Anhänge, steht das im Eintrag; das Senden hält es nicht auf.
async function versandVon(tabId, details) {
  const versand = {
    identitaet: [...V.adressen(liste(details.from))][0] || "",
    an: [...V.adressen(liste(details.to))],
    kopie: [...V.adressen(liste(details.cc))],
    blindkopie: [...V.adressen(liste(details.bcc))],
  };
  try {
    const anhaenge = await browser.compose.listAttachments(tabId);
    versand.anhaenge = (anhaenge || []).map((a) => String(a.name || ""));
  } catch (fehler) {
    versand.anhaenge_fehler = String(fehler);
  }
  return versand;
}

browser.compose.onBeforeSend.addListener(async (tab, details) => {
  const stand = await merken(tab.id, false);
  // Blieb die UID beim Öffnen leer, hier noch einmal: Der Eintrag `gesendet`
  // ist der, über den `status` die Mail ihrem Entwurf zuordnet, und bis hierher
  // ist das Fenster fertig geladen (#420). `stand.ursprung` ist dasselbe
  // Objekt, das `geoeffnet` schon geschrieben hat — jene Zeile steht und bleibt
  // wie sie ist, die folgenden tragen die Werte.
  if (stand.ursprung && stand.ursprung.typ === "draft" && stand.ursprung.uid === null) {
    try {
      await ankern(stand.ursprung, tab.id, details.relatedMessageId);
    } catch (fehler) {
      console.error("falzmarke Ursprung", fehler);
    }
  }
  stand.angehalten = false;
  stand.versand = await versandVon(tab.id, details).catch((fehler) => ({
    versand_fehler: String(fehler),
  }));
  const eigen = merkmaleVon(details, stand.ursprung, false);
  let fund;
  try {
    fund = await mitFrist(befund(details, eigen, tab.id), FRIST_PRUEFUNG_MS);
  } catch (fehler) {
    await eintragen("pruefung_fehlgeschlagen", tab.id, { fehler: String(fehler) });
    return hinausMerken(tab.id, details, stand.ursprung);
  }
  if (!fund) {
    return hinausMerken(tab.id, details, stand.ursprung);
  }
  const [titel, text] = frage(fund);
  const mehr = {
    grund: fund.grund,
    frueher: Number.isFinite(fund.zeit) ? new Date(fund.zeit).toISOString() : "",
    an: fund.an,
  };
  let trotzdem;
  try {
    trotzdem = await browser.entwurfsbruecke.fragen(tab.id, titel, text);
  } catch (fehler) {
    await eintragen("pruefung_fehlgeschlagen", tab.id, { ...mehr, fehler: String(fehler) });
    return hinausMerken(tab.id, details, stand.ursprung);
  }
  if (trotzdem) {
    await eintragen("trotzdem", tab.id, mehr);
    return hinausMerken(tab.id, details, stand.ursprung);
  }
  await eintragen("gesperrt", tab.id, mehr);
  stand.angehalten = true;
  return { cancel: true };
});

// ── Das Tagebuch ────────────────────────────────────────────────────────────

browser.compose.onAfterSend.addListener(async (tab, sendInfo) => {
  const stand = await merken(tab.id, false);
  const modus = sendInfo.mode || "";
  if (sendInfo.error) {
    if (stand.angehalten) {
      // Thunderbird meldet das Anhalten noch einmal als gescheitertes Senden („Send
      // aborted by an onBeforeSend event“, gemessen 25.10.2026). „gesperrt“ steht schon da.
      stand.angehalten = false;
      return;
    }
    // Was nicht hinausging, darf die nächste Sendung nicht aufhalten (#413).
    hinausVergessen(tab.id);
    await eintragen("senden_fehlgeschlagen", tab.id, { modus, fehler: String(sendInfo.error) });
    return;
  }
  stand.gesendet = true;
  await eintragen("gesendet", tab.id, {
    ...(stand.versand || {}),
    modus,
    message_id: sendInfo.headerMessageId || "",
  });
});

browser.compose.onAfterSave.addListener(async (tab, saveInfo) => {
  await merken(tab.id, false);
  const neu = [];
  // Das Fenster als zweiter Weg nur bei **einer** gespeicherten Nachricht:
  // Seine `draftId` zeigt auf genau einen Entwurf, und bei mehreren wäre nicht
  // zu sagen, auf welchen (ADR 0060).
  const einzeln = (saveInfo.messages || []).length === 1;
  for (const nachricht of saveInfo.messages || []) {
    neu.push(
      await browser.entwurfsbruecke
        .entwurfskennung(nachricht.id, einzeln ? tab.id : null)
        .then((kennung) => (kennung && kennung.uid !== undefined ? kennung.uid : null))
        .catch(() => null)
    );
  }
  await eintragen("gespeichert", tab.id, { modus: saveInfo.mode || "", neu_uid: neu });
});

browser.tabs.onCreated.addListener((tab) => {
  if (tab.type === "messageCompose") {
    merken(tab.id, true);
  }
});

browser.tabs.onRemoved.addListener((tabId) => {
  const stand = fenster.get(tabId);
  if (!stand) {
    return;
  }
  setTimeout(() => {
    stand.bereit
      .then(() => (stand.gesendet ? null : eintragen("geschlossen", tabId)))
      .finally(() => fenster.delete(tabId));
  }, NACHLAUF_MS);
});

// Fenster, die schon offen waren, als das Add-on geladen wurde.
browser.tabs.query({ type: "messageCompose" }).then(
  (offen) => offen.forEach((tab) => merken(tab.id, false)),
  (fehler) => console.error("falzmarke Tagebuch", fehler)
);
