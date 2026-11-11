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
Lk.new(et.outputs['Color'], bg_c.inputs['Color']); Lk.new(vm.outputs[0], bg_l.inputs['Color'])
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
cd.dof.use_dof = True; cd.dof.aperture_fstop = 5.6
cam = bpy.data.objects.new('cam', cd); col.objects.link(cam); sc.camera = cam
cam.location = cam_loc; dv = Vector(tgt) - Vector(cam_loc); cam.rotation_euler = dv.to_track_quat('-Z', 'Y').to_euler()
cd.dof.focus_distance = (Vector((1.70, 0.45, 0.3)) - Vector(cam_loc)).length
cd.shift_y = shift_y
if mode == 'pano':
    cd.type = 'PANO'
    try: cd.panorama_type = 'EQUIRECTANGULAR'
    except Exception: cd.cycles.panorama_type = 'EQUIRECTANGULAR'
    cd.dof.use_dof = False; cd.shift_y = 0.0
    cam.rotation_euler = (math.pi / 2, 0, math.atan2(tgt[1] - cam_loc[1], tgt[0] - cam_loc[0]) - math.pi / 2)
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
