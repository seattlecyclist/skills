# Patterns

Coordinates are inches, x across the board, y along it, y up. Every generator returns polygons
(`pts`, counter-clockwise, convex), each with a `role` (species), plus the `trim` rectangle and
`cells`: the grid of logs the face is cut into (see `custom`).

## cubes (tumbling blocks)

Rhombille tiling: pointy-top hexagons of circumradius `side`, each split into three 60/120 degree
rhombi (lid, left, right) meeting at the centre. Hexagon width √3·side, rows 1.5·side apart, odd
rows shifted half a hexagon.

| param | default | meaning |
|---|---|---|
| `side` | 1.25 | rhombus side, inches |
| `cols`, `rows` | fitted | hexagons per row, rows |

| `build` | `hexagon` | `hexagon` or `triangle` (below) |

Build, `hexagon` (default): the way makers build this board (Tom Silva, This Old House; Degoose and
lanwater on LumberJocks). Three diamond bars, one of each wood, are taped into a hexagon log; the logs
are sliced into pucks; every puck is glued at once inside a clamped frame of four boards, from the
centre out. One bar shape at a 30 degree tilt, no triangle bar. The long sides run through the
centres of every other row, where half pucks go, so the width moves to a multiple of `0.87·side`.
Nothing is machined between the bars and the board, so the bars must all be cut at one setup, and
the plan keeps Silva's gap-filling step. Keep `side` at 1.5" or less so the log passes under the saw;
1.5" gives about 35 pucks on a 12 x 16 board (Silva's has 36).

Build, `triangle`: triangle logs three diamonds on a side (`3·side`), each of three diamonds and
three small triangles (half lids) in two glue-ups, trued in a V block. Every face is machined, but it
needs a triangle bar and no published build uses it. Keep `side` at 1" or less.

Roles: `lid`, `left`, `right`. Light lid, mid left, dark right puts the light top left.

## Lattice patterns: chevrons, gems, ziggurat, ribbons, notched

Five expert-plus patterns drawn as colourings of a fine triangular lattice (small triangles of side
`side`) and built from triangle logs two or three small triangles on a side. Same-wood neighbours
inside a log merge into one bar, so every log is two to four bars and one glue-up. `side` defaults to
0.75"; the board moves to a whole number of logs.

| pattern | what it is | roles | log | bars |
|---|---|---|---|---|
| `chevrons` | three-armed pinwheels that run into zigzag chains | `a`, `b`, `c` | 3 x side, one type | one trapezoid; no triangle bar |
| `gems` | hexagonal cut gems: a table ringed by six shaded facets | `light`, `pale`, `shade`, `dark`, `table` | 2 x side, four types | trapezoid, small triangle |
| `ziggurat` | one stepped hexagonal pyramid centred on the board | `light`, `mid`, `dark`, `line` | 2 x side, six types | trapezoid, small triangle |
| `ribbons` | zigzag ribbons of diamonds, lit and shaded like pleated paper | `a_lit`, `a_shade`, `b_lit`, `b_shade` | 2 x side, four types | diamond, small triangle |
| `notched` | tumbling blocks with a small cube bitten out of each near corner | `lid`, `left`, `right` | 2 x side (`log`), six types | trapezoid, small triangle |

`chevrons` is the build Mike Dillen documented after SPALM's board (three trapezoid sticks in a V
cradle). The other four are this skill's own designs on the same triangle-log method; no published
build of them exists. All but `chevrons` need the small triangle bar and so the McMillan cut.
`ziggurat` is one motif, not a repeat. To add another, write a `colour(u, v)` function and pass it to
`_lattice`.

## tribars (impossible triangles)

On the same lattice with logs four small triangles on a side. Every upward log is a Penrose tribar: three
identical trapezoid bars (3 and 2 units on their faces, one unit thick) set pinwheel fashion round a
one-unit triangular key. Every downward log is plain ground, split into a trapezoid and a triangle bar
because a triangle the size of the log is deeper than a 10" saw rips at 30 degrees. Roles `a`, `b`, `c`
(the bars), `key`, `ground`, `ground_mid`; give `ground` and `ground_mid` the same wood. `side` 0.75.
All rows are the same crosscut slid half a log: one plank. This skill's own design.

## sierpinski

Each large upward triangle (eight units on a side) is the fractal: light unit triangles with dark holes
of one, two and four units; the large downward triangles are ground. Built at `levels: 2`: first-level
logs two units on a side (three light bars round a dark one, or one solid bar), four of those to a log
four units on a side. No bar is larger than two units. Roles `tri`, `hole`, `ground`. `side` 0.625.
Two planks, each cut for half the rows. This skill's own design.

## swell (graded checkerboard)

