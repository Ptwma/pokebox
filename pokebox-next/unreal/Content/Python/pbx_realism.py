# Pokebox Next — realistic world pass (2026-10-22, user decision: "realistic world, stylized characters").
#   import pbx_realism; pbx_realism.assets()        once: Poly Haven textures (+ models) -> /Game/PBX/Tex/PH, /Game/PBX/PH
#   import pbx_realism; pbx_realism.materials()     masters/instances: real mountains, Poly Haven ground layers,
#                                                   Fantastic Village building surfaces -> photo-scanned textures
#   import pbx_realism; pbx_realism.level()         on the open level: physical sky + volumetric clouds instead of the
#                                                   painted dome, real-time sky light, haze, neutral grade, comic pass off
# pbx_build.build_level() calls level() after every rebuild. Source files: PokeboxNext_src/polyhaven (CC0, local only).
import unreal, os, glob

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
                plant = any(k in a.get_name() for k in ('grass', 'dandelion', 'celandine', 'fern', 'shrub'))
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
float3 col = lerp(g * GrassTint, r * RockTint, saturate(max(rockW, alpine * 0.85)));
col = lerp(col, s * SnowTint, snowW);
col *= lerp(0.82, 1.15, m1 * 0.6 + m2 * 0.4);
float rough = lerp(lerp(0.95, 0.88, rockW), 0.55, snowW);
return Mode > 0.5 ? rough.xxx : col;
"""
MOUNTAIN_PARAMS = [('GrassSize', 38.0), ('RockSize', 34.0), ('SnowSize', 9.0), ('RockA', .3), ('RockB', .55), ('AlpineZ', 118.0), ('SnowZ', 160.0)]

def master_mountain():
    m = B._fresh('M_PBX_Mountain', G + '/Materials'); E = B._e
    keys = [k for k, _ in MOUNTAIN_PARAMS] + ['WP', 'N', 'Grass', 'Rock', 'Snow', 'Macro', 'GrassTint', 'RockTint', 'SnowTint', 'Mode']
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
    for k, tex in (('Grass', 'aerial_grass_rock_diff'), ('Rock', 'aerial_rocks_02_diff'), ('Snow', 'snow_02_diff')):
        o = E(m, unreal.MaterialExpressionTextureObjectParameter, -1100, y); o.set_editor_property('parameter_name', k + 'Tex')
        t = T(tex)
        if t: o.set_editor_property('texture', t)
        shared[k] = o; y += 150
    o = E(m, unreal.MaterialExpressionTextureObjectParameter, -1100, y); o.set_editor_property('parameter_name', 'MacroTex')
    o.set_editor_property('texture', unreal.load_asset('/Game/DreamscapeSeries/SharedResources/Textures/Utility/T_MacroVariation')); shared['Macro'] = o; y += 150
    for k, v in (('GrassTint', (.74, .92, .56, 1)), ('RockTint', (.95, .95, .97, 1)), ('SnowTint', (1.05, 1.07, 1.1, 1))):
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
