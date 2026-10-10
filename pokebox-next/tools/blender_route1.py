# Pokebox Next — Route 1 generator (runs inside Blender 5.x, bpy). Reuses the town's helpers (blender_town.py).
# A 340 m valley road from the Lumen Harbor gate (east) to the Mistvale gate (west): tall grass with wild Echoes,
# three sight-line trainers, a Ranger Rest stop (healer + trader), hidden items, forest and mountains either side.
# Output: fbx/SM_R1_*.fbx, tex/T_R1Splat.png, route1_plan.json (pbx_build.build_level) and Content/PBX/Data/L_Route1.json.
# Coordinates: metres, Blender Z-up, x east / y north. Unreal: x_ue = x*100, y_ue = -y*100.
import bpy, bmesh, math, json, os, random, importlib.util
from mathutils import Vector

_here = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else r"E:\GAME-APP-DEV\POKEMON\PokeboxNext_src\tools"
os.environ['PBX_TOWN_NORUN'] = '1'
try:
    _spec = importlib.util.spec_from_file_location('blender_town', os.path.join(_here, 'blender_town.py'))
    T = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(T)
finally:
    os.environ.pop('PBX_TOWN_NORUN', None)

OUT, FBX = T.OUT, T.FBX
R = random.Random(11)

# ------------------------------------------------------------------ layout
PATH = [(16, 0), (-30, 0), (-60, -12), (-95, -14), (-125, 4), (-150, 18), (-185, 14), (-215, -4), (-245, -14), (-280, -6), (-312, 0), (-336, 0)]
PATH_W = 4.0
WALL0 = 20.0                       # the valley floor is flat-ish this far from the road, then the sides climb
AREA = (-390.0, 70.0, -200.0, 200.0)   # ground mesh x0, x1, y0, y1
SPLAT_C, SPLAT_S = (-160.0, 0.0), 460.0  # splat texture square (centre, size) — must match pbx_build (M_PBX_GroundR1)
EAST_GATE, WEST_GATE = (10.0, 0.0), (-328.0, 0.0)
REST = (-198.0, 31.0)              # Ranger Rest hut (front faces the road, south)
PLAZA = (-198.0, 22.5, 7.5)        # flagstone circle in front of it

def seg_dist(x, y, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]; L2 = max(1e-6, dx * dx + dy * dy)
    t = max(0.0, min(1.0, ((x - a[0]) * dx + (y - a[1]) * dy) / L2))
    return math.hypot(x - a[0] - dx * t, y - a[1] - dy * t), t

def path_dist(x, y):
    return min(seg_dist(x, y, PATH[i], PATH[i + 1])[0] for i in range(len(PATH) - 1))

def path_y(x):
    """road centre y at a given x (the road runs monotonically west)"""
    for i in range(len(PATH) - 1):
        (ax, ay), (bx, by) = PATH[i], PATH[i + 1]
        if bx <= x <= ax: return ay + (by - ay) * (ax - x) / max(1e-6, ax - bx)
    return 0.0

def path_dir(x):
    for i in range(len(PATH) - 1):
        (ax, ay), (bx, by) = PATH[i], PATH[i + 1]
        if bx <= x <= ax:
            L = math.hypot(bx - ax, by - ay); return ((bx - ax) / L, (by - ay) / L)
    return (-1.0, 0.0)

def beside(x, off):
    """point `off` metres to the right (+) / left (-) of the road at x, looking west; and the unit vector back to the road"""
    dx, dy = path_dir(x); nx, ny = dy, -dx            # right-hand normal when walking west = north
    px, py = x + nx * off, path_y(x) + ny * off
    return px, py, (-nx * (1 if off > 0 else -1), -ny * (1 if off > 0 else -1))

def side_pt(x, off):
    """like beside(), but past the road ends it keeps x (no piling up at the end points)"""
    if -336 <= x <= 16: return beside(x, off)[:2]
    return x, path_y(max(-336, min(16, x))) + off

