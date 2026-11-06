# Sigil & Spark v4 — set #2: THE SCRIPTORIUM (Ep1 scenes 2 "The Rite", 3 "The White Page", 4 "The Spark").
#   blender -b --python set_scriptorium.py -- <SRC> <out.png> [wide|ring|gate|stacks|export]
# A candle-lit hall: a ring of six lecterns under a wheel of candles, benches for the town along both walls, high round
# windows (cold moonlight), the iron SEA GATE at the north end behind Vale's desk; through an arch at the south end, the
# STACKS — tall shelves of books and jars of sleeping Sparks. Colour key: candle gold × the cold white of the windows.
import os
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kit.py')).read())

W, L, H = 6, 10, 2          # half-width / half-length in metres, storeys
WALL = 'UnevenBrick'
wood = mat('BenchWood', (0.24, 0.15, 0.09)); dark = mat('DarkWood', (0.12, 0.08, 0.06)); iron = mat('Iron', (0.04, 0.04, 0.045), 0.5)
leather = mat('BookRed', (0.38, 0.07, 0.06)); leather2 = mat('BookBlue', (0.08, 0.12, 0.28)); leather3 = mat('BookGreen', (0.1, 0.22, 0.12))
paper = mat('Paper', (0.86, 0.80, 0.66)); wax = mat('Wax', (0.92, 0.88, 0.76)); jarm = glow('JarGlow', (0.45, 0.75, 1.0), 0.6)
flame = glow('Candle', (1.0, 0.62, 0.22), 6.0); stone = mat('Stone', (0.24, 0.22, 0.21)); rug = mat('Rug', (0.34, 0.10, 0.08))

# ------------------------------------------------------------------ the hall shell (floor, two storeys of walls, ceiling, beams)
for x in range(-W + 1, W, 2):
    for y in range(-L + 1, L, 2):
        piece('Floor_WoodDark', (x, y, 0))
        piece('Floor_WoodDark', (x, y, H * 3.12))                     # ceiling boards
for f in range(H):
    z = f * 3.12
    for x in range(-W + 1, W, 2):
        if f == 0 and abs(x) <= 1: piece('Wall_Arch', (x, -L, z), 0)    # south: the arch into the stacks
        else: piece(f'Wall_{WALL}_Straight', (x, -L, z), 0)
        if f == 0 and abs(x) <= 1: piece(f'Wall_{WALL}_Door_Round', (x, L, z), 180)   # north: the sea gate
        else: piece(f'Wall_{WALL}_Straight' if f == 0 else f'Wall_{WALL}_Window_Thin_Round', (x, L, z), 180)
    for y in range(-L + 1, L, 2):
        n = f'Wall_{WALL}_Window_Thin_Round' if f == 1 else f'Wall_{WALL}_Straight'
        piece(n, (-W, y, z), -90); piece(n, (W, y, z), 90)
for y in range(-L + 2, L, 2):
    b = box('Beam', (W * 2, 0.32, 0.38), (0, y, H * 3.12 - 0.2), dark)
# the sea gate itself: two iron leaves in the north doorway (they open in scene 3)
for sx in (-1, 1):   # one iron leaf filling each of the two north doorways (x = ±1)
    g = box('GateLeaf', (1.3, 0.14, 2.45), (sx * 1.0, L + 0.05, 1.22), iron); g['gate'] = sx
    for k in range(4): box('GateBand', (1.32, 0.18, 0.07), (sx * 1.0, L + 0.05, 0.35 + k * 0.6), mat('Rust', (0.32, 0.14, 0.08)))

# ------------------------------------------------------------------ the ring of six lecterns and their closed books
LECTERNS = []
for i in range(6):
    a = math.radians(i * 60 + 30); x, y = 3.0 * math.cos(a), 3.0 * math.sin(a); face = math.degrees(a) + 90
    box('LecternPost', (0.14, 0.14, 1.0), (x, y, 0.5), dark)
    box('LecternFoot', (0.5, 0.5, 0.06), (x, y, 0.03), dark)
    top = box('LecternTop', (0.62, 0.46, 0.05), (x, y, 1.05), wood, rot=(18, 0, face - 90))
    bk = box('Codex', (0.34, 0.26, 0.07), (x, y, 1.1), leather if i % 3 == 0 else leather2 if i % 3 == 1 else leather3, rot=(18, 0, face - 90))
    LECTERNS.append((x, y))
