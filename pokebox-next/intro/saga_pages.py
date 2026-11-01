# Sigil & Spark — "The Saga of the Script": the 16 drawn pages of the intro (intro/SAGA_SCRIPT.md).
# Inside Blender 5.2:
#   exec(open(SRC+r"\tools\saga_blender.py").read()); exec(open(SRC+r"\tools\saga_pages.py").read())
#   build_page(5); still(5)              # one page, one test frame
#   build_all(); save_blend()            # then render_bg() renders every page in a background Blender
#   assemble()                           # VSE: pages + narration + music → intro_render/saga_intro.mp4
# Look: painterly compositor (Kuwahara) + parchment grain multiply + bloom + grade + vignette, Freestyle ink lines,
# cel-band watercolour materials, gold glyphs that WRITE themselves (curve bevel factor), embers, volumetric fog.
import bpy, math, os, random, json
from mathutils import Vector

FPS = 24
AUD = os.path.join(SRC, 'audio', 'saga')
MUS = os.path.join(SRC, 'music_cc0', 'saga')
VO = {}   # id -> seconds (filled from the wavs)
GAP = {4: 1.6, 6: 1.6, 9: 1.8, 12: 1.6, 14: 1.6}

def vo_secs(i):
    if not VO:
        import wave
        for k in range(1, 17):
            f = os.path.join(AUD, 'vo_saga_%02d.wav' % k)
            with wave.open(f) as w: VO[k] = w.getnframes() / w.getframerate()
    return VO[i]

def page_frames(i):
    """page length = its narration + a breath (+ 5 s of title on the last page)"""
    s = 1.0 + vo_secs(i) + GAP.get(i, 1.0) + (5.0 if i == 16 else 0.0)
    return int(round(s * FPS))

