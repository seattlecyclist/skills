---
name: end-grain-boards
description: Design end-grain cutting boards with geometric patterns (3D tumbling blocks or cubes, six-point and eight-point LeMoyne stars, snowflakes, geodesic domes, kagome star lattice, hexagon-square-triangle rosettes, checkerboard, brick, or any custom pattern of convex pieces) from a described pattern and wood species, and produce a checked shop plan with a material list in board feet, a cut list with exact bar sizes and blade tilts, step-by-step rip, glue-up, crosscut and re-glue instructions, SVG diagrams of every stage, and a photorealistic render through plan-to-photo. Use whenever the user wants a cutting board or butcher block pattern, asks how to make a 3D or star or checkerboard end grain board, gives a pattern and woods ("tumbling blocks in maple, cherry and walnut"), wants a cut list or glue-up sequence for a board, or asks to change the pattern, size, piece size or species of an existing board plan.
---

# End-grain boards

Turn "repeating 3D cubes in maple, cherry and walnut" into a plan a woodworker can build from and a
photo of the finished board. The board face is the truth: every piece is a convex polygon, the
script proves the pieces tile the board, and every list, drawing and step is derived from it.

```
brief → design.json → cbplan.py (checks, plan, diagrams, guide image) → read checks + look → render → deliver
```

**How every board here is built.** An end-grain face is the cut end of a log. Each polygon on the
face is a long *bar* of that cross-section, ripped on the table saw. Bars are glued three or four at a
time into a small closed *log*: a triangle for 60 degree patterns (glued in a V block whose sides stop
3/16" under the top of the log), a rectangle for 45 and 90 degree patterns (bands, then quarter logs in
corner cauls). **Every face of every log is
machined flat** before anything else is glued to it. The long logs are then glued side by side into
*planks*: a plank is one row of the board made long. Planks are planed (they are long grain), crosscut
into *rows*, and the rows are glued into the board, which is flattened and then trimmed. **No row is
ever assembled from loose slices.** `scripts/planks.py` finds which rows can come off the same plank
(as cut, turned end for end, turned over, or slid along), so a repeating pattern needs one or two
planks. A pattern whose rows do not repeat needs a plank per row and the checks say so: prefer
patterns that repeat row to row. An optional *frame* of end-grain blocks is glued round the trimmed
field. Every truing pass takes a skim, so the plan lays the pattern out at the trued sizes, not the drawn ones. `scripts/logs.py` works this out from the face: it lays the
pattern's log grid over it, merges same-wood neighbours into single bars, finds which cells are the
same log turned or flipped, and orders each log's glue-ups in flat layers.

`maze` is a plank build (`scripts/twoply.py`): nothing is assembled from small pieces. Long two-ply blanks are ripped into
slabs, slabs are stacked into square logs, logs are glued into one plank, and every row is a crosscut slice of
that plank. Prefer this shape of build wherever a pattern allows it: long glued planks, rows cut from the plank.

One board is the exception: `cubes` (tumbling blocks) is built the way makers build it, three diamond
bars taped into a hexagon log, the logs sliced into pucks and all the pucks glued at once in a clamped
frame. Its logs are not machined, so its plan stresses one-setup bars and keeps a gap-filling step.

Never plan a glue-up whose outside is a zigzag or V-groove (rows of hexagons, nested units): those
faces cannot be machined, squeeze-out stays in them and the next joint gaps. `references/technique.md`
has the rules and the reasons.

