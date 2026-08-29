"""Kontrast messen — die eine Stelle, an der die WCAG-Formel steht.

Zwei Dinge im Haus brauchen sie, und sie brauchten sie unabhaengig voneinander:
das Bildzeichen der Marke (Issue #82, ein SVG, das seine Farben umschalten kann)
und das Logo in der Mailsignatur (Issue #154, ein Rasterbild, das es nicht kann).
Die Formel stand deshalb als Kopie im Test des Bildzeichens. Zwei Kopien einer
Rechenvorschrift driften — deshalb hier, und beide holen sie von hier.

Gerechnet wird nach WCAG 2.2, Verhaeltnis der relativen Leuchtdichten. Die
Schwelle 3,0:1 stammt aus Erfolgskriterium 1.4.11 (Non-text Contrast) und gilt
fuer grafische Elemente — ein Logo ist eines.
"""

from __future__ import annotations

from pathlib import Path

#: Der helle Grund. Eine Mail steht in den drei grossen Programmen auf Weiss.
GRUND_HELL = (0xFF, 0xFF, 0xFF)

#: Der dunkle Grund, gegen den gemessen wird.
#:
#: Kein Programm nennt seinen Wert im Datenmodell — `color-scheme: light dark`
#: sagt nur, DASS umgeschaltet wird, nicht worauf. `#1E1E1E` ist der Wert, an
#: dem im Haus schon einmal gemessen wurde (Bildzeichen, Issue #82), und er
#: liegt im Bereich dessen, was dunkle Schemata setzen. Eine Messung gegen
#: reines Schwarz waere guenstiger und deshalb unehrlich: Sie liesse Farben
#: durchgehen, die auf einem etwas helleren Grund verschwinden.
GRUND_DUNKEL = (0x1E, 0x1E, 0x1E)

#: WCAG 1.4.11 fuer grafische Elemente.
SCHWELLE = 3.0

#: Ab hier zaehlt ein Bildpunkt als sichtbar. Alles darunter ist Rand oder
#: Weichzeichnung und gehoert nicht zur Flaeche, die das Logo ausmacht.
DECKEND_AB = 128

#: Wie viel der sichtbaren Flaeche sich abheben muss, damit das Logo traegt.
#:
#: Die Mehrheit — und das ist bewusst keine feiner gewaehlte Zahl. Jeder Wert
#: zwischen 0 und 1 waere erfunden; die Haelfte ist die einzige Grenze, die sich
#: ohne Zahlenspiel begruenden laesst: Woraus das Logo ueberwiegend besteht,
#: muss man sehen. Beim Zeichen dieses Werkzeugs bleibt auf dunklem Grund nur
#: die gruene Ecke uebrig — ein kleiner Teil, und genau das soll auffallen.
ANTEIL_MINDEST = 0.5


def leuchtdichte(farbe: tuple[int, int, int]) -> float:
    """Relative Leuchtdichte nach WCAG 2.2."""
    werte = [x / 255 for x in farbe]
    werte = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in werte]
    return 0.2126 * werte[0] + 0.7152 * werte[1] + 0.0722 * werte[2]


def kontrast(vordergrund: tuple[int, int, int],
            hintergrund: tuple[int, int, int]) -> float:
    """Kontrastverhaeltnis zweier Farben, zwischen 1,0 und 21,0."""
    a, b = leuchtdichte(vordergrund), leuchtdichte(hintergrund)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def tragender_anteil(bild: Path, grund: tuple[int, int, int]) -> float:
    """Welcher Teil der sichtbaren Flaeche hebt sich von diesem Grund ab?

    Rueckgabe zwischen 0,0 und 1,0. Ein Bild ohne sichtbare Flaeche ergibt 0,0.

    Halbdurchsichtige Punkte werden ueber den Grund gerechnet, nicht als ihre
    eigene Farbe genommen: Ein Logo mit weichem Rand steht in der Mail auf dem
    Grund des Programms, und genau diese Mischfarbe sieht der Leser.
    """
    from PIL import Image

    with Image.open(bild) as offen:
        # `tobytes` statt `getdata`: Letzteres ist ab Pillow 14 abgekuendigt,
        # und sein Ersatz gibt es in aelteren Fassungen noch nicht — ein Aufruf,
        # der je nach installierter Version warnt oder fehlt. Rohbytes gibt es
        # in jeder. Vier je Punkt, weil RGBA.
        #
        # Nicht quantisiert: Das legte Farben zusammen, die sich gerade an der
        # Schwelle unterscheiden. Ein Signaturlogo ist klein genug.
        roh = offen.convert("RGBA").tobytes()

    sichtbar = 0
    traegt = 0
    for i in range(0, len(roh), 4):
        r, g, b, a = roh[i], roh[i + 1], roh[i + 2], roh[i + 3]
        if a < DECKEND_AB:
            continue
        sichtbar += 1
        if a < 255:
            anteil = a / 255
            r = round(r * anteil + grund[0] * (1 - anteil))
            g = round(g * anteil + grund[1] * (1 - anteil))
            b = round(b * anteil + grund[2] * (1 - anteil))
        if kontrast((r, g, b), grund) >= SCHWELLE:
            traegt += 1

    return traegt / sichtbar if sichtbar else 0.0


def logo_grund_ohne_halt(bild: Path) -> list[str]:
    """Die Gruende, auf denen dieses Logo nicht traegt — als lesbare Namen.

    Leere Liste heisst: es traegt auf beiden. Das ist die Form, die der Linter
    braucht — er meldet, WAS fehlt, nicht eine Zahl.
    """
    ohne = []
    for name, grund in (("hellem", GRUND_HELL), ("dunklem", GRUND_DUNKEL)):
        if tragender_anteil(bild, grund) < ANTEIL_MINDEST:
            ohne.append(name)
    return ohne
