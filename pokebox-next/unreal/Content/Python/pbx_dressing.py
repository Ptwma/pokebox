# Pokebox Next — set dressing (council S10), applied in the editor on top of the generated levels:
#   import pbx_dressing; pbx_dressing.route1()   (L_Route1 open)  -> the road to Mistvale closed on purpose: barricade,
#                                                   landslide rocks, a ROAD CLOSED board, cart and barrels (not an empty frame)
#   import pbx_dressing; pbx_dressing.town()     (L_Town open)     -> the grey tunnel-portal cliff boxes get Dreamscape
#                                                   cliffs and rocks in front of them; plaza flagstones tiled ~3x smaller
# Placed actors are labelled DRS_* and replaced on every run. pbx_build runs these after a level rebuild.
import unreal, math

EAL = unreal.EditorAssetLibrary; EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
FVP = '/Game/Fantastic_Village_Pack/meshes/props/'
PH = '/Game/PBX/PH/'
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
          (PH + 'rock_moss_set_01/rock_moss_set_01_2k/StaticMeshes/rock_moss_set_01_rock01', X - 650, -250, 30, ('h', 3.2), 60),
          (PH + 'rock_moss_set_01/rock_moss_set_01_2k/StaticMeshes/rock_moss_set_01_rock04', X - 700, 380, -40, ('h', 3.6), 60),
          (PH + 'rock_moss_set_02/rock_moss_set_02_2k/StaticMeshes/rock_moss_set_02_rock11', X - 380, 60, 10, ('h', 1.6), 20),
          (PH + 'boulder_01/boulder_01_2k/StaticMeshes/boulder_01_2k', X - 420, -520, 80, ('h', 1.4), 20),
          (PH + 'rock_moss_set_02/rock_moss_set_02_2k/StaticMeshes/rock_moss_set_02_rock08', X - 300, 0, 0, ('h', .6), 10),
          (PH + 'namaqualand_cliff_02/namaqualand_cliff_02_2k/StaticMeshes/namaqualand_cliff_02_2k', X - 1300, 0, 90, ('h', 9.0), 150)]   # landslide: Poly Haven scans
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
        o, ext = portal.get_actor_bounds(False)
        fy = o.y - ext.y              # the face towards the town (-Y); the arch (5.6 m wide, 7.4 m high) sits at x = o.x
        gz = o.z - ext.z               # foot of the portal
        # realistic pass (2026-10-22): Poly Haven photo-scanned cliffs / boulders instead of the painted Dreamscape ones
        MS = PH + 'mountainside/mountainside_2k/StaticMeshes/mountainside_2k'; NC = PH + 'namaqualand_cliff_02/namaqualand_cliff_02_2k/StaticMeshes/namaqualand_cliff_02_2k'
        R1 = PH + 'rock_moss_set_01/rock_moss_set_01_2k/StaticMeshes/rock_moss_set_01_rock0%d'; BO = PH + 'boulder_01/boulder_01_2k/StaticMeshes/boulder_01_2k'
        # 2026-10-23: the portal is now a stone headwall + wing walls backed by the tunnel mountain (terrain): only fallen
        # rocks at the foot of the wing walls, nothing stacked on the headwall
        L = [(R1 % 1, o.x - 1700, fy + 150, 30, ('h', 2.2), 30, None), (R1 % 4, o.x + 1750, fy + 120, -50, ('h', 2.0), 30, None),
             (BO, o.x - 2100, fy - 200, 70, ('h', 1.3), 15, None), (R1 % 6, o.x + 2050, fy - 260, 0, ('h', 1.2), 15, None)]
        for i, (mesh, x, y, yaw, size, sink, z) in enumerate(L):
            if _put(i, mesh, x, y, yaw, size, sink, z): n += 1
        print('[drs] tunnel portal dressed', n)
    else: print('[drs] tunnel portal not found')
    # (the stylized-era flagstone re-tiling was removed in the realistic pass: pbx_realism.GROUND_UV owns the tiling now)
    if save: unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()

VIEWS_R1 = [('drs_mistvale', (-32200, 0, 260), (-33800, 0, 150))]
