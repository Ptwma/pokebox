# Sigil & Spark — the title screen background (user 2026-11-01: "not the map behind the menu, make something nice in
# Blender"): a 10 s seamless loop in the legend intro's look — an open Codex on a dark desk by candlelight; the left page
# carries a living pen-and-ink Spark, the right page is UNWRITTEN (the hero's book) and breathes a faint gold; dust in the
# light, an ink pot and a quill, the camera drifting on a closed circle (so the loop has no seam).
# exec order: saga_blender → saga_pages → saga_crimson → sample2d → pilot_book → legend_book → legend_full → title_loop
#   tl_build(); tl_still([1, 120]); tl_render_bg()   → TL_OUT/title_loop.mp4 → Content/Movies/title_loop.mp4
import bpy, math, os, json, subprocess
from mathutils import Vector

TL_OUT = os.path.join(SRC, 'intro_render', 'title_loop')
TL_F = 240

def _glossy_ink(name='TL_InkPot'):
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); nt, N, L = _nodes(m)
    o = N.new('ShaderNodeOutputMaterial'); b = N.new('ShaderNodeBsdfPrincipled')
    b.inputs['Base Color'].default_value = (0.01, 0.012, 0.02, 1); b.inputs['Roughness'].default_value = 0.12
    L.new(b.outputs[0], o.inputs['Surface']); return m

def _quill_mat(name='TL_Quill'):
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); nt, N, L = _nodes(m)
    o = N.new('ShaderNodeOutputMaterial'); b = N.new('ShaderNodeBsdfPrincipled')
    b.inputs['Base Color'].default_value = (0.78, 0.72, 0.62, 1); b.inputs['Roughness'].default_value = 0.6
    L.new(b.outputs[0], o.inputs['Surface']); return m

def tl_build():
    meta = json.load(open(os.path.join(TEX, 'drawings.json')))
    sc, _ = page_scene('TITLE', TL_F, fade_in=0, fade_out=0, black_extra=[(1, 0.0)])
    nf_p1 = meta['p1']['frames']
    mats = {-1: m_codex_page('TL_Page_L', 0, (dpath('p1'), nf_p1), side=-1, seq_frames=nf_p1,
                             glow_keys=[(1, 0.0), (120, 0.10), (TL_F, 0.0)]),
            1: m_codex_page('TL_Page_R', 5, None, side=1, blank=True, glow_keys=[(1, 0.04), (120, 0.22), (TL_F, 0.04)])}
    root, pages = codex_book('BookTL', (0, 0, 0), math.radians(-8), mats)
    _, fl1, _, _ = candle_lit('CandleTL1', (1.55, 0.85, -0.06), out_f=None, energy=45.0)
    _, fl2, _, _ = candle_lit('CandleTL2', (-1.75, 1.15, -0.06), out_f=None, energy=22.0)
    light('KeyTL', 'AREA', (1.3, 0.6, 0.9), 70.0, (1.0, 0.62, 0.32), size=0.6, look=(-0.3, 0.0, 0.0))
    light('BounceTL', 'AREA', (-1.5, -2.0, 2.5), 9.0, (0.55, 0.6, 0.75), size=2.5, look=(0, 0, 0))
    # an ink pot and a quill resting in it (right of the book)
    pot = cube('TL_Pot', (0.16, 0.16, 0.13), (0.95, -0.95, 0.005), _glossy_ink(), bevel=0.05)
    q = cube('TL_Quill', (0.012, 0.012, 0.62), (0.95, -0.95, 0.30), _quill_mat(), bevel=0.004)
    q.rotation_euler = (math.radians(24), math.radians(-18), 0)
    vane = cube('TL_Vane', (0.05, 0.004, 0.34), (0.95 + 0.06, -0.95 + 0.11, 0.47), _quill_mat(), bevel=0.002)
    vane.rotation_euler = (math.radians(24), math.radians(-18), 0)
    dust = embers(80, (-1.8, -1.2, 0.1), (1.8, 1.5, 1.4), 1, TL_F, color=(1.0, 0.82, 0.6), size=0.0022, rise=0.18, seed=61, strength=1.4)
    bpy.context.view_layer.update()
    C = Vector((0.0, 0.05, 0.02))
    c = cam('CamTL', (0, -1, 1), (0, 0, 0), lens=38)
    # the camera drifts on a small closed circle → the 240-frame loop has no seam
    keys, look = [], []
    for k in range(9):
        f = 1 + round(k * (TL_F - 1) / 8); a = 2 * math.pi * k / 8
        keys.append((f, tuple(C + Vector((0.18 * math.sin(a), -2.35 + 0.08 * math.cos(a), 1.95 + 0.05 * math.sin(2 * a))))))
        look.append((f, tuple(C + Vector((0.05 * math.sin(a + 0.6), 0.25, 0.0)))))
    dolly(c, keys, look, fstop=2.8, shake=0.0)
    finish_scene(sc, c, [fl1, fl2] + dust, [(1, 0.0)])
    return sc