# ------------------------------------------------------------------ paper + painterly compositor
def paper_image(name='SagaPaper', w=1920, h=1080, seed=3):
    """procedural parchment (numpy): low-frequency stains, fibres, darker burnt edges; values ~0.6–1.0 so it multiplies"""
    img = bpy.data.images.get(name)
    if img: return img
    import numpy as np
    rng = np.random.default_rng(seed)
    def octave(sc):
        g = rng.random((h // sc + 2, w // sc + 2))
        yi = np.linspace(0, g.shape[0] - 1.001, h); xi = np.linspace(0, g.shape[1] - 1.001, w)
        y0 = yi.astype(int); x0 = xi.astype(int); fy = (yi - y0)[:, None]; fx = (xi - x0)[None, :]
        fy = fy * fy * (3 - 2 * fy); fx = fx * fx * (3 - 2 * fx)
        a = g[y0][:, x0]; b = g[y0][:, x0 + 1]; c = g[y0 + 1][:, x0]; d = g[y0 + 1][:, x0 + 1]
        return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy
    n = octave(240) * .5 + octave(90) * .25 + octave(30) * .15 + octave(6) * .1
    fib = octave(2) * .5 + octave(3) * .5
    yy, xx = np.mgrid[0:h, 0:w]; ex = np.abs(xx / w - .5) * 2; ey = np.abs(yy / h - .5) * 2
    edge = np.clip((np.maximum(ex, ey) - .72) / .28, 0, 1) ** 1.6
    v = 0.93 - (n - .5) * .22 - (fib - .5) * .06 - edge * .32
    col = np.stack([v * 1.0, v * 0.93, v * 0.80, np.ones_like(v)], -1).astype(np.float32)
    img = bpy.data.images.new(name, w, h, alpha=True, float_buffer=True)
    img.pixels.foreach_set(col[::-1].ravel()); img.pack()
    return img

def comp_paint(sc, kuwa=5, paper=0.85, bloom=0.8, grade=(1.0, 1.0, 1.0), sat=1.1, vignette=0.55):
    ng = bpy.data.node_groups.new('Comp_' + sc.name, 'CompositorNodeTree')
    ng.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
    N, L = ng.nodes, ng.links
    rl = N.new('CompositorNodeRLayers'); rl.scene = sc
    ku = N.new('CompositorNodeKuwahara'); ku.inputs['Size'].default_value = kuwa
    try: ku.inputs['Type'].default_value = 'Anisotropic'
    except Exception: pass
    L.new(rl.outputs['Image'], ku.inputs['Image'])
    pi = N.new('CompositorNodeImage'); pi.image = paper_image()
    mul = N.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'
    mul.inputs['Factor'].default_value = paper
    L.new(ku.outputs['Image'], mul.inputs['A']); L.new(pi.outputs['Image'], mul.inputs['B'])
    gl = N.new('CompositorNodeGlare')
    for v in ('Bloom', 'Fog Glow'):
        try: gl.inputs['Type'].default_value = v; break
        except Exception: pass
    for nm, v in (('Threshold', 0.75), ('Strength', bloom), ('Size', 0.7)):
        if nm in gl.inputs: gl.inputs[nm].default_value = v
    L.new(mul.outputs['Result'], gl.inputs['Image'])
    hs = N.new('CompositorNodeHueSat'); hs.inputs['Saturation'].default_value = sat
    L.new(gl.outputs['Image'], hs.inputs['Image'])
    cb = N.new('CompositorNodeColorBalance')
    try:
        g = [i for i in cb.inputs if i.name == 'Gain' and i.type == 'RGBA']
        if g: g[0].default_value = (*grade, 1)
    except Exception: pass
    L.new(hs.outputs['Image'], cb.inputs['Image'])
    # vignette: ellipse mask, blurred, multiply
    em = N.new('CompositorNodeEllipseMask')
    try: em.inputs['Size'].default_value = (0.92, 0.85)
    except Exception: pass
    bl = N.new('CompositorNodeBlur'); bl.inputs['Size'].default_value = (260, 260) if bl.inputs['Size'].type == 'VECTOR' else 260
    L.new(em.outputs['Mask'], bl.inputs['Image'])
    vg = N.new('ShaderNodeMix'); vg.data_type = 'RGBA'; vg.blend_type = 'MULTIPLY'; vg.inputs['Factor'].default_value = vignette
    L.new(cb.outputs['Image'], vg.inputs['A']); L.new(bl.outputs['Image'], vg.inputs['B'])
    out = N.new('NodeGroupOutput'); L.new(vg.outputs['Result'], out.inputs[0])
    sc.compositing_node_group = ng; sc.render.use_compositing = True
    return ng

# ------------------------------------------------------------------ animation helpers
def kf(obj, path, frame, value, index=-1):
    if index >= 0: getattr(obj, path)[index] = value
    else: setattr(obj, path, value)
    obj.keyframe_insert(path, index=index, frame=frame)

def kfs(obj, path, keys, index=-1):
    for f, v in keys: kf(obj, path, f, v, index)

def ease(obj):
    ad = obj.animation_data
    if ad and ad.action:
        try:
            for fc in ad.action.fcurves:
                for k in fc.keyframe_points: k.interpolation = 'BEZIER'
        except Exception: pass

def glow(name, color, strength=8.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    nt, N, L = _nodes(m)
    out = N.new('ShaderNodeOutputMaterial'); em = N.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (*color, 1); em.inputs['Strength'].default_value = strength
    L.new(em.outputs[0], out.inputs['Surface'])
    return m

def glow_key(mat, keys):
    """animate a glow material's strength: [(frame, strength)]"""
    em = next(n for n in mat.node_tree.nodes if n.type == 'EMISSION')
    for f, v in keys:
        em.inputs['Strength'].default_value = v; em.inputs['Strength'].keyframe_insert('default_value', frame=f)

def write_on(curve_obj, f0, f1):
    """the stroke draws itself: bevel factor end 0 → 1"""
    cu = curve_obj.data; cu.bevel_factor_mapping_end = 'SPLINE'
    cu.bevel_factor_end = 0.0; cu.keyframe_insert('bevel_factor_end', frame=f0)
    cu.bevel_factor_end = 1.0; cu.keyframe_insert('bevel_factor_end', frame=f1)

def big_glyph(name, seed, center, scale, mat, depth=0.01, rot=(0, 0, 0)):
    o = glyph(name, seed, (0, 0, 0), scale, mat, depth=depth, segs=6)
    o.location = center; o.rotation_euler = rot
    return o

def sphere(name, r, loc, mat):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=24, ring_count=12)
    o = bpy.context.active_object; o.name = name
    for c in list(o.users_collection): c.objects.unlink(o)
    link(o); o.data.materials.append(mat); bpy.ops.object.shade_smooth() if False else None
    return o

def embers(n, box_min, box_max, f0, f1, color=(1.0, 0.45, 0.12), size=0.006, rise=0.6, seed=1, strength=14):
    """floating sparks: small glowing spheres drifting up and fading (cheap, fully keyframed)"""
    rnd = random.Random(seed); m = glow(f'M_Ember_{seed}', color, strength); out = []
    for i in range(n):
        p = Vector([rnd.uniform(a, b) for a, b in zip(box_min, box_max)])
        o = sphere(f'Ember{seed}_{i}', size * rnd.uniform(.5, 1.5), p, m)
        s = f0 + rnd.randint(0, max(1, (f1 - f0) // 2)); e = min(f1, s + rnd.randint(30, 90))
        kf(o, 'location', s, p); kf(o, 'location', e, p + Vector((rnd.uniform(-.2, .2), rnd.uniform(-.2, .2), rise * rnd.uniform(.5, 1.2))))
        kf(o, 'scale', s - 1, (0, 0, 0)); kf(o, 'scale', s, (1, 1, 1)); kf(o, 'scale', e, (0, 0, 0))
        out.append(o)
    return out

def world_fog(sc, density=0.0, color=(0.6, 0.6, 0.65), keys=None):
    w = sc.world.copy(); sc.world = w
    N, L = w.node_tree.nodes, w.node_tree.links
    out = next(n for n in N if n.type == 'OUTPUT_WORLD')
    pv = N.new('ShaderNodeVolumePrincipled'); pv.inputs['Color'].default_value = (*color, 1)
    pv.inputs['Density'].default_value = density
    try: pv.inputs['Absorption Color'].default_value = (*color, 1)   # no black absorption: fog reads as pale mist, not night
    except Exception: pass
    L.new(pv.outputs[0], out.inputs['Volume'])
    for f, v in (keys or []):
        pv.inputs['Density'].default_value = v; pv.inputs['Density'].keyframe_insert('default_value', frame=f)
    return pv

def world_color(sc, color, strength=1.0):
    w = sc.world.copy(); sc.world = w
    bg = w.node_tree.nodes.get('Background'); bg.inputs[0].default_value = (*color, 1); bg.inputs[1].default_value = strength

def cam_move(c, keys, look_keys=None):
    """keys: [(frame, loc)], look target via a Track-To empty"""
    tgt = bpy.data.objects.new(c.name + '_Tgt', None); link(tgt)
    tr = c.constraints.new('TRACK_TO'); tr.target = tgt; tr.track_axis = 'TRACK_NEGATIVE_Z'; tr.up_axis = 'UP_Y'
    for f, p in keys: kf(c, 'location', f, Vector(p))
    for f, p in (look_keys or [(keys[0][0], (0, 0, 0))]): kf(tgt, 'location', f, Vector(p))
    return tgt

def shake(obj, f0, f1, amp=0.01, seed=0):
    rnd = random.Random(seed); base = obj.location.copy()
    for f in range(f0, f1, 2): kf(obj, 'location', f, base + Vector((rnd.uniform(-amp, amp), rnd.uniform(-amp, amp), rnd.uniform(0, amp))))
    kf(obj, 'location', f1, base)

def text3d(name, body, loc, size, mat, font=r"C:\Windows\Fonts\georgiab.ttf", extrude=0.01):
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = body; cu.size = size; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'
    cu.extrude = extrude
    if os.path.exists(font):
        try: cu.font = bpy.data.fonts.load(font, check_existing=True)
        except Exception: pass
    o = bpy.data.objects.new(name, cu); link(o); o.location = loc; cu.materials.append(mat)
    return o

def play_creature_anim(roots, prefer=('Flying_Idle', 'Idle', 'Fast_Flying', 'Walk'), frames=400):
    """loop the glTF clip on the armature (NLA strip, repeated)"""
    for r in roots:
        if r.type != 'ARMATURE': continue
        acts = [a for a in bpy.data.actions if r.name.split('.')[0].replace('CharacterArmature', '') in a.name or True]
        act = None
        for p in prefer:
            act = next((a for a in bpy.data.actions if a.name.endswith(p) or a.name.split('|')[-1] == p), None)
            if act: break
        if not act: continue
        ad = r.animation_data or r.animation_data_create(); ad.action = None
        tr = ad.nla_tracks.new(); st = tr.strips.new(act.name, 1, act)
        st.repeat = max(1.0, frames / max(1.0, act.frame_range[1] - act.frame_range[0]))

def paint_creature(rel, loc, scale, color, rot_z=0.0, anim=('Flying_Idle', 'Idle')):
    roots, new = creature(rel, loc, scale, color=color, rot_z=rot_z)
    play_creature_anim(roots, anim)
    return roots, new

def inkmat(name='M_InkStroke', color=(0.05, 0.03, 0.025)):
    return glow(name, color, 1.0)

def gold(strength=10): return glow('M_Gold_%d' % strength, (1.0, 0.70, 0.22), strength)

# ------------------------------------------------------------------ the pages
PAGES = {}
def page(i):
    def deco(fn): PAGES[i] = fn; return fn
    return deco

def base(i, kuwa=5, paper=0.85, bloom=0.9, grade=(1, 1, 1), sat=1.15, vignette=0.6):
    sc = new_scene('SAGA_%02d' % i)
    sc.render.fps = FPS; sc.frame_start = 1; sc.frame_end = page_frames(i)
    sc.eevee.taa_render_samples = 32
    comp_paint(sc, kuwa, paper, bloom, grade, sat, vignette)
    return sc, sc.frame_end

def parchment_floor(size=(12, 8), loc=(0, 0, 0), base_col=(0.80, 0.68, 0.48), dark=(0.36, 0.24, 0.13), name='Floor'):
    return plane(name, size, loc, mat_parchment('M_' + name, base_col, dark))

@page(1)
def p01():
    """black; an ink drop falls, blooms on parchment, becomes one burning gold glyph"""
    sc, F = base(1, paper=0.9, bloom=0.8, grade=(1, .95, .85))
    world_color(sc, (0.0, 0.0, 0.0))
    pg = parchment_floor((3, 2), (0, 0, 0), (0.55, 0.45, 0.32), (0.08, 0.05, 0.03))
    key = light('Key', 'SPOT', (0, -0.2, 1.4), 0, (1, .85, .6), look=(0, 0, 0)); key.data.spot_size = 0.9
    kfs(key.data, 'energy', [(1, 0), (40, 0), (70, 60), (F, 40)])
    drop = sphere('Drop', 0.025, (0, 0, 1.2), glow('M_Drop', (0.02, 0.015, 0.02), 1))
    kfs(drop, 'location', [(20, (0, 0, 1.0)), (46, (0, 0, 0.01))])
    kfs(drop, 'scale', [(45, (1, 1, 1.4)), (47, (2.5, 2.5, .05)), (70, (9, 9, .02))])
    g = big_glyph('Glyph', 11, (0, 0, 0.012), 0.32, gold(9), depth=0.012); write_on(g, 70, 70 + 60)
    glow_key(g.data.materials[0], [(70, 4), (130, 18), (F, 10)])
    embers(40, (-.5, -.4, 0), (.5, .4, .1), 110, F, (1, .7, .3), seed=11, rise=.4)
    c = cam('Cam', (0, -0.9, 1.2), (0, 0, 0), 50)
    cam_move(c, [(1, (0, -0.9, 1.25)), (F, (0, -0.55, 0.75))], [(1, (0, 0, 0.3)), (60, (0, 0, 0)), (F, (0, 0, 0))])

@page(2)
def p02():
    """the world written: ink islands on a parchment sea, gold veins of Script running through everything"""
    sc, F = base(2, paper=0.75, bloom=0.9, grade=(1.0, .97, .9))
    world_color(sc, (0.5, 0.42, 0.3), 0.6)
    sea = parchment_floor((40, 26), (0, 0, 0), (0.55, 0.62, 0.62), (0.18, 0.22, 0.26), 'Sea')
    land = mat_paint('M_Land', (0.62, 0.55, 0.36)); grass = mat_paint('M_Grass', (0.36, 0.48, 0.26))
    rnd = random.Random(4)
    for k in range(9):
        p = (rnd.uniform(-12, 12), rnd.uniform(-6, 9), 0)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1, location=p)
        o = bpy.context.active_object; o.name = f'Isle{k}'
        for cc in list(o.users_collection): cc.objects.unlink(o)
        link(o); s = rnd.uniform(1.2, 3.2); o.scale = (s * rnd.uniform(.8, 1.5), s, s * rnd.uniform(.25, .5))
        tex = bpy.data.textures.new(f'IsleN{k}', 'CLOUDS'); tex.noise_scale = .6
        d = o.modifiers.new('D', 'DISPLACE'); d.texture = tex; d.strength = .5
        o.data.materials.append(grass if k % 2 else land)
    gm = gold(9)
    for k in range(18):
        g = big_glyph(f'Vein{k}', 200 + k, (rnd.uniform(-12, 12), rnd.uniform(-6, 9), 0.6), rnd.uniform(1.0, 2.6), gm, depth=0.03)
        write_on(g, 10 + k * 12, 10 + k * 12 + 50)
    sun = light('Sun', 'SUN', (5, -5, 9), 3.5, (1, .9, .75), look=(0, 0, 0)); sun.data.use_shadow = True
    c = cam('Cam', (-14, -16, 9), (0, 0, 0), 32)
    cam_move(c, [(1, (-14, -16, 9)), (F, (10, -9, 6))], [(1, (-4, 0, 0)), (F, (6, 4, 0))])

@page(3)
def p03():
    """close on a page of glyphs; two of them twitch and blink open as glowing eyes"""
    sc, F = base(3, kuwa=4, paper=0.9, bloom=1.3, grade=(1, .95, .85))
    world_color(sc, (0.02, 0.015, 0.012))
    parchment_floor((2.4, 1.4))
    ink = inkmat()
    rnd = random.Random(7)
    for k in range(60):
        big_glyph(f'G{k}', 300 + k, (rnd.uniform(-1.1, 1.1), rnd.uniform(-.6, .6), 0.003), rnd.uniform(.05, .11), ink, depth=0.004)
    eye = glow('M_Eye', (1.0, 0.62, 0.15), 22)
    for side in (-1, 1):
        e = sphere(f'Eye{side}', 0.035, (side * 0.09, 0.02, 0.01), eye)
        kfs(e, 'scale', [(1, (1.6, 0.02, 0.2)), (int(F * .45), (1.6, 0.02, 0.2)), (int(F * .5), (1.6, 1.0, 0.4)),
                         (int(F * .62), (1.6, 1.0, 0.4)), (int(F * .64), (1.6, 0.05, 0.2)), (int(F * .68), (1.6, 1.0, 0.4))])
    l = light('Candle', 'POINT', (0.4, -0.3, 0.4), 25, (1, .65, .35))
    kfs(l.data, 'energy', [(f, 22 + 6 * math.sin(f * .7)) for f in range(1, F, 3)])
    c = cam('Cam', (0, -0.55, 0.45), (0, 0, 0), 50)
    cam_move(c, [(1, (0.2, -0.6, 0.55)), (F, (0, -0.28, 0.22))], [(1, (0.05, 0, 0)), (F, (0, 0.02, 0))])

@page(4)
def p04():
    """watercolour Sparks rise out of the paper in a burst of colour, circling"""
    sc, F = base(4, kuwa=6, paper=0.7, bloom=1.0, grade=(1, 1, 1), sat=1.35)
    world_color(sc, (0.85, 0.72, 0.5), 0.8)
    parchment_floor((30, 20))
    cast = [('Flying/Dragon', (0.95, 0.42, 0.16)), ('Flying/Glub', (0.25, 0.55, 0.95)), ('Flying/Armabee', (0.98, 0.82, 0.18)),
            ('Blob/Mushnub', (0.45, 0.75, 0.35)), ('Flying/Ghost', (0.75, 0.55, 0.95))]
    for k, (rel, col) in enumerate(cast):
        a = k / len(cast) * 2 * math.pi; r = 0.75
        roots, _ = paint_creature(rel, (r * math.cos(a), r * math.sin(a), -0.4), 0.13, col, rot_z=a + math.pi)
        for ro in roots:
            kfs(ro, 'location', [(1 + k * 6, (r * math.cos(a), r * math.sin(a), -0.35)),
                                 (40 + k * 6, (r * math.cos(a + .6), r * math.sin(a + .6), 0.35 + .1 * k)),
                                 (F, (r * 1.1 * math.cos(a + 2.2), r * 1.1 * math.sin(a + 2.2), 0.45 + .1 * k))])
            kfs(ro, 'rotation_euler', [(1, a + math.pi), (F, a + math.pi + 1.6)], index=2)
    embers(120, (-1.2, -1.2, 0), (1.2, 1.2, .2), 1, F, (1, .8, .4), seed=4, rise=1.2, size=.008)
    sun = light('Sun', 'SUN', (3, -4, 6), 3.5, (1, .92, .8), look=(0, 0, 0)); sun.data.use_shadow = False
    c = cam('Cam', (0, -3.2, 1.1), (0, 0, 0.3), 35)
    cam_move(c, [(1, (0, -2.6, 2.2)), (F, (0.8, -2.0, 1.8))], [(1, (0, 0, 0.0)), (F, (0, 0, 0.4))])

@page(5)
def p05():
    """THE BOOK: candle-lit leather Codex, three empty sockets on its sigil; it shudders, bursts open, pages storm"""
    sc, F = base(5, kuwa=5, paper=0.65, bloom=1.1, grade=(1.05, .95, .85), sat=1.2)
    world_color(sc, (0.01, 0.008, 0.008))
    desk = plane('Desk', (6, 5), (0, 0, -0.001), mat_parchment('M_Desk5', (0.30, 0.18, 0.10), (0.06, 0.03, 0.02)))
    root, hinge, socks = codex((-0.21, 0, 0), open_deg=0.0)
    for o in root.children_recursive: pass
    o_ = int(F * .55)
    kfs(hinge, 'rotation_euler', [(1, 0), (o_, 0), (o_ + 14, -math.radians(170)), (F, -math.radians(178))], index=1)
    shake(root, int(F * .25), o_, 0.006, seed=5)
    # pages storming out
    pm = mat_paint('M_LoosePage', (0.92, 0.85, 0.66), grain=.2); rnd = random.Random(55)
    for k in range(26):
        pg = plane(f'Leaf{k}', (0.07, 0.10), (0, 0, 0.13), pm)
        t0 = o_ + 4 + rnd.randint(0, 30)
        kf(pg, 'scale', t0 - 1, (0, 0, 0)); kf(pg, 'scale', t0, (1, 1, 1))
        kf(pg, 'location', t0, (0, 0, 0.14))
        kf(pg, 'location', min(F, t0 + 70), (rnd.uniform(-1.0, 0.6), rnd.uniform(0.0, 1.2), rnd.uniform(.3, 0.9)))
        kf(pg, 'rotation_euler', t0, (0, 0, 0))
        kf(pg, 'rotation_euler', min(F, t0 + 70), (rnd.uniform(-6, 6), rnd.uniform(-6, 6), rnd.uniform(-3, 3)))
    embers(80, (-.6, -.5, .05), (.6, .5, .3), o_, F, (1, .75, .3), seed=5, rise=1.0)
    cnd = light('Candle', 'POINT', (0.5, -0.35, 0.35), 45, (1, .6, .3), 0.05)
    kfs(cnd.data, 'energy', [(f, 40 + 10 * math.sin(f * .9) + 6 * math.sin(f * 2.3)) for f in range(1, F, 2)])
    burst = light('Burst', 'POINT', (0, 0, 0.4), 0, (1, .75, .35), 0.3)
    kfs(burst.data, 'energy', [(o_ - 1, 0), (o_ + 4, 400), (o_ + 40, 60), (F, 40)])
    light('Rim', 'POINT', (-0.7, 0.7, 0.6), 15, (0.3, 0.4, 1.0), 0.3)
    c = cam('Cam', (0.9, -0.85, 0.7), (0, 0, 0.05), 45)
    cam_move(c, [(1, (1.1, -1.0, 0.85)), (o_, (0.75, -0.7, 0.55)), (F, (0.35, -0.95, 1.2))],
             [(1, (0, 0, 0.05)), (o_, (0, 0, 0.08)), (F, (0, 0.1, 0.3))])

@page(6)
def p06():
    """an open page; a gold line writes a Spark's outline; one socket ignites"""
    sc, F = base(6, kuwa=4, paper=0.85, bloom=1.3, grade=(1.05, .97, .85))
    world_color(sc, (0.02, 0.015, 0.012))
    parchment_floor((1.6, 1.0), (0, 0, 0), (0.88, 0.80, 0.60), (0.40, 0.28, 0.16))
    gm = gold(12)
    # the Spark outline: a dragon silhouette traced as a closed gold curve (from the mesh's top view hull)
    roots, new = creature('Flying/Dragon', (0, 0, -2), 0.18, color=(0.9, .4, .15))
    mesh = next(o for o in new if o.type == 'MESH')
    pts = [mesh.matrix_world @ v.co for v in mesh.data.vertices]
    for o in new: bpy.data.objects.remove(o, do_unlink=True)
    import math as _m
    hull = []
    for k in range(48):     # radial max hull, front view (x, z)
        a = k / 48 * 2 * _m.pi; best = 0
        for p in pts:
            ang = _m.atan2(p.z + 2 - .2, p.x)
            if abs((ang - a + _m.pi) % (2 * _m.pi) - _m.pi) < .07: best = max(best, Vector((p.x, p.z + 2 - .2)).length)
        hull.append((best * _m.cos(a), best * _m.sin(a)))
    cu = bpy.data.curves.new('Outline', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 0.004
    sp = cu.splines.new('POLY'); sp.points.add(len(hull)); sp.use_cyclic_u = False
    for k, (x, y) in enumerate(hull + hull[:1]): sp.points[k].co = (x * 1.4, y * 1.4, 0.004, 1)
    ol = bpy.data.objects.new('Outline', cu); link(ol); cu.materials.append(gm); write_on(ol, 10, int(F * .6))
    glow_key(gm, [(10, 6), (int(F * .6), 16), (F, 10)])
    sock = sphere('Socket', 0.05, (0.62, 0.36, 0.01), glow('M_Sock6', (1, .75, .3), 0))
    sock.scale = (1, 1, .3)
    glow_key(sock.data.materials[0], [(int(F * .6), 0), (int(F * .66), 40), (F, 18)])
    embers(50, (-.6, -.4, 0), (.6, .4, .1), int(F * .6), F, (1, .8, .4), seed=6, rise=.5)
    light('Candle', 'POINT', (0.5, -0.4, 0.5), 30, (1, .7, .4))
    c = cam('Cam', (0, -0.9, 1.0), (0, 0, 0), 45)
    cam_move(c, [(1, (0.1, -0.75, 0.95)), (F, (0, -0.45, 0.7))], [(1, (0, 0, 0)), (F, (0.05, 0.05, 0))])

def town(sc, warm=True, n=26, seed=9):
    """a painted harbour town: houses with roofs along a curve, lanterns, a few boats"""
    rnd = random.Random(seed)
    wall = mat_paint('M_Wall' + ('W' if warm else 'N'), (0.86, 0.78, 0.62) if warm else (0.28, 0.24, 0.30))
    roof = mat_paint('M_Roof' + ('W' if warm else 'N'), (0.62, 0.22, 0.14) if warm else (0.16, 0.10, 0.12))
    lamp = glow('M_Lamp' + ('W' if warm else 'N'), (1.0, 0.7, 0.3), 12)
    lamps = []
    for k in range(n):
        a = -1.2 + k / n * 2.4; R = 6 + rnd.uniform(-.6, .6) + (k % 3) * .9
        x, y = R * math.sin(a), R * math.cos(a) - 4
        h = rnd.uniform(.6, 1.2); w = rnd.uniform(.5, .8)
        hs = cube(f'House{k}', (w, w * .9, h), (x, y, h / 2), wall)
        hs.rotation_euler[2] = -a
        bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=w * .82, depth=h * .7, location=(x, y, h + h * .35))
        rf = bpy.context.active_object; rf.name = f'Roof{k}'
        for cc in list(rf.users_collection): cc.objects.unlink(rf)
        link(rf); rf.rotation_euler[2] = -a + math.pi / 4; rf.data.materials.append(roof)
        if k % 2 == 0:
            lp = sphere(f'Lamp{k}', 0.05, (x * .93, y * .93 + .3, .5), lamp); lamps.append(lp)
    hull = mat_paint('M_Hull', (0.45, 0.28, 0.16)); sail = mat_paint('M_Sail', (0.95, 0.92, 0.84))
    for k in range(4):
        x, y = rnd.uniform(-3, 3), rnd.uniform(-1.5, 1.5)
        cube(f'Boat{k}', (.8, .25, .15), (x, y, .07), hull)
    return lamps

@page(7)
def p07():
    """a thousand years of peace: warm painted harbour, lanterns, Sparks over the roofs"""
    sc, F = base(7, kuwa=7, paper=0.65, bloom=1.0, grade=(1.08, .98, .85), sat=1.3)
    world_color(sc, (0.95, 0.70, 0.45), 1.0)
    plane('Water', (40, 30), (0, 0, 0), mat_paint('M_WaterW', (0.30, 0.52, 0.62)))
    town(sc, True)
    for k, (rel, col) in enumerate([('Flying/Glub', (.3, .6, .95)), ('Flying/Armabee', (.98, .8, .2))]):
        roots, _ = paint_creature(rel, (-1 + k * 2, 2.5, 2.2), 0.12, col)
        for ro in roots: kfs(ro, 'location', [(1, (-2 + k * 2, 2.5, 2.2)), (F, (0 + k * 2, 2.8, 2.5))])
    sun = light('Sun', 'SUN', (-6, 4, 3), 4.0, (1, .75, .45), look=(0, 0, 0)); sun.data.use_shadow = True
    c = cam('Cam', (-6, -6, 2.4), (0, 2, 0.6), 32)
    cam_move(c, [(1, (-6, -6.5, 2.4)), (F, (-2.5, -7, 2.8))], [(1, (-1, 2, .6)), (F, (1.5, 2, .6))])

@page(8)
def p08():
    """the Surge: night, red Script cracks open under the town, a storm of Spark silhouettes, embers"""
    sc, F = base(8, kuwa=6, paper=0.6, bloom=1.4, grade=(1.1, .8, .75), sat=1.25)
    world_color(sc, (0.05, 0.03, 0.05), 1.0)
    plane('Water', (40, 30), (0, 0, 0), mat_paint('M_WaterN', (0.08, 0.10, 0.16)))
    lamps = town(sc, False)
    red = glow('M_RedScript', (1.0, 0.12, 0.05), 0); rnd = random.Random(8)
    for k in range(22):
        g = big_glyph(f'Crack{k}', 800 + k, (rnd.uniform(-6, 6), rnd.uniform(-1, 4), 0.02), rnd.uniform(1, 3), red, depth=0.04)
        write_on(g, 10 + k * 5, 40 + k * 5)
    glow_key(red, [(1, 0), (20, 12), (int(F * .7), 30), (F, 22)])
    dark = (0.05, 0.03, 0.06)
    for k in range(10):
        roots, _ = paint_creature(random.choice(['Flying/Dragon', 'Flying/Ghost', 'Flying/Pigeon', 'Flying/Squidle']),
                                  (rnd.uniform(-5, 5), rnd.uniform(1, 5), rnd.uniform(2, 4)), 0.1, dark, rot_z=rnd.uniform(0, 6))
        for ro in roots:
            p = ro.location.copy()
            kfs(ro, 'location', [(1, p), (F, p + Vector((rnd.uniform(-3, 3), rnd.uniform(-2, 2), rnd.uniform(-1, 1.5))))])
            kfs(ro, 'rotation_euler', [(1, ro.rotation_euler[2]), (F, ro.rotation_euler[2] + rnd.uniform(-4, 4))], index=2)
    embers(160, (-6, -1, 0), (6, 5, 1), 1, F, (1, .35, .1), seed=8, rise=3, size=.03)
    world_fog(sc, 0.0, (0.6, 0.15, 0.1), [(1, 0.0), (F, 0.05)])
    r = light('Under', 'POINT', (0, 2, -0.5), 0, (1, .2, .1), 2)
    kfs(r.data, 'energy', [(1, 0), (int(F * .5), 3000), (F, 6000)])
    c = cam('Cam', (-6, -7, 2.0), (0, 2, 0.6), 30)
    cam_move(c, [(1, (-5, -7, 2.0)), (F, (-1, -5, 1.4))], [(1, (0, 2, 1)), (F, (1, 2, 1.6))])
    shake(c, int(F * .6), F, 0.03, seed=8)

@page(9)
def p09():
    """a great ink wave swallows the town; red ink bleeds across the page and soaks away"""
    sc, F = base(9, kuwa=7, paper=0.7, bloom=1.0, grade=(1.0, .85, .82), sat=1.1)
    world_color(sc, (0.06, 0.04, 0.05))
    plane('Water', (40, 30), (0, 0, 0), mat_paint('M_WaterN9', (0.08, 0.10, 0.16)))
    town(sc, False, seed=10)
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=5, depth=24, location=(0, 14, 0))
    wv = bpy.context.active_object; wv.name = 'Wave'
    for cc in list(wv.users_collection): cc.objects.unlink(wv)
    link(wv); wv.rotation_euler = (0, math.pi / 2, 0); wv.scale = (1, 1, 1)
    wv.data.materials.append(mat_paint('M_WaveInk', (0.10, 0.14, 0.22), grain=.6))
    kfs(wv, 'location', [(1, (0, 16, -1)), (int(F * .45), (0, 2, 1.5)), (int(F * .7), (0, -6, 0)), (F, (0, -8, -6))])
    bleed = plane('Bleed', (30, 20), (0, -2, 3), glow('M_Bleed', (0.55, 0.0, 0.02), 1.0))
    kfs(bleed, 'scale', [(int(F * .55), (0, 0, 0)), (int(F * .75), (1, 1, 1)), (F, (1.2, 1.2, 1.2))])
    kfs(bleed, 'location', [(int(F * .75), (0, -2, 3)), (F, (0, -2, -1))])
    light('Moon', 'SUN', (3, -4, 6), 1.2, (0.6, 0.7, 1.0), look=(0, 0, 0))
    c = cam('Cam', (0, -9, 3.0), (0, 2, 1), 30)
    cam_move(c, [(1, (0, -9, 3.0)), (F, (0, -11, 5.0))], [(1, (0, 2, 1)), (F, (0, 0, 0))])
    shake(c, int(F * .35), int(F * .75), 0.05, seed=9)

@page(10)
def p10():
    """grey dawn sea; only a long shadow on wet sand (no figure); a white thread drifts out of the water"""
    sc, F = base(10, kuwa=7, paper=0.8, bloom=0.8, grade=(.92, .95, 1.0), sat=0.55)
    world_color(sc, (0.55, 0.57, 0.6), 0.9)
    plane('Sand', (30, 20), (0, -4, 0), mat_paint('M_Sand', (0.55, 0.52, 0.48)))
    plane('SeaG', (30, 20), (0, 12, 0.01), mat_paint('M_SeaG', (0.38, 0.42, 0.46)))
    sh = plane('Shadow', (0.5, 5.0), (0.3, -2.0, 0.012), glow('M_Shadow', (0.08, 0.08, 0.1), 1.0))
    sh.rotation_euler[2] = 0.25
    kfs(sh, 'scale', [(1, (1, 0.9, 1)), (F, (1, 1.1, 1))])
    cu = bpy.data.curves.new('Thread', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 0.01
    sp = cu.splines.new('BEZIER'); sp.bezier_points.add(4)
    for k in range(5):
        bp = sp.bezier_points[k]; bp.co = (k * 0.8 - 1.5, 3 + k * .6, 0.05 + .4 * math.sin(k)); bp.handle_left_type = bp.handle_right_type = 'AUTO'
    th = bpy.data.objects.new('Thread', cu); link(th); cu.materials.append(glow('M_Thread', (1, 1, 1), 6)); write_on(th, 20, F)
    world_fog(sc, 0.03, (0.8, 0.82, 0.86))
    light('Dawn', 'SUN', (-2, 8, 1.2), 2.5, (0.85, 0.85, 0.95), look=(0, 0, 0))
    c = cam('Cam', (0, -6, 1.6), (0, 2, 0), 35)
    cam_move(c, [(1, (0, -6, 1.6)), (F, (0.6, -4.5, 1.2))], [(1, (0, 2, 0.2)), (F, (0.4, 3, 0.4))])

@page(11)
def p11():
    """white masks around the page edge; white ink spreads inward and devours the drawings"""
    sc, F = base(11, kuwa=5, paper=0.85, bloom=0.9, grade=(1, 1, 1.05), sat=0.8)
    world_color(sc, (0.02, 0.02, 0.025))
    parchment_floor((3.2, 1.8))
    ink = inkmat(); rnd = random.Random(11)
    for k in range(70):
        big_glyph(f'G{k}', 1100 + k, (rnd.uniform(-1.4, 1.4), rnd.uniform(-.8, .8), 0.003), rnd.uniform(.05, .12), ink, depth=0.004)
    white = mat_paint('M_Mask', (0.95, 0.95, 0.97), shadow=(0.55, 0.56, 0.62)); hole = glow('M_Hole', (0, 0, 0), 1)
    for k in range(9):
        a = k / 9 * 2 * math.pi; p = (1.25 * math.cos(a), .72 * math.sin(a), 0.06)
        m = sphere(f'Mask{k}', 0.12, p, white); m.scale = (0.8, 1.0, 0.35)
        for s in (-1, 1): e = sphere(f'MaskEye{k}{s}', 0.022, (p[0] + s * .04, p[1] + .02, .1), hole); e.scale = (1.4, .6, .4)
        kf(m, 'scale', int(F * .1) + k * 4 - 1, (0, 0, 0)); kf(m, 'scale', int(F * .1) + k * 4 + 6, (0.8, 1.0, 0.35))
    wd = sphere('WhiteTide', 1.0, (0, 0, 0.01), glow('M_WhiteTide', (0.96, 0.96, 0.98), 1.6)); wd.scale = (0, 0, 0)
    kfs(wd, 'scale', [(int(F * .55), (0, 0, 0)), (F, (2.2, 1.4, 0.01))])
    light('Cold', 'POINT', (0, -0.5, 1.2), 40, (0.8, 0.85, 1.0), 0.5)
    c = cam('Cam', (0, -1.0, 1.9), (0, 0, 0), 40)
    cam_move(c, [(1, (0, -1.2, 2.0)), (F, (0, -0.6, 1.4))], [(1, (0, 0, 0)), (F, (0, 0, 0))])

@page(12)
def p12():
    """the Blanking: a colourful Spark turns grey from the tail up; lanterns go white one by one"""
    sc, F = base(12, kuwa=6, paper=0.7, bloom=1.0, grade=(.95, .95, 1.0), sat=1.1)
    world_color(sc, (0.08, 0.07, 0.1))
    plane('Ground', (20, 14), (0, 0, 0), mat_paint('M_Ground12', (0.25, 0.22, 0.24)))
    roots, new = paint_creature('Flying/Dragon', (0, 0, 0.8), 0.35, (0.95, 0.42, 0.16), rot_z=math.radians(-20))
    grey = mat_paint('M_Greyed', (0.62, 0.62, 0.64))
    meshes = [o for o in new if o.type == 'MESH']
    # grey wash rising: a second, grey copy revealed by a rising boolean-free trick (scale from the bottom)
    for m in meshes:
        g = m.copy(); g.data = m.data.copy(); link(g); g.data.materials.clear(); g.data.materials.append(grey)
        g.modifiers.clear(); g.parent = m.parent
        if m.parent: g.matrix_parent_inverse = m.matrix_parent_inverse.copy()
        g.scale = m.scale * 1.01
        kfs(g, 'scale', [(int(F * .2), m.scale * 0.0), (int(F * .7), m.scale * 1.01)])
    lamp = glow('M_Lamp12', (1.0, 0.7, 0.3), 14); wl = glow('M_LampWhite', (0.95, 0.95, 1.0), 4)
    for k in range(10):
        lp = sphere(f'Lamp{k}', 0.06, (-3 + k * .65, 2.5, 0.9), lamp)
        t = int(F * .5) + k * 6
        kf(lp, 'scale', t, (1, 1, 1)); kf(lp, 'scale', t + 4, (0, 0, 0))
        wlp = sphere(f'LampW{k}', 0.06, (-3 + k * .65, 2.5, 0.9), wl); kf(wlp, 'scale', t, (0, 0, 0)); kf(wlp, 'scale', t + 4, (1, 1, 1))
    light('Key', 'SUN', (3, -4, 5), 2.5, (0.85, 0.85, 1.0), look=(0, 0, 0))
    c = cam('Cam', (0, -3.5, 1.4), (0, 0, 0.9), 35)
    cam_move(c, [(1, (0.6, -3.5, 1.4)), (F, (-0.4, -2.6, 1.1))], [(1, (0, 0, 0.9)), (F, (0, 0.5, 1.0))])

def codex_row(nlit, x, name):
    root, hinge, socks = codex((x - 0.21, 0, 0), open_deg=0.0, name=name)
    for k in range(nlit): light_socket(socks[k])
    return root, hinge, socks

@page(13)
def p13():
    """three Codices on an altar glowing 1 · 2 · 3 sockets in candle light"""
    sc, F = base(13, kuwa=5, paper=0.65, bloom=1.2, grade=(1.05, .97, .88), sat=1.2)
    world_color(sc, (0.015, 0.012, 0.012))
    plane('Altar', (5, 3), (0, 0, -0.001), mat_paint('M_Stone', (0.35, 0.32, 0.30)))
    for k in range(3):
        root, hinge, socks = codex_row(k + 1, (k - 1) * 0.65, f'Codex{k}')
        kfs(hinge, 'rotation_euler', [(1 + k * 20, 0), (30 + k * 20, -math.radians(25))], index=1)
    for k in range(5):
        x = -1.1 + k * .55
        cube(f'Candle{k}', (.05, .05, .25), (x, .55, .125), mat_paint('M_Wax', (0.92, 0.88, 0.75)))
        fl = sphere(f'Flame{k}', 0.02, (x, .55, .27), glow('M_Flame', (1, .65, .25), 20)); fl.scale = (1, 1, 2)
        l = light(f'CL{k}', 'POINT', (x, .5, .35), 12, (1, .65, .35), 0.05)
        kfs(l.data, 'energy', [(f, 10 + 4 * math.sin(f * .8 + k)) for f in range(1, F, 3)])
    embers(40, (-1.2, -.3, .1), (1.2, .6, .5), 1, F, (1, .8, .4), seed=13, rise=.4, size=.004)
    c = cam('Cam', (0, -1.6, 0.9), (0, 0, 0.1), 40)
    cam_move(c, [(1, (-0.8, -1.5, 0.8)), (F, (0.8, -1.4, 0.9))], [(1, (-0.3, 0, 0.1)), (F, (0.3, 0, 0.1))])

@page(14)
def p14():
    """a fourth book. It opens. Nothing. A cold draft blows the candle out"""
    sc, F = base(14, kuwa=5, paper=0.7, bloom=1.0, grade=(.9, .93, 1.0), sat=0.9)
    world_color(sc, (0.01, 0.01, 0.015))
    plane('Altar', (4, 3), (0, 0, -0.001), mat_paint('M_Stone14', (0.28, 0.27, 0.28)))
    root, hinge, socks = codex((-0.21, 0, 0), name='Blank')
    kfs(hinge, 'rotation_euler', [(10, 0), (40, -math.radians(175))], index=1)
    fl = sphere('Flame', 0.025, (0.5, .3, .3), glow('M_Flame14', (1, .65, .25), 20)); fl.scale = (1, 1, 2)
    cube('Candle', (.06, .06, .28), (0.5, .3, .14), mat_paint('M_Wax14', (0.9, 0.86, 0.75)))
    l = light('CL', 'POINT', (0.5, .25, .4), 40, (1, .65, .35), 0.05)
    out = int(F * .7)
    kfs(fl, 'scale', [(out - 6, (1, 1, 2)), (out - 3, (1.4, .4, 1.4)), (out, (0, 0, 0))])
    kfs(l.data, 'energy', [(out - 6, 40), (out, 0)])
    light('Cold', 'POINT', (-0.6, -0.5, 0.8), 6, (0.5, 0.6, 1.0), 0.5)
    c = cam('Cam', (0.2, -0.8, 0.75), (0, 0, 0.05), 45)
    cam_move(c, [(1, (0.3, -0.9, 0.8)), (F, (0.05, -0.55, 0.6))], [(1, (0, 0, 0.05)), (F, (0, 0, 0.1))])

@page(15)
def p15():
    """fog; white sails glide out of it; the harbour lanterns go white in a wave; silence"""
    sc, F = base(15, kuwa=7, paper=0.7, bloom=1.1, grade=(.9, .93, 1.0), sat=0.7)
    world_color(sc, (0.12, 0.13, 0.16), 1.0)
    plane('Water', (60, 40), (0, 0, 0), mat_paint('M_Water15', (0.12, 0.15, 0.2)))
    sail = mat_paint('M_WhiteSail', (0.97, 0.97, 1.0), shadow=(0.6, 0.62, 0.7)); hullm = mat_paint('M_Hull15', (0.85, 0.85, 0.88))
    for k in range(3):
        x0 = -10 + k * 5; y0 = 14 + k * 3
        h = cube(f'Ship{k}', (3.0, 0.8, 0.6), (x0, y0, 0.3), hullm)
        for s in range(2):
            bpy.ops.mesh.primitive_cone_add(vertices=3, radius1=1.2, depth=3.2, location=(x0 - .6 + s * 1.2, y0, 2.1))
            sl = bpy.context.active_object; sl.name = f'Sail{k}{s}'
            for cc in list(sl.users_collection): cc.objects.unlink(sl)
            link(sl); sl.scale = (1, .12, 1); sl.data.materials.append(sail); sl.parent = h
            sl.location = (-.6 + s * 1.2, 0, 1.8)
        kfs(h, 'location', [(1, (x0, y0, .3)), (F, (x0 + 6, y0 - 9, .3))])
    lamps = []
    lamp = glow('M_Lamp15', (1.0, 0.7, 0.3), 12); wl = glow('M_Lamp15W', (0.95, 0.95, 1.0), 6)
    for k in range(14):
        x = -7 + k
        a = sphere(f'L{k}', .09, (x, -2, .6), lamp); b = sphere(f'LW{k}', .09, (x, -2, .6), wl)
        t = int(F * .55) + k * 3
        kf(a, 'scale', t, (1, 1, 1)); kf(a, 'scale', t + 3, (0, 0, 0)); kf(b, 'scale', t, (0, 0, 0)); kf(b, 'scale', t + 3, (1, 1, 1))
    world_fog(sc, 0.06, (0.85, 0.87, 0.9))
    light('Moon', 'SUN', (2, 6, 5), 1.5, (0.7, 0.75, 1.0), look=(0, 0, 0))
    c = cam('Cam', (0, -8, 1.6), (0, 6, 2), 32)
    cam_move(c, [(1, (0, -8, 1.6)), (F, (0, -9.5, 1.4))], [(1, (-2, 8, 2)), (F, (1, 6, 1.8))])

@page(16)
def p16():
    """the blank book alone; a drop of blood falls, becomes a burning gold glyph; the first socket ignites; title"""
    sc, F = base(16, kuwa=4, paper=0.7, bloom=1.5, grade=(1.05, .95, .88), sat=1.25)
    world_color(sc, (0.0, 0.0, 0.0))
    plane('Void', (6, 4), (0, 0, -0.001), mat_paint('M_Void', (0.06, 0.05, 0.05)))
    root, hinge, socks = codex((-0.21, 0, 0), open_deg=178, name='First')
    pages = mat_paint('M_OpenPage', (0.9, 0.84, 0.66))
    pg = plane('OpenPage', (0.4, 0.56), (-0.21, 0, 0.122), pages)
    t_hit = int(FPS * 4.0)
    blood = sphere('Blood', 0.012, (-0.2, 0, 0.9), glow('M_Blood', (0.45, 0.0, 0.01), 1.6))
    kfs(blood, 'location', [(int(t_hit * .5), (-0.2, 0, 0.9)), (t_hit, (-0.2, 0, 0.125))])
    kfs(blood, 'scale', [(t_hit, (1, 1, 1.5)), (t_hit + 2, (3, 3, .1)), (t_hit + 10, (5, 5, .05))])
    g = big_glyph('FirstGlyph', 16, (-0.2, 0, 0.126), 0.22, gold(16), depth=0.004); write_on(g, t_hit + 6, t_hit + 40)
    sock = socks[0]
    on = glow('M_FirstSock', (1, .75, .3), 0); sock.data.materials[0] = on
    glow_key(on, [(t_hit + 40, 0), (t_hit + 48, 60), (F, 25)])
    burst = light('Burst', 'POINT', (-0.2, 0, 0.4), 0, (1, .75, .3), 0.3)
    kfs(burst.data, 'energy', [(t_hit + 40, 0), (t_hit + 46, 300), (F, 60)])
    embers(120, (-.6, -.5, .1), (.4, .5, .4), t_hit + 40, F, (1, .78, .35), seed=16, rise=1.2)
    title_t = page_frames(16) - int(FPS * 5.0)
    tt = text3d('Title', 'SIGIL  &  SPARK', (0, 0.15, 0.9), 0.16, gold(10))
    tt.rotation_euler = (math.radians(55), 0, 0)
    kfs(tt, 'scale', [(title_t, (0, 0, 0)), (title_t + 12, (1.08, 1.08, 1.08)), (title_t + 24, (1, 1, 1))])
    c = cam('Cam', (0, -0.9, 1.1), (0, 0, 0.1), 42)
    cam_move(c, [(1, (0.1, -0.6, 0.85)), (t_hit, (0, -0.45, 0.6)), (title_t, (0, -0.5, 0.75)), (F, (0, -1.2, 1.5))],
             [(1, (-0.2, 0, 0.1)), (t_hit, (-0.2, 0, 0.12)), (title_t, (-0.1, 0.05, 0.3)), (F, (0, 0.15, 0.85))])

# ------------------------------------------------------------------ build / render / assemble
def build_page(i):
    PAGES[i](); return bpy.data.scenes['SAGA_%02d' % i]

def build_all():
    for i in sorted(PAGES): build_page(i)
    return [s.name for s in bpy.data.scenes if s.name.startswith('SAGA_')]

def still(i, frac=0.7, res=50):
    sc = bpy.data.scenes['SAGA_%02d' % i]; bpy.context.window.scene = sc
    sc.frame_set(max(1, int(sc.frame_end * frac))); sc.render.resolution_percentage = res
    os.makedirs(OUT, exist_ok=True); sc.render.filepath = os.path.join(OUT, 'still_%02d.png' % i)
    bpy.ops.render.render(write_still=True); sc.render.resolution_percentage = 100
    return sc.render.filepath

def save_blend(path=None):
    path = path or os.path.join(OUT, 'saga.blend')
    bpy.ops.wm.save_as_mainfile(filepath=path, copy=True)
    return path

def render_bg(pages=None, blend=None):
    """render page PNG sequences in a separate background Blender (keeps this one responsive)"""
    import subprocess, sys
    blend = blend or os.path.join(OUT, 'saga.blend')
    exe = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(sys.executable))), 'blender.exe')
    if not os.path.exists(exe): exe = bpy.app.binary_path
    pages = pages or sorted(PAGES)
    procs = []
    script = os.path.join(OUT, '_render_pages.py')
    open(script, 'w').write('import bpy, os, sys\n'
        'pages = [int(x) for x in sys.argv[sys.argv.index("--")+1:]]\n'
        f'OUT = r"{OUT}"\n'
        'for i in pages:\n'
        '    sc = bpy.data.scenes["SAGA_%02d" % i]\n'
        '    d = os.path.join(OUT, "frames", "p%02d" % i); os.makedirs(d, exist_ok=True)\n'
        '    sc.render.filepath = os.path.join(d, "f_"); sc.render.image_settings.file_format = "PNG"\n'
        '    sc.render.use_overwrite = False; sc.render.use_placeholder = True\n'
        '    bpy.ops.render.render(animation=True, scene=sc.name)\n'
        '    open(os.path.join(d, "_done"), "w").write("ok")\n')
    log = open(os.path.join(OUT, '_render_log.txt'), 'w')
    p = subprocess.Popen([exe, '-b', blend, '--python', script, '--'] + [str(x) for x in pages], stdout=log, stderr=subprocess.STDOUT,
                         creationflags=0x08000000 | 0x00004000)   # no window, below-normal priority
    return p.pid

