# Sigil & Spark — intro v4 "CRIMSON": the saga told like a dark anime legend (user 2026-11-01: red, black, white,
# dark theme, one burst of action, a narrated trailer, the spirit of an anime grimoire-legend cold open; very detailed).
# Style: black silhouettes with razor white/red rim light (woodcut look), painted crimson skies with a huge pale sun,
# white-hot glyphs, ink splatter + paper grain, chromatic aberration, impact frames, speed lines, fast cuts in the action.
# exec order inside Blender: saga_blender.py → saga_pages.py → saga_crimson.py   (this file overrides the pages)
import bpy, math, os, random
from mathutils import Vector

RED = (0.78, 0.04, 0.03); BLOOD = (0.42, 0.0, 0.01); WHITE = (1.0, 0.97, 0.92); HOT = (1.0, 0.86, 0.62); BLACK = (0.006, 0.004, 0.004)

# ------------------------------------------------------------------ materials
def mat_rim(name='MR_Black', rim=WHITE, base=BLACK, mid=None, width=0.22, light_band=0.0):
    """woodcut silhouette: flat black body, crisp rim line where the surface turns away from the camera,
    optional dark-red band on the lit side (3-tone graphic look)"""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    nt, N, L = _nodes(m)
    out = N.new('ShaderNodeOutputMaterial'); em = N.new('ShaderNodeEmission'); em.inputs['Strength'].default_value = 1.0
    lw = N.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.5
    rim_t = N.new('ShaderNodeMapRange'); rim_t.inputs['From Min'].default_value = 1 - width; rim_t.inputs['From Max'].default_value = 1 - width + 0.04
    L.new(lw.outputs['Facing'], rim_t.inputs['Value'])
    col = N.new('ShaderNodeMix'); col.data_type = 'RGBA'; col.inputs['A'].default_value = (*base, 1); col.inputs['B'].default_value = (*rim, 1)
    L.new(rim_t.outputs['Result'], col.inputs['Factor'])
    src = col.outputs['Result']
    if light_band > 0:
        dif = N.new('ShaderNodeBsdfDiffuse'); s2r = N.new('ShaderNodeShaderToRGB'); L.new(dif.outputs[0], s2r.inputs[0])
        bw = N.new('ShaderNodeRGBToBW'); L.new(s2r.outputs[0], bw.inputs[0])
        lt = N.new('ShaderNodeMapRange'); lt.inputs['From Min'].default_value = light_band; lt.inputs['From Max'].default_value = light_band + 0.02
        L.new(bw.outputs[0], lt.inputs['Value'])
        mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs['B'].default_value = (*(mid or (0.25, 0.01, 0.01)), 1)
        L.new(lt.outputs['Result'], mx.inputs['Factor']); mx.inputs['A'].default_value = (*base, 1)
        mx2 = N.new('ShaderNodeMix'); mx2.data_type = 'RGBA'; L.new(rim_t.outputs['Result'], mx2.inputs['Factor'])
        L.new(mx.outputs['Result'], mx2.inputs['A']); mx2.inputs['B'].default_value = (*rim, 1)
        src = mx2.outputs['Result']
    L.new(src, em.inputs['Color']); L.new(em.outputs[0], out.inputs['Surface'])
    return m

def mat_paper(name, light=(0.92, 0.88, 0.80), dark=(0.55, 0.05, 0.04), stain=0.55, scale=2.5):
    """painted paper: light ground with blotchy wash of `dark` (red ink soaking through)"""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    nt, N, L = _nodes(m)
    out = N.new('ShaderNodeOutputMaterial'); em = N.new('ShaderNodeEmission')
    tc = N.new('ShaderNodeTexCoord'); nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = scale; nz.inputs['Detail'].default_value = 10
    nz.inputs['Roughness'].default_value = 0.65
    L.new(tc.outputs['UV'], nz.inputs['Vector'])
    fb = N.new('ShaderNodeTexNoise'); fb.inputs['Scale'].default_value = 140; L.new(tc.outputs['UV'], fb.inputs['Vector'])
    mr = N.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 0.5 - stain * 0.2; mr.inputs['From Max'].default_value = 0.72
    L.new(nz.outputs['Fac'], mr.inputs['Value'])
    mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs['A'].default_value = (*light, 1); mx.inputs['B'].default_value = (*dark, 1)
    L.new(mr.outputs['Result'], mx.inputs['Factor'])
    gm = N.new('ShaderNodeMapRange'); gm.inputs['To Min'].default_value = 0.86; L.new(fb.outputs['Fac'], gm.inputs['Value'])
    mul = N.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 1
    L.new(mx.outputs['Result'], mul.inputs['A']); L.new(gm.outputs['Result'], mul.inputs['B'])
    L.new(mul.outputs['Result'], em.inputs['Color']); L.new(em.outputs[0], out.inputs['Surface'])
    return m

def mat_streak_sea(name, col_a=(0.10, 0.0, 0.0), col_b=(0.85, 0.12, 0.05), sun_x=0.0):
    """sea as horizontal brush streaks of reflected red (stretched noise)"""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    nt, N, L = _nodes(m)
    out = N.new('ShaderNodeOutputMaterial'); em = N.new('ShaderNodeEmission')
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (0.08, 3.0, 1)
    L.new(tc.outputs['Object'], mp.inputs['Vector'])
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 1.6; nz.inputs['Detail'].default_value = 8; L.new(mp.outputs[0], nz.inputs['Vector'])
    cr = N.new('ShaderNodeValToRGB'); r = cr.color_ramp; r.interpolation = 'CONSTANT'
    r.elements[0].color = (*col_a, 1); r.elements[1].position = 0.62; r.elements[1].color = (*col_b, 1)
    e = r.elements.new(0.55); e.color = (col_a[0] * 3 + .05, col_a[1], col_a[2], 1)
    L.new(nz.outputs['Fac'], cr.inputs['Fac'])
    L.new(cr.outputs['Color'], em.inputs['Color']); L.new(em.outputs[0], out.inputs['Surface'])
    return m

def mat_speedlines(name='MR_Speed', color=(0.0, 0.0, 0.0), n=90.0, inner=0.22):
    """radial anime speed lines on a camera-facing plane (transparent centre)"""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    nt, N, L = _nodes(m)
    out = N.new('ShaderNodeOutputMaterial'); em = N.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (*color, 1)
    tr = N.new('ShaderNodeBsdfTransparent'); mix = N.new('ShaderNodeMixShader')
    tc = N.new('ShaderNodeTexCoord'); sep = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['UV'], sep.inputs[0])
    sx = N.new('ShaderNodeMath'); sx.operation = 'SUBTRACT'; sx.inputs[1].default_value = .5; L.new(sep.outputs['X'], sx.inputs[0])
    sy = N.new('ShaderNodeMath'); sy.operation = 'SUBTRACT'; sy.inputs[1].default_value = .5; L.new(sep.outputs['Y'], sy.inputs[0])
    at = N.new('ShaderNodeMath'); at.operation = 'ARCTAN2'; L.new(sy.outputs[0], at.inputs[0]); L.new(sx.outputs[0], at.inputs[1])
    ln = N.new('ShaderNodeMath'); ln.operation = 'MULTIPLY'; ln.inputs[1].default_value = n; L.new(at.outputs[0], ln.inputs[0])
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 1.0; nz.noise_dimensions = '1D' if hasattr(nz, 'noise_dimensions') else None
    L.new(ln.outputs[0], nz.inputs['W']) if 'W' in nz.inputs else None
    th = N.new('ShaderNodeMath'); th.operation = 'GREATER_THAN'; th.inputs[1].default_value = 0.58; L.new(nz.outputs['Fac'], th.inputs[0])
    vl = N.new('ShaderNodeVectorMath'); vl.operation = 'LENGTH'
    cb = N.new('ShaderNodeCombineXYZ'); L.new(sx.outputs[0], cb.inputs['X']); L.new(sy.outputs[0], cb.inputs['Y']); L.new(cb.outputs[0], vl.inputs[0])
    rad = N.new('ShaderNodeMapRange'); rad.inputs['From Min'].default_value = inner; rad.inputs['From Max'].default_value = inner + .25
    L.new(vl.outputs['Value'], rad.inputs['Value'])
    mk = N.new('ShaderNodeMath'); mk.operation = 'MULTIPLY'; L.new(th.outputs[0], mk.inputs[0]); L.new(rad.outputs['Result'], mk.inputs[1])
    L.new(mk.outputs[0], mix.inputs[0]); L.new(tr.outputs[0], mix.inputs[1]); L.new(em.outputs[0], mix.inputs[2]); L.new(mix.outputs[0], out.inputs['Surface'])
    try: m.surface_render_method = 'BLENDED'
    except Exception: pass
    return m

