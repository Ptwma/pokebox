# Sigil & Spark v4 — set #3: THE FISH-MARKET ALLEY (Ep1 scene 5, the Pact moment). Night, rain, fog.
#   blender -b --python set_alley.py -- <SRC> <out.png> [wide|spark|export]
# A narrow lane (4 m) between two rows of tall harbour houses; laundry lines and nets overhead, crates and fish barrels,
# puddles; ONE red lamp halfway down (the colour key: fog blue-grey × that red); the far end opens on the fog and the
# lighthouse. The Blanked Spark blocks the lane in the middle.
import os
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kit.py')).read())

LEN = 12; HW = 2.0   # half-length (x), half-width (y) in metres
wood = mat('CrateWood', (0.28, 0.18, 0.1)); dark = mat('DarkWood', (0.12, 0.08, 0.06)); iron = mat('Iron', (0.04, 0.04, 0.045), 0.5)
net = mat('Net', (0.10, 0.16, 0.12)); cloth1 = mat('ClothWhite', (0.75, 0.72, 0.66)); cloth2 = mat('ClothBlue', (0.18, 0.26, 0.42))
puddle = mat('Puddle', (0.03, 0.035, 0.05), 0.05); red = glow('LampRed', (1.0, 0.12, 0.08), 5.0); win = glow('RoomLit', (1.0, 0.6, 0.28), 2.0)

WINS = []; DOORS = []
def row(y, rot, seed):
    rr = random.Random(seed)
    for x in range(-LEN + 1, LEN, 2):
        for f in range(3):
            mat_ = 'UnevenBrick' if f == 0 else rr.choice(['Plaster', 'Plaster', 'UnevenBrick'])
            if f == 0: n = rr.choice([f'Wall_{mat_}_Door_Flat', f'Wall_{mat_}_Straight', f'Wall_{mat_}_Straight'])
            else: n = rr.choice([f'Wall_{mat_}_Window_Thin_Round', f'Wall_{mat_}_Window_Wide_Flat', f'Wall_{mat_}_Straight'])
            piece(n, (x, y, f * 3.12), rot)
            if 'Window' in n: WINS.append((x, y, f * 3.12, rot, 'Wide' in n))
            if 'Door' in n: DOORS.append((x, y, rot))
            if 'Window' in n and rr.random() < 0.25:   # a lit room behind a few windows
                b = box('RoomLit', (1.6, 0.02, 1.4), (x, y + (0.5 if rot == 180 else -0.5), f * 3.12 + 1.6), win)
            elif 'Window' in n:
                box('RoomDark', (1.6, 0.02, 1.4), (x, y + (0.5 if rot == 180 else -0.5), f * 3.12 + 1.6), mat('RoomDarkM', (0.02, 0.025, 0.04)))
        if rr.random() < 0.3: piece('Balcony_Simple_Straight', (x, y + (-0.1 if rot == 180 else 0.1), 3.12), rot)
row(HW, 180, 3)     # north row, facades face the lane (-y)
row(-HW, 0, 7)      # south row, facades face +y
for x in range(-LEN + 1, LEN, 2):
    for y in (-1, 1): piece('Floor_UnevenBrick', (x, y, 0))
for y in (-1, 1):                                    # the closed west end
    for f in range(3): piece('Wall_UnevenBrick_Straight', (-LEN, y, f * 3.12), -90)

# overhead: laundry lines and nets between the rows
R2 = random.Random(11)
for x in (-8, -3.5, 2.5, 7):
    z = R2.uniform(4.8, 6.6)
    cyl('Line', 0.01, HW * 2, (x, 0, z), iron, 6, rot=(90, 0, 0))
    for k in range(R2.randint(2, 4)):
        box('Laundry', (R2.uniform(0.4, 0.8), 0.02, R2.uniform(0.5, 0.9)), (x, R2.uniform(-1.4, 1.4), z - 0.4), R2.choice([cloth1, cloth2]))

# the market leftovers: crates, fish barrels, a cart, puddles
_cr = {}
for (x, y, r) in [(-9.75, 1.05, 10), (-8.55, 1.1, 4), (-2.6, -1.1, 20), (5.35, 1.05, 5), (6.6, 1.08, -3)]:   # QA: no two crates in each other, y kept off the walls (the kit crate is ~1 m deep)
    _cr[(x, y)] = piece('Prop_Crate', (x, y, 0.0), r)
