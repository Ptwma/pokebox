// Pokebox — gamepad support (PC controllers, Android handhelds like the AYN Thor / Odin / Retroid, BT pads on phones).
// Two sources, merged every frame:
//   1. the browser Gamepad API (PC, Chrome/Edge)
//   2. the Android app: MainActivity reads the built-in controls natively (KeyEvent / MotionEvent, reliable in a WebView)
//      and pushes them in through window.__padKey(code, down) and window.__padAxes(lx, ly, rx, ry, lt, rt, hx, hy).
// Layout (Xbox / Android positions: A = bottom): A talk/use when in reach, else jump · confirm, B roll · back, X use/talk, Y map, LB/RB zoom,
// LT/L3 run, Start menu, Select journey. In menus, dialogue, battles and the map the D-pad / left stick moves a focus
// ring between buttons and A presses the focused one.
const DEAD = .18;
const BTN = { A: 0, B: 1, X: 2, Y: 3, LB: 4, RB: 5, LT: 6, RT: 7, SELECT: 8, START: 9, L3: 10, R3: 11, UP: 12, DOWN: 13, LEFT: 14, RIGHT: 15 };
const nat = { b: new Array(16).fill(false), latch: new Array(16).fill(false), ax: [0, 0, 0, 0, 0, 0, 0, 0], t: 0 }; /* latch: a tap shorter than one frame still counts */
let prev = new Array(16).fill(false), active = false, lastNow = 0, getWorld = () => null, focusEl = null, navT = 0, lastStick = [0, 0];
const listeners = new Set();

/* ---- native bridge (Android) */
window.__padKey = (code, down) => { if (code in BTN) { nat.b[BTN[code]] = !!down; if (down) nat.latch[BTN[code]] = true; nat.t = performance.now(); } };
window.__padAxes = (...a) => { for (let i = 0; i < 8; i++) nat.ax[i] = +a[i] || 0; nat.t = performance.now(); };

function read() {
  const b = nat.b.map((v, i) => v || nat.latch[i]), ax = nat.ax.slice(0, 4); nat.latch.fill(false); let lt = nat.ax[4], rt = nat.ax[5];
  if (nat.ax[6] < -.5) b[BTN.LEFT] = true; if (nat.ax[6] > .5) b[BTN.RIGHT] = true; if (nat.ax[7] < -.5) b[BTN.UP] = true; if (nat.ax[7] > .5) b[BTN.DOWN] = true; // hat → d-pad
  let any = performance.now() - nat.t < 4000;
  const pads = navigator.getGamepads ? [...navigator.getGamepads()].filter(Boolean) : [];
  for (const p of pads) {
    if (!p.connected) continue;
    p.buttons.forEach((x, i) => { if (i < 16 && (x.pressed || x.value > .5)) { b[i] = true; any = true; } });
    for (let i = 0; i < 4; i++) if (Math.abs(p.axes[i] || 0) > Math.abs(ax[i])) ax[i] = p.axes[i] || 0;
    lt = Math.max(lt, p.buttons[6]?.value || 0); rt = Math.max(rt, p.buttons[7]?.value || 0); any = any || pads.length > 0;
  }
  if (lt > .5) b[BTN.LT] = true; if (rt > .5) b[BTN.RT] = true;
  const dz = v => Math.abs(v) < DEAD ? 0 : (v - Math.sign(v) * DEAD) / (1 - DEAD);
  return { b, lx: dz(ax[0]), ly: dz(ax[1]), rx: dz(ax[2]), ry: dz(ax[3]), lt, rt, any };
}

const key = (code, key = code) => { const o = { code, key, bubbles: true, cancelable: true }; (document.activeElement || document.body).dispatchEvent(new KeyboardEvent('keydown', o)); setTimeout(() => (document.activeElement || document.body).dispatchEvent(new KeyboardEvent('keyup', o)), 60); };
const vis = el => { if (!el || el.disabled || el.closest('[hidden]')) return false; const r = el.getBoundingClientRect(); if (r.width < 4 || r.height < 4 || r.bottom < 0 || r.right < 0 || r.top > innerHeight || r.left > innerWidth) return false;
  const cs = getComputedStyle(el); if (cs.visibility === 'hidden' || +cs.opacity < .15 || cs.pointerEvents === 'none') return false;
  const top = document.elementFromPoint(Math.min(innerWidth - 1, Math.max(0, r.left + r.width / 2)), Math.min(innerHeight - 1, Math.max(0, r.top + r.height / 2))); return !!top && (el === top || el.contains(top) || top.contains(el)); };
const SEL = 'button,a[href],[data-go],[data-st],[data-travel],[data-fly],[data-z],[tabindex]:not([tabindex="-1"]),input,select,.mv,.stc2';
function candidates() { return [...document.querySelectorAll(SEL)].filter(vis); }
function setFocus(el) { if (focusEl) focusEl.classList.remove('pad-focus'); focusEl = el; if (!el) return; el.classList.add('pad-focus'); try { el.focus({ preventScroll: true }); } catch {} el.scrollIntoView?.({ block: 'nearest', inline: 'nearest' }); }
function move(dx, dy) {
  const c = candidates(); if (!c.length) return; if (!focusEl || !c.includes(focusEl)) { setFocus(pickDefault(c)); return; }
  const r = focusEl.getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height / 2; let best = null, bs = 1e9;
  for (const el of c) { if (el === focusEl) continue; const q = el.getBoundingClientRect(), vx = q.left + q.width / 2 - cx, vy = q.top + q.height / 2 - cy, along = vx * dx + vy * dy; if (along <= 4) continue;
    const across = Math.abs(vx * dy - vy * dx), s = along + across * 2.2; if (s < bs) { bs = s; best = el; } }
  if (best) setFocus(best);
}
function pickDefault(c) { return c.find(e => e.matches('.btn.gold,.stc2,.mv:not(:disabled),#lvOk,#wYes')) || c[0]; }
function press(el) { if (!el) return; el.click(); }

