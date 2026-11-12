"""plan-to-photo: shared Blender helpers.

Import it from any script that runs inside Blender (or with the `bpy` pip package):

    import sys; sys.path.insert(0, '<skill>/scripts'); from p2p import *

Units are meters, Z up. Everything here was worked out on a real render (the walnut castle-leg bed
in examples/walnut-bed) and each helper carries the lesson that produced it. See
references/realism.md for the why.
"""
import bpy, bmesh, math, os, re, json
from mathutils import Vector, Matrix, Euler

IN = 0.0254
MM = 0.001


def sc():
    return bpy.context.scene


def col():
    return bpy.context.scene.collection


# ------------------------------------------------------------------ geometry

def mk_obj(name, verts, faces, mat=None):
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    o = bpy.data.objects.new(name, me); col().objects.link(o)
    if mat: o.data.materials.append(mat)
    return o


def box(name, x0, y0, z0, x1, y1, z1, mat=None):
    x0, x1 = sorted((x0, x1)); y0, y1 = sorted((y0, y1)); z0, z1 = sorted((z0, z1))
    v = [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    f = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return mk_obj(name, v, f, mat)


def apply_mods(o, types=None):
    """Apply modifiers (all, or only those whose type is in `types`)."""
    for m in list(o.modifiers):
        if types and m.type not in types: continue
        with bpy.context.temp_override(object=o, active_object=o):
            bpy.ops.object.modifier_apply(modifier=m.name)


def boolean(o, cutter, op='DIFFERENCE'):
    m = o.modifiers.new('b', 'BOOLEAN'); m.operation = op; m.object = cutter; m.solver = 'EXACT'
    apply_mods(o, {'BOOLEAN'}); bpy.data.objects.remove(cutter)


def ease(o, width=1.5 * MM, segments=2, angle=40):
    """Eased edges. Nothing real has a knife-sharp 90 degree edge; a 1 to 2 mm round catches a line
    of light along every arris and is the single cheapest realism win for furniture."""
    m = o.modifiers.new('ease', 'BEVEL'); m.width = width; m.segments = segments
    m.limit_method = 'ANGLE'; m.angle_limit = math.radians(angle); m.harden_normals = False
    return m


def smooth(o, on=True):
    for p in o.data.polygons: p.use_smooth = on


def recalc(o, merge=1e-5):
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=merge)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(o.data); bm.free()


def dissolve_flat(o, angle=1.0):
    """Merge coplanar triangles from an exporter into clean faces so the bevel stays tidy."""
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(angle), verts=bm.verts, edges=bm.edges)
    bm.to_mesh(o.data); bm.free()


def lathe(name, prof, segs=64, mat=None, cap_bottom=True, cap_top=True):
    """Solid of revolution from [(radius, z), ...]: lamps, vases, bowls, bottles, turned legs."""
    verts, faces = [], []
    for (r, z) in prof:
        for i in range(segs):
            a = 2 * math.pi * i / segs; verts.append((r * math.cos(a), r * math.sin(a), z))
    for j in range(len(prof) - 1):
        for i in range(segs):
            a = j * segs + i; b = j * segs + (i + 1) % segs
            faces.append((a, b, b + segs, a + segs))
    if cap_bottom: faces.append(tuple(reversed(range(segs))))
    if cap_top: faces.append(tuple(range((len(prof) - 1) * segs, len(prof) * segs)))
    return mk_obj(name, verts, faces, mat)


def extrude(name, poly, y0, y1, mat=None):
    """Extrude a closed XZ outline [(x, z), ...] between y0 and y1: curved boards, arched aprons,
    headboards. Model true curves this way instead of trusting a faceted export."""
    n = len(poly)
    verts = [(x, y0, z) for x, z in poly] + [(x, y1, z) for x, z in poly]
    faces = [tuple(range(n)), tuple(reversed(range(n, 2 * n)))]
    for i in range(n): faces.append((i, n + i, n + (i + 1) % n, (i + 1) % n))
    o = mk_obj(name, verts, faces, mat); recalc(o)
    return o


def grid(name, nu, nv, fn, mat=None, uv_scale=(2.0, 2.4)):
    """A cloth sheet from fn(u, v) -> (x, y, z), u and v in 0..1, with UVs."""
    verts, faces, uvs = [], [], []
    for j in range(nv + 1):
        for i in range(nu + 1):
            verts.append(fn(i / nu, j / nv)); uvs.append((i / nu * uv_scale[0], j / nv * uv_scale[1]))
    for j in range(nv):
        for i in range(nu):
            a = j * (nu + 1) + i; faces.append((a, a + 1, a + nu + 2, a + nu + 1))
    o = mk_obj(name, verts, faces, mat)
    uvl = o.data.uv_layers.new(name='UVMap')
    for p in o.data.polygons:
        for li in p.loop_indices: uvl.data[li].uv = uvs[o.data.loops[li].vertex_index]
    return o


def bounds(objs, evaluated=True):
    """World-space (min, max) over one object or a list."""
    if not isinstance(objs, (list, tuple)): objs = [objs]
    dg = bpy.context.evaluated_depsgraph_get()
    lo = [1e9] * 3; hi = [-1e9] * 3
    for o in objs:
        e = o.evaluated_get(dg) if evaluated else o
        for v in e.data.vertices:
            w = o.matrix_world @ v.co
            for i in range(3): lo[i] = min(lo[i], w[i]); hi[i] = max(hi[i], w[i])
    return Vector(lo), Vector(hi)


def long_axis(o):
    d = o.dimensions
    return 'XYZ'[max(range(3), key=lambda i: d[i])]


# ------------------------------------------------------------------ model import

def import_model(path, scale=1.0, up='Z', forward='Y'):
    """Import OBJ, glTF/GLB, FBX, STL or PLY. Returns the new mesh objects, with transforms applied
    and normals fixed. `scale` converts to meters (0.0254 for inches, 0.001 for mm)."""
    before = set(bpy.data.objects)
    ext = os.path.splitext(path)[1].lower()
    if ext == '.obj':
        bpy.ops.wm.obj_import(filepath=path, forward_axis=forward, up_axis=up)
    elif ext in ('.glb', '.gltf'):
        bpy.ops.import_scene.gltf(filepath=path)
    elif ext == '.fbx':
        bpy.ops.import_scene.fbx(filepath=path)
    elif ext == '.stl':
        bpy.ops.wm.stl_import(filepath=path, forward_axis=forward, up_axis=up)
    elif ext == '.ply':
        bpy.ops.wm.ply_import(filepath=path, forward_axis=forward, up_axis=up)
    else:
        raise SystemExit('import_model: unsupported format ' + ext)
    objs = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
    for o in objs:
        if o.name not in col().objects and not o.users_collection: col().objects.link(o)
        o.data = o.data.copy()
        o.data.transform(Matrix.Scale(scale, 4) @ o.matrix_world)
        o.matrix_world = Matrix.Identity(4)
        recalc(o)
    for o in [o for o in bpy.data.objects if o not in before and o.type == 'EMPTY']:
        bpy.data.objects.remove(o)
    return objs


