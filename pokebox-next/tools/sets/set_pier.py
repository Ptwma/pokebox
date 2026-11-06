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
EXPORT = CAMNAME == 'export'   # export mode: no toon nodes, no character; writes <OUT>.fbx + <OUT>.json for Unreal (pbx_sets.py)
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
PLASTER_TINTS = [(1, 1, 1), (0.82, 0.86, 0.95), (0.95, 0.80, 0.72), (0.78, 0.84, 0.76), (0.70, 0.66, 0.72)]
def tint_obj(o, rgb, tag):
    """give this piece its own copies of the plaster materials, multiplied by a colour (houses painted differently)"""
    for i, m in enumerate(o.data.materials):
        if m and 'Plaster' in m.name:
            k = f'{m.name}_{tag}'
            mm = bpy.data.materials.get(k) or m.copy(); mm.name = k; mm['tint'] = rgb
            o.data.materials[i] = mm
def house(x0, floors, w=2, style='UnevenBrick', upper='Plaster', door_at=0, seed=0):
    rr = random.Random(seed); tint = rr.choice(PLASTER_TINTS); tag = f'h{seed}'
    for f in range(floors):
        z = f * 3.12
        mat = style if f == 0 else upper
        for i in range(w):
            x = x0 + i * 2 + 1
            if f == 0 and i == door_at: n = f'Wall_{mat}_Door_Round'
            else: n = rr.choice([f'Wall_{mat}_Window_Wide_Round', f'Wall_{mat}_Window_Thin_Round', f'Wall_{mat}_Straight'])
            fo = piece(n, (x, 0, z), 180)                  # facade faces -Y (the quay)
            fo.data = fo.data.copy(); tint_obj(fo, tint, tag)
            if 'Window_Wide' in n and rr.random() < 0.5:
                piece(rr.choice(['WindowShutters_Wide_Round_Open', 'WindowShutters_Wide_Round_Closed']), (x, -0.05, z), 180)
            if f == 1 and rr.random() < 0.25: piece('Balcony_Simple_Straight', (x, -0.1, z), 180)
            piece(f'Wall_{mat}_Straight', (x, 2 * 2, z), 0) # back
        for j in range(2):
            piece(f'Wall_{mat}_Straight', (x0, j * 2 + 1, z), 90)
            piece(f'Wall_{mat}_Straight', (x0 + w * 2, j * 2 + 1, z), -90)
        if f > 0: piece('Floor_WoodDark', (x0 + 1, 1, z), 0)
    piece(rr.choice(['Roof_RoundTiles_4x4', 'Roof_RoundTiles_4x4', 'Roof_RoundTiles_4x6']), (x0 + w, 2, floors * 3.12), 0)
    if rr.random() < 0.5: piece('Prop_Vine' + rr.choice(['1', '2', '4', '5']), (x0 + 0.6, -0.25, 0.1), 180)
    # the rooms behind the windows: a backdrop plane per floor, some lit warm (people at home), most dark
    for f in range(floors):
        bpy.ops.mesh.primitive_plane_add(size=1, location=(x0 + w, 1.2, f * 3.12 + 1.6), rotation=(math.radians(90), 0, 0))
        bp = bpy.context.object; bp.scale = (w * 2 - 0.2, 3.0, 1); noink(bp)
        lit = rr.random() < 0.4
        m = bpy.data.materials.new('RoomLit' if lit else 'RoomDark'); m.use_nodes = True; nt = m.node_tree
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
bpy.ops.mesh.primitive_cone_add(radius1=2.0, radius2=1.3, depth=16, vertices=24, location=(26, -70, 7)); tower = bpy.context.object
bpy.ops.mesh.primitive_cylinder_add(radius=1.45, depth=1.6, vertices=24, location=(26, -70, 15.8)); lamp_room = bpy.context.object
bpy.ops.mesh.primitive_cone_add(radius1=1.8, depth=1.8, vertices=24, location=(26, -70, 17.5)); cap = bpy.context.object
for zb in (3.0, 9.0):
    bpy.ops.mesh.primitive_cylinder_add(radius=1.9 - zb * 0.04, depth=2.2, vertices=24, location=(26, -70, zb)); band = bpy.context.object; band['band'] = 1
