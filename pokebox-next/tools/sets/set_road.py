# Sigil & Spark v4 — set #5: THE NORTH ROAD / MILESTONE (Ep1 scene 8 "The Road").
#   blender -b --python set_road.py -- <SRC> <out.png> [wide|stone|north|export]
# The cliff road out of Lumen Harbor at violet dusk: the town's north gate behind, a rutted dirt road between dry-stone
# walls, the old milestone ("LUMEN HARBOR 0 · NORTHREACH 40"), ONE lantern on a post (the only warm light), a wayside
# shrine with candles, a broken cart, wind-bent dead trees and pines, the cliff edge with a fence and the sea far below.
# Colour key: violet dusk × one lantern. The stage sits 15 m up (the town's sea shows under the cliff).
import os
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kit.py')).read())
import bmesh

DR = random.Random(31); I = Matrix()
grass = mat('MoorGrass', (0.20, 0.24, 0.13)); grass2 = mat('MoorGrassDry', (0.34, 0.31, 0.17)); dirt = mat('RoadDirt', (0.30, 0.22, 0.15))
rut = mat('RoadRut', (0.24, 0.17, 0.11)); stone = mat('DryStone', (0.42, 0.40, 0.37)); stone2 = mat('DryStoneDark', (0.28, 0.27, 0.26))
moss = mat('Moss', (0.18, 0.26, 0.12)); wood = mat('PostWood', (0.22, 0.15, 0.09)); iron = mat('Iron', (0.04, 0.04, 0.045), 0.5)
cliff = mat('CliffRock', (0.30, 0.28, 0.27)); lampg = glow('LanternGlass', (1.0, 0.55, 0.2), 6.0); gilt = mat('Gilt', (0.62, 0.45, 0.16), 0.35)
cloth = mat('ShrineCloth', (0.45, 0.08, 0.06)); wax = mat('Wax', (0.92, 0.88, 0.76))

# ------------------------------------------------------------------ the ground: a moor that rolls up inland, cut by the cliff
X0, X1, Y0, Y1, N = -22.0, 30.0, -8.0, 26.0, 1
bm = bmesh.new(); nx, ny = 104, 68; vs = []
for j in range(ny + 1):
    row = []
    for i in range(nx + 1):
        x = X0 + (X1 - X0) * i / nx; y = Y0 + (Y1 - Y0) * j / ny
        h = 0.0 if abs(y) < 2.6 else (0.06 * (abs(y) - 2.6)) ** 1.0 * (1 if y > 0 else 0.4)        # flat road bed, rising inland
        h += 0.18 * math.sin(x * 0.35 + 1.3) * math.sin(y * 0.4) * min(1, abs(y) / 4) + 0.04 * math.sin(x * 2.1 + y * 1.7)
        if y > 6: h += 0.07 * (y - 6) ** 1.25
        row.append(bm.verts.new((x, y, h)))
    vs.append(row)
for j in range(ny):
    for i in range(nx):
        f = bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i])); f.material_index = 0
me = bpy.data.meshes.new('Moor'); bm.to_mesh(me); bm.free(); me.materials.append(grass)
ground = bpy.data.objects.new('Moor', me); sc.collection.objects.link(ground)
# the cliff face down to the sea (rock blocks stepping down from the edge at y = -8)
for k in range(28):
    x = X0 + k * 1.9 + DR.uniform(-.3, .3)
    for d in range(4):
        dbox(I, (2.4, 1.6 + d * .5, 4.2), (x, -8.6 - d * 1.1, -2.0 - d * 3.6), DR.choice([cliff, stone2]), rz=DR.uniform(-8, 8), rx=DR.uniform(-6, 6))

# ------------------------------------------------------------------ the road: dirt bed, two wheel ruts, puddles, stones
dbox(I, (X1 - X0, 4.2, 0.04), ((X0 + X1) / 2, 0, 0.02), dirt)
for yy in (-0.75, 0.75): dbox(I, (X1 - X0, 0.42, 0.025), ((X0 + X1) / 2, yy + DR.uniform(-.05, .05), 0.035), rut)
for k in range(6):
    x = DR.uniform(X0 + 3, X1 - 3); dcyl(I, DR.uniform(.35, .7), .01, (x, DR.choice((-.75, .75)), .05), mat('Puddle', (0.03, 0.035, 0.05), 0.05), 16)
