#!/usr/bin/env python3
"""`verify --email`: misst die fertige Datei, nie die Absicht.

Dasselbe Versprechen wie beim PDF und aus demselben Grund. Ein Prüfer, der die
Eingabe liest und daraus schließt, was herausgekommen sein müsste, bestätigt
nur den eigenen Bauplan — er kann nicht rot werden, wenn der Emitter etwas
anderes tut, als er soll. Hier wird deshalb die `.eml` geöffnet, geparst und
gemessen; die Quelle wird nicht befragt.

**Was nicht in der Datei steht, wird nicht geprüft.** Ohne den optionalen
`text/markdown`-Teil (ADR 0034, Punkt 3) lässt sich nicht feststellen, ob Text-
und HTML-Teil den Brief vollständig wiedergeben — dann sagt der Bericht das,
statt die Prüfung stillschweigend zu überspringen. Eine übersprungene Prüfung,
die wie eine bestandene aussieht, ist schlimmer als keine.
"""

from __future__ import annotations

import email
import re
import unicodedata
from email import policy
from pathlib import Path

from falzmarke import emit_html
from falzmarke.geometrie import Bericht

#: RFC 5322: keine Zeile über 998 Zeichen. Darüber schneiden Server ab.
ZEILE_HART = 998

#: Bilder dürfen nur aus der Nachricht selbst kommen.
ERLAUBTE_QUELLEN = ("cid:", "data:")

#: Die Signaturtrennzeile nach RFC 3676 §4.3: zwei Striche, ein Leerzeichen.
#:
#: Sie steht hier ausgeschrieben und wird **nicht** aus `eml.py` importiert.
#: Ein Prüfer, der die Konstante des Erzeugers verwendet, kann nicht rot
#: werden, wenn der Erzeuger sie ändert — er bestätigt dann nur, dass beide
#: dasselbe meinen. Dasselbe Argument, mit dem die vendorte Layoutquelle in
#: `regeln/din5008.yaml` nicht als Beleg zählt.
SIGNATUR_TRENNER = "-- "


class EmlUnlesbar(ValueError):
    """Die Datei ist keine Nachricht — kein Grund für einen Traceback."""


def _lies(pfad: Path):
    roh = Path(pfad).read_bytes()
    if not roh.strip():
        raise EmlUnlesbar(f"{pfad.name} ist leer.")
    nachricht = email.message_from_bytes(roh, policy=policy.default)
    if not nachricht.get("From") and not nachricht.get("To"):
        raise EmlUnlesbar(
            f"{pfad.name} trägt weder From noch To — das ist keine E-Mail-Datei.")
    return nachricht


def _teil(nachricht, art: str):
    for teil in nachricht.walk():
        if teil.get_content_type() == art:
            return teil
    return None


def _normalisiert(text: str) -> str:
    """Für den Vergleich von Text- und HTML-Fassung.

    Verglichen werden Wörter, nicht Zeichen: Der eine Teil ist gefaltet, der
    andere in Absätze gesetzt, und geschützte Leerzeichen stehen mal so, mal
    so. Was gleich sein muss, ist der Wortlaut.
    """
    ohne_markup = re.sub(r"<[^>]+>", " ", text)
    entschaerft = (ohne_markup.replace("&amp;", "&").replace("&lt;", "<")
                   .replace("&gt;", ">").replace("&quot;", '"').replace("&#x27;", "'"))
    zusammen = unicodedata.normalize("NFKC", entschaerft)
    return " ".join(zusammen.split()).casefold()


def _woerter(text: str) -> set[str]:
    """Die Wortmenge eines Teils — für den Vergleich der Fassungen.

    Zwei Feinheiten, beide gemessen:

    * **Nur Tokens mit Buchstabe oder Ziffer.** `-` ist im Text ein
      Aufzählungspunkt und im HTML ein `<li>`, `--` der Signaturtrenner und im
      HTML gar nichts. Beides ist Markup, kein Wortlaut; es zu vergleichen
      meldet einen Unterschied, der keiner ist.
    * **Mengenvergleich, kein Substring.** `wort in text` findet auch, was nur
      Teil eines anderen Wortes ist — `-` etwa in „620-9800". Der Test wäre
      dann fast immer grün, und zwar aus dem falschen Grund.
    """
    return {w for w in _normalisiert(text).split() if any(z.isalnum() for z in w)}


# ── Die einzelnen Prüfungen ─────────────────────────────────────────────────

