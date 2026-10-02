// Pokebox — data, save state, economy, market
import { PREMIUM, packURL } from './packart.js';
export const CARD_DIR = '../pokemon-card-scraper/pokemon_cards/images/';
export const SET_DIR = 'assets/sets/';
export const RARITY = ['Common', 'Uncommon', 'Rare', 'Holo Rare', 'Ultra Rare', 'Illustration Rare', 'Secret Rare'];
export const RSHORT = ['C', 'U', 'R', 'H', 'UR', 'IR', 'SR'];
export const RCOLOR = ['#9c9486', '#7fb38a', '#6fa8dc', '#8fe0d6', '#c9a4ff', '#ff9ecb', '#ffd257'];
export const TYPES = ['Grass', 'Fire', 'Water', 'Lightning', 'Psychic', 'Fighting', 'Darkness', 'Metal', 'Dragon', 'Colorless'];
export const TCOLOR = { Grass: '#5fae4f', Fire: '#e8603c', Water: '#3d8fd6', Lightning: '#f2c230', Psychic: '#b05fc9', Fighting: '#b5673a',
  Darkness: '#3f4a5a', Metal: '#8e9aa6', Dragon: '#c29a2c', Colorless: '#c9c2b0', Trainer: '#6d6a63', Energy: '#4f7f6f' };

export const DB = { sets: [], setBy: {}, cards: [], bySet: {}, ready: false, hd: false };

export async function loadDB() {
  const [s, c] = await Promise.all([fetch('data/sets.json').then(r => r.json()), fetch('data/cards.json').then(r => r.json())]);
  DB.sets = s.sets.sort((a, b) => a.order - b.order);
  DB.sets.forEach(x => (DB.setBy[x.code] = x));
  const K = c.keys;
  DB.cards = c.rows.map(r => { const o = {}; K.forEach((k, i) => (o[k] = r[i])); return o; });
  for (const card of DB.cards) (DB.bySet[card.s] ||= []).push(card);
  for (const code in DB.bySet) DB.bySet[code].byR = [0, 1, 2, 3, 4, 5, 6].map(r => DB.bySet[code].filter(x => x.r === r));
  DB.ready = true;
}
export const CARD_HD_DIR = '../pokemon-card-scraper/pokemon_cards/images_hd/';
export const cardImg = c => CARD_DIR + encodeURIComponent(c.f);
export const cardHD = c => DB.hd ? CARD_HD_DIR + encodeURIComponent(c.f.replace(/\.[a-z]+$/i, '.webp')) : null;
export async function detectHD() {
  // HD = Real-ESRGAN upscaled copies made by tools/upscale_cards.bat; used automatically when present
  try { DB.hd = true; const probe = DB.cards.find(c => c.s === 'PFL') || DB.cards[0]; const r = await fetch(cardHD(probe), { method: 'HEAD' }); DB.hd = r.ok; } catch { DB.hd = false; }
  return DB.hd;
}
export const setImg = (s, k) => (s.img && s.img[k] ? SET_DIR + s.img[k] : null);
export const isMon = c => c.t !== 'Trainer' && c.t !== 'Energy';

