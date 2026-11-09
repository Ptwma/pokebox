# Sigil & Spark — period clothes for the MetaHuman cast, made from each character's own body (owner 2026-11-08: "you make
# the clothes"; free only). A garment is a shell of the body surface in the regions it covers (picked by the skin weights
# of the MetaHuman skeleton), pushed out by its thickness, smoothed so no anatomy shows through, solidified, with the body's
# own skin weights (so it moves exactly with the body: leader pose in Unreal). Robes and coats get a flared skirt below the
# hips. Fabric: Poly Haven CC0 scans (tint per character) — materials are made in Unreal (pbx_clothes.py).
#   blender -b --factory-startup --python clothes_mh.py -- <body.fbx> <out.fbx> <character id>
import bpy, bmesh, sys, os, math, json
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:]
BODY, OUT, CID = argv[0], argv[1], argv[2]

# region = bones whose weight puts a vertex in the garment; cut = extra limits (metres, body space: Z up, front -Y)
REG = {
    'shirt_long':  {'bones': ('spine_01', 'spine_02', 'spine_03', 'spine_04', 'spine_05', 'clavicle_l', 'clavicle_r', 'upperarm_l', 'upperarm_r', 'lowerarm_l', 'lowerarm_r', 'pelvis', 'neck_01'),
                    'zmin_rel': 0.47, 'neck_max_rel': 0.83, 'off': 0.010},
    'shirt_short': {'bones': ('spine_01', 'spine_02', 'spine_03', 'spine_04', 'spine_05', 'clavicle_l', 'clavicle_r', 'upperarm_l', 'upperarm_r', 'pelvis', 'neck_01'),
                    'zmin_rel': 0.47, 'neck_max_rel': 0.83, 'off': 0.010},
    'vest':        {'bones': ('spine_02', 'spine_03', 'spine_04', 'spine_05', 'clavicle_l', 'clavicle_r', 'spine_01', 'pelvis'),
                    'zmin_rel': 0.50, 'neck_max_rel': 0.80, 'off': 0.022},
    'coat':        {'bones': ('spine_01', 'spine_02', 'spine_03', 'spine_04', 'spine_05', 'clavicle_l', 'clavicle_r', 'upperarm_l', 'upperarm_r', 'lowerarm_l', 'lowerarm_r', 'pelvis', 'neck_01'),
                    'zmin_rel': 0.47, 'neck_max_rel': 0.84, 'off': 0.030, 'skirt': 0.30},
    'robe':        {'bones': ('spine_01', 'spine_02', 'spine_03', 'spine_04', 'spine_05', 'clavicle_l', 'clavicle_r', 'upperarm_l', 'upperarm_r', 'lowerarm_l', 'lowerarm_r', 'pelvis', 'neck_01'),
                    'zmin_rel': 0.47, 'neck_max_rel': 0.845, 'off': 0.024, 'skirt': 0.06},
    'trousers':    {'bones': ('pelvis', 'thigh_l', 'thigh_r', 'calf_l', 'calf_r', 'spine_01'),
                    'zmin_rel': 0.075, 'zmax_rel': 0.585, 'off': 0.012},
    'skirt':       {'bones': ('pelvis', 'spine_01'), 'zmin_rel': 0.46, 'zmax_rel': 0.585, 'off': 0.014, 'skirt': 0.05},
    'boots':       {'bones': ('calf_l', 'calf_r', 'foot_l', 'foot_r', 'ball_l', 'ball_r'), 'zmax_rel': 0.30, 'off': 0.014},
    'shoes':       {'bones': ('foot_l', 'foot_r', 'ball_l', 'ball_r', 'calf_l', 'calf_r'), 'zmax_rel': 0.075, 'off': 0.010},
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

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=BODY, use_anim=False, ignore_leaf_bones=True, automatic_bone_orientation=False)
arm = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
body = max((o for o in bpy.context.scene.objects if o.type == 'MESH'), key=lambda o: len(o.data.vertices))
dg = bpy.context.evaluated_depsgraph_get()
zs = [(body.matrix_world @ v.co).z for v in body.data.vertices]
Z0, Z1 = min(zs), max(zs); HGT = Z1 - Z0
print('BODY', body.name, len(body.data.vertices), 'verts, height %.3f m' % HGT)
gname = {g.index: g.name for g in body.vertex_groups}
SCALE = body.matrix_world.to_scale()[0] or 1.0

