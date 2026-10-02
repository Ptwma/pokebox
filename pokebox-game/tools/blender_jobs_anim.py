# Job animations (jobs.glb): IK-target paths + overlay rotations baked on top of Idle_Neutral — Blender text 'anim_lib'

import bpy, math
from mathutils import Vector, Quaternion, Euler
def fcurves_of(act):
    try: return list(act.fcurves)
    except Exception: pass
    out = []
    for L in act.layers:
        for st in L.strips:
            for cb in st.channelbags: out += list(cb.fcurves)
    return out
def setup(arm, idle):
    ad = arm.animation_data or arm.animation_data_create()
    ad.action = None
    for t in list(ad.nla_tracks): ad.nla_tracks.remove(t)
    base = idle.copy(); base.name = 'JobBase'
    for fc in fcurves_of(base):
        if not any(m.type == 'CYCLES' for m in fc.modifiers): fc.modifiers.new('CYCLES')
    tr = ad.nla_tracks.new(); tr.name = 'base'; s = tr.strips.new('base', 0, base); s.repeat = 1
    s.extrapolation = 'HOLD'
    return base
def empty(name, loc):
    o = bpy.data.objects.get(name)
    if not o: o = bpy.data.objects.new(name, None); bpy.context.scene.collection.objects.link(o); o.empty_display_size = .05
    o.location = loc; o.animation_data_clear(); return o
def ik(arm, side):
    pb = arm.pose.bones['LowerArm.' + side]
    for c in list(pb.constraints): pb.constraints.remove(c)
    t = empty('IK_' + side, (0, 0, 0)); p = empty('POLE_' + side, ((-1 if side == 'R' else 1) * .45, .45, .8))
    c = pb.constraints.new('IK'); c.target = t; c.pole_target = p; c.pole_angle = math.radians(-90 if side == 'R' else -90); c.chain_count = 2
    return t, c
def key_path(o, frames):
    """frames: list of (frame, (x,y,z))"""
    for f, p in frames: o.location = p; o.keyframe_insert('location', frame=f)
    if o.animation_data and o.animation_data.action:
        for fc in fcurves_of(o.animation_data.action):
            for k in fc.keyframe_points: k.interpolation = 'BEZIER'; k.handle_left_type = k.handle_right_type = 'AUTO_CLAMPED'
def overlay(arm, name, keys, n):
    """keys: {bone: [(frame, (rx,ry,rz) degrees)]} added on top of the base (COMBINE)"""
    act = bpy.data.actions.new(name)
    ad = arm.animation_data; ad.action = act
    for b, ks in keys.items():
        pb = arm.pose.bones[b]
        for f, e in ks:
            pb.rotation_quaternion = Euler([math.radians(x) for x in e]).to_quaternion(); pb.keyframe_insert('rotation_quaternion', frame=f)
        pb.rotation_quaternion = (1, 0, 0, 0)
    ad.action = None
    tr = ad.nla_tracks.new(); tr.name = 'ov'; s = tr.strips.new('ov', 0, act); s.blend_type = 'COMBINE'
    s.extrapolation = 'HOLD'
    return tr
def bake(arm, name, n):
    bpy.context.view_layer.objects.active = arm
    for o in bpy.context.selected_objects: o.select_set(False)
    arm.select_set(True); bpy.ops.object.mode_set(mode='POSE'); bpy.ops.pose.select_all(action='SELECT')
    bpy.ops.nla.bake(frame_start=0, frame_end=n, only_selected=False, visual_keying=True, clear_constraints=False, use_current_action=False, bake_types={'POSE'})
    bpy.ops.object.mode_set(mode='OBJECT')
    act = arm.animation_data.action; act.name = name; arm.animation_data.action = None
    return act