/* ------------------------------------------------------------------ rng */
export function hash(str) { let h = 2166136261; for (let i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; }
export function rng(seed) { let s = seed >>> 0; return () => ((s = (Math.imul(s, 1664525) + 1013904223) >>> 0) / 4294967296); }
export const today = (d = new Date()) => d.toISOString().slice(0, 10);
export const dayNum = (d = new Date()) => Math.floor((d.getTime() - d.getTimezoneOffset() * 60000) / 86400000);

/* ------------------------------------------------------------------ market */
export function marketMult(i, day = dayNum()) {
  const p1 = (i * 12.9898) % 6.283, p2 = (i * 78.233) % 6.283, p3 = (i * 3.137) % 6.283;
  const n = .13 * Math.sin(day * .21 + p1) + .08 * Math.sin(day * .57 + p2) + .05 * Math.sin(day * 1.9 + p3);
  return Math.exp(n);
}
export const price = (c, day) => Math.max(1, Math.round(c.v * marketMult(c.i, day)));
export const sellPrice = (c) => Math.max(1, Math.floor(price(c) * .9));
export const buyPrice = (c) => Math.ceil(price(c) * 1.2);
export function priceHistory(c, days = 30) { const d = dayNum(); return Array.from({ length: days }, (_, k) => price(c, d - days + 1 + k)); }

/* ------------------------------------------------------------------ pack generation */
const HIT = [[2, .60], [3, .22], [4, .105], [5, .05], [6, .025]];
function pickFrom(list, R) { return list[Math.floor(R() * list.length)]; }
function pickRarity(byR, r, R) { let k = r; while (k >= 0 && !byR[k].length) k--; if (k < 0) { k = r; while (k < 7 && !byR[k].length) k++; } return pickFrom(byR[k], R); }
export function rollPack(code, R = Math.random) {
  const byR = DB.bySet[code].byR, out = [];
  for (let i = 0; i < 3; i++) out.push(pickRarity(byR, 0, R));
  for (let i = 0; i < 2; i++) out.push(pickRarity(byR, 1, R));
  // reverse-holo style bonus slot: any card from the set, weighted to lower rarities
  const x = R(); out.push(pickRarity(byR, x < .6 ? 1 : x < .9 ? 2 : 3, R));
  let roll = R(), hr = 2; for (const [r, p] of HIT) { if (roll < p) { hr = r; break; } roll -= p; }
  out.push(pickRarity(byR, hr, R));
  return out; // 7 cards, hit last
}

/* ------------------------------------------------------------------ vault (premium) packs */
export const VAULT = PREMIUM, vaultBy = Object.fromEntries(PREMIUM.map(p => [p.code, p]));
export const vaultArt = p => packURL(p.art), vaultUpgrade = p => p.upgrade ? packURL(p.upgrade) : null;
const THEME_R = {};
// themed pool per vault pack: only Pokémon (no Trainer/Energy), and ~90% from the pack's own types
function themeByR(code) {
  if (THEME_R[code]) return THEME_R[code];
  const p = vaultBy[code], mons = DB.cards.filter(c => DB.setBy[c.s]?.sellable && isMon(c));
  const split = f => [0, 1, 2, 3, 4, 5, 6].map(r => mons.filter(c => c.r === r && f(c)));
  return (THEME_R[code] = { theme: split(c => p.types.includes(c.t)), any: split(() => true) });
}
function pickThemed(code, r, R) { const T = themeByR(code); return pickRarity(R() < .9 ? T.theme : T.any, r, R); }
export function rollVault(code, R = Math.random) {
  const p = vaultBy[code], out = [];
  for (let i = 0; i < 3; i++) out.push(pickThemed(code, 0, R));
  for (let i = 0; i < 2; i++) out.push(pickThemed(code, 1, R));
  for (let i = 0; i < 2; i++) out.push(pickThemed(code, R() < .6 ? 2 : 3, R));
  for (let i = 0; i < 3; i++) { let roll = R(), hr = p.odds[0][0]; for (const [r, q] of p.odds) { if (roll < q) { hr = r; break; } roll -= q; } out.push(pickThemed(code, hr, R)); }
  const hits = out.splice(7).sort((a, b) => a.r - b.r || a.v - b.v); out.push(...hits);
  return out; // 10 cards, best last
}
export function vaultLeft(code) {
  const p = vaultBy[code], d = dayNum(), f = (hash(code + d) % 1000) / 1000, hour = new Date().getHours() / 24;
  const sold = Math.floor(p.stock * (.2 + .45 * f) * (.4 + .6 * hour)) + ((S.vault || {})[code + ':' + d] || 0);
  return Math.max(0, p.stock - sold);
}
export function vaultBuy(code) { S.vault ||= {}; const k = code + ':' + dayNum(); S.vault[k] = (S.vault[k] || 0) + 1; save(); }
export function vaultEV(code) {
  const p = vaultBy[code], byR = themeByR(code).theme, avg = r => byR[r].reduce((a, c) => a + c.v, 0) / Math.max(1, byR[r].length);
  return Math.round(avg(0) * 3 + avg(1) * 2 + (avg(2) * .6 + avg(3) * .4) * 2 + 3 * p.odds.reduce((a, [r, q]) => a + avg(r) * q, 0));
}

/* ------------------------------------------------------------------ save */
const KEY = 'pokebox.save.v1';
const fresh = () => ({
  v: 1, coins: 750, tokens: 1, created: Date.now(), lastDaily: null, streak: 0,
  xp: 0, owned: {}, first: {}, packs: 0, pulls: [], history: [], team: [], fav: {},
  battle: { wins: 0, losses: 0, beaten: {} }, ach: {}, claimed: {}, stats: { spent: 0, earned: 0, best: null },
  settings: { sound: true, studio: 'studio', mystery: true, fast: false, hitFx: true }, vault: {},
});
export let S = fresh();
export function load() {
  try { const j = JSON.parse(localStorage.getItem(KEY)); if (j && j.v === 1) S = Object.assign(fresh(), j, { settings: Object.assign(fresh().settings, j.settings) }); } catch {}
  return S;
}
let saveT;
export function save(now = false) {
  clearTimeout(saveT);
  const w = () => { try { localStorage.setItem(KEY, JSON.stringify(S)); } catch {} };
  now ? w() : (saveT = setTimeout(w, 250));
}
export function resetSave() { S = fresh(); save(true); }
export function exportSave() { return JSON.stringify(S); }
export function importSave(txt) { const j = JSON.parse(txt); if (!j || j.v !== 1) throw new Error('Not a Pokebox save file'); S = Object.assign(fresh(), j); save(true); }

/* ------------------------------------------------------------------ economy helpers */
const listeners = new Set();
export const onChange = fn => (listeners.add(fn), () => listeners.delete(fn));
export const emit = (what) => listeners.forEach(fn => fn(what));

export function addCoins(n, why) { S.coins += n; if (n > 0) S.stats.earned += n; else S.stats.spent -= n; save(); emit('coins'); }
export function addCard(c) {
  const isNew = !S.owned[c.i];
  S.owned[c.i] = (S.owned[c.i] || 0) + 1;
  if (isNew) S.first[c.i] = Date.now();
  if (!S.stats.best || c.v > (DB.cards[S.stats.best]?.v || 0)) S.stats.best = c.i;
  save(); return isNew;
}
export function removeCard(c, n = 1) {
  const have = S.owned[c.i] || 0; if (have < n) return false;
  if (have === n) { delete S.owned[c.i]; S.team = S.team.filter(i => i !== c.i); } else S.owned[c.i] = have - n;
  save(); emit('cards'); return true;
}
export function ownedCards() { return Object.keys(S.owned).map(i => DB.cards[+i]); }
export function collectionValue() { let v = 0; for (const i in S.owned) v += price(DB.cards[+i]) * S.owned[i]; return v; }
export function uniqueCount() { return Object.keys(S.owned).length; }
export function setProgress(code) { const l = DB.bySet[code] || []; let n = 0; for (const c of l) if (S.owned[c.i]) n++; return { have: n, total: l.length }; }
export function snapshotValue() {
  const d = today(), v = collectionValue(), h = S.history;
  if (h.length && h[h.length - 1].d === d) h[h.length - 1].v = v; else h.push({ d, v });
  if (h.length > 120) h.splice(0, h.length - 120);
  save();
}

/* daily reward: coins scale with streak, plus a free pack token */
export function dailyState() {
  const t = today(); if (S.lastDaily === t) return { ready: false };
  const y = today(new Date(Date.now() - 86400000));
  const streak = S.lastDaily === y ? S.streak + 1 : 1;
  return { ready: true, streak, coins: 200 + 50 * Math.min(streak, 7) };
}
export function claimDaily() {
  const d = dailyState(); if (!d.ready) return null;
  S.lastDaily = today(); S.streak = d.streak; S.tokens += 1; addCoins(d.coins, 'daily'); save(true);
  return d;
}

/* achievements */
export const ACH = [
  { id: 'pack1', name: 'First rip', desc: 'Open your first pack', reward: 100, test: () => S.packs >= 1 },
  { id: 'pack25', name: 'Pack addict', desc: 'Open 25 packs', reward: 500, test: () => S.packs >= 25 },
  { id: 'pack100', name: 'Box breaker', desc: 'Open 100 packs', reward: 2000, test: () => S.packs >= 100 },
  { id: 'ultra', name: 'Big hit', desc: 'Pull an Ultra Rare or better', reward: 250, test: () => ownedCards().some(c => c.r >= 4) },
  { id: 'secret', name: 'Chase card', desc: 'Pull a Secret Rare', reward: 750, test: () => ownedCards().some(c => c.r === 6) },
  { id: 'u100', name: 'Collector', desc: 'Own 100 different cards', reward: 400, test: () => uniqueCount() >= 100 },
  { id: 'u1000', name: 'Archivist', desc: 'Own 1,000 different cards', reward: 3000, test: () => uniqueCount() >= 1000 },
  { id: 'val5k', name: 'Portfolio', desc: 'Collection worth 5,000 coins', reward: 500, test: () => collectionValue() >= 5000 },
  { id: 'win1', name: 'First win', desc: 'Win a battle', reward: 150, test: () => S.battle.wins >= 1 },
  { id: 'win10', name: 'Gym regular', desc: 'Win 10 battles', reward: 800, test: () => S.battle.wins >= 10 },
  { id: 'champ', name: 'Champion', desc: 'Beat the Champion', reward: 2500, test: () => !!S.battle.beaten[7] },
  { id: 'set', name: 'Set master', desc: 'Complete any set', reward: 1500, test: () => DB.sets.some(s => { const p = setProgress(s.code); return p.total && p.have === p.total; }) },
];
export function checkAch() {
  const got = [];
  for (const a of ACH) if (!S.ach[a.id] && a.test()) { S.ach[a.id] = Date.now(); addCoins(a.reward, 'ach'); got.push(a); }
  if (got.length) save(true);
  return got;
}

/* trainer level: xp from packs, pulls and battles */
export const levelOf = xp => Math.floor(Math.sqrt(xp / 40)) + 1;
export const xpFor = lv => (lv - 1) * (lv - 1) * 40;
export function levelInfo() { const lv = levelOf(S.xp || 0), a = xpFor(lv), b = xpFor(lv + 1); return { lv, cur: (S.xp || 0) - a, need: b - a, pct: ((S.xp || 0) - a) / (b - a) }; }
export function gainXP(n) {
  const before = levelOf(S.xp || 0); S.xp = (S.xp || 0) + n; const after = levelOf(S.xp);
  const ups = [];
  for (let lv = before + 1; lv <= after; lv++) { const coins = 100 * lv, token = lv % 5 === 0 ? 1 : 0; S.coins += coins; S.stats.earned += coins; S.tokens += token; ups.push({ lv, coins, token }); }
  save(); emit('xp'); return ups;
}

/* formatting */
export const fmt = n => Math.round(n).toLocaleString('en-US');
export const esc = s => String(s).replace(/[&<>"']/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
