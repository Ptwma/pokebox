// Pokebox — procedural town buildings.
// Every town gets 30+ buildings in its own architecture (tropical port, stilt village, star-lantern town, winter chalets,
// storm-tech city, walled desert bazaar). Buildings are assembled from boxes and prisms with flat vertex colours in the same
// toy-town language as the Blender kits (cream/pastel walls, bold roofs, white window frames), and ALL the buildings of a
// town are merged into two meshes: one for walls/roofs, one for windows (which glow at night). That keeps a 40-building
// town at two draw calls, so it runs on phones.
import * as THREE from 'three';

/* ---------- geometry builder: flat-shaded boxes / prisms with per-face colours, placed with a 2D transform */
class Builder {
  constructor() { this.p = []; this.n = []; this.c = []; }
  tri(a, b, c, col) {
    const ux = b[0] - a[0], uy = b[1] - a[1], uz = b[2] - a[2], vx = c[0] - a[0], vy = c[1] - a[1], vz = c[2] - a[2];
    let nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx; const l = Math.hypot(nx, ny, nz) || 1; nx /= l; ny /= l; nz /= l;
    // baked ambient occlusion: walls darken toward the ground they stand on (aoBase = ground height of the current building)
    for (const v of [a, b, c]) { const k = this.aoBase == null ? 1 : Math.min(1, .66 + Math.max(0, v[1] - this.aoBase) * .15);
      this.p.push(v[0], v[1], v[2]); this.n.push(nx, ny, nz); this.c.push(col.r * k, col.g * k, col.b * k); }
  }
  quad(a, b, c, d, col) { this.tri(a, b, c, col); this.tri(a, c, d, col); }
  geometry() {
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(this.p, 3)); g.setAttribute('normal', new THREE.Float32BufferAttribute(this.n, 3));
    g.setAttribute('color', new THREE.Float32BufferAttribute(this.c, 3)); g.computeBoundingSphere(); return g;
  }
}
const C = (hex) => new THREE.Color(hex);
const shade = (col, k) => col.clone().multiplyScalar(k);
// a local frame: building origin (x, y, z) rotated by ry; local +z is the front (door side)
function frame(x, y, z, ry) { const c = Math.cos(ry), s = Math.sin(ry); return (lx, ly, lz) => [x + lx * c + lz * s, y + ly, z - lx * s + lz * c]; }
// axis-aligned (in local space) box: centre (cx, cy, cz), size (w, h, d); top/side colours
function box(B, T, cx, cy, cz, w, h, d, col, top = null, skipBottom = true) {
  const x0 = cx - w / 2, x1 = cx + w / 2, y0 = cy, y1 = cy + h, z0 = cz - d / 2, z1 = cz + d / 2, P = (a, b, c) => T(a, b, c);
  const side = col, front = shade(col, 1.04), back = shade(col, .9), t = top || shade(col, 1.08);
  B.quad(P(x0, y0, z1), P(x1, y0, z1), P(x1, y1, z1), P(x0, y1, z1), front);   // +z
  B.quad(P(x1, y0, z0), P(x0, y0, z0), P(x0, y1, z0), P(x1, y1, z0), back);    // -z
  B.quad(P(x1, y0, z1), P(x1, y0, z0), P(x1, y1, z0), P(x1, y1, z1), side);    // +x
  B.quad(P(x0, y0, z0), P(x0, y0, z1), P(x0, y1, z1), P(x0, y1, z0), shade(side, .95)); // -x
  B.quad(P(x0, y1, z1), P(x1, y1, z1), P(x1, y1, z0), P(x0, y1, z0), t);       // top
  if (!skipBottom) B.quad(P(x0, y0, z0), P(x1, y0, z0), P(x1, y0, z1), P(x0, y0, z1), shade(col, .7));
}
// gable roof along x (ridge parallel to the front) or along z
function gable(B, T, cx, y, cz, w, d, h, over, col, alongZ = false, snow = null) {
  const hw = w / 2 + over, hd = d / 2 + over, P = (a, b, c) => T(cx + a, y + b, cz + c);
  if (!alongZ) {
    const r = col, r2 = shade(col, .82);
    B.quad(P(-hw, 0, hd), P(hw, 0, hd), P(hw, h, 0), P(-hw, h, 0), r);       // front slope
    B.quad(P(hw, 0, -hd), P(-hw, 0, -hd), P(-hw, h, 0), P(hw, h, 0), r2);    // back slope
    B.tri(P(hw - over, 0, hd - over), P(hw - over, 0, -hd + over), P(hw - over, h, 0), shade(col, .65)); // gable ends (wall-ish)
    B.tri(P(-hw + over, 0, -hd + over), P(-hw + over, 0, hd - over), P(-hw + over, h, 0), shade(col, .65));
    if (snow) { const s = h * .42, k = .42; B.quad(P(-hw, h - s, hd * k), P(hw, h - s, hd * k), P(hw, h + .06, 0), P(-hw, h + .06, 0), snow); B.quad(P(hw, h - s, -hd * k), P(-hw, h - s, -hd * k), P(-hw, h + .06, 0), P(hw, h + .06, 0), shade(snow, .92)); }
  } else {
    const r = col, r2 = shade(col, .82);
    B.quad(P(hw, 0, hd), P(hw, 0, -hd), P(0, h, -hd), P(0, h, hd), r);
    B.quad(P(-hw, 0, -hd), P(-hw, 0, hd), P(0, h, hd), P(0, h, -hd), r2);
    B.tri(P(-hw + over, 0, hd - over), P(hw - over, 0, hd - over), P(0, h, hd - over), shade(col, .65));
    B.tri(P(hw - over, 0, -hd + over), P(-hw + over, 0, -hd + over), P(0, h, -hd + over), shade(col, .65));
  }
}
function hip(B, T, cx, y, cz, w, d, h, over, col) {
  const hw = w / 2 + over, hd = d / 2 + over, r = Math.min(hw, hd) * .55, P = (a, b, c) => T(cx + a, y + b, cz + c);
  const ax = hw > hd ? hw - r : 0, az = hd > hw ? hd - r : 0;
  B.quad(P(-hw, 0, hd), P(hw, 0, hd), P(ax, h, az), P(-ax, h, az), col);
  B.quad(P(hw, 0, -hd), P(-hw, 0, -hd), P(-ax, h, -az), P(ax, h, -az), shade(col, .8));
  B.quad(P(hw, 0, hd), P(hw, 0, -hd), P(ax, h, -az), P(ax, h, az), shade(col, .9));
  B.quad(P(-hw, 0, -hd), P(-hw, 0, hd), P(-ax, h, az), P(-ax, h, -az), shade(col, .86));
}
function dome(B, T, cx, y, cz, r, col, seg = 8, hk = .9) {
  const P = (a, b, c) => T(cx + a, y + b, cz + c), rows = 4;
  for (let j = 0; j < rows; j++) { const a0 = j / rows * Math.PI / 2, a1 = (j + 1) / rows * Math.PI / 2;
    for (let i = 0; i < seg; i++) { const t0 = i / seg * Math.PI * 2, t1 = (i + 1) / seg * Math.PI * 2, k = shade(col, .82 + .18 * Math.sin(a1));
      const v = (a, t) => P(Math.cos(t) * Math.cos(a) * r, Math.sin(a) * r * hk, Math.sin(t) * Math.cos(a) * r);
      if (j === rows - 1) B.tri(v(a0, t1), v(a0, t0), v(a1, 0), k); else B.quad(v(a0, t1), v(a0, t0), v(a1, t0), v(a1, t1), k); } }
}
function cyl(B, T, cx, y, cz, r, h, col, seg = 8, top = null) {
  const P = (a, b, c) => T(cx + a, y + b, cz + c);
  for (let i = 0; i < seg; i++) { const t0 = i / seg * Math.PI * 2, t1 = (i + 1) / seg * Math.PI * 2, k = shade(col, .85 + .15 * Math.cos(t0));
    B.quad(P(Math.cos(t1) * r, 0, Math.sin(t1) * r), P(Math.cos(t0) * r, 0, Math.sin(t0) * r), P(Math.cos(t0) * r, h, Math.sin(t0) * r), P(Math.cos(t1) * r, h, Math.sin(t1) * r), k);
    if (top) B.tri(P(Math.cos(t0) * r, h, Math.sin(t0) * r), P(Math.cos(t1) * r, h, Math.sin(t1) * r), P(0, h, 0), top); }
}
function cone(B, T, cx, y, cz, r, h, col, seg = 8) {
  const P = (a, b, c) => T(cx + a, y + b, cz + c);
  for (let i = 0; i < seg; i++) { const t0 = i / seg * Math.PI * 2, t1 = (i + 1) / seg * Math.PI * 2; B.tri(P(Math.cos(t1) * r, 0, Math.sin(t1) * r), P(Math.cos(t0) * r, 0, Math.sin(t0) * r), P(0, h, 0), shade(col, .8 + .2 * Math.cos(t0))); }
}

