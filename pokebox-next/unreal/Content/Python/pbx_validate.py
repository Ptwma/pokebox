# Pokebox Next — level validator. Runs in the editor after a build and FAILS when the layout breaks the basic rules
# the autotest never checked (council 2026-10-11, quality freeze):
#   keep-clear   blocking props within 2 m of a door, a door's standing spot, an NPC, an item, an exit or a named spot
#   floating     a prop whose bottom hangs more than 30 cm above the ground under it
#   buried       a prop sunk deeper than 60 % of its height (usually a snapping error)
#   material     empty slot, engine default/world-grid material, or an instance with a missing/engine-default texture
#   placeholder  Kenney flat-colour kit meshes (banned from the final look)
# Usage from a queue job:   import pbx_validate; pbx_validate.run('L_Town')   (the level must be the one open in the editor)
# Writes Saved/pbx_validate_<map>.txt and prints "[pbx] VALIDATE <map> FAIL n WARN m".
import unreal, os, json, math

EAL = unreal.EditorAssetLibrary
SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
DATA = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()) + 'PBX/Data/'

CLEAR_R = 200.0          # cm, keep-clear radius around doors, exits, items and named spots
NPC_R = 120.0            # cm, around NPCs (they stand next to stalls and fences on purpose)
LANE_LEN, LANE_HALF = 800.0, 150.0   # cm, the walk-up lane in front of every outside door
SOFT = ('SM_Flower', 'SM_Grass', 'SM_Fol_', 'SM_Plant', 'SM_Fern', 'SM_Mushroom', 'SM_Clover')   # small plants: never 'block', but must not collide
FLOAT_TOL = 30.0         # cm
SKIP_LABELS = ('Ground', 'GroundFar', 'Mountains', 'R1_Ground', 'R1_Mountains', 'SkyDome', 'Sea', 'PostProcess', 'PlayerStart',
               'RoomLight', 'WindowFill')
SKIP_MESH = ('SM_Room_', 'SM_Ground', 'SM_R1_Ground', 'SM_Mountains', 'SM_R1_Mountains', 'SM_SkyDome', 'SM_Water', 'SM_GroundFar')
BAD_MAT = ('WorldGridMaterial', 'DefaultMaterial', 'DefaultDeferredDecalMaterial')
BAD_TEX = ('/Engine/EngineResources/DefaultTexture', '/Engine/EngineResources/Black', '/Engine/EngineResources/WhiteSquareTexture',
           '/Engine/EngineMaterials/DefaultWhiteGrid', '/Engine/EngineResources/DefaultTextureCube')
KENNEY = ('/Kits/KTown/', '/Kits/KPirate/', '/Kits/KSurvival/', '/Kits/KFurniture/', '/Kits/Kenney')

def _world(): return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()

def _points(G):
    """(label, x, y, z) gameplay points that must stay walkable"""
    P = []
    def add(lbl, p):
        if p and len(p) >= 3: P.append((lbl, float(p[0]), float(p[1]), float(p[2])))
    for d in G.get('doors', []):
        add('door %s outside' % d['id'], (d.get('outside') or {}).get('pos'))
        add('door %s inside' % d['id'], (d.get('inside') or {}).get('pos'))
    for n in G.get('npcs', []): add('npc %s' % n['id'], n.get('pos'))   # radius NPC_R (label starts with 'npc ')
    for k, s in (G.get('spots') or {}).items():
        if k.endswith('_hint') or k in ('starter_table', 'bed'): continue
        add('spot %s' % k, s.get('pos') if isinstance(s, dict) else s)
    for it in G.get('items', []): add('item %s' % it['id'], it.get('pos'))
    for e in G.get('exits', []): add('exit %s' % e['id'], e.get('pos'))
    if G.get('new_game'): add('new_game', G['new_game'].get('pos'))
    return P

def _lanes(G):
    """(label, points along the lane) from each outside door 8 m out towards/through its standing spot"""
    L = []
    for d in G.get('doors', []):
        od, sp_ = d.get('out_door'), (d.get('outside') or {}).get('pos')
        if not od: continue
        if sp_: dx, dy = sp_[0] - od[0], sp_[1] - od[1]
        else: continue
        n = math.hypot(dx, dy) or 1.0; dx, dy = dx / n, dy / n
        L.append(('door %s lane' % d['id'], od[2], [(od[0] + dx * t, od[1] + dy * t) for t in range(0, int(LANE_LEN) + 1, 50)]))
    return L

def _dist2d_box(x, y, mn, mx):
    dx = max(mn.x - x, 0.0, x - mx.x); dy = max(mn.y - y, 0.0, y - mx.y)
    return math.hypot(dx, dy)

def _ground_below(world, x, y, z_top, ignore):
    h = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, z_top), unreal.Vector(x, y, z_top - 20000.0),
                                               unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, ignore, unreal.DrawDebugTrace.NONE, True)
    if not h: return None
    for v in h.to_tuple()[4:7]:
        if isinstance(v, unreal.Vector): return v.z
    return None

def _mesh_path(a):
    c = a.get_component_by_class(unreal.StaticMeshComponent)
    m = c.get_editor_property('static_mesh') if c else None
    return (m.get_path_name() if m else ''), c

