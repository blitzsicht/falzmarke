#!/usr/bin/env python3
"""Prüft E-Rechnungen mit Mustang — einem fremden Werkzeug (Issue #118).

WARUM ES DIESES SKRIPT GIBT

Ohne eine fremde Prüfung ist die ganze E-Rechnung eine Behauptung. Eine
selbstgeschriebene Prüfung, die das eigene Erzeugnis abnimmt, bestätigt nur,
dass Erzeuger und Prüfer dasselbe meinen. Für PDF/A steht dafür veraPDF in der
CI (`pdf_konformitaet.py`); dies ist das Gegenstück für ZUGFeRD.

Mustang (https://www.mustangproject.org, Apache-2.0) prüft beides, was eine
ZUGFeRD-Rechnung ausmacht: das PDF gegen PDF/A-3 und das eingebettete XML gegen
die Schematron-Regeln des Formats. Es teilt keine Zeile Code mit falzmarke.

ES RECHNET NACH, UND DAS BLEIBT SO

Mustang prüft die Summen einer Rechnung nach („arithmetic recalculation check",
abschaltbar mit `--no-arithmetic-check`). Das Skript schaltet ihn **nicht** ab.
falzmarke rechnet nicht (ADR 0039) — der fremde Prüfer schon, und genau das ist
die Arbeitsteilung: Wer überträgt, lässt nachrechnen.

DAS URTEIL KOMMT AUS DEM EXIT-CODE

Gemessen am 11.09.2026 an Mustang 2.26.0 mit vier Dateien:

    0    gültig        (EN16931_Einfach.pdf, validXRechnung.pdf)
    255  ungültig      (invalidXRechnung.pdf — PDF intakt, XML verletzt BR-DE-2)
    255  ungültig      (eine Datei von 15 Byte)

Alles andere ist ein **Werkzeugfehler**, kein Urteil über die Datei, und ergibt
NICHT GEPRÜFT. Die Textausgabe wird nur für die Meldung gelesen: Wer sie
auswertet, statt den Exit-Code zu nehmen, baut sich einen Check, der bei jeder
Formatänderung still grün wird. Ein Beispiel dafür steht in der Ausgabe selbst:
`validateExpectInvalid` meldet bei erfüllter Erwartung „Overall test result:
valid" — gemeint ist „wie erwartet", nicht „die Datei ist gültig".

JAVA, DAS KEINES IST

Auf macOS liegt unter `/usr/bin/java` ein Platzhalter, der „Unable to locate a
Java Runtime" meldet. `shutil.which("java")` findet ihn trotzdem. Deshalb wird
`java -version` **ausgeführt**, nicht nur gesucht — sonst wäre die Prüfung auf
Existenz genau dann grün, wenn gar kein Java da ist.

DIE REGELFASSUNG

Die Schematron-Regeln haben eine Fassung, und sie ändert sich (#118, Abnahme 2).
Mustang 2.26.0 prüft ZUGFeRD gegen `ZF_250` — die Regeln der Fassung **2.5.0**.
ADR 0039 nennt 2.5.2 als aktuelle Fassung des Standards. Ob sich die Regeln
zwischen 2.5.0 und 2.5.2 unterscheiden, sagt dieses Skript nicht; es sagt,
wogegen tatsächlich geprüft wurde, und schreibt es ins Protokoll.

DIE GEGENPROBE IST PFLICHT

Ohne `--schlecht` ist der Lauf ein Befund. Eine Prüfung, die nur gültige Dateien
sieht, belegt nur, dass Mustang gestartet ist. Die schlechte Datei muss
**inhaltlich** falsch sein, nicht bloß kaputt: Eine Datei von 15 Byte fällt aus
dem banalsten Grund durch („File too small") und sagt nichts über die
Schematron-Prüfung. `invalidXRechnung.pdf` dagegen ist ein intaktes PDF mit
einem XML, das eine Regel verletzt.

    python3 scripts/erechnung_pruefen.py --mustang Mustang-CLI-2.26.0.jar \\
        --gut gut1.pdf gut2.pdf --schlecht schlecht.pdf

Exit 0: alles wie erwartet. Exit 1: ein Befund. Exit 2: NICHT GEPRÜFT — Java
fehlt, das Werkzeug fehlt, es ist nicht das vereinbarte, oder es ist abgestürzt.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

#: Das vereinbarte Werkzeug. Eine Quelle für Version und Prüfsumme: Die CI lädt
#: nur, und `tests/test_erechnung_pruefen.py` hält die Download-Adresse in
#: `ci.yml` an diese Version gebunden. Zwei Pins, die gleich sein müssen, ohne
#: dass etwas sie gleich hält, laufen auseinander (Issue #212).
MUSTANG_VERSION = "2.26.0"
MUSTANG_SHA256 = "42d7868cb68264874a7b8cab4c3587b03b23ccc7cd72373da917f66758bb9736"

GUELTIG = "gültig"
UNGUELTIG = "ungültig"
WERKZEUGFEHLER = "Werkzeugfehler"

#: Exit-Code -> Urteil. Gemessen, siehe Modulkopf.
URTEILE = {0: GUELTIG, 255: UNGUELTIG}

Ausfuehren = Callable[[list[str]], tuple[int, str]]


class Fehlt(Exception):
    """Das Werkzeug ist nicht verfügbar. Das ist NICHT GEPRÜFT, nicht grün."""


def _subprocess(befehl: list[str]) -> tuple[int, str]:
    """Führt aus und gibt (Exit-Code, gesamte Ausgabe) zurück.

    Im temporären Verzeichnis, damit eine Logdatei des Werkzeugs nicht im
    Repository landet.
    """
    with tempfile.TemporaryDirectory(prefix="mustang-") as tmp:
        lauf = subprocess.run(befehl, capture_output=True, text=True, cwd=tmp)
    return lauf.returncode, (lauf.stdout or "") + (lauf.stderr or "")


def java_funktioniert(java: str = "java", ausfuehren: Ausfuehren | None = None) -> bool:
    """Läuft Java wirklich — nicht nur: liegt etwas unter diesem Namen?"""
    ausfuehren = ausfuehren or _subprocess
    try:
        code, _ = ausfuehren([java, "-version"])
    except OSError:
        return False
    return code == 0


def sha256(pfad: Path) -> str:
    h = hashlib.sha256()
    with pfad.open("rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def pruefe_jar(pfad: Path) -> None:
    """Liegt das vereinbarte Werkzeug vor? Sonst ist das Urteil wertlos.

    Eine andere Prüfsumme heißt: ein anderes Werkzeug als vereinbart. Dessen
    Urteil zählt nicht — das ist NICHT GEPRÜFT, kein Befund gegen die Rechnung.
    """
    if not pfad.is_file():
        raise Fehlt(f"Mustang nicht gefunden: {pfad}")
    ist = sha256(pfad)
    if ist != MUSTANG_SHA256:
        raise Fehlt(
            f"Mustang hat nicht die vereinbarte Prüfsumme — erwartet {MUSTANG_SHA256[:16]}…, "
            f"gefunden {ist[:16]}…. Ein anderes Werkzeug als vereinbart urteilt nicht.")


def befehl(java: str, jar: Path, pdf: Path) -> list[str]:
    return [java, "-jar", str(jar), "--action", "validate", "--source", str(pdf)]


def urteil(pdf: Path, jar: Path, java: str = "java",
           ausfuehren: Ausfuehren | None = None) -> tuple[str, str]:
    """(Urteil, Ausgabe) für eine Datei. Das Urteil kommt aus dem Exit-Code."""
    ausfuehren = ausfuehren or _subprocess
    code, ausgabe = ausfuehren(befehl(java, jar, pdf))
    return URTEILE.get(code, WERKZEUGFEHLER), ausgabe


def regelfassung(ausgabe: str) -> str:
    """Wogegen tatsächlich geprüft wurde — aus der Ausgabe gelesen, nicht angenommen."""
    version = re.search(r'<validator version="([^"]+)"', ausgabe)
    regeln = sorted(set(re.findall(r"xslt/((?:ZF|XR)_\d+)/", ausgabe)))
    teile = [f"Mustang {version.group(1)}" if version else "Mustang (Version unbekannt)"]
    teile.append("Schematron " + ", ".join(regeln) if regeln else "Schematron (unbekannt)")
    return " · ".join(teile)


def main(argv: list[str] | None = None, ausfuehren: Ausfuehren | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--mustang", type=Path, required=True, help="Mustang-CLI-JAR")
    p.add_argument("--java", default="java", help="Java-Aufruf (Vorgabe: java)")
    p.add_argument("--gut", type=Path, nargs="*", default=[],
                   help="Dateien, die bestehen müssen")
    p.add_argument("--schlecht", type=Path, nargs="*", default=[],
                   help="Dateien, die durchfallen müssen — die Gegenprobe")
    args = p.parse_args(argv)
    ausfuehren = ausfuehren or _subprocess

    if not java_funktioniert(args.java, ausfuehren):
        print(f"NICHT GEPRÜFT: `{args.java} -version` läuft nicht. Ohne Java kein fremdes "
              "Urteil — das ist ein eigener Zustand, kein Grün.", file=sys.stderr)
        return 2
    try:
        pruefe_jar(args.mustang)
    except Fehlt as f:
        print(f"NICHT GEPRÜFT: {f}", file=sys.stderr)
        return 2

    befunde = 0
    nicht_geprueft = 0
    fassung = ""
    erwartung = [(pdf, GUELTIG) for pdf in args.gut] + [(pdf, UNGUELTIG) for pdf in args.schlecht]

    for pdf, soll in erwartung:
        if not pdf.is_file():
            print(f"FEHL  {pdf} — Datei fehlt")
            befunde += 1
            continue
        vorher = sha256(pdf)
        ist, ausgabe = urteil(pdf, args.mustang, args.java, ausfuehren)
        fassung = fassung or (regelfassung(ausgabe) if "xslt/" in ausgabe else "")
        if ist == WERKZEUGFEHLER:
            print(f"NICHT GEPRÜFT  {pdf.name} — Mustang ist abgestürzt, kein Urteil")
            nicht_geprueft += 1
        elif ist == soll:
            art = "Gegenprobe fällt durch" if soll == UNGUELTIG else "besteht"
            print(f"OK    {pdf.name}  {art}  sha256={vorher[:16]}…")
        else:
            print(f"FEHL  {pdf.name} — erwartet {soll}, Mustang sagt {ist}")
            befunde += 1
        if sha256(pdf) != vorher:
            print(f"FEHL  {pdf.name} — Datei hat sich während der Prüfung geändert")
            befunde += 1

    if not args.gut:
        print("FEHL  keine Datei, die bestehen muss — der Lauf belegt nichts")
        befunde += 1
    if not args.schlecht:
        print("FEHL  keine Gegenprobe — ohne eine Datei, die durchfallen muss, belegt ein "
              "grüner Lauf nur, dass Mustang gestartet ist")
        befunde += 1

    print()
    print(f"Regelfassung: {fassung or 'nicht ermittelt — keine Schematron-Angabe in der Ausgabe'}")
    if nicht_geprueft:
        print(f"{nicht_geprueft} Datei(en) NICHT GEPRÜFT — kein Grün")
        return 2
    if befunde:
        print(f"{befunde} Befund(e)")
        return 1
    print(f"{len(erwartung)} Datei(en), alle wie erwartet — bestätigt von Mustang, "
          "nicht von uns selbst")
    return 0


if __name__ == "__main__":
    sys.exit(main())
