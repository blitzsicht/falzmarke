#!/usr/bin/env python3
"""Aufruf ohne Installation.

Der Skill muss auf claude.ai laufen, wo nichts eingerichtet werden kann. Dieses
Skript legt den Skill-Ordner auf den Suchpfad und ruft dieselbe main()-Funktion
auf, die auch der installierte Befehl `normbrief` benutzt — es gibt keine
zweite Fassung, die auseinanderlaufen könnte.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from normbrief.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
