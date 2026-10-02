// Pokebox — Ranger Rank: an offline ranking. Every battle, capture and discovery earns Rank Points (RP);
// ranks Rookie → Bronze → Silver → Gold → Platinum → Diamond → Master → Champion League, with rewards on every promotion.
// The leaderboard puts you between the trainers of Veyra (their RP grows with the story, so the race stays alive).
import * as C from './core.js';

export const RANKS = [
  { id: 'rookie', name: 'Rookie', rp: 0, col: '#9aa3b5', reward: 0 },
  { id: 'b1', name: 'Bronze I', rp: 100, col: '#c97a3c', reward: 300 }, { id: 'b2', name: 'Bronze II', rp: 220, col: '#c97a3c', reward: 350 }, { id: 'b3', name: 'Bronze III', rp: 360, col: '#c97a3c', reward: 400 },
  { id: 's1', name: 'Silver I', rp: 520, col: '#b8c4d6', reward: 500 }, { id: 's2', name: 'Silver II', rp: 700, col: '#b8c4d6', reward: 550 }, { id: 's3', name: 'Silver III', rp: 900, col: '#b8c4d6', reward: 600 },
  { id: 'g1', name: 'Gold I', rp: 1150, col: '#f2c230', reward: 800 }, { id: 'g2', name: 'Gold II', rp: 1420, col: '#f2c230', reward: 850 }, { id: 'g3', name: 'Gold III', rp: 1720, col: '#f2c230', reward: 900 },
  { id: 'p', name: 'Platinum', rp: 2100, col: '#5cf2d6', reward: 1200 }, { id: 'd', name: 'Diamond', rp: 2600, col: '#7fb8ff', reward: 1600 },
  { id: 'm', name: 'Master', rp: 3300, col: '#c46bff', reward: 2200 }, { id: 'c', name: 'Champion League', rp: 4200, col: '#ff5a7a', reward: 3500 },
];
const R = () => (C.S.rank ||= { rp: 0, best: 0, log: [] });
export const rp = () => R().rp;
export function rankOf(p = rp()) { let r = RANKS[0]; for (const k of RANKS) if (p >= k.rp) r = k; return r; }
export function nextRank(p = rp()) { return RANKS.find(k => k.rp > p) || null; }
export function progress(p = rp()) { const a = rankOf(p), b = nextRank(p); return b ? (p - a.rp) / (b.rp - a.rp) : 1; }
let onPromote = null; export const setPromoteHook = fn => { onPromote = fn; };
/** add (or remove) Rank Points; a rank never drops below the floor of the best tier reached (no frustrating demotions) */
export function add(n, why = '') {
  const s = R(), before = rankOf(s.rp), floor = rankOf(s.best).rp;
  s.rp = Math.max(n < 0 ? floor : 0, Math.round(s.rp + n)); s.best = Math.max(s.best, s.rp);
  s.log.unshift([Date.now(), n, why]); s.log.length = Math.min(s.log.length, 30);
  const after = rankOf(s.rp);
  if (after.rp > before.rp) { for (const k of RANKS) if (k.rp > before.rp && k.rp <= after.rp && k.reward) C.addCoins(k.reward); onPromote?.(after); }
  C.save(); C.emit('rank'); return after;
}
/* RP table */
export const RP = { trainer: lvl => 25 + Math.round(lvl * 9), warden: 120, rival: 60, wild: 4, capture: 8, chest: 3, find: 6, ladder: tier => 40 + tier * 15, lose: -12 };

/* leaderboard: named trainers of Veyra with RP that follows the story chapter */
const RIVALS = [['Champion Lyra', 4400, 0], ['Elite Orin', 3500, 0], ['Elite Sable', 3150, 0], ['Director Kest', 2800, 0], ['Warden Vera', 2350, 0], ['Warden Dom', 2050, 0],
  ['Ace Kai', 600, 260], ['Rho', 60, 230], ['Captain Maren', 1500, 0], ['Warden Mira', 1250, 0], ['Ranger Tomas', 380, 120], ['Dockhand Sol', 160, 70], ['Youngster Joey', 90, 45],
  ['Lass Mina', 140, 90], ['Hiker Bram', 300, 110], ['Runner Saya', 220, 140]];
export function leaderboard(chapter = 0) {
  const rows = RIVALS.map(([n, base, per]) => ({ name: n, rp: base + per * chapter }));
  rows.push({ name: 'You', rp: rp(), me: true });
  return rows.sort((a, b) => b.rp - a.rp).map((r, i) => ({ ...r, pos: i + 1, rank: rankOf(r.rp) }));
}