def crimson_sky(sc, top=(0.02, 0.0, 0.0), mid=(0.45, 0.02, 0.02), horizon=(1.0, 0.32, 0.12), sun_dir=(0.0, 1.0, 0.12),
                sun_r=0.07, sun_col=(1.0, 0.95, 0.85), strength=1.0, streaks=0.5):
    """world shader: black zenith → blood red → burning horizon, painted streaks, a huge pale sun / moon disc with a halo"""
    w = bpy.data.worlds.new('Sky_' + sc.name); w.use_nodes = True; sc.world = w
    N, L = w.node_tree.nodes, w.node_tree.links
    for n in list(N): N.remove(n)
    out = N.new('ShaderNodeOutputWorld'); bg = N.new('ShaderNodeBackground'); bg.inputs['Strength'].default_value = strength
    tc = N.new('ShaderNodeTexCoord'); sep = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Generated'], sep.inputs[0])
    nm = N.new('ShaderNodeVectorMath'); nm.operation = 'NORMALIZE'; L.new(tc.outputs['Generated'], nm.inputs[0])
    sz = N.new('ShaderNodeSeparateXYZ'); L.new(nm.outputs[0], sz.inputs[0])
    mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1.2, 1.2, 9.0); L.new(nm.outputs[0], mp.inputs['Vector'])
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 2.5; nz.inputs['Detail'].default_value = 7; L.new(mp.outputs[0], nz.inputs['Vector'])
    ad = N.new('ShaderNodeMath'); ad.operation = 'MULTIPLY_ADD'; ad.inputs[1].default_value = streaks * 0.25
    L.new(nz.outputs['Fac'], ad.inputs[0]); L.new(sz.outputs['Z'], ad.inputs[2])
    cr = N.new('ShaderNodeValToRGB'); r = cr.color_ramp
    r.elements[0].position = 0.0; r.elements[0].color = (*horizon, 1)
    e1 = r.elements.new(0.12); e1.color = (*mid, 1)
    r.elements[-1].position = 0.55; r.elements[-1].color = (*top, 1)
    L.new(ad.outputs[0], cr.inputs['Fac'])
    sd = Vector(sun_dir).normalized()
    dp = N.new('ShaderNodeVectorMath'); dp.operation = 'DOT_PRODUCT'; dp.inputs[1].default_value = sd; L.new(nm.outputs[0], dp.inputs[0])
    disc = N.new('ShaderNodeMapRange'); disc.inputs['From Min'].default_value = math.cos(sun_r) - 0.0008; disc.inputs['From Max'].default_value = math.cos(sun_r)
    L.new(dp.outputs['Value'], disc.inputs['Value'])
    halo = N.new('ShaderNodeMapRange'); halo.inputs['From Min'].default_value = math.cos(sun_r * 6); halo.inputs['From Max'].default_value = 1.0
    halo.interpolation_type = 'SMOOTHERSTEP'; L.new(dp.outputs['Value'], halo.inputs['Value'])
    hm = N.new('ShaderNodeMix'); hm.data_type = 'RGBA'; hm.blend_type = 'SCREEN'; L.new(halo.outputs['Result'], hm.inputs['Factor'])
    L.new(cr.outputs['Color'], hm.inputs['A']); hm.inputs['B'].default_value = (*horizon, 1)
    dm = N.new('ShaderNodeMix'); dm.data_type = 'RGBA'; L.new(disc.outputs['Result'], dm.inputs['Factor'])
    L.new(hm.outputs['Result'], dm.inputs['A']); dm.inputs['B'].default_value = (*sun_col, 1)
    L.new(dm.outputs['Result'], bg.inputs['Color']); L.new(bg.outputs[0], out.inputs['Surface'])
    return w

