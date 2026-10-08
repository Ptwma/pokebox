// Pokebox — second screen link (game side). The bottom screen of dual-screen handhelds (AYN Thor) shows bottom.html;
// this module feeds it a small state snapshot a few times a second and carries out what is tapped there.
// Transport: Android → window.PokeboxDual (MainActivity relays to the bottom WebView) · PC test → BroadcastChannel
// (open pokebox-game/bottom.html in a second window next to the game). Nothing is sent while no bottom screen is attached.
import { DB, S, cardImg } from './core.js';
import * as C from './core.js';
import * as QS from './quests.js';
import * as P from './progress.js';

const N = () => window.PokeboxDual;
let bc = null; try { bc = new BroadcastChannel('pokebox-dual'); } catch {}
let linked = false, ctx = null, timer = 0, sentMap = false, log = [], lastLine = '';
const send = o => { const j = JSON.stringify(o); if (N()?.toBottom) N().toBottom(j); else bc?.postMessage(j); };

function setLinked(v) {
  linked = !!v; document.documentElement.classList.toggle('dual', linked); clearInterval(timer); sentMap = false;
  if (linked) { timer = setInterval(tick, 250); tick(); }
}
window.__dualChanged = v => setLinked(v);
window.__fromBottom = j => { let m; try { m = JSON.parse(j); } catch { return; } handle(m); };
if (bc) bc.onmessage = e => { let m; try { m = JSON.parse(e.data); } catch { return; } if (m.c) { if (!linked) setLinked(true); handle(m); } };

function key(code, k = code) { const o = { code, key: k, bubbles: true, cancelable: true }; const t = document.activeElement || document.body; t.dispatchEvent(new KeyboardEvent('keydown', o)); setTimeout(() => t.dispatchEvent(new KeyboardEvent('keyup', o)), 60); }
function handle(m) {
  const W = ctx?.world();
  switch (m.c) {
    case 'hello': sentMap = false; tick(); break;
    case 'key': key(m.code, m.k); break;
    case 'wkey': if (W) { W.key(m.code); setTimeout(() => W.key(m.code, false), 80); } break;
    case 'click': { const el = [...document.querySelectorAll(m.sel)][m.i | 0]; if (el && !el.disabled) el.click(); break; }
    case 'scene': document.querySelector('#scene')?.click(); break;
    case 'skip': document.querySelector('#scene .cskip')?.click(); break;
    case 'hash': location.hash = m.h; break;
    case 'menu': ctx?.menu?.(); break;
    case 'travel': if (W && QS.Q().visited?.[m.id] && W.area !== m.id && W.mode === 'explore') ctx?.travel?.(m.id); break;
  }
  setTimeout(tick, 120);
}

function mode() {
  if (!document.querySelector('#scene')?.hidden) return 'scene';
  if (document.querySelector('.fb-ui')) return 'battle';
  if (document.querySelector('#gMenu:not([hidden]),#lattice:not([hidden]),#wModal:not([hidden])')) return 'menu';
  return location.hash === '#world' ? 'explore' : 'app';
}
const txt = (sel, root = document) => root.querySelector(sel)?.textContent?.trim() || '';
function plate(sel) { const p = document.querySelector(sel); if (!p) return null; const t = p.textContent.replace(/\s+/g, ' '), hp = t.match(/(\d+)\s*\/\s*(\d+)\s*HP/);
  return { n: txt('b', p), hp: hp ? +hp[1] : 0, max: hp ? +hp[2] : 1, pct: parseFloat(p.querySelector('.fb-hp i')?.style.width) || 0 }; }

function tick() {
  if (!linked || !ctx) return;
  const W = ctx.world(), md = mode(), s = P.ensure();
  if (W && !sentMap && W.mapCanvas) {
    const src = W.mapCanvas, c = document.createElement('canvas'), k = Math.min(1, 640 / src.width); c.width = c.height = Math.round(src.width * k);
    const g = c.getContext('2d'); g.imageSmoothingQuality = 'high'; g.drawImage(src, 0, 0, c.width, c.height);
    send({ t: 'map', img: c.toDataURL('image/jpeg', .82), size: W.size,
      towns: Object.keys(W.regions).map(id => ({ id, x: W.regions[id].x, z: W.regions[id].z, name: W.areas[id]?.name || id })),
      routes: (W.routes || []).map(r => ({ name: r.name, pts: r.pts.filter((_, i) => i % 3 === 0 || i === r.pts.length - 1) })) });
    sentMap = true;
  }
  // dialogue log (what was said, newest last)
  if (md === 'scene') { const who = txt('#scene .scname b'), line = txt('#scP'); /* the line types itself out: grow the last entry, add a new one when a new line starts */
    if (line && line !== lastLine) { const last = log[log.length - 1]; if (last && last.w === who && line.startsWith(last.l)) last.l = line; else log.push({ w: who, l: line }); lastLine = line; if (log.length > 30) log.shift(); } }
  const team = (S.team || []).map(i => DB.cards[i]).filter(Boolean).map(c => ({ n: c.n, t: c.t, img: cardImg(c) }));
  const tg = QS.target(), pp = W?.player?.group.position, L = C.levelInfo();
  const st = { t: 'state', mode: md, name: s.name, lv: L.lv, xp: L.pct, coins: S.coins || 0, team, area: txt('#wName') || (W ? (W.areas[W.area]?.name || '') : ''), clock: (document.querySelector('#wClock')?.innerText || '').replace(/\s*\n\s*/g, ' · ').trim(),
    me: pp ? { x: pp.x, z: pp.z, r: W.player.group.rotation.y } : null, goal: tg && tg.x != null ? { x: tg.x, z: tg.z, label: tg.label } : tg ? { label: tg.label } : null,
    visited: QS.Q().visited || {}, here: W?.area, chapter: txt('#wQuest .eyebrow'), log: log.slice(-8) };
  if (md === 'battle') st.battle = { foe: plate('#fbE'), me: plate('#fbP'), hint: txt('#fbHint'), msg: [...document.querySelectorAll('#fbLog p')].slice(-1)[0]?.textContent || '',
    moves: [...document.querySelectorAll('#fbMoves button')].map(b => ({ t: txt('b', b) || b.textContent.trim(), s: txt('small', b), d: b.disabled, c: b.className, tc: b.style.getPropertyValue('--tc') })) };
  if (md === 'scene') st.scene = { who: txt('#scene .scname b'), line: txt('#scP') };
  send(st);
}

/** ctx: { world: () => W, travel(id), menu() } */
export function initDual(c) {
  ctx = c;
  try { if (N()?.has?.()) setLinked(true); } catch {}
  if (bc) bc.postMessage(JSON.stringify({ t: 'ping' }));
}
export const isDual = () => linked;
export function deviceInfo() { try { return JSON.parse(N()?.info?.() || 'null'); } catch { return null; } }
