# Pokebox Next — off-screen screenshots with a SceneCapture2D (no viewport / window needed; works while the editor
# sits in the background). Same post process as the level (the unbound PostProcessVolume + comic blendable apply).
# Used from a queue job:  import pbx_capture; tick = pbx_capture.make_tick(views=None, frames=24)
# Files land in <Project>/Saved/pbx_shots/<view>.png
import unreal, os, math
import pbx_shots

OUT = pbx_shots.OUT
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

def _world(): return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()

def _setup(res):
    for a in EAS.get_all_level_actors():
        if a.get_actor_label() == 'PBX_Capture': EAS.destroy_actor(a)
    cap = EAS.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, 0, 500), unreal.Rotator(0, 0, 0))
    cap.set_actor_label('PBX_Capture')
    c = cap.get_component_by_class(unreal.SceneCaptureComponent2D)
    rt = unreal.RenderingLibrary.create_render_target2d(_world(), res[0], res[1], unreal.TextureRenderTargetFormat.RTF_RGBA8)
    c.set_editor_property('texture_target', rt)
    c.set_editor_property('capture_source', unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    c.set_editor_property('capture_every_frame', False)
    c.set_editor_property('always_persist_rendering_state', True)   # keeps eye adaptation / Lumen history between captures
    c.set_editor_property('fov_angle', 80.0)
    pp = c.get_editor_property('post_process_settings')
    for k, v in [('auto_exposure_speed_up', 12.0), ('auto_exposure_speed_down', 12.0)]:
        try: pp.set_editor_property('override_' + k, True); pp.set_editor_property(k, v)
        except Exception as ex: print('[cap] pp', k, ex)
    c.set_editor_property('post_process_settings', pp)
    return cap, c, rt

def make_tick(views=None, frames=24, res=(1920, 1080), delay=2.0):
    views = views or pbx_shots.VIEWS
    os.makedirs(OUT, exist_ok=True)
    cap, c, rt = _setup(res)
    st = {'i': 0, 'n': 0, 't': 0.0}
    def tick(dt):
        st['t'] += dt
        if st['t'] < delay: return False
        if st['i'] >= len(views):
            EAS.destroy_actor(cap); return True
        name, frm, to = views[st['i']]
        if st['n'] == 0:
            cap.set_actor_location_and_rotation(unreal.Vector(*frm), pbx_shots._look(frm, to), False, False)
        c.capture_scene(); st['n'] += 1
        if st['n'] >= frames:
            unreal.RenderingLibrary.export_render_target(_world(), rt, OUT, name + '.png')
            print('[cap] saved', name); st['i'] += 1; st['n'] = 0
        return False
    return tick
