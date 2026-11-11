import bpy, bmesh, sys, math
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

S = sys.argv[sys.argv.index('--') + 1]
A = S + '/assets/'
bpy.ops.wm.open_mainfile(filepath=S + '/scene_v2.blend')
O = bpy.data.objects
YH = 2.184
ZM = 0.554
MX0, MX1, MY0, MY1 = 0.051, 1.626, 0.051, 2.134
MZ0 = 0.3
GY0 = 1.2
RES = 0.005


def smin(a, b, k):
    h = np.maximum(k - np.abs(a - b), 0.0) / k
    return np.minimum(a, b) - h * h * k * 0.25


def smax(a, b, k):
    return -smin(-a, -b, k)


def apply_mod(o, mtype):
    for m in list(o.modifiers):
        if m.type == mtype:
            with bpy.context.temp_override(object=o, active_object=o):
                bpy.ops.object.modifier_apply(modifier=m.name)


def creases(P, seed, depth):
    rng = np.random.default_rng(seed)
    a, b, c = np.abs(P).max(0)
    x, y, z = P[:, 0] / a, P[:, 1] / b, P[:, 2] / c
    nrm = np.stack([x / a, y / b, z / c], 1)
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
    off = np.zeros(len(P))
    X, Y = P[:, 0], P[:, 1]
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = sx * a * 0.97, sy * b * 0.95
            base = math.atan2(-cy, -cx)
            for k in range(rng.integers(3, 6)):
                ang = base + rng.uniform(-0.55, 0.55)
                dx, dy = math.cos(ang), math.sin(ang)
                rx, ry = X - cx, Y - cy
                t = rx * dx + ry * dy
                dist = np.abs(-rx * dy + ry * dx)
                ln = rng.uniform(0.10, 0.24)
                w = rng.uniform(0.004, 0.009)
                fade = np.clip(t / 0.02, 0, 1) * np.exp(-np.clip(t, 0, None) / ln)
                off += rng.uniform(0.5, 1.0) * np.exp(-(dist / w) ** 2) * fade
    for k in range(rng.integers(3, 6)):
        ang = rng.uniform(0, math.pi)
        dx, dy = math.cos(ang), math.sin(ang)
        px, py = rng.uniform(-0.6, 0.6) * a, rng.uniform(-0.6, 0.6) * b
        rx, ry = X - px, Y - py
        t = rx * dx + ry * dy
        dist = np.abs(-rx * dy + ry * dx)
        ln = rng.uniform(0.06, 0.16)
        off += rng.uniform(0.3, 0.6) * np.exp(-(dist / rng.uniform(0.008, 0.015)) ** 2) * np.exp(-(t / ln) ** 2)
    face = np.clip(np.abs(z) * 1.6 - 0.3, 0, 1)
    off = -depth * off * face
    sag = -0.35 * c * np.exp(-((x / 0.55) ** 2 + (y / 0.5) ** 2)) * np.clip(z * 2, 0, 1)
    lumps = 0.004 * (np.sin(7.1 * X + rng.uniform(0, 6)) * np.sin(9.3 * Y + rng.uniform(0, 6)))
    return P + nrm * (off + lumps)[:, None] + np.stack([0 * x, 0 * x, sag], 1)


def bake(o, rot_x_deg=None, seed=None, depth=0.0):
    if rot_x_deg is not None:
        o.rotation_euler.x = math.radians(rot_x_deg)
    o.data = o.data.copy()
    apply_mod(o, 'DISPLACE')
    if seed is not None:
        apply_mod(o, 'SUBSURF')
        P = getv(o)
        setv(o, creases(P, seed, depth))
        sm = o.modifiers.new('sub', 'SUBSURF'); sm.levels = 1; sm.render_levels = 1
    o.data.transform(o.matrix_world)
    o.matrix_world = Matrix.Identity(4)


def getv(o):
    a = np.zeros(len(o.data.vertices) * 3)
    o.data.vertices.foreach_get('co', a)
    return a.reshape(-1, 3)


def setv(o, P):
    o.data.vertices.foreach_set('co', P.reshape(-1))
    o.data.update()


def world_verts(o):
    P = getv(o)
    M = np.array(o.matrix_world)
    return P @ M[:3, :3].T + M[:3, 3]


hbv = world_verts(O['HB_Top'])

