"""Walnut castle-leg bed: the parts rebuilt by hand, and the matching nightstands.

Runs inside build_scene.py after the model, room and props (SPEC, M, WOOD, MODEL and every p2p
helper are in scope). Coordinates are the plan's, in inches, with the foot-left outside leg corner at
the origin and the headboard at +Y; the model sits on the rug (RUG meters up).

Why rebuild: the plan's legs are boxes with a taper and its headboard boards are faceted arcs. The
camera sees both up close, so they are modelled here as the real thing: a 3/4" radius on the one
outside corner, tapered inside faces, castle slots at the top, and headboard boards on a true
parabolic curve with radiused top corners.
"""
import math, bmesh
from mathutils import Vector

RUG = SPEC['model']['offset'][2]
WAL = WOOD['walnut']
built = []

# ---- legs: 3" square, 3/4" radius outside corner, tapering to 2-1/4" at the floor, castle slots
W, D = 66.0, 86.0
LS, legH, foot, taperTop, R = 3.0, 13.0, 2.25, 8.0, 0.75


def leg_ring(z):
    s = foot + (LS - foot) * min(z, taperTop) / taperTop
    pts = [(R + R * math.cos(math.pi + math.pi / 2 * i / 8), R + R * math.sin(math.pi + math.pi / 2 * i / 8)) for i in range(9)]
    return pts + [(s, 0), (s, s), (0, s)]


for li, (cx, cy, sx, sy) in enumerate([(0, 0, 1, 1), (W, 0, -1, 1), (0, D, 1, -1), (W, D, -1, -1)]):
    zs = (0, taperTop, legH); rings = [leg_ring(z) for z in zs]; n = len(rings[0])
    verts = [((cx + sx * u) * IN, (cy + sy * v) * IN, z * IN + RUG) for ring, z in zip(rings, zs) for (u, v) in ring]
    faces = [(j * n + i, j * n + (i + 1) % n, j * n + (i + 1) % n + n, j * n + i + n) for j in range(2) for i in range(n)]
    faces += [tuple(reversed(range(n))), tuple(range(2 * n, 3 * n))]
    o = mk_obj('Leg_%d' % li, verts, faces, WAL['Z']); recalc(o)
    zb = (legH - 4) * IN + RUG
    x0, x1 = sorted(((cx + sx * 1) * IN, (cx + sx * 2) * IN)); y0, y1 = sorted(((cy + sy * 1) * IN, (cy + sy * 2) * IN))
    boolean(o, box('c1', x0, min(cy - sy * 1, cy + sy * 4) * IN, zb, x1, max(cy - sy * 1, cy + sy * 4) * IN, 1))
    boolean(o, box('c2', min(cx - sx * 1, cx + sx * 4) * IN, y0, zb, max(cx - sx * 1, cx + sx * 4) * IN, y1, 1))
    ease(o, 0.0015, 3); built.append(o)

# ---- headboard: two 1" boards on a true parabolic curve, 1-1/2" rise, 1/4" gap, radiused top corners
HB_top, rise, gapZ, gap, t, N = 44.0, 1.5, 30.0, 0.25, 1.0, 240
par = lambda x: 1 - ((x - W / 2) / (W / 2)) ** 2
yt = lambda x: HB_top - rise * par(x); yb = lambda x: gapZ + rise * par(x); yl = lambda x: yb(x) - gap
top = [(x, yb(x)) for x in [W * i / N for i in range(N + 1)]]
top += [(W, HB_top - R)] + [(W - R + R * math.cos(math.pi / 2 * i / 8), HB_top - R + R * math.sin(math.pi / 2 * i / 8)) for i in range(1, 9)]
top += [(x, yt(x)) for x in [W - R - (W - 2 * R) * i / N for i in range(1, N)]]
top += [(R + R * math.cos(math.pi / 2 + math.pi / 2 * i / 8), HB_top - R + R * math.sin(math.pi / 2 + math.pi / 2 * i / 8)) for i in range(0, 9)]
low = [(0, 9.0), (W, 9.0)] + [(x, yl(x)) for x in [W - W * i / N for i in range(N + 1)]]
for nm, poly in (('HB_Top', top), ('HB_Lower', low)):
    o = extrude(nm, [(x * IN, z * IN + RUG) for x, z in poly], D * IN, (D + t) * IN, WAL['X'])
    ease(o, 0.0015, 3, 30); built.append(o)
