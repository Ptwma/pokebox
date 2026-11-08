# Sigil & Spark — the "Saga of the Script" intro, drawn in Blender (ink + watercolour on parchment).
# User 2026-11-01: told like a tale, no characters presented, everything a drawing, colour + suspense.
# Run inside Blender (5.2):  exec(open(r"...\saga_blender.py").read()); look_test()
# Creatures: Quaternius Ultimate Monsters (CC0, local only). Nothing from here ships in the repo except this script.
import bpy, math, os, random
from mathutils import Vector

SRC = r"E:\GAME-APP-DEV\POKEMON\SigilAndSpark_src"
CRE = os.path.join(SRC, 'creatures', 'ultimate_monsters')
OUT = os.path.join(SRC, 'intro_render')

# ------------------------------------------------------------------ scene
def new_scene(name, res=(1920, 1080)):
    sc = bpy.data.scenes.get(name)
    if sc:
        for o in list(sc.objects): bpy.data.objects.remove(o, do_unlink=True)
    else:
        sc = bpy.data.scenes.new(name)
    bpy.context.window.scene = sc
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.film_transparent = False
    sc.view_settings.view_transform = 'Standard'     # flat, illustration-like colours (no filmic wash)
    sc.view_settings.look = 'None'
    w = bpy.data.worlds.get('SagaWorld') or bpy.data.worlds.new('SagaWorld')
    w.use_nodes = True
    bg = w.node_tree.nodes.get('Background')
    if bg: bg.inputs[0].default_value = (0.02, 0.018, 0.016, 1); bg.inputs[1].default_value = 1.0
    sc.world = w
    ink_lines(sc)
    return sc

def ink_lines(sc, thick=3.2, color=(0.07, 0.04, 0.03)):
    """hand-drawn ink: Freestyle silhouettes / creases / borders, wobbly (perlin) and tapered at both ends"""
    sc.render.use_freestyle = True
    sc.render.line_thickness_mode = 'ABSOLUTE'; sc.render.line_thickness = 1.0
    vl = sc.view_layers[0]; vl.use_freestyle = True; fs = vl.freestyle_settings
    ls = fs.linesets[0] if fs.linesets else fs.linesets.new('Ink')
    ls.select_by_visibility = True; ls.select_by_edge_types = True
    ls.select_silhouette = True; ls.select_border = True; ls.select_crease = True; ls.select_external_contour = True
    st = ls.linestyle
    st.color = color; st.thickness = thick; st.thickness_position = 'CENTER'
    st.chaining = 'PLAIN'; st.use_chaining = True
    if not any(m.type == 'ALONG_STROKE' for m in st.thickness_modifiers):
        m = st.thickness_modifiers.new('Taper', 'ALONG_STROKE'); m.mapping = 'CURVE'; m.blend = 'MULTIPLY'
        c = m.curve.curves[0]; c.points[0].location = (0, 0.25); c.points[-1].location = (1, 0.25); c.points.new(0.5, 1.0)
    if not any(m.type == 'PERLIN_NOISE_1D' for m in st.geometry_modifiers):
        g = st.geometry_modifiers.new('Wobble', 'PERLIN_NOISE_1D'); g.frequency = 8; g.amplitude = 1.6; g.octaves = 2

def comp_bloom(sc, glare=0.9):
    """gold glyphs and embers bleed light (compositor Glare / bloom); best effort across 5.x node APIs"""
    try:
        ng = bpy.data.node_groups.get('SagaComp') or bpy.data.node_groups.new('SagaComp', 'CompositorNodeTree')
        for n in list(ng.nodes): ng.nodes.remove(n)
        if not ng.interface.items_tree:
            ng.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
        rl = ng.nodes.new('CompositorNodeRLayers'); out = ng.nodes.new('NodeGroupOutput')
        gl = ng.nodes.new('CompositorNodeGlare')
        for v in ('Bloom', 'Fog Glow'):   # 5.x: the type is a menu SOCKET
            try: gl.inputs['Type'].default_value = v; break
            except Exception: pass
        for nm, v in (('Threshold', 0.9), ('Strength', glare), ('Size', 0.6)):
            if nm in gl.inputs: gl.inputs[nm].default_value = v
        ng.links.new(rl.outputs['Image'], gl.inputs['Image']); ng.links.new(gl.outputs['Image'], out.inputs[0])
        sc.compositing_node_group = ng
        sc.render.use_compositing = True
        return True
    except Exception as ex:
        print('bloom n/a', ex); return False

