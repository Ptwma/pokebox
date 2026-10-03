// Tiny synthesized sound kit (no audio files needed)
let ctx = null, master = null, enabled = true;
export function setSound(on) { enabled = on; }
function ac() {
  if (!enabled) return null;
  if (!ctx) { try { ctx = new (window.AudioContext || window.webkitAudioContext)(); master = ctx.createGain(); master.gain.value = .5; master.connect(ctx.destination); } catch { return null; } }
  if (ctx.state === 'suspended') ctx.resume();
  return ctx;
}
function noise(dur) {
  const c = ctx, b = c.createBuffer(1, Math.ceil(c.sampleRate * dur), c.sampleRate), d = b.getChannelData(0);
  for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
  const s = c.createBufferSource(); s.buffer = b; return s;
}
function env(g, t, a, peak, dcy) { g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(peak, t + a); g.gain.exponentialRampToValueAtTime(0.0001, t + a + dcy); }
function tone(freq, t, dur, type = 'sine', vol = .2, slide = 0) {
  const o = ctx.createOscillator(), g = ctx.createGain(); o.type = type; o.frequency.setValueAtTime(freq, t);
  if (slide) o.frequency.exponentialRampToValueAtTime(Math.max(20, freq * slide), t + dur);
  env(g, t, .005, vol, dur); o.connect(g).connect(master); o.start(t); o.stop(t + dur + .05);
}
export const sfx = {
  tick() { if (!ac()) return; tone(1400, ctx.currentTime, .03, 'sine', .025); },
  click() { if (!ac()) return; tone(900, ctx.currentTime, .05, 'triangle', .06); },
  coin() { if (!ac()) return; const t = ctx.currentTime; tone(988, t, .08, 'square', .06); tone(1319, t + .07, .22, 'square', .06); },
  whoosh(d = .5) {
    if (!ac()) return; const t = ctx.currentTime, n = noise(d), f = ctx.createBiquadFilter(), g = ctx.createGain();
    f.type = 'bandpass'; f.Q.value = 1.2; f.frequency.setValueAtTime(300, t); f.frequency.exponentialRampToValueAtTime(3200, t + d * .7);
    env(g, t, d * .35, .35, d * .6); n.connect(f).connect(g).connect(master); n.start(t); n.stop(t + d + .1);
  },
  rip() {
    if (!ac()) return; const t = ctx.currentTime;
    for (let k = 0; k < 7; k++) {
      const n = noise(.08), f = ctx.createBiquadFilter(), g = ctx.createGain(); f.type = 'highpass'; f.frequency.value = 1800 + Math.random() * 2500;
      env(g, t + k * .028, .004, .45, .06); n.connect(f).connect(g).connect(master); n.start(t + k * .028); n.stop(t + k * .028 + .1);
    }
  },
  burst() {
    if (!ac()) return; const t = ctx.currentTime;
    [523, 659, 784, 1047, 1319].forEach((f, i) => tone(f, t + i * .045, .9, 'sine', .07));
    const n = noise(1.2), fl = ctx.createBiquadFilter(), g = ctx.createGain(); fl.type = 'highpass'; fl.frequency.value = 6000;
    env(g, t, .02, .08, 1.1); n.connect(fl).connect(g).connect(master); n.start(t); n.stop(t + 1.3);
  },
  sparkle() { if (!ac()) return; const t = ctx.currentTime; [2093, 2637, 3136].forEach((f, i) => tone(f, t + i * .06, .35, 'sine', .04)); },
  rare(level = 1) {
    if (!ac()) return; const t = ctx.currentTime; const base = [392, 494, 587, 784, 988, 1175];
    base.slice(0, 3 + level).forEach((f, i) => { tone(f, t + i * .07, 1.2, 'triangle', .07); tone(f * 2, t + i * .07, .8, 'sine', .03); });
  },
  zap() {
    if (!ac()) return; const t = ctx.currentTime;
    for (let k = 0; k < 6; k++) { const n = noise(.05), f = ctx.createBiquadFilter(), g = ctx.createGain(); f.type = 'bandpass'; f.frequency.value = 2500 + Math.random() * 4000; f.Q.value = 3;
      env(g, t + k * .035, .002, .35, .04); n.connect(f).connect(g).connect(master); n.start(t + k * .035); n.stop(t + k * .035 + .08); }
    tone(90, t, .3, 'sawtooth', .08, 2.2);
  },
  thunder() {
    if (!ac()) return; const t = ctx.currentTime, n = noise(1.6), f = ctx.createBiquadFilter(), g = ctx.createGain(); f.type = 'lowpass'; f.frequency.setValueAtTime(3000, t); f.frequency.exponentialRampToValueAtTime(180, t + 1.4);
    env(g, t, .01, .55, 1.5); n.connect(f).connect(g).connect(master); n.start(t); n.stop(t + 1.7); this.zap();
  },
  boom(v = 1) {
    if (!ac()) return; const t = ctx.currentTime; tone(110, t, .7 * v, 'sine', .35 * v, .3);
    const n = noise(.8), f = ctx.createBiquadFilter(), g = ctx.createGain(); f.type = 'lowpass'; f.frequency.value = 900; env(g, t, .005, .4 * v, .7); n.connect(f).connect(g).connect(master); n.start(t); n.stop(t + .9);
  },
  pop() { if (!ac()) return; const t = ctx.currentTime; tone(600, t, .12, 'square', .08, .4); const n = noise(.06), g = ctx.createGain(); env(g, t, .002, .3, .05); n.connect(g).connect(master); n.start(t); n.stop(t + .08); },
  thud() { if (!ac()) return; tone(140, ctx.currentTime, .25, 'sine', .3, .4); },
  charge(d = 2) {
    if (!ac()) return; const t = ctx.currentTime, o = ctx.createOscillator(), g = ctx.createGain(), f = ctx.createBiquadFilter();
    o.type = 'sawtooth'; o.frequency.setValueAtTime(80, t); o.frequency.exponentialRampToValueAtTime(900, t + d); f.type = 'lowpass'; f.frequency.setValueAtTime(400, t); f.frequency.exponentialRampToValueAtTime(5000, t + d);
    g.gain.setValueAtTime(.0001, t); g.gain.exponentialRampToValueAtTime(.09, t + d * .9); g.gain.exponentialRampToValueAtTime(.0001, t + d + .05);
    o.connect(f).connect(g).connect(master); o.start(t); o.stop(t + d + .1);
  },
  flame(d = 1) {
    if (!ac()) return; const t = ctx.currentTime, n = noise(d), f = ctx.createBiquadFilter(), g = ctx.createGain(); f.type = 'lowpass'; f.frequency.value = 700;
    env(g, t, d * .3, .3, d * .65); n.connect(f).connect(g).connect(master); n.start(t); n.stop(t + d + .1);
  },
  plink() { if (!ac()) return; const t = ctx.currentTime, f = 900 + Math.random() * 900; tone(f, t, .09, 'sine', .05); tone(f * 2.4, t, .05, 'sine', .02); },
  clink() { if (!ac()) return; const t = ctx.currentTime, f = 2400 + Math.random() * 1600; tone(f, t, .12, 'triangle', .035); tone(f * 1.5, t + .01, .08, 'sine', .02); },
  hit() { if (!ac()) return; const t = ctx.currentTime; tone(160, t, .25, 'sawtooth', .18, .4); const n = noise(.15), g = ctx.createGain(); env(g, t, .003, .3, .12); n.connect(g).connect(master); n.start(t); n.stop(t + .2); },
  ko() { if (!ac()) return; const t = ctx.currentTime; tone(440, t, .6, 'square', .08, .25); },
  win() { if (!ac()) return; const t = ctx.currentTime; [523, 659, 784, 1047].forEach((f, i) => tone(f, t + i * .12, .5, 'square', .06)); },
  lose() { if (!ac()) return; const t = ctx.currentTime; [392, 330, 262].forEach((f, i) => tone(f, t + i * .18, .5, 'triangle', .08)); },
};

