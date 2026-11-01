# Sigil & Spark — the FULL legend intro (~88 s, 8 pages), user 2026-11-01 "let's do the whole intro now".
# Pages 5 + 7 are the approved sample (LEGEND_BOOK frames 1–270 / 271–384, already rendered). This file builds the other
# six as their own scenes (each starts at frame 1, rendered separately, joined + scored afterwards):
#   P1 leg_01  ink writes itself on an empty page; a Spark draws itself line by line and breathes
#   P2 leg_02  three vignettes: a Spark by a lantern, by a boat, curled by a fire — the camera glides across them
#   P3 leg_03  the Rite: a closed Codex with the sigil on an altar, candles, a crowd as bokeh; the Codex opens
#   P4 leg_04  pages wake in gold: one book (1), the next (2), the rare one (3) — the camera dollies along the altar
#   P6 leg_06  a clean, EMPTY Codex in the dark: no light. White masks surface from the dark around it
#   P8 leg_08  a drop of blood falls on the empty page → a gold glyph burns into it → SIGIL & SPARK
# exec order: saga_blender → saga_pages → saga_crimson → sample2d → pilot_book → legend_book → legend_full
import bpy, math, os, random, json, subprocess
from mathutils import Vector

LF_OUT = os.path.join(SRC, 'intro_render', 'legend_full')
FR = {'P1': 270, 'P2': 180, 'P3': 200, 'P4': 486, 'P6': 435, 'P8': 176}
VO_START = {'P1': 19, 'P2': 6, 'P3': 6, 'P4': 8, 'P6': 24, 'P8': 30}   # frame where the line starts inside its page
GOLD = (1.0, 0.70, 0.26)

DRAWINGS2 = {   # name: (model, frames, clip, speed, wash, props)
    'p1':    ('Flying/Alpaking', 120, 'Flying_Idle', 0.6, (0.86, 0.72, 0.62), None),
    'lamp':  ('Flying/Hywirl', 60, 'Flying_Idle', 0.7, (0.86, 0.74, 0.62), 'lamp'),
    'boat':  ('Flying/Glub', 60, 'Flying_Idle', 0.7, (0.78, 0.78, 0.80), 'boat'),
    'fire':  ('Blob/Mushnub', 60, 'Idle', 0.6, (0.86, 0.70, 0.62), 'fire'),
}

def _prop_lamp(pm):
    objs = []
    objs.append(cube('LampBody', (0.28, 0.28, 0.42), (0, 1.55, 0.55), pm, bevel=0.03))
    objs.append(cube('LampTop', (0.36, 0.36, 0.06), (0, 1.55, 0.79), pm, bevel=0.02))
    objs.append(cube('LampBase', (0.36, 0.36, 0.06), (0, 1.55, 0.31), pm, bevel=0.02))
    objs.append(cube('LampPost', (0.06, 0.06, 1.2), (0, 1.55, -0.3), pm))
    return objs

def _prop_boat(pm):
    import bmesh
    me = bpy.data.meshes.new('Hull'); bm = bmesh.new()
    pts = [(-1.0, 0.15), (-0.7, -0.25), (0.7, -0.25), (1.1, 0.2)]
    vs_top, vs_bot = [], []
    for x, z in pts:
        vs_top.append(bm.verts.new((0.35, x + 1.9, z))); vs_bot.append(bm.verts.new((-0.35, x + 1.9, z)))
    for i in range(len(pts) - 1):
        bm.faces.new([vs_top[i], vs_top[i + 1], vs_bot[i + 1], vs_bot[i]])
    bm.to_mesh(me); bm.free()
    h = bpy.data.objects.new('Hull', me); link(h); me.materials.append(pm)
    sol = h.modifiers.new('S', 'SOLIDIFY'); sol.thickness = 0.06
    mast = cube('Mast', (0.05, 0.05, 1.3), (0, 1.9, 0.75), pm)
    sail = plane('Sail', (0.9, 1.0), (0.0, 2.25, 0.85), pm, rot=(math.radians(90), 0, math.radians(90)))
    return [h, mast, sail]

def _prop_fire(pm):
    objs = []
    for i in range(5):
        a = i / 5 * math.pi
        o = cube(f'Log{i}', (0.9, 0.12, 0.12), (0, 1.55, -0.55), pm, bevel=0.03); o.rotation_euler = (0, math.radians(18), a); objs.append(o)
    for i, (dx, s) in enumerate(((0, 0.55), (-0.18, 0.38), (0.2, 0.34))):
        bpy.ops.mesh.primitive_cone_add(vertices=10, radius1=0.2 * s / 0.5, depth=s * 1.6, location=(0, 1.55 + dx, -0.5 + s * 0.8))
        c = bpy.context.active_object; c.name = f'Flame{i}'
        for cc in list(c.users_collection): cc.objects.unlink(c)
        link(c); c.data.materials.append(pm); objs.append(c)
    return objs

