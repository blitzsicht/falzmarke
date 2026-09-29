#!/usr/bin/env python3
"""Packt den Skill als Plugin für ChatGPT („Skills only").

Warum es das gibt: Eigene Skills nimmt ChatGPT nur in der Desktop-App und in
Business-, Enterprise- und Edu-Tarifen an. Im Browser und auf dem Handy mit
privatem Tarif erreicht ein Skill die Nutzer nur als Plugin, das OpenAI geprüft
hat. Am 29.09.2026 hat ChatGPT genau deshalb bei einem Leser der Anleitung die
Installation abgelehnt. Im selben Browser-Chat (Plus) lief der hochgeladene Skill
danach durch: `verify: 34/34`. Die Laufzeit reicht also, es fehlt nur der Weg
hinein.

Das Plugin ist kein zweiter Skill. Es ist derselbe Ordner wie im Offline-Paket
(`paket/falzmarke/`, samt typst-Wheel), dazu ein Manifest. Name, Version und
Kurzbeschreibung kommen aus `pyproject.toml` — eine Stelle, nicht zwei.

Aufruf (von `scripts/skill_packen.sh`, nach dem Offline-Paket):

    python3 scripts/plugin_packen.py paket/falzmarke falzmarke-chatgpt-plugin.zip

Bricht mit Code 1 ab, bevor ein Paket entsteht, das OpenAI zurückweisen würde.
"""

from __future__ import annotations

import json
import os
import re
import sys
import tomllib
import zipfile
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent

# ── Sollwerte ─────────────────────────────────────────────────────────────
# Grenzen der Einreichung, gelesen am 29.09.2026 unter
# https://developers.openai.com/plugins/deploy/submission-errors.md
# Die Grenze je Skill nennt OpenAI nur im Fehlertext des Portals; sie ist
# deshalb hier nicht geprüft, sondern bis zur ersten Einreichung offen.
#: ZIP „100 MB or less". Per Umgebungsvariable absenkbar, damit die
#: Gegenprobe den Abbruch auslösen kann, ohne 100 MB zu bauen.
MAX_ZIP_BYTES = int(os.environ.get("FALZMARKE_PLUGIN_MAX_BYTES", "100000000"))
MAX_EINTRAEGE = 5000
MAX_PFADSEGMENTE = 20
#: SKILL.md `description`: höchstens 1024 Zeichen.
MAX_DESCRIPTION = 1024
#: `plugin-name:skill-name` höchstens 64 Zeichen.
MAX_QUALIFIZIERT = 64
#: Listing, „Final directory submission": Anzeigename und Kurzbeschreibung je
#: höchstens 30 Zeichen, lange Beschreibung höchstens 4000, höchstens drei
#: Startprompts zu je höchstens 128 Zeichen. Diese Regeln greifen erst bei der
#: Einreichung, nicht beim Hochladen — ein Paket kann den Upload bestehen und
#: dort scheitern. Die erste Fassung dieses Skripts hätte es: 99 Zeichen
#: Kurzbeschreibung, rund 230 Zeichen Startprompt.
MAX_ANZEIGENAME = 30
MAX_KURZBESCHREIBUNG = 30
MAX_LANGBESCHREIBUNG = 4000
MAX_STARTPROMPTS = 3
MAX_STARTPROMPT = 128

SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
#: Muster für `name` aus dem Schema oben (gelesen am 29.09.2026).
NAME_MUSTER = re.compile(r"^(?!.*(?:--|\.\.))[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$")

WEBSITE = "https://falzmarke.com"
DATENSCHUTZ = "https://falzmarke.com/datenschutz/"
REPOSITORY = "https://github.com/blitzsicht/falzmarke"
KURZBESCHREIBUNG = "DIN-5008-Briefe und E-Mails"
LANGBESCHREIBUNG = (
    "falzmarke setzt Geschäftsbriefe und E-Mails nach DIN 5008: Briefe als PDF mit "
    "Falz- und Lochmarken und einem Anschriftfeld, das ins Fenster des Umschlags "
    "passt, E-Mails als .eml mit Signatur. Danach misst es das fertige PDF nach und "
    "zeigt den Messbericht. Den Text schreibst du mit ChatGPT, die Form übernimmt "
    "falzmarke. Alles läuft in der Sandbox von ChatGPT; es gibt keinen Server und "
    "kein Konto bei uns.\n\n"
    "Die Sollwerte stammen aus Sekundärquellen; der Abgleich mit dem Originaltext "
    "der DIN 5008:2020-03 einschließlich Berichtigung 1:2020-07 steht aus, und "
    "Regeln aus einzelnen Quellen wirken nur als Warnung. Open Source, MIT-Lizenz."
)
#: Beide mit Beispielprofil: Sie laufen ohne eigenes Absenderprofil durch.
STARTPROMPTS = [
    ("Schreib mit falzmarke eine Kündigung an die Muster GmbH, Musterstraße 1, "
     "12345 Musterstadt. Nutze das Beispielprofil."),
    ("Schreib eine E-Mail an kunde@example.de: Der Termin am 3. Oktober verschiebt "
     "sich auf 14 Uhr. Nutze das Beispielprofil."),
]


class Abbruch(Exception):
    """Das Paket würde bei OpenAI zurückgewiesen."""


def projekt(pyproject: Path = REPO / "pyproject.toml") -> dict:
    return tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]


def skill_kopf(skill: Path) -> dict:
    text = (skill / "SKILL.md").read_text(encoding="utf-8")
    teile = text.split("---", 2)
    if len(teile) < 3 or teile[0].strip():
        raise Abbruch(f"{skill / 'SKILL.md'} hat keinen Frontmatter-Kopf.")
    return yaml.safe_load(teile[1])


