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
# new village houses (2026-10-22): (blueprint, door x, door y, facing) — doors open onto the new side paths
NEW_HOUSES = [(12, 6.2, 15.5, (-1, 0)), (8, 5.8, 31.0, (-1, 0)), (11, -6.2, 15.0, (1, 0)), (7, 22.0, -15.0, (0, 1)), (1, -11.1, -16.2, (1, 0))]
NEW_HOUSE_BLOCKS = [(11.2, 14.2, 9.5), (9.9, 30.8, 10.5), (-10.7, 15.7, 10.0), (21.9, -22.8, 11.0), (-15.3, -16.2, 6.5)]
PADS = [(9.9, 30.8, 11.0), (-85.0, -80.8, 7.0), (95.0, -72.8, 7.0), (92.0, -30.8, 7.0)]   # levelled ground: harbour inn, the windmills
# 2026-10-23 (phase 2): seven more houses — a harbour lane in the south-west, a farm hamlet across the stream in the east
# (reached over a stone bridge), two cottages behind the lab — and three more windmills, two of them at the mountains' foot
NEW_HOUSES2 = [(2, -14.0, 33.5, (0, 1)), (10, -30.0, 33.5, (0, 1)), (4, 68.0, 0.0, (-1, 0)), (12, 68.0, -22.0, (-1, 0)),
               (2, 82.0, 14.0, (0, -1)), (1, -13.0, -46.0, (0, 1)), (11, 14.0, -44.0, (0, 1))]
NEW_HOUSE_BLOCKS2 = [(-14, 29.3, 7.0), (-30.3, 31, 6.5), (72, .4, 11.5), (73, -23.3, 10.5), (82, 17, 6.5), (-13, -50.3, 6.5), (13.3, -48.5, 9.5)]
WINDMILLS = [(-85.0, -78.0), (95.0, -70.0), (92.0, -28.0)]
# the Lamplighters' Path: from behind the memorial garden up the north-western slope to the old Rest (a clearing with the
# keepers' graves) and on to the cairn on the ridge. The only way up; beyond the cairn the forest closes.
TRAIL = [(-36, -46), (-48, -62), (-62, -82), (-78, -106), (-92, -132), (-95, -150), (-90, -165), (-80, -182), (-68, -198), (-60, -208)]
REST = (-90.0, -165.0)
def trail_dist(x, y):
    best = 1e9
    for (ax, ay), (bx, by) in zip(TRAIL[:-1], TRAIL[1:]):
        dx, dy = bx - ax, by - ay; L2 = dx * dx + dy * dy
        u = max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / L2)); best = min(best, math.hypot(x - ax - dx * u, y - ay - dy * u))
    return best
# carved wooden signs (3D lettering on the board) and notes / grave inscriptions (read with E) — a small story off the
# main game: the keepers of the old harbour lamp, and the storm night Ansel Vorn took the lamp up to the ridge
LORE_SIGNS = [((-38.5, -49.0), (-1, 1), "LAMPLIGHTERS' PATH\nup to the old Rest\nmind the roots"),
              ((-79.5, -103.0), (1, 1), "'Light the lamp,\nthen come home.'\n— carved by A.V."),
              ((-84.0, -158.0), (1, 1), "HERE REST THE KEEPERS\nOF THE HARBOUR LAMP"),
              ((-63.0, -203.0), (0, 1), "Beyond the cairn\nthe forest closes.\nNo keeper went further.")]
LORE_NOTES = [((-93.5, -161.5), "Ledger of the Lamplighters' Rest. Oil: 12 casks. Wicks: 40. The lighthouse on the island is finished. After tonight the lamp up here goes dark for good."),
              ((-96.5, -166.0), "Ansel's note: The storm came early and Mara's boat is still out past the island. I am taking the lamp up to the ridge so she can see the shore. If you find this, keep a light in the window."),
              ((-88.5, -170.5), "ANSEL VORN — Keeper of the Harbour Lamp. He lit the way."),
              ((-91.5, -171.0), "MARA VORN — Fisher. She came home."),
              ((-85.5, -169.5), "The first keepers. Their names are worn away; someone still leaves pebbles on the stone."),
              ((-61.0, -206.0), "A torn page wedged under the cairn: '...his Echo card was never found. Fishers say a small light still moves between the pines on stormy nights...'")]


def height_raw(x, y):
    """flat village plateau, soft hills inland, slope down to the beach on the south (+y)"""
    h = 0.0
    h += .35 * math.sin(x * .07) * math.cos(y * .05) + .25 * math.sin(x * .13 + 1.3) * math.sin(y * .11 + .4)
    d = math.hypot(x, y + 10)
    h *= min(1, max(0, (d - 30) / 25))              # village core stays flat
    for (px_, py_, pr_) in PADS: h *= min(1, max(0, (math.hypot(x - px_, y - py_) - pr_) / 6))
    ring = max(0, d - 70); h += ring * ring * .004 * (1 - min(1, max(0, (y - 25) / 20)))  # hills around (forest edge), not on the sea side
    if y > 42: h -= (y - 42) * .32                  # beach slope
    if y > 52: h -= (y - 52) * .25                  # under the sea
    if y > 44 and abs(x) < 60:                      # the harbour basin: a flat 3 m deep sandy floor inside the arms
        k = _ss(60, 45, abs(x)) * _ss(112, 96, y); h = h + (max(h, -3.0) - h) * k
    # railway: a flat bed (a cutting through the hills) from the station north to the tunnel in the mountains
    if TRACK_Y0 - 1.0 < y < 30:                     # (2026-10-23: only up to the portal — it used to cut a trench through the whole mountain)
        k = min(1, max(0, (abs(x - TRACK_X) - 4.0) / 7.0)); k = k * k * (3 - 2 * k)
        h = h * k
    return h

def height(x, y):
    """town ground height with the stream bed carved in (2026-10-23)"""
    return river_carve(x, y, height_raw(x, y))

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

def _arch_outline(w, h, n=18):
    """inner outline of the opening, bottom-right -> up -> over the half-round top -> down to bottom-left"""
    r = w / 2; pts = [(r, 0.0), (r, h)]
    for k in range(1, n): a = math.pi * k / n; pts.append((r * math.cos(a), h + r * math.sin(a)))
    pts += [(-r, h), (-r, 0.0)]; return pts

