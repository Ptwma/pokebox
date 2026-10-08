// Pokebox — first-run prologue + guided first steps.
// 1) a narrated opening: the map of Veyra, then camera flyovers over the real 3D world (world.prologue) explaining what the
//    game is — the relay, Echoes, Lattice cards, Pokébox Labs, Rangers & Wardens — and a tease of what lies under Node 7.
// 2) a short coach that teaches moving, the camera, the objective beacon/map and interacting, step by step, then gets out
//    of the way. Both are skippable and run once (s.story.seen.prologue / .coach); Settings can replay the prologue.
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const wait = ms => new Promise(r => setTimeout(r, ms));

export const PROLOGUE = [
  { k: 'Veyra', h: 'A ring of islands', t: 'Around a flooded caldera lies Veyra — six towns, one ring of sea roads, and at its heart Relay Node 7, the oldest Pokémon storage relay in the world.' },
  { k: 'Thirty years ago', h: 'The night the PCs went dark', t: 'Thirty years ago a storm struck Node 7. For one night every PC in Veyra went silent. When the lights came back on, everyone was relieved — and nobody asked what the relay had kept.' },
  { k: 'Mistvale', h: 'Echoes', t: 'It kept everything. Every Pokémon ever sent through a PC left a faint trace behind. Now those traces are waking up in the fog and the tall grass. We call them Echoes.' },
  { k: 'Pokébox Labs', h: 'Lattice cards', t: 'Dr. Ione Vale learned to bind an Echo to crystal card stock: the Lattice card. A bound Echo can battle as a projection — and no real Pokémon is ever hurt. Or so the Lab says.' },
  { k: 'Starfall', h: 'Rangers, Wardens, Archivists', t: 'Lattice Rangers explore the islands and collect the Echoes. Circuit Wardens guard the towns and test the Rangers. And on Starfall hill, the Archivists listen to the relay as if it were speaking.' },
  { k: 'Frostline', h: 'Two memories, one shape', t: 'Under the ice of Frostline, two Echoes drifted into each other. What came out has no name in any Pokédex.' },
  { k: 'Voltspire', h: 'The Static Syndicate', t: 'In the storm towers, men in black coats found out that a frightened Echo prints a rare card. Fear sells. They call themselves the Static Syndicate.' },
  { k: 'Sandreach', h: 'Glass that remembers', t: 'In the south, the dunes have begun to melt into glass — in the exact shapes of Pokémon that passed through Node 7, three decades ago.' },
  { k: 'Under Node 7', h: 'Something is listening', t: 'The Echoes are multiplying. The relay hums in patterns no one can read… and something deep beneath it has started to answer.', glitch: true },
  { k: 'Lumen Harbor', h: 'Your story starts now', t: 'You are Veyra’s newest Lattice Ranger. Your ferry just docked in Lumen Harbor — and a courier with goggles and too much energy is already waving at you.' },
];

/** plays the prologue. ctx: { W, sfx, music, onDone } — resolves when finished or skipped */
export async function runPrologue(ctx) {
  const { W, sfx, music } = ctx;
  const el = document.createElement('div'); el.className = 'prolog'; document.body.append(el);
  el.innerHTML = `<canvas class="pl-map"></canvas><div class="pl-lb t"></div><div class="pl-lb b"></div>
    <button class="pl-skip" type="button">Skip intro ▸▸</button>
    <div class="pl-cap"><div class="pl-k"></div><h2 class="pl-h display"></h2><p class="pl-t"></p><div class="pl-dots">${PROLOGUE.map(() => '<i></i>').join('')}</div></div>`;
  let skipped = false, typing = 0; const cap = el.querySelector('.pl-cap');
  el.querySelector('.pl-skip').onclick = () => { skipped = true; W.stopCinematic?.(); };
  const onKey = e => { if (e.code === 'Escape') { e.preventDefault(); e.stopImmediatePropagation(); skipped = true; W.stopCinematic?.(); } };
  addEventListener('keydown', onKey, true);
  const say = i => { const P = PROLOGUE[i]; if (!P) return; clearInterval(typing);
    cap.classList.remove('in'); void cap.offsetWidth; cap.classList.add('in'); el.classList.toggle('glitch', !!P.glitch);
    el.querySelector('.pl-k').textContent = P.k; el.querySelector('.pl-h').textContent = P.h; const tp = el.querySelector('.pl-t'); let n = 0;
    typing = setInterval(() => { n += 2; tp.textContent = P.t.slice(0, n); if (n >= P.t.length) clearInterval(typing); }, 22);
    el.querySelectorAll('.pl-dots i').forEach((d, k) => d.classList.toggle('on', k <= i)); sfx?.tick?.();
    if (P.glitch) { sfx?.zap?.(); music?.world?.('rift', true); } else if (i === PROLOGUE.length - 1) music?.world?.('harbor', false); };
  try {
    // ---- panel 0: the map of Veyra (2D), slow push-in toward Node 7 with the towns appearing
    await mapPanel(el, W, () => skipped, () => say(0));
    if (!skipped) { el.classList.add('live'); await W.prologue({ onShot: i => say(i + 1) }); }
    if (!skipped) await wait(1600);
  } catch (e) { console.warn('[prologue]', e); }
  finally {
    clearInterval(typing); removeEventListener('keydown', onKey, true);
    el.classList.add('out'); await wait(450); el.remove(); music?.world?.('harbor', false); ctx.onDone?.();
  }
}