def splatter_image(name='SagaSplatter', w=1600, h=900, seed=5):
    """a torn, dark ink border (noise-roughened) + fine ink spray clustered in two corners — white = clear
    (r63 lesson: big round splats read as dirt on the lens, not ink)"""
    img = bpy.data.images.get(name)
    if img: return img
    import numpy as np
    rng = np.random.default_rng(seed)
    def octave(sc):
        g = rng.random((h // sc + 2, w // sc + 2))
        yi = np.linspace(0, g.shape[0] - 1.001, h); xi = np.linspace(0, g.shape[1] - 1.001, w)
        y0 = yi.astype(int); x0 = xi.astype(int); fy = (yi - y0)[:, None]; fx = (xi - x0)[None, :]
        a = g[y0][:, x0]; b = g[y0][:, x0 + 1]; c = g[y0 + 1][:, x0]; d = g[y0 + 1][:, x0 + 1]
        return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    n = octave(60) * .55 + octave(18) * .3 + octave(5) * .15
    dx = np.minimum(xx, w - 1 - xx) / w; dy = np.minimum(yy, h - 1 - yy) / h
    dist = np.minimum(dx * 1.0, dy * 1.6)                       # distance to the frame edge
    border = np.clip((dist - 0.006 - n * 0.03) / 0.012, 0, 1)   # torn edge, ~1–4 % of the frame
    v = 0.25 + 0.75 * border
    for (cx, cy) in ((w * 0.04, h * 0.06), (w * 0.96, h * 0.93)):
        for _ in range(140):
            r = rng.gamma(1.2, 1.2) + 0.6
            px = cx + rng.normal(0, w * 0.06); py = cy + rng.normal(0, h * 0.07)
            x0, x1 = int(max(0, px - r - 1)), int(min(w, px + r + 2)); y0, y1 = int(max(0, py - r - 1)), int(min(h, py + r + 2))
            if x0 >= x1 or y0 >= y1: continue
            m = (xx[y0:y1, x0:x1] - px) ** 2 + (yy[y0:y1, x0:x1] - py) ** 2 < r * r
            v[y0:y1, x0:x1][m] = np.minimum(v[y0:y1, x0:x1][m], 0.18)
    grain = (rng.random((h, w)) * 0.06 + 0.94).astype(np.float32)
    v = (v * grain).astype(np.float32)
    rgba = np.stack([v, v * 0.97, v * 0.94, np.ones_like(v)], -1).astype(np.float32)
    img = bpy.data.images.new(name, w, h, alpha=True, float_buffer=True)
    img.pixels.foreach_set(rgba[::-1].ravel()); img.pack()
    return img

def comp_crimson(sc, kuwa=3, bloom=0.9, contrast=1.15, splatter=1.0, aberr=0.012, vignette=0.75, invert_keys=None):
    """crimson grade: light paint filter, ink splatter frame, bloom, contrast, chromatic aberration, black vignette,
    optional impact frames (Invert factor keyed per frame)"""
    ng = bpy.data.node_groups.new('CompC_' + sc.name, 'CompositorNodeTree')
    ng.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
    N, L = ng.nodes, ng.links
    rl = N.new('CompositorNodeRLayers'); rl.scene = sc
    src = rl.outputs['Image']
    if kuwa:
        ku = N.new('CompositorNodeKuwahara'); ku.inputs['Size'].default_value = kuwa
        try: ku.inputs['Type'].default_value = 'Anisotropic'
        except Exception: pass
        L.new(src, ku.inputs['Image']); src = ku.outputs['Image']
    gl = N.new('CompositorNodeGlare')
    for v in ('Bloom', 'Fog Glow'):
        try: gl.inputs['Type'].default_value = v; break
        except Exception: pass
    for nm, v in (('Threshold', 0.8), ('Strength', bloom), ('Size', 0.8)):
        if nm in gl.inputs: gl.inputs[nm].default_value = v
    L.new(src, gl.inputs['Image']); src = gl.outputs['Image']
    cv = N.new('CompositorNodeCurveRGB')
    try:
        c = cv.mapping.curves[3]; c.points[0].location = (0.0, 0.0); c.points[-1].location = (1.0, 1.0)
        c.points.new(0.25, 0.25 / contrast); c.points.new(0.75, min(1, 0.75 * contrast)); cv.mapping.update()
    except Exception: pass
    L.new(src, cv.inputs['Image']); src = cv.outputs['Image']
    pi = N.new('CompositorNodeImage'); pi.image = splatter_image()
    mul = N.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = splatter
    L.new(src, mul.inputs['A']); L.new(pi.outputs['Image'], mul.inputs['B']); src = mul.outputs['Result']
    ld = N.new('CompositorNodeLensdist')
    if 'Dispersion' in ld.inputs: ld.inputs['Dispersion'].default_value = aberr
    L.new(src, ld.inputs['Image']); src = ld.outputs['Image']
    em = N.new('CompositorNodeEllipseMask')
    try: em.inputs['Size'].default_value = (0.95, 0.85)
    except Exception: pass
    bl = N.new('CompositorNodeBlur')
    try: bl.inputs['Size'].default_value = (300, 300)
    except Exception: bl.inputs['Size'].default_value = 300
    L.new(em.outputs['Mask'], bl.inputs['Image'])
    vg = N.new('ShaderNodeMix'); vg.data_type = 'RGBA'; vg.blend_type = 'MULTIPLY'; vg.inputs['Factor'].default_value = vignette
    L.new(src, vg.inputs['A']); L.new(bl.outputs['Image'], vg.inputs['B']); src = vg.outputs['Result']
    if invert_keys:
        iv = N.new('CompositorNodeInvert'); L.new(src, iv.inputs['Color'])
        fac = iv.inputs['Fac'] if 'Fac' in iv.inputs else iv.inputs[0]
        for f, v in invert_keys:
            fac.default_value = v; fac.keyframe_insert('default_value', frame=f)
        src = iv.outputs['Color']
    out = N.new('NodeGroupOutput'); L.new(src, out.inputs[0])
    sc.compositing_node_group = ng; sc.render.use_compositing = True
    return ng

def cbase(i, sky=None, kuwa=3, bloom=0.9, aberr=0.012, invert_keys=None, lines=False):
    sc = new_scene('SAGA_%02d' % i)
    sc.render.fps = FPS; sc.frame_start = 1; sc.frame_end = page_frames(i)
    sc.eevee.taa_render_samples = 24
    sc.render.use_freestyle = lines
    if sky: crimson_sky(sc, **sky)
    else: world_color(sc, BLACK)
    comp_crimson(sc, kuwa, bloom, 1.15, 1.0, aberr, 0.75, invert_keys)
    return sc, sc.frame_end

def silhouette(objs, rim=WHITE, width=0.22, name='MR_Sil'):
    m = mat_rim(f'{name}_{"%.2f%.2f%.2f" % rim}_{width}', rim=rim, width=width)
    for o in objs:
        if o.type in ('MESH', 'CURVE', 'FONT') and o.data:
            o.data.materials.clear(); o.data.materials.append(m)
            for md in list(getattr(o, 'modifiers', [])):
                if md.type == 'SOLIDIFY' and md.name == 'InkLine': o.modifiers.remove(md)
    return m

def crim_creature(rel, loc, scale, rim=WHITE, rot_z=0.0, eyes=WHITE, width=0.2):
    roots, new = creature(rel, loc, scale, color=(0, 0, 0), rot_z=rot_z)
    silhouette(new, rim, width)
    play_creature_anim(roots)
    return roots, new

def crim_town(night=True, rim=(1.0, 0.25, 0.12), lamp=WHITE, trees=0.3):
    """the harbour as one silhouette mass: every kit object black with a rim; windows / lamps glowing"""
    before = set(bpy.context.scene.objects)
    town2(night, trees=trees)
    new = [o for o in bpy.context.scene.objects if o not in before]
    wm = glow('MR_Window', lamp, 6)
    for o in new:
        if o.type != 'MESH': continue
        if o.name.startswith('Sea'):
            o.data.materials.clear(); o.data.materials.append(mat_streak_sea('MR_SeaTown', (0.03, 0.0, 0.0), (0.55, 0.05, 0.03))); continue
        keep = [i for i, s in enumerate(o.material_slots) if s.material and s.material.name.startswith('M_WinNight')]
        rimmat = mat_rim(f'MR_Town_{"%.2f%.2f%.2f" % rim}', rim=rim, width=0.18)
        for i, s in enumerate(o.material_slots): s.material = wm if i in keep else rimmat
    return new

def speedlines(cam, f0, f1, color=(0, 0, 0), dist=1.0, n=90.0):
    p = plane('Speed_' + cam.name, (2.4, 1.4), (0, 0, -dist), mat_speedlines('MR_Speed_%d' % int(n), color, n))
    p.parent = cam
    kf(p, 'scale', f0 - 1, (0, 0, 0)); kf(p, 'scale', f0, (1, 1, 1)); kf(p, 'scale', f1, (1, 1, 1)); kf(p, 'scale', f1 + 1, (0, 0, 0))
    for f in range(f0, f1, 2): kf(p, 'rotation_euler', f, (0, 0, random.uniform(-.2, .2)))
    return p

def brush_cloud(seed, center, scale, mat, n=5, depth=0.06):
    """big ink-brush cloud strokes (calligraphic sweeps) as black ribbons in the sky"""
    rnd = random.Random(seed); out = []
    for k in range(n):
        g = glyph(f'Cloud{seed}_{k}', seed * 10 + k, (center[0] + rnd.uniform(-1, 1) * scale, center[1], center[2] + rnd.uniform(-.3, .3) * scale),
                  scale * rnd.uniform(.8, 1.6), mat, depth=depth)
        g.rotation_euler = (math.pi / 2, 0, 0); out.append(g)
    return out

def cut(sc, cams):
    """camera cuts on markers: [(frame, cam)]"""
    for f, c in cams:
        mk = sc.timeline_markers.new(f'cut{f}', frame=f); mk.camera = c
    sc.camera = cams[0][1]

def lightning(seed, a, b, f0, f1, mat, segs=14, jitter=0.25):
    rnd = random.Random(seed); cu = bpy.data.curves.new(f'Bolt{seed}', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 0.02 * (Vector(b) - Vector(a)).length / 10
    sp = cu.splines.new('POLY'); sp.points.add(segs)
    A, B = Vector(a), Vector(b); L = (B - A).length
    for k in range(segs + 1):
        t = k / segs; p = A.lerp(B, t)
        if 0 < k < segs: p += Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))) * L * jitter * .15
        sp.points[k].co = (*p, 1)
    o = bpy.data.objects.new(f'Bolt{seed}', cu); link(o); cu.materials.append(mat)
    kf(o, 'scale', f0 - 1, (0, 0, 0)); kf(o, 'scale', f0, (1, 1, 1)); kf(o, 'scale', f1, (1, 1, 1)); kf(o, 'scale', f1 + 1, (0, 0, 0))
    return o

# ======================================================================= the CRIMSON pages
def crim_codex(loc=(0, 0, 0), open_deg=0.0, name='Codex', rim=(1.0, 0.3, 0.2), glyph_col=HOT):
    root, hinge, socks = codex(loc, open_deg, name)
    leather = mat_rim('MR_Leather', rim=rim, base=BLACK, mid=(0.22, 0.01, 0.01), width=0.25, light_band=0.35)
    pagesm = mat_paper('MR_PagesBlock', (0.86, 0.80, 0.70), (0.45, 0.06, 0.04), 0.2, 8)
    gm = glow('MR_CodexGold', glyph_col, 4)
    for o in [root] + list(root.children_recursive):
        if o.type not in ('MESH', 'CURVE') or not o.data: continue
        if '_Socket' in o.name:
            o.data.materials.clear(); o.data.materials.append(mat_rim('MR_SocketOff', rim=(0.6, 0.05, 0.03), width=0.4))
        elif o.name.endswith('_Pages'): o.data.materials.clear(); o.data.materials.append(pagesm)
        elif '_Ring' in o.name or '_Quill' in o.name: o.data.materials.clear(); o.data.materials.append(gm)
        else: o.data.materials.clear(); o.data.materials.append(leather)
    return root, hinge, socks

def ignite(sock, f0, col=RED, peak=40, hold=14):
    m = glow('MR_SockOn_' + sock.name, col, 0); sock.data.materials.clear(); sock.data.materials.append(m)
    glow_key(m, [(f0, 0), (f0 + 4, peak), (f0 + 20, hold)])

