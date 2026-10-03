// Pokebox — building interiors you can walk into (like the Pokémon Center and the Poké Mart in the games).
// Each room is built once from flat-coloured boxes (town_gen Builder → one mesh) plus a few glowing parts, and lives far
// away from the island (world.js moves the player there and hides the outdoors while you are inside).
// A room describes itself as: { group, size:[w,d], spawn:{x,z}, boxes:[{x,z,hw,hd}] (blocked), spots:[{x,z,r,label,act}], people:[{x,z,face,look,name}] }
import * as THREE from 'three';
import { Builder, box, cyl, frame, col } from './town_gen.js';

const C = col;
function floor(B, w, d, a, b, tile = 2) { const T = frame(0, 0, 0, 0);
  for (let i = 0; i < w / tile; i++) for (let j = 0; j < d / tile; j++) { const x = -w / 2 + i * tile, z = -d / 2 + j * tile; B.quad(T(x, 0, z + tile), T(x + tile, 0, z + tile), T(x + tile, 0, z), T(x, 0, z), (i + j) % 2 ? a : b); } }
function walls(B, w, d, h, wall, band, doorW = 2.6) { const T = frame(0, 0, 0, 0);
  box(B, T, 0, 0, -d / 2 - .2, w + .8, h, .4, wall); for (const sx of [-1, 1]) { box(B, T, sx * (w / 2 + .2), 0, -d * .2, .4, h, d * .6, wall); box(B, T, sx * (w / 2 + .2), 0, d * .3, .4, 1, d * .4 + .4, wall); } // side walls step down toward the camera
  const side = (w - doorW) / 2; box(B, T, -w / 2 + side / 2, 0, d / 2 + .2, side, 1, .4, wall); box(B, T, w / 2 - side / 2, 0, d / 2 + .2, side, 1, .4, wall); // the front wall is cut away (dollhouse view, like the games)
  box(B, T, 0, .9, -d / 2 + .02, w, .35, .06, band); box(B, T, -w / 2 + .02, .9, 0, .06, .35, d, band); box(B, T, w / 2 - .02, .9, 0, .06, .35, d, band); // a coloured band at waist height
  box(B, T, 0, 0, -d / 2 + .05, w, .18, .1, C('#3a3448')); box(B, T, -w / 2 + .05, 0, 0, .1, .18, d, C('#3a3448')); box(B, T, w / 2 - .05, 0, 0, .1, .18, d, C('#3a3448')); }
const glowMat = c => new THREE.MeshBasicMaterial({ color: new THREE.Color(c).multiplyScalar(1.6) });
function glowBox(g, x, y, z, w, h, d, c) { const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), glowMat(c)); m.position.set(x, y + h / 2, z); g.add(m); return m; }
function plant(B, x, z) { const T = frame(x, 0, z, 0); cyl(B, T, 0, 0, 0, .35, .6, C('#c96a3a'), 8, C('#5a3a22')); for (const [dx, dz, h] of [[0, 0, 1.4], [.2, .1, 1.1], [-.2, -.1, 1.2]]) box(B, T, dx, .6, dz, .45, h, .45, C('#3f8a3a'), C('#5fae4f')); }

