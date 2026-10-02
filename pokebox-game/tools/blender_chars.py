# Pokebox anime trainers — run inside Blender (text block 'char_lib').
# build(arm, kind, top) builds a character on a Quaternius armature; bind() + export() write chars/anime/*.glb

import bpy, bmesh, math
from mathutils import Vector, Matrix

def mat(name, col, rough=.8, emit=0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = (*col, 1)
    b.inputs['Roughness'].default_value = rough
    if emit:
        b.inputs['Emission Color'].default_value = (*col, 1); b.inputs['Emission Strength'].default_value = emit
    return m

def srgb(h):
    h = h.lstrip('#'); c = [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4 for x in c)

def skin_body(name, verts, edges, radii, root=0, subs=1):
    me = bpy.data.meshes.new(name); me.from_pydata(verts, edges, []); me.update()
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    sk = ob.modifiers.new('skin', 'SKIN'); sk.use_smooth_shade = True
    for i, r in enumerate(radii): me.skin_vertices[0].data[i].radius = r
    me.skin_vertices[0].data[root].use_root = True
    ss = ob.modifiers.new('sub', 'SUBSURF'); ss.levels = subs; ss.render_levels = subs
    apply_all(ob)
    return ob

def apply_all(ob):
    bpy.context.view_layer.objects.active = ob
    for o in bpy.context.selected_objects: o.select_set(False)
    ob.select_set(True)
    for m in list(ob.modifiers): bpy.ops.object.modifier_apply(modifier=m.name)

def smooth(ob):
    for p in ob.data.polygons: p.use_smooth = True

def ellipsoid(name, c, r, segs=24, rings=16):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=1)
    for v in bm.verts: v.co = Vector((v.co.x * r[0], v.co.y * r[1], v.co.z * r[2]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob); ob.location = c
    smooth(ob); return ob

def bake_loc(ob):
    ob.data.transform(Matrix.Translation(ob.location) @ Matrix.Rotation(ob.rotation_euler.z, 4, 'Z') @ Matrix.Rotation(ob.rotation_euler.y, 4, 'Y') @ Matrix.Rotation(ob.rotation_euler.x, 4, 'X') @ Matrix.Diagonal((*ob.scale, 1)))
    ob.location = (0, 0, 0); ob.rotation_euler = (0, 0, 0); ob.scale = (1, 1, 1)

def set_mat(ob, m):
    ob.data.materials.clear(); ob.data.materials.append(m)

def join(obs, name):
    for o in bpy.context.selected_objects: o.select_set(False)
    for o in obs: bake_loc(o); o.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]; bpy.ops.object.join(); obs[0].name = name; obs[0].data.name = name
    return obs[0]


def J(arm, n, tail=False):
    b = arm.data.bones[n]; return arm.matrix_world @ (b.tail_local if tail else b.head_local)

