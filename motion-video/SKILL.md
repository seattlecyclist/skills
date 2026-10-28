---
name: motion-video
description: Make a short promo, teaser, launch or explainer motion video for any product or idea - 3D objects that fly in and get measured, real app screens with typing, captions, a stamp, an end card, synthesized sound effects and music, and a voiceover when a TTS key or connector is available - rendered frame-exact from a browser scene into 16:9 and 9:16 MP4s mixed to -14 LUFS. Triggers on "promo video", "motion video", "launch video", "teaser", "explainer video", "product animation", "social video", "make a video for".
---

# Motion video: a browser scene rendered frame by frame

A film is an HTML page whose picture is a **pure function of time**. `renderAt(t)` puts every object,
camera and caption where it belongs at `t` seconds, reading nothing else: no clock, no `Math.random`, no
state left over from the last frame. Because of that a headless browser can render frame 0, frame 1,
frame 2 … at any speed, every render is identical, any single moment can be checked as a still, and
picture and sound line up to the frame.

```
brief → script and beat sheet → footage capture → scene → stills check → render → voice → sound mix → verify
```

Everything lives in this folder:

| Path | What it is |
|---|---|
| `assets/kit.js` | ES module for scenes: easing, shot lists, fly-in assembly, dimension lines, sprites, captions, browser window, stamp, end card, sound synth, boot contract. |
| `assets/scene.template.html` | Smallest runnable scene. Copy it to start. |
| `scripts/capture.mjs` | Screenshot a real page as footage, with element boxes to animate over. |
| `scripts/stills.mjs` | Render chosen moments plus a labelled contact sheet. |
| `scripts/render.mjs` | Render every frame into an H.264 MP4, and the scene's sound into a WAV. |
| `scripts/voiceover.py` | `keys`, `tts` (ElevenLabs or OpenAI), `split` a single take into lines, `place` lines on the timeline. |
| `scripts/mix.py` | Duck the bed under the voice, two-pass loudness normalize, mux. |
| `examples/budget-teaser/` | A complete 15 s film for a made-up app, with `run.sh` that does every step. |

**Needs:** Node 18+ with Playwright and Chromium, Python 3 (standard library only), ffmpeg. Scenes load
three.js 0.160.0 and fonts from CDNs; for an offline machine `npm i three@0.160.0` and point the
importmap at `node_modules`, and use local `@font-face` files. Self-test: `FPS=12 examples/budget-teaser/run.sh`.

## 1. Brief

Get these from the user, or from what they gave you, before anything else. Ask once, only for what you
cannot find.

- **What it is for**: launch post, landing page loop, ad, investor update, social. This sets the length
  (15 to 30 s for social, up to 60 s for an explainer) and the formats (16:9, 9:16, 1:1).
- **The one idea** the viewer should leave with. A film carries one idea; everything else is a feature list.
- **Real material**: the product URL or screenshots, the brand colours and fonts, the logo or name, the URL
  for the end card. Real screens beat mock-ups: capture them (step 3).
- **Voice**: whether to narrate. With no key or connector, the film is made with captions only, or with
  a take the user records (see step 6).

## 2. Script and beat sheet

Write the voiceover first, one line per beat, then hang the picture off it. A good default for a product:

1. **The ask** (2 to 4 s): the real product, the user typing or clicking the thing it does.
2. **The idea made physical** (4 to 6 s): what the product produces, as objects that assemble on a
   set: bars, parts, pages, cards. Things land one by one on a rhythm.
3. **The proof** (3 to 5 s): measure it. A dimension line that draws itself, a value that rings, a limit
   line. Show the number on screen that the voice says.
4. **The payoff** (1 to 2 s): a stamp, a checkmark, a before and after.
5. **End card** (2 to 3 s): name, three short phrases on cue, the URL.

Keep the timeline in one object (`const T = {...}`) at the top of the scene, and give every beat a start
taken from a voiceover line. When real voice files exist, read their durations from `vo/lines.json`
(written by `voiceover.py tts` or `split`) and move the beats so no line overlaps the next and each
picture event lands on the word that names it. `voiceover.py place` prints where each line ends.

## 3. Footage from the real product