/* ---------- title theme: an original 8-bar chiptune loop (square lead, triangle bass, noise hats), scheduled ahead in WebAudio */
const NOTE = n => { if (n === 'R') return 0; const m = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 }[n[0]], o = +n[n.length - 1], s = n.length === 3 ? (n[1] === '#' ? 1 : -1) : 0; return 440 * Math.pow(2, (m + s + (o - 4) * 12 - 9) / 12); };
const LEAD = [['E5', 1], ['G5', 1], ['C6', 2], ['B5', 1], ['A5', 1], ['G5', 2], ['A5', 1], ['B5', 1], ['C6', 1], ['D6', 1], ['E6', 2], ['D6', 2],
  ['C6', 1], ['A5', 1], ['F5', 2], ['G5', 1], ['A5', 1], ['G5', 2], ['E5', 1], ['F5', 1], ['G5', 1], ['E5', 1], ['D5', 4],
  ['E5', 1], ['G5', 1], ['C6', 2], ['B5', 1], ['A5', 1], ['G5', 2], ['A5', 1], ['C6', 1], ['E6', 2], ['D6', 1], ['C6', 1], ['A5', 2],
  ['F5', 1], ['A5', 1], ['G5', 1], ['E5', 1], ['D5', 2], ['G5', 2], ['C5', 4], ['R', 4]];