/** Relay Center: rest your team (saves, sets your respawn), a PC for your cards, a lounge */
export function relayCenter(townName = 'Relay Center') {
  const w = 18, d = 14, h = 4.6, B = new Builder(), g = new THREE.Group(), T = frame(0, 0, 0, 0);
  floor(B, w, d, C('#f4efe6'), C('#e3dccd')); walls(B, w, d, h, C('#fbf6ec'), C('#2fb3a5'));
  box(B, T, 0, 0, d / 2 - 1.5, 3, .02, 2.2, C('#2fb3a5'));                          // welcome mat
  box(B, T, 0, 0, -2.6, 9, 1.1, 1.1, C('#fbf6ec'), C('#2fb3a5')); box(B, T, 0, 1.1, -2.6, 9.2, .12, 1.3, C('#e8f6f3'));  // the counter
  box(B, T, 0, 0, -5.9, 5, 2.2, 1.2, C('#d8dde4'), C('#b8c2cc'));                    // healing machine body
  box(B, T, -6.6, 0, -5.6, 2.2, 1.9, 1.2, C('#3a4450'), C('#5a6470'));              // the PC terminal
  for (const x of [5.5, 7.4]) box(B, T, x, 0, 3.4, 1.8, .55, .9, C('#e2683c'), C('#f08a5a')); box(B, T, 6.45, 0, 4.1, 3.8, 1.1, .3, C('#c9553a'));  // sofa
  box(B, T, 6.4, 0, 2.2, 1.6, .5, .9, C('#8a6440'), C('#a07a52'));                   // low table
  plant(B, -8, 5.8); plant(B, 8, -5.8); plant(B, -8, -1.5); plant(B, 8, 5.8);
  const m = new THREE.Mesh(B.geometry(), new THREE.MeshStandardMaterial({ vertexColors: true, roughness: .8 })); m.receiveShadow = true; m.castShadow = true; g.add(m);
  // glowing parts: healing slots, PC screen, ceiling lights, windows
  const slots = []; for (let i = 0; i < 6; i++) slots.push(glowBox(g, -1.75 + i * .7, 2.22, -5.9, .5, .16, .5, '#5cf2d6'));
  glowBox(g, -6.6, 1.25, -4.98, 1.6, .9, .04, '#7fd8ff');
  for (const x of [-6, 6]) glowBox(g, x, 1.7, -d / 2 + .06, 2.2, 1.4, .04, '#bfe8ff');
  return { kind: 'relay', name: townName, group: g, size: [w, d], spawn: { x: 0, z: d / 2 - 1.4 }, slots,
    boxes: [{ x: 0, z: -2.6, hw: 4.6, hd: .65 }, { x: 0, z: -5.9, hw: 2.6, hd: .7 }, { x: -6.6, z: -5.6, hw: 1.2, hd: .7 }, { x: 6.45, z: 3.6, hw: 2, hd: .9 }, { x: 6.4, z: 2.2, hw: .9, hd: .5 },
      { x: -8, z: 5.8, hw: .45, hd: .45 }, { x: 8, z: -5.8, hw: .45, hd: .45 }, { x: -8, z: -1.5, hw: .45, hd: .45 }, { x: 8, z: 5.8, hw: .45, hd: .45 }],
    spots: [{ id: 'nurse', x: 0, z: -1.4, r: 2.2, label: 'Rest your team' }, { id: 'pc', x: -6.6, z: -4.3, r: 1.8, label: 'Use the Relay PC' }],
    people: [{ id: 'nurse', x: 0, z: -3.9, face: 0, arch: 'worker_f', name: 'Relay Nurse' }],
    sign: ['RELAY CENTER', townName, '#5cf2d6'] };
}
/** Card Shop: shelves of packs, the clerk at the till (opens the shop) */
export function cardShop() {
  const w = 14, d = 11, h = 4.2, B = new Builder(), g = new THREE.Group(), T = frame(0, 0, 0, 0);
  floor(B, w, d, C('#e8dcc8'), C('#d9cab0'), 1.4); walls(B, w, d, h, C('#fff4e0'), C('#ffd257'));
  box(B, T, 0, 0, d / 2 - 1.2, 2.6, .02, 1.6, C('#e2683c'));
  box(B, T, 3.4, 0, -2.2, 5, 1.05, 1, C('#7a4a2a'), C('#a06a42'));                   // till counter
  const PACKS = ['#e2483c', '#3d8fd6', '#5fae4f', '#ffd23c', '#c46bff', '#ff8fd0', '#2fb3a5', '#e2683c'];
  for (const [x, z, ry] of [[-6.2, -2.5, Math.PI / 2], [-6.2, 1.5, Math.PI / 2], [-1.5, -4.9, 0]]) { const S = frame(x, 0, z, ry);
    box(B, S, 0, 0, 0, 3.4, 2.4, .7, C('#8a6440')); for (let r = 0; r < 3; r++) for (let k = 0; k < 7; k++) box(B, S, -1.45 + k * .48, .35 + r * .7, .3, .32, .45, .1, C(PACKS[(k + r * 3) % PACKS.length])); }
  box(B, T, 0, 0, 0, 2.6, .9, 1.4, C('#fff4e0'), C('#ffd257'));                      // display table
  for (let k = 0; k < 5; k++) box(B, T, -.9 + k * .45, .9, 0, .3, .4, .08, C(PACKS[k]));
  plant(B, 6, 4.4); plant(B, -6, 4.4);
  const m = new THREE.Mesh(B.geometry(), new THREE.MeshStandardMaterial({ vertexColors: true, roughness: .8 })); m.receiveShadow = true; m.castShadow = true; g.add(m);
  return { kind: 'shop', name: 'Card Shop', group: g, size: [w, d], spawn: { x: 0, z: d / 2 - 1.2 },
    boxes: [{ x: 3.4, z: -2.2, hw: 2.6, hd: .6 }, { x: -6.2, z: -2.5, hw: .45, hd: 1.8 }, { x: -6.2, z: 1.5, hw: .45, hd: 1.8 }, { x: -1.5, z: -4.9, hw: 1.8, hd: .45 }, { x: 0, z: 0, hw: 1.4, hd: .8 }, { x: 6, z: 4.4, hw: .45, hd: .45 }, { x: -6, z: 4.4, hw: .45, hd: .45 }],
    spots: [{ id: 'clerk', x: 3.4, z: -1.1, r: 2.2, label: 'Buy packs & clothes' }, { id: 'shelf', x: -5.2, z: -.5, r: 2, label: 'Browse the shelves' }],
    people: [{ id: 'clerk', x: 3.4, z: -3.3, face: 0, arch: 'merchant', name: 'Shop Clerk' }],
    sign: ['CARD SHOP', 'Packs · Clothes', '#ffd257'] };
}