MUSIC = [  # (start page, file, gain)
    (1, 'gregor_quendel_-_cinematic_trailer_music_-_variations_-_05_-_cinematic_suspense_trailer_-_extended_percussion_version.mp3', 0.55),
    (8, 'gregor_quendel_-_cinematic_trailer_music_-_variations_-_03_-_cinematic_orchestral_action_trailer_-_extended_version.mp3', 0.6),
    (13, 'gregor_quendel_-_cinematic_trailer_music_-_20_-_cinematic_sentimental_lullaby_trailer.mp3', 0.6),
    (15, 'gregor_quendel_-_cinematic_trailer_music_-_13_-_cinematic_epic_hybrid_riser.mp3', 0.55),
    (16, 'Production_Intro_Theme.wav', 0.75),
]

def timeline():
    """page start frames on the master timeline (1-frame overlap free, 10-frame crossfades)"""
    t, out = 1, {}
    for i in sorted(PAGES): out[i] = t; t += page_frames(i)
    return out, t

def assemble(out_name='saga_intro.mp4'):
    """VSE: image sequences (crossfaded) + narration + music → H.264 mp4 with AAC audio"""
    starts, end = timeline()
    sc = bpy.data.scenes.get('SAGA_EDIT') or bpy.data.scenes.new('SAGA_EDIT')
    sc.render.fps = FPS; sc.frame_start = 1; sc.frame_end = end
    sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
    ed = sc.sequence_editor or sc.sequence_editor_create()
    strips = ed.strips if hasattr(ed, 'strips') else ed.sequences
    for s in list(strips): strips.remove(s)
    for i, f0 in starts.items():
        d = os.path.join(OUT, 'frames', 'p%02d' % i)
        files = sorted(x for x in os.listdir(d) if x.endswith('.png')) if os.path.isdir(d) else []
        if not files: continue
        st = strips.new_image(f'P{i:02d}', os.path.join(d, files[0]), channel=1 + (i % 2), frame_start=f0)
        for f in files[1:]: st.elements.append(f)
        vo = os.path.join(AUD, 'vo_saga_%02d.wav' % i)
        if os.path.exists(vo): strips.new_sound(f'VO{i:02d}', vo, channel=4, frame_start=f0 + FPS)
    for k, (pg, fn, gain) in enumerate(MUSIC):
        f = os.path.join(MUS, fn)
        if not os.path.exists(f): continue
        f0 = starts[pg]; f1 = starts[MUSIC[k + 1][0]] if k + 1 < len(MUSIC) else end
        m = strips.new_sound(f'MUS{k}', f, channel=5 + (k % 2), frame_start=f0)
        m.frame_final_end = min(m.frame_final_end, f1 + FPS)
        m.volume = gain
    try: sc.render.image_settings.media_type = 'VIDEO'   # Blender 5.x: pick the video media type before FFMPEG
    except Exception: pass
    sc.render.image_settings.file_format = 'FFMPEG'
    sc.render.ffmpeg.format = 'MPEG4'; sc.render.ffmpeg.codec = 'H264'; sc.render.ffmpeg.constant_rate_factor = 'HIGH'
    sc.render.ffmpeg.audio_codec = 'AAC'; sc.render.ffmpeg.audio_bitrate = 192
    sc.render.filepath = os.path.join(OUT, out_name)
    return sc.name, end

