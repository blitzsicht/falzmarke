#!/usr/bin/env python3
"""Farbmessung der E-Mail-Signaturen in vier Lagen, gerendert in Chromium.

Aufruf (aus der Wurzel des Repos):

    uv run --with playwright --with pillow python \
        docs/messungen/2026-10-21-signatur-farben/messung.py \
        --profile ~/.config/falzmarke/profiles \
        --gesendet <Belege>/gesendet-signatur-probe-drei.html

Gemessen wird, was Chromium tatsächlich setzt (berechnete Farben, gewählte
Bildquelle), nicht was im Quelltext steht. Drei Arten Prüfling:

- ``Q``  die Signaturdatei aus dem Profilordner, unverändert. So setzt sie
         Thunderbird per ``user.js`` (ADR 0050) — ob Thunderbird ihr
         ``<style>`` mitnimmt, ist nicht gemessen.
- ``F``  der HTML-Teil der ``.eml``, die falzmarke für das Profil erzeugt.
- ``G``  der HTML-Teil der echten gesendeten Mail (Thunderbird hat ihn beim
         Senden umgeschrieben).

Vier Lagen:

1. hell — ``prefers-color-scheme: light``, Grund ``#ffffff``.
2. dunkel, die Mail schaltet um — ``prefers-color-scheme: dark``, Grund
   ``#1e1e1e`` (``farbe.GRUND_DUNKEL``); Medienabfragen und ``<picture>``
   greifen, Schrift ohne eigene Farbe wird hell (``CanvasText``).
3. dunkler Grund, die Mail bleibt — ``light``, Grund ``#1e1e1e``; keine
   Medienabfrage greift, Schrift ohne eigene Farbe bleibt schwarz.
4. Teilumkehrung wie Gmail/Outlook — NACHGESTELLT: aus Lage 1 werden helle
   Gründe dunkel (HSL-Helligkeit gespiegelt, L' = 1 - L) und dunkle Schrift- und
   Linienfarben hell, kontrasterhaltend: gleicher Ton, so hell, dass sie auf
   ``#1e1e1e`` den Kontrast erreichen, den sie auf Weiß hatten (höchstens Weiß).
   Bilder bleiben, Grund ``#1e1e1e``. Kein Programm
   legt seinen Algorithmus offen; die Lage zeigt die Richtung, keine
   Herstellermessung. ``[data-ogsc]`` wird nicht gesetzt (Gmail-Art).

Schwellen: Schrift 4,5:1, große Schrift (ab 24 px oder ab 18,66 px fett) 3:1,
Linie 3:1, Logo: mindestens die Hälfte der sichtbaren Bildpunkte mit 3:1 gegen
den Grund (``farbe.ANTEIL_MINDEST``, wie ``lint``). Emoji werden genauso
gemessen, aber getrennt gezählt: Sie sind Schmuck neben einem Text, der dasselbe
sagt, und WCAG 1.4.11 gilt für Schmuck nicht.

Ergebnis: die Tabelle in ``bericht.md`` zwischen den Marken
``<!-- tabelle:anfang -->`` und ``<!-- tabelle:ende -->`` (ohne Textauszüge; der Text
außerhalb der Marken bleibt, wie er ist). Bilder und ``messwerte.json`` zeigen echte
Absenderdaten und gehen deshalb nicht in dieses öffentliche Repository, sondern nach
``--belege`` (Vorgabe: ``messungen/`` neben dem Profilordner, beim Betreiber das private
Repository ``falzmarke-profile``).

Gegenprobe: ein synthetischer Prüfling mit ``#777`` auf ``#888`` und ein
dunkles Bild auf dunklem Grund müssen durchfallen, die Kontrolle ``#000`` auf
``#fff`` muss bestehen. Sonst bricht das Skript mit Exit 1 ab.
"""

from __future__ import annotations

import argparse
import base64
import email
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from email import policy
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WURZEL / "skill"))

from falzmarke import farbe  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

HIER = Path(__file__).resolve().parent
GRUND_HELL = "#ffffff"
GRUND_DUNKEL = "#1e1e1e"
BREITEN = (390, 700)

LAGEN = {
    1: ("hell", "light", GRUND_HELL, False),
    2: ("dunkel, Mail schaltet um", "dark", GRUND_DUNKEL, False),
    3: ("dunkler Grund, Mail bleibt", "light", GRUND_DUNKEL, False),
    4: ("Teilumkehrung (nachgestellt)", "light", GRUND_HELL, True),
}


