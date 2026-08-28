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
keinen Code. Seit Dialekt 1.1 setzt der Briefsatz Überschriften; hierher kommen
sie trotzdem nicht — `markdown.py` lehnt sie bei `ziel="email"` ab, bevor der
Knoten entsteht, und `baum.NUR_BRIEF` hält fest, dass das kein Versehen ist.
Zitate und Code kommen mit den nächsten Teilvorgängen von #26 — dann
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

# ── Dunkles Farbschema ──────────────────────────────────────────────────────
#
# Die Farben sind FEST und kommen nicht aus dem Profil. Das ist keine
# Bequemlichkeit: Eine Markenfarbe, die auf Weiss traegt, traegt auf Dunkel
# selten — und ein Profil, das seine eigenen Dunkelfarben mitbringt, muesste
# jede davon gegen den dunklen Grund messen. Solange das niemand tut, sind
# abgestimmte Festwerte ehrlicher als eine Einstellung, die schiefgehen kann.
TINTE_DUNKEL = "#e8e8e8"
RAHMEN_DUNKEL = "#4a4a4a"
GEDAEMPFT_DUNKEL = "#a8a8a8"

#: Die Klassen, an denen die Umschaltung haengt. Inline-Stile haben hoehere
#: Spezifitaet als Klassen — ohne `!important` gewinnt der helle Wert.
KLASSE_TEXT = "fm-t"
KLASSE_LEISE = "fm-l"
KLASSE_LINIE = "fm-r"

#: Der EINZIGE `<style>`-Block, den eine erzeugte Nachricht tragen darf.
#:
#: ADR 0034 verbietet `<style>` sonst pauschal, und das bleibt so. Die Ausnahme
#: gibt es, weil Inline-Stile keine Medienabfrage tragen koennen — das ist eine
#: Eigenschaft der Sprache, keine Bequemlichkeit. Ohne sie erscheint jede
#: Nachricht in dunklen Clients als weisser Kasten.
#:
#: Zwei Mechanismen, nicht einer: `prefers-color-scheme` deckt Apple Mail und
#: Thunderbird ab, `[data-ogsc]` setzt Outlook stattdessen. Mit nur einem
#: bleibt genau ein Programm hell.
#:
#: Der Block ist eine **Konstante**. Nichts daran wird aus Eingabe oder Profil
#: zusammengesetzt, und `verstoesse()` vergleicht ihn Zeichen fuer Zeichen —
#: damit ist die Ausnahme nicht dehnbar.
DUNKELREGELN = f"""\
@media (prefers-color-scheme: dark) {{
  .{KLASSE_TEXT} {{ color: {TINTE_DUNKEL} !important; }}
  .{KLASSE_LEISE} {{ color: {GEDAEMPFT_DUNKEL} !important; }}
  .{KLASSE_LINIE} {{ border-color: {RAHMEN_DUNKEL} !important; }}
}}
[data-ogsc] .{KLASSE_TEXT} {{ color: {TINTE_DUNKEL} !important; }}
[data-ogsc] .{KLASSE_LEISE} {{ color: {GEDAEMPFT_DUNKEL} !important; }}
[data-ogsc] .{KLASSE_LINIE} {{ border-color: {RAHMEN_DUNKEL} !important; }}
"""

#: Genau das, was zwischen `<style>` und `</style>` steht. Erzeugung und
#: Prüfung nehmen DIESELBE Konstante — sonst scheitert der Vergleich an einem
#: Zeilenumbruch, und man baut sich eine Normalisierung ein, die die Ausnahme
#: wieder dehnbar macht.
STIL_INHALT = "\n" + DUNKELREGELN

#: Der Block, wie er im Dokument steht — inklusive der Marken drumherum.
STILBLOCK = f'<style type="text/css">{STIL_INHALT}</style>'


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
    return f'<p class="{KLASSE_TEXT}" style="margin: 0 0 {ABSTAND_UNTEN}; {TEXTSTIL}">{inhalt}</p>'