# ======================================================================= v2 upgrades (look pass 2)
def glyph(name, seed, center, scale, mat, depth=0.004, segs=5):
    """a Script glyph, calligraphic: 2–4 brush strokes (arcs, hooks, stems, a dot) as Bézier curves whose radius
    tapers like a brush (thin – full – thin). Centred on `center`. Original design."""
    rnd = random.Random(seed)
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = max(depth, scale * 0.045)
    cu.bevel_resolution = 3; cu.resolution_u = 16
    strokes = []
    for s in range(rnd.randint(2, 4)):
        kind = rnd.choice(['arc', 'hook', 'stem', 'arc', 'sweep', 'dot'])
        c0 = Vector((rnd.uniform(-.35, .35), rnd.uniform(-.35, .35), 0))
        if kind == 'arc':
            r = rnd.uniform(.18, .42); a0 = rnd.uniform(0, 6.28); span = rnd.uniform(1.6, 3.6)
            pts = [c0 + Vector((r * math.cos(a0 + span * t), r * math.sin(a0 + span * t), 0)) for t in (0, .33, .66, 1)]
        elif kind == 'hook':
            d = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), 0)).normalized() * rnd.uniform(.4, .7)
            n = Vector((-d.y, d.x, 0)) * rnd.choice([-1, 1]) * .25
            pts = [c0 - d * .5, c0, c0 + d * .45, c0 + d * .45 + n]
        elif kind == 'stem':
            pts = [c0 + Vector((0, -.4, 0)), c0 + Vector((rnd.uniform(-.08, .08), -.1, 0)), c0 + Vector((rnd.uniform(-.1, .1), .2, 0)), c0 + Vector((rnd.uniform(-.15, .15), .45, 0))]
        elif kind == 'sweep':
            pts = [c0 + Vector((-.45, rnd.uniform(-.2, .2), 0)), c0 + Vector((-.1, rnd.uniform(-.35, .35), 0)), c0 + Vector((.15, rnd.uniform(-.35, .35), 0)), c0 + Vector((.45, rnd.uniform(-.2, .2), 0))]
        else:
            pts = [c0 + Vector((0, 0, 0)), c0 + Vector((.03, .02, 0))]
        strokes.append((kind, pts))
    allp = [p for _, ps in strokes for p in ps]
    mid = Vector(((max(p.x for p in allp) + min(p.x for p in allp)) / 2, (max(p.y for p in allp) + min(p.y for p in allp)) / 2, 0))
    for kind, pts in strokes:
        sp = cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts) - 1)
        for k, p in enumerate(pts):
            bp = sp.bezier_points[k]; q = (p - mid) * scale
            bp.co = (center[0] + q.x, center[1] + q.y, center[2]); bp.handle_left_type = bp.handle_right_type = 'AUTO'
            t = k / max(1, len(pts) - 1)
            bp.radius = 1.6 if kind == 'dot' else (0.25 + 1.1 * math.sin(math.pi * min(1, t * 1.15)))
    o = bpy.data.objects.new(name, cu); link(o); cu.materials.append(mat)
    return o