def lf_draw_build(names=None):
    """like lb_draw_build, plus simple props drawn with the same pen, framed together with the Spark"""
    meta = {}
    for name in (names or DRAWINGS2):
        rel, nf, clipn, speed, wash, prop = DRAWINGS2[name]
        sc = new_scene('DRAW_' + name, (1024, 1024)); sc.timeline_markers.clear()
        sc.frame_start, sc.frame_end = 1, nf; sc.render.fps = LB_FPS; sc.eevee.taa_render_samples = 16
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
        props = {'lamp': _prop_lamp, 'boat': _prop_boat, 'fire': _prop_fire}[prop](pm) if prop else []
        if props:   # props at the Spark's scale: parent to a pivot beside it and scale up
            piv = bpy.data.objects.new('PropPivot', None); link(piv); piv.location = (0, 1.55, 0.0)
            for o in props:
                if o.parent is None:
                    o.parent = piv; o.location = o.location - Vector((0, 1.55, 0.0))
            piv.scale = (2.3, 2.3, 2.3); piv.location = (0, 2.2, 0.6)
        light('DrawKey', 'SUN', (-2, -7, 7), 1.1, look=(0, 0, 0))
        sc.frame_set(1); bpy.context.view_layer.update()
        mn, mx = model_bounds(b)
        for o in props:
            bpy.context.view_layer.update()
            for c in o.bound_box:
                p = o.matrix_world @ Vector(c); mn = Vector(map(min, mn, p)); mx = Vector(map(max, mx, p))
        cy, cz = (mn.y + mx.y) / 2, (mn.z + mx.z) / 2; size = max(mx.y - mn.y, mx.z - mn.z) * 1.12
        c = cam('DrawCam', (8, cy, cz), (0, cy, cz)); c.data.type = 'ORTHO'; c.data.ortho_scale = size; sc.camera = c
        rnd = random.Random(hash(name) & 0xffff)
        for f in range(1, nf + 1, 2):
            kf(c, 'location', f, (8, cy + rnd.uniform(-1, 1) * size * 0.0025, cz + rnd.uniform(-1, 1) * size * 0.0025))
        _key_const(c)
        meta[name] = {'ortho': size, 'cy': cy, 'cz': cz, 'frames': nf}
    jp = os.path.join(TEX, 'drawings.json'); old = json.load(open(jp)) if os.path.exists(jp) else {}
    old.update(meta); json.dump(old, open(jp, 'w'), indent=1)
    return meta

def lf_draw_render_bg(names=None):
    return lb_draw_render_bg(names or list(DRAWINGS2))

def no_ink(objs):
    """per-SCENE no-Freestyle collection (a shared one dragged other scenes' objects into every page)"""
    sc = bpy.context.scene; nm = 'S_NoInk_' + sc.name
    col = bpy.data.collections.get(nm) or bpy.data.collections.new(nm)
    if col.name not in sc.collection.children: sc.collection.children.link(col)
    for o in objs:
        for c in list(o.users_collection): c.objects.unlink(o)
        col.objects.link(o)
    ls = sc.view_layers[0].freestyle_settings.linesets[0]
    ls.select_by_collection = True; ls.collection = col; ls.collection_negation = 'EXCLUSIVE'

# ------------------------------------------------------------------ shared page-scene setup
def page_scene(name, nf, fade_in=8, fade_out=8, black_extra=None, invert=None):
    sc = new_scene('LF_' + name, (1920, 1080)); sc.timeline_markers.clear()
    for c in list(sc.collection.children): sc.collection.children.unlink(c)
    sc.frame_start, sc.frame_end = 1, nf; sc.render.fps = LB_FPS; sc.frame_step = 1; sc.eevee.taa_render_samples = 32
    try: sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.5
    except Exception: pass
    ink_lines(sc, thick=1.6, color=(0.03, 0.012, 0.01)); world_color(sc, (0.004, 0.0025, 0.002))
    try: sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Punchy'
    except Exception: pass
    tbl = bpy.data.materials.get('LB_Table')
    if not tbl:
        tbl = bpy.data.materials.new('LB_Table'); nt, N, L = _nodes(tbl)
        o_ = N.new('ShaderNodeOutputMaterial'); b_ = N.new('ShaderNodeBsdfPrincipled'); b_.inputs['Base Color'].default_value = (0.05, 0.025, 0.015, 1)
        b_.inputs['Roughness'].default_value = 0.7; L.new(b_.outputs[0], o_.inputs['Surface'])
    plane('Table', (40, 40), (0, 0, -0.06), tbl)
    bk = [(1, 1.0), (1 + fade_in, 0.0), (nf - fade_out, 0.0), (nf, 1.0)] if fade_in else [(1, 0.0), (nf - fade_out, 0.0), (nf, 1.0)]
    if black_extra: bk = black_extra
    return sc, bk

def finish_scene(sc, cam_obj, fx, black_keys, invert_keys=None):
    sc.camera = cam_obj
    no_ink(fx + [o for o in sc.objects if o.name.startswith('Table') or '_Page' in o.name or o.name.startswith(('Crack', 'Glyph', 'Mask'))])
    comp_legend(sc, invert_keys=invert_keys or [(1, 0)], black_keys=black_keys, splat_keys=[(1, 0)])

