# Sigil & Spark v4 — look test set #1: "The pier at dusk" (Ep1 scene 1 hub). Built from CC0 Quaternius kits (local only).
#   blender -b --python set_pier.py -- <SRC> <out.png> [cam]      SRC = PokeboxNext_src
# Look: painted-toon materials (light banded through a colour ramp, the kit's texture as paint), ink outlines (Line Art),
# a 2-colour key (ember dusk × cold teal), fog. The same layout is exported to Unreal later (set_export).
import bpy, os, sys, math, random
from mathutils import Vector, Euler

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
SRC = argv[0] if argv else r"E:\GAME-APP-DEV\POKEMON\PokeboxNext_src"
OUT = argv[1] if len(argv) > 1 else os.path.join(SRC, 'sets_render', 'pier_test.png')
CAMNAME = argv[2] if len(argv) > 2 else 'wide'
KIT = os.path.join(SRC, 'environment', 'quaternius', 'Medieval Village MegaKit[Standard]', 'glTF')
CH = os.path.join(SRC, 'characters', 'quaternius')
R = random.Random(4)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
_cache = {}
NOINK = bpy.data.collections.new('NoInk'); sc.collection.children.link(NOINK)
def noink(o):
    for c in list(o.users_collection): c.objects.unlink(o)
    NOINK.objects.link(o)

def piece(name, loc, rot=0.0, scale=1.0):
    """place a kit piece (linked duplicate of a cached import); rot in degrees about Z"""
    if name not in _cache:
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=os.path.join(KIT, name + '.gltf'))
        new = [o for o in bpy.data.objects if o not in before]
        src = next(o for o in new if o.type == 'MESH')
        for o in new:
            if o is not src: bpy.data.objects.remove(o)
        src.parent = None; _cache[name] = src; src.location = loc; src.rotation_euler = (0, 0, math.radians(rot)); src.scale = (scale,) * 3
        return src
    o = _cache[name].copy(); sc.collection.objects.link(o)
    o.location = loc; o.rotation_euler = (0, 0, math.radians(rot)); o.scale = (scale,) * 3
    return o

# ------------------------------------------------------------------ layout (metres; X along the quay, Y = inland +)
# a row of three narrow harbour houses on the left of the quay, the pier going out into the water on the right
def house(x0, floors, w=2, style='UnevenBrick', upper='Plaster', door_at=0, seed=0):
    rr = random.Random(seed)
    for f in range(floors):
        z = f * 3.12
        mat = style if f == 0 else upper
        for i in range(w):
            x = x0 + i * 2 + 1
            if f == 0 and i == door_at: n = f'Wall_{mat}_Door_Round'
            else: n = rr.choice([f'Wall_{mat}_Window_Wide_Round', f'Wall_{mat}_Window_Thin_Round', f'Wall_{mat}_Straight'])
            piece(n, (x, 0, z), 180)                       # facade faces -Y (the quay)
            piece(f'Wall_{mat}_Straight', (x, 2 * 2, z), 0) # back
        for j in range(2):
            piece(f'Wall_{mat}_Straight', (x0, j * 2 + 1, z), 90)
            piece(f'Wall_{mat}_Straight', (x0 + w * 2, j * 2 + 1, z), -90)
        if f > 0: piece('Floor_WoodDark', (x0 + 1, 1, z), 0)
    piece('Roof_RoundTiles_4x4', (x0 + w, 2, floors * 3.12), 0)
    # the rooms behind the windows: a backdrop plane per floor, some lit warm (people at home), most dark
    for f in range(floors):
        bpy.ops.mesh.primitive_plane_add(size=1, location=(x0 + w, 1.2, f * 3.12 + 1.6), rotation=(math.radians(90), 0, 0))
        bp = bpy.context.object; bp.scale = (w * 2 - 0.2, 3.0, 1); noink(bp)
        lit = rr.random() < 0.4
        m = bpy.data.materials.new('Room'); m.use_nodes = True; nt = m.node_tree
        em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (1.0, 0.62, 0.28, 1) if lit else (0.02, 0.025, 0.04, 1)
        em.inputs['Strength'].default_value = 3.0 if lit else 1.0
        nt.links.new(em.outputs[0], nt.nodes['Material Output'].inputs['Surface']); bp.data.materials.append(m); m['toon'] = 1