def height(x, y):
    d = path_dist(x, y)
    h = 3.2 * math.sin(math.pi * max(0.0, min(1.0, -x / 330.0)))           # a gentle rise in the middle of the route
    h += .5 * math.sin(x * .045 + 1.1) * math.cos(y * .06) + .35 * math.sin(x * .11) * math.sin(y * .09 + .7)
    w = max(0.0, d - WALL0)
    h += 30.0 * (1 - math.exp(-w * w * .0014))                              # valley sides
    h += (.8 * math.sin(x * .045 + y * .03) + .4 * math.sin(y * .08 - x * .025)) * min(1.0, w / 15)  # gently lumpy slopes
    # flatten the rest stop plaza and the two gates
    for (cx, cy, r) in ((PLAZA[0], PLAZA[1] + 3, 13.0), (EAST_GATE[0], 0, 8.0), (WEST_GATE[0], 0, 8.0)):
        k = max(0.0, min(1.0, (math.hypot(x - cx, y - cy) - r) / 6.0)); k = k * k * (3 - 2 * k)
        h = h * k + base_at(cx, cy) * (1 - k)
    return h

def base_at(x, y):
    return 3.2 * math.sin(math.pi * max(0.0, min(1.0, -x / 330.0)))

def path_mask(x, y):
    d = path_dist(x, y) - PATH_W / 2
    m = max(0.0, min(1.0, (1.3 - d) / 1.3))
    # dirt worn into the plaza edge and in front of the hut
    return m

def plaza_mask(x, y):
    d = math.hypot(x - PLAZA[0], y - PLAZA[1])
    return max(0.0, min(1.0, (PLAZA[2] - d) / .8))

# tall grass patches: (x0, y0, x1, y1), pool [(card, weight)], levels
G1 = (-108, -19, -92, -3)
G2 = (-178, 8, -162, 24)
G3 = (-236, -16, -220, 0)
_mx, _my, _ = beside(-133.0, -16.0)          # hidden meadow south of the road (behind the trees): Pikachu lives here
G4 = (_mx - 7, _my - 5, _mx + 7, _my + 5)
GRASS = [
    (G1, [('Pidgey_MEW_016', 35), ('Rattata_MEW_019', 35), ('Spearow_MEW_021', 20), ('Nidoran_Female_MEW_029', 5), ('Nidoran_Male_MEW_032', 5)], (11, 13)),
    (G2, [('Caterpie_MEW_010', 30), ('Weedle_MEW_013', 30), ('Pidgey_MEW_016', 15), ('Oddish_MEW_043', 15), ('Metapod_MEW_011', 5), ('Kakuna_MEW_014', 5)], (11, 14)),
    (G3, [('Rattata_MEW_019', 25), ('Spearow_MEW_021', 20), ('Jigglypuff_MEW_039', 15), ('Oddish_MEW_043', 15), ('Nidoran_Female_MEW_029', 10),
          ('Nidoran_Male_MEW_032', 10), ('Pidgeotto_MEW_017', 5)], (12, 14)),
    (G4, [('Pikachu_MEW_025', 25), ('Oddish_MEW_043', 30), ('Jigglypuff_MEW_039', 25), ('Pidgey_MEW_016', 20)], (12, 15)),
]

def in_grass(x, y, pad=0.0):
    return any(r[0] - pad < x < r[2] + pad and r[1] - pad < y < r[3] + pad for (r, _, _) in GRASS)

# trainers: x along the road, side offset (+ north / - south), sight (m), team
TRAINERS = [
    dict(id='joey', name='Youngster Joey', outfit='youngster', body='m', hair='Hair_Buzzed', hair_color=[.35, .2, .08], scale=.8, x=-46.0, off=4.6, sight=9.5,
         team=[['Rattata_MEW_019', 12], ['Spearow_MEW_021', 13]], reward=200,
         intro=["Hey! You! You're a Ranger, right? I can tell — you've got that new-licence smell.", "My Rattata's in the top percent of all Rattata. Probably. Let's battle!"],
         win=["Aww, no! My Rattata was supposed to be top percent...", "Okay, okay. You're good. Mistvale's to the west — mind the bug kid in the trees."],
         after=["I'm gonna train Rattata until it's the TOP top percent. You'll see."]),
    dict(id='wes', name='Bug Catcher Wes', outfit='bugcatcher', body='m', hair='Hair_SimpleParted', hair_color=[.1, .07, .05], scale=.85, x=-141.0, off=-4.8, sight=10.0,
         team=[['Caterpie_MEW_010', 12], ['Weedle_MEW_013', 12], ['Metapod_MEW_011', 14]], reward=240,
         intro=["Shh! Don't step on the grass like that — you'll scare them. ...Too late. Battle me instead!"],
         win=["My bugs! They're just... resting. Metapod is ALWAYS resting, to be fair.", "Hey — the meadow behind these trees? Something yellow sparks in there. I'm too scared to look."],
         after=["Caterpie eats twice its weight in leaves. Echo leaves, I mean. They're projected. Don't ask."]),
    dict(id='mira', name='Lass Mira', outfit='lass', body='f', hair='Hair_Long', hair_color=[.85, .55, .25], scale=.92, x=-255.0, off=4.8, sight=10.0,
         team=[['Jigglypuff_MEW_039', 14], ['Oddish_MEW_043', 15]], reward=280,
         intro=["A new Ranger? How sweet. My Echoes are cuter than yours — that's just science. Battle!"],
         win=["Hmph. Fine. Yours are... a little cute too.", "The fog past the Mistvale gate has been weird lately. Glowing. Be careful, okay?"],
         after=["Jigglypuff sang all night again. I haven't slept since Tuesday."]),
]

