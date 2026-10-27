# Plan object

`plan.js` exports `build(PARAMS, J)` returning this object (or the object itself); `plan.json`
works too. The scripts pass `J`, the joint helpers in `scripts/joints.js` (below). Lengths accept
numbers (inches) or strings: `23.75`, `"23-3/4"`, `"3/4"`, `"18mm"`. `--validate` checks every field
here and warns on unknown keys.

```js
{
  meta: {
    series: 'Shop Plan', plan_no: '014', rev: 'B', date: 'Oct 2026',
    title: 'Castle Joint Bed',                       // page title and masthead
    subtitle: 'Queen platform frame with slatted headboard',
    overall: { w, d, h },                            // checked against the model (x, y, z extents)
    wood: 'White oak & poplar', skill: 'Intermediate', time: '3 weekends',
    intro: ['paragraph', 'paragraph'],               // {#id} renders a part chip
    needs: ['tool or supply', ...],                  // lumber lines are added automatically
    basis: [{ what: 'Seat height 18"', from: 'photo',  // where each governing size came from: 'you' (the
              note: 'Scaled from the 30" table beside it' }],  //   builder said it), 'reference' (their plan, PDF
                                                     //   or drawing), 'photo' (estimated from a photo; say what
                                                     //   it was scaled from in note) or 'choice' (yours)
    changed: [{ what: 'Mortise and tenon for pocket screws', why: 'Stronger, and you named it' }],  // departures from their reference
    check: { min_wall: 0.25, tol: 1/64, bore_wall: 1/8 },  // optional check settings
    tools: { dado: 2.5 },                            // optional: how deep each tool cuts (overrides)
    toolkit: ['Spokeshave']                          // extra tools for the list; false hides the derived list
  },
  materials: { wood: { color: '#efcf78' }, poplar: { color: '#f4ec9e' }, hardware: { color: '#c5c2be' } },  // illustration tints, yellow to gold
  // one Material List sheet per section, headed by that section's own exploded view;
  // view: a preset name ('Front right', 'Front left', 'Rear', 'Top', 'Front') to draw it from
  sections: [{ id: 'frame', title: 'Bed Frame' }, { id: 'head', title: 'Headboard', view: 'Front right' }],
  parts: [ Part, ... ],
  cutlist_notes: ['line', ...],
  joints: [ Joint, ... ],                            // usually from the J helpers
  bores: [ Bore, ... ],
  hardware: [{ item, qty, source, note, part,        // part: id to highlight on click
               draw: { shape: 'screw', d: 0.164, len: 1.25 } }],   // optional: add it to Fasteners, Actual Size
  details: [ Detail, ... ],
  details_intro: 'optional paragraph above the details',
  view: {
    explode: 100,                                    // initial explode, 0-100
    start: 'Front right',                            // initial preset
    presets: { 'Under': [0.4, -1, -0.6] },           // extra camera directions
    hint: 'text shown in the viewer corner',
    elevations: ['front', 'side', 'top'],
    dims: { front: [{ a: [x, z], b: [x, z], off: 2, text }] },   // extra elevation dimensions
    labels: { front: [{ at: [x, z], text, anchor }] },
    sections: [{ id: 'A', cut: 'y', at: 40, keep: '+', title, on: 'side' }]   // section views (below)
  },
  stock: { sheet: { w: 48, l: 96, kerf: 0.125 }, board: { w: 7.25, l: 96, kerf: 0.125 },
           boards: { '1-3/4': { w: 9.25 } },        // per-thickness board size overrides
           sheets: { 'Baltic birch': { w: 60, l: 60 } },   // per-material sheet sizes (key = part material)
           spare: 0.2, buy: 'dimensional' },          // shopping list: board spares; name boards 1x8, 2x4 …
  cutting_note: 'text above the cutting diagrams',
  steps: [{ title, text, parts: ['1', '8'],          // parts added at this step (assembly mode)
             wrong: 'glue the laps; the bed has to come apart' }],   // optional "Don't" panel (or { text, items, w, h })
  jigs: [ Jig, ... ],                                // Shop Aids sheet
  story_sticks: [{ title, axis: 'z', parts: ['8', '9'], marks: [{ at, label }], from, to, note }],
  finish: { title, note, steps: [{ step, product, method, dry, note }] },
  revisions: [{ rev, date, summary, changes: [{ id, summary, parts, reason }] }],
  review: [{ rev, change, verdict, mates, checks: [{ check, evidence, result }] }]
}
```