def dolly(c, keys, look, focus_keys=None, fstop=2.0, shake=0.005, seed=1):
    cam_move(c, keys, look)
    j = bpy.data.objects.new(c.name + '_Jit', None); link(j); c.parent = j
    handheld(j, 1, max(f for f, _ in keys), shake, seed)
    c.data.dof.use_dof = True; c.data.dof.aperture_fstop = fstop
    fo = bpy.data.objects.new(c.name + '_Focus', None); link(fo); c.data.dof.focus_object = fo
    for f, p in (focus_keys or look): kf(fo, 'location', f, p)
    return c

def dpath(n): return os.path.join(TEX, f'draw_{n}', 'd_0001.png')

# ------------------------------------------------------------------ P1: the world was written
def build_p1():
    nf = FR['P1']; meta = json.load(open(os.path.join(TEX, 'drawings.json')))
    sc, bk = page_scene('P1', nf, fade_in=30)
    mats = {-1: m_codex_page('LF_P1_L', 0, (dpath('p1'), meta['p1']['frames']), side=-1, seq_frames=meta['p1']['frames'],
                             reveal_keys=[(1, 0.0), (120, 0.0), (205, 1.0)], script_reveal_keys=[(1, 0.0), (30, 0.0), (125, 1.0)]),
            1: m_codex_page('LF_P1_R', 5, None, side=1, script_reveal_keys=[(1, 0.0), (40, 0.0), (140, 1.0)])}
    root, pages = codex_book('BookP1', (0, 0, 0), 0.0, mats)
    _, fl, _, _ = candle_lit('CandleP1', (1.45, 0.95, -0.06), energy=45.0)
    light('KeyP1', 'AREA', (1.3, 0.7, 0.9), 70.0, (1.0, 0.62, 0.32), size=0.6, look=(-0.4, 0.0, 0.0))
    light('BounceP1', 'AREA', (-1.5, -2.0, 2.5), 10.0, (0.55, 0.6, 0.75), size=2.5, look=(0, 0, 0))
    dust = embers(70, (-1.8, -1.2, 0.1), (1.8, 1.5, 1.4), 1, nf, color=(1.0, 0.82, 0.6), size=0.0035, rise=0.25, seed=51, strength=3.0)
    bpy.context.view_layer.update(); D = decal_world(pages[-1], -1)
    c = cam('CamP1', (0, -1, 1), (0, 0, 0), lens=45)
    dolly(c, [(1, tuple(D + Vector((0.5, -1.2, 1.25)))), (110, tuple(D + Vector((0.25, -1.0, 1.05)))), (nf, tuple(D + Vector((0.04, -0.78, 0.88))))],
          [(1, tuple(D + Vector((0.45, 0.0, 0.0)))), (110, tuple(D + Vector((0.15, 0.0, 0.0)))), (nf, tuple(D))])
    finish_scene(sc, c, [fl] + dust, bk)
    return sc

# ------------------------------------------------------------------ P2: lamps, boats, fires
def build_p2():
    nf = FR['P2']; meta = json.load(open(os.path.join(TEX, 'drawings.json')))
    sc, bk = page_scene('P2', nf)
    vg = lambda n, uv, sz: (dpath(n), meta[n]['frames'], uv, sz)
    mats = {-1: m_codex_page('LF_P2_L', 2, None, side=-1, blank=True, extra=[vg('lamp', (0.5, 0.64), 0.5), vg('boat', (0.5, 0.24), 0.46)]),
            1: m_codex_page('LF_P2_R', 3, None, side=1, blank=True, extra=[vg('fire', (0.5, 0.5), 0.58)])}
    root, pages = codex_book('BookP2', (0, 0, 0), 0.0, mats)
    _, fl, _, _ = candle_lit('CandleP2', (1.55, 1.0, -0.06), energy=45.0)
    light('KeyP2', 'AREA', (1.3, 0.7, 0.9), 65.0, (1.0, 0.62, 0.32), size=0.6, look=(0.0, 0.0, 0.0))
    light('BounceP2', 'AREA', (-1.5, -2.0, 2.5), 10.0, (0.55, 0.6, 0.75), size=2.5, look=(0, 0, 0))
    dust = embers(60, (-1.8, -1.2, 0.1), (1.8, 1.5, 1.2), 1, nf, color=(1.0, 0.82, 0.6), size=0.0035, rise=0.25, seed=52, strength=3.0)
    bpy.context.view_layer.update()
    L = pages[-1].matrix_world; R = pages[1].matrix_world
    lamp = L @ Vector((-0.5, (0.62 - 0.5) * PAGE_H, page_z(0.5))); boat = L @ Vector((-0.5, (0.25 - 0.5) * PAGE_H, page_z(0.5)))
    fire = R @ Vector((0.5, 0.0, page_z(0.5)))
    c = cam('CamP2', (0, -1, 1), (0, 0, 0), lens=50)
    off = Vector((0.05, -0.55, 0.6))
    dolly(c, [(1, tuple(lamp + off)), (55, tuple(lamp + off + Vector((0.05, 0, -0.02)))), (75, tuple(boat + off)), (110, tuple(boat + off + Vector((0.08, 0, 0)))),
              (135, tuple(fire + off)), (nf, tuple(fire + off + Vector((0.05, 0.06, -0.06))))],
          [(1, tuple(lamp)), (55, tuple(lamp)), (75, tuple(boat)), (110, tuple(boat)), (135, tuple(fire)), (nf, tuple(fire))])
    finish_scene(sc, c, [fl] + dust, bk)
    return sc

