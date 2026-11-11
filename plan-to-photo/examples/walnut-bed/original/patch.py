import bpy, sys, math
S = sys.argv[sys.argv.index('--') + 1]
bpy.ops.wm.open_mainfile(filepath=S + '/scene_v1.blend')
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


def wood_mat(name, axis, dark, mid, light, rough=0.42, coat=0.12, quarter=True, streak=25.0, line=40.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name); b = NB(m)
    tc = b.new('ShaderNodeTexCoord'); sep = b.new('ShaderNodeSeparateXYZ'); b.link(tc.outputs['Object'], sep.inputs[0])
    rnd = b.new('ShaderNodeObjectInfo').outputs['Random']
    X, Y, Z = sep.outputs[0], sep.outputs[1], sep.outputs[2]
    along, p1, p2 = {'X': (X, Z, Y), 'Y': (Y, Z, X), 'Z': (Z, X, Y)}[axis]
    s = b.math('MULTIPLY_ADD', p2, 0.35 if quarter else 0.8, p1)
    s = b.math('MULTIPLY_ADD', rnd, 7.3, s)
    a = b.math('MULTIPLY_ADD', rnd, 31.0, along)
    def vec(k):
        v = b.new('ShaderNodeCombineXYZ'); b.link(s, v.inputs[0]); b.link(b.math('MULTIPLY', a, k), v.inputs[1]); b.link(b.math('MULTIPLY', p2, 0.3), v.inputs[2]); return v.outputs[0]
    # broad colour streaks, a few cm across, long along the grain
    nB = b.noise(vec(0.08), streak, detail=3, rough=0.5, dist=0.3)
    nC = b.noise(vec(0.03), streak*0.25, detail=2, rough=0.5)
    # growth lines, a few mm apart, wandering
    w1 = b.new('ShaderNodeTexWave', wave_type='BANDS', bands_direction='X', wave_profile='SAW')
    w1.inputs['Scale'].default_value = line; w1.inputs['Distortion'].default_value = 4; w1.inputs['Detail'].default_value = 2; w1.inputs['Detail Scale'].default_value = 0.6
    b.link(vec(0.04), w1.inputs['Vector'])
    # pores: bump only
    nP = b.noise(vec(0.08), 450, detail=0, rough=0.3)
    base = b.ramp(nB.outputs['Fac'], [(0.28, dark), (0.48, mid), (0.70, light)])
    big = b.ramp(nC.outputs['Fac'], [(0.35, (0.85, 0.82, 0.80)), (0.65, (1.1, 1.08, 1.05))])
    c = b.mix(1.0, base, big, 'MULTIPLY')
    ln = b.ramp(w1.outputs['Fac'], [(0.0, (1.05, 1.04, 1.03)), (0.75, (0.90, 0.89, 0.88)), (1.0, (0.62, 0.60, 0.60))])
    c = b.mix(1.0, c, ln, 'MULTIPLY')
    b.set('Base Color', c)
    b.set('Roughness', b.math('MULTIPLY_ADD', nP.outputs['Fac'], 0.12, rough - 0.06))
    b.set('Coat Weight', coat); b.set('Coat Roughness', 0.3)
    h = b.math('ADD', b.math('MULTIPLY', w1.outputs['Fac'], 0.15), b.math('MULTIPLY', b.math('GREATER_THAN', nP.outputs['Fac'], 0.6), -0.6))
    b.set('Normal', b.bump(h, 0.035, 0.0003))
    return m

for ax in 'XYZ':
    wood_mat('walnut_'+ax, ax, (0.032, 0.0145, 0.007), (0.080, 0.038, 0.018), (0.135, 0.070, 0.034))
    wood_mat('oak_'+ax, ax, (0.24, 0.16, 0.09), (0.34, 0.24, 0.14), (0.42, 0.31, 0.19), rough=0.55, coat=0.0, quarter=False, streak=18, line=30)
    wood_mat('maple_'+ax, ax, (0.50, 0.37, 0.23), (0.60, 0.46, 0.30), (0.66, 0.52, 0.36), rough=0.5, coat=0.05)
# puffier duvet
d = bpy.data.objects['Duvet']
d.modifiers['sol'].thickness = 0.028
tx = bpy.data.textures.new('lumps', 'CLOUDS'); tx.noise_scale = 0.12
dm = d.modifiers.new('lumps', 'DISPLACE'); dm.texture = tx; dm.strength = 0.012; dm.mid_level = 0.5
while d.modifiers[0].name != 'lumps':
    with bpy.context.temp_override(object=d): bpy.ops.object.modifier_move_up(modifier='lumps')
d.modifiers['sub'].levels = 2
for n in ('PillowL', 'PillowR', 'Lumbar'):
    o = bpy.data.objects[n]
    for m in o.modifiers:
        if m.type == 'DISPLACE': m.strength = 0.02; m.texture.noise_scale = 0.12
bpy.ops.wm.save_as_mainfile(filepath=S + '/scene.blend')
print('PATCHED')