const BASS = [['C3', 'G3'], ['F2', 'C3'], ['D3', 'A3'], ['G2', 'D3'], ['C3', 'G3'], ['A2', 'E3'], ['F2', 'G2'], ['C3', 'G2']];
let musT = null, musGain = null, musOn = false;
export const music = {
  title() {
    if (musOn || !ac()) return; musOn = true;
    musGain = ctx.createGain(); musGain.gain.value = .0001; musGain.connect(master); musGain.gain.exponentialRampToValueAtTime(.55, ctx.currentTime + .8);
    const E = 60 / 132 / 2; let bar0 = ctx.currentTime + .1;
    const blip = (f, t, d, type, v) => { if (!f) return; const o = ctx.createOscillator(), g = ctx.createGain(); o.type = type; o.frequency.setValueAtTime(f, t);
      g.gain.setValueAtTime(.0001, t); g.gain.exponentialRampToValueAtTime(v, t + .01); g.gain.setValueAtTime(v * .8, t + d * .6); g.gain.exponentialRampToValueAtTime(.0001, t + d * .95);
      o.connect(g).connect(musGain); o.start(t); o.stop(t + d); };
    const hat = (t, v) => { const n = noise(.05), f = ctx.createBiquadFilter(), g = ctx.createGain(); f.type = 'highpass'; f.frequency.value = 7000; g.gain.setValueAtTime(v, t); g.gain.exponentialRampToValueAtTime(.0001, t + .04); n.connect(f).connect(g).connect(musGain); n.start(t); n.stop(t + .06); };
    const kick = t => { const o = ctx.createOscillator(), g = ctx.createGain(); o.frequency.setValueAtTime(150, t); o.frequency.exponentialRampToValueAtTime(40, t + .12); g.gain.setValueAtTime(.35, t); g.gain.exponentialRampToValueAtTime(.0001, t + .16); o.connect(g).connect(musGain); o.start(t); o.stop(t + .2); };
    const loop = () => {
      if (!musOn) return; let t = bar0;
      for (const [n, l] of LEAD) { blip(NOTE(n), t, l * E, 'square', .07); blip(NOTE(n) * 2, t + .012, l * E * .5, 'triangle', .015); t += l * E; }
      BASS.forEach(([a, b], i) => { for (let q = 0; q < 4; q++) blip(NOTE(q % 2 ? b : a), bar0 + (i * 8 + q * 2) * E, E * 1.8, 'triangle', .16); });
      for (let k = 0; k < 64; k++) { hat(bar0 + k * E, k % 2 ? .025 : .045); if (k % 4 === 0) kick(bar0 + k * E); }
      bar0 += 64 * E; musT = setTimeout(loop, Math.max(100, (bar0 - ctx.currentTime - 1.5) * 1000));
    };
    loop();
  },
  stop(fade = 1) { if (!musOn) return; musOn = false; clearTimeout(musT); const g = musGain; if (g && ctx) { g.gain.cancelScheduledValues(ctx.currentTime); g.gain.setValueAtTime(g.gain.value, ctx.currentTime); g.gain.exponentialRampToValueAtTime(.0001, ctx.currentTime + fade); setTimeout(() => g.disconnect(), fade * 1000 + 200); } },
  get playing() { return musOn; },
};