| Path | What it is |
|---|---|
| `scripts/cbplan.py` | `design.json` → `out/`: `plan.html`, `plan.json`, `svg/*.svg`, `board.obj`, `guide.png`, `spec.md`, `room.md`. Exit 1 if a check fails. |
| `scripts/logs.py` | The build: face + log grid → log types (bars, glue-up stages, jig), slices with their orientation, rows. Triangle logs (one or two levels), square star blocks, strip panels. |
| `scripts/planks.py` | Groups the rows into planks: which rows are the same sequence of logs as cut, turned or slid along, and the end view of each plank. |
| `scripts/twoply.py` | The plank build, used by `maze`: a two-ply blank, slabs ripped off it at 45 degrees, four slabs to a square log, logs glued into one plank, rows crosscut from the plank. Its own checks, drawings and plan sheets (pattern, blanks & slabs, plank & rows, flattening & border, sources). |
| `scripts/patterns.py` | The pattern generators (`cubes`, `stars6`, `snowflakes`, `stars8`, `geodomes`, `kagome`, `pinwheel`, `chevrons`, `gems`, `ziggurat`, `ribbons`, `notched`, `checker`, `brick`; `rosettes` draws but has no sound build) and the polygon format for `custom`. Each returns its log grid as `cells`. |
| `scripts/drawings.py` | Every drawing: face, slice layout, bar sections and rip setups, each log's end view in its jig glue-up by glue-up, 3D exploded logs, jigs, crosscut, row jig, board glue-up, trim. |
| `scripts/species.py` | Cutting-board woods: end-grain colour, Janka, shrinkage, notes; the woods to refuse. |
| `scripts/plan_page.py` | The plan page: numbered sheets (overview, material list, bars & rip setups, logs, slice layout, building it) with title blocks, then the checks. Warm paper, Archivo / Source Serif 4 / IBM Plex Mono, walnut accent, light and dark. Change the look here, not in cbplan. |
| `scripts/assembly.py` | `Scene`: the small 3D drawing engine behind the exploded views (solid parts in their woods, glue faces blue, orange clamp arrows, circled labels, grain arrow, red cut lines). |
| `scripts/render_guide.py` | The colour-coded perspective of the board (called by cbplan; rerun with another `--az/--el`). |
| `scripts/selftest.py` | Proves every example passes and the checks catch an overlap, a gap, a bevel past 45 degrees, a bad wood and an unbuildable pattern. |
| `references/patterns.md` | Each pattern's geometry and parameters, and how to write a `custom` design. **Read for anything not in the generators.** |
| `references/technique.md` | The five rules, ripping, triangle and square logs, jigs, crosscutting, rows, flattening, finishing. **Read before writing advice the plan doesn't already give.** |
| `references/species.md` | Choosing and pairing woods. |
| `examples/` | Fourteen worked boards: `tumbling-blocks`, `six-point-stars`, `snowflakes`, `lemoyne-stars`, `checkerboard`, three expert ones, `geodesic-domes`, `kagome-stars`, `pinwheel-rosettes`, `two-wood-maze` (the plank build), and five expert-plus ones, `pinwheel-chevrons`, `faceted-gems`, `ziggurat`, `folded-ribbons`, `notched-cubes`; each with `design.json`, `plan.html`, `guide.jpg` and (all but the checkerboard) `photo.jpg`. |

**Needs** Python 3 with numpy and Pillow. The render uses the `plan-to-photo` skill
(`plan-to-photo/scripts/nano_banana.py`, needs `GEMINI_API_KEY`); look for it beside this skill, in
`~/.claude/skills/plan-to-photo`, or in https://github.com/seattlecyclist/skills. If `scripts/` is
missing, the full skill is in `end-grain-boards/` of that repo.

## 1. Brief

