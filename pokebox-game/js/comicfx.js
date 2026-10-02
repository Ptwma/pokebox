// Pokebox — graphic-novel UI effects (DOM + CSS only, cheap on phones):
//   panelBreak()  world -> battle: the screen cracks into inked comic panels that fly apart, a VS splash, then the battle.
//   areaCard()    chapter title card when you arrive in an area.
//   onomato()     comic sound-effect words ("FWOOSH!") on hits, per type.
//   impactFrame() 2-frame black/white inverted impact flash for big hits.
//   speedLines()  radial speed lines while an ultimate charges.
export const TYPE_COL = { Fire: '#ff6a3d', Water: '#3fa7ff', Grass: '#5fcf5a', Lightning: '#ffd23f', Psychic: '#c46bff', Fighting: '#e0763a',
  Darkness: '#5a4a7a', Metal: '#9fb0c4', Dragon: '#e0b040', Colorless: '#e8e2d0', Fairy: '#ff8fd0' };
const WORDS = { Fire: ['FWOOSH!', 'KA-BOOM!'], Water: ['SPLASH!', 'SPLOOSH!'], Grass: ['THWIP!', 'SWISH!'], Lightning: ['ZZAP!', 'KRA-KOOM!'],
  Psychic: ['WHUMMM!', 'VWORP!'], Fighting: ['POW!', 'WHAM!'], Darkness: ['SLASH!', 'SHNK!'], Metal: ['KLANG!', 'CLANK!'], Dragon: ['ROAAAR!', 'KRAKA!'],
  Colorless: ['WHAM!', 'BAM!'], Fairy: ['TWINKLE!', 'SHIMMER!'] };
const reduced = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
const wait = ms => new Promise(r => setTimeout(r, ms));
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

/* ---------------------------------------------------------------- world -> battle panel break */
function shards(seed = Math.random()) {
  // fan of polygons around an off-centre crack point; slightly shrunk so black ink "gutters" show between them
  let s = Math.floor(seed * 1e6) || 7; const R = () => ((s = (s * 16807) % 2147483647) / 2147483647);
  const cx = 44 + R() * 12, cy = 42 + R() * 14, pts = [];
  const N = 9; for (let i = 0; i < N; i++) { const a = (i + R() * .6) / N * Math.PI * 2; const dx = Math.cos(a), dy = Math.sin(a);
    const t = Math.min(dx > 0 ? (100 - cx) / dx : dx < 0 ? -cx / dx : 1e9, dy > 0 ? (100 - cy) / dy : dy < 0 ? -cy / dy : 1e9); pts.push([cx + dx * t, cy + dy * t]); }
  const corners = [[100, 100], [0, 100], [0, 0], [100, 0]];
  const out = [];
  for (let i = 0; i < N; i++) {
    const a = pts[i], b = pts[(i + 1) % N], poly = [[cx, cy], a];
    // include any screen corners between a and b (walking the border)
    const ang = p => Math.atan2(p[1] - cy, p[0] - cx), a0 = ang(a); let a1 = ang(b); if (a1 < a0) a1 += Math.PI * 2;
    corners.map(c => [c, ang(c) < a0 ? ang(c) + Math.PI * 2 : ang(c)]).filter(([, t]) => t > a0 && t < a1).sort((x, y) => x[1] - y[1]).forEach(([c]) => poly.push(c));
    poly.push(b);
    const gx = poly.reduce((q, p) => q + p[0], 0) / poly.length, gy = poly.reduce((q, p) => q + p[1], 0) / poly.length;
    const k = .975; out.push({ poly: poly.map(([x, y]) => [gx + (x - gx) * k, gy + (y - gy) * k]), gx, gy });
  }
  return { cx, cy, out };
}
/** Plays the break. `onCovered` runs while the VS splash fully covers the screen (swap the view there). */
export async function panelBreak({ img, title = 'Battle!', sub = '', color = '#ff5a4e' } = {}, onCovered) {
  const o = document.createElement('div'); o.className = 'cx-break'; o.style.setProperty('--c', color);
  const { cx, cy, out } = shards();
  o.innerHTML = `<div class="cx-splash"><div class="cx-dots"></div><div class="cx-rays"></div><div class="cx-title"><b>${esc(title)}</b>${sub ? `<small>${esc(sub)}</small>` : ''}</div></div>`
    + out.map(s => `<i class="cx-shard" style="clip-path:polygon(${s.poly.map(([x, y]) => `${x.toFixed(2)}% ${y.toFixed(2)}%`).join(',')});${img ? `background-image:url(${img})` : ''}"></i>`).join('')
    + `<svg class="cx-crack" viewBox="0 0 100 100" preserveAspectRatio="none"><path d="${out.map(s => `M${cx} ${cy} L${s.poly[1][0]} ${s.poly[1][1]}`).join(' ')}"/></svg>`;
  document.body.append(o);
  const sh = [...o.querySelectorAll('.cx-shard')];
  if (reduced()) { onCovered?.(); await wait(500); o.remove(); return; }
  // 1) freeze + crack
  await wait(30); o.classList.add('crack'); await wait(260);
  // 2) panels fly apart revealing the VS splash
  o.classList.add('fly');
  const anims = sh.map((el, i) => { const s = out[i], dx = s.gx - cx, dy = s.gy - cy, l = Math.hypot(dx, dy) || 1;
    return el.animate([{ transform: 'none', opacity: 1 }, { transform: `translate(${dx / l * 70}vw,${dy / l * 70}vh) rotate(${(i % 2 ? 1 : -1) * (18 + i * 5)}deg) scale(.8)`, opacity: .9 }],
      { duration: 620, delay: i * 18, easing: 'cubic-bezier(.55,0,.9,.45)', fill: 'forwards' }).finished.catch(() => {}); });
  await Promise.all(anims);
  // 3) splash holds, swap the view underneath, then wipe away
  try { onCovered?.(); } catch (e) { console.warn(e); }
  await wait(650);
  await o.animate([{ clipPath: 'circle(150% at 50% 50%)' }, { clipPath: 'circle(0% at 50% 50%)' }], { duration: 420, easing: 'cubic-bezier(.7,0,.3,1)', fill: 'forwards' }).finished.catch(() => {});
  o.remove();
}