ITEMS = [  # (id, x along road, side offset, item, count)
    ('r1_potion_a', -80.0, 11.0, 'potion', 1),
    ('r1_balls', -133.0, -19.5, 'ball', 3),
    ('r1_potion_b', -266.0, -10.5, 'potion', 1),
]

# ------------------------------------------------------------------ meshes
def ground():
    x0, x1, y0, y1 = AREA; step = 2.5
    nx, ny = int((x1 - x0) / step), int((y1 - y0) / step)
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UV')
    grid = [[bm.verts.new((x0 + i * step, y0 + j * step, 0)) for i in range(nx + 1)] for j in range(ny + 1)]
    for row in grid:
        for v in row: v.co.z = height(v.co.x, v.co.y)
    for j in range(ny):
        for i in range(nx):
            f = bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
            for l in f.loops: l[uvl].uv = (l.vert.co.x / 4, l.vert.co.y / 4)
    ob = T.mesh_obj('SM_R1_Ground', bm); T.set_mat(ob, 'M_GroundR1')
    for p in ob.data.polygons: p.use_smooth = True
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.fbx(filepath=os.path.join(FBX, 'SM_R1_Ground.fbx'), use_selection=True, apply_scale_options='FBX_SCALE_ALL',
                             axis_forward='-Z', axis_up='Y', mesh_smooth_type='FACE', add_leaf_bones=False, bake_anim=False)

def splat(res=1024):
    """R = dirt road, G = (unused: sand), B = flagstones (rest stop plaza). Covers the SPLAT square, sampled by world XY in Unreal."""
    import numpy as np
    S = SPLAT_S; cx, cy = SPLAT_C
    img = np.zeros((res, res, 4), np.float32); img[..., 3] = 1
    # coarse evaluation (every 2nd texel) then upsample: 1M path_dist calls are slow in Python
    h = res // 2
    for j in range(h):
        y = cy - S / 2 + S * (j * 2 + 1) / res
        if abs(y) > 60: continue
        for i in range(h):
            x = cx - S / 2 + S * (i * 2 + 1) / res
            if x < -350 or x > 30: continue
            r = path_mask(x, y); b = plaza_mask(x, y)
            if r or b: img[j * 2:j * 2 + 2, i * 2:i * 2 + 2, 0] = r; img[j * 2:j * 2 + 2, i * 2:i * 2 + 2, 2] = b
    im = bpy.data.images.new('T_R1Splat', res, res, alpha=False, float_buffer=False); im.colorspace_settings.name = 'Non-Color'
    im.pixels.foreach_set(img.ravel()); im.filepath_raw = os.path.join(OUT, 'tex', 'T_R1Splat.png'); im.file_format = 'PNG'; im.save()
    bpy.data.images.remove(im)

