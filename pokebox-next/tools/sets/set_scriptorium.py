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
rust = mat('Rust', (0.32, 0.14, 0.08)); brass = mat('GateBrass', (0.55, 0.40, 0.15), 0.4)
for sx in (-1, 1):   # one iron leaf filling each of the two north doorways (x = ±1): riveted plate, vertical straps, a sigil boss
    cx = sx * 1.0; fy = L - 0.05                       # front face (hall side)
    g = box('GateLeaf', (1.3, 0.14, 2.45), (cx, L + 0.05, 1.22), iron); g['gate'] = sx
    GM = _M((cx, fy, 0))
    for k in (-0.45, 0.0, 0.45): dbox(GM, (0.09, 0.05, 2.4), (k, -0.02, 1.22), rust)                # vertical straps
    for zz in (0.25, 2.2): dbox(GM, (1.3, 0.06, 0.12), (0, -0.03, zz), rust)                          # top/bottom bands
    for k in (-0.45, 0.0, 0.45):
        for zz in (0.25, 0.7, 1.2, 1.7, 2.2): dcyl(GM, 0.022, 0.03, (k, -0.065, zz), brass, 8, rx=90)  # rivets
    dbox(GM, (0.34, 0.04, 0.34), (-sx * 0.42, -0.05, 1.25), brass, ry=45)                             # sigil boss
    dbox(GM, (0.2, 0.05, 0.2), (-sx * 0.42, -0.07, 1.25), iron, ry=45)
    dcyl(GM, 0.09, 0.025, (-sx * 0.42, -0.1, 1.0), iron, 12, rx=90); dcyl(GM, 0.06, 0.03, (-sx * 0.42, -0.1, 1.0), iron, 12, rx=90)  # ring pull
    dbox(GM, (0.04, 0.04, 0.12), (-sx * 0.42, -0.08, 1.12), iron)

# ------------------------------------------------------------------ the ring of six lecterns and their closed books
LECTERNS = []
for i in range(6):
    a = math.radians(i * 60 + 30); x, y = 3.0 * math.cos(a), 3.0 * math.sin(a); face = math.degrees(a) + 90
    box('LecternPost', (0.14, 0.14, 1.0), (x, y, 0.5), dark)
    box('LecternFoot', (0.5, 0.5, 0.06), (x, y, 0.03), dark)
    top = box('LecternTop', (0.62, 0.46, 0.05), (x, y, 1.05), wood, rot=(18, 0, face - 90))
    LM = _M((x, y, 1.0775), face - 90, 18)
    book(LM, (0, 0, 0.0), 0.075, 0.27, 0.36, cov=_bookmats()['cov'][(0, 2, 4, 0, 2, 4)[i]], lying=True, rng=random.Random(i))
    dbox(LM, (0.05, 0.02, 0.06), (0.17, -0.01, 0.04), _bookmats()['gilt'])   # brass clasp
    LECTERNS.append((x, y))
# a dais disc under the ring
c = cyl('Dais', 4.2, 0.12, (0, 0, 0.06), stone, 48)
r_ = cyl('RugRing', 3.5, 0.02, (0, 0, 0.125), rug, 48)
gold = mat('RugGold', (0.55, 0.40, 0.14)); rugd = mat('RugDark', (0.16, 0.05, 0.05))
cyl('RugB1', 3.36, 0.022, (0, 0, 0.126), gold, 48); cyl('RugB2', 3.30, 0.024, (0, 0, 0.127), rugd, 48); cyl('RugB3', 3.12, 0.026, (0, 0, 0.128), rug, 48)
cyl('RugB4', 2.62, 0.028, (0, 0, 0.129), gold, 48)
for k in range(12):   # woven diamonds around the ring
    a = k * math.tau / 12; box('RugDiamond', (0.22, 0.22, 0.03), (2.87 * math.cos(a), 2.87 * math.sin(a), 0.13), gold, rot=(0, 0, 45 + math.degrees(a)))
r2 = cyl('RugInner', 2.5, 0.032, (0, 0, 0.131), stone, 48)

# ------------------------------------------------------------------ the candle wheel above the ring + floor candelabra
bpy.ops.mesh.primitive_torus_add(major_radius=2.2, minor_radius=0.06, location=(0, 0, 4.6)); wheel = bpy.context.object; wheel.data.materials.append(iron)
for k in range(4): box('WheelChain', (0.03, 0.03, 1.6), (2.2 * math.cos(k * 1.5708), 2.2 * math.sin(k * 1.5708), 5.45), iron)
for k in range(16):
    a = k * math.tau / 16; x, y = 2.2 * math.cos(a), 2.2 * math.sin(a)
    candle((x, y, 4.64), 0.18 + 0.06 * ((k * 7) % 3) / 2, 0.035)
