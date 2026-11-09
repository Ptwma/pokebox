# Sigil & Spark — period clothes for the MetaHuman cast, made from each character's own body (owner 2026-11-08: "you make
# the clothes"; free only). A garment is a shell of the body surface in the regions it covers (picked by the skin weights
# of the MetaHuman skeleton), pushed out by its thickness, smoothed so no anatomy shows through, solidified, with the body's
# own skin weights (so it moves exactly with the body: leader pose in Unreal). Robes and coats get a flared skirt below the
# hips. Fabric: Poly Haven CC0 scans (tint per character) — materials are made in Unreal (pbx_clothes.py).
#   blender -b --factory-startup --python clothes_mh.py -- <body.fbx> <out.fbx> <character id> [<outfit.fbx>]
import bpy, bmesh, sys, os, math, json
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:]
BODY, OUT, CID = argv[0], argv[1], argv[2]
OUTFIT = argv[3] if len(argv) > 3 else None

# region = bone-name PREFIXES whose weight puts a vertex in the garment (MetaHuman spreads skin over many twist /
# corrective bones: upperarm_twistCor_01_l, spine_04_latissimus_l ...), lo/hi = height limits from skeleton landmarks
# (metres above/below them, world space): ankle, knee, hip (pelvis), waist (spine_02), neck (neck_01), wrist, elbow.
REG = {
    'shirt_long':  {'bones': ('spine', 'clavicle', 'upperarm', 'lowerarm', 'pelvis', 'neck'), 'lo': ('hip', -0.10), 'hi': ('neck', 0.02), 'arm': 'wrist', 'off': 0.010},
    'shirt_short': {'bones': ('spine', 'clavicle', 'upperarm', 'pelvis', 'neck'), 'lo': ('hip', -0.10), 'hi': ('neck', 0.02), 'arm': 'midarm', 'off': 0.010},
    'vest':        {'bones': ('spine', 'clavicle', 'pelvis'), 'lo': ('hip', -0.06), 'hi': ('neck', -0.03), 'arm': 'none', 'off': 0.022},
    'coat':        {'bones': ('spine', 'clavicle', 'upperarm', 'lowerarm', 'pelvis', 'neck'), 'lo': ('hip', -0.12), 'hi': ('neck', 0.04), 'arm': 'wrist', 'off': 0.032, 'skirt': ('knee', -0.05)},
    'robe':        {'bones': ('spine', 'clavicle', 'upperarm', 'lowerarm', 'pelvis', 'neck'), 'lo': ('hip', -0.12), 'hi': ('neck', 0.04), 'arm': 'wrist', 'off': 0.026, 'skirt': ('ankle', 0.02)},
    'trousers':    {'bones': ('pelvis', 'thigh', 'calf', 'spine_01'), 'lo': ('ankle', 0.05), 'hi': ('hip', 0.07), 'off': 0.012},
    'skirt':       {'bones': ('pelvis', 'spine_01', 'thigh'), 'lo': ('hip', -0.12), 'hi': ('hip', 0.07), 'off': 0.014, 'skirt': ('ankle', 0.06)},
    'boots':       {'bones': ('calf', 'foot', 'ball', 'bigtoe', 'indextoe', 'middletoe', 'ringtoe', 'littletoe'), 'lo': ('ground', -1.0), 'hi': ('knee', -0.10), 'off': 0.014},
    'shoes':       {'bones': ('foot', 'ball', 'calf', 'bigtoe', 'indextoe', 'middletoe', 'ringtoe', 'littletoe'), 'lo': ('ground', -1.0), 'hi': ('ankle', 0.04), 'off': 0.010},
}
# character -> garments, inner to outer: (kind, fabric, rgb tint)
OUTFITS = {
    'player_m': [('trousers', 'ribbed_corduroy', (.32, .26, .20)), ('shirt_long', 'rough_linen', (.80, .76, .66)), ('vest', 'brown_leather', (.55, .40, .28)), ('boots', 'fabric_leather_01', (.30, .22, .16))],
    'rho':      [('trousers', 'poly_wool_herringbone', (.20, .22, .26)), ('shirt_long', 'cotton_jersey', (.18, .22, .38)), ('coat', 'caban', (.16, .17, .22)), ('boots', 'fabric_leather_01', (.18, .14, .11))],
    'fisher':   [('trousers', 'hessian_230', (.42, .38, .30)), ('shirt_long', 'rough_linen', (.72, .70, .64)), ('vest', 'wool_boucle', (.50, .36, .18)), ('boots', 'fabric_leather_01', (.22, .17, .12))],
    'vale':     [('robe', 'velour_velvet', (.34, .34, .40)), ('shoes', 'brown_leather', (.20, .16, .12))],
    'aide':     [('trousers', 'poly_wool_herringbone', (.24, .22, .20)), ('robe', 'rough_linen', (.30, .38, .52)), ('shoes', 'brown_leather', (.22, .16, .12))],
    'merchant': [('skirt', 'hessian_230', (.55, .30, .16)), ('shirt_long', 'rough_linen', (.85, .78, .62)), ('vest', 'fabric_leather_01', (.45, .22, .12)), ('shoes', 'brown_leather', (.25, .18, .12))],
    'gardener': [('skirt', 'rough_linen', (.30, .40, .24)), ('shirt_long', 'cotton_jersey', (.80, .74, .60)), ('shoes', 'brown_leather', (.24, .18, .12))],
    'guard':    [('trousers', 'poly_wool_herringbone', (.22, .22, .24)), ('shirt_long', 'rough_linen', (.55, .52, .46)), ('coat', 'caban', (.22, .24, .28)), ('boots', 'fabric_leather_01', (.14, .11, .09))],
    'kid':      [('trousers', 'ribbed_corduroy', (.30, .32, .40)), ('shirt_short', 'cotton_jersey', (.25, .55, .80)), ('shoes', 'brown_leather', (.26, .18, .12))],
}