bpy.ops.mesh.primitive_cone_add(radius1=0.2, radius2=7.0, depth=60, vertices=24, location=(26 - 30 * 0.8, -70 + 30 * 0.6, 15.8), rotation=(0, math.radians(90), math.radians(143))); beam = bpy.context.object; noink(beam)
bm_ = bpy.data.materials.new('Beam'); bm_.use_nodes = True; bnt = bm_.node_tree
be = bnt.nodes.new('ShaderNodeEmission'); be.inputs['Color'].default_value = (1.0, 0.85, 0.55, 1); be.inputs['Strength'].default_value = 0.35
tr = bnt.nodes.new('ShaderNodeBsdfTransparent'); mx = bnt.nodes.new('ShaderNodeAddShader')
bnt.links.new(be.outputs[0], mx.inputs[0]); bnt.links.new(tr.outputs[0], mx.inputs[1]); bnt.links.new(mx.outputs[0], bnt.nodes['Material Output'].inputs['Surface'])
bm_.surface_render_method = 'BLENDED' if hasattr(bm_, 'surface_render_method') else bm_.blend_method; beam.data.materials.append(bm_); bm_['toon'] = 1
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
    for o in arm.children:
        if o.type == 'MESH' and ('Hair' in o.name or 'Eyebrow' in o.name):
            for i, m in enumerate(o.data.materials):
                if m: mm = m.copy(); mm['tint'] = (0.12, 0.13, 0.2); o.data.materials[i] = mm
    for o in base:
        if o.type == 'MESH' and 'Eyebrow' in o.name:
            for i, m in enumerate(o.data.materials):
                if m: mm = m.copy(); mm['tint'] = (0.12, 0.13, 0.2); o.data.materials[i] = mm
    arm.location = loc; arm.rotation_euler = (0, 0, math.radians(yaw)); arm.scale = (0.88, 0.88, 0.88)
    for bn in ('spine_01', 'spine_02', 'spine_03'):
        pb = arm.pose.bones.get(bn)
        if pb: pb.scale = (0.88, 1.0, 0.9)
    for side, s_ in (('l', 1), ('r', -1)):
        b = arm.pose.bones.get('upperarm_' + side)
        if b: b.rotation_mode = 'XYZ'; b.rotation_euler = (0, 0, math.radians(-74 * s_))
        lb = arm.pose.bones.get('lowerarm_' + side)
        if lb: lb.rotation_mode = 'XYZ'; lb.rotation_euler = (0, 0, math.radians(-12 * s_))
    hd = arm.pose.bones.get('Head')
    if hd: hd.rotation_mode = 'XYZ'; hd.rotation_euler = (math.radians(6), 0, math.radians(-10))
    return arm, base + fit

if not EXPORT: rho, rho_objs = character('Male_Peasant', 'Hair_Buzzed', (7.0, -8.0, 0.02), 150)

