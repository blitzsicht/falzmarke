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

Seit Dialekt 1.1 gibt es die Positivliste **zweimal**: Der Dialekt trägt eine
Fassung. `1.0` ist der Standardbrief, `1.1` öffnet ihn für lange Schreiben.
Welche das ist, entscheidet das Feld `dialekt:` im Frontmatter — **fehlt es,
gilt 1.0.** Ein heute geschriebener Brief rendert damit unverändert weiter;
das ist der Unterschied zwischen einer Erweiterung und einem Bruch.

Der Dialekt ist in `references/markdown.md` vollständig dokumentiert.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from falzmarke import baum, emit

#: Die Fassungen des Dialekts. Wer eine hinzufügt, trägt sie hier ein und
#: erweitert die Tabellen darunter — sonst gilt sie stillschweigend als 1.0.
FASSUNGEN = ("1.0", "1.1")

#: Was ohne Angabe gilt. Bewusst die alte Fassung: Ein Brief, der geschrieben
#: wurde, bevor es das Feld gab, darf sein Aussehen nicht ändern.
STANDARDFASSUNG = "1.0"

#: Wie viele Überschriftebenen eine Fassung kennt. Vier reichen für Abschnitt,
#: Unterabschnitt, Punkt und Unterpunkt — die fünfte gliedert nicht mehr, sie
#: versteckt. 1.0 kennt keine: dort ist jede Überschrift ein Fehler.
MAX_UEBERSCHRIFT = {"1.0": 0, "1.1": 4}

#: Wie tief Aufzählungen gehen dürfen, je Fassung.
#: 1.0 blieb bei zwei Ebenen — mehr braucht ein Standardbrief nicht.
#: In 1.1 sind 5 und 6 lesbar, aber selten gewollt: Sie erzeugen eine Warnung
#: statt eines Verbots, ab 7 bricht es ab.
MAX_LISTENTIEFE = {"1.0": 2, "1.1": 6}
LISTENTIEFE_WARNUNG = {"1.0": 2, "1.1": 4}


class MarkdownFehler(ValueError):
    def __init__(self, zeile: int, meldung: str) -> None:
        super().__init__(f"Zeile {zeile}: {meldung}")
        self.zeile = zeile
        self.meldung = meldung


@dataclass(frozen=True)
class Hinweis:
    """Etwas ist auffällig, aber der Brief wird trotzdem gesetzt.

    Bis Dialekt 1.1 kannte diese Datei nur Fehler mit Abbruch. Das reicht nicht mehr:
    Eine einzelne nummerierte Zeile wird jetzt gesetzt UND gemeldet, und tiefe
    Listen sollen auffallen, ohne den Brief anzuhalten.
    """

    zeile: int
    meldung: str


@dataclass
class Lage:
    """Was während des Lesens an jeder Stelle bekannt sein muss.

    Vorher wurde `versatz` durch jede Funktion gereicht. Mit Fassung, Ziel und
    Hinweisen wären daraus vier Parameter in fünf Signaturen geworden — und
    jede neue Angabe hätte sie erneut angefasst.

    `zeilenversatz` ist die Zeilenzahl des Frontmatters, damit Fehlermeldungen
    die Zeile der Originaldatei nennen.
    """

    zeilenversatz: int = 0
    dialekt: str = STANDARDFASSUNG
    ziel: str = "brief"
    hinweise: list = field(default_factory=list)

    def melde(self, zeile: int, meldung: str) -> None:
        self.hinweise.append(Hinweis(zeile, meldung))


# Knotentypen, die in JEDER Fassung gesetzt werden.
ERLAUBT = {
    "root", "paragraph", "text", "em", "strong", "softbreak", "hardbreak",
    "bullet_list", "ordered_list", "list_item",
    "table", "thead", "tbody", "tr", "th", "td",
}

#: Was eine Fassung zusätzlich setzt. 1.0 ist bewusst leer und bleibt es:
#: Diese Fassung ist abgeschlossen, sie beschreibt den Standardbrief.
ZUSAETZLICH = {
    "1.0": frozenset(),
    "1.1": frozenset({"heading", "heading_open", "inline"}),
}