def _nodes(mat):
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    return nt, nt.nodes, nt.links

# ------------------------------------------------------------------ materials
def mat_paint(name, color, shadow=None, grain=0.35, emission=0.0):
    """watercolour cel paint: light → 3 flat bands (Shader to RGB + constant ramp), pigment pooling from noise,
    a paper grain multiply. Reads like a painted illustration, not a 3D render."""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    nt, N, L = _nodes(m)
    out = N.new('ShaderNodeOutputMaterial'); out.location = (900, 0)
    dif = N.new('ShaderNodeBsdfDiffuse'); dif.location = (-600, 0)
    s2r = N.new('ShaderNodeShaderToRGB'); s2r.location = (-400, 0)
    L.new(dif.outputs[0], s2r.inputs[0])
    bw = N.new('ShaderNodeRGBToBW'); bw.location = (-220, 0); L.new(s2r.outputs[0], bw.inputs[0])
    ramp = N.new('ShaderNodeValToRGB'); ramp.location = (-40, 0); L.new(bw.outputs[0], ramp.inputs[0])
    cr = ramp.color_ramp; cr.interpolation = 'CONSTANT'
    sh = shadow or tuple(c * 0.38 for c in color[:3])
    mid = tuple((a + b) / 2 for a, b in zip(color[:3], sh))
    cr.elements[0].position = 0.0; cr.elements[0].color = (*sh, 1)
    cr.elements[1].position = 0.45; cr.elements[1].color = (*color[:3], 1)
    e = cr.elements.new(0.18); e.color = (*mid, 1)
    # pigment pooling + paper grain
    tc = N.new('ShaderNodeTexCoord'); tc.location = (-800, -400)
    nz = N.new('ShaderNodeTexNoise'); nz.location = (-600, -400); nz.inputs['Scale'].default_value = 3.0
    nz.inputs['Detail'].default_value = 6.0
    L.new(tc.outputs['Object'], nz.inputs['Vector'])
    gr = N.new('ShaderNodeTexNoise'); gr.location = (-600, -650); gr.inputs['Scale'].default_value = 180.0
    L.new(tc.outputs['Object'], gr.inputs['Vector'])
    pool = N.new('ShaderNodeMapRange'); pool.location = (-380, -400)
    pool.inputs['To Min'].default_value = 0.78; pool.inputs['To Max'].default_value = 1.12
    L.new(nz.outputs['Fac'], pool.inputs['Value'])
    grain_mr = N.new('ShaderNodeMapRange'); grain_mr.location = (-380, -650)
    grain_mr.inputs['To Min'].default_value = 1.0 - grain * 0.3; grain_mr.inputs['To Max'].default_value = 1.0
    L.new(gr.outputs['Fac'], grain_mr.inputs['Value'])
    mul1 = N.new('ShaderNodeMix'); mul1.data_type = 'RGBA'; mul1.blend_type = 'MULTIPLY'; mul1.location = (250, 0)
    mul1.inputs['Factor'].default_value = 1.0
    L.new(ramp.outputs['Color'], mul1.inputs['A']); L.new(pool.outputs['Result'], mul1.inputs['B'])
    mul2 = N.new('ShaderNodeMix'); mul2.data_type = 'RGBA'; mul2.blend_type = 'MULTIPLY'; mul2.location = (450, 0)
    mul2.inputs['Factor'].default_value = 1.0
    L.new(mul1.outputs['Result'], mul2.inputs['A']); L.new(grain_mr.outputs['Result'], mul2.inputs['B'])
    em = N.new('ShaderNodeEmission'); em.location = (650, 0)
    em.inputs['Strength'].default_value = 1.0 + emission
    L.new(mul2.outputs['Result'], em.inputs['Color']); L.new(em.outputs[0], out.inputs['Surface'])
    return m

