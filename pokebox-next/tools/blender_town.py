# Pokebox Next — town generator (runs inside Blender 5.x, bpy).
# Builds the first town's buildings, props and ground as FBX files + a placement plan (town_plan.json) that the
# Unreal build script (Content/Python/build_town.py) turns into a level.
# Style target: chunky, bevelled, hand-made "stylized realism": modelled clapboard siding, trims, gutters, window
# boxes, tiled gable roofs, stone foundations. Every surface gets world-scale box UVs (1 UV = 1 m) so the Poly Haven
# textures tile evenly; material slot names are the Unreal material names (M_*).
# Coordinates: metres, Blender Z-up. Unreal: x_ue = x*100, y_ue = -y*100, z_ue = z*100.
import bpy, bmesh, math, json, os, random
from mathutils import Vector, Matrix

OUT = os.environ.get('PBX_OUT', r"E:\GAME-APP-DEV\POKEMON\PokeboxNext_src")
FBX = os.path.join(OUT, 'fbx'); os.makedirs(FBX, exist_ok=True)
R = random.Random(7)

# ------------------------------------------------------------------ scene helpers
def reset():
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete()
    for m in list(bpy.data.meshes): bpy.data.meshes.remove(m)
    for m in list(bpy.data.materials): bpy.data.materials.remove(m)

def mat(name):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    return m

def mesh_obj(name, bm):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(ob); return ob

def set_mat(ob, mname):
    ob.data.materials.clear(); ob.data.materials.append(mat(mname))

def box(name, sx, sy, sz, loc=(0, 0, 0), m='M_Trim', rot=(0, 0, 0), bevel=0.012):
    """axis-aligned box (size in metres) whose BOTTOM-centre sits at loc"""
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector((sx, sy, sz)), verts=bm.verts)
    bmesh.ops.translate(bm, vec=Vector((0, 0, sz / 2)), verts=bm.verts)
    if bevel > 0 and min(sx, sy, sz) > bevel * 2.5:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=1, affect='EDGES', profile=.5)
    ob = mesh_obj(name, bm); set_mat(ob, m)
    ob.rotation_euler = rot; ob.location = loc; return ob

def cyl(name, r, h, loc=(0, 0, 0), m='M_Metal', rot=(0, 0, 0), seg=12):
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=h)
    bmesh.ops.translate(bm, vec=Vector((0, 0, h / 2)), verts=bm.verts)
    ob = mesh_obj(name, bm); set_mat(ob, m); ob.rotation_euler = rot; ob.location = loc; return ob

def prism_roof(name, w, d, rise, thick, loc, m):
    """gable roof: two slabs meeting at a ridge along X, eaves overhang included in w/d"""
    parts = []
    half = d / 2; L = math.hypot(half, rise); ang = math.atan2(rise, half)
    for s in (-1, 1):
        ob = box(name + ('_L' if s < 0 else '_R'), w, L + .02, thick, (0, 0, 0), m, bevel=.02)
        ob.location = (loc[0], loc[1] + s * half / 2, loc[2] + rise / 2 - thick * .5)
        ob.rotation_euler = (-s * ang, 0, 0)
        parts.append(ob)
    ridge = box(name + '_Ridge', w + .04, .26, .16, (loc[0], loc[1], loc[2] + rise - .04), m, bevel=.03); parts.append(ridge)
    return parts

def gable_wall(name, w, rise, thick, loc, m, axis='x'):
    """triangular gable infill on the short walls"""
    bm = bmesh.new(); h = w / 2
    vs = [bm.verts.new(p) for p in [(-h, -thick / 2, 0), (h, -thick / 2, 0), (0, -thick / 2, rise), (-h, thick / 2, 0), (h, thick / 2, 0), (0, thick / 2, rise)]]
    bm.faces.new((vs[0], vs[1], vs[2])); bm.faces.new((vs[5], vs[4], vs[3])); bm.faces.new((vs[0], vs[3], vs[4], vs[1]))
    bm.faces.new((vs[1], vs[4], vs[5], vs[2])); bm.faces.new((vs[2], vs[5], vs[3], vs[0]))
    ob = mesh_obj(name, bm); set_mat(ob, m); ob.location = loc
    if axis == 'y': ob.rotation_euler = (0, 0, math.pi / 2)
    return ob

def join(objs, name):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    bpy.ops.object.join(); ob = bpy.context.view_layer.objects.active; ob.name = name; ob.data.name = name
    return ob

def box_uv(ob, scale=1.0):
    """world-scale box projection: each face gets the plane of its dominant normal axis"""
    me = ob.data; bm = bmesh.new(); bm.from_mesh(me)
    uv = bm.loops.layers.uv.verify(); mw = ob.matrix_world
    for f in bm.faces:
        n = (mw.to_3x3() @ f.normal); ax = max(range(3), key=lambda i: abs(n[i]))
        for l in f.loops:
            p = mw @ l.vert.co
            if ax == 0: u, v = p.y * (1 if n.x > 0 else -1), p.z
            elif ax == 1: u, v = p.x * (-1 if n.y > 0 else 1), p.z
            else: u, v = p.x, p.y
            l[uv].uv = (u / scale, v / scale)
    bm.to_mesh(me); bm.free()

def export(ob, name):
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active = ob
    box_uv(ob)
    for p in ob.data.polygons: p.use_smooth = False
    path = os.path.join(FBX, name + '.fbx')
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y',
                             mesh_smooth_type='FACE', use_mesh_modifiers=True, add_leaf_bones=False, bake_anim=False)
    return path

# ------------------------------------------------------------------ building parts
def clapboard_wall(prefix, length, height, along, origin, normal_sign, openings, m='M_Siding_White'):
    """overlapping horizontal boards; openings = list of (u0,u1,v0,v1) cut-outs in wall-local metres.
    along: 'x' or 'y' (wall direction); origin = wall start at ground; normal_sign = which side faces out."""
    parts = []; bh = .19; v = 0.0; i = 0
    while v < height - .01:
        hh = min(bh, height - v)
        # split the board around openings
        segs = [(0.0, length)]
        for (u0, u1, v0, v1) in openings:
            if v + hh > v0 and v < v1:
                ns = []
                for a, b in segs:
                    if u1 <= a or u0 >= b: ns.append((a, b)); continue
                    if u0 > a: ns.append((a, u0))
                    if u1 < b: ns.append((u1, b))
                segs = ns
        for a, b in segs:
            if b - a < .05: continue
            t = .028; mid = (a + b) / 2
            if along == 'x': loc = (origin[0] + mid, origin[1] + normal_sign * t / 2, origin[2] + v); sz = (b - a, t, hh + .012)
            else: loc = (origin[0] + normal_sign * t / 2, origin[1] + mid, origin[2] + v); sz = (t, b - a, hh + .012)
            ob = box(f'{prefix}_b{i}', *sz, loc, m, bevel=.006)
            # tilt the board a hair so each one casts a thin shadow line on the next (the clapboard look)
            tilt = math.radians(2.2) * (-normal_sign)
            ob.rotation_euler = (tilt, 0, 0) if along == 'x' else (0, -tilt, 0)
            parts.append(ob); i += 1
        v += bh
    return parts

def window(prefix, w, h, along, center, out_sign, sill=True, flower_box=False, frame_m='M_Trim', glass_m='M_Glass'):
    """framed window centred at center (x,y,z of the opening centre on the wall face)"""
    P = []; cx, cy, cz = center; fw = .09; depth = .12
    def put(sx, sy, sz, lx, lz, m, dy=0.0):
        if along == 'x': P.append(box(f'{prefix}_{len(P)}', sx, depth if sy is None else sy, sz, (cx + lx, cy + out_sign * (depth / 2 + dy), cz + lz), m, bevel=.01))
        else: P.append(box(f'{prefix}_{len(P)}', depth if sy is None else sy, sx, sz, (cx + out_sign * (depth / 2 + dy), cy + lx, cz + lz), m, bevel=.01))
    put(w + fw * 2, None, fw, 0, h / 2, frame_m)               # top
    put(w + fw * 2, None, fw, 0, -h / 2 - fw, frame_m)         # bottom
    put(fw, None, h, -w / 2 - fw / 2, -h / 2, frame_m)          # left
    put(fw, None, h, w / 2 + fw / 2, -h / 2, frame_m)           # right
    put(.045, None, h, 0, -h / 2, frame_m)                      # mullion
    put(w, None, .045, 0, -.02, frame_m)                        # transom
    put(w + .02, .02, h + .02, 0, -h / 2 - .01, glass_m, dy=-.05)  # glass, recessed
    put(w + .3, None, .1, 0, h / 2 + fw, frame_m, dy=.02)       # head trim
    if sill: put(w + .34, .2, .06, 0, -h / 2 - fw - .06, frame_m, dy=.04)
    if flower_box:
        put(w + .1, .28, .22, 0, -h / 2 - fw - .3, 'M_WoodBox', dy=.12)
    return P

