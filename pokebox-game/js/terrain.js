// Pokebox — the Veyra continent as pure math (no three.js): usable from the main thread and from workers.
// Veyra is a ring of land around a flooded caldera. Six towns sit on the ring, the Obsidian Rift is the island in the
// middle (reached by the old relay causeway from Frostline). Routes run along the ring between towns; mountains grow
// wherever you are far from a road or a town, so the land naturally funnels you along the routes while still leaving
// meadows, lakes and side valleys to explore.
export const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
export const lerp = (a, b, k) => a + (b - a) * k;
export const smooth = (a, b, x) => { const t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
function hash2(x, z) { let h = Math.imul(x | 0, 374761393) + Math.imul(z | 0, 668265263); h = Math.imul(h ^ (h >>> 13), 1274126177); return ((h ^ (h >>> 16)) >>> 0) / 4294967296; }
export function vnoise(x, z) { const xi = Math.floor(x), zi = Math.floor(z), xf = x - xi, zf = z - zi, u = xf * xf * (3 - 2 * xf), v = zf * zf * (3 - 2 * zf);
  return lerp(lerp(hash2(xi, zi), hash2(xi + 1, zi), u), lerp(hash2(xi, zi + 1), hash2(xi + 1, zi + 1), u), v); }
export const fbm = (x, z, o = 4) => { let s = 0, a = .5, f = 1; for (let i = 0; i < o; i++) { s += a * vnoise(x * f, z * f); f *= 2.03; a *= .5; } return s; };
export function segDist(px, pz, pts) {
  let best = 1e9;
  for (let i = 0; i < pts.length - 1; i++) {
    const [ax, az] = pts[i], [bx, bz] = pts[i + 1], dx = bx - ax, dz = bz - az, l = dx * dx + dz * dz || 1;
    const t = clamp(((px - ax) * dx + (pz - az) * dz) / l, 0, 1), qx = ax + dx * t - px, qz = az + dz * t - pz;
    best = Math.min(best, qx * qx + qz * qz);
  }
  return Math.sqrt(best);
}

/* ------------------------------------------------------------------ layout */
/** world scale: the whole continent layout (towns, routes, coast, lake, Rift) is spread by K; towns themselves keep their size */
export const K = 1.5;
export const WORLD = Math.round(1150 * K); // square the continent fits in (centre 0,0)
export const REGIONS = {
  harbor:    { x: 0 * K,    z: 392 * K,  biome: 'meadow',   name: 'Lumen Harbor' },
  mistvale:  { x: -318 * K, z: 190 * K,  biome: 'marsh',    name: 'Mistvale' },
  starfall:  { x: -318 * K, z: -190 * K, biome: 'cliffs',   name: 'Starfall' },
  frostline: { x: 0 * K,    z: -392 * K, biome: 'snow',     name: 'Frostline' },
  voltspire: { x: 318 * K,  z: -190 * K, biome: 'plateau',  name: 'Voltspire' },
  sandreach: { x: 318 * K,  z: 190 * K,  biome: 'dunes',    name: 'Sandreach' },
  rift:      { x: 0,    z: 0,    biome: 'volcanic', name: 'Obsidian Rift' },
};
export const RING_ORDER = ['harbor', 'mistvale', 'starfall', 'frostline', 'voltspire', 'sandreach'];

/* routes: arcs along the ring between neighbouring towns (+ the causeway to the Rift) */
function arcRoute(a, b, seed) {
  const A = REGIONS[a], B = REGIONS[b], ta = Math.atan2(A.x, A.z), tb0 = Math.atan2(B.x, B.z);
  let tb = tb0; while (tb - ta > Math.PI) tb -= Math.PI * 2; while (ta - tb > Math.PI) tb += Math.PI * 2;
  const pts = [], N = Math.round(14 * K);
  for (let i = 0; i <= N; i++) {
    const k = i / N, th = lerp(ta, tb, k), rr = (372 + Math.sin(k * Math.PI * 2 + seed) * 22 * Math.sin(k * Math.PI) + (vnoise(seed * 3.1, k * 4) - .5) * 26 * Math.sin(k * Math.PI)) * K;
    pts.push([Math.sin(th) * rr, Math.cos(th) * rr]);
  }
  pts[0] = [A.x, A.z]; pts[N] = [B.x, B.z];
  return pts;
}
export const ROUTES = [
  { id: 'r1', name: 'Route 1', sub: 'Tidegrass Way', from: 'harbor', to: 'mistvale', pts: arcRoute('harbor', 'mistvale', 1) },
  { id: 'r2', name: 'Route 2', sub: 'Reedmist Trail', from: 'mistvale', to: 'starfall', pts: arcRoute('mistvale', 'starfall', 2) },
  { id: 'r3', name: 'Route 3', sub: 'Signal Pass', from: 'starfall', to: 'frostline', pts: arcRoute('starfall', 'frostline', 3) },
  { id: 'r4', name: 'Route 4', sub: 'Stormrise Road', from: 'frostline', to: 'voltspire', pts: arcRoute('frostline', 'voltspire', 4) },
  { id: 'r5', name: 'Route 5', sub: 'Glassburn Steps', from: 'voltspire', to: 'sandreach', pts: arcRoute('voltspire', 'sandreach', 5) },
  { id: 'r6', name: 'Route 6', sub: 'Old Ferry Coast', from: 'sandreach', to: 'harbor', pts: arcRoute('sandreach', 'harbor', 6) },
  { id: 'cw', name: 'Relay Causeway', sub: 'to the Obsidian Rift', from: 'frostline', to: 'rift', pts: [[0, -392], [0, -330], [3, -250], [-2, -170], [2, -110], [0, -40]].map(([x, z]) => [x * K, z * K]) },
];
/* gates: barricades on a route that open with story progress (flag names are set by the quest engine).
   `at` is placed where quests.ringLimit() actually stops the player, so the sign and the invisible wall agree. */
export const GATES = [
  { id: 'g-r1', route: 'r1', at: .235, flag: 'gate-r1', text: 'Rho: "Route 1 opens once Dr. Vale signs your Ranger licence."' },
  { id: 'g-r2', route: 'r2', at: .195, flag: 'gate-r2', text: 'A Mistvale ranger: "Fog alarm. Nobody leaves north until the Trial Warden clears it."' },
  { id: 'g-r3', route: 'r3', at: .185, flag: 'gate-r3', text: 'An Archivist blocks the pass: "Warden Sable must vouch for you first."' },
  { id: 'g-r4', route: 'r4', at: .215, flag: 'gate-r4', text: 'Ice has sealed the road. Frostline\'s Warden keeps the only thaw-key.' },
  { id: 'g-r5', route: 'r5', at: .185, flag: 'gate-r5', text: 'The Stormrise pylons are sparking. Voltspire\'s Warden has locked the road.' },
  { id: 'g-r6', route: 'r6', at: .2, flag: 'gate-r6', text: 'The old ferry bridge is down. Relay crews are rebuilding it.' },
  { id: 'g-r6b', route: 'r6', at: .88, flag: 'gate-r6', text: 'The old ferry bridge is down. Relay crews are rebuilding it.' },
  { id: 'g-cw', route: 'cw', at: .12, flag: 'gate-cw', text: 'The causeway to Node 7 is sealed. Only a Champion may pass.' },
];
export function routePoint(route, k) { // point + direction at fraction k (0..1) along a route polyline
  const pts = route.pts; let total = 0; const L = [];
  for (let i = 0; i < pts.length - 1; i++) { const l = Math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]); L.push(l); total += l; }
  let d = k * total;
  for (let i = 0; i < L.length; i++) { if (d <= L[i] || i === L.length - 1) { const t = clamp(d / L[i], 0, 1), [ax, az] = pts[i], [bx, bz] = pts[i + 1];
    return { x: lerp(ax, bx, t), z: lerp(az, bz, t), dx: (bx - ax) / L[i], dz: (bz - az) / L[i] }; } d -= L[i]; }
  return { x: pts[0][0], z: pts[0][1], dx: 1, dz: 0 };
}

