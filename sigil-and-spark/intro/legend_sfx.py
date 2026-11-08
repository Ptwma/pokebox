# Sigil & Spark — legend sample sound design, synthesised (original, no downloads): room tone, paper crackle, candle
# blow-outs, the fading-name hiss, the transition boom, heartbeat + eye glint, the paper RIP, sub drops, the beast's growl,
# the lunge whoosh, the final impact. Mixed with the narration + music by mix().
#   python legend_sfx.py <vo_wav> <music_mp3> <out_wav>
import sys, numpy as np
from scipy import signal
from scipy.io import wavfile

SR = 48000; FPS = 24
A_END, B0, EYE, TEAR, LUNGE, HIT, LB_F = 270, 271, 300, 312, 340, 372, 384
DUR = LB_F / FPS + 1.0
rng = np.random.default_rng(7)

def t_of(frame): return (frame - 1) / FPS
def n(sec): return int(sec * SR)
def bp(x, lo, hi, order=4):
    sos = signal.butter(order, [lo, hi], btype='band', fs=SR, output='sos'); return signal.sosfilt(sos, x)
def lp(x, hi, order=4):
    sos = signal.butter(order, hi, btype='low', fs=SR, output='sos'); return signal.sosfilt(sos, x)
def hp(x, lo, order=4):
    sos = signal.butter(order, lo, btype='high', fs=SR, output='sos'); return signal.sosfilt(sos, x)
def env(length, a, d, curve=3.0):
    e = np.ones(length); na = max(1, n(a)); nd = max(1, n(d))
    e[:na] = np.linspace(0, 1, na) ** 2
    if nd < length: e[-nd:] = np.linspace(1, 0, nd) ** curve
    return e
def db(x, d): return x * 10 ** (d / 20)
def place(track, clip, at_sec, gain_db=0.0):
    i = n(at_sec); j = min(len(track), i + len(clip)); track[i:j] += db(clip[:j - i], gain_db)

def room(length):
    x = np.cumsum(rng.normal(0, 1, length)); x = hp(x, 30); x /= np.abs(x).max() + 1e-9
    return lp(x, 400) * 0.5
def crackle(sec, density=40):
    L = n(sec); x = np.zeros(L)
    for _ in range(int(density * sec)):
        i = rng.integers(0, L - 400); w = rng.integers(40, 300)
        x[i:i + w] += rng.normal(0, 1, w) * np.exp(-np.linspace(0, 6, w)) * rng.uniform(0.2, 1)
    return bp(x, 1500, 9000)
def whoosh(sec, lo=200, hi=1600, rise=False):
    L = n(sec); x = rng.normal(0, 1, L)
    if rise:
        out = np.zeros(L); seg = L // 12
        for k in range(12):
            f0 = lo * (hi / lo) ** (k / 12); out[k * seg:(k + 1) * seg] = bp(x, f0, f0 * 2.2)[k * seg:(k + 1) * seg]
        x = out
    else: x = bp(x, lo, hi)
    return x * env(L, sec * (0.7 if rise else 0.15), sec * (0.1 if rise else 0.7))
def thump(f0=48, sec=0.45, drop=0.6):
    t = np.arange(n(sec)) / SR; f = f0 * (1 - drop * t / sec)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)
def boom(sec=2.2):
    t = np.arange(n(sec)) / SR
    sub = np.sin(2 * np.pi * np.cumsum(60 * np.exp(-t * 1.4) + 28) / SR) * np.exp(-t * 1.6)
    nz = lp(rng.normal(0, 1, len(t)), 500) * np.exp(-t * 4) * 0.6
    return sub + nz
def ping(f=2400, sec=1.4):
    t = np.arange(n(sec)) / SR
    return (np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * f * 2.01 * t)) * np.exp(-t * 3.2) * env(len(t), 0.005, 0.3)
