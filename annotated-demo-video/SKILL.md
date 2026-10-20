---
name: annotated-demo-video
description: Produce a narrated, annotated walkthrough video of a real running web app — title and chapter cards, the exact elements ringed with caption cards, a closing "what happened" frame — as a shareable HTML player plus an MP4, deterministically from a JSON storyboard and verified with a contact sheet. Use for bug repros (before/after), feature or flow showcases, and "walk a stakeholder through this PR's affected surfaces". Triggers on "demo video", "bug repro video", "annotated walkthrough", "showcase this flow", "video of this PR for review".
---

# Annotated demo / walkthrough video (drive the real app, narrate on-screen, verify)

Turns a flow in a **real running web app** into a narrated walkthrough: a title card, then one still per
step with the element that matters ringed in the accent colour, the rest of the page dimmed, and a
caption card ("3 / 12", a short title, one or two sentences). The same frames come out three ways:

- **`<name>.html`**: a self-contained player (frames inlined) with autoplay, a step rail with chapters,
  Back/Next and arrow keys, light and dark mode. Publish it as an Artifact or host it anywhere.
- **`<name>.mp4`**: H.264, one still per step with crossfades, each held for its reading time.
- **`sheet.png`**: a contact sheet to check the run at a glance before showing anyone.

Everything is scripted. The same storyboard against the same app state gives byte-identical frames,
MP4 and HTML (fixed viewport and scale, animations, transitions, carets and focus rings off, fonts
awaited, clock optionally frozen).

Two shapes, same storyboard format:

- **Bug repro** — reproduce a specific failure and name its cause; optionally a **before/after** with a
  chapter per state (see `examples/checkout/`).
- **Showcase / walkthrough** — narrate a feature, flow, or a PR's affected surfaces for a
  stakeholder/decision. Same overlays, no "wrong outcome" framing.

For a plain video with no callouts, or stills only, the live-recording harness in `scripts/` covers
that too (see "Live-recording harness" below) — annotations are the reason to use the storyboard path.

This skill is **tool-agnostic about the app** but specific about technique. **[ADAPT]** sections are
environment-specific; examples there are from Rails apps, but nothing depends on Rails.

## Files

`$WT` below is this skill's folder (e.g. `export WT=~/.claude/skills/annotated-demo-video`).

| Path | What it is |
|---|---|
| `scripts/record.cjs` | Playwright recorder: runs a storyboard JSON against a URL, writes `frames/` + `manifest.json` |
| `adapters/capybara_walkthrough.rb` | Same output from inside a Rails/Capybara system test (fixtures, sign-in helpers, jobs) |
| `scripts/annotate.js` | The overlay drawing both recorders inject (`__wt.titleCard`, `__wt.frame`, `__wt.ready`) |
| `scripts/finish.py` | Crops, contact sheet, MP4 (ffmpeg xfade) and HTML player from a manifest |
| `assets/player.html`, `assets/theme.json` | Player template and the default theme (violet palette, Outfit type) |
| `examples/demo-site/`, `examples/storyboard.json`, `examples/run_example.sh` | A tiny task board, a 5-step showcase storyboard and the self-test |
| `examples/checkout/` | A Shopify-style checkout with a planted subtotal bug, a before/after storyboard and `run_checkout.sh` |
| `scripts/lib.mjs`, `hero.template.mjs`, `walkthrough.template.mjs`, `verify.sh` | Live-recording harness (`recordVideo` webm) for motion a still can't show |

## Delegate by default

If you are an orchestrator with subagents available, do not execute this skill inline: spawn a
general-purpose agent primed with this skill and hand it the scene sentence / walkthrough + seed spec.
§1–§5 are the *producer's* manual — §4's sheet check and re-records included. The main session keeps
three things: its own acceptance review (read the returned `sheet.png` once, judged against the scene
sentence, before attaching), any PR/ticket attach step that needs a logged-in browser, and **quoting the
producer's absolute asset paths verbatim in its final reply** (§6 — a delegated run is the most common
way the path gets lost; require the producer to return it). Rationale: recording inline eats a large
share of the orchestrator's context and output budget.

---

## 0. What "good" looks like (the bar)

