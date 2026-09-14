#!/usr/bin/env python3
"""Baut die Gegenproben zur Rechnung eines Kleinunternehmers (#317, ADR 0041).

    python3 scripts/erechnung_kleinunternehmer_gegenprobe.py ohne-hinweis rechnung.xml ziel.xml
    python3 scripts/erechnung_kleinunternehmer_gegenprobe.py mit-satz rechnung.xml ziel.xml

`ohne-hinweis` entfernt BT-120 (`ExemptionReason`) und BT-33 (`Description` des
Verkäufers) — die Datei muss an BR-E-10 scheitern. `mit-satz` setzt jeden
`RateApplicablePercent` mit Kategorie E auf 19.00 — sie muss an BR-E-05
scheitern. Per ElementTree und gezählt wie `erechnung_ohne_referenz.py`: Findet
die Änderung nichts zu ändern, entsteht keine Datei (Exit 1) — sonst wäre die
„Gegenprobe" ein gültiges Dokument und belegte nichts.
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from erechnung_ohne_referenz import QDT, RAM, RSM, UDT


def gegenprobe(art: str, quelle: Path, ziel: Path) -> int:
    """Schreibt `ziel` und gibt die Zahl der Änderungen zurück (0 → keine Datei)."""
    for praefix, raum in (("rsm", RSM), ("ram", RAM), ("udt", UDT), ("qdt", QDT)):
        ET.register_namespace(praefix, raum)
    baum = ET.parse(quelle)
    wurzel = baum.getroot()
    geaendert = 0
    if art == "ohne-hinweis":
        for eltern in list(wurzel.iter()):
            for kind in list(eltern):
                ist_grund = kind.tag == f"{{{RAM}}}ExemptionReason"
                ist_bt33 = (kind.tag == f"{{{RAM}}}Description"
                            and eltern.tag == f"{{{RAM}}}SellerTradeParty")
                if ist_grund or ist_bt33:
                    eltern.remove(kind)
                    geaendert += 1
        rest = len(wurzel.findall(f".//{{{RAM}}}ExemptionReason"))
        if rest or geaendert < 2:
            return 0
    elif art == "mit-satz":
        for steuer in wurzel.iter(f"{{{RAM}}}ApplicableTradeTax"):
            if steuer.findtext(f"{{{RAM}}}CategoryCode") != "E":
                continue
            satz = steuer.find(f"{{{RAM}}}RateApplicablePercent")
            if satz is not None:
                satz.text = "19.00"
                geaendert += 1
    else:
        raise ValueError(art)
    if geaendert:
        baum.write(ziel, encoding="UTF-8", xml_declaration=True)
    return geaendert


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 3 or argv[0] not in ("ohne-hinweis", "mit-satz"):
        print(__doc__, file=sys.stderr)
        return 2
    geaendert = gegenprobe(argv[0], Path(argv[1]), Path(argv[2]))
    print(f"{argv[0]}: {geaendert} Stelle(n) geändert")
    if not geaendert:
        print("FEHL  nichts zu ändern — keine Gegenprobe geschrieben", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
