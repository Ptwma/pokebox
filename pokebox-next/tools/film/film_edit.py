# Sigil & Spark — FILM MODE: compose the rendered beat shots on the inked comic page (sequencer).
#   blender -b --python film_edit.py -- <OUTDIR> preview [choice_beat "opt1|opt2|opt3" picked]   → OUTDIR/film_proto.mp4 (voice + subtitles)
#   blender -b --python film_edit.py -- <OUTDIR> clips <MOVIES_DIR>                              → one SILENT clip per beat, <id>.mp4
# Panel 1 = the speaker (big), panel 2 = the listener's reaction (comes in half a second later), panel 3 = the place.
# In the game the voice, music, subtitles and choices come from the engine; the clips carry only the picture.
import bpy, os, sys, json
argv = sys.argv[sys.argv.index('--') + 1:]
OUTDIR, MODE = argv[0], (argv[1] if len(argv) > 1 else 'preview')
HERE = os.path.dirname(os.path.abspath(__file__))
plan = json.load(open(os.path.join(OUTDIR, 'plan.json')))
FPS = 12; W, H = 1920, 1080
PANELS = {'A': (60, 60, 1240, 1020), 'B': (1290, 90, 1870, 560), 'C': (1290, 610, 1870, 1000)}
NAMES = {'gus': 'Gus', 'hero': 'You', 'rho': 'Rho', 'vale': 'Vale'}

def fresh():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene; sc.render.resolution_x, sc.render.resolution_y = W, H; sc.render.fps = FPS
    se = sc.sequence_editor_create()
    return sc, (se.strips if hasattr(se, 'strips') else se.sequences)

def img_seq(S, ch, d, start, x0, y0, x1, y1, offset=0):
    files = sorted(f for f in os.listdir(d) if f.endswith('.png'))
    st = S.new_image(name=os.path.basename(os.path.dirname(d)) + os.path.basename(d), filepath=os.path.join(d, files[0]), channel=ch, frame_start=start + offset, fit_method='ORIGINAL')
    for f in files[1:]: st.elements.append(f)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    st.transform.offset_x = cx - W / 2; st.transform.offset_y = (H - cy) - H / 2
    return st

def text(S, ch, start, length, body, x, y, size=34, color=(0.95, 0.92, 0.85, 1)):
    t = S.new_effect(name='T', type='TEXT', channel=ch, frame_start=start, length=length)
    t.text = body; t.font_size = size; t.color = color; t.location = (x / W, 1 - y / H); t.anchor_x = 'CENTER'; t.anchor_y = 'CENTER'
    t.use_box = True; t.box_color = (0.04, 0.03, 0.03, 0.82); t.wrap_width = 0.58
    return t

def beat(S, b, t, voice, subs):
    n = b['frames']
    for sh, ch, off in (('A', 2, 0), ('B', 3, int(0.5 * FPS)), ('C', 4, 0)):
        st = img_seq(S, ch, os.path.join(OUTDIR, b['id'], sh), t, *PANELS[sh], offset=off)
        if off: st.frame_final_duration = max(1, n - off)
    if voice and b['wav']: S.new_sound(name='vo', filepath=b['wav'], channel=8, frame_start=t)
    if subs: text(S, 9, t, n, f"{NAMES.get(b['spk'], b['spk'].title())}:  {b['text']}", 650, 965, 30)
    return n

def page(S, length):
    bg = S.new_image(name='page', filepath=os.path.join(HERE, 'page_bg.png'), channel=1, frame_start=1, fit_method='ORIGINAL'); bg.frame_final_duration = length
    fr = S.new_image(name='frames', filepath=os.path.join(HERE, 'page_frames.png'), channel=7, frame_start=1, fit_method='ORIGINAL'); fr.frame_final_duration = length
    fr.blend_type = 'ALPHA_OVER'

def render(sc, end, path, audio):
    sc.frame_start, sc.frame_end = 1, end
    r = sc.render; r.image_settings.media_type = 'VIDEO'; r.image_settings.file_format = 'FFMPEG'; r.ffmpeg.format = 'MPEG4'; r.ffmpeg.codec = 'H264'; r.ffmpeg.constant_rate_factor = 'HIGH'
    r.ffmpeg.audio_codec = 'AAC' if audio else 'NONE'; r.filepath = path
    bpy.ops.render.render(animation=True); print('WROTE', path, flush=True)

if MODE == 'clips':
    MOV = argv[2]; os.makedirs(MOV, exist_ok=True)
    for b in plan:
        sc, S = fresh(); n = beat(S, b, 1, False, False); page(S, n + 1)
        render(sc, n, os.path.join(MOV, b['id'] + '.mp4'), False)
else:
    CHOICE = (argv[2], argv[3].split('|'), int(argv[4])) if len(argv) >= 5 else None
    sc, S = fresh(); t = 1
    for b in plan:
        if CHOICE and b['id'] == CHOICE[0]:   # the decision: the options on the page, the pick in red, then its animation at once
            n = int(2.2 * FPS)
            for i, o in enumerate(CHOICE[1]): text(S, 10 + i, t, n, o, 650, 760 + i * 70, 36, (0.86, 0.12, 0.08, 1) if i == CHOICE[2] else (0.95, 0.92, 0.85, 1))
            t += n
        t += beat(S, b, t, True, True)
    page(S, t)
    render(sc, t - 1, os.path.join(OUTDIR, 'film_proto.mp4'), True)
print('FILM EDIT DONE', flush=True)
