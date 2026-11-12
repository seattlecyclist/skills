"""Bake the lit scene into textures and export a GLB for the three.js viewer.

Called by render.py with --mode viewer, after the world, sun, portals and camera are set up, so the
bake sees exactly the light of the still. Per mesh: real mesh from the evaluated one, a fresh smart UV
projection, then two bakes. Albedo is DIFFUSE colour at 1 sample at full resolution. Irradiance is
DIFFUSE direct + indirect at `spp` samples at half resolution, blurred by about 1.2 cm in world units
to hide the noise, upsampled and multiplied into the albedo. Translucent, glass and emissive
materials bake COMBINED instead. Each texture is saved with the scene's view transform (AgX, look,
exposure, white balance), so the texels are display-referred and match the stills; the viewer shows
them unlit.

Objects matched by `cutaway` (regexes on names) light the bake but are left out of the export, so
the orbit camera can see in. The world HDRI is baked onto a large sky dome so the windows show the
same view as the stills. Materials are renamed <object>__<family> (matte, metal, sheer, shade,
glass, emit, sky) for the viewer.
"""
import bpy, os, re, math, json, shutil
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = os.path.join(os.path.dirname(HERE), 'viewer')
SHELL = re.compile(r'^(Floor|Ceiling|Wall_\w+|Rug)$')
COMBINED = ('sheer', 'shade', 'glass', 'emit')


def blur(a, sigma):
    r = max(1, int(3 * sigma))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2).astype(np.float32); k /= k.sum()
    p = np.pad(a, ((r, r), (0, 0), (0, 0)), mode='edge')
    a = sum(k[i] * p[i:i + a.shape[0]] for i in range(2 * r + 1))
    p = np.pad(a, ((0, 0), (r, r), (0, 0)), mode='edge')
    return sum(k[i] * p[:, i:i + a.shape[1]] for i in range(2 * r + 1))


def family(o):
    for s in o.material_slots:
        m = s.material
        if not m or not m.node_tree: continue
        kinds = {n.bl_idname for n in m.node_tree.nodes}
        if 'ShaderNodeBsdfTranslucent' in kinds:
            return 'sheer' if 'ShaderNodeBsdfTransparent' in kinds else 'shade'
        for n in m.node_tree.nodes:
            if n.bl_idname != 'ShaderNodeBsdfPrincipled': continue
            g = lambda k: n.inputs[k].default_value if k in n.inputs else 0.0
            if g('Transmission Weight') >= 0.5: return 'glass'
            if g('Emission Strength') > 0 and max(tuple(g('Emission Color'))[:3]) > 0: return 'emit'
            if g('Metallic') >= 0.5: return 'metal'
    return 'matte'


def default_cutaway(cam, target):
    """Walls behind the camera (outward normal facing away from the view), their baseboards and
    windows, the ceiling, and the outside ground."""
    out = [r'^Ceiling$', r'^Outside$']
    d = Vector(target) - Vector(cam)
    normals = {'left': (-1, 0), 'right': (1, 0), 'front': (0, -1), 'back': (0, 1)}
    windows = json.loads(bpy.context.scene.get('p2p_windows', '[]'))
    for wall, (nx, ny) in normals.items():
        if nx * d.x + ny * d.y < 0:
            out += [r'^Wall_%s$' % wall, r'^Base_%s$' % wall]
            out += [r'^Win%d_' % i for i, w in enumerate(windows) if w['wall'] == wall]
    return out


def start_camera(cam, target, lens, shift_y, res):
    """The still's camera in three.js terms: Y up, (x, y, z) -> (x, z, -y), vertical FOV."""
    rx, ry = res
    c, t = Vector(cam), Vector(target)
    d = t - c; h = math.hypot(d.x, d.y)
    pitch = math.atan2(d.z, h) + math.atan(shift_y * 36.0 / lens)
    t = c + Vector((d.x / h * math.cos(pitch), d.y / h * math.cos(pitch), math.sin(pitch))) * d.length
    y_up = lambda v: [round(v.x, 4), round(v.z, 4), round(-v.y, 4)]
    fov = math.degrees(2 * math.atan(36.0 * ry / rx / (2 * lens)))
    return {'position': y_up(c), 'target': y_up(t), 'fov': round(fov, 2)}


def write_config(out_dir, **kw):
    path = os.path.join(out_dir, 'viewer.json')
    cfg = json.load(open(path)) if os.path.exists(path) else {}
    cfg.update(kw)
    json.dump(cfg, open(path, 'w'), indent=1)


