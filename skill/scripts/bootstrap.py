#!/usr/bin/env python3
"""Prüft die Laufzeitabhängigkeiten von falzmarke und installiert sie bei Bedarf.

Zwei Wege, in dieser Reihenfolge:

1. **Aus dem Paket, ohne Netz.** Liegt neben diesem Skript ein `vendor/` mit
   Wheels, wird zuerst daraus installiert (`--no-index`). Das Skill-Paket bringt
   das `typst`-Wheel mit — von den fünf Abhängigkeiten die einzige mit nativem
   Binärkern und deshalb die, die in einer Sandbox als Erste fehlt.
2. **Von PyPI**, falls danach noch etwas offen ist und Netzzugriff besteht.

Warum je Requirement einzeln aus `vendor/`: `pip install --no-index` bricht
komplett ab, sobald für **ein** genanntes Paket kein Wheel danebenliegt — es
installiert dann auch die anderen nicht. Ein Paket, das nur `typst` mitbringt,
hätte damit gar nichts ausgerichtet.

Exit 0: alles vorhanden (oder erfolgreich installiert)
Exit 1: Installation nicht möglich — die Meldung nennt den Grund
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

# Modulname -> pip-Requirement. Alle Abhängigkeiten tragen eine permissive
# Lizenz (MIT/BSD/Apache); siehe THIRD_PARTY_LICENSES.md. Das ist kein Zufall:
# PyMuPDF wäre technisch geeignet, ist aber AGPL-3.0 und hätte jede Firma, die
# falzmarke einbaut, in die AGPL gezwungen.
DEPS = {
    "typst": "typst>=0.15,<0.16",
    "yaml": "pyyaml>=6",
    "pdfplumber": "pdfplumber>=0.11",
    "pypdf": "pypdf>=5",
    "markdown_it": "markdown-it-py>=4,<5",
    "PIL": "pillow>=10",
}

#: Wheels, die mit dem Skill-Paket ausgeliefert werden. Im Quellbaum ist das
#: Verzeichnis leer — siehe `vendor/README.md`; gefüllt wird es beim Packen.
VENDOR = Path(__file__).resolve().parent.parent / "vendor"


def fehlende() -> dict[str, str]:
    return {m: r for m, r in DEPS.items() if importlib.util.find_spec(m) is None}


def wheels() -> list[Path]:
    return sorted(VENDOR.glob("*.whl")) if VENDOR.is_dir() else []


def _pip(reqs: list[str], extra: list[str]) -> tuple[bool, str]:
    """Erst der normale Weg, dann der Sandbox-Weg mit --break-system-packages."""
    basis = [sys.executable, "-m", "pip", "install", "--quiet", "--disable-pip-version-check"]
    letzter_fehler = ""
    for schutz in ([], ["--break-system-packages"]):
        ergebnis = subprocess.run(basis + schutz + extra + reqs,
                                  capture_output=True, text=True)
        if ergebnis.returncode == 0:
            return True, ""
        letzter_fehler = ergebnis.stderr.strip()
    return False, letzter_fehler


def aus_dem_paket(offen: dict[str, str]) -> None:
    """Ohne Netz, aus `vendor/`. Fehlschläge sind hier normal und still:
    Was kein Wheel danebenliegen hat, holt der nächste Schritt."""
    for req in offen.values():
        _pip([req], ["--no-index", "--find-links", str(VENDOR)])


def main() -> int:
    offen = fehlende()
    if not offen:
        print("OK  Alle Abhängigkeiten vorhanden.")
        return 0

    vorrat = wheels()
    print(f"Fehlend: {', '.join(offen)} — installiere …")

    if vorrat:
        print(f"    aus dem Paket, ohne Netz ({len(vorrat)} Wheel(s) in vendor/)")
        aus_dem_paket(offen)
        offen = fehlende()

    fehler = ""
    if offen:
        if vorrat:
            print(f"    noch offen: {', '.join(offen)} — versuche PyPI")
        erfolg, fehler = _pip(list(offen.values()), [])
        offen = fehlende()

    if offen:
        print(
            f"FEHLER  Diese Pakete fehlen weiterhin: {', '.join(offen)}\n"
            f"        Im Paket lagen {len(vorrat)} Wheel(s); für die oben genannten war keines "
            "dabei,\n"
            "        und PyPI war nicht erreichbar.\n"
            "        Ohne sie gibt es bewusst keinen Ersatz-Renderer — ein zweiter Renderer "
            "würde\n"
            "        ein anderes Layout erzeugen, und die Nachmessung wäre wertlos.",
            file=sys.stderr,
        )
        if fehler:
            print(f"        pip meldete: {fehler.splitlines()[-1]}", file=sys.stderr)
        return 1

    print("OK  Abhängigkeiten installiert.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
