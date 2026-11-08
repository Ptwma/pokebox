# Sigil & Spark — "Codex" UI sounds (synthesised, original): paper and quill instead of chiptune blips.
#   sfx_cursor  a soft paper flick (menu / move cursor)
#   sfx_confirm a quill stroke + a wax-seal press (pick)
#   ui_page     a page turning (a menu / choice opens)
#   ui_quill    a short quill scratch (toast / new objective written)
#   python ui_codex_sfx.py <out_dir>   → 48 kHz mono 16-bit wavs (import with pbx_build.import_audio)
import sys, os, numpy as np
from scipy.io import wavfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'intro'))
import legend_sfx as S

R = np.random.default_rng(11)

def noise(sec): return R.normal(0, 1, S.n(sec))

def paper_flick():
    x = S.bp(noise(0.09), 1800, 7000) * S.env(S.n(0.09), 0.004, 0.08, 4.0)
    tick = S.bp(noise(0.02), 3000, 9000) * S.env(S.n(0.02), 0.001, 0.018, 6.0)
    out = np.zeros(S.n(0.12)); out[:len(x)] += x; out[S.n(0.012):S.n(0.012) + len(tick)] += tick * 0.6
    return out

def quill(sec=0.22, strokes=3):
    x = S.bp(noise(sec), 2600, 9000)
    t = np.linspace(0, 1, len(x))
    am = np.clip(np.sin(t * np.pi * strokes) ** 2, 0, 1) * (0.5 + 0.5 * np.abs(R.normal(0, 1, len(x))).clip(0, 2) / 2)
    am = S.lp(am, 60, 2)
    return x * am * S.env(len(x), 0.01, sec * 0.6)

def seal_press():
    th = S.thump(140, 0.16, 0.35)
    body = S.lp(noise(0.12), 900) * S.env(S.n(0.12), 0.003, 0.1, 5.0)
    out = np.zeros(max(len(th), len(body))); out[:len(th)] += th; out[:len(body)] += body * 0.5
    return out

def page_turn():
    sec = 0.55; x = noise(sec); t = np.linspace(0, 1, len(x))
    # a swish whose band sweeps up then down while the page lifts and falls
    lo = S.bp(x, 300, 1800); hi = S.bp(x, 1800, 7000)
    sweep = np.sin(t * np.pi) ** 1.5
    sw = lo * (1 - sweep) * 0.6 + hi * sweep
    crinkle = S.bp(noise(sec), 3000, 10000) * (R.random(len(x)) > 0.985) * 3.0
    out = (sw + S.lp(crinkle, 9000)) * S.env(len(x), 0.08, 0.3, 2.5)
    land = S.lp(noise(0.06), 1200) * S.env(S.n(0.06), 0.002, 0.05, 5.0)
    o = np.zeros(len(out) + S.n(0.05)); o[:len(out)] += out; o[S.n(0.44):S.n(0.44) + len(land)] += land * 0.8
    return o

def write(path, x, peak):
    x = x / (np.abs(x).max() + 1e-9) * peak
    fade = min(len(x), S.n(0.01)); x[-fade:] *= np.linspace(1, 0, fade)
    wavfile.write(path, S.SR, (x * 32767).astype(np.int16))

if __name__ == '__main__':
    out = sys.argv[1]; os.makedirs(out, exist_ok=True)
    write(os.path.join(out, 'sfx_cursor.wav'), paper_flick(), 0.5)
    q = quill(0.2, 2); s = seal_press(); c = np.zeros(len(q) + len(s)); c[:len(q)] += q; c[S.n(0.15):S.n(0.15) + len(s)] += s * 1.4
    write(os.path.join(out, 'sfx_confirm.wav'), c, 0.7)
    write(os.path.join(out, 'ui_page.wav'), page_turn(), 0.6)
    write(os.path.join(out, 'ui_quill.wav'), quill(0.32, 3), 0.45)
    print('ok')
