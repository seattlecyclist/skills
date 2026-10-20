#!/usr/bin/env bash
# Self-test: serves the demo site, records the sample storyboard and builds every output.
# Expect 5 frames, demo.mp4 (~25 s), demo.html and sheet.png in ${1:-/tmp/wt-example}.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; OUT="${1:-/tmp/wt-example}"
python3 -m http.server 8765 --bind 127.0.0.1 --directory "$HERE/demo-site" >/dev/null 2>&1 & SERVER=$!
trap 'kill $SERVER' EXIT
for _ in $(seq 50); do curl -sf http://127.0.0.1:8765/index.html >/dev/null && break; sleep 0.1; done
node "$HERE/../scripts/record.cjs" "$HERE/storyboard.json" --out "$OUT"
python3 "$HERE/../scripts/finish.py" "$OUT" --name demo