# ------------------------------------------------------------------ P3: the Rite — a closed Codex on the altar opens
def closed_codex(name, loc, open_keys):
    """closed Codex: leather boards + page block; on the front board a gold sigil ring with three empty sockets;
    the front board swings open on its hinge (open_keys = [(frame, degrees)])"""
    root = bpy.data.objects.new(name, None); link(root); root.location = loc
    W, H, T = PAGE_W, PAGE_H, 0.035
    back = cube(name + '_Back', (W + 0.06, H + 0.08, T), (W / 2, 0, T / 2), m_leather(), bevel=0.012); back.parent = root
    blk = cube(name + '_Block', (W - 0.02, H - 0.03, 0.12), (W / 2, 0, T + 0.06), m_block(), bevel=0.006); blk.parent = root
    spine = cube(name + '_Spine', (0.05, H + 0.08, 0.2), (0.0, 0, 0.1), m_leather(), bevel=0.02); spine.parent = root
    page_mat = m_codex_page(name + '_FirstPage', 6, None, side=1, blank=True)
    pg = make_page(name + '_FirstPage', 1, page_mat); pg.parent = root; pg.location = (0, 0, T + 0.122); pg.scale = (1, 1, 0.2)
    hinge = bpy.data.objects.new(name + '_Hinge', None); link(hinge); hinge.parent = root; hinge.location = (0, 0, 0.19)
    front = cube(name + '_Front', (W + 0.06, H + 0.08, T), (W / 2, 0, T / 2), m_leather(), bevel=0.012); front.parent = hinge
    gold = bpy.data.materials.get('LF_Gold')
    if not gold:
        gold = bpy.data.materials.new('LF_Gold'); nt, N, L = _nodes(gold)
        o_ = N.new('ShaderNodeOutputMaterial'); b_ = N.new('ShaderNodeBsdfPrincipled'); b_.inputs['Base Color'].default_value = (1.0, 0.72, 0.3, 1)
        b_.inputs['Metallic'].default_value = 1.0; b_.inputs['Roughness'].default_value = 0.28; L.new(b_.outputs[0], o_.inputs['Surface'])
    ring = bpy.data.curves.new(name + '_Ring', 'CURVE'); ring.dimensions = '3D'; ring.bevel_depth = 0.008
    sp = ring.splines.new('POLY'); n = 72; sp.points.add(n); R = 0.22
    for i in range(n + 1):
        a = i / n * 2 * math.pi; sp.points[i].co = (W / 2 + R * math.cos(a), R * math.sin(a), T + 0.004, 1)
    ro = bpy.data.objects.new(name + '_RingO', ring); link(ro); ro.parent = hinge; ring.materials.append(gold)
    socks = []
    for k in range(3):
        a = math.pi / 2 + k * 2 * math.pi / 3
        s = sphere(f'{name}_Sock{k}', 0.045, (0, 0, 0), m_leather()); s.parent = hinge
        s.location = (W / 2 + R * math.cos(a), R * math.sin(a), T + 0.006); s.scale = (1, 1, 0.35); socks.append(s)
    q = glyph(name + '_Quill', 7, (W / 2, 0, T + 0.005), 0.22, gold, depth=0.006); q.parent = hinge
    for f, deg in open_keys:
        hinge.rotation_euler = (0, -math.radians(deg), 0); hinge.keyframe_insert('rotation_euler', frame=f)
    return root, hinge, socks, pg

