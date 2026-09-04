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
from falzmarke import emit as emit_modul
from falzmarke import lint as lint_modul
from falzmarke.markdown import MarkdownFehler, konvertiere, lies

PAKET = Path(__file__).resolve().parent
SKILL = PAKET.parent
TYPST_DIR = PAKET / "typst"
FONT_DIR = PAKET / "assets" / "fonts"

EXIT_OK, EXIT_EINGABE, EXIT_GEOMETRIE, EXIT_UMGEBUNG = 0, 1, 2, 3

# Die Monatsnamen stehen je Sprache in sprachen.MONATE.

# Datenvertrag und Leitwörter stehen in lint.py — dort, wo sie geprüft werden.
# cli importiert lint ohnehin; eine zweite Liste hier wäre eine Kopie, die bei
# der naechsten Aenderung still auseinanderlaeuft.
from falzmarke import anlagen as anlagen_modul  # noqa: E402
from falzmarke import sprachen  # noqa: E402
from falzmarke.lint import (  # noqa: E402
    INFOBLOCK_REIHENFOLGE, INFOBLOCK_WERT_MAX, PFLICHTFELDER)



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


def formatiere_datum(wert, format_name: str, sprache: str = sprachen.VORGABE) -> str:
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
    if sprache == "de":
        return f"{wert.day}. {sprachen.monat(sprache, wert.month)} {wert.year}"
    # Ohne Punkt hinter dem Tag: „26. August“ ist die deutsche Ordinalform, im
    # Englischen stünde dort ein Punkt, der nichts bedeutet.
    return f"{wert.day} {sprachen.monat(sprache, wert.month)} {wert.year}"


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

