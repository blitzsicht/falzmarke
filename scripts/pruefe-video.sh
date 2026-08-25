#!/usr/bin/env bash
# Prueft die fertigen Videos, bevor sie ins README oder auf die Website gehen.
#
#   bash scripts/pruefe-video.sh                 # beide Fassungen des Erklaerfilms
#   bash scripts/pruefe-video.sh datei.mp4       # eine bestimmte Datei
#   bash scripts/pruefe-video.sh --gegenprobe    # zeigt, dass die Pruefungen rot werden koennen
#
# Portiert aus customer-blitzsicht/marketing/campaigns/2026-08-bsfz-siegel/_video/
# pruefe-reel.sh. Der Gegenprobe-Modus ist der Grund, warum es dieses Skript in
# dieser Form gibt: eine Pruefung, die nie rot wird, ist kein Nachweis
# (CLAUDE.md, „Messen statt behaupten"). --gegenprobe baut absichtlich kaputte
# Dateien und erwartet, dass jede Pruefung anschlaegt. Schlaegt eine nicht an,
# ist die Pruefung kaputt — nicht das Video gut.
set -uo pipefail
cd "$(dirname "$0")/.."

readonly MAX_BYTES=$((10 * 1024 * 1024))   # README-tauglich
readonly SOLL_FPS=30

rot=0
ok()   { echo "  [ok]   $*"; }
fehl() { echo "  [FEHL] $*"; rot=$((rot + 1)); }

# <datei> <soll-breite> <soll-hoehe> <soll-sekunden|"">
pruefe() {
  local datei="$1" sollB="$2" sollH="$3" sollSek="${4:-}"
  echo "== $datei"
  if [ ! -f "$datei" ]; then fehl "Datei fehlt"; return; fi

  local probe='ffprobe -v error'
  # `-of csv=p=0` haengt ein Trennzeichen an und liefert "1080," statt "1080";
  # der Vergleich schlaegt dann immer fehl. `default=nw=1:nk=1` gibt den nackten Wert.
  local breite hoehe codec pixfmt dauer
  breite=$($probe -select_streams v:0 -show_entries stream=width      -of default=nw=1:nk=1 "$datei" 2>/dev/null)
  hoehe=$( $probe -select_streams v:0 -show_entries stream=height     -of default=nw=1:nk=1 "$datei" 2>/dev/null)
  codec=$( $probe -select_streams v:0 -show_entries stream=codec_name -of default=nw=1:nk=1 "$datei" 2>/dev/null)
  pixfmt=$($probe -select_streams v:0 -show_entries stream=pix_fmt    -of default=nw=1:nk=1 "$datei" 2>/dev/null)
  dauer=$( $probe -show_entries format=duration -of default=nw=1:nk=1 "$datei" 2>/dev/null)

  if [ -z "$breite" ]; then fehl "kein lesbarer Videostrom"; return; fi

  [ "$breite" = "$sollB" ] && [ "$hoehe" = "$sollH" ] \
    && ok "Masse ${breite}x${hoehe}" \
    || fehl "Masse ${breite}x${hoehe}, erwartet ${sollB}x${sollH}"

  [ "$codec" = "h264" ] && ok "Codec h264" || fehl "Codec $codec, erwartet h264"

  case "$pixfmt" in
    yuv420p)  ok "Pixelformat yuv420p" ;;
    # Remotion schreibt bei JPEG-Zwischenbildern yuvj420p. Spielt ueberall,
    # deshalb akzeptiert statt bemaengelt.
    yuvj420p) ok "Pixelformat yuvj420p (Remotion-Standard, akzeptiert)" ;;
    *)        fehl "Pixelformat $pixfmt" ;;
  esac

  if [ -n "$sollSek" ]; then
    awk -v ist="$dauer" -v soll="$sollSek" 'BEGIN{exit !(ist>soll-0.5 && ist<soll+0.5)}' \
      && ok "Dauer ${dauer}s" \
      || fehl "Dauer ${dauer}s, erwartet ~${sollSek}s"
  fi

  local bytes; bytes=$(stat -f%z "$datei" 2>/dev/null || stat -c%s "$datei")
  [ "$bytes" -le "$MAX_BYTES" ] \
    && ok "Groesse $((bytes / 1024)) KB" \
    || fehl "Groesse $((bytes / 1024)) KB ueber $((MAX_BYTES / 1024)) KB"

  # Ein Standbild aus der Mitte: faengt Dateien, die zwar Metadaten haben,
  # aber keinen dekodierbaren Inhalt.
  local mitte tmp; tmp="$(mktemp -t frame).png"
  mitte=$(awk -v d="$dauer" 'BEGIN{printf "%.1f", d/2}')
  if ffmpeg -v error -ss "$mitte" -i "$datei" -frames:v 1 -y "$tmp" 2>/dev/null && [ -s "$tmp" ]; then
    ok "Bild bei ${mitte}s dekodierbar"
  else
    fehl "kein Bild bei ${mitte}s"
  fi
  rm -f "$tmp"
}

if [ "${1:-}" = "--gegenprobe" ]; then
  echo "GEGENPROBE — jede dieser Dateien MUSS Pruefungen rot machen."
  tmp="$(mktemp -d)"
  # 1. falsche Masse, falsches Pixelformat, falsche Dauer
  ffmpeg -v error -f lavfi -i testsrc=size=640x480:rate=30:duration=2 \
    -pix_fmt yuv444p -c:v libx264 -y "$tmp/falsch.mp4" 2>/dev/null
  # 2. gar kein Video
  echo "kein Video" > "$tmp/leer.mp4"
  pruefe "$tmp/falsch.mp4" 1920 1080 60
  pruefe "$tmp/leer.mp4"   1920 1080 60
  pruefe "$tmp/gibtesnicht.mp4" 1920 1080 60
  rm -rf "$tmp"
  if [ "$rot" -ge 3 ]; then
    echo "GEGENPROBE BESTANDEN — $rot Pruefungen sind rot geworden."
    exit 0
  fi
  echo "GEGENPROBE GESCHEITERT — nur $rot Pruefungen rot. Das Skript misst nicht." >&2
  exit 1
fi

if [ "$#" -gt 0 ]; then
  pruefe "$1" "${2:-1920}" "${3:-1080}" "${4:-}"
else
  pruefe docs/renders/erklaerfilm-16x9.mp4 1920 1080 60
  pruefe docs/renders/erklaerfilm-9x16.mp4 1080 1920 60
fi

echo
if [ "$rot" -eq 0 ]; then echo "Alles in Ordnung."; exit 0; fi
echo "$rot Pruefung(en) rot." >&2
exit 1
