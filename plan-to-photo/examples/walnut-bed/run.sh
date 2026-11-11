#!/usr/bin/env bash
# Rebuild and render the walnut bed example.
#   ./run.sh [workdir] [--preview]
# Needs Node 18+, Blender 4.2+ on PATH (or BLENDER=/path/to/blender), and network access for the
# CC0 assets on first run. Without the assets it still runs, with procedural fallback materials.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; SK="$HERE/../../scripts"
W="${1:-/tmp/walnut-bed-photo}"; shift || true
BL="${BLENDER:-blender}"
mkdir -p "$W"; cp "$HERE"/{scene.json,walnut_bed.py,plan.js} "$W"/
cd "$W"
node "$SK/export_obj.js" plan.js bed.obj
python3 "$SK/fetch_assets.py" assets polyhaven:walnut_veneer_02 polyhaven:white_oak_veneer polyhaven:rough_linen \
  polyhaven:knitted_fleece ambientcg:Carpet016 polyhaven:borghese_gardens || echo "some assets failed; continuing with fallbacks"
"$BL" -b -P "$SK/build_scene.py" -- scene.json
HDRI=(); [ -f assets/hdri/borghese_gardens_4k.exr ] && HDRI=(--hdri assets/hdri/borghese_gardens_4k.exr)
"$BL" -b -P "$SK/render.py" -- scene.blend walnut-bed.png "${HDRI[@]}" \
  --cam 2.45,-1.1,0.95 --target 0.6,1.3,0.5 --focus 1.70,0.45,0.3 --lens 28 --shift-y 0.07 \
  --fstop 5.6 --sun-az 160 --exposure 1.1 --wb 5400 --res 3000x2000 --samples 2048 "$@"
python3 "$SK/review.py" walnut-bed.png
echo "done: $W/walnut-bed.png and walnut-bed-review.png"
