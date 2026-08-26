#!/usr/bin/env python3
"""Prüft PDF-Konformität mit veraPDF — einem fremden Werkzeug (Issue #34).

WARUM ES DIESES SKRIPT GIBT

falzmarke schreibt PDF/A und misst das Ergebnis anschließend selbst nach. Das
belegt, dass das Werkzeug einhält, was es sich vornimmt — nicht, dass das
Ergebnis der Norm entspricht. Beides wird von derselben Codebasis erzeugt und
geprüft; in der Quellenlage trägt `eigene_messung` deshalb die Zählstufe `nie`.

veraPDF ist die Referenzimplementierung der PDF Association. Es hat den Brief
nicht geschrieben und teilt keine Zeile Code mit dem Renderer. Erst damit steht
hinter der Konformitätsaussage ein unabhängiger Beleg.

WAS GEPRÜFT WIRD — UND WARUM NICHT EIN FESTER WERT

Geprüft wird, was die Datei **selbst deklariert**, nicht eine im Skript
hinterlegte Stufe. Ein PDF, das `pdfaid:part=2, conformance=B` in seine
XMP-Metadaten schreibt, behauptet PDF/A-2b — genau diese Behauptung wird gegen
veraPDF gehalten. Steht zusätzlich `pdfuaid:part=1` drin, wird auch PDF/UA-1
geprüft.

Das hat zwei Gründe. Erstens ist es die Aussage, die im Umlauf ist: Wer das PDF
öffnet, liest die Deklaration, nicht dieses Skript. Zweitens überlebt die
Prüfung eine Umstellung — zöge das Projekt eines Tages auf A-3b um, prüft dieses
Skript ohne Änderung mit.

Eine Datei ganz **ohne** Deklaration ist ein Fehler, kein stiller Durchlauf:
sonst wäre der grüne Lauf genau dann am grünsten, wenn gar nichts behauptet wird.
`--ohne-deklaration erlaubt` hebt das für Fälle auf, in denen bewusst ohne
PDF/A gerendert wurde (`render --no-pdfa`).

DIE PRÜFSUMME

Vor und nach dem Lauf wird SHA-256 gebildet und verglichen. Das belegt, dass
geprüft wurde, was auch ausgeliefert wird — und nicht ein Zwischenstand, der
danach noch Metadaten bekommt. Die Summe steht im Bericht, damit sie gegen das
CI-Artefakt gehalten werden kann.

DIE GEGENPROBE

`--gegenprobe` erzeugt aus derselben Quelle ein PDF **ohne** PDF/A und verlangt,
dass veraPDF es ablehnt. Ohne sie belegt ein grüner Lauf nur, dass veraPDF
gestartet ist. Schlägt die Gegenprobe fehl — läuft das kaputte PDF also durch —
endet das Skript mit Fehler, auch wenn alle echten Prüfungen bestanden haben.

Usage:
  scripts/pdf_konformitaet.py bau/*.pdf
  scripts/pdf_konformitaet.py bau/*.pdf --gegenprobe examples/brief-form-b.md
  scripts/pdf_konformitaet.py brief.pdf --ohne-deklaration erlaubt
"""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "skill"))

from falzmarke import geometrie  # noqa: E402


class Fehlt(Exception):
    """veraPDF ist nicht installiert. Das ist NICHT GEPRÜFT, nicht grün."""


def verapdf_pfad() -> str:
    pfad = shutil.which("verapdf")
    if not pfad:
        raise Fehlt(
            "veraPDF nicht gefunden. Ohne das fremde Werkzeug ist die Konformität\n"
            "  NICHT GEPRÜFT — das ist ein eigener Zustand, kein Grün.\n"
            "  macOS:  brew install verapdf\n"
            "  Linux:  https://software.verapdf.org/releases/verapdf-installer.zip"
        )
    return pfad