house(-9, 2, seed=1)
house(-5, 3, seed=2, upper='Plaster')
house(-1, 2, seed=3, style='UnevenBrick', upper='UnevenBrick')
house(3, 3, seed=5)
for i, x0 in enumerate([-13, -7, -3, 1, 5]):
    o = len(bpy.data.objects)
    house(x0, 3 + (i % 2), seed=20 + i, upper='Plaster')
    for ob in list(bpy.data.objects)[o:]:
        if ob.parent is None: ob.location.y += 9; ob.location.z += 2.5
house(-13, 2, seed=9)
house(7, 2, seed=11, upper='UnevenBrick')
# the hill the town climbs: a dark mass behind everything
bpy.ops.mesh.primitive_uv_sphere_add(radius=40, location=(-5, 50, -22)); hill = bpy.context.object; hill.scale = (1.6, 1, .9); hill['hill'] = 1
# the quay: brick floor along the houses, a low stone border at the water
for x in range(-13, 12, 2):
    for y in (-1, -3, -5):
        piece('Floor_UnevenBrick', (x, y, 0))
    piece('Prop_ExteriorBorder_Straight1', (x, -6.1, 0), 0)
# the pier: wooden planks on posts out over the water (to -Y), then a T at the end
for k in range(0, 6):
    piece('Floor_WoodDark', (7, -7 - k * 2, 0.0))
    for sx in (-0.95, 0.95):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.14, depth=3.2, location=(7 + sx, -7 - k * 2, -1.5), vertices=10)
        pile = bpy.context.object; pile['wood'] = 1
for x in (5, 9):
    piece('Floor_WoodDark', (x, -17, 0.0))
# props: crates, the wagon, fences, vines
for (x, y, r) in [(-6.2, -1.6, 10), (-5.3, -1.2, 40), (-5.8, -2.0, 0), (5.7, -8.4, 15), (8.3, -15.9, 30)]:
    piece('Prop_Crate', (x, y, 0.0), r)
piece('Prop_Wagon', (0.5, -2.6, 0), 80)
piece('Prop_Vine2', (-4.95, -0.25, 0.2), 180)


# water, sky, the lighthouse far out on its rock
bpy.ops.mesh.primitive_plane_add(size=400, location=(0, -150, -0.6)); water = bpy.context.object; noink(water)
bpy.ops.mesh.primitive_cylinder_add(radius=1.6, depth=16, location=(26, -70, 7)); tower = bpy.context.object
bpy.ops.mesh.primitive_cone_add(radius1=2.1, depth=2.4, location=(26, -70, 16.2)); cap = bpy.context.object
bpy.ops.mesh.primitive_ico_sphere_add(radius=7, location=(26, -70, -3)); rock = bpy.context.object; rock.scale = (1.4, 1, .6)

# ------------------------------------------------------------------ Rho (Quaternius base + fantasy outfit)
def character(outfit, hair, loc, yaw, body='Superhero_Male_FullBody'):
    B = os.path.join(CH, 'Universal Base Characters[Standard]')
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(B, 'Base Characters', 'Godot - UE', body + '.gltf'))
    base = [o for o in bpy.data.objects if o not in before]
    arm = next(o for o in base if o.type == 'ARMATURE')
    for o in base:
        if o.type == 'MESH' and o.name.startswith('Icosphere'): bpy.data.objects.remove(o)
    base = [o for o in bpy.data.objects if o not in before]
    b2 = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(CH, 'Modular Character Outfits - Fantasy[Standard]', 'Exports', 'glTF (Godot-Unreal)', 'Outfits', outfit + '.gltf'))
    fit = [o for o in bpy.data.objects if o not in b2]
    for o in fit:
        if o.type == 'MESH':
            o.parent = arm
            for md in o.modifiers:
                if md.type == 'ARMATURE': md.object = arm
        elif o.type in ('ARMATURE', 'EMPTY'): pass
    for o in fit:
        if o.type in ('ARMATURE', 'EMPTY') and o is not arm: bpy.data.objects.remove(o)
    COVER = ('spine', 'pelvis', 'thigh', 'calf', 'foot', 'ball', 'upperarm', 'clavicle')
    for o in base:
        if o.type == 'MESH' and o.name.startswith('SuperHero') or (o.type == 'MESH' and 'Superhero' in o.name):
            me = o.data; gi = {g.index: g.name for g in o.vertex_groups}
            import bmesh
            bm = bmesh.new(); bm.from_mesh(me); dl = bm.verts.layers.deform.active
            kill = []
            for v in bm.verts:
                if dl is None: break
                w = v[dl]
                if not w: continue
                g = max(w.items(), key=lambda kv: kv[1])[0]
                if any(gi.get(g, '').lower().startswith(c) for c in COVER): kill.append(v)
            bmesh.ops.delete(bm, geom=kill, context='VERTS'); bm.to_mesh(me); bm.free()
    hb = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(B, 'Hairstyles', 'Origin at 0', 'glTF (Godot)', hair + '.gltf'))
    for o in [o for o in bpy.data.objects if o not in hb]:
        if o.type == 'MESH':
            mw = o.matrix_world.copy(); o.parent = arm; o.parent_type = 'BONE'; o.parent_bone = 'Head'
            o.matrix_world = arm.matrix_world @ arm.pose.bones['Head'].matrix @ arm.pose.bones['Head'].bone.matrix_local.inverted() @ mw
        else: bpy.data.objects.remove(o)
    arm.location = loc; arm.rotation_euler = (0, 0, math.radians(yaw)); arm.scale = (0.9, 0.9, 0.9)
    for bn in ('spine_01', 'spine_02', 'spine_03'):
        pb = arm.pose.bones.get(bn)
        if pb: pb.scale = (0.88, 1.0, 0.9)
    for side, s_ in (('l', 1), ('r', -1)):
        b = arm.pose.bones.get('upperarm_' + side)
        if b: b.rotation_mode = 'XYZ'; b.rotation_euler = (0, 0, math.radians(-62 * s_))
    return arm, base + fit

