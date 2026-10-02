# Pokebox regional buildings (towns2.glb) — run in Blender after tt_lib (blender_toon_town.py)

import bpy, bmesh, math, random
from mathutils import Vector, Matrix
exec(bpy.data.texts['tt_lib'].as_string(), globals())
PAL.update({
 'moss': (0.40,0.60,0.30), 'thatch': (0.78,0.62,0.34), 'beam': (0.32,0.21,0.13), 'slate': (0.32,0.40,0.62), 'snow': (0.96,0.98,1.0),
 'logs': (0.62,0.40,0.22), 'concrete': (0.80,0.80,0.83), 'neon': (1.0,0.86,0.18), 'adobe': (0.93,0.76,0.56), 'adobe2': (0.88,0.64,0.46),
 'sand': (0.84,0.70,0.48), 'awn_r': (0.92,0.32,0.26), 'awn_b': (0.22,0.56,0.84), 'crystal': (0.62,0.95,1.0), 'copper': (0.82,0.52,0.30),
 'dome': (0.90,0.92,0.97), 'navy': (0.18,0.22,0.40), 'ice': (0.78,0.90,0.99), 'cream': (0.98,0.94,0.82), 'teal2': (0.20,0.62,0.64),
})
PKEYS = list(PAL.keys()); PN = 8
assert len(PKEYS) <= 64, len(PKEYS)
def palette_mat():
    m = bpy.data.materials.get('T2_Palette')
    if m: return m
    img = bpy.data.images.new('t2_palette.png', PN*4, PN*4, alpha=False)
    px = [0.0] * (PN*4*PN*4*4)
    for i, k in enumerate(PKEYS):
        cx, cy = i % PN, i // PN; c = PAL[k]
        for yy in range(cy*4, cy*4+4):
            for xx in range(cx*4, cx*4+4):
                j = (yy*PN*4 + xx)*4; px[j:j+4] = [c[0], c[1], c[2], 1.0]
    img.pixels[:] = px; img.update(); img.pack()
    m = bpy.data.materials.new('T2_Palette'); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = img; tex.interpolation = 'Closest'
    nt.links.new(tex.outputs['Color'], b.inputs['Base Color']); b.inputs['Roughness'].default_value = 0.8
    return m

def slab_roof(key, w, d, h, z, over=.45, t=.28, snow=False):
    roof(key, w, d, h, 0, 0, z, over, t)
    if snow:
        ang = math.atan2(h, w/2); half = w/2 + over*.9; L = half / math.cos(ang)
        for s in (-1, 1):
            o = box('snow', L, d + 2*over*.9, .14, 0, 0, -.07); o.rotation_euler = (0, s*ang, 0)
            o.location = (s*half/2, 0, z + h - (half/2)*math.tan(ang) + t + .12)

def door(D, w=1.1, h=2.1, key='door', z=.3, arch=False):
    box('trim', w + .25, .16, h + .15, 0, -D/2 - .02, z); box(key, w, .2, h, 0, -D/2 - .04, z)
    if arch: cyl(key, w/2, .2, 0, -D/2 - .04, z + h, seg=12, rx=math.pi/2)
    box('gold', .1, .26, .1, w*.3, -D/2 - .06, z + 1.0)

