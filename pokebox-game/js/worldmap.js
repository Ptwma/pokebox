// Pokebox — the full-screen map of Veyra (phone first).
// One canvas, drawn crisply at the device pixel ratio: drag to pan, pinch / wheel / buttons to zoom, tap a town for its card
// (fast travel when its Relay Ferry stop is open). Shows where you are and which way you face, the current objective with a
// dashed guide line, every route with its name, and which areas are ahead of your story (dangerous Echoes).
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const TYPEC = { Grass: '#5fae4f', Fire: '#ff6a3c', Water: '#3d9fff', Lightning: '#ffd23c', Psychic: '#d86bff', Fighting: '#d8844a', Darkness: '#8a6ae8', Metal: '#b8c6d4', Dragon: '#e0b040', Colorless: '#f0ece0' };

/**
 * opts: { W (world api), q (quest state), req (area → chapter needed), target (QS.target()), onTravel(id), onClose() }
 * returns { close }
 */
export function openWorldMap(host, opts) {
  const { W, q, req = {}, target, onTravel, onClose } = opts;
  const size = W.size || 1150, ids = Object.keys(W.regions), here = W.area;
  // the terrain map, colour-graded once (a canvas filter every frame is slow on phones and glitches on some GPUs)
  const map = (() => { const src = W.mapCanvas; if (!src) return null; const c = document.createElement('canvas'); c.width = src.width; c.height = src.height; const x = c.getContext('2d');
    try { x.filter = 'saturate(1.15) contrast(1.08)'; } catch {} x.drawImage(src, 0, 0); return c; })();
  host.hidden = false; host.classList.add('fs');
  host.innerHTML = `<div class="wmapfs">
    <canvas class="wm-cv" aria-label="Map of Veyra"></canvas>
    <header class="wm-top"><div><div class="eyebrow">Map of Veyra</div><h3 class="display">${esc(W.areas[here]?.name || 'Veyra')}</h3></div>
      <button class="wm-x" type="button" aria-label="Close map">✕</button></header>
    ${target?.label ? `<button class="wm-goal" type="button"><i>◆</i><span><small>Objective</small>${esc(target.label)}</span></button>` : ''}
    <div class="wm-legend"><span><i class="me"></i>You</span><span><i class="goal"></i>Objective</span><span><i class="ferry"></i>Ferry stop</span><span><i class="lock"></i>Not visited</span></div>
    <div class="wm-zoom"><button type="button" data-z="in" aria-label="Zoom in">+</button><button type="button" data-z="out" aria-label="Zoom out">−</button><button type="button" data-z="me" aria-label="Center on me">◎</button><button type="button" data-z="all" aria-label="Whole map">⤢</button></div>
    <div class="wm-sheet" hidden></div></div>`;
  const root = host.querySelector('.wmapfs'), cv = root.querySelector('.wm-cv'), g = cv.getContext('2d'), sheet = root.querySelector('.wm-sheet');
  let dpr = 1, cw = 0, ch = 0, alive = true, raf = 0, sel = null;
  const view = { x: 0, z: 0, s: 1 }; // centre (world m) and scale (css px per metre)
  const fitAll = () => Math.min(cw, ch) / (size * .92);
  function resize() { dpr = Math.min(devicePixelRatio || 1, 2.5); cw = root.clientWidth; ch = root.clientHeight; cv.width = Math.round(cw * dpr); cv.height = Math.round(ch * dpr); cv.style.width = cw + 'px'; cv.style.height = ch + 'px'; }
  resize();
  const pp = W.player?.group.position, me = pp ? { x: pp.x, z: pp.z, r: W.player.group.rotation.y } : null;
  view.s = fitAll(); if (me) { view.s = Math.max(view.s, Math.min(cw, ch) / 520); view.x = me.x * .6; view.z = me.z * .6; }
  const clampView = () => { const lo = fitAll() * .8, hi = Math.min(cw, ch) / 70; view.s = Math.max(lo, Math.min(hi, view.s)); const lim = size * .55; view.x = Math.max(-lim, Math.min(lim, view.x)); view.z = Math.max(-lim, Math.min(lim, view.z)); };
  clampView();
  const toS = (x, z) => [(x - view.x) * view.s + cw / 2, (z - view.z) * view.s + ch / 2];
  const toW = (sx, sy) => [(sx - cw / 2) / view.s + view.x, (sy - ch / 2) / view.s + view.z];

  // what each town looks like on the map
  const towns = ids.map(id => { const R = W.regions[id], A = W.areas[id], visited = !!q.visited?.[id], ahead = (req[id] ?? 0) > (q.ch ?? 0);
    return { id, x: R.x, z: R.z, name: A.name, sub: A.sub, echo: A.echo || [], visited, ahead, col: TYPEC[(A.echo || [])[0]] || '#ffd257' }; });
  const goals = (() => { if (!target) return []; if (target.x != null) return [{ x: target.x, z: target.z }]; if (target.findIds && W.findPos) return W.findPos(target.findIds); return []; })();

  function pill(x, y, text, sub, { bg = 'rgba(18,16,40,.82)', fg = '#fff', border = null, fs = 14 } = {}) {
    g.font = `800 ${fs}px "Barlow Condensed", system-ui, sans-serif`; const w1 = g.measureText(text).width;
    let w2 = 0; if (sub) { g.font = `600 ${fs * .72}px system-ui, sans-serif`; w2 = g.measureText(sub).width; }
    const w = Math.max(w1, w2) + 16, hh = sub ? fs * 2.05 : fs * 1.45, rx = x - w / 2, ry = y - hh;
    g.fillStyle = bg; g.beginPath(); g.roundRect(rx, ry, w, hh, 8); g.fill(); if (border) { g.strokeStyle = border; g.lineWidth = 2; g.stroke(); }
    g.fillStyle = fg; g.textAlign = 'center'; g.textBaseline = 'alphabetic'; g.font = `800 ${fs}px "Barlow Condensed", system-ui, sans-serif`; g.fillText(text, x, ry + fs * 1.08);
    if (sub) { g.font = `600 ${fs * .72}px system-ui, sans-serif`; g.fillStyle = 'rgba(255,255,255,.72)'; g.fillText(sub, x, ry + fs * 1.85); }
    return { x: rx, y: ry, w, h: hh };
  }
  function draw(t) {
    g.setTransform(dpr, 0, 0, dpr, 0, 0); g.clearRect(0, 0, cw, ch);
    g.fillStyle = '#1d4c80'; g.fillRect(0, 0, cw, ch);
    if (map) { const [x0, y0] = toS(-size / 2, -size / 2); g.imageSmoothingEnabled = true; g.drawImage(map, x0, y0, size * view.s, size * view.s); }
    // routes: dark casing + light core, names along the way when zoomed in
    for (const r of W.routes || []) { g.lineJoin = g.lineCap = 'round';
      for (const [wd, c] of [[7, 'rgba(30,22,10,.55)'], [3.5, '#f3e2b8']]) { g.lineWidth = wd; g.strokeStyle = c; g.beginPath(); r.pts.forEach(([x, z], i) => { const [sx, sy] = toS(x, z); i ? g.lineTo(sx, sy) : g.moveTo(sx, sy); }); g.stroke(); }
      if (view.s > fitAll() * 1.25) { const m = r.pts[(r.pts.length / 2) | 0], [sx, sy] = toS(m[0], m[1]); pill(sx, sy - 6, r.name, r.sub, { bg: 'rgba(255,248,230,.9)', fg: '#3a2a12', fs: 11 }); } }
    // areas ahead of the story: a red haze (wild Echoes outclass your team there)
    for (const T of towns) if (T.ahead) { const [sx, sy] = toS(T.x, T.z), rr = 90 * view.s; const gr = g.createRadialGradient(sx, sy, 0, sx, sy, rr); gr.addColorStop(0, 'rgba(255,70,50,.28)'); gr.addColorStop(1, 'rgba(255,70,50,0)'); g.fillStyle = gr; g.beginPath(); g.arc(sx, sy, rr, 0, 7); g.fill(); }
    // objective guide line + markers
    if (me && goals[0]) { const [ax, ay] = toS(me.x, me.z), [bx, by] = toS(goals[0].x, goals[0].z); g.setLineDash([8, 7]); g.lineDashOffset = -t * .03; g.lineWidth = 3; g.strokeStyle = 'rgba(255,210,87,.9)'; g.beginPath(); g.moveTo(ax, ay); g.lineTo(bx, by); g.stroke(); g.setLineDash([]); }
    // towns
    for (const T of towns) { const [sx, sy] = toS(T.x, T.z), isHere = T.id === here, r = 11;
      g.beginPath(); g.arc(sx, sy, r + 5, 0, 7); g.fillStyle = 'rgba(0,0,0,.45)'; g.fill();
      g.beginPath(); g.arc(sx, sy, r, 0, 7); g.fillStyle = T.visited ? T.col : '#6b6f7c'; g.fill(); g.lineWidth = 3; g.strokeStyle = T.visited ? '#ffd257' : '#2a2c36'; g.stroke();
      g.fillStyle = '#1b1530'; g.font = '900 12px system-ui'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(T.visited ? '⛴' : '?', sx, sy + 1);
      if (isHere) { g.beginPath(); g.arc(sx, sy, r + 9 + Math.sin(t * .004) * 2, 0, 7); g.strokeStyle = 'rgba(255,255,255,.8)'; g.lineWidth = 2; g.stroke(); }
      T.box = pill(sx, sy - r - 8, T.name, T.ahead ? '⚠ ahead of your story' : T.visited ? 'Ferry stop' : 'Not visited yet', { border: sel === T.id ? '#ffd257' : T.ahead ? 'rgba(255,110,90,.8)' : null, fs: 15 }); }
    for (const p of goals) { const [sx, sy] = toS(p.x, p.z), k = 1 + Math.sin(t * .006) * .15; g.save(); g.translate(sx, sy); g.scale(k, k); g.rotate(Math.PI / 4);
      g.fillStyle = '#ffd257'; g.strokeStyle = '#1b1530'; g.lineWidth = 3; g.beginPath(); g.rect(-8, -8, 16, 16); g.fill(); g.stroke(); g.restore(); }
    // you: an arrow pointing where you face
    if (me) { const [sx, sy] = toS(me.x, me.z), a = Math.atan2(Math.cos(me.r), Math.sin(me.r)); g.save(); g.translate(sx, sy);
      g.beginPath(); g.arc(0, 0, 18 + Math.sin(t * .005) * 3, 0, 7); g.fillStyle = 'rgba(92,242,214,.22)'; g.fill(); g.rotate(a + Math.PI / 2);
      g.fillStyle = '#ffffff'; g.strokeStyle = '#ff4e6a'; g.lineWidth = 3; g.beginPath(); g.moveTo(0, -13); g.lineTo(10, 10); g.lineTo(0, 5); g.lineTo(-10, 10); g.closePath(); g.fill(); g.stroke(); g.restore(); }
    // compass + scale bar
    g.save(); g.translate(cw - 34, ch - 92); g.fillStyle = 'rgba(18,16,40,.8)'; g.beginPath(); g.arc(0, 0, 18, 0, 7); g.fill(); g.fillStyle = '#ff6a5a'; g.beginPath(); g.moveTo(0, -13); g.lineTo(5, 0); g.lineTo(-5, 0); g.fill(); g.fillStyle = '#fff'; g.font = '800 10px system-ui'; g.textAlign = 'center'; g.fillText('N', 0, 11); g.restore();
    const m100 = 100 * view.s; g.fillStyle = 'rgba(18,16,40,.8)'; g.fillRect(12, ch - 30, m100 + 16, 20); g.fillStyle = '#fff'; g.fillRect(20, ch - 18, m100, 3); g.font = '700 10px system-ui'; g.textAlign = 'left'; g.fillText('100 m', 22, ch - 21);
  }
  const loop = t => { if (!alive) return; draw(t); raf = requestAnimationFrame(loop); }; raf = requestAnimationFrame(loop);

  // ---- town card (bottom sheet)
  function showSheet(T) {
    sel = T ? T.id : null; if (!T) { sheet.hidden = true; return; }
    const can = T.visited && T.id !== here;
    sheet.innerHTML = `<div class="wm-sh"><div><div class="eyebrow" style="color:${T.col}">${esc(T.sub)}</div><h4 class="display">${esc(T.name)}</h4>
      <div class="wm-chips">${T.echo.map(e => `<span style="--c:${TYPEC[e] || '#fff'}">${esc(e)}</span>`).join('')}</div>
      <p class="small">${T.id === here ? 'You are here.' : T.visited ? 'Relay Ferry stop — travel there instantly.' : 'Not visited yet: walk there along the routes to open its ferry stop.'}${T.ahead ? ' <b class="warn">Wild Echoes here are ahead of your story.</b>' : ''}</p></div>
      <div class="wm-act">${can ? `<button class="btn gold" type="button" data-travel="${T.id}">Travel ⛴</button>` : ''}<button class="btn ghost sm" type="button" data-fly="${T.id}">Show</button></div></div>`;
    sheet.hidden = false;
    sheet.querySelector('[data-travel]')?.addEventListener('click', e => { e.stopPropagation(); close(); onTravel?.(T.id); }); // (not data-go: the app's global click handler treats data-go as a page link)
    sheet.querySelector('[data-fly]').addEventListener('click', () => flyTo(T.x, T.z, Math.max(view.s, Math.min(cw, ch) / 260)));
  }
  function flyTo(x, z, s = view.s) { const a = { ...view }, t0 = performance.now(); const step = now => { const k = Math.min(1, (now - t0) / 380), e = 1 - (1 - k) ** 3; view.x = a.x + (x - a.x) * e; view.z = a.z + (z - a.z) * e; view.s = a.s + (s - a.s) * e; clampView(); if (k < 1 && alive) requestAnimationFrame(step); }; requestAnimationFrame(step); }
  function zoomAt(sx, sy, k) { const [wx, wz] = toW(sx, sy); view.s *= k; clampView(); const [nx, nz] = toW(sx, sy); view.x += wx - nx; view.z += wz - nz; clampView(); }
  function hit(sx, sy) { let best = null, bd = 1e9; for (const T of towns) { const [x, y] = toS(T.x, T.z), b = T.box; const inBox = b && sx >= b.x && sx <= b.x + b.w && sy >= b.y && sy <= b.y + b.h, d = Math.hypot(sx - x, sy - y); if ((inBox || d < 30) && d < bd) { best = T; bd = inBox ? 0 : d; } } return best; }

  // ---- gestures: drag, pinch, wheel, double tap
  const pts = new Map(); let downAt = null, pinch = null, lastTap = 0, moved = 0;
  cv.addEventListener('pointerdown', e => { cv.setPointerCapture(e.pointerId); pts.set(e.pointerId, [e.offsetX, e.offsetY]); moved = 0; if (pts.size === 1) downAt = [e.offsetX, e.offsetY]; if (pts.size === 2) { const [a, b] = [...pts.values()]; pinch = { d: Math.hypot(a[0] - b[0], a[1] - b[1]), s: view.s }; } });
  cv.addEventListener('pointermove', e => { if (!pts.has(e.pointerId)) return; const p = pts.get(e.pointerId), dx = e.offsetX - p[0], dy = e.offsetY - p[1]; pts.set(e.pointerId, [e.offsetX, e.offsetY]); moved += Math.abs(dx) + Math.abs(dy);
    if (pts.size === 1) { view.x -= dx / view.s; view.z -= dy / view.s; clampView(); }
    else if (pts.size === 2 && pinch) { const [a, b] = [...pts.values()], d = Math.hypot(a[0] - b[0], a[1] - b[1]); zoomAt((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (pinch.s * d / pinch.d) / view.s); } });
  const up = e => { pts.delete(e.pointerId); if (pts.size < 2) pinch = null;
    if (!pts.size && downAt && moved < 8) { const now = performance.now(), T = hit(e.offsetX, e.offsetY);
      if (T) showSheet(T); else if (now - lastTap < 320) zoomAt(e.offsetX, e.offsetY, 1.8); else showSheet(null); lastTap = now; }
    if (!pts.size) downAt = null; };
  cv.addEventListener('pointerup', up); cv.addEventListener('pointercancel', up);
  cv.addEventListener('wheel', e => { e.preventDefault(); zoomAt(e.offsetX, e.offsetY, Math.exp(-e.deltaY * .0015)); }, { passive: false });
  root.querySelector('.wm-zoom').addEventListener('click', e => { const z = e.target.closest('[data-z]')?.dataset.z; if (!z) return;
    if (z === 'in') zoomAt(cw / 2, ch / 2, 1.5); else if (z === 'out') zoomAt(cw / 2, ch / 2, 1 / 1.5); else if (z === 'me' && me) flyTo(me.x, me.z, Math.max(view.s, Math.min(cw, ch) / 300)); else if (z === 'all') flyTo(0, 0, fitAll()); });
  root.querySelector('.wm-goal')?.addEventListener('click', () => { if (goals[0]) flyTo(goals[0].x, goals[0].z, Math.max(view.s, Math.min(cw, ch) / 300)); });
  const onKey = e => { if (e.code === 'Escape' || e.code === 'KeyM') { e.preventDefault(); e.stopPropagation(); close(); } };
  addEventListener('keydown', onKey, true); addEventListener('resize', resize);
  root.querySelector('.wm-x').onclick = () => close();
  function close() { if (!alive) return; alive = false; cancelAnimationFrame(raf); removeEventListener('keydown', onKey, true); removeEventListener('resize', resize); host.hidden = true; host.classList.remove('fs'); host.innerHTML = ''; onClose?.(); }
  return { close };
}
