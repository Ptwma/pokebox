# Pokebox Next — realistic world pass (2026-10-22, user decision: "realistic world, stylized characters").
#   import pbx_realism; pbx_realism.assets()        once: Poly Haven textures (+ models) -> /Game/PBX/Tex/PH, /Game/PBX/PH
#   import pbx_realism; pbx_realism.materials()     masters/instances: real mountains, Poly Haven ground layers,
#                                                   Fantastic Village building surfaces -> photo-scanned textures
#   import pbx_realism; pbx_realism.level()         on the open level: physical sky + volumetric clouds instead of the
#                                                   painted dome, real-time sky light, haze, neutral grade, comic pass off
# pbx_build.build_level() calls level() after every rebuild. Source files: PokeboxNext_src/polyhaven (CC0, local only).
import unreal, os, glob, math

SRC = r"E:\GAME-APP-DEV\POKEMON\PokeboxNext_src"
PH = os.path.join(SRC, 'polyhaven')
G = '/Game/PBX'; TEX = G + '/Tex/PH'; MESH = G + '/PH'
AT = unreal.AssetToolsHelpers.get_asset_tools(); EAL = unreal.EditorAssetLibrary; MEL = unreal.MaterialEditingLibrary
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
def log(*a): print('[real]', *a)

# ------------------------------------------------------------------ assets
def _import(pairs, dest):
    tasks = []
    for f, name in pairs:
        t = unreal.AssetImportTask(); t.set_editor_property('filename', f); t.set_editor_property('destination_path', dest)
        if name: t.set_editor_property('destination_name', name)
        t.set_editor_property('automated', True); t.set_editor_property('replace_existing', True); t.set_editor_property('save', True)
        tasks.append(t)
    AT.import_asset_tasks(tasks)
    out = []
    for t in tasks: out += list(t.get_editor_property('imported_object_paths') or [])
    return out

def import_textures():
    pairs = []
    for d in sorted(glob.glob(os.path.join(PH, 'textures', '*'))):
        n = os.path.basename(d)
        for f in os.listdir(d):
            for key, suf in (('_diff_', '_diff'), ('_nor_gl_', '_nor'), ('_arm_', '_arm')):
                if key in f: pairs.append((os.path.join(d, f), 'PH_' + n + suf))
    _import(pairs, TEX)
    for p in EAL.list_assets(TEX, recursive=False):
        a = EAL.load_asset(p)
        if not isinstance(a, unreal.Texture2D): continue
        n = a.get_name()
        if n.endswith('_nor'):
            a.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_NORMALMAP); a.set_editor_property('srgb', False)
            a.set_editor_property('flip_green_channel', True)
        elif n.endswith('_arm'):
            a.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_MASKS); a.set_editor_property('srgb', False)
        a.set_editor_property('max_texture_size', 2048); EAL.save_loaded_asset(a)
    log('textures', len(pairs))

def import_models(names=None):
    """glTF 2k models (meshes + their own photo-scanned materials) -> /Game/PBX/PH/<name>/"""
    n = 0
    for d in sorted(glob.glob(os.path.join(PH, 'models', '*'))):
        name = os.path.basename(d)
        if names and name not in names: continue
        g = glob.glob(os.path.join(d, '*.gltf'))
        if not g: continue
        out = _import([(g[0], None)], MESH + '/' + name); n += 1
        for p in out:
            a = unreal.load_asset(p)
            if isinstance(a, unreal.StaticMesh):
                try:
                    ns = a.get_editor_property('nanite_settings'); ns.set_editor_property('enabled', True); a.set_editor_property('nanite_settings', ns)
                except Exception as ex: log('nanite', name, ex)
                plant = any(k in a.get_name() for k in ('grass', 'dandelion', 'celandine', 'fern', 'shrub', 'fir_', 'pine_', 'sapling', 'moss', 'tree'))
                bs = a.get_editor_property('body_setup')
                if bs: bs.set_editor_property('collision_trace_flag', unreal.CollisionTraceFlag.CTF_USE_DEFAULT if plant else unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
                EAL.save_loaded_asset(a)
        log('model', name, len(out))
    log('models', n)

def assets():
    import_textures(); import_models()

def town_inputs():
    """after tools/blender_town.py ran: the new splat + ground / far ground / mountain meshes"""
    B._import([os.path.join(SRC, 'tex', 'T_TownSplat.png')], G + '/Tex')
    t = unreal.load_asset(G + '/Tex/T_TownSplat')
    if t:
        t.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_MASKS); t.set_editor_property('srgb', False)
        t.set_editor_property('address_x', unreal.TextureAddress.TA_CLAMP); t.set_editor_property('address_y', unreal.TextureAddress.TA_CLAMP)
        EAL.save_loaded_asset(t)
    B.import_meshes(only=['SM_Ground', 'SM_GroundFar', 'SM_Mountains'])

def T(name): return unreal.load_asset(name if name.startswith('/Game/') else f'{TEX}/PH_{name}')

# ------------------------------------------------------------------ materials
import pbx_build as B