# ---------------------------------------------------------------- Mistvale: timber cottages, stilt house, lookout
def mv_cottage(name, W=5, D=4.4, roofk='moss', wall='cream', seed=1):
    R = random.Random(seed); fh = 2.7
    box('stone', W + .4, D + .4, .45, 0, 0, 0)
    box(wall, W, D, fh, 0, 0, .45)
    for x in (-W/2, -W/6, W/6, W/2):
        box('beam', .2, D + .04, fh, x, 0, .45)
    for y in (-D/2, D/2): box('beam', W + .04, .2, .2, 0, y, .45 + fh*.55); box('beam', W + .1, .22, .22, 0, y, .45 + fh - .1)
    rh = W * .55; prism(wall, W, rh, D, 0, 0, .45 + fh)
    box('beam', .18, D + .05, rh*.9, 0, 0, .45 + fh)
    slab_roof(roofk, W, D, rh, .45 + fh, over=.6, t=.4)
    door(D, key='wood')
    for x in (-W*.33, W*.33):
        window(x, -D/2, 1.55, '-y', .8, .9); box('wood', 1.0, .4, .25, x, -D/2 - .25, 1.15)
        for k in range(4): sphere(R.choice(['flower_r', 'flower_y', 'flower_w']), .13, x - .35 + k*.23, -D/2 - .3, 1.45, sub=1)
    window(0, D/2, 1.55, '+y', .9, .9); window(-W/2, 0, 1.55, '-x', .9, .9); window(W/2, 0, 1.55, '+x', .9, .9)
    box('stone', .7, .7, fh + rh + .6, W*.3, D*.2, .45)
    cyl('thatch', .9, .2, 0, -D/2 - 1.0, 0, seg=10)  # doormat
    return finish(name)

def mv_stilt(name):
    W, D, z0 = 4.6, 4, 1.6
    for x in (-W/2 + .2, W/2 - .2):
        for y in (-D/2 + .2, D/2 - .2, 0): cyl('logs', .16, z0 + .3, x, y, -.4, seg=8)
    box('wood', W + 2.2, D + .6, .2, -.9, 0, z0)
    for i in range(7): box('beam', .1, .1, .9, -W/2 - 2 + i*.36 if i < 7 else 0, -D/2 - .25, z0 + .2)
    box('beam', 2.3, .1, .1, -W/2 - .9, -D/2 - .25, z0 + 1.0)
    box('logs', W, D, 2.5, 0, 0, z0 + .2)
    for z in range(5): box('beam', W + .05, D + .05, .06, 0, 0, z0 + .4 + z*.5)
    rh = W*.5; prism('logs', W, rh, D, 0, 0, z0 + 2.7); slab_roof('thatch', W, D, rh, z0 + 2.7, over=.55, t=.45)
    door(D, key='wood', z=z0 + .2); window(W/2, 0, z0 + 1.4, '+x', .8, .8); window(-W/2, 0, z0 + 1.4, '-x', .8, .8)
    for k in range(6): box('wood', 1.2, .4, .1, -W/2 - 1.0, -D/2 - .6 - k*.0, z0 - k*.3 + .0) if False else box('wood', 1.1, .45, .12, 0, -D/2 - .5 - k*.42, z0 - k*.3)
    return finish(name)

def mv_lookout(name):
    H = 7.5
    for x in (-1.3, 1.3):
        for y in (-1.3, 1.3): cyl('logs', .18, H, x, y, 0, seg=8, r2=.14)
    for z in (2.2, 4.6): 
        box('beam', 2.8, .12, .12, 0, -1.3, z); box('beam', 2.8, .12, .12, 0, 1.3, z); box('beam', .12, 2.8, .12, -1.3, 0, z); box('beam', .12, 2.8, .12, 1.3, 0, z)
    box('wood', 3.6, 3.6, .2, 0, 0, H - .5)
    for (x, y, sx, sy) in [(0, -1.8, 3.6, .1), (0, 1.8, 3.6, .1), (-1.8, 0, .1, 3.6), (1.8, 0, .1, 3.6)]: box('beam', sx, sy, .9, x, y, H - .3)
    for x in (-1.7, 1.7):
        for y in (-1.7, 1.7): cyl('logs', .1, 2.1, x, y, H - .3, seg=6)
    cyl('thatch', 2.9, 1.6, 0, 0, H + 1.8, seg=8, r2=.05)
    box('gold', .3, .3, .3, 0, 0, H + 3.3)
    for k in range(10): box('beam', .9, .1, .1, 0, -1.45, .3 + k*.68)
    box('beam', .1, .1, H, -.42, -1.5, 0); box('beam', .1, .1, H, .42, -1.5, 0)
    return finish(name)

