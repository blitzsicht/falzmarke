#!/usr/bin/env bash
# Erzeugt die Bilder der README aus den frischen Renders in docs/renders/.
#
# Anlass: hero.png und die drei gallery-Bilder lagen als PNG im Repo, ohne dass
# irgendwo stand, wie sie entstanden sind. Nach jeder Aenderung am Beispielbrief
# oder am Beispielprofil waren sie still veraltet.
#
#   bash scripts/demobilder.sh
#
# Voraussetzung: ImageMagick (magick). Die Renders erzeugt die CI ohnehin:
#   python3 skill/scripts/falzmarke.py preview examples/<name>.md \
#     -o docs/renders/<name>.png --ppi 110
set -euo pipefail
cd "$(dirname "$0")/.."

command -v magick >/dev/null || { echo "magick fehlt (brew install imagemagick)"; exit 1; }

RENDERS=docs/renders
DEMO=docs/assets/demo
mkdir -p "$DEMO"

# Ausschnitt: obere Briefhaelfte, gemessen am 110-ppi-Render (909x1286).
# hero laeuft bis kurz unter die Anrede, die Galerie bis in den Fliesstext.
ausschnitt() {   # <quelle> <ziel> <hoehe-im-original> <zielbreite>
  local quelle="$1" ziel="$2" hoehe="$3" breite="$4"
  [ -f "$quelle" ] || { echo "fehlt: $quelle — erst die Renders erzeugen"; exit 1; }
  magick "$quelle" -crop "909x${hoehe}+0+0" +repage -resize "${breite}x" -strip "$ziel"
  printf '  %-46s %s\n' "$ziel" "$(magick "$ziel" -format '%wx%h' info:)"
}

ausschnitt "$RENDERS/brief-form-b.png"        "$DEMO/hero.png"                 510 1241
ausschnitt "$RENDERS/brief-form-b.png"        "$DEMO/gallery-standard.png"     649  827
ausschnitt "$RENDERS/brief-einschreiben.png"  "$DEMO/gallery-einschreiben.png" 649  827
ausschnitt "$RENDERS/brief-mehrseitig-2.png"  "$DEMO/gallery-mehrseitig.png"   649  827

# Das GitHub-Social-Preview. Die SVG-Quelle verweist relativ auf das Briefbild;
# rsvg-convert laedt aus Sicherheitsgruenden keine externen Dateien, deshalb
# wird zum Rendern eine Fassung mit eingebettetem Bild gebaut und wieder
# verworfen. Die Quelle im Repo bleibt lesbar.
echo
command -v rsvg-convert >/dev/null || { echo "rsvg-convert fehlt (brew install librsvg) — social-preview uebersprungen"; exit 0; }
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
magick "$RENDERS/brief-form-b.png" -resize 800x -strip "$tmp/brief.png"
python3 - "$tmp" <<'PY'
import base64, pathlib, sys
tmp = pathlib.Path(sys.argv[1])
b64 = base64.b64encode((tmp / "brief.png").read_bytes()).decode()
quelle = pathlib.Path("docs/assets/brand/social-preview.svg")
text = quelle.read_text(encoding="utf-8")
alt = 'xlink:href="../../renders/brief-form-b.png"'
assert alt in text, "Verweis auf das Briefbild nicht gefunden"
(tmp / "preview.svg").write_text(
    text.replace(alt, f'xlink:href="data:image/png;base64,{b64}"'), encoding="utf-8")
PY
rsvg-convert -w 1280 -h 640 -o docs/assets/brand/social-preview.png "$tmp/preview.svg"
printf '  %-46s %s\n' "docs/assets/brand/social-preview.png" "$(magick docs/assets/brand/social-preview.png -format '%wx%h' info:)"