def manifest(proj: dict) -> dict:
    return {
        "$schema": SCHEMA,
        "name": proj["name"],
        "version": proj["version"],
        "description": proj["description"],
        "homepage": WEBSITE,
        "repository": REPOSITORY,
        "license": "MIT",
        # author.name und developerName müssen gleich sein, sonst ersetzt das
        # Portal beide durch die geprüfte Identität (developer_name_defaulted).
        "author": {"name": proj["authors"][0]["name"]},
        "extensions": {
            "com.openai": {
                "interface": {
                    "displayName": "falzmarke",
                    "shortDescription": KURZBESCHREIBUNG,
                    "longDescription": LANGBESCHREIBUNG,
                    "developerName": proj["authors"][0]["name"],
                    "category": "Productivity",
                    "websiteURL": WEBSITE,
                    "privacyPolicyURL": DATENSCHUTZ,
                    "defaultPrompt": STARTPROMPTS,
                }
            }
        },
    }


def listing_fehler(oberflaeche: dict) -> list[str]:
    """Die Regeln der Einreichung für die Angaben im Verzeichnis."""
    fehler = []
    for feld, grenze in (("displayName", MAX_ANZEIGENAME),
                         ("shortDescription", MAX_KURZBESCHREIBUNG),
                         ("longDescription", MAX_LANGBESCHREIBUNG)):
        wert = oberflaeche.get(feld) or ""
        if not wert:
            fehler.append(f"{feld} fehlt, ist aber Pflicht.")
        elif len(wert) > grenze:
            fehler.append(f"{feld} hat {len(wert)} Zeichen, erlaubt sind {grenze}.")
    prompts = oberflaeche.get("defaultPrompt") or []
    if len(prompts) > MAX_STARTPROMPTS:
        fehler.append(f"{len(prompts)} Startprompts, erlaubt sind {MAX_STARTPROMPTS}.")
    for prompt in prompts:
        if len(prompt) > MAX_STARTPROMPT or "\n" in prompt:
            fehler.append(f"Startprompt mit {len(prompt)} Zeichen, erlaubt ist eine "
                          f"Zeile bis {MAX_STARTPROMPT}: {prompt[:40]!r} …")
    return fehler


def pruefe_vorher(skill: Path, mani: dict) -> None:
    """Alles, was sich vor dem Packen feststellen lässt."""
    fehler = []
    if not NAME_MUSTER.match(mani["name"]) or len(mani["name"]) > 64:
        fehler.append(f"Plugin-Name {mani['name']!r} passt nicht zum Schema.")
    fehler += listing_fehler(mani["extensions"]["com.openai"]["interface"])
    kopf = skill_kopf(skill)
    beschreibung = kopf.get("description") or ""
    if len(beschreibung) > MAX_DESCRIPTION:
        fehler.append(f"SKILL.md: description hat {len(beschreibung)} Zeichen, "
                      f"erlaubt sind {MAX_DESCRIPTION}.")
    qualifiziert = f"{mani['name']}:{kopf.get('name', '')}"
    if len(qualifiziert) > MAX_QUALIFIZIERT:
        fehler.append(f"{qualifiziert!r} ist länger als {MAX_QUALIFIZIERT} Zeichen.")
    links = [p for p in skill.rglob("*") if p.is_symlink()]
    if links:
        fehler.append(f"Symlinks ignoriert OpenAI, hier liegen {len(links)}: "
                      f"{links[0].relative_to(skill)} …")
    if not list((skill / "vendor").glob("*.whl")):
        fehler.append("Kein Wheel in vendor/ — ohne PyPI käme der Renderer nie zustande.")
    if fehler:
        raise Abbruch("\n".join(fehler))


def packe(skill: Path, ziel: Path, mani: dict) -> None:
    dateien = sorted(p for p in skill.rglob("*") if p.is_file())
    eintraege = len(dateien) + 1
    if eintraege > MAX_EINTRAEGE:
        raise Abbruch(f"{eintraege} Einträge, erlaubt sind {MAX_EINTRAEGE}.")
    wurzel = Path("skills") / skill_kopf(skill)["name"]
    with zipfile.ZipFile(ziel, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("plugin.json", json.dumps(mani, ensure_ascii=False, indent=2) + "\n")
        for datei in dateien:
            pfad = wurzel / datei.relative_to(skill)
            if len(pfad.parts) > MAX_PFADSEGMENTE:
                raise Abbruch(f"{pfad.as_posix()} hat mehr als {MAX_PFADSEGMENTE} Pfadsegmente.")
            z.write(datei, pfad.as_posix())
    groesse = ziel.stat().st_size
    if groesse > MAX_ZIP_BYTES:
        ziel.unlink()
        raise Abbruch(f"{ziel.name} ist {groesse} Bytes groß, erlaubt sind {MAX_ZIP_BYTES}.")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Aufruf: plugin_packen.py <skill-ordner> <ziel.zip>", file=sys.stderr)
        return 2
    skill, ziel = Path(argv[0]), Path(argv[1])
    mani = manifest(projekt())
    try:
        pruefe_vorher(skill, mani)
        packe(skill, ziel, mani)
    except Abbruch as grund:
        print(f"FEHL: {grund}", file=sys.stderr)
        print("      OpenAI würde dieses Plugin zurückweisen; es wird nicht gebaut.",
              file=sys.stderr)
        return 1
    print(f"    OK  {ziel.name}: {ziel.stat().st_size} Bytes, Version {mani['version']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