/* explore = the 3D world has the controls (nothing on top of it) */
function overlay() {
  if (!document.querySelector('#scene')?.hidden) return 'scene';
  if (document.body.classList.contains('in-battle') || document.querySelector('.fb-ui')) return 'battle';
  const m = document.querySelector('#wModal'); if (m && !m.hidden) return 'modal';
  for (const s of ['#lattice:not([hidden])', '#gMenu:not([hidden])', '#modal:not([hidden])', '#lvup:not([hidden])', '.upd', '#opening:not([hidden])']) if (document.querySelector(s)) return 'ui';
  return null;
}
function frame(now) {
  requestAnimationFrame(frame);
  const dt = Math.min(.05, Math.max(0, (now - (lastNow || now)) / 1000)); lastNow = now;
  const s = read(); if (!s.any && !active) return;
  const W = getWorld(), down = i => s.b[i] && !prev[i], held = i => s.b[i];
  const used = s.b.some(Boolean) || Math.abs(s.lx) + Math.abs(s.ly) + Math.abs(s.rx) + Math.abs(s.ry) > 0;
  if (used && !active) { active = true; document.documentElement.classList.add('pad'); listeners.forEach(f => f(true)); }
  const ov = overlay(), inWorld = location.hash === '#world' && W?.running && !W.paused && W.mode === 'explore' && !ov;
  if (inWorld) {
    if (focusEl) setFocus(null);
    W.setStick(s.lx, s.ly); lastStick = [s.lx, s.ly]; W.setRun(held(BTN.LT) || held(BTN.L3) || held(BTN.RT));
    const k = 2.8 * dt * (W.sens?.() || 1); W.look?.(s.rx * Math.abs(s.rx) * k * 1.3, s.ry * Math.abs(s.ry) * k * .8);
    const z = 7 * dt; if (held(BTN.LB) || held(BTN.DOWN)) W.zoomBy?.(z); if (held(BTN.RB) || held(BTN.UP)) W.zoomBy?.(-z);
    if (down(BTN.A)) { const k = W.near ? 'KeyE' : 'Space'; W.key(k); setTimeout(() => W.key(k, false), 80); } /* A talks/uses when something is in reach, else jumps (like Pokémon) */
    if (down(BTN.B)) W.key('KeyQ'), setTimeout(() => W.key('KeyQ', false), 80);
    if (down(BTN.X)) W.key('KeyE'), setTimeout(() => W.key('KeyE', false), 80);
    if (down(BTN.Y)) key('KeyM', 'm');
    if (down(BTN.START)) key('Escape', 'Escape');
    if (down(BTN.SELECT)) location.hash = '#journey';
  } else {
    if (W && (lastStick[0] || lastStick[1])) { W.setStick(0, 0); W.setRun(false); lastStick = [0, 0]; }
    // focus navigation: d-pad steps, stick steps with repeat
    let dx = 0, dy = 0; if (down(BTN.LEFT)) dx = -1; else if (down(BTN.RIGHT)) dx = 1; else if (down(BTN.UP)) dy = -1; else if (down(BTN.DOWN)) dy = 1;
    if (!dx && !dy && Math.hypot(s.lx, s.ly) > .6 && now > navT) { if (Math.abs(s.lx) > Math.abs(s.ly)) dx = Math.sign(s.lx); else dy = Math.sign(s.ly); navT = now + 220; }
    if (Math.hypot(s.lx, s.ly) < .3) navT = 0;
    if (dx || dy) move(dx, dy);
    if (s.ry) { const sc = document.querySelector('.gm .gbody,#modal .mbody,.page.active,main') ; sc?.scrollBy?.(0, s.ry * 14); }
    if (down(BTN.A)) { if (ov === 'scene') document.querySelector('#scene')?.click(); else if (focusEl && candidates().includes(focusEl)) press(focusEl); else { const c = candidates(); setFocus(pickDefault(c)); if (ov === 'battle' || !c.length) key('Space', ' '); } }
    if (down(BTN.B)) { if (ov === 'scene') document.querySelector('#scene .cskip')?.click(); else key('Escape', 'Escape'); }
    if (down(BTN.START)) key('Escape', 'Escape');
    if (ov === 'battle') { for (const [bi, d] of [[BTN.X, 'Digit1'], [BTN.Y, 'Digit4']]) if (down(bi)) key(d); }
  }
  prev = s.b;
}
requestAnimationFrame(frame);
// a mouse/touch after the pad hands the screen back to touch controls
addEventListener('pointerdown', e => { if (active && e.pointerType !== '') { active = false; document.documentElement.classList.remove('pad'); setFocus(null); listeners.forEach(f => f(false)); } }, true);

export const padActive = () => active;
export const onPad = f => listeners.add(f);
export function bindWorld(fn) { getWorld = fn; }
/* button glyphs for prompts: "E" → X button etc. */
export const glyph = b => `<b class="padg padg-${b.toLowerCase()}">${b}</b>`;
/* devices with built-in controls (AYN Thor): start in controller mode, touch still switches back */
export function assume() { active = true; document.documentElement.classList.add('pad'); listeners.forEach(f => f(true)); }