@page(1)
def c01():
    """black. A single drop of ink falls, blooms into a pool of red, burns into one white-hot glyph"""
    sc, F = cbase(1, None, kuwa=2, bloom=1.0)
    floor = plane('Floor', (4, 3), (0, 0, 0), mat_paper('MR_BlackPaper', (0.05, 0.03, 0.03), (0.16, 0.0, 0.0), .7, 3))
    drop = sphere('Drop', 0.02, (0, 0, 1.0), glow('MR_Drop', (0.28, 0.0, 0.005), 1))
    kfs(drop, 'location', [(16, (0, 0, 1.0)), (40, (0, 0, 0.01))])
    kfs(drop, 'scale', [(39, (1, 1, 1.5)), (41, (3, 3, .05)), (70, (7, 7, .02))])
    rnd = random.Random(1)
    for k in range(22):   # splash droplets flung out
        a = rnd.uniform(0, 6.28); r = rnd.uniform(.08, .35)
        s = sphere(f'Spl{k}', rnd.uniform(.003, .01), (0, 0, .01), drop.data.materials[0])
        kf(s, 'scale', 40, (0, 0, 0)); kf(s, 'scale', 41, (1, 1, 1)); kf(s, 'location', 41, (0, 0, .01))
        kf(s, 'location', 52, (r * math.cos(a), r * math.sin(a), .01)); kf(s, 'scale', 52, (1.4, 1.4, .2))
    g = glyph('Glyph', 11, (0, 0, 0.014), 0.3, glow('MR_Hot1', HOT, 0), depth=0.01); write_on(g, 72, 128)
    glow_key(g.data.materials[0], [(72, 0), (80, 3), (128, 5), (F, 4)])
    embers(60, (-.5, -.4, 0), (.5, .4, .05), 100, F, (1, .55, .3), seed=11, rise=.5, strength=10)
    l = light('Key', 'SPOT', (0.2, -0.3, 1.3), 0, (1, .3, .2), look=(0, 0, 0)); kfs(l.data, 'energy', [(1, 0), (45, 0), (75, 80)])
    c = cam('Cam', (0, -0.9, 1.2), (0, 0, 0), 50)
    cam_move(c, [(1, (0, -0.95, 1.3)), (60, (0, -0.7, 1.0)), (F, (0.05, -0.45, 0.62))], [(1, (0, 0, 0.3)), (40, (0, 0, 0)), (F, (0, 0, 0))])

@page(2)
def c02():
    """the world written: black islands on a burning sea under a vast pale sun; white Script veins run through them"""
    sc, F = cbase(2, dict(sun_dir=(0.15, 1.0, 0.06), sun_r=0.09, horizon=(1.0, 0.35, 0.12), mid=(0.5, 0.03, 0.02)), kuwa=3)
    plane('Sea', (600, 400), (0, 0, 0), mat_streak_sea('MR_Sea2'))
    rnd = random.Random(4); sil = mat_rim('MR_Isle', rim=(1.0, 0.45, 0.25), width=0.2)
    for k in range(10):
        p = (rnd.uniform(-16, 16), rnd.uniform(2, 26), 0)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4, radius=1, location=p)
        o = bpy.context.active_object; o.name = f'Isle{k}'
        for cc in list(o.users_collection): cc.objects.unlink(o)
        link(o); s = rnd.uniform(1.6, 4.0); o.scale = (s * rnd.uniform(.9, 1.8), s, s * rnd.uniform(.4, .9))
        tex = bpy.data.textures.new(f'IsleN{k}', 'CLOUDS'); tex.noise_scale = .6
        d = o.modifiers.new('D', 'DISPLACE'); d.texture = tex; d.strength = .9
        o.data.materials.append(sil)
    wm = glow('MR_Vein', WHITE, 3)
    for k in range(18):
        g = glyph(f'Vein{k}', 200 + k, (rnd.uniform(-16, 16), rnd.uniform(2, 26), 0.05), rnd.uniform(1.6, 3.4), wm, depth=0.05)
        write_on(g, 8 + k * 12, 8 + k * 12 + 45)
    birds = mat_rim('MR_Birds', rim=(1, .4, .3), width=0.3)
    for k in range(9):
        roots, new = crim_creature('Flying/Pigeon', (rnd.uniform(-8, 8), rnd.uniform(14, 22), rnd.uniform(5, 9)), 0.25, (1, .4, .3), rnd.uniform(-.5, .5))
        for r_ in roots: kfs(r_, 'location', [(1, r_.location.copy()), (F, r_.location + Vector((rnd.uniform(3, 6), rnd.uniform(-2, 2), 0.5)))])
    c = cam('Cam', (-12, -14, 6), (0, 0, 0), 30); c.data.clip_end = 3000
    cam_move(c, [(1, (-10, -12, 4.5)), (F, (6, -10, 3.2))], [(1, (-2, 12, 1)), (F, (3, 14, 1.5))])

@page(3)
def c03():
    """a black page of red glyphs; two of them shudder and blink open — white eyes with a red slit"""
    sc, F = cbase(3, None, kuwa=2, bloom=1.0)
    plane('Page', (2.6, 1.6), (0, 0, 0), mat_paper('MR_DarkPage', (0.08, 0.05, 0.05), (0.30, 0.0, 0.0), .8, 2))
    red = glow('MR_RedInk', (0.55, 0.02, 0.02), 1.2); rnd = random.Random(7)
    for k in range(80):
        g = glyph(f'G{k}', 300 + k, (rnd.uniform(-1.2, 1.2), rnd.uniform(-.7, .7), 0.003), rnd.uniform(.05, .11), red, depth=0.003)
    eyew = glow('MR_EyeW', WHITE, 2.5); slit = glow('MR_Slit', (0.7, 0.0, 0.0), 3)
    for side in (-1, 1):
        e = sphere(f'Eye{side}', 0.009, (side * 0.04, 0.02, 0.005), eyew)
        p = sphere(f'Pupil{side}', 0.003, (side * 0.04, 0.02, 0.009), slit); p.scale = (0.35, 1.6, 0.3)
        a, b, c_, d = int(F * .4), int(F * .48), int(F * .7), int(F * .74)
        kfs(e, 'scale', [(1, (1.7, 0.02, 0.2)), (a, (1.7, 0.02, 0.2)), (b, (1.7, 1.0, 0.4)), (c_, (1.7, 1.0, 0.4)), (c_ + 2, (1.7, .05, .2)), (d, (1.7, 1.0, .4))])
        kfs(p, 'scale', [(a, (0, 0, 0)), (b, (0.35, 1.6, 0.3)), (c_, (0.35, 1.6, 0.3)), (c_ + 2, (0, 0, 0)), (d, (0.35, 1.6, 0.3))])
    c = cam('Cam', (0, -0.55, 0.45), (0, 0, 0), 50)
    cam_move(c, [(1, (0.3, -0.75, 0.7)), (int(F * .45), (0.05, -0.45, 0.32)), (F, (0, -0.3, 0.2))], [(1, (0.05, 0, 0)), (F, (0, 0.02, 0))])
    shake(c, int(F * .48), int(F * .55), 0.004, seed=3)

@page(4)
def c04():
    """the Sparks rise: black silhouettes with white rims and glowing eyes, wheeling across a gigantic red sun"""
    sc, F = cbase(4, dict(sun_dir=(0.0, 1.0, 0.22), sun_r=0.26, sun_col=(1.0, 0.92, 0.82), horizon=(0.95, 0.15, 0.05), mid=(0.35, 0.0, 0.0)), kuwa=3, bloom=1.0)
    plane('Ground', (400, 300), (0, 0, -0.3), mat_rim('MR_Ground4', rim=(0.4, 0, 0), width=0.1))
    cast = [('Flying/Dragon', 1.2), ('Flying/Glub', .9), ('Flying/Armabee', .8), ('Flying/Ghost', .9), ('Flying/Hywirl', .8), ('Flying/Alpaking', 1.0), ('Flying/Squidle', .8)]
    rnd = random.Random(44)
    for k, (rel, s) in enumerate(cast):
        a = k / len(cast) * 2 * math.pi
        p0 = Vector((math.cos(a) * 4, 18 + math.sin(a) * 3, -1)); p1 = Vector((math.cos(a + 1.2) * 5, 18 + math.sin(a + 1.2) * 3, 4 + k * .5))
        roots, _ = crim_creature(rel, p0, s, WHITE, a + math.pi / 2)
        for r_ in roots:
            kfs(r_, 'location', [(1 + k * 5, p0), (int(F * .6) + k * 3, p1), (F, p1 + Vector((rnd.uniform(-2, 2), 0, 1.5)))])
            kfs(r_, 'rotation_euler', [(1, a + math.pi / 2), (F, a + math.pi / 2 + rnd.uniform(-1, 1))], index=2)
    embers(140, (-8, 10, -1), (8, 24, 8), 1, F, (1, .4, .25), seed=4, rise=4, size=.03, strength=9)
    c = cam('Cam', (0, -6, 1.2), (0, 18, 3), 32); c.data.clip_end = 2000
    cam_move(c, [(1, (0, -7, 0.4)), (F, (1.0, -4.5, 1.8))], [(1, (0, 18, 1.5)), (F, (0, 18, 4.5))])