def sha256(pfad: Path) -> str:
    h = hashlib.sha256()
    with pfad.open("rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def deklarierte_standards(pdf: Path) -> list[str]:
    """Welche Konformität behauptet die Datei über ihre XMP-Metadaten?

    Rückgabe sind veraPDF-Flavours, etwa ['2b'] oder ['2b', 'ua1'].
    """
    xmp = geometrie.xmp_lesen(pdf)
    kompakt = xmp.replace(" ", "")
    flavours: list[str] = []

    # pdfaid:part und pdfaid:conformance stehen als Element ODER als Attribut —
    # beide Schreibweisen kommen in freier Wildbahn vor.
    teil = re.search(r"pdfaid:part>(\d)", kompakt) or re.search(r'pdfaid:part="(\d)"', xmp)
    konf = re.search(r"pdfaid:conformance>([AaBbUu])", kompakt) or re.search(
        r'pdfaid:conformance="([AaBbUu])"', xmp
    )
    if teil and konf:
        flavours.append(f"{teil.group(1)}{konf.group(1).lower()}")

    ua = re.search(r"pdfuaid:part>(\d)", kompakt) or re.search(r'pdfuaid:part="(\d)"', xmp)
    if ua:
        flavours.append(f"ua{ua.group(1)}")

    return flavours


def verapdf_urteil(pdf: Path, flavour: str) -> tuple[bool, str]:
    """Ruft veraPDF und gibt (bestanden, erste Zeile) zurück.

    Der Exit-Code ist die Quelle der Wahrheit, nicht der Text: 0 = PASS,
    1 = FAIL. Gemessen an veraPDF 1.30.2 mit vier Fällen (A-2b und UA-1, je
    einmal haltend und einmal brechend). Die Textausgabe wird nur für die
    Meldung gelesen — wer sie auswertet, statt den Exit-Code zu nehmen, baut
    sich einen Check, der bei jeder Formatänderung still grün wird.
    """
    lauf = subprocess.run(
        [verapdf_pfad(), "--flavour", flavour, "--format", "text", str(pdf)],
        capture_output=True,
        text=True,
    )
    erste = (lauf.stdout or lauf.stderr or "").strip().splitlines()
    return lauf.returncode == 0, (erste[0] if erste else "(keine Ausgabe)")


def gegenprobe(quelle: Path) -> tuple[bool, str]:
    """Rendert bewusst ohne PDF/A und verlangt, dass veraPDF das ablehnt.

    Der Sinn steht im Modulkopf: ein Prüfmittel, das nie rot werden kann, ist
    kein Nachweis. Diese Funktion ist der Beleg, dass der Lauf oben trennt.
    """
    with tempfile.TemporaryDirectory() as tmp:
        ziel = Path(tmp) / "ohne-pdfa.pdf"
        lauf = subprocess.run(
            [
                sys.executable,
                str(REPO / "skill" / "scripts" / "falzmarke.py"),
                "render",
                str(quelle),
                "-o",
                str(ziel),
                "--no-pdfa",
            ],
            capture_output=True,
            text=True,
        )
        if lauf.returncode != 0 or not ziel.exists():
            return False, f"Gegenprobe-PDF liess sich nicht erzeugen: {lauf.stderr[:200]}"

        # Zweite Absicherung: die Datei darf gar keine PDF/A-Deklaration tragen.
        # Täte sie es, prüfte die Gegenprobe etwas anderes als gedacht.
        if deklarierte_standards(ziel):
            return False, "Gegenprobe-PDF trägt wider Erwarten eine Deklaration — sie prüft nichts"

        bestanden, meldung = verapdf_urteil(ziel, "2b")
        if bestanden:
            return False, f"veraPDF liess ein PDF ohne PDF/A durchgehen: {meldung}"
        return True, meldung


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("pdfs", nargs="+", type=Path, help="zu prüfende PDF-Dateien")
    p.add_argument(
        "--gegenprobe",
        type=Path,
        metavar="BRIEF.md",
        help="Quelle, aus der ein bewusst nicht-konformes PDF erzeugt wird",
    )
    p.add_argument(
        "--ohne-deklaration",
        choices=["fehler", "erlaubt"],
        default="fehler",
        help="wie mit PDFs ohne Konformitäts-Deklaration umgegangen wird (Vorgabe: fehler)",
    )
    args = p.parse_args()

    try:
        verapdf_pfad()
    except Fehlt as f:
        print(f"NICHT GEPRÜFT: {f}", file=sys.stderr)
        return 2  # eigener Zustand — weder grün noch ein Befund gegen die PDFs

    fehler = 0
    geprueft = 0

    for pdf in args.pdfs:
        if not pdf.exists():
            print(f"FEHL  {pdf} — Datei fehlt")
            fehler += 1
            continue

        vorher = sha256(pdf)
        flavours = deklarierte_standards(pdf)

        if not flavours:
            if args.ohne_deklaration == "erlaubt":
                print(f"übergangen  {pdf.name} — keine Konformitäts-Deklaration")
                continue
            print(f"FEHL  {pdf.name} — keine Konformitäts-Deklaration in den XMP-Metadaten")
            fehler += 1
            continue

        for flavour in flavours:
            bestanden, meldung = verapdf_urteil(pdf, flavour)
            geprueft += 1
            if bestanden:
                print(f"OK    {pdf.name}  {flavour}  sha256={vorher[:16]}…")
            else:
                print(f"FEHL  {pdf.name}  {flavour}  {meldung}")
                fehler += 1

        nachher = sha256(pdf)
        if vorher != nachher:
            # Wäre die Datei zwischendurch verändert worden, bezöge sich das
            # Urteil oben auf etwas anderes als das, was ausgeliefert wird.
            print(f"FEHL  {pdf.name} — Datei hat sich während der Prüfung geändert")
            fehler += 1

    if args.gegenprobe:
        ok, meldung = gegenprobe(args.gegenprobe)
        if ok:
            print(f"OK    Gegenprobe — ein PDF ohne PDF/A fällt durch ({meldung.split()[0]})")
        else:
            print(f"FEHL  Gegenprobe — {meldung}")
            fehler += 1

    print()
    if geprueft == 0 and not fehler:
        # Leere Menge gegen leere Menge belegt nichts.
        print("FEHL  0 Konformitätsprüfungen gelaufen — der Lauf belegt nichts")
        return 1
    if fehler:
        print(f"{fehler} Befund(e) bei {geprueft} Prüfung(en)")
        return 1
    print(f"{geprueft} Prüfung(en), alle bestanden — bestätigt von veraPDF, nicht von uns selbst")
    return 0


if __name__ == "__main__":
    sys.exit(main())
