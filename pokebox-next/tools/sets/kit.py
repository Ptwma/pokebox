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
        src.parent = None; src.rotation_mode = 'XYZ'; _cache[name] = src   # glTF imports are QUATERNION: rotation_euler was ignored
        src.location = loc; src.rotation_euler = (0, 0, math.radians(rot)); src.scale = (scale,) * 3
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


# ------------------------------------------------------------------ DETAIL builder (owner 19:59: "books and things have no detail,
# props stuck in walls, empty bookcases — I want details"). Telltale-style set dressing: chunky, readable shapes with many
# small parts (bands, page blocks, labels, drips), varied heights and angles, nothing floating, nothing clipping, no empty shelf.
# Everything is merged into one multi-material mesh (fast in Blender, one draw-friendly mesh in Unreal).
import bmesh
from mathutils import Matrix
_DB = {'bm': None, 'mats': [], 'idx': {}}
def _dmat(m):
    i = _DB['idx'].get(m.name)
    if i is None: i = len(_DB['mats']); _DB['mats'].append(m); _DB['idx'][m.name] = i
    return i
def _M(loc=(0, 0, 0), rz=0.0, rx=0.0, ry=0.0):
    return Matrix.Translation(Vector(loc)) @ Euler((math.radians(rx), math.radians(ry), math.radians(rz)), 'ZYX').to_matrix().to_4x4()
