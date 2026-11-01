# Sigil & Spark — full legend intro: timeline + score (narration, synthesised SFX, suspense bed, riser into the hit,
# title boom). Uses the synth functions of legend_sfx.py.
#   python legend_full_sfx.py <audio_dir> <music_dir> <out_wav>   → also prints the page offsets for the video join
import sys, os, json, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import legend_sfx as S
from scipy.io import wavfile

FPS = 24
# page order and lengths (frames); P5/P7 come from the sample render (LEGEND_BOOK 1–270 / 271–384)
PAGES = [('P1', 270), ('P2', 180), ('P3', 200), ('P4', 486), ('P5', 270), ('P6', 435), ('P7', 114), ('P8', 176)]
VO = {'P1': ('vo_leg_01.wav', 19), 'P2': ('vo_leg_02.wav', 6), 'P3': ('vo_leg_03.wav', 6), 'P4': ('vo_leg_04.wav', 8),
      'P5': ('vo_leg_05.wav', 15), 'P6': ('vo_leg_06.wav', 24), 'P8': ('vo_leg_08.wav', 30)}

def offsets():
    o, t = {}, 0
    for p, n in PAGES: o[p] = t; t += n
    return o, t

def T(page, frame, off): return (off[page] + frame - 1) / FPS

def build(audio_dir, music_dir, out):
    off, total = offsets(); L = S.n(total / FPS + 1.5)
    sfx = np.zeros(L); vo = np.zeros(L); bed = np.zeros(L); hit = np.zeros(L)
    for p, (f, at) in VO.items():
        x = S.load_mono(os.path.join(audio_dir, f)); S.place(vo, x, T(p, at, off), 0)
    # room tone throughout, very low
    rt = S.room(L); S.place(sfx, rt, 0, -32)
    # P1: a quill scratching while the script writes itself
    for k in range(9):
        sc = S.bp(S.rng.normal(0, 1, S.n(0.7)), 2500, 8000) * (0.4 + 0.6 * np.abs(np.sin(np.linspace(0, 18, S.n(0.7))))) * S.env(S.n(0.7), 0.05, 0.2)
        S.place(sfx, sc, T('P1', 34 + k * 11, off), -16)
    S.place(sfx, S.ping(1800, 1.6), T('P1', 200, off), -24)                     # the drawn Spark comes alive
    # P2: candle crackle, a soft gust
    S.place(sfx, S.crackle(6.0, 14), T('P2', 1, off), -24)
    # P3: the crowd's murmur + the book's clasp + the cover opening (whoosh) + warm light hum
    mur = S.bp(S.rng.normal(0, 1, S.n(8.5)), 250, 1200) * (0.6 + 0.4 * np.sin(np.linspace(0, 30, S.n(8.5))) ** 2) * S.env(S.n(8.5), 1.5, 2.0)
    S.place(sfx, mur, T('P3', 1, off), -20)
    S.place(sfx, S.thump(120, 0.15, 0.2), T('P3', 120, off), -12)
    S.place(sfx, S.whoosh(1.2, 200, 2000), T('P3', 126, off), -14)
    # P4: a bell for each waking page (1 · 2 · 3), the third one bigger, gold sparks
    s4 = VO['P4'][1]
    for sec, f, g in ((0.8, 1320, -16), (7.2, 1320, -16), (7.9, 1660, -16), (9.8, 1320, -15), (10.6, 1660, -15), (11.6, 1980, -10)):
        S.place(sfx, S.ping(f, 2.5), T('P4', int(s4 + sec * FPS), off), g)
    S.place(sfx, S.crackle(3.0, 60), T('P4', int(s4 + 11.6 * FPS), off), -22)
    # P5 + P7: the sample's sound design, re-placed
    a5 = off['P5'] / FPS
    for i in range(5): S.place(sfx, S.whoosh(0.5, 250, 1400), a5 + (170 + i * 16 - 1) / FPS, -14 - i)
    S.place(sfx, S.crackle(2.5, 30), a5 + 91 / FPS, -16)
    S.place(sfx, S.boom(2.0), a5 + 262 / FPS, -6)
    # P6: a whisper bed (formant-filtered noise), the candle dies, masks — a low drone
    wh = S.bp(S.rng.normal(0, 1, S.n(4.0)), 1800, 5200) * (np.abs(np.sin(np.linspace(0, 40, S.n(4.0)))) ** 3) * S.env(S.n(4.0), 0.6, 1.0)
    S.place(sfx, wh, T('P6', 30, off), -22)
    S.place(sfx, S.whoosh(0.6, 250, 1200), T('P6', 24 + 9 * FPS, off), -16)
    t6 = np.arange(S.n(5.5)) / S.SR; drone = (np.sin(2 * np.pi * 41 * t6) + 0.5 * np.sin(2 * np.pi * 61.5 * t6)) * S.env(len(t6), 2.0, 1.5)
    S.place(sfx, drone, T('P6', 24 + 12 * FPS, off), -12)
    # P7: heartbeat → glint → rip → boom → roar → lunge → impact (frames relative to the sample's B part: TEAR=312 → P7 frame 42)
    def p7(f_sample): return T('P7', f_sample - 270, off)
    S.place(sfx, S.thump(46, 0.5), p7(300) - 0.18, -6); S.place(sfx, S.thump(42, 0.5), p7(300) + 0.12, -9)
    S.place(sfx, S.ping(2600, 1.2), p7(300), -22)
    S.place(sfx, S.whoosh(0.5, 300, 4000, rise=True), p7(312) - 0.5, -18)
    S.place(sfx, S.rip(0.9), p7(312), -4); S.place(sfx, S.boom(2.4), p7(312), -3); S.place(sfx, S.crackle(1.0, 120), p7(312) + 0.1, -16)
    S.place(sfx, S.growl(1.6), p7(322), -6)
    S.place(sfx, S.whoosh(1.1, 150, 5000, rise=True), p7(340) - 0.1, -8)
    S.place(hit, S.impact(), p7(372), 0)
    # P8: silence → the drop (plink) → the glyph burns (sizzle + low swell) → TITLE boom
    s8 = VO['P8'][1]; DROP = s8 + int(2.6 * FPS); GLY = DROP + 8; TITLE = DROP + 46
    tp = np.arange(S.n(0.6)) / S.SR; plink = np.sin(2 * np.pi * 900 * tp * (1 + 0.6 * np.exp(-tp * 30))) * np.exp(-tp * 9)
    S.place(sfx, plink, T('P8', DROP, off), -10)
    S.place(sfx, S.bp(S.rng.normal(0, 1, S.n(1.6)), 2000, 9000) * S.env(S.n(1.6), 0.05, 1.0), T('P8', GLY, off), -18)
    S.place(sfx, S.thump(55, 0.6), T('P8', GLY, off), -8)
    S.place(hit, S.boom(3.0), T('P8', TITLE, off), -2)
    # music: the suspense bed under P1–P6 (low), the riser lands on the hit, quiet after; a final swell on the title
    sus = S.load_mono(os.path.join(music_dir, 'gregor_quendel_-_cinematic_trailer_music_-_variations_-_05_-_cinematic_suspense_trailer_-_extended_percussion_version.mp3'))
    end_bed = off['P7'] / FPS
    seg = sus[:S.n(end_bed)].copy(); seg *= S.env(len(seg), 3.0, 2.5, 2.0)
    S.place(bed, seg, 0, 0)
    ris = S.load_mono(os.path.join(music_dir, 'gregor_quendel_-_cinematic_trailer_music_-_13_-_cinematic_epic_hybrid_riser.mp3'))
    pk = S.music_peak(ris); t_hit = p7(372); start_t = p7(300)
    rs = ris[S.n(max(0.0, pk - (t_hit - start_t))):]; rs = rs[:S.n(t_hit - start_t + 1.2)]; rs *= S.env(len(rs), 0.3, 0.9)
    S.place(bed, rs * 1.6, start_t, 0)
    tail = sus[S.n(40):S.n(40 + 9)].copy() if len(sus) > S.n(49) else sus[-S.n(9):].copy()
    tail *= S.env(len(tail), 1.0, 2.5); S.place(bed, tail, T('P8', 1, off), -6)
    # mix: voice on top, sfx ducked under the voice, music lower still and ducked
    duck = 1 - 0.45 * np.clip(S.lp(np.abs(vo), 6) * 8, 0, 1)
    vo_n = vo / (np.abs(vo).max() + 1e-9) * 0.72
    sfx_n = sfx / (np.abs(sfx).max() + 1e-9) * 0.55
    bed_n = bed / (np.abs(bed).max() + 1e-9) * 0.42
    hit_n = hit / (np.abs(hit).max() + 1e-9) * 0.85
    master = vo_n + sfx_n * duck + bed_n * duck + hit_n
    master = np.tanh(master * 1.15) * 0.93
    st = np.stack([master, master], 1); d = S.n(0.012); st[d:, 1] = 0.85 * master[:-d] + 0.15 * st[d:, 1]
    st = st[:S.n(total / FPS)]
    wavfile.write(out, S.SR, (st * 32767).astype(np.int16))
    return off, total

if __name__ == '__main__':
    off, total = build(sys.argv[1], sys.argv[2], sys.argv[3])
    print(json.dumps({'offsets': off, 'total_frames': total, 'seconds': total / FPS}))
