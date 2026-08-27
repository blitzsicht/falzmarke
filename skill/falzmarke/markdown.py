#!/usr/bin/env python3
"""falzmarke-Markdown: eine Teilmenge von CommonMark, geprüft statt geraten.

Bis v0.1.2 war das hier ein Regex-Konverter. Regexe können Markdown nicht
zerlegen — sie sehen `**` und `*`, aber keine Struktur, und was sie nicht
kennen, reichen sie durch. Ein `//` im Fließtext löschte so den Rest der Zeile,
weil Typst es als Kommentar las.

Jetzt parst `markdown-it-py` nach CommonMark, und der Baum wird gegen eine
**Positivliste** von Knotentypen geprüft. Was nicht auf der Liste steht, ist ein
Fehler mit Zeile, Grund und Korrektur — nie ein stilles Durchreichen. Der
Emitter erzeugt daraus Typst-Funktionsaufrufe mit Zeichenketten
(siehe `emit.py`), sodass es im Ergebnis keine Sonderzeichen mehr gibt.

Der Dialekt ist in `references/frontmatter.md` vollständig dokumentiert.
"""

from __future__ import annotations

import re

from falzmarke import baum, emit

MAX_LISTENTIEFE = 2


class MarkdownFehler(ValueError):
    def __init__(self, zeile: int, meldung: str) -> None:
        super().__init__(f"Zeile {zeile}: {meldung}")
        self.zeile = zeile
        self.meldung = meldung


# Knotentypen, die gesetzt werden. Alles andere wird abgelehnt.
ERLAUBT = {
    "root", "paragraph", "text", "em", "strong", "softbreak", "hardbreak",
    "bullet_list", "ordered_list", "list_item",
    "table", "thead", "tbody", "tr", "th", "td",
}

# Was nicht gesetzt wird, und was der Schreibende stattdessen tun soll.
ABLEHNUNG = {
    "heading": "Überschriften sind in einem Brief nicht vorgesehen — der Betreff steht im Frontmatter",
    "blockquote": "Blockzitate werden nicht gesetzt — den Text als eigenen Absatz schreiben",
    "code_inline": "Code ist in Briefen nicht vorgesehen — den Text ohne Backticks schreiben",
    "code_block": "Code ist in Briefen nicht vorgesehen — die Einrückung entfernen",
    "fence": "Code ist in Briefen nicht vorgesehen — den Text ohne Backticks schreiben",
    "link": "Adresse ausschreiben — auf Papier gibt es keinen Link zum Anklicken",
    "link_open": "Adresse ausschreiben — auf Papier gibt es keinen Link zum Anklicken",
    "image": "Bilder gehören ins Profil (Logo, Signatur), nicht in den Brieftext",
    "html_inline": "HTML wird nicht durchgereicht — den Text ohne Auszeichnung schreiben",
    "html_block": "HTML wird nicht durchgereicht — den Text ohne Auszeichnung schreiben",
    "hr": "Trennlinien werden nicht gesetzt — Absätze trennen den Text",
}

# Syntax, die CommonMark ohne Erweiterung als Text durchreicht. Ungeprüft
# stünde sie wörtlich im Brief — mit Tilden und Klammern.
ROHMUSTER = [
    (re.compile(r"~~.+?~~"), "Durchgestrichener Text wird nicht gesetzt — die Streichung ausformulieren"),
    (re.compile(r"^\s*[-*+]\s+\[[ xX]\]\s"), "Aufgabenlisten werden nicht gesetzt — als gewöhnliche Aufzählung schreiben"),
    (re.compile(r"\[\^[^\]]+\]"), "Fußnoten werden nicht gesetzt — die Anmerkung in den Satz aufnehmen"),
]

# Eine einzelne Zeile, die wie ein Listenpunkt aussieht, aber keiner ist.
EINZELNE_NUMMER = re.compile(r"^\s*(\d+)([.)])\s+(.*)$")
EINZELNER_STRICH = re.compile(r"^\s*([-*+])\s+(.*)$")


