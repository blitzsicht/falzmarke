#!/usr/bin/env python3
"""Meldet einen deutschen Schliesssatz, den GitHub nicht als solchen liest (#268).

GitHub schliesst ein Issue beim Merge nur, wenn im Rumpf ein **englisches**
Keyword steht — `close`, `fix`, `resolve` in ihren Beugungen. Dieses Repository
schreibt deutsch. „Schliesst #261" liest sich wie eine Zusage und ist keine.

Gemessen an PR #262: Der Rumpf trug den Satz, nach dem Squash-Merge meldete
`gh issue view 261` weiterhin `OPEN`. Das Issue musste von Hand geschlossen
werden, und aufgefallen ist es nur, weil jemand hinterher nachgesehen hat. Genau
das macht den Fehler teuer: Er ist still, er wiederholt sich bei jedem Vorgang,
und er faellt erst auf, wenn der Rueckstand schon dasteht.

Der Pruefer liest einen Text, nie ein Repository und nie das Netz — dieselbe
Entscheidung wie in scripts/changelog_pflicht.py und scripts/pflicht_checks.py,
und aus demselben Grund (#196): Das Ergebnis haengt allein von der Eingabe ab,
nie vom Zeitpunkt des Aufrufs.

    gh pr view 42 --repo blitzsicht/falzmarke --json body,labels > pr.json
    python3 scripts/closing_keyword.py --pr-json pr.json

Verwendet von .github/workflows/ci.yml.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Die ausdrueckliche Einzelfall-Ausnahme, gleiche Bauart wie „ohne-changelog":
# Sie steht am Vorgang, ist damit sichtbar und begruendbar — anders als ein
# stiller Sonderweg im Code. Fuer den Fall, dass ein Vorgang auf ein Issue
# verweist, das absichtlich offen bleibt (Teilarbeit an einem groesseren Faden).
AUSNAHME_LABEL = "ohne-autoschluss"

# Deutsche Verben, die eine Erledigung zusagen. Bewusst kurz gehalten: Jedes
# weitere Wort erhoeht die Zahl der Faelle, in denen der Pruefer etwas meldet,
# was niemand als Zusage gemeint hat — und ein Pruefer, der oft danebenliegt,
# wird weggeklickt statt gelesen.
DEUTSCHE_VERBEN = (
    "schließt", "schliesst", "behebt", "löst", "loest", "erledigt", "fixt",
)

# Was GitHub tatsaechlich auswertet. Quelle: die Dokumentation zu „Linking a
# pull request to an issue" — drei Staemme in je drei Beugungen.
ENGLISCHE_KEYWORDS = (
    "close", "closes", "closed",
    "fix", "fixes", "fixed",
    "resolve", "resolves", "resolved",
)

_DEUTSCH = re.compile(
    r"\b(?:" + "|".join(DEUTSCHE_VERBEN) + r")\b[^\S\n]*"
    r"(?::)?[^\S\n]*(?:die[^\S\n]+)?(?:Issue[^\S\n]+)?#(\d+)",
    re.IGNORECASE,
)

# Auch die ausgeschriebene Adresse zaehlt — GitHub liest sie genauso.
_ENGLISCH = re.compile(
    r"\b(?:" + "|".join(ENGLISCHE_KEYWORDS) + r")\b[^\S\n]*(?::)?[^\S\n]*"
    r"(?:#|https?://github\.com/[^/\s]+/[^/\s]+/issues/)(\d+)",
    re.IGNORECASE,
)

_CODEBLOCK = re.compile(r"^```.*?^```", re.DOTALL | re.MULTILINE)


def ohne_codebloecke(text: str) -> str:
    """Ein Satz in einem Auszug ist ein Beispiel, keine Zusage.

    Ohne diesen Schritt meldete der Pruefer jeden Rumpf, der die Falle
    *erklaert* — auch den dieses Vorgangs. Ein Pruefer, der an seiner eigenen
    Beschreibung anschlaegt, ist keiner.
    """
    return _CODEBLOCK.sub("", text)


def nummern(muster: re.Pattern, text: str) -> set[int]:
    return {int(t) for t in muster.findall(text)}


def pruefe(rumpf: str, labels: tuple[str, ...] = ()) -> tuple[bool, str]:
    """(in Ordnung, Begruendung) — die ganze Entscheidung an einer Stelle."""
    if AUSNAHME_LABEL in labels:
        return True, f"Label „{AUSNAHME_LABEL}“ gesetzt — ausdrücklich ausgenommen."

    text = ohne_codebloecke(rumpf or "")
    versprochen = nummern(_DEUTSCH, text)
    if not versprochen:
        return True, "Kein deutscher Schließsatz auf eine Nummer im Rumpf."

    # Je Nummer, nicht als Menge: Ein „Closes #99" neben „Schließt #261" ist
    # kein Beleg fuer #261. Genau dieser Fall — zwei Vorgaenge in einem Rumpf,
    # einer englisch zugesagt, einer deutsch — waere einer Mengenpruefung
    # entgangen.
    gedeckt = nummern(_ENGLISCH, text)
    offen = sorted(versprochen - gedeckt)
    if not offen:
        return True, ("Jeder zugesagte Vorgang trägt ein englisches Keyword: "
                      + ", ".join(f"#{n}" for n in sorted(versprochen)) + ".")

    liste = ", ".join(f"#{n}" for n in offen)
    return False, (
        "Dieser Rumpf sagt auf Deutsch zu, einen Vorgang zu schließen — GitHub liest das nicht.\n"
        "\n"
        f"Ohne englisches Keyword: {liste}\n"
        "\n"
        "GitHub wertet beim Merge ausschließlich aus: "
        + ", ".join(ENGLISCHE_KEYWORDS) + "\n"
        "Ein deutscher Satz daneben ist in Ordnung — er muss nur begleitet sein:\n"
        "\n"
        f"    Closes #{offen[0]}\n"
        "\n"
        "Gemessen an PR #262: Der Rumpf trug „Schließt #261\", nach dem Merge stand\n"
        "das Issue weiter auf OPEN und musste von Hand geschlossen werden.\n"
        "\n"
        "Soll der Vorgang bewusst offen bleiben, setzt ein Maintainer das Label\n"
        f"„{AUSNAHME_LABEL}“."
    )


def aus_pr_json(text: str) -> tuple[str, tuple[str, ...]]:
    """(Rumpf, Labels) aus der Ausgabe von `gh pr view --json body,labels`.

    Labels kommen in einem Stueck an, nicht als Wortliste durch die Shell: Ein
    Label darf Leerzeichen enthalten („good first issue"), und unquoted
    expandiert zerfaellt es in drei.
    """
    daten = json.loads(text)
    return (
        daten.get("body") or "",
        tuple(l["name"] for l in daten.get("labels") or []),
    )


def _ausgabe_auf_utf8() -> None:
    """Damit die Ausgabe unter Windows nicht abbricht.

    Dort schreibt Python standardmaessig in cp1252, und die Meldungen hier
    tragen „ und “ — der Aufruf endete dann mit einem UnicodeEncodeError, und
    was beim Aufrufer ankam, war gar nichts. Gemessen in der CI am 08.09.2026
    (Windows-Lauf zu #268): `stderr` kam als None zurueck, weil sich die Bytes
    nicht als UTF-8 lesen liessen.

    Dieselbe Vorkehrung wie in falzmarke/cli.py:_ausgabe_auf_utf8 — dort seit
    dem 25.08.2026 und aus demselben Grund. `scripts/changelog_pflicht.py`
    druckt dieselben Zeichen und hat sie noch nicht; dort faellt es nur
    deshalb nicht auf, weil der Job ausschliesslich auf ubuntu laeuft.
    """
    for strom in (sys.stdout, sys.stderr):
        rekonfigurieren = getattr(strom, "reconfigure", None)
        if rekonfigurieren is not None:
            try:
                rekonfigurieren(encoding="utf-8", errors="replace")
            except (ValueError, OSError):   # pragma: no cover — sehr alte Streams
                pass


def main() -> int:
    _ausgabe_auf_utf8()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pr-json", type=Path,
                        help="Ausgabe von `gh pr view --json body,labels`")
    parser.add_argument("--label", action="append", default=[], help="Label (mehrfach)")
    parser.add_argument("--rumpf", type=Path,
                        help="Datei mit dem Rumpf; ohne beides von der Standardeingabe")
    args = parser.parse_args()

    if args.pr_json:
        rumpf, labels = aus_pr_json(args.pr_json.read_text(encoding="utf-8"))
    elif args.rumpf:
        rumpf, labels = args.rumpf.read_text(encoding="utf-8"), tuple(args.label)
    else:
        rumpf, labels = sys.stdin.read(), tuple(args.label)

    gut, grund = pruefe(rumpf, labels)
    print(grund, file=sys.stdout if gut else sys.stderr)
    return 0 if gut else 1


if __name__ == "__main__":
    raise SystemExit(main())
