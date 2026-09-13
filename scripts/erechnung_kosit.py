#!/usr/bin/env python3
"""Prüft XRechnungen mit dem KoSIT-Validator — der zweite fremde Prüfer (#311).

Mustang (`erechnung_pruefen.py`) ist eine Implementierung; der KoSIT-Validator
mit der Konfiguration für XRechnung ist das Werkzeug der herausgebenden Stelle
und bringt die jeweils aktuelle Schematron-Fassung mit. Beide urteilen
unabhängig voneinander über dieselben Dateien.

    python3 scripts/erechnung_kosit.py --validator validator-1.6.3-standalone.jar \\
        --konfiguration konfiguration/ \\
        --gut eigene-xrechnung.xml --schlecht ohne-referenz.xml::BR-DE-15

**Das Urteil kommt aus dem Bericht**, nicht aus dem Exit-Code: `rep:accept` oder
`rep:reject` in `<datei>-report.xml`, dazu das Szenario, das der Validator
angewendet hat. Nur „EN16931 XRechnung (CII)“ zählt — unter einem anderen
Szenario prüfte er nicht die XRechnung-Regeln, auch wenn er annimmt.

`datei::REGEL` bei `--schlecht`: Die Gegenprobe muss an genau dieser Regel
scheitern; fällt sie aus einem anderen Grund, ist das ein Befund.

Exit 0: alles wie erwartet. Exit 1: ein Befund. Exit 2: NICHT GEPRÜFT — Java
fehlt, das Werkzeug oder die Konfiguration fehlt oder ist nicht das vereinbarte,
oder es entstand kein Bericht.

Gemessen am 13.09.2026 (Validator 1.6.3, Konfiguration 2026-08-31): Exit 0 bei
ACCEPTABLE, Exit 1 bei REJECT; der Bericht liegt als `<stamm>-report.xml` im
Ausgabeverzeichnis.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from erechnung_pruefen import (  # noqa: E402
    Ausfuehren, GUELTIG, UNGUELTIG, Fehlt, _subprocess, java_funktioniert, sha256,
)

#: Das vereinbarte Werkzeug und die vereinbarte Konfiguration — eine Quelle für
#: Fassung und Prüfsumme. Die CI lädt nur; `tests/test_erechnung_kosit.py` hält
#: die Adressen in `ci.yml` an diese Werte gebunden.
VALIDATOR_VERSION = "1.6.3"
VALIDATOR_SHA256 = "799e64befca97d4080e03608c80b85dd5a5ecc5f4ae4f35d1116ec2855b9a7c9"
KONFIGURATION_STAND = "2026-08-31"
KONFIGURATION_SHA256 = "2530cd107c414511c5d0462ec10f886910395abfca820db82e83d70bf01221a8"

#: Das Szenario, unter dem eine XRechnung in CII geprüft wird.
SZENARIO_XRECHNUNG_CII = "EN16931 XRechnung (CII)"

NS = {
    "rep": "http://www.xoev.de/de/validator/varl/1",
    "s": "http://www.xoev.de/de/validator/framework/1/scenarios",
    "svrl": "http://purl.oclc.org/dsdl/svrl",
}


def pruefe_validator(pfad: Path) -> None:
    if not pfad.is_file():
        raise Fehlt(f"KoSIT-Validator nicht gefunden: {pfad}")
    ist = sha256(pfad)
    if ist != VALIDATOR_SHA256:
        raise Fehlt(
            f"der KoSIT-Validator hat nicht die vereinbarte Prüfsumme — erwartet "
            f"{VALIDATOR_SHA256[:16]}…, gefunden {ist[:16]}…. Ein anderes Werkzeug als "
            "vereinbart urteilt nicht.")


def konfigurationsname(konfiguration: Path) -> str:
    """Der Name der Konfiguration aus `scenarios.xml` — gelesen, nicht angenommen."""
    datei = konfiguration / "scenarios.xml"
    if not datei.is_file():
        raise Fehlt(f"keine scenarios.xml in {konfiguration}")
    name = ET.parse(datei).getroot().find("s:name", NS)
    return (name.text or "").strip() if name is not None else "Konfiguration ohne Namen"


def befehl(java: str, jar: Path, konfiguration: Path, ausgabe: Path, datei: Path) -> list[str]:
    return [java, "-jar", str(jar), "-s", str(konfiguration / "scenarios.xml"),
            "-r", str(konfiguration), "-o", str(ausgabe), str(datei)]


def lies_bericht(pfad: Path) -> dict:
    """Urteil, Szenario, Engine und die verletzten Regeln aus einem Bericht."""
    wurzel = ET.parse(pfad).getroot()
    urteil = None
    if wurzel.find("rep:assessment/rep:accept", NS) is not None:
        urteil = GUELTIG
    elif wurzel.find("rep:assessment/rep:reject", NS) is not None:
        urteil = UNGUELTIG
    szenario = wurzel.find("rep:scenarioMatched/s:scenario/s:name", NS)
    engine = wurzel.find("rep:engine/rep:name", NS)
    # Die Regel steht als `rep:message code="BR-DE-15" level="error"` — gemessen am
    # echten Bericht (13.09.2026). Eine erste Fassung suchte `svrl:failed-assert`;
    # der nachgestellte Bericht im Test trug dieselbe falsche Annahme und blieb
    # grün, erst der Lauf gegen den echten Validator zeigte „ohne Regel".
    regeln = {m.get("code") for m in wurzel.iter(f"{{{NS['rep']}}}message")
              if m.get("code") and m.get("level") in ("error", "fatal")}
    return {
        "urteil": urteil,
        "szenario": (szenario.text or "").strip() if szenario is not None else "",
        "engine": (engine.text or "").strip() if engine is not None else "",
        "regeln": regeln,
    }


def main(argv: list[str] | None = None, ausfuehren: Ausfuehren | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--validator", type=Path, required=True, help="KoSIT-Validator (standalone-JAR)")
    p.add_argument("--konfiguration", type=Path, required=True,
                   help="entpackte Validator-Konfiguration XRechnung (mit scenarios.xml)")
    p.add_argument("--java", default="java", help="Java-Aufruf (Vorgabe: java)")
    p.add_argument("--gut", type=Path, nargs="*", default=[], help="Dateien, die bestehen müssen")
    p.add_argument("--schlecht", nargs="*", default=[],
                   help="Dateien, die abgelehnt werden müssen; `datei::REGEL` verlangt genau diese Regel")
    args = p.parse_args(argv)
    lauf: Ausfuehren = ausfuehren or _subprocess

    if not java_funktioniert(args.java, lauf):
        print(f"NICHT GEPRÜFT: `{args.java} -version` läuft nicht.", file=sys.stderr)
        return 2
    try:
        pruefe_validator(args.validator)
        konfiguration = konfigurationsname(args.konfiguration)
    except Fehlt as f:
        print(f"NICHT GEPRÜFT: {f}", file=sys.stderr)
        return 2

    erwartung: list[tuple[Path, str, str | None]] = [(d, GUELTIG, None) for d in args.gut]
    for eintrag in args.schlecht:
        pfad, _, regel = str(eintrag).partition("::")
        erwartung.append((Path(pfad), UNGUELTIG, regel or None))

    befunde = nicht_geprueft = 0
    engines: list[str] = []
    with tempfile.TemporaryDirectory(prefix="kosit-") as tmp:
        for datei, soll, regel in erwartung:
            if not datei.is_file():
                print(f"FEHL  {datei} — Datei fehlt")
                befunde += 1
                continue
            vorher = sha256(datei)
            ziel = Path(tmp) / datei.stem
            ziel.mkdir(exist_ok=True)
            lauf(befehl(args.java, args.validator, args.konfiguration, ziel, datei))
            bericht_pfad = ziel / f"{datei.stem}-report.xml"
            if not bericht_pfad.is_file():
                print(f"NICHT GEPRÜFT  {datei.name} — kein Bericht, kein Urteil")
                nicht_geprueft += 1
                continue
            bericht = lies_bericht(bericht_pfad)
            if bericht["engine"] and bericht["engine"] not in engines:
                engines.append(bericht["engine"])
            marke = f"[{bericht['engine'] or 'Engine unbekannt'} · {konfiguration}]"
            if bericht["szenario"] != SZENARIO_XRECHNUNG_CII:
                print(f"FEHL  {datei.name} — Szenario „{bericht['szenario'] or 'keins'}“ statt "
                      f"„{SZENARIO_XRECHNUNG_CII}“  {marke}")
                befunde += 1
            elif bericht["urteil"] is None:
                print(f"NICHT GEPRÜFT  {datei.name} — der Bericht enthält kein Urteil  {marke}")
                nicht_geprueft += 1
            elif bericht["urteil"] != soll:
                gruende = ", ".join(sorted(bericht["regeln"])) or "ohne Regel"
                print(f"FEHL  {datei.name} — erwartet {soll}, KoSIT sagt {bericht['urteil']} "
                      f"({gruende})  {marke}")
                befunde += 1
            elif regel and regel not in bericht["regeln"]:
                print(f"FEHL  {datei.name} — abgelehnt, aber nicht an {regel} "
                      f"({', '.join(sorted(bericht['regeln'])) or 'ohne Regel'})  {marke}")
                befunde += 1
            else:
                art = "abgelehnt" + (f" an {regel}" if regel else "") if soll == UNGUELTIG else "angenommen"
                print(f"OK    {datei.name}  {art}  sha256={vorher[:16]}…  {marke}")
            if sha256(datei) != vorher:
                print(f"FEHL  {datei.name} — Datei hat sich während der Prüfung geändert")
                befunde += 1

    if not args.gut:
        print("FEHL  keine Datei, die bestehen muss — der Lauf belegt nichts")
        befunde += 1
    if not args.schlecht:
        print("FEHL  keine Gegenprobe — ohne eine Datei, die abgelehnt werden muss, belegt ein "
              "grüner Lauf nur, dass der Validator gestartet ist")
        befunde += 1

    print()
    print(f"Regelfassung: {' | '.join(engines) or 'Engine unbekannt'} · {konfiguration} "
          f"(Stand {KONFIGURATION_STAND})")
    if nicht_geprueft:
        print(f"{nicht_geprueft} Datei(en) NICHT GEPRÜFT — kein Grün")
        return 2
    if befunde:
        print(f"{befunde} Befund(e)")
        return 1
    print(f"{len(erwartung)} Datei(en), alle wie erwartet — bestätigt vom KoSIT-Validator, "
          "nicht von uns selbst")
    return 0


if __name__ == "__main__":
    sys.exit(main())
