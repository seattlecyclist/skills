import bpy, bmesh, sys, math, random
from mathutils import Vector, Matrix, Euler
S = sys.argv[-1]
IN = 0.0254
RUG = 0.008
random.seed(4)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
col = sc.collection

# ---------------- helpers ----------------
def mk_obj(name, verts, faces, mat=None):
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    o = bpy.data.objects.new(name, me); col.objects.link(o)
    if mat: o.data.materials.append(mat)
    return o

def box(name, x0, y0, z0, x1, y1, z1, mat=None):
    v = [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    f = [(0,1,3,2),(4,6,7,5),(0,4,5,1),(2,3,7,6),(0,2,6,4),(1,5,7,3)]
    return mk_obj(name, v, f, mat)

def apply_mods(o):
    bpy.context.view_layer.objects.active = o
    for m in list(o.modifiers):
        with bpy.context.temp_override(object=o, active_object=o):
            bpy.ops.object.modifier_apply(modifier=m.name)

def boolean(o, cutter, op='DIFFERENCE'):
    m = o.modifiers.new('b', 'BOOLEAN'); m.operation = op; m.object = cutter; m.solver = 'EXACT'
    apply_mods(o); bpy.data.objects.remove(cutter)

def bevel(o, w=0.0015, seg=3, angle=40):
    m = o.modifiers.new('bevel', 'BEVEL'); m.width = w; m.segments = seg; m.limit_method = 'ANGLE'; m.angle_limit = math.radians(angle)
    return m

def smooth(o):
    for p in o.data.polygons: p.use_smooth = True

def recalc(o):
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(o.data); bm.free()

def lathe(name, prof, segs=64, mat=None, cap_bottom=True, cap_top=True):
    verts, faces = [], []
    for (r, z) in prof:
        for i in range(segs):
            a = 2*math.pi*i/segs; verts.append((r*math.cos(a), r*math.sin(a), z))
    for j in range(len(prof)-1):
        for i in range(segs):
            a = j*segs+i; b = j*segs+(i+1)%segs
            faces.append((a, b, b+segs, a+segs))
    if cap_bottom: faces.append(tuple(reversed(range(segs))))
    if cap_top: faces.append(tuple(range((len(prof)-1)*segs, len(prof)*segs)))
    return mk_obj(name, verts, faces, mat)

def inp(n, ident):
    for s in n.inputs:
        if s.identifier == ident: return s
    raise KeyError(ident)
def outp(n, ident):
    for s in n.outputs:
        if s.identifier == ident: return s
    raise KeyError(ident)

class NB:
    def __init__(self, mat):
        mat.use_nodes = True; self.t = mat.node_tree; self.n = self.t.nodes; self.l = self.t.links
        self.n.clear()
        self.out = self.n.new('ShaderNodeOutputMaterial')
        self.bsdf = self.n.new('ShaderNodeBsdfPrincipled')
        self.link(self.bsdf.outputs[0], self.out.inputs['Surface'])
    def new(self, t, **kw):
        nd = self.n.new(t)
        for k, v in kw.items(): setattr(nd, k, v)
        return nd
    def link(self, a, b): self.l.new(a, b)
    def math(self, op, a, b=None, c=None):
        m = self.new('ShaderNodeMath', operation=op)
        for i, x in enumerate((a, b, c)):
            if x is None: continue
            if isinstance(x, (int, float)): m.inputs[i].default_value = x
            else: self.link(x, m.inputs[i])
        return m.outputs[0]
    def mix(self, fac, a, b, blend='MIX'):
        m = self.new('ShaderNodeMix', data_type='RGBA', blend_type=blend)
        for ident, x in (('Factor_Float', fac), ('A_Color', a), ('B_Color', b)):
            s = inp(m, ident)
            if isinstance(x, (int, float)): s.default_value = x
            elif isinstance(x, tuple): s.default_value = (*x, 1) if len(x) == 3 else x
            else: self.link(x, s)
        return outp(m, 'Result_Color')
    def ramp(self, fac, stops):
        r = self.new('ShaderNodeValToRGB'); self.link(fac, r.inputs[0])
        el = r.color_ramp.elements
        while len(el) < len(stops): el.new(0.5)
        for e, (p, c) in zip(el, stops):
            e.position = p; e.color = (*c, 1) if len(c) == 3 else c
        return r.outputs[0]
    def set(self, name, v):
        s = self.bsdf.inputs[name]
        if isinstance(v, (int, float, tuple)): s.default_value = (*v, 1) if isinstance(v, tuple) and len(v) == 3 and s.type == 'RGBA' else v
        else: self.link(v, s)
    def noise(self, vec, scale, detail=2, rough=0.5, dist=0.0):
        nz = self.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = scale; nz.inputs['Detail'].default_value = detail
        nz.inputs['Roughness'].default_value = rough; nz.inputs['Distortion'].default_value = dist
        if vec is not None: self.link(vec, nz.inputs['Vector'])
        return nz
    def bump(self, h, strength, dist=0.001, normal=None):
        b = self.new('ShaderNodeBump'); b.inputs['Strength'].default_value = strength; b.inputs['Distance'].default_value = dist
        self.link(h, b.inputs['Height'])
        if normal is not None: self.link(normal, b.inputs['Normal'])
        return b.outputs[0]

# ---------------- materials ----------------
def wood_mat(name, axis, dark, mid, light, rough=0.42, coat=0.12, ring_scale=95, quarter=True):
    m = bpy.data.materials.new(name); b = NB(m)
    tc = b.new('ShaderNodeTexCoord'); sep = b.new('ShaderNodeSeparateXYZ'); b.link(tc.outputs['Object'], sep.inputs[0])
    oi = b.new('ShaderNodeObjectInfo'); rnd = oi.outputs['Random']
    X, Y, Z = sep.outputs[0], sep.outputs[1], sep.outputs[2]
    along, p1, p2 = {'X': (X, Z, Y), 'Y': (Y, Z, X), 'Z': (Z, X, Y)}[axis]
    k2 = 0.35 if quarter else 0.8
    s = b.math('MULTIPLY_ADD', p2, k2, p1)
    s = b.math('MULTIPLY_ADD', rnd, 7.3, s)
    a = b.math('MULTIPLY_ADD', rnd, 31.0, along)
    a_slow = b.math('MULTIPLY', a, 0.045)
    v = b.new('ShaderNodeCombineXYZ'); b.link(s, v.inputs[0]); b.link(a_slow, v.inputs[1]); b.link(b.math('MULTIPLY', p2, 0.3), v.inputs[2])
    w1 = b.new('ShaderNodeTexWave', wave_type='BANDS', bands_direction='X', wave_profile='SIN')
    w1.inputs['Scale'].default_value = ring_scale; w1.inputs['Distortion'].default_value = 7; w1.inputs['Detail'].default_value = 3; w1.inputs['Detail Scale'].default_value = 1.2
    b.link(v.outputs[0], w1.inputs['Vector'])
    w2 = b.new('ShaderNodeTexWave', wave_type='BANDS', bands_direction='X', wave_profile='SIN')
    w2.inputs['Scale'].default_value = ring_scale*0.23; w2.inputs['Distortion'].default_value = 4; w2.inputs['Detail'].default_value = 2
    b.link(v.outputs[0], w2.inputs['Vector'])
    # broad streaks, stretched along the grain
    v2 = b.new('ShaderNodeCombineXYZ'); b.link(s, v2.inputs[0]); b.link(b.math('MULTIPLY', a, 0.12), v2.inputs[1]); b.link(p2, v2.inputs[2])
    nB = b.noise(v2.outputs[0], 5.0, detail=3, rough=0.55)
    # pores
    v3 = b.new('ShaderNodeCombineXYZ'); b.link(s, v3.inputs[0]); b.link(b.math('MULTIPLY', a, 0.06), v3.inputs[1]); b.link(p2, v3.inputs[2])
    nP = b.noise(v3.outputs[0], 700, detail=1, rough=0.4)
    pore = b.math('SMOOTHERSTEP' if False else 'GREATER_THAN', nP.outputs['Fac'], 0.62)
    lines = b.ramp(w1.outputs['Fac'], [(0.0, dark), (0.35, mid), (1.0, mid)])
    bands = b.ramp(w2.outputs['Fac'], [(0.0, (0.82, 0.82, 0.82)), (1.0, (1.08, 1.06, 1.04))])
    c = b.mix(1.0, lines, bands, 'MULTIPLY')
    sf = b.ramp(nB.outputs['Fac'], [(0.42, (0, 0, 0)), (0.7, (0.6, 0.6, 0.6))])
    c = b.mix(sf, c, light)
    c = b.mix(b.math('MULTIPLY', pore, 0.55), c, (dark[0]*0.5, dark[1]*0.5, dark[2]*0.5))
    b.set('Base Color', c)
    b.set('Roughness', b.math('MULTIPLY_ADD', pore, 0.18, rough))
    b.set('Coat Weight', coat); b.set('Coat Roughness', 0.32)
    h = b.math('MULTIPLY_ADD', w1.outputs['Fac'], 0.25, b.math('MULTIPLY', pore, -1.0))
    b.set('Normal', b.bump(h, 0.06, 0.0004))
    return m

WAL = {ax: wood_mat('walnut_'+ax, ax, (0.040, 0.018, 0.008), (0.125, 0.060, 0.027), (0.185, 0.098, 0.045)) for ax in 'XYZ'}
MAPLE = {ax: wood_mat('maple_'+ax, ax, (0.45, 0.32, 0.19), (0.60, 0.45, 0.29), (0.66, 0.52, 0.36), rough=0.5, coat=0.05, ring_scale=60) for ax in 'XYZ'}
OAK = {ax: wood_mat('oak_'+ax, ax, (0.20, 0.13, 0.07), (0.36, 0.25, 0.15), (0.42, 0.31, 0.19), rough=0.55, coat=0.0, ring_scale=55, quarter=False) for ax in 'XYZ'}

def fabric(name, color, rough=0.85, sheen=0.6, weave=600, bumpst=0.25, uv=True, knit=False):
    m = bpy.data.materials.new(name); b = NB(m)
    tc = b.new('ShaderNodeTexCoord'); vec = tc.outputs['UV' if uv else 'Object']
    wa = b.new('ShaderNodeTexWave', wave_type='BANDS', bands_direction='X'); wa.inputs['Scale'].default_value = weave; wa.inputs['Distortion'].default_value = 1.5
    wb = b.new('ShaderNodeTexWave', wave_type='BANDS', bands_direction='Y'); wb.inputs['Scale'].default_value = weave*(0.4 if knit else 1); wb.inputs['Distortion'].default_value = 1.5
    b.link(vec, wa.inputs['Vector']); b.link(vec, wb.inputs['Vector'])
    nz = b.noise(vec, weave/8, detail=4, rough=0.6)
    h = b.math('ADD', b.math('MULTIPLY', wa.outputs['Fac'], wb.outputs['Fac']), b.math('MULTIPLY', nz.outputs['Fac'], 0.6))
    var = b.ramp(nz.outputs['Fac'], [(0.3, tuple(c*0.9 for c in color)), (0.7, tuple(min(1, c*1.06) for c in color))])
    b.set('Base Color', var); b.set('Roughness', rough)
    b.set('Sheen Weight', sheen); b.set('Sheen Roughness', 0.4); b.set('Sheen Tint', (1, 1, 1))
    b.set('Subsurface Weight', 0.05)
    b.set('Normal', b.bump(h, bumpst, 0.002))
    return m

LINEN = fabric('linen_duvet', (0.60, 0.55, 0.47), weave=900)
SHAM = fabric('linen_sham', (0.42, 0.37, 0.30), weave=900)
PILLOW = fabric('percale', (0.72, 0.71, 0.68), weave=1400, bumpst=0.1, sheen=0.3)
SHEET = fabric('sheet', (0.70, 0.69, 0.66), weave=1400, bumpst=0.1, sheen=0.3, uv=False)
THROW = fabric('wool_throw', (0.26, 0.105, 0.055), weave=160, bumpst=0.6, sheen=0.9, knit=True)

def plain(name, color, rough=0.8, bump_scale=None, bump_st=0.03, var=0.0, metal=0.0, coat=0.0):
    m = bpy.data.materials.new(name); b = NB(m)
    b.set('Roughness', rough); b.set('Metallic', metal); b.set('Coat Weight', coat)
    if var or bump_scale:
        tc = b.new('ShaderNodeTexCoord')
        nz = b.noise(tc.outputs['Object'], bump_scale or 3, detail=6, rough=0.6)
        if var:
            b.set('Base Color', b.ramp(nz.outputs['Fac'], [(0.3, tuple(c*(1-var) for c in color)), (0.7, tuple(c*(1+var) for c in color))]))
        else: b.set('Base Color', color)
        if bump_scale: b.set('Normal', b.bump(nz.outputs['Fac'], bump_st, 0.003))
    else: b.set('Base Color', color)
    return m

WALL = plain('wall_white', (0.70, 0.67, 0.62), rough=0.9, bump_scale=30, bump_st=0.04, var=0.02)
ACCENT = plain('wall_limewash', (0.34, 0.31, 0.27), rough=0.95, bump_scale=2.5, bump_st=0.05, var=0.10)
TRIM = plain('trim_paint', (0.74, 0.72, 0.68), rough=0.45)
CEIL = plain('ceiling', (0.78, 0.77, 0.74), rough=0.95)
CERAMIC = plain('ceramic', (0.55, 0.50, 0.43), rough=0.55, bump_scale=60, bump_st=0.15, var=0.05, coat=0.3)
CERAMIC2 = plain('ceramic_dark', (0.06, 0.055, 0.05), rough=0.6, bump_scale=60, bump_st=0.15, var=0.08)
BRASS = plain('brass', (0.8, 0.6, 0.35), rough=0.3, metal=1.0)
STEEL = plain('steel', (0.4, 0.4, 0.4), rough=0.4, metal=1.0)
RUGM = fabric('rug_wool', (0.55, 0.51, 0.44), rough=0.95, weave=250, bumpst=0.8, sheen=1.0, uv=False)
PAGES = plain('pages', (0.72, 0.69, 0.62), rough=0.9)
BOOKS = [plain('book%d' % i, c, rough=0.7) for i, c in enumerate([(0.12, 0.16, 0.18), (0.45, 0.38, 0.28), (0.25, 0.08, 0.05)])]

# shade: translucent linen
SHADE = bpy.data.materials.new('shade'); b = NB(SHADE)
tr = b.new('ShaderNodeBsdfTranslucent'); tr.inputs['Color'].default_value = (0.9, 0.8, 0.62, 1)
b.set('Base Color', (0.75, 0.70, 0.62)); b.set('Roughness', 0.9)
mx = b.new('ShaderNodeMixShader'); mx.inputs[0].default_value = 0.5
b.link(b.bsdf.outputs[0], mx.inputs[1]); b.link(tr.outputs[0], mx.inputs[2]); b.link(mx.outputs[0], b.out.inputs['Surface'])
# sheer curtain
SHEER = bpy.data.materials.new('sheer'); b = NB(SHEER)
tr = b.new('ShaderNodeBsdfTranslucent'); tr.inputs['Color'].default_value = (0.9, 0.88, 0.84, 1)
tp = b.new('ShaderNodeBsdfTransparent')
b.set('Base Color', (0.8, 0.78, 0.74)); b.set('Roughness', 0.8); b.set('Sheen Weight', 0.5)
m1 = b.new('ShaderNodeMixShader'); m1.inputs[0].default_value = 0.45
b.link(b.bsdf.outputs[0], m1.inputs[1]); b.link(tr.outputs[0], m1.inputs[2])
m2 = b.new('ShaderNodeMixShader'); m2.inputs[0].default_value = 0.55
b.link(m1.outputs[0], m2.inputs[1]); b.link(tp.outputs[0], m2.inputs[2]); b.link(m2.outputs[0], b.out.inputs['Surface'])
# art canvas
ART = bpy.data.materials.new('art'); b = NB(ART)
tc = b.new('ShaderNodeTexCoord'); nz = b.noise(tc.outputs['Generated'], 1.6, detail=6, rough=0.55, dist=1.2)
b.set('Base Color', b.ramp(nz.outputs['Fac'], [(0.25, (0.62, 0.57, 0.48)), (0.48, (0.48, 0.40, 0.30)), (0.58, (0.20, 0.13, 0.08)), (0.75, (0.05, 0.045, 0.04))]))
b.set('Roughness', 0.85)
nz2 = b.noise(tc.outputs['Generated'], 300, detail=3)
b.set('Normal', b.bump(nz2.outputs['Fac'], 0.25, 0.002))
# floor
FLOOR = bpy.data.materials.new('floor_oak'); b = NB(FLOOR)
tc = b.new('ShaderNodeTexCoord'); mp = b.new('ShaderNodeMapping')
mp.inputs['Scale'].default_value = (1/2.0, 1/1.0, 1); mp.inputs['Rotation'].default_value = (0, 0, math.radians(90))
b.link(tc.outputs['Object'], mp.inputs['Vector'])
def img(fn, noncolor=False):
    t = b.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(S + '/tex/' + fn)
    if noncolor: t.image.colorspace_settings.name = 'Non-Color'
    b.link(mp.outputs[0], t.inputs[0]); return t
d = img('hardwood2_diffuse.jpg'); rgh = img('hardwood2_roughness.jpg', True); bmp = img('hardwood2_bump.jpg', True)
hs = b.new('ShaderNodeHueSaturation'); hs.inputs['Saturation'].default_value = 0.5; hs.inputs['Value'].default_value = 0.62; hs.inputs['Hue'].default_value = 0.49
b.link(d.outputs[0], hs.inputs['Color'])
b.set('Base Color', b.mix(0.45, hs.outputs[0], (0.20, 0.15, 0.10)))
rr = b.new('ShaderNodeMapRange'); rr.inputs['To Min'].default_value = 0.35; rr.inputs['To Max'].default_value = 0.6
b.link(rgh.outputs[0], rr.inputs[0]); b.set('Roughness', rr.outputs[0])
b.set('Coat Weight', 0.15); b.set('Coat Roughness', 0.2)
b.set('Normal', b.bump(bmp.outputs[0], 0.25, 0.002))

# ---------------- the bed ----------------
bpy.ops.wm.obj_import(filepath=S + '/bed.obj', forward_axis='Y', up_axis='Z')
bed = [o for o in sc.objects if o.type == 'MESH']
for o in list(bed):
    if o.name.startswith(('P1_', 'P12_', 'P13_')):
        bpy.data.objects.remove(o); bed.remove(o)

def grain_axis(o):
    d = o.dimensions
    return 'XYZ'[max(range(3), key=lambda i: d[i])]

for o in bed:
    recalc(o)
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1), verts=bm.verts, edges=bm.edges)
    bm.to_mesh(o.data); bm.free()
    o.data.materials.clear()
    lib = MAPLE if 'Slat' in o.name or 'U_Brack' in o.name or 'Center_Rail' in o.name or 'Slat_Supp' in o.name else WAL
    o.data.materials.append(lib[grain_axis(o)])
    bevel(o, 0.0012, 2)

