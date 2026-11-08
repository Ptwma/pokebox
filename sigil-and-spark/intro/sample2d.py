# Sigil & Spark — "2D anime, alive" SAMPLE (user 2026-11-01: better 2D, things must MOVE — not monsters flapping in
# place — smooth, visually interesting, like an AAA game trailer).  One 9 s shot sequence at full 24 fps:
#   cut 1  tracking shot over a cel-shaded crimson sea: Cindril races alongside the camera, banking; a flock weaves behind
#   cut 2  hero 3/4: it overtakes the camera, roars — fire burst (2DFX impact sheet) + shake + impact frame
#   cut 3  it climbs into the giant sun, the camera tilts up after it; silhouette, rings, final impact frame
# Look: cel bands (Shader to RGB) on the creatures' real atlas colours, Freestyle ink, banded anime sky, hard sun rings.
# Run in Blender 5.2 after saga_blender.py + saga_pages.py:  exec(sample2d.py); build(); still(0.5); render_bg()
import bpy, math, os, random, subprocess
from mathutils import Vector

S_NAME = 'SAMPLE2D'
FPS = 24; F = 216
S_OUT = os.path.join(SRC, 'intro_render', 'sample2d')
FX_SHEET = os.path.join(SRC, 'intro2d', 'fx_2dfx_impacts', 'impact07.png')
MUSIC = os.path.join(SRC, 'music_cc0', 'saga')

# ------------------------------------------------------------------ materials
def m_flat(name, color, strength=1.0):
    return glow(name, color, strength)

def m_cel(name, lit, shade, mid=None, rim=None):
    """3-band cel paint + an anime rim light on the edge facing away from the camera"""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    nt, N, L = _nodes(m)
    out = N.new('ShaderNodeOutputMaterial')
    dif = N.new('ShaderNodeBsdfDiffuse'); s2r = N.new('ShaderNodeShaderToRGB'); bw = N.new('ShaderNodeRGBToBW')
    ramp = N.new('ShaderNodeValToRGB'); cr = ramp.color_ramp; cr.interpolation = 'CONSTANT'
    cr.elements[0].color = (*shade, 1); cr.elements[1].position = 0.5; cr.elements[1].color = (*lit, 1)
    e = cr.elements.new(0.2); e.color = (*(mid or tuple((a + b) / 2 for a, b in zip(lit, shade))), 1)
    L.new(dif.outputs[0], s2r.inputs[0]); L.new(s2r.outputs[0], bw.inputs[0]); L.new(bw.outputs[0], ramp.inputs[0])
    col = ramp.outputs['Color']
    if rim:
        lw = N.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.25
        st = N.new('ShaderNodeMath'); st.operation = 'GREATER_THAN'; st.inputs[1].default_value = 0.72
        L.new(lw.outputs['Facing'], st.inputs[0])
        mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs['B'].default_value = (*rim, 1)
        L.new(st.outputs[0], mx.inputs['Factor']); L.new(col, mx.inputs['A']); col = mx.outputs['Result']
    em = N.new('ShaderNodeEmission'); L.new(col, em.inputs['Color']); L.new(em.outputs[0], out.inputs['Surface'])
    return m