/* ------------------------------------------------------------------ the original town cores (local coordinates, water = 0) */
export const TOWN_BASE = {
  harbor: (x, z) => { const r = Math.hypot(x * .95, z * 1.05); return 1.5 - smooth(40, 52, z) * 5 + (fbm(x * .05, z * .05) - .5) * 1.8 * smooth(22, 40, r) - .35 - Math.max(0, 1 - Math.hypot(x - 28, z - 34) / 22) * 2.2; },
  mistvale: (x, z) => .9 + (fbm(x * .06 + 7, z * .06) - .5) * 3 - Math.max(0, 1 - Math.hypot(x - 12, z + 6) / 10) * 2.4 - Math.max(0, 1 - Math.hypot(x + 16, z - 12) / 8) * 2,
  sandreach: (x, z) => 1.2 + Math.sin(x * .12 + fbm(x * .03, z * .03) * 4) * 1.4 + (fbm(x * .04, z * .04 + 3) - .5) * 3,
  starfall: (x, z) => 2 + (fbm(x * .07, z * .07) - .5) * 4 + Math.max(0, 1 - Math.hypot(x + 4, z + 14) / 12) * 3,
  voltspire: (x, z) => 1.4 + (fbm(x * .05 + 11, z * .05) - .5) * 2.6 + Math.floor(fbm(x * .02, z * .02) * 4) * .6,
  frostline: (x, z) => 2 + (fbm(x * .06 + 2, z * .06) - .5) * 5 + Math.max(0, -z - 20) * .35 - Math.max(0, 1 - Math.hypot(x - 14, z - 14) / 9) * 3.2,
  rift: (x, z) => { const r = Math.hypot(x, z); return 1 + (fbm(x * .08, z * .08) - .5) * 2.2 + Math.max(0, r - 30) * .18 - Math.max(0, 1 - r / 9) * 1.6; },
};
export const FLATS = { // flat pads for buildings / plazas: [x, z, radius, height] (local)
  harbor: [[0, 2, 12, 1.25], [-10, -11, 9, 1.25], [10, -12, 5.5, 1.25]], // the other houses stand on planned lots (TOWN_LOTS)
  mistvale: [[16, 5, 5, 1.1], [-22, -12, 5, 1.2]], sandreach: [[-4, -6, 7, 1.6]], starfall: [[-4, -14, 9, 3.2], [8, -4, 5, 2.4]],
  voltspire: [[0, 0, 8, 1.8]], frostline: [[2, -4, 7, 2.2], [-14, 8, 5, 2.2]], rift: [[0, -18, 11, 1.4], [0, 4, 7, .9]],
};
export const TOWN_PATHS = { // local
  harbor: [{ pts: [[0, 30], [0, 16], [0, 4], [-4, -4], [-10, -4]] }, { pts: [[0, 6], [8, 6], [15, 10], [20, 17], [21, 23]] }, { pts: [[-2, 2], [-12, 4], [-20, 1], [-26, -10]] }, { pts: [[2, -4], [4, -14], [6, -18], [16, -20], [24, -18]] }],
  mistvale: [{ pts: [[0, 32], [0, 20], [4, 10], [12, 4], [16, 3]] }, { pts: [[4, 10], [-6, 4], [-10, 2], [-20, -10]] }],
  sandreach: [{ pts: [[0, 36], [0, 20], [-4, 6], [-6, 0]] }, { pts: [[-4, 6], [10, 12], [20, 6], [30, 6]] }],
  starfall: [{ pts: [[0, 32], [0, 20], [2, 6], [-2, -4], [-4, -6]] }, { pts: [[2, 6], [12, 8], [20, 10]] }],
  voltspire: [{ pts: [[0, 36], [0, 20], [-4, 6], [0, 0]] }, { pts: [[0, 0], [-10, -4], [-20, -8]] }, { pts: [[0, 0], [12, 4], [22, 8]] }, { pts: [[0, 0], [0, -30]] }],
  frostline: [{ pts: [[0, 34], [0, 20], [2, 6], [2, -4]] }, { pts: [[2, 6], [-10, 8], [-14, 10]] }],
  rift: [{ pts: [[0, 34], [0, 20], [0, 4], [0, -8]] }],
};
/* ------------------------------------------------------------------ town planning: building lots along the streets
   Every lot sits beside a street with its door facing it, gets a flat pad (no grass) and a short footpath to the street.
   Computed once, deterministically, so the terrain worker (pads, paths) and the world (buildings) agree. */
