// Pokebox — game shell: home, shop, binder, collection, market, battle, profile
import * as C from './core.js';
import * as SIDE from './side.js';
import { DB, S, RARITY, RSHORT, RCOLOR, TCOLOR, fmt, esc, cardImg, setImg } from './core.js';
import { sfx, setSound, music, setMusic, setVolumes } from './audio.js';
import { createOpener, T_ZOOMED } from './opener.js';
import { createVfx } from './vfx.js';
import { startSpace } from './space.js';
import * as P from './progress.js';
import { createWorld, AREAS } from './world.js';
import * as QS from './quests.js';
import { runTitle } from './title.js';
import * as RK from './rank.js';
import { openWorldMap } from './worldmap.js';
import * as PAD from './pad.js';
import { initDual, deviceInfo } from './dual.js';
import { runPrologue, startCoach } from './prologue.js';
import { festivalToday, FESTIVALS } from './events.js';
import { autoCheck, manualCheck } from './updater.js';
import { createPreview, PETS, portrait, VRM_CAST } from './chars.js';
import { panelBreak, areaCard, onomato, impactFrame, speedLines, TYPE_COL } from './comicfx.js';
import { Battle, TRAINERS, fighter, enemyTeam, bestTeam, power, mult, SIG, MOVES, ENERGY_MAX, estimate } from './battle.js';

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const view = $('#view');
let state = C.load();
const st = () => C.S;   // live save object (C.S is re-bound on import)

/* ------------------------------------------------------------------ helpers */
function toast(msg, kind = '') {
  const t = document.createElement('div'); t.className = 'toast ' + kind; t.innerHTML = msg; $('#toasts').append(t);
  requestAnimationFrame(() => t.classList.add('on')); setTimeout(() => { t.classList.remove('on'); setTimeout(() => t.remove(), 400); }, 3200);
}
let shownCoins = null, coinAnim = 0;
function updateTop() {
  const target = st().coins;
  if (shownCoins === null) shownCoins = target;
  if (target !== shownCoins) {
    cancelAnimationFrame(coinAnim); const from = shownCoins, t0 = performance.now();
    $('.res.coins').classList.remove('bump'); void $('.res.coins').offsetWidth; $('.res.coins').classList.add('bump');
    const step = now => { const k = Math.min(1, (now - t0) / 600); shownCoins = Math.round(from + (target - from) * (1 - Math.pow(1 - k, 3))); $('#coins').textContent = fmt(shownCoins); if (k < 1) coinAnim = requestAnimationFrame(step); };
    coinAnim = requestAnimationFrame(step);
  } else $('#coins').textContent = fmt(target);
  $('#tokens').textContent = st().tokens; $('#tokenPill').hidden = !st().tokens; $('#uniq').textContent = fmt(C.uniqueCount());
  const av = $('#hudAv'), key = JSON.stringify(st().look || {}); if (av && av.dataset.k !== key) { liveAvatar(av, P.ensure().look, 40); av.dataset.k = key; }
  const jn = P.readyCount(), jb = $('#jBadge'); if (jb) { jb.hidden = !jn; jb.textContent = jn; }
  const L = C.levelInfo(); $('#hudLv').textContent = L.lv; $('#hudXp').style.width = (L.pct * 100).toFixed(1) + '%'; $('#hudXpT').textContent = `${fmt(L.cur)} / ${fmt(L.need)} XP`;
}
function xp(n) {
  const ups = C.gainXP(n); updateTop();
  if (ups.length) { const u = ups[ups.length - 1], args = [u.lv, ups.reduce((a, x) => a + x.coins, 0), ups.reduce((a, x) => a + x.token, 0)];
    if (deferLv || !$('#opening').hidden) pendingLv = args; else showLevelUp(...args); } // never cover a pack opening
}
let pendingLv = null, deferLv = false;
function showLevelUp(lv, coins, tokens) {
  const el = $('#lvup'); el.hidden = false; sfx.win();
  el.innerHTML = `<div class="lvbox"><div class="eyebrow">Trainer level up</div><div class="n">${lv}</div><h2 class="display grad">Level ${lv} reached</h2>
    <p><span class="gold">+${fmt(coins)} coins</span>${tokens ? ` · <b>+${tokens} free pack</b>` : ''}</p><button class="btn gold big" type="button" id="lvOk">Awesome</button></div>`;
  $('#lvOk').onclick = () => { el.hidden = true; }; $('#lvOk').focus();
}
C.onChange(updateTop);
function achievements() { for (const a of C.checkAch()) { toast(`<b>Achievement:</b> ${esc(a.name)} <span class="gold">+${fmt(a.reward)}</span>`, 'ach'); sfx.coin(); } updateTop(); }
const rarityChip = r => `<span class="rchip" style="--rc:${RCOLOR[r]}">${RSHORT[r]}</span>`;
const typeDot = t => `<span class="tdot" style="--tc:${TCOLOR[t] || '#777'}" title="${t}"></span>`;
function cardTile(c, opt = {}) {
  const owned = st().owned[c.i] || 0, miss = opt.binder && !owned;
  return `<button class="ctile ${miss ? 'miss' : ''} r${c.r}" data-card="${c.i}" type="button" aria-label="${esc(c.n)}">
    <span class="cimg"><img loading="lazy" src="${cardImg(c)}" alt="" onerror="this.parentNode.classList.add('broken')"></span>
    ${owned > 1 ? `<span class="count">×${owned}</span>` : ''}${opt.isNew ? '<span class="newb">NEW</span>' : ''}
    <span class="cmeta"><span class="cn">${esc(c.n)}</span><span class="cv">${rarityChip(c.r)} ${opt.binder ? '#' + esc(c.no) : fmt(C.price(c))}</span></span>
  </button>`;
}
function packTile(s) {
  const th = setImg(s, 'pack'), p = C.setProgress(s.code);
  return `<article class="ptile" data-set="${s.code}">
    <div class="pimg" data-go="#pack/${encodeURIComponent(s.code)}" title="Pack details">${th ? `<img loading="lazy" src="${th}" alt="${esc(s.name)} booster pack">` : `<div class="genpack"><span>${esc(s.name)}</span></div>`}</div>
    <div class="pinfo"><div class="pname">${esc(s.name)}</div><div class="pser">${esc(s.series)} · ${p.have}/${p.total} collected</div><div class="pbar"><i style="width:${(p.have / p.total * 100).toFixed(1)}%"></i></div></div>
    <div class="pbuy"><button class="btn" data-open="${s.code}" type="button">Open · <span class="coin"></span>${fmt(s.price)}</button>
    <button class="btn ghost sm" data-quick="${s.code}" type="button" title="Open 5 packs without animation">×5 quick</button></div>
  </article>`;
}
function vaultTile(p) {
  const left = C.vaultLeft(p.code);
  return `<article class="vtile ${left ? '' : 'soldout'}" data-go="#pack/${p.code}" tabindex="0" role="link" aria-label="${esc(p.name)}">
    <div class="vring"><img loading="lazy" src="${C.vaultArt(p)}" alt="${esc(p.name)}"></div>
    <div class="vinfo"><div class="vtags">${p.tags.map(t => `<span>${esc(t)}</span>`).join('')}</div><b>${esc(p.name)}</b>
      <div class="vprice"><span class="coin"></span>${fmt(p.price)} <small>pt</small></div>
      <div class="avail"><span>AVAILABLE</span><span>LEFT <b>${left}</b>/${p.stock}</span></div><div class="abar"><i style="width:${left / p.stock * 100}%"></i></div></div>
  </article>`;
}
function spark(vals, w = 120, h = 32) {
  const mn = Math.min(...vals), mx = Math.max(...vals), sx = w / (vals.length - 1), sy = v => h - 3 - (mx === mn ? .5 : (v - mn) / (mx - mn)) * (h - 6);
  const d = vals.map((v, i) => `${i ? 'L' : 'M'}${(i * sx).toFixed(1)},${sy(v).toFixed(1)}`).join('');
  const up = vals[vals.length - 1] >= vals[0];
  return `<svg class="spark ${up ? 'up' : 'down'}" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" aria-hidden="true"><path d="${d}L${w},${h}L0,${h}Z" class="fill"/><path d="${d}" class="line"/><circle cx="${w}" cy="${sy(vals[vals.length - 1])}" r="2.6"/></svg>`;
}
function lazyGrid(el, items, render, chunk = 120) {
  let n = 0; el.innerHTML = '';
  const more = () => { el.insertAdjacentHTML('beforeend', items.slice(n, n + chunk).map(render).join('')); n += chunk; if (n < items.length) io.observe(sentinel); else sentinel.remove(); };
  const sentinel = document.createElement('div'); sentinel.className = 'sentinel';
  const io = new IntersectionObserver(e => { if (e[0].isIntersecting) { io.unobserve(sentinel); more(); el.append(sentinel); } }, { rootMargin: '800px' });
  el.after(sentinel); more();
  if (!items.length) el.innerHTML = '<p class="empty">Nothing here yet.</p>';
}

/* ------------------------------------------------------------------ card modal */
function openCard(i) {
  const c = DB.cards[i], s = DB.setBy[c.s], owned = st().owned[c.i] || 0, hist = C.priceHistory(c), pr = C.price(c), prev = hist[hist.length - 2];
  const ch = ((pr - prev) / prev * 100);
  const inTeam = st().team.includes(c.i);
  const m = $('#modal'); m.hidden = false; document.body.classList.add('noscroll');
  m.innerHTML = `<div class="mcard" role="dialog" aria-modal="true" aria-label="${esc(c.n)}">
    <button class="x" data-close type="button" aria-label="Close">✕</button>
    <div class="tiltwrap"><div class="tilt r${c.r}" id="tilt"><img src="${C.cardHD(c) || cardImg(c)}" data-fallback="${cardImg(c)}" onerror="if(this.dataset.fallback&&this.src!==this.dataset.fallback)this.src=this.dataset.fallback" alt="${esc(c.n)}"><span class="glare"></span><span class="holo"></span></div></div>
    <div class="mdet">
      <div class="eyebrow">${esc(s.name)} · #${esc(c.no)}</div>
      <h2 class="display">${esc(c.n)}</h2>
      <div class="chips">${rarityChip(c.r)} <span>${RARITY[c.r]}</span> ${typeDot(c.t)} <span>${c.t}</span></div>
      ${C.isMon(c) ? `<div class="stats"><div><b>${c.hp}</b><small>HP</small></div><div><b>${c.atk}</b><small>ATK</small></div><div><b>${c.spd}</b><small>SPD</small></div><div><b>${Math.round(power(c))}</b><small>POWER</small></div></div>` : ''}
      <div class="mkt"><div><small>Market price</small><b><span class="coin"></span>${fmt(pr)}</b><span class="delta ${ch >= 0 ? 'up' : 'down'}">${ch >= 0 ? '▲' : '▼'} ${Math.abs(ch).toFixed(1)}%</span></div>${spark(hist, 180, 44)}</div>
      <div class="own">${owned ? `You own <b>${owned}</b>` : 'Not in your collection'}</div>
      <div class="acts">
        ${owned ? `<button class="btn" data-sell="${c.i}" type="button">Sell 1 · <span class="coin"></span>${fmt(C.sellPrice(c))}</button>` : `<button class="btn" data-buy="${c.i}" type="button">Buy · <span class="coin"></span>${fmt(C.buyPrice(c))}</button>`}
        ${owned > 1 ? `<button class="btn ghost" data-sellx="${c.i}" type="button">Sell duplicates (${owned - 1})</button>` : ''}
        ${owned && C.isMon(c) ? `<button class="btn ghost" data-team="${c.i}" type="button">${inTeam ? 'Remove from team' : 'Add to battle team'}</button>` : ''}
      </div>
    </div></div>`;
  const tilt = $('#tilt'), wrap = $('.tiltwrap');
  wrap.onpointermove = e => { const r = wrap.getBoundingClientRect(), x = (e.clientX - r.left) / r.width - .5, y = (e.clientY - r.top) / r.height - .5;
    tilt.style.transform = `rotateY(${x * 22}deg) rotateX(${-y * 22}deg)`; tilt.style.setProperty('--mx', (x + .5) * 100 + '%'); tilt.style.setProperty('--my', (y + .5) * 100 + '%'); };
  wrap.onpointerleave = () => { tilt.style.transform = ''; };
  // phones: tilt the card with the gyroscope
  if (matchMedia('(pointer: coarse)').matches && 'DeviceOrientationEvent' in window) {
    const onOri = e => { if (!tilt.isConnected) { removeEventListener('deviceorientation', onOri); return; } const x = Math.max(-1, Math.min(1, (e.gamma || 0) / 30)), y = Math.max(-1, Math.min(1, ((e.beta || 45) - 45) / 30));
      tilt.style.transform = `rotateY(${x * 16}deg) rotateX(${-y * 16}deg)`; tilt.style.setProperty('--mx', (x * .5 + .5) * 100 + '%'); tilt.style.setProperty('--my', (y * .5 + .5) * 100 + '%'); };
    addEventListener('deviceorientation', onOri, { passive: true });
  }
}
function closeModal() {
  const m = $('#modal'); if (m.hidden || m.classList.contains('closing')) return;
  m.classList.add('closing'); document.body.classList.remove('noscroll');
  setTimeout(() => { m.hidden = true; m.innerHTML = ''; m.classList.remove('closing'); }, 200);
}
document.addEventListener('click', e => {
  const t = e.target.closest('[data-card],[data-close],[data-sell],[data-sellx],[data-buy],[data-team],[data-open],[data-vault],[data-quick],[data-go]');
  if (!t) { if (e.target.id === 'modal') closeModal(); return; }
  if (t.dataset.card != null && !t.closest('.opening')) {
    sfx.click(); const im = t.querySelector('img'), inModal = t.closest('#modal');
    if (im && !inModal && document.startViewTransition && !reduceMotion.matches) { im.style.viewTransitionName = 'hero-card'; transition(() => { im.style.viewTransitionName = ''; openCard(+t.dataset.card); $('#tilt img').style.viewTransitionName = 'hero-card'; }, 'card'); }
    else openCard(+t.dataset.card);
  }
  else if (t.dataset.close != null) closeModal();
  else if (t.dataset.sell) { const c = DB.cards[+t.dataset.sell], p = C.sellPrice(c); if (C.removeCard(c)) { C.addCoins(p); P.track('sell'); sfx.coin(); toast(`Sold ${esc(c.n)} for <span class="gold">${fmt(p)}</span>`); openCard(c.i); rerender(); } }
  else if (t.dataset.sellx) { const c = DB.cards[+t.dataset.sellx], n = st().owned[c.i] - 1, p = C.sellPrice(c) * n; if (n > 0 && C.removeCard(c, n)) { C.addCoins(p); P.track('sell', { n }); sfx.coin(); toast(`Sold ${n} duplicates for <span class="gold">${fmt(p)}</span>`); openCard(c.i); rerender(); } }
  else if (t.dataset.buy) { const c = DB.cards[+t.dataset.buy], p = C.buyPrice(c); if (st().coins < p) { toast('Not enough coins.', 'err'); return; } C.addCoins(-p); C.addCard(c); P.track('buy'); sfx.coin(); toast(`Bought ${esc(c.n)}`); achievements(); openCard(c.i); rerender(); }
  else if (t.dataset.team) { const i = +t.dataset.team, tm = st().team; if (tm.includes(i)) st().team = tm.filter(x => x !== i); else { if (tm.length >= 3) tm.shift(); tm.push(i); } C.save(); openCard(i); if (location.hash.startsWith('#battle')) rerender(); }
  else if (t.dataset.open) { openPack(t.dataset.open); }
  else if (t.dataset.vault) { openVault(t.dataset.vault); }
  else if (t.dataset.quick) { quickOpen(t.dataset.quick, 5); }
  else if (t.dataset.go) { const im = t.querySelector('.pimg img,.vring img'); if (im) im.style.viewTransitionName = 'hero-pack'; location.hash = t.dataset.go; }
});
addEventListener('keydown', e => { if (e.key === 'Escape' && !$('#modal').hidden) closeModal(); });