# ---------------------------------------------------------------- Starfall: observatory, archive, stargazer houses
def sf_observatory(name):
    cyl('stone', 6.2, .6, 0, 0, 0, seg=32); cyl('dome', 5.4, 3.6, 0, 0, .6, seg=32); cyl('navy', 5.55, .35, 0, 0, 4.1, seg=32)
    me = bpy.data.meshes.new('d'); bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=5.2)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -.01], context='VERTS')
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if abs(f.calc_center_median().x) < .8 and f.calc_center_median().y < 0], context='FACES')
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, 4.4)); bm.to_mesh(me); bm.free(); o = _obj(me, 'dome')
    sol = o.modifiers.new('s', 'SOLIDIFY'); sol.thickness = .2
    me = bpy.data.meshes.new('sl'); bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=5.0)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -.01 or abs(v.co.x) > .8 or v.co.y > 0], context='VERTS')
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, 4.4)); bm.to_mesh(me); bm.free(); _obj(me, 'dark')
    cyl('metal', .55, 7.5, 0, -1.0, 6.0, seg=16, r2=.8, rx=-1.0)
    door(10.8, 1.6, 2.4, 'navy', .6, arch=True)
    for a in range(8):
        t = a / 8 * math.tau + .2
        if abs(math.sin(t) + 1) < .3: continue
        x, y = math.cos(t)*5.45, math.sin(t)*5.45
        box('glass', .8, .2, 1.3, x, y, 1.8, rz=t + math.pi/2); box('white', 1.1, .3, .15, x*1.01, y*1.01, 1.65, rz=t + math.pi/2)
    for k in range(4): box('stone', 3.0, .7, .15, 0, -6.3 - k*.6, .45 - k*.15)
    sphere('gold', .35, 0, 0, 9.85, sub=2); cyl('metal', .06, 1.2, 0, 0, 9.4, seg=6)
    return finish(name)

def sf_archive(name):
    W, D = 9, 6
    box('stone', W + 1.2, D + 1.0, .6, 0, 0, 0); box('cream', W, D, 4.2, 0, 0, .6)
    for x in [-3.6, -1.8, 0, 1.8, 3.6]:
        if abs(x) < .5: continue
        cyl('white', .32, 3.9, x, -D/2 - .5, .6, seg=12); box('white', .8, .8, .2, x, -D/2 - .5, 4.4)
    box('white', W + .6, 1.6, .5, 0, -D/2 - .3, 4.6)
    prism('cream', W + .6, 1.7, 1.2, 0, -D/2 - .3, 5.1)
    slab_roof('slate', W, D, 2.0, 4.8, over=.5)
    door(D, 1.6, 2.6, 'navy', .6, arch=True)
    for x in (-3, 3): window(x, -D/2, 2.2, '-y', 1.0, 1.6)
    for y in (-1.5, 1.5): window(-W/2, y, 2.2, '-x', .9, 1.5); window(W/2, y, 2.2, '+x', .9, 1.5)
    cyl('cream', 1.6, 8.2, W/2 - .6, D/2 - .6, .6, seg=16); cyl('slate', 2.0, 2.4, W/2 - .6, D/2 - .6, 8.8, seg=16, r2=.05)
    for k in range(3): box('glass', .5, .2, .9, W/2 - .6, D/2 - 2.25, 2.5 + k*2.0)
    sphere('gold', .25, W/2 - .6, D/2 - .6, 11.3, sub=1)
    for k in range(3): box('stone', 3.0, .6, .2, 0, -D/2 - 1.6 - k*.55, .4 - k*.15)
    return finish(name)

