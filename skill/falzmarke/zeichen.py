#!/usr/bin/env python3
"""Unsichtbare und ungewöhnliche Zeichen im Entwurf — gemeldet, nie geändert.

Ein aus einem Browser oder einem Chatfenster kopierter Absatz bringt Zeichen
mit, die niemand sieht: Zero-Width-Marken, weiche Trennstriche,
Bidi-Steuerzeichen, Variantenselektoren. Sie überleben jeden Weg, den falzmarke
baut — sie stehen hinterher in der `.eml` und im PDF, und niemand erfährt
davon. Vor dieser Datei prüfte das nichts: Gesucht wurde in `lint.py`,
`markdown.py`, `pruefung_eml.py` und `eml.py` nach `u200`, `u00ad`, `\\xa0`,
`zero.?width`, `bidi` und `NBSP` — ein Kommentar, sonst kein Treffer.

Diese Datei **meldet und ändert nie**. Zeichen setzt `typografie.py`, und die
Trennung ist Absicht: „Ein Werkzeug, das ungefragt in einen Text schreibt,
schreibt irgendwann den falschen" (`references/stil.md`).

Drei Klassen, nach der Wirkung getrennt:

* **ohne Zweck in deutschem Text** → Fehler, Regel `zeichen.unsichtbar`.
  Steuer- und Formatzeichen, Variantenselektoren ohne Bildzeichen davor,
  Nichtzeichen, Private Use. Das ist eine Aussage über die Eingabe, keine über
  die Norm — deshalb Ebene `werkzeug` (ADR 0052).
* **ungewöhnliches Leerzeichen** → Warnung, Regel `zeichen.geschuetzt`. Ob ein
  geschütztes Leerzeichen an einer Stelle gewollt ist, ist Ermessen. Dass das
  eine Warnung bleibt, steht in der Regeldatei (`deckel: warnung`) und nicht
  hier — siehe `Befund`.
* **harmlos** → keine Meldung. Geschützte Leerzeichen an den Stellen, an denen
  der Satz selbst eines setzt; ein Variantenselektor hinter einem Bildzeichen;
  ein Zero-Width-Joiner zwischen zwei Bildzeichen.

Die Positivregel liest ihre Stellen **aus `typografie.py`**, nicht aus einer
zweiten Liste. Das ist der Kern: `anwenden()` setzt bei `z. B.`, `§ 7`,
`12 kg`, `25. August`, `Nr. 4711` selbst ein geschütztes Leerzeichen. Eine
Prüfung mit eigener Liste würde dieselbe Ausgabe melden, die das Werkzeug
gerade erzeugt hat — und eine Warnung, die am eigenen Ergebnis anschlägt,
kostet Vertrauen in alle anderen.
"""

from __future__ import annotations

import re
import unicodedata
from typing import NamedTuple

from falzmarke import typografie

#: Die Regel der Fehlerklasse. Steht in `regeln/din5008.yaml`, weil dasselbe
#: Zeichen im Brief ins PDF wandert und nicht nur in die E-Mail.
REGEL_UNSICHTBAR = "zeichen.unsichtbar"
#: Die Regel der Warnklasse — derselbe Weg, `deckel: warnung` in der Regeldatei.
REGEL_GESCHUETZT = "zeichen.geschuetzt"

#: Was der Zeilenumbruch und der Tabulator sind, meldet `lint` schon selbst
#: (Regeln `umbruch` und `tabulator`). Zweimal dasselbe zu melden macht die
#: Meldung nicht wahrer.
#:
#: Das Wagenrücklaufzeichen steht hier, weil eine unter Windows geschriebene
#: Datei es am Ende jeder Zeile trägt. Ohne diese Ausnahme meldete die Prüfung
#: jede Zeile einer CRLF-Datei als Fehler — ein Fehlalarm, der mit dem
#: Betriebssystem kommt und nicht mit dem Text.
STEUERZEICHEN_DES_SATZES = frozenset("\t\n\r")

#: Zeichen, die keine der Kategorien unten fängt, in deutschem Text aber
#: nichts zu suchen haben. Der Verbinder U+034F ist `Mn`, die Füllzeichen sind
#: `Lo` — beide sähen als Kategorie wie gewöhnliche Schrift aus.
ZWECKLOS_EINZELN = frozenset({
    0x034F,            # COMBINING GRAPHEME JOINER
    0x115F, 0x1160,    # HANGUL CHOSEONG/JUNGSEONG FILLER
    0x17B4, 0x17B5,    # KHMER VOWEL INHERENT AQ/AA
    0x3164,            # HANGUL FILLER
    0xFFA0,            # HALFWIDTH HANGUL FILLER
})

