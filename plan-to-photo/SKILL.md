---
name: plan-to-photo
description: Turn a furniture or woodworking plan (a woodworking-plans plan.js or plan.html, a plan PDF, images of plan pages such as scans, phone photos or screenshots, an OBJ/GLB/STL/FBX model, or dimensioned drawings) plus a description of a setting (a bedroom, kitchen, living room, dining room, office, patio) into a photorealistic render of the piece in that room, built in Blender Cycles from the plan's exact geometry with scanned CC0 materials, cloth-simulated soft goods, an HDRI sky with a matched sun, and a review pass for the giveaways (floating pillows, light leaks, plastic wood, blown highlights). Use whenever the user wants to see a plan "for real" (including when they attach a plan PDF or picture), asks for a photoreal or realistic render, a lifestyle or catalogue shot, a "what would it look like in my bedroom/kitchen", or says "render my plan", "make a photo of this", "put this bed in a bedroom".
---

# Plan to photo

Make a photograph of something that only exists as a plan. The plan's geometry is the truth: it is
imported exactly, so the joinery, tapers and proportions in the picture are the ones that will be
built. AI image generators redraw the piece and lose those details, so this skill does it the
archviz way: Blender Cycles, real scans, real light.

```
brief → geometry → scene spec → build → preview + review → fix → final render → iterate by version
```

| Path | What it is |
|---|---|
| `scripts/export_obj.js` | woodworking-plans `plan.js` → OBJ in meters, a material group per wood. |
| `scripts/read_drawings.py` | Plan PDF or images → one PNG per page, the text layer if any, a contact sheet and a page index; `--tile` for small text. |
| `scripts/build_model.js` | `model.json` (parts read off a PDF or images) → the same OBJ, checked against the takeoff, the overall size, overlaps and floating parts. |
| `scripts/fetch_assets.py` | Download CC0 scans and HDRIs from Poly Haven and ambientCG; `--list <setting>` for a starter set. |
| `scripts/build_scene.py` | `scene.json` → `scene.blend`: model, materials, room, props, dress scripts. |
| `scripts/p2p.py` | The helper library every script uses (geometry, scanned materials, cloth, contact, props, room). |
| `scripts/dress/bed.py` | Dress a bed frame: mattress, duvet, pillows, lumbar, throw. |
| `scripts/render.py` | HDRI with matched sun, window portals, camera, Cycles on the GPU, AgX. `--preview`, `--border`. |
| `scripts/review.py` | Review sheet: the frame plus 100% crops of the places renders give themselves away. |
| `references/drawings.md` | Reading a PDF or image plan into `takeoff.json` and `model.json`. **Read before modelling from drawings.** |
| `references/realism.md` | The rules, each from a real miss; what was tried and rejected; where renders still fail; untested advice from the research. **Read before the first preview.** |
| `references/settings.md` | Room recipes: bedroom, kitchen, living, dining, office, bathroom, patio, workshop. |
| `references/scene-spec.md` | Every field of `scene.json` and how dress scripts work. |
| `examples/walnut-bed/` | The worked example: plan, shop plan, scene, dress script, final render, and the original scripts. Also the same bed from its PDF: `Castle-Leg-Bed-rev-A.pdf`, `takeoff.json`, `model.json`, `run_pdf.sh`. |

