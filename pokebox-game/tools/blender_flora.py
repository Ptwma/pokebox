# Pokebox toon flora kit (toon_flora.glb) — Blender text 'flora_lib'\n
import bpy, bmesh, math, random
from mathutils import Vector, Matrix, noise
P = {
 'leafA': (0.38,0.70,0.30), 'leafB': (0.25,0.56,0.27), 'leafC': (0.55,0.80,0.33), 'leafD': (0.20,0.46,0.25),
 'birchL': (0.62,0.84,0.38), 'pineA': (0.15,0.44,0.33), 'pineB': (0.21,0.54,0.39), 'snow': (0.95,0.97,1.0),
 'palmL': (0.36,0.68,0.27), 'cactus': (0.38,0.64,0.36), 'cactusD': (0.27,0.50,0.30), 'fern': (0.30,0.62,0.30),
 'reed': (0.56,0.62,0.30), 'lily': (0.30,0.60,0.30), 'stem': (0.30,0.56,0.25), 'moss': (0.40,0.60,0.30),
 'fl_y': (1.0,0.85,0.25), 'fl_w': (0.98,0.97,0.94), 'fl_p': (0.92,0.48,0.72), 'fl_b': (0.45,0.62,0.98), 'fl_r': (0.95,0.32,0.30), 'fl_c': (1.0,0.72,0.45),
 'berry': (0.86,0.15,0.25),
 'trunk': (0.47,0.32,0.20), 'trunkD': (0.36,0.24,0.16), 'birch': (0.93,0.91,0.86), 'birchD': (0.25,0.22,0.22), 'palmT': (0.72,0.55,0.34),
 'rock': (0.62,0.64,0.70), 'rockD': (0.48,0.50,0.57), 'rockS': (0.80,0.65,0.48), 'rockSD': (0.66,0.50,0.38), 'rockV': (0.30,0.30,0.36),
 'mush': (0.90,0.24,0.22), 'mushW': (0.98,0.95,0.88), 'reedH': (0.45,0.30,0.18), 'dead': (0.50,0.42,0.36), 'deadD': (0.38,0.31,0.27), 'ice': (0.78,0.90,0.99),
}
KEYS = list(P.keys()); PN = 8
LEAF = {'leafA','leafB','leafC','leafD','birchL','pineA','pineB','palmL','fern','reed','lily','stem','moss','fl_y','fl_w','fl_p','fl_b','fl_r','fl_c','berry','snow'}
PARTS = []
def pal_img():
    img = bpy.data.images.get('fl_palette.png')
    if img: return img
    img = bpy.data.images.new('fl_palette.png', PN*4, PN*4, alpha=False); px = [0.0] * (PN*4*PN*4*4)
    for i, k in enumerate(KEYS):
        cx, cy = i % PN, i // PN; c = P[k]
        for yy in range(cy*4, cy*4+4):
            for xx in range(cx*4, cx*4+4):
                j = (yy*PN*4 + xx)*4; px[j:j+4] = [c[0], c[1], c[2], 1.0]
    img.pixels[:] = px; img.update(); img.pack(); return img
def pmat(name):
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = pal_img(); t.interpolation = 'Closest'
    nt.links.new(t.outputs['Color'], b.inputs['Base Color']); b.inputs['Roughness'].default_value = .85; return m
def _o(bm, key, smooth=True):
    me = bpy.data.meshes.new('p'); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new('p', me); bpy.context.scene.collection.objects.link(o); o['k'] = key
    for p in me.polygons: p.use_smooth = smooth
    PARTS.append(o); return o
def blob(key, r, x, y, z, sx=1, sy=1, sz=1, sub=2, jit=.18, seed=0, smooth=True):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=r)
    for v in bm.verts:
        n = noise.noise(v.co * (2.2 / r) + Vector((seed * 3.1, seed * 1.7, 0)))
        v.co *= 1 + n * jit; v.co = Vector((v.co.x * sx, v.co.y * sy, v.co.z * sz)) + Vector((x, y, z))
    return _o(bm, key, smooth)
