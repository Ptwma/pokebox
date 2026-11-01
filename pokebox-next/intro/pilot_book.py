# Sigil & Spark — legend intro v4 PILOT (~16 s): pages 5 → 7 of LEGEND (council 2026-11-01: the whole intro lives on the
# pages of a Codex; creatures are INK drawn on the page, they peel off the paper — never cute 3D bodies in a sky).
#   A (VO leg_05, ~10 s)  "But some books are found grey..." — an ink Spark on a page drains to grey, the page cracks,
#                          a written name fades; pull back: a row of open books, all grey, candles going out
#   B (no VO, ~6 s)        silence → a clean page, an ink beast drawn on it opens a red eye → the page TEARS, the drawing
#                          peels off the paper into a black ink beast (red rim) and lunges at the camera; impact frames
# exec order: saga_blender → saga_pages → saga_crimson → sample2d → pilot_book;  build_pilot(); render_pilot_bg()
import bpy, math, os, random, subprocess
from mathutils import Vector

P_NAME = 'PILOT_BOOK'; P_FPS = 24
P_OUT = os.path.join(SRC, 'intro_render', 'pilot_book')
VO_DIR = os.path.join(SRC, 'audio', 'legend')
FA = 246            # part A length (VO leg_05 = 10.24 s)
FB0 = FA + 1; PF = FA + 140
GREY = (0.42, 0.41, 0.40); PAPER = (0.93, 0.89, 0.80)

def keyed_factor(sock, keys):
    for f, v in keys:
        sock.default_value = v; sock.keyframe_insert('default_value', frame=f)

def m_page(name, drain_keys=None, light=PAPER, stain=(0.62, 0.08, 0.05)):
    """paper with soaked red stains; a keyable 'drain' that turns it to dead grey paper"""
    m = mat_paper(name, light=light, dark=stain, stain=0.35, scale=2.0)
    N, L = m.node_tree.nodes, m.node_tree.links
    em = next(n for n in N if n.type == 'EMISSION'); src = em.inputs['Color'].links[0].from_socket
    bw = N.new('ShaderNodeRGBToBW'); L.new(src, bw.inputs[0])
    gr = N.new('ShaderNodeMix'); gr.data_type = 'RGBA'; gr.blend_type = 'MULTIPLY'; gr.inputs['Factor'].default_value = 1
    cc = N.new('ShaderNodeCombineColor'); L.new(bw.outputs[0], cc.inputs[0]); L.new(bw.outputs[0], cc.inputs[1]); L.new(bw.outputs[0], cc.inputs[2])
    L.new(cc.outputs[0], gr.inputs['A']); gr.inputs['B'].default_value = (0.62, 0.61, 0.60, 1)
    mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; L.new(src, mx.inputs['A']); L.new(gr.outputs['Result'], mx.inputs['B'])
    keyed_factor(mx.inputs['Factor'], drain_keys or [(1, 0.0)])
    L.new(mx.outputs['Result'], em.inputs['Color'])
    return m

def m_ink(name, drain_keys=None, rim=RED, eye=False):
    """ink-black body with a crisp red rim (woodcut); 'drain' fades it to washed-out grey with a dead grey rim"""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    nt, N, L = _nodes(m)
    out = N.new('ShaderNodeOutputMaterial'); em = N.new('ShaderNodeEmission')
    lw = N.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.5
    rt = N.new('ShaderNodeMapRange'); rt.inputs['From Min'].default_value = 0.80; rt.inputs['From Max'].default_value = 0.84
    L.new(lw.outputs['Facing'], rt.inputs['Value'])
    alive = N.new('ShaderNodeMix'); alive.data_type = 'RGBA'; alive.inputs['A'].default_value = (0.008, 0.005, 0.005, 1); alive.inputs['B'].default_value = (*rim, 1)
    L.new(rt.outputs['Result'], alive.inputs['Factor'])
    dead = N.new('ShaderNodeMix'); dead.data_type = 'RGBA'; dead.inputs['A'].default_value = (0.47, 0.46, 0.45, 1); dead.inputs['B'].default_value = (0.70, 0.69, 0.67, 1)
    L.new(rt.outputs['Result'], dead.inputs['Factor'])
    mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; L.new(alive.outputs['Result'], mx.inputs['A']); L.new(dead.outputs['Result'], mx.inputs['B'])
    keyed_factor(mx.inputs['Factor'], drain_keys or [(1, 0.0)])
    L.new(mx.outputs['Result'], em.inputs['Color']); L.new(em.outputs[0], out.inputs['Surface'])
    return m