def tunnel_portal():
    """2026-10-23: a real railway tunnel. Stone headwall (18 x 11 m) with a cut-stone arch ring, coping, two flared wing
    walls retaining the cutting, and a 60 m stone-lined bore (it bends nothing: the far part fades into soot-black).
    The tunnel mountain (tunnel_bump) rises as a cliff right behind the headwall, so the bore is always under rock.
    Local -Y = into the mountain. Origin = rail level at the portal face."""
    import bmesh as _bm
    W, H = 5.6, 4.6; HW, HH, T = 18.0, 11.0, 1.6; P = []
    inner = _arch_outline(W, H); N = len(inner)
    # outer boundary walked the same way: right edge up, along the top, left edge down
    outer = []
    for k, (x, z) in enumerate(inner):
        f = k / (N - 1)                                   # 0 .. 1 along the path
        per = 2 * HH + HW; d = f * per
        if d < HH: outer.append((HW / 2, d))
        elif d < HH + HW: outer.append((HW / 2 - (d - HH), HH))
        else: outer.append((-HW / 2, HH - (d - HH - HW)))
    bm = _bm.new()
    def ring(y): return [bm.verts.new((x, y, z)) for (x, z) in inner], [bm.verts.new((x, y, z)) for (x, z) in outer]
    fi, fo = ring(0.0); bi, bo = ring(-T)
    for k in range(N - 1):
        bm.faces.new((fi[k], fo[k], fo[k + 1], fi[k + 1]))          # front face (towards the town, +y)
        bm.faces.new((bi[k + 1], bo[k + 1], bo[k], bi[k]))          # back face
        bm.faces.new((fi[k + 1], bi[k + 1], bi[k], fi[k]))          # intrados (inside the opening)
        bm.faces.new((fo[k], bo[k], bo[k + 1], fo[k + 1]))          # outer edges
    bm.faces.new((fo[0], fi[0], bi[0], bo[0])); bm.faces.new((fi[-1], fo[-1], bo[-1], bi[-1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)        # closed solid: outward normals
    hw = mesh_obj('tn_headwall', bm); set_mat(hw, 'M_Stone'); P.append(hw)
    # arch ring of voussoirs standing proud of the wall + keystone, piers' plinths, coping on top
    n = 13; r = W / 2 + .45
    for i in range(n):
        am = math.pi * (i + .5) / n
        ob = box(f'tn_v{i}', .95, .3, math.pi * r / n - .04, (0, 0, 0), 'M_Stone', bevel=.03)
        ob.rotation_euler = (0, -(am - math.pi / 2), 0); ob.location = (math.cos(am) * r, .15, H + math.sin(am) * r); P.append(ob)
    P.append(box('tn_key', .8, .45, 1.1, (0, .2, H + W / 2 + .05), 'M_Stone', bevel=.04))
    for s_ in (-1, 1): P.append(box(f'tn_plinth{s_}', 1.4, .45, 1.0, (s_ * (W / 2 + .7), .2, 0), 'M_Stone', bevel=.04))
    P.append(box('tn_coping', HW + .6, T + .5, .45, (0, -T / 2 + .1, HH), 'M_Stone', bevel=.05))
    # wing walls: flare out towards the town at 30 deg, 11 -> 2.5 m high over 11 m, retaining the cutting's slopes
    for s_ in (-1, 1):
        bm = _bm.new(); L = 11.0; th = 1.1
        ang = math.radians(30) * s_
        def pt(u, z, o):          # u along the wall (0 at the headwall), o across (0 = front face)
            x0, y0 = s_ * (HW / 2 - .4), 0.0
            dx, dy = math.sin(ang) * 1.0, math.cos(ang) * 1.0      # direction away from the headwall, towards the town
            return (x0 + dx * u + (-dy * s_) * o, y0 + dy * u + (dx * s_) * o, z)
        top = lambda u: HH - (HH - 2.5) * (u / L)
        vs = [bm.verts.new(pt(u, z, o)) for (u, z, o) in [(0, 0, 0), (L, 0, 0), (L, top(L), 0), (0, top(0), 0),
                                                            (0, 0, th), (L, 0, th), (L, top(L), th), (0, top(0), th)]]
        for f in ((0, 1, 2, 3), (5, 4, 7, 6), (4, 0, 3, 7), (1, 5, 6, 2), (3, 2, 6, 7), (4, 5, 1, 0)): bm.faces.new([vs[k] for k in f])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        ob = mesh_obj(f'tn_wing{s_}', bm); set_mat(ob, 'M_Stone'); P.append(ob)
    # the bore: the same arch profile swept 60 m into the mountain, faces pointing inwards; stone for 12 m, then soot-black
    for (y0, y1, m) in ((-T, -12.0, 'M_Stone'), (-12.0, -60.0, 'M_TunnelDark')):
        bm = _bm.new(); a = [bm.verts.new((x, y0, z)) for (x, z) in inner]; b = [bm.verts.new((x, y1, z)) for (x, z) in inner]
        for k in range(N - 1): bm.faces.new((b[k], b[k + 1], a[k + 1], a[k]))      # normals point into the bore
        bm.normal_update()
        ob = mesh_obj(f'tn_bore{y0}', bm); set_mat(ob, m); P.append(ob)
    P.append(box('tn_end', W + .4, .3, H + W / 2 + .3, (0, -60.2, 0), 'M_TunnelDark', bevel=0))
    P.append(box('tn_floor', W + .2, 60.4, .1, (0, -30.05, -.02), 'M_Gravel', bevel=0))   # from just in front of the face
    for s_ in (-1, 1): P.append(box(f'tn_rail{s_}', .09, 58.0, .14, (s_ * .72, -31.0, .26), 'M_Metal', bevel=0))
    for k in range(29): P.append(box(f'tn_sleeper{k}', 2.4, .25, .12, (0, -3.0 - k * 2.0, .08), 'M_WoodDark', bevel=0))
    return join(P, 'SM_Tunnel')

def _body_shell(name, L, W, H, z0, m, nose=0.0, seg=10):
    """a rail-vehicle body: straight sides with a slight tumblehome, an arched roof, closed ends. Length along local Y.
    nose > 0 rounds the plan of both ends (locomotive cabs). Origin: centre, z0 = floor level above rail top."""
    prof = [(W / 2 - .04, 0.0), (W / 2, .35), (W / 2, H - .55)]
    for k in range(1, seg):
        a = math.pi / 2 * k / seg; prof.append((W / 2 - .55 * (1 - math.cos(a)) * 1.0 - (W / 2 - .6) * (1 - math.cos(a)) ** 3 * 0, H - .55 + .55 * math.sin(a)))
    prof.append((W / 2 - .6, H)); prof += [(-x, z) for (x, z) in reversed(prof)]
    rows = []; N = 24
    bm = bmesh.new()
    for r in range(N + 1):
        y = -L / 2 + L * r / N; e = min(1, (L / 2 - abs(y)) / max(nose, 1e-3)) if nose > 0 else 1.0
        sc = .78 + .22 * math.sqrt(max(0, e)) if nose > 0 else 1.0
        rows.append([bm.verts.new((x * sc, y, z0 + z)) for (x, z) in prof])
    n = len(prof)
    for r in range(N):
        for q in range(n - 1): bm.faces.new((rows[r][q], rows[r][q + 1], rows[r + 1][q + 1], rows[r + 1][q]))
    for r in (0, N): bm.faces.new(rows[r] if r == 0 else list(reversed(rows[r])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = mesh_obj(name, bm); set_mat(ob, m)
    return ob

def _bogie(P, tag, y, z0, wheel_r=.5, base=2.6):
    """two axles; the wheels stand ON the rail top (local z = 0)"""
    P.append(box(f'{tag}_frame', 2.2, base + 1.2, .4, (0, y, wheel_r + .05), 'M_Iron', bevel=.04))
    for s_ in (-1, 1):
        P.append(box(f'{tag}_side{s_}', .18, base + 1.6, .55, (s_ * 1.0, y, wheel_r - .3), 'M_Iron', bevel=.03))
        for a in (-base / 2, base / 2):
            P.append(cyl(f'{tag}_w{s_}{a}', wheel_r, .14, (s_ * .74, y + a, wheel_r), 'M_Metal', rot=(0, math.pi / 2, 0), seg=20))
            P.append(cyl(f'{tag}_ab{s_}{a}', .17, .3, (s_ * 1.12, y + a, wheel_r), 'M_Iron', rot=(0, math.pi / 2, 0), seg=10))
            P.append(cyl(f'{tag}_sp{s_}{a}', .13, .35, (s_ * 1.0, y + a, wheel_r + .2), 'M_Metal', seg=8))

def loco():
    """2026-10-23: a realistic Swiss-style electric locomotive (Re 4/4 II proportions): 15 m red body with rounded cab
    ends, wrap-around windscreens, louvre bands, two pantographs and roof insulators, two 2-axle bogies, buffers,
    headlights. Front towards local -Y (north). Origin: rail top, centre."""
    P = []; L, W, H, zf = 14.8, 2.95, 2.75, 1.25
    P.append(_body_shell('lo_body', L, W, H, zf, 'M_TrainRed', nose=1.6))
    P.append(box('lo_under', 2.6, L - 1.2, .55, (0, 0, zf - .55), 'M_Iron', bevel=.03))
    for k, yy in enumerate((-3.8, -1.3, 1.3, 3.8)): P.append(box(f'lo_tank{k}', 2.1, 1.6, .45, (0, yy, zf - .95), 'M_Iron', bevel=.06))
    for yb in (-L / 2 + 3.3, L / 2 - 3.3): _bogie(P, f'lo_b{yb}', yb, .32, wheel_r=.62, base=2.6)
    for e in (-1, 1):                       # cab ends: windscreens, lights, buffers, coupler, handrails
        ye = e * (L / 2 - .05)
        for s_ in (-1, 1): P.append(box(f'lo_ws{e}{s_}', 1.15, .06, .95, (s_ * .62, ye + e * .02, zf + 1.45), 'M_Glass', rot=(math.radians(-12 * e), 0, math.radians(8 * s_ * e)), bevel=0))
        P.append(box(f'lo_ws_mid{e}', .08, .08, .95, (0, ye + e * .05, zf + 1.45), 'M_Iron', bevel=0))
        for s_ in (-1, 1): P.append(cyl(f'lo_hl{e}{s_}', .13, .08, (s_ * .95, ye + e * .05, zf + .45), 'M_LampGlass', rot=(math.pi / 2, 0, 0), seg=12))
        P.append(cyl(f'lo_hlt{e}', .12, .08, (0, ye + e * .03, zf + 2.55), 'M_LampGlass', rot=(math.pi / 2, 0, 0), seg=12))
        P.append(box(f'lo_beam{e}', 2.8, .3, .55, (0, ye + e * .12, zf - .55), 'M_Iron', bevel=.03))
        for s_ in (-1, 1):
            P.append(cyl(f'lo_bufs{e}{s_}', .09, .45, (s_ * .875, ye + e * .45, zf - .3), 'M_Metal', rot=(math.pi / 2, 0, 0), seg=10))
            P.append(cyl(f'lo_bufh{e}{s_}', .22, .06, (s_ * .875, ye + e * .7, zf - .3), 'M_Metal', rot=(math.pi / 2, 0, 0), seg=16))
            P.append(box(f'lo_hr{e}{s_}', .04, .04, 1.2, (s_ * 1.35, ye - e * .5, zf + .2), 'M_Metal', bevel=0))
        P.append(box(f'lo_hook{e}', .2, .5, .14, (0, ye + e * .4, zf - .3), 'M_Metal', bevel=0))
        P.append(box(f'lo_stripe{e}', 2.9, .05, .12, (0, ye + e * .02, zf + .85), 'M_TrainCream', bevel=0))
    for s_ in (-1, 1):                      # sides: cab doors + windows, louvre bands, a white line
        for e in (-1, 1):
            P.append(box(f'lo_door{s_}{e}', .05, .75, 1.9, (s_ * (W / 2 + .005), e * (L / 2 - 1.9), zf + .25), 'M_TrainRed', bevel=.01))
            P.append(box(f'lo_dwin{s_}{e}', .05, .5, .55, (s_ * (W / 2 + .02), e * (L / 2 - 1.9), zf + 1.45), 'M_Glass', bevel=0))
        for k in range(5):
            P.append(box(f'lo_louv{s_}{k}', .05, 1.25, .7, (s_ * (W / 2 + .01), -3.4 + k * 1.7, zf + 1.3), 'M_Iron', bevel=0))
        P.append(box(f'lo_line{s_}', .03, L - 3.0, .08, (s_ * (W / 2 + .015), 0, zf + .7), 'M_TrainCream', bevel=0))
    for k, yy in enumerate((-3.6, 3.6)):     # pantographs (lowered-diamond frame) + insulators + roof conduit
        P.append(box(f'lo_pbase{k}', 1.6, 1.2, .12, (0, yy, zf + H + .02), 'M_Metal', bevel=0))
        for s_ in (-1, 1): P.append(box(f'lo_parm{k}{s_}', .06, 1.7, .06, (s_ * .45, yy, zf + H + .45), 'M_Metal', rot=(math.radians(22 * s_), 0, 0), bevel=0))
        P.append(box(f'lo_phead{k}', 1.9, .12, .05, (0, yy, zf + H + .78), 'M_Metal', bevel=0))
        for s_ in (-1, 1): P.append(cyl(f'lo_ins{k}{s_}', .07, .25, (s_ * .6, yy + .7, zf + H), 'M_Trim', seg=8))
    P.append(box('lo_conduit', .12, 7.0, .1, (.4, 0, zf + H + .05), 'M_Metal', bevel=0))
    return join(P, 'SM_TrainLoco')

def carriage():
    """2026-10-23: a realistic 14 m regional coach (dark green with a cream window band): arched-roof body, 7 framed windows
    a side, sliding doors at both ends, roof vents, two bogies, gangway bellows, buffers. Origin: rail top, centre."""
    P = []; L, W, H, zf = 14.0, 2.85, 2.7, 1.12
    P.append(_body_shell('ca_body', L, W, H, zf, 'M_TrainGreen'))
    P.append(box('ca_under', 2.5, L - 1.0, .45, (0, 0, zf - .45), 'M_Iron', bevel=.03))
    for yb in (-L / 2 + 2.6, L / 2 - 2.6): _bogie(P, f'ca_b{yb}', yb, .32, wheel_r=.46, base=2.5)
    for s_ in (-1, 1):
        x = s_ * (W / 2 + .012)
        P.append(box(f'ca_band{s_}', .03, L - .3, .95, (x, 0, zf + 1.05), 'M_TrainCream', bevel=0))
        for k in range(7):
            y = -L / 2 + 2.6 + k * 1.47
            P.append(box(f'ca_win{s_}{k}', .04, 1.12, .78, (s_ * (W / 2 + .03), y, zf + 1.13), 'M_Glass', bevel=0))
            P.append(box(f'ca_wfr{s_}{k}', .03, 1.22, .06, (s_ * (W / 2 + .04), y, zf + 1.93), 'M_Metal', bevel=0))
        for e in (-1, 1):
            P.append(box(f'ca_door{s_}{e}', .05, .95, 2.0, (s_ * (W / 2 + .02), e * (L / 2 - .9), zf + .02), 'M_Door', bevel=.01))
            P.append(box(f'ca_dwin{s_}{e}', .05, .45, .6, (s_ * (W / 2 + .045), e * (L / 2 - .9), zf + 1.25), 'M_Glass', bevel=0))
            P.append(box(f'ca_step{s_}{e}', .35, .95, .06, (s_ * (W / 2 - .05), e * (L / 2 - .9), zf - .35), 'M_Metal', bevel=0))
    for k in range(5): P.append(box(f'ca_vent{k}', .45, .6, .18, (0, -5.0 + k * 2.5, zf + H - .02), 'M_Metal', bevel=.04))
    for e in (-1, 1):
        ye = e * (L / 2)
        P.append(box(f'ca_gang{e}', 1.2, .35, 2.1, (0, ye + e * .15, zf), 'M_Iron', bevel=.08))
        P.append(box(f'ca_beam{e}', 2.6, .25, .45, (0, ye + e * .1, zf - .5), 'M_Iron', bevel=.03))
        for s_ in (-1, 1):
            P.append(cyl(f'ca_bufs{e}{s_}', .09, .4, (s_ * .875, ye + e * .35, zf - .3), 'M_Metal', rot=(math.pi / 2, 0, 0), seg=10))
            P.append(cyl(f'ca_bufh{e}{s_}', .21, .06, (s_ * .875, ye + e * .58, zf - .3), 'M_Metal', rot=(math.pi / 2, 0, 0), seg=16))
    return join(P, 'SM_TrainCar')

# ------------------------------------------------------------------ distant landscape (skirt around the town square, mountains, sky)
def far_height(x, y):
    """continues height() outside the 220 m town square: the hills keep rising to a plateau, the sea floor keeps sinking"""
    return height_raw(max(-110, min(110, x)), max(-110, min(110, y))) if (abs(x) <= 110 and abs(y) <= 110) else height_raw(x, y)

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

# ------------------------------------------------------------------ realistic mountains (2026-10-22): real elevation data
# The skyline is the real Bernese Oberland around Grindelwald (Eiger / Mettenberg / Wetterhorn), from the public AWS Terrain
# Tiles (Terrarium, zoom 12, ~38 m/px) fetched by tools/ph_download.py into PokeboxNext_src/polyhaven/dem. Rotated 180 deg so the
# big north faces stand to the game's north (the sea is south), scaled 1:DEM_K in all three axes (true proportions:
# Eiger ~245 m above the village, ~430 m away). Near the village the relief fades out into the existing hills; the
# railway tunnel keeps a mountain over it. One smooth mesh, no UVs (Unreal textures it by world position, slope and height).
DEM_DIR = os.path.join(OUT, 'polyhaven', 'dem')
DEM_K = 12.0
_DEM = {}
def dem_load():
    if _DEM: return _DEM
    import numpy as np
    meta = json.load(open(os.path.join(DEM_DIR, 'dem.json'))); z, cx, cy, r = meta['z'], meta['cx'], meta['cy'], meta['r']
    n = 2 * r + 1; mos = np.zeros((n * 256, n * 256), np.float32)
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            im = bpy.data.images.load(os.path.join(DEM_DIR, '%d_%d_%d.png' % (z, cx + dx, cy + dy)), check_existing=False)
            im.colorspace_settings.name = 'Non-Color'
            px = np.empty(256 * 256 * 4, np.float32); im.pixels.foreach_get(px); bpy.data.images.remove(im)
            a = np.round(px.reshape(256, 256, 4)[::-1] * 255.0)          # row 0 = north
            e = a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768
            mos[(dy + r) * 256:(dy + r + 1) * 256, (dx + r) * 256:(dx + r + 1) * 256] = e
    _DEM.update(mos=mos, z=z, x0=cx - r, y0=cy - r, lat=meta['lat'], lon=meta['lon'])
    _DEM['e0'] = dem_real(0.0, 0.0)
    return _DEM

def dem_real(dE, dN):
    """real elevation (m) at dE / dN metres east / north of the village, bilinear"""
    import numpy as np
    d = _DEM; lat = d['lat'] + dN / 111320.0; lon = d['lon'] + dE / (111320.0 * math.cos(math.radians(d['lat'])))
    n = 2 ** d['z']
    fx = (lon + 180) / 360 * n; fy = (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n
    px = (fx - d['x0']) * 256 - .5; py = (fy - d['y0']) * 256 - .5
    m = d['mos']; H, W = m.shape
    px = min(max(px, 0), W - 1.001); py = min(max(py, 0), H - 1.001); i, j = int(py), int(px); ty, tx = py - i, px - j
    return float(m[i, j] * (1 - tx) * (1 - ty) + m[i, j + 1] * tx * (1 - ty) + m[i + 1, j] * (1 - tx) * ty + m[i + 1, j + 1] * tx * ty)

def dem_game(x, y):
    """relief (game metres above the village) at Blender (x, y): rotated 180 deg, 1:DEM_K"""
    return (dem_real(-x * DEM_K, y * DEM_K) - _DEM['e0']) / DEM_K

def real_weight(x, y):
    """0 in the village, 1 in the mountains (the sea is handled by the coastline, not here)"""
    d = math.hypot(x, y + 10)
    w = min(1, max(0, (d - 150) / 120)); return w * w * (3 - 2 * w)

def _ss(a, b, t):
    t = min(1, max(0, (t - a) / (b - a))); return t * t * (3 - 2 * t)

def coast_y(x):
    """the shoreline: the harbour bay in front of the village, headlands curving south on both sides (2026-10-23)"""
    ax = abs(x)
    return 45.0 if ax < 110 else 45.0 + (ax - 110) * .55 + max(0, ax - 400) * .35

def tunnel_bump(x, y):
    """the railway mountain behind the portal (2026-10-23 b). Between the wing walls the rock face stands INSIDE the 1.6 m
    deep headwall (the terrain grid has rows at the face +5 cm and 1 m behind it, and a hole over the bore there, so no
    terrain ever shows in the arch). Beside the headwall the hillside follows the 30 deg wing walls down to the cutting,
    never higher than their tops. Over the bore it is always >= 10.6 m (the arch is 7.4 m)."""
    dy = TRACK_Y0 - y; a = abs(x - TRACK_X)
    if dy > 300: return -99.0
    gx = math.exp(-((x - TRACK_X) / 55.0) ** 2)
    if gx < .03: return -99.0
    full = (10.6 + 50.0 * _ss(2.5, 90, dy)) * (1 - _ss(140, 300, dy)) * (gx if dy > 70 else max(gx, _ss(14, 9, a)))
    if a < 8.6:
        return full * _ss(-.05, .95, dy) if dy > -.05 else -99.0
    f = 1.73 * (a - 8.6)                          # the wing wall line: 30 deg towards the town
    if dy < -f: return -99.0
    u = min(11.0, (a - 8.6) / .5)
    return min(full, 11.0 - 8.5 * u / 11.0 + (dy + f) * .9)

TUNNEL_HOLE = (TRACK_X - 4.0, TRACK_X + 4.0, TRACK_Y0 - 1.0, TRACK_Y0 + .05)   # x0, x1, y0, y1: no terrain faces here

def real_height_raw(x, y):
    """terrain outside the town square: hills -> real Alpine relief (1:12), coastline + sea floor, tunnel mountain"""
    land = min(height_raw(x, min(y, 40.0)), 16.0)
    land += real_weight(x, y) * max(-20.0, dem_game(x, y))
    land = max(land, .6 * _ss(100, 160, math.hypot(x, y + 10)))     # valleys below the village level must not flood (sea is at -1.2 m)
    cy = coast_y(x); sea = _ss(cy - 2, cy + 34, y)
    floor = -3.0 - 26.0 * _ss(0, 420, y - cy)
    z = land + (floor - land) * sea
    # continuous with the town ground mesh at the edge of the 220 m square
    b = _ss(110, 132, max(abs(x), abs(y)))
    z = height_raw(x, y) + (z - height_raw(x, y)) * b
    tb = tunnel_bump(x, y)                # after the blend: the portal sits 3 m outside the town square
    if tb > -50: z = max(z, min(height_raw(x, min(y, 40.0)), 16.0) + tb)
    return z

_REST_Z = []
def real_height(x, y):
    z = real_height_raw(x, y)
    d = math.hypot(x - REST[0], y - REST[1])
    if d < 22:                                   # the Lamplighters' Rest: a levelled clearing on the slope
        if not _REST_Z: _REST_Z.append(real_height_raw(*REST))
        k = 1 - _ss(12, 22, d); z = z * (1 - k) + _REST_Z[0] * k
    return river_carve(x, y, z)

# ------------------------------------------------------------------ the stream (2026-10-23): from the mountains in the
# north-east, down a gully east of the railway, past the east edge of the village and into the harbour.
RIVER_SRC = (150.0, -232.0)                                         # a spring ~60 m up at the foot of the mountain north-east of the tunnel
# past the east edge of the village into the sea east of the harbour (gentle bends; the bridge crossing stays at (54.4, 29))
RIVER_TOWN = [(62, -72), (58, -56), (55, -40), (57, -24), (55.5, -8), (52.5, 6), (53.5, 18), (54.4, 29), (55.5, 39), (54.5, 47), (53.5, 53)]
RIVER_SEA = -1.55                                                   # the stream's surface meets this under the sea surface (-1.2)
def _river_path():
    """follow the real valley downhill (terrain gradient, a pull towards the village so it doesn't wander off, and a
    slow lateral wobble so it bends like a mountain stream), then the fixed course past the village."""
    dem_load(); x, y = RIVER_SRC; pts = [(x, y)]; px, py = 0.0, 1.0; tx, ty = RIVER_TOWN[0]
    for k in range(400):
        e = 2.0
        gx = (real_height_raw(x + e, y) - real_height_raw(x - e, y)) / (2 * e); gy = (real_height_raw(x, y + e) - real_height_raw(x, y - e)) / (2 * e)
        gl = math.hypot(gx, gy) or 1e-6; dx, dy = tx - x, ty - y; dl = math.hypot(dx, dy) or 1e-6
        pull = .12 + .9 * _ss(120, 25, dl)
        wob = (.75 * math.sin(k * .16 + 1.3) + .35 * math.sin(k * .41 + .2)) * (1 - _ss(60, 20, dl))
        vx = -gx / gl + pull * dx / dl + .5 * px - py * wob; vy = -gy / gl + pull * dy / dl + .5 * py + px * wob
        vl = math.hypot(vx, vy) or 1e-6; px, py = vx / vl, vy / vl
        x += 3.0 * px; y += 3.0 * py
        pts.append((round(x, 2), round(y, 2)))
        if math.hypot(tx - x, ty - y) < 8: break
    # light smoothing of the traced course (3-tap), then the village course
    sm = [pts[0]] + [((pts[i - 1][0] + 2 * pts[i][0] + pts[i + 1][0]) / 4, (pts[i - 1][1] + 2 * pts[i][1] + pts[i + 1][1]) / 4) for i in range(1, len(pts) - 1)] + [pts[-1]]
    return sm[::2] + RIVER_TOWN
RIVER = None
_RIV = {}
def _river_samples():
    if _RIV: return _RIV
    RV = _river_path(); pts = []
    # Catmull-Rom through the control points, ~2 m steps -> smooth bends instead of straight segments
    C = [RV[0]] + RV + [RV[-1]]
    for i in range(1, len(C) - 2):
        p0, p1, p2, p3 = C[i - 1], C[i], C[i + 1], C[i + 2]
        L = math.hypot(p2[0] - p1[0], p2[1] - p1[1]); n = max(1, int(L / 2.0))
        for k in range(n):
            t = k / n; t2 = t * t; t3 = t2 * t
            pts.append(tuple(.5 * (2 * p1[c] + (-p0[c] + p2[c]) * t + (2 * p0[c] - 5 * p1[c] + 4 * p2[c] - p3[c]) * t2 + (-p0[c] + 3 * p1[c] - 3 * p2[c] + p3[c]) * t3) for c in (0, 1)))
    pts.append(RV[-1])
    tot = [0.0]
    for (ax, ay), (bx, by) in zip(pts[:-1], pts[1:]): tot.append(tot[-1] + math.hypot(bx - ax, by - ay))
    T = tot[-1]; dem_load()
    surf = []; run = 1e9
    for k, (x, y) in enumerate(pts):
        raw = height_raw(x, y) if (abs(x) < 110 and abs(y) < 110) else real_height_raw(x, y)
        run = min(run, raw - .55 - .25 * (tot[k] / T)); surf.append(run)
    for k, (x, y) in enumerate(pts):              # the mouth: the surface slides under the sea surface at the shoreline
        t = _ss(coast_y(x) - 24, coast_y(x) - 1, y); surf[k] = max(RIVER_SEA, surf[k] * (1 - t) + RIVER_SEA * t)
    _RIV.update(pts=pts, s=[t / T for t in tot], surf=surf, T=T)
    return _RIV

def river_width(t): return 2.4 + 4.6 * t + .5 * math.sin(t * 37.0) * t        # half of this is the water's half-width
def river_query(x, y):
    """(distance to the centre line, t 0..1 along, water surface z) — coarse segment search"""
    R = _river_samples(); P = R['pts']; best = (1e9, 0, 0)
    for k in range(0, len(P) - 1):
        ax, ay = P[k]; bx, by = P[k + 1]
        if abs(x - ax) > 40 and abs(x - bx) > 40: continue
        dx, dy = bx - ax, by - ay; L2 = dx * dx + dy * dy or 1e-6
        u = max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / L2)); d = math.hypot(x - ax - dx * u, y - ay - dy * u)
        if d < best[0]: best = (d, R['s'][k] + (R['s'][k + 1] - R['s'][k]) * u, R['surf'][k] + (R['surf'][k + 1] - R['surf'][k]) * u)
    return best

def river_carve(x, y, z):
    if x < 30 or x > 235 or y < -500 or y > 90: return z
    d, t, sz = river_query(x, y)
    hw = river_width(t) / 2; bank = 3.0 + 4.0 * t
    if d > hw + bank: return z
    depth = .7 + .5 * t
    if d <= hw: c = sz - depth * (1 - (d / hw) ** 2) - .05
    else: c = sz + .25 + (z - sz - .25) * _ss(0, 1, (d - hw) / bank) if z > sz + .25 else z
    return min(z, c)

def river_mesh():
    """the water ribbon: 2 m steps along the stream, width grows downstream; UV.x = metres along (the flow), UV.y across"""
    R = _river_samples(); P = R['pts']; V = []; F = []; UV = []
    P = [p for p in P if p[1] < coast_y(p[0]) + 5.0]
    for k, (x, y) in enumerate(P):
        a = P[min(k + 1, len(P) - 1)]; b = P[max(k - 1, 0)]; tx, ty = a[0] - b[0], a[1] - b[1]; L = math.hypot(tx, ty) or 1
        nx, ny = -ty / L, tx / L; hw = river_width(R['s'][k]) / 2 + .6
        for side in (-1, 1): V.append((x + nx * hw * side, y + ny * hw * side, R['surf'][k])); UV.append((R['s'][k] * R['T'], (side + 1) / 2))
    for k in range(len(P) - 1):
        i = 2 * k; F.append((i, i + 1, i + 3, i + 2))
    me = bpy.data.meshes.new('SM_River'); me.from_pydata(V, [], F); me.update()
    uv = me.uv_layers.new(name='UV')
    for poly in me.polygons:
        for li in poly.loop_indices: uv.data[li].uv = UV[me.loops[li].vertex_index]
    if sum(p.normal.z for p in me.polygons) < 0: me.flip_normals()
    ob = bpy.data.objects.new('SM_River', me); bpy.context.collection.objects.link(ob); set_mat(ob, 'M_River')
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.fbx(filepath=os.path.join(FBX, 'SM_River.fbx'), use_selection=True, apply_scale_options='FBX_SCALE_ALL',
                             axis_forward='-Z', axis_up='Y', mesh_smooth_type='FACE', add_leaf_bones=False, bake_anim=False)
    print('river', len(V), 'verts, length', round(R['T']), 'm, surface', round(R['surf'][0], 1), '->', round(R['surf'][-1], 1))

def _axis(a, b, fine, coarse, f0, f1):
    import numpy as np
    xs = list(np.arange(a, f0, coarse)) + list(np.arange(f0, f1, fine)) + list(np.arange(f1, b + .01, coarse))
    return np.array(sorted(set(round(float(v), 3) for v in xs)))

def mountains_real(ext=1400.0):
    """ONE terrain from the edge of the town square out to 1.4 km: hills, real relief, coast, sea floor, stream bed, tunnel
    mountain (replaces SM_GroundFar + the old separate mountains: no seam, no gap). Rectilinear grid, 4 m inside +-400 m,
    10 m outside (crack-free: the same x / y lines everywhere). It slips 3 m under the town ground mesh."""
    dem_load(); _river_samples()
    import numpy as np
    xs = _axis(-ext, ext, 4.0, 10.0, -400.0, 400.0); n = len(xs)
    ys = np.array(sorted(set(list(xs) + [TUNNEL_HOLE[2], TUNNEL_HOLE[3]]))); m_ = len(ys)   # + the tunnel face rows
    Z = np.zeros((m_, n), np.float32)
    for j, y in enumerate(ys):
        for i, x in enumerate(xs): Z[j, i] = real_height(x, y)
    inside = (np.abs(xs)[None, :] < 106.5) & (np.abs(ys)[:, None] < 106.5)
    under = (np.abs(xs)[None, :] < 110.5) & (np.abs(ys)[:, None] < 110.5)     # sits 4 cm under the town ground where they overlap
    me = bpy.data.meshes.new('SM_Mountains'); V = []; F = []; idx = -np.ones((m_, n), np.int64)
    for j in range(m_):
        for i in range(n): idx[j, i] = len(V); V.append((float(xs[i]), float(ys[j]), float(Z[j, i]) - (.04 if under[j, i] else 0)))
    hx0, hx1, hy0, hy1 = TUNNEL_HOLE
    for j in range(m_ - 1):
        for i in range(n - 1):
            if inside[j, i] and inside[j + 1, i + 1] and inside[j + 1, i] and inside[j, i + 1]: continue
            if abs(ys[j] - hy0) < 1e-3 and abs(ys[j + 1] - hy1) < 1e-3 and xs[i] > hx0 - 1e-3 and xs[i + 1] < hx1 + 1e-3: continue   # the bore
            F.append((idx[j, i], idx[j, i + 1], idx[j + 1, i + 1], idx[j + 1, i]))   # counter-clockwise from above (verified in Unreal)
    me.from_pydata(V, [], F); me.update()
    used = set(v for f in F for v in f)
    for p in me.polygons: p.use_smooth = True
    ob = bpy.data.objects.new('SM_Mountains', me); bpy.context.collection.objects.link(ob); set_mat(ob, 'M_Mountain')
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index not in used], context='VERTS'); bm.to_mesh(me); bm.free()
    # vertex colour R = the Lamplighters' Path (worn dirt in the terrain material)
    ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
    for v in me.vertices:
        x, y = v.co.x, v.co.y
        m = 0.0
        if -110 < x < -20 and -230 < y < -40:
            m = max(1 - _ss(1.1, 2.6, trail_dist(x, y)), 1 - _ss(6.0, 11.0, math.hypot(x - REST[0], y - REST[1])))
        ca.data[v.index].color = (m, 0.0, 0.0, 1.0)
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.fbx(filepath=os.path.join(FBX, 'SM_Mountains.fbx'), use_selection=True, apply_scale_options='FBX_SCALE_ALL',
                             axis_forward='-Z', axis_up='Y', mesh_smooth_type='FACE', colors_type='LINEAR', add_leaf_bones=False, bake_anim=False)
    print('terrain', len(me.vertices), 'verts', len(F), 'faces, peak', float(Z.max()), 'deepest', float(Z.min()))
    return ob

def water_plane():
    """the sea: a flat grid (Unreal moves it with Gerstner waves in the material), 2 m cells over the harbour where the
    camera is, 25 m cells out to 3 km (crack-free rectilinear grid). Origin at world 0; the plan places it at z = -1.2."""
    import numpy as np
    xs = _axis(-3000, 3000, 2.0, 25.0, -260.0, 260.0); ys = _axis(-200, 3400, 2.0, 25.0, 30.0, 330.0)
    me = bpy.data.meshes.new('SM_Water'); V = [(float(x), float(y), 0.0) for y in ys for x in xs]; n = len(xs); F = []
    for j in range(len(ys) - 1):
        for i in range(n - 1):
            a = j * n + i; F.append((a, a + 1, a + n + 1, a + n))
    me.from_pydata(V, [], F); me.update()
    uv = me.uv_layers.new(name='UV')
    for poly in me.polygons:
        for li in poly.loop_indices:
            v = V[me.loops[li].vertex_index]; uv.data[li].uv = (v[0] / 10.0, v[1] / 10.0)
    ob = bpy.data.objects.new('SM_Water', me); bpy.context.collection.objects.link(ob); set_mat(ob, 'M_Water')
    for p in me.polygons: p.use_smooth = True
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.fbx(filepath=os.path.join(FBX, 'SM_Water.fbx'), use_selection=True, apply_scale_options='FBX_SCALE_ALL',
                             axis_forward='-Z', axis_up='Y', mesh_smooth_type='FACE', add_leaf_bones=False, bake_anim=False)
    print('sea', len(V), 'verts')

# ------------------------------------------------------------------ the island across the bay (2026-10-23, phase 3):
# ~300 x 220 m, 1.45 km south of the village; a cove with a jetty facing the village, a grassy hill, rocky shores and the
# lighthouse on the north-eastern headland. Reached with the rowboat (C++ boat mode: APBXDirector::TickBoat).
ISLAND = (240.0, 1450.0); ISLAND_JETTY = (232.0, 1338.0)
# 2026-10-23 b: a deliberate layout — the lighthouse on the north-eastern point (it guards the way into the bay), the
# keeper's cottage just inland of it with a fenced yard, a 23 m jetty in the north cove, and a worn path between them
LIGHTHOUSE = (333.0, 1382.0); COTTAGE_DOOR = (314.5, 1392.5); COTTAGE_FACE = (-1.0, -.35); COTTAGE_C = (318.7, 1394.0)
ISLAND_PIER = (232.0, 1349.0, 23.0)                  # shore end x, y, length (runs north)
ISLAND_PATH = [(232.0, 1350.0), (240.0, 1360.0), (258.0, 1372.0), (285.0, 1384.0), (COTTAGE_DOOR[0] - 1.0, COTTAGE_DOOR[1] - .3), (LIGHTHOUSE[0] - 4.6, LIGHTHOUSE[1] + .4)]
def island_path_dist(x, y):
    best = 1e9
    for (ax, ay), (bx, by) in zip(ISLAND_PATH[:-1], ISLAND_PATH[1:]):
        dx, dy = bx - ax, by - ay; L2 = dx * dx + dy * dy
        u = max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / L2)); best = min(best, math.hypot(x - ax - dx * u, y - ay - dy * u))
    return best