def _zeile(knoten, versatz: int) -> int:
    if knoten.map:
        return knoten.map[0] + 1 + versatz
    eltern = knoten.parent
    while eltern is not None:
        if eltern.map:
            return eltern.map[0] + 1 + versatz
        eltern = eltern.parent
    return 1 + versatz


TABELLENZEILE = re.compile(r"^\s*\|.*\|\s*$")
TRENNZEILE = re.compile(r"^\s*\|[\s:|-]+\|\s*$")


def _pruefe_tabellen(markdown: str, versatz: int) -> None:
    """Eine Pipe-Zeile ohne Trennzeile ist für CommonMark gewöhnlicher Text.

    Der Brief bekäme dann eine Zeile voller Striche statt einer Tabelle. Wer
    Pipes schreibt, meint eine Tabelle — also lieber melden.
    """
    zeilen = markdown.splitlines()
    index = 0
    while index < len(zeilen):
        if not TABELLENZEILE.match(zeilen[index]):
            index += 1
            continue
        block_start = index
        while index < len(zeilen) and TABELLENZEILE.match(zeilen[index]):
            index += 1
        block = zeilen[block_start:index]
        if not any(TRENNZEILE.match(z) for z in block):
            raise MarkdownFehler(
                block_start + 1 + versatz,
                "Tabelle ohne Trennzeile — unter die Kopfzeile gehört `|---|---|`, "
                "sonst steht die Zeile als Text im Brief",
            )


def _pruefe_rohtext(markdown: str, versatz: int) -> None:
    for nummer, zeile in enumerate(markdown.splitlines(), start=1 + versatz):
        for muster, meldung in ROHMUSTER:
            if muster.search(zeile):
                raise MarkdownFehler(nummer, meldung)
    _pruefe_tabellen(markdown, versatz)


def _inline(knoten, versatz: int) -> tuple:
    """Inline-Inhalt eines Absatzes oder einer Zelle, als Baumknoten."""
    teile = []
    for kind in knoten.children or []:
        typ = kind.type
        if typ == "text":
            teile.append(baum.Text(kind.content))
        elif typ == "softbreak":
            # Ein weicher Umbruch ist ein Leerzeichen und sonst nichts — die
            # typografischen Ersetzungen haben daran nichts zu suchen.
            teile.append(baum.Text(" ", typografie=False))
        elif typ == "hardbreak":
            teile.append(baum.Umbruch())
        elif typ == "strong":
            teile.append(baum.Stark(_inline(kind, versatz)))
        elif typ == "em":
            teile.append(baum.Betont(_inline(kind, versatz)))
        elif typ in ABLEHNUNG:
            raise MarkdownFehler(_zeile(kind, versatz), ABLEHNUNG[typ])
        elif typ == "inline":
            teile.extend(_inline(kind, versatz))
        else:
            raise MarkdownFehler(
                _zeile(kind, versatz),
                f"'{typ}' wird in einem Brief nicht gesetzt",
            )
    return tuple(teile)


def _liste(knoten, versatz: int, tiefe: int) -> baum.Liste:
    if tiefe > MAX_LISTENTIEFE:
        raise MarkdownFehler(
            _zeile(knoten, versatz),
            f"Aufzählungen gehen bis {MAX_LISTENTIEFE} Ebenen — tiefer wird ein Brief unlesbar",
        )
    punkte = [p for p in knoten.children if p.type == "list_item"]
    if len(punkte) < 2:
        zeile = _zeile(knoten, versatz)
        if knoten.type == "ordered_list":
            raise MarkdownFehler(
                zeile,
                "eine einzelne nummerierte Zeile wird als Liste gesetzt — soll die Zahl "
                "zum Satz gehören, den Punkt schützen: `2\\. Mahnung`",
            )
        raise MarkdownFehler(
            zeile,
            "ein einzelner Strich am Zeilenanfang wird zum Aufzählungspunkt — soll er zum "
            "Satz gehören, ihn schützen: `\\- 5 °C`",
        )

    inhalte = []
    for punkt in punkte:
        stuecke = []
        for kind in punkt.children or []:
            if kind.type == "paragraph":
                stuecke.extend(_inline(kind, versatz))
            elif kind.type in ("bullet_list", "ordered_list"):
                stuecke.append(_liste(kind, versatz, tiefe + 1))
            else:
                stuecke.extend(_block(kind, versatz, tiefe))
        inhalte.append(tuple(stuecke))

    start = 1
    if knoten.type == "ordered_list":
        start = int(knoten.attrs.get("start", 1)) if knoten.attrs else 1
    return baum.Liste(tuple(inhalte), nummeriert=knoten.type == "ordered_list", start=start)