def m_fade(name, color, keys):
    """flat ink colour whose opacity is keyed (a written name fading off the page)"""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    nt, N, L = _nodes(m)
    out = N.new('ShaderNodeOutputMaterial'); em = N.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (*color, 1)
    tr = N.new('ShaderNodeBsdfTransparent'); mx = N.new('ShaderNodeMixShader')
    L.new(tr.outputs[0], mx.inputs[1]); L.new(em.outputs[0], mx.inputs[2]); keyed_factor(mx.inputs[0], keys)
    L.new(mx.outputs[0], out.inputs['Surface'])
    try: m.surface_render_method = 'BLENDED'
    except Exception: pass
    return m

def book(name, loc, rot_z=0.0, page_mat=None, size=(1.0, 1.4), tilt=7.0):
    """an open Codex: dark leather cover, page blocks, two facing pages slightly V-shaped at the spine"""
    W, H = size
    root = bpy.data.objects.new(name, None); link(root); root.location = loc; root.rotation_euler = (0, 0, rot_z)
    leather = mat_rim('MR_Leather', rim=(0.35, 0.03, 0.02), base=(0.03, 0.008, 0.006), width=0.12)
    cov = cube(name + '_Cover', (W * 2 + 0.12, H + 0.1, 0.03), (0, 0, 0.015), leather, bevel=0.01); cov.parent = root
    pm = page_mat or m_page('MP_' + name)
    pages = []
    for side in (-1, 1):
        blk = cube(f'{name}_Block{side}', (W - 0.02, H - 0.04, 0.06), (side * W / 2, 0, 0.06), m_page('MP_Block', light=(0.80, 0.74, 0.62)), bevel=0.004)
        blk.parent = root
        hinge = bpy.data.objects.new(f'{name}_Hinge{side}', None); link(hinge); hinge.parent = root; hinge.location = (0, 0, 0.095)
        hinge.rotation_euler = (0, math.radians(-tilt * side), 0)
        pg = plane(f'{name}_Page{side}', (W, H), (side * W / 2, 0, 0), pm); pg.parent = hinge
        pages.append((hinge, pg))
    return root, pages

def ink_drawing(rel, parent, loc, scale, name, drain_keys=None, flat=0.035, rot=0.0):
    """a Spark drawn on the page: the real monster model, side view, flattened into the paper, ink material"""
    h, b, arm, acts = rig(rel, scale, name)
    for o in bpy.data.objects:
        if o.parent and (o.parent == b or o.parent.parent == b or (o.parent.parent and o.parent.parent.parent == b)):
            if o.type == 'MESH':
                o.data.materials.clear(); o.data.materials.append(m_ink('MI_' + name, drain_keys))
    h.parent = parent; h.location = loc; h.scale = (1, 1, flat); h.rotation_euler = (0, 0, rot)
    root = next(o for o in bpy.data.objects if o.parent == b)
    root.rotation_mode = 'XYZ'                                # glTF roots import as QUATERNION → euler keys were ignored
    root.rotation_euler = (0, math.radians(-90), 0)          # side view facing up off the page
    return h, b, root, arm, acts