/* ---------- architecture styles (one per town; every style is a full vocabulary, not a recolour) */
export const STYLES = {
  // Lumen Harbor — sunny port in the spirit of a canal city by the sea: pastel stucco, terracotta & teal roofs, balconies, awnings
  tropical: { walls: ['#fbe8c8', '#ffd7c2', '#d6f0ea', '#fff3d6', '#ffe1ea', '#e3ecff'], roofs: ['#e2683c', '#d9553b', '#2fb3a5', '#3d8fd6', '#f2a03d'],
    trim: '#ffffff', door: '#7a4a2a', glass: '#3a7ec8', roof: ['gable', 'hip', 'hip', 'flat'], floors: [1, 2, 2, 3], w: [6.2, 9], d: [6, 8], balcony: .55, awning: .35, chimney: .15, plinth: '#c9b79a' },
  // Mistvale — a village among ponds and reeds, houses raised on stilts with dark timber and mossy roofs
  wetland: { walls: ['#d9c7a3', '#c9b48c', '#e6d8b8', '#bfa77e'], roofs: ['#4f7a3a', '#5d6b3a', '#7a5a32', '#3f6a4a'], trim: '#f4ead2', door: '#5a3a22', glass: '#5a8a9a',
    roof: ['gable', 'gable', 'steep'], floors: [1, 2, 2], w: [5.6, 8], d: [5.4, 7], stilts: .7, timber: '#5b3d26', chimney: .3, plinth: '#5b3d26' },
  // Starfall — a stone town of lanterns and slate under the night sky; round towers, blue slate, warm windows
  stargaze: { walls: ['#d6d4e6', '#c4c8dc', '#e6e2ee', '#b8bdd6'], roofs: ['#3d4a8a', '#4a3d7a', '#2f5a8a', '#5a4a9a'], trim: '#f0eefa', door: '#4a3a5a', glass: '#ffd27a',
    roof: ['steep', 'hip', 'tower'], floors: [2, 2, 3], w: [5.8, 8.4], d: [5.6, 7.6], chimney: .2, lantern: .7, plinth: '#8a8aa8' },
  // Frostline — alpine winter village: timber chalets, steep roofs heavy with snow, smoking chimneys
  winter: { walls: ['#8a5a3a', '#a06a42', '#7a4e32', '#e8dccb', '#b47a4a'], roofs: ['#6a3a2a', '#3a4a6a', '#5a2a2a', '#2f3f4f'], trim: '#ffffff', door: '#4a2e1c', glass: '#ffcf80',
    roof: ['steep', 'steep', 'gable'], floors: [1, 2, 2], w: [6.2, 9], d: [6, 8], snow: '#f6fbff', chimney: .8, plinth: '#8f9aa8' },
  // Voltspire — a storm-powered tech city: concrete and steel blocks, flat roofs with antennas, pipes and signal lights
  tech: { walls: ['#d8dde4', '#b8c2cc', '#e8ecf0', '#9fb0c0', '#f0e6c8'], roofs: ['#4a5560', '#3a4450', '#5a6470'], trim: '#ffd23c', door: '#3a4450', glass: '#5ad8ff',
    roof: ['flat', 'flat', 'flat', 'hip'], floors: [3, 4, 5, 6], w: [6.6, 9], d: [6.4, 8], antenna: .6, pipes: .5, plinth: '#5a6470' },
  // Sandreach — a walled oasis bazaar: adobe cubes, domes and arches, striped awnings, rooftop terraces
  desert: { walls: ['#f1d2a2', '#e8bf86', '#f6dfb8', '#e2b07a', '#f4c99a'], roofs: ['#f1d2a2', '#e8bf86', '#2f9ac8', '#e2683c'], trim: '#fff4e0', door: '#6a3a1e', glass: '#3a5a7a',
    roof: ['flat', 'flat', 'dome', 'flat'], floors: [1, 2, 2, 3], w: [5.8, 8.6], d: [5.6, 8], awning: .55, plinth: '#c99a62' },
};