def mat_ink(name='Ink', color=(0.03, 0.025, 0.03)):
    """the outline: backfaces only of a pushed-out shell (inverted hull)"""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    nt, N, L = _nodes(m)
    out = N.new('ShaderNodeOutputMaterial'); out.location = (400, 0)
    em = N.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (*color, 1)
    geo = N.new('ShaderNodeNewGeometry'); geo.location = (-400, 200)
    tr = N.new('ShaderNodeBsdfTransparent'); tr.location = (-200, 200)
    mix = N.new('ShaderNodeMixShader'); mix.location = (200, 0)
    L.new(geo.outputs['Backfacing'], mix.inputs[0]); L.new(tr.outputs[0], mix.inputs[1]); L.new(em.outputs[0], mix.inputs[2])
    L.new(mix.outputs[0], out.inputs['Surface'])
    m.use_backface_culling = False
    try: m.surface_render_method = 'BLENDED'
    except Exception: pass
    return m

def mat_glow(name, color, strength=6.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    nt, N, L = _nodes(m)
    out = N.new('ShaderNodeOutputMaterial'); em = N.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (*color, 1); em.inputs['Strength'].default_value = min(strength, 2.5)
    L.new(em.outputs[0], out.inputs['Surface'])
    return m

def mat_parchment(name='Parchment', base=(0.80, 0.68, 0.48), dark=(0.36, 0.24, 0.13)):
    """old paper: warm base, fibres, stains, burnt darker edges (UV vignette)"""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    nt, N, L = _nodes(m)
    out = N.new('ShaderNodeOutputMaterial'); out.location = (1000, 0)
    tc = N.new('ShaderNodeTexCoord'); tc.location = (-1000, 0)
    st = N.new('ShaderNodeTexNoise'); st.location = (-700, 200); st.inputs['Scale'].default_value = 2.2; st.inputs['Detail'].default_value = 8
    fb = N.new('ShaderNodeTexNoise'); fb.location = (-700, -100); fb.inputs['Scale'].default_value = 90; fb.inputs['Detail'].default_value = 3
    L.new(tc.outputs['UV'], st.inputs['Vector']); L.new(tc.outputs['UV'], fb.inputs['Vector'])
    # edge vignette from UV distance to centre
    sep = N.new('ShaderNodeSeparateXYZ'); sep.location = (-700, -400); L.new(tc.outputs['UV'], sep.inputs[0])
    def edge(ax):
        a = N.new('ShaderNodeMath'); a.operation = 'SUBTRACT'; a.inputs[1].default_value = 0.5; L.new(sep.outputs[ax], a.inputs[0])
        b = N.new('ShaderNodeMath'); b.operation = 'ABSOLUTE'; L.new(a.outputs[0], b.inputs[0]); return b
    ex, ey = edge('X'), edge('Y')
    mx = N.new('ShaderNodeMath'); mx.operation = 'MAXIMUM'; L.new(ex.outputs[0], mx.inputs[0]); L.new(ey.outputs[0], mx.inputs[1])
    vig = N.new('ShaderNodeMapRange'); vig.location = (-300, -400)
    vig.inputs['From Min'].default_value = 0.30; vig.inputs['From Max'].default_value = 0.5
    L.new(mx.outputs[0], vig.inputs['Value'])
    add = N.new('ShaderNodeMath'); add.operation = 'ADD'; add.location = (-100, -200)
    stm = N.new('ShaderNodeMapRange'); stm.inputs['From Min'].default_value = 0.45; stm.inputs['From Max'].default_value = 0.75
    stm.inputs['To Max'].default_value = 0.45; L.new(st.outputs['Fac'], stm.inputs['Value'])
    L.new(vig.outputs['Result'], add.inputs[0]); L.new(stm.outputs['Result'], add.inputs[1])
    mix = N.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.location = (200, 0)
    mix.inputs['A'].default_value = (*base, 1); mix.inputs['B'].default_value = (*dark, 1)
    L.new(add.outputs[0], mix.inputs['Factor'])
    gm = N.new('ShaderNodeMapRange'); gm.inputs['To Min'].default_value = 0.88; L.new(fb.outputs['Fac'], gm.inputs['Value'])
    mul = N.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 1
    mul.location = (450, 0); L.new(mix.outputs['Result'], mul.inputs['A']); L.new(gm.outputs['Result'], mul.inputs['B'])
    dif = N.new('ShaderNodeBsdfDiffuse'); dif.location = (700, 0); L.new(mul.outputs['Result'], dif.inputs['Color'])
    L.new(dif.outputs[0], out.inputs['Surface'])
    return m

# ------------------------------------------------------------------ helpers
def outline(obj, thick=0.012):
    """ink lines come from Freestyle now (ink_lines); kept as a no-op so callers stay simple"""
    return None
    """inverted-hull ink line around an object"""
    ink = mat_ink()
    if ink.name not in [s.material.name for s in obj.material_slots if s.material]:
        obj.data.materials.append(ink)
    mod = obj.modifiers.new('InkLine', 'SOLIDIFY')
    mod.thickness = -thick; mod.use_flip_normals = True; mod.offset = 1.0
    mod.material_offset = len(obj.data.materials) - 1
    return mod

def link(obj, sc=None):
    (sc or bpy.context.scene).collection.objects.link(obj); return obj

def cube(name, size, loc, mat=None, bevel=0.0):
    me = bpy.data.meshes.new(name); import bmesh
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); o.location = loc; link(o)
    if mat: me.materials.append(mat)
    if bevel:
        b = o.modifiers.new('Bevel', 'BEVEL'); b.width = bevel; b.segments = 3
    return o