/* ------------------------------------------------------------------ opening */
const opening = $('#opening');
let opener = null, openCtx = null, lastPaid = 'coins';
function ensureOpener() {
  if (opener) return opener;
  opener = createOpener($('#openCanvas'), {
    sfx: (n, a) => sfx[n]?.(a),
    onReveal: k => showCaption(k),
    onSwap: (k, big, r) => { $('#oCap').classList.remove('on'); sfx.whoosh(.35); if (big) { $('#oHint').textContent = 'Something special…'; }
      if (r >= 4) { const o = $('#opening'); onomato(o, innerWidth * (.25 + Math.random() * .5), innerHeight * .28, r >= 6 ? 'Dragon' : r >= 5 ? 'Fairy' : 'Psychic', { big: r >= 5 }); } },
    onFinish: () => finishOpening(),
  });
  return opener;
}
function showCaption(k) {
  const c = openCtx.cards[k], cap = $('#oCap');
  cap.innerHTML = `<div class="cnum">${k + 1} / ${openCtx.cards.length}</div><b>${esc(c.n)}</b><span>${rarityChip(c.r)} ${RARITY[c.r]} · <span class="coin"></span>${fmt(C.price(c))}${openCtx.fresh[k] ? ' · <em>NEW</em>' : ''}</span>`;
  cap.classList.add('on'); cap.style.setProperty('--rc', RCOLOR[c.r]);
  $('#oHint').textContent = k === openCtx.cards.length - 1 ? 'Tap for summary' : 'Tap / Space for next card';
}
function chargePack(code) {
  const s = DB.setBy[code];
  if (st().tokens > 0) { st().tokens--; C.save(); updateTop(); return 'token'; }
  if (st().coins < s.price) { toast(`You need <span class="gold">${fmt(s.price)}</span> coins. Claim your daily reward, win battles or sell cards.`, 'err'); return null; }
  C.addCoins(-s.price); return 'coins';
}
function grant(cards, meta = {}) {
  const fresh = cards.map(c => C.addCard(c));
  st().packs++; st().pulls.unshift(...cards.slice().reverse().map(c => ({ i: c.i, t: Date.now() }))); st().pulls = st().pulls.slice(0, 40);
  C.snapshotValue(); C.save(true);
  xp(10 + cards.reduce((a, c) => a + [0, 0, 1, 3, 8, 15, 30][c.r], 0));
  P.track('pack', { cards, ...meta });
  return fresh;
}
let vfx = null;
function ensureVfx() { return vfx ||= createVfx($('#vfxCanvas'), { sfx: (n, a) => sfx[n]?.(a) }); }
const FX_BY_HIT = { 4: 'electric', 5: 'candy', 6: 'legendary' };
async function playFx(kind, art, upgrade) {
  const cv = $('#vfxCanvas'); cv.hidden = false; $('#oHint').textContent = 'Tap to skip'; document.body.classList.add('vfxon');
  try { await ensureVfx().play(kind, { art, upgrade }); } catch (e) { console.error(e); }
  cv.hidden = true; document.body.classList.remove('vfxon');
}
function beginOpening(title) {
  document.activeElement?.blur?.(); opening.hidden = false; document.body.classList.add('noscroll'); $('#openCanvas').focus(); $('#oCap').classList.remove('on'); $('#oSum').hidden = true;
  $('#oTitle').textContent = title; $('#oHint').textContent = 'Opening…';
}
async function runOpening(s, cards, fresh, o) {
  openCtx = { s, cards, fresh };
  beginOpening(s.name);
  if (o.fx && o.fx !== 'classic') await playFx(o.fx, o.fxArt, o.fxUpgrade);
  if (opening.hidden) return; // closed during the effect
  $('#oHint').textContent = 'Opening…';
  try {
    await ensureOpener().play({
      packUrl: o.packUrl, logoUrl: o.logoUrl, setName: s.name, mystery: o.mystery, themeName: o.theme, startAt: o.fx && o.fx !== 'classic' ? T_ZOOMED : 0, // after a signature effect: straight to the tear, no second intro
      cards: cards.map(c => ({ img: cardImg(c), hd: C.cardHD(c), r: c.r, n: c.n })),
    });
  } catch (e) { console.error(e); toast('Could not start the 3D opening — showing results instead.', 'err'); closeOpening(); showSummary(s, cards, fresh); }
}
async function openPack(code) {
  const s = DB.setBy[code]; if (!s) return;
  const paid = chargePack(code); if (!paid) return;
  deferLv = !st().settings.fast;
  const cards = C.rollPack(code), fresh = grant(cards);
  lastPaid = paid; lastAgain = () => openPack(code);
  if (st().settings.fast) { showSummary(s, cards, fresh); achievements(); return; }
  const top = Math.max(...cards.map(c => c.r)), fx = st().settings.hitFx !== false ? FX_BY_HIT[top] : null, art = setImg(s, 'pack');
  runOpening(s, cards, fresh, { fx: art ? fx : null, fxArt: art, fxUpgrade: art, packUrl: art, logoUrl: setImg(s, 'logo'), mystery: fx ? false : st().settings.mystery, theme: fx ? 'dark' : st().settings.studio });
}
async function openVault(code) {
  const p = C.vaultBy[code]; if (!p) return;
  if (!C.vaultLeft(code)) { toast('Sold out for today — restocks at midnight.', 'err'); return; }
  if (st().coins < p.price) { toast(`You need <span class="gold">${fmt(p.price)}</span> coins for ${esc(p.name)}.`, 'err'); return; }
  C.addCoins(-p.price); C.vaultBuy(code);
  const s = { code, name: p.name, price: p.price, vault: true };
  deferLv = !st().settings.fast;
  const cards = C.rollVault(code), fresh = grant(cards, { vault: true, code });
  lastPaid = 'coins'; lastAgain = () => openVault(code);
  if (st().settings.fast) { showSummary(s, cards, fresh); achievements(); return; }
  const art = C.vaultArt(p), up = C.vaultUpgrade(p);
  runOpening(s, cards, fresh, { fx: p.fx, fxArt: art, fxUpgrade: up, packUrl: up || art, mystery: false, theme: 'dark' });
}
let lastAgain = null;
function finishOpening() { const { s, cards, fresh } = openCtx; $('#oCap').classList.remove('on'); showSummary(s, cards, fresh, true); }
function closeOpening() { deferLv = false; if (pendingLv) { const a = pendingLv; pendingLv = null; setTimeout(() => showLevelUp(...a), 350); } vfx?.stop(); opener?.stop(); $('#vfxCanvas').hidden = true; document.body.classList.remove('vfxon'); opening.hidden = true; document.body.classList.remove('noscroll'); $('#oSum').hidden = true; rerender(); achievements(); }
const PRIZE_LABEL = ['COMMON', 'UNCOMMON', 'RARE', 'HOLO RARE', 'EPIC', 'MYTHIC', 'LEGENDARY'];
function showSummary(s, cards, fresh, inOpening = false) {
  const total = cards.reduce((a, c) => a + C.price(c), 0), refund = cards.reduce((a, c) => a + C.sellPrice(c), 0);
  const html = `<div class="prizes">
    <div class="pz-head"><button class="btn ghost sm" id="sumBack" type="button">← Go back</button><h2 class="pz-title">Checkout your prizes</h2>
      <span class="pz-pts"><span class="coin"></span>${fmt(st().coins)} <small>points</small></span></div>
    <div class="pz-sub">${esc(s.name)} · pack value <b class="gold">${fmt(total)}</b> ${lastPaid === 'token' ? '· free pack' : '· paid ' + fmt(s.price)}</div>
    <div class="pz-grid">${cards.map((c, k) => `<div class="pz r${c.r}" style="--rc:${RCOLOR[c.r]};--d:${k * 45}ms">
      <div class="pz-lab">${PRIZE_LABEL[c.r]}</div>
      <div class="pz-img"><img src="${cardImg(c)}" alt="" onerror="this.parentNode.classList.add('broken')">${fresh[k] ? '<span class="newb">NEW</span>' : ''}</div>
      <div class="pz-name">${esc(c.n)}</div><div class="pz-meta">${esc(DB.setBy[c.s]?.name || '')} · #${esc(c.no)}</div>
      <div class="pz-grade">${rarityChip(c.r)} ${RARITY[c.r]}</div>
      <div class="pz-val"><span class="coin"></span>${fmt(C.price(c))}</div></div>`).join('')}</div>
    <div class="pz-bar"><button class="btn ghost" id="sumRefund" type="button"><span class="coin"></span>${fmt(refund)} Refund points</button>
      <button class="btn purple" id="sumAgain" type="button">Play again · <span class="coin"></span>${fmt(s.price)}</button>
      <button class="btn gold" id="sumDone" type="button">Continue to collection</button></div></div>`;
  if (inOpening) { const el = $('#oSum'); el.innerHTML = html; el.hidden = false; }
  else { const m = $('#modal'); m.hidden = false; m.innerHTML = `<div class="mcard wide prizewrap">${html}</div>`; document.body.classList.add('noscroll'); rerender(); achievements(); }
  const again = lastAgain || (() => openPack(s.code));
  $('#sumAgain').onclick = () => { if (inOpening) { $('#oSum').hidden = true; opener.stop(); } else closeModal(); again(); };
  const done = () => { if (inOpening) closeOpening(); else closeModal(); };
  $('#sumDone').onclick = done; $('#sumBack').onclick = done;
  let armed = false;
  $('#sumRefund').onclick = e => {
    const b = e.currentTarget;
    if (!armed) { armed = true; b.innerHTML = `Tap again to sell all ${cards.length} cards`; b.classList.add('danger'); return; }
    let got = 0, nn = 0; for (const c of cards) if (C.removeCard(c)) { got += C.sellPrice(c); nn++; } P.track('sell', { n: nn });
    C.addCoins(got); sfx.coin(); toast(`Refunded <span class="gold">+${fmt(got)}</span>`); b.disabled = true; b.innerHTML = 'Refunded ✓'; b.classList.remove('danger');
    $$('.pz').forEach(x => x.classList.add('gone')); updateTop();
  };
}
function quickOpen(code, n) {
  lastPaid = 'coins'; lastAgain = null;
  const s = DB.setBy[code], all = [], fresh = [];
  for (let k = 0; k < n; k++) { if (!chargePack(code)) break; const cs = C.rollPack(code); all.push(...cs); fresh.push(...grant(cs)); }
  if (!all.length) return;
  const order = all.map((c, k) => ({ c, f: fresh[k] })).sort((a, b) => b.c.r - a.c.r || b.c.v - a.c.v);
  sfx.burst(); if (order[0].c.r >= 4) setTimeout(() => sfx.rare(order[0].c.r - 3), 300);
  showSummary({ ...s, price: s.price }, order.map(o => o.c), order.map(o => o.f));
  $('#sumAgain').innerHTML = `Open ×${n} again`; $('#sumAgain').onclick = () => { closeModal(); quickOpen(code, n); };
}
$('#oSkip').onclick = () => opener?.revealAll();
$('#oClose').onclick = () => closeOpening();
$('#openCanvas').addEventListener('click', () => opener?.next());
$('#vfxCanvas').addEventListener('click', () => vfx?.skip());
addEventListener('keydown', e => { if (!opening.hidden && $('#oSum').hidden && (e.code === 'Space' || e.code === 'Enter' || e.code === 'ArrowRight')) { e.preventDefault(); if (vfx?.active) vfx.skip(); else opener?.next(); } });

/* 3D hover tilt for every card and pack tile */
document.addEventListener('pointermove', e => {
  const el = e.target.closest?.('.ctile,.ptile'); if (tiltEl && tiltEl !== el) { tiltEl.style.transform = ''; tiltEl = null; }
  if (!el || el.closest('.opening')) return; tiltEl = el;
  const r = el.getBoundingClientRect(), x = (e.clientX - r.left) / r.width - .5, y = (e.clientY - r.top) / r.height - .5;
  el.style.transform = `perspective(700px) rotateY(${x * 16}deg) rotateX(${-y * 16}deg) translateY(-4px)`;
  el.style.setProperty('--gx', (x + .5) * 100 + '%'); el.style.setProperty('--gy', (y + .5) * 100 + '%');
});
let tiltEl = null;

/* small text dialog (save codes): copy-able text or a paste box */
function openModalText(title, text, onOk) {
  const m = $('#modal'); m.hidden = false;
  m.innerHTML = `<div class="mbox" style="max-width:520px;padding:20px"><h3 class="display">${esc(title)}</h3><textarea id="mtxt" rows="6" style="width:100%;font:12px monospace;border-radius:10px;padding:8px" ${onOk ? '' : 'readonly'}>${esc(text)}</textarea>
    <div class="row" style="margin-top:10px">${onOk ? '<button class="btn gold" id="mok" type="button">Restore</button>' : ''}<button class="btn ghost" data-close type="button">Close</button></div></div>`;
  const ta = $('#mtxt'); if (!onOk) { ta.focus(); ta.select(); } $('#mok')?.addEventListener('click', () => { const v = ta.value; closeModal(); onOk(v); });
}
function confirmTwice(b) { if (b.dataset.arm) return true; b.dataset.arm = 1; const t = b.textContent; b.textContent = 'Tap again to replace your current progress'; setTimeout(() => { delete b.dataset.arm; b.textContent = t; }, 4000); return false; }

/* ------------------------------------------------------------------ page groups: one rail entry, tabs at the top
   Cards = your cards, binder, team and market (all about the cards you own); Journey = story + ranking. Fewer places to look. */
const GROUPS = {
  cards: [['collection', 'Cards'], ['dex', 'Pokédex'], ['binder', 'Binder'], ['battle', 'Team'], ['market', 'Market']],
  journey: [['journey', 'Story'], ['ranking', 'Ranking']],
};
const GROUP_OF = Object.fromEntries(Object.entries(GROUPS).flatMap(([g, l]) => l.map(([n]) => [n, g])));
function subnav(name) {
  const g = GROUP_OF[name]; if (!g || name === 'world') return; view.querySelector(':scope > .subnav')?.remove();
  const nav = document.createElement('nav'); nav.className = 'subnav'; nav.setAttribute('aria-label', 'Section');
  nav.innerHTML = GROUPS[g].map(([n, t]) => `<a href="#${n}" class="${n === name ? 'on' : ''}">${t}</a>`).join('');
  view.prepend(nav);
}

/* ------------------------------------------------------------------ views */
const VIEWS = {};
let current = '';
function rerender() { const h = location.hash.slice(1) || 'home'; const [name, arg] = h.split('/'); (VIEWS[name] || VIEWS.home)(arg, true); subnav(name); updateTop(); }
/* smooth, context-aware transitions (View Transitions API; CSS fallback) */
const ORDER = ['home', 'shop', 'binder', 'collection', 'market', 'battle', 'ranking', 'profile'];
const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)');
function transition(update, type) {
  if (!document.startViewTransition || reduceMotion.matches) { update(); return null; }
  const root = document.documentElement; root.dataset.vt = type;
  const vt = document.startViewTransition(update); vt.ready?.catch(() => {}); vt.updateCallbackDone?.catch(() => {});
  vt.finished.catch(() => {}).finally(() => { if (root.dataset.vt === type) delete root.dataset.vt; $$('[style*="view-transition-name"]').forEach(e => { if (!e.classList.contains('vt-keep')) e.style.viewTransitionName = ''; }); });
  return vt;
}
function routeType(prev, next) {
  const [pn, pa] = prev.split('/'), [nn, na] = next.split('/');
  if (nn === 'pack') return 'in';
  if (pn === 'pack') return (nn === 'shop' || nn === 'home') ? 'out' : 'in';
  if (pn === nn) return na && !pa ? 'in' : !na && pa ? 'out' : 'swap';
  const a = ORDER.indexOf(pn), b = ORDER.indexOf(nn);
  return b > a ? 'down' : 'up';
}
function route() {
  const h = location.hash.slice(1) || 'world', [name, arg] = h.split('/');
  const changed = current !== h, prev = current || h;
  const apply = () => {
    if ((location.hash.slice(1) || 'world') !== h) return; // a newer navigation already happened — never render a stale view
    if (name !== 'world') { hideWorld(); closeLattice(); }
    $('#backWorld')?.classList.toggle('on', name !== 'world');
    const grp = GROUP_OF[name];
    $$('.rail a').forEach(a => a.classList.toggle('on', !a.classList.contains('rlogo') && (a.getAttribute('href') === '#' + name || (!!grp && a.dataset.group === grp))));
    if (changed) view.scrollTop = 0; current = h;
    (VIEWS[name] || VIEWS.home)(arg); subnav(name); updateTop();
  };
  if (!changed) { apply(); return; }
  sfx.tick();
  const vt = name !== 'world' && !prev.startsWith('world'); // never snapshot the 3D canvas (slow GPUs freeze on it)
  if (!(vt && document.startViewTransition && !reduceMotion.matches && transition(apply, routeType(prev, h)))) { apply(); view.classList.remove('enter'); void view.offsetWidth; view.classList.add('enter'); clearTimeout(route.t); route.t = setTimeout(() => view.classList.remove('enter'), 700); }
}
addEventListener('hashchange', () => { if (!opening.hidden && typeof closeOpening === 'function') closeOpening(); route(); }); // leaving the page (Android back) also closes a pack opening

