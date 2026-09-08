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
#: Die Lesebreite des Fließtextes — und nur seine.
#:
#: Bis #264 deckelte diese Breite die GANZE Nachricht: Der Umschlag trug
#: `width="600"` und `max-width: 600px`, und alles darin wurde hineingequetscht.
#: Bei einer Datentabelle mit vier Spalten reicht das nicht — gemessen am
#: 08.09.2026 in Outlook für Mac brach die Kopfzelle „Datum" mitten im Wort und
#: der Betrag zwischen Zahl und Währung, während das Fenster mehr als doppelt so
#: breit war. Der Platz war da, der Deckel ließ ihn nicht durch.
#:
#: Deshalb gilt die Grenze jetzt dort, wo sie hergehört: an Absätzen und Listen,
#: deren Zeilen sonst zu lang zum Lesen würden. Tabellen tragen sie nicht — eine
#: Tabelle ist so breit, wie ihre Spalten es verlangen.
LESEBREITE = "640px"

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
    return (f'<p class="{KLASSE_TEXT}" style="margin: 0 0 {ABSTAND_UNTEN}; '
            f'max-width: {LESEBREITE}; {TEXTSTIL}">{inhalt}</p>')


def liste(punkte: list[str], nummeriert: bool = False, start: int = 1) -> str:
    """`<ul>`/`<ol>`; verschachtelte Listen stecken schon in den Punkten."""
    zeilen = [
        f'<li class="{KLASSE_TEXT}" style="margin: 0 0 4px; {TEXTSTIL}">{p}</li>' for p in punkte
    ]
    stil = (f"margin: 0 0 {ABSTAND_UNTEN}; padding-left: 22px; "
            f"max-width: {LESEBREITE}; {TEXTSTIL}")
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
            # `word-break: normal` steht hier, obwohl es der Vorgabewert der
            # Sprache ist: Gemessen am 08.09.2026 trennte Outlook für Mac die
            # Kopfzelle „Datum" mitten im Wort, sobald die Spalte schmaler war
            # als ihr Inhalt. Ein Client, der `break-word` von sich aus setzt,
            # wird damit überstimmt — lieber eine Spalte, die breiter wird, als
            # ein Wort, das entzweigeht.
            #
            # Rechtsbündig heißt in einer Datentabelle nach DIN 5008: Zahlen.
            # Die brechen nicht zwischen Wert und Einheit. Das ist bewusst
            # KEINE Ersetzung im Text — das geschützte Leerzeichen vor „EUR"
            # steht auf einer Einzelquelle und darf deshalb nicht automatisch
            # gesetzt werden (`regeln.darf_automatisch_ersetzen`). Was hier
            # steht, ändert die Darstellung, nicht die Zeichen.
            stil = (f"border: 1px solid {RAHMEN}; padding: 5px 8px; "
                    f"text-align: {richtung}; word-break: normal; "
                    f"overflow-wrap: normal; {TEXTSTIL}")
            if richtung == "right":
                stil += " white-space: nowrap;"
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


def link(ziel: str, inhalt: str) -> str:
    """Ein `<a>` — ohne Nachverfolgung und ohne Umleitung.

    Kein `utm_`-Anhang, kein Zaehlpixel, keine Weiterleitung ueber einen
    eigenen Dienst: Der Empfaenger bekommt die Adresse, die der Absender
    geschrieben hat. Das ist dieselbe Zusage wie beim Logo — eine erzeugte
    Nachricht laedt nichts von aussen und meldet nichts nach Hause (ADR 0034).

    Die Farbe steht inline und schaltet mit `KLASSE_TEXT` um: Ein Link in
    Systemblau steht auf dunklem Grund bei 2,3:1 und ist dort kaum zu lesen.
    `text-decoration: underline` bleibt, damit er auch ohne Farbe erkennbar
    ist — Farbe allein ist nach WCAG 1.4.1 kein Unterscheidungsmerkmal.
    """
    return (f'<a href="{as_text(ziel, typografie_anwenden=False)}" '
            f'class="{KLASSE_TEXT}" style="color: inherit; '
            f'text-decoration: underline;">{inhalt}</a>')


