#!/usr/bin/env python3
"""Mail-Adressen, Domains und URLs im Brieftext: erkennen und zusammenhalten.

Typst trennt Wörter nach den Silbentrennregeln der Sprache, und eine Adresse
ist für Typst ein Wort wie jedes andere. Gemessen an versendeten Briefen
(14.10.2026 und 17.10.2026): Aus „servus@blitzsicht.com“ wurde „ser-“ am
Zeilenende und „vus@blitzsicht.com“ in der nächsten Zeile, aus
„blitzsicht.com/datenschutz“ wurde „blitzsicht.com/da-“ und „tenschutz“. Wer
das abtippt, schreibt an eine Adresse, die es nicht gibt. Dazu kommt ein
zweiter Weg, auf dem eine Adresse zerfällt: Text, der mit `http://` oder
`https://` beginnt, bricht Typst ohne Trennstrich nach Punkt und Schrägstrich
um („https://blitzsicht.“ / „com/datenschutz.“), bei Platznot auch mitten im
Wort („…/handwerk“ / „sbetriebe/…“).

Dieses Modul ist die eine Stelle, an der feststeht, was als Adresse gilt. Der
Typst-Emitter (`emit.as_text`) setzt jedes Wort, das eine enthält, unteilbar;
`verify` (`geometrie.pruefe`) sucht im fertigen PDF nach einer, die trotzdem
über das Zeilenende läuft. Beide lesen dasselbe Muster, damit Satz und
Nachmessung nicht auseinanderlaufen.

Die E-Mail-Emitter brauchen das nicht: HTML und Text bricht das Mailprogramm
des Empfängers um, und dort gibt es keine Silbentrennung, die falzmarke
einschaltet.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Ein Rechnername mit Endung. `\w` statt `[A-Za-z0-9]`, damit auch eine Domain
# mit Umlaut („bäckerei-zink.de“) als Adresse gilt.
_RECHNER = r"(?:[\w-]+\.)+[A-Za-z]{2,}"
# Eine Domain ohne Schema und ohne @. Die Endung nur klein: Sonst gälte jeder
# fehlende Leerschritt nach einem Satzpunkt („Ende.Die“) als Domain.
_DOMAIN = r"(?:[\w-]+\.)+[a-z]{2,}(?!\w)"
# Pfad, Abfrage oder Anker. Satzzeichen am Ende gehören dazu; wo das stört,
# schneidet der Aufrufer sie ab (`_vollstaendig`).
_REST = r"(?:[/?#]\S*)?"

#: Was als Adresse gilt: URL mit Schema, E-Mail-Adresse oder Domain.
NETZADRESSE = re.compile(
    rf"(?:https?|ftp)://{_RECHNER}(?::\d+)?{_REST}"
    rf"|[\w.%+-]+@{_RECHNER}"
    rf"|{_DOMAIN}{_REST}"
)

#: Bis zu dieser Länge wird ein Wort mit Adresse im Fließtext als Box gesetzt.
#:
#: Eine Box rückt als Ganzes in die nächste Zeile, wenn sie nicht mehr passt.
#: Ist sie breiter als die ganze Zeile, ragt sie nicht etwa über den Rand:
#: Typst bricht sie in sich um, und das Wort danach steht neben ihrer ersten
#: Zeile statt hinter ihrer letzten. Gemessen am 17.10.2026 mit einer URL aus
#: 103 Zeichen: „…foerderung-und- und“ / „zuschuesse“ / „danach weiter.“ Keine
#: Maßprüfung schlägt an, und auch diese nicht — die Zeile endet auf „und“.
#: Die Grenze muss deshalb sicher unter der Zeilenbreite bleiben. Gemessen mit
#: Libertinus Serif in 11 pt (Satzbreite 165 mm): eine Filial-URL aus 61
#: Zeichen 98,8 mm, eine aus 72 Zeichen 117,5 mm, eine Mail-Adresse aus 43
#: Zeichen 68,7 mm. Erst ein Kunstwort aus lauter „mw“ (2,86 mm je Zeichen)
#: bräuchte bei 60 Zeichen mehr als die Zeile.
#:
#: Über der Grenze setzt der Emitter nur die Silbentrennung aus: Typst darf
#: dann an Punkt oder Schrägstrich umbrechen, eine URL auch mitten im Wort,
#: aber ohne Trennstrich, der wie ein Teil der Adresse aussähe. Bricht die
#: Adresse dabei, meldet `verify` es (`getrennt`, Fall 3).
UNTEILBAR_BIS = 60

#: Dieselbe Grenze im Blocksatz (Urkunde mit `blocksatz: true`).
#:
#: Rückt eine Box in die nächste Zeile, treibt der Blocksatz die Zeile davor
#: auf volle Breite aus. Gemessen am 17.10.2026 an der Muster-Urkunde, größte
#: Lücke zwischen zwei Wörtern der Zeile davor: bis 40 Zeichen 1,0 mm wie im
#: übrigen Text, 47 Zeichen 2,0 mm, 52 Zeichen 5,7 mm, 59 Zeichen 10,9 mm.
UNTEILBAR_BIS_BLOCKSATZ = 40

# Was einem Satz folgt, ohne zur Adresse zu gehören.
_SATZZEICHEN = ".,;:!?)]}»«“”‘’\"'"
# Was am Zeilenende eine Silbentrennung anzeigt. pdfplumber liest Typsts
# Trennstrich als „-“, pdftotext als weiches Trennzeichen (U+00AD).
_TRENNSTRICHE = "-­‐‑"


def zerlege(text: str) -> list[tuple[str, bool]]:
    """Text in Stücke, je mit der Angabe, ob es ein Wort mit Adresse ist.

    Zusammengehalten wird das ganze Wort bis zum nächsten Leerraum, nicht nur
    die Adresse selbst: Ein Komma oder eine Klammer direkt daran darf nicht
    allein am Anfang der nächsten Zeile stehen.

    Ohne Adresse kommt der Text unverändert als ein einziges Stück zurück.
    Damit bleibt der Satz jedes Briefes ohne Adresse Byte für Byte, wie er war.
    """
    teile: list[tuple[str, bool]] = []
    bis = 0
    for wort in re.finditer(r"\S+", text):
        if not NETZADRESSE.search(wort.group()):
            continue
        if wort.start() > bis:
            teile.append((text[bis:wort.start()], False))
        teile.append((wort.group(), True))
        bis = wort.end()
    if bis < len(text) or not teile:
        teile.append((text[bis:], False))
    return teile


def _vollstaendig(stueck: str) -> bool:
    """Ist das Stück für sich schon eine ganze Adresse, gefolgt höchstens von Satzzeichen?"""
    kern = stueck.rstrip(_SATZZEICHEN)
    return bool(kern) and NETZADRESSE.fullmatch(kern) is not None


def _ueber_die_fuge(verbunden: str, fuge: int):
    """Die erste Adresse in `verbunden`, die vor der Fuge beginnt und dahinter endet."""
    for treffer in NETZADRESSE.finditer(verbunden):
        if treffer.start() < fuge < treffer.end():
            return treffer
    return None


@dataclass(frozen=True)
class Trennung:
    """Eine Adresse, die über das Zeilenende läuft."""

    #: Index der Zeile, an deren Ende die Adresse abbricht (ab 0).
    zeile: int
    #: Das letzte Wort dieser Zeile und das erste der nächsten.
    ende: str
    anfang: str
    #: `trennstrich`: Die Zeile endet auf einem Trennstrich mitten in der
    #: Adresse. `umbruch`: Die Adresse bricht ohne Strich ab.
    #: `ueberlang`: Sie ist zu lang für die Box und bricht irgendwo ab (Fall 3
    #: in `getrennt`).
    art: str

    def __str__(self) -> str:
        # Ein weiches Trennzeichen (so liest pdfplumber den Trennstrich im
        # fetten Betreff) wäre im Bericht unsichtbar: „ser ⏎ vus@…“.
        return f"„{self.ende.replace(chr(0xAD), '-')} ⏎ {self.anfang}“"


#: Womit das Wort am Zeilenanfang beginnen kann, wenn es eine URL fortsetzt.
_PFADZEICHEN = "-._~%?#&=+"


def getrennt(zeilen: list[str], unteilbar_bis: int = UNTEILBAR_BIS) -> list[Trennung]:
    """Jede Adresse, die über das Ende einer der Zeilen läuft.

    `zeilen` ist der Text, so wie er im fertigen Dokument Zeile für Zeile
    steht. Verglichen wird das letzte Wort einer Zeile mit dem ersten der
    nächsten — drei Fälle, alle ohne Rückgriff auf die Quelle:

    1. **Trennstrich.** Die Zeile endet auf Buchstabe oder Ziffer und einem
       Trennstrich, und zusammengesetzt (mit oder ohne den Strich) ergibt sich
       eine Adresse, die über die Fuge reicht: „ser-“ / „vus@blitzsicht.com“.
    2. **Umbruch ohne Strich.** Das Wort am Zeilenende trägt schon das
       Merkmal einer Adresse — `://`, `@` oder `www.` —, ist für sich aber
       noch keine ganze: „https://blitzsicht.“ / „com/datenschutz.“.
    3. **Umbruch in einer langen Adresse.** Die Adresse am Zeilenende hat
       ein Schema oder einen Pfad, das nächste Wort könnte sie fortsetzen (es
       beginnt klein, mit einer Ziffer oder einem Zeichen aus einem Pfad;
       groß beginnt ein neuer Satz oder ein Substantiv), und beide zusammen
       sind länger als `unteilbar_bis`. Ohne Box
       bricht Typst eine URL nicht nur nach „/“ um, sondern auch mitten im
       Wort, ganz ohne Strich: „…/handwerksbetriebe/“ / „regensburg/…“,
       „…/handwerk“ / „sbetriebe/…“, „https://www.blitzsicht.“ / „com/…“
       (gemessen am 17.10.2026). Das Stück am Zeilenende sieht dann aus wie
       eine ganze Adresse. Gedruckt ist das nicht zu unterscheiden von einer
       ganzen Adresse, auf die ein neues Wort folgt („https://blitzsicht.com/“
       / „finden Sie“). Fest steht es nur über die Länge: Ein Wort bis
       `unteilbar_bis` Zeichen setzt der Emitter als Box, und eine Box bricht
       nicht um — sind beide zusammen nicht länger, waren es zwei Wörter.
       Sind sie länger, wird gemeldet, auch wenn es zwei Wörter waren: Eine
       Adresse, die mit dem nächsten Wort über die Grenze reicht, ist lang
       genug, um sie zu kürzen.

    `unteilbar_bis` ist deshalb die Grenze, die der Emitter an dieser Stelle
    benutzt hat: 60 im Fließtext, 40 im Blocksatz, 0 in einer Tabellenzelle.

    Was nicht gemeldet wird:

    - Eine Adresse, die über einen Seitenwechsel läuft — gepaart werden nur
      Zeilen derselben Seite.
    - Fall 3 in einem PDF, das nicht falzmarke gesetzt hat, oder an einer
      Stelle, für die der Aufrufer eine größere Grenze angibt, als der
      Emitter benutzt hat: Dort fehlt die Box, auf die sich die Längenprobe
      verlässt. `verify` kennt eine Zelle nur, wenn sie gerahmt ist
      (Markdown-Tabelle); in den Angaben ohne Rahmen gilt die Grenze des
      Fließtexts.
    """
    treffer: list[Trennung] = []
    for nummer in range(len(zeilen) - 1):
        oben, unten = zeilen[nummer].split(), zeilen[nummer + 1].split()
        if not oben or not unten:
            continue
        ende, anfang = oben[-1], unten[0]

        if len(ende) >= 2 and ende[-1] in _TRENNSTRICHE and ende[-2].isalnum():
            # Ob der Strich vom Satz kommt oder zur Adresse gehört („stilp-bau.com“),
            # steht im PDF nicht fest — beide Lesarten werden geprüft, und beide
            # sind ein Befund: Auch ein echter Bindestrich am Zeilenende lässt
            # offen, ob er zur Adresse gehört.
            if (_ueber_die_fuge(ende[:-1] + anfang, len(ende) - 1)
                    or _ueber_die_fuge(ende + anfang, len(ende))):
                treffer.append(Trennung(nummer, ende, anfang, "trennstrich"))
            continue

        adresse = _ueber_die_fuge(ende + anfang, len(ende))
        if adresse is None:
            continue
        # Das Merkmal muss VOR der Fuge stehen. Sonst zöge der lokale Teil einer
        # E-Mail-Adresse jedes Wort davor an sich: „unter“ / „servus@…“ ergäbe
        # zusammengesetzt „unterservus@…“, und ein richtig umbrochener Satz
        # stünde als Befund da (gemessen an der Wiedergabe, 17.10.2026).
        oben_teil = ende[adresse.start():]
        merkmal = "://" in oben_teil or "@" in oben_teil or oben_teil.lower().startswith("www.")
        if merkmal and not _vollstaendig(oben_teil):
            treffer.append(Trennung(nummer, ende, anfang, "umbruch"))
        elif ("/" in oben_teil and len(ende) + len(anfang) > unteilbar_bis
              and (anfang[0].islower() or anfang[0].isdigit() or anfang[0] in _PFADZEICHEN)):
            treffer.append(Trennung(nummer, ende, anfang, "ueberlang"))
    return treffer
