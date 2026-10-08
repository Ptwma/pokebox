// Pokebox — the Relay Express: a little steam train between the towns' stations (fast travel with a ride).
// Procedural models (no downloads): a locomotive with a tall chimney and red wheels, two carriages, rails on sleepers,
// a station platform, and soft smoke puffs that rise and fade.
import * as THREE from 'three';

const M = (c, o = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: .7, metalness: 0, ...o });
const MAT = { body: M('#2f6fb3'), trim: M('#f2c94c', { metalness: .3, roughness: .4 }), dark: M('#2a2a33'), red: M('#c8402f'), wood: M('#8a5a36'), cab: M('#e9e2d0'), glass: M('#bfe3ff', { emissive: new THREE.Color('#ffd27a'), emissiveIntensity: .25 }), rail: M('#6f6a66', { metalness: .6, roughness: .45 }), sleeper: M('#5b3d26'), stone: M('#b9b2a6') };
const mesh = (g, m, x = 0, y = 0, z = 0, rx = 0, ry = 0, rz = 0) => { const o = new THREE.Mesh(g, m); o.position.set(x, y, z); o.rotation.set(rx, ry, rz); o.castShadow = true; o.receiveShadow = true; return o; };

/* the train faces +z; length ~ 19 m (loco 7 + 2 carriages 5.5 + gaps) */
export function makeTrain() {
  const g = new THREE.Group(), wheels = [];
  const wheel = (x, z, r = .55) => { const w = mesh(new THREE.CylinderGeometry(r, r, .22, 16), MAT.red, x, r, z, 0, 0, Math.PI / 2); wheels.push(w); g.add(w); const hub = mesh(new THREE.CylinderGeometry(r * .35, r * .35, .26, 8), MAT.trim, x, r, z, 0, 0, Math.PI / 2); wheels.push(hub); g.add(hub); };
  // locomotive (front at +z)
  const L = new THREE.Group(); L.position.z = 6.4; g.add(L);
  L.add(mesh(new THREE.BoxGeometry(2.2, .5, 6.6), MAT.dark, 0, .95, 0));                                      // frame
  L.add(mesh(new THREE.CylinderGeometry(1.0, 1.0, 4.2, 20), MAT.body, 0, 2.15, .9, Math.PI / 2));            // boiler
  for (const z of [-.6, .9, 2.4]) L.add(mesh(new THREE.TorusGeometry(1.02, .06, 6, 24), MAT.trim, 0, 2.15, z));
  L.add(mesh(new THREE.CylinderGeometry(1.02, 1.02, .2, 20), MAT.dark, 0, 2.15, 3.05, Math.PI / 2));          // smokebox door
  const chim = mesh(new THREE.CylinderGeometry(.42, .3, 1.3, 14), MAT.dark, 0, 3.7, 2.2); L.add(chim); L.add(mesh(new THREE.CylinderGeometry(.55, .42, .25, 14), MAT.dark, 0, 4.4, 2.2));
  L.add(mesh(new THREE.SphereGeometry(.38, 14, 10, 0, Math.PI * 2, 0, Math.PI / 2), MAT.trim, 0, 3.1, .6));     // dome
  L.add(mesh(new THREE.BoxGeometry(2.3, 2.5, 2.2), MAT.cab, 0, 2.45, -2.0));                                 // cab
  L.add(mesh(new THREE.BoxGeometry(2.6, .25, 2.7), MAT.red, 0, 3.8, -2.0));                                  // cab roof
  for (const x of [-1.16, 1.16]) L.add(mesh(new THREE.BoxGeometry(.04, .9, 1.1), MAT.glass, x, 2.9, -2.0));
  L.add(mesh(new THREE.BoxGeometry(2.0, .55, .5), MAT.red, 0, .85, 3.45));                                   // buffer beam
  L.add(mesh(new THREE.ConeGeometry(.8, 1.0, 4, 1, true), MAT.red, 0, .55, 3.7, Math.PI / 2, Math.PI / 4));   // cow-catcher
  const lamp = mesh(new THREE.SphereGeometry(.22, 10, 8), new THREE.MeshBasicMaterial({ color: '#fff3c4' }), 0, 2.9, 3.15); L.add(lamp);
  for (const z of [5.0, 6.6, 8.2]) { wheel(-1.05, z); wheel(1.05, z); }
  // two carriages
  for (const [k, z] of [[0, -.4], [1, -6.6]]) { const C = new THREE.Group(); C.position.z = z; g.add(C);
    C.add(mesh(new THREE.BoxGeometry(2.3, .4, 5.6), MAT.dark, 0, .95, 0));
    C.add(mesh(new THREE.BoxGeometry(2.4, 2.1, 5.6), k ? MAT.red : MAT.body, 0, 2.2, 0));
    C.add(mesh(new THREE.BoxGeometry(2.5, .22, 5.9), MAT.cab, 0, 3.35, 0)); C.add(mesh(new THREE.BoxGeometry(2.42, .14, 5.62), MAT.trim, 0, 1.25, 0));
    for (const zz of [-1.7, -.55, .6, 1.75]) for (const x of [-1.21, 1.21]) C.add(mesh(new THREE.BoxGeometry(.04, .8, .8), MAT.glass, x, 2.55, zz));
    for (const zz of [-1.9, 1.9]) { wheel(-1.05, z + zz); wheel(1.05, z + zz); } }
  g.userData = { wheels, chimney: new THREE.Vector3(0, 4.6, 8.6), door: new THREE.Vector3(1.6, 0, -.4) };
  return g;
}