function mapPanel(el, W, isSkipped, start) {
  return new Promise(res => {
    const cv = el.querySelector('.pl-map'), g = cv.getContext('2d'), map = W.mapCanvas, size = W.size || 1150, ids = Object.keys(W.regions);
    const dpr = Math.min(devicePixelRatio || 1, 2); let t0 = 0, raf = 0; const DUR = 9500;
    const fit = () => { cv.width = innerWidth * dpr; cv.height = innerHeight * dpr; }; fit();
    const frame = now => { if (!t0) { t0 = now; start(); } const t = now - t0, k = Math.min(1, t / DUR), cw = cv.width, ch = cv.height;
      const s = Math.min(cw, ch) / size * (.82 + k * .5), cx = cw / 2, cy = ch / 2;
      g.fillStyle = '#081426'; g.fillRect(0, 0, cw, ch);
      if (map) { g.globalAlpha = Math.min(1, t / 900); g.drawImage(map, cx - size / 2 * s, cy - size / 2 * s, size * s, size * s); g.globalAlpha = 1; }
      const vg = g.createRadialGradient(cx, cy, Math.min(cw, ch) * .2, cx, cy, Math.max(cw, ch) * .7); vg.addColorStop(0, 'rgba(8,20,38,0)'); vg.addColorStop(1, 'rgba(8,20,38,.85)'); g.fillStyle = vg; g.fillRect(0, 0, cw, ch);
      // Node 7: pulsing rings at the centre
      const R = W.regions.rift || { x: 0, z: 0 }, nx = cx + R.x * s, ny = cy + R.z * s;
      for (let i = 0; i < 3; i++) { const p = ((t / 1600) + i / 3) % 1; g.beginPath(); g.arc(nx, ny, (8 + p * 70) * dpr, 0, 7); g.strokeStyle = `rgba(92,242,214,${(1 - p) * .7})`; g.lineWidth = 2.5 * dpr; g.stroke(); }
      g.beginPath(); g.arc(nx, ny, 6 * dpr, 0, 7); g.fillStyle = '#5cf2d6'; g.fill();
      // towns fade in one after another
      g.textAlign = 'center'; g.font = `800 ${15 * dpr}px "Barlow Condensed", system-ui, sans-serif`;
      ids.filter(id => id !== 'rift').forEach((id, i) => { const a = Math.max(0, Math.min(1, (t - 1400 - i * 650) / 500)); if (!a) return; const Rg = W.regions[id], x = cx + Rg.x * s, y = cy + Rg.z * s;
        g.globalAlpha = a; g.beginPath(); g.arc(x, y, 6 * dpr, 0, 7); g.fillStyle = '#ffd257'; g.fill(); g.lineWidth = 2 * dpr; g.strokeStyle = '#1b1530'; g.stroke();
        const name = W.areas[id].name, w = g.measureText(name).width + 14 * dpr; g.fillStyle = 'rgba(14,12,30,.82)'; g.fillRect(x - w / 2, y - 32 * dpr, w, 21 * dpr); g.fillStyle = '#fff'; g.fillText(name, x, y - 16 * dpr); g.globalAlpha = 1; });
      if (isSkipped() || k >= 1) { cancelAnimationFrame(raf); removeEventListener('resize', fit); cv.classList.add('gone'); setTimeout(() => cv.remove(), 600); res(); return; }
      raf = requestAnimationFrame(frame); };
    addEventListener('resize', fit); raf = requestAnimationFrame(frame);
  });
}