def m_sea():
    """banded anime sea: two scrolling wave textures → 4 hard colour bands + sun-glitter stripes"""
    m = bpy.data.materials.get('S_Sea') or bpy.data.materials.new('S_Sea')
    nt, N, L = _nodes(m)
    out = N.new('ShaderNodeOutputMaterial')
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping')
    L.new(tc.outputs['Object'], mp.inputs['Vector'])
    d = mp.inputs['Location'].driver_add('default_value', 0).driver; d.expression = 'frame * 0.06'
    w1 = N.new('ShaderNodeTexWave'); w1.inputs['Scale'].default_value = 0.35; w1.inputs['Distortion'].default_value = 6
    w1.inputs['Detail'].default_value = 3; w1.bands_direction = 'Y'
    L.new(mp.outputs['Vector'], w1.inputs['Vector'])
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 0.6; L.new(mp.outputs['Vector'], nz.inputs['Vector'])
    mx = N.new('ShaderNodeMath'); mx.operation = 'MULTIPLY'; L.new(w1.outputs['Fac'], mx.inputs[0]); L.new(nz.outputs['Fac'], mx.inputs[1])
    # distance fade toward the horizon (lighter, warmer)
    cam_d = N.new('ShaderNodeCameraData'); dist = N.new('ShaderNodeMapRange')
    dist.inputs['From Min'].default_value = 10; dist.inputs['From Max'].default_value = 160; dist.inputs['To Max'].default_value = 0.55
    L.new(cam_d.outputs['View Distance'], dist.inputs['Value'])
    ad = N.new('ShaderNodeMath'); ad.operation = 'ADD'; L.new(mx.outputs[0], ad.inputs[0]); L.new(dist.outputs['Result'], ad.inputs[1])
    ramp = N.new('ShaderNodeValToRGB'); cr = ramp.color_ramp; cr.interpolation = 'CONSTANT'
    cols = [(0.0, (0.015, 0.0, 0.004)), (0.42, (0.07, 0.006, 0.01)), (0.62, (0.22, 0.02, 0.02)), (0.86, (0.65, 0.10, 0.05)), (0.97, (1.0, 0.75, 0.5))]
    cr.elements[0].position, cr.elements[0].color = cols[0][0], (*cols[0][1], 1)
    cr.elements[1].position, cr.elements[1].color = cols[1][0], (*cols[1][1], 1)
    for p, c in cols[2:]:
        e = cr.elements.new(min(p, 1.0)); e.color = (*c, 1)
    L.new(ad.outputs[0], ramp.inputs[0])
    em = N.new('ShaderNodeEmission'); L.new(ramp.outputs['Color'], em.inputs['Color']); L.new(em.outputs[0], out.inputs['Surface'])
    return m

def sky_world(sc):
    """banded anime sky: view-direction Z → hard colour bands (no smooth CG gradient)"""
    w = bpy.data.worlds.new('S_Sky'); sc.world = w; w.use_nodes = True
    N, L = w.node_tree.nodes, w.node_tree.links
    for n in list(N): N.remove(n)
    out = N.new('ShaderNodeOutputWorld'); bg = N.new('ShaderNodeBackground')
    tc = N.new('ShaderNodeTexCoord'); sep = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Generated'], sep.inputs[0])
    ramp = N.new('ShaderNodeValToRGB'); cr = ramp.color_ramp; cr.interpolation = 'CONSTANT'
    bands = [(0.0, (0.02, 0.0, 0.004)), (0.497, (1.0, 0.85, 0.65)), (0.505, (0.98, 0.42, 0.14)), (0.515, (0.66, 0.08, 0.04)),
             (0.535, (0.32, 0.02, 0.025)), (0.565, (0.13, 0.008, 0.015)), (0.62, (0.04, 0.0, 0.006))]
    cr.elements[0].position, cr.elements[0].color = bands[0][0], (*bands[0][1], 1)
    cr.elements[1].position, cr.elements[1].color = bands[1][0], (*bands[1][1], 1)
    for p, c in bands[2:]:
        e = cr.elements.new(p); e.color = (*c, 1)
    mr = N.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = -1.0; mr.inputs['From Max'].default_value = 1.0
    L.new(sep.outputs['Z'], mr.inputs['Value']); L.new(mr.outputs['Result'], ramp.inputs[0]); L.new(ramp.outputs['Color'], bg.inputs['Color'])
    L.new(bg.outputs[0], out.inputs['Surface'])

