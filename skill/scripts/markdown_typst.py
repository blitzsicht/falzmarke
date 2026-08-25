#!/usr/bin/env python3
"""Übersetzt die zugelassene Markdown-Teilmenge in Typst-Markup.

Alles, was nicht ausdrücklich zugelassen ist, führt zu einem Fehler mit
Zeilennummer. Stilles Durchreichen wäre schlimmer als ein Abbruch: Typst
würde ein `#` als Codebeginn lesen und der Brief sähe still falsch aus.
"""

from __future__ import annotations

import re

NBSP = " "


class MarkdownFehler(ValueError):
    def __init__(self, zeile: int, meldung: str) -> None:
        super().__init__(f"Zeile {zeile}: {meldung}")
        self.zeile = zeile


# Abkürzungen, die DIN 5008 mit geschütztem Leerzeichen schreibt.
ABKUERZUNGEN = [
    (re.compile(r"\bz\. ?B\."), f"z.{NBSP}B."),
    (re.compile(r"\bu\. ?a\."), f"u.{NBSP}a."),
    (re.compile(r"\bd\. ?h\."), f"d.{NBSP}h."),
    (re.compile(r"\bi\. ?d\. ?R\."), f"i.{NBSP}d.{NBSP}R."),
    (re.compile(r"\bo\. ?Ä\."), f"o.{NBSP}Ä."),
    (re.compile(r"\bu\. ?U\."), f"u.{NBSP}U."),
    (re.compile(r"\bz\. ?T\."), f"z.{NBSP}T."),
    (re.compile(r"\bi\. ?A\."), f"i.{NBSP}A."),
    (re.compile(r"\bi\. ?V\."), f"i.{NBSP}V."),
]

# Zeichen mit Sonderbedeutung im Typst-Markup.
SONDERZEICHEN = "\\#$*_@<>~`[]"

VERBOTEN = [
    (re.compile(r"^\s{0,3}#{1,6}\s"), "Überschriften sind in einem Brief nicht vorgesehen — "
                                      "der Betreff steht im Frontmatter"),
    (re.compile(r"^\s{0,3}>"), "Blockzitate werden nicht unterstützt"),
    (re.compile(r"^\s{0,3}```"), "Codeblöcke werden nicht unterstützt"),
    (re.compile(r"^\s{0,3}(---|\*\*\*|___)\s*$"), "Trennlinien werden nicht unterstützt"),
    (re.compile(r"!\["), "Bilder im Fließtext werden nicht unterstützt — "
                         "ein Logo gehört ins Profil"),
    (re.compile(r"\[[^\]]*\]\([^)]*\)"), "Markdown-Links werden nicht unterstützt — "
                                         "die Adresse einfach ausschreiben"),
]


def _schuetze_abkuerzungen(text: str) -> str:
    for muster, ersatz in ABKUERZUNGEN:
        text = muster.sub(ersatz, text)
    return text


def _escape(text: str) -> str:
    ergebnis = []
    for zeichen in text:
        if zeichen in SONDERZEICHEN:
            ergebnis.append("\\" + zeichen)
        else:
            ergebnis.append(zeichen)
    return "".join(ergebnis)


def _inline(text: str, zeilennummer: int) -> str:
    """**fett** und *kursiv* nach Typst; alles andere wird escaped."""
    if text.count("**") % 2 or (text.replace("**", "").count("*") % 2):
        raise MarkdownFehler(zeilennummer, "unpaarige Sternchen — fett ist **so**, kursiv *so*")

    text = _schuetze_abkuerzungen(text)
    teile: list[str] = []
    muster = re.compile(r"\*\*(.+?)\*\*|\*(.+?)\*")
    position = 0
    for treffer in muster.finditer(text):
        teile.append(_escape(text[position:treffer.start()]))
        if treffer.group(1) is not None:
            teile.append("*" + _escape(treffer.group(1)) + "*")
        else:
            teile.append("_" + _escape(treffer.group(2)) + "_")
        position = treffer.end()
    teile.append(_escape(text[position:]))
    return "".join(teile)


