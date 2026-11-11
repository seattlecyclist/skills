import bpy, bmesh, sys, math
from mathutils import Vector

S = sys.argv[sys.argv.index('--') + 1]
bpy.ops.wm.open_mainfile(filepath=S + '/scene.blend')
O = bpy.data.objects
col = bpy.context.scene.collection
IN = 0.0254

W_TOP, D_TOP, H = 22 * IN, 16 * IN, 22 * IN
T_TOP = 0.75 * IN
REVEAL = 0.125 * IN
OVER = 0.5 * IN
LEG = 1.75 * IN
LEG_FLOOR = 1.25 * IN
LEG_R = 0.375 * IN
AP_T = 0.75 * IN
AP_H = 3 * IN
DR_GAP = 0.0625 * IN
DR_ARC = 0.375 * IN
SHELF_Z = 5 * IN
SHELF_T = 0.75 * IN
W, D = W_TOP - 2 * OVER, D_TOP - 2 * OVER
Z_AP_TOP = H - T_TOP - REVEAL
Z_AP_BOT = Z_AP_TOP - AP_H

MAT = {a: bpy.data.materials['walnut_' + a] for a in 'XYZ'}


def finish(name, bm, mat, ease=0.0016):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    col.objects.link(o)
    if ease:
        b = o.modifiers.new('bevel', 'BEVEL')
        b.width = ease
        b.segments = 2
        b.limit_method = 'ANGLE'
        b.angle_limit = math.radians(40)
        b.harden_normals = False
    return o


def add_box(bm, x0, x1, y0, y1, z0, z1):
    vs = [bm.verts.new((x, y, z)) for z in (z0, z1) for y in (y0, y1) for x in (x0, x1)]
    idx = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    for f in idx:
        bm.faces.new([vs[i] for i in f])


