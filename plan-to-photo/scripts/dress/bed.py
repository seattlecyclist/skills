"""Dress a bed frame: mattress, cloth-sim duvet folded back, creased pillows leaning on the
headboard and pressed into the mattress, a lumbar cushion and a throw. Runs inside build_scene.py
(names like SPEC, M, MODEL, mat and every p2p helper are in scope).

SPEC['bed'] (meters, bed facing -Y with the headboard at +Y):
  opening     [x0, y0, x1, y1]  inner faces of the rails: the mattress fills this exactly
  deck_z      top of the slats or platform the mattress sits on
  mattress_h  mattress thickness (default 0.254, 10")
  headboard_y front face of the headboard where pillows lean (default y1 of the opening)
  materials   {sheet, duvet, pillow, sham, throw}: names from SPEC['materials']
  throw       true/false (default true); throw_side +1 or -1 (which side it hangs off, default +1)
  lumbar      true/false (default true)

Lessons baked in (references/realism.md):
- The mattress fills the frame opening and has a flat bottom. A mattress narrower than the rails, or
  one rounded underneath by subsurf, lets light through the slats and paints slat stripes on the
  floor beside the bed (walnut bed v3).
- Pillows lean on the headboard and dent the mattress; 1 cm of air under a pillow reads as floating.
- Pillows get sculpted creases, corner pulls and a centre sag; smooth inflated cases read as vinyl.
"""
import math
import numpy as np
from mathutils import Vector, Euler
from mathutils.bvhtree import BVHTree

B = SPEC['bed']
bx0, by0, bx1, by1 = B['opening']
DECK = B['deck_z']
MH = B.get('mattress_h', 0.254)
ZM = DECK + MH
YH = B.get('headboard_y', by1)
BM = {k: mat(v) for k, v in B['materials'].items()}
cx = (bx0 + bx1) / 2; mw = bx1 - bx0; ml = by1 - by0

# mattress: fills the opening, flat bottom, rounded top edges only
import bmesh
bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
for v in bm.verts:
    v.co = Vector((bx0 if v.co.x < 0 else bx1, by0 if v.co.y < 0 else by1, DECK if v.co.z < 0 else ZM))
top = [e for e in bm.edges if all(v.co.z > ZM - 0.001 for v in e.verts)]
bmesh.ops.bevel(bm, geom=top, offset=0.035, segments=6, profile=0.5, affect='EDGES')
me = bpy.data.meshes.new('Mattress'); bm.to_mesh(me); bm.free()
matt = bpy.data.objects.new('Mattress', me); col().objects.link(matt); me.materials.append(BM['sheet'])
for p in me.polygons: p.use_smooth = p.normal.z > 0.05
print('BED mattress %.3f x %.3f x %.3f m, top at %.3f' % (mw, ml, MH, ZM))

for o in MODEL + [matt]: add_collision(o)
for n in ('Rug', 'Floor'):
    if n in bpy.data.objects: add_collision(bpy.data.objects[n])

# duvet, folded back at 65% of the length
ztop = ZM + 0.035; DW = mw + 0.30; y0 = by0 - 0.13; yf = by0 + 0.65 * ml; rr = 0.022; back_len = 0.42
L1 = yf - y0; L2 = math.pi * rr; Lt = L1 + L2 + back_len


def duvet_fn(u, v):
    x = cx - DW / 2 + DW * u; s = v * Lt
    if s <= L1: return (x, y0 + s, ztop)
    if s <= L1 + L2:
        a = (s - L1) / rr; return (x, yf + rr * math.sin(a), ztop + rr - rr * math.cos(a))
    return (x, yf - (s - L1 - L2), ztop + 2 * rr)


