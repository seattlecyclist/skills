---
name: build-walkthrough-3d
description: Turn a woodworking or shop build plan (drawings, a cut list, a woodworking-plans plan.js, a PDF, or a description) into an interactive 3D step-by-step assembly walkthrough - every part modelled at its real size in a lit shop, each step animating the parts into place with labels and sizes, shareable links per step - with a physics check that proves no part passes through another while it moves, every part lands on something, and the finished piece has no overlaps. Use whenever the user wants assembly instructions, a build sequence, a step-by-step 3D guide or animation of how to put a project together, or says things like "show me how to build this step by step", "make a 3D build guide for this plan", "animate the assembly", or "what order do I put this together in".
---

# 3D build walkthrough

Turn a plan into a page a builder keeps open in the shop: the piece in a lit 3D workshop, one step
at a time, each new part gliding into place, glowing, and labelled with its name and size. Every
move is proven physically possible before anyone sees it.

The model is the walkthrough. You write one `build.js`: parts as boxes in their finished place,
grouped into rigid bodies, then steps that move bodies in along paths. The engine evaluates any
moment of the sequence, the checker proves it, and the page renders from the same file.

```
assets/engine.js         bodies, parts, moves, pose evaluation, the physics check (no DOM; runs in Node and the page)
assets/app.js            the three.js viewer: shop, materials, labels, step card, tap-to-measure, in-page re-check
assets/page.html         the page shell and its look (placeholders filled from PLAN.meta)
scripts/verify.js        physics check: collisions along every path, support at rest, overlaps when finished
scripts/mutate.js        proves the check catches broken moves in THIS build
scripts/build.js         check, then inline everything into one HTML page
scripts/render_check.js  open it in Chromium, shoot every step, contact sheet, phone view, problem list
examples/skeleton/build.js       START HERE: a 6-step plywood bookcase using every part of the API
examples/miter-station/build.js  the full worked example: 272 parts, 30 steps, sub-assemblies, fixtures
references/api.md        every function and option                (read when writing build.js)
references/sequencing.md how to choose a build order a person can follow  (read before writing steps)
```

If `scripts/` is missing (the skill was installed from this file alone), the full skill is in
`build-walkthrough-3d/` of https://github.com/seattlecyclist/skills.

**Needs:** Node 18+. For `render_check.js`, Playwright with Chromium. The page loads three.js
0.160.0 from jsDelivr and fonts from Google Fonts; everything else is inline. On a machine that
cannot reach jsDelivr, `npm i three@0.160.0` somewhere and pass `--libs <that>/node_modules`.

## Example prompts

- "Make a 3D step-by-step build guide for this miter station plan." (with the plan artifact or PDF)
- "Show me how to assemble the bookcase from my woodworking plan, one step at a time."
- "Animate the assembly of this workbench: frames first, then rails, then the top."
- "Turn the dresser plan.js into a walkthrough I can follow on my phone in the shop."
- "What order should I glue this cabinet up in? Show it in 3D."
- "Add a step to the walkthrough for fitting the drawer slides before the boxes."
- "The fence goes on before the T-track in my shop, swap those steps."

## 1. Get the plan

Work from the user's own plan wherever one exists: a woodworking-plans `plan.js` or page, a drawing
set, a cut list, a PDF, photos with dimensions. Copy sizes from it, never re-derive them. If the plan
came from the `woodworking-plans` skill, its `plan.js` has every part's box and instance position:
use those numbers. Both skills use inches with x left to right, y front to back and z up.

Ask once, only for what governs the sequence and cannot be found: what the user builds on (floor,
bench, assembly table), what is glued up flat first, and any tool or machine that ends up in the piece.
Pick the rest and say so.

## 2. Plan the sequence

Read `references/sequencing.md`. Write the step list in prose first: one action a person does per
step, in the order they would really do it, with the sub-assemblies glued up flat before they stand up.
Each step gets a title in the imperative ("Slide in the bottom rails"), one or two sentences saying
what and why, and the drawing sheet it comes from.

## 3. Write build.js

Copy `examples/skeleton/build.js`. Read `references/api.md` for every option.

- **Parts** are axis-aligned boxes (`box`) and cylinders (`cyl`) in their **finished** position, in
  inches by default (`{units:'mm'}` for millimetres). Model joinery that changes what touches what:
  tenons, grooves, rabbets, the layers of a laminated part. A groove is the boxes either side of it,
  so the part that sits in it can be proven to sit on the groove bottom.
- **Bodies** are things that move as one. A glued-up frame is a `virtual` body whose children are
  its pieces: the pieces arrive one by one on the table, then the whole frame moves.
- `loose:true` on anything that rests by gravity (tops, shelves, a machine, a platform): the check
  then demands it **sits on** something, not just touches it.
- `temp:true` on shop fixtures that come off again (build stands, braces, cauls); remove them in a
  later step with `mv(id, path, {remove:true})`.
- Put real shop furniture in with `K.table(...)` (parts can rest on it) and `K.obstacle(...)`; lights
  are added above the piece automatically and moves must avoid them too.
- **Moves** say where a body comes from: `drop(h)` lowers from above, `slide(dx,dy,dz)` pushes in
  along an axis, a path of poses (`at(x,y,z)`, `{rot, axis}`) for anything that turns over or stands
  up. Stagger repeated parts with `delay`. The path must be one a person could do: rails slide in
  from the side that is open, panels drop where nothing is above.
- Give each step a camera with `orbit(target, azimuth, elevation, distance)` that frames what moves.
- Finish with `K.finish({meta})`: title, what the thing is called, About facts and a link back to
  the plan.

## 4. Prove it

```
node scripts/verify.js build.js        # every step, every move
node scripts/mutate.js build.js        # the check catches breaks in this build
```

Fix every issue. Do not loosen the check, raise the tolerance, or delete a part to get a pass: an
issue means the model is wrong (a part not where it sits) or the move is impossible (a rail that
cannot get past a post). `verify.js` names the step, the moving part and what it hits. When a move
collides, change the path or the order, the same way you would in the shop. `mutate.js` must pass
too: a broken move it misses usually means a part floats a hair off what it should rest on.

## 5. Look at it

```
node scripts/render_check.js build.js --out check [--libs node_modules]
```

Read `check/sheet.png` (every step on one sheet) and `check/phone.png`. Each step should frame the
parts that move, with labels readable and nothing important behind the step card; fix cameras in the
build file and run it again. The command fails on page errors, a blank view, the in-page physics
check failing, or sideways scrolling on a phone.

## 6. Deliver

```
node scripts/build.js build.js walkthrough.html                  # page body for the Artifact tool
node scripts/build.js build.js walkthrough.html --standalone     # a full document to send as a file
```

Publish the body as an Artifact (it adds the document skeleton) and republish changes to the same
URL. Every step has its own link (`#overview`, `#step-N`). In chat give the step count, part count,
that the physics check passed, and anything you assumed about the order. Keep `build.js` with the
page: it is the source for every later change.

## Changes

Edit `build.js` (sizes in the constants at the top, never in derived numbers), then verify, mutate,
render check, build and republish. Tell the user which steps moved besides the one they asked about.

## Style

Steps are short and imperative and say why when it is not obvious ("the rails stop 1″ shy of the edge
to leave the channel the long rails sit in"). Name parts the way the plan's cut list does, so the
label in 3D matches the label on the part.