/* ---------------------------------------------------------------- chapter card on area arrival */
export function areaCard({ kicker = '', name = '', sub = '', color = '#ffd257' } = {}) {
  document.querySelector('.cx-area')?.remove();
  const d = document.createElement('div'); d.className = 'cx-area'; d.style.setProperty('--c', color);
  d.innerHTML = `<div class="cx-panel"><span class="cx-kick">${esc(kicker)}</span><b>${esc(name)}</b><small>${esc(sub)}</small></div>`;
  document.body.append(d);
  setTimeout(() => d.classList.add('out'), 2800); setTimeout(() => d.remove(), 3500);
}

/* ---------------------------------------------------------------- battle helpers */
export function onomato(layer, x, y, type = 'Colorless', { big = false, crit = false } = {}) {
  if (!layer) return;
  const list = crit ? ['KRAKK!', 'CRUNCH!'] : WORDS[type] || WORDS.Colorless, word = list[Math.floor(Math.random() * list.length)];
  const d = document.createElement('div'); d.className = 'cx-sfx' + (big ? ' big' : '');
  d.style.cssText = `left:${x}px;top:${y}px;--c:${TYPE_COL[type] || '#ffd257'};--r:${(Math.random() - .5) * 24}deg`;
  d.innerHTML = `<svg viewBox="0 0 200 120"><polygon points="${burstPts()}"/></svg><b>${word}</b>`;
  layer.append(d);
  d.animate([{ transform: 'translate(-50%,-50%) rotate(var(--r)) scale(.2)', opacity: 0 }, { transform: 'translate(-50%,-50%) rotate(var(--r)) scale(1.15)', opacity: 1, offset: .18 },
    { transform: 'translate(-50%,-50%) rotate(var(--r)) scale(1)', opacity: 1, offset: .7 }, { transform: 'translate(-50%,-60%) rotate(var(--r)) scale(1.05)', opacity: 0 }],
    { duration: big ? 1200 : 900, easing: 'cubic-bezier(.2,.9,.3,1.2)' }).finished.then(() => d.remove(), () => d.remove());
}
function burstPts() { const p = []; const n = 14; for (let i = 0; i < n * 2; i++) { const a = i / (n * 2) * Math.PI * 2, r = i % 2 ? 42 + Math.random() * 6 : 58 + Math.random() * 10;
  p.push(`${(100 + Math.cos(a) * r * 1.6).toFixed(1)},${(60 + Math.sin(a) * r).toFixed(1)}`); } return p.join(' '); }
export function impactFrame(field) {
  if (!field || reduced()) return;
  const d = document.createElement('div'); d.className = 'cx-impact'; field.append(d);
  setTimeout(() => d.classList.add('b'), 55); setTimeout(() => d.remove(), 120);
}
export function speedLines(field, color = '#000', ms = 900) {
  if (!field) return () => {};
  const d = document.createElement('div'); d.className = 'cx-speed'; d.style.setProperty('--c', color); field.append(d);
  const t = setTimeout(() => d.remove(), ms + 400); return () => { clearTimeout(t); d.remove(); };
}