Every change id needs a `review` entry; `result` is `pass`, `fixed`, `flag` or `fail`, and the
`verdict` must be the worst line (fail, flag, fixed, pass). Evidence may not say TODO.

## Joint helpers (`J`)

Model each part as one plain box per piece, placed where it sits, then call one helper per
connection. Helpers take part objects (not ids), change them in place, and return the joint record.
Every option below is optional except the parts; `title`, `glue`, `fasteners`, `note`, `explode`,
`id` pass through to the record (ids default to J1, J2 … in order).

| Helper | Model the parts | It does | Defaults |
|---|---|---|---|
| `J.castle({ post, lower, upper, tool })` | both rails at full height, crossing in the post | half-laps the rails (lower keeps its bottom half), slots the post for both | tool `bandsaw` |
| `J.halfLap({ lower, upper, axis })` | crossing at full thickness | half of the crossing out of each | axis z |
| `J.mortiseTenon({ rail, hosts, thick, length, shoulder, twin, offset, type })` | rail shoulder to shoulder, touching the hosts end-on | tenons at each touching end, sets `rail.l` | thick ≈ 1/3 stock (nearest chisel), length 2/3 of the host up to 1-1/2" (min 3/4"), edge shoulders 1/2" (1/4" under 3"), twins when wider than 5× thick (`twin: false` to refuse, a number for the twin width) |
| `J.bridle({ post, rail, tool })` | rail through the post top | open slot in the post | |
| `J.dado / J.groove / J.rabbet({ host, guest, depth, tool })` | guest touching the host's face | grows the guest into the host by `depth` and cuts the housing; updates `l` (or `w`) | 1/3 of the host (3/8" in 3/4" sheet); rabbet 1/2 |
| `J.housing({ host, guest, type })` | guest overlapping the host | cuts the overlap out of the host | |
| `J.joint(type, parts, opts)` | | record only (screwed, rests, bracket, bed-bolt, buttons …) | |

A cut that reaches a face runs 1" past it so the slot opens cleanly. The copies of one part must all
need the same cut; mirror copies that face the other way, or the helper throws.

## Bore

Bolts, nuts, screws, pegs and plain holes, in world coordinates. The check walks each one.

```js
{
  id: 'B1', joint: 'J1', kind: 'bolt' | 'screw' | 'cross-dowel' | 'peg' | 'hole', label: 'cross-bolt',
  at: [x, y, z], dir: '-z',          // entry point on the surface, drilling direction (+x -x +y -y +z -z)
  d: 5/16, depth: 8.625,              // bore diameter and depth from the entry (screws: len)
  len: 8,                             // fastener length, from the counterbore bottom
  counterbore: { d: 1, depth: 0.625 }, washer: 0.875,
  nut: 'B2',                          // bolt: the cross-dowel bore it threads into
  bit: 12,                            // drill reach (or meta.tools.drill)
  access: 1,                          // clear space needed outside the entry once assembled (0 = none)
  through: false,                     // allowed to exit the far face
  hardware: true,                     // screw: holds a thin hardware flange (slide, hinge, bracket) lying
                                      // on the entry face, so the 2–3× rule is skipped; model `at` on the wood
  cross: ['B7'],                      // bores this one is meant to meet (a nut's bolt is implied)
  copies: [{ at, dir }, ...],         // the same bore at several places (keys B1.1, B1.2 …)
  qty: 24                             // total in the build when copies only sample them (Fasteners, Actual Size)
}
```