def tube(key, pts, r0, r1, seg=7, smooth=True):
    bm = bmesh.new(); rings = []
    for i, p in enumerate(pts):
        p = Vector(p); t = i / (len(pts) - 1); r = r0 + (r1 - r0) * t
        d = (Vector(pts[min(i + 1, len(pts) - 1)]) - Vector(pts[max(i - 1, 0)])).normalized()
        a = d.orthogonal().normalized(); b = d.cross(a)
        rings.append([bm.verts.new(p + (a * math.cos(k / seg * 6.283) + b * math.sin(k / seg * 6.283)) * r) for k in range(seg)])
    for i in range(len(rings) - 1):
        for k in range(seg): bm.faces.new((rings[i][k], rings[i][(k + 1) % seg], rings[i + 1][(k + 1) % seg], rings[i + 1][k]))
    bm.faces.new(rings[-1][::-1]); return _o(bm, key, smooth)
def cone(key, r, h, x, y, z, seg=10, r2=0.0, smooth=False, jit=0, seed=0):
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r2, depth=h)
    R = random.Random(seed)
    for v in bm.verts:
        if jit and v.co.z < h / 2 - .01: v.co.x *= 1 + (R.random() - .5) * jit; v.co.y *= 1 + (R.random() - .5) * jit
        v.co += Vector((x, y, z + h / 2))
    return _o(bm, key, smooth)