def _pruefe_aufbau(nachricht, bericht: Bericht) -> None:
    arten = [t.get_content_type() for t in nachricht.walk()
             if t.get_content_maintype() != "multipart"]
    koerper = [a for a in arten if not a.startswith("application/")
               and not a.startswith("image/")]

    bericht.wahr("Textteil vorhanden", "text/plain" in arten, "text/plain", ", ".join(arten))
    bericht.wahr("HTML-Teil vorhanden", "text/html" in arten, "text/html", ", ".join(arten))

    # Die Reihenfolge ist nicht kosmetisch: In multipart/alternative gilt der
    # LETZTE Teil als der reichste. Stünde der Text hinten, zeigte jeder Client
    # den Klartext statt des HTML.
    if "text/plain" in koerper and "text/html" in koerper:
        bericht.wahr(
            "Reihenfolge der Alternativen",
            koerper.index("text/plain") < koerper.index("text/html"),
            "text/plain vor text/html", " vor ".join(koerper))

    bericht.wahr("Keine Message-ID", nachricht.get("Message-ID") is None,
                 "nicht gesetzt", nachricht.get("Message-ID") or "nicht gesetzt")

    for name in ("From", "To", "Subject"):
        bericht.wahr(f"Kopfzeile {name}", bool(nachricht.get(name)),
                     "gesetzt", nachricht.get(name) or "fehlt")


def _pruefe_textteil(teil, bericht: Bericht) -> None:
    if teil is None:
        return
    bericht.wahr("Zeichensatz des Textteils", (teil.get_content_charset() or "") == "utf-8",
                 "utf-8", teil.get_content_charset() or "nicht gesetzt")
    kodierung = (teil["Content-Transfer-Encoding"] or "").lower()
    # base64 im Textteil macht die Rohansicht unlesbar — und die Rohansicht ist
    # das, was von einer .eml als Vorlage übrig bleibt.
    bericht.wahr("Transfer-Encoding des Textteils", kodierung != "base64",
                 "nicht base64", kodierung or "nicht gesetzt")
    bericht.wahr("format=flowed", teil.get_param("format") == "flowed",
                 "flowed", teil.get_param("format") or "nicht gesetzt")
    bericht.wahr("delsp gesetzt", teil.get_param("delsp") in ("yes", "no"),
                 "yes oder no", teil.get_param("delsp") or "nicht gesetzt")

    text = teil.get_content()
    zeilen = text.split("\n")
    laengste = max((len(z) for z in zeilen), default=0)
    bericht.add("Zeilenlänge im Textteil", f"<= {ZEILE_HART}", str(laengste), "—",
                laengste <= ZEILE_HART)

    # Space-Stuffing: Eine Zeile, die mit '>' beginnt, läse der Empfänger als
    # Zitat. Sie muss ein vorangestelltes Leerzeichen tragen.
    ungestufft = [z for z in zeilen if z.startswith(">")]
    bericht.wahr("Space-Stuffing", not ungestufft, "keine Zeile beginnt mit >",
                 f"{len(ungestufft)} Zeile(n)" if ungestufft else "keine")

    bericht.wahr("Signaturtrenner", f"\n{SIGNATUR_TRENNER}\n" in f"\n{text}",
                 SIGNATUR_TRENNER.replace(" ", "␣"),
                 "vorhanden" if SIGNATUR_TRENNER in text else "fehlt")


