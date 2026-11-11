"""Light, frame and render a scene built by build_scene.py.

    blender -b -P render.py -- scene.blend out.png [options]
    python render.py -- scene.blend out.png [options]          (with the `bpy` pip package)

Lighting is an HDRI for sky and bounce, split into two parts so it both looks right and renders
clean: everything brighter than --clamp is cut out of the HDRI and put back as a SUN lamp of the same
energy, colour and direction (sharp, noise-free sun patches), and the world is rotated so that sun
comes from --sun-az. Every window from build_room gets a light portal. Cycles on whatever GPU is
there, AgX tone mapping, white balance, depth of field.

Options (all optional; defaults are the walnut bed's):
  --res 3000x2000        --samples 2048        --preview (quarter res, 64 spp, fast denoise)
  --cam x,y,z            --target x,y,z        --lens 28 (mm, 36 mm sensor)   --shift-y 0.07
  --fstop 5.6            --focus x,y,z (default: target)
  --hdri path            --sun-az deg (compass direction the sun shines FROM, in scene XY: 0 = +X, 90 = +Y)
  --sun-gain 1.0         --clamp 8.0           --env 1.0
  --exposure 1.1         --wb 5400             --look "AgX - Medium High Contrast"
  --border x0,y0,x1,y1   (render a crop, fractions of the frame, for detail checks)
  --backplate path       (separate high-res image seen only through windows; --haze 0.12 --bp-gain 1.0)
  --suncheck             (render 64 px looking at the sun direction, to verify the HDRI alignment)
  --device auto|cpu
Lamps already in the scene (bedside lamps, pendants, under-cabinet strips) are kept.
"""
import bpy, sys, os, math, json, argparse
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
ap = argparse.ArgumentParser()
ap.add_argument('scene'); ap.add_argument('out')
ap.add_argument('--res', default='3000x2000'); ap.add_argument('--samples', type=int, default=2048)
ap.add_argument('--preview', action='store_true')
ap.add_argument('--cam', default='2.45,-1.1,0.95'); ap.add_argument('--target', default='0.6,1.3,0.5')
ap.add_argument('--lens', type=float, default=28); ap.add_argument('--shift-y', type=float, default=0.07)
ap.add_argument('--shift-x', type=float, default=0.0)
ap.add_argument('--fstop', type=float, default=5.6); ap.add_argument('--focus', default=None)
ap.add_argument('--hdri', default=None); ap.add_argument('--sun-az', type=float, default=160)
ap.add_argument('--sun-gain', type=float, default=1.0); ap.add_argument('--clamp', type=float, default=8.0)
ap.add_argument('--env', type=float, default=1.0)
ap.add_argument('--sun-el', type=float, default=26, help='only used without an HDRI')
ap.add_argument('--exposure', type=float, default=1.1); ap.add_argument('--wb', type=float, default=5400)
ap.add_argument('--look', default='AgX - Medium High Contrast')
ap.add_argument('--border', default=None)
ap.add_argument('--backplate', default=None); ap.add_argument('--haze', type=float, default=0.12)
ap.add_argument('--bp-gain', type=float, default=1.0)
ap.add_argument('--suncheck', action='store_true'); ap.add_argument('--device', default='auto')
A = ap.parse_args(argv)
V = lambda s: Vector(tuple(map(float, s.split(','))))

bpy.ops.wm.open_mainfile(filepath=os.path.abspath(A.scene))
sc = bpy.context.scene; col = sc.collection
LUMA = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)


def hdri_sun(im, clamp):
    """Brightest pixel's direction, and the energy above `clamp` (W/m2) and its colour."""
    w, h = im.size
    px = np.empty(w * h * 4, dtype=np.float32); im.pixels.foreach_get(px)
    px = px.reshape(h, w, 4)[:, :, :3]; lum = px @ LUMA
    row, cl = np.unravel_index(np.argmax(lum), lum.shape)
    el = ((row + 0.5) / h - 0.5) * math.pi; az = math.pi - 2 * math.pi * (cl + 0.5) / w
    lat = ((np.arange(h) + 0.5) / h - 0.5) * math.pi
    dom = (2 * math.pi / w) * (math.pi / h) * np.cos(lat)[:, None]
    E = ((np.clip(px - clamp, 0, None) * (lum > clamp)[:, :, None]) * dom[:, :, None]).reshape(-1, 3).sum(0)
    return az, el, float(E @ LUMA), E / max(E.max(), 1e-9)