def build(arm, kind='m', top='tee', tag='G', cols=None):
    """anime trainer on a Quaternius armature. kind m/f; top tee|long|hoodie|jacket|vest|coat|skirt"""
    C = dict(skin='#fcdcc4', hair='#5a3a26', eye='#4a7fd0', outfit='#d8483c', pants='#2f3e5c', shoes='#f2f2f2', sole='#d8483c', inner='#f4f1ea', belt='#2a2430', skirt='#2f3e5c')
    C.update(cols or {})
    S = srgb; f = kind == 'f'
    mats = {k: mat(k, S(v), r) for k, v, r in [('Skin', C['skin'], 1), ('Hair', C['hair'], .5), ('Eye', C['eye'], .3), ('Outfit', C['outfit'], .9),
            ('Pants', C['pants'], .9), ('Shoes', C['shoes'], .7), ('Sole', C['sole'], .8), ('Inner', C['inner'], .9), ('Belt', C['belt'], .6), ('Skirt', C['skirt'], .9)]}
    mats.update({'EyeWhite': mat('EyeWhite', S('#ffffff'), .4), 'Pupil': mat('Pupil', S('#1a1420'), .3), 'EyeShine': mat('EyeShine', S('#ffffff'), .2, 2),
            'Eyebrows': mat('Eyebrows', S('#3a2618'), .8), 'Mouth': mat('Mouth', S('#a24848'), .8), 'Buckle': mat('Buckle', S('#f2c230'), .3), 'Blush': mat('Blush', S('#ff9f9f'), 1)})
    objs = []
    def keep(o, m, bone=None):
        set_mat(o, mats[m]) if isinstance(m, str) else None; o['bone'] = bone or ''; o.name = tag + '_' + o.name; objs.append(o); return o
    hip, kne, ank = J(arm, 'UpperLeg.L'), J(arm, 'LowerLeg.L'), J(arm, 'LowerLeg.L', True)
    sh, el, wr = J(arm, 'UpperArm.L'), J(arm, 'LowerArm.L'), J(arm, 'Wrist.L')
    hp, ch, nk, hd = J(arm, 'Hips'), J(arm, 'Chest'), J(arm, 'Neck'), J(arm, 'Head')
    Y = (hp.y + ch.y) / 2 + .005
    zP = hip.z - .02; zN = nk.z; zH = hd.z
    if f: R0 = [(.135, .095), (.092, .072), (.118, .092), (.112, .078), (.04, .04), (.036, .036)]
    else: R0 = [(.13, .095), (.108, .082), (.13, .09), (.125, .08), (.045, .045), (.04, .04)]
    V = [(0, Y, zP), (0, Y, zP + (zN - zP) * .3), (0, Y - (.012 if f else 0), zP + (zN - zP) * .62), (0, Y - .005, zN - .09), (0, Y, zN - .01), (0, Y, zH - .01)]
    E = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)]; R = list(R0)
    for s in (1, -1):
        b = len(V)
        V += [(s * (sh.x + .02), Y, sh.z - .008), (s * el.x, el.y, el.z), (s * (wr.x - .005), wr.y, wr.z), (s * (wr.x + .035), wr.y, wr.z + .001),
              (s * (hip.x - .02 if not f else hip.x), Y, hip.z - .07), (s * kne.x, kne.y + .01, kne.z), (s * ank.x, ank.y, ank.z + .03)]
        E += [(3, b), (b, b + 1), (b + 1, b + 2), (b + 2, b + 3), (0, b + 4), (b + 4, b + 5), (b + 5, b + 6)]
        R += [(.052, .052) if f else (.058, .058), (.04, .04) if f else (.046, .046), (.031, .03) if f else (.036, .034), (.03, .027),
              (.098, .095) if f else (.09, .09), (.055, .058) if f else (.06, .062), (.04, .042) if f else (.046, .048)]
    body = skin_body('Body', V, E, R, 0, 2)
    body.data.materials.clear()
    for k in ('Skin', 'Outfit', 'Pants', 'Inner'): body.data.materials.append(mats[k])
    belt_z = zP + .035
    sleeve = {'tee': sh.x + .12, 'vest': sh.x + .12, 'skirt': sh.x + .1}.get(top, wr.x - .02)
    for p in body.data.polygons:
        c = p.center
        if c.z > zN + .01 or abs(c.x) > sleeve: p.material_index = 0
        elif c.z > belt_z: p.material_index = 3 if top == 'vest' else 1
        else: p.material_index = 2
        if top in ('tee', 'skirt', 'vest') and f is False and False: pass
    keep(body, None)
    # hands
    for s in (1, -1):
        keep(ellipsoid('hand', (s * (wr.x + .095), wr.y - .01, wr.z), (.055 if f else .06, .024, .04), 16, 10), 'Skin', 'Wrist.' + ('L' if s > 0 else 'R'))
        t = ellipsoid('thumb', (s * (wr.x + .055), wr.y - .04, wr.z), (.028, .014, .015), 10, 6); t.rotation_euler.z = s * .6; keep(t, 'Skin', 'Wrist.' + ('L' if s > 0 else 'R'))
    # shoes
    for s in (1, -1):
        bn = 'Foot.' + ('L' if s > 0 else 'R')
        o = ellipsoid('shoe', (s * ank.x, ank.y - .05, .058), (.052 if f else .058, .11, .052), 20, 12)
        for v in o.data.vertices:
            if v.co.z < -.02: v.co.z = -.02 - (v.co.z + .02) * .25
        keep(o, 'Shoes', bn); keep(ellipsoid('sole', (s * ank.x, ank.y - .05, .026), (.056 if f else .062, .115, .019), 20, 8), 'Sole', bn)
    # belt (not with skirt/coat)
    if top not in ('skirt',):
        pts = [tuple(v.co) for v in body.data.vertices if abs(v.co.z - belt_z) < .03]
        rx = max(abs(p[0]) for p in pts) + .008; ry = max(abs(p[1] - Y) for p in pts) + .008
        o = ring('belt', rx, ry, Y, belt_z - .02, .04, .008); keep(o, 'Belt', 'Hips')
        keep(ellipsoid('buckle', (0, Y - ry - .008, belt_z), (.026, .008, .019), 12, 8), 'Buckle', 'Hips')
    # ---- clothes shells
    def shell(name, zlo, zhi, grow, m, open_front=0, flare=0, bone=None):
        bm = bmesh.new(); bm.from_mesh(body.data)
        kill = [v for v in bm.verts if not (zlo <= v.co.z <= zhi) or abs(v.co.x) > (sleeve if name != 'coat' else wr.x - .02)]
        bmesh.ops.delete(bm, geom=kill, context='VERTS')
        for v in bm.verts:
            v.co += v.normal * grow
            if flare and v.co.z < zlo + (zhi - zlo) * .5: k = (zlo + (zhi - zlo) * .5 - v.co.z) / ((zhi - zlo) * .5); v.co.x *= 1 + flare * k; v.co.y = Y + (v.co.y - Y) * (1 + flare * k)
        if open_front:
            kill = [f_ for f_ in bm.faces if f_.calc_center_median().y < Y - .04 and abs(f_.calc_center_median().x) < open_front]
            bmesh.ops.delete(bm, geom=kill, context='FACES')
        me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
        o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
        sol = o.modifiers.new('s', 'SOLIDIFY'); sol.thickness = .008; apply_all(o); smooth(o)
        return keep(o, m, bone)
    if top == 'vest': shell('vest', belt_z - .02, zN - .02, .012, 'Outfit', open_front=.035)
    if top == 'jacket': shell('jacket', belt_z - .06, zN - .01, .012, 'Outfit', open_front=.04); body.data.materials[1] = mats['Inner']
    if top == 'coat':
        shell('coat', belt_z - .04, zN - .01, .014, 'Outfit', open_front=.035); body.data.materials[1] = mats['Inner']
        cs = cone_skirt('coattail', Y + .01, belt_z + .02, kne.z - .08, .15 if not f else .145, .22, .012)
        bm = bmesh.new(); bm.from_mesh(cs.data)   # open at the front like a lab coat
        bmesh.ops.delete(bm, geom=[f_ for f_ in bm.faces if f_.calc_center_median().y < Y - .06 and abs(f_.calc_center_median().x) < .045], context='FACES'); bm.to_mesh(cs.data); bm.free()
        keep(cs, 'Outfit', 'Hips')
    if top == 'hoodie':
        hood = ellipsoid('hood', (0, Y + .07, zN + .02), (.13, .07, .06), 20, 12); keep(hood, 'Outfit', 'Chest')
        pts = [tuple(v.co) for v in body.data.vertices if abs(v.co.z - (belt_z + .09)) < .03 and abs(v.co.x) < .05]
        fy = min(p[1] for p in pts) if pts else Y - .09
        keep(ellipsoid('pocket', (0, fy - .004, belt_z + .085), (.085, .008, .045), 14, 8), 'Outfit', 'Abdomen')
        for s in (1, -1): keep(ellipsoid('string', (s * .03, Y - .11, zN - .07), (.006, .006, .04), 6, 6), 'Inner', 'Chest')
    if top == 'skirt':
        sk = cone_skirt('skirt', Y, belt_z + .01, hip.z - .26, .14 if f else .15, .23, .02); keep(sk, 'Skirt', 'Hips')
    # ---- head
    k = 1.16; HC = Vector((0, Y, zH + .128 * k + (-.02 if f else 0)))
    head = ellipsoid('head', HC, (.148 * k * (.96 if f else 1), .142 * k, .165 * k), 32, 22)
    for v in head.data.vertices:
        z = v.co.z / (.165 * k)
        if z < 0:
            t = min(1, -z); v.co.x *= 1 - (.42 if f else .38) * t * t
            if v.co.y < 0: v.co.y *= 1 - .12 * t
    bake_loc(head); keep(head, 'Skin', 'Head')
    def surf(x, z):
        ok, loc, n, i = head.ray_cast(Vector((x, -2, z)), Vector((0, 1, 0)))
        return loc if ok else Vector((x, Y - .16, z))
    for s in (1, -1):
        ex, ez = s * .066 * (1.02 if f else 1), HC.z - .03
        p = surf(ex, ez); ew = 1.12 if f else 1
        keep(ellipsoid('ew', p + Vector((0, .007, 0)), (.038 * ew, .013, .049 * ew), 20, 14), 'EyeWhite', 'Head')
        keep(ellipsoid('ir', p + Vector((s * -.003, -.003, -.005)), (.027 * ew, .01, .039 * ew), 20, 14), 'Eye', 'Head')
        keep(ellipsoid('pu', p + Vector((s * -.003, -.009, -.008)), (.013 * ew, .006, .02 * ew), 12, 8), 'Pupil', 'Head')
        keep(ellipsoid('shine', p + Vector((s * .007, -.012, .014)), (.009, .004, .009), 10, 6), 'EyeShine', 'Head')
        if f:  # lashes
            la = ellipsoid('lash', p + Vector((s * .006, -.004, .045)), (.043, .007, .008), 12, 6); la.rotation_euler.y = s * -.2; keep(la, 'Pupil', 'Head')
            keep(ellipsoid('blush', surf(s * .09, HC.z - .085) + Vector((0, -.002, 0)), (.022, .004, .01), 10, 6), 'Blush', 'Head')
        br = ellipsoid('brow', surf(s * .068, HC.z + .052) + Vector((0, -.005, 0)), (.036, .008, .007), 12, 6); br.rotation_euler.y = s * (.08 if f else .14); keep(br, 'Eyebrows', 'Head')
        keep(ellipsoid('ear', (s * .148 * k * .97, Y + .01, HC.z - .03), (.022, .03, .042), 12, 8), 'Skin', 'Head')
    keep(ellipsoid('mouth', surf(0, HC.z - .125) + Vector((0, .002, 0)), (.02, .005, .005), 12, 6), 'Mouth', 'Head')
    keep(ellipsoid('nose', surf(0, HC.z - .07) + Vector((0, .004, 0)), (.008, .01, .012), 8, 6), 'Skin', 'Head')
    keep(make_hair(HC, k, Y, f), 'Hair', 'Head')
    return objs