const LOT = { gap: 10.5, set: 6.8, pad: 4.3, plaza: 14, edge: 41, apart: 9.5 };
// how many houses each town gets (closest to the plaza first); the Rift is a ruin, not a town
const LOT_N = { harbor: 12, mistvale: 9, starfall: 8, frostline: 9, voltspire: 11, sandreach: 11, rift: 0 };
// every town gets a ring lane and a cross avenue besides its original streets, so houses can line real streets
for (const id in TOWN_PATHS) { if (!LOT_N[id]) continue;
  const ring = Array.from({ length: 17 }, (_, i) => { const a = i / 16 * Math.PI * 2; return [Math.cos(a) * 24, 2 + Math.sin(a) * 24]; });
  TOWN_PATHS[id].push({ pts: ring, lane: true }, { pts: [[-34, 2], [-12, 2]], lane: true }, { pts: [[12, 2], [34, 2]], lane: true }); }
export const TOWN_LOTS = {};
for (const id in TOWN_PATHS) {
  const lots = [], base = TOWN_BASE[id], hand = (FLATS[id] || []).slice(), streets = TOWN_PATHS[id].slice();
  for (const p of streets) for (let i = 0; i < p.pts.length - 1; i++) {
    const [ax, az] = p.pts[i], [bx, bz] = p.pts[i + 1], L = Math.hypot(bx - ax, bz - az), dx = (bx - ax) / L, dz = (bz - az) / L;
    for (let d = 4; d <= L - 3; d += LOT.gap) for (const side of [-1, 1]) {
      const sx = ax + dx * d, sz = az + dz * d, x = sx - dz * side * LOT.set, z = sz + dx * side * LOT.set;
      if (Math.hypot(x, z - 2) < LOT.plaza || Math.hypot(x, z) > LOT.edge) continue;                 // keep the plaza and the town edge free
      if (lots.some(l => Math.hypot(l.x - x, l.z - z) < LOT.apart)) continue;
      if (streets.some(q => segDist(x, z, q.pts) < LOT.set - .6)) continue;                          // not on top of another street
      if (hand.some(([fx, fz, r]) => Math.hypot(fx - x, fz - z) < r + 4.5)) continue;                // not on the hand-built pads (lab, shop, plaza…)
      const y0 = base(x, z), y1 = Math.min(base(x + 3, z), base(x - 3, z), base(x, z + 3), base(x, z - 3)); if (y1 < .35) continue; // dry land only
      lots.push({ x, z, sx, sz, rot: Math.atan2(sx - x, sz - z), y: Math.max(.95, y0) });
    }
  }
  lots.sort((a, b) => Math.hypot(a.x, a.z - 2) - Math.hypot(b.x, b.z - 2)); lots.length = Math.min(lots.length, LOT_N[id] || 0);
  for (const l of lots) {
    FLATS[id].push([l.x, l.z, LOT.pad, l.y]);
    const k = (LOT.set - 2.6) / LOT.set; TOWN_PATHS[id].push({ spur: true, pts: [[l.x + (l.sx - l.x) * .42, l.z + (l.sz - l.z) * .42], [l.x + (l.sx - l.x) * k, l.z + (l.sz - l.z) * k]] });
  }
  TOWN_LOTS[id] = lots;
}
const TOWN_R = 44, TOWN_BLEND = 72;