MODEL.extend(built)   # so the bedding collides with them

# ---- nightstands: 22 x 16 x 22 in, same walnut and design language
W_TOP, D_TOP, H = 22 * IN, 16 * IN, 22 * IN
T_TOP, REVEAL, OVER = 0.75 * IN, 0.125 * IN, 0.5 * IN
LEG, LEG_FLOOR, LEG_R = 1.75 * IN, 1.25 * IN, 0.375 * IN
AP_T, AP_H, DR_GAP, DR_ARC = 0.75 * IN, 3 * IN, 0.0625 * IN, 0.375 * IN
SHELF_Z, SHELF_T = 5 * IN, 0.75 * IN
NW, ND = W_TOP - 2 * OVER, D_TOP - 2 * OVER
Z_AP_TOP = H - T_TOP - REVEAL; Z_AP_BOT = Z_AP_TOP - AP_H


def part(name, bm, m, e=0.0016):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.materials.append(m)
    o = bpy.data.objects.new(name, me); col().objects.link(o)
    if e: ease(o, e)
    return o


def add_box(bm, x0, x1, y0, y1, z0, z1):
    vs = [bm.verts.new((x, y, z)) for z in (z0, z1) for y in (y0, y1) for x in (x0, x1)]
    for f in [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]: bm.faces.new([vs[i] for i in f])


def add_prism(bm, rings):
    vv = [[bm.verts.new(p) for p in r] for r in rings]; n = len(rings[0])
    bm.faces.new(vv[0][::-1]); bm.faces.new(vv[-1])
    for a, b in zip(vv[:-1], vv[1:]):
        for i in range(n): j = (i + 1) % n; bm.faces.new([a[i], a[j], b[j], b[i]])


def leg_profile(s, z):
    pts = [(s, 0.0, z)] + [(LEG_R + LEG_R * math.cos(math.radians(180 + 90 * k / 6)), LEG_R + LEG_R * math.sin(math.radians(180 + 90 * k / 6)), z) for k in range(6, -1, -1)]
    pts += [(0.0, s, z), (s, s, z)]; out = []
    for p in pts:
        if not out or (Vector(p) - Vector(out[-1])).length > 1e-6: out.append(p)
    return out