def copy_template(name, out_dir):
    shutil.copy(os.path.join(TEMPLATES, name), os.path.join(out_dir, name))


def _bake_target(o, image):
    nodes = []
    for s in o.material_slots:
        m = s.material
        if not m or not m.node_tree: continue
        nt = m.node_tree
        nd = nt.nodes.get('BAKE_TARGET') or nt.nodes.new('ShaderNodeTexImage')
        nd.name = 'BAKE_TARGET'; nd.image = image; nt.nodes.active = nd; nodes.append(nd)
    return nodes


def _select(o):
    vl = bpy.context.view_layer
    for x in bpy.context.selected_objects: x.select_set(False)
    vl.objects.active = o; o.select_set(True)


def _pixels(im, n):
    a = np.empty(n * n * 4, dtype=np.float32); im.pixels.foreach_get(a)
    return a.reshape(n, n, 4)


def _sky_dome(center, env_image, env_rot, env_strength, tex):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=96, ring_count=48, radius=40, location=center)
    sky = bpy.context.active_object; sky.name = 'SkyDome'
    sm = bpy.data.materials.new('skydome')
    try: sm.use_nodes = True
    except Exception: pass
    nt = sm.node_tree
    for n in list(nt.nodes):
        if n.bl_idname != 'ShaderNodeOutputMaterial': nt.nodes.remove(n)
    outn = [n for n in nt.nodes if n.bl_idname == 'ShaderNodeOutputMaterial'][0]
    geo = nt.nodes.new('ShaderNodeNewGeometry')
    sub = nt.nodes.new('ShaderNodeVectorMath'); sub.operation = 'SUBTRACT'; sub.inputs[1].default_value = center
    nt.links.new(geo.outputs['Position'], sub.inputs[0])
    nrm = nt.nodes.new('ShaderNodeVectorMath'); nrm.operation = 'NORMALIZE'; nt.links.new(sub.outputs[0], nrm.inputs[0])
    mp = nt.nodes.new('ShaderNodeMapping'); mp.vector_type = 'VECTOR'; mp.inputs['Rotation'].default_value = (0, 0, env_rot)
    nt.links.new(nrm.outputs[0], mp.inputs['Vector'])
    envn = nt.nodes.new('ShaderNodeTexEnvironment'); envn.image = env_image; nt.links.new(mp.outputs[0], envn.inputs['Vector'])
    em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Strength'].default_value = env_strength
    nt.links.new(envn.outputs['Color'], em.inputs['Color']); nt.links.new(em.outputs[0], outn.inputs['Surface'])
    sky.data.materials.append(sm)
    img = bpy.data.images.new('sky_lit', 4096, 2048, alpha=False, float_buffer=True)
    tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = img; nt.nodes.active = tn
    _select(sky)
    sc = bpy.context.scene; sc.cycles.samples = 4
    bpy.ops.object.bake(type='EMIT', use_clear=True)
    path = os.path.join(tex, 'SkyDome.jpg'); img.save_render(path, scene=sc)
    return sky, path