point((0, 0, 4.4), 900, (1.0, 0.62, 0.3), 1.0)
for i in range(6):
    a = math.radians(i * 60); x, y = 4.6 * math.cos(a), 4.6 * math.sin(a)
    cyl('CandelabraPole', 0.05, 1.6, (x, y, 0.8), iron, 8)
    for d in (-0.18, 0, 0.18):
        cyl('CandleCup', 0.05, 0.03, (x + d, y, 1.6), iron, 10); candle((x + d, y, 1.615), 0.14 + abs(d) * 0.5, 0.03)
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
DR = random.Random(11)
book_stack((-0.85, L - 2.0, 0.96), 6, 8, rng=DR); book_stack((0.95, L - 1.95, 0.96), 4, -20, rng=DR)
open_book((0.05, L - 2.35, 0.96), 180); papers((-0.35, L - 2.45, 0.96), 6, 0.18, rng=DR)
cyl('Inkwell', 0.045, 0.07, (0.45, L - 2.05, 0.995), iron, 10); box('Quill', (0.01, 0.01, 0.3), (0.47, L - 2.05, 1.12), wax, rot=(18, -14, 0))
candle((-0.5, L - 1.95, 0.96), 0.16, 0.03)

# ------------------------------------------------------------------ the stacks behind the south arch
SL = 12   # stacks depth
for x in range(-W + 1, W, 2):
    for y in range(-L - SL + 1, -L, 2):
        piece('Floor_WoodDark', (x, y, 0)); piece('Floor_WoodDark', (x, y, 3.12))
for x in range(-W + 1, W, 2): piece(f'Wall_{WALL}_Straight', (x, -L - SL, 0), 0)
for y in range(-L - SL + 1, -L, 2): piece(f'Wall_{WALL}_Straight', (-W, y, 0), -90); piece(f'Wall_{WALL}_Straight', (W, y, 0), 90)
JARMAT = jarm; SR = random.Random(21)
STACK_ROWS = (-3.6, -1.2, 1.2, 3.6)
for x in STACK_ROWS:
    for y0 in (-L - 3.0, -L - 7.5):
        for half in (-0.9, 0.9):
            if x > -4: bookcase((x - 0.22, y0 + half, 0), -90, w=1.8, h=2.9, d=0.42, levels=5, back=False, rng=SR)   # faces -X
            if x < 4: bookcase((x + 0.22, y0 + half, 0), 90, w=1.8, h=2.9, d=0.42, levels=5, back=False, rng=SR)    # faces +X
        box('StackSpine', (0.04, 3.6, 2.9), (x, y0, 1.45), dark)
# shelves along the stacks' back wall too
for xx in (-4.2, -2.4, 2.4, 4.2): bookcase((xx, -L - SL + 0.3, 0), 180, w=1.7, h=2.9, rng=SR)
# a rolling ladder leaning on a stack
for sx in (-0.2, 0.2): box('LadderRail', (0.05, 0.05, 3.0), (-1.2 + 0.55, -L - 6.0 + sx, 1.45), wood, rot=(0, -12, 0))
for k in range(9): box('LadderRung', (0.04, 0.42, 0.04), (-1.2 + 0.55 + 0.06 - k * 0.035, -L - 6.0, 0.3 + k * 0.32), wood)
point((0, -L - 5, 2.6), 300, (1.0, 0.6, 0.3), 0.5); point((0, -L - 10, 2.6), 180, (0.5, 0.7, 1.0), 0.5)

# ------------------------------------------------------------------ cold moonlight through the high windows (the "white" key)
for side in (-1, 1):
    for y in (-6, 0, 6): spot((side * 9.5, y, 6.5), (side * 2.0, y, 0), 2500, (0.62, 0.72, 1.0), 30)


# ------------------------------------------------------------------ dressing (owner: "a little full, not empty")
D = random.Random(5)
for side in (-1, 1):   # the hall is a library: full bookcases behind the benches along both walls, banners above
    for y in (-7.0, -5.0, -3.0, -1.0, 1.0, 3.0, 5.0, 7.0):
        bookcase((side * 5.6, y, 0), 90 if side < 0 else -90, w=1.9, h=2.7, d=0.42, levels=5, rng=D)
    for y in (-6.0, 0.0, 6.0): prop('Banner_1', (side * 5.7, y, 3.6), 90 if side < 0 else -90, height=2.2)