def drawing_mid(b):
    dg = bpy.context.evaluated_depsgraph_get(); pts = []
    for o in bpy.data.objects:
        if o.type == 'MESH' and _is_under(o, b):
            oe = o.evaluated_get(dg); me = oe.to_mesh()
            mw = oe.matrix_world
            vs = me.vertices; pts += [mw @ vs[i].co for i in range(0, len(vs), 7)]
            oe.to_mesh_clear()
    return (sum(pts, Vector()) / len(pts)) if pts else None

def center_drawing(h, b, parent, it=3):
    for _ in range(it):
        bpy.context.view_layer.update()
        mid = drawing_mid(b)
        if mid is None: return
        d = mid - h.matrix_world.translation; d.z = 0
        dl = parent.matrix_world.inverted().to_3x3() @ d
        b.location = (b.location.x - dl.x, b.location.y - dl.y, 0)

def _is_under(o, top):
    p = o.parent
    while p:
        if p == top: return True
        p = p.parent
    return False

def crack(name, parent, seed, center, size, mat, f0, f1):
    """grey cracks writing themselves across a drained page"""
    rnd = random.Random(seed)
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 0.0035
    for s in range(5):
        sp = cu.splines.new('POLY'); n = rnd.randint(4, 7); sp.points.add(n - 1)
        p = Vector((center[0] + rnd.uniform(-size, size) * .3, center[1] + rnd.uniform(-size, size) * .3, 0.004))
        a = rnd.uniform(0, 2 * math.pi)
        for i in range(n):
            sp.points[i].co = (*p, 1); a += rnd.uniform(-0.9, 0.9); p += Vector((math.cos(a), math.sin(a), 0)) * rnd.uniform(.05, .14) * size
    o = bpy.data.objects.new(name, cu); link(o); o.parent = parent; cu.materials.append(mat)
    write_on(o, f0, f1)
    return o

def candle(name, loc, out_f=None):
    wax = mat_rim('MR_Wax', rim=(0.9, 0.75, 0.5), base=(0.25, 0.18, 0.12), width=0.3)
    c = cube(name, (0.06, 0.06, 0.32), (loc[0], loc[1], loc[2] + 0.16), wax, bevel=0.01)
    fl = sphere(name + '_Flame', 0.035, (loc[0], loc[1], loc[2] + 0.36), glow('M_Flame', (1.0, 0.62, 0.25), 6.0))
    fl.scale = (0.7, 0.7, 1.4)
    rnd = random.Random(hash(name) & 0xffff)
    for f in range(1, (out_f or PF) + 1, 3):
        s = rnd.uniform(0.85, 1.15); kf(fl, 'scale', f, (0.7 * s, 0.7 * s, 1.4 * rnd.uniform(0.85, 1.2)))
    if out_f:
        kf(fl, 'scale', out_f + 2, (0, 0, 0))
        embers(6, (loc[0] - .03, loc[1] - .03, loc[2] + .36), (loc[0] + .03, loc[1] + .03, loc[2] + .4), out_f, out_f + 40,
               color=(0.35, 0.33, 0.32), size=0.01, rise=0.5, seed=hash(name) & 0xff, strength=1.0)
    return c, fl