bpy.context.view_layer.update(); _ch = _cr[(-9.75, 1.05)].dimensions.z
piece('Prop_Crate', (-9.15, 1.0, _ch + 0.002), 28)   # the third crate stacked on the first two
for (x, y) in [(-6.8, -1.4), (-6.2, -1.5), (3.2, 1.4), (8.4, -1.4)]:
    cyl('Barrel', 0.32, 0.85, (x, y, 0.43), wood, 14)
    cyl('BarrelBand', 0.335, 0.06, (x, y, 0.2), iron, 14); cyl('BarrelBand', 0.335, 0.06, (x, y, 0.68), iron, 14)
piece('Prop_Wagon', (-4.2, 0.75, 0), 97)   # QA: along the lane (at 10 deg its shafts went through the house)
# puddles: irregular blobs of a few overlapping ellipses each, mostly along the gutter and in the cobble dips (QA: the
# perfect ellipses read as blue discs)
PR = random.Random(23)
for (x, y, s) in [(-1.0, 0.15, 0.9), (1.8, -0.35, 0.6), (4.6, 0.3, 1.0), (-7.4, -0.15, 0.6), (-4.9, 1.2, 0.35), (7.6, -1.1, 0.4), (9.9, 0.1, 0.7)]:
    for k in range(PR.randint(3, 5)):
        r = s * PR.uniform(0.35, 0.7)
        d = cyl('Puddle', r, 0.004, (x + PR.uniform(-s, s) * 0.6, y + PR.uniform(-s, s) * 0.25, 0.010 + k * 0.0004), puddle, 20)
        d.scale.y = r * PR.uniform(0.45, 0.8); d.rotation_euler.z = PR.uniform(0, math.pi)

# the red lamp halfway down (key light) + a cold fill from the open end
box('LampArm', (0.04, 0.5, 0.04), (0.6, 1.75, 3.3), iron); box('LampFrame', (0.24, 0.24, 0.32), (0.6, 1.5, 3.1), iron)
box('LampRed', (0.27, 0.27, 0.22), (0.6, 1.5, 3.1), red)   # glass shows through the frame
point((0.6, 1.2, 3.0), 1100, (1.0, 0.16, 0.1), 0.2)
point((11.0, 0.0, 4.0), 900, (0.45, 0.6, 1.0), 2.0)
point((-10.5, 0.0, 3.0), 180, (1.0, 0.55, 0.25), 0.4)    # a doorway's warm spill at the closed end


# ------------------------------------------------------------------ DETAIL pass (owner 19:59: "I want details")
DA = random.Random(17); I = Matrix()
cork = mat('Cork', (0.62, 0.45, 0.22)); rope = mat('RopeHemp', (0.55, 0.45, 0.28)); shut = [mat('ShutterGreen', (0.16, 0.26, 0.20)), mat('ShutterBlue', (0.14, 0.20, 0.30)), mat('ShutterRed', (0.36, 0.12, 0.08))]
grime = mat('Grime', (0.10, 0.09, 0.08)); paperm = mat('Poster', (0.78, 0.72, 0.58)); inkm = mat('InkBlack', (0.02, 0.02, 0.02)); pipe = mat('PipeIron', (0.08, 0.08, 0.09), 0.4)
def face(y, rot): return (-1 if rot == 180 else 1)   # +1: the facade looks toward +y
def fishnet(x, y, z, w, h, sgn):
    """a hanging net: a grid of cords that sags, cork floats along the top rope"""
    for k in range(int(w / 0.14) + 1):
        xx = x - w / 2 + k * 0.14; sag = 0.18 * math.sin(math.pi * k / max(1, int(w / 0.14)))
        dbox(I, (0.012, 0.012, h - sag), (xx, y + sgn * 0.06, z - (h + sag) / 2), net)
    for j in range(int(h / 0.14) + 1):
        dbox(I, (w, 0.012, 0.012), (x, y + sgn * 0.06, z - j * 0.14 - 0.09 * math.sin(math.pi * j / max(1, int(h / 0.14)))), net)
    dbox(I, (w + 0.1, 0.03, 0.03), (x, y + sgn * 0.06, z), rope)
    for k in range(int(w / 0.3)): dcyl(I, 0.05, 0.08, (x - w / 2 + 0.15 + k * 0.3, y + sgn * 0.08, z - 0.04), cork, 8, rx=90)