def rip(sec=0.8):
    """paper tearing: dense crackle + band noise with a jagged, accelerating envelope"""
    L = n(sec); x = rng.normal(0, 1, L)
    jag = np.repeat(rng.uniform(0.2, 1.0, L // 400 + 1), 400)[:L]
    jag = lp(jag, 60, 2); shape = env(L, 0.02, 0.25, 2.0) * (0.5 + np.linspace(0, 1, L) ** 0.5)
    tear = bp(x, 1200, 7000) * jag * shape + crackle(sec, 260)[:L] * 0.7 * shape
    return tear
def growl(sec=1.5):
    t = np.arange(n(sec)) / SR
    f = 58 + 14 * np.sin(2 * np.pi * 3.1 * t) + rng.normal(0, 4, len(t)).cumsum() * 0.002
    saw = signal.sawtooth(2 * np.pi * np.cumsum(f) / SR)
    am = 0.6 + 0.4 * np.abs(np.sin(2 * np.pi * 11 * t + np.sin(2 * np.pi * 2.3 * t)))
    rough = bp(rng.normal(0, 1, len(t)), 180, 1400) * 0.5
    x = np.tanh((saw * am + rough) * 2.5)
    x = lp(x, 1800) + bp(x, 400, 900) * 0.6          # throat formant
    return x * env(len(t), 0.12, 0.5, 2.0)
def impact():
    t = np.arange(n(1.8)) / SR
    hit = lp(rng.normal(0, 1, len(t)), 3000) * np.exp(-t * 14)
    return hit * 0.8 + boom(1.8) * 1.2

def normalise(x, peak=0.9): return x / (np.abs(x).max() + 1e-9) * peak

def build_sfx():
    L = n(DUR); tr = np.zeros(L)
    rt = room(L); quiet = np.ones(L); quiet[n(t_of(B0)):n(t_of(EYE))] = 0.35
    tr += db(rt * quiet, -30)
    place(tr, crackle(2.5, 30), t_of(92), -16)                      # cracks opening
    place(tr, crackle(2.0, 22), t_of(104), -18)
    for i in range(5): place(tr, whoosh(0.5, 250, 1400), t_of(170 + i * 16), -14 - i)   # candles blown out
    place(tr, bp(rng.normal(0, 1, n(2.8)), 3000, 9000) * env(n(2.8), 0.8, 1.2), t_of(185), -24)   # the name fades (sand)
    place(tr, boom(2.0), t_of(A_END - 8), -6)                      # into black
    place(tr, thump(46, 0.5), t_of(EYE) - 0.18, -6); place(tr, thump(42, 0.5), t_of(EYE) + 0.12, -9)   # heartbeat
    place(tr, ping(2600, 1.2), t_of(EYE), -22)                      # the eye glints
    place(tr, whoosh(0.5, 300, 4000, rise=True), t_of(TEAR) - 0.5, -18)
    place(tr, rip(0.9), t_of(TEAR), -4)                             # THE RIP
    place(tr, boom(2.4), t_of(TEAR), -3)
    place(tr, crackle(1.0, 120), t_of(TEAR) + 0.1, -16)             # ink droplets
    place(tr, growl(1.6), t_of(TEAR + 10), -6)                      # the beast roars
    place(tr, whoosh(1.1, 150, 5000, rise=True), t_of(LUNGE) - 0.1, -8)   # the lunge
    place(tr, impact(), t_of(HIT), 0)                               # hit
    return tr

def load_mono(path):
    import subprocess, tempfile, os
    tmp = tempfile.mktemp(suffix='.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', path, '-ac', '1', '-ar', str(SR), tmp], check=True)
    sr, x = wavfile.read(tmp); os.remove(tmp)
    return x.astype(np.float32) / 32768.0

def music_peak(x, win=0.5):
    """time (s) of the loudest half-second in a track"""
    w = n(win); e = np.convolve(x ** 2, np.ones(w) / w, mode='valid')
    return int(np.argmax(e)) / SR

def mix(vo_path, music_path, out):
    sfx = build_sfx(); L = len(sfx)
    vo = load_mono(vo_path); voT = np.zeros(L); place(voT, vo, t_of(15), 0)
    mus = np.zeros(L)
    if music_path:
        m = load_mono(music_path); pk = music_peak(m)
        # the riser's peak lands on the HIT; nothing of it before the eye
        start_in_track = max(0.0, pk - (t_of(HIT) - t_of(EYE)))
        seg = m[n(start_in_track):]; place(mus, seg, t_of(EYE), 0)
        mus[n(t_of(HIT) + 0.6):] *= np.linspace(1, 0, L - n(t_of(HIT) + 0.6)) ** 2
    # duck the room/sfx under the voice a little
    duck = 1 - 0.35 * np.clip(lp(np.abs(voT), 8) * 6, 0, 1)
    master = normalise(voT, 0.75) + normalise(sfx, 0.8) * duck * 0.9 + normalise(mus, 0.55) if mus.any() else normalise(voT, 0.75) + normalise(sfx, 0.8) * duck * 0.9
    master = np.tanh(master * 1.1) * 0.92
    st = np.stack([master, master], 1)
    # tiny stereo width on sfx (Haas)
    d = n(0.012); st[d:, 1] = 0.85 * master[:-d] + 0.15 * st[d:, 1]
    wavfile.write(out, SR, (st * 32767).astype(np.int16))
    return out

if __name__ == '__main__':
    print(mix(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] != '-' else None, sys.argv[3]))