FBX = os.path.join(SRC, 'fbx')
_LIB = {}
def fbx(name):
    """import an FBX of the game's own town kit once (hidden library), return the object to copy"""
    if name in _LIB and _LIB[name].name in bpy.data.objects: return _LIB[name]
    lib = bpy.data.collections.get('SagaLib') or bpy.data.collections.new('SagaLib')
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(FBX, name + '.fbx'))
    new = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
    for o in [o for o in bpy.data.objects if o not in before]:
        for c in list(o.users_collection): c.objects.unlink(o)
        if o.type == 'MESH': lib.objects.link(o)
    o = new[0] if new else None
    if o and len(new) > 1:       # join multi-part kits into one
        for n in new[1:]: n.parent = o
    _LIB[name] = o
    return o

PAINT_DAY = {'Siding': (0.90, 0.84, 0.70), 'Roof': (0.66, 0.24, 0.16), 'Trim': (0.95, 0.93, 0.88), 'Glass': (0.35, 0.50, 0.62),
             'Stone': (0.55, 0.52, 0.48), 'Wood': (0.55, 0.36, 0.20), 'Metal': (0.35, 0.36, 0.40), 'Ground': (0.52, 0.62, 0.34),
             'Grass': (0.46, 0.60, 0.30), 'Rock': (0.52, 0.50, 0.46), 'Sand': (0.86, 0.78, 0.58), 'Water': (0.30, 0.52, 0.62),
             'Snow': (0.95, 0.95, 0.97), 'Mountain': (0.45, 0.50, 0.40), 'Light': (1.0, 0.85, 0.5)}
def repaint(o, night=False, tint=None):
    """swap the kit's PBR material slots for watercolour paint by slot name (M_Roof_Red → Roof ...)"""
    for i, s in enumerate(o.material_slots):
        nm = s.material.name if s.material else 'M_Trim'
        key = next((k for k in PAINT_DAY if k.lower() in nm.lower()), 'Trim')
        col = PAINT_DAY[key]
        if 'Roof' in nm:   # every house its own roof paint (a painter never repeats one colour 20 times)
            pal = [(0.66, 0.24, 0.16), (0.25, 0.38, 0.62), (0.30, 0.50, 0.32), (0.45, 0.30, 0.22), (0.38, 0.40, 0.48), (0.70, 0.45, 0.20)]
            col = pal[sum(map(ord, o.name)) % len(pal)]
        if night:
            if key in ('Glass', 'Light'): s.material = glow('M_WinNight', (1.0, 0.62, 0.25), 9); continue
            col = tuple(c * .32 for c in col); col = (col[0] * .9, col[1] * .85, col[2] * 1.25)
        if tint: col = tuple(a * b for a, b in zip(col, tint))
        s.material = mat_paint(f'MP_{key}_{"N" if night else "D"}_{"%.2f%.2f%.2f" % col}', col)

def place(name, loc, rot_z=0.0, scale=1.0, night=False, tint=None):
    src = fbx(name)
    if not src: return None
    o = src.copy(); o.data = src.data.copy(); link(o)
    o.location = loc; o.rotation_euler = (0, 0, rot_z); o.scale = (scale,) * 3
    repaint(o, night, tint)
    return o

def town2(night=False, trees=0.25, seed=2, tint=None):
    """the real Lumen Harbor layout (town_plan.json) drawn: terrain, mountains, island, our house kits at every
    building spot, lighthouse, breakwaters, boats, painted firs and coast rocks"""
    plan = json.load(open(os.path.join(SRC, 'town_plan.json')))
    for t in ('SM_Ground', 'SM_Mountains', 'SM_Island', 'SM_BreakwaterE', 'SM_BreakwaterW'):
        place(t, (0, 0, 0), night=night, tint=tint)
    wz = plan.get('water', {}).get('z', -1.2)
    plane('Sea', (2400, 2400), (0, 0, wz), mat_paint('MP_Sea_' + ('N' if night else 'D'), (0.10, 0.13, 0.22) if night else (0.30, 0.52, 0.64), grain=.5))
    rnd = random.Random(seed); kits = ['SM_House_Player', 'SM_House_Rival']; k = 0
    fir = mat_paint('MP_Fir_' + ('N' if night else 'D'), (0.10, 0.16, 0.14) if night else (0.22, 0.40, 0.24))
    rock = mat_paint('MP_Rock_' + ('N' if night else 'D'), (0.18, 0.18, 0.22) if night else (0.55, 0.53, 0.48))
    for ob in plan['objects']:
        m = ob['mesh'].split('/')[-1]; p = (ob['x'], ob['y'], ob.get('z', 0)); r = math.radians(ob.get('rot', 0))
        if 'BP_BLD' in m:
            place(kits[k % 2], p, r, 1.0, night, tint); k += 1
        elif m == 'SM_Lab': place('SM_Lab', p, r, 1.0, night, tint)
        elif m in ('SM_Rowboat', 'SM_FishingBoat', 'SM_Sailboat', 'SM_Lighthouse', 'SM_LampPost'):
            place(m, p, r, ob.get('s', 1.0), night, tint)
        elif m.startswith('fir_sapling') and rnd.random() < trees:
            h = rnd.uniform(3, 6)
            bpy.ops.mesh.primitive_cone_add(vertices=7, radius1=h * .28, depth=h, location=(p[0], p[1], p[2] + h / 2))
            c = bpy.context.active_object
            for cc in list(c.users_collection): cc.objects.unlink(c)
            link(c); c.data.materials.append(fir)
        elif m.startswith('coast_rocks') and rnd.random() < .35:
            bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=rnd.uniform(.8, 1.8), location=p)
            c = bpy.context.active_object
            for cc in list(c.users_collection): cc.objects.unlink(c)
            link(c); c.data.materials.append(rock); c.scale = (1, 1, .6)
    return plan

@page(7)
def p07():
    """a thousand years of peace: the real harbour, painted warm at golden hour, Sparks over the roofs"""
    sc, F = base(7, kuwa=6, paper=0.6, bloom=0.9, grade=(1.08, .98, .86), sat=1.3)
    world_color(sc, (0.95, 0.72, 0.48), 1.0)
    town2(False)
    for k, (rel, col) in enumerate([('Flying/Glub', (.3, .6, .95)), ('Flying/Armabee', (.98, .8, .2)), ('Flying/Dragon', (.95, .45, .2))]):
        roots, _ = paint_creature(rel, (-10 + k * 8, 10, 14), 1.2, col)
        for ro in roots: kfs(ro, 'location', [(1, (-14 + k * 9, 6, 14 + k)), (F, (-4 + k * 9, 9, 16 + k))])
    sun = light('Sun', 'SUN', (-60, 40, 25), 4.0, (1, .78, .5), look=(0, 0, 0)); sun.data.use_shadow = True
    c = cam('Cam', (-40, -70, 30), (0, 0, 0), 30); c.data.clip_end = 3000
    cam_move(c, [(1, (-55, -75, 32)), (F, (-20, -80, 28))], [(1, (-5, 5, 2)), (F, (10, 5, 2))])

@page(8)
def p08():
    """the Surge: night over the harbour, red Script cracks under the town, a storm of Spark silhouettes, embers"""
    sc, F = base(8, kuwa=6, paper=0.55, bloom=1.4, grade=(1.1, .82, .78), sat=1.25)
    world_color(sc, (0.04, 0.025, 0.045), 1.0)
    town2(True)
    red = glow('M_RedScript', (1.0, 0.14, 0.05), 0); rnd = random.Random(8)
    for k in range(26):
        g = glyph(f'Crack{k}', 800 + k, (rnd.uniform(-45, 45), rnd.uniform(-25, 30), 1.5), rnd.uniform(6, 16), red, depth=0.25)
        write_on(g, 8 + k * 4, 40 + k * 4)
    glow_key(red, [(1, 0), (20, 10), (int(F * .7), 26), (F, 20)])
    dark = (0.05, 0.03, 0.06)
    for k in range(12):
        roots, _ = paint_creature(rnd.choice(['Flying/Dragon', 'Flying/Ghost', 'Flying/Pigeon', 'Flying/Squidle']),
                                  (rnd.uniform(-35, 35), rnd.uniform(-5, 30), rnd.uniform(12, 30)), 1.0, dark, rot_z=rnd.uniform(0, 6))
        for ro in roots:
            p = ro.location.copy()
            kfs(ro, 'location', [(1, p), (F, p + Vector((rnd.uniform(-15, 15), rnd.uniform(-10, 10), rnd.uniform(-4, 8))))])
    embers(180, (-45, -25, 0), (45, 30, 6), 1, F, (1, .35, .1), seed=8, rise=25, size=.25)
    world_fog(sc, 0.0, (0.7, 0.18, 0.1), [(1, 0.0), (F, 0.006)])
    r = light('Under', 'POINT', (0, 5, -2), 0, (1, .2, .1), 20)
    kfs(r.data, 'energy', [(1, 0), (int(F * .5), 2e6), (F, 4e6)])
    light('Moon', 'SUN', (40, -30, 60), 0.6, (0.5, 0.55, 1.0), look=(0, 0, 0))
    c = cam('Cam', (-40, -70, 30), (0, 0, 0), 30); c.data.clip_end = 3000
    cam_move(c, [(1, (-45, -70, 26)), (F, (-15, -50, 16))], [(1, (0, 5, 4)), (F, (5, 8, 8))])
    shake(c, int(F * .6), F, 0.25, seed=8)

@page(9)
def p09():
    """a great ink wave swallows the town; red ink bleeds across the page"""
    sc, F = base(9, kuwa=7, paper=0.65, bloom=1.0, grade=(1.0, .85, .82), sat=1.1)
    world_color(sc, (0.05, 0.035, 0.05))
    town2(True, trees=0.15)
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=30, depth=260, location=(0, 120, 0))
    wv = bpy.context.active_object; wv.name = 'Wave'
    for cc in list(wv.users_collection): cc.objects.unlink(wv)
    link(wv); wv.rotation_euler = (0, math.pi / 2, 0)
    wv.data.materials.append(mat_paint('M_WaveInk', (0.08, 0.12, 0.22), grain=.6))
    kfs(wv, 'location', [(1, (0, 140, -15)), (int(F * .45), (0, 30, 6)), (int(F * .75), (0, -40, -5)), (F, (0, -60, -40))])
    bleed = plane('Bleed', (300, 200), (0, -20, 25), glow('M_Bleed', (0.55, 0.0, 0.02), 1.0))
    kfs(bleed, 'scale', [(int(F * .55), (0, 0, 0)), (int(F * .78), (1, 1, 1))])
    light('Moon', 'SUN', (30, -40, 60), 1.2, (0.6, 0.7, 1.0), look=(0, 0, 0))
    c = cam('Cam', (0, -90, 30), (0, 10, 5), 28); c.data.clip_end = 3000
    cam_move(c, [(1, (0, -90, 30)), (F, (0, -110, 45))], [(1, (0, 10, 5)), (F, (0, 0, 0))])
    shake(c, int(F * .35), int(F * .75), 0.4, seed=9)