/* ---------- one building */
function building(B, W, x, y, z, ry, st, R, opts = {}) {
  const pick = a => a[(R() * a.length) | 0], rng = (a, b) => a + R() * (b - a);
  const w = Math.min(opts.maxW || 99, opts.w || rng(st.w[0], st.w[1])), d = Math.min(opts.maxD || 99, opts.d || rng(st.d[0], st.d[1])), floors = opts.floors || pick(st.floors), fh = st === STYLES.tech ? 3.8 : 3.5; // generous storeys: the buildings read big next to a 2 m character, like in the games
  let roof = opts.roof || pick(st.roof); const wall = C(opts.wall || pick(st.walls)), roofC = C(opts.roofC || pick(st.roofs)), trim = C(st.trim), glass = C(st.glass), door = C(st.door);
  const lift = st.stilts ? 1.3 : 0, T = frame(x, y + lift, z, ry), Ty = frame(x, y, z, ry), H = floors * fh;
  if (st.stilts) { for (const [sx, sz] of [[-w / 2 + .3, -d / 2 + .3], [w / 2 - .3, -d / 2 + .3], [-w / 2 + .3, d / 2 - .3], [w / 2 - .3, d / 2 - .3]]) box(B, Ty, sx, -1.2, sz, .32, lift + 1.2, .32, C(st.timber));
    box(B, Ty, 0, lift - .25, d / 2 + .9, 1.4, .25, 1.6, C(st.timber)); for (let k = 0; k < 3; k++) box(B, Ty, 0, k * .42, d / 2 + 2 + k * -.35, 1.2, .14, .4, C(st.timber)); } // deck + steps
  else box(B, T, 0, -.4, 0, w + .25, .55, d + .25, C(st.plinth));            // plinth hides uneven ground
  box(B, T, 0, 0, 0, w, H, d, wall);                                                    // body
  if (st.timber && !st.stilts) {} // (timber frame only on stilt houses)
  if (st === STYLES.wetland) for (let f = 1; f <= floors; f++) box(B, T, 0, f * fh - .16, 0, w + .06, .16, d + .06, C(st.timber)); // timber bands
  if (st === STYLES.winter) { box(B, T, 0, 0, 0, w + .08, .9, d + .08, C('#8f9aa8')); }  // stone base course
  // corner pilasters + a cornice band under the roof: gives every wall a crisp silhouette edge
  if (st !== STYLES.wetland) { const pc = st === STYLES.winter ? C('#5a3a24') : st === STYLES.tech ? C('#8a96a2') : shade(C(st.trim), .97);
    for (const [px, pz] of [[-w / 2, -d / 2], [w / 2, -d / 2], [-w / 2, d / 2], [w / 2, d / 2]]) box(B, T, px, 0, pz, .34, H, .34, pc);
    box(B, T, 0, H - .22, 0, w + .3, .22, d + .3, pc);
    if (floors > 1 && st !== STYLES.tech) for (let f = 1; f < floors; f++) box(B, T, 0, f * fh - .08, 0, w + .12, .14, d + .12, pc); }
  // door (front, +z) with frame and a small canopy
  box(B, T, 0, 0, d / 2 + .02, 1.7, 2.85, .12, trim); box(B, T, 0, 0, d / 2 + .08, 1.4, 2.65, .1, door);
  box(B, T, 0, 2.95, d / 2 + .4, 2.1, .14, .8, roofC);
  // windows on every floor, front and sides (glass goes to the night-glow mesh)
  const win = (lx, ly, lz, face) => { const ww = 1.05, wh = 1.35;
    if (face === 'f') { box(B, T, lx, ly - .1, lz + .03, ww + .24, wh + .24, .08, trim); box(W, T, lx, ly - .02, lz + .08, ww, wh, .05, glass); if (st.shutters) {} }
    else { const sx = face === 'r' ? 1 : -1; box(B, T, lx + sx * .03, ly - .1, lz, .08, wh + .24, ww + .24, trim); box(W, T, lx + sx * .08, ly - .02, lz, .05, wh, ww, glass); } };
  for (let f = 0; f < floors; f++) { const wy = f * fh + 1.25;
    const nF = Math.max(1, Math.floor(w / 2.5)); for (let i = 0; i < nF; i++) { const lx = -w / 2 + (i + .5) * w / nF; if (f === 0 && Math.abs(lx) < 1.5) continue; win(lx, wy, d / 2, 'f'); }
    const nS = Math.max(1, Math.floor(d / 2.9)); for (let i = 0; i < nS; i++) { const lz = -d / 2 + (i + .5) * d / nS; win(w / 2, wy, lz, 'r'); win(-w / 2, wy, lz, 'l'); } }
  // style details
  if (st.balcony && floors > 1 && R() < st.balcony) { box(B, T, 0, fh, d / 2 + .55, Math.min(w - .6, 3.2), .14, 1.1, trim); box(B, T, 0, fh + .14, d / 2 + 1.05, Math.min(w - .6, 3.2), .55, .08, trim); }
  if (st.awning && R() < st.awning) { const stripe = pick(['#e2683c', '#2fb3a5', '#3d8fd6', '#f2c03d', '#d9553b']); for (let k = 0; k < 4; k++) box(B, T, -1.2 + k * .8, 2.6 - k * 0, d / 2 + .7, .8, .1, 1.3, C(k % 2 ? '#ffffff' : stripe)); }
  if (st.lantern && R() < st.lantern) { box(B, T, .95, 2.2, d / 2 + .3, .08, .5, .08, C('#3a3a4a')); box(W, T, .95, 1.75, d / 2 + .3, .26, .34, .26, C('#ffd27a')); }
  if (st.pipes && R() < st.pipes) { cyl(B, T, w / 2 + .25, 0, -d / 4, .18, H + .8, C('#8a96a2'), 6); cyl(B, T, w / 2 + .25, 0, d / 6, .14, H * .7, C('#c87a3a'), 6); }
  // roofs
  const ry0 = H;
  if (roof === 'flat') { box(B, T, 0, ry0, 0, w + .2, .3, d + .2, shade(wall, .92), roofC); box(B, T, 0, ry0 + .3, d / 2, w + .2, .35, .18, shade(wall, .85)); box(B, T, 0, ry0 + .3, -d / 2, w + .2, .35, .18, shade(wall, .85));
    if (st === STYLES.desert && R() < .5) { box(B, T, -w / 4, ry0 + .3, -d / 4, w / 2.2, .9, d / 2.2, wall, shade(wall, 1.05)); }
    if (st.antenna && R() < st.antenna) { box(B, T, w / 4, ry0 + .3, -d / 4, .1, 2.6, .1, C('#6a7480')); box(W, T, w / 4, ry0 + 2.9, -d / 4, .22, .22, .22, C('#ff4a3a')); }
    if (st === STYLES.tech && R() < .5) { box(B, T, -w / 4, ry0 + .3, d / 6, 1.6, .9, 1.2, C('#9fb0c0')); } }
  else if (roof === 'dome') { const r = Math.min(w, d) * .36; box(B, T, 0, ry0, 0, w + .2, .3, d + .2, shade(wall, .92)); cyl(B, T, 0, ry0 + .3, 0, r * 1.02, .9, shade(wall, 1.04), 12); box(B, T, 0, ry0 + 1.2, 0, r * 2.15, .14, r * 2.15, C(st.trim));
    dome(B, T, 0, ry0 + 1.3, 0, r, roofC, 12, 1.3); cyl(B, T, 0, ry0 + 1.3 + r * 1.3, 0, .07, .9, C('#e8c25a'), 5); box(B, T, 0, ry0 + 2.1 + r * 1.3, 0, .26, .26, .26, C('#e8c25a')); }
  else if (roof === 'hip') hip(B, T, 0, ry0, 0, w, d, Math.min(w, d) * .38, .35, roofC);
  else if (roof === 'tower') { gable(B, T, 0, ry0, 0, w, d, 1.6, .3, roofC); cyl(B, T, w / 2 - .6, 0, -d / 2 + .6, 1.1, H + 1.8, wall, 8); cone(B, T, w / 2 - .6, H + 1.8, -d / 2 + .6, 1.45, 2.4, roofC, 8); box(W, T, w / 2 - .6, H + .6, -d / 2 + 1.72, .4, .7, .06, glass); }
  else { const steep = roof === 'steep', alongZ = !steep && d > w * 1.15; gable(B, T, 0, ry0, 0, w, d, (alongZ ? w : d) * (steep ? .62 : .34), .38, roofC, alongZ, st.snow ? C(st.snow) : null); }
  if (st.chimney && R() < st.chimney && roof !== 'flat') { box(B, T, w / 4, H, -d / 5, .6, (roof === 'steep' ? d * .6 : d * .34) + .9, .6, C('#a8a0a0'), C('#5a5050')); }
  return { w: w + .3, d: d + .3, h: H + lift, stilts: !!st.stilts };
}

