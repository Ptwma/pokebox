# Sigil & Spark — legend intro, the REAL sample (~16 s, pages 5 → 7): user 2026-11-01 "the small piece with the 5–7 hours".
# Upgrades over pilot_book.py:
#   * the Sparks are real PEN-AND-INK drawings: rendered in their own scenes (ortho side view, Freestyle pen lines with
#     calligraphic thickness + taper + wobble, cel hatching in the shadows, an ink wash), animated (idle breath, lines boil
#     on twos), then printed onto the page as a decal → they read as drawn, not as cut-out silhouettes
#   * lit aged paper (fibres, foxing, burnt edges, bump) with invented marginalia script + ruled frames, curved pages
#   * living ink: bleed into the fibres, the Blanking erodes the lines into dust, ink runs toward the spine, cracks open
#     with paper fibres, the owner's name fades
#   * the tear: jagged rip with fibres, the drawing peels off the paper into a 3D ink beast backlit by a red flash,
#     ink strands snap, droplets, ink splatters the lens, the beast lunges into the camera; impact frames
#   * candle light that flickers and dies, dust in the air, depth of field, motion blur, handheld camera
# exec order in Blender: saga_blender → saga_pages → saga_crimson → sample2d → pilot_book (m_ink, m_fade) → legend_book
#   lb_draw_build(); lb_draw_render_bg()   → TEX/draw_<name>/d_####.png   (pen drawings)
#   lb_build(); lb_still([...]); lb_render_bg()   → OUT/frames → OUT/legend_book_silent.mp4 (sound is mixed afterwards)
import bpy, math, os, random, json, subprocess
from mathutils import Vector, Matrix, Quaternion

LB_OUT = os.path.join(SRC, 'intro_render', 'legend_book')
TEX = os.path.join(SRC, 'intro2d', 'tex')
LB_FPS = 24
# timeline (frames @24)
A_END = 270; VO_AT = 15
B0 = 271; EYE = 300; TEAR = 312; LUNGE = 340; HIT = 372; LB_F = 384
PAGE_W, PAGE_H = 1.0, 1.4
DECAL = 0.66            # world size of the drawing window on the page

DRAWINGS = {   # name: (model, frames to render, clip, speed, wash colour)
    'ghost':  ('Flying/Ghost', 150, 'Flying_Idle', 0.55, (0.80, 0.76, 0.70)),
    'beast':  ('Flying/Dragon', 48, 'Flying_Idle', 0.7, (0.88, 0.68, 0.60)),
    'row0':   ('Flying/Glub', 1, 'Flying_Idle', 1.0, (0.8, 0.78, 0.74)),
    'row1':   ('Flying/Hywirl', 1, 'Flying_Idle', 1.0, (0.8, 0.78, 0.74)),
    'row2':   ('Blob/Mushnub', 1, 'Idle', 1.0, (0.8, 0.78, 0.74)),
    'row3':   ('Flying/Squidle', 1, 'Flying_Idle', 1.0, (0.8, 0.78, 0.74)),
    'row4':   ('Flying/Armabee', 1, 'Flying_Idle', 1.0, (0.8, 0.78, 0.74)),
}
SIDE_UP = Matrix(((0, 1, 0), (0, 0, 1), (1, 0, 0))).to_quaternion()   # model +X → up, model -Y (head) → page -X, model +Z → page +Y

def _key_const(obj):
    """constant interpolation on every key of obj (works with layered actions in 5.x)"""
    ad = obj.animation_data
    if not (ad and ad.action): return
    fcs = []
    try: fcs = list(ad.action.fcurves)
    except Exception: pass
    if not fcs:
        try:
            for lay in ad.action.layers:
                for st in lay.strips:
                    for cb in st.channelbags: fcs += list(cb.fcurves)
        except Exception: pass
    for fc in fcs:
        for k in fc.keyframe_points: k.interpolation = 'CONSTANT'

def key_hide_tree(obj, states):
    """hide_render does not propagate to children → key it on obj AND every descendant. states = [(frame, hidden)]"""
    objs = [obj] + [o for o in bpy.data.objects if _is_under(o, obj)]
    for o in objs:
        for f, h in states:
            o.hide_render = h; o.keyframe_insert('hide_render', frame=f)

def model_bounds(b):
    """world bbox of the evaluated (posed, skinned) meshes under b"""
    dg = bpy.context.evaluated_depsgraph_get(); pts = []
    for o in bpy.data.objects:
        if o.type == 'MESH' and _is_under(o, b):
            oe = o.evaluated_get(dg); me = oe.to_mesh(); mw = oe.matrix_world; vs = me.vertices
            pts += [mw @ vs[i].co for i in range(0, len(vs), 3)]
            oe.to_mesh_clear()
    mn = Vector([min(p[i] for p in pts) for i in range(3)]); mx = Vector([max(p[i] for p in pts) for i in range(3)])
    return mn, mx

def _is_under(o, top):
    p = o.parent
    while p:
        if p == top: return True
        p = p.parent
    return False

# =================================================================== 1. pen-and-ink drawings
def m_pen(name, wash):
    """drawing fill: paper-white where lit, ink wash in the mid band, wash + cross-hatching in the shadows
    (screen-space hatch so it reads as drawn strokes)"""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    nt, N, L = _nodes(m)
    out = N.new('ShaderNodeOutputMaterial')
    dif = N.new('ShaderNodeBsdfDiffuse'); s2r = N.new('ShaderNodeShaderToRGB'); bw = N.new('ShaderNodeRGBToBW')
    L.new(dif.outputs[0], s2r.inputs[0]); L.new(s2r.outputs[0], bw.inputs[0])
    tc = N.new('ShaderNodeTexCoord'); sep = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Window'], sep.inputs[0])
    def hatch(angle_sign, freq, width):
        a = N.new('ShaderNodeMath'); a.operation = 'MULTIPLY'; a.inputs[1].default_value = freq
        b = N.new('ShaderNodeMath'); b.operation = 'MULTIPLY'; b.inputs[1].default_value = freq * angle_sign
        L.new(sep.outputs['X'], a.inputs[0]); L.new(sep.outputs['Y'], b.inputs[0])
        s = N.new('ShaderNodeMath'); s.operation = 'ADD'; L.new(a.outputs[0], s.inputs[0]); L.new(b.outputs[0], s.inputs[1])
        f = N.new('ShaderNodeMath'); f.operation = 'FRACT'; L.new(s.outputs[0], f.inputs[0])
        t = N.new('ShaderNodeMath'); t.operation = 'LESS_THAN'; t.inputs[1].default_value = width; L.new(f.outputs[0], t.inputs[0])
        return t.outputs[0]
    h1 = hatch(1.0, 95.0, 0.2); h2 = hatch(-1.0, 95.0, 0.18)
    mid = N.new('ShaderNodeMath'); mid.operation = 'LESS_THAN'; mid.inputs[1].default_value = 0.30; L.new(bw.outputs[0], mid.inputs[0])
    dark = N.new('ShaderNodeMath'); dark.operation = 'LESS_THAN'; dark.inputs[1].default_value = 0.12; L.new(bw.outputs[0], dark.inputs[0])
    m1 = N.new('ShaderNodeMath'); m1.operation = 'MULTIPLY'; L.new(mid.outputs[0], m1.inputs[0]); L.new(h1, m1.inputs[1])
    m2 = N.new('ShaderNodeMath'); m2.operation = 'MULTIPLY'; L.new(dark.outputs[0], m2.inputs[0]); L.new(h2, m2.inputs[1])
    hs = N.new('ShaderNodeMath'); hs.operation = 'MAXIMUM'; L.new(m1.outputs[0], hs.inputs[0]); L.new(m2.outputs[0], hs.inputs[1])
    # wash: white → wash colour in the mid band, deeper in the dark band
    w1 = N.new('ShaderNodeMix'); w1.data_type = 'RGBA'; w1.inputs['A'].default_value = (1, 1, 1, 1); w1.inputs['B'].default_value = (*wash, 1)
    L.new(mid.outputs[0], w1.inputs['Factor'])
    w2 = N.new('ShaderNodeMix'); w2.data_type = 'RGBA'; w2.inputs['B'].default_value = (*(c * 0.82 for c in wash), 1)
    L.new(dark.outputs[0], w2.inputs['Factor']); L.new(w1.outputs['Result'], w2.inputs['A'])
    ink = N.new('ShaderNodeMix'); ink.data_type = 'RGBA'; ink.inputs['B'].default_value = (0.12, 0.08, 0.06, 1)
    L.new(hs.outputs[0], ink.inputs['Factor']); L.new(w2.outputs['Result'], ink.inputs['A'])
    em = N.new('ShaderNodeEmission'); L.new(ink.outputs['Result'], em.inputs['Color']); L.new(em.outputs[0], out.inputs['Surface'])
    return m