def _pruefe_htmlteil(teil, bericht: Bericht) -> None:
    if teil is None:
        return
    html = teil.get_content()
    bericht.wahr("Zeichensatz des HTML-Teils", (teil.get_content_charset() or "") == "utf-8",
                 "utf-8", teil.get_content_charset() or "nicht gesetzt")

    # Dieselbe Messung, die der Emitter an sich selbst anlegt (ADR 0034, Punkt
    # 4). Sie steht dort, damit sie beim Erweitern greift, und wird hier auf
    # die fertige Datei angewendet — die Fassung, die tatsächlich ankommt.
    verstoesse = emit_html.verstoesse(html)
    bericht.wahr("Keine verbotenen Bestandteile", not verstoesse,
                 "keine", "; ".join(verstoesse) if verstoesse else "keine")

    bericht.wahr("Sprache ausgezeichnet", bool(re.search(r"<html[^>]+\blang=", html)),
                 "lang gesetzt", "gesetzt" if "lang=" in html else "fehlt")
    bericht.wahr("Breite begrenzt", "max-width" in html, "max-width vorhanden",
                 "vorhanden" if "max-width" in html else "fehlt")

    # Ein 1×1-Bild ist keine Abbildung, sondern eine Messung am Empfänger.
    zaehlpixel = re.findall(r'<img\b[^>]*\b(?:width|height)\s*=\s*["\']?1["\']?', html, re.I)
    bericht.wahr("Kein Zählpixel", not zaehlpixel, "keins",
                 f"{len(zaehlpixel)} gefunden" if zaehlpixel else "keins")

    # Eine Tabelle ohne <th> ist im Zweifel Layout, keine Daten. Layout in
    # Tabellen liest jeder Screenreader als Datensatz vor.
    tabellen = re.findall(r"<table\b.*?</table>", html, re.I | re.S)
    ohne_kopf = [t for t in tabellen if "<th" not in t.lower()]
    bericht.wahr("Tabellen sind Datentabellen", not ohne_kopf,
                 "jede Tabelle mit <th>",
                 f"{len(ohne_kopf)} ohne <th>" if ohne_kopf else "alle mit <th>")


def _pruefe_gleichlaut(text_teil, html_teil, bericht: Bericht) -> None:
    """Text und HTML müssen dasselbe sagen.

    Sonst liest der eine Empfänger etwas anderes als der andere — und welche
    Fassung ankommt, entscheidet sein Programm, nicht der Absender.
    """
    if text_teil is None or html_teil is None:
        return
    fehlend = sorted(_woerter(text_teil.get_content()) - _woerter(html_teil.get_content()))
    bericht.add("Text und HTML sagen dasselbe", "kein Wort fehlt",
                f"{len(fehlend)} Wort(e) fehlen" if fehlend else "gleich", "—", not fehlend)


def _pruefe_quellteil(nachricht, text_teil, html_teil, bericht: Bericht) -> None:
    quelle = _teil(nachricht, "text/markdown")
    if quelle is None:
        # Ausdrücklich gemeldet statt übersprungen: Eine Prüfung, die fehlt,
        # darf nicht wie eine aussehen, die bestanden wurde.
        bericht.add("Vollständigkeit gegen die Quelle", "text/markdown-Teil",
                    "nicht enthalten — nicht prüfbar", "—", True)
        return
    bericht.wahr("Quellteil ist CommonMark", quelle.get_param("variant") == "CommonMark",
                 "CommonMark", quelle.get_param("variant") or "nicht gesetzt")

    roh = quelle.get_content()
    ohne_frontmatter = roh.split("\n---", 2)[-1] if roh.startswith("---") else roh
    woerter = {w for w in _woerter(ohne_frontmatter) if len(w) > 3}
    for name, teil in (("Textteil", text_teil), ("HTML-Teil", html_teil)):
        if teil is None:
            continue
        fehlend = sorted(woerter - _woerter(teil.get_content()))
        bericht.add(f"Quelle vollständig im {name}", "kein Wort fehlt",
                    f"{len(fehlend)} fehlen" if fehlend else "vollständig", "—", not fehlend)


def _pruefe_anhaenge(nachricht, bericht: Bericht) -> None:
    anhaenge = [t for t in nachricht.walk() if t.get_filename()]
    if not anhaenge:
        return
    gesamt = sum(len(t.get_content()) for t in anhaenge)
    bericht.wahr("Anhänge tragen Dateinamen", all(t.get_filename() for t in anhaenge),
                 "jeder benannt", f"{len(anhaenge)} Anhang/Anhänge")
    bericht.add("Gesamtgröße der Anhänge", "<= 10 MB",
                f"{gesamt / 1_048_576:.1f} MB", "—", gesamt <= 10 * 1_048_576)


def pruefe(pfad: Path) -> Bericht:
    """Öffnet die `.eml` und misst sie."""
    nachricht = _lies(Path(pfad))
    bericht = Bericht(gegenstand="Prüfungen bestanden")

    _pruefe_aufbau(nachricht, bericht)
    text_teil = _teil(nachricht, "text/plain")
    html_teil = _teil(nachricht, "text/html")
    _pruefe_textteil(text_teil, bericht)
    _pruefe_htmlteil(html_teil, bericht)
    _pruefe_gleichlaut(text_teil, html_teil, bericht)
    _pruefe_quellteil(nachricht, text_teil, html_teil, bericht)
    _pruefe_anhaenge(nachricht, bericht)
    return bericht