MOUNTAIN_HLSL = r"""
float3 p = WP / 100.0;
float3 n = normalize(N);
float slope = 1.0 - saturate(n.z);
float m1 = Texture2DSample(Macro, MacroSampler, p.xy / 517.0).r;
float m2 = Texture2DSample(Macro, MacroSampler, p.xy / 131.0).g;
float3 g = Texture2DSample(Grass, GrassSampler, p.xy / GrassSize).rgb;
g = lerp(g, Texture2DSample(Grass, GrassSampler, p.xy / (GrassSize * 4.7) + 0.31).rgb, 0.45);
float3 bw = pow(abs(n), 4.0); bw /= (bw.x + bw.y + bw.z);
float3 r = Texture2DSample(Rock, RockSampler, p.yz / RockSize).rgb * bw.x + Texture2DSample(Rock, RockSampler, p.xz / RockSize).rgb * bw.y
         + Texture2DSample(Rock, RockSampler, p.xy / RockSize).rgb * bw.z;
float3 s = Texture2DSample(Snow, SnowSampler, p.xy / SnowSize).rgb;
float nz = (m1 - 0.5) * 34.0 + (m2 - 0.5) * 12.0;
float rockW = smoothstep(RockA, RockB, slope + (m2 - 0.5) * 0.18);
float alpine = smoothstep(AlpineZ - 12.0, AlpineZ + 12.0, p.z + nz);
float snowW = smoothstep(SnowZ, SnowZ + 14.0, p.z + nz) * (1.0 - smoothstep(0.72, 0.93, slope + (m2 - 0.5) * 0.25));
// near the village the meadow uses the same leafy-grass scan + tint as the town ground (no seam where they meet)
float nearW = max(1.0 - smoothstep(170.0, 430.0, length(p.xy - float2(0.0, 10.0))), VC.g);   // VC.g: meadow (the island)
float3 gn = Texture2DSample(Near, NearSampler, p.xy / 25.0).rgb * NearTint;
g = lerp(g * GrassTint, gn, nearW);
float3 col = lerp(g, r * RockTint, saturate(max(rockW, alpine * 0.85)));
// beaches and the sea floor: sand below ~1 m, with a ragged edge
float3 sd = Texture2DSample(Sand, SandSampler, p.xy / 6.0).rgb * float3(1.1, 1.05, 0.95);
col = lerp(col, sd, 1.0 - smoothstep(-0.3, 1.3, p.z + (m2 - 0.5) * 1.6));
// the Lamplighters' Path: worn dirt where the terrain's vertex colour R says so
float3 dt = Texture2DSample(Dirt, DirtSampler, p.xy / 4.0).rgb;
col = lerp(col, dt, saturate(VC.r * (0.8 + 0.4 * m2)));
col = lerp(col, s * SnowTint, snowW);
col *= lerp(0.82, 1.15, m1 * 0.6 + m2 * 0.4);
float rough = lerp(lerp(0.95, 0.88, rockW), 0.55, snowW);
return Mode > 0.5 ? rough.xxx : col;
"""
MOUNTAIN_PARAMS = [('GrassSize', 38.0), ('RockSize', 34.0), ('SnowSize', 9.0), ('RockA', .3), ('RockB', .55), ('AlpineZ', 118.0), ('SnowZ', 160.0)]