# Was nicht gesetzt wird, und was der Schreibende stattdessen tun soll.
#
# Kein Eintrag für `heading`: Seit Fassung 1.1 gibt es Überschriften, und die
# alte Begründung („in einem Brief nicht vorgesehen") wäre falsch. Elemente aus
# `ZUSAETZLICH` melden über `_meldung_fassung` bzw. `_meldung_email` — die
# sagen, WO es geht, statt zu behaupten, es ginge nirgends.
ABLEHNUNG = {
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

#: Wie ein Element heißt, das eine neuere Fassung setzt. Gebraucht für zwei
#: Meldungen, die die Ablehnung aus 1.0 NICHT wiederholen dürfen: „in einem
#: Brief nicht vorgesehen" ist falsch, sobald eine Fassung es vorsieht.
BENENNUNG = {
    "heading": "Überschriften",
    "blockquote": "Blockzitate",
    "code_inline": "Code im Text",
    "code_block": "Codeblöcke",
    "fence": "Codeblöcke",
}


def _meldung_fassung(typ: str) -> str:
    """Das Element gibt es — nur nicht in der Fassung, die dieser Brief trägt.

    Die 1.0-Meldung wäre hier irreführend: Sie liest sich wie ein
    grundsätzliches Verbot, und niemand käme auf die Idee, dass ein Feld im
    Frontmatter sie auflöst.
    """
    was = BENENNUNG.get(typ, "dieses Element")
    return (f"{was} brauchen `dialekt: 1.1` im Frontmatter — ohne das Feld gilt "
            "Fassung 1.0, und die kennt sie nicht")


def _meldung_email(typ: str) -> str:
    """Dasselbe Element in einer E-Mail.

    Brief, HTML-Teil und Textteil entstehen aus DEMSELBEN geprüften Baum; ein
    Knoten, den nur der Briefsatz kennt, ließe die beiden anderen abstürzen
    statt melden. Deshalb wird hier abgelehnt, bevor der Knoten überhaupt
    entsteht — nicht erst im Emitter.
    """
    was = BENENNUNG.get(typ, "dieses Element")
    return (f"{was} setzt der HTML-Teil einer E-Mail noch nicht — "
            "im Brief gehen sie mit `dialekt: 1.1`")


def _zeile(knoten, lage: Lage) -> int:
    if knoten.map:
        return knoten.map[0] + 1 + lage.zeilenversatz
    eltern = knoten.parent
    while eltern is not None:
        if eltern.map:
            return eltern.map[0] + 1 + lage.zeilenversatz
        eltern = eltern.parent
    return 1 + lage.zeilenversatz


def _lehne_ab(knoten, lage: Lage) -> None:
    """Ein Knotentyp, den diese Fassung nicht setzt.

    Die Meldung sagt zusätzlich, WARUM er hier nicht geht: weil die Fassung
    älter ist, oder weil das Ziel eine E-Mail ist. Eine Meldung, die beide
    Fälle verschweigt, schickt den Schreibenden auf die falsche Fährte.
    """
    typ = knoten.type
    if typ in ZUSAETZLICH["1.1"]:
        meldung = (_meldung_email(typ) if lage.ziel == "email"
                   else _meldung_fassung(typ))
    else:
        meldung = ABLEHNUNG.get(typ, f"'{typ}' wird in einem Brief nicht gesetzt")
    raise MarkdownFehler(_zeile(knoten, lage), meldung)


def _gesetzt(typ: str, lage: Lage) -> bool:
    """Setzt diese Fassung diesen Knotentyp — an diesem Ziel?"""
    if typ in ERLAUBT:
        return True
    if lage.ziel == "email":
        return False
    return typ in ZUSAETZLICH.get(lage.dialekt, frozenset())


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

TABELLENZEILE = re.compile(r"^\s*\|.*\|\s*$")
TRENNZEILE = re.compile(r"^\s*\|[\s:|-]+\|\s*$")


def _pruefe_tabellen(markdown: str, lage: Lage) -> None:
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
                block_start + 1 + lage.zeilenversatz,
                "Tabelle ohne Trennzeile — unter die Kopfzeile gehört `|---|---|`, "
                "sonst steht die Zeile als Text im Brief",
            )


