# Worked example: Kapex 120 Miter Station

A 96″ mobile miter station in ½″ Baltic birch with a Festool Kapex KS 120 dropped into a 30″ bay so
its table lands flush with the wings at 36″. 272 parts, 30 steps, built from the plan's Rev A drawing set.

- `build.js`: the whole model and sequence
- `walkthrough.html`: the built page (standalone; download and open it, it loads three.js from jsDelivr)
- `sheet.jpg`: every step on one sheet, from `render_check.js`
- `finished.jpg`: the last step

## The prompt

The plan already existed (made with the `woodworking-plans` skill). The walkthrough came from:

> Make a 3D step-by-step build guide for my Kapex miter station plan, so I can follow it in the shop.
> Show the frames being glued up flat on the assembly table and then stood up.

## What it shows off

- **Sub-assemblies**: each cross-frame is a `virtual` body. Frame 1 is glued up piece by piece on the
  assembly table (children dropping in, in the frame's own turned coordinates via `frameLocal`), the
  other three arrive glued up, then all four are stood up with a lift, turn and lower path (`seg`).
- **Shop fixtures**: build stands and cheeks hold the frames at castor height, a 2×4 brace holds them
  plumb, and both come off (`remove: true`) once the rails tie the carcass together.
- **Joinery that matters to the order**: the layer 2 rails are longer than layer 1, which makes the
  tenons and leaves the channel the long rails slide into; the check proves each rail can only come
  in from the open side.
- **Hardware and a machine**: slides, T-track in routed grooves, stick-on tapes reading out from the
  blade, flip stops, leveling castors and the saw itself as simplified volumes with `note` tooltips.

## Re-run it

```bash
node ../../scripts/verify.js build.js
node ../../scripts/mutate.js build.js
node ../../scripts/render_check.js build.js --out /tmp/miter-check
node ../../scripts/build.js build.js walkthrough.html --standalone
```