def master_mountain():
    m = B._fresh('M_PBX_Mountain', G + '/Materials'); E = B._e
    keys = [k for k, _ in MOUNTAIN_PARAMS] + ['WP', 'N', 'VC', 'Grass', 'Rock', 'Snow', 'Near', 'Sand', 'Dirt', 'Macro', 'GrassTint', 'RockTint', 'SnowTint', 'NearTint', 'Mode']
    nodes = []
    for mode, y0 in ((0, 0), (1, 900)):
        cu = E(m, unreal.MaterialExpressionCustom, -300, y0); cu.set_editor_property('code', MOUNTAIN_HLSL)
        cu.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT3)
        ins = []
        for k in keys:
            ci = unreal.CustomInput(); ci.set_editor_property('input_name', k); ins.append(ci)
        cu.set_editor_property('inputs', ins); nodes.append(cu)
    shared = {}
    y = -600
    for k, v in MOUNTAIN_PARAMS: shared[k] = B._scalar(m, k, v, -1100, y); y += 70
    shared['WP'] = E(m, unreal.MaterialExpressionWorldPosition, -1100, y); y += 100
    shared['N'] = E(m, unreal.MaterialExpressionVertexNormalWS, -1100, y); y += 100
    shared['VC'] = E(m, unreal.MaterialExpressionVertexColor, -1100, y); y += 100
    for k, tex in (('Grass', 'aerial_grass_rock_diff'), ('Rock', 'aerial_rocks_02_diff'), ('Snow', 'snow_02_diff'), ('Near', 'leafy_grass_diff'),
                   ('Sand', f'{G}/Tex/coast_sand_01_diff'), ('Dirt', 'stony_dirt_path_diff')):
        o = E(m, unreal.MaterialExpressionTextureObjectParameter, -1100, y); o.set_editor_property('parameter_name', k + 'Tex')
        t = T(tex)
        if t: o.set_editor_property('texture', t)
        shared[k] = o; y += 150
    o = E(m, unreal.MaterialExpressionTextureObjectParameter, -1100, y); o.set_editor_property('parameter_name', 'MacroTex')
    o.set_editor_property('texture', unreal.load_asset('/Game/DreamscapeSeries/SharedResources/Textures/Utility/T_MacroVariation')); shared['Macro'] = o; y += 150
    for k, v in (('GrassTint', (.74, .92, .56, 1)), ('RockTint', (.95, .95, .97, 1)), ('SnowTint', (1.05, 1.07, 1.1, 1)), ('NearTint', GRASS_TINT)):
        shared[k] = B._vec(m, k, v, -1100, y); y += 120
    for mode, cu in enumerate(nodes):
        for k in keys[:-1]: MEL.connect_material_expressions(shared[k], 'RGB' if k.endswith('Tint') else '', cu, k)
        c = E(m, unreal.MaterialExpressionConstant, -600, 900 * mode + 700); c.set_editor_property('r', float(mode))
        MEL.connect_material_expressions(c, '', cu, 'Mode')
    MEL.connect_material_property(nodes[0], '', unreal.MaterialProperty.MP_BASE_COLOR)
    rm = E(m, unreal.MaterialExpressionComponentMask, 0, 900); rm.set_editor_property('r', True); MEL.connect_material_expressions(nodes[1], '', rm, '')
    MEL.connect_material_property(rm, '', unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.recompile_material(m); EAL.save_loaded_asset(m)
    log('mountain instr', MEL.get_statistics(m).num_pixel_shader_instructions)
    return m

def _ph(n): return {'BaseTex': f'{TEX}/PH_{n}_diff', 'NormalTex': f'{TEX}/PH_{n}_nor', 'ArmTex': f'{TEX}/PH_{n}_arm'}

# ------------------------------------------------------------------ water (2026-10-23): Single Layer Water shading (real
# absorption / scattering, Lumen reflections), Gerstner swell moving the sea mesh, rippled normals, shore foam.
# WAVES must stay identical to APBXBoat's buoyancy (C++): (direction deg in UE XY, wavelength m, amplitude m)
WAVES = [(84.0, 23.0, .20), (101.0, 13.5, .11), (70.0, 7.8, .055), (115.0, 4.6, .025)]
GERSTNER = r"""
float3 o = 0; float2 sl = 0;
float2 q = WP.xy / 100.0;
// calmer water near the shore (APBXDirector::ShoreDamp must match)
float dcst = -q.y - (45.0 + max(0.0, abs(q.x) - 110.0) * 0.55);
Amp *= lerp(0.25, 1.0, smoothstep(5.0, 150.0, dcst));
WAVEBODY
return Mode > 0.5 ? normalize(float3(-sl.x, -sl.y, 1.0)) : o * 100.0;
"""
def _gerstner_code():
    b = ''
    for i, (deg, lam, amp) in enumerate(WAVES):
        k = 6.2831853 / lam; c = (9.81 / k) ** .5; a = math.radians(deg)
        b += (f"{{ float2 d = float2({math.cos(a):.5f}, {math.sin(a):.5f}); float f = {k:.5f} * (dot(d, q) - {c:.5f} * T);"
              f" float A = {amp:.4f} * Amp; o.xy += d * (0.7 * A) * cos(f); o.z += A * sin(f); sl += d * ({k:.5f} * A) * cos(f); }}\n")
    return GERSTNER.replace('WAVEBODY', b)

def _custom(m, code, inputs, x, y, out=unreal.CustomMaterialOutputType.CMOT_FLOAT3):
    cu = B._e(m, unreal.MaterialExpressionCustom, x, y); cu.set_editor_property('code', code); cu.set_editor_property('output_type', out)
    ins = []
    for k in inputs:
        ci = unreal.CustomInput(); ci.set_editor_property('input_name', k); ins.append(ci)
    cu.set_editor_property('inputs', ins); return cu

def _water_common(m, flow_uv=False):
    """shared: SLW shading model + output node, detail ripples, foam. Returns (normal_node_ws or None)"""
    E = B._e
    m.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_SINGLE_LAYER_WATER)
    for k in ('used_with_nanite',):
        try: m.set_editor_property(k, False)
        except Exception: pass
    out = E(m, unreal.MaterialExpressionSingleLayerWaterMaterialOutput, 400, 600)
    MEL.connect_material_expressions(B._vec(m, 'Scattering', (.012, .035, .038, 1), 100, 500), '', out, 'ScatteringCoefficients')
    MEL.connect_material_expressions(B._vec(m, 'Absorption', (.42, .09, .06, 1), 100, 650), '', out, 'AbsorptionCoefficients')
    MEL.connect_material_expressions(B._scalar(m, 'PhaseG', .1, 100, 800), '', out, 'PhaseG')
    return out