A **bug-repro** walkthrough:
1. Opens with a **title card** (bug ID + one-line thesis).
2. Establishes the **setup** in the first frame's caption ("Customer X on plan Y, $Z/mo").
3. Drives the **real UI** to the failure, ringing the element each caption is about.
4. Shows the **wrong outcome**; ends with a **"what actually happened"** frame: ring the wrong value, and
   the caption gives the ✗ facts plus **Net:** impact.
5. For a **before/after**, add an "After" chapter that repeats the key frames against the fixed build
   (same cart, same data) so the two totals sit side by side in the step rail.

A **showcase/walkthrough**: title card (what we're showing + why it matters) → each surface with a
caption naming what changed → optional closing frame stating the decision being asked.

Both: **verified** — frames confirmed by reading `sheet.png`, and any claimed state confirmed
independently. **Read live values from the page** into captions (`{{ selector }}`, §3); never hardcode
a number that can drift.

---

## 1. Prerequisites (one-time, per machine)

Work in a **scratch dir in the OS temp dir** (`/tmp/demos/<id>`), never the workspace — every asset
produced here is ephemeral and must stay out of the app's repo (§6).

Needs: Node 18+ with Playwright and **full Chromium** (not headless-shell), Python 3 with Pillow, ffmpeg
(only for the MP4). In Claude Code cloud containers all are preinstalled (Playwright under
`/opt/node22/lib/node_modules`, Chromium at `/opt/pw-browsers`). Elsewhere:

```bash
mkdir -p /tmp/demos && cd /tmp/demos
npm i playwright@latest >/dev/null && npx playwright install chromium
pip install pillow
which ffmpeg || brew install ffmpeg
```

`record.cjs` finds Playwright in the current directory, `NODE_PATH`, or the usual global folders; set
`CHROMIUM_PATH` to point at a specific browser binary.

**Self-test once per machine:** `bash $WT/examples/run_example.sh /tmp/wt-example`. Expect 5 frames,
`demo.mp4`, `demo.html`, `sheet.png`. If this fails the environment is the problem, not your storyboard.
`bash $WT/examples/checkout/run_checkout.sh /tmp/wt-checkout` records the before/after bug demo (7 frames).

---

## 2. [ADAPT] Bring up the target environment

| Need | How to find it | Example (a Rails app) |
|---|---|---|
| **Runtime** (not system default) | `.ruby-version`/`.nvmrc`/`mise`; check the *running server's* process | mise Ruby; prepend to PATH or you get system Ruby + cryptic bundler errors |
| **Backing services** | compose file / `bin/*`; `docker ps` | `docker compose up -d` (postgres/redis) |
| **Web server + URL** | running process; dev proxy; `curl` it | `bin/dev` on `http://localhost:3000`; with per-worktree hosts, use the host that serves *this* checkout |
| **Auth / login** | seed file; the actual login path | `/users/sign_in`, fields `user[email]`/`user[password]`; set a known dev password via `rails runner` if needed |
| **Tenant / mode** data must match | controller before_actions; cookies | sandbox vs live; feature flags — seed to match or data won't render |
| **A console/runner** to seed + verify | `bin/rails runner`, `node script.js`, SQL | `bundle exec rails runner script.rb` |

Sanity check: `<runner> -e 'puts DB ok && counts'` and `curl -k <login URL>` returns 200/302 (not 500).

---

## 3. The workflow (loop)

```
identify scene → (bug only) classify demonstrability → seed data → rehearse headless
   → write storyboard → record → read sheet.png → build → output the path
```

### 3a. Write the one-sentence scene
Bug: *"Given <setup>, when <action>, the system <wrong outcome> because <root cause>."*
Showcase: *"This shows <capability> across <surfaces>, so <stakeholder> can decide <X>."* Narrate exactly that.

### 3b. (Bug only) Classify demonstrability — decide if it's filmable
| Class | Definition | Approach |
|---|---|---|
| 🎥 UI-repro | cause AND see the failure in the UI | drive it live |
| 🩺 State-demo | server-side trigger, broken end-state visible in UI | trigger off-camera (runner/in-page fetch), then show + annotate |
| 🚫 Not filmable | symptom only in a field the UI never shows / API-only / an *absence* | document + recommend a console walkthrough |
| 🧩 Structural | schema/type/concurrency smell, no single frame | same as 🚫 |

**Be honest about 🚫/🧩** — a contrived video is worse than a documented rationale. **Don't harvest or
hardcode API keys/secrets** to demo API-only behavior; classify it 🚫.

### 3c. Seed deterministic data (runner script)
Build via **real models/services** (factories often aren't loaded in a dev runner). Derive the
tenant/owner from the login user so data is visible. Make it **idempotent** (mark prior demo rows by a
known name/email, destroy/recreate). Choose **round, drift-robust** values and realistic names; never
record real people's data. Print created IDs + URLs.

### 3d. Rehearse headless (de-risk before recording)
Run the exact code path the UI will hit (service/controller in the runner) and assert the end-state.
If the rehearsal mutates the demo, **re-seed** (IDs change → update the storyboard, or better, resolve
ids by name).

### 3e. Turn the walkthrough into a storyboard
The caller provides the walkthrough: either a ready storyboard JSON (record it as is) or the flow in
prose or a list of steps. In the second case:
- Each step they wrote becomes one frame, in their order, with their wording kept for the title and
  caption (tighten to the limits below, never change the meaning). Their headline becomes the title card.
- Don't add, drop or reorder steps. Your job is the mechanics they left out: the actions between frames,
  the selectors and the demo data. Find these by reading the app's routes, views or components, so
  every selector exists before you record.
- If a step can't be shown (the screen doesn't exist, it needs data you can't seed), record the rest and
  say which step and why, rather than inventing a substitute.
- With no walkthrough given, ask for one, or offer a draft storyboard for the caller to approve first.

Storyboard rules, for what you write or fill in:
- Open with a title card: the feature's name (or bug ID) as the title, one sentence on what the viewer
  will see.
- 6 to 14 frames for a full walkthrough (a quick demo may have fewer). One idea per frame. Group them
  into 2 to 4 chapters (`chapter` on the first frame of each). A before/after is two chapters.
- Frame title: at most 6 words, in the product's own nouns ("Step 1: add the athletes").
- Frame body: one or two sentences, at most about 30 words, saying what is on screen and why it matters.
  Name people and data the demo uses ("Lena accepts her invite"), never "the user clicks the button".
- **Read live values, never hardcode displayed numbers:** write `{{ css selector }}` in a title or body
  and the recorder substitutes that element's rendered text at shot time ("The total reads
  `{{ #summary .total }}`"). In the Capybara adapter, interpolate `find(sel).text` in Ruby.
- `selector` is what the caption is about; set `target` when a different (usually larger) element should
  be ringed and centred, e.g. ring the whole totals box, talk about the subtotal line.
- End on the outcome: the result the flow exists for (or, for a bug, the wrong result), seen from whoever
  it affects.

### 3f. Record
Use whichever recorder can reach the flow:
- App reachable by URL (a dev server, a deployed preview, a static site), sign-in by filling a form:
  `node $WT/scripts/record.cjs storyboard.json --out /tmp/demos/<id>` (`--headed` to watch). Log in once
  as the first steps; the session persists — don't re-login mid-run. `goto` is **Turbo-safe** (retries
  `ERR_ABORTED`, which a raw `page.goto` hits when Turbo Drive intercepts).
- Rails app whose flow needs test fixtures, sign-in helpers, `perform_enqueued_jobs` or time travel:
  write a throwaway system test using the adapter (template below), run it with `WALKTHROUGH_DIR=<dir>`,
  then delete the test file. Never commit it.

Interaction patterns (the ones that bite):
- **Submit by role+name** (`{"action":"click","role":"button","name":"Change Product"}`); a generic
  `button[type=submit]` can grab the wrong button (it grabbed "Sign out" once).
- **Custom selects** (TomSelect/Select2) hide the native `<select>` — set programmatically with `eval`:
  `document.querySelector('#sel').tomselect.setValue(id)`; resolve ids by name to survive re-seeds.
- **State-demo (server-triggered):** trigger off-camera — either run the service in a runner before
  recording, or an in-page `fetch` (`eval`) to a same-origin endpoint with the CSRF token, then `goto`
  to reload the new state.
- **Before/after:** serve the fixed build on a second URL (or a second checkout on another port) and
  `goto` it at the start of the "After" chapter; the frames repeat the same selectors and `{{ }}` values.
  Open each chapter with its own title card (`"type": "title"` with a `kicker` such as "Before" / "After")
  so the boundary is visible in the MP4 too, not only in the player's step rail; every caption card also
  carries the current chapter name.
- To read a value back for your own checks, **`return` it from `page.evaluate`** (console.log inside the
  browser is not captured to your stdout).

---

## 4. Verify (don't trust it blind)

**Check `sheet.png` before going further** (finish.py writes it; run §5 with `--no-video` first if you
like). Read the image and look for: a ring around the wrong or an empty element, a caption card covering
what it describes (use `"side": "left"` or ring a smaller target), flash messages or toasts missing, a
frame showing a loading state (add a `wait_for` before the shot), half-loaded fonts, a live value that
came out wrong. Fix the storyboard and re-record; recording is cheap. **Re-confirm any claimed end-state**
in the DB (the run performed the real mutation).

When a step fails, the recorder stops, saves `<out>/failed-step.png` and names the step. Fix that step
and rerun.

---

## 5. Build

`python3 $WT/scripts/finish.py <dir> --name <kebab-name>`. Options: `--fade 0.6`, `--jpeg-width 1200`,
`--quality 82`, `--crf 22`, `--no-video`, `--wpm 200`, `--seconds N`.

**THE READING-TIME RULE (hold ∝ word count, not a magic number).** Each step is held for
`base + words/wpm`, clamped (defaults `wpm:200, base:1.2s, min:2.2s, max:9s`), in both the MP4 and the
player's autoplay. A short caption gets a quick beat and a dense one gets up to `max` — no per-scene
tuning. Tune `--wpm` for a faster/slower pace; use `--seconds` only when a fixed hold is really wanted.

Compression: UI frames are flat, so the MP4 is small; raise `--crf` for smaller files and eyeball one
frame for legibility. The HTML warns when it passes 15 MB; lower `--jpeg-width`.

---

## 6. Deliver and output the path — never commit into the app repo

Publish `<name>.html` with the Artifact tool (icon `video`; it already has a `<title>`, light and dark
tokens and a phone layout). Deliver the MP4 as a file. Tell the person it was recorded from the real app
with demo data, and mention any bug the recording turned up.

These assets are **ephemeral**: the mp4, HTML, frames, contact sheet, storyboard, seed script and any
throwaway test exist only to be watched/shared once. They live in the **OS temp dir** (`/tmp/demos`),
**not the workspace** — so they can never be accidentally committed.

- **Never copy a video, still, or any other generated asset into the app's repo, and never commit one.**
  Don't create `docs/<area>/assets/...` or stage the mp4. If git status shows one, it's misplaced.
  (The committed outputs under this skill's own `examples/` are the one exception: they document the
  skill itself.)
- **Always end with the absolute path(s)** of the finished assets — at minimum the mp4, plus the HTML
  and contact sheet: `🎬 /tmp/demos/<id>/<name>.mp4`, `🌐 /tmp/demos/<id>/<name>.html`,
  `🖼  /tmp/demos/<id>/sheet.png`, plus the Artifact link if published. This is **not optional and has no
  exceptions**. The full path goes in the **final user-facing message** of the run, spelled out in full —
  not only in a script's stdout, not only in a subagent's report, never abbreviated (`~/…`, `<id>.mp4`,
  "in /tmp/demos"). It still goes there when the video was attached to a PR, when the run was delegated
  (quote what the producer returned), when a re-record replaced an earlier take (give the path of the take
  you're standing behind), and when the run ended partly failed but an mp4 exists. If you can't state the
  path, the run isn't done.
- To attach to a PR/ticket, upload the mp4 through the tracker's UI/API (GitHub renders an uploaded mp4
  inline) — that's a copy living off-repo, not a committed file.

---

## Storyboard reference

The `//` comments below are explanation only; real storyboards are plain JSON (see
`$WT/examples/storyboard.json` and `$WT/examples/checkout/storyboard.json`).

```json
{
  "title": "Adding a task",                       // player heading, and the default title card kicker's subject
  "kicker": "Tasks · new in this release",        // small caps line on the title card and above the player heading
  "note": "Recorded from the demo site with sample data.",
  "base_url": "http://127.0.0.1:3000/",           // opened first; relative URLs in goto resolve against it
  "viewport": { "width": 1440, "height": 900 },   // frame size; keep 16:10 or 16:9
  "freeze_time": "2026-10-14T09:00:00Z",          // optional: pins Date.now() in the page
  "timezone": "UTC", "locale": "en-US", "color_scheme": "light",
  "show_count": true,                             // "3 / 12" on caption cards
  "show_chapter": true,                           // current chapter name on caption cards ("Before · 3 / 12")
  "theme": { "accent": "#0E6E78" },               // optional overrides of assets/theme.json
  "theme_file": "brand-theme.json",               // or a whole theme, relative to the storyboard
  "steps": [
    { "shot": { "type": "title", "title": "Adding a task", "body": "One sentence on what the viewer will see." } },
    { "do": [ { "action": "click", "role": "link", "name": "New task" } ],
      "shot": { "selector": "#task-form", "title": "Fill in the task", "body": "...", "chapter": "Create" } }
  ]
}
```

Each step runs its `do` actions in order, then takes its `shot` (a step may have only one of the two).
Shot fields: `selector` (required for frames), `target`, `title`, `body` (both accept `{{ selector }}`
live values), `chapter`, `side` (`right` or `left`), `keep_focus` (keep the focused field's ring; off by
default for stable frames).

| Action | Fields | Notes |
|---|---|---|
| `goto` | `url` | Waits for network idle; retries Turbo `ERR_ABORTED` |
| `click`, `hover`, `check` | a locator | |
| `fill` | a locator, `value` | |
| `select` | a locator, `value` | Option value or label |
| `upload` | a locator, `files` | Path or list, relative to the storyboard |
| `press` | `key` | e.g. `Enter`, `Control+A` |
| `wait_for` | `selector` or `text`, optional `timeout` ms | Use before any shot that follows navigation or a network call |
| `wait_url` | `url` | Glob allowed |
| `wait_ms` | `ms` | Last resort |
| `eval` | `js` | Runs in the page, e.g. to open a menu, set a TomSelect, or fire a CSRF'd fetch |
| `resize` | `width`, `height` | |

A locator is one of `selector` (CSS), `role` + `name`, `label`, `placeholder` or `text`, plus optional
`exact: true`. Prefer role, label and text: they read like the captions and survive markup changes.

## Capybara adapter template

```ruby
require "application_system_test_case"
require "<path to $WT>/adapters/capybara_walkthrough"

class ZzWalkthroughTest < ApplicationSystemTestCase
  include CapybaraWalkthrough
  include ActiveJob::TestHelper

  test "walkthrough" do
    data = Demo::Seed.call                                  # the app's own demo seed, or fixtures
    walkthrough_start out: ENV.fetch("WALKTHROUGH_DIR"), title: "Moving a roster",
                      kicker: "Acme · new in this release", steps: 12   # steps = frames after the title card
    sign_in data.coach
    visit coach_path
    walkthrough_title "Moving a roster", "A coach brings athletes across in three steps."
    walkthrough_frame ".head-actions .move", "Start from the morning page", "The new button sits beside Library.", chapter: "The coach"
    click_on "Move your roster"
    walkthrough_frame "#step-1", "Step 1: add the athletes", "Upload the list, or add them one at a time.", target: ".move-step:first-child"
    # Signing out: Capybara.reset_sessions! then walkthrough_resize, then sign the next person in.
    walkthrough_finish
  end
end
```

Run it alone, e.g. `WALKTHROUGH_DIR=/tmp/demos/roster bin/rails test test/system/zz_walkthrough_test.rb`,
then `python3 $WT/scripts/finish.py /tmp/demos/roster --name roster-move`, then delete the test. With
Cuprite/Ferrum the adapter takes full-page shots and crops at the offset; with Selenium it scrolls to the
offset and takes a viewport shot.

## Theming

`assets/theme.json` is the default (fonts via `font_css`, the accent and card colours, and the player's
light and dark palettes). Override a few keys inline with `"theme": {...}` in the storyboard, or write a
whole theme file from the product's design tokens and point `theme_file` at it (or pass `theme:` to
`walkthrough_start`). Keep the accent strong enough to read as a ring on both white and dark pages.

