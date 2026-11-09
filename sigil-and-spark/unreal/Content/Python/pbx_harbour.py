# Sigil & Spark — the harbour (s1, Ep1) as a real place for VIDEO MODE (owner 2026-11-08 22:11). Around the Pier stage:
# a photographed harbour sky (Poly Haven HDRI on a huge unlit dome centred on the stage, so every lens sees a real sky),
# real ships at anchor, the coast and a fort on the far headland, buoys and markers on the water, real props on the quay.
# All CC0 Poly Haven (SigilAndSpark_src/polyhaven, local only).
#   import pbx_harbour as H; H.run()          (editor, L_Town loaded; pbx_setreal.apply('Pier') does the set surfaces)
import unreal, os, glob, math

SRC = r"E:\GAME-APP-DEV\POKEMON\SigilAndSpark_src"
PH = os.path.join(SRC, 'polyhaven')
G = '/Game/PBX'; MESH = G + '/PH'; SKY = G + '/Sky'
AT = unreal.AssetToolsHelpers.get_asset_tools(); EAL = unreal.EditorAssetLibrary; MEL = unreal.MaterialEditingLibrary
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
STAGE = unreal.Vector(120000.0, 0.0, 0.0)   # pbx_sets.STAGES['Pier']; the sea lies towards +Y (the pier runs to y≈+1700)
TAG = 'HBR_'
def log(*a): print('[harbour]', *a)

# name, (x, y) cm from the stage origin, yaw, uniform scale, z offset — the far side first, then the water, then the quay
LAYOUT = [
    ('modular_fort_01',     (2500, 26000), 200, 1.0, 0),
    ('coastal_cliff_01',    (-14000, 21000), 30, 1.6, -150),
    ('coastal_cliff_04',    (16000, 23000), 160, 1.6, -150),
    ('coast_line_01',       (-9000, 9500), 15, 1.2, -60),
    ('coast_rocks_01',      (5200, 4200), 70, 1.0, -40),
    ('coast_land_rocks_02', (-4200, 3800), 120, 1.0, -50),
    ('dutch_ship_medium',   (-3600, 9000), 70, 1.0, -60),
    ('ship_pinnace',        (4600, 8200), 205, 1.0, -25),
    ('ocean_buoy',          (1800, 3000), 0, 1.0, -20),
    ('lateral_sea_marker',  (-1400, 5200), 0, 1.0, -30),
    ('wooden_barrels_01',   (-560, 120), 25, 1.0, 0),
    ('wicker_basket_01',    (240, 150), 0, 1.0, 0),
    ('wicker_basket_02',    (300, 110), 40, 1.0, 0),
    ('wine_barrel_01',      (-620, 40), 90, 1.0, 0),
    ('wooden_lantern_01',   (520, 330), 0, 1.0, 0),
    ('lifebuoy',            (650, 1260), 0, 1.0, 90),
    ('fishermans_hat',      (262, 140), 30, 1.0, 46),
    ('rubber_boots',        (-480, 90), 60, 1.0, 0),
]

def import_models(names, force=()):
    tasks = []
    for n in names:
        merged = glob.glob(os.path.join(PH, 'models', n, n + '_merged.glb'))
        if n in force and EAL.does_directory_exist(f'{MESH}/{n}'): EAL.delete_directory(f'{MESH}/{n}')
        if EAL.does_directory_exist(f'{MESH}/{n}') and EAL.list_assets(f'{MESH}/{n}'): continue
        g = merged or glob.glob(os.path.join(PH, 'models', n, '*.gltf'))
        if not g: log('not downloaded', n); continue
        t = unreal.AssetImportTask()
        for k, v in (('filename', g[0]), ('destination_path', f'{MESH}/{n}'), ('automated', True), ('replace_existing', True), ('save', True)): t.set_editor_property(k, v)
        tasks.append(t)
    if tasks: AT.import_asset_tasks(tasks)
    for t in tasks:
        for p in t.get_editor_property('imported_object_paths') or []:
            a = unreal.load_asset(p)
            if isinstance(a, unreal.StaticMesh):
                try: ns = a.get_editor_property('nanite_settings'); ns.set_editor_property('enabled', True); a.set_editor_property('nanite_settings', ns)
                except Exception: pass
                EAL.save_loaded_asset(a)
    log('imported', len(tasks))

