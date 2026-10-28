---
name: woodworking-plans
description: Design woodworking projects and publish them as magazine-style shop plans (numbered exploded view, material and hardware lists, shopping list, shop cut list, dimensioned part layouts, section views, joinery details, cutting diagrams with cut order, jigs, full-size patterns and story sticks, build steps, finishing schedule) rendered as an interactive HTML page with a 3D exploded view, pan and zoom drawings, and assembly step-through. Every design and every later change gets an adversarial review that re-checks dimensions, joinery and how each part connects to its neighbours. Use whenever the user wants furniture, cabinets, shop fixtures, beds, tables, benches, shelves, boxes or jigs designed, wants a cut list or build plan, asks to change a dimension, joint, material or part on an existing plan, or says things like "draw me plans for", "how would I build", "make it 6 inches wider", or "use mortise and tenon instead".
---

# Woodworking plans

Turn a project idea into a plan a woodworker can build from, in the look of a classic woodworking-magazine
drawings supplement, with an interactive 3D exploded view and a printable PDF. The model is the
plan: you write a parametric `plan.js`, the scripts prove it fits, and the page renders from it.

```
scripts/build_plan.js    --validate, --check, --review, and build: plan.js → page.html
scripts/joints.js        joint helpers (J.castle, J.mortiseTenon, J.dado …) that cut and size joinery
scripts/render_check.js  screenshots, PDF test and a problem list, in one command
scripts/selftest.js      the checks must catch known breaks
examples/skeleton/plan.js    START HERE: a 4 KB side table using every part of the schema
examples/castle-bed/plan.js  a full worked example (castle-joint queen bed, Rev D)
examples/modern-dresser/plan.js  casework: an 8-drawer plywood dresser with slides and full drawer boxes
examples/round-table/plan.js     curves and angles: a turned round top, tapered legs, arched aprons
examples/wall-cabinet/plan.js    doors: a frameless wall cabinet, a pair of overlay doors on Blum hinges
references/plan-schema.md    every field, the J helpers, bores        (read when writing plan.js)
references/joinery.md        proportions and rules of thumb             (read when choosing joints)
references/drawers.md        slides, box, front and pull sizing          (read for any plan with drawers)
references/doors.md          door sizes, reveals, hinges, cups, pulls    (read for any plan with doors)
references/adversarial-review.md  review procedure and record format    (read for every review)
references/modeling.md       joints the helpers don't cover             (read only when needed)
references/style-guide.md    the page's look, sampled colours, voice    (read only to change the template)
```

If `scripts/` is missing (the skill was installed from this file alone), the full skill is in
`woodworking-plans/` of https://github.com/seattlecyclist/skills. Use that copy; this file and the
saved skill are kept in step.

## 1. Brief

Get, or ask once for: the governing constraint (overall size, or what it holds or fits), wood and
stock, any joinery the user named (a requirement, not a suggestion), and whether it must knock down
(beds and big tables: yes). Pick tools, finish and skill level yourself and say so.