# detail pass (owner 2026-11-09 19:19: "the clothes want a little more detail"): a raised TRIM band in a second material
# along every hem / cuff / neckline, a front placket with buttons on shirts, vests and coats, a waistband (belt) on
# trousers and skirts, dark soles on footwear, and soft fabric folds (low-frequency displacement) everywhere.
# kind -> (trim fabric or None = same fabric, trim tint or a multiplier on the garment tint, band m, buttons, button radius m)
TRIM = {
    'shirt_long':  (None, 0.72, 0.018, 6, 0.0055), 'shirt_short': (None, 0.72, 0.018, 5, 0.0055),
    'vest':        ('fabric_leather_01', (.10, .07, .05), 0.016, 5, 0.007),
    'coat':        ('fabric_leather_01', (.09, .07, .06), 0.026, 5, 0.011),
    'robe':        ('velour_velvet', (.55, .42, .16), 0.03, 0, 0),
    'trousers':    ('brown_leather', (.14, .09, .06), 0.016, 0, 0), 'skirt': ('brown_leather', (.16, .10, .07), 0.016, 0, 0),
    'boots':       ('brown_leather', (.06, .045, .035), 0.012, 0, 0), 'shoes': ('brown_leather', (.06, .045, .035), 0.010, 0, 0),
}

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=BODY, use_anim=False, ignore_leaf_bones=True, automatic_bone_orientation=False)
arm = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
body = max((o for o in bpy.context.scene.objects if o.type == 'MESH'), key=lambda o: len(o.data.vertices))
if OUTFIT and os.path.exists(OUTFIT):   # the torso / hips live only in the default garment: join it into the tailoring surface
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.fbx(filepath=OUTFIT, use_anim=False, ignore_leaf_bones=True, automatic_bone_orientation=False)
    new = [o for o in bpy.context.scene.objects if o not in before]
    new_arms = [o for o in new if o.type == 'ARMATURE']; new_meshes = [o for o in new if o.type == 'MESH']
    # where the body skin and the default garment overlap (the rim around the garment's cut-out), keep only the garment:
    # two layers there were pushed out together and came through each other as ragged frills at the waist / hems
    from mathutils.kdtree import KDTree
    # the garment's hems are folded inside (inner faces facing the skin): pushed out along their normals they turned into
    # ragged frills → drop every garment face that faces against the skin under it
    _bw = [(body.matrix_world @ v.co, (body.matrix_world.to_3x3() @ v.normal).normalized()) for v in body.data.vertices]
    _bk = KDTree(len(_bw))
    for i, (p_, _) in enumerate(_bw): _bk.insert(p_, i)
    _bk.balance()
    for o in new_meshes:
        bmo = bmesh.new(); bmo.from_mesh(o.data); bmo.normal_update(); R3o = o.matrix_world.to_3x3()
        inner = []
        for f in bmo.faces:
            c_ = o.matrix_world @ f.calc_center_median(); _, i_, _ = _bk.find(c_)
            if (R3o @ f.normal).normalized().dot(_bw[i_][1]) < -0.6: inner.append(f)
        bmesh.ops.delete(bmo, geom=inner, context='FACES'); bmo.to_mesh(o.data); bmo.free()
        print('INNER faces dropped', len(inner))
    _ow = [o.matrix_world @ v.co for o in new_meshes for v in o.data.vertices]
    if _ow:
        _kd = KDTree(len(_ow))
        for i, p_ in enumerate(_ow): _kd.insert(p_, i)
        _kd.balance()
        # snap (not delete: deleting cut the sleeves / legs off as separate islands) the skin under the garment onto it,
        # so the weld below fuses the two layers into one connected surface
        Mb = body.matrix_world; Mbi = Mb.inverted(); n_ = 0
        for v in body.data.vertices:
            co, _, d = _kd.find(Mb @ v.co)
            if d < 0.022: v.co = Mbi @ co; n_ += 1
        print('OVERLAP snapped', n_, 'body verts onto the garment')
    for o in new_meshes:
        for m in o.modifiers:
            if m.type == 'ARMATURE': m.object = arm
        o.parent = arm
        for x in bpy.context.scene.objects: x.select_set(False)
        o.select_set(True); body.select_set(True); bpy.context.view_layer.objects.active = body
        bpy.ops.object.join()
    for o in new_arms: bpy.data.objects.remove(o)
    bpy.ops.object.select_all(action='DESELECT')
    bm0 = bmesh.new(); bm0.from_mesh(body.data); _s = body.matrix_world.to_scale()[0] or 1; bmesh.ops.remove_doubles(bm0, verts=bm0.verts, dist=0.004 / _s); bmesh.ops.dissolve_degenerate(bm0, edges=bm0.edges, dist=0.001 / _s); bm0.to_mesh(body.data); bm0.free()