def master_sea():
    m = B._fresh('M_PBX_Sea', G + '/Materials'); E = B._e
    _water_common(m)
    m.set_editor_property('tangent_space_normal', False)
    wp = E(m, unreal.MaterialExpressionWorldPosition, -1600, 0); tm = E(m, unreal.MaterialExpressionTime, -1600, 120)
    amp = B._scalar(m, 'WaveAmp', 1.0, -1600, 220)
    ins = ['WP', 'T', 'Amp', 'Mode']
    nodes = []
    for mode, y in ((0, 0), (1, 400)):
        cu = _custom(m, _gerstner_code(), ins, -1200, y)
        MEL.connect_material_expressions(wp, '', cu, 'WP'); MEL.connect_material_expressions(tm, '', cu, 'T'); MEL.connect_material_expressions(amp, '', cu, 'Amp')
        c = E(m, unreal.MaterialExpressionConstant, -1400, y + 300); c.set_editor_property('r', float(mode)); MEL.connect_material_expressions(c, '', cu, 'Mode')
        nodes.append(cu)
    MEL.connect_material_property(nodes[0], '', unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    # detail ripples (two scrolling samples of the tileable normal) bent around the swell normal, plus shore foam
    tex = unreal.load_asset(G + '/Tex/T_WaterNormal')
    o = E(m, unreal.MaterialExpressionTextureObjectParameter, -1200, 800); o.set_editor_property('parameter_name', 'RippleTex')
    if tex: o.set_editor_property('texture', tex)
    sd = E(m, unreal.MaterialExpressionSceneDepthWithoutWater, -1200, 1000); pd = E(m, unreal.MaterialExpressionPixelDepth, -1200, 1100)
    code = r"""
float2 q = WP.xy / 100.0;
float3 a = Texture2DSample(Rip, RipSampler, q / 9.0 + T * float2(0.011, 0.017)).xyz * 2 - 1;
float3 b = Texture2DSample(Rip, RipSampler, q / 4.3 - T * float2(0.019, -0.008)).xyz * 2 - 1;
float3 d = normalize(float3((a.xy + b.xy) * RipStr, 1.0));
float3 n = normalize(Swell);
float3 t = normalize(cross(float3(0, 1, 0), n)); float3 bt = cross(n, t);
float3 N = normalize(t * d.x + bt * d.y + n * d.z);
float depth = max(0.0, SD - PD);
float foam = (1.0 - smoothstep(4.0, 38.0, depth)) * saturate(0.35 + 0.6 * (a.x * b.y));
return Mode > 0.5 ? float3(foam, depth, 0) : N;
"""
    cn = []
    for mode, y in ((0, 800), (1, 1200)):
        cu = _custom(m, code, ['WP', 'T', 'Rip', 'RipStr', 'Swell', 'SD', 'PD', 'Mode'], -700, y)
        MEL.connect_material_expressions(wp, '', cu, 'WP'); MEL.connect_material_expressions(tm, '', cu, 'T'); MEL.connect_material_expressions(o, '', cu, 'Rip')
        MEL.connect_material_expressions(B._scalar(m, 'RippleStrength', .55, -1000, y + 200), '', cu, 'RipStr')
        MEL.connect_material_expressions(nodes[1], '', cu, 'Swell'); MEL.connect_material_expressions(sd, '', cu, 'SD'); MEL.connect_material_expressions(pd, '', cu, 'PD')
        c = E(m, unreal.MaterialExpressionConstant, -900, y + 300); c.set_editor_property('r', float(mode)); MEL.connect_material_expressions(c, '', cu, 'Mode')
        cn.append(cu)
    MEL.connect_material_property(cn[0], '', unreal.MaterialProperty.MP_NORMAL)
    fm = E(m, unreal.MaterialExpressionComponentMask, -300, 1200); fm.set_editor_property('r', True); MEL.connect_material_expressions(cn[1], '', fm, '')
    base = E(m, unreal.MaterialExpressionLinearInterpolate, -100, 900)
    MEL.connect_material_expressions(B._vec(m, 'WaterColor', (.0, .0, .0, 1), -300, 900), '', base, 'A')
    MEL.connect_material_expressions(B._vec(m, 'FoamColor', (.85, .88, .88, 1), -300, 1000), '', base, 'B'); MEL.connect_material_expressions(fm, '', base, 'Alpha')
    MEL.connect_material_property(base, '', unreal.MaterialProperty.MP_BASE_COLOR)
    rough = E(m, unreal.MaterialExpressionLinearInterpolate, -100, 1100); rough.set_editor_property('const_a', .035); rough.set_editor_property('const_b', .6)
    MEL.connect_material_expressions(fm, '', rough, 'Alpha'); MEL.connect_material_property(rough, '', unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.recompile_material(m); EAL.save_loaded_asset(m)
    log('sea instr', MEL.get_statistics(m).num_pixel_shader_instructions)
    return m

def master_river():
    """the stream: same water shading, ripples scrolling DOWNSTREAM along the ribbon's UV.x (metres), white water where
    the ribbon is steep (rapids) and along the banks"""
    m = B._fresh('M_PBX_River', G + '/Materials'); E = B._e
    _water_common(m)
    m.set_editor_property('tangent_space_normal', False)
    uv = E(m, unreal.MaterialExpressionTextureCoordinate, -1400, 0); tm = E(m, unreal.MaterialExpressionTime, -1400, 120)
    vn = E(m, unreal.MaterialExpressionVertexNormalWS, -1400, 240)
    sd = E(m, unreal.MaterialExpressionSceneDepthWithoutWater, -1400, 360); pd = E(m, unreal.MaterialExpressionPixelDepth, -1400, 460)
    tex = unreal.load_asset(G + '/Tex/T_WaterNormal')
    o = E(m, unreal.MaterialExpressionTextureObjectParameter, -1400, 600); o.set_editor_property('parameter_name', 'RippleTex')
    if tex: o.set_editor_property('texture', tex)
    code = r"""
float steep = saturate((1.0 - normalize(VN).z - 0.07) * 7.0);
float sp = Speed * (1.0 + 2.5 * steep);
float3 a = Texture2DSample(Rip, RipSampler, float2(UV.x / 3.0 - T * sp / 3.0, UV.y * 0.7)).xyz * 2 - 1;
float3 b = Texture2DSample(Rip, RipSampler, float2(UV.x / 1.7 - T * sp * 1.3 / 1.7, UV.y * 0.45 + 0.3)).xyz * 2 - 1;
float3 n = normalize(VN);
float3 t = normalize(cross(float3(0, 0, 1), n) + float3(0.0001, 0, 0)); float3 bt = cross(n, t);
float3 N = normalize(t * (a.y + b.y) * 0.5 + bt * (a.x + b.x) * 0.5 + n);
float depth = max(0.0, SD - PD);
float foam = saturate(steep * (0.4 + 0.35 * a.x));    // white water only on the rapids (no bank outline)
return Mode > 0.5 ? float3(foam, 0, 0) : N;
"""
    cn = []
    for mode, y in ((0, 0), (1, 400)):
        cu = _custom(m, code, ['UV', 'T', 'VN', 'SD', 'PD', 'Rip', 'Speed', 'Mode'], -800, y)
        for k, nd in (('UV', uv), ('T', tm), ('VN', vn), ('SD', sd), ('PD', pd), ('Rip', o)): MEL.connect_material_expressions(nd, '', cu, k)
        MEL.connect_material_expressions(B._scalar(m, 'FlowSpeed', 1.1, -1100, y + 200), '', cu, 'Speed')
        c = E(m, unreal.MaterialExpressionConstant, -1000, y + 300); c.set_editor_property('r', float(mode)); MEL.connect_material_expressions(c, '', cu, 'Mode')
        cn.append(cu)
    MEL.connect_material_property(cn[0], '', unreal.MaterialProperty.MP_NORMAL)
    fm = E(m, unreal.MaterialExpressionComponentMask, -400, 400); fm.set_editor_property('r', True); MEL.connect_material_expressions(cn[1], '', fm, '')
    base = E(m, unreal.MaterialExpressionLinearInterpolate, -100, 300)
    MEL.connect_material_expressions(B._vec(m, 'WaterColor', (.0, .0, .0, 1), -300, 200), '', base, 'A')
    MEL.connect_material_expressions(B._vec(m, 'FoamColor', (.9, .92, .92, 1), -300, 300), '', base, 'B'); MEL.connect_material_expressions(fm, '', base, 'Alpha')
    MEL.connect_material_property(base, '', unreal.MaterialProperty.MP_BASE_COLOR)
    rough = E(m, unreal.MaterialExpressionLinearInterpolate, -100, 500); rough.set_editor_property('const_a', .05); rough.set_editor_property('const_b', .55)
    MEL.connect_material_expressions(fm, '', rough, 'Alpha'); MEL.connect_material_property(rough, '', unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.recompile_material(m); EAL.save_loaded_asset(m)
    log('river instr', MEL.get_statistics(m).num_pixel_shader_instructions)
    return m

# harbour craft from tools/blender_town.py (2026-10-23 b) and their Poly Haven surfaces (painted / weathered planks, rubble)
CRAFT = ['SM_Rowboat', 'SM_RowboatB', 'SM_FishingBoat', 'SM_Sailboat', 'SM_BreakwaterW', 'SM_BreakwaterE', 'SM_StreamBridge']
BOAT_MATS = {'MI_BoatWhite': ('distressed_painted_planks', .5, (1, 1, 1)), 'MI_BoatBlue': ('blue_painted_planks', .5, (1, 1, 1)),
             'MI_BoatGreen': ('green_rough_planks', .5, (1, 1, 1)), 'MI_BoatWood': ('weathered_planks', .5, (1, 1, 1)),
             'MI_BoatPeel': ('wood_peeling_paint_weathered', .5, (1, 1, 1)), 'MI_BoatRed': ('distressed_painted_planks', .5, (.85, .22, .18)),
             'MI_HarbourStone': ('rubble', .35, (1, 1, 1)), 'MI_Quay': ('concrete_moss', .4, (1, 1, 1))}
def boat_materials():
    parent = unreal.load_asset(G + '/Materials/M_PBX_Surface')
    if not parent: log('no M_PBX_Surface'); return
    for name, (tex, uv, tint) in BOAT_MATS.items():
        if not unreal.load_asset(f'{TEX}/PH_{tex}_diff'): log('boat texture missing', tex); continue
        B._mi(name, parent, {'UVScale': uv}, {'Tint': (*tint, 1)}, {k: f'{TEX}/PH_{tex}{suf}' for k, suf in (('BaseTex', '_diff'), ('NormalTex', '_nor'), ('ArmTex', '_arm'))})

def water_inputs():
    """the ripple normal map (tools/water_normal.py) + the sea / river meshes"""
    B._import([os.path.join(SRC, 'tex', 'T_WaterNormal.png')], G + '/Tex')
    t = unreal.load_asset(G + '/Tex/T_WaterNormal')
    if t:
        t.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_NORMALMAP); t.set_editor_property('srgb', False)
        t.set_editor_property('flip_green_channel', True); EAL.save_loaded_asset(t)
    B.import_meshes(only=['SM_Water', 'SM_River', 'SM_Tunnel', 'SM_Island', 'SM_Lighthouse', 'SM_TrainLoco', 'SM_TrainCar'] + CRAFT)

def water_materials():
    sea = master_sea(); riv = master_river()
    for mesh, mat in (('SM_Water', sea), ('SM_River', riv)):
        sm = unreal.load_asset(f'{G}/Meshes/{mesh}')
        if not sm: log('missing', mesh); continue
        for i in range(len(sm.get_editor_property('static_materials'))): sm.set_material(i, mat)
        try:
            ns = sm.get_editor_property('nanite_settings'); ns.set_editor_property('enabled', False); sm.set_editor_property('nanite_settings', ns)
        except Exception as ex: log('nanite', mesh, ex)
        bs = sm.get_editor_property('body_setup')
        if bs: bs.set_editor_property('collision_trace_flag', unreal.CollisionTraceFlag.CTF_USE_DEFAULT)
        EAL.save_loaded_asset(sm)
    # meshes re-imported on their own (tunnel): each slot named M_X gets /Game/PBX/Materials/Inst/MI_X
    boat_materials()
    for mesh in ['SM_Tunnel', 'SM_Island', 'SM_Lighthouse', 'SM_TrainLoco', 'SM_TrainCar'] + CRAFT:
        sm = unreal.load_asset(f'{G}/Meshes/{mesh}')
        if not sm: continue
        for i, sl in enumerate(sm.get_editor_property('static_materials')):
            nm = str(sl.get_editor_property('material_slot_name')).split('.')[0]
            mi = unreal.load_asset(f'{G}/Materials/Inst/MI_{nm[2:]}') if nm.startswith('M_') else None
            if mi: sm.set_material(i, mi)
            else: log('tunnel slot without material', nm)
        bs = sm.get_editor_property('body_setup')
        if bs: bs.set_editor_property('collision_trace_flag', unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        EAL.save_loaded_asset(sm)
    # tunnel / built stone: photo-scanned rubble stone instead of the painted wall
    st = unreal.load_asset(f'{G}/Materials/Inst/MI_Stone')
    if st:
        for k, v in {'BaseTex': f'{G}/Tex/rustic_stone_wall_diff', 'NormalTex': f'{G}/Tex/rustic_stone_wall_nor', 'ArmTex': f'{G}/Tex/rustic_stone_wall_arm'}.items():
            tx = unreal.load_asset(v)
            if tx: MEL.set_material_instance_texture_parameter_value(st, k, tx)
        MEL.set_material_instance_scalar_parameter_value(st, 'UVScale', .4); MEL.set_material_instance_vector_parameter_value(st, 'Tint', unreal.LinearColor(.95, .93, .9, 1))
        MEL.update_material_instance(st); EAL.save_loaded_asset(st)
    log('water + stone materials')

# ground layers (town + Route 1): grass / dirt road / sand / paving
GROUND_REAL = {'GrassBase': f'{TEX}/PH_leafy_grass_diff', 'GrassNor': f'{TEX}/PH_leafy_grass_nor', 'GrassArm': f'{TEX}/PH_leafy_grass_arm',
               'DirtBase': f'{TEX}/PH_stony_dirt_path_diff', 'DirtNor': f'{TEX}/PH_stony_dirt_path_nor', 'DirtArm': f'{TEX}/PH_stony_dirt_path_arm',
               'SandBase': f'{G}/Tex/coast_sand_01_diff', 'SandNor': f'{G}/Tex/coast_sand_01_nor', 'SandArm': f'{G}/Tex/coast_sand_01_arm',
               'StoneBase': f'{TEX}/PH_cobblestone_floor_01_diff', 'StoneNor': f'{TEX}/PH_cobblestone_floor_01_nor', 'StoneArm': f'{TEX}/PH_cobblestone_floor_01_arm'}
GROUND_UV = {'GrassUV': .16, 'DirtUV': .2, 'SandUV': .2, 'StoneUV': .25}
GRASS_TINT = (.62, .86, .42, 1)     # the leafy-grass scan is mostly brown litter: pushed to a summer meadow green

# Fantastic Village Pack surfaces -> Poly Haven scans (the pack's houses keep their shapes, lose the hand-painted look)
FVP = '/Game/Fantastic_Village_Pack/materials/'
# roofs: Alpine village -> dark slate-grey tiles, not terracotta
FVP_REAL = {'MI_rooftiles_01': ('/Game/PBX/Tex/grey_roof_tiles', (.9, .86, .84)), 'MI_wall_02': ('plastered_wall_02', (1, 1, 1)),
            'MI_stonebrick_02': ('stacked_stone_wall', (1, 1, 1)), 'MI_ENV_stone': ('mossy_rock', (1, 1, 1)),
            'MI_wood_05': ('brown_planks_05', (1, 1, 1)), 'MI_wood_06': ('brown_planks_05', (.62, .55, .5)), 'MI_wood_07': ('brown_planks_05', (.8, .72, .64)),
            'MI_wood_planks_01': ('brown_planks_05', (1, 1, 1)), 'MI_wood_planks_03': ('brown_planks_05', (.9, .85, .8)),
            'MI_wood_planks_05': ('brown_planks_05', (1, 1, 1)), 'MI_wood_planks_07': ('brown_planks_05', (.75, .7, .65))}
# the pack's own textures, so real=False puts everything back exactly
FVP_ORIG = {'MI_rooftiles_01': ('T_rooftiles_01_BC', 'T_rooftiles_01_N'), 'MI_wall_02': ('T_wall_02_BC', 'T_wall_02_N'),
            'MI_stonebrick_02': ('T_stonebrick_02_BC', 'T_stonebrick_01_N'), 'MI_ENV_stone': ('T_ENV_stone_BC', 'T_ENV_stone_N'),
            'MI_wood_05': ('T_wood_05_BC', 'T_wood_05_N'), 'MI_wood_06': ('T_wood_06_BC', 'T_wood_06_N'), 'MI_wood_07': ('T_wood_07_BC', 'T_wood_07_N'),
            'MI_wood_planks_01': ('T_wood_planks_01_BC', 'T_wood_planks_01_N'), 'MI_wood_planks_03': ('T_wood_planks_03_BC', 'T_wood_planks_02_N'),
            'MI_wood_planks_05': ('T_wood_planks_05_BC', 'T_wood_planks_05_N'), 'MI_wood_planks_07': ('T_wood_planks_07_BC', 'T_wood_planks_07_N')}

def fvp_materials(real=True):
    n = 0
    for mi_name, (ph, tint) in FVP_REAL.items():
        mi = unreal.load_asset(FVP + mi_name)
        if not mi: log('fvp missing', mi_name); continue
        if real: b, nor = T(ph + '_diff'), T(ph + '_nor'); col = tint
        else:
            o = FVP_ORIG[mi_name]; b = unreal.load_asset('/Game/Fantastic_Village_Pack/textures/' + o[0]); nor = unreal.load_asset('/Game/Fantastic_Village_Pack/textures/' + o[1]); col = (1, 1, 1)
        if b: MEL.set_material_instance_texture_parameter_value(mi, 'Base Color Texture', b)
        if nor: MEL.set_material_instance_texture_parameter_value(mi, 'Normal Texture', nor)
        MEL.set_material_instance_vector_parameter_value(mi, 'Base Color Tint', unreal.LinearColor(col[0], col[1], col[2], 1))
        MEL.set_material_instance_scalar_parameter_value(mi, 'Normal Power', 1.0)
        MEL.set_material_instance_scalar_parameter_value(mi, 'Custom Roughness', .85 if real else .5)
        MEL.update_material_instance(mi); EAL.save_loaded_asset(mi); n += 1
    log('fvp materials', 'real' if real else 'original', n)

# painted Fab foliage (trees / bushes stay stylized — no free realistic trees that run in a game): toned down to natural
# greens so they sit in the photo-real world. Originals are saved once to Saved/pbx_foliage_orig.json (real=False restores).
FOLIAGE = {'/Game/Stylized_PBR_Nature/Foliage/Materials/': ('Diffuse_Colour_Multiply', (.66, .74, .56)),
           '/Game/StyleHex_Studio/Free_Packs/FREE_Stylized_Forest_Sample/Materials/Mat_Trees/': ('Custom Tint for Base Color texture', (.7, .78, .6)),
           '/Game/StyleHex_Studio/Free_Packs/FREE_Stylized_Forest_Sample/Materials/Mat_Foliage/': ('Custom Tint for Base Color texture', (.7, .78, .6))}

def foliage_tone(real=True):
    import json
    orig_f = os.path.join(unreal.Paths.project_saved_dir(), 'pbx_foliage_orig.json')
    orig = json.load(open(orig_f)) if os.path.exists(orig_f) else {}
    n = 0
    for folder, (param, tint) in FOLIAGE.items():
        if not EAL.does_directory_exist(folder): continue
        for p in EAL.list_assets(folder, recursive=False):
            mi = EAL.load_asset(p)
            if not isinstance(mi, unreal.MaterialInstanceConstant): continue
            names = [str(x) for x in MEL.get_vector_parameter_names(mi.get_base_material())]
            if param not in names or not any(k in mi.get_name() for k in ('Leaves', 'Leaf', 'Bush', 'Fol', 'Grass', 'Fern')): continue
            key = mi.get_path_name()
            if key not in orig:
                c = MEL.get_material_instance_vector_parameter_value(mi, param); orig[key] = [c.r, c.g, c.b, c.a]
            o = orig[key]
            col = (o[0] * tint[0], o[1] * tint[1], o[2] * tint[2], o[3]) if real else tuple(o)
            MEL.set_material_instance_vector_parameter_value(mi, param, unreal.LinearColor(*col)); MEL.update_material_instance(mi); EAL.save_loaded_asset(mi); n += 1
    json.dump(orig, open(orig_f, 'w'), indent=0)
    log('foliage toned' if real else 'foliage restored', n)

def materials():
    M = master_mountain()
    mi = B._mi('MI_Mountain', M)
    for p in ('/Game/PBX/Meshes/SM_Mountains',):
        sm = unreal.load_asset(p)
        if sm:
            for i in range(len(sm.get_editor_property('static_materials'))): sm.set_material(i, mi)
            EAL.save_loaded_asset(sm)
    for name, uv in (('MI_Ground', GROUND_UV), ('MI_GroundR1', GROUND_UV)):
        g = unreal.load_asset(f'{G}/Materials/Inst/{name}')
        if not g: continue
        for k, v in GROUND_REAL.items():
            t = unreal.load_asset(v)
            if t: MEL.set_material_instance_texture_parameter_value(g, k, t)
            else: log('ground tex missing', v)
        for k, v in uv.items(): MEL.set_material_instance_scalar_parameter_value(g, k, v)
        MEL.set_material_instance_vector_parameter_value(g, 'GrassTint', unreal.LinearColor(*GRASS_TINT))
        MEL.set_material_instance_vector_parameter_value(g, 'SandTint', unreal.LinearColor(1.1, 1.05, .95, 1))
        MEL.update_material_instance(g); EAL.save_loaded_asset(g)
    for mesh, mi_name in (('SM_Ground', 'MI_Ground'), ('SM_GroundFar', 'MI_Ground'), ('SM_R1_Ground', 'MI_GroundR1')):
        sm = unreal.load_asset(f'{G}/Meshes/{mesh}'); gm = unreal.load_asset(f'{G}/Materials/Inst/{mi_name}')
        if sm and gm: sm.set_material(0, gm); EAL.save_loaded_asset(sm)
    W = unreal.load_asset(f'{G}/Materials/M_PBX_Water')
    if W:
        wm = B._mi('MI_Water_Real', W, {'Roughness': .03}, {'Deep': (.012, .045, .06, 1), 'Shallow': (.03, .12, .13, 1)})
        sm = unreal.load_asset(f'{G}/Meshes/SM_Water')
        if sm:
            for i in range(len(sm.get_editor_property('static_materials'))): sm.set_material(i, wm)
            EAL.save_loaded_asset(sm)
    cr = unreal.load_asset(f'{G}/Materials/Inst/MI_CliffRock')   # tunnel-portal rock boxes: photo scan (edited in place, the meshes keep the reference)
    if cr:
        for k, v in _ph('aerial_rocks_02').items(): MEL.set_material_instance_texture_parameter_value(cr, k, unreal.load_asset(v))
        MEL.set_material_instance_scalar_parameter_value(cr, 'UVScale', .12); MEL.set_material_instance_vector_parameter_value(cr, 'Tint', unreal.LinearColor(.92, .9, .88, 1))
        MEL.update_material_instance(cr); EAL.save_loaded_asset(cr)
    fix_ph_collision()
    fvp_materials(True)
    foliage_tone(True)
    log('materials done')

def fix_ph_collision():
    n = 0
    for p in EAL.list_assets(MESH, recursive=True):
        a = EAL.load_asset(p)
        if not isinstance(a, unreal.StaticMesh): continue
        plant = any(k in a.get_name() for k in ('grass', 'dandelion', 'celandine', 'fern', 'shrub'))
        bs = a.get_editor_property('body_setup')
        if bs: bs.set_editor_property('collision_trace_flag', unreal.CollisionTraceFlag.CTF_USE_DEFAULT if plant else unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE); EAL.save_loaded_asset(a); n += 1
    log('ph collision', n)

# ------------------------------------------------------------------ level: light, sky, grade
def _sp(obj, **kw):
    for k, v in kw.items():
        try: obj.set_editor_property(k, v)
        except Exception as ex: log('prop', type(obj).__name__, k, ex)

def level(save=True):
    acts = EAS.get_all_level_actors()
    for a in acts:
        lbl = a.get_actor_label()
        if lbl in ('SkyDome',) or lbl.startswith('REAL_'): EAS.destroy_actor(a)
    acts = EAS.get_all_level_actors()
    sun = next((a for a in acts if isinstance(a, unreal.DirectionalLight)), None)
    if sun:
        sun.set_actor_rotation(unreal.Rotator(0, -42, 128), False)     # late-morning sun from the south-east (behind the camera on the street)
        lc = sun.get_component_by_class(unreal.DirectionalLightComponent)
        _sp(lc, intensity=10.0, light_color=unreal.Color(r=255, g=247, b=236, a=255), light_source_angle=.55, atmosphere_sun_light=True,
            cast_shadows=True, dynamic_shadow_distance_movable_light=12000.0)
    W = lambda cls, label, loc=(0, 0, 0): (lambda a: (a.set_actor_label(label), a)[1])(EAS.spawn_actor_from_class(cls, unreal.Vector(*loc)))
    sa = W(unreal.SkyAtmosphere, 'REAL_SkyAtmosphere')
    sac = sa.get_component_by_class(unreal.SkyAtmosphereComponent)
    _sp(sac, transform_mode=unreal.SkyAtmosphereTransformMode.PLANET_TOP_AT_ABSOLUTE_WORLD_ORIGIN, rayleigh_exponential_distribution=8.0,
        mie_scattering_scale=.006, aerial_pespective_view_distance_scale=1.6)
    vc = W(unreal.VolumetricCloud, 'REAL_Clouds')
    cm = unreal.load_asset('/Engine/EngineSky/VolumetricClouds/m_SimpleVolumetricCloud_Inst')
    vcc = vc.get_component_by_class(unreal.VolumetricCloudComponent)
    if cm: _sp(vcc, material=cm)
    _sp(vcc, layer_bottom_altitude=2.2, layer_height=4.5)
    for a in acts:
        if isinstance(a, unreal.SkyLight):
            c = a.get_component_by_class(unreal.SkyLightComponent)
            _sp(c, real_time_capture=True, source_type=unreal.SkyLightSourceType.SLS_CAPTURED_SCENE, sky_distance_threshold=150000.0, intensity=1.6,
                lower_hemisphere_is_black=False)
        if isinstance(a, unreal.ExponentialHeightFog):
            c = a.get_component_by_class(unreal.ExponentialHeightFogComponent)
            _sp(c, fog_density=.006, fog_height_falloff=.035, start_distance=6000.0, fog_inscattering_luminance=unreal.LinearColor(.45, .55, .7, 1),
                enable_volumetric_fog=True, volumetric_fog_scattering_distribution=.6, volumetric_fog_extinction_scale=.6, fog_max_opacity=.85)
        if isinstance(a, unreal.PostProcessVolume):
            s = a.get_editor_property('settings')
            wb = unreal.WeightedBlendables(); wb.set_editor_property('array', []); s.set_editor_property('weighted_blendables', wb)   # comic ink / cel pass off
            for k, v in [('auto_exposure_bias', .6), ('bloom_intensity', .35), ('ambient_occlusion_intensity', .55), ('vignette_intensity', .18),
                         ('color_saturation', unreal.Vector4(1.0, 1.0, 1.0, 1)), ('color_contrast', unreal.Vector4(1.02, 1.02, 1.02, 1)),
                         ('white_temp', 6500.0), ('sharpen', .25), ('film_toe', .55), ('film_slope', .86)]:
                try: s.set_editor_property('override_' + k, True); s.set_editor_property(k, v)
                except Exception as ex: log('pp', k, ex)
            a.set_editor_property('settings', s)
    log('level: physical sky, clouds, real-time sky light, haze, neutral grade')
    if save: unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()

# camera spots (UE cm; UE y = -Blender y, north = +y)
VIEWS = [('real_north', (0, -2600, 420), (0, 4000, 900)), ('real_peaks', (-1500, 800, 600), (2500, 40000, 9000)),
         ('real_plaza', (1400, 1000, 500), (-200, 2600, 200)), ('real_south', (0, 1200, 380), (0, -3600, 150)),
         ('real_inn', (-600, -2400, 350), (900, -3100, 300)), ('real_east', (-1200, -400, 450), (2400, 1800, 300)),
         ('real_aerial', (-6000, -9000, 6000), (0, 6000, 0)), ('real_tunnel', (4000, 6800, 450), (4000, 11205, 750))]