/** build all houses of a town: lots = [{x, z, y, rot}] in the town's local frame. Returns { group, colliders, mats } */
export function buildHouses(styleName, lots, seed = 1) {
  const st = STYLES[styleName] || STYLES.tropical, B = new Builder(), W = new Builder(), cols = [];
  let s = seed >>> 0 || 1; const R = () => ((s = (Math.imul(s, 1664525) + 1013904223) >>> 0) / 4294967296);
  for (const l of lots) { B.aoBase = l.y - .2; const b = building(B, W, l.x, l.y, l.z, l.rot, st, R, l.opts || {}); cols.push({ x: l.x, z: l.z, hw: b.w / 2, hd: b.d / 2, rot: l.rot, h: b.h }); }
  const mat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: .88, metalness: 0 });
  const glass = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: .25, metalness: .1, emissive: new THREE.Color(st === STYLES.tech ? '#9ff0ff' : '#ffc870'), emissiveIntensity: 0 });
  const g = new THREE.Group(), m = new THREE.Mesh(B.geometry(), mat), wm = new THREE.Mesh(W.geometry(), glass);
  m.castShadow = m.receiveShadow = true; wm.receiveShadow = true; g.add(m, wm); g.name = 'houses_' + styleName;
  return { group: g, colliders: cols, glass, tris: (B.p.length + W.p.length) / 9 };
}

