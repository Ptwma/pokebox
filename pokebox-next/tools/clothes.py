# Pokebox Next — real 3D clothes for the Quaternius Universal Base Characters (runs inside Blender 5.x).
# The base bodies are bare; painted textures (outfits.py) alone read as "superhero bodysuits". This builds garment
# meshes per role that are skinned to the SAME skeleton (bone names), so in Unreal they follow the body through
# SetLeaderPoseComponent:
#   * shells  — copies of the body surface for a region (shirt, sleeves, trousers, boots, gloves, bib) pushed out
#               along the normals; they inherit the body's skin weights, so they bend exactly like it.
#   * tubes   — skirts, coat tails and aprons hanging from the waist, weighted pelvis -> thighs.
#   * props   — caps, hats, scarf, glasses, backpack, hood — rigid on one bone.
# Colours go into a vertex-colour attribute (linear); Unreal uses one two-sided material that reads it.
# Output: <SRC>/clothes/SK_Cloth_<role>.gltf (+ .bin). Usage (Blender):  exec(open(r'...\clothes.py').read())
import bpy, bmesh, math, os
from mathutils import Vector

SRC = os.environ.get('PBX_OUT', r"E:\GAME-APP-DEV\POKEMON\PokeboxNext_src")
BODY_DIR = os.path.join(SRC, 'kits', 'q_chars', 'Universal Base Characters[Standard]', 'Base Characters', 'Godot - UE')
OUT = os.path.join(SRC, 'clothes'); os.makedirs(OUT, exist_ok=True)
BODY = {'male': ('Superhero_Male_FullBody.gltf', 'SuperHero_Male'), 'female': ('Superhero_Female_FullBody.gltf', 'Superhero_Female')}

def lin(c):  # sRGB -> linear
    return tuple(((x + .055) / 1.055) ** 2.4 if x > .04045 else x / 12.92 for x in c)

