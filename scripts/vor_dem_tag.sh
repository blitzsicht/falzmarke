#!/usr/bin/env bash
# Vor jedem Release-Tag, lokal — die eine Stelle, an der Paket UND Repo-Zustand
# gemessen werden (#211).
#
# paket_pruefen.sh prüft das Paket; es läuft auch in der CI. Der Drift-Wächter
# (repo_pruefung.py) braucht Admin-Leserechte, die der GITHUB_TOKEN nicht hat,
# und ein Token mit diesem Recht gehört nicht in die Secrets eines öffentlichen
# Repositories (Entscheidung in #211). Also läuft er hier, mit den gh-Rechten
# des Maintainers, an der Stelle, die vor jedem Release ohnehin durchlaufen wird.
#
# Exit 2 des Wächters (ein Wert nicht abfragbar) zählt als Fehlschlag: Nicht
# geprüft ist nicht grün.
#
#     bash scripts/vor_dem_tag.sh

set -euo pipefail
cd "$(dirname "$0")/.."

bash scripts/paket_pruefen.sh

echo
echo "── Repo-Zustand gegen die Sollwerte (Drift-Wächter) ──────────────────"
set +e
python3 scripts/repo_pruefung.py --repo blitzsicht/falzmarke
code=$?
set -e
case "$code" in
  0) echo "OK  Paket und Repo-Zustand halten die Sollwerte. Der Tag kann gesetzt werden." ;;
  2) echo "FEHL: Mindestens ein Wert war nicht abfragbar — nicht geprüft ist nicht grün."; exit 2 ;;
  *) echo "FEHL: Der Repo-Zustand weicht vom Soll ab (siehe oben). Erst klären, dann taggen."; exit 1 ;;
esac
