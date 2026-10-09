# Pokebox Next — builds the first town in Unreal from the Blender output (PokeboxNext_src): imports textures and meshes,
# creates the materials (PBR surfaces from Poly Haven, foliage from the Quaternius kit, ground blend, water), lays out the
# level from town_plan.json and sets up the lighting (Lumen, sky atmosphere, clouds, fog, post process).
# Re-runnable: every step replaces what it made before. Units: Unreal cm.
import unreal, os, json, math

SRC = r"E:\GAME-APP-DEV\POKEMON\PokeboxNext_src"
G = '/Game/PBX'
AT = unreal.AssetToolsHelpers.get_asset_tools()
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary

def log(*a): print('[pbx]', *a)

def sp(obj, **kw):
    """set editor properties, trying alternative names; logs what does not exist in this engine version"""
    for k, v in kw.items():
        for name in (k, 'b_' + k, 'enable_' + k, 'b_enable_' + k):
            try: obj.set_editor_property(name, v); break
            except Exception: continue
        else: log('no property', type(obj).__name__, k)

# ------------------------------------------------------------------ import
def _import(files, dest):
    tasks = []
    for f in files:
        t = unreal.AssetImportTask()
        t.set_editor_property('filename', f); t.set_editor_property('destination_path', dest)
        t.set_editor_property('automated', True); t.set_editor_property('replace_existing', True); t.set_editor_property('save', True)
        tasks.append(t)
    AT.import_asset_tasks(tasks)
    out = []
    for t in tasks: out += list(t.get_editor_property('imported_object_paths') or [])
    return out

def import_textures():
    tex = os.path.join(SRC, 'tex'); files = [os.path.join(tex, f) for f in sorted(os.listdir(tex)) if f.endswith('.jpg') and os.path.getsize(os.path.join(tex, f)) > 0]
    ntex = os.path.join(SRC, 'nature', 'Textures'); files += [os.path.join(ntex, f) for f in sorted(os.listdir(ntex)) if f.endswith('.png')]
    paths = _import(files, G + '/Tex')
    for p in EAL.list_assets(G + '/Tex', recursive=False):
        a = EAL.load_asset(p)
        if not isinstance(a, unreal.Texture2D): continue
        n = a.get_name().lower()
        if n.endswith('_nor') or n.endswith('_normal'):
            a.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_NORMALMAP); a.set_editor_property('srgb', False)
            if n.endswith('_nor'): a.set_editor_property('flip_green_channel', True)  # Poly Haven ships OpenGL normals
        elif n.endswith('_arm') or n.startswith('t_townsplat'):
            a.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_MASKS); a.set_editor_property('srgb', False)
        a.set_editor_property('max_texture_size', 2048)
        EAL.save_loaded_asset(a)
    log('textures', len(paths))

def import_meshes():
    fbx = os.path.join(SRC, 'fbx'); nat = os.path.join(SRC, 'nature', 'FBX')
    a = _import([os.path.join(fbx, f) for f in sorted(os.listdir(fbx)) if f.endswith('.fbx')], G + '/Meshes')
    b = _import([os.path.join(nat, f) for f in sorted(os.listdir(nat)) if f.endswith('.fbx')], G + '/Nature')
    log('meshes', len(a), 'nature', len(b))

# ------------------------------------------------------------------ materials
def _fresh(name, path, cls=unreal.Material, factory=None):
    full = f'{path}/{name}'
    if EAL.does_asset_exist(full): EAL.delete_asset(full)
    return AT.create_asset(name, path, cls, factory or unreal.MaterialFactoryNew())

def _e(m, cls, x, y): return MEL.create_material_expression(m, cls, x, y)

def _texp(m, name, x, y, sampler=None, default=None):
    t = _e(m, unreal.MaterialExpressionTextureSampleParameter2D, x, y); t.set_editor_property('parameter_name', name)
    if sampler is not None: t.set_editor_property('sampler_type', sampler)
    if default: t.set_editor_property('texture', unreal.load_asset(default))
    return t