## Why it is built this way (THE SCROLL RULE)

**Never blind-scroll.** A timed scroll overshoots a short page and parks in dead whitespace — it reads as
"stuck/broken". The storyboard recorder never scrolls at all: overlays are absolutely positioned in
document coordinates and the screenshot is taken full-page and clipped at the offset `__wt.frame`
returns, which centres the target. Scrolling first and drawing fixed-position overlays gives blank or
misaligned frames in headless Chrome, so keep this approach if you change anything. Overlays are real DOM
with `pointer-events:none`; `__wt.clear()` runs between shots so they never stack.

## Live-recording harness (motion you must show)

When the point is motion a still can't show (an animation, a race, a spinner that never resolves), or
when a plain captioned video or a set of stills is all that's wanted, use the `recordVideo` harness in
`scripts/`:

- `cp $WT/scripts/{lib.mjs,hero.template.mjs,walkthrough.template.mjs,verify.sh} /tmp/demos/`, fill the
  CONFIG and SCENE in a copy of `hero.template.mjs` (annotated) or `walkthrough.template.mjs` (plain
  video or screenshots, `MODE=video|screenshots`), run with `node` from `/tmp/demos` (playwright
  installed there).
- `lib.mjs`: `login` once then **`gotoSafe`** for every navigation; `chapter()`, `banner()`,
  `callout(selector, html, {pos})`, `summary(title, rows, netHtml)`, `clearOverlays()` between scenes.
