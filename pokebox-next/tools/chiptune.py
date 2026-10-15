# Pokebox Next — original chiptune music + sound effects, generated in code (Game Boy style: 2 pulse voices, a triangle bass
# and a noise drum). Everything here is composed for this project, so it carries no licence. Output: 44.1 kHz 16-bit mono WAVs.
# usage: python chiptune.py <out dir>
import sys, os, math, wave, struct, random

SR = 44100

def note_hz(n):   # n = MIDI note number
    return 440.0 * 2 ** ((n - 69) / 12.0)

NOTES = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}
def N(s):   # 'C5' -> midi, '-' = rest
    if s in ('-', '.'): return None
    name, octv = (s[:-1], int(s[-1]))
    return 12 * (octv + 1) + NOTES[name]

def pulse(t, f, duty): return 1.0 if (t * f) % 1.0 < duty else -1.0
def tri(t, f): x = (t * f) % 1.0; return 4 * x - 1 if x < .5 else 3 - 4 * x

def render_voice(seq, step, kind, vol, duty=.5, out=None, dec=6.0):
    """seq: list of note strings, each one 'step' seconds; '.' holds the previous note, '-' is silence"""
    n_total = int(len(seq) * step * SR)
    buf = out if out is not None else [0.0] * n_total
    cur, start = None, 0
    events = []
    for i, s in enumerate(seq):
        if s == '.': continue
        if cur is not None: events.append((cur, start, i))
        cur, start = (N(s), i) if s != '-' else (None, i)
    if cur is not None: events.append((cur, start, len(seq)))
    for (m, a, b) in events:
        f = note_hz(m); i0, i1 = int(a * step * SR), int(b * step * SR)
        L = i1 - i0
        for k in range(L):
            t = k / SR
            env = min(1.0, k / 200.0) * math.exp(-dec * t / max(.25, (b - a) * step)) * min(1.0, (L - k) / 300.0)
            v = pulse(t, f, duty) if kind == 'pulse' else tri(t, f)
            buf[i0 + k] += v * vol * env
    return buf

def render_noise(pattern, step, vol, out):
    """pattern: 'x' kick-ish, 's' snare, 'h' hat, '.' nothing"""
    rnd = random.Random(7)
    for i, c in enumerate(pattern):
        if c == '.': continue
        i0 = int(i * step * SR); L = int((.09 if c == 'h' else .16) * SR)
        for k in range(L):
            if i0 + k >= len(out): break
            t = k / SR
            if c == 'x': v = math.sin(2 * math.pi * (110 - 300 * t) * t) * math.exp(-t * 28)
            else: v = (rnd.random() * 2 - 1) * math.exp(-t * (38 if c == 'h' else 18)) * (.5 if c == 'h' else 1.0)
            out[i0 + k] += v * vol
    return out

def write(path, buf, gain=.85):
    peak = max(1e-6, max(abs(x) for x in buf))
    g = gain / peak
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(b''.join(struct.pack('<h', int(max(-1, min(1, x * g)) * 32767)) for x in buf))

def song(lead, harm, bass, drums, bpm, sub=4, duty_l=.25, duty_h=.5):
    step = 60.0 / bpm / sub
    n = int(len(lead) * step * SR)
    buf = [0.0] * n
    render_voice(lead, step, 'pulse', .30, duty_l, buf)
    if harm: render_voice(harm, step, 'pulse', .16, duty_h, buf)
    if bass: render_voice(bass, step, 'tri', .38, out=buf, dec=1.5)
    if drums: render_noise(drums, step, .22, buf)
    return buf

def seq(s): return s.split()