def place_on_floor(objs, z=0.0, at=None, rotate_z=0.0):
    """Rotate about Z, sit the lowest point at z, and optionally move the bbox's min corner to `at`
    (x, y)."""
    if rotate_z:
        R = Matrix.Rotation(math.radians(rotate_z), 4, 'Z')
        for o in objs: o.data.transform(R); o.data.update()
    lo, hi = bounds(objs, evaluated=False)
    d = Vector((0, 0, z - lo.z))
    if at is not None: d.x = at[0] - lo.x; d.y = at[1] - lo.y
    T = Matrix.Translation(d)
    for o in objs: o.data.transform(T); o.data.update()
    return bounds(objs, evaluated=False)


# ------------------------------------------------------------------ node builder

def _sock(sockets, ident):
    for s in sockets:
        if s.identifier == ident: return s
    raise KeyError(ident)


class NB:
    """Tiny node-tree builder for Principled materials."""

    def __init__(self, mat, clear=True):
        mat.use_nodes = True; self.t = mat.node_tree; self.n = self.t.nodes; self.l = self.t.links
        if clear:
            self.n.clear()
            self.out = self.n.new('ShaderNodeOutputMaterial')
            self.bsdf = self.n.new('ShaderNodeBsdfPrincipled')
            self.link(self.bsdf.outputs[0], self.out.inputs['Surface'])
        else:
            self.bsdf = [x for x in self.n if x.bl_idname == 'ShaderNodeBsdfPrincipled'][0]
            self.out = [x for x in self.n if x.bl_idname == 'ShaderNodeOutputMaterial'][0]

    def new(self, t, **kw):
        nd = self.n.new(t)
        for k, v in kw.items(): setattr(nd, k, v)
        return nd

    def link(self, a, b): self.l.new(a, b)

    def m(self, op, a, b=None, c=None):
        nd = self.new('ShaderNodeMath', operation=op)
        for i, x in enumerate((a, b, c)):
            if x is None: continue
            if isinstance(x, (int, float)): nd.inputs[i].default_value = x
            else: self.link(x, nd.inputs[i])
        return nd.outputs[0]

    def comb(self, x, y, z=0.0):
        nd = self.new('ShaderNodeCombineXYZ')
        for i, v in enumerate((x, y, z)):
            if isinstance(v, (int, float)): nd.inputs[i].default_value = v
            else: self.link(v, nd.inputs[i])
        return nd.outputs[0]

    def tex(self, image, vec, proj='FLAT', blend=0.2):
        nd = self.new('ShaderNodeTexImage', image=image, interpolation='Cubic', projection=proj)
        if proj == 'BOX': nd.projection_blend = blend
        self.link(vec, nd.inputs['Vector'])
        return nd

    def mixc(self, fac, a, b, blend='MIX'):
        nd = self.new('ShaderNodeMix', data_type='RGBA', blend_type=blend)
        for ident, x in (('Factor_Float', fac), ('A_Color', a), ('B_Color', b)):
            s = _sock(nd.inputs, ident)
            if isinstance(x, (int, float)): s.default_value = x
            elif isinstance(x, tuple): s.default_value = (*x, 1.0) if len(x) == 3 else x
            else: self.link(x, s)
        return _sock(nd.outputs, 'Result_Color')

    def mixf(self, fac, a, b):
        nd = self.new('ShaderNodeMix', data_type='FLOAT')
        for ident, x in (('Factor_Float', fac), ('A_Float', a), ('B_Float', b)):
            s = _sock(nd.inputs, ident)
            if isinstance(x, (int, float)): s.default_value = x
            else: self.link(x, s)
        return _sock(nd.outputs, 'Result_Float')

    def maprange(self, v, a, b, c, d):
        nd = self.new('ShaderNodeMapRange'); self.link(v, nd.inputs['Value'])
        nd.inputs['From Min'].default_value = a; nd.inputs['From Max'].default_value = b
        nd.inputs['To Min'].default_value = c; nd.inputs['To Max'].default_value = d
        return nd.outputs['Result']

    def ramp(self, fac, stops):
        r = self.new('ShaderNodeValToRGB'); self.link(fac, r.inputs[0])
        el = r.color_ramp.elements
        while len(el) < len(stops): el.new(0.5)
        for e, (p, c) in zip(el, stops): e.position = p; e.color = (*c, 1) if len(c) == 3 else c
        return r.outputs[0]

    def noise(self, vec, scale, detail=2, rough=0.5, dist=0.0):
        nz = self.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = scale
        nz.inputs['Detail'].default_value = detail; nz.inputs['Roughness'].default_value = rough
        nz.inputs['Distortion'].default_value = dist
        if vec is not None: self.link(vec, nz.inputs['Vector'])
        return nz

    def bump(self, h, strength, dist):
        nd = self.new('ShaderNodeBump'); nd.inputs['Strength'].default_value = strength
        nd.inputs['Distance'].default_value = dist; self.link(h, nd.inputs['Height'])
        return nd.outputs['Normal']

    def set(self, name, v):
        s = self.bsdf.inputs[name]
        if isinstance(v, tuple) and s.type == 'RGBA' and len(v) == 3: s.default_value = (*v, 1)
        elif isinstance(v, (int, float, tuple)): s.default_value = v
        else: self.link(v, s)


# ------------------------------------------------------------------ scanned PBR sets

MAP_KEYS = {
    'color': ('_diff', '_color', '_albedo', '_basecolor', '_diffuse', '_col'),
    'rough': ('_rough', '_roughness'),
    'disp': ('_disp', '_displacement', '_height', '_bump'),
    'normal': ('_nor_gl', '_normalgl', '_normal_gl'),
    'ao': ('_ao', '_ambientocclusion'),
}


