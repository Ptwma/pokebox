// Pokebox world — CC0 model kits (Quaternius): loading, instancing, wind-swayed foliage, modular house builder.
import * as THREE from 'three';
import { loader } from './chars.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';


const DIR = new URL('../assets/world/', import.meta.url).href;
export const KITS = ['nature', 'pirate', 'village', 'scifi', 'nature_lod', 'toon_town', 'towns2']; // toon_town: bright Pokémon-style town kit made in Blender (tools/blender_toon_town.py) // nature_lod: the same trees simplified ~8x (far-away LOD)
const T = {}; // name -> template Object3D
export const wind = { value: 0 };
let kitsP = null;

const FOLIAGE = /Leaf|Leaves|Grass|Flower|Bush|Fern|Plant|Clover|Petal|Pine|Vine/i;
function prepMaterial(m) {
  if (m.userData.prepped) return m; m.userData.prepped = true;
  m.roughness = Math.max(.6, m.roughness ?? .8); m.metalness = Math.min(m.metalness ?? 0, .3); m.envMapIntensity = .9;
  if (FOLIAGE.test(m.name) || (m.map && m.transparent)) {
    m.alphaTest = .5; m.transparent = false; m.side = THREE.DoubleSide; m.depthWrite = true;
    m.userData.foliage = true;
    m.onBeforeCompile = sh => {
      sh.uniforms.uWind = wind;
      sh.vertexShader = 'uniform float uWind;\n' + sh.vertexShader.replace('#include <begin_vertex>', `#include <begin_vertex>
        #ifdef USE_INSTANCING
          vec2 wo = instanceMatrix[3].xz;
        #else
          vec2 wo = modelMatrix[3].xz;
        #endif
        float sway = sin(uWind * 1.6 + wo.x * .3 + wo.y * .2) * .6 + sin(uWind * 3.7 + transformed.y * 1.3 + wo.x) * .25;
        transformed.x += sway * .018 * max(transformed.y, 0.);
        transformed.z += cos(uWind * 1.3 + wo.y * .25) * .01 * max(transformed.y, 0.);`);
    };
    m.customProgramCacheKey = () => 'foliage';
  }
  return m;
}

export function loadKits() {
  if (kitsP) return kitsP;
  kitsP = Promise.all(KITS.map(k => loader.loadAsync(DIR + k + '.glb').then(g => {
    for (const o of g.scene.children.slice()) {
      o.traverse(c => { if (c.isMesh) { c.material = prepMaterial(c.material); c.castShadow = true; c.receiveShadow = true; } });
      o.position.set(0, 0, 0); o.updateMatrixWorld(true); T[o.name + (k === 'nature_lod' ? '_LOD' : '')] = o;
    }
  }).catch(e => console.warn('[kit] failed', k, e)))).then(() => Object.keys(T).length);
  return kitsP;
}
export const has = n => !!T[n];

/* size helpers */
const bbCache = {};
export function bounds(name) { if (!bbCache[name] && T[name]) bbCache[name] = new THREE.Box3().setFromObject(T[name]); return bbCache[name]; }

/* single placement (buildings, hero props) */
export function place(parent, name, x, y, z, { rot = 0, scale = 1, tint = null, shadow = true } = {}) {
  const t = T[name]; if (!t) return null;
  const o = t.clone(true); o.position.set(x, y, z); o.rotation.y = rot; o.scale.setScalar(scale);
  if (tint || !shadow) o.traverse(c => { if (c.isMesh) { if (tint) c.material = tinted(c.material, tint); c.castShadow = shadow; } });
  parent.add(o); return o;
}

/* colour variants of kit materials (e.g. snowy pines, autumn maples) */
const tintCache = new Map();
export function tinted(m, tint) {
  const key = m.uuid + JSON.stringify(tint); if (tintCache.has(key)) return tintCache.get(key);
  const t = typeof tint === 'string' ? { all: tint } : tint;
  const c = t.all || (m.userData.foliage ? t.leaf : t.other);
  if (!c) { tintCache.set(key, m); return m; }
  const n = m.clone(); n.color = m.color.clone().multiply(new THREE.Color(c)); n.userData = { ...m.userData }; n.onBeforeCompile = m.onBeforeCompile; n.customProgramCacheKey = m.customProgramCacheKey;
  tintCache.set(key, n); return n;
}