def _tabelle(zeilen: list[tuple[int, str]]) -> str:
    """Pipe-Tabelle nach #table(). Die Trennzeile legt die Spaltenzahl fest."""
    kopf_nr, kopf = zeilen[0]
    spalten = [z.strip() for z in kopf.strip().strip("|").split("|")]
    inhalt_zeilen = []
    for nummer, roh in zeilen[2:]:
        zellen = [z.strip() for z in roh.strip().strip("|").split("|")]
        if len(zellen) != len(spalten):
            raise MarkdownFehler(
                nummer, f"Tabellenzeile hat {len(zellen)} Zellen, der Kopf {len(spalten)}"
            )
        inhalt_zeilen.append(zellen)

    ausgabe = [f"#table(", f"  columns: {len(spalten)},", "  stroke: 0.4pt + gray,",
               "  inset: (x: 2mm, y: 1.4mm),"]
    ausgabe.append("  " + ", ".join(f"[*{_inline(z, kopf_nr)}*]" for z in spalten) + ",")
    for nummer, zellen in zip((n for n, _ in zeilen[2:]), inhalt_zeilen):
        ausgabe.append("  " + ", ".join(f"[{_inline(z, nummer)}]" for z in zellen) + ",")
    ausgabe.append(")")
    return "\n".join(ausgabe)


def konvertiere(markdown: str, zeilenversatz: int = 0) -> str:
    """Markdown-Teilmenge -> Typst-Markup.

    `zeilenversatz` ist die Zeilenzahl des Frontmatters, damit Fehlermeldungen
    die Zeilennummer der Originaldatei nennen.
    """
    roh_zeilen = markdown.splitlines()
    nummerierte = [(i + 1 + zeilenversatz, z) for i, z in enumerate(roh_zeilen)]

    for nummer, zeile in nummerierte:
        for muster, meldung in VERBOTEN:
            if muster.search(zeile):
                raise MarkdownFehler(nummer, meldung)

    ausgabe: list[str] = []
    index = 0
    while index < len(nummerierte):
        nummer, zeile = nummerierte[index]
        gestrippt = zeile.strip()

        if not gestrippt:
            ausgabe.append("")
            index += 1
            continue

        # Tabelle
        if gestrippt.startswith("|"):
            block = []
            while index < len(nummerierte) and nummerierte[index][1].strip().startswith("|"):
                block.append(nummerierte[index])
                index += 1
            if len(block) < 3:
                raise MarkdownFehler(
                    block[0][0], "Tabelle braucht Kopfzeile, Trennzeile und mindestens eine Zeile"
                )
            if not re.match(r"^\|[\s:|-]+\|$", block[1][1].strip()):
                raise MarkdownFehler(block[1][0], "zweite Tabellenzeile muss die Trennzeile sein")
            ausgabe.append(_tabelle(block))
            continue

        # Aufzählung
        if re.match(r"^\s*[-*+]\s+", zeile):
            inhalt = re.sub(r"^\s*[-*+]\s+", "", zeile)
            ausgabe.append("- " + _inline(inhalt, nummer))
            index += 1
            continue

        # Nummerierte Liste
        if re.match(r"^\s*\d+[.)]\s+", zeile):
            inhalt = re.sub(r"^\s*\d+[.)]\s+", "", zeile)
            ausgabe.append("+ " + _inline(inhalt, nummer))
            index += 1
            continue

        # Normale Zeile; ein abschließender Backslash bleibt harter Umbruch
        harter_umbruch = gestrippt.endswith("\\")
        if harter_umbruch:
            gestrippt = gestrippt[:-1].rstrip()
        ausgabe.append(_inline(gestrippt, nummer) + (" \\" if harter_umbruch else ""))
        index += 1

    return "\n".join(ausgabe).strip() + "\n"
