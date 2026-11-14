---
name: end-grain-boards
description: Design end-grain cutting boards with geometric patterns (3D tumbling blocks or cubes, six-point and eight-point LeMoyne stars, checkerboard, brick, or any custom pattern of convex pieces) from a described pattern and wood species, and produce a checked shop plan with a material list in board feet, a cut list with exact bar sizes and blade tilts, step-by-step rip, glue-up, crosscut and re-glue instructions, SVG diagrams of every stage, and a photorealistic render through plan-to-photo. Use whenever the user wants a cutting board or butcher block pattern, asks how to make a 3D or star or checkerboard end grain board, gives a pattern and woods ("tumbling blocks in maple, cherry and walnut"), wants a cut list or glue-up sequence for a board, or asks to change the pattern, size, piece size or species of an existing board plan.
---

# End-grain boards

Turn "repeating 3D cubes in maple, cherry and walnut" into a plan a woodworker can build from and a
photo of the finished board. The board face is the truth: every piece is a convex polygon, the
script proves the pieces tile the board, and every list, drawing and step is derived from it.

```
brief → design.json → cbplan.py (checks, plan, diagrams, guide image) → read checks + look → render → deliver
```

**How every board here is built.** An end-grain face is the cut end of a log. Each polygon on the
face is a long *bar* of that cross-section, ripped on the table saw (bevelled for angles). Bars are
glued into *units* (a cube = three rhombi), units or bars side by side into a *log*, the log is
crosscut into *slices* about 1-5/8" thick, and the slices are laid out (some turned or flipped) and
glued edge to edge into the board, which is trimmed and flattened. Identical slices come from one
log, so the script matches slices by shape (any of the eight ways a slice can lie on the bench) and
makes as few logs as it can.

| Path | What it is |
|---|---|
| `scripts/cbplan.py` | `design.json` → `out/`: `plan.html`, `plan.json`, `svg/*.svg`, `board.obj`, `guide.png`, `spec.md`, `room.md`. Exit 1 if a check fails. |
| `scripts/patterns.py` | The pattern generators (`cubes`, `stars6`, `snowflakes`, `stars8`, `checker`, `brick`) and the polygon format for `custom`. |
| `scripts/species.py` | Cutting-board woods: end-grain colour, Janka, shrinkage, notes; the woods to refuse. |
| `scripts/plan_page.py` | The plan page: numbered sheets (overview, material list, bars & rip setups, units & logs, slice layout, building it) with title blocks, then the checks. Warm paper, Archivo / Source Serif 4 / IBM Plex Mono, walnut accent, light and dark. Change the look here, not in cbplan. |
| `scripts/render_guide.py` | The colour-coded perspective of the board (called by cbplan; rerun with another `--az/--el`). |
| `scripts/selftest.py` | Proves the checks catch an overlap, a gap, a bevel past 45 degrees and a bad wood. |
| `references/patterns.md` | Each pattern's geometry and parameters, and how to write a `custom` design. **Read for anything not in the generators.** |
| `references/technique.md` | Bevel ripping, tape glue-ups, crosscutting slices, flattening, finishing, safety. **Read before writing advice the plan doesn't already give.** |
| `references/species.md` | Choosing and pairing woods. |
| `examples/` | Five worked boards: `tumbling-blocks`, `six-point-stars`, `snowflakes`, `lemoyne-stars`, `checkerboard`, each with `design.json`, `plan.html`, `guide.jpg` and (four) `photo.jpg`. |

**Needs** Python 3 with numpy and Pillow. The render uses the `plan-to-photo` skill
(`plan-to-photo/scripts/nano_banana.py`, needs `GEMINI_API_KEY`); look for it beside this skill, in
`~/.claude/skills/plan-to-photo`, or in https://github.com/seattlecyclist/skills. If `scripts/` is
missing, the full skill is in `end-grain-boards/` of that repo.

## 1. Brief

Get, or ask once for only what you cannot infer:
- **Pattern.** Map the user's words to a generator: cubes, 3D boxes, tumbling blocks → `cubes`;
  stars, Star of David, hexagram → `stars6`; snowflakes → `snowflakes`; eight-point, quilt or LeMoyne star, compass star →
  `stars8`; checkerboard → `checker`; brick, running bond, offset → `brick`. Anything else (chevrons,
  hexagons, diamonds, a logo-like motif) → `custom` polygons (`references/patterns.md`). Say which you chose.
- **Woods**, one per role the pattern has (`cubes`: lid, left, right; `stars6`: star, field; `snowflakes`: flake, field; `stars8`:
  star_a, star_b, field; `checker` and `brick`: a, b). For 3D effects, light-medium-dark
  matters more than the species: maple / cherry / walnut is the classic. Fill gaps from
  `references/species.md` and say so. Refuse red oak, softwoods, spalted wood, cocobolo (it explains why).