def _inline(knoten) -> str:
    if isinstance(knoten, tuple):
        return "".join(_inline(k) for k in knoten)
    if isinstance(knoten, baum_modul.Text):
        return as_text(knoten.inhalt, typografie_anwenden=knoten.typografie)
    if isinstance(knoten, baum_modul.Umbruch):
        return umbruch()
    if isinstance(knoten, baum_modul.Link):
        return link(knoten.ziel, _inline(knoten.kinder))
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


def dokument(rumpf: str, sprache: str = "de", vorspann: str = "") -> str:
    """Der Rumpf in einer vollständigen HTML-Datei.

    `color-scheme` sagt dem Client, dass die Seite beide Modi verträgt — ohne
    die Angabe invertieren einige den Text und lassen den Hintergrund stehen.

    `vorspann` steht im Umschlag über dem Rumpf und ist nur für die
    `.html`-Vorschau gedacht (An, Kopie, Betreff). Er ist ein Parameter und
    keine nachträgliche Ersetzung: Bis Issue #104 schnitt `eml.begleit_html`
    den Kopf mit `str.replace` an einer Zeichenkette ein, die den Umschlag
    beschrieb. Als der Umschlag zur Tabelle wurde, traf die Ersetzung ins
    Leere und der Vorschaukopf verschwand **stillschweigend** — gefangen hat
    es ein Test, nicht der Emitter.
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
        # Umschlag als Tabelle, nicht als `div` (Issue #104): Das klassische
        # Outlook rechnet mit der Word-Engine und versteht von den beiden
        # Breitenangaben nur das Attribut. Beide sagen jetzt dasselbe — die
        # Nachricht nimmt die Breite, die das Fenster hergibt.
        #
        # Bis #264 stand hier `width="600"`, `max-width: 600px` und
        # `align="center"`. Der Deckel quetschte Datentabellen (siehe
        # `LESEBREITE`), und die Zentrierung war ein Newsletter-Idiom, das nie
        # begründet wurde: Sie setzte die Nachricht mittig ins Fenster, während
        # die Signatur, die das Mailprogramm darunter anfügt, am linken Rand
        # beginnt — zwei Ausrichtungen in einem Fenster. Ein Geschäftsbrief
        # beginnt links.
        #
        # `role="presentation"` ist Pflicht und nicht Zierde: Ohne die Marke
        # liest ein Screenreader den Umschlag als Datensatz vor, und die
        # Prüfung in `verstoesse` lehnt ihn ab.
        f'<table role="presentation" width="100%" align="left" '
        f'cellpadding="0" cellspacing="0" border="0" '
        f'style="width: 100%; border-collapse: collapse;">\n'
        f'<tr><td style="padding: 0;">\n'
        f"{vorspann}{rumpf}"
        "</td></tr>\n</table>\n</body>\n</html>\n"
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
    (r"<form\b", "Formular"),
    # Ereignis-Attribute sind Skript ohne `<script>`. Die Liste ist bewusst
    # eng: `\bon[a-z]+\s*=` traefe auch `<td on...>` in einem Wort wie
    # `one=`, deshalb das Wortgrenzen-`\s` davor.
    (r"\son[a-z]+\s*=", "Ereignis-Attribut — Skript ohne script-Element"),
    (r"background-image\s*:", "Hintergrundbild"),
    (r"url\(", "Verweis auf eine Ressource im Stil"),
)


#: Wie viele Bilder eine erzeugte Mail tragen darf.
#:
#: ADR 0034, Punkt 4: „Bilder nur als eingebettete Ressource mit Alt-Text, und
#: auch das nur für das Logo des Profils." Gemessen hat das bis #243 **niemand**
#: — drei Bilder mit `cid:` wären anstandslos durchgegangen.
#:
#: Die Zahl steht hier, seit die Quellenregel gefallen ist. Bis dahin hielt
#: `cid:`-only die Grenze nebenbei mit: Was in der Nachricht steckt, muss dort
#: erst hineingelegt werden. Seit `email.logo` auch eine Adresse und eine
#: Data-URI nimmt, kostet ein zusätzliches Bild nichts mehr — und dann ist die
#: Anzahl das Einzige, was zwischen einer Signatur und einem Werbebrief steht.
BILDER_MAX = 1

#: Ein 1×1-Bild ist keine Abbildung, sondern eine Messung am Empfänger.
#:
#: Der Wert muss GANZ „1" sein. Bis Issue #104 stand hier `["\']?1["\']?` ohne
#: Abschluss, und das traf die führende Ziffer jeder Breite, die mit 1 beginnt:
#: `width="120"` galt als Zählpixel. Aufgefallen ist es erst, als das Logo Maße
#: bekam — vorher trug kein erzeugtes Bild eine Breite, und die Prüfung konnte
#: gar nicht falsch anschlagen.
ZAEHLPIXEL = re.compile(
    r'<img\b[^>]*\b(?:width|height)\s*=\s*(?:"1"|\'1\'|1)(?=[\s>])', re.IGNORECASE)


def zaehlpixel(html: str) -> list[str]:
    """Bilder, die als Messung am Empfänger taugen.

    Steht seit #243 hier statt nur in `pruefung_eml`: Solange `verstoesse()`
    fremde Bildquellen pauschal ablehnte, fiel ein Zählpixel dort schon als
    „Bild von außerhalb" auf — die 1×1-Messung war der zweite Zaun hinter dem
    ersten. Mit der Quellenregel ist der erste Zaun weg, und ein einzelnes
    externes 1×1-Bild wäre für den Emitter unsichtbar geworden.

    Eine Funktion, zwei Aufrufer — wie bei `_layouttabellen_pruefen`. Zwei
    Fassungen derselben Regel laufen auseinander, und `pruefung_eml` sagt das
    an genau dieser Stelle schon über die Tabellen.
    """
    return ZAEHLPIXEL.findall(html)


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
#:
#: `border-left:` steht seit #243 dabei — die senkrechte Linie zwischen Logo
#: und Angaben setzt eine Farbe wie jede andere. Ohne den Eintrag hätte diese
#: Prüfung an genau der Stelle nie rot werden können, an der die neue Linie
#: entsteht: `"border:" in stil` trifft `border-left:` nicht, weil dazwischen
#: ein Bindestrich steht und kein Doppelpunkt.
#: `background-color:` steht mit LEERER Klassenliste da: Es gibt keine, die ihn
#: umschaltet — `DUNKELREGELN` kennt nur Text-, Dämpfungs- und Rahmenfarbe. Ein
#: gesetzter Hintergrund bliebe im dunklen Client also unter allen Umständen
#: hell, und damit ist jedes Vorkommen ein Befund.
#:
#: Bis #243 fiel er zufällig unter `color:` — die Prüfung suchte den Namen als
#: Teilstring irgendwo im Stil, und `background-color:` enthält ihn. Seit die
#: Suche an der Deklaration ankert, muss er eigens dastehen. Sonst hätte diese
#: Änderung eine Prüfung stillgelegt, ohne dass jemand es beschlossen hätte.
UMSCHALTPFLICHTIG = (("color:", (KLASSE_TEXT, KLASSE_LEISE)),
                     ("background-color:", ()),
                     ("border-top:", (KLASSE_LINIE,)),
                     ("border-left:", (KLASSE_LINIE,)),
                     ("border:", (KLASSE_LINIE,)))

#: Werte, die die Eigenschaft abschalten statt eine Farbe zu setzen.
#:
#: `border: 0` am Logo ist der gemessene Fall (#243): Es gibt dort keine
#: Rahmenfarbe, die im Dunkeln hell bleiben könnte — die Angabe nimmt dem Bild
#: den Rahmen, den ältere Clients von sich aus zeichnen. Ohne diese Ausnahme
#: meldete die Prüfung jede Nachricht mit Logo, und der einzige Weg, sie
#: stillzustellen, wäre eine Klasse gewesen, die nichts umschaltet — ein
#: Etikett statt einer Wirkung.
OHNE_FARBE = {"0", "0px", "none"}


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
            wert = re.search(rf"(?:^|;)\s*{re.escape(eigenschaft)}\s*([^;]*)", stil.group(1))
            if not wert or wert.group(1).strip().lower() in OHNE_FARBE:
                continue
            if not vorhanden & set(taugliche):
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

    **Was sie seit #243 nicht mehr prüft:** woher ein Bild kommt. `data:` und
    fremde Adressen waren Verstöße; `email.logo` nimmt sie jetzt ausdrücklich
    an, weil der Signatur-Baukasten im Browser keinen MIME-Container hat und
    das Logo dort sonst ganz fehlt. Die gemessenen Nachteile sind damit nicht
    verschwunden — sie sind die Sache dessen, der die Form wählt, und
    `eml.logo_hinweis()` sagt sie ihm beim Setzen.

    An ihre Stelle tritt `BILDER_MAX`. Der Grund steht dort: Die alte Regel
    hielt die Anzahl nebenbei mit, die neue muss es ausdrücklich tun.
    """
    gefunden = []
    for muster, grund in VERBOTEN:
        if re.search(muster, html, re.IGNORECASE):
            gefunden.append(grund)
    gefunden.extend(_stilbloecke_pruefen(html))
    bilder = re.findall(r"<img\b[^>]*>", html, re.IGNORECASE)
    if len(bilder) > BILDER_MAX:
        gefunden.append(
            f"{len(bilder)} Bilder — eine erzeugte Mail trägt höchstens das Logo des Profils")
    if zaehlpixel(html):
        gefunden.append("Zählpixel — ein 1×1-Bild ist keine Abbildung, "
                        "sondern eine Messung am Empfänger")
    for marke in bilder:
        if not re.search(r'\balt\s*=', marke, re.IGNORECASE):
            gefunden.append("Bild ohne Alternativtext")
        if not re.search(r'\b(width|height)\s*=', marke, re.IGNORECASE):
            # Ohne Maße reserviert kein Client Platz: Die Nachricht springt
            # beim Laden, und wo Bilder blockiert sind, steht der Alternativtext
            # in einem Kasten von null Pixeln.
            gefunden.append("Bild ohne Breiten- oder Höhenangabe")
    gefunden.extend(_layouttabellen_pruefen(html))
    return gefunden