def find_maps(set_dir):
    """Map a texture-set folder (Poly Haven, ambientCG, or any `<name>_<map>` set) to its files."""
    out = {}
    if not set_dir or not os.path.isdir(set_dir): return out
    files = sorted(f for f in os.listdir(set_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.exr', '.tif', '.tiff')))
    for key, pats in MAP_KEYS.items():
        for f in files:
            fl = f.lower()
            if any(p in fl for p in pats) and '_nor_dx' not in fl and 'normaldx' not in fl:
                out[key] = os.path.join(set_dir, f); break
    return out


def img(path, data=False):
    im = bpy.data.images.load(path, check_existing=True)
    if data: im.colorspace_settings.name = 'Non-Color'
    return im


def wood(name, set_dir=None, axis='X', tile=1.0, tone=(1, 1, 1), gamma=1.0, rough=(0.32, 0.50),
         bump=0.12, coat=0.0, procedural=None):
    """Scanned wood with the grain along `axis` of each object.

    - Every object reads its own patch of the scan (offset by Object Info > Random), and two patches
      cross-fade along the length, so no two boards repeat and long rails don't show the tile.
    - End grain: faces whose normal points along the grain get the scan turned 90 degrees and
      compressed, so ends read as end grain instead of stretched streaks.
    - `tone` multiplies the scan and `gamma` deepens it: scans are shot flat and unfinished, an oiled
      finish darkens and warms them (walnut: gamma 1.5, tone (0.24, 0.205, 0.19)).
    - Oiled satin is roughness 0.32 to 0.50 with no clearcoat; a coat > 0 reads as varnish.
    Falls back to a procedural wood when the set is missing (`procedural` = (dark, mid, light)).
    """
    maps = find_maps(set_dir)
    m = bpy.data.materials.new(name)
    if 'color' not in maps:
        return _procedural_wood(m, axis, *(procedural or ((0.040, 0.018, 0.008), (0.125, 0.060, 0.027), (0.185, 0.098, 0.045))), rough=sum(rough) / 2, coat=coat)
    t = NB(m)
    D = img(maps['color']); R = img(maps['rough'], True) if 'rough' in maps else None
    H = img(maps['disp'], True) if 'disp' in maps else None
    tc = t.new('ShaderNodeTexCoord')
    sp = t.new('ShaderNodeSeparateXYZ'); t.link(tc.outputs['Object'], sp.inputs[0])
    sn = t.new('ShaderNodeSeparateXYZ'); t.link(tc.outputs['Normal'], sn.inputs[0])
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
    u = t.m('DIVIDE', t.m('MULTIPLY_ADD', rnd, 17.31, u), tile)
    v = t.m('DIVIDE', t.m('MULTIPLY_ADD', rnd, 5.13, t.m('MULTIPLY_ADD', m1, 0.37, v)), tile)
    va = t.comb(u, v); vb = t.comb(t.m('ADD', u, 0.47), t.m('ADD', v, 0.291))
    nz = t.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 1.3; nz.inputs['Detail'].default_value = 0.0
    t.link(t.comb(t.m('MULTIPLY_ADD', rnd, 9.0, along), 0.0, 0.0), nz.inputs['Vector'])
    fac = t.maprange(nz.outputs['Fac'], 0.42, 0.58, 0.0, 1.0)
    c = t.mixc(fac, t.tex(D, va).outputs['Color'], t.tex(D, vb).outputs['Color'])
    if gamma != 1.0:
        g = t.new('ShaderNodeGamma'); g.inputs['Gamma'].default_value = gamma; t.link(c, g.inputs['Color']); c = g.outputs['Color']
    if tuple(tone) != (1, 1, 1): c = t.mixc(1.0, c, tuple(tone), 'MULTIPLY')
    t.link(c, t.bsdf.inputs['Base Color'])
    if R: t.link(t.maprange(t.mixf(fac, t.tex(R, va).outputs['Color'], t.tex(R, vb).outputs['Color']), 0, 1, *rough), t.bsdf.inputs['Roughness'])
    else: t.set('Roughness', sum(rough) / 2)
    if H: t.link(t.bump(t.mixf(fac, t.tex(H, va).outputs['Color'], t.tex(H, vb).outputs['Color']), bump, 0.0004), t.bsdf.inputs['Normal'])
    t.set('Coat Weight', coat)
    return m


def _procedural_wood(m, axis, dark, mid, light, rough=0.42, coat=0.0, ring_scale=95, quarter=True):
    b = NB(m)
    tc = b.new('ShaderNodeTexCoord'); sep = b.new('ShaderNodeSeparateXYZ'); b.link(tc.outputs['Object'], sep.inputs[0])
    rnd = b.new('ShaderNodeObjectInfo').outputs['Random']
    X, Y, Z = sep.outputs[0], sep.outputs[1], sep.outputs[2]
    along, p1, p2 = {'X': (X, Z, Y), 'Y': (Y, Z, X), 'Z': (Z, X, Y)}[axis]
    s = b.m('MULTIPLY_ADD', rnd, 7.3, b.m('MULTIPLY_ADD', p2, 0.35 if quarter else 0.8, p1))
    a = b.m('MULTIPLY_ADD', rnd, 31.0, along)
    v = b.comb(s, b.m('MULTIPLY', a, 0.045), b.m('MULTIPLY', p2, 0.3))
    w1 = b.new('ShaderNodeTexWave', wave_type='BANDS', bands_direction='X', wave_profile='SIN')
    w1.inputs['Scale'].default_value = ring_scale; w1.inputs['Distortion'].default_value = 7; w1.inputs['Detail'].default_value = 3
    b.link(v, w1.inputs['Vector'])
    nB = b.noise(b.comb(s, b.m('MULTIPLY', a, 0.12), p2), 5.0, detail=3, rough=0.55)
    nP = b.noise(b.comb(s, b.m('MULTIPLY', a, 0.06), p2), 700, detail=1, rough=0.4)
    pore = b.m('GREATER_THAN', nP.outputs['Fac'], 0.62)
    c = b.ramp(w1.outputs['Fac'], [(0.0, dark), (0.35, mid), (1.0, mid)])
    c = b.mixc(b.ramp(nB.outputs['Fac'], [(0.42, (0, 0, 0)), (0.7, (0.6, 0.6, 0.6))]), c, light)
    c = b.mixc(b.m('MULTIPLY', pore, 0.55), c, tuple(x * 0.5 for x in dark))
    b.set('Base Color', c); b.set('Roughness', b.m('MULTIPLY_ADD', pore, 0.18, rough)); b.set('Coat Weight', coat)
    b.set('Normal', b.bump(b.m('MULTIPLY_ADD', w1.outputs['Fac'], 0.25, b.m('MULTIPLY', pore, -1.0)), 0.06, 0.0004))
    return m


def wood_set(name, **kw):
    """Three materials, one per grain axis: {'X': mat, 'Y': mat, 'Z': mat}."""
    return {ax: wood('%s_%s' % (name, ax), axis=ax, **kw) for ax in 'XYZ'}


def assign_wood(o, lib, axis=None):
    """Give an object the material from `lib` whose grain runs along its longest side (legs
    vertical, rails along their length) unless `axis` says otherwise."""
    o.data.materials.clear(); o.data.materials.append(lib[axis or long_axis(o)])


def planks(name, set_dir=None, plank_w=0.185, plank_l=1.7, tile=0.5, tone=(0.92, 0.86, 0.78), rough=(0.38, 0.62),
           along='Y', seam=0.0012, procedural=((0.20, 0.13, 0.07), (0.36, 0.25, 0.15), (0.42, 0.31, 0.19))):
    """Plank floor (or butcher block, or table top) from one veneer scan: rows of planks with
    staggered butt joints, a different patch and tone per plank, and dark seams in colour and bump.
    A floor from one tiled photo reads as wallpaper; per-plank variation is what sells it."""
    maps = find_maps(set_dir)
    m = bpy.data.materials.new(name)
    if 'color' not in maps: return _procedural_wood(m, 'Y' if along == 'Y' else 'X', *procedural, rough=0.5, quarter=False)
    t = NB(m)
    D = img(maps['color']); R = img(maps['rough'], True) if 'rough' in maps else None
    H = img(maps['disp'], True) if 'disp' in maps else None
    tc = t.new('ShaderNodeTexCoord'); sp = t.new('ShaderNodeSeparateXYZ'); t.link(tc.outputs['Object'], sp.inputs[0])
    x, y = (sp.outputs[0], sp.outputs[1]) if along == 'Y' else (sp.outputs[1], sp.outputs[0])
    row = t.m('FLOOR', t.m('DIVIDE', x, plank_w))
    wn1 = t.new('ShaderNodeTexWhiteNoise', noise_dimensions='1D'); t.link(row, wn1.inputs['W'])
    yy = t.m('MULTIPLY_ADD', wn1.outputs['Value'], plank_l, y)
    pl = t.m('FLOOR', t.m('DIVIDE', yy, plank_l))
    wn2 = t.new('ShaderNodeTexWhiteNoise', noise_dimensions='3D'); t.link(t.comb(row, pl, 0.5), wn2.inputs['Vector'])
    wn3 = t.new('ShaderNodeTexWhiteNoise', noise_dimensions='3D'); t.link(t.comb(row, pl, 2.5), wn3.inputs['Vector'])
    r2, r3 = wn2.outputs['Value'], wn3.outputs['Value']
    across = t.m('SUBTRACT', x, t.m('MULTIPLY', row, plank_w))
    alongp = t.m('SUBTRACT', yy, t.m('MULTIPLY', pl, plank_l))
    vec = t.comb(t.m('DIVIDE', t.m('MULTIPLY_ADD', r2, 3.7, across), tile), t.m('DIVIDE', t.m('MULTIPLY_ADD', r3, 5.3, alongp), tile))
    dA = t.m('MINIMUM', across, t.m('SUBTRACT', plank_w, across))
    dL = t.m('MINIMUM', alongp, t.m('SUBTRACT', plank_l, alongp))
    sm = t.m('MINIMUM', t.maprange(dA, 0.0, seam, 0.0, 1.0), t.maprange(dL, 0.0, seam, 0.0, 1.0))
    c = t.tex(D, vec).outputs['Color']
    tn = t.maprange(r2, 0.0, 1.0, 0.84, 1.10)
    c = t.mixc(1.0, c, t.comb(tn, tn, tn), 'MULTIPLY')
    c = t.mixc(1.0, c, tuple(tone), 'MULTIPLY')
    sv = t.maprange(sm, 0, 1, 0.45, 1)
    c = t.mixc(1.0, c, t.comb(sv, sv, sv), 'MULTIPLY')
    t.link(c, t.bsdf.inputs['Base Color'])
    if R: t.link(t.maprange(t.tex(R, vec).outputs['Color'], 0, 1, *rough), t.bsdf.inputs['Roughness'])
    h = sm if not H else t.m('ADD', t.m('MULTIPLY', t.tex(H, vec).outputs['Color'], 0.25), sm)
    t.link(t.bump(h, 0.35, 0.0008), t.bsdf.inputs['Normal'])
    return m


def surface(name, set_dir=None, tile=0.5, color=None, hsv=(0.5, 1.0, 1.0), rough=(0.4, 0.8), bump=0.4,
            bump_dist=0.002, sheen=0.0, metal=0.0, coat=0.0, proj='BOX'):
    """Any scanned surface on box projection: stone and quartz counters, tile, concrete, plaster,
    brick, carpet and rugs, leather. `color` (r, g, b) replaces the scan's colour (keeping its
    detail); `hsv` = (hue, saturation, value) adjusts it."""
    maps = find_maps(set_dir)
    m = bpy.data.materials.new(name); t = NB(m)
    tc = t.new('ShaderNodeTexCoord'); mp = t.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (1 / tile,) * 3; t.link(tc.outputs['Object'], mp.inputs['Vector'])
    vec = mp.outputs[0]
    if 'color' in maps:
        c = t.tex(img(maps['color']), vec, proj).outputs['Color']
        if tuple(hsv) != (0.5, 1.0, 1.0):
            hs = t.new('ShaderNodeHueSaturation'); hs.inputs['Hue'].default_value, hs.inputs['Saturation'].default_value, hs.inputs['Value'].default_value = hsv
            t.link(c, hs.inputs['Color']); c = hs.outputs['Color']
        if color: c = t.mixc(0.85, c, tuple(color), 'COLOR')
        t.link(c, t.bsdf.inputs['Base Color'])
    else:
        t.set('Base Color', tuple(color or (0.6, 0.6, 0.6)))
    if 'rough' in maps: t.link(t.maprange(t.tex(img(maps['rough'], True), vec, proj).outputs['Color'], 0, 1, *rough), t.bsdf.inputs['Roughness'])
    else: t.set('Roughness', sum(rough) / 2)
    if 'disp' in maps: t.link(t.bump(t.tex(img(maps['disp'], True), vec, proj).outputs['Color'], bump, bump_dist), t.bsdf.inputs['Normal'])
    t.set('Sheen Weight', sheen); t.set('Sheen Roughness', 0.6); t.set('Metallic', metal); t.set('Coat Weight', coat)
    return m


def fabric(name, color, set_dir=None, tile=0.27, bump=0.22, rough=(0.78, 0.95), sheen=0.6, uv=True, weave=900):
    """Cloth: your colour, with the scan's weave in bump and roughness, plus sheen. Linen, percale,
    knit, boucle, velvet. Use UVs (uv=True) on cloth-sim sheets so the weave follows the drape."""
    maps = find_maps(set_dir)
    m = bpy.data.materials.new(name); t = NB(m)
    tc = t.new('ShaderNodeTexCoord'); mp = t.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (1 / tile,) * 3
    t.link(tc.outputs['UV' if uv else 'Object'], mp.inputs['Vector']); vec = mp.outputs[0]
    proj = 'FLAT' if uv else 'BOX'
    nz = t.noise(vec, 3.0, detail=4, rough=0.6)
    t.link(t.ramp(nz.outputs['Fac'], [(0.3, tuple(c * 0.92 for c in color)), (0.7, tuple(min(1, c * 1.05) for c in color))]), t.bsdf.inputs['Base Color'])
    h = maps.get('disp') or maps.get('rough')
    if h:
        t.link(t.bump(t.tex(img(h, True), vec, proj).outputs['Color'], bump, 0.0005), t.bsdf.inputs['Normal'])
    else:
        wa = t.new('ShaderNodeTexWave', wave_type='BANDS', bands_direction='X'); wa.inputs['Scale'].default_value = weave * tile
        wb = t.new('ShaderNodeTexWave', wave_type='BANDS', bands_direction='Y'); wb.inputs['Scale'].default_value = weave * tile
        t.link(vec, wa.inputs['Vector']); t.link(vec, wb.inputs['Vector'])
        t.link(t.bump(t.m('MULTIPLY', wa.outputs['Fac'], wb.outputs['Fac']), bump, 0.002), t.bsdf.inputs['Normal'])
    if 'rough' in maps: t.link(t.maprange(t.tex(img(maps['rough'], True), vec, proj).outputs['Color'], 0, 1, *rough), t.bsdf.inputs['Roughness'])
    else: t.set('Roughness', sum(rough) / 2)
    t.set('Sheen Weight', sheen); t.set('Sheen Roughness', 0.4); t.set('Subsurface Weight', 0.05)
    return m


def paint(name, color, rough=0.9, var=0.012, bump=0.02, scale=2.5):
    """Wall paint or limewash. Keep the variation tiny (var about 0.01, bump about 0.02): v3 of the
    walnut bed had visible blotches from a 10% noise ramp, and they also slowed denoising."""
    m = bpy.data.materials.new(name); b = NB(m)
    tc = b.new('ShaderNodeTexCoord'); nz = b.noise(tc.outputs['Object'], scale, detail=6, rough=0.6)
    b.set('Base Color', b.ramp(nz.outputs['Fac'], [(0.15, tuple(c * (1 - var) for c in color)), (0.85, tuple(c * (1 + var) for c in color))]))
    b.set('Roughness', rough); b.set('Normal', b.bump(nz.outputs['Fac'], bump, 0.003))
    return m


def plain(name, color, rough=0.5, metal=0.0, coat=0.0, alpha=1.0):
    m = bpy.data.materials.new(name); b = NB(m)
    b.set('Base Color', tuple(color)); b.set('Roughness', rough); b.set('Metallic', metal); b.set('Coat Weight', coat)
    if alpha < 1: b.set('Alpha', alpha)
    return m


def metal(name, color=(0.8, 0.6, 0.35), rough=0.3):
    """Brass (0.8, 0.6, 0.35), steel (0.55, 0.55, 0.55), blackened (0.05, 0.05, 0.05) rough 0.45."""
    return plain(name, color, rough=rough, metal=1.0)


def glass(name, tint=(1, 1, 1), rough=0.0):
    m = bpy.data.materials.new(name); b = NB(m)
    b.set('Base Color', tuple(tint)); b.set('Roughness', rough); b.set('Transmission Weight', 1.0); b.set('IOR', 1.5)
    return m


def translucent(name, color, mix=0.5, transparent=0.0):
    """Lamp shades (mix 0.5) and sheer curtains (transparent 0.55)."""
    m = bpy.data.materials.new(name); b = NB(m)
    tr = b.new('ShaderNodeBsdfTranslucent'); tr.inputs['Color'].default_value = (*color, 1)
    b.set('Base Color', tuple(c * 0.85 for c in color)); b.set('Roughness', 0.85); b.set('Sheen Weight', 0.4)
    mx = b.new('ShaderNodeMixShader'); mx.inputs[0].default_value = mix
    b.link(b.bsdf.outputs[0], mx.inputs[1]); b.link(tr.outputs[0], mx.inputs[2]); out = mx.outputs[0]
    if transparent:
        tp = b.new('ShaderNodeBsdfTransparent'); m2 = b.new('ShaderNodeMixShader'); m2.inputs[0].default_value = transparent
        b.link(out, m2.inputs[1]); b.link(tp.outputs[0], m2.inputs[2]); out = m2.outputs[0]
    b.link(out, b.out.inputs['Surface'])
    return m


def emissive(name, color=(1.0, 0.75, 0.5), strength=5.0):
    m = bpy.data.materials.new(name); b = NB(m)
    b.set('Emission Color', tuple(color)); b.set('Emission Strength', strength)
    return m


# ------------------------------------------------------------------ cloth and contact

def add_collision(o, outer=0.004, friction=40):
    if not any(m.type == 'COLLISION' for m in o.modifiers): o.modifiers.new('Collision', 'COLLISION')
    o.collision.thickness_outer = outer; o.collision.cloth_friction = friction


def clear_collisions():
    for o in sc().objects:
        for m in list(o.modifiers):
            if m.type == 'COLLISION': o.modifiers.remove(m)


def run_cloth(o, frames, mass=0.4, bend=2.0, tension=12, self_col=True, pressure=None, gravity=1.0,
              dist=0.008, selfd=0.008, shrink=0.0):
    """Simulate a cloth sheet over the collision objects and bake the result into the mesh.
    Duvet: mass 0.5, bend 1.5. Throw: mass 0.35, bend 0.25. Tablecloth: mass 0.3, bend 0.5."""
    m = o.modifiers.new('Cloth', 'CLOTH'); s = m.settings
    s.quality = 8; s.mass = mass; s.tension_stiffness = tension; s.compression_stiffness = tension
    s.shear_stiffness = tension * 0.6; s.bending_stiffness = bend; s.air_damping = 2.0
    s.effector_weights.gravity = gravity; s.shrink_min = shrink
    if pressure is not None: s.use_pressure = True; s.uniform_pressure_force = pressure
    c = m.collision_settings; c.distance_min = dist; c.collision_quality = 4
    c.use_self_collision = self_col; c.self_distance_min = selfd
    m.point_cache.frame_start = 1; m.point_cache.frame_end = frames
    sc().frame_start = 1; sc().frame_end = frames
    for f in range(1, frames + 1): sc().frame_set(f)
    apply_mods(o, {'CLOTH'}); sc().frame_set(1)


def _np():
    import numpy as np
    return np


def getv(o):
    np = _np(); a = np.zeros(len(o.data.vertices) * 3); o.data.vertices.foreach_get('co', a); return a.reshape(-1, 3)


def setv(o, P):
    o.data.vertices.foreach_set('co', P.reshape(-1)); o.data.update()


def bake_world(o):
    """Bake the object's transform into its mesh so vertex coords are world coords."""
    bpy.context.view_layer.update()  # location/rotation set in this script are not in matrix_world until now
    o.data = o.data.copy(); o.data.transform(o.matrix_world); o.matrix_world = Matrix.Identity(4)


def smin(a, b, k):
    np = _np(); h = np.maximum(k - np.abs(a - b), 0.0) / k
    return np.minimum(a, b) - h * h * k * 0.25


def smax(a, b, k):
    return -smin(-a, -b, k)


def rest_on(o, z, sink=0.024):
    """Drop an object so its lowest point sinks `sink` below the support height `z`. Soft things
    (pillows, cushions, a folded throw) must press INTO what holds them; a 1 cm gap reads as
    floating in every render."""
    bake_world(o); P = getv(o); P[:, 2] += (z - sink) - P[:, 2].min(); setv(o, P)


def lean_on(o, axis, plane, overlap=0.014, k=0.02):
    """Slide a soft object along +axis ('x' or 'y', negative plane side) until it presses into the
    plane at `plane` (a headboard face, a sofa back), then flatten its back against it."""
    bake_world(o); i = 'xy'.index(axis); P = getv(o)
    P[:, i] += (plane + overlap) - P[:, i].max(); P[:, i] = smin(P[:, i], plane + 0.001, k); setv(o, P)


def press_into(support, pressers, res=0.005, strength=0.6, band=0.04):
    """Dent a soft support (mattress, seat cushion) where soft things press into it, and lift the
    pressers' undersides to the dented surface. The support must be a mesh whose top face is at
    its max Z; it is re-sliced finely so the dent can show."""
    np = _np()
    bake_world(support); lo, hi = bounds(support, evaluated=False)
    X0, X1, Y0, Y1, ZT = lo.x, hi.x, lo.y, hi.y, hi.z
    gx = np.arange(X0, X1 + res, res); gy = np.arange(Y0, Y1 + res, res)
    pen = np.zeros((len(gx), len(gy)))
    for o in pressers:
        P = getv(o)
        m = (P[:, 2] < ZT) & (P[:, 0] > X0) & (P[:, 0] < X1) & (P[:, 1] > Y0) & (P[:, 1] < Y1)
        ix = ((P[m, 0] - X0) / res).round().astype(int).clip(0, len(gx) - 1)
        iy = ((P[m, 1] - Y0) / res).round().astype(int).clip(0, len(gy) - 1)
        np.maximum.at(pen, (ix, iy), ZT - P[m, 2])

    def maxf(a, r):
        out = a.copy()
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1): out = np.maximum(out, np.roll(np.roll(a, dx, 0), dy, 1))
        return out

    def blur(a, s):
        r = int(3 * s); kk = np.exp(-0.5 * (np.arange(-r, r + 1) / s) ** 2); kk /= kk.sum()
        a = np.apply_along_axis(lambda v: np.convolve(np.pad(v, r, mode='edge'), kk, 'valid'), 0, a)
        return np.apply_along_axis(lambda v: np.convolve(np.pad(v, r, mode='edge'), kk, 'valid'), 1, a)

    Dn = strength * blur(maxf(pen, 3), 4.0)

    def dent(x, y):
        fx = np.clip((x - X0) / res, 0, len(gx) - 1.001); fy = np.clip((y - Y0) / res, 0, len(gy) - 1.001)
        i, j = fx.astype(int), fy.astype(int); tx, ty = fx - i, fy - j
        v = Dn[i, j] * (1 - tx) * (1 - ty) + Dn[i + 1, j] * tx * (1 - ty) + Dn[i, j + 1] * (1 - tx) * ty + Dn[i + 1, j + 1] * tx * ty
        inside = (x > X0) & (x < X1) & (y > Y0) & (y < Y1)
        return np.where(inside, v, 0.0), inside

    for o in pressers:
        P = getv(o); d, inside = dent(P[:, 0], P[:, 1])
        P[:, 2] = np.where(inside, smax(P[:, 2], ZT - d - 0.001, 0.012), P[:, 2]); setv(o, P); smooth(o)
    if Dn.max() > 0:
        ys, xs = np.nonzero(Dn.T > 1e-4)
        bx0, bx1 = gx[xs.min()] - 0.05, gx[xs.max()] + 0.05; by0, by1 = gy[ys.min()] - 0.05, gy[ys.max()] + 0.05
        bm = bmesh.new(); bm.from_mesh(support.data)
        cuts = [('x', x) for x in np.arange(max(X0 + 0.01, bx0), min(X1 - 0.01, bx1), 0.012)]
        cuts += [('y', y) for y in np.arange(max(Y0 + 0.01, by0), min(Y1 - 0.01, by1), 0.012)]
        for ax, c in cuts:
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
                                   plane_co=(c, 0, 0) if ax == 'x' else (0, c, 0), plane_no=(1, 0, 0) if ax == 'x' else (0, 1, 0))
        bm.to_mesh(support.data); bm.free()
        P = getv(support); d, _ = dent(P[:, 0], P[:, 1])
        P[:, 2] -= d * np.clip((P[:, 2] - (ZT - band)) / (band * 0.875), 0, 1); setv(support, P)
    return float(Dn.max())


