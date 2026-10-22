# Pokebox Next — interiors (council S8): the home and Pokébox Labs rooms (60 m under the town) furnished from the free
# Fantastic Village Pack + Dreamscape props instead of the Kenney flat-colour kit. Runs on the open L_Town level:
#   import pbx_interiors; pbx_interiors.run()            (pbx_build calls it after every town build)
# Every placed actor is labelled INT_*, so a re-run first deletes the previous INT_ set. Kenney pieces are removed,
# except the bed (no bed in the free packs). Room geometry: floor z = -6000; home x[-1975,-1025] y[125,875] (door at y 125);
# lab x[-900,900] y[2850,3950] (door at y 2850). Gameplay points to keep clear: home door-in (-1500,270), Mum (-1280,340),
# new-game (-1660,620); lab door-in (0,2980), Vale (0,3540), aide Pim (600,3690), starter table (0,3700).
import unreal

EAL = unreal.EditorAssetLibrary; EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
FLOOR = -6000.0
KENNEY_KEEP = ()
KENNEY_EXTRA = ('bedSingle',)
KENNEY = ('bookcaseOpen', 'books', 'desk', 'computerScreen', 'chairDesk', 'rugRectangle', 'pottedPlant', 'rugDoormat', 'kitchenCabinet',
          'kitchenStove', 'radio', 'laptop', 'bookcaseClosedWide', 'cabinetTelevision', 'televisionModern', 'loungeSofaLong',
          'tableCoffeeGlass', 'Table_Large', 'chair', 'coatRackStanding', 'sideTable', 'tableCoffee', 'tableRound', 'lampRoundTable', 'loungeSofa',
          'kitchenFridge')
FVP = '/Game/Fantastic_Village_Pack/meshes/props/'
SMALL = ('SM_Candle', 'SM_BookOpen', 'SM_InkWell', 'SM_Book_', 'SM_PROP_plate', 'SM_PROP_cup', 'SM_PROP_food', 'SM_PROP_lantern', 'SM_Globe',
         'SM_PROP_bottle', 'SM_PROP_cookingpot', 'SM_Crystal')

# (mesh, x, y, yaw, size[, z offset cm]) size = ('h'|'w', metres[, 'x'|'y' = axis the long side must run along])
QP = '/Game/PBX/Kits/QProps/'
HOME = [
    (QP + 'Bed_Twin1', -1830, 720, 0, ('w', 2.0, 'y')), (QP + 'Nightstand_Shelf', -1940, 560, 0, ('h', .6)),
    (QP + 'CandleStick', -1940, 560, 0, ('h', .3), 60),
    (QP + 'Bookcase_2', -1270, 845, 0, ('h', 2.0, 'x')),
    ('SM_WoodDesk', -1090, 815, 0, ('h', .8)), ('SM_Chair', -1090, 720, 180, ('h', 1.0)),
    (QP + 'BookGroup_Small_1', -1130, 815, 0, ('w', .3), 80), (QP + 'Candle_1', -1035, 820, 0, ('h', .2), 80),
    (QP + 'Table_Large', -1200, 560, 0, ('h', .78, 'x')),
    (QP + 'Chair_1', -1200, 455, 0, ('h', .95)), (QP + 'Chair_1', -1200, 665, 180, ('h', .95)),
    (QP + 'Table_Plate', -1235, 560, 0, ('w', .28), 78), (QP + 'Mug', -1150, 575, 0, ('h', .12), 78), (QP + 'Vase_2', -1190, 540, 0, ('h', .3), 78),
    (QP + 'Workbench_Drawers', -1820, 175, 180, ('h', .9, 'x')), (QP + 'Pot_1', -1800, 175, 0, ('h', .3), 90),
    (QP + 'Barrel_Apples', -1935, 330, 0, ('h', .9)), (FVP + 'container/SM_PROP_basket_01', -1935, 430, 0, ('h', .35)),
    (QP + 'Chandelier', -1500, 500, 0, ('h', .7), 245),
    (FVP + 'natural/SM_PROP_PLANT_pot_v1_01', -1065, 165, 0, ('h', .7)), (FVP + 'natural/SM_PROP_PLANT_pot_v2_01', -1940, 845, 0, ('h', .6)),
]
LAB = [
    (QP + 'Bookcase_2', -862, 3150, 90, ('h', 2.2, 'y')), (QP + 'Bookcase_2', -862, 3450, 90, ('h', 2.2, 'y')), (QP + 'Bookcase_2', -862, 3750, 90, ('h', 2.2, 'y')),
    ('SM_WoodDesk', -560, 3875, 0, ('h', .8)), ('SM_Chair', -560, 3770, 180, ('h', 1.0)),
    ('SM_Globe', -650, 3880, 0, ('h', .45), 80), (QP + 'Potion_1', -500, 3880, 0, ('h', .2), 80), (QP + 'BookGroup_Small_2', -560, 3870, 0, ('w', .3), 80),
    ('SM_WoodDesk', 560, 3875, 0, ('h', .8)), (QP + 'CandleStick_Triple', 640, 3880, 0, ('h', .35), 80), (QP + 'Scroll_1', 500, 3870, 0, ('w', .3), 80),
    (QP + 'Table_Large', 0, 3720, 0, ('h', .92, 'x')),          # the starter-card table (cards stand at z +95)
    (QP + 'Cabinet', 862, 3100, -90, ('h', 1.9, 'y')),
    ('SM_CrystalGroup_01_Blue', 820, 2960, 0, ('h', .8)), ('SM_RuneStone_01', 780, 3400, -90, ('h', 1.7)),
    (QP + 'Crate_Wooden', 830, 3600, 10, ('h', .6)), (QP + 'Crate_Metal', 830, 3700, -90, ('h', .5)),
    (QP + 'Chandelier', -450, 3400, 0, ('h', .8), 330), (QP + 'Chandelier', 450, 3400, 0, ('h', .8), 330),
    (FVP + 'natural/SM_PROP_PLANT_pot_v1_02', -850, 2905, 0, ('h', .8)), (FVP + 'natural/SM_PROP_PLANT_pot_v3_01', 850, 2880, 0, ('h', .8)),
    (QP + 'Workbench', 845, 3240, 0, ('h', .9, 'y')), (QP + 'Cage_Small', 850, 3200, 0, ('h', .45), 90), (QP + 'Potion_4', 845, 3290, 0, ('h', .22), 90),
    (QP + 'Book_Stack_1', 120, 3725, 0, ('h', .15), 92), (QP + 'CandleStick', -110, 3725, 0, ('h', .3), 92),
    (FVP + 'furniture/SM_PROP_bench_01', -520, 2910, 0, ('w', 1.8, 'x')), (FVP + 'furniture/SM_PROP_bench_01', 520, 2910, 0, ('w', 1.8, 'x')),
    (QP + 'Lantern_Wall', -880, 2990, 90, ('h', .5), 190), (QP + 'Lantern_Wall', 880, 3800, -90, ('h', .5), 190),
]
MOVE = {'Cauldron': (760, 3820)}     # existing Quaternius pieces that stay, but out of the middle of the room