#: Profile, die falzmarke als .eml erzeugt.
PROFILE = ["blitzsicht", "blitzsicht-erstkontakt", "siluri", "siluri-joe", "siluri-order",
           "gottl-gbr", "johannes-kueche", "johannes-privat"]

#: Signaturdateien, die Thunderbird bekommt (auch ohne falzmarke-Profil).
SIGNATURDATEIEN = ["blitzsicht", "blitzsicht-erstkontakt", "siluri", "siluri-joe",
                   "siluri-order", "siluri-bewerbung", "siluri-buchhaltung", "siluri-paypal",
                   "gottl-gbr"]

#: Nur Messung, kein Bild: per `varianten.py` aus siluri.html erzeugt, nur die Adresse anders.
OHNE_BILD = {"siluri-bewerbung", "siluri-buchhaltung", "siluri-paypal"}

ROLLEN = {"esig-name": "Name", "esig-position": "Position", "esig-label": "Label",
          "esig-link": "Link", "esig-company": "Firma", "esig-compliance": "Pflichtangabe/Hinweis"}

GEGENPROBE = """<!DOCTYPE html><html><head><meta name="color-scheme" content="light dark"></head>
<body><div class="moz-signature">
<p class="gp-falsch" style="color:#777777;background:#888888;font-size:14px">Gegenprobe #777 auf #888</p>
<p class="gp-kontrolle" style="color:#000000;background:#ffffff;font-size:14px">Kontrolle #000 auf #fff</p>
<div class="gp-linie" style="border-top:2px solid #888888;background:#777777;height:4px"></div>
<img class="gp-logo" src="GP_LOGO" alt="Gegenprobe" width="40" height="40">
</div></body></html>"""


# ── Messung im Browser ──────────────────────────────────────────────────────

JS_UMKEHRUNG = r"""
(grund) => {
  const p = c => { const m = c && c.match(/rgba?\(([^)]+)\)/); if (!m) return null;
    const v = m[1].split(',').map(parseFloat); return [v[0], v[1], v[2], v.length > 3 ? v[3] : 1]; };
  const hsl = ([r, g, b]) => { r/=255; g/=255; b/=255; const mx = Math.max(r,g,b), mn = Math.min(r,g,b);
    let h = 0, s = 0, l = (mx+mn)/2; if (mx !== mn) { const d = mx-mn; s = l > .5 ? d/(2-mx-mn) : d/(mx+mn);
    h = mx === r ? (g-b)/d + (g < b ? 6 : 0) : mx === g ? (b-r)/d + 2 : (r-g)/d + 4; h /= 6; } return [h, s, l]; };
  const rgb = ([h, s, l]) => { if (s === 0) { const v = Math.round(l*255); return [v,v,v]; }
    const q = l < .5 ? l*(1+s) : l+s-l*s, pp = 2*l-q;
    const f = t => { if (t < 0) t += 1; if (t > 1) t -= 1; if (t < 1/6) return pp+(q-pp)*6*t;
      if (t < 1/2) return q; if (t < 2/3) return pp+(q-pp)*(2/3-t)*6; return pp; };
    return [f(h+1/3), f(h), f(h-1/3)].map(x => Math.round(x*255)); };
  const um = c => { const [h, s, l] = hsl(c); return 'rgb(' + rgb([h, s, 1-l]).join(',') + ')'; };
  // Schrift und Linie: kontrasterhaltend. Dieselbe Farbe (Ton, Sättigung), so hell, dass sie
  // auf dem dunklen Grund den Kontrast hat, den sie auf Weiß hatte — höchstens Weiß. Eine
  // bloße Spiegelung der HSL-Helligkeit ließe gesättigtes Blau dunkel (#0000ee -> #1111ff,
  // 2:1) und erzeugte damit einen Befund, den die Messung selbst verursacht.
  const lum = ([r, g, b]) => { const f = x => { x /= 255; return x <= .04045 ? x/12.92 : Math.pow((x+.055)/1.055, 2.4); };
    return .2126*f(r) + .7152*f(g) + .0722*f(b); };
  const kon = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y)+.05)/(Math.min(x, y)+.05); };
  const dunkel = (() => { const m = grund.match(/[0-9a-f]{2}/gi); return m.map(x => parseInt(x, 16)); })();
  const hell = c => { const [h, s] = hsl(c); const ziel = kon(c, [255, 255, 255]);
    let lo = .5, hi = 1, best = rgb([h, s, 1]);
    for (let i = 0; i < 30; i++) { const m = (lo+hi)/2, k = rgb([h, s, m]);
      if (kon(k, dunkel) >= ziel) { best = k; hi = m; } else lo = m; }
    return 'rgb(' + best.join(',') + ')'; };
  const plan = [];
  for (const el of document.body.querySelectorAll('*')) {
    const cs = getComputedStyle(el);
    plan.push([el, p(cs.color), p(cs.backgroundColor),
      ['Top','Right','Bottom','Left'].map(s => [s, p(cs['border'+s+'Color']), parseFloat(cs['border'+s+'Width'])])]);
  }
  const bodyFarbe = p(getComputedStyle(document.body).color);
  for (const [el, c, bg, raender] of plan) {
    if (c && hsl(c)[2] < .5) el.style.setProperty('color', hell(c), 'important');
    else if (c) el.style.setProperty('color', 'rgb(' + c.slice(0,3).join(',') + ')', 'important');
    if (bg && bg[3] > 0 && hsl(bg)[2] > .5) el.style.setProperty('background-color', um(bg), 'important');
    for (const [s, rc, w] of raender) if (w > 0 && rc && hsl(rc)[2] < .5)
      el.style.setProperty('border-' + s.toLowerCase() + '-color', hell(rc), 'important');
  }
  if (bodyFarbe && hsl(bodyFarbe)[2] < .5) document.body.style.setProperty('color', hell(bodyFarbe), 'important');
  document.documentElement.style.setProperty('background-color', grund, 'important');
}
"""