def pen_lines(sc):
    """pen: silhouettes + creases + contours, calligraphic thickness (nib at 45°), tapered ends, a slight wobble"""
    ink_lines(sc, thick=3.4, color=(0.05, 0.03, 0.025))
    st = sc.view_layers[0].freestyle_settings.linesets[0].linestyle
    if not any(mm.type == 'CALLIGRAPHY' for mm in st.thickness_modifiers):
        c = st.thickness_modifiers.new('Nib', 'CALLIGRAPHY'); c.orientation = 45; c.thickness_min = 1.0; c.thickness_max = 4.5
        c.blend = 'MULTIPLY'
    for g in st.geometry_modifiers:
        if g.type == 'PERLIN_NOISE_1D': g.amplitude = 1.1; g.frequency = 6

def lb_draw_build(names=None):
    """one scene per drawing: white paper world, ortho side camera framed on the model, pen material + pen lines"""
    meta = {}
    for name in (names or DRAWINGS):
        rel, nf, clipn, speed, wash = DRAWINGS[name]
        sc = new_scene('DRAW_' + name, (1024, 1024))
        sc.timeline_markers.clear()
        sc.frame_start, sc.frame_end = 1, nf; sc.render.fps = LB_FPS
        sc.eevee.taa_render_samples = 16
        # white paper behind the drawing but NO white ambient light on the model (camera rays only)
        w = bpy.data.worlds.new('DrawWorld'); sc.world = w; w.use_nodes = True; Nw, Lw = w.node_tree.nodes, w.node_tree.links
        for n in list(Nw): Nw.remove(n)
        ow = Nw.new('ShaderNodeOutputWorld'); bgw = Nw.new('ShaderNodeBackground'); bgw.inputs[0].default_value = (1, 1, 1, 1)
        bk = Nw.new('ShaderNodeBackground'); bk.inputs[0].default_value = (0.06, 0.06, 0.06, 1)
        lp = Nw.new('ShaderNodeLightPath'); ms = Nw.new('ShaderNodeMixShader')
        Lw.new(lp.outputs['Is Camera Ray'], ms.inputs[0]); Lw.new(bk.outputs[0], ms.inputs[1]); Lw.new(bgw.outputs[0], ms.inputs[2]); Lw.new(ms.outputs[0], ow.inputs['Surface'])
        pen_lines(sc)
        h, b, arm, acts = rig(rel, 1.0, 'Draw_' + name)
        pm = m_pen('MPen_' + name, wash)
        for o in bpy.data.objects:
            if o.type == 'MESH' and _is_under(o, b):
                o.data.materials.clear(); o.data.materials.append(pm)
        clip(arm, acts, clipn, 1, max(nf, 2), speed)
        light('DrawKey', 'SUN', (-2, -7, 7), 1.1, look=(0, 0, 0))   # raking light from the front-top-behind: the camera side gets real shadow bands
        sc.frame_set(1); bpy.context.view_layer.update()
        mn, mx = model_bounds(b)
        cy, cz = (mn.y + mx.y) / 2, (mn.z + mx.z) / 2
        size = max(mx.y - mn.y, mx.z - mn.z) * 1.18
        c = cam('DrawCam', (8, cy, cz), (0, cy, cz)); c.data.type = 'ORTHO'; c.data.ortho_scale = size
        sc.camera = c
        # lines boil on twos (a hair of camera jitter → Freestyle re-traces the strokes slightly differently)
        rnd = random.Random(hash(name) & 0xffff)
        for f in range(1, nf + 1, 2):
            kf(c, 'location', f, (8, cy + rnd.uniform(-1, 1) * size * 0.0025, cz + rnd.uniform(-1, 1) * size * 0.0025))
        _key_const(c)
        meta[name] = {'ortho': size, 'cy': cy, 'cz': cz, 'frames': nf}
    os.makedirs(TEX, exist_ok=True)
    jp = os.path.join(TEX, 'drawings.json'); old = json.load(open(jp)) if os.path.exists(jp) else {}
    old.update(meta); json.dump(old, open(jp, 'w'), indent=1)
    return meta

def lb_draw_render_bg(names=None):
    blend = os.path.join(TEX, 'drawings.blend'); bpy.ops.wm.save_as_mainfile(filepath=blend, copy=True)
    py = os.path.join(TEX, '_draw_render.py'); names = names or list(DRAWINGS)
    open(py, 'w').write(f'''import bpy, os
for n in {names!r}:
    sc = bpy.data.scenes["DRAW_" + n]; bpy.context.window.scene = sc
    d = os.path.join(r"{TEX}", "draw_" + n); os.makedirs(d, exist_ok=True)
    sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGB"
    sc.render.filepath = os.path.join(d, "d_")
    bpy.ops.render.render(animation=True, scene=sc.name)
open(os.path.join(r"{TEX}", "_draw_done"), "w").write("ok")
''')
    p = subprocess.Popen([bpy.app.binary_path, '-b', blend, '--python', py], creationflags=0x08000000,
                         stdout=open(os.path.join(TEX, '_draw_render.log'), 'w'), stderr=subprocess.STDOUT)
    return p.pid

# =================================================================== 2. paper, pages, book
def page_z(x_from_spine):
    """page curvature: rises from the spine, flattens, a slight droop at the outer edge"""
    t = abs(x_from_spine)
    return 0.055 * (1 - math.exp(-t / 0.07)) - 0.03 * (t / PAGE_W) ** 2

def make_page(name, side, mat, segs=(36, 30)):
    import bmesh
    me = bpy.data.meshes.new(name); bm = bmesh.new(); uv = bm.loops.layers.uv.new()
    nx, ny = segs; verts = []
    for j in range(ny + 1):
        row = []
        for i in range(nx + 1):
            t = i / nx; x = side * t * PAGE_W; y = (j / ny - 0.5) * PAGE_H
            row.append(bm.verts.new((x, y, page_z(x))))
        verts.append(row)
    for j in range(ny):
        for i in range(nx):
            vs = [verts[j][i], verts[j][i + 1], verts[j + 1][i + 1], verts[j + 1][i]]
            if side < 0: vs = vs[::-1]
            f = bm.faces.new(vs)
            for l in f.loops:
                co = l.vert.co; u = (co.x / PAGE_W) if side > 0 else (1 + co.x / PAGE_W)
                l[uv].uv = (u, co.y / PAGE_H + 0.5)
    bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    o = bpy.data.objects.new(name, me); link(o); me.materials.append(mat)
    return o

def _img(path, seq=None):
    if not os.path.exists(path): print('missing', path); return None
    im = bpy.data.images.load(path, check_existing=True)
    if seq: im.source = 'SEQUENCE'
    return im