# ------------------------------------------------------------------ actors
def disc(name, r, loc, mat, rot=(math.radians(90), 0, 0)):
    bpy.ops.mesh.primitive_circle_add(vertices=96, radius=r, fill_type='NGON', location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name
    for c in list(o.users_collection): c.objects.unlink(o)
    link(o); o.data.materials.append(mat); return o

def sun(loc, r=9.0):
    """sun disc + 3 hard rings (anime light, not bloom); rings breathe"""
    disc('Sun', r, loc, m_flat('S_SunCore', (1.0, 0.96, 0.85), 3.0))
    rings = []
    for i, (k, c, a) in enumerate([(1.25, (1.0, 0.78, 0.45), 1.6), (1.6, (1.0, 0.55, 0.25), 1.0), (2.1, (0.85, 0.25, 0.10), 0.7)]):
        o = disc(f'SunRing{i}', r * k, Vector(loc) + Vector((0, 0.5 + i * 0.5, 0)), m_flat(f'S_Ring{i}', c, a))
        for f in range(1, F + 1, 24):
            s = 1 + 0.025 * math.sin(f * 0.15 + i)
            kf(o, 'scale', f, (s, s, s))
        rings.append(o)
    return rings

def cloud_card(name, loc, w, h, col, seed):
    """flat painted cloud: a stack of overlapping cel blobs (flattened spheres) facing the camera"""
    rnd = random.Random(seed); out = []
    m = m_cel(f'S_Cloud{seed}', col, tuple(c * 0.55 for c in col), rim=(1.0, 0.85, 0.6))
    for i in range(7):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=20, ring_count=10,
                                             location=(loc[0] + rnd.uniform(-w, w) * 0.5, loc[1] + rnd.uniform(-1, 1), loc[2] + rnd.uniform(0, h) * 0.4))
        o = bpy.context.active_object; o.name = f'{name}_{i}'
        for c in list(o.users_collection): c.objects.unlink(o)
        link(o); o.scale = (rnd.uniform(.25, .45) * w, 0.6, rnd.uniform(.25, .5) * h); o.data.materials.append(m)
        bpy.ops.object.shade_smooth() if False else None
        out.append(o)
    return out

def import_creature(rel, scale=1.0):
    """import + cel paint from the atlas; returns (root, armature, {clip: action}) — actions tracked per import"""
    acts0 = set(bpy.data.actions)
    roots, new = creature_painted_from_atlas(rel, (0, 0, 0), scale)
    acts = {a.name.split('|')[-1].split('.')[0]: a for a in bpy.data.actions if a not in acts0}
    arm = next((o for o in new if o.type == 'ARMATURE'), None)
    root = roots[0]
    if arm and arm.animation_data: arm.animation_data.action = None
    return root, arm, acts

def clip(arm, acts, name, f0, f1, speed=1.0, blend=4):
    """NLA strip of a clip, looped from f0 to f1 (with a short blend-in so clip changes don't pop)"""
    a = acts.get(name)
    if not (arm and a): return
    ad = arm.animation_data or arm.animation_data_create()
    tr = ad.nla_tracks.new(); st = tr.strips.new(f'{name}_{f0}', f0, a)
    ln = (a.frame_range[1] - a.frame_range[0]) / speed
    st.scale = 1.0 / speed; st.repeat = max(1.0, (f1 - f0) / max(ln, 1)); st.blend_in = blend; st.blend_out = blend
    st.extrapolation = 'NOTHING'

def fly_path(name, pts, tilt=None):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.path_duration = F
    sp = cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts) - 1)
    for i, p in enumerate(pts):
        bp = sp.bezier_points[i]; bp.co = p; bp.handle_left_type = bp.handle_right_type = 'AUTO'
        if tilt: bp.tilt = tilt[i]
    o = bpy.data.objects.new(name, cu); link(o); o.hide_render = True
    return o

def follow(obj, path, keys):
    """obj rides the path; keys = [(frame, 0..1 offset)] eased (bezier) — banking comes from the curve tilt"""
    c = obj.constraints.new('FOLLOW_PATH'); c.target = path; c.use_curve_follow = True; c.forward_axis = 'TRACK_NEGATIVE_Y'   # glTF monsters face -Y
    c.use_fixed_location = True
    for f, v in keys:
        c.offset_factor = v; c.keyframe_insert('offset_factor', frame=f)
    return c