def peaks():
    rnd = random.Random(31); P = []
    for side in (1, -1):
        x = 40.0
        while x > -400:
            px, py = x, path_y(max(-336, min(16, x)))
            rad = rnd.uniform(48, 80); d = rad * 1.15 + rnd.uniform(44, 70); hgt = rnd.uniform(45, 105) * (1.3 if rnd.random() < .3 else 1.0)
            P.append((px + rnd.uniform(-10, 10), py + side * d, rad, hgt))
            for k in range(2):
                a = rnd.uniform(0, math.tau); sd = rad * rnd.uniform(.45, .7)
                P.append((px + math.cos(a) * sd, py + side * d + math.sin(a) * sd, rad * rnd.uniform(.4, .6), hgt * rnd.uniform(.45, .7)))
            x -= rnd.uniform(38, 55)
    # the two ends: a ridge behind each gate closes the valley (Lumen Harbor east, Mistvale's fog basin west)
    for (cx, cy, rad, hgt) in [(78, -40, 55, 60), (80, 45, 60, 70), (-395, -50, 60, 80), (-400, 40, 55, 65)]:
        P.append((cx, cy, rad, hgt))
    # no mountain foot may reach into the valley (the road, the rest stop, the meadow): keep 42 m of valley either side
    return [p for p in P if path_dist(p[0], p[1]) - p[2] * 1.15 > 42.0]

def mountains():
    """same faceted look and palette as the Lumen mountains (T_Palette_Mountain, already imported)"""
    rnd = random.Random(21); bm = bmesh.new()
    for k, (cx, cy, rad, hgt) in enumerate(peaks()):
        rr = random.Random(500 + k); big = hgt > 45; seg, rings = (22, 11) if big else (14, 7)
        base_z = height(cx, cy) - 8
        lobes = rr.choice((3, 4, 5)); ph = rr.uniform(0, 6.28); ph2 = rr.uniform(0, 6.28); rows = []
        for i in range(rings + 1):
            t = i / rings; row = []
            for s_ in range(seg):
                a = 2 * math.pi * s_ / seg + rr.uniform(-.08, .08)
                ridge = 1 + .22 * math.sin(lobes * a + ph) * (1 - t * .6) + .1 * math.sin((lobes * 2 + 1) * a + ph2)
                rk = rad * (1 - t) ** 1.2 * ridge * (1 + rr.uniform(-.1, .1) * (1 - t))
                z = base_z + hgt * (t ** .9) + rr.uniform(-.05, .05) * hgt * (1 - t) * t
                row.append(bm.verts.new((cx + math.cos(a) * rk, cy + math.sin(a) * rk, z)))
            rows.append(row)
        top = bm.verts.new((cx + rr.uniform(-2, 2), cy + rr.uniform(-2, 2), base_z + hgt * 1.02))
        for i in range(rings):
            for s_ in range(seg): bm.faces.new((rows[i][s_], rows[i][(s_ + 1) % seg], rows[i + 1][(s_ + 1) % seg], rows[i + 1][s_]))
        for s_ in range(seg): bm.faces.new((rows[rings][s_], rows[rings][(s_ + 1) % seg], top))
    bm.normal_update()
    NPAL = 21   # 7 colour groups x 3 shades, same order as blender_town.mountains()
    uvl = bm.loops.layers.uv.new('UV')
    for f in bm.faces:
        c = f.calc_center_median(); zc = c.z - 6; slope = 1 - abs(f.normal.z)
        n_ = math.sin(c.x * .05) * 6 + math.sin(c.y * .07) * 5
        if zc < 40 + n_ - slope * 14: k = 0 if (int((zc + n_) / 6) % 2 == 0) else 1
        else: k = 2 if (int((zc + n_) / 8) % 2 == 0) else 3
        if slope > .72 and zc > 26: k = 5
        if zc > 86 + n_ - slope * 20: k = 4 if slope < .6 else 6
        idx = k * 3 + rnd.randrange(3)
        for l in f.loops: l[uvl].uv = ((idx + .5) / NPAL, .5)
    ob = T.mesh_obj('SM_R1_Mountains', bm); T.set_mat(ob, 'M_Mountain')
    for p in ob.data.polygons: p.use_smooth = False
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.fbx(filepath=os.path.join(FBX, 'SM_R1_Mountains.fbx'), use_selection=True, apply_scale_options='FBX_SCALE_ALL',
                             axis_forward='-Z', axis_up='Y', mesh_smooth_type='FACE', add_leaf_bones=False, bake_anim=False)

def hut():
    return T.house('SM_R1_Hut', 7.0, 5.5, 3.0, 'M_Roof_Green', 'M_Siding_Cream', porch=True, chimney=True)

