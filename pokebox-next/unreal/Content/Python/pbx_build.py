# Pokebox Next — builds the first town in Unreal from the Blender output (PokeboxNext_src): imports textures and meshes,
# creates the materials (PBR surfaces from Poly Haven, foliage from the Quaternius kit, ground blend, water), lays out the
# level from town_plan.json and sets up the lighting (Lumen, sky atmosphere, clouds, fog, post process).
# Re-runnable: every step replaces what it made before. Units: Unreal cm.
import unreal, os, json, math

SRC = r"E:\GAME-APP-DEV\POKEMON\PokeboxNext_src"
KITS = os.path.join(SRC, 'kits')
# full Quaternius Stylized Nature MegaKit (Standard) when present, else the old free subset
NATURE = os.path.join(KITS, 'q_nature') if os.path.isdir(os.path.join(KITS, 'q_nature')) else os.path.join(SRC, 'nature')
# kit folder in Unreal -> FBX folder on disk
KIT_DIRS = {'QProps': os.path.join(KITS, 'q_props', 'Exports', 'FBX'), 'KTown': os.path.join(KITS, 'k_town', 'Models', 'FBX format'),
            'KPirate': os.path.join(KITS, 'k_pirate', 'Models', 'FBX format'), 'KSurvival': os.path.join(KITS, 'k_survival', 'Models', 'FBX format'),
            'KFurniture': os.path.join(KITS, 'k_furniture', 'Models', 'FBX format')}
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
def _fbx_options():
    """static meshes keep their vertex colours (ground masks, mountains)"""
    o = unreal.FbxImportUI()
    o.set_editor_property('import_mesh', True); o.set_editor_property('import_as_skeletal', False); o.set_editor_property('import_materials', False)
    o.set_editor_property('import_textures', False)
    d = o.get_editor_property('static_mesh_import_data')
    d.set_editor_property('vertex_color_import_option', unreal.VertexColorImportOption.REPLACE)
    d.set_editor_property('combine_meshes', True); d.set_editor_property('auto_generate_collision', False)
    return o

def _import(files, dest, fbx_static=False):
    tasks = []
    for f in files:
        t = unreal.AssetImportTask()
        t.set_editor_property('filename', f); t.set_editor_property('destination_path', dest)
        t.set_editor_property('automated', True); t.set_editor_property('replace_existing', True); t.set_editor_property('save', True)
        if fbx_static and f.lower().endswith('.fbx'): t.set_editor_property('options', _fbx_options())
        tasks.append(t)
    AT.import_asset_tasks(tasks)
    out = []
    for t in tasks: out += list(t.get_editor_property('imported_object_paths') or [])
    return out

def import_textures():
    tex = os.path.join(SRC, 'tex'); files = [os.path.join(tex, f) for f in sorted(os.listdir(tex)) if f.endswith('.jpg') and os.path.getsize(os.path.join(tex, f)) > 0]
    files += [os.path.join(tex, f) for f in sorted(os.listdir(tex)) if f.startswith('T_') and f.endswith('.png') and not f.startswith('T_TownSplat')]
    ntex = os.path.join(NATURE, 'Textures'); files += [os.path.join(ntex, f) for f in sorted(os.listdir(ntex)) if f.endswith('.png')]
    paths = _import(files, G + '/Tex')
    for p in EAL.list_assets(G + '/Tex', recursive=False):
        a = EAL.load_asset(p)
        if not isinstance(a, unreal.Texture2D): continue
        n = a.get_name().lower()
        if n.endswith('_nor') or n.endswith('_normal'):
            a.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_NORMALMAP); a.set_editor_property('srgb', False)
            if n.endswith('_nor'): a.set_editor_property('flip_green_channel', True)  # Poly Haven ships OpenGL normals
        elif n.endswith('_arm') or n.startswith('t_townsplat') or n.startswith('t_r1splat'):
            a.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_MASKS); a.set_editor_property('srgb', False)
            if n.startswith('t_townsplat') or n.startswith('t_r1splat'):   # outside the town square the edge texels continue (no repeating paths on the far terrain)
                a.set_editor_property('address_x', unreal.TextureAddress.TA_CLAMP); a.set_editor_property('address_y', unreal.TextureAddress.TA_CLAMP)
        elif n.startswith('t_palette'):   # one texel per colour: no filtering, no mips
            a.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP); a.set_editor_property('srgb', True)
            a.set_editor_property('filter', unreal.TextureFilter.TF_NEAREST); a.set_editor_property('mip_gen_settings', unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
            EAL.save_loaded_asset(a); continue
        elif n.startswith('t_sky'):   # mostly blue -> Unreal guesses "normal map"; force colour
            a.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_DEFAULT); a.set_editor_property('srgb', True)
            a.set_editor_property('max_texture_size', 4096); a.set_editor_property('mip_gen_settings', unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
            EAL.save_loaded_asset(a); continue
        a.set_editor_property('max_texture_size', 2048)
        EAL.save_loaded_asset(a)
    log('textures', len(paths))

def import_meshes(only=None):
    fbx = os.path.join(SRC, 'fbx'); nat = os.path.join(NATURE, 'FBX')
    a = _import([os.path.join(fbx, f) for f in sorted(os.listdir(fbx)) if f.endswith('.fbx') and (only is None or f[:-4] in only)], G + '/Meshes', fbx_static=True)
    if only is not None: log('meshes', len(a)); return
    b = _import([os.path.join(nat, f) for f in sorted(os.listdir(nat)) if f.endswith('.fbx')], G + '/Nature')
    log('meshes', len(a), 'nature', len(b))

def fix_kit_materials():
    """Quaternius Fantasy Props come in as material instances without their trim-sheet textures (white props).
    Re-parent every MI_Trim_* to our PBR master and plug in BaseColor / ORM / (Unreal-convention) Normal."""
    td = os.path.join(KITS, 'q_props', 'Textures'); nd = os.path.join(td, 'Normals-UnrealEngine')
    files = [os.path.join(td, f) for f in os.listdir(td) if f.startswith('T_Trim_') and ('BaseColor' in f or 'ORM' in f)]
    files += [os.path.join(nd, f) for f in os.listdir(nd) if f.endswith('.png')]
    dest = f'{G}/Kits/QProps/Tex'; _import(files, dest)
    for p in EAL.list_assets(dest, recursive=False):
        t = EAL.load_asset(p)
        if not isinstance(t, unreal.Texture2D): continue
        n = t.get_name()
        if n.endswith('_Normal'): t.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_NORMALMAP); t.set_editor_property('srgb', False)
        elif n.endswith('_ORM'): t.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_MASKS); t.set_editor_property('srgb', False)
        t.set_editor_property('max_texture_size', 2048); EAL.save_loaded_asset(t)
    S = unreal.load_asset(f'{G}/Materials/M_PBX_Surface'); n = 0
    for p in EAL.list_assets(f'{G}/Kits/QProps', recursive=False):
        mi = EAL.load_asset(p)
        if not isinstance(mi, unreal.MaterialInstanceConstant) or not mi.get_name().startswith('MI_Trim_'): continue
        kind = mi.get_name()[len('MI_Trim_'):].replace('_Vertex', '')
        MEL.set_material_instance_parent(mi, S)
        for prm, suf in (('BaseTex', 'BaseColor'), ('NormalTex', 'Normal'), ('ArmTex', 'ORM')):
            t = unreal.load_asset(f'{dest}/T_Trim_{kind}_{suf}')
            if t: MEL.set_material_instance_texture_parameter_value(mi, prm, t)
            else: log('qprops missing tex', kind, suf)
        MEL.set_material_instance_scalar_parameter_value(mi, 'UVScale', 1.0)
        MEL.update_material_instance(mi); EAL.save_loaded_asset(mi); n += 1
    log('qprops materials fixed', n)

