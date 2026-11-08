# Sigil & Spark v4 — set #4: THE LAMP ROOM at the top of the lighthouse (Ep1 scene 6 "Dawn", 6b "The Lamp Room").
#   blender -b --python set_lighthouse.py -- <SRC> <out.png> [wide|lamp|cot|export]
# A round room 30 m above the sea (the stage sits high so the windows look DOWN on the harbour): a ring of tall window
# frames, a stone sill, the great lamp on its brass pedestal in the middle, Gus's cot, a table with the tea cups, the oil
# cupboard (the egg), the trapdoor to the stair. Colour key: grey-blue dawn / the lamp's warm sweep at night.
import os
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kit.py')).read())

RAD = 3.6
wood = mat('FloorWood', (0.30, 0.20, 0.12)); dark = mat('DarkWood', (0.12, 0.08, 0.06)); brass = mat('Brass', (0.55, 0.40, 0.16), 0.35)
stone = mat('WhiteStone', (0.70, 0.68, 0.62)); redroof = mat('RoofRed', (0.42, 0.09, 0.07)); iron = mat('Iron', (0.04, 0.04, 0.045), 0.5)
blanket = mat('Blanket', (0.36, 0.16, 0.12)); cup = mat('Cup', (0.82, 0.80, 0.74)); lamp = glow('LampRoom', (1.0, 0.82, 0.5), 6.0)

cyl('Floor', RAD, 0.2, (0, 0, -0.1), wood, 48)
SEG = 24
for k in range(SEG):   # the stone sill: a ring of blocks (a solid cylinder would fill the room)
    a = (k + 0.5) * math.tau / SEG
    box('Sill', (0.35, 2 * (RAD + 0.1) * math.sin(math.pi / SEG) + 0.02, 1.0), ((RAD - 0.08) * math.cos(a), (RAD - 0.08) * math.sin(a), 0.5), stone, rot=(0, 0, math.degrees(a)))
N = 12
for k in range(N):   # window mullions + a top ring: open frames (no glass: the wind and the rain come in)
    a = k * math.tau / N; x, y = (RAD - 0.05) * math.cos(a), (RAD - 0.05) * math.sin(a)
    box('Mullion', (0.08, 0.08, 2.4), (x, y, 2.2), iron, rot=(0, 0, math.degrees(a)))
    box('Transom', (0.06, 2 * RAD * math.sin(math.pi / N), 0.06), ((RAD - 0.05) * math.cos(a + math.pi / N), (RAD - 0.05) * math.sin(a + math.pi / N), 2.1), iron, rot=(0, 0, math.degrees(a + math.pi / N)))
for k in range(SEG):
    a = (k + 0.5) * math.tau / SEG
    box('TopRing', (0.4, 2 * (RAD + 0.15) * math.sin(math.pi / SEG) + 0.02, 0.3), ((RAD - 0.05) * math.cos(a), (RAD - 0.05) * math.sin(a), 3.5), stone, rot=(0, 0, math.degrees(a)))
cyl('Ceiling', RAD + 0.2, 0.08, (0, 0, 3.66), mat('CeilWood', (0.2, 0.13, 0.08)), 48)
bpy.ops.mesh.primitive_cone_add(radius1=RAD + 0.5, depth=2.2, vertices=32, location=(0, 0, 4.75)); roof = bpy.context.object; roof.data.materials.append(redroof)
# the great lamp
cyl('Pedestal', 0.35, 1.0, (0, 0, 0.5), brass, 16); cyl('PedestalFoot', 0.6, 0.12, (0, 0, 0.06), brass, 16)
cyl('LampLens', 0.55, 1.1, (0, 0, 1.6), lamp, 24); cyl('LampCap', 0.6, 0.12, (0, 0, 2.2), brass, 24); cyl('LampBase', 0.6, 0.12, (0, 0, 1.02), brass, 24)
for k in range(8): box('LensRib', (0.03, 0.03, 1.1), (0.56 * math.cos(k * 0.785), 0.56 * math.sin(k * 0.785), 1.6), brass)
# Gus's cot (Omari sleeps on it if he was saved), a table with two cups, the oil cupboard, a chair, the trapdoor
for sx in (-1, 1): box('CotRail', (0.06, 1.9, 0.12), (-2.2 + sx * 0.4, 0.9, 0.36), dark)
for sy in (-1, 1): box('CotEnd', (0.86, 0.06, 0.3 if sy > 0 else 0.18), (-2.2, 0.9 + sy * 0.93, 0.45 if sy > 0 else 0.39), dark)
box('Table', (0.9, 0.7, 0.06), (1.9, -1.4, 0.75), dark)
for (dx, dy) in [(-0.35, -0.25), (0.35, -0.25), (-0.35, 0.25), (0.35, 0.25)]: box('TableLeg', (0.06, 0.06, 0.72), (1.9 + dx, -1.4 + dy, 0.36), dark)
cyl('TeaCup', 0.05, 0.08, (1.7, -1.35, 0.82), cup, 10); cyl('TeaCup', 0.05, 0.08, (2.05, -1.5, 0.82), cup, 10); cyl('Teapot', 0.1, 0.16, (1.95, -1.2, 0.86), iron, 12)
box('Chair', (0.45, 0.45, 0.05), (1.2, -1.9, 0.46), dark); box('ChairBack', (0.45, 0.05, 0.5), (1.2, -2.12, 0.72), dark)
box('OilCupboard', (0.9, 0.5, 1.4), (0.0, 2.9, 0.7), dark, rot=(0, 0, 0)); box('CupboardDoor', (0.4, 0.03, 1.2), (-0.2, 2.64, 0.75), mat('DoorWood', (0.22, 0.14, 0.08)))
box('Trapdoor', (1.0, 1.0, 0.03), (2.0, 1.4, 0.01), dark); box('TrapRail', (1.1, 0.05, 0.9), (2.0, 1.95, 0.45), iron)
for (x, y) in [(-1.2, -2.6), (2.6, 0.2)]: cyl('OilCan', 0.12, 0.3, (x, y, 0.15), mat('Tin', (0.35, 0.36, 0.38), 0.4), 12)
# outside the windows: a walkway rail (the gallery)
bpy.ops.mesh.primitive_torus_add(major_radius=RAD + 0.9, minor_radius=0.03, location=(0, 0, 1.05)); rail = bpy.context.object; rail.data.materials.append(iron)
cyl('Gallery', RAD + 0.95, 0.12, (0, 0, -0.06), stone, 48)


