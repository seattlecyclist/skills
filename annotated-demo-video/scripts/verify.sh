#!/usr/bin/env bash
# Verify + finalize a recorded walkthrough/demo.
#   - extracts a contact sheet (eyeball every chapter/overlay — you cannot watch
#     the video directly, so this is how the capture is actually checked)
#   - optionally grabs full-res stills at given timestamps
#   - converts to a compressed, faststart mp4 (what you commit/share)
#
# Usage:
#   verify.sh <webm-or-dir> [name] [<sec>:<label>,...]
#
#   <webm-or-dir>  a .webm file, OR a dir (uses the newest *.webm in it —
#                  recordVideo writes hash-named files, so passing the dir is normal)
#   [name]         output basename (default: walkthrough)
#   [stills]       e.g. 12:index,30:churned  → name_index.png at 12s, etc.
#
# Env: OUT=<dir> output dir (default: dirname of the webm); CRF=28 (higher=smaller).
set -euo pipefail

src="${1:?usage: verify.sh <webm-or-dir> [name] [<sec>:<label>,...]}"
name="${2:-walkthrough}"
stills="${3:-}"

if [ -d "$src" ]; then
  webm="$(ls -t "$src"/*.webm 2>/dev/null | head -1 || true)"
  [ -n "$webm" ] || { echo "✗ no *.webm in $src" >&2; exit 1; }
else
  webm="$src"
fi
[ -f "$webm" ] || { echo "✗ no recording at $webm" >&2; exit 1; }
out="${OUT:-$(dirname "$webm")}"
mkdir -p "$out"

echo "── source: $webm"
echo "── duration ───────────────────────────────────────────"
# || true: a failed probe must fall through to the awk fps fallback below, not
# die here under set -e
dur="$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$webm" || true)"
echo "${dur:-unavailable}"

echo "── contact sheet → $out/${name}_sheet.png ─────────────"
# Spread exactly 24 samples across the whole video so one 4x6 sheet always
# covers it (a fixed fps=1/4 overflows the tile past 96s and image2 refuses a
# second frame without -update). -frames:v 1 -update 1 guards the muxer anyway.
sheet_fps="$(awk -v d="$dur" 'BEGIN { printf "%.6f", (d + 0 > 0) ? 24 / d : 0.25 }')"
ffmpeg -y -loglevel error -i "$webm" -vf "fps=${sheet_fps},scale=440:-1,tile=4x6" \
  -frames:v 1 -update 1 "$out/${name}_sheet.png"
echo "open $out/${name}_sheet.png   # eyeball every chapter/overlay/surface"

if [ -n "$stills" ]; then
  echo "── stills ─────────────────────────────────────────────"
  IFS=',' read -ra pairs <<< "$stills"
  for p in "${pairs[@]}"; do
    sec="${p%%:*}"; label="${p##*:}"
    ffmpeg -y -loglevel error -ss "$sec" -i "$webm" -frames:v 1 -update 1 "$out/${name}_${label}.png"
    echo "  $out/${name}_${label}.png  (t=${sec}s)"
  done
fi

echo "── mp4 (compressed, faststart) → $out/${name}.mp4 ─────"
ffmpeg -y -loglevel error -i "$webm" \
  -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" \
  -c:v libx264 -preset slow -crf "${CRF:-28}" -pix_fmt yuv420p -movflags +faststart "$out/${name}.mp4"
webm_kb=$(( $(wc -c < "$webm") / 1024 )); mp4_kb=$(( $(wc -c < "$out/${name}.mp4") / 1024 ))
echo "✓ $out/${name}.mp4  (${mp4_kb}KB, CRF ${CRF:-28}; from ${webm_kb}KB webm)"