pillows = [O['PillowL'], O['PillowR']]
for o, rx, sd in zip(pillows, (63.0, 61.0), (11, 23)):
    bake(o, rx, sd, 0.009)
    P = getv(o)
    P[:, 1] += (YH + 0.014) - P[:, 1].max()
    P[:, 2] += (ZM - 0.024) - P[:, 2].min()
    P[:, 1] = smin(P[:, 1], YH + 0.001, 0.02)
    setv(o, P)
    near = hbv[(hbv[:, 0] > P[:, 0].min()) & (hbv[:, 0] < P[:, 0].max())]
    print('PILLOW', o.name, 'top z %.3f, headboard top over its width min %.3f' % (P[:, 2].max(), near[:, 2].max() if len(near) else -1))

dg = bpy.context.evaluated_depsgraph_get()
dg.update()
trees = [BVHTree.FromObject(o, dg) for o in pillows]


def pillow_front(x, z):
    best = np.inf
    for t in trees:
        hit = t.ray_cast(Vector((x, 1.0, z)), Vector((0, 1, 0)), 2.0)
        if hit[0] is not None:
            best = min(best, hit[0].y)
    return best


lum = O['Lumbar']
bake(lum, 70.0, 37, 0.004)
L = getv(lum)
L[:, 2] += (ZM - 0.018) - L[:, 2].min()
front = np.array([pillow_front(v[0], v[2]) for v in L])
fin = np.isfinite(front)
L[:, 1] += 0.010 - np.max(L[fin, 1] - front[fin])
L[fin, 1] = smin(L[fin, 1], front[fin] + 0.001, 0.012)
setv(lum, L)
print('LUMBAR y %.3f..%.3f z %.3f..%.3f' % (L[:, 1].min(), L[:, 1].max(), L[:, 2].min(), L[:, 2].max()))

gx = np.arange(MX0, MX1 + RES, RES)
gy = np.arange(GY0, MY1 + RES, RES)
pen = np.zeros((len(gx), len(gy)))
for o in pillows + [lum]:
    P = getv(o)
    m = (P[:, 2] < ZM) & (P[:, 0] > MX0) & (P[:, 0] < MX1) & (P[:, 1] > GY0) & (P[:, 1] < MY1)
    ix = ((P[m, 0] - MX0) / RES).round().astype(int).clip(0, len(gx) - 1)
    iy = ((P[m, 1] - GY0) / RES).round().astype(int).clip(0, len(gy) - 1)
    np.maximum.at(pen, (ix, iy), ZM - P[m, 2])


def maxfilter(a, r):
    out = a.copy()
    for dx in range(-r, r + 1):
        for dy in range(-r, r + 1):
            out = np.maximum(out, np.roll(np.roll(a, dx, 0), dy, 1))
    return out


def blur(a, sigma):
    r = int(3 * sigma)
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    a = np.apply_along_axis(lambda v: np.convolve(np.pad(v, r, mode='edge'), k, 'valid'), 0, a)
    return np.apply_along_axis(lambda v: np.convolve(np.pad(v, r, mode='edge'), k, 'valid'), 1, a)


D = 0.6 * blur(maxfilter(pen, 3), 4.0)


def dent(x, y):
    fx = np.clip((x - MX0) / RES, 0, len(gx) - 1.001)
    fy = np.clip((y - GY0) / RES, 0, len(gy) - 1.001)
    i, j = fx.astype(int), fy.astype(int)
    tx, ty = fx - i, fy - j
    v = (D[i, j] * (1 - tx) * (1 - ty) + D[i + 1, j] * tx * (1 - ty) + D[i, j + 1] * (1 - tx) * ty + D[i + 1, j + 1] * tx * ty)
    inside = (x > MX0) & (x < MX1) & (y > GY0) & (y < MY1)
    return np.where(inside, v, 0.0), inside


for o in pillows + [lum]:
    P = getv(o)
    d, inside = dent(P[:, 0], P[:, 1])
    floor_z = ZM - d - 0.001
    P[:, 2] = np.where(inside, smax(P[:, 2], floor_z, 0.012), P[:, 2])
    setv(o, P)
    for p in o.data.polygons:
        p.use_smooth = True

mat = O['Mattress']
old_mats = list(mat.data.materials)
for m in list(mat.modifiers):
    mat.modifiers.remove(m)
mat.matrix_world = Matrix.Identity(4)
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=1.0)
for v in bm.verts:
    v.co = Vector((MX0 if v.co.x < 0 else MX1, MY0 if v.co.y < 0 else MY1, MZ0 if v.co.z < 0 else ZM))