W, D = 66.0, 86.0
L, legH, foot, taperTop, R = 3.0, 13.0, 2.25, 8.0, 0.75
def leg_ring(z):
    s = foot + (L - foot) * min(z, taperTop) / taperTop
    pts = []
    for i in range(9):
        a = math.pi + math.pi/2 * i/8
        pts.append((R + R*math.cos(a), R + R*math.sin(a)))
    pts += [(s, 0), (s, s), (0, s)]
    return pts
for li, (cx, cy, sx, sy) in enumerate([(0, 0, 1, 1), (W, 0, -1, 1), (0, D, 1, -1), (W, D, -1, -1)]):
    rings = [leg_ring(z) for z in (0, taperTop, legH)]
    zs = (0, taperTop, legH)
    verts = []; n = len(rings[0])
    for ring, z in zip(rings, zs):
        for (u, v) in ring: verts.append(((cx + sx*u)*IN, (cy + sy*v)*IN, z*IN))
    faces = []
    for j in range(2):
        for i in range(n):
            a, bb = j*n + i, j*n + (i+1) % n
            faces.append((a, bb, bb+n, a+n))
    faces.append(tuple(reversed(range(n)))); faces.append(tuple(range(2*n, 3*n)))
    o = mk_obj('Leg_%d' % li, verts, faces, WAL['Z']); recalc(o)
    # castle slots: 1" wide, 4" deep, centred 1" to 2" from the outside faces
    zb = (legH - 4)*IN
    x0, x1 = sorted(((cx + sx*1)*IN, (cx + sx*2)*IN)); y0, y1 = sorted(((cy + sy*1)*IN, (cy + sy*2)*IN))
    boolean(o, box('c1', x0, (cy - 1)*IN, zb, x1, (cy + 4)*IN if sy > 0 else (cy + 1)*IN, 1, None)) if False else None
    boolean(o, box('c1', x0, min(cy - sy*1, cy + sy*4)*IN, zb, x1, max(cy - sy*1, cy + sy*4)*IN, 1))
    boolean(o, box('c2', min(cx - sx*1, cx + sx*4)*IN, y0, zb, max(cx - sx*1, cx + sx*4)*IN, y1, 1))
    bevel(o, 0.0015, 3); bed.append(o)

