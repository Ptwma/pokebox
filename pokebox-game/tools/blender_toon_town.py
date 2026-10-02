
import bpy, bmesh, math, random
from mathutils import Vector, Matrix

PAL = {
 'wall': (0.96,0.93,0.86), 'wall2': (0.99,0.86,0.70), 'wall3': (0.80,0.90,0.97),
 'trim': (0.42,0.27,0.16), 'wood': (0.55,0.36,0.20), 'stone': (0.62,0.62,0.66), 'base': (0.50,0.48,0.46),
 'roof_red': (0.86,0.20,0.18), 'roof_blue': (0.18,0.42,0.86), 'roof_green': (0.22,0.66,0.34), 'roof_orange': (0.95,0.52,0.16),
 'roof_teal': (0.10,0.70,0.68), 'roof_purple': (0.52,0.30,0.80),
 'glass': (0.45,0.75,0.95), 'door': (0.30,0.45,0.75), 'white': (0.97,0.97,0.97), 'dark': (0.12,0.12,0.15),
 'metal': (0.75,0.78,0.82), 'gold': (1.0,0.80,0.25), 'leaf': (0.30,0.70,0.25), 'leaf2': (0.20,0.55,0.25), 'pine': (0.14,0.46,0.30),
 'trunk': (0.45,0.30,0.18), 'flower_r': (0.95,0.30,0.35), 'flower_y': (1.0,0.85,0.25), 'flower_w': (0.98,0.95,0.95), 'soil': (0.36,0.25,0.16),
 'glow': (1.0,0.92,0.60), 'red': (0.90,0.18,0.20), 'blue': (0.20,0.50,0.95),
}
def mat(key):
    name = 'TT_' + key
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']; c = PAL[key]
    b.inputs['Base Color'].default_value = (c[0]**2.2, c[1]**2.2, c[2]**2.2, 1)  # sRGB -> linear
    b.inputs['Roughness'].default_value = 0.35 if key in ('glass','metal','gold') else 0.8
    b.inputs['Metallic'].default_value = 0.6 if key in ('metal','gold') else 0.0
    if key in ('glow',):
        b.inputs['Emission Color'].default_value = (1,0.85,0.5,1); b.inputs['Emission Strength'].default_value = 2.0
    return m

PARTS = []
def _obj(me, key):
    o = bpy.data.objects.new('tt_part', me); bpy.context.scene.collection.objects.link(o)
    o.data.materials.append(mat(key)); PARTS.append(o); return o

def box(key, sx, sy, sz, x=0, y=0, z=0, rz=0, bevel=0.0):
    """box with size (sx,sy,sz), bottom centre at (x,y,z) (Blender: z up)"""
    me = bpy.data.meshes.new('b'); bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1)
    for v in bm.verts: v.co = Vector((v.co.x*sx, v.co.y*sy, v.co.z*sz + sz/2))
    if bevel > 0: bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=2, affect='EDGES', profile=0.5)
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0,0,0), matrix=Matrix.Rotation(rz, 3, 'Z'))
    bmesh.ops.translate(bm, verts=bm.verts, vec=(x,y,z)); bm.to_mesh(me); bm.free(); return _obj(me, key)

def cyl(key, r, h, x=0, y=0, z=0, seg=16, r2=None, rx=0, ry=0):
    me = bpy.data.meshes.new('c'); bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=(r if r2 is None else r2), depth=h)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0,0,h/2))
    if rx or ry: bmesh.ops.rotate(bm, verts=bm.verts, cent=(0,0,0), matrix=Matrix.Rotation(rx,3,'X') @ Matrix.Rotation(ry,3,'Y'))
    bmesh.ops.translate(bm, verts=bm.verts, vec=(x,y,z)); bm.to_mesh(me); bm.free(); return _obj(me, key)

def sphere(key, r, x=0, y=0, z=0, sz=1.0, sub=2, sx=1.0, sy=1.0):
    me = bpy.data.meshes.new('s'); bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=r)
    for v in bm.verts: v.co = Vector((v.co.x*sx, v.co.y*sy, v.co.z*sz))
    bmesh.ops.translate(bm, verts=bm.verts, vec=(x,y,z)); bm.to_mesh(me); bm.free(); return _obj(me, key)