top = [e for e in bm.edges if all(v.co.z > ZM - 0.001 for v in e.verts)]
bmesh.ops.bevel(bm, geom=top, offset=0.035, segments=6, profile=0.5, affect='EDGES')
cuts = [('x', x) for x in np.arange(MX0 + 0.012, MX1 - 0.01, 0.012)]
cuts += [('y', y) for y in np.arange(0.15, GY0, 0.1)]
cuts += [('y', y) for y in np.arange(GY0, MY1 - 0.01, 0.012)]
for ax, c in cuts:
    co = (c, 0, 0) if ax == 'x' else (0, c, 0)
    no = (1, 0, 0) if ax == 'x' else (0, 1, 0)
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no)
me = bpy.data.meshes.new('MattressV4')
bm.to_mesh(me)
bm.free()
for m in old_mats:
    me.materials.append(m)
mat.data = me
P = getv(mat)
d, inside = dent(P[:, 0], P[:, 1])
band = np.clip((P[:, 2] - (ZM - 0.04)) / 0.035, 0, 1)
P[:, 2] -= d * band
setv(mat, P)
for p in mat.data.polygons:
    p.use_smooth = p.normal.z > 0.05
print('MATTRESS box x %.3f..%.3f y %.3f..%.3f z %.3f..%.3f' % (P[:, 0].min(), P[:, 0].max(), P[:, 1].min(), P[:, 1].max(), P[:, 2].min(), P[:, 2].max()))

for n in ('Duvet', 'Throw'):
    o = O[n]
    o.data = o.data.copy()
    M = np.array(o.matrix_world)
    P = getv(o) @ M[:3, :3].T + M[:3, 3]
    P[:, 0] = 0.8385 + (P[:, 0] - 0.8385) * 1.045
    P[:, 1] = 1.435 + (P[:, 1] - 1.435) * 1.026
    Mi = np.linalg.inv(M)
    setv(o, P @ Mi[:3, :3].T + Mi[:3, 3])
    inside = (P[:, 0] > MX0) & (P[:, 0] < MX1) & (P[:, 1] > MY0) & (P[:, 1] < MY1) & (P[:, 2] < ZM - 0.01)
    print('DRAPE', n, 'x %.3f..%.3f y %.3f..%.3f' % (P[:, 0].min(), P[:, 0].max(), P[:, 1].min(), P[:, 1].max()), 'verts inside mattress', int(inside.sum()))
print('MATTRESS verts', len(P), 'max dent %.4f' % D.max(), 'max pen %.4f' % pen.max())

for o in pillows:
    P = world_verts(o)
    print('CHECK', o.name, 'back max y %.4f (headboard %.3f)' % (P[:, 1].max(), YH), 'bottom min z %.4f (mattress %.3f)' % (P[:, 2].min(), ZM))

# ---------------- materials ----------------


def img(path, data=False):
    im = bpy.data.images.load(A + path, check_existing=True)
    if data:
        im.colorspace_settings.name = 'Non-Color'
    return im


def first(dirname, key):
    import os
    for f in sorted(os.listdir(A + dirname)):
        if key in f:
            return dirname + '/' + f
    return None