# headboard boards, true curves
HB_top, rise, gapZ, gap, t = 44.0, 1.5, 30.0, 0.25, 1.0
par = lambda x: 1 - ((x - W/2)/(W/2))**2
yt = lambda x: HB_top - rise*par(x); yb = lambda x: gapZ + rise*par(x); yl = lambda x: yb(x) - gap
N = 240
def slab(name, poly):
    verts = [(x*IN, D*IN, z*IN) for x, z in poly] + [(x*IN, (D + t)*IN, z*IN) for x, z in poly]
    n = len(poly); faces = [tuple(range(n)), tuple(reversed(range(n, 2*n)))]
    for i in range(n): faces.append((i, n + i, n + (i+1) % n, (i+1) % n))
    o = mk_obj(name, verts, faces, WAL['X']); recalc(o); bevel(o, 0.0015, 3, 30); bed.append(o)
    return o
top = [(x, yb(x)) for x in [W*i/N for i in range(N+1)]]
xr = [W - R + R*math.cos(math.pi/2*i/8) for i in range(9)]
top += [(W, HB_top - R)] + [(W - R + R*math.cos(math.pi/2*i/8), HB_top - R + R*math.sin(math.pi/2*i/8)) for i in range(1, 9)]
top += [(x, yt(x)) for x in [W - R - (W - 2*R)*i/N for i in range(1, N)]]
top += [(R + R*math.cos(math.pi/2 + math.pi/2*i/8), HB_top - R + R*math.sin(math.pi/2 + math.pi/2*i/8)) for i in range(0, 9)]
slab('HB_Top', top)
low = [(0, 9.0), (W, 9.0)] + [(x, yl(x)) for x in [W - W*i/N for i in range(N+1)]]
slab('HB_Lower', low)