def _pruefe_rohtext(markdown: str, lage: Lage) -> None:
    for nummer, zeile in enumerate(markdown.splitlines(), start=1 + lage.zeilenversatz):
        for muster, meldung in ROHMUSTER:
            if muster.search(zeile):
                raise MarkdownFehler(nummer, meldung)
    _pruefe_tabellen(markdown, lage)


def _inline(knoten, lage: Lage) -> tuple:
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
            teile.append(baum.Stark(_inline(kind, lage)))
        elif typ == "em":
            teile.append(baum.Betont(_inline(kind, lage)))
        elif typ == "inline":
            teile.extend(_inline(kind, lage))
        else:
            _lehne_ab(kind, lage)
    return tuple(teile)


def _liste(knoten, lage: Lage, tiefe: int) -> baum.Liste:
    grenze = MAX_LISTENTIEFE[lage.dialekt]
    if tiefe > grenze:
        raise MarkdownFehler(
            _zeile(knoten, lage),
            f"Aufzählungen gehen bis {grenze} Ebenen — tiefer wird ein Brief unlesbar",
        )
    if tiefe > LISTENTIEFE_WARNUNG[lage.dialekt]:
        lage.melde(
            _zeile(knoten, lage),
            f"Aufzählung auf Ebene {tiefe} — lesbar, aber selten gewollt; "
            f"ab Ebene {grenze + 1} wird es abgelehnt",
        )

    punkte = [p for p in knoten.children if p.type == "list_item"]
    if len(punkte) < 2:
        zeile = _zeile(knoten, lage)
        if knoten.type == "ordered_list":
            # Bis Dialekt 1.1 ein Fehler. Jetzt wird die Zeile als Liste gesetzt und
            # gemeldet — in BEIDEN Fassungen. Das macht keinen gültigen Brief
            # ungültig: Wo abgebrochen wurde, gab es keine Ausgabe, die sich
            # ändern könnte. Still verändert wird auch nichts, der Startwert
            # bleibt erhalten.
            lage.melde(
                zeile,
                "eine einzelne nummerierte Zeile wird als Liste gesetzt — soll die Zahl "
                "zum Satz gehören, den Punkt schützen: `2\\. Mahnung`",
            )
        else:
            # Beim Strich bleibt es beim Abbruch: Anders als bei einer Zahl ist
            # dort nicht erkennbar, was gemeint war.
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
                stuecke.extend(_inline(kind, lage))
            elif kind.type in ("bullet_list", "ordered_list"):
                stuecke.append(_liste(kind, lage, tiefe + 1))
            else:
                stuecke.extend(_block(kind, lage, tiefe))
        inhalte.append(tuple(stuecke))

    start = 1
    if knoten.type == "ordered_list":
        start = int(knoten.attrs.get("start", 1)) if knoten.attrs else 1
    return baum.Liste(tuple(inhalte), nummeriert=knoten.type == "ordered_list", start=start)


def _ueberschrift(knoten, lage: Lage) -> baum.Ueberschrift:
    """`#` bis `####`. Tiefer wird abgelehnt, nicht heruntergestuft.

    Eine fünfte Ebene still zur vierten zu machen wäre genau das stille
    Verändern, gegen das dieses Werkzeug antritt: Der Brief sähe anders aus als
    geschrieben, und niemand erführe warum.
    """
    grenze = MAX_UEBERSCHRIFT[lage.dialekt]
    # markdown-it liefert die Ebene als Tag: h1 bis h6.
    ebene = int(knoten.tag[1:])
    if ebene > grenze:
        raise MarkdownFehler(
            _zeile(knoten, lage),
            f"Überschriften gehen bis Ebene {grenze} (`{'#' * grenze}`) — "
            f"tiefer gliedert ein Brief nicht mehr, es versteckt nur",
        )
    return baum.Ueberschrift(ebene, _inline(knoten, lage))