def bob(obj, amp=0.15, freq=0.18, seed=0):
    """secondary motion: a soft vertical / roll bob on a parent empty so the path motion never looks rail-locked"""
    for f in range(1, F + 1, 3):
        kf(obj, 'location', f, (0, 0, amp * math.sin(f * freq + seed)), -1)
        kf(obj, 'rotation_euler', f, (0, amp * 0.25 * math.sin(f * freq * 0.7 + seed), 0), -1)

def rig(rel, scale, name):
    root, arm, acts = import_creature(rel, scale)
    holder = bpy.data.objects.new(name, None); link(holder)
    bobber = bpy.data.objects.new(name + '_bob', None); link(bobber); bobber.parent = holder
    root.parent = bobber; root.location = (0, 0, 0); root.rotation_euler = (0, 0, 0)
    return holder, bobber, arm, acts

def fx_sheet_plane(name, loc, size, f0, tint=(1.0, 0.55, 0.25), fps_sheet=64):
    """the 2DFX impact spritesheet (8×8 = 64 frames) on a camera-facing plane, frame index driven by time"""
    img = bpy.data.images.load(FX_SHEET, check_existing=True)
    m = bpy.data.materials.new(name)
    nt, N, L = _nodes(m)
    out = N.new('ShaderNodeOutputMaterial'); tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (0.125, 0.125, 1)
    idx = f'min(63, max(0, floor((frame - {f0}) * {fps_sheet / FPS:.4f})))'
    dx = mp.inputs['Location'].driver_add('default_value', 0).driver; dx.expression = f'({idx} % 8) * 0.125'
    dy = mp.inputs['Location'].driver_add('default_value', 1).driver; dy.expression = f'(7 - floor({idx} / 8)) * 0.125'
    L.new(tc.outputs['UV'], mp.inputs['Vector'])
    tx = N.new('ShaderNodeTexImage'); tx.image = img; tx.extension = 'CLIP'; L.new(mp.outputs['Vector'], tx.inputs['Vector'])
    em = N.new('ShaderNodeEmission'); em.inputs['Strength'].default_value = 4.0
    mul = N.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 1
    mul.inputs['B'].default_value = (*tint, 1)
    L.new(tx.outputs['Color'], mul.inputs['A']); L.new(mul.outputs['Result'], em.inputs['Color'])
    tr = N.new('ShaderNodeBsdfTransparent'); ms = N.new('ShaderNodeMixShader')
    L.new(tx.outputs['Alpha'], ms.inputs[0]); L.new(tr.outputs[0], ms.inputs[1]); L.new(em.outputs[0], ms.inputs[2])
    L.new(ms.outputs[0], out.inputs['Surface'])
    try: m.surface_render_method = 'BLENDED'
    except Exception: pass
    o = plane(name, (size, size), loc, m)
    kf(o, 'scale', f0 - 1, (0, 0, 0)); kf(o, 'scale', f0, (1, 1, 1)); kf(o, 'scale', f0 + int(64 * FPS / fps_sheet), (1, 1, 1))
    kf(o, 'scale', f0 + int(64 * FPS / fps_sheet) + 1, (0, 0, 0))
    o.visible_shadow = False
    return o