for o in bed: o.location.z += RUG

# mattress (fitted sheet)
mz0, mz1 = 11.5*IN + RUG, 21.5*IN + RUG
matt = box('Mattress', 3*IN, 3*IN, mz0, 63*IN, 83*IN, mz1, SHEET)
bm_ = matt.modifiers.new('bv', 'BEVEL'); bm_.width = 0.035; bm_.segments = 5
sd = matt.modifiers.new('sub', 'SUBSURF'); sd.levels = 1; sd.render_levels = 2
smooth(matt)

# ---------------- room ----------------
RX0, RX1, RY0, RY1, RH = -1.35, 3.05, -3.4, D*IN + 1.25*IN + 0.04, 2.70
floor = mk_obj('Floor', [(RX0, RY0, 0), (RX1, RY0, 0), (RX1, RY1, 0), (RX0, RY1, 0)], [(0, 1, 2, 3)], FLOOR)
ceil_ = mk_obj('Ceiling', [(RX0, RY0, RH), (RX0, RY1, RH), (RX1, RY1, RH), (RX1, RY0, RH)], [(0, 1, 2, 3)], CEIL)
T = 0.12
back = box('WallBack', RX0 - T, RY1, 0, RX1 + T, RY1 + T, RH, ACCENT)
front = box('WallFront', RX0 - T, RY0 - T, 0, RX1 + T, RY0, RH, WALL)
right = box('WallRight', RX1, RY0, 0, RX1 + T, RY1, RH, WALL)
left = box('WallLeft', RX0 - T, RY0, 0, RX0, RY1, RH, WALL)
WY0, WY1, WZ0, WZ1 = -0.75, 0.95, 0.55, 2.35
boolean(left, box('win', RX0 - 0.5, WY0, WZ0, RX0 + 0.1, WY1, WZ1))
# window trim, sill, mullions
cw = 0.07
for nm, a in [('trimL', (RX0 - T, WY0 - cw, WZ0 - cw, RX0 + 0.018, WY0, WZ1 + cw)), ('trimR', (RX0 - T, WY1, WZ0 - cw, RX0 + 0.018, WY1 + cw, WZ1 + cw)),
              ('trimT', (RX0 - T, WY0 - cw, WZ1, RX0 + 0.018, WY1 + cw, WZ1 + cw)), ('sill', (RX0 - T, WY0 - cw - 0.03, WZ0 - 0.025, RX0 + 0.045, WY1 + cw + 0.03, WZ0 + 0.005)),
              ('apron', (RX0, WY0 - cw, WZ0 - 0.12, RX0 + 0.016, WY1 + cw, WZ0 - 0.025)),
              ('mullV', (RX0 - 0.09, (WY0 + WY1)/2 - 0.025, WZ0, RX0 - 0.04, (WY0 + WY1)/2 + 0.025, WZ1)),
              ('mullH', (RX0 - 0.09, WY0, 1.62, RX0 - 0.04, WY1, 1.66)),
              ('sashF', (RX0 - 0.09, WY0, WZ0, RX0 - 0.04, WY1, WZ0 + 0.05))]:
    o = box(nm, *a, TRIM); bevel(o, 0.003, 2)