def gable(key, w, d, h, x=0, y=0, z=0, over=0.35, thick=0.18):
    """pitched roof, ridge along Y. w = width (X), d = depth (Y), h = height above z"""
    W = w/2 + over; D = d/2 + over
    me = bpy.data.meshes.new('g'); bm = bmesh.new()
    # two slabs as extruded quads
    for s in (-1, 1):
        a = bm.verts.new((x + s*W, y - D, z - over*h/(w/2)*0.0)); b_ = bm.verts.new((x, y - D, z + h)); c = bm.verts.new((x, y + D, z + h)); e = bm.verts.new((x + s*W, y + D, z))
        a.co.z = z; f = bm.faces.new((a, b_, c, e) if s > 0 else (e, c, b_, a))
    bm.normal_update()
    ret = bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=thick) if hasattr(bmesh.ops, 'solidify') else None
    bm.to_mesh(me); bm.free(); o = _obj(me, key)
    mod = o.modifiers.new('sol', 'SOLIDIFY'); mod.thickness = thick; mod.offset = 1
    return o

def gable_wall(key, w, h, x=0, y=0, z=0, depth=0.2):
    """triangular wall piece (front/back of the roof) in the XZ plane, thickness along Y"""
    me = bpy.data.meshes.new('t'); bm = bmesh.new()
    v = [bm.verts.new((x - w/2, y - depth/2, z)), bm.verts.new((x + w/2, y - depth/2, z)), bm.verts.new((x, y - depth/2, z + h))]
    f = bm.faces.new(v); bmesh.ops.extrude_face_region(bm, geom=[f])
    for vv in bm.verts:
        if abs(vv.co.y - (y - depth/2)) < 1e-6 and vv not in v: pass
    bm.to_mesh(me); bm.free(); o = _obj(me, key)
    s = o.modifiers.new('sol', 'SOLIDIFY'); s.thickness = depth
    return o


PKEYS = list(PAL.keys())
PN = 8   # palette grid PN x PN cells
def palette_mat():
    m = bpy.data.materials.get('TT_Palette')
    if m: return m
    img = bpy.data.images.get('tt_palette.png') or bpy.data.images.new('tt_palette.png', PN*4, PN*4, alpha=False)
    px = [0.0] * (PN*4*PN*4*4)
    for i, k in enumerate(PKEYS):
        cx, cy = i % PN, i // PN; c = PAL[k]
        for yy in range(cy*4, cy*4+4):
            for xx in range(cx*4, cx*4+4):
                j = (yy*PN*4 + xx)*4; px[j:j+4] = [c[0], c[1], c[2], 1.0]
    img.pixels[:] = px; img.update(); img.pack()
    m = bpy.data.materials.new('TT_Palette'); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = img; tex.interpolation = 'Closest'
    nt.links.new(tex.outputs['Color'], b.inputs['Base Color']); b.inputs['Roughness'].default_value = 0.8
    return m