def gate_arch(name):
    """timber arch over the road with a cross beam (the sign hangs from it); origin at road level, spans x (local)"""
    P = []
    for s_ in (-1, 1):
        P.append(T.box(f'{name}_post{s_}', .4, .4, 4.6, (s_ * 3.4, 0, 0), 'M_WoodDark', bevel=.04))
        P.append(T.box(f'{name}_foot{s_}', .9, .9, .5, (s_ * 3.4, 0, -.1), 'M_Stone', bevel=.05))
        P.append(T.box(f'{name}_brace{s_}', .18, .18, 1.6, (s_ * 2.85, 0, 3.55), 'M_WoodDark', rot=(0, s_ * math.radians(45), 0), bevel=.02))
    P.append(T.box(f'{name}_beam', 8.0, .45, .45, (0, 0, 4.4), 'M_WoodDark', bevel=.04))
    P.append(T.box(f'{name}_cap', 8.4, .7, .14, (0, 0, 4.85), 'M_Roof_Green', bevel=.02))
    P.append(T.box(f'{name}_board', 3.4, .12, .8, (0, -.1, 3.35), 'M_WoodLight', bevel=.03))
    for s_ in (-1, 1): P.append(T.box(f'{name}_chain{s_}', .05, .05, .35, (s_ * 1.4, -.1, 4.15), 'M_Iron', bevel=0))
    return T.join(P, name)

def item_glint():
    """a Poké Ball lying in the grass: red/white halves and a black band (items you can pick up)"""
    P = [T.cyl('ib_bot', .14, .12, (0, 0, 0), 'M_Trim', seg=16), T.cyl('ib_top', .14, .12, (0, 0, .14), 'M_Red', seg=16),
         T.cyl('ib_band', .145, .03, (0, 0, .12), 'M_Iron', seg=16), T.cyl('ib_btn', .045, .03, (0, -.14, .135), 'M_Trim', rot=(math.pi / 2, 0, 0), seg=10)]
    return T.join(P, 'SM_ItemBall')

# ------------------------------------------------------------------ placements
def _ue(x, y, z): return [round(x * 100, 1), round(-y * 100, 1), round(z * 100, 1)]
def _yaw(dx, dy): return round(math.degrees(math.atan2(-dy, dx)), 1)

