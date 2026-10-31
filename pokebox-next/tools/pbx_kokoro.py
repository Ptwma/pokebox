# Sigil & Spark — narration with Kokoro-82M (Apache-2.0, offline ONNX). Run with Blender's python + the local pylib:
#   python pbx_kokoro.py <voice> <speed> <out_dir> <suffix> [ids...]
# Model / voices / pylib stay local in PokeboxNext_src/tts/kokoro (never in the repo).
import sys, os, json
K = r"E:\GAME-APP-DEV\POKEMON\PokeboxNext_src\tts\kokoro"
sys.path.insert(0, os.path.join(K, 'pylib'))
import soundfile as sf
from kokoro_onnx import Kokoro

# user 2026-10-31 (3rd pass): "some parts sound AI — do it as you would, male voice". Fixes: whole SENTENCES per call (the model
# needs the context for natural intonation — single phrases each fell into the same robotic cadence), natural wording with
# no one-word fragments, short pauses only BETWEEN sentences, and the voice: am_onyx is one of Kokoro's lowest-graded voices
# (D) → am_michael (C+) blended with a little onyx for depth.
LINES = {
    'intro_01': "Before the sea had a name, there was the Script.",
    'intro_02': "Every wave, every stone, every living thing. Each one a word, written in a language older than memory.",
    'intro_03': "Some words carried so much meaning... that they woke up. We call them Sparks.",
    'intro_04': "And people learned to write beside them, in books that remember every bond.",
    'intro_05': "But there are those who believe that every word is a wound, waiting to open. They call themselves the White Page.",
    'intro_07': "Lumen Harbor. Thirty years without a Blanking.",
    'intro_08': "Today, every eleven-year-old on the island receives a Codex.",
    'intro_10': "And then... there was you.",
    'intro_14': "Some books are blank... because they haven't been written yet.",
}
PAUSE_SENTENCE = 0.42      # seconds between sentences (an ellipsis inside a sentence is voiced by the model itself)
VOICE_DEFAULT = 'am_michael*0.7+am_onyx*0.3'

def sentences(text):
    import re
    return [t.strip() for t in re.split(r'(?<=[^.][.!?])\s+', text) if t.strip()]

def style(k, spec):
    """'am_michael*0.7+am_onyx*0.3' → a blended voice style vector (kokoro voices are style embeddings)"""
    if '*' not in spec and '+' not in spec: return spec
    acc = None
    for part in spec.split('+'):
        name, w = (part.split('*') + ['1'])[:2]
        v = k.get_voice_style(name.strip()) * float(w)
        acc = v if acc is None else acc + v
    return acc

if __name__ == '__main__':
    voice, speed, out, suffix = sys.argv[1], float(sys.argv[2]), sys.argv[3], sys.argv[4]
    ids = sys.argv[5:] or list(LINES)
    k = Kokoro(os.path.join(K, 'kokoro-v1.0.int8.onnx'), os.path.join(K, 'voices-v1.0.bin'))
    info = {}
    import numpy as np
    vs = style(k, voice if voice != 'default' else VOICE_DEFAULT)
    for i in ids:
        parts, sr = [], 24000
        for sen in sentences(LINES[i]):
            samples, sr = k.create(sen, voice=vs, speed=speed, lang='en-us')
            parts += [samples.astype(np.float32), np.zeros(int(sr * PAUSE_SENTENCE), np.float32)]
        parts[-1] = np.zeros(int(sr * .25), np.float32)
        audio = np.concatenate(parts); audio = audio / max(1e-6, np.abs(audio).max()) * 0.9   # even loudness
        f = os.path.join(out, f'vo_{i}{suffix}.wav'); sf.write(f, audio, sr)
        info[i] = {'secs': round(len(audio) / sr, 2), 'text': LINES[i]}; print('vo', i, info[i]['secs'])
    if not suffix: json.dump(info, open(os.path.join(out, 'vo_lines.json'), 'w'), indent=1)