JS_MESSUNG = r"""
() => {
  const p = c => { const m = c && c.match(/rgba?\(([^)]+)\)/); if (!m) return null;
    const v = m[1].split(',').map(parseFloat); return [v[0], v[1], v[2], v.length > 3 ? v[3] : 1]; };
  const grund = el => { const schicht = [];
    for (let e = el; e; e = e.parentElement) { const c = p(getComputedStyle(e).backgroundColor);
      if (c && c[3] > 0) { schicht.push(c); if (c[3] >= 1) break; } }
    let r = [0,0,0]; let start = true;
    for (const c of schicht.reverse()) { if (start) { r = c.slice(0,3); start = false; }
      else r = r.map((x, i) => x*(1-c[3]) + c[i]*c[3]); }
    return r.map(Math.round); };
  const sig = document.querySelector('.moz-signature');
  const inSig = el => !sig || sig.contains(el);
  const emoji = /\p{Extended_Pictographic}/u;
  const out = {text: [], linien: [], bilder: [], emoji: []};
  let n = 0;
  for (const el of document.body.querySelectorAll('*')) {
    const r = el.getBoundingClientRect(); if (r.width === 0 || r.height === 0) continue;
    const cs = getComputedStyle(el);
    const eigen = [...el.childNodes].filter(k => k.nodeType === 3).map(k => k.textContent).join('').replace(/\s+/g, ' ').trim();
    if (eigen) {
      const id = 'm' + (n++); el.setAttribute('data-messung', id);
      const reinEmoji = emoji.test(eigen) && !/[\p{L}\p{N}]/u.test(eigen);
      const eintrag = {id, tag: el.tagName.toLowerCase(), klassen: el.className && typeof el.className === 'string' ? el.className : '',
        text: eigen.slice(0, 40), farbe: p(cs.color).slice(0,3), grund: grund(el), groesse: parseFloat(cs.fontSize),
        gewicht: parseInt(cs.fontWeight), link: !!el.closest('a'), signatur: inSig(el),
        rolle: (el.closest('[class*="esig-"]') || {}).className || ''};
      (reinEmoji ? out.emoji : out.text).push(eintrag);
    }
    for (const s of ['Top','Right','Bottom','Left']) {
      const w = parseFloat(cs['border'+s+'Width']), st = cs['border'+s+'Style'];
      if (w > 0 && st !== 'none' && st !== 'hidden')
        out.linien.push({tag: el.tagName.toLowerCase(), seite: s, breite: w, farbe: p(cs['border'+s+'Color']).slice(0,3),
          grund: grund(el), signatur: inSig(el), klassen: typeof el.className === 'string' ? el.className : ''});
    }
    if (el.tagName === 'IMG') {
      const id = 'm' + (n++); el.setAttribute('data-messung', id);
      out.bilder.push({id, quelle: el.currentSrc || el.src, alt: el.alt, grund: grund(el.parentElement),
        geladen: el.complete && el.naturalWidth > 0, signatur: inSig(el)});
    }
  }
  return out;
}
"""


