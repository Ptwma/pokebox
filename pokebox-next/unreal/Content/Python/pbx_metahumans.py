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
# id: (preset face from the Optional Content, sex 0 masc..1 fem, height cm, fat, muscularity, hair groom, beard groom or None, outfit colour)
SPEC = {
    # 2026-10-31 (user: "story based ... kids close to the game's age"): the hero, the rival and the village kids are
    # 10–12 year olds (Pokémon-Red age). MetaHuman has no child body: the height floor is 135.7 cm, so kids = 136–146 cm,
    # slim, low muscle, near-neutral sex; the C++ also enlarges their head a little (KIDS → manifest "kid").
    # 2026-11-01 (user: dark adventure, blood, alone — Expedition 33 tone): the hero (Rook / Vesna) and Rho are 16 now
    'player_m':  ('Mateo',   0.0, 168, -.3, -.2, 'Hair_S_Messy', None, (.85, .62, .1)),
    'player_f':  ('Aoi',     0.7, 163, -.3, -.4, 'Hair_L_Straight', None, (.85, .62, .1)),
    'mom':       ('Grace',   0.9, 166, .45, .3, 'Hair_S_UpdoBuns', None, (.55, .25, .3)),
    'vale':      ('Vivian',  0.9, 171, .3, .25, 'Hair_M_BobSlick', None, (.9, .9, .92)),
    'aide':      ('Kelvin',  0.1, 178, .35, .35, 'Hair_S_SideSweptFringe', None, (.3, .45, .7)),
    'rho':       ('Trey',    0.0, 172, -.2, -.1, 'Hair_S_Messy', None, (.15, .2, .45)),   # BuzzCut built no hair cards
    'fisher':    ('Walter',  0.0, 174, .55, .5, 'Hair_S_BaldingStubble', 'Beard_L_Full', (.9, .75, .1)),
    'gardener':  ('Sunita',  0.9, 163, .5, .4, 'Hair_S_LowPonytail', None, (.35, .55, .25)),
    'merchant':  ('Zuri',    0.95, 168, .4, .3, 'Hair_S_Coil', None, (.75, .35, .15)),
    'kid':       ('Omari',   0.0, 136, -.4, -.8, 'Hair_S_Casual', None, (.25, .6, .9)),
    'conductor': ('Jelena',  0.9, 170, .35, .35, 'Hair_S_Updo', None, (.12, .18, .35)),
    'guard':     ('Bruce',   0.0, 186, .4, .7, 'Hair_S_BrushCut', 'Beard_S_Stubble', (.3, .3, .32)),
    'crew_jon':  ('Jorge',   0.0, 180, .45, .6, 'Hair_S_Clean', 'Mustache_L_Full', (.9, .75, .1)),
    'crew_ada':  ('Ada',     1.0, 164, .35, .45, 'Hair_S_PulledBack', None, (.2, .45, .6)),
    'crew_ben':  ('Dominic', 0.0, 177, .6, .5, 'Hair_S_RecedeMessy', 'Beard_M_Curly', (.25, .3, .2)),
    'crew_old':  ('Victor',  0.0, 169, .5, .3, 'Hair_S_HairLoss', 'Beard_L_Messy', (.6, .55, .45)),
    'crew_sail': ('Lani',    0.95, 167, .25, .35, 'Hair_M_Layered', None, (.85, .85, .8)),
    'crew_kid':  ('Mikel',   0.0, 136, -.4, -.8, 'Hair_S_CurlyFade', None, (.85, .3, .2)),
}
# r65 (user 2026-11-01: "why am I black? I see no other colour"): four looks per hero — the same face, four skin tones
# (MetaHuman skin u = melanin, v = undertone) and matching hair colours. Picked on the "Your look" screen after gender.
for _i, (_u, _v, _hc) in enumerate(((0.18, 0.45, (.20, .11, .05)), (0.34, 0.55, (.03, .02, .015)), (0.52, 0.62, (.05, .03, .02))), start=2):
    SPEC[f'player_m{_i}'] = SPEC['player_m']
SKIN = {'player_m2': (0.18, 0.45), 'player_m3': (0.34, 0.55), 'player_m4': (0.52, 0.62),
        'player_f2': (0.18, 0.45), 'player_f3': (0.55, 0.62), 'player_f4': (0.82, 0.85)}