def _mesh(n):
    for p in EAL.list_assets(f'{MESH}/{n}', recursive=True):
        a = unreal.load_asset(p.split('.')[0])
        if isinstance(a, unreal.StaticMesh): return a
    return None

def _clear():
    for a in EAS.get_all_level_actors():
        if a.get_actor_label().startswith(TAG): EAS.destroy_actor(a)

MERGED = ('dutch_ship_medium', 'ship_pinnace', 'modular_fort_01')   # tools/sets/ph_merge.py joins their parts first

def tag_town():
    """the old town's mountain ring + foliage instances hide while a scene plays on a stage (PBXStory 'place' stage:)"""
    n = 0
    for a in EAS.get_all_level_actors():
        if a.get_actor_label() in ('Mountains', 'Instances'):
            tags = list(a.get_editor_property('tags'))
            if 'PBX_Town' not in [str(x) for x in tags]: tags.append('PBX_Town'); a.set_editor_property('tags', tags); n += 1
    log('town tagged', n)

def dress(reimport_merged=False):
    import_models([n for n, *_ in LAYOUT], MERGED if reimport_merged else ())
    n = 0
    for i, (name, (x, y), yaw, s, dz) in enumerate(LAYOUT):
        sm = _mesh(name)
        if not sm: log('missing', name); continue
        p = unreal.Vector(STAGE.x + x, STAGE.y + y, STAGE.z); z = STAGE.z
        a = EAS.spawn_actor_from_object(sm, unreal.Vector(p.x, p.y, z + dz), unreal.Rotator(0, 0, yaw))
        a.set_actor_label(f'{TAG}{i:02d}_{name}'); a.set_actor_scale3d(unreal.Vector(s, s, s)); n += 1
    log('placed', n)