def hex_(rgb) -> str:
    return "#%02x%02x%02x" % tuple(int(x) for x in rgb[:3])


def kontrast(a, b) -> float:
    return farbe.kontrast(tuple(int(x) for x in a[:3]), tuple(int(x) for x in b[:3]))


def bild_anteil(daten: bytes, grund) -> tuple[float, list[tuple[str, float, float]]]:
    """Tragender Anteil über alle Bilder einer Animation (das schwächste zählt), dazu die
    zwei häufigsten deckenden Farben des ersten Bildes mit Anteil und Kontrast."""
    grund = tuple(int(x) for x in grund)
    anteile = []
    with Image.open(io.BytesIO(daten)) as bild:
        # Das erste Bild zuerst lesen: Nach `seek` durch eine Animation mit Palette gibt
        # Pillow für `seek(0)` nicht wieder dasselbe Bild zurück (gemessen 21.10.2026).
        roh = bild.convert("RGBA").tobytes()
        for nummer in range(getattr(bild, "n_frames", 1)):
            bild.seek(nummer)
            puffer = io.BytesIO()
            bild.convert("RGBA").save(puffer, "PNG")
            anteile.append(farbe.tragender_anteil(puffer.getvalue(), grund))
    zaehler: dict = {}
    for i in range(0, len(roh), 4):
        if roh[i + 3] >= farbe.DECKEND_AB:
            k = (roh[i] // 8 * 8, roh[i + 1] // 8 * 8, roh[i + 2] // 8 * 8)
            zaehler[k] = zaehler.get(k, 0) + 1
    gesamt = sum(zaehler.values()) or 1
    haeufig = sorted(zaehler.items(), key=lambda kv: -kv[1])[:2]
    farben = [(hex_(k), v / gesamt, kontrast(k, grund)) for k, v in haeufig]
    return min(anteile) if anteile else 0.0, farben


def glyph_anteil(png: bytes, grund) -> float:
    """Emoji: Anteil der Glyphenpunkte (≠ Grund) mit 3:1 gegen den Grund."""
    grund = tuple(int(x) for x in grund)
    with Image.open(io.BytesIO(png)) as bild:
        roh = bild.convert("RGB").tobytes()
    glyphe = traegt = 0
    for i in range(0, len(roh), 3):
        px = (roh[i], roh[i + 1], roh[i + 2])
        if sum(abs(px[k] - grund[k]) for k in range(3)) < 60:
            continue
        glyphe += 1
        if farbe.kontrast(px, grund) >= farbe.SCHWELLE:
            traegt += 1
    return traegt / glyphe if glyphe else 0.0


def rolle(e: dict) -> str:
    for klasse, name in ROLLEN.items():
        if klasse in (e.get("rolle") or "") or klasse in (e.get("klassen") or ""):
            return name
    if not e.get("signatur"):
        return "Rumpf-Text"
    return "Link" if e.get("link") else "Text"


# ── Prüflinge ───────────────────────────────────────────────────────────────


def html_aus_eml(pfad: Path) -> str:
    nachricht = email.message_from_bytes(pfad.read_bytes(), policy=policy.default)
    return nachricht.get_body(("html",)).get_content()


def erzeuge_eml(profil: str, profile: Path, ziel: Path) -> str:
    quelle = ziel / f"{profil}.md"
    quelle.write_text(
        f"---\ntyp: email\nprofil: {profil}\nan: Test <test@example.de>\n"
        f"betreff: Farbprobe {profil}\nanrede: Hallo Joe,\n---\n"
        "Testtext für die Farbmessung der Signatur. Ein [Link im Text](https://example.de) "
        "steht hier.\n\nViele Grüße\n", encoding="utf-8")
    umgebung = dict(os.environ, FALZMARKE_OEFFNEN="nie", FALZMARKE_GESENDET="nie",
                    FALZMARKE_POSTFACH="nie")
    subprocess.run([sys.executable, str(WURZEL / "skill/scripts/falzmarke.py"), "email",
                    str(quelle), "--profiles", str(profile), "-o", str(ziel / profil)],
                   check=True, env=umgebung, capture_output=True)
    return html_aus_eml(ziel / f"{profil}.eml")


def mit_grund(html: str, grund: str) -> str:
    """Den Grund des Programms nachstellen: `html` bekommt ihn, vor allem anderen Stil."""
    stil = f"<style>html{{background-color:{grund}}}</style>"
    if re.search(r"<head[^>]*>", html, re.I):
        return re.sub(r"(<head[^>]*>)", r"\1" + stil, html, count=1, flags=re.I)
    return stil + html


# ── Lauf ────────────────────────────────────────────────────────────────────


def bild_holen(url: str, ablage: Path) -> bytes:
    """Ein Logo per GET holen und zwischenlagern — nur lesen, nichts hochladen."""
    ablage.mkdir(parents=True, exist_ok=True)
    datei = ablage / re.sub(r"[^A-Za-z0-9.-]", "_", url.split("://", 1)[-1])
    if not datei.exists():
        with urllib.request.urlopen(url, timeout=15) as antwort:
            datei.write_bytes(antwort.read())
    return datei.read_bytes()


def stapeln(bahnen: list[tuple[str, bytes]], breite: int) -> Image.Image:
    schrift = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 13)
    bilder = [(t, Image.open(io.BytesIO(b)).convert("RGB")) for t, b in bahnen]
    hoehe = sum(b.height + 22 for _, b in bilder)
    ganz = Image.new("RGB", (breite, hoehe), "#d0d0d0")
    y = 0
    for titel, bild in bilder:
        ImageDraw.Draw(ganz).rectangle([0, y, breite, y + 21], fill="#ffe680")
        ImageDraw.Draw(ganz).text((6, y + 4), titel, fill="#000000", font=schrift)
        ganz.paste(bild, (0, y + 22))
        y += bild.height + 22
    return ganz