@page(5)
def c05():
    """THE CODEX: a black grimoire edged in red light; it trembles, bursts open in white fire, pages storm out"""
    sc, F = cbase(5, None, kuwa=2, bloom=1.2, invert_keys=[(int(page_frames(5) * .55) - 1, 0), (int(page_frames(5) * .55), 1), (int(page_frames(5) * .55) + 2, 0)])
    world_color(sc, (0.03, 0.0, 0.0))
    plane('Desk', (6, 5), (0, 0, -0.001), mat_paper('MR_Desk', (0.06, 0.02, 0.02), (0.22, 0.0, 0.0), .7, 2))
    root, hinge, socks = crim_codex((-0.21, 0, 0))
    o_ = int(F * .55)
    kfs(hinge, 'rotation_euler', [(1, 0), (o_, 0), (o_ + 10, -math.radians(172)), (F, -math.radians(178))], index=1)
    shake(root, int(F * .22), o_, 0.007, seed=5)
    pm = mat_paper('MR_Leaf', (0.95, 0.92, 0.86), (0.6, 0.05, 0.03), .25, 6); rnd = random.Random(55)
    for k in range(40):
        pg = plane(f'Leaf{k}', (0.07, 0.10), (0, 0, 0.13), pm)
        t0 = o_ + 2 + rnd.randint(0, 34)
        kf(pg, 'scale', t0 - 1, (0, 0, 0)); kf(pg, 'scale', t0, (1, 1, 1)); kf(pg, 'location', t0, (0, 0, 0.14))
        kf(pg, 'location', min(F, t0 + 60), (rnd.uniform(-1.0, 0.5), rnd.uniform(0.0, 1.3), rnd.uniform(.3, 1.0)))
        kf(pg, 'rotation_euler', t0, (0, 0, 0)); kf(pg, 'rotation_euler', min(F, t0 + 60), (rnd.uniform(-7, 7), rnd.uniform(-7, 7), rnd.uniform(-3, 3)))
    core = sphere('Burst', 0.08, (0, 0, 0.16), glow('MR_BurstW', WHITE, 0))
    glow_key(core.data.materials[0], [(o_ - 1, 0), (o_ + 1, 25), (o_ + 30, 5), (F, 3)])
    kfs(core, 'scale', [(o_ - 1, (0, 0, 0)), (o_ + 2, (1.6, 1.6, .6)), (F, (0.8, 0.8, .3))])
    embers(120, (-.6, -.5, .05), (.6, .5, .3), o_, F, (1, .5, .3), seed=5, rise=1.1, strength=9)
    cnd = light('Candle', 'POINT', (0.5, -0.35, 0.35), 30, (1, .35, .2), 0.05)
    c1 = cam('CamA', (1.15, -1.05, 0.9), (0, 0, 0.05), 40)
    cam_move(c1, [(1, (1.3, -1.2, 1.0)), (o_, (0.95, -0.9, 0.72))], [(1, (0, 0, 0.05)), (o_, (0, 0, 0.08))])
    c2 = cam('CamB', (0.3, -0.5, 0.25), (0, 0, 0.1), 28)
    cam_move(c2, [(o_, (0.75, -0.85, 0.42)), (F, (0.9, -1.7, 1.35))], [(o_, (0, 0.05, 0.14)), (F, (0, 0.3, 0.4))])
    cut(sc, [(1, c1), (o_ - 6, c2)])
    speedlines(c2, o_, o_ + 18, (0.02, 0, 0), 1.0)

@page(6)
def c06():
    """an open white page; a ring of red Script writes itself; a Spark is inked into being; a socket bleeds red"""
    sc, F = cbase(6, None, kuwa=2, bloom=1.0)
    plane('Page', (1.6, 1.0), (0, 0, 0), mat_paper('MR_WhitePage', (0.93, 0.90, 0.84), (0.55, 0.04, 0.03), .35, 3))
    red = glow('MR_RedRing', (0.7, 0.02, 0.02), 1.5)
    for k in range(12):
        a = k / 12 * 2 * math.pi
        g = glyph(f'Ring{k}', 600 + k, (0.3 * math.cos(a), 0.3 * math.sin(a), 0.004), 0.07, red, depth=0.003); write_on(g, 6 + k * 5, 26 + k * 5)
    roots, new = crim_creature('Flying/Dragon', (0, 0, 0.05), 0.07, (0.8, 0.05, 0.03))
    for r_ in roots: kfs(r_, 'scale', [(int(F * .45), (0, 0, 0)), (int(F * .58), (0.08, 0.08, 0.08)), (F, (0.07, 0.07, 0.07))])
    sock = sphere('Socket', 0.035, (0.55, 0.32, 0.01), glow('MR_S6', RED, 0)); sock.scale = (1, 1, .3)
    glow_key(sock.data.materials[0], [(int(F * .6), 0), (int(F * .64), 30), (F, 12)])
    c = cam('Cam', (0, -0.9, 1.0), (0, 0, 0), 45)
    cam_move(c, [(1, (0.15, -0.85, 0.95)), (F, (0, -0.55, 0.7))], [(1, (0, 0, 0)), (F, (0.05, 0.05, 0.03))])

@page(7)
def c07():
    """a thousand years of peace: Lumen Harbor as a black silhouette against a vast crimson sunset; lanterns, Sparks"""
    sc, F = cbase(7, dict(sun_dir=(0.35, 1.0, 0.05), sun_r=0.11, horizon=(1.0, 0.42, 0.15), mid=(0.55, 0.05, 0.03), top=(0.06, 0.0, 0.01)), kuwa=3)
    crim_town(True, rim=(1.0, 0.45, 0.2), lamp=(1.0, 0.85, 0.6), trees=0.35)
    for o in list(sc.objects):
        if o.name.startswith('Sea'): o.data.materials.clear(); o.data.materials.append(mat_streak_sea('MR_Sea7', (0.12, 0.0, 0.0), (1.0, 0.35, 0.12)))
    rnd = random.Random(7)
    for k, rel in enumerate(['Flying/Glub', 'Flying/Armabee', 'Flying/Dragon']):
        roots, _ = crim_creature(rel, (-14 + k * 9, 6, 14 + k), 1.2, WHITE)
        for r_ in roots: kfs(r_, 'location', [(1, (-14 + k * 9, 6, 14 + k)), (F, (-4 + k * 9, 9, 16 + k))])
    c = cam('Cam', (-55, -75, 32), (0, 0, 0), 30); c.data.clip_end = 4000
    cam_move(c, [(1, (-60, -80, 26)), (F, (-25, -85, 22))], [(1, (-5, 30, 8)), (F, (10, 30, 8))])