# baseboards
bb = 0.11
for nm, a in [('baseB', (RX0, RY1 - 0.016, 0, RX1, RY1, bb)), ('baseR', (RX1 - 0.016, RY0, 0, RX1, RY1, bb)),
              ('baseL', (RX0, RY0, 0, RX0 + 0.016, RY1, bb)), ('baseF', (RX0, RY0, 0, RX1, RY0 + 0.016, bb))]:
    o = box(nm, *a, TRIM); bevel(o, 0.003, 2)
# rug (8x10)
rug = box('Rug', 0.838 - 1.22, -0.95, 0, 0.838 + 1.22, RY1 - 0.05, RUG, RUGM); bevel(rug, 0.003, 2, 60)
# outside ground
gnd = mk_obj('Outside', [(-60, -60, -0.6), (-60, 60, -0.6), (-3, 60, -0.6), (-3, -60, -0.6)], [(0, 1, 2, 3)], plain('ground', (0.25, 0.27, 0.20), 0.9))

# nightstands, white oak
def nightstand(name, x0, x1):
    y1 = RY1 - 0.02; y0 = y1 - 0.40
    body = box(name, x0, y0, 0.0, x1, y1, 0.56, OAK['X']); bevel(body, 0.002, 3)
    boolean(body, box('g', x0 - 0.01, y0 - 0.01, 0.10, x1 + 0.01, y0 + 0.004, 0.085))
    boolean(body, box('g2', x0 - 0.01, y0 - 0.01, 0.35, x1 + 0.01, y0 + 0.004, 0.354))
    boolean(body, box('g3', x0 + 0.02, y0 - 0.01, 0.0, x1 - 0.02, y0 + 0.04, 0.085))
    pull = box(name + '_pull', (x0 + x1)/2 - 0.05, y0 - 0.012, 0.335, (x0 + x1)/2 + 0.05, y0 + 0.001, 0.345, BRASS)
    return (x0 + x1)/2, (y0 + y1)/2