def m_codex_page(name, script_idx, drawing=None, drain_keys=None, vis_keys=None, side=-1, seq_frames=1, seq_offset=0,
                 reveal_keys=None, script_reveal_keys=None, glow_keys=None, blank=False, extra=None, centre=(0.5, 0.53), size=None):
    """lit aged paper + script + an optional pen drawing decal. Keyed inputs: Drain (0 alive → 1 Blanked),
    Vis (drawing visible → 0 gone: the beast has left the paper). Full-intro extras: Reveal (the drawing draws itself),
    ScriptReveal (lines of script write themselves top→bottom), Glow (the page wakes: ink turns to glowing gold),
    blank (no script at all), extra = [(path, nframes, (u, v), size)] more drawings on the same page."""
    m = bpy.data.materials.new(name)
    nt, N, L = _nodes(m)
    out = N.new('ShaderNodeOutputMaterial'); bsdf = N.new('ShaderNodeBsdfPrincipled')
    bsdf.inputs['Roughness'].default_value = 0.88
    for nm in ('Specular IOR Level', 'Specular'):
        if nm in bsdf.inputs: bsdf.inputs[nm].default_value = 0.15
    tc = N.new('ShaderNodeTexCoord'); uvn = tc.outputs['UV']
    V = lambda nm, v: (lambda n: (setattr(n.outputs[0], 'default_value', v), n)[1])(N.new('ShaderNodeValue'))
    drain = N.new('ShaderNodeValue'); drain.label = 'Drain'; keyed_factor(drain.outputs[0], drain_keys or [(1, 0.0)])
    vis = N.new('ShaderNodeValue'); vis.label = 'Vis'; keyed_factor(vis.outputs[0], vis_keys or [(1, 1.0)])
    def mix(a, b, f, blend='MIX'):
        mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = blend
        for sock, val in (('A', a), ('B', b), ('Factor', f)):
            if isinstance(val, (tuple, list)): mx.inputs[sock].default_value = (*val, 1) if len(val) == 3 else val
            elif isinstance(val, (int, float)): mx.inputs[sock].default_value = val
            else: L.new(val, mx.inputs[sock])
        return mx.outputs['Result']
    def math_(op, a, b=None):
        mt = N.new('ShaderNodeMath'); mt.operation = op
        for i, val in enumerate((a, b)):
            if val is None: continue
            if isinstance(val, (int, float)): mt.inputs[i].default_value = val
            else: L.new(val, mt.inputs[i])
        return mt.outputs[0]
    # --- paper: aged blotches, fibres, foxing, burnt edges
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 2.6; nz.inputs['Detail'].default_value = 8; L.new(uvn, nz.inputs['Vector'])
    paper = mix((0.90, 0.82, 0.64), (0.70, 0.57, 0.38), math_('POWER', nz.outputs['Fac'], 2.2))
    mpf = N.new('ShaderNodeMapping'); mpf.inputs['Scale'].default_value = (420, 60, 1); L.new(uvn, mpf.inputs['Vector'])
    fb = N.new('ShaderNodeTexNoise'); fb.inputs['Scale'].default_value = 1.0; fb.inputs['Detail'].default_value = 3; L.new(mpf.outputs[0], fb.inputs['Vector'])
    paper = mix(paper, (0.62, 0.52, 0.36), math_('MULTIPLY', math_('GREATER_THAN', fb.outputs['Fac'], 0.62), 0.35))
    vo = N.new('ShaderNodeTexVoronoi'); vo.inputs['Scale'].default_value = 38; L.new(uvn, vo.inputs['Vector'])
    fox = math_('LESS_THAN', vo.outputs['Distance'], 0.06)
    nz2 = N.new('ShaderNodeTexNoise'); nz2.inputs['Scale'].default_value = 6; L.new(uvn, nz2.inputs['Vector'])
    paper = mix(paper, (0.55, 0.36, 0.20), math_('MULTIPLY', fox, math_('GREATER_THAN', nz2.outputs['Fac'], 0.58)))
    sep = N.new('ShaderNodeSeparateXYZ'); L.new(uvn, sep.inputs[0])
    ex = math_('ABSOLUTE', math_('SUBTRACT', sep.outputs['X'], 0.5)); ey = math_('ABSOLUTE', math_('SUBTRACT', sep.outputs['Y'], 0.5))
    edge = math_('MAXIMUM', ex, ey)
    burn = N.new('ShaderNodeMapRange'); burn.inputs['From Min'].default_value = 0.40; burn.inputs['From Max'].default_value = 0.5
    L.new(math_('ADD', edge, math_('MULTIPLY', nz2.outputs['Fac'], 0.06)), burn.inputs['Value'])
    paper = mix(paper, (0.30, 0.18, 0.09), math_('POWER', burn.outputs['Result'], 1.6))
    # --- script ink (alpha) — sepia, drains to grey and lightens
    img = _img(os.path.join(TEX, f'script_{script_idx % 8}.png'))
    ink_col = mix((0.16, 0.08, 0.05), (0.42, 0.41, 0.40), drain.outputs[0])
    if img and not blank:
        ti = N.new('ShaderNodeTexImage'); ti.image = img; L.new(uvn, ti.inputs['Vector'])
        a_s = math_('MULTIPLY', ti.outputs['Alpha'], math_('SUBTRACT', 0.9, math_('MULTIPLY', drain.outputs[0], 0.5)))
        if script_reveal_keys:
            sr = N.new('ShaderNodeValue'); sr.label = 'ScriptReveal'; keyed_factor(sr.outputs[0], script_reveal_keys)
            prog = math_('ADD', math_('SUBTRACT', 1.0, sep.outputs['Y']), math_('MULTIPLY', sep.outputs['X'], 0.06))
            a_s = math_('MULTIPLY', a_s, math_('LESS_THAN', prog, math_('MULTIPLY', sr.outputs[0], 1.08)))
        paper = mix(paper, ink_col, a_s)
    glow = None
    if glow_keys:
        glow = N.new('ShaderNodeValue'); glow.label = 'Glow'; keyed_factor(glow.outputs[0], glow_keys)
    rev = None
    if reveal_keys:
        rev = N.new('ShaderNodeValue'); rev.label = 'Reveal'; keyed_factor(rev.outputs[0], reveal_keys)
    ink_total = None
    # --- the pen drawing decal (window centred on the page, DECAL wide)
    decals = ([(drawing[0], drawing[1], centre, size or DECAL)] if drawing else []) + list(extra or [])
    for path, nf, (cu, cv), dsz in decals:
        dimg = _img(path, seq=(nf > 1))
        if dimg:
            mp = N.new('ShaderNodeMapping'); mp.vector_type = 'POINT'
            # page UV (0..1) → decal UV: centre (0.5, 0.53), size DECAL/PAGE_W × DECAL/PAGE_H
            mp.inputs['Scale'].default_value = (PAGE_W / dsz, PAGE_H / dsz, 1)
            mp.inputs['Location'].default_value = (0.5 - cu * PAGE_W / dsz, 0.5 - cv * PAGE_H / dsz, 0)
            L.new(uvn, mp.inputs['Vector'])
            def sample(vec):
                t = N.new('ShaderNodeTexImage'); t.image = dimg; t.extension = 'EXTEND'; t.interpolation = 'Cubic'   # white border repeats → no dark seams
                if nf > 1:
                    t.image_user.frame_duration = nf; t.image_user.frame_start = 1 + seq_offset; t.image_user.use_auto_refresh = True
                    t.image_user.use_cyclic = True; t.image_user.frame_offset = 0
                L.new(vec, t.inputs['Vector']); return t
            t0 = sample(mp.outputs[0])
            # bleed: a second, slightly displaced sample feathers the strokes into the fibres
            bn = N.new('ShaderNodeTexNoise'); bn.inputs['Scale'].default_value = 90; L.new(uvn, bn.inputs['Vector'])
            off = N.new('ShaderNodeVectorMath'); off.operation = 'SCALE'; off.inputs['Scale'].default_value = 0.004
            cen = N.new('ShaderNodeVectorMath'); cen.operation = 'SUBTRACT'; cen.inputs[1].default_value = (0.5, 0.5, 0.5)
            L.new(bn.outputs['Color'], cen.inputs[0]); L.new(cen.outputs[0], off.inputs[0])
            v2 = N.new('ShaderNodeVectorMath'); v2.operation = 'ADD'; L.new(mp.outputs[0], v2.inputs[0]); L.new(off.outputs[0], v2.inputs[1])
            t1 = sample(v2.outputs[0])
            # ink running toward the spine while draining (smear sample, shifted along x by Drain)
            sh = N.new('ShaderNodeCombineXYZ'); L.new(math_('MULTIPLY', drain.outputs[0], 0.10 * (1 if side < 0 else -1)), sh.inputs['X'])
            fbm = N.new('ShaderNodeTexNoise'); fbm.inputs['Scale'].default_value = 14; L.new(uvn, fbm.inputs['Vector'])
            shs = N.new('ShaderNodeVectorMath'); shs.operation = 'SCALE'; L.new(sh.outputs[0], shs.inputs[0]); L.new(fbm.outputs['Fac'], shs.inputs['Scale'])
            v3 = N.new('ShaderNodeVectorMath'); v3.operation = 'ADD'; L.new(mp.outputs[0], v3.inputs[0]); L.new(shs.outputs[0], v3.inputs[1])
            t2 = sample(v3.outputs[0])
            dcol = mix(t0.outputs['Color'], t1.outputs['Color'], 0.35, 'DARKEN')
            # Blanking: desaturate, lighten, erode the strokes into dust
            gray = N.new('ShaderNodeRGBToBW'); L.new(dcol, gray.inputs[0])
            dgrey = mix(dcol, gray.outputs[0], drain.outputs[0])
            dl = mix(dgrey, (1, 1, 1), math_('MULTIPLY', drain.outputs[0], 0.5))
            er = N.new('ShaderNodeTexNoise'); er.inputs['Scale'].default_value = 170; er.inputs['Detail'].default_value = 5; L.new(uvn, er.inputs['Vector'])
            dust = math_('LESS_THAN', er.outputs['Fac'], math_('MULTIPLY', drain.outputs[0], 0.62))
            dl = mix(dl, (1, 1, 1), dust)
            smear = mix((1, 1, 1), t2.outputs['Color'], math_('MULTIPLY', drain.outputs[0], 0.35))
            dl = mix(dl, smear, 1.0, 'MULTIPLY')
            # vis 1 → 0: the drawing leaves; a faint ink ghost stays where it was
            vf = math_('ADD', math_('MULTIPLY', vis.outputs[0], 0.92), 0.08)
            if rev is not None:   # the pen draws it: a ragged diagonal wipe in decal space
                sd = N.new('ShaderNodeSeparateXYZ'); L.new(mp.outputs[0], sd.inputs[0])
                rn = N.new('ShaderNodeTexNoise'); rn.inputs['Scale'].default_value = 18; L.new(uvn, rn.inputs['Vector'])
                pr = math_('ADD', math_('MULTIPLY', math_('ADD', sd.outputs['X'], math_('SUBTRACT', 1.0, sd.outputs['Y'])), 0.5), math_('MULTIPLY', rn.outputs['Fac'], 0.18))
                vf = math_('MULTIPLY', vf, math_('LESS_THAN', pr, math_('MULTIPLY', rev.outputs[0], 1.3)))
            dv = mix((1, 1, 1), dl, vf)
            ibw = N.new('ShaderNodeRGBToBW'); L.new(dv, ibw.inputs[0]); ink_amt = math_('SUBTRACT', 1.0, ibw.outputs[0])
            ink_total = ink_amt if ink_total is None else math_('MAXIMUM', ink_total, ink_amt)
            if glow is not None:   # the bond wakes: the drawing's ink turns to gold
                dv = mix(dv, (0.95, 0.55, 0.12), math_('MULTIPLY', ink_amt, glow.outputs[0]))
            paper = mix(paper, dv, 1.0, 'MULTIPLY')
    # --- the page itself drains to dead grey paper
    pg = N.new('ShaderNodeRGBToBW'); L.new(paper, pg.inputs[0])
    dead = mix(pg.outputs[0], (0.80, 0.79, 0.77), 0.0)
    dead = mix(dead, (0.86, 0.85, 0.83), 0.35, 'MULTIPLY')
    final = mix(paper, dead, drain.outputs[0])
    L.new(final, bsdf.inputs['Base Color'])
    bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.06; L.new(fb.outputs['Fac'], bump.inputs['Height'])
    L.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    if glow is not None:   # glowing gold ink + a warm wash over the whole page
        em = math_('MULTIPLY', glow.outputs[0], math_('ADD', math_('MULTIPLY', ink_total, 1.5) if ink_total is not None else 0.0, 0.10))
        for nm in ('Emission Color', 'Emission'):
            if nm in bsdf.inputs: bsdf.inputs[nm].default_value = (1.0, 0.52, 0.12, 1); break
        if 'Emission Strength' in bsdf.inputs: L.new(em, bsdf.inputs['Emission Strength'])
    L.new(bsdf.outputs[0], out.inputs['Surface'])
    return m