# ------------------------------------------------------------------ the painted-toon look
def toonify(mat, tint=(1, 1, 1), shadow=(0.10, 0.12, 0.24)):
    if EXPORT:   # Unreal draws the look with its own post-process; keep the kit's PBR materials (tints baked into base colour)
        if mat and mat.get('tint') and mat.use_nodes:
            b = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if b and not b.inputs['Base Color'].is_linked: b.inputs['Base Color'].default_value = tuple(c * t for c, t in zip(b.inputs['Base Color'].default_value, (*mat['tint'], 1)))
        return
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
    if col_src:
        if mat.get('tint'):
            tm = N.new('ShaderNodeMix'); tm.data_type = 'RGBA'; tm.blend_type = 'MULTIPLY'; tm.inputs['Factor'].default_value = 1.0
            L.new(col_src, tm.inputs[6]); tm.inputs[7].default_value = (*mat['tint'], 1); L.new(tm.outputs[2], mul.inputs[6])
        else: L.new(col_src, mul.inputs[6])
    else: mul.inputs[6].default_value = tuple(b * t for b, t in zip(base, (*mat.get('tint', (1, 1, 1)), 1)))
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
flat(tower, (0.80, 0.77, 0.70)); flat(cap, (0.35, 0.08, 0.07)); flat(rock, (0.12, 0.11, 0.12))
lm = bpy.data.materials.new('LampRoom'); lm.use_nodes = True; lnt = lm.node_tree
le = lnt.nodes.new('ShaderNodeEmission'); le.inputs['Color'].default_value = (1.0, 0.8, 0.45, 1); le.inputs['Strength'].default_value = 3.0
lnt.links.new(le.outputs[0], lnt.nodes['Material Output'].inputs['Surface']); lamp_room.data.materials.append(lm); lm['toon'] = 1
for ob in bpy.data.objects:
    if ob.get('band'): flat(ob, (0.45, 0.07, 0.06))

# lanterns along the quay: small warm emissive boxes + point lights (the ember key)
LANTERNS = [(-11, -0.45, 2.7), (-7, -0.45, 2.7), (-1, -0.45, 2.7), (5, -0.45, 2.7), (7.95, -12.0, 1.5)]
iron = bpy.data.materials.new('Iron'); iron.use_nodes = True; iron.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.03, 0.03, 0.035, 1); toonify(iron)
glass = bpy.data.materials.new('LanternGlass'); glass.use_nodes = True; gnt = glass.node_tree
ge = gnt.nodes.new('ShaderNodeEmission'); ge.inputs['Color'].default_value = (1.0, 0.48, 0.14, 1); ge.inputs['Strength'].default_value = 2.4
gnt.links.new(ge.outputs[0], gnt.nodes['Material Output'].inputs['Surface']); glass['toon'] = 1
for (x, y, z) in LANTERNS:
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y - 0.25, z)); fr = bpy.context.object; fr.scale = (0.26, 0.26, 0.34); fr.data.materials.append(iron)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y - 0.25, z)); gl = bpy.context.object; gl.scale = (0.2, 0.28, 0.26); gl.data.materials.append(glass)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y - 0.1, z + 0.22)); br = bpy.context.object; br.scale = (0.04, 0.3, 0.04); br.data.materials.append(iron)
    bpy.ops.object.light_add(type='POINT', location=(x, y - 0.7, z - 0.1)); L_ = bpy.context.object
    L_.data.energy = 420; L_.data.color = (1.0, 0.5, 0.2); L_.data.shadow_soft_size = 0.15

# key: a low dusk sun from the sea side (ember), fill: cold teal sky
bpy.ops.object.light_add(type='SUN', rotation=(math.radians(78), 0, math.radians(-35))); sun = bpy.context.object
sun.data.energy = 0.9; sun.data.color = (1.0, 0.52, 0.30); sun.data.angle = math.radians(2)
w = bpy.data.worlds.new('Dusk'); sc.world = w; w.use_nodes = True
wn = w.node_tree.nodes; bg = wn['Background']
tc = wn.new('ShaderNodeTexCoord'); sep = wn.new('ShaderNodeSeparateXYZ'); rp = wn.new('ShaderNodeValToRGB')
ce = rp.color_ramp.elements
ce[0].position = 0.50; ce[0].color = (0.70, 0.22, 0.10, 1)      # the last of the sun at the horizon
ce[1].position = 0.60; ce[1].color = (0.025, 0.035, 0.08, 1)      # night coming down
m2 = ce.new(0.535); m2.color = (0.28, 0.12, 0.20, 1)
mr = wn.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = -1; mr.inputs['From Max'].default_value = 1
wl = w.node_tree.links
wl.new(tc.outputs['Generated'], sep.inputs[0]); wl.new(sep.outputs['Z'], mr.inputs['Value']); wl.new(mr.outputs[0], rp.inputs[0]); wl.new(rp.outputs[0], bg.inputs[0])
bg.inputs['Strength'].default_value = 1.0

