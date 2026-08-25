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


# Das Vorschaubild wird NICHT hier erzeugt. Es kommt aus der Markenwerkstatt
# (docs/marke/quelle/social-preview.html) und liegt fertig unter
# docs/assets/brand/social-preview.png (1280x640) und hero.png (2560x1280).
# Wer es ändert, ändert die HTML-Quelle — nicht das PNG.
