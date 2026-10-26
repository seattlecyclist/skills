# Modeling joints

Use the helpers in `scripts/joints.js` first (table in `plan-schema.md`): they cut castle slots,
half-laps, bridles, dadoes, grooves and rabbets and add tenons, sized by `joinery.md`. This file is
for the joints they don't cover and for reading what they produce.

Every part is a union of `box`es minus a union of `cut`s, in part coordinates, placed by its
instances. The renderer turns that into exact faces and crease lines (no seams between boxes), and
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

Don't cut the mortise. Give the tenoned part `role: 'tenon'` boxes that extend into the mating
part. The checker allows that overlap only inside a declared joint and requires the tenon to be
fully inside material (pass `through: true` for a through tenon that shows on the far face).

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