def _tabelle(knoten, lage: Lage) -> baum.Tabelle:
    zeilen, ausrichtungen = [], []
    for teil in knoten.children:
        for tr in teil.children:
            zellen = []
            for zelle in tr.children:
                zellen.append(_inline(zelle, lage))  # Tupel von Inline-Knoten
                if teil.type == "thead":
                    stil = (zelle.attrs or {}).get("style", "")
                    treffer = re.search(r"text-align:\s*(\w+)", str(stil))
                    ausrichtungen.append(treffer.group(1) if treffer else None)
            zeilen.append(zellen)
    if not zeilen:
        raise MarkdownFehler(_zeile(knoten, lage), "leere Tabelle")
    return baum.Tabelle(
        tuple(tuple(z) for z in zeilen),
        tuple(ausrichtungen or [None] * len(zeilen[0])),
    )


def _block(knoten, lage: Lage, tiefe: int = 1) -> tuple:
    """Ein Block wird zu null, einem oder mehreren Baumknoten."""
    typ = knoten.type
    if typ == "paragraph":
        return (baum.Absatz(_inline(knoten, lage)),)
    if typ in ("bullet_list", "ordered_list"):
        return (_liste(knoten, lage, tiefe),)
    if typ == "table":
        return (_tabelle(knoten, lage),)
    if typ == "heading":
        if not _gesetzt(typ, lage):
            _lehne_ab(knoten, lage)
        return (_ueberschrift(knoten, lage),)
    if not _gesetzt(typ, lage):
        _lehne_ab(knoten, lage)
    teile = []
    for k in knoten.children or []:
        teile.extend(_block(k, lage, tiefe))
    return tuple(teile)


def pruefe_fassung(wert) -> str:
    """Der Wert des Feldes `dialekt`, geprüft.

    Ein Tippfehler darf nicht stillschweigend zur alten Fassung führen: Der
    Brief sähe dann anders aus als geschrieben, und die Meldung, die erklärt
    warum, käme nie.
    """
    if wert is None or wert == "":
        return STANDARDFASSUNG
    text = str(wert).strip()
    if text not in FASSUNGEN:
        bekannt = ", ".join(FASSUNGEN)
        raise MarkdownFehler(
            1, f"dialekt: '{text}' gibt es nicht — bekannt sind {bekannt}")
    return text


def lies(markdown: str, zeilenversatz: int = 0, *, dialekt: str = STANDARDFASSUNG,
         ziel: str = "brief", hinweise: list | None = None) -> tuple:
    """falzmarke-Markdown -> geprüfter Baum (siehe baum.py).

    `dialekt` ist die Fassung aus dem Frontmatter, `ziel` das Erzeugnis
    (`brief` oder `email`). Beide haben die bisherigen Werte als Voreinstellung,
    damit ein bestehender Aufruf unverändert dasselbe tut.

    `hinweise`: Wer wissen will, was aufgefallen ist, ohne den Brief anzuhalten,
    gibt eine Liste mit — sie wird um `Hinweis`-Einträge ergänzt. Dasselbe
    Muster wie `anlagen_bericht` in `cli.rendere()`; ein zusätzlicher
    Rückgabewert hätte jeden Aufrufer gebrochen.

    Hier endet die Prüfung: Was zurückkommt, ist zulässig. Ein Emitter muss
    nicht mehr entscheiden, ob er etwas ablehnen darf.
    """
    from markdown_it import MarkdownIt
    from markdown_it.tree import SyntaxTreeNode

    lage = Lage(zeilenversatz=zeilenversatz, dialekt=pruefe_fassung(dialekt),
                ziel=ziel, hinweise=hinweise if hinweise is not None else [])

    _pruefe_rohtext(markdown, lage)

    parser = MarkdownIt("commonmark").enable("table")
    wurzel = SyntaxTreeNode(parser.parse(markdown))

    bloecke = []
    for kind in wurzel.children:
        bloecke.extend(_block(kind, lage))
    return tuple(bloecke)


def konvertiere(markdown: str, zeilenversatz: int = 0, *, dialekt: str = STANDARDFASSUNG,
                ziel: str = "brief", hinweise: list | None = None) -> str:
    """falzmarke-Markdown -> Typst.

    Der bisherige Weg in einem Aufruf: lesen, dann setzen. Bleibt, weil ihn
    cli.py und die Tests benutzen — und weil „Markdown zu Typst" für den
    Brief die richtige Beschreibung ist.
    """
    return emit.setze(lies(markdown, zeilenversatz, dialekt=dialekt, ziel=ziel,
                           hinweise=hinweise))