# ------------------------------------------------------------------ role specs (colours are sRGB 0..1)
# Every role differs in silhouette (hat / coat / skirt / bag) AND palette. z values are fractions of body height.
ROLES = {
    'player_m': dict(body='male', top=dict(col=(.80, .13, .10), sleeves='short'), under=dict(col=(.12, .12, .14), sleeves='long'),
                     legs=dict(col=(.14, .18, .34), kind='long'), shoes=dict(col=(.95, .95, .95), z=.07, sole=(.1, .1, .1)),
                     belt=(.18, .12, .08), cap=dict(col=(.85, .14, .12), front=(.97, .97, .97)), backpack=(.95, .68, .16), wrist=(.12, .12, .14)),
    'player_f': dict(body='female', top=dict(col=(.97, .97, .97), sleeves='none'), legs=dict(col=(.85, .2, .32), kind='skirt', z=.36, flare=.55),
                     shoes=dict(col=(.85, .2, .32), z=.30, sole=(.95, .95, .95)), hat=dict(kind='bucket', col=(.97, .97, .97), band=(.85, .2, .32)),
                     backpack=(.2, .55, .85), wrist=(.2, .55, .85)),
    'mom': dict(body='female', top=dict(col=(.62, .5, .78), sleeves='long'), legs=dict(col=(.86, .78, .6), kind='skirt', z=.18, flare=.35),
                apron=dict(col=(.97, .95, .9), z=.30, trim=(.85, .45, .45)), shoes=dict(col=(.35, .2, .12), z=.06)),
    'vale': dict(body='female', top=dict(col=(.30, .32, .40), sleeves='long'), legs=dict(col=(.25, .26, .3), kind='long'),
                 coat=dict(col=(.96, .96, .95), z=.30, flare=.25), shoes=dict(col=(.28, .16, .1), z=.06), glasses=(.08, .08, .1)),
    'aide': dict(body='male', top=dict(col=(.55, .72, .9), sleeves='short'), legs=dict(col=(.75, .66, .45), kind='long'),
                 coat=dict(col=(.93, .95, .97), z=.47, flare=.12, sleeves='short'), shoes=dict(col=(.25, .15, .08), z=.06), glasses=(.55, .3, .1),
                 cap=None, tie=(.2, .3, .65)),
    'rho': dict(body='male', top=dict(col=(.15, .40, .80), sleeves='long', loose=.022), legs=dict(col=(.12, .12, .14), kind='shorts'),
                shoes=dict(col=(.97, .97, .97), z=.08, sole=(.9, .75, .2)), hood=(.15, .40, .80), wrist=(.9, .75, .2), socks=(.95, .95, .95)),
    'fisher': dict(body='male', top=dict(col=(.25, .3, .45), sleeves='long'), legs=dict(col=(.2, .35, .22), kind='long'),
                   coat=dict(col=(.97, .80, .12), z=.42, flare=.18, closed=True), shoes=dict(col=(.12, .25, .14), z=.27),
                   hat=dict(kind='bucket', col=(.97, .80, .12), band=(.97, .80, .12))),
    'gardener': dict(body='female', top=dict(col=(.95, .93, .88), sleeves='short'), legs=dict(col=(.30, .52, .28), kind='long'),
                     bib=(.30, .52, .28), shoes=dict(col=(.4, .25, .12), z=.2), gloves=(.85, .7, .2),
                     hat=dict(kind='straw', col=(.92, .80, .5), band=(.75, .25, .2))),
    'merchant': dict(body='female', top=dict(col=(.92, .50, .15), sleeves='short'), legs=dict(col=(.45, .2, .3), kind='skirt', z=.10, flare=.45),
                     apron=dict(col=(.95, .90, .75), z=.25, trim=(.92, .5, .15)), shoes=dict(col=(.45, .3, .15), z=.05),
                     scarf=(.85, .2, .25)),
    'kid': dict(body='male', top=dict(col=(.95, .82, .20), sleeves='short', stripes=(.85, .2, .15)), legs=dict(col=(.25, .4, .7), kind='shorts'),
                shoes=dict(col=(.2, .7, .3), z=.08, sole=(.97, .97, .97)), cap=dict(col=(.25, .4, .7), front=(.25, .4, .7), backwards=True), socks=(.97, .97, .97)),
    'conductor': dict(body='female', top=dict(col=(.14, .18, .34), sleeves='long'), legs=dict(col=(.14, .18, .34), kind='skirt', z=.22, flare=.25),
                      coat=dict(col=(.14, .18, .34), z=.47, flare=.1, closed=True), shoes=dict(col=(.06, .06, .06), z=.09), tie=(.8, .15, .12),
                      hat=dict(kind='peaked', col=(.14, .18, .34), band=(.8, .15, .12)), wrist=(.85, .65, .2)),
    'guard': dict(body='male', top=dict(col=(.20, .30, .22), sleeves='long'), legs=dict(col=(.18, .26, .2), kind='long'),
                  coat=dict(col=(.20, .30, .22), z=.47, flare=.08, closed=True), belt=(.08, .07, .06), shoes=dict(col=(.06, .06, .06), z=.24),
                  hat=dict(kind='peaked', col=(.18, .26, .2), band=(.8, .65, .2)), gloves=(.95, .95, .95), shoulder=(.8, .65, .2)),
}

# ------------------------------------------------------------------ body analysis
GROUPS = {'torso': ('pelvis', 'spine_01', 'spine_02', 'spine_03', 'clavicle_l', 'clavicle_r'), 'neck': ('neck_01',), 'head': ('Head',),
          'uarm': ('upperarm_l', 'upperarm_r'), 'larm': ('lowerarm_l', 'lowerarm_r'), 'thigh': ('thigh_l', 'thigh_r'),
          'calf': ('calf_l', 'calf_r'), 'foot': ('foot_l', 'foot_r', 'ball_l', 'ball_r')}

