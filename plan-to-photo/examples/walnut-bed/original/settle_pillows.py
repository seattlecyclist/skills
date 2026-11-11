import bpy, sys
from mathutils import Vector
S = sys.argv[sys.argv.index('--') + 1]
bpy.ops.wm.open_mainfile(filepath=S + '/scene_v2.blend')
sc = bpy.context.scene; O = bpy.data.objects
def apply(o, names):
    bpy.context.view_layer.objects.active = o
    for m in list(o.modifiers):
        if m.name in names or m.type in names:
            with bpy.context.temp_override(object=o, active_object=o): bpy.ops.object.modifier_apply(modifier=m.name)
def strip(o, types):
    for m in list(o.modifiers):
        if m.type in types: o.modifiers.remove(m)
def bounds(o):
    vs = [o.matrix_world @ v.co for v in o.data.vertices]
    return [min(v[i] for v in vs) for i in range(3)], [max(v[i] for v in vs) for i in range(3)]
def collide(o, outer=0.004):
    if not any(m.type == 'COLLISION' for m in o.modifiers): o.modifiers.new('Collision', 'COLLISION')
    o.collision.thickness_outer = outer; o.collision.cloth_friction = 60
def settle(objs, frames=45):
    for o in objs:
        m = o.modifiers.new('Cloth', 'CLOTH'); s = m.settings
        s.quality = 8; s.mass = 0.3; s.tension_stiffness = 15; s.compression_stiffness = 15; s.shear_stiffness = 8; s.bending_stiffness = 0.6
        s.air_damping = 3; s.use_pressure = True; s.uniform_pressure_force = 3.0
        c = m.collision_settings; c.distance_min = 0.004; c.collision_quality = 4; c.use_self_collision = False
        m.point_cache.frame_start = 1; m.point_cache.frame_end = frames
    sc.frame_start = 1; sc.frame_end = frames
    for f in range(1, frames + 1): sc.frame_set(f)
    for o in objs:
        apply(o, {'Cloth'})
    sc.frame_set(1)
for n in ('Mattress', 'HB_Lower', 'HB_Top', 'Duvet'): collide(O[n])
pil = [O['PillowL'], O['PillowR']]
for o in pil:
    strip(o, {'SUBSURF'}); apply(o, {'DISPLACE'})
    # make the mesh data single-user and bake the transform in
    o.data = o.data.copy(); o.data.transform(o.matrix_world); o.matrix_world.identity()
    lo, hi = bounds(o)
    o.data.transform(__import__('mathutils').Matrix.Translation((0, 2.172 - hi[1], 0.566 - lo[2])))
settle(pil)
for o in pil:
    collide(o, 0.004)
lum = O['Lumbar']
strip(lum, {'SUBSURF'}); apply(lum, {'DISPLACE'})
lum.data = lum.data.copy(); lum.data.transform(lum.matrix_world); lum.matrix_world.identity()
lo, hi = bounds(lum)
lum.data.transform(__import__('mathutils').Matrix.Translation((0, 0.06, 0.566 - lo[2])))
settle([lum])
for o in pil + [lum]:
    strip(o, {'COLLISION'})
    o.modifiers.new('sub', 'SUBSURF').levels = 1
    for p in o.data.polygons: p.use_smooth = True
for n in ('Mattress', 'HB_Lower', 'HB_Top', 'Duvet'): strip(O[n], {'COLLISION'})
for o in pil + [lum]:
    lo, hi = bounds(o); print(o.name, [round(x, 3) for x in lo], [round(x, 3) for x in hi])
bpy.ops.wm.save_as_mainfile(filepath=S + '/scene.blend'); print('SAVED')
