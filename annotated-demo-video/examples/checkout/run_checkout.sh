#!/usr/bin/env bash
# Records the before/after checkout bug demo and builds every output.
# Expect 7 frames, checkout-bug.mp4, checkout-bug.html and sheet.png in ${1:-/tmp/wt-checkout}.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; OUT="${1:-/tmp/wt-checkout}"
python3 -m http.server 8766 --bind 127.0.0.1 --directory "$HERE" >/dev/null 2>&1 & SERVER=$!
trap 'kill $SERVER' EXIT
for _ in $(seq 50); do curl -sf http://127.0.0.1:8766/checkout.html >/dev/null && break; sleep 0.1; done
node "$HERE/../../scripts/record.cjs" "$HERE/storyboard.json" --out "$OUT"
python3 "$HERE/../../scripts/finish.py" "$OUT" --name checkout-bug --crf 26