def speed_lines_ring(cam, f0, f1, n=70, seed=4, color=(1.0, 0.93, 0.88)):
    """anime focus lines: thin tapered wedges radiating toward the frame centre, parented to the camera at 1 m,
    re-drawn (new random angles / lengths) every 2 frames like hand-drawn speed lines"""
    rnd = random.Random(seed); m = m_flat('S_Speed%d' % seed, color, 0.85)
    objs = []
    me = bpy.data.meshes.new('SpeedWedge')
    me.from_pydata([(-0.003, 0, 0), (0.003, 0, 0), (0, 1, 0)], [], [(0, 1, 2)]); me.materials.append(m)
    for i in range(n):
        o = bpy.data.objects.new(f'Speed{seed}_{i}', me); link(o); o.parent = cam; o.visible_shadow = False
        for f in range(f0, f1, 2):
            a = rnd.uniform(0, 2 * math.pi); r0 = rnd.uniform(1.0, 1.15); ln = rnd.uniform(0.07, 0.18)
            # wedge base just outside the frame edge, tip points inward (only the outer ~25% of the frame)
            p = Vector((math.cos(a) * r0 * 0.62, math.sin(a) * r0 * 0.36, -1.0))
            on = rnd.random() < 0.6
            kf(o, 'location', f, p); kf(o, 'rotation_euler', f, (0, 0, a + math.pi / 2))
            kf(o, 'scale', f, (rnd.uniform(0.3, 0.9), ln, 1) if on else (0, 0, 0))
        kf(o, 'scale', f0 - 1, (0, 0, 0)); kf(o, 'scale', f1, (0, 0, 0))
        try:
            for fc in o.animation_data.action.fcurves:
                for k in fc.keyframe_points: k.interpolation = 'CONSTANT'
        except Exception:
            try:
                for lay in o.animation_data.action.layers:
                    for strip in lay.strips:
                        for cb in strip.channelbags:
                            for fc in cb.fcurves:
                                for k in fc.keyframe_points: k.interpolation = 'CONSTANT'
            except Exception as ex: print('interp', ex)
        objs.append(o)
    return objs

# ------------------------------------------------------------------ compositor: bloom + impact frames + vignette
def comp_sample(sc, invert_keys, vignette=0.6):
    ng = bpy.data.node_groups.new('S_Comp', 'CompositorNodeTree')
    ng.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
    N, L = ng.nodes, ng.links
    rl = N.new('CompositorNodeRLayers'); src = rl.outputs['Image']
    gl = N.new('CompositorNodeGlare')
    for v in ('Bloom', 'Fog Glow'):
        try: gl.inputs['Type'].default_value = v; break
        except Exception: pass
    for nm, v in (('Threshold', 0.92), ('Strength', 0.55), ('Size', 0.55)):
        if nm in gl.inputs: gl.inputs[nm].default_value = v
    L.new(src, gl.inputs['Image']); src = gl.outputs['Image']
    em = N.new('CompositorNodeEllipseMask')
    for nm, v in (('Size', (0.92, 0.85)),):
        try: em.inputs[nm].default_value = v
        except Exception: pass
    bl = N.new('CompositorNodeBlur')
    try: bl.inputs['Size'].default_value = (300, 300)
    except Exception: bl.inputs['Size'].default_value = 300
    L.new(em.outputs['Mask'], bl.inputs['Image'])
    vg = N.new('ShaderNodeMix'); vg.data_type = 'RGBA'; vg.blend_type = 'MULTIPLY'; vg.inputs['Factor'].default_value = vignette
    L.new(src, vg.inputs['A']); L.new(bl.outputs['Image'], vg.inputs['B']); src = vg.outputs['Result']
    iv = N.new('CompositorNodeInvert'); L.new(src, iv.inputs['Color'])
    fac = iv.inputs['Fac'] if 'Fac' in iv.inputs else iv.inputs[0]
    for f, v in invert_keys:
        fac.default_value = v; fac.keyframe_insert('default_value', frame=f)
    src = iv.outputs['Color']
    out = N.new('NodeGroupOutput'); L.new(src, out.inputs[0])
    sc.compositing_node_group = ng; sc.render.use_compositing = True

def no_ink(objs):
    """FX / sun / speed lines must not get Freestyle outlines → put them in a collection the lineset excludes"""
    sc = bpy.context.scene
    col = bpy.data.collections.get('S_NoInk') or bpy.data.collections.new('S_NoInk')
    if col.name not in sc.collection.children: sc.collection.children.link(col)
    for o in objs:
        for c in list(o.users_collection): c.objects.unlink(o)
        col.objects.link(o)
    ls = sc.view_layers[0].freestyle_settings.linesets[0]
    ls.select_by_collection = True; ls.collection = col; ls.collection_negation = 'EXCLUSIVE'