for k in range(60): dbox(I, (DR.uniform(.06, .18),) * 2 + (DR.uniform(.04, .08),), (DR.uniform(X0, X1), DR.uniform(-2.0, 2.0), .05), DR.choice([stone, stone2]), rz=DR.uniform(0, 90))

# ------------------------------------------------------------------ dry-stone walls both sides (stacked uneven stones, mossy caps, a gap)
def drywall(xa, xb, y, h=0.9):
    x = xa
    while x < xb:
        if 8.0 < x < 10.2 and y > 0: x += 2.2; continue          # the gap to the inland track
        z = 0.0; row = 0
        while z < h:
            w = DR.uniform(.35, .7); hh = DR.uniform(.16, .26)
            dbox(I, (w, DR.uniform(.42, .55), hh), (x + w / 2 + (row % 2) * .15, y + DR.uniform(-.04, .04), z + hh / 2), DR.choice([stone, stone, stone2]), rz=DR.uniform(-4, 4), ry=DR.uniform(-3, 3))
            z += hh * .92; row += 1
        if DR.random() < .55: dbox(I, (DR.uniform(.3, .6), .5, .08), (x + .3, y, z + .02), moss)
        x += DR.uniform(.38, .66)
drywall(X0 + 6, X1 - 1, 2.55); drywall(X0 + 6, X1 - 1, -2.55, 0.7)

# ------------------------------------------------------------------ the town's north gate behind the road (stone arch, walls, a lamp)
prop('k_pirate/castle-gate', (X0 + 4.0, 0, 0), 90, height=5.5)
for yy in (-5.2, 5.2): prop('k_pirate/castle-wall', (X0 + 4.0, yy, 0), 90, height=4.2)

# ------------------------------------------------------------------ the milestone: a weathered stone with a carved, gilt-filled inscription
MS = _M((6.0, 2.05, 0), 0)
dbox(MS, (0.62, 0.34, 0.16), (0, 0, .08), stone2)
dbox(MS, (0.48, 0.26, 1.05), (0, 0, .66), stone, ry=2)
dcyl(MS, 0.24, 0.26, (0, 0, 1.18), stone, 16, rx=90)                     # rounded top
for k, w in enumerate((.34, .22, .30, .26)): dbox(MS, (w, .02, .035), (0, -.135, 1.05 - k * .13), gilt)   # "LUMEN HARBOR / 0 / NORTHREACH / 40"
dbox(MS, (.2, .02, .2), (0, -.135, .46), gilt, ry=45)                    # the Codex sigil
dbox(MS, (.5, .3, .07), (0, .0, .06), moss); dbox(MS, (.12, .27, .4), (.18, 0, .3), moss)
# ------------------------------------------------------------------ ONE lantern on a post (the scene's only warm light)
LP = (5.0, -2.1, 0)
dbox(I, (.12, .12, 2.6), (LP[0], LP[1], 1.3), wood); dbox(I, (.06, .55, .06), (LP[0], LP[1] + .25, 2.5), wood)
dbox(I, (.19, .19, .24), (LP[0], LP[1] + .5, 2.22), lampg)
for sx in (-1, 1):
    for sy in (-1, 1): dbox(I, (.025, .025, .3), (LP[0] + sx * .1, LP[1] + .5 + sy * .1, 2.22), iron)   # an open iron frame: the glass shows
for zz in (2.07, 2.37): dbox(I, (.23, .23, .03), (LP[0], LP[1] + .5, zz), iron)
dcyl(I, .14, .08, (LP[0], LP[1] + .5, 2.42), iron, 8, r2=.03)
point((LP[0], LP[1] + .5, 2.15), 520, (1.0, 0.55, 0.22), 0.15)
# ------------------------------------------------------------------ a wayside shrine (little roof, red cloth, candles, offerings)
SH = _M((12.5, 3.3, 0), 180)
dbox(SH, (.16, .16, 1.3), (0, 0, .65), wood); dbox(SH, (.7, .45, .06), (0, 0, 1.32), wood)
dbox(SH, (.62, .02, .5), (0, .2, 1.58), wood); dbox(SH, (.8, .35, .04), (0, -.06, 1.88), wood, rx=-30); dbox(SH, (.8, .35, .04), (0, .1, 1.88), wood, rx=30)
dbox(SH, (.4, .02, .32), (0, .18, 1.55), cloth)
for k in range(4): candle((DR.uniform(-.25, .25), DR.uniform(-.12, .1), 1.35), DR.uniform(.06, .14), .025, M=SH)
point((12.5, 3.2, 1.6), 60, (1.0, 0.6, 0.28), 0.1)