def bake_viewer(out_dir, name, camera, spp=256, texel=900, cutaway=None, hero=None, hero_gain=2.2, max_res=4096,
                env_image=None, env_rot=0.0, env_strength=1.0):
    sc = bpy.context.scene
    tex = os.path.join(out_dir, 'bake_tmp'); os.makedirs(tex, exist_ok=True)
    drop = [re.compile(r) for r in (cutaway or [])]
    heroes = [re.compile(r) for r in (hero or [])]
    dropped = lambda o: any(r.search(o.name) for r in drop) or not o.visible_camera
    sc.cycles.use_denoising = False; sc.cycles.use_adaptive_sampling = False
    sc.render.bake.margin = 8
    sc.render.image_settings.file_format = 'JPEG'; sc.render.image_settings.quality = 86

    dg = bpy.context.evaluated_depsgraph_get()
    meshes = [o for o in bpy.data.objects if o.type == 'MESH' and o.visible_get()]
    for o in meshes:
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
        o.modifiers.clear(); o.data = me

    baked = {}; fams = {}
    keep = [o for o in meshes if not dropped(o) and len(o.data.polygons)]
    print('BAKE %d meshes (%d cut away), %d spp, %d px/m' % (len(keep), len(meshes) - len(keep), spp, texel), flush=True)
    for idx, o in enumerate(keep):
        try:
            me = o.data; area = sum(p.area for p in me.polygons)
            big = bool(o.get('p2p_hero')) or any(r.search(o.name) for r in heroes)
            if SHELL.match(o.name): res = max_res
            else:
                d = texel * (hero_gain if big else 1.0)
                cap = max_res if big else max_res // 2
                res = min(cap, max(128, int(2 ** round(math.log2(max(1, math.sqrt(area) * d))))))
            for uv in list(me.uv_layers): me.uv_layers.remove(uv)
            me.uv_layers.new(name='bake')
            _select(o)
            bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.01, scale_to_bounds=False)
            bpy.ops.object.mode_set(mode='OBJECT')
            f = fams[o.name] = family(o)
            imA = bpy.data.images.new('%s_alb' % o.name, res, res, alpha=False, float_buffer=True)
            if not _bake_target(o, imA): continue
            if f in COMBINED:
                sc.cycles.samples = spp * 2
                bpy.ops.object.bake(type='COMBINED', pass_filter={'DIRECT', 'INDIRECT', 'DIFFUSE', 'TRANSMISSION', 'EMIT'}, use_clear=True)
            else:
                lres = max(64, res // 2)
                imL = bpy.data.images.new('%s_irr' % o.name, lres, lres, alpha=False, float_buffer=True)
                sc.cycles.samples = 1
                bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'}, use_clear=True)
                _bake_target(o, imL); sc.cycles.samples = spp
                bpy.ops.object.bake(type='DIFFUSE', pass_filter={'DIRECT', 'INDIRECT'}, use_clear=True)
                A = _pixels(imA, res); L = _pixels(imL, lres)[:, :, :3]
                L = blur(L, min(4.0, max(1.3, 0.012 * lres / max(1e-3, math.sqrt(area)))))
                if lres != res:
                    k = res // lres; L = blur(np.repeat(np.repeat(L, k, 0), k, 1), 1.0)
                A[:, :, :3] *= L; A[:, :, 3] = 1.0
                imA.pixels.foreach_set(A.reshape(-1))
                bpy.data.images.remove(imL)
            path = os.path.join(tex, '%s.jpg' % re.sub(r'[^\w.-]', '_', o.name))
            imA.save_render(path, scene=sc)
            baked[o.name] = path
            print('LIT %d/%d %s %s %d px' % (idx + 1, len(keep), o.name, f, res), flush=True)
        except Exception as e:
            print('BAKE FAILED', o.name, e, flush=True)
            if bpy.context.object and bpy.context.object.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')

    floor = bpy.data.objects.get('Floor')
    pts = [floor.matrix_world @ v.co for v in floor.data.vertices] if floor else [o.matrix_world.translation for o in keep]
    center = (sum(p.x for p in pts) / len(pts), sum(p.y for p in pts) / len(pts), 1.0)
    if env_image is not None:
        sky, spath = _sky_dome(center, env_image, env_rot, env_strength, tex)
        baked[sky.name] = spath; fams[sky.name] = 'sky'

    for o in list(bpy.data.objects):
        if o.name not in baked: bpy.data.objects.remove(o)
    lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
    for nm, path in baked.items():
        o = bpy.data.objects[nm]
        if fams[nm] != 'sky':
            for v in o.data.vertices:
                w = o.matrix_world @ v.co; lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
        m = bpy.data.materials.new('%s__%s' % (nm, fams[nm]))
        try: m.use_nodes = True
        except Exception: pass
        b = m.node_tree.nodes.get('Principled BSDF')
        t = m.node_tree.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(path)
        m.node_tree.links.new(t.outputs['Color'], b.inputs['Base Color'])
        o.data.materials.clear(); o.data.materials.append(m)
        for p in o.data.polygons: p.material_index = 0

    glb = os.path.join(out_dir, name + '.glb')
    bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', use_selection=False, export_apply=True,
                              export_image_format='JPEG', export_jpeg_quality=86,
                              export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6,
                              export_cameras=False, export_lights=False, export_yup=True)
    shutil.rmtree(tex, ignore_errors=True)
    write_config(out_dir, glb=os.path.basename(glb), camera=camera, maxDistance=round(max(3.0, (hi - lo).length * 1.2), 2))
    copy_template('index.html', out_dir)
    print('VIEWER %s (%d objects, %.1f MB)' % (glb, len(baked), os.path.getsize(glb) / 1e6), flush=True)
    return glb
