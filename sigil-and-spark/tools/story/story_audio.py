# Sigil & Spark — the story's music, ambience and sound effects as loose WAVs for PBXAudio (Content/PBX/StoryAudio/...).
#   Run inside Blender (needs the `aud` module for mp3 → wav):  exec(open(story_audio.py).read()); build_all()
# Music = the CC0 (opengameart) and CC-BY (Gregor Quendel) tracks already in SigilAndSpark_src/music_cc0 — credit them.
# Ambience / effects = synthesised here (numpy only, FFT band filters): original, no samples.
import os, numpy as np, wave
SRC = r"E:\GAME-APP-DEV\POKEMON\SigilAndSpark_src"
OUT = r"E:\GAME-APP-DEV\POKEMON\SigilAndSpark\Content\PBX\StoryAudio"
SR = 44100
MUSIC = {
    'harbour':  r'music_cc0\mus_harbour.wav',     # "The Bard's Tale" loop (CC0)
    'calm':     r'music_cc0\mus_home.wav',        # "Cinematic Calm" (CC0)
    'suspense': r'music_cc0\saga\gregor_quendel_-_cinematic_trailer_music_-_variations_-_05_-_cinematic_suspense_trailer_-_extended_percussion_version.mp3',
    'action':   r'music_cc0\saga\gregor_quendel_-_cinematic_trailer_music_-_variations_-_03_-_cinematic_orchestral_action_trailer_-_extended_version.mp3',
    'lullaby':  r'music_cc0\saga\gregor_quendel_-_cinematic_trailer_music_-_20_-_cinematic_sentimental_lullaby_trailer.mp3',
    'riser':    r'music_cc0\saga\gregor_quendel_-_cinematic_trailer_music_-_13_-_cinematic_epic_hybrid_riser.mp3',
}
R = np.random.default_rng(7)