def creases(o, seed=11, depth=0.009):
    """Sculpt corner pulls, random fold lines, a centre sag and lumps into a pillow or cushion
    (local coords centred at 0, thin along Z). Smooth pressure-inflated pillows read as plastic."""
    np = _np(); rng = np.random.default_rng(seed)
    for m in list(o.modifiers):
        if m.type in ('DISPLACE', 'SUBSURF'): apply_mods(o, {m.type})
    P = getv(o); a, b, c = np.abs(P).max(0)
    x, y, z = P[:, 0] / a, P[:, 1] / b, P[:, 2] / c
    nrm = np.stack([x / a, y / b, z / c], 1); nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
    off = np.zeros(len(P)); X, Y = P[:, 0], P[:, 1]
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = sx * a * 0.97, sy * b * 0.95; base = math.atan2(-cy, -cx)
            for _ in range(rng.integers(3, 6)):
                ang = base + rng.uniform(-0.55, 0.55); dx, dy = math.cos(ang), math.sin(ang)
                rx, ry = X - cx, Y - cy; t = rx * dx + ry * dy; dist = np.abs(-rx * dy + ry * dx)
                ln = rng.uniform(0.10, 0.24); w = rng.uniform(0.004, 0.009)
                off += rng.uniform(0.5, 1.0) * np.exp(-(dist / w) ** 2) * np.clip(t / 0.02, 0, 1) * np.exp(-np.clip(t, 0, None) / ln)
    for _ in range(rng.integers(3, 6)):
        ang = rng.uniform(0, math.pi); dx, dy = math.cos(ang), math.sin(ang)
        px, py = rng.uniform(-0.6, 0.6) * a, rng.uniform(-0.6, 0.6) * b
        rx, ry = X - px, Y - py; t = rx * dx + ry * dy; dist = np.abs(-rx * dy + ry * dx)
        off += rng.uniform(0.3, 0.6) * np.exp(-(dist / rng.uniform(0.008, 0.015)) ** 2) * np.exp(-(t / rng.uniform(0.06, 0.16)) ** 2)
    off = -depth * off * np.clip(np.abs(z) * 1.6 - 0.3, 0, 1)
    sag = -0.35 * c * np.exp(-((x / 0.55) ** 2 + (y / 0.5) ** 2)) * np.clip(z * 2, 0, 1)
    lumps = 0.004 * (np.sin(7.1 * X + rng.uniform(0, 6)) * np.sin(9.3 * Y + rng.uniform(0, 6)))
    setv(o, P + nrm * (off + lumps)[:, None] + np.stack([0 * x, 0 * x, sag], 1))
    o.modifiers.new('sub', 'SUBSURF').levels = 1; smooth(o)


