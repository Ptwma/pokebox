// Pokebox battles v2 — 3v3 card duels with a readable damage model.
//   HP  = the HP printed on the card (enemy trainers scale it with their level)
//   ATK = card attack, DEF = derived from bulk (HP) and attack, SPD decides who moves first.
//   damage = power × ATK / (DEF + 40) × 1.22 × type × random(0.9–1.05) × crit(1.5, 6%)
//   → a basic hit takes ~20% of an equal card's HP, a signature move ~40%, an ultimate ~60%.
//   A typical 3v3 lasts 9–13 rounds instead of 4–5.
import { DB, isMon, rng } from './core.js';

export const WEAK = { // attacker type -> defender types it hits for x1.5
  Fire: ['Grass', 'Metal'], Water: ['Fire'], Grass: ['Water', 'Fighting'], Lightning: ['Water', 'Colorless'],
  Fighting: ['Lightning', 'Darkness', 'Colorless', 'Metal'], Psychic: ['Fighting'], Darkness: ['Psychic'], Metal: ['Psychic', 'Fairy'],
  Dragon: ['Dragon'], Colorless: [],
};
export const RESIST = { // defender type -> attacker types it takes x0.75 from
  Fire: ['Grass'], Water: ['Fire', 'Metal'], Grass: ['Water', 'Lightning'], Lightning: ['Metal'], Metal: ['Grass'], Darkness: ['Psychic'], Fighting: [], Psychic: [], Dragon: [], Colorless: [],
};
export const mult = (a, d) => ((WEAK[a] || []).includes(d) ? 1.5 : 1) * ((RESIST[d] || []).includes(a) ? .75 : 1);

// signature move per type: name, power, energy cost, side effect
export const SIG = {
  Fire: { name: 'Flame Burst', fx: 'burn', note: 'burns for 3 turns' },
  Water: { name: 'Hydro Cannon', fx: 'soak', note: 'lowers their speed' },
  Grass: { name: 'Leaf Drain', fx: 'drain', note: 'heals 35% of damage' },
  Lightning: { name: 'Thunder Shock', fx: 'para', note: '30% paralysis' },
  Psychic: { name: 'Mind Crush', fx: 'weaken', note: 'lowers their attack' },
  Fighting: { name: 'Close Combat', fx: 'pierce', note: 'ignores guard' },
  Darkness: { name: 'Night Slash', fx: 'crit', note: 'high critical chance' },
  Metal: { name: 'Iron Bash', fx: 'shield', note: 'raises your defense' },
  Dragon: { name: 'Dragon Rush', fx: 'none', note: 'massive power' },
  Colorless: { name: 'Hyper Strike', fx: 'none', note: 'reliable damage' },
};
export const ENERGY_MAX = 5;
export const MOVES = {
  attack: { power: 30, cost: 0, gain: 1 },
  sig: { power: 58, cost: 2, gain: 0 },
  ult: { power: 92, cost: 4, gain: 0 },
  guard: { cost: 0, gain: 1 },
};

export const TRAINERS = [
  { name: 'Youngster Joey', title: 'Route 1', maxR: 1, lvl: .9, reward: 60 },
  { name: 'Lass Mira', title: 'Forest trail', maxR: 2, lvl: .95, reward: 80 },
  { name: 'Hiker Dom', title: 'Rock tunnel', maxR: 2, lvl: 1, reward: 100 },
  { name: 'Ace Trainer Kai', title: 'Victory road', maxR: 3, lvl: 1.03, reward: 140 },
  { name: 'Gym Leader Vera', title: 'Cinder gym', maxR: 4, lvl: 1.06, reward: 200, token: 1 },
  { name: 'Elite Sable', title: 'Elite Four', maxR: 5, lvl: 1.1, reward: 280 },
  { name: 'Elite Orin', title: 'Elite Four', maxR: 5, lvl: 1.14, reward: 360, token: 1 },
  { name: 'Champion Lyra', title: 'Hall of Fame', maxR: 6, lvl: 1.2, reward: 600, token: 2 },
];

