# Pokebox Next — phase 5: every character as a MetaHuman (user decision 2026-10-22, confirmed 2026-10-31).
# Needs (user actions, done once): the MetaHuman Creator Optional Content installed from the Epic Games Launcher
# (UE 5.8 > Options), and the user signed in to their Epic account when the editor asks (face auto-rigging runs in
# Epic's MetaHuman Cloud). Claude never enters credentials.
#   import pbx_metahumans as M
#   M.check()            what is installed / available (optional content, wardrobe, presets)
#   M.create_all()       create / update the MetaHumanCharacter assets from SPEC (body, skin, hair, clothes)  — local
#   M.rig_all()          cloud auto-rig (JOINTS_ONLY = the cheapest rig, enough for idle/talk; triggers the sign-in once)
#   M.build_all()        assemble OPTIMIZED / LOW quality runtime blueprints (RTX 2060 budget) into /Game/PBX/MH/Built
# Kids: MetaHuman has no child bodies → short, slim adult proportions (user's choice).
import unreal, random

ROOT = '/Game/PBX/MH'
EAL = unreal.EditorAssetLibrary
def log(*a): print('[mh]', *a)

# id: (sex 0 = masculine .. 1 = feminine, height cm, fat 0..1, muscularity 0..1, skin (u, v), hair slot keyword, outfit colour)
SPEC = {
    'player_m':  (0.05, 158, .25, .35, (.35, .45), 'Short', (.85, .62, .1)),
    'player_f':  (0.95, 155, .25, .3, (.3, .4), 'Long', (.85, .62, .1)),
    'mom':       (0.9, 166, .45, .3, (.32, .45), 'Bun', (.55, .25, .3)),
    'vale':      (0.9, 171, .3, .25, (.25, .3), 'Long', (.9, .9, .92)),
    'aide':      (0.1, 178, .35, .35, (.55, .6), 'Short', (.3, .45, .7)),
    'rho':       (0.05, 160, .2, .45, (.4, .55), 'Buzz', (.15, .2, .45)),
    'fisher':    (0.0, 174, .55, .5, (.45, .65), 'Beard', (.9, .75, .1)),
    'gardener':  (0.9, 163, .5, .4, (.6, .7), 'Bun', (.35, .55, .25)),
    'merchant':  (0.95, 168, .4, .3, (.75, .8), 'Short', (.75, .35, .15)),
    'kid':       (0.15, 132, .2, .2, (.3, .4), 'Short', (.25, .6, .9)),
    'conductor': (0.9, 170, .35, .35, (.4, .5), 'Bun', (.12, .18, .35)),
    'guard':     (0.0, 186, .4, .7, (.7, .75), 'Short', (.3, .3, .32)),
    'crew_jon':  (0.0, 180, .45, .6, (.5, .55), 'Short', (.9, .75, .1)),
    'crew_ada':  (1.0, 164, .35, .45, (.35, .5), 'Bun', (.2, .45, .6)),
    'crew_ben':  (0.0, 177, .6, .5, (.45, .6), 'Beard', (.25, .3, .2)),
    'crew_old':  (0.0, 169, .5, .3, (.3, .4), 'Beard', (.6, .55, .45)),
    'crew_sail': (0.95, 167, .25, .35, (.4, .45), 'Long', (.85, .85, .8)),
    'crew_kid':  (0.1, 128, .15, .2, (.35, .5), 'Short', (.85, .3, .2)),
}

def S(): return unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)

def check():
    import os
    opt = unreal.Paths.convert_relative_path_to_full(unreal.Paths.engine_plugins_dir()) + 'MetaHuman/MetaHumanCharacter/Content/Optional'
    log('optional content', os.path.isdir(opt))
    for k in ('Clothing', 'Grooms', 'Presets', 'TextureSynthesis'):
        log(' ', k, [p.split('.')[-1] for p in EAL.list_assets('/MetaHumanCharacter/Optional/' + k, recursive=True) if p.split('/')[-1].startswith('WI_')][:12])
    return os.path.isdir(opt)

def _wardrobe(kind, key):
    items = [p.split('.')[0] for p in EAL.list_assets('/MetaHumanCharacter/Optional/' + kind, recursive=True) if p.split('/')[-1].startswith('WI_')]
    hit = [p for p in items if key.lower() in p.lower()]
    return unreal.load_asset((hit or items or [None])[0]) if (hit or items) else None