let lobbyIdx = 0;
VIEWS.home = () => {
  const d = C.dailyState(), sellable = DB.sets.filter(s => s.sellable && s.img.pack), featured = sellable.slice(-8).reverse();
  lobbyIdx = (lobbyIdx + featured.length) % featured.length;
  const hero = featured[lobbyIdx], val = C.collectionValue(), L = C.levelInfo();
  const pulls = st().pulls.slice(0, 14).map(p => DB.cards[p.i]);
  const best = st().stats.best != null ? DB.cards[st().stats.best] : null;
  const pickArt = (code) => { const l = (DB.bySet[code] || []).filter(c => c.r >= 4); return l.length ? cardImg(l[0]) : ''; };
  view.innerHTML = `
  <a class="worldhero" href="#world"><div><div class="eyebrow">Open world · 7 areas</div><h2 class="display">Explore Veyra in 3D</h2><p>Walk Lumen Harbor, meet trainers, catch Echo shells as pets and duel with your cards.</p></div><span class="btn gold glow">Back to Veyra ▸</span></a>
  <section class="wrap lobby">
    <div class="side">
      <div class="tile daily ${d.ready ? 'ready' : ''}">
        <div class="chest">🎁</div><div class="eyebrow">Daily reward</div>
        ${d.ready ? `<h3>Day ${d.streak}</h3><p><span class="gold">+${fmt(d.coins)}</span> coins + 1 free pack</p><button class="btn gold glow" id="claim" type="button">Claim</button>` : `<h3>Claimed</h3><p class="muted">Streak ${st().streak} day${st().streak === 1 ? '' : 's'} · back tomorrow</p>`}
      </div>
      ${(() => { const f = festivalToday(); return f ? `<a class="tile fest" href="#world" style="--fc:${f.color}"><div class="eyebrow">Today's festival</div><h3 class="small">${esc(f.name)}</h3><p class="muted">${esc(AREAS[f.town]?.name || '')} · more ${f.types.join(' & ')} Echoes · beat ${esc(f.host)} for clothes</p></a>` : ''; })()}
      <div class="tile"><div class="eyebrow">Trainer</div><h3>Level ${L.lv}</h3><div class="xpbar" style="height:12px"><i style="width:${(L.pct * 100).toFixed(1)}%"></i></div><p class="muted">${fmt(L.need - L.cur)} XP to next level · every 5 levels = free pack</p></div>
    </div>
    <div class="stage">
      <div class="rays"></div><div class="ped"></div>
      <div class="pack3d" data-open="${hero.code}" title="Open ${esc(hero.name)}"><img class="vt-keep" style="view-transition-name:lobby-pack" src="${setImg(hero, 'pack')}" alt="${esc(hero.name)} booster pack" data-open="${hero.code}"></div>
      <div class="carousel"><button class="btn ghost" id="prevPack" type="button" aria-label="Previous pack">◀</button><button class="btn ghost" id="nextPack" type="button" aria-label="Next pack">▶</button></div>
      <div class="sname vt-keep" style="view-transition-name:lobby-name"><div class="eyebrow">${esc(hero.series)} · ${hero.count} cards</div><h1 class="display grad">${esc(hero.name)}</h1></div>
      <div class="row"><button class="btn big glow" data-open="${hero.code}" type="button">${st().tokens ? 'Open free pack' : `Open · <span class="coin"></span>${fmt(hero.price)}`}</button><button class="btn ghost big" data-quick="${hero.code}" type="button">×5</button></div>
    </div>
    <div class="side">
      <div class="tile"><div class="eyebrow">Collection value</div><h3><span class="coin"></span>${fmt(val)}</h3>${st().history.length > 1 ? spark(st().history.map(h => h.v), 260, 44) : '<p class="muted">Open packs to start tracking.</p>'}</div>
      <div class="tile"><div class="eyebrow">Best pull</div>${best ? `<div class="row" style="flex-wrap:nowrap"><div style="width:70px;flex:none">${cardTile(best)}</div><div><h3 class="small">${esc(best.n)}</h3><p class="muted">${RARITY[best.r]} · ${fmt(C.price(best))}</p></div></div>` : '<p class="muted">Nothing yet — rip your first pack.</p>'}</div>
    </div>
  </section>
  <section class="wrap"><div class="modes">
    <a class="mode" href="#shop" style="--mc:rgba(123,92,255,.9)"><span class="mbg" style="background-image:url('${setImg(featured[1] || hero, 'pack')}')"></span><b>Shop</b><small>${DB.sets.filter(s => s.sellable).length} booster sets</small></a>
    <a class="mode" href="#binder" style="--mc:rgba(0,140,190,.9)"><span class="mbg" style="background-image:url('${pickArt(hero.code)}')"></span><b>Binder</b><small>${fmt(C.uniqueCount())} / ${fmt(DB.cards.length)} collected</small></a>
    <a class="mode" href="#battle" style="--mc:rgba(210,50,60,.9)"><span class="mbg" style="background-image:url('${pickArt((featured[2] || hero).code)}')"></span><b>Battle</b><small>${st().battle.wins} wins · 8 trainers</small></a>
    <a class="mode" href="#pack/PX-ASCEND" style="--mc:rgba(200,150,40,.95)"><span class="mbg" style="background-image:url('${C.vaultArt(C.VAULT[2])}')"></span><b>Vault</b><small>Premium packs · signature FX</small></a>
    <a class="mode" href="#market" style="--mc:rgba(20,160,90,.9)"><span class="mbg" style="background-image:url('${pickArt((featured[3] || hero).code)}')"></span><b>Market</b><small>Prices move daily</small></a>
  </div></section>
  <section class="wrap"><div class="sech"><div><div class="eyebrow gold">The Vault</div><h2 class="display">Premium packs</h2></div><a class="btn sm ghost" href="#shop">See all</a></div>
    <div class="vgrid">${C.VAULT.slice(0, 3).map(vaultTile).join('')}</div></section>
  <section class="wrap"><div class="sech"><div><div class="eyebrow">Recent pulls</div><h2 class="display">Your latest hits</h2></div><a class="btn sm ghost" href="#collection">All cards</a></div>
    ${pulls.length ? `<div class="strip">${pulls.map(c => cardTile(c)).join('')}</div>` : '<p class="empty">No pulls yet. Your first pack is free.</p>'}</section>`;
  const cl = $('#claim'); if (cl) cl.onclick = () => { const r = C.claimDaily(); if (r) { sfx.coin(); toast(`Daily reward: <span class="gold">+${fmt(r.coins)}</span> and a free pack`); xp(20); VIEWS.home(); updateTop(); } };
  $('#prevPack').onclick = () => { lobbyIdx--; sfx.whoosh(.2); transition(() => VIEWS.home(), 'prev') || 0; };
  $('#nextPack').onclick = () => { lobbyIdx++; sfx.whoosh(.2); transition(() => VIEWS.home(), 'next') || 0; };
};

let shopFilter = { series: 'All', q: '' };
VIEWS.shop = () => {
  const series = ['All', ...new Set(DB.sets.filter(s => s.sellable).map(s => s.series))];
  view.innerHTML = `<section class="wrap"><div class="sech"><div><div class="eyebrow">Shop</div><h2 class="display">Booster packs</h2></div>
    <label class="search"><span class="sr">Search sets</span><input id="shopQ" placeholder="Search sets…" value="${esc(shopFilter.q)}"></label></div>
    <div class="vault"><div class="vhead"><div><div class="eyebrow gold">The Vault</div><h3 class="display">Premium packs</h3></div><p class="muted">10 cards · 3 guaranteed hits · limited daily stock · signature openings</p></div>
      <div class="vgrid">${C.VAULT.map(vaultTile).join('')}</div></div>
    <div class="chipsrow">${series.map(s => `<button class="fchip ${s === shopFilter.series ? 'on' : ''}" data-ser="${esc(s)}" type="button">${esc(s)}</button>`).join('')}</div>
    <div class="grid packs" id="shopGrid"></div></section>
  <section class="wrap"><div class="sech"><div><div class="eyebrow">Ranger Outfitters</div><h2 class="display">Clothes</h2></div><p class="muted">Buy any outfit piece early, or find them in treasure chests out in Veyra. Wear them in <a href="#profile" class="gold">Trainer ▸</a></p></div>
    <div class="outfits" id="outfits"></div></section>`;
  const drawOutfits = () => { const box = $('#outfits'); if (!box) return; const L = P.outfitShop(), look = P.ensure().look;
    box.innerHTML = L.map(it => `<div class="ofit ${it.owned ? 'own' : ''}"><div class="ofav">${it.c ? `<i style="background:${it.c}"></i>` : P.avatarSVG({ ...look, [it.slot]: it.id }, { size: 64, bg: false })}</div>
      <b>${esc(it.name)}</b><small>${esc(P.SLOTS.find(x => x.id === it.slot)?.name || '')}</small>
      ${it.owned ? '<span class="muted small">Owned</span>' : `<button class="btn sm gold" type="button" data-outfit="${it.slot}:${it.id}">${fmt(it.price)} coins</button>`}</div>`).join('');
    $$('[data-outfit]').forEach(b => b.onclick = () => { const [sl, id] = b.dataset.outfit.split(':'), r = P.buyOutfit(sl, id);
      if (r === false) toast('Not enough coins.', 'err'); else if (r) { sfx.coin?.(); toast(`Bought <b>${esc(r.name)}</b>! Wear it in <a href="#profile" class="gold">Trainer ▸</a>`); updateTop?.(); drawOutfits(); } }); };
  drawOutfits();
  const draw = () => {
    const q = shopFilter.q.toLowerCase();
    const list = DB.sets.filter(s => s.sellable && (shopFilter.series === 'All' || s.series === shopFilter.series) && (!q || s.name.toLowerCase().includes(q))).reverse();
    $('#shopGrid').innerHTML = list.map(packTile).join('') || '<p class="empty">No sets match.</p>';
  };
  draw();
  $('#shopQ').oninput = e => { shopFilter.q = e.target.value; draw(); };
  $$('.fchip').forEach(b => b.onclick = () => { shopFilter.series = b.dataset.ser; VIEWS.shop(); });
};

let topIdx = 0;
VIEWS.pack = (code, keep) => {
  code = decodeURIComponent(code || ''); const v = C.vaultBy[code], s = DB.setBy[code];
  if (!v && !s) { location.hash = '#shop'; return; }
  if (!keep) topIdx = 0;
  const pool = v ? DB.cards.filter(c => c.r >= 4 && DB.setBy[c.s]?.sellable && C.isMon(c) && v.types.includes(c.t)) : DB.bySet[code];
  const top = pool.slice().sort((a, b) => b.v - a.v).slice(0, 40);
  const tier = c => c.r === 6 ? ['TIER 1', '#ffd257'] : c.r === 5 ? ['TIER 2', '#ff9ecb'] : c.r === 4 ? ['TIER 3', '#c9a4ff'] : ['ROUND', '#e7c16a'];
  const name = v ? v.name : s.name, img = v ? C.vaultArt(v) : setImg(s, 'pack'), price = v ? v.price : s.price;
  const tags = v ? [...v.tags, ...v.types.map(t => t.toUpperCase())] : [s.series, `${s.count} CARDS`, `EV ${fmt(s.ev)}`];
  const left = v ? C.vaultLeft(code) : 0, p = s ? C.setProgress(code) : null;
  const odds = v ? v.odds : [[2, .6], [3, .22], [4, .105], [5, .05], [6, .025]];
  view.innerHTML = `<section class="wrap"><a class="btn ghost sm" href="#shop">← Shop</a>
  <div class="pdetail"><div class="pdcard">
    <div class="pdtop">
      <div class="pdimg">${img ? `<img src="${img}" alt="${esc(name)}" style="view-transition-name:hero-pack">` : `<div class="genpack"><span>${esc(name)}</span></div>`}</div>
      <div class="pdinfo">
        <div class="pdtags">${tags.map(t => `<span>${esc(t)}</span>`).join('')}<span class="grade">${v ? '10 CARDS' : '7 CARDS'}</span></div>
        <h1 class="pdname">${esc(name)}</h1>
        <div class="pdprice"><span class="coin big"></span>${fmt(price)} <small>pt</small>${v ? `<span class="muted"> · expected value ≈ ${fmt(C.vaultEV(code))}</span>` : ''}</div>
        ${v ? `<div class="avail big"><span>AVAILABLE</span><span>LEFT <b>${left}</b>/${v.stock}</span></div><div class="ticks" style="--p:${left / v.stock}"></div>`
            : `<div class="avail big"><span>COLLECTED</span><span><b>${p.have}</b>/${p.total}</span></div><div class="ticks" style="--p:${p.have / p.total}"></div>`}
        <p class="muted">${v ? esc(v.blurb) : `Standard booster · 3 common, 2 uncommon, 1 bonus, 1 rare-or-better hit.`}</p>
        <div class="odds">${odds.map(([r, q]) => `<span style="--rc:${RCOLOR[r]}"><b>${RSHORT[r]}</b> ${(q * 100).toFixed(q < .1 ? 1 : 0)}%</span>`).join('')}<small>${v ? 'per hit slot ×3' : 'hit slot'}</small></div>
        <div class="row">${v ? `<button class="btn big gold glow" data-vault="${code}" type="button" ${left ? '' : 'disabled'}>${left ? `Open · <span class="coin"></span>${fmt(price)}` : 'Sold out today'}</button>`
          : `<button class="btn big glow" data-open="${code}" type="button">${st().tokens ? 'Open free pack' : `Open · <span class="coin"></span>${fmt(price)}`}</button><button class="btn ghost big" data-quick="${code}" type="button">×5 quick</button><a class="btn ghost big" href="#binder/${encodeURIComponent(code)}">Binder</a>`}</div>
      </div>
    </div>
    <div class="pdtopcards"><div class="sech"><div class="eyebrow">Top cards inside</div><div><button class="ibtn round" id="tcPrev" type="button" aria-label="Previous">‹</button><button class="ibtn round" id="tcNext" type="button" aria-label="Next">›</button></div></div>
      <div class="tcrow" id="tcRow">${top.map(c => { const [tl, tc] = tier(c); return `<button class="tc" data-card="${c.i}" type="button"><span class="tcimg"><img loading="lazy" src="${cardImg(c)}" alt="${esc(c.n)}" onerror="this.parentNode.classList.add('broken')"></span><span class="tcl" style="color:${tc}">${tl}</span><small>${fmt(C.price(c))}</small></button>`; }).join('')}</div>
    </div>
  </div></div></section>`;
  const row = $('#tcRow'), step = () => row.clientWidth * .8;
  $('#tcPrev').onclick = () => row.scrollBy({ left: -step(), behavior: 'smooth' });
  $('#tcNext').onclick = () => row.scrollBy({ left: step(), behavior: 'smooth' });
};

VIEWS.binder = (code) => {
  const sets = DB.sets; code = code && DB.setBy[code] ? code : (Object.keys(st().owned).length ? DB.cards[+Object.keys(st().owned).slice(-1)[0]].s : sets[sets.length - 1].code);
  const s = DB.setBy[code], p = C.setProgress(code), list = DB.bySet[code];
  const done = p.have === p.total, claimed = st().claimed[code], reward = 500 + p.total * 6;
  const groups = {}; sets.forEach(x => (groups[x.series] ||= []).push(x));
  view.innerHTML = `<section class="wrap binder">
    <aside class="setlist"><label class="search"><span class="sr">Filter sets</span><input id="bq" placeholder="Filter sets…"></label>
      ${Object.entries(groups).map(([g, l]) => `<div class="sg"><div class="sgt">${esc(g)}</div>${l.slice().reverse().map(x => { const q = C.setProgress(x.code); return `<a href="#binder/${encodeURIComponent(x.code)}" class="${x.code === code ? 'on' : ''} ${q.have === q.total ? 'full' : ''}" data-n="${esc(x.name.toLowerCase())}"><span>${esc(x.name)}</span><small>${q.have}/${q.total}</small></a>`; }).join('')}</div>`).join('')}
    </aside>
    <div class="bmain">
      <div class="bhead">${setImg(s, 'logo') ? `<img class="blogo" src="${setImg(s, 'logo')}" alt="${esc(s.name)} logo">` : ''}
        <div><div class="eyebrow">${esc(s.series)}</div><h2 class="display">${esc(s.name)}</h2>
        <div class="prog"><div style="width:${(p.have / p.total * 100).toFixed(1)}%"></div></div><p class="muted">${p.have} of ${p.total} collected · ${Math.round(p.have / p.total * 100)}%</p></div>
        <div class="bacts">${s.sellable ? `<button class="btn" data-open="${s.code}" type="button">Open pack · <span class="coin"></span>${fmt(s.price)}</button>` : '<span class="muted">Promo set — find these on the Market</span>'}
        ${done && !claimed ? `<button class="btn gold" id="claimSet" type="button">Claim set bonus +${fmt(reward)}</button>` : claimed ? '<span class="badge">Set complete ✓</span>' : `<span class="muted">Complete for +${fmt(reward)}</span>`}</div>
      </div>
      <div class="grid cards" id="bgrid"></div>
    </div></section>`;
  lazyGrid($('#bgrid'), list, c => cardTile(c, { binder: true }), 90);
  $('#bq').oninput = e => { const q = e.target.value.toLowerCase(); $$('.setlist a').forEach(a => a.hidden = !a.dataset.n.includes(q)); };
  const on = $('.setlist a.on'); if (on) on.scrollIntoView({ block: 'center' });
  const cs = $('#claimSet'); if (cs) cs.onclick = () => { st().claimed[code] = Date.now(); C.addCoins(reward); xp(250); sfx.win(); toast(`Set complete! <span class="gold">+${fmt(reward)}</span>`); achievements(); VIEWS.binder(code); };
};

let colF = { q: '', r: 'all', t: 'all', sort: 'value' };
VIEWS.collection = () => {
  const owned = C.ownedCards();
  view.innerHTML = `<section class="wrap"><div class="sech"><div><div class="eyebrow">Collection</div><h2 class="display">Your cards</h2>
      <p class="muted">${fmt(C.uniqueCount())} unique · ${fmt(Object.values(st().owned).reduce((a, b) => a + b, 0))} total · worth <span class="gold">${fmt(C.collectionValue())}</span></p></div>
      <button class="btn ghost sm" id="sellDupes" type="button">Sell all duplicates</button></div>
    <div class="filters">
      <label class="search"><span class="sr">Search cards</span><input id="cq" placeholder="Search name…" value="${esc(colF.q)}"></label>
      <label><span class="sr">Rarity</span><select id="cr"><option value="all">All rarities</option>${RARITY.map((r, i) => `<option value="${i}" ${colF.r == i ? 'selected' : ''}>${r}</option>`).join('')}</select></label>
      <label><span class="sr">Type</span><select id="ct"><option value="all">All types</option>${[...C.TYPES, 'Trainer', 'Energy'].map(t => `<option ${colF.t === t ? 'selected' : ''}>${t}</option>`).join('')}</select></label>
      <label><span class="sr">Sort</span><select id="cs">${[['value', 'Highest value'], ['rarity', 'Rarity'], ['new', 'Newest'], ['name', 'Name'], ['set', 'Set']].map(([v, l]) => `<option value="${v}" ${colF.sort === v ? 'selected' : ''}>${l}</option>`).join('')}</select></label>
    </div><div class="grid cards" id="cgrid"></div></section>`;
  const draw = () => {
    const q = colF.q.toLowerCase();
    let l = owned.filter(c => (!q || c.n.toLowerCase().includes(q)) && (colF.r === 'all' || c.r == colF.r) && (colF.t === 'all' || c.t === colF.t));
    const so = { value: (a, b) => C.price(b) - C.price(a), rarity: (a, b) => b.r - a.r || b.v - a.v, new: (a, b) => (st().first[b.i] || 0) - (st().first[a.i] || 0), name: (a, b) => a.n.localeCompare(b.n), set: (a, b) => DB.setBy[a.s].order - DB.setBy[b.s].order || a.i - b.i };
    l.sort(so[colF.sort]); lazyGrid($('#cgrid'), l, c => cardTile(c));
  };
  draw();
  $('#cq').oninput = e => { colF.q = e.target.value; draw(); };
  $('#cr').onchange = e => { colF.r = e.target.value; draw(); };
  $('#ct').onchange = e => { colF.t = e.target.value; draw(); };
  $('#cs').onchange = e => { colF.sort = e.target.value; draw(); };
  $('#sellDupes').onclick = () => {
    let n = 0, coins = 0; for (const c of owned) { const k = st().owned[c.i] - 1; if (k > 0) { coins += C.sellPrice(c) * k; n += k; C.removeCard(c, k); } }
    if (!n) { toast('No duplicates to sell.'); return; } C.addCoins(coins); P.track('sell', { n }); sfx.coin(); toast(`Sold ${n} duplicates for <span class="gold">${fmt(coins)}</span>`); VIEWS.collection();
  };
};

/* ------------------------------------------------------------------ Pokédex: every species you can meet in Veyra */
const DEX_GOALS = [10, 25, 50, 100, 200, 400];
let dexFilter = 'all';
VIEWS.dex = () => {
  const mons = DB.cards.filter(c => C.isMon(c) && DB.setBy[c.s]?.sellable), by = new Map();
  for (const c of mons) { const k = P.species(c.n); if (!k) continue; const e = by.get(k) || { k, t: c.t, cards: [] }; e.cards.push(c); by.set(k, e); }
  const seen = P.dexSeenSet(), own = st().owned || {}, list = [...by.values()].sort((a, b) => a.t.localeCompare(b.t) || a.k.localeCompare(b.k));
  list.forEach((e, i) => { e.no = i + 1; e.caught = e.cards.some(c => own[c.i]); e.seen = e.caught || !!seen[e.k]; e.show = e.cards.find(c => own[c.i]) || e.cards[0]; });
  const nC = list.filter(e => e.caught).length, nS = list.filter(e => e.seen).length, s = P.ensure(); s.dexClaim ||= {};
  const where = t => Object.entries(AREAS).filter(([, a]) => (a.echo || []).includes(t)).map(([, a]) => a.name).join(', ') || 'anywhere, rarely';
  const shown = list.filter(e => dexFilter === 'all' || (dexFilter === 'caught' ? e.caught : dexFilter === 'seen' ? e.seen && !e.caught : !e.seen));
  view.innerHTML = `<section class="wrap dex"><div class="sech"><div><div class="eyebrow">Veyra Pokédex</div><h2 class="display">Pokédex</h2></div>
      <div class="dexsum"><b>${nC}</b><small>caught</small><b>${nS}</b><small>seen</small><b>${list.length}</b><small>species</small></div></div>
    <div class="dexgoals">${DEX_GOALS.map(g => { const done = nC >= g, got = s.dexClaim[g]; return `<button class="btn sm ${done && !got ? 'gold glow' : 'ghost'}" type="button" data-dexg="${g}" ${done && !got ? '' : 'disabled'}>${got ? '✓ ' : ''}${g} caught · ${fmt(g * 40)}</button>`; }).join('')}</div>
    <div class="dexfil">${[['all', 'All'], ['caught', 'Caught'], ['seen', 'Seen'], ['unknown', 'Not seen']].map(([k, t]) => `<button class="chip ${dexFilter === k ? 'on' : ''}" type="button" data-dexf="${k}">${t}</button>`).join('')}</div>
    <div class="dexgrid">${shown.map(e => `<div class="dexe ${e.caught ? 'caught' : e.seen ? 'seen' : 'unk'}" style="--tc:${TYPEC[e.t] || '#888'}" ${e.caught ? `data-card="${e.show.i}"` : ''} title="${e.seen ? esc(e.k) + ' · ' + esc(e.t) + ' · found in ' + esc(where(e.t)) : '???'}">
      <span class="dno">#${String(e.no).padStart(3, '0')}</span>${e.seen ? `<img loading="lazy" src="${cardImg(e.show)}" alt="">` : '<i>?</i>'}
      <b>${e.seen ? esc(e.k) : '???'}</b><small>${e.caught ? '● caught' : e.seen ? '○ seen' : esc(e.t)}</small></div>`).join('')}</div></section>`;
  $$('[data-dexf]').forEach(b => b.onclick = () => { dexFilter = b.dataset.dexf; VIEWS.dex(); });
  $$('[data-dexg]').forEach(b => b.onclick = () => { const g = +b.dataset.dexg; if (nC < g || s.dexClaim[g]) return; s.dexClaim[g] = Date.now(); C.addCoins(g * 40, 'pokedex'); C.save(); sfx.coin(); toast(`Pokédex milestone: <b>${g} caught</b> <span class="gold">+${fmt(g * 40)}</span>`); updateTop(); VIEWS.dex(); });
};
VIEWS.market = () => {
  const day = C.dayNum(), R = C.rng(day * 7919), pool = DB.cards, listings = [];
  const want = [3, 3, 3, 4, 4, 4, 4, 5, 5, 6, 2, 2];
  for (const r of want) { let c; for (let k = 0; k < 50; k++) { c = pool[Math.floor(R() * pool.length)]; if (c.r === r) break; } listings.push(c); }
  const owned = C.ownedCards();
  const movers = owned.map(c => ({ c, d: (C.price(c) - C.price(c, day - 1)) / C.price(c, day - 1) })).sort((a, b) => Math.abs(b.d) - Math.abs(a.d)).slice(0, 8);
  const hist = st().history;
  view.innerHTML = `<section class="wrap"><div class="sech"><div><div class="eyebrow">Market</div><h2 class="display">Today's singles</h2><p class="muted">Listings refresh daily. Buy at +20%, sell at −10% of market.</p></div></div>
    <div class="grid cards">${listings.map(c => `<div class="lcard">${cardTile(c)}<button class="btn sm" data-buy="${c.i}" type="button">Buy · ${fmt(C.buyPrice(c))}</button></div>`).join('')}</div></section>
    <section class="wrap two">
      <div class="panel"><div class="eyebrow">Portfolio</div><h3 class="display">Collection value</h3>
        ${hist.length > 1 ? `<div class="bigchart">${spark(hist.map(h => h.v), 560, 140)}</div><p class="muted">${hist[0].d} → ${hist[hist.length - 1].d}</p>` : '<p class="muted">Your value is recorded each day you play.</p>'}
        <p class="big"><span class="coin"></span>${fmt(C.collectionValue())}</p></div>
      <div class="panel"><div class="eyebrow">Your movers</div><h3 class="display">Biggest price moves</h3>
        ${movers.length ? `<table class="tbl"><tbody>${movers.map(m => `<tr data-card="${m.c.i}"><td>${esc(m.c.n)}<small>${esc(DB.setBy[m.c.s].name)}</small></td><td>${spark(C.priceHistory(m.c, 14), 80, 24)}</td><td class="num">${fmt(C.price(m.c))}</td><td class="num ${m.d >= 0 ? 'up' : 'down'}">${m.d >= 0 ? '+' : ''}${(m.d * 100).toFixed(1)}%</td></tr>`).join('')}</tbody></table>` : '<p class="muted">Own some cards to see how they move.</p>'}
      </div></section>`;
};

/* battle */
let B = null, bBusy = false;
VIEWS.battle = (arg) => {
  if (B && arg === 'fight') return drawBattle();
  B = null;
  const team = st().team.map(i => DB.cards[i]).filter(Boolean);
  const mons = C.ownedCards().filter(C.isMon);
  view.innerHTML = `<section class="wrap"><div class="sech"><div><div class="eyebrow">Battle</div><h2 class="display">Trainer ladder</h2>
      <p class="muted">Pick 3 Pokémon. HP is the number on the card. Basic attacks charge ⚡ energy: ⚡2 fires the type's signature move (burn, paralysis, drain…), ⚡4 the Ultimate. Weakness ×1.5, resistance ×0.75, Guard blocks 55%.</p></div></div>
    <div class="teamrow">${[0, 1, 2].map(k => team[k] ? `<div class="slot filled">${cardTile(team[k])}<small>${team[k].t} · HP ${team[k].hp} · ATK ${team[k].atk}</small></div>` : `<div class="slot"><span>Empty slot</span><small>Open a card and choose “Add to battle team”</small></div>`).join('')}
      <div class="slot act"><button class="btn" id="autoTeam" type="button" ${mons.length ? '' : 'disabled'}>Auto-pick strongest</button><small>${mons.length} Pokémon owned</small></div></div>
    <div class="ladder">${TRAINERS.map((t, i) => { const unlocked = i === 0 || st().battle.beaten[i - 1]; return `<div class="rung ${st().battle.beaten[i] ? 'beaten' : ''} ${unlocked ? '' : 'locked'}">
      <div class="rn">${i + 1}</div><div class="ri"><b>${esc(t.name)}</b><small>${esc(t.title)} · up to ${RARITY[t.maxR]}</small></div>
      <div class="rr"><span class="gold">+${t.reward}</span>${t.token ? ` · ${t.token} free pack${t.token > 1 ? 's' : ''}` : ''}</div>
      <button class="btn sm" data-fight="${i}" type="button" ${unlocked && team.length === 3 ? '' : 'disabled'}>${st().battle.beaten[i] ? 'Rematch' : 'Fight'}</button></div>`; }).join('')}</div>
    <p class="muted">Record: ${st().battle.wins} wins · ${st().battle.losses} losses</p></section>`;
  $('#autoTeam').onclick = () => { st().team = bestTeam(mons).map(c => c.i); C.save(); VIEWS.battle(); };
  $$('[data-fight]').forEach(b => b.onclick = () => startBattle(+b.dataset.fight));
};
// opts (world battles): { T: {name,title,lvl,reward}, enemy: [fighters], returnTo: '#world', onWin(), ladder: false }
function startBattle(tier, opts = {}) {
  if (st().team.length < 3) { const mons = C.ownedCards().filter(C.isMon); if (mons.length < 3) { toast('You need 3 Pokémon cards for a battle — open a few packs first.', 'err'); return; } st().team = bestTeam(mons).map(c => c.i); C.save(); toast('Auto-picked your 3 strongest cards as your team.'); }
  const mine = st().team.map(i => fighter(DB.cards[i]));
  B = { tier, opts, b: new Battle(mine, opts.enemy || enemyTeam(tier, Date.now() & 0xffff)), log: [] };
  const go = () => { if (location.hash === '#battle/fight') VIEWS.battle('fight'); else location.hash = 'battle/fight'; };
  if (document.body.classList.contains('game') && world && !opts.noIntro) {
    const T = opts.T || TRAINERS[tier], lead = B.b.active('e');
    let img = null; try { img = world.snapshot(); } catch (e) { /* no snapshot: plain splash */ }
    world.setPaused(true); sfx.whoosh?.(.8);
    panelBreak({ img, title: T.name, sub: `${lead.name} · ${lead.type}`, color: TYPE_COL[lead.type] || '#ff5a4e' }, go);
  } else go();
}
const bT = () => B.opts?.T || TRAINERS[B.tier];
window.__startBattle = startBattle;
/* ---------- battle presentation: the cards themselves fight ---------- */
let bSpeed = 1;
const bw = ms => new Promise(r => setTimeout(r, ms / bSpeed));
const anim = (el, kf, o) => el ? el.animate(kf, { ...o, duration: (o.duration || 400) / bSpeed }).finished.catch(() => {}) : Promise.resolve();
const TCOL = t => TCOLOR[t] || '#ccc';
function fighterHTML(f, side) {
  return `<div class="bf ${side}" id="bf-${side}" style="--tc:${TCOL(f.type)}">
    <div class="bf-card"><div class="bf-float"><img src="${C.cardHD(f.card) || cardImg(f.card)}" onerror="this.onerror=null;this.src='${cardImg(f.card)}'" alt="${esc(f.name)}"><span class="bf-flash"></span><span class="bf-shield"></span><span class="bf-aura"></span></div></div>
    <div class="bf-plate">
      <div class="bf-top"><b class="bf-name">${esc(f.name)}</b><span class="bf-type">${typeDot(f.type)}${f.type}</span><span class="bf-st"></span></div>
      <div class="bf-hp"><i class="ghost"></i><i class="live"></i></div>
      <div class="bf-bot"><span class="bf-hpt"></span><span class="bf-en">${Array.from({ length: ENERGY_MAX }, () => '<i></i>').join('')}</span></div>
    </div></div>`;
}
function benchHTML(side) {
  const t = B.b[side].team;
  return t.map((f, i) => `<span class="bpip ${f.hp <= 0 ? 'down' : ''} ${i === B.b[side].act ? 'on' : ''}" title="${esc(f.name)}"><img src="${cardImg(f.card)}" alt=""></span>`).join('');
}
function drawBattle() {
  const b = B.b, T = bT();
  view.innerHTML = `<section class="arena2" id="arena">
    <div class="bfield" id="bfield">
      <div class="bhead e"><div><b>${esc(T.name)}</b><small>${esc(T.title)} · Lv ×${T.lvl}</small></div><div class="bench" id="bench-e">${benchHTML('e')}</div></div>
      <div class="bhead p"><div class="bench" id="bench-p">${benchHTML('p')}</div><div><b>You</b><small id="bturn">Round ${b.turn}</small></div></div>
      <div class="bslot e" id="slot-e">${fighterHTML(b.active('e'), 'e')}</div>
      <div class="bslot p" id="slot-p">${fighterHTML(b.active('p'), 'p')}</div>
      <div class="bvs">VS</div>
      <div class="fxl" id="fxl"></div>
    </div>
    <div class="bhud">
      <div class="blog2" id="blog"></div>
      <div class="bctrl"><div class="moves2" id="moves"></div>
        <div class="bmeta"><span class="adv" id="adv"></span><button class="btn ghost sm" id="bspd" type="button">Speed ×${bSpeed}</button><button class="btn ghost sm" id="bflee" type="button">Forfeit</button></div></div>
    </div></section>`;
  for (const s of ['p', 'e']) { $('#bf-' + s)._f = b.active(s); refreshFighter(s, true); }
  refreshMoves(); logLine(`${esc(T.name)} wants to battle!`);
  $('#bspd').onclick = () => { bSpeed = bSpeed === 1 ? 2 : 1; $('#bspd').textContent = `Speed ×${bSpeed}`; };
  $('#bflee').onclick = () => { if (bBusy) return; B.b.over = 'lose'; st().battle.losses++; C.save(); showResult('lose'); };
  anim($('#bf-e .bf-card'), [{ transform: 'translate(260px,-80px) rotate(20deg) scale(.6)', opacity: 0 }, { transform: 'none', opacity: 1 }], { duration: 700, easing: 'cubic-bezier(.2,.9,.3,1.2)' });
  anim($('#bf-p .bf-card'), [{ transform: 'translate(-260px,80px) rotate(-20deg) scale(.6)', opacity: 0 }, { transform: 'none', opacity: 1 }], { duration: 700, delay: 120, easing: 'cubic-bezier(.2,.9,.3,1.2)' });
}
function refreshFighter(side, instant) {
  const el = $('#bf-' + side); if (!el) return; const f = el._f || B.b.active(side);
  if (el._hp == null) el._hp = f.hp;
  const hp = Math.max(0, Math.round(el._hp)), pct = hp / f.maxHp * 100, live = el.querySelector('.live'), ghost = el.querySelector('.ghost');
  if (instant) { live.style.transition = ghost.style.transition = 'none'; requestAnimationFrame(() => { live.style.transition = ghost.style.transition = ''; }); }
  live.style.width = ghost.style.width = pct + '%'; live.classList.toggle('low', pct < 30); live.classList.toggle('mid', pct >= 30 && pct < 55);
  el.querySelector('.bf-hpt').textContent = `${hp} / ${f.maxHp} HP`;
  el.querySelectorAll('.bf-en i').forEach((x, i) => x.classList.toggle('on', i < f.energy));
  const st2 = [f.status === 'burn' ? '<span class="stb burn">BRN</span>' : '', f.status === 'para' ? '<span class="stb para">PAR</span>' : '',
    f.buff.atk < 1 ? '<span class="stb dn">ATK↓</span>' : '', f.buff.spd < 1 ? '<span class="stb dn">SPD↓</span>' : '', f.buff.def > 1 ? '<span class="stb up">DEF↑</span>' : ''].join('');
  el.querySelector('.bf-st').innerHTML = st2;
  el.classList.toggle('guarding', !!f.guard);
  const bench = $('#bench-' + side); if (bench) bench.innerHTML = benchHTML(side);
}
function refreshMoves() {
  const b = B.b, me = b.active('p'), foe = b.active('e'), sig = SIG[me.type] || SIG.Colorless, box = $('#moves'); if (!box) return;
  const btn = (k, label, sub, cls = '') => `<button class="mv ${cls}" data-m="${k}" type="button" ${b.canUse(me, k) && !bBusy ? '' : 'disabled'} style="--tc:${TCOL(me.type)}"><b>${label}</b><small>${sub}</small></button>`;
  box.innerHTML = btn('attack', 'Attack', `≈${estimate(me, foe, 'attack')} dmg · +1⚡`)
    + btn('sig', sig.name, `≈${estimate(me, foe, 'sig')} dmg · ⚡${MOVES.sig.cost} · ${sig.note}`, 'sig')
    + btn('ult', 'Ultimate', `≈${estimate(me, foe, 'ult')} dmg · ⚡${MOVES.ult.cost}`, 'ult')
    + btn('guard', 'Guard', 'take −55% · +1⚡', 'guard')
    + b.p.team.map((f, i) => i !== b.p.act && f.hp > 0 ? `<button class="mv sw" data-sw="${i}" type="button" ${bBusy ? 'disabled' : ''}><b>Switch</b><small>${esc(f.name)} · ${f.hp} HP</small></button>` : '').join('');
  const m1 = mult(me.type, foe.type), m2 = mult(foe.type, me.type);
  $('#adv').innerHTML = m1 > 1 ? '<span class="good">Your type is super effective</span>' : m2 > 1 ? '<span class="bad">You are weak to them — consider switching</span>' : m1 < 1 ? '<span class="bad">They resist your type</span>' : '';
  $('#bturn') && ($('#bturn').textContent = `Round ${b.turn}`);
  $$('#moves [data-m]').forEach(x => x.onclick = () => act({ kind: x.dataset.m }));
  $$('#moves [data-sw]').forEach(x => x.onclick = () => act({ kind: 'switch', to: +x.dataset.sw }));
}
function logLine(html) {
  const l = $('#blog'); if (!l) return; B.log.push(html);
  const p = document.createElement('p'); p.innerHTML = html; l.append(p); while (l.children.length > 5) l.firstChild.remove();
}
function centerOf(el) { const r = el.getBoundingClientRect(), f = $('#bfield').getBoundingClientRect(); return { x: r.left + r.width / 2 - f.left, y: r.top + r.height / 2 - f.top, w: r.width, h: r.height }; }
function fxAt(cls, x, y, html = '', style = '') { const d = document.createElement('div'); d.className = 'fx ' + cls; d.style.cssText = `left:${x}px;top:${y}px;${style}`; d.innerHTML = html; $('#fxl').append(d); return d; }
function floatText(side, text, cls) {
  const c = centerOf($('#bf-' + side + ' .bf-card')), d = fxAt('ftext ' + cls, c.x + (Math.random() - .5) * 40, c.y - c.h * .2, text);
  anim(d, [{ transform: 'translate(-50%,-50%) scale(.4)', opacity: 0 }, { transform: 'translate(-50%,-90%) scale(1.25)', opacity: 1, offset: .2 }, { transform: 'translate(-50%,-190%) scale(1)', opacity: 0 }], { duration: 1100, easing: 'cubic-bezier(.2,.8,.2,1)' }).then(() => d.remove());
}
function shakeField(k = 1) { anim($('#bfield'), [0, 1, 2, 3, 4, 5].map(i => ({ transform: i === 5 ? 'none' : `translate(${(Math.random() - .5) * 18 * k}px,${(Math.random() - .5) * 12 * k}px)` })), { duration: 360 }); }
async function projectile(from, to, type, big) {
  const a = centerOf($('#bf-' + from + ' .bf-card')), b2 = centerOf($('#bf-' + to + ' .bf-card'));
  const d = fxAt('proj t-' + type + (big ? ' big' : ''), a.x, a.y, '<i></i><i></i><i></i>', `--tc:${TCOL(type)}`);
  const ang = Math.atan2(b2.y - a.y, b2.x - a.x) * 180 / Math.PI;
  await anim(d, [{ transform: `translate(-50%,-50%) rotate(${ang}deg) scale(.3)`, opacity: 0 }, { transform: `translate(-50%,-50%) rotate(${ang}deg) scale(1)`, opacity: 1, offset: .15 },
    { transform: `translate(calc(-50% + ${b2.x - a.x}px), calc(-50% + ${b2.y - a.y}px)) rotate(${ang}deg) scale(${big ? 1.6 : 1.1})`, opacity: 1 }], { duration: big ? 520 : 420, easing: 'cubic-bezier(.5,0,.8,.6)' });
  d.remove();
}
function burst(side, type, big) {
  const c = centerOf($('#bf-' + side + ' .bf-card')), d = fxAt('burst t-' + type + (big ? ' big' : ''), c.x, c.y, '', `--tc:${TCOL(type)}`);
  anim(d, [{ transform: 'translate(-50%,-50%) scale(.2) rotate(0deg)', opacity: 1 }, { transform: `translate(-50%,-50%) scale(${big ? 2.6 : 1.7}) rotate(40deg)`, opacity: 0 }], { duration: big ? 800 : 520, easing: 'cubic-bezier(.1,.8,.2,1)' }).then(() => d.remove());
  for (let i = 0; i < (big ? 22 : 12); i++) {
    const s = fxAt('spark', c.x, c.y, '', `--tc:${TCOL(type)}`), a = Math.random() * 6.28, r = (big ? 160 : 100) * (.5 + Math.random());
    anim(s, [{ transform: 'translate(-50%,-50%) scale(1)', opacity: 1 }, { transform: `translate(calc(-50% + ${Math.cos(a) * r}px), calc(-50% + ${Math.sin(a) * r}px)) scale(.2)`, opacity: 0 }], { duration: 500 + Math.random() * 300, easing: 'cubic-bezier(.1,.8,.3,1)' }).then(() => s.remove());
  }
}
async function strike(e) {
  const s = e.side, o = s === 'p' ? 'e' : 'p', att = $('#bf-' + s + ' .bf-card'), def = $('#bf-' + o + ' .bf-card'), who = B.b.active(s);
  const A = centerOf(att), D = centerOf(def), dx = D.x - A.x, dy = D.y - A.y, big = e.kind === 'ult', ranged = e.kind !== 'attack';
  logLine(`${s === 'p' ? 'Your' : 'Their'} <b>${esc(who.name)}</b> used <b class="mvn" style="color:${TCOL(e.type)}">${esc(e.move)}</b>`);
  if (ranged) {
    // charge up: the card rises and glows in its type colour
    const el = $('#bf-' + s); el.classList.add('charging'); if (big) { $('#arena').classList.add('dim'); sfx.charge(.9 / bSpeed); speedLines($('#bfield'), TCOL(e.type), 1300 / bSpeed); } else sfx.whoosh(.3);
    await anim(att, [{ transform: 'none' }, { transform: `translate(${-dx * .06}px,${-dy * .06 - 24}px) rotate(${s === 'p' ? -8 : 8}deg) scale(${big ? 1.18 : 1.08})` }], { duration: big ? 900 : 480, easing: 'ease-out', fill: 'forwards' });
    if (big) {
      // ultimate: the card itself flies into the opponent
      await anim(att, [{ transform: `translate(${-dx * .06}px,${-dy * .06 - 24}px) rotate(${s === 'p' ? -8 : 8}deg) scale(1.18)` }, { transform: `translate(${dx * .78}px,${dy * .78}px) rotate(${s === 'p' ? 16 : -16}deg) scale(1.25)` }], { duration: 300, easing: 'cubic-bezier(.6,0,.9,.5)', fill: 'forwards' });
    } else { projectile(s, o, e.type, false); await bw(330); }
  } else {
    // basic attack: wind-up, dash, hit
    sfx.whoosh(.2);
    await anim(att, [{ transform: 'none' }, { transform: `translate(${-dx * .08}px,${-dy * .08}px) rotate(${s === 'p' ? -7 : 7}deg)` }], { duration: 260, easing: 'ease-out', fill: 'forwards' });
    await anim(att, [{ transform: `translate(${-dx * .08}px,${-dy * .08}px) rotate(${s === 'p' ? -7 : 7}deg)` }, { transform: `translate(${dx * .62}px,${dy * .62}px) rotate(${s === 'p' ? 10 : -10}deg) scale(1.06)` }], { duration: 200, easing: 'cubic-bezier(.7,0,1,.6)', fill: 'forwards' });
  }
  // impact
  sfx.hit(); burst(o, e.type, big || e.crit); if (big || e.crit || e.eff) shakeField(big ? 1.6 : 1);
  if (big || e.crit) impactFrame($('#bfield'));
  onomato($('#fxl'), D.x + (Math.random() - .5) * 60, D.y - D.h * .42, e.kind === 'attack' ? 'Fighting' : e.type, { big, crit: e.crit });
  const defEl = $('#bf-' + o); defEl.classList.add('hit'); setTimeout(() => defEl.classList.remove('hit'), 260 / bSpeed);
  const kx = dx / Math.hypot(dx, dy) * (big ? 60 : 34), ky = dy / Math.hypot(dx, dy) * (big ? 60 : 34);
  anim(def, [{ transform: 'none' }, { transform: `translate(${kx}px,${ky}px) rotate(${s === 'p' ? 9 : -9}deg)`, offset: .25 }, { transform: 'none' }], { duration: 520, easing: 'ease-out' });
  { const de = $('#bf-' + o); de._hp = Math.max(0, (de._hp ?? 0) - e.d); }
  floatText(o, '−' + e.d, 'dmg' + (e.crit ? ' crit' : '') + (big ? ' big' : ''));
  if (e.crit) setTimeout(() => floatText(o, 'CRITICAL!', 'lbl crit'), 120 / bSpeed);
  if (e.eff) setTimeout(() => floatText(o, 'SUPER EFFECTIVE', 'lbl eff'), 220 / bSpeed);
  else if (e.weak) setTimeout(() => floatText(o, 'resisted', 'lbl weak'), 220 / bSpeed);
  if (e.guarded) setTimeout(() => floatText(o, 'guarded', 'lbl weak'), 300 / bSpeed);
  refreshFighter(o);
  // return home
  anim(att, [{ transform: getComputedStyle(att).transform === 'none' ? 'none' : getComputedStyle(att).transform }, { transform: 'none' }], { duration: 420, easing: 'cubic-bezier(.2,.8,.2,1)' }).then(() => att.getAnimations().forEach(a => a.cancel()));
  $('#bf-' + s).classList.remove('charging'); $('#arena')?.classList.remove('dim');
  refreshFighter(s);
  await bw(big ? 700 : 520);
}
async function knockOut(side) {
  const card = $('#bf-' + side + ' .bf-card'); sfx.ko();
  logLine(`${side === 'p' ? 'Your' : 'Their'} <b>${esc($('#bf-' + side)?._f?.name || 'Pokémon')}</b> fainted!`);
  await anim(card, [{ transform: 'none', opacity: 1, filter: 'none' }, { transform: 'translateY(-14px) rotate(-4deg)', offset: .2 }, { transform: `translateY(80px) rotate(${side === 'p' ? -24 : 24}deg) scale(.7)`, opacity: 0, filter: 'grayscale(1) brightness(.4)' }], { duration: 850, easing: 'cubic-bezier(.5,0,.8,.4)', fill: 'forwards' });
}
async function sendOut(side, idx, forced) {
  const slot = $('#slot-' + side), old = $('#bf-' + side), f = B.b[side].team[idx];
  if (old && !forced) await anim(old.querySelector('.bf-card'), [{ transform: 'none', opacity: 1 }, { transform: `translateX(${side === 'p' ? -220 : 220}px) rotate(${side === 'p' ? -18 : 18}deg) scale(.7)`, opacity: 0 }], { duration: 420, easing: 'ease-in', fill: 'forwards' });
  slot.innerHTML = fighterHTML(f, side); $('#bf-' + side)._f = f; refreshFighter(side, true);
  logLine(`${side === 'p' ? 'You' : esc(bT().name.split(' ').pop())} sent out <b>${esc(f.name)}</b>!`); sfx.whoosh(.4);
  await anim($('#bf-' + side + ' .bf-card'), [{ transform: `translateX(${side === 'p' ? -260 : 260}px) rotateY(${side === 'p' ? -90 : 90}deg) scale(.7)`, opacity: 0 }, { transform: 'none', opacity: 1 }], { duration: 620, easing: 'cubic-bezier(.2,.9,.3,1.15)' });
}
function showResult(r) {
  const T = bT(), a = $('#arena'); if (!a) return; const back = B.opts?.returnTo;
  const d = document.createElement('div'); d.className = 'bresult ' + r;
  d.innerHTML = `<div class="brbox"><div class="eyebrow">${esc(T.name)}</div><h2 class="display">${r === 'win' ? 'Victory!' : 'Defeated'}</h2>
    <p>${r === 'win' ? `<span class="gold">+${T.reward} coins</span>${T.token && B.firstWin ? ` · +${T.token} free pack${T.token > 1 ? 's' : ''}` : ''} · ${B.b.turn - 1} rounds` : 'Upgrade your team, use type advantages and try again.'}</p>
    <div class="row" style="justify-content:center">${r === "win" && B.opts?.prize ? `<div class="bprize">${B.opts.prize}</div>` : ''}<button class="btn gold" data-go="${back || 'battle'}" type="button">${back ? 'Back to the World' : 'Back to ladder'}</button>${r === 'lose' ? `<button class="btn ghost" id="bRetry" type="button">Retry</button>` : ''}</div></div>`;
  a.append(d); const rt = $('#bRetry'); if (rt) rt.onclick = () => startBattle(B.tier, B.opts);
}
async function act(a) {
  if (bBusy || !B || B.b.over) return; bBusy = true; refreshMoves();
  const b = B.b, ev = b.round(a);
  for (const e of ev) {
    if (!$('#arena')) break; // left the screen mid-round
    const actor = e.side === 'p' ? 'You' : bT().name.split(' ').pop();
    if (e.t === 'hit') await strike(e);
    else if (e.t === 'ko') await knockOut(e.side);
    else if (e.t === 'switch') await sendOut(e.side, e.to, e.forced);
    else if (e.t === 'guard') { logLine(`${actor} ${e.side === 'p' ? 'raise' : 'raises'} a guard.`); refreshFighter(e.side); sfx.click(); await bw(350); }
    else if (e.t === 'status') { logLine(`${e.side === 'p' ? 'Your' : 'Their'} Pokémon is ${e.st === 'burn' ? '<b style="color:#ff8a4c">burned</b>' : '<b style="color:#f2c230">paralyzed</b>'}!`); floatText(e.side, e.st === 'burn' ? 'BURNED' : 'PARALYZED', 'lbl ' + e.st); refreshFighter(e.side); await bw(450); }
    else if (e.t === 'para') { logLine(`${e.side === 'p' ? 'Your' : 'Their'} Pokémon is paralyzed and can't move!`); floatText(e.side, 'can’t move', 'lbl para'); anim($('#bf-' + e.side + ' .bf-card'), [0, 1, 2, 3, 4].map(i => ({ transform: i === 4 ? 'none' : `translateX(${i % 2 ? 6 : -6}px)` })), { duration: 300 }); await bw(600); }
    else if (e.t === 'burn') { const be = $('#bf-' + e.side); if (be) be._hp = Math.max(0, be._hp - e.d); floatText(e.side, '−' + e.d, 'dmg burn'); logLine(`Burn deals ${e.d} damage.`); $('#bf-' + e.side).classList.add('burning'); setTimeout(() => $('#bf-' + e.side)?.classList.remove('burning'), 600); refreshFighter(e.side); await bw(550); }
    else if (e.t === 'cure') { refreshFighter(e.side); }
    else if (e.t === 'heal') { const he = $('#bf-' + e.side); if (he) he._hp = Math.min(he._f.maxHp, he._hp + e.n); floatText(e.side, '+' + e.n, 'heal'); refreshFighter(e.side); await bw(300); }
    else if (e.t === 'debuff' || e.t === 'buff') { floatText(e.side, e.stat + (e.t === 'buff' ? ' ↑' : ' ↓'), 'lbl ' + (e.t === 'buff' ? 'up' : 'dn')); refreshFighter(e.side); await bw(300); }
    else if (e.t === 'end') {
      const T = bT(), ladder = B.opts?.ladder !== false && !B.opts?.T;
      P.track('battle', { win: e.result === 'win', tier: B.tier, types: [...new Set(B.b.p.team.map(f => f.type))] });
      if (e.result === 'win') { B.firstWin = ladder && !st().battle.beaten[B.tier]; st().battle.wins++; C.addCoins(T.reward); if (T.token && B.firstWin) st().tokens += T.token; if (ladder) { st().battle.beaten[B.tier] = Date.now(); RK.add(RK.RP.ladder(B.tier), 'Ladder'); } sfx.win(); B.opts?.onWin?.(); }
      else { st().battle.losses++; sfx.lose(); }
      C.save(true); await bw(500); showResult(e.result);
      const gain = e.result === 'win' ? (B.opts?.xp ?? 40 + B.tier * 15) : 10; setTimeout(() => xp(gain), 1800); // let the victory screen breathe first
      achievements();
    }
  }
  bBusy = false; if ($('#arena') && !b.over) { for (const s of ['p', 'e']) { const el = $('#bf-' + s); if (el) el._hp = el._f.hp; refreshFighter(s); } refreshMoves(); }
}