def wrinkle(o, seed=7, depth=0.018, folds=90, lump=0.007):
    """Fine folds and lumps on a simulated sheet (duvet, throw, tablecloth). A cloth sim over a
    mattress settles into a few big smooth drapes; real bedding also carries dozens of small
    compression folds and filling lumps, and without them it reads as rubber (walnut bed r00).
    Subdivides once, then pushes vertices along their normals."""
    np = _np(); rng = np.random.default_rng(seed)
    o.modifiers.new('wsub', 'SUBSURF').levels = 1; apply_mods(o, {'SUBSURF'})
    P = getv(o); o.data.update(); N = np.zeros(P.size); o.data.vertex_normals.foreach_get('vector', N); N = N.reshape(-1, 3)
    off = np.zeros(len(P))
    for _ in range(folds):
        c = P[rng.integers(len(P))]; a = rng.uniform(0, math.pi); d = np.array([math.cos(a), math.sin(a), 0.0])
        r = P - c; t = r @ d; s = np.linalg.norm(r - t[:, None] * d, axis=1)
        ln = rng.uniform(0.12, 0.5); w = rng.uniform(0.012, 0.03)
        off += rng.choice([1.0, 1.0, -0.6]) * rng.uniform(0.4, 1.0) * np.exp(-(s / w) ** 2) * np.exp(-(t / ln) ** 2)
    ph = rng.uniform(0, 2 * math.pi, 4)
    lumps = (np.sin(11 * P[:, 0] + ph[0]) * np.sin(13 * P[:, 1] + ph[1]) + 0.5 * np.sin(23 * P[:, 0] + 17 * P[:, 1] + ph[2])) / 1.5
    setv(o, P + N * (depth * off + lump * lumps)[:, None])
    print('WRINKLE %s %d verts, deepest fold %.1f mm' % (o.name, len(P), 1000 * depth * float(np.abs(off).max())))


