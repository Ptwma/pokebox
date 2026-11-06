# Sigil & Spark — FILM MODE: compose the rendered beat shots on the inked comic page (sequencer) → one mp4.
#   blender -b --python film_edit.py -- <OUTDIR> [choice beat_id "opt1|opt2|opt3" picked_index]
# Panel 1 = the speaker (big), panel 2 = the listener's reaction (comes in a beat later), panel 3 = the place.
# The game uses one silent clip per beat (voice/music play in the engine); this preview adds the voice and subtitles.
import bpy, os, sys, json
argv = sys.argv[sys.argv.index('--') + 1:]
OUTDIR = argv[0]; HERE = os.path.dirname(os.path.abspath(__file__))
CHOICE = (argv[1], argv[2].split('|'), int(argv[3])) if len(argv) >= 4 else None
plan = json.load(open(os.path.join(OUTDIR, 'plan.json')))
FPS = 12; W, H = 1920, 1080
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; sc.render.resolution_x, sc.render.resolution_y = W, H; sc.render.fps = FPS
se = sc.sequence_editor_create()
S = getattr(se, 'strips', None) or se.sequences
PANELS = {'A': (60, 60, 1240, 1020), 'B': (1290, 90, 1870, 560), 'C': (1290, 610, 1870, 1000)}

def img_seq(ch, d, start, x0, y0, x1, y1, offset=0):
    files = sorted(f for f in os.listdir(d) if f.endswith('.png'))
    st = S.new_image(name=os.path.basename(os.path.dirname(d)) + os.path.basename(d), filepath=os.path.join(d, files[0]), channel=ch, frame_start=start + offset, fit_method='ORIGINAL')
    for f in files[1:]: st.elements.append(f)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    st.transform.offset_x = cx - W / 2; st.transform.offset_y = (H - cy) - H / 2
    return st

def text(ch, start, length, body, x, y, size=34, color=(0.95, 0.92, 0.85, 1), box=True):
    t = S.new_effect(name='T', type='TEXT', channel=ch, frame_start=start, length=length)
    t.text = body; t.font_size = size; t.color = color; t.location = (x / W, 1 - y / H); t.anchor_x = 'CENTER'; t.anchor_y = 'CENTER'
    t.use_box = box; t.box_color = (0.04, 0.03, 0.03, 0.82); t.wrap_width = 0.58
    try: t.use_shadow = False
    except Exception: pass
    return t

NAMES = {'gus': 'Gus', 'hero': 'You', 'rho': 'Rho', 'vale': 'Vale'}
t = 1; total = 0
for b in plan:
    if CHOICE and b['id'] == CHOICE[0]:   # the decision: options on the page with the fuse, the pick in red, then its animation
        n = int(2.2 * FPS)
        for i, o in enumerate(CHOICE[1]):
            text(10 + i, t, n, o, 650, 760 + i * 70, 36, (0.86, 0.12, 0.08, 1) if i == CHOICE[2] else (0.95, 0.92, 0.85, 1))
        t += n
    n = b['frames']
    for sh, ch, off in (('A', 2, 0), ('B', 3, int(0.5 * FPS)), ('C', 4, 0)):
        d = os.path.join(OUTDIR, b['id'], sh)
        st = img_seq(ch, d, t, *PANELS[sh], offset=off)
        if off: st.frame_final_duration = max(1, n - off)
    if b['wav']: S.new_sound(name='vo', filepath=b['wav'], channel=8, frame_start=t)
    who = NAMES.get(b['spk'], b['spk'].title())
    text(9, t, n, f"{who}:  {b['text']}", 650, 965, 30)
    t += n
bg = S.new_image(name='page', filepath=os.path.join(HERE, 'page_bg.png'), channel=1, frame_start=1, fit_method='ORIGINAL'); bg.frame_final_duration = t
fr = S.new_image(name='frames', filepath=os.path.join(HERE, 'page_frames.png'), channel=7, frame_start=1, fit_method='ORIGINAL'); fr.frame_final_duration = t
fr.blend_type = 'ALPHA_OVER'
sc.frame_start, sc.frame_end = 1, t - 1
r = sc.render; r.image_settings.file_format = 'FFMPEG'; r.ffmpeg.format = 'MPEG4'; r.ffmpeg.codec = 'H264'; r.ffmpeg.constant_rate_factor = 'HIGH'
r.ffmpeg.audio_codec = 'AAC'; r.filepath = os.path.join(OUTDIR, 'film_proto.mp4')
bpy.ops.render.render(animation=True)
print('FILM EDIT DONE', r.filepath, flush=True)
