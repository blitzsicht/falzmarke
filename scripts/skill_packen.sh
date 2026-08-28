#!/usr/bin/env bash
# Baut falzmarke.skill — dieselbe Datei, die das Release als Anhang traegt.
#
# Anlass (Issue #122): Das Paket enthielt nur Quelltext. In einer Sandbox ohne
# PyPI-Zugriff — und das sind die Umgebungen, in denen ein Skill laeuft — kam
# der Renderer nie zustande, weil `typst` fehlte und nicht nachladbar war.
# Seitdem reist das typst-Wheel im Paket mit; scripts/bootstrap.py installiert
# zuerst daraus.
#
# Dieses Skript wird von BEIDEN Seiten aufgerufen:
#   .github/workflows/release.yml  beim Bau des Release-Anhangs
#   lokal, vor einem Release:      bash scripts/skill_packen.sh
#
# Deshalb ein Skript und keine zwei Schrittlisten — dieselbe Begruendung wie bei
# scripts/paket_pruefen.sh. tests/test_skillpaket.py haelt fest, dass der
# Workflow es aufruft.
#
# Ergebnis: ./falzmarke.skill im Wurzelverzeichnis des Repos.

set -euo pipefail

cd "$(dirname "$0")/.."

# Das Wheel gilt fuer jedes Python ab 3.8 (cp38-abi3) und fuer die Plattform,
# auf der Skill-Sandboxen laufen. Eine Datei statt einer je Python-Fassung.
PLATTFORM="manylinux_2_17_x86_64"
PYTHON_FASSUNG="3.8"

# Die Fassung steht in skill/requirements.txt und wird von dort gelesen, nicht
# hier wiederholt. Zwei Stellen laufen auseinander, eine nicht.
TYPST_REQ="$(grep -E '^typst' skill/requirements.txt)"
echo "── Vendor-Wheel: $TYPST_REQ ──────────────────────────────────────────"

rm -rf paket falzmarke.skill
mkdir -p paket

# claude.ai erwartet den Skill-Ordner mit SKILL.md an der Wurzel des Zips.
cp -r skill paket/falzmarke
rm -rf paket/falzmarke/typst/profiles.local
rm -rf paket/falzmarke/falzmarke.egg-info
find paket/falzmarke -name '__pycache__' -type d -prune -exec rm -rf {} +

python3 -m pip download \
  --only-binary=:all: \
  --no-deps \
  --platform "$PLATTFORM" \
  --python-version "$PYTHON_FASSUNG" \
  --implementation cp \
  --abi abi3 \
  --dest paket/falzmarke/vendor \
  "$TYPST_REQ"

echo
echo "── Was im vendor/ liegt ──────────────────────────────────────────────"
ls -lh paket/falzmarke/vendor/

# Ein leeres vendor/ waere genau der Zustand vor #122 — und er saehe von aussen
# aus wie ein gelungener Lauf. Deshalb hier abbrechen und nicht spaeter.
if ! ls paket/falzmarke/vendor/*.whl >/dev/null 2>&1; then
  echo "FEHL: kein Wheel in vendor/ — das Paket waere ohne Netz unbrauchbar." >&2
  exit 1
fi

cd paket && zip -rq ../falzmarke.skill falzmarke && cd ..

echo
echo "── Ergebnis ──────────────────────────────────────────────────────────"
unzip -l falzmarke.skill | head -5
echo "…"
unzip -l falzmarke.skill | grep -E 'vendor/.*\.whl'
echo
echo "Groesse: $(du -h falzmarke.skill | cut -f1)"
