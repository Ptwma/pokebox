# Sigil & Spark intro — Unreal FX plates (user 2026-11-01: "use Unreal for the effects").
# Each clip = one small studio level (black backdrop for light FX → composited with ADD/SCREEN; white backdrop for
# blood / dark goo → composited with MULTIPLY), a CineCamera, a LevelSequence, rendered with Movie Render Queue to PNG.
#   import pbx_fxclips as X; X.build_all(); X.render_all()    → PokeboxNext_src/intro_render/ue_fx/<clip>/####.png
import unreal, os, math

EAL = unreal.EditorAssetLibrary
SRC = r"E:\GAME-APP-DEV\POKEMON\PokeboxNext_src"
OUTDIR = os.path.join(SRC, 'intro_render', 'ue_fx')
ROOT = '/Game/PBX/Intro/FX'
def log(*a): print('[fx]', *a)

# clip: (niagara system, frames @24, camera distance cm, camera height, backdrop, exposure bias, scale)
CLIPS = {
    'explosion':  ('/Game/NiagaraExamples/FX_Explosions/NS_Explosion', 60, 1400, 300, 'black', 0.0, 1.0),
    'fire':       ('/Game/NiagaraExamples/FX_Misc/NS_Fire', 72, 230, 110, 'black', 0.5, 1.0),
    'sparks':     ('/Game/NiagaraExamples/FX_Sparks/NS_Spark_Burst', 48, 260, 40, 'black', 1.0, 1.0),
    'electric':   ('/Game/NiagaraExamples/FX_Ribbons/NS_TeslaCoil', 72, 700, 200, 'black', 0.0, 1.0),
    'firework':   ('/Game/NiagaraExamples/FX_Misc/NS_FireworkBurst', 60, 1300, 700, 'black', 2.0, 1.0),
    'blood':      ('/Game/Vefects/VFX_Free_Blood/VFX/Particles/Once/NS_Blood_Splat_Directional_01_Floor_Bunch_Once', 48, 260, 160, 'white', 0.0, 1.0),
    'ink_burst':  ('/Game/Vefects/Tentacles_VFX/VFX/Goo/Particles/NS_Goo_Explode_Dark', 48, 500, 120, 'white', 0.0, 1.0),
    'ink_rise':   ('/Game/Vefects/Tentacles_VFX/VFX/Goo/Particles/NS_Goo_Up_Dark', 72, 500, 150, 'white', 0.0, 1.0),
}

TOPDOWN = {'blood', 'ink_burst'}

