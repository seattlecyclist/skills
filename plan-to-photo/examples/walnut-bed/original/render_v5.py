import bpy, sys, math
import numpy as np
from mathutils import Vector
args = sys.argv[sys.argv.index('--') + 1:]
S, out, rx, ry, spp = args[0], args[1], int(args[2]), int(args[3]), int(args[4])
cam_loc = tuple(map(float, args[5].split(','))); tgt = tuple(map(float, args[6].split(','))); lens = float(args[7])
sun_az, exposure, shift_y = float(args[8]), float(args[9]), float(args[10])
mode = args[11] if len(args) > 11 else 'render'
HDRI = S + '/assets/hdri/borghese_gardens_4k.exr'
CLAMP = 8.0
ENV = 1.0
BACKPLATE = S + '/assets/hdri/suburban_garden_16k.hdr'
HAZE = float(args[14]) if len(args) > 14 else 0.12
BP_GAIN = float(args[15]) if len(args) > 15 else 1.0

import os
bpy.ops.wm.open_mainfile(filepath=S + '/' + os.environ.get('SCENE', 'scene.blend'))
sc = bpy.context.scene; col = sc.collection

im = bpy.data.images.load(HDRI)
w, h = im.size
px = np.empty(w * h * 4, dtype=np.float32); im.pixels.foreach_get(px)
px = px.reshape(h, w, 4)[:, :, :3]
lum = px @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
row, cl = np.unravel_index(np.argmax(lum), lum.shape)
el0 = ((row + 0.5) / h - 0.5) * math.pi
az0 = math.pi - 2 * math.pi * (cl + 0.5) / w
lat = ((np.arange(h) + 0.5) / h - 0.5) * math.pi
dom = (2 * math.pi / w) * (math.pi / h) * np.cos(lat)[:, None]
excess = np.clip(px - CLAMP, 0, None) * (lum > CLAMP)[:, :, None]
E = (excess * dom[:, :, None]).reshape(-1, 3).sum(0) * ENV
sun_strength = float(E @ np.array([0.2126, 0.7152, 0.0722]))
sun_strength *= float(args[13]) if len(args) > 13 else 1.0
sun_color = E / max(E.max(), 1e-9)
rot = az0 - math.radians(sun_az + 180)
print('HDRI sun az0 %.1f el %.1f, world rot %.1f, sun irradiance %.2f color %s' % (math.degrees(az0), math.degrees(el0), math.degrees(rot), sun_strength, np.round(sun_color, 3)))

wd = bpy.data.worlds.new('hdri'); sc.world = wd
nt = wd.node_tree; N = nt.nodes; Lk = nt.links
for n in list(N):
    if n.bl_idname != 'ShaderNodeOutputWorld': N.remove(n)
wout = [n for n in N if n.bl_idname == 'ShaderNodeOutputWorld'][0]
tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping'); mp.inputs['Rotation'].default_value = (0, 0, rot)
Lk.new(tc.outputs['Generated'], mp.inputs['Vector'])
et = N.new('ShaderNodeTexEnvironment'); et.image = im; et.interpolation = 'Cubic'
Lk.new(mp.outputs[0], et.inputs['Vector'])
vm = N.new('ShaderNodeVectorMath'); vm.operation = 'MINIMUM'; vm.inputs[1].default_value = (CLAMP, CLAMP, CLAMP)
Lk.new(et.outputs['Color'], vm.inputs[0])
lp = N.new('ShaderNodeLightPath')
bg_c = N.new('ShaderNodeBackground'); bg_c.inputs['Strength'].default_value = ENV
bg_l = N.new('ShaderNodeBackground'); bg_l.inputs['Strength'].default_value = ENV
bp = bpy.data.images.load(BACKPLATE)
bw, bh = bp.size
bpx = np.empty(bw * bh * 4, dtype=np.float32); bp.pixels.foreach_get(bpx)
bl = bpx.reshape(bh, bw, 4)[:, :, :3] @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
br_, bc_ = np.unravel_index(np.argmax(bl), bl.shape)
del bpx, bl
bp_az0 = math.pi - 2 * math.pi * (bc_ + 0.5) / bw
bp_rot = bp_az0 - math.radians(sun_az + 180)
if len(args) > 16: bp_rot = math.radians(float(args[16]))
print('BACKPLATE sun az0 %.1f rot %.1f' % (math.degrees(bp_az0), math.degrees(bp_rot)))
mp2 = N.new('ShaderNodeMapping'); mp2.inputs['Rotation'].default_value = (0, 0, bp_rot)
Lk.new(tc.outputs['Generated'], mp2.inputs['Vector'])
et2 = N.new('ShaderNodeTexEnvironment'); et2.image = bp; et2.interpolation = 'Cubic'
Lk.new(mp2.outputs[0], et2.inputs['Vector'])
hz = N.new('ShaderNodeMix'); hz.data_type = 'RGBA'; hz.blend_type = 'MIX'
SK = lambda n, i: [x for x in n.inputs if x.identifier == i][0]
SK(hz, 'Factor_Float').default_value = HAZE
Lk.new(et2.outputs['Color'], SK(hz, 'A_Color'))
SK(hz, 'B_Color').default_value = (0.80, 0.86, 0.95, 1.0)
Lk.new([x for x in hz.outputs if x.identifier == 'Result_Color'][0], bg_c.inputs['Color'])
bg_c.inputs['Strength'].default_value = BP_GAIN
Lk.new(vm.outputs[0], bg_l.inputs['Color'])
gm = bpy.data.meshes.new('glass')
gm.from_pydata([(-1.415, -0.75, 0.55), (-1.415, 0.95, 0.55), (-1.415, 0.95, 2.35), (-1.415, -0.75, 2.35)], [], [(0, 1, 2, 3)])
go = bpy.data.objects.new('WindowGlass', gm); col.objects.link(go)
gmat = bpy.data.materials.new('window_glass'); gn = gmat.node_tree.nodes; gl = gmat.node_tree.links
for n in list(gn):
    if n.bl_idname != 'ShaderNodeOutputMaterial': gn.remove(n)