for _c in ('player_f2', 'player_f3', 'player_f4'): SPEC[_c] = SPEC['player_f']
KIDS = {'kid', 'crew_kid'}   # 2026-11-01: hero + rival are 16
# hair colour for the hair CARDS material (the MetaHuman hair shader only draws through the groom renderer — r61)
HAIR_COLOR = {'player_m': (.05, .03, .02), 'player_f': (.02, .015, .012), 'mom': (.09, .05, .03), 'vale': (.55, .42, .28),
              'aide': (.04, .03, .02), 'rho': (.02, .015, .01), 'fisher': (.55, .55, .55), 'gardener': (.03, .02, .015),
              'merchant': (.02, .015, .01), 'kid': (.03, .02, .015), 'conductor': (.25, .12, .05), 'guard': (.12, .08, .05),
              'crew_jon': (.08, .05, .03), 'crew_ada': (.20, .10, .04), 'crew_ben': (.06, .04, .03), 'crew_old': (.75, .75, .74),
              'crew_sail': (.62, .48, .30), 'crew_kid': (.04, .03, .02)}
HAIR_COLOR.update({'player_m2': (.20, .11, .05), 'player_m3': (.03, .02, .015), 'player_m4': (.05, .03, .02),
                   'player_f2': (.25, .08, .03), 'player_f3': (.02, .015, .012), 'player_f4': (.02, .015, .012)})

class builtins_flag: done = False
HAIR_DEFAULT_TEX = '/MetaHumanCharacter/Optional/Grooms/GroomAssets/Hair/Hair_S_Messy/Hair_S_Messy_RootUVSeedCoverage'