def miss(seite, kennung: str, html: str, lage: int, bilder_ablage: Path, bilder: dict,
         bildziel: Path | None) -> list[dict]:
    name, schema, grund, umkehren = LAGEN[lage]
    seite.emulate_media(color_scheme=schema)
    seite.set_viewport_size({"width": 700, "height": 600})
    seite.set_content(mit_grund(html, grund), wait_until="load")
    if umkehren:
        seite.evaluate(JS_UMKEHRUNG, GRUND_DUNKEL)
    roh = seite.evaluate(JS_MESSUNG)
    zeilen = []
    for e in roh["text"]:
        gross = e["groesse"] >= 24 or (e["groesse"] >= 18.66 and e["gewicht"] >= 700)
        schwelle = 3.0 if gross else 4.5
        k = kontrast(e["farbe"], e["grund"])
        zeilen.append(dict(element=rolle(e), art="Schrift", vorn=hex_(e["farbe"]),
                           hinten=hex_(e["grund"]), wert=k, schwelle=schwelle,
                           auszug=e["text"][:28], groesse=e["groesse"]))
    for e in roh["emoji"]:
        ort = seite.locator(f'[data-messung="{e["id"]}"]')
        anteil = glyph_anteil(ort.screenshot(), e["grund"])
        zeilen.append(dict(element="Emoji", art="Emoji", vorn="(Glyphe)", hinten=hex_(e["grund"]),
                           wert=anteil, schwelle=farbe.ANTEIL_MINDEST, auszug=e["text"],
                           groesse=e["groesse"]))
    for li in roh["linien"]:
        zeilen.append(dict(element=f"Linie {li['seite'].lower()} ({li['tag']} {li['breite']:g}px)",
                           art="Linie", vorn=hex_(li["farbe"]), hinten=hex_(li["grund"]),
                           wert=kontrast(li["farbe"], li["grund"]), schwelle=3.0, auszug="",
                           groesse=0))
    for b in roh["bilder"]:
        quelle = b["quelle"]
        if quelle.startswith("data:"):
            daten = base64.b64decode(quelle.split(",", 1)[1])
        else:
            daten = bild_holen(quelle, bilder_ablage)
        anteil, farben = bild_anteil(daten, b["grund"])
        beschr = ", ".join(f"{f} {a:.0%} {k:.2f}:1" for f, a, k in farben)
        zeilen.append(dict(element="Logo", art="Bild", vorn=quelle.rsplit("/", 1)[-1][:40],
                           hinten=hex_(b["grund"]), wert=anteil, schwelle=farbe.ANTEIL_MINDEST,
                           auszug=beschr, groesse=0, geladen=b["geladen"]))
    if bildziel is not None:
        for breite in BREITEN:
            seite.set_viewport_size({"width": breite, "height": 600})
            bilder.setdefault(breite, []).append((f"{lage} · {name}", seite.screenshot(full_page=True)))
    for z in zeilen:
        z.update(pruefling=kennung, lage=lage, bestanden=z["wert"] >= z["schwelle"] - 1e-9)
    return zeilen