def pillow(name, sx, sy, sz, mat, n=48, seed=0):
    """A pillow or cushion: a filled case sx by sy (half sizes) and sz thick, centred at the origin,
    lying in XY. Follow with creases(), then rotate and place, then lean_on/rest_on/press_into."""
    import random as rd; rd.seed(seed)
    verts, faces, idx = [], [], {}

    def f(u, v): return max(0.0, (1 - u * u)) ** 0.55 * max(0.0, (1 - v * v)) ** 0.55
    for side in (1, -1):
        for j in range(n + 1):
            for i in range(n + 1):
                u = -1 + 2 * i / n; v = -1 + 2 * j / n
                x = sx * u * (1 - 0.07 * (1 - v * v)); y = sy * v * (1 - 0.07 * (1 - u * u))
                z = side * sz * f(u, v) * (1 + 0.04 * math.sin(3 * u + seed) * math.cos(2 * v))
                key = (i, j) if (i in (0, n) or j in (0, n)) else (i, j, side)
                if key not in idx: idx[key] = len(verts); verts.append((x, y, z))
        for j in range(n):
            for i in range(n):
                k = lambda ii, jj: idx[(ii, jj)] if (ii in (0, n) or jj in (0, n)) else idx[(ii, jj, side)]
                q = (k(i, j), k(i + 1, j), k(i + 1, j + 1), k(i, j + 1))
                faces.append(q if side > 0 else tuple(reversed(q)))
    o = mk_obj(name, verts, faces, mat)
    uvl = o.data.uv_layers.new(name='UVMap')
    for p_ in o.data.polygons:
        for li in p_.loop_indices:
            co = o.data.vertices[o.data.loops[li].vertex_index].co; uvl.data[li].uv = (co.x * 2, co.y * 2)
    return o