nsL = nightstand('NS_L', -0.62, -0.10)
nsR = nightstand('NS_R', 66*IN + 0.10, 66*IN + 0.62)

def lamp(cx, cy, z0, tag):
    prof = [(0.0, 0), (0.06, 0.0), (0.075, 0.02), (0.095, 0.08), (0.10, 0.14), (0.085, 0.22), (0.05, 0.27), (0.025, 0.30), (0.02, 0.33), (0.0, 0.33)]
    o = lathe('LampBase' + tag, prof, 64, CERAMIC2, cap_bottom=False, cap_top=False); smooth(o)
    o.location = (cx, cy, z0)
    sd = o.modifiers.new('s', 'SUBSURF'); sd.levels = 2; sd.render_levels = 2
    rod = lathe('Rod' + tag, [(0.006, 0.33), (0.006, 0.52)], 24, BRASS); rod.location = (cx, cy, z0)
    sh = lathe('Shade' + tag, [(0.16, 0.36), (0.13, 0.56)], 96, SHADE, cap_bottom=False, cap_top=False); sh.location = (cx, cy, z0)
    so = sh.modifiers.new('sol', 'SOLIDIFY'); so.thickness = 0.002; smooth(sh)
    ld = bpy.data.lights.new('bulb' + tag, 'POINT'); ld.energy = 18; ld.shadow_soft_size = 0.03; ld.color = (1.0, 0.72, 0.45)
    lo = bpy.data.objects.new('bulb' + tag, ld); lo.location = (cx, cy, z0 + 0.46); col.objects.link(lo)
lamp(nsL[0] - 0.02, nsL[1] + 0.03, 0.56, 'L')
lamp(nsR[0] + 0.03, nsR[1] + 0.04, 0.56, 'R')
# books on right nightstand
zb_ = 0.56
for i, (w_, d_, h_, rot) in enumerate([(0.24, 0.17, 0.032, 4), (0.21, 0.15, 0.025, -6)]):
    bx = box('Book%d' % i, -w_/2, -d_/2, 0, w_/2, d_/2, h_, BOOKS[i]); bevel(bx, 0.002, 2)
    pg = box('Pages%d' % i, -w_/2 + 0.004, -d_/2 + 0.006, 0.003, w_/2 - 0.004, d_/2 + 0.0005, h_ - 0.003, PAGES)
    for o in (bx, pg):
        o.location = (nsR[0] - 0.08, nsR[1] - 0.06, zb_); o.rotation_euler.z = math.radians(rot)
    zb_ += h_
