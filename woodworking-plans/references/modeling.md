# Modeling joints

Use the helpers in `scripts/joints.js` first (table in `plan-schema.md`): they cut castle slots,
half-laps, bridles, dadoes, grooves and rabbets and add tenons, sized by `joinery.md`. This file is
for the joints they don't cover and for reading what they produce.

Every part is a union of `box`es minus a union of `cut`s, shaped by any curve or angle entries
(below), in part coordinates, placed by its instances. The renderer turns that into exact faces and crease lines (no seams between boxes), and
the checker turns it into cells it can intersect. Model the joint as you would cut it, so the check
proves the fit and the exploded view shows the joinery.

Rule of thumb: **material you remove is a `cut`; material that enters another part is a `tenon`;
everything else must not overlap.**

## Castle joint (post with two crossing rails)

```js
// post P square, rail thickness t, rail height h, slot bottom at Zb
shape: [
  { box: [0, 0, 0, P, P, Ztop] },
  { cut: [-1, P/2 - t/2, Zb, P + 2, t, h + 1] },   // slot along x
  { cut: [P/2 - t/2, -1, Zb, t, P + 2, h + 1] }    // slot along y
]
// lower rail (runs along x): notched from the top where the other rail crosses
{ cut: [xc - t/2, -1, h/2, t, t + 2, h] }
// upper rail (runs along y): notched from the bottom
{ cut: [-1, yc - t/2, -1, t + 2, t, h/2 + 1] }
```

Cuts run 1" past the part so they open cleanly. Remember the posts' inner quarter stands inside
the rail line; size any opening between post faces.

## Mortise and tenon

Don't cut the mortise yourself. Give the tenoned part `role: 'tenon'` boxes that extend into the
mating part (`J.mortiseTenon` does this). The checker allows that overlap only inside a declared
joint and requires the tenon to be fully inside material (pass `through: true` for a through tenon
that shows on the far face). Once the joint is declared, `plan-core` cuts a mortise the exact size
of each tenon into the mating part, copy by copy, so the drawings, sections and 3D view show it.
A joint typed `mortise-tenon` or `stub-tenon` with no tenon entering a mating part fails the check
(`joint-no-mortise`), and two tenons that meet inside one part fail it too (`tenon-clash`).

```js
{ box: [0, 0, 0, span, T, H] },                                        // rail body between shoulders
{ box: [-L, (T - tt)/2, s, L, tt, H - 2*s], role: 'tenon' },           // tenon, thickness tt, shoulders s
{ box: [span, (T - tt)/2, s, L, tt, H - 2*s], role: 'tenon' }
```

The cut list length includes both tenons.

## Other joints

- **Dado / groove**: `cut` across or along the panel at the depth; the shelf or panel sits in it
  (no overlap). Shelf length includes both dado depths.
- **Rabbet**: `cut` along the edge.
- **Half-lap**: a `cut` of half the thickness on each part, facing each other.
- **Bridle (open slot)**: `cut` down the post top; the rail passes through the slot.
- **Dovetails, box joints**: model the overall box parts with a `cut` per pin socket if the layout
  matters, otherwise as butt joints and describe the joint in `joints` and a detail.
- **Dowels, biscuits, dominoes, pocket screws, splines**: don't model; the parts butt. Declare the
  joint type and fasteners, and draw a detail if placement matters.
- **Sheet goods**: `stock: 'sheet'`, so they pack onto 48 × 96 sheets.
- **Hardware with a body** (casters, legs, slides): a part with `stock: 'hardware'` and a box, so
  connections are checked and it shows in the exploded view.
- **Gaps that hardware bridges** (bed-rail hooks, center-rail brackets, slides): leave the gap and
  declare `gap` on the joint.

## Curves and angles

The box is the blank you cut the part from. Shape entries then cut it the way the shop does, and
the drawings, 3D view, patterns, joint details and print show the true curve or angle. Never build
a curve from stacked boxes or stepped cuts. Shapes never trim `role: 'tenon'` boxes, so a tenon on
a curved rail keeps its size. The cut list lists the blank (the boxes), so size `t`, `w`, `l` to it.

A profile is drawn in two axes, seen along `axis` (the direction the saw blade passes through the
part): along `y` you draw in (x, z), along `x` in (y, z), along `z` in (x, y). Profile entries:

| Entry | Means |
|---|---|
| `[u, v]` | a corner; `[u, v, r]` rounds that corner to radius `r` (both neighbours straight) |
| `{ arc: [u, v], rise: h }` | arc to [u, v] bulging `h` at the middle; positive bulges out of the shape, negative cuts into it |
| `{ arc: [u, v], through: [u, v] }` | arc through a point |
| `{ arc: [u, v], center: [u, v] }` | arc about a centre, the short way (`long: true` or `ccw` to choose) |
| `{ curve: [[u, v], ...] }` | a smooth curve through the points (cabriole, ogee, freeform brackets) |
| `{ circle: [cu, cv, r] }`, `{ ellipse: [cu, cv, ru, rv] }` | the whole profile |