def tl_still(frames, pct=50):
    sc = bpy.data.scenes['LF_TITLE']; bpy.context.window.scene = sc; os.makedirs(TL_OUT, exist_ok=True)
    sc.render.resolution_percentage = pct; fmt = sc.render.image_settings.file_format; sc.render.image_settings.file_format = 'JPEG'
    outs = []
    for f in frames:
        sc.frame_set(f); p = os.path.join(TL_OUT, f'st_{f:04d}.jpg'); sc.render.filepath = p; bpy.ops.render.render(write_still=True); outs.append(p)
    sc.render.image_settings.file_format = fmt; sc.render.resolution_percentage = 100
    return outs

def tl_render_bg():
    os.makedirs(os.path.join(TL_OUT, 'frames'), exist_ok=True)
    blend = os.path.join(TL_OUT, 'title_loop.blend'); bpy.ops.wm.save_as_mainfile(filepath=blend, copy=True)
    py = os.path.join(TL_OUT, '_render.py')
    open(py, 'w').write(f'''import bpy, os
sc = bpy.data.scenes["LF_TITLE"]; bpy.context.window.scene = sc
sc.render.image_settings.file_format = "PNG"; sc.render.filepath = r"{os.path.join(TL_OUT, 'frames', 'f_')}"
bpy.ops.render.render(animation=True, scene=sc.name)
ed = bpy.data.scenes.new("TL_EDIT"); ed.render.resolution_x, ed.render.resolution_y = 1920, 1080; ed.render.fps = 24
ed.frame_start, ed.frame_end = 1, {TL_F}
se = ed.sequence_editor_create(); coll = se.strips if hasattr(se, "strips") else se.sequences
d = r"{os.path.join(TL_OUT, 'frames')}"; fs = sorted(f for f in os.listdir(d) if f.endswith(".png"))
st = coll.new_image("img", os.path.join(d, fs[0]), 1, 1)
for f in fs[1:]: st.elements.append(f)
ed.render.image_settings.media_type = "VIDEO"; ed.render.image_settings.file_format = "FFMPEG"
ed.render.ffmpeg.format = "MPEG4"; ed.render.ffmpeg.codec = "H264"; ed.render.ffmpeg.constant_rate_factor = "HIGH"
ed.render.filepath = r"{os.path.join(TL_OUT, 'title_loop.mp4')}"; ed.render.use_sequencer = True
bpy.context.window.scene = ed
bpy.ops.render.render(animation=True, scene=ed.name)
open(r"{os.path.join(TL_OUT, '_done')}", "w").write("ok")
''')
    p = subprocess.Popen([bpy.app.binary_path, '-b', blend, '--python', py], creationflags=0x08000000,
                         stdout=open(os.path.join(TL_OUT, '_render.log'), 'w'), stderr=subprocess.STDOUT)
    return p.pid