- **Scroll rule:** only `reveal(page, selector)` (scroll the element to centre, outline, hold) or `tour(page)`
  (page-aware, stops at the document bottom). Never a timed scroll.
- **Reading-time rule:** never `sleep(5000)` after an overlay; `await dwell(...everyStringOnScreen)` /
  `readMs(text, {wpm,base,min,max})` (default `wpm:200, base:1200, min:2200, max:9000` ms).
- **Verify:** you cannot watch the webm — `bash verify.sh /tmp/demos/_video <id>` gives duration, a 4×6
  contact sheet and a compressed faststart mp4 (`-preset slow -crf 28`, ~1MB/min; tune with `CRF=`); grab
  stills with `verify.sh ... <id> 33:wrong_value,50:summary` after reading the sheet.

## 7. Pitfalls & lessons (read before starting)

- **Never blind-scroll** — the storyboard recorder never scrolls; in the live harness use `reveal()`/`tour()` only.
- **Never hold an annotation for a magic number** — holds come from word count (§5 / `dwell()`).
- **Verify from the contact sheet, not assumptions** — read `sheet.png`; re-confirm end-states in the DB.
- **Never hardcode displayed numbers** — use `{{ selector }}` live values; seed/time drift will disagree.
- **Re-seeding changes IDs** — resolve ids by name; update hardcoded ids after a re-seed.
- **Use the project runtime** (mise/rbenv/nvm), not the system default, or you get cryptic errors.
- **Match seed mode** (tenant, sandbox/live, soft-delete scopes) or data won't render.
- **Hit the right host** — with per-worktree dev hosts, a flat `localhost:3000` may serve a sibling
  checkout's schema; use the URL that serves *this* checkout.
