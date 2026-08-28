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
class Ueberschrift:
    """Eine Zwischenüberschrift im Brieftext. Erst ab Dialekt 1.1.

    `ebene` ist 1 bis 4. Sie gliedert den **Brieftext** — nicht den Brief: Der
    Betreff steht im Frontmatter, und keine Überschrift verschiebt Anschriftfeld,
    Informationsblock oder Betreffposition.
    """

    ebene: int = 1
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
KNOTEN = (Text, Umbruch, Stark, Betont, Absatz, Ueberschrift, Liste, Tabelle)

#: Knoten, die **nur** der Briefsatz setzt. Die E-Mail-Emitter kennen sie
#: nicht — und sollen sie auch nicht stillschweigend übergehen.
#:
#: Das ist keine Lücke, sondern eine Grenze mit Wache davor: `markdown.py`
#: lehnt diese Elemente bei `ziel="email"` ab, bevor der Knoten überhaupt
#: entsteht. Ein Eintrag hier ist deshalb nur zulässig, solange genau das
#: geprüft ist — `tests/test_emit_html.py` und `tests/test_emit_text.py`
#: verlangen den Nachweis in beide Richtungen: Der Emitter muss abbrechen,
#: UND der Weg dorthin muss versperrt sein.
#:
#: `Ueberschrift` verlässt die Liste, sobald der HTML-Teil sie setzt.
NUR_BRIEF = (Ueberschrift,)