The shape entries:

```js
// arched top on a headboard panel 60 wide, 18 tall at the centre, 14 at the ends
{ outline: [[0, 0], [60, 0], [60, 14], { arc: [0, 14], rise: 4 }], axis: 'y', tool: 'bandsaw' }
// apron with a 1-1/4" arch cut up into its bottom edge
{ outline: [[0, 0], [0, 4.5], [L, 4.5], [L, 0], { arc: [0, 0], rise: -1.25 }], axis: 'y' }
// round or oval top from a square blank
{ outline: { circle: [15, 15, 15] }, axis: 'z' }
// leg tapered on its +x face, 1-3/4 at the top to 1" at the foot, from 19" up: cut it away
{ cutout: [[0.96, -1], [2.75, -1], [2.75, 19], [1.75, 19]], axis: 'y' }
// mitre: the triangle off the end of a 2"-wide rail, seen from above
{ cutout: [[0, 0], [2, 2], [0, 2.01], [-1, 2.01], [-1, 0]], axis: 'z' }
// bevel or chamfer along a part: a triangle cutout, or an edge treatment of the blank
{ chamfer: 0.125, edges: 'bottom' }          // all four bottom edges of the blank
{ roundover: 0.25, edges: ['top-front', 'top-back'] }   // top, bottom, front, back, left, right, pairs, 'long', 'all'
// turned leg: [radius, height] pairs from foot to top, about the blank's centre; the blank stays
// square outside the profile's height range (a pommel for the apron joinery)
{ lathe: [[0.6, 0], [0.75, 2], { arc: [0.75, 4], rise: 0.25 }, [0.9, 20], [1, 22]], axis: 'z' }
// round top with a 1/4" round-over on the top edge: a lathe profile about z
{ lathe: [[15, 0], [15, 0.5], { arc: [14.75, 0.75], center: [14.75, 0.5] }], axis: 'z' }
```

- `outline` keeps what is inside the profile; `cutout` removes it. `span: [from, to]` limits either
  to part of the blank along the axis (a taper that stops partway through the thickness).
- `roundover` and `chamfer` ease the blank's straight edges only. On a curved edge (a round top,
  an arched rail) use a `lathe` profile or say the round-over in the steps.
- Splayed legs: draw the leg's side view as a parallelogram `outline` in a blank sized to its
  bounding box (`blank.l_extra` for the longer stock); splay in two directions with two outlines,
  one per axis. Mitres and bevels are `cutout` triangles; both parts of a mitre meet on the line.
- Every angle and radius is measured for the builder, from the model itself: the Layout drawing
  (and the full-size pattern) gives each corner that isn't square in degrees, each taper as its
  angle off straight, each arc its radius with its centre marked or, when the centre is off the
  drawing, its rise over the chord, each turning its diameters and each bead or cove its radius,
  and each free `curve` its points, dimensioned. The Joint Details sheet lists and calls out the
  angles and radii where the parts meet (a mitre's 45°). A bevel or profile seen only from the end gets an End view. The cut list repeats
  them ("Shaped: Angle 45°, Arc R 21-21/32" (rise 1-1/4" over 14-1/2")"). Write shapes so those
  numbers are ones a builder can set and lay out: give angles by points that make a round angle
  (a 45° mitre, a 2° taper), arcs by `rise` or `center` in shop fractions, and use `curve` only
  for a truly free shape (cabriole, ogee), with `pattern: true` so it prints at full size. Say
  the angle or radius again in the step that cuts it ("set the bevel to 15°", "bend a batten
  through the 1-1/4" rise").
- Turned parts, round tops and curved parts get a Layout drawing with their points dimensioned,
  radii and diameters labelled; set `pattern: true` so the curve also prints at full size.
- The check measures shapes on a 1/16" lattice (coarser on long curves), so it proves fit to about
  that. Faces that meet on a curve or an angle count as touching.

## Explode vectors

`scripts/explode.js` works these out from the joints when `explode` is left out: each part moves
out of its joint (up out of a slot, along a tenon, off a face), far enough to clear it, starting from
the furthest part it joins; a part held from both sides spreads them; later sections move off as a
unit. Set vectors by hand only when the render check or a look at the views says one is wrong, using
these rules:

- Move parts along the direction they are assembled: rails up out of slots, tenoned parts away
  from mortises, drawers out the front, tops up.
- Stack layers so each separates: posts down and out, lower rails up a little, upper rails more,
  cleats with their rail, slats highest.
- Keep sub-assemblies together and move them as a group (the headboard moves back 20" as a unit,
  then its own parts spread from there).
- Check at 100% that nothing passes through anything, and at about 50% that each joint reads.

## Clearances

The model is exact; real parts need room. Build clearances into `PARAMS` and the derivations:
1/8" at the ends of parts that drop between others (slats, cleats), 1/16" to 1/8" per side for
drawers and doors (or the slide's spec), 3/8" per side for a mattress. Joints that are cut to fit
(slots, tenons) model at exact size, and the steps say to fit them.