export function fighter(card, lvl = 1) {
  const hp = Math.round(card.hp * lvl), atk = Math.round(card.atk * lvl);
  return { card, name: card.n, type: card.t, maxHp: hp, hp, atk, def: Math.round(card.hp * .25 + card.atk * .2), spd: card.spd,
    energy: 0, guard: false, status: null, statusT: 0, buff: { atk: 1, def: 1, spd: 1 } };
}
export function power(card) { return card.hp * .7 + card.atk * 1.5 + card.spd * .3; }

export function enemyTeam(tier, seed) {
  const T = TRAINERS[tier], R = rng(seed);
  const pool = DB.cards.filter(c => isMon(c) && c.r <= T.maxR && c.r >= Math.max(0, T.maxR - 2));
  const team = []; const used = new Set();
  while (team.length < 3 && pool.length) { const c = pool[Math.floor(R() * pool.length)]; if (!used.has(c.n)) { used.add(c.n); team.push(c); } }
  return team.map(c => fighter(c, T.lvl));
}
export function bestTeam(cards) { return cards.filter(isMon).sort((a, b) => power(b) - power(a)).slice(0, 3); }
export function estimate(att, def, kind) {
  const m = MOVES[kind]; if (!m?.power) return 0;
  return Math.round(m.power * (att.atk * att.buff.atk) / (def.def * def.buff.def + 40) * 1.22 * mult(att.type, def.type));
}

