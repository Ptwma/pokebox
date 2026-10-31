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
    'player_m':  ('Mateo',   0.05, 158, .25, .35, 'Hair_S_Messy', None, (.85, .62, .1)),
    'player_f':  ('Aoi',     0.95, 155, .25, .3, 'Hair_L_Straight', None, (.85, .62, .1)),
    'mom':       ('Grace',   0.9, 166, .45, .3, 'Hair_S_UpdoBuns', None, (.55, .25, .3)),
    'vale':      ('Vivian',  0.9, 171, .3, .25, 'Hair_M_BobSlick', None, (.9, .9, .92)),
    'aide':      ('Kelvin',  0.1, 178, .35, .35, 'Hair_S_SideSweptFringe', None, (.3, .45, .7)),
    'rho':       ('Trey',    0.05, 160, .2, .45, 'Hair_S_BuzzCut', None, (.15, .2, .45)),
    'fisher':    ('Walter',  0.0, 174, .55, .5, 'Hair_S_BaldingStubble', 'Beard_L_Full', (.9, .75, .1)),
    'gardener':  ('Sunita',  0.9, 163, .5, .4, 'Hair_S_LowPonytail', None, (.35, .55, .25)),
    'merchant':  ('Zuri',    0.95, 168, .4, .3, 'Hair_S_Coil', None, (.75, .35, .15)),
    'kid':       ('Omari',   0.15, 132, .2, .2, 'Hair_S_Casual', None, (.25, .6, .9)),
    'conductor': ('Jelena',  0.9, 170, .35, .35, 'Hair_S_Updo', None, (.12, .18, .35)),
    'guard':     ('Bruce',   0.0, 186, .4, .7, 'Hair_S_BrushCut', 'Beard_S_Stubble', (.3, .3, .32)),
    'crew_jon':  ('Jorge',   0.0, 180, .45, .6, 'Hair_S_Clean', 'Mustache_L_Full', (.9, .75, .1)),
    'crew_ada':  ('Ada',     1.0, 164, .35, .45, 'Hair_S_PulledBack', None, (.2, .45, .6)),
    'crew_ben':  ('Dominic', 0.0, 177, .6, .5, 'Hair_S_RecedeMessy', 'Beard_M_Curly', (.25, .3, .2)),
    'crew_old':  ('Victor',  0.0, 169, .5, .3, 'Hair_S_HairLoss', 'Beard_L_Messy', (.6, .55, .45)),
    'crew_sail': ('Lani',    0.95, 167, .25, .35, 'Hair_M_Layered', None, (.85, .85, .8)),
    'crew_kid':  ('Mikel',   0.1, 128, .15, .2, 'Hair_S_CurlyFade', None, (.85, .3, .2)),
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
    for slot, name in (('Hair', hair), ('Beard', beard)):
        wi = _groom(name) if name else None
        if not wi: continue
        try:
            k = ch.internal_collection.try_add_item_from_wardrobe_item(slot, wi)
            ch.internal_collection.default_instance.try_add_slot_selection(unreal.MetaHumanPipelineSlotSelection(slot_name=slot, selected_item=k))
        except Exception as ex: log('groom', cid, slot, ex)
    EAL.save_loaded_asset(ch); log('created', cid, 'from', preset); return ch

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
        EAS.destroy_actor(a); out[cid] = e; log('manifest', cid, e['body'] is not None, len(e['parts']), len(e['grooms']))
    path = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()) + 'PBX/Data/mh_manifest.json'
    open(path, 'w', encoding='utf-8').write(json.dumps(out, indent=1)); log('manifest ->', path)
    return out
