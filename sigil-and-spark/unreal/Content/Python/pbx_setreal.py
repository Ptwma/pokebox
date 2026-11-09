# Sigil & Spark — realistic set pass for VIDEO MODE (owner 2026-11-08 22:11: "very high quality, detail in everything").
# The story sets (SM_Set_<Name>, built from the stylised Quaternius kit) get photo-scanned Poly Haven surfaces instead of
# the kit's painted textures: a world-aligned TRIPLANAR master (no kit UVs needed, no stretching, real scale in metres),
# one instance per surface. Unmatched slots are logged so the mapping can be finished by hand.
#   import pbx_setreal as R; R.textures(); R.apply('Pier'); R.report('Pier')
import unreal, os, glob, re

SRC = r"E:\GAME-APP-DEV\POKEMON\SigilAndSpark_src"
PH = os.path.join(SRC, 'polyhaven')
G = '/Game/PBX'; TEX = G + '/Tex/PH'; MI = G + '/Sets/Real'
AT = unreal.AssetToolsHelpers.get_asset_tools(); EAL = unreal.EditorAssetLibrary; MEL = unreal.MaterialEditingLibrary
def log(*a): print('[setreal]', *a)

# slot-name keyword (lower case, first match wins) -> (Poly Haven texture, tile size m, tint, roughness multiplier)
SURF = [
    ('vine',        None),                       # the kit's ivy keeps its own material
    ('roundtiles',  ('roof_slates_02', 1.6, (.78, .74, .72), 1.0)),
    ('rocktrim',    ('seaworn_sandstone_brick', 1.6, (.85, .84, .82), 1.0)),
    ('woodtrimwear',('weathered_peeling_timber', 1.4, (.62, .55, .48), 1.0)),
    ('woodtrim',    ('weathered_peeling_timber', 1.4, (.55, .47, .40), 1.0)),
    ('trimfurniture',('worn_planks', 1.2, (.62, .52, .42), 1.0)),
    ('trimmetal',   'IRON'),
    ('lifebuoy',    'BUOY'),
    ('colormap',    ('weathered_planks', 1.2, (.70, .62, .52), 1.0)),
    ('planterbox',  ('weathered_plank_siding', 1.2, (.66, .58, .50), 1.0)),
    ('roof',        ('roof_slates_02', 2.0, (.80, .82, .86), 1.0)),
    ('tile',        ('red_slate_roof_tiles_01', 2.0, (.85, .78, .74), 1.0)),
    ('plaster',     ('white_plaster_rough_02', 2.5, (.93, .90, .84), 1.0)),
    ('unevenbrick', ('old_stone_wall', 2.4, (.86, .84, .80), 1.0)),
    ('brick',       ('castle_brick_07', 2.0, (.84, .78, .72), 1.0)),
    ('stone',       ('seaworn_sandstone_brick', 2.2, (.85, .84, .82), 1.0)),
    ('rock',        ('low_tide_rocks', 3.0, (.80, .80, .80), 1.0)),
    ('cobble',      ('mossy_cobblestone', 2.0, (.82, .82, .80), 1.0)),
    ('floor',       ('worn_planks', 2.0, (.80, .74, .66), 1.0)),
    ('plank',       ('weathered_planks', 2.0, (.78, .72, .64), 1.0)),
    ('wooddark',    ('weathered_peeling_timber', 2.0, (.55, .48, .42), 1.0)),
    ('wood',        ('weathered_plank_siding', 2.0, (.75, .68, .60), 1.0)),
    ('sand',        ('damp_beach_sand', 3.0, (.85, .82, .76), 1.0)),
    ('ground',      ('mossy_cobblestone', 2.0, (.80, .80, .78), 1.0)),
]
TRI = r"""
float3 p = WP / 100.0 / Size; float3 n = normalize(N);
float3 w = pow(abs(n), 4.0); w /= (w.x + w.y + w.z);
float2 ux = p.yz, uy = p.xz, uz = p.xy;
if (Mode < 0.5) return Texture2DSample(Base, BaseSampler, ux).rgb * w.x + Texture2DSample(Base, BaseSampler, uy).rgb * w.y + Texture2DSample(Base, BaseSampler, uz).rgb * w.z;
if (Mode < 1.5) return Texture2DSample(Arm, ArmSampler, ux).rgb * w.x + Texture2DSample(Arm, ArmSampler, uy).rgb * w.y + Texture2DSample(Arm, ArmSampler, uz).rgb * w.z;
float2 ax = Texture2DSample(Nor, NorSampler, ux).rg * 2.0 - 1.0, ay = Texture2DSample(Nor, NorSampler, uy).rg * 2.0 - 1.0, az = Texture2DSample(Nor, NorSampler, uz).rg * 2.0 - 1.0;
float3 tx = float3(ax, sqrt(saturate(1.0 - dot(ax, ax)))), ty = float3(ay, sqrt(saturate(1.0 - dot(ay, ay)))), tz = float3(az, sqrt(saturate(1.0 - dot(az, az))));
tx = float3(tx.xy * Bump + n.zy, abs(tx.z) * n.x); ty = float3(ty.xy * Bump + n.xz, abs(ty.z) * n.y); tz = float3(tz.xy * Bump + n.xy, abs(tz.z) * n.z);
return normalize(tx.zyx * w.x + ty.xzy * w.y + tz.xyz * w.z);
"""