/* ---------------------------------------------------------------- the coach: first steps, one at a time */
export function startCoach({ W, touch, isBusy, onDone }) {
  const el = document.createElement('div'); el.className = 'coach'; el.hidden = true; document.body.append(el);
  const pos0 = () => { const p = W.player?.group.position; return p ? { x: p.x, z: p.z } : null; };
  const sp = () => { const v = W.player?.vel; return v ? Math.hypot(v.x, v.z) : 0; };
  const steps = [
    { h: 'Move', t: touch ? 'Drag the <b>left stick</b> to walk.' : '<b>W A S D</b> (or the arrow keys) to walk.', done: s => { const p = W.player?.group.position; return p && s.p && Math.hypot(p.x - s.p.x, p.z - s.p.z) > 6; }, max: 40 },
    { h: 'Run', t: touch ? 'Push the stick <b>all the way</b> to run.' : 'Hold <b>Shift</b> while walking to run.', done: () => sp() > 7, max: 20 },
    { h: 'Jump & glide', t: touch ? 'Tap <b>⤒</b> to jump. Tap it again in the air to open the glider.' : '<b>Space</b> to jump. Press it again in the air to glide.', done: () => (W.player?.group.position.y ?? 0) - (W.groundAt?.() ?? -99) > .6, max: 18 },
    { h: 'Look around', t: touch ? 'Drag on the <b>right side</b> of the screen to turn the camera. <b>Pinch</b> to zoom.' : 'Drag with the <b>mouse</b> to turn the camera. The <b>mouse wheel</b> zooms.', done: s => Math.abs((W.camYaw ?? 0) - s.yaw) > .9, max: 16 },
    { h: 'Your objective', t: 'The gold <b>◆ beacon</b> and the star on the minimap show where to go. ' + (touch ? '<b>Tap the minimap</b>' : 'Press <b>M</b>') + ' for the map of Veyra.', done: () => false, max: 10 },
    { h: 'Talk & interact', t: 'Walk up to people, chests, doors and signs, then press ' + (touch ? '<b>✋</b>' : '<b>E</b>') + '.', done: () => false, max: 9 },
    { h: 'Your Lattice', t: (touch ? 'The <b>☰</b> button' : '<b>Esc</b>') + ' opens your Lattice: cards, packs, your partner, the journey and the settings.', done: () => false, max: 9 },
    { h: 'Wild Echoes', t: 'Echoes live in the tall grass. Get close and they challenge you — weaken one in battle, then throw a <b>Poké Ball</b> to catch it.', done: () => false, max: 10 },
  ];
  let i = -1, st = null, timer = 0, gone = false;
  const show = () => { const S = steps[i]; el.innerHTML = `<div class="co-n">${i + 1}/${steps.length}</div><div class="co-b"><b>${esc(S.h)}</b><p>${S.t}</p></div><div class="co-a"><button class="btn gold sm" type="button" data-ok>Got it</button><button class="co-skip" type="button" data-skip>Skip tutorial</button></div>`;
    el.hidden = false; el.classList.remove('in'); void el.offsetWidth; el.classList.add('in');
    el.querySelector('[data-ok]').onclick = next; el.querySelector('[data-skip]').onclick = finish; };
  function next() { if (gone) return; i++; if (i >= steps.length) return finish(); st = { p: pos0(), yaw: W.camYaw ?? 0, t: 0 }; show(); }
  function finish() { if (gone) return; gone = true; clearInterval(timer); el.classList.add('out'); setTimeout(() => el.remove(), 350); onDone?.(); }
  timer = setInterval(() => { if (gone) return; const busy = isBusy(); el.hidden = busy || i < 0; if (busy) return; if (i < 0) return next();
    if (st.lock) return; st.t += .25; const S = steps[i]; if (S.done(st)) { st.lock = true; el.classList.add('ok'); setTimeout(() => { el.classList.remove('ok'); next(); }, 650); } else if (st.t > S.max) next(); }, 250);
  return { stop: finish };
}