A two-wood checkerboard whose strip widths and row thicknesses grow from `min` (3/8") at the edges to
the middle on a sine curve; the middle size is solved from the board size. `cols` (16) and `rows` (22)
must be even. `cells` is `{"kind": "panel", "graded": true}`: one strip panel makes every row, planed
thinner before each set of slices, thickest first, and made long enough (`shop.planer_min_length`, 14")
to go through the planer at the last setting. Every second row is turned end for end. The graded-width
method is Andrei Muntian's, documented by Bob Chambers (research folder); the sine layout in both
directions is this skill's own. Roles `a`, `b`.

## stars6 (six-point stars)

The same rhombille tiling coloured differently. Six rhombi meet at their 60 degree corners at every
hexagon's bottom vertex; those vertices form a triangular lattice, and a star is the six rhombi around
a chosen vertex. Chosen vertices never neighbour, so no rhombus is in two stars.

| param | default | meaning |
|---|---|---|
| `side` | 1.25 | rhombus side |
| `spacing` | `open` | `touching`: every third vertex, stars tip to tip, 2/3 of the board is star, 1 log type. `open`: one in four, stars separated by field hexagons, 3 log types. `sparse`: one in seven, 7 log types (avoid). |
| `shade` | false | roles `star_lid`, `star_left`, `star_right` instead of `star`, for faceted 3D stars |

Roles: `star` (or the three shaded), `field`. Dark stars on a light field read most clearly with
`open`; with `touching`, light stars on dark read better than dark on light.

## snowflakes

The rhombille tiling again: every rhombus joins two neighbouring 6-way vertices, so a flake is drawn
as lattice edges: six arms of `arm` rhombi end to end from a centre, with side branches of `branch`
rhombi at 60 degrees from the arm points in `branch_at`. A branch at step 1 meets the next arm's
branch and closes a hexagon ring (a different motif); branches at step 2 or more read as a snowflake.

| param | default | meaning |
|---|---|---|
| `side` | 0.75 | rhombus side (5/8" to 3/4" keeps two flakes across a 13" board) |
| `arm` | 3 | rhombi per arm |
| `branch_at`, `branch` | [1, 2] for arm 3, else [1]; 1 | where branches leave the arm, and their length |
| `spacing` | 2·arm+1 | edges between flakes across; flake rows sit `rise`·2 hexagon rows apart (rise ≈ spacing/√3) |
| `stagger` | false | shift every other flake row half a spacing (doubles the log types) |
| `core` | false | role `core` for the six centre rhombi |

Roles: `flake`, `field`. Flake centres are snapped to log corners and `spacing` should be a multiple
of 3, or the flakes land differently on every log and the log types multiply. The example (arm 2,
branch at 1, spacing 6, stagger, side 0.5, `levels` 2) needs seven log types, two of them sliced.

## stars8 (LeMoyne / eight-point quilt star)

Square blocks of side a(2+√2) (a = diamond side): 8 diamonds of 45/135 degrees around the centre,
4 corner squares of side a, 4 right-isosceles edge triangles. Built as square logs: a diamond bar and
a small triangle bar make a flat band; two bands and a square bar make a quarter log in corner cauls;
two quarter logs make a half log, two halves the block log. Every log is jointed and planed square
before the next glue-up. Blocks are the slices. Keep the block under 2-5/8" (`side` 0.75).

| param | default | meaning |
|---|---|---|
| `side` | 1.0 | rhombus side (block 3.414·side) |
| `alternate` | true | star points alternate `star_a` / `star_b`; false: all `star_a` |
| `cols`, `rows` | fitted | blocks |

Three bar shapes: 45 degree rhombus (blade 45), square, right isosceles triangle (blade 45, flip
the blank each pass).

## geodomes (geodesic domes)

Equilateral-triangle tiling in row strips. Flat-top hexagons `freq` triangles a side tile it, each a
faceted dome: six sectors (one per hexagon side) by `freq` rings. The two sides facing the light
take the lightest tone, the next two the second, then the third, and the side away the darkest; the
crown ring is a tone lighter and the rim ring a tone darker, so each dome bulges.

| param | default | meaning |
|---|---|---|
| `side` | 0.8 | triangle side (1" with `freq` 3 makes 5.2" domes) |
| `freq` | 4 | triangles per hexagon side (3 reads most clearly on a 12 x 16 board) |
| `tones` | 4 | woods, roles `tone1` (lightest) to `toneN` |
| `light` | [-0.55, 0.6, 0.58] | light direction (x, y, z); upper left by default |
| `rim` | true | darken the outer ring |

Logs are the dome's six sectors: triangles `freq·side` on a side, each glued from flat layers
(same-tone neighbours merge into one trapezoid bar, so there are far fewer bars than facets). With
`freq` 3 there are four log types. Light to dark woods with clear steps: maple / canarywood / cherry / walnut.

## kagome (trihexagonal star lattice)

Regular hexagons on a triangular grid with up and down triangles between them; every hexagon is
ringed by six triangles, so it reads as interlocking six-point stars (a triaxial weave).

| param | default | meaning |
|---|---|---|
| `side` | 0.9 | hexagon and triangle side |
| `levels` | 2 | four `2·side` logs glued into a `4·side` log before slicing |

Roles `hex`, `up`, `down`. Logs of side `2·side`: a trapezoid (a third of a hexagon) under a
triangle. Two small log types, two large. Keep `4·side` at 3" or less (`side` 0.75). Make the hexagon
the light wood: a dark hexagon takes over the board.

## rosettes (rhombitrihexagonal, 3.4.6.4): drawn, not built

Hexagons, squares and triangles of one edge length. The generator still draws it, but `cbplan.py`
refuses to plan it: the pattern mixes 60 and 90 degree corners, so no grid of triangle or square
logs holds it. Every way of cutting it up leaves either a glue-up whose faces cannot be machined
flat or slivers of hexagon and square. Offer `pinwheel` instead and say why.

## pinwheel (pinwheel rosettes, snub trihexagonal)

The buildable rosette: hexagons, each ringed by six diamonds that all lean the same way, with small
triangles where three rings meet. Every corner is 60 or 120 degrees, so it sits on a triangle grid.

| param | default | meaning |
|---|---|---|
| `side` | 0.75 | every edge; hexagons are `2·side` across |
| `levels` | 1 | 2 glues four `2·side` logs into a `4·side` log: a quarter of the slices to handle |

Roles `hex`, `diamond`, `tri`. Three small log types (plus three large with `levels` 2). Bars: a
triangle, a diamond and a trapezoid, all at a 30 degree blade tilt. Keep `4·side` at 3" or less.

## checker

Square bars `side`, alternating `a`/`b`. The classic two-step: strips glued into a panel `side`
thick, the panel crosscut, every other slice turned end for end. Use `side` 1-1/4" to 2".

## brick

Bricks `brick` x `course` (default 2 x 1), alternating `a`/`b` along a row, rows offset half a brick.
Even rows carry half a brick past each end that is trimmed. Two log types.

## custom

Give the face directly:

```json
{"pattern": "custom",
 "polygons": [
   {"pts": [[0,0],[1,0],[1,1],[0,1]], "role": "a", "slice": "r0"},
   {"pts": [[1,0],[2,0],[2,1],[1,1]], "role": "b", "slice": "r0"}
 ],
 "trim": [0, 0, 2, 1],
 "species": {"a": "maple", "b": "walnut"}, "board": {"width": 2, "length": 1, "thickness": 1.5}}
```

Without `cells` a custom face is built as strip panels, so every polygon must be a rectangle and a
`slice` must be one straight row of them (checkerboards, bricks, stripes, basket weaves).

For a face with 60 degree geometry, add the log grid and leave `slice` out:

```json
"cells": {"kind": "tri", "side": 3.0, "origin": [0, 0], "angle": 0, "levels": 1}
```

`side` is the side of the triangle log, `origin` a grid corner, `angle` the direction the rows run
(0 across the board, 90 up it), `levels: 2` glues four logs into a log of side `2·side` before
slicing. `logs.py` clips the face to that grid, merges same-wood neighbours into single bars, and
finds which cells are the same log turned or flipped. Choose the grid so that:
- grid lines follow piece edges or cut pieces along a line of symmetry (a cut through a piece
  becomes a same-wood glue line, which disappears in end grain);
- the pattern repeats on the grid, so few log types come out (print the plan and count; over six
  is a lot of glue-ups);
- the log is at most 2-5/8" tall (side 3"), or it will not pass under a 10" saw on a sled;
- every piece left after clipping and merging is a diamond, parallelogram, trapezoid or triangle
  with 60 degree corners. Anything else fails "Bar can be cut".

Write a generator in `patterns.py` (and add it to `GENERATORS`) when a pattern will be reused; add a
`design.json` to `examples/` and run `scripts/selftest.py`.
## Options every design takes

```json
"frame": {"width": 0.75, "species": "walnut", "liner": {"width": 0.375, "species": "cherry"}},
"whole_motifs": true
```

- `frame` is an optional add-on, absent from every base design and example; add it only when the
  user asks for a border. It glues rings of end-grain blocks round the trimmed field: an optional `liner` first, then
  the frame. The blocks are slices of a square bar, so the whole face stays end grain. Pick a liner
  wood that differs from both the frame and the pieces that touch it, or the line disappears. A
  ring under 3/8" wide is flagged: its blocks are too small to handle.
- `whole_motifs` (default true) moves the trim so it runs between motifs, or through their line of
  symmetry, instead of through an arbitrary point. Generators say where with `centers` (motif
  centres) and `period` (the repeat along the board, for patterns with no mirror line across the
  rows).
- `stars8` takes `params.border`: a plain border in the ground wood, cut as a border bar, so no
  star point is cut by the edge.

## Ideas that map onto these

- Chevron / herringbone: parallelogram bars (45 or 60 degrees), rows of alternating lean.
- Hexagon honeycomb: regular hexagon bars (two 30-degree bevel passes on each side of a rectangle
  blank) or three rhombi per hexagon in one species.
- Diamond lattice: 45 or 60 degree rhombi in two species, alternate along the row.
- Borders: a ring of rectangular bars around any pattern; give them their own slices.