/* instancing: one InstancedMesh per sub-mesh of the template. list = [[x,y,z,rotY,scale], ...] */
const tmpM = new THREE.Matrix4(), tmpQ = new THREE.Quaternion(), tmpS = new THREE.Vector3(), tmpP = new THREE.Vector3(), UP = new THREE.Vector3(0, 1, 0);
export function instances(parent, name, list, { shadow = true, tint = null, receive = true, cell = 26 } = {}) {
  const t = T[name]; if (!t || !list.length) return [];
  // split into spatial cells so each InstancedMesh has a tight bounding sphere (frustum culling works)
  const cells = new Map();
  for (const it of list) { const k = Math.floor(it[0] / cell) + ',' + Math.floor(it[2] / cell); if (!cells.has(k)) cells.set(k, []); cells.get(k).push(it); }
  const out = [];
  t.traverse(c => {
    if (!c.isMesh) return;
    const rel = c.matrixWorld.clone(), mat = tint ? tinted(c.material, tint) : c.material;
    for (const part of cells.values()) {
      const im = new THREE.InstancedMesh(c.geometry, mat, part.length);
      part.forEach(([x, y, z, r = 0, s = 1], i) => { tmpQ.setFromAxisAngle(UP, r); tmpM.compose(tmpP.set(x, y, z), tmpQ, tmpS.set(s, s, s)).multiply(rel); im.setMatrixAt(i, tmpM); });
      im.instanceMatrix.needsUpdate = true; im.castShadow = shadow; im.receiveShadow = receive; im.computeBoundingSphere();
      parent.add(im); out.push(im);
    }
  });
  return out;
}

/* ================================================================== toon houses (toon_town kit, one palette material each)
   footprints in metres (front door at +z): S 5×5 one floor, M 6×6 two floors, L 8×6 two floors */
const TOON = {
  S: { w: 5, d: 5, roofs: ['red', 'blue', 'green', 'orange'] },
  M: { w: 6, d: 6, roofs: ['red', 'blue', 'purple'] },
  L: { w: 8, d: 6, roofs: ['teal', 'orange'] },
};
export const hasToon = () => !!T.TT_House_S_red;
export function toonHouse(parent, x, y, z, { w = 3, d = 3, floors = 1, rot = 0, seed = 1 } = {}) {
  const W = w * 2, D = d * 2, size = floors < 2 ? 'S' : Math.max(W, D) <= 6.5 ? 'M' : 'L', spec = TOON[size];
  const name = `TT_House_${size}_${spec.roofs[Math.abs(seed) % spec.roofs.length]}`;
  const sc = Math.min(1.35, Math.max(.8, Math.min(W / spec.w, D / spec.d) * 1.08));
  const o = place(parent, name, x, y - .05, z, { rot, scale: sc }); if (!o) return null;
  o.userData.radius = Math.hypot(spec.w, spec.d) * sc / 2; o.userData.W = spec.w * sc; o.userData.D = spec.d * sc;
  return o;
}

/* ================================================================== modular village house (Medieval Village MegaKit)
   walls are 2 m wide × 3 m tall; outer face = +z of each piece. w,d = modules (2 m each). */