def hero_track(hero, frames):
    """evaluated hero world positions (Follow Path + bob) for hero-relative camera keys"""
    sc = bpy.context.scene; out = {}
    for f in frames:
        sc.frame_set(f); out[f] = hero.matrix_world.translation.copy()
    return out

def cam_follow(c, hp, f0, f1, off0, off1, look_off=(0, 0, 0), step=4, lock_pos_after=None):
    """camera = hero position + an offset that eases off0 → off1; look = hero + look_off (Track-To empty)"""
    tgt = bpy.data.objects.new(c.name + '_Tgt', None); link(tgt)
    tr = c.constraints.new('TRACK_TO'); tr.target = tgt; tr.track_axis = 'TRACK_NEGATIVE_Z'; tr.up_axis = 'UP_Y'
    fs = list(range(f0, f1, step)) + [f1]
    for f in fs:
        t = (f - f0) / max(1, f1 - f0); t = t * t * (3 - 2 * t)
        off = Vector(off0).lerp(Vector(off1), t)
        base = hp[lock_pos_after] if (lock_pos_after and f >= lock_pos_after) else hp[f]
        kf(c, 'location', f, base + off)
        kf(tgt, 'location', f, hp[f] + Vector(look_off))
    return tgt

# ------------------------------------------------------------------ build
def build():
    sc = new_scene(S_NAME, (1600, 900))
    sc.timeline_markers.clear()
    for c in list(sc.collection.children): sc.collection.children.unlink(c)
    sc.frame_start, sc.frame_end = 1, F; sc.render.fps = FPS; sc.frame_step = 1
    sc.eevee.taa_render_samples = 32
    ink_lines(sc, thick=2.6, color=(0.06, 0.02, 0.02))
    sky_world(sc)
    # sea + horizon
    sea = plane('Sea', (600, 600), (0, 150, 0), m_sea())
    rings = sun((0, 160, 8.5), 9.0)
    for i, (x, z, w, h, col) in enumerate([(-45, 16, 40, 7, (0.55, 0.10, 0.07)), (38, 21, 46, 8, (0.42, 0.06, 0.05)),
                                           (-8, 32, 70, 10, (0.20, 0.02, 0.03)), (60, 11, 26, 4, (0.85, 0.30, 0.12))]):
        cloud_card(f'Cloud{i}', (x, 140 + i * 6, z), w, h, col, i + 3)
    # far island silhouettes (parallax)
    m_isl = m_cel('S_Isle', (0.10, 0.012, 0.02), (0.02, 0.0, 0.006), rim=(1.0, 0.45, 0.18))
    for i, (x, y, s) in enumerate([(-55, 120, 9), (-25, 130, 5), (40, 115, 12), (75, 125, 6)]):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1, location=(x, y, 0))
        o = bpy.context.active_object; o.name = f'Isle{i}'
        for c in list(o.users_collection): c.objects.unlink(o)
        link(o); o.scale = (s * 1.8, s, s * 0.9); o.data.materials.append(m_isl)
        tx = bpy.data.textures.new(f'IsleTx{i}', 'CLOUDS'); tx.noise_scale = 0.45
        dm = o.modifiers.new('Crag', 'DISPLACE'); dm.texture = tx; dm.strength = 0.55
        o.modifiers.new('Sub', 'SUBSURF').levels = 1
    # lights: back sun (rim side) + warm key from the camera side
    light('Key', 'SUN', (0, -10, 10), 3.0, (1.0, 0.85, 0.7), look=(0, 10, 0))
    # --- the hero: Cindril (Flying/Dragon), races alongside, overtakes, roars, climbs into the sun
    hero, hbob, harm, hacts = rig('Flying/Dragon', 2.0, 'Hero')
    p = fly_path('HeroPath', [(-40, 6, 2.2), (-14, 4, 2.8), (2, 8, 2.4), (10, 22, 3.2), (12, 38, 6.0), (8, 70, 14.0), (2, 120, 13.0)],
                 tilt=[0.0, -0.35, 0.3, -0.45, 0.0, 0.25, 0.0])
    follow(hero, p, [(1, 0.0), (84, 0.30), (150, 0.50), (216, 0.92)])
    bob(hbob, 0.22, 0.21, 1.0)
    clip(harm, hacts, 'Fast_Flying', 1, 128, 1.15)
    clip(harm, hacts, 'Headbutt', 126, 148, 0.8)
    clip(harm, hacts, 'Fast_Flying', 146, F, 1.3)
    # --- the flock: 6 smaller Sparks weaving on offset paths (different speeds, phases, banking)
    flock = [('Flying/Armabee', 0.9), ('Flying/Glub', 1.0), ('Flying/Pigeon', 1.0), ('Flying/Goleling', 0.9), ('Flying/Hywirl', 0.9), ('Flying/Squidle', 0.9)]
    rnd = random.Random(11)
    for i, (rel, s) in enumerate(flock):
        h, b, a, acts = rig(rel, s, f'Flock{i}')
        dy = 14 + i * 4; dz = 3 + rnd.uniform(-1, 3)
        pts = [(-45 + rnd.uniform(-5, 5), dy, dz), (-15, dy + rnd.uniform(-3, 3), dz + 2), (15, dy + rnd.uniform(-3, 3), dz - 1),
               (45, dy + 6, dz + 4), (60, 60, 14)]
        pp = fly_path(f'FlockPath{i}', pts, tilt=[rnd.uniform(-.5, .5) for _ in pts])
        t0 = rnd.uniform(0.0, 0.1)
        follow(h, pp, [(1, t0), (F, min(1.0, t0 + rnd.uniform(0.75, 0.95)))])
        bob(b, 0.35, 0.25 + i * 0.03, i)
        clip(a, acts, 'Fast_Flying', 1, F, rnd.uniform(1.0, 1.4))
    # --- cameras: all three are hero-relative (computed from the evaluated flight), so the hero is always the subject
    hp = hero_track(hero, range(1, F + 1))
    c1 = cam('Cam1', (0, -8, 3), (0, 0, 3), lens=32)
    cam_follow(c1, hp, 1, 84, (-5.0, -9.5, 0.9), (3.5, -8.0, 0.2), look_off=(1.5, 0, 0.1))
    shake(c1, 1, 84, 0.03, 1)
    c2 = cam('Cam2', (0, 8, 3), (0, 0, 3), lens=26)
    cam_follow(c2, hp, 85, 150, (5.0, 13.0, -0.6), (2.2, 6.0, -1.0), look_off=(0, 0, 0.9))
    c3 = cam('Cam3', (0, -6, 1), (0, 0, 3), lens=24)
    cam_follow(c3, hp, 151, 216, (-2.5, -5.5, -1.8), (-2.0, -4.0, -2.4), look_off=(0, 0, 0.0), lock_pos_after=164)
    for f, c in ((1, c1), (85, c2), (151, c3)):
        mk = sc.timeline_markers.new(f'cut{f}', frame=f); mk.camera = c
    sc.camera = c1
    # shake on the roar: Cam2 rides on top of its keys via a parent jitter empty
    jit = bpy.data.objects.new('Cam2_Jit', None); link(jit); c2.parent = jit
    rj = random.Random(7)
    for f in range(126, 150, 2):
        amp = 0.22 * (1 - (f - 126) / 24)
        kf(jit, 'location', f, (rj.uniform(-amp, amp), rj.uniform(-amp, amp), rj.uniform(-amp, amp)))
    kf(jit, 'location', 125, (0, 0, 0)); kf(jit, 'location', 150, (0, 0, 0))
    # --- FX: focus lines in the tracking shot + the climb; the roar burst at the hero's mouth; embers
    fx = speed_lines_ring(c1, 8, 84, 40, 4) + speed_lines_ring(c3, 158, 214, 45, 5)
    mouth = hp[132] + Vector((0, 0, 1.0))
    burst = fx_sheet_plane('RoarBurst', (0, -2.6, 1.0), 5.0, 130); burst.parent = hero
    tc = burst.constraints.new('TRACK_TO'); tc.target = c2; tc.track_axis = 'TRACK_Z'; tc.up_axis = 'UP_Y'
    burst2 = fx_sheet_plane('RoarBurst2', (0.3, -3.2, 1.2), 3.4, 138, tint=(1.0, 0.25, 0.12)); burst2.parent = hero
    tc = burst2.constraints.new('TRACK_TO'); tc.target = c2; tc.track_axis = 'TRACK_Z'; tc.up_axis = 'UP_Y'
    em = embers(70, tuple(mouth - Vector((5, 5, 2))), tuple(mouth + Vector((5, 8, 5))), 126, 210, color=(1.0, 0.45, 0.12), size=0.04, rise=3.0, seed=21, strength=10)
    no_ink(fx + [burst, burst2] + em + [o for o in sc.objects if o.name.startswith('Sun')])
    comp_sample(sc, [(1, 0), (131, 0), (132, 1), (134, 0), (195, 0), (196, 1), (198, 0)])
    return sc