def build_p3():
    nf = FR['P3']
    sc, bk = page_scene('P3', nf)
    stone = bpy.data.materials.new('LF_Stone'); nt, N, L = _nodes(stone)
    o_ = N.new('ShaderNodeOutputMaterial'); b_ = N.new('ShaderNodeBsdfPrincipled'); b_.inputs['Roughness'].default_value = 0.85
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 6; nz.inputs['Detail'].default_value = 10
    cr = N.new('ShaderNodeValToRGB'); cr.color_ramp.elements[0].color = (0.10, 0.09, 0.085, 1); cr.color_ramp.elements[1].color = (0.32, 0.29, 0.26, 1)
    L.new(nz.outputs['Fac'], cr.inputs[0]); L.new(cr.outputs[0], b_.inputs['Base Color'])
    bp = N.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.4; L.new(nz.outputs['Fac'], bp.inputs['Height']); L.new(bp.outputs['Normal'], b_.inputs['Normal'])
    L.new(b_.outputs[0], o_.inputs['Surface'])
    cube('Altar', (3.2, 2.2, 1.0), (0.5, 0.0, -0.56), stone, bevel=0.04)
    cube('AltarStep', (4.2, 3.0, 0.3), (0.5, 0.0, -1.05), stone, bevel=0.03)
    root, hinge, socks, pg = closed_codex('Rite', (0.0, 0.0, -0.06), [(1, 0), (120, 0), (128, 18), (165, 175), (nf, 178)])
    fx = []
    for i, (x, y) in enumerate(((-0.8, 0.7), (1.8, 0.75), (-0.9, -0.75), (1.9, -0.7))):
        _, fl, _, _ = candle_lit(f'CandleP3_{i}', (x, y, -0.06), energy=30.0); fx.append(fl)
    light('KeyP3', 'AREA', (0.5, -1.4, 2.4), 60.0, (1.0, 0.65, 0.35), size=1.0, look=(0.5, 0, 0))
    # warm light pours out of the opening book
    bl = bpy.data.lights.new('BookGlow', 'POINT'); bl.color = (1.0, 0.7, 0.35); bl.shadow_soft_size = 0.4
    bo = bpy.data.objects.new('BookGlow', bl); link(bo); bo.location = (0.5, 0.0, 0.4)
    for f, e in ((1, 0), (126, 0), (150, 45), (nf, 35)): bl.energy = e; bl.keyframe_insert('energy', frame=f)
    # the whole town watching: a sea of out-of-focus lanterns behind the altar
    rnd = random.Random(4); lm = glow('LF_Lantern', (1.0, 0.6, 0.28), 6.0)
    for i in range(140):
        p = (rnd.uniform(-9, 9), rnd.uniform(5, 16), rnd.uniform(-0.6, 1.6))
        o = sphere(f'Crowd{i}', rnd.uniform(0.03, 0.06), p, lm); fx.append(o)
    c = cam('CamP3', (0, -1, 1), (0, 0, 0), lens=40)
    dolly(c, [(1, (1.9, -3.2, 1.3)), (110, (1.3, -2.6, 1.15)), (nf, (0.75, -1.7, 1.6))],
          [(1, (0.5, 0.0, 0.0)), (110, (0.5, 0.0, 0.05)), (nf, (0.5, 0.0, 0.1))],
          focus_keys=[(1, (0.5, 0.0, 0.0)), (nf, (0.5, 0.0, 0.1))], fstop=1.6)
    finish_scene(sc, c, fx, bk)
    return sc

# ------------------------------------------------------------------ P4: one, two… three
def build_p4():
    nf = FR['P4']; meta = json.load(open(os.path.join(TEX, 'drawings.json')))
    sc, bk = page_scene('P4', nf)
    # line timing (leg_04, ~19.5 s): "Most wake a single glowing page…" 0–7 s · "The lucky wake two." 7–9 s ·
    # "Once in a generation… three." 9–13 s · "And the town speaks that name for years. That is how it has always been." 13–19.5 s
    s = VO_START['P4']; t = lambda sec: int(s + sec * LB_FPS)
    books = []
    specs = [  # x, drawings per page (left, right), glow start frames (left, right)
        (-3.4, ('row0', None), (t(0.8), None)),
        (0.0, ('row1', 'row3'), (t(7.2), t(7.9))),
        (3.4, ('row4', 'row2'), (t(9.8), t(10.6))),
    ]
    for i, (x, (dl, dr), (gl, gr)) in enumerate(specs):
        def gk(f0): return [(1, 0.0), (f0, 0.0), (f0 + 14, 1.0)] if f0 else [(1, 0.0)]
        mats = {-1: m_codex_page(f'LF_P4_{i}L', 2 + i, (dpath(dl), 1) if dl else None, side=-1, glow_keys=gk(gl),
                                 reveal_keys=[(1, 0.0), (gl, 0.0), (gl + 20, 1.0)] if gl else [(1, 0.0)]),
                1: m_codex_page(f'LF_P4_{i}R', 3 + i, (dpath(dr), 1) if dr else None, side=1, glow_keys=gk(gr),
                                reveal_keys=[(1, 0.0), (gr, 0.0), (gr + 20, 1.0)] if gr else [(1, 0.0)])}
        r, p = codex_book(f'BookP4_{i}', (x, 0, 0), 0.0, mats); books.append((r, p))
    # the third book: a THIRD page rises out of the block and glows (the rare one)
    g3 = m_codex_page('LF_P4_third', 7, (dpath('row3'), 1), side=1, glow_keys=[(1, 0.0), (t(11.6), 0.0), (t(11.6) + 14, 1.0)],
                      reveal_keys=[(1, 0.0), (t(11.6), 0.0), (t(11.6) + 20, 1.0)])
    third = make_page('ThirdPage', 1, g3); third.parent = books[2][0]; third.location = (0, 0, 0.01)
    for f, deg in ((1, 0), (t(11.0), 0), (t(11.6), -48), (t(12.4), -42)):
        third.rotation_euler = (0, math.radians(deg), 0); third.keyframe_insert('rotation_euler', frame=f)
    key_hide_tree(third, [(1, True), (t(11.0) - 1, True), (t(11.0), False)])
    fx = []
    sparks = embers(50, (3.4 - 1.0, -0.6, 0.1), (3.4 + 1.0, 0.6, 1.0), t(11.6), nf, color=GOLD, size=0.006, rise=1.2, seed=61, strength=10.0)
    fx += sparks
    for i, x in enumerate((-3.4, 0.0, 3.4)):
        _, fl, _, _ = candle_lit(f'CandleP4_{i}', (x + 1.45, 0.95, -0.06), energy=32.0); fx.append(fl)
    light('KeyP4', 'AREA', (0.0, -2.5, 2.6), 80.0, (1.0, 0.65, 0.35), size=2.0, look=(0, 0, 0))
    c = cam('CamP4', (0, -1, 1), (0, 0, 0), lens=45)
    off = Vector((0.0, -1.55, 1.25))
    dolly(c, [(1, tuple(Vector((-3.4, 0, 0)) + off)), (t(6.4), tuple(Vector((-3.25, 0.1, 0)) + off * 0.82)), (t(7.0), tuple(Vector((0.0, 0, 0)) + off)),
              (t(9.0), tuple(Vector((0.1, 0.05, 0)) + off * 0.9)), (t(9.6), tuple(Vector((3.4, 0, 0)) + off)), (t(13.0), tuple(Vector((3.5, 0.0, 0)) + off * 1.05)),
              (nf, (0.0, -6.8, 4.2))],
          [(1, (-3.4, 0, 0)), (t(6.4), (-3.3, 0.05, 0)), (t(7.0), (0, 0, 0)), (t(9.0), (0.05, 0, 0)), (t(9.6), (3.4, 0, 0)), (t(13.0), (3.5, 0.1, 0.1)),
           (nf, (0.0, 0.5, 0.0))], fstop=2.2)
    finish_scene(sc, c, fx, bk)
    return sc