/* ================= world score: an original, generated soundtrack per region (no audio files) =================
   Each region has a key, mode, chord loop, tempo, lead voice and an ambience bed (waves, wind, birds, crickets, rumble).
   The melody is composed on the fly from the scale: a 4-bar motif played A A' B A' with chord tones on strong beats,
   so it sounds written rather than random but never loops exactly. Night = slower, sparser, crickets.
   Battles switch to a driving chiptune variant of the same engine. Volume is kept under the sound effects. */
const SCALES = { maj: [0, 2, 4, 7, 9], min: [0, 3, 5, 7, 10], dor: [0, 2, 3, 5, 7, 9, 10], hij: [0, 1, 4, 5, 7, 8, 10], whole: [0, 2, 4, 6, 8, 10], lyd: [0, 2, 4, 6, 7, 9, 11] };
const THEMES = {
  harbor:    { root: 'F3', scale: 'maj', prog: [[0, 'M'], [9, 'm'], [5, 'M'], [7, 'M']], bpm: 92, lead: 'pluck', perc: 'shaker', amb: ['waves'] },
  mistvale:  { root: 'D3', scale: 'dor', prog: [[0, 'm'], [10, 'M'], [3, 'M'], [5, 'm']], bpm: 76, lead: 'flute', amb: ['birds', 'waves'] },
  starfall:  { root: 'A2', scale: 'min', prog: [[0, 'm'], [8, 'M'], [3, 'M'], [10, 'M']], bpm: 64, lead: 'bell', amb: ['crickets'] },
  frostline: { root: 'E3', scale: 'min', prog: [[0, 'm'], [5, 'm'], [8, 'M'], [7, 'm']], bpm: 70, lead: 'bell', amb: ['wind'] },
  voltspire: { root: 'C3', scale: 'dor', prog: [[0, 'm'], [3, 'M'], [10, 'M'], [5, 'M']], bpm: 104, lead: 'reed', perc: 'shaker', amb: ['wind'] },
  sandreach: { root: 'D3', scale: 'hij', prog: [[0, 'M'], [1, 'M'], [0, 'M'], [10, 'm']], bpm: 84, lead: 'pluck', perc: 'shaker', amb: ['wind'] },
  rift:      { root: 'B2', scale: 'whole', prog: [[0, 'm'], [1, 'M'], [0, 'm'], [6, 'M']], bpm: 56, lead: 'bell', amb: ['rumble'] },
  battle:    { root: 'A2', scale: 'min', prog: [[0, 'm'], [8, 'M'], [10, 'M'], [7, 'M']], bpm: 148, lead: 'chip', perc: 'drums', amb: [] },
};
let wm = null; // { id, night, gain, timer, ambNodes, bar0, seed }
let musicOn = true;
export function setMusic(on) { musicOn = on; if (!on) music.world(null); }
function rnd(seed) { let s = seed >>> 0 || 1; return () => ((s = (Math.imul(s, 1664525) + 1013904223) >>> 0) / 4294967296); }
function voice(kind, f, t, d, v, out) {
  const g = ctx.createGain(); g.connect(out);
  if (kind === 'pad') { for (const det of [-6, 5]) { const o = ctx.createOscillator(); o.type = 'triangle'; o.frequency.value = f; o.detune.value = det; const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 900; o.connect(lp).connect(g); o.start(t); o.stop(t + d + 2.2); }
    g.gain.setValueAtTime(.0001, t); g.gain.exponentialRampToValueAtTime(v, t + Math.min(1.4, d * .4)); g.gain.setValueAtTime(v, t + d); g.gain.exponentialRampToValueAtTime(.0001, t + d + 2); return; }
  const o = ctx.createOscillator(); o.frequency.setValueAtTime(f, t); let rel = d;
  if (kind === 'pluck') { o.type = 'triangle'; g.gain.setValueAtTime(.0001, t); g.gain.exponentialRampToValueAtTime(v, t + .008); g.gain.exponentialRampToValueAtTime(.0001, t + .55); rel = .6; }
  else if (kind === 'bell') { o.type = 'sine'; const o2 = ctx.createOscillator(), g2 = ctx.createGain(); o2.frequency.value = f * 2.76; g2.gain.setValueAtTime(v * .35, t); g2.gain.exponentialRampToValueAtTime(.0001, t + .5); o2.connect(g2).connect(out); o2.start(t); o2.stop(t + .6);
    g.gain.setValueAtTime(.0001, t); g.gain.exponentialRampToValueAtTime(v, t + .005); g.gain.exponentialRampToValueAtTime(.0001, t + 1.8); rel = 1.9; }
  else if (kind === 'flute') { o.type = 'sine'; const l = ctx.createOscillator(), lg = ctx.createGain(); l.frequency.value = 5.2; lg.gain.value = f * .006; l.connect(lg).connect(o.frequency); l.start(t); l.stop(t + d + .3);
    g.gain.setValueAtTime(.0001, t); g.gain.exponentialRampToValueAtTime(v, t + .09); g.gain.setValueAtTime(v * .85, t + d * .8); g.gain.exponentialRampToValueAtTime(.0001, t + d + .25); rel = d + .3; }
  else if (kind === 'reed') { o.type = 'square'; const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 1400; o.disconnect(); o.connect(lp).connect(g);
    g.gain.setValueAtTime(.0001, t); g.gain.exponentialRampToValueAtTime(v * .5, t + .03); g.gain.exponentialRampToValueAtTime(.0001, t + d + .15); rel = d + .2; o.start(t); o.stop(t + rel); return; }
  else if (kind === 'chip') { o.type = 'square'; g.gain.setValueAtTime(.0001, t); g.gain.exponentialRampToValueAtTime(v * .45, t + .005); g.gain.setValueAtTime(v * .35, t + d * .7); g.gain.exponentialRampToValueAtTime(.0001, t + d * .98); }
  else if (kind === 'bass') { o.type = 'sine'; g.gain.setValueAtTime(.0001, t); g.gain.exponentialRampToValueAtTime(v, t + .02); g.gain.exponentialRampToValueAtTime(.0001, t + d); }
  o.connect(g); o.start(t); o.stop(t + rel + .05);
}
function perc(kind, t, v, out) {
  if (kind === 'shaker') { const n = noise(.06), f = ctx.createBiquadFilter(), g = ctx.createGain(); f.type = 'highpass'; f.frequency.value = 6000; g.gain.setValueAtTime(v, t); g.gain.exponentialRampToValueAtTime(.0001, t + .05); n.connect(f).connect(g).connect(out); n.start(t); n.stop(t + .07); }
  if (kind === 'kick') { const o = ctx.createOscillator(), g = ctx.createGain(); o.frequency.setValueAtTime(140, t); o.frequency.exponentialRampToValueAtTime(42, t + .12); g.gain.setValueAtTime(v, t); g.gain.exponentialRampToValueAtTime(.0001, t + .16); o.connect(g).connect(out); o.start(t); o.stop(t + .2); }
  if (kind === 'snare') { const n = noise(.15), f = ctx.createBiquadFilter(), g = ctx.createGain(); f.type = 'bandpass'; f.frequency.value = 1800; g.gain.setValueAtTime(v, t); g.gain.exponentialRampToValueAtTime(.0001, t + .13); n.connect(f).connect(g).connect(out); n.start(t); n.stop(t + .16); }
}
function ambience(kinds, out) { // continuous beds + scheduled critters; returns a stop function
  const nodes = [], timers = [];
  const bed = (type, freq, q, base, depth, rate) => { const b = ctx.createBuffer(1, ctx.sampleRate * 4, ctx.sampleRate), d = b.getChannelData(0); for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    const s = ctx.createBufferSource(); s.buffer = b; s.loop = true; const f = ctx.createBiquadFilter(); f.type = type; f.frequency.value = freq; f.Q.value = q; const g = ctx.createGain(); g.gain.value = base;
    const l = ctx.createOscillator(), lg = ctx.createGain(); l.frequency.value = rate; lg.gain.value = depth; l.connect(lg).connect(g.gain); s.connect(f).connect(g).connect(out); s.start(); l.start(); nodes.push(s, l); };
  for (const k of kinds) {
    if (k === 'waves') bed('lowpass', 520, .7, .05, .035, 1 / 7);
    if (k === 'wind') bed('bandpass', 420, .8, .035, .025, 1 / 11);
    if (k === 'rumble') bed('lowpass', 110, .7, .08, .03, 1 / 9);
    if (k === 'birds' || k === 'crickets') { const tick = () => { if (!ctx) return; const t = ctx.currentTime + .05;
        if (k === 'birds') for (let i = 0, n = 2 + (Math.random() * 3 | 0); i < n; i++) { const o = ctx.createOscillator(), g = ctx.createGain(), f0 = 2300 + Math.random() * 1400; o.frequency.setValueAtTime(f0, t + i * .11); o.frequency.exponentialRampToValueAtTime(f0 * 1.45, t + i * .11 + .07); g.gain.setValueAtTime(.0001, t + i * .11); g.gain.exponentialRampToValueAtTime(.018, t + i * .11 + .01); g.gain.exponentialRampToValueAtTime(.0001, t + i * .11 + .08); o.connect(g).connect(out); o.start(t + i * .11); o.stop(t + i * .11 + .1); }
        else for (let i = 0; i < 4; i++) { const o = ctx.createOscillator(), g = ctx.createGain(); o.frequency.value = 4400 + Math.random() * 300; g.gain.setValueAtTime(.0001, t + i * .045); g.gain.exponentialRampToValueAtTime(.006, t + i * .045 + .004); g.gain.exponentialRampToValueAtTime(.0001, t + i * .045 + .02); o.connect(g).connect(out); o.start(t + i * .045); o.stop(t + i * .045 + .03); }
        timers.push(setTimeout(tick, (k === 'birds' ? 2200 + Math.random() * 4500 : 500 + Math.random() * 900))); }; tick(); }
  }
  return () => { timers.forEach(clearTimeout); for (const n of nodes) { try { n.stop(); } catch { } } };
}
function compose(T, seed, night) { // 4 chords × 2 bars, 8 eighths per bar → 64 slots: [slot, semitone, length]
  const R = rnd(seed), sc = SCALES[T.scale], notes = [], dens = (T.lead === 'chip' ? .7 : .42) * (night ? .6 : 1);
  const degree = d => { const o = Math.floor(d / sc.length); return sc[((d % sc.length) + sc.length) % sc.length] + o * 12; };
  const motif = []; let d = sc.length + (R() * 3 | 0);
  for (let s = 0; s < 32; s++) { if (R() < dens || s % 8 === 0) { d += [-2, -1, -1, 0, 1, 1, 2][R() * 7 | 0]; d = Math.max(sc.length - 2, Math.min(sc.length * 2 + 2, d)); const len = R() < .3 ? 2 : 1; motif.push([s, d, len]); s += len - 1; } }
  const vary = (m, k) => m.map(([s, d, l]) => [s, R() < k ? d + (R() < .5 ? 1 : -1) : d, l]);
  const B = vary(motif, .7).map(([s, d, l]) => [s, d + 2, l]);
  for (const [part, off] of [[motif, 0], [vary(motif, .25), 32]]) for (const [s, dd, l] of part) notes.push([s + off, degree(dd), l]);
  return { notes, B, degree };
}
music.world = function (id, night = false) {
  if (!id || !musicOn || !ac()) { if (wm) { const w = wm; wm = null; clearTimeout(w.timer); w.stopAmb?.(); w.gain.gain.cancelScheduledValues(ctx.currentTime); w.gain.gain.setValueAtTime(w.gain.gain.value, ctx.currentTime); w.gain.gain.exponentialRampToValueAtTime(.0001, ctx.currentTime + 1.5); setTimeout(() => w.gain.disconnect(), 1800); } return; }
  if (wm && wm.id === id && wm.night === night) return;
  music.world(null); if (musOn) music.stop(.8);
  const T = THEMES[id] || THEMES.harbor, gain = ctx.createGain(); gain.gain.value = .0001; gain.connect(master);
  gain.gain.exponentialRampToValueAtTime(id === 'battle' ? .32 : .22, ctx.currentTime + 2.5);
  const w = wm = { id, night, gain, seed: (Math.random() * 1e9) | 0, bar0: ctx.currentTime + .3 };
  w.stopAmb = ambience(night && id !== 'battle' ? [...new Set([...T.amb.filter(a => a !== 'birds'), 'crickets'])] : T.amb, gain);
  const root = NOTE(T.root), hz = st => root * Math.pow(2, st / 12);
  const loop = () => {
    if (wm !== w) return;
    const E = 60 / (T.bpm * (night && id !== 'battle' ? .85 : 1)) / 2, t0 = w.bar0, { notes } = compose(T, w.seed++, night);
    T.prog.forEach(([r, q], i) => { const t = t0 + i * 16 * E, tri = q === 'm' ? [0, 3, 7] : [0, 4, 7];
      for (const iv of tri) voice('pad', hz(r + iv), t, 16 * E, id === 'battle' ? .018 : .03, gain);
      for (let b = 0; b < (id === 'battle' ? 8 : 4); b++) voice('bass', hz(r - 12 + (b % 2 && id === 'battle' ? 7 : 0)), t + b * (id === 'battle' ? 2 : 4) * E, (id === 'battle' ? 1.8 : 3.6) * E, id === 'battle' ? .12 : .09, gain); });
    for (const [s, st, l] of notes) voice(T.lead, hz(st), t0 + s * E, l * E * 1.6, T.lead === 'flute' ? .07 : T.lead === 'bell' ? .06 : .08, gain);
    if (T.perc === 'shaker') for (let k = 0; k < 64; k++) if (k % 2 || Math.random() < .3) perc('shaker', t0 + k * E, k % 4 === 2 ? .02 : .01, gain);
    if (T.perc === 'drums') for (let k = 0; k < 64; k++) { if (k % 4 === 0) perc('kick', t0 + k * E, .3, gain); if (k % 8 === 4) perc('snare', t0 + k * E, .12, gain); perc('shaker', t0 + k * E, .012, gain); }
    w.bar0 += 64 * E; w.timer = setTimeout(loop, Math.max(200, (w.bar0 - ctx.currentTime - 2) * 1000));
  };
  loop();
};
