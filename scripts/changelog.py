#!/usr/bin/env python3
"""Traegt die juengsten Aenderungen in die README ein — aus CHANGELOG.md.

Anlass: Viele Projekte fuehren ihren Verlauf in der README, damit man ihn sieht,
ohne eine zweite Datei zu oeffnen. Das ist ein echter Gewinn — aber eine zweite
Fassung derselben Sache driftet auseinander. Dieses Repository hat dafuer schon
ein Muster: docs/ROADMAP.md kommt aus den Issues, die Quellenlage aus
din5008.yaml. Der README-Abschnitt kommt also aus CHANGELOG.md.

    python3 scripts/changelog.py            # Abschnitt in die README schreiben
    python3 scripts/changelog.py --pruefen  # nur melden, ob er auf dem Stand ist

Uebernommen wird der WORTLAUT der juengsten Versionen, nicht eine Kurzfassung.
Der naheliegende Weg waere gewesen, je Punkt nur den fett gesetzten Anfang zu
zeigen. 19 der 73 Punkte in CHANGELOG.md haben keinen — sie stehen allerdings
alle in v0.2 und v0.3, also ausserhalb dessen, was der Auszug heute zeigt. Eine
solche Kuerzung liefe hier also unbemerkt durch und faellt erst auf, wenn eine
kuenftige Version einen schmucklosen Punkt enthaelt. Genau dafuer steht
tests/test_changelog.py::test_ein_schmuckloser_punkt_ueberlebt_den_auszug.

Angepasst wird allein die Ueberschriftenebene, damit die Gliederung der README
heil bleibt.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
QUELLE = REPO / "CHANGELOG.md"
ZIEL = REPO / "README.md"
MARKE_START = "<!-- changelog:anfang -->"
MARKE_ENDE = "<!-- changelog:ende -->"

# Absolut, nicht relativ: Die README wird auch auf PyPI gerendert, und dort
# zeigt ein relativer Verweis ins Leere. tests/test_readme_auf_pypi.py haelt
# das fest — diese Zeile ist einmal dagegen gelaufen.
CHANGELOG_URL = "https://github.com/blitzsicht/falzmarke/blob/main/CHANGELOG.md"

# Zwei Versionen. Mehr macht aus der Produktseite ein Archiv; weniger zeigt
# keine Bewegung. Wer alles will, folgt dem Link auf CHANGELOG.md.
VERSIONEN = 2

# Kleine Zahlen im Fließtext werden ausgeschrieben.
ZAHLWORT = {2: "zwei", 3: "drei", 4: "vier", 5: "fünf"}

VERSION_KOPF = re.compile(r"^## (v\d+\.\d+\.\d+.*)$", re.MULTILINE)


def versionen(text: str) -> list[tuple[str, str]]:
    """Zerlegt CHANGELOG.md in (Ueberschrift, Rumpf), juengste zuerst."""
    treffer = list(VERSION_KOPF.finditer(text))
    if not treffer:
        raise SystemExit(
            f"{QUELLE.name} enthält keine Überschrift der Form „## v1.2.3“.\n"
            "Entweder hat sich das Format geändert oder die Datei ist leer — "
            "beides muss auffallen, statt einen leeren Abschnitt zu erzeugen."
        )
    abschnitte = []
    for nummer, kopf in enumerate(treffer):
        ende = treffer[nummer + 1].start() if nummer + 1 < len(treffer) else len(text)
        abschnitte.append((kopf.group(1), text[kopf.end():ende].strip("\n")))
    return abschnitte


def _tiefer(rumpf: str) -> str:
    """Jede Überschrift eine Ebene tiefer — sonst zerschneidet der Auszug die README."""
    return re.sub(r"^(#{1,5}) ", r"#\1 ", rumpf, flags=re.MULTILINE)


def abschnitt() -> str:
    alle = versionen(QUELLE.read_text(encoding="utf-8"))
    gezeigt = alle[:VERSIONEN]
    zeilen = [
        MARKE_START,
        "",
        "## Was sich zuletzt getan hat",
        "",
        f"Die {'letzte Version' if len(gezeigt) == 1 else 'letzten ' + ZAHLWORT.get(len(gezeigt), str(len(gezeigt))) + ' Versionen'}"
        f" im Wortlaut. **Erzeugt aus [`CHANGELOG.md`]({CHANGELOG_URL}) — dort ändern, dann"
        " `python3 scripts/changelog.py`.**",
        "",
    ]
    for kopf, rumpf in gezeigt:
        zeilen += [f"### {kopf}", "", _tiefer(rumpf), ""]
    aeltere = len(alle) - len(gezeigt)
    if aeltere:
        zeilen += [
            f"Davor liegen {aeltere} weitere Versionen — der vollständige Verlauf steht in"
            f" [`CHANGELOG.md`]({CHANGELOG_URL}).",
            "",
        ]
    zeilen.append(MARKE_ENDE)
    return "\n".join(zeilen)


def eingesetzt(text: str) -> str:
    neu = abschnitt()
    if MARKE_START in text and MARKE_ENDE in text:
        vorher = text[: text.index(MARKE_START)]
        nachher = text[text.index(MARKE_ENDE) + len(MARKE_ENDE):]
        return vorher + neu + nachher
    # Ans Ende zu haengen waere falsch: Der Verlauf gehoert vor die Lizenz, nicht
    # dahinter. Wer den Abschnitt neu anlegt, setzt die Marken selbst.
    raise SystemExit(
        f"In {ZIEL.name} fehlen die Marken {MARKE_START} und {MARKE_ENDE}.\n"
        "Beide dort einsetzen, wo der Abschnitt stehen soll — vor „## Lizenz“."
    )


def main() -> int:
    text = ZIEL.read_text(encoding="utf-8")
    neu = eingesetzt(text)
    if "--pruefen" in sys.argv:
        if neu != text:
            print(f"{ZIEL.name} ist nicht auf dem Stand von {QUELLE.name} — "
                  "python3 scripts/changelog.py ausführen.", file=sys.stderr)
            return 1
        print(f"{ZIEL.name} ist aktuell.")
        return 0
    ZIEL.write_text(neu, encoding="utf-8")
    gezeigt = versionen(QUELLE.read_text(encoding="utf-8"))[:VERSIONEN]
    print(f"OK  {ZIEL.relative_to(REPO)} zeigt "
          + ", ".join(kopf.split(" ")[0] for kopf, _ in gezeigt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