/* ------------------------------------------------------------------ biomes */
export const BIOMES = {
  meadow:   { ground: ['#5a9a42', '#478838', '#72ac4c'], sand: '#e8d7a4', rock: '#8f8a80', path: '#cdb07c', grass: ['#4a8a36', '#a4d468'], grassK: 1, snowY: 99 },
  marsh:    { ground: ['#5e9150', '#3f7045', '#7ea55e'], sand: '#aaa37a', rock: '#707768', path: '#978764', grass: ['#2f6a3d', '#9cc978'], grassK: 1.1, snowY: 99 },
  cliffs:   { ground: ['#5f8f86', '#4a7670', '#7fa89a'], sand: '#8a8fa6', rock: '#6f7488', path: '#a4a6be', grass: ['#3f6e66', '#9cc8b4'], grassK: .8, snowY: 99 },
  snow:     { ground: ['#e8f1fa', '#cddcee', '#ffffff'], sand: '#e6eef6', rock: '#8a9aae', path: '#bccadc', grass: ['#8aa0a8', '#dfeaf0'], grassK: .15, snowY: 2.5 },
  plateau:  { ground: ['#a19a66', '#7d7850', '#bdb27c'], sand: '#958d6c', rock: '#77725f', path: '#b0a27a', grass: ['#6d6a3c', '#d8cf80'], grassK: .75, snowY: 99 },
  dunes:    { ground: ['#eab974', '#d69f5a', '#f4d396'], sand: '#f4d9a2', rock: '#be7c4a', path: '#d1a264', grass: ['#9a7a3a', '#ecd28a'], grassK: .18, snowY: 99 },
  volcanic: { ground: ['#2d3236', '#23282c', '#3a4044'], sand: '#2c3134', rock: '#1f2427', path: '#40504c', grass: ['#0f3a34', '#44c8ae'], grassK: .35, snowY: 99 },
};
const RING_IDS = RING_ORDER;
/** per-biome weights at a point (sum 1). Returns an array aligned with BIOME_LIST. */
export const BIOME_LIST = Object.keys(BIOMES);
export function regionWeights(x, z) {
  const w = {}; let s = 0;
  for (const id of RING_IDS) { const R = REGIONS[id], d = Math.hypot(x - R.x, z - R.z), v = Math.exp(-((d / (190 * K)) ** 2)); w[id] = v; s += v; }
  const rr = Math.hypot(x, z); w.rift = Math.exp(-((rr / (120 * K)) ** 2)) * 3; s += w.rift;
  if (s < 1e-6) { w.harbor = 1; s = 1; }
  for (const k in w) w[k] /= s;
  return w;
}
export function nearestRegion(x, z) { let best = 'harbor', bd = 1e9; for (const id in REGIONS) { const R = REGIONS[id], d = Math.hypot(x - R.x, z - R.z); if (d < bd) { bd = d; best = id; } } return { id: best, d: bd }; }