- **Turbo aborts navigations** — `goto` in the recorder and `gotoSafe` in the harness retry; never a raw
  `page.goto` in custom code.
- **Watch for id collisions in demo pages** — a section `id="shipping"` and a totals span `id="shipping"`
  will put the shipping cost in the address form (this bit the checkout example).
- **Don't fake API-only bugs with harvested credentials** — classify 🚫 and document.
- **Assets are ephemeral — never commit them into the app repo.** They stay in `/tmp/demos`; output the
  path instead (§6).
- **Never finish without the full mp4 path** — the last message of every run states the absolute path
  (§6), including after a PR attach or a delegated run. "It's in /tmp/demos" is a failed handoff.

## 8. Checklist (copy per item)

```
[ ] Scene sentence written (bug: given/when/wrong/because — or showcase: shows/so-that)
[ ] (bug) Demonstrability classified 🎥/🩺/🚫/🧩 — if 🚫/🧩, document & stop
[ ] Seed script written (real models, idempotent, deterministic, realistic names), data seeded
[ ] Rehearsed headless — end-state asserted; re-seeded if consumed
[ ] Storyboard: title card, one idea per frame, ≤6-word titles, ≤30-word bodies, live values via {{ }}, ends on the outcome; every selector checked in the source
[ ] Recorded into /tmp/demos/<id>; sheet.png read and every frame correct; DB end-state re-confirmed
[ ] finish.py built <name>.html + <name>.mp4 (reading-time holds, CRF-tuned, frame eyeballed); HTML published as an Artifact
[ ] FINAL MESSAGE states the full absolute mp4/html/sheet paths — no exceptions, even after a PR attach
    or a delegated run; assets left in /tmp, NOT copied into the app repo or committed
```
