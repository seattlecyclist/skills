#!/usr/bin/env bash
# The walnut bed as a photo from Nano Banana instead of Blender: model.json -> OBJ -> line drawing -> photo.
#   GEMINI_API_KEY=... ./run_nano_banana.sh [workdir] [takes]
# Needs Node 18+, Python 3 with numpy and Pillow, and network access to generativelanguage.googleapis.com.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; SK="$HERE/../../scripts"
W="${1:-/tmp/walnut-bed-nano-banana}"; TAKES="${2:-2}"
mkdir -p "$W"; cd "$W"
node "$SK/build_model.js" "$HERE/model.json" bed.obj --takeoff "$HERE/takeoff.json"
python3 "$SK/line_drawing.py" bed.obj bed-lines.jpg --cam=-1.35,-1.75,1.45 --target=0.85,1.05,0.42 --fov 50
python3 "$SK/nano_banana.py" bed-lines.jpg "$HERE/nano_banana_spec.md" "$HERE/nano_banana_room.md" walnut-bed-nb.jpg --takes "$TAKES"
echo "done: $W"
