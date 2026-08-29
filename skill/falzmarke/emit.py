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

from falzmarke import baum as baum_modul
from falzmarke import typografie


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


def ueberschrift(inhalt: str, ebene: int) -> str:
    """Eine Zwischenüberschrift, ab Dialekt 1.1.

    `#heading` statt fett gesetztem Text: Nur so steht die Gliederung als
    Struktur im PDF, und davon lebt ein Screenreader. Wie sie aussieht,
    entscheidet die `show`-Regel in `falzmarke.typ` — rastertreu, ohne
    Schriftgrößenwechsel.

    `outlined: false`, weil ein Brief kein Inhaltsverzeichnis hat.
    """
    return f"#heading(level: {ebene}, outlined: false)[{inhalt}]"


def zitat(inhalt: str) -> str:
    """Ein Blockzitat. Wie es aussieht, entscheidet `falzmarke.typ`."""
    return f"#zitat[{inhalt}]"


def wortlaut(inhalt: str, block: bool) -> str:
    """Ein wortgetreuer Auszug — und die heikelste Stelle dieser Datei.

    Ein Codeblock enthält per Definition Zeichen, die anderswo Bedeutung
    tragen: `#import`, `#read`, `#eval`. Würde er als Markup gesetzt, führte
    Typst sie aus — mit Dateizugriff auf dem Rechner des Setzenden.

    Er geht deshalb als **Zeichenkette** an `raw()`, genau wie jeder andere
    Text an `#text()`. In einer Zeichenkette gibt es keine Sonderzeichen mehr;
    zu schützen sind nur Backslash und Anführungszeichen, die sie begrenzen —
    und das tut `zeichenkette()`. Die Fehlerklasse ist damit geschlossen, nicht
    verkleinert.

    Keine Sprachangabe: `raw(lang: …)` färbt ein. Ein Geschäftsbrief zitiert
    wortgetreu; Farbe wäre eine Deutung, die der Zitierende nicht getroffen
    hat — und auf einem Schwarzweißdruck ohnehin verloren.

    Der Typografie-Pass läuft hier **nicht**. Ein Auszug, in dem aus `"` ein „
    und aus `--` ein – wird, ist kein Auszug mehr.
    """
    if block:
        return f"#codeblock(raw({zeichenkette(inhalt)}, block: true))"
    return f"#raw({zeichenkette(inhalt)})"


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
        if nummer == 0:
            # `table.header` statt einer bloss fett gesetzten ersten Zeile: Fett
            # ist eine Aussage ueber das Aussehen, `header` eine ueber die
            # Bedeutung. Im PDF wird daraus `/TH` in einem `/THead` — ohne das
            # liest ein Screenreader „Wert 1" vor, ohne je zu sagen, in welcher
            # Spalte man ist (Issue #138). Nachgemessen mit pypdf,
            # tests/test_struktur.py.
            zellen = [f"[{stark(z)}]" for z in zeile]
            teile.append("  table.header(" + ", ".join(zellen) + "),")
        else:
            teile.append("  " + ", ".join(f"[{z}]" for z in zeile) + ",")
    teile.append(")")
    return "\n".join(teile)


# ── Der Weg über den Baum ───────────────────────────────────────────────────
#
# Bis hierher steht, WIE ein einzelnes Element aussieht. Was folgt, geht den
# geprueften Baum aus markdown.lies() ab und setzt ihn damit. Die Trennung ist
# der Grund, warum eine zweite Ausgabeform daneben passt, ohne die Pruefung zu
# verdoppeln: Der Baum kennt keine Zielsprache.


def _inline(knoten) -> str:
    """Ein Inline-Knoten oder eine Folge davon."""
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
    if isinstance(knoten, baum_modul.Wortlaut):
        return wortlaut(knoten.inhalt, knoten.block)
    return _block(knoten)


def _block(knoten) -> str:
    if isinstance(knoten, baum_modul.Absatz):
        return absatz(_inline(knoten.kinder))
    if isinstance(knoten, baum_modul.Wortlaut):
        return wortlaut(knoten.inhalt, knoten.block)
    if isinstance(knoten, baum_modul.Zitat):
        return zitat("\n".join(_block(k) for k in knoten.kinder))
    if isinstance(knoten, baum_modul.Ueberschrift):
        return ueberschrift(_inline(knoten.kinder), knoten.ebene)
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
    # Kein stilles Uebergehen: Ein Knoten, den dieser Emitter nicht kennt, ist
    # ein Fehler im Werkzeug, kein Fehler des Briefes — und er darf nicht als
    # leerer Absatz in einem Brief landen, den jemand abschickt.
    raise TypeError(
        f"Der Typst-Emitter kennt {type(knoten).__name__} nicht. "
        "Neuer Knoten in baum.py? Dann gehört er auch hierher."
    )


def setze(bloecke) -> str:
    """Geprüfter Baum -> Typst."""
    gesetzt = [_block(b) for b in bloecke]
    return "\n\n".join(b for b in gesetzt if b.strip()) + "\n"
