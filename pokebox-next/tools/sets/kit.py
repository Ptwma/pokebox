# Sigil & Spark v4 — shared helpers for the set scripts (tools/sets/set_*.py): kit pieces, painted-toon preview
# materials, simple props, ink preview render and the Unreal export (FBX + lights json → pbx_sets.import_set).
#   exec(open(os.path.join(os.path.dirname(__file__), 'kit.py')).read())   at the top of a set script
import bpy, os, sys, math, random
from mathutils import Vector, Euler

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
SRC = argv[0] if argv else r"E:\GAME-APP-DEV\POKEMON\PokeboxNext_src"
OUT = argv[1] if len(argv) > 1 else os.path.join(SRC, 'sets_render', 'pier_test.png')
CAMNAME = argv[2] if len(argv) > 2 else 'wide'
EXPORT = CAMNAME == 'export'   # export mode: no toon nodes, no character; writes <OUT>.fbx + <OUT>.json for Unreal (pbx_sets.py)
KIT = os.path.join(SRC, 'environment', 'quaternius', 'Medieval Village MegaKit[Standard]', 'glTF')
CH = os.path.join(SRC, 'characters', 'quaternius')
R = random.Random(4)
SETNAME = os.path.splitext(os.path.basename(OUT))[0]

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
_cache = {}
NOINK = bpy.data.collections.new('NoInk'); sc.collection.children.link(NOINK)
def noink(o):
    for c in list(o.users_collection): c.objects.unlink(o)
    NOINK.objects.link(o)

def piece(name, loc, rot=0.0, scale=1.0):
    """place a kit piece (linked duplicate of a cached import); rot in degrees about Z"""
    if name not in _cache:
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=os.path.join(KIT, name + '.gltf'))
        new = [o for o in bpy.data.objects if o not in before]
        src = next(o for o in new if o.type == 'MESH')
        for o in new:
            if o is not src: bpy.data.objects.remove(o)
        src.parent = None; _cache[name] = src; src.location = loc; src.rotation_euler = (0, 0, math.radians(rot)); src.scale = (scale,) * 3
        return src
    o = _cache[name].copy(); sc.collection.objects.link(o)
    o.location = loc; o.rotation_euler = (0, 0, math.radians(rot)); o.scale = (scale,) * 3
    return o

def toonify(mat, tint=(1, 1, 1), shadow=(0.10, 0.12, 0.24)):
    if EXPORT:   # Unreal draws the look with its own post-process; keep the kit's PBR materials (tints baked into base colour)
        if mat and mat.get('tint') and mat.use_nodes:
            b = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if b and not b.inputs['Base Color'].is_linked: b.inputs['Base Color'].default_value = tuple(c * t for c, t in zip(b.inputs['Base Color'].default_value, (*mat['tint'], 1)))
        return
    """light → 3 hard bands (shadow tinted cold, lit tinted warm) × the kit's own colour texture = paint"""
    if not mat or not mat.use_nodes or mat.get('toon'): return
    nt = mat.node_tree; N, L = nt.nodes, nt.links
    out = next((n for n in N if n.type == 'OUTPUT_MATERIAL'), None)
    bsdf = next((n for n in N if n.type == 'BSDF_PRINCIPLED'), None)
    if not out or not bsdf: return
    col_src = bsdf.inputs['Base Color'].links[0].from_socket if bsdf.inputs['Base Color'].is_linked else None
    base = tuple(bsdf.inputs['Base Color'].default_value)
    diff = N.new('ShaderNodeBsdfDiffuse'); s2r = N.new('ShaderNodeShaderToRGB')
    ramp = N.new('ShaderNodeValToRGB'); cr = ramp.color_ramp; cr.interpolation = 'CONSTANT'
    cr.elements[0].position = 0.0; cr.elements[0].color = (*shadow, 1)
    cr.elements[1].position = 0.12; cr.elements[1].color = (0.36, 0.30, 0.36, 1)
    e = cr.elements.new(0.40); e.color = (1.0, 0.80, 0.62, 1)
    bw = N.new('ShaderNodeRGBToBW'); mul = N.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 1.0
    emit = N.new('ShaderNodeEmission')
    L.new(diff.outputs[0], s2r.inputs[0]); L.new(s2r.outputs['Color'], bw.inputs[0]); L.new(bw.outputs[0], ramp.inputs[0])
    if col_src:
        if mat.get('tint'):
            tm = N.new('ShaderNodeMix'); tm.data_type = 'RGBA'; tm.blend_type = 'MULTIPLY'; tm.inputs['Factor'].default_value = 1.0
            L.new(col_src, tm.inputs[6]); tm.inputs[7].default_value = (*mat['tint'], 1); L.new(tm.outputs[2], mul.inputs[6])
        else: L.new(col_src, mul.inputs[6])
    else: mul.inputs[6].default_value = tuple(b * t for b, t in zip(base, (*mat.get('tint', (1, 1, 1)), 1)))
    L.new(ramp.outputs['Color'], mul.inputs[7])
    L.new(mul.outputs[2], emit.inputs['Color']); emit.inputs['Strength'].default_value = 1.0
    L.new(emit.outputs[0], out.inputs['Surface'])
    mat['toon'] = 1

