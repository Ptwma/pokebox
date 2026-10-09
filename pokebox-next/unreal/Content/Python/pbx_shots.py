# Pokebox Next — screenshots of the town from fixed camera spots, taken inside the running editor (no screen access needed).
# Used from a queue job:  import pbx_shots; tick = pbx_shots.make_tick(delay=60)
# Files land in <Project>/Saved/pbx_shots/<view>.png
import unreal, os, math, glob, shutil, time

OUT = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), 'pbx_shots')
SHOTDIR = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), 'Screenshots')

def _look(frm, to):
    dx, dy, dz = to[0] - frm[0], to[1] - frm[1], to[2] - frm[2]
    yaw = math.degrees(math.atan2(dy, dx)); pitch = math.degrees(math.atan2(dz, math.hypot(dx, dy)))
    return unreal.Rotator(roll=0.0, pitch=pitch, yaw=yaw)

def ue(x, y, z): return (x * 100.0, -y * 100.0, z * 100.0)   # Blender metres -> Unreal cm

# (name, camera position, look-at point) in Blender town coordinates (metres)
VIEWS = [
    ('street', ue(3, 16, 1.8), ue(-1, -30, 2.5)),
    ('house', ue(-9.5, 5.5, 1.7), ue(-15, -3, 2.6)),
    ('lab', ue(7, -14, 1.9), ue(0, -32, 4.0)),
    ('beach', ue(12, 36, 2.2), ue(-12, 70, 0.0)),
    ('garden', ue(-21, 9, 1.4), ue(-12, -2, 1.5)),
    ('overview', ue(42, 34, 20), ue(0, -12, 0)),
]

def _prep():
    try: unreal.get_default_object(unreal.EditorPerformanceSettings).set_editor_property('throttle_cpu_when_not_foreground', False)
    except Exception as ex: print('[shots] throttle', ex)
    try: unreal.EditorLevelLibrary.editor_set_game_view(True)
    except Exception as ex: print('[shots] game view', ex)
    for c in ('r.ScreenPercentage 100', 'ShowFlag.Grid 0'):
        unreal.SystemLibrary.execute_console_command(None, c)
    os.makedirs(OUT, exist_ok=True)

def make_tick(delay=45.0, settle=6.0, views=None, res=(1920, 1080)):
    views = views or VIEWS
    st = {'t': 0.0, 'i': -1, 'phase': 'wait', 'since': 0.0, 'before': set()}
    ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    _prep()
    def tick(dt):
        st['t'] += dt; st['since'] += dt
        if st['phase'] == 'wait':
            if st['t'] < delay: return False
            st['phase'] = 'move'; st['i'] = 0
        if st['i'] >= len(views): return True
        name, frm, to = views[st['i']]
        if st['phase'] == 'move':
            ues.set_level_viewport_camera_info(unreal.Vector(*frm), _look(frm, to))
            st['phase'] = 'settle'; st['since'] = 0.0; return False
        if st['phase'] == 'settle' and st['since'] >= settle:
            st['before'] = set(glob.glob(os.path.join(SHOTDIR, '**', '*.png'), recursive=True))
            unreal.SystemLibrary.execute_console_command(None, 'HighResShot %dx%d' % res)
            st['phase'] = 'grab'; st['since'] = 0.0; return False
        if st['phase'] == 'grab':
            new = [p for p in glob.glob(os.path.join(SHOTDIR, '**', '*.png'), recursive=True) if p not in st['before']]
            if new:
                time.sleep(0.3); shutil.copy(max(new, key=os.path.getmtime), os.path.join(OUT, name + '.png'))
                print('[shots] saved', name); st['i'] += 1; st['phase'] = 'move'
            elif st['since'] > 40: print('[shots] no file for', name); st['i'] += 1; st['phase'] = 'move'
        return False
    return tick
