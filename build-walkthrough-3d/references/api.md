# build.js reference

A build file is a plain script wrapped so it runs in Node and in the page:

```js
(function(root){
"use strict";
const K = root.Walkthrough.create({units:'in'});          // or {units:'mm'}
const {body, inBody, box, cyl, step, mv, at, HOME, drop, slide, orbit, fmt, BODY} = K;
// constants, parts, fixtures, steps
root.PLAN = K.finish({meta:{ ... }});
})(typeof window!=='undefined'?window:globalThis);
```

Coordinates: x left to right, y front (0) to back, z up from the floor (z = 0). The viewer stands
at −y. Inches by default; `{units:'mm'}` makes every number millimetres and every label read in mm.
The file must not contain the text `</script` (split the string if you need it).

## Bodies and parts

`body(id, label, options)` declares something that moves as one. `inBody(id, fn)` puts the parts made
inside `fn` into it. Ids are short and unique (`'WLfb'`, `'D3f'`); the label is what the step card and
tooltip show.

| option | meaning |
|---|---|
| `parent: 'id'` | part of a sub-assembly; it moves with its parent (declare the parent first) |
| `virtual: true` | a sub-assembly with no parts of its own, only children (a glued-up frame) |
| `pivot: [x,y,z]` | the point it turns about (default: the centre of its parts) |
| `axis: 'x'\|'y'\|'z'` | default axis for `rot` in its poses (default `'y'`) |
| `loose: true` | rests by gravity: the check demands it sits on something |
| `temp: true` | a shop fixture that comes off again: not counted in part totals, excluded from the finished bounds |
| `sizeText: '…'` | replaces the computed size on labels (`'713 × 500 mm footprint'`) |
| `listAs: '…'` | the name the step card groups it under (default: the label without Left/Right) |

`box(name, group, min, max, options)` is a part: an axis-aligned box from `min` to `max` in finished
position. `group` is a free tag for your own use. `cyl(name, group, axis, centre, r, length, options)`
is a cylinder along `axis`; the check treats it as its bounding box.

| part option | meaning |
|---|---|
| `mat` | `'ply'` (default for boxes; Baltic birch faces with ply stripes on every edge), `'pine'`, `'oak'`, `'maple'`, `'walnut'`, `'cherry'`, `'mdf'` (solid wood textures, tinted by `color`), `'steel'` (default for cylinders), `'alu'`, `'zinc'`, `'brass'`, `'blade'`, `'rubber'`, `'black'`, `'paint'` (with `color`) |
| `color: '#hex'` | tint for wood, the finish for `'paint'`, or a flat colour on ply |
| `metal: true` | with `color`: a metallic finish |
| `plyBase: z` | where a ply part's layer stripes start (for a layer cut into pieces, so the stripes line up) |
| `profile: 'ttrack'` | draws the top face as T-track |
| `tape: {zero: x}` | a stick-on tape measure on the top face reading out from `x` (inches) |
| `decal: true` | a printed or routed mark: drawn, never checked, not counted |
| `note: '…'` | replaces the size in the tap-to-measure tooltip (`'Finger pull, 5″ wide'`) |

Model a part as several boxes when it is not a plain block: a routed groove is the material either
side of it plus the thin skin under it; a tenoned rail is the rail with its tenons included. What
matters is that every face that touches another part in the real piece touches it in the model.

## Shop fixtures

| call | meaning |
|---|---|
| `K.table(min, max, name)` | an assembly table: parts can rest on its top; moves must avoid it |
| `K.obstacle(min, max, name)` | any other fixed thing moves must avoid, drawn as a dark block |
| `K.pendant(x, y, z)` | a pendant light with its shade bottom at `z`; moves must avoid it. If you add none, a row is hung over the piece and one over each table |

The room is sized around the piece and the tables: the workbench, lumber rack, table saw and window
are placed against its walls. Put tables in front of and to the left of the piece (negative x and y),
as in the examples, so they sit clear of the shop dressing.

## Steps and moves

`step({key, title, text, cam, sheet, intro})` starts a step; every `mv` after it belongs to it.
The first step must have `intro: true`: the overview, which shows the finished piece. `sheet` is the
drawing sheet shown as a badge (`'B-101'`, or `'Shop'` for a fixture step). `key` is a stable name
for your own reference.

`cam: orbit(target, azimuth, elevation, distance)`: look at `target` from `azimuth` degrees (0 =
straight in from the front, positive from the right, 180 from behind), `elevation` degrees up, from
`distance` away. Frame what moves; narrower screens step back automatically.

`mv(id, path, {delay, dur, remove, seg})` moves a body along `path`, a list of poses relative to its
finished place. The body appears at the first pose and ends at the last. A body's first move brings
it in; later moves (in later steps) move it again, and its last pose stays until then.

| pose helper | meaning |
|---|---|
| `HOME` | its finished place |
| `at(dx, dy, dz)` | offset from its finished place |
| `{off:[dx,dy,dz], rot:deg, axis:'x'\|'y'\|'z'}` | offset plus a turn about its pivot |
| `drop(h)` | `[at(0,0,h), HOME]`: lowered in from `h` above |
| `slide(dx, dy, dz)` | `[at(dx,dy,dz), HOME]`: pushed in from that offset |

| move option | meaning |
|---|---|
| `delay` | seconds after the step starts (stagger repeated parts by 0.1–0.3) |
| `dur` | seconds the move takes (default 1.3) |
| `remove: true` | the body fades out at the end (a fixture coming off) |
| `seg: [..]` | for a path with several legs, the share of the time each leg takes (sums to 1) |

Children of a virtual body can have their own moves (each piece of a frame dropping onto the
table), with poses in the parent's frame. When the parent is turned (lying flat), an offset meant
as "straight down in the world" has to be rotated into the parent's frame first: the miter station's
`frameLocal` does this.

## finish

`K.finish({meta})` totals the steps, adds default lights, and returns the `PLAN` object.

| meta | meaning |
|---|---|
| `title` | the piece's name: page title and header |
| `eyebrow` | small line above it (`'Step-by-step build · Rev A'`) |
| `thing` | what it is called in sentences (`'bench'`: "Finished bench") |
| `intro` | first paragraph of the About panel |
| `about` | `[['Overall','96″ L × 26″ D × 36″ H'], …]` facts in the About panel |
| `links` | `[['Open the drawing set', url], …]` links in the About panel |
| `loading` | the line under "Opening the shop" while it loads |
| `sheetLabel` | word before a step's sheet (`'Sheet'` → "Sheet B-101") |
| `rev` | revision shown on the drawing pinned to the shop wall |
| `listStrip` | regex source for prefixes dropped when grouping a step's parts (default `'^(Left\|Right) '`) |
| `pendants: false` | no default lights |

## What the check proves

For every step, sampled along every move (`verify.js`, 40 samples by default):

- **collision**: a moving part's box overlaps a part already there (or another moving part).
- **floor / static**: a moving part goes below the floor or through a table, obstacle or light.

At the end of every step:

- **floating**: some group of parts touches nothing that reaches the floor or a table.
- **no-contact**: a part placed this step touches nothing.
- **unsupported**: a `loose` part (or a whole sub-assembly) has nothing directly under it.

When the piece is finished:

- **final-overlap**: two parts share volume.
- **never-placed**: a part no step brings in.

Parts of one sub-assembly that sit still are not tested against each other while it moves. Contact
means faces within 0.0001″ (0.0025 mm), so model parts exactly where they sit: a part 1/64″ off its
neighbour floats. Gravity is checked as "something under it", not balance: a tall part standing on
its edge passes, so say in the step text what holds it (a clamp, a square, the stand cheeks).