def _tabelle(knoten, versatz: int) -> baum.Tabelle:
    zeilen, ausrichtungen = [], []
    for teil in knoten.children:
        for tr in teil.children:
            zellen = []
            for zelle in tr.children:
                zellen.append(_inline(zelle, versatz))  # Tupel von Inline-Knoten
                if teil.type == "thead":
                    stil = (zelle.attrs or {}).get("style", "")
                    treffer = re.search(r"text-align:\s*(\w+)", str(stil))
                    ausrichtungen.append(treffer.group(1) if treffer else None)
            zeilen.append(zellen)
    if not zeilen:
        raise MarkdownFehler(_zeile(knoten, versatz), "leere Tabelle")
    return baum.Tabelle(
        tuple(tuple(z) for z in zeilen),
        tuple(ausrichtungen or [None] * len(zeilen[0])),
    )


def _block(knoten, versatz: int, tiefe: int = 1) -> tuple:
    """Ein Block wird zu null, einem oder mehreren Baumknoten."""
    typ = knoten.type
    if typ in ABLEHNUNG:
        raise MarkdownFehler(_zeile(knoten, versatz), ABLEHNUNG[typ])
    if typ == "paragraph":
        return (baum.Absatz(_inline(knoten, versatz)),)
    if typ in ("bullet_list", "ordered_list"):
        return (_liste(knoten, versatz, tiefe),)
    if typ == "table":
        return (_tabelle(knoten, versatz),)
    if typ not in ERLAUBT:
        raise MarkdownFehler(_zeile(knoten, versatz), f"'{typ}' wird in einem Brief nicht gesetzt")
    teile = []
    for k in knoten.children or []:
        teile.extend(_block(k, versatz, tiefe))
    return tuple(teile)


def lies(markdown: str, zeilenversatz: int = 0) -> tuple:
    """falzmarke-Markdown -> geprüfter Baum (siehe baum.py).

    `zeilenversatz` ist die Zeilenzahl des Frontmatters, damit Fehlermeldungen
    die Zeile der Originaldatei nennen.

    Hier endet die Prüfung: Was zurückkommt, ist zulässig. Ein Emitter muss
    nicht mehr entscheiden, ob er etwas ablehnen darf.
    """
    from markdown_it import MarkdownIt
    from markdown_it.tree import SyntaxTreeNode

    _pruefe_rohtext(markdown, zeilenversatz)

    parser = MarkdownIt("commonmark").enable("table")
    wurzel = SyntaxTreeNode(parser.parse(markdown))

    bloecke = []
    for kind in wurzel.children:
        bloecke.extend(_block(kind, zeilenversatz))
    return tuple(bloecke)


def konvertiere(markdown: str, zeilenversatz: int = 0) -> str:
    """falzmarke-Markdown -> Typst.

    Der bisherige Weg in einem Aufruf: lesen, dann setzen. Bleibt, weil ihn
    cli.py und die Tests benutzen — und weil „Markdown zu Typst" für den
    Brief die richtige Beschreibung ist.
    """
    return emit.setze(lies(markdown, zeilenversatz))
