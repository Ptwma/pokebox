# Pokebox — "props2" kit: Quaternius Fantasy Props MegaKit + Stylized Nature MegaKit (both CC0) re-styled for Pokebox.
# The packs ship trim-sheet PBR textures (normal + ORM maps), which would not match Pokebox's flat toon palette look.
# Every face gets ONE colour sampled from its texture (vertex colour), saturation is pushed a little, textures and
# UVs are dropped, the model is merged into one mesh named PR_<Name>, then the kit is exported as assets/world/props2.glb.
# Run inside Blender (Text editor or the MCP bridge): exec(bpy.data.texts['props2_lib'].as_string())
import bpy, os, numpy as np, colorsys
SRC = r"E:\GAME-APP DEV\POKEMON\incoming\props2_src"
if 'PROPS2' not in bpy.data.scenes: bpy.data.scenes.new('PROPS2')
sc = bpy.data.scenes['PROPS2']
_imgcache = {}
def img_arr(im):
    # read a 256 px copy of the texture (a 2048 px pixels[:] list crashed Blender: ~67M Python floats per image)
    key = im.name
    if key in _imgcache: return _imgcache[key]
    small = im.copy(); small.scale(256, 256)
    a = np.empty(256 * 256 * 4, dtype=np.float32); small.pixels.foreach_get(a); a = a.reshape(256, 256, 4)
    bpy.data.images.remove(small)
    _imgcache[key] = a; return a
def base_image(mat):
    if not mat or not mat.use_nodes: return None
    for n in mat.node_tree.nodes:
        if n.type == 'BSDF_PRINCIPLED':
            l = n.inputs['Base Color'].links
            if l:
                nd = l[0].from_node
                if nd.type == 'TEX_IMAGE': return nd.image
                for inp in nd.inputs:
                    for ll in inp.links:
                        if ll.from_node.type == 'TEX_IMAGE': return ll.from_node.image
    return None
def flat_color(mat):
    if mat and mat.use_nodes:
        for n in mat.node_tree.nodes:
            if n.type == 'BSDF_PRINCIPLED': return tuple(n.inputs['Base Color'].default_value[:3])
    return (.7, .7, .7)
def toonify(rgb):
    h, s, v = colorsys.rgb_to_hsv(*rgb)
    s = min(1, s * 1.18 + .04); v = min(1, v * 1.08 + .03)
    return colorsys.hsv_to_rgb(h, s, v)
def mix_info(mat):
    """the packs tint a greyscale trim texture with the mesh's vertex colours: Base Color = Mix(texture, Color Attribute)"""
    if not mat or not mat.use_nodes: return None
    for n in mat.node_tree.nodes:
        if n.type == 'MIX' and n.data_type == 'RGBA':
            fac = n.inputs[0].default_value if not n.inputs[0].links else 1.0
            return n.blend_type, fac
    return None
def face_vcol(me, p, attr):
    if attr is None: return None
    if attr.domain == 'CORNER': cs = [attr.data[li].color for li in p.loop_indices]
    else: cs = [attr.data[me.loops[li].vertex_index].color for li in p.loop_indices]
    return tuple(sum(c[k] for c in cs) / len(cs) for k in range(3))
def color_faces(o):
    """write one flat colour per face into a 'Col' corner attribute: texture colour x the pack's vertex tint"""
    me = o.data; uv = me.uv_layers.active
    tint = next((a for a in me.color_attributes if a.name != 'Col'), None)
    ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'CORNER')
    for p in me.polygons:
        mat = o.material_slots[p.material_index].material if o.material_slots and p.material_index < len(o.material_slots) else None
        im = base_image(mat)
        if im and uv:
            us = [uv.data[li].uv for li in p.loop_indices]
            cu = sum(u.x for u in us) / len(us); cv = sum(u.y for u in us) / len(us)
            a = img_arr(im); h, w = a.shape[:2]
            x = int((cu % 1) * (w - 1)); y = int((cv % 1) * (h - 1))
            px = a[max(0, y - 1):y + 2, max(0, x - 1):x + 2, :3].reshape(-1, 3).mean(0)
            rgb = tuple(float(c) for c in px)
        else: rgb = flat_color(mat)
        mi, vc = mix_info(mat), face_vcol(me, p, tint)
        if mi and vc:
            bt, fac = mi
            if bt == 'MULTIPLY': rgb = tuple(t * (1 - fac) + t * v * fac for t, v in zip(rgb, vc))
            elif bt == 'MIX': rgb = tuple(t * (1 - fac) + v * fac for t, v in zip(rgb, vc))
            elif bt == 'OVERLAY': rgb = tuple((2 * t * v if t < .5 else 1 - 2 * (1 - t) * (1 - v)) * fac + t * (1 - fac) for t, v in zip(rgb, vc))
            else: rgb = tuple(t * v for t, v in zip(rgb, vc))
        rgb = toonify(rgb)
        for li in p.loop_indices: ca.data[li].color = (*rgb, 1)
    if tint is not None: me.color_attributes.remove(tint)
