/* falzmarke Entwurfsbrücke, Hintergrund (ADR 0054, ADR 0055, ADR 0056)
 *
 * Startet die Brücke und führt das Tagebuch: Für jedes Verfassen-Fenster hält
 * es fest, woher der Entwurf kam (Konto, UID, Fassung) und was aus ihm wurde,
 * also geöffnet, gespeichert, gesendet oder ohne Senden geschlossen. Beim
 * Senden stehen Absender, Empfänger samt Bcc und die Namen der Anhänge dabei.
 * `falzmarke status` liest das Tagebuch aus dem Profilordner, auch wenn
 * Thunderbird zu ist.
 *
 * Dazu die Sperre beim Senden. Sie fragt nach, wenn derselbe Text in den
 * letzten 14 Tagen schon an einen dieser Empfänger ging, oder wenn in den
 * letzten 24 Stunden ein anderer Text mit demselben Betreff an sie ging und
 * das Fenster ein Entwurf oder eine neue Mail ist (Antworten teilen ihren
 * Betreff). Vorgewählt ist „Nicht senden“. Kann die Sperre nicht prüfen,
 * lässt sie senden und schreibt das ins Tagebuch: Eine Prüfung, die
 * scheitert, darf den Menschen nicht aufhalten.
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

// Je Verfassen-Fenster: woher der Entwurf kam und ob er hinausging.
const fenster = new Map();

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
  if (details.type === "draft" && details.relatedMessageId) {
    try {
      ursprung.uid = await browser.entwurfsbruecke.kennung(details.relatedMessageId);
    } catch (e) {
      ursprung.uid = null;
    }
    try {
      const voll = await browser.messages.getFull(details.relatedMessageId);
      ursprung.fassung = kopfwert(voll, "x-falzmarke-fassung");
    } catch (e) {
      ursprung.fassung = "";
    }
  }
  return ursprung;
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

// Message-ID → Fassung aus dem Tagebuch (ADR 0056). Thunderbird übernimmt
// `X-Falzmarke-Fassung` beim Senden nicht; ohne das hier griffe der Vergleich
// über die Fassung bei keiner gesendeten Mail.
async function fassungenAusTagebuch() {
  const bekannt = new Map();
  let eintraege = [];
  try {
    eintraege = await browser.entwurfsbruecke.fassungen();
  } catch (fehler) {
    // Ohne Tagebuch vergleicht die Sperre wie bisher über Text und Betreff.
    console.error("falzmarke Tagebuch", fehler);
  }
  for (const { message_id, fassung } of eintraege || []) {
    const kennung = V.kennung(message_id);
    if (kennung && fassung) {
      bekannt.set(kennung, fassung);
    }
  }
  return bekannt;
}

async function befund(details, ursprung) {
  const empfaenger = V.adressen([
    ...liste(details.to),
    ...liste(details.cc),
    ...liste(details.bcc),
  ]);
  if (!empfaenger.size) {
    return null;
  }
  const bekannt = await fassungenAusTagebuch();
  const eigen = V.merkmale({
    empfaenger,
    betreff: details.subject || "",
    text: details.plainTextBody || V.klartextAusHtml(details.body || ""),
    fassung: (ursprung && ursprung.fassung) || "",
  });
  const jetzt = Date.now();
  const ordner = await gesendetOrdner(details.identityId);
  const gesendete = await gesendeteSeit(ordner, new Date(jetzt - FRIST_GLEICH_MS));
  const mitBetreff = details.type === "draft" || details.type === "new";
  let aehnlich = null;
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
    const voll = await browser.messages.getFull(kopf.id);
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
      return { ...fund, grund: "gleicher_text" };
    }
    if (urteil === "geaendert" && mitBetreff && !aehnlich && jetzt - zeit <= FRIST_BETREFF_MS) {
      aehnlich = { ...fund, grund: "gleicher_betreff" };
    }
  }
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
  stand.angehalten = false;
  stand.versand = await versandVon(tab.id, details).catch((fehler) => ({
    versand_fehler: String(fehler),
  }));
  let fund;
  try {
    fund = await befund(details, stand.ursprung);
  } catch (fehler) {
    await eintragen("pruefung_fehlgeschlagen", tab.id, { fehler: String(fehler) });
    return {};
  }
  if (!fund) {
    return {};
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
    return {};
  }
  if (trotzdem) {
    await eintragen("trotzdem", tab.id, mehr);
    return {};
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
  for (const nachricht of saveInfo.messages || []) {
    neu.push(await browser.entwurfsbruecke.kennung(nachricht.id).catch(() => null));
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