```bash
node scripts/capture.mjs https://app.example.com/dashboard out/app.png --width 1600 --height 1000 --scale 2 \
  --boxes "#search input,#search button,main" [--goto-first "https://app.example.com/sign-in?token=…"] [--cookies c.json]
```

`out/app.json` gets each selector's box in screenshot pixels. The scene draws the screenshot onto a
canvas each frame and paints over those boxes: typed text into an empty field, a button press, a reply
wiping in (see `drawApp` in the example). Then `K.browserWindow` shows that canvas in a plain browser
frame that fades in, pushes in toward `focusX`, and shrinks away.

- Seed the page with realistic data first. Empty states make weak footage.
- One-time sign-in links are consumed by the first visit. Mint a fresh one for each capture, and never
  open it in a probe page first. Do not write tokens or cookies into the repo.
- Capture at `--scale 2` so text stays sharp when the window pushes in.
- Use a still screenshot, not a screen recording: the scene animates over it and stays a pure function of t.

## 4. Build the scene

Copy `assets/scene.template.html` next to your footage, set the import path to `kit.js`, then build beats.
The render contract, which `K.boot` sets up for you:

```
window.scene = { width, height, duration }   window.renderAt(t)   window.renderAudio() → base64 WAV   window.ready = true
```

Principles that make it look made, not generated:

- **Every move eases.** `K.cameraAt` interpolates a shot list with smootherstep, so every move starts and
  ends at rest. Two keys with the same pose hold; slightly different poses drift. Never cut the camera
  mid-move or move linearly.
- **One camera job per beat**: settle on the set while things land, push in on the thing being measured,
  then hold for the payoff. Don't orbit and push at once.
- **Things land, not appear.** `K.assembly` flies parts in from an exploded offset with a small backOut
  overshoot, one after another on a steady interval (0.3 to 0.4 s).
- **Measure, don't decorate.** `K.dimension` draws from the middle out, ticks appear, the label pops in.
  The number must be the real one.
- **Draw text after fonts load.** Call `await K.loadFonts([...])` before creating sprites or textures with
  text, or they render in the fallback font.
- **Deterministic randomness only.** `K.seeded(n)` for grain, scatter or jitter.
- **Formats from one scene.** `K.format()` reads `?format=v` (1080x1920) or `?format=s` (1080x1080).
  Give the vertical cut its own camera distances (stand further back: the horizontal field of view is
  about half) and its own caption and stamp positions.
- **Captions are short**: a kicker, a headline of five words or fewer, one line of support. On screen for
  at least the time it takes to read twice.
- **Brand**: the user's colours in `colors`, the user's fonts in `fonts`. One accent colour, used for the
  thing that matters in each frame.

Preview by opening the page in a browser (it loops), or freeze a moment with `?t=6.5`. Serve it over
http (the scripts do this for you): ES modules don't load from `file://`.

## 5. Check stills, then render

A still costs about a second; a full 60 fps render of 20 s costs 20 minutes. Always look first:

```bash
node scripts/stills.mjs scene.html --root <folder holding scene and kit.js> --out out/stills --count 10
node scripts/stills.mjs scene.html --root … --format v --out out/stills-v --times 1.5,4,7.2,9,12
```

Read `out/stills/sheet.png` yourself. Check: nothing important clipped at the frame edge (vertical cut
especially), captions not covering the subject, labels in the right font, numbers correct and legible,
the end card centred. Fix and re-check until clean, then render:

```bash
node scripts/render.mjs scene.html --root … --fps 60 --out out/film-h.mp4
node scripts/render.mjs scene.html --root … --format v --fps 60 --out out/film-v.mp4
```

- Rendering uses SwiftShader (software WebGL) at roughly 1 to 1.5 s per 1080p frame. Draft at
  `--fps 24`, final at 60. `--from`/`--to` re-renders a section. `--gpu` uses a real GPU where present.
- Run the formats one after another, not in parallel, on a small machine: parallel renders each slow down.
- Long renders: run in the background and keep working.

## 6. Voiceover

```bash
python3 scripts/voiceover.py keys            # prints elevenlabs | openai, or exits 3 with "none"
python3 scripts/voiceover.py tts lines.txt --out out/vo [--provider elevenlabs --voice <id>]
python3 scripts/voiceover.py place timeline.json --duration 15.5 --out out/vo-track.wav
```