def sf_house(name, seed=1):
    W, D = 4.6, 4.2
    box('stone', W + .3, D + .3, .3); box('dome', W, D, 2.8, 0, 0, .3)
    box('navy', W + .14, D + .14, .16, 0, 0, 3.02)
    prism('dome', W, 1.9, D, 0, 0, 3.1); slab_roof('slate', W, D, 1.9, 3.1, over=.4)
    door(D, key='navy'); window(-1.4, -D/2, 1.5, '-y', .8, .9); window(1.4, -D/2, 1.5, '-y', .8, .9)
    window(W/2, 0, 1.5, '+x'); window(-W/2, 0, 1.5, '-x'); window(0, D/2, 1.5, '+y')
    cyl('white', .7, .7, -1.0, .9, 4.6, seg=12); sphere('dome', .72, -1.0, .9, 5.3, sz=.8, sub=2); cyl('metal', .1, .9, -.7, .6, 5.5, seg=6, rx=-.7)
    return finish(name)

# ---------------------------------------------------------------- Frostline: snowy chalets, lodge
def fl_chalet(name, W=5.2, D=5, wall='logs', roofk='roof_red'):
    box('stone', W + .4, D + .4, .7)
    box(wall, W, D, 2.6, 0, 0, .7)
    for z in range(6): box('beam', W + .06, D + .06, .07, 0, 0, .85 + z*.42)
    rh = W*.8; prism(wall, W, rh, D, 0, 0, 3.3); slab_roof(roofk, W, D, rh, 3.3, over=.6, t=.3, snow=True)
    box('wood', W + .4, 1.4, .18, 0, -D/2 - .7, 3.3); 
    for x in (-W/2, -W/4, 0, W/4, W/2): box('beam', .1, .1, .8, x, -D/2 - 1.35, 3.45)
    box('beam', W + .4, .1, .1, 0, -D/2 - 1.35, 4.2)
    door(D, z=.7, key='wood'); window(-1.5, -D/2, 1.9, '-y', .8, .9); window(1.5, -D/2, 1.9, '-y', .8, .9)
    window(0, -D/2, 4.2, '-y', 1.2, 1.0); window(W/2, 0, 1.9, '+x'); window(-W/2, 0, 1.9, '-x')
    box('stone', .8, .8, 6.6, -W*.3, D*.15, .7); box('snow', .9, .9, .15, -W*.3, D*.15, 7.3)
    for k in range(3): box('stone', 1.8, .6, .2, 0, -D/2 - .5 - k*.5, .5 - k*.2)
    return finish(name)

def fl_lodge(name):
    W, D = 9, 6
    box('stone', W + .4, D + .4, 1.4); box('logs', W, D, 3.0, 0, 0, 1.4)
    for z in range(7): box('beam', W + .06, D + .06, .07, 0, 0, 1.55 + z*.42)
    rh = 3.2; prism('logs', W, rh, D, 0, 0, 4.4); slab_roof('roof_teal', W, D, rh, 4.4, over=.7, t=.32, snow=True)
    door(D, 1.6, 2.4, 'wood', 1.4)
    box('roof_teal', 3.0, 1.6, .16, 0, -D/2 - .8, 4.0); box('snow', 3.1, 1.7, .1, 0, -D/2 - .8, 4.16)
    for x in (-1.3, 1.3): cyl('logs', .14, 2.6, x, -D/2 - 1.45, 1.4, seg=8)
    for x in (-3.2, -1.9, 1.9, 3.2): window(x, -D/2, 2.6, '-y', .8, 1.1)
    for y in (-1.5, 1.5): window(-W/2, y, 2.6, '-x'); window(W/2, y, 2.6, '+x')
    for x in (-W*.32, W*.32): box('stone', .9, .9, 7.2, x, D*.2, 1.4); box('snow', 1.0, 1.0, .15, x, D*.2, 8.6)
    for k in range(5): box('stone', 2.6, .6, .25, 0, -D/2 - .5 - k*.55, 1.2 - k*.28)
    return finish(name)