# ------------------------------------------------------------------ props

def lamp(name, x, y, z0, base_mat, shade_mat, rod_mat, watts=18, color=(1.0, 0.72, 0.45)):
    """Table lamp with a warm bulb inside a translucent shade."""
    prof = [(0.0, 0), (0.06, 0.0), (0.075, 0.02), (0.095, 0.08), (0.10, 0.14), (0.085, 0.22), (0.05, 0.27), (0.025, 0.30), (0.02, 0.33), (0.0, 0.33)]
    b = lathe(name + '_Base', prof, 64, base_mat, cap_bottom=False, cap_top=False); smooth(b); b.location = (x, y, z0)
    b.modifiers.new('s', 'SUBSURF').levels = 2
    r = lathe(name + '_Rod', [(0.006, 0.33), (0.006, 0.52)], 24, rod_mat); r.location = (x, y, z0)
    s = lathe(name + '_Shade', [(0.16, 0.36), (0.13, 0.56)], 96, shade_mat, cap_bottom=False, cap_top=False); s.location = (x, y, z0)
    s.modifiers.new('sol', 'SOLIDIFY').thickness = 0.002; smooth(s)
    ld = bpy.data.lights.new(name + '_Bulb', 'POINT'); ld.energy = watts; ld.shadow_soft_size = 0.065; ld.color = color
    lo = bpy.data.objects.new(name + '_Bulb', ld); lo.location = (x, y, z0 + 0.46); col().objects.link(lo)
    return [b, r, s, lo]


def books(name, x, y, z0, mats, page_mat, sizes=((0.24, 0.17, 0.032, 4), (0.21, 0.15, 0.025, -6))):
    out = []; z = z0
    for i, (w_, d_, h_, rot) in enumerate(sizes):
        bx = box('%s%d' % (name, i), -w_ / 2, -d_ / 2, 0, w_ / 2, d_ / 2, h_, mats[i % len(mats)]); ease(bx, 0.002)
        pg = box('%s%d_pages' % (name, i), -w_ / 2 + 0.004, -d_ / 2 + 0.006, 0.003, w_ / 2 - 0.004, d_ / 2 + 0.0005, h_ - 0.003, page_mat)
        for o in (bx, pg): o.location = (x, y, z); o.rotation_euler.z = math.radians(rot)
        z += h_; out += [bx, pg]
    return out


VESSELS = {
    'vase': [(0.0, 0), (0.035, 0), (0.05, 0.03), (0.055, 0.08), (0.035, 0.15), (0.018, 0.19), (0.02, 0.21), (0.015, 0.21), (0.012, 0.19)],
    'bowl': [(0.0, 0), (0.05, 0), (0.06, 0.005), (0.12, 0.05), (0.14, 0.085), (0.135, 0.085), (0.115, 0.05), (0.055, 0.012), (0.0, 0.012)],
    'jar': [(0.0, 0), (0.05, 0), (0.055, 0.01), (0.055, 0.16), (0.045, 0.17), (0.045, 0.19), (0.0, 0.19)],
    'mug': [(0.0, 0), (0.04, 0), (0.042, 0.005), (0.042, 0.095), (0.038, 0.095), (0.038, 0.006), (0.0, 0.006)],
    'bottle': [(0.0, 0), (0.035, 0), (0.037, 0.01), (0.037, 0.2), (0.015, 0.25), (0.013, 0.3), (0.0, 0.3)],
    'pot': [(0.0, 0), (0.07, 0), (0.08, 0.01), (0.1, 0.2), (0.105, 0.21), (0.095, 0.21), (0.0, 0.19)],
}


def vessel(name, kind, x, y, z0, mat, scale=1.0):
    """Turned ceramics and glass: vase, bowl, jar, mug, bottle, pot."""
    o = lathe(name, [(r * scale, z * scale) for r, z in VESSELS[kind]], 64, mat, cap_bottom=True, cap_top=False)
    smooth(o); o.modifiers.new('s', 'SUBSURF').levels = 2; o.location = (x, y, z0)
    return o


def art(name, x0, x1, z0, z1, wall_y, frame_mat, canvas_mat, depth=0.035, border=0.025):
    """A framed canvas hung on a wall facing -Y at wall_y."""
    fr = box(name + '_Frame', x0, wall_y - depth, z0, x1, wall_y, z1, frame_mat); ease(fr, 0.002)
    boolean(fr, box('fi', x0 + border, wall_y - depth - 0.02, z0 + border, x1 - border, wall_y - 0.01, z1 - border))
    cv = box(name + '_Canvas', x0 + border, wall_y - 0.022, z0 + border, x1 - border, wall_y - 0.005, z1 - border, canvas_mat)
    return [fr, cv]