class Body:
    def __init__(self, kind):
        self.sc = bpy.data.scenes.get('PBX_Cloth') or bpy.data.scenes.new('PBX_Cloth')
        bpy.context.window.scene = self.sc
        for o in list(self.sc.objects): bpy.data.objects.remove(o, do_unlink=True)
        f, bname = BODY[kind]
        bpy.ops.import_scene.gltf(filepath=os.path.join(BODY_DIR, f))
        self.arm = [o for o in self.sc.objects if o.type == 'ARMATURE'][0]
        self.body = [o for o in self.sc.objects if o.type == 'MESH' and o.name.lower().startswith('superhero')][0]
        self.extra = [o for o in self.sc.objects if o.type == 'MESH' and o != self.body]
        me = self.body.data; mw = self.body.matrix_world
        self.P = [mw @ v.co for v in me.vertices]
        self.H = max(p.z for p in self.P)
        names = {g.index: g.name for g in self.body.vertex_groups}
        cat = {}
        for k, bs in GROUPS.items():
            for b in bs: cat[b] = k
        self.hand = set(n for n in names.values() if n not in cat)  # fingers, hand_*, root...
        self.W = []
        for v in me.vertices:
            w = {}
            for g in v.groups:
                n = names[g.group]; k = cat.get(n, 'hand' if ('hand' in n or any(s in n for s in ('index', 'middle', 'ring', 'pinky', 'thumb'))) else 'other')
                w[k] = w.get(k, 0) + g.weight
            self.W.append(w)
        self.bone = {b.name: self.arm.matrix_world @ b.head_local for b in self.arm.data.bones}
        self.wrist = abs(self.bone['hand_l'].x) - .02
        self.shoulder = abs(self.bone['upperarm_l'].x)
        self.elbow = abs(self.bone['lowerarm_l'].x)
        hv = [p for p, w in zip(self.P, self.W) if w.get('head', 0) > .6]
        self.head_top = max(p.z for p in hv); self.head_c = Vector((0, sum(p.y for p in hv) / len(hv), 0))
        top = [p for p in hv if p.z > self.head_top - .11]
        self.head_rx = max(abs(p.x) for p in top); ys = [p.y for p in top]
        self.head_c = Vector((0, (max(ys) + min(ys)) / 2, 0)); self.head_ry = (max(ys) - min(ys)) / 2
        self.head_r = self.head_rx
        ey = [self.extra_eye(o) for o in self.extra if 'eye' in o.name.lower() and 'brow' not in o.name.lower()]
        self.eye = ey[0] if ey else Vector((.033, self.head_c.y - .09, self.head_top - .12))
        self.parts = []

    def extra_eye(self, o):
        vs = [o.matrix_world @ v.co for v in o.data.vertices]
        vl = [v for v in vs if v.x > 0]
        return Vector((sum(v.x for v in vl) / len(vl), min(v.y for v in vl), sum(v.z for v in vl) / len(vl)))

    def z(self, f): return f * self.H

    # torso cross-section at height z: (centre y, half width x, half depth y)
    def section(self, z, band=.03):
        pts = [p for p, w in zip(self.P, self.W) if abs(p.z - z) < band and abs(p.x) < self.shoulder and w.get('uarm', 0) + w.get('larm', 0) + w.get('hand', 0) < .2]
        if not pts: return 0.0, .16, .11
        ys = [p.y for p in pts]; xs = [abs(p.x) for p in pts]
        return (max(ys) + min(ys)) / 2, max(xs), (max(ys) - min(ys)) / 2

# ------------------------------------------------------------------ mesh builders
def _color(ob, col):
    me = ob.data
    a = me.color_attributes.get('Col') or me.color_attributes.new('Col', 'FLOAT_COLOR', 'CORNER')
    c = lin(col) + (1.0,)
    if callable(col):
        pass
    for d in a.data: d.color = c
    me.color_attributes.active_color = a

def _finish(B, ob, col):
    ob.parent = B.arm
    mod = ob.modifiers.new('Armature', 'ARMATURE'); mod.object = B.arm
    ob.data.materials.clear(); ob.data.materials.append(bpy.data.materials.get('M_PBX_Cloth') or bpy.data.materials.new('M_PBX_Cloth'))
    if col is not None: _color(ob, col)
    B.parts.append(ob); return ob