gout = [n for n in gn if n.bl_idname == 'ShaderNodeOutputMaterial'][0]
tr = gn.new('ShaderNodeBsdfTransparent'); gs = gn.new('ShaderNodeBsdfGlossy'); gs.inputs['Roughness'].default_value = 0.0
fr = gn.new('ShaderNodeFresnel'); fr.inputs['IOR'].default_value = 1.52
fm = gn.new('ShaderNodeMath'); fm.operation = 'MULTIPLY'; fm.inputs[1].default_value = 0.6; gl.new(fr.outputs[0], fm.inputs[0])
gmx = gn.new('ShaderNodeMixShader'); gl.new(fm.outputs[0], gmx.inputs[0]); gl.new(tr.outputs[0], gmx.inputs[1]); gl.new(gs.outputs[0], gmx.inputs[2])
gl.new(gmx.outputs[0], gout.inputs['Surface'])
gm.materials.append(gmat)
mx = N.new('ShaderNodeMixShader')
Lk.new(lp.outputs['Is Camera Ray'], mx.inputs[0]); Lk.new(bg_l.outputs[0], mx.inputs[1]); Lk.new(bg_c.outputs[0], mx.inputs[2])
Lk.new(mx.outputs[0], wout.inputs['Surface'])

az = math.radians(sun_az)
to_sun = Vector((math.cos(el0) * math.cos(az + math.pi), math.cos(el0) * math.sin(az + math.pi), math.sin(el0)))

prefs = bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type = 'METAL'
prefs.get_devices()
for d in prefs.devices:
    d.use = d.type == 'METAL'
print('DEVICES', [(d.name, d.type, d.use) for d in prefs.devices])
sc.render.engine = 'CYCLES'; c = sc.cycles
c.device = 'GPU'

if mode == 'suncheck':
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    cd = bpy.data.cameras.new('chk'); cd.lens = 200
    cam = bpy.data.objects.new('chk', cd); col.objects.link(cam); sc.camera = cam
    cam.location = (0, 0, 0); cam.rotation_euler = to_sun.to_track_quat('-Z', 'Y').to_euler()
    c.samples = 4; c.use_denoising = False
    sc.render.resolution_x = 64; sc.render.resolution_y = 64; sc.render.resolution_percentage = 100
    sc.view_settings.view_transform = 'Standard'; sc.view_settings.exposure = -12
    sc.render.image_settings.file_format = 'PNG'; sc.render.filepath = out
    bpy.ops.render.render(write_still=True)
    sys.exit(0)

d = -to_sun
sl = bpy.data.lights.new('sun', 'SUN'); sl.energy = sun_strength; sl.angle = math.radians(0.55)
sl.color = tuple(float(x) for x in sun_color)
so = bpy.data.objects.new('sun', sl); col.objects.link(so); so.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
pl = bpy.data.lights.new('portal', 'AREA'); pl.shape = 'RECTANGLE'; pl.size = 1.7; pl.size_y = 1.8
try: pl.cycles.is_portal = True
except Exception: pl.is_portal = True
po = bpy.data.objects.new('portal', pl); col.objects.link(po)
po.location = (-1.40, 0.10, 1.45); po.rotation_euler = (0, math.radians(90), 0)
cd = bpy.data.cameras.new('cam'); cd.lens = lens; cd.sensor_width = 36
cd.dof.use_dof = True; cd.dof.aperture_fstop = 8.0
cam = bpy.data.objects.new('cam', cd); col.objects.link(cam); sc.camera = cam
cam.location = cam_loc; dv = Vector(tgt) - Vector(cam_loc); cam.rotation_euler = dv.to_track_quat('-Z', 'Y').to_euler()
cd.dof.focus_distance = (Vector((1.70, 0.45, 0.3)) - Vector(cam_loc)).length
cd.shift_y = shift_y
c.samples = spp; c.use_adaptive_sampling = True; c.adaptive_threshold = 0.006 if spp > 200 else 0.05
c.use_denoising = True
try: c.denoiser = 'OPENIMAGEDENOISE'
except Exception: pass
c.max_bounces = 12; c.diffuse_bounces = 6; c.glossy_bounces = 4; c.transmission_bounces = 8; c.transparent_max_bounces = 16
c.sample_clamp_indirect = 3; c.caustics_reflective = False; c.caustics_refractive = False
c.blur_glossy = 1.0
sc.render.resolution_x = rx; sc.render.resolution_y = ry; sc.render.resolution_percentage = 100
vs = sc.view_settings
vs.view_transform = 'AgX'
for lk in ('AgX - Medium High Contrast', 'Medium High Contrast', 'AgX - Base Contrast'):
    try: vs.look = lk; break
    except Exception: pass
vs.exposure = exposure
try:
    vs.use_white_balance = True; vs.white_balance_temperature = float(args[12]) if len(args) > 12 else 5400.0
except Exception as e: print('WB', e)
sc.render.image_settings.file_format = 'PNG'
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
print('RENDERED', out)