def build_pilot():
    sc = new_scene(P_NAME, (1280, 720))
    sc.timeline_markers.clear()
    for c in list(sc.collection.children): sc.collection.children.unlink(c)
    sc.frame_start, sc.frame_end = 1, PF; sc.render.fps = P_FPS; sc.frame_step = 1
    sc.eevee.taa_render_samples = 16
    ink_lines(sc, thick=2.2, color=(0.03, 0.01, 0.01))
    world_color(sc, (0.006, 0.003, 0.003))
    table = plane('Table', (30, 30), (0, 0, -0.01), mat_rim('MR_Table', rim=(0.12, 0.02, 0.015), base=(0.018, 0.008, 0.006), width=0.05))
    fx = []
    # ---------------- PART A: the hero grey book + a row of grey books
    dk = [(1, 0.0), (30, 0.0), (120, 1.0)]                      # drain: alive → grey while "some books are found grey. Drained."
    root, pages = book('BookA', (0, 0, 0), 0.0, m_page('MP_A', drain_keys=dk))
    (hl, pl), (hr, pr) = pages
    spark, sb, sroot, sarm, sacts = ink_drawing('Flying/Ghost', pl, (0.0, 0.05, 0.004), 0.2, 'InkA', drain_keys=[(1, 0.0), (40, 0.0), (125, 1.0)])
    clip(sarm, sacts, 'Flying_Idle', 1, 80, 0.6)              # it is still breathing on the page… then it stops
    sc.frame_set(20); center_drawing(spark, sb, pl)            # centre on the posed (evaluated) mesh
    for f, v in ((1, 0.035), (90, 0.035), (130, 0.012)): kf(spark, 'scale', f, (1, 1, v))
    crack('CrackA', pl, 3, (0.0, 0.0), 1.0, glow('M_CrackGrey', (0.30, 0.29, 0.28), 1.0), 70, 130)
    crack('CrackB', pr, 5, (0.0, 0.1), 1.0, glow('M_CrackGrey', (0.30, 0.29, 0.28), 1.0), 85, 140)
    # the owner's name on the right page, fading as "no longer sure of their own names"
    nm = text3d('NameA', 'Tomas Hale', (0.0, -0.35, 0.003), 0.11, m_fade('M_Name', (0.05, 0.02, 0.02), [(1, 1.0), (175, 1.0), (225, 0.0)]),
                font=r"C:\Windows\Fonts\segoesc.ttf", extrude=0.0)
    nm.parent = pr; nm.location = (0.0, -0.35, 0.003)
    for i, (x, y, r) in enumerate([(-2.9, 1.6, 0.25), (2.9, 1.9, -0.2), (-5.6, 3.6, 0.35), (5.4, 3.9, -0.3), (0.3, 4.6, 0.05)]):
        rb, rp = book(f'BookRow{i}', (x, y, 0), r, m_page(f'MP_Row{i}', drain_keys=[(1, 1.0)]))
        rh, rbb, _r, _a, _ac = ink_drawing(['Flying/Glub', 'Flying/Hywirl', 'Blob/Mushnub', 'Flying/Squidle', 'Flying/Armabee'][i], rp[i % 2][1],
                    (0.0, 0.05, 0.004), 0.18, f'InkRow{i}', drain_keys=[(1, 1.0)])
        center_drawing(rh, rbb, rp[i % 2][1])
        candle(f'Candle{i}', (x + 1.3, y + 0.9, 0), out_f=150 + i * 14)
    candle('CandleA', (1.35, 0.95, 0), out_f=None)
    # ---------------- PART B: a clean page far from the grey ones; the drawing tears out of it
    rootB, pagesB = book('BookB', (0, -14, 0), 0.0, m_page('MP_B', drain_keys=[(1, 0.0)]))
    (hlB, plB), (hrB, prB) = pagesB
    beast, bb, broot, barm, bacts = ink_drawing('Flying/Dragon', plB, (0.0, 0.0, 0.004), 0.3, 'InkBeast')
    eye = sphere('BeastEye', 0.02, (0, 0, 0), glow('M_Eye', (1.0, 0.05, 0.02), 4.0))
    hb = next((bn.name for bn in barm.data.bones if 'head' in bn.name.lower()), None) if barm else None
    if hb:
        eye.parent = barm; eye.parent_type = 'BONE'; eye.parent_bone = hb; eye.location = (0.0, -0.25, -0.15)
    else:
        eye.parent = broot; eye.location = (0.0, -0.33, 0.62)
    kf(eye, 'scale', FB0, (0, 0, 0)); kf(eye, 'scale', FB0 + 10, (0, 0, 0)); kf(eye, 'scale', FB0 + 13, (1.6, 1.6, 1.6)); kf(eye, 'scale', FB0 + 16, (1, 1, 1))
    T = FB0 + 18   # the tear
    # the left page splits into two halves that rip away from the spine
    pl_mat = plB.data.materials[0]
    plB.hide_render = True; kf(plB, 'hide_render', 1, True)
    for k, (dy, sgn) in enumerate(((0.35, 1), (-0.35, -1))):
        half = plane(f'TearHalf{k}', (1.0, 0.7), (-0.5, dy, 0.002), pl_mat); half.parent = hlB
        kf(half, 'location', T, (-0.5, dy, 0.002)); kf(half, 'rotation_euler', T, (0, 0, 0))
        kf(half, 'location', T + 10, (-0.75, dy + sgn * 0.9, 0.5)); kf(half, 'rotation_euler', T + 10, (math.radians(-70 * sgn), math.radians(25), math.radians(20 * sgn)))
        kf(half, 'location', T + 40, (-1.2, dy + sgn * 2.4, 0.2)); kf(half, 'rotation_euler', T + 40, (math.radians(-150 * sgn), math.radians(40), math.radians(35 * sgn)))
    # the drawing peels off: un-flatten with overshoot, turn to face the camera, lunge
    kf(beast, 'scale', T, (1, 1, 0.035)); kf(beast, 'scale', T + 5, (1, 1, 1.25)); kf(beast, 'scale', T + 9, (1, 1, 0.95)); kf(beast, 'scale', T + 12, (1, 1, 1))
    kf(broot, 'rotation_euler', T, (0, math.radians(-90), 0)); kf(broot, 'rotation_euler', T + 10, (math.radians(-35), 0, 0))
    camB_pos = Vector((0.2, -14 - 3.2, 0.9))
    kf(beast, 'location', T, (0.0, 0.0, 0.004)); kf(beast, 'location', T + 12, (0.1, -0.3, 0.6))
    kf(beast, 'location', T + 45, (0.5, -1.8, 0.85)); kf(beast, 'location', PF - 10, (0.75, -3.05, 0.95))
    clip(barm, bacts, 'Headbutt', T, T + 24, 1.0); clip(barm, bacts, 'Fast_Flying', T + 22, PF, 1.4)
    sc.frame_set(FB0 + 2); center_drawing(beast, bb, plB)
    # ink splash
    sp = embers(70, (-1.0, -14.6, 0.05), (0.2, -13.4, 0.4), T, T + 30, color=(0.01, 0.005, 0.005), size=0.022, rise=1.4, seed=31, strength=1.0)
    rd = embers(40, (-1.0, -14.6, 0.05), (0.2, -13.4, 0.4), T, T + 34, color=(0.85, 0.05, 0.03), size=0.012, rise=1.8, seed=32, strength=6.0)
    fx += sp + rd + [eye]
    # ---------------- cameras
    cA = cam('CamA', (-0.5, -0.2, 2.1), (-0.5, 0.05, 0), lens=40)
    cam_move(cA, [(1, (-0.55, -0.25, 1.55)), (120, (-0.35, -0.6, 1.25)), (150, (0.2, -1.6, 1.4)), (FA, (0.3, -4.6, 3.2))],
             [(1, (-0.5, 0.05, 0.0)), (120, (-0.3, 0.0, 0.0)), (150, (0.3, -0.3, 0.0)), (FA, (0.3, 2.0, 0.0))])
    cB = cam('CamB', tuple(camB_pos), (-0.5, -14, 0.1), lens=30)
    tB = cam_move(cB, [(FB0, (-0.5, -14 - 1.2, 1.1)), (T, (-0.45, -14 - 1.35, 1.0)), (T + 14, tuple(camB_pos)), (PF, tuple(camB_pos + Vector((0, -0.4, 0.05))))],
                  [(FB0, (-0.5, -14, 0.02)), (T, (-0.5, -14, 0.05)), (T + 14, (-0.4, -14.3, 0.6)), (PF, (0.2, -16.4, 0.95))])
    jit = bpy.data.objects.new('CamB_Jit', None); link(jit); cB.parent = jit
    rj = random.Random(9)
    kf(jit, 'location', T - 1, (0, 0, 0))
    for f in range(T, T + 26, 2):
        a = 0.09 * (1 - (f - T) / 26); kf(jit, 'location', f, (rj.uniform(-a, a), rj.uniform(-a, a), rj.uniform(-a, a)))
    kf(jit, 'location', T + 26, (0, 0, 0))
    for f in range(PF - 14, PF, 2):
        a = 0.05; kf(jit, 'location', f, (rj.uniform(-a, a), rj.uniform(-a, a), rj.uniform(-a, a)))
    for f, c in ((1, cA), (FB0, cB)):
        mk = sc.timeline_markers.new(f'cut{f}', frame=f); mk.camera = c
    sc.camera = cA
    fx += speed_lines_ring(cB, T + 2, PF, 45, 7, color=(0.75, 0.04, 0.03))
    no_ink(fx + [o for o in sc.objects if o.name.endswith('_Flame')])
    comp_sample(sc, [(1, 0), (T - 1, 0), (T, 1), (T + 2, 0), (PF - 3, 0), (PF - 2, 1), (PF, 1)], vignette=0.75)
    return sc

