# Sigil & Spark — voice every line of an episode with Kokoro-82M (offline). Run with Blender's python (pbx_kokoro setup):
#   python voice_story.py <ep_lines.json> <out_dir> [--only <id-prefix>] [--force]
# One voice per character (owner 2026-11-06: "characters talk normally"); the hero has a male and a female take.
import sys, os, json, re
K = r"E:\GAME-APP-DEV\POKEMON\PokeboxNext_src\tts\kokoro"
sys.path.insert(0, os.path.join(K, 'pylib'))
import numpy as np, soundfile as sf
from kokoro_onnx import Kokoro

VOICES = {   # speaker → (voice blend, speed)
    'narrator': ('am_michael*0.7+am_onyx*0.3', 0.92),
    'hero_m':   ('am_liam*0.8+am_echo*0.2', 1.0),
    'hero_f':   ('af_sarah*0.7+af_nova*0.3', 1.0),
    'rho':      ('am_puck', 1.05),
    'bruce':    ('bm_george*0.7+am_onyx*0.3', 0.92),
    'vale':     ('bf_emma', 0.96),
    'kelvin':   ('bm_lewis*0.6+am_echo*0.4', 1.12),
    'gus':      ('bm_daniel*0.5+am_onyx*0.5', 0.86),
    'omari':    ('af_sky*0.7+af_nicole*0.3', 1.08),
    'eraser':   ('bf_isabella*0.6+af_river*0.4', 0.82),
    'zuri':     ('af_nicole*0.6+af_heart*0.4', 1.0),
    'sunita':   ('bf_alice', 0.95),
    'town':     ('am_adam', 1.0),
}
SPARKS = {1: 'Cindril', 2: 'Glublet', 3: 'Sporrow'}
PAUSE = 0.32

def blend(k, spec):
    v = None
    for part in spec.split('+'):
        name, w = (part.split('*') + ['1'])[:2]; s = k.get_voice_style(name) * float(w)
        v = s if v is None else v + s
    return v

def clean(t):
    t = t.replace('—', ', ').replace('...', '…').replace('"', '')
    return re.sub(r'\s+', ' ', t).strip()

def say(k, text, voice, speed):
    parts = [p for p in re.split(r'(?<=[.!?…])\s+', clean(text)) if p.strip()]
    out, sr = [], 24000
    st = blend(k, voice)
    for p in parts:
        a, sr = k.create(p, voice=st, speed=speed, lang='en-us'); out += [a, np.zeros(int(sr * PAUSE), dtype=np.float32)]
    a = np.concatenate(out[:-1]) if out else np.zeros(sr // 4, dtype=np.float32)
    a = a / max(1e-6, np.abs(a).max()) * 0.85
    return a, sr

if __name__ == '__main__':
    src, out = sys.argv[1], sys.argv[2]; os.makedirs(out, exist_ok=True)
    only = sys.argv[sys.argv.index('--only') + 1] if '--only' in sys.argv else ''
    force = '--force' in sys.argv
    k = Kokoro(os.path.join(K, 'kokoro-v1.0.int8.onnx'), os.path.join(K, 'voices-v1.0.bin'))
    lines = json.load(open(src, encoding='utf-8')); done = 0
    for L in lines:
        if only and not L['id'].startswith(only): continue
        takes = []
        genders = ['m', 'f'] if L['g'] else ['']
        sparks = [1, 2, 3] if L['s'] else [0]
        for g in genders:
            for sp in sparks:
                t = L['text'].replace('{hero}', 'Rook' if g != 'f' else 'Vesna').replace('{lad}', 'lad' if g != 'f' else 'girl').replace('{he}', 'he' if g != 'f' else 'she')
                if sp: t = t.replace('{spark}', SPARKS[sp])
                who = L['who']
                if who == 'hero': who = 'hero_f' if g == 'f' else 'hero_m'
                vid = L['id'] + (f'_{g}' if g else '') + (f'_p{sp}' if sp else '')
                takes.append((vid, t, who))
        for vid, t, who in takes:
            p = os.path.join(out, vid + '.wav')
            if os.path.exists(p) and not force: continue
            voice, speed = VOICES.get(who, VOICES['town'])
            a, sr = say(k, t, voice, speed)
            sf.write(p, a, sr, subtype='PCM_16'); done += 1
    print('voiced', done)