/* ------------------------------------------------------------------ story scenes (visual-novel style) */
function playScene(lines, { title, cine, onLine } = {}) {
  return new Promise(res => {
    const el = $('#scene'); let i = 0, typing = null, done = false;
    const ownCine = cine && !document.body.classList.contains('cine-on'); if (ownCine) document.body.classList.add('cine-on'); // letterboxed scenes own the screen: HUD hides
    const who2 = who => who === 'you' ? { name: st().name, role: P.item('title', P.ensure().look.title).name, look: P.ensure().look } : P.CAST[who] || { name: who, role: '', look: null };
    const finish = () => { if (done) return; done = true; if (ownCine) document.body.classList.remove('cine-on'); clearInterval(typing); el.hidden = true; el.onclick = null; el.classList.remove('cine'); removeEventListener('keydown', key, true); res(); };
    let voiceOf = ''; const type = (pEl, text) => { let k = 0; clearInterval(typing); sfx.tick(); const spd = st().settings.textSpeed ?? 2, vo = st().settings.voices !== false; typing = setInterval(() => { k += spd; pEl.textContent = text.slice(0, k); if (vo && k % 6 < spd && /\w/.test(text[k] || '')) sfx.talk?.(voiceOf, text[k]); if (k >= text.length) { clearInterval(typing); typing = null; } }, 16); };
    const show = () => {
      const [who, text] = lines[i], c = who2(who); voiceOf = who;
      onLine?.(who, i);
      if (cine) { // Genshin-style: letterbox, no portraits — the 3D actors are on screen; name + subtitle at the bottom
        if (!el.querySelector('.cdlg')) el.innerHTML = `<div class="lbx t"></div><div class="lbx b"></div><button class="cskip" type="button">Skip ▸▸</button>${title ? `<div class="ctitle">${esc(title)}</div>` : ''}<div class="cdlg"><div class="cname"></div><p id="scP"></p><div class="cnext">▾</div></div>`;
        const d = el.querySelector('.cdlg'); d.classList.toggle('me', who === 'you'); d.style.animation = 'none'; void d.offsetWidth; d.style.animation = '';
        d.querySelector('.cname').innerHTML = `<b>${esc(c.name)}</b>${c.role ? `<small>${esc(c.role)}</small>` : ''}`;
        el.querySelector('.cskip').onclick = e => { e.stopPropagation(); finish(); };
        type($('#scP'), text);
      } else {
        el.innerHTML = `<div class="scbox ${who === 'you' ? 'me' : ''}" style="--i:${i}">${title && i === 0 ? `<div class="sctitle">${esc(title)}</div>` : ''}
          <div class="scav">${c.look ? av3(who === 'you' ? c.look : { ...c.look, vrm: VRM_CAST[who] }, 170) : ''}</div>
          <div class="sctext"><div class="scname"><b>${esc(c.name)}</b><small>${esc(c.role)}</small></div><p id="scP"></p><div class="scnext">${i < lines.length - 1 ? 'Click to continue ▸' : 'Click to close ✓'}</div></div></div>`;
        type($('#scP'), text);
      }
      el.onclick = () => { const pEl = $('#scP'); if (typing) { clearInterval(typing); typing = null; pEl.textContent = text; return; } if (++i < lines.length) show(); else finish(); };
    };
    const key = e => { if (cine && !document.body.classList.contains('game')) return; /* a waiting world cutscene never eats keys on the menu pages */ if (e.code === 'Space' || e.code === 'Enter') { e.preventDefault(); e.stopImmediatePropagation(); el.onclick?.(); } /* the key that advances a dialogue must not also act in the world */ else if (e.code === 'Escape' && cine) { e.preventDefault(); e.stopImmediatePropagation(); finish(); } };
    addEventListener('keydown', key, true); el.classList.toggle('cine', !!cine); el.innerHTML = ''; el.hidden = false; show();
  });
}