def m_leather(name='LB_Leather'):
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); nt, N, L = _nodes(m)
    out = N.new('ShaderNodeOutputMaterial'); b = N.new('ShaderNodeBsdfPrincipled'); b.inputs['Roughness'].default_value = 0.55
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 40; nz.inputs['Detail'].default_value = 10
    cr = N.new('ShaderNodeValToRGB'); cr.color_ramp.elements[0].color = (0.05, 0.012, 0.008, 1); cr.color_ramp.elements[1].color = (0.20, 0.05, 0.03, 1)
    L.new(nz.outputs['Fac'], cr.inputs[0]); L.new(cr.outputs[0], b.inputs['Base Color'])
    bp = N.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.35; L.new(nz.outputs['Fac'], bp.inputs['Height']); L.new(bp.outputs['Normal'], b.inputs['Normal'])
    L.new(b.outputs[0], out.inputs['Surface']); return m

def m_block(name='LB_Block'):
    """page-block edge: fine stacked lines of old paper"""
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); nt, N, L = _nodes(m)
    out = N.new('ShaderNodeOutputMaterial'); b = N.new('ShaderNodeBsdfPrincipled'); b.inputs['Roughness'].default_value = 0.9
    tc = N.new('ShaderNodeTexCoord'); wv = N.new('ShaderNodeTexWave'); wv.wave_type = 'BANDS'; wv.bands_direction = 'Z'
    wv.inputs['Scale'].default_value = 60; wv.inputs['Distortion'].default_value = 2; L.new(tc.outputs['Object'], wv.inputs['Vector'])
    cr = N.new('ShaderNodeValToRGB'); cr.color_ramp.elements[0].color = (0.55, 0.45, 0.30, 1); cr.color_ramp.elements[1].color = (0.82, 0.74, 0.58, 1)
    L.new(wv.outputs['Fac'], cr.inputs[0]); L.new(cr.outputs[0], b.inputs['Base Color']); L.new(b.outputs[0], out.inputs['Surface'])
    return m

def codex_book(name, loc, rot_z, mats):
    """open Codex: leather cover, page blocks, two curved pages; returns (root, {side: page_obj})"""
    root = bpy.data.objects.new(name, None); link(root); root.location = loc; root.rotation_euler = (0, 0, rot_z)
    cov = cube(name + '_Cover', (PAGE_W * 2 + 0.14, PAGE_H + 0.12, 0.035), (0, 0, -0.035), m_leather(), bevel=0.012); cov.parent = root
    pages = {}
    for side in (-1, 1):
        blk = cube(f'{name}_Block{side}', (PAGE_W - 0.01, PAGE_H - 0.02, 0.05), (side * PAGE_W / 2, 0, -0.025), m_block(), bevel=0.006)
        blk.parent = root
        pg = make_page(f'{name}_Page{side}', side, mats[side]); pg.parent = root; pg.location = (0, 0, 0.002)
        pages[side] = pg
    return root, pages

def decal_world(page_obj, side):
    """world position of the drawing window centre on a page (UV 0.5, 0.53)"""
    x = side * PAGE_W * 0.5; y = (0.53 - 0.5) * PAGE_H
    return page_obj.matrix_world @ Vector((x, y, page_z(x) + 0.004))

