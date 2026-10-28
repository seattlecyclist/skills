#!/usr/bin/env bash
# Makes the example film end to end: capture the app, check stills, voice it (when a TTS key is set),
# render both cuts, mix. `./run.sh stills` stops after the contact sheets. FPS=24 ./run.sh for a quick draft.
set -euo pipefail
cd "$(dirname "$0")"
S=../../scripts
FPS=${FPS:-60}
DURATION=15.5
mkdir -p out

# 1. footage: a screenshot of the real page, plus where the elements we animate over sit
node $S/capture.mjs "file://$PWD/app/index.html" out/app.png --width 1600 --height 1000 \
  --boxes "main,#month,#ask input,#ask button"

# 2. look before you render: one contact sheet per cut
node $S/stills.mjs scene.html --root ../.. --out out/stills --count 8
node $S/stills.mjs scene.html --root ../.. --format v --out out/stills-v --count 8
echo "Check out/stills/sheet.png and out/stills-v/sheet.png"
[ "${1:-}" = stills ] && exit 0

# 3. voice: with a TTS key, one generated file per line; otherwise split the recorded take that ships
#    with the example (an ElevenLabs take; the scene's beat times are fitted to it). Either way the
#    lines are placed at their beats. With neither, the film is made without a voice.
VO=()
if python3 $S/voiceover.py keys >/dev/null; then
  python3 $S/voiceover.py tts lines.txt --out out/vo
  echo "New TTS lines run to different lengths than the take: check where each ends below, then move T in scene.html."
elif [ -f voice/take.mp3 ]; then
  python3 $S/voiceover.py split voice/take.mp3 --lines 4 --script lines.txt --cuts 1.60,5.04,9.12 --out out/vo
fi
if [ -f out/vo/line04.wav ]; then
  python3 $S/voiceover.py place timeline.json --duration $DURATION --out out/vo-track.wav
  VO=(--vo out/vo-track.wav)
else
  echo "No voice: making the film without a voiceover."
fi

# 4. picture and sound, then 5. the mix
for f in h v; do
  node $S/render.mjs scene.html --root ../.. --format $f --fps "$FPS" --out out/film-$f.mp4
  python3 $S/mix.py out/film-$f.mp4 --sfx out/film-$f.sfx.wav ${VO[@]+"${VO[@]}"} --out out/tally-$f.mp4
done
echo "Done: out/tally-h.mp4 (16:9) and out/tally-v.mp4 (9:16)"