# ---------------------------------------------------------------- music (original melodies)
def town():   # warm, walking pace, C major, 4 bars x2 (loops)
    lead = seq("E5 . G5 . A5 . G5 . E5 . D5 . C5 . . . "
               "D5 . E5 . G5 . E5 . D5 . . . - . . . "
               "E5 . G5 . A5 . C6 . B5 . A5 . G5 . . . "
               "A5 . G5 . E5 . D5 . C5 . . . - . . . ")
    harm = seq("C5 . . . E5 . . . C5 . . . E5 . . . "
               "B4 . . . D5 . . . B4 . . . G4 . . . "
               "C5 . . . E5 . . . F5 . . . E5 . . . "
               "F5 . . . D5 . . . E5 . . . - . . . ")
    bass = seq("C3 . . . G3 . . . A2 . . . E3 . . . "
               "G2 . . . D3 . . . G2 . . . B2 . . . "
               "F2 . . . C3 . . . C3 . . . G3 . . . "
               "F2 . . . G2 . . . C3 . . . G2 . . . ")
    drums = "x...h...s...h..." * 4
    return song(lead * 2, harm * 2, bass * 2, drums * 2, 112)

def route():   # brisk adventure, G major
    lead = seq("D5 . G5 . B5 . A5 G5 F#5 . G5 . A5 . . . "
               "B5 . A5 . G5 . D5 . E5 . F#5 . G5 . . . "
               "D5 . G5 . B5 . D6 . C6 . B5 . A5 . . . "
               "G5 . A5 . B5 . A5 . G5 . . . - . . . ")
    harm = seq("B4 . . . D5 . . . C5 . . . C5 . . . "
               "D5 . . . B4 . . . C5 . . . B4 . . . "
               "B4 . . . D5 . . . E5 . . . F#5 . . . "
               "E5 . . . C5 . . . B4 . . . - . . . ")
    bass = seq("G2 . G3 . G2 . G3 . C3 . C3 . D3 . D3 . "
               "E2 . E3 . E2 . E3 . C3 . C3 . D3 . D3 . "
               "G2 . G3 . G2 . G3 . A2 . A3 . D3 . D3 . "
               "C3 . C3 . D3 . D3 . G2 . G2 . G2 . . . ")
    drums = "x.h.s.h.x.h.s.hh" * 4
    return song(lead * 2, harm * 2, bass * 2, drums * 2, 132)

def battle():   # driving, A minor
    lead = seq("A5 . A5 C6 . A5 G5 . E5 . G5 A5 . . - . "
               "A5 . A5 C6 . D6 E6 . D6 . C6 B5 . . - . "
               "F5 . F5 A5 . F5 E5 . C5 . E5 F5 . . - . "
               "G5 . G5 B5 . D6 C6 . B5 . G5 E5 . . - . ")
    harm = seq("E5 . E5 E5 . E5 D5 . C5 . D5 E5 . . - . "
               "E5 . E5 A5 . A5 C6 . B5 . A5 G5 . . - . "
               "C5 . C5 F5 . C5 C5 . A4 . C5 C5 . . - . "
               "D5 . D5 G5 . B5 A5 . G5 . D5 B4 . . - . ")
    bass = seq("A2 A3 A2 A3 A2 A3 A2 A3 A2 A3 A2 A3 A2 A3 G2 G3 "
               "A2 A3 A2 A3 A2 A3 A2 A3 A2 A3 A2 A3 A2 A3 E2 E3 "
               "F2 F3 F2 F3 F2 F3 F2 F3 F2 F3 F2 F3 F2 F3 E2 E3 "
               "G2 G3 G2 G3 G2 G3 G2 G3 E2 E3 E2 E3 E2 E3 E2 E3 ")
    drums = "x.hsx.hsx.hsxshs" * 4
    return song(lead * 2, harm * 2, bass * 2, drums * 2, 150, duty_l=.125)

def jingle(notes, bpm, sub=4, bass=None):
    return song(seq(notes), None, seq(bass) if bass else None, None, bpm, sub)

