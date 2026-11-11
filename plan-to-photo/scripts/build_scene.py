"""Build a photoreal scene from a scene spec and save it as a .blend.

    blender -b -P build_scene.py -- scene.json [out.blend]
    python build_scene.py -- scene.json [out.blend]        (with the `bpy` pip package)

The spec (references/scene-spec.md) names the model to import, the materials (scanned PBR sets or
fallbacks), which parts get which material, the room, the rug, declarative props, and any number of
`dress` scripts for the parts that need hand modelling (rebuilt curves, bedding, a kitchen's
fruit bowl). Lights and camera are added at render time by render.py, so one scene renders many
views.
"""
import bpy, sys, os, json, re, math

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import p2p
from p2p import *

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
SPEC_PATH = os.path.abspath(argv[0])
DIR = os.path.dirname(SPEC_PATH)
SPEC = json.load(open(SPEC_PATH))
OUT = os.path.abspath(argv[1]) if len(argv) > 1 else os.path.join(DIR, SPEC.get('out', 'scene.blend'))
ASSETS = os.path.join(DIR, SPEC.get('assets', 'assets'))


def P(p):
    """Resolve a path from the spec: absolute, relative to the spec, or a set name under assets/."""
    if p is None: return None
    if os.path.isabs(p): return p
    for base in (DIR, ASSETS):
        q = os.path.join(base, p)
        if os.path.exists(q): return q
    return os.path.join(ASSETS, p)


bpy.ops.wm.read_factory_settings(use_empty=True)
UNITS = {'m': 1.0, 'cm': 0.01, 'mm': 0.001, 'in': IN, 'ft': 12 * IN}

# ---------------------------------------------------------------- materials
M = {}
WOOD = {}
for name, d in SPEC.get('materials', {}).items():
    d = dict(d); kind = d.pop('type')
    if 'set' in d: d['set_dir'] = P(d.pop('set'))
    for k in ('tone', 'color', 'rough', 'hsv', 'procedural', 'tint'):
        if k in d and isinstance(d[k], list): d[k] = tuple(tuple(x) if isinstance(x, list) else x for x in d[k])
    if kind == 'wood':
        WOOD[name] = wood_set(name, **d); M[name] = WOOD[name]['X']
    elif kind == 'planks': M[name] = planks(name, **d)
    elif kind == 'surface': M[name] = surface(name, **d)
    elif kind == 'fabric': M[name] = fabric(name, **d)
    elif kind == 'paint': M[name] = paint(name, **d)
    elif kind == 'plain': M[name] = plain(name, **d)
    elif kind == 'metal': M[name] = metal(name, **d)
    elif kind == 'glass': M[name] = glass(name, **d)
    elif kind == 'translucent': M[name] = translucent(name, **d)
    elif kind == 'emissive': M[name] = emissive(name, **d)
    elif kind == 'canvas': M[name] = abstract_canvas(name, **d)
    else: raise SystemExit('unknown material type ' + kind)
    missing = d.get('set_dir') and not find_maps(d['set_dir'])
    print('MATERIAL', name, kind, '(fallback: texture set not found at %s)' % d['set_dir'] if missing else '')


def mat(name, axis='X'):
    if name in WOOD: return WOOD[name][axis]
    return M[name]


# ---------------------------------------------------------------- model
MODEL = []
md = SPEC.get('model')
if md:
    objs = import_model(P(md['file']), scale=UNITS.get(md.get('units', 'm'), 1.0))
    skip = [re.compile(s) for s in md.get('skip', [])]
    for o in list(objs):
        if any(s.search(o.name) for s in skip):
            bpy.data.objects.remove(o); objs.remove(o)
    if 'offset' in md:  # keep the plan's own coordinates (needed when dress scripts rebuild parts in them)
        T = Matrix.Translation(Vector(md['offset']))
        for o in objs: o.data.transform(T); o.data.update()
        lo, hi = bounds(objs, evaluated=False)
    else:
        lo, hi = place_on_floor(objs, z=md.get('floor_z', 0.0), at=md.get('at'), rotate_z=md.get('rotate_z', 0.0))
    print('MODEL %d objects, bbox %s .. %s m' % (len(objs), tuple(round(v, 3) for v in lo), tuple(round(v, 3) for v in hi)))
    rules = [(re.compile(r['match'], re.I), r) for r in md.get('assign', [])]
    for o in objs:
        src = o.data.materials[0].name if o.data.materials else ''
        rule = next((r for rx, r in rules if rx.search(o.name) or rx.search(src)), None)
        name = rule['material'] if rule else md.get('default', next(iter(M)))
        axis = (rule or {}).get('axis') or long_axis(o)
        if md.get('clean', True): dissolve_flat(o)
        o.data.materials.clear(); o.data.materials.append(mat(name, axis))
        if (rule or {}).get('ease_mm', md.get('ease_mm', 1.2)): ease(o, (rule or {}).get('ease_mm', md.get('ease_mm', 1.2)) * MM)
    MODEL = objs

# ---------------------------------------------------------------- room
ROOM = SPEC.get('room')
if ROOM:
    rm = {k: mat(v) for k, v in ROOM.get('materials', {}).items()}
    build_room(ROOM, rm)
    if ROOM.get('rug'):
        r = ROOM['rug']; rug('Rug', r['x'][0], r['y'][0], r['x'][1], r['y'][1], mat(r['material']), r.get('thick', 0.008))

# ---------------------------------------------------------------- props
for i, pr in enumerate(SPEC.get('props', [])):
    k = pr['kind']; nm = pr.get('name', '%s%d' % (k, i))
    if k == 'lamp': lamp(nm, *pr['at'], mat(pr['base']), mat(pr['shade']), mat(pr['rod']), pr.get('watts', 18))
    elif k == 'books': books(nm, *pr['at'], [mat(m) for m in pr['covers']], mat(pr['pages']))
    elif k == 'vessel': vessel(nm, pr['type'], *pr['at'], mat(pr['material']), pr.get('scale', 1.0))
    elif k == 'art': art(nm, *pr['x'], *pr['z'], pr['wall_y'], mat(pr['frame']), mat(pr['canvas']))
    elif k == 'box':
        o = box(nm, *pr['min'], *pr['max'], mat(pr['material'], pr.get('axis', 'X')))
        if pr.get('ease_mm', 1.5): ease(o, pr.get('ease_mm', 1.5) * MM)
    else: raise SystemExit('unknown prop kind ' + k)

# ---------------------------------------------------------------- dress scripts
NS = dict(vars(p2p)); NS.update(M=M, WOOD=WOOD, mat=mat, MODEL=MODEL, SPEC=SPEC, ROOM=ROOM, DIR=DIR, ASSETS=ASSETS, P=P, HERE=HERE)
for d in SPEC.get('dress', []):
    path = P(d) if not os.path.exists(os.path.join(HERE, 'dress', d)) else os.path.join(HERE, 'dress', d)
    print('DRESS', path)
    exec(compile(open(path).read(), path, 'exec'), NS)

clear_collisions()
save(OUT)