# ------------------------------------------------------------------ P6: the unwritten book, the masks
def build_p6():
    nf = FR['P6']
    sc, bk = page_scene('P6', nf, fade_in=20)
    s = VO_START['P6']; t = lambda sec: int(s + sec * LB_FPS)
    mats = {-1: m_codex_page('LF_P6_L', 0, None, side=-1, blank=True), 1: m_codex_page('LF_P6_R', 0, None, side=1, blank=True)}
    root, pages = codex_book('BookP6', (0, 0, 0), 0.0, mats)
    # one weak, cold light: "no light at all"
    light('MoonP6', 'SPOT', (0.4, -0.8, 3.0), 260.0, (0.7, 0.75, 0.9), size=0.3, look=(0, 0, 0)).data.spot_size = math.radians(45)
    _, fl, lo, sm = candle_lit('CandleP6', (1.45, 0.95, -0.06), out_f=t(9.0), energy=30.0)
    fx = [fl] + sm
    # white masks surface from the dark around the book ("whatever hunts the grey… is hunting it too")
    mimg = os.path.join(TEX, 'mask.png')
    mm = bpy.data.materials.new('LF_Mask'); nt, N, L = _nodes(mm)
    o_ = N.new('ShaderNodeOutputMaterial'); tx = N.new('ShaderNodeTexImage')
    if os.path.exists(mimg): tx.image = bpy.data.images.load(mimg, check_existing=True)
    em = N.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (0.92, 0.92, 0.90, 1)
    tr = N.new('ShaderNodeBsdfTransparent'); mx = N.new('ShaderNodeMixShader')
    fade = N.new('ShaderNodeMath'); fade.operation = 'MULTIPLY'; L.new(tx.outputs['Alpha'], fade.inputs[0])
    keyed_factor(fade.inputs[1], [(1, 0.0), (t(12.0), 0.0), (t(14.5), 1.0)])
    L.new(fade.outputs[0], mx.inputs[0]); L.new(tr.outputs[0], mx.inputs[1]); L.new(em.outputs[0], mx.inputs[2]); L.new(mx.outputs[0], o_.inputs['Surface'])
    keyed_factor(em.inputs['Strength'], [(1, 0.5), (nf, 0.9)])
    try: mm.surface_render_method = 'BLENDED'
    except Exception: pass
    c = cam('CamP6', (0, -1, 1), (0, 0, 0), lens=40)
    for i, (x, y, z, sz) in enumerate(((-1.6, 1.4, 0.35, 0.5), (0.1, 2.0, 0.5, 0.55), (1.7, 1.3, 0.3, 0.46))):
        mo = plane(f'Mask{i}', (sz, sz * 1.3), (x, y, z - 0.25), mm, rot=(math.radians(90), 0, 0)); fx.append(mo)
        kf(mo, 'location', t(12.0), (x, y + 0.6, z - 0.25)); kf(mo, 'location', nf, (x * 0.92, y - 0.2, z))
        tc = mo.constraints.new('TRACK_TO'); tc.target = c; tc.track_axis = 'TRACK_Z'; tc.up_axis = 'UP_Y'
    dolly(c, [(1, (0.6, -2.4, 1.9)), (t(8.0), (0.15, -1.4, 1.2)), (t(11.5), (-0.1, -0.95, 0.85)), (nf, (0.0, -2.2, 1.5))],
          [(1, (0.0, 0.0, 0.0)), (t(8.0), (-0.3, 0.0, 0.0)), (t(11.5), (-0.4, 0.05, 0.0)), (nf, (0.0, 1.0, 0.45))], fstop=4.0)
    finish_scene(sc, c, fx, bk)
    return sc