# ---------------------------------------------------------------- sound effects
def sweep(f0, f1, dur, duty=.5, vol=.6, kind='pulse'):
    L = int(dur * SR); out = []
    ph = 0.0
    for k in range(L):
        t = k / SR; f = f0 + (f1 - f0) * (k / L); ph += f / SR
        v = (1.0 if ph % 1 < duty else -1.0) if kind == 'pulse' else (4 * (ph % 1) - 1 if ph % 1 < .5 else 3 - 4 * (ph % 1))
        out.append(v * vol * min(1, k / 60.0) * (1 - k / L))
    return out

def noise(dur, decay, vol=.6, seed=3):
    r = random.Random(seed); L = int(dur * SR)
    return [(r.random() * 2 - 1) * vol * math.exp(-decay * k / SR) for k in range(L)]

def cat(*parts):
    out = []
    for p in parts: out += p
    return out

def mix(a, b):
    n = max(len(a), len(b)); return [(a[i] if i < len(a) else 0) + (b[i] if i < len(b) else 0) for i in range(n)]

def sfx():
    S = {}
    S['sfx_confirm'] = cat(sweep(990, 990, .05, .5, .5), sweep(1320, 1320, .07, .5, .5))
    S['sfx_cancel'] = cat(sweep(660, 660, .05, .5, .5), sweep(440, 440, .08, .5, .5))
    S['sfx_cursor'] = sweep(1200, 1200, .03, .25, .35)
    S['sfx_hit'] = mix(noise(.18, 22, .9), sweep(320, 80, .14, .5, .5))
    S['sfx_hit_big'] = mix(noise(.32, 12, 1.0, 5), sweep(500, 60, .3, .25, .6))
    S['sfx_faint'] = sweep(700, 90, .55, .5, .55)
    S['sfx_ball_throw'] = sweep(300, 1400, .22, .5, .4, 'tri')
    S['sfx_ball_shake'] = cat(noise(.05, 60, .6), [0.0] * int(.05 * SR), noise(.05, 60, .6))
    S['sfx_capture'] = cat(sweep(784, 784, .08), sweep(988, 988, .08), sweep(1175, 1175, .08), sweep(1568, 1568, .2))
    S['sfx_door'] = mix(noise(.12, 30, .5, 9), sweep(180, 120, .12, .5, .3, 'tri'))
    S['sfx_coin'] = cat(sweep(1319, 1319, .06, .25, .5), sweep(1976, 1976, .16, .25, .5))
    S['sfx_card_flip'] = mix(noise(.07, 50, .5, 11), sweep(600, 1500, .08, .5, .25, 'tri'))
    S['sfx_step'] = noise(.04, 90, .25, 13)
    S['sfx_spotted'] = cat(sweep(1568, 1568, .06, .25, .6), [0.0] * int(.03 * SR), sweep(1568, 1568, .12, .25, .6))   # the "!" before a trainer battle
    S['sfx_levelup'] = cat(sweep(1047, 1047, .07), sweep(1319, 1319, .07), sweep(1568, 1568, .07), sweep(2093, 2093, .18))
    return S

if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else 'audio'
    os.makedirs(out, exist_ok=True)
    write(os.path.join(out, 'mus_town.wav'), town())
    write(os.path.join(out, 'mus_route.wav'), route())
    write(os.path.join(out, 'mus_battle.wav'), battle())
    write(os.path.join(out, 'jin_victory.wav'), jingle("C5 E5 G5 C6 . . - G5 C6 . . . . . . .", 150, 4, "C3 . . . . . . . G2 . . . C3 . . ."))
    write(os.path.join(out, 'jin_heal.wav'), jingle("G5 . E5 . C5 . E5 . G5 . C6 . . . . .", 160, 4))
    write(os.path.join(out, 'jin_badge.wav'), jingle("G5 G5 G5 . E5 . G5 . C6 . . . . . . .", 140, 4, "C3 . . . . . . . C3 . . . . . . ."))
    for k, v in sfx().items(): write(os.path.join(out, k + '.wav'), v, .8)
    print('written', sorted(os.listdir(out)))