class T:
    def __init__(self, mat, clear=True):
        mat.use_nodes = True
        self.t = mat.node_tree
        self.n = self.t.nodes
        if clear:
            self.n.clear()
            self.out = self.n.new('ShaderNodeOutputMaterial')
            self.bsdf = self.n.new('ShaderNodeBsdfPrincipled')
            self.t.links.new(self.bsdf.outputs[0], self.out.inputs['Surface'])
        else:
            self.bsdf = [x for x in self.n if x.bl_idname == 'ShaderNodeBsdfPrincipled'][0]

    def new(self, t, **kw):
        nd = self.n.new(t)
        for k, v in kw.items():
            setattr(nd, k, v)
        return nd

    def link(self, a, b):
        self.t.links.new(a, b)

    def m(self, op, a, b=None, c=None):
        nd = self.new('ShaderNodeMath', operation=op)
        for i, x in enumerate((a, b, c)):
            if x is None:
                continue
            if isinstance(x, (int, float)):
                nd.inputs[i].default_value = x
            else:
                self.link(x, nd.inputs[i])
        return nd.outputs[0]

    def comb(self, x, y, z=0.0):
        nd = self.new('ShaderNodeCombineXYZ')
        for i, v in enumerate((x, y, z)):
            if isinstance(v, (int, float)):
                nd.inputs[i].default_value = v
            else:
                self.link(v, nd.inputs[i])
        return nd.outputs[0]

    def tex(self, image, vec, proj='FLAT'):
        nd = self.new('ShaderNodeTexImage', image=image, interpolation='Cubic', projection=proj)
        self.link(vec, nd.inputs['Vector'])
        return nd

    def mixc(self, fac, a, b, blend='MIX'):
        nd = self.new('ShaderNodeMix', data_type='RGBA', blend_type=blend)
        for ident, x in (('Factor_Float', fac), ('A_Color', a), ('B_Color', b)):
            s = [i for i in nd.inputs if i.identifier == ident][0]
            if isinstance(x, (int, float)):
                s.default_value = x
            elif isinstance(x, tuple):
                s.default_value = (*x, 1.0)
            else:
                self.link(x, s)
        return [o for o in nd.outputs if o.identifier == 'Result_Color'][0]

    def mixf(self, fac, a, b):
        nd = self.new('ShaderNodeMix', data_type='FLOAT')
        for ident, x in (('Factor_Float', fac), ('A_Float', a), ('B_Float', b)):
            s = [i for i in nd.inputs if i.identifier == ident][0]
            if isinstance(x, (int, float)):
                s.default_value = x
            else:
                self.link(x, s)
        return [o for o in nd.outputs if o.identifier == 'Result_Float'][0]

    def maprange(self, v, a, b, c, d):
        nd = self.new('ShaderNodeMapRange')
        self.link(v, nd.inputs['Value'])
        nd.inputs['From Min'].default_value = a
        nd.inputs['From Max'].default_value = b
        nd.inputs['To Min'].default_value = c
        nd.inputs['To Max'].default_value = d
        return nd.outputs['Result']

    def bump(self, h, strength, dist):
        nd = self.new('ShaderNodeBump')
        nd.inputs['Strength'].default_value = strength
        nd.inputs['Distance'].default_value = dist
        self.link(h, nd.inputs['Height'])
        return nd.outputs['Normal']


W_DIFF = img('walnut_veneer_02/walnut_veneer_02_diff_4k.jpg')
W_ROUGH = img('walnut_veneer_02/walnut_veneer_02_rough_4k.jpg', True)
W_DISP = img('walnut_veneer_02/walnut_veneer_02_disp_4k.png', True)


def walnut(name, axis):
    t = T(bpy.data.materials[name])
    tc = t.new('ShaderNodeTexCoord')
    sp = t.new('ShaderNodeSeparateXYZ')
    t.link(tc.outputs['Object'], sp.inputs[0])
    sn = t.new('ShaderNodeSeparateXYZ')
    t.link(tc.outputs['Normal'], sn.inputs[0])
    rnd = t.new('ShaderNodeObjectInfo').outputs['Random']
    idx = {'X': (0, 1, 2), 'Y': (1, 0, 2), 'Z': (2, 0, 1)}[axis]
    along, p1, p2 = (sp.outputs[i] for i in idx)
    na, n1, n2 = (t.m('ABSOLUTE', sn.outputs[i]) for i in idx)
    m_end = t.m('MULTIPLY', t.m('GREATER_THAN', na, n1), t.m('GREATER_THAN', na, n2))
    not_end = t.m('SUBTRACT', 1.0, m_end)
    m1 = t.m('MULTIPLY', not_end, t.m('GREATER_THAN', n1, n2))
    m2 = t.m('SUBTRACT', not_end, m1)
    u = t.m('ADD', t.m('MULTIPLY', m_end, p1), t.m('MULTIPLY', not_end, along))
    v = t.m('ADD', t.m('MULTIPLY', m_end, p2), t.m('ADD', t.m('MULTIPLY', m1, p2), t.m('MULTIPLY', m2, p1)))
    u = t.m('MULTIPLY_ADD', rnd, 17.31, u)
    v = t.m('MULTIPLY_ADD', rnd, 5.13, t.m('MULTIPLY_ADD', m1, 0.37, v))
    va = t.comb(u, v)
    vb = t.comb(t.m('ADD', u, 0.47), t.m('ADD', v, 0.291))
    nz = t.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 1.3
    nz.inputs['Detail'].default_value = 0.0
    t.link(t.comb(t.m('MULTIPLY_ADD', rnd, 9.0, along), 0.0, 0.0), nz.inputs['Vector'])
    fac = t.maprange(nz.outputs['Fac'], 0.42, 0.58, 0.0, 1.0)
    col = t.mixc(fac, t.tex(W_DIFF, va).outputs['Color'], t.tex(W_DIFF, vb).outputs['Color'])
    rough = t.mixf(fac, t.tex(W_ROUGH, va).outputs['Color'], t.tex(W_ROUGH, vb).outputs['Color'])
    hgt = t.mixf(fac, t.tex(W_DISP, va).outputs['Color'], t.tex(W_DISP, vb).outputs['Color'])
    g = t.new('ShaderNodeGamma')
    g.inputs['Gamma'].default_value = 1.5
    t.link(col, g.inputs['Color'])
    col = t.mixc(1.0, g.outputs['Color'], (0.24, 0.205, 0.19), 'MULTIPLY')
    t.link(col, t.bsdf.inputs['Base Color'])
    t.link(t.maprange(rough, 0.0, 1.0, 0.32, 0.50), t.bsdf.inputs['Roughness'])
    t.link(t.bump(hgt, 0.12, 0.0004), t.bsdf.inputs['Normal'])
    t.bsdf.inputs['Coat Weight'].default_value = 0.0