#: Variantenselektoren. Hinter einem Bildzeichen gehören sie dazu, sonst sind
#: sie unsichtbare Fracht.
VARIANTENSELEKTOREN = frozenset(
    list(range(0xFE00, 0xFE10)) + list(range(0xE0100, 0xE01F0)))

def _ist_nichtzeichen(punkt: int) -> bool:
    """U+FDD0–FDEF und die beiden letzten Stellen jeder Ebene.

    Der Unicode-Standard reserviert sie dauerhaft; sie altern nicht. Die
    Kategorie `Cn` wäre der bequemere Weg und der falsche: Sie trifft in einer
    älteren Python-Fassung auch ein neues, gültiges Zeichen — ein Fehlalarm,
    der mit dem Alter des Interpreters kommt und nicht mit dem Text.
    """
    return 0xFDD0 <= punkt <= 0xFDEF or (punkt & 0xFFFE) == 0xFFFE


class Befund(NamedTuple):
    """Eine Stelle, ein Zeichen, eine Meldung.

    `zeichen.py` kennt die Bericht-API nicht; sie gibt Befunde zurück, und
    `lint.pruefe_body` meldet sie. So bleibt die Prüfung ohne Testaufbau
    messbar.

    **Ohne Stufe, mit Absicht.** Ob ein Befund Fehler oder Warnung ist, steht
    in der Regeldatei und nirgends sonst: `Bericht.fehler` deckelt jede Meldung
    nach `herkunft`, `ebene` und `deckel` (ADR 0035). Eine zweite Angabe hier
    wäre eine zweite Wahrheit — sie könnte von der Regeldatei abweichen, ohne
    dass etwas meldet. Deshalb trägt der Befund nur den Regelnamen.
    """

    zeile: int
    spalte: int          # 1-basiert, in Zeichen gezählt
    zeichen: str
    regel: str
    meldung: str
    hinweis: str


def _name(zeichen: str) -> str:
    """`U+200B ZERO WIDTH SPACE` — der Normname ist ein Eigenname und bleibt
    englisch. Ohne Namen (Private Use, Nichtzeichen) nur die Zahl."""
    bezeichnung = unicodedata.name(zeichen, "")
    stelle = f"U+{ord(zeichen):04X}"
    return f"{stelle} {bezeichnung}" if bezeichnung else stelle


def _ist_bildzeichen(zeichen: str) -> bool:
    return (unicodedata.category(zeichen) == "So"
            or 0x1F000 <= ord(zeichen) <= 0x1FAFF)


def _bildzeichen_davor(zeile: str, spalte: int) -> bool:
    """Das letzte sichtbare Zeichen vor `spalte` — Variantenselektoren
    übersprungen, denn in einer Emoji-Folge stehen sie dazwischen."""
    stelle = spalte - 1
    while stelle >= 0 and ord(zeile[stelle]) in VARIANTENSELEKTOREN:
        stelle -= 1
    return stelle >= 0 and _ist_bildzeichen(zeile[stelle])


def _bildzeichen_danach(zeile: str, spalte: int) -> bool:
    stelle = spalte + 1
    while stelle < len(zeile) and ord(zeile[stelle]) in VARIANTENSELEKTOREN:
        stelle += 1
    return stelle < len(zeile) and _ist_bildzeichen(zeile[stelle])


def _positivmuster() -> list[re.Pattern[str]]:
    """Die Stellen, an denen `typografie.anwenden()` selbst ein geschütztes
    Leerzeichen setzt — aus seinen eigenen Listen gebaut.

    Spiegelbild zu `_abkuerzungen`, `_einheiten`, `_datum`, `_paragraf` und
    `_vor_angabe`. Wächst eine der Listen dort, wächst diese hier mit; eine
    Kopie der Listen würde genau dann falsch, wenn es darauf ankommt.
    """
    schutz = f"[{typografie.NBSP}{typografie.SCHMAL}]"
    einheiten = "|".join(re.escape(e) for e in typografie.EINHEITEN)
    monate = "|".join(typografie.MONATE)

    muster = [
        re.compile(rf"§{schutz}\d"),
        re.compile(rf"\d{schutz}(?:{einheiten})(?![\w])"),
        re.compile(rf"\b\d{{1,2}}\.{schutz}(?:{monate})\b"),
    ]
    for kuerzel in typografie.VOR_ANGABE:
        muster.append(re.compile(rf"\b{re.escape(kuerzel)}{schutz}\S"))
    for _, ersatz in typografie.ABKUERZUNGEN:
        muster.append(re.compile(re.escape(ersatz).replace(typografie.NBSP, schutz)))
    return muster


