"""Das Zwischenformat zwischen Markdown und Ausgabe.

`markdown.py` prüft die Quelle und baut daraus diese Knoten; ein Emitter setzt
sie. Vorher gab `markdown.py` fertigen Typst-Code zurück und rief `emit`
mitten in der Prüfung auf — damit ließ sich keine zweite Ausgabeform daneben
stellen, ohne die Prüfung zu verdoppeln.

Der Baum ist bewusst schmal: Er kennt nur, was der Dialekt zulässt. Was
markdown.py ablehnt, hat hier keinen Knoten — es gibt also keine Möglichkeit,
über diesen Weg etwas in die Ausgabe zu bringen, das die Prüfung nicht gesehen
hat.

Die Knoten tragen keine Zeilennummern. Fehler entstehen beim Bauen, nicht beim
Setzen: Wer bis hierher kommt, hat eine geprüfte Quelle, und ein Emitter soll
sich nicht mehr fragen müssen, ob er ablehnen darf.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Text:
    """Reiner Text.

    `typografie` sagt, ob die Ersetzungen aus typografie.py greifen. Für den
    weichen Zeilenumbruch, der nur ein Leerzeichen ist, greifen sie nicht —
    sonst würde aus dem Zwischenraum ein typografisches Zeichen.
    """

    inhalt: str
    typografie: bool = True


@dataclass(frozen=True)
class Umbruch:
    """Ein harter Zeilenumbruch innerhalb eines Absatzes."""


@dataclass(frozen=True)
class Stark:
    kinder: tuple = ()


@dataclass(frozen=True)
class Betont:
    kinder: tuple = ()


@dataclass(frozen=True)
class Absatz:
    kinder: tuple = ()


@dataclass(frozen=True)
class Liste:
    """`punkte` ist je Punkt eine Folge von Inline-Knoten oder Blöcken."""

    punkte: tuple = ()
    nummeriert: bool = False
    start: int = 1


@dataclass(frozen=True)
class Tabelle:
    """`zeilen[0]` ist die Kopfzeile; `ausrichtungen` hat eine Angabe je Spalte."""

    zeilen: tuple = ()
    ausrichtungen: tuple = ()


#: Alles, was in einem Brieftext stehen darf. Ein Emitter, der einen Knoten
#: nicht kennt, soll abbrechen statt ihn zu übergehen — deshalb die Liste.
KNOTEN = (Text, Umbruch, Stark, Betont, Absatz, Liste, Tabelle)
