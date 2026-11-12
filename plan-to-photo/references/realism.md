# What makes a render read as a photograph

Every rule here came from a real miss on the walnut bed (examples/walnut-bed), found by looking at a
render the way a viewer does. Check each one on the review sheet before calling a render done.

## Geometry

- **The plan's geometry is the truth, but not always the finish.** Import the plan exactly (joints,
  tapers, proportions), then rebuild anything the camera sees up close that the exporter faceted:
  curves as true curves (`extrude` an outline sampled 200+ times), radiused corners, turned parts
  (`lathe`). Keep the dimensions; change only the tessellation.
- **Ease every edge.** 1 to 2 mm bevels (`ease`) on all wood and stone. Real arrises catch a thin
  line of light; knife edges are the first giveaway of CG.
- **Furniture never sits on air or in the floor.** Lowest point on the floor or rug top. When there
  is a rug, raise the model by its thickness (8 mm) or the legs sink into it.

## Contact and soft goods

- **Soft things press into what holds them.** A pillow 1 cm above a mattress, or 14 cm in front of a
  headboard, reads as floating in every render (v2). Lean pillows on the headboard, sink them 2 to 3
  cm, and dent the mattress under them (`lean_on`, `rest_on`, `press_into`).
- **Pressure-sim pillows go wrong.** Low pressure deflates them flat into the mattress, high pressure
  makes vinyl balloons. Model the case, then sculpt it: corner pulls, fold lines, centre sag, lumps
  (`creases`).
- **Drape cloth with a sim, never by hand.** Duvet, throw, tablecloth, curtains hang from cloth
  simulation over collision objects (`run_cloth`), then get thickness and subdivision.
- **A settled sim is too smooth; add the small folds.** A duvet sim over a mattress settles into a
  few big drapes and reads as rubber (gauntlet r00: six of six critics named it). `wrinkle` adds
  dozens of 1 to 3 cm compression folds and filling lumps along the normals after the sim; five of
  five critics preferred it. Don't go finer: 3 mm creases and crinkle bump maps read as pockmarks
  or a pasted pattern (r02, r03), and quilt puffs as blobs (r07).
- **Put cloth's fine creases in the shader, not the mesh.** Cloth has no subsurface and a fuzzy
  sheen (roughness 0.3), and `fabric` draws sparse, thin crease lines as bump (`crease` 0.3,
  `crease_scale` 6, `crease_sharp` 14). Five of five critics preferred that to plain linen
  (gauntlet run 2, r03). Doing it in geometry failed. More, smaller `wrinkle` folds read as
  displacement blobs (r01, 0 of 5). Subdividing the sim mesh twice for sharp creases leaves pinpoint
  dimples like tufting (r02 and r03 draft). A 12 mm cloth sim collapsed the duvet into a heap. Keep
  the lines sparse: a dense contour pattern reads as embossed matelassé. Close crops still call it
  a bump map, so this narrows the gap, not closes it.

## Light

- **Light leaks are physics bugs, not lighting bugs.** v3 showed slat-shaped stripes on the floor
  beside the bed: the mattress was 1 in narrower than the rails and rounded underneath, so room light
  went down between the slats. The fix was physical: the mattress fills the frame opening with a
  flat bottom. Before touching lights, ask what real object should be blocking that light.
- **Use a real sky.** An HDRI for sky and bounce, with its sun split out into a SUN lamp of the same
  direction, colour and energy (render.py does this). Sun patches are then sharp and noise-free and
  the window view matches the light.
- **Portals in every window** for interiors, or the room renders noisy and dark.
- **Watch blown highlights.** A sun patch on a pale rug clips to white. Lower `--sun-gain` (0.7 to
  0.85) or `--exposure` a little; AgX keeps the rest.
- **Practical lamps on.** Warm (about 2700 K) lamps in a daylit room are what make a room feel lived in.
- **Lamp bulbs are big.** A 3 cm point bulb throws a hard-edged cone up the wall that critics call a
  CG spotlight; a 6.5 cm bulb (a real A19) softens the cone's edge (gauntlet r05, four of five
  preferred). Don't switch lamps off to hide it: the room goes dark (r13).

## Materials

- **Scans, not procedurals,** for anything the camera sees large: wood, floor, rug, linen. Poly Haven
  and ambientCG are CC0 (`fetch_assets.py`). Procedural wood reads as CG within a second.
- **Grain runs along each part**: legs vertical, rails and boards along their length, end grain on
  the ends. One scan per material, a different patch per part (`wood`, `assign_wood`).