# vase on left nightstand
v = lathe('Vase', [(0.0, 0), (0.035, 0), (0.05, 0.03), (0.055, 0.08), (0.035, 0.15), (0.018, 0.19), (0.02, 0.21), (0.015, 0.21), (0.012, 0.19)], 64, CERAMIC, cap_bottom=True, cap_top=False)
smooth(v); v.modifiers.new('s', 'SUBSURF').levels = 2; v.location = (nsL[0] + 0.15, nsL[1] - 0.08, 0.56)
# art above the bed
ax0, ax1, az0, az1 = 0.838 - 0.55, 0.838 + 0.55, 1.42, 2.12
fr = box('ArtFrame', ax0, RY1 - 0.035, az0, ax1, RY1, az1, OAK['X']); bevel(fr, 0.002, 2)
boolean(fr, box('fi', ax0 + 0.025, RY1 - 0.05, az0 + 0.025, ax1 - 0.025, RY1 - 0.01, az1 - 0.025))
cv = box('ArtCanvas', ax0 + 0.025, RY1 - 0.022, az0 + 0.025, ax1 - 0.025, RY1 - 0.005, az1 - 0.025, ART)
# sheer curtains
def curtain(name, y0, y1):
    nx, nz = 120, 60; verts = []; faces = []
    for j in range(nz + 1):
        z = 0.02 + (2.58 - 0.02)*j/nz
        for i in range(nx + 1):
            y = y0 + (y1 - y0)*i/nx
            x = RX0 + 0.10 + 0.035*math.sin((y - y0)/0.09*2*math.pi + 0.3*math.sin(z*3))*(0.8 + 0.2*j/nz)
            verts.append((x, y, z))
    for j in range(nz):
        for i in range(nx): a = j*(nx + 1) + i; faces.append((a, a + 1, a + nx + 2, a + nx + 1))
    o = mk_obj(name, verts, faces, SHEER); smooth(o)
curtain('CurtainA', WY0 - 0.42, WY0 + 0.08)
curtain('CurtainB', WY1 - 0.08, WY1 + 0.42)
rod = box('CurtainRod', RX0 + 0.08, WY0 - 0.5, 2.58, RX0 + 0.10, WY1 + 0.5, 2.60, STEEL)

# ---------------- cloth: duvet, then pillows, then throw ----------------
def grid(name, nu, nv, fn, mat):
    verts = []; faces = []; uvs = []
    for j in range(nv + 1):
        for i in range(nu + 1):
            verts.append(fn(i/nu, j/nv)); uvs.append((i/nu*2.0, j/nv*2.4))
    for j in range(nv):
        for i in range(nu): a = j*(nu + 1) + i; faces.append((a, a + 1, a + nu + 2, a + nu + 1))
    o = mk_obj(name, verts, faces, mat)
    uvl = o.data.uv_layers.new(name='UVMap')
    for p in o.data.polygons:
        for li in p.loop_indices: uvl.data[li].uv = uvs[o.data.loops[li].vertex_index]
    return o

def add_collision(o, outer=0.004):
    o.modifiers.new('Collision', 'COLLISION'); o.collision.thickness_outer = outer; o.collision.cloth_friction = 40

def run_cloth(o, frames, mass=0.4, bend=2.0, tension=12, self_col=True, pressure=None, gravity=1.0, dist=0.008, selfd=0.008, shrink=0.0):
    m = o.modifiers.new('Cloth', 'CLOTH'); s = m.settings
    s.quality = 8; s.mass = mass; s.tension_stiffness = tension; s.compression_stiffness = tension; s.shear_stiffness = tension*0.6
    s.bending_stiffness = bend; s.air_damping = 2.0; s.effector_weights.gravity = gravity; s.shrink_min = shrink
    if pressure is not None: s.use_pressure = True; s.uniform_pressure_force = pressure
    c = m.collision_settings; c.distance_min = dist; c.collision_quality = 4
    c.use_self_collision = self_col; c.self_distance_min = selfd
    m.point_cache.frame_start = 1; m.point_cache.frame_end = frames
    sc.frame_start = 1; sc.frame_end = frames
    for f in range(1, frames + 1): sc.frame_set(f)
    apply_mods(o); sc.frame_set(1)

for o in bed + [matt]:
    if o.name.startswith(('P2_', 'P3_', 'P4_', 'P5_', 'Leg_', 'HB_')) or o is matt: add_collision(o)

# duvet with the top folded back
mx0, mx1 = 3*IN, 63*IN; ztop = mz1 + 0.035
DW, y0, yf, rr, back_len = 1.80, -0.05, 1.40, 0.022, 0.42
cxm = (mx0 + mx1)/2
L1 = yf - y0; L2 = math.pi*rr; Ltot = L1 + L2 + back_len
def duvet_fn(u, v):
    x = cxm - DW/2 + DW*u; s = v*Ltot
    if s <= L1: return (x, y0 + s, ztop)
    if s <= L1 + L2:
        a = (s - L1)/rr; return (x, yf + rr*math.sin(a), ztop + rr - rr*math.cos(a))
    return (x, yf - (s - L1 - L2), ztop + 2*rr)