for ax in 'XYZ':
    walnut('walnut_' + ax, ax)

OAK_DIFF = img('white_oak_veneer/white_oak_veneer_diff_4k.jpg')
OAK_ROUGH = img('white_oak_veneer/white_oak_veneer_rough_4k.jpg', True)
OAK_DISP = img('white_oak_veneer/white_oak_veneer_disp_4k.png', True)


def floor_oak():
    t = T(bpy.data.materials['floor_oak'])
    tc = t.new('ShaderNodeTexCoord')
    sp = t.new('ShaderNodeSeparateXYZ')
    t.link(tc.outputs['Object'], sp.inputs[0])
    x, y = sp.outputs[0], sp.outputs[1]
    Wp, Lp, tile = 0.185, 1.7, 0.5
    row = t.m('FLOOR', t.m('DIVIDE', x, Wp))
    wn1 = t.new('ShaderNodeTexWhiteNoise', noise_dimensions='1D')
    t.link(row, wn1.inputs['W'])
    yy = t.m('MULTIPLY_ADD', wn1.outputs['Value'], Lp, y)
    pl = t.m('FLOOR', t.m('DIVIDE', yy, Lp))
    wn2 = t.new('ShaderNodeTexWhiteNoise', noise_dimensions='3D')
    t.link(t.comb(row, pl, 0.5), wn2.inputs['Vector'])
    r2 = wn2.outputs['Value']
    wn3 = t.new('ShaderNodeTexWhiteNoise', noise_dimensions='3D')
    t.link(t.comb(row, pl, 2.5), wn3.inputs['Vector'])
    r3 = wn3.outputs['Value']
    across = t.m('SUBTRACT', x, t.m('MULTIPLY', row, Wp))
    alongp = t.m('SUBTRACT', yy, t.m('MULTIPLY', pl, Lp))
    vec = t.comb(t.m('DIVIDE', t.m('MULTIPLY_ADD', r2, 3.7, across), tile), t.m('DIVIDE', t.m('MULTIPLY_ADD', r3, 5.3, alongp), tile))
    dA = t.m('MINIMUM', across, t.m('SUBTRACT', Wp, across))
    dL = t.m('MINIMUM', alongp, t.m('SUBTRACT', Lp, alongp))
    seam = t.m('MINIMUM', t.maprange(dA, 0.0, 0.0012, 0.0, 1.0), t.maprange(dL, 0.0, 0.0012, 0.0, 1.0))
    c = t.tex(OAK_DIFF, vec).outputs['Color']
    tone = t.maprange(r2, 0.0, 1.0, 0.84, 1.10)
    c = t.mixc(1.0, c, t.comb(tone, tone, tone), 'MULTIPLY')
    c = t.mixc(1.0, c, (0.92, 0.86, 0.78), 'MULTIPLY')
    c = t.mixc(1.0, c, t.comb(t.maprange(seam, 0, 1, 0.45, 1), t.maprange(seam, 0, 1, 0.45, 1), t.maprange(seam, 0, 1, 0.45, 1)), 'MULTIPLY')
    t.link(c, t.bsdf.inputs['Base Color'])
    t.link(t.maprange(t.tex(OAK_ROUGH, vec).outputs['Color'], 0, 1, 0.38, 0.62), t.bsdf.inputs['Roughness'])
    h = t.m('ADD', t.m('MULTIPLY', t.tex(OAK_DISP, vec).outputs['Color'], 0.25), seam)
    t.link(t.bump(h, 0.35, 0.0008), t.bsdf.inputs['Normal'])


