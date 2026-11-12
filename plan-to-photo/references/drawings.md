# Reading a plan from a PDF or images

Use this when the plan arrives as a PDF or as images rather than as a woodworking-plans `plan.js`:
a shop plan PDF, a scan, a phone photo of a magazine page, a screenshot, a hand sketch with
dimensions. (A `plan.js` still goes straight to `export_obj.js`; skip this file.) Many PDFs are pictures of pages with no text layer, so
assume every number is read off an image. The output of this step is two files:

- `takeoff.json`: what the drawing says, copied, with the page each number came from.
- `model.json`: the 3D parts built from it, which `build_model.js` turns into the same kind of OBJ
  `export_obj.js` writes from a plan.js (same object names, same material groups), and checks
  against the takeoff and the drawing's overall size. Everything after the OBJ is the same.

The picture can only be as right as this step, so it is slow on purpose: read, write it down with
its source, model it, and let the checks find the misreadings.

## 1. Pages

```bash
python3 scripts/read_drawings.py plan.pdf drawings/
python3 scripts/read_drawings.py IMG_2041.jpg IMG_2042.jpg drawings/       # photos or scans
python3 scripts/read_drawings.py plan.pdf drawings/ --pages 6,11 --dpi 300 --tile 2   # small dimensions
```

Open `drawings/contact.png` and `drawings/pages.md`. Pages marked full-size tile are patterns
printed at 1:1 across several sheets; skip them for reading and come back only to measure a curve.
Then read the pages that matter at full size, in this order:

1. **Title page and overall dimensions** (W x D x H, the front and side views). Every later number
   has to add up to these.
2. **Parts list / material list / cut list.** Number, name, quantity, T x W x L, material. This is the
   takeoff's backbone. Note which parts are listed as blanks that get shaped (curves, tapers).
3. **Part layouts and elevations.** Notches, slots, tapers, curves, hole spacings, each with its
   dimension chain. Check each chain sums to the overall (1 + 82 + 1 + 1 + 1 = 86).
4. **Sections.** They give what the list never does: heights (slat top below the rail top), which
   face a part sits against, what is under what.
5. **Text, steps, joinery table, review notes.** Positions often live only here: "brackets at 31 to
   35", "cap nuts 1-1/2 from the leg face", "slats 1-1/2 below the rail tops".
6. **Exploded view and photos last,** for what touches what and the finish. Don't scale off them.

For a photo of a printed page: crop and straighten if the text is small (`--tile` helps), and
never measure off a photo unless a known dimension is in the same plane; then say so in `basis`.

## 2. takeoff.json

```json
{
  "units": "in",
  "overall": {"w": 66, "d": 88.25, "h": 44, "from": "p1, p6, p7"},
  "parts": [
    {"id": "2", "name": "Side Rails", "qty": 2, "t": 1, "w": 4, "l": 86, "material": "Walnut, quartersawn", "from": "p3, p12"}
  ],
  "positions": ["Rails centred in the leg slots, tops flush with the leg tops: 9 to 13 (p11, p12)", "..."]
}
```

Convert to inches (decimal; `81-7/8` is 81.875). Use the plan's own part numbers as ids. Copy
material names as written: the OBJ gets one material group per name, and `scene.json` maps them.
`positions` is free text, one line per part or group, saying where it sits and which page says so.
If a number is unreadable or missing, write what you assumed and why; tell the user.

## 3. model.json

Parts in one frame: **inches, origin at the front-left-bottom outside corner, x across the front,
y toward the back (the wall side), z up.** The scene puts the piece against the back wall facing -Y,
so a bed's headboard, a cabinet's back, a desk's modesty panel go at +Y.

```json
{
  "meta": { "title": "Castle Leg Bed", "overall": { "w": 66, "d": 88.25, "h": 44 } },
  "parts": [
    { "id": "2", "name": "Side Rails", "qty": 2, "t": 1, "w": 4, "l": 86, "material": "Walnut, quartersawn",
      "shape": [{ "box": [0, 0, 0, 1, 86, 4] }, { "cut": [-1, 1, 2, 3, 1, 3] }, { "cut": [-1, 84, 2, 3, 1, 3] }],
      "instances": [{ "at": [1, 0, 9] }, { "at": [64, 0, 9] }] }
  ]
}
```

- `shape` is in part coordinates: `box: [x, y, z, dx, dy, dz]` is the blank, `cut` removes a box
  (notches, slots, dadoes, mortises). The blank's sorted size must equal the listed T x W x L.
- Curves and angles cut from the blank, as profiles seen along `axis` (along `y` you draw in (x, z),
  along `x` in (y, z), along `z` in (x, y)):
  - `{ "outline": [[0,0], [66,0], [66,20.75], {"arc": [0,20.75], "rise": 1.5}], "axis": "y" }` keeps
    the inside: an arched top edge. `rise` positive bulges out, negative cuts in. `[u, v, r]` rounds
    a corner between two straight edges; `{"arc": [u,v], "center": [cu,cv]}` for a radius next to a curve.
  - `{ "cutout": [[2.156,-1], [3.1,-1], [3.1,8], [3,8]], "axis": "y" }` removes the inside: a taper
    from 3 at 8" high to 2-1/4 at the floor on the +x face.
  - `lathe` (turned legs), `curve` (through points), `roundover`, `chamfer`: see
    `woodworking-plans/references/modeling.md`, Curves and angles.
- `instances` place copies: `at` moves the part origin, `rot` (degrees about z, around the part
  origin) turns it. Model a corner leg once with its outside corner at the origin and place four
  copies with `rot` 0, 90, 180, 270, rather than four different parts.
- Keep the plan's ids, names and materials. Order copies front-left, front-right, back-left,
  back-right (or front to back) so object names are predictable for `--skip` and dress scripts.
- When the plan gives a rounded spacing that comes from an even division ("16 slats, 2-13/16 apart"
  and the arithmetic is (80 - 32) / 17 = 2.8235), model the even division: that is what the builder
  lays out, and the rounding error otherwise piles up at the far end.
- `meta.basis`: one line per governing size that did not come straight off the drawing (from:
  `reference`, `photo`, `choice`), so the user can see what you decided.

## 4. Build and check

```bash
node scripts/build_model.js model.json model.obj --takeoff takeoff.json
```

It prints the material groups and part list, then checks:

| Check | Catches |
|---|---|
| modelled blank = listed T x W x L, copies = qty | a box typed with the wrong size, a missing copy |
| model = takeoff (size, count, material) | the model drifting from what the drawing says |
| overall extents = `meta.overall` | a part placed past the outline, a wrong origin |
| no two parts in the same space | a misread height or offset (a slat inside a rail) |
| every piece touches another, one assembly | a part floating off its support |

Fix every FAIL before building the scene: decide whether the drawing was misread (fix the takeoff
and the model) or the model was mistyped. Then look at it once from the camera side before dressing
it: the first preview (SKILL.md step 4) with the room materials is enough; compare it to the plan's
exploded view and elevations, part by part.

## What the drawing doesn't say

- **Finish and colour**: from the plan's text (finishing schedule) or the user; otherwise ask once.
- **Hidden faces**: model them as boxes; the camera never sees them.
- **Hardware**: leave it out unless the camera sees it (pulls, hinges on an open door, exposed bolts).
- **Soft goods** (mattress, cushions): the opening sizes come from the model; `dress/bed.py`
  fills the opening.