def plane(name, size, loc, mat=None, rot=(0, 0, 0)):
    me = bpy.data.meshes.new(name); import bmesh
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
    uv = bm.loops.layers.uv.new()
    for f in bm.faces:
        for l in f.loops: l[uv].uv = (l.vert.co.x + 0.5, l.vert.co.y + 0.5)
    for v in bm.verts: v.co = Vector((v.co.x * size[0], v.co.y * size[1], 0))
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); o.location = loc; o.rotation_euler = rot; link(o)
    if mat: me.materials.append(mat)
    return o

def glyph(name, seed, center, scale, mat, depth=0.004, segs=5):
    """a Script glyph: a few angular strokes (original design: stems, hooks, a dot) as bevelled curves"""
    rnd = random.Random(seed)
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = depth; cu.bevel_resolution = 2
    for s in range(rnd.randint(2, 4)):
        sp = cu.splines.new('POLY'); n = rnd.randint(2, segs)
        sp.points.add(n - 1)
        p = Vector((rnd.uniform(-.5, .5), rnd.uniform(-.5, .5), 0))
        for i in range(n):
            sp.points[i].co = (center[0] + p.x * scale, center[1] + p.y * scale, center[2], 1)
            ang = rnd.choice([0, 45, 90, 135, 180, 225, 270, 315]) * math.pi / 180
            p += Vector((math.cos(ang), math.sin(ang), 0)) * rnd.uniform(.2, .45)
    o = bpy.data.objects.new(name, cu); link(o); cu.materials.append(mat)
    return o

def cam(name, loc, look, lens=50):
    c = bpy.data.cameras.new(name); c.lens = lens
    o = bpy.data.objects.new(name, c); link(o); o.location = loc
    d = Vector(look) - Vector(loc); o.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.camera = o
    return o

def light(name, kind, loc, energy, color=(1, 1, 1), size=0.2, look=None):
    l = bpy.data.lights.new(name, kind); l.energy = energy; l.color = color
    if hasattr(l, 'shadow_soft_size'): l.shadow_soft_size = size
    o = bpy.data.objects.new(name, l); link(o); o.location = loc
    if look: o.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return o

