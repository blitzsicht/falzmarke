#!/usr/bin/env bash
# Baut die beiden Skill-Pakete, die das Release als Anhang traegt.
#
# ── Warum zwei ────────────────────────────────────────────────────────────
#
# falzmarke.skill          ~1 MB   ueberall hochladbar, erster Lauf braucht Netz
# falzmarke-offline.skill  ~34 MB  typst reist mit, laeuft ohne PyPI
#
# Anlass (Issue #122, nachgemessen am 28.08.2026): Das Paket enthielt nur
# Quelltext und kam in einer Sandbox ohne PyPI-Zugriff nie zum Rendern.
# Seitdem reist das typst-Wheel mit — und genau das hat das Paket ueber die
# Uploadgrenze von claude.ai gehoben. Gemeldet wird dort woertlich:
#
#     Zip file must be less than 30MB
#
# 34,71 MB gegen 30 MB. Der dokumentierte Hauptweg war damit unbrauchbar, und
# zwar still: Der Fehler erscheint erst beim Hochladen, nicht beim Bauen.
# Deshalb ist die Grenze hier ein Sollwert und keine Fussnote — das Skript
# bricht ab, bevor ein Paket entsteht, das niemand einspielen kann.
#
# Dieses Skript wird von BEIDEN Seiten aufgerufen:
#   .github/workflows/ci.yml       bei jedem Push
#   .github/workflows/release.yml  beim Bau der Release-Anhaenge
#   lokal, vor einem Release:      bash scripts/skill_packen.sh
#
# tests/test_skillpaket.py haelt fest, dass beide Workflows es aufrufen und
# dass der Sollwert nur an dieser einen Stelle steht.

set -euo pipefail

cd "$(dirname "$0")/.."

# ── Sollwert ──────────────────────────────────────────────────────────────
# Die Uploadgrenze von claude.ai, gemessen am 28.08.2026 an der Fehlermeldung
# des Dialogs „Faehigkeit hochladen". Sie gilt fuer .zip UND .skill; die
# Endung war nie das Problem.
MAX_MB=30

# Das Wheel gilt fuer jedes Python ab 3.8 (cp38-abi3) und fuer die Plattform,
# auf der Skill-Sandboxen laufen. Eine Datei statt einer je Python-Fassung.
PLATTFORM="manylinux_2_17_x86_64"
PYTHON_FASSUNG="3.8"

# Die Fassung steht in skill/requirements.txt und wird von dort gelesen, nicht
# hier wiederholt. Zwei Stellen laufen auseinander, eine nicht.
TYPST_REQ="$(grep -E '^typst' skill/requirements.txt)"

rm -rf paket falzmarke.skill falzmarke-offline.skill
mkdir -p paket

# claude.ai erwartet den Skill-Ordner mit SKILL.md an der Wurzel des Zips.
cp -r skill paket/falzmarke
rm -rf paket/falzmarke/typst/profiles.local
rm -rf paket/falzmarke/falzmarke.egg-info
find paket/falzmarke -name '__pycache__' -type d -prune -exec rm -rf {} +

echo "── 1. falzmarke.skill — schlank, ueberall hochladbar ─────────────────"
(cd paket && zip -rq ../falzmarke.skill falzmarke)
ls -lh falzmarke.skill | awk '{print "   ", $5}'

# Die Grenze wird hier geprueft und nicht am Ende: Ein Paket, das sich nicht
# einspielen laesst, soll auffallen, bevor 34 MB geladen werden.
BYTES=$(wc -c < falzmarke.skill | tr -d ' ')
GRENZE=$((MAX_MB * 1000 * 1000))
printf "    %s Bytes = %.2f MB (Grenze %d MB)\n" \
  "$BYTES" "$(echo "$BYTES" | awk '{printf "%.2f", $1/1000000}')" "$MAX_MB"
if [ "$BYTES" -ge "$GRENZE" ]; then
  echo "FEHL: falzmarke.skill ist zu gross fuer den Upload nach claude.ai." >&2
  echo "      Dort meldet der Dialog woertlich: Zip file must be less than ${MAX_MB}MB." >&2
  echo "      Ein Paket, das sich nicht einspielen laesst, ist kein Deliverable." >&2
  exit 1
fi
echo "    OK  unter der Grenze."

echo
echo "── 2. falzmarke-offline.skill — mit $TYPST_REQ ───────────────────────"
python3 -m pip download \
  --only-binary=:all: \
  --no-deps \
  --platform "$PLATTFORM" \
  --python-version "$PYTHON_FASSUNG" \
  --implementation cp \
  --abi abi3 \
  --dest paket/falzmarke/vendor \
  "$TYPST_REQ"

# Ein leeres vendor/ waere genau der Zustand vor #122 — und er saehe von aussen
# aus wie ein gelungener Lauf. Deshalb hier abbrechen und nicht spaeter.
if ! ls paket/falzmarke/vendor/*.whl >/dev/null 2>&1; then
  echo "FEHL: kein Wheel in vendor/ — das Paket waere ohne Netz unbrauchbar." >&2
  exit 1
fi
ls -lh paket/falzmarke/vendor/*.whl | awk '{print "   Wheel:", $5}'
(cd paket && zip -rq ../falzmarke-offline.skill falzmarke)
ls -lh falzmarke-offline.skill | awk '{print "   ", $5}'

echo
echo "── Ergebnis ──────────────────────────────────────────────────────────"
for f in falzmarke.skill falzmarke-offline.skill; do
  printf "   %-26s %s\n" "$f" "$(du -h "$f" | cut -f1)"
done