def shell(B, name, keep, off, col, colfn=None):
    """copy of the body surface where keep(pos, weights) holds for all of a face's vertices, offset along the normal"""
    src = B.body; me = src.data.copy(); me.name = name
    for a in list(me.color_attributes): me.color_attributes.remove(a)
    ob = bpy.data.objects.new(name, me); B.sc.collection.objects.link(ob); ob.matrix_world = src.matrix_world.copy()
    for g in src.vertex_groups: ob.vertex_groups.new(name=g.name)
    # vertex groups are per object -> copy weights
    for v in me.vertices:
        for g in src.data.vertices[v.index].groups: ob.vertex_groups[g.group].add([v.index], g.weight, 'REPLACE')
    k = [keep(B.P[i], B.W[i]) for i in range(len(B.P))]
    bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
    bad = [f for f in bm.faces if not all(k[v.index] for v in f.verts)]
    bmesh.ops.delete(bm, geom=bad, context='FACES_ONLY')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.normal_update()
    for v in bm.verts: v.co += v.normal * off
    bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    _finish(B, ob, None)
    a = me.color_attributes.new('Col', 'FLOAT_COLOR', 'CORNER'); me.color_attributes.active_color = a
    mw = ob.matrix_world
    for poly in me.polygons:
        for li in poly.loop_indices:
            p = mw @ me.vertices[me.loops[li].vertex_index].co
            c = colfn(p) if colfn else col
            a.data[li].color = lin(c) + (1.0,)
    return ob

def _weights_obj(ob, groups):
    """groups: list (per vertex) of {bone: w}"""
    for i, gw in enumerate(groups):
        for b, w in gw.items():
            if w <= 0: continue
            vg = ob.vertex_groups.get(b) or ob.vertex_groups.new(name=b)
            vg.add([i], w, 'REPLACE')