/* ------------------------------------------------------------------ Journey */
const AREA = { harbor: 'Lumen Harbor', mistvale: 'Mistvale', sandreach: 'Sandreach', starfall: 'Starfall Observatory', voltspire: 'Voltspire', frostline: 'Frostline Peaks', rift: 'The Obsidian Rift' };
function resetIn(ms) { const h = Math.floor(ms / 3.6e6), m = Math.floor(ms % 3.6e6 / 6e4); return h > 24 ? `${Math.floor(h / 24)}d ${h % 24}h` : `${h}h ${m}m`; }
/* ------------------------------------------------------------------ Ranger Rank */
function rankChip(big) { const r = RK.rankOf(), n = RK.nextRank(); return `<span class="rankchip ${big ? 'big' : ''}" style="--rc:${r.col}"><i>🏆</i><b>${esc(r.name)}</b><em>${fmt(RK.rp())} RP</em>${n ? `<span class="rbar"><i style="width:${(RK.progress() * 100).toFixed(1)}%"></i></span>` : ''}</span>`; }
RK.setPromoteHook(r => { sfx.rare?.(3); const b = document.createElement('div'); b.className = 'rankup'; b.style.setProperty('--rc', r.col);
  b.innerHTML = `<small>Rank up!</small><b>${esc(r.name)}</b><span>+${fmt(r.reward)} coins</span>`; document.body.append(b); setTimeout(() => b.classList.add('out'), 3200); setTimeout(() => b.remove(), 4000); worldHud?.(); });
VIEWS.ranking = () => {
  const ch = QS?.Q?.().ch || 0, rows = RK.leaderboard(ch), r = RK.rankOf(), n = RK.nextRank(), log = (st().rank?.log || []).slice(0, 8);
  view.innerHTML = `<section class="wrap ranking"><div class="sech"><div><div class="eyebrow">Ranger Rank</div><h2 class="display">Ranking</h2></div>
    <p class="muted">Win battles, capture Echoes, open chests and finish Trials to earn Rank Points. Every promotion pays coins — and you never drop below a tier you reached.</p></div>
    <div class="rkgrid">
      <div class="tile rkme" style="--rc:${r.col}"><div class="rkbadge">🏆</div><h3 class="display">${esc(r.name)}</h3><b class="rkrp">${fmt(RK.rp())} RP</b>
        ${n ? `<div class="cbar"><i style="width:${(RK.progress() * 100).toFixed(1)}%"></i></div><small>${fmt(n.rp - RK.rp())} RP to <b>${esc(n.name)}</b> (+${fmt(n.reward)} coins)</small>` : '<small>Top rank reached.</small>'}
        <div class="rklog">${log.map(([, v, w]) => `<span class="${v < 0 ? 'neg' : ''}">${v > 0 ? '+' : ''}${v} <em>${esc(w)}</em></span>`).join('') || '<em class="muted">No ranked results yet — go battle!</em>'}</div></div>
      <div class="tile rkboard"><div class="eyebrow">Veyra leaderboard</div>
        ${rows.map(x => `<div class="rkrow ${x.me ? 'me' : ''}"><span class="pos">${x.pos}</span><b>${esc(x.name)}</b><span class="rkt" style="color:${x.rank.col}">${esc(x.rank.name)}</span><span class="rp">${fmt(x.rp)}</span></div>`).join('')}</div>
    </div>
    <div class="tile rktiers">${RK.RANKS.map(k => `<span class="${RK.rp() >= k.rp ? 'got' : ''}" style="--rc:${k.col}"><b>${esc(k.name)}</b><small>${fmt(k.rp)} RP</small></span>`).join('')}</div>
  </section>`;
};

VIEWS.journey = () => {  // one story: the Veyra quest line (quests.js) — chapters, steps, seals — plus daily/weekly challenges
  const s = P.ensure(), q = QS.Q(), N = QS.STORY.length, done = q.ch >= N, ch = QS.STORY[Math.min(q.ch, N - 1)], step = QS.stepNow();
  const REG = { harbor: 'Lumen Harbor', mistvale: 'Mistvale', starfall: 'Starfall', frostline: 'Frostline', voltspire: 'Voltspire', sandreach: 'Sandreach', rift: 'The Obsidian Rift' };
  const all = P.challenges(), now = new Date(), midnight = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
  const toMonday = new Date(midnight); toMonday.setDate(midnight.getDate() + ((8 - midnight.getDay()) % 7));
  const chal = c => `<div class="chal ${c.done ? 'done' : ''} ${c.claimed ? 'claimed' : ''}"><div><b>${esc(c.text)}</b><div class="cbar"><i style="width:${c.cur / c.n * 100}%"></i></div><small>${c.cur}/${c.n} · <span class="gold">+${c.coins}</span> · ★${c.st}</small></div>
    ${c.claimed ? '<span class="muted">✓</span>' : `<button class="btn sm ${c.done ? 'gold glow' : 'ghost'}" data-claim="${c.key}" type="button" ${c.done ? '' : 'disabled'}>Claim</button>`}</div>`;
  const next = P.STAR_TRACK.find(i => s.stars < i.u.n);
  const speakers = [...new Set(ch.steps.flatMap(x => (x.lines || []).map(l => l[0])))].filter(w => P.CAST[w]).slice(0, 3);
  view.innerHTML = `<section class="wrap journey">
    <div class="jhero" style="--ac:${done ? '#5cf2d6' : ch.color}">
      <div class="jtxt"><div class="eyebrow">${done ? 'Journey complete' : `Chapter ${q.ch + 1} of ${N} · ${REG[ch.region] || ''}`}</div>
        <h1 class="display">${done ? 'Echo Warden' : esc(ch.title)}</h1>
        <p>${done ? 'Veyra is safe — for now. The Rift stays open for rematches.' : `<b>Now:</b> ${esc(step?.text || '')}`}</p>
        <div class="row"><a class="btn gold glow" href="#world">▶ Go to objective</a><span class="jseals">${Array.from({ length: 9 }, (_, i) => `<i class="${i < q.seals.length ? 'on' : ''}" title="${esc(q.seals[i] || 'Seal')}">◆</i>`).join('')}</span></div></div>
      <div class="jcast">${speakers.map(w => `<div class="jc">${av3({ ...P.CAST[w].look, vrm: VRM_CAST[w] }, 120)}<small>${esc(P.CAST[w].name)}</small></div>`).join('')}</div>
    </div>
    <div class="jgrid">
      <div class="tile jobj"><div class="eyebrow">This chapter</div>
        ${done ? '<p class="muted">All chapters complete.</p>' : ch.steps.map((x, i) => { const ok = i < q.step, cur = i === q.step; return `<div class="obj ${ok ? 'ok' : ''} ${cur ? 'cur' : ''}"><span class="ck">${ok ? '✓' : cur ? '▶' : ''}</span><div><b>${esc(x.text)}</b></div></div>`; }).join('')}
        ${done ? '' : `<small class="muted">Reward: <span class="gold">+${fmt(ch.reward.coins)} coins · +${ch.reward.xp} XP</span>${ch.reward.seal ? ` · ${esc(ch.reward.seal)}` : ''}</small>`}
      </div>
      <div class="tile jchal"><div class="sech"><div class="eyebrow">Daily challenges</div><small class="muted">resets in ${resetIn(midnight - now)}</small></div>${all.daily.map(chal).join('')}
        <div class="sech" style="margin-top:14px"><div class="eyebrow">Weekly challenges</div><small class="muted">resets in ${resetIn(toMonday - now)}</small></div>${all.weekly.map(chal).join('')}
        <div class="stars"><b>★ ${s.stars}</b> challenge stars${next ? ` · next unlock at ★${next.u.n}: <b>${esc(next.name)}</b>` : ' · all star rewards unlocked'}</div></div>
    </div>
    <div class="tile jside"><div class="sech"><div class="eyebrow">Side stories</div><small class="muted">${SIDE.doneCount()}/${SIDE.SIDE.length} complete</small></div>
      ${SIDE.SIDE.map(sq => { const ss = SIDE.stateOf(sq.id), open = q.ch >= sq.minCh, cur = SIDE.current(sq), town = AREA[sq.town] || sq.town;
        return `<div class="obj ${ss?.done ? 'ok' : cur ? 'cur' : ''}"><span class="ck">${ss?.done ? '✓' : cur ? '✦' : ''}</span><div><b>${open ? esc(sq.title) : '???'}</b><small class="muted">${!open ? 'Unlocks later in the story' : ss?.done ? 'Complete' : cur ? esc(cur.text) : `Talk to ${esc(sq.giver.name)} in ${esc(town)}`}</small></div></div>`; }).join('')}</div>
    <div class="tile jline"><div class="eyebrow">Chapters</div><div class="tl">${QS.STORY.map((c, i) => `<div class="tlc ${i < q.ch ? 'done' : i === q.ch ? 'now' : 'lock'}" style="--ac:${c.color}"><span>${i + 1}</span><b>${i <= q.ch ? esc(c.title) : '???'}</b><small>${REG[c.region] || ''}</small></div>`).join('')}</div></div>
  </section>`;
  $$('[data-claim]').forEach(b => b.onclick = () => { const c = P.claimChallenge(b.dataset.claim); if (c) { sfx.coin(); toast(`Challenge complete: <b>${esc(c.text)}</b> <span class="gold">+${c.coins}</span> ★${c.st}`); xp(15 + c.st * 5); afterProgress(); VIEWS.journey(); } });
};
let lastReady = 0;
function afterProgress() {
  for (const it of P.newlyUnlocked()) toast(`New look unlocked: <b>${esc(it.name)}</b> <a href="#profile" class="gold">Trainer ▸</a>`, 'ach');
  const n = P.readyCount(); if (n > lastReady) { toast(`<b>Journey:</b> ${n} reward${n > 1 ? 's' : ''} ready to claim <a href="#journey" class="gold">Open ▸</a>`); } lastReady = n; updateTop();
}
P.onProgress(() => setTimeout(afterProgress, 50));

/* anime-model portraits anywhere in the UI: av3() prints the drawn avatar as a placeholder, an observer swaps in the 3D render */
const AV3 = new Map(); let av3n = 0;
function av3(look, size) { const id = 'a' + (++av3n % 5000); AV3.set(id, look); return `<span class="av3" data-lk="${id}" style="width:${size}px;height:${size}px">${P.avatarSVG(look, { size, bg: false })}</span>`; }
let av3q = 0; new MutationObserver(() => { if (av3q) return; av3q = requestAnimationFrame(() => { av3q = 0;
  for (const el of document.querySelectorAll('.av3[data-lk]')) { const lk = el.dataset.lk, look = AV3.get(lk); AV3.delete(lk); el.removeAttribute('data-lk'); if (look) liveAvatar(el, look, parseInt(el.style.width) || 96); } }); }).observe(document.body, { childList: true, subtree: true });