def write(path, x, stereo=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    x = np.asarray(x, dtype=np.float64)
    if stereo is not None: x = np.stack([x, stereo], 1)
    pk = np.abs(x).max() + 1e-9; x = x / pk * 0.9
    ch = 1 if x.ndim == 1 else 2
    with wave.open(path, 'wb') as w:
        w.setnchannels(ch); w.setsampwidth(2); w.setframerate(SR); w.writeframes((x * 32767).astype('<i2').tobytes())

def band(x, lo, hi):
    F = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    m = np.clip((f - lo * 0.8) / (lo * 0.2 + 1e-9), 0, 1) * np.clip((hi * 1.25 - f) / (hi * 0.25), 0, 1)
    return np.fft.irfft(F * m, len(x))

def noise(sec): return R.normal(0, 1, int(SR * sec))
def t_(sec): return np.arange(int(SR * sec)) / SR
def loopify(x, xf=2.0):
    n = int(SR * xf); a = x[:n]; b = x[-n:]; k = np.linspace(0, 1, n)
    y = x[n:-n].copy() if len(x) > 3 * n else x.copy()
    return np.concatenate([b * (1 - k) + a * k, x[n:-n]])

def waves(sec):
    t = t_(sec); sw = 0.55 + 0.45 * np.sin(2 * np.pi * t / 7.0) ** 2 * (0.7 + 0.3 * np.sin(2 * np.pi * t / 19.0))
    return band(noise(sec), 60, 900) * sw + band(noise(sec), 900, 4000) * sw ** 3 * 0.25

def wind(sec):
    t = t_(sec); m = 0.5 + 0.5 * np.sin(2 * np.pi * t / 11.0 + np.sin(2 * np.pi * t / 4.3))
    return band(noise(sec), 200, 1200) * (0.3 + 0.7 * m) * 0.6

def rain(sec):
    x = band(noise(sec), 1500, 9000) * 0.5 + band(noise(sec), 300, 1500) * 0.25
    drips = np.zeros(int(SR * sec)); idx = R.integers(0, len(drips) - 2000, int(sec * 9))
    for i in idx:
        d = np.exp(-np.arange(1500) / 120.0) * np.sin(2 * np.pi * R.uniform(1800, 4200) * np.arange(1500) / SR); drips[i:i + 1500] += d * R.uniform(0.2, 0.7)
    return x + drips * 0.5

def bell(sec=5.0, f0=196.0):
    t = t_(sec); x = np.zeros_like(t)
    for r, a, d in [(0.5, .5, 4.5), (1.0, 1.0, 3.5), (1.19, .6, 2.6), (1.5, .45, 2.2), (2.0, .5, 1.6), (2.52, .3, 1.1), (3.0, .2, .8)]:
        x += a * np.sin(2 * np.pi * f0 * r * t) * np.exp(-t / d)
    return x * np.minimum(1, t / 0.005)

def fire(sec):
    x = band(noise(sec), 80, 700) * 0.6
    cr = np.zeros(int(SR * sec)); idx = R.integers(0, len(cr) - 400, int(sec * 30))
    for i in idx: cr[i:i + 300] += band(R.normal(0, 1, 300), 0, SR / 2)[:300] * np.exp(-np.arange(300) / 40.0) * R.uniform(0.3, 1.2)
    return x + band(cr, 1500, 8000) * 0.8

def white_swell(sec=4.0):
    t = t_(sec); env = np.sin(np.pi * np.clip(t / sec, 0, 1)) ** 2
    x = sum(np.sin(2 * np.pi * f * t * (1 + 0.02 * t)) for f in (220, 221.7, 330.4, 440.9, 659.3)) * 0.3
    return (x + band(noise(sec), 2000, 9000) * 0.5 * env) * env

def tear(sec=0.7):
    x = band(noise(sec), 1200, 7000); t = t_(sec)
    am = (R.random(len(x)) > 0.6) * 0.6 + 0.4
    return x * am * np.exp(-t / 0.35) * np.minimum(1, t / 0.01)

def build_amb():
    L = 40.0
    write(os.path.join(OUT, 'amb', 'sea.wav'), loopify(waves(L)))
    write(os.path.join(OUT, 'amb', 'wind.wav'), loopify(wind(L) + waves(L) * 0.25))
    write(os.path.join(OUT, 'amb', 'rain.wav'), loopify(rain(L) + wind(L) * 0.3))
    h = waves(L) * 0.8 + wind(L) * 0.5
    b = bell(5.0, 146.8) * 0.12; i = int(SR * 17); h[i:i + len(b)] += b          # a far bell once a loop
    write(os.path.join(OUT, 'amb', 'harbour.wav'), loopify(h))
    write(os.path.join(OUT, 'amb', 'hall.wav'), loopify(band(noise(L), 60, 400) * 0.2 + rain(L) * 0.18))
    write(os.path.join(OUT, 'amb', 'fire.wav'), loopify(fire(L)))

def build_sfx():
    write(os.path.join(OUT, 'sfx', 'bell.wav'), np.concatenate([bell(4.0), np.zeros(int(SR * .3)), bell(4.0), np.zeros(int(SR * .3)), bell(5.0)]))
    write(os.path.join(OUT, 'sfx', 'white.wav'), white_swell())
    write(os.path.join(OUT, 'sfx', 'tear.wav'), tear())

def build_music():
    import aud
    for k, rel in MUSIC.items():
        src = os.path.join(SRC, rel); dst = os.path.join(OUT, 'music', k + '.wav'); os.makedirs(os.path.dirname(dst), exist_ok=True)
        s = aud.Sound(src).resample(SR, False)
        s.write(dst, rate=SR, channels=aud.CHANNELS_STEREO, format=aud.FORMAT_S16, container=aud.CONTAINER_WAV, codec=aud.CODEC_PCM)

def build_all():
    build_music(); build_amb(); build_sfx()
    return sorted(os.path.relpath(os.path.join(d, f), OUT) for d, _, fs in os.walk(OUT) for f in fs if f.endswith('.wav'))
