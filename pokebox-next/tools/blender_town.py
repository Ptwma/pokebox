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
def height(x, y):
    """flat village plateau, soft hills inland, slope down to the beach on the south (+y)"""
    h = 0.0
    h += .35 * math.sin(x * .07) * math.cos(y * .05) + .25 * math.sin(x * .13 + 1.3) * math.sin(y * .11 + .4)
    d = math.hypot(x, y + 10)
    h *= min(1, max(0, (d - 30) / 25))              # village core stays flat
    ring = max(0, d - 70); h += ring * ring * .004  # hills around (forest edge)
    if y > 42: h -= (y - 42) * .32                  # beach slope
    if y > 52: h -= (y - 52) * .25                  # under the sea
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

def water_plane():
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=40, y_segments=20, size=1)
    bmesh.ops.scale(bm, vec=Vector((1600, 700, 1)), verts=bm.verts)
    ob = mesh_obj('SM_Water', bm); set_mat(ob, 'M_Water'); return export(ob, 'SM_Water')

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
def plan_town():
    P = {'paths': [(0, -24, 0, 48, 3.6), (-24, 6, 24, 6, 3.0), (-15, 6, -15, 0, 2.2), (15, 6, 15, 0, 2.2)],
         'objects': []}
    def add(mesh, x, y, rot=0.0, s=1.0, z=None):
        P['objects'].append(dict(mesh=mesh, x=round(x, 3), y=round(y, 3), z=round(height(x, y) if z is None else z, 3), rot=round(rot, 2), s=round(s, 3)))
    add('SM_House_Player', -15, -5, 180); add('SM_House_Rival', 15, -5, 180); add('SM_Lab', 0, -34, 180)  # fronts face the village street (+y)
    add('SM_Mailbox', -12.3, 2.2, 90); add('SM_Mailbox', 17.7, 2.2, 90)
    add('SM_Sign', 4, 9, 0); add('SM_Sign', -4, -20, 0)
    for x in (-6, 6):
        for y in (-12, 14, 30): add('SM_LampPost', x * .55, y)
    add('SM_Bench', 8, -18, 180); add('SM_Bin', 10, -18)
    # garden fences around the two houses and along the path edges
    for cx in (-15, 15):
        for k in range(-3, 4):
            if k == 0: continue
            add('SM_Fence', cx + k * 2.1, 3.0, 0)
        for k in range(5): add('SM_Fence', cx - 7.4 * (1 if cx < 0 else -1), 1.9 - k * 2.1 - 1, 90)
    for k in range(10): add('SM_Fence', 7 + k * 2.1, 22, 0); add('SM_Fence', -7 - k * 2.1, 22, 0)
    # foliage (Quaternius Stylized Nature MegaKit names), kept off paths, houses and the beach
    blocked = [(-15, -5, 8.5), (15, -5, 8.5), (0, -34, 13)]
    def free(x, y, r=1.5):
        if path_mask(x, y, P) > .05: return False
        if y > 38 or abs(x) > 104 or abs(y) > 104: return False
        return all(math.hypot(x - bx, y - by) > br + r for bx, by, br in blocked)
    trees = ['CommonTree_1', 'CommonTree_2', 'CommonTree_3', 'CommonTree_4', 'CommonTree_5']
    n = 0
    while n < 170:                       # forest ring
        a = R.random() * math.tau; d = 44 + R.random() * 55; x, y = math.cos(a) * d, math.sin(a) * d - 10
        if y > 34 or not free(x, y, 2): continue
        add(R.choice(trees + ['Pine_1', 'Pine_2', 'Pine_3']), x, y, R.random() * 360, .9 + R.random() * .5); n += 1
    for x, y in [(-27, -14), (-26, 4), (27, -14), (26, 6), (-11, -40), (11, -42), (-22, 16), (23, 17), (-31, 30), (32, 28)]:
        add(R.choice(trees), x, y, R.random() * 360, 1.0 + R.random() * .3)
    n = 0
    while n < 260:                       # bushes, plants, flowers, grass clumps everywhere near the village
        x, y = (R.random() - .5) * 96, (R.random() - .5) * 90 - 6
        if not free(x, y, .6): continue
        k = R.random()
        m = ('Bush_Common_Flowers' if k < .18 else 'Bush_Common' if k < .32 else 'Plant_1' if k < .42 else 'Fern_1' if k < .5 else
             'Flower_3_Group' if k < .62 else 'Flower_4_Group' if k < .72 else 'Grass_Common_Tall' if k < .86 else 'Grass_Wispy_Tall')
        add(m, x, y, R.random() * 360, .8 + R.random() * .5); n += 1
    for cx in (-15, 15):                 # flower beds in the front gardens
        for k in range(14): add(R.choice(['Flower_3_Group', 'Flower_4_Group', 'Bush_Common_Flowers']), cx + (R.random() - .5) * 12, 0.5 + R.random() * 1.6, R.random() * 360, .7)
    for k in range(40):                  # pebbles and rocks along the paths
        x = (R.random() - .5) * 6; y = -20 + R.random() * 60
        if abs(x) > 2.2: add(R.choice(['Pebble_Round_1', 'Pebble_Round_2', 'Pebble_Square_3', 'Rock_Medium_1']), x, y, R.random() * 360, .6 + R.random() * .5)
    # ---- kit props (Quaternius Fantasy Props = QProps/, Kenney kits = KTown/ KPirate/ KSurvival/). h / w = target
    # height / footprint in metres; Unreal scales each mesh from its bounds, so the kits' differing units don't matter.
    def kit(mesh, x, y, rot=0.0, h=None, w=None, z=None):
        add(mesh, x, y, rot, 1.0, z); o = P['objects'][-1]
        if h: o['h'] = h
        if w: o['w'] = w
    # plaza in front of the lab: fountain + a small market
    kit('KTown/fountain_round', 0, -20.5, 0, w=3.4)
    kit('QProps/Stall_Empty', -6.8, -19.5, 90, h=2.6); kit('QProps/Stall_Cart_Empty', 6.8, -23.5, -90, h=2.1)
    for (m, x, y, r, h) in [('QProps/FarmCrate_Apple', -5.4, -21.4, 10, .45), ('QProps/FarmCrate_Carrot', -5.6, -17.8, -8, .45),
                            ('QProps/Barrel_Apples', -7.9, -22.0, 0, .95), ('QProps/Crate_Wooden', 5.3, -25.4, 15, .7),
                            ('QProps/Crate_Wooden', 5.5, -25.3, 40, .7), ('QProps/Barrel', 8.3, -25.6, 0, 1.0), ('KTown/cart', 9.6, -21.5, 70, 1.4)]:
        kit(m, x, y, r, h=h)
    kit('QProps/Crate_Wooden', 5.4, -25.35, 25, h=.7, z=height(5.4, -25.35) + .7)          # stacked crate
    # lab flanked by hedges
    for s in (-1, 1):
        for k in range(4): kit('KTown/hedge', s * 10.6, -30.5 - k * 2.0, 90, w=2.0)
    # homes: barrels, buckets, flower pots, wood pile
    for (m, x, y, r, h) in [('QProps/Barrel', -20.2, -2.6, 0, 1.0), ('QProps/Bucket_Wooden_1', -19.4, -1.9, 0, .4), ('QProps/Pot_1', -16.9, -.9, 0, .5),
                            ('QProps/Pot_1', -13.1, -.9, 0, .5), ('QProps/Barrel', 20.3, -2.4, 0, 1.0), ('QProps/Barrel', 20.4, -3.6, 30, 1.0),
                            ('QProps/Crate_Wooden', 19.6, -1.5, 12, .7), ('QProps/Pot_1', 13.1, -.9, 0, .5), ('QProps/Pot_1', 16.9, -.9, 0, .5),
                            ('KSurvival/resource_wood', -21.0, -7.0, 90, .6), ('QProps/Workbench', 21.0, -8.0, -90, 1.0)]:
        kit(m, x, y, r, h=h)
    # path ends: signposts towards the routes
    kit('KSurvival/signpost', -23.0, 8.2, 90, h=2.0); kit('KSurvival/signpost', 23.0, 8.2, -90, h=2.0); kit('KSurvival/signpost', 2.6, 40.0, 0, h=2.0)
    # beach: wooden pier, row boats, campfire with log seats, sandy rocks
    kit('KPirate/structure_platform_dock', 9.0, 47.8, 0, w=6.0, z=-.35); kit('KPirate/structure_platform_dock', 9.0, 53.6, 0, w=6.0, z=-.35)
    kit('KPirate/boat_row_small', 13.5, 52.0, 25, w=3.2, z=-1.15); kit('KPirate/boat_row_large', -9.0, 46.2, -60, w=4.2)
    kit('KSurvival/campfire_pit', -15.0, 42.5, 0, w=1.4)
    for a in (0, 120, 240):
        kit('KSurvival/tree_log_small', -15.0 + 1.8 * math.cos(math.radians(a)), 42.5 + 1.8 * math.sin(math.radians(a)), a + 90, w=1.6)
    for (m, x, y, w) in [('KPirate/rocks_sand_a', -25, 47, 2.4), ('KPirate/rocks_sand_b', 22, 45, 2.0), ('KPirate/rocks_sand_c', 30, 49, 3.0), ('KPirate/rocks_sand_a', -34, 44, 2.6)]:
        kit(m, x, y, R.random() * 360, w=w)
    # extra nature from the full Stylized Nature kit: short grass carpet, clover, mushrooms, more tree variety
    n = 0
    while n < 320:
        x, y = (R.random() - .5) * 110, (R.random() - .5) * 96 - 8
        if not free(x, y, .3): continue
        k = R.random()
        if k < .55: kit('Grass_Common_Short', x, y, R.random() * 360, h=.32 + R.random() * .12)
        elif k < .75: kit(R.choice(['Clover_1', 'Clover_2']), x, y, R.random() * 360, w=.6 + R.random() * .4)
        elif k < .83: kit('Plant_7', x, y, R.random() * 360, h=.5 + R.random() * .3)
        elif k < .9: kit(R.choice(['Mushroom_Common', 'Mushroom_Laetiporus']), x, y, R.random() * 360, h=.18)
        else: kit(R.choice(['Petal_1', 'Petal_2', 'Petal_3']), x, y, R.random() * 360, w=.5)
        n += 1
    n = 0
    while n < 40:
        a = R.random() * math.tau; d = 50 + R.random() * 50; x, y = math.cos(a) * d, math.sin(a) * d - 10
        if y > 34 or not free(x, y, 2): continue
        add(R.choice(['Pine_4', 'Pine_5', 'TwistedTree_1', 'TwistedTree_3', 'CommonTree_5']), x, y, R.random() * 360, .9 + R.random() * .4); n += 1
    P['water'] = dict(x=0, y=380, z=-1.2)
    P['player_start'] = dict(x=0, y=10, z=height(0, 10) + 1.0, rot=-90)
    return P

def run():
    reset()
    plan = plan_town()
    export(house('SM_House_Player', 9.0, 7.0, 3.3, 'M_Roof_Red', 'M_Siding_White'), 'SM_House_Player'); reset()
    export(house('SM_House_Rival', 9.5, 7.2, 3.3, 'M_Roof_Red', 'M_Siding_Cream'), 'SM_House_Rival'); reset()
    export(house('SM_Lab', 18.0, 11.0, 6.4, 'M_Roof_Blue', 'M_Siding_White', porch=False, chimney=False, two_storey=True, lab=True), 'SM_Lab'); reset()
    for f in (fence_segment, lamp_post, mailbox, signboard, bench, trash_bin):
        ob = f(); export(ob, ob.name); reset()
    water_plane(); reset()
    painted_textures()
    ground(plan); reset(); splat(plan)
    with open(os.path.join(OUT, 'town_plan.json'), 'w') as fh: json.dump(plan, fh, indent=1)
    print('town built:', len(plan['objects']), 'placements')

if __name__ == '__main__' or True:
    run()
