# Pokebox Next — set dressing (council S10), applied in the editor on top of the generated levels:
#   import pbx_dressing; pbx_dressing.route1()   (L_Route1 open)  -> the road to Mistvale closed on purpose: barricade,
#                                                   landslide rocks, a ROAD CLOSED board, cart and barrels (not an empty frame)
#   import pbx_dressing; pbx_dressing.town()     (L_Town open)     -> the grey tunnel-portal cliff boxes get Dreamscape
#                                                   cliffs and rocks in front of them; plaza flagstones tiled ~3x smaller
# Placed actors are labelled DRS_* and replaced on every run. pbx_build runs these after a level rebuild.
import unreal, math

EAL = unreal.EditorAssetLibrary; EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
FVP = '/Game/Fantastic_Village_Pack/meshes/props/'
_paths = {}

def _find(name):
    if name.startswith('/Game/'): return name
    if not _paths:
        for p in EAL.list_assets('/Game/DreamscapeSeries', recursive=True): _paths.setdefault(p.split('.')[-1], p.split('.')[0])
    return _paths.get(name)

def _world(): return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()

def _ground(x, y, z0=20000.0):
    h = unreal.SystemLibrary.line_trace_single(_world(), unreal.Vector(x, y, z0), unreal.Vector(x, y, -20000.0), unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,
                                               True, [], unreal.DrawDebugTrace.NONE, True)
    if not h: return 0.0
    for v in h.to_tuple()[4:7]:
        if isinstance(v, unreal.Vector): return v.z
    return 0.0

def _clear(prefix='DRS_'):
    for a in EAS.get_all_level_actors():
        if a.get_actor_label().startswith(prefix): EAS.destroy_actor(a)

def _put(i, mesh, x, y, yaw, size, sink=0.0, z=None, pitch=0.0, roll=0.0):
    p = _find(mesh); sm = unreal.load_asset(p) if p and EAL.does_asset_exist(p) else None
    if not sm or not isinstance(sm, unreal.StaticMesh): print('[drs] missing', mesh); return None
    b = sm.get_bounding_box(); e = b.max - b.min
    s = size[1] * 100.0 / max(1e-3, e.z if size[0] == 'h' else max(e.x, e.y))
    gz = _ground(x, y) if z is None else z
    a = EAS.spawn_actor_from_object(sm, unreal.Vector(x, y, gz - b.min.z * s - sink), unreal.Rotator(roll, pitch, yaw))
    a.set_actor_scale3d(unreal.Vector(s, s, s)); a.set_actor_label('DRS_%02d_%s' % (i, mesh.split('/')[-1])); a.set_folder_path('Dressing')
    return a

def route1(save=True):
    """the Mistvale exit is at x -33100 (trigger radius 3 m); the road runs on to x -33600 along y = 0. The barricade stands
    just past the trigger so the player sees it while the ROUTE 1 CLEARED screen explains the washout."""
    _clear()
    X = -33480.0; L = []
    for k, y in enumerate((-330.0, 0.0, 330.0)):                                  # a wooden fence line across the road
        L.append((FVP + 'construction/SM_PROP_fence_v03_01', X, y, 90, ('w', 3.4)))
    L += [(FVP + 'construction/SM_PROP_planks_01', X + 60, -140, 70, ('w', 2.6)), (FVP + 'construction/SM_PROP_planks_02', X + 70, 180, 110, ('w', 2.4)),
          (FVP + 'deco/SM_PROP_board_01', X + 140, 520, 90, ('w', 1.9)),          # the ROAD CLOSED notice, facing the player (east)
          (FVP + 'vehicles/SM_PROP_cart_03', X - 120, -650, 25, ('w', 3.0)),
          (FVP + 'container/SM_PROP_barrel_01', X + 90, -620, 0, ('h', .9)), (FVP + 'container/SM_PROP_barrel_03', X + 60, -520, 0, ('h', .9)),
          (FVP + 'light/SM_PROP_lantern_01', X + 120, 470, 0, ('h', .45), -0.0, None),
          ('SM_RockLarge_01', X - 650, -250, 30, ('h', 3.2), 60), ('SM_RockLarge_02', X - 700, 380, -40, ('h', 3.6), 60),
          ('SM_RockMedium_01', X - 380, 60, 10, ('h', 1.6), 20), ('SM_RockMedium_02', X - 420, -520, 80, ('h', 1.4), 20),
          ('SM_Pebbles_Dense_Stone', X - 300, 0, 0, ('w', 6.0)), ('SM_Cliff_03', X - 1300, 0, 90, ('h', 9.0), 150)]
    n = 0
    for i, spec in enumerate(L):
        if _put(i, *spec): n += 1
    print('[drs] route1 barricade', n)
    if save: unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()

def town(save=True):
    _clear()
    # tunnel portal: wrap the generated grey cliff boxes in Dreamscape cliffs (front face towards the town = -Y of the portal)
    portal = None
    for a in EAS.get_all_level_actors():
        c = a.get_component_by_class(unreal.StaticMeshComponent)
        m = c.get_editor_property('static_mesh') if c else None
        if m and 'Tunnel' in m.get_name(): portal = a; break
    n = 0
    if portal:
        o, ext = portal.get_actor_bounds(False); yaw = portal.get_actor_rotation().yaw
        fx, fy = math.cos(math.radians(yaw - 90)), math.sin(math.radians(yaw - 90))      # towards the town
        rx, ry = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        front = 0.45 * max(ext.x, ext.y)
        spots = [(-1, 0.55, 0), (1, 0.55, 0), (-1, 0.95, 0.2), (1, 0.95, 0.2), (0, 0.0, 1.0)]
        for i, (side, out_k, up) in enumerate(spots):
            if side == 0: x, y = o.x + fx * front * .3, o.y + fy * front * .3; h = 8.0
            else: x, y = o.x + rx * side * (ext.x * out_k + 350) + fx * front * .2, o.y + ry * side * (ext.x * out_k + 350) + fy * front * .2; h = 14.0 + 4 * up
            a = _put(i, 'SM_Cliff_0%d' % (i % 8 + 1), x, y, yaw + (0 if side <= 0 else 180) + 15 * i, ('h', h), 200, None if side else o.z + ext.z * .55)
            if a: n += 1
        for i, (dx, s_) in enumerate(((-900, 2.2), (950, 1.8), (-600, 1.2), (700, 1.4))):
            if _put(10 + i, 'SM_RockLarge_0%d' % (1 + i % 2), o.x + rx * dx + fx * front, o.y + ry * dx + fy * front, 37 * i, ('h', s_), 30): n += 1
        print('[drs] tunnel portal dressed', n)
    else: print('[drs] tunnel portal not found')
    # plaza flagstones: ~1.5 m flags read like giant tiles -> tile the stone layer 3x smaller on every ground instance
    for p in EAL.list_assets('/Game/PBX/Materials', recursive=True):
        mi = EAL.load_asset(p.split('.')[0])
        if isinstance(mi, unreal.MaterialInstanceConstant) and mi.get_editor_property('parent') and 'Ground' in mi.get_editor_property('parent').get_name():
            cur = unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(mi, 'StoneUV')
            if cur and cur < 6.0:
                unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(mi, 'StoneUV', cur * 3.0)
                EAL.save_loaded_asset(mi); print('[drs] StoneUV', mi.get_name(), cur, '->', cur * 3.0)
    if save: unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()

VIEWS_R1 = [('drs_mistvale', (-32200, 0, 260), (-33800, 0, 150))]