def house(name, W, D, H, roof_m, siding_m, porch=True, chimney=True, two_storey=False, lab=False):
    parts = []
    # stone foundation
    parts.append(box(f'{name}_found', W + .3, D + .3, .55, (0, 0, -.1), 'M_Stone', bevel=.04))
    base = .45
    # walls: one flat box; the clapboard boards are PAINTED into the siding texture (T_Siding_*), not modelled —
    # modelled 3 cm boards turned into sub-pixel moiré + black slivers under the ink pass (Wolf Among Us paints them)
    parts.append(box(f'{name}_core', W, D, H, (0, 0, base), siding_m, bevel=.0))
    # window layout per facade (wall-local u from the wall start)
    rows = [1.25] if not two_storey else [1.2, 1.2 + H / 2]
    winw, winh = (1.25, 1.35) if not lab else (1.5, 1.7)
    def facade(length, door=False, n=2):
        ops, wins = [], []
        slots = [length * (i + 1) / (n + 1) for i in range(n)]
        if door: slots = [s for s in slots if abs(s - length / 2) > 1.4] or [length * .2, length * .8]
        for rz in rows:
            for s in slots:
                ops.append((s - winw / 2 - .1, s + winw / 2 + .1, rz - .1, rz + winh + .1)); wins.append((s, rz + winh / 2))
        if door: ops.append((length / 2 - .75, length / 2 + .75, 0, 2.45))
        return ops, wins
    nf = 3 if lab else 2
    F = {'front': facade(W, door=True, n=nf + (1 if lab else 0)), 'back': facade(W, n=nf), 'left': facade(D, n=1 if not lab else 2), 'right': facade(D, n=1 if not lab else 2)}
    # front faces -Y (towards the camera/path), back +Y, left -X, right +X
    walls = {'front': ('x', (-W / 2, -D / 2, base), -1, W), 'back': ('x', (-W / 2, D / 2, base), 1, W),
             'left': ('y', (-W / 2, -D / 2, base), -1, D), 'right': ('y', (W / 2, -D / 2, base), 1, D)}
    for k, (along, org, sgn, L) in walls.items():
        ops, wins = F[k]
        for j, (u, vz) in enumerate(wins):
            if along == 'x': c = (org[0] + u, org[1] + sgn * .03, base + vz)
            else: c = (org[0] + sgn * .03, org[1] + u, base + vz)
            parts += window(f'{name}_{k}_w{j}', winw, winh, along, c, sgn, flower_box=(k == 'front' and vz < 2.5 and not lab))
    # corner boards
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(box(f'{name}_corner{sx}{sy}', .2, .2, H + .05, (sx * (W / 2 + .03), sy * (D / 2 + .03), base), 'M_Trim', bevel=.015))
    # frieze board under the eaves
    parts.append(box(f'{name}_friezeF', W + .3, .1, .22, (0, -D / 2 - .06, base + H - .2), 'M_Trim'))
    parts.append(box(f'{name}_friezeB', W + .3, .1, .22, (0, D / 2 + .06, base + H - .2), 'M_Trim'))
    # door
    door_m = 'M_Door'
    parts.append(box(f'{name}_door', 1.2, .1, 2.25, (0, -D / 2 - .02, base), door_m, bevel=.02))
    parts.append(box(f'{name}_doorframe', 1.6, .16, .16, (0, -D / 2 - .05, base + 2.3), 'M_Trim'))
    for s in (-1, 1): parts.append(box(f'{name}_doorjamb{s}', .16, .16, 2.3, (s * .72, -D / 2 - .05, base), 'M_Trim'))
    parts.append(box(f'{name}_knob', .08, .08, .08, (.42, -D / 2 - .1, base + 1.05), 'M_Metal', bevel=.0))
    # steps
    for i in range(3): parts.append(box(f'{name}_step{i}', 2.0 - i * .25, .45, .16, (0, -D / 2 - .5 - (2 - i) * .3 + .3, -.05 + i * .16), 'M_Stone', bevel=.03))
    if porch:
        parts.append(box(f'{name}_canopy', 2.4, 1.3, .12, (0, -D / 2 - .6, base + 2.75), roof_m, rot=(math.radians(-12), 0, 0), bevel=.02))
        for s in (-1, 1): parts.append(box(f'{name}_bracket{s}', .1, .7, .1, (s * 1.0, -D / 2 - .35, base + 2.55), 'M_Trim'))
    # roof
    rise = D * (.42 if not lab else .3); ov = .45
    parts += prism_roof(f'{name}_roof', W + ov * 2, D + ov * 2, rise + ov * .42 * 2, .16, (0, 0, base + H - .05 - ov * .42), roof_m)
    parts.append(gable_wall(f'{name}_gableL', D, rise, .3, (-W / 2 + .14, 0, base + H), siding_m, axis='y'))
    parts.append(gable_wall(f'{name}_gableR', D, rise, .3, (W / 2 - .14, 0, base + H), siding_m, axis='y'))
    # gutters + downpipes
    for s in (-1, 1):
        parts.append(cyl(f'{name}_gutter{s}', .07, W + ov * 2, (-(W + ov * 2) / 2, s * (D / 2 + ov - .05), base + H - .28), 'M_Metal', rot=(0, math.pi / 2, 0)))
        parts.append(cyl(f'{name}_pipe{s}', .05, H + .2, (s * (W / 2 + .12), -(D / 2 + .15), base - .1), 'M_Metal'))
    if chimney:
        parts.append(box(f'{name}_chimney', .8, .8, rise + 1.6, (W * .28, D * .18, base + H - .2), 'M_Brick', bevel=.02))
        parts.append(box(f'{name}_chimcap', 1.0, 1.0, .14, (W * .28, D * .18, base + H + rise + 1.4), 'M_Stone', bevel=.02))
    if lab:  # matte white radar dish (shallow cone, not a chrome half-sphere) + columns at the entrance
        px_, py_, pz_ = W * .35, -D * .1, base + H + rise * .55
        parts.append(cyl(f'{name}_dishpole', .07, 1.3, (px_, py_, pz_), 'M_Iron'))
        bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=False, segments=20, radius1=.12, radius2=.85, depth=.32)
        dish = mesh_obj(f'{name}_dish', bm); set_mat(dish, 'M_Trim'); dish.location = (px_, py_ - .15, pz_ + 1.45); dish.rotation_euler = (math.radians(55), 0, 0); parts.append(dish)
        parts.append(cyl(f'{name}_dishfeed', .03, .55, (px_, py_ - .15, pz_ + 1.3), 'M_Red', rot=(math.radians(55), 0, 0), seg=8))
        for s in (-1, 1): parts.append(cyl(f'{name}_col{s}', .14, 2.8, (s * 1.25, -D / 2 - 1.2, base), 'M_Trim'))
    ob = join(parts, name)
    return ob

# ------------------------------------------------------------------ interiors (rooms live 60 m under their buildings)
INTERIOR_Z = -60.0
def room(name, W, D, H, wall_m, n_windows=2, door_w=1.5, door_h=2.5):
    """closed room shell, inner size W x D x H, floor top at z=0, door opening centred in the +Y wall,
    'daylight' window panes (emissive) in the -Y wall. Walls are 0.25 m boxes OUTSIDE the inner rectangle."""
    P = []; t = .25
    P.append(box(f'{name}_floor', W + 2 * t, D + 2 * t, .3, (0, 0, -.3), 'M_Floor', bevel=0))
    P.append(box(f'{name}_ceil', W + 2 * t, D + 2 * t, .3, (0, 0, H), 'M_Plaster', bevel=0))
    for s in (-1, 1): P.append(box(f'{name}_side{s}', t, D, H, (s * (W / 2 + t / 2), 0, 0), wall_m, bevel=0))
    # back wall (-Y) with window openings
    wins = [W * (i + 1) / (n_windows + 1) - W / 2 for i in range(n_windows)]; ww, wh, wz = 1.6, 1.5, 1.0
    xs = [-W / 2] + sum([[c - ww / 2, c + ww / 2] for c in wins], []) + [W / 2]
    for i in range(0, len(xs), 2):
        a, b = xs[i], xs[i + 1]
        if b - a > .01: P.append(box(f'{name}_back{i}', b - a, t, H, ((a + b) / 2, -D / 2 - t / 2, 0), wall_m, bevel=0))
    for j, c in enumerate(wins):
        P.append(box(f'{name}_wlo{j}', ww, t, wz, (c, -D / 2 - t / 2, 0), wall_m, bevel=0))
        P.append(box(f'{name}_whi{j}', ww, t, H - wz - wh, (c, -D / 2 - t / 2, wz + wh), wall_m, bevel=0))
        P.append(box(f'{name}_pane{j}', ww, .05, wh, (c, -D / 2 - t + .02, wz), 'M_WindowLight', bevel=0))
        for k in (-1, 1): P.append(box(f'{name}_wf{j}{k}', .09, .14, wh, (c + k * (ww / 2 - .045), -D / 2 + .03, wz), 'M_Trim', bevel=.01))
        P.append(box(f'{name}_wft{j}', ww, .14, .09, (c, -D / 2 + .03, wz + wh - .09), 'M_Trim', bevel=.01))
        P.append(box(f'{name}_wfm{j}', .06, .12, wh, (c, -D / 2 + .03, wz), 'M_Trim', bevel=0))
        P.append(box(f'{name}_sill{j}', ww + .2, .26, .07, (c, -D / 2 + .1, wz - .07), 'M_Trim', bevel=.01))
    # front wall (+Y) with the door opening + a closed door leaf you walk "through" (interaction teleports)
    for s in (-1, 1):
        L = W / 2 - door_w / 2; P.append(box(f'{name}_front{s}', L, t, H, (s * (door_w / 2 + L / 2), D / 2 + t / 2, 0), wall_m, bevel=0))
    P.append(box(f'{name}_lintel', door_w, t, H - door_h, (0, D / 2 + t / 2, door_h), wall_m, bevel=0))
    P.append(box(f'{name}_door', door_w, .08, door_h, (0, D / 2 + .05, 0), 'M_Door', bevel=.02))
    P.append(box(f'{name}_knob', .08, .08, .08, (door_w * .32, D / 2 - .02, 1.05), 'M_Metal', bevel=0))
    for s in (-1, 1): P.append(box(f'{name}_jamb{s}', .12, .16, door_h + .1, (s * (door_w / 2 + .06), D / 2 - .02, 0), 'M_Trim', bevel=.01))
    P.append(box(f'{name}_head', door_w + .36, .16, .12, (0, D / 2 - .02, door_h), 'M_Trim', bevel=.01))
    # baseboards + a ceiling cornice: the comic ink loves these edges
    for (sx, sy, lx, ly) in [(W, .05, 0, -D / 2 + .025), (.05, D, -W / 2 + .025, 0), (.05, D, W / 2 - .025, 0)]:
        P.append(box(f'{name}_base{lx}{ly}', sx, sy, .14, (lx, ly, 0), 'M_Trim', bevel=0))
        P.append(box(f'{name}_corn{lx}{ly}', sx, sy, .1, (lx, ly, H - .1), 'M_Trim', bevel=0))
    return join(P, name)

# ------------------------------------------------------------------ props
def fence_segment():
    P = [box('f_post0', .14, .14, 1.1, (-1, 0, 0), 'M_WoodDark', bevel=.02), box('f_post1', .14, .14, 1.1, (1, 0, 0), 'M_WoodDark', bevel=.02)]
    for z in (.45, .85): P.append(box(f'f_rail{z}', 2.1, .08, .12, (0, 0, z), 'M_WoodDark', bevel=.015))
    return join(P, 'SM_Fence')

def lamp_post():
    P = [cyl('lp_base', .16, .3, (0, 0, 0), 'M_Iron'), cyl('lp_pole', .06, 3.2, (0, 0, .3), 'M_Iron'), box('lp_head', .36, .36, .5, (0, 0, 3.45), 'M_LampGlass', bevel=.02),
         box('lp_cap', .5, .5, .1, (0, 0, 3.95), 'M_Iron', bevel=.02), box('lp_ring', .3, .3, .06, (0, 0, 3.42), 'M_Iron', bevel=.0)]
    return join(P, 'SM_LampPost')

def mailbox():
    P = [box('mb_post', .12, .12, 1.0, (0, 0, 0), 'M_WoodDark', bevel=.02), box('mb_box', .32, .55, .3, (0, 0, 1.0), 'M_MailBlue', bevel=.05),
         box('mb_flag', .03, .05, .3, (.18, .1, 1.1), 'M_Red', bevel=.0)]
    return join(P, 'SM_Mailbox')

def signboard():
    P = [box('sg_p0', .14, .14, 1.4, (-.6, 0, 0), 'M_WoodDark'), box('sg_p1', .14, .14, 1.4, (.6, 0, 0), 'M_WoodDark'),
         box('sg_board', 1.6, .1, .8, (0, -.05, .75), 'M_WoodLight', bevel=.03)]
    return join(P, 'SM_Sign')

def bench():
    P = [box('bn_seat', 1.8, .45, .07, (0, 0, .45), 'M_WoodLight'), box('bn_back', 1.8, .07, .4, (0, .22, .55), 'M_WoodLight')]
    for s in (-1, 1): P.append(box(f'bn_leg{s}', .08, .45, .45, (s * .8, 0, 0), 'M_Iron'))
    return join(P, 'SM_Bench')

