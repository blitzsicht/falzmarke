/* Ging diese Nachricht schon hinaus? Derselbe Vergleich wie in
 * `skill/falzmarke/gesendet.py` (ADR 0051), für die Sperre beim Senden (ADR 0055).
 *
 * Zwei Fassungen derselben Regel laufen auseinander, wenn niemand hinsieht.
 * `tests/test_vergleich_js.py` gibt beiden dieselben Eingaben und verlangt
 * dieselben Ergebnisse — über node, ohne Thunderbird.
 *
 * Bewusst gleich grob wie dort: nur Buchstaben und Ziffern, kleingeschrieben,
 * ohne Adressen, bis zur Grußformel. Bekannte Abweichung: Python faltet mit
 * `casefold()` auch seltene Zeichen (Ligaturen, langes s), hier nur ß.
 */

"use strict";

(function (wurzel) {
  const KERN_MIN = 20;
  const ANFANG_MIN = 80;

  const GRUSS = new RegExp(
    "^(?:(?:viele|beste|liebe|herzliche|freundliche|schöne|sonnige|mit (?:freundlichen|" +
    "besten|herzlichen|lieben|vielen))\\s+)?gr(?:ü|ue)(?:ß|ss)e?n?(?:\\s+aus\\s+.+)?$" +
    "|^(?:(?:best|kind|warm|warmest)\\s+)?regards$|^(?:best|cheers|mfg|lg|vg|servus|ciao)$", "u");
  const DANACH = new RegExp(
    "^--\\s?$|^>|^(?:am|on)\\s.+(?:schrieb|wrote)\\b.*:$" +
    "|^-{2,}\\s*(?:original|ursprüngliche)|^(?:von|from):\\s", "u");
  const ADRESSE = /<?(?:https?|mailto):[^\s>]+>?/gu;
  const LISTE = /^\s*(?:[-*•·–+]|\d{1,3}[.)])\s+/u;
  const VORSILBE = /^\s*(?:re|aw|wg|fw|fwd|antw|sv|vs|tr)\s*(?:\[\d+\])?\s*:\s*/iu;
  const ZEICHEN = /[\p{L}\p{N}]/u;
  // Wie Pythons `str.splitlines()`.
  const ZEILENENDE = /\r\n|[\n\r\v\f\x1c-\x1e\x85\u2028\u2029]/u;

  function falte(text) {
    return String(text || "").toLowerCase().replace(/ß/g, "ss");
  }

  function nurZeichen(text) {
    let aus = "";
    for (const z of falte(text)) {
      if (ZEICHEN.test(z)) {
        aus += z;
      }
    }
    return aus;
  }

  function betreffKern(betreff) {
    let rest = String(betreff || "");
    for (;;) {
      const kuerzer = rest.replace(VORSILBE, "");
      if (kuerzer === rest) {
        break;
      }
      rest = kuerzer;
    }
    return nurZeichen(rest);
  }

  // ── HTML zu Text, wie `_Klartext` ──────────────────────────────────────────

  const BLOCK = new Set(["p", "br", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6",
    "table", "ul", "ol", "blockquote", "pre", "hr"]);
  const STILL = new Set(["style", "script", "head", "title"]);
  const ROH = new Set(["style", "script"]);
  const ZEICHENNAMEN = {
    amp: "&", lt: "<", gt: ">", quot: "\"", apos: "'", nbsp: "\u00a0",
    auml: "ä", ouml: "ö", uuml: "ü", Auml: "Ä", Ouml: "Ö", Uuml: "Ü", szlig: "ß",
    eacute: "é", egrave: "è", agrave: "à", aacute: "á", ccedil: "ç", euro: "€",
  };
  const MARKE = new RegExp(
    "<!--[\\s\\S]*?(?:-->|$)|<![^>]*>|<\\?[^>]*>" +
    "|<(/?)([A-Za-z][A-Za-z0-9:-]*)((?:[^>\"']|\"[^\"]*\"|'[^']*')*?)(/?)>", "g");

  function entschluesseln(text) {
    return text.replace(/&(#x[0-9a-fA-F]+|#[0-9]+|[A-Za-z][A-Za-z0-9]*);/g, (ganz, name) => {
      if (name[0] === "#") {
        const zahl = name[1] === "x" || name[1] === "X"
          ? parseInt(name.slice(2), 16) : parseInt(name.slice(1), 10);
        try {
          return String.fromCodePoint(zahl);
        } catch (_fehler) {
          return "\ufffd";
        }
      }
      return Object.hasOwn(ZEICHENNAMEN, name) ? ZEICHENNAMEN[name] : ganz;
    });
  }

  function klartextAusHtml(html) {
    const quelle = String(html || "");
    const teile = [];
    let still = 0;
    let stelle = 0;
    MARKE.lastIndex = 0;
    let treffer;
    while ((treffer = MARKE.exec(quelle)) !== null) {
      if (treffer.index > stelle && !still) {
        teile.push(entschluesseln(quelle.slice(stelle, treffer.index)));
      }
      stelle = MARKE.lastIndex;
      const name = (treffer[2] || "").toLowerCase();
      if (!name) {
        continue;  // Kommentar, Deklaration
      }
      const ende = treffer[1] === "/";
      const leer = treffer[4] === "/";
      if (!ende) {
        if (STILL.has(name)) {
          still += 1;
        }
        if (BLOCK.has(name)) {
          teile.push("\n");
        }
        if (ROH.has(name) && !leer) {
          // Inhalt von <script> und <style> ist Text bis zum schließenden Tag.
          const schluss = quelle.toLowerCase().indexOf("</" + name, stelle);
          stelle = schluss < 0 ? quelle.length : schluss;
          MARKE.lastIndex = stelle;
          continue;
        }
      }
      if (ende || leer) {
        if (STILL.has(name)) {
          still = Math.max(0, still - 1);
        }
        if (BLOCK.has(name)) {
          teile.push("\n");
        }
      }
    }
    if (stelle < quelle.length && !still) {
      teile.push(entschluesseln(quelle.slice(stelle)));
    }
    return teile.join("");
  }

  // ── Merkmale und Urteil, wie `merkmale()` und `vergleiche()` ───────────────

  function zeilen(text) {
    const stuecke = String(text || "").split(ZEILENENDE);
    if (stuecke.length && stuecke[stuecke.length - 1] === "") {
      stuecke.pop();
    }
    return stuecke;
  }

  function ohneZeichenAmEnde(text, zeichen) {
    let ende = text.length;
    while (ende > 0 && zeichen.includes(text[ende - 1])) {
      ende -= 1;
    }
    return text.slice(0, ende);
  }

  function schnitt(text, gruss) {
    const behalten = [];
    for (const zeile of zeilen(text)) {
      const rein = falte(zeile.trim());
      if (DANACH.test(rein) || (gruss && GRUSS.test(ohneZeichenAmEnde(rein, ",.!")))) {
        break;
      }
      behalten.push(zeile.replace(LISTE, ""));
    }
    return nurZeichen(behalten.join("\n").replace(ADRESSE, ""));
  }

  function voll(text) {
    return nurZeichen(zeilen(text).map((z) => z.replace(LISTE, "")).join("\n")
      .replace(ADRESSE, ""));
  }

  /** Die Adressen einer Empfängerliste, klein: „Name <a@b>“, „a@b“ oder Listen davon. */
  function adressen(liste) {
    const aus = new Set();
    const werte = Array.isArray(liste) ? liste : [liste];
    for (const wert of werte) {
      if (typeof wert !== "string") {
        continue;
      }
      // Erst die Namen in Anführungszeichen weg, dann die Adressen in <…>; was
      // übrig bleibt, sind nackte Adressen zwischen Kommas.
      const rest = wert.replace(/"(?:[^"\\]|\\.)*"/g, " ")
        .replace(/<([^<>\s]+@[^<>\s]+)>/g, (_ganz, adresse) => {
          aus.add(adresse.toLowerCase());
          return " ";
        });
      for (const teil of rest.split(/[,;\s]+/)) {
        if (teil.includes("@")) {
          aus.add(teil.replace(/^["'(]+|["')]+$/g, "").toLowerCase());
        }
      }
    }
    return aus;
  }

  function merkmale({ empfaenger = [], betreff = "", text = "", fassung = "" } = {}) {
    return {
      empfaenger: empfaenger instanceof Set ? empfaenger : adressen(empfaenger),
      betreff: betreffKern(betreff),
      kern: schnitt(text, true),
      bisSignatur: schnitt(text, false),
      voll: voll(text),
      fassung: String(fassung || "").trim(),
    };
  }

  function laenge(text) {
    return [...text].length;
  }

  function gleicherText(eigen, fremd) {
    if (laenge(eigen.kern) >= KERN_MIN && eigen.kern === fremd.kern) {
      return true;
    }
    return [eigen.kern, eigen.bisSignatur].some(
      (anfang) => laenge(anfang) >= ANFANG_MIN && fremd.voll.startsWith(anfang));
  }

  function vergleiche(eigen, fremd) {
    if (eigen.fassung && eigen.fassung === fremd.fassung) {
      return "gesendet";
    }
    if (gleicherText(eigen, fremd)) {
      return "gesendet";
    }
    if (eigen.betreff && eigen.betreff === fremd.betreff) {
      return "geaendert";
    }
    return "frei";
  }

  const api = { KERN_MIN, ANFANG_MIN, nurZeichen, betreffKern, klartextAusHtml, schnitt, voll,
    adressen, merkmale, gleicherText, vergleiche };
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    wurzel.FalzmarkeVergleich = api;
  }
})(this);