/* your real 3D character as a little portrait (HUD, Lattice, menu); the drawn avatar shows until it is rendered */
function liveAvatar(el, look, size) {
  if (!el) return; const k = JSON.stringify(look); if (el.dataset.pk === k && el.querySelector('img')) return; el.dataset.pk = k;
  if (!el.firstChild) el.innerHTML = P.avatarSVG(look, { size, bg: false });
  portrait(look, size * 2).then(u => { if (u && el.dataset.pk === k) el.innerHTML = `<img class="pav" src="${u}" width="${size}" height="${size}" alt="">`; });
}
/* ------------------------------------------------------------------ World (3D Veyra) */
let world = null, worldCh = -1; PAD.bindWorld(() => world);
initDual({ world: () => world, travel: id => { sfx.whoosh(.5); world?.travelTo(id); }, menu: () => openLattice() });
const AREA_REQ = { harbor: 0, mistvale: 1, sandreach: 2, starfall: 3, voltspire: 4, frostline: 5, rift: 6 };
function worldConfirm(q, yes, no) {
  return new Promise(res => { const m = $('#wModal'); m.hidden = false;
    m.innerHTML = `<div class="wbox"><p>${esc(q)}</p><div class="row"><button class="btn gold" id="wYes" type="button">${esc(yes)}</button><button class="btn ghost" id="wNo" type="button">${esc(no)}</button></div></div>`;
    const done = v => { m.hidden = true; m.innerHTML = ''; res(v); }; $('#wYes').onclick = () => done(true); $('#wNo').onclick = () => done(false); $('#wYes').focus(); });
}
function worldTravel() {
  const W = world; if (!W) return; if (!$('#wModal').hidden && $('#wModal').classList.contains('fs')) return;
  if (W.indoors) { toast('You are inside — step out of the door to see the map.'); return; }
  sfx.whoosh?.(.25); document.querySelector('.cx-area')?.remove();
  openWorldMap($('#wModal'), { W, q: QS.Q(), req: AREA_REQ, target: QS.target(), onTravel: id => { sfx.whoosh(.5); W.travelTo(id); } });
}
/* starter choice (story step) */
function chooseStarter() {
  /* a short cut-scene: the lab goes dark, three blank-stock cards rise one by one out of the light, flip to reveal their Echo,
     you pick one, the others fade and your partner's card flies to you */
  return new Promise(res => {
    const cards = QS.starterCards(), m = $('#wModal'); m.hidden = false; m.classList.add('stcine');
    m.innerHTML = `<div class="stc-scene"><div class="stc-bars t"></div><div class="stc-bars b"></div>
      <div class="stc-line" id="stLine">Dr. Vale lays three blank-stock cards on the table…</div>
      <div class="stc-row">${cards.map((c, k) => `<button class="stc2" data-st="${c.i}" type="button" style="--c:${TYPEC[c.t] || '#fff'};--d:${.6 + k * .55}s">
        <span class="stc-glow"></span><span class="stc-card"><i class="back"></i><img src="${cardImg(c)}" alt=""></span><b>${esc(c.n)}</b><small>${esc(c.t)} type · HP ${c.hp || '?'}</small></button>`).join('')}</div>
      <p class="stc-hint" id="stHint">Tap a card to choose your partner</p></div>`;
    sfx.whoosh?.(.3); cards.forEach((c, k) => setTimeout(() => sfx.tick?.(), 600 + k * 550));
    setTimeout(() => { const l = $('#stLine'); if (l) l.textContent = `"Every one of them holds an Echo that has been waiting for a Ranger. Choose with your heart."`; }, 2400);
    let chosen = false;
    $$('[data-st]').forEach(b => b.onclick = () => { if (chosen) return; chosen = true; const i = +b.dataset.st, c = DB.cards[i];
      b.classList.add('pick'); m.querySelectorAll('.stc2').forEach(o => o !== b && o.classList.add('gone')); sfx.win?.(); $('#stLine').textContent = `${c.n} chose you too.`; $('#stHint').textContent = '';
      setTimeout(() => { C.addCard(c); const S = st(); S.team = [i, ...(S.team || []).filter(x => x !== i)].slice(0, 3);
        const pets = ensurePets(); pets.card = i; pets.none = false; C.save(true); m.hidden = true; m.innerHTML = ''; m.classList.remove('stcine'); toast(`<b>${esc(c.n)}</b> is your partner!`); res(i); }, 1900); });
  });
}
/* objective HUD: chapter, current step, distance + arrow to the target */
let lastGoal = null;
function worldGoal(g) { lastGoal = g; renderQuestHud(); }
function renderQuestHud() {
  const el = $('#wQuest'); if (!el) return; const q = QS.Q(), ch = QS.chapterNow(), st2 = QS.stepNow(), g = lastGoal;
  if (QS.done()) { el.innerHTML = `<div class="eyebrow">Story complete · ${q.seals.length} seals</div><b>Veyra remembers you.</b>`; return; }
  const idx = ch.steps.indexOf(st2);
  el.innerHTML = `<div class="eyebrow">Chapter ${q.ch + 1}/${QS.STORY.length} · ${esc(ch.title)}</div>
    <div class="wgoal"><span class="warrow" style="transform:rotate(${g?.dist != null ? (-g.ang * 180 / Math.PI) : 0}deg);opacity:${g?.dist != null ? 1 : .3}">➤</span><b>${esc(st2?.text || '')}</b>${g?.dist != null ? `<small>${g.dist} m</small>` : ''}</div>
    <div class="wsteps">${ch.steps.map((s2, i) => `<i class="${i < idx ? 'ok' : i === idx ? 'now' : ''}"></i>`).join('')}</div>
    ${q.seals.length ? `<div class="wseals">${q.seals.map(n => `<span title="${esc(n)}">◆</span>`).join('')}</div>` : ''}`;
}
function sealToast(name, idx) {
  const d = document.createElement('div'); d.className = 'cx-area'; d.style.setProperty('--c', '#ffd257');
  d.innerHTML = `<div class="cx-panel"><span class="cx-kick">Circuit Seal earned</span><b>${esc(name)}</b><small>${QS.Q().seals.length} of 9 seals</small></div>`;
  document.body.append(d); sfx.win?.(); setTimeout(() => d.classList.add('out'), 3200); setTimeout(() => d.remove(), 3900);
}
function wildBattle(spec) {
  const types = spec.types, lv = C.levelInfo().lv, maxR = Math.min(6, 1 + Math.floor(lv / 3)), minR = Math.max(0, maxR - 2), area = AREAS[spec.area];
  const pool = DB.cards.filter(c => C.isMon(c) && types.includes(c.t) && c.r >= minR && c.r <= maxR && DB.setBy[c.s]?.sellable);
  const pickC = () => pool[Math.floor(Math.random() * pool.length)], lvl = .85 + lv * .012;
  const lead = spec.card ? DB.cards[spec.card.i] : null;
  const enemy = [lead || pickC(), pickC()].filter(Boolean).map(c => fighter(c, lvl)); if (!enemy.length) return;
  const T = { name: `Wild ${types[0]} Echo`, title: area.name, lvl: +lvl.toFixed(2), reward: 25 };
  startBattle(0, { T, enemy, returnTo: '#world', xp: 25, onWin() {
    const c = lead || enemy[Math.floor(Math.random() * enemy.length)].card; const isNew = C.addCard(c); P.track('echo');
    pendingEcho = true; const petMsg = `<br><small>It is now a stable card creature — pick it as your partner in <b>Menu → Partner</b>.</small>`;
    B.opts.prize = `Echo stabilised — <b>${esc(c.n)}</b> ${rarityChip(c.r)} ${isNew ? '<em class="gold">NEW</em>' : ''} joins your collection${petMsg}`; } });
}
function partnerCard() { const tm = st().team.filter(i => st().owned[i]); return tm.length ? DB.cards[tm[0]] : bestTeam(C.ownedCards().filter(C.isMon))[0] || null; }
function companionCard() { const p = ensurePets(); if (p.none) return null; const c = p.card != null && st().owned[p.card] ? DB.cards[p.card] : partnerCard(); return c && C.isMon(c) ? c : null; }
function partnerInfo() { const c = companionCard(); return c ? { img: cardImg(c), type: c.t, name: c.n, i: c.i, f: c.f } : null; }
let pendingEcho = false;
function ensurePets() { const s = st(); s.pets ||= { owned: {}, active: null }; return s.pets; }
// integrated / low-power GPUs (Intel UHD/Iris, mobile) start at a lower render scale
const IS_APP = /PokeboxAndroid/.test(navigator.userAgent), TOUCH = IS_APP || matchMedia('(pointer: coarse)').matches;
if (TOUCH) document.documentElement.classList.add('touch'); if (IS_APP) document.documentElement.classList.add('app', 'lowfx');
const WEAK_GPU = (() => { try { const gl = document.createElement('canvas').getContext('webgl2'), d = gl?.getExtension('WEBGL_debug_renderer_info'); const r = d ? gl.getParameter(d.UNMASKED_RENDERER_WEBGL) : ''; return /Intel|UHD|Iris|HD Graphics|Mali|Adreno|PowerVR|Apple GPU/i.test(r); } catch { return false; } })();
const gfx = () => { const g = st().settings; return { q: g.gfx || (TOUCH ? 'low' : 'medium'), auto: g.autoGfx !== false, fov: g.fov || (TOUCH ? 55 : 50), sens: g.sens || 1, inv: !!g.invertY, scale: g.rscale || (WEAK_GPU ? .85 : 1) }; };
let worldPartner = null, worldPet = null;
function ensureWorld() {
  if (world) return world;
  world = createWorld($('#worldCanvas'), {
    quality: () => gfx().q, renderScale: () => gfx().scale, comic: () => st().settings.comic !== false, style: () => st().settings.style || 'toon', setQuality: q => { st().settings.gfx = q; C.save(); if (!$('#gMenu').hidden) renderMenu(); },
    shadows: () => st().settings.shadows !== false, viewDist: () => st().settings.viewDist ?? 1, grassAmt: () => st().settings.grassAmt ?? 1, bloom: () => st().settings.bloom !== false, shaderFx: () => st().settings.shaderFx ?? (PHONE_UI ? 1 : 2), fpsCap: () => st().settings.fpsCap || 0, shake: () => st().settings.shake !== false, fov: () => gfx().fov, sensitivity: () => gfx().sens, invertY: () => gfx().inv,
    minimap: () => $('#wMini'), fps: n => { const f = $('#wFps'); if (f) f.textContent = n + ' fps'; },
    loading: (on, name) => { const l = $('#wLoad'); l.hidden = !on; if (on) $('#wLoadT').textContent = name; },
    partner: partnerInfo,
    clock: ({ tod, state, night }) => { const el = $('#wClock'); if (!el) return; const hh = Math.floor(tod), mm = Math.floor((tod - hh) * 60 / 10) * 10;
      const ic = { rain: '🌧', storm: '⛈', fog: '🌫', snow: '❄', dust: '🌪', cloudy: night ? '☁' : '⛅' }[state] || (night ? '🌙' : tod < 8 || tod > 18 ? '🌅' : '☀');
      el.innerHTML = `<span>${ic}</span><b>${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}</b><small>${state}</small>`; },
    echoCard: (type, R) => { const ch = QS.Q().ch, post = QS.done() && R() < .12, maxR = post ? 8 : Math.min(5, 1 + Math.floor(ch / 2)), minR = post ? 5 : Math.max(0, maxR - 2); // after the story: rare legends roam
      const pool = DB.cards.filter(c => C.isMon(c) && c.t === type && c.r >= minR && c.r <= maxR && DB.setBy[c.s]?.sellable); if (!pool.length) return null;
      const c = pool[Math.floor(R() * pool.length)]; return { i: c.i, img: cardImg(c), n: c.n, f: c.f, t: c.t }; },
    talk: (lines, o) => playScene(lines, o), confirm: worldConfirm, chooseStarter, goal: worldGoal,
    onStep: st => { if (st) toast(`<b>New objective:</b> ${esc(st.text)}`); worldHud(); },
    compass: (head, goal, dist) => compassHud(head, goal, dist),
    fade: on => new Promise(res => { let f = $('#fadeBlack'); if (!f) { f = document.createElement('div'); f.id = 'fadeBlack'; document.body.append(f); } f.classList.toggle('on', !!on); setTimeout(res, 320); }),
    stuck: () => toast(`Stuck? <a href="#" class="gold" onclick="event.preventDefault();window.__world?.respawnNearest()">Go to the nearest checkpoint ▸</a> (also in the menu: Unstuck)`),
    festivalWin: (f, key) => { const s = P.ensure(); s.story.seen ||= {}; if (s.story.seen['fest:' + key]) { toast(`Nice battle! The ${esc(f.name)} prize is once a day — come back tomorrow.`); return; }
      s.story.seen['fest:' + key] = Date.now(); C.addCoins(600, 'festival'); const it = P.chestOutfit(); C.save(); sfx.rare?.(2);
      toast(`🎉 <b>${esc(f.name)} champion!</b> <span class="gold">+600 coins</span>${it ? ` · new clothes: <b>${esc(it.name)}</b> <a href="#profile" class="gold">Wear ▸</a>` : ''}`); afterProgress(); },
    hallOfFame: () => { const q = QS.Q(); if (q.flags.hof) return; q.flags.hof = Date.now(); C.addCoins(5000, 'hall of fame'); C.save(); sfx.rare?.(3);
      playScene([['vale', 'You beat the whole Rift League. Your team goes into the Hall of Fame of Veyra — the first Ranger ever.'], ['rho', 'Champion of the Rift. I am NOT jealous. Okay, a little.']], { title: 'Hall of Fame', cine: true }).then(() => toast('🏆 <b>Hall of Fame!</b> <span class="gold">+5,000 coins</span> · rare legends now roam Veyra more often')); },
    reveal: o => vsCard(o), arrival: (id, a) => { sfx.rare?.(1); },
    onChapter: (ch, idx) => { whenFree(() => chapterCard(idx + 1)); xp(ch.reward?.xp || 0); if (ch.reward?.seal) sealToast(ch.reward.seal, idx); toast(`<b>Chapter complete:</b> ${esc(ch.title)} <span class="gold">+${fmt(ch.reward?.coins || 0)} coins</span>`); worldHud(); }, toast: m => toast(m), sfx: (n, a) => sfx[n]?.(a), xp: n => { xp(n); worldHud(); }, travel: worldTravel, go: h => { location.hash = h; },
    prompt: html => { const p = $('#wPrompt'); p.hidden = !html; document.querySelector('.tb.use')?.classList.toggle('has', !!html); if (!html) return; if (PAD.padActive()) html = html.replace('<b>E</b>', PAD.glyph('X'));
      if (TOUCH) { p.innerHTML = html.replace('<b>E</b>', '<b class="tap">✋</b>'); p.onclick = () => { world.key('KeyE', true); setTimeout(() => world.key('KeyE', false), 60); (st().settings.haptics !== false) && navigator.vibrate?.(8); }; }
      else p.innerHTML = html; },
    region: (id, night) => { musRegion = [id, night]; if (!battleMusic && st().settings.music !== false) music.world(id, night); },
    music: k => { battleMusic = !!k; if (st().settings.music !== false) music.world(k || musRegion[0], k ? false : musRegion[1]); },
    onArea: (a) => { if ((location.hash.slice(1) || 'world').split('/')[0] !== 'world' || document.body.classList.contains('at-title') || document.body.classList.contains('cine-on') || !$('#scene').hidden || !$('#wModal').hidden) return; const dg = a.danger || 0; areaCard({ kicker: a.sub, name: a.name, sub: (dg ? `⚠ Danger ${'★'.repeat(Math.min(5, dg))} · Echoes here outclass your team · ` : '') + 'Wild Echoes · ' + a.echo.join(' / '), color: dg >= 2 ? '#ff6a4a' : TYPE_COL[a.echo[0]] || '#ffd257' }); if (dg >= 2) toast('This area is ahead of your story — wild Echoes are much stronger here. You can explore, but battles will be tough.'); { const f = festivalToday(); if (f && f.town === a.id) setTimeout(() => toast(`🎉 <b>${esc(f.name)}</b> today in ${esc(a.name)} — more ${f.types.join(' & ')} Echoes around town, and ${esc(f.host)} is waiting in the plaza.`), 1800); } $('#wName').textContent = a.name; $('#wSub').textContent = a.sub; const b = $('.warea'); b.classList.remove('in'); void b.offsetWidth; b.classList.add('in'); worldHud(); },
  });
  world.setAutoQuality(gfx().auto);
  $('#wMap').onclick = worldTravel; $('#wMini').onclick = () => worldTravel(); $('#wMenuBtn').onclick = () => openLattice(); $('#wFs').onclick = toggleFullscreen;
  if (TOUCH) { // virtual stick (left) + action buttons (right); camera = drag anywhere else, pinch = zoom
    $('#wTouch').hidden = false; const st2 = $('#wStick'), knob = st2.querySelector('i'); let sid = null, c0 = null;
    const setK = (dx, dy) => { const r = 52, l = Math.hypot(dx, dy), k = l > r ? r / l : 1; knob.style.transform = `translate(${dx * k}px,${dy * k}px)`; world.setStick(dx * k / r, dy * k / r); };
    st2.onpointerdown = e => { sid = e.pointerId; st2.setPointerCapture(sid); const b = st2.getBoundingClientRect(); c0 = { x: b.left + b.width / 2, y: b.top + b.height / 2 }; setK(e.clientX - c0.x, e.clientY - c0.y); st2.classList.add('on'); };
    st2.onpointermove = e => { if (e.pointerId === sid) setK(e.clientX - c0.x, e.clientY - c0.y); };
    st2.onpointerup = st2.onpointercancel = e => { if (e.pointerId !== sid) return; sid = null; knob.style.transform = ''; world.setStick(0, 0); st2.classList.remove('on'); };
    $$('#wTouch [data-k]').forEach(b => { const k = b.dataset.k; b.onpointerdown = e => { e.preventDefault(); b.classList.add('on'); world.key(k, true); (st().settings.haptics !== false) && navigator.vibrate?.(8); }; b.onpointerup = b.onpointercancel = b.onpointerleave = () => { if (b.classList.contains('on')) { b.classList.remove('on'); world.key(k, false); } }; });
    const run = $('#wTouch [data-run]'); run.onclick = () => { run.classList.toggle('on'); world.setRun(run.classList.contains('on')); };
  }
  return world;
}
/* in-world HUD: trainer plate, current objective, pet card */
function worldHud() {
  const s = P.ensure(), L = C.levelInfo();
  liveAvatar($('#wAv'), s.look, 46); $('#wNameP').textContent = s.name; $('#wLv').textContent = L.lv; $('#wXp').style.width = (L.pct * 100).toFixed(1) + '%'; $('#wCoins').textContent = fmt(st().coins);
  { const r = RK.rankOf(), el = $('#wRank'); if (el) { el.textContent = r.name; el.style.setProperty('--rc', r.col); } }
  const ch = P.chapter(), done = P.storyDone();
  if (QS) { renderQuestHud(); } else $('#wQuest').innerHTML = done ? `<div class="eyebrow">Journey complete</div><b>Veyra is stable — for now.</b>` : `<div class="eyebrow">Chapter ${ch.n} · ${esc(ch.title)}</div>${ch.goals.map(g => { const c = g.cur(), ok = c >= g.need; return `<div class="wq ${ok ? 'ok' : ''}"><i>${ok ? '✓' : ''}</i><span>${esc(g.text)}</span><small>${Math.min(c, g.need)}/${g.need}</small></div>`; }).join('')}${P.chapterReady() ? '<a class="wqgo" href="#journey">Chapter ready — open Journey ▸</a>' : ''}`;
  const cc = companionCard(), pe = $('#wPet'); pe.hidden = !cc;
  if (cc) { pe.innerHTML = `<img class="pimg" src="${cardImg(cc)}" alt=""><div><b>${esc(cc.n)}</b><small>${esc(cc.t)} · partner card</small></div><button class="wb sm" type="button" id="wPetBtn">Partner</button>`; $('#wPetBtn').onclick = () => openMenu('pets'); }
}
const TYPEC = { Grass: '#5fae4f', Fire: '#ff6a3c', Water: '#3d9fff', Lightning: '#ffd23c', Psychic: '#d86bff', Fighting: '#d8844a', Darkness: '#8a6ae8', Metal: '#b8c6d4', Dragon: '#e0b040', Colorless: '#f0ece0' };
let musRegion = ['harbor', false], battleMusic = false; // the world soundtrack (audio.js music.world) follows the region
function hideWorld() { music.world(null); const w = $('#worldWrap'); document.body.classList.remove('game'); if (!w.hidden) { w.hidden = true; world?.stop(); $('#wModal').hidden = true; } }
VIEWS.world = () => {
  view.innerHTML = ''; const w = $('#worldWrap'), s = P.ensure(); w.hidden = false; document.body.classList.add('game'); const W = ensureWorld();
  if (st().settings.music !== false && !document.body.classList.contains('at-title')) setTimeout(() => { if (document.body.classList.contains('game')) music.world(...musRegion); }, 600);
  const pets = ensurePets();
  if (wantsPrologue()) document.body.classList.add('prolog-on'); // the story waits until the prologue has played
  if (!W.ready && !W._entering) { W._entering = true; W.enter('here', {}).finally(() => { W._entering = false; worldHud(); firstSteps(W); }); W._look = JSON.stringify(s.look); }
  else if (W.ready) firstSteps(W);
  if (W.ready && JSON.stringify(s.look) !== W._look) { W.refreshLook(); W._look = JSON.stringify(s.look); }
  else if ((companionCard()?.i ?? null) !== worldPartner) W.refreshPartner();
  worldPartner = companionCard()?.i ?? null;
  if (pendingEcho) { pendingEcho = false; setTimeout(() => W.echoWon?.(), 700); }
  W.setPaused(false); W.start(); $('#worldCanvas').focus(); window.__world = W; worldHud();
};
/* compass strip at the top of the world view: where you look, and where the objective is */
let cStripBuilt = false;
function compassHud(head, goal, dist) {
  const strip = $('#wCStrip'), g = $('#wCGoal'); if (!strip) return; const PX = 2.6; // px per degree
  if (!cStripBuilt) { cStripBuilt = true; const L = { 0: 'N', 45: 'NE', 90: 'E', 135: 'SE', 180: 'S', 225: 'SW', 270: 'W', 315: 'NW' }; let h = '';
    for (let d = -360; d <= 720; d += 15) { const dd = ((d % 360) + 360) % 360; h += `<span style="left:${d * PX}px" class="${L[dd] ? (dd % 90 ? 'mid' : 'card') : 'tick'}">${L[dd] || ''}</span>`; } strip.innerHTML = h; }
  const deg = ((head * 180 / Math.PI) % 360 + 360) % 360; strip.style.transform = `translateX(${-deg * PX}px)`;
  if (goal == null || dist < 4) { g.hidden = true; return; }
  let rel = ((goal - head) * 180 / Math.PI) % 360; if (rel > 180) rel -= 360; if (rel < -180) rel += 360;
  g.hidden = false; const half = ($('#wCompass').clientWidth || 300) / 2 - 12, x = Math.max(-half, Math.min(half, rel * PX)); g.style.transform = `translateX(${x}px)`; g.classList.toggle('edge', Math.abs(rel * PX) > half);
  g.querySelector('small').textContent = Math.round(dist) + ' m';
}
/* cinematic cards: the VS reveal before Warden / rival / GLYPH battles and the title card of each new chapter */
function vsCard({ name, role, glyph }) {
  document.querySelector('.vsrev')?.remove(); const d = document.createElement('div'); d.className = 'vsrev' + (glyph ? ' glyph' : '');
  d.innerHTML = `<div class="vs-band"><span class="vs-vs">VS</span><div><small>${esc(role)}</small><b>${esc(name)}</b></div></div>`; document.body.append(d); sfx.charge?.(.7);
  setTimeout(() => d.classList.add('out'), 2300); setTimeout(() => d.remove(), 2900);
}
function whenFree(fn, tries = 240) { const free = !document.body.classList.contains('cine-on') && $('#scene').hidden && $('#wModal').hidden && !document.querySelector('.prolog, .upd'); if (free) fn(); else if (tries > 0) setTimeout(() => whenFree(fn, tries - 1), 500); }
function chapterCard(idx) {
  const ch = QS.STORY[idx]; if (!ch || !document.body.classList.contains('game')) return;
  const d = document.createElement('div'); d.className = 'chcard'; d.style.setProperty('--ac', ch.color || '#ffd257');
  d.innerHTML = `<div class="ch-in"><small>Chapter ${idx + 1} of ${QS.STORY.length} · ${esc(AREA[ch.region] || '')}</small><b class="display">${esc(ch.title)}</b><p>${esc(ch.steps[0]?.text || '')}</p></div>`;
  document.body.append(d); sfx.whoosh?.(.4); const bye = () => { d.classList.add('out'); setTimeout(() => d.remove(), 500); }; d.onclick = bye; setTimeout(bye, 3800);
}
/* first run: the prologue (what Veyra, Echoes and Lattice cards are), then a step-by-step coach for the controls */
const NO_INTRO = /[?&]noprologue/.test(location.search) || (navigator.webdriver && !/[?&]prologue/.test(location.search)); // automated checks skip it unless asked
function wantsPrologue() { const s = P.ensure(), q = QS.Q(); return !NO_INTRO && (s.story.seen.replayIntro || (!s.story.seen.prologue && q.ch === 0 && q.step === 0)); }
let introRunning = false, coach = null;
async function firstSteps(W) {
  if (introRunning) return; const s = P.ensure(); let played = false;
  if (wantsPrologue()) { played = true;
    introRunning = true;
    while (document.body.classList.contains('at-title') || !W.ready) await new Promise(r => setTimeout(r, 250)); // never under the title screen
    s.story.seen.prologue = Date.now(); delete s.story.seen.replayIntro; C.save();
    try { await runPrologue({ W, sfx, music: st().settings.music !== false ? music : null }); } finally { document.body.classList.remove('prolog-on'); introRunning = false; W.refreshStory?.(); }
  }
  document.body.classList.remove('prolog-on');
  if (!s.story.seen.coach && !NO_INTRO && !coach && (played || !s.story.seen.worldIntro)) { // veterans (who saw the old welcome) are not coached again
    coach = startCoach({ W, touch: TOUCH, isBusy: () => !$('#scene').hidden || document.body.classList.contains('cine-on') || !$('#wModal').hidden || $('#worldWrap').hidden || !!document.querySelector('.prolog, #lattice:not([hidden]), #gMenu:not([hidden]), .upd'),
      onDone: () => { s.story.seen.coach = Date.now(); s.story.seen.worldIntro = Date.now(); C.save(); coach = null; } });
  }
}