fishnet(-5.5, HW - 0.33, 3.0, 2.4, 1.3, -1); fishnet(4.0, -HW + 0.33, 2.8, 1.8, 1.1, 1)
for (x, y, z, rot, wide) in WINS:      # shutters, sills, flower boxes, rags on the sills
    sg = face(y, rot)
    yy = y + sg * 0.33; hw = 0.75 if wide else 0.42
    dbox(I, (hw * 2 + 0.25, 0.14, 0.06), (x, yy, z + 0.9), grime)                                            # sill
    if DA.random() < 0.65:
        m = DA.choice(shut); closed = DA.random() < 0.3
        for sx in (-1, 1):
            px = x + sx * (hw / 2 if closed else hw * 1.5 + 0.06)
            dbox(I, (hw - 0.02, 0.04, 1.25), (px, yy + sg * 0.03, z + 1.55), m)
            for k in range(5): dbox(I, (hw - 0.08, 0.02, 0.03), (px, yy + sg * 0.06, z + 1.05 + k * 0.25), grime)   # slats
            dbox(I, (0.08, 0.03, 0.03), (x + sx * (hw + 0.02), yy + sg * 0.05, z + 1.9), pipe)                   # hinge
    if DA.random() < 0.3:
        dbox(I, (hw * 1.6, 0.22, 0.18), (x, yy + sg * 0.1, z + 1.0), mat('PlanterWood', (0.30, 0.18, 0.10)))
        for k in range(5): dcyl(I, 0.07, 0.14, (x - hw * 0.6 + k * hw * 0.3, yy + sg * 0.1, z + 1.15), mat('Leaves', (0.16, 0.30, 0.12)), 6)
for (x, y, rot) in DOORS:              # stone step, a nameplate, a boot-scraper
    sg = face(y, rot); yy = y + sg * 0.45
    dbox(I, (1.2, 0.35, 0.12), (x, yy, 0.06), mat('StepStone', (0.40, 0.38, 0.35)))
    dbox(I, (0.22, 0.02, 0.14), (x + 0.75, y + sg * 0.33, 1.7), paperm)
    dm = DA.choice([mat('DoorPlank', (0.26, 0.16, 0.09)), mat('DoorPlankDark', (0.17, 0.10, 0.06)), shut[0]])
    for k in range(6): dbox(I, (0.155, 0.06, 2.12), (x - 0.4 + k * 0.16, y + sg * 0.12, 1.06), dm)              # planks
    for zz in (0.4, 1.7): dbox(I, (0.98, 0.07, 0.07), (x, y + sg * 0.15, zz), pipe)                            # iron straps
    dcyl(I, 0.045, 0.03, (x + 0.3, y + sg * 0.19, 1.05), pipe, 10, rx=90); dbox(I, (0.05, 0.02, 0.1), (x + 0.3, y + sg * 0.2, 0.95), pipe)
for (y, rot) in ((HW, 180), (-HW, 0)):  # grime at the foot of the walls, drainpipes, posters
    sg = face(y, rot); yy = y + sg * 0.32
    dbox(I, (LEN * 2, 0.02, 0.35), (0, yy, 0.17), grime)
    for x in (-9.0, -1.0, 6.0) if y > 0 else (-5.0, 3.0, 9.5):
        dcyl(I, 0.05, 8.6, (x, yy + sg * 0.06, 4.3), pipe, 8); dcyl(I, 0.08, 0.25, (x, yy + sg * 0.06, 8.6), pipe, 8, r2=0.05)
        dbox(I, (0.12, 0.3, 0.06), (x, yy + sg * 0.18, 0.08), pipe, rx=0)
        for zz in (1.5, 4.0, 6.5): dbox(I, (0.14, 0.1, 0.03), (x, yy + sg * 0.03, zz), pipe)
    for k in range(6):
        x = DA.uniform(-LEN + 1.5, LEN - 1.5); z = DA.uniform(1.2, 1.9); w, h = DA.uniform(0.3, 0.5), DA.uniform(0.4, 0.6)
        dbox(I, (w, 0.01, h), (x, yy + sg * 0.005, z), paperm, ry=DA.uniform(-6, 6))
        dbox(I, (w * 0.8, 0.012, 0.04), (x, yy + sg * 0.01, z + h * 0.36), inkm)
        for j in range(7): dbox(I, (w * DA.uniform(0.5, 0.8), 0.012, 0.008), (x - w * 0.05, yy + sg * 0.01, z + h * 0.22 - j * h * 0.075), inkm)
        if DA.random() < 0.5: dbox(I, (w * 0.5, 0.013, h * 0.25), (x, yy + sg * 0.012, z + h * 0.3), mat('PosterRed', (0.45, 0.08, 0.06)))