const ROOFS = { '2x2': 'Roof_RoundTiles_4x4', '2x3': 'Roof_RoundTiles_4x6', '3x3': 'Roof_RoundTiles_6x6', '3x4': 'Roof_RoundTiles_6x8', '4x4': 'Roof_RoundTiles_8x8', '4x5': 'Roof_RoundTiles_8x10' };
export function house(parent, x, y, z, { w = 3, d = 3, floors = 1, rot = 0, wall = 'Plaster', seed = 1, door = 'front', shutters = true, chimney = true, vines = true, balcony = false } = {}) {
  if (hasToon()) return toonHouse(parent, x, y, z, { w, d, floors, rot, seed });
  const g = new THREE.Group(); g.position.set(x, y, z); g.rotation.y = rot; parent.add(g);
  let s = seed; const R = () => ((s = (Math.imul(s, 1664525) + 1013904223) >>> 0) / 4294967296);
  const W = w * 2, D = d * 2;
  const pieceWall = wall === 'Brick' ? 'Wall_UnevenBrick_Straight' : 'Wall_Plaster_Straight';
  const pieceWin = wall === 'Brick' ? 'Wall_UnevenBrick_Window_Wide_Round' : (R() < .5 ? 'Wall_Plaster_Window_Wide_Round' : 'Wall_Plaster_Window_Thin_Round');
  const pieceDoor = wall === 'Brick' ? 'Wall_UnevenBrick_Door_Round' : 'Wall_Plaster_Door_Round';
  const sides = [ // [axis origin fn, rotation, count]
    { n: w, pos: i => [-W / 2 + 1 + i * 2, D / 2], r: 0, key: 'front' },
    { n: w, pos: i => [W / 2 - 1 - i * 2, -D / 2], r: Math.PI, key: 'back' },
    { n: d, pos: i => [W / 2, D / 2 - 1 - i * 2], r: Math.PI / 2, key: 'right' },
    { n: d, pos: i => [-W / 2, -D / 2 + 1 + i * 2], r: -Math.PI / 2, key: 'left' },
  ];
  for (let f = 0; f < floors; f++) {
    const fy = f * 3;
    for (const sd of sides) for (let i = 0; i < sd.n; i++) {
      const [px, pz] = sd.pos(i), isDoor = f === 0 && sd.key === door && i === Math.floor(sd.n / 2);
      const isWin = !isDoor && (f > 0 || R() < .7) && !(sd.n > 2 && (i === 0 || i === sd.n - 1) && R() < .4);
      const name = isDoor ? pieceDoor : isWin ? pieceWin : (f > 0 && wall !== 'Brick' && R() < .35 ? 'Wall_Plaster_WoodGrid' : pieceWall);
      place(g, name, px, fy, pz, { rot: sd.r });
      if (isDoor) place(g, 'Door_1_Round', px - .53, fy, pz - .1, { rot: sd.r });
      if (isWin) { place(g, /Thin/.test(name) ? 'Window_Thin_Round1' : 'Window_Wide_Round1', px, fy, pz, { rot: sd.r, shadow: false });
        if (shutters && R() < .6) place(g, /Thin/.test(name) ? 'WindowShutters_Thin_Round_Open' : 'WindowShutters_Wide_Round_Open', px, fy, pz, { rot: sd.r, shadow: false }); }
      if (vines && f === 0 && !isDoor && R() < .18) place(g, R() < .5 ? 'Prop_Vine1' : 'Prop_Vine4', px + (R() - .5), fy + 2.6, pz + .12 * (sd.r === 0 ? 1 : -1), { rot: sd.r, shadow: false });
      if (balcony && f === 1 && sd.key === 'front' && isWin) place(g, 'Balcony_Simple_Straight', px, fy, pz - .9, { rot: sd.r });
    }
    for (const [cx, cz] of [[W / 2, D / 2], [-W / 2, D / 2], [W / 2, -D / 2], [-W / 2, -D / 2]]) place(g, wall === 'Brick' ? 'Corner_Exterior_Brick' : 'Corner_Exterior_Wood', cx, fy, cz, { rot: Math.atan2(cx, cz) - Math.PI / 4 });
  }
  // floor + roof
  for (let i = 0; i < w; i++) for (let j = 0; j < d; j++) place(g, 'Floor_WoodDark', -W / 2 + 1 + i * 2, .02, -D / 2 + 1 + j * 2, { shadow: false });
  const key = w <= d ? `${w}x${d}` : `${d}x${w}`, roofName = ROOFS[key] || 'Roof_RoundTiles_6x6', roofRot = w <= d ? 0 : Math.PI / 2;
  const roof = place(g, roofName, 0, floors * 3, 0, { rot: roofRot });
  const gw = w <= d ? W : D, gable = 'Roof_Front_Brick' + gw;
  if (w <= d) { place(g, gable, 0, floors * 3, D / 2, { rot: 0 }); place(g, gable, 0, floors * 3, -D / 2, { rot: Math.PI }); }
  else { place(g, gable, W / 2, floors * 3, 0, { rot: Math.PI / 2 }); place(g, gable, -W / 2, floors * 3, 0, { rot: -Math.PI / 2 }); }
  if (chimney) place(g, 'Prop_Chimney', W / 2 - 1.1, floors * 3 + .3, -D / 2 + 1.2);
  mergeStatic(g);
  g.userData.radius = Math.hypot(W, D) / 2; g.userData.W = W; g.userData.D = D;
  return g;
}

/* ================================================================== static batching: merge every mesh of a group by material (fewer draw calls) */
function toFloat(geo) {
  const g = new THREE.BufferGeometry();
  for (const name of ['position', 'normal', 'uv']) {
    const a = geo.getAttribute(name); if (!a) { if (name === 'uv') g.setAttribute('uv', new THREE.Float32BufferAttribute(new Float32Array(geo.getAttribute('position').count * 2), 2)); continue; }
    const out = new Float32Array(a.count * a.itemSize);
    for (let i = 0; i < a.count; i++) for (let k = 0; k < a.itemSize; k++) out[i * a.itemSize + k] = a.getComponent(i, k);
    g.setAttribute(name, new THREE.BufferAttribute(out, a.itemSize));
  }
  if (!g.getAttribute('normal')) g.computeVertexNormals();
  const idx = geo.index ? Array.from(geo.index.array) : Array.from({ length: geo.getAttribute('position').count }, (_, i) => i);
  g.setIndex(idx); return g;
}
export function mergeStatic(group, { shadow = true } = {}) {
  group.updateMatrixWorld(true); const inv = new THREE.Matrix4().copy(group.matrixWorld).invert();
  const buckets = new Map(), kill = [];
  group.traverse(o => { if (!o.isMesh || o.isInstancedMesh || o.isSkinnedMesh) return;
    const g = toFloat(o.geometry); g.applyMatrix4(new THREE.Matrix4().multiplyMatrices(inv, o.matrixWorld));
    const k = o.material.uuid; if (!buckets.has(k)) buckets.set(k, { m: o.material, list: [], cast: false }); const b = buckets.get(k); b.list.push(g); b.cast ||= o.castShadow; kill.push(o); });
  for (const o of kill) o.parent.remove(o);
  for (const [, b] of buckets) { const geo = mergeGeometries(b.list, false); if (!geo) continue; b.list.forEach(x => x.dispose()); const m = new THREE.Mesh(geo, b.m); m.castShadow = shadow && b.cast; m.receiveShadow = true; group.add(m); }
  // drop now-empty helper nodes
  const empties = []; group.traverse(o => { if (o !== group && !o.isMesh && o.children.length === 0) empties.push(o); }); empties.forEach(o => o.parent?.remove(o));
  return group;
}