# fog: a volume cube (thin) over the water and the quay
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -40, 4)); fog = bpy.context.object; fog.scale = (120, 120, 10); noink(fog)
fm = bpy.data.materials.new('Fog'); fm.use_nodes = True; fnt = fm.node_tree
vol = fnt.nodes.new('ShaderNodeVolumePrincipled'); vol.inputs['Density'].default_value = 0.02; vol.inputs['Color'].default_value = (0.55, 0.6, 0.7, 1)
fnt.nodes.remove(fnt.nodes['Principled BSDF']); fnt.links.new(vol.outputs[0], fnt.nodes['Material Output'].inputs['Volume']); fog.data.materials.append(fm)

# ink outlines: Freestyle (works in EEVEE; the Unreal port uses our ink post-process instead)
sc.render.use_freestyle = True; sc.render.line_thickness_mode = 'ABSOLUTE'; sc.render.line_thickness = 1.6
ls = sc.view_layers[0].freestyle_settings.linesets[0] if sc.view_layers[0].freestyle_settings.linesets else sc.view_layers[0].freestyle_settings.linesets.new('ink')
ls.select_by_visibility = True; ls.select_by_collection = True; ls.collection = NOINK; ls.collection_negation = 'EXCLUSIVE'; ls.select_silhouette = ls.select_border = ls.select_crease = True
if ls.linestyle is None: ls.linestyle = bpy.data.linestyles.new('Ink')
ls.linestyle.color = (0.03, 0.02, 0.03); ls.linestyle.thickness = 1.8

if EXPORT:
    import json
    drop = [o for o in bpy.data.objects if o.type in ('CAMERA', 'LIGHT') or o is fog or o is beam]
    lights = [{'pos': [round(o.location.x * 100, 1), round(-o.location.y * 100, 1), round(o.location.z * 100, 1)], 'energy': o.data.energy, 'color': list(o.data.color), 'type': o.data.type} for o in bpy.data.objects if o.type == 'LIGHT' and o.data.type == 'POINT']
    for o in drop: bpy.data.objects.remove(o)
    fbx = os.path.splitext(OUT)[0] + '.fbx'; os.makedirs(os.path.dirname(fbx), exist_ok=True)
    bpy.ops.export_scene.fbx(filepath=fbx, use_selection=False, object_types={'MESH'}, apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS',
                             path_mode='COPY', embed_textures=True, mesh_smooth_type='FACE', use_mesh_modifiers=True, axis_forward='-Z', axis_up='Y')
    json.dump({'lights': lights, 'marks': {'rho': [700, 800, 0], 'pier_end': [700, 1700, 0], 'quay': [0, 300, 0], 'houses': [-500, 100, 0]}},
              open(os.path.splitext(OUT)[0] + '.json', 'w'), indent=1)
    print('EXPORTED', fbx, len(lights), 'lights')
    raise SystemExit(0)

# camera
cams = {'wide': ((15.5, -15.0, 2.3), (1.0, -3.0, 3.4), 27), 'rho': ((8.9, -11.2, 1.55), (6.8, -7.6, 1.45), 40), 'sea': ((5.6, -5.5, 1.7), (24.0, -70.0, 6.0), 35)}
p, t, lens = cams[CAMNAME]
bpy.ops.object.camera_add(location=p); cam = bpy.context.object; cam.data.lens = lens
d = Vector(t) - Vector(p); cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler(); sc.camera = cam

sc.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE'
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1600, 900, 100
sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'; sc.view_settings.exposure = -0.75
os.makedirs(os.path.dirname(OUT), exist_ok=True); sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.splitext(OUT)[0] + '.blend')
print('RENDERED', OUT)
