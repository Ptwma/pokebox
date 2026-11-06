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
box('CotFrame', (0.85, 1.9, 0.35), (-2.2, 0.9, 0.25), dark); box('CotBlanket', (0.8, 1.6, 0.12), (-2.2, 0.75, 0.48), blanket)
box('CotPillow', (0.6, 0.3, 0.1), (-2.2, 1.6, 0.48), cup)
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


# ------------------------------------------------------------------ dressing (owner: "a little full, not empty")
D = random.Random(3)
prop('Mug', (1.75, -1.3, 0.78), 0, height=0.1); prop('Bottle_1', (2.2, -1.25, 0.78), 0, height=0.28); prop('CandleStick', (1.55, -1.6, 0.78), 0, height=0.25)
prop('Chest_Wood', (-2.9, -1.2, 0), 60, height=0.6)
prop('Rope_3', (2.6, -0.8, 0.01), 30, height=0.2); prop('Bucket_Wooden_1', (-1.6, -2.7, 0), 0, height=0.4); prop('CandleStick_Stand', (-0.9, 2.6, 0), 0, height=1.3)
prop('Stool', (-1.3, 0.2, 0), 0, height=0.45); prop('Book_Stack_1', (-1.3, 0.2, 0.45), 20, height=0.15)
prop('Chair_1', (2.5, -2.2, 0), 210, height=0.95); prop('Pot_1', (0.2, 2.9, 1.4), 0, height=0.25)
for k in range(3): prop('k_survival/fish', (-2.7 + k * 0.25, -2.2, 0.0), D.uniform(0, 360), height=0.1)

point((0, 0, 1.6), 1400, (1.0, 0.75, 0.42), 0.6)   # the lamp
point((-2.4, -2.0, 2.4), 140, (0.6, 0.7, 1.0), 1.0)  # cool window fill
cams = {'wide': ((2.6, -2.4, 1.7), (-1.6, 1.2, 1.0), 22), 'lamp': ((1.6, -1.8, 1.5), (0, 0, 1.6), 30), 'cot': ((-0.3, -1.9, 1.3), (-2.2, 0.9, 0.45), 30)}
marks = {'cot': [-220, -90, 0], 'table': [190, 140, 0], 'lamp': [0, 0, 0], 'trap': [200, -140, 0], 'cupboard': [0, -290, 0]}
finish(cams, marks, world_rgb=(0.32, 0.36, 0.44), exposure=-0.1)
