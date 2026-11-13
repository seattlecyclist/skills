# Patterns

Coordinates are inches, x across the board, y along it, y up. Every generator returns polygons
(`pts`, counter-clockwise, convex), each with a `role` (species), a `slice` (which slice it lands in)
and a `unit` (the sub-assembly glued before the log, or none), plus the `trim` rectangle.

## cubes (tumbling blocks)

Rhombille tiling: pointy-top hexagons of circumradius `side`, each split into three 60/120 degree
rhombi (lid, left, right) meeting at the centre. Hexagon width √3·side, rows 1.5·side apart, odd
rows shifted half a hexagon.

| param | default | meaning |
|---|---|---|
| `side` | 1.25 | rhombus side, inches |
| `cols`, `rows` | fitted | hexagons per row, rows |

Build: one bar (60 degree rhombus, blank side·sin60 thick, blade 30 degrees) → hex units of 3 →
row logs of `cols` hexes → slices nest with a half-hex offset. One log type. Finished width
(cols − 1/2)·√3·side, length 1.5·side·(rows − 1) + side. Roles: `lid`, `left`, `right`. Light lid,
mid left, dark right puts the light top left.

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

## stars8 (LeMoyne / eight-point quilt star)

Square blocks of side a(2+√2) (a = rhombus side): 8 rhombi of 45/135 degrees around the centre,
4 corner squares of side a, 4 right-isosceles edge triangles (legs a, hypotenuse a√2). Each block is
4 identical quarter units turned 90 degrees, and each quarter is 2 rhombi, a square and two
half-triangles (legs a/√2) so that quarters have straight sides. Blocks are the slices: one block log
makes every block.

| param | default | meaning |
|---|---|---|
| `side` | 1.0 | rhombus side (block 3.414·side) |
| `alternate` | true | star points alternate `star_a` / `star_b`; false: all `star_a` |
| `cols`, `rows` | fitted | blocks |

Three bar shapes: 45 degree rhombus (blade 45), square, right isosceles triangle (blade 45, flip
the blank each pass).

## checker

Square bars `side`, alternating `a`/`b`; rows are slices, every other one turned end for end.
Classic two-step: the row log is a strip panel `side` thick. Use `side` = finished-thickness-ish
squares (1-1/4" to 2").

## brick

Bricks `brick` x `course` (default 2 x 1), alternating `a`/`b` along a row, rows offset half a brick.
Even rows carry half a brick past each end that is trimmed. Two log types.

## custom

Give the face directly:

```json
{"pattern": "custom",
 "polygons": [
   {"pts": [[0,0],[1,0],[1,1],[0,1]], "role": "a", "slice": "r0", "unit": null},
   {"pts": [[1,0],[2,0],[2,1],[1,1]], "role": "b", "slice": "r0", "unit": null}
 ],
 "trim": [0, 0, 2, 1],
 "species": {"a": "maple", "b": "walnut"}, "board": {"width": 2, "length": 1, "thickness": 1.5}}
```

Rules that make it buildable:
- Every polygon convex; split concave pieces (a chevron is two parallelograms).
- Angles a table saw can bevel: each bar's faces within 45 degrees of square to a reference face.
  Parallelograms and rhombi from 45 to 90 degrees, isosceles triangles with an apex of 90 degrees
  or less, squares and rectangles all rip directly. Others get a warning and a sled.
- A `slice` is one crosscut piece: all its polygons must be glued as one log. Make slices rows or
  blocks with at least one flat side where possible; slices with matching zigzag sides nest (rows of
  hexagons).
- A `unit` groups bars glued first (a hexagon of three rhombi); unit ids must be unique across the
  board (prefix with the slice id).
- Make repeats identical so they match: the script groups slices and units that are the same up to
  translation, a 90 or 180 degree turn or a flip, and makes one log per group.

Write a generator in `patterns.py` (and add it to `GENERATORS`) when a pattern will be reused; add a
`design.json` to `examples/` and run `scripts/selftest.py`.

## Ideas that map onto these

- Chevron / herringbone: parallelogram bars (45 or 60 degrees), rows of alternating lean.
- Hexagon honeycomb: regular hexagon bars (two 30-degree bevel passes on each side of a rectangle
  blank) or three rhombi per hexagon in one species.
- Diamond lattice: 45 or 60 degree rhombi in two species, alternate along the row.
- Borders: a ring of rectangular bars around any pattern; give them their own slices.