Pick the path by what is available, and say which one you used:

1. **A TTS key in the environment** (`ELEVENLABS_API_KEY`, or `OPENAI_API_KEY`): `tts` generates one file
   per line. ElevenLabs gets the neighbouring lines as context, so separately generated lines keep one
   continuous delivery. Voice and model come from `--voice`/`--model` or `ELEVENLABS_VOICE_ID`,
   `ELEVENLABS_MODEL_ID`, `OPENAI_TTS_VOICE`, `OPENAI_TTS_MODEL`, `OPENAI_TTS_INSTRUCTIONS`.
2. **An ElevenLabs connector (MCP) instead of a key**: list voices, pick one that fits the brand (a warm
   narrator by default), generate the whole script as one take with line breaks as pauses, download it,
   then `voiceover.py split take.mp3 --lines N --script lines.txt --out out/vo`. Split prints every
   pause it finds and cuts at the N-1 longest. A pause inside a line ("Groceries: … dollars.") can be as
   long as a line break, so read the printed pauses against the script; when the pick is wrong, pass the
   right ones with `--cuts 1.6,5.04,9.12`. Keep the take and its cut times with the film so a later
   remix needs no new generation (the example ships `voice/take.mp3`).
3. **A take the user recorded**: same `split`.
4. **None of these**: no voice. The captions carry the words, and the music bed and effects carry the
   rhythm. Tell the user a voice can be added later by setting a key and re-running the mix; the picture
   does not need re-rendering unless beats move.

Generating speech spends the user's credits: generate each line once, listen (check durations in
`lines.json`), and regenerate only a line that is wrong. Never put a key in a file or a commit.

After the voice exists, adjust the beat times to the real durations, re-check stills, and re-render.

## 7. Sound and mix

The scene's `renderAudio()` synthesizes effects and music offline from an event list, tied to picture
events: `tick` per typed key, `send` on a button, `whoosh` on a big move, `knock` per part landing (pitch
varies by index), `pencil` under a line drawing, `paper`, `thud` under a stamp, `shimmer`, `chime` on the
end card, and an arpeggio `music` bed on a chord list. **Put every sound one frame after its event**
(`t + 1/fps`): it reads as caused by the picture. `render.mjs` saves it as `film.sfx.wav`.

```bash
python3 scripts/mix.py out/film-h.mp4 --sfx out/film-h.sfx.wav [--vo out/vo-track.wav] --out out/final-h.mp4
```

With a voice, the bed ducks under it by sidechain compression. The mix is then measured, given one
linear gain to -14 LUFS integrated, and limited to a -2 dBTP ceiling, re-measuring until it lands within
0.3 LU; that suits web and social, and the script prints the result. Synthesized knocks and thuds are
very peaky, so one-pass loudnorm misses the target by 2 to 4 LU on these mixes.

## 8. Verify and deliver

- Re-run `stills.mjs` on the final scene and read the sheet one last time.
- `ffprobe` the finals: duration, resolution, an audio stream. Spot-check a few frames from the MP4
  itself (`ffmpeg -ss 8 -i final.mp4 -frames:v 1 check.png`).
- Report what is real and what is depicted. If the film shows an outcome the product did not actually
  produce (a passing check, a number), say so to the user.
- File size: CRF 17 at 1080p60 is about 0.6 MB per second. If an upload limit bites, re-encode the
  picture with `--crf 20` to 23 rather than lowering resolution.

## Pitfalls

- **Playwright not found** from an ES module: `NODE_PATH` does not apply to `import`. The scripts look in
  the current project, then the global `npm root -g`.
- **Lines render as zigzags**: use `THREE.LineSegments` with point pairs, not `THREE.Line`.
- **A frame shows the wrong state**: something in the scene depends on the previous frame or the clock.
  Every value must come from `t`.
- **Stills look right but the render is blank or black**: the canvas needs `preserveDrawingBuffer: true`
  (`K.stage` sets it) and the page must set `window.ready` only after assets load.
- **Fallback fonts in sprites**: text drawn before `K.loadFonts` resolved.
- **Killing servers by pattern** (`pkill -f …`) can kill your own shell. Stop a process by its pid.