def island_h(x, y):
    u, v = (x - ISLAND[0]) / 150.0, (y - ISLAND[1]) / 110.0
    rr = math.hypot(u, v) * (1 + .1 * math.sin(x * .045 + 1.1) + .07 * math.sin(y * .061 + .4) + .04 * math.sin((x + y) * .13))
    z = -18.0 + 18.0 * _ss(1.45, .98, rr) + 2.2 * _ss(.98, .86, rr) + 15.0 * _ss(.86, .42, rr) ** 1.3
    c = 1 - _ss(10, 42, math.hypot(x - ISLAND_JETTY[0], (y - ISLAND_JETTY[1]) * 1.3))      # the cove: a low beach at the jetty
    if z > .6: z = z * (1 - c) + .7 * c
    if abs(x - ISLAND_PIER[0]) < 14 and ISLAND_PIER[1] - ISLAND_PIER[2] - 8 < y < ISLAND_PIER[1]:       # sandy shallows under the jetty
        z = max(z, -2.9 + 2.9 * _ss(ISLAND_PIER[1] - ISLAND_PIER[2] + 2, ISLAND_PIER[1], y) * 0)
    for (px_, py_, pr_) in ((LIGHTHOUSE[0], LIGHTHOUSE[1], 6.5), (COTTAGE_C[0], COTTAGE_C[1], 8.5)):   # levelled ground
        k = 1 - _ss(pr_, pr_ + 7, math.hypot(x - px_, y - py_))
        if k > 0: z = z * (1 - k) + _island_raw(px_, py_) * k
    return z

def _island_raw(x, y):
    u, v = (x - ISLAND[0]) / 150.0, (y - ISLAND[1]) / 110.0
    rr = math.hypot(u, v) * (1 + .1 * math.sin(x * .045 + 1.1) + .07 * math.sin(y * .061 + .4) + .04 * math.sin((x + y) * .13))
    return -18.0 + 18.0 * _ss(1.45, .98, rr) + 2.2 * _ss(.98, .86, rr) + 15.0 * _ss(.86, .42, rr) ** 1.3

def island_mesh():
    import numpy as np
    xs = np.arange(ISLAND[0] - 230, ISLAND[0] + 230.1, 2.5); ys = np.arange(ISLAND[1] - 180, ISLAND[1] + 180.1, 2.5)
    V = [(float(x), float(y), island_h(x, y)) for y in ys for x in xs]; n = len(xs); F = []
    for j in range(len(ys) - 1):
        for i in range(n - 1):
            a = j * n + i; F.append((a, a + 1, a + n + 1, a + n))
    me = bpy.data.meshes.new('SM_Island'); me.from_pydata(V, [], F); me.update()
    if sum(p.normal.z for p in me.polygons) < 0: me.flip_normals()
    ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')         # R = the island path (dirt), G = 1: meadow grass (terrain material)
    for k, v in enumerate(me.vertices): ca.data[k].color = (1 - _ss(1.0, 2.2, island_path_dist(v.co.x, v.co.y)), 1.0, 0.0, 1.0)
    for p in me.polygons: p.use_smooth = True
    ob = bpy.data.objects.new('SM_Island', me); bpy.context.collection.objects.link(ob); set_mat(ob, 'M_Mountain')
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.fbx(filepath=os.path.join(FBX, 'SM_Island.fbx'), use_selection=True, apply_scale_options='FBX_SCALE_ALL',
                             axis_forward='-Z', axis_up='Y', mesh_smooth_type='FACE', colors_type='LINEAR', add_leaf_bones=False, bake_anim=False)
    print('island', len(V), 'verts, top', max(v[2] for v in V))

def _ring_tower(name, r0, r1, h, z0, m, seg=32):
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=False, segments=seg, radius1=r0, radius2=r1, depth=h)
    bmesh.ops.translate(bm, vec=Vector((0, 0, z0 + h / 2)), verts=bm.verts)
    ob = mesh_obj(name, bm); set_mat(ob, m); return ob

def lighthouse():
    """a 21 m stone-and-plaster lighthouse: plinth, tapered tower in white with two red bands, iron gallery with railing,
    glazed lantern room with the lamp, domed iron roof with a vent ball. Origin = ground at the centre."""
    P = [cyl('lh_plinth', 4.2, 1.2, (0, 0, 0), 'M_Stone', seg=32)]
    H = 17.0; r0, r1 = 3.2, 2.3
    bands = [(0, 6.0, 'M_Plaster'), (6.0, 2.2, 'M_Red'), (8.2, 4.6, 'M_Plaster'), (12.8, 2.2, 'M_Red'), (15.0, 2.0, 'M_Plaster')]
    for k, (z0, h, m) in enumerate(bands):
        ra = r0 + (r1 - r0) * z0 / H; rb = r0 + (r1 - r0) * (z0 + h) / H
        P.append(_ring_tower(f'lh_band{k}', ra, rb, h, 1.2 + z0, m))
    top = 1.2 + H
    P.append(cyl('lh_cap', r1 + .05, .2, (0, 0, top - .2), 'M_Plaster', seg=32))
    P.append(cyl('lh_gallery', 3.3, .28, (0, 0, top), 'M_Iron', seg=36))
    for k in range(24):
        a = 2 * math.pi * k / 24; P.append(box(f'lh_post{k}', .06, .06, 1.05, (math.cos(a) * 3.15, math.sin(a) * 3.15, top + .28), 'M_Iron', bevel=0))
    P.append(_ring_tower('lh_rail', 3.15, 3.15, .06, top + 1.3, 'M_Iron', seg=36))
    P.append(cyl('lh_lanbase', 1.85, .9, (0, 0, top + .28), 'M_Iron', seg=24))
    P.append(_ring_tower('lh_glass', 1.75, 1.75, 2.2, top + 1.18, 'M_Glass', seg=24))
    for k in range(8):
        a = 2 * math.pi * k / 8; P.append(box(f'lh_mull{k}', .08, .08, 2.2, (math.cos(a) * 1.76, math.sin(a) * 1.76, top + 1.18), 'M_Iron', bevel=0))
    P.append(cyl('lh_lamp', .55, 1.1, (0, 0, top + 1.6), 'M_LampGlass', seg=16))
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=2.0, radius2=.15, depth=1.5)
    bmesh.ops.translate(bm, vec=Vector((0, 0, top + 3.38 + .75)), verts=bm.verts); ob = mesh_obj('lh_roof', bm); set_mat(ob, 'M_Iron'); P.append(ob)
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=.28)
    bmesh.ops.translate(bm, vec=Vector((0, 0, top + 5.0)), verts=bm.verts); ob = mesh_obj('lh_ball', bm); set_mat(ob, 'M_Iron'); P.append(ob)
    P.append(box('lh_door', 1.1, .25, 2.1, (0, -r0 - .02, 1.2), 'M_Door', bevel=.02))
    for k, z in enumerate((5.0, 10.5, 14.5)):
        P.append(box(f'lh_win{k}', .55, .2, .9, (0, -(r0 + (r1 - r0) * (z - 1.2) / H) - .02, z), 'M_Glass', bevel=.02))
    return join(P, 'SM_Lighthouse')