The check reports a bore whose entry is covered once assembled (`bore-blocked`), that crosses or
exits into air, that leaves less than `bore_wall` of wood around it, that is deeper than the bit, a
counterbore too small for washer + socket, a screw outside 2–3× the part it holds or longer than the
wood, a bolt that misses its nut, stops short of its far side, or is longer than its hole, and two
bores that run into each other (`bore-cross`: screws driven from both faces of a divider or shelf).
A problem shared by many copies of one bore is reported once, with the count.

## Part

```js
{
  id: '3',                    // part number, shown everywhere; continuous across sections
  name: 'Side Rails',
  section: 'frame',
  qty: 2,                     // must equal instances.length
  t: 1.5, w: 6.5, l: 91.75,   // finished T x W x L; checked against the shape's bounding box
  material: 'White oak',
  stock: 'solid' | 'sheet' | 'hardware',
  mat: 'poplar',              // key into materials for the 3D tint (default wood / hardware)
  glueup: 2,                  // face-glued layers; cutting diagram lays out t/2 stock
  stock_t: 1.75,              // rough stock thickness override for diagrams
  blank: { l_extra: 1, w_extra: 0.25 },   // milling allowance for diagrams (default 1" and 1/4" on solid)
  size: 'Adjustable steel',   // hardware: description in place of T x W x L
  note: 'one line for the cut list; {#id} chips allowed',
  shape: [
    { box: [x, y, z, dx, dy, dz] },                 // material, part coordinates
    { cut: [x, y, z, dx, dy, dz], tool: 'dado' },   // removed material; tool: checked against its depth
    { box: [...], role: 'tenon', through: false },  // tenon: allowed inside a joined part, which
                                                    // gets the matching mortise cut automatically
    // curves and angles, cut from the blank (modeling.md, Curves and angles):
    { outline: [[u, v], { arc: [u, v], rise }, ...], axis: 'y', span: [from, to], tool: 'bandsaw' },  // keep inside
    { cutout: [[u, v], ...], axis: 'z' },           // remove inside: mitres, bevels, coves, cutouts
    { lathe: [[r, along], ...], axis: 'z', center: [u, v] },   // turned: keep inside the revolved profile
    { outline: [...], axis: 'z', ease: { roundover: 0.375, faces: 'top' } },   // round-over that follows the profile
    { splay: [front°, side°], section: [w, d], top: [x, y] },  // a leg splayed one or both ways, ends level
    { roundover: 0.25, edges: 'top' }, { chamfer: 0.125, edges: ['bottom'] }   // ease the blank's edges
  ],
  instances: [{ at: [x, y, z], rot: 0, mirror: 'x', explode: [dx, dy, dz], label: 'A' }],
                              // explode: leave out; worked out from the joints (scripts/explode.js)
                              // label: for copies that are machined differently (Upright A, B, C);
                              // every labelled copy gets its own balloon with the letter in red
  stage: 0,                   // optional: explode order (higher stages move first)
  callout: { inst: 1, dist: 34, anchor: [dx, dy, dz] } | false,   // leave out: placed automatically
  drawing: false | true | { vertical: true, sub: 'Layout' },  // part layout control
  pattern: true,              // also print the face view at full size (Full-Size Patterns sheet)
  grain: false,               // sheet part with no grain direction (MDF etc. are detected by material)
  min_wall: 0.1875            // per-part override of the thin-wall warning
}
```

`rot` turns the part about z around its local origin before `at` is added. Most parts are easiest
modeled in world orientation with `rot: 0`.

The checker's notion of grain: the axis of the part's bounding box that matches `l`. A shaped
part's `t`, `w`, `l` are its blank (the boxes before shaping).

## Joint