dg = bpy.context.evaluated_depsgraph_get()
zs = [(body.matrix_world @ v.co).z for v in body.data.vertices]
Z0, Z1 = min(zs), max(zs); HGT = Z1 - Z0
print('BODY', body.name, len(body.data.vertices), 'verts, height %.3f m' % HGT)
gname = {g.index: g.name for g in body.vertex_groups}
SCALE = body.matrix_world.to_scale()[0] or 1.0

# landmarks from the MESH itself (bone rest positions do not always match the exported bind pose): the mean height of
# the vertices each bone dominates
def _dom(v):
    best = max(v.groups, key=lambda g: g.weight, default=None)
    return gname.get(best.group, '') if best else ''
_acc = {}
for v in body.data.vertices:
    d = _dom(v); z = (body.matrix_world @ v.co).z
    for key, pre in (('foot', 'foot'), ('calf', 'calf'), ('thigh', 'thigh'), ('pelvis', 'pelvis'), ('neck', 'neck'), ('spine05', 'spine_05')):
        if d.startswith(pre): _acc.setdefault(key, []).append(z)
_m = lambda k, f=lambda a: sum(a) / len(a): f(_acc[k]) if _acc.get(k) else None
LM = {'ground': Z0, 'ankle': (_m('foot', max) or Z0 + 0.09) - 0.01, 'knee': (_m('calf', max) or Z0 + 0.45),
      'hip': _m('pelvis') or Z0 + 0.85, 'neck': _m('neck', min) or _m('spine05', max) or Z1 - 0.02}