- **Size.** Default 12 x 16 x 1-1/2". Generators fit whole repeats, so the finished size moves to the
  nearest repeat; report the actual size. Piece size (`side`) sets how busy it looks: rhombus sides
  1" to 1-1/2", star rhombi 3/4" to 1-1/4".
- **Extras:** edge treatment, feet, juice groove, handles (`options`), and the setting for the photo.

## 2. design.json

```json
{
  "name": "Tumbling Blocks End-Grain Board",
  "description": "3D tumbling blocks: a honeycomb of cubes seen corner-on, maple lids over cherry and walnut sides",
  "pattern": "cubes",
  "params": {"side": 1.25},
  "board": {"width": 12, "length": 16, "thickness": 1.5},
  "species": {"lid": "maple", "left": "cherry", "right": "walnut"},
  "options": {"edge": "1/8\" chamfer", "feet": true, "juice_groove": false, "handles": false},
  "shop": {"kerf": 0.125, "max_log_length": 24, "stock_width": 5.5},
  "render": {"room": "optional room brief for the photo"}
}
```

`description` is used word for word in the render prompt, so describe what a viewer sees. `shop`
defaults: kerf 1/8", slices cut 1/8" over finished thickness, 3/4" trimmed off each log end, logs at
most 24" (longer ones are split), blanks 5-1/2" wide, one spare slice per log. Generator `params`
are in `references/patterns.md` (`rows`/`cols` override the fit).

## 3. Build and check

```bash
python3 scripts/cbplan.py design.json out/
```

It prints the actual size, every bar shape with its blade tilt, each log (count, length, slices) and
the board feet per species, then the checks: species hard enough (Janka 900+), bars convex, **no
overlaps and no gaps** over the finished board (a sampled coverage test), every bevel 45 degrees or
less, board 1" or thicker; warnings for species that move differently, unknown species and boards
large for their thickness. A FAIL is a design error: fix the design, never the plan text. Explain any
WARN to the user.

Then look. Open `out/svg/face.svg` (or `plan.html`) and `out/guide.png` and ask: does the pattern
read as what the user described? Contrast between roles is the usual problem (two mid-browns
merge); the star patterns also depend on `spacing` and on which wood is the star. Change and rerun.
Also read the log and layout diagrams: a pattern that needs many log types (`stars6` with `sparse`
spacing needs seven) is more glue-ups; prefer a variant with one to three logs where the look allows,
and say why. Motifs bigger than a few rows (snowflakes) are built row by row: tell the user how many
logs and that the extra end trim raises the board feet.

## 4. Render (plan-to-photo)

The photo is made by plan-to-photo's Nano Banana path from `guide.png` (the board drawn exactly, colour
coded by wood) plus `spec.md` (the board in words) and `room.md` (the setting):

```bash
P2P=../plan-to-photo   # or ~/.claude/skills/plan-to-photo
GEMINI_API_KEY=... python3 $P2P/scripts/nano_banana.py out/guide.png out/spec.md out/room.md out/photo.jpg --takes 2
python3 scripts/cbplan.py design.json out/ --photo out/photo-1.jpg      # embed the chosen take in plan.html
```

Edit `room.md` for the user's setting (keep the last sentence: nothing may cover the board's top).
Change the view with `"guide": {"az": -28, "el": 36}` in the design. Always make at least two takes
and compare each to `guide.png` piece by piece: count the repeats, check which wood is where and
that the edges show the right stripes. Takes go wrong in recognisable ways (in the LeMoyne example
one take drew a single giant star in face grain); keep only a take that matches, and make more if
none does. Without a key, deliver the plan with `guide.png` and say the photo needs `GEMINI_API_KEY`.
For a Blender render, `board.obj` (meters, Z up, a material per species) goes into plan-to-photo's
scene spec like any other model.

## 5. Deliver

Publish `plan.html` (self-contained) as an Artifact or attach it, with the photo. In chat give: the
finished size, the woods and board feet, how many bars, units, logs and slices, the saw setups (for
example "every bar is one 60-degree rhombus, blade at 30 degrees"), anything the checks warned
about, and what you chose for them. Keep `design.json` with the plan.

## Changes

Edit `design.json` (pattern params, size, species, options) and rerun; never edit `plan.html`.
Say what moved besides what was asked: a new `side` changes the repeat count and the actual size, a
new wood changes board feet and possibly the warnings.

## Pitfalls

- Bevel accuracy is everything: half a degree off on a 60-degree rhombus opens a gap at every third
  joint across a row. The plan tells the builder to set tilt with a digital gauge and dry-fit a unit
  before ripping all the bars; keep that advice if you rewrite steps.
- A thickness planer destroys end-grain boards. Flatten with a router sled or drum sander.
- Patterns whose rows differ need a log per row type. Before you promise a pattern, check the log count.
- The generators' coordinates are inches, y up; the SVGs flip y. In a `custom` design every polygon
  must be convex (split concave shapes into convex bars) and the slice groups must be what is
  physically crosscut from one log.