def still(frac=0.5, res=50, frames=None):
    sc = bpy.data.scenes[S_NAME]; bpy.context.window.scene = sc
    os.makedirs(S_OUT, exist_ok=True); sc.render.resolution_percentage = res
    outs = []
    for f in (frames or [int(F * frac)]):
        sc.frame_set(f); sc.render.filepath = os.path.join(S_OUT, f'still_{f:04d}.png'); bpy.ops.render.render(write_still=True)
        outs.append(sc.render.filepath)
    sc.render.resolution_percentage = 100
    return outs

def render_bg():
    """frames in a background Blender, then a VSE edit with music → sample2d.mp4"""
    blend = os.path.join(S_OUT, 'sample2d.blend'); os.makedirs(os.path.join(S_OUT, 'frames'), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=blend, copy=True)
    music = next((os.path.join(MUSIC, f) for f in os.listdir(MUSIC) if 'action' in f.lower()), None) if os.path.isdir(MUSIC) else None
    py = os.path.join(S_OUT, '_render.py')
    open(py, 'w').write(f'''import bpy, os
sc = bpy.data.scenes["{S_NAME}"]; bpy.context.window.scene = sc
sc.render.image_settings.file_format = "PNG"; sc.render.filepath = r"{os.path.join(S_OUT, 'frames', 'f_')}"
bpy.ops.render.render(animation=True, scene=sc.name)
ed = bpy.data.scenes.new("S_EDIT"); ed.render.resolution_x, ed.render.resolution_y = 1600, 900; ed.render.fps = {FPS}
ed.frame_start, ed.frame_end = 1, {F}
se = ed.sequence_editor_create()
d = r"{os.path.join(S_OUT, 'frames')}"; fs = sorted(f for f in os.listdir(d) if f.endswith(".png"))
coll = getattr(se, "strips", None) or se.sequences
st = coll.new_image("img", os.path.join(d, fs[0]), 1, 1)
for f in fs[1:]: st.elements.append(f)
mus = {music!r}
if mus:
    snd = coll.new_sound("mus", mus, 2, 1)
    try: snd.frame_offset_start = int(24 * 38)
    except Exception: pass
    snd.volume = 0.8
ed.render.image_settings.media_type = "VIDEO"
ed.render.image_settings.file_format = "FFMPEG"; ed.render.ffmpeg.format = "MPEG4"; ed.render.ffmpeg.codec = "H264"
ed.render.ffmpeg.constant_rate_factor = "HIGH"; ed.render.ffmpeg.audio_codec = "AAC"
ed.render.filepath = r"{os.path.join(S_OUT, 'sample2d.mp4')}"
ed.render.use_sequencer = True
bpy.context.window.scene = ed
bpy.ops.render.render(animation=True, scene=ed.name)
open(r"{os.path.join(S_OUT, '_done')}", "w").write("ok")
''')
    p = subprocess.Popen([bpy.app.binary_path, '-b', blend, '--python', py], creationflags=0x08000000,
                         stdout=open(os.path.join(S_OUT, '_render.log'), 'w'), stderr=subprocess.STDOUT)
    return p.pid