def plan_route():
    P = {'objects': []}
    def add(mesh, x, y, rot=0.0, s=1.0, z=None, **kw):
        o = dict(mesh=mesh, x=round(x, 3), y=round(y, 3), z=round(height(x, y) if z is None else z, 3), rot=round(rot, 2), s=round(s, 3), snap=z is None)
        o.update(kw); P['objects'].append(o); return o
    blocked = [(REST[0], REST[1], 7.5), (PLAZA[0], PLAZA[1], PLAZA[2] + 1.5), (EAST_GATE[0], 0, 6), (WEST_GATE[0], 0, 6)]
    for t in TRAINERS:
        tx, ty, _ = beside(t['x'], t['off']); blocked.append((tx, ty, 3.0))
        # keep the trainer's line of sight to the road clear
        mx, my, _ = beside(t['x'], t['off'] / 2); blocked.append((mx, my, 3.0))
    for (iid, ix, off, _, _) in ITEMS:
        x, y, _ = beside(ix, off); blocked.append((x, y, 2.5))
    def free(x, y, r=1.5):
        if path_dist(x, y) < PATH_W / 2 + r + .6: return False
        if in_grass(x, y, r + .4): return False
        if not (AREA[0] + 5 < x < AREA[1] - 5 and AREA[2] + 5 < y < AREA[3] - 5): return False
        return all(math.hypot(x - bx, y - by) > br + r for bx, by, br in blocked)
    # ---- forest: dense on the valley sides, thinner near the road; pines higher up the slopes
    n = 0
    while n < 420:
        x = R.uniform(-345, 30); d = R.uniform(7, 55) * (1 if R.random() < .5 else -1)
        px, py = side_pt(x, d)
        if not free(px, py, 2.4): continue
        far = abs(d) > WALL0 + 6
        mesh = R.choice([T.NAT + 'SM_Pine_Tree_1', T.NAT + 'SM_Pine_Tree_2']) if (far and R.random() < .6) else R.choice(T.TREES_FOREST)
        add(mesh, px, py, R.random() * 360, (.85 + R.random() * .4) * (1.15 if far else 1.0)); n += 1
    n = 0
    while n < 160:   # far slopes: pines up to the mountain feet
        x = R.uniform(-380, 60); d = R.uniform(55, 85) * (1 if R.random() < .5 else -1)
        px, py = side_pt(x, d)
        if not free(px, py, 4): continue
        add(R.choice([T.NAT + 'SM_Pine_Tree_1', T.NAT + 'SM_Pine_Tree_2']), px, py, R.random() * 360, 1.3 + R.random() * .7); n += 1
    for x in (-20, -88, -118, -170, -205, -232, -290, -318):     # a few big broadleaf "landmark" trees close to the road
        for off in ((8.5,) if (int(x) // 7) % 2 else (-8.5,)):
            px, py, _ = beside(x, off)
            if free(px, py, 1.5): add(R.choice(T.TREES_TOWN), px, py, R.random() * 360, .75 + R.random() * .15)
    n = 0
    while n < 230:   # bushes lining the road
        x = R.uniform(-336, 14); d = R.uniform(3.6, 14) * (1 if R.random() < .5 else -1)
        px, py, _ = beside(x, d)
        if not free(px, py, 1.0): continue
        add(R.choice(T.BUSHES), px, py, R.random() * 360, .7 + R.random() * .5); n += 1
    n = 0
    while n < 800:   # grass clumps, flowers, ferns
        x = R.uniform(-340, 20); d = R.uniform(2.8, 22) * (1 if R.random() < .5 else -1)
        px, py, _ = beside(x, d)
        if not free(px, py, .2): continue
        k = R.random()
        if k < .6: add(R.choice(T.GRASS), px, py, R.random() * 360, .9 + R.random() * .6)
        elif k < .88: add(R.choice(T.FLOWERS), px, py, R.random() * 360, .8 + R.random() * .5)
        else: add(T.NAT + 'SM_Fern', px, py, R.random() * 360, .7 + R.random() * .4)
        n += 1
    for k in range(70):   # small rocks along the verge, boulders and cliffs on the slopes
        x = R.uniform(-336, 14); d = R.uniform(3.5, 16) * (1 if R.random() < .5 else -1)
        px, py, _ = beside(x, d)
        if free(px, py, .8): add(R.choice(T.ROCKS_S), px, py, R.random() * 360, .22 + R.random() * .25)
    for k in range(40):
        x = R.uniform(-350, 40); d = R.uniform(24, 50) * (1 if R.random() < .5 else -1)
        px, py = side_pt(x, d)
        if free(px, py, 3): add(R.choice(T.CLIFFS + T.ROCKS_L), px, py, R.random() * 360, .8 + R.random() * .6)
    # ---- tall grass: the Echo patches (dense) + the hidden meadow ringed with flowers
    for (r, _, _) in GRASS:
        x0, y0, x1, y1 = r; n = int((x1 - x0) * (y1 - y0) * 1.1)   # dense: the patches must read as "tall grass" from the road
        for k in range(n): add(T.NAT + 'SM_Grass', R.uniform(x0, x1), R.uniform(y0, y1), R.random() * 360, 1.1 + R.random() * .5)
    x0, y0, x1, y1 = G4
    for k in range(40):
        a = R.random() * math.tau; cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        add(R.choice(T.FLOWERS), cx + math.cos(a) * (8.5 + R.random() * 2), cy + math.sin(a) * (6.5 + R.random() * 2), R.random() * 360, 1.0)
    # ---- the road: wooden fence along a few stretches, signposts, the two gates
    for (xa, xb, off) in [(-4, -26, -3.4), (-150, -176, 3.4), (-282, -306, -3.4)]:
        x = xa
        while x > xb:
            px, py, _ = beside(x, off); dx, dy = path_dir(x)
            add(R.choice(T.FENCES), px, py, math.degrees(math.atan2(dy, dx)), .95); x -= 3.3
    for (gx, label, name) in [(EAST_GATE[0], 'ROUTE 1\nLumen Harbor', 'SM_R1_GateEast'), (WEST_GATE[0], 'MISTVALE\nfog advisory', 'SM_R1_GateWest')]:
        add(name, gx, 0, 90, 1.0, z=base_at(gx, 0))
    for (x, off, txt) in [(4.0, 4.2, 'ROUTE 1\nwest: Mistvale'), (-190.0, 4.6, 'RANGER REST\nheal & supplies'), (-318.0, -4.2, 'MISTVALE\nahead')]:
        px, py, _ = beside(x, off); dx, dy = path_dir(x); add('SM_Sign', px, py, math.degrees(math.atan2(-dx, dy)))   # board faces along the road
    # ---- Ranger Rest: hut, flagstone plaza, campfire with log seats, trader's stall, benches, lamp posts
    add('SM_R1_Hut', REST[0], REST[1], 0)
    fx, fy = PLAZA[0] - 4.5, PLAZA[1] - 1.0
    add('KSurvival/campfire_pit', fx, fy, 0, w=1.4)
    for a in (20, 140, 260):
        add('KSurvival/tree_log_small', fx + 1.7 * math.cos(math.radians(a)), fy + 1.7 * math.sin(math.radians(a)), a + 90, w=1.15)
    add('QProps/Stall_Empty', PLAZA[0] + 6.2, PLAZA[1] + 1.5, -90, h=2.6)
    for (m, dx, dy, r, h) in [('QProps/FarmCrate_Apple', 7.6, -.2, 10, .45), ('QProps/Barrel', 7.9, 3.4, 0, .95), ('QProps/Crate_Wooden', 4.8, 4.0, 15, .7)]:
        add(m, PLAZA[0] + dx, PLAZA[1] + dy, r, h=h)
    add('SM_Bench', PLAZA[0] - 1.0, PLAZA[1] + 4.2, 180); add('SM_Bin', PLAZA[0] + 1.2, PLAZA[1] + 4.4)
    for (dx, dy) in [(-6.5, -4.5), (6.5, -4.5)]: add('SM_LampPost', PLAZA[0] + dx, PLAZA[1] + dy)
    add('KSurvival/signpost', PLAZA[0] + 3.0, PLAZA[1] - 5.6, 0, h=2.0)
    # ---- items: Poké Balls lying in the grass (the game hides them once picked)
    for (iid, ix, off, item, cnt) in ITEMS:
        x, y, _ = beside(ix, off); add('SM_ItemBall', x, y, R.random() * 360, 1.0, tag='PBX_Item_' + iid)
    P['gameplay'] = gameplay_data()
    P['terrain'] = ['SM_R1_Ground', 'SM_R1_Mountains']
    P['player_start'] = dict(x=4, y=0, z=height(4, 0) + 1.0, rot=180)
    return P

def gameplay_data():
    G = {'map': 'L_Route1', 'title': 'ROUTE 1', 'chapter': 'Chapter 2 · Route 1'}
    def spot(x, y, face=(1, 0), dz=0.0): return {'pos': _ue(x, y, height(x, y) + dz), 'yaw': _yaw(*face)}
    G['new_game'] = spot(4, 0, (-1, 0))
    G['doors'] = [{'id': 'hut', 'label': 'Ranger Rest', 'locked': True, 'out_door': _ue(REST[0], REST[1] - 2.85, height(REST[0], REST[1] - 3) + .5),
                   'locked_text': 'The hut is locked. A card on the door: "Back in five minutes — Nell (at the campfire)."'}]
    hx, hy = PLAZA[0] - 3.0, PLAZA[1] + 1.4
    G['npcs'] = [
        {'id': 'healer', 'outfit': 'healer', 'hair_color': [0.15, 0.08, 0.05], 'name': 'Ranger Nell', 'body': 'f', 'hair': 'Hair_Buns', 'anim': 'Idle_Loop', **spot(hx, hy, (0, -1))},
        {'id': 'trader', 'outfit': 'trader', 'hair_color': [0.5, 0.45, 0.4], 'name': 'Trader Fenn', 'body': 'm', 'hair': 'Hair_Beard', 'anim': 'Idle_FoldArms_Loop', **spot(PLAZA[0] + 4.9, PLAZA[1] + 1.4, (-1, -.3))},
        {'id': 'scout', 'outfit': 'guard', 'hair_color': [0.2, 0.12, 0.06], 'name': 'Ranger Tam', 'body': 'm', 'hair': 'Hair_SimpleParted', 'anim': 'Idle_FoldArms_Loop', **spot(-3.0, -4.2, (0, 1))},
    ]
    for t in TRAINERS:
        x, y, (fx, fy) = beside(t['x'], t['off'])
        G['npcs'].append({'id': t['id'], 'outfit': t['outfit'], 'hair_color': t['hair_color'], 'name': t['name'], 'body': t['body'], 'hair': t['hair'],
                          'anim': 'Idle_Loop', 'scale': t['scale'], **spot(x, y, (fx, fy)),
                          'trainer': {'sight': t['sight'] * 100.0, 'team': t['team'], 'reward': t['reward'], 'intro': t['intro'], 'win': t['win'], 'after': t['after']}})
    G['spots'] = {'from_lumen': spot(5.0, 0, (-1, 0)), 'from_mistvale': spot(WEST_GATE[0] + 6.0, 0, (1, 0)), 'respawn': spot(PLAZA[0] - 1.0, PLAZA[1] - 3.0, (0, 1))}
    G['grass'] = []
    for (r, pool, lv) in GRASS:
        x0, y0, x1, y1 = r
        G['grass'].append({'min': _ue(x0, y1, 0)[:2], 'max': _ue(x1, y0, 0)[:2], 'pool': [[c, w] for (c, w) in pool], 'lv': list(lv)})
    G['wild_spawns'] = []
    for (r, _, _) in GRASS:
        x0, y0, x1, y1 = r
        for (u, v) in ((.3, .35), (.7, .65)):
            x, y = x0 + (x1 - x0) * u, y0 + (y1 - y0) * v; G['wild_spawns'].append(_ue(x, y, height(x, y)))
    G['bounds'] = {'center': _ue(-160, 0, 0)[:2], 'radius': 40000.0, 'water_z': -5000.0, 'safe': spot(4, 0, (-1, 0))}
    # soft wall: stay within this distance of the road polyline (the forest beyond is "too thick")
    G['corridor'] = {'points': [_ue(x, y, 0)[:2] for (x, y) in PATH], 'width': 3300.0}
    G['signs'] = []
    for (x, off, txt) in [(4.0, 4.2, 'ROUTE 1\nwest: Mistvale'), (-190.0, 4.6, 'RANGER REST\nheal & supplies'), (-318.0, -4.2, 'MISTVALE\nahead')]:
        px, py, _ = beside(x, off); G['signs'].append({'pos': _ue(px, py, height(px, py) + 1.15), 'yaw': _yaw(*path_dir(x)), 'text': txt})
    G['exits'] = [{'id': 'lumen', 'pos': _ue(EAST_GATE[0] + 4.0, 0, base_at(EAST_GATE[0], 0)), 'radius': 300.0, 'to_map': 'L_Town', 'to_spot': 'from_route1', 'min_step': 0, 'label': 'Lumen Harbor'},
                  {'id': 'mistvale', 'pos': _ue(WEST_GATE[0] - 3.0, 0, base_at(WEST_GATE[0], 0)), 'radius': 320.0, 'to_map': '', 'to_spot': '', 'min_step': 0, 'label': 'Mistvale'}]
    G['items'] = []
    for (iid, ix, off, item, cnt) in ITEMS:
        x, y, _ = beside(ix, off); G['items'].append({'id': iid, 'pos': _ue(x, y, height(x, y) + .2), 'item': item, 'count': cnt})
    return G

def run():
    T.reset()
    plan = plan_route()
    T.export(hut(), 'SM_R1_Hut'); T.reset()
    T.export(gate_arch('SM_R1_GateEast'), 'SM_R1_GateEast'); T.reset()
    T.export(gate_arch('SM_R1_GateWest'), 'SM_R1_GateWest'); T.reset()
    T.export(item_glint(), 'SM_ItemBall'); T.reset()
    ground(); T.reset(); mountains(); T.reset()
    splat()
    with open(os.path.join(OUT, 'route1_plan.json'), 'w') as fh: json.dump(plan, fh, indent=1)
    gd = os.environ.get('PBX_GAMEDATA', os.path.join(os.path.dirname(OUT), 'PokeboxNext', 'Content', 'PBX', 'Data'))
    os.makedirs(gd, exist_ok=True)
    with open(os.path.join(gd, 'L_Route1.json'), 'w', encoding='utf-8') as fh: json.dump(plan['gameplay'], fh, indent=1, ensure_ascii=False)
    print('route 1 built:', len(plan['objects']), 'placements')

if os.environ.get('PBX_ROUTE1_NORUN') != '1':
    run()