# ------------------------------------------------------------------ the Codex (original design)
def codex(loc=(0, 0, 0), open_deg=0.0, name='Codex'):
    """a heavy leather book: cover + spine + page block; gold corner plates; on the cover a gold sigil — a ring with
    THREE empty sockets (one lights per bond) around a central quill-glyph. Our emblem, not anyone else's."""
    leather = mat_paint('M_Leather', (0.55, 0.16, 0.09), grain=0.6)
    pages = mat_paint('M_Pages', (0.86, 0.78, 0.60), grain=0.2)
    gold = mat_paint('M_Gold', (0.95, 0.68, 0.22), shadow=(0.40, 0.22, 0.05), emission=0.4)
    W, D, T = 0.42, 0.58, 0.022
    root = bpy.data.objects.new(name, None); link(root); root.location = loc
    back = cube(name + '_Back', (W, D, T), (W / 2, 0, T / 2), leather, bevel=0.006); back.parent = root
    block = cube(name + '_Pages', (W - 0.02, D - 0.03, 0.08), (W / 2, 0, T + 0.04), pages, bevel=0.003); block.parent = root
    spine = cube(name + '_Spine', (0.03, D, 0.13), (0.0, 0, 0.065), leather, bevel=0.01); spine.parent = root
    hinge = bpy.data.objects.new(name + '_Hinge', None); link(hinge); hinge.parent = root; hinge.location = (0, 0, 0.12)
    hinge.rotation_euler = (0, -math.radians(open_deg), 0)
    front = cube(name + '_Front', (W, D, T), (W / 2, 0, T / 2), leather, bevel=0.006); front.parent = hinge
    for o in (back, block, spine, front): outline(o, 0.004)
    # sigil on the front cover (in the hinge's space, on top of the cover)
    ring = bpy.data.objects.new(name + '_Ring', bpy.data.curves.new(name + '_RingC', 'CURVE')); link(ring)
    rc = ring.data; rc.dimensions = '3D'; rc.bevel_depth = 0.004
    sp = rc.splines.new('POLY'); n = 64; sp.points.add(n); R = 0.11
    for i in range(n + 1):
        a = i / n * 2 * math.pi; sp.points[i].co = (W / 2 + R * math.cos(a), R * math.sin(a), T + 0.002, 1)
    rc.materials.append(gold); ring.parent = hinge
    sockets = []
    for k in range(3):
        a = math.pi / 2 + k * 2 * math.pi / 3
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.022, location=(0, 0, 0))
        s = bpy.context.active_object; s.name = f'{name}_Socket{k}'
        for c in s.users_collection: c.objects.unlink(s)
        link(s); s.parent = hinge; s.location = (W / 2 + R * math.cos(a), R * math.sin(a), T + 0.004); s.scale = (1, 1, .35)
        s.data.materials.append(mat_paint(f'M_SocketOff{k}', (0.06, 0.05, 0.06))); outline(s, 0.003); sockets.append(s)
    q = glyph(name + '_Quill', 7, (W / 2, 0, T + 0.003), 0.11, gold, depth=0.004); q.parent = hinge
    return root, hinge, sockets

def light_socket(sock, color=(1.0, 0.75, 0.25), strength=12):
    sock.data.materials[0] = mat_glow('M_SocketOn_' + sock.name, color, strength)

# ------------------------------------------------------------------ creatures (painted)
def creature(rel, loc, scale=1.0, color=None, rot_z=0.0):
    """import a Quaternius monster and repaint every material as watercolour cel paint + ink line"""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(CRE, rel + '.gltf'))
    new = [o for o in bpy.data.objects if o not in before]
    roots = [o for o in new if o.parent is None]
    for o in new:
        if o.type == 'MESH':
            for i, s in enumerate(o.material_slots):
                base = color or (0.8, 0.4, 0.2)
                try:
                    bsdf = s.material.node_tree.nodes.get('Principled BSDF')
                    if bsdf and not color: base = tuple(bsdf.inputs['Base Color'].default_value)[:3]
                except Exception: pass
                s.material = mat_paint(f'M_{o.name}_{i}', base)
            outline(o, 0.012)
    for r in roots: r.location = loc; r.scale = (scale,) * 3; r.rotation_euler[2] = rot_z
    return roots, new

