# Sigil & Spark — turns a film CAPTURE (Saved/film/<name>: f_000000.png… + cues.jsonl, written by the game with -pbxfilm)
# into an mp4 with its sound: voices, music and ambience loops (with their fades), story sfx, all placed on the frame they
# started in the capture. 30 fps, H.264 CRF 16 (visually lossless), AAC 192k. Optional: split at the choices.
#   python film_mux.py <capture dir> <out.mp4> [--keep-png]
# Runs with Blender's bundled python (numpy). ffmpeg: PATH or SigilAndSpark_src/tools/bin/ffmpeg.exe.
import os, sys, json, wave, glob, shutil, subprocess
import numpy as np

CAP, OUT = sys.argv[1], sys.argv[2]
KEEP = '--keep-png' in sys.argv
FPS, SR = 30, 48000
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(HERE, '..', '..'))
PRJ = os.path.join(os.path.dirname(SRC), 'SigilAndSpark')
AUD = os.path.join(PRJ, 'Content', 'PBX', 'StoryAudio')
FF = shutil.which('ffmpeg') or os.path.join(SRC, 'tools', 'bin', 'ffmpeg.exe')
FF = FF if os.path.exists(FF) else None

def load(kind, name):
    p = os.path.join(AUD, kind, name + '.wav')
    if not os.path.exists(p): print('missing', kind, name); return None
    with wave.open(p) as w:
        ch, rate, n = w.getnchannels(), w.getframerate(), w.getnframes()
        a = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
    a = a.reshape(-1, ch)
    if ch == 1: a = np.repeat(a, 2, axis=1)
    if rate != SR:   # linear resample (voices are 24 kHz)
        t = np.arange(int(len(a) * SR / rate)) * rate / SR
        a = np.stack([np.interp(t, np.arange(len(a)), a[:, c]) for c in range(2)], axis=1).astype(np.float32)
    return a

frames = sorted(glob.glob(os.path.join(CAP, 'f_*.jpg')) or glob.glob(os.path.join(CAP, 'f_*.png')))
EXT = os.path.splitext(frames[0])[1] if frames else '.png'
if not frames: sys.exit('no frames in ' + CAP)
N = int(os.path.basename(frames[-1])[2:8]) + 1
cues = [json.loads(l) for l in open(os.path.join(CAP, 'cues.jsonl'), encoding='utf-8') if l.strip()]
L = int(N / FPS * SR) + SR
mix = np.zeros((L, 2), np.float32)
loops = {}   # kind -> (start sample, name, vol, fade-in s)

def place(a, s0, vol, fade_in=0.0, end=None, fade_out=0.0, loop=False):
    if a is None: return
    e = L if end is None else min(L, end)
    if s0 >= e: return
    n = e - s0
    if loop: seg = np.tile(a, (n // len(a) + 1, 1))[:n]
    else: seg = a[:n]; n = len(seg)
    g = np.full(n, vol, np.float32)
    if fade_in > 0: k = min(n, int(fade_in * SR)); g[:k] *= np.linspace(0, 1, k)
    if fade_out > 0: k = min(n, int(fade_out * SR)); g[n - k:] *= np.linspace(1, 0, k)
    mix[s0:s0 + n] += seg * g[:, None]

for c in cues:
    s = int(c['f'] / FPS * SR); k = c['k']
    if k == 'vo': place(load('vo', c['id']), s, c['v'])
    elif k == 'sfx': place(load('sfx', c['id']), s, c['v'])
    elif k in ('music', 'amb'):
        if k in loops: st, nm, v, fi = loops.pop(k); place(load(k, nm), st, v, fi, s + int(c.get('fade', 1) * SR), c.get('fade', 1), True)
        loops[k] = (s, c['id'], c['v'], c.get('fade', 0))
    elif k in ('music_out', 'amb_out'):
        kk = k[:-4]
        if kk in loops: st, nm, v, fi = loops.pop(kk); place(load(kk, nm), st, v, fi, s + int(c.get('fade', 1) * SR), c.get('fade', 1), True)
for kk, (st, nm, v, fi) in loops.items(): place(load(kk, nm), st, v, fi, None, 2.0, True)

peak = float(np.abs(mix).max()) or 1.0
if peak > 0.98: mix *= 0.98 / peak   # never clip
wav = os.path.join(CAP, '_mix.wav')
with wave.open(wav, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix[:int(N / FPS * SR)] * 32767).astype(np.int16).tobytes())
if FF and os.path.exists(FF):
    cmd = [FF, '-y', '-framerate', str(FPS), '-i', os.path.join(CAP, 'f_%06d' + EXT), '-i', wav, '-c:v', 'libx264', '-preset', 'slow', '-crf', '16',
           '-pix_fmt', 'yuv420p', '-vf', 'scale=1920:1080:flags=lanczos', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', OUT]
else:   # no ffmpeg on this PC: Blender's built-in encoder (same H.264), run in the background
    enc = os.path.join(CAP, '_encode.py')
    open(enc, 'w').write(f"""import bpy, os
s = bpy.data.scenes.new('FILM'); s.render.resolution_x, s.render.resolution_y, s.render.resolution_percentage = 1920, 1080, 100; s.render.fps = {FPS}
se = s.sequence_editor_create(); coll = se.strips if hasattr(se, 'strips') else se.sequences
fr = sorted(f for f in os.listdir(r'{CAP}') if f.startswith('f_') and f.endswith(('.png', '.jpg')))
st = coll.new_image('img', os.path.join(r'{CAP}', fr[0]), 1, 1)
for f in fr[1:]: st.elements.append(f)
try: st.transform.filter = 'BICUBIC'
except Exception: pass
s.frame_start, s.frame_end = 1, len(fr)
coll.new_sound('mix', r'{wav}', 2, 1)
r = s.render; r.image_settings.media_type = 'VIDEO'; r.image_settings.file_format = 'FFMPEG'
r.ffmpeg.format = 'MPEG4'; r.ffmpeg.codec = 'H264'; r.ffmpeg.constant_rate_factor = 'PERC_LOSSLESS'; r.ffmpeg.ffmpeg_preset = 'GOOD'
r.ffmpeg.audio_codec = 'AAC'; r.ffmpeg.audio_bitrate = 192; r.ffmpeg.audio_mixrate = {SR}; r.ffmpeg.audio_channels = 'STEREO'
r.filepath = r'{OUT}'; r.use_sequencer = True
bpy.context.window.scene = s
bpy.ops.render.render(animation=True, scene=s.name)
""")
    BL = os.environ.get('PBX_BLENDER', r'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe')
    cmd = [BL, '-b', '--factory-startup', '--python', enc]
r = subprocess.run(cmd, capture_output=True, text=True)
ok = r.returncode == 0 and os.path.exists(OUT) and os.path.getsize(OUT) > 0
print('encode', r.returncode, ok, (r.stderr or r.stdout)[-600:])
json.dump([c for c in cues if c['k'] in ('line', 'lineend', 'choice', 'pick', 'start')], open(os.path.splitext(OUT)[0] + '.cues.json', 'w', encoding='utf-8'), indent=0)
if ok and not KEEP:
    for f in frames: os.remove(f)
print('frames', N, 'secs %.1f' % (N / FPS), '->', OUT)
