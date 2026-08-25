#!/usr/bin/env python3
"""normbrief — Geschäftsbriefe nach DIN 5008 aus Markdown.

  normbrief.py render   BRIEF.md [-o AUS.pdf] [--png] [--no-pdfa] [--profiles DIR]
  normbrief.py check    AUS.pdf --form B [--json]
  normbrief.py preview  BRIEF.md [-o AUS.png] [--ppi 120]
  normbrief.py profiles
  normbrief.py init     ZIEL.md --profil NAME [--empfaenger "..."] [--betreff "..."]

Exit-Codes: 0 ok · 1 Eingabefehler · 2 Geometrie-Check gescheitert · 3 Umgebung
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from markdown_typst import MarkdownFehler, konvertiere  # noqa: E402

SKILL = Path(__file__).resolve().parent.parent
TYPST_DIR = SKILL / "typst"
FONT_DIR = SKILL / "assets" / "fonts"

EXIT_OK, EXIT_EINGABE, EXIT_GEOMETRIE, EXIT_UMGEBUNG = 0, 1, 2, 3

MONATE = [
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
]

# Leitwörter des Informationsblocks in der Reihenfolge der Norm.
INFOBLOCK_REIHENFOLGE = [
    ("ihr_zeichen", "Ihr Zeichen"),
    ("ihre_nachricht_vom", "Ihre Nachricht vom"),
    ("unser_zeichen", "Unser Zeichen"),
    ("unsere_nachricht_vom", "Unsere Nachricht vom"),
    ("ansprechpartner", "Name"),
    ("telefon", "Telefon"),
    ("fax", "Fax"),
    ("email", "E-Mail"),
]

PFLICHTFELDER = ("profil", "empfaenger", "datum", "betreff")


class Eingabefehler(ValueError):
    pass


class Umgebungsfehler(RuntimeError):
    pass


# ── Frontmatter ─────────────────────────────────────────────────────────────

def lies_brief(pfad: Path) -> tuple[dict, str, int]:
    """Liefert (Frontmatter, Markdown-Body, Zeilenversatz)."""
    import yaml

    if not pfad.is_file():
        raise Eingabefehler(f"Datei nicht gefunden: {pfad}")
    text = pfad.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise Eingabefehler(
            f"{pfad.name}: Die Datei muss mit einem YAML-Frontmatter beginnen "
            "(eine Zeile '---' als erste Zeile)."
        )
    teile = text.split("\n---", 2)
    if len(teile) < 2:
        raise Eingabefehler(f"{pfad.name}: Das Frontmatter wird nicht durch '---' abgeschlossen.")
    kopf_roh = teile[0][3:]
    body = teile[1].lstrip("\n")
    if body.startswith("-\n"):
        body = body[2:]
    versatz = kopf_roh.count("\n") + 2
    try:
        kopf = yaml.safe_load(kopf_roh) or {}
    except yaml.YAMLError as fehler:
        raise Eingabefehler(f"{pfad.name}: Frontmatter ist kein gültiges YAML — {fehler}") from None
    if not isinstance(kopf, dict):
        raise Eingabefehler(f"{pfad.name}: Frontmatter muss ein Feld-Wert-Block sein.")
    return kopf, body, versatz


def als_liste(wert) -> list[str]:
    if wert is None:
        return []
    if isinstance(wert, str):
        return [wert]
    return [str(z) for z in wert]


def formatiere_datum(wert, format_name: str) -> str:
    if isinstance(wert, dt.datetime):
        wert = wert.date()
    if isinstance(wert, str):
        try:
            wert = dt.date.fromisoformat(wert.strip())
        except ValueError:
            return wert.strip()          # bereits ausformuliert, unverändert übernehmen
    if not isinstance(wert, dt.date):
        raise Eingabefehler(f"datum: '{wert}' ist kein Datum im Format JJJJ-MM-TT.")
    if format_name == "iso":
        return wert.isoformat()
    return f"{wert.day}. {MONATE[wert.month - 1]} {wert.year}"


# ── Profile ─────────────────────────────────────────────────────────────────

def profil_verzeichnisse(zusatz: Path | None = None) -> list[Path]:
    pfade = []
    if zusatz:
        pfade.append(Path(zusatz).expanduser().resolve())
    aus_umgebung = os.environ.get("NORMBRIEF_PROFILES")
    if aus_umgebung:
        pfade.extend(Path(p).expanduser().resolve() for p in aus_umgebung.split(os.pathsep) if p)
    pfade.append(TYPST_DIR / "profiles.local")
    pfade.append(TYPST_DIR / "profiles")
    return [p for p in pfade if p.is_dir()]


def finde_profile(zusatz: Path | None = None) -> dict[str, Path]:
    """Profilname -> Pfad. Frühere Verzeichnisse haben Vorrang."""
    gefunden: dict[str, Path] = {}
    for verzeichnis in profil_verzeichnisse(zusatz):
        for datei in sorted(verzeichnis.glob("*.yaml")) + sorted(verzeichnis.glob("*.yml")):
            gefunden.setdefault(datei.stem, datei)
    return gefunden


def lade_profil(name: str, zusatz: Path | None = None) -> tuple[dict, Path]:
    import yaml

    profile = finde_profile(zusatz)
    if name not in profile:
        bekannt = ", ".join(sorted(profile)) or "keine"
        raise Eingabefehler(
            f"Profil '{name}' nicht gefunden. Vorhanden: {bekannt}.\n"
            f"Gesucht in: {', '.join(str(p) for p in profil_verzeichnisse(zusatz))}"
        )
    pfad = profile[name]
    profil = yaml.safe_load(pfad.read_text(encoding="utf-8")) or {}
    for feld in ("absender", "ruecksendeangabe"):
        if feld not in profil:
            raise Eingabefehler(f"Profil {pfad.name}: Pflichtfeld '{feld}' fehlt.")
    return profil, pfad


# ── Daten für den Typst-Wrapper ─────────────────────────────────────────────

def baue_daten(kopf: dict, profil: dict, profil_pfad: Path, arbeitsverzeichnis: Path) -> dict:
    fehlend = [f for f in PFLICHTFELDER if not kopf.get(f)]
    if fehlend:
        raise Eingabefehler(f"Pflichtfelder fehlen: {', '.join(fehlend)}")

    empfaenger = als_liste(kopf["empfaenger"])
    if not 1 <= len(empfaenger) <= 6:
        raise Eingabefehler(
            f"empfaenger: {len(empfaenger)} Zeilen. Das Anschriftfeld fasst 1 bis 6 Zeilen "
            "und darf keine Leerzeile enthalten."
        )
    if any(not z.strip() for z in empfaenger):
        raise Eingabefehler("empfaenger: Leerzeilen sind im Anschriftfeld nicht zulässig.")

    vermerke = als_liste(kopf.get("vermerke"))
    if len(vermerke) > 3:
        raise Eingabefehler(f"vermerke: {len(vermerke)} Zeilen, die Zusatz- und Vermerkzone fasst 3.")

    form = str(kopf.get("form", profil.get("form", "B"))).upper()
    if form not in ("A", "B"):
        raise Eingabefehler(f"form: '{form}' ist unbekannt, zulässig sind A und B.")

    norm = str(kopf.get("norm", "din5008")).lower()
    if norm != "din5008":
        raise Eingabefehler(
            f"norm: '{norm}' wird noch nicht unterstützt. Diese Fassung kennt nur din5008."
        )

    betreff = str(kopf["betreff"]).strip()
    if len(betreff) > 160:
        raise Eingabefehler(f"betreff: {len(betreff)} Zeichen — die Norm lässt höchstens 2 Zeilen zu.")

    datum = formatiere_datum(kopf["datum"], profil.get("datumsformat", "lang"))

    defaults = profil.get("infoblock_defaults") or {}
    info_roh = {**defaults, **(kopf.get("infoblock") or {})}
    infoblock = []
    for schluessel, leitwort in INFOBLOCK_REIHENFOLGE:
        wert = info_roh.get(schluessel)
        if wert in (None, ""):
            continue
        if schluessel.endswith("_vom"):
            wert = formatiere_datum(wert, profil.get("datumsformat", "lang"))
        infoblock.append([leitwort, str(wert)])
    infoblock.append(["Datum", datum])

    anrede = str(kopf.get("anrede") or "Sehr geehrte Damen und Herren,").strip()
    if not anrede.endswith(","):
        raise Eingabefehler(f"anrede: '{anrede}' — die Anrede endet nach DIN mit einem Komma.")

    gruss = str(kopf.get("gruss") or profil.get("gruss") or "Mit freundlichen Grüßen").strip()
    if gruss.endswith(","):
        raise Eingabefehler(f"gruss: '{gruss}' — die Grußformel steht ohne Komma.")

    unterzeichner = str(
        kopf.get("unterzeichner") or profil.get("unterzeichner") or profil["absender"]["name"]
    ).strip()

    signatur = None
    if profil.get("signatur"):
        quelle = (profil_pfad.parent / profil["signatur"]).resolve()
        if not quelle.is_file():
            raise Eingabefehler(f"Profil: Signaturbild nicht gefunden: {quelle}")
        ziel = arbeitsverzeichnis / "assets" / quelle.name
        ziel.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(quelle, ziel)
        signatur = f"assets/{quelle.name}"

    return {
        "form": form,
        "empfaenger": empfaenger,
        "vermerke": vermerke,
        "datum": datum,
        "betreff": betreff,
        "betreff_kurz": str(kopf.get("betreff_kurz") or betreff),
        "infoblock": infoblock,
        "anrede": anrede,
        "gruss": gruss,
        "unterzeichner": unterzeichner,
        "anlagen": als_liste(kopf.get("anlagen")),
        "verteiler": als_liste(kopf.get("verteiler")),
        "signatur": signatur,
    }


def baue_profil_daten(profil: dict, profil_pfad: Path, arbeitsverzeichnis: Path) -> dict:
    """Kopiert Profil-Assets ins Arbeitsverzeichnis und macht Pfade relativ."""
    daten = json.loads(json.dumps(profil, default=str))
    briefkopf = daten.get("briefkopf") or {}
    logo = briefkopf.get("logo")
    if logo:
        quelle = (profil_pfad.parent / logo).resolve()
        if not quelle.is_file():
            raise Eingabefehler(f"Profil {profil_pfad.name}: Logo nicht gefunden: {quelle}")
        ziel = arbeitsverzeichnis / "assets" / quelle.name
        ziel.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(quelle, ziel)
        briefkopf["logo"] = f"assets/{quelle.name}"
        daten["briefkopf"] = briefkopf
    daten.setdefault("absender", {})

    # Der untere Rand muss die Fusszeile fassen: letter-pro verankert sie an der
    # Unterkante des Textbereichs und laesst sie nach unten wachsen. Gemessen
    # (Fusszeile 7,5 pt): der Footer-Bereich braucht 16,8 mm Grundbedarf
    # (Seitenzahlzeile, Innenabstaende, Trennlinie) plus 3,4 mm je Textzeile.
    # Darunter bleiben so rund 12 mm Rand bis zur Blattkante.
    if "rand_unten_mm" not in daten:
        spalten = daten.get("fusszeile") or []
        zeilen = max((len(s) for s in spalten), default=0)
        daten["rand_unten_mm"] = 20 if zeilen == 0 else round(28.8 + zeilen * 3.4)
    return daten


# ── Rendern ─────────────────────────────────────────────────────────────────

def _typst_modul():
    try:
        import typst
    except ImportError:
        raise Umgebungsfehler(
            "Das Python-Paket 'typst' fehlt.\n"
            "  python3 scripts/bootstrap.py   installiert alle Abhängigkeiten."
        ) from None
    return typst


def baue_arbeitsverzeichnis(ziel: Path) -> None:
    """Typst darf nur innerhalb seiner Wurzel lesen — deshalb ein eigener Baum."""
    (ziel / "vendor").mkdir(parents=True, exist_ok=True)
    shutil.copy2(TYPST_DIR / "normbrief.typ", ziel / "normbrief.typ")
    shutil.copy2(
        TYPST_DIR / "vendor" / "letter-pro-v3.0.0.typ", ziel / "vendor" / "letter-pro-v3.0.0.typ"
    )


def rendere(
    brief_pfad: Path,
    ausgabe: Path | None = None,
    *,
    profil_verzeichnis: Path | None = None,
    pdfa: bool = True,
    format_name: str = "pdf",
    ppi: int = 120,
) -> tuple[Path, str]:
    typst = _typst_modul()
    kopf, body_md, versatz = lies_brief(brief_pfad)
    profil, profil_pfad = lade_profil(str(kopf.get("profil", "")), profil_verzeichnis)

    with tempfile.TemporaryDirectory(prefix="normbrief-") as tmp:
        arbeit = Path(tmp)
        baue_arbeitsverzeichnis(arbeit)
        daten = baue_daten(kopf, profil, profil_pfad, arbeit)
        profil_daten = baue_profil_daten(profil, profil_pfad, arbeit)

        try:
            body_typst = konvertiere(body_md, versatz)
        except MarkdownFehler as fehler:
            raise Eingabefehler(f"{brief_pfad.name}, {fehler}") from None
        if not body_typst.strip():
            raise Eingabefehler(f"{brief_pfad.name}: Der Brief hat keinen Text.")

        haupt = arbeit / "main.typ"
        haupt.write_text(
            '#import "normbrief.typ": brief\n'
            "#let profil = json(bytes(sys.inputs.profil))\n"
            "#let daten = json(bytes(sys.inputs.daten))\n"
            "#show: brief.with(profil: profil, daten: daten)\n\n"
            + body_typst,
            encoding="utf-8",
        )

        if ausgabe is None:
            endung = ".png" if format_name == "png" else ".pdf"
            ausgabe = brief_pfad.with_suffix(endung)
        ausgabe = Path(ausgabe)
        ausgabe.parent.mkdir(parents=True, exist_ok=True)

        argumente = {
            "input": str(haupt),
            "output": str(ausgabe),
            "root": str(arbeit),
            "sys_inputs": {
                "profil": json.dumps(profil_daten, ensure_ascii=False),
                "daten": json.dumps(daten, ensure_ascii=False),
            },
        }
        if FONT_DIR.is_dir():
            argumente["font_paths"] = [str(FONT_DIR)]
        if format_name == "png":
            argumente["format"] = "png"
            argumente["ppi"] = ppi
        elif pdfa:
            argumente["pdf_standards"] = "a-2b"

        try:
            typst.compile(**argumente)
        except Exception as fehler:                       # noqa: BLE001
            meldung = str(fehler)
            if "unknown" in meldung and "pdf_standards" in meldung:
                argumente.pop("pdf_standards", None)
                typst.compile(**argumente)
                return ausgabe, daten["form"]
            raise Eingabefehler(f"Typst konnte den Brief nicht setzen:\n{meldung}") from None

    return ausgabe, daten["form"]


# ── Unterbefehle ────────────────────────────────────────────────────────────

def befehl_render(args) -> int:
    import geometrie

    pdf, form = rendere(
        Path(args.brief),
        Path(args.output) if args.output else None,
        profil_verzeichnis=Path(args.profiles) if args.profiles else None,
        pdfa=not args.no_pdfa,
    )
    print(f"OK  PDF geschrieben: {pdf}")

    if args.png:
        png, _ = rendere(
            Path(args.brief),
            pdf.with_suffix(".png"),
            profil_verzeichnis=Path(args.profiles) if args.profiles else None,
            format_name="png",
            ppi=args.ppi,
        )
        print(f"OK  Vorschau: {png}")

    bericht = geometrie.pruefe(pdf, form)
    if not args.no_pdfa:
        ist_pdfa, _ = geometrie.pdfa_geprueft(pdf)
        bericht.wahr("PDF/A-2b", ist_pdfa, "pdfaid part 2, conformance B",
                     "vorhanden" if ist_pdfa else "fehlt")
    print(bericht.als_text())
    if not bericht.ok:
        print("\nFEHLGESCHLAGEN — das PDF hält die Maße aus DIN 5008 nicht ein.", file=sys.stderr)
        return EXIT_GEOMETRIE
    return EXIT_OK


def befehl_check(args) -> int:
    import geometrie

    pdf = Path(args.pdf)
    if not pdf.is_file():
        print(f"Datei nicht gefunden: {pdf}", file=sys.stderr)
        return EXIT_EINGABE
    bericht = geometrie.pruefe(pdf, args.form.upper())
    if args.json:
        print(json.dumps(bericht.als_dict(), ensure_ascii=False, indent=2))
    else:
        print(bericht.als_text())
    return EXIT_OK if bericht.ok else EXIT_GEOMETRIE


def befehl_preview(args) -> int:
    png, _ = rendere(
        Path(args.brief),
        Path(args.output) if args.output else None,
        profil_verzeichnis=Path(args.profiles) if args.profiles else None,
        format_name="png",
        ppi=args.ppi,
    )
    print(f"OK  Vorschau: {png}")
    return EXIT_OK


def befehl_profiles(args) -> int:
    profile = finde_profile(Path(args.profiles) if args.profiles else None)
    if not profile:
        print("Keine Profile gefunden.")
        print("Gesucht in: " + ", ".join(str(p) for p in profil_verzeichnisse()))
        return EXIT_EINGABE
    for name, pfad in sorted(profile.items()):
        print(f"{name:20s} {pfad}")
    return EXIT_OK


VORLAGE = """---
profil: {profil}
form: {form}
empfaenger:
{empfaenger}
datum: {datum}
betreff: {betreff}
anrede: Sehr geehrte Damen und Herren,
---
"""


def befehl_init(args) -> int:
    ziel = Path(args.ziel)
    if ziel.exists():
        print(f"{ziel} gibt es schon — nichts überschrieben.", file=sys.stderr)
        return EXIT_EINGABE
    zeilen = args.empfaenger.split("|") if args.empfaenger else ["Muster GmbH", "Musterstraße 1", "12345 Musterstadt"]
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(
        VORLAGE.format(
            profil=args.profil,
            form=args.form,
            empfaenger="\n".join(f"  - {z.strip()}" for z in zeilen),
            datum=dt.date.today().isoformat(),
            betreff=args.betreff or "Betreff hier eintragen",
        )
        + "\nden Brieftext hier schreiben.\n",
        encoding="utf-8",
    )
    print(f"OK  Vorlage geschrieben: {ziel}")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="normbrief", description="Geschäftsbriefe nach DIN 5008 aus Markdown."
    )
    unter = parser.add_subparsers(dest="befehl", required=True)

    p = unter.add_parser("render", help="Brief nach PDF setzen und nachmessen")
    p.add_argument("brief")
    p.add_argument("-o", "--output")
    p.add_argument("--png", action="store_true", help="zusätzlich eine PNG-Vorschau")
    p.add_argument("--no-pdfa", action="store_true", help="ohne PDF/A-2b")
    p.add_argument("--profiles", help="zusätzliches Profilverzeichnis")
    p.add_argument("--ppi", type=int, default=120)
    p.set_defaults(funktion=befehl_render)

    p = unter.add_parser("check", help="ein PDF gegen die Normmaße vermessen")
    p.add_argument("pdf")
    p.add_argument("--form", default="B", choices=["A", "B", "a", "b"])
    p.add_argument("--json", action="store_true")
    p.set_defaults(funktion=befehl_check)

    p = unter.add_parser("preview", help="PNG der ersten Seite")
    p.add_argument("brief")
    p.add_argument("-o", "--output")
    p.add_argument("--ppi", type=int, default=120)
    p.add_argument("--profiles")
    p.set_defaults(funktion=befehl_preview)

    p = unter.add_parser("profiles", help="verfügbare Absenderprofile auflisten")
    p.add_argument("--profiles", dest="profiles")
    p.set_defaults(funktion=befehl_profiles)

    p = unter.add_parser("init", help="Frontmatter-Vorlage schreiben")
    p.add_argument("ziel")
    p.add_argument("--profil", required=True)
    p.add_argument("--form", default="B", choices=["A", "B"])
    p.add_argument("--empfaenger", help="Zeilen mit | getrennt")
    p.add_argument("--betreff")
    p.set_defaults(funktion=befehl_init)

    args = parser.parse_args(argv)
    try:
        return args.funktion(args)
    except Eingabefehler as fehler:
        print(f"FEHLER  {fehler}", file=sys.stderr)
        return EXIT_EINGABE
    except Umgebungsfehler as fehler:
        print(f"FEHLER  {fehler}", file=sys.stderr)
        return EXIT_UMGEBUNG


if __name__ == "__main__":
    sys.exit(main())