# gutter channel down the middle of the lane, cobble edging, a lobster pot and oars
dbox(I, (LEN * 2, 0.25, 0.02), (0, 0, 0.005), grime)
for sy in (-1, 1):   # the gutter's kerb stones, laid in short irregular lengths
    xx = -LEN
    while xx < LEN:
        ln = DA.uniform(0.35, 0.6); dbox(I, (ln - 0.02, 0.1, 0.05), (xx + ln / 2, sy * 0.17, 0.02), mat('StepStone', (0.40, 0.38, 0.35)), rz=DA.uniform(-2, 2)); xx += ln
_south = [d[0] for d in DOORS if d[1] < 0]
_lx = next((c for c in (-4.3, 1.3, -11.0, 9.8) if all(abs(c + 0.6 - dx) > 1.6 for dx in _south)), -4.3)   # QA: clear of the door steps and the bag
for k in range(3):
    x = _lx + k * 0.6
    for j in range(6): dbox(I, (0.02, 0.02, 0.45), (x + 0.22 * math.cos(j * 1.047), -1.4 + 0.22 * math.sin(j * 1.047), 0.22), dark)
    for zz in (0.02, 0.44): dcyl(I, 0.24, 0.03, (x, -1.4, zz), dark, 12)
for k in range(2): dbox(I, (0.06, 0.12, 2.6), (8.9 + k * 0.25, HW - 0.5, 1.25), wood, ry=-12 + k * 4)

# ------------------------------------------------------------------ dressing (owner: "a little full, not empty")
D = random.Random(9)
_north = [d[0] for d in DOORS if d[1] > 0]; _cx = next((c for c in (8.6, 7.6, -5.0, 1.5) if all(abs(c - dx) > 1.9 for dx in _north)), 8.6)
prop('Stall_Cart_Empty', (_cx, 0.85, 0), 172, height=1.8)   # QA: a spot with no door step under it
prop('FarmCrate_Apple', (-2.0, 1.1, 0), 4, height=0.5)   # QA: the kit farm crate is 1.6 m wide — one fits the lane, two sat on each other
prop('Barrel_Apples', (9.6, -1.35, 0), 0, height=0.95); prop('Barrel_Holder', (-10.4, -1.2, 0), 90, height=1.0)
for (x, y) in [(-7.8, 1.5), (2.2, -1.5), (5.0, -1.55)]: prop('k_pirate/crate-bottles', (x, y, 0), D.uniform(0, 90), height=0.6)
for (x, y) in [(-4.95, -0.95), (0.4, 1.55), (6.8, -1.5)]: prop('Bucket_Metal', (x, y, 0), D.uniform(0, 360), height=0.38)
for (x, y, z) in [(-2.6, -1.1, 1.2), (3.2, 1.4, 0.9)]: prop('k_survival/fish', (x, y, z), D.uniform(0, 360), height=0.12)   # on the crate / barrel top (settle drops them)
for (x, y) in [(-8.6, -1.6), (4.4, 1.6)]: prop('Rope_2', (x, y, 0.01), D.uniform(0, 360), height=0.2)
for x in (-2.9, 3.0, 8.0): prop('Lantern_Wall', (x, 1.7, 2.5), 180, height=0.5)   # QA: the -6 one hung inside the fishing net
# warm practical light from those lanterns and from a few doorways: pools of light on the wet stones (night scene)
for x in (-2.9, 3.0, 8.0): point((x, 1.35, 2.45), 400, (1.0, 0.58, 0.26), 0.12)
for (x, y, rot) in DOORS[::3]: point((x, y + face(y, rot) * 0.9, 2.3), 150, (1.0, 0.55, 0.25), 0.3)
prop('k_survival/barrel-open', (-0.6, -1.5, 0), 0, height=0.9); prop('k_town/stall-stool', (-0.2, -0.9, 0), 0, height=0.5)
prop('Bag', (-9.6, -1.5, 0), 20, height=0.5); prop('Pouch_Large', (6.4, 1.5, 0), 0, height=0.4)

cams = {'wide': ((-11.2, -0.4, 1.7), (6.0, 0.3, 2.0), 24), 'spark': ((-3.0, -1.2, 1.2), (1.0, 0.2, 1.4), 30)}
marks = {'start': [-950, 0, 0], 'spark': [100, 0, 0], 'exit': [1100, 0, 0]}
SKIPCLEAR = ('Stall_Cart',)
keep_clear([(d[0] - 0.62, (d[1] + face(d[1], d[2]) * 0.45) - 0.2, d[0] + 0.62, (d[1] + face(d[1], d[2]) * 0.45) + 0.2) for d in DOORS])   # door steps stay free
finish(cams, marks, world_rgb=(0.05, 0.06, 0.08), exposure=0.0)