rho, rho_objs = character('Male_Peasant', 'Hair_Buzzed', (7.0, -8.0, 0.02), 150)

# ------------------------------------------------------------------ the painted-toon look
def toonify(mat, tint=(1, 1, 1), shadow=(0.10, 0.12, 0.24)):
    """light → 3 hard bands (shadow tinted cold, lit tinted warm) × the kit's own colour texture = paint"""
    if not mat or not mat.use_nodes or mat.get('toon'): return
    nt = mat.node_tree; N, L = nt.nodes, nt.links
    out = next((n for n in N if n.type == 'OUTPUT_MATERIAL'), None)
    bsdf = next((n for n in N if n.type == 'BSDF_PRINCIPLED'), None)
    if not out or not bsdf: return
    col_src = bsdf.inputs['Base Color'].links[0].from_socket if bsdf.inputs['Base Color'].is_linked else None
    base = tuple(bsdf.inputs['Base Color'].default_value)
    diff = N.new('ShaderNodeBsdfDiffuse'); s2r = N.new('ShaderNodeShaderToRGB')
    ramp = N.new('ShaderNodeValToRGB'); cr = ramp.color_ramp; cr.interpolation = 'CONSTANT'
    cr.elements[0].position = 0.0; cr.elements[0].color = (*shadow, 1)
    cr.elements[1].position = 0.12; cr.elements[1].color = (0.36, 0.30, 0.36, 1)
    e = cr.elements.new(0.40); e.color = (1.0, 0.80, 0.62, 1)
    bw = N.new('ShaderNodeRGBToBW'); mul = N.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 1.0
    emit = N.new('ShaderNodeEmission')
    L.new(diff.outputs[0], s2r.inputs[0]); L.new(s2r.outputs['Color'], bw.inputs[0]); L.new(bw.outputs[0], ramp.inputs[0])
    if col_src: L.new(col_src, mul.inputs[6])
    else: mul.inputs[6].default_value = base
    L.new(ramp.outputs['Color'], mul.inputs[7])
    L.new(mul.outputs[2], emit.inputs['Color']); emit.inputs['Strength'].default_value = 1.0
    L.new(emit.outputs[0], out.inputs['Surface'])
    mat['toon'] = 1

for m in bpy.data.materials: toonify(m)

def flat(obj, rgb, emit=1.0):
    m = bpy.data.materials.new(obj.name + '_M'); m.use_nodes = True
    b = m.node_tree.nodes.get('Principled BSDF'); b.inputs['Base Color'].default_value = (*rgb, 1)
    obj.data.materials.clear(); obj.data.materials.append(m); toonify(m)
flat(water, (0.05, 0.16, 0.20)); flat(hill, (0.06, 0.07, 0.10))
for ob in bpy.data.objects:
    if ob.get('wood'): flat(ob, (0.22, 0.14, 0.09))
flat(tower, (0.75, 0.72, 0.66)); flat(cap, (0.45, 0.12, 0.10)); flat(rock, (0.16, 0.15, 0.16))