def gruppiere(zeilen: list[dict]) -> list[dict]:
    """Gleiche Messung, gleiche Rolle → eine Zeile mit Anzahl."""
    gruppen: dict = {}
    for z in zeilen:
        schluessel = (z["pruefling"], z["lage"], z["element"], z["vorn"], z["hinten"],
                      z["schwelle"], z["auszug"] if z["art"] != "Schrift" else "")
        if schluessel not in gruppen:
            gruppen[schluessel] = dict(z, anzahl=0, auszuege=[])
        gruppen[schluessel]["anzahl"] += 1
        if z["auszug"] and z["auszug"] not in gruppen[schluessel]["auszuege"]:
            gruppen[schluessel]["auszuege"].append(z["auszug"])
    return list(gruppen.values())


def main() -> int:
    argumente = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    argumente.add_argument("--profile", type=Path,
                           default=Path("~/.config/falzmarke/profiles").expanduser())
    argumente.add_argument("--gesendet", type=Path, help="HTML-Teil der gesendeten Mail")
    argumente.add_argument("--ziel", type=Path, default=HIER)
    argumente.add_argument("--belege", type=Path,
                           help="Bilder und Rohwerte; Vorgabe: <Profilordner>/../messungen/"
                                + HIER.name)
    argumente.add_argument("--bilder-ablage", type=Path,
                           default=Path(tempfile.gettempdir()) / "signatur-farben-logos")
    a = argumente.parse_args()
    profile = a.profile.resolve()
    belege = (a.belege or profile.parent / "messungen" / HIER.name).resolve()

    prueflinge: list[tuple[str, str]] = []
    gp_logo = io.BytesIO()
    Image.new("RGBA", (40, 40), (0x22, 0x22, 0x22, 255)).save(gp_logo, "PNG")
    prueflinge.append(("Gegenprobe", GEGENPROBE.replace(
        "GP_LOGO", "data:image/png;base64," + base64.b64encode(gp_logo.getvalue()).decode())))
    for name in SIGNATURDATEIEN:
        prueflinge.append((f"Q {name}", (profile / "signatur" / f"{name}.html").read_text("utf-8")))
    with tempfile.TemporaryDirectory() as tmp:
        for name in PROFILE:
            prueflinge.append((f"F {name}", erzeuge_eml(name, profile, Path(tmp))))
    if a.gesendet:
        prueflinge.append(("G blitzsicht", a.gesendet.read_text("utf-8")))

    alle: list[dict] = []
    a.ziel.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        kontext = browser.new_context(device_scale_factor=1)
        seite = kontext.new_page()
        for kennung, html in prueflinge:
            name = kennung.split(" ", 1)[-1]
            ohne = kennung == "Gegenprobe" or name in OHNE_BILD
            ziel = None if ohne else belege
            bilder: dict = {}
            for lage in LAGEN:
                alle += miss(seite, kennung, html, lage, a.bilder_ablage, bilder, ziel)
            if ziel is not None:
                ziel.mkdir(parents=True, exist_ok=True)
                datei = kennung.replace(" ", "-").lower()
                for breite, bahnen in bilder.items():
                    # 256 Farben reichen fürs Ansehen; gemessen wird am DOM, nicht am Bild.
                    stapeln(bahnen, breite).quantize(256).save(
                        ziel / f"{datei}-{breite}.png", optimize=True)
        browser.close()

    # Gegenprobe: muss rot werden, Kontrolle muss grün bleiben.
    gp = [z for z in alle if z["pruefling"] == "Gegenprobe"]
    falsch = [z for z in gp if z["auszug"].startswith("Gegenprobe")]
    kontrolle = [z for z in gp if z["auszug"].startswith("Kontrolle") and z["lage"] == 1]
    linie = [z for z in gp if z["art"] == "Linie"]
    logo_dunkel = [z for z in gp if z["element"] == "Logo" and z["hinten"] == GRUND_DUNKEL]
    logo_hell = [z for z in gp if z["element"] == "Logo" and z["hinten"] == GRUND_HELL]
    pruefung = {
        "#777 auf #888 fällt in jeder Lage durch": len(falsch) == 4 and not any(z["bestanden"] for z in falsch),
        "#000 auf #fff besteht in Lage 1": len(kontrolle) == 1 and kontrolle[0]["bestanden"],
        "Linie #888 auf #777 fällt durch": bool(linie) and not any(z["bestanden"] for z in linie),
        "dunkles Bild auf #1e1e1e fällt durch": bool(logo_dunkel) and not any(z["bestanden"] for z in logo_dunkel),
        "dunkles Bild auf #ffffff besteht": bool(logo_hell) and all(z["bestanden"] for z in logo_hell),
    }
    belege.mkdir(parents=True, exist_ok=True)
    (belege / "messwerte.json").write_text(json.dumps(
        {"gegenprobe": pruefung, "zeilen": gruppiere(alle)}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    for satz, ok in pruefung.items():
        print(("OK    " if ok else "FEHLT ") + satz)
    if not all(pruefung.values()):
        print("Gegenprobe gescheitert — die Messung ist nichts wert.", file=sys.stderr)
        return 1
    zeilen = gruppiere(alle)
    durch = [z for z in zeilen if not z["bestanden"] and z["art"] != "Emoji"
             and z["pruefling"] != "Gegenprobe"]
    print(f"{len(alle)} Einzelmessungen, {len(zeilen)} Zeilen, "
          f"{len(durch)} Zeilen nicht bestanden (ohne Emoji und Gegenprobe)")
    tabelle_schreiben(a.ziel / "bericht.md", zeilen, pruefung)
    return 0


def tabelle_schreiben(bericht: Path, zeilen: list[dict], pruefung: dict) -> None:
    """Die volle Tabelle in `bericht.md`, zwischen den Marken."""
    def wert(z):
        if z["art"] in ("Bild", "Emoji"):
            return f"{z['wert']:.0%} tragen"
        return f"{z['wert']:.2f}:1".replace(".", ",")

    def schwelle(z):
        if z["art"] in ("Bild", "Emoji"):
            return f"≥ {z['schwelle']:.0%}"
        return f"≥ {z['schwelle']:.1f}:1".replace(".", ",")

    teile = ["| Prüfling | Lage | Element | Vorn | Grund | Wert | Schwelle | Ergebnis | Auszug |",
             "|---|---|---|---|---|---|---|---|---|"]
    for z in sorted(zeilen, key=lambda z: (z["pruefling"] != "Gegenprobe", z["pruefling"], z["lage"])):
        if z["bestanden"]:
            urteil = "bestanden"
        elif z["art"] == "Emoji":
            urteil = "nicht bestanden (Schmuck)"
        else:
            urteil = "**nicht bestanden**"
        # Textauszüge sind echte Absenderdaten und bleiben in den Belegen (privat).
        oeffentlich = z["pruefling"] == "Gegenprobe" or z["art"] in ("Bild", "Emoji")
        auszug = "; ".join(z["auszuege"])[:60].replace("|", "/") if oeffentlich else ""
        teile.append(f"| {z['pruefling']} | {z['lage']} | {z['element']} | {z['vorn']} | "
                     f"{z['hinten']} | {wert(z)} | {schwelle(z)} | {urteil} | {auszug} |")
    gp = "\n".join(f"- {'bestätigt' if ok else 'GESCHEITERT'}: {satz}" for satz, ok in pruefung.items())
    block = (f"<!-- tabelle:anfang -->\n_Erzeugt von `messung.py`, nicht von Hand ändern._\n\n"
             f"Gegenprobe:\n\n{gp}\n\n" + "\n".join(teile) + "\n<!-- tabelle:ende -->")
    text = bericht.read_text("utf-8") if bericht.exists() else "<!-- tabelle:anfang --><!-- tabelle:ende -->\n"
    text = re.sub(r"<!-- tabelle:anfang -->.*<!-- tabelle:ende -->", lambda _: block, text, flags=re.S)
    bericht.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
