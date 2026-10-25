#!/usr/bin/env python3
"""Packt das Thunderbird-Add-on Entwurfsbrücke als `.xpi` (ADR 0054).

Eine `.xpi` ist ein Zip mit `manifest.json` an der Wurzel. Gepackt wird genau,
was das Manifest braucht, in fester Reihenfolge und mit festem Zeitstempel:
Zweimal gepackt gibt dieselben Bytes. So lässt sich an der Prüfsumme sehen, ob
die installierte Fassung die aus dem Repo ist.

Aufruf:

    python3 scripts/xpi_packen.py [zielordner]

Ohne Zielordner landet die Datei in `dist/`. Die Fassung im Dateinamen kommt
aus dem Manifest — eine Stelle, nicht zwei.
"""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
QUELLE = REPO / "thunderbird" / "entwurfsbruecke"

#: Was in das Paket gehört. Die README bleibt draußen: Thunderbird liest sie nicht.
DATEIEN = ("manifest.json", "schema.json", "zeichennamen.js", "vergleich.js",
           "background.js", "implementation.js")

#: Fester Zeitstempel, damit das Paket reproduzierbar ist (Zip kennt nichts vor 1980).
ZEIT = (1980, 1, 1, 0, 0, 0)


def packe(quelle: Path = QUELLE, ziel: Path = REPO / "dist") -> Path:
    manifest = json.loads((quelle / "manifest.json").read_text(encoding="utf-8"))
    fehlend = [n for n in DATEIEN if not (quelle / n).is_file()]
    if fehlend:
        raise SystemExit(f"FEHLER  im Add-on fehlt: {', '.join(fehlend)}")
    ziel.mkdir(parents=True, exist_ok=True)
    paket = ziel / f"entwurfsbruecke-{manifest['version']}.xpi"
    with zipfile.ZipFile(paket, "w", zipfile.ZIP_DEFLATED) as archiv:
        for name in DATEIEN:
            eintrag = zipfile.ZipInfo(name, date_time=ZEIT)
            eintrag.compress_type = zipfile.ZIP_DEFLATED
            eintrag.external_attr = 0o644 << 16
            archiv.writestr(eintrag, (quelle / name).read_bytes())
    return paket


if __name__ == "__main__":
    ziel = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "dist"
    print(f"OK  geschrieben: {packe(ziel=ziel)}")