print('LANDMARKS', {k: round(v - Z0, 3) for k, v in LM.items()})
# body axes: forward = heel→toe (the ball of the foot lies in front of the ankle), the centre line from the spine
_fa, _ba, _sp = [], [], []
for v in body.data.vertices:
    d = _dom(v); p = body.matrix_world @ v.co
    if d.startswith('foot'): _fa.append(p)
    elif d.startswith('ball'): _ba.append(p)
    elif d.startswith('spine'): _sp.append(p)
_avg = lambda a: sum(a, Vector()) / len(a) if a else Vector()
FWD = (_avg(_ba) - _avg(_fa)) if _fa and _ba else Vector((0, -1, 0)); FWD.z = 0; FWD = FWD.normalized() if FWD.length > 1e-6 else Vector((0, -1, 0))
LAT = FWD.cross(Vector((0, 0, 1))).normalized(); CEN = _avg(_sp) if _sp else Vector()
print('AXES fwd', tuple(round(c, 2) for c in FWD))

def _arm_ok(v, mode):
    """sleeves by skin weight: long = upper + lower arm, short = upper arm, none = no arm at all; hands never"""
    d = _dom(v)
    if d.startswith(('hand', 'thumb', 'index', 'middle', 'ring', 'pinky')): return False
    if mode == 'none' and d.startswith(('upperarm', 'lowerarm')): return False
    if mode == 'midarm' and d.startswith('lowerarm'): return False
    return True

def region_verts(spec):
    pre = spec['bones']
    lo = LM.get(spec['lo'][0], Z0) + spec['lo'][1] - 0.04 if 'lo' in spec else -1e9   # margin: the hem is cut by a plane later
    hi = LM.get(spec['hi'][0], Z1) + spec['hi'][1] + 0.04 if 'hi' in spec else 1e9
    out = []
    for v in body.data.vertices:
        tot = sum(g.weight for g in v.groups) or 1.0
        w = sum(g.weight for g in v.groups if gname.get(g.group, '').startswith(pre))
        if w / tot < 0.5: continue
        p = body.matrix_world @ v.co
        if p.z < lo or p.z > hi: continue
        if 'arm' in spec and not _arm_ok(v, spec['arm']): continue
        out.append(v.index)
    return set(out)