export class Battle {
  constructor(mine, theirs) { this.p = { team: mine, act: 0 }; this.e = { team: theirs, act: 0 }; this.turn = 1; this.over = null; }
  active(side) { return this[side].team[this[side].act]; }
  alive(side) { return this[side].team.filter(f => f.hp > 0); }
  canUse(f, kind) { const m = MOVES[kind]; return !!m && f.energy >= m.cost; }
  damage(att, def, kind) {
    const m = MOVES[kind], sig = kind === 'sig' ? SIG[att.type] || SIG.Colorless : null;
    const type = mult(att.type, def.type), roll = .9 + Math.random() * .15;
    const critP = sig?.fx === 'crit' ? .3 : .06, crit = Math.random() < critP ? 1.5 : 1;
    let d = m.power * (att.atk * att.buff.atk) / (def.def * def.buff.def + 40) * 1.22 * type * roll * crit;
    if (def.guard && sig?.fx !== 'pierce') d *= .45;
    return { d: Math.max(3, Math.round(d)), eff: type > 1, weak: type < 1, crit: crit > 1, guarded: def.guard && sig?.fx !== 'pierce' };
  }
  aiAction() {
    const me = this.active('e'), foe = this.active('p');
    const bench = this.e.team.map((f, i) => ({ f, i })).filter(x => x.i !== this.e.act && x.f.hp > 0);
    if (mult(foe.type, me.type) > 1 && me.hp < me.maxHp * .5 && bench.length && Math.random() < .45) {
      const good = bench.find(x => mult(foe.type, x.f.type) <= 1) || bench[0]; return { kind: 'switch', to: good.i };
    }
    if (this.canUse(me, 'ult') && (Math.random() < .7 || foe.hp < estimate(me, foe, 'ult'))) return { kind: 'ult' };
    if (this.canUse(me, 'sig') && (foe.hp <= estimate(me, foe, 'sig') || Math.random() < .35)) return { kind: 'sig' };
    if (me.hp < me.maxHp * .35 && !me.guard && Math.random() < .3) return { kind: 'guard' };
    return { kind: 'attack' };
  }
  // resolve one full round; returns a list of events for the UI to animate
  round(playerAct) {
    const ev = [], acts = { p: playerAct, e: this.aiAction() };
    for (const s of ['p', 'e']) if (acts[s].kind === 'switch') { this.active(s).guard = false; this[s].act = acts[s].to; ev.push({ t: 'switch', side: s, to: acts[s].to }); }
    for (const s of ['p', 'e']) this.active(s).guard = false;
    for (const s of ['p', 'e']) if (acts[s].kind === 'guard') { const f = this.active(s); f.guard = true; f.energy = Math.min(ENERGY_MAX, f.energy + MOVES.guard.gain); ev.push({ t: 'guard', side: s }); }
    const spd = s => this.active(s).spd * this.active(s).buff.spd;
    const order = ['p', 'e'].sort((a, b) => spd(b) - spd(a) || (Math.random() - .5));
    const skip = {};
    for (const s of order) {
      if (this.over) break;
      if (skip[s]) continue;
      const a = acts[s], me = this.active(s), o = s === 'p' ? 'e' : 'p', foe = this.active(o);
      if (me.hp <= 0 || !MOVES[a.kind]?.power) continue;
      if (!this.canUse(me, a.kind)) a.kind = 'attack';
      if (me.status === 'para' && Math.random() < .3) { ev.push({ t: 'para', side: s }); continue; }
      const m = MOVES[a.kind]; me.energy = Math.min(ENERGY_MAX, me.energy - m.cost + m.gain);
      const r = this.damage(me, foe, a.kind); foe.hp = Math.max(foe.minHp || 0, foe.hp - r.d); if (foe.minHp && foe.hp <= foe.minHp) r.cling = true;
      const sig = a.kind === 'sig' ? (SIG[me.type] || SIG.Colorless) : null;
      ev.push({ t: 'hit', side: s, kind: a.kind, move: a.kind === 'attack' ? 'Attack' : a.kind === 'ult' ? 'Ultimate' : sig.name, type: me.type, ...r });
      if (sig && foe.hp > 0) {
        const fx = sig.fx;
        if (fx === 'burn' && !foe.status) { foe.status = 'burn'; foe.statusT = 3; ev.push({ t: 'status', side: o, st: 'burn' }); }
        else if (fx === 'para' && !foe.status && Math.random() < .3) { foe.status = 'para'; foe.statusT = 2; ev.push({ t: 'status', side: o, st: 'para' }); }
        else if (fx === 'soak') { foe.buff.spd = Math.max(.6, foe.buff.spd - .2); ev.push({ t: 'debuff', side: o, stat: 'SPD' }); }
        else if (fx === 'weaken') { foe.buff.atk = Math.max(.6, foe.buff.atk - .15); ev.push({ t: 'debuff', side: o, stat: 'ATK' }); }
      }
      if (sig?.fx === 'drain') { const h = Math.round(r.d * .35); me.hp = Math.min(me.maxHp, me.hp + h); ev.push({ t: 'heal', side: s, n: h }); }
      if (sig?.fx === 'shield') { me.buff.def = Math.min(1.6, me.buff.def + .2); ev.push({ t: 'buff', side: s, stat: 'DEF' }); }
      if (this.ko(o, s, ev, skip)) break;
    }
    // end of round: burn ticks, statuses wear off
    for (const s of ['p', 'e']) {
      if (this.over) break;
      const f = this.active(s); if (f.hp <= 0 || !f.status) continue;
      if (f.status === 'burn') { const d = Math.max(4, Math.round(f.maxHp * .06)); f.hp = Math.max(f.minHp || 0, f.hp - d); ev.push({ t: 'burn', side: s, d }); if (this.ko(s, s === 'p' ? 'e' : 'p', ev, skip)) break; }
      if (--f.statusT <= 0) { ev.push({ t: 'cure', side: s, st: f.status }); f.status = null; }
    }
    this.turn++;
    return ev;
  }
  ko(o, winner, ev, skip) {
    const foe = this.active(o); if (foe.hp > 0) return false;
    ev.push({ t: 'ko', side: o });
    const next = this[o].team.findIndex(f => f.hp > 0);
    if (next < 0) { this.over = winner === 'p' ? 'win' : 'lose'; ev.push({ t: 'end', result: this.over }); return true; }
    this[o].act = next; skip[o] = true; ev.push({ t: 'switch', side: o, to: next, forced: true });
    return false;
  }
}