@page(15)
def p15():
    """fog; white sails glide out of it toward the harbour; the lanterns go white in a wave"""
    sc, F = base(15, kuwa=7, paper=0.65, bloom=1.1, grade=(.9, .93, 1.0), sat=0.7)
    world_color(sc, (0.10, 0.11, 0.14), 1.0)
    town2(True, trees=0.15, tint=(.8, .85, 1.0))
    for k in range(3):
        s = place('SM_Sailboat', (-80 + k * 30, 180 + k * 20, -1.2), math.radians(-120), 4.0, False, (1.15, 1.15, 1.2))
        if s: kfs(s, 'location', [(1, (-80 + k * 30, 180 + k * 20, -1.2)), (F, (-50 + k * 30, 90 + k * 15, -1.2))])
    wl = glow('M_Lamp15W', (0.95, 0.95, 1.0), 8); lamp = glow('M_Lamp15', (1.0, 0.7, 0.3), 12)
    for k in range(16):
        x = -40 + k * 5
        a = sphere(f'L{k}', .5, (x, -10, 3), lamp); b = sphere(f'LW{k}', .5, (x, -10, 3), wl)
        t = int(F * .55) + k * 3
        kf(a, 'scale', t, (1, 1, 1)); kf(a, 'scale', t + 3, (0, 0, 0)); kf(b, 'scale', t, (0, 0, 0)); kf(b, 'scale', t + 3, (1, 1, 1))
    world_fog(sc, 0.012, (0.85, 0.87, 0.9))
    light('Moon', 'SUN', (20, 60, 50), 1.5, (0.7, 0.75, 1.0), look=(0, 0, 0))
    c = cam('Cam', (0, -60, 12), (0, 60, 10), 32); c.data.clip_end = 3000
    cam_move(c, [(1, (-10, -60, 12)), (F, (5, -70, 10))], [(1, (-30, 120, 12)), (F, (-10, 80, 8))])

# ======================================================================= look pass 3 (fixes after the first contact sheet)
def mat_blank(name, color, start, end):
    """watercolour paint that is BLANKED from the bottom up between frames start→end (object-space Z threshold)"""
    m = mat_paint(name, color)
    N, L = m.node_tree.nodes, m.node_tree.links
    em = next(n for n in N if n.type == 'EMISSION'); src = em.inputs['Color'].links[0].from_socket
    tc = N.new('ShaderNodeTexCoord'); sep = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Generated'], sep.inputs[0])
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 8; L.new(tc.outputs['Generated'], nz.inputs['Vector'])
    ad = N.new('ShaderNodeMath'); ad.operation = 'MULTIPLY_ADD'; ad.inputs[1].default_value = 0.15
    L.new(nz.outputs['Fac'], ad.inputs[0]); L.new(sep.outputs['Z'], ad.inputs[2])
    th = N.new('ShaderNodeValue'); th.name = 'BlankLevel'
    for f, v in ((start, -0.2), (end, 1.3)):
        th.outputs[0].default_value = v; th.outputs[0].keyframe_insert('default_value', frame=f)
    lt = N.new('ShaderNodeMath'); lt.operation = 'LESS_THAN'; L.new(ad.outputs[0], lt.inputs[0]); L.new(th.outputs[0], lt.inputs[1])
    mix = N.new('ShaderNodeMix'); mix.data_type = 'RGBA'; L.new(lt.outputs[0], mix.inputs['Factor'])
    L.new(src, mix.inputs['A']); mix.inputs['B'].default_value = (0.62, 0.62, 0.64, 1)
    L.new(mix.outputs['Result'], em.inputs['Color'])
    return m

def translucent_glow(name, color, strength=1.0, alpha=0.6):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    nt, N, L = _nodes(m)
    out = N.new('ShaderNodeOutputMaterial'); em = N.new('ShaderNodeEmission'); tr = N.new('ShaderNodeBsdfTransparent')
    mx = N.new('ShaderNodeMixShader'); mx.inputs[0].default_value = alpha
    em.inputs['Color'].default_value = (*color, 1); em.inputs['Strength'].default_value = strength
    L.new(tr.outputs[0], mx.inputs[1]); L.new(em.outputs[0], mx.inputs[2]); L.new(mx.outputs[0], out.inputs['Surface'])
    try: m.surface_render_method = 'BLENDED'
    except Exception: pass
    return m

@page(2)
def p02():
    """the world written: painted islands on a sea of parchment-blue, gold veins of Script running through them"""
    sc, F = base(2, paper=0.75, bloom=0.7, grade=(1.0, .97, .9))
    world_color(sc, (0.78, 0.70, 0.55), 1.0)
    plane('Sea', (400, 300), (0, 0, 0), mat_paint('M_Sea2', (0.42, 0.58, 0.62), grain=.6))
    land = mat_paint('M_Land', (0.70, 0.60, 0.40)); grass = mat_paint('M_Grass', (0.40, 0.55, 0.30)); rock = mat_paint('M_Rock2', (0.55, 0.52, 0.48))
    rnd = random.Random(4)
    for k in range(9):
        p = (rnd.uniform(-14, 14), rnd.uniform(-2, 16), 0)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4, radius=1, location=p)
        o = bpy.context.active_object; o.name = f'Isle{k}'
        for cc in list(o.users_collection): cc.objects.unlink(o)
        link(o); s = rnd.uniform(1.4, 3.4); o.scale = (s * rnd.uniform(.9, 1.6), s, s * rnd.uniform(.35, .7))
        tex = bpy.data.textures.new(f'IsleN{k}', 'CLOUDS'); tex.noise_scale = .7
        d = o.modifiers.new('D', 'DISPLACE'); d.texture = tex; d.strength = .7
        o.data.materials.append([grass, land, rock][k % 3])
    gm = gold(5)
    for k in range(16):
        g = glyph(f'Vein{k}', 200 + k, (rnd.uniform(-14, 14), rnd.uniform(-2, 16), 0.05), rnd.uniform(1.5, 3.2), gm, depth=0.05)
        write_on(g, 10 + k * 14, 10 + k * 14 + 50)
    sun = light('Sun', 'SUN', (5, -5, 9), 3.5, (1, .9, .75), look=(0, 0, 0))
    c = cam('Cam', (-12, -14, 6), (0, 0, 0), 30); c.data.clip_end = 2000
    cam_move(c, [(1, (-12, -16, 7)), (F, (8, -12, 5))], [(1, (-2, 6, 0)), (F, (4, 8, 0))])

@page(3)
def p03():
    sc, F = base(3, kuwa=4, paper=0.9, bloom=0.8, grade=(1, .95, .85))
    world_color(sc, (0.02, 0.015, 0.012))
    parchment_floor((2.4, 1.4)); ink = inkmat(); rnd = random.Random(7)
    for k in range(70):
        glyph(f'G{k}', 300 + k, (rnd.uniform(-1.1, 1.1), rnd.uniform(-.6, .6), 0.003), rnd.uniform(.05, .1), ink, depth=0.003)
    eye = glow('M_Eye', (1.0, 0.62, 0.15), 8)
    for side in (-1, 1):
        e = sphere(f'Eye{side}', 0.016, (side * 0.05, 0.02, 0.006), eye)
        kfs(e, 'scale', [(1, (1.6, 0.02, 0.2)), (int(F * .45), (1.6, 0.02, 0.2)), (int(F * .5), (1.6, 1.0, 0.4)),
                         (int(F * .62), (1.6, 1.0, 0.4)), (int(F * .64), (1.6, 0.05, 0.2)), (int(F * .68), (1.6, 1.0, 0.4))])
    l = light('Candle', 'POINT', (0.4, -0.3, 0.4), 22, (1, .65, .35))
    kfs(l.data, 'energy', [(f, 20 + 5 * math.sin(f * .7)) for f in range(1, F, 3)])
    c = cam('Cam', (0, -0.55, 0.45), (0, 0, 0), 50)
    cam_move(c, [(1, (0.25, -0.7, 0.65)), (F, (0, -0.38, 0.3))], [(1, (0.05, 0, 0)), (F, (0, 0.02, 0))])

@page(4)
def p04():
    sc, F = base(4, kuwa=6, paper=0.7, bloom=0.7, grade=(1, 1, 1), sat=1.35)
    world_color(sc, (0.80, 0.68, 0.48), 1.0)
    parchment_floor((40, 30))
    ink = inkmat(); rnd = random.Random(44)
    for k in range(50): glyph(f'G{k}', 440 + k, (rnd.uniform(-2, 2), rnd.uniform(-1, 2), 0.003), rnd.uniform(.08, .2), ink, depth=0.004)
    cast = [('Flying/Dragon', (0.95, 0.42, 0.16)), ('Flying/Glub', (0.25, 0.55, 0.95)), ('Flying/Armabee', (0.98, 0.82, 0.18)),
            ('Blob/Mushnub', (0.45, 0.75, 0.35)), ('Flying/Ghost', (0.75, 0.55, 0.95))]
    for k, (rel, col) in enumerate(cast):
        x = (k - 2) * 0.55
        roots, _ = paint_creature(rel, (x, 0.3, -0.5), 0.14, col, rot_z=math.radians(rnd.uniform(-25, 25)))
        for ro in roots:
            t = 1 + k * 8
            kfs(ro, 'location', [(t, (x, 0.3, -0.5)), (t + 30, (x, 0.3, 0.25 + 0.08 * (k % 2))), (F, (x * 1.15, 0.2, 0.45 + 0.08 * (k % 2)))])
    embers(120, (-1.5, -.6, 0), (1.5, .9, .2), 1, F, (1, .8, .4), seed=4, rise=1.2, size=.006)
    sun = light('Sun', 'SUN', (3, -4, 6), 3.5, (1, .92, .8), look=(0, 0, 0)); sun.data.use_shadow = False
    c = cam('Cam', (0, -2.6, 0.9), (0, 0.3, 0.3), 35)
    cam_move(c, [(1, (0, -2.6, 0.7)), (F, (0.3, -2.2, 0.8))], [(1, (0, 0.3, 0.1)), (F, (0, 0.3, 0.4))])

@page(5)
def p05():
    sc, F = base(5, kuwa=5, paper=0.65, bloom=0.8, grade=(1.05, .95, .85), sat=1.2)
    world_color(sc, (0.01, 0.008, 0.008))
    plane('Desk', (6, 5), (0, 0, -0.001), mat_parchment('M_Desk5', (0.30, 0.18, 0.10), (0.06, 0.03, 0.02)))
    root, hinge, socks = codex((-0.21, 0, 0), open_deg=0.0)
    o_ = int(F * .55)
    kfs(hinge, 'rotation_euler', [(1, 0), (o_, 0), (o_ + 14, -math.radians(170)), (F, -math.radians(178))], index=1)
    shake(root, int(F * .25), o_, 0.006, seed=5)
    pm = mat_paint('M_LoosePage', (0.92, 0.85, 0.66), grain=.2); rnd = random.Random(55)
    for k in range(30):
        pg = plane(f'Leaf{k}', (0.07, 0.10), (0, 0, 0.13), pm)
        t0 = o_ + 4 + rnd.randint(0, 30)
        kf(pg, 'scale', t0 - 1, (0, 0, 0)); kf(pg, 'scale', t0, (1, 1, 1))
        kf(pg, 'location', t0, (0, 0, 0.14))
        kf(pg, 'location', min(F, t0 + 70), (rnd.uniform(-1.0, 0.4), rnd.uniform(0.1, 1.2), rnd.uniform(.3, 0.9)))
        kf(pg, 'rotation_euler', t0, (0, 0, 0))
        kf(pg, 'rotation_euler', min(F, t0 + 70), (rnd.uniform(-6, 6), rnd.uniform(-6, 6), rnd.uniform(-3, 3)))
    embers(80, (-.6, -.5, .05), (.6, .5, .3), o_, F, (1, .75, .3), seed=5, rise=1.0)
    cnd = light('Candle', 'POINT', (0.5, -0.35, 0.35), 45, (1, .6, .3), 0.05)
    kfs(cnd.data, 'energy', [(f, 40 + 10 * math.sin(f * .9) + 6 * math.sin(f * 2.3)) for f in range(1, F, 2)])
    burst = light('Burst', 'POINT', (0, 0, 0.4), 0, (1, .75, .35), 0.3)
    kfs(burst.data, 'energy', [(o_ - 1, 0), (o_ + 4, 150), (o_ + 40, 40), (F, 30)])
    light('Rim', 'POINT', (-0.7, 0.7, 0.6), 15, (0.3, 0.4, 1.0), 0.3)
    c = cam('Cam', (0.9, -0.85, 0.7), (0, 0, 0.05), 40)
    cam_move(c, [(1, (1.25, -1.15, 0.95)), (o_, (0.95, -0.95, 0.75)), (F, (0.6, -1.4, 1.35))],
             [(1, (0, 0, 0.05)), (o_, (0, 0, 0.08)), (F, (0, 0.2, 0.3))])

@page(6)
def p06():
    """an open page; a ring of gold Script writes itself; a Spark is painted into being inside it; a socket ignites"""
    sc, F = base(6, kuwa=4, paper=0.85, bloom=0.8, grade=(1.05, .97, .85))
    world_color(sc, (0.02, 0.015, 0.012))
    parchment_floor((1.6, 1.0), (0, 0, 0), (0.88, 0.80, 0.60), (0.40, 0.28, 0.16))
    gm = gold(5)
    for k in range(10):
        a = k / 10 * 2 * math.pi
        g = glyph(f'Ring{k}', 600 + k, (0.28 * math.cos(a), 0.28 * math.sin(a), 0.004), 0.07, gm, depth=0.003)
        write_on(g, 8 + k * 6, 30 + k * 6)
    roots, new = paint_creature('Flying/Dragon', (0, 0, 0.05), 0.07, (0.95, 0.42, 0.16))
    for ro in roots: kfs(ro, 'scale', [(int(F * .45), (0, 0, 0)), (int(F * .6), (0.08, 0.08, 0.08)), (F, (0.07, 0.07, 0.07))])
    sock = sphere('Socket', 0.035, (0.55, 0.32, 0.01), glow('M_Sock6', (1, .75, .3), 0)); sock.scale = (1, 1, .3)
    glow_key(sock.data.materials[0], [(int(F * .6), 0), (int(F * .66), 18), (F, 9)])
    embers(50, (-.4, -.3, 0), (.4, .3, .1), int(F * .5), F, (1, .8, .4), seed=6, rise=.4, size=.004)
    light('Candle', 'POINT', (0.5, -0.4, 0.5), 25, (1, .7, .4))
    c = cam('Cam', (0, -0.9, 1.0), (0, 0, 0), 45)
    cam_move(c, [(1, (0.1, -0.85, 0.95)), (F, (0, -0.6, 0.75))], [(1, (0, 0, 0)), (F, (0.05, 0.05, 0.03))])

