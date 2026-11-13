# SketchUp plans (.skp)

A .skp file is the best plan input there is: the author's exact 3D model, so nothing is read off a
drawing. The format is closed and nothing in a Linux container reads it, so the export runs inside
SketchUp on the user's Mac or PC, and the rest of the skill runs anywhere.

```
plan.skp ─(SketchUp + export_for_p2p.rb)→ export/ ─(skp_import.py)→ out/model.obj, cameras.txt, materials.md
         → line_drawing.py → nano_banana.py        (or build_scene.py for the Blender path)
```

## 1. Export in SketchUp

Needs SketchUp desktop: Make 2017 or newer, or any Pro. It does not need Pro's OBJ exporter, and the
free web version can't run Ruby. If the user only has the web version, ask for an OBJ, DAE or STL
from someone with Pro, or fall back to the PDF route in `drawings.md`.

1. Open the plan and pick the scene that shows the **assembled** piece. Turn off tags for exploded
   views, cut-list layouts, dimensions and people. Or select just the assembled piece: a selection
   is exported instead of everything visible.
2. Window > Ruby Console, then:
   ```ruby
   load "/path/to/plan-to-photo/scripts/sketchup/export_for_p2p.rb"
   P2P.export("/path/to/export")
   ```
   Copying the file into SketchUp's Plugins folder adds Extensions > Export for plan-to-photo.
3. Send the `export/` folder (model.obj, parts.json, scenes.json) to wherever the skill runs.

What the script writes:
- `model.obj`: meters, Z up, one `o` object per part, a `usemtl` per SketchUp material, and vertex
  normals that are smooth across soft and smooth edges. Each group or component that holds faces
  is a part; nested ones are parts of their own; loose faces are one more part.
- `parts.json`: every part's name, path in the hierarchy, main material, size in inches as placed,
  and the model's material list with colours and texture file names.
- `scenes.json`: the current view and every saved scene's camera, in meters, with a horizontal
  field of view widened as needed so a 3:2 frame crops nothing the author framed.

When a Remote Control session on the user's Mac is available, it can run the export itself: open
SketchUp with the file and run the two Ruby lines in the console.

## 2. Clean it up

```bash
python3 scripts/skp_import.py export/ out/                       # prints what it drops and the size
python3 scripts/skp_import.py export/ out/ --drop 'jig|clamp'    # drop more by name
python3 scripts/skp_import.py export/ out/ --keep 'shelf' --all  # keep everything
```

It drops parts named like extras (people, dimensions, labels), then groups the rest by touching
bounding boxes and keeps the biggest group, so an exploded view or a second copy falls away. It
moves the front-left-bottom corner to the origin (cameras move with it) and prints the size in
meters and inches. **Check the printed size and the dropped list against the plan before going
on.** A part that sits apart from the piece on purpose (a loose shelf pin, a lid shown open) needs
`--keep`.

It also takes a plain OBJ. One exported by SketchUp Pro in inches needs `--scale 0.0254`.

## 3. Draw and photograph

`cameras.txt` has `line_drawing.py` arguments for every saved perspective scene (the author's own
views, usually the best ones) and a default 3/4 view. For another angle use
`scripts/frame_camera.py out/model.obj --az 35 --el 18`.

```bash
python3 scripts/line_drawing.py out/model.obj lines.jpg $(sed -n 2p out/cameras.txt)
GEMINI_API_KEY=... python3 scripts/nano_banana.py lines.jpg spec.md room.md photo.jpg --takes 2
```

Write `spec.md` from `materials.md`, but don't trust SketchUp material names: authors often leave
a default ("Wood Cherry Original" on a walnut plan) or use one colour for everything. Take the wood
and finish from the plan's text or cut list. Say paint as paint ("solid opaque paint, no grain"),
or Nano Banana turns "painted dark walnut" into walnut.

## Gotchas

- Parallel-projection scenes are skipped; `line_drawing.py` is perspective only.
- A scene looking straight down or rolled still draws with Z up.
- Hidden geometry is not exported. If a part is missing, check its tag and Hide state in SketchUp.
- Parts seen through an opening (a far-side slat through an arch) can be drawn by Nano Banana as
  extra parts. Pick a camera that doesn't look through the opening, or say the count in spec.md.