def blanked_material():
    """M_PBX_Blanked: the overlay for people the Blanking took — translucent chalk white, a little brighter at the rim"""
    path = '/Game/PBX/Materials/M_PBX_Blanked'
    MEL = unreal.MaterialEditingLibrary
    if EAL.does_asset_exist(path):
        m = unreal.load_asset(path)
        if not m.get_editor_property('used_with_skeletal_mesh'):   # r62: without the flag → "Default Material will be used in game" (no white)
            m.set_editor_property('used_with_skeletal_mesh', True); MEL.recompile_material(m); EAL.save_loaded_asset(m); log('blanked: skeletal usage set')
        return m
    m = unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_PBX_Blanked', '/Game/PBX/Materials', unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
    m.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property('used_with_skeletal_mesh', True)
    fr = MEL.create_material_expression(m, unreal.MaterialExpressionFresnel, -600, 100)
    op = MEL.create_material_expression(m, unreal.MaterialExpressionLinearInterpolate, -300, 100)
    op.set_editor_property('const_a', .78); op.set_editor_property('const_b', .95)
    MEL.connect_material_expressions(fr, '', op, 'Alpha')
    col = MEL.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, -600, -150)
    col.set_editor_property('constant', unreal.LinearColor(.82, .82, .86, 1))
    MEL.connect_material_property(col, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    MEL.connect_material_property(op, '', unreal.MaterialProperty.MP_OPACITY)
    MEL.recompile_material(m); EAL.save_loaded_asset(m); log('blanked material')
    return m

def hair_master():
    """M_PBX_HairCards: masked, two-sided, coverage from the groom's RooUVSeedCoverage atlas (alpha), colour per character"""
    import pbx_build as B
    path = '/Game/PBX/Materials/M_PBX_HairCards'
    MEL = unreal.MaterialEditingLibrary
    if EAL.does_asset_exist(path):
        m = unreal.load_asset(path)
        if not getattr(builtins_flag, 'done', False):   # r61: the atlas is TC_MASKS → the sampler must be Masks (LinearColor = compile error → grey default material)
            for e in MEL.get_material_expressions(m) if hasattr(MEL, 'get_material_expressions') else []:
                if isinstance(e, unreal.MaterialExpressionTextureSampleParameter2D):
                    e.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
                    e.set_editor_property('texture', unreal.load_asset(HAIR_DEFAULT_TEX))   # a Masks default (the engine default is Color → compile error)
            MEL.recompile_material(m); EAL.save_loaded_asset(m); builtins_flag.done = True
        return m
    m = unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_PBX_HairCards', '/Game/PBX/Materials', unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property('blend_mode', unreal.BlendMode.BLEND_MASKED); m.set_editor_property('two_sided', True)
    m.set_editor_property('opacity_mask_clip_value', .35)
    t = MEL.create_material_expression(m, unreal.MaterialExpressionTextureSampleParameter2D, -700, 0)
    t.set_editor_property('parameter_name', 'Coverage'); t.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_MASKS); t.set_editor_property('texture', unreal.load_asset(HAIR_DEFAULT_TEX))
    c = MEL.create_material_expression(m, unreal.MaterialExpressionVectorParameter, -700, -250)
    c.set_editor_property('parameter_name', 'HairColor'); c.set_editor_property('default_value', unreal.LinearColor(.05, .03, .02, 1))
    var = MEL.create_material_expression(m, unreal.MaterialExpressionLinearInterpolate, -400, -200)
    var.set_editor_property('const_a', .7); var.set_editor_property('const_b', 1.25)
    MEL.connect_material_expressions(t, 'B', var, 'Alpha')            # seed → strand-to-strand variation
    mul = MEL.create_material_expression(m, unreal.MaterialExpressionMultiply, -200, -220)
    MEL.connect_material_expressions(c, '', mul, 'A'); MEL.connect_material_expressions(var, '', mul, 'B')
    MEL.connect_material_property(mul, '', unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(t, 'A', unreal.MaterialProperty.MP_OPACITY_MASK)
    r = MEL.create_material_expression(m, unreal.MaterialExpressionConstant, -200, 100); r.set_editor_property('r', .5)
    MEL.connect_material_property(r, '', unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.recompile_material(m); EAL.save_loaded_asset(m); log('hair master instr', MEL.get_statistics(m).num_pixel_shader_instructions)
    return m

def hair_mi(cid, groom_name):
    """MI_HairCards_<cid>_<groom>: the master with that groom's coverage atlas and the character's hair colour"""
    # the atlas is spelled RootUV... (built / plugin) or RooUV... (some Common copies): look in the character's build first
    cov = None
    for root in (f'/Game/PBX/MH/Built/MH_{cid}/Grooms', '/Game/PBX/MH/Common/Optional/Grooms', '/MetaHumanCharacter/Optional/Grooms'):
        if not EAL.does_directory_exist(root): continue
        cov = next((p.split('.')[0] for p in EAL.list_assets(root, recursive=True)
                    if p.split('/')[-1].split('.')[0] in (f'{groom_name}_RootUVSeedCoverage', f'{groom_name}_RooUVSeedCoverage')), None)
        if cov: break
    if not cov: log('no coverage atlas', groom_name); return ''
    path = f'/Game/PBX/MH/HairCards/MI_HairCards_{cid}_{groom_name}'
    mi = unreal.load_asset(path) if EAL.does_asset_exist(path) else unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        path.split('/')[-1], '/Game/PBX/MH/HairCards', unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL = unreal.MaterialEditingLibrary
    mi.set_editor_property('parent', hair_master())
    MEL.set_material_instance_texture_parameter_value(mi, 'Coverage', unreal.load_asset(cov))
    col = HAIR_COLOR.get(cid, (.05, .03, .02)) if groom_name.startswith('Hair') else tuple(min(1, x * 1.1) for x in HAIR_COLOR.get(cid, (.05, .03, .02)))
    MEL.set_material_instance_vector_parameter_value(mi, 'HairColor', unreal.LinearColor(col[0], col[1], col[2], 1))
    MEL.update_material_instance(mi); EAL.save_loaded_asset(mi)
    return path

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

def _groom(name):
    hit = [p.split('.')[0] for p in EAL.list_assets('/MetaHumanCharacter/Optional/Grooms', recursive=True) if p.split('/')[-1].split('.')[0] == 'WI_' + name]
    return unreal.load_asset(hit[0]) if hit else None

def create(cid):
    # 2026-10-31: commit_skin_settings without the Optional Content CRASHES the editor (assert BodyTexture) → refuse early
    if not _has_optional(): log('Optional Content not installed (Epic Launcher > UE 5.8 > Options) — nothing created'); return None
    preset, sex, h, fat, mus, hair, beard, col = SPEC[cid]
    full = f'{ROOT}/Characters/MH_{cid}'
    if EAL.does_asset_exist(full): EAL.delete_asset(full)
    ch = EAL.duplicate_asset(f'/MetaHumanCharacter/Optional/Presets/{preset}', full)     # an Epic preset face (real, varied)
    if not ch: log('preset missing', preset); return None
    s = S()
    if not s.try_add_object_to_edit(ch): log('busy', cid); return None
    try:
        cons = s.get_body_constraints(ch); m = {str(c.name).lower().replace(' ', '_'): c for c in cons}
        for k, v in (('height', h), ('masculine/feminine', sex), ('fat', fat), ('muscularity', mus)):
            if k in m: m[k].is_active = True; m[k].target_measurement = float(v)
        s.set_body_constraints(ch, list(m.values())); s.commit_body_state(ch)
    finally:
        if s.is_object_added_for_editing(ch): s.remove_object_to_edit(ch)
    try: _set_grooms(ch, cid)
    except Exception as ex: log('groom', cid, ex)
    if cid in SKIN: set_skin(ch, *SKIN[cid])
    EAL.save_loaded_asset(ch); log('created', cid, 'from', preset); return ch

def set_skin(ch, u, v):
    """skin tone on a (not yet rigged) character: MetaHuman skin u = melanin, v = undertone"""
    s = S()
    if not s.try_add_object_to_edit(ch): log('busy (skin)'); return False
    try:
        ss = ch.get_editor_property('skin_settings'); sk = ss.skin; sk.u = float(u); sk.v = float(v); ss.skin = sk
        s.commit_skin_settings(ch, ss); log('skin', ch.get_name(), u, v)
    finally:
        if s.is_object_added_for_editing(ch): s.remove_object_to_edit(ch)
    return True

def looks():
    """r65: create + rig + texture + build the hero looks that don't exist yet (one at a time, saved after each)"""
    for cid in [c for c in SKIN if not is_built(c)]:
        try:
            if not EAL.does_asset_exist(f'{ROOT}/Characters/MH_{cid}'): create(cid)
            build_save(cid)
        except Exception as ex: log('look FAILED', cid, ex)
    log('looks pending', [c for c in SKIN if not is_built(c)])

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

def textures(cid):
    """download the face/body texture sources from MetaHuman Cloud at 2K (smallest: the RTX 2060 has 6 GB)"""
    ch = unreal.load_asset(f'{ROOT}/Characters/MH_{cid}'); s = S()
    if not ch or not s.try_add_object_to_edit(ch): return
    try:
        try:
            r = ch.get_editor_property('texture_source_resolutions')
            for k in ('face_albedo', 'face_normal', 'face_cavity', 'face_animated_maps', 'body_albedo', 'body_normal', 'body_cavity', 'body_masks'):
                r.set_editor_property(k, unreal.RequestTextureResolution.RES2K)
            ch.set_editor_property('texture_source_resolutions', r)
        except Exception as ex: log('resolution default', ex)
        t = unreal.MetaHumanCharacterTextureRequestParams(); t.blocking = True; t.report_progress = False
        s.request_texture_sources(ch, t); log('textures', cid)
    finally:
        if s.is_object_added_for_editing(ch): s.remove_object_to_edit(ch)
    EAL.save_loaded_asset(ch)

def rig_all():
    for cid in SPEC: rig(cid); textures(cid)

def build(cid):
    ch = unreal.load_asset(f'{ROOT}/Characters/MH_{cid}'); s = S()
    if not ch or not s.try_add_object_to_edit(ch): return
    try:
        b = unreal.MetaHumanCharacterEditorBuildParameters()
        b.pipeline_type = unreal.MetaHumanDefaultPipelineType.OPTIMIZED; b.pipeline_quality = unreal.MetaHumanQualityLevel.LOW
        b.absolute_build_path = f'{ROOT}/Built'; b.common_folder_path = f'{ROOT}/Common'; b.enable_wardrobe_item_validation = False
        try: s.build_meta_human(character=ch, params=b)
        except SystemError as ex: log('build returned without a result (the Control Rig copy warnings) — checking the output', cid)
        ok = EAL.does_asset_exist(f'{ROOT}/Built/MH_{cid}/BP_MH_{cid}')
        log('built' if ok else 'BUILD FAILED', cid)
    finally:
        if s.is_object_added_for_editing(ch): s.remove_object_to_edit(ch)

def build_all():
    for cid in SPEC: build(cid)

def is_built(cid): return EAL.does_asset_exist(f'{ROOT}/Built/MH_{cid}/BP_MH_{cid}')
def pending(): return [c for c in SPEC if not is_built(c)]

def _ram():
    import ctypes
    class M(ctypes.Structure):
        _fields_ = [('l', ctypes.c_ulong), ('load', ctypes.c_ulong), ('tot', ctypes.c_ulonglong), ('avail', ctypes.c_ulonglong),
                    ('tp', ctypes.c_ulonglong), ('ap', ctypes.c_ulonglong), ('tv', ctypes.c_ulonglong), ('av', ctypes.c_ulonglong), ('x', ctypes.c_ulonglong)]
    m = M(); m.l = ctypes.sizeof(M); ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return round(m.avail / 2**30, 1), round(m.ap / 2**30, 1)   # free physical GB, free commit GB

def cap_textures(cid, size=2048):
    """the build writes 8K virtual-texture body maps — cap them (RTX 2060, 6 GB)"""
    n = 0
    for a in EAL.list_assets(f'{ROOT}/Built/MH_{cid}', recursive=True, include_folder=False):
        d = EAL.find_asset_data(a)
        if str(d.asset_class_path.asset_name) != 'Texture2D': continue
        t = d.get_asset()
        if t.get_editor_property('max_texture_size') != size: t.set_editor_property('max_texture_size', size); n += 1
    log('capped', cid, n)

def build_save(cid):
    """one character end to end, then write it to disk and free it — r58 lesson: 16 unsaved builds = out-of-memory crash"""
    if is_built(cid): log('already built', cid); return True
    import os
    sz = os.path.getsize(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()) + f'PBX/MH/Characters/MH_{cid}.uasset')
    if sz < 40e6: rig(cid); textures(cid)          # not yet rigged / textured (≈10 MB → ≈110 MB once done)
    build(cid)
    ok = is_built(cid)
    if ok:
        try: cap_textures(cid)
        except Exception as ex: log('cap failed', cid, ex)
    save_all(); unreal.SystemLibrary.collect_garbage(); log('ram free', cid, _ram())
    return ok

def next_builds(n=1):
    """build the next n pending characters (one queue job per call, so a crash loses at most one)"""
    for cid in pending()[:n]:
        try: build_save(cid)
        except Exception as ex: log('FAILED', cid, ex)
    log('pending', len(pending()), pending())

def _set_grooms(ch, cid):
    """the Epic presets ship their own hair/beard/mustache: REPLACE every facial-hair slot (r59 bug: the old create()
    only added a 2nd Hair item → the preset's beard stayed on the girl and the kids, and two Hair picks built no hair)"""
    _, _, _, _, _, hair, beard, _ = SPEC[cid]
    col = ch.internal_collection; inst = col.default_instance
    want = {'Hair': hair, 'Beard': None, 'Mustache': None}
    if beard: want['Mustache' if beard.startswith('Mustache') else 'Beard'] = beard
    for slot, name in want.items():
        key = unreal.MetaHumanPaletteItemKey()          # empty key = nothing in this slot
        if name:
            wi = _groom(name)
            if not wi: log('groom missing', cid, name); continue
            keys = [k for k in col.get_item_keys_for_wardrobe_item(wi) if str(col.get_item_slot_name(k)) == slot]
            key = keys[0] if keys else col.try_add_item_from_wardrobe_item(slot, wi)
        inst.set_single_slot_selection(slot, key)
    log('grooms', cid, want)

def restyle(cid):
    """body (height / fat / muscle / sex) + facial hair on the EXISTING character (keeps the rig and the textures)"""
    ch = unreal.load_asset(f'{ROOT}/Characters/MH_{cid}'); s = S()
    _, sex, h, fat, mus, _, _, _ = SPEC[cid]
    if not s.try_add_object_to_edit(ch): log('busy', cid); return False
    try:
        cons = s.get_body_constraints(ch); m = {str(c.name).lower().replace(' ', '_'): c for c in cons}
        for k, v in (('height', h), ('masculine/feminine', sex), ('fat', fat), ('muscularity', mus)):
            if k in m: m[k].is_active = True; m[k].target_measurement = float(v)
        s.set_body_constraints(ch, list(m.values())); s.commit_body_state(ch)
    finally:
        if s.is_object_added_for_editing(ch): s.remove_object_to_edit(ch)
    _set_grooms(ch, cid)
    EAL.save_loaded_asset(ch)
    d = f'{ROOT}/Built/MH_{cid}'
    if EAL.does_directory_exist(d): EAL.delete_directory(d)     # → pending() rebuilds it
    log('restyled', cid, h); return True

def recreate(cid):
    """height / build changes do NOT reach a character that is already auto-rigged (r60: the kids kept their old
    heights) → start again from the preset: create (body + grooms), then build_save() rigs, textures and builds it"""
    d = f'{ROOT}/Built/MH_{cid}'
    if EAL.does_directory_exist(d): EAL.delete_directory(d)
    return create(cid)

def restyle_all():
    for cid in SPEC:
        try: restyle(cid)
        except Exception as ex: log('restyle FAILED', cid, ex)
    log('pending', pending())

def all_steps(skip=()):
    """rig → textures → build for every character (≈2 min each; the Epic sign-in is reused)"""
    for cid in SPEC:
        if cid in skip: continue
        try: rig(cid); textures(cid); build(cid)
        except Exception as ex: log('FAILED', cid, ex)

def save_all():
    """the build leaves its packages dirty — write them to disk"""
    for d in (f'{ROOT}/Built', f'{ROOT}/Common', f'{ROOT}/Characters'):
        if EAL.does_directory_exist(d): EAL.save_directory(d, only_if_is_dirty=True, recursive=True)
    log('saved')

def manifest():
    """Content/PBX/Data/mh_manifest.json: for every built character the meshes the C++ needs (body = the animated
    mesh, the other skeletal parts follow it through the leader pose, grooms attach to the face). Read from the
    assembled blueprint by spawning it once below the world."""
    import json
    EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem); out = {}
    for cid in SPEC:
        bp = f'{ROOT}/Built/MH_{cid}/BP_MH_{cid}'
        if not EAL.does_asset_exist(bp): log('not built', cid); continue
        a = EAS.spawn_actor_from_class(EAL.load_blueprint_class(bp), unreal.Vector(0, 0, -90000), unreal.Rotator(0, 0, 0))
        e = {'body': None, 'parts': [], 'grooms': []}
        for c in a.get_components_by_class(unreal.SkeletalMeshComponent):
            m = c.get_editor_property('skeletal_mesh_asset') if hasattr(c, 'get_skeletal_mesh_asset') or True else None
            try: m = c.get_skeletal_mesh_asset()
            except Exception: m = c.get_editor_property('skeletal_mesh')
            if not m: continue
            p = m.get_path_name().split('.')[0]; nm = c.get_name()
            if nm.lower() == 'body' or 'BodyMesh' in p: e['body'] = p
            else: e['parts'].append({'name': nm, 'mesh': p, 'face': 'FaceMesh' in p or nm.lower() == 'face'})
        for c in a.get_components_by_class(unreal.GroomComponent):
            g = c.get_editor_property('groom_asset'); b = c.get_editor_property('binding_asset')
            if g: e['grooms'].append({'name': c.get_name(), 'groom': g.get_path_name().split('.')[0], 'binding': b.get_path_name().split('.')[0] if b else '',
                                      'parent': c.get_attach_parent().get_name() if c.get_attach_parent() else ''})
        e['height'] = SPEC[cid][2]; e['kid'] = cid in KIDS
        # hair CARDS (static meshes the build makes from each groom): strand grooms never drew in -game (r60), cards do and
        # are far cheaper on the RTX 2060 → per groom the LOD1 cards meshes (all groups) + the cards material
        for g in e['grooms']:
            gd = g['groom'].rsplit('/', 1)[0]; gn = g['groom'].rsplit('/', 1)[1]; cards = []
            names = [p.split('.')[0] for p in EAL.list_assets(gd, recursive=False)]
            for lod in ('LOD1', 'LOD0', 'LOD2'):
                cards = [n for n in names if n.split('/')[-1].startswith(gn + '_CardsMesh_') and n.endswith('_' + lod)]
                if cards: break
            mat = next((n for n in names if n.split('/')[-1] == f'MI_WI_{gn}_Hair_Cards'), '') or next((n for n in names if n.endswith('_Cards') and n.split('/')[-1].startswith('MI_')), '')
            try: mat = hair_mi(cid, gn) or mat
            except Exception as ex: log('hair mi', cid, gn, ex)
            g['cards'] = [{'mesh': c, 'material': mat} for c in cards]
        EAS.destroy_actor(a); out[cid] = e; log('manifest', cid, e['body'] is not None, len(e['parts']), len(e['grooms']))
    path = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()) + 'PBX/Data/mh_manifest.json'
    open(path, 'w', encoding='utf-8').write(json.dumps(out, indent=1)); log('manifest ->', path)
    return out