def dbox(M, size, center, m, rz=0.0, rx=0.0, ry=0.0):
    """a box (size = full extents) at center in the frame M, rotated locally; merged into the detail mesh"""
    if _DB['bm'] is None: _DB['bm'] = bmesh.new()
    bm = _DB['bm']; T = M @ _M(center, rz, rx, ry) @ Matrix.Diagonal((*size, 1))
    vs = [bm.verts.new(T @ Vector((x * .5, y * .5, z * .5))) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
    mi = _dmat(m)
    for f in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
        bm.faces.new([vs[i] for i in f]).material_index = mi
def dcyl(M, r, h, center, m, seg=10, rz=0.0, rx=0.0, ry=0.0, r2=None):
    if _DB['bm'] is None: _DB['bm'] = bmesh.new()
    bm = _DB['bm']; T = M @ _M(center, rz, rx, ry); r2 = r if r2 is None else r2
    lo = [bm.verts.new(T @ Vector((r * math.cos(a), r * math.sin(a), -h / 2))) for a in [k * math.tau / seg for k in range(seg)]]
    hi = [bm.verts.new(T @ Vector((r2 * math.cos(a), r2 * math.sin(a), h / 2))) for a in [k * math.tau / seg for k in range(seg)]]
    mi = _dmat(m)
    for k in range(seg):
        bm.faces.new((lo[k], lo[(k + 1) % seg], hi[(k + 1) % seg], hi[k])).material_index = mi
    bm.faces.new(list(reversed(lo))).material_index = mi; bm.faces.new(hi).material_index = mi
def flush_details():
    if _DB['bm'] is None: return None
    me = bpy.data.meshes.new('Details'); _DB['bm'].normal_update(); _DB['bm'].to_mesh(me); _DB['bm'].free(); _DB['bm'] = None
    for m in _DB['mats']: me.materials.append(m)
    o = bpy.data.objects.new('Details', me); sc.collection.objects.link(o); _DB['mats'] = []; _DB['idx'] = {}
    return o

# palette for books: worn leathers + cloth, gilt, page cream, labels
_BK = None
def _bookmats():
    global _BK
    if _BK: return _BK
    cols = [(0.36, 0.07, 0.05), (0.22, 0.05, 0.04), (0.08, 0.12, 0.26), (0.05, 0.08, 0.16), (0.10, 0.20, 0.11), (0.06, 0.12, 0.07),
            (0.30, 0.19, 0.09), (0.18, 0.11, 0.06), (0.06, 0.05, 0.05), (0.42, 0.32, 0.18), (0.25, 0.10, 0.20), (0.40, 0.36, 0.30)]
    _BK = {'cov': [mat(f'BookCover{i}', c, 0.7) for i, c in enumerate(cols)], 'gilt': mat('Gilt', (0.62, 0.45, 0.16), 0.35),
           'page': mat('Pages', (0.80, 0.73, 0.58)), 'label': mat('BookLabel', (0.78, 0.70, 0.52)), 'ink': mat('InkBlack', (0.02, 0.02, 0.02))}
    return _BK

def book(M, loc, t, d, h, cov=None, rz=0.0, rx=0.0, ry=0.0, rng=None, lying=False):
    """one book in frame M: thickness t (x), depth d (y, spine at -y facing the viewer), height h (z), base at loc.
    Two boards + spine + recessed page block + raised spine bands (gilt) + sometimes a label / gilt title strip."""
    rng = rng or R; B = _bookmats(); cov = cov or rng.choice(B['cov']); c = max(0.004, t * 0.09)
    F = M @ _M(loc, rz, rx, ry)
    if lying: F = F @ Matrix.Translation((0, 0, t / 2)) @ _M((0, 0, 0), 0, 0, 90) @ Matrix.Translation((0, 0, -h / 2))   # thickness vertical
    z = h / 2
    dbox(F, (c, d, h), (-t / 2 + c / 2, 0, z), cov); dbox(F, (c, d, h), (t / 2 - c / 2, 0, z), cov)       # boards
    dbox(F, (t, c * 1.2, h), (0, -d / 2 + c * 0.6, z), cov)                                                # spine
    dbox(F, (t - 2 * c, d - c * 1.8, h - 2 * c), (0, c * 0.6, z), B['page'])                             # pages
    nb = rng.choice((2, 3, 4)) if h > 0.18 else 2
    for k in range(nb):                                                                                     # raised bands
        zz = h * (0.18 + 0.64 * k / max(1, nb - 1)); dbox(F, (t * 1.02, c * 1.6, 0.010), (0, -d / 2 - c * 0.2, zz), B['gilt'])
    r = rng.random()
    if r < 0.45: dbox(F, (t * 0.72, 0.003, h * 0.16), (0, -d / 2 - c * 0.25, h * 0.62), B['label'])         # paper label
    elif r < 0.75: dbox(F, (t * 0.5, 0.003, h * 0.30), (0, -d / 2 - c * 0.25, h * 0.55), B['gilt'])         # gilt title
    if rng.random() < 0.3: dbox(F, (t * 1.02, c * 1.6, 0.014), (0, -d / 2 - c * 0.2, h * 0.06), B['gilt'])  # foot band

def book_row(M, x0, x1, depth, hmax, rng=None, gaps=True, objs=True):
    """fill a shelf run from x0 to x1 (frame M, shelf top at z=0, front edge at y=-depth/2) with books: runs of upright
    books in families of similar height, a book leaning on its neighbour, small horizontal stacks, a gap now and then,
    and an object (jar / candle stub / scroll / skull-sized box) at the ends. Never leaves the run empty."""
    rng = rng or R; B = _bookmats(); x = x0 + rng.uniform(0, 0.03)
    fam_h = rng.uniform(0.7, 0.95) * hmax; fam_c = rng.choice(B['cov']); fam_n = 0
    while x < x1 - 0.03:
        r = rng.random(); room = x1 - x
        if fam_n <= 0:
            fam_h = rng.uniform(0.62, 0.96) * hmax; fam_c = rng.choice(B['cov']) if rng.random() < 0.5 else None; fam_n = rng.randint(3, 9)
        if gaps and r < 0.05 and room > 0.25:
            x += rng.uniform(0.06, 0.16); continue
        if r < 0.11 and room > 0.32:                                     # horizontal stack
            w = rng.uniform(0.20, min(0.30, depth * 1.1)); zz = 0.0
            for k in range(rng.randint(2, 5)):
                tk = rng.uniform(0.03, 0.06)
                book(M, (x + w / 2, rng.uniform(-0.01, 0.02), zz), tk, rng.uniform(0.6, 0.9) * depth, w * rng.uniform(0.85, 1.0), rz=rng.uniform(-8, 8), lying=True, rng=rng)
                zz += tk
                if zz > hmax * 0.8: break
            x += w + 0.02; continue
        if objs and r < 0.16 and room > 0.2:                             # an object between the books
            k = rng.random()
            if k < 0.4:
                jm = JARMAT if (JARMAT is not None and rng.random() < 0.6) else B['page']; jh = rng.uniform(0.12, min(0.26, hmax * 0.8))
                dcyl(M, 0.05 + jh * 0.15, jh, (x + 0.08, 0, jh / 2), jm, 10); dcyl(M, 0.035, 0.03, (x + 0.08, 0, jh + 0.015), B['cov'][6], 8); x += 0.17
            elif k < 0.7:
                for j in range(rng.randint(2, 4)): dcyl(M, 0.025, depth * 0.85, (x + 0.03, 0, 0.026 + j * 0.05 * 0.9), B['label'], 8, rx=90)
                x += 0.08
            else: dbox(M, (0.12, depth * 0.7, 0.10), (x + 0.07, 0, 0.05), B['cov'][8]); dbox(M, (0.13, depth * 0.72, 0.012), (x + 0.07, 0, 0.1), B['gilt']); x += 0.15
            continue
        t = rng.uniform(0.028, 0.075); h = min(hmax, fam_h * rng.uniform(0.9, 1.06)); d = min(depth, h * rng.uniform(0.62, 0.8))
        if r < 0.19 and room > 0.2:                                      # leaning on the next book
            ang = rng.uniform(10, 22); book(M, (x + h * math.sin(math.radians(ang)) / 2 + t / 2, (depth - d) / -2 + 0.005, 0), t, d, h * 0.97, cov=fam_c, ry=ang, rng=rng)
            x += h * math.sin(math.radians(ang)) + t + 0.004; fam_n -= 1; continue
        book(M, (x + t / 2, -(depth - d) / 2 + rng.uniform(0, 0.02), 0), t, d, h, cov=fam_c if (fam_c and rng.random() < 0.7) else None, rz=rng.uniform(-2, 2), rng=rng)
        x += t + rng.uniform(0.0, 0.004); fam_n -= 1

JARMAT = None   # set by a set script: glowing jars between the books
_BC = []   # registered bookcases (for the wall check)
def bookcase(loc, rz=0.0, w=1.6, h=2.5, d=0.42, levels=5, fill=1.0, back=True, rng=None, m=None, trim=None):
    """a detailed bookcase (plinth, sides, crown, back panel, shelves with a lip) FULL of books; front faces -y in its frame
    (rz=0: front looks toward -Y). Registered so unclip() keeps it out of walls."""
    rng = rng or R; m = m or mat('CaseWood', (0.20, 0.12, 0.07)); trim = trim or mat('CaseTrim', (0.13, 0.08, 0.05))
    rec = {'loc': list(loc), 'rz': rz, 'w': w, 'h': h, 'd': d}; _BC.append(rec)
    def build():
        M = _M(rec['loc'], rec['rz']); st = 0.05
        dbox(M, (w + 0.06, d + 0.04, 0.12), (0, 0, 0.06), trim)                                   # plinth
        dbox(M, (w + 0.14, d + 0.10, 0.06), (0, -0.02, h + 0.03), trim)                           # crown
        dbox(M, (w + 0.08, d + 0.06, 0.05), (0, -0.01, h - 0.02), m)
        for sx in (-1, 1): dbox(M, (st, d, h), (sx * (w / 2 - st / 2), 0, h / 2), m)              # sides
        for sx in (-1, 1): dbox(M, (0.03, 0.03, h - 0.15), (sx * (w / 2 - st / 2), -d / 2 - 0.012, h / 2 + 0.05), trim)  # pilasters
        if back: dbox(M, (w, 0.02, h), (0, d / 2 - 0.01, h / 2), trim)
        z0 = 0.12; gap = (h - 0.17 - z0) / levels
        for lv in range(levels + 1):
            zz = z0 + lv * gap
            dbox(M, (w - 2 * st, d - 0.02, 0.03), (0, -0.01, zz), m); dbox(M, (w - 2 * st, 0.02, 0.05), (0, -d / 2 + 0.005, zz + 0.005), trim)
            if lv < levels and rng.random() < fill:
                book_row(M @ _M((0, 0.0, zz + 0.015)), -w / 2 + st + 0.01, w / 2 - st - 0.01, d - 0.06, gap - 0.06, rng=rng)
    rec['build'] = build; return rec

def candle(loc, h=0.2, r=0.03, lit=True, M=None):
    """a candle with a melted drip collar and a flame"""
    M = M or Matrix(); wax = mat('Wax', (0.92, 0.88, 0.76)); fl = glow('Candle', (1.0, 0.62, 0.22), 6.0)
    dcyl(M, r, h, (loc[0], loc[1], loc[2] + h / 2), wax, 10); dcyl(M, r * 1.5, 0.012, (loc[0], loc[1], loc[2] + 0.006), wax, 10)
    dcyl(M, r * 1.08, 0.03, (loc[0], loc[1], loc[2] + h - 0.02), wax, 10)
    if lit: dcyl(M, r * 0.45, 0.05, (loc[0], loc[1], loc[2] + h + 0.03), fl, 6, r2=0.002)

def papers(loc, n=5, spread=0.25, rng=None, M=None):
    rng = rng or R; M = M or Matrix(); B = _bookmats()
    for k in range(n): dbox(M, (0.21, 0.29, 0.002), (loc[0] + rng.uniform(-spread, spread), loc[1] + rng.uniform(-spread, spread), loc[2] + 0.001 + k * 0.002), B['page'], rz=rng.uniform(0, 180))

def open_book(loc, rz=0.0, w=0.36, d=0.26, M=None, tilt=0.0):
    """an open book: two page-block halves bending up toward the gutter, cover under them, a ribbon"""
    M = (M or Matrix()) @ _M(loc, rz, tilt); B = _bookmats(); cov = B['cov'][0]
    dbox(M, (w + 0.02, d + 0.02, 0.008), (0, 0, 0.004), cov)
    for sx in (-1, 1):
        dbox(M, (w / 2 - 0.01, d, 0.022), (sx * w / 4, 0, 0.02), B['page'], ry=sx * -6)
        for k in range(3): dbox(M, (w / 2 - 0.06, 0.004, 0.0015), (sx * w / 4, -d / 3 + k * 0.03, 0.033 + 0.001), B['ink'], ry=sx * -6)
    dbox(M, (0.012, 0.004, 0.14), (0.02, -d / 2 - 0.002, -0.05), mat('Ribbon', (0.5, 0.05, 0.05)))

def book_stack(loc, n=None, rz=0.0, rng=None, M=None):
    rng = rng or R; M = M or Matrix(); zz = 0.0; n = n or rng.randint(3, 7)
    for k in range(n):
        t = rng.uniform(0.035, 0.07); h = rng.uniform(0.22, 0.34)
        book(M, (loc[0], loc[1], loc[2] + zz), t, h * 0.72, h, rz=rz + rng.uniform(-12, 12), lying=True, rng=rng); zz += t

def unclip(margin=0.03, passes=4, extra=(), ref=None):
    """keep dressing out of walls and out of each other.
    1) every dressing prop (P_* roots) and registered bookcase is pushed out of the walls (kit pieces named Wall*) along the
       wall's thin axis, toward ref (the mean camera position: the side of the wall the audience sees);
    2) props standing on the same level (same floor/table height) that interpenetrate: the smaller one steps aside."""
    bpy.context.view_layer.update()
    ref = Vector(ref) if ref is not None else Vector((0, 0, 0))
    def bb(objs):
        pts = [o.matrix_world @ Vector(c) for o in objs if o.type == 'MESH' for c in o.bound_box]
        if not pts: return None
        return [min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts), max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)]
    walls = [bb([o]) for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith('Wall') and 'Arch' not in o.name]
    walls += [bb([o]) for o in extra]
    walls = [w for w in walls if w]
    def movers():
        out = []
        for r in [o for o in bpy.data.objects if o.name.startswith('P_') and o.parent is None]:
            b = bb(list(r.children_recursive))
            if b: out.append(['prop', r, b])
        for rec in _BC:
            ca, sa = math.cos(math.radians(rec['rz'])), math.sin(math.radians(rec['rz']))
            hx = abs(ca) * rec['w'] / 2 + abs(sa) * rec['d'] / 2 + 0.07; hy = abs(sa) * rec['w'] / 2 + abs(ca) * rec['d'] / 2 + 0.07
            x, y, z = rec['loc']; out.append(['case', rec, [x - hx, y - hy, z, x + hx, y + hy, z + rec['h']]])
        return out
    def move(it, d):
        kind, o, b = it
        if kind == 'prop': o.location += d
        else: o['loc'][0] += d.x; o['loc'][1] += d.y
        it[2] = [b[0] + d.x, b[1] + d.y, b[2], b[3] + d.x, b[4] + d.y, b[5]]
    def nm(it): return it[1].name if it[0] == 'prop' else 'Bookcase@%s' % [round(v, 1) for v in it[1]['loc']]
    moved = 0
    for _ in range(passes):
        n0 = moved; M_ = movers()
        for it in M_:                                                   # 1) walls
            for w in walls:
                b = it[2]
                ox = min(b[3], w[3]) - max(b[0], w[0]); oy = min(b[4], w[4]) - max(b[1], w[1]); oz = min(b[5], w[5]) - max(b[2], w[2])
                if ox <= 0.005 or oy <= 0.005 or oz <= 0.05: continue
                wx, wy = (w[0] + w[3]) / 2, (w[1] + w[4]) / 2
                if (w[3] - w[0]) < (w[4] - w[1]):   # wall runs along Y: move in X to the audience side
                    d = Vector((w[3] - b[0] + margin, 0, 0)) if ref.x >= wx else Vector((w[0] - b[3] - margin, 0, 0))
                else:
                    d = Vector((0, w[4] - b[1] + margin, 0)) if ref.y >= wy else Vector((0, w[1] - b[4] - margin, 0))
                if d.length > 0.6: print('BIGMOVE', nm(it), [round(v, 2) for v in d])
                move(it, d); moved += 1
        props = [it for it in M_ if it[0] == 'prop']
        for i in range(len(props)):                                     # 2) prop vs prop on the same level
            for j in range(i + 1, len(props)):
                a_, c_ = props[i][2], props[j][2]
                if abs(a_[2] - c_[2]) > 0.06: continue
                ox = min(a_[3], c_[3]) - max(a_[0], c_[0]); oy = min(a_[4], c_[4]) - max(a_[1], c_[1])
                if ox <= 0.01 or oy <= 0.01: continue
                fa = (a_[3] - a_[0]) * (a_[4] - a_[1]); fc = (c_[3] - c_[0]) * (c_[4] - c_[1])
                small, big = (props[i], props[j]) if fa < fc else (props[j], props[i])
                sb, bb_ = small[2], big[2]
                if ox < oy: d = Vector(((ox + 0.02) * (1 if (sb[0] + sb[3]) >= (bb_[0] + bb_[3]) else -1), 0, 0))
                else: d = Vector((0, (oy + 0.02) * (1 if (sb[1] + sb[4]) >= (bb_[1] + bb_[4]) else -1), 0))
                move(small, d); moved += 1
        bpy.context.view_layer.update()
        if moved == n0: break
    print('UNCLIP moved', moved)
    L = movers()
    for i in range(len(L)):
        for j in range(i + 1, len(L)):
            a_, c_ = L[i][2], L[j][2]
            if L[i][0] == 'case' and L[j][0] == 'case': continue
            ox = min(a_[3], c_[3]) - max(a_[0], c_[0]); oy = min(a_[4], c_[4]) - max(a_[1], c_[1]); oz = min(a_[5], c_[5]) - max(a_[2], c_[2])
            if ox > 0.08 and oy > 0.08 and oz > 0.08: print('OVERLAP', nm(L[i]), nm(L[j]), round(ox, 2), round(oy, 2))

def flat_colors():
    """untextured materials → {name: [r, g, b, roughness]} so Unreal gets exact colours (FBX diffuse import is unreliable)"""
    import re as _re
    out = {}
    for m in bpy.data.materials:
        if not m.use_nodes: continue
        b = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if not b or b.inputs['Base Color'].is_linked: continue
        c = b.inputs['Base Color'].default_value
        out[_re.sub(r'\.\d+$', '', m.name)] = [round(c[0], 4), round(c[1], 4), round(c[2], 4), round(b.inputs['Roughness'].default_value, 3)]
    return out

def build_details():
    for rec in _BC: rec['build']()
    return flush_details()

def finish(cams, marks=None, world_rgb=(0.02, 0.025, 0.04), exposure=-0.4, drop=()):
    """preview render (cams[CAMNAME]) with ink lines, or in export mode write <OUT>.fbx + <OUT>.json and quit"""
    unclip(ref=sum((Vector(c[0]) for c in cams.values()), Vector()) / max(1, len(cams))); build_details()
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
        json.dump({'lights': lights, 'marks': marks or {}, 'mats': flat_colors()}, open(os.path.splitext(OUT)[0] + '.json', 'w'), indent=1)
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
