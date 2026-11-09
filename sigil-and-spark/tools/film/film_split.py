# Sigil & Spark — cuts a film CAPTURE into the per-line clips the game plays (Content/Movies/<ep>/<vo id>.mp4,
# APBXDirector::StoryFilm). A clip runs from its voice cue to the next voice / choice cue, so the picture of every line
# (with its breath) is one file; the game itself plays the voice, music, ambience, subtitles and choices over it.
# Video only (no sound), H.264, 1920x1080, 30 fps. Run with Blender (one background session encodes every clip):
#   blender -b --factory-startup --python film_split.py -- <capture dir> <out dir> [--only s1_]
import bpy, os, sys, json
argv = sys.argv[sys.argv.index('--') + 1:]
CAP, OUT = argv[0], argv[1]
ONLY = argv[argv.index('--only') + 1] if '--only' in argv else ''
FPS = 30
cues = [json.loads(l) for l in open(os.path.join(CAP, 'cues.jsonl'), encoding='utf-8') if l.strip()]
frames = sorted(f for f in os.listdir(CAP) if f.startswith('f_') and f.endswith(('.png', '.jpg')))
N = len(frames)
marks = [c for c in cues if c['k'] in ('vo', 'choice')]
clips = []
for i, c in enumerate(marks):
    if c['k'] != 'vo' or not c['id'].startswith(ONLY): continue
    end = marks[i + 1]['f'] if i + 1 < len(marks) else N
    clips.append((c['id'], c['f'], min(end, N) - 1))
os.makedirs(OUT, exist_ok=True)
s = bpy.data.scenes.new('SPLIT'); s.render.resolution_x, s.render.resolution_y, s.render.resolution_percentage = 1920, 1080, 100; s.render.fps = FPS
se = s.sequence_editor_create(); coll = se.strips if hasattr(se, 'strips') else se.sequences
st = coll.new_image('img', os.path.join(CAP, frames[0]), 1, 1)
for f in frames[1:]: st.elements.append(f)
r = s.render; r.image_settings.media_type = 'VIDEO'; r.image_settings.file_format = 'FFMPEG'
r.ffmpeg.format = 'MPEG4'; r.ffmpeg.codec = 'H264'; r.ffmpeg.constant_rate_factor = 'PERC_LOSSLESS'; r.ffmpeg.ffmpeg_preset = 'GOOD'
r.ffmpeg.audio_codec = 'NONE'; r.use_sequencer = True
bpy.context.window.scene = s
done = []
for cid, f0, f1 in clips:
    if f1 <= f0: continue
    s.frame_start, s.frame_end = f0 + 1, f1 + 1          # strip frame 1 = capture frame 0
    r.filepath = os.path.join(OUT, cid + '.mp4')
    bpy.ops.render.render(animation=True, scene=s.name)
    done.append({'id': cid, 'from': f0, 'to': f1, 'secs': round((f1 - f0 + 1) / FPS, 2)})
    print('CLIP', cid, f0, f1)
json.dump(done, open(os.path.join(OUT, '_clips_' + os.path.basename(CAP.rstrip('\\/')) + '.json'), 'w'), indent=0)
print('SPLIT DONE', len(done))
