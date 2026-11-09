# Sigil & Spark — the realistic pass on every Ep1 set (owner 2026-11-09: "finish everything, fix every gap"): photo-scanned
# triplanar surfaces instead of the kit's painted / missing (checker) materials, a photographed sky dome over each outdoor
# stage, the old town hidden on stages (tag PBX_Town, see pbx_harbour.tag_town).
#   import pbx_allsets as A; A.run()
import unreal, importlib
import pbx_setreal as R, pbx_harbour as H, pbx_sets as S
EXTRA = [
    ('leaves', None), ('bark', None), ('grass', None), ('moss', None), ('lens', None), ('glass', None), ('glow', None),
    ('puddle', 'PUDDLE'), ('grime', 'GRIME'), ('banner', 'BANNER'), ('pageempty', 'PAGE'), ('trimcloth', 'CLOTH'), ('trimprops', ('weathered_planks', 1.2, (.66, .58, .50), 1.0)),
    ('whitestone', ('white_rough_plaster', 2.0, (1, 1, 1), 1.0)),
    ('roofred', ('red_slate_roof_tiles_01', 1.6, (1, 1, 1), 1.0)),
    ('roaddirt', ('damp_beach_sand', 3.0, (.62, .50, .38), 1.0)), ('roadrut', ('damp_beach_sand', 2.0, (.50, .40, .30), 1.0)),
    ('cliffrock', ('low_tide_rocks', 4.0, (.80, .78, .74), 1.0)), ('drystone', ('old_stone_wall', 2.0, (.85, .83, .78), 1.0)),
    ('stepstone', ('seaworn_sandstone_brick', 1.6, (.85, .84, .80), 1.0)),
    ('ceilwood', ('weathered_peeling_timber', 1.4, (.58, .50, .42), 1.0)), ('darkwood', ('weathered_peeling_timber', 1.4, (.42, .35, .28), 1.0)),
    ('doorplank', ('weathered_plank_siding', 1.2, (.62, .52, .42), 1.0)), ('doorwood', ('weathered_plank_siding', 1.2, (.62, .52, .42), 1.0)),
    ('casewood', ('worn_planks', 1.0, (.55, .42, .30), 1.0)), ('benchwood', ('worn_planks', 1.0, (.60, .48, .36), 1.0)),
    ('cratewood', ('weathered_planks', 1.0, (.70, .60, .48), 1.0)), ('postwood', ('weathered_peeling_timber', 1.0, (.55, .48, .40), 1.0)),
    ('planterwood', ('weathered_planks', 1.0, (.62, .54, .44), 1.0)),
]

def _flat(kind):
    return {'BANNER': R.flat('RealBanner', (.42, .06, .05), .7), 'PAGE': R.flat('RealPage', (.80, .74, .60), .8),
            'CLOTH': R.flat('RealCloth', (.62, .56, .48), .85),
            'PUDDLE': R.flat('RealPuddle', (.015, .017, .02), .04), 'GRIME': R.flat('RealGrime', (.05, .045, .04), .35)}[kind]

def apply_set(name):
    sm = unreal.load_asset(f'/Game/PBX/Sets/{name}/SM_Set_{name}')
    if not sm: print('[allsets] no set', name); return
    # the flat kinds the shared rule table cannot express
    for i, sl in enumerate(sm.get_editor_property('static_materials')):
        key = str(sl.get_editor_property('material_slot_name')).lower().replace('_', '')
        for k, v in EXTRA:
            if k in key and isinstance(v, str): sm.set_material(i, _flat(v)); break
    unreal.EditorAssetLibrary.save_asset(sm.get_path_name())
    R.apply(name, [(k, v) for k, v in EXTRA if not isinstance(v, str)])

def tag_stages():
    """every set actor (the set mesh, its lights, the harbour dressing, the sky domes) gets PBX_Stage_<its stage>; the game
    shows only the playing stage's actors (the sets are 300 m apart and would float on each other's horizon)"""
    EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem); n = 0
    for a in EAS.get_all_level_actors():
        if a.get_class().get_name() in ('DirectionalLight', 'SkyLight', 'SkyAtmosphere', 'VolumetricCloud', 'ExponentialHeightFog', 'PostProcessVolume'): continue
        tags = [str(x) for x in a.get_editor_property('tags')]
        if 'PBX_Town' in tags: continue
        l = a.get_actor_location()
        best = min(S.STAGES.items(), key=lambda kv: abs(l.x - kv[1][0]))
        if abs(l.x - best[1][0]) > 14000 or abs(l.y) > 40000: continue
        if a.get_actor_label() in ('Sea', 'Mountains', 'Instances'): continue
        tags = [t for t in tags if not t.startswith('PBX_Stage_')] + ['PBX_Stage_' + best[0]]
        a.set_editor_property('tags', [unreal.Name(t) for t in tags]); n += 1
    print('[allsets] stage-tagged', n)

def tag_domes():
    EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem); n = 0
    for a in EAS.get_all_level_actors():
        if a.get_actor_label().startswith('HBR_SkyDome'):
            tags = [str(x) for x in a.get_editor_property('tags')]
            if 'PBX_SkyDome' not in tags: a.set_editor_property('tags', [unreal.Name(x) for x in tags + ['PBX_SkyDome']]); n += 1
    print('[allsets] domes tagged', n)

def run():
    importlib.reload(R); importlib.reload(H)
    R.textures()
    for n in ('Pier', 'Scriptorium', 'Alley', 'Lighthouse', 'Road'): apply_set(n)
    H.tag_town(); tag_stages()
    for n in ('Alley', 'Lighthouse', 'Road', 'Scriptorium'):
        H.sky(center=unreal.Vector(*S.STAGES[n]), label='SkyDome_' + n)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    print('[allsets] done')