# ---------------------------------------------------------------- Voltspire: modern blocks, power station
def vs_block(name, W=6, D=5, floors=3, accent='neon'):
    fh = 3.0; H = floors*fh
    box('base', W + .3, D + .3, .3); box('concrete', W, D, H, 0, 0, .3)
    for f in range(floors):
        z = .3 + f*fh
        box(accent, W + .12, D + .12, .14, 0, 0, z + fh - .2)
        if f == 0: continue
        for x in (-W/3, 0, W/3): box('glass', 1.4, .2, 1.6, x, -D/2 - .02, z + .7); box('dark', 1.6, .24, .12, x, -D/2 - .04, z + .62)
        for y in (-D/4, D/4): box('glass', .2, 1.3, 1.6, W/2 + .02, y, z + .7); box('glass', .2, 1.3, 1.6, -W/2 - .02, y, z + .7)
    box('glass', W*.7, .2, 2.0, 0, -D/2 - .02, .5); box('dark', 1.4, .26, 2.1, 0, -D/2 - .05, .3)
    box('metal', W*.8, 1.2, .14, 0, -D/2 - .6, 2.6)
    box('concrete', W + .3, D + .3, .4, 0, 0, .3 + H)
    box('metal', 1.4, 1.0, .8, -W/4, 0, .7 + H); box('metal', 1.0, 1.0, .6, W/4, D/5, .7 + H)
    cyl('metal', .07, 3.5, W/3, -D/4, .7 + H, seg=6); sphere('red', .16, W/3, -D/4, 4.3 + H, sub=1)
    box(accent, .3, .3, H*.9, -W/2 - .1, -D/2 - .1, .4)
    return finish(name)

def vs_station(name):
    box('base', 9, 7, .4); box('concrete', 6, 5, 3.2, -1, 0, .4); box('neon', 6.12, 5.12, .2, -1, 0, 3.2)
    door(5, 1.8, 2.4, 'dark', .4)
    cyl('metal', 1.1, 9.0, 3.0, 0, .4, seg=16, r2=.7)
    for k in range(5):
        me = bpy.data.meshes.new('t'); bm = bmesh.new()
        bmesh.ops.create_circle(bm, cap_ends=False, segments=24, radius=1.3 - k*.08); bmesh.ops.translate(bm, verts=bm.verts, vec=(3.0, 0, 2.0 + k*1.6)); bm.to_mesh(me); bm.free()
        o = _obj(me, 'copper'); sk = o.modifiers.new('sk', 'SKIN')
    cyl('copper', .8, .4, 3.0, 0, 9.4, seg=16); sphere('crystal', .65, 3.0, 0, 10.4, sub=2)
    for x, y in [(-3.5, -2.8), (-3.5, 2.8), (.5, 2.8)]: cyl('metal', .1, 4.2, x, y, .4, seg=6); box('metal', .9, .1, .1, x, y, 4.3)
    box('neon', .25, 5.6, .25, -4.05, 0, 1.2)
    return finish(name)

# ---------------------------------------------------------------- Sandreach: adobe houses, market stalls, glass workshop
def sr_adobe(name, W=5, D=4.6, wall='adobe', dome=False, floors=1):
    fh = 2.9; H = floors*fh
    box('sand', W + .3, D + .3, .3); box(wall, W, D, H, 0, 0, .3, bevel=.18)
    box(wall, W + .1, D + .1, .5, 0, 0, .3 + H)
    box('sand', W - .5, D - .5, .52, 0, 0, .32 + H)
    for x in (-W*.35, 0, W*.35): cyl('beam', .1, .7, x, -D/2 - .25, .3 + H - .5, seg=6, rx=math.pi/2)
    door(D, 1.1, 2.2, 'teal2', .3, arch=True)
    for x in (-W*.3, W*.3): box('dark', .7, .2, .9, x, -D/2 - .01, 1.5); cyl('dark', .35, .2, x, -D/2 - .01, 2.4, seg=10, rx=math.pi/2)
    box('dark', .2, .7, .9, W/2 + .01, 0, 1.5); box('dark', .2, .7, .9, -W/2 - .01, 0, 1.5)
    if dome: sphere('dome', 1.5, W*.15, D*.1, .3 + H + .4, sz=.75, sub=3); sphere('gold', .2, W*.15, D*.1, .3 + H + 1.6, sub=1)
    else:
        for x in (-.8, .8): box('awn_r' if x < 0 else 'awn_b', 1.2, 1.0, .08, x - 0, D*.15, .85 + H)
        cyl('beam', .05, 1.0, -1.4, D*.15 - .5, .8 + H, seg=6); cyl('beam', .05, 1.0, 1.4, D*.15 - .5, .8 + H, seg=6)
    box('awn_r', 2.0, 1.0, .1, 0, -D/2 - .5, 2.65)
    for k in range(3): box('sand', .9, .9, .5 + k*.2, -W/2 - .7 + 0, D*.3 - k*.0, .0) if k == 0 else None
    cyl('copper', .35, .8, W/2 - .2, -D/2 - .7, 0, seg=10, r2=.25)
    return finish(name)

