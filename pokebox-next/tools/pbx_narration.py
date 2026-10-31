# Pokebox Next / Sigil & Spark — intro narration with Piper (offline TTS, MIT) and the en_GB "cori" voice
# (trained from scratch on public-domain LibriVox recordings). Binaries + voice stay local: PokeboxNext_src/tts.
# Writes PokeboxNext_src/audio/vo_<id>.wav (imported by pbx_build.import_audio()) and vo_lines.json (id -> seconds, text).
#   exec(open(r"E:\GAME-APP-DEV\POKEMON\PokeboxNext_src\tools\pbx_narration.py").read()); NARRATE()
import os, subprocess, json, wave

SRC = r"E:\GAME-APP-DEV\POKEMON\PokeboxNext_src"
PIPER = os.path.join(SRC, 'tts', 'piper', 'piper.exe')
VOICE = os.path.join(SRC, 'tts', 'en_US-norman-medium.onnx')   # user 2026-10-31: a heavy, deep male narrator (public-domain LibriVox voices: norman / john)
OUT = os.path.join(SRC, 'audio')

# the intro (SIGIL_AND_SPARK.md section 8) — ids are used by the C++ cutscene
LINES = [
    ('intro_01', "Before the sea had a name... there was the Script."),
    ('intro_02', "Every wave, every stone, every living thing... a word, in a language older than memory."),
    ('intro_03', "Some words held so much meaning... that they woke up. We call them Sparks."),
    ('intro_04', "And people learned to write beside them, in books that remember a bond."),
    ('intro_05', "But some believe that every word is a wound, waiting to open. They call themselves... the White Page."),
    ('intro_07', "Lumen Harbor. Thirty years without a Blanking."),
    ('intro_08', "Today, every eleven-year-old on the island receives a Codex."),
    ('intro_10', "And then... there was you."),
    ('intro_14', "Some books are blank... because they have not been written yet."),
]

def deep(path, pitch=0.93, wet=0.07, double=0.12):   # user: "more normal" (0.82 / .28 / .35 sounded like a cave)
    """heavy narrator: lower the pitch by resampling (slower too = weightier), a second layer a few % lower for body,
    a low-shelf boost and a dark hall reverb. Not an imitation of any actor — a generic deep, solemn storyteller."""
    import numpy as np
    with wave.open(path) as w: sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    def resample(sig, f):
        n = int(len(sig) / f); t = np.arange(n) * f
        return np.interp(t, np.arange(len(sig)), sig).astype(np.float32)
    a = resample(x, pitch); b = resample(x, pitch * 0.94)
    n = max(len(a), len(b)); y = np.zeros(n + int(sr * 1.6), np.float32)
    y[:len(a)] += a; d = int(sr * 0.012); y[d:d + len(b)] += double * b
    lp = np.convolve(y, np.ones(9) / 9.0, mode='same'); y = y + 0.6 * lp            # low-end weight
    rng = np.random.default_rng(7); L = int(sr * 1.5); tt = np.arange(L) / sr
    ir = rng.standard_normal(L).astype(np.float32) * np.exp(-tt * 3.2); ir = np.convolve(ir, np.ones(25) / 25.0, mode='same')  # dark hall
    ir[0] = 0; ir /= np.sqrt((ir ** 2).sum())
    rev = np.fft.irfft(np.fft.rfft(y, 2 * len(y)) * np.fft.rfft(ir, 2 * len(y)))[:len(y)].astype(np.float32)
    y = y + wet * rev; y /= max(1e-6, np.abs(y).max()) / 0.92
    with wave.open(path, 'wb') as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((y * 32767).astype(np.int16).tobytes())

def NARRATE(length_scale=1.05, sentence_silence=0.5, voice=None, suffix='', heavy=True):
    os.makedirs(OUT, exist_ok=True); info = {}
    for lid, text in LINES:
        f = os.path.join(OUT, f'vo_{lid}{suffix}.wav')
        p = subprocess.run([PIPER, '--model', voice or VOICE, '--output_file', f, '--length_scale', str(length_scale),
                            '--sentence_silence', str(sentence_silence)], input=text.encode('utf-8'),
                           capture_output=True, creationflags=0x08000000)
        if p.returncode != 0 or not os.path.exists(f): print('piper failed', lid, p.stderr[-300:]); continue
        if heavy: deep(f)
        with wave.open(f) as w: secs = w.getnframes() / float(w.getframerate())
        info[lid] = {'secs': round(secs, 2), 'text': text}; print('vo', lid, round(secs, 1), 's')
    if not suffix: json.dump(info, open(os.path.join(OUT, 'vo_lines.json'), 'w'), indent=1)
    return info