def _scalar(m, name, v, x, y):
    s = _e(m, unreal.MaterialExpressionScalarParameter, x, y); s.set_editor_property('parameter_name', name); s.set_editor_property('default_value', v); return s

def _vec(m, name, v, x, y):
    s = _e(m, unreal.MaterialExpressionVectorParameter, x, y); s.set_editor_property('parameter_name', name); s.set_editor_property('default_value', unreal.LinearColor(*v)); return s

def _mul(m, a, b, x, y, ao='', bo=''):
    n = _e(m, unreal.MaterialExpressionMultiply, x, y); MEL.connect_material_expressions(a, ao, n, 'A'); MEL.connect_material_expressions(b, bo, n, 'B'); return n

WHITE = '/Engine/EngineResources/WhiteSquareTexture.WhiteSquareTexture'
FLATN = '/Engine/EngineMaterials/DefaultNormal.DefaultNormal'
NORMAL = unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL
MASKS = unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR

def master_surface():
    m = _fresh('M_PBX_Surface', G + '/Materials')
    uv = _e(m, unreal.MaterialExpressionTextureCoordinate, -1400, 0); sc = _scalar(m, 'UVScale', 1.0, -1400, 150)
    uvs = _mul(m, uv, sc, -1200, 50)
    base = _texp(m, 'BaseTex', -900, -300, default=WHITE); nor = _texp(m, 'NormalTex', -900, 50, NORMAL, FLATN); arm = _texp(m, 'ArmTex', -900, 400, MASKS, WHITE)
    for t in (base, nor, arm): MEL.connect_material_expressions(uvs, '', t, 'UVs')
    tint = _vec(m, 'Tint', (1, 1, 1, 1), -700, -450)
    MEL.connect_material_property(_mul(m, base, tint, -450, -350, 'RGB'), '', unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(nor, 'RGB', unreal.MaterialProperty.MP_NORMAL)
    MEL.connect_material_property(arm, 'R', unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
    MEL.connect_material_property(_mul(m, arm, _scalar(m, 'RoughMul', 1.0, -700, 550), -450, 450, 'G'), '', unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.recompile_material(m); EAL.save_loaded_asset(m); return m

def master_color():
    m = _fresh('M_PBX_Color', G + '/Materials')
    MEL.connect_material_property(_vec(m, 'Color', (.8, .8, .8, 1), -500, -200), '', unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(_scalar(m, 'Roughness', .6, -500, 0), '', unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(_scalar(m, 'Metallic', 0.0, -500, 100), '', unreal.MaterialProperty.MP_METALLIC)
    MEL.connect_material_property(_mul(m, _vec(m, 'Emissive', (0, 0, 0, 1), -700, 250), _scalar(m, 'EmissiveMul', 0.0, -700, 400), -500, 300), '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    MEL.recompile_material(m); EAL.save_loaded_asset(m); return m

def master_foliage(wind=False):
    m = _fresh('M_PBX_Foliage', G + '/Materials')
    m.set_editor_property('blend_mode', unreal.BlendMode.BLEND_MASKED); m.set_editor_property('two_sided', True)
    t = _texp(m, 'Tex', -800, 0, default=WHITE); tint = _vec(m, 'Tint', (1, 1, 1, 1), -800, -250)
    MEL.connect_material_property(_mul(m, t, tint, -500, -100, 'RGB'), '', unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(t, 'A', unreal.MaterialProperty.MP_OPACITY_MASK)
    MEL.connect_material_property(_scalar(m, 'Roughness', .65, -500, 150), '', unreal.MaterialProperty.MP_ROUGHNESS)
    # gentle wind sway (engine material function)
    if wind:
     try:
        fn = unreal.load_asset('/Engine/Functions/Engine_MaterialFunctions01/WorldPositionOffset/SimpleGrassWind.SimpleGrassWind')
        w = _e(m, unreal.MaterialExpressionMaterialFunctionCall, -500, 350); w.set_editor_property('material_function', fn)
        log('wind inputs', MEL.get_material_expression_input_names(w))
        MEL.connect_material_expressions(_scalar(m, 'WindIntensity', .15, -800, 300), '', w, 'WindIntensity')
        MEL.connect_material_expressions(_scalar(m, 'WindSpeed', .25, -800, 400), '', w, 'WindSpeed')
        MEL.connect_material_expressions(_scalar(m, 'WindWeight', 1.0, -800, 500), '', w, 'WindWeight')
        MEL.connect_material_property(w, '', unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
     except Exception as ex: log('wind skipped', ex)
    MEL.recompile_material(m); EAL.save_loaded_asset(m)
    st = MEL.get_statistics(m); log('foliage instr', st.num_pixel_shader_instructions)
    return m

def master_ground():
    m = _fresh('M_PBX_Ground', G + '/Materials')
    uv = _e(m, unreal.MaterialExpressionTextureCoordinate, -2200, 0)
    # layer mask from the town splat texture, sampled by world XY (town square = 220 m centred on the origin)
    wp = _e(m, unreal.MaterialExpressionWorldPosition, -1600, -1100); cm = _e(m, unreal.MaterialExpressionComponentMask, -1400, -1100)
    cm.set_editor_property('r', True); cm.set_editor_property('g', True); MEL.connect_material_expressions(wp, '', cm, '')
    dv = _e(m, unreal.MaterialExpressionDivide, -1200, -1100); dv.set_editor_property('const_b', 22000.0); MEL.connect_material_expressions(cm, '', dv, 'A')
    ad = _e(m, unreal.MaterialExpressionAdd, -1000, -1100); ad.set_editor_property('const_b', 0.5); MEL.connect_material_expressions(dv, '', ad, 'A')
    vc = _texp(m, 'Splat', -800, -1100, MASKS, WHITE); MEL.connect_material_expressions(ad, '', vc, 'UVs')
    layers = []
    for i, key in enumerate(['Grass', 'Dirt', 'Sand', 'Stone']):
        sc = _scalar(m, key + 'UV', 2.0 if key != 'Stone' else 2.5, -2200, 200 + i * 900); uvs = _mul(m, uv, sc, -2000, 100 + i * 900)
        b = _texp(m, key + 'Base', -1700, i * 900, default=WHITE); n = _texp(m, key + 'Nor', -1700, 300 + i * 900, NORMAL, FLATN); a = _texp(m, key + 'Arm', -1700, 600 + i * 900, MASKS, WHITE)
        for t in (b, n, a): MEL.connect_material_expressions(uvs, '', t, 'UVs')
        layers.append((b, n, a))
    def lerp(a, ao, b, bo, alpha_ch, x, y):
        l = _e(m, unreal.MaterialExpressionLinearInterpolate, x, y)
        MEL.connect_material_expressions(a, ao, l, 'A'); MEL.connect_material_expressions(b, bo, l, 'B'); MEL.connect_material_expressions(vc, alpha_ch, l, 'Alpha'); return l
    out = {}
    for k, (ch, idx) in {'base': ('RGB', 0), 'nor': ('RGB', 1), 'rough': ('G', 2)}.items():
        g0 = layers[0][idx]
        l1 = lerp(g0, ch, layers[1][idx], ch, 'R', -1200, idx * 400)
        l2 = lerp(l1, '', layers[2][idx], ch, 'G', -1000, idx * 400)
        l3 = lerp(l2, '', layers[3][idx], ch, 'B', -800, idx * 400)
        out[k] = l3
    tint = _vec(m, 'GrassTint', (1, 1, 1, 1), -800, -700)
    MEL.connect_material_property(_mul(m, out['base'], tint, -600, -300), '', unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(out['nor'], '', unreal.MaterialProperty.MP_NORMAL)
    MEL.connect_material_property(out['rough'], '', unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.recompile_material(m); EAL.save_loaded_asset(m); return m

def master_water():
    m = _fresh('M_PBX_Water', G + '/Materials')
    fres = _e(m, unreal.MaterialExpressionFresnel, -900, 0)
    deep = _vec(m, 'Deep', (.01, .09, .16, 1), -900, -300); shallow = _vec(m, 'Shallow', (.05, .32, .38, 1), -900, -150)
    l = _e(m, unreal.MaterialExpressionLinearInterpolate, -600, -200)
    MEL.connect_material_expressions(deep, '', l, 'A'); MEL.connect_material_expressions(shallow, '', l, 'B'); MEL.connect_material_expressions(fres, '', l, 'Alpha')
    MEL.connect_material_property(l, '', unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(_scalar(m, 'Roughness', .035, -600, 100), '', unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(_scalar(m, 'Specular', 1.0, -600, 200), '', unreal.MaterialProperty.MP_SPECULAR)
    # moving ripples: two panning noise-free normals from the stone texture would look wrong, so use the engine's water normal if present
    try:
        wn = unreal.load_asset('/Engine/EngineMaterials/T_Water_N.T_Water_N') or unreal.load_asset('/Engine/VREditor/Textures/T_Water_N.T_Water_N')
    except Exception: wn = None
    if wn:
        uv = _e(m, unreal.MaterialExpressionTextureCoordinate, -1500, 400); uv.set_editor_property('u_tiling', 18.0); uv.set_editor_property('v_tiling', 18.0)
        pan = _e(m, unreal.MaterialExpressionPanner, -1300, 400); pan.set_editor_property('speed_x', .01); pan.set_editor_property('speed_y', .007)
        MEL.connect_material_expressions(uv, '', pan, 'Coordinate')
        t = _e(m, unreal.MaterialExpressionTextureSample, -1000, 400); t.set_editor_property('texture', wn); t.set_editor_property('sampler_type', NORMAL)
        MEL.connect_material_expressions(pan, '', t, 'UVs'); MEL.connect_material_property(t, 'RGB', unreal.MaterialProperty.MP_NORMAL)
    MEL.recompile_material(m); EAL.save_loaded_asset(m); return m

def _mi(name, parent, scalars=None, vectors=None, textures=None):
    path = G + '/Materials/Inst'; full = f'{path}/{name}'
    if EAL.does_asset_exist(full): EAL.delete_asset(full)
    mi = AT.create_asset(name, path, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, parent)
    for k, v in (scalars or {}).items(): MEL.set_material_instance_scalar_parameter_value(mi, k, v)
    for k, v in (vectors or {}).items(): MEL.set_material_instance_vector_parameter_value(mi, k, unreal.LinearColor(*v))
    for k, v in (textures or {}).items():
        t = unreal.load_asset(f'{G}/Tex/{v}')
        if t: MEL.set_material_instance_texture_parameter_value(mi, k, t)
        else: log('missing texture', v)
    MEL.update_material_instance(mi); EAL.save_loaded_asset(mi); return mi

def _ph(base): return {'BaseTex': base + '_diff', 'NormalTex': base + '_nor', 'ArmTex': base + '_arm'}

def make_materials():
    S, C, F, Gm, W = master_surface(), master_color(), master_foliage(), master_ground(), master_water()
    M = {}
    # building surfaces (Blender box UVs: 1 UV = 1 m)
    # Wolf-Among-Us look: walls and roofs are flat painted colour (the modelled boards and tiles give the detail, the ink pass draws it)
    M['M_Siding_White'] = _mi('MI_Siding_White', C, {'Roughness': .7}, {'Color': (.82, .84, .86, 1)})
    M['M_Siding_Cream'] = _mi('MI_Siding_Cream', C, {'Roughness': .7}, {'Color': (.86, .76, .58, 1)})
    M['M_Plaster'] = _mi('MI_Plaster', C, {'Roughness': .8}, {'Color': (.7, .7, .68, 1)})
    M['M_Roof_Red'] = _mi('MI_Roof_Red', S, {'UVScale': .45}, {'Tint': (1.25, .55, .45, 1)}, _ph('grey_roof_tiles'))
    M['M_Roof_Blue'] = _mi('MI_Roof_Blue', S, {'UVScale': .45}, {'Tint': (.45, .7, 1.35, 1)}, _ph('grey_roof_tiles'))
    M['M_Stone'] = _mi('MI_Stone', S, {'UVScale': .6}, {}, _ph('rustic_stone_wall'))
    M['M_Brick'] = _mi('MI_Brick', S, {'UVScale': .8}, {}, _ph('red_brick'))
    M['M_WoodBox'] = _mi('MI_WoodBox', S, {'UVScale': 1.0}, {'Tint': (.85, .7, .55, 1)}, _ph('brown_planks_05'))
    M['M_WoodDark'] = _mi('MI_WoodDark', S, {'UVScale': 1.0}, {'Tint': (.55, .42, .32, 1)}, _ph('brown_planks_05'))
    M['M_WoodLight'] = _mi('MI_WoodLight', S, {'UVScale': 1.0}, {'Tint': (1.05, .95, .8, 1)}, _ph('oak_wood_planks'))
    M['M_Floor'] = _mi('MI_Floor', S, {'UVScale': .5, 'RoughMul': .45}, {}, _ph('old_wood_floor'))
    for k, col, r, met in [('M_Trim', (.92, .92, .9, 1), .5, 0), ('M_Glass', (.04, .07, .1, 1), .04, 0), ('M_Door', (.18, .3, .55, 1), .45, 0),
                           ('M_Metal', (.55, .56, .58, 1), .35, 1), ('M_Iron', (.06, .06, .07, 1), .45, 1), ('M_MailBlue', (.1, .28, .65, 1), .4, 0),
                           ('M_Red', (.8, .08, .06, 1), .4, 0), ('M_BinGreen', (.12, .3, .16, 1), .5, 0)]:
        M[k] = _mi('MI_' + k[2:], C, {'Roughness': r, 'Metallic': met}, {'Color': col})
    M['M_LampGlass'] = _mi('MI_LampGlass', C, {'Roughness': .2, 'EmissiveMul': 4.0}, {'Color': (1, .9, .7, 1), 'Emissive': (1, .78, .45, 1)})
    M['M_Ground'] = _mi('MI_Ground', Gm, {}, {'GrassTint': (.55, 1.25, .38, 1)}, {'Splat': 'T_TownSplat', 'GrassBase': 'leafy_grass_diff', 'GrassNor': 'leafy_grass_nor', 'GrassArm': 'leafy_grass_arm',
                        'DirtBase': 'park_dirt_diff', 'DirtNor': 'park_dirt_nor', 'DirtArm': 'park_dirt_arm', 'SandBase': 'coast_sand_01_diff', 'SandNor': 'coast_sand_01_nor',
                        'SandArm': 'coast_sand_01_arm', 'StoneBase': 'grey_stone_path_diff', 'StoneNor': 'grey_stone_path_nor', 'StoneArm': 'grey_stone_path_arm'})
    M['M_Water'] = _mi('MI_Water', W)
    # nature kit (Quaternius): slot names in the FBX → our instances
    M['Leaves_NormalTree'] = _mi('MI_Leaves_Tree', F, {}, {'Tint': (1.0, 1.08, .9, 1)}, {'Tex': 'Leaves_NormalTree_C'})
    M['Leaves_Pine'] = _mi('MI_Leaves_Pine', F, {}, {}, {'Tex': 'Leaf_Pine_C'})
    M['Leaves_TwistedTree'] = _mi('MI_Leaves_Twisted', F, {}, {}, {'Tex': 'Leaves_TwistedTree_C'})
    M['Leaves_GiantPine'] = _mi('MI_Leaves_GiantPine', F, {}, {}, {'Tex': 'Leaves_GiantPine_C'})
    M['Leaves'] = _mi('MI_Leaves_Plant', F, {}, {}, {'Tex': 'Leaves'})
    M['Flowers'] = _mi('MI_Flowers', F, {'WindIntensity': .25}, {}, {'Tex': 'Flowers'})
    M['Grass'] = _mi('MI_GrassClump', F, {'WindIntensity': .35}, {'Tint': (.95, 1.05, .8, 1)}, {'Tex': 'Grass'})
    M['Bark_NormalTree'] = _mi('MI_Bark_Tree', S, {'RoughMul': .85}, {}, {'BaseTex': 'Bark_NormalTree', 'NormalTex': 'Bark_NormalTree_Normal'})
    M['Bark_DeadTree'] = _mi('MI_Bark_Dead', S, {'RoughMul': .85}, {}, {'BaseTex': 'Bark_DeadTree', 'NormalTex': 'Bark_DeadTree_Normal'})
    M['Bark_TwistedTree'] = _mi('MI_Bark_Twisted', S, {'RoughMul': .85}, {}, {'BaseTex': 'Bark_TwistedTree', 'NormalTex': 'Bark_TwistedTree_Normal'})
    M['Rocks'] = _mi('MI_Rocks', S, {'RoughMul': .8}, {}, {'BaseTex': 'Rocks_Diffuse'})
    M['PathRocks'] = _mi('MI_PathRocks', S, {'RoughMul': .8}, {}, {'BaseTex': 'PathRocks_Diffuse'})
    M['Mushrooms'] = _mi('MI_Mushrooms', S, {'RoughMul': .7}, {}, {'BaseTex': 'Mushrooms'})
    log('materials', len(M)); return M

def assign_materials(M):
    n = 0
    for folder in (G + '/Meshes', G + '/Nature'):
        for p in EAL.list_assets(folder, recursive=True):
            sm = EAL.load_asset(p)
            if not isinstance(sm, unreal.StaticMesh): continue
            mats = sm.get_editor_property('static_materials')
            for i, sl in enumerate(mats):
                nm = str(sl.get_editor_property('material_slot_name'))
                key = nm.split('.')[0]
                mi = M.get(key) or M.get(key.replace('MI_', 'M_'))
                if not mi:
                    for k in M:
                        if key.startswith(k): mi = M[k]; break
                if mi: sm.set_material(i, mi); n += 1
                else: log('no material for slot', sm.get_name(), nm)
            # collision: walk on houses/ground/props; plants have none
            bs = sm.get_editor_property('body_setup')
            name = sm.get_name()
            if bs:
                plant = any(name.startswith(k) for k in ('Grass', 'Flower', 'Clover', 'Fern', 'Plant', 'Petal', 'Bush', 'Mushroom', 'Pebble'))
                bs.set_editor_property('collision_trace_flag', unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
                if plant: bs.set_editor_property('collision_trace_flag', unreal.CollisionTraceFlag.CTF_USE_DEFAULT)
            EAL.save_loaded_asset(sm)
    log('slots assigned', n)

# ------------------------------------------------------------------ level
KIT_SCALE = {'Fern_1': .22, 'Flower_3_Group': .55, 'Flower_4_Group': .55, 'Grass_Common_Tall': .5, 'Grass_Wispy_Tall': .5, 'Plant_1': .8, 'Bush_Common': .9, 'Bush_Common_Flowers': .85}
NO_COLLIDE = ('Grass', 'Flower', 'Clover', 'Fern', 'Plant', 'Petal', 'Pebble', 'Mushroom')
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

def _mesh(name):
    for f in ('Meshes', 'Nature'):
        p = f'{G}/{f}/{name}'
        if EAL.does_asset_exist(p): return unreal.load_asset(p)
    return None

def _spawn_cls(cls, loc=(0, 0, 0), rot=(0, 0, 0), label=None):
    a = EAS.spawn_actor_from_class(cls, unreal.Vector(*loc), unreal.Rotator(*rot))
    if label: a.set_actor_label(label)
    return a

def build_level():
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    path = G + '/Maps/L_Town'
    if EAL.does_asset_exist(path): les.load_level(path)
    else: les.new_level(path)
    for a in EAS.get_all_level_actors(): EAS.destroy_actor(a)
    plan = json.load(open(os.path.join(SRC, 'town_plan.json'), encoding='utf-8'))
    # ---- light & atmosphere (warm late-morning sun like the reference)
    sun = _spawn_cls(unreal.DirectionalLight, (0, 0, 1000), (0, -38, 35), 'Sun')
    lc = sun.get_component_by_class(unreal.DirectionalLightComponent)
    sp(lc, intensity=8.0, light_color=unreal.Color(r=255, g=244, b=228, a=255), atmosphere_sun_light=True, mobility=unreal.ComponentMobility.MOVABLE, light_source_angle=1.2)
    _spawn_cls(unreal.SkyAtmosphere, label='SkyAtmosphere')
    sky = _spawn_cls(unreal.SkyLight, (0, 0, 800), label='SkyLight'); sc = sky.get_component_by_class(unreal.SkyLightComponent)
    sp(sc, mobility=unreal.ComponentMobility.MOVABLE, real_time_capture=True, intensity=1.1)
    try: _spawn_cls(unreal.VolumetricCloud, label='Clouds')
    except Exception as ex: log('clouds', ex)
    fog = _spawn_cls(unreal.ExponentialHeightFog, (0, 0, -200), label='Fog'); fc = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
    sp(fc, fog_density=.006, fog_height_falloff=.25, volumetric_fog=True, start_distance=1500.0)
    pp = _spawn_cls(unreal.PostProcessVolume, label='PostProcess'); pp.set_editor_property('unbound', True)
    s = pp.get_editor_property('settings')
    for k, v in [('auto_exposure_bias', .3), ('bloom_intensity', .55), ('ambient_occlusion_intensity', .75),
                 ('ambient_occlusion_radius', 120.0), ('vignette_intensity', .25), ('color_saturation', unreal.Vector4(1.12, 1.12, 1.12, 1)),
                 ('color_contrast', unreal.Vector4(1.04, 1.04, 1.04, 1)), ('white_temp', 6200.0), ('sharpen', .4)]:
        try: s.set_editor_property('override_' + k, True); s.set_editor_property(k, v)
        except Exception as ex: log('pp', k, ex)
    pp.set_editor_property('settings', s)
    # ---- ground, water, buildings, props, foliage
    def put(mesh, x, y, z, rot=0.0, scale=1.0, label=None):
        sm = _mesh(mesh)
        if not sm: log('missing mesh', mesh); return None
        a = EAS.spawn_actor_from_object(sm, unreal.Vector(x * 100, -y * 100, z * 100), unreal.Rotator(0, 0, -rot))
        a.set_actor_scale3d(unreal.Vector(scale, scale, scale))
        if label: a.set_actor_label(label)
        if mesh.startswith(NO_COLLIDE):
            a.get_component_by_class(unreal.StaticMeshComponent).set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        a.set_folder_path('Town/' + ('Nature' if not mesh.startswith('SM_') else 'Built'))
        return a
    put('SM_Ground', 0, 0, 0, label='Ground')
    w = plan['water']; put('SM_Water', w['x'], w['y'], w['z'], label='Sea')
    for o in plan['objects']:
        put(o['mesh'], o['x'], o['y'], o['z'], o['rot'], o['s'] * KIT_SCALE.get(o['mesh'], 1.0))
    ps = plan['player_start']
    _spawn_cls(unreal.PlayerStart, (ps['x'] * 100, -ps['y'] * 100, ps['z'] * 100 + 100), (0, 0, -ps['rot']), 'PlayerStart')
    # game mode: the template's third-person setup
    try:
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        gm = unreal.load_class(None, '/Game/ThirdPerson/Blueprints/BP_ThirdPersonGameMode.BP_ThirdPersonGameMode_C')
        world.get_world_settings().set_editor_property('default_game_mode', gm)
    except Exception as ex: log('game mode', ex)
    les.save_current_level()
    log('level built', len(plan['objects']), 'objects')

def all_steps():
    import_textures(); import_meshes(); M = make_materials(); assign_materials(M); build_level()

# ------------------------------------------------------------------ "graphic novel" look (The Wolf Among Us style)
# A post-process material: thick ink outlines from depth + normal discontinuities, soft cel bands on the lighting,
# a touch of extra saturation, and a paper-warm ink colour. Mirrors js/comic.js of the web version.
COMIC_HLSL = r'''
float2 uv = GetDefaultSceneTextureUV(Parameters, 14);
float2 px = View.BufferSizeAndInvSize.zw * Thick;
float3 c = SceneTextureLookup(uv, 14, false).rgb;
float d = SceneTextureLookup(uv, 1, false).r;
float3 n = SceneTextureLookup(uv, 8, false).rgb;
float dd = 0, nd = 0;
float2 o[8] = { float2(px.x,0), float2(-px.x,0), float2(0,px.y), float2(0,-px.y), px, -px, float2(px.x,-px.y), float2(-px.x,px.y) };
for (int i = 0; i < 8; i++) {
    float di = SceneTextureLookup(uv + o[i], 1, false).r;
    dd = max(dd, abs(di - d) / max(min(d, di), 1.0));
    float3 ni = SceneTextureLookup(uv + o[i], 8, false).rgb;
    nd = max(nd, 1.0 - saturate(dot(normalize(ni), normalize(n))));
}
float fade = saturate(1.0 - d / FadeDist);
float edge = saturate(max((dd - DepthT) * DepthK, (nd - NormT) * NormK)) * fade;
float L = dot(c, float3(0.299, 0.587, 0.114));
float B = Bands; float f = frac(L * B);
float Lq = (floor(L * B) + smoothstep(0.5 - Soft, 0.5 + Soft, f)) / B;
float3 cel = c * (max(Lq, 0.02) / max(L, 0.02));
float3 col = lerp(c, cel, CelAmt);
float g = dot(col, float3(0.299, 0.587, 0.114)); col = lerp(g.xxx, col, Sat);
col = lerp(col, Ink, edge * InkAmt);
return col + (DummyA.rgb + DummyB.rrr + DummyC.rgb) * 0.0;
'''

def master_comic():
    m = _fresh('M_PBX_Comic', G + '/Materials')
    m.set_editor_property('material_domain', unreal.MaterialDomain.MD_POST_PROCESS)
    try: m.set_editor_property('blendable_location', unreal.BlendableLocation.BL_SCENE_COLOR_AFTER_TONEMAPPING)
    except Exception:
        try: m.set_editor_property('blendable_location', unreal.BlendableLocation.BL_AFTER_TONEMAPPING)
        except Exception as ex: log('blendable location', ex)
    cu = _e(m, unreal.MaterialExpressionCustom, -400, 0)
    cu.set_editor_property('code', COMIC_HLSL); cu.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    names = [('Thick', 2.1), ('DepthT', .015), ('DepthK', 18.0), ('NormT', .2), ('NormK', 3.5), ('FadeDist', 12000.0), ('Bands', 3.5), ('Soft', .06),
             ('CelAmt', .8), ('Sat', 1.22), ('InkAmt', .95)]
    ins = []
    for k in [n for n, _ in names] + ['Ink', 'DummyA', 'DummyB', 'DummyC']:
        ci = unreal.CustomInput(); ci.set_editor_property('input_name', k); ins.append(ci)
    cu.set_editor_property('inputs', ins)
    y = 0
    for k, v in names: MEL.connect_material_expressions(_scalar(m, k, v, -900, y), '', cu, k); y += 70
    MEL.connect_material_expressions(_vec(m, 'Ink', (.035, .028, .04, 1), -900, y), '', cu, 'Ink')
    for k, sid in (('DummyA', unreal.SceneTextureId.PPI_POST_PROCESS_INPUT0), ('DummyB', unreal.SceneTextureId.PPI_SCENE_DEPTH), ('DummyC', unreal.SceneTextureId.PPI_WORLD_NORMAL)):
        st = _e(m, unreal.MaterialExpressionSceneTexture, -700, y); st.set_editor_property('scene_texture_id', sid); y += 120
        MEL.connect_material_expressions(st, 'Color', cu, k)
    MEL.connect_material_property(cu, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    MEL.recompile_material(m); EAL.save_loaded_asset(m)
    st = MEL.get_statistics(m); log('comic instr', st.num_pixel_shader_instructions)
    return m

def apply_comic(on=True):
    m = master_comic()
    mi = _mi('MI_PBX_Comic', m)
    for a in EAS.get_all_level_actors():
        if isinstance(a, unreal.PostProcessVolume):
            s = a.get_editor_property('settings')
            wb = unreal.WeightedBlendables(); wb.set_editor_property('array', [unreal.WeightedBlendable(weight=1.0 if on else 0.0, object=mi)])
            s.set_editor_property('weighted_blendables', wb); a.set_editor_property('settings', s)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    log('comic applied', on)