```js
{
  id: 'J1', type: 'castle', title: 'Castle joint, four corners',
  parts: ['1', '2', '3'],     // every part involved; each must touch another in the list
  glue: false,
  fasteners: 'One 5/16" cross-bolt through the lap',
  gap: 0.125,                 // hardware-bridged gap instead of contact (brackets, hooks)
  note: 'sizes that matter',
  at: [x, y, z], radius: 10,  // optional: where Show focuses (default: where the parts meet)
  explode: 55                 // explode % used by Show
}
```

Types with extra checks: `mortise-tenon` and `stub-tenon` (tenon thickness 25–55% of the stock),
`castle` (towers at least a quarter of the post). Every joint must have both halves modeled: a type
containing `tenon` needs a tenon of one part inside another (`joint-no-mortise`); `dado`, `groove`,
`rabbet`, `housed`, `bridle`, `castle`, `half-lap`, `notch` and `slot` need a cut in one part that
another part of the joint fills (`joint-no-housing`); `dowel` needs bores with its joint id
(`joint-no-bore`, a warning). Any other type string is fine (`dado`, `rabbet`,
`half-lap`, `bridle`, `dovetail`, `dowel`, `screwed`, `bed-bolt`, `bracket`, `rests`).

Every joint also gets a drawing on the Joint Details sheet, made from the model, not authored: the
first two listed parts that meet, cropped to where they meet and pulled apart the way the joint goes
together, with the tenons, the cuts in the mating part and the joint's bores dimensioned. So model
the joinery for real: a shelf needs its dado, a dowel its bore with
`joint` set. A tenon in solid wood, parts that overlap with nothing cut, or parts that never meet are
drawn in red with what to fix.

## Detail

Coordinates in inches, v up. Each item is one of:

```js
{ rect: [x, y, w, h], fill: 'wood' | 'end' | 'none' | 'steel', dash: false, part: '1' }
{ poly: [[x, y], ...], fill: 'wood' }
{ line: [x1, y1, x2, y2], dash: true }
{ dim: [x1, y1, x2, y2], off: 0.8, text: 'optional label' }   // off > 0 is left of a→b
{ text: [x, y, 'label'], size: 0.8, anchor: 'start' | 'middle' | 'end' }
{ callout: [x, y, '3'], to: [x2, y2] }                        // balloon at x, y; leader to x2, y2. Don't cross other leaders
{ grain: [x1, y1, x2, y2] }                                    // grain-direction arrow
```

