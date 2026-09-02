#!/usr/bin/env python3
"""Verlangt zu jedem Vorgang einen Changelog-Eintrag (Issue #229).

Von 46 Vorgaengen zwischen v0.8.2 und v0.9.0 hat einer CHANGELOG.md angefasst.
Nach dem Nachtragen von 39 Eintraegen von Hand waren es bei den naechsten vier
Vorgaengen wieder null. Der Grund ist strukturell, nicht Nachlaessigkeit: Es gab
keinen Ort fuer einen Eintrag ohne Version. Den gibt es jetzt — changelog.d/ —
und dieser Pruefer sorgt dafuer, dass er benutzt wird.

Der Pruefer liest eine Dateiliste, nie ein Repository und nie das Netz. Damit
haengt sein Ergebnis allein von seiner Eingabe ab, nie vom Zeitpunkt des Aufrufs
— dieselbe Entscheidung wie in scripts/pflicht_checks.py, und aus demselben
Grund (#196). Der Preis ist, dass der Aufrufer die Liste beschaffen muss; das
tut der Job „Changelog-Eintrag" in .github/workflows/ci.yml.

    gh pr view 42 --json files --jq '.files[].path' \\
      | python3 scripts/changelog_pflicht.py --autor siluri --label P1

Verwendet von .github/workflows/ci.yml.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from changelog import FRAGMENTE, RUBRIKEN, fragment_mangel  # noqa: E402

REPO = Path(__file__).resolve().parent.parent

# Abhaengigkeits-Aktualisierungen kommen im Dutzend und tragen einzeln nichts
# zum Verlauf bei. Sie erscheinen beim Release als ein Sammelpunkt.
#
# BEIDE Schreibweisen, und das ist kein Guertel-und-Hosentraeger: `gh pr view
# --json author` meldet `app/dependabot` (am 02.09.2026 an PR #222 gemessen),
# waehrend `github.actor` und die REST-API `dependabot[bot]` liefern. Wer nur
# die zweite eintraegt, baut eine Ausnahme, die nie greift — und merkt es nicht,
# weil ein nicht greifender Sonderfall sich wie ein strenger Pruefer anfuehlt.
AUSNAHME_AUTOREN = frozenset({
    "app/dependabot",
    "dependabot[bot]",
    "dependabot-preview[bot]",
})

# Die ausdrueckliche Einzelfall-Ausnahme. Sie steht am Vorgang und ist damit
# sichtbar und begruendbar — anders als ein stiller Sonderweg im Code.
AUSNAHME_LABEL = "ohne-changelog"


def ist_fragment(pfad: str) -> bool:
    return pfad.startswith("changelog.d/") and pfad.endswith(".md")


def verlangt_keinen_punkt(pfad: str) -> bool:
    """Ein Pfad, der fuer sich genommen nichts zum Verlauf beitraegt.

    Drei Gruppen, und die Grenze ist mit Absicht eng gezogen:

    * `docs/**` und die Markdown-Dateien im Wurzelverzeichnis — Prosa ueber das
      Werkzeug, nicht das Werkzeug. Dazu gehoert CHANGELOG.md selbst.
    * `tests/**` — eine Zusicherung ohne Verhaltensaenderung.
    * `changelog.d/**` — die Eintraege selbst; sonst verlangte ein Vorgang, der
      nur einen Eintrag nachtraegt, wieder einen Eintrag.

    Ausdruecklich **nicht** dabei ist `skill/**`, auch nicht die Markdown-Datei
    `skill/references/din5008.md`: Das ist die Quelle der Normregeln, ihre
    Aenderung aendert das Verhalten des Linters. Wer sie unter „Doku" faellen
    liesse, koennte den Sollwert einer Regel aendern, ohne dass es jemand im
    Verlauf sieht.
    """
    if pfad.startswith(("docs/", "tests/")):
        return True
    if ist_fragment(pfad):
        return True
    return "/" not in pfad and pfad.endswith(".md")


def maengel_der_fragmente(verzeichnis: Path = FRAGMENTE) -> list[str]:
    """Alle Fragmente auf einmal pruefen — nicht nur die dieses Vorgangs.

    Ein kaputtes Fragment blockiert, egal wer es abgelegt hat: Beim Buendeln
    faellt es sonst unter den Tisch, und das merkt niemand, weil ein fehlender
    Punkt nichts meldet.
    """
    if not verzeichnis.is_dir():
        return []
    return [m for m in (fragment_mangel(p) for p in sorted(verzeichnis.glob("*.md"))) if m]


def pruefe(pfade: list[str], autor: str = "", labels: tuple[str, ...] = (),
           verzeichnis: Path = FRAGMENTE) -> tuple[bool, str]:
    """(in Ordnung, Begruendung) — die ganze Entscheidung an einer Stelle."""
    maengel = maengel_der_fragmente(verzeichnis)
    if maengel:
        return False, ("Fragmente in changelog.d/ sind unbrauchbar:\n  "
                       + "\n  ".join(maengel))

    if autor in AUSNAHME_AUTOREN:
        return True, f"{autor} ist von der Eintragspflicht ausgenommen."
    if AUSNAHME_LABEL in labels:
        return True, f"Label „{AUSNAHME_LABEL}“ gesetzt — ausdrücklich ausgenommen."

    if any(ist_fragment(p) for p in pfade):
        return True, "Eintrag liegt in changelog.d/."

    # Die Ausnahme greift nur, wenn ALLE Pfade hineinfallen. Ein Vorgang, der
    # Code und Doku zugleich anfasst, ist eine Änderung am Werkzeug — daran
    # ändert die Doku nichts.
    if pfade and all(verlangt_keinen_punkt(p) for p in pfade):
        return True, "Nur Doku, Tests und Einträge geändert — kein Punkt nötig."

    verlangend = [p for p in pfade if not verlangt_keinen_punkt(p)]
    return False, (
        "Dieser Vorgang ändert das Werkzeug, trägt aber keinen Punkt in den Verlauf ein.\n"
        "\n"
        "Ohne Eintrag: " + ", ".join(sorted(verlangend)[:5])
        + (" …" if len(verlangend) > 5 else "") + "\n"
        "\n"
        "Eine Datei anlegen, benannt „<vorgang>.<rubrik>.md“:\n"
        "\n"
        "    changelog.d/229.behoben.md\n"
        "\n"
        "Rubriken: " + ", ".join(RUBRIKEN) + "\n"
        "Inhalt: der Listenpunkt im Wortlaut, wie er später im Changelog steht —\n"
        "keine Kurzfassung, er wandert unverändert in die README.\n"
        "\n"
        "    - **Kurz, was sich ändert.** Ein, zwei Sätze warum. (#229)\n"
        "\n"
        "Trägt der Vorgang wirklich nichts zum Verlauf bei, setzt ein Maintainer\n"
        f"das Label „{AUSNAHME_LABEL}“."
    )


def aus_pr_json(text: str) -> tuple[list[str], str, tuple[str, ...]]:
    """(Pfade, Autor, Labels) aus der Ausgabe von `gh pr view --json ...`.

    Ein Label darf Leerzeichen enthalten („good first issue"), und genau daran
    zerbricht der naheliegende Weg: Labels als Wortliste durch die Shell zu
    reichen und dort unquoted zu expandieren. Hier kommen sie in einem Stueck an.
    """
    daten = json.loads(text)
    return (
        [d["path"] for d in daten.get("files") or []],
        (daten.get("author") or {}).get("login", ""),
        tuple(l["name"] for l in daten.get("labels") or []),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--autor", default="", help="Login des Autors")
    parser.add_argument("--label", action="append", default=[], help="Label (mehrfach)")
    parser.add_argument("--pr-json", type=Path,
                        help="Ausgabe von `gh pr view --json files,author,labels`")
    parser.add_argument("--verzeichnis", type=Path, default=FRAGMENTE)
    parser.add_argument("dateien", nargs="*",
                        help="geänderte Pfade; ohne Angabe von der Standardeingabe")
    args = parser.parse_args()

    if args.pr_json:
        pfade, autor, labels = aus_pr_json(args.pr_json.read_text(encoding="utf-8"))
        gut, grund = pruefe(pfade, autor, labels, args.verzeichnis)
        print(grund, file=sys.stdout if gut else sys.stderr)
        return 0 if gut else 1

    pfade = args.dateien or [z.strip() for z in sys.stdin if z.strip()]
    if not pfade:
        print("Keine geänderten Dateien übergeben — so kann nichts geprüft werden.",
              file=sys.stderr)
        return 1

    gut, grund = pruefe(pfade, args.autor, tuple(args.label), args.verzeichnis)
    print(grund, file=sys.stdout if gut else sys.stderr)
    return 0 if gut else 1


if __name__ == "__main__":
    raise SystemExit(main())
