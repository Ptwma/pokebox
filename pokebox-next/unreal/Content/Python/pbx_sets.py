# Sigil & Spark v4 — small dressed sets ("stages") built in Blender (tools/sets/set_*.py export mode) placed into L_Town far from
# the old town, one stage per set; the story's `place` node moves the player onto a stage.
#   import pbx_sets; pbx_sets.import_set('Pier')     (editor; L_Town loaded)
import unreal, os, json
SRC = r"E:\GAME-APP-DEV\POKEMON\PokeboxNext_src"
G = '/Game/PBX'
AT = unreal.AssetToolsHelpers.get_asset_tools(); EAL = unreal.EditorAssetLibrary
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
MEL = unreal.MaterialEditingLibrary
STAGES = {'Pier': (120000.0, 0.0, 0.0), 'Scriptorium': (150000.0, 0.0, 0.0), 'Alley': (180000.0, 0.0, 0.0), 'Lighthouse': (210000.0, 0.0, 3000.0)}   # stage origins (cm): far east of the old town, at sea level
def log(*a): print('[pbx]', *a)

def _emissive():
    """M_PBX_Emissive: unlit colour × strength (lantern glass, lit windows, the lighthouse lamp)"""
    path = G + '/Materials/M_PBX_Emissive'
    if EAL.does_asset_exist(path): return unreal.load_asset(path)
    m = AT.create_asset('M_PBX_Emissive', G + '/Materials', unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    c = MEL.create_material_expression(m, unreal.MaterialExpressionVectorParameter, -400, 0); c.set_editor_property('parameter_name', 'Color'); c.set_editor_property('default_value', unreal.LinearColor(1, .5, .15, 1))
    s = MEL.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -400, 200); s.set_editor_property('parameter_name', 'Strength'); s.set_editor_property('default_value', 4.0)
    mu = MEL.create_material_expression(m, unreal.MaterialExpressionMultiply, -200, 80)
    MEL.connect_material_expressions(c, '', mu, 'A'); MEL.connect_material_expressions(s, '', mu, 'B')
    MEL.connect_material_property(mu, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    MEL.recompile_material(m); EAL.save_asset(path); return m

def _mi(name, color, strength):
    path = f'{G}/Sets/MI_{name}'
    mi = unreal.load_asset(path) if EAL.does_asset_exist(path) else AT.create_asset(f'MI_{name}', G + '/Sets', unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mi.set_editor_property('parent', _emissive())
    MEL.set_material_instance_vector_parameter_value(mi, 'Color', unreal.LinearColor(*color, 1))
    MEL.set_material_instance_scalar_parameter_value(mi, 'Strength', strength)
    EAL.save_asset(path); return mi

def import_set(name='Pier'):
    base = os.path.join(SRC, 'sets', name.lower(), f'SM_Set_{name}')
    dest = f'{G}/Sets/{name}'
    o = unreal.FbxImportUI()
    o.set_editor_property('import_mesh', True); o.set_editor_property('import_as_skeletal', False)
    o.set_editor_property('import_materials', True); o.set_editor_property('import_textures', True)
    d = o.get_editor_property('static_mesh_import_data')
    d.set_editor_property('combine_meshes', True); d.set_editor_property('auto_generate_collision', False)
    try: d.set_editor_property('generate_lightmap_u_vs', False)
    except Exception: pass
    t = unreal.AssetImportTask()
    for k, v in (('filename', base + '.fbx'), ('destination_path', dest), ('automated', True), ('replace_existing', True), ('save', True), ('options', o)): t.set_editor_property(k, v)
    AT.import_asset_tasks([t])
    paths = list(t.get_editor_property('imported_object_paths') or [])
    sm = next((unreal.load_asset(p) for p in paths if isinstance(unreal.load_asset(p), unreal.StaticMesh)), None)
    if not sm: log('ERROR no static mesh imported', paths); return
    # collision: complex as simple so the player can walk the quay and the pier
    bs = sm.get_editor_property('body_setup')
    if bs: bs.set_editor_property('collision_trace_flag', unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    # emissive slots by Blender material name
    glow = {'LanternGlass': ((1.0, .45, .12), 6.0), 'RoomLit': ((1.0, .6, .28), 2.5), 'RoomDark': ((.02, .025, .04), 1.0), 'LampRoom': ((1.0, .8, .45), 8.0),
            'Candle': ((1.0, .62, .22), 10.0), 'JarGlow': ((.45, .75, 1.0), 1.5), 'LampRed': ((1.0, .12, .08), 8.0)}
    mats = sm.get_editor_property('static_materials')
    for i, sl in enumerate(mats):
        n = str(sl.get_editor_property('material_slot_name'))
        for k, (c, st) in glow.items():
            if n.startswith(k): sm.set_material(i, _mi(k, c, st))
    EAL.save_asset(sm.get_path_name())
    # place the stage
    loc = unreal.Vector(*STAGES.get(name, (120000.0, 0, 0)))
    for a in EAS.get_all_level_actors():
        if a.get_actor_label().startswith(f'SET_{name}'): EAS.destroy_actor(a)
    act = EAS.spawn_actor_from_object(sm, loc, unreal.Rotator(0, 0, 0)); act.set_actor_label(f'SET_{name}')
    info = json.load(open(base + '.json'))
    for i, L in enumerate(info['lights']):
        if L.get('type') == 'SPOT': continue   # preview-only moonlight shafts (outside the walls)
        p = unreal.Vector(loc.x + L['pos'][0], loc.y + L['pos'][1], loc.z + L['pos'][2])
        la = EAS.spawn_actor_from_class(unreal.PointLight, p, unreal.Rotator(0, 0, 0)); la.set_actor_label(f'SET_{name}_Light{i}')
        lc = la.get_component_by_class(unreal.PointLightComponent)
        # Blender watts → candelas, roughly (a 420 W lantern ≈ 8 cd); colour from the set
        c = L.get('color', [1, .55, .25])
        lc.set_editor_property('intensity', max(1.0, L.get('energy', 300) / 52.0)); lc.set_editor_property('intensity_units', unreal.LightUnits.CANDELAS)
        lc.set_editor_property('light_color', unreal.Color(r=int(255 * c[0]), g=int(255 * c[1]), b=int(255 * c[2]), a=255)); lc.set_editor_property('attenuation_radius', 1000.0)
        lc.set_editor_property('mobility', unreal.ComponentMobility.MOVABLE)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    log('set', name, 'at', loc, 'slots', len(mats), 'lights', len(info['lights']))
    return act
