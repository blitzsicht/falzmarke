"""Misst die Tabelle im fertigen PDF (Issue #151).

Gemeinsam für `test_raster.py` und `test_gegenbeweis.py`: Der eine hält den
Sollwert fest, der andere zeigt, dass er rot wird, wenn jemand den Innenabstand
in `emit.py` anfasst. Beide müssen dieselbe Messung benutzen — zwei Fassungen
könnten zwei verschiedene Dinge messen, und die Gegenprobe belegte dann nichts
über den Test, zu dem sie gehört.

**Der Sollwert steht hier als Zahl, nicht als Rechnung.** Er ist der Beschluss
vom 20.09.2026 („die Lesbarkeit gewinnt", Innenabstand 1,4 mm), gemessen am
Beispiel mit Tabelle. Gelesen wird er nicht aus `emit.py`: Ein Sollwert, der
aus derselben Konstante stammt, gegen die er prüft, bleibt grün, wenn jemand
sie ändert, und misst nichts. Dieses Modul importiert `falzmarke.emit`
deshalb nicht, und `test_raster.py` hält das fest.
"""

from __future__ import annotations

from pathlib import Path

from falzmarke import geometrie

#: Höhe einer Tabellenzeile in mm bei 11 pt und 1,4 mm Innenabstand: 3,88 mm
#: Text plus zweimal 1,4 mm. Das sind 1,58 Rasterzeilen.
ZEILENHOEHE_MM = 6.68

#: Wie weit eine gemessene Höhe abweichen darf. Gemessen liegen alle fünf Zeilen
#: des Beispiels bei 6,681 mm; 0,05 mm ist Spiel für die Rundung im PDF und
#: fängt jede Änderung des Innenabstands ab 0,025 mm — er geht zweimal ein,
#: oben und unten in der Zelle.
TOLERANZ_MM = 0.05

#: Absatz → erste Tabellenzeile und letzte Tabellenzeile → Absatz, gemessen an
#: `examples/brief-tabelle.md`: 2,33 Rasterzeilen zu 4,2333 mm.
EINTRITT_MM = 9.86
AUSTRITT_MM = 9.86


def _seite(pdf: Path):
    return geometrie._oeffne(pdf).pages[0]


def zeilenhoehen_mm(pdf: Path) -> list[float]:
    """Abstände der Zeilenlinien der ersten Tabelle auf Seite 1, von oben nach unten.

    Gemessen wird der Abstand der waagerechten Rahmenlinien, nicht der des
    Textes: Er ist die Höhe der Zeile selbst und hängt an nichts anderem als
    Texthöhe und Innenabstand. Eine Zelle zeichnet ihre Linien einzeln; Linien
    in einem Abstand unter 0,5 mm gelten daher als eine.

    Nur Linien im Satzspiegel zählen. Die Lochmarke ist ebenfalls eine
    waagerechte Linie, steht bei 148,5 mm und damit mitten in der Tabelle des
    Beispiels — beim ersten Versuch verschob sie eine Zeilengrenze um 0,18 mm
    (6,86 und 6,50 statt zweimal 6,68), ohne dass die Summe es verriet.
    """
    seite = _seite(pdf)
    bereiche = geometrie._tabellenbereiche(seite)
    assert bereiche, "keine Tabelle im PDF gefunden — die Messung misst nichts"
    oben, unten = bereiche[0]

    lagen = sorted(
        geometrie.mm(linie["top"]) for linie in seite.lines
        if abs(linie["y0"] - linie["y1"]) < 0.3
        and geometrie.mm(linie["x0"]) >= geometrie.RAND_LINKS - 1.0
        and oben <= geometrie.mm(linie["top"]) <= unten
    )
    gruppen: list[list[float]] = []
    for lage in lagen:
        if gruppen and lage - gruppen[-1][-1] < 0.5:
            gruppen[-1].append(lage)
        else:
            gruppen.append([lage])
    mitte = [sum(g) / len(g) for g in gruppen]
    return [b - a for a, b in zip(mitte, mitte[1:])]


def uebergaenge_mm(pdf: Path) -> tuple[list[float], list[float]]:
    """(Eintritte, Austritte): Abstand der Textzeilen vor und hinter der Tabelle.

    Dieselbe Auswahl wie in `geometrie._raster` — Körpertext, oberhalb des
    Fußbereichs, je Zeile die höchste Oberkante —, damit die Zahl hier die
    ist, die die Rasterprüfung ausnimmt.
    """
    seite = _seite(pdf)
    tabellen = geometrie._tabellenbereiche(seite)
    spans = [s for s in geometrie._spans(seite)
             if abs(s.groesse - geometrie.KOERPER_PT) < 0.3
             and s.y0 < geometrie.RASTER_BIS]
    zeilen = sorted(geometrie._zeilen_gruppieren(spans),
                    key=lambda g: min(s.y0 for s in g))
    hoehen = [min(s.y0 for s in z) for z in zeilen]
    innen = [any(a <= h <= b for a, b in tabellen) for h in hoehen]

    eintritte = [hoehen[i] - hoehen[i - 1] for i in range(1, len(hoehen))
                 if innen[i] and not innen[i - 1]]
    austritte = [hoehen[i] - hoehen[i - 1] for i in range(1, len(hoehen))
                 if innen[i - 1] and not innen[i]]
    return eintritte, austritte