def ring(name, rx, ry, Y, z, h, th):
    bm = bmesh.new(); seg = 40
    lo = [bm.verts.new((math.cos(i / seg * 6.283) * rx, Y + math.sin(i / seg * 6.283) * ry, z)) for i in range(seg)]
    hi = [bm.verts.new((math.cos(i / seg * 6.283) * rx, Y + math.sin(i / seg * 6.283) * ry, z + h)) for i in range(seg)]
    for i in range(seg): bm.faces.new((lo[i], lo[(i + 1) % seg], hi[(i + 1) % seg], hi[i]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    sol = o.modifiers.new('s', 'SOLIDIFY'); sol.thickness = th; apply_all(o); smooth(o); return o

def cone_skirt(name, Y, ztop, zbot, rtop, rbot, th):
    bm = bmesh.new(); seg = 32; rows = 5; prev = None
    for r in range(rows):
        t = r / (rows - 1); z = ztop + (zbot - ztop) * t; rr = rtop + (rbot - rtop) * t
        cur = [bm.verts.new((math.cos(i / seg * 6.283) * rr * (1 + .06 * math.sin(i * 3.0) * t), Y + math.sin(i / seg * 6.283) * rr * .8, z)) for i in range(seg)]
        if prev:
            for i in range(seg): bm.faces.new((prev[i], prev[(i + 1) % seg], cur[(i + 1) % seg], cur[i]))
        prev = cur
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    sol = o.modifiers.new('s', 'SOLIDIFY'); sol.thickness = th; apply_all(o); smooth(o); return o

def spike(base, d, L, r, bend=Vector((0, 0, 0)), flat=.7, seg=10):
    bm = bmesh.new(); d = d.normalized(); up = Vector((0, 0, 1)) if abs(d.z) < .9 else Vector((1, 0, 0)); a = d.cross(up).normalized(); b = d.cross(a).normalized()
    rows = 6; prev = None
    for kk in range(rows):
        t = kk / (rows - 1); c = base + d * L * t + bend * (t * t) * L; rr = r * (1 - t) ** 1.1 + .0008
        cur = [bm.verts.new(c + (a * math.cos(i / seg * 6.283) * rr * 1.25 + b * math.sin(i / seg * 6.283) * rr * flat)) for i in range(seg)]
        if prev:
            for i in range(seg): bm.faces.new((prev[i], prev[(i + 1) % seg], cur[(i + 1) % seg], cur[i]))
        prev = cur
    me = bpy.data.meshes.new('spk'); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new('spk', me); bpy.context.scene.collection.objects.link(o); smooth(o); return o

def make_hair(HC, k, Y, f):
    cap = ellipsoid('hair', HC + Vector((0, .01, .02)), (.162 * k, .16 * k, .172 * k), 32, 22)
    bm = bmesh.new(); bm.from_mesh(cap.data); s_ = k
    kill = [v for v in bm.verts if (v.co.y < -.07 * s_ and v.co.z < .05 * s_) or v.co.z < (-.2 if f else -.11) * s_ or (v.co.y < 0 and v.co.z < -.02 * s_ and abs(v.co.x) < .14 * s_)]
    bmesh.ops.delete(bm, geom=kill, context='VERTS'); bm.to_mesh(cap.data); bm.free()
    sol = cap.modifiers.new('s', 'SOLIDIFY'); sol.thickness = .012; sol.offset = 1; apply_all(cap); smooth(cap)
    parts = [cap]
    if not f:
        for ax, az, L in [(0, 1.3, .15), (.5, 1.1, .14), (-.5, 1.1, .14), (1.0, .7, .13), (-1.0, .7, .13), (.3, .5, .16), (-.3, .5, .16), (.75, .2, .13), (-.75, .2, .13), (0, .15, .15), (1.25, 0.0, .11), (-1.25, 0.0, .11)]:
            dv = Vector((math.sin(ax) * math.cos(az - .4), math.cos(ax) * .9 + .25, math.sin(az))).normalized()
            parts.append(spike(HC + Vector((dv.x * .15, dv.y * .14 + .01, dv.z * .15 + .02)), dv + Vector((0, .5, 0)), L * k, .06, Vector((0, .3, -.25))))
        bangs = [(-.1, .11, -.25), (-.04, .13, -.08), (.02, .125, .1), (.085, .11, .3), (.135, .09, .5), (-.14, .09, -.5)]
    else:
        # long hair: a sheet of locks down the back to the shoulder blades + side locks framing the face
        for i in range(11):
            a = -1.25 + i * .25; base = HC + Vector((math.sin(a) * .15 * k, math.cos(a) * .12 * k + .03, -.02))
            parts.append(spike(base, Vector((math.sin(a) * .15, .25, -1)), .3 * k, .06, Vector((0, .15, .1)), flat=.55))
        for s in (1, -1): parts.append(spike(HC + Vector((s * .14 * k, -.06, .02)), Vector((s * .08, -.12, -1)), .24 * k, .045, Vector((s * .02, 0, 0)), flat=.6))
        bangs = [(-.1, .1, -.3), (-.045, .12, -.1), (.01, .125, .05), (.065, .115, .2), (.115, .1, .45)]
    for x, L, tw in bangs:
        parts.append(spike(HC + Vector((x * k, -.12 * k, .14 * k)), Vector((tw * .4, -.35, -1)), L * k, .045, Vector((0, -.15, .1))))
    if not f:
        for s in (1, -1): parts.append(spike(HC + Vector((s * .155 * k, -.045, .05)), Vector((s * .1, -.15, -1)), .1 * k, .035))
    return join(parts, 'hair')

def bind(arm, objs):
    for o in bpy.context.selected_objects: o.select_set(False)
    autos = [o for o in objs if not o.get('bone')]; rig = [o for o in objs if o.get('bone')]
    for o in autos: o.select_set(True)
    arm.select_set(True); bpy.context.view_layer.objects.active = arm
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    for o in rig:
        for g in list(o.vertex_groups): o.vertex_groups.remove(g)
        g = o.vertex_groups.new(name=o['bone']); g.add([v.index for v in o.data.vertices], 1.0, 'REPLACE')
        bake_loc(o)
    # one mesh: every material becomes a single draw call
    main = autos[0]
    for o in bpy.context.selected_objects: o.select_set(False)
    for o in rig + autos: o.select_set(True)
    bpy.context.view_layer.objects.active = main; bpy.ops.object.join()
    main.name = 'Trainer'; main.data.name = 'Trainer'
    objs[:] = [main]

def export(arm, objs, path):
    if arm.animation_data: arm.animation_data.action = None
    arm.data.pose_position = 'POSE'
    for sc_ in bpy.data.scenes:
        for vl in sc_.view_layers:
            for o in sc_.objects:
                try: o.select_set(False, view_layer=vl)
                except Exception: pass
    arm.select_set(True)
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.export_scene.gltf(filepath=path, use_selection=True, export_format='GLB', export_animations=True, export_animation_mode='NLA_TRACKS',
        export_apply=False, export_yup=True, export_skins=True, export_morph=False, export_texcoords=False, export_normals=True, export_materials='EXPORT')
