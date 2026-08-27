#!/usr/bin/env bash
# Alles am Paket, was sich OHNE Tag und OHNE Upload pruefen laesst.
#
# Anlass (Issue #76): Die erste Veroeffentlichung auf PyPI brauchte fuenf
# Anlaeufe. Alle fuenf Ursachen sassen VOR dem Upload, vier davon fielen erst
# nach dem manuellen Freigabeklick auf — und jeder Anlauf kostete eine
# Versionsnummer, die niemand je wieder verwenden kann. Ein Tag laesst sich
# nicht verschieben, und das soll auch so bleiben; also muss der Job vorher
# schon einmal gelaufen sein.
#
# Dieses Skript wird von BEIDEN Seiten aufgerufen:
#   .github/workflows/ci.yml       bei jedem Push und Pull Request
#   .github/workflows/release.yml  am Tag, vor dem Upload
#
# Deshalb ein Skript und keine zwei Schrittlisten: Eine Probe, die vom echten
# Job abweichen kann, prueft irgendwann etwas anderes als das, was passiert.
# tests/test_paketprobe.py haelt fest, dass beide Workflows es aufrufen.
#
# Lokal vor einem Release:
#     bash scripts/paket_pruefen.sh
#
# Es baut in einem eigenen venv und fasst die Umgebung des Aufrufers nicht an.

set -euo pipefail

cd "$(dirname "$0")/.."

VENV="$(mktemp -d)/venv"
python3 -m venv "$VENV"
"$VENV/bin/pip" install --quiet --upgrade pip build twine pytest
"$VENV/bin/pip" install --quiet -r skill/requirements.txt

echo "── Paket bauen (Wheel UND sdist) ─────────────────────────────────────"
rm -rf dist
"$VENV/bin/python" -m build
ls -la dist/

echo
echo "── Metadaten ─────────────────────────────────────────────────────────"
# twine check prueft, ob die Langbeschreibung rendert. Dass ihre Links und
# Bilder auch aufloesen, prueft der Test daneben — twine sieht das nicht und
# meldet auch bei kaputten Bildern PASSED.
"$VENV/bin/python" -m twine check dist/*
"$VENV/bin/python" -m pytest tests/test_readme_auf_pypi.py -o addopts="" -q

echo
echo "── In dist/ liegt nur, was hochgeladen werden darf ───────────────────"
# Die Publish-Action laedt dieses Verzeichnis vollstaendig hoch und prueft
# vorher jede Datei darin. An der ersten, die kein Distributions-Format ist,
# bricht sie ab — nach der Freigabe. Lauf 32966455275 (v0.7.2) ist genau
# daran gescheitert, an einer SHA256SUMS-Datei.
FREMD="$(find dist -maxdepth 1 -type f ! -name '*.whl' ! -name '*.tar.gz')"
if [ -n "$FREMD" ]; then
  echo "FEHL: dist/ enthaelt Dateien, die kein Paket sind:"
  echo "$FREMD"
  exit 1
fi
echo "dist/ enthaelt nur Pakete:"
ls -1 dist/

echo
echo "OK  Das Paket haelt alles, was ohne Tag pruefbar ist."
