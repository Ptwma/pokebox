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
    'intro_08': "Today, every sixteen-year-old on the island receives a Codex.",
    'intro_10': "And then... there was you.",
    'intro_14': "Some books are blank... because they haven't been written yet.",
    # dark tone (user 2026-11-01: "adventure with darkness, blood, alone")
    'intro_15': "By morning, half of Lumen Harbor had forgotten its own name. Only you were left... unwritten.",
    # v3 saga intro (intro/SAGA_SCRIPT.md) — user 2026-11-01: told like a tale, more words
    'saga_01': 'Before the sea had a name... before the first ship cut the first wave... there was the Script.',
    'saga_02': 'It was not a language anyone spoke. It was the language the world itself was written in. Every wave was a word. Every stone, a sentence. Every living thing, a story that was still being told.',
    'saga_03': 'And some words carried so much meaning, so much weight... that one day, they opened their eyes.',
    'saga_04': 'Our ancestors called them Sparks. Living words. Wild, and proud, and older than any kingdom.',
    'saga_05': 'The first scribes did not try to tame them. They wrote beside them. They bound their names into books of leather and gold. Books that remember. We call them... the Codex.',
    'saga_06': 'When a Spark chooses to trust you, the Codex writes a new page by itself. A page is a promise. And a Codex... is a life.',
    'saga_07': 'For a thousand years, the islands lived by that promise.',
    'saga_08': 'Until the night of the Surge. Thirty years ago, the Script beneath the town of Hollowmere began to burn. Hundreds of Sparks woke at once, screaming words no one could read.',
    'saga_09': 'By dawn, Hollowmere was gone. Swallowed by the very sea it had been written beside.',
    'saga_10': 'Only one soul walked out of the water. And from that day, she believed she understood. Every word is a wound. Every name is a door through which pain can enter.',
    'saga_11': 'So she founded an order to close those doors forever. They wear white. They carry no books. They call themselves... the White Page.',
    'saga_12': 'Where the White Page passes, the Script is erased. Sparks turn grey and forget themselves. People keep breathing, keep walking... but nothing is written in them anymore. That is the Blanking.',
    'saga_13': 'On the island of Lumen, every sixteen-year-old receives a Codex. Most open with one page already glowing. The lucky, with two. The rare, with three.',
    'saga_14': 'And one book, on one cold morning... opened blank.',
    'saga_15': 'That same night, white sails came out of the fog. And by morning, half of Lumen Harbor had forgotten its own name.',
    'saga_16': "Some books are blank because they are broken. Some books are blank... because they haven't been written yet.",
    # v4 legend intro (60–90 s, council 2026-11-01): the everyday (Rite of Pages 1·2·3) + ONE hint (an unwritten Codex)
    'leg_01': 'Long ago, the world was written. Some of its words woke up, with teeth, and wings, and wills of their own. We call them Sparks.',
    'leg_02': 'They light our lamps. They guard our boats. They sleep beside our fires.',
    'leg_03': 'On this island, every child turns sixteen with a Codex in their hands... and opens it before the whole town.',
    'leg_04': 'Most wake a single glowing page. One Spark. One bond. A good life. The lucky wake two. Once in a generation... three. And the town speaks that name for years. That is how it has always been.',
    'leg_05': 'But some books are found grey. Drained. Their Sparks gone quiet. Their owners... no longer sure of their own names.',
    'leg_06': 'And the oldest keepers whisper of one more kind of book. One that opens with no light at all. Not burned. Not erased. Unwritten. And whatever hunts the grey... is hunting it too.',
    'leg_08': 'Tonight, a Codex opens.',
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
    if not suffix:   # merge (a run for a few ids must not drop the others)
        jp = os.path.join(out, 'vo_lines.json'); old = json.load(open(jp)) if os.path.exists(jp) else {}
        old.update(info); json.dump(old, open(jp, 'w'), indent=1)
