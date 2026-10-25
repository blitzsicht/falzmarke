#!/usr/bin/env python3
"""Schreibt das Update-Manifest der Entwurfsbrücke (`updates.json`).

Thunderbird fragt die Adresse aus `update_url` im Manifest regelmäßig ab. Sie
zeigt auf `releases/latest/download/updates.json`, also auf den Anhang des
jüngsten Releases. Darum muss jedes Release diese Datei tragen: Fehlt sie
einmal, findet keine installierte Brücke mehr ein Update.

Alles kommt aus der gepackten `.xpi`, nicht aus dem Quellordner: Fassung,
Mindestversion und Prüfsumme gehören zu genau der Datei, die am Release hängt.

Aufruf:

    python3 scripts/xpi_updates.py <xpi> <tag> [ziel]

Ohne Ziel landet `updates.json` neben der `.xpi`.
"""

from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path

REPO_URL = "https://github.com/blitzsicht/falzmarke"

#: Steht so in `manifest.json` unter `browser_specific_settings.gecko.update_url`.
UPDATE_URL = f"{REPO_URL}/releases/latest/download/updates.json"


def updates(xpi: Path, tag: str) -> dict:
    with zipfile.ZipFile(xpi) as archiv:
        manifest = json.loads(archiv.read("manifest.json").decode("utf-8"))
    gecko = manifest["browser_specific_settings"]["gecko"]
    eintrag = {
        "version": manifest["version"],
        "update_link": f"{REPO_URL}/releases/download/{tag}/{xpi.name}",
        # Bei https verlangt Thunderbird keinen Hash. Er steht trotzdem da: So
        # installiert es nur genau die Datei, die der Release-Lauf gebaut hat.
        "update_hash": "sha256:" + hashlib.sha256(xpi.read_bytes()).hexdigest(),
    }
    if "strict_min_version" in gecko:
        eintrag["applications"] = {"gecko": {"strict_min_version": gecko["strict_min_version"]}}
    return {"addons": {gecko["id"]: {"updates": [eintrag]}}}


def schreibe(xpi: Path, tag: str, ziel: Path | None = None) -> Path:
    ziel = ziel or xpi.parent / "updates.json"
    ziel.write_text(json.dumps(updates(xpi, tag), indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    return ziel


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        raise SystemExit("Aufruf: python3 scripts/xpi_updates.py <xpi> <tag> [ziel]")
    ziel = Path(sys.argv[3]) if len(sys.argv) == 4 else None
    print(f"OK  geschrieben: {schreibe(Path(sys.argv[1]), sys.argv[2], ziel)}")