/* ------------------------------------------------------------------ Lattice device: the Ranger's card device, the hub between Veyra and the card game */
const LAT_APPS = [ // the same five places as the main menu, plus the map and settings
  { k: 'resume', ic: '🌍', t: 'Veyra', s: 'Back to the world' },
  { k: 'map', ic: '🗺️', t: 'Map & Travel', s: 'Relay Express' },
  { k: '#journey', ic: '📜', t: 'Journey', s: 'Story · challenges · ranking' },
  { k: '#collection', ic: '🃏', t: 'Cards', s: 'Cards · binder · team · market' },
  { k: '#shop', ic: '🎁', t: 'Shop', s: 'Card packs & clothes' },
  { k: '#profile', ic: '🧢', t: 'Trainer', s: 'Your look, titles, stats' },
  { k: 'settings', ic: '⚙️', t: 'Settings', s: 'Graphics · sound · controls' },
];
function openLattice() {
  if (document.body.classList.contains('cine-on') || !$('#scene').hidden) return; // finish the scene first
  const L = $('#lattice'), s = P.ensure(), Lv = C.levelInfo(), inWorld = document.body.classList.contains('game');
  world?.setPaused(inWorld); L.hidden = false; sfx.click();
  const q = QS?.Q(), stp = QS?.stepNow(), ch = QS?.chapterNow(), cc = companionCard(), team = (st().team || []).filter(i => st().owned[i]).slice(0, 3);
  L.innerHTML = `<div class="latbox" role="dialog" aria-label="Lattice device">
    <aside class="latme">
      <div class="lathead"><span class="latlogo">◆</span><div><b>LATTICE</b><small>Ranger device · Echo storage</small></div></div>
      <div class="latcard">${av3(s.look, 92)}<div><b>${esc(s.name)}</b><small>Level ${Lv.lv} · ${fmt(st().coins)} coins</small>${rankChip()}
        <span class="xpbar"><i style="width:${(Lv.pct * 100).toFixed(1)}%"></i></span><span class="latseals">${q ? Array.from({ length: 9 }, (_, i) => `<i class="${i < q.seals.length ? 'on' : ''}">◆</i>`).join('') : ''}</span></div></div>
      ${stp ? `<div class="latobj"><small>Chapter ${q.ch + 1} · ${esc(ch.title)}</small><b>${esc(stp.text)}</b></div>` : ''}
      <div class="latteam"><small>Team</small><div>${team.map(i => `<img src="${cardImg(DB.cards[i])}" alt="${esc(DB.cards[i].n)}" title="${esc(DB.cards[i].n)}">`).join('') || '<em>No partners yet</em>'}</div>${cc ? `<small>Walking with <b>${esc(cc.n)}</b></small>` : ''}</div>
    </aside>
    <section class="latapps">${LAT_APPS.map(a => `<button class="latapp" type="button" data-lat="${a.k}"><span>${a.ic}</span><b>${a.t}</b><small>${a.s}</small></button>`).join('')}</section>
    <button class="latx" type="button" aria-label="Close">✕</button>
  </div>`;
  L.querySelector('.latx').onclick = closeLattice;
  L.onclick = e => { if (e.target === L) closeLattice(); };
  $$('#lattice [data-lat]').forEach(b => b.onclick = () => {
    const k = b.dataset.lat; sfx.click();
    if (k === 'resume') { closeLattice(); if (location.hash !== '#world') location.hash = '#world'; return; }
    if (k === 'map') { closeLattice(); if (location.hash !== '#world') location.hash = '#world'; setTimeout(worldTravel, 50); return; }
    if (k === 'settings') { closeLattice(true); openMenu('settings'); return; }
    closeLattice(true); location.hash = k;
  });
}
function closeLattice(keepPaused) {
  const L = $('#lattice'); if (!L || L.hidden) return; L.hidden = true; L.innerHTML = '';
  if (!keepPaused && document.body.classList.contains('game')) { world?.setPaused(false); $('#worldCanvas')?.focus(); }
}
window.__openLattice = openLattice;

/* ------------------------------------------------------------------ Game menu (Esc) — pause, pets, settings, controls, fullscreen */
let menuTab = 'resume';
/* fullscreen is a setting: it stays on until you switch to Windowed in Settings. Esc is captured with the Keyboard Lock API
   (Chrome/Edge: a short Esc reaches the game — opens the menu — instead of leaving fullscreen; holding Esc still exits). */
const PHONE_UI = matchMedia('(pointer: coarse)').matches;
function enterFullscreen() { if (document.fullscreenElement) return; document.documentElement.requestFullscreen?.({ navigationUI: 'hide' }).then(() => navigator.keyboard?.lock?.(['Escape']).catch(() => {})).catch(() => {}); }
function setFullscreen(on) { C.S.settings.fullscreen = !!on; C.save(); if (on) enterFullscreen(); else if (document.fullscreenElement) { navigator.keyboard?.unlock?.(); document.exitFullscreen().catch(() => {}); } }
function toggleFullscreen() { setFullscreen(!document.fullscreenElement); }
/* apply one setting (or all of them at boot) */
function applySettings(k) {
  const S2 = st().settings, all = !k, is = (...ks) => all || ks.includes(k);
  if (!all && ['rscale', 'viewDist', 'grassAmt', 'shadows', 'bloom', 'comic', 'shaderFx'].includes(k)) world?.setQuality();
  if (!all && k === 'autoGfx') world?.setAutoQuality(S2.autoGfx);
  if (!all && k === 'dualScr') { try { window.PokeboxDual?.setEnabled?.(S2.dualScr !== false); } catch {} }
  if (is('volMaster', 'volMusic', 'volSfx')) setVolumes({ master: S2.volMaster ?? 1, music: S2.volMusic ?? 1, sfx: S2.volSfx ?? 1 });
  if (!all && k === 'sound') { setSound(S2.sound); $('#sndBtn')?.classList.toggle('off', !S2.sound); }
  if (is('uiScale')) document.documentElement.style.setProperty('--uis', String(S2.uiScale ?? (PHONE_UI ? 1.1 : 1)));
  if (is('stickSize')) document.documentElement.style.setProperty('--stick', String(S2.stickSize ?? 1));
  if (is('wfps')) { const f = $('#wFps'); if (f) f.hidden = !S2.wfps; }
}
document.addEventListener('fullscreenchange', () => { if (document.fullscreenElement) navigator.keyboard?.lock?.(['Escape']).catch(() => {}); });
for (const ev of ['pointerdown', 'keydown']) addEventListener(ev, () => { if (C.S.settings?.fullscreen && !document.fullscreenElement && !PHONE_UI) enterFullscreen(); }, true);
/* no browser context menu (right click → Inspect…) anywhere in the game, except in text fields */
document.addEventListener('contextmenu', e => { if (!e.target.closest?.('input,textarea,[contenteditable]')) e.preventDefault(); });
function openMenu(tab) {
  const m = $('#gMenu'); menuTab = tab || (document.body.classList.contains('game') ? 'resume' : 'settings');
  world?.setPaused(document.body.classList.contains('game')); m.hidden = false; renderMenu(); sfx.click();
}
function closeMenu() { const m = $('#gMenu'); if (m.hidden) return; m.hidden = true; if (document.body.classList.contains('game')) { world?.setPaused(false); $('#worldCanvas').focus(); } }
function renderMenu() {
  const m = $('#gMenu'), inWorld = document.body.classList.contains('game'), g = gfx(), S2 = st().settings, pets = ensurePets();
  const tabs = [['resume', inWorld ? 'Resume' : 'Close'], ...(inWorld ? [['map', 'Map'], ['pets', 'Partner'], ['respawn', 'Unstuck']] : []), ['settings', 'Settings'], ['controls', 'Controls'], ['fs', document.fullscreenElement ? 'Exit fullscreen' : 'Fullscreen'], ['quit', inWorld ? 'Leave world' : 'Home']];
  let body = '';
  if (menuTab === 'pets') {
    const cur = companionCard(), q = (pets.q || '').toLowerCase();
    const mons = C.ownedCards().filter(C.isMon), team = new Set(st().team);
    const list = mons.filter(c => !q || c.n.toLowerCase().includes(q) || c.t.toLowerCase().includes(q)).sort((a, b) => (team.has(b.i) - team.has(a.i)) || power(b) - power(a)).slice(0, 48);
    body = `<h3 class="display">Partner <small>${mons.length} Pokémon cards</small></h3><p class="muted">The Pokémon on the card you pick steps out and walks with you — cut out of the card art like a sticker. Beat wild Echoes to add more cards.</p>
      <input class="psearch lg" id="petQ" type="search" placeholder="Search name or type…" value="${esc(pets.q || '')}">
      <div class="petgrid cards">${list.map(c => `<button class="petc ${cur?.i === c.i ? 'on' : ''}" data-pcard="${c.i}" type="button" style="--c:${TYPEC[c.t] || '#fff'}"><img src="${cardImg(c)}" alt="" loading="lazy"><b>${esc(c.n)}</b><small>${esc(c.t)}${team.has(c.i) ? ' · team' : ''}</small></button>`).join('') || '<p class="muted">No Pokémon cards yet — open packs first.</p>'}</div>
      <button class="btn ghost sm" id="petNone" type="button">${pets.none ? 'Walk with my partner again' : 'Walk alone'}</button>`;
  } else if (menuTab === 'settings') {
    const sec = S2.setSec || 'gfx', seg = (id, val, opts) => `<div class="seg">${opts.map(([v, l]) => `<button type="button" class="${String(val) === String(v) ? 'on' : ''}" data-set="${id}" data-v="${v}">${l}</button>`).join('')}</div>`;
    const row = (label, ctl, note = '') => `<div class="setrow"><span>${label}${note ? `<small class="muted"> ${note}</small>` : ''}</span>${ctl}</div>`;
    const chk = (id, on) => `<input type="checkbox" data-chk="${id}" ${on ? 'checked' : ''}>`;
    const rng2 = (id, v, min, max, step, fmtv) => `<span class="rng"><input type="range" data-rng="${id}" min="${min}" max="${max}" step="${step}" value="${v}"><b>${fmtv}</b></span>`;
    const secs = [['gfx', 'Graphics'], ['audio', 'Audio'], ['display', 'Display'], ['ctl', 'Controls'], ['about', 'About']];
    let inner = '';
    if (sec === 'gfx') inner = row('Quality preset', `<div class="seg">${['low', 'medium', 'high'].map(q => `<button type="button" class="${g.q === q ? 'on' : ''}" data-gfx="${q}">${q[0].toUpperCase() + q.slice(1)}</button>`).join('')}</div>`)
      + `<p class="muted small">Low: no post-effects or shadows. Medium: shadows, bloom. High: + ambient occlusion, 2K shadows, sharpest image.</p>`
      + row('Render scale', rng2('rscale', Math.round(g.scale * 100), 50, 100, 5, Math.round(g.scale * 100) + '%'), WEAK_GPU ? '(integrated graphics)' : '')
      + row('View distance', seg('viewDist', S2.viewDist ?? 1, [[.75, 'Near'], [1, 'Normal'], [1.3, 'Far']]))
      + row('Grass density', seg('grassAmt', S2.grassAmt ?? 1, [[.5, 'Low'], [1, 'Normal'], [1.3, 'Lush']]))
      + row('Shader look', seg('shaderFx', S2.shaderFx ?? (PHONE_UI ? 1 : 2), [[0, 'Off'], [1, 'Soft'], [2, 'Cinematic']]), 'depth of field, haze, sun rays')
      + row('Real-time shadows', chk('shadows', S2.shadows !== false)) + row('Bloom / glow', chk('bloom', S2.bloom !== false))
      + row('Graphic-novel style (ink, cel bands)', chk('comic', S2.comic !== false))
      + row('Frame-rate limit', seg('fpsCap', S2.fpsCap || 0, [[30, '30'], [60, '60'], [0, 'Max']]), PHONE_UI ? '30 saves battery and heat' : '')
      + row('Auto-lower quality when the frame rate drops', chk('autoGfx', g.auto));
    else if (sec === 'audio') inner = row('Master volume', rng2('volMaster', Math.round((S2.volMaster ?? 1) * 100), 0, 100, 5, Math.round((S2.volMaster ?? 1) * 100) + '%'))
      + row('Music', rng2('volMusic', Math.round((S2.volMusic ?? 1) * 100), 0, 100, 5, Math.round((S2.volMusic ?? 1) * 100) + '%'))
      + row('Sound effects', rng2('volSfx', Math.round((S2.volSfx ?? 1) * 100), 0, 100, 5, Math.round((S2.volSfx ?? 1) * 100) + '%'))
      + row('Sound on', chk('sound', S2.sound)) + row('Character voices (dialogue blips)', chk('voices', S2.voices !== false))
      + `<p class="muted small">Sound pauses by itself when the game is in the background.</p>`;
    else if (sec === 'display') inner = (PHONE_UI ? '' : row('Display mode', seg('dispMode', S2.fullscreen ? 'fs' : 'win', [['fs', 'Fullscreen'], ['win', 'Windowed']]), 'Esc opens the menu, it does not leave fullscreen'))
      + row('Text & menu size', seg('uiScale', S2.uiScale ?? (PHONE_UI ? 1.1 : 1), [[.9, 'S'], [1, 'M'], [1.15, 'L'], [1.3, 'XL']]))
      + row('Dialogue text speed', seg('textSpeed', S2.textSpeed ?? 2, [[1, 'Slow'], [2, 'Normal'], [4, 'Fast'], [999, 'Instant']]))
      + row('Field of view', rng2('fov', g.fov, 45, 85, 1, g.fov + '°')) + row('Camera shake', chk('shake', S2.shake !== false))
      + row('Show FPS counter', chk('wfps', S2.wfps));
    else if (sec === 'ctl') inner = row('Camera sensitivity', rng2('sens', Math.round(g.sens * 10), 3, 25, 1, g.sens.toFixed(1) + '×')) + row('Invert camera Y', chk('invertY', g.inv))
      + (PHONE_UI ? row('Joystick size', seg('stickSize', S2.stickSize ?? 1, [[.85, 'S'], [1, 'M'], [1.2, 'L']])) + row('Vibration', chk('haptics', S2.haptics !== false)) : '');
    else { const di = deviceInfo(); inner = row(`Game version <b>${esc(window.__pbxVersion || '—')}</b>`, '<button class="btn ghost sm" id="mUpd" type="button">Check for updates</button>')
      + (di ? row('Second screen (dual-screen handhelds)', chk('dualScr', di.dual !== false), di.displays?.length > 1 ? `${di.displays.length} displays found` : 'no second display found')
        + `<details class="small muted"><summary>Device &amp; controller info</summary><pre style="white-space:pre-wrap;font-size:11px;user-select:text">${esc(JSON.stringify(di, null, 1))}</pre></details>` : ''); }
    body = `<h3 class="display">Settings</h3><div class="setsec">${secs.map(([k, v]) => `<button type="button" class="${sec === k ? 'on' : ''}" data-sec="${k}">${v}</button>`).join('')}</div>${inner}`;
  } else if (menuTab === 'controls') {
    body = `<h3 class="display">Controls</h3><div class="keys">${[['W A S D / Arrows', 'Move'], ['Shift', 'Run'], ['Space', 'Jump'], ['Q / Ctrl', 'Dodge roll'], ['E / Enter', 'Talk, read, battle'], ['Mouse drag', 'Turn camera'], ['Mouse wheel', 'Zoom'], ['Left click ground', 'Walk there'], ['M / Tab', 'Map & travel'], ['F', 'Fullscreen'], ['Esc', 'Menu / pause'], ['F8', 'Performance meter']].map(([k, v]) => `<div><kbd>${k}</kbd><span>${v}</span></div>`).join('')}</div>`;
  } else {
    const s = P.ensure(), L = C.levelInfo();
    body = `<h3 class="display">${inWorld ? 'Paused' : 'Menu'}</h3><div class="mcard">${av3(s.look, 84)}<div><b>${esc(s.name)}</b><small>Level ${L.lv} · ${fmt(st().coins)} coins · ★${s.stars}</small><small>${inWorld ? esc(AREAS[world?.area]?.name || '') : ''}</small></div></div>
      <div class="mquick"><a class="btn ghost" href="#journey">📜 Journey</a><a class="btn ghost" href="#shop">🛍 Shop</a><a class="btn ghost" href="#battle">⚔ Battle</a><a class="btn ghost" href="#profile">👤 Trainer</a></div>`;
  }
  m.innerHTML = `<div class="gm"><nav>${tabs.map(([k, v]) => `<button type="button" class="gtab ${menuTab === k ? 'on' : ''}" data-mt="${k}">${v}</button>`).join('')}<small class="muted">Esc to ${inWorld ? 'resume' : 'close'}</small></nav><section>${body}</section></div>`;
  $$('#gMenu [data-mt]').forEach(b => b.onclick = () => {
    const k = b.dataset.mt; sfx.click();
    if (k === 'resume') return closeMenu();
    if (k === 'respawn') { closeMenu(); if (world?.indoors) { toast('Step out of the door first.'); return; } sfx.whoosh?.(.4); if (world?.respawnNearest()) toast('Back to the nearest checkpoint.'); return; }
    if (k === 'fs') { toggleFullscreen(); setTimeout(renderMenu, 250); return; }
    if (k === 'map') { closeMenu(); return worldTravel(); }
    if (k === 'quit') { closeMenu(); location.hash = '#home'; return; }
    menuTab = k; renderMenu();
  });
  $$('#gMenu a').forEach(a => a.addEventListener('click', () => closeMenu()));
  $$('#gMenu [data-pcard]').forEach(b => b.onclick = () => { pets.card = +b.dataset.pcard; pets.none = false; C.save(); sfx.click(); world?.refreshPet(); worldPartner = companionCard()?.i ?? null; worldHud(); renderMenu(); });
  const pn = $('#petNone'); if (pn) pn.onclick = () => { pets.none = !pets.none; C.save(); world?.refreshPet(); worldPartner = companionCard()?.i ?? null; worldHud(); renderMenu(); };
  const pq = $('#petQ'); if (pq) { pq.oninput = () => { pets.q = pq.value; clearTimeout(pq._t); pq._t = setTimeout(() => { renderMenu(); const n = $('#petQ'); n?.focus(); n?.setSelectionRange(n.value.length, n.value.length); }, 250); }; pq.onkeydown = e => e.stopPropagation(); }
  $$('#gMenu [data-gfx]').forEach(b => b.onclick = () => { S2.gfx = b.dataset.gfx; C.save(); world?.setQuality(); renderMenu(); });
  const on = (id, fn) => { const el = $(id); if (el) el.oninput = el.onchange = () => { fn(el); C.save(); }; };
  const sc = $('#mScale'); if (sc) { sc.oninput = () => { $('#mScaleV').textContent = sc.value + '%'; }; sc.onchange = () => { S2.rscale = +sc.value / 100; C.save(); world?.setQuality(); }; }
  $$('#gMenu [data-sec]').forEach(b => b.onclick = () => { S2.setSec = b.dataset.sec; sfx.click(); renderMenu(); });
  const applySet = (k, v) => { S2[k] = v; C.save(); applySettings(k); };
  $$('#gMenu [data-set]').forEach(b => b.onclick = () => { const k = b.dataset.set, raw = b.dataset.v, v = isNaN(+raw) ? raw : +raw; sfx.click();
    if (k === 'dispMode') setFullscreen(v === 'fs'); else applySet(k, v); setTimeout(renderMenu, k === 'dispMode' ? 250 : 0); });
  $$('#gMenu [data-chk]').forEach(el => el.onchange = () => applySet(el.dataset.chk, el.checked));
  $$('#gMenu [data-rng]').forEach(el => { const k = el.dataset.rng, out = el.parentElement.querySelector('b');
    const val = () => k === 'rscale' || k.startsWith('vol') ? +el.value / 100 : k === 'sens' ? +el.value / 10 : +el.value;
    const label = () => k === 'fov' ? el.value + '°' : k === 'sens' ? (+el.value / 10).toFixed(1) + '×' : el.value + '%';
    el.oninput = () => { out.textContent = label(); if (k.startsWith('vol') || k === 'fov' || k === 'sens') applySet(k, val()); };
    el.onchange = () => applySet(k, val()); });
  const mu = $('#mUpd'); if (mu) mu.onclick = () => { closeMenu(); manualCheck(m => toast(m)); };
}
window.__androidBack = () => { dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', code: 'Escape' })); };
addEventListener('keydown', e => {
  const inWorld = document.body.classList.contains('game');
  if (e.key === 'Escape') {
    if (!$('#gMenu').hidden) { e.preventDefault(); closeMenu(); return; }
    if (!$('#lattice').hidden) { e.preventDefault(); closeLattice(); return; }
    if (!$('#modal').hidden || !$('#scene').hidden || !$('#opening').hidden || !$('#lvup').hidden) return;
    if (inWorld && !$('#wModal').hidden) { $('#wModal').hidden = true; return; }
    e.preventDefault(); if (inWorld) openLattice(); else if (location.hash !== '#world') location.hash = '#world'; else openMenu();
  }
  if (inWorld && e.code === 'KeyJ' && $('#gMenu').hidden && !e.target.closest?.('input,textarea')) location.hash = '#journey';
  if (inWorld && e.code === 'KeyF' && !e.ctrlKey && !e.target.closest?.('input,textarea') && $('#gMenu').hidden) toggleFullscreen();
});
document.addEventListener('fullscreenchange', () => { world?.resize(); if (!$('#gMenu').hidden) renderMenu(); });

/* ------------------------------------------------------------------ Trainer look editor */
let lookSlot = 'hair';
function trainerCardHTML() {
  const s = P.ensure(), L = C.levelInfo(), fr = P.item('frame', s.look.frame), ti = P.item('title', s.look.title);
  return `<div class="tcard" style="--fr:${fr.bg}"><div class="tcin">
    <div class="tcav">${av3(s.look, 190)}</div>
    <div class="tcinfo"><div class="eyebrow">${esc(ti.name)}</div><input class="tcname" id="tName" maxlength="16" value="${esc(s.name)}" aria-label="Trainer name">
      <div class="tclv"><span class="lvl">${L.lv}</span><div class="xpbar"><i style="width:${(L.pct * 100).toFixed(1)}%"></i></div></div>
      <div class="tcst"><div><b>${s.packs}</b><small>packs</small></div><div><b>${s.battle.wins}</b><small>wins</small></div><div><b>${fmt(C.uniqueCount())}</b><small>cards</small></div><div><b>★${s.stars}</b><small>stars</small></div><div><b>${Math.min(s.story.ch, 7)}/7</b><small>chapters</small></div></div></div>
  </div></div>`;
}
function lookEditorHTML() {
  const s = P.ensure(), items = P.ITEMS.filter(i => i.slot === lookSlot);
  const prev = it => { if (lookSlot === 'frame') return `<span class="fsw" style="background:${it.bg}"></span>`; if (lookSlot === 'title') return `<span class="tsw">${esc(it.name)}</span>`;
    return P.avatarSVG({ ...s.look, [lookSlot]: it.id }, { size: 74, bg: false }); };
  return `<div class="ledit"><div class="ltabs">${P.SLOTS.map(sl => `<button class="fchip ${sl.id === lookSlot ? 'on' : ''}" data-slot="${sl.id}" type="button">${sl.name}</button>`).join('')}</div>
    <div class="lgrid">${items.map(it => { const un = P.isUnlocked(it), on = s.look[lookSlot] === it.id;
      return `<button class="litem ${on ? 'on' : ''} ${un ? '' : 'locked'}" data-look="${it.id}" type="button" ${un ? '' : 'aria-disabled="true"'} title="${esc(un ? it.name : '🔒 ' + P.unlockReason(it.u))}">
        <span class="lprev">${prev(it)}</span><b>${esc(it.name)}</b>${un ? '' : `<small>🔒 ${esc(P.unlockReason(it.u))}</small>`}</button>`; }).join('')}</div></div>`;
}
function bindLook() {
  $$('[data-slot]').forEach(b => b.onclick = () => { lookSlot = b.dataset.slot; sfx.click(); $('#lookBox').innerHTML = lookEditorHTML(); bindLook(); });
  $$('[data-look]').forEach(b => b.onclick = () => { const it = P.item(lookSlot, b.dataset.look); if (!P.isUnlocked(it)) { toast('🔒 ' + esc(P.unlockReason(it.u)), 'err'); return; }
    P.ensure().look[lookSlot] = it.id; C.save(); sfx.click(); preview3d()?.set({ ...P.ensure().look }, { cheer: true }); $('#tcBox').innerHTML = trainerCardHTML(); $('#lookBox').innerHTML = lookEditorHTML(); bindLook(); bindName(); updateTop(); });
}
let prev3d = null;
function preview3d() { const box = $('#t3d'); if (!box) return null; // one renderer for the whole session, its canvas is re-parented
  if (!prev3d) { const c = document.createElement('canvas'); c.setAttribute('aria-label', '3D preview of your trainer'); prev3d = createPreview(c); prev3d.canvas = c; }
  if (prev3d.canvas.parentNode !== box) box.prepend(prev3d.canvas); prev3d.attach(prev3d.canvas); return prev3d; }
function bindName() { const n = $('#tName'); if (n) n.onchange = () => { P.ensure().name = n.value.trim().slice(0, 16) || 'Ranger'; C.save(); }; }

VIEWS.profile = () => {
  const s = st(), best = s.stats.best != null ? DB.cards[s.stats.best] : null;
  P.newlyUnlocked();
  view.innerHTML = `<section class="wrap"><div class="sech"><div><div class="eyebrow">Trainer</div><h2 class="display">Your look</h2></div><p class="muted">Unlock more with levels, Journey chapters, challenge stars, the battle ladder and binder sets.</p></div>
    <div class="tprof"><div class="tcol"><div id="tcBox">${trainerCardHTML()}</div><div class="t3d" id="t3d"><small>How you look in the 3D world · drag to turn</small></div></div><div id="lookBox">${lookEditorHTML()}</div></div></section>
  <section class="wrap"><div class="tiles"><div class="tile"><div class="eyebrow">Coins earned</div><h3>${fmt(s.stats.earned)}</h3></div><div class="tile"><div class="eyebrow">Coins spent</div><h3>${fmt(s.stats.spent)}</h3></div>
    <div class="tile"><div class="eyebrow">Packs opened</div><h3>${s.packs}</h3></div><div class="tile"><div class="eyebrow">Best pull</div><h3 class="small">${best ? `<a href="#" data-card="${best.i}">${esc(best.n)}</a>` : '—'}</h3></div></div></section>
  <section class="wrap"><div class="eyebrow">Achievements</div><div class="achs">${C.ACH.map(a => `<div class="ach ${s.ach[a.id] ? 'got' : ''}"><b>${esc(a.name)}</b><small>${esc(a.desc)}</small><span class="gold">+${fmt(a.reward)}</span></div>`).join('')}</div></section>
  <section class="wrap"><div class="eyebrow">Card quality</div>
    <div class="hdbox"><b>${DB.hd ? 'HD cards: ON' : 'HD cards: not installed'}</b><span class="muted">${DB.hd ? 'Upscaled images are used in the 3D opening and card viewer.' : 'Run <b>tools\\upscale_cards.bat</b> once to create sharp 2×/4× versions of all cards (uses your graphics card).'}</span></div></section>
  <section class="wrap"><div class="eyebrow">Settings</div><div class="settings">
    <label><input type="checkbox" id="setSound" ${s.settings.sound ? 'checked' : ''}> Sound effects</label>
    <label><input type="checkbox" id="setMusic" ${s.settings.music !== false ? 'checked' : ''}> Music &amp; ambience in the world</label>
    <label><input type="checkbox" id="setMystery" ${s.settings.mystery ? 'checked' : ''}> White mystery pack intro (from the reference animation)</label>
    <label><input type="checkbox" id="setFast" ${s.settings.fast ? 'checked' : ''}> Skip the 3D animation (instant results)</label>
    <label><input type="checkbox" id="setFps" ${s.settings.fps ? 'checked' : ''}> Show performance meter (FPS + graphics card) — shortcut F8</label>
    <label><input type="checkbox" id="setShadows" ${s.settings.shadows !== false ? 'checked' : ''}> 3D world: real-time shadows (turn off on weak graphics cards)</label>
    <label><input type="checkbox" id="setHitFx" ${s.settings.hitFx !== false ? 'checked' : ''}> Signature openings for big hits (Ultra Rare → thunder, Illustration → candy rain, Secret → ascension)</label>
    <label>Opening studio <select id="setStudio"><option value="studio" ${s.settings.studio === 'studio' ? 'selected' : ''}>Pink studio (GIF)</option><option value="dark" ${s.settings.studio === 'dark' ? 'selected' : ''}>Dark Pokebox</option></select></label>
  </div>
  <div class="row"><button class="btn ghost" id="exp" type="button">Export save</button><label class="btn ghost" for="imp">Import save</label><input type="file" id="imp" accept=".json,application/json" hidden>
  <button class="btn ghost" id="copyCode" type="button">Copy save code</button><button class="btn ghost" id="pasteCode" type="button">Paste save code</button>
  <button class="btn ghost" id="replayIntro" type="button">Replay intro</button><button class="btn danger" id="reset" type="button">Reset progress</button></div><p class="muted" id="resetMsg"></p>
  <div class="bklist"><div class="eyebrow">Automatic backups on this device</div>${C.backups().map((b, i) => `<button class="btn sm ghost" type="button" data-bk="${i}">Restore ${new Date(b.t).toLocaleString()} · ${fmt(b.coins || 0)} coins</button>`).join('') || '<span class="muted small">The first backup is made after 15 minutes of play.</span>'}
  <p class="muted small">Your save lives on this device. To keep it safe or move it to another phone/PC, use <b>Copy save code</b> and paste it somewhere safe (notes, a message to yourself).</p></div></section>`;
  bindLook(); bindName(); preview3d()?.set({ ...P.ensure().look });
  $('#setSound').onchange = e => { s.settings.sound = e.target.checked; setSound(e.target.checked); C.save(); };
  $('#setMusic').onchange = e => { s.settings.music = e.target.checked; setMusic(e.target.checked); if (e.target.checked && document.body.classList.contains('game')) music.world(...musRegion); C.save(); };
  $('#setMystery').onchange = e => { s.settings.mystery = e.target.checked; C.save(); };
  $('#copyCode').onclick = async () => { const code = C.saveCode(); try { await navigator.clipboard.writeText(code); toast('Save code copied — paste it somewhere safe.'); } catch { openModalText('Your save code', code); } };
  $('#pasteCode').onclick = () => openModalText('Paste a save code', '', code => { try { C.loadSaveCode(code); toast('Save restored.'); route(); } catch (e) { toast('That code is not a Pokebox save.', 'err'); } });
  $$('[data-bk]').forEach(b => b.onclick = () => { if (!confirmTwice(b)) return; if (C.restoreBackup(+b.dataset.bk)) { toast('Backup restored.'); route(); } });
  $('#replayIntro').onclick = () => { s.story.seen.replayIntro = 1; C.save(); location.hash = '#world'; };
  $('#setFast').onchange = e => { s.settings.fast = e.target.checked; C.save(); };
  $('#setFps').onchange = e => { s.settings.fps = e.target.checked; C.save(); window.__perfHud?.(e.target.checked); };
  $('#setShadows').onchange = e => { s.settings.shadows = e.target.checked; C.save(); toast('Applies the next time the game starts.'); };
  $('#setHitFx').onchange = e => { s.settings.hitFx = e.target.checked; C.save(); };
  $('#setStudio').onchange = e => { s.settings.studio = e.target.value; C.save(); };
  $('#exp').onclick = () => { const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([C.exportSave()], { type: 'application/json' })); a.download = `pokebox-save-${C.today()}.json`; a.click(); };
  $('#imp').onchange = async e => { try { C.importSave(await e.target.files[0].text()); toast('Save imported.'); route(); } catch (err) { toast(esc(err.message), 'err'); } };
  let armed = false; $('#reset').onclick = () => { if (!armed) { armed = true; $('#reset').textContent = 'Click again to erase everything'; $('#resetMsg').textContent = 'This deletes your coins, cards and progress.'; return; } C.resetSave(); toast('Progress reset.'); route(); };
};