def flat(obj, rgb, emit=1.0):
    m = bpy.data.materials.new(obj.name + '_M'); m.use_nodes = True
    b = m.node_tree.nodes.get('Principled BSDF'); b.inputs['Base Color'].default_value = (*rgb, 1)
    obj.data.materials.clear(); obj.data.materials.append(m); toonify(m)

def mat(name, rgb, rough=0.8):
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes.get('Principled BSDF'); b.inputs['Base Color'].default_value = (*rgb, 1); b.inputs['Roughness'].default_value = rough
    toonify(m); return m

def glow(name, rgb, strength=3.0):
    """emissive material; the export keeps the name so pbx_sets swaps in an Unreal emissive (names: LanternGlass, RoomLit,
    RoomDark, LampRoom, Candle, JarGlow, ...)"""
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (*rgb, 1); em.inputs['Strength'].default_value = strength
    nt.links.new(em.outputs[0], nt.nodes['Material Output'].inputs['Surface']); m['toon'] = 1
    if EXPORT:   # FBX keeps a principled base colour; Unreal re-assigns by name anyway
        b = nt.nodes.get('Principled BSDF')
        if b: b.inputs['Base Color'].default_value = (*rgb, 1); nt.links.new(b.outputs[0], nt.nodes['Material Output'].inputs['Surface'])
    return m

_PRIM = {}
def _prim_mesh(kind, verts=12):
    """one shared unit mesh per primitive kind (data API, no bpy.ops: thousands of props stay fast)"""
    key = (kind, verts)
    if key in _PRIM: return _PRIM[key]
    import bmesh
    bm = bmesh.new()
    if kind == 'cube': bmesh.ops.create_cube(bm, size=1.0)
    else: bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=verts, radius1=1.0, radius2=1.0, depth=1.0)
    me = bpy.data.meshes.new(f'prim_{kind}_{verts}'); bm.to_mesh(me); bm.free(); _PRIM[key] = me
    return me

_MESH_BY_MAT = {}
def _inst(name, me, m, loc, scale, rot):
    # one mesh per (primitive, material) with the material on the mesh data — FBX drops object-linked slots
    key = (me.name, m.name if m else '')
    mm = _MESH_BY_MAT.get(key)
    if mm is None:
        mm = me.copy(); mm.materials.clear(); mm.materials.append(m); _MESH_BY_MAT[key] = mm
    o = bpy.data.objects.new(name, mm); sc.collection.objects.link(o)
    o.location = loc; o.scale = scale; o.rotation_euler = tuple(math.radians(r) for r in rot)
    return o