def crack_curve(name, page_obj, side, seed, f0, f1, centre=(0.5, 0.5)):
    """a crack writing itself across a drained page + a pale fibre edge beside it"""
    rnd = random.Random(seed); out = []
    for k, (col, depth, off) in enumerate((((0.20, 0.18, 0.17), 0.0006, 0.0), ((0.62, 0.60, 0.57), 0.00025, 0.0012))):
        rr = random.Random(seed)
        cu = bpy.data.curves.new(f'{name}{k}', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = depth
        for s in range(5):
            sp = cu.splines.new('POLY'); n = rr.randint(5, 8); sp.points.add(n - 1)
            u, v = centre[0] + rr.uniform(-0.25, 0.25), centre[1] + rr.uniform(-0.3, 0.3); a = rr.uniform(0, 2 * math.pi)
            for i in range(n):
                x = side * (u if side > 0 else 1 - u) * PAGE_W; y = (v - 0.5) * PAGE_H
                sp.points[i].co = (x + off, y + off, page_z(x) + 0.0004, 1)
                a += rr.uniform(-0.8, 0.8); st = rr.uniform(0.03, 0.08)
                u += math.cos(a) * st * (1 if side > 0 else -1) * 0.7; v += math.sin(a) * st
        o = bpy.data.objects.new(f'{name}{k}', cu); link(o); o.parent = page_obj; o.visible_shadow = False
        cu.materials.append(glow(f'LB_Crack{k}', col, 1.0)); write_on(o, f0 + k * 3, f1 + k * 3); out.append(o)
    return out

def candle_lit(name, loc, out_f=None, energy=6.0):
    """wax candle + flame + a real flickering point light; dies at out_f with a curl of smoke"""
    wax = bpy.data.materials.get('LB_Wax')
    if not wax:
        wax = bpy.data.materials.new('LB_Wax'); nt, N, L = _nodes(wax)
        o = N.new('ShaderNodeOutputMaterial'); b = N.new('ShaderNodeBsdfPrincipled'); b.inputs['Base Color'].default_value = (0.85, 0.78, 0.62, 1)
        b.inputs['Roughness'].default_value = 0.4
        for nm in ('Subsurface Weight', 'Subsurface'):
            if nm in b.inputs: b.inputs[nm].default_value = 0.3
        L.new(b.outputs[0], o.inputs['Surface'])
    c = cube(name, (0.07, 0.07, 0.34), (loc[0], loc[1], loc[2] + 0.17), wax, bevel=0.012)
    fl = sphere(name + '_Flame', 0.03, (loc[0], loc[1], loc[2] + 0.38), glow('LB_Flame', (1.0, 0.62, 0.26), 8.0)); fl.scale = (0.65, 0.65, 1.5)
    ld = bpy.data.lights.new(name + '_L', 'POINT'); ld.color = (1.0, 0.58, 0.28); ld.shadow_soft_size = 0.02; ld.energy = energy
    lo = bpy.data.objects.new(name + '_L', ld); link(lo); lo.location = (loc[0], loc[1], loc[2] + 0.42)
    rnd = random.Random(hash(name) & 0xffff); end = out_f or LB_F
    for f in range(1, end + 1, 2):
        s = rnd.uniform(0.85, 1.15); kf(fl, 'scale', f, (0.65 * s, 0.65 * s, 1.5 * rnd.uniform(0.8, 1.25)))
        ld.energy = energy * rnd.uniform(0.75, 1.1); ld.keyframe_insert('energy', frame=f)
    if out_f:
        kf(fl, 'scale', out_f + 2, (0, 0, 0)); ld.energy = 0; ld.keyframe_insert('energy', frame=out_f + 3)
        sm = embers(10, (loc[0] - .02, loc[1] - .02, loc[2] + .38), (loc[0] + .02, loc[1] + .02, loc[2] + .42), out_f + 1, out_f + 50,
                    color=(0.30, 0.29, 0.28), size=0.008, rise=0.55, seed=hash(name) & 0xff, strength=0.6)
        return c, fl, lo, sm
    return c, fl, lo, []

# =================================================================== 3. the beast, strands, compositor
def m_beast():
    """the ink beast: black ink body, a red rim where it turns away (backlit by the flash), a faint wet sheen"""
    return m_ink('LB_Beast', [(1, 0.0)], rim=(0.95, 0.06, 0.03))

def comp_legend(sc, invert_keys, black_keys, splat_keys):
    ng = bpy.data.node_groups.new('LB_Comp', 'CompositorNodeTree')
    ng.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
    N, L = ng.nodes, ng.links
    rl = N.new('CompositorNodeRLayers'); src = rl.outputs['Image']
    gl = N.new('CompositorNodeGlare')
    for v in ('Bloom', 'Fog Glow'):
        try: gl.inputs['Type'].default_value = v; break
        except Exception: pass
    for nm, v in (('Threshold', 0.85), ('Strength', 0.5), ('Size', 0.6)):
        if nm in gl.inputs: gl.inputs[nm].default_value = v
    L.new(src, gl.inputs['Image']); src = gl.outputs['Image']
    try:
        ld = N.new('CompositorNodeLensdist')
        for nm, v in (('Dispersion', 0.012), ('Distortion', 0.0)):
            if nm in ld.inputs: ld.inputs[nm].default_value = v
        L.new(src, ld.inputs['Image']); src = ld.outputs['Image']
    except Exception as ex: print('lensdist', ex)
    em = N.new('CompositorNodeEllipseMask')
    try: em.inputs['Size'].default_value = (0.95, 0.85)
    except Exception: pass
    bl = N.new('CompositorNodeBlur')
    try: bl.inputs['Size'].default_value = (320, 320)
    except Exception: bl.inputs['Size'].default_value = 320
    L.new(em.outputs['Mask'], bl.inputs['Image'])
    vg = N.new('ShaderNodeMix'); vg.data_type = 'RGBA'; vg.blend_type = 'MULTIPLY'; vg.inputs['Factor'].default_value = 0.7
    L.new(src, vg.inputs['A']); L.new(bl.outputs['Image'], vg.inputs['B']); src = vg.outputs['Result']
    # ink splatter on the lens
    sp_path = os.path.join(TEX, 'splatter_b.png')
    if os.path.exists(sp_path):
        im = N.new('CompositorNodeImage'); im.image = bpy.data.images.load(sp_path, check_existing=True)
        mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs['B'].default_value = (0.004, 0.002, 0.002, 1)
        fm = N.new('ShaderNodeMath'); fm.operation = 'MULTIPLY'; L.new(im.outputs['Alpha'], fm.inputs[0])
        keyed_factor(fm.inputs[1], splat_keys)
        L.new(fm.outputs[0], mx.inputs['Factor']); L.new(src, mx.inputs['A']); src = mx.outputs['Result']
    iv = N.new('CompositorNodeInvert'); L.new(src, iv.inputs['Color'])
    fac = iv.inputs['Fac'] if 'Fac' in iv.inputs else iv.inputs[0]; keyed_factor(fac, invert_keys); src = iv.outputs['Color']
    bk = N.new('ShaderNodeMix'); bk.data_type = 'RGBA'; bk.inputs['B'].default_value = (0, 0, 0, 1)
    keyed_factor(bk.inputs['Factor'], black_keys); L.new(src, bk.inputs['A']); src = bk.outputs['Result']
    out = N.new('NodeGroupOutput'); L.new(src, out.inputs[0])
    sc.compositing_node_group = ng; sc.render.use_compositing = True

def handheld(obj, f0, f1, amp, seed, step=3):
    """slow handheld drift on a parent jitter empty (the camera's own keys stay clean)"""
    rnd = random.Random(seed)
    for f in range(f0, f1 + 1, step):
        t = f * 0.11
        kf(obj, 'location', f, (amp * math.sin(t * 1.3 + seed), amp * math.sin(t * 0.9 + seed * 2), amp * 0.6 * math.sin(t * 1.7 + seed * 3)))

def lb_build():
    meta = json.load(open(os.path.join(TEX, 'drawings.json')))
    sc = new_scene('LEGEND_BOOK', (1920, 1080))
    sc.timeline_markers.clear()
    for c in list(sc.collection.children): sc.collection.children.unlink(c)
    sc.frame_start, sc.frame_end = 1, LB_F; sc.render.fps = LB_FPS; sc.frame_step = 1
    sc.eevee.taa_render_samples = 32
    try: sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.5
    except Exception: pass
    ink_lines(sc, thick=1.6, color=(0.03, 0.012, 0.01))
    world_color(sc, (0.004, 0.0025, 0.002))
    try:
        sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Punchy'
    except Exception: pass
    tbl = bpy.data.materials.new('LB_Table'); nt, N, L = _nodes(tbl)
    o_ = N.new('ShaderNodeOutputMaterial'); b_ = N.new('ShaderNodeBsdfPrincipled'); b_.inputs['Base Color'].default_value = (0.05, 0.025, 0.015, 1)
    b_.inputs['Roughness'].default_value = 0.7; L.new(b_.outputs[0], o_.inputs['Surface'])
    plane('Table', (40, 40), (0, 0, -0.06), tbl)
    fx = []
    dpath = lambda n: os.path.join(TEX, f'draw_{n}', 'd_0001.png')
    # ---------------- PART A: the hero book (ghost alive → Blanked), a row of grey books, candles dying
    dkA = [(1, 0.0), (40, 0.0), (140, 1.0)]
    matsA = {-1: m_codex_page('LB_PageA_L', 1, (dpath('ghost'), meta['ghost']['frames']), dkA, side=-1, seq_frames=meta['ghost']['frames']),
             1: m_codex_page('LB_PageA_R', 2, None, dkA, side=1)}
    rootA, pagesA = codex_book('BookA', (0, 0, 0), 0.0, matsA)
    crack_curve('CrackA', pagesA[-1], -1, 3, 92, 150); crack_curve('CrackB', pagesA[1], 1, 5, 104, 160)
    nm = text3d('NameA', 'Tomas Hale', (0.5, -0.47, page_z(0.5) + 0.005), 0.085,
                m_fade('LB_Name', (0.10, 0.05, 0.03), [(1, 1.0), (185, 1.0), (250, 0.0)]), font=r"C:\Windows\Fonts\segoesc.ttf", extrude=0.0)
    nm.parent = rootA
    row = [(-2.9, 1.7, 0.22), (2.95, 1.95, -0.18), (-5.7, 3.7, 0.3), (5.5, 4.0, -0.26), (0.2, 4.7, 0.04)]
    for i, (x, y, r) in enumerate(row):
        mm = {-1: m_codex_page(f'LB_Row{i}_L', 3 + i, (dpath(f'row{i}'), 1) if i % 2 == 0 else None, [(1, 1.0)], side=-1),
              1: m_codex_page(f'LB_Row{i}_R', 4 + i, (dpath(f'row{i}'), 1) if i % 2 == 1 else None, [(1, 1.0)], side=1)}
        codex_book(f'BookRow{i}', (x, y, 0), r, mm)
        _, fl, _, sm = candle_lit(f'Candle{i}', (x + 1.35, y + 0.95, -0.06), out_f=170 + i * 16, energy=35.0)
        fx += [fl] + sm
    _, fl, _, _ = candle_lit('CandleA', (1.45, 0.95, -0.06), energy=45.0); fx.append(fl)
    # the candle's glow as a soft warm key (an area light where the flame is) + a faint cold bounce
    kA = light('KeyA', 'AREA', (1.3, 0.7, 0.9), 70.0, (1.0, 0.62, 0.32), size=0.6, look=(-0.4, 0.0, 0.0))
    light('BounceA', 'AREA', (-1.5, -2.0, 2.5), 12.0, (0.55, 0.6, 0.75), size=2.5, look=(0, 0, 0))
    dust = embers(90, (-2.5, -1.5, 0.1), (2.5, 3.0, 1.6), 1, A_END, color=(1.0, 0.82, 0.6), size=0.0035, rise=0.25, seed=41, strength=3.0)
    fx += dust
    # ---------------- PART B: a clean Codex, the beast drawing (alive), the tear, the beast
    BY = -16.0
    matsB = {-1: m_codex_page('LB_PageB_L', 6, (dpath('beast'), meta['beast']['frames']), [(1, 0.0)],
                              vis_keys=[(1, 1.0), (TEAR - 1, 1.0), (TEAR, 0.0)], side=-1, seq_frames=meta['beast']['frames']),
             1: m_codex_page('LB_PageB_R', 7, None, [(1, 0.0)], side=1)}
    rootB, pagesB = codex_book('BookB', (0, BY, 0), 0.0, matsB)
    bpy.context.view_layer.update()
    D0 = decal_world(pagesB[-1], -1)
    # the tear: the left page is replaced at TEAR by two halves with a jagged edge that rip up and away
    pl = pagesB[-1]
    pl.hide_render = False; pl.keyframe_insert('hide_render', frame=TEAR - 1); pl.hide_render = True; pl.keyframe_insert('hide_render', frame=TEAR)
    for k, sgn in enumerate((1, -1)):
        half = make_page(f'TearHalf{k}', -1, matsB[-1], segs=(36, 30))
        import bmesh
        bm = bmesh.new(); bm.from_mesh(half.data)
        rr = random.Random(77)
        cut = lambda x: 0.02 + 0.06 * math.sin(x * 9) + rr.uniform(-0.02, 0.02)
        dele = [f for f in bm.faces if (f.calc_center_median().y - cut(f.calc_center_median().x)) * sgn < 0]
        bmesh.ops.delete(bm, geom=dele, context='FACES'); bm.to_mesh(half.data); bm.free()
        half.parent = rootB; half.location = (0, 0, 0.002)
        bd = half.modifiers.new('Curl', 'SIMPLE_DEFORM'); bd.deform_method = 'BEND'; bd.deform_axis = 'Y'; bd.angle = 0.0
        kf(half, 'location', TEAR, (0, 0, 0.002)); kf(half, 'rotation_euler', TEAR, (0, 0, 0))
        kf(half, 'location', TEAR + 7, (-0.15, sgn * 0.35, 0.45)); kf(half, 'rotation_euler', TEAR + 7, (math.radians(-55 * sgn), math.radians(-30), math.radians(12 * sgn)))
        kf(half, 'location', TEAR + 30, (-0.6, sgn * 1.4, 0.25)); kf(half, 'rotation_euler', TEAR + 30, (math.radians(-140 * sgn), math.radians(-55), math.radians(30 * sgn)))
        bd.angle = 0.0; bd.keyframe_insert('angle', frame=TEAR); bd.angle = math.radians(80 * sgn); bd.keyframe_insert('angle', frame=TEAR + 10)
        # fibres along the torn edge (short pale strands)
        fib = bpy.data.curves.new(f'Fibre{k}', 'CURVE'); fib.dimensions = '3D'; fib.bevel_depth = 0.0007
        for i in range(70):
            x = -rr.uniform(0.02, 0.98) * PAGE_W; y = cut(x)
            sp = fib.splines.new('POLY'); sp.points.add(1)
            sp.points[0].co = (x, y, page_z(x) + 0.003, 1); sp.points[1].co = (x + rr.uniform(-.01, .01), y + sgn * rr.uniform(0.004, 0.018), page_z(x) + 0.003, 1)
        fo = bpy.data.objects.new(f'Fibre{k}', fib); link(fo); fo.parent = half; fib.materials.append(glow('LB_Fibre', (0.95, 0.92, 0.85), 1.2))
        key_hide_tree(half, [(1, True), (TEAR - 1, True), (TEAR, False)])
    # the 3D ink beast: lies flat exactly over the drawing until TEAR, then peels off and lunges
    dm = meta['beast']; s_world = DECAL / dm['ortho']
    hB, bB, armB, actsB = rig('Flying/Dragon', 1.0, 'InkBeast')
    for o in bpy.data.objects:
        if o.type == 'MESH' and _is_under(o, bB):
            o.data.materials.clear(); o.data.materials.append(m_beast())
    # put the model's bbox centre (the drawing's frame centre) on the bob pivot, so the pivot = decal centre
    sc.frame_set(1); bpy.context.view_layer.update()
    rootM = next(o for o in bpy.data.objects if o.parent == bB)   # keep the glTF import rotation (same as in the drawing scene)
    rootM.location = (0, -dm['cy'], -dm['cz'])
    hB.rotation_mode = 'QUATERNION'; bB.scale = (s_world,) * 3
    clip(armB, actsB, 'Flying_Idle', 1, TEAR, 0.7); clip(armB, actsB, 'Headbutt', TEAR + 8, TEAR + 34, 0.85); clip(armB, actsB, 'Fast_Flying', TEAR + 30, LB_F, 1.5)
    camB_end = Vector((0.15, BY - 3.05, 0.55))
    P0 = D0.copy(); P1 = D0 + Vector((0.05, -0.25, 0.55)); P2 = D0 + Vector((0.1, -0.9, 0.7))
    def face(p, up_tilt=0.0):
        d = (camB_end - p).normalized(); d.z += up_tilt; d.normalize()
        return (-d).to_track_quat('Y', 'Z')
    key_hide_tree(hB, [(1, True), (TEAR - 1, True), (TEAR, False)])
    keys = [(1, P0, SIDE_UP, 0.012), (TEAR, P0, SIDE_UP, 0.012), (TEAR + 5, P0 + Vector((0, -0.05, 0.22)), SIDE_UP.slerp(face(P1, 0.5), 0.5), 1.2),
            (TEAR + 10, P1, face(P1, 0.45), 0.95), (TEAR + 14, P1 + Vector((0, 0, 0.03)), face(P1, 0.35), 1.0),
            (LUNGE, P2, face(P2, 0.15), 1.0), (HIT, camB_end + Vector((0, 0.12, 0.0)), face(camB_end, 0.0), 1.0)]
    for f, p, q, sz in keys:
        hB.location = p; hB.rotation_quaternion = q; hB.scale = (sz, 1, 1) if f <= TEAR else (sz, sz, sz)   # local X is world-up while lying on the page
        hB.keyframe_insert('location', frame=f); hB.keyframe_insert('rotation_quaternion', frame=f); hB.keyframe_insert('scale', frame=f)
    # ink strands from the paper to the rising body, snapping at TEAR+15
    rr = random.Random(5)
    for i in range(6):
        cu = bpy.data.curves.new(f'Strand{i}', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 0.006; cu.bevel_resolution = 3
        sp = cu.splines.new('BEZIER'); sp.bezier_points.add(1)
        so = bpy.data.objects.new(f'Strand{i}', cu); link(so); cu.materials.append(glow('LB_StrandInk', (0.008, 0.004, 0.004), 1.0))
        a0 = D0 + Vector((rr.uniform(-0.2, 0.2), rr.uniform(-0.25, 0.25), 0.0))
        for f in range(TEAR, TEAR + 16):
            sc.frame_set(f); bpy.context.view_layer.update(); tip = hB.matrix_world.translation + Vector((rr.uniform(-.05, .05), rr.uniform(-.05, .05), -0.05))
            for j, p in enumerate((a0, tip)):
                bp = sp.bezier_points[j]; bp.co = p; bp.handle_left = p + Vector((0, 0, -0.1 if j else 0.12)); bp.handle_right = p + Vector((0, 0, 0.1 if j else -0.12))
                for attr in ('co', 'handle_left', 'handle_right'): bp.keyframe_insert(attr, frame=f)
            cu.bevel_depth = 0.006 * (1 - (f - TEAR) / 18); cu.keyframe_insert('bevel_depth', frame=f)
        so.hide_render = True; so.keyframe_insert('hide_render', frame=TEAR - 1); so.hide_render = False; so.keyframe_insert('hide_render', frame=TEAR)
        so.hide_render = True; so.keyframe_insert('hide_render', frame=TEAR + 16)
        fx.append(so)
    drops = embers(80, tuple(D0 - Vector((0.35, 0.35, 0.0))), tuple(D0 + Vector((0.35, 0.35, 0.3))), TEAR, TEAR + 30, color=(0.006, 0.003, 0.003),
                   size=0.012, rise=1.2, seed=31, strength=1.0)
    reds = embers(45, tuple(D0 - Vector((0.4, 0.4, 0.0))), tuple(D0 + Vector((0.4, 0.4, 0.3))), TEAR, TEAR + 36, color=(1.0, 0.08, 0.03),
                  size=0.006, rise=1.6, seed=32, strength=8.0)
    fx += drops + reds
    # the red eye opens in the drawing (a glint on the page, before the tear)
    eye = sphere('EyeGlint', 0.012, (0, 0, 0), glow('LB_Eye', (1.0, 0.04, 0.02), 9.0)); fx.append(eye)
    eye.location = D0 + Vector((-0.143, 0.014, -0.002)); eye.visible_shadow = False   # on the drawing's eye (measured in d_0001)
    kf(eye, 'scale', EYE - 1, (0, 0, 0)); kf(eye, 'scale', EYE + 2, (1.8, 1.8, 0.4)); kf(eye, 'scale', EYE + 5, (1, 1, 0.3)); kf(eye, 'scale', TEAR - 1, (1.2, 1.2, 0.3))
    kf(eye, 'scale', TEAR, (0, 0, 0))
    # lights for B: one candle, a cold fill, and the red flash behind the book at the tear
    _, fl, _, _ = candle_lit('CandleB', (1.5, BY + 0.9, -0.06), energy=40.0); fx.append(fl)
    light('KeyB', 'AREA', (1.3, BY + 0.7, 0.9), 55.0, (1.0, 0.6, 0.3), size=0.6, look=(-0.4, BY, 0.0))
    rl = bpy.data.lights.new('RedFlash', 'POINT'); rl.color = (1.0, 0.07, 0.03); rl.shadow_soft_size = 0.3
    ro = bpy.data.objects.new('RedFlash', rl); link(ro); ro.location = D0 + Vector((0.2, 1.6, 0.9))
    for f, e in ((1, 0), (TEAR - 1, 0), (TEAR, 2600), (TEAR + 6, 900), (TEAR + 24, 600), (HIT, 1400)):
        rl.energy = e; rl.keyframe_insert('energy', frame=f)
    light('Fill', 'AREA', (0, BY - 4, 3), 30.0, (0.6, 0.65, 0.8), size=3.0, look=(0, BY, 0))
    # a red bloom behind the beast: radial glow card facing camera B → the black beast reads as a silhouette
    gm = bpy.data.materials.new('LB_RedBloom'); nt, N, L = _nodes(gm)
    o_ = N.new('ShaderNodeOutputMaterial'); em_ = N.new('ShaderNodeEmission'); em_.inputs['Color'].default_value = (1.0, 0.025, 0.008, 1)
    tc_ = N.new('ShaderNodeTexCoord'); gr_ = N.new('ShaderNodeTexGradient'); gr_.gradient_type = 'SPHERICAL'
    mp_ = N.new('ShaderNodeMapping'); mp_.inputs['Scale'].default_value = (2, 2, 1); mp_.inputs['Location'].default_value = (-1, -1, 0); L.new(tc_.outputs['UV'], mp_.inputs['Vector']); L.new(mp_.outputs[0], gr_.inputs['Vector'])
    pw_ = N.new('ShaderNodeMath'); pw_.operation = 'POWER'; pw_.inputs[1].default_value = 2.2; L.new(gr_.outputs['Fac'], pw_.inputs[0])
    tr_ = N.new('ShaderNodeBsdfTransparent'); ms_ = N.new('ShaderNodeMixShader'); L.new(pw_.outputs[0], ms_.inputs[0]); L.new(tr_.outputs[0], ms_.inputs[1]); L.new(em_.outputs[0], ms_.inputs[2])
    L.new(ms_.outputs[0], o_.inputs['Surface'])
    try: gm.surface_render_method = 'BLENDED'
    except Exception: pass
    keyed_factor(em_.inputs['Strength'], [(1, 0.0), (TEAR - 1, 0.0), (TEAR, 6.0), (TEAR + 8, 2.6), (HIT - 6, 2.0), (HIT, 4.5)])
    bloom = plane('RedBloom', (7.0, 7.0), tuple(D0 + Vector((0.3, 3.8, 1.2))), gm, rot=(math.radians(90), 0, 0)); fx.append(bloom)
    # ---------------- cameras
    cA = cam('CamA', (0, -1, 1), (0, 0, 0), lens=50)
    DA = decal_world(pagesA[-1], -1)
    cam_move(cA, [(1, tuple(DA + Vector((0.06, -0.95, 1.05)))), (150, tuple(DA + Vector((0.03, -0.72, 0.80)))), (175, tuple(DA + Vector((0.2, -1.0, 1.0)))),
                  (A_END, (0.5, -3.0, 2.5))],
             [(1, tuple(DA)), (150, tuple(DA + Vector((0.0, 0.02, 0.0)))), (175, tuple(DA + Vector((0.3, 0.1, 0.0)))), (A_END, (0.4, 1.6, 0.0))])
    jA = bpy.data.objects.new('CamA_Jit', None); link(jA); cA.parent = jA; handheld(jA, 1, A_END, 0.006, 1)
    cA.data.dof.use_dof = True; cA.data.dof.aperture_fstop = 1.8
    fA = bpy.data.objects.new('CamA_Focus', None); link(fA); cA.data.dof.focus_object = fA
    kf(fA, 'location', 1, tuple(DA)); kf(fA, 'location', 160, tuple(DA)); kf(fA, 'location', A_END, (0.2, 0.6, 0.0))
    cB = cam('CamB', tuple(camB_end), tuple(D0), lens=35)
    tB = cam_move(cB, [(B0, tuple(D0 + Vector((0.12, -0.75, 0.42)))), (TEAR, tuple(D0 + Vector((0.1, -0.62, 0.34)))),
                       (TEAR + 18, tuple(camB_end + Vector((0, 0.5, -0.05)))), (LB_F, tuple(camB_end))],
                  [(B0, tuple(D0)), (TEAR, tuple(D0)), (TEAR + 10, tuple(P1)), (LUNGE, tuple(P2)), (HIT, tuple(camB_end + Vector((0, 0.5, 0.0))))])
    jB = bpy.data.objects.new('CamB_Jit', None); link(jB); cB.parent = jB
    handheld(jB, B0, TEAR - 1, 0.004, 2)
    rj = random.Random(9)
    for f in range(TEAR, TEAR + 24, 2):
        a = 0.05 * (1 - (f - TEAR) / 24); kf(jB, 'location', f, (rj.uniform(-a, a), rj.uniform(-a, a), rj.uniform(-a, a)))
    handheld(jB, TEAR + 24, LUNGE, 0.008, 3)
    for f in range(LUNGE, HIT + 1, 2):
        a = 0.03 * (f - LUNGE) / (HIT - LUNGE); kf(jB, 'location', f, (rj.uniform(-a, a), rj.uniform(-a, a), rj.uniform(-a, a)))
    cB.data.dof.use_dof = True; cB.data.dof.aperture_fstop = 2.2
    fB = bpy.data.objects.new('CamB_Focus', None); link(fB); cB.data.dof.focus_object = fB
    kf(fB, 'location', B0, tuple(D0)); kf(fB, 'location', TEAR, tuple(D0))
    for f in range(TEAR + 2, HIT + 1, 4):
        sc.frame_set(f); bpy.context.view_layer.update(); kf(fB, 'location', f, tuple(hB.matrix_world.translation))
    for f, c in ((1, cA), (B0, cB)):
        mk = sc.timeline_markers.new(f'cut{f}', frame=f); mk.camera = c
    sc.camera = cA
    fx += speed_lines_ring(cB, TEAR + 2, HIT, 40, 7, color=(0.8, 0.05, 0.03))
    no_ink(fx + [o for o in sc.objects if o.name.startswith(('Table', 'BookA_Page', 'BookB_Page', 'TearHalf', 'Fibre', 'Crack', 'NameA'))
                 or o.name.startswith('BookRow') and '_Page' in o.name])
    comp_legend(sc, invert_keys=[(1, 0), (TEAR - 1, 0), (TEAR, 1), (TEAR + 2, 0), (HIT - 1, 0), (HIT, 1), (HIT + 2, 0)],
                black_keys=[(1, 0), (A_END - 6, 0), (A_END, 1), (B0, 1), (B0 + 8, 0), (HIT + 2, 0), (HIT + 3, 1), (LB_F, 1)],
                splat_keys=[(1, 0), (HIT - 7, 0), (HIT - 6, 1), (LB_F, 1)])
    return sc

def lb_still(frames, pct=40):
    sc = bpy.data.scenes['LEGEND_BOOK']; bpy.context.window.scene = sc; os.makedirs(LB_OUT, exist_ok=True)
    sc.render.resolution_percentage = pct; fmt = sc.render.image_settings.file_format; sc.render.image_settings.file_format = 'JPEG'
    outs = []
    for f in frames:
        sc.frame_set(f); p = os.path.join(LB_OUT, f'st_{f:04d}.jpg'); sc.render.filepath = p; bpy.ops.render.render(write_still=True); outs.append(p)
    sc.render.image_settings.file_format = fmt; sc.render.resolution_percentage = 100
    return outs

def lb_render_bg(frames=None):
    blend = os.path.join(LB_OUT, 'legend_book.blend'); os.makedirs(os.path.join(LB_OUT, 'frames'), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=blend, copy=True)
    py = os.path.join(LB_OUT, '_render.py')
    open(py, 'w').write(f'''import bpy, os
sc = bpy.data.scenes["LEGEND_BOOK"]; bpy.context.window.scene = sc
sc.render.image_settings.file_format = "PNG"; sc.render.filepath = r"{os.path.join(LB_OUT, 'frames', 'f_')}"
bpy.ops.render.render(animation=True, scene=sc.name)
ed = bpy.data.scenes.new("LB_EDIT"); ed.render.resolution_x, ed.render.resolution_y = 1920, 1080; ed.render.fps = {LB_FPS}
ed.frame_start, ed.frame_end = 1, {LB_F}
se = ed.sequence_editor_create(); coll = se.strips if hasattr(se, "strips") else se.sequences
d = r"{os.path.join(LB_OUT, 'frames')}"; fs = sorted(f for f in os.listdir(d) if f.endswith(".png"))
st = coll.new_image("img", os.path.join(d, fs[0]), 1, 1)
for f in fs[1:]: st.elements.append(f)
ed.render.image_settings.media_type = "VIDEO"; ed.render.image_settings.file_format = "FFMPEG"
ed.render.ffmpeg.format = "MPEG4"; ed.render.ffmpeg.codec = "H264"; ed.render.ffmpeg.constant_rate_factor = "PERC_LOSSLESS"
ed.render.filepath = r"{os.path.join(LB_OUT, 'legend_book_silent.mp4')}"; ed.render.use_sequencer = True
bpy.context.window.scene = ed
bpy.ops.render.render(animation=True, scene=ed.name)
open(r"{os.path.join(LB_OUT, '_done')}", "w").write("ok")
''')
    p = subprocess.Popen([bpy.app.binary_path, '-b', blend, '--python', py], creationflags=0x08000000,
                         stdout=open(os.path.join(LB_OUT, '_render.log'), 'w'), stderr=subprocess.STDOUT)
    return p.pid
