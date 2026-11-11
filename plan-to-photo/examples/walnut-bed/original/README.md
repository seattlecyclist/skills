# The walnut bed as it was actually rendered

These are the project scripts that produced `../walnut-bed-bedroom.jpg` (render v6), kept as a
record of how a first render was iterated to photoreal. The skill's generic scripts
(`../../scripts/`) were distilled from them; use those for new work.

| Step | Script | What it did |
|---|---|---|
| v1 | `export_obj.js`, `build.py` | plan.js to OBJ; room, procedural woods, rebuilt legs and headboard, cloth duvet and throw, pressure pillows |
| v2 | `patch.py` | better procedural walnut, oak and maple, puffier duvet |
| v2 | `settle_pillows.py` | a failed attempt to settle pillows with gravity (they deflated and sank) |
| v3 | `patch_v3.py` | scanned Poly Haven walnut, white oak plank floor, ambientCG carpet, linen and knit scans; pillows leaned on the headboard and dented into the mattress |
| v3 | `render_v3.py` | Borghese Gardens HDRI with its sun cut out and replaced by a matched sun lamp, window portal, Metal GPU, AgX |
| v4 | `patch_v4.py` | mattress fills the frame with a flat bottom (fixed the slat-stripe light leak), pillow creases, taupe throw, calmer wall |
| v5 | `render_v5.py` | 16K backplate through the window, glass, haze, f/8. Mike preferred v4's softer garden, so v6 went back |
| v6 | `nightstands_v6.py` | walnut nightstands in the bed's design language (22 x 16 x 22 in), then `render_v3.py` at 3000x2000 |

Render v6: `blender -b -P render_v3.py -- <dir> walnut-bed-bedroom-v6.png 3000 2000 2048 2.45,-1.1,0.95 0.6,1.3,0.5 28 -20 1.1 0.07`
with `SCENE=scene_v6.blend` (camera, lens, sun azimuth, exposure and shift from the session notes; the
sample count is approximate).