Get, or ask once for only what you cannot infer:
- **Pattern.** Map the user's words to a generator: cubes, 3D boxes, tumbling blocks → `cubes`; pinwheels, chevron chains → `chevrons`; cut gems, faceted hexagons → `gems`; stepped pyramid, concentric hexagons → `ziggurat`; pleats, folded ribbons → `ribbons`; cubes with a notch → `notched`; a two-wood maze of stepped bars that seem to weave (Stammherz's "just 2 woods" board) → `maze` (roles light, dark; `params.bar` is the bar width, 1/2" by default, and the tile is four bars square);
  stars, Star of David, hexagram → `stars6`; snowflakes → `snowflakes`; eight-point, quilt or LeMoyne star, compass star →
  `stars8`; checkerboard → `checker`; brick, running bond, offset → `brick`; geodesic, domes, triangulated
  spheres → `geodomes`; kagome, trihexagonal, triaxial weave, star lattice → `kagome`; rosettes, hexagons ringed
  by other pieces → `pinwheel` (the hexagon-square-triangle rosette, `rosettes`, has no sound build; say so and offer `pinwheel`). Anything else (chevrons,
  hexagons, diamonds, a logo-like motif) → `custom` polygons (`references/patterns.md`). Say which you chose.
- **Woods**, one per role the pattern has (`cubes`: lid, left, right; `stars6`: star, field; `snowflakes`: flake, field; `stars8`:
  star_a, star_b, field; `geodomes`: tone1 (lightest) to tone4 (darkest); `kagome`: hex, up, down;
  `pinwheel`: hex, diamond, tri; `checker` and `brick`: a, b). For 3D effects, light-medium-dark
  matters more than the species: maple / cherry / walnut is the classic. Fill gaps from
  `references/species.md` and say so. Refuse red oak, softwoods, spalted wood, cocobolo (it explains why).
- **Size.** Default 12 x 16 x 1-1/2". Generators fit whole repeats, so the finished size moves to the
  nearest repeat; report the actual size. Piece size (`side`) sets how busy it looks, and the log it
  makes must pass under the saw (2-5/8" tall): cube and star diamonds up to 1", kagome and pinwheel 3/4", LeMoyne 3/4".
- **Frame (optional add-on).** The base design has no frame or border: the pattern runs to the edge,
  and the trim is placed between motifs or on their line of symmetry so opposite edges match. Add
  `"frame": {"width": 1.0, "species": "walnut"}` (with an optional `liner`) only when the user asks for
  a border; it puts a plain end-grain frame round the field and the finished size includes it. You may
  offer it, but never add it on your own. Never a long-grain frame.
- **Whole motifs.** `stars6` and `snowflakes` leave out any star or flake the trim would cut through
  (`"whole_motifs": false` turns this off). Check the face: what is left should be a symmetric group.
- **Extras:** edge treatment, feet, juice groove, handles (`options`), and the setting for the photo.

## 2. design.json

```json
{
  "name": "Tumbling Blocks End-Grain Board",
  "description": "3D tumbling blocks: a honeycomb of cubes seen corner-on, maple lids over cherry and walnut sides",
  "pattern": "cubes",
  "params": {"side": 1.5},
  "board": {"width": 12, "length": 16, "thickness": 1.5},
  "species": {"lid": "maple", "left": "cherry", "right": "walnut"},
  "options": {"edge": "1/8\" chamfer", "feet": true, "juice_groove": false, "handles": false},
  "shop": {"kerf": 0.125, "max_log_length": 24, "stock_width": 5.5},
  "render": {"room": "optional room brief for the photo"}
}
```

`description` is used word for word in the render prompt, so describe what a viewer sees. `shop`
defaults: kerf 1/8", slices cut 1/8" over finished thickness, 3/4" waste at each log end, logs at
most 24" (longer ones are split), blanks 5-1/2" wide with the last 1-1/2" not ripped, bars ripped 1/32" over,
0.01" allowed for each truing pass (`true_skim`), 1/8" cleaned off every board edge, the last 2" of a log held and not sliced, saw clearance 3-1/8" over a 1/2" sled, drum sander opening 3". Generator `params`
are in `references/patterns.md` (`rows`/`cols` override the fit).

## 3. Build and check

```bash
python3 scripts/cbplan.py design.json out/
```

It prints the actual size, every bar shape with its blade tilt, each log (count, length, slices) and
the board feet per species, then the checks: species hard enough (Janka 900+), pieces convex, **no
overlaps and no gaps**, slices cover the board, every log's parts fill its section, every bar has a
table-saw setup with a bevel of 45 degrees or less, every sliced log fits under the saw, no glue-up has
more than four parts, at least 1/8" to trim on every edge, board 1" or thicker; warnings for small bars,
many log types, species that move differently and boards large for their thickness. A FAIL is a design
error: fix the design (usually `side` or `levels`), never the plan text. Explain any WARN to the user.

Then look at `plan.html`:
- **Face** (sheet 01): does it read as what the user described? Contrast between roles is the usual
  problem (two mid-browns merge; a dark wood on the largest pieces takes over). Is the crop balanced
  and the same on opposite edges? Are motifs whole? If not, change `side` or move the size so the trim lands on a line of symmetry; a frame is the user's choice, not a fix.
- **Logs** (sheet 04): every glue-up is drawn as it sits in the jig. Each should be flat layers, tip
  down, with a flat top for the caul. Count the log types; over six, try `levels`, another `side` or
  a simpler variant and say why.
- **Planks & rows** (sheet 05): each plank's end view, letters, reference marks and primes must be legible; the row table says which plank each row comes from and how it is turned.
- **Jigs** (sheet 06, step 2): one V block per size and height of part. More than four blocks means many
  small bar shapes; a larger `side` or fewer roles usually removes some.
- **Steps** (sheet 06): a builder who cannot picture a glue-up builds from the drawings beside the steps.

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
finished size, the woods and board feet, how many bars, logs, slices and rows, the saw setups (for
example "two bar shapes, both with the blade at 30 degrees"), the jigs to make, anything the checks warned
about, and what you chose for them. Keep `design.json` with the plan.

## Changes

Edit `design.json` (pattern params, size, species, options) and rerun; never edit `plan.html`.
Say what moved besides what was asked: a new `side` changes the repeat count and the actual size, a
new wood changes board feet and possibly the warnings.

## Pitfalls

- Bevel accuracy is everything: half a degree off on a 60 degree bar opens a gap in every log. The
  plan has the builder set tilt with a digital gauge and dry-fit three scrap bars; keep that advice.
- The faces glued when logs become planks and rows become the board are long grain (the sides of the
  logs). Never tell the builder to size them or double-coat them as end grain.
- The plan's trim margins are measured from the deepest notch of a ragged edge to the cut, at the trued
  sizes. If you change `true_skim`, the margins and the finished size move with it.
- Flatten, then trim. A thickness planer destroys end-grain boards; so does a jointer on a row's edge. Planks are planed before they are crosscut, while they are still long grain.
- A log taller than 2-5/8" does not pass under a 10" saw on a sled. Shrink `side` before promising a size.
- Same-wood glue lines disappear in end grain, so the build may cut a piece in two or merge two
  pieces into one bar; the face drawing shows the pieces as built.
- The generators' coordinates are inches, y up; the SVGs flip y. In a `custom` design every polygon
  must be convex.
