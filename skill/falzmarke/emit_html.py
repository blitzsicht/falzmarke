#!/usr/bin/env python3
"""Erzeugt E-Mail-HTML aus dem geprüften Markdown-Baum.

Derselbe Baum wie in `emit.py`, andere Zielsprache. Was hier steht, ist nicht
eine zweite Prüfung — geprüft hat `markdown.py`, und was diese Prüfung ablehnt,
hat in `baum.py` keinen Knoten. Dieser Emitter setzt nur.

**Der Stil steht inline an jedem Element.** Kein `<style>`-Block, kein externes
Stylesheet: Gmail entfernt `<style>` in der Weiterleitungsansicht, Outlook lädt
nichts von außen, und was nicht ankommt, kann man nicht prüfen. Der Preis ist
ein wortreiches HTML — er wird bezahlt, weil das Ergebnis in Outlook, Gmail und
Apple Mail gleich aussieht.

**Der Stil erbt nicht.** Jeder Block trägt Schrift, Größe, Zeilenhöhe und Farbe
selbst, obwohl ein Container das könnte. Mehrere Clients hängen den Rumpf in
ihre eigene Umgebung, und dabei geht die Vererbung verloren.

Was der Dialekt nicht kennt, kommt hier auch nicht vor: Es gibt keine Links
(`link` steht nicht in `markdown.ERLAUBT`), keine Überschriften, keine Zitate,
keinen Code. Überschriften, Zitate und Code kommen mit Dialekt 1.1 (#26) — dann
hier ergänzt, nicht vorher auf Vorrat.

Die Grenzen aus ADR 0034 gelten: keine Spalten, keine Buttons, keine Zählpixel,
keine Hintergrundbilder, keine Skripte, keine externen Stylesheets.
"""

from __future__ import annotations

import html as html_modul
import re

from falzmarke import baum as baum_modul
from falzmarke import typografie

#: Systemschriften. Kein Webfont — der käme von außen und wird geblockt.
SCHRIFTSTAPEL = "-apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
TINTE = "#1a1a1a"
RAHMEN = "#c8c8c8"
BREITE_MAX = "600px"

#: An jedem Block wiederholt, weil die Vererbung in Mail-Clients unzuverlässig ist.
TEXTSTIL = f"font-family: {SCHRIFTSTAPEL}; font-size: 16px; line-height: 1.45; color: {TINTE};"

ABSTAND_UNTEN = "12px"


def as_text(text: str, typografie_anwenden: bool = True) -> str:
    """Ein Textknoten als HTML-Text.

    Erst die Typografie, dann das Escaping — nie umgekehrt: `anwenden()` setzt
    geschützte Leerzeichen und Striche, und die dürfen nicht als Entity-Reste
    aus einem vorher escapten Text herausgelesen werden.
    """
    if typografie_anwenden:
        text = typografie.anwenden(text)
    return html_modul.escape(text, quote=True)


def stark(inhalt: str) -> str:
    return f"<strong>{inhalt}</strong>"


def betont(inhalt: str) -> str:
    return f"<em>{inhalt}</em>"


def umbruch() -> str:
    return "<br>"


def absatz(inhalt: str) -> str:
    return f'<p style="margin: 0 0 {ABSTAND_UNTEN}; {TEXTSTIL}">{inhalt}</p>'


def liste(punkte: list[str], nummeriert: bool = False, start: int = 1) -> str:
    """`<ul>`/`<ol>`; verschachtelte Listen stecken schon in den Punkten."""
    zeilen = [
        f'<li style="margin: 0 0 4px; {TEXTSTIL}">{p}</li>' for p in punkte
    ]
    stil = f"margin: 0 0 {ABSTAND_UNTEN}; padding-left: 22px; {TEXTSTIL}"
    if nummeriert:
        # start="1" wäre die Vorgabe und nur Rauschen im Quelltext.
        zusatz = f' start="{start}"' if start != 1 else ""
        return f'<ol{zusatz} style="{stil}">' + "".join(zeilen) + "</ol>"
    return f'<ul style="{stil}">' + "".join(zeilen) + "</ul>"


#: Wie in `emit.py`: was die Trennzeile nicht sagt, wird linksbündig.
AUSRICHTUNG = {"left": "left", "right": "right", "center": "center", None: "left", "": "left"}


def tabelle(zeilen: list[list[str]], ausrichtungen: list[str | None]) -> str:
    """Kopfzeile fett, sichtbarer Rahmen, Ausrichtung je Spalte."""
    stil_tabelle = (
        f"border-collapse: collapse; margin: 0 0 {ABSTAND_UNTEN}; {TEXTSTIL}"
    )
    teile = [f'<table style="{stil_tabelle}" cellpadding="0" cellspacing="0">']
    for nummer, zeile in enumerate(zeilen):
        teile.append("<tr>")
        for spalte, inhalt in enumerate(zeile):
            richtung = AUSRICHTUNG.get(
                ausrichtungen[spalte] if spalte < len(ausrichtungen) else None, "left"
            )
            stil = f"border: 1px solid {RAHMEN}; padding: 5px 8px; text-align: {richtung}; {TEXTSTIL}"
            if nummer == 0:
                teile.append(f'<th style="{stil} font-weight: 600;">{inhalt}</th>')
            else:
                teile.append(f'<td style="{stil}">{inhalt}</td>')
        teile.append("</tr>")
    teile.append("</table>")
    return "".join(teile)