- **Finish changes the colour.** Scans are shot raw. Oiled walnut is much darker and warmer than a
  raw veneer scan: gamma 1.5 and a warm multiply. Oiled satin is roughness 0.32 to 0.5 and no coat.
- **Floors are planks, not a tiled photo**: per-plank patch and tone, staggered butt joints, dark seams.
- **Keep paint quiet.** Wall noise above about 2% shows as blotches (v3) and slows the denoiser.
- **Match the request's colour words.** "Mauve" came out rust in v3; check every named colour in the
  render, not just in the node values.

## Camera

- Eye height 0.9 to 1.6 m, 24 to 35 mm full-frame lens, verticals vertical (keep the camera level and
  frame with `--shift-y`, not by tilting).
- f/5.6 with focus on the hero: the background softens a little, as a real photo would. Stopping
  down to f/8 to sharpen the window view (v5) made the garden look like a photo pasted in; Mike
  preferred v4's soft view. A window view should be slightly soft and brighter than the room.
- **A little grain.** A denoised render is cleaner than any camera; faint shot-noise grain
  (`--grain 0.007`, scaled with width, no stronger than the walls in real photos) won five of five
  (gauntlet r06). Stronger reads as added noise, and at 3000 px wide even this was called render
  noise by some critics, so keep it faint.
- Keep the exposure moody rather than lifted: opening up half a stop read as hazy render GI (r11).
- 3:2 at 3000x2000 for the final. Previews at a quarter size and 64 samples.

## Process

- Preview at low samples, read the review sheet at 100% crops, fix, then render the final. A full
  render is 8 to 20 minutes on an Apple M-series or RTX GPU at 2048 spp, hours on a CPU.
- Version every render (v1, v2, ...) and keep the scene file that made it, so "go back to v4's window"
  is a one-line change.
- Change one thing the user asked for at a time and keep everything else identical, same camera
  included, so versions can be compared side by side.

## Tried and rejected

Every change below was tested in the walnut bed gauntlet: a blind A/B against the current best,
judged by five fresh critics who also saw a real bedroom photo, and kept only if four of five
preferred it. Don't try these again without a new idea about why they failed.

| Change | Round | Critics who preferred it | What the critics saw |
|---|---|---|---|
| Crinkle bump texture on the duvet | run 1 r02 | 3 of 5 | A uniform procedural bump. |
| 3 mm micro-creases in the geometry | run 1 r03 | 1 of 5 | Pockmarks. |
| Matte cloth shading (no sheen) | run 1 r04 | 0 of 5 | The throw went grey. |
| Quilting puffs on the duvet | run 1 r07 | 0 of 5 | Lumpy blobs, and a scalloped sun-patch edge. |
| Weave pattern in the cloth's base colour | run 1 r08 | not sent | Invisible at this distance on the 100% crop. |
| Softer duvet sim (bend 0.4, one subdivision) | run 1 r09 | not sent | No visible change on the 100% crop. |
| Striped throw | run 1 r10 | 3 of 5 | The stripes read as pasted on. |
| Exposure half a stop brighter | run 1 r11 | 0 of 5 | Hazy render GI; critics liked the darker corners as photographic. |
| Vignette 0.35 | run 1 r12 | 3 of 5 | All five called it a coin flip and all picked the same slot, so it was position bias. |
| Bedside lamps off | run 1 r13 | not sent | The room went far too dark. |
| About 200 smaller `wrinkle` folds | run 2 r01 | 0 of 5 | Displacement blobs, and a melted sun-patch edge. |
| Sharp creases on a sim mesh subdivided twice, plus a topstitched flange | run 2 r02 | 3 of 5 | Evenly spaced pinpoint dimples like tufting, and a stiff padded edge. |
| 12 mm cloth sim resolution | run 2 | not sent | The duvet collapsed into a heap after 76 minutes. |

The pattern: fine detail added to cloth as geometry or as a texture reads as a pattern, not as
cloth. Only shading changes (no subsurface, fuzzier sheen, sparse crease lines in bump) and medium
1 to 3 cm folds held.

## Where it still fails

The gauntlet did not make the bed pass as a photo. After run 1, critics shown the render beside two
real photos picked the render 21 times out of 21. A check of 15 specific things the render must match
failed 10 in run 1 and 9 in run 2. In both runs the walnut colour and grain, the rail sheen, the
headboard, the duvet, the pillows, the throw, contact shadows, lamp glow and the depth of field on
the wall art failed. The critics' remaining giveaways, with what the code does today and an untested
lead for each:

