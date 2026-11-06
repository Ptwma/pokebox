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

def row(y, rot, seed):
    rr = random.Random(seed)
    for x in range(-LEN + 1, LEN, 2):
        for f in range(3):
            mat_ = 'UnevenBrick' if f == 0 else rr.choice(['Plaster', 'Plaster', 'UnevenBrick'])
            if f == 0: n = rr.choice([f'Wall_{mat_}_Door_Flat', f'Wall_{mat_}_Straight', f'Wall_{mat_}_Straight'])
            else: n = rr.choice([f'Wall_{mat_}_Window_Thin_Round', f'Wall_{mat_}_Window_Wide_Flat', f'Wall_{mat_}_Straight'])
            piece(n, (x, y, f * 3.12), rot)
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
box('NetHang', (2.4, 0.04, 1.2), (-5.5, 1.75, 2.4), net); box('NetHang', (1.8, 0.04, 1.0), (4.0, -1.75, 2.2), net)

# the market leftovers: crates, fish barrels, a cart, puddles
for (x, y, r) in [(-9.5, 1.3, 10), (-9.0, 1.4, 40), (-9.2, 1.2, 0), (-2.6, -1.3, 20), (5.6, 1.3, 5), (6.2, 1.25, 30)]:
    piece('Prop_Crate', (x, y, 0.0), r)
for (x, y) in [(-6.8, -1.4), (-6.2, -1.5), (3.2, 1.4), (8.4, -1.4)]:
    cyl('Barrel', 0.32, 0.85, (x, y, 0.43), wood, 14)
    cyl('BarrelBand', 0.335, 0.06, (x, y, 0.2), iron, 14); cyl('BarrelBand', 0.335, 0.06, (x, y, 0.68), iron, 14)
piece('Prop_Wagon', (-4.2, 0.9, 0), 10)
for (x, y, s) in [(-1.0, 0.2, 1.2), (1.8, -0.5, 0.9), (4.6, 0.4, 1.4), (-7.4, -0.2, 0.8)]:
    d = cyl('Puddle', s, 0.006, (x, y, 0.012), puddle, 24); d.scale.y = s * 0.6

# the red lamp halfway down (key light) + a cold fill from the open end
box('LampArm', (0.04, 0.5, 0.04), (0.6, 1.75, 3.3), iron); box('LampFrame', (0.24, 0.24, 0.32), (0.6, 1.5, 3.1), iron)
box('LampRed', (0.27, 0.27, 0.22), (0.6, 1.5, 3.1), red)   # glass shows through the frame
point((0.6, 1.2, 3.0), 1100, (1.0, 0.16, 0.1), 0.2)
point((11.0, 0.0, 4.0), 900, (0.45, 0.6, 1.0), 2.0)
point((-10.5, 0.0, 3.0), 180, (1.0, 0.55, 0.25), 0.4)    # a doorway's warm spill at the closed end


# ------------------------------------------------------------------ dressing (owner: "a little full, not empty")
D = random.Random(9)
prop('Stall_Cart_Empty', (7.6, 0.9, 0), 170, height=1.8); prop('FarmCrate_Apple', (-1.8, 1.45, 0), 10, height=0.5); prop('FarmCrate_Empty', (-1.2, 1.5, 0), 40, height=0.5)
prop('Barrel_Apples', (9.6, -1.35, 0), 0, height=0.95); prop('Barrel_Holder', (-10.4, -1.2, 0), 90, height=1.0)
for (x, y) in [(-7.8, 1.5), (2.2, -1.5), (5.0, -1.55)]: prop('k_pirate/crate-bottles', (x, y, 0), D.uniform(0, 90), height=0.6)
for (x, y) in [(-5.0, -1.55), (0.4, 1.55), (6.8, -1.5)]: prop('Bucket_Metal', (x, y, 0), D.uniform(0, 360), height=0.38)
for (x, y) in [(-2.8, -1.4), (3.9, 1.5)]: prop('k_survival/fish', (x, y, 0.62 if x > 0 else 0.0), D.uniform(0, 360), height=0.12)
for (x, y) in [(-8.6, -1.6), (4.4, 1.6)]: prop('Rope_2', (x, y, 0.01), D.uniform(0, 360), height=0.2)
for x in (-6.0, 3.0, 8.0): prop('Lantern_Wall', (x, 1.7, 2.5), 180, height=0.5)
prop('k_survival/barrel-open', (-0.6, -1.5, 0), 0, height=0.9); prop('k_town/stall-stool', (-0.2, -0.9, 0), 0, height=0.5)
prop('Bag', (-9.6, -1.5, 0), 20, height=0.5); prop('Pouch_Large', (6.4, 1.5, 0), 0, height=0.4)

cams = {'wide': ((-11.2, -0.4, 1.7), (6.0, 0.3, 2.0), 24), 'spark': ((-3.0, -1.2, 1.2), (1.0, 0.2, 1.4), 30)}
marks = {'start': [-950, 0, 0], 'spark': [100, 0, 0], 'exit': [1100, 0, 0]}
finish(cams, marks, world_rgb=(0.05, 0.06, 0.08), exposure=0.0)
