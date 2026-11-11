#!/bin/bash
# Proves the upgraded 33SN0W studio pipeline (~2-4 min):
# all 6 core formats + art-style overrides + studio.py / qa_check.py / analytics.py.
#   bash selftest.sh              all formats + full checks
#   bash selftest.sh --no-voice   skip Kokoro/Whisper (estimated timing)
set -u
SKILL="$(cd "$(dirname "$0")/.." && pwd)"; PY="$SKILL/scripts/py"
T="$HOME/faceless-shorts/_selftest"; rm -rf "$T"; mkdir -p "$T"; LOG="$T/selftest.log"; : > "$LOG"
VOICE=1; [ "${1:-}" = "--no-voice" ] && VOICE=0
fail=0; note() { printf '%-22s %s\n' "$1" "$2"; }

for d in "$SKILL"/styles/*/; do
  s=$(basename "$d")
  [ "$s" = "_shared" ] && continue
  P="$T/$s"; t1=$(date +%s)
  bash "$SKILL/scripts/new_video.sh" "$s" "$s" --dir "$T" >> "$LOG" 2>&1 || { note "$s" "FAILED to create (see $LOG)"; fail=1; continue; }
  (
    cd "$P" || exit 1; echo "== $s"
    if [ $VOICE = 1 ]; then "$PY" "$SKILL/scripts/voice.py" . && "$PY" "$SKILL/scripts/words.py" . || exit 1
    else "$PY" "$SKILL/scripts/estimate.py" . || exit 1; fi
    node tools/capture.mjs check | tee review/check.txt; grep -q "CHECK OK" review/check.txt || exit 1
    node tools/capture.mjs cues && "$PY" tools/mix.py . || exit 1
    node tools/capture.mjs sheet review/all.jpg 1 8 || exit 1
    node tools/capture.mjs video renders/selftest.mp4 2 6 --draft || exit 1
  ) >> "$LOG" 2>&1
  M="$P/renders/selftest.mp4"
  if [ -f "$M" ]; then
    A=$(ffmpeg -v info -i "$M" -af volumedetect -vn -f null - 2>&1 | awk '/mean_volume/ {printf "%d", $5}')
    if [ "${A:--99}" -gt -50 ]; then note "$s" "ok, $(( $(date +%s) - t1 )) s · sheet: $P/review/all.jpg · clip: $M"; else note "$s" "FAILED: clip is silent ($A dB)"; fail=1; fi
  else note "$s" "FAILED (see $LOG)"; fail=1; fi
done

# Verify studio CLI tools & non-default art style rendering
(
  echo "== studio tools =="
  python3 "$SKILL/scripts/studio.py" recommend --topic "The submarine pressure implosion experiment" --json >/dev/null || exit 1
  python3 "$SKILL/scripts/studio.py" check-originality --topic "Unique test submarine topic" --history-dir "$T" --json >/dev/null || exit 1
  python3 "$SKILL/scripts/studio.py" score --topic "Unique test submarine topic" --json >/dev/null || exit 1
  python3 "$SKILL/scripts/studio.py" check-script "$T/tall-tale" --json >/dev/null || exit 1
  python3 "$SKILL/scripts/studio.py" metadata "$T/tall-tale" >/dev/null || exit 1
  "$PY" "$SKILL/scripts/qa_check.py" "$T/tall-tale" --min-score 40 >/dev/null || exit 1
  python3 "$SKILL/scripts/analytics.py" summary --json >/dev/null || exit 1
  cd "$T/tall-tale" && node tools/capture.mjs check --art-style comic-art --safe-zones | grep -q "CHECK OK" || exit 1
  cd "$T/deep-dive" && node tools/capture.mjs check --art-style glow-sketch | grep -q "CHECK OK" || exit 1
) >> "$LOG" 2>&1 && note "studio-suite" "ok · studio.py + qa_check.py + analytics.py + art-style overrides" || { note "studio-suite" "FAILED (see $LOG)"; fail=1; }

[ $fail = 0 ] && echo "SELFTEST PASSED" || { echo "SELFTEST FAILED. Full log: $LOG"; exit 1; }
