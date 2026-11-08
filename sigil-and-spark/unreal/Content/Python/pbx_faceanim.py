# Sigil & Spark — MetaHuman Animator audio-driven faces for every spoken line (FA_<vo id> on the MetaHuman face skeleton).
# Resumable and non-blocking: start() registers a slate tick that converts ONE line per tick (~24 s each), so the editor stays
# alive between lines and a crash/shutdown loses at most one line. Skips narrator/codex/spark lines and lines already done.
#   import pbx_faceanim; pbx_faceanim.start()        status: Saved/pbx_faceanim.log ('ALLDONE n' at the end)
import unreal, os, json, time

PRJ = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
SRC = os.path.normpath(os.path.join(PRJ, '..', 'SigilAndSpark_src'))
VO = os.path.join(PRJ, 'Content', 'PBX', 'StoryAudio', 'vo')
LOG = os.path.join(PRJ, 'Saved', 'pbx_faceanim.log')
SKIP_WHO = ('narrator', 'codex', 'spark', '?')
_state = {'todo': None, 'h': None, 'n': 0, 't0': 0.0, 'lines': None, 'busy': False}

def _log(s):
    with open(LOG, 'a', encoding='utf-8') as f: f.write(s + '\n')

def _todo():
    EAL = unreal.EditorAssetLibrary
    lines = {l['id']: l for l in json.load(open(os.path.join(SRC, 'tools', 'story', 'out', 'ep1_lines.json'), encoding='utf-8'))}
    out = []
    for f in sorted(os.listdir(VO)):
        if not f.endswith('.wav'): continue
        name = f[:-4]; base = name
        for suf in ('_m', '_f', '_p1', '_p2', '_p3'):
            if base.endswith(suf): base = base[:-len(suf)]
        who = lines.get(base, {}).get('who', '?')
        if who in SKIP_WHO: continue
        if EAL.does_asset_exist('/Game/PBX/Story/FaceAnim/FA_' + name): continue
        out.append((name, f, who))
    return out

def convert(name, f, who):
    AT = unreal.AssetToolsHelpers.get_asset_tools(); EAL = unreal.EditorAssetLibrary; U = unreal.MetaHumanPerformanceExportUtils
    snd_path = '/Game/PBX/Story/VO/' + name
    if not EAL.does_asset_exist(snd_path):
        t = unreal.AssetImportTask(); t.filename = os.path.join(VO, f); t.destination_path = '/Game/PBX/Story/VO'
        t.automated = True; t.replace_existing = True; t.save = True; AT.import_asset_tasks([t])
    snd = unreal.load_asset(snd_path)
    pp = '/Game/PBX/Story/Face/PF_' + name
    perf = unreal.load_asset(pp) if EAL.does_asset_exist(pp) else AT.create_asset('PF_' + name, '/Game/PBX/Story/Face', unreal.MetaHumanPerformance, unreal.MetaHumanPerformanceFactoryNew())
    perf.set_editor_property('input_type', unreal.DataInputType.AUDIO); perf.set_editor_property('audio', snd)
    perf.set_blocking_processing(True); perf.start_pipeline()
    s = U.get_export_animation_sequence_settings(perf)
    s.set_editor_property('show_export_dialog', False); s.set_editor_property('package_path', '/Game/PBX/Story/FaceAnim')
    s.set_editor_property('asset_name', 'FA_' + name)
    s.set_editor_property('target_skeleton_or_skeletal_mesh', unreal.load_asset('/Game/PBX/MH/Common/Face/SKM_Face'))
    s.set_editor_property('enable_head_movement', True); s.set_editor_property('auto_save_anim_sequence', True)
    U.export_animation_sequence(perf, s)
    EAL.save_asset(pp, only_if_is_dirty=True)

def _tick(dt):
    st = _state
    if not st['todo']:
        unreal.unregister_slate_post_tick_callback(st['h']); st['h'] = None
        _log('ALLDONE %d %.0fs' % (st['n'], time.time() - st['t0'])); return
    if st['busy']: return          # the MetaHuman pipeline pumps Slate while it works: never start a line inside another
    st['busy'] = True
    name, f, who = st['todo'].pop(0)
    try:
        convert(name, f, who); st['n'] += 1
        _log('%s %s %.0fs left=%d' % (name, who, time.time() - st['t0'], len(st['todo'])))
    except Exception as ex:
        _log('ERR %s %s' % (name, ex))
    finally:
        st['busy'] = False

def start():
    if _state['h']: return 'already running'
    _state['todo'] = _todo(); _state['n'] = 0; _state['t0'] = time.time()
    _log('--- batch (tick) %d to do' % len(_state['todo']))
    _state['h'] = unreal.register_slate_post_tick_callback(_tick)
    return len(_state['todo'])
