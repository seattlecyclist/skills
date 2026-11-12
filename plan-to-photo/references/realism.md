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