def make(kind, fabric, tint, layer):
    spec = REG[kind]
    keep = region_verts(spec)
    g = body.copy(); g.data = body.data.copy(); g.name = f'SKM_{CID}_{kind}'; bpy.context.scene.collection.objects.link(g)
    for m in list(g.modifiers):
        if m.type != 'ARMATURE': g.modifiers.remove(m)
    bm = bmesh.new(); bm.from_mesh(g.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index not in keep], context='VERTS')
    # drop tiny islands (fingers, stray verts at the region edge)
    bm.verts.ensure_lookup_table()
    seen, islands = set(), []
    for v in bm.verts:
        if v in seen: continue
        stack, isl = [v], []
        while stack:
            x = stack.pop()
            if x in seen: continue
            seen.add(x); isl.append(x); stack.extend(e.other_vert(x) for e in x.link_edges)
        islands.append(isl)
    big = max(len(i) for i in islands) if islands else 0
    small = [x for i in islands if len(i) < max(60, big * 0.12) for x in i]
    if small: bmesh.ops.delete(bm, geom=small, context='VERTS')
    # close the seams where the body skin meets the default garment (two open borders a few mm apart): weld border to
    # border, so only the real hems stay open (QA: the trim band ran along those seams as ragged dark lines)
    _bd = [v for v in bm.verts if any(e.is_boundary for e in v.link_edges)]
    if _bd: bmesh.ops.remove_doubles(bm, verts=_bd, dist=0.016 / SCALE)
    # clean hems: cut the shell with horizontal planes at lo / hi (the weight-picked border was ragged)
    Mi = g.matrix_world.inverted(); nz = (Mi.to_3x3() @ Vector((0, 0, 1))).normalized()
    for key, inner in (('lo', True), ('hi', False)):
        if key not in spec or spec[key][0] == 'ground': continue
        z = LM.get(spec[key][0], Z0 if key == 'lo' else Z1) + spec[key][1]
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=Mi @ Vector((0, 0, z)), plane_no=nz, clear_inner=inner, clear_outer=not inner)
    # smooth the anatomy away, then push out along the normals (layer = order over other garments)
    for _ in range(3): bmesh.ops.smooth_vert(bm, verts=bm.verts, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    # straighten the hems / cuffs / neckline: the weight-picked border is jagged → smooth only the border loop, hard
    for _ in range(4):   # the plane-cut hems are straight already: only the cuffs / neckline need it
        edge = [v for v in bm.verts if any(e.is_boundary for e in v.link_edges)]
        bmesh.ops.smooth_vert(bm, verts=edge, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=False)
    bm.normal_update()
    off = (spec['off'] + 0.008 + 0.007 * layer) / SCALE      # metres → the mesh's own units (an Unreal FBX imports in cm × 0.01)
    for v in bm.verts: v.co += v.normal * off
    bm.to_mesh(g.data); bm.free()
    # skirt for robes / coats / skirts: a flared tube from the lowest ring of the shell down to the hem
    if spec.get('skirt') is not None:
        add_skirt(g, LM[spec['skirt'][0]] + spec['skirt'][1])
    details(g, kind, spec)
    tx = bpy.data.textures.get('PBX_Folds') or bpy.data.textures.new('PBX_Folds', 'CLOUDS')
    tx.noise_scale = 0.09; tx.noise_depth = 1
    dp = g.modifiers.new('folds', 'DISPLACE'); dp.texture = tx; dp.texture_coords = 'GLOBAL'; dp.strength = 0.006 / SCALE; dp.mid_level = 0.5
    so = g.modifiers.new('thick', 'SOLIDIFY'); so.thickness = 0.004 / SCALE; so.offset = 1.0
    sub = g.modifiers.new('sub', 'SUBSURF'); sub.levels = 1; sub.render_levels = 1
    # the armature modifier must stay LAST so the export keeps the skinning
    am = next((m for m in g.modifiers if m.type == 'ARMATURE'), None)
    if am:
        bpy.context.view_layer.objects.active = g
        while g.modifiers[-1] != am: bpy.ops.object.modifier_move_down(modifier=am.name)
    g['kind'] = kind
    mat = bpy.data.materials.new(f'M_{CID}_{kind}'); mat['fabric'] = fabric; mat['tint'] = list(tint)
    tf, tt, *_ = TRIM.get(kind, (None, 0.72, 0, 0, 0))
    trim = bpy.data.materials.new(f'M_{CID}_{kind}_trim'); trim['fabric'] = tf or fabric
    trim['tint'] = [c * tt for c in tint] if isinstance(tt, float) else list(tt)
    keep_idx = [p.material_index for p in g.data.polygons]   # details() marked the trim faces with index 1
    g.data.materials.clear(); g.data.materials.append(mat); g.data.materials.append(trim)
    for p, k in zip(g.data.polygons, keep_idx): p.material_index = 1 if k == 1 else 0
    return g

def details(g, kind, spec):
    if kind not in TRIM: return
    tf, tt, band, nbut, brad = TRIM[kind]
    me = g.data; M = g.matrix_world; Mi = M.inverted(); R3 = M.to_3x3().normalized()
    bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table(); bm.normal_update()
    defl = bm.verts.layers.deform.verify()
    for f in bm.faces: f.material_index = 0   # the body copy carries its own slot indices
    W = {v: M @ v.co for v in bm.verts}
    from mathutils.kdtree import KDTree
    z_lo_ = LM.get(spec['lo'][0], Z0) + spec['lo'][1] if 'lo' in spec else -1e9
    z_hi_ = LM.get(spec['hi'][0], Z1) + spec['hi'][1] if 'hi' in spec else 1e9
    def _hem(v):   # a REAL hem: at a cut plane, the neckline, a cuff (out along the arm) or the skirt's hem — not a seam
        p = W[v]
        if abs(p.z - z_lo_) < 0.025 or abs(p.z - z_hi_) < 0.025 or p.z > LM['neck'] - 0.06: return True
        if abs((p - CEN).dot(LAT)) > 0.30: return True                         # sleeve ends
        if spec.get('skirt') and p.z < LM['hip'] - 0.10: return True              # the skirt / coat hem
        return False
    bverts = [v for v in bm.verts if any(e.is_boundary for e in v.link_edges) and _hem(v)]
    kd = KDTree(max(1, len(bverts)))
    for i, v in enumerate(bverts): kd.insert(W[v], i)
    kd.balance()
    z_hi = LM.get(spec['hi'][0], Z1) + spec['hi'][1] if 'hi' in spec else 1e9
    band_v = set()
    for v in bm.verts:
        p = W[v]; d = kd.find(p)[2] if bverts else 1e9
        if kind in ('trousers', 'skirt') and abs(p.z - z_hi) < 0.045: band_v.add(v)        # waistband / belt
        elif kind in ('boots', 'shoes') and p.z < Z0 + 0.022: band_v.add(v)               # sole
        elif d < band: band_v.add(v)                                                      # hems, cuffs, neckline
        elif nbut and abs((p - CEN).dot(LAT)) < 0.014 and (p - CEN).dot(FWD) > 0 and p.z < z_hi - 0.03:   # front placket
            band_v.add(v)
    lift = 0.0028 / SCALE
    nrm = {v: v.normal.copy() for v in band_v}
    for v in band_v: v.co += nrm[v] * lift
    for f in bm.faces:
        if all(v in band_v for v in f.verts): f.material_index = 1
    # buttons down the placket: small discs on the surface, skinned like the cloth under them
    if nbut:
        cand = [v for v in bm.verts if abs((W[v] - CEN).dot(LAT)) < 0.01 and (W[v] - CEN).dot(FWD) > 0]
        if cand:
            zs_ = [W[v].z for v in cand]; z_lo, z_top = min(zs_) + 0.05, min(max(zs_), z_hi) - 0.07
            for k in range(nbut):
                zt = z_lo + (z_top - z_lo) * k / max(1, nbut - 1)
                v0 = min(cand, key=lambda v: abs(W[v].z - zt))
                n = (R3 @ v0.normal).normalized(); p0 = W[v0] + n * (0.0045 + 0.0028)
                ax = n.orthogonal().normalized(); ay = n.cross(ax)
                ring_b, ring_t = [], []
                for i in range(10):
                    a_ = math.tau * i / 10; o = (ax * math.cos(a_) + ay * math.sin(a_)) * brad
                    ring_b.append(bm.verts.new(Mi @ (p0 + o))); ring_t.append(bm.verts.new(Mi @ (p0 + o * 0.85 + n * brad * 0.45)))
                for vv in ring_b + ring_t:
                    for gi_, w in v0[defl].items(): vv[defl][gi_] = w
                for i in range(10):
                    j = (i + 1) % 10; bm.faces.new((ring_b[i], ring_b[j], ring_t[j], ring_t[i])).material_index = 1
                bm.faces.new(ring_t).material_index = 1
    bm.normal_update(); bm.to_mesh(me); bm.free()

def add_skirt(g, z_hem):
    """flare from the shell's hip ring down to hem_rel (fraction of body height); weights: pelvis above, thighs by side.
    Built in world space (the FBX import may rotate the rig), then brought into the mesh's own space."""
    me = g.data; M = g.matrix_world; Mi = M.inverted()
    wv = [M @ v.co for v in me.vertices]
    # the hip girth: the shell's vertices just under the pelvis line (not its lowest point, which is the crotch)
    zh = LM['hip'] - 0.06
    ring = []
    for v in body.data.vertices:
        p = body.matrix_world @ v.co
        if abs(p.z - zh) > 0.03: continue
        tot = sum(x.weight for x in v.groups) or 1.0
        if sum(x.weight for x in v.groups if gname.get(x.group, '').startswith(('pelvis', 'thigh', 'spine'))) / tot >= 0.5: ring.append(p)
    if len(ring) < 8: print('SKIRT: no hip ring'); return
    print('SKIRT ring', len(ring))
    zmin = LM["hip"] + 0.08   # starts at the waist, over the shell, so no skin or hem shows between them
    c = sum(ring, Vector()) / len(ring)
    rx = max(abs(p.x - c.x) for p in ring) * 1.10 + 0.012; ry = max(abs(p.y - c.y) for p in ring) * 1.14 + 0.012
    bm = bmesh.new(); bm.from_mesh(me)
    defl = bm.verts.layers.deform.verify()
    gi = {gr.name: gr.index for gr in g.vertex_groups}
    N, R = 40, 10
    z_top = zmin
    rows = []
    for j in range(R + 1):
        t_ = j / R; z = z_top + (z_hem - z_top) * t_; fl = 1.0 + 0.55 * t_ * t_
        row = []
        for i in range(N):
            a_ = 2 * math.pi * i / N
            v = bm.verts.new(Mi @ Vector((c.x + math.cos(a_) * rx * fl, c.y + math.sin(a_) * ry * fl, z)))
            side = 'thigh_l' if math.cos(a_) > 0 else 'thigh_r'
            wl = min(0.85, t_ * 1.1)
            for name, w in (('pelvis', 1.0 - wl), (side, wl)):
                if name in gi: v[defl][gi[name]] = w
            row.append(v)
        rows.append(row)
    uvl = bm.loops.layers.uv.active or bm.loops.layers.uv.new()
    for j in range(R):
        for i in range(N):
            f = bm.faces.new((rows[j][i], rows[j][(i + 1) % N], rows[j + 1][(i + 1) % N], rows[j + 1][i]))
            for lp, (a, b) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):   # cylindrical UVs so the fabric tiles on the skirt too
                lp[uvl].uv = (a / N * 0.6, 1.0 - b / R * 0.35)
    bm.normal_update(); bm.to_mesh(me); bm.free()