nu = max(40, int(DW / 0.024)); nv = max(60, int(Lt / 0.024))
duvet = grid('Duvet', nu, nv, duvet_fn, BM['duvet'])
run_cloth(duvet, 55, mass=0.5, bend=1.5, tension=10, dist=0.008, selfd=0.009)
wrinkle(duvet, seed=B.get('wrinkle_seed', 7))
duvet.modifiers.new('sol', 'SOLIDIFY').thickness = 0.014
duvet.modifiers.new('sub', 'SUBSURF').render_levels = 2; smooth(duvet)

# pillows
n_p = 1 if mw < 1.2 else 2
psx = 0.46 if mw > 1.8 else min(0.37, mw / (2 * n_p) - 0.01)
pillows = []
for i in range(n_p):
    o = pillow('Pillow%d' % i, psx, 0.24, 0.075, BM['pillow'], seed=2 + i)
    creases(o, seed=11 + 12 * i, depth=0.009)
    o.rotation_euler = Euler((math.radians(63 - 2 * i), 0, math.radians((-1) ** i * 1.5)))
    o.location = (cx + (i - (n_p - 1) / 2) * 2 * psx, YH - 0.2, ZM + 0.2)
    bake_world(o); lean_on(o, 'y', YH); rest_on(o, ZM, 0.024)
    pillows.append(o)
soft = list(pillows)
if B.get('lumbar', True):
    lum = pillow('Lumbar', min(0.27, mw * 0.18), 0.16, 0.06, BM.get('sham', BM['pillow']), seed=3)
    creases(lum, seed=37, depth=0.004)
    lum.rotation_euler = Euler((math.radians(70), 0, math.radians(-3))); lum.location = (cx + 0.05, YH - 0.5, ZM + 0.15)
    bake_world(lum); rest_on(lum, ZM, 0.018)
    dg = bpy.context.evaluated_depsgraph_get(); dg.update()
    trees = [BVHTree.FromObject(o, dg) for o in pillows]

    def front(x, z):
        best = np.inf
        for t in trees:
            hit = t.ray_cast(Vector((x, YH - 1.2, z)), Vector((0, 1, 0)), 2.0)
            if hit[0] is not None: best = min(best, hit[0].y)
        return best
    Lv = getv(lum); fr = np.array([front(v[0], v[2]) for v in Lv]); fin = np.isfinite(fr)
    if fin.any():
        Lv[:, 1] += 0.010 - np.max(Lv[fin, 1] - fr[fin]); Lv[fin, 1] = smin(Lv[fin, 1], fr[fin] + 0.001, 0.012)
        setv(lum, Lv)
    soft.append(lum)
d = press_into(matt, soft)
for o in soft:
    lo, hi = bounds(o, evaluated=False)
    print('BED %s back %.3f (headboard %.3f) bottom %.3f (mattress %.3f)' % (o.name, hi.y, YH, lo.z, ZM))
print('BED mattress dent %.1f mm' % (d * 1000))

# throw across the foot
if B.get('throw', True):
    side = B.get('throw_side', 1)
    dz = max((duvet.matrix_world @ Vector(v.co)).z for v in duvet.data.vertices) + 0.06
    add_collision(duvet, 0.012)
    for o in soft: add_collision(o, 0.006)
    TW, TL = 0.62, mw + 0.03
    ty = by0 + 0.24 * ml

    def throw_fn(u, v):
        X = TL * (v - 0.5) + side * 0.12; Y = TW * (u - 0.5); a = 0.12 * side
        return (cx + X * math.cos(a) - Y * math.sin(a), ty + X * math.sin(a) + Y * math.cos(a), dz + 0.05 + 0.04 * math.sin(9 * v + 2 * u) * math.sin(5 * u))
    throw = grid('Throw', 46, 120, throw_fn, BM['throw'])
    run_cloth(throw, 70, mass=0.35, bend=0.25, tension=10, dist=0.006, selfd=0.006)
    throw.modifiers.new('sol', 'SOLIDIFY').thickness = 0.01
    throw.modifiers.new('sub', 'SUBSURF').levels = 1; smooth(throw)