sun_from = math.radians(A.sun_az)
wd = bpy.data.worlds.new('p2p_world'); sc.world = wd; wd.use_nodes = True
nt = wd.node_tree; N = nt.nodes; L = nt.links
for n in list(N):
    if n.bl_idname != 'ShaderNodeOutputWorld': N.remove(n)
wout = [n for n in N if n.bl_idname == 'ShaderNodeOutputWorld'][0]
if A.hdri:
    im = bpy.data.images.load(os.path.abspath(A.hdri))
    az0, el, sun_e, sun_c = hdri_sun(im, A.clamp)
    rot = az0 - sun_from
    sun_e *= A.env * A.sun_gain
    print('HDRI sun at az %.1f el %.1f; world rotated %.1f; sun %.2f W/m2 colour %s' % (math.degrees(az0), math.degrees(el), math.degrees(rot), sun_e, np.round(sun_c, 3)))
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping'); mp.inputs['Rotation'].default_value = (0, 0, rot)
    L.new(tc.outputs['Generated'], mp.inputs['Vector'])
    et = N.new('ShaderNodeTexEnvironment'); et.image = im; et.interpolation = 'Cubic'; L.new(mp.outputs[0], et.inputs['Vector'])
    vm = N.new('ShaderNodeVectorMath'); vm.operation = 'MINIMUM'; vm.inputs[1].default_value = (A.clamp,) * 3
    L.new(et.outputs['Color'], vm.inputs[0])
    bg_l = N.new('ShaderNodeBackground'); bg_l.inputs['Strength'].default_value = A.env; L.new(vm.outputs[0], bg_l.inputs['Color'])
    bg_c = N.new('ShaderNodeBackground'); bg_c.inputs['Strength'].default_value = A.env
    if A.backplate:
        bp = bpy.data.images.load(os.path.abspath(A.backplate))
        baz, _, _, _ = hdri_sun(bp, A.clamp) if bp.size[0] * bp.size[1] < 9e7 else (az0, 0, 0, 0)
        mp2 = N.new('ShaderNodeMapping'); mp2.inputs['Rotation'].default_value = (0, 0, baz - sun_from)
        L.new(tc.outputs['Generated'], mp2.inputs['Vector'])
        et2 = N.new('ShaderNodeTexEnvironment'); et2.image = bp; et2.interpolation = 'Cubic'; L.new(mp2.outputs[0], et2.inputs['Vector'])
        hz = N.new('ShaderNodeMix'); hz.data_type = 'RGBA'
        [s for s in hz.inputs if s.identifier == 'Factor_Float'][0].default_value = A.haze
        L.new(et2.outputs['Color'], [s for s in hz.inputs if s.identifier == 'A_Color'][0])
        [s for s in hz.inputs if s.identifier == 'B_Color'][0].default_value = (0.80, 0.86, 0.95, 1.0)
        L.new([s for s in hz.outputs if s.identifier == 'Result_Color'][0], bg_c.inputs['Color'])
        bg_c.inputs['Strength'].default_value = A.bp_gain
    else:
        L.new(et.outputs['Color'], bg_c.inputs['Color'])
    lp = N.new('ShaderNodeLightPath'); mx = N.new('ShaderNodeMixShader')
    L.new(lp.outputs['Is Camera Ray'], mx.inputs[0]); L.new(bg_l.outputs[0], mx.inputs[1]); L.new(bg_c.outputs[0], mx.inputs[2])
    L.new(mx.outputs[0], wout.inputs['Surface'])
else:
    el = math.radians(A.sun_el); sun_e = 3.5 * A.sun_gain; sun_c = np.array([1.0, 0.93, 0.82])
    bg = N.new('ShaderNodeBackground'); bg.inputs['Color'].default_value = (0.55, 0.65, 0.85, 1); bg.inputs['Strength'].default_value = 0.6 * A.env
    L.new(bg.outputs[0], wout.inputs['Surface'])
    print('No HDRI: flat sky plus a sun. Fetch one with fetch_assets.py for real light.')

to_sun = Vector((math.cos(el) * math.cos(sun_from), math.cos(el) * math.sin(sun_from), math.sin(el)))

prefs = bpy.context.preferences.addons['cycles'].preferences
sc.render.engine = 'CYCLES'; c = sc.cycles; c.device = 'CPU'
if A.device != 'cpu':
    for kind in ('METAL', 'OPTIX', 'CUDA', 'HIP', 'ONEAPI'):
        try:
            prefs.compute_device_type = kind; prefs.get_devices()
            devs = [d for d in prefs.devices if d.type == kind]
            if devs:
                for d in prefs.devices: d.use = d.type == kind
                c.device = 'GPU'; print('DEVICE', kind, [d.name for d in devs]); break
        except Exception:
            pass