def sr_market(name, a='awn_r'):
    for x in (-1.6, 1.6):
        for y in (-1.0, 1.0): cyl('beam', .08, 2.6, x, y, 0, seg=6)
    box('wood', 3.4, 1.0, .9, 0, -.6, 0); box('cream', 3.5, 1.1, .1, 0, -.6, .9)
    for i in range(6):
        k = a if i % 2 == 0 else 'cream'
        o = box(k, .6, 2.6, .08, -1.5 + i*.6, -.1, 2.7); o.rotation_euler.x = .2
    for i, c in enumerate(['flower_r', 'flower_y', 'leaf', 'copper', 'crystal']): sphere(c, .17, -1.2 + i*.6, -.7, 1.12, sub=1)
    box('wood', .7, .7, .7, 1.1, .7, 0); box('wood', .6, .6, .6, -1.2, .8, 0); cyl('copper', .25, .7, -.4, .9, 0, seg=10, r2=.18)
    return finish(name)

def sr_workshop(name):
    W, D = 6.5, 5
    box('sand', W + .3, D + .3, .3); box('adobe2', W, D, 3.4, 0, 0, .3, bevel=.2); box('adobe2', W + .1, D + .1, .5, 0, 0, 3.7)
    door(D, 1.6, 2.4, 'teal2', .3, arch=True)
    box('glass', 1.8, .2, 1.4, W*.28, -D/2 - .02, 1.3); box('glass', 1.8, .2, 1.4, -W*.28, -D/2 - .02, 1.3)
    cyl('adobe', 1.0, 3.2, W/2 - 1.2, D/2 - 1.0, 3.7, seg=12, r2=.6); cyl('dark', .55, .3, W/2 - 1.2, D/2 - 1.0, 6.85, seg=12)
    for i, (x, h) in enumerate([(-2.2, 1.2), (-1.6, .8), (2.0, 1.0), (2.6, .7)]):
        o = cyl('crystal', .22, h, x, -D/2 - 1.1, .0, seg=6, r2=.02)
    box('awn_b', W*.8, 1.3, .1, 0, -D/2 - .6, 2.9)
    return finish(name)

def build_all():
    out = []
    out += [mv_cottage('MV_Cottage_A', seed=1), mv_cottage('MV_Cottage_B', 5.6, 4.6, 'thatch', 'wall2', 3), mv_stilt('MV_Stilt'), mv_lookout('MV_Lookout')]
    out += [sf_observatory('SF_Observatory'), sf_archive('SF_Archive'), sf_house('SF_House')]
    out += [fl_chalet('FL_Chalet_A'), fl_chalet('FL_Chalet_B', 6, 5.4, 'logs', 'roof_blue'), fl_lodge('FL_Lodge')]
    out += [vs_block('VS_Block_A'), vs_block('VS_Block_B', 7, 6, 4, 'blue'), vs_block('VS_Block_C', 5, 5, 2, 'awn_r'), vs_station('VS_Station')]
    out += [sr_adobe('SR_Adobe_A'), sr_adobe('SR_Adobe_B', 6, 5, 'adobe2', True, 2), sr_adobe('SR_Adobe_C', 4.4, 4.4, 'sand', True), sr_market('SR_Market_A'), sr_market('SR_Market_B', 'awn_b'), sr_workshop('SR_Workshop')]
    return out