def sky(hdri='small_harbour_sunset_skyonly', exposure=1.0, rebuild=False, yaw=0.0, center=None, label='SkyDome'):
    """the photographed sky: the HDRI on an unlit, two-sided dome (radius 4 km) centred on the stage"""
    f = glob.glob(os.path.join(PH, 'hdri', hdri + '*.exr'))
    if not f: log('hdri not downloaded', hdri); return
    tex_path = f'{SKY}/T_HDRI_{hdri}'
    if not EAL.does_asset_exist(tex_path):
        t = unreal.AssetImportTask()
        for k, v in (('filename', f[0]), ('destination_path', SKY), ('destination_name', f'T_HDRI_{hdri}'), ('automated', True), ('replace_existing', True), ('save', True)): t.set_editor_property(k, v)
        AT.import_asset_tasks([t])
    tex = unreal.load_asset(tex_path)
    if not tex: log('hdri import failed'); return
    cube = isinstance(tex, unreal.TextureCube)
    mpath = f'{SKY}/M_HDRIDome_{"Cube" if cube else "LL"}'
    if rebuild:
        for a in EAS.get_all_level_actors():
            if a.get_actor_label() == TAG + 'SkyDome': EAS.destroy_actor(a)
        for p_ in (f'{SKY}/MI_HDRI_{hdri}', mpath):
            if EAL.does_asset_exist(p_): EAL.delete_asset(p_)
    if not EAL.does_asset_exist(mpath):
        m = AT.create_asset(mpath.split('/')[-1], SKY, unreal.Material, unreal.MaterialFactoryNew())
        m.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT); m.set_editor_property('two_sided', True); m.set_editor_property('is_sky', True)   # Is Sky: no fog over it (the 4 km dome sat inside the height fog)
        E = lambda c, x, y: MEL.create_material_expression(m, c, x, y)
        o = E(unreal.MaterialExpressionTextureObjectParameter, -900, 0); o.set_editor_property('parameter_name', 'Sky'); o.set_editor_property('texture', tex)
        ex = E(unreal.MaterialExpressionScalarParameter, -900, 200); ex.set_editor_property('parameter_name', 'Exposure'); ex.set_editor_property('default_value', 1.0)
        rot = E(unreal.MaterialExpressionScalarParameter, -900, 280); rot.set_editor_property('parameter_name', 'Yaw'); rot.set_editor_property('default_value', 0.0)
        wp = E(unreal.MaterialExpressionWorldPosition, -900, -200); cp = E(unreal.MaterialExpressionCameraPositionWS, -900, -120)
        cu = E(unreal.MaterialExpressionCustom, -500, 0); cu.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT3)
        # the photo's own ground never shows: tools/sets/hdri_skyonly.py repaints it with the sky above the horizon
        code = ("float3 d = normalize(WP - CP); float c = cos(Yaw), s = sin(Yaw); d.xy = float2(c * d.x - s * d.y, s * d.x + c * d.y); "
                + ("return TextureCubeSample(Sky, SkySampler, float3(d.x, d.y, d.z)).rgb * Exp;" if cube else
                   "float2 uv = float2(0.5 + atan2(d.y, d.x) / 6.2831853, acos(clamp(d.z, -1.0, 1.0)) / 3.1415927); return Texture2DSampleLevel(Sky, SkySampler, uv, 0).rgb * Exp;"))
        cu.set_editor_property('code', code)
        ins = []
        for k in ('WP', 'CP', 'Sky', 'Exp', 'Yaw'):
            ci = unreal.CustomInput(); ci.set_editor_property('input_name', k); ins.append(ci)
        cu.set_editor_property('inputs', ins)
        for k, src in (('WP', wp), ('CP', cp), ('Sky', o), ('Exp', ex), ('Yaw', rot)): MEL.connect_material_expressions(src, '', cu, k)
        MEL.connect_material_property(cu, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        MEL.recompile_material(m); EAL.save_asset(mpath)
    mip = f'{SKY}/MI_HDRI_{hdri}'
    mi = unreal.load_asset(mip) if EAL.does_asset_exist(mip) else AT.create_asset(mip.split('/')[-1], SKY, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mi.set_editor_property('parent', unreal.load_asset(mpath))
    MEL.set_material_instance_texture_parameter_value(mi, 'Sky', tex); MEL.set_material_instance_scalar_parameter_value(mi, 'Exposure', exposure); MEL.set_material_instance_scalar_parameter_value(mi, 'Yaw', yaw)
    MEL.update_material_instance(mi); EAL.save_asset(mip)
    for a in EAS.get_all_level_actors():
        if a.get_actor_label() == TAG + label: EAS.destroy_actor(a)
    sph = unreal.load_asset('/Engine/BasicShapes/Sphere')
    c0 = center or STAGE
    d = EAS.spawn_actor_from_object(sph, unreal.Vector(c0.x, c0.y, c0.z), unreal.Rotator(0, 0, 0))
    d.set_actor_label(TAG + label); d.set_actor_scale3d(unreal.Vector(8000, 8000, 8000))   # 100 cm sphere x 8000 = 4 km radius
    c = d.get_component_by_class(unreal.StaticMeshComponent)
    c.set_material(0, mi); c.set_editor_property('cast_shadow', False); c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    d.set_editor_property('tags', [unreal.Name('PBX_SkyDome')])   # the game dims it with the scene's sun (PBXStory 'sun')
    log('sky', hdri, 'cube' if cube else 'latlong')

def run(hdri='small_harbour_sunset_skyonly', reimport_merged=False):
    _clear(); tag_town(); dress(reimport_merged); sky(hdri)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    log('done')
