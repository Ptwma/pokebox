// Pokebox — battles that happen right where you are in the open world (Pokémon style).
// Your lead card's creature steps out next to you, the opponent's creature faces it, the camera swings to the side,
// and the fight plays out with the battle.js rules (types, energy, signature moves, ultimates, guard, switching).
// Wild Echoes can be CAPTURED once weakened: the blank Lattice card flies out and shakes 1-3 times.
import * as C from './core.js';
import { DB, isMon } from './core.js';
import { Battle, fighter, SIG, MOVES, ENERGY_MAX, estimate, mult } from './battle.js';
import { onomato, impactFrame, TYPE_COL as TC } from './comicfx.js';
import { cardImg } from './core.js';
import * as QS from './quests.js';

const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const wait = ms => new Promise(r => setTimeout(r, ms));
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
  function setupStage(spec) {
    const pl = ctx.player(), P0 = pl.group.position.clone();
    let foe = spec.wild ? new THREE.Vector3(spec.wild.x, 0, spec.wild.z) : new THREE.Vector3(spec.npc.x, 0, spec.npc.z);
    const D = foe.clone().sub(P0).setY(0); if (D.lengthSq() < .01) D.set(0, 0, 1); D.normalize();
    const side = new THREE.Vector3(-D.z, 0, D.x);
    const a = P0.clone().addScaledVector(D, 2.4).addScaledVector(side, -.6), b = P0.clone().addScaledVector(D, 8.6).addScaledVector(side, .4);
    a.y = H(a.x, a.z); b.y = H(b.x, b.z);
    pl.group.rotation.y = Math.atan2(D.x, D.z);
    const pet = ctx.pet(); if (pet) pet.group.visible = false;
    return { P0, D, side, a, b, center: a.clone().lerp(b, .5) };
  }
  let shake = 0, camK = 0, focus = null;
  function battleCam(cam, dt) {
    const st = state; if (!st) return; camK = Math.min(1, camK + dt * 1.6);
    const c = st.center, want = tmp.copy(c).addScaledVector(st.side, 8.2).addScaledVector(st.D, -3.2); want.y = Math.max(c.y + 3.4, H(want.x, want.z) + 1.5);
    if (focus) want.lerp(tmp.clone().copy(focus).addScaledVector(st.side, 5).setY(focus.y + 2.2), .35);
    cam.position.lerp(want, Math.min(1, dt * (camK < 1 ? 2.5 : 4)));
    if (shake > 0) { cam.position.x += (Math.random() - .5) * shake; cam.position.y += (Math.random() - .5) * shake * .6; shake = Math.max(0, shake - dt * 2.2); }
    cam.lookAt(c.x, c.y + 1.1, c.z);
  }

  /* ---------- UI */
  function buildUI(spec) {
    ui = document.createElement('div'); ui.className = 'fb-ui';
    ui.innerHTML = `<div class="fb-plate e" id="fbE"></div><div class="fb-plate p" id="fbP"></div>
      <div class="fb-log" id="fbLog"></div><div class="fb-moves" id="fbMoves"></div><div class="fb-fx" id="fbFx"></div>
      <div class="fb-title">${spec.kind === 'wild' ? 'Wild ' + esc(spec.wild.card.n) + ' appeared!' : esc(spec.name) + ' wants to battle!'}</div>`;
    (document.getElementById('worldWrap') || document.body).append(ui);
    ui.querySelector('.fb-title').animate([{ transform: 'translate(-50%,-30px) scale(.8)', opacity: 0 }, { transform: 'translate(-50%,0) scale(1)', opacity: 1, offset: .2 }, { opacity: 1, offset: .8 }, { opacity: 0 }], { duration: 2200, fill: 'forwards' });
  }
  function plate(side) {
    const f = B.active(side), el = ui.querySelector(side === 'e' ? '#fbE' : '#fbP'), hp = Math.max(0, f.hp), pct = hp / f.maxHp * 100;
    const team = B[side].team.map((x, i) => `<i class="${x.hp <= 0 ? 'down' : ''} ${i === B[side].act ? 'on' : ''}"></i>`).join('');
    el.style.setProperty('--tc', TC[f.type] || '#ccc');
    el.innerHTML = `<div class="fb-top"><b>${esc(f.name)}</b><span class="fb-type">${esc(f.type)}</span><span class="fb-r">${RN[f.card.r] || ''}</span>${f.status ? `<span class="fb-st">${f.status === 'burn' ? 'BRN' : 'PAR'}</span>` : ''}</div>
      <div class="fb-hp"><i style="width:${pct}%" class="${pct < 30 ? 'low' : pct < 55 ? 'mid' : ''}"></i></div>
      <div class="fb-bot"><small>${hp} / ${f.maxHp} HP</small><span class="fb-en">${Array.from({ length: ENERGY_MAX }, (_, i) => `<i class="${i < f.energy ? 'on' : ''}"></i>`).join('')}</span><span class="fb-team">${team}</span></div>`;
  }
  function log(html) { const l = ui.querySelector('#fbLog'); const p = document.createElement('p'); p.innerHTML = html; l.append(p); while (l.children.length > 3) l.firstChild.remove(); }
  function moves() {
    const box = ui.querySelector('#fbMoves'), me = B.active('p'), foe = B.active('e'), sig = SIG[me.type] || SIG.Colorless, wild = state.spec.kind === 'wild';
    const btn = (k, label, sub, cls = '') => `<button class="mv lg ${cls}" data-m="${k}" type="button" ${B.canUse(me, k) && !busy ? '' : 'disabled'} style="--tc:${TC[me.type] || '#ccc'}"><b>${label}</b><small>${sub}</small></button>`;
    const chance = Math.round(captureChance(foe) * 100);
    box.innerHTML = btn('attack', 'Attack', `≈${estimate(me, foe, 'attack')} · +1⚡`) + btn('sig', sig.name, `≈${estimate(me, foe, 'sig')} · ⚡${MOVES.sig.cost}`, 'sig') + btn('ult', 'Ultimate', `≈${estimate(me, foe, 'ult')} · ⚡${MOVES.ult.cost}`, 'ult') + btn('guard', 'Guard', '−55% dmg · +1⚡', 'guard')
      + B.p.team.map((f, i) => i !== B.p.act && f.hp > 0 ? `<button class="mv lg sw" data-sw="${i}" type="button" ${busy ? 'disabled' : ''}><b>Switch</b><small>${esc(f.name)}</small></button>` : '').join('')
      + (wild ? `<button class="mv lg cap" data-cap type="button" ${busy ? 'disabled' : ''}><b>Capture</b><small>${chance}% chance</small></button><button class="mv lg run" data-run type="button" ${busy ? 'disabled' : ''}><b>Run</b><small>escape</small></button>` : '');
    box.querySelectorAll('[data-m]').forEach(x => x.onclick = () => act({ kind: x.dataset.m }));
    box.querySelectorAll('[data-sw]').forEach(x => x.onclick = () => act({ kind: 'switch', to: +x.dataset.sw }));
    box.querySelector('[data-cap]')?.addEventListener('click', capture); box.querySelector('[data-run]')?.addEventListener('click', run);
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
  function burst(at, color, big) {
    const n = big ? 26 : 14, parts = [];
    for (let i = 0; i < n; i++) { const s = orb(color, false); s.scale.setScalar(.25 + Math.random() * .3); s.position.copy(at); parts.push({ s, v: new THREE.Vector3((Math.random() - .5) * 6, Math.random() * 5, (Math.random() - .5) * 6) }); }
    tween(650, k => { for (const p of parts) { p.s.position.addScaledVector(p.v, 1 / 60); p.v.y -= .12; p.s.material.opacity = 1 - k; } if (k >= 1) for (const p of parts) { scene.remove(p.s); p.s.material.dispose(); } });
  }
  async function strike(e) {
    const s = e.side, o = s === 'p' ? 'e' : 'p', att = state.mon[s], def = state.mon[o], big = e.kind === 'ult', ranged = e.kind !== 'attack';
    log(`${s === 'p' ? 'Your' : 'The foe\'s'} <b>${esc(B.active(s).name)}</b> used <b style="color:${TC[e.type]}">${esc(e.move)}</b>`);
    const A0 = att.group.position.clone(), D0 = def.group.position.clone(), dir = D0.clone().sub(A0).setY(0).normalize();
    focus = A0; hooks.sfx?.(ranged ? (big ? 'charge' : 'whoosh') : 'whoosh', big ? .9 : .3);
    if (ranged) {
      await tween(big ? 650 : 300, k => { att.group.position.y = A0.y + Math.sin(k * Math.PI) * (big ? .9 : .4); att.group.rotation.z = Math.sin(k * 20) * .04 * k; });
      const ob = orb(TC[e.type] || '#fff', big), from = A0.clone().setY(A0.y + 1), to = D0.clone().setY(D0.y + 1);
      await tween(big ? 420 : 320, k => { ob.position.lerpVectors(from, to, ease(k)); ob.position.y += Math.sin(k * Math.PI) * 1.2; ob.scale.setScalar((big ? 1.6 : 1) * (1 + k * .5)); });
      scene.remove(ob); ob.material.dispose();
    } else {
      await tween(180, k => att.group.position.copy(A0).addScaledVector(dir, -.4 * k));
      await tween(160, k => att.group.position.copy(A0).addScaledVector(dir, -.4 + (A0.distanceTo(D0) - 1.4) * ease(k)));
    }
    focus = D0; hooks.sfx?.('hit'); shake = big ? .5 : e.crit ? .35 : .18; burst(D0.clone().setY(D0.y + 1), TC[e.type] || '#fff', big || e.crit);
    def.setFlash?.(1); setTimeout(() => def.setFlash?.(0), 110);
    if (big || e.crit) impactFrame(ui);
    const sp = screenOf(def.group, 2.2); onomato(ui.querySelector('#fbFx'), sp.x, sp.y - 30, e.kind === 'attack' ? 'Fighting' : e.type, { big, crit: e.crit });
    floatText(def.group, '−' + e.d, 'dmg' + (e.crit ? ' crit' : ''));
    if (e.cling) setTimeout(() => floatText(def.group, 'Hanging on!', 'lbl weak'), 360);
    if (e.eff) setTimeout(() => floatText(def.group, 'Super effective!', 'lbl eff'), 180); else if (e.weak) setTimeout(() => floatText(def.group, 'Not very effective', 'lbl weak'), 180);
    const kb = dir.clone().multiplyScalar(big ? .9 : .45);
    tween(420, k => def.group.position.copy(D0).addScaledVector(kb, Math.sin(k * Math.PI)));
    await tween(360, k => att.group.position.lerp(A0, k));
    att.group.position.copy(A0); att.group.rotation.z = 0; plate('p'); plate('e'); await wait(360); focus = null;
  }
  async function knockOut(side) {
    const m = state.mon[side]; log(`${side === 'p' ? 'Your' : 'The foe\'s'} <b>${esc(B.active(side).name)}</b> fainted!`); hooks.sfx?.('ko');
    const p0 = m.group.position.clone(); await tween(700, k => { m.group.rotation.x = -k * 1.4; m.group.position.y = p0.y - k * .4; m.group.scale.setScalar(1 - k * .6); });
    m.group.visible = false;
  }
  async function sendOut(side, idx) {
    const old = state.mon[side]; if (old && old !== state.wildMon) { scene.remove(old.group); old.dispose?.(); } else if (old) old.group.visible = false;
    const spot = side === 'p' ? state.a : state.b; const f = B[side].team[idx];
    const m = creature(f, spot, { echo: side === 'e' && state.spec.kind === 'wild' ? .28 : 0 }); state.mon[side] = m; state.own.push(m);
    m.group.scale.setScalar(.01); await tween(380, k => m.group.scale.setScalar(Math.max(.01, ease(k))));
    log(`${side === 'p' ? 'Go' : esc(state.spec.name || 'Foe') + ' sends out'} <b>${esc(f.name)}</b>!`); plate(side);
  }
  async function act(a) {
    if (busy || B.over) return; busy = true; moves();
    const ev = B.round(a);
    for (const e of ev) {
      if (e.t === 'hit') await strike(e);
      else if (e.t === 'ko') await knockOut(e.side);
      else if (e.t === 'switch') await sendOut(e.side, e.to);
      else if (e.t === 'guard') { floatText(state.mon[e.side].group, 'Guard', 'lbl up'); await wait(300); }
      else if (e.t === 'status') { floatText(state.mon[e.side].group, e.st === 'burn' ? 'Burned!' : 'Paralyzed!', 'lbl ' + e.st); await wait(400); }
      else if (e.t === 'para') { floatText(state.mon[e.side].group, 'Can\'t move!', 'lbl para'); await wait(500); }
      else if (e.t === 'burn') { floatText(state.mon[e.side].group, '−' + e.d, 'dmg burn'); await wait(400); }
      else if (e.t === 'heal') { floatText(state.mon[e.side].group, '+' + e.n, 'heal'); await wait(300); }
      else if (e.t === 'debuff' || e.t === 'buff') { floatText(state.mon[e.side].group, e.stat + (e.t === 'buff' ? ' ↑' : ' ↓'), 'lbl ' + (e.t === 'buff' ? 'up' : 'dn')); await wait(300); }
      else if (e.t === 'end') { await wait(400); return finish(e.result); }
      plate('p'); plate('e');
    }
    busy = false; if (ui) { moves(); captureHint(); }
  }
  async function capture() {
    if (busy) return; busy = true; moves();
    const foe = B.active('e'), m = state.mon.e, ch = captureChance(foe);
    log(`You throw a blank Lattice card!`); hooks.sfx?.('whoosh', .5);
    const card = new THREE.Mesh(new THREE.PlaneGeometry(.5, .7), new THREE.MeshBasicMaterial({ color: new THREE.Color('#ffd257').multiplyScalar(1.8), side: THREE.DoubleSide }));
    scene.add(card); const from = state.a.clone().setY(state.a.y + 1.4), to = m.group.position.clone().setY(m.group.position.y + 1.2);
    await tween(520, k => { card.position.lerpVectors(from, to, ease(k)); card.position.y += Math.sin(k * Math.PI) * 1.8; card.rotation.set(k * 8, k * 6, 0); });
    await tween(360, k => { m.group.scale.setScalar(1 - k * .98); m.setFlash?.(k); });
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
      hooks.toast?.(`${spec.kind === 'wild' ? 'The wild ' + esc(spec.wild.card.n) + ' faded back into the grass.' : 'You beat ' + esc(spec.name) + '!'} <span class="gold">+${coins} coins · +${xp} XP</span>`);
    } else if (result === 'caught') { hooks.xp?.(20); hooks.toast?.(`<b>${esc(extra.card.n)}</b> joined your collection${extra.isNew ? ' <em class="gold">NEW</em>' : ''}. ${C.S.team.includes(extra.card.i) ? 'It joined your team!' : ''}`); }
    else if (result === 'lose') { C.S.battle.losses++; C.save(); hooks.toast?.('Your team fainted… you blacked out and woke up in the last town.'); }
    await cleanup(result === 'lose');
    const r = { result, ...extra }; const fn = resolveFn; resolveFn = null; fn?.(r);
  }
  async function cleanup(lost) {
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
      if (spec.kind === 'wild') enemy = [fighter(DB.cards[spec.wild.card.i], .8 + QS.Q().ch * .05 + Math.random() * .08)];
      if (spec.kind === 'wild' && storyCapture(spec.wild.card)) enemy[0].minHp = 1; // a story capture can't be wasted by knocking the Echo out
      else if (spec.mirror) enemy = mine.map(f => fighter(f.card, 1.15));
      else enemy = trainerTeam(spec.npc.key, spec.npc.trainer);
      if (!enemy.length) return { result: 'none' };
      B = new Battle(mine, enemy);
      const st = setupStage(spec); state = { ...st, spec, mon: {}, own: [], wildMon: null, wildHome: null };
      if (spec.kind === 'wild') { const w = spec.wild; state.wildMon = w.shell; state.wildHome = w.g.position.clone(); w.g.position.copy(st.b); state.mon.e = w.shell; w.shell.setEcho(0); }
      camK = 0; ctx.setCam(battleCam); buildUI(spec); hooks.sfx?.('charge', .6);
      if (spec.kind !== 'wild') { state.mon.e = creature(B.active('e'), st.b); state.own.push(state.mon.e); }
      state.mon.p = creature(B.active('p'), st.a); state.own.push(state.mon.p);
      for (const m of [state.mon.p, spec.kind !== 'wild' ? state.mon.e : null]) if (m) { m.group.scale.setScalar(.01); tween(420, k => m.group.scale.setScalar(Math.max(.01, ease(k)))); }
      plate('p'); plate('e'); moves(); log(spec.kind === 'wild' ? `A wild <b>${esc(spec.wild.card.n)}</b> Echo appeared!` : `<b>${esc(spec.name)}</b> challenges you!`);
      return new Promise(res => { resolveFn = res; });
    },
    update(dt, t) {
      for (let i = tweens.length - 1; i >= 0; i--) { const w = tweens[i]; w.t += dt * 1000; const k = Math.min(1, w.t / w.ms); w.fn(k); if (k >= 1) { tweens.splice(i, 1); w.res(); } }
      if (!state) return;
      for (const s of ['p', 'e']) { const m = state.mon[s]; if (m && m.group.visible) m.update(dt, 0, t, camera); }
    },
  };
}
