#!/usr/bin/env bash
# Legt die Module, die der Referenzdienst braucht, neben den Vercel-Einstieg.
#
# Warum: Die Vercel-CLI lädt nur das Projektverzeichnis hoch (mcp-dienst/).
# `../skill` wäre dort nicht vorhanden, und der Dienst fände sein Paket nicht.
#
# Kopiert wird genau, was der Dienst zur Laufzeit lädt — gemessen am 29.09.2026
# in einem frischen Interpreter: falzmarke, geometrie, regeln, referenzdienst.
# tests/test_referenzdienst.py prüft, dass der gepackte Stand für sich allein
# läuft; fehlt hier etwas, wird er dort rot.
#
#   bash mcp-dienst/packen.sh            nach mcp-dienst/_skill
#   bash mcp-dienst/packen.sh <ziel>     woandershin (für Tests)
set -euo pipefail

cd "$(dirname "$0")/.."
ZIEL="${1:-mcp-dienst/_skill}"
QUELLE="skill/falzmarke"

rm -rf "$ZIEL"
mkdir -p "$ZIEL/falzmarke/regeln"
cp "$QUELLE/__init__.py" "$QUELLE/geometrie.py" "$QUELLE/referenzdienst.py" "$ZIEL/falzmarke/"
cp "$QUELLE"/regeln/*.py "$QUELLE"/regeln/*.yaml "$ZIEL/falzmarke/regeln/"

echo "OK  $(find "$ZIEL" -type f | wc -l | tr -d ' ') Dateien nach $ZIEL"