# ------------------------------------------------------------------ P8: blood → gold glyph → title
def build_p8():
    nf = FR['P8']
    sc, bk = page_scene('P8', nf, fade_in=14, black_extra=None)
    s = VO_START['P8']; t = lambda sec: int(s + sec * LB_FPS)
    DROP = t(2.6); GLY = DROP + 8; TITLE = DROP + 46
    mats = {-1: m_codex_page('LF_P8_L', 0, None, side=-1, blank=True), 1: m_codex_page('LF_P8_R', 0, None, side=1, blank=True)}
    root, pages = codex_book('BookP8', (0, 0, 0), 0.0, mats)
    _, fl, _, _ = candle_lit('CandleP8', (1.45, 0.95, -0.06), energy=36.0)
    light('KeyP8', 'AREA', (1.3, 0.7, 0.9), 55.0, (1.0, 0.62, 0.32), size=0.6, look=(-0.4, 0.0, 0.0))
    bpy.context.view_layer.update(); D = decal_world(pages[-1], -1)
    blood = bpy.data.materials.new('LF_Blood'); nt, N, L = _nodes(blood)
    o_ = N.new('ShaderNodeOutputMaterial'); b_ = N.new('ShaderNodeBsdfPrincipled'); b_.inputs['Base Color'].default_value = (0.35, 0.0, 0.005, 1)
    b_.inputs['Roughness'].default_value = 0.35
    for nm in ('Coat Weight',):
        if nm in b_.inputs: b_.inputs[nm].default_value = 1.0
    L.new(b_.outputs[0], o_.inputs['Surface'])
    drop = sphere('BloodDrop', 0.022, tuple(D + Vector((0, 0, 1.4))), blood); drop.scale = (1, 1, 1.5)
    kf(drop, 'location', DROP - 22, tuple(D + Vector((0, 0, 1.4)))); kf(drop, 'location', DROP, tuple(D + Vector((0, 0, 0.012))))
    try:
        for fc in drop.animation_data.action.fcurves: fc.keyframe_points[-1].interpolation = 'LINEAR'
    except Exception: pass
    kf(drop, 'scale', DROP, (1, 1, 1.5)); kf(drop, 'scale', DROP + 1, (1.8, 1.8, 0.25)); kf(drop, 'scale', DROP + 6, (2.3, 2.3, 0.06))
    kf(drop, 'scale', GLY + 10, (2.3, 2.3, 0.06)); kf(drop, 'scale', GLY + 16, (0, 0, 0))
    splash = embers(14, tuple(D - Vector((0.05, 0.05, 0))), tuple(D + Vector((0.05, 0.05, 0.02))), DROP, DROP + 10, color=(0.4, 0.0, 0.01),
                    size=0.004, rise=0.12, seed=81, strength=1.0)
    # the gold glyph burns into the page where the blood landed
    gm = glow('LF_GlyphGold', (1.0, 0.55, 0.04), 1.0); glow_key(gm, [(1, 0.0), (GLY, 0.0), (GLY + 4, 1.6), (GLY + 18, 1.0), (nf, 0.95)])
    gy = big_glyph('GlyphGold', 13, tuple(D + Vector((0, 0, 0.002))), 0.30, gm, depth=0.0025)
    gy.data.bevel_depth = 0.0042   # a burned stroke, not a fat tube
    write_on(gy, GLY, GLY + 16)
    gl = bpy.data.lights.new('GlyphLight', 'POINT'); gl.color = GOLD; gl.shadow_soft_size = 0.2
    go = bpy.data.objects.new('GlyphLight', gl); link(go); go.location = D + Vector((0, 0, 0.25))
    for f, e in ((1, 0), (GLY, 0), (GLY + 4, 9), (GLY + 20, 4), (nf, 3.5)): gl.energy = e; gl.keyframe_insert('energy', frame=f)
    embs = embers(40, tuple(D - Vector((0.3, 0.3, 0))), tuple(D + Vector((0.3, 0.3, 0.05))), GLY, TITLE - 2, color=(1.0, 0.45, 0.08), size=0.003, rise=0.25, seed=82, strength=2.5)
    # title over black
    tm = glow('LF_TitleW', (1.0, 0.97, 0.92), 3.0)
    c = cam('CamP8', (0, -1, 1), (0, 0, 0), lens=50)
    dolly(c, [(1, tuple(D + Vector((0.1, -0.9, 1.0)))), (DROP, tuple(D + Vector((0.04, -0.6, 0.65)))), (TITLE, tuple(D + Vector((0.0, -0.45, 0.5)))), (nf, tuple(D + Vector((0.0, -0.44, 0.49))))],
          [(1, tuple(D)), (nf, tuple(D))], fstop=2.2, shake=0.003)
    tt = text3d('TitleP8', 'SIGIL  &  SPARK', (0, 0, 0), 0.026, tm, extrude=0.0); tt.parent = c; tt.location = (0, 0.008, -0.5)
    sl = bpy.data.curves.new('TitleSlashP8', 'CURVE'); sl.dimensions = '3D'; sl.bevel_depth = 0.0013; sl.bevel_resolution = 3
    sp = sl.splines.new('BEZIER'); sp.bezier_points.add(2)
    for bp, co, rad in zip(sp.bezier_points, [(-0.088, -0.012, -0.5), (0.0, -0.010, -0.5), (0.092, -0.007, -0.5)], (0.15, 1.0, 0.25)):
        bp.co = co; bp.handle_left_type = bp.handle_right_type = 'AUTO'; bp.radius = rad
    so = bpy.data.objects.new('TitleSlashP8', sl); link(so); so.parent = c; sl.materials.append(glow('LF_Slash', (0.9, 0.04, 0.02), 3.0))
    write_on(so, TITLE + 6, TITLE + 16)
    for o in (tt, so): key_hide_tree(o, [(1, True), (TITLE - 1, True), (TITLE, False)])
    c.data.dof.aperture_fstop = 2.2; c.data.dof.keyframe_insert('aperture_fstop', frame=TITLE - 1)
    c.data.dof.aperture_fstop = 128.0; c.data.dof.keyframe_insert('aperture_fstop', frame=TITLE)   # the title is sharp
    kf(tt, 'scale', TITLE, (0.85, 0.85, 0.85)); kf(tt, 'scale', TITLE + 10, (1.04, 1.04, 1.04)); kf(tt, 'scale', TITLE + 18, (1, 1, 1))
    # behind the title the world goes black (comp black key ramps up right before the title, the title is drawn after?)
    # → the title objects are parented to the camera at 0.5 m; a black card behind them hides the book
    bc = plane('TitleBlack', (2.0, 1.2), (0, 0, -0.52), glow('LF_Black', (0, 0, 0), 1.0)); bc.parent = c
    key_hide_tree(bc, [(1, True), (TITLE - 1, True), (TITLE, False)])
    finish_scene(sc, c, [fl, gy, tt, so, bc] + splash + embs, [(1, 1.0), (14, 0.0), (nf - 4, 0.0), (nf, 1.0)],
                 invert_keys=[(1, 0), (TITLE - 1, 0), (TITLE, 1), (TITLE + 2, 0)])
    return sc