# a dais disc under the ring
c = cyl('Dais', 4.2, 0.12, (0, 0, 0.06), stone, 48)
r_ = cyl('RugRing', 3.5, 0.02, (0, 0, 0.125), rug, 48); r2 = cyl('RugInner', 2.5, 0.025, (0, 0, 0.13), stone, 48)

# ------------------------------------------------------------------ the candle wheel above the ring + floor candelabra
bpy.ops.mesh.primitive_torus_add(major_radius=2.2, minor_radius=0.06, location=(0, 0, 4.6)); wheel = bpy.context.object; wheel.data.materials.append(iron)
for k in range(4): box('WheelChain', (0.03, 0.03, 1.6), (2.2 * math.cos(k * 1.5708), 2.2 * math.sin(k * 1.5708), 5.45), iron)
for k in range(16):
    a = k * math.tau / 16; x, y = 2.2 * math.cos(a), 2.2 * math.sin(a)
    cyl('Candle', 0.035, 0.22, (x, y, 4.75), wax, 8); cyl('Flame', 0.02, 0.06, (x, y, 4.9), flame, 6)
point((0, 0, 4.4), 900, (1.0, 0.62, 0.3), 1.0)
for i in range(6):
    a = math.radians(i * 60); x, y = 4.6 * math.cos(a), 4.6 * math.sin(a)
    cyl('CandelabraPole', 0.05, 1.6, (x, y, 0.8), iron, 8)
    for d in (-0.18, 0, 0.18):
        cyl('Candle', 0.03, 0.2, (x + d, y, 1.7), wax, 8); cyl('Flame', 0.018, 0.05, (x + d, y, 1.83), flame, 6)
    point((x, y, 1.95), 120, (1.0, 0.58, 0.25), 0.3)

# ------------------------------------------------------------------ benches for the town along both walls
for side in (-1, 1):
    for y in range(-8, 9, 2):
        if abs(y) < 2: continue
        bx = side * 4.9
        box('BenchSeat', (0.42, 1.7, 0.08), (bx, y, 0.46), wood); box('BenchBack', (0.06, 1.7, 0.5), (bx + side * 0.2, y, 0.78), wood)
        for dy in (-0.75, 0.75): box('BenchLeg', (0.36, 0.06, 0.44), (bx, y + dy, 0.22), dark)

# ------------------------------------------------------------------ Vale's desk before the gate
box('ValeDesk', (2.2, 0.8, 0.9), (0, L - 2.2, 0.45), dark); box('ValeDeskTop', (2.3, 0.9, 0.06), (0, L - 2.2, 0.93), wood)
for k, (dx, m) in enumerate([(-0.7, leather), (-0.45, leather2), (0.6, paper)]): box('DeskBook', (0.3, 0.22, 0.08 + 0.04 * k), (dx, L - 2.2, 1.0 + 0.02 * k), m)
cyl('Inkwell', 0.05, 0.08, (0.2, L - 2.0, 1.0), iron, 10)

# ------------------------------------------------------------------ the stacks behind the south arch
SL = 12   # stacks depth
for x in range(-W + 1, W, 2):
    for y in range(-L - SL + 1, -L, 2):
        piece('Floor_WoodDark', (x, y, 0)); piece('Floor_WoodDark', (x, y, 3.12))
for x in range(-W + 1, W, 2): piece(f'Wall_{WALL}_Straight', (x, -L - SL, 0), 0)
for y in range(-L - SL + 1, -L, 2): piece(f'Wall_{WALL}_Straight', (-W, y, 0), -90); piece(f'Wall_{WALL}_Straight', (W, y, 0), 90)
books = [leather, leather2, leather3, mat('BookBrown', (0.3, 0.2, 0.1)), mat('BookBlack', (0.06, 0.05, 0.05))]
for row, x in enumerate((-3.6, -1.2, 1.2, 3.6)):
    for y0 in (-L - 3.0, -L - 7.5):
        box('Shelf', (0.5, 3.6, 2.9), (x, y0, 1.45), dark)
        for lv in range(5):
            z = 0.3 + lv * 0.55
            yy = y0 - 1.7
            while yy < y0 + 1.7:
                w = R.uniform(0.05, 0.11); hgt = R.uniform(0.3, 0.45)
                if R.random() < 0.12 and lv in (1, 3):   # a jar with a sleeping Spark
                    cyl('Jar', 0.11, 0.3, (x + 0.27 * (1 if row % 2 else -1), yy + 0.12, z + 0.15), jarm, 10); yy += 0.28; continue
                box('Book', (0.24, w, hgt), (x + 0.15 * (1 if row % 2 else -1), yy + w / 2, z + hgt / 2), R.choice(books)); yy += w + 0.005