const biomeHeight = {
  meadow: (x, z) => 2.1 + (fbm(x * .011, z * .011) - .5) * 6.5 + (fbm(x * .05, z * .05) - .5) * 1.4,
  marsh: (x, z) => .75 + (fbm(x * .018 + 7, z * .018) - .5) * 3 - Math.max(0, fbm(x * .028, z * .028 + 5) - .6) * 20,
  cliffs: (x, z) => { const f = fbm(x * .012 + 3, z * .012); const step = Math.floor(f * 6); return 2.5 + lerp(step, f * 6, .35) * 2.1 + (fbm(x * .06, z * .06) - .5) * 1.2; },
  snow: (x, z) => { const r = 1 - Math.abs(fbm(x * .01 + 9, z * .01) * 2 - 1); return 3.5 + r * r * 16 + (fbm(x * .04, z * .04) - .5) * 3; },
  plateau: (x, z) => 2.5 + Math.floor(fbm(x * .015 + 11, z * .015) * 5) * 1.6 + (fbm(x * .05, z * .05) - .5) * 1.5,
  dunes: (x, z) => 2.4 + Math.sin(x * .045 + fbm(x * .01, z * .01) * 6) * 2.4 + (fbm(x * .02, z * .02 + 3) - .5) * 3.5,
  volcanic: (x, z) => { const r = Math.hypot(x, z) / K; return 2.5 + smooth(18, 42, r) * 6 * (1 - smooth(48, 70, r)) + (fbm(x * .05, z * .05) - .5) * 2 - (1 - smooth(10, 20, r)) * 2; },
};
const BIOME_OF = Object.fromEntries(Object.entries(REGIONS).map(([k, v]) => [k, v.biome]));