BUILDERS = {'P1': build_p1, 'P2': build_p2, 'P3': build_p3, 'P4': build_p4, 'P6': build_p6, 'P8': build_p8}

def lf_still(page, frames, pct=30):
    sc = bpy.data.scenes['LF_' + page]; bpy.context.window.scene = sc; os.makedirs(LF_OUT, exist_ok=True)
    sc.render.resolution_percentage = pct; sc.render.image_settings.file_format = 'JPEG'; outs = []
    for f in frames:
        sc.frame_set(f); p = os.path.join(LF_OUT, f'st_{page}_{f:04d}.jpg'); sc.render.filepath = p; bpy.ops.render.render(write_still=True); outs.append(p)
    sc.render.image_settings.file_format = 'PNG'; sc.render.resolution_percentage = 100
    return outs

def lf_render_bg(pages):
    """render the given page scenes one after another in ONE background Blender (frames → LF_OUT/<page>/f_####.png)"""
    os.makedirs(LF_OUT, exist_ok=True)
    blend = os.path.join(LF_OUT, 'legend_full.blend'); bpy.ops.wm.save_as_mainfile(filepath=blend, copy=True)
    py = os.path.join(LF_OUT, '_render.py')
    open(py, 'w').write(f'''import bpy, os
for pg in {list(pages)!r}:
    sc = bpy.data.scenes["LF_" + pg]; bpy.context.window.scene = sc
    d = os.path.join(r"{LF_OUT}", pg); os.makedirs(d, exist_ok=True)
    sc.render.image_settings.file_format = "PNG"; sc.render.filepath = os.path.join(d, "f_")
    bpy.ops.render.render(animation=True, scene=sc.name)
    open(os.path.join(d, "_done"), "w").write("ok")
open(os.path.join(r"{LF_OUT}", "_all_done"), "w").write("ok")
''')
    p = subprocess.Popen([bpy.app.binary_path, '-b', blend, '--python', py], creationflags=0x08000000,
                         stdout=open(os.path.join(LF_OUT, '_render.log'), 'w'), stderr=subprocess.STDOUT)
    return p.pid