/* ------------------------------------------------------------------ ambient background */
// the animated space background was replaced by a still comic sky (css/comic-ui.css): saves battery and GPU on phones

/* F3 = performance overlay (fps, frame time, GPU) — for diagnosing lag on a given machine */
(function perfHud() {
  let el = null, on = false, n = 0, acc = 0, worst = 0, last = 0;
  const gpu = (() => { try { const g = document.createElement('canvas').getContext('webgl'), d = g.getExtension('WEBGL_debug_renderer_info'); return d ? g.getParameter(d.UNMASKED_RENDERER_WEBGL) : 'unknown'; } catch { return 'no WebGL'; } })();
  function tick(now) { if (!on) return; requestAnimationFrame(tick); const dt = now - last; last = now; if (dt < 500) { acc += dt; n++; worst = Math.max(worst, dt); }
    if (acc > 500) { el.textContent = `${Math.round(1000 * n / acc)} fps · avg ${(acc / n).toFixed(1)} ms · worst ${worst.toFixed(0)} ms · ${devicePixelRatio}x · ${innerWidth}×${innerHeight}\n${gpu}`; n = 0; acc = 0; worst = 0; } }
  const toggle = (force) => { on = force ?? !on;
    if (on) { el ||= Object.assign(document.createElement('pre'), { className: 'perfhud' }); document.body.append(el); last = performance.now(); requestAnimationFrame(tick); } else el?.remove(); };
  // F8 or the ` key (F3 is taken by the browser's Find), or Profile → Settings
  addEventListener('keydown', e => { if (e.key === 'F8' || e.key === '`' || (e.ctrlKey && e.shiftKey && e.code === 'KeyF')) { e.preventDefault(); toggle(); st().settings.fps = on; C.save(); } });
  window.__perfHud = toggle; setTimeout(() => { if (st().settings.fps) toggle(true); }, 500);
})();

$('#wMap').onclick = () => worldTravel();
/* hover ticks + hud buttons */
document.addEventListener('pointerover', e => { const b = e.target.closest?.('.btn,.rail a,.fchip,.mode'); if (b && b !== document.__lastHover) { document.__lastHover = b; sfx.tick?.(); } });
$('#sndBtn').onclick = () => { st().settings.sound = !st().settings.sound; setSound(st().settings.sound); if (!st().settings.sound) music.world(null); else if (document.body.classList.contains('game')) music.world(...musRegion); $('#sndBtn').classList.toggle('off', !st().settings.sound); C.save(); };
$('#fsBtn').onclick = () => toggleFullscreen();

/* ------------------------------------------------------------------ boot */
(async () => {
  const bar = $('#spBar'), msg = $('#spMsg'); let fake = 0; const ft = setInterval(() => { fake = Math.min(85, fake + 7); bar.style.width = fake + '%'; }, 120);
  try { await C.loadDB(); }
  catch (e) { clearInterval(ft); msg.innerHTML = 'Could not load the card database.<br>Start the game with <b>Pokebox.exe</b> (or start.bat).'; return; }
  msg.textContent = 'Checking HD cards…'; await C.detectHD();
  clearInterval(ft); bar.style.width = '100%'; msg.textContent = `${fmt(DB.cards.length)} cards · ${DB.sets.length} sets${DB.hd ? ' · HD' : ''}`;
  setSound(st().settings.sound); setMusic(st().settings.music !== false); applySettings(); $('#sndBtn').classList.toggle('off', !st().settings.sound);
  C.snapshotValue(); P.ensure(); P.newlyUnlocked(); lastReady = P.readyCount(); route(); achievements();
  const start = () => { $('#splash').classList.add('out'); sfx.burst(); const d = C.dailyState(); if (d.ready) setTimeout(() => toast('🎁 Your daily reward is ready — <a href="#home" class="gold">Home ▸</a>'), 700); if (!P.ensure().story.done[1] && !location.hash.startsWith('#journey')) setTimeout(() => toast('📜 Your Journey in Veyra begins — <a href="#journey" class="gold">open Journey ▸</a>'), 1600); };
  const qp = new URLSearchParams(location.search);
  if (qp.has('nosplash')) start(); // tests
  else { // title screen / main menu (Pokebox.exe and the Android app land here too); the world keeps loading behind it
    $('#splash').classList.add('out');
    const worldReady = new Promise(res => { const t0 = Date.now(); (function poll() { if (window.__world?.ready || Date.now() - t0 > 45000) res(); else setTimeout(poll, 300); })(); });
    const prog = P.ensure(); const hasProgress = !!(QS?.Q?.().ch || QS?.Q?.().step || prog.story?.done?.[1]);
    runTitle({ touch: TOUCH, hasProgress, ready: worldReady,
      onStart: () => { document.body.classList.add('ingame'); if (location.hash && location.hash !== '#world') location.hash = '#world'; start(); },
      onCards: () => { document.body.classList.add('ingame'); start(); location.hash = '#collection'; },
      onSettings: () => { document.body.classList.add('ingame'); start(); location.hash = '#world'; setTimeout(() => openMenu('settings'), 400); } });
  }
  window.__pbxTest = { showLevelUp, chooseStarter, worldConfirm, worldTravel, openCard, openPack, openMenu, openLattice, playScene, toast }; // used by the automated UI checks
  window.__ready = true;
  setTimeout(autoCheck, 3500); // new version on GitHub? ask the player (never during the first seconds)
  // after an update: show once what changed, so the player can see the new version really arrived (PC and Android)
  (async () => { try {
    const v = await (await fetch('version.json', { cache: 'no-store' })).json(); let seen = null; try { seen = localStorage.getItem('pbxSeenVer'); } catch {}
    try { localStorage.setItem('pbxSeenVer', v.version); } catch {}
    if (!seen || seen === v.version || !v.notes?.length) return;
    while (document.body.classList.contains('at-title') || document.querySelector('.upd')) await new Promise(r => setTimeout(r, 600));
    const box = document.createElement('div'); box.className = 'upd'; box.innerHTML = `<div class="updbox"><div class="eyebrow">Updated ${esc(seen)} → <b>${esc(v.version)}</b></div><h3 class="display">What's new</h3><ul>${v.notes.map(n => `<li>${esc(n)}</li>`).join('')}</ul><div class="row"><button class="btn gold" type="button">Let's go</button></div></div>`;
    document.body.append(box); box.querySelector('button').onclick = () => box.remove();
  } catch { /* no version file: nothing to show */ } })();
  if (!IS_APP) setInterval(() => fetch('/__ping').catch(() => {}), 20000);
  // flush the save when the window closes or the phone app goes to the background (Android may kill it there)
  const flush = () => { try { const p = world?.player?.group.position; if (p) P.ensure().world.pos = { v2: 1, x: p.x, z: p.z }; } catch {} C.save(true); };
  window.__pbxFlush = flush;
  addEventListener('pagehide', flush); document.addEventListener('visibilitychange', () => { if (document.hidden) flush(); });
  setInterval(flush, 30000);   // keeps the local server alive while the window is open
})();

/* liquid glass: specular highlight follows the pointer */
addEventListener('pointermove', e => { const t = e.target.closest?.('.ibtn,.res,.wb,.btn.ghost,.gtab,.mv,.lg'); if (!t) return; const r = t.getBoundingClientRect();
  t.style.setProperty('--mx', ((e.clientX - r.left) / r.width * 100).toFixed(0) + '%'); t.style.setProperty('--my', ((e.clientY - r.top) / r.height * 100).toFixed(0) + '%'); }, { passive: true });

/* grouped pages keep their tabs even when a page redraws itself (claim buttons, filters…) */
for (const n of Object.keys(GROUP_OF)) { const f = VIEWS[n]; if (f) VIEWS[n] = (...a) => { const r = f(...a); subnav(n); return r; }; }
