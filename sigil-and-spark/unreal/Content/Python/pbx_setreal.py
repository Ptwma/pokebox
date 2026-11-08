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

def master():
    path = G + '/Materials/M_PBX_Triplanar'
    if EAL.does_asset_exist(path): return unreal.load_asset(path)
    m = AT.create_asset('M_PBX_Triplanar', G + '/Materials', unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property('tangent_space_normal', False)   # the triplanar normal is built in world space
    E = lambda c, x, y: MEL.create_material_expression(m, c, x, y)
    def sp(name, v, x, y):
        e = E(unreal.MaterialExpressionScalarParameter, x, y); e.set_editor_property('parameter_name', name); e.set_editor_property('default_value', v); return e
    wp = E(unreal.MaterialExpressionWorldPosition, -1200, -200); nn = E(unreal.MaterialExpressionVertexNormalWS, -1200, -80)
    size = sp('Size', 2.0, -1200, 40); bump = sp('Bump', 1.0, -1200, 120)
    texs = {}
    for i, k in enumerate(('Base', 'Arm', 'Nor')):
        o = E(unreal.MaterialExpressionTextureObjectParameter, -1200, 220 + 160 * i); o.set_editor_property('parameter_name', k + 'Tex')
        if k == 'Nor': o.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        elif k == 'Arm': o.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
        texs[k] = o
    outs = []
    for mode in range(3):
        cu = E(unreal.MaterialExpressionCustom, -600, -300 + 400 * mode); cu.set_editor_property('code', TRI)
        cu.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT3)
        ins = []
        for k in ('WP', 'N', 'Size', 'Bump', 'Base', 'Arm', 'Nor', 'Mode'):
            ci = unreal.CustomInput(); ci.set_editor_property('input_name', k); ins.append(ci)
        cu.set_editor_property('inputs', ins)
        for k, src in (('WP', wp), ('N', nn), ('Size', size), ('Bump', bump), ('Base', texs['Base']), ('Arm', texs['Arm']), ('Nor', texs['Nor'])):
            MEL.connect_material_expressions(src, '', cu, k)
        c = E(unreal.MaterialExpressionConstant, -800, -200 + 400 * mode); c.set_editor_property('r', float(mode)); MEL.connect_material_expressions(c, '', cu, 'Mode')
        outs.append(cu)
    tint = E(unreal.MaterialExpressionVectorParameter, -400, -500); tint.set_editor_property('parameter_name', 'Tint'); tint.set_editor_property('default_value', unreal.LinearColor(1, 1, 1, 1))
    mb = E(unreal.MaterialExpressionMultiply, -200, -400); MEL.connect_material_expressions(outs[0], '', mb, 'A'); MEL.connect_material_expressions(tint, '', mb, 'B')
    MEL.connect_material_property(mb, '', unreal.MaterialProperty.MP_BASE_COLOR)
    r = E(unreal.MaterialExpressionComponentMask, -300, 0); r.set_editor_property('r', True); MEL.connect_material_expressions(outs[1], '', r, '')
    g = E(unreal.MaterialExpressionComponentMask, -300, 80); g.set_editor_property('g', True); MEL.connect_material_expressions(outs[1], '', g, '')
    b = E(unreal.MaterialExpressionComponentMask, -300, 160); b.set_editor_property('b', True); MEL.connect_material_expressions(outs[1], '', b, '')
    rm = E(unreal.MaterialExpressionMultiply, -150, 80); MEL.connect_material_expressions(g, '', rm, 'A'); MEL.connect_material_expressions(sp('RoughMul', 1.0, -300, 240), '', rm, 'B')
    MEL.connect_material_property(r, '', unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
    MEL.connect_material_property(rm, '', unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(b, '', unreal.MaterialProperty.MP_METALLIC)
    MEL.connect_material_property(outs[2], '', unreal.MaterialProperty.MP_NORMAL)
    MEL.recompile_material(m); EAL.save_asset(path); log('master', MEL.get_statistics(m).num_pixel_shader_instructions, 'instr')
    return m

PLASTER_TINTS = [(.95, .93, .88), (.80, .84, .92), (.95, .82, .74), (.80, .86, .76), (.86, .80, .82)]   # houses painted differently

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
            hs = re.findall(r'h(\d+)', n.lower()); k = (int(hs[0]) if hs else 0) % len(PLASTER_TINTS)
            sm.set_material(i, inst(hit[0], hit[1], PLASTER_TINTS[k], hit[3], f'_{k}')); done += 1; continue
        sm.set_material(i, inst(*hit)); done += 1
    EAL.save_asset(sm.get_path_name())
    log('set', name, 'real surfaces', done, 'unmatched', skip)
    return skip