# lanterns along the quay: small warm emissive boxes + point lights (the ember key)
for i, x in enumerate([-7, -1, 5, 8.6]):
    y = -0.5 if i < 3 else -16.6
    bpy.ops.mesh.primitive_cube_add(size=0.28, location=(x, y - 0.3, 2.6 if i < 3 else 1.4)); lb = bpy.context.object
    m = bpy.data.materials.new('Lantern'); m.use_nodes = True; nt = m.node_tree
    em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (1.0, 0.45, 0.12, 1); em.inputs['Strength'].default_value = 2.2
    nt.links.new(em.outputs[0], nt.nodes['Material Output'].inputs['Surface']); lb.data.materials.append(m)
    bpy.ops.object.light_add(type='POINT', location=(x, y - 0.6, 2.4 if i < 3 else 1.3)); L_ = bpy.context.object
    L_.data.energy = 260; L_.data.color = (1.0, 0.55, 0.22); L_.data.shadow_soft_size = 0.2

# key: a low dusk sun from the sea side (ember), fill: cold teal sky
bpy.ops.object.light_add(type='SUN', rotation=(math.radians(78), 0, math.radians(-35))); sun = bpy.context.object
sun.data.energy = 1.6; sun.data.color = (1.0, 0.52, 0.30); sun.data.angle = math.radians(2)
w = bpy.data.worlds.new('Dusk'); sc.world = w; w.use_nodes = True
wn = w.node_tree.nodes; bg = wn['Background']
tc = wn.new('ShaderNodeTexCoord'); sep = wn.new('ShaderNodeSeparateXYZ'); rp = wn.new('ShaderNodeValToRGB')
ce = rp.color_ramp.elements
ce[0].position = 0.50; ce[0].color = (0.85, 0.30, 0.12, 1)      # the last of the sun at the horizon
ce[1].position = 0.62; ce[1].color = (0.05, 0.07, 0.14, 1)      # night coming down
m2 = ce.new(0.545); m2.color = (0.45, 0.20, 0.28, 1)
mr = wn.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = -1; mr.inputs['From Max'].default_value = 1
wl = w.node_tree.links
wl.new(tc.outputs['Generated'], sep.inputs[0]); wl.new(sep.outputs['Z'], mr.inputs['Value']); wl.new(mr.outputs[0], rp.inputs[0]); wl.new(rp.outputs[0], bg.inputs[0])
bg.inputs['Strength'].default_value = 1.0

# fog: a volume cube (thin) over the water and the quay
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -40, 4)); fog = bpy.context.object; fog.scale = (120, 120, 10); noink(fog)
fm = bpy.data.materials.new('Fog'); fm.use_nodes = True; fnt = fm.node_tree
vol = fnt.nodes.new('ShaderNodeVolumePrincipled'); vol.inputs['Density'].default_value = 0.012; vol.inputs['Color'].default_value = (0.55, 0.6, 0.7, 1)
fnt.nodes.remove(fnt.nodes['Principled BSDF']); fnt.links.new(vol.outputs[0], fnt.nodes['Material Output'].inputs['Volume']); fog.data.materials.append(fm)

# ink outlines: Freestyle (works in EEVEE; the Unreal port uses our ink post-process instead)
sc.render.use_freestyle = True; sc.render.line_thickness_mode = 'ABSOLUTE'; sc.render.line_thickness = 1.6
ls = sc.view_layers[0].freestyle_settings.linesets[0] if sc.view_layers[0].freestyle_settings.linesets else sc.view_layers[0].freestyle_settings.linesets.new('ink')
ls.select_by_visibility = True; ls.select_by_collection = True; ls.collection = NOINK; ls.collection_negation = 'EXCLUSIVE'; ls.select_silhouette = ls.select_border = ls.select_crease = True
if ls.linestyle is None: ls.linestyle = bpy.data.linestyles.new('Ink')
ls.linestyle.color = (0.03, 0.02, 0.03); ls.linestyle.thickness = 1.8

# camera
cams = {'wide': ((10.5, -19.0, 1.9), (0.0, -2.0, 3.0), 28), 'rho': ((8.9, -11.2, 1.55), (6.8, -7.6, 1.45), 40), 'sea': ((5.6, -5.5, 1.7), (24.0, -70.0, 6.0), 35)}
p, t, lens = cams[CAMNAME]
bpy.ops.object.camera_add(location=p); cam = bpy.context.object; cam.data.lens = lens
d = Vector(t) - Vector(p); cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler(); sc.camera = cam

sc.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE'
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1600, 900, 100
sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'; sc.view_settings.exposure = -0.6
os.makedirs(os.path.dirname(OUT), exist_ok=True); sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.splitext(OUT)[0] + '.blend')
print('RENDERED', OUT)
