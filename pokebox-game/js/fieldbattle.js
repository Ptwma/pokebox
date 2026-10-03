// Pokebox — battles that happen right where you are in the open world (Pokémon style).
// Your lead card's creature steps out next to you, the opponent's creature faces it, the camera swings to the side,
// and the fight plays out with the battle.js rules (types, energy, signature moves, ultimates, guard, switching).
// Wild Echoes can be CAPTURED once weakened: the blank Lattice card flies out and shakes 1-3 times.
// Presentation is built around the turn: a CHOOSE phase (turn banner, matchup + speed hint, foe intent, moves panel up)
// and a RESOLVE phase (panel down, acting plate lit, anticipation → execution → hit-stop impact → recovery, camera shots).
import * as C from './core.js';
import * as RK from './rank.js';
import { DB, isMon } from './core.js';
import { Battle, fighter, SIG, MOVES, ENERGY_MAX, estimate, mult } from './battle.js';
import { onomato, impactFrame, TYPE_COL as TC } from './comicfx.js';
import { cardImg } from './core.js';
import * as QS from './quests.js';

const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const FAST = () => window.__pbxFast || 1; // automated tests run battles faster
const wait = ms => new Promise(r => setTimeout(r, ms / FAST()));
const ease = k => k < .5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
const RN = ['C', 'U', 'R', 'H', 'UR', 'IR', 'SR'];

