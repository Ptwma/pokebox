// Pokebox — bottom-screen companion (bottom.html). Shows what you look at between actions — map, objective, team,
// battle commands, dialogue history, quick menu — and sends taps back to the game. No three.js here: plain DOM and one
// 2D canvas, redrawn only when the game sends a new snapshot (4 per second), so it never steals frames from the game.
const TYPEC = { Grass: '#5fae4f', Fire: '#ff6a3c', Water: '#3d9fff', Lightning: '#e8c22c', Psychic: '#c45bf0', Fighting: '#d8844a', Darkness: '#6a5ad8', Metal: '#8fa1b3', Dragon: '#d0a030', Colorless: '#9a958a' };
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const $ = s => document.querySelector(s);
const N = () => window.PokeboxDual;
let bc = null; try { bc = new BroadcastChannel('pokebox-dual'); } catch {}
const send = o => { const j = JSON.stringify(o); if (N()?.toGame) N().toGame(j); else bc?.postMessage(j); };
const vibrate = () => { try { navigator.vibrate?.(12); } catch {} };

let S = null, M = null, mapImg = null, shown = '', zoom = 1, sel = null;
window.__fromGame = j => { let m; try { m = JSON.parse(j); } catch { return; } recv(m); };
if (bc) bc.onmessage = e => { let m; try { m = JSON.parse(e.data); } catch { return; } if (m.t === 'ping') send({ c: 'hello' }); else if (m.t) recv(m); };
function recv(m) {
  if (m.t === 'map') { M = m; mapImg = new Image(); mapImg.onload = drawMap; mapImg.src = m.img; return; }
  if (m.t === 'state') { S = m; render(); }
}
send({ c: 'hello' }); setTimeout(() => { if (!S) send({ c: 'hello' }); }, 1500);

/* ---------- header (always) */
function header() {
  $('#hd').innerHTML = `<span class="lv">${S.lv}</span><div class="who"><b>${esc(S.name)}</b><small>${esc(S.area || 'Veyra')}</small></div><span class="sp"></span>
    ${S.clock ? `<span class="pill">${esc(S.clock)}</span>` : ''}<span class="pill gold">◉ ${Number(S.coins).toLocaleString()}</span>`;
}