out_objs = []
for layer, (kind, fabric, tint) in enumerate(OUTFITS.get(CID, OUTFITS['player_m'])):
    out_objs.append(make(kind, fabric, tint, layer))
    print('GARMENT', kind, fabric, len(out_objs[-1].data.vertices), 'verts')
body.hide_set(True); body.hide_render = True
arm.name = 'root'   # the body FBX imports with its root JOINT as the armature OBJECT: exported under the name 'root' it becomes the root bone again (named 'Armature' Unreal dropped it, the skeleton started at pelvis and could not merge)
for o in bpy.context.scene.objects: o.select_set(False)
arm.select_set(True)
for o in out_objs: o.select_set(True)
bpy.ops.export_scene.fbx(filepath=OUT, use_selection=True, object_types={'ARMATURE', 'MESH'}, add_leaf_bones=False, use_armature_deform_only=False,
                         apply_unit_scale=True, apply_scale_options='FBX_SCALE_ALL', bake_anim=False, mesh_smooth_type='FACE', use_mesh_modifiers=True,
                         primary_bone_axis='Y', secondary_bone_axis='X')
json.dump({'garments': [{'name': o.name, 'kind': o['kind'] + sfx, 'fabric': m['fabric'], 'tint': list(m['tint'])} for o in out_objs for m, sfx in zip(o.data.materials, ('', '_trim'))]},
          open(os.path.splitext(OUT)[0] + '.json', 'w'), indent=1)
print('CLOTHES DONE', OUT, len(out_objs))

# QA preview: the body (grey) under the garments (their tints), front and side, workbench
try:
    body.hide_set(False); body.hide_render = False
    sc = bpy.context.scene; sc.render.engine = 'BLENDER_WORKBENCH'; sc.display.shading.color_type = 'MATERIAL'
    sc.render.resolution_x, sc.render.resolution_y = 700, 1000
    for o in out_objs:
        for m in o.data.materials: m.diffuse_color = (*m['tint'], 1)
    bm_ = bpy.data.materials.new('skin'); bm_.diffuse_color = (.75, .62, .55, 1); body.data.materials.clear(); body.data.materials.append(bm_)
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = HGT * 1.25 + 0.3
    mid = (Z0 + Z1) / 2
    for tag, loc, rot in (('f', (0, -4, mid), (math.radians(90), 0, 0)), ('s', (4, 0, mid), (math.radians(90), 0, math.radians(90)))):
        cam.location = loc; cam.rotation_euler = rot
        sc.render.filepath = os.path.splitext(OUT)[0] + f'_{tag}.png'; bpy.ops.render.render(write_still=True)
    print('PREVIEW written')
except Exception as ex:
    print('PREVIEW failed', ex)