floor_oak()

C_DIFF = img(first('Carpet016', '_Color'))
C_DISP = img(first('Carpet016', '_Displacement'), True)
C_ROUGH = img(first('Carpet016', '_Roughness'), True)


def rug():
    t = T(bpy.data.materials['rug_wool'])
    tc = t.new('ShaderNodeTexCoord')
    mp = t.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (1 / 0.45, 1 / 0.45, 1 / 0.45)
    t.link(tc.outputs['Object'], mp.inputs['Vector'])
    c = t.tex(C_DIFF, mp.outputs[0], 'BOX').outputs['Color']
    hs = t.new('ShaderNodeHueSaturation')
    hs.inputs['Saturation'].default_value = 0.55
    hs.inputs['Value'].default_value = 1.05
    t.link(c, hs.inputs['Color'])
    t.link(hs.outputs['Color'], t.bsdf.inputs['Base Color'])
    t.link(t.maprange(t.tex(C_ROUGH, mp.outputs[0], 'BOX').outputs['Color'], 0, 1, 0.85, 1.0), t.bsdf.inputs['Roughness'])
    t.link(t.bump(t.tex(C_DISP, mp.outputs[0], 'BOX').outputs['Color'], 0.7, 0.003), t.bsdf.inputs['Normal'])
    t.bsdf.inputs['Sheen Weight'].default_value = 1.0
    t.bsdf.inputs['Sheen Roughness'].default_value = 0.6


rug()

LIN_H = img(first('rough_linen', '_disp') or first('rough_linen', '_rough'), True)
LIN_R = img(first('rough_linen', '_rough'), True)
KNIT_H = img(first('knitted_fleece', '_disp') or first('knitted_fleece', '_rough'), True)
KNIT_R = img(first('knitted_fleece', '_rough'), True)


def fabric(name, h_img, r_img, scale, strength, uv=True):
    t = T(bpy.data.materials[name], clear=False)
    tc = t.new('ShaderNodeTexCoord')
    mp = t.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (scale, scale, scale)
    t.link(tc.outputs['UV' if uv else 'Object'], mp.inputs['Vector'])
    proj = 'FLAT' if uv else 'BOX'
    h = t.tex(h_img, mp.outputs[0], proj).outputs['Color']
    r = t.tex(r_img, mp.outputs[0], proj).outputs['Color']
    t.link(t.bump(h, strength, 0.0005), t.bsdf.inputs['Normal'])
    t.link(t.maprange(r, 0, 1, 0.78, 0.95), t.bsdf.inputs['Roughness'])


fabric('linen_duvet', LIN_H, LIN_R, 1 / 0.27, 0.22)
fabric('linen_sham', LIN_H, LIN_R, 0.5 / 0.27, 0.22)
fabric('percale', LIN_H, LIN_R, 0.5 / 0.15, 0.12)
fabric('sheet', LIN_H, LIN_R, 1 / 0.15, 0.12, uv=False)
fabric('wool_throw', KNIT_H, KNIT_R, 1 / 0.27, 0.35)

O['Outside'].visible_camera = False

for nm, lo, hi in (('wool_throw', (0.105, 0.072, 0.070), (0.135, 0.095, 0.090)),):
    r = [x for x in bpy.data.materials[nm].node_tree.nodes if x.bl_idname == 'ShaderNodeValToRGB'][0]
    r.color_ramp.elements[0].color = (*lo, 1); r.color_ramp.elements[1].color = (*hi, 1)
wl = bpy.data.materials['wall_limewash'].node_tree.nodes
r = [x for x in wl if x.bl_idname == 'ShaderNodeValToRGB'][0]
r.color_ramp.elements[0].position = 0.15; r.color_ramp.elements[1].position = 0.85
r.color_ramp.elements[0].color = (0.328, 0.299, 0.261, 1); r.color_ramp.elements[1].color = (0.346, 0.316, 0.276, 1)
[x for x in wl if x.bl_idname == 'ShaderNodeBump'][0].inputs['Strength'].default_value = 0.02
rn = [x for x in bpy.data.materials['rug_wool'].node_tree.nodes if x.bl_idname == 'ShaderNodeHueSaturation'][0]
rn.inputs['Value'].default_value = 0.9

bpy.ops.wm.save_as_mainfile(filepath=S + '/scene.blend')
print('PATCHED_V4')
