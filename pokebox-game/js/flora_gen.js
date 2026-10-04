// Pokebox — anime-style procedural trees (the Genshin / Ghibli foliage trick):
// a canopy made of many small "leaf-card" quads with a painted leaf-cluster texture, whose normals point away from the
// canopy centre, so the whole crown shades like one soft cloud while the cut-out edges stay leafy. A dark inner core
// hides the gaps. Built once at load (no downloads) and registered as kit templates, so the existing instancing,
// wind sway, LOD and shadows all keep working.
import * as THREE from 'three';

function rnd(seed) { let s = seed >>> 0; return () => ((s = (Math.imul(s, 1664525) + 1013904223) >>> 0) / 4294967296); }

let LEAF = null;
function leafTex() {
  if (LEAF) return LEAF;
  const cv = document.createElement('canvas'); cv.width = cv.height = 128; const g = cv.getContext('2d'), R = rnd(7);
  for (let i = 0; i < 90; i++) { const a = R() * 6.283, rr = Math.sqrt(R()) * 50, x = 64 + Math.cos(a) * rr, y = 64 + Math.sin(a) * rr; g.save(); g.translate(x, y); g.rotate(R() * 6.283);
    const l = 58 + R() * 30; g.fillStyle = `hsl(0,0%,${l}%)`; g.beginPath(); g.ellipse(0, 0, 7 + R() * 3, 3.6 + R() * 1.4, 0, 0, 7); g.fill(); g.restore(); }
  LEAF = new THREE.CanvasTexture(cv); LEAF.colorSpace = THREE.SRGBColorSpace; LEAF.anisotropy = 2; return LEAF;
}
const MATS = {};
const leafMat = (hex) => MATS['l' + hex] ||= Object.assign(new THREE.MeshStandardMaterial({ map: leafTex(), color: new THREE.Color(hex), roughness: .9, metalness: 0, alphaTest: .5, side: THREE.DoubleSide }), { name: 'PX_Leaf' });
const coreMat = (hex) => MATS['c' + hex] ||= Object.assign(new THREE.MeshStandardMaterial({ color: new THREE.Color(hex).multiplyScalar(.42), roughness: 1 }), { name: 'PX_LeafCore' });
const barkMat = (hex) => MATS['b' + hex] ||= Object.assign(new THREE.MeshStandardMaterial({ color: new THREE.Color(hex), roughness: 1 }), { name: 'PX_Bark' });

/* leaf cards scattered on an ellipsoid shell (cx,cy,cz, rx,ry,rz); normals = direction from the crown centre */
function cards(R, list, C, n, size) {
  const P = [], N = [], U = [], I = []; const v = new THREE.Vector3(), up = new THREE.Vector3(), rt = new THREE.Vector3(), c = new THREE.Vector3(), nrm = new THREE.Vector3();
  for (const [cx, cy, cz, rx, ry, rz, k] of list) for (let i = 0; i < n * k; i++) {
    v.set(R() * 2 - 1, R() * 2 - 1, R() * 2 - 1); if (v.lengthSq() < 1e-4) continue; v.normalize(); if (v.y < -.55) v.y = -.55 + R() * .2;
    const d = .78 + R() * .3; c.set(cx + v.x * rx * d, cy + v.y * ry * d, cz + v.z * rz * d);
    nrm.copy(c).sub(C).normalize(); rt.set(R() * 2 - 1, R() * 2 - 1, R() * 2 - 1).normalize(); up.crossVectors(nrm, rt).normalize(); rt.crossVectors(up, nrm).normalize();
    const sz = size * (.8 + R() * .45), b = P.length / 3, ua = (R() * 4 | 0) * .5;
    for (const [a, bb, uu, vv] of [[-1, -1, 0, 0], [1, -1, 1, 0], [1, 1, 1, 1], [-1, 1, 0, 1]]) { P.push(c.x + (rt.x * a + up.x * bb) * sz, c.y + (rt.y * a + up.y * bb) * sz, c.z + (rt.z * a + up.z * bb) * sz); N.push(nrm.x, nrm.y, nrm.z); U.push(uu, vv); }
    I.push(b, b + 1, b + 2, b, b + 2, b + 3);
  }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(P, 3)); g.setAttribute('normal', new THREE.Float32BufferAttribute(N, 3)); g.setAttribute('uv', new THREE.Float32BufferAttribute(U, 2)); g.setIndex(I); return g;
}
/* solid inner blobs with the same spherised normals (fills the holes, gives the dark depth inside the crown) */
function core(list, C, k = .8) {
  const parts = list.map(([cx, cy, cz, rx, ry, rz]) => { const g = new THREE.IcosahedronGeometry(1, 1); g.scale(rx * k, ry * k, rz * k); g.translate(cx, cy, cz); return g; });
  let n = 0; for (const g of parts) n += g.attributes.position.count;
  const P = new Float32Array(n * 3), N = new Float32Array(n * 3); let o = 0; const v = new THREE.Vector3();
  for (const g of parts) { const p = g.attributes.position; for (let i = 0; i < p.count; i++) { v.fromBufferAttribute(p, i); P.set([v.x, v.y, v.z], (o + i) * 3); v.sub(C).normalize(); N.set([v.x, v.y, v.z], (o + i) * 3); } o += p.count; }
  const out = new THREE.BufferGeometry(); out.setAttribute('position', new THREE.BufferAttribute(P, 3)); out.setAttribute('normal', new THREE.BufferAttribute(N, 3)); return out;
}
function trunk(h, r0, r1, bend = 0) {
  const g = new THREE.CylinderGeometry(r1, r0, h, 7, 4); g.translate(0, h / 2, 0); const p = g.attributes.position;
  for (let i = 0; i < p.count; i++) { const t = p.getY(i) / h; p.setX(i, p.getX(i) + Math.sin(t * 2.2) * bend * t); } g.computeVertexNormals(); return g;
}
const mesh = (g, m, name) => { const o = new THREE.Mesh(g, m); o.name = name; o.castShadow = true; o.receiveShadow = true; return o; };