for (x, y) in [(-0.8, 7.85), (0.75, 7.75)]: prop('CandleStick_Triple', (x, y, 0.96), 0, height=0.45)
prop('BookStand', (-2.2, 7.6, 0), 0, height=1.3); prop('Chest_Wood', (2.6, 8.6, 0), 180, height=0.7); prop('Chest_Wood', (-3.4, 8.8, 0), 160, height=0.7)
open_book((-2.2, 7.6, 1.32), 180, tilt=-15)
for (x, y) in [(-5.2, 8.6), (5.2, 8.6), (-5.2, -8.6), (5.2, -8.6)]: prop('Vase_4', (x, y, 0), D.uniform(0, 360), height=0.8)
for (x, y) in [(-4.3, -4.0), (4.3, 4.0), (-4.3, 5.9), (4.3, -6.1)]: book_stack((x, y, 0.5), rng=D)   # left on the benches
for (x, y, n) in [(-5.0, 8.2, 5), (5.0, 8.1, 3), (-5.0, -8.2, 4), (5.0, -8.2, 6)]:                    # floor candle clusters
    for k in range(n): candle((x + D.uniform(-0.25, 0.25), y + D.uniform(-0.25, 0.25), 0), D.uniform(0.08, 0.32), D.uniform(0.025, 0.04))
book_stack((3.3, 8.2, 0), 8, rng=D); book_stack((3.6, 8.5, 0), 5, rng=D); book_stack((-4.0, 8.3, 0), 6, rng=D)
# the north wall: two tall banners flanking the gate, a gilt Codex sigil above it, sconces, a notice board of the Rite
HM = Matrix(); gilt = _bookmats()['gilt']
for sx in (-1, 1): prop('Banner_1', (sx * 3.3, L - 0.45, 2.7), 180, height=2.6)
dcyl(HM, 0.62, 0.05, (0, L - 0.36, 3.75), gilt, 32, rx=90); dcyl(HM, 0.5, 0.06, (0, L - 0.37, 3.75), mat('SigilDark', (0.08, 0.06, 0.05)), 32, rx=90)
dbox(HM, (0.6, 0.07, 0.6), (0, L - 0.4, 3.75), gilt, ry=45); dbox(HM, (0.4, 0.08, 0.4), (0, L - 0.41, 3.75), mat('SigilRed', (0.45, 0.07, 0.05)), ry=45)
for sx in (-1, 1):
    for xx in (2.3, 4.6):
        dbox(HM, (0.08, 0.25, 0.08), (sx * xx, L - 0.45, 2.3), iron); dcyl(HM, 0.08, 0.04, (sx * xx, L - 0.6, 2.34), iron, 10); candle((sx * xx, L - 0.6, 2.36), 0.18, 0.03)
        point((sx * xx, L - 0.8, 2.7), 40, (1.0, 0.6, 0.28), 0.2)
dbox(HM, (1.2, 0.04, 0.9), (-4.3, L - 0.35, 1.6), mat('Cork', (0.45, 0.32, 0.18)))
for k in range(6): dbox(HM, (0.21, 0.01, 0.28), (-4.75 + (k % 3) * 0.42 + DR.uniform(-0.03, 0.03), L - 0.38, 1.82 - (k // 3) * 0.38), _bookmats()['page'], ry=DR.uniform(-8, 8))
for (x, y) in [(-1.5, 9.4), (1.5, 9.4)]: prop('Torch_Metal', (x, y, 1.6), 180, height=0.7)
# the stacks: reading table, floor piles, cages, potions
prop('Table_Large', (0, -L - 5.2, 0), 90, height=0.8)
open_book((0.0, -L - 5.0, 0.8), 90); book_stack((-0.25, -L - 5.8, 0.8), 5, rng=D); book_stack((0.2, -L - 4.4, 0.8), 3, rng=D)
papers((0.2, -L - 5.5, 0.8), 5, 0.15, rng=D); candle((-0.25, -L - 4.6, 0.8), 0.18); candle((0.25, -L - 6.0, 0.8), 0.1)
for (x, y) in [(-5.0, -L - 2.0), (5.0, -L - 9.0), (-2.4, -L - 10.6), (2.4, -L - 1.4), (-5.1, -L - 10.0)]: book_stack((x, y, 0), D.randint(5, 9), D.uniform(0, 90), rng=D)
for (x, y) in [(-5.3, -L - 6.0), (5.3, -L - 4.0)]: prop('Cage_Small', (x, y, 0), 0, height=0.8)
prop('Chandelier', (0, -L - 5.2, 2.2), 0, height=0.9)

cams = {'wide': ((0, -9.2, 3.4), (0, 2.5, 1.0), 24), 'ring': ((2.8, -4.6, 1.6), (0, 0.6, 1.2), 32),
        'gate': ((0, -3.0, 1.8), (0, L, 1.6), 30), 'stacks': ((0.0, -L + 1.5, 1.7), (-0.6, -L - 8.0, 1.3), 30)}
marks = {'lecterns': [[round(x * 100), round(-y * 100), 0] for x, y in LECTERNS], 'vale': [0, -(L - 3.2) * 100, 0], 'gate': [0, -L * 100, 0],
         'arch': [0, L * 100, 0], 'stacks': [0, (L + 6) * 100, 0]}
finish(cams, marks, world_rgb=(0.01, 0.012, 0.02), exposure=-0.2)
