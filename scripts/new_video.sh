#!/bin/bash
# Start a new 33SN0W video from a format's working example + studio scaffolding.
#   bash new_video.sh <format> <short-name> [--art-style <style>] [--duration short|standard|extended] [--title "..."] [--dir <parent>]
#   bash new_video.sh --list
set -eu
SKILL="$(cd "$(dirname "$0")/.." && pwd)"

list_formats() {
  for d in "$SKILL"/styles/*/; do
    b="$(basename "$d")"
    [ "$b" = "_shared" ] && continue
    echo "$b"
  done
}

canon_format() {
  case "$1" in
    tall-tale|tall-tale-3d) echo "tall-tale" ;;
    deep-dive|deep-dive-3d) echo "deep-dive" ;;
    night-file|night-file-3d) echo "night-file" ;;
    inside-out|stick-story|paper-atlas) echo "$1" ;;
    *) echo "$1" ;;
  esac
}

if [ "${1:-}" = "--list" ]; then list_formats; exit 0; fi

PARENT="$HOME/faceless-shorts"
ART_STYLE="default"
DURATION="standard"
TITLE=""
FPS="30"
NO_SAFE_ZONE=""
POS=()

while [ $# -gt 0 ]; do
  case "$1" in
    --dir) PARENT="${2:?}"; shift 2 ;;
    --art-style) ART_STYLE="${2:?}"; shift 2 ;;
    --duration) DURATION="${2:?}"; shift 2 ;;
    --title) TITLE="${2:?}"; shift 2 ;;
    --fps) FPS="${2:?}"; shift 2 ;;
    --no-safe-zone) NO_SAFE_ZONE="--no-safe-zone"; shift ;;
    -*) echo "unknown option $1" >&2; exit 2 ;;
    *) POS+=("$1"); shift ;;
  esac
done

USAGE="usage: new_video.sh <format> <short-name> [--art-style <preset>] [--duration short|standard|extended] [--title <title>] [--dir <parent>]  (formats: $(list_formats | tr '\n' ' '))"
STYLE_RAW="${POS[0]:?$USAGE}"
NAME="${POS[1]:?$USAGE}"
STYLE="$(canon_format "$STYLE_RAW")"
SRC="$SKILL/styles/$STYLE/example"
[ -d "$SRC" ] || { echo "no format '$STYLE_RAW' ($USAGE)" >&2; exit 2; }
DST="$PARENT/$NAME"
[ -e "$DST" ] && { echo "$DST already exists: pick another name" >&2; exit 2; }

mkdir -p "$PARENT"
cp -R "$SRC" "$DST"
mkdir -p "$DST/renders" "$DST/review"
rm -f "$DST/data/narration.wav" "$DST/data/mix.wav"

python3 "$SKILL/scripts/studio.py" scaffold "$DST" \
  --format "$STYLE" \
  --art-style "$ART_STYLE" \
  --duration "$DURATION" \
  ${TITLE:+--title "$TITLE"} \
  --fps "$FPS" \
  $NO_SAFE_ZONE >/dev/null

echo "$DST"
echo "format: $STYLE | artStyle: $ART_STYLE | durationTier: $DURATION"
echo "Read $SKILL/formats/ and $SKILL/art-styles/$ART_STYLE.md (if non-default), then update research.json, characters.json, storyboard.json, script.json, src/shots.js"