/* ---------- views */
function render() {
  header();
  const m = S.mode === 'explore' || S.mode === 'app' && !S.me ? S.mode : S.mode;
  if (m !== shown) { shown = m; build(m); }
  update(m);
}
const mn = () => $('#mn');
function build(m) {
  const el = mn(); el.className = '';
  if (m === 'explore') {
    el.className = 'ex';
    el.innerHTML = `<div class="card mapw"><canvas id="map"></canvas><div class="mapz"><button data-z="1.4">+</button><button data-z=".7">−</button></div><div class="sheet" id="sheet" hidden></div></div>
      <div class="side"><div class="card obj"><div class="eyebrow" id="chap">Objective</div><p id="goal"></p><span class="dist" id="dist"></span></div>
        <div class="team" id="team"></div>
        <div class="quick"><button class="big" data-k="KeyM">🗺 Map</button><button class="big" data-h="#journey">📜 Journey</button><button class="big" data-h="#binder">🃏 Binder</button><button class="big gold" data-k="Escape">☰ Menu</button></div></div>`;
    const cv = $('#map'); cv.addEventListener('pointerup', tapMap);
    el.querySelectorAll('[data-z]').forEach(b => b.onclick = () => { zoom = Math.max(.5, Math.min(4, zoom * +b.dataset.z)); drawMap(); });
  } else if (m === 'battle') {
    el.className = 'bt';
    el.innerHTML = `<div class="card"><div class="hp"><div><div class="eyebrow">Foe</div><b id="fn"></b><div class="bar"><i id="fh"></i></div><small id="fht"></small></div>
      <div><div class="eyebrow">Your partner</div><b id="pn"></b><div class="bar"><i id="ph"></i></div><small id="pht"></small></div></div><div class="bmsg" id="bmsg"></div></div>
      <div class="moves" id="moves"></div>`;
  } else if (m === 'scene') {
    el.className = 'sc';
    el.innerHTML = `<div class="card now"><b id="sw"></b><p id="sl"></p></div><div class="card hist" id="hist"></div>
      <div class="row"><button class="big gold" data-c="scene">Continue ▸</button><button class="big" data-c="skip">Skip</button></div>`;
  } else {
    el.className = 'menu';
    el.innerHTML = `<div class="card"><div class="eyebrow">${m === 'menu' ? 'Menu open on the top screen' : 'Pokebox'}</div><h2>${m === 'menu' ? 'Use the controller or tap here' : 'Main menu'}</h2></div>
      <div class="quick" style="grid-template-columns:1fr 1fr 1fr"><button class="big gold" data-k="Escape">◀ Back</button><button class="big" data-h="#world">🌍 World</button><button class="big" data-h="#journey">📜 Journey</button>
        <button class="big" data-h="#binder">🃏 Binder</button><button class="big" data-h="#shop">🛍 Shop</button><button class="big" data-h="#profile">👤 Trainer</button></div>`;
  }
  el.querySelectorAll('[data-k]').forEach(b => b.onclick = () => { vibrate(); send({ c: 'key', code: b.dataset.k, k: b.dataset.k === 'Escape' ? 'Escape' : b.dataset.k.replace('Key', '').toLowerCase() }); });
  el.querySelectorAll('[data-h]').forEach(b => b.onclick = () => { vibrate(); send({ c: 'hash', h: b.dataset.h }); });
  el.querySelectorAll('[data-c]').forEach(b => b.onclick = () => { vibrate(); send({ c: b.dataset.c }); });
}
function update(m) {
  if (m === 'explore') {
    $('#chap').textContent = S.chapter || 'Objective'; $('#goal').textContent = S.goal?.label || 'Explore Veyra';
    $('#dist').textContent = S.goal?.x != null && S.me ? Math.round(Math.hypot(S.goal.x - S.me.x, S.goal.z - S.me.z)) + ' m away' : '';
    const tk = JSON.stringify(S.team); const t = $('#team'); if (t.dataset.k !== tk) { t.dataset.k = tk; t.innerHTML = S.team.map(c => `<div class="mon" style="--tc:${TYPEC[c.t] || '#888'}"><img src="${esc(c.img)}" alt="" loading="lazy"><b>${esc(c.n)}</b></div>`).join('') || '<small class="muted">No team yet</small>'; }
    drawMap();
  } else if (m === 'battle' && S.battle) {
    const B = S.battle, hp = (id, p) => { if (!p) return; $('#' + id + 'n').textContent = p.n; const i = $('#' + id + 'h'); i.style.width = p.pct + '%'; i.className = p.pct < 30 ? 'low' : p.pct < 55 ? 'mid' : ''; $('#' + id + 'ht').textContent = `${p.hp} / ${p.max} HP`; };
    hp('f', B.foe); hp('p', B.me); $('#bmsg').textContent = B.msg || B.hint || '';
    const mk = JSON.stringify(B.moves); const box = $('#moves'); if (box.dataset.k !== mk) { box.dataset.k = mk;
      box.innerHTML = B.moves.map((v, i) => `<button class="big mv ${/\bcap\b/.test(v.c) ? 'cap' : ''} ${/\brun\b/.test(v.c) ? 'run' : ''}" data-i="${i}" ${v.d ? 'disabled' : ''} style="${v.tc ? `--tc:${v.tc}` : ''}"><b>${esc(v.t)}</b><small>${esc(v.s)}</small></button>`).join('')
        || '<div class="card center">Waiting…</div>';
      box.querySelectorAll('[data-i]').forEach(b => b.onclick = () => { vibrate(); send({ c: 'click', sel: '#fbMoves button', i: +b.dataset.i }); }); }
    if (!B.moves.length) box.onclick = () => send({ c: 'key', code: 'Space', k: ' ' }); else box.onclick = null; /* the Poké Ball timing tap */
  } else if (m === 'scene' && S.scene) {
    $('#sw').textContent = S.scene.who; $('#sl').textContent = S.scene.line;
    const hk = JSON.stringify(S.log); const h = $('#hist'); if (h.dataset.k !== hk) { h.dataset.k = hk; h.innerHTML = S.log.slice(0, -1).reverse().map(x => `<div><b>${esc(x.w)}:</b> ${esc(x.l)}</div>`).join('') || '<small>Dialogue history appears here.</small>'; }
  }
}