_paths = {}
def _find(name):
    if name.startswith('/Game/'): return name
    if not _paths:
        for p in EAL.list_assets('/Game/DreamscapeSeries', recursive=True): _paths.setdefault(p.split('.')[-1], p.split('.')[0])
    return _paths.get(name)

def _place(spec, i):
    mesh, x, y, yaw, size = spec[:5]; dz = spec[5] if len(spec) > 5 else 0.0
    p = _find(mesh); sm = unreal.load_asset(p) if p and EAL.does_asset_exist(p) else None
    if not sm or not isinstance(sm, unreal.StaticMesh): print('[int] missing/not static', mesh); return None
    b = sm.get_bounding_box(); e = b.max - b.min
    s = size[1] * 100.0 / max(1e-3, e.z if size[0] == 'h' else max(e.x, e.y))
    if len(size) > 2:   # turn it so its long side runs along the wanted world axis (taking the given yaw into account)
        quarter = int(round(yaw / 90.0)) % 2 == 1
        long_x = (e.x >= e.y) != quarter; want_x = size[2] == 'x'
        if long_x != want_x: yaw += 90
    z = FLOOR + dz - b.min.z * s
    a = EAS.spawn_actor_from_object(sm, unreal.Vector(x, y, z), unreal.Rotator(0, 0, yaw))
    a.set_actor_scale3d(unreal.Vector(s, s, s)); a.set_actor_label('INT_%02d_%s' % (i, mesh.split('/')[-1]))
    a.set_folder_path('Interiors/Furniture')
    c = a.get_component_by_class(unreal.StaticMeshComponent)
    if any(mesh.split('/')[-1].startswith(k) for k in SMALL): c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    if mesh.split('/')[-1] in ('Chandelier', 'CandleStick', 'Candle_1', 'CandleStick_Triple'): c.set_cast_shadow(False)   # they hang on the room lights
    return a

def run(save=True):
    removed = moved = 0
    for a in EAS.get_all_level_actors():
        lbl = a.get_actor_label(); L = a.get_actor_location()
        if L.z > -3000: continue
        if lbl.startswith('INT_'): EAS.destroy_actor(a); continue
        base = lbl.rstrip('0123456789')
        if (base in KENNEY or base in KENNEY_EXTRA) and base not in KENNEY_KEEP: EAS.destroy_actor(a); removed += 1; continue
        if base in MOVE:
            x, y = MOVE[base]; a.set_actor_location(unreal.Vector(x, y, L.z), False, False); moved += 1
    n = 0
    for i, spec in enumerate(HOME + LAB):
        if _place(spec, i): n += 1
    for a in EAS.get_all_level_actors():   # the lab's white wallpaper -> the home's wood siding
        if a.get_actor_label() == 'SM_Room_Lab':
            mi = unreal.load_asset('/Game/PBX/Materials/Inst/MI_Wallpaper_Home') or None
            if mi: a.get_component_by_class(unreal.StaticMeshComponent).set_material(2, mi)
    print('[int] removed %d Kenney pieces, moved %d, placed %d' % (removed, moved, n))
    if save: unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    return n

# camera spots for checking the rooms with pbx_capture (name, from, to) in Unreal cm
VIEWS = [('int_home_door', (-1500, 200, -5830), (-1500, 760, -5890)), ('int_home_corner', (-1080, 200, -5780), (-1800, 760, -5930)),
         ('int_lab_door', (0, 2900, -5790), (0, 3800, -5880)), ('int_lab_side', (780, 2950, -5760), (-500, 3800, -5900))]