def trash_bin():
    return join([cyl('tb', .3, .9, (0, 0, 0), 'M_BinGreen', seg=16), cyl('tb_lid', .33, .08, (0, 0, .9), 'M_BinGreen', seg=16)], 'SM_Bin')

# ------------------------------------------------------------------ ground
TOWN = dict(size=220.0, res=176)
TRACK_X = 40.0                       # railway along x = 40 (east edge of town), tunnel portal at the north end
TRACK_Y0, TRACK_Y1 = -113.0, 27.0    # tunnel mouth .. buffer stop
PLATFORM = (34.6, 38.4, -20.0, 24.0) # x0, x1, y0, y1 (top at +0.55 m)
def height(x, y):
    """flat village plateau, soft hills inland, slope down to the beach on the south (+y)"""
    h = 0.0
    h += .35 * math.sin(x * .07) * math.cos(y * .05) + .25 * math.sin(x * .13 + 1.3) * math.sin(y * .11 + .4)
    d = math.hypot(x, y + 10)
    h *= min(1, max(0, (d - 30) / 25))              # village core stays flat
    ring = max(0, d - 70); h += ring * ring * .004 * (1 - min(1, max(0, (y - 25) / 20)))  # hills around (forest edge), not on the sea side
    if y > 42: h -= (y - 42) * .32                  # beach slope
    if y > 52: h -= (y - 52) * .25                  # under the sea
    # railway: a flat bed (a cutting through the hills) from the station north to the tunnel in the mountains
    if y < 30:
        k = min(1, max(0, (abs(x - TRACK_X) - 4.0) / 7.0)); k = k * k * (3 - 2 * k)
        h = h * k
    return h

def path_mask(x, y, plan):
    m = 0.0
    for (ax, ay, bx, by, w) in plan['paths']:
        dx, dy = bx - ax, by - ay; L2 = max(1e-6, dx * dx + dy * dy)
        t = max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / L2)); px, py = ax + dx * t, ay + dy * t
        d = math.hypot(x - px, y - py) - w / 2
        m = max(m, min(1, max(0, (1.2 - d) / 1.2)))
    return m

def ground(plan):
    S, N = TOWN['size'], TOWN['res']
    bm = bmesh.new(); col = bm.loops.layers.color.new('Col'); uvl = bm.loops.layers.uv.new('UV')
    grid = [[bm.verts.new((-S / 2 + S * i / N, -S / 2 + S * j / N, 0)) for i in range(N + 1)] for j in range(N + 1)]
    for row in grid:
        for v in row: v.co.z = height(v.co.x, v.co.y)
    for j in range(N):
        for i in range(N):
            f = bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
            for l in f.loops:
                x, y = l.vert.co.x, l.vert.co.y
                pm = path_mask(x, y, plan); sand = min(1, max(0, (y - 40) / 5)); plaza = 1.0 if (abs(x) < 9 and -27 < y < -17) else 0.0
                l[col] = (pm, sand, plaza, 1.0)           # R = dirt path, G = sand, B = flagstone plaza
                l[uvl].uv = (x / 4, y / 4)
    ob = mesh_obj('SM_Ground', bm); set_mat(ob, 'M_Ground')
    for p in ob.data.polygons: p.use_smooth = True
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.fbx(filepath=os.path.join(FBX, 'SM_Ground.fbx'), use_selection=True, apply_scale_options='FBX_SCALE_ALL',
                             axis_forward='-Z', axis_up='Y', mesh_smooth_type='FACE', colors_type='LINEAR', add_leaf_bones=False, bake_anim=False)

def splat(plan, res=512):
    """ground mask texture (R = dirt path, G = sand, B = flagstone plaza) covering the TOWN square; Unreal samples it by world XY"""
    S = TOWN['size']; px = [0.0] * (res * res * 4)
    for j in range(res):
        y = -S / 2 + S * (j + .5) / res
        for i in range(res):
            x = -S / 2 + S * (i + .5) / res; k = (j * res + i) * 4
            px[k] = path_mask(x, y, plan); px[k + 1] = min(1, max(0, (y - 40) / 5)); px[k + 2] = 1.0 if (abs(x) < 9 and -27 < y < -17) else 0.0; px[k + 3] = 1.0
    im = bpy.data.images.new('T_TownSplat', res, res, alpha=False, float_buffer=False); im.colorspace_settings.name = 'Non-Color'
    im.pixels = px; im.filepath_raw = os.path.join(OUT, 'tex', 'T_TownSplat.png'); im.file_format = 'PNG'; im.save()