def liste(punkte: list[str], nummeriert: bool = False, start: int = 1) -> str:
    """`<ul>`/`<ol>`; verschachtelte Listen stecken schon in den Punkten."""
    zeilen = [
        f'<li class="{KLASSE_TEXT}" style="margin: 0 0 4px; {TEXTSTIL}">{p}</li>' for p in punkte
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
    if not zeilen:
        return ""
    # Alle Zeilen auf die breiteste bringen — wie im Text-Emitter. Eine Zeile
    # mit einer Zelle weniger ergäbe sonst eine Tabelle, in der eine Spalte
    # lautlos fehlt, während dieselbe Mail im Textteil eine leere Zelle zeigt.
    spalten = max(len(z) for z in zeilen)
    teile = [f'<table class="{KLASSE_TEXT}" style="{stil_tabelle}" '
             f'cellpadding="0" cellspacing="0">']
    for nummer, zeile in enumerate(zeilen):
        teile.append("<tr>")
        for spalte in range(spalten):
            inhalt = zeile[spalte] if spalte < len(zeile) else ""
            richtung = AUSRICHTUNG.get(
                ausrichtungen[spalte] if spalte < len(ausrichtungen) else None, "left"
            )
            stil = (f"border: 1px solid {RAHMEN}; padding: 5px 8px; "
                    f"text-align: {richtung}; {TEXTSTIL}")
            if nummer == 0:
                # Fett zusätzlich semantisch, nicht nur als Stil — wie in
                # emit.py. Wo das CSS nicht ankommt (Textansicht, Vorlesen),
                # bleibt der Kopf sonst ein Datensatz wie jeder andere.
                teile.append(f'<th class="{KLASSE_TEXT} {KLASSE_LINIE}" style="{stil} '
                             f'font-weight: 600;">{stark(inhalt)}</th>')
            else:
                teile.append(f'<td class="{KLASSE_TEXT} {KLASSE_LINIE}" '
                             f'style="{stil}">{inhalt}</td>')
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
        f"{STILBLOCK}\n"
        "</head>\n"
        f'<body class="{KLASSE_TEXT}" style="margin: 0; padding: 16px; {TEXTSTIL}">\n'
        f'<div style="max-width: {BREITE_MAX};">\n'
        f"{rumpf}"
        "</div>\n</body>\n</html>\n"
    )


# ── Die eigene Grenze, prüfbar ──────────────────────────────────────────────

#: Was in einer erzeugten Mail nicht vorkommen darf, mit dem Grund daneben.
#: Die Regel steht in ADR 0034, Punkt 4 — hier steht ihre Messung.
#:
#: `<style>` stand bis zum 28.08.2026 in dieser Liste. ADR 0034 verlangt das
#: nicht: Dort steht „keine externen Stylesheets", also `<link>`. Der pauschale
#: Ausschluss war eine Verschaerfung, die nie beschlossen wurde — und er machte
#: das dunkle Farbschema unmoeglich. Was jetzt gilt, steht in `_stilbloecke_pruefen`
#: und als Ergaenzung in ADR 0034.
VERBOTEN = (
    (r"<link\b", "externes Stylesheet oder externe Ressource"),
    (r"<script\b", "Skript"),
    (r"<iframe\b", "eingebettetes Fremddokument"),
    (r"background-image\s*:", "Hintergrundbild"),
    (r"url\(", "Verweis auf eine Ressource im Stil"),
)


