# Sigil & Spark — narration with Kokoro-82M (Apache-2.0, offline ONNX). Run with Blender's python + the local pylib:
#   python pbx_kokoro.py <voice> <speed> <out_dir> <suffix> [ids...]
# Model / voices / pylib stay local in PokeboxNext_src/tts/kokoro (never in the repo).
import sys, os, json
K = r"E:\GAME-APP-DEV\POKEMON\PokeboxNext_src\tts\kokoro"
sys.path.insert(0, os.path.join(K, 'pylib'))
import soundfile as sf
from kokoro_onnx import Kokoro

# user 2026-10-31: am_onyx, delivered slowly and deliberately — short heavy statements with long silences between them
# (the cadence, not the voice, of a calm, solemn speaker). "/" = a short breath, "..." = a long pause, "." = a full stop.
LINES = {
    'intro_01': "Before the sea had a name... there was the Script.",
    'intro_02': "Every wave. Every stone. Every living thing... a word. Written in a language... older than memory.",
    'intro_03': "Some words held so much meaning... that they woke. We call them... Sparks.",
    'intro_04': "And people learned to write beside them. In books... that remember a bond.",
    'intro_05': "But some believe... that every word is a wound. Waiting to open. They call themselves... the White Page.",
    'intro_07': "Lumen Harbor. Thirty years... without a Blanking.",
    'intro_08': "Today, every child of eleven... receives a Codex.",
    'intro_10': "And then... there was you.",
    'intro_14': "Some books are blank... because they have not been written. Yet.",
}
PAUSE = {',': .25, '.': .55, '...': .85}   # seconds of silence after each kind of break (user: shorter — dramatic, not slow)

def phrases(text):
    """split at '...', '.' and ',' → [(phrase, pause after)]"""
    import re
    out = []
    for m in re.finditer(r'([^.,]+?)(\.\.\.|\.|,|$)', text):
        ph, br = m.group(1).strip(), m.group(2)
        if ph: out.append((ph + ('.' if br in ('.', '...', '') else ','), PAUSE.get(br, .8)))
    return out

if __name__ == '__main__':
    voice, speed, out, suffix = sys.argv[1], float(sys.argv[2]), sys.argv[3], sys.argv[4]
    ids = sys.argv[5:] or list(LINES)
    k = Kokoro(os.path.join(K, 'kokoro-v1.0.int8.onnx'), os.path.join(K, 'voices-v1.0.bin'))
    info = {}
    import numpy as np
    for i in ids:
        parts, sr = [], 24000
        for ph, pause in phrases(LINES[i]):
            samples, sr = k.create(ph, voice=voice, speed=speed, lang='en-us')
            parts += [samples.astype(np.float32), np.zeros(int(sr * pause), np.float32)]
        if parts: parts[-1] = np.zeros(int(sr * .3), np.float32)
        audio = np.concatenate(parts)
        f = os.path.join(out, f'vo_{i}{suffix}.wav'); sf.write(f, audio, sr)
        info[i] = {'secs': round(len(audio) / sr, 2), 'text': LINES[i]}; print('vo', i, info[i]['secs'])
    if not suffix: json.dump(info, open(os.path.join(out, 'vo_lines.json'), 'w'), indent=1)