def echo_card():
    """1 x 1 m upright quad for the paper Echoes / display cards: bottom-centre origin, faces -Y (Unreal +Y), UV 0..1"""
    me = bpy.data.meshes.new('SM_EchoCard')
    me.from_pydata([(-.5, 0, 0), (.5, 0, 0), (.5, 0, 1), (-.5, 0, 1)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(name='UV')
    for i, l in enumerate(me.loops): uv.data[i].uv = [(0, 0), (1, 0), (1, 1), (0, 1)][l.vertex_index]
    ob = bpy.data.objects.new('SM_EchoCard', me); bpy.context.collection.objects.link(ob); set_mat(ob, 'M_EchoPaper')
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.fbx(filepath=os.path.join(FBX, 'SM_EchoCard.fbx'), use_selection=True, apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y',
                             mesh_smooth_type='FACE', add_leaf_bones=False, bake_anim=False)

def water_plane():
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=40, y_segments=20, size=1)
    bmesh.ops.scale(bm, vec=Vector((1600, 700, 1)), verts=bm.verts)
    ob = mesh_obj('SM_Water', bm); set_mat(ob, 'M_Water'); return export(ob, 'SM_Water')


# ------------------------------------------------------------------ railway (station, platform, track, tunnel, train)
def station_building():
    return house('SM_Station', 8.0, 5.5, 3.4, 'M_Roof_Green', 'M_Siding_Cream', porch=True, chimney=False)

def platform():
    x0, x1, y0, y1 = PLATFORM; W, L = x1 - x0, y1 - y0; cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    P = [box('pf_body', W, L, .55, (0, 0, 0), 'M_Stone', bevel=.03),
         box('pf_edge', .35, L, .06, (W / 2 - .17, 0, .55), 'M_EdgeYellow', bevel=.0)]       # yellow safety line on the track side
    for i in range(4):                                                                    # steps up from the road end
        P.append(box(f'pf_step{i}', 2.4, .35, .14 * (i + 1), (-W / 2 - .2 - (3 - i) * .35 + .17, -L / 2 + 26, 0), 'M_Stone', bevel=.02))
    # canopy over the middle third: iron posts + a pitched sheet roof
    for k in range(5):
        y = -8 + k * 4.2
        P.append(cyl(f'pf_post{k}', .09, 3.4, (-W / 2 + .5, y - cy + cy, .55), 'M_Iron'))
    P.append(box('pf_roof', W + 1.0, 18.5, .14, (.1, .4, 3.95), 'M_Roof_Green', rot=(0, math.radians(-7), 0), bevel=.02))
    P.append(box('pf_fascia', .12, 18.5, .3, (W / 2 + .55, .4, 3.75), 'M_Trim', bevel=.0))
    # benches, clock, sign posts
    for y in (-4.0, 4.0):
        P += [box(f'pf_bs{y}', .45, 1.8, .07, (-W / 2 + 1.0, y, 1.0), 'M_WoodLight'), box(f'pf_bb{y}', .07, 1.8, .4, (-W / 2 + .8, y, 1.1), 'M_WoodLight')]
        for s_ in (-1, 1): P.append(box(f'pf_bl{y}{s_}', .45, .08, .45, (-W / 2 + 1.0, y + s_ * .8, .55), 'M_Iron'))
    P.append(cyl('pf_clockpole', .06, 2.6, (0, 9.5, .55), 'M_Iron'))
    P.append(cyl('pf_clock', .32, .14, (0, 9.5 + .07, 3.4), 'M_Trim', rot=(math.pi / 2, 0, 0), seg=20))
    P.append(cyl('pf_clockrim', .36, .1, (0, 9.5 + .05, 3.4), 'M_Iron', rot=(math.pi / 2, 0, 0), seg=20))
    ob = join(P, 'SM_Platform'); return ob

def track():
    """two rails on sleepers on a gravel bed, from the tunnel mouth to the buffer stop (local x = 0 is the track centre)"""
    L = TRACK_Y1 - TRACK_Y0; cy = (TRACK_Y0 + TRACK_Y1) / 2
    P = [box('tr_bed', 3.6, L, .22, (0, 0, -.05), 'M_Gravel', bevel=.0)]
    n = int(L / .65)
    for i in range(n): P.append(box(f'tr_sl{i}', 2.5, .24, .12, (0, -L / 2 + .3 + i * .65, .14), 'M_WoodDark', bevel=.0))
    for s_ in (-1, 1): P.append(box(f'tr_rail{s_}', .09, L, .14, (s_ * .72, 0, .26), 'M_Metal', bevel=.0))
    # buffer stop at the south end
    y = L / 2 - .4
    P += [box('tr_bufbeam', 2.4, .35, .4, (0, y, .55), 'M_Red', bevel=.03), box('tr_bufpost0', .25, .6, .9, (-.9, y + .2, .1), 'M_Iron'),
          box('tr_bufpost1', .25, .6, .9, (.9, y + .2, .1), 'M_Iron')]
    for s_ in (-1, 1): P.append(cyl(f'tr_bufpad{s_}', .16, .2, (s_ * .72, y - .17, .75), 'M_Iron', rot=(math.pi / 2, 0, 0), seg=12))
    return join(P, 'SM_Track')

def tunnel_portal():
    """stone arch built into the mountain face; the opening is 5.6 m wide x 6.4 m high, dark inside"""
    P = []; w, h, d = 5.6, 4.6, 1.6
    for s_ in (-1, 1): P.append(box(f'tp_pier{s_}', 2.2, d, h, (s_ * (w / 2 + 1.1), 0, 0), 'M_Stone', bevel=.05))
    n = 11
    for i in range(n):            # voussoirs of a round arch
        a0 = math.pi * i / n; a1 = math.pi * (i + 1) / n; am = (a0 + a1) / 2
        r = w / 2 + .55
        ob = box(f'tp_v{i}', 1.1, d, math.pi * r / n + .05, (0, 0, 0), 'M_Stone', bevel=.04)
        ob.rotation_euler = (0, -(am - math.pi / 2), 0)
        ob.location = (math.cos(am) * r, 0, h + math.sin(am) * r - (math.pi * r / n) / 2 * 0)
        P.append(ob)
    P.append(box('tp_wall', w + 7.0, d * .8, 3.0, (0, .3, h + w / 2 + .6), 'M_Stone', bevel=.05))      # wall above the arch
    P.append(box('tp_cornice', w + 7.4, d + .3, .35, (0, 0, h + w / 2 + 3.5), 'M_Stone', bevel=.05))
    # the cliff the tunnel is cut into: rock masses either side of and above the tube, up to the mountain behind
    for s_ in (-1, 1): P.append(box(f'tp_cliff{s_}', 14.0, 32.0, 20.0, (s_ * (w / 2 + 2.2 + 7.0), -16.6, -1.0), 'M_CliffRock', bevel=.3))
    P.append(box('tp_cliff_top', w + 4.4, 32.0, 20.0 - (h + w / 2 + 3.9), (0, -16.6, h + w / 2 + 3.9), 'M_CliffRock', bevel=.3))
    P.append(box('tp_cliff_mid', w + 4.4, 30.0, 4.2, (0, -17.6, h + w / 2 - .3), 'M_CliffRock', bevel=0))
    # darkness: a black tube going into the hill
    P.append(box('tp_dark_back', w + .2, .2, h + w / 2 + .2, (0, -30, 0), 'M_TunnelDark', bevel=0))
    for s_ in (-1, 1): P.append(box(f'tp_dark_side{s_}', .2, 30, h + w / 2, (s_ * (w / 2 + .05), -15, 0), 'M_TunnelDark', bevel=0))
    P.append(box('tp_dark_top', w + .2, 30, .2, (0, -15, h + w / 2 - .1), 'M_TunnelDark', bevel=0))
    P.append(box('tp_dark_floor', w + .2, 29.2, .08, (0, -15.8, .02), 'M_TunnelDark', bevel=0))
    # the rails run on into the dark
    for s_ in (-1, 1): P.append(box(f'tp_rail{s_}', .09, 20.0, .14, (s_ * .72, -11, .26), 'M_Metal', bevel=0))
    return join(P, 'SM_Tunnel')

def loco():
    """chunky toy-like steam locomotive, front towards local -Y (north). Origin: rail top, centre."""
    P = []; z0 = .32
    P.append(box('lo_frame', 2.3, 9.0, .45, (0, 0, z0 + .45), 'M_Iron', bevel=.03))
    P.append(cyl('lo_boiler', 1.05, 5.4, (0, -4.6, z0 + 2.05), 'M_TrainRed', rot=(-math.pi / 2, 0, 0), seg=20))
    for k in range(4): P.append(cyl(f'lo_band{k}', 1.09, .12, (0, -4.6 + .9 + k * 1.25, z0 + 2.05), 'M_Brass', rot=(-math.pi / 2, 0, 0), seg=20))
    P.append(cyl('lo_smokebox', 1.08, .7, (0, -4.6, z0 + 2.05), 'M_Iron', rot=(math.pi / 2, 0, 0), seg=20))
    P.append(cyl('lo_lamp', .28, .3, (0, -4.65, z0 + 2.95), 'M_LampGlass', rot=(math.pi / 2, 0, 0), seg=12))
    P.append(cyl('lo_chimney', .38, 1.3, (0, -3.6, z0 + 2.9), 'M_Iron', seg=14))
    P.append(cyl('lo_chimtop', .55, .32, (0, -3.6, z0 + 4.1), 'M_Iron', seg=14))
    P.append(cyl('lo_dome', .45, .55, (0, -1.6, z0 + 3.0), 'M_Brass', seg=14))
    P.append(box('lo_cab', 2.5, 2.8, 2.6, (0, 2.3, z0 + .9), 'M_TrainRed', bevel=.05))
    P.append(box('lo_cabroof', 2.8, 3.2, .18, (0, 2.3, z0 + 3.5), 'M_Iron', bevel=.04))
    for s_ in (-1, 1): P.append(box(f'lo_cabwin{s_}', .06, 1.0, .8, (s_ * 1.26, 2.0, z0 + 2.3), 'M_Glass', bevel=0))
    P.append(box('lo_cow', 2.2, .9, .5, (0, -4.9, z0 + .1), 'M_Red', rot=(math.radians(-25), 0, 0), bevel=.03))   # cow-catcher
    P.append(box('lo_buffer', 2.5, .2, .3, (0, -4.55, z0 + .7), 'M_Red', bevel=.02))
    for s_ in (-1, 1):
        for k, yy in enumerate((-2.8, -1.0, .8)):
            P.append(cyl(f'lo_wheel{s_}{k}', .62, .16, (s_ * 1.0, yy, z0 + .3), 'M_Iron', rot=(0, math.pi / 2, 0), seg=18))
            P.append(cyl(f'lo_hub{s_}{k}', .2, .2, (s_ * 1.06, yy, z0 + .3), 'M_Red', rot=(0, math.pi / 2, 0), seg=10))
        P.append(box(f'lo_rod{s_}', .06, 3.8, .12, (s_ * 1.12, -1.0, z0 + .22), 'M_Metal', bevel=0))
        P.append(box(f'lo_step{s_}', .4, .5, .08, (s_ * 1.2, 3.2, z0 + .1), 'M_Iron', bevel=0))
    ob = join(P, 'SM_TrainLoco'); return ob

def carriage():
    """passenger carriage, 12 m, green with cream window band; origin rail top, centre"""
    P = []; z0 = .32; L = 12.0
    P.append(box('ca_frame', 2.4, L, .4, (0, 0, z0 + .45), 'M_Iron', bevel=.03))
    P.append(box('ca_body', 2.7, L - .4, 1.3, (0, 0, z0 + .85), 'M_TrainGreen', bevel=.05))
    P.append(box('ca_band', 2.74, L - .45, 1.0, (0, 0, z0 + 2.1), 'M_TrainCream', bevel=.04))
    P.append(box('ca_top', 2.7, L - .4, .3, (0, 0, z0 + 3.1), 'M_TrainGreen', bevel=.04))
    P.append(box('ca_roof', 2.9, L - .1, .22, (0, 0, z0 + 3.4), 'M_Iron', bevel=.08))
    for s_ in (-1, 1):
        for k in range(6):
            y = -L / 2 + 1.3 + k * 1.9
            if k == 3: P.append(box(f'ca_door{s_}', .06, 1.0, 2.0, (s_ * 1.38, y, z0 + .95), 'M_Door', bevel=0)); continue
            P.append(box(f'ca_win{s_}{k}', .06, 1.3, .75, (s_ * 1.38, y, z0 + 2.2), 'M_Glass', bevel=0))
        for yy in (-L / 2 + 1.6, L / 2 - 1.6):
            for dy in (-.6, .6): P.append(cyl(f'ca_wh{s_}{yy}{dy}', .42, .14, (s_ * .95, yy + dy, z0 + .1), 'M_Iron', rot=(0, math.pi / 2, 0), seg=14))
    for e in (-1, 1): P.append(box(f'ca_buf{e}', 2.0, .25, .3, (0, e * (L / 2 + .05), z0 + .7), 'M_Iron', bevel=.02))
    return join(P, 'SM_TrainCar')

# ------------------------------------------------------------------ distant landscape (skirt around the town square, mountains, sky)
def far_height(x, y):
    """continues height() outside the 220 m town square: the hills keep rising to a plateau, the sea floor keeps sinking"""
    return height(max(-110, min(110, x)), max(-110, min(110, y))) if (abs(x) <= 110 and abs(y) <= 110) else height(x, y)

def ground_far():
    """coarse ring of terrain from the town square out to 700 m, vertex-coloured grass (tinted darker with distance)"""
    bm = bmesh.new(); col = bm.loops.layers.color.new('Col'); uvl = bm.loops.layers.uv.new('UV')
    R = 700.0; N = 70; inner = 110.0
    xs = [-R + 2 * R * i / N for i in range(N + 1)]
    # split so the inner square edge lines up exactly with the town ground's border
    xs = sorted(set([round(v, 3) for v in xs if abs(v) > inner + 1] + [-inner, inner] + [-inner - 6, inner + 6]
                    + [TRACK_X + d for d in (-11, -7.5, -4, 0, 4, 7.5, 11)]))   # extra lines so the railway cutting stays a clean flat bed
    grid = {}
    for j, y in enumerate(xs):
        for i, x in enumerate(xs):
            z = height(x, y) if (abs(x) > inner - .01 or abs(y) > inner - .01) else 0
            z = min(z, 16.0) if y < 45 else min(z, -8.0)     # hills level out into a plateau; the sea floor stays under water
            grid[(i, j)] = bm.verts.new((x, y, z))
    n = len(xs)
    for j in range(n - 1):
        for i in range(n - 1):
            cx, cy = (xs[i] + xs[i + 1]) / 2, (xs[j] + xs[j + 1]) / 2
            if abs(cx) < inner and abs(cy) < inner: continue
            f = bm.faces.new((grid[(i, j)], grid[(i + 1, j)], grid[(i + 1, j + 1)], grid[(i, j + 1)]))
            for l in f.loops:
                x, y, z = l.vert.co
                sea = min(1, max(0, (y - 40) / 5))
                l[col] = (0.0, sea, 0.0, 1.0)
                l[uvl].uv = (x / 4, y / 4)
    ob = mesh_obj('SM_GroundFar', bm); set_mat(ob, 'M_Ground')
    for p in ob.data.polygons: p.use_smooth = True
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.fbx(filepath=os.path.join(FBX, 'SM_GroundFar.fbx'), use_selection=True, apply_scale_options='FBX_SCALE_ALL',
                             axis_forward='-Z', axis_up='Y', mesh_smooth_type='FACE', colors_type='LINEAR', add_leaf_bones=False, bake_anim=False)

def mountain_peaks():
    """(cx, cy, radius, height) of every mountain; shared by the mesh and by the dressing (trees / rocks on the slopes)"""
    import random as _r
    rnd = _r.Random(21); peaks = []
    # north / east / west arc (the sea is to the south, +y)
    for i in range(26):
        a = math.radians(-200 + 220 * i / 25 + rnd.uniform(-3, 3))   # from west-south-west over north to east-south-east
        d = rnd.uniform(185, 290)
        cx, cy = math.cos(a) * d, math.sin(a) * d * .9 - 20
        if cy > 60: continue
        rad = rnd.uniform(55, 95); hgt = rnd.uniform(55, 120) * (1.0 if i % 3 else 1.35)
        peaks.append((cx, cy, rad, hgt))
        for k in range(2):   # shoulder peaks: break up the cone silhouettes
            sa = rnd.uniform(0, math.tau); sd = rad * rnd.uniform(.45, .7)
            peaks.append((cx + math.cos(sa) * sd, cy + math.sin(sa) * sd, rad * rnd.uniform(.4, .6), hgt * rnd.uniform(.45, .7)))
    for i in range(30):   # green foothills in front (hide the plateau edge)
        a = math.radians(-198 + 216 * i / 29 + rnd.uniform(-4, 4)); d = rnd.uniform(125, 170)
        cx, cy = math.cos(a) * d, math.sin(a) * d * .9 - 15
        if cy > 45: continue
        peaks.append((cx, cy, rnd.uniform(34, 55), rnd.uniform(20, 34)))
    # keep the railway cutting open: nothing may sit on the track between the town and the tunnel portal
    peaks = [p_ for p_ in peaks if not (abs(p_[0] - TRACK_X) < p_[2] + 9 and p_[1] + p_[2] > TRACK_Y0 - 2)]
    peaks.append((TRACK_X, TRACK_Y0 - 30 - 46, 46, 66))   # the tunnel mountain, its foot just behind the cliff the portal is cut into
    return peaks

def mountains():
    """ring of faceted stylized mountains (flat-shaded, palette colours grass -> rock -> snow) around the north half,
    plus the tunnel mountain the railway runs into. Ridges: each cone's radius is modulated by a few angular lobes and
    noise, rows wobble in height; shoulder peaks overlap the big ones. One mesh, origin at world 0."""
    import random as _r
    rnd = _r.Random(21)
    bm = bmesh.new()
    GR, GR2, RK, RK2, SN = (.34, .58, .24), (.26, .48, .2), (.66, .58, .48), (.56, .5, .44), (.97, .98, 1.0)
    def peak(cx, cy, rad, hgt, seg=14, rings=7, seed=0):
        rr = _r.Random(seed); base_z = min(far_height(cx, cy), 12) - 6
        lobes = rr.choice((3, 4, 5)); ph = rr.uniform(0, 6.28); ph2 = rr.uniform(0, 6.28)
        rows = []
        for k in range(rings + 1):
            t = k / rings
            row = []
            for s_ in range(seg):
                a = 2 * math.pi * s_ / seg + rr.uniform(-.08, .08)
                ridge = 1 + .22 * math.sin(lobes * a + ph) * (1 - t * .6) + .1 * math.sin((lobes * 2 + 1) * a + ph2)
                rk = rad * (1 - t) ** 1.2 * ridge * (1 + rr.uniform(-.1, .1) * (1 - t))
                z = base_z + hgt * (t ** .9) + rr.uniform(-.05, .05) * hgt * (1 - t) * t
                row.append(bm.verts.new((cx + math.cos(a) * rk, cy + math.sin(a) * rk, z)))
            rows.append(row)
        top = bm.verts.new((cx + rr.uniform(-2, 2), cy + rr.uniform(-2, 2), base_z + hgt * 1.02))
        for k in range(rings):
            for s_ in range(seg):
                bm.faces.new((rows[k][s_], rows[k][(s_ + 1) % seg], rows[k + 1][(s_ + 1) % seg], rows[k + 1][s_]))
        for s_ in range(seg): bm.faces.new((rows[rings][s_], rows[rings][(s_ + 1) % seg], top))
    for k, (cx, cy, rad, hgt) in enumerate(mountain_peaks()):
        big = hgt > 45
        peak(cx, cy, rad, hgt, seg=24 if big else 14, rings=12 if big else 7, seed=100 + k)
    bm.normal_update()
    # colours via a palette texture (T_Palette_Mountain, one texel per colour): every face's UVs sit in its colour's cell
    # (vertex colours did not survive the FBX -> Interchange import)
    pal = []
    CL, SN2 = (.42, .38, .36), (.85, .88, .95)
    for c in (GR, GR2, RK, RK2, SN, CL, SN2):
        for j in (.9, 1.0, 1.08): pal.append(tuple(min(1, v * j) for v in c))
    uvl = bm.loops.layers.uv.new('UV')
    for f in bm.faces:
        zc = sum(v.co.z for v in f.verts) / len(f.verts); slope = 1 - abs(f.normal.z)
        n_ = math.sin(f.calc_center_median().x * .05) * 6 + math.sin(f.calc_center_median().y * .07) * 5   # wavy band edges
        if zc < 34 + n_ - slope * 14: k = 0 if (int((zc + n_) / 6) % 2 == 0) else 1
        else: k = 2 if (int((zc + n_) / 8) % 2 == 0) else 3
        if slope > .72 and zc > 20: k = 5                                     # steep faces: dark cliff rock
        if zc > 80 + n_ - slope * 20: k = 4 if slope < .6 else 6             # snow caps, greyer on steep sides
        idx = k * 3 + rnd.randrange(3)
        for l in f.loops: l[uvl].uv = ((idx + .5) / len(pal), .5)
    import numpy as np
    img = np.ones((4, len(pal), 4), np.float32)
    for i, c in enumerate(pal): img[:, i, :3] = c
    _save_png('T_Palette_Mountain', img)
    ob = mesh_obj('SM_Mountains', bm); set_mat(ob, 'M_Mountain')
    for p in ob.data.polygons: p.use_smooth = False
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.fbx(filepath=os.path.join(FBX, 'SM_Mountains.fbx'), use_selection=True, apply_scale_options='FBX_SCALE_ALL',
                             axis_forward='-Z', axis_up='Y', mesh_smooth_type='FACE', colors_type='LINEAR', add_leaf_bones=False, bake_anim=False)

def sky_dome():
    """unit sphere seen from inside, equirectangular UVs (v = 1 at the zenith) for the baked stylized sky"""
    me = bpy.data.meshes.new('SM_SkyDome'); NU, NV = 64, 32; V = []; F = []; UV = []
    for j in range(NV + 1):
        lat = -math.pi / 2 + math.pi * j / NV
        for i in range(NU + 1):
            lon = 2 * math.pi * i / NU
            V.append((math.cos(lat) * math.cos(lon), math.cos(lat) * math.sin(lon), math.sin(lat))); UV.append((1 - i / NU, j / NV))
    for j in range(NV):
        for i in range(NU):
            a = j * (NU + 1) + i; b = a + 1; c = a + NU + 2; d = a + NU + 1
            F.append((a, d, c, b))     # wound inwards
    me.from_pydata(V, [], F); uv = me.uv_layers.new(name='UV')
    for poly in me.polygons:
        for li in poly.loop_indices: uv.data[li].uv = UV[me.loops[li].vertex_index]
    ob = bpy.data.objects.new('SM_SkyDome', me); bpy.context.collection.objects.link(ob); set_mat(ob, 'M_Sky')
    for p in me.polygons: p.use_smooth = True
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.fbx(filepath=os.path.join(FBX, 'SM_SkyDome.fbx'), use_selection=True, apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y',
                             mesh_smooth_type='FACE', add_leaf_bones=False, bake_anim=False)

# ------------------------------------------------------------------ painted textures (graphic-novel look)
def _save_png(name, arr):
    """arr: float32 HxWx4 in 0..1, row 0 = bottom (Blender order)"""
    import numpy as np
    h, w = arr.shape[:2]
    im = bpy.data.images.new(name, w, h, alpha=True, float_buffer=False)
    if name.endswith('_nor') or name.endswith('_arm'): im.colorspace_settings.name = 'Non-Color'
    im.pixels.foreach_set(np.ascontiguousarray(arr, dtype=np.float32).ravel())
    im.filepath_raw = os.path.join(OUT, 'tex', name + '.png'); im.file_format = 'PNG'; im.save(); bpy.data.images.remove(im)

def _noise(np, h, w, cells, seed):
    """smooth value noise (bilinear upsampled random grid), tileable"""
    rng = np.random.default_rng(seed); g = rng.random((cells, cells))
    ys = np.arange(h) * cells / h; xs = np.arange(w) * cells / w
    y0 = ys.astype(int); x0 = xs.astype(int); fy = (ys - y0)[:, None]; fx = (xs - x0)[None, :]
    y1 = (y0 + 1) % cells; x1 = (x0 + 1) % cells
    a = g[y0][:, x0]; b = g[y0][:, x1]; c = g[y1][:, x0]; d = g[y1][:, x1]
    fy = fy * fy * (3 - 2 * fy); fx = fx * fx * (3 - 2 * fx)
    return a * (1 - fx) * (1 - fy) + b * fx * (1 - fy) + c * (1 - fx) * fy + d * fx * fy

def _normal_from_height(np, hgt, strength):
    gy, gx = np.gradient(hgt)
    n = np.dstack([-gx * strength, -gy * strength, np.ones_like(hgt)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return np.dstack([n * .5 + .5, np.ones_like(hgt)])   # OpenGL convention (+Y up) like Poly Haven -> flipped on import

def painted_textures(res=512):
    """1 texture = 1 m (box UVs are 1 UV per metre). Greyscale albedo: the material instance tints it.
    T_Siding: 5 clapboards per metre, painted shadow under each lap + a thin ink line, faint brush grain.
    T_Roof: staggered shingles (4 rows / m) with painted gaps and per-tile value jitter."""
    import numpy as np
    os.makedirs(os.path.join(OUT, 'tex'), exist_ok=True)
    H = W = res; v = (np.arange(H) + .5) / H; u = (np.arange(W) + .5) / W
    # ---- siding
    nb = 5; t = (v * nb) % 1.0                       # 0 at the bottom edge of each board, 1 at its top
    lap = np.clip((t - .80) / .20, 0, 1) ** 1.5       # shadow cast by the board above onto the top of this one
    alb = .93 - .20 * lap
    alb = np.where(t < .035, .30, alb)                # ink line at the lap edge (painted, ~2 px at 512)
    alb = np.where((t >= .035) & (t < .07), .99, alb) # highlight on the board's lower lip
    A = np.repeat(alb[:, None], W, axis=1)
    grain = _noise(np, H, W, 64, 3)[:, :] * .5 + _noise(np, H, W, 8, 4) * .5
    A = A * (.95 + .07 * grain)
    # occasional butt joints (vertical seams), different per board
    rng = np.random.default_rng(11); bi = (v * nb).astype(int)
    for b in range(nb):
        x = rng.random(); rows = bi == b; col = int(x * W)
        A[rows, max(0, col - 1):col + 1] = .45
    hgt = np.repeat((1 - t)[:, None], W, axis=1) * .9
    _save_png('T_Siding_diff', np.dstack([A, A, A, np.ones_like(A)]))
    _save_png('T_Siding_nor', _normal_from_height(np, hgt, 6.0))
    # ---- roof shingles (rows along U, the ridge direction)
    nr = 4; tr = (v * nr) % 1.0; row = (v * nr).astype(int)
    R2 = np.zeros((H, W)); ntile = 3
    for r in range(nr):
        rows = row == r; off = .5 / ntile if r % 2 else 0.0
        tu = ((u + off) * ntile) % 1.0; ti = ((u + off) * ntile).astype(int) % ntile
        jit = np.random.default_rng(100 + r).random(ntile)[ti] * .14 - .07
        R2[rows] = (.80 + jit)[None, :]
        gap = (tu < .025) | (tu > .975)
        R2[np.ix_(rows, gap)] = .32
    edge = (tr < .06)
    R2 = R2 - .22 * np.repeat(np.clip(1 - tr / .35, 0, 1)[:, None] ** 2, W, axis=1)   # each row darker under the row above
    R2[edge, :] = .28
    R2 = R2 * (.94 + .1 * _noise(np, H, W, 32, 9))
    _save_png('T_Roof_diff', np.dstack([R2, R2, R2, np.ones_like(R2)]))
    print('painted textures written')

# ------------------------------------------------------------------ the town plan
TALL_GRASS = [(-44.0, -9.0, -29.0, 2.5), (-44.0, 10.0, -31.0, 18.0)]   # rectangles (x0, y0, x1, y1), metres
GATE = (-47.0, 6.0)                                                  # Route 1 gate on the west road
ROOMS = {'house': dict(c=(-15.0, -5.0), W=9.0, D=7.0, H=3.2, mesh='SM_Room_House'),
         'lab': dict(c=(0.0, -34.0), W=18.0, D=11.0, H=4.2, mesh='SM_Room_Lab')}

def _ue(x, y, z): return [round(x * 100, 1), round(-y * 100, 1), round(z * 100, 1)]
def _yaw(dx, dy): return round(math.degrees(math.atan2(-dy, dx)), 1)   # Blender facing direction -> Unreal yaw
def gameplay_data():
    """everything the C++ game needs to know about this map (Unreal cm / degrees) -> Content/PBX/Data/L_Town.json"""
    G = {}
    def spot(x, y, z=None, face=(0, 1)): return {'pos': _ue(x, y, height(x, y) if z is None else z), 'yaw': _yaw(*face)}
    hc, lc = ROOMS['house'], ROOMS['lab']; HZ = INTERIOR_Z
    def inside(r, lx, ly, face=(0, -1)): return spot(r['c'][0] + lx, r['c'][1] + ly, HZ, face)
    G['new_game'] = inside(hc, -1.6, -1.2, (1, 0))                  # wake up next to the bed
    G['doors'] = [
        {'id': 'house', 'label': 'Home', 'outside': spot(-15, .7, None, (0, 1)), 'inside': inside(hc, 0, hc['D'] / 2 - 1.2, (0, -1)),
         'out_door': _ue(-15, -1.45, height(-15, -1.45) + .5), 'in_door': _ue(hc['c'][0], hc['c'][1] + hc['D'] / 2 - .2, HZ)},
        {'id': 'lab', 'label': 'Pokébox Labs', 'outside': spot(0, -26.2, None, (0, 1)), 'inside': inside(lc, 0, lc['D'] / 2 - 1.3, (0, -1)),
         'out_door': _ue(0, -28.45, height(0, -28.45) + .5), 'in_door': _ue(lc['c'][0], lc['c'][1] + lc['D'] / 2 - .2, HZ)},
        {'id': 'rival', 'label': "Rho's house", 'locked': True, 'out_door': _ue(15, -1.45, height(15, -1.45) + .5)}]
    G['npcs'] = [
        {'id': 'mom', 'outfit': 'mom', 'hair_color': [0.3, 0.16, 0.08], 'name': 'Mum', 'body': 'f', 'hair': 'Hair_Buns', 'anim': 'Idle_Loop', **inside(hc, 2.2, 1.6, (-1, 0))},
        {'id': 'vale', 'outfit': 'vale', 'hair_color': [0.78, 0.78, 0.8], 'name': 'Dr. Vale', 'body': 'f', 'hair': 'Hair_Long', 'anim': 'Idle_FoldArms_Loop', **inside(lc, 0, -1.4, (0, 1))},
        {'id': 'aide', 'outfit': 'aide', 'hair_color': [0.25, 0.15, 0.08], 'name': 'Lab Aide Pim', 'body': 'm', 'hair': 'Hair_SimpleParted', 'anim': 'Idle_TalkingPhone_Loop', **inside(lc, 6.0, -2.9, (0, 1))},
        {'id': 'rho', 'outfit': 'rho', 'hair_color': [0.08, 0.1, 0.22], 'name': 'Rho', 'body': 'm', 'hair': 'Hair_Buzzed', 'anim': 'Idle_FoldArms_Loop', **spot(-12.6, 3.6, None, (-1, -.4))},
        {'id': 'fisher', 'outfit': 'fisher', 'hair_color': [0.65, 0.65, 0.65], 'name': 'Old Fisher Gus', 'body': 'm', 'hair': 'Hair_Beard', 'anim': 'Idle_Rail_Loop', **spot(9.0, 50.2, -.35 + .1, (0, 1))},
        {'id': 'gardener', 'outfit': 'gardener', 'hair_color': [0.55, 0.22, 0.08], 'name': 'Gardener Ines', 'body': 'f', 'hair': 'Hair_Buns', 'anim': 'Farm_Watering', **spot(19.5, .2, None, (1, 0))},
        {'id': 'merchant', 'outfit': 'merchant', 'hair_color': [0.05, 0.04, 0.04], 'name': 'Fruit Seller Dora', 'body': 'f', 'hair': 'Hair_BuzzedFemale', 'anim': 'Idle_Talking_Loop', **spot(-5.4, -19.6, None, (1, 0))},
        {'id': 'kid', 'outfit': 'kid', 'hair_color': [0.85, 0.62, 0.2], 'name': 'Little Leo', 'body': 'm', 'hair': 'Hair_Buzzed', 'anim': 'Idle_Loop', 'scale': .72, **spot(3.2, -17.6, None, (-1, -.3))},
        {'id': 'conductor', 'outfit': 'conductor', 'hair_color': [0.4, 0.38, 0.36], 'name': 'Conductor Mabel', 'body': 'f', 'hair': 'Hair_Buns', 'anim': 'Idle_Loop', **spot(36.6, 9.5, height(36.5, 9.5) + .55, (-1, 0))},
        {'id': 'guard', 'outfit': 'guard', 'hair_color': [0.06, 0.05, 0.05], 'name': 'Gate Warden Bo', 'body': 'm', 'hair': 'Hair_SimpleParted', 'anim': 'Idle_FoldArms_Loop', **spot(-44.6, 9.4, None, (1, 0))}]
    G['spots'] = {'rho_greet': spot(-12.6, 3.6, None, (-1, -.4)), 'rho_gate': spot(-42.5, 3.4, None, (1, .3)),
                  'starter_table': _ue(lc['c'][0], lc['c'][1] - 3.0, HZ + .95), 'bed': _ue(hc['c'][0] - 3.3, hc['c'][1] - 2.2, HZ + .5),
                  'battle_center_hint': _ue(-36, 6, 0), 'from_route1': spot(GATE[0] + 4.0, GATE[1], None, (1, 0))}
    G['grass'] = [{'min': _ue(x0, y1, 0)[:2], 'max': _ue(x1, y0, 0)[:2]} for (x0, y0, x1, y1) in TALL_GRASS]   # (y flips sign)
    G['wild_spawns'] = [_ue(x, y, height(x, y)) for (x, y) in [(-40, -5), (-33, -2), (-37, 14), (-41, 15.5), (-34, 1)]]
    G['gate'] = {'pos': _ue(GATE[0], GATE[1], height(*GATE)), 'exit_x': round((GATE[0] - 3.0) * 100, 1), 'barrier_mesh': 'fence-gate'}
    G['bounds'] = {'center': _ue(0, -8, 0)[:2], 'radius': 9000.0, 'water_z': -110.0, 'safe': spot(0, 10)}
    G['map'] = 'L_Town'; G['title'] = 'LUMEN HARBOR'
    # walking out through the (re-opened) Route 1 gate loads the Route 1 level; min_step 7 = EPBXStep::Gate (licence signed)
    G['exits'] = [{'id': 'route1', 'pos': _ue(GATE[0] - 3.2, GATE[1], height(GATE[0] - 3.2, GATE[1])), 'radius': 260.0, 'to_map': 'L_Route1', 'to_spot': 'from_lumen',
                   'min_step': 7, 'label': 'Route 1'}]
    G['signs'] = [{'pos': _ue(GATE[0] + 2.5, GATE[1] + 3.6, height(GATE[0] + 2.5, GATE[1] + 3.6) + 1.15), 'yaw': _yaw(1, 0), 'text': 'ROUTE 1\nwest to Mistvale'},
                  {'pos': _ue(4, 9, height(4, 9) + 1.15), 'yaw': _yaw(0, 1), 'text': 'LUMEN HARBOR'},
                  {'pos': _ue(-4, -20, height(-4, -20) + 1.15), 'yaw': _yaw(0, 1), 'text': 'POKEBOX LABS'},
                  {'pos': _ue(26.5, 9.2, height(26.5, 9.2) + 1.15), 'yaw': _yaw(0, 1), 'text': 'LUMEN STATION\ntrains to Mistvale'}]
    # railway: where you board, which way the train leaves (north = Unreal +Y) and where it disappears (the tunnel)
    pz = height(36.5, 1.0) + .55
    G['train'] = {'board': spot(37.6, 1.0, pz, (1, 0)), 'dir': [0.0, 1.0, 0.0], 'exit_y': round(-(TRACK_Y0 - 6) * 100, 1),
                  'cam': {'pos': _ue(31.0, -26.0, 7.0), 'yaw': _yaw(TRACK_X - 31.0, 2.0 + 26.0)}}
    return G

# Fab packs in the Unreal project (mesh paths are used as-is by pbx_build)
NAT = '/Game/Stylized_PBR_Nature/Foliage/Assets/'; RCK = '/Game/Stylized_PBR_Nature/Rocks/Assets/'
SHX = '/Game/StyleHex_Studio/Free_Packs/FREE_Stylized_Forest_Sample/Meshes/'; GFP = '/Game/StylizedGrassFlowersPack/StaticMesh/'
DSC = '/Game/DreamscapeSeries/DreamscapeTower/Meshes/'; GRV = '/Game/StylizedGravestones/Meshes/Gravetombs_UE5_Gravestone_0'
TREES_TOWN = [SHX + 'Trees/SM_Tree_Broadleaf_1', SHX + 'Trees/SM_Tree_Broadleaf_2', SHX + 'Trees/SM_Tree_Birch_1', SHX + 'Trees/SM_Tree_Birch_2']
TREES_FOREST = [NAT + f'SM_Common_Tree_{i:02d}' for i in (1, 2, 3, 6, 8, 9, 10, 11)] + [NAT + 'SM_Pine_Tree_1', NAT + 'SM_Pine_Tree_2']
BUSHES = [NAT + 'SM_Bush', SHX + 'Foliage/SM_Fol_Bush_1', SHX + 'Foliage/SM_Fol_Bush_2']
GRASS = [SHX + f'Foliage/SM_Fol_Grass_Clump_{i}' for i in (1, 2, 3, 4, 5)] + [GFP + 'SM_Grass_a', GFP + 'SM_Grass_b']
FLOWERS = [GFP + n for n in ('SM_Flower_Bell_Blue_a', 'SM_Flower_Bell_Blue_b', 'SM_Flower_Cluster_Pink_a', 'SM_Flower_Cluster_Pink_b', 'SM_Flower_Daisy_White_a',
                             'SM_Flower_Daisy_White_c', 'SM_Flower_Daisy_White_e', 'SM_Flower_Spike_Orange_a', 'SM_Flower_Spike_Orange_b')]
ROCKS_S = [RCK + f'SM_R_Rock_0{i}' for i in range(1, 6)]
ROCKS_L = [RCK + f'SM_S_Rock_{i:02d}' for i in (2, 4, 5, 6, 8, 9, 10)]
CLIFFS = [DSC + f'Stones/Cliffs/SM_Cliff_0{i}' for i in range(1, 8)]
FENCES = [DSC + f'Structures/SM_Fence_0{i}' for i in (1, 2, 3, 4)]

def plan_town():
    P = {'paths': [(0, -24, 0, 48, 3.6), (-24, 6, 24, 6, 3.0), (-15, 6, -15, 0, 2.2), (15, 6, 15, 0, 2.2), (-24, 6, -52, 6, 3.0),
                   (24, 6, 34.4, 6, 3.0), (30, 6, 30, .8, 2.2)],
         'objects': []}
    def add(mesh, x, y, rot=0.0, s=1.0, z=None):
        # snap = sits on the outdoor ground: Unreal re-measures the real ground under its footprint (no floating / sinking)
        P['objects'].append(dict(mesh=mesh, x=round(x, 3), y=round(y, 3), z=round(height(x, y) if z is None else z, 3), rot=round(rot, 2), s=round(s, 3), snap=z is None))
    add('SM_House_Player', -15, -5, 180); add('SM_House_Rival', 15, -5, 180); add('SM_Lab', 0, -34, 180)  # fronts face the village street (+y)
    add('SM_Mailbox', -12.3, 2.2, 90); add('SM_Mailbox', 17.7, 2.2, 90)
    add('SM_Sign', 4, 9, 0); add('SM_Sign', -4, -20, 0); add('SM_Sign', 26.5, 9.2, 0)
    for x in (-6, 6):
        for y in (-12, 14, 30): add('SM_LampPost', x * .55, y)
    for x in (12, 21, 29): add('SM_LampPost', x, 8.2)
    add('SM_Bench', 8, -18, 180); add('SM_Bin', 10, -18)
    # ---- railway: station building, platform, track from the tunnel in the north to the buffer stop, the train at the platform
    add('SM_Station', 29.5, -2.2, 180)
    x0, x1, y0, y1 = PLATFORM; add('SM_Platform', (x0 + x1) / 2, (y0 + y1) / 2, 0)
    add('SM_Track', TRACK_X, (TRACK_Y0 + TRACK_Y1) / 2, 0, z=0.0)
    add('SM_Tunnel', TRACK_X, TRACK_Y0, 0, z=0.0)
    for (m, y) in (('SM_TrainLoco', -9.0), ('SM_TrainCar', 1.0), ('SM_TrainCar', 13.2)):
        add(m, TRACK_X, y, 0, z=.40); P['objects'][-1]['tag'] = 'PBX_Train'
    # ---- garden fences (Dreamscape fence panels, 3.3 m) around the two houses
    for cx in (-15, 15):
        for k in (-2, -1, 1, 2):
            add(R.choice(FENCES), cx + k * 3.3 + (-.9 if k < 0 else .9), 3.0, 0, .98)
        for k in range(3): add(R.choice(FENCES), cx - 7.4 * (1 if cx < 0 else -1), 1.4 - k * 3.3 - 1.6, 90, .98)
    for k in range(6): add(R.choice(FENCES), 8.6 + k * 3.3, 22, 0); add(R.choice(FENCES), -8.6 - k * 3.3, 22, 0)
    # ---- nature (Fab packs), kept off paths, houses, the railway and the beach
    blocked = [(-15, -5, 8.5), (15, -5, 8.5), (0, -34, 13), (-47, 6, 7), (29.5, -2.2, 7), (0, -20.5, 4.5), (-32, -38, 8)]
    def in_grass(x, y, pad=0.0): return any(x0 - pad < x < x1 + pad and y0 - pad < y < y1 + pad for (x0, y0, x1, y1) in TALL_GRASS)
    def railway(x, y, pad=0.0): return (abs(x - TRACK_X) < 7 + pad and y < TRACK_Y1 + 3) or (PLATFORM[0] - 3 - pad < x < 46 and PLATFORM[2] - 3 < y < PLATFORM[3] + 3)
    def free(x, y, r=1.5, far=False):
        if path_mask(x, y, P) > .05: return False
        if in_grass(x, y, r + .5) or railway(x, y, r): return False
        if y > 38: return False
        if not far and (abs(x) > 104 or abs(y) > 104): return False
        return all(math.hypot(x - bx, y - by) > br + r for bx, by, br in blocked)
    n = 0
    while n < 190:                       # forest ring around the village
        a = R.random() * math.tau; d = 46 + R.random() * 55; x, y = math.cos(a) * d, math.sin(a) * d - 10
        if y > 34 or not free(x, y, 2.5): continue
        add(R.choice(TREES_FOREST), x, y, R.random() * 360, .8 + R.random() * .35); n += 1
    n = 0
    while n < 170:                       # far forest on the hills in front of the mountains (outside the town square)
        a = R.random() * math.tau; d = 108 + R.random() * 70; x, y = math.cos(a) * d, math.sin(a) * d - 10
        if y > 30 or not free(x, y, 4, far=True): continue
        add(R.choice(TREES_FOREST), x, y, R.random() * 360, 1.0 + R.random() * .5); n += 1
    # mountain dressing: pines up the green lower slopes, boulders and cliffs higher up (they snap onto the mountain mesh)
    for k_, (cx, cy, rad, hgt) in enumerate(mountain_peaks()):
        if hgt < 45 and R.random() < .5: continue
        for j in range(5 if hgt > 45 else 3):
            a = R.random() * math.tau; x0 = R.random()
            if math.hypot(cx + math.cos(a) * rad * .8, cy + math.sin(a) * rad * .8 + 10) < 112: continue
            if x0 < .6:   # pines on the lower, green half of the slope
                d = rad * R.uniform(.6, .92); x, y = cx + math.cos(a) * d, cy + math.sin(a) * d
                if railway(x, y, 6): continue
                add(R.choice([NAT + 'SM_Pine_Tree_1', NAT + 'SM_Pine_Tree_2']), x, y, R.random() * 360, 1.6 + R.random())
            else:         # boulders / cliffs only near the foot (never perched on a peak)
                d = rad * R.uniform(.8, .97); x, y = cx + math.cos(a) * d, cy + math.sin(a) * d
                if railway(x, y, 6): continue
                add(R.choice(ROCKS_L + CLIFFS), x, y, R.random() * 360, 1.2 + R.random() * .8)
    for x, y in [(-27, -14), (-26, 4), (27, -14), (-11, -42), (11, -43), (-22, 16), (23, 17), (-31, 30), (32, 30), (8, 30)]:
        add(R.choice(TREES_TOWN), x, y, R.random() * 360, .62 + R.random() * .12)      # big feature trees in the village
    n = 0
    while n < 150:                       # bushes
        x, y = (R.random() - .5) * 100, (R.random() - .5) * 92 - 6
        if not free(x, y, 1.2): continue
        add(R.choice(BUSHES), x, y, R.random() * 360, .65 + R.random() * .45); n += 1
    n = 0
    while n < 420:                       # grass clumps + flowers carpet
        x, y = (R.random() - .5) * 110, (R.random() - .5) * 96 - 8
        if not free(x, y, .35): continue
        k = R.random()
        if k < .62: add(R.choice(GRASS), x, y, R.random() * 360, .9 + R.random() * .6)
        elif k < .9: add(R.choice(FLOWERS), x, y, R.random() * 360, .8 + R.random() * .5)
        else: add(NAT + 'SM_Fern', x, y, R.random() * 360, .7 + R.random() * .4)
        n += 1
    for cx in (-15, 15):                 # flower beds in the front gardens
        for k in range(18): add(R.choice(FLOWERS), cx + (R.random() - .5) * 12, 0.6 + R.random() * 1.6, R.random() * 360, .9)
    for k in range(26):                  # small rocks along the paths and at the forest edge
        a = R.random() * math.tau; d = 34 + R.random() * 30; x, y = math.cos(a) * d, math.sin(a) * d - 10
        if not free(x, y, 1.0): continue
        add(R.choice(ROCKS_S), x, y, R.random() * 360, .22 + R.random() * .2)
    for k in range(14):                  # cliffs and big rocks on the hill rim (north, west, east)
        a = math.radians(-180 + 180 * k / 13 + R.uniform(-4, 4)); d = 88 + R.random() * 14; x, y = math.cos(a) * d, math.sin(a) * d - 10
        if not free(x, y, 3): continue
        add(R.choice(CLIFFS + ROCKS_L), x, y, R.random() * 360, .7 + R.random() * .5)
    # ---- kit props (Quaternius Fantasy Props = QProps/, Kenney kits = KTown/ KPirate/ KSurvival/). h / w = target
    # height / footprint in metres; Unreal scales each mesh from its bounds, so the kits' differing units don't matter.
    def kit(mesh, x, y, rot=0.0, h=None, w=None, z=None):
        add(mesh, x, y, rot, 1.0, z); o = P['objects'][-1]
        if h: o['h'] = h
        if w: o['w'] = w
    # plaza in front of the lab: the town's Relay Stone (Lattice storage relay) on a paved circle + a small market
    kit(DSC + 'Structures/SM_Floor_03', 0, -20.5, 0, w=4.6)
    kit(DSC + 'Stones/SM_RuneStone_02', 0, -20.5, 25, h=3.8)
    kit('QProps/Stall_Empty', -6.8, -19.5, 90, h=2.6); kit('QProps/Stall_Cart_Empty', 6.8, -23.5, -90, h=2.1)
    for (m, x, y, r, h) in [('QProps/FarmCrate_Apple', -5.4, -21.4, 10, .45), ('QProps/FarmCrate_Carrot', -5.6, -17.8, -8, .45),
                            ('QProps/Barrel_Apples', -7.9, -22.0, 0, .95), ('QProps/Crate_Wooden', 5.3, -25.4, 15, .7),
                            ('QProps/Barrel', 8.3, -25.6, 0, 1.0), ('KTown/cart', 9.6, -21.5, 70, 1.4)]:
        kit(m, x, y, r, h=h)
    kit('QProps/Crate_Wooden', 5.3, -25.4, 40, h=.7, z=height(5.3, -25.4) + .7)          # stacked crate
    # lab flanked by bushes
    for s_ in (-1, 1):
        for k in range(4): add(R.choice(BUSHES[1:]), s_ * 10.8, -29.5 - k * 2.2, R.random() * 360, .85)
    # homes: barrels, buckets, flower pots, wood pile
    for (m, x, y, r, h) in [('QProps/Barrel', -20.2, -2.6, 0, 1.0), ('QProps/Bucket_Wooden_1', -19.4, -1.9, 0, .4), ('QProps/Pot_1', -16.9, -.9, 0, .5),
                            ('QProps/Pot_1', -13.1, -.9, 0, .5), ('QProps/Barrel', 20.3, -2.4, 0, 1.0), ('QProps/Barrel', 20.4, -3.6, 30, 1.0),
                            ('QProps/Crate_Wooden', 19.6, -1.5, 12, .7), ('QProps/Pot_1', 13.1, -.9, 0, .5), ('QProps/Pot_1', 16.9, -.9, 0, .5),
                            ('KSurvival/resource_wood', -21.0, -7.0, 90, .6), ('QProps/Workbench', 21.0, -8.0, -90, 1.0)]:
        kit(m, x, y, r, h=h)
    # station: luggage, benches on the forecourt
    for (m, x, y, r, h) in [('QProps/Crate_Wooden', 33.2, -6.2, 10, .6), ('QProps/Barrel', 33.6, -7.4, 0, .9), ('SM_Bench', 26.0, 1.6, 180, None)]:
        kit(m, x, y, r, h=h)
    # path ends: signposts towards the routes
    kit('KSurvival/signpost', -23.0, 8.2, 90, h=2.0); kit('KSurvival/signpost', 2.6, 40.0, 0, h=2.0)
    # memorial garden on the north-west hill: five old gravestones inside a ruined wall
    for i, (dx, dy) in enumerate([(-2.6, -1.2), (0, -1.6), (2.6, -1.2), (-1.3, 1.6), (1.3, 1.6)]):
        kit(GRV + str(i + 1), -32 + dx, -38 + dy, 180 + R.uniform(-6, 6), h=1.1 + R.random() * .5)
    for (dx, dy, r) in [(-4.6, 0, 90), (4.6, 0, 90), (-2.2, -4.2, 0), (2.2, -4.2, 0), (-2.6, 4.0, 0)]:
        kit(DSC + R.choice(['Structures/SM_Wall_Ruin_01', 'Structures/SM_Wall_Ruin_02', 'Structures/SM_Wall_Ruin_03_Final']), -32 + dx, -38 + dy, r, h=1.1)
    # beach: wooden pier, row boats, campfire with log seats, rocks
    kit('KPirate/structure_platform_dock', 9.0, 47.8, 0, w=6.0, z=-.35); kit('KPirate/structure_platform_dock', 9.0, 53.6, 0, w=6.0, z=-.35)
    kit('KPirate/boat_row_small', 13.5, 52.0, 25, w=3.2, z=-1.15); kit('KPirate/boat_row_large', -9.0, 46.2, -60, w=4.2)
    kit('KSurvival/campfire_pit', -15.0, 42.5, 0, w=1.4)
    for a in (0, 120, 240):
        kit('KSurvival/tree_log_small', -15.0 + 1.8 * math.cos(math.radians(a)), 42.5 + 1.8 * math.sin(math.radians(a)), a + 90, w=1.6)
    for (m, x, y, sc) in [(ROCKS_L[0], -27, 47, .45), (ROCKS_S[2], 22, 45, .5), (ROCKS_L[3], 31, 50, .5), (ROCKS_S[0], -35, 44, .55), (ROCKS_L[5], 44, 47, .6), (ROCKS_L[1], -48, 46, .55)]:
        add(m, x, y, R.random() * 360, sc)
    # ---- west road: tall grass where the wild Echoes live, and the Route 1 gate (closed: landslide — the train is the way out)
    for (x0, y0, x1, y1) in TALL_GRASS:
        n = int((x1 - x0) * (y1 - y0) * .55)
        for k in range(n):
            x, y = x0 + R.random() * (x1 - x0), y0 + R.random() * (y1 - y0)
            add(NAT + 'SM_Grass', x, y, R.random() * 360, .85 + R.random() * .4)
    gx, gy = GATE
    for s_ in (-1, 1): kit('KTown/pillar-stone', gx, gy + s_ * 2.3, 0, h=3.2)
    kit('KTown/fence-gate', gx, gy, 90, w=4.0)                         # the barrier
    P['objects'][-1]['tag'] = 'PBX_GateBarrier'
    for (dx, dy, sc) in [(-3.5, 0, .55), (-6, 2, .45)]:                 # the landslide behind the gate (cleared once the licence is signed)
        add(R.choice(ROCKS_L), gx + dx, gy + dy, R.random() * 360, sc); P['objects'][-1]['tag'] = 'PBX_GateBarrier'
    add('SM_Sign', gx + 2.5, gy + 3.6, 90)
    for k in range(6):                                                  # bushes either side of the gate so the road is the only way out
        for sgn in (1, -1): add(R.choice(BUSHES), gx + R.uniform(-.4, .4), gy + sgn * (3.6 + k * 2.0), R.random() * 360, .9)
    # ---- interiors (60 m below their buildings). Furniture: Kenney Furniture Kit, footprints in metres
    def furn(room, mesh, lx, ly, rot=0.0, h=None, w=None, dz=0.0):
        cx, cy = ROOMS[room]['c']; kit(mesh, cx + lx, cy + ly, rot, h=h, w=w, z=INTERIOR_Z + dz)
    for room, r in ROOMS.items(): add(r['mesh'], r['c'][0], r['c'][1], 0, 1.0, INTERIOR_Z)
    F = 'KFurniture/'
    for (m, lx, ly, rot, h, w, dz) in [
        (F + 'bedSingle', -3.3, -2.2, 0, None, 2.1, 0), (F + 'sideTable', -1.9, -3.0, 0, .55, None, 0), (F + 'lampRoundTable', -1.9, -3.0, 0, .5, None, .55),
        (F + 'bookcaseOpen', .3, -3.15, 0, 1.9, None, 0), (F + 'books', .3, -3.1, 0, None, .5, 1.0),
        (F + 'desk', 2.8, -3.0, 0, None, 1.4, 0), (F + 'computerScreen', 2.8, -3.15, 0, .45, None, .76), (F + 'chairDesk', 2.8, -2.1, 180, 1.0, None, 0),
        (F + 'tableRound', 2.6, .6, 0, None, 1.1, 0), (F + 'chair', 1.8, .6, 90, .95, None, 0), (F + 'chair', 3.4, .6, -90, .95, None, 0),
        (F + 'loungeSofa', -3.7, .9, 90, None, 2.0, 0), (F + 'rugRectangle', -.6, -.2, 0, None, 3.2, 0), (F + 'tableCoffee', -2.2, .9, 0, None, 1.0, 0),
        (F + 'pottedPlant', 4.0, 2.9, 0, 1.1, None, 0), (F + 'pottedPlant', -4.0, -3.0, 0, 1.1, None, 0), (F + 'coatRackStanding', 1.6, 3.0, 0, 1.8, None, 0),
        (F + 'rugDoormat', 0, 2.95, 0, None, 1.1, 0), (F + 'kitchenCabinet', -2.9, 3.0, 180, .9, None, 0), (F + 'kitchenStove', -3.9, 3.0, 180, .9, None, 0),
        (F + 'kitchenFridge', -1.8, 3.05, 180, 1.9, None, 0), (F + 'radio', 2.6, .6, 30, .25, None, .75)]:
        furn('house', m, lx, ly, rot, h, w, dz)
    for (m, lx, ly, rot, h, w, dz) in [
        ('QProps/Table_Large', 0, -3.0, 0, None, 2.6, 0),
        (F + 'desk', -6.0, -4.6, 0, None, 1.6, 0), (F + 'computerScreen', -6.0, -4.8, 0, .5, None, .76), (F + 'chairDesk', -6.0, -3.7, 180, 1.0, None, 0),
        (F + 'desk', 6.0, -4.6, 0, None, 1.6, 0), (F + 'computerScreen', 6.0, -4.8, 0, .5, None, .76), (F + 'laptop', 5.5, -4.5, 0, None, .4, .76),
        (F + 'chairDesk', 6.0, -3.7, 180, 1.0, None, 0),
        (F + 'bookcaseClosedWide', -8.6, -2.5, 90, 2.2, None, 0), (F + 'bookcaseClosedWide', -8.6, .5, 90, 2.2, None, 0), (F + 'bookcaseClosedWide', -8.6, 3.5, 90, 2.2, None, 0),
        (F + 'cabinetTelevision', 8.6, -1.5, -90, .7, None, 0), (F + 'televisionModern', 8.6, -1.5, -90, .9, None, .7),
        (F + 'loungeSofaLong', 8.4, 2.5, -90, None, 2.6, 0), (F + 'tableCoffeeGlass', 7.2, 2.5, 0, None, 1.0, 0),
        (F + 'rugRectangle', 0, -.5, 0, None, 6.0, 0), (F + 'pottedPlant', -8.5, 5.0, 0, 1.3, None, 0), (F + 'pottedPlant', 8.5, 5.0, 0, 1.3, None, 0),
        (F + 'pottedPlant', -8.5, -5.0, 0, 1.3, None, 0), (F + 'pottedPlant', 8.5, -5.0, 0, 1.3, None, 0), (F + 'rugDoormat', 0, 5.2, 0, None, 1.2, 0),
        ('QProps/Shelf_Small_Bottles', -3.2, -5.2, 0, 1.2, None, 0), ('QProps/BookStand', 3.2, -5.1, 0, 1.3, None, 0), ('QProps/Cauldron', 3.6, 1.5, 0, .8, None, 0)]:
        furn('lab', m, lx, ly, rot, h, w, dz)
    P['rooms'] = [dict(c=_ue(r['c'][0], r['c'][1], INTERIOR_Z), W=r['W'] * 100, D=r['D'] * 100, H=r['H'] * 100) for r in ROOMS.values()]
    P['gameplay'] = gameplay_data()
    P['water'] = dict(x=0, y=380, z=-1.2)
    P['player_start'] = dict(x=0, y=10, z=height(0, 10) + 1.0, rot=-90)
    return P

def run():
    reset()
    plan = plan_town()
    export(house('SM_House_Player', 9.0, 7.0, 3.3, 'M_Roof_Red', 'M_Siding_White'), 'SM_House_Player'); reset()
    export(house('SM_House_Rival', 9.5, 7.2, 3.3, 'M_Roof_Red', 'M_Siding_Cream'), 'SM_House_Rival'); reset()
    export(house('SM_Lab', 18.0, 11.0, 6.4, 'M_Roof_Blue', 'M_Siding_White', porch=False, chimney=False, two_storey=True, lab=True), 'SM_Lab'); reset()
    for f in (fence_segment, lamp_post, mailbox, signboard, bench, trash_bin, station_building, platform, track, tunnel_portal, loco, carriage):
        ob = f(); export(ob, ob.name); reset()
    ground_far(); reset(); mountains(); reset(); sky_dome(); reset()
    water_plane(); reset()
    echo_card(); reset()
    for r in ROOMS.values():
        export(room(r['mesh'], r['W'], r['D'], r['H'], 'M_Wallpaper_Home' if r['mesh'] == 'SM_Room_House' else 'M_Wallpaper_Lab'), r['mesh']); reset()
    painted_textures()
    ground(plan); reset(); splat(plan)
    with open(os.path.join(OUT, 'town_plan.json'), 'w') as fh: json.dump(plan, fh, indent=1)
    gd = os.environ.get('PBX_GAMEDATA', os.path.join(os.path.dirname(OUT), 'PokeboxNext', 'Content', 'PBX', 'Data'))
    os.makedirs(gd, exist_ok=True)
    with open(os.path.join(gd, 'L_Town.json'), 'w', encoding='utf-8') as fh: json.dump(plan['gameplay'], fh, indent=1, ensure_ascii=False)
    print('town built:', len(plan['objects']), 'placements')

if os.environ.get('PBX_TOWN_NORUN') != '1':   # blender_route1.py imports this file for its helpers without rebuilding the town
    run()