def import_echoes():
    """paper Echo cut-outs (made from the user's local card images — never in git) + their master material"""
    d = os.path.join(SRC, 'echo'); files = [os.path.join(d, f) for f in sorted(os.listdir(d)) if f.endswith('.png')]
    _import(files, G + '/Echo')
    for p in EAL.list_assets(G + '/Echo', recursive=False):
        t = EAL.load_asset(p)
        if isinstance(t, unreal.Texture2D):
            t.set_editor_property('max_texture_size', 1024); t.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_UI if False else unreal.TextureGroup.TEXTUREGROUP_WORLD)
            EAL.save_loaded_asset(t)
    m = _fresh('M_PBX_Echo', G + '/Materials')
    m.set_editor_property('blend_mode', unreal.BlendMode.BLEND_MASKED); m.set_editor_property('two_sided', True)
    t = _texp(m, 'Tex', -900, 0, default=WHITE)
    MEL.connect_material_property(t, 'RGB', unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(t, 'A', unreal.MaterialProperty.MP_OPACITY_MASK)
    fl = _mul(m, _vec(m, 'FlashColor', (1, 1, 1, 1), -900, 300), _scalar(m, 'Flash', 0.0, -900, 450), -600, 350)
    MEL.connect_material_property(_mul(m, t, fl, -400, 250, 'RGB'), '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    MEL.connect_material_property(_scalar(m, 'Roughness', .85, -600, 100), '', unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.recompile_material(m); EAL.save_loaded_asset(m)
    log('echoes', len(files))

def import_outfits():
    d = os.path.join(SRC, 'outfits'); files = [os.path.join(d, f) for f in sorted(os.listdir(d)) if f.startswith('T_Outfit_') and f.endswith('.png')]
    _import(files, G + '/Characters/Outfits'); log('outfits', len(files))
    for p in EAL.list_assets(G + '/Characters/Outfits', recursive=False):   # bluish outfits get mistaken for normal maps
        t = EAL.load_asset(p)
        if isinstance(t, unreal.Texture2D):
            t.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_DEFAULT); t.set_editor_property('srgb', True); EAL.save_loaded_asset(t)

def import_clothes():
    d = os.path.join(SRC, 'clothes'); files = [os.path.join(d, f) for f in sorted(os.listdir(d)) if f.startswith('SK_Cloth_') and f.endswith('.gltf')]
    got = _import(files, G + '/Characters/Clothes'); log('clothes', len(files), len(got))
    pals = [os.path.join(d, f) for f in sorted(os.listdir(d)) if f.startswith('T_ClothPal_') and f.endswith('.png')]
    _import(pals, G + '/Characters/Clothes/Pal')
    for p in EAL.list_assets(G + '/Characters/Clothes/Pal', recursive=False):
        t = EAL.load_asset(p)
        if isinstance(t, unreal.Texture2D):
            t.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP); t.set_editor_property('srgb', True)
            t.set_editor_property('filter', unreal.TextureFilter.TF_NEAREST); t.set_editor_property('mip_gen_settings', unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
            EAL.save_loaded_asset(t)
    log('clothes palettes', len(pals))

def import_hair():
    d = os.path.join(KITS, 'q_chars', 'Universal Base Characters[Standard]', 'Hairstyles', 'Rigged to Head Bone', 'glTF (Godot -Unreal)')
    files = [os.path.join(d, f) for f in sorted(os.listdir(d)) if f.endswith('.gltf')]
    got = _import(files, G + '/Characters/Hair'); log('hair', len(files), len(got))

def fix_usage_flags():
    """materials used on Nanite meshes need the usage flag, else a cooked / -game run shows the default material"""
    for p in ('/Game/Shader_Water/MM_Water', '/Game/PBX/Materials/M_PBX_Echo'):
        m = unreal.load_asset(p)
        if not m: continue
        try: m.set_editor_property('used_with_nanite', True); MEL.recompile_material(m); EAL.save_loaded_asset(m); log('nanite flag', p)
        except Exception as ex: log('flag', p, ex)

def link_skeletons():
    """UAL animations play on the Quaternius characters through skeleton remapping (same bone names)"""
    sks = [EAL.load_asset(p) for p in EAL.list_assets(G + '/Characters', recursive=True) if str(EAL.find_asset_data(p).asset_class_path.asset_name) == 'Skeleton']
    # Fab: the stylized boy (UE5-mannequin bone names) and the Free Animations Pack 2 mannequin
    for extra in ('/Game/Fab/Free_Stylized_Boy_Character/boy1_Skeleton', '/Game/FreeAnimationsPack2/Demo/Mannequins/Meshes/SK_Mannequin'):
        if EAL.does_asset_exist(extra): sks.append(EAL.load_asset(extra))
    for s in sks:
        others = [o for o in sks if o != s]
        try:
            s.set_editor_property('compatible_skeletons', [o for o in others]); EAL.save_loaded_asset(s)
        except Exception as ex: log('compat', s.get_name(), ex)
    log('skeletons', [s.get_path_name() for s in sks])

def import_kits(only=None):
    """Quaternius Fantasy Props + Kenney kits, each into /Game/PBX/Kits/<name> with the materials the FBX brings"""
    for k, d in KIT_DIRS.items():
        if only and k not in only: continue
        if not os.path.isdir(d): log('kit missing', k, d); continue
        got = _import([os.path.join(d, f) for f in sorted(os.listdir(d)) if f.lower().endswith('.fbx')], f'{G}/Kits/{k}')
        log('kit', k, len(got))

# ------------------------------------------------------------------ materials
def _fresh(name, path, cls=unreal.Material, factory=None):
    full = f'{path}/{name}'
    if EAL.does_asset_exist(full): EAL.delete_asset(full)
    m = AT.create_asset(name, path, cls, factory or unreal.MaterialFactoryNew())
    try: m.set_editor_property('used_with_nanite', True)   # imported meshes are Nanite: without the flag a packaged/-game run shows the default material
    except Exception as ex: log('nanite flag', ex)
    return m

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

def master_ground(name='M_PBX_Ground', size=22000.0, center=(0.0, 0.0)):
    m = _fresh(name, G + '/Materials')
    uv = _e(m, unreal.MaterialExpressionTextureCoordinate, -2200, 0)
    # layer mask from the level's splat texture, sampled by world XY (a `size` cm square around `center`, Unreal cm)
    wp = _e(m, unreal.MaterialExpressionWorldPosition, -1800, -1100); cm = _e(m, unreal.MaterialExpressionComponentMask, -1600, -1100)
    cm.set_editor_property('r', True); cm.set_editor_property('g', True); MEL.connect_material_expressions(wp, '', cm, '')
    if center != (0.0, 0.0):
        c2 = _e(m, unreal.MaterialExpressionConstant2Vector, -1600, -1250); c2.set_editor_property('r', center[0]); c2.set_editor_property('g', center[1])
        sb = _e(m, unreal.MaterialExpressionSubtract, -1400, -1150); MEL.connect_material_expressions(cm, '', sb, 'A'); MEL.connect_material_expressions(c2, '', sb, 'B')
        cm = sb
    dv = _e(m, unreal.MaterialExpressionDivide, -1200, -1100); dv.set_editor_property('const_b', size); MEL.connect_material_expressions(cm, '', dv, 'A')
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
    tint = _vec(m, 'GrassTint', (1, 1, 1, 1), -1500, -700)
    grass_tinted = _mul(m, layers[0][0], tint, -1400, -500, 'RGB')   # tint the grass only (sand / dirt / stone keep their colour)
    sand_tinted = _mul(m, layers[2][0], _vec(m, 'SandTint', (1, 1, 1, 1), -1500, -900), -1400, -800, 'RGB')  # the Poly Haven sand is dark & wet-looking
    for k, (ch, idx) in {'base': ('RGB', 0), 'nor': ('RGB', 1), 'rough': ('G', 2)}.items():
        g0, g0o = (grass_tinted, '') if k == 'base' else (layers[0][idx], ch)
        l1 = lerp(g0, g0o, layers[1][idx], ch, 'R', -1200, idx * 400)
        l2 = lerp(l1, '', *((sand_tinted, '') if k == 'base' else (layers[2][idx], ch)), 'G', -1000, idx * 400)
        l3 = lerp(l2, '', layers[3][idx], ch, 'B', -800, idx * 400)
        out[k] = l3
    MEL.connect_material_property(out['base'], '', unreal.MaterialProperty.MP_BASE_COLOR)
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

def master_vertex():
    """vertex-colour surfaces (mountains, far terrain): colour comes from the mesh"""
    m = _fresh('M_PBX_Vertex', G + '/Materials')
    vc = _e(m, unreal.MaterialExpressionVertexColor, -800, -200)
    MEL.connect_material_property(_mul(m, vc, _vec(m, 'Tint', (1, 1, 1, 1), -800, 0), -500, -100, 'RGB'), '', unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(_scalar(m, 'Roughness', .92, -500, 150), '', unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.recompile_material(m); EAL.save_loaded_asset(m); return m

def master_cloth():
    """3D clothes (tools/clothes.py): vertex colour, two-sided (open sleeves / skirts are single shells)"""
    m = _fresh('M_PBX_Cloth', G + '/Materials'); m.set_editor_property('two_sided', True)
    try: m.set_editor_property('used_with_skeletal_mesh', True)
    except Exception as ex: log('cloth flag', ex)
    t = _texp(m, 'Pal', -800, -200, default=WHITE)          # per-role palette (tools/clothes.py), UVs point into its cells
    MEL.connect_material_property(t, 'RGB', unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(_scalar(m, 'Roughness', .85, -500, 150), '', unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.recompile_material(m); EAL.save_loaded_asset(m); return m

def master_sky():
    """the baked stylized sky (Samples/Sky_World.blend #3) on an inside-out dome: unlit, flagged as sky so the
    real-time sky light captures it"""
    m = _fresh('M_PBX_Sky', G + '/Materials')
    m.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT); m.set_editor_property('two_sided', True)
    for k in ('is_sky',):
        try: m.set_editor_property(k, True)
        except Exception as ex: log('sky flag', k, ex)
    t = _texp(m, 'SkyTex', -900, 0, default=WHITE)
    MEL.connect_material_property(_mul(m, t, _scalar(m, 'Intensity', 1.0, -900, 250), -500, 50, 'RGB'), '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    MEL.recompile_material(m); EAL.save_loaded_asset(m); return m

def master_fx():
    """glowing particle sprites (C++ APBXFX): additive, unlit, colour + alpha from the instance's custom data"""
    m = _fresh('M_PBX_FX', G + '/Materials')
    m.set_editor_property('blend_mode', unreal.BlendMode.BLEND_ADDITIVE); m.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property('two_sided', True)
    for k in ('used_with_instanced_static_meshes',):
        try: m.set_editor_property(k, True)
        except Exception as ex: log('fx flag', k, ex)
    t = _texp(m, 'Tex', -1100, 0, default=WHITE)
    cd = []
    for i in range(4):
        e = _e(m, unreal.MaterialExpressionPerInstanceCustomData, -1100, 300 + i * 120); e.set_editor_property('data_index', i); cd.append(e)
    rg = _e(m, unreal.MaterialExpressionAppendVector, -850, 330); MEL.connect_material_expressions(cd[0], '', rg, 'A'); MEL.connect_material_expressions(cd[1], '', rg, 'B')
    rgb = _e(m, unreal.MaterialExpressionAppendVector, -700, 360); MEL.connect_material_expressions(rg, '', rgb, 'A'); MEL.connect_material_expressions(cd[2], '', rgb, 'B')
    a = _mul(m, t, cd[3], -850, 100, 'R')
    c = _mul(m, rgb, a, -550, 200)
    MEL.connect_material_property(_mul(m, c, _scalar(m, 'Intensity', 6.0, -550, 400), -350, 250), '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    MEL.recompile_material(m); EAL.save_loaded_asset(m)
    _mi('MI_FX_Dot', m, {'Intensity': 6.0}, {}, {'Tex': 'T_FX_Dot'}); _mi('MI_FX_Star', m, {'Intensity': 7.0}, {}, {'Tex': 'T_FX_Star'})
    return m

def _mi(name, parent, scalars=None, vectors=None, textures=None):
    path = G + '/Materials/Inst'; full = f'{path}/{name}'
    if EAL.does_asset_exist(full): EAL.delete_asset(full)
    mi = AT.create_asset(name, path, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, parent)
    for k, v in (scalars or {}).items(): MEL.set_material_instance_scalar_parameter_value(mi, k, v)
    for k, v in (vectors or {}).items(): MEL.set_material_instance_vector_parameter_value(mi, k, unreal.LinearColor(*v))
    for k, v in (textures or {}).items():
        t = unreal.load_asset(v if v.startswith('/Game/') else f'{G}/Tex/{v}')
        if t: MEL.set_material_instance_texture_parameter_value(mi, k, t)
        else: log('missing texture', v)
    MEL.update_material_instance(mi); EAL.save_loaded_asset(mi); return mi

def _ph(base): return {'BaseTex': base + '_diff', 'NormalTex': base + '_nor', 'ArmTex': base + '_arm'}

def make_materials():
    S, C, F, Gm, W = master_surface(), master_color(), master_foliage(), master_ground(), master_water()
    M = {}
    # building surfaces (Blender box UVs: 1 UV = 1 m)
    # Wolf-Among-Us look: walls and roofs are flat painted colour (the modelled boards and tiles give the detail, the ink pass draws it)
    # siding and roof tiles are painted greyscale textures (boards, lap shadows and ink lines drawn in), tinted per house
    sid = {'BaseTex': 'T_Siding_diff', 'NormalTex': 'T_Siding_nor'}; roof = {'BaseTex': 'T_Roof_diff'}
    M['M_Siding_White'] = _mi('MI_Siding_White', S, {'UVScale': 1.0, 'RoughMul': .75}, {'Tint': (.88, .9, .92, 1)}, sid)
    M['M_Siding_Cream'] = _mi('MI_Siding_Cream', S, {'UVScale': 1.0, 'RoughMul': .75}, {'Tint': (.95, .8, .58, 1)}, sid)
    M['M_Plaster'] = _mi('MI_Plaster', C, {'Roughness': .8}, {'Color': (.7, .7, .68, 1)})
    M['M_Wallpaper_Home'] = _mi('MI_Wallpaper_Home', S, {'UVScale': 1.0, 'RoughMul': .8}, {'Tint': (.95, .82, .62, 1)}, sid)
    M['M_Wallpaper_Lab'] = _mi('MI_Wallpaper_Lab', C, {'Roughness': .6}, {'Color': (.78, .84, .88, 1)})
    M['M_WindowLight'] = _mi('MI_WindowLight', C, {'Roughness': .3, 'EmissiveMul': 6.0}, {'Color': (.9, .95, 1, 1), 'Emissive': (.85, .93, 1.0, 1)})
    M['M_Roof_Red'] = _mi('MI_Roof_Red', S, {'UVScale': 1.0, 'RoughMul': .7}, {'Tint': (.72, .2, .14, 1)}, roof)
    M['M_Roof_Blue'] = _mi('MI_Roof_Blue', S, {'UVScale': 1.0, 'RoughMul': .7}, {'Tint': (.2, .34, .62, 1)}, roof)
    M['M_Stone'] = _mi('MI_Stone', S, {'UVScale': .6}, {}, _ph('rustic_stone_wall'))
    M['M_Brick'] = _mi('MI_Brick', S, {'UVScale': .8}, {}, _ph('red_brick'))
    M['M_WoodBox'] = _mi('MI_WoodBox', S, {'UVScale': 1.0}, {'Tint': (.85, .7, .55, 1)}, _ph('brown_planks_05'))
    M['M_WoodDark'] = _mi('MI_WoodDark', S, {'UVScale': 1.0}, {'Tint': (.55, .42, .32, 1)}, _ph('brown_planks_05'))
    M['M_WoodLight'] = _mi('MI_WoodLight', S, {'UVScale': 1.0}, {'Tint': (1.05, .95, .8, 1)}, _ph('oak_wood_planks'))
    M['M_Floor'] = _mi('MI_Floor', S, {'UVScale': .5, 'RoughMul': .45}, {}, _ph('old_wood_floor'))
    for k, col, r, met in [('M_Trim', (.92, .92, .9, 1), .5, 0), ('M_Glass', (.04, .07, .1, 1), .04, 0), ('M_Door', (.18, .3, .55, 1), .45, 0),
                           ('M_Metal', (.5, .52, .55, 1), .55, .3), ('M_Iron', (.06, .06, .07, 1), .45, 1), ('M_MailBlue', (.1, .28, .65, 1), .4, 0),
                           ('M_Red', (.8, .08, .06, 1), .4, 0), ('M_BinGreen', (.12, .3, .16, 1), .5, 0)]:
        M[k] = _mi('MI_' + k[2:], C, {'Roughness': r, 'Metallic': met}, {'Color': col})
    M['M_LampGlass'] = _mi('MI_LampGlass', C, {'Roughness': .2, 'EmissiveMul': 4.0}, {'Color': (1, .9, .7, 1), 'Emissive': (1, .78, .45, 1)})
    # ground: stylized grass + dirt from the Stylized Nature pack (painted), Poly Haven sand + flagstones
    M['M_Ground'] = _mi('MI_Ground', Gm, {'GrassUV': 1.2}, {'GrassTint': (1.0, 1.0, 1.0, 1), 'SandTint': (1.55, 1.35, 1.0, 1)}, {'Splat': 'T_TownSplat',
                        'GrassBase': '/Game/Stylized_PBR_Nature/Terrain/T_Grass_1', 'DirtBase': 'park_dirt_diff', 'DirtNor': 'park_dirt_nor', 'DirtArm': 'park_dirt_arm', 'SandBase': 'coast_sand_01_diff', 'SandNor': 'coast_sand_01_nor',
                        'SandArm': 'coast_sand_01_arm', 'StoneBase': 'grey_stone_path_diff', 'StoneNor': 'grey_stone_path_nor', 'StoneArm': 'grey_stone_path_arm'})
    # Route 1 (tools/blender_route1.py): same layers, its own splat (460 m square centred on Blender (-160, 0) = UE (-16000, 0))
    G1 = master_ground('M_PBX_GroundR1', 46000.0, (-16000.0, 0.0))
    M['M_GroundR1'] = _mi('MI_GroundR1', G1, {'GrassUV': 1.2}, {'GrassTint': (1.0, 1.0, 1.0, 1), 'SandTint': (1.55, 1.35, 1.0, 1)}, {'Splat': 'T_R1Splat',
                          'GrassBase': '/Game/Stylized_PBR_Nature/Terrain/T_Grass_1', 'DirtBase': 'park_dirt_diff', 'DirtNor': 'park_dirt_nor', 'DirtArm': 'park_dirt_arm',
                          'StoneBase': 'grey_stone_path_diff', 'StoneNor': 'grey_stone_path_nor', 'StoneArm': 'grey_stone_path_arm'})
    tw = unreal.load_asset('/Game/Shader_Water/MI_Water')          # Samples/TestWater stylized water
    M['M_Water'] = tw if tw else _mi('MI_Water', W)
    V = master_vertex(); master_cloth(); SK = master_sky()
    M['M_Mountain'] = _mi('MI_Mountain', S, {'UVScale': 1.0, 'RoughMul': .95}, {}, {'BaseTex': 'T_Palette_Mountain'})
    M['M_Sky'] = _mi('MI_Sky', SK, {'Intensity': 1.0}, {}, {'SkyTex': 'T_Sky_Day'})
    for k, col, r, met in [('M_TrainRed', (.72, .1, .08, 1), .45, 0), ('M_TrainGreen', (.12, .36, .24, 1), .5, 0), ('M_TrainCream', (.93, .86, .7, 1), .55, 0),
                           ('M_Brass', (.85, .62, .25, 1), .35, .8), ('M_EdgeYellow', (.95, .78, .1, 1), .6, 0), ('M_Gravel', (.42, .4, .38, 1), .95, 0),
                           ('M_TunnelDark', (0, 0, 0, 1), 1.0, 0)]:
        M[k] = _mi('MI_' + k[2:], C, {'Roughness': r, 'Metallic': met}, {'Color': col})
    M['M_CliffRock'] = _mi('MI_CliffRock', S, {'UVScale': .25, 'RoughMul': .9}, {'Tint': (1.15, 1.05, .95, 1)}, {'BaseTex': '/Game/Stylized_PBR_Nature/Rocks/Textures/T_S_Rocks_1-6_D'})
    M['M_Roof_Green'] = _mi('MI_Roof_Green', S, {'UVScale': 1.0, 'RoughMul': .7}, {'Tint': (.24, .48, .3, 1)}, {'BaseTex': 'T_Roof_diff'})
    # nature kit (Quaternius): slot names in the FBX → our instances
    M['Leaves_NormalTree'] = _mi('MI_Leaves_Tree', F, {}, {'Tint': (1.0, 1.08, .9, 1)}, {'Tex': 'Leaves_NormalTree_C'})
    M['Leaves_Pine'] = _mi('MI_Leaves_Pine', F, {}, {}, {'Tex': 'Leaf_Pine_C'})
    # the kit's twisted-tree / bush leaves are autumn red; this coastal town is summer green -> reuse the green blob atlas
    M['Leaves_TwistedTree'] = _mi('MI_Leaves_Twisted', F, {}, {'Tint': (.95, 1.08, .85, 1)}, {'Tex': 'Leaves_GiantPine_C'})
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
KIT_SCALE = {}
# plant-like meshes: no collision, foliage stencil (soft ink). Matched against the mesh's base name.
NO_COLLIDE = ('Grass', 'Flower', 'Clover', 'Fern', 'Plant', 'Petal', 'Pebble', 'Mushroom', 'SM_Fol_Grass', 'SM_Fol_Flower', 'SM_SmallFlower', 'SM_Bush', 'SM_Fol_Bush')
FOLIAGE_INK = NO_COLLIDE + ('CommonTree', 'Pine', 'TwistedTree', 'DeadTree', 'Bush', 'SM_Tree', 'SM_Common_Tree', 'SM_Pine')
TREES = ('SM_Tree', 'SM_Common_Tree', 'SM_Pine', 'CommonTree', 'Pine_')
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

def _base(name): return name.split('/')[-1]

def _mesh(name):
    if name.startswith('/Game/'):   # Fab pack asset, full path
        return unreal.load_asset(name) if EAL.does_asset_exist(name) else None
    if '/' in name:   # kit mesh; Kenney keeps the hyphens of its file names, the plan uses underscores
        for cand in (name, name.split('/')[0] + '/' + name.split('/')[1].replace('_', '-')):
            p = f'{G}/Kits/{cand}'
            if EAL.does_asset_exist(p): return unreal.load_asset(p)
        return None
    for f in ('Meshes', 'Nature'):
        p = f'{G}/{f}/{name}'
        if EAL.does_asset_exist(p): return unreal.load_asset(p)
    return None

def _spawn_cls(cls, loc=(0, 0, 0), rot=(0, 0, 0), label=None):
    a = EAS.spawn_actor_from_class(cls, unreal.Vector(*loc), unreal.Rotator(*rot))
    if label: a.set_actor_label(label)
    return a

def _world(): return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()

def _ground_z(world, x, y):
    """height of the terrain (town ground / far terrain / mountains — the only things spawned when this runs) at UE x, y"""
    h = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, 60000.0), unreal.Vector(x, y, -60000.0), unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,
                                               True, [], unreal.DrawDebugTrace.NONE, True)
    if not h: return None
    t = h.to_tuple()
    for v in t[4:7]:
        if isinstance(v, unreal.Vector): return v.z
    return None

def _snap_z(world, sm, o, scale):
    """lowest terrain point under the footprint (centre + 4 points at 70 % of the extents, rotated) -> no floating edge;
    meshes whose bottom sits above their pivot (flower heads etc.) are lowered so the bottom touches."""
    b = sm.get_bounding_box(); mn, mx = b.min, b.max
    x, y = o['x'] * 100, -o['y'] * 100
    name = _base(o['mesh'])
    if name.startswith(TREES): r = (40.0, 40.0)
    else: r = (min(400.0, (mx.x - mn.x) * .35 * scale), min(400.0, (mx.y - mn.y) * .35 * scale))
    yaw = math.radians(-o['rot']); c, s_ = math.cos(yaw), math.sin(yaw)
    cx, cy = (mx.x + mn.x) / 2 * scale, (mx.y + mn.y) / 2 * scale
    pts = [(0, 0), (r[0], r[1]), (-r[0], r[1]), (r[0], -r[1]), (-r[0], -r[1])]
    zs = []
    for (px, py) in pts:
        lx, ly = cx + px, cy + py
        z = _ground_z(world, x + lx * c - ly * s_, y + lx * s_ + ly * c)
        if z is not None: zs.append(z)
    if not zs: return None
    z = min(zs) - 3.0
    if mn.z > 0: z -= mn.z * scale
    return z

def build_level(map_name='L_Town', plan_file='town_plan.json'):
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    path = G + '/Maps/' + map_name
    if EAL.does_asset_exist(path): les.load_level(path)
    else: les.new_level(path)
    world = _world()
    gm_cls = None
    try: gm_cls = world.get_world_settings().get_editor_property('default_game_mode')
    except Exception as ex: log('read game mode', ex)
    for a in EAS.get_all_level_actors(): EAS.destroy_actor(a)
    plan = json.load(open(os.path.join(SRC, plan_file), encoding='utf-8'))
    # ---- light & sky: warm late-morning sun, the baked stylized sky dome (no physical atmosphere / volumetric clouds)
    sun = _spawn_cls(unreal.DirectionalLight, (0, 0, 1000), (0, -38, 35), 'Sun')
    lc = sun.get_component_by_class(unreal.DirectionalLightComponent)
    sp(lc, intensity=8.0, light_color=unreal.Color(r=255, g=244, b=228, a=255), mobility=unreal.ComponentMobility.MOVABLE, light_source_angle=1.2)
    sky = _spawn_cls(unreal.SkyLight, (0, 0, 800), label='SkyLight'); sc = sky.get_component_by_class(unreal.SkyLightComponent)
    # captures the sky dome only (everything nearer than 1.5 km is ignored) -> soft blue ambient + sky reflections
    sp(sc, mobility=unreal.ComponentMobility.MOVABLE, real_time_capture=False, source_type=unreal.SkyLightSourceType.SLS_CAPTURED_SCENE,
       sky_distance_threshold=150000.0, intensity=1.4, lower_hemisphere_is_black=False)
    fog = _spawn_cls(unreal.ExponentialHeightFog, (0, 0, -200), label='Fog'); fc = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
    # haze softens the mountains; the sky dome (100 km away) is beyond the fog cutoff so it keeps its colours
    sp(fc, fog_density=.012, fog_height_falloff=.12, start_distance=4000.0, fog_cutoff_distance=4.0e6,
       fog_inscattering_luminance=unreal.LinearColor(.62, .74, .92, 1.0), volumetric_fog=False)
    pp = _spawn_cls(unreal.PostProcessVolume, label='PostProcess'); pp.set_editor_property('unbound', True)
    s = pp.get_editor_property('settings')
    for k, v in [('auto_exposure_bias', .2), ('bloom_intensity', .45), ('ambient_occlusion_intensity', .6),
                 ('ambient_occlusion_radius', 120.0), ('motion_blur_amount', 0.0), ('vignette_intensity', .22), ('color_saturation', unreal.Vector4(1.08, 1.08, 1.08, 1)),
                 ('color_contrast', unreal.Vector4(1.05, 1.05, 1.05, 1)), ('white_temp', 6200.0), ('sharpen', .3),
                 ('auto_exposure_speed_up', 5.0), ('auto_exposure_speed_down', 5.0)]:   # doors / teleports: adapt fast
        try: s.set_editor_property('override_' + k, True); s.set_editor_property(k, v)
        except Exception as ex: log('pp', k, ex)
    pp.set_editor_property('settings', s)
    missing = set()
    def classify(a, mesh):
        c = a.get_component_by_class(unreal.StaticMeshComponent); n = _base(mesh)
        if n.startswith(NO_COLLIDE): c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        if n.startswith(FOLIAGE_INK):
            # stencil 1 = foliage: the comic pass draws only soft silhouette ink here (no normal-crease scribble)
            c.set_editor_property('render_custom_depth', True); c.set_editor_property('custom_depth_stencil_value', 1)
        return c
    def put(mesh, x, y, z, rot=0.0, scale=1.0, label=None, h=None, w=None, z_cm=None):
        sm = _mesh(mesh)
        if not sm:
            if mesh not in missing: log('missing mesh', mesh); missing.add(mesh)
            return None
        if h or w:   # kits come in different units: scale from the mesh bounds to the wanted size in metres
            b = sm.get_bounding_box(); e = b.max - b.min
            size = e.z if h else max(e.x, e.y)
            scale = ((h or w) * 100.0) / max(size, 1e-3)
        a = EAS.spawn_actor_from_object(sm, unreal.Vector(x * 100, -y * 100, z * 100 if z_cm is None else z_cm), unreal.Rotator(0, 0, -rot))
        a.set_actor_scale3d(unreal.Vector(scale, scale, scale))
        if label: a.set_actor_label(label)
        classify(a, mesh)
        a.set_folder_path('Town/' + ('Nature' if mesh.startswith('/Game/') or not (mesh.startswith('SM_') or '/' in mesh) else 'Built'))
        return a
    def obj_scale(o, sm):
        if o.get('h') or o.get('w'):
            b = sm.get_bounding_box(); e = b.max - b.min
            return ((o.get('h') or o.get('w')) * 100.0) / max(e.z if o.get('h') else max(e.x, e.y), 1e-3)
        return o['s'] * KIT_SCALE.get(o['mesh'], 1.0)
    # ---- terrain first (the snapping traces must only see terrain)
    for k, tm in enumerate(plan.get('terrain', ['SM_Ground', 'SM_GroundFar', 'SM_Mountains'])): put(tm, 0, 0, 0, label=tm.replace('SM_', ''))
    dome = put('SM_SkyDome', 0, 0, 0, 0.0, 100000.0, label='SkyDome')
    if dome:
        c = dome.get_component_by_class(unreal.StaticMeshComponent); c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        sp(c, cast_shadow=False)
    snaps = {}; n_snap = 0
    for i, o in enumerate(plan['objects']):
        if not o.get('snap'): continue
        sm = _mesh(o['mesh'])
        if not sm: continue
        z = _snap_z(world, sm, o, obj_scale(o, sm))
        if z is not None: snaps[i] = z; n_snap += 1
    log('snapped to terrain', n_snap)
    w = plan.get('water')
    if w: put('SM_Water', w['x'], w['y'], w['z'], label='Sea')
    for i, o in enumerate(plan['objects']):
        a = put(o['mesh'], o['x'], o['y'], o['z'], o['rot'], o['s'] * KIT_SCALE.get(o['mesh'], 1.0), h=o.get('h'), w=o.get('w'), z_cm=snaps.get(i))
        if a and o.get('tag'): a.tags = [unreal.Name(o['tag'])]
    # interiors: warm ceiling lights + a cool 'window daylight' fill
    for r in plan.get('rooms', []):
        cx, cy, cz = r['c']; W, D, H = r['W'], r['D'], r['H']
        n = 2 if W > 1200 else 1
        for i in range(n):
            x = cx + (i - (n - 1) / 2) * W / 2
            pl = _spawn_cls(unreal.PointLight, (x, cy, cz + H - 40), (0, 0, 0), 'RoomLight')
            c = pl.get_component_by_class(unreal.PointLightComponent)
            sp(c, intensity=9000.0, attenuation_radius=max(W, D) * 1.1, light_color=unreal.Color(r=255, g=226, b=190, a=255), source_radius=20.0)
            pl.set_folder_path('Interiors')
        rl = _spawn_cls(unreal.RectLight, (cx, cy + D / 2 - 60, cz + H * .55), (0, -15, -90), 'WindowFill')   # from the window wall side
        c = rl.get_component_by_class(unreal.RectLightComponent)
        sp(c, intensity=1800.0, attenuation_radius=max(W, D) * 1.5, light_color=unreal.Color(r=200, g=220, b=255, a=255), source_width=W * .8, source_height=H * .6)
        rl.set_folder_path('Interiors')
    ps = plan['player_start']
    _spawn_cls(unreal.PlayerStart, (ps['x'] * 100, -ps['y'] * 100, ps['z'] * 100 + 100), (0, 0, -ps['rot']), 'PlayerStart')
    # game mode: keep whatever the map had (the C++ APBXGameMode), else our class
    try:
        if not gm_cls: gm_cls = unreal.load_class(None, '/Script/PokeboxNext.PBXGameMode')
        world.get_world_settings().set_editor_property('default_game_mode', gm_cls)
    except Exception as ex: log('game mode', ex)
    try: sc.recapture_sky()
    except Exception as ex: log('recapture', ex)
    les.save_current_level()
    log('level built', len(plan['objects']), 'objects', 'missing', sorted(missing))

ROUTE1_MESHES = ['SM_R1_Ground', 'SM_R1_Mountains', 'SM_R1_Hut', 'SM_R1_GateEast', 'SM_R1_GateWest', 'SM_ItemBall']

def route1_steps():
    """Route 1 level (after tools/blender_route1.py ran in Blender). Rebuilds the materials (they are shared), then lays out L_Route1."""
    import_textures(); import_meshes(only=ROUTE1_MESHES); M = make_materials(); assign_materials(M)
    # make_materials recreates the masters: re-parent the kit instances, rebuild FX + Echo masters (and import the new Echo cut-outs)
    fix_kit_materials(); master_fx(); import_echoes(); import_outfits(); import_clothes(); fix_usage_flags()
    build_level('L_Route1', 'route1_plan.json')

def all_steps():
    import_textures(); import_meshes(); M = make_materials(); assign_materials(M); build_level()

# ------------------------------------------------------------------ "graphic novel" look (The Wolf Among Us style) — v2
# Runs BEFORE DOF / TSR (HDR scene colour), so the temporal upscaler anti-aliases the ink instead of shredding it.
#  * Light is banded, not colour: light = sceneColour / baseColour (G-buffer), quantised to shadow / mid / lit steps and
#    multiplied back, so albedo detail (painted boards, roof tiles) survives and hues don't shift.
#  * Shadows take a cool violet tint (the WAU palette), lit areas stay warm and clean. No global saturation boost.
#  * Ink: inverse-depth Laplacian (flat ground/walls give zero even at grazing angles, silhouettes give big values) +
#    normal creases, both sampled InkPx screen pixels away; fades with distance. Foliage (custom stencil 1) gets only a
#    soft silhouette, no crease scribble. The sky (huge depth) is left untouched.
COMIC_HLSL = r"""
float2 uv = GetDefaultSceneTextureUV(Parameters, 14);
float2 px = View.BufferSizeAndInvSize.zw * InkPx;
float3 c = SceneTextureLookup(uv, 14, false).rgb;
float d = SceneTextureLookup(uv, 1, false).r;
if (d > SkyDepth) return c;
float3 base = SceneTextureLookup(uv, BASE_ID, false).rgb;
float3 n = normalize(SceneTextureLookup(uv, 8, false).rgb);
float stencil = SceneTextureLookup(uv, STENCIL_ID, false).r;
float cdep = SceneTextureLookup(uv, CDEPTH_ID, false).r;
// custom depth/stencil is drawn without occlusion: only trust it where the foliage is the visible surface
bool leafy = abs(stencil - 1.0) < 0.5 && abs(cdep - d) < max(d * 0.02, 5.0);
// ---------- banded light
float3 W3 = float3(0.2126, 0.7152, 0.0722);
// light = colour / albedo, averaged over a small cross so GI noise doesn't break the bands into blotches
float2 q = View.BufferSizeAndInvSize.zw * 2.0;
float2 t5[4] = { float2(q.x, 0), float2(-q.x, 0), float2(0, q.y), float2(0, -q.y) };
float sc = dot(c, W3), sb = dot(base, W3);
for (int k = 0; k < 4; k++) {
    sc += dot(SceneTextureLookup(uv + t5[k], 14, false).rgb, W3);
    sb += dot(SceneTextureLookup(uv + t5[k], BASE_ID, false).rgb, W3);
}
float Lx = sc / max(sb, 0.2) * Exp;               // exposed light intensity hitting the surface
float Lp0 = dot(c, W3) / max(dot(base, W3), 0.04) * Exp;
if (Debug > 3.5) {                                          // debug 4: false-colour light level (red<.125<orange<.25<yellow<.5<green<1<cyan<2<blue<4<magenta)
    float lv = clamp(floor(log2(max(Lx, 1e-4)) + 4.0), 0.0, 6.0);
    float3 pal[7] = { float3(1,0,0), float3(1,.5,0), float3(1,1,0), float3(0,1,0), float3(0,1,1), float3(0,0,1), float3(1,0,1) };
    return pal[(int)lv] * 0.5 / max(Exp, 1e-4);
}
if (Debug > 2.5) return base / max(Exp, 1e-4);              // debug 3: G-buffer base colour
if (Debug > 1.5) return (Lp0 / 4.0).xxx / max(Exp, 1e-4);   // debug 2: per-pixel light level / 4
if (Debug > 0.5) return (Lx / 4.0).xxx / max(Exp, 1e-4);   // debug 1: smoothed light level / 4 as grey
float s1 = smoothstep(T1 - Soft, T1 + Soft, Lx);  // out of shadow
float s2 = smoothstep(T2 - Soft, T2 + Soft, Lx);  // into full light
float Lq = lerp(lerp(ShadowLvl, MidLvl, s1), LitLvl, s2);
float keep = smoothstep(HiCut, HiCut * 1.6, Lx);  // lamps, emissive, speculars: leave alone
float amt = CelAmt * (1.0 - keep) * (leafy ? 0.6 : 1.0);
float Lf = Lq;
float Lp = dot(c, W3) / max(dot(base, W3), 0.04) * Exp;   // this pixel's own light, for the ratio
float3 col = c * (lerp(Lp, Lf, amt) / max(Lp, 1e-4));
col *= lerp(ShadowTint, float3(1, 1, 1), lerp(1.0, s1, amt));
float g = dot(col, W3); col = lerp(g.xxx, col, Sat);
// ---------- ink
float iz = 1.0 / max(d, 1.0);
float zl = 1.0 / max(SceneTextureLookup(uv - float2(px.x, 0), 1, false).r, 1.0);
float zr = 1.0 / max(SceneTextureLookup(uv + float2(px.x, 0), 1, false).r, 1.0);
float zu = 1.0 / max(SceneTextureLookup(uv - float2(0, px.y), 1, false).r, 1.0);
float zd = 1.0 / max(SceneTextureLookup(uv + float2(0, px.y), 1, false).r, 1.0);
float lap = (abs(zl + zr - 2.0 * iz) + abs(zu + zd - 2.0 * iz)) / iz;
float de = saturate((lap - DepthT) * DepthK);
float ne = 0.0;
if (!leafy) {
    float2 o[4] = { float2(px.x, 0), float2(-px.x, 0), float2(0, px.y), float2(0, -px.y) };
    for (int i = 0; i < 4; i++) {
        float3 ni = normalize(SceneTextureLookup(uv + o[i], 8, false).rgb);
        ne = max(ne, 1.0 - dot(ni, n));
    }
    ne = saturate((ne - NormT) * NormK);
}
float fade = 1.0 - smoothstep(FadeNear, FadeFar, d);
float edge = max(de * (leafy ? 0.55 : 1.0), ne) * fade * InkAmt;
col = lerp(col, Ink / max(Exp, 1e-4), edge);
return col + (DA.rgb + DB.rrr + DC.rgb + DD.rgb + DE.rrr + DF.rrr) * 0.0;
"""

COMIC_PARAMS = [('InkPx', 1.6), ('SkyDepth', 5.0e6), ('T1', .25), ('T2', .26), ('Soft', .08), ('ShadowLvl', .4), ('MidLvl', .7), ('LitLvl', 1.0),
                ('HiCut', 8.0), ('CelAmt', .8), ('Sat', 1.0), ('DepthT', .015), ('DepthK', 10.0), ('NormT', .3), ('NormK', 3.5),
                ('FadeNear', 2500.0), ('FadeFar', 16000.0), ('InkAmt', .9), ('Debug', 0.0)]

def master_comic():
    m = _fresh('M_PBX_Comic', G + '/Materials')
    m.set_editor_property('material_domain', unreal.MaterialDomain.MD_POST_PROCESS)
    m.set_editor_property('blendable_location', unreal.BlendableLocation.BL_SCENE_COLOR_BEFORE_DOF)
    STI = unreal.SceneTextureId
    code = COMIC_HLSL.replace('BASE_ID', str(int(STI.PPI_BASE_COLOR.value))).replace('STENCIL_ID', str(int(STI.PPI_CUSTOM_STENCIL.value))).replace('CDEPTH_ID', str(int(STI.PPI_CUSTOM_DEPTH.value)))
    cu = _e(m, unreal.MaterialExpressionCustom, -400, 0)
    cu.set_editor_property('code', code); cu.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    keys = [k for k, _ in COMIC_PARAMS] + ['ShadowTint', 'Ink', 'Exp', 'DA', 'DB', 'DC', 'DD', 'DE', 'DF']
    ins = []
    for k in keys:
        ci = unreal.CustomInput(); ci.set_editor_property('input_name', k); ins.append(ci)
    cu.set_editor_property('inputs', ins)
    y = 0
    for k, v in COMIC_PARAMS: MEL.connect_material_expressions(_scalar(m, k, v, -900, y), '', cu, k); y += 70
    MEL.connect_material_expressions(_vec(m, 'ShadowTint', (.78, .8, 1.0, 1), -900, y), '', cu, 'ShadowTint'); y += 120
    MEL.connect_material_expressions(_vec(m, 'Ink', (.03, .025, .045, 1), -900, y), '', cu, 'Ink'); y += 120
    MEL.connect_material_expressions(_e(m, unreal.MaterialExpressionEyeAdaptation, -900, y), '', cu, 'Exp'); y += 100
    for k, sid in (('DA', STI.PPI_POST_PROCESS_INPUT0), ('DB', STI.PPI_SCENE_DEPTH), ('DC', STI.PPI_WORLD_NORMAL), ('DD', STI.PPI_BASE_COLOR), ('DE', STI.PPI_CUSTOM_STENCIL), ('DF', STI.PPI_CUSTOM_DEPTH)):
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
            s.set_editor_property('weighted_blendables', wb)
            # comic grade: no sharpening (it chews the ink), gentler bloom, neutral saturation (the bands carry the punch)
            for k, v in [('sharpen', 0.0), ('bloom_intensity', .3), ('color_saturation', unreal.Vector4(1.03, 1.03, 1.03, 1)), ('vignette_intensity', .3)]:
                try: s.set_editor_property('override_' + k, True); s.set_editor_property(k, v)
                except Exception as ex: log('pp', k, ex)
            a.set_editor_property('settings', s)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    log('comic applied', on)