@page(8)
def c08():
    """THE SURGE — the action: night, red Script cracks under Hollowmere, the sky splits with lightning, a storm of
    black Sparks with white eyes; fast cuts, speed lines, impact frames"""
    F = page_frames(8); hits = [int(F * x) for x in (.30, .52, .70, .86)]
    inv = []
    for h in hits: inv += [(h - 1, 0), (h, 1), (h + 2, 0)]
    sc, F = cbase(8, dict(sun_dir=(-0.2, 1.0, 0.25), sun_r=0.05, sun_col=(0.9, 0.85, 0.8), horizon=(0.6, 0.02, 0.02), mid=(0.15, 0.0, 0.0), top=(0.0, 0.0, 0.0)),
                  kuwa=3, bloom=1.3, aberr=0.02, invert_keys=inv)
    crim_town(True, rim=(0.9, 0.08, 0.04), lamp=(1.0, 0.6, 0.4), trees=0.25)
    red = glow('MR_Crack', (1.0, 0.1, 0.04), 0); rnd = random.Random(8)
    for k in range(30):
        g = glyph(f'Crack{k}', 800 + k, (rnd.uniform(-50, 50), rnd.uniform(-25, 35), 1.0), rnd.uniform(6, 18), red, depth=0.3); write_on(g, 6 + k * 3, 30 + k * 3)
    glow_key(red, [(1, 0), (hits[0], 3), (hits[2], 6), (F, 4.5)])
    wbolt = glow('MR_Bolt', WHITE, 12)
    for k, h in enumerate(hits):
        lightning(80 + k, (rnd.uniform(-30, 30), rnd.uniform(20, 60), 90), (rnd.uniform(-20, 20), rnd.uniform(0, 20), 2), h, h + 3, wbolt)
    for k in range(16):
        roots, _ = crim_creature(rnd.choice(['Flying/Dragon', 'Flying/Ghost', 'Flying/Pigeon', 'Flying/Squidle', 'Flying/Hywirl']),
                                 (rnd.uniform(-35, 35), rnd.uniform(-5, 30), rnd.uniform(10, 30)), 1.0, (1.0, 0.15, 0.08), rnd.uniform(0, 6), width=0.25)
        for r_ in roots:
            p = r_.location.copy(); kfs(r_, 'location', [(1, p), (F, p + Vector((rnd.uniform(-18, 18), rnd.uniform(-12, 12), rnd.uniform(-4, 9))))])
    embers(240, (-50, -25, 0), (50, 35, 8), 1, F, (1, .3, .1), seed=8, rise=30, size=.3, strength=10)
    wide = cam('CamWide', (-45, -70, 26), (0, 5, 4), 30); wide.data.clip_end = 4000
    cam_move(wide, [(1, (-45, -70, 26)), (hits[0], (-35, -62, 22))], [(1, (0, 5, 6)), (hits[0], (0, 5, 8))])
    low = cam('CamLow', (8, -18, 1.5), (0, 10, 12), 22); low.data.clip_end = 4000
    cam_move(low, [(hits[0], (8, -18, 1.5)), (hits[1], (4, -14, 2.5))], [(hits[0], (0, 10, 10)), (hits[1], (-4, 10, 16))])
    close = cam('CamClose', (2, -6, 3), (0, 2, 0.5), 35); close.data.clip_end = 4000
    cam_move(close, [(hits[1], (14, -22, 9)), (hits[2], (9, -16, 6))], [(hits[1], (0, 4, 2)), (hits[2], (0, 6, 3))])
    sky = cam('CamSky', (0, -70, 30), (0, 20, 40), 22); sky.data.clip_end = 4000
    cam_move(sky, [(hits[2], (0, -70, 30)), (F, (0, -80, 26))], [(hits[2], (0, 20, 32)), (F, (5, 20, 42))])
    cut(sc, [(1, wide), (hits[0], low), (hits[1], close), (hits[2], sky)])
    for c_, (a, b) in ((low, (hits[0], hits[0] + 14)), (close, (hits[1], hits[1] + 12)), (sky, (hits[2], hits[2] + 16))): speedlines(c_, a, b, (0.02, 0, 0), 1.0)
    for c_ in (wide, low, close, sky): shake(c_, int(F * .25), F, 0.25, seed=hash(c_.name) % 99)

@page(9)
def c09():
    """a black wave with a white crest swallows the town against the red sky; then blood-red ink floods the frame and drains"""
    F = page_frames(9)
    sc, F = cbase(9, dict(sun_dir=(0.0, 1.0, 0.1), sun_r=0.06, horizon=(0.9, 0.12, 0.05), mid=(0.3, 0.0, 0.0), top=(0.0, 0, 0)), kuwa=3, bloom=1.0,
                  invert_keys=[(int(F * .5) - 1, 0), (int(F * .5), 1), (int(F * .5) + 2, 0)])
    crim_town(True, rim=(0.9, 0.1, 0.05), trees=0.2)
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=34, depth=320, location=(0, 120, 0))
    wv = bpy.context.active_object; wv.name = 'Wave'
    for cc in list(wv.users_collection): cc.objects.unlink(wv)
    link(wv); wv.rotation_euler = (0, math.pi / 2, 0); wv.data.materials.append(mat_rim('MR_Wave', rim=WHITE, width=0.32))
    kfs(wv, 'location', [(1, (0, 170, -18)), (int(F * .45), (0, 40, 8)), (int(F * .6), (0, -10, 2)), (int(F * .62), (0, -10, -70))])
    for o in list(sc.objects):
        if o.type == 'MESH' and o.name not in ('Wave',) and not o.name.startswith(('Sea', 'SM_Mount')):
            kf(o, 'location', int(F * .55), o.location.copy()); kf(o, 'location', int(F * .6), o.location + Vector((0, 0, -90)))
    flood = plane('Flood', (3, 2), (0, 0, -0.5), glow('MR_Flood', BLOOD, 1.2))
    c = cam('Cam', (0, -95, 14), (0, 40, 16), 28); c.data.clip_end = 4000
    flood.parent = c; flood.location = (0, 0, -0.6)
    kfs(flood, 'scale', [(int(F * .6), (0, 0, 0)), (int(F * .7), (1, 1, 1)), (int(F * .85), (1, 1, 1)), (F, (1, 0, 1))])
    cam_move(c, [(1, (0, -95, 14)), (F, (0, -110, 18))], [(1, (0, 40, 16)), (F, (0, 30, 10))])
    shake(c, int(F * .38), int(F * .62), 0.5, seed=9)

