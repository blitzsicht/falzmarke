#!/usr/bin/env bash
# Erzeugt die Markenbilder aus docs/marke/quelle/social-preview.html.
#
#   bash scripts/marke.sh            # banner.png und social-preview.png
#   bash scripts/marke.sh --verify   # zusaetzlich zweimal rendern und vergleichen
#
# Anlass: Die HTML-Quelle zeigte bis zum 25.08.2026 auf /tmp/sp/ und
# /home/claude/fz/ — eine fremde Sandbox. Das Bild lag als PNG im Repo, ohne dass
# es hier jemand haette neu bauen koennen. Wer die Aussage aendern will, aendert
# jetzt die HTML und laesst dieses Skript laufen.
#
# Die Pruefungen stammen aus customer-blitzsicht/marketing/render.sh. Sie sind
# dort aus echten Fehlschlaegen entstanden und hier uebernommen, nicht erfunden.
set -euo pipefail
cd "$(dirname "$0")/.."

readonly CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
readonly QUELLE="docs/marke/quelle/social-preview.html"
readonly ZIEL="docs/assets/brand"

[ -x "$CHROME" ] || { echo "FEHLER: Google Chrome nicht gefunden unter $CHROME" >&2; exit 3; }
[ -f "$QUELLE" ] || { echo "FEHLER: $QUELLE fehlt" >&2; exit 1; }

# Ein PNG ist erst vollstaendig, wenn der IEND-Chunk dasteht: Laenge 00000000,
# Typ "IEND" (49454e44), CRC (ae426082). Die Dateigroesse allein ist KEIN
# Fertigkriterium — in customer-blitzsicht hat Chrome unter Last einmal
# ausgeloest, bevor die per file:// geladenen SVGs da waren: 116 KB statt 144 KB,
# und die Groessenpruefung war zufrieden.
# Ob die Schriften wirklich geladen wurden, verraet die Dateigroesse NICHT:
# Ein Gegentest mit absichtlich totem Montserrat-Pfad ergab 56087 statt 56120
# Byte — 33 Byte Unterschied bei sichtbar anderer Schrift und anderem Umbruch.
# Wer hier vergleichen will, vergleicht Bilder, nicht Byte-Zahlen.
png_vollstaendig() {
  [ -s "$1" ] && [ "$(tail -c 12 "$1" | xxd -p | tr -d '\n')" = "0000000049454e44ae426082" ]
}

# Rendert die Quelle in ein PNG. <ziel> <breite> <hoehe> <skalierung>
#
# Chrome laeuft im Hintergrund und wird von uns beendet, sobald die Datei
# vollstaendig und ihre Groesse ueber zwei Sekunden stabil ist. --headless=new
# kehrt nach --screenshot nicht zuverlaessig von selbst zurueck; ein Vordergrund-
# aufruf haengt dann bis zum Timeout, obwohl das Bild laengst geschrieben ist.
rendere() {
  local ziel="$1" breite="$2" hoehe="$3" skala="$4"
  local profil pid wartezeit=0 g1 g2
  profil="$(mktemp -d)"
  rm -f "$ziel"

  # Kein --allow-file-access-from-files: hier gemessen am 25.08.2026, dass es
  # nichts aendert — mit und ohne Flag ist die Ausgabe bytegleich. Chrome laedt
  # @font-face-Dateien neben der HTML auch so. (customer-blitzsicht/marketing/
  # _fonts.css haelt das Flag fuer noetig und bettet die Schriften deshalb als
  # base64 ein; fuer diese Verzeichnislage trifft das nicht zu.)
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars \
    --force-device-scale-factor="$skala" \
    --window-size="$breite,$hoehe" \
    --user-data-dir="$profil" \
    --virtual-time-budget=10000 \
    --screenshot="$ziel" "file://$PWD/$QUELLE" >/dev/null 2>&1 &
  pid=$!

  while [ "$wartezeit" -lt 60 ]; do
    if png_vollstaendig "$ziel"; then
      g1="$(stat -f%z "$ziel")"; sleep 2; g2="$(stat -f%z "$ziel")"
      [ "$g1" = "$g2" ] && png_vollstaendig "$ziel" && break
    fi
    sleep 1
    # NICHT (( wartezeit++ )) — liefert bei 0 den Exit-Status 1 und bricht unter
    # `set -e` das ganze Skript ab.
    wartezeit=$(( wartezeit + 1 ))
  done

  kill "$pid" 2>/dev/null || true
  wait "$pid" 2>/dev/null || true
  rm -rf "$profil"

  png_vollstaendig "$ziel" || { echo "FEHLER: $ziel unvollstaendig (kein IEND)" >&2; return 2; }

  # Gegenprobe der Masse: ein Renderer, der still die falsche Groesse liefert, ist
  # schlimmer als einer, der abbricht.
  local ist soll="$((breite * skala))x$((hoehe * skala))"
  ist="$(sips -g pixelWidth -g pixelHeight "$ziel" | awk '/pixelWidth/{w=$2} /pixelHeight/{h=$2} END{print w"x"h}')"
  [ "$ist" = "$soll" ] || { echo "FEHLER: $ziel ist $ist, erwartet $soll" >&2; return 2; }
  printf '  %-42s %s  %s KB\n' "$ziel" "$ist" "$(( $(stat -f%z "$ziel") / 1024 ))"
}

mkdir -p "$ZIEL"
echo "Markenbilder aus $QUELLE:"
rendere "$ZIEL/banner.png"          1280 640 2   # README-Kopf, 2560x1280
rendere "$ZIEL/social-preview.png"  1280 640 1   # GitHub-Vorschau, 1280x640

if [ "${1:-}" = "--verify" ]; then
  echo "Gegenprobe: zweimal rendern muss dieselbe Datei ergeben."
  tmp="$(mktemp -d)"; fehler=0
  for datei in banner social-preview; do
    case "$datei" in banner) s=2 ;; *) s=1 ;; esac
    rendere "$tmp/$datei.png" 1280 640 "$s" >/dev/null
    if [ "$(shasum -a 256 <"$ZIEL/$datei.png" | cut -d' ' -f1)" \
       = "$(shasum -a 256 <"$tmp/$datei.png"  | cut -d' ' -f1)" ]; then
      echo "  OK   $datei.png reproduzierbar"
    else
      echo "  FEHL $datei.png weicht zwischen zwei Laeufen ab" >&2; fehler=1
    fi
  done
  rm -rf "$tmp"
  [ "$fehler" -eq 0 ] || exit 2
fi