def textures():
    """import the Poly Haven texture folders that are not in /Game/PBX/Tex/PH yet (diff sRGB, nor/arm linear)"""
    pairs = []
    for d in sorted(glob.glob(os.path.join(PH, 'textures', '*'))):
        n = os.path.basename(d)
        for f in os.listdir(d):
            for key, suf in (('_diff_', '_diff'), ('_nor_gl_', '_nor'), ('_arm_', '_arm')):
                if key in f and not EAL.does_asset_exist(f'{TEX}/PH_{n}{suf}'): pairs.append((os.path.join(d, f), 'PH_' + n + suf))
    tasks = []
    for f, name in pairs:
        t = unreal.AssetImportTask()
        for k, v in (('filename', f), ('destination_path', TEX), ('destination_name', name), ('automated', True), ('replace_existing', True), ('save', True)): t.set_editor_property(k, v)
        tasks.append(t)
    if tasks: AT.import_asset_tasks(tasks)
    for _, name in pairs:
        a = unreal.load_asset(f'{TEX}/{name}')
        if not a: continue
        if name.endswith('_nor'):
            a.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_NORMALMAP); a.set_editor_property('srgb', False)
        elif name.endswith('_arm'):
            a.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_MASKS); a.set_editor_property('srgb', False)
        a.set_editor_property('max_texture_size', 2048); EAL.save_loaded_asset(a)
    log('imported', len(pairs))