# ------------------------------------------------------------------ DETAIL pass (owner 19:59: "I want details")
DL = random.Random(8); I = Matrix()
planks = [mat('Plank1', (0.32, 0.21, 0.12)), mat('Plank2', (0.27, 0.17, 0.10)), mat('Plank3', (0.36, 0.25, 0.15))]
x = -RAD + 0.1
while x < RAD - 0.1:   # floor boards, each row broken into staggered lengths (ink lines on every seam)
    half = math.sqrt(max(0.0, (RAD - 0.3) ** 2 - x ** 2)); y = -half + DL.uniform(0, 0.6)
    while y < half - 0.1:
        ln = min(DL.uniform(0.7, 1.6), half - y); dbox(I, (0.17, ln - 0.01, 0.012), (x, y + ln / 2, 0.006), DL.choice(planks)); y += ln
    x += 0.18
for k in range(SEG):   # sill cap (darker, proud) and a wooden skirting at the floor: breaks the plain band
    a = (k + 0.5) * math.tau / SEG; ln = 2 * (RAD + 0.1) * math.sin(math.pi / SEG) + 0.02
    dbox(I, (0.46, ln, 0.06), ((RAD - 0.12) * math.cos(a), (RAD - 0.12) * math.sin(a), 1.03), mat('SillCap', (0.52, 0.50, 0.46)), rz=math.degrees(a))
    dbox(I, (0.05, ln, 0.14), ((RAD - 0.27) * math.cos(a), (RAD - 0.27) * math.sin(a), 0.07), dark, rz=math.degrees(a))
    if k % 2 == 0: dbox(I, (0.02, 0.02, 0.9), ((RAD - 0.255) * math.cos(a), (RAD - 0.255) * math.sin(a), 0.5), mat('SillSeam', (0.45, 0.43, 0.40)), rz=math.degrees(a))
prism = mat('LensPrism', (0.55, 0.62, 0.62), 0.2)
for k in range(9): dcyl(I, 0.575, 0.025, (0, 0, 1.1 + k * 0.125), prism if k % 2 else brass, 24)   # fresnel prism rings
for k in range(6): dbox(I, (0.05, 0.05, 0.7), (0.66 * math.cos(k * 1.047), 0.66 * math.sin(k * 1.047), 2.6), brass, rz=math.degrees(k * 1.047))  # chimney struts
dcyl(I, 0.18, 0.5, (0, 0, 3.1), iron, 12, r2=0.12)                                                     # smoke flue
# the cot: legs, a straw mattress, a rumpled blanket hanging over the side, pillow, boots and a coat on a peg
for (dx, dy) in [(-0.38, -0.88), (0.38, -0.88), (-0.38, 0.88), (0.38, 0.88)]: dbox(I, (0.07, 0.07, 0.42), (-2.2 + dx, 0.9 + dy, 0.21), dark)
dbox(I, (0.78, 1.82, 0.1), (-2.2, 0.9, 0.47), mat('Straw', (0.55, 0.45, 0.25)))
dbox(I, (0.86, 1.2, 0.05), (-2.18, 0.55, 0.555), blanket, rx=0, ry=4); dbox(I, (0.04, 1.1, 0.32), (-1.77, 0.55, 0.4), blanket, ry=8)
dbox(I, (0.5, 0.28, 0.12), (-2.2, 1.6, 0.58), cup, rz=6)
leather = mat('BootLeather', (0.14, 0.09, 0.06))
for dx in (-0.12, 0.08): dbox(I, (0.11, 0.28, 0.08), (-1.6 + dx, 1.5, 0.04), leather, rz=DL.uniform(-15, 15)); dbox(I, (0.1, 0.1, 0.3), (-1.6 + dx, 1.4, 0.19), leather)
dbox(I, (0.05, 0.05, 1.8), (-2.95, 1.95, 0.9), dark); dbox(I, (0.3, 0.06, 0.04), (-2.85, 1.95, 1.75), dark)   # coat stand
dbox(I, (0.45, 0.12, 0.9), (-2.85, 1.95, 1.3), mat('Oilskin', (0.55, 0.45, 0.12)), rz=-30)                    # oilskin coat
# the oil cupboard: panelled doors, iron handles, a funnel and cans
for dx in (-0.22, 0.22):
    dbox(I, (0.36, 0.02, 0.5), (dx, 2.63, 1.05), mat('DoorWood', (0.22, 0.14, 0.08))); dbox(I, (0.36, 0.02, 0.5), (dx, 2.63, 0.42), mat('DoorWood', (0.22, 0.14, 0.08)))
    dcyl(I, 0.02, 0.04, (dx * 0.3, 2.61, 0.8), iron, 8, rx=90)
