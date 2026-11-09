# Sigil & Spark — film_split.py, but LIVE, while the capture is still running (a 60-min path is ~108k JPEG frames ≈ 54 GB:
# more than the free disk). Every clip whose end is known (the next voice / choice cue is written) and whose frames are all
# on disk is encoded to <out>/<vo id>.mp4 and its frames are deleted, together with any frames no clip uses (before the
# first line, under a choice). When the game has exited, the last clip runs to the last frame.
#   blender -b --factory-startup --python film_split_live.py -- <capture dir> <out dir> [--crf HIGH]
import bpy, os, sys, json, time, subprocess
argv = sys.argv[sys.argv.index('--') + 1:]
CAP, OUT = argv[0], argv[1]
CRF = argv[argv.index('--crf') + 1] if '--crf' in argv else 'HIGH'
FPS = 30
os.makedirs(OUT, exist_ok=True)
LOG = open(os.path.join(CAP, '_split_live.log'), 'a', buffering=1)
def log(*a): LOG.write(time.strftime('%H:%M:%S ') + ' '.join(str(x) for x in a) + '\n')
DONEF = os.path.join(OUT, '_clips_live.json')
done = json.load(open(DONEF)) if os.path.exists(DONEF) else []
done_ids = {d['id'] for d in done}

def fname(i): return os.path.join(CAP, 'f_%06d.jpg' % i)
def game_running():
    r = subprocess.run('tasklist /FI "IMAGENAME eq UnrealEditor.exe" /NH', shell=True, capture_output=True, text=True)
    return 'UnrealEditor.exe' in r.stdout

def encode(cid, f0, f1):
    s = bpy.data.scenes.new('CLIP'); s.render.resolution_x, s.render.resolution_y, s.render.resolution_percentage = 1920, 1080, 100; s.render.fps = FPS
    se = s.sequence_editor_create(); coll = se.strips if hasattr(se, 'strips') else se.sequences
    st = coll.new_image('img', fname(f0), 1, 1)
    for i in range(f0 + 1, f1 + 1): st.elements.append(os.path.basename(fname(i)))
    s.frame_start, s.frame_end = 1, f1 - f0 + 1
    r = s.render; r.image_settings.media_type = 'VIDEO'; r.image_settings.file_format = 'FFMPEG'
    r.ffmpeg.format = 'MPEG4'; r.ffmpeg.codec = 'H264'; r.ffmpeg.constant_rate_factor = CRF; r.ffmpeg.ffmpeg_preset = 'GOOD'
    r.ffmpeg.audio_codec = 'NONE'; r.use_sequencer = True; r.filepath = os.path.join(OUT, cid + '.mp4')
    bpy.context.window.scene = s
    bpy.ops.render.render(animation=True, scene=s.name)
    ok = os.path.exists(r.filepath) and os.path.getsize(r.filepath) > 0
    bpy.data.scenes.remove(s)
    return ok

purged = 0   # every frame below this index is gone (encoded or unused)
log('start', CAP, '->', OUT)
while True:
    running = game_running()
    cp = os.path.join(CAP, 'cues.jsonl')
    cues = [json.loads(l) for l in open(cp, encoding='utf-8') if l.strip().endswith('}')] if os.path.exists(cp) else []
    marks = [c for c in cues if c['k'] in ('vo', 'choice')]
    last = -1
    while os.path.exists(fname(last + 1)) or (last + 1 < purged): last += 1
    work = False
    for i, c in enumerate(marks):
        if c['k'] != 'vo' or c['id'] in done_ids: continue
        if i + 1 < len(marks): end = marks[i + 1]['f'] - 1
        elif not running: end = last
        else: break
        if end > last: break                       # its frames are not all written yet
        if end <= c['f']: done_ids.add(c['id']); continue
        if encode(c['id'], c['f'], end):
            done.append({'id': c['id'], 'from': c['f'], 'to': end, 'secs': round((end - c['f'] + 1) / FPS, 2)}); done_ids.add(c['id'])
            json.dump(done, open(DONEF, 'w'), indent=0); log('CLIP', c['id'], c['f'], end)
            # delete everything up to this clip's end (the clip, and unused frames before it)
            for k in range(purged, end + 1):
                try: os.remove(fname(k))
                except OSError: pass
            purged = end + 1; work = True
        else:
            log('ENCODE FAILED', c['id']); done_ids.add(c['id'])
    if not running and not work:
        log('game gone, all clips written', len(done)); break
    if not work: time.sleep(20)
LOG.close()