/* rails + sleepers along local z in [-len/2, len/2], plus a platform on the +x side */
export function makeTrack(len = 90, ys = null) {
  const g = new THREE.Group(), n = Math.floor(len / 1.2);
  const sl = new THREE.InstancedMesh(new THREE.BoxGeometry(2.6, .16, .4), MAT.sleeper, n); const m4 = new THREE.Matrix4();
  for (let i = 0; i < n; i++) { const z = -len / 2 + i * 1.2, y = ys ? ys(z) : 0; m4.makeTranslation(0, y + .08, z); sl.setMatrixAt(i, m4); }
  sl.receiveShadow = true; g.add(sl);
  for (const x of [-.72, .72]) { const r = new THREE.Mesh(new THREE.BoxGeometry(.12, .14, len), MAT.rail); r.position.set(x, (ys ? ys(0) : 0) + .23, 0); r.receiveShadow = true; g.add(r); }
  const pf = new THREE.Mesh(new THREE.BoxGeometry(3.2, .7, 16), MAT.stone); pf.position.set(3.1, (ys ? ys(0) : 0) + .35, 0); pf.receiveShadow = pf.castShadow = true; g.add(pf);
  const edge = new THREE.Mesh(new THREE.BoxGeometry(.25, .06, 16), MAT.trim); edge.position.set(1.62, (ys ? ys(0) : 0) + .72, 0); g.add(edge);
  return g;
}

/* soft smoke puffs */
let PUFF = null;
function puffTex() { if (PUFF) return PUFF; const c = document.createElement('canvas'); c.width = c.height = 64; const x = c.getContext('2d'), gr = x.createRadialGradient(32, 32, 2, 32, 32, 30);
  gr.addColorStop(0, 'rgba(255,255,255,.95)'); gr.addColorStop(.6, 'rgba(235,235,240,.55)'); gr.addColorStop(1, 'rgba(230,230,235,0)'); x.fillStyle = gr; x.fillRect(0, 0, 64, 64);
  PUFF = new THREE.CanvasTexture(c); return PUFF; }
export function makeSmoke(n = 40) {
  const puffs = [], g = new THREE.Group();
  for (let i = 0; i < n; i++) { const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: puffTex(), transparent: true, depthWrite: false, opacity: 0 })); s.visible = false; g.add(s); puffs.push({ s, t: 9, vx: 0, vy: 0, vz: 0 }); }
  let k = 0, acc = 0;
  return { group: g, emit(pos, vel, rate, dt) { acc += rate * dt; while (acc > 1) { acc--; const p = puffs[k++ % n]; p.t = 0; p.s.position.copy(pos); p.vx = vel.x * .3 + (Math.random() - .5) * .6; p.vy = 1.8 + Math.random(); p.vz = vel.z * .3 + (Math.random() - .5) * .6; p.s.visible = true; } },
    update(dt) { for (const p of puffs) { if (p.t > 3.2) { p.s.visible = false; continue; } p.t += dt; p.s.position.x += p.vx * dt; p.s.position.y += p.vy * dt; p.s.position.z += p.vz * dt; p.vy *= .985; const sc = .8 + p.t * 1.6; p.s.scale.set(sc, sc, 1); p.s.material.opacity = Math.max(0, .75 * (1 - p.t / 3.2)); } } };
}