/** distance to the nearest road (routes + the causeway) */
export function roadDist(x, z) { let d = 1e9; for (const r of ROUTES) { d = Math.min(d, segDist(x, z, r.pts)); if (d < 1) return d; } return d; }
/** distance to the nearest town centre */
export function townDist(x, z) { let d = 1e9, id = null; for (const k in REGIONS) { const R = REGIONS[k], dd = Math.hypot(x - R.x, z - R.z); if (dd < d) { d = dd; id = k; } } return { d, id }; }

function landMask(x, z) {
  const r = Math.hypot(x, z) / K, th = Math.atan2(x, z); z /= K; x /= K;
  let coast = 505 + (fbm(Math.sin(th) * 2.2 + 5, Math.cos(th) * 2.2) - .5) * 70;
  const harborSector = Math.exp(-((th / .22) ** 2)); coast = lerp(coast, 434, harborSector);                // Lumen Harbor sits on the sea
  const lake = 228 + (fbm(Math.sin(th) * 3 + 1, Math.cos(th) * 3 + 2) - .5) * 50;
  const ring = smooth(lake - 12, lake + 16, r) * (1 - smooth(coast - 26, coast + 6, r));
  const island = 1 - smooth(60, 92, r);
  const cw = Math.abs(x) < 16 / K && z < -30 && z > -380 ? 1 - smooth(5 / K, 11 / K, Math.abs(x - Math.sin(z * .02) * 2)) : 0;   // rock causeway to the Rift
  return Math.max(ring, island, cw);
}

/**
 * H(x, z): terrain height in metres (water at 0). The single source of truth for the continent.
 * Returns only the number; use sample() when colours / masks are needed too.
 */
export function H(x, z) { return sample(x, z, false).y; }

/** full sample: height + biome weights + road distance + grass amount + town info */
export function sample(x, z, full = true) {
  const w = regionWeights(x, z);
  let y = 0; for (const id in w) if (w[id] > .003) y += w[id] * biomeHeight[BIOME_OF[id]](x, z);
  const rd = roadDist(x, z), { d: td, id: tid } = townDist(x, z);
  // mountains away from roads & towns (guides you along the routes), with gaps for meadows/side valleys
  const mask = smooth(.5, .7, fbm(x * .006 / K + 2, z * .006 / K + 7, 3));
  const mountain = smooth(34, 90, rd) * smooth(70, 120, td) * mask;
  if (mountain > 0) { const rg = 1 - Math.abs(fbm(x * .02 + 4, z * .02, 4) * 2 - 1); y += mountain * (8 + rg * rg * 26); }
  // roads: gently flattened
  if (rd < 9) y = lerp(y, 1.4 + (y - 1.4) * .35, smooth(9, 2.5, rd) * (1 - (w.snow ?? 0) * .3));
  // land / sea
  const land = landMask(x, z);
  y = land < 1 ? lerp(-4.5, Math.max(y, .6), land) : y;
  // towns keep their hand-built cores
  let town = 0;
  if (td < TOWN_BLEND) {
    const R = REGIONS[tid], lx = x - R.x, lz = z - R.z; town = smooth(TOWN_BLEND, TOWN_R, td);
    let yt = TOWN_BASE[tid](lx, lz);
    for (const [fx, fz, r, fy] of FLATS[tid] || []) { const t = smooth(r + 5, r, Math.hypot(lx - fx, lz - fz)); if (t > 0) yt = lerp(yt, fy, t); }
    y = lerp(y, yt, town);
  }
  if (!full) return { y };
  // how much grass may grow here (biome, not on roads/plazas/beaches, not under water)
  let gk = 0; for (const id in w) gk += w[id] * BIOMES[BIOME_OF[id]].grassK;
  let plaza = 0; if (td < TOWN_R + 4) { const R = REGIONS[tid]; for (const [fx, fz, r] of FLATS[tid] || []) plaza = Math.max(plaza, smooth(r + 1.5, r - 1, Math.hypot(x - R.x - fx, z - R.z - fz))); }
  let tpath = 9; if (td < TOWN_R + 6) { const R = REGIONS[tid]; for (const p of TOWN_PATHS[tid] || []) tpath = Math.min(tpath, segDist(x - R.x, z - R.z, p.pts)); }
  const snowcap = smooth(13, 17, y) * smooth(.2, .4, mountain);   // no lawn on the snowy peaks
  const grass = clamp(gk * smooth(.3, .8, y) * smooth(2.4, 4.2, rd) * smooth(1.6, 2.8, tpath) * (1 - plaza) * (1 - mountain * .7) * (1 - snowcap), 0, 1.2);
  return { y, w, rd, td, tid, town, mountain, grass, tpath, land };
}