dcyl(I, 0.1, 0.12, (0.25, 2.9, 1.46), mat('Tin', (0.35, 0.36, 0.38), 0.4), 12, r2=0.02)
# things left on the stone sill: spyglass, jars, a lantern, a bottle, a coil of rope, shells
for k, a in enumerate((200, 215, 232, 300, 318, 335, 20, 40, 120, 140)):
    r = RAD - 0.2; x, y = r * math.cos(math.radians(a)), r * math.sin(math.radians(a)); kind = k % 5
    if kind == 0: dcyl(I, 0.03, 0.45, (x, y, 1.04), brass, 10, rx=90, rz=a)
    elif kind == 1: dcyl(I, 0.06, 0.16, (x, y, 1.08), mat('JarGlass', (0.40, 0.50, 0.45), 0.2), 10); dcyl(I, 0.05, 0.03, (x, y, 1.175), dark, 10)
    elif kind == 2: candle((x, y, 1.0), 0.1, 0.03)
    elif kind == 3: dcyl(I, 0.035, 0.22, (x, y, 1.11), mat('BottleGreen', (0.10, 0.25, 0.12), 0.2), 10); dcyl(I, 0.012, 0.06, (x, y, 1.25), dark, 6)
    else:
        for j in range(4): dcyl(I, 0.12 - j * 0.02, 0.025, (x, y, 1.012 + j * 0.025), mat('RopeHemp', (0.55, 0.45, 0.28)), 12)

# ------------------------------------------------------------------ dressing (owner: "a little full, not empty")
D = random.Random(3)
prop('Mug', (1.75, -1.3, 0.78), 0, height=0.1); prop('Bottle_1', (2.2, -1.25, 0.78), 0, height=0.28); prop('CandleStick', (1.55, -1.6, 0.78), 0, height=0.25)
prop('Chest_Wood', (-2.3, -0.95, 0), 60, height=0.6)   # QA: was through the sill/skirting
prop('Bucket_Wooden_1', (-1.45, -2.45, 0), 0, height=0.4); prop('CandleStick_Stand', (-0.9, 2.6, 0), 0, height=1.3)
prop('Stool', (-1.3, 0.2, 0), 0, height=0.45); book_stack((-1.3, 0.2, 0.45), 4, 20, rng=D)
open_book((1.95, -1.55, 0.78), 200, w=0.3, d=0.22)          # the keeper's log, open
papers((2.25, -1.0, 0.78), 4, 0.12, rng=D); candle((1.55, -1.1, 0.78), 0.12, 0.025)
bookcase((-1.9, 2.3, 0), 39.7, w=0.9, h=1.3, d=0.32, levels=3, rng=D)   # a small shelf of charts and almanacs
prop('Chair_1', (2.3, -1.9, 0), 210, height=0.95); prop('Pot_1', (-0.2, 2.95, 1.4), 0, height=0.25)   # QA: pot was inside the tin funnel
for k in range(3): prop('k_survival/fish', (-1.45 + (k - 1) * 0.07, -2.45 + (k % 2) * 0.05, 0.3 + k * 0.03), D.uniform(0, 360), height=0.1, tilt=(0, 25))   # QA: the catch sits in the bucket, not on the floor

point((0, 0, 1.6), 1400, (1.0, 0.75, 0.42), 0.6)   # the lamp
point((-2.4, -2.0, 2.4), 140, (0.6, 0.7, 1.0), 1.0)  # cool window fill
cams = {'wide': ((2.6, -2.4, 1.7), (-1.6, 1.2, 1.0), 22), 'lamp': ((1.6, -1.8, 1.5), (0, 0, 1.6), 30), 'cot': ((-0.3, -1.9, 1.3), (-2.2, 0.9, 0.45), 30)}
marks = {'cot': [-220, -90, 0], 'table': [190, 140, 0], 'lamp': [0, 0, 0], 'trap': [200, -140, 0], 'cupboard': [0, -290, 0]}
finish(cams, marks, world_rgb=(0.32, 0.36, 0.44), exposure=-0.1)