export function createFieldBattle(ctx) {
  const { THREE, scene, camera, H, hooks, makeCardPet } = ctx;
  let B = null, ui = null, busy = false, resolveFn = null, state = null;
  const tweens = [];
  const tween = (ms, fn) => new Promise(res => tweens.push({ t: 0, ms, fn, res }));
  const tmp = new THREE.Vector3(), proj = new THREE.Vector3();

  function myTeam() {
    const S = C.S, ids = (S.team || []).filter(i => S.owned[i]).slice(0, 3);
    if (!ids.length) { const q = QS.Q(); if (q.starter != null && S.owned[q.starter]) ids.push(q.starter); }
    if (ids.length < 3) for (const c of C.ownedCards().filter(isMon).sort((a, b) => b.hp + b.atk - a.hp - a.atk)) { if (ids.length >= 3) break; if (!ids.includes(c.i)) ids.push(c.i); }
    return ids.map(i => fighter(DB.cards[i]));
  }
  function trainerTeam(key, spec) {
    let s = 0; for (const ch of key) s = (s * 31 + ch.charCodeAt(0)) >>> 0; const R = () => ((s = (Math.imul(s, 1664525) + 1013904223) >>> 0) / 4294967296);
    const pool = DB.cards.filter(c => isMon(c) && spec.types.includes(c.t) && c.r >= spec.r[0] && c.r <= spec.r[1] && DB.setBy[c.s]?.sellable);
    const team = [], used = new Set(); let guard = 0;
    while (team.length < spec.n && pool.length && guard++ < 200) { const c = pool[(R() * pool.length) | 0]; if (!used.has(c.n)) { used.add(c.n); team.push(c); } }
    return team.map(c => fighter(c, spec.lvl));
  }

  /* ---------- staging */
  function creature(f, spot, { echo = 0 } = {}) {
    const cp = makeCardPet({ i: f.card.i, f: f.card.f, n: f.card.n, t: f.card.t }, cardImg(f.card), { size: 1.5 });
    cp.group.position.copy(spot); cp.setFog?.(scene.fog); if (echo) cp.setEcho(echo); scene.add(cp.group); cp.home = spot.clone(); return cp;
  }
  const TYPE_SFX = { Fire: 'flame', Lightning: 'zap', Water: 'pop', Metal: 'clink', Fighting: 'thud', Dragon: 'boom', Darkness: 'thud', Psychic: 'sparkle', Grass: 'pop', Fairy: 'sparkle' };
  function ring(spot, color) { // the fighter's footprint on the field: shows side, type and whose turn it is
    const g = new THREE.Group(), mat = c => new THREE.MeshBasicMaterial({ color: c, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false });
    const r = new THREE.Mesh(new THREE.RingGeometry(.86, 1.02, 56), mat(color)), d = new THREE.Mesh(new THREE.CircleGeometry(.86, 40), mat(color));
    for (const m of [r, d]) { m.rotation.x = -Math.PI / 2; m.renderOrder = 2; g.add(m); }
    g.position.copy(spot); g.position.y = H(spot.x, spot.z) + .06; scene.add(g); return { g, r, d, on: 0, flare: 0 };
  }
  function setRingColor(rg, color) { rg.r.material.color.set(color); rg.d.material.color.set(color); }
  function setupStage(spec) {
    const pl = ctx.player(), P0 = pl.group.position.clone();
    let foe = spec.wild ? new THREE.Vector3(spec.wild.x, 0, spec.wild.z) : new THREE.Vector3(spec.npc.x, 0, spec.npc.z);
    const D = foe.clone().sub(P0).setY(0); if (D.lengthSq() < .01) D.set(0, 0, 1); D.normalize();
    const side = new THREE.Vector3(-D.z, 0, D.x);
    const a = P0.clone().addScaledVector(D, 2.4).addScaledVector(side, -.6), b = P0.clone().addScaledVector(D, 8.6).addScaledVector(side, .4);
    a.y = H(a.x, a.z); b.y = H(b.x, b.z);
    pl.group.rotation.y = Math.atan2(D.x, D.z);
    const pet = ctx.pet(); if (pet) pet.group.visible = false;
    const st = { P0, D, side, a, b, center: a.clone().lerp(b, .5), camS: 1, camDist: 7.4 };
    pickCamera(st, [pl.group, spec.wild?.g, spec.npc?.ch?.group].filter(Boolean));
    ctx.arena?.(st.center.x, st.center.z, 11, 1);
    return st;
  }
  // choose the camera side/distance that sees both fighters (trees, houses and hills used to block the fixed angle)
  const ray = new THREE.Raycaster();
  // framing: behind and beside your creature (lower-left of the frame), the foe big in the upper right — reads like a duel
  function camPos(st, s, dist, out) { const a = st.a; out.copy(a).addScaledVector(st.D, -dist * .62).addScaledVector(st.side, s * dist * .4); out.y = Math.max(a.y + 2.1 + dist * .16, H(out.x, out.z) + 1.5); return out; }
  function pickCamera(st, ignore) {
    const skip = o => { for (let p = o; p; p = p.parent) if (ignore.includes(p) || p.userData?.grass || p.isPoints || p.isSprite || p.isLine) return true; return false; };
    const targets = scene.children.filter(o => o.visible && !skip(o));
    let best = null; const pos = new THREE.Vector3(), to = new THREE.Vector3(), dir = new THREE.Vector3();
    for (const [s, dist] of [[1, 7.4], [-1, 7.4], [1, 5.8], [-1, 5.8], [1, 9.2], [-1, 9.2]]) {
      camPos(st, s, dist, pos); let hits = 0;
      for (const [p, w] of [[st.a, 1.4], [st.b, 1.4], [st.center, 1]]) {
        to.copy(p); to.y += 1.1; dir.copy(to).sub(pos); const len = dir.length(); ray.set(pos, dir.divideScalar(len)); ray.camera = camera; ray.far = Math.max(.1, len - .6);
        try { if (ray.intersectObjects(targets, true).some(h => h.object.visible && !skip(h.object))) hits += w; } catch { }
      }
      const score = hits + (dist === 7.4 ? 0 : .15) + (s > 0 ? 0 : .05);
      if (!best || score < best.score) best = { s, dist, score };
    }
    st.camS = best.s; st.camDist = best.dist; st.camScore = best.score;
    st.cleared = clearCorridors(st, skip);
  }
  // props (trees, rocks, fences...) standing between any battle camera and the fighters are tucked away for the fight
  function clearCorridors(st, skip) {
    const cams = [camPos(st, st.camS, st.camDist, new THREE.Vector3())];
    for (const [A, Bp] of [[st.a, st.b], [st.b, st.a]]) { const dir = Bp.clone().sub(A).setY(0).normalize(); cams.push(A.clone().addScaledVector(dir, -3.3).addScaledVector(st.side, st.camS * 1.9)); }
    const segs = []; for (const c of cams) for (const t of [st.a, st.b, st.center]) segs.push([c.x, c.z, t.x, t.z]);
    const near = (x, z) => { for (const [ax, az, bx, bz] of segs) { const dx = bx - ax, dz = bz - az, L = dx * dx + dz * dz, k = Math.max(0, Math.min(1, ((x - ax) * dx + (z - az) * dz) / L)), ex = ax + dx * k - x, ez = az + dz * k - z; if (ex * ex + ez * ez < (k < .15 ? 6.2 : 2.6)) return true; } return false; };
    const R2 = (st.camDist + 12) ** 2, cx = st.center.x, cz = st.center.z, out = [], m4 = new THREE.Matrix4(), zero = new THREE.Matrix4().makeScale(0, 0, 0), p = new THREE.Vector3();
    scene.traverse(o => {
      if (!o.visible || skip(o) || o === scene) return;
      if (o.isInstancedMesh) { if (o.count > 20000) return; o.updateWorldMatrix(true, false); let hit = false;
        for (let i = 0; i < o.count; i++) { o.getMatrixAt(i, m4); p.setFromMatrixPosition(m4).applyMatrix4(o.matrixWorld); if ((p.x - cx) ** 2 + (p.z - cz) ** 2 > R2 || !near(p.x, p.z)) continue;
          out.push({ o, i, m: m4.clone() }); o.setMatrixAt(i, zero); hit = true; }
        if (hit) o.instanceMatrix.needsUpdate = true; }
      else if (o.isMesh && !o.isSkinnedMesh && o.geometry && o.parent !== scene) { o.getWorldPosition(p); if ((p.x - cx) ** 2 + (p.z - cz) ** 2 > R2) return;
        o.geometry.boundingSphere || o.geometry.computeBoundingSphere(); const r = o.geometry.boundingSphere.radius * o.getWorldScale(new THREE.Vector3()).x;
        if (r < 6 && near(p.x, p.z)) { out.push({ o }); o.visible = false; } }
    });
    return out;
  }
  function restoreCorridors(list) { const dirty = new Set(); for (const c of list || []) { if (c.m) { c.o.setMatrixAt(c.i, c.m); dirty.add(c.o); } else c.o.visible = true; } for (const o of dirty) o.instanceMatrix.needsUpdate = true; }
  // camera shots: wide while choosing, over the attacker's shoulder for anticipation, on the target for impact
  let shake = 0, camK = 0, shot = null;
  const look = new THREE.Vector3(), lookS = new THREE.Vector3(), tmp2 = new THREE.Vector3();
  function battleCam(cam, dt) {
    const st = state; if (!st) return; camK = Math.min(1, camK + dt * 1.6);
    const want = tmp;
    if (shot?.mode === 'over') {
      const A = shot.a, Bp = shot.b, dir = tmp2.copy(Bp).sub(A).setY(0).normalize();
      want.copy(A).addScaledVector(dir, -3.3).addScaledVector(st.side, st.camS * 1.9); want.y = Math.max(A.y + 2.2, H(want.x, want.z) + 1.4);
      look.copy(A).lerp(Bp, .72); look.y = Bp.y + 1.05;
    } else if (shot?.mode === 'impact') {
      camPos(st, st.camS, st.camDist * .8, want); want.lerp(shot.b, .2); want.y = Math.max(want.y, H(want.x, want.z) + 1.4);
      look.copy(shot.b); look.y += 1;
    } else { camPos(st, st.camS, st.camDist, want); look.copy(st.a).lerp(st.b, .62); look.y += .9; }
    const k = 1 - Math.exp(-dt * (camK < 1 ? 2.6 : shot ? 5.5 : 3.2));
    cam.position.lerp(want, k); if (lookS.lengthSq() === 0) lookS.copy(look); lookS.lerp(look, k);
    if (shake > 0) { cam.position.x += (Math.random() - .5) * shake; cam.position.y += (Math.random() - .5) * shake * .6; shake = Math.max(0, shake - dt * 2.4); }
    cam.lookAt(lookS);
  }

  /* ---------- UI */
  function buildUI(spec) {
    ui = document.createElement('div'); ui.className = 'fb-ui';
    ui.innerHTML = `<div class="fb-plate e" id="fbE"></div><div class="fb-plate p" id="fbP"></div>
      <div class="fb-turn" id="fbTurn"></div><div class="fb-cut" id="fbCut"></div>
      <div class="fb-log" id="fbLog"></div><div class="fb-dock" id="fbDock"><div class="fb-hint" id="fbHint"></div><div class="fb-moves" id="fbMoves"></div></div><div class="fb-fx" id="fbFx"></div>
      <div class="fb-title">${spec.kind === 'wild' ? 'Wild ' + esc(spec.wild.card.n) + ' appeared!' : esc(spec.name) + ' wants to battle!'}</div>`;
    (document.getElementById('worldWrap') || document.body).append(ui);
    ui.querySelector('.fb-title').animate([{ transform: 'translate(-50%,-30px) scale(.8)', opacity: 0 }, { transform: 'translate(-50%,0) scale(1)', opacity: 1, offset: .2 }, { opacity: 1, offset: .8 }, { opacity: 0 }], { duration: 2000, fill: 'forwards' });
    document.body.classList.add('in-battle');
    addEventListener('keydown', onKey, true);
  }
  function onKey(e) { // 1-9 pick an action, so the PC player never has to reach for the mouse
    if (!ui || busy || !/^Digit[1-9]$/.test(e.code)) return; const b = [...ui.querySelectorAll('#fbMoves button:not([disabled])')][+e.code.slice(5) - 1];
    if (b) { e.preventDefault(); e.stopPropagation(); b.click(); }
  }
  function plate(side) {
    const f = B.active(side), el = ui.querySelector(side === 'e' ? '#fbE' : '#fbP'), hp = Math.max(0, Math.round(f._hp ?? f.hp)), pct = hp / f.maxHp * 100, en = f._en ?? f.energy;
    const team = B[side].team.map((x, i) => `<i class="${x.hp <= 0 ? 'down' : ''} ${i === B[side].act ? 'on' : ''}"></i>`).join('');
    const buffs = ['atk', 'def', 'spd'].filter(k => f.buff[k] !== 1).map(k => `<span class="fb-bf ${f.buff[k] > 1 ? 'up' : 'dn'}">${k.toUpperCase()}${f.buff[k] > 1 ? '▲' : '▼'}</span>`).join('');
    // the foe telegraphs what it can do next turn — that is what makes Guard and switching real decisions
    const intent = side === 'e' && !B.over ? (f.energy >= MOVES.ult.cost ? `<div class="fb-intent ult">⚠ Ultimate charged — it may unleash it</div>` : f.energy >= MOVES.sig.cost ? `<div class="fb-intent">${esc((SIG[f.type] || SIG.Colorless).name)} ready</div>` : '') : '';
    el.style.setProperty('--tc', TC[f.type] || '#ccc');
    el.innerHTML = `<div class="fb-top"><b>${esc(f.name)}</b><span class="fb-type">${esc(f.type)}</span>${f.status ? `<span class="fb-st ${f.status}">${f.status === 'burn' ? 'BRN' : 'PAR'} ${f.statusT}</span>` : ''}${buffs}<span class="fb-r">${RN[f.card.r] || ''}</span></div>
      <div class="fb-hp"><i style="width:${pct}%" class="${pct < 30 ? 'low' : pct < 55 ? 'mid' : ''}"></i></div>
      <div class="fb-bot"><small>${hp} / ${f.maxHp} HP</small><span class="fb-en" title="Energy">${Array.from({ length: ENERGY_MAX }, (_, i) => `<i class="${i < en ? 'on' : ''}"></i>`).join('')}</span><span class="fb-team">${team}</span></div>${intent}`;
  }
  function log(html) { const l = ui.querySelector('#fbLog'); const p = document.createElement('p'); p.innerHTML = html; l.append(p); while (l.children.length > 2) l.firstChild.remove(); }
  function moves() {
    const box = ui.querySelector('#fbMoves'), me = B.active('p'), foe = B.active('e'), sig = SIG[me.type] || SIG.Colorless, wild = state.spec.kind === 'wild';
    let n = 0; const key = () => `<kbd>${++n}</kbd>`;
    const btn = (k, label, sub, cls = '') => `<button class="mv lg ${cls}" data-m="${k}" type="button" ${B.canUse(me, k) && !busy ? '' : 'disabled'} style="--tc:${TC[me.type] || '#ccc'}">${key()}<b>${label}</b><small>${sub}</small></button>`;
    const chance = Math.round(captureChance(foe) * 100);
    box.innerHTML = btn('attack', 'Attack', `≈${estimate(me, foe, 'attack')} dmg · +1⚡`) + btn('sig', sig.name, `≈${estimate(me, foe, 'sig')} · ${sig.note} · ⚡${MOVES.sig.cost}`, 'sig') + btn('ult', 'Ultimate', `≈${estimate(me, foe, 'ult')} dmg · ⚡${MOVES.ult.cost}`, 'ult') + btn('guard', 'Guard', '−55% dmg this turn · +1⚡', 'guard')
      + B.p.team.map((f, i) => i !== B.p.act && f.hp > 0 ? `<button class="mv lg sw" data-sw="${i}" type="button" ${busy ? 'disabled' : ''} style="--tc:${TC[f.type] || '#ccc'}">${key()}<b>Switch</b><small>${esc(f.name)} · ${esc(f.type)}${mult(foe.type, f.type) < 1 ? ' · resists' : mult(foe.type, f.type) > 1 ? ' · weak' : ''}</small></button>` : '').join('')
      + (wild ? `<button class="mv lg cap" data-cap type="button" ${busy ? 'disabled' : ''}>${key()}<b>Capture</b><small>${chance}% chance</small></button><button class="mv lg run" data-run type="button" ${busy ? 'disabled' : ''}>${key()}<b>Run</b><small>escape</small></button>` : '');
    box.querySelectorAll('[data-m]').forEach(x => x.onclick = () => act({ kind: x.dataset.m }));
    box.querySelectorAll('[data-sw]').forEach(x => x.onclick = () => act({ kind: 'switch', to: +x.dataset.sw }));
    box.querySelector('[data-cap]')?.addEventListener('click', capture); box.querySelector('[data-run]')?.addEventListener('click', run);
    // matchup + turn order: the two facts every decision depends on
    const m = mult(me.type, foe.type), mFoe = mult(foe.type, me.type), sp = s => B.active(s).spd * B.active(s).buff.spd, first = sp('p') >= sp('e');
    ui.querySelector('#fbHint').innerHTML = `<span class="${m > 1 ? 'good' : m < 1 ? 'bad' : ''}">${esc(me.type)} → ${esc(foe.type)}: ${m > 1 ? 'super effective ×' + m : m < 1 ? 'resisted ×' + m : 'neutral'}</span>`
      + (mFoe > 1 ? `<span class="bad">its ${esc(foe.type)} hits you hard</span>` : '') + `<span>${first ? 'You move first' : esc(foe.name) + ' is faster — it moves first'}</span>`;
  }
  function phase(choose) { // CHOOSE: panel up, your ring lit · RESOLVE: panel down, the actor is lit instead
    ui?.classList.toggle('choose', choose); if (!state) return;
    state.ring.p.on = choose ? 1 : 0; state.ring.e.on = 0;
    if (choose) { const t = ui.querySelector('#fbTurn'); t.innerHTML = `<small>Turn ${B.turn}</small><b>Your move</b>`; t.getAnimations().forEach(a => a.cancel());
      t.animate([{ opacity: 0, transform: 'translate(-50%,-14px)' }, { opacity: 1, transform: 'translate(-50%,0)', offset: .15 }, { opacity: 1, offset: .75 }, { opacity: .0 }], { duration: 1900, fill: 'forwards' }); }
  }
  function banner(small, big, side) { // who is acting right now — makes the foe's reply read as ITS turn, not as damage from your own attack
    const t = ui?.querySelector('#fbTurn'); if (!t) return; t.innerHTML = `<small>${small}</small><b class="${side === 'e' ? 'foe' : ''}">${esc(big)}</b>`; t.getAnimations().forEach(a => a.cancel());
    t.animate([{ opacity: 0, transform: 'translate(-50%,-10px)' }, { opacity: 1, transform: 'translate(-50%,0)', offset: .15 }, { opacity: 1, offset: .7 }, { opacity: 0 }], { duration: 1500, fill: 'forwards' }); }
  function acting(side) { for (const s of ['p', 'e']) { ui?.querySelector(s === 'e' ? '#fbE' : '#fbP')?.classList.toggle('acting', s === side); if (state) state.ring[s].on = s === side ? 1 : 0; } }
  function cutIn(name, type, big) { // move name banner for signature moves and ultimates
    const el = ui.querySelector('#fbCut'); el.style.setProperty('--tc', TC[type] || '#fff'); el.className = 'fb-cut' + (big ? ' big' : ''); el.innerHTML = `<b>${esc(name)}</b>`;
    el.getAnimations().forEach(a => a.cancel());
    el.animate([{ opacity: 0, transform: 'translate(-60%,-50%) skewX(-12deg)' }, { opacity: 1, transform: 'translate(-50%,-50%) skewX(-12deg)', offset: .18 }, { opacity: 1, offset: .78 }, { opacity: 0, transform: 'translate(-40%,-50%) skewX(-12deg)' }], { duration: big ? 1100 : 850, fill: 'forwards' });
  }
  function storyCapture(card) { const st = QS.stepNow(); return !!st && st.kind === 'capture' && (!st.type || [].concat(st.type).includes(card?.t)); }
  function captureHint() { // tell the player when to throw the card
    const foe = B?.active('e'); if (!foe || state?.spec.kind !== 'wild' || foe.hp <= 0) return; const k = foe.hp / foe.maxHp, cap = ui?.querySelector('[data-cap]');
    if (cap) cap.classList.toggle('hint', k < .4);
    if (k < .4 && !state.hinted) { state.hinted = true; log(`<b class="gold">It's weak — press CAPTURE now!</b>`); }
  }
  function captureChance(f) { return Math.max(.08, Math.min(.95, .22 + (1 - f.hp / f.maxHp) * .72 - f.card.r * .05 + (f.status ? .1 : 0))); }
  function screenOf(obj, dy = 1.2) { obj.getWorldPosition(proj); proj.y += dy; proj.project(camera); const r = ui.getBoundingClientRect(); return { x: (proj.x * .5 + .5) * r.width, y: (-proj.y * .5 + .5) * r.height }; }
  function floatText(obj, text, cls) { const p = screenOf(obj, 1.8), d = document.createElement('div'); d.className = 'fb-float ' + cls; d.textContent = text; d.style.left = p.x + 'px'; d.style.top = p.y + 'px'; ui.querySelector('#fbFx').append(d);
    d.animate([{ transform: 'translate(-50%,-50%) scale(.4)', opacity: 0 }, { transform: 'translate(-50%,-90%) scale(1.2)', opacity: 1, offset: .2 }, { transform: 'translate(-50%,-200%) scale(1)', opacity: 0 }], { duration: 1100 }).finished.then(() => d.remove(), () => d.remove()); }

  /* ---------- animation helpers */
  function orb(color, big) {
    const s = new THREE.Sprite(new THREE.SpriteMaterial({ color: new THREE.Color(color).multiplyScalar(2.2), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, map: glowTex() }));
    s.scale.setScalar(big ? 1.6 : 1); scene.add(s); return s;
  }
  let _glow = null; function glowTex() { if (_glow) return _glow; const c = document.createElement('canvas'); c.width = c.height = 64; const g = c.getContext('2d'), gr = g.createRadialGradient(32, 32, 0, 32, 32, 32); gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(.35, 'rgba(255,255,255,.7)'); gr.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = gr; g.fillRect(0, 0, 64, 64); return _glow = new THREE.CanvasTexture(c); }
  const drop = s => { scene.remove(s); s.material.dispose(); };
  function burst(at, color, big) {
    const n = big ? 26 : 14, parts = [];
    for (let i = 0; i < n; i++) { const s = orb(color, false); s.scale.setScalar(.25 + Math.random() * .3); s.position.copy(at); parts.push({ s, v: new THREE.Vector3((Math.random() - .5) * 6, Math.random() * 5, (Math.random() - .5) * 6) }); }
    tween(650, k => { for (const p of parts) { p.s.position.addScaledVector(p.v, 1 / 60); p.v.y -= .12; p.s.material.opacity = 1 - k; } if (k >= 1) for (const p of parts) drop(p.s); });
  }
  function flashGlow(at, color, size, ms) { // a short bloom of light: the impact "lights up" the field without adding real lights (no shader recompiles)
    const s = orb(color, false); s.position.copy(at); tween(ms, k => { s.scale.setScalar(size * (.6 + k * .8)); s.material.opacity = (1 - k) * (1 - k); if (k >= 1) drop(s); });
  }
  function trail(from, to, color, n = 6) { for (let i = 0; i < n; i++) { const s = orb(color, false), p = from.clone().lerp(to, i / n); s.position.copy(p); s.scale.setScalar(.35); tween(360 + i * 30, k => { s.material.opacity = (1 - k) * .8; s.scale.setScalar(.35 * (1 - k * .6)); if (k >= 1) drop(s); }); } }
  function guardBubble(side, on) {
    const m = state?.mon[side]; if (!m) return; let b = state.bubble[side];
    if (on && !b) { b = state.bubble[side] = new THREE.Mesh(new THREE.SphereGeometry(1, 28, 18), new THREE.MeshBasicMaterial({ color: new THREE.Color(TC[B.active(side).type] || '#9fd').lerp(new THREE.Color('#fff'), .4), transparent: true, opacity: .16, blending: THREE.AdditiveBlending, depthWrite: false }));
      const sz = m.size || { w: 1, h: 1.5 }; b.scale.set(Math.max(.9, sz.w * .8), sz.h * .72, Math.max(.9, sz.w * .8)); b.position.copy(m.group.position); b.position.y += sz.h * .5; scene.add(b);
      const s0 = b.scale.clone(); tween(260, k => b.scale.copy(s0).multiplyScalar(.6 + ease(k) * .4)); }
    else if (!on && b) { state.bubble[side] = null; tween(220, k => { b.material.opacity = .16 * (1 - k); if (k >= 1) { scene.remove(b); b.geometry.dispose(); b.material.dispose(); } }); }
  }
  let emitT = 0;
  function statusFx(dt) { // burning creatures shed embers, paralysed ones crackle
    emitT -= dt; if (emitT > 0 || !state || !B) return; emitT = .11;
    for (const s of ['p', 'e']) { const f = B.active(s), m = state.mon[s]; if (!f?.status || !m?.group.visible || f.hp <= 0) continue;
      const h = m.size?.h || 1.4, p = m.group.position.clone().add(new THREE.Vector3((Math.random() - .5) * .9, Math.random() * h, (Math.random() - .5) * .5));
      const o = orb(f.status === 'burn' ? '#ff7a2a' : '#ffe94a', false); o.position.copy(p); o.scale.setScalar(f.status === 'burn' ? .28 : .2);
      const v = f.status === 'burn' ? new THREE.Vector3(0, 1.2, 0) : new THREE.Vector3((Math.random() - .5) * 3, (Math.random() - .5) * 3, 0);
      tween(f.status === 'burn' ? 700 : 180, k => { o.position.addScaledVector(v, 1 / 60); o.material.opacity = 1 - k; if (k >= 1) drop(o); }); }
  }
  let freeze = 0; const hitStop = s => { freeze = Math.max(freeze, s); };

  async function strike(e) {
    const s = e.side, o = s === 'p' ? 'e' : 'p', att = state.mon[s], def = state.mon[o], big = e.kind === 'ult', ranged = e.kind !== 'attack', col = TC[e.type] || '#fff';
    acting(s); banner(s === 'p' ? 'Your turn' : 'Foe\'s turn', s === 'p' ? B.active(s).name : (state.spec.name ? state.spec.name + '\'s ' : '') + B.active(s).name, s);
    log(`${s === 'p' ? 'Your' : 'The foe\'s'} <b>${esc(B.active(s).name)}</b> used <b style="color:${col}">${esc(e.move)}</b>`);
    const A0 = att.group.position.clone(), D0 = def.group.position.clone(), dir = D0.clone().sub(A0).setY(0).normalize(), sc0 = att.group.scale.clone();
    // 1 · anticipation: the camera settles behind the attacker, it gathers itself (squash), its ring flares with type light
    if (ranged) { shot = { mode: 'over', a: A0, b: D0 }; cutIn(e.move, e.type, big); }
    state.ring[s].flare = 1; hooks.sfx?.(ranged ? 'charge' : 'whoosh', big ? .9 : .35);
    const gather = orb(col, false); gather.position.copy(A0).setY(A0.y + 1);
    await tween(ranged ? (big ? 720 : 480) : 220, k => { att.group.scale.set(sc0.x * (1 + .12 * Math.sin(k * Math.PI)), sc0.y * (1 - .16 * Math.sin(k * Math.PI)), sc0.z); att.group.position.copy(A0).addScaledVector(dir, -.25 * Math.sin(k * Math.PI * .5));
      gather.scale.setScalar((big ? 1.8 : 1) * ease(k)); gather.material.opacity = .8 * k; });
    drop(gather); att.group.scale.copy(sc0);
    // 2 · execution
    if (ranged) {
      await tween(big ? 220 : 160, k => { att.group.position.copy(A0).addScaledVector(dir, -.25 + .55 * ease(k)); att.group.position.y = A0.y + Math.sin(k * Math.PI) * (big ? .5 : .25); });
      const ob = orb(col, big), from = A0.clone().setY(A0.y + 1), to = D0.clone().setY(D0.y + 1);
      shot = null; hooks.sfx?.('whoosh', big ? .6 : .3);
      await tween(big ? 380 : 300, k => { ob.position.lerpVectors(from, to, ease(k)); ob.position.y += Math.sin(k * Math.PI) * 1.1; ob.scale.setScalar((big ? 1.7 : 1) * (1 + k * .5)); });
      trail(from, to, col, big ? 9 : 5); drop(ob);
    } else {
      await tween(170, k => att.group.position.copy(A0).addScaledVector(dir, -.25 + (A0.distanceTo(D0) - 1.25) * ease(k)));
    }
    // 3 · impact: freeze-frame, light bloom, type-coloured burst, knockback, numbers
    const at = D0.clone().setY(D0.y + 1);
    shot = { mode: 'impact', b: D0 }; hitStop(big ? .16 : e.crit ? .12 : .07);
    hooks.sfx?.('hit'); hooks.sfx?.(TYPE_SFX[e.type] || 'thud', big ? .8 : .4);
    shake = big ? .55 : e.crit ? .38 : .2; burst(at, col, big || e.crit); flashGlow(at, col, big ? 7 : e.crit ? 5 : 3.2, big ? 520 : 340);
    def.setFlash?.(1); setTimeout(() => def.setFlash?.(0), big ? 160 : 110);
    if (big || e.crit) impactFrame(ui);
    const sp = screenOf(def.group, 2.2); onomato(ui.querySelector('#fbFx'), sp.x, sp.y - 30, e.kind === 'attack' ? 'Fighting' : e.type, { big, crit: e.crit });
    e._apply?.(); floatText(def.group, '−' + e.d, 'dmg' + (e.crit ? ' crit' : '') + (o === 'p' ? ' hurt' : ''));
    if (e.guarded) setTimeout(() => floatText(def.group, 'Guarded', 'lbl up'), 120);
    if (e.cling) setTimeout(() => floatText(def.group, 'Hanging on!', 'lbl weak'), 360);
    if (e.eff) setTimeout(() => floatText(def.group, 'Super effective!', 'lbl eff'), 180); else if (e.weak) setTimeout(() => floatText(def.group, 'Not very effective', 'lbl weak'), 180);
    const kb = dir.clone().multiplyScalar(big ? .9 : .45);
    tween(420, k => def.group.position.copy(D0).addScaledVector(kb, Math.sin(k * Math.PI)));
    plate('p'); plate('e');
    // 4 · recovery: hold on the hit for a beat, then everyone settles back and the camera pulls out
    await wait(big ? 380 : 220); shot = null;
    const from = att.group.position.clone(); await tween(380, k => att.group.position.lerpVectors(from, A0, ease(k)));
    att.group.position.copy(A0); att.group.rotation.z = 0; def.group.position.copy(D0); await wait(240);
  }
  async function knockOut(side) {
    const m = state.mon[side]; acting(side); log(`${side === 'p' ? 'Your' : 'The foe\'s'} <b>${esc(B.active(side).name)}</b> fainted!`); hooks.sfx?.('ko');
    guardBubble(side, false); hitStop(.1); m.setFlash?.(1);
    const p0 = m.group.position.clone(); await tween(800, k => { m.group.rotation.x = -ease(k) * 1.4; m.group.position.y = p0.y - k * .4; m.group.scale.setScalar(1 - k * .6); m.setFlash?.(Math.max(0, 1 - k * 3)); });
    m.group.visible = false; m.group.rotation.x = 0; state.ring[side].on = 0; await wait(250);
  }
  async function sendOut(side, idx) {
    const old = state.mon[side]; if (old && old !== state.wildMon) { scene.remove(old.group); old.dispose?.(); } else if (old) old.group.visible = false;
    const spot = side === 'p' ? state.a : state.b; const f = B[side].team[idx];
    const m = creature(f, spot, { echo: side === 'e' && state.spec.kind === 'wild' ? .28 : 0 }); state.mon[side] = m; state.own.push(m);
    setRingColor(state.ring[side], TC[f.type] || '#fff'); acting(side); state.ring[side].flare = 1; flashGlow(spot.clone().setY(spot.y + .8), TC[f.type] || '#fff', 3, 420); hooks.sfx?.('pop', .5);
    m.group.scale.setScalar(.01); await tween(420, k => m.group.scale.setScalar(Math.max(.01, 1 + Math.sin(k * Math.PI) * .12 * (1 - k) + (ease(k) - 1))));
    m.group.scale.setScalar(1);
    log(`${side === 'p' ? 'Go' : esc(state.spec.name || 'Foe') + ' sends out'} <b>${esc(f.name)}</b>!`); plate(side); await wait(200);
  }
  async function act(a) {
    if (busy || B.over) return; busy = true; phase(false); moves();
    // the whole round is resolved up front; the plates must only show what the animation has reached so far —
    // otherwise your own HP dropped the moment YOU attacked (it already contained the foe's reply)
    const all = [...B.p.team, ...B.e.team]; for (const f of all) { f._hp = f.hp; f._en = f.energy; }
    const ev = B.round(a);
    for (const e of ev) {
      if (!ui) return;
      if (e.t === 'hit') { const att = B.active(e.side), def = B.active(e.side === 'p' ? 'e' : 'p'); att._en = att.energy;
        e._apply = () => { def._hp = Math.max(def.minHp || 0, (def._hp ?? def.hp) - e.d); }; await strike(e); }
      else if (e.t === 'ko') await knockOut(e.side);
      else if (e.t === 'switch') await sendOut(e.side, e.to);
      else if (e.t === 'guard') { const gf = B.active(e.side); gf._en = gf.energy; acting(e.side); guardBubble(e.side, true); floatText(state.mon[e.side].group, 'Guard', 'lbl up'); hooks.sfx?.('clink', .4); await wait(420); }
      else if (e.t === 'status') { flashGlow(state.mon[e.side].group.position.clone().setY(state.mon[e.side].group.position.y + 1), e.st === 'burn' ? '#ff7a2a' : '#ffe94a', 3, 400); floatText(state.mon[e.side].group, e.st === 'burn' ? 'Burned!' : 'Paralyzed!', 'lbl ' + e.st); await wait(500); }
      else if (e.t === 'para') { acting(e.side); floatText(state.mon[e.side].group, 'Can\'t move!', 'lbl para'); hooks.sfx?.('zap', .3); await wait(650); }
      else if (e.t === 'burn') { const bf = B.active(e.side); bf._hp = Math.max(bf.minHp || 0, (bf._hp ?? bf.hp) - e.d); acting(e.side); state.mon[e.side].setFlash?.(.6); setTimeout(() => state?.mon[e.side]?.setFlash?.(0), 120); floatText(state.mon[e.side].group, '−' + e.d, 'dmg burn'); hooks.sfx?.('flame', .3); await wait(520); }
      else if (e.t === 'cure') { floatText(state.mon[e.side].group, e.st === 'burn' ? 'Burn faded' : 'Can move again', 'lbl up'); await wait(300); }
      else if (e.t === 'heal') { const hf = B.active(e.side); hf._hp = Math.min(hf.maxHp, (hf._hp ?? hf.hp) + e.n); flashGlow(state.mon[e.side].group.position.clone().setY(state.mon[e.side].group.position.y + 1), '#7fe3a2', 2.6, 380); floatText(state.mon[e.side].group, '+' + e.n, 'heal'); await wait(320); }
      else if (e.t === 'debuff' || e.t === 'buff') { floatText(state.mon[e.side].group, e.stat + (e.t === 'buff' ? ' ↑' : ' ↓'), 'lbl ' + (e.t === 'buff' ? 'up' : 'dn')); await wait(320); }
      else if (e.t === 'end') { await wait(450); return finish(e.result); }
      plate('p'); plate('e');
    }
    for (const f of all) { f._hp = f.hp; f._en = f.energy; } // end of the round: plates catch up with the real state
    guardBubble('p', false); guardBubble('e', false); acting(null);
    busy = false; if (ui) { plate('p'); plate('e'); moves(); captureHint(); phase(true); }
  }
  async function capture() {
    if (busy) return; busy = true; phase(false); moves(); acting('p');
    const foe = B.active('e'), m = state.mon.e, ch = captureChance(foe);
    log(`You throw a blank Lattice card!`); hooks.sfx?.('whoosh', .5);
    const card = new THREE.Mesh(new THREE.PlaneGeometry(.5, .7), new THREE.MeshBasicMaterial({ color: new THREE.Color('#ffd257').multiplyScalar(1.8), side: THREE.DoubleSide }));
    scene.add(card); const from = state.a.clone().setY(state.a.y + 1.4), to = m.group.position.clone().setY(m.group.position.y + 1.2);
    await tween(520, k => { card.position.lerpVectors(from, to, ease(k)); card.position.y += Math.sin(k * Math.PI) * 1.8; card.rotation.set(k * 8, k * 6, 0); });
    hitStop(.08); flashGlow(to, '#ffd257', 3.5, 420); await tween(360, k => { m.group.scale.setScalar(1 - k * .98); m.setFlash?.(k); });
    const shakes = Math.random() < ch ? 3 : Math.min(2, Math.floor(Math.random() * 3));
    for (let i = 0; i < shakes; i++) { hooks.sfx?.('tick'); await tween(420, k => { card.rotation.z = Math.sin(k * Math.PI * 2) * .5; card.position.y = to.y - .6 + Math.abs(Math.sin(k * Math.PI)) * .1; }); await wait(180); }
    if (shakes === 3) {
      hooks.sfx?.('win'); burst(to, '#ffd257', true); scene.remove(card); card.geometry.dispose(); card.material.dispose();
      const isNew = C.addCard(foe.card); log(`Gotcha! <b>${esc(foe.name)}</b> was captured!`); floatText(m.group, 'CAPTURED!', 'lbl eff');
      const S = C.S; if ((S.team || []).length < 3 && !S.team.includes(foe.card.i)) { S.team.push(foe.card.i); C.save(); }
      await wait(900); return finish('caught', { card: foe.card, isNew });
    }
    hooks.sfx?.('ko'); log(`Oh no! It broke free!`); await tween(300, k => { m.group.scale.setScalar(.02 + k * .98); m.setFlash?.(1 - k); }); scene.remove(card); card.geometry.dispose(); card.material.dispose();
    busy = false; await act({ kind: 'guard' });
  }
  async function run() { if (busy) return; busy = true; log('Got away safely!'); await wait(500); finish('fled'); }

  async function finish(result, extra = {}) {
    const spec = state.spec, T = spec.npc?.trainer;
    if (result === 'win') {
      const xp = spec.kind === 'wild' ? 14 + QS.Q().ch * 3 : 40 + QS.Q().ch * 18, coins = spec.kind === 'wild' ? 10 : Math.round(80 + QS.Q().ch * 45 * (T?.lvl || 1));
      C.addCoins(coins); hooks.xp?.(xp); C.S.battle.wins++; C.save();
      const nid = spec.npc?.id, rp = spec.kind === 'wild' ? RK.RP.wild : ['maren', 'mira', 'sable', 'orin', 'vera', 'dom', 'lyra', 'kest'].includes(nid) ? RK.RP.warden : nid === 'rho' || nid === 'kai' ? RK.RP.rival : RK.RP.trainer(T?.lvl || 1);
      RK.add(rp, spec.kind === 'wild' ? 'Wild Echo' : spec.name || 'Trainer');
      hooks.toast?.(`${spec.kind === 'wild' ? 'The wild ' + esc(spec.wild.card.n) + ' faded back into the grass.' : 'You beat ' + esc(spec.name) + '!'} <span class="gold">+${coins} coins · +${xp} XP · +${rp} RP</span>`);
    } else if (result === 'caught') { hooks.xp?.(20); RK.add(RK.RP.capture, 'Capture'); hooks.toast?.(`<b>${esc(extra.card.n)}</b> joined your collection${extra.isNew ? ' <em class="gold">NEW</em>' : ''}. ${C.S.team.includes(extra.card.i) ? 'It joined your team!' : ''}`); }
    else if (result === 'lose') { C.S.battle.losses++; C.save(); RK.add(RK.RP.lose, 'Defeat'); hooks.toast?.('Your team fainted… you blacked out and woke up in the last town.'); }
    await cleanup(result === 'lose');
    const r = { result, ...extra }; const fn = resolveFn; resolveFn = null; fn?.(r);
  }
  async function cleanup(lost) {
    hooks.music?.(null); restoreCorridors(state.cleared); removeEventListener('keydown', onKey, true); document.body.classList.remove('in-battle'); ctx.arena?.(0, 0, 1, 0); shot = null; freeze = 0; lookS.set(0, 0, 0);
    for (const s of ['p', 'e']) { const rg = state.ring?.[s]; if (rg) { scene.remove(rg.g); rg.g.traverse(o => { o.geometry?.dispose(); o.material?.dispose(); }); } guardBubble(s, false); }
    ui?.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 300 }).finished.catch(() => {}).then(() => { ui?.remove(); ui = null; });
    for (const m of state.own) { scene.remove(m.group); m.dispose?.(); }
    if (state.wildMon) { state.wildMon.group.visible = true; state.wildMon.group.scale.setScalar(1); state.wildMon.group.rotation.x = 0; state.wildMon.setFlash?.(0); state.wildMon.group.position.copy(state.wildHome); }
    const pet = ctx.pet(); if (pet) { pet.group.visible = true; }
    ctx.setCam(null); if (lost) ctx.respawn();
    state = null; B = null; busy = false;
  }

  return {
    get active() { return !!state; },
    async start(spec) {
      const mine = myTeam(); if (!mine.length) { hooks.toast?.('You have no Pokémon cards yet — Dr. Vale in Lumen Harbor can help.'); return { result: 'none' }; }
      let enemy;
      if (spec.kind === 'wild') enemy = [fighter(DB.cards[spec.wild.card.i], .8 + Math.max(QS.Q().ch, QS.tierAt(spec.wild.x, spec.wild.z)) * .05 + QS.dangerAt(spec.wild.x, spec.wild.z) * .09 + Math.random() * .08)];
      if (spec.kind === 'wild' && storyCapture(spec.wild.card)) enemy[0].minHp = 1; // a story capture can't be wasted by knocking the Echo out
      else if (spec.mirror) enemy = mine.map(f => fighter(f.card, 1.08)); // GLYPH copies your team: a little stronger, beatable with Guard, switching and type play
      else enemy = trainerTeam(spec.npc.key, spec.npc.trainer);
      if (!enemy.length) return { result: 'none' };
      B = new Battle(mine, enemy);
      const st = setupStage(spec); state = { ...st, spec, mon: {}, own: [], wildMon: null, wildHome: null, bubble: {}, ring: { p: ring(st.a, TC[B.active('p').type] || '#fff'), e: ring(st.b, TC[B.active('e').type] || '#fff') } };
      if (spec.kind === 'wild') { const w = spec.wild; state.wildMon = w.shell; state.wildHome = w.g.position.clone(); w.g.position.copy(st.b); state.mon.e = w.shell; w.shell.setEcho(0); }
      camK = 0; ctx.setCam(battleCam); buildUI(spec); hooks.sfx?.('charge', .6); hooks.music?.('battle');
      if (spec.kind !== 'wild') { state.mon.e = creature(B.active('e'), st.b); state.own.push(state.mon.e); }
      state.mon.p = creature(B.active('p'), st.a); state.own.push(state.mon.p);
      for (const m of [state.mon.p, spec.kind !== 'wild' ? state.mon.e : null]) if (m) { m.group.scale.setScalar(.01); tween(420, k => m.group.scale.setScalar(Math.max(.01, ease(k)))); }
      plate('p'); plate('e'); moves(); log(spec.kind === 'wild' ? `A wild <b>${esc(spec.wild.card.n)}</b> Echo appeared!` : `<b>${esc(spec.name)}</b> challenges you!`);
      ui.classList.add('choose'); setTimeout(() => { if (ui && !busy && state) phase(true); }, 1700);
      return new Promise(res => { resolveFn = res; });
    },
    update(dt, t) {
      if (freeze > 0) { freeze -= dt; dt = 0; } // hit-stop: the whole fight holds its breath on impact
      for (let i = tweens.length - 1; i >= 0; i--) { const w = tweens[i]; w.t += dt * 1000 * FAST(); const k = Math.min(1, w.t / w.ms); w.fn(k); if (k >= 1) { tweens.splice(i, 1); w.res(); } }
      if (!state) return;
      for (const s of ['p', 'e']) { const m = state.mon[s]; if (m && m.group.visible) m.update(dt, 0, t, camera);
        const rg = state.ring?.[s]; if (rg) { rg.flare = Math.max(0, rg.flare - dt * 1.6); const pulse = rg.on ? .55 + .25 * Math.sin(t * 5) : .22;
          rg.r.material.opacity = Math.min(1, pulse + rg.flare * .8) * (m?.group.visible ? 1 : .3); rg.d.material.opacity = (rg.on ? .14 : .05) + rg.flare * .35; rg.g.scale.setScalar(1 + rg.flare * .25); } }
      statusFx(dt);
    },
  };
}