def _check_materials(c):
    bad = []
    for i, m in enumerate(c.get_materials()):
        if m is None: bad.append('slot %d empty' % i); continue
        p = m.get_path_name()
        if any(b in p for b in BAD_MAT): bad.append('slot %d default material %s' % (i, p.split('.')[-1])); continue
        if isinstance(m, unreal.MaterialInstanceConstant):
            for tp in m.get_editor_property('texture_parameter_values') or []:
                t = tp.get_editor_property('parameter_value')
                if t is None: bad.append('?slot %d texture %s missing' % (i, tp.get_editor_property('parameter_info').name))
                elif any(b in t.get_path_name() for b in BAD_TEX): bad.append('?slot %d texture %s = engine default' % (i, tp.get_editor_property('parameter_info').name))
    return bad

def run(map_name):
    world = _world()
    G = json.load(open(DATA + map_name + '.json', encoding='utf-8')) if os.path.exists(DATA + map_name + '.json') else {}
    pts = _points(G); lanes = _lanes(G)
    fails, warns = [], []
    actors = unreal.EditorLevelLibrary.get_all_level_actors()
    for a in actors:
        lbl = a.get_actor_label()
        if lbl.startswith(SKIP_LABELS) or isinstance(a, (unreal.Light, unreal.PlayerStart, unreal.PostProcessVolume, unreal.ExponentialHeightFog,
                                                       unreal.SkyLight, unreal.SkyAtmosphere, unreal.VolumetricCloud)):
            continue
        path, c = _mesh_path(a)
        is_bp = c is None or not isinstance(a, unreal.StaticMeshActor)
        if path and any(s in path for s in SKIP_MESH): continue
        o, ext = a.get_actor_bounds(False)
        mn, mx = o - ext, o + ext
        tall = ext.z * 2.0
        # ---- materials (every static mesh component, blueprints included)
        for sc in a.get_components_by_class(unreal.StaticMeshComponent):
            if not sc.get_editor_property('static_mesh'): continue
            for b in _check_materials(sc):
                (warns if b.startswith('?') else fails).append('MATERIAL  %s (%s): %s' % (lbl, sc.get_editor_property('static_mesh').get_name(), b.lstrip('?')))
        for sk in a.get_components_by_class(unreal.SkeletalMeshComponent):
            for i, m in enumerate(sk.get_materials()):
                if m is None or any(b in m.get_path_name() for b in BAD_MAT): fails.append('MATERIAL  %s skeletal slot %d default/empty' % (lbl, i))
        if path and any(k in path for k in KENNEY): warns.append('PLACEHOLDER  %s uses Kenney mesh %s' % (lbl, path.split('.')[-1]))
        # ---- keep-clear: only things you would bump into (collision on, taller than 30 cm, not a building — buildings own their door)
        blocking = c is not None and c.get_collision_enabled() != unreal.CollisionEnabled.NO_COLLISION
        building = is_bp or max(ext.x, ext.y) > 450.0
        soft = lbl.startswith(SOFT) or path.split('.')[-1].startswith(SOFT)
        if blocking and soft: warns.append('COLLIDES  plant %s has collision (the player bumps into it)' % lbl)
        if blocking and tall > 30.0 and not building and not soft:
            for (pl, x, y, z) in pts:
                if abs(z - o.z) > 400.0: continue        # interiors sit 60 m below; don't mix floors
                d = _dist2d_box(x, y, mn, mx)
                if d < (NPC_R if pl.startswith('npc ') else CLEAR_R): fails.append('KEEP-CLEAR  %s is %.0f cm from %s' % (lbl, d, pl))
            for (pl, z, P) in lanes:
                if abs(z - o.z) > 400.0: continue
                d = min(_dist2d_box(x, y, mn, mx) for (x, y) in P)
                if d < LANE_HALF: fails.append('DOOR-LANE  %s sits in the walk-up lane of %s' % (lbl, pl))
        # ---- floating / buried (single props only)
        if not building and c is not None and tall > 10.0:
            g = _ground_below(world, o.x, o.y, mx.z + 50.0, [a])   # from the top: a prop sunk into a slope must still see that slope
            if g is not None:
                if mn.z - g > FLOAT_TOL: fails.append('FLOATING  %s bottom %.0f cm above ground' % (lbl, mn.z - g))
                elif g - mn.z > .6 * tall and tall > 60.0: warns.append('BURIED  %s sunk %.0f of %.0f cm' % (lbl, g - mn.z, tall))
    out = os.path.join(SAVED, 'pbx_validate_%s.txt' % map_name)
    with open(out, 'w', encoding='utf-8') as fh:
        fh.write('%s  FAIL %d  WARN %d  (points checked %d, actors %d)\n\n' % (map_name, len(fails), len(warns), len(pts), len(actors)))
        for l in sorted(set(fails)): fh.write('FAIL ' + l + '\n')
        for l in sorted(set(warns)): fh.write('WARN ' + l + '\n')
    print('[pbx] VALIDATE %s FAIL %d WARN %d -> %s' % (map_name, len(set(fails)), len(set(warns)), out))
    return sorted(set(fails)), sorted(set(warns))