def nightstand(prefix, x0, y0):
    def corner(lx, ly, sx, sy):
        return (x0 if sx > 0 else x0 + NW) + sx * lx, (y0 if sy > 0 else y0 + ND) + sy * ly
    for i, (sx, sy) in enumerate(((1, 1), (-1, 1), (1, -1), (-1, -1))):
        bm = bmesh.new()
        rings = [[(*corner(px, py, sx, sy), pz) for px, py, pz in leg_profile(s, z)] for s, z in ((LEG_FLOOR, 0.0), (LEG, Z_AP_BOT))]
        if sx * sy < 0: rings = [r[::-1] for r in rings]
        add_prism(bm, rings)
        a0, a1 = corner(AP_T, AP_T, sx, sy); b0, b1 = corner(LEG, LEG, sx, sy)
        add_box(bm, min(a0, b0), max(a0, b0), min(a1, b1), max(a1, b1), Z_AP_BOT, Z_AP_TOP)
        part('%s_Leg_%d' % (prefix, i), bm, WAL['Z'])
    zm = (Z_AP_BOT + Z_AP_TOP) / 2
    bm = bmesh.new()
    add_box(bm, x0 + AP_T, x0 + NW - AP_T, y0 + ND - AP_T, y0 + ND, Z_AP_BOT, Z_AP_TOP)
    add_box(bm, x0, x0 + AP_T, y0 + ND - AP_T, y0 + ND, zm, Z_AP_TOP)
    add_box(bm, x0 + NW - AP_T, x0 + NW, y0 + ND - AP_T, y0 + ND, zm, Z_AP_TOP)
    part(prefix + '_Apron_Back', bm, WAL['X'])
    for side, (xa, xb) in (('L', (x0, x0 + AP_T)), ('R', (x0 + NW - AP_T, x0 + NW))):
        bm = bmesh.new()
        add_box(bm, xa, xb, y0 + AP_T, y0 + ND - AP_T, Z_AP_BOT, Z_AP_TOP)
        add_box(bm, xa, xb, y0, y0 + AP_T, Z_AP_BOT, zm); add_box(bm, xa, xb, y0 + ND - AP_T, y0 + ND, Z_AP_BOT, zm)
        part(prefix + '_Apron_' + side, bm, WAL['Y'])
    bm = bmesh.new()
    add_box(bm, x0, x0 + AP_T, y0, y0 + AP_T, zm, Z_AP_TOP); add_box(bm, x0 + AP_T, x0 + LEG, y0, y0 + AP_T, Z_AP_BOT, Z_AP_TOP)
    add_box(bm, x0 + NW - AP_T, x0 + NW, y0, y0 + AP_T, zm, Z_AP_TOP); add_box(bm, x0 + NW - LEG, x0 + NW - AP_T, y0, y0 + AP_T, Z_AP_BOT, Z_AP_TOP)
    part(prefix + '_Apron_FrontStubs', bm, WAL['X'])
    # drawer front with a shallow arc finger pull along its bottom edge
    fx0, fx1 = x0 + LEG + DR_GAP, x0 + NW - LEG - DR_GAP; fz0, fz1 = Z_AP_BOT + DR_GAP, Z_AP_TOP - DR_GAP
    Lr = fx1 - fx0; Rr = (Lr * Lr / 4 + DR_ARC * DR_ARC) / (2 * DR_ARC)
    poly = [(fx0 + Lr * k / 48, fz0 + math.sqrt(Rr * Rr - (Lr * k / 48 - Lr / 2) ** 2) - (Rr - DR_ARC)) for k in range(49)] + [(fx1, fz1), (fx0, fz1)]
    o = extrude(prefix + '_DrawerFront', poly, y0, y0 + AP_T, WAL['X']); ease(o, 0.0016)
    bm = bmesh.new(); add_box(bm, fx0 + 0.006, fx1 - 0.006, y0 + AP_T, y0 + ND - AP_T - 0.01, fz0 + 0.004, fz1 - 0.004)
    part(prefix + '_DrawerBox', bm, WAL['X'], 0)
    s_at = LEG_FLOOR + (LEG - LEG_FLOOR) * (SHELF_Z + SHELF_T / 2) / Z_AP_BOT
    bm = bmesh.new(); add_box(bm, x0 + s_at, x0 + NW - s_at, y0 + s_at, y0 + ND - s_at, SHELF_Z, SHELF_Z + SHELF_T)
    part(prefix + '_Shelf', bm, WAL['X'])
    bm = bmesh.new(); tx0, ty0 = x0 - OVER, y0 - OVER
    add_box(bm, tx0, tx0 + W_TOP, ty0, ty0 + D_TOP, H - T_TOP, H)
    bmesh.ops.bevel(bm, geom=[e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > 1e-6], offset=LEG_R, segments=6, profile=0.5, affect='EDGES')
    part(prefix + '_Top', bm, WAL['X'])
    bm = bmesh.new()
    for cxs in (x0 + LEG + 0.03, x0 + NW - LEG - 0.06):
        for cys in (y0 + 0.08, y0 + ND - 0.11): add_box(bm, cxs, cxs + 0.03, cys, cys + 0.03, Z_AP_TOP - 0.012, H - T_TOP)
    part(prefix + '_Buttons', bm, WAL['X'], 0)


y_back = ROOM['y'][1] - 0.020 - OVER - ND
for prefix, cx in (('NSL', -0.36), ('NSR', 2.036)):
    nightstand(prefix, cx - NW / 2, y_back)
print('WALNUT BED legs, headboard and two nightstands built; nightstand top at %.3f m' % H)
