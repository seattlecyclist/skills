# scene.json

One file describes the scene. `build_scene.py` reads it and saves a .blend; `render.py` lights and
frames that .blend. Paths are relative to the spec, or set names under `assets`. Meters, Z up. The
full worked file is `examples/walnut-bed/scene.json`.

```jsonc
{
  "assets": "assets",                // folder of texture sets (one folder per set) and assets/hdri/
  "out": "scene.blend",
  "materials": {                      // name -> definition; names are used everywhere below
    "walnut":  {"type": "wood", "set": "walnut_veneer_02", "tone": [0.24, 0.205, 0.19], "gamma": 1.5, "rough": [0.32, 0.5]},
    "floor":   {"type": "planks", "set": "white_oak_veneer", "plank_w": 0.185, "plank_l": 1.7},
    "counter": {"type": "surface", "set": "marble_01", "tile": 0.8, "rough": [0.15, 0.3], "coat": 0.3},
    "rug":     {"type": "surface", "set": "Carpet016", "tile": 0.45, "sheen": 1.0, "color": [0.55, 0.51, 0.44]},
    "linen":   {"type": "fabric", "color": [0.60, 0.55, 0.47], "set": "rough_linen", "tile": 0.27},
    "wall":    {"type": "paint", "color": [0.70, 0.67, 0.62]},
    "trim":    {"type": "plain", "color": [0.74, 0.72, 0.68], "rough": 0.45},
    "brass":   {"type": "metal", "color": [0.8, 0.6, 0.35], "rough": 0.3},
    "glass":   {"type": "glass"},
    "shade":   {"type": "translucent", "color": [0.9, 0.8, 0.62], "mix": 0.5},
    "led":     {"type": "emissive", "color": [1, 0.8, 0.6], "strength": 8},
    "canvas":  {"type": "canvas"}
  },
  "model": {
    "file": "model.obj",              // .obj .glb .gltf .fbx .stl .ply
    "units": "m",                     // m, cm, mm, in, ft (export_obj.js writes meters)
    "at": [0.1, 0.2], "rotate_z": 0,  // sit on the floor with the bbox min corner at (x, y) ...
    "floor_z": 0.0,
    "offset": [0, 0, 0.008],          // ... or keep the file's own coordinates, moved by this
    "skip": ["^P1_"],                 // regexes on object names to drop (parts rebuilt in a dress script)
    "assign": [{"match": "hard_maple", "material": "maple", "axis": null, "ease_mm": 1.2}],
    "default": "walnut",              // rules match object names or the file's material names;
    "ease_mm": 1.2                    // wood materials pick the grain axis from each part's longest side
  },
  "room": {                           // null for outdoor scenes
    "x": [-1.35, 3.05], "y": [-3.4, 2.256], "height": 2.7,
    "materials": {"floor": "floor", "wall": "wall", "wall_back": "accent", "trim": "trim",
                  "ceiling": "ceiling", "sheer": "sheer", "rod": "steel"},
    "windows": [{"wall": "left", "from": -0.75, "to": 0.95, "sill": 0.55, "head": 2.35,
                 "muntins": true, "meeting_rail": 1.64, "curtains": true}],
    "omit_walls": [],                 // e.g. ["front"] when the camera stands outside the room
    "baseboard": 0.11,
    "rug": {"x": [-0.38, 2.06], "y": [-0.95, 2.2], "material": "rug"}
  },
  "props": [
    {"kind": "lamp", "at": [x, y, z], "base": "ceramic", "shade": "shade", "rod": "brass", "watts": 18},
    {"kind": "books", "at": [x, y, z], "covers": ["book_blue", "book_tan"], "pages": "pages"},
    {"kind": "vessel", "type": "vase|bowl|jar|mug|bottle|pot", "at": [x, y, z], "material": "ceramic", "scale": 1},
    {"kind": "art", "x": [x0, x1], "z": [z0, z1], "wall_y": 2.256, "frame": "oak", "canvas": "canvas"},
    {"kind": "box", "min": [x, y, z], "max": [x, y, z], "material": "walnut", "axis": "X"}
  ],
  "dress": ["my_parts.py", "bed.py"], // run in order; bare names are looked up in scripts/dress/ first
  "bed": { ... },                     // read by dress/bed.py, see its docstring
  "render": { ... }                   // not read by the scripts; keep the render command's values here as a record
}
```

## Dress scripts

A dress script is plain Python run inside the build with every `p2p` helper in scope plus:
`SPEC`, `M` (materials by name), `WOOD` (wood materials by name, then grain axis), `mat(name, axis)`,
`MODEL` (imported objects; append rebuilt parts so cloth collides with them), `ROOM`, `DIR`,
`ASSETS`, `P(path)`. Use them for parts the camera sees up close that need real curves, and for any
dressing the props list can't express. `examples/walnut-bed/walnut_bed.py` rebuilds the bed's legs
and curved headboard and adds matching nightstands.

## Room frame

Walls are named by the side they bound: `left` is x = x0, `right` x = x1, `front` y = y0 (behind
the camera, usually), `back` y = y1. Windows give `from`/`to` along the wall (y for left/right, x for
front/back) and `sill`/`head` heights. Put the hero piece against the back wall facing -Y and the
camera in front of it.
