#!/usr/bin/env python3
"""Baut die Gegenprobe zu #316: dieselbe XML ohne Verkäuferkennung (BT-29).

    python3 scripts/erechnung_ohne_kennung.py nur-steuernummer.xml ohne-kennung.xml

Entfernt wird nur `ram:ID` direkt unter `SellerTradeParty` — andere `ram:ID`
(Rechnungsnummer, Steuernummer in `SpecifiedTaxRegistration`) bleiben. Gezählt
wird wie in `erechnung_ohne_referenz.py`: genau eine Kennung davor, keine
danach, sonst Exit 1 und keine Datei. Die CI erwartet von Mustang und dem
KoSIT-Validator, dass diese Datei an genau BR-CO-26 scheitert.
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from erechnung_ohne_referenz import QDT, RAM, RSM, UDT

VERKAEUFER = f"{{{RAM}}}SellerTradeParty"
KENNUNG = f"{{{RAM}}}ID"


def ohne_kennung(quelle: Path, ziel: Path) -> tuple[int, int]:
    """Schreibt `ziel` ohne BT-29. Gibt (vorher, nachher) zurück."""
    for praefix, raum in (("rsm", RSM), ("ram", RAM), ("udt", UDT), ("qdt", QDT)):
        ET.register_namespace(praefix, raum)
    baum = ET.parse(quelle)
    verkaeufer = baum.getroot().findall(f".//{VERKAEUFER}")
    vorher = sum(len(v.findall(KENNUNG)) for v in verkaeufer)
    for partei in verkaeufer:
        for kind in partei.findall(KENNUNG):
            partei.remove(kind)
    nachher = sum(len(v.findall(KENNUNG)) for v in verkaeufer)
    if vorher == 1 and nachher == 0:
        baum.write(ziel, encoding="UTF-8", xml_declaration=True)
    return vorher, nachher


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    vorher, nachher = ohne_kennung(Path(argv[0]), Path(argv[1]))
    print(f"SellerTradeParty/ID vorher {vorher}, nachher {nachher}")
    if (vorher, nachher) != (1, 0):
        print("FEHL  erwartet genau eine Verkäuferkennung davor und keine danach — "
              "keine Gegenprobe geschrieben", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
