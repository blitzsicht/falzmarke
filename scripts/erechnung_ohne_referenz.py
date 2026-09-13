#!/usr/bin/env python3
"""Baut die Gegenprobe für XRechnung: dieselbe XML ohne Käuferreferenz (BT-10).

    python3 scripts/erechnung_ohne_referenz.py eigene-xrechnung.xml ohne-referenz.xml

Entfernt wird per ElementTree, nicht per Textersetzung, und gezählt wird vorher
und nachher: genau eine `BuyerReference` davor, keine danach — sonst Exit 1 und
keine Datei. Eine Gegenprobe, die auf einem beschädigten Dokument beruht, fiele
bei Mustang aus dem falschen Grund durch; deshalb nennt die CI die erwartete
Regel (`::BR-DE-15`) und `erechnung_pruefen.py` hält die Ausgabe dagegen (#117).
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

RSM = "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
RAM = "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
UDT = "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100"
QDT = "urn:un:unece:uncefact:data:standard:QualifiedDataType:100"
REFERENZ = f"{{{RAM}}}BuyerReference"


def ohne_referenz(quelle: Path, ziel: Path) -> tuple[int, int]:
    """Schreibt `ziel` ohne BuyerReference. Gibt (vorher, nachher) zurück."""
    for praefix, raum in (("rsm", RSM), ("ram", RAM), ("udt", UDT), ("qdt", QDT)):
        ET.register_namespace(praefix, raum)
    baum = ET.parse(quelle)
    wurzel = baum.getroot()
    vorher = len(wurzel.findall(f".//{REFERENZ}"))
    for eltern in list(wurzel.iter()):
        for kind in list(eltern):
            if kind.tag == REFERENZ:
                eltern.remove(kind)
    nachher = len(wurzel.findall(f".//{REFERENZ}"))
    if vorher == 1 and nachher == 0:
        baum.write(ziel, encoding="UTF-8", xml_declaration=True)
    return vorher, nachher


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    vorher, nachher = ohne_referenz(Path(argv[0]), Path(argv[1]))
    print(f"BuyerReference vorher {vorher}, nachher {nachher}")
    if (vorher, nachher) != (1, 0):
        print("FEHL  erwartet genau eine BuyerReference davor und keine danach — "
              "keine Gegenprobe geschrieben", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