def vcol_material():
    m = bpy.data.materials.get('PR_Vcol')
    if not m:
        m = bpy.data.materials.new('PR_Vcol'); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
        cn = nt.nodes.new('ShaderNodeVertexColor'); cn.layer_name = 'Col'; nt.links.new(cn.outputs['Color'], b.inputs['Base Color'])
        b.inputs['Roughness'].default_value = .85
    return m
def import_one(path, name, decimate=None):
    import bmesh
    before = set(bpy.data.objects)
    vl = sc.view_layers[0]
    with bpy.context.temp_override(window=bpy.context.window, scene=sc, view_layer=vl, collection=sc.collection):
        bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    bm = bmesh.new()
    for o in new:
        if o.type != 'MESH': continue
        color_faces(o)
        tmp = o.data.copy(); tmp.transform(o.matrix_world)
        for uvl in list(tmp.uv_layers): tmp.uv_layers.remove(uvl)
        bm.from_mesh(tmp); bpy.data.meshes.remove(tmp)
    for o in new:
        d = o.data if o.type == 'MESH' else None
        bpy.data.objects.remove(o, do_unlink=True)
        if d and d.users == 0: bpy.data.meshes.remove(d)
    old = bpy.data.objects.get('PR_' + name)
    if old: bpy.data.objects.remove(old, do_unlink=True)
    me = bpy.data.meshes.new('PR_' + name); bm.to_mesh(me); bm.free()
    for poly in me.polygons: poly.material_index = 0
    me.materials.append(vcol_material())
    ob = bpy.data.objects.new('PR_' + name, me); sc.collection.objects.link(ob)
    if decimate and len(me.polygons) > decimate:
        md = ob.modifiers.new('dec', 'DECIMATE'); md.ratio = decimate / len(me.polygons)
        dg = sc.view_layers[0].depsgraph; dg.update()
        m2 = bpy.data.meshes.new_from_object(ob.evaluated_get(dg)); ob.modifiers.clear(); ob.data = m2; bpy.data.meshes.remove(me); m2.name = 'PR_' + name
    return ob, len(ob.data.polygons)
PROPS = ['Anvil', 'Anvil_Log', 'Barrel', 'Barrel_Apples', 'Barrel_Holder', 'Bench', 'Bucket_Wooden_1', 'Bucket_Metal', 'Cage_Small', 'Cauldron',
         'Chest_Wood', 'Crate_Wooden', 'Crate_Metal', 'Dummy', 'FarmCrate_Apple', 'FarmCrate_Carrot', 'FarmCrate_Empty', 'Lantern_Wall', 'Pot_1', 'Rope_1',
         'Shield_Wooden', 'Stall_Cart_Empty', 'Stall_Empty', 'Stool', 'Table_Large', 'Torch_Metal', 'Vase_2', 'Vase_4', 'Vase_Rubble_Medium', 'WeaponStand',
         'Whetstone', 'Workbench', 'Banner_1', 'Banner_2', 'Bag', 'Pouch_Large', 'Chair_1', 'Pickaxe_Bronze', 'Axe_Bronze', 'Coin_Pile']
NATURE = ['RockPath_Round_Small_1', 'RockPath_Round_Small_2', 'RockPath_Round_Wide', 'RockPath_Square_Wide', 'Pebble_Round_1', 'Pebble_Round_2',
          'Pebble_Square_1', 'Mushroom_Laetiporus', 'Rock_Medium_1', 'Rock_Medium_2']
def build(names, folder, limit=6, decimate=2400):
    done = []
    for n in names:
        if ('PR_' + n) in bpy.data.objects: continue
        ob, tris = import_one(os.path.join(folder, n + '.gltf'), n, decimate)
        done.append((n, tris))
        if len(done) >= limit: break
    return done
def export(path):
    bpy.context.window.scene = sc
    for s in bpy.data.scenes:
        for vl in s.view_layers:
            for o in s.objects:
                try: o.select_set(False, view_layer=vl)
                except Exception: pass
    for o in sc.objects:
        if o.name.startswith('PR_'): o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_apply=True, export_yup=True, export_materials='EXPORT')