# ------------------------------------------------------------------ nature and leftovers (CC0 kits)
prop('k_town/cart', (17.5, -3.4, 0), 200, height=1.4, tilt=(0, 9))                # a cart with a broken wheel in the ditch
prop('k_survival/signpost', (9.6, 2.9, 0), 60, height=2.2)
for (x, y, n, h) in [(-6.0, 6.5, 'q_nature/DeadTree_2', 5.0), (14.0, 5.6, 'q_nature/DeadTree_4', 4.4), (24.0, 4.8, 'q_nature/DeadTree_1', 5.5),
                     (2.0, -5.6, 'q_nature/DeadTree_3', 3.2), (20.0, -5.4, 'q_nature/DeadTree_5', 3.0)]:
    prop(n, (x, y, 0.15), DR.uniform(0, 360), height=h, tilt=(0, -6))          # bent by the north wind
for k in range(14):
    x = DR.uniform(-12, 30); y = DR.uniform(9, 24); prop(DR.choice(['q_nature/Pine_1', 'q_nature/Pine_3', 'q_nature/Pine_4']), (x, y, 0.3 + 0.07 * (y - 6) ** 1.25), DR.uniform(0, 360), height=DR.uniform(5, 8))
for k in range(26):
    x = DR.uniform(X0 + 6, X1); y = DR.choice([DR.uniform(2.9, 6), DR.uniform(-6.8, -2.9)])
    prop(DR.choice(['q_nature/Grass_Wispy_Tall', 'q_nature/Grass_Common_Tall', 'q_nature/Grass_Wispy_Short', 'q_nature/Bush_Common']), (x, y, 0.05), DR.uniform(0, 360), height=DR.uniform(.35, .8))
for (x, y, s) in [(-2, -4.2, 1.1), (11, -6.2, 1.6), (22.5, 7.5, 1.4), (27, -4.5, 0.9), (4, 7.0, 1.0)]:
    prop(DR.choice(['k_survival/rock-a', 'k_survival/rock-b', 'k_town/rock-large']), (x, y, 0), DR.uniform(0, 360), height=s)
# a fence along the cliff edge (posts + two rails, one section broken)
for k in range(26):
    x = X0 + 6 + k * 1.9
    if 11 < x < 15: continue
    dbox(I, (.1, .1, 1.0), (x, -7.2, .5), wood, ry=DR.uniform(-5, 5))
    for zz in (.45, .85): dbox(I, (1.95, .05, .07), (x + .95, -7.2, zz), wood, ry=DR.uniform(-2, 2))
dbox(I, (1.9, .05, .07), (13.0, -7.3, .2), wood, ry=25)

point((-14.0, 0.0, 4.5), 300, (1.0, 0.6, 0.3), 1.0)        # the gate lamp behind
cams = {'wide': ((-3.0, -4.6, 1.7), (9.0, 1.5, 1.1), 26), 'stone': ((4.2, -0.6, 1.45), (6.0, 2.0, 0.9), 34),
        'north': ((-8.0, 0.4, 1.8), (24.0, 0.0, 1.5), 30)}
marks = {'milestone': [600, -205, 0], 'lantern': [500, 210, 0], 'shrine': [1250, -330, 0], 'gate': [-1800, 0, 0], 'cart': [1750, 340, 0]}
sea = box('SeaPreview', (300, 200, .1), (0, -100, -15.0), mat('SeaPreviewM', (0.05, 0.07, 0.11), 0.1))   # Unreal: the town's own sea
finish(cams, marks, world_rgb=(0.20, 0.14, 0.26), exposure=-0.3, drop=(sea,))