# ── Der Weg über den Baum ───────────────────────────────────────────────────


def _inline(knoten) -> str:
    if isinstance(knoten, tuple):
        return "".join(_inline(k) for k in knoten)
    if isinstance(knoten, baum_modul.Text):
        return as_text(knoten.inhalt, typografie_anwenden=knoten.typografie)
    if isinstance(knoten, baum_modul.Umbruch):
        return umbruch()
    if isinstance(knoten, baum_modul.Stark):
        return stark(_inline(knoten.kinder))
    if isinstance(knoten, baum_modul.Betont):
        return betont(_inline(knoten.kinder))
    return _block(knoten)


def _block(knoten) -> str:
    if isinstance(knoten, baum_modul.Absatz):
        return absatz(_inline(knoten.kinder))
    if isinstance(knoten, baum_modul.Liste):
        return liste(
            [_inline(p) for p in knoten.punkte],
            nummeriert=knoten.nummeriert,
            start=knoten.start,
        )
    if isinstance(knoten, baum_modul.Tabelle):
        return tabelle(
            [[_inline(z) for z in zeile] for zeile in knoten.zeilen],
            list(knoten.ausrichtungen),
        )
    # Kein stilles Uebergehen — derselbe Grund wie im Typst-Emitter: ein leerer
    # Absatz in einer Mail, die jemand abschickt, faellt niemandem auf.
    raise TypeError(
        f"Der HTML-Emitter kennt {type(knoten).__name__} nicht. "
        "Neuer Knoten in baum.py? Dann gehört er auch hierher."
    )


def setze(bloecke) -> str:
    """Geprüfter Baum -> HTML-Rumpf, ohne Hülle.

    Wie `emit.setze()` nur der Brieftext. Anrede, Grußformel und Signatur kommen
    aus dem Profil und werden in #63 um diesen Rumpf herumgelegt.
    """
    gesetzt = [_block(b) for b in bloecke]
    return "\n".join(b for b in gesetzt if b.strip()) + "\n"


def dokument(rumpf: str, sprache: str = "de") -> str:
    """Der Rumpf in einer vollständigen HTML-Datei.

    `color-scheme` sagt dem Client, dass die Seite beide Modi verträgt — ohne
    die Angabe invertieren einige den Text und lassen den Hintergrund stehen.
    """
    return (
        f'<!DOCTYPE html>\n<html lang="{html_modul.escape(sprache, quote=True)}">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<meta name="color-scheme" content="light dark">\n'
        "</head>\n"
        f'<body style="margin: 0; padding: 16px; {TEXTSTIL}">\n'
        f'<div style="max-width: {BREITE_MAX};">\n'
        f"{rumpf}"
        "</div>\n</body>\n</html>\n"
    )


# ── Die eigene Grenze, prüfbar ──────────────────────────────────────────────

#: Was in einer erzeugten Mail nicht vorkommen darf, mit dem Grund daneben.
#: Die Regel steht in ADR 0034, Punkt 4 — hier steht ihre Messung.
VERBOTEN = (
    (r"<link\b", "externes Stylesheet oder externe Ressource"),
    (r"<style\b", "Style-Block statt Inline-Stil"),
    (r"<script\b", "Skript"),
    (r"<iframe\b", "eingebettetes Fremddokument"),
    (r"background-image\s*:", "Hintergrundbild"),
    (r"url\(", "Verweis auf eine Ressource im Stil"),
)


def verstoesse(html: str) -> list[str]:
    """Prüft erzeugtes HTML gegen die Grenzen aus ADR 0034.

    Sie steht hier und nicht im Lint, weil ein Emitter seine eigene Grenze
    kennen soll: Wer sie beim Erweitern überschreitet, merkt es an dieser
    Stelle und nicht erst beim Ausliefern. Der vollständige Regelsatz E7xx mit
    Meldungstexten und Fundstellen gehört zu #64 und ruft diese Funktion auf.

    **Was sie nicht prüft:** ob das Ergebnis gut aussieht, ob eine Tabelle als
    Spaltenlayout missbraucht wird, ob ein Link wie ein Button gestaltet ist.
    Das sind Urteile, keine Messungen — sie stehen in ADR 0034 als Regel, aber
    nicht hier als Prüfung.
    """
    gefunden = []
    for muster, grund in VERBOTEN:
        if re.search(muster, html, re.IGNORECASE):
            gefunden.append(grund)
    for treffer in re.finditer(r"<img\b[^>]*>", html, re.IGNORECASE):
        marke = treffer.group(0)
        if not re.search(r'\balt\s*=', marke, re.IGNORECASE):
            gefunden.append("Bild ohne Alternativtext")
        quelle = re.search(r'\bsrc\s*=\s*["\']([^"\']*)', marke, re.IGNORECASE)
        if quelle and not quelle.group(1).startswith(("cid:", "data:")):
            gefunden.append("Bild von außerhalb der Mail — auch ein Zählpixel ist eines")
    return gefunden