- **Bedding** is the weakest part in both runs. Shading changes helped; geometry detail did not.
  Lead: sculpted mid-size wrinkles and modelled hems and seams (Field Guide), not more sim detail.
- **Repeating walnut veneer.** `wood` gives each part its own offset into one scan, and critics
  still called it tiled. Lead: also flip and tint each part from Object Info > Random, and a second
  scan for the large panels.
- **Flat rug.** `rug` is an 8 mm box with a texture and no pile. Lead: pile in displacement or
  hair, and legs that sink into it.
- **Lamp glow.** The bulb is a POINT light of 6.5 cm radius inside the shade; critics still called
  the light on the wall a CG cone. Lead: a bulb-sized mesh or area emitter and a lamp dimmed to its
  true ratio against daylight.
- **Render noise.** Even `--grain 0.007` was called added noise by some critics at 3000 px.
- **Props too clean.** Books, vessels and lamps are new and spotless. Lead: restrained dust and
  handling marks, a few objects that imply a person.

## Untested advice from the research

The Photoreal Blender Field Guide (written after run 1) collects practitioner and Blender manual
advice. None of the items below has been through the gauntlet. Its sheen and roughness starting
values are estimates, not documented figures, so tune them against a reference photo. The Blender
facts were checked against Blender 5.3.0 on 2026-11-11, as noted.

- **Camera aperture: rejected.** The guide suggests f/8 to f/11. Keep f/5.6 with a slightly soft,
  bright window: Mike rejected a sharp f/8 window in v5.
- **Denoising.** The guide wants OpenImageDenoise with albedo and normal passes and the Accurate
  prefilter. In 5.3 those are the defaults (`denoising_input_passes` `RGB_ALBEDO_NORMAL`,
  `denoising_prefilter` `ACCURATE`) and `render.py` leaves them alone, so this is already done.
  The final adaptive threshold is 0.006, inside the guide's "0.01 or below".
- **Indirect clamping.** The guide says to turn it off or set it high, because clamping dims bounce
  light and reflections. `render.py` sets `sample_clamp_indirect = 3`, lower than the 5.3 default of
  10. Untested; a candidate for the contact shadow and lamp glow failures. (`--clamp` is a different
  thing: the HDRI level above which light moves into the sun lamp.)
- **Sun size.** The guide says use the real angular size, about 0.53 degrees. `render.py` uses 0.55
  and the 5.3 default is 0.526, so this is already done.
- **Physical sky.** The guide prefers the Sky texture's Multiple Scattering model to an HDRI for
  control. 5.3 has it (`sky_type` `MULTIPLE_SCATTERING`). The skill uses an HDRI split into a sun
  lamp instead; untested against it.
- **View transform.** AgX with a contrast look, as `render.py` does. 5.3 also offers `ACES 2.0`,
  which the manual calls gentler in the highlights. Avoid `Standard`; `Filmic` is still selectable
  in 5.3 but superseded by AgX.
- **Cloth shading.** Sheen on all cloth, weight 0.3 to 1.0 and roughness 0.3 to 0.5, base roughness
  0.8 to 1.0, no subsurface. `fabric` already uses sheen 0.6, sheen roughness 0.3, roughness 0.78 to
  0.95 and no subsurface, and run 2 confirmed the last two.
- **Wood finish.** No coat on oiled wood (a coat reads as laminate), roughness driven by the grain
  map, a fine pore bump and slight anisotropy along the grain. `wood` has no coat and a roughness
  range; pore bump and anisotropy are untested.
- **Base colours** between about 30 and 240 sRGB, and whites made bright with light, not with 255.
- **Work from one reference photo** of the kind viewers will compare against, and flip between the
  two at the same size. Run a grey clay render to test light, contact and edges before materials.
- **Finishing.** Glare on clipped highlights only, a little lens softness, grain weighted by
  luminance, and output resized and compressed like the comparison photos. Avoid strong chromatic
  aberration, distortion and vignette (run 1 r12 agrees: the vignette did nothing).

## Testing a change

The gauntlet method, for anyone tuning realism further:
- Change one thing per round and judge it as a blind A/B against the current best, with a real photo
  alongside, by fresh critics who see only the images. Keep it only if four of five prefer it.
- Look at a 100% crop of the change before spending critic calls. Two rounds in run 1 changed
  nothing visible.
- Counterbalance which slot the candidate is in. In run 1 r12 every critic called it a coin flip and
  picked the same slot.
- Hold out real photos the bar was not written from, and re-draw them for each run.