# ------------------------------------------------------------------ harbour craft (2026-10-23 b): modelled boats, a
# wooden pier on piles, rubble-stone breakwaters, a timber trestle bridge over the stream. Boats: bow = local +X (the
# C++ boat code drives along the actor's forward axis), waterline at z = 0, so they are placed at the sea level (-1.2).
def export_smooth(ob, name, smooth_mats=()):
    """like export(), but faces of the listed materials keep smooth shading (hulls)"""
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active = ob
    box_uv(ob)
    names = [m.name if m else '' for m in ob.data.materials]
    for pl in ob.data.polygons: pl.use_smooth = names[pl.material_index] in smooth_mats if pl.material_index < len(names) else False
    path = os.path.join(FBX, name + '.fbx')
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y',
                             mesh_smooth_type='FACE', use_mesh_modifiers=True, add_leaf_bones=False, bake_anim=False)
    return path

def _hull_dims(s, L, B, D, fb, sheer, transom, p):
    """half-beam, gunwale height, keel depth at s (0 = stern .. 1 = bow)"""
    if s < .42: b = B / 2 * (transom + (1 - transom) * math.sin(math.pi / 2 * s / .42))
    else: b = B / 2 * max(0.0, math.cos(math.pi / 2 * (s - .42) / .58)) ** .7
    g = fb + sheer * ((s - .45) / .55) ** 2 * (1.5 if s > .45 else .6)
    d = max(.04, D * (1 - abs((s - .45) / .58) ** 2.4))
    return b, g, d

def hull(prefix, L, B, D, fb, sheer=.22, transom=.55, p=.55, m_out='M_Siding_White', m_in='M_WoodLight', m_rim='M_WoodDark', ns=28, nr=9, t=.05):
    """an open wooden hull lofted along X (stern -L/2 .. bow +L/2): outer planking, inner planking, gunwale cap and a
    transom board. Sections are rounded-V (cos^p bilge)."""
    O, I = [], []
    for i in range(ns + 1):
        s_ = i / ns; x = -L / 2 + L * s_
        b, g, d = _hull_dims(s_, L, B, D, fb, sheer, transom, p)
        ro, ri = [], []
        for j in range(2 * nr + 1):
            th = (j - nr) / nr * math.pi / 2
            ro.append((x, b * math.sin(th), g - (g + d) * abs(math.cos(th)) ** p))
            bi = max(0.0, b - t); di = max(0.0, d - t)
            ri.append((x + (t if i == 0 else 0), bi * math.sin(th), g - (g + di) * abs(math.cos(th)) ** p + (t * .3 if i == 0 else 0)))
        O.append(ro); I.append(ri)
    def surf(name, grid, flip, m):
        bm = bmesh.new(); vv = [[bm.verts.new(c) for c in row] for row in grid]
        for i in range(len(grid) - 1):
            for j in range(len(grid[0]) - 1):
                q = (vv[i][j], vv[i + 1][j], vv[i + 1][j + 1], vv[i][j + 1])
                try: bm.faces.new(q[::-1] if flip else q)
                except ValueError: pass
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
        ob = mesh_obj(name, bm); set_mat(ob, m); return ob
    # outer: i along +X, j from port (-Y) to starboard: (x) x (y) = +z at the keel -> wound so normals point outwards
    P = [surf(prefix + '_out', O, True, m_out), surf(prefix + '_in', I, False, m_in)]
    rim = []
    for i in range(ns + 1):
        rim.append([O[i][0], I[i][0]]); 
    bm = bmesh.new()
    for side in (0, 2 * nr):
        a = [bm.verts.new(O[i][side]) for i in range(ns + 1)]; c = [bm.verts.new(I[i][side]) for i in range(ns + 1)]
        ua = [bm.verts.new((v[0], v[1], v[2] + .045)) for v in [O[i][side] for i in range(ns + 1)]]
        uc = [bm.verts.new((v[0], v[1], v[2] + .045)) for v in [I[i][side] for i in range(ns + 1)]]
        for i in range(ns):
            for q in ((ua[i], ua[i + 1], uc[i + 1], uc[i]), (a[i], a[i + 1], ua[i + 1], ua[i]), (c[i + 1], c[i], uc[i], uc[i + 1])):
                try: bm.faces.new(q if side == 0 else q[::-1])
                except ValueError: pass
    bm.normal_update()
    ob = mesh_obj(prefix + '_rim', bm); set_mat(ob, m_rim); P.append(ob)
    # transom board: the stern section as a solid plate
    bm = bmesh.new(); f0 = [bm.verts.new(c) for c in O[0]]; f1 = [bm.verts.new((c[0] + t, c[1], c[2])) for c in O[0]]
    try:
        bm.faces.new(f0[::-1]); bm.faces.new(f1)
        for j in range(len(f0) - 1): bm.faces.new((f0[j], f0[j + 1], f1[j + 1], f1[j]))
        bm.faces.new((f0[-1], f0[0], f1[0], f1[-1]))
    except ValueError: pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = mesh_obj(prefix + '_transom', bm); set_mat(ob, m_out); P.append(ob)
    return P, O

def _fix_outward(ob, inward=False):
    """flip the faces of an open surface so the normal at its lowest point faces down (outer) / up (inner)"""
    me = ob.data; low = min(me.polygons, key=lambda pl: pl.center.z)
    if (low.normal.z > 0) != inward: 
        for pl in me.polygons: pl.flip()

def _thwart(name, L, B, D, fb, sheer, transom, p, s_, z_off, w=.24, m='M_WoodDark'):
    b, g, d = _hull_dims(s_, L, B, D, fb, sheer, transom, p)
    zz = g - z_off; th = math.acos(min(1.0, max(0.0, ((g - zz) / (g + d)) ** (1 / p)))); half = (b - .05) * math.sin(th)
    return box(name, w, 2 * half, .045, (-L / 2 + L * s_, 0, zz), m, bevel=.008)

def rowboat(name='SM_Rowboat', m_out='M_BoatWhite', m_stripe='M_BoatGreen'):
    """a 4.2 m clinker-style rowing boat: painted planking, varnished inside, three thwarts, floorboards, oars, rowlocks"""
    L, B, D, fb, sh, tr, p = 4.2, 1.45, .32, .3, .2, .5, .6
    P, O = hull(name, L, B, D, fb, sh, tr, p, m_out=m_out, m_in='M_BoatWood', m_rim='M_BoatWood')
    _fix_outward(P[0]); _fix_outward(P[1], True)
    for k, (s_, w) in enumerate(((.12, .3), (.48, .24), (.8, .2))): P.append(_thwart(f'{name}_th{k}', L, B, D, fb, sh, tr, p, s_, .26, w))
    P.append(box(f'{name}_floor', 2.3, .56, .03, (-.1, 0, -.13), 'M_WoodLight', bevel=0))
    for k in range(4): P.append(box(f'{name}_rib{k}', .05, .6, .04, (-1.0 + k * .62, 0, -.16), 'M_WoodDark', bevel=0))
    # a painted sheer stripe just under the gunwale
    for side in (0, len(O[0]) - 1):
        pts = [O[i][side] for i in range(len(O))]
        for i in range(len(pts) - 1):
            a_, b_ = pts[i], pts[i + 1]; mx = ((a_[0] + b_[0]) / 2, (a_[1] + b_[1]) / 2 * 1.006, (a_[2] + b_[2]) / 2 - .07)
            ln = math.hypot(b_[0] - a_[0], b_[1] - a_[1])
            ob = box(f'{name}_st{side}_{i}', ln + .01, .012, .07, mx, m_stripe, bevel=0)
            ob.rotation_euler = (0, -math.atan2(b_[2] - a_[2], ln), math.atan2(b_[1] - a_[1], b_[0] - a_[0])); P.append(ob)
    # oars shipped inside, rowlocks on the gunwale
    for sgn in (-1, 1):
        P.append(cyl(f'{name}_oar{sgn}', .025, 2.6, (-1.25, sgn * .28, -.12), 'M_WoodLight', rot=(0, math.pi / 2, 0), seg=8))
        P.append(box(f'{name}_blade{sgn}', .55, .14, .015, (1.38, sgn * .28, -.13), 'M_WoodLight', bevel=0))
        b, g, d = _hull_dims(.48, L, B, D, fb, sh, tr, p)
        P.append(cyl(f'{name}_lock{sgn}', .018, .1, (-L / 2 + L * .55, sgn * (b - .02), g + .04), 'M_Iron', seg=6))
    P.append(cyl(f'{name}_ring', .05, .02, (L / 2 - .1, 0, _hull_dims(.97, L, B, D, fb, sh, tr, p)[1] - .05), 'M_Iron', rot=(math.pi / 2, 0, 0), seg=8))
    return join(P, name)

def fishing_boat(name='SM_FishingBoat'):
    """an 8 m inshore fishing boat: blue hull with a red boot-top, deck, aft wheelhouse with windows, a short mast with a
    derrick, net drum, fish boxes, rubbing strake, tyres as fenders"""
    L, B, D, fb, sh, tr, p = 8.0, 2.7, .75, .85, .38, .62, .5
    P, O = hull(name, L, B, D, fb, sh, tr, p, m_out='M_BoatBlue', m_in='M_BoatWhite', m_rim='M_BoatWood', ns=32)
    _fix_outward(P[0]); _fix_outward(P[1], True)
    # deck at 0.45 m above the waterline (polygon strip that follows the inner planking)
    zd = .45; bm = bmesh.new(); L_ = []; R_ = []
    for i in range(33):
        s_ = i / 32; b, g, d = _hull_dims(s_, L, B, D, fb, sh, tr, p)
        th = math.acos(min(1.0, max(0.0, ((g - zd) / (g + d - .05)) ** (1 / p)))); h_ = max(.0, (b - .05) * math.sin(th))
        x = -L / 2 + L * s_ + (.05 if i == 0 else 0); L_.append(bm.verts.new((x, -h_, zd))); R_.append(bm.verts.new((x, h_, zd)))
    for i in range(32):
        try: bm.faces.new((L_[i], L_[i + 1], R_[i + 1], R_[i]))
        except ValueError: pass
    bm.normal_update(); ob = mesh_obj(name + '_deck', bm); set_mat(ob, 'M_BoatWood'); _fix_outward(ob, True); P.append(ob)
    # wheelhouse (aft), windows, roof, mast + derrick, net drum, fish boxes, tyre fenders
    wx = -L / 2 + 2.3
    P.append(box(name + '_wh', 1.9, 1.7, 1.75, (wx, 0, zd), 'M_BoatWhite', bevel=.03))
    P.append(box(name + '_whroof', 2.2, 1.95, .08, (wx, 0, zd + 1.75), 'M_BoatBlue', bevel=.02))
    for sgn in (-1, 1): P.append(box(f'{name}_wins{sgn}', 1.2, .03, .5, (wx + .1, sgn * .86, zd + 1.05), 'M_Glass', bevel=0))
    P.append(box(name + '_winf', .03, 1.3, .55, (wx + .96, 0, zd + 1.05), 'M_Glass', bevel=0))
    P.append(box(name + '_door', .03, .62, 1.45, (wx - .96, 0, zd + .05), 'M_Door', bevel=0))
    P.append(cyl(name + '_mast', .07, 4.6, (wx + 1.6, 0, zd), 'M_WoodDark', seg=10))
    boom = cyl(name + '_boom', .05, 3.2, (wx + 1.6, 0, zd + 2.1), 'M_WoodDark', seg=8); boom.rotation_euler = (0, math.radians(62), 0); P.append(boom)
    P.append(cyl(name + '_light', .09, .2, (wx + 1.6, 0, zd + 4.6), 'M_LampGlass', seg=8))
    P.append(cyl(name + '_drum', .3, 1.0, (-L / 2 + .8, .5, zd + .4), 'M_Iron', rot=(math.pi / 2, 0, 0), seg=14))
    P.append(cyl(name + '_net', .27, .9, (-L / 2 + .8, .45, zd + .4), 'M_TrainGreen', rot=(math.pi / 2, 0, 0), seg=14))
    for k, (x, y) in enumerate(((.8, .5), (.8, -.3), (1.5, .4), (1.45, -.4), (.95, .1))):
        P.append(box(f'{name}_fb{k}', .6, .4, .28, (x, y, zd + (.28 if k == 4 else 0)), 'M_Red' if k % 2 else 'M_Siding_White', bevel=.02))
    for k in range(3):
        for sgn in (-1, 1):
            b, g, d = _hull_dims(.3 + k * .18, L, B, D, fb, sh, tr, p)
            P.append(cyl(f'{name}_tyre{k}{sgn}', .2, .1, (-L / 2 + L * (.3 + k * .18), sgn * (b + .07), g - .45), 'M_Iron', rot=(math.pi / 2, 0, 0), seg=12))
    return join(P, name)

def sailboat(name='SM_Sailboat'):
    """a 6.5 m day sailer: cream hull, mast with a gaff-less mainsail and a jib (double-sided), a little cuddy, tiller"""
    L, B, D, fb, sh, tr, p = 6.5, 2.1, .55, .62, .26, .55, .5
    P, O = hull(name, L, B, D, fb, sh, tr, p, m_out='M_BoatRed', m_in='M_BoatWood', m_rim='M_BoatWood', ns=30)
    _fix_outward(P[0]); _fix_outward(P[1], True)
    zd = .2
    P.append(box(name + '_cock', 3.2, 1.2, .03, (-.9, 0, zd), 'M_BoatWood', bevel=0))
    P.append(box(name + '_cuddy', 1.8, 1.5, .55, (1.2, 0, zd + .1), 'M_BoatWhite', bevel=.06))
    for sgn in (-1, 1): P.append(box(f'{name}_seat{sgn}', 2.6, .32, .05, (-1.0, sgn * .62, zd + .38), 'M_WoodDark', bevel=.01))
    mx = .9; H = 7.6
    P.append(cyl(name + '_mast', .06, H, (mx, 0, zd + .65), 'M_WoodLight', seg=10))
    boom = cyl(name + '_boom', .045, 3.3, (mx, 0, zd + 1.55), 'M_WoodLight', seg=8); boom.rotation_euler = (0, -math.pi / 2, 0); P.append(boom)
    P.append(cyl(name + '_tiller', .03, 1.0, (-L / 2 + .1, 0, zd + .6), 'M_WoodDark', rot=(0, -math.pi / 2 - .2, 0), seg=6))
    def sail(nm, pts, bulge):
        bm = bmesh.new(); a, b_, c = [Vector(q) for q in pts]; nu = 8; rows = []
        for i in range(nu + 1):
            u = i / nu; row = []
            for j in range(nu + 1 - i):
                v = j / nu; w = 1 - u - v; q = a * w + b_ * u + c * v
                q.y += bulge * 4 * w * (u + v) * (1 - (u + v)) * 2.2; row.append(bm.verts.new(q))
            rows.append(row)
        for i in range(nu):
            for j in range(nu - i):
                bm.faces.new((rows[i][j], rows[i + 1][j], rows[i][j + 1]))
                if j < nu - i - 1: bm.faces.new((rows[i + 1][j], rows[i + 1][j + 1], rows[i][j + 1]))
        back = bmesh.ops.duplicate(bm, geom=list(bm.faces))['geom']
        bmesh.ops.reverse_faces(bm, faces=[g for g in back if isinstance(g, bmesh.types.BMFace)])
        bmesh.ops.translate(bm, vec=Vector((0, .006, 0)), verts=[g for g in back if isinstance(g, bmesh.types.BMVert)])
        ob = mesh_obj(nm, bm); set_mat(ob, 'M_Plaster'); return ob
    P.append(sail(name + '_main', [(mx - .05, 0, zd + 1.6), (mx - 3.2, 0, zd + 1.6), (mx - .05, 0, zd + .65 + H - .2)], .18))
    P.append(sail(name + '_jib', [(mx + .1, 0, zd + 1.0), (L / 2 - .05, 0, zd + .7), (mx + .1, 0, zd + .65 + H * .8)], .12))
    return join(P, name)