def _white_mat():
    p = f'{ROOT}/M_FXWhite'
    if EAL.does_asset_exist(p): return unreal.load_asset(p)
    MEL = unreal.MaterialEditingLibrary
    m = unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_FXWhite', ROOT, unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    c = MEL.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, -300, 0); c.set_editor_property('constant', unreal.LinearColor(1, 1, 1, 1))
    MEL.connect_material_property(c, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    MEL.recompile_material(m); EAL.save_loaded_asset(m)
    return m

def build_clip(name):
    sysp, frames, dist, h, bg, bias, scale = CLIPS[name]
    lvl = f'{ROOT}/L_FX_{name}'
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if EAL.does_asset_exist(lvl): EAL.delete_asset(lvl)
    les.new_level(lvl)
    world = unreal.EditorLevelLibrary.get_editor_world()
    for a in unreal.EditorLevelLibrary.get_all_level_actors():   # the new-level template ships a floor / sky / lights → a clean black studio
        if not isinstance(a, (unreal.WorldSettings,)) and a.get_class().get_name() not in ('WorldSettings', 'Brush', 'DefaultPhysicsVolume'): unreal.EditorLevelLibrary.destroy_actor(a)
    ns = unreal.load_asset(sysp)
    na = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.NiagaraActor, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
    nc = na.get_editor_property('niagara_component') if hasattr(na, 'get_editor_property') else None
    nc = nc or na.get_component_by_class(unreal.NiagaraComponent)
    nc.set_editor_property('asset', ns); nc.set_editor_property('auto_activate', True); nc.set_asset(ns); na.set_actor_scale3d(unreal.Vector(scale, scale, scale))
    look = unreal.Vector(0, 0, h * 0.5)
    camloc = unreal.Vector(-dist, 0, h)
    if name in TOPDOWN: camloc = unreal.Vector(-dist * 0.15, 0, dist); look = unreal.Vector(0, 0, 0)
    cam = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.CineCameraActor, camloc, unreal.MathLibrary.find_look_at_rotation(camloc, look))
    cc = cam.get_cine_camera_component()
    fs = cc.get_editor_property('focus_settings'); fs.set_editor_property('focus_method', unreal.CameraFocusMethod.DISABLE); cc.set_editor_property('focus_settings', fs)
    pp = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
    pp.set_editor_property('unbound', True)
    s = pp.get_editor_property('settings')
    s.set_editor_property('override_auto_exposure_method', True); s.set_editor_property('auto_exposure_method', unreal.AutoExposureMethod.AEM_MANUAL)
    s.set_editor_property('override_auto_exposure_bias', True); s.set_editor_property('auto_exposure_bias', bias)
    s.set_editor_property('override_auto_exposure_apply_physical_camera_exposure', True); s.set_editor_property('auto_exposure_apply_physical_camera_exposure', False)
    s.set_editor_property('override_bloom_intensity', True); s.set_editor_property('bloom_intensity', 0.6)
    s.set_editor_property('override_vignette_intensity', True); s.set_editor_property('vignette_intensity', 0.0)
    pp.set_editor_property('settings', s)
    if bg == 'white':
        pl = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(dist * 2.5, 0, 0), unreal.Rotator(0, 90, 90))
        smc = pl.static_mesh_component; smc.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Plane')); pl.set_actor_scale3d(unreal.Vector(400, 400, 1))
        smc.set_material(0, _white_mat())
        fl = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, -2), unreal.Rotator(0, 0, 0))
        fl.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Plane')); fl.set_actor_scale3d(unreal.Vector(400, 400, 1)); fl.static_mesh_component.set_material(0, _white_mat())
        unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 500), unreal.Rotator(-50, 30, 0))
        unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 300), unreal.Rotator(0, 0, 0))
    # the sequence: camera cut on our camera
    sp = f'{ROOT}/SEQ_FX_{name}'
    if EAL.does_asset_exist(sp): EAL.delete_asset(sp)
    seq = unreal.AssetToolsHelpers.get_asset_tools().create_asset(f'SEQ_FX_{name}', ROOT, unreal.LevelSequence, unreal.LevelSequenceFactoryNew())
    seq.set_display_rate(unreal.FrameRate(24, 1)); seq.set_tick_resolution(unreal.FrameRate(24000, 1))
    seq.set_playback_start(0); seq.set_playback_end(frames)
    b = seq.add_possessable(cam)
    ct = seq.add_track(unreal.MovieSceneCameraCutTrack); sec = ct.add_section(); sec.set_range(0, frames)
    bid = unreal.MovieSceneObjectBindingID(); bid.set_editor_property('guid', b.get_id())
    sec.set_camera_binding_id(bid)
    EAL.save_loaded_asset(seq)
    les.save_current_level()
    log('built', name, lvl, sp)
    return lvl, sp

def build_all(names=None):
    return [build_clip(n) for n in (names or CLIPS)]

def render_all(names=None, res=(1600, 900)):
    subsys = unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem)
    q = subsys.get_queue()
    for j in list(q.get_jobs()): q.delete_job(j)
    for n in (names or CLIPS):
        job = q.allocate_new_job(unreal.MoviePipelineExecutorJob)
        job.set_editor_property('job_name', n)
        job.set_editor_property('sequence', unreal.SoftObjectPath(f'{ROOT}/SEQ_FX_{n}.SEQ_FX_{n}'))
        job.set_editor_property('map', unreal.SoftObjectPath(f'{ROOT}/L_FX_{n}.L_FX_{n}'))
        cfg = job.get_configuration()
        o = cfg.find_or_add_setting_by_class(unreal.MoviePipelineOutputSetting)
        d = unreal.DirectoryPath(); d.set_editor_property('path', os.path.join(OUTDIR, n)); o.set_editor_property('output_directory', d)
        o.set_editor_property('output_resolution', unreal.IntPoint(*res)); o.set_editor_property('file_name_format', '{frame_number}')
        o.set_editor_property('zero_pad_frame_numbers', 4)
        cfg.find_or_add_setting_by_class(unreal.MoviePipelineDeferredPassBase)
        cfg.find_or_add_setting_by_class(unreal.MoviePipelineImageSequenceOutput_PNG)
        aa = cfg.find_or_add_setting_by_class(unreal.MoviePipelineAntiAliasingSetting)
        aa.set_editor_property('spatial_sample_count', 2); aa.set_editor_property('temporal_sample_count', 2)
        aa.set_editor_property('render_warm_up_count', 0); aa.set_editor_property('engine_warm_up_count', 0)
    subsys.render_queue_with_executor(unreal.MoviePipelinePIEExecutor)
    log('MRQ started', len(q.get_jobs()), 'jobs ->', OUTDIR)