Note where each governing size comes from as you go: the builder's words, their reference (a plan,
PDF or drawing), a photo (an estimate: say what you scaled it from, such as a 30" table beside it)
or your own choice. It goes in `meta.basis`, and anything you changed from their
reference goes in `meta.changed` with the reason; the page shows both, so the builder knows which
numbers to measure before buying wood.

## 2. Design

Decide the visual idea in one sentence, the load path joint by joint (every load ends in bearing on
wood or the floor), the joint for each connection from `joinery.md`, knock-down hardware, wood
movement (nothing glued across a solid panel wider than about 6"), and the assemblies, which become
`sections` (each gets its own exploded view over its Material List).

## 3. Write plan.js

Copy `examples/skeleton/plan.js`. Every driving number goes in `PARAMS`; derive the rest.

- Units are inches; x is width, y depth (the viewer stands at −y), z up.
- Each part is one plain `box` per piece, placed by `instances` where it sits in the assembly.
  Mirror copies that face the other way (`mirror: 'x'`).
- Shape anything that is not square with a shape entry on the part, never with stacked boxes or
  stair-step cuts: `outline` for arched or curved edges, round and oval tops and tapers,
  `cutout` for mitres, bevels, coves and curved cutouts, `lathe` for turned legs and round tops
  with an edge profile, `splay` for legs splayed one or both ways, `roundover` and `chamfer` for
  eased edges (`ease` on an outline for a round-over that follows a curve). The box is the blank;
  the shape is what you saw, rout or turn from it. See `modeling.md` (Curves and angles). A builder who
  says the curve looks like steps is right: there is no resolution to raise; use a shape. The
  drawings and cut list give every angle in degrees and every radius (with its rise or centre)
  from the model; pick round, settable numbers and repeat them in the step that cuts them.
- Make every connection with a helper (`J.castle`, `J.mortiseTenon`, `J.halfLap`, `J.bridle`,
  `J.dado`, `J.groove`, `J.rabbet`, or `J.joint(type, parts)` for screws, brackets, resting parts).
  It cuts the joinery, sets the tenoned part's length and returns the joint record. Every joint
  needs both halves in the model: a tenon and its mortise (cut for you from the tenon), a dado,
  groove, rabbet, slot or lap and the part that fills it, a dowel joint and its bores. The check
  fails a joint whose mating half is missing. Defaults follow
  `joinery.md`; pass a size only to depart from them, and say why.
- Model every bolt, nut, screw and peg in `bores`, so the check can prove each hole can be drilled,
  stays in the wood, that bolts reach their nuts, and that no two holes meet. Screws that hold a
  hardware flange (slides, hinges) start on the wood face with `hardware: true`.
- Drawers: read `drawers.md`. Choose the slide first (ask the builder, or use `accuride-3832`
  and say so), then size every box from the opening and that slide's spec sheet with
  `C.drawerSize`: side-mount width = opening minus two clearances aimed mid-window, undermount
  inside width = opening minus the maker's deduction with the sides in its range, the bottom
  recess and rear notches it needs, box length = slide length (NL), and the longest slide the
  case depth allows. Model the slides as hardware parts in their real place (1/8" back from the
  front; front thickness + 1/8" on inset drawers); each box as sides, front and back, bottom;
  fronts as their own section. Model box stock at its real thickness (12 mm Baltic birch is
  15/32"), because the box width is built up from it and slides tolerate about 1/32". Declare
  every opening in `drawers` (plan-schema.md) with its slide, box, slide and front parts and the
  pull: the check proves each box against the slide and the page prints the Drawer Breakout.
  List the slides by maker and model with length and pair count, the pulls with their screws, and
  the front-mounting screws in `hardware`. The dresser example shows the whole pattern, including
  staggered slide screws on a shared divider.
- Doors: read `doors.md`. Settle the cabinet (frameless or face frame) and the style (full overlay,
  half overlay, face-frame overlay, inset) first, then the hinge (ask the builder, or use
  `blum-clip-top-110` and say so), then size each door with `C.doorSize`: frameless full overlay
  = case width − 2 × reveal (1/16" or 1/8"), pairs split it less a 1/8" gap (4 mm on solid wood),
  inset = opening − 2 × gap. Get the cup distance and plate that give that overlay from
  `C.hingeSetup` (overlay = k + cup distance − plate, in mm, from the maker's sheet); a door the
  hinge cannot reach is wrong, not something to adjust out. Count hinges by height and weight (2 to
  36" and 20 lb, 3 to 60", 4 to 84"), 3"–4" from the ends. Model the doors, the hinges as hardware
  parts on the hinge edge, and the 35 mm cup bores at the maker's depth in `bores`. Declare every
  opening in `doors` (plan-schema.md): the check proves each door against its hinge and the page
  prints the Door Breakout. List the hinges by maker and model with their plates, and the pulls with
  their screws. The wall cabinet example shows the whole pattern.
- Leave `explode` and `callout` out; they are worked out from the joints. Set them only to fix a
  view the render check shows is wrong (including a "balloon leaders cross" warning that reads badly). Drawers are the exception: auto explode lifts parts out of
  their grooves, so set boxes, slides and fronts by hand to come out the front (the dresser does).
- Number parts in build order across sections; write `steps` in build order with the parts each adds.
- `materials` colours are illustration tints, yellow to gold (maple about `#f2e38a`), not photo-real wood.

Then the shop paperwork. The page already derives the shopping list, tools list, shop cut list,
sheet cut order, grain arrows and actual-size fasteners from the model; add what only you know:

- `view.sections`: a Section A–A wherever a joint or profile is hidden from the outside views.
- `story_sticks`: one for any repeated heights or spacings (headboards, drawer banks, shelves).
- `pattern: true` on any part with a curve, or a `details` drawing with `pattern: true`, for
  anything better traced than measured; they print at 100%.
- `jigs`: every jig, fence or template a step relies on, drawn with its parts.
- `steps[].wrong`: a "Don't" at the step people most often get wrong (glue where it must move,
  the wrong face up, a cut that can't be undone). One or two per plan, not one per step.
- `finish`: the finishing schedule, step by step with dry times.

## 4. Validate and check

```
node scripts/build_plan.js plan.js --check
```

It validates the plan against the schema, then proves from the geometry that the cut list matches,
nothing overlaps, tenons seat in mortises cut to match, every joint has both halves, joints touch, the assembly connects, walls and towers are thick
enough, cuts suit their tools, and every bore can be drilled and its fastener reaches. Fix every
error; fix or explain every warning. It knows geometry, not strength: that is the review's job.

## 5. Adversarial review: the first design and every change

```
node scripts/build_plan.js plan.js --review [--base plan.prev.js]
```

The worksheet gives each change's touched parts, mates, what moved since `plan.prev.js`, the
paperwork to re-read, and a record skeleton. Follow `references/adversarial-review.md`: attack every
line, re-derive numbers by hand from `PARAMS`, and fill the evidence with numbers and part numbers.
With a subagent tool, give a fresh reviewer the worksheet, check output and `plan.js` (prompt in the
reference) and verify what it finds. Fix, re-check, repeat. Record only what happened: never invent
a finding or mark a line `pass` unchecked. The verdict is the worst line; validation rejects TODOs.

## 6. Build, look, deliver

```
node scripts/build_plan.js plan.js page.html --artifact     # body only, for the Artifact tool
node scripts/render_check.js plan.js --out check --pdf      # add --libs <node_modules> if offline
```

It reports page errors, broken drawings, overlapping balloons, missing section views, phone
overflow, collisions at full explode and PDF failures, and warns (without failing) when balloon
leaders cross: keep leaders from crossing where you can, in authored `details` too, but one
crossing beats a balloon stranded far from its part (the PDF ends with the full-size pages, tiled
at 100%). Look once at `check/viewer.png` and the
`plate-*.png` views: every joint readable, balloons next to their parts. The page loads three.js
0.160.0 from jsDelivr and fonts from Google Fonts (and, for the PDF link, html2canvas 1.4.1 and
jsPDF 2.5.1 from jsDelivr); everything else is inline.

Publish as an Artifact with `capabilities: {downloads: true}` (the Printable PDF link needs it), and
republish changes to the same URL. In chat give the overall size, the joinery in a sentence, what
the review found and fixed, and anything left for the user to decide. Keep `plan.js` with the page.

## Changes to an existing plan

Copy `plan.js` to `plan.prev.js`, change `PARAMS` (never derived numbers), bump `meta.rev`, add a
`revisions` entry with one change id per requested change and a reason, then check, review with
`--base plan.prev.js`, rebuild and republish. Tell the user what moved besides what they asked for.

## Changes to the skill itself

Update the repo's SKILL.md, run `node scripts/selftest.js`, push, and propose the same full
SKILL.md as an update to the user's saved skill. Compare any change to the look against the
reference PDF pages, not memory.

## Style

The template already draws the magazine look (`style-guide.md` has it page by page). Write steps
short and imperative, and say why when it isn't obvious ("pare the slot bottoms flat; the rails
bear on them").