@page(8)
def p08():
    sc, F = base(8, kuwa=6, paper=0.55, bloom=0.9, grade=(1.1, .85, .8), sat=1.2)
    world_color(sc, (0.05, 0.03, 0.055), 1.0)
    town2(True)
    red = glow('M_RedScript', (1.0, 0.14, 0.05), 0); rnd = random.Random(8)
    for k in range(26):
        g = glyph(f'Crack{k}', 800 + k, (rnd.uniform(-45, 45), rnd.uniform(-25, 30), 1.5), rnd.uniform(6, 16), red, depth=0.25)
        write_on(g, 8 + k * 4, 40 + k * 4)
    glow_key(red, [(1, 0), (20, 5), (int(F * .7), 10), (F, 8)])
    dark = (0.05, 0.03, 0.06)
    for k in range(12):
        roots, _ = paint_creature(rnd.choice(['Flying/Dragon', 'Flying/Ghost', 'Flying/Pigeon', 'Flying/Squidle']),
                                  (rnd.uniform(-35, 35), rnd.uniform(-5, 30), rnd.uniform(12, 30)), 1.0, dark, rot_z=rnd.uniform(0, 6))
        for ro in roots:
            p = ro.location.copy()
            kfs(ro, 'location', [(1, p), (F, p + Vector((rnd.uniform(-15, 15), rnd.uniform(-10, 10), rnd.uniform(-4, 8))))])
    embers(180, (-45, -25, 0), (45, 30, 6), 1, F, (1, .35, .1), seed=8, rise=25, size=.25, strength=8)
    r = light('Under', 'POINT', (0, 5, 3), 0, (1, .2, .1), 20)
    kfs(r.data, 'energy', [(1, 0), (int(F * .5), 2e5), (F, 4e5)])
    light('Moon', 'SUN', (40, -30, 60), 0.8, (0.5, 0.55, 1.0), look=(0, 0, 0))
    c = cam('Cam', (-40, -70, 30), (0, 0, 0), 30); c.data.clip_end = 3000
    cam_move(c, [(1, (-45, -70, 26)), (F, (-15, -50, 16))], [(1, (0, 5, 4)), (F, (5, 8, 8))])
    shake(c, int(F * .6), F, 0.25, seed=8)

@page(9)
def p09():
    sc, F = base(9, kuwa=7, paper=0.65, bloom=0.8, grade=(1.0, .85, .82), sat=1.1)
    world_color(sc, (0.05, 0.035, 0.05))
    town2(True, trees=0.15)
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=30, depth=260, location=(0, 120, 0))
    wv = bpy.context.active_object; wv.name = 'Wave'
    for cc in list(wv.users_collection): cc.objects.unlink(wv)
    link(wv); wv.rotation_euler = (0, math.pi / 2, 0)
    wv.data.materials.append(mat_paint('M_WaveInk', (0.10, 0.16, 0.28), grain=.6))
    kfs(wv, 'location', [(1, (0, 140, -15)), (int(F * .5), (0, 30, 6)), (int(F * .8), (0, -40, -5)), (F, (0, -60, -40))])
    bleed = sphere('Bleed', 1.0, (0, -60, 20), translucent_glow('M_Bleed', (0.6, 0.0, 0.02), 1.2, 0.55))
    kfs(bleed, 'scale', [(int(F * .6), (0, 0, 0)), (F, (30, 0.2, 18))])
    light('Moon', 'SUN', (30, -40, 60), 1.4, (0.6, 0.7, 1.0), look=(0, 0, 0))
    c = cam('Cam', (0, -90, 30), (0, 10, 5), 28); c.data.clip_end = 3000
    cam_move(c, [(1, (0, -90, 30)), (F, (0, -110, 45))], [(1, (0, 10, 5)), (F, (0, 0, 0))])
    shake(c, int(F * .4), int(F * .8), 0.4, seed=9)

@page(10)
def p10():
    sc, F = base(10, kuwa=7, paper=0.8, bloom=0.6, grade=(.92, .95, 1.0), sat=0.55)
    world_color(sc, (0.62, 0.64, 0.68), 1.0)
    plane('Sand', (60, 40), (0, -10, 0), mat_paint('M_Sand', (0.58, 0.55, 0.50)))
    plane('SeaG', (300, 200), (0, 105, 0.01), mat_paint('M_SeaG', (0.40, 0.44, 0.48)))
    me = bpy.data.meshes.new('ShadowM'); import bmesh
    bm = bmesh.new(); vs = [bm.verts.new(v) for v in ((-.12, 0, 0), (.12, 0, 0), (.35, 5, 0), (-.35, 5, 0))]; bm.faces.new(vs); bm.to_mesh(me); bm.free()
    sh = bpy.data.objects.new('Shadow', me); link(sh); sh.location = (0.3, -2.4, 0.012); sh.rotation_euler[2] = 0.25
    me.materials.append(translucent_glow('M_Shadow', (0.05, 0.05, 0.07), 1.0, 0.75))
    kfs(sh, 'scale', [(1, (1, 0.9, 1)), (F, (1, 1.15, 1))])
    cu = bpy.data.curves.new('Thread', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 0.012
    sp = cu.splines.new('BEZIER'); sp.bezier_points.add(5)
    for k in range(6):
        bp = sp.bezier_points[k]; bp.co = (k * 0.7 - 1.8, 4 + k * 1.2, 0.05 + .35 * math.sin(k * 1.3)); bp.handle_left_type = bp.handle_right_type = 'AUTO'
    th = bpy.data.objects.new('Thread', cu); link(th); cu.materials.append(glow('M_Thread', (1, 1, 1), 4)); write_on(th, 20, F)
    light('Dawn', 'SUN', (-2, 8, 1.2), 2.5, (0.85, 0.85, 0.95), look=(0, 0, 0))
    c = cam('Cam', (0, -6, 1.6), (0, 2, 0), 35)
    cam_move(c, [(1, (0, -7, 1.8)), (F, (0.6, -5.5, 1.4))], [(1, (0, 3, 0.2)), (F, (0.4, 4, 0.4))])

@page(11)
def p11():
    sc, F = base(11, kuwa=5, paper=0.85, bloom=0.6, grade=(1, 1, 1.05), sat=0.8)
    world_color(sc, (0.02, 0.02, 0.025))
    parchment_floor((3.2, 1.8)); ink = inkmat(); rnd = random.Random(11)
    for k in range(70):
        glyph(f'G{k}', 1100 + k, (rnd.uniform(-1.4, 1.4), rnd.uniform(-.8, .8), 0.003), rnd.uniform(.05, .12), ink, depth=0.004)
    white = mat_paint('M_Mask', (0.95, 0.95, 0.97), shadow=(0.55, 0.56, 0.62)); hole = glow('M_Hole', (0, 0, 0), 1)
    for k in range(9):
        a = k / 9 * 2 * math.pi; p = (1.15 * math.cos(a), .66 * math.sin(a), 0.06)
        m = sphere(f'Mask{k}', 0.11, p, white)
        for s in (-1, 1):
            e = sphere(f'MaskEye{k}{s}', 0.02, (s * .04 / 0.8, .02, .7), hole); e.parent = m; e.scale = (1.4, .6, .4)
        t = int(F * .1) + k * 4
        kf(m, 'scale', t - 1, (0, 0, 0)); kf(m, 'scale', t + 6, (0.8, 1.0, 0.35))
    wd = sphere('WhiteTide', 1.0, (0, 0, 0.012), glow('M_WhiteTide', (0.96, 0.96, 0.98), 1.4))
    kfs(wd, 'scale', [(int(F * .45), (0, 0, 0)), (F, (0.95, 0.55, 0.005))])
    light('Cold', 'POINT', (0, -0.5, 1.2), 40, (0.8, 0.85, 1.0), 0.5)
    c = cam('Cam', (0, -1.0, 1.9), (0, 0, 0), 40)
    cam_move(c, [(1, (0, -1.3, 2.1)), (F, (0, -0.9, 1.6))], [(1, (0, 0, 0)), (F, (0, 0, 0))])

@page(12)
def p12():
    """the Blanking: a colourful Spark turns grey from the tail up; a row of lanterns goes white one by one"""
    sc, F = base(12, kuwa=6, paper=0.7, bloom=0.7, grade=(.95, .95, 1.0), sat=1.1)
    world_color(sc, (0.08, 0.07, 0.1))
    plane('Ground', (40, 30), (0, 0, 0), mat_paint('M_Ground12', (0.25, 0.22, 0.24)))
    roots, new = creature('Flying/Dragon', (0, 0, 0.9), 0.35, color=(0.95, 0.42, 0.16), rot_z=math.radians(-20))
    play_creature_anim(roots)
    bm_ = mat_blank('M_Blanking', (0.95, 0.42, 0.16), int(F * .2), int(F * .8))
    for o in new:
        if o.type == 'MESH':
            for s in o.material_slots: s.material = bm_
    lamp = glow('M_Lamp12', (1.0, 0.7, 0.3), 8); wl = glow('M_LampWhite', (0.95, 0.95, 1.0), 3)
    for k in range(10):
        p = (-4 + k * .9, 4.5, 1.6)
        lp = sphere(f'Lamp{k}', 0.07, p, lamp); wlp = sphere(f'LampW{k}', 0.07, p, wl)
        t = int(F * .5) + k * 6
        kf(lp, 'scale', t, (1, 1, 1)); kf(lp, 'scale', t + 4, (0, 0, 0)); kf(wlp, 'scale', t, (0, 0, 0)); kf(wlp, 'scale', t + 4, (1, 1, 1))
    light('Key', 'SUN', (3, -4, 5), 2.5, (0.85, 0.85, 1.0), look=(0, 0, 0))
    c = cam('Cam', (0, -3.5, 1.4), (0, 0, 0.9), 35)
    cam_move(c, [(1, (0.6, -3.8, 1.3)), (F, (-0.4, -3.0, 1.1))], [(1, (0, 0, 0.9)), (F, (0, 0.5, 1.0))])

@page(14)
def p14():
    sc, F = base(14, kuwa=5, paper=0.7, bloom=0.7, grade=(.9, .93, 1.0), sat=0.9)
    world_color(sc, (0.01, 0.01, 0.015))
    plane('Altar', (4, 3), (0, 0, -0.001), mat_paint('M_Stone14', (0.28, 0.27, 0.28)))
    root, hinge, socks = codex((-0.21, 0, 0), name='Blank')
    kfs(hinge, 'rotation_euler', [(10, 0), (40, -math.radians(175))], index=1)
    fl = sphere('Flame', 0.025, (0.5, .3, .3), glow('M_Flame14', (1, .65, .25), 12)); fl.scale = (1, 1, 2)
    cube('Candle', (.06, .06, .28), (0.5, .3, .14), mat_paint('M_Wax14', (0.9, 0.86, 0.75)))
    l = light('CL', 'POINT', (0.5, .25, .4), 40, (1, .65, .35), 0.05)
    out = int(F * .7)
    kfs(fl, 'scale', [(out - 6, (1, 1, 2)), (out - 3, (1.4, .4, 1.4)), (out, (0, 0, 0))])
    kfs(l.data, 'energy', [(out - 6, 40), (out, 0)])
    smoke = mat_paint('M_Smoke', (0.6, 0.62, 0.68))
    for k in range(10):
        s = sphere(f'Smoke{k}', 0.012, (0.5, .3, .33), smoke); t = out + k * 3
        kf(s, 'scale', t - 1, (0, 0, 0)); kf(s, 'location', t, (0.5, .3, .33)); kf(s, 'scale', t, (1, 1, 1))
        kf(s, 'location', t + 30, (0.5 + .03 * math.sin(k), .3, .6 + k * .02)); kf(s, 'scale', t + 30, (2.5, 2.5, 2.5))
    light('Cold', 'POINT', (-0.6, -0.5, 0.8), 6, (0.5, 0.6, 1.0), 0.5)
    c = cam('Cam', (0.2, -0.8, 0.75), (0, 0, 0.05), 40)
    cam_move(c, [(1, (0.55, -1.25, 0.95)), (F, (0.35, -1.0, 0.8))], [(1, (0.05, 0, 0.05)), (F, (0.1, 0.05, 0.1))])

@page(15)
def p15():
    sc, F = base(15, kuwa=7, paper=0.65, bloom=0.8, grade=(.95, .97, 1.05), sat=0.75)
    world_color(sc, (0.22, 0.24, 0.30), 1.0)
    town2(True, trees=0.15, tint=(1.2, 1.25, 1.4))
    for k in range(3):
        s = place('SM_Sailboat', (-80 + k * 30, 180 + k * 20, -1.2), math.radians(-120), 4.0, False, (1.15, 1.15, 1.2))
        if s: kfs(s, 'location', [(1, (-80 + k * 30, 180 + k * 20, -1.2)), (F, (-50 + k * 30, 90 + k * 15, -1.2))])
    wl = glow('M_Lamp15W', (0.95, 0.95, 1.0), 5); lamp = glow('M_Lamp15', (1.0, 0.7, 0.3), 8)
    for k in range(16):
        x = -40 + k * 5
        a = sphere(f'L{k}', .5, (x, -10, 3), lamp); b = sphere(f'LW{k}', .5, (x, -10, 3), wl)
        t = int(F * .55) + k * 3
        kf(a, 'scale', t, (1, 1, 1)); kf(a, 'scale', t + 3, (0, 0, 0)); kf(b, 'scale', t, (0, 0, 0)); kf(b, 'scale', t + 3, (1, 1, 1))
    world_fog(sc, 0.008, (0.85, 0.87, 0.9))
    light('Moon', 'SUN', (20, 60, 50), 3.0, (0.75, 0.8, 1.0), look=(0, 0, 0))
    c = cam('Cam', (0, -60, 12), (0, 60, 10), 32); c.data.clip_end = 3000
    cam_move(c, [(1, (-10, -60, 12)), (F, (5, -70, 10))], [(1, (-30, 120, 12)), (F, (-10, 80, 8))])

@page(16)
def p16():
    sc, F = base(16, kuwa=4, paper=0.7, bloom=0.8, grade=(1.05, .95, .88), sat=1.15)
    world_color(sc, (0.0, 0.0, 0.0))
    plane('Void', (6, 4), (0, 0, -0.001), mat_paint('M_Void', (0.06, 0.05, 0.05)))
    root, hinge, socks = codex((-0.21, 0, 0), open_deg=178, name='First')
    plane('OpenPage', (0.4, 0.56), (-0.21, 0, 0.122), mat_paint('M_OpenPage', (0.9, 0.84, 0.66)))
    t_hit = int(FPS * 4.0)
    blood = sphere('Blood', 0.012, (-0.2, 0, 0.9), glow('M_Blood', (0.45, 0.0, 0.01), 1.4))
    kfs(blood, 'location', [(int(t_hit * .5), (-0.2, 0, 0.9)), (t_hit, (-0.2, 0, 0.125))])
    kfs(blood, 'scale', [(t_hit, (1, 1, 1.5)), (t_hit + 2, (3, 3, .1)), (t_hit + 10, (5, 5, .05))])
    g = glyph('FirstGlyph', 16, (-0.2, 0, 0.126), 0.2, gold(6), depth=0.003); write_on(g, t_hit + 6, t_hit + 40)
    on = glow('M_FirstSock', (1, .75, .3), 0); socks[0].data.materials[0] = on
    glow_key(on, [(t_hit + 40, 0), (t_hit + 48, 25), (F, 10)])
    burst = light('Burst', 'POINT', (-0.2, 0, 0.4), 0, (1, .75, .3), 0.3)
    kfs(burst.data, 'energy', [(t_hit + 40, 0), (t_hit + 46, 120), (F, 40)])
    embers(120, (-.6, -.5, .1), (.4, .5, .4), t_hit + 40, F, (1, .78, .35), seed=16, rise=1.2, size=.004, strength=8)
    title_t = page_frames(16) - int(FPS * 5.0)
    tt = text3d('Title', 'SIGIL  &  SPARK', (0, 0.15, 0.9), 0.11, glow('M_TitleGold', (1.0, 0.74, 0.30), 2.2))
    tt.rotation_euler = (math.radians(55), 0, 0)
    kfs(tt, 'scale', [(title_t, (0, 0, 0)), (title_t + 12, (1.06, 1.06, 1.06)), (title_t + 24, (1, 1, 1))])
    c = cam('Cam', (0, -0.9, 1.1), (0, 0, 0.1), 42)
    cam_move(c, [(1, (0.1, -0.6, 0.85)), (t_hit, (0, -0.45, 0.6)), (title_t, (0, -0.5, 0.75)), (F, (0, -1.1, 1.4))],
             [(1, (-0.2, 0, 0.1)), (t_hit, (-0.2, 0, 0.12)), (title_t, (-0.1, 0.05, 0.3)), (F, (0, 0.15, 0.8))])

# ======================================================================= look pass 4
@page(4)
def p04():
    sc, F = base(4, kuwa=6, paper=0.7, bloom=0.7, grade=(1, 1, 1), sat=1.35)
    world_color(sc, (0.88, 0.80, 0.60), 1.0)
    parchment_floor((60, 40))
    ink = inkmat(); rnd = random.Random(44)
    for k in range(60): glyph(f'G{k}', 440 + k, (rnd.uniform(-2.2, 2.2), rnd.uniform(-1, 3), 0.003), rnd.uniform(.08, .2), ink, depth=0.004)
    cast = [('Flying/Dragon', (0.95, 0.42, 0.16)), ('Flying/Glub', (0.25, 0.55, 0.95)), ('Flying/Armabee', (0.98, 0.82, 0.18)),
            ('Blob/Mushnub', (0.45, 0.75, 0.35)), ('Flying/Ghost', (0.75, 0.55, 0.95))]
    for k, (rel, col) in enumerate(cast):
        x = (k - 2) * 0.42; y = 0.4 + (k % 2) * 0.35
        roots, _ = paint_creature(rel, (x, y, -0.5), 0.12, col, rot_z=math.radians(rnd.uniform(-25, 25)))
        for ro in roots:
            t = 1 + k * 8
            kfs(ro, 'location', [(t, (x, y, -0.5)), (t + 30, (x, y, 0.22 + 0.08 * (k % 2))), (F, (x * 1.1, y - 0.1, 0.4 + 0.08 * (k % 2)))])
    embers(120, (-1.5, -.6, 0), (1.5, 1.2, .2), 1, F, (1, .8, .4), seed=4, rise=1.2, size=.006)
    sun = light('Sun', 'SUN', (3, -4, 6), 3.5, (1, .92, .8), look=(0, 0, 0)); sun.data.use_shadow = False
    c = cam('Cam', (0, -2.6, 1.6), (0, 0.4, 0.2), 28)
    cam_move(c, [(1, (0, -2.6, 1.7)), (F, (0.3, -2.3, 1.5))], [(1, (0, 0.5, 0.0)), (F, (0, 0.5, 0.3))])

@page(9)
def p09():
    """the wave takes Hollowmere; when it has passed, red ink blooms across the empty water"""
    sc, F = base(9, kuwa=7, paper=0.65, bloom=0.7, grade=(1.0, .85, .82), sat=1.1)
    world_color(sc, (0.08, 0.06, 0.08))
    town2(True, trees=0.15)
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=30, depth=260, location=(0, 120, 0))
    wv = bpy.context.active_object; wv.name = 'Wave'
    for cc in list(wv.users_collection): cc.objects.unlink(wv)
    link(wv); wv.rotation_euler = (0, math.pi / 2, 0)
    wv.data.materials.append(mat_paint('M_WaveInk', (0.10, 0.16, 0.28), grain=.6))
    kfs(wv, 'location', [(1, (0, 160, -15)), (int(F * .45), (0, 40, 8)), (int(F * .6), (0, -10, 2)), (int(F * .62), (0, -10, -60))])
    # everything the wave covered sinks away with it
    for o in list(sc.objects):
        if o.type == 'MESH' and o.name not in ('Wave', 'Sea') and not o.name.startswith('SM_Mount'):
            kf(o, 'location', int(F * .55), o.location.copy()); kf(o, 'location', int(F * .6), o.location + Vector((0, 0, -80)))
    red = translucent_glow('M_Bleed', (0.6, 0.0, 0.02), 1.1, 0.6); rnd = random.Random(99)
    for k in range(14):
        b = sphere(f'Bleed{k}', 1.0, (rnd.uniform(-40, 40), rnd.uniform(-20, 30), -1.0), red)
        t = int(F * .62) + k * 3; s = rnd.uniform(4, 14)
        kf(b, 'scale', t, (0, 0, 0)); kf(b, 'scale', min(F, t + 40), (s * rnd.uniform(1, 1.8), s, 0.05))
    light('Moon', 'SUN', (30, -40, 60), 1.4, (0.6, 0.7, 1.0), look=(0, 0, 0))
    c = cam('Cam', (0, -90, 30), (0, 10, 5), 28); c.data.clip_end = 3000
    cam_move(c, [(1, (0, -90, 30)), (F, (0, -100, 40))], [(1, (0, 10, 5)), (F, (0, 5, 0))])
    shake(c, int(F * .4), int(F * .62), 0.4, seed=9)