/** broadleaf tree: a few overlapping clumps on a short trunk. kind: 'round' | 'tall' | 'wide' */
export function roundTree(seed, { kind = 'round', leaf = '#5aa142', bark = '#6b4a32', lod = false } = {}) {
  const R = rnd(seed * 7919 + 13), G = new THREE.Group();
  const H = kind === 'tall' ? 4.2 : kind === 'wide' ? 2.6 : 3.2, cr = kind === 'wide' ? 3.2 : kind === 'tall' ? 2.2 : 2.6, ch = kind === 'tall' ? 3.4 : 2.4;
  G.add(mesh(trunk(H + ch * .4, .34, .2, (R() - .5) * .5), barkMat(bark), 'PX_Trunk'));
  const C = new THREE.Vector3(0, H + ch * .55, 0), list = [[0, C.y, 0, cr, ch, cr, 1.6]];
  const nClump = 3 + (R() * 3 | 0);
  for (let i = 0; i < nClump; i++) { const a = R() * 6.283, d = cr * (.45 + R() * .3); list.push([Math.cos(a) * d, C.y + (R() - .35) * ch * .7, Math.sin(a) * d, cr * (.55 + R() * .2), ch * (.5 + R() * .2), cr * (.55 + R() * .2), .7]); }
  G.add(mesh(core(list, C, lod ? .98 : .66), coreMat(leaf), lod ? 'PX_LeafCoreLOD' : 'PX_LeafCore'));
  if (lod) { G.children[1].material = MATS['lod' + leaf] ||= Object.assign(new THREE.MeshStandardMaterial({ color: new THREE.Color(leaf).multiplyScalar(.85), roughness: 1 }), { name: 'PX_LeafLOD' }); return G; }
  G.add(mesh(cards(R, list, C, 150, .5), leafMat(leaf), 'PX_Leaves'));
  return G;
}
/** conifer: stacked leaf-card cones */
export function pineTree(seed, { leaf = '#3f7d4a', bark = '#5a3f2c', lod = false } = {}) {
  const R = rnd(seed * 104729 + 7), G = new THREE.Group(), H = 7.5 + R() * 1.5;
  G.add(mesh(trunk(H * .55, .3, .16), barkMat(bark), 'PX_Trunk'));
  const C = new THREE.Vector3(0, H * .55, 0), list = [];
  const tiers = 5; for (let i = 0; i < tiers; i++) { const t = i / (tiers - 1), y = 1.6 + t * (H - 2.2), r = 2.3 * (1 - t * .78); list.push([0, y, 0, r, .9 - t * .25, r, 1 - t * .45]); }
  G.add(mesh(core(list, C, lod ? .95 : .8), coreMat(leaf), 'PX_LeafCore'));
  if (lod) return G;
  G.add(mesh(cards(R, list, C, 150, .42), leafMat(leaf), 'PX_Leaves'));
  return G;
}

/* scale a generated template so it occupies the same footprint/height as the kit model it replaces */
export function fitTo(obj, box) {
  const b = new THREE.Box3().setFromObject(obj), s = new THREE.Vector3(); b.getSize(s); const t = new THREE.Vector3(); box.getSize(t);
  const k = Math.min(t.y / s.y, Math.max(t.x, t.z) / Math.max(s.x, s.z) * 1.05); obj.scale.setScalar(k); obj.updateMatrixWorld(true); return obj;
}