def add_prism(bm, rings):
    vv = [[bm.verts.new(p) for p in r] for r in rings]
    n = len(rings[0])
    bm.faces.new(vv[0][::-1])
    bm.faces.new(vv[-1])
    for a, b in zip(vv[:-1], vv[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new([a[i], a[j], b[j], b[i]])


def leg_profile(s, z):
    pts = [(s, 0.0, z)]
    for k in range(6, -1, -1):
        t = math.radians(180 + 90 * k / 6)
        pts.append((LEG_R + LEG_R * math.cos(t), LEG_R + LEG_R * math.sin(t), z))
    pts += [(0.0, s, z), (s, s, z)]
    seen = []
    for p in pts:
        if not seen or (Vector(p) - Vector(seen[-1])).length > 1e-6:
            seen.append(p)
    return seen


def build(prefix, x0, y0):
    def corner(lx, ly, sx, sy):
        cx = x0 if sx > 0 else x0 + W
        cy = y0 if sy > 0 else y0 + D
        return cx + sx * lx, cy + sy * ly

    parts = []
    for i, (sx, sy) in enumerate(((1, 1), (-1, 1), (1, -1), (-1, -1))):
        bm = bmesh.new()
        rings = []
        for s, z in ((LEG_FLOOR, 0.0), (LEG, Z_AP_BOT)):
            rings.append([(*corner(px, py, sx, sy), pz) for px, py, pz in leg_profile(s, z)])
        if sx * sy < 0:
            rings = [r[::-1] for r in rings]
        add_prism(bm, rings)
        a0, a1 = corner(AP_T, AP_T, sx, sy)
        b0, b1 = corner(LEG, LEG, sx, sy)
        add_box(bm, min(a0, b0), max(a0, b0), min(a1, b1), max(a1, b1), Z_AP_BOT, Z_AP_TOP)
        parts.append(finish('%s_Leg_%d' % (prefix, i), bm, MAT['Z']))

    zm = (Z_AP_BOT + Z_AP_TOP) / 2
    bm = bmesh.new()
    add_box(bm, x0 + AP_T, x0 + W - AP_T, y0 + D - AP_T, y0 + D, Z_AP_BOT, Z_AP_TOP)
    add_box(bm, x0, x0 + AP_T, y0 + D - AP_T, y0 + D, zm, Z_AP_TOP)
    add_box(bm, x0 + W - AP_T, x0 + W, y0 + D - AP_T, y0 + D, zm, Z_AP_TOP)
    parts.append(finish(prefix + '_Apron_Back', bm, MAT['X']))
    for side, (xa, xb) in (('L', (x0, x0 + AP_T)), ('R', (x0 + W - AP_T, x0 + W))):
        bm = bmesh.new()
        add_box(bm, xa, xb, y0 + AP_T, y0 + D - AP_T, Z_AP_BOT, Z_AP_TOP)
        add_box(bm, xa, xb, y0, y0 + AP_T, Z_AP_BOT, zm)
        add_box(bm, xa, xb, y0 + D - AP_T, y0 + D, Z_AP_BOT, zm)
        parts.append(finish(prefix + '_Apron_' + side, bm, MAT['Y']))
    bm = bmesh.new()
    add_box(bm, x0, x0 + AP_T, y0, y0 + AP_T, zm, Z_AP_TOP)
    add_box(bm, x0 + AP_T, x0 + LEG, y0, y0 + AP_T, Z_AP_BOT, Z_AP_TOP)
    add_box(bm, x0 + W - AP_T, x0 + W, y0, y0 + AP_T, zm, Z_AP_TOP)
    add_box(bm, x0 + W - LEG, x0 + W - AP_T, y0, y0 + AP_T, Z_AP_BOT, Z_AP_TOP)
    parts.append(finish(prefix + '_Apron_FrontStubs', bm, MAT['X']))

    fx0, fx1 = x0 + LEG + DR_GAP, x0 + W - LEG - DR_GAP
    fz0, fz1 = Z_AP_BOT + DR_GAP, Z_AP_TOP - DR_GAP
    L = fx1 - fx0
    R = (L * L / 4 + DR_ARC * DR_ARC) / (2 * DR_ARC)
    n = 48
    bm = bmesh.new()
    front, back = [], []
    for yv, lst in ((y0, front), (y0 + AP_T, back)):
        bot, top = [], []
        for k in range(n + 1):
            x = fx0 + L * k / n
            u = x - (fx0 + fx1) / 2
            rise = math.sqrt(R * R - u * u) - (R - DR_ARC)
            bot.append(bm.verts.new((x, yv, fz0 + rise)))
            top.append(bm.verts.new((x, yv, fz1)))
        lst.extend([bot, top])
    for k in range(n):
        bm.faces.new([front[0][k], front[0][k + 1], front[1][k + 1], front[1][k]])
        bm.faces.new([back[0][k + 1], back[0][k], back[1][k], back[1][k + 1]])
        bm.faces.new([front[0][k + 1], front[0][k], back[0][k], back[0][k + 1]])
        bm.faces.new([front[1][k], front[1][k + 1], back[1][k + 1], back[1][k]])
    bm.faces.new([front[0][0], front[1][0], back[1][0], back[0][0]])
    bm.faces.new([front[0][n], back[0][n], back[1][n], front[1][n]])
    parts.append(finish(prefix + '_DrawerFront', bm, MAT['X']))

    bm = bmesh.new()
    add_box(bm, fx0 + 0.006, fx1 - 0.006, y0 + AP_T, y0 + D - AP_T - 0.01, fz0 + 0.004, fz1 - 0.004)
    parts.append(finish(prefix + '_DrawerBox', bm, MAT['X'], 0))

    s_at = LEG_FLOOR + (LEG - LEG_FLOOR) * (SHELF_Z + SHELF_T / 2) / Z_AP_BOT
    bm = bmesh.new()
    add_box(bm, x0 + s_at, x0 + W - s_at, y0 + s_at, y0 + D - s_at, SHELF_Z, SHELF_Z + SHELF_T)
    parts.append(finish(prefix + '_Shelf', bm, MAT['X']))

    bm = bmesh.new()
    tx0, ty0 = x0 - OVER, y0 - OVER
    add_box(bm, tx0, tx0 + W_TOP, ty0, ty0 + D_TOP, H - T_TOP, H)
    vert_edges = [e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > 1e-6]
    bmesh.ops.bevel(bm, geom=vert_edges, offset=LEG_R, segments=6, profile=0.5, affect='EDGES')
    parts.append(finish(prefix + '_Top', bm, MAT['X']))

    bm = bmesh.new()
    for cxs in (x0 + LEG + 0.03, x0 + W - LEG - 0.06):
        for cys in (y0 + 0.08, y0 + D - 0.11):
            add_box(bm, cxs, cxs + 0.03, cys, cys + 0.03, Z_AP_TOP - 0.012, H - T_TOP)
    parts.append(finish(prefix + '_Buttons', bm, MAT['X'], 0))
    return parts


for n in ('NS_L', 'NS_R', 'NS_L_pull', 'NS_R_pull'):
    if n in O:
        bpy.data.objects.remove(O[n])

WALL_GAP = 0.020
y_top_back = 2.256 - WALL_GAP
y0 = y_top_back - OVER - D
built = {}
for prefix, cx in (('NSL', -0.36), ('NSR', 2.036)):
    built[prefix] = build(prefix, cx - W / 2, y0)

dz = H - 0.56
for n in ('LampBaseL', 'LampBaseR', 'ShadeL', 'ShadeR', 'RodL', 'RodR', 'bulbL', 'bulbR', 'Vase', 'Book0', 'Book1', 'Pages0', 'Pages1'):
    if n in O:
        O[n].location.z += dz

dg = bpy.context.evaluated_depsgraph_get()
for prefix, parts in built.items():
    vs = []
    for o in parts:
        e = o.evaluated_get(dg)
        vs += [o.matrix_world @ v.co for v in e.data.vertices]
    lo = [min(v[i] for v in vs) for i in range(3)]
    hi = [max(v[i] for v in vs) for i in range(3)]
    print('NIGHTSTAND', prefix, 'x %.4f..%.4f y %.4f..%.4f z %.4f..%.4f' % (lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]))
print('DIMS in: top %.2f x %.2f x %.2f H, legs %.2f -> %.2f, apron %.2f x %.2f, drawer arc %.3f, shelf at %.2f, top z %.4f m vs mattress 0.554' % (
    W_TOP / IN, D_TOP / IN, H / IN, LEG / IN, LEG_FLOOR / IN, AP_H / IN, AP_T / IN, DR_ARC / IN, SHELF_Z / IN, H))
bpy.ops.wm.save_as_mainfile(filepath=S + '/scene_v6.blend')
print('SAVED_V6')
