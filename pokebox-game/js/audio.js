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