def render_pilot_bg():
    blend = os.path.join(P_OUT, 'pilot_book.blend'); os.makedirs(os.path.join(P_OUT, 'frames'), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=blend, copy=True)
    vo = os.path.join(VO_DIR, 'vo_leg_05.wav')
    mus = os.path.join(MUSIC, 'gregor_quendel_-_cinematic_trailer_music_-_13_-_cinematic_epic_hybrid_riser.mp3')
    py = os.path.join(P_OUT, '_render.py')
    open(py, 'w').write(f'''import bpy, os
sc = bpy.data.scenes["{P_NAME}"]; bpy.context.window.scene = sc
sc.render.image_settings.file_format = "PNG"; sc.render.filepath = r"{os.path.join(P_OUT, 'frames', 'f_')}"
bpy.ops.render.render(animation=True, scene=sc.name)
ed = bpy.data.scenes.new("P_EDIT"); ed.render.resolution_x, ed.render.resolution_y = 1280, 720; ed.render.fps = {P_FPS}
ed.frame_start, ed.frame_end = 1, {PF}
se = ed.sequence_editor_create(); coll = se.strips if hasattr(se, "strips") else se.sequences
d = r"{os.path.join(P_OUT, 'frames')}"; fs = sorted(f for f in os.listdir(d) if f.endswith(".png"))
st = coll.new_image("img", os.path.join(d, fs[0]), 1, 1)
for f in fs[1:]: st.elements.append(f)
v = coll.new_sound("vo", r"{vo}", 2, 1); v.volume = 1.0
if os.path.exists(r"{mus}"):
    m = coll.new_sound("mus", r"{mus}", 3, {FB0 - 24}); m.volume = 0.7
ed.render.image_settings.media_type = "VIDEO"; ed.render.image_settings.file_format = "FFMPEG"
ed.render.ffmpeg.format = "MPEG4"; ed.render.ffmpeg.codec = "H264"; ed.render.ffmpeg.constant_rate_factor = "HIGH"; ed.render.ffmpeg.audio_codec = "AAC"
ed.render.filepath = r"{os.path.join(P_OUT, 'pilot_book.mp4')}"; ed.render.use_sequencer = True
bpy.context.window.scene = ed
bpy.ops.render.render(animation=True, scene=ed.name)
open(r"{os.path.join(P_OUT, '_done')}", "w").write("ok")
''')
    p = subprocess.Popen([bpy.app.binary_path, '-b', blend, '--python', py], creationflags=0x08000000,
                         stdout=open(os.path.join(P_OUT, '_render.log'), 'w'), stderr=subprocess.STDOUT)
    return p.pid