point((0, -L - 5, 2.6), 300, (1.0, 0.6, 0.3), 0.5); point((0, -L - 10, 2.6), 180, (0.5, 0.7, 1.0), 0.5)

# ------------------------------------------------------------------ cold moonlight through the high windows (the "white" key)
for side in (-1, 1):
    for y in (-6, 0, 6): spot((side * 9.5, y, 6.5), (side * 2.0, y, 0), 2500, (0.62, 0.72, 1.0), 30)


# ------------------------------------------------------------------ dressing (owner: "a little full, not empty")
D = random.Random(5)
for side in (-1, 1):   # bookcases between the benches and banners on the walls
    for y in (-9.0, -1.0, 1.0, 9.0):
        prop('Bookcase_2', (side * 5.55, y, 0), 90 if side < 0 else -90, height=2.6)
    for y in (-6.0, 0.0, 6.0): prop('Banner_1', (side * 5.7, y, 3.6), 90 if side < 0 else -90, height=2.2)
for (x, y) in [(-0.8, 7.85), (0.75, 7.75)]: prop('CandleStick_Triple', (x, y, 0.96), 0, height=0.45)
prop('BookGroup_Medium_1', (0.3, 7.7, 0.96), 10, height=0.3); prop('Scroll_1', (-0.2, 7.9, 0.96), 40, height=0.08); prop('Scroll_2', (0.9, 8.0, 0.96), 80, height=0.08)
prop('BookStand', (-2.2, 7.6, 0), 0, height=1.3); prop('Chest_Wood', (2.6, 8.6, 0), 180, height=0.7); prop('Chest_Wood', (-3.4, 8.8, 0), 160, height=0.7)
for (x, y) in [(-5.2, 8.6), (5.2, 8.6), (-5.2, -8.6), (5.2, -8.6)]: prop('Vase_4', (x, y, 0), D.uniform(0, 360), height=0.8)
for (x, y) in [(-4.4, -4.0), (4.4, 4.0), (-4.4, 5.6)]: prop('Book_Stack_1', (x, y, 0.5), D.uniform(0, 360), height=0.2)
for (x, y) in [(-1.5, 9.4), (1.5, 9.4)]: prop('Torch_Metal', (x, y, 1.6), 180, height=0.7)
# the stacks: ladders, stacks of books on the floor, a reading table, cages, potions
prop('Table_Large', (0, -L - 5.2, 0), 90, height=0.8)
for (dx, n) in [(-0.5, 'BookGroup_Small_1'), (0.2, 'Book_7'), (0.6, 'CandleStick')]: prop(n, (dx, -L - 5.2, 0.8), D.uniform(0, 360), height=0.25)
for (x, y) in [(-4.8, -L - 2.0), (4.8, -L - 9.0), (-2.4, -L - 10.5), (2.4, -L - 1.6)]: prop('Book_Stack_2', (x, y, 0), D.uniform(0, 360), height=0.45)
for (x, y) in [(-5.3, -L - 6.0), (5.3, -L - 4.0)]: prop('Cage_Small', (x, y, 0), 0, height=0.8)
prop('Shelf_Small_Bottles', (5.5, -L - 11.4, 0), 180, height=1.6); prop('Chandelier', (0, -L - 5.2, 2.2), 0, height=0.9)

cams = {'wide': ((0, -9.2, 3.4), (0, 2.5, 1.0), 24), 'ring': ((2.8, -4.6, 1.6), (0, 0.6, 1.2), 32),
        'gate': ((0, -3.0, 1.8), (0, L, 1.6), 30), 'stacks': ((0.0, -L + 1.5, 1.7), (-0.6, -L - 8.0, 1.3), 30)}
marks = {'lecterns': [[round(x * 100), round(-y * 100), 0] for x, y in LECTERNS], 'vale': [0, -(L - 3.2) * 100, 0], 'gate': [0, -L * 100, 0],
         'arch': [0, L * 100, 0], 'stacks': [0, (L + 6) * 100, 0]}
finish(cams, marks, world_rgb=(0.01, 0.012, 0.02), exposure=-0.2)