def abstract_canvas(name, palette=((0.62, 0.57, 0.48), (0.48, 0.40, 0.30), (0.20, 0.13, 0.08), (0.05, 0.045, 0.04))):
    m = bpy.data.materials.new(name); b = NB(m); tc = b.new('ShaderNodeTexCoord')
    nz = b.noise(tc.outputs['Generated'], 1.6, detail=6, rough=0.55, dist=1.2)
    b.set('Base Color', b.ramp(nz.outputs['Fac'], list(zip((0.25, 0.48, 0.58, 0.75), palette))))
    b.set('Roughness', 0.85); b.set('Normal', b.bump(b.noise(tc.outputs['Generated'], 300, detail=3).outputs['Fac'], 0.25, 0.002))
    return m


# ------------------------------------------------------------------ room shell

def _wall_frame(room, wall):
    """Return (to_world(u, w, z), wall_len) for a wall: u runs along the wall, w into the room."""
    x0, x1 = room['x']; y0, y1 = room['y']
    if wall == 'left': return (lambda u, w, z: (x0 + w, u, z)), (y0, y1)
    if wall == 'right': return (lambda u, w, z: (x1 - w, u, z)), (y0, y1)
    if wall == 'front': return (lambda u, w, z: (u, y0 + w, z)), (x0, x1)
    if wall == 'back': return (lambda u, w, z: (u, y1 - w, z)), (x0, x1)
    raise SystemExit('wall must be left, right, front or back')


def _ubox(name, f, u0, u1, w0, w1, z0, z1, mat):
    a = f(u0, w0, z0); b = f(u1, w1, z1)
    return box(name, a[0], a[1], a[2], b[0], b[1], b[2], mat)


def build_room(room, mats):
    """A room shell from a spec dict (see references/scene-spec.md): floor, ceiling, four walls with
    thickness, window openings with trim, sill, apron and muntins, baseboards, optional curtains,
    and an invisible outside ground. Returns the window rectangles for render.py's light portals.
    Walls are real boxes (not planes) so light can't leak at the corners."""
    x0, x1 = room['x']; y0, y1 = room['y']; H = room.get('height', 2.7); T = 0.12
    mk_obj('Floor', [(x0, y0, 0), (x1, y0, 0), (x1, y1, 0), (x0, y1, 0)], [(0, 1, 2, 3)], mats['floor'])
    if room.get('ceiling', True):
        mk_obj('Ceiling', [(x0, y0, H), (x0, y1, H), (x1, y1, H), (x1, y0, H)], [(0, 1, 2, 3)], mats['ceiling'])
    walls = {
        'back': box('Wall_back', x0 - T, y1, 0, x1 + T, y1 + T, H, mats.get('wall_back', mats['wall'])),
        'front': box('Wall_front', x0 - T, y0 - T, 0, x1 + T, y0, H, mats.get('wall_front', mats['wall'])),
        'right': box('Wall_right', x1, y0, 0, x1 + T, y1, H, mats.get('wall_right', mats['wall'])),
        'left': box('Wall_left', x0 - T, y0, 0, x0, y1, H, mats.get('wall_left', mats['wall'])),
    }
    for nm in room.get('omit_walls', []):
        bpy.data.objects.remove(walls.pop(nm))
    trim = mats['trim']; windows = []
    for i, w in enumerate(room.get('windows', [])):
        f, _ = _wall_frame(room, w['wall']); u0, u1 = w['from'], w['to']; z0, z1 = w.get('sill', 0.55), w.get('head', 2.35)
        a = f(u0, -0.5, z0); b = f(u1, 0.1, z1)
        boolean(walls[w['wall']], box('cut', a[0], a[1], a[2], b[0], b[1], b[2]))
        cw = 0.07
        for nm, args in [('L', (u0 - cw, u0, -T, 0.018, z0 - cw, z1 + cw)), ('R', (u1, u1 + cw, -T, 0.018, z0 - cw, z1 + cw)),
                         ('T', (u0 - cw, u1 + cw, -T, 0.018, z1, z1 + cw)),
                         ('Sill', (u0 - cw - 0.03, u1 + cw + 0.03, -T, 0.045, z0 - 0.025, z0 + 0.005)),
                         ('Apron', (u0 - cw, u1 + cw, 0, 0.016, z0 - 0.12, z0 - 0.025)),
                         ('Rail', (u0, u1, -0.09, -0.04, z0, z0 + 0.05))]:
            ease(_ubox('Win%d_%s' % (i, nm), f, *args, trim), 0.003)
        if w.get('muntins', True):
            um = (u0 + u1) / 2; zm = w.get('meeting_rail', z0 + (z1 - z0) * 0.6)
            ease(_ubox('Win%d_MullV' % i, f, um - 0.025, um + 0.025, -0.09, -0.04, z0, z1, trim), 0.003)
            ease(_ubox('Win%d_MullH' % i, f, u0, u1, -0.09, -0.04, zm - 0.02, zm + 0.02, trim), 0.003)
        if w.get('curtains') and 'sheer' in mats:
            for side, (c0, c1) in (('A', (u0 - 0.42, u0 + 0.08)), ('B', (u1 - 0.08, u1 + 0.42))):
                _curtain('Win%d_Curtain%s' % (i, side), f, c0, c1, H, mats['sheer'])
            if 'rod' in mats: _ubox('Win%d_Rod' % i, f, u0 - 0.5, u1 + 0.5, 0.08, 0.10, H - 0.12, H - 0.10, mats['rod'])
        c = f((u0 + u1) / 2, -0.06, (z0 + z1) / 2)
        windows.append({'wall': w['wall'], 'center': c, 'width': u1 - u0, 'height': z1 - z0})
    bb = room.get('baseboard', 0.11)
    if bb:
        for wall in walls:
            f, (a, b) = _wall_frame(room, wall)
            ease(_ubox('Base_' + wall, f, a, b, 0, 0.016, 0, bb, trim), 0.003)
    g = mk_obj('Outside', [(-80, -80, -0.6), (80, -80, -0.6), (80, 80, -0.6), (-80, 80, -0.6)], [(0, 1, 2, 3)], plain('ground', (0.25, 0.27, 0.20), 0.9))
    g.visible_camera = False  # it lights the room from below the sill; the camera sees the HDRI instead
    sc()['p2p_windows'] = json.dumps(windows)
    return windows


def _curtain(name, f, u0, u1, H, mat, nx=120, nz=60):
    verts, faces = [], []
    for j in range(nz + 1):
        z = 0.02 + (H - 0.14) * j / nz
        for i in range(nx + 1):
            u = u0 + (u1 - u0) * i / nx
            w = 0.10 + 0.035 * math.sin((u - u0) / 0.09 * 2 * math.pi + 0.3 * math.sin(z * 3)) * (0.8 + 0.2 * j / nz)
            verts.append(f(u, w, z))
    for j in range(nz):
        for i in range(nx): a = j * (nx + 1) + i; faces.append((a, a + 1, a + nx + 2, a + nx + 1))
    o = mk_obj(name, verts, faces, mat); smooth(o)
    return o


def rug(name, x0, y0, x1, y1, mat, thick=0.008):
    o = box(name, x0, y0, 0, x1, y1, thick, mat); ease(o, 0.003, 2, 60)
    return o


def save(path):
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(path))
    print('SAVED', path)