@page(10)
def c10():
    """inverted palette: a white dawn, a black sea; only a long black shadow on the sand; a red thread drifts out of the water"""
    sc, F = cbase(10, dict(sun_dir=(0.0, 1.0, 0.02), sun_r=0.05, sun_col=(0.95, 0.15, 0.1), horizon=(0.96, 0.94, 0.9), mid=(0.85, 0.83, 0.8), top=(0.7, 0.68, 0.66), streaks=0.3), kuwa=3, bloom=0.6)
    plane('Sand', (80, 50), (0, -14, 0), mat_paper('MR_Sand', (0.92, 0.9, 0.86), (0.6, 0.58, 0.55), .5, 2))
    plane('SeaB', (400, 300), (0, 160, 0.01), mat_streak_sea('MR_SeaB', (0.02, 0.02, 0.025), (0.25, 0.25, 0.27)))
    import bmesh
    me = bpy.data.meshes.new('ShadowM'); bm = bmesh.new(); vs = [bm.verts.new(v) for v in ((-.12, 0, 0), (.12, 0, 0), (.4, 6, 0), (-.4, 6, 0))]; bm.faces.new(vs); bm.to_mesh(me); bm.free()
    sh = bpy.data.objects.new('Shadow', me); link(sh); sh.location = (0.3, -2.6, 0.012); sh.rotation_euler[2] = 0.22; me.materials.append(glow('MR_ShadowK', BLACK, 1))
    kfs(sh, 'scale', [(1, (1, 0.9, 1)), (F, (1, 1.15, 1))])
    cu = bpy.data.curves.new('Thread', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 0.014
    sp = cu.splines.new('BEZIER'); sp.bezier_points.add(5)
    for k in range(6):
        bp = sp.bezier_points[k]; bp.co = (k * 0.7 - 1.8, 4 + k * 1.3, 0.05 + .35 * math.sin(k * 1.3)); bp.handle_left_type = bp.handle_right_type = 'AUTO'
    th = bpy.data.objects.new('Thread', cu); link(th); cu.materials.append(glow('MR_ThreadR', RED, 2)); write_on(th, 20, F)
    c = cam('Cam', (0, -7, 1.8), (0, 3, 0.2), 35)
    cam_move(c, [(1, (0, -7.5, 1.9)), (F, (0.6, -5.5, 1.4))], [(1, (0, 3, 0.3)), (F, (0.4, 4, 0.4))])

@page(11)
def c11():
    """the White Page: white masks with weeping red eyes close in around the page; white ink devours the red Script"""
    sc, F = cbase(11, None, kuwa=2, bloom=0.9)
    plane('Page', (3.4, 2.0), (0, 0, 0), mat_paper('MR_DarkPage11', (0.06, 0.04, 0.04), (0.25, 0.0, 0.0), .8, 2))
    red = glow('MR_RedInk11', (0.6, 0.02, 0.02), 1.3); rnd = random.Random(11)
    for k in range(80): glyph(f'G{k}', 1100 + k, (rnd.uniform(-1.5, 1.5), rnd.uniform(-.85, .85), 0.003), rnd.uniform(.05, .12), red, depth=0.004)
    white = mat_rim('MR_Mask', rim=(0.7, 0.7, 0.75), base=(0.96, 0.95, 0.93), width=0.15); hole = glow('MR_Hole', BLACK, 1); tear = glow('MR_Tear', RED, 2)
    for k in range(10):
        a = k / 10 * 2 * math.pi; p = (1.2 * math.cos(a), .7 * math.sin(a), 0.06)
        m = sphere(f'Mask{k}', 0.11, p, white)
        for s in (-1, 1):
            e = sphere(f'MaskEye{k}{s}', 0.02, (s * .05, .02, .7), hole); e.parent = m; e.scale = (1.4, .6, .4)
            t = sphere(f'MaskTear{k}{s}', 0.008, (s * .05, -.04, .75), tear); t.parent = m; t.scale = (.6, 3.0, .4)
        tt = int(F * .1) + k * 4; kf(m, 'scale', tt - 1, (0, 0, 0)); kf(m, 'scale', tt + 6, (0.8, 1.0, 0.35))
    wd = sphere('WhiteTide', 1.0, (0, 0, 0.012), glow('MR_WhiteTide', WHITE, 1.3))
    kfs(wd, 'scale', [(int(F * .45), (0, 0, 0)), (F, (0.62, 0.36, 0.005))])
    c = cam('Cam', (0, -1.0, 1.9), (0, 0, 0), 40)
    cam_move(c, [(1, (0, -1.6, 2.6)), (F, (0, -1.2, 2.0))], [(1, (0, 0, 0)), (F, (0, 0, 0))])

@page(12)
def c12():
    """the Blanking: a red-rimmed Spark turns chalk white from the tail up; a row of red lanterns dies into white"""
    sc, F = cbase(12, dict(sun_dir=(0.0, 1.0, 0.15), sun_r=0.05, sun_col=(1, 1, 1), horizon=(0.45, 0.02, 0.02), mid=(0.12, 0.0, 0.0), top=(0.0, 0.0, 0.0)), kuwa=3)
    plane('Ground', (80, 60), (0, 0, 0), mat_rim('MR_G12', rim=(0.3, 0, 0), width=0.1))
    roots, new = creature('Flying/Dragon', (0, 0, 0.7), 0.3, color=(0, 0, 0), rot_z=math.radians(-20))
    play_creature_anim(roots)
    bm_ = mat_blank('MR_Blanking', (0.08, 0.0, 0.0), int(F * .25), int(F * .85))
    for o in new:
        if o.type == 'MESH':
            for s_ in o.material_slots: s_.material = bm_
    lamp = glow('MR_L12', RED, 8); wl = glow('MR_L12W', WHITE, 4)
    for k in range(12):
        p = (-5 + k * .9, 6, 1.4)
        lp = sphere(f'Lamp{k}', 0.08, p, lamp); wlp = sphere(f'LampW{k}', 0.08, p, wl)
        t = int(F * .45) + k * 5
        kf(lp, 'scale', t, (1, 1, 1)); kf(lp, 'scale', t + 3, (0, 0, 0)); kf(wlp, 'scale', t, (0, 0, 0)); kf(wlp, 'scale', t + 3, (1, 1, 1))
    c = cam('Cam', (0, -4.5, 1.0), (0, 0, 0.7), 32)
    cam_move(c, [(1, (0.6, -4.8, 1.0)), (F, (-0.4, -4.0, 0.9))], [(1, (0, 0, 0.6)), (F, (0, 0.5, 0.7))])

@page(13)
def c13():
    """three black Codices on a stone altar, their sockets burning red — one, two, three — in candle light"""
    sc, F = cbase(13, None, kuwa=2, bloom=1.1)
    world_color(sc, (0.03, 0.0, 0.0))
    plane('Altar', (5, 3), (0, 0, -0.001), mat_paper('MR_Stone', (0.12, 0.10, 0.10), (0.25, 0.02, 0.02), .6, 4))
    for k in range(3):
        root, hinge, socks = crim_codex(((k - 1) * 0.65 - 0.21, 0, 0), name=f'Codex{k}')
        kfs(hinge, 'rotation_euler', [(1 + k * 20, 0), (30 + k * 20, -math.radians(25))], index=1)
        for j in range(k + 1): ignite(socks[j], 20 + k * 20 + j * 6)
    for k in range(5):
        x = -1.1 + k * .55
        cube(f'Candle{k}', (.05, .05, .25), (x, .55, .125), mat_rim('MR_Wax', rim=(1, .8, .6), width=0.3))
        fl = sphere(f'Flame{k}', 0.02, (x, .55, .27), glow('MR_Flame', HOT, 14)); fl.scale = (1, 1, 2.2)
        l = light(f'CL{k}', 'POINT', (x, .5, .35), 10, (1, .4, .2), 0.05)
    embers(50, (-1.2, -.3, .1), (1.2, .6, .5), 1, F, (1, .5, .3), seed=13, rise=.4, size=.004, strength=8)
    c = cam('Cam', (0, -1.6, 0.9), (0, 0, 0.1), 40)
    cam_move(c, [(1, (-0.8, -1.5, 0.8)), (F, (0.8, -1.4, 0.9))], [(1, (-0.3, 0, 0.1)), (F, (0.3, 0, 0.1))])

@page(14)
def c14():
    """a fourth book opens on nothing — a dead white page; a cold draft kills the only candle"""
    sc, F = cbase(14, None, kuwa=2, bloom=0.9)
    plane('Altar', (4, 3), (0, 0, -0.001), mat_paper('MR_Stone14', (0.1, 0.09, 0.09), (0.2, 0.02, 0.02), .6, 4))
    root, hinge, socks = crim_codex((-0.21, 0, 0), name='Blank', rim=(0.85, 0.85, 0.9))
    kfs(hinge, 'rotation_euler', [(10, 0), (40, -math.radians(175))], index=1)
    blank = plane('BlankPage', (0.38, 0.54), (-0.21, 0, 0.123), glow('MR_BlankGlow', (0.85, 0.86, 0.9), 0.9))
    fl = sphere('Flame', 0.025, (0.5, .3, .3), glow('MR_Flame14', HOT, 12)); fl.scale = (1, 1, 2)
    cube('Candle', (.06, .06, .28), (0.5, .3, .14), mat_rim('MR_Wax14', rim=(1, .8, .6), width=0.3))
    l = light('CL', 'POINT', (0.5, .25, .4), 30, (1, .4, .2), 0.05)
    out = int(F * .7)
    kfs(fl, 'scale', [(out - 6, (1, 1, 2)), (out - 3, (1.4, .4, 1.4)), (out, (0, 0, 0))]); kfs(l.data, 'energy', [(out - 6, 30), (out, 0)])
    smoke = glow('MR_Smoke', (0.7, 0.7, 0.72), 0.8)
    for k in range(12):
        s = sphere(f'Smoke{k}', 0.012, (0.5, .3, .33), smoke); t = out + k * 3
        kf(s, 'scale', t - 1, (0, 0, 0)); kf(s, 'location', t, (0.5, .3, .33)); kf(s, 'scale', t, (1, 1, 1))
        kf(s, 'location', t + 34, (0.5 + .04 * math.sin(k), .3, .62 + k * .02)); kf(s, 'scale', t + 34, (2.6, 2.6, 2.6))
    c = cam('Cam', (0.2, -0.8, 0.75), (0, 0, 0.05), 40)
    cam_move(c, [(1, (0.8, -1.7, 1.25)), (F, (0.55, -1.35, 1.0))], [(1, (0.05, 0, 0.05)), (F, (0.1, 0.05, 0.1))])

@page(15)
def c15():
    """black fog, a blood-red moon; white sails slide out of the dark toward the harbour; the lanterns go white"""
    sc, F = cbase(15, dict(sun_dir=(-0.3, 1.0, 0.18), sun_r=0.08, sun_col=(0.85, 0.08, 0.05), horizon=(0.22, 0.03, 0.03), mid=(0.06, 0.0, 0.0), top=(0.0, 0, 0)), kuwa=3)
    crim_town(True, rim=(0.6, 0.05, 0.03), lamp=(1.0, 0.55, 0.3), trees=0.2)
    for k in range(3):
        s = place('SM_Sailboat', (-80 + k * 30, 180 + k * 20, -1.2), math.radians(-120), 4.0)
        if s:
            s.data.materials.clear(); s.data.materials.append(mat_rim('MR_WhiteShip', rim=(0.6, 0.6, 0.65), base=(0.95, 0.95, 0.96), width=0.15))
            kfs(s, 'location', [(1, (-80 + k * 30, 180 + k * 20, -1.2)), (F, (-50 + k * 30, 90 + k * 15, -1.2))])
    wl = glow('MR_L15W', WHITE, 5); lamp = glow('MR_L15', (1.0, 0.45, 0.2), 8)
    for k in range(16):
        x = -40 + k * 5
        a = sphere(f'L{k}', .5, (x, -10, 3), lamp); b = sphere(f'LW{k}', .5, (x, -10, 3), wl)
        t = int(F * .55) + k * 3
        kf(a, 'scale', t, (1, 1, 1)); kf(a, 'scale', t + 3, (0, 0, 0)); kf(b, 'scale', t, (0, 0, 0)); kf(b, 'scale', t + 3, (1, 1, 1))
    world_fog(sc, 0.006, (0.75, 0.74, 0.76))
    c = cam('Cam', (0, -60, 12), (0, 60, 10), 32); c.data.clip_end = 4000
    cam_move(c, [(1, (-10, -60, 12)), (F, (5, -70, 10))], [(1, (-30, 120, 14)), (F, (-10, 80, 10))])

@page(16)
def c16():
    """the blank book alone in the dark; a drop of blood falls; it becomes a red glyph that ignites white-gold;
    the first socket bursts into flame; impact; title"""
    F = page_frames(16); t_hit = int(FPS * 4.0); title_t = F - int(FPS * 5.0)
    sc, F = cbase(16, None, kuwa=2, bloom=1.4, invert_keys=[(t_hit + 39, 0), (t_hit + 40, 1), (t_hit + 42, 0), (title_t - 1, 0), (title_t, 1), (title_t + 2, 0)])
    plane('Void', (6, 4), (0, 0, -0.001), mat_paper('MR_Void', (0.03, 0.02, 0.02), (0.12, 0.0, 0.0), .6, 3))
    root, hinge, socks = crim_codex((-0.21, 0, 0), open_deg=178, name='First')
    plane('OpenPage', (0.4, 0.56), (-0.21, 0, 0.122), mat_paper('MR_OpenPage', (0.93, 0.9, 0.84), (0.6, 0.55, 0.5), .3, 5))
    blood = sphere('Blood', 0.012, (-0.2, 0, 0.9), glow('MR_Blood', BLOOD, 1.5))
    kfs(blood, 'location', [(int(t_hit * .5), (-0.2, 0, 0.9)), (t_hit, (-0.2, 0, 0.125))])
    kfs(blood, 'scale', [(t_hit, (1, 1, 1.5)), (t_hit + 2, (3, 3, .1)), (t_hit + 12, (6, 6, .05))])
    gr = glyph('BloodGlyph', 16, (-0.2, 0, 0.126), 0.2, glow('MR_BloodGlyph', (0.6, 0.0, 0.01), 1.5), depth=0.003); write_on(gr, t_hit + 4, t_hit + 30)
    gw = glyph('FireGlyph', 16, (-0.2, 0, 0.127), 0.2, glow('MR_FireGlyph', HOT, 0), depth=0.0034); write_on(gw, t_hit + 30, t_hit + 40)
    glow_key(gw.data.materials[0], [(t_hit + 30, 0), (t_hit + 40, 14), (F, 8)])
    ignite(socks[0], t_hit + 40, (1.0, 0.25, 0.08), 60, 20)
    embers(160, (-.6, -.5, .1), (.4, .5, .5), t_hit + 40, F, (1, .45, .2), seed=16, rise=1.4, size=.004, strength=9)
    tt = text3d('Title', 'SIGIL  &  SPARK', (0, 0.15, 0.9), 0.095, glow('MR_TitleW', WHITE, 2.4)); tt.rotation_euler = (math.radians(55), 0, 0)
    kfs(tt, 'scale', [(title_t, (0, 0, 0)), (title_t + 8, (1.08, 1.08, 1.08)), (title_t + 20, (1, 1, 1))])
    # red brush slash under the title (r63 fix: the old glyph was baked at world coords, so the X-rotation threw it off-frame)
    scu = bpy.data.curves.new('TitleSlash', 'CURVE'); scu.dimensions = '3D'; scu.bevel_depth = 0.011; scu.bevel_resolution = 3; scu.resolution_u = 24
    ssp = scu.splines.new('BEZIER'); ssp.bezier_points.add(2)
    for bp, co, rad in zip(ssp.bezier_points, [(-0.36, 0, -0.012), (0.0, 0, 0.004), (0.37, 0, 0.022)], (0.15, 1.0, 0.25)):
        bp.co = co; bp.handle_left_type = bp.handle_right_type = 'AUTO'; bp.radius = rad
    sl = bpy.data.objects.new('TitleSlash', scu); link(sl); scu.materials.append(glow('MR_Slash', RED, 2.5))
    sl.location = (0, 0.12, 0.815)
    write_on(sl, title_t + 6, title_t + 18)
    c = cam('Cam', (0, -0.9, 1.1), (0, 0, 0.1), 42)
    # the title must HOLD (user feedback r63: it drifted off-frame after ~2 s): fast pull-back, then a still frame
    cam_move(c, [(1, (0.1, -0.6, 0.85)), (t_hit, (0, -0.42, 0.55)), (title_t - 6, (0, -0.5, 0.75)), (title_t + 6, (0, -1.0, 1.32)), (F, (0, -1.04, 1.36))],
             [(1, (-0.2, 0, 0.1)), (t_hit, (-0.2, 0, 0.12)), (title_t - 6, (-0.1, 0.05, 0.3)), (title_t + 6, (0, 0.13, 0.84)), (F, (0, 0.13, 0.84))])
    speedlines(c, t_hit + 40, t_hit + 56, (0.02, 0, 0), 0.8)
    shake(c, t_hit + 40, t_hit + 52, 0.01, seed=16)

# ======================================================================= Unreal FX plates over the drawn pages
UEFX = os.path.join(SRC, 'intro_render', 'ue_fx')
# (page, start as fraction of the page, clip, blend, scale, offset x px, offset y px, opacity)
FX_PLAN = [
    (5, 0.55, 'explosion', 'SCREEN', 0.9, 0, 40, 0.75),
    (8, 0.10, 'fire', 'SCREEN', 1.6, -420, 260, 0.85), (8, 0.20, 'fire', 'SCREEN', 1.3, 380, 300, 0.8),
    (8, 0.30, 'explosion', 'SCREEN', 1.2, 0, 0, 1.0), (8, 0.52, 'electric', 'SCREEN', 1.4, 200, -80, 1.0),
    (8, 0.70, 'explosion', 'SCREEN', 1.6, -250, 120, 1.0), (8, 0.86, 'explosion', 'SCREEN', 1.0, 300, -60, 1.0),
    (9, 0.05, 'fire', 'SCREEN', 1.5, 0, 280, 0.7),
    (16, 0.40, 'explosion', 'SCREEN', 0.8, -140, 0, 0.7),
    (16, 0.40, 'fire', 'SCREEN', 0.9, 260, 140, 0.6),
]

def assemble_crimson(out_name='saga_intro.mp4'):
    """the master edit at 12 fps: drawn pages + Unreal FX plates (every 2nd frame of the 24 fps plates) + narration + music"""
    name, end, secs = assemble(out_name)
    sc = bpy.data.scenes[name]; ed = sc.sequence_editor
    strips = ed.strips if hasattr(ed, 'strips') else ed.sequences
    starts, _ = timeline(); fps = FPS // STEP
    for k, (pg, frac, clip, blend, scale, ox, oy, op) in enumerate(FX_PLAN):
        d = os.path.join(UEFX, clip)
        files = sorted(f for f in os.listdir(d) if f.endswith('.png'))[::STEP] if os.path.isdir(d) else []
        if not files: continue
        f0 = starts[pg] + int((page_frames(pg) // STEP) * frac)
        st = strips.new_image(f'FX{k}_{clip}', os.path.join(d, files[0]), channel=6 + (k % 3), frame_start=f0)
        for f in files[1:]: st.elements.append(f)
        st.blend_type = blend; st.blend_alpha = op
        if clip == 'electric': st.color_saturation = 0.0        # white lightning (the pack's is blue)
        if clip in ('fire', 'explosion', 'sparks'): st.color_multiply = 1.15
        try:
            st.transform.scale_x = st.transform.scale_y = scale; st.transform.offset_x = ox; st.transform.offset_y = oy
        except Exception: pass
    return name, end, secs

def render_edit_bg(blend):
    """render the SAGA_EDIT scene (VSE → mp4) in a background Blender"""
    import subprocess, sys
    exe = bpy.app.binary_path
    log = open(os.path.join(OUT, '_edit_log.txt'), 'w')
    p = subprocess.Popen([exe, '-b', blend, '-S', 'SAGA_EDIT', '-a'], stdout=log, stderr=subprocess.STDOUT, creationflags=0x08000000 | 0x00004000)
    return p.pid