def tube(B, name, z_top, z_bot, col, flare=.3, open_front=False, front_only=False, extra=0.0, rows=7, segs=28, trim=None):
    """skirt / coat tail / apron hanging from z_top down to z_bot (metres), elliptical, flaring out"""
    cy, rx, ry = B.section(z_top)
    rx += .018 + extra; ry += .018 + extra
    bm = bmesh.new(); grid = []; W = []
    gap = math.radians(9)
    angs = []
    for s in range(segs + 1):
        a = -math.pi / 2 + gap + (2 * math.pi - 2 * gap) * s / segs if open_front else 2 * math.pi * s / segs
        if front_only: a = math.radians(-170) + math.radians(160) * s / segs
        angs.append(a)
    for r in range(rows + 1):
        t = r / rows; z = z_top + (z_bot - z_top) * t; f = 1 + flare * t ** 1.3
        row = []
        for a in angs:
            x = math.cos(a) * rx * f; y = cy + math.sin(a) * ry * f * (1.08 if math.sin(a) < 0 else 1.0)
            row.append(bm.verts.new((x, y, z)))
            side = 'thigh_l' if x > 0 else 'thigh_r'
            wl = min(.75, t * .9) * min(1, abs(math.cos(a)) * 1.6 + .25)
            W.append({'pelvis': 1 - wl, side: wl})
        grid.append(row)
    closed = not open_front and not front_only
    for r in range(rows):
        for s in range(segs):
            bm.faces.new((grid[r][s], grid[r][s + 1], grid[r + 1][s + 1], grid[r + 1][s]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    if closed: pass
    ob = bpy.data.objects.new(name, me); B.sc.collection.objects.link(ob)
    for p in me.polygons: p.use_smooth = True
    _weights_obj(ob, W)
    _finish(B, ob, None)
    a = me.color_attributes.new('Col', 'FLOAT_COLOR', 'CORNER'); me.color_attributes.active_color = a
    for poly in me.polygons:
        for li in poly.loop_indices:
            z = me.vertices[me.loops[li].vertex_index].co.z
            c = trim if (trim and z < z_bot + .035) else col
            a.data[li].color = lin(c) + (1.0,)
    return ob

def rigid(B, name, build, bone, col, colfn=None):
    """mesh made by build(bm), weighted 100 % to one bone"""
    bm = bmesh.new(); build(bm)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); B.sc.collection.objects.link(ob)
    for p in me.polygons: p.use_smooth = True
    vg = ob.vertex_groups.new(name=bone); vg.add(list(range(len(me.vertices))), 1.0, 'REPLACE')
    _finish(B, ob, None)
    a = me.color_attributes.new('Col', 'FLOAT_COLOR', 'CORNER'); me.color_attributes.active_color = a
    for poly in me.polygons:
        c = colfn(poly) if colfn else col
        for li in poly.loop_indices: a.data[li].color = lin(c) + (1.0,)
    return ob

def _sphere(bm, c, r, sz=1.0, top_only=False, u=20, v=12, cut=0.0):
    g = bmesh.ops.create_uvsphere(bm, u_segments=u, v_segments=v, radius=1.0)
    vs = g['verts']
    if top_only:
        bmesh.ops.delete(bm, geom=[x for x in vs if x.co.z < cut - 1e-4], context='VERTS')
        vs = [x for x in bm.verts if x.is_valid]
    for x in vs:
        if x.is_valid: x.co = Vector((c[0] + x.co.x * r[0], c[1] + x.co.y * r[1], c[2] + x.co.z * r[2] * sz))

def _disc(bm, c, r_in, r_out, z0, z1=None, segs=28, sx=1.0, sy=1.0, front=None):
    """flat ring (brim) between r_in and r_out; z1 = height at the outer edge (droop)"""
    z1 = z0 if z1 is None else z1
    a0, a1 = (0, 2 * math.pi) if front is None else front
    full = front is None
    inner, outer = [], []
    n = segs if full else segs + 1
    for s in range(n):
        a = a0 + (a1 - a0) * s / segs
        inner.append(bm.verts.new((c[0] + math.cos(a) * r_in * sx, c[1] + math.sin(a) * r_in * sy, z0)))
        outer.append(bm.verts.new((c[0] + math.cos(a) * r_out * sx, c[1] + math.sin(a) * r_out * sy, z1)))
    m = segs if full else segs
    for s in range(m):
        j = (s + 1) % n
        bm.faces.new((inner[s], inner[j], outer[j], outer[s]))
    return inner, outer

def _cyl(bm, c, rx, ry, z0, z1, segs=24, r1x=None, r1y=None, cap=True):
    r1x = rx if r1x is None else r1x; r1y = ry if r1y is None else r1y
    lo = [bm.verts.new((c[0] + math.cos(2 * math.pi * s / segs) * rx, c[1] + math.sin(2 * math.pi * s / segs) * ry, z0)) for s in range(segs)]
    hi = [bm.verts.new((c[0] + math.cos(2 * math.pi * s / segs) * r1x, c[1] + math.sin(2 * math.pi * s / segs) * r1y, z1)) for s in range(segs)]
    for s in range(segs):
        j = (s + 1) % segs; bm.faces.new((lo[s], lo[j], hi[j], hi[s]))
    if cap: bm.faces.new(list(reversed(hi))) if False else bm.faces.new(hi)
    return lo, hi

def _box(bm, c, sx, sy, sz):
    g = bmesh.ops.create_cube(bm, size=1.0)
    for v in g['verts']: v.co = Vector((c[0] + v.co.x * sx, c[1] + v.co.y * sy, c[2] + v.co.z * sz))
    return g

# ------------------------------------------------------------------ garments
def is_arm(B, p, w): return w.get('uarm', 0) + w.get('larm', 0) + w.get('hand', 0) > .5 or abs(p.x) > B.shoulder + .07
def skin_free(w): return w.get('head', 0) < .25 and w.get('neck', 0) < .55

def g_top(B, name, spec, off):
    sl = spec.get('sleeves', 'long'); zlo = B.z(.50)
    lim = {'long': B.wrist - .015, 'short': B.shoulder + (B.elbow - B.shoulder) * .62, 'none': B.shoulder + .05}[sl]
    def keep(p, w):
        if w.get('hand', 0) > .3 or not skin_free(w) or p.z < zlo: return False
        if p.z > B.z(.835): return False
        if is_arm(B, p, w): return abs(p.x) < lim
        return True
    st = spec.get('stripes')
    colfn = (lambda p: st if (int(p.z / .055) % 2 == 0 and abs(p.x) < B.shoulder + .02) else spec['col']) if st else None
    return shell(B, name, keep, off, spec['col'], colfn)

def g_legs(B, spec, off=.010):
    kind = spec['kind']; zb = {'long': B.z(.05), 'shorts': B.z(.36), 'skirt': B.z(.47)}[kind]
    def keep(p, w):
        if p.z > B.z(.545) or p.z < zb: return False
        if is_arm(B, p, w): return False
        return w.get('thigh', 0) + w.get('calf', 0) + w.get('torso', 0) + w.get('foot', 0) > .5
    shell(B, 'legs', keep, off, spec['col'])
    if kind == 'skirt': tube(B, 'skirt', B.z(.535), B.z(spec.get('z', .3)), spec['col'], flare=spec.get('flare', .4), extra=.004)

def g_shoes(B, spec):
    zt = B.z(max(spec['z'], .085)); sole = spec.get('sole', spec['col'])
    def keep(p, w): return p.z < zt and (w.get('foot', 0) + w.get('calf', 0)) > .5
    shell(B, 'shoes', keep, .009, spec['col'], lambda p: sole if p.z < .025 else spec['col'])

def g_socks(B, col):
    def keep(p, w): return B.z(.07) < p.z < B.z(.17) and w.get('calf', 0) + w.get('foot', 0) > .5
    shell(B, 'socks', keep, .006, col)

def g_belt(B, col, off=.022):
    z0 = B.z(.535); z1 = B.z(.56)
    shell(B, 'belt', lambda p, w: z0 < p.z < z1 and not is_arm(B, p, w), off, col)
    cy, rx, ry = B.section((z0 + z1) / 2)
    rigid(B, 'buckle', lambda bm: _box(bm, (0, cy - ry - off - .012, (z0 + z1) / 2), .06, .014, .04), 'pelvis', (.85, .7, .25))

def g_gloves(B, col):
    shell(B, 'gloves', lambda p, w: w.get('hand', 0) > .4 or (abs(p.x) > B.wrist - .03 and w.get('larm', 0) > .2), .005, col)

def g_wrist(B, col):
    shell(B, 'wristband', lambda p, w: B.wrist - .06 < abs(p.x) < B.wrist - .01 and w.get('larm', 0) > .3, .012, col)

def g_coat(B, spec):
    sl = spec.get('sleeves', 'long')
    g_top(B, 'coat_top', dict(col=spec['col'], sleeves=sl), .024)
    if spec.get('z', .5) < .5:
        tube(B, 'coat_tail', B.z(.56), B.z(spec['z']), spec['col'], flare=spec.get('flare', .2), open_front=not spec.get('closed'), extra=.012)

def g_apron(B, spec):
    tube(B, 'apron', B.z(.555), B.z(spec['z']), spec['col'], flare=.18, front_only=True, extra=.03, trim=spec.get('trim'))
    def bib(p, w):
        cy, rx, ry = B.section(p.z)
        return B.z(.555) < p.z < B.z(.74) and p.y < cy - ry * .25 and abs(p.x) < .13 and not is_arm(B, p, w)
    shell(B, 'apron_bib', bib, .03, spec['col'])

def g_bib(B, col):   # dungarees: bib + straps over the shirt
    def bib(p, w):
        if is_arm(B, p, w) or not skin_free(w): return False
        cy, rx, ry = B.section(min(p.z, B.z(.74)))
        front = p.y < cy - ry * .2
        if B.z(.53) < p.z < B.z(.70) and front and abs(p.x) < .12: return True
        return B.z(.53) < p.z < B.z(.815) and .055 < abs(p.x) < .095
    shell(B, 'bib', bib, .02, col)

def g_hood(B, col):
    z = B.bone['neck_01'].z; cy = B.bone['neck_01'].y
    rigid(B, 'hood', lambda bm: _sphere(bm, (0, cy + .1, z - .02), (.17, .08, .09)), 'spine_03', col)

def g_tie(B, col):
    cy, rx, ry = B.section(B.z(.74))
    def build(bm):
        y = cy - ry - .028
        bm.verts.ensure_lookup_table()
        vs = [bm.verts.new(v) for v in ((-.022, y, B.z(.80)), (.022, y, B.z(.80)), (.032, y - .004, B.z(.62)), (0, y - .006, B.z(.595)), (-.032, y - .004, B.z(.62)))]
        bm.faces.new(vs)
    rigid(B, 'tie', build, 'spine_03', col)

def g_backpack(B, col):
    z = B.z(.72); cy, rx, ry = B.section(z)
    def build(bm):
        _box(bm, (0, cy + ry + .1, z), .30, .15, .36)
        _box(bm, (0, cy + ry + .19, z - .06), .22, .05, .18)   # front pocket
    rigid(B, 'backpack', build, 'spine_03', col, lambda poly: tuple(c * .78 for c in col) if poly.center.y > cy + ry + .17 else col)
    for s in (-1, 1):   # straps over the shoulders
        shell(B, f'strap{s}', lambda p, w, s=s: B.z(.62) < p.z < B.z(.83) and .07 < p.x * s < .105 and not is_arm(B, p, w), .028, tuple(c * .6 for c in col))

def g_shoulder(B, col):
    for s in (-1, 1):
        x = s * (B.shoulder - .01); z = B.bone['upperarm_l'].z + .07
        rigid(B, f'epaulette{s}', lambda bm, x=x, z=z: _box(bm, (x, 0.02, z), .12, .11, .025), 'clavicle_l' if s > 0 else 'clavicle_r', col)

def g_glasses(B, col):
    e = B.eye
    def build(bm):
        for s in (-1, 1):
            c = (s * abs(e.x), e.y - .014, e.z)
            ring = [bm.verts.new((c[0] + math.cos(a) * .026, c[1], c[2] + math.sin(a) * .02)) for a in [2 * math.pi * i / 16 for i in range(16)]]
            inner = [bm.verts.new((c[0] + math.cos(a) * .021, c[1], c[2] + math.sin(a) * .016)) for a in [2 * math.pi * i / 16 for i in range(16)]]
            for i in range(16): bm.faces.new((ring[i], ring[(i + 1) % 16], inner[(i + 1) % 16], inner[i]))
        _box(bm, (0, e.y - .014, e.z + .006), abs(e.x) * 2 - .05, .006, .006)
    rigid(B, 'glasses', build, 'Head', col)

def hat_base(B):
    """hats sit over the hair: centre / radius of the skull top, padded"""
    return B.head_c.y, B.head_top, B.head_rx * 1.3

def ky(B): return B.head_ry / B.head_rx

def g_cap(B, spec):
    cy, top, r = hat_base(B); zc = top - .075; back = spec.get('backwards')
    def build(bm):
        _sphere(bm, (0, cy, zc), (r, r * ky(B), .1), top_only=True)
        sgn = 1 if back else -1
        _disc(bm, (0, cy, zc + .005), r * .95, r * 1.75, zc + .005, zc - .005, segs=14, sy=ky(B),
              front=(math.radians(-150), math.radians(-30)) if not back else (math.radians(30), math.radians(150)))
    rigid(B, 'cap', build, 'Head', spec['col'], lambda poly: spec.get('front', spec['col']) if (poly.center.z > zc + .07 and poly.center.y < cy) else spec['col'])

def g_hat(B, spec):
    cy, top, r = hat_base(B); k = spec['kind']; band = spec.get('band', spec['col'])
    if k == 'bucket':
        zc = top - .085
        def build(bm):
            _cyl(bm, (0, cy), r, r * ky(B), zc, zc + .1, r1x=r * .86, r1y=r * ky(B) * .9)
            _disc(bm, (0, cy), r, r * 1.55, zc, zc - .045, segs=28, sy=ky(B))
        rigid(B, 'hat', build, 'Head', spec['col'], lambda poly: band if abs(poly.center.z - zc - .012) < .012 else spec['col'])
    elif k == 'straw':
        zc = top - .07
        def build(bm):
            _sphere(bm, (0, cy, zc), (r * .95, r * ky(B), .11), top_only=True)
            _disc(bm, (0, cy), r * .93, r * 2.4, zc, zc - .04, segs=32, sy=ky(B))
        rigid(B, 'hat', build, 'Head', spec['col'], lambda poly: band if (abs(poly.center.z - zc - .015) < .016 and math.hypot(poly.center.x, poly.center.y - cy) < r * 1.0) else spec['col'])
    elif k == 'peaked':
        zc = top - .065
        def build(bm):
            _cyl(bm, (0, cy), r * .98, r * ky(B), zc, zc + .085, r1x=r * 1.12, r1y=r * ky(B) * 1.14)
            _disc(bm, (0, cy, zc), r * .95, r * 1.55, zc + .01, zc - .01, segs=12, sy=ky(B), front=(math.radians(-145), math.radians(-35)))
        rigid(B, 'hat', build, 'Head', spec['col'], lambda poly: band if poly.center.z < zc + .025 and poly.center.y < cy else ((.05, .05, .05) if poly.center.z < zc + .015 else spec['col']))

def g_scarf(B, col):
    cy, top, r = hat_base(B); zc = top - .1
    def build(bm):
        _sphere(bm, (0, cy + .01, zc), (r * .98, r * ky(B), .13), top_only=True)
        _sphere(bm, (0, cy + r * ky(B) * .95, zc - .02), (.04, .03, .04))   # knot at the back
    rigid(B, 'scarf', build, 'Head', col)

# ------------------------------------------------------------------ build + export one role
def build_role(role):
    S = ROLES[role]; B = Body(S['body'])
    if 'under' in S: g_top(B, 'under', S['under'], .006)
    g_top(B, 'top', S['top'], S['top'].get('loose', .012))
    g_legs(B, S['legs'])
    if 'socks' in S: g_socks(B, S['socks'])
    g_shoes(B, S['shoes'])
    if 'bib' in S: g_bib(B, S['bib'])
    if S.get('belt'): g_belt(B, S['belt'])
    if S.get('coat'): g_coat(B, S['coat'])
    if S.get('apron'): g_apron(B, S['apron'])
    if S.get('tie'): g_tie(B, S['tie'])
    if S.get('gloves'): g_gloves(B, S['gloves'])
    if S.get('wrist'): g_wrist(B, S['wrist'])
    if S.get('hood'): g_hood(B, S['hood'])
    if S.get('backpack'): g_backpack(B, S['backpack'])
    if S.get('shoulder'): g_shoulder(B, S['shoulder'])
    if S.get('glasses'): g_glasses(B, S['glasses'])
    if S.get('cap'): g_cap(B, S['cap'])
    if S.get('hat'): g_hat(B, S['hat'])
    if S.get('scarf'): g_scarf(B, S['scarf'])
    # join all garments into one skinned mesh (explicit context: the window's scene switch is not visible to ops yet)
    vl = B.sc.view_layers[0]
    with bpy.context.temp_override(window=bpy.context.window, scene=B.sc, view_layer=vl):
        for o in B.sc.objects: o.select_set(False, view_layer=vl)
        for o in B.parts: o.select_set(True, view_layer=vl)
        vl.objects.active = B.parts[0]
        bpy.ops.object.join()
    ob = vl.objects.active; ob.name = 'SK_Cloth_' + role; ob.data.name = ob.name
    ca = ob.data.color_attributes
    for a in [a for a in ca if a.name != 'Col']: ca.remove(a)
    i = [a.name for a in ca].index('Col'); ca.active_color_index = i; ca.render_color_index = i
    for o in B.extra + [B.body]: bpy.data.objects.remove(o, do_unlink=True)
    path = os.path.join(OUT, f'SK_Cloth_{role}.gltf')
    with bpy.context.temp_override(window=bpy.context.window, scene=B.sc, view_layer=vl):
        for o in B.sc.objects: o.select_set(False, view_layer=vl)
        ob.select_set(True, view_layer=vl); B.arm.select_set(True, view_layer=vl); vl.objects.active = B.arm
        bpy.ops.export_scene.gltf(filepath=path, export_format='GLTF_SEPARATE', use_selection=True, use_active_scene=True, export_animations=False,
                                  export_skins=True, export_vertex_color='ACTIVE', export_all_vertex_colors=False, export_materials='EXPORT', export_morph=False)
    print('clothes', role, len(ob.data.vertices), 'verts ->', path)
    return path

def run(roles=None):
    prev = bpy.context.window.scene
    try:
        for r in (roles or ROLES): build_role(r)
    finally:
        bpy.context.window.scene = prev

if __name__ == '__main__' or True:
    pass