def box(name, size, loc, m, rot=(0, 0, 0)):
    return _inst(name, _prim_mesh('cube'), m, loc, size, rot)

def cyl(name, r, h, loc, m, verts=12, rot=(0, 0, 0)):
    return _inst(name, _prim_mesh('cyl', verts), m, loc, (r, r, h), rot)

def point(loc, energy, color, radius=0.15):
    bpy.ops.object.light_add(type='POINT', location=loc); L = bpy.context.object
    L.data.energy = energy; L.data.color = color; L.data.shadow_soft_size = radius; return L

def spot(loc, target, energy, color, angle=40):
    bpy.ops.object.light_add(type='SPOT', location=loc); L = bpy.context.object
    L.data.energy = energy; L.data.color = color; L.data.spot_size = math.radians(angle); L.data.spot_blend = 0.6
    L.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); return L

def finish(cams, marks=None, world_rgb=(0.02, 0.025, 0.04), exposure=-0.4, drop=()):
    """preview render (cams[CAMNAME]) with ink lines, or in export mode write <OUT>.fbx + <OUT>.json and quit"""
    for m in bpy.data.materials: toonify(m)
    if EXPORT:
        import json
        lights = [{'pos': [round(o.location.x * 100, 1), round(-o.location.y * 100, 1), round(o.location.z * 100, 1)], 'energy': o.data.energy,
                   'color': list(o.data.color), 'type': o.data.type} for o in bpy.data.objects if o.type == 'LIGHT' and o.data.type in ('POINT', 'SPOT')]
        for o in [o for o in bpy.data.objects if o.type == 'MESH' and o.parent is not None]:
            mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
        for o in [o for o in bpy.data.objects if o.type in ('CAMERA', 'LIGHT') or o in drop]:
            bpy.data.objects.remove(o)
        fbx = os.path.splitext(OUT)[0] + '.fbx'; os.makedirs(os.path.dirname(fbx), exist_ok=True)
        bpy.ops.export_scene.fbx(filepath=fbx, use_selection=False, object_types={'MESH'}, apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS',
                                 path_mode='COPY', embed_textures=True, mesh_smooth_type='FACE', use_mesh_modifiers=True, axis_forward='-Z', axis_up='Y')
        json.dump({'lights': lights, 'marks': marks or {}}, open(os.path.splitext(OUT)[0] + '.json', 'w'), indent=1)
        print('EXPORTED', fbx, len(lights), 'lights'); raise SystemExit(0)
    w = bpy.data.worlds.new('W'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs['Color'].default_value = (*world_rgb, 1)
    sc.render.use_freestyle = True; sc.render.line_thickness_mode = 'ABSOLUTE'; sc.render.line_thickness = 1.6
    fs = sc.view_layers[0].freestyle_settings
    ls = fs.linesets[0] if fs.linesets else fs.linesets.new('ink')
    ls.select_by_visibility = True; ls.select_by_collection = True; ls.collection = NOINK; ls.collection_negation = 'EXCLUSIVE'
    if ls.linestyle is None: ls.linestyle = bpy.data.linestyles.new('Ink')
    ls.linestyle.color = (0.03, 0.02, 0.03); ls.linestyle.thickness = 1.8
    p, t, lens = cams[CAMNAME]
    bpy.ops.object.camera_add(location=p); cam = bpy.context.object; cam.data.lens = lens
    cam.rotation_euler = (Vector(t) - Vector(p)).to_track_quat('-Z', 'Y').to_euler(); sc.camera = cam
    sc.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE'
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1600, 900, 100
    sc.view_settings.view_transform = 'Standard'; sc.view_settings.exposure = exposure
    os.makedirs(os.path.dirname(OUT), exist_ok=True); sc.render.filepath = OUT
    bpy.ops.render.render(write_still=True); print('RENDERED', OUT)

# ------------------------------------------------------------------ dressing props from the local CC0 kits
# (Quaternius medieval props, Kenney pirate / town / survival / food, Poly Haven models) — owner 2026-11-06: "put objects in
# every scene, it should look normal, a little full, not empty".
KITS = os.path.join(SRC, 'kits'); PHM = os.path.join(SRC, 'polyhaven', 'models')
_PROPIDX = None
def _prop_index():
    global _PROPIDX
    if _PROPIDX is not None: return _PROPIDX
    idx = {}
    for root in (KITS, PHM):
        for dp, dn, fn in os.walk(root):
            for f in fn:
                n, e = os.path.splitext(f); e = e.lower()
                if e not in ('.glb', '.gltf', '.fbx'): continue
                n = n.replace('_2k', '')
                key = os.path.basename(os.path.dirname(dp)) if False else None
                rank = {'.glb': 0, '.gltf': 1, '.fbx': 2}[e]
                kitname = os.path.relpath(dp, root).split(os.sep)[0]
                for k in (n, f'{kitname}/{n}'):
                    if k not in idx or rank < idx[k][0]: idx[k] = (rank, os.path.join(dp, f))
    _PROPIDX = idx; return idx

_IMGIDX = None
def _fix_images(near):
    """FBX props (Quaternius) reference textures by an old absolute path: re-point missing images to the png found in the kits"""
    global _IMGIDX
    if _IMGIDX is None:
        _IMGIDX = {}
        for root in (KITS, PHM):
            for dp, dn, fn in os.walk(root):
                for f in fn:
                    if f.lower().endswith(('.png', '.jpg', '.jpeg', '.tga')): _IMGIDX.setdefault(f.lower(), os.path.join(dp, f))
    for im in bpy.data.images:
        if im.source != 'FILE' or (im.filepath and os.path.exists(bpy.path.abspath(im.filepath))): continue
        b = os.path.basename(im.filepath.replace('\\', '/')).lower() or (im.name.lower() + '.png')
        hit = _IMGIDX.get(b) or _IMGIDX.get(os.path.splitext(b)[0] + '.png')
        if hit: im.filepath = hit; im.reload()

def prop(name, loc, rot=0.0, height=None, scale=1.0, tilt=(0, 0)):
    """place a kit prop by file name ('Barrel', 'k_pirate/crate', 'lifebuoy'); height (m) normalises its size"""
    idx = _prop_index()
    if name not in idx: print('PROP MISSING', name); return None
    path = idx[name][1]; before = set(bpy.data.objects)
    try:
        if path.lower().endswith('.fbx'): bpy.ops.import_scene.fbx(filepath=path)
        else: bpy.ops.import_scene.gltf(filepath=path)
    except Exception as ex: print('PROP FAIL', name, ex); return None
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == 'MESH']
    keep = []
    for o in new:
        if o.type in ('MESH', 'EMPTY'): keep.append(o)
        else:
            for ch in list(o.children):
                mw = ch.matrix_world.copy(); ch.parent = None; ch.matrix_world = mw
            bpy.data.objects.remove(o)
    new = keep
    _fix_images(os.path.dirname(path))
    root = bpy.data.objects.new('P_' + name.split('/')[-1], None); sc.collection.objects.link(root)
    for o in new:
        if o.parent is None: o.parent = root
    bpy.context.view_layer.update()
    if height and meshes:
        zs = [(o.matrix_world @ Vector(c)).z for o in meshes for c in o.bound_box]
        h = max(zs) - min(zs)
        if h > 1e-4: scale = scale * height / h
    root.scale = (scale,) * 3; root.location = loc; root.rotation_euler = (math.radians(tilt[0]), math.radians(tilt[1]), math.radians(rot))
    bpy.context.view_layer.update()
    if meshes:   # sit on loc.z
        zmin = min((o.matrix_world @ Vector(c)).z for o in meshes for c in o.bound_box)
        root.location.z += loc[2] - zmin
    return root