def _stilbloecke_pruefen(html: str) -> list[str]:
    """`<style>` bleibt verboten — mit genau einer benannten Ausnahme.

    Die Ausnahme ist der Dunkelblock aus dieser Datei, und sie ist nicht
    dehnbar: Verglichen wird **Zeichen für Zeichen** gegen `DUNKELREGELN`.
    Nichts daran wird aus Eingabe oder Profil zusammengesetzt, also gibt es
    auch nichts zu deuten. Ein zweiter Block, ein geänderter Block, ein Block
    mit einer Deklaration mehr — alles bleibt ein Verstoß.

    Warum überhaupt eine Ausnahme: Inline-Stile können keine Medienabfrage
    tragen. Ohne sie erscheint jede Nachricht in dunklen Clients als weisser
    Kasten, und dunkle Clients sind der Normalfall. Der Grund für das Verbot
    war fremde Gestaltung, die den Text überlagert, und Regeln, die auf Inhalte
    greifen, die der Verfasser geschrieben hat — davon trifft ein Block, der
    ausschliesslich Farben umschaltet, nichts.

    Festgehalten als Ergänzung zu ADR 0034, nicht als stille Lockerung.
    """
    bloecke = re.findall(r"<style\b[^>]*>(.*?)</style>", html, re.IGNORECASE | re.DOTALL)
    if not bloecke:
        return []
    if len(bloecke) > 1:
        return [f"{len(bloecke)} Style-Blöcke — zulässig ist höchstens der Dunkelblock"]
    # Zeilenenden vereinheitlichen, und NUR die. Eine `.eml` reist mit CRLF —
    # das schreibt RFC 5322 so vor, und es passiert ohne Zutun des Werkzeugs.
    # `\r\n` und `\n` sind derselbe Inhalt; alles andere bleibt Zeichen für
    # Zeichen verglichen. Ohne diese eine Ausnahme meldete die Prüfung jede
    # versendete Nachricht als Verstoß gegen sich selbst.
    if bloecke[0].replace("\r\n", "\n") != STIL_INHALT:
        return ["Style-Block, der nicht der Dunkelblock des Werkzeugs ist"]
    return []


#: Eigenschaften, die im dunklen Schema umgeschaltet werden müssen. Wer sie
#: inline setzt, ohne die passende Klasse zu tragen, bleibt hell.
UMSCHALTPFLICHTIG = (("color:", (KLASSE_TEXT, KLASSE_LEISE)),
                     ("border-top:", (KLASSE_LINIE,)),
                     ("border:", (KLASSE_LINIE,)))


def nicht_umschaltbar(html: str) -> list[str]:
    """Elemente, die eine Farbe setzen, aber im Dunkeln hell blieben.

    Der Fehler, gegen den das gebaut ist: **halb umgeschaltet.** Beim
    Bildzeichen der Marke stand die helle Grundregel einmal nach der
    Medienabfrage — das Blatt schaltete um, die Kontur nicht. Im Kleinen sieht
    man so etwas nicht; man merkt es, wenn jemand die Mail im dunklen Client
    öffnet und die Hälfte fehlt.

    Geprüft wird die Form, nicht das Aussehen: Trägt ein Element eine Farbe
    inline, muss es auch die Klasse tragen, die sie umschaltet. Ein Renderer
    wäre hier keine Hilfe — es gibt keinen, der `[data-ogsc]` versteht.
    """
    offen = []
    for treffer in re.finditer(r"<(\w+)([^>]*)>", html):
        marke, attribute = treffer.group(0), treffer.group(2)
        stil = re.search(r'style="([^"]*)"', attribute)
        if not stil:
            continue
        klassen = re.search(r'class="([^"]*)"', attribute)
        vorhanden = set((klassen.group(1) if klassen else "").split())
        for eigenschaft, taugliche in UMSCHALTPFLICHTIG:
            if eigenschaft in stil.group(1) and not vorhanden & set(taugliche):
                offen.append(f"{marke[:56]} setzt `{eigenschaft}` ohne umschaltbare Klasse")
                break
    return offen


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
    gefunden.extend(_stilbloecke_pruefen(html))
    for treffer in re.finditer(r"<img\b[^>]*>", html, re.IGNORECASE):
        marke = treffer.group(0)
        if not re.search(r'\balt\s*=', marke, re.IGNORECASE):
            gefunden.append("Bild ohne Alternativtext")
        quelle = re.search(r'\bsrc\s*=\s*["\']([^"\']*)', marke, re.IGNORECASE)
        if quelle and not quelle.group(1).startswith(("cid:", "data:")):
            gefunden.append("Bild von außerhalb der Mail — auch ein Zählpixel ist eines")
    return gefunden