def creature_painted_from_atlas(rel, loc, scale=1.0, rot_z=0.0):
    """keep the pack's palette atlas (its real colours) but run it through the cel/watercolour ramp"""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(CRE, rel + '.gltf'))
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        if o.type != 'MESH': continue
        for s in o.material_slots:
            m = s.material
            if not m or not m.use_nodes: continue
            N, L = m.node_tree.nodes, m.node_tree.links
            img = next((n for n in N if n.type == 'TEX_IMAGE'), None)
            out = next((n for n in N if n.type == 'OUTPUT_MATERIAL'), None)
            if not (img and out): continue
            img.interpolation = 'Closest'
            dif = N.new('ShaderNodeBsdfDiffuse'); s2r = N.new('ShaderNodeShaderToRGB'); bw = N.new('ShaderNodeRGBToBW')
            ramp = N.new('ShaderNodeValToRGB'); cr = ramp.color_ramp; cr.interpolation = 'CONSTANT'
            cr.elements[0].color = (0.42, 0.40, 0.48, 1); cr.elements[1].position = 0.4; cr.elements[1].color = (1.08, 1.04, 0.98, 1)
            e = cr.elements.new(0.15); e.color = (0.70, 0.68, 0.74, 1)
            mul = N.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 1
            em = N.new('ShaderNodeEmission')
            L.new(dif.outputs[0], s2r.inputs[0]); L.new(s2r.outputs[0], bw.inputs[0]); L.new(bw.outputs[0], ramp.inputs[0])
            L.new(img.outputs['Color'], mul.inputs['A']); L.new(ramp.outputs['Color'], mul.inputs['B'])
            L.new(mul.outputs['Result'], em.inputs['Color']); L.new(em.outputs[0], out.inputs['Surface'])
        outline(o, 0.015)
    roots = [o for o in new if o.parent is None]
    for r in roots: r.location = loc; r.scale = (scale,) * 3; r.rotation_euler[2] = rot_z
    return roots, new

# ------------------------------------------------------------------ look test
def look_test():
    """two stills to approve the look: (A) the Codex on a candle-lit desk, (B) a Spark rising off a glyph page"""
    os.makedirs(OUT, exist_ok=True)
    # A — the Codex
    sc = new_scene('SAGA_A')
    desk = plane('Desk', (6, 5), (0, 0, -0.001), mat_parchment('M_DeskPaper', (0.42, 0.27, 0.15), (0.12, 0.07, 0.04)))
    root, hinge, socks = codex((-0.21, 0, 0), open_deg=0.0)
    light_socket(socks[0])
    gold = mat_glow('M_GlyphGold', (1.0, 0.72, 0.25), 8)
    for i in range(14):
        a = i / 14 * 2 * math.pi; r = random.uniform(.45, .9)
        g = glyph(f'G{i}', i + 20, (r * math.cos(a), r * math.sin(a), 0.002), random.uniform(.05, .1), gold, depth=0.0025)
    light('Candle', 'POINT', (0.55, -0.35, 0.35), 60, (1.0, 0.62, 0.30), 0.05)
    light('Rim', 'POINT', (-0.6, 0.6, 0.5), 20, (0.35, 0.45, 1.0), 0.3)
    cam('CamA', (0.95, -0.85, 0.75), (0.0, 0.0, 0.05), 45)
    comp_bloom(sc); sc.render.filepath = os.path.join(OUT, 'look_A_codex.png')
    bpy.ops.render.render(write_still=True)
    # B — a Spark off the page
    sc = new_scene('SAGA_B')
    page = plane('Page', (9, 6), (0, 1.5, 0), mat_parchment())
    inkm = mat_glow('M_InkLine', (0.05, 0.035, 0.03), 1.0); gold = mat_glow('M_GlyphGold', (1.0, 0.72, 0.25), 6)
    for i in range(40):
        glyph(f'P{i}', 100 + i, (random.uniform(-1.4, 1.4), random.uniform(-.8, .8), 0.002), random.uniform(.05, .12),
              gold if i % 7 == 0 else inkm, depth=0.003)
    creature('Flying/Dragon', (0, 0.15, 0.32), 0.16, color=(0.93, 0.42, 0.16), rot_z=math.radians(-15))
    k = light('Key', 'SUN', (2, -2, 4), 3.0, (1.0, 0.9, 0.75), look=(0, 0, 0)); k.data.use_shadow = False
    cam('CamB', (0.0, -1.25, 0.62), (0, 0.15, 0.30), 38)
    comp_bloom(sc); sc.render.filepath = os.path.join(OUT, 'look_B_spark.png')
    bpy.ops.render.render(write_still=True)
    return [os.path.join(OUT, 'look_A_codex.png'), os.path.join(OUT, 'look_B_spark.png')]