if c.device == 'CPU': print('DEVICE CPU (no GPU found; expect long final renders)')

if A.suncheck:
    for o in list(bpy.data.objects): bpy.data.objects.remove(o)
    cd = bpy.data.cameras.new('chk'); cd.lens = 200
    cam = bpy.data.objects.new('chk', cd); col.objects.link(cam); sc.camera = cam
    cam.rotation_euler = to_sun.to_track_quat('-Z', 'Y').to_euler()
    c.samples = 4; c.use_denoising = False
    sc.render.resolution_x = sc.render.resolution_y = 64; sc.render.resolution_percentage = 100
    sc.view_settings.view_transform = 'Standard'; sc.view_settings.exposure = -12
    sc.render.filepath = os.path.abspath(A.out); bpy.ops.render.render(write_still=True)
    print('SUNCHECK: the bright spot should be centred in', A.out); sys.exit(0)

sl = bpy.data.lights.new('p2p_sun', 'SUN'); sl.energy = sun_e; sl.angle = math.radians(0.55)
sl.color = tuple(float(x) for x in sun_c)
so = bpy.data.objects.new('p2p_sun', sl); col.objects.link(so); so.rotation_euler = (-to_sun).to_track_quat('-Z', 'Y').to_euler()

for i, w in enumerate(json.loads(sc.get('p2p_windows', '[]'))):
    pl = bpy.data.lights.new('portal%d' % i, 'AREA'); pl.shape = 'RECTANGLE'; pl.size = w['width'] + 0.05; pl.size_y = w['height'] + 0.05
    try: pl.cycles.is_portal = True
    except Exception: pl.is_portal = True
    po = bpy.data.objects.new('portal%d' % i, pl); col.objects.link(po); po.location = w['center']
    face = {'left': (0, math.radians(90), 0), 'right': (0, math.radians(-90), 0), 'front': (math.radians(-90), 0, 0), 'back': (math.radians(90), 0, 0)}[w['wall']]
    po.rotation_euler = face

cd = bpy.data.cameras.new('p2p_cam'); cd.lens = A.lens; cd.sensor_width = 36
cam = bpy.data.objects.new('p2p_cam', cd); col.objects.link(cam); sc.camera = cam
cam.location = V(A.cam); cam.rotation_euler = (V(A.target) - V(A.cam)).to_track_quat('-Z', 'Y').to_euler()
cd.shift_x = A.shift_x; cd.shift_y = A.shift_y
cd.dof.use_dof = A.fstop > 0
if A.fstop > 0:
    cd.dof.aperture_fstop = A.fstop; cd.dof.focus_distance = (V(A.focus or A.target) - V(A.cam)).length

rx, ry = map(int, A.res.lower().split('x'))
if A.preview: rx, ry = rx // 4, ry // 4
c.samples = 64 if A.preview else A.samples
c.use_adaptive_sampling = True; c.adaptive_threshold = 0.05 if A.preview or c.samples <= 200 else 0.006
c.use_denoising = True
try: c.denoiser = 'OPENIMAGEDENOISE'
except Exception: pass
c.max_bounces = 12; c.diffuse_bounces = 6; c.glossy_bounces = 4; c.transmission_bounces = 8; c.transparent_max_bounces = 16
c.sample_clamp_indirect = 3; c.caustics_reflective = False; c.caustics_refractive = False; c.blur_glossy = 1.0
sc.render.resolution_x = rx; sc.render.resolution_y = ry; sc.render.resolution_percentage = 100
if A.border:
    b = list(map(float, A.border.split(',')))
    sc.render.use_border = True; sc.render.use_crop_to_border = True
    sc.render.border_min_x, sc.render.border_min_y, sc.render.border_max_x, sc.render.border_max_y = b[0], 1 - b[3], b[2], 1 - b[1]
vs = sc.view_settings; vs.view_transform = 'AgX'
for lk in (A.look, 'AgX - Medium High Contrast', 'Medium High Contrast', 'AgX - Base Contrast', 'None'):
    try: vs.look = lk; break
    except Exception: pass
vs.exposure = A.exposure
try: vs.use_white_balance = True; vs.white_balance_temperature = A.wb
except Exception as e: print('WB not available:', e)
sc.render.image_settings.file_format = 'PNG'; sc.render.filepath = os.path.abspath(A.out)
bpy.ops.render.render(write_still=True)
print('RENDERED', A.out, '%dx%d' % (rx, ry), c.samples, 'spp')