/* ---------- landmark set pieces (Pokémon-movie inspired, original designs) */
export function windmill(seed = 1) { // hill windmill of a wind-festival port town; returns { group, blades }
  const B = new Builder(), T = frame(0, 0, 0, 0);
  cyl(B, T, 0, 0, 0, 1.9, 6.5, C('#fbf3e2'), 10); cone(B, T, 0, 6.5, 0, 2.3, 2.6, C('#e2683c'), 10); box(B, T, 0, 0, 1.85, 1, 2, .2, C('#7a4a2a'));
  const g = new THREE.Group(), m = new THREE.Mesh(B.geometry(), new THREE.MeshStandardMaterial({ vertexColors: true, roughness: .85 })); m.castShadow = true; g.add(m);
  const BB = new Builder(), TB = frame(0, 0, 0, 0); box(BB, TB, 0, -.3, 0, .6, .6, .5, C('#7a4a2a'));
  for (let i = 0; i < 4; i++) { const a = i * Math.PI / 2, TT = (lx, ly, lz) => { const c = Math.cos(a), s = Math.sin(a); return [lx * c - ly * s, lx * s + ly * c, lz]; };
    BB.quad(TT(-.12, .3, .1), TT(.12, .3, .1), TT(.12, 4.4, .1), TT(-.12, 4.4, .1), C('#7a4a2a')); BB.quad(TT(.12, 1.2, .14), TT(1.15, 1.2, .14), TT(1.15, 4.3, .14), TT(.12, 4.3, .14), C(i % 2 ? '#fff6e6' : '#ffe0c8')); }
  const blades = new THREE.Mesh(BB.geometry(), new THREE.MeshStandardMaterial({ vertexColors: true, roughness: .9, side: THREE.DoubleSide })); blades.position.set(0, 5.8, 2.05); blades.castShadow = true; g.add(blades);
  return { group: g, blades };
}
export function lighthouse() {
  const B = new Builder(), T = frame(0, 0, 0, 0);
  for (let i = 0; i < 5; i++) cyl(B, T, 0, i * 2.2, 0, 1.7 - i * .12, 2.2, C(i % 2 ? '#e2483c' : '#ffffff'), 12);
  cyl(B, T, 0, 11, 0, 1.25, .3, C('#3a3a4a'), 12); cone(B, T, 0, 12.6, 0, 1.3, 1.2, C('#e2483c'), 12);
  const g = new THREE.Group(), m = new THREE.Mesh(B.geometry(), new THREE.MeshStandardMaterial({ vertexColors: true, roughness: .7 })); m.castShadow = true; g.add(m);
  const lampM = new THREE.MeshBasicMaterial({ color: new THREE.Color('#fff2b0').multiplyScalar(2) }), lamp = new THREE.Mesh(new THREE.CylinderGeometry(1, 1, 1.3, 12), lampM); lamp.position.y = 11.95; g.add(lamp);
  const beam = new THREE.Mesh(new THREE.ConeGeometry(2.4, 26, 16, 1, true), new THREE.MeshBasicMaterial({ color: '#fff2b0', transparent: true, opacity: .0, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide }));
  beam.rotation.z = Math.PI / 2; beam.position.set(13, 0, 0); const pivot = new THREE.Group(); pivot.position.y = 11.95; pivot.add(beam); g.add(pivot);
  return { group: g, pivot, beam };
}
export function greatTree() { // the village's heart: a huge old tree (forest-village films), roots you can walk around
  const B = new Builder(), T = frame(0, 0, 0, 0);
  cyl(B, T, 0, -.3, 0, 2.6, 9, C('#6b4a2e'), 10); for (let i = 0; i < 6; i++) { const a = i / 6 * Math.PI * 2; box(B, frame(Math.cos(a) * 2.4, -.3, Math.sin(a) * 2.4, -a), 0, 0, 0, 1.2, 1.2, 2.6, C('#5f3f26')); }
  for (const [x, y, z, r] of [[0, 10, 0, 7], [4, 8.5, 2, 4.6], [-4, 8.8, -1.5, 4.8], [1.5, 13, -2, 4.4], [-2, 12, 3, 4.2]]) { const P = frame(x, y, z, 0); dome(B, P, 0, 0, 0, r, C('#4f9a3a'), 9); dome(B, frame(x, y + .01, z, 0), 0, 0, 0, r * .98, C('#3f7f30'), 9); }
  const g = new THREE.Group(), m = new THREE.Mesh(B.geometry(), new THREE.MeshStandardMaterial({ vertexColors: true, roughness: .9 })); m.castShadow = m.receiveShadow = true; g.add(m); return g;
}
export function lightString(points, color = '#ffd27a', sag = .9, per = 1.4) { // festival lanterns strung between posts
  const pos = []; for (let i = 0; i < points.length - 1; i++) { const [a, b] = [points[i], points[i + 1]], L = Math.hypot(b[0] - a[0], b[2] - a[2]), n = Math.max(2, Math.round(L / per));
    for (let k = 0; k <= n; k++) { const t = k / n; pos.push([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t - Math.sin(t * Math.PI) * sag, a[2] + (b[2] - a[2]) * t]); } }
  const mat = new THREE.MeshBasicMaterial({ color: new THREE.Color(color).multiplyScalar(1.6) }), m = new THREE.InstancedMesh(new THREE.SphereGeometry(.13, 6, 4), mat, pos.length), o = new THREE.Object3D();
  pos.forEach((p, i) => { o.position.set(...p); o.updateMatrix(); m.setMatrixAt(i, o.matrix); }); m.frustumCulled = false;
  const wire = new THREE.Line(new THREE.BufferGeometry().setFromPoints(pos.map(p => new THREE.Vector3(...p))), new THREE.LineBasicMaterial({ color: '#2a2a2a' }));
  const g = new THREE.Group(); g.add(m, wire); return { group: g, mat, base: new THREE.Color(color) };
}
export function wallSegment(B0, x0, z0, x1, z1, y, col = '#e2b07a', h = 3.2) { // town wall with crenellations (desert)
  const B = B0 || new Builder(), L = Math.hypot(x1 - x0, z1 - z0), ry = Math.atan2(x1 - x0, z1 - z0), T = frame((x0 + x1) / 2, y, (z0 + z1) / 2, ry + Math.PI / 2);
  box(B, T, 0, -.6, 0, L, h + .6, 1, C(col)); for (let k = -L / 2 + .5; k < L / 2; k += 1.4) box(B, T, k, h, 0, .7, .6, 1, shade(C(col), 1.05)); return B;
}
/** garden fences around the house lots, in the town's own style (front left open to the street). Returns { mesh, walls: [{x,z,hw,hd,rot}] } */
const FENCE = { tropical: { kind: 'picket', c: '#ffffff', c2: '#f2e6d0', h: .9 }, wetland: { kind: 'rail', c: '#6b4a2e', c2: '#5b3d26', h: 1 }, stargaze: { kind: 'wall', c: '#b8bdd6', c2: '#9aa0bf', h: .8 },
  winter: { kind: 'rail', c: '#7a4e32', c2: '#f6fbff', h: 1.05, snow: true }, desert: { kind: 'wall', c: '#e2b07a', c2: '#d9a066', h: .9 }, tech: { kind: 'hedge', c: '#4f8a3a', c2: '#3f7030', h: .8 } };
