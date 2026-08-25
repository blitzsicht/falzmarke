#!/usr/bin/env python3
"""Prüft die Laufzeitabhängigkeiten von normbrief und installiert sie bei Bedarf.

Exit 0: alles vorhanden (oder erfolgreich installiert)
Exit 1: Installation nicht möglich — die Meldung nennt den Grund
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

# Modulname -> pip-Requirement
DEPS = {
    "typst": "typst>=0.15,<0.16",
    "yaml": "pyyaml>=6",
    "fitz": "pymupdf>=1.24",
}


def fehlende() -> list[str]:
    return [req for modul, req in DEPS.items() if importlib.util.find_spec(modul) is None]


def installiere(reqs: list[str]) -> bool:
    """Erst der normale Weg, dann der Sandbox-Weg mit --break-system-packages."""
    basis = [sys.executable, "-m", "pip", "install", "--quiet", "--disable-pip-version-check"]
    for extra in ([], ["--break-system-packages"]):
        ergebnis = subprocess.run(basis + extra + reqs, capture_output=True, text=True)
        if ergebnis.returncode == 0:
            return True
        letzter_fehler = ergebnis.stderr.strip()
    print(letzter_fehler, file=sys.stderr)
    return False


def main() -> int:
    offen = fehlende()
    if not offen:
        print("OK  Alle Abhängigkeiten vorhanden.")
        return 0

    print(f"Fehlend: {', '.join(offen)} — installiere …")
    if not installiere(offen):
        print(
            "FEHLER  Installation fehlgeschlagen.\n"
            "        normbrief braucht Netzwerkzugriff für den ersten Lauf "
            f"({', '.join(offen)}).\n"
            "        Ohne diese Pakete gibt es bewusst keinen Ersatz-Renderer — "
            "ein zweiter Renderer würde ein anderes Layout erzeugen.",
            file=sys.stderr,
        )
        return 1

    noch_offen = fehlende()
    if noch_offen:
        print(f"FEHLER  Nach der Installation weiterhin fehlend: {', '.join(noch_offen)}", file=sys.stderr)
        return 1

    print("OK  Abhängigkeiten installiert.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