_POSITIVMUSTER = _positivmuster()


def erwartete_schutzstellen(zeile: str) -> set[int]:
    """Die Spalten (0-basiert), an denen ein geschütztes Leerzeichen richtig ist."""
    stellen: set[int] = set()
    for muster in _POSITIVMUSTER:
        for treffer in muster.finditer(zeile):
            stellen.update(
                stelle for stelle, zeichen in enumerate(treffer.group(0), treffer.start())
                if zeichen in (typografie.NBSP, typografie.SCHMAL))
    return stellen


def befunde(text: str, versatz: int = 0) -> list[Befund]:
    """Alle Befunde des Textes, Zeile für Zeile, in Lesereihenfolge.

    `versatz` ist die Zahl der Zeilen, die im Entwurf davorstehen — dieselbe
    Rechnung wie in `lint.pruefe_body`, damit die Zeilennummer auf die
    Quelldatei zeigt und nicht auf den Textteil.
    """
    ergebnis: list[Befund] = []
    # `split("\n")` und nicht `splitlines()`: Letzteres trennt auch an \v, \f,
    # U+2028 und U+2029 — ausgerechnet an vier Zeichen, die diese Prüfung
    # melden soll. Sie wären nie geprüft worden, weil sie im Zeilentrenner
    # verschwinden, und die Zeilennummern aller Befunde danach wären um eins
    # verschoben. Gemessen am 25.10.2026: `"eins\u2028zwei\x0bdrei".splitlines()`
    # ergibt drei Zeilen, `split("\n")` eine.
    for nummer, zeile in enumerate(text.split("\n"), start=1 + versatz):
        erlaubt = erwartete_schutzstellen(zeile)
        for spalte, zeichen in enumerate(zeile):
            befund = _pruefe_zeichen(zeile, zeichen, spalte, nummer, erlaubt)
            if befund is not None:
                ergebnis.append(befund)
    return ergebnis


def _pruefe_zeichen(zeile: str, zeichen: str, spalte: int, nummer: int,
                    erlaubt: set[int]) -> Befund | None:
    punkt = ord(zeichen)
    if zeichen in STEUERZEICHEN_DES_SATZES:
        return None

    kategorie = unicodedata.category(zeichen)

    # ── harmlos: was zu einem Bildzeichen gehört ────────────────────────────
    if punkt in VARIANTENSELEKTOREN and _bildzeichen_davor(zeile, spalte):
        return None
    if punkt == 0x200D and _bildzeichen_davor(zeile, spalte) \
            and _bildzeichen_danach(zeile, spalte):
        return None

    # ── Leerzeichen, die keines sind ────────────────────────────────────────
    if kategorie == "Zs" and zeichen != " ":
        if zeichen in (typografie.NBSP, typografie.SCHMAL):
            if spalte in erlaubt:
                return None
            return Befund(
                nummer, spalte + 1, zeichen, REGEL_GESCHUETZT,
                f"{_name(zeichen)} steht an einer Stelle, an der der Satz keines setzt",
                "ein gewöhnliches Leerzeichen genügt — geschützte setzt der "
                "Typografie-Pass selbst, bei „z. B.“, „§ 7“, „12 kg“, „25. August“ "
                "und „Nr. 4711“",
            )
        return Befund(
            nummer, spalte + 1, zeichen, REGEL_GESCHUETZT,
            f"{_name(zeichen)} ist ein Leerzeichen, das nicht wie eines aussieht",
            "durch ein gewöhnliches Leerzeichen ersetzen — in Suche, Sortierung "
            "und Serienbrief verhält es sich anders",
        )

    # ── ohne Zweck in deutschem Text ────────────────────────────────────────
    # `Zl` und `Zp` sind U+2028 und U+2029: ein Zeilen- und ein
    # Absatzumbruch, die kein Editor als solchen zeigt.
    if kategorie in ("Cf", "Cc", "Co", "Zl", "Zp") or punkt in ZWECKLOS_EINZELN \
            or punkt in VARIANTENSELEKTOREN or _ist_nichtzeichen(punkt):
        return Befund(
            nummer, spalte + 1, zeichen, REGEL_UNSICHTBAR,
            f"{_name(zeichen)} steht unsichtbar im Text (Zeichen {spalte + 1})",
            "löschen — das Zeichen hat in deutschem Text keinen Zweck und kommt "
            "meist aus einer Zwischenablage. Es bleibt in der .eml und im PDF "
            "stehen, ohne dass es jemand sieht",
        )
    return None