def to_palette(o):
    """bake every material of o into UVs pointing at its palette cell; o ends up with one material"""
    me = o.data
    keys = [ (mm.name[3:] if mm and mm.name.startswith('TT_') else 'white') for mm in me.materials ]
    if not me.uv_layers: me.uv_layers.new(name='UVMap')
    uv = me.uv_layers.active.data
    for poly in me.polygons:
        k = keys[poly.material_index] if poly.material_index < len(keys) else 'white'
        i = PKEYS.index(k) if k in PKEYS else PKEYS.index('white')
        u = ((i % PN) + 0.5) / PN; v = ((i // PN) + 0.5) / PN
        for li in poly.loop_indices: uv[li].uv = (u, v)
    me.materials.clear(); me.materials.append(palette_mat())
    for p in me.polygons: p.material_index = 0

def sign_disc(key_ring, key_face, x, y, z, r=0.7):
    cyl(key_ring, r, 0.18, x, y, z, seg=20, rx=1.5708); cyl(key_face, r*0.75, 0.22, x, y - 0.02, z, seg=20, rx=1.5708)

def relay_center(name='TT_RelayCenter'):
    W, D, H = 11, 8, 4.2
    box('base', W + .4, D + .4, .3); box('white', W, D, H, 0, 0, .3)
    box('roof_orange', W + .8, D + .8, .5, 0, 0, .3 + H)                     # flat slab roof
    box('white', W + .9, D + .9, .18, 0, 0, .3 + H + .5)
    cyl('roof_orange', 2.4, 1.6, 0, 0, .3 + H + .6, seg=24, r2=1.2)          # roof cupola
    cyl('glass', 1.25, .5, 0, 0, .3 + H + 2.2, seg=24, r2=.9)
    box('glass', 5.0, .2, 2.8, 0, -D/2 - .02, .3)                             # glass front
    for xx in (-2.5, 0, 2.5): box('white', .18, .3, 2.8, xx, -D/2 - .05, .3)
    box('roof_orange', 6.2, 1.6, .25, 0, -D/2 - .7, .3 + 3.0)                 # canopy
    box('stone', 6.5, 2.0, .2, 0, -D/2 - .9, 0)
    sign_disc('white', 'roof_teal', 0, -D/2 - .1, .3 + H - .4, .85)            # relay emblem
    box('white', 1.2, .22, .22, 0, -D/2 - .25, .3 + H - .4); box('white', .22, .22, 1.2, 0, -D/2 - .25, .3 + H - 1.0)
    for xx in (-W/2 + 1.3, W/2 - 1.3): window(xx, -D/2, 1.3, '-y', w=1.6, h=1.6)
    for yy in (-2, 2): window(-W/2, yy, 1.3, '-x', w=1.6, h=1.6); window(W/2, yy, 1.3, '+x', w=1.6, h=1.6)
    return finish(name)

def lab(name='TT_Lab'):
    W, D, H = 13, 9, 5.6
    box('base', W + .4, D + .4, .3); box('wall3', W, D, H, 0, 0, .3)
    box('white', W + .3, D + .3, .35, 0, 0, .3 + H); box('white', W + .3, D + .3, .2, 0, 0, .3 + 2.8)
    box('white', 3.4, D + .6, H + .8, -W/2 + 1.7, 0, .3)                      # tower wing
    box('glass', 3.0, .2, H - .6, -W/2 + 1.7, -D/2 - .3, .6)
    box('glass', 2.2, .2, 2.4, 1.5, -D/2 - .02, .3); box('trim', 2.6, .16, 2.6, 1.5, -D/2, .3)
    box('roof_blue', 3.6, 1.4, .22, 1.5, -D/2 - .6, .3 + 2.6)
    for f in (0, 1):
        for xx in (-1.5, 4.0): window(xx, -D/2, .3 + f*2.8 + 1.0, '-y', w=1.4, h=1.2)
        for yy in (-2.2, 2.2): window(W/2, yy, .3 + f*2.8 + 1.0, '+x', w=1.4, h=1.2)
    # satellite dish on the roof
    z0 = .3 + H + .35
    cyl('metal', .25, 1.4, 3.5, 1.5, z0, seg=10)
    cyl('white', 2.0, .55, 3.5, 1.2, z0 + 1.6, seg=24, r2=.4, rx=-0.7)
    cyl('metal', .06, 1.6, 3.5, .4, z0 + 2.0, seg=6, rx=-0.7)
    box('roof_blue', 3.8, D + .8, .3, -W/2 + 1.7, 0, .3 + H + .8)
    box('metal', .9, .9, .5, -1.5, 2, z0); box('metal', .9, .9, .5, 0, 2, z0)  # roof vents
    return finish(name)

def gym(name='TT_Gym'):
    W, D, H = 14, 12, 5.0
    box('base', W + .4, D + .4, .3); box('wall2', W, D, H, 0, 0, .3)
    for cx in (-1, 1):
        for cy in (-1, 1): cyl('white', .7, H + .8, cx*W/2, cy*D/2, .3, seg=12)
    sphere('roof_purple', 6.4, 0, 0, .3 + H - .4, sz=.45, sub=3, sx=1.05, sy=.9)    # dome
    box('white', W + .3, D + .3, .3, 0, 0, .3 + H)
    box('dark', 3.4, .2, 3.4, 0, -D/2 - .02, .3); box('gold', 4.0, .25, .4, 0, -D/2 - .05, .3 + 3.4)
    for xx in (-1.8, 1.8): cyl('gold', .32, 4.6, xx, -D/2 - 1.0, .3, seg=10)
    box('stone', 6, 2.6, .25, 0, -D/2 - 1.3, 0)
    sign_disc('gold', 'roof_purple', 0, -D/2 - .1, .3 + H - .3, 1.1)
    for xx in (-4.8, 4.8): window(xx, -D/2, 1.5, '-y', w=1.6, h=2.2)
    return finish(name)

def shop(name='TT_Shop'):
    W, D, H = 7, 6, 3.4
    box('base', W + .3, D + .3, .3); box('wall', W, D, H, 0, 0, .3)
    box('roof_blue', W + .6, D + .6, .35, 0, 0, .3 + H); box('white', W + .7, D + .7, .14, 0, 0, .3 + H + .35)
    box('glass', 4.2, .2, 2.2, -.6, -D/2 - .02, .5); box('white', 4.5, .22, .2, -.6, -D/2 - .04, .5 + 2.2)
    box('door', 1.0, .2, 2.1, 2.4, -D/2 - .03, .3)
    for i in range(6):                                                        # striped awning
        box('blue' if i % 2 == 0 else 'white', .8, 1.3, .14, -2.9 + i*.8 + .4 - .2, -D/2 - .6, .3 + 2.75)
    box('gold', 3.2, .2, .7, 0, -D/2 - .05, .3 + H - .8)                         # shop sign board
    return finish(name)

def lamp():
    cyl('dark', .16, .3, 0, 0, 0, seg=8, r2=.12); cyl('dark', .07, 3.0, 0, 0, .3, seg=8)
    box('dark', .5, .5, .1, 0, 0, 3.25); box('glow', .36, .36, .45, 0, 0, 3.35); cyl('dark', .3, .25, 0, 0, 3.8, seg=4, r2=.02)
    return finish('TT_Lamp')
def fence():
    for x in (-.9, -.3, .3, .9): box('white', .14, .08, .95, x, 0, 0); cyl('white', .1, .12, x, 0, .95, seg=4, r2=.01)
    for z in (.3, .7): box('white', 2.0, .06, .1, 0, .06, z)
    return finish('TT_Fence')
def bench():
    for x in (-.7, .7): box('dark', .1, .45, .45, x, 0, 0)
    box('wood', 1.7, .45, .08, 0, 0, .45); box('wood', 1.7, .08, .4, 0, .2, .55)
    return finish('TT_Bench')
def signpost():
    box('wood', .14, .14, 1.8, 0, 0, 0); box('wood', 1.1, .08, .55, 0, -.06, 1.15); box('white', .95, .1, .4, 0, -.08, 1.22)
    return finish('TT_Signpost')
def flowerbed():
    R = random.Random(4)
    box('wood', 2.0, 1.0, .3, 0, 0, 0); box('soil', 1.85, .85, .32, 0, 0, 0)
    for i in range(14):
        x = R.uniform(-.8, .8); y = R.uniform(-.35, .35)
        cyl('leaf2', .03, .25, x, y, .3, seg=4); sphere(R.choice(['flower_r', 'flower_y', 'flower_w', 'roof_purple']), .09, x, y, .58, sub=1)
    return finish('TT_Flowerbed')
def mailbox():
    box('wood', .1, .1, 1.0, 0, 0, 0); box('red', .35, .5, .3, 0, 0, 1.0); cyl('red', .175, .5, 0, -.25, 1.3, seg=10, rx=-1.5708)
    return finish('TT_Mailbox')
def fountain():
    cyl('stone', 2.4, .55, 0, 0, 0, seg=24); cyl('glass', 2.1, .58, 0, 0, 0.0, seg=24)
    cyl('stone', .4, 1.6, 0, 0, 0, seg=12); cyl('stone', .9, .2, 0, 0, 1.4, seg=16); cyl('glass', .75, .24, 0, 0, 1.4, seg=16)
    cyl('stone', .18, .7, 0, 0, 1.6, seg=8); sphere('glass', .25, 0, 0, 2.35, sub=1)
    return finish('TT_Fountain')
def tree_round(name, key, h=3.0, seed=1):
    R = random.Random(seed)
    cyl('trunk', .28, h*0.55, 0, 0, 0, seg=7, r2=.18)
    for i in range(4):
        a = i*1.7; r = 1.15 + R.uniform(-.15, .2)
        sphere(key, r, math.cos(a)*.55, math.sin(a)*.55, h*0.55 + .8 + R.uniform(0, .5), sub=1, sz=.9)
    sphere(key, 1.3, 0, 0, h*0.55 + 1.6, sub=1, sz=.9)
    return finish(name)
def tree_pine(name='TT_Tree_Pine'):
    cyl('trunk', .25, 1.0, 0, 0, 0, seg=6, r2=.2)
    for i, (r, z) in enumerate([(1.7, .8), (1.35, 1.9), (1.0, 2.9), (.6, 3.8)]): cyl('pine', r, 1.5, 0, 0, z, seg=8, r2=0.05)
    return finish(name)
def bush(name='TT_Bush'):
    sphere('leaf', .8, 0, 0, .5, sub=1, sz=.75); sphere('leaf2', .6, .6, .2, .4, sub=1, sz=.75); sphere('leaf', .55, -.55, -.15, .38, sub=1, sz=.75)
    return finish(name)

def finish(name, origin=(0,0,0)):
    """apply modifiers, join all PARTS into one object called name, origin at bottom centre"""
    global PARTS
    bpy.ops.object.select_all(action='DESELECT')
    for o in PARTS:
        o.select_set(True); bpy.context.view_layer.objects.active = o
        for m in list(o.modifiers): bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.context.view_layer.objects.active = PARTS[0]
    bpy.ops.object.join(); o = bpy.context.active_object; o.name = name; o.data.name = name
    bpy.ops.object.shade_flat()
    to_palette(o)
    PARTS = []
    return o

def window(x, y, z, face='-y', w=0.9, h=1.0):
    """framed window on a wall face; face = side of the house it sits on"""
    t = 0.12
    if face in ('-y', '+y'):
        s = -1 if face == '-y' else 1
        box('trim', w + 0.2, t, h + 0.2, x, y + s*0.02, z - 0.1)
        box('glass', w, t + 0.04, h, x, y + s*0.04, z)
        box('white', 0.06, t + 0.08, h, x, y + s*0.06, z)
        box('white', w + 0.3, 0.25, 0.08, x, y + s*0.12, z - 0.12)
    else:
        s = -1 if face == '-x' else 1
        box('trim', t, w + 0.2, h + 0.2, x + s*0.02, y, z - 0.1)
        box('glass', t + 0.04, w, h, x + s*0.04, y, z)
        box('white', t + 0.08, 0.06, h, x + s*0.06, y, z)
        box('white', 0.25, w + 0.3, 0.08, x + s*0.12, y, z - 0.12)

def prism(key, w, h, depth, x=0, y=0, z=0):
    """triangular prism: base width w (X), apex height h (Z), length depth (Y), base centre at (x,y,z)"""
    me = bpy.data.meshes.new('p'); bm = bmesh.new(); vs = []
    for yy in (-depth/2, depth/2):
        vs.append([bm.verts.new((x - w/2, y + yy, z)), bm.verts.new((x + w/2, y + yy, z)), bm.verts.new((x, y + yy, z + h))])
    a, b_ = vs
    bm.faces.new((a[0], a[1], a[2])); bm.faces.new((b_[2], b_[1], b_[0]))
    bm.faces.new((a[0], b_[0], b_[1], a[1])); bm.faces.new((a[1], b_[1], b_[2], a[2])); bm.faces.new((a[2], b_[2], b_[0], a[0]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free(); return _obj(me, key)

def roof(key, w, d, h, x=0, y=0, z=0, over=0.4, t=0.22):
    """pitched roof made of two slabs, ridge along Y at height z+h, eaves overhang by over"""
    import math
    ang = math.atan2(h, w/2); half = w/2 + over; L = half / math.cos(ang)
    for s in (-1, 1):
        o = box(key, L, d + 2*over, t, 0, 0, -t/2)          # centred slab
        o.rotation_euler = (0, s*ang, 0)
        o.location = (x + s*half/2, y, z + h - (half/2)*math.tan(ang) + t*0.5)
    box(key, 0.34, d + 2*over + 0.05, 0.24, x, y, z + h + t*0.35)   # ridge cap

def house(name, W=5, D=5, floors=1, wall='wall', roof_key='roof_red', fh=2.8, chimney=True, porch=True, seed=1):
    import random; R = random.Random(seed)
    H = floors*fh
    box('base', W + 0.3, D + 0.3, 0.3, 0, 0, 0)                               # plinth
    box(wall, W, D, H, 0, 0, 0.3)                                             # walls
    for f in range(1, floors): box('white', W + 0.12, D + 0.12, 0.14, 0, 0, 0.3 + f*fh - 0.07)
    box('white', W + 0.14, D + 0.14, 0.16, 0, 0, 0.3 + H - 0.08)                 # eaves band
    for cx in (-1, 1):
        for cy in (-1, 1): box('white', 0.22, 0.22, H, cx*(W/2), cy*(D/2), 0.3)   # corner posts
    rh = W*0.42
    prism(wall, W, rh, D, 0, 0, 0.3 + H)                                       # gable walls
    roof(roof_key, W, D, rh, 0, 0, 0.3 + H)
    # door (front = -Y) + steps + small porch roof
    box('trim', 1.3, 0.16, 2.25, 0, -D/2 - 0.02, 0.3)
    box('door', 1.05, 0.2, 2.05, 0, -D/2 - 0.04, 0.3)
    box('gold', 0.12, 0.26, 0.12, 0.32, -D/2 - 0.06, 1.3)
    box('stone', 1.8, 0.8, 0.22, 0, -D/2 - 0.45, 0.0); box('stone', 1.6, 0.5, 0.15, 0, -D/2 - 0.75, 0.0)
    if porch:
        box(roof_key, 2.0, 1.0, 0.14, 0, -D/2 - 0.45, 0.3 + 2.55)
        for sx in (-0.85, 0.85): box('white', 0.12, 0.12, 2.5, sx, -D/2 - 0.85, 0.3)
    # windows: front (beside the door), back, sides, upper floors
    for f in range(floors):
        zz = 0.3 + f*fh + 1.0
        xs = [-W/2 + 1.0, W/2 - 1.0] if W >= 4.5 else [-W/2 + 0.8, W/2 - 0.8]
        for xx in xs:
            if f == 0 and abs(xx) < 1.2: continue
            window(xx, -D/2, zz, '-y'); window(xx, D/2, zz, '+y')
        if f > 0: window(0, -D/2, zz, '-y')
        for yy in ([0] if D < 6 else [-D/4, D/4]):
            window(-W/2, yy, zz, '-x'); window(W/2, yy, zz, '+x')
    if chimney:
        box('stone', 0.7, 0.7, rh + 1.0, W/4, D/4, 0.3 + H); box('dark', 0.8, 0.8, 0.15, W/4, D/4, 0.3 + H + rh + 1.0)
    # flower boxes under front windows
    for xx in [-W/2 + 1.0, W/2 - 1.0]:
        if abs(xx) > 1.2: box('flower_r' if R.random() < .5 else 'flower_y', 1.0, 0.3, 0.2, xx, -D/2 - 0.2, 0.3 + 0.75)
    return finish(name)