def finish(name):
    global PARTS
    for o in bpy.context.selected_objects: o.select_set(False)
    for o in PARTS:
        me = o.data; k = o['k']; i = KEYS.index(k); u = ((i % PN) + .5) / PN; v = ((i // PN) + .5) / PN
        if not me.uv_layers: me.uv_layers.new(name='UVMap')
        for l in me.uv_layers.active.data: l.uv = (u, v)
        me.materials.clear(); me.materials.append(pmat('FL_Leaves' if k in LEAF else 'FL_Wood'))
        o.select_set(True)
    bpy.context.view_layer.objects.active = PARTS[0]; bpy.ops.object.join()
    o = bpy.context.active_object; o.name = name; o.data.name = name; PARTS = []; return o

# ------------------------------------------------------------------ trees
def tree_big(name, seed=1, h=4.6, leaf=('leafA', 'leafB', 'leafC')):
    R = random.Random(seed)
    tube('trunk', [(0, 0, -.2), (0, 0, h * .35), (R.uniform(-.2, .2), R.uniform(-.2, .2), h * .62)], .34, .2)
    for k in range(3):   # branches
        a = k / 3 * 6.283 + R.random(); tube('trunk', [(0, 0, h * .45), (math.cos(a) * 1.0, math.sin(a) * 1.0, h * .68)], .14, .07, seg=6)
    blob(leaf[1], 1.55, 0, 0, h * .78, 1.15, 1.15, .85, 2, .2, seed)
    for k in range(5):
        a = k / 5 * 6.283 + R.random() * .6; rr = R.uniform(.95, 1.25)
        blob(leaf[k % 3 if k % 3 != 1 else 0], R.uniform(.85, 1.1), math.cos(a) * rr, math.sin(a) * rr, h * .7 + R.uniform(-.1, .5), 1, 1, .8, 2, .22, seed + k + 1)
    blob(leaf[2], .9, R.uniform(-.2, .2), R.uniform(-.2, .2), h * 1.02, 1.1, 1.1, .75, 2, .2, seed + 9)
    for k in range(4): tube('trunkD', [(0, 0, .05), (math.cos(k * 1.57 + .4) * .55, math.sin(k * 1.57 + .4) * .55, -.12)], .14, .05, seg=5)   # roots
    return finish(name)
def tree_birch(name, seed=2):
    R = random.Random(seed); h = 5.2
    tube('birch', [(0, 0, -.2), (.1, 0, h * .5), (-.05, .1, h * .9)], .17, .1)
    for k in range(5): blob('birchD', .06, R.uniform(-.14, .14), -.15, R.uniform(.5, h * .8), 1.3, .4, .5, 1, 0, smooth=False)
    for k in range(4):
        a = k / 4 * 6.283 + R.random(); blob('birchL', R.uniform(.7, .95), math.cos(a) * .6, math.sin(a) * .6, h * .72 + R.uniform(0, .9), .9, .9, 1.1, 2, .22, seed + k)
    blob('birchL', .8, 0, 0, h * 1.05, .9, .9, 1.2, 2, .2, seed + 7)
    return finish(name)
def pine(name, seed=3, snow=False, h=6.0):
    R = random.Random(seed)
    tube('trunkD', [(0, 0, -.2), (0, 0, h * .4)], .22, .14)
    tiers = 4
    for t in range(tiers):
        z = h * .18 + t * h * .19; r = 1.6 * (1 - t / (tiers + .6)); ch = h * .34
        cone('pineA' if t % 2 else 'pineB', r, ch, 0, 0, z, 9, 0, True, .25, seed + t)
        if snow: cone('snow', r * .78, ch * .5, 0, 0, z + ch * .52, 9, 0, True, .2, seed + t)
    return finish(name)
def palm(name, seed=4):
    R = random.Random(seed); h = 5.5; lean = R.uniform(.6, 1.0)
    pts = [(lean * (i / 6) ** 2, 0, h * i / 6) for i in range(7)]
    tube('palmT', pts, .2, .13, seg=7)
    tx, ty, tz = pts[-1]
    for k in range(7):
        a = k / 7 * 6.283 + R.random() * .3
        fr = [(tx + math.cos(a) * 1.6 * t, ty + math.sin(a) * 1.6 * t, tz + .2 + math.sin(t * 2.4) * .6 - t * t * .9) for t in [i / 5 for i in range(6)]]
        bm = bmesh.new(); prev = None
        for i, p in enumerate(fr):
            p = Vector(p); w = .38 * math.sin(math.pi * min(.95, i / 5 + .1)); side = Vector((-math.sin(a), math.cos(a), 0)) * w
            cur = (bm.verts.new(p - side), bm.verts.new(p + side))
            if prev: bm.faces.new((prev[0], prev[1], cur[1], cur[0]))
            prev = cur
        _o(bm, 'palmL', True)
    blob('palmT', .25, tx, ty, tz - .1, 1, 1, .8, 1, .1)
    return finish(name)
def dead_tree(name, seed=5):
    R = random.Random(seed); h = 3.6
    tube('dead', [(0, 0, -.2), (.2, 0, h * .5), (-.1, .2, h)], .22, .06)
    for k in range(4):
        a = R.random() * 6.283; z = R.uniform(h * .4, h * .8)
        tube('deadD', [(0, 0, z), (math.cos(a) * .9, math.sin(a) * .9, z + .7), (math.cos(a) * 1.3, math.sin(a) * 1.3, z + .6)], .08, .02, seg=5)
    return finish(name)

# ------------------------------------------------------------------ bushes, plants, flowers
def bush(name, seed=6, leaf=('leafA', 'leafB', 'leafC'), berries=False, flowers=None):
    R = random.Random(seed)
    for k in range(5):
        a = k / 5 * 6.283 + R.random(); rr = R.uniform(.25, .5)
        blob(leaf[k % 3], R.uniform(.42, .6), math.cos(a) * rr, math.sin(a) * rr, .35 + R.uniform(0, .25), 1, 1, .85, 2, .25, seed + k)
    blob(leaf[0], .55, 0, 0, .6, 1, 1, .9, 2, .2, seed + 8)
    if berries or flowers:
        for k in range(14):
            a = R.random() * 6.283; e = R.uniform(.1, 1.2)
            v = Vector((math.cos(a) * math.cos(e), math.sin(a) * math.cos(e), math.sin(e))) * .78 + Vector((0, 0, .45))
            blob('berry' if berries else flowers, .065 if berries else .09, v.x, v.y, v.z, 1, 1, 1 if berries else .5, 1, 0, smooth=True)
    return finish(name)
def disc(key, r, x, y, z, seg=6, tilt=0.0):
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r * .7, depth=.02)
    for v in bm.verts: v.co += Vector((x, y, z))
    return _o(bm, key, False)
def flowers(name, key, seed=7, n=7):
    R = random.Random(seed)
    for k in range(n):
        a = R.random() * 6.283; rr = R.uniform(0, .45); x, y = math.cos(a) * rr, math.sin(a) * rr; hh = R.uniform(.22, .42)
        tube('stem', [(x, y, 0), (x, y, hh)], .012, .01, seg=3)
        disc(key, .085, x, y, hh, 6); disc('fl_y' if key != 'fl_y' else 'fl_c', .032, x, y, hh + .015, 5)
    for k in range(3):
        a = R.random() * 6.283; blob('leafA', .12, math.cos(a) * .2, math.sin(a) * .2, .04, 1.4, .6, .3, 1, .1)
    return finish(name)
def fern(name, seed=8):
    R = random.Random(seed)
    for k in range(7):
        a = k / 7 * 6.283 + R.random() * .3; L = R.uniform(.6, .85)
        bm = bmesh.new(); prev = None
        for i in range(6):
            t = i / 5; p = Vector((math.cos(a) * L * t, math.sin(a) * L * t, .55 * math.sin(t * 2.2) * (1 - t * .3)))
            w = .13 * math.sin(math.pi * min(.97, t + .08)); side = Vector((-math.sin(a), math.cos(a), 0)) * w
            cur = (bm.verts.new(p - side), bm.verts.new(p + side))
            if prev: bm.faces.new((prev[0], prev[1], cur[1], cur[0]))
            prev = cur
        _o(bm, 'fern', True)
    return finish(name)
def reeds(name, seed=9):
    R = random.Random(seed)
    for k in range(9):
        x, y = R.uniform(-.35, .35), R.uniform(-.35, .35); h = R.uniform(.9, 1.5)
        tube('reed', [(x, y, 0), (x + R.uniform(-.1, .1), y + R.uniform(-.1, .1), h)], .02, .008, seg=4)
        if k % 3 == 0: tube('reedH', [(x, y, h * .72), (x, y, h * .9)], .035, .035, seg=6)
    return finish(name)
def tallgrass(name, seed=10, key='leafC'):
    R = random.Random(seed)
    for k in range(14):
        a = R.random() * 6.283; x, y = math.cos(a) * R.uniform(0, .3), math.sin(a) * R.uniform(0, .3); h = R.uniform(.5, .85)
        bm = bmesh.new(); lean = Vector((math.cos(a), math.sin(a), 0)) * R.uniform(.1, .3); side = Vector((-math.sin(a), math.cos(a), 0)) * .04
        v0, v1 = bm.verts.new(Vector((x, y, 0)) - side), bm.verts.new(Vector((x, y, 0)) + side)
        v2, v3 = bm.verts.new(Vector((x, y, h * .5)) + lean * .4 - side * .7), bm.verts.new(Vector((x, y, h * .5)) + lean * .4 + side * .7)
        v4 = bm.verts.new(Vector((x, y, h)) + lean)
        bm.faces.new((v0, v1, v3, v2)); bm.faces.new((v2, v3, v4)); _o(bm, key if k % 3 else 'leafA', True)
    return finish(name)
def cactus(name, seed=11, arms=2):
    R = random.Random(seed); h = R.uniform(1.6, 2.4)
    tube('cactus', [(0, 0, -.1), (0, 0, h)], .24, .2, seg=10); blob('cactus', .2, 0, 0, h, 1, 1, .7, 1, 0)
    for k in range(arms):
        s = 1 if k == 0 else -1; z = h * R.uniform(.35, .55)
        tube('cactusD', [(0, 0, z), (s * .45, 0, z + .05), (s * .5, 0, z + .6)], .13, .12, seg=8); blob('cactusD', .12, s * .5, 0, z + .6, 1, 1, .7, 1, 0)
    blob('fl_p', .08, 0, 0, h + .17, 1, 1, .5, 1, 0)
    return finish(name)
def mushrooms(name, seed=12):
    R = random.Random(seed)
    for k in range(4):
        x, y = R.uniform(-.3, .3), R.uniform(-.3, .3); h = R.uniform(.15, .35); s = R.uniform(.7, 1.2)
        tube('mushW', [(x, y, 0), (x, y, h)], .04 * s, .035 * s, seg=6); blob('mush', .12 * s, x, y, h, 1, 1, .55, 2, .05)
        for d in range(3): blob('mushW', .02 * s, x + R.uniform(-.06, .06), y + R.uniform(-.06, .06), h + .055 * s, 1, 1, .5, 1, 0)
    return finish(name)
def lily(name, seed=13):
    R = random.Random(seed)
    for k in range(3):
        x, y = R.uniform(-.5, .5), R.uniform(-.5, .5); blob('lily', .3, x, y, 0, 1, 1, .08, 2, .05)
    blob('fl_p', .07, 0, 0, .06, 1, 1, .6, 1, 0); return finish(name)
def rock(name, seed=14, key=('rock', 'rockD'), s=1.0):
    R = random.Random(seed)
    blob(key[0], .8 * s, 0, 0, .25 * s, 1.3, 1.0, .75, 2, .3, seed, smooth=False)
    blob(key[1], .5 * s, .6 * s, .3 * s, .1 * s, 1, 1, .7, 1, .25, seed + 2, smooth=False)
    if R.random() < .6: blob('moss' if key[0] == 'rock' else key[1], .45 * s, -.1 * s, -.05 * s, .62 * s, 1.2, .9, .3, 2, .2, seed + 3)
    return finish(name)
def stump(name, seed=15):
    tube('trunk', [(0, 0, -.1), (0, 0, .45)], .38, .33, seg=10); blob('trunkD', .3, 0, 0, .45, 1, 1, .08, 1, 0)
    blob('moss', .2, .2, 0, .5, 1, 1, .3, 1, .1); return finish(name)
def log(name, seed=16):
    tube('trunk', [(-1.0, 0, .25), (1.0, 0, .28)], .25, .22, seg=9); blob('moss', .3, .2, 0, .45, 1.6, .8, .3, 2, .1)
    for s in (-1, 1): blob('trunkD', .2, s * 1.0, 0, .26, .2, 1, 1, 1, 0)
    return finish(name)

def tree_lod(name, leaf='leafA', h=4.6, birch=False):
    tube('birch' if birch else 'trunk', [(0, 0, -.2), (0, 0, h * .6)], .3 if not birch else .16, .18 if not birch else .1, seg=5)
    blob(leaf, 1.9 if not birch else 1.2, 0, 0, h * .82, 1.1, 1.1, .85 if not birch else 1.3, 1, .15, 3)
    return finish(name)
def pine_lod(name, snow=False, h=6.0):
    tube('trunkD', [(0, 0, -.2), (0, 0, h * .3)], .2, .14, seg=4)
    cone('pineB', 1.6, h * .85, 0, 0, h * .15, 6, 0, False)
    if snow: cone('snow', .9, h * .35, 0, 0, h * .62, 6, 0, False)
    return finish(name)
def bush_lod(name, leaf='leafA'):
    blob(leaf, .75, 0, 0, .45, 1.1, 1.1, .8, 1, .15, 2); return finish(name)

def build_all():
    out = [tree_big('FL_Tree_A', 1), tree_big('FL_Tree_B', 2, 5.2, ('leafB', 'leafD', 'leafA')), tree_big('FL_Tree_C', 3, 4.0, ('leafC', 'leafA', 'birchL')),
           tree_birch('FL_Birch', 2), pine('FL_Pine_A', 3), pine('FL_Pine_B', 4, h=7.5), pine('FL_Pine_Snow', 5, True), palm('FL_Palm', 4), dead_tree('FL_Dead', 5),
           bush('FL_Bush_A', 6), bush('FL_Bush_B', 7, ('leafB', 'leafD', 'leafA')), bush('FL_Bush_Berry', 8, berries=True), bush('FL_Bush_Flower', 9, flowers='fl_p'),
           flowers('FL_Flowers_Y', 'fl_y', 1), flowers('FL_Flowers_W', 'fl_w', 2), flowers('FL_Flowers_P', 'fl_p', 3), flowers('FL_Flowers_B', 'fl_b', 4),
           fern('FL_Fern'), reeds('FL_Reeds'), tallgrass('FL_TallGrass'), tallgrass('FL_TallGrass_Dry', 11, 'reed'), cactus('FL_Cactus', 11), cactus('FL_Cactus_B', 12, 1),
           mushrooms('FL_Mushrooms'), lily('FL_Lily'), rock('FL_Rock_A', 14), rock('FL_Rock_B', 15, s=1.6), rock('FL_Rock_Sand', 16, ('rockS', 'rockSD')), rock('FL_Rock_Dark', 17, ('rockV', 'rockD')),
           stump('FL_Stump'), log('FL_Log'),
           tree_lod('FL_Tree_A_LOD'), tree_lod('FL_Tree_B_LOD', 'leafB', 5.2), tree_lod('FL_Tree_C_LOD', 'leafC', 4.0), tree_lod('FL_Birch_LOD', 'birchL', 5.2, True),
           pine_lod('FL_Pine_A_LOD'), pine_lod('FL_Pine_B_LOD', h=7.5), pine_lod('FL_Pine_Snow_LOD', True), bush_lod('FL_Bush_A_LOD'), bush_lod('FL_Bush_B_LOD', 'leafB'),
           bush_lod('FL_Bush_Berry_LOD'), bush_lod('FL_Bush_Flower_LOD')]
    return out