def pier(name='SM_Pier', L=18.0, W=2.4, step=3.0):
    """a timber pier on driven piles: deck planks with gaps, three stringers, a cap beam on every pile bent, diagonal
    bracing, bollards and a ladder at the end. Shore end at y = 0, running to +y; deck top at z = 0."""
    P = []; n = int(L / .26)
    for k in range(n): P.append(box(f'{name}_pl{k}', W, .235, .05, (0, .13 + k * .26, -.05), 'M_WoodLight' if k % 7 else 'M_WoodDark', bevel=.006))
    for x in (-W / 2 + .18, 0, W / 2 - .18): P.append(box(f'{name}_str{x:.1f}', .12, L, .2, (x, L / 2, -.25), 'M_WoodDark', bevel=.01))
    nb = int(L / step) + 1
    for k in range(nb):
        y = min(L - .2, .3 + k * step)
        P.append(box(f'{name}_cap{k}', W + .5, .24, .22, (0, y, -.47), 'M_WoodDark', bevel=.012))
        for sgn in (-1, 1): P.append(cyl(f'{name}_pile{k}{sgn}', .14, 6.6, (sgn * (W / 2 + .1), y, -6.6), 'M_WoodDark', seg=10))
        if k < nb - 1:
            for sgn in (-1, 1):
                br = box(f'{name}_br{k}{sgn}', .08, math.hypot(step, 1.6), .14, (sgn * (W / 2 + .26), y + step / 2, -1.45), 'M_WoodDark', bevel=0)
                br.rotation_euler = (math.atan2(1.6, step) * (1 if k % 2 else -1), 0, 0); P.append(br)
    for k, (x, y) in enumerate(((-W / 2 + .2, L - .35), (W / 2 - .2, L - .35), (W / 2 - .2, L * .5), (-W / 2 + .2, L * .5))):
        P.append(cyl(f'{name}_bol{k}', .13, .45, (x, y, 0), 'M_Iron', seg=12)); P.append(cyl(f'{name}_bolc{k}', .17, .05, (x, y, .45), 'M_Iron', seg=12))
    for sgn in (-1, 1): P.append(box(f'{name}_lad{sgn}', .06, .06, 2.3, (sgn * .25, L + .06, -2.3), 'M_Iron', bevel=0))
    for k in range(6): P.append(box(f'{name}_rung{k}', .5, .04, .04, (0, L + .06, -2.1 + k * .38), 'M_Iron', bevel=0))
    return join(P, name)

def _smooth_line(pts, step=2.0):
    C = [pts[0]] + pts + [pts[-1]]; out = []
    for i in range(1, len(C) - 2):
        p0, p1, p2, p3 = C[i - 1], C[i], C[i + 1], C[i + 2]
        n = max(1, int(math.hypot(p2[0] - p1[0], p2[1] - p1[1]) / step))
        for k in range(n):
            t = k / n; t2 = t * t; t3 = t2 * t
            out.append(tuple(.5 * (2 * p1[c] + (-p0[c] + p2[c]) * t + (2 * p0[c] - 5 * p1[c] + 4 * p2[c] - p3[c]) * t2 + (-p0[c] + 3 * p1[c] - 3 * p2[c] + p3[c]) * t3) for c in (0, 1)))
    out.append(pts[-1]); return out