def baue_daten(kopf: dict, profil: dict, profil_pfad: Path, arbeitsverzeichnis: Path,
               brief_pfad: Path) -> dict:
    # Ohne diesen Abbruch meldet der Renderer „Pflichtfelder fehlen: empfaenger,
    # datum" — für ein Schreiben, das als E-Mail vollständig ist. Wer dann
    # `empfaenger:` ergänzt, läuft in den Ausschluss des Linters. Zwei Fehler
    # hintereinander, und keiner nennt die Ursache.
    if str(kopf.get("typ") or "brief") == "email":
        raise Eingabefehler(
            "Dieses Schreiben trägt `typ: email` und wird deshalb nicht als Brief gesetzt.\n"
            "Die E-Mail-Fassung erzeugt Dateien, kein PDF — der Befehl dafür entsteht in #65.\n"
            "Bis dahin prüft `falzmarke lint` die Datei; für einen Brief `typ: email` entfernen."
        )

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

    # Wie bei form: Der Brief schlägt das Profil. Ein Absender schreibt meist in
    # einer Sprache, aber der eine Brief ins Ausland soll nicht zwingen, das
    # Profil umzuschreiben.
    try:
        sprache = sprachen.pruefe(
            str(kopf.get("sprache", profil.get("sprache", sprachen.VORGABE))).lower())
    except ValueError as fehler:
        raise Eingabefehler(str(fehler)) from None

    norm = str(kopf.get("norm", "din5008")).lower()
    if norm != "din5008":
        raise Eingabefehler(
            f"norm: '{norm}' wird noch nicht unterstützt. Diese Fassung kennt nur din5008."
        )

    betreff = str(kopf["betreff"]).strip()
    if len(betreff) > 160:
        raise Eingabefehler(f"betreff: {len(betreff)} Zeichen — die Norm lässt höchstens 2 Zeilen zu.")

    datum = formatiere_datum(kopf["datum"], profil.get("datumsformat", "lang"), sprache)

    defaults = profil.get("infoblock_defaults") or {}
    info_roh = {**defaults, **(kopf.get("infoblock") or {})}
    infoblock = []
    # Woher der Wert kam. Der Brief ueberschreibt das Profil, und die Meldung
    # unten muss das sagen koennen: Ein Wert aus `infoblock_defaults` steht
    # NICHT in der Briefdatei, in der man ihn dann sucht (#244).
    herkunft: dict[str, str] = {}
    for schluessel, _ in INFOBLOCK_REIHENFOLGE:
        leitwort = sprachen.leitwort(sprache, schluessel)
        wert = info_roh.get(schluessel)
        if wert in (None, ""):
            continue
        if schluessel.endswith("_vom"):
            wert = formatiere_datum(wert, profil.get("datumsformat", "lang"), sprache)
        infoblock.append([leitwort, str(wert)])
        herkunft[leitwort] = (
            f"infoblock.{schluessel} im Brief"
            if schluessel in (kopf.get("infoblock") or {})
            else f"infoblock_defaults.{schluessel} im Profil")
    infoblock.append([sprachen.leitwort(sprache, "datum"), datum])

    # Die Zeilen des Informationsblocks stehen im 12-pt-Raster und haben feste
    # Höhe. Ein überlanger Wert würde deshalb nicht umbrechen, sondern über den
    # rechten Rand hinauslaufen — sichtbar erst im fertigen PDF. Lieber hier
    # abbrechen.
    zu_lang = [(lw, w) for lw, w in infoblock if len(w) > INFOBLOCK_WERT_MAX]
    if zu_lang:
        leitwort, wert = zu_lang[0]
        quelle = herkunft.get(leitwort)
        raise Eingabefehler(
            f"infoblock: '{leitwort}' ist mit {len(wert)} Zeichen zu lang "
            f"(höchstens {INFOBLOCK_WERT_MAX}, sonst reicht die Zeile über den rechten "
            "Rand des Satzspiegels hinaus).\n"
            f"        Wert: {wert}"
            + (f"\n        Steht in: {quelle}" if quelle else "")
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

    signatur = _signatur(kopf, profil, profil_pfad, brief_pfad, arbeitsverzeichnis)

    return {
        "form": form,
        "sprache": sprache,
        "gebiet": list(sprachen.GEBIET[sprache]),
        "woerter": sprachen.WOERTER[sprache],
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


def _signatur(
    kopf: dict, profil: dict, profil_pfad: Path, brief_pfad: Path, arbeitsverzeichnis: Path
) -> str | None:
    """Welches Unterschriftsbild gilt — und ob überhaupt eines gilt.

    Vorrang wie bei `unterzeichner:`: Was im Brief steht, schlägt das Profil.
    Ohne diese Möglichkeit unterschreibt ein Profil immer oder nie — ein Brief
    „i. A.“ trüge dann die Unterschrift der Geschäftsführung.

    | `signatur:` im Brief | Wirkung                                  |
    |----------------------|------------------------------------------|
    | fehlt                | Profilwert gilt                          |
    | `keine` oder leer    | kein Bild, drei Leerzeilen Raum          |
    | Dateiangabe          | dieses Bild, relativ zum Briefordner     |
    """
    def uebernimm(quelle: Path, name: str) -> str:
        ziel = arbeitsverzeichnis / "assets" / name
        ziel.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(quelle, ziel)
        return f"assets/{name}"

    if "signatur" in kopf:
        angabe = kopf["signatur"]
        text = "" if angabe is None else str(angabe).strip()
        if text == "" or text.lower() == "keine":
            return None
        quelle = datei_aus_dem_briefordner(brief_pfad, text, "Signaturbild")
        # Eigener Name: Das Profil legt sein Logo unter dem Dateinamen der
        # Quelle ab. Hieße die Unterschrift des Briefes genauso, überschriebe
        # eine der beiden die andere — still, und erst im PDF sichtbar.
        return uebernimm(quelle, f"signatur-brief{quelle.suffix}")

    if profil.get("signatur"):
        quelle = datei_aus_dem_profilordner(profil_pfad, profil["signatur"], "Signaturbild")
        return uebernimm(quelle, quelle.name)

    return None


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


def _datei_in_der_grenze(
    basis: Path, angabe: str, feld: str, vorspann: str, grenze: str, rat: str
) -> Path:
    """Löst eine Dateiangabe auf und hält sie in ihrem Ordner.

    Eine Datei-Angabe darf auf Nachbardateien zeigen — Logo, Unterschrift,
    eigener Briefkopf — aber nicht darüber hinaus. Der Grund ist das
    eingebettete Profil: Ein Brief bringt sein Profil im Frontmatter mit, und
    dann stammt beides von dem, der den Brief geschickt hat. Ohne diese Grenze
    bettet ein fremder Brief jede Bilddatei ein, die der Empfänger lesen kann —
    gemessen am 25.08.2026 mit `logo: ../geheim/privat.png`: das Bild stand im
    Briefkopf, der Lauf meldete 30/30 Maße eingehalten.

    `resolve()` folgt Symlinks, deshalb hilft auch ein getarnter Verweis nicht.

    Die Funktion steht bewusst nur einmal da: Der Fund von damals war nicht die
    fehlende Prüfung an sich, sondern dass dieselbe Fehlerklasse an einer von
    drei Stellen bedacht war. Wer einen weiteren Dateipfad einführt, ruft hier
    an — sonst wiederholt sich das.
    """
    ordner = basis.resolve()
    quelle = (basis / angabe).resolve()
    # Grenze zuerst, Existenz danach. Andersherum verriete die Meldung, ob eine
    # Datei ausserhalb liegt: `../../../etc/shadow` antwortete mit „nicht
    # gefunden“ oder „muss … liegen“ — je nachdem, und das ist ein Orakel.
    # Wer draussen ist, erfaehrt nichts ueber draussen.
    if ordner not in quelle.parents:
        raise Eingabefehler(
            f"{vorspann}: {feld} muss {grenze} (angegeben: {angabe}). {rat}"
        )
    if not quelle.is_file():
        raise Eingabefehler(f"{vorspann}: {feld} nicht gefunden: {quelle}")
    return quelle


def datei_aus_dem_profilordner(profil_pfad: Path, angabe: str, feld: str) -> Path:
    """Logo, Unterschrift und eigener Briefkopf eines Profils."""
    return _datei_in_der_grenze(
        profil_pfad.parent, angabe, feld,
        f"Profil {profil_pfad.name}", "im Profilordner liegen",
        "Die Datei neben das Profil legen.",
    )


def datei_aus_dem_briefordner(brief_pfad: Path, angabe: str, feld: str) -> Path:
    """Was ein einzelner Brief mitbringt — heute nur `signatur:`.

    Der Bezugspunkt ist hier der Brief, nicht das Profil: Eine
    Vertretungsunterschrift gehört zu dem Brief, der sie braucht, und liegt
    neben ihm. Sie im Profilordner zu verlangen, hieße für jede Vertretung ein
    fremdes Profilverzeichnis anzufassen.
    """
    return _datei_in_der_grenze(
        brief_pfad.parent, angabe, feld,
        f"Brief {brief_pfad.name}", "beim Brief liegen",
        "Die Datei neben den Brief legen.",
    )


def baue_profil_daten(profil: dict, profil_pfad: Path, arbeitsverzeichnis: Path) -> dict:
    """Kopiert Profil-Assets ins Arbeitsverzeichnis und macht Pfade relativ."""
    _pruefe_textzeilen(profil, profil_pfad)
    daten = json.loads(json.dumps(profil, default=str))
    briefkopf = daten.get("briefkopf") or {}
    logo = briefkopf.get("logo")
    if logo:
        quelle = datei_aus_dem_profilordner(profil_pfad, logo, "Logo")
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
    lint_modul.pruefe_body(body_md, versatz, bericht, kopf.get("dialekt"))
    if str(kopf.get("typ") or "brief") == "email":
        lint_modul.pruefe_email_anlagen(kopf, body_md, kopf_roh, bericht)
        # Dieselbe Auflösung wie in `eml._haenge_an`: relativ zum Brief, nicht
        # zum Arbeitsverzeichnis. Sonst misst der Linter eine andere Datei als
        # die, die angehängt wird.
        lint_modul.pruefe_anhanggroesse(kopf, Path(brief_pfad).parent, kopf_roh, bericht)
        lint_modul.pruefe_email_tabellen(body_md, versatz, bericht)

    hinweise: list = []
    try:
        # `lies` statt `konvertiere`: Hier wird geprüft, nicht gesetzt, und das
        # Ergebnis wird ohnehin verworfen. `konvertiere` hängt `emit.setze` an
        # — den **Typst**-Emitter, also den des Briefes. Für eine Mail ist das
        # der falsche: Ein Link ist dort zulässig, und der Typst-Emitter kennt
        # ihn zu Recht nicht (Issue #103). Er brach damit den Linter ab, statt
        # dass dieser den Befund gemeldet hätte.
        lies(body_md, versatz, dialekt=kopf.get("dialekt"),
             ziel=str(kopf.get("typ") or "brief"), hinweise=hinweise)
    except MarkdownFehler as fehler:
        bericht.fehler(fehler.zeile, fehler.regel, fehler.meldung)
    # Was gesetzt wird, aber auffällt. Der Linter ist die Stelle, an der es
    # jemand liest — die Prüfung selbst kann nur abbrechen oder durchlassen.
    for hinweis in hinweise:
        bericht.warnung(hinweis.zeile, hinweis.regel, hinweis.meldung)

    if kopf.get("profil"):
        try:
            profil, profil_datei = lade_profil(kopf["profil"], profil_verzeichnis, brief_pfad)
        except Eingabefehler as fehler:
            bericht.fehler(1, "profil", str(fehler).splitlines()[0])
        else:
            # Das Profil ist hier ohnehin geladen. Es wegzuwerfen und die
            # Mail-Angaben erst beim Bauen der .eml zu vermissen, hieße den
            # Fehler in den teuren Schritt zu verschieben.
            # Gilt fuer beide Typen: Den Briefkopf setzt auch die E-Mail
            # nicht, aber ein Profil wird fuer beides benutzt, und eine tote
            # Angabe bleibt eine tote Angabe.
            lint_modul.pruefe_briefkopf(profil, bericht)
            if str(kopf.get("typ") or "brief") == "email":
                # Der Pfad wird mitgegeben, weil eine Profildatei auf Dateien
                # neben sich zeigen kann (`email.logo`) — ohne ihn bliebe die
                # Logo-Pruefung stumm, statt zu melden, dass sie nicht lief.
                lint_modul.pruefe_email_profil(profil, bericht, profil_datei)
                # Braucht Profil UND Text — deshalb hier und nicht in einer der
                # beiden Prüfungen, die nur eines von beidem sehen.
                lint_modul.pruefe_email_ton(profil, kopf, body_md, bericht)
    return bericht


def rendere(
    brief_pfad: Path,
    ausgabe: Path | None = None,
    *,
    profil_verzeichnis: Path | None = None,
    pdfa: bool = True,
    pdfua: bool = False,
    #: Werte für `{{platzhalter}}` im Brieftext — nur der Serienbrief setzt sie.
    #: `None` heisst: unveraendert der Weg, den jeder einzelne Brief nimmt.
    ersetzungen: dict | None = None,
    format_name: str = "pdf",
    ppi: int = 120,
    anlagen_bericht: list | None = None,
) -> tuple[Path, str]:
    """Setzt den Brief. Gibt (Pfad, Form) zurück.

    `anlagen_bericht`: Wer wissen will, was beim Anhängen von `anlagen_dateien`
    geschah, gibt eine Liste mit — der Bericht wird angehängt. Ein
    Rückgabewert mehr hätte jeden Aufrufer gebrochen, ein Modul-Global wäre
    Zustand, den niemand erwartet.
    """
    typst = _typst_modul()
    kopf, body_md, versatz = lies_brief(brief_pfad)
    profil, profil_pfad = lade_profil(kopf.get("profil", ""), profil_verzeichnis, brief_pfad)

    # Was ins PDF gelegt wird. Der Datenvertrag hat die Einträge schon geprüft
    # (`lint.pruefe_eingebettet`); hier steht nur noch, ob überhaupt etwas da
    # ist — davon hängt die PDF/A-Stufe ab.
    eingebettet = [e for e in (kopf.get("eingebettet") or []) if isinstance(e, dict)]

    with tempfile.TemporaryDirectory(prefix="falzmarke-") as tmp:
        arbeit = Path(tmp)
        baue_arbeitsverzeichnis(arbeit)
        daten = baue_daten(kopf, profil, profil_pfad, arbeit, brief_pfad)
        profil_daten = baue_profil_daten(profil, profil_pfad, arbeit)

        try:
            if ersetzungen is None:
                body_typst = konvertiere(body_md, versatz, dialekt=kopf.get("dialekt"))
            else:
                # Der Serienbrief (#3). Zwischen Lesen und Setzen greift hier
                # die Ersetzung — und genau dort, weil der Baum an dieser
                # Stelle bereits geprüft ist: Was jetzt eingesetzt wird, läuft
                # nie wieder durch den Parser und kann kein Markup mehr werden.
                #
                # Der Umweg über eine Datei mit rohem Ersatz wäre einfacher und
                # falsch: Ein Empfänger namens `Müller & Söhne *GmbH*` stünde
                # dann kursiv im Brief.
                from falzmarke import emit as _emit
                from falzmarke import serie as _serie

                bloecke = lies(body_md, versatz, dialekt=kopf.get("dialekt"))
                body_typst = _emit.setze(_serie.fuelle_bloecke(bloecke, ersetzungen))
        except MarkdownFehler as fehler:
            raise Eingabefehler(f"{brief_pfad.name}, {fehler}") from None
        if not body_typst.strip():
            raise Eingabefehler(f"{brief_pfad.name}: Der Brief hat keinen Text.")

        # Eigener Briefkopf, falls das Profil einen mitbringt
        kopf_import, kopf_argument = "", ""
        eigener_kopf = profil.get("briefkopf_typ")
        if eigener_kopf:
            quelle = datei_aus_dem_profilordner(profil_pfad, eigener_kopf, "briefkopf_typ")
            shutil.copy2(quelle, arbeit / "briefkopf-eigen.typ")
            kopf_import = '#import "briefkopf-eigen.typ": briefkopf as eigener-kopf\n'
            kopf_argument = ", briefkopf-eigen: eigener-kopf"

        # Die eingebetteten Dateien: kopiert in den Arbeitsordner, weil Typst
        # nur unterhalb seiner Wurzel lesen darf, und als `#pdf.attach` VOR dem
        # Brieftext gesetzt. Sie erzeugen keine Ausgabe — sie legen die Datei in
        # das PDF (Issue #114).
        attach_zeilen = ""
        for nummer, eintrag in enumerate(eingebettet, start=1):
            quelle = Path(eintrag["datei"])
            if not quelle.is_absolute():
                quelle = brief_pfad.parent / quelle
            if not quelle.is_file():
                raise Eingabefehler(
                    f"`eingebettet:` Eintrag {nummer}: {quelle} gibt es nicht.\n"
                    "Der Pfad ist relativ zur Briefdatei.")
            ziel = arbeit / f"anlage-{nummer}{quelle.suffix}"
            shutil.copy2(quelle, ziel)
            attach_zeilen += (
                f"#pdf.attach({emit_modul.zeichenkette(ziel.name)}, "
                f"mime-type: {emit_modul.zeichenkette(str(eintrag['typ']))}, "
                f"description: {emit_modul.zeichenkette(str(eintrag['beschreibung']))}"
                + (f", relationship: {emit_modul.zeichenkette(str(eintrag['beziehung']).lower())}"
                   if eintrag.get("beziehung") else "")
                + ")\n"
            )

        haupt = arbeit / "main.typ"
        haupt.write_text(
            # `zitat` und `codeblock` gehoeren zum Dialekt 1.1: Der Brieftext
            # ruft sie auf, also muessen sie hier im Namensraum stehen.
            '#import "falzmarke.typ": brief, zitat, codeblock\n'
            + kopf_import
            + "#let profil = json(bytes(sys.inputs.profil))\n"
            "#let daten = json(bytes(sys.inputs.daten))\n"
            f"#show: brief.with(profil: profil, daten: daten{kopf_argument})\n\n"
            + attach_zeilen
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
            #
            # A-3b nur, wenn wirklich etwas eingebettet wird: PDF/A-2 kennt
            # keine beliebigen Dateien im Dokument, A-3 lässt sie zu. Die Stufe
            # wird verlangt, nicht stillschweigend umgestellt (ADR 0033) —
            # `tests/test_einbetten.py` hält beide Richtungen fest.
            stufe = "a-3b" if eingebettet else "a-2b"
            argumente["pdf_standards"] = [stufe, "ua-1"] if pdfua else stufe

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

        # Anlagen zuletzt: Der Brief ist dann fertig gemessen und vermerkt, und
        # die angehängten Seiten verschieben nichts an seiner Geometrie.
        dateien = als_liste(kopf.get("anlagen_dateien"))
        if dateien:
            try:
                bericht = anlagen_modul.haenge_an(
                    ausgabe, anlagen_modul.loese_auf(dateien, brief_pfad))
            except anlagen_modul.AnlagenFehler as fehler:
                raise Eingabefehler(str(fehler)) from None
            if anlagen_bericht is not None:
                anlagen_bericht.append(bericht)

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


def _melde_anlagen(bericht: dict) -> None:
    """Sagt, was angehängt wurde — und was das für die PDF/A-Kennzeichnung hiess.

    Beides still zu tun waere das Schlechteste: Wer nicht merkt, dass die
    Kennzeichnung fiel, legt eine Datei ins Archiv, die er fuer PDF/A haelt.
    Wer nicht merkt, dass sie blieb, weiss nicht, worauf sie beruht.
    """
    dazu = bericht["seiten_nachher"] - bericht["seiten_vorher"]
    namen = ", ".join(a["datei"] for a in bericht["anlagen"])
    print(f"OK  {len(bericht['anlagen'])} Anlage(n) angehängt, {dazu} Seiten: {namen}")

    if bericht["ohne_deklaration"]:
        print(
            "    Die PDF/A-Kennzeichnung wurde entfernt: "
            + ", ".join(bericht["ohne_deklaration"])
            + " trägt keine.\n"
            "    falzmarke hat diese Datei nicht gesetzt und kann ihre Konformität nicht\n"
            "    prüfen. Ein PDF, das PDF/A behauptet und es nicht ist, fällt erst im\n"
            "    Archiv auf. Prüfen lässt sich das Ergebnis mit veraPDF.",
            file=sys.stderr,
        )
    elif bericht["pdfa_nachher"]:
        print(
            f"    PDF/A-{bericht['pdfa_nachher']} bleibt gekennzeichnet — jede Anlage\n"
            "    deklariert es selbst. Das ist ihre Aussage, keine Prüfung: Belegt ist\n"
            "    die Konformität erst durch veraPDF.",
        )


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

    anlagen_berichte: list = []
    pdf, form = rendere(
        Path(args.brief),
        Path(args.output) if args.output else None,
        profil_verzeichnis=Path(args.profiles) if args.profiles else None,
        pdfa=not args.no_pdfa,
        pdfua=args.pdfua,
        anlagen_bericht=anlagen_berichte,
    )
    print(f"OK  PDF geschrieben: {pdf}")
    for anlagen_bericht in anlagen_berichte:
        _melde_anlagen(anlagen_bericht)

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
    # Die Kennzeichnung faellt absichtlich, wenn eine Anlage keine traegt — das
    # ist dann kein Fehler des Briefes, und die Meldung dazu steht schon oben.
    # Sie hier als Geometriebefund zu fuehren, wuerde EXIT_GEOMETRIE ergeben und
    # behaupten, die Masse stimmten nicht.
    kennzeichnung_gefallen = any(b["ohne_deklaration"] for b in anlagen_berichte)
    # Erneut aus der Quelle statt durchgereicht: `rendere` gibt Pfad und Form
    # zurück, keine Kopfdaten, und ein dritter Rückgabewert bräche jeden
    # Aufrufer. Die Datei ist zu diesem Zeitpunkt ohnehin gelesen.
    eingebettet_gefragt = bool(lies_brief(Path(args.brief))[0].get("eingebettet"))
    if not args.no_pdfa and not kennzeichnung_gefallen:
        # Der Name der Prüfung nennt die Stufe, die das Dokument behauptet —
        # nicht die, die es meistens hat. Ein Brief mit eingebetteter Datei ist
        # A-3b, und „PDF/A-2b: fehlt" wäre dort eine Meldung über die falsche
        # Sache (Issue #114).
        stufe = geometrie.pdfa_stufe(pdf)
        erwartet = "3b" if eingebettet_gefragt else "2b"
        bericht.wahr(f"PDF/A-{erwartet}", stufe == erwartet,
                     f"pdfaid part {erwartet[0]}, conformance B",
                     f"PDF/A-{stufe}" if stufe else "fehlt")
    print(bericht.als_text(ausfuehrlich=args.verbose))
    if not bericht.ok:
        print("\nFEHLGESCHLAGEN — das PDF hält die Maße aus DIN 5008 nicht ein.", file=sys.stderr)
        return EXIT_GEOMETRIE
    return EXIT_OK


#: Was eine Begleitmail von ihrem Brief erbt, wenn sie es selbst nicht sagt.
#:
#: `betreff` und `profil`: Beide beschreiben denselben Vorgang, und zweimal
#: gepflegt driften sie auseinander (Issue #78). Wer in der Mail einen eigenen
#: Betreff schreibt, bekommt seinen — geerbt wird nur, was fehlt.
#:
#: **Nicht** dabei: `empfaenger`. Eine Postanschrift ist keine Mailadresse, und
#: `an:` bleibt Pflicht der Mail. `datum` ebenso wenig — das setzt der
#: Mailclient beim Versand, und ein geerbtes Briefdatum wäre eine Angabe über
#: den falschen Vorgang.
ERBT_VOM_BRIEF = ("betreff", "profil", "dialekt", "sprache")


def _baue_nachricht(eml_modul, kopf, profil, body_md, bloecke,
                    brief_pfad, mit_quelle, profil_pfad):
    """Der Bau der Nachricht, einmal — mit und ohne Begleitbrief.

    Als Funktion statt als Kopie: Der Begleitbrief lebt in einem
    Arbeitsverzeichnis, das nur so lange bestehen darf, wie das PDF gelesen
    wird. Damit steht der Bau innerhalb eines `with` und ohne Begleitbrief
    ausserhalb — zwei Stellen, ein Ablauf.
    """
    try:
        return eml_modul.baue(kopf, profil, body_md, bloecke,
                              brief_pfad=brief_pfad, mit_quelle=mit_quelle,
                              profil_pfad=profil_pfad)
    except (ValueError, FileNotFoundError) as fehler:
        raise Eingabefehler(f"{Path(brief_pfad).name}: {fehler}") from None


def setze_email(brief_pfad: Path, ausgabe: Path | None = None, *,
                profil_verzeichnis: Path | None = None,
                mit_quelle: bool = False) -> tuple[Path, list[Path]]:
    """Setzt die E-Mail-Fassung. Gibt (.eml, alle geschriebenen Dateien) zurück.

    Kein Versandweg — ADR 0034. Was hier entsteht, sind Dateien; ob und wann
    sie jemand abschickt, entscheidet ein Mailprogramm, nicht dieses Werkzeug.

    Trägt die Nachricht ein Feld `brief:`, wird dieser Brief **jetzt gesetzt**
    und sein PDF angehängt (Issue #78). Das ist der Unterschied zu
    `anlagen_dateien:`, das vorhandene Dateien nimmt: Hier kann kein veraltetes
    PDF mitreisen, weil es keines gibt, das älter wäre als dieser Aufruf.
    """
    from falzmarke import eml as eml_modul

    kopf, body_md, versatz = lies_brief(brief_pfad)
    if str(kopf.get("typ") or "brief") != "email":
        raise Eingabefehler(
            f"{brief_pfad.name} trägt kein `typ: email` und ist damit ein Brief.\n"
            "Für ein PDF `falzmarke render` verwenden."
        )
    # Der Brief, der mitreist (#78). Er wird VOR dem Profil aufgelöst, weil die
    # Mail ihr Profil von ihm erben kann.
    if kopf.get("brief"):
        quelle = Path(str(kopf["brief"]))
        if not quelle.is_absolute():
            quelle = brief_pfad.parent / quelle
        if not quelle.is_file():
            raise Eingabefehler(
                f"{brief_pfad.name}: `brief: {kopf['brief']}` gibt es nicht.\n"
                "Der Pfad ist relativ zur Nachricht.")
        briefkopf, _, _ = lies_brief(quelle)
        if str(briefkopf.get("typ") or "brief") == "email":
            raise Eingabefehler(
                f"{brief_pfad.name}: `brief:` zeigt auf {quelle.name}, und das trägt "
                "selbst `typ: email`. Eine Nachricht kann keine Nachricht begleiten.")
        # Erben, bevor irgendetwas davon gelesen wird.
        for feld in ERBT_VOM_BRIEF:
            if not kopf.get(feld) and briefkopf.get(feld):
                kopf[feld] = briefkopf[feld]

    profil, profil_pfad = lade_profil(kopf.get("profil", ""), profil_verzeichnis, brief_pfad)

    try:
        bloecke = lies(body_md, versatz, dialekt=kopf.get("dialekt"), ziel="email")
    except MarkdownFehler as fehler:
        raise Eingabefehler(f"{brief_pfad.name}, {fehler}") from None
    if not body_md.strip():
        raise Eingabefehler(f"{brief_pfad.name}: Die Nachricht hat keinen Text.")

    # Der Brief wird JETZT gesetzt, in einen Arbeitsordner. Damit kann kein
    # veraltetes PDF mitreisen — es gibt keines, das älter wäre als dieser
    # Aufruf. Genau das war der Punkt in #78: „ein veraltetes PDF in einer
    # frischen Mail muss auffallen und nicht stillschweigend mitreisen."
    if kopf.get("brief"):
        quelle = Path(str(kopf["brief"]))
        if not quelle.is_absolute():
            quelle = brief_pfad.parent / quelle
        with tempfile.TemporaryDirectory(prefix="falzmarke-begleit-") as arbeit:
            pdf, _ = rendere(quelle, Path(arbeit) / f"{quelle.stem}.pdf",
                             profil_verzeichnis=profil_verzeichnis)
            # An `anlagen_dateien` anhängen statt es zu ersetzen: Wer daneben
            # noch etwas beilegt, behält es.
            kopf = dict(kopf)
            kopf["anlagen_dateien"] = (
                list(eml_modul._als_liste(kopf.get("anlagen_dateien"))) + [str(pdf)])
            nachricht = _baue_nachricht(eml_modul, kopf, profil, body_md, bloecke,
                                        brief_pfad, mit_quelle, profil_pfad)
    else:
        nachricht = _baue_nachricht(eml_modul, kopf, profil, body_md, bloecke,
                                    brief_pfad, mit_quelle, profil_pfad)

    ziel = Path(ausgabe) if ausgabe else brief_pfad.with_suffix("")
    sprache = str(kopf.get("sprache") or profil.get("sprache") or "de")
    dateien = eml_modul.schreibe(
        nachricht, ziel,
        html=eml_modul.begleit_html(kopf, profil, bloecke, sprache=sprache),
        text=eml_modul.textteil(kopf, profil, bloecke),
    )
    return dateien[0], dateien


def befehl_email(args) -> int:
    from falzmarke import pruefung_eml

    brief = Path(args.brief)
    profile = Path(args.profiles) if args.profiles else None

    # Dieselbe Reihenfolge wie beim Brief: Ein Eingabefehler soll Exit 1
    # ergeben und kein Setzen kosten.
    vorpruefung = linte(brief, profile)
    if not vorpruefung.ok:
        print(vorpruefung.als_text(brief.name), file=sys.stderr)
        return EXIT_EINGABE
    for befund in vorpruefung.befunde:
        print(befund.als_zeile(brief.name), file=sys.stderr)

    eml_pfad, dateien = setze_email(
        brief, Path(args.output) if args.output else None,
        profil_verzeichnis=profile, mit_quelle=args.mit_quelle)

    behalten = {".eml"}
    if args.html:
        behalten.add(".html")
    if args.txt:
        behalten.add(".txt")
    for datei in dateien:
        if datei.suffix in behalten:
            print(f"OK  geschrieben: {datei}")
        else:
            datei.unlink()

    # `verify --email` läuft mit — dieselbe Zusage wie beim PDF: Was
    # herauskommt, wird nachgemessen, nicht nur erzeugt.
    bericht = pruefung_eml.pruefe(eml_pfad)
    print(bericht.als_text(ausfuehrlich=args.verbose))
    if not bericht.ok:
        print("\nFEHLGESCHLAGEN — die Nachricht hält die eigenen Vorgaben nicht ein.",
              file=sys.stderr)
        return EXIT_GEOMETRIE

    # Der einzige Schritt mit einer Wirkung außerhalb dieses Prozesses — und er
    # steht hinter der Messung: Was seine eigene Prüfung nicht besteht, wird
    # niemandem ins Mailprogramm gelegt, wo der nächste Handgriff
    # „Weiterleiten" heißt (Regel 0 im Skill, ADR 0038 Punkt 3).
    #
    # Spät importiert, damit `subprocess` nicht in jedem Prozess liegt, der
    # `falzmarke.cli` lädt — der MCP-Dienst tut das auf Modulebene.
    if args.oeffnen:
        from falzmarke import oeffnen as oeffnen_modul

        grund = oeffnen_modul.oeffne(eml_pfad)
        if grund:
            # Kein anderer Exit-Code: Die Datei ist geschrieben und gemessen,
            # das ist die Zusage des Befehls (ADR 0038, Punkt 4).
            print(f"HINWEIS  nicht geöffnet: {grund}\n"
                  f"         Die Nachricht liegt fertig da: {eml_pfad}",
                  file=sys.stderr)
        else:
            print(f"OK  geöffnet: {eml_pfad}")
    return EXIT_OK


def befehl_verify(args) -> int:
    from falzmarke import geometrie

    pdf = Path(args.pdf)
    if not pdf.is_file():
        print(f"Datei nicht gefunden: {pdf}", file=sys.stderr)
        return EXIT_EINGABE

    if getattr(args, "email", False):
        return _verify_email(args, pdf)

    try:
        return _verify(args, pdf, geometrie)
    except geometrie.PdfUnlesbar as fehler:
        print(f"FEHLER  {fehler}", file=sys.stderr)
        return EXIT_EINGABE


def _verify(args, pdf: Path, geometrie) -> int:
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


def _verify_email(args, pfad: Path) -> int:
    """`verify --email`: misst die fertige Nachricht, nie die Absicht.

    Derselbe Bericht, dieselben Exit-Codes wie beim PDF. Ein zweiter
    Berichtstyp hieße, dass ein Aufrufer zwei Ausgaben auseinanderhalten muss,
    um dieselbe Frage beantwortet zu bekommen.
    """
    from falzmarke import pruefung_eml

    try:
        bericht = pruefung_eml.pruefe(pfad)
    except pruefung_eml.EmlUnlesbar as fehler:
        print(f"FEHLER  {fehler}", file=sys.stderr)
        return EXIT_EINGABE

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


def befehl_mcp(args) -> int:
    """Der Dienst liegt in einem eigenen Modul — es zieht das SDK erst beim Start."""
    from falzmarke import dienst

    return dienst.main()


def befehl_serie(args) -> int:
    """Eine Vorlage plus Datenquelle ergibt n Briefe (#3).

    Der Aufbau folgt dem, was der Vorgang verlangt: Ein Datensatz, der nicht
    durchgeht, bricht **diesen** ab und nicht die Serie. Bei zweihundert
    Empfängern und einem zu langen Namen wäre das Gegenteil die falsche
    Antwort — man hätte am Ende nichts statt hundertneunundneunzig Briefen.

    Was den ganzen Lauf anhält, ist ein Fehler an der Vorlage oder der
    Datenquelle: ein Platzhalter ohne Spalte, eine unlesbare Datei. Der beträfe
    jeden Datensatz, und zweihundertmal dieselbe Meldung ist keine Hilfe.
    """
    import yaml

    from falzmarke import serie

    vorlage = Path(args.vorlage)
    ziel = Path(args.ziel)
    profile = Path(args.profiles) if args.profiles else None

    try:
        kopf, body_md, _versatz = lies_brief(vorlage)
        saetze = serie.lies_daten(Path(args.daten))
    except (Eingabefehler, serie.Seriefehler) as fehler:
        print(str(fehler), file=sys.stderr)
        return EXIT_EINGABE

    if not saetze:
        print(f"{Path(args.daten).name}: kein Datensatz.", file=sys.stderr)
        return EXIT_EINGABE

    # Die Vorlage wird EINMAL gegen die Spalten gehalten, nicht je Datensatz.
    roh = vorlage.read_text(encoding="utf-8")
    spalten = set(saetze[0])
    try:
        serie.pruefe_vorlage(serie.platzhalter(roh), spalten)
    except serie.Seriefehler as fehler:
        print(str(fehler), file=sys.stderr)
        return EXIT_EINGABE

    ziel.mkdir(parents=True, exist_ok=True)
    bericht = serie.Bericht()

    with tempfile.TemporaryDirectory(prefix="falzmarke-serie-") as tmp:
        arbeit = Path(tmp)
        for nummer, satz in enumerate(saetze, start=1):
            # +2, weil Zeile 1 die Kopfzeile ist. Der Nutzer sucht die Zeile in
            # SEINER Datei, nicht den Index im Programm.
            zeile = nummer + 1 if Path(args.daten).suffix.lower() == ".csv" else nummer
            name = serie.dateiname(satz, nummer, args.benennen)
            ergebnis = serie.Ergebnis(zeile=zeile, name=name)
            try:
                # Das Frontmatter wird im Rohtext gefüllt — ein YAML-Wert ist
                # bereits Text. Der Brieftext NICHT: Der geht als Vorlage in
                # `rendere` und wird dort im geprüften Baum ersetzt.
                gefuellt = serie.fuelle_kopf(kopf, satz)
                einzeln = arbeit / f"{name}.md"
                einzeln.write_text(
                    "---\n" + yaml.safe_dump(gefuellt, allow_unicode=True, sort_keys=False)
                    + "---\n" + body_md,
                    encoding="utf-8")

                pruefung = linte(einzeln, profile)
                if not pruefung.ok:
                    erster = next(b for b in pruefung.befunde if b.schwere == lint_modul.FEHLER)
                    raise Eingabefehler(f"{erster.regel}: {erster.meldung}")

                pdf, _ = rendere(einzeln, ziel / f"{name}.pdf",
                                 profil_verzeichnis=profile, ersetzungen=satz)
                ergebnis.pfad = pdf
            except (Eingabefehler, serie.Seriefehler, ValueError, OSError) as fehler:
                ergebnis.fehler = str(fehler).splitlines()[0]
            bericht.ergebnisse.append(ergebnis)

    print(bericht.als_text())

    if args.sammel and bericht.geschrieben:
        from falzmarke import anlagen

        sammel = ziel / "serie.pdf"
        erste = bericht.geschrieben[0].pfad
        shutil.copy2(erste, sammel)
        weitere = [e.pfad for e in bericht.geschrieben[1:] if e.pfad]
        if weitere:
            anlagen.haenge_an(sammel, weitere)
        print(f"OK  Sammel-PDF: {sammel} ({len(bericht.geschrieben)} Briefe)")

    return EXIT_OK if bericht.ok else EXIT_EINGABE


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
dialekt: "1.1"
empfaenger:
{empfaenger}
datum: {datum}
betreff: {betreff}
anrede: Sehr geehrte Damen und Herren,
---
"""


def befehl_einlesen(args) -> int:
    """Ein bestehendes PDF als falzmarke-Markdown-Gerüst (#191).

    Lücken sind hier KEIN Fehler, sondern das erwartete Ergebnis: Bei einem
    Brief ohne DIN-Raster ist die Lücke die einzige ehrliche Antwort. Der
    Befehl endet deshalb mit EXIT_OK, auch wenn Felder offen bleiben — ein
    Skript, das den Exit-Code prüft, soll nicht bei jedem Altbrief „scheitern".

    Für die maschinelle Auswertung gibt es `--json`, wie bei `lint` und
    `verify`. Einen sechsten Exit-Code einzuführen wäre eine Änderung am
    öffentlichen Vertrag (docs/cli.md nennt 0–4) und für dieses Feature nicht
    nötig.
    """
    from falzmarke.einlesen import PdfUnlesbar, lies_pdf

    try:
        ergebnis = lies_pdf(Path(args.pdf))
    except PdfUnlesbar as fehler:
        print(f"FEHL  {fehler}", file=sys.stderr)
        return EXIT_EINGABE

    if args.json:
        import json as _json

        print(_json.dumps({
            "quelle": ergebnis.quelle,
            "form": ergebnis.form,
            "felder": ergebnis.felder,
            "luecken": [
                {"feld": l.feld, "grund": l.grund, "kandidat": l.kandidat}
                for l in ergebnis.luecken
            ],
            "koerper": ergebnis.koerper,
        }, ensure_ascii=False, indent=2))
        return EXIT_OK

    markdown = ergebnis.als_markdown()
    if args.ziel:
        ziel = Path(args.ziel)
        if ziel.exists() and not args.ueberschreiben:
            print(f"{ziel} gibt es schon — nichts überschrieben.", file=sys.stderr)
            return EXIT_EINGABE
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(markdown, encoding="utf-8")
        print(f"OK  Gerüst geschrieben: {ziel}")
    else:
        print(markdown)

    if not ergebnis.luecken:
        return EXIT_OK

    # Die Lücken werden GENANNT, nicht gezählt: "3 Felder fehlen" sagt niemandem,
    # was zu tun ist. Auf stderr, damit `falzmarke einlesen x.pdf > y.md` sauber
    # bleibt.
    print(
        f"\nHINWEIS  {len(ergebnis.luecken)} Feld(er) konnten nicht belegt werden "
        f"und stehen als Kommentar im Gerüst:",
        file=sys.stderr,
    )
    for luecke in ergebnis.luecken:
        print(f"  {luecke.feld}: {luecke.grund}", file=sys.stderr)
        if luecke.kandidat:
            erste = luecke.kandidat.split("\n")[0]
            print(f"    Kandidat (ungeprüft): {erste}", file=sys.stderr)
    print(
        "\nHier wird bewusst nicht geraten: Ein falsch erkannter Empfänger fällt\n"
        "erst im gedruckten Brief auf. Die Lücken füllt, wer den Brief liest.",
        file=sys.stderr,
    )
    return EXIT_OK


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
        p.add_argument("pdf", help="PDF — oder mit --email eine .eml")
        p.add_argument("--email", action="store_true",
                       help="eine .eml prüfen statt eines PDF")
        p.add_argument("--form", choices=["A", "B", "a", "b"],
                       help="ohne Angabe aus den Falzmarken erkannt")
        p.add_argument("--json", action="store_true")
        p.add_argument("--verbose", action="store_true", help="alle Prüfungen zeigen")
        p.set_defaults(funktion=befehl_verify)

    p = unter.add_parser("serie", help="eine Vorlage plus Datenquelle ergibt n Briefe")
    p.add_argument("vorlage", help="Markdown-Vorlage mit `{{platzhalter}}`")
    p.add_argument("--daten", required=True, help="CSV- oder JSON-Datei mit den Datensätzen")
    p.add_argument("--ziel", required=True, help="Ordner für die erzeugten PDFs")
    p.add_argument("--benennen", metavar="SPALTE",
                   help="Spalte, aus der der Dateiname gebildet wird "
                        "(die laufende Nummer steht ohnehin davor)")
    p.add_argument("--sammel", action="store_true",
                   help="zusätzlich alle Briefe in einer Datei, für den Druck")
    p.add_argument("--profiles", help="Profilverzeichnis")
    p.set_defaults(funktion=befehl_serie)

    p = unter.add_parser("email", help="E-Mail-Fassung als .eml setzen und nachmessen")
    p.add_argument("brief", help="Markdown-Datei mit `typ: email`")
    p.add_argument("-o", "--output", help="Zielname ohne Endung")
    p.add_argument("--html", action="store_true", help="die .html-Vorschau behalten")
    p.add_argument("--txt", action="store_true", help="den Textteil als .txt behalten")
    p.add_argument("--mit-quelle", dest="mit_quelle", action="store_true",
                   help="die Markdown-Quelle als text/markdown-Teil mitschicken")
    p.add_argument("--oeffnen", action="store_true",
                   help="die fertige .eml dem Standardprogramm übergeben")
    p.add_argument("--profiles")
    p.add_argument("--verbose", action="store_true", help="alle Prüfungen zeigen")
    p.set_defaults(funktion=befehl_email)

    p = unter.add_parser("preview", help="PNG der ersten Seite")
    p.add_argument("brief")
    p.add_argument("-o", "--output")
    p.add_argument("--ppi", type=int, default=120)
    p.add_argument("--profiles")
    p.set_defaults(funktion=befehl_preview)

    p = unter.add_parser("mcp", help="als MCP-Dienst über stdio laufen")
    p.set_defaults(funktion=befehl_mcp)

    p = unter.add_parser("profiles", help="verfügbare Absenderprofile auflisten")
    p.add_argument("--profiles", dest="profiles")
    p.set_defaults(funktion=befehl_profiles)

    p = unter.add_parser(
        "einlesen", help="ein bestehendes PDF als Markdown-Gerüst zurücklesen"
    )
    p.add_argument("pdf")
    p.add_argument("-o", "--ziel", help="Zieldatei (ohne sie: Ausgabe auf stdout)")
    p.add_argument(
        "--ueberschreiben", action="store_true", help="vorhandene Zieldatei ersetzen"
    )
    p.add_argument("--json", action="store_true", help="Befund maschinenlesbar")
    p.set_defaults(funktion=befehl_einlesen)

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