**Needs** Blender 4.2 or newer (`blender` on PATH, or the `bpy` pip package for Python 3.11+),
Node 18+ for plan.js export, Python 3 with Pillow for review sheets, poppler (`pdftoppm`) or
PyMuPDF for PDF plans, and network access to Poly Haven
and ambientCG the first time. A GPU (Apple Metal, NVIDIA OptiX/CUDA, AMD HIP) turns a 3000x2000 final
into 8 to 20 minutes; a CPU takes hours, so on a CPU-only machine deliver previews and run the final
where there is a GPU (a cloud container builds and previews fine; the user's Mac renders the final).
If `scripts/` is missing, the full skill is in `plan-to-photo/` of https://github.com/seattlecyclist/skills.

## 1. Brief

Get, or ask once for only what you cannot infer:
- **The plan.** A `plan.js` from woodworking-plans (best: exact parts and materials), a PDF or images
  of a plan (a shop plan PDF, scans, phone photos, screenshots, a dimensioned sketch), or a 3D model
  file. For a PDF or images, ask once for any page that is missing (no parts list, no side view)
  rather than guessing a whole dimension.
- **The setting.** Room type and style ("a calm Scandinavian bedroom", "a dark green kitchen with
  brass"), time of day, and anything specific (their own floor, a wall colour, a window on the left).
  Pick the closest recipe in `references/settings.md` and fill the gaps yourself; say what you chose.
- **The finish** on each material (oiled walnut, white oak with a matte poly, painted maple).

## 2. Geometry

```bash
node scripts/export_obj.js plan.js model.obj              # prints the material groups and part ids
node scripts/export_obj.js plan.js model.obj --skip 1,12  # drop parts you will rebuild
```

**From a PDF or images**, read the drawings into a model first (`references/drawings.md`):

```bash
python3 scripts/read_drawings.py plan.pdf drawings/          # pages, contact sheet, index; then read them
node scripts/build_model.js model.json model.obj --takeoff takeoff.json [--skip 1,12]
```

Write `takeoff.json` (every size off the parts list, with its page) and `model.json` (each part's
blank, cuts, curves and copies, inches, front-left-bottom corner at the origin, back at +Y). The OBJ
is the same as a plan.js export, so everything below applies unchanged. Every check must pass; a
FAIL is nearly always a misreading, so go back to the page.

Decide what to rebuild: anything the camera sees large that the export facets or simplifies (curved
boards, radiused or turned legs). Rebuild it in a dress script in the plan's own coordinates with the
same dimensions (`extrude`, `lathe`, `ease`), and use `model.offset` to keep those coordinates.
Other model formats import directly; set `units` and check the printed bbox against the plan.

## 3. Scene spec

Copy `examples/walnut-bed/scene.json` and edit it (fields: `references/scene-spec.md`). Put the hero
piece against the back wall facing -Y. Map each material group to a scanned set with the right
finish; fetch the sets:

```bash
python3 scripts/fetch_assets.py assets $(python3 scripts/fetch_assets.py assets --list kitchen)
python3 scripts/fetch_assets.py assets polyhaven:walnut_veneer_02 ambientcg:Carpet016
```

Browse polyhaven.com/textures and ambientcg.com for other woods, stones, tiles and fabrics; the id
is the last part of the page URL. Missing sets fall back to procedural materials (fine for previews,
never for the final).

## 4. Build and preview

```bash
blender -b -P scripts/build_scene.py -- scene.json                 # writes scene.blend (1 to 4 min)
blender -b -P scripts/render.py -- scene.blend v1-preview.png --preview \
  --hdri assets/hdri/borghese_gardens_4k.exr --sun-az 160 \
  --cam 2.45,-1.1,0.95 --target 0.6,1.3,0.5 --focus 1.7,0.45,0.3 --lens 28 --shift-y 0.07
python3 scripts/review.py v1-preview.png --crop "pillows:0.3,0.3,0.75,0.6" --crop "under:0.6,0.5,1,1"
```

`build_scene.py` prints checks: the model's bbox, each pillow's back against the headboard and bottom
against the mattress, the mattress dent. Read them. `--sun-az` is the direction the sun shines from
in scene XY (0 = +X, 90 = +Y); aim it through the window. Frame with the camera level and
`--shift-y`, never by tilting (verticals stay vertical).

## 5. Review

Look at the review sheet at 100% against `references/realism.md`, in this order: contact (does every
object touch what holds it), shadows (does each belong to its object; any light leaking through the
piece), edges, grain direction and texture scale, colours against the words the user used, blown
highlights, noise, the window view. Fix the cause in the spec or a dress script, rebuild, re-preview.
Use `--border x0,y0,x1,y1` for a quick full-resolution check of one area.

## 6. Final and iteration

```bash
blender -b -P scripts/render.py -- scene.blend v1.png --res 3000x2000 --samples 2048 [same light and camera]
```

Show the user the render (and the review sheet if something is still open, saying what). Each change
they ask for becomes the next version: copy the spec, change only that, same camera, render `v2`, and
put the versions side by side. Keep every version's spec and .blend so "go back to v4's window" is
one line. Record the camera and light flags in the spec's `render` block.

## Pitfalls

- A mattress or cushion narrower than its frame, or rounded underneath, leaks light through slats
  as stripes on the floor. Fill the opening; flat bottom (`dress/bed.py` does).
- `location` set in a script is not in `matrix_world` until the view layer updates; `bake_world`
  updates it. Without that, every pillow lands at the origin.
- Cloth needs collision objects on everything it should rest on, including rebuilt parts: append
  them to `MODEL` in the dress script before `bed.py` runs.
- A sharper window view is not a better one: f/8 and a 16K backplate made the garden look pasted in
  (walnut bed v5). Keep f/5.6 and let the outside be slightly soft and bright.
- Scans are raw wood; finish them (`gamma`, `tone`). Raw walnut veneer renders milk-chocolate.
- Don't ship procedural fallbacks: `build_scene.py` prints `fallback` for every missing set.
- Fine cloth detail as geometry or texture reads as a pattern: crinkle bumps, 3 mm creases, quilting,
  hundreds of small folds and a twice-subdivided sim all lost blind tests. Keep `wrinkle`'s 1 to 3 cm
  folds and put finer creases in the `fabric` shader (`realism.md`, Tried and rejected).
- Expect close viewers to still spot the render. Bedding, the walnut veneer, the rug, lamp glow and
  spotless props are the open giveaways; say so if the user asks whether it will pass as a photo.