# the two harbour arms (world metres, Blender): they start buried in the beach and curve round to a 24 m entrance
HARBOUR_W = [(-46.0, 36.0), (-48.0, 58.0), (-42.0, 80.0), (-27.0, 93.0), (-14.0, 98.0)]
HARBOUR_E = [(36.0, 36.0), (38.0, 60.0), (32.0, 81.0), (19.0, 93.0), (10.0, 97.0)]
def breakwater(name, pts, top=.8, half_top=1.7, half_bot=4.4, foot=-5.0):
    """a rubble-stone harbour arm: trapezoid section swept along the smoothed line (top paved), a round head at the
    sea end. World coordinates; placed at (0, 0, 0)."""
    L = _smooth_line(pts); bm = bmesh.new(); prof = [(-half_bot, foot), (-half_top, top), (half_top, top), (half_bot, foot)]
    rings = []
    for i, (x, y) in enumerate(L):
        a = L[min(i + 1, len(L) - 1)]; b = L[max(i - 1, 0)]; tx, ty = a[0] - b[0], a[1] - b[1]; ln = math.hypot(tx, ty) or 1
        nx, ny = -ty / ln, tx / ln
        rings.append([bm.verts.new((x + nx * o, y + ny * o, z)) for (o, z) in prof])
    for i in range(len(rings) - 1):
        for j in range(3): bm.faces.new((rings[i][j], rings[i + 1][j], rings[i + 1][j + 1], rings[i][j + 1]))
    bm.faces.new(rings[0][::-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    topf = set(f for f in bm.faces if f.normal.z > .95)
    for f in bm.faces: f.material_index = 1 if f in topf else 0
    ob = mesh_obj(name + '_arm', bm); ob.data.materials.clear(); ob.data.materials.append(mat('M_HarbourStone')); ob.data.materials.append(mat('M_Quay'))
    ex, ey = L[-1]
    head = bmesh.new(); bmesh.ops.create_cone(head, cap_ends=True, segments=28, radius1=half_bot + .3, radius2=half_top + .2, depth=top - foot)
    bmesh.ops.translate(head, vec=Vector((ex, ey, (top + foot) / 2)), verts=head.verts)
    hob = mesh_obj(name + '_head', head); set_mat(hob, 'M_HarbourStone')
    lamp = [cyl(name + '_lp', .18, 3.2, (ex, ey, top), 'M_Iron', seg=10), cyl(name + '_lpg', .28, .45, (ex, ey, top + 3.2), 'M_LampGlass', seg=10),
            cyl(name + '_lpc', .34, .12, (ex, ey, top + 3.65), 'M_Red', seg=10)]
    bol = []
    for k in range(4, len(L) - 3, 6):
        x, y = L[k]; bol.append(cyl(f'{name}_b{k}', .14, .4, (x, y, top), 'M_Iron', seg=10))
    return join([ob, hob] + lamp + bol, name)

def stream_bridge(name='SM_StreamBridge', L=16.0, W=3.4):
    """the farm road over the stream: a timber deck on two trestle bents and stone abutments, railings both sides.
    Along X; deck top at z = 0; centre at the origin."""
    P = []
    for k in range(int(L / .3)): P.append(box(f'{name}_pl{k}', .27, W, .07, (-L / 2 + .15 + k * .3, 0, -.07), 'M_WoodLight' if k % 5 else 'M_WoodDark', bevel=.006))
    for y in (-W / 2 + .3, -.5, .5, W / 2 - .3): P.append(box(f'{name}_str{y:.1f}', L, .16, .28, (0, y, -.35), 'M_WoodDark', bevel=.01))
    for bx in (-3.4, 3.4):
        P.append(box(f'{name}_cap{bx}', .3, W + .5, .26, (bx, 0, -.61), 'M_WoodDark', bevel=.01))
        for y in (-W / 2 - .05, 0, W / 2 + .05): P.append(cyl(f'{name}_pile{bx}{y:.1f}', .15, 3.6, (bx, y, -4.2), 'M_WoodDark', seg=10))
        for sgn in (-1, 1):
            br = box(f'{name}_x{bx}{sgn}', .08, math.hypot(W, 1.6), .12, (bx + .2, 0, -1.55), 'M_WoodDark', bevel=0); br.rotation_euler = (sgn * math.atan2(1.6, W), 0, 0); P.append(br)
    for sgn in (-1, 1):
        P.append(box(f'{name}_abut{sgn}', 2.4, W + 1.0, 2.6, (sgn * (L / 2 - 1.0), 0, -2.66), 'M_Stone', bevel=.05))
        for k in range(12):
            x = -L / 2 + .3 + k * (L - .6) / 11
            P.append(box(f'{name}_post{sgn}{k}', .12, .12, 1.05, (x, sgn * (W / 2 - .06), 0), 'M_WoodDark', bevel=.01))
        P.append(box(f'{name}_rail{sgn}', L - .4, .1, .1, (0, sgn * (W / 2 - .06), .98), 'M_WoodLight', bevel=.01))
        P.append(box(f'{name}_mid{sgn}', L - .4, .06, .08, (0, sgn * (W / 2 - .06), .5), 'M_WoodDark', bevel=0))
    return join(P, name)

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
        {'id': 'fisher', 'outfit': 'fisher', 'hair_color': [0.65, 0.65, 0.65], 'name': 'Old Fisher Gus', 'body': 'm', 'hair': 'Hair_Beard', 'anim': 'Idle_Rail_Loop', **spot(9.6, 50.2, .27, (0, 1))},
        {'id': 'gardener', 'outfit': 'gardener', 'hair_color': [0.55, 0.22, 0.08], 'name': 'Gardener Ines', 'body': 'f', 'hair': 'Hair_Buns', 'anim': 'Farm_Watering', **spot(19.5, .2, None, (1, 0))},
        {'id': 'merchant', 'outfit': 'merchant', 'hair_color': [0.05, 0.04, 0.04], 'name': 'Fruit Seller Dora', 'body': 'f', 'hair': 'Hair_BuzzedFemale', 'anim': 'Idle_Talking_Loop', **spot(-5.4, -19.6, None, (1, 0))},
        {'id': 'kid', 'outfit': 'kid', 'hair_color': [0.85, 0.62, 0.2], 'name': 'Little Leo', 'body': 'm', 'hair': 'Hair_Buzzed', 'anim': 'Idle_Loop', 'scale': .72, **spot(3.2, -17.6, None, (-1, -.3))},
        {'id': 'conductor', 'outfit': 'conductor', 'hair_color': [0.4, 0.38, 0.36], 'name': 'Conductor Mabel', 'body': 'f', 'hair': 'Hair_Buns', 'anim': 'Idle_Loop', **spot(36.6, 9.5, height(36.5, 9.5) + .55, (-1, 0))},
        {'id': 'guard', 'outfit': 'guard', 'hair_color': [0.06, 0.05, 0.05], 'name': 'Gate Warden Bo', 'body': 'm', 'hair': 'Hair_SimpleParted', 'anim': 'Idle_FoldArms_Loop', **spot(-44.6, 9.4, None, (1, 0))}]
    for (cid, nm, tag, body, hair, hcol, anim, (sx, sy, sz), syaw, sc) in BOAT_CREW:
        bx, by = next((b[2], b[3]) for b in SEA_BOATS if b[0] == tag)
        G['npcs'].append({'id': cid, 'outfit': 'fisher', 'hair_color': hcol, 'name': nm, 'body': body, 'hair': hair, 'anim': anim, 'scale': sc,
                          'pos': _ue(bx, by, 0.0), 'yaw': 0.0, 'boat': tag, 'seat': _ue(sx, sy, sz + .92 * sc), 'seat_yaw': syaw})
    G['sea_boats'] = [dict(tag=t, mode=m) for (t, _, _, _, _, m) in SEA_BOATS if m != 'sail'] + \
                     [dict(tag=t, mode='sail', center=_ue(*SAIL_LOOP['center'], -1.2), rx=SAIL_LOOP['rx'] * 100, ry=SAIL_LOOP['ry'] * 100, period=SAIL_LOOP['period'])
                      for (t, _, _, _, _, m) in SEA_BOATS if m == 'sail']
    G['spots'] = {'rho_greet': spot(-12.6, 3.6, None, (-1, -.4)), 'rho_gate': spot(-42.5, 3.4, None, (1, .3)),
                  'starter_table': _ue(lc['c'][0], lc['c'][1] - 3.0, HZ + .95), 'bed': _ue(hc['c'][0] - 3.3, hc['c'][1] - 2.2, HZ + .5),
                  'battle_center_hint': _ue(-36, 6, 0), 'from_route1': spot(GATE[0] + 4.0, GATE[1], None, (1, 0))}
    G['grass'] = [{'min': _ue(x0, y1, 0)[:2], 'max': _ue(x1, y0, 0)[:2]} for (x0, y0, x1, y1) in TALL_GRASS]   # (y flips sign)
    G['wild_spawns'] = [_ue(x, y, height(x, y)) for (x, y) in [(-40, -5), (-33, -2), (-37, 14), (-41, 15.5), (-34, 1)]]
    G['gate'] = {'pos': _ue(GATE[0], GATE[1], height(*GATE)), 'exit_x': round((GATE[0] - 3.0) * 100, 1), 'barrier_mesh': 'fence-gate'}
    G['bounds'] = {'center': _ue(0, -8, 0)[:2], 'radius': 9000.0, 'water_z': -110.0, 'safe': spot(0, 10),
                   # walkable beyond the circle: the Lamplighters' Path (4 m each side) and the farm hamlet across the stream
                   'paths': [{'pts': [_ue(x, y, 0)[:2] for (x, y) in TRAIL], 'w': 400.0},
                             {'pts': [_ue(x, y, 0)[:2] for (x, y) in [(REST[0] - 6, REST[1]), (REST[0] + 6, REST[1])]], 'w': 1300.0},
                             {'pts': [_ue(x, y, 0)[:2] for (x, y) in [(64, 29), (64, -26)]], 'w': 2400.0},
                             {'pts': [_ue(ISLAND[0] - 60, ISLAND[1], 0)[:2], _ue(ISLAND[0] + 60, ISLAND[1], 0)[:2]], 'w': 9500.0}]}
    # the rowboat (phase 3): where it starts, and the places you can step ashore (water spot for the boat, land spot for you)
    jx, jy, jl = ISLAND_PIER
    G['boat'] = {'start': _ue(11.7, 52.0, -1.2), 'yaw': _yaw(0, 1), 'radius': 260000.0,
                 'docks': [{'name': 'Lumen Harbor pier', 'water': _ue(11.7, 52.0, -1.2), 'land': spot(9.0, 49.0, .3, (0, -1))},
                           {'name': 'Lighthouse Island jetty', 'water': _ue(jx + 2.8, jy - jl + 4.0, -1.2),
                            'land': {'pos': _ue(jx, jy - jl + 6.0, 1.1), 'yaw': _yaw(0, 1)}}]}
    G['map'] = 'L_Town'; G['title'] = 'LUMEN HARBOR'
    # walking out through the (re-opened) Route 1 gate loads the Route 1 level; min_step 7 = EPBXStep::Gate (licence signed)
    G['exits'] = [{'id': 'route1', 'pos': _ue(GATE[0] - 3.2, GATE[1], height(GATE[0] - 3.2, GATE[1])), 'radius': 260.0, 'to_map': 'L_Route1', 'to_spot': 'from_lumen',
                   'min_step': 7, 'label': 'Route 1'}]
    def gz(x, y): return height(x, y) if (abs(x) < 108 and abs(y) < 108) else real_height(x, y)
    G['notes'] = [{'pos': _ue(x, y, gz(x, y) + 1.0), 'text': t} for ((x, y), t) in LORE_NOTES]
    G['signs'] = [{'pos': _ue(x, y, gz(x, y) + 1.15), 'yaw': _yaw(fx, fy), 'text': t} for ((x, y), (fx, fy), t) in LORE_SIGNS] + [{'pos': _ue(GATE[0] + 2.5, GATE[1] + 3.6, height(GATE[0] + 2.5, GATE[1] + 3.6) + 1.15), 'yaw': _yaw(1, 0), 'text': 'ROUTE 1\nwest to Mistvale'},
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
# realistic pass (2026-10-22): Poly Haven photo-scanned plants / rocks / props replace the painted ones in and around the village
PHM = '/Game/PBX/PH/'
def _ph(asset, mesh): return PHM + f'{asset}/{asset}_2k/StaticMeshes/{mesh}'
PH_GRASS = [_ph('grass_medium_01', f'grass_medium_01_{k}_LOD0') for k in ('large_a', 'large_b', 'large_c', 'mid_a', 'mid_b', 'tall_a', 'tall_b')] + \
           [_ph('grass_medium_02', f'grass_medium_02_{k}') for k in ('c', 'd', 'e')]
PH_TALL = [_ph('grass_medium_01', f'grass_medium_01_{k}_LOD0') for k in ('tall_a', 'tall_b', 'tall_c', 'large_a', 'large_b')] + [_ph('grass_medium_02', 'grass_medium_02_e')]
PH_FLOWERS = [_ph('dandelion_01', f'dandelion_01_{k}_LOD0') for k in 'abc'] + [_ph('celandine_01', f'celandine_01_{k}_LOD0') for k in 'abcd']
PH_FERN = [_ph('fern_02', f'fern_02_{k}') for k in 'abcd']
PH_SHRUB = [_ph('shrub_02', f'shrub_02_{k}') for k in 'abcd']
PH_ROCK_S = [_ph('rock_moss_set_02', f'rock_moss_set_02_rock{i:02d}') for i in range(7, 14)]
PH_ROCK_L = [_ph('rock_moss_set_01', f'rock_moss_set_01_rock{i:02d}') for i in range(1, 7)] + [_ph('boulder_01', 'boulder_01_2k')]
PH_BARREL = _ph('Barrel_01', 'Barrel_01_2k'); PH_CRATE = _ph('wooden_crate_01', 'wooden_crate_01'); PH_PLANTER = _ph('planter_box_01', 'planter_box_01_2k')
PH_BENCH = _ph('painted_wooden_bench', 'painted_wooden_bench_2k'); PH_FIRE = _ph('stone_fire_pit', 'stone_fire_pit_2k'); PH_STUMP = _ph('tree_stump_01', 'tree_stump_01_2k')
PH_BUCKET = _ph('wooden_bucket_01', 'wooden_bucket_01'); PH_TABLE = _ph('outdoor_table_chair_set_01', 'outdoor_table_chair_set_01_table')
PH_CHAIRS = [_ph('outdoor_table_chair_set_01', 'outdoor_table_chair_set_01_chair_01'), _ph('outdoor_table_chair_set_01', 'outdoor_table_chair_set_01_chair_02')]
FVP_FENCES = ['/Game/Fantastic_Village_Pack/meshes/props/construction/SM_PROP_fence_v02_0%d' % i for i in (1, 2, 3)]
GRASS, FLOWERS, ROCKS_S, ROCKS_L, BUSHES = PH_GRASS, PH_FLOWERS, PH_ROCK_S, PH_ROCK_L, PH_SHRUB

# ------------------------------------------------------------------ Fantastic Village Pack (Fab): stylized houses + props
FVP = '/Game/Fantastic_Village_Pack/'
FVM = FVP + 'meshes/props/'
def FVP_HOUSE(i): return FVP + f'blueprints/buildings/BP_BLD_house_{i}'
# ground-floor door of each house blueprint, in Blender local metres (Unreal (dx, dy) cm -> (dx/100, -dy/100)), measured in the editor
FVP_DOORS = {1: (0.0, 2.79), 2: (0.0, -2.79), 5: (0.0, -5.63), 9: (-2.52, 0.0), 10: (-2.48, 0.0), 14: (-.03, 2.79),
             4: (5.70, 0.0), 7: (0.10, 5.69), 8: (-6.53, 0.28), 11: (5.64, 0.0), 12: (-2.74, 0.02)}   # measured 2026-10-22 (ground-floor door meshes)
# older kit props -> Fantastic Village Pack equivalents (one consistent hand-painted style). Value: (mesh, default size)
SWAP = {
    'SM_LampPost': (FVM + 'light/SM_PROP_streetlamp_v01_01', {'h': 3.6}), 'SM_Bench': (FVM + 'furniture/SM_PROP_bench_01', {'w': 1.9}),
    'SM_Bin': (FVM + 'container/SM_PROP_barrel_02', {'h': .95}), 'SM_Mailbox': (FVM + 'deco/SM_PROP_mailbox', {'h': 1.25}),
    'QProps/Stall_Empty': (FVM + 'construction/SM_PROP_market_v01_01', {'h': 2.8}), 'QProps/Stall_Cart_Empty': (FVM + 'vehicles/SM_PROP_cart_01', {'h': 1.8}),
    'QProps/FarmCrate_Apple': (FVM + 'food/SM_PROP_crate_02', {'h': .5}), 'QProps/FarmCrate_Carrot': (FVM + 'food/SM_PROP_crate_03', {'h': .5}),
    'QProps/Barrel_Apples': (FVM + 'container/SM_PROP_barrel_05', {'h': 1.0}), 'QProps/Crate_Wooden': (FVM + 'container/SM_PROP_box_01', {'h': .7}),
    'QProps/Barrel': (FVM + 'container/SM_PROP_barrel_01', {'h': 1.0}), 'QProps/Bucket_Wooden_1': (FVM + 'container/SM_PROP_bucket_01', {'h': .4}),
    'QProps/Pot_1': (FVM + 'natural/SM_PROP_PLANT_pot_v1_01', {'h': .6}), 'QProps/Workbench': (FVM + 'furniture/SM_PROP_table_01', {'h': .9}),
    'KTown/cart': (FVM + 'vehicles/SM_PROP_cart_02', {'h': 1.6}), 'KSurvival/resource_wood': (FVM + 'natural/SM_PROP_treetrunk_01', {'w': 1.4}),
    'KSurvival/signpost': (FVM + 'deco/SM_PROP_signpost_01', {'h': 2.2}), 'KSurvival/campfire_pit': (FVM + 'light/SM_PROP_campfire', {'w': 1.5}),
    'KSurvival/tree_log_small': (FVM + 'natural/SM_PROP_treetrunk_02', {'w': 1.5}), 'KPirate/boat_row_small': (FVM + 'vehicles/SM_PROP_rowboat', {'w': 3.2}),
    'KPirate/boat_row_large': (FVM + 'vehicles/SM_PROP_rowboat', {'w': 3.8}), 'KPirate/structure_platform_dock': (FVM + 'construction/SM_PROP_walkway_wood', {'w': 6.0}),
    'SM_Sign': (FVM + 'deco/SM_PROP_board_01', {'w': 1.9}),   # the procedural board rendered black (S7)
    'KTown/pillar-stone': (FVM + 'construction/SM_PROP_wall_wood_post_01', {'h': 3.4}), 'KTown/fence-gate': (FVM + 'construction/SM_PROP_fence_door_gate', {'w': 4.0}),
}
def swap(mesh):
    return SWAP.get(mesh, (mesh, None))

# ------------------------------------------------------------------ Poly Haven glTF inventory (mesh names + sizes), so
# the plan can use the real scanned assets without hard-coding their part names
PH_DIR = os.path.join(OUT, 'polyhaven', 'models')
_PHINV = {}
def ph_meshes(asset):
    """[(mesh name, (sx, sy, sz) metres)] of a downloaded Poly Haven model (glTF, Y-up). Empty if not downloaded."""
    if asset in _PHINV: return _PHINV[asset]
    out = []
    try:
        d = os.path.join(PH_DIR, asset); f = [n for n in os.listdir(d) if n.endswith('.gltf')][0]
        g = json.load(open(os.path.join(d, f), encoding='utf-8'))
        for nd in g.get('nodes', []):                 # Unreal names the static meshes after the glTF nodes
            if 'mesh' not in nd: continue
            m = g['meshes'][nd['mesh']]; sc = nd.get('scale', [1, 1, 1])
            lo = [1e9] * 3; hi = [-1e9] * 3
            for pr in m['primitives']:
                a = g['accessors'][pr['attributes']['POSITION']]
                lo = [min(lo[i], a['min'][i]) for i in range(3)]; hi = [max(hi[i], a['max'][i]) for i in range(3)]
            out.append((nd['name'], ((hi[0] - lo[0]) * sc[0], (hi[2] - lo[2]) * sc[2], (hi[1] - lo[1]) * sc[1])))
    except Exception as ex: print('ph_meshes', asset, ex)
    _PHINV[asset] = out; return out
def ph_path(asset, mesh): return PHM + f'{asset}/{asset}_2k/StaticMeshes/{mesh}'

def _fbm(x, y, seed=0.0):
    return (math.sin(x * .013 + seed) * math.cos(y * .011 - seed * .7) + .55 * math.sin(x * .031 - y * .027 + seed * 1.3)
            + .3 * math.sin(x * .071 + y * .059 + seed * 2.1)) / 1.85

def mountain_forest(add, railway):
    """2026-10-23 b: a real montane conifer forest (Poly Haven fir scans, instanced). Rules taken from the Bernese
    Oberland: closed spruce/fir forest on the lower and middle slopes, densest in the gullies and on the shaded north
    faces; it thins and the trees shrink towards an irregular tree line (~1900 m real = ~72 m here); nothing on rock
    faces steeper than ~40 deg, on scree or snow; pastures (open meadow) around the village and along the valley floor,
    avalanche tracks as open stripes down the steep slopes. Trees are life size near the village and scale towards
    1:12 on the far mountains so the relief keeps its scale."""
    firs = [m for m in ph_meshes('fir_tree_01') if m[1][2] > 3.0]
    saps = [m for m in ph_meshes('fir_sapling_medium') if m[1][2] > .8]
    old = [NAT + 'SM_Pine_Tree_1', NAT + 'SM_Pine_Tree_2']
    dem_load(); n = 0; Rf = random.Random(23)
    def spot_ok(x, y):
        if y > coast_y(x) - 8 or (abs(x) < 112 and abs(y) < 112): return False
        if railway(x, y, 6) or (abs(x - TRACK_X) < 22 and TRACK_Y0 - 6 < y < TRACK_Y0 + 30): return False   # cutting + portal stay clear
        if 25 < x < 240 and -520 < y < 95:
            d_, t_, _ = river_query(x, y)
            if d_ < river_width(t_) / 2 + 4.5: return False
        if trail_dist(x, y) < 3.6 or math.hypot(x - REST[0], y - REST[1]) < 15: return False
        return True
    cells = []
    for gy in range(-950, 300, 5):                   # 5 m grid near the village, 8 m beyond 450 m
        for gx in range(-950, 951, 5):
            if 118 <= math.hypot(gx, gy + 10) < 450: cells.append((gx, gy, 5.0))
    for gy in range(-1000, 300, 8):
        for gx in range(-1000, 1001, 8):
            if 450 <= math.hypot(gx, gy + 10) < 1000: cells.append((gx, gy, 8.0))
    for (gx, gy, step) in cells:
        if True:
            d = math.hypot(gx, gy + 10)
            x = gx + Rf.uniform(-.45, .45) * step; y = gy + Rf.uniform(-.45, .45) * step
            if d < 118 or d > 1000 or not spot_ok(x, y): continue
            z = real_height(x, y)
            if z < 1.5: continue
            e = 3.0; sx = real_height(x + e, y) - real_height(x - e, y); sy = real_height(x, y + e) - real_height(x, y - e)
            slope = math.hypot(sx, sy) / (2 * e)
            tl = 70.0 + 9.0 * _fbm(x, y, 4.0)                                   # irregular tree line
            dens = 1.0 - _ss(.62, .9, slope)                                    # no trees on rock faces
            dens *= 1.0 - _ss(tl - 10, tl + 3, z)                               # thinning to the tree line
            dens *= _ss(-.75, -.3, _fbm(x, y, 1.0))                             # meadows / clearings (~15 % of the slopes)
            dens *= 1.0 - .85 * _ss(.45, .6, slope) * _ss(.55, .8, math.sin(x * .09 + _fbm(x, y, 7.0) * 3.0))  # avalanche tracks
            dens *= .25 + .75 * _ss(.35, .75, real_weight(x, y))               # pastures near the village
            if sy < 0: dens = min(1.0, dens * 1.15)                             # shaded north-facing slopes are lusher
            if Rf.random() > min(1.0, dens * 1.1): continue
            scale = 1.0 - .55 * _ss(220, 620, d)                                # life size near the village -> ~1:2.2 far away
            krumm = 1.0 - .45 * _ss(tl - 18, tl, z)
            h = Rf.uniform(14.0, 26.0) * scale * krumm
            if firs and h > 7.0:
                m = Rf.choice(firs); add(ph_path('fir_tree_01', m[0]), x, y, Rf.random() * 360, 1.0, z - .35)
            elif saps:
                m = Rf.choice(saps); add(ph_path('fir_sapling_medium', m[0]), x, y, Rf.random() * 360, 1.0, z - .2); h = min(h, Rf.uniform(4.0, 8.0))
            else:
                add(Rf.choice(old), x, y, Rf.random() * 360, 1.0, z - .3)
            o = P_CUR[0]['objects'][-1]; o['h'] = round(h, 2); o['inst'] = True; o['snap'] = False; n += 1
            # undergrowth: young firs at the forest edge
            if dens < .55 and saps and Rf.random() < .35:
                m = Rf.choice(saps); ox, oy = x + Rf.uniform(-2.5, 2.5), y + Rf.uniform(-2.5, 2.5)
                add(ph_path('fir_sapling_medium', m[0]), ox, oy, Rf.random() * 360, 1.0, real_height(ox, oy) - .15)
                o = P_CUR[0]['objects'][-1]; o['h'] = round(Rf.uniform(1.5, 4.0) * scale, 2); o['inst'] = True; o['snap'] = False; n += 1
    print('mountain forest', n, 'trees')
P_CUR = [None]

# ------------------------------------------------------------------ the harbour + the island (2026-10-23 b)
PIER = 'modular_wooden_pier'
def pier_line(x, y, dx, dy, length, deck_z):
    """a Poly Haven wooden pier (photo-scanned planks, posts, rope lashings) from (x, y) along (dx, dy): the modular
    sections chained every 2.92 m. pbx_build seats each section so its deck top sits at deck_z ('pier' objects)."""
    L = math.hypot(dx, dy); ux, uy = dx / L, dy / L; n = max(2, int(round(length / 2.92)))
    # the sections are authored in place along the asset's -Y (Unreal), 2.92 m apart, deck top 2.67 m above the pivot:
    # each copy is shifted back by its own authored offset so they chain
    seq = [0] + [1 if k % 2 == 0 else 2 for k in range(n - 2)] + [3]
    yaw = round(math.degrees(math.atan2(ux, uy)), 2)
    out = []
    for i, j in enumerate(seq):
        d = (i - j) * 2.92
        out.append(dict(mesh=ph_path(PIER, f'{PIER}_section_0{j + 1}'), x=round(x + ux * d, 3), y=round(y + uy * d, 3), z=round(deck_z - 2.67, 3),
                        rot=0.0, s=1.0, snap=False, pier=True, yaw_ue=yaw))
    return out

# boats on the water. tag -> how the C++ moves it (moored in the harbour, anchored in the bay, sailing a loop)
SEA_BOATS = [  # (tag, mesh, x, y, facing (dx, dy), mode)
    ('PBX_Boat', 'SM_Rowboat', 11.7, 52.0, (0, 1), 'moored'),                 # yours (rows from the pier)
    ('PBX_Bob_1', 'SM_FishingBoat', -21.9, 51.5, (0, 1), 'moored'),           # the Pelling family's boat, at the west pier
    ('PBX_Bob_2', 'SM_RowboatB', -28.4, 47.5, (.2, 1), 'moored'),
    ('PBX_Bob_3', 'SM_RowboatB', 6.3, 56.0, (-.1, 1), 'moored'),
    ('PBX_Bob_4', 'SM_FishingBoat', -135.0, 245.0, (.8, .6), 'anchored'),     # out in the bay, nets over the side
    ('PBX_Bob_5', 'SM_Rowboat', 118.0, 196.0, (-.7, .7), 'anchored'),          # an old man fishing from his rowboat
    ('PBX_Sail_1', 'SM_Sailboat', 240.0, 430.0, (0, 1), 'sail')]
SAIL_LOOP = dict(center=(0.0, 430.0), rx=240.0, ry=115.0, period=260.0)
# crews: (id, name, boat tag, body, hair, hair colour, anim, local seat (x fwd, y left, z) m, seat yaw deg, scale)
BOAT_CREW = [
    ('crew_jon', 'Jon Pelling', 'PBX_Bob_1', 'm', 'Hair_SimpleParted', [.3, .2, .1], 'Fixing_Kneeling', (1.7, .2, .45), 200, 1.0),
    ('crew_ada', 'Ada Pelling', 'PBX_Bob_4', 'f', 'Hair_Buns', [.55, .3, .12], 'Fixing_Kneeling', (1.5, -.3, .45), 90, 1.0),
    ('crew_ben', 'Ben Pelling', 'PBX_Bob_4', 'm', 'Hair_Beard', [.2, .14, .1], 'Idle_Rail_Loop', (-2.4, -.55, .45), 90, 1.0),
    ('crew_old', 'Old Harlan', 'PBX_Bob_5', 'm', 'Hair_Beard', [.8, .8, .8], 'Sitting_Idle_Loop', (-.08, 0, -.33), 180, 1.0),
    ('crew_sail', 'Wren', 'PBX_Sail_1', 'f', 'Hair_Long', [.75, .55, .25], 'Sitting_Idle_Loop', (-1.9, -.62, .21), -90, 1.0),
    ('crew_kid', 'Pip', 'PBX_Sail_1', 'm', 'Hair_Buzzed', [.85, .62, .2], 'Sitting_Talking_Loop', (-.6, .62, .21), 90, .72)]

def harbour(P, add, kit, house):
    """two rubble-stone arms enclose a small harbour with two wooden piers; fishing boats and rowboats moored inside,
    more out in the bay. The island: lighthouse on the north-east point, keeper's cottage, jetty in the north cove."""
    O = P['objects']
    O.append(dict(mesh='SM_BreakwaterW', x=0, y=0, z=0.0, rot=0.0, s=1.0, snap=False))
    O.append(dict(mesh='SM_BreakwaterE', x=0, y=0, z=0.0, rot=0.0, s=1.0, snap=False))
    # armour stones along the seaward faces (half under water), photo-scanned coastal rocks
    rocks = [m for m in ph_meshes('coast_rocks_05')] + [m for m in ph_meshes('coast_land_rocks_04')]
    big = [ph_path('coast_rocks_05', m[0]) for m in ph_meshes('coast_rocks_05')] or PH_ROCK_L
    Rr = random.Random(5)
    for pts, sgn in ((HARBOUR_W, -1), (HARBOUR_E, 1)):
        L = _smooth_line(pts, 3.0)
        for i in range(2, len(L)):
            x, y = L[i]; a = L[min(i + 1, len(L) - 1)]; b = L[i - 1]; tx, ty = a[0] - b[0], a[1] - b[1]; ln = math.hypot(tx, ty) or 1
            nx, ny = -ty / ln, tx / ln
            cx_, cy_ = -4.0, 72.0                                     # harbour centre: armour goes on the other side
            if (x + nx - cx_) ** 2 + (y + ny - cy_) ** 2 < (x - nx - cx_) ** 2 + (y - ny - cy_) ** 2: nx, ny = -nx, -ny
            if y < 44: continue
            for k in range(2):
                o_ = Rr.uniform(3.6, 5.2) + k * 1.6
                add(Rr.choice(big), x + nx * o_ + Rr.uniform(-.6, .6), y + ny * o_ + Rr.uniform(-.6, .6), Rr.random() * 360, 1.0, -1.4 - k * .6)
                O[-1]['h'] = round(Rr.uniform(1.4, 2.4), 2); O[-1]['snap'] = False
    # piers: the main pier (your rowboat, Old Fisher Gus) and the west pier (fishing boats)
    O.extend(pier_line(9.0, 40.5, 0, 1, 18.0, .25))
    O.extend(pier_line(-25.0, 40.5, 0, 1, 15.0, .25))
    # mooring poles, buoys, lifebuoys, tyres, barrels and crates on the piers, harbour lamps on the arm heads
    for (x, y) in ((14.5, 60.0), (-19.0, 57.5), (-31.0, 54.0)):
        kit(ph_path(PIER, f'{PIER}_poles'), x, y, Rr.random() * 360, h=4.2, z=-2.9)
    for k, (x, y) in enumerate(((-6.0, 75.0), (22.0, 70.0), (-34.0, 70.0))):
        kit(ph_path('ocean_buoy', 'ocean_buoy') if ph_meshes('ocean_buoy') else PH_BARREL, x, y, Rr.random() * 360, h=1.6, z=-1.6)
    kit(ph_path('lateral_sea_marker', 'lateral_sea_marker') if ph_meshes('lateral_sea_marker') else PH_BARREL, -1.0, 108.0, 0, h=4.5, z=-2.2)
    for (x, y, r) in ((10.15, 47.0, 90), (-23.85, 46.0, 90)):
        kit(ph_path('lifebuoy', 'lifebuoy') if ph_meshes('lifebuoy') else PH_BARREL, x, y, r, h=.8, z=.25 + .55)
    for (m, x, y, r, h_) in ((ph_path('wooden_barrels_01', ph_meshes('wooden_barrels_01')[0][0]) if ph_meshes('wooden_barrels_01') else PH_BARREL, 8.2, 43.5, 20, 1.0),
                             (ph_path('wooden_crate_02', 'wooden_crate_02') if ph_meshes('wooden_crate_02') else PH_CRATE, -25.6, 43.0, 10, .5),
                             (PH_CRATE, -24.3, 44.6, 40, .5), (PH_BUCKET, 9.6, 49.0, 0, .35)):
        kit(m, x, y, r, h=h_, z=.25)
    for (x, y) in ((-10.0, 41.0), (24.0, 41.0)):
        kit(ph_path('street_lamp_01', 'street_lamp_01') if ph_meshes('street_lamp_01') else 'SM_LampPost', x, y, 0, h=4.2)
    # boats (waterline at z = 0 in the meshes -> placed at sea level; the C++ makes them ride the swell)
    for (tag, mesh, x, y, (fx, fy), mode) in SEA_BOATS:
        z = -1.2
        O.append(dict(mesh=mesh, x=x, y=y, z=z, rot=round(math.degrees(math.atan2(fy, fx)), 2), s=1.0, snap=False, tag=tag))
    # one rowboat pulled up on the beach, keel in the sand
    O.append(dict(mesh='SM_Rowboat', x=-8.0, y=44.0, z=round(height(-8.0, 44.0) + .12, 3), rot=-62.0, s=1.0, snap=False))
    # ---- the island
    lx_, ly_ = LIGHTHOUSE
    O.append(dict(mesh='SM_Lighthouse', x=lx_, y=ly_, z=round(island_h(lx_, ly_) - .3, 3), rot=0.0, s=1.0, snap=False))
    house(2, COTTAGE_DOOR[0], COTTAGE_DOOR[1], COTTAGE_FACE); O[-1]['z'] = round(island_h(*COTTAGE_DOOR), 3)
    jx, jy, jl = ISLAND_PIER
    O.extend(pier_line(jx, jy, 0, -1, jl, 1.05))
    cx_, cy_ = COTTAGE_C
    # the keeper's yard: low fence round a vegetable plot and a washing line, wood pile, bench facing the sea at the lighthouse
    for k in range(7):
        a_ = math.radians(110 + k * 22); O_ = (cx_ + 8.5 * math.cos(a_), cy_ + 8.5 * math.sin(a_))
        add(R.choice(FVP_FENCES), O_[0], O_[1], math.degrees(a_) + 90); O[-1].pop('h', None); O[-1]['w'] = 3.3
    for (m, dx, dy, r, h_) in ((PH_PLANTER, -3.0, 6.0, 0, None), (PH_PLANTER, -.6, 6.4, 0, None), (FVM + 'deco/SM_PROP_clothesline_01', 3.5, 6.5, 0, 2.0),
                               (FVM + 'deco/SM_PROP_firepit_woodpile', 6.0, -2.0, 70, 1.0), (PH_BARREL, 5.5, 1.5, 0, None), (PH_BUCKET, 5.0, 2.3, 0, None)):
        if h_: kit(m, cx_ + dx, cy_ + dy, r, h=h_)
        else: add(m, cx_ + dx, cy_ + dy, r, 1.0)
    add(PH_BENCH, lx_ - 3.0, ly_ - 6.0, 200, 1.0)
    kit('/Game/PBX/PH/Lantern_01/Lantern_01_2k/StaticMeshes/Lantern_01', lx_ - 4.2, ly_ + .6, 0, h=.35)
    for (m, dx, dy, r, h_) in ((PH_CRATE, 2.0, 1.0, 20, None), (PH_BARREL, -2.0, 1.4, 0, None), (PH_CRATE, 2.3, 2.1, 50, None)):
        add(m, jx + dx, jy + dy, r, 1.0)
    kit('KSurvival/signpost', jx + 2.4, jy + 4.0, 30, h=2.0)
    # shore: scanned coastal rocks ringing the island (half in the water), heavier on the exposed south / east
    Ri = random.Random(41)
    for k in range(90):
        a_ = Ri.random() * math.tau; best = None
        for rr in [r_ / 100 for r_ in range(70, 160, 3)]:
            x_, y_ = ISLAND[0] + math.cos(a_) * 150 * rr, ISLAND[1] + math.sin(a_) * 110 * rr
            if island_h(x_, y_) < .3: best = (x_, y_); break
        if not best or math.hypot(best[0] - jx, best[1] - (jy - 10)) < 22: continue
        add(Ri.choice(big), best[0], best[1], Ri.random() * 360, 1.0, island_h(*best) - .8); O[-1]['h'] = round(Ri.uniform(1.0, 3.2), 2); O[-1]['snap'] = False
    # firs: wind-bent clumps on the sheltered south-west slopes; low shrubs; meadow grass + flowers everywhere else
    firs = [m for m in ph_meshes('fir_tree_01') if m[1][2] > 3.0]; saps = ph_meshes('fir_sapling_medium')
    clumps = [(185.0, 1478.0, 16), (215.0, 1515.0, 14), (262.0, 1520.0, 10), (176.0, 1430.0, 9), (300.0, 1490.0, 8)]
    for (gx_, gy_, n_) in clumps:
        for k in range(n_):
            x_, y_ = gx_ + Ri.gauss(0, 9), gy_ + Ri.gauss(0, 7); z_ = island_h(x_, y_)
            if z_ < 2.0 or island_path_dist(x_, y_) < 3 or math.hypot(x_ - cx_, y_ - cy_) < 14 or math.hypot(x_ - lx_, y_ - ly_) < 12: continue
            if firs and Ri.random() < .7: m = ph_path('fir_tree_01', Ri.choice(firs)[0]); h_ = Ri.uniform(7, 13)
            elif saps: m = ph_path('fir_sapling_medium', Ri.choice(saps)[0]); h_ = Ri.uniform(2.5, 5)
            else: m = NAT + 'SM_Pine_Tree_1'; h_ = Ri.uniform(6, 10)
            add(m, x_, y_, Ri.random() * 360, 1.0, z_ - .3); O[-1]['h'] = round(h_, 2); O[-1]['inst'] = True; O[-1]['snap'] = False
    gr = [ph_path('grass_bermuda_01', m[0]) for m in ph_meshes('grass_bermuda_01')] + PH_GRASS
    for k in range(5200):
        u_, v_ = Ri.uniform(-1, 1), Ri.uniform(-1, 1)
        x_, y_ = ISLAND[0] + u_ * 160, ISLAND[1] + v_ * 120; z_ = island_h(x_, y_)
        if z_ < 1.0 or island_path_dist(x_, y_) < 1.3 or math.hypot(x_ - cx_, y_ - cy_) < 7.5 or math.hypot(x_ - lx_, y_ - ly_) < 5: continue
        r_ = Ri.random()
        m = Ri.choice(gr) if r_ < .82 else (Ri.choice(PH_FLOWERS) if r_ < .94 else Ri.choice(PH_SHRUB))
        add(m, x_, y_, Ri.random() * 360, 1.4 + Ri.random() * .8 if r_ < .94 else 1.0, z_ - .05); O[-1]['inst'] = True; O[-1]['snap'] = False


def plan_town():
    P = {'paths': [(0, -24, 0, 48, 3.6), (-24, 6, 24, 6, 3.0), (-15, 6, -15, 0, 2.2), (15, 6, 15, 0, 2.2), (-24, 6, -52, 6, 3.0),
                   (24, 6, 34.4, 6, 3.0), (30, 6, 30, .8, 2.2),
                   (1.8, 15.5, 6.2, 15.5, 2.0), (1.8, 31, 5.8, 31, 2.2), (-1.8, 15.0, -6.2, 15.0, 2.0), (22, -15, 22, -13, 2.2), (22, -13, 1.8, -13, 2.2),
                   (-11.1, -16.2, -1.8, -16.2, 2.0),
                   # phase 2: harbour lane, the road east over the railway end and the stream bridge to the farm hamlet, cottages
                   (-1.8, 36.0, -36.0, 36.0, 2.6), (-14.0, 33.5, -14.0, 36.0, 1.8), (-30.0, 33.5, -30.0, 36.0, 1.8),
                   (24.0, 6.0, 30.0, 14.0, 2.6), (30.0, 14.0, 32.0, 28.0, 2.6), (32.0, 28.0, 46.0, 29.0, 2.6), (46.0, 29.0, 64.0, 29.0, 2.6),
                   (64.0, 29.0, 64.0, -26.0, 2.4), (64.0, 0.0, 68.0, 0.0, 1.8), (64.0, -22.0, 68.0, -22.0, 1.8), (64.0, 12.0, 82.0, 12.0, 2.0), (82.0, 12.0, 82.0, 14.0, 1.8),
                   (-13.0, -46.0, -16.0, -42.0, 1.8), (-16.0, -42.0, -16.0, -24.0, 2.0), (-16.0, -24.0, -1.8, -24.0, 2.0),
                   (14.0, -44.0, 14.0, -31.0, 2.0), (14.0, -31.0, 5.0, -31.0, 2.0), (5.0, -31.0, 5.0, -26.0, 2.0),
                   (-36.0, -46.0, -48.0, -62.0, 1.8), (-48.0, -62.0, -62.0, -82.0, 1.8)],
         'objects': []}
    P_CUR[0] = P
    def add(mesh, x, y, rot=0.0, s=1.0, z=None):
        # snap = sits on the outdoor ground: Unreal re-measures the real ground under its footprint (no floating / sinking)
        mesh, size = swap(mesh)
        P['objects'].append(dict(mesh=mesh, x=round(x, 3), y=round(y, 3), z=round(height(x, y) if z is None else z, 3), rot=round(rot, 2), s=round(s, 3), snap=z is None))
        if size: P['objects'][-1].update(size)
    def house(i, door_x, door_y, face=(0.0, 1.0)):
        """a Fantastic Village house blueprint placed so its ground-floor door is at (door_x, door_y), facing `face`"""
        lx, ly = FVP_DOORS[i]; L = math.hypot(lx, ly); ox, oy = lx / L, ly / L
        phi = math.atan2(face[1], face[0]) - math.atan2(oy, ox); c, s_ = math.cos(phi), math.sin(phi)
        rx, ry = lx * c - ly * s_, lx * s_ + ly * c
        P['objects'].append(dict(mesh=FVP_HOUSE(i), x=round(door_x - rx, 3), y=round(door_y - ry, 3), z=round(height(door_x, door_y), 3), rot=round(math.degrees(phi), 2), s=1.0, snap=False))
    # homes and the lab: Fantastic Village houses, doors exactly where the game's door spots are (fronts face the street, +y)
    house(10, -15, -1.45); house(2, 15, -1.45); house(5, 0, -28.45)
    add('SM_Mailbox', -12.3, 2.2, 90); add('SM_Mailbox', 17.7, 2.2, 90)
    add('SM_Sign', 4, 9, 0); add('SM_Sign', -4, -20, 0); add('SM_Sign', 26.5, 9.2, 0)
    for x in (-6, 6):
        for y in (-12, 14, 30): add('SM_LampPost', x * .55, y)
    for x in (12, 21, 29): add('SM_LampPost', x, 8.2)
    add('SM_Bench', 8, -18, 180); add('SM_Bin', 10, -18)
    # ---- more of a village (2026-10-22): five more Fantastic Village houses on the streets, doors onto paths (not enterable)
    for (i_, dx_, dy_, face_) in NEW_HOUSES + NEW_HOUSES2: house(i_, dx_, dy_, face_)
    for (wx_, wy_) in WINDMILLS: house(14, wx_, wy_)                         # windmills (door south)
    # ---- railway: station building, platform, track from the tunnel in the north to the buffer stop, the train at the platform
    house(9, 29.5, .55)   # the station building (no door interaction)
    house(14, -66, -26)   # windmill on the west hill
    x0, x1, y0, y1 = PLATFORM; add('SM_Platform', (x0 + x1) / 2, (y0 + y1) / 2, 0)
    add('SM_Track', TRACK_X, (TRACK_Y0 + TRACK_Y1) / 2, 0, z=0.0)
    add('SM_Tunnel', TRACK_X, TRACK_Y0, 0, z=0.0)
    for (m, y) in (('SM_TrainLoco', -12.6), ('SM_TrainCar', 2.0), ('SM_TrainCar', 16.4)):   # 15 m loco + two 14 m coaches
        add(m, TRACK_X, y, 0, z=.40); P['objects'][-1]['tag'] = 'PBX_Train'
    def fence(x, y, rot):
        add(R.choice(FVP_FENCES), x, y, rot); P['objects'][-1].pop('h', None); P['objects'][-1]['w'] = 3.3
    # ---- garden fences (Fantastic Village fence, 3.3 m) around the two houses
    for cx in (-15, 15):
        for k in (-2, -1, 1, 2):
            fence(cx + k * 3.3 + (-.9 if k < 0 else .9), 3.0, 0)
        for k in range(3): fence(cx - 7.4 * (1 if cx < 0 else -1), 1.4 - k * 3.3 - 1.6, 90)
    for k in range(6): fence(8.6 + k * 3.3, 22, 0)
    # ---- nature (Fab packs), kept off paths, houses, the railway and the beach
    blocked = [(-15, -5, 8.5), (15, -5, 8.5), (0, -34, 13), (6, -34, 11), (-47, 6, 7), (29.5, -2.2, 7), (0, -20.5, 4.5), (-32, -38, 8), (-66, -26, 10), (9.5, -16.5, 2.5)] + [(x_, y_, r_) for (x_, y_, r_) in NEW_HOUSE_BLOCKS + NEW_HOUSE_BLOCKS2] + [(wx_, wy_ - 2.8, 10.0) for (wx_, wy_) in WINDMILLS]
    def in_grass(x, y, pad=0.0): return any(x0 - pad < x < x1 + pad and y0 - pad < y < y1 + pad for (x0, y0, x1, y1) in TALL_GRASS)
    def railway(x, y, pad=0.0): return (abs(x - TRACK_X) < 7 + pad and y < TRACK_Y1 + 3) or (PLATFORM[0] - 3 - pad < x < 46 and PLATFORM[2] - 3 < y < PLATFORM[3] + 3)
    def free(x, y, r=1.5, far=False):
        if path_mask(x, y, P) > .05: return False
        if in_grass(x, y, r + .5) or railway(x, y, r): return False
        if y > 38: return False
        if not far and (abs(x) > 104 or abs(y) > 104): return False
        if trail_dist(x, y) < 2.6 + r or math.hypot(x - REST[0], y - REST[1]) < 13 + r: return False
        if 30 < x < 235 and -500 < y < 90:          # keep the stream and its banks clear
            d_, t_, _ = river_query(x, y)
            if d_ < river_width(t_) / 2 + 3.0 + r: return False
        return all(math.hypot(x - bx, y - by) > br + r for bx, by, br in blocked)
    n = 0
    while n < 190:                       # forest ring around the village
        a = R.random() * math.tau; d = 46 + R.random() * 55; x, y = math.cos(a) * d, math.sin(a) * d - 10
        if y > 34 or not free(x, y, 2.5): continue
        add(R.choice(TREES_FOREST), x, y, R.random() * 360, .8 + R.random() * .35); n += 1
    mountain_forest(add, railway)
    for x, y in [(-27, -14), (-26, 4), (31, -12), (-24, 19), (24, 18), (-40, 27), (27, 35), (-6, 40), (50, -10), (76, 24), (58, -40)]:
        add(R.choice(TREES_TOWN), x, y, R.random() * 360, .62 + R.random() * .12)      # big feature trees in the village
    n = 0
    while n < 150:                       # bushes
        x, y = (R.random() - .5) * 100, (R.random() - .5) * 92 - 6
        if not free(x, y, 1.2): continue
        add(R.choice(BUSHES), x, y, R.random() * 360, .65 + R.random() * .45); n += 1
    n = 0
    while n < 950:                       # grass clumps + wild flowers (Poly Haven scans, life size)
        x, y = (R.random() - .5) * 110, (R.random() - .5) * 96 - 8
        if not free(x, y, .35): continue
        k = R.random()
        if k < .7: add(R.choice(GRASS), x, y, R.random() * 360, 1.4 + R.random() * 1.0)
        elif k < .92: add(R.choice(FLOWERS), x, y, R.random() * 360, 1.4 + R.random() * .8)
        else: add(R.choice(PH_FERN), x, y, R.random() * 360, 1.0 + R.random() * .6)
        n += 1
    for cx in (-15, 15):                 # flower beds in the front gardens
        for k in range(26): add(R.choice(FLOWERS), cx + (R.random() - .5) * 12, 0.6 + R.random() * 1.6, R.random() * 360, 1.8)
    for k in range(26):                  # small rocks along the paths and at the forest edge
        a = R.random() * math.tau; d = 34 + R.random() * 30; x, y = math.cos(a) * d, math.sin(a) * d - 10
        if not free(x, y, 1.0): continue
        add(R.choice(ROCKS_S), x, y, R.random() * 360, .35 + R.random() * .35)
    for k in range(14):                  # cliffs and big rocks on the hill rim (north, west, east)
        a = math.radians(-180 + 180 * k / 13 + R.uniform(-4, 4)); d = 88 + R.random() * 14; x, y = math.cos(a) * d, math.sin(a) * d - 10
        if not free(x, y, 3): continue
        add(R.choice(ROCKS_L), x, y, R.random() * 360, 1.2 + R.random() * 1.0)
    # ---- kit props (Quaternius Fantasy Props = QProps/, Kenney kits = KTown/ KPirate/ KSurvival/). h / w = target
    # height / footprint in metres; Unreal scales each mesh from its bounds, so the kits' differing units don't matter.
    def kit(mesh, x, y, rot=0.0, h=None, w=None, z=None):
        add(mesh, x, y, rot, 1.0, z); o = P['objects'][-1]
        if h or w: o.pop('h', None); o.pop('w', None)
        if h: o['h'] = h
        if w: o['w'] = w
    # plaza in front of the lab: the town's Relay Stone (Lattice storage relay) on a paved circle + a small market
    kit(FVM + 'deco/SM_PROP_well', 9.5, -16.5, 20, h=3.0)
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
    # new houses: front gardens, wood piles, washing lines, a beer garden at the harbour inn
    for (m, x, y, r, h) in [(PH_PLANTER, 3.6, 13.0, 90, None), (PH_PLANTER, 3.6, 18.0, 90, None), (PH_BARREL, 19.3, 9.0, 0, None), (PH_BUCKET, 19.2, 8.1, 0, None),
                            (FVM + 'deco/SM_PROP_clothesline_01', 20.6, 14.0, 90, 2.0), (FVM + 'natural/SM_PROP_treetrunk_03', 20.4, 10.4, 90, 1.0),
                            (PH_TABLE, 2.9, 25.0, 0, None), (PH_CHAIRS[0], 2.9, 24.2, 0, None), (PH_CHAIRS[1], 2.9, 25.8, 180, None),
                            (PH_TABLE, 2.9, 36.0, 0, None), (PH_CHAIRS[0], 2.9, 35.2, 0, None), (PH_CHAIRS[1], 2.9, 36.8, 180, None),
                            (PH_BARREL, 2.6, 27.6, 0, None), (PH_BARREL, 2.7, 28.4, 40, None), (FVM + 'deco/SM_PROP_sign_02', 2.6, 29.6, 90, 1.6),
                            (PH_PLANTER, -2.3, 12.8, 90, None), (PH_PLANTER, -2.3, 17.4, 90, None), (PH_BENCH, -2.4, 20.6, 90, None),
                            (FVM + 'natural/SM_PROP_hay_02', -21.0, 24.0, 20, 1.2), (PH_STUMP, -19.6, 10.4, 0, None), (PH_CRATE, -19.8, 12.6, 80, None),
                            (FVM + 'deco/SM_PROP_firepit_woodpile', -21.4, -12.4, 0, 1.0), (PH_PLANTER, -10.4, -13.0, 0, None), (PH_BUCKET, -10.0, -19.6, 0, None),
                            (PH_BENCH, 16.5, -11.2, 0, None), (PH_PLANTER, 25.6, -12.4, 0, None), (FVM + 'deco/SM_PROP_clothesline_02', 31.4, -24.0, 90, 2.0),
                            (PH_CRATE, 11.5, -33.0, 0, None), (PH_BARREL, 12.2, -34.4, 0, None), (FVM + 'container/SM_PROP_trough_01', 13.8, -20.0, 90, .6)]:
        if h: kit(m, x, y, r, h=h)
        else: add(m, x, y, r, 1.0)
    # ---- the Lamplighters' Path (2026-10-23): walled by pines so it is the only way up, the old Rest with the keepers'
    # graves, notes and carved signs, the cairn on the ridge; beyond it the forest closes (and the bounds corridor ends)
    def trail_z(x, y): return height(x, y) if (abs(x) < 108 and abs(y) < 108) else real_height(x, y)
    PINES = [NAT + 'SM_Pine_Tree_1', NAT + 'SM_Pine_Tree_2']
    acc = 0.0
    for (ax, ay), (bx, by) in zip(TRAIL[:-1], TRAIL[1:]):
        L = math.hypot(bx - ax, by - ay); ux, uy = (bx - ax) / L, (by - ay) / L; nx, ny = -uy, ux; d = 0.0
        while d < L:
            x, y = ax + ux * d, ay + uy * d
            if math.hypot(x - REST[0], y - REST[1]) > 15 and math.hypot(x - TRAIL[0][0], y - TRAIL[0][1]) > 9:
                for side in (-1, 1):
                    for row, off in enumerate((R.uniform(3.4, 4.4), R.uniform(6.0, 7.5))):
                        tx, ty = x + nx * off * side + ux * R.uniform(-1, 1), y + ny * off * side + uy * R.uniform(-1, 1)
                        if trail_dist(tx, ty) < 3.0: continue
                        add(R.choice(PINES), tx, ty, R.random() * 360, 1.0); P['objects'][-1]['h'] = round(R.uniform(8.0, 13.0), 2)
                if int((acc + d) / 7.0) != int((acc + d - 3.2) / 7.0):
                    side = R.choice((-1, 1)); add(R.choice(PH_ROCK_S), x + nx * 2.2 * side, y + ny * 2.2 * side, R.random() * 360, .5 + R.random() * .4)
            d += 3.2
        acc += L
    # the Rest: a fenced little graveyard, the keepers' table with the ledger, a lantern, the cold fire pit
    rx, ry = REST
    for k, (gx_, gy_) in enumerate([(1.5, -5.5), (-1.5, -6.0), (4.5, -4.5), (-4.5, -5.0)]):
        kit(GRV + str(k + 1), rx + gx_, ry + gy_, 180 + R.uniform(-8, 8), h=1.0 + R.random() * .4)
    for k in range(8):
        a_ = math.pi * (1.1 + .8 * k / 7); fence(rx + math.cos(a_) * 8.0, ry - 5.2 + math.sin(a_) * 3.0 + 3.0, math.degrees(a_) + 90)
    kit(FVM + 'furniture/SM_PROP_table_01', rx - 3.5, ry + 3.5, 20, h=.85)
    kit(FVM + 'deco/SM_PROP_paper_01', rx - 3.5, ry + 3.5, 35, w=.32, z=trail_z(rx - 3.5, ry + 3.5) + .86)
    kit(FVM + 'deco/SM_PROP_scroll', rx - 3.1, ry + 3.8, 80, w=.35, z=trail_z(rx - 3.1, ry + 3.8) + .86)
    add(PH_CRATE, rx - 6.5, ry + 1.0, 30, 1.0); kit(FVM + 'deco/SM_PROP_paper_03', rx - 6.5, ry + 1.0, -10, w=.3, z=trail_z(rx - 6.5, ry + 1.0) + .33)
    add(PH_FIRE, rx + 2.5, ry + 4.5, 0, 1.0); add(PH_BENCH, rx + 5.0, ry + 4.5, 90, 1.0); add(PH_STUMP, rx + 1.0, ry + 7.0, 0, .8)
    kit('/Game/PBX/PH/Lantern_01/Lantern_01_2k/StaticMeshes/Lantern_01', rx - 3.9, ry + 3.2, 0, h=.3, z=trail_z(rx - 3.9, ry + 3.2) + .86)
    kit(FVM + 'deco/SM_PROP_hangingboard', rx + 6.5, ry + 1.0, -60, h=2.4)
    # the cairn on the ridge (the end of the path) and the torn page under it
    cx_, cy_ = TRAIL[-1]
    for k, (dz_, sc_) in enumerate(((0.0, 1.0), (.55, .75), (1.0, .5))):
        kit(PH_ROCK_S[k], cx_ + .3 * k, cy_ - .2 * k, R.random() * 360, h=.6 * sc_ + .2, z=trail_z(cx_, cy_) + dz_)
    kit(FVM + 'deco/SM_PROP_paper_02', cx_ - 1.0, cy_ + 1.2, 15, w=.3)
    # beyond the cairn the forest closes: three rows of pines and boulders in an arc around the end of the path
    for k in range(34):
        a_ = math.radians(-160 + 140 * (k % 17) / 16.0 + R.uniform(-3, 3)); rr = 4.5 + 2.6 * (k // 17) + R.uniform(0, .8)
        tx, ty = cx_ + math.cos(a_) * rr, cy_ + math.sin(a_) * rr
        add(R.choice(PINES), tx, ty, R.random() * 360, 1.0); P['objects'][-1]['h'] = round(R.uniform(9.0, 14.0), 2)
    for k in range(6):
        a_ = math.radians(-150 + 120 * k / 5); add(R.choice(PH_ROCK_L), cx_ + math.cos(a_) * 3.6, cy_ + math.sin(a_) * 3.6, R.random() * 360, 1.1)
    # carved signs on the path (the lettering is drawn by the game from G['signs'])
    for ((sx_, sy_), (fx_, fy_), _t) in LORE_SIGNS:
        kit(FVM + 'deco/SM_PROP_board_01', sx_, sy_, math.degrees(math.atan2(fy_, fx_)) - 90, w=1.9)
    # timber trestle bridge where the east road crosses the stream (deck flush with the road)
    P['objects'].append(dict(mesh='SM_StreamBridge', x=54.4, y=29.0, z=round(max(height_raw(46.5, 29.0), height_raw(62.5, 29.0)) + .1, 3), rot=0.0, s=1.0, snap=False))
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
    harbour(P, add, kit, house)
    kit('KSurvival/campfire_pit', -15.0, 42.5, 0, w=1.4)
    for a in (0, 120, 240):
        kit('KSurvival/tree_log_small', -15.0 + 1.8 * math.cos(math.radians(a)), 42.5 + 1.8 * math.sin(math.radians(a)), a + 90, w=1.6)
    for (m, x, y, sc) in [(ROCKS_S[2], 22, 45, 1.0), (ROCKS_S[0], -35, 44, 1.1), (ROCKS_L[5], 44, 47, .9)]:
        add(m, x, y, R.random() * 360, sc)
    # ---- west road: tall grass where the wild Echoes live, and the Route 1 gate (closed: landslide — the train is the way out)
    for (x0, y0, x1, y1) in TALL_GRASS:
        n = int((x1 - x0) * (y1 - y0) * .55)
        for k in range(n):
            x, y = x0 + R.random() * (x1 - x0), y0 + R.random() * (y1 - y0)
            add(R.choice(PH_TALL), x, y, R.random() * 360, 2.2 + R.random() * .8)
    gx, gy = GATE
    for s_ in (-1, 1): kit('KTown/pillar-stone', gx, gy + s_ * 2.3, 0, h=3.2)
    kit('KTown/fence-gate', gx, gy, 90, w=4.0)                         # the barrier
    P['objects'][-1]['tag'] = 'PBX_GateBarrier'
    for (dx, dy, sc) in [(-3.5, 0, 1.1), (-6, 2, .95)]:                 # the landslide behind the gate (cleared once the licence is signed)
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
    P['water'] = dict(x=0, y=0, z=-1.2)
    P['terrain'] = ['SM_Ground', 'SM_Mountains', 'SM_Island']
    P['objects'].append(dict(mesh='SM_River', x=0, y=0, z=0.0, rot=0.0, s=1.0, snap=False))
    P['player_start'] = dict(x=0, y=10, z=height(0, 10) + 1.0, rot=-90)
    return P

def run():
    reset()
    plan = plan_town()
    export(house('SM_House_Player', 9.0, 7.0, 3.3, 'M_Roof_Red', 'M_Siding_White'), 'SM_House_Player'); reset()
    export(house('SM_House_Rival', 9.5, 7.2, 3.3, 'M_Roof_Red', 'M_Siding_Cream'), 'SM_House_Rival'); reset()
    export(house('SM_Lab', 18.0, 11.0, 6.4, 'M_Roof_Blue', 'M_Siding_White', porch=False, chimney=False, two_storey=True, lab=True), 'SM_Lab'); reset()
    for f in (fence_segment, lamp_post, mailbox, signboard, bench, trash_bin, station_building, platform, track, tunnel_portal, loco, carriage, lighthouse):
        ob = f(); export(ob, ob.name); reset()
    HULLS = ('M_BoatWhite', 'M_BoatBlue', 'M_BoatGreen', 'M_BoatWood', 'M_BoatPeel', 'M_BoatRed')
    for f in (lambda: rowboat(), lambda: rowboat('SM_RowboatB', 'M_BoatPeel', 'M_BoatWhite'), fishing_boat, sailboat):
        ob = f(); export_smooth(ob, ob.name, HULLS); reset()
    for nm, pts in (('SM_BreakwaterW', HARBOUR_W), ('SM_BreakwaterE', HARBOUR_E)):
        ob = breakwater(nm, pts); export(ob, nm); reset()
    ob = stream_bridge(); export(ob, ob.name); reset()
    mountains_real(); reset(); river_mesh(); reset(); island_mesh(); reset(); sky_dome(); reset()   # one terrain (no SM_GroundFar any more)
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
