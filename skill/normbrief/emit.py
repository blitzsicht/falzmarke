#!/usr/bin/env python3
"""Erzeugt Typst-Code aus dem geprüften Markdown-Baum.

**Text wird als Typst-Zeichenkette ausgegeben, nicht als Markup.** Das ist die
wichtigste Entscheidung dieser Datei. Bis v0.1.2 wurde Markup erzeugt und jedes
Sonderzeichen einzeln escaped — eine Liste, die zwangsläufig unvollständig ist:
`//` fehlte darin und löschte den Rest der Zeile, weil Typst es als
Zeilenkommentar liest. Der Fehler war stumm.

In `#text("…")` gibt es keine Sonderzeichen mehr. Zu schützen sind nur zwei:
der Backslash und das Anführungszeichen, die die Zeichenkette selbst begrenzen.
Damit ist die Fehlerklasse geschlossen statt verkleinert.

Der Preis: Typsts eingebaute Kurzschreibweisen (`--` zu Halbgeviertstrich,
gerade zu typografischen Anführungszeichen) greifen in Zeichenketten nicht.
Sie werden deshalb in `typografie.py` selbst erzeugt — deterministisch und
prüfbar.
"""

from __future__ import annotations

from normbrief import typografie


def zeichenkette(text: str) -> str:
    """Ein Python-String als Typst-Zeichenkette."""
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def as_text(text: str, typografie_anwenden: bool = True) -> str:
    if typografie_anwenden:
        text = typografie.anwenden(text)
    return f"#text({zeichenkette(text)})"


def stark(inhalt: str) -> str:
    return f"#strong[{inhalt}]"


def betont(inhalt: str) -> str:
    return f"#emph[{inhalt}]"


def umbruch() -> str:
    return "#linebreak()"


def absatz(inhalt: str) -> str:
    return f"#par[{inhalt}]"


def liste(punkte: list[str], nummeriert: bool = False, start: int = 1) -> str:
    zellen = ", ".join(f"[{p}]" for p in punkte)
    if nummeriert:
        return f"#enum(start: {start}, {zellen})"
    return f"#list({zellen})"


AUSRICHTUNG = {"left": "left", "right": "right", "center": "center", None: "left", "": "left"}


def tabelle(zeilen: list[list[str]], ausrichtungen: list[str | None]) -> str:
    """Kopfzeile fett, Ausrichtung je Spalte aus der Trennzeile."""
    spalten = len(ausrichtungen)
    align = ", ".join(AUSRICHTUNG.get(a, "left") for a in ausrichtungen)
    teile = [
        f"#table(",
        f"  columns: {spalten},",
        f"  align: ({align}{',' if spalten == 1 else ''}),",
        "  stroke: 0.4pt + gray,",
        "  inset: (x: 2mm, y: 1.4mm),",
    ]
    for nummer, zeile in enumerate(zeilen):
        zellen = [f"[{stark(z)}]" if nummer == 0 else f"[{z}]" for z in zeile]
        teile.append("  " + ", ".join(zellen) + ",")
    teile.append(")")
    return "\n".join(teile)