def _has_optional():
    import os
    return os.path.isdir(unreal.Paths.convert_relative_path_to_full(unreal.Paths.engine_plugins_dir()) + 'MetaHuman/MetaHumanCharacter/Content/Optional')

def create(cid):
    # 2026-10-31: commit_skin_settings without the Optional Content CRASHES the editor (assert BodyTexture) → refuse early
    if not _has_optional(): log('Optional Content not installed (Epic Launcher > UE 5.8 > Options) — nothing created'); return None
    sex, h, fat, mus, (su, sv), hair, col = SPEC[cid]
    path = f'{ROOT}/Characters'; full = f'{path}/MH_{cid}'
    ch = unreal.load_asset(full) if EAL.does_asset_exist(full) else unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        asset_name=f'MH_{cid}', package_path=path, asset_class=unreal.MetaHumanCharacter, factory=unreal.new_object(type=unreal.MetaHumanCharacterFactoryNew))
    s = S()
    if not s.try_add_object_to_edit(ch): log('busy', cid); return None
    try:
        cons = s.get_body_constraints(ch); m = {str(c.name).lower().replace(' ', '_'): c for c in cons}
        for k, v in (('height', h), ('masculine/feminine', sex), ('fat', fat), ('muscularity', mus)):
            if k in m: m[k].is_active = True; m[k].target_measurement = float(v)
        s.set_body_constraints(ch, list(m.values())); s.commit_body_state(ch)
        # face: small seeded variation of the model coefficients, so no two neighbours share a face
        try:
            co = list(s.get_face_model_coefficients(ch)); rnd = random.Random(hash(cid) & 0xffff)
            co = [c + rnd.gauss(0, .35) for c in co]; s.set_face_model_coefficients(ch, co); s.commit_face_state(ch)
        except Exception as ex: log('face variation skipped', cid, ex)
        try:
            sk = unreal.MetaHumanCharacterSkinSettings(); p = unreal.MetaHumanCharacterSkinProperties(); p.u = su; p.v = sv; p.roughness = .8
            sk.skin = p; s.commit_skin_settings(character=ch, skin_settings=sk)
        except Exception as ex: log('skin skipped', cid, ex)
    finally:
        if s.is_object_added_for_editing(ch): s.remove_object_to_edit(ch)
    for slot, kind, key in (('Hair', 'Grooms', hair), ('Outfits', 'Clothing', 'Garment')):
        wi = _wardrobe(kind, key)
        if wi:
            try:
                k = ch.internal_collection.try_add_item_from_wardrobe_item(slot, wi)
                ch.internal_collection.default_instance.try_add_slot_selection(unreal.MetaHumanPipelineSlotSelection(slot_name=slot, selected_item=k))
            except Exception as ex: log('wardrobe', cid, slot, ex)
    EAL.save_loaded_asset(ch); log('created', cid); return ch

def create_all():
    for cid in SPEC: create(cid)

def rig(cid):
    ch = unreal.load_asset(f'{ROOT}/Characters/MH_{cid}'); s = S()
    if not ch or not s.try_add_object_to_edit(ch): return
    try:
        r = unreal.MetaHumanCharacterAutoRiggingRequestParams(); r.blocking = True; r.report_progress = False
        r.rig_type = unreal.MetaHumanRigType.JOINTS_ONLY
        s.request_auto_rigging(ch, r); log('rigged', cid)
    finally:
        if s.is_object_added_for_editing(ch): s.remove_object_to_edit(ch)
    EAL.save_loaded_asset(ch)

def rig_all():
    for cid in SPEC: rig(cid)

def build(cid):
    ch = unreal.load_asset(f'{ROOT}/Characters/MH_{cid}'); s = S()
    if not ch or not s.try_add_object_to_edit(ch): return
    try:
        b = unreal.MetaHumanCharacterEditorBuildParameters()
        b.pipeline_type = unreal.MetaHumanDefaultPipelineType.OPTIMIZED; b.pipeline_quality = unreal.MetaHumanQualityLevel.LOW
        b.absolute_build_path = f'{ROOT}/Built'; b.common_folder_path = f'{ROOT}/Common'; b.enable_wardrobe_item_validation = False
        s.build_meta_human(character=ch, params=b); log('built', cid)
    finally:
        if s.is_object_added_for_editing(ch): s.remove_object_to_edit(ch)

def build_all():
    for cid in SPEC: build(cid)