/* ---------- map: centred on you, towns, routes, objective; tap a visited town for the train */
let view = null;
function drawMap() {
  const cv = $('#map'); if (!cv || !S) return; const dpr = Math.min(2, devicePixelRatio || 1), w = cv.clientWidth, h = cv.clientHeight; if (!w || !h) return;
  if (cv.width !== Math.round(w * dpr)) { cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); }
  const g = cv.getContext('2d'); g.setTransform(dpr, 0, 0, dpr, 0, 0); g.fillStyle = '#2d70b8'; g.fillRect(0, 0, w, h);
  const size = M?.size || 1150, sc = Math.min(w, h) / 420 * zoom, cx = S.me?.x ?? 0, cz = S.me?.z ?? 0;
  const toS = (x, z) => [(x - cx) * sc + w / 2, (z - cz) * sc + h / 2]; view = { toS, sc };
  if (mapImg?.complete) { const [x0, y0] = toS(-size / 2, -size / 2); g.imageSmoothingEnabled = true; g.drawImage(mapImg, x0, y0, size * sc, size * sc); }
  g.lineJoin = g.lineCap = 'round';
  for (const r of M?.routes || []) for (const [lw, c] of [[5, 'rgba(30,22,10,.5)'], [2.5, '#f3e2b8']]) { g.lineWidth = lw; g.strokeStyle = c; g.beginPath(); r.pts.forEach(([x, z], i) => { const [a, b] = toS(x, z); i ? g.lineTo(a, b) : g.moveTo(a, b); }); g.stroke(); }
  if (S.goal?.x != null) { const [a, b] = toS(S.goal.x, S.goal.z), [ma, mb] = toS(cx, cz); g.setLineDash([7, 6]); g.lineWidth = 2.5; g.strokeStyle = 'rgba(255,210,87,.9)'; g.beginPath(); g.moveTo(ma, mb); g.lineTo(a, b); g.stroke(); g.setLineDash([]);
    g.save(); g.translate(Math.max(12, Math.min(w - 12, a)), Math.max(12, Math.min(h - 12, b))); g.rotate(Math.PI / 4); g.fillStyle = '#ffd257'; g.strokeStyle = '#1b1530'; g.lineWidth = 2.5; g.fillRect(-8, -8, 16, 16); g.strokeRect(-8, -8, 16, 16); g.restore(); }
  for (const T of M?.towns || []) { const [a, b] = toS(T.x, T.z), v = !!S.visited?.[T.id]; if (a < -60 || b < -40 || a > w + 60 || b > h + 40) continue;
    g.beginPath(); g.arc(a, b, 10, 0, 7); g.fillStyle = v ? '#ffd257' : '#6b6f7c'; g.fill(); g.lineWidth = 3; g.strokeStyle = sel === T.id ? '#5cf2d6' : '#1b1530'; g.stroke();
    g.font = '800 15px "Barlow Condensed",system-ui'; g.textAlign = 'center'; const tw = g.measureText(T.name).width + 14; g.fillStyle = 'rgba(18,16,40,.82)'; g.beginPath(); g.roundRect(a - tw / 2, b - 36, tw, 22, 7); g.fill(); g.fillStyle = '#fff'; g.fillText(T.name, a, b - 20); }
  if (S.me) { const [a, b] = toS(cx, cz), ang = Math.atan2(Math.cos(S.me.r), Math.sin(S.me.r)); g.save(); g.translate(a, b); g.beginPath(); g.arc(0, 0, 16, 0, 7); g.fillStyle = 'rgba(92,242,214,.25)'; g.fill(); g.rotate(ang + Math.PI / 2);
    g.fillStyle = '#fff'; g.strokeStyle = '#ff4e6a'; g.lineWidth = 3; g.beginPath(); g.moveTo(0, -12); g.lineTo(9, 9); g.lineTo(0, 4); g.lineTo(-9, 9); g.closePath(); g.fill(); g.stroke(); g.restore(); }
}
function tapMap(e) {
  if (!view || !M) return; const r = e.currentTarget.getBoundingClientRect(), x = e.clientX - r.left, y = e.clientY - r.top; let best = null, bd = 40;
  for (const T of M.towns) { const [a, b] = view.toS(T.x, T.z), d = Math.hypot(a - x, b - y - 14); if (d < bd) { bd = d; best = T; } }
  const sh = $('#sheet'); sel = best?.id || null; drawMap(); if (!best) { sh.hidden = true; return; }
  const v = !!S.visited?.[best.id], here = S.here === best.id;
  sh.innerHTML = `<div class="t"><div class="eyebrow">${here ? 'You are here' : v ? 'Relay Express' : 'Not visited yet'}</div><h2>${esc(best.name)}</h2></div>${v && !here ? `<button class="big gold" id="ride">Ride 🚂</button>` : ''}<button class="big" id="shx">✕</button>`;
  sh.hidden = false; vibrate();
  sh.querySelector('#ride')?.addEventListener('click', () => { send({ c: 'travel', id: best.id }); sh.hidden = true; sel = null; });
  sh.querySelector('#shx').onclick = () => { sh.hidden = true; sel = null; drawMap(); };
}
addEventListener('resize', () => drawMap());