#: Eine Tabelle, die als Layout dient, traegt `role="presentation"`.
#:
#: Warum die Marke Pflicht ist: Ein Screenreader liest jede Tabelle als
#: Datensatz vor — Zeile fuer Zeile, Zelle fuer Zelle, mit angesagter Position.
#: Bei einem Umschlag oder einem Logo daneben ist das sinnlos. `role` schaltet
#: das ab, und zugleich macht die Marke die Absicht pruefbar: Eine Tabelle ohne
#: `<th>` UND ohne `role` ist entweder eine Datentabelle ohne Kopf oder ein
#: unmarkiertes Layout, und beides ist ein Befund.
LAYOUTMARKE = re.compile(r'role\s*=\s*["\']?presentation', re.IGNORECASE)


def _layouttabellen_pruefen(html: str) -> list[str]:
    """Jede Tabelle ist entweder Daten (mit `<th>`) oder Layout (mit `role`).

    Gemessen am 29.08.2026: Eine Mail mit Logo im Profil fiel durch
    `verify --email` — die Signaturtabelle um das Logo trug weder das eine noch
    das andere. Aufgefallen ist es niemandem, weil das Beispielprofil kein Logo
    hat und deshalb kein Test die Tabelle je erzeugte.
    """
    offen: list[str] = []
    #: Je offene Tabelle: trägt sie die Layoutmarke, hat sie eine Kopfzelle.
    stapel: list[list[bool]] = []
    for treffer in re.finditer(r"<table\b([^>]*)>|</table\s*>|<th\b", html, re.IGNORECASE):
        marke = treffer.group(0).lower()
        if marke.startswith("</table"):
            if stapel:
                layout, kopf = stapel.pop()
                if not layout and not kopf:
                    offen.append("Tabelle ohne <th> und ohne role=presentation — "
                                 "Daten oder Layout, eines von beidem muss dastehen")
        elif marke.startswith("<th"):
            # Gehört zur innersten offenen Tabelle. Genau deshalb ein Stapel
            # und kein Paar-Muster: `<table>(.*?)</table>` fand beim Umschlag
            # das Ende der INNEREN Tabelle, übersprang deren Anfang und ließ
            # eine Datentabelle ohne Kopf unbemerkt durch. Gefangen hat das
            # `test_jede_pruefung_kann_rot_werden` — die Sabotage `<th>` zu
            # `<td>` blieb grün.
            if stapel:
                stapel[-1][1] = True
        else:
            stapel.append([bool(LAYOUTMARKE.search(treffer.group(1) or "")), False])
    return offen