export function yardFences(styleName, lots, cols) {
  const F = FENCE[styleName] || FENCE.tropical, B = new Builder(), walls = [], c = C(F.c), c2 = C(F.c2);
  lots.forEach((l, i) => { const co = cols[i]; if (!co) return; const hw = Math.max(co.hw + .7, 3.6), back = -(Math.max(co.hd + .7, 3.6)), front = Math.min(hw * .6, 2.6), T = frame(l.x, l.y - .05, l.z, l.rot);
    const run = (x0, z0, x1, z1) => { const L = Math.hypot(x1 - x0, z1 - z0), ry = Math.atan2(x1 - x0, z1 - z0), cx = (x0 + x1) / 2, cz = (z0 + z1) / 2;
      // local frame of the run, expressed inside the lot frame
      const RT = (lx, ly, lz) => { const ca = Math.cos(ry), sa = Math.sin(ry); return T(cx + lx * ca + lz * sa, ly, cz - lx * sa + lz * ca); };
      if (F.kind === 'wall' || F.kind === 'hedge') { box(B, RT, 0, 0, 0, .34, F.h, L, c, F.kind === 'hedge' ? shade(c, 1.12) : c2); if (F.kind === 'wall') for (let k = -L / 2; k <= L / 2; k += 2.2) box(B, RT, 0, F.h, k, .42, .12, .42, c2); }
      else { const n = Math.max(2, Math.round(L / (F.kind === 'picket' ? .62 : 1.6)));
        for (let k = 0; k <= n; k++) { const z = -L / 2 + L * k / n; box(B, RT, 0, 0, z, F.kind === 'picket' ? .09 : .14, F.kind === 'picket' ? F.h : F.h + .1, F.kind === 'picket' ? .09 : .14, c, F.snow ? C('#f6fbff') : null); }
        for (const y of F.kind === 'picket' ? [.3, .65] : [.35, .75]) box(B, RT, F.kind === 'picket' ? -.06 : 0, y, 0, .05, .08, L, c2, F.snow && y > .5 ? C('#f6fbff') : null); }
      // collider in the town frame
      const wx = l.x + (cx * Math.cos(l.rot) + cz * Math.sin(l.rot)), wz = l.z + (-cx * Math.sin(l.rot) + cz * Math.cos(l.rot));
      walls.push({ x: wx, z: wz, hw: .22, hd: L / 2, rot: l.rot + ry }); };
    run(-hw, back, hw, back); run(-hw, back, -hw, front); run(hw, back, hw, front); });
  const mesh = new THREE.Mesh(B.geometry(), new THREE.MeshStandardMaterial({ vertexColors: true, roughness: .85 })); mesh.castShadow = true; mesh.receiveShadow = true;
  return { mesh, walls, tris: B.p.length / 9 };
}
export function fishingBoat(seed = 1) { // a small fishing boat: tapered hull, wheelhouse, mast with a flag (all one mesh)
  const R = (() => { let s = seed >>> 0 || 1; return () => ((s = (Math.imul(s, 1664525) + 1013904223) >>> 0) / 4294967296); })();
  const hullC = C(['#e2483c', '#2f7fd6', '#2fb3a5', '#f2c03d', '#ffffff'][(R() * 5) | 0]), trim = C('#f6f3ee'), wood = C('#8a6440'), B = new Builder(), T = frame(0, 0, 0, 0);
  const P = (x, y, z) => T(x, y, z);
  // hull: a prism, wide at the stern (−z), pointed bow (+z)
  const L = 4.2, W = 1.7, Hh = .8; const s0 = [-W / 2, 0, -L / 2], s1 = [W / 2, 0, -L / 2], b = [0, 0, L / 2 + .6], k0 = [-W * .3, -Hh, -L / 2 + .2], k1 = [W * .3, -Hh, -L / 2 + .2], kb = [0, -Hh * .6, L / 2];
  const tri = (a, b2, c, col) => B.tri(P(...a), P(...b2), P(...c), col);
  tri(s0, b, s1, shade(wood, 1.05)); tri(s0, k0, b, hullC); tri(k0, kb, b, shade(hullC, .9)); tri(s1, b, k1, shade(hullC, .8)); tri(k1, b, kb, shade(hullC, .75)); tri(s0, s1, k1, shade(hullC, .7)); tri(s0, k1, k0, shade(hullC, .7));
  box(B, T, 0, -.02, 0, W * .98, .12, .1, trim);
  box(B, T, 0, 0, -.7, 1.0, .9, 1.0, C('#f6f3ee'), C('#3a4450')); box(B, T, 0, .45, -.2, .9, .3, .04, C('#5ad8ff'));
  cyl(B, T, 0, 0, .7, .05, 2.4, wood, 5); box(B, T, .3, 2.0, .7, .55, .35, .03, C(['#ffd23c', '#e2483c', '#ffffff'][(R() * 3) | 0]));
  const g = new THREE.Group(), m = new THREE.Mesh(B.geometry(), new THREE.MeshStandardMaterial({ vertexColors: true, roughness: .7, side: THREE.DoubleSide })); m.castShadow = true; g.add(m); return g;
}
export { Builder, box, cyl, cone, dome, frame, C as col };