duvet = grid('Duvet', 74, 96, duvet_fn, LINEN)
run_cloth(duvet, 55, mass=0.5, bend=1.5, tension=10, dist=0.008, selfd=0.009)
sol = duvet.modifiers.new('sol', 'SOLIDIFY'); sol.thickness = 0.014; sol.offset = 0
ss = duvet.modifiers.new('sub', 'SUBSURF'); ss.levels = 1; ss.render_levels = 2
smooth(duvet)

# pillows: pressure-inflated cases
def pillow(name, sx, sy, sz, mat, n=48, seed=0):
    import random as rd; rd.seed(seed)
    verts=[]; faces=[]; idx={}
    def f(u,v): return max(0.0,(1-u*u))**0.55*max(0.0,(1-v*v))**0.55
    for side in (1,-1):
        for j in range(n+1):
            for i in range(n+1):
                u=-1+2*i/n; v=-1+2*j/n
                x=sx*u*(1-0.07*(1-v*v)); y=sy*v*(1-0.07*(1-u*u))
                z=side*sz*f(u,v)*(1+0.04*math.sin(3*u+seed)*math.cos(2*v))
                edge = i in (0,n) or j in (0,n)
                key=(i,j) if edge else (i,j,side)
                if key not in idx: idx[key]=len(verts); verts.append((x,y,z))
        for j in range(n):
            for i in range(n):
                k=lambda ii,jj:idx[(ii,jj)] if (ii in (0,n) or jj in (0,n)) else idx[(ii,jj,side)]
                q=(k(i,j),k(i+1,j),k(i+1,j+1),k(i,j+1))
                faces.append(q if side>0 else tuple(reversed(q)))
    o=mk_obj(name,verts,faces,mat)
    uvl=o.data.uv_layers.new(name='UVMap')
    for p_ in o.data.polygons:
        for li in p_.loop_indices:
            co=o.data.vertices[o.data.loops[li].vertex_index].co; uvl.data[li].uv=(co.x*2,co.y*2)
    tx=bpy.data.textures.new(name+'_n','CLOUDS'); tx.noise_scale=0.25
    dm=o.modifiers.new('d','DISPLACE'); dm.texture=tx; dm.strength=0.012; dm.mid_level=0.5
    o.modifiers.new('sub','SUBSURF').levels=1; smooth(o)
    return o
sham = pillow('Sham0', 0.33, 0.33, 0.085, SHAM, seed=1)
pil = pillow('Pillow0', 0.37, 0.24, 0.075, PILLOW, seed=2)
def place(src, name, loc, rot):
    o = src.copy(); o.data = src.data.copy(); o.name = name; col.objects.link(o)
    o.location = loc; o.rotation_euler = Euler([math.radians(r) for r in rot]); return o
lum = pillow('Lumbar0', 0.27, 0.16, 0.06, SHAM, seed=3)
place(lum, 'Lumbar', (cxm + 0.05, 1.58, mz1 + 0.11), (48, 0, -3))
bpy.data.objects.remove(lum)
place(pil, 'PillowL', (cxm - 0.37, 1.84, mz1 + 0.17), (40, 0, 1.5))
place(pil, 'PillowR', (cxm + 0.37, 1.845, mz1 + 0.17), (38, 0, -2))
bpy.data.objects.remove(sham); bpy.data.objects.remove(pil)
for n_ in ('PillowL','PillowR','Lumbar'): add_collision(bpy.data.objects[n_], 0.006)

# throw across the foot, hanging off the camera side
for o in sc.objects:
    if 'Collision' in [m.type.title() for m in o.modifiers] or any(m.type == 'COLLISION' for m in o.modifiers):
        if o is not duvet: pass
dz = max((duvet.matrix_world @ Vector(v.co)).z for v in duvet.data.vertices) + 0.06
add_collision(duvet, 0.012)
TW, TL = 0.62, 1.55
add_collision(rug); add_collision(floor)
throw = grid('Throw', 46, 120, lambda u, v: (lambda X, Y: (0.838 + X*math.cos(0.12) - Y*math.sin(0.12), 0.45 + X*math.sin(0.12) + Y*math.cos(0.12), dz + 0.05 + 0.04*math.sin(9*v + 2*u)*math.sin(5*u)))(TL*(v - 0.5) + 0.12, TW*(u - 0.5)), THROW)
for p in throw.data.polygons: pass
run_cloth(throw, 70, mass=0.35, bend=0.25, tension=10, dist=0.006, selfd=0.006)
throw.modifiers.new('sol', 'SOLIDIFY').thickness = 0.01
throw.modifiers.new('sub', 'SUBSURF').levels = 1; smooth(throw)
# remove collision modifiers (not needed for render)
for o in sc.objects:
    for m in list(o.modifiers):
        if m.type == 'COLLISION': o.modifiers.remove(m)

bpy.ops.wm.save_as_mainfile(filepath=S + '/scene.blend')
print('SAVED')
