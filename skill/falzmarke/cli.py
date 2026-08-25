#!/usr/bin/env python3
"""falzmarke — Geschäftsbriefe nach DIN 5008 aus Markdown.

  falzmarke.py render   BRIEF.md [-o AUS.pdf] [--png] [--no-pdfa] [--profiles DIR]
  falzmarke.py check    AUS.pdf --form B [--json]
  falzmarke.py preview  BRIEF.md [-o AUS.png] [--ppi 120]
  falzmarke.py profiles
  falzmarke.py init     ZIEL.md --profil NAME [--empfaenger "..."] [--betreff "..."]

Exit-Codes: 0 ok · 1 Eingabefehler · 2 Geometrie-Check gescheitert · 3 Umgebung
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

from falzmarke import __version__ as VERSION_PAKET
from falzmarke import lint as lint_modul
from falzmarke.markdown import MarkdownFehler, konvertiere

PAKET = Path(__file__).resolve().parent
SKILL = PAKET.parent
TYPST_DIR = PAKET / "typst"
FONT_DIR = PAKET / "assets" / "fonts"

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

# Zeichen, die bei 10 pt in die Wertespalte des Informationsblocks passen
# (43 mm Spaltenbreite, gemessen rund 1,24 mm je Zeichen).
INFOBLOCK_WERT_MAX = 32


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
    except ValueError as fehler:
        # PyYAML erkennt `2026-13-45` am Muster als Zeitstempel und scheitert
        # beim Bauen des Datums — mit ValueError, nicht mit YAMLError. Ohne
        # diesen Zweig endet der Lauf in einem Traceback.
        raise Eingabefehler(
            f"{pfad.name}: Frontmatter enthält einen unmöglichen Wert — {fehler}\n"
            "        Bei einem Datum: als ISO-Datum schreiben, z. B. 2026-08-25."
        ) from None
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

def benutzer_profilverzeichnis() -> Path:
    """Der Ort, an dem eigene Profile ein Update überstehen.

    Alles unterhalb der Installation ist dafür ungeeignet: Wer den Skill
    aktualisiert — Zip neu hochladen, Verzeichnis ersetzen, `pip install -U` —
    verliert dort seine Profile, und mit ihnen die Möglichkeit, alte Briefe
    erneut zu setzen.
    """
    basis = os.environ.get("XDG_CONFIG_HOME")
    wurzel = Path(basis).expanduser() if basis else Path.home() / ".config"
    return wurzel / "falzmarke" / "profiles"


def profil_verzeichnisse(zusatz: Path | None = None,
                         brief_pfad: Path | None = None) -> list[Path]:
    """Suchorte in absteigendem Vorrang.

    1. --profiles                       ausdrücklich genannt
    2. FALZMARKE_PROFILES               Umgebung, mehrere Pfade erlaubt
    3. neben dem Brief und dessen profiles/
    4. /mnt/user-data/uploads           was auf claude.ai hochgeladen wurde
    5. ./profiles/                      zum Vorgang gehörend
    6. ~/.config/falzmarke/profiles/    die eigenen Absender, updatefest
    7. profiles.local/                  alter Ort, nur noch als Übergang
    8. mitgelieferte Beispiele
    """
    pfade = []
    if zusatz:
        pfade.append(Path(zusatz).expanduser().resolve())
    aus_umgebung = os.environ.get("FALZMARKE_PROFILES")
    if aus_umgebung:
        pfade.extend(Path(p).expanduser().resolve() for p in aus_umgebung.split(os.pathsep) if p)
    if brief_pfad is not None:
        # Neben dem Brief: so lassen sich Brief und Profil zusammen weitergeben
        pfade.append(Path(brief_pfad).expanduser().resolve().parent)
        pfade.append(Path(brief_pfad).expanduser().resolve().parent / "profiles")
    # Auf claude.ai landen hochgeladene Dateien hier.
    pfade.append(Path("/mnt/user-data/uploads"))
    pfade.append(Path.cwd() / "profiles")
    pfade.append(benutzer_profilverzeichnis())
    pfade.append(TYPST_DIR / "profiles.local")
    pfade.append(TYPST_DIR / "profiles")

    gesehen, eindeutig = set(), []
    for pfad in pfade:
        aufgeloest = pfad.expanduser()
        if aufgeloest.is_dir() and aufgeloest not in gesehen:
            gesehen.add(aufgeloest)
            eindeutig.append(aufgeloest)
    return eindeutig


def finde_profile(zusatz: Path | None = None,
                  brief_pfad: Path | None = None) -> dict[str, Path]:
    """Profilname -> Pfad. Frühere Verzeichnisse haben Vorrang."""
    gefunden: dict[str, Path] = {}
    for verzeichnis in profil_verzeichnisse(zusatz, brief_pfad):
        for datei in sorted(verzeichnis.glob("*.yaml")) + sorted(verzeichnis.glob("*.yml")):
            gefunden.setdefault(datei.stem, datei)
    return gefunden


def lade_profil(
    name, zusatz: Path | None = None, brief_pfad: Path | None = None
) -> tuple[dict, Path]:
    """Profil aus einem Namen, einem Pfad oder direkt aus dem Frontmatter.

    Der eingebettete Fall ist für claude.ai gedacht: dort überlebt kein
    Verzeichnis den nächsten Chat, ein Brief mit allem Nötigen darin schon.
    """
    import yaml

    if isinstance(name, dict):
        # Vollständig im Brief. Als Bezugspunkt für Logopfade dient der Brief.
        basis = Path(brief_pfad).parent if brief_pfad else Path.cwd()
        return name, basis / "<frontmatter>"

    name = str(name)
    if name.endswith((".yaml", ".yml")) or "/" in name:
        pfad = Path(name).expanduser()
        if not pfad.is_absolute() and brief_pfad is not None:
            pfad = (Path(brief_pfad).parent / pfad).resolve()
        if not pfad.is_file():
            raise Eingabefehler(f"Profil nicht gefunden: {pfad}")
        return yaml.safe_load(pfad.read_text(encoding="utf-8")) or {}, pfad

    profile = finde_profile(zusatz, brief_pfad)
    if name not in profile:
        bekannt = ", ".join(sorted(profile)) or "keine"
        raise Eingabefehler(
            f"Profil '{name}' nicht gefunden. Vorhanden: {bekannt}.\n"
            f"Gesucht in: {', '.join(str(p) for p in profil_verzeichnisse(zusatz, brief_pfad))}"
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

    # Die Zeilen des Informationsblocks stehen im 12-pt-Raster und haben feste
    # Höhe. Ein überlanger Wert würde deshalb nicht umbrechen, sondern über die
    # 75 mm hinauslaufen — sichtbar erst im fertigen PDF. Lieber hier abbrechen.
    zu_lang = [(lw, w) for lw, w in infoblock if len(w) > INFOBLOCK_WERT_MAX]
    if zu_lang:
        leitwort, wert = zu_lang[0]
        raise Eingabefehler(
            f"infoblock: '{leitwort}' ist mit {len(wert)} Zeichen zu lang "
            f"(höchstens {INFOBLOCK_WERT_MAX}, sonst passt die Zeile nicht in die 75 mm "
            "des Informationsblocks).\n"
            f"        Wert: {wert}"
        )

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


def _pruefe_textzeilen(profil: dict, profil_pfad: Path) -> None:
    """Fängt die häufigste YAML-Falle ab.

    `- Geschäftsführerin: Erika Muster` ist für YAML kein Text, sondern ein
    Mapping. Ungeprüft landet so ein Dictionary im PDF — sichtbar, aber leicht
    zu übersehen. Zeilen mit Doppelpunkt gehören in Anführungszeichen.
    """
    def melde(ort: str, wert) -> None:
        raise Eingabefehler(
            f"Profil {profil_pfad.name}: {ort} ist kein Text, sondern {type(wert).__name__} "
            f"({wert!r}).\n"
            "        Enthält die Zeile einen Doppelpunkt, gehört sie in Anführungszeichen:\n"
            '        - "Geschäftsführerin: Erika Muster"'
        )

    for nummer, spalte in enumerate(profil.get("fusszeile") or [], start=1):
        if not isinstance(spalte, list):
            melde(f"fusszeile, Spalte {nummer}", spalte)
        for zeile in spalte:
            if not isinstance(zeile, (str, int, float)):
                melde(f"fusszeile, Spalte {nummer}", zeile)
    for zeile in (profil.get("briefkopf") or {}).get("zeilen") or []:
        if not isinstance(zeile, (str, int, float)):
            melde("briefkopf.zeilen", zeile)


def baue_profil_daten(profil: dict, profil_pfad: Path, arbeitsverzeichnis: Path) -> dict:
    """Kopiert Profil-Assets ins Arbeitsverzeichnis und macht Pfade relativ."""
    _pruefe_textzeilen(profil, profil_pfad)
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
    # Aufgerundet auf 31 mm Grundbedarf, damit rund 11 mm Rand bis zur
    # Blattkante bleiben.
    if "rand_unten_mm" not in daten:
        spalten = daten.get("fusszeile") or []
        zeilen = max((len(s) for s in spalten), default=0)
        daten["rand_unten_mm"] = 20 if zeilen == 0 else round(31.0 + zeilen * 3.4)
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
    shutil.copy2(TYPST_DIR / "falzmarke.typ", ziel / "falzmarke.typ")
    shutil.copy2(
        TYPST_DIR / "vendor" / "letter-pro-v3.0.0.typ", ziel / "vendor" / "letter-pro-v3.0.0.typ"
    )


def linte(brief_pfad: Path, profil_verzeichnis: Path | None = None) -> lint_modul.Bericht:
    """Prüft die Eingabe, ohne Typst zu bemühen."""
    kopf, body_md, versatz = lies_brief(brief_pfad)
    bericht = lint_modul.Bericht()
    kopf_roh = brief_pfad.read_text(encoding="utf-8").split("\n---", 2)[0][3:]

    lint_modul.pruefe_frontmatter(kopf, kopf_roh, bericht)
    lint_modul.pruefe_body(body_md, versatz, bericht)

    try:
        konvertiere(body_md, versatz)
    except MarkdownFehler as fehler:
        bericht.fehler(fehler.zeile, "markdown", fehler.meldung)

    if kopf.get("profil"):
        try:
            lade_profil(kopf["profil"], profil_verzeichnis, brief_pfad)
        except Eingabefehler as fehler:
            bericht.fehler(1, "profil", str(fehler).splitlines()[0])
    return bericht


def rendere(
    brief_pfad: Path,
    ausgabe: Path | None = None,
    *,
    profil_verzeichnis: Path | None = None,
    pdfa: bool = True,
    pdfua: bool = False,
    format_name: str = "pdf",
    ppi: int = 120,
) -> tuple[Path, str]:
    typst = _typst_modul()
    kopf, body_md, versatz = lies_brief(brief_pfad)
    profil, profil_pfad = lade_profil(kopf.get("profil", ""), profil_verzeichnis, brief_pfad)

    with tempfile.TemporaryDirectory(prefix="falzmarke-") as tmp:
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

        # Eigener Briefkopf, falls das Profil einen mitbringt
        kopf_import, kopf_argument = "", ""
        eigener_kopf = profil.get("briefkopf_typ")
        if eigener_kopf:
            quelle = (profil_pfad.parent / eigener_kopf).resolve()
            if not quelle.is_file():
                raise Eingabefehler(
                    f"Profil {profil_pfad.name}: briefkopf_typ verweist auf "
                    f"{eigener_kopf}, die Datei gibt es dort nicht."
                )
            if profil_pfad.parent.resolve() not in quelle.parents:
                raise Eingabefehler(
                    f"Profil {profil_pfad.name}: briefkopf_typ muss im Profilordner liegen "
                    f"(angegeben: {eigener_kopf})."
                )
            shutil.copy2(quelle, arbeit / "briefkopf-eigen.typ")
            kopf_import = '#import "briefkopf-eigen.typ": briefkopf as eigener-kopf\n'
            kopf_argument = ", briefkopf-eigen: eigener-kopf"

        haupt = arbeit / "main.typ"
        haupt.write_text(
            '#import "falzmarke.typ": brief\n'
            + kopf_import
            + "#let profil = json(bytes(sys.inputs.profil))\n"
            "#let daten = json(bytes(sys.inputs.daten))\n"
            f"#show: brief.with(profil: profil, daten: daten{kopf_argument})\n\n"
            + body_typst,
            encoding="utf-8",
        )

        if ausgabe is None:
            endung = ".png" if format_name == "png" else ".pdf"
            ausgabe = brief_pfad.with_suffix(endung)
        ausgabe = Path(ausgabe)
        ausgabe.parent.mkdir(parents=True, exist_ok=True)

        # Typst schreibt PNGs seitenweise und verlangt dafuer den Platzhalter {n}
        # im Dateinamen. Ohne ihn bricht jeder mehrseitige Brief ab.
        png_ziel = ausgabe
        if format_name == "png":
            ausgabe = ausgabe.with_name(ausgabe.stem + "-{n}" + ausgabe.suffix)

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

        # Ohne diese Zeile zieht Typst Schriften vom Rechner, auf dem gerade
        # gesetzt wird. Gemessen am 25.08.2026: ein Brief mit einem Emoji
        # bettete die Apple-Systemschrift STSong ins PDF ein — das ist
        # lizenzrechtlich heikel und macht das Ergebnis vom Rechner abhängig.
        # Fehlt eine Glyphe, soll das auffallen und nicht still ersetzt werden;
        # `lint` meldet es vor dem Render.
        argumente["ignore_system_fonts"] = True
        if format_name == "png":
            argumente["format"] = "png"
            argumente["ppi"] = ppi
        elif pdfa:
            # PDF/UA-1 setzt eine getaggte Struktur voraus; Typst 0.15 erzeugt
            # sie zusammen mit A-2b.
            # typst-py nimmt eine Liste oder einen String, kein Tupel.
            argumente["pdf_standards"] = ["a-2b", "ua-1"] if pdfua else "a-2b"

        try:
            typst.compile(**argumente)
        except Exception as fehler:                       # noqa: BLE001
            meldung = str(fehler)
            if "unknown" in meldung and "pdf_standards" in meldung:
                argumente.pop("pdf_standards", None)
                typst.compile(**argumente)
                return ausgabe, daten["form"]
            treffer = re.search(
                r'the text `"(.+?)"` could not be displayed with font `"(.+?)"`', meldung
            )
            if treffer:
                zeichen, schrift = treffer.group(1), treffer.group(2)
                punkte = " ".join(f"U+{ord(z):04X}" for z in zeichen)
                raise Eingabefehler(
                    f"Das Zeichen „{zeichen}“ ({punkte}) gibt es in der Schrift "
                    f"„{schrift}“ nicht.\n"
                    "        Ein anderes Zeichen wählen oder im Profil eine Schrift "
                    "einstellen, die es enthält.\n"
                    "        Emoji sind in keiner der mitgelieferten Schriften enthalten."
                ) from None
            raise Eingabefehler(f"Typst konnte den Brief nicht setzen:\n{meldung}") from None

    if format_name == "pdf":
        # Der Herkunftsvermerk gehört hierher und nicht in den CLI-Befehl:
        # sonst trägt ihn nur, wer über die Kommandozeile rendert.
        schreibe_herkunft(ausgabe, brief_pfad, str(kopf.get("profil", "")), daten["form"])

    if format_name == "png":
        seiten = sorted(png_ziel.parent.glob(png_ziel.stem + "-*" + png_ziel.suffix))
        if len(seiten) == 1:
            seiten[0].replace(png_ziel)
            return png_ziel, daten["form"]
        return seiten[0] if seiten else png_ziel, daten["form"]

    return ausgabe, daten["form"]


# ── Unterbefehle ────────────────────────────────────────────────────────────

VERSION = VERSION_PAKET


def schreibe_herkunft(pdf: Path, quelle: Path, profil: str, form: str) -> None:
    """Vermerkt im PDF, womit es gesetzt wurde.

    Beantwortet zwei Fragen, die sonst niemand mehr beantworten kann: Mit
    welcher Fassung ist dieser Brief entstanden, und aus welcher Quelle? Der
    Hash macht den Abgleich möglich, ohne die Quelle mitzuliefern.
    """
    from pypdf import PdfReader, PdfWriter

    hash_quelle = hashlib.sha256(quelle.read_bytes()).hexdigest()
    leser = PdfReader(str(pdf))
    schreiber = PdfWriter(clone_from=leser)
    schreiber.add_metadata({
        "/Producer": f"falzmarke {VERSION}",
        "/falzmarke_Version": VERSION,
        "/falzmarke_Profil": profil,
        "/falzmarke_Form": form,
        "/falzmarke_Quelle": f"sha256:{hash_quelle}",
    })
    ziel = pdf.with_suffix(".herkunft.pdf")
    with ziel.open("wb") as datei:
        schreiber.write(datei)
    ziel.replace(pdf)


def befehl_lint(args) -> int:
    bericht = linte(
        Path(args.brief), Path(args.profiles) if args.profiles else None
    )
    if args.json:
        print(json.dumps(bericht.als_dict(), ensure_ascii=False, indent=2))
    else:
        print(bericht.als_text(Path(args.brief).name))
    return EXIT_OK if bericht.ok else EXIT_EINGABE


def befehl_render(args) -> int:
    from falzmarke import geometrie

    # Erst prüfen, dann setzen: Ein Eingabefehler soll Exit 1 ergeben und keinen
    # Render kosten — und nicht als Geometriebefund erscheinen.
    vorpruefung = linte(Path(args.brief), Path(args.profiles) if args.profiles else None)
    if not vorpruefung.ok:
        print(vorpruefung.als_text(Path(args.brief).name), file=sys.stderr)
        return EXIT_EINGABE
    for befund in vorpruefung.befunde:
        print(befund.als_zeile(Path(args.brief).name), file=sys.stderr)

    pdf, form = rendere(
        Path(args.brief),
        Path(args.output) if args.output else None,
        profil_verzeichnis=Path(args.profiles) if args.profiles else None,
        pdfa=not args.no_pdfa,
        pdfua=args.pdfua,
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
    print(bericht.als_text(ausfuehrlich=args.verbose))
    if not bericht.ok:
        print("\nFEHLGESCHLAGEN — das PDF hält die Maße aus DIN 5008 nicht ein.", file=sys.stderr)
        return EXIT_GEOMETRIE
    return EXIT_OK


def befehl_verify(args) -> int:
    from falzmarke import geometrie

    pdf = Path(args.pdf)
    if not pdf.is_file():
        print(f"Datei nicht gefunden: {pdf}", file=sys.stderr)
        return EXIT_EINGABE

    form = (args.form or "").upper()
    if not form:
        # Die Form steht im Blatt: Form A faltet bei 87 und 192 mm, Form B bei
        # 105 und 210. Wer ein fremdes PDF prüft, muss sie nicht wissen.
        form = geometrie.erkenne_form(pdf) or ""
        if not form:
            print(
                "Die Form ließ sich nicht erkennen — es sind keine Falzmarken im "
                "Heftrand.\n        Mit --form A oder --form B angeben.",
                file=sys.stderr,
            )
            return EXIT_EINGABE

    bericht = geometrie.pruefe(pdf, form)
    if args.json:
        print(json.dumps(bericht.als_dict(), ensure_ascii=False, indent=2))
    else:
        print(bericht.als_text(ausfuehrlich=args.verbose))
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


def befehl_init_profil(args) -> int:
    ziel_verzeichnis = (
        Path(args.ziel).expanduser() if args.ziel else benutzer_profilverzeichnis()
    )
    ziel = ziel_verzeichnis / f"{args.name}.yaml"
    if ziel.exists():
        print(f"{ziel} gibt es schon — nichts überschrieben.", file=sys.stderr)
        return EXIT_EINGABE

    vorlage = (TYPST_DIR / "profiles" / "example.yaml").read_text(encoding="utf-8")
    kopf = (
        f"# Absenderprofil '{args.name}'\n"
        "#\n"
        "# Dieser Ort überlebt Aktualisierungen des Skills. Profile innerhalb der\n"
        "# Installation tun das nicht.\n"
        "#\n"
        "# Die Werte unten stammen aus dem Beispiel und sind zu ersetzen.\n"
        "# Zeilen mit Doppelpunkt gehören in Anführungszeichen.\n\n"
    )
    ziel_verzeichnis.mkdir(parents=True, exist_ok=True)
    zeilen = [z for z in vorlage.splitlines() if not z.startswith("# ")]
    ziel.write_text(kopf + "\n".join(zeilen).lstrip("\n") + "\n", encoding="utf-8")
    print(f"OK  Profil angelegt: {ziel}")
    print(f"    Jetzt ausfüllen, dann: falzmarke.py render BRIEF.md  (profil: {args.name})")
    return EXIT_OK


def befehl_pack(args) -> int:
    """Ein Skill-Zip mit eingebackenen Profilen.

    Auf claude.ai überlebt kein Verzeichnis den nächsten Chat: Profile unter
    ~/.config sind dort nach dem ersten Brief weg, und das Release-Asset
    enthält nur das Beispiel. Wer den Skill dort ernsthaft nutzt, braucht ein
    Zip mit seinen eigenen Absendern darin.
    """
    import zipfile

    profile = finde_profile(Path(args.profiles) if args.profiles else None)
    gewaehlt = {}
    for name in args.profil:
        if name not in profile:
            print(f"Profil '{name}' nicht gefunden. Vorhanden: {', '.join(sorted(profile))}",
                  file=sys.stderr)
            return EXIT_EINGABE
        gewaehlt[name] = profile[name]

    ziel = Path(args.output or f"falzmarke-{'-'.join(args.profil)}.skill")
    with tempfile.TemporaryDirectory(prefix="falzmarke-pack-") as tmp:
        bau = Path(tmp) / "falzmarke"
        shutil.copytree(SKILL, bau, ignore=shutil.ignore_patterns(
            "profiles.local", "__pycache__", "*.pyc", "*.egg-info"))
        ziel_profile = bau / "falzmarke" / "typst" / "profiles"

        for name, quelle in gewaehlt.items():
            shutil.copy2(quelle, ziel_profile / f"{name}.yaml")
            import yaml

            inhalt = yaml.safe_load(quelle.read_text(encoding="utf-8")) or {}
            # Alles, worauf das Profil zeigt, muss mit — sonst fehlt im Chat
            # das Logo und der Render bricht ab.
            beilagen = [
                (inhalt.get("briefkopf") or {}).get("logo"),
                inhalt.get("signatur"),
                inhalt.get("briefkopf_typ"),
            ]
            for beilage in [b for b in beilagen if b]:
                mit = (quelle.parent / beilage).resolve()
                if mit.is_file():
                    (ziel_profile / Path(beilage).parent).mkdir(parents=True, exist_ok=True)
                    shutil.copy2(mit, ziel_profile / beilage)

        with zipfile.ZipFile(ziel, "w", zipfile.ZIP_DEFLATED) as archiv:
            for datei in sorted(bau.rglob("*")):
                if datei.is_file():
                    archiv.write(datei, datei.relative_to(bau.parent))

    groesse = ziel.stat().st_size / 1024
    print(f"OK  Skill geschrieben: {ziel} ({groesse:.0f} KB)")
    print(f"    Enthaltene Profile: {', '.join(sorted(gewaehlt))}")
    print("    ACHTUNG: Diese Datei enthält Absenderdaten — Anschrift, Bankverbindung,")
    print("             Register. Sie gehört nicht in ein öffentliches Repository.")
    return EXIT_OK


def _ausgabe_auf_utf8() -> None:
    """Damit die Ausgabe unter Windows nicht abbricht.

    Dort schreibt Python standardmäßig in cp1252. Ein `≤` oder `→` im
    Prüfbericht beendet dann jeden Aufruf mit einem UnicodeEncodeError —
    gemessen in der CI am 25.08.2026, betrifft `verify` bei jedem Lauf.
    """
    for strom in (sys.stdout, sys.stderr):
        rekonfigurieren = getattr(strom, "reconfigure", None)
        if rekonfigurieren is not None:
            try:
                rekonfigurieren(encoding="utf-8", errors="replace")
            except (ValueError, OSError):   # pragma: no cover — sehr alte Streams
                pass


def main(argv: list[str] | None = None) -> int:
    _ausgabe_auf_utf8()
    parser = argparse.ArgumentParser(
        prog="falzmarke", description="Geschäftsbriefe nach DIN 5008 aus Markdown."
    )
    parser.add_argument("--version", action="version", version=f"falzmarke {VERSION}")
    unter = parser.add_subparsers(dest="befehl", required=True)

    p = unter.add_parser("render", help="Brief nach PDF setzen und nachmessen")
    p.add_argument("brief")
    p.add_argument("-o", "--output")
    p.add_argument("--png", action="store_true", help="zusätzlich eine PNG-Vorschau")
    p.add_argument("--no-pdfa", action="store_true", help="ohne PDF/A-2b")
    p.add_argument("--pdfua", action="store_true",
                   help="zusätzlich PDF/UA-1 (barrierefrei getaggt)")
    p.add_argument("--verbose", action="store_true", help="alle Prüfungen zeigen")
    p.add_argument("--profiles", help="zusätzliches Profilverzeichnis")
    p.add_argument("--ppi", type=int, default=120)
    p.set_defaults(funktion=befehl_render)

    p = unter.add_parser("lint", help="Brief prüfen, ohne ihn zu setzen")
    p.add_argument("brief")
    p.add_argument("--json", action="store_true")
    p.add_argument("--profiles")
    p.set_defaults(funktion=befehl_lint)

    for name, hilfe in (
        ("verify", "ein PDF gegen die Normmaße vermessen"),
        ("check", "frühere Schreibweise von verify"),
    ):
        p = unter.add_parser(name, help=hilfe)
        p.add_argument("pdf")
        p.add_argument("--form", choices=["A", "B", "a", "b"],
                       help="ohne Angabe aus den Falzmarken erkannt")
        p.add_argument("--json", action="store_true")
        p.add_argument("--verbose", action="store_true", help="alle Prüfungen zeigen")
        p.set_defaults(funktion=befehl_verify)

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

    p = unter.add_parser("pack", help="Skill-Zip mit eigenen Profilen für claude.ai")
    p.add_argument("--profil", action="append", required=True,
                   help="Profilname; mehrfach angebbar")
    p.add_argument("-o", "--output")
    p.add_argument("--profiles", dest="profiles")
    p.set_defaults(funktion=befehl_pack)

    p = unter.add_parser("init-profil", help="eigenes Absenderprofil anlegen")
    p.add_argument("name", help="Name des Profils, wird zum Dateinamen")
    p.add_argument("--ziel", help="Verzeichnis; ohne Angabe ~/.config/falzmarke/profiles/")
    p.set_defaults(funktion=befehl_init_profil)

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