@page(12)
def p12():
    sc, F = base(12, kuwa=6, paper=0.7, bloom=0.7, grade=(.95, .95, 1.0), sat=1.1)
    world_color(sc, (0.10, 0.09, 0.12))
    plane('Ground', (60, 40), (0, 0, 0), mat_paint('M_Ground12', (0.25, 0.22, 0.24)))
    roots, new = creature('Flying/Dragon', (0, 0, 0.7), 0.3, color=(0.95, 0.42, 0.16), rot_z=math.radians(-20))
    play_creature_anim(roots)
    bm_ = mat_blank('M_Blanking', (0.95, 0.42, 0.16), int(F * .25), int(F * .85))
    for o in new:
        if o.type == 'MESH':
            for s_ in o.material_slots: s_.material = bm_
    lamp = glow('M_Lamp12', (1.0, 0.7, 0.3), 8); wl = glow('M_LampWhite', (0.95, 0.95, 1.0), 3)
    for k in range(10):
        p = (-4 + k * .9, 5.5, 1.2)
        lp = sphere(f'Lamp{k}', 0.07, p, lamp); wlp = sphere(f'LampW{k}', 0.07, p, wl)
        t = int(F * .5) + k * 6
        kf(lp, 'scale', t, (1, 1, 1)); kf(lp, 'scale', t + 4, (0, 0, 0)); kf(wlp, 'scale', t, (0, 0, 0)); kf(wlp, 'scale', t + 4, (1, 1, 1))
    light('Key', 'SUN', (3, -4, 5), 2.5, (0.85, 0.85, 1.0), look=(0, 0, 0))
    c = cam('Cam', (0, -4.5, 1.0), (0, 0, 0.7), 32)
    cam_move(c, [(1, (0.6, -4.8, 1.0)), (F, (-0.4, -4.0, 0.9))], [(1, (0, 0, 0.6)), (F, (0, 0.5, 0.7))])

# ======================================================================= final render settings: drawn "on twos"
STEP = 2            # 12 drawings per second, like hand-drawn animation (and half the render time)
RES = (1600, 900)

def finalize_scenes():
    for sc in bpy.data.scenes:
        if not sc.name.startswith('SAGA_') or sc.name == 'SAGA_EDIT': continue
        sc.render.resolution_x, sc.render.resolution_y = RES; sc.render.resolution_percentage = 100
        sc.frame_step = STEP; sc.eevee.taa_render_samples = 24
    return True

def timeline():
    t, out = 1, {}
    for i in sorted(PAGES):
        out[i] = t; t += (page_frames(i) + STEP - 1) // STEP
    return out, t

def assemble(out_name='saga_intro.mp4'):
    """VSE at 12 fps: each page's drawings + its narration + the music bed → H.264/AAC mp4"""
    fps = FPS // STEP
    starts, end = timeline()
    sc = bpy.data.scenes.get('SAGA_EDIT') or bpy.data.scenes.new('SAGA_EDIT')
    sc.render.fps = fps; sc.frame_start = 1; sc.frame_end = end
    sc.render.resolution_x, sc.render.resolution_y = RES; sc.render.resolution_percentage = 100
    ed = sc.sequence_editor or sc.sequence_editor_create()
    strips = ed.strips if hasattr(ed, 'strips') else ed.sequences
    for st in list(strips): strips.remove(st)
    for i, f0 in starts.items():
        d = os.path.join(OUT, 'frames', 'p%02d' % i)
        files = sorted(x for x in os.listdir(d) if x.endswith('.png')) if os.path.isdir(d) else []
        if files:
            st = strips.new_image(f'P{i:02d}', os.path.join(d, files[0]), channel=1, frame_start=f0)
            for f in files[1:]: st.elements.append(f)
        vo = os.path.join(AUD, 'vo_saga_%02d.wav' % i)
        if os.path.exists(vo): strips.new_sound(f'VO{i:02d}', vo, channel=3, frame_start=f0 + fps)
    for k, (pg, fn, gain) in enumerate(MUSIC):
        f = os.path.join(MUS, fn)
        if not os.path.exists(f): continue
        f0 = starts[pg]; f1 = starts[MUSIC[k + 1][0]] if k + 1 < len(MUSIC) else end
        m = strips.new_sound(f'MUS{k}', f, channel=4 + (k % 2), frame_start=f0)
        if m.frame_final_end > f1 + fps: m.frame_final_end = f1 + fps
        m.volume = gain
    try: sc.render.image_settings.media_type = 'VIDEO'   # Blender 5.x: pick the video media type before FFMPEG
    except Exception: pass
    sc.render.image_settings.file_format = 'FFMPEG'
    sc.render.ffmpeg.format = 'MPEG4'; sc.render.ffmpeg.codec = 'H264'; sc.render.ffmpeg.constant_rate_factor = 'HIGH'
    sc.render.ffmpeg.audio_codec = 'AAC'; sc.render.ffmpeg.audio_bitrate = 192; sc.render.ffmpeg.audio_mixrate = 48000
    sc.render.filepath = os.path.join(OUT, out_name)
    return sc.name, end, end / fps

def write_subs(dest=None):
    """subtitle cues for the game (Content/Movies/saga_intro_subs.json): each page's narration split into sentence
    chunks (≤ ~95 chars), timed in proportion to their length across that line's real wav duration"""
    import re
    ns = {}; exec(open(os.path.join(SRC, 'tools', 'pbx_kokoro.py')).read().split("if __name__")[0].split("import soundfile")[0] + "\n", ns) if False else None
    src = open(os.path.join(SRC, 'tools', 'pbx_kokoro.py'), encoding='utf-8').read()
    lines = dict(re.findall(r"'(saga_\d+)':\s*(['\"])(.+?)\2,\n", src) and [(a, c) for a, b, c in re.findall(r"'(saga_\d+)':\s*(['\"])(.+?)\2,\n", src)])
    fps = FPS // STEP; starts, end = timeline(); cues = []
    for i, f0 in starts.items():
        text = lines.get('saga_%02d' % i, '')
        if not text: continue
        sents = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
        chunks, cur = [], ''
        for s in sents:
            if cur and len(cur) + len(s) > 95: chunks.append(cur); cur = s
            else: cur = (cur + ' ' + s).strip()
        if cur: chunks.append(cur)
        t = (f0 - 1) / fps + 1.0; dur = vo_secs(i); total = sum(len(c) for c in chunks)
        for c in chunks:
            d = dur * len(c) / total; cues.append({'t0': round(t, 2), 't1': round(t + d + 0.25, 2), 'text': c}); t += d
    dest = dest or os.path.join(OUT, 'saga_intro_subs.json')
    json.dump(cues, open(dest, 'w', encoding='utf-8'), indent=1)
    return dest, len(cues)
