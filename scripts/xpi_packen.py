#!/usr/bin/env python3
"""Packt das Thunderbird-Add-on Entwurfsbrücke als `.xpi` (ADR 0054).

Eine `.xpi` ist ein Zip mit `manifest.json` an der Wurzel. Gepackt wird genau,
was das Manifest braucht, in fester Reihenfolge und mit festem Zeitstempel:
Zweimal gepackt gibt dieselben Bytes. So lässt sich an der Prüfsumme sehen, ob
die installierte Fassung die aus dem Repo ist.

Aufruf:

    python3 scripts/xpi_packen.py [zielordner]

Ohne Zielordner landet die Datei in `dist/`. Die Fassung im Dateinamen kommt
aus dem Manifest — eine Stelle, nicht zwei. Dasselbe gilt seit #412 für die
Dateiliste: Sie wird am Manifest abgelesen, nicht daneben geführt.
"""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
QUELLE = REPO / "thunderbird" / "entwurfsbruecke"

#: Fester Zeitstempel, damit das Paket reproduzierbar ist (Zip kennt nichts vor 1980).
ZEIT = (1980, 1, 1, 0, 0, 0)


def dateien(manifest: dict) -> tuple[str, ...]:
    """Was in das Paket gehört, abgelesen am Manifest. Die README bleibt draußen:
    Thunderbird liest sie nicht.

    Eine eigene Liste neben `background.scripts` wäre eine zweite Wahrheit. Fiele
    dort ein Eintrag aus, könnte eine Prüfung, die gegen diese Liste vergleicht,
    das nie finden — der Befund aus #412. Die Reihenfolge ist festgelegt, damit
    zweimal Packen dieselben Bytes gibt: erst das Manifest, dann das Schema des
    Experiments, dann die Hintergrundskripte in der Reihenfolge des Manifests
    (ADR 0057), zuletzt das Experiment selbst.
    """
    apis = manifest.get("experiment_apis", {}).values()
    namen = ["manifest.json"]
    namen += [api["schema"] for api in apis]
    namen += manifest.get("background", {}).get("scripts", [])
    namen += [api["parent"]["script"] for api in apis]
    # Dieselbe Datei an zwei Stellen des Manifests ergibt einen Eintrag, nicht zwei.
    return tuple(dict.fromkeys(namen))


def packe(quelle: Path = QUELLE, ziel: Path = REPO / "dist") -> Path:
    manifest = json.loads((quelle / "manifest.json").read_text(encoding="utf-8"))
    namen = dateien(manifest)
    fehlend = [n for n in namen if not (quelle / n).is_file()]
    if fehlend:
        raise SystemExit(f"FEHLER  im Add-on fehlt: {', '.join(fehlend)}")
    ziel.mkdir(parents=True, exist_ok=True)
    paket = ziel / f"entwurfsbruecke-{manifest['version']}.xpi"
    with zipfile.ZipFile(paket, "w", zipfile.ZIP_DEFLATED) as archiv:
        for name in namen:
            eintrag = zipfile.ZipInfo(name, date_time=ZEIT)
            eintrag.compress_type = zipfile.ZIP_DEFLATED
            eintrag.external_attr = 0o644 << 16
            archiv.writestr(eintrag, (quelle / name).read_bytes())
    return paket


if __name__ == "__main__":
    ziel = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "dist"
    print(f"OK  geschrieben: {packe(ziel=ziel)}")