Plus `{ title, sub, w, h, wide, font, pattern }` on the detail itself. Use details for hardware
placement and anything the auto layouts can't show (fastener positions, a jig's shape); model the
curves and angles of the parts themselves with shape entries, not details; use a
section view (below) for a plain cut through the model. `pattern: true` moves a detail to the
Full-Size Patterns sheet, drawn at actual size (type 0.16") with a 1" check square, and the PDF tiles
it across letter pages at 100%. Use it for curves, tapers and templates; draw the real outline in
inches.

## Section view

`view.sections` adds a section drawing to the Drawings sheet and a cutting-plane line (heavy chain
line, arrows, letters) on the elevation that shows the plane edge-on (`on` picks it).

| Key | Meaning |
|---|---|
| `id` | the letter: Section A–A |
| `cut` | the axis the plane crosses: `'x'` (left–right), `'y'` (front–back), `'z'` (height) |
| `at` | where, in model inches |
| `keep` | which side is drawn: `'+'` or `'-'`. Defaults look toward the back (y), from the right (x), down (z) |
| `title` | subtitle, e.g. "through the side rails, looking toward the head" |
| `box` | optional `[x, y, z, dx, dy, dz]`: draw only this region, a close-up of one joint. A close-up gets no automatic overall dimensions; add them in `view.dims[<id>]` |

Faces on the cut plane are hatched. Add dimensions with `view.dims[<id>]` in the section's own
drawing coordinates (u to the right, v up, as drawn). Use one wherever a joint or profile is hidden
in the outside views.

## Jig

A shop aid the build needs (tall fence, taper jig, drilling guide, router template). Drawn like a
detail on the Shop Aids sheet, beside its own small parts list.

```js
{ title: 'Tall Bandsaw Fence', sub: 'End View', w: 6, h: 9,      // w, h set the type scale, as for details
  purpose: 'why it exists', use: 'how to use it', for: ['1'],      // part chips
  parts: [{ name, qty, t, w, l, material }],                       // or size: 'description'
  items: [ ...detail items ] }
```

## Story stick

Marks every edge of the listed parts along one axis, merged and measured from `from` (default: the
lowest edge), on a full-size stick printed across letter pages. `marks` adds extra lines with a label
(bolt heights, shelf pins). Use one for anything with repeated heights or spacings: headboards, drawer
banks, shelf units.

## Drawers

One record per drawer size; required in any plan with a drawer. The check measures the modeled box,
slides and front in each opening against the slide maker's numbers (`drawers.md`), and the page prints
a **Drawer Breakout** sheet from them.

```js
drawers: [{
  name: 'Top drawers',                 // as the builder would say it
  slide: 'accuride-3832',              // catalogue key (drawers.md), or the maker's numbers:
                                       // { like: 'accuride-3832', name, clear: [min, max] } or
                                       // { kind: 'under', name, k, side: [min, max], h, below, above, recess, notch, lengths }
  length: 18,                          // nominal slide length (NL for undermount runners)
  opening: { at: [[x, y, z], ...],     // front-left-bottom corner of each opening this size (x across, y back, z up)
             w: 28.875, h: 5.625, d: 19 },   // between the faces the slides mount to; floor to underside of what is above; front to back
  box: ['10', '11', '12'],             // the box parts (sides, front and back, bottom)
  slides: '9',                         // the slide hardware part
  front: { part: '22', style: 'full-overlay' },   // inset | overlay | full-overlay | false-front
  pull: { item: '3-3/4" bar pull', cc: '96 mm', screw: '8-32 x 1"', through_box: false, at: 'centred, 2" down' },
  waive: { 'drawer-wide': 'why this departure from the maker is fine' }   // warnings only, with a reason
}]
```

For openings with no rails between drawers (a bank of overlay drawers), each opening runs from its
front's bottom edge up to the next front, or to the case top. `drawerSize(opening, slide, { side, inset })`
in `plan-core.js` gives the box the slide wants; size the parts from it.

Check codes: `drawer-clearance` (side-mount gap outside the window), `drawer-inside-width`,
`drawer-side-thickness`, `drawer-height`, `drawer-under`, `drawer-recess`, `drawer-length`,
`drawer-depth` (slide or runner longer than the case allows), `drawer-slides` (wrong number modeled),
`drawer-front-fit` and `drawer-setback` (inset), and warnings `drawer-centred`, `drawer-gap`,
`drawer-wide`, `drawer-slide-length`, `drawer-front-cover`, `drawer-pull-screw`, `drawer-play`.

## Generated paperwork

These come from the model and need no fields:

- **What You'll Need**: the shopping list (below) and a tools list worked out from the joints, cut
  tools, bores and stock (`meta.toolkit` adds to it).
- **Shopping List** on the Shop Cut List sheet: sheets as drawn; boards in store units (hardwood by
  the quarter, `4/4 White oak, 7-1/4" wide @ 8'`; softwood or `stock.buy: 'dimensional'` as `1x8`), with
  `stock.spare` extra and at least one spare, counting strips for parts that need a glue-up. Hardware
  lines follow.
- **Shop Cut List**: every part sorted by stock, thickness, width, length; rough and finished sizes;
  R and F tick boxes kept in the reader's browser.
- **Cutting diagrams**: sheets carry the breakdown order (rip into strips, crosscut, trim; cut 1 is
  the "First cut") and face-grain arrows.
- **Fasteners, Actual Size**: every bore except plain holes, grouped with a count, plus hardware with
  `draw`, after the hardware box; tiled at 100% in the PDF.
- **Units**: the in / mm toggle re-renders every size in millimetres (store units stay imperial).