def region_verts(spec):
    keep = set(spec['bones'])
    out = []
    for v in body.data.vertices:
        w = sum(g.weight for g in v.groups if gname.get(g.group) in keep)
        tot = sum(g.weight for g in v.groups) or 1.0
        if w / tot < 0.5: continue
        z = ((body.matrix_world @ v.co).z - Z0) / HGT
        if 'zmin_rel' in spec and z < spec['zmin_rel']: continue
        if 'zmax_rel' in spec and z > spec['zmax_rel']: continue
        if 'neck_max_rel' in spec and z > spec['neck_max_rel']: continue
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
    small = [x for i in islands if len(i) < max(40, big * 0.04) for x in i]
    if small: bmesh.ops.delete(bm, geom=small, context='VERTS')
    # smooth the anatomy away, then push out along the normals (layer = order over other garments)
    for _ in range(6): bmesh.ops.smooth_vert(bm, verts=bm.verts, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bm.normal_update()
    off = (spec['off'] + 0.006 * layer) / SCALE      # metres → the mesh's own units (an Unreal FBX imports in cm × 0.01)
    for v in bm.verts: v.co += v.normal * off
    bm.to_mesh(g.data); bm.free()
    # skirt for robes / coats / skirts: a flared tube from the lowest ring of the shell down to the hem
    if spec.get('skirt') is not None:
        add_skirt(g, spec['skirt'])
    so = g.modifiers.new('thick', 'SOLIDIFY'); so.thickness = 0.004 / SCALE; so.offset = 1.0
    sub = g.modifiers.new('sub', 'SUBSURF'); sub.levels = 1; sub.render_levels = 1
    # the armature modifier must stay LAST so the export keeps the skinning
    am = next((m for m in g.modifiers if m.type == 'ARMATURE'), None)
    if am:
        bpy.context.view_layer.objects.active = g
        while g.modifiers[-1] != am: bpy.ops.object.modifier_move_down(modifier=am.name)
    g['kind'] = kind
    mat = bpy.data.materials.new(f'M_{CID}_{kind}'); mat['fabric'] = fabric; mat['tint'] = list(tint)
    g.data.materials.clear(); g.data.materials.append(mat)
    for p in g.data.polygons: p.material_index = 0
    return g

def add_skirt(g, hem_rel):
    """flare from the shell's hip ring down to hem_rel (fraction of body height); weights: pelvis above, thighs by side.
    Built in world space (the FBX import may rotate the rig), then brought into the mesh's own space."""
    me = g.data; M = g.matrix_world; Mi = M.inverted()
    wv = [M @ v.co for v in me.vertices]
    zmin = min(p.z for p in wv)
    ring = [p for p in wv if p.z <= zmin + 0.02 * HGT]
    if len(ring) < 8: return
    c = sum(ring, Vector()) / len(ring)
    rx = max(abs(p.x - c.x) for p in ring) * 1.08; ry = max(abs(p.y - c.y) for p in ring) * 1.12
    bm = bmesh.new(); bm.from_mesh(me)
    defl = bm.verts.layers.deform.verify()
    gi = {gr.name: gr.index for gr in g.vertex_groups}
    N, R = 40, 10
    z_top = zmin; z_hem = Z0 + hem_rel * HGT
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
    for j in range(R):
        for i in range(N):
            bm.faces.new((rows[j][i], rows[j][(i + 1) % N], rows[j + 1][(i + 1) % N], rows[j + 1][i]))
    bm.normal_update(); bm.to_mesh(me); bm.free()

out_objs = []
for layer, (kind, fabric, tint) in enumerate(OUTFITS.get(CID, OUTFITS['player_m'])):
    out_objs.append(make(kind, fabric, tint, layer))
    print('GARMENT', kind, fabric, len(out_objs[-1].data.vertices), 'verts')
body.hide_set(True); body.hide_render = True
for o in bpy.context.scene.objects: o.select_set(False)
arm.select_set(True)
for o in out_objs: o.select_set(True)
bpy.ops.export_scene.fbx(filepath=OUT, use_selection=True, object_types={'ARMATURE', 'MESH'}, add_leaf_bones=False, use_armature_deform_only=False,
                         apply_unit_scale=True, apply_scale_options='FBX_SCALE_ALL', bake_anim=False, mesh_smooth_type='FACE', use_mesh_modifiers=True,
                         primary_bone_axis='Y', secondary_bone_axis='X')
json.dump({'garments': [{'name': o.name, 'kind': o['kind'], 'fabric': o.data.materials[0]['fabric'], 'tint': list(o.data.materials[0]['tint'])} for o in out_objs]},
          open(os.path.splitext(OUT)[0] + '.json', 'w'), indent=1)
print('CLOTHES DONE', OUT, len(out_objs))