/** vertex colour (linear-ish sRGB triplet 0..1) for a terrain sample */
const hex = h => [parseInt(h.slice(1, 3), 16) / 255, parseInt(h.slice(3, 5), 16) / 255, parseInt(h.slice(5, 7), 16) / 255];
const PAL = Object.fromEntries(Object.entries(BIOMES).map(([k, b]) => [k, { g0: hex(b.ground[0]), g1: hex(b.ground[1]), g2: hex(b.ground[2]), sand: hex(b.sand), rock: hex(b.rock), path: hex(b.path), snowY: b.snowY }]));
const SNOW = hex('#f4f8ff'), WET = [.24, .3, .22];
export function colorAt(x, z, s, slope) {
  const out = [0, 0, 0], n = fbm(x * .05, z * .05), n2 = vnoise(x * .4, z * .4);
  for (const id in s.w) {
    const k = s.w[id]; if (k < .003) continue; const P = PAL[BIOME_OF[id]];
    const t = clamp(n * 1.6 - .3, 0, 1), c = [lerp(P.g0[0], P.g1[0], t), lerp(P.g0[1], P.g1[1], t), lerp(P.g0[2], P.g1[2], t)];
    const hi = clamp((s.y - 4) * .12, 0, 1); for (let i = 0; i < 3; i++) c[i] = lerp(c[i], P.g2[i], hi * .6);
    if (s.y < .9) { const b = smooth(.9, .3, s.y); for (let i = 0; i < 3; i++) c[i] = lerp(c[i], P.sand[i], b); }
    const rk = smooth(.55, 1.0, slope) + s.mountain * smooth(6, 14, s.y) * .6; for (let i = 0; i < 3; i++) c[i] = lerp(c[i], P.rock[i], clamp(rk, 0, 1));
    if (s.y > P.snowY + (n2 - .5) * 2) for (let i = 0; i < 3; i++) c[i] = lerp(c[i], SNOW[i], .85);
    if (s.mountain > .3 && s.y > 16 + n2 * 4) for (let i = 0; i < 3; i++) c[i] = lerp(c[i], SNOW[i], .7); // snow caps on every high peak
    const pk = Math.max(smooth(3.2, 1.2, s.rd), smooth(2, .6, s.tpath) * .9); for (let i = 0; i < 3; i++) c[i] = lerp(c[i], P.path[i] * (.9 + n2 * .12), pk);
    for (let i = 0; i < 3; i++) out[i] += c[i] * k;
  }
  const v = .9 + n2 * .16; for (let i = 0; i < 3; i++) out[i] *= v;
  if (s.y < .05) { const b = smooth(.05, -.8, s.y); for (let i = 0; i < 3; i++) out[i] = lerp(out[i], WET[i] * out[i] * 2.2, b); }
  return out;
}