def master(rebuild=False):
    """world-aligned (triplanar) PBR with Epic's own WorldAlignedTexture / WorldAlignedNormal functions (2026-11-08: a
    hand-written Custom-node version showed the ARM map as colour)"""
    path = G + '/Materials/M_PBX_TriplanarWA'
    if EAL.does_asset_exist(path) and not rebuild: return unreal.load_asset(path)
    m = unreal.load_asset(path) if EAL.does_asset_exist(path) else AT.create_asset('M_PBX_TriplanarWA', G + '/Materials', unreal.Material, unreal.MaterialFactoryNew())
    if rebuild: MEL.delete_all_material_expressions(m)
    m.set_editor_property('tangent_space_normal', False)
    E = lambda c, x, y: MEL.create_material_expression(m, c, x, y)
    def sp(name, v, x, y):
        e = E(unreal.MaterialExpressionScalarParameter, x, y); e.set_editor_property('parameter_name', name); e.set_editor_property('default_value', v); return e
    WAT = unreal.load_asset('/Engine/Functions/Engine_MaterialFunctions01/Texturing/WorldAlignedTexture')
    WAN = unreal.load_asset('/Engine/Functions/Engine_MaterialFunctions01/Texturing/WorldAlignedNormal')
    size = sp('Size', 2.0, -1400, 0); cm = E(unreal.MaterialExpressionMultiply, -1250, 0); cm.set_editor_property('const_b', 100.0)
    MEL.connect_material_expressions(size, '', cm, 'A')
    v3 = E(unreal.MaterialExpressionAppendVector, -1100, 0); v2 = E(unreal.MaterialExpressionAppendVector, -1180, 60)
    MEL.connect_material_expressions(cm, '', v2, 'A'); MEL.connect_material_expressions(cm, '', v2, 'B')
    MEL.connect_material_expressions(v2, '', v3, 'A'); MEL.connect_material_expressions(cm, '', v3, 'B')
    contrast = sp('Contrast', 4.0, -1400, 120)
    outs = {}
    for i, (k, fn, st) in enumerate((('Base', WAT, None), ('Arm', WAT, unreal.MaterialSamplerType.SAMPLERTYPE_MASKS), ('Nor', WAN, unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL))):
        o = E(unreal.MaterialExpressionTextureObjectParameter, -1100, 200 + 200 * i); o.set_editor_property('parameter_name', k + 'Tex')
        if st is not None: o.set_editor_property('sampler_type', st)
        dflt = unreal.load_asset(f'{TEX}/PH_castle_brick_07' + {'Base': '_diff', 'Arm': '_arm', 'Nor': '_nor'}[k])   # a parameter needs a default of the right type
        if dflt: o.set_editor_property('texture', dflt)
        f = E(unreal.MaterialExpressionMaterialFunctionCall, -800, 200 + 200 * i); f.set_material_function(fn)
        MEL.connect_material_expressions(o, '', f, 'TextureObject')
        MEL.connect_material_expressions(v3, '', f, 'TextureSize')
        MEL.connect_material_expressions(contrast, '', f, 'ProjectionTransitionContrast')
        outs[k] = f
    tint = E(unreal.MaterialExpressionVectorParameter, -500, -100); tint.set_editor_property('parameter_name', 'Tint'); tint.set_editor_property('default_value', unreal.LinearColor(1, 1, 1, 1))
    mb = E(unreal.MaterialExpressionMultiply, -300, 0); MEL.connect_material_expressions(outs['Base'], 'XYZ Texture', mb, 'A'); MEL.connect_material_expressions(tint, '', mb, 'B')
    MEL.connect_material_property(mb, '', unreal.MaterialProperty.MP_BASE_COLOR)
    r = E(unreal.MaterialExpressionComponentMask, -400, 300); r.set_editor_property('r', True); MEL.connect_material_expressions(outs['Arm'], 'XYZ Texture', r, '')
    g = E(unreal.MaterialExpressionComponentMask, -400, 380); g.set_editor_property('g', True); MEL.connect_material_expressions(outs['Arm'], 'XYZ Texture', g, '')
    b = E(unreal.MaterialExpressionComponentMask, -400, 460); b.set_editor_property('b', True); MEL.connect_material_expressions(outs['Arm'], 'XYZ Texture', b, '')
    rm = E(unreal.MaterialExpressionMultiply, -250, 380); MEL.connect_material_expressions(g, '', rm, 'A'); MEL.connect_material_expressions(sp('RoughMul', 1.0, -400, 540), '', rm, 'B')
    MEL.connect_material_property(r, '', unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
    MEL.connect_material_property(rm, '', unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(b, '', unreal.MaterialProperty.MP_METALLIC)
    MEL.connect_material_property(outs['Nor'], 'XYZ Texture', unreal.MaterialProperty.MP_NORMAL)
    MEL.recompile_material(m); EAL.save_asset(path); log('master', MEL.get_statistics(m).num_pixel_shader_instructions, 'instr')
    return m

PLASTERS = [('white_rough_plaster', 2.0, (1, 1, 1)), ('painted_plaster_wall', 2.0, (1, .98, .95)), ('red_plaster_weathered', 2.0, (1, 1, 1)),
            ('blue_plaster_weathered', 2.0, (1, 1, 1)), ('white_stucco', 2.0, (.97, .93, .86))]   # houses painted differently (real painted plasters)

def flat(name, rgb, rough):
    import pbx_sets
    return pbx_sets._fmi(name, rgb, rough)

def inst(tex, size, tint, rough, tag=''):
    name = f'MI_TP_{tex}{tag}'; path = f'{MI}/{name}'
    mi = unreal.load_asset(path) if EAL.does_asset_exist(path) else AT.create_asset(name, MI, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mi.set_editor_property('parent', master())
    for k, suf in (('BaseTex', '_diff'), ('ArmTex', '_arm'), ('NorTex', '_nor')):
        t = unreal.load_asset(f'{TEX}/PH_{tex}{suf}')
        if t: MEL.set_material_instance_texture_parameter_value(mi, k, t)
        else: log('missing texture', tex + suf)
    MEL.set_material_instance_scalar_parameter_value(mi, 'Size', size); MEL.set_material_instance_scalar_parameter_value(mi, 'RoughMul', rough)
    MEL.set_material_instance_vector_parameter_value(mi, 'Tint', unreal.LinearColor(*tint, 1))
    MEL.update_material_instance(mi); EAL.save_asset(path); return mi

def report(name='Pier'):
    sm = unreal.load_asset(f'{G}/Sets/{name}/SM_Set_{name}')
    if not sm: log('no set', name); return []
    out = []
    for i, sl in enumerate(sm.get_editor_property('static_materials')):
        mi = sl.get_editor_property('material_interface')
        out.append((i, str(sl.get_editor_property('material_slot_name')), mi.get_name() if mi else None))
    for o in out: log(*o)
    return out

def apply(name='Pier', extra=None):
    """swap every kit surface slot of SM_Set_<name> for its triplanar photo-scan instance; emissive/flat slots stay"""
    sm = unreal.load_asset(f'{G}/Sets/{name}/SM_Set_{name}')
    if not sm: log('no set', name); return
    rules = (extra or []) + SURF
    done, skip = 0, []
    for i, sl in enumerate(sm.get_editor_property('static_materials')):
        n = str(sl.get_editor_property('material_slot_name')); cur = sl.get_editor_property('material_interface')
        if cur and (cur.get_name().startswith(('MI_Lantern', 'MI_Room', 'MI_Lamp', 'MI_Candle', 'MI_Jar'))): continue   # emissive
        key = n.lower().replace('_', '')
        found = [v for k, v in rules if k in key]
        if not found: skip.append(n); continue
        hit = found[0]
        if hit is None: continue
        if hit == 'IRON': sm.set_material(i, flat('RealIron', (.045, .043, .045), .42)); done += 1; continue
        if hit == 'BUOY': sm.set_material(i, flat('RealBuoy', (.75, .12, .06), .55)); done += 1; continue
        if 'plaster' in key:   # one tint per house (the kit names carry the house tag: _h1, _h20 ...)
            hs = re.findall(r'h(\d+)', n.lower()); k = (int(hs[0]) if hs else 0) % len(PLASTERS)
            tx, sz, tn = PLASTERS[k]; sm.set_material(i, inst(tx, sz, tn, 1.0)); done += 1; continue
        sm.set_material(i, inst(*hit)); done += 1
    EAL.save_asset(sm.get_path_name())
    log('set', name, 'real surfaces', done, 'unmatched', skip)
    return skip
