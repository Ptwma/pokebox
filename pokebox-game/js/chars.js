// Pokebox — rigged, animated people and pets for the 3D world.
// People: Quaternius "Ultimate Modular Men/Women" (CC0) — modern outfits, 10 shared animations per model.
// Pets / Echo shells: Quaternius "Cute Animated Monsters" (CC0).
// The trainer look is applied by recolouring the model's named materials (Skin / Hair / main outfit colour)
// plus primitive headwear & accessories parented to the Head bone. Models load lazily and are cached.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import * as SkeletonUtils from 'three/addons/utils/SkeletonUtils.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import * as P from './progress.js';
import { applyComic } from './comic.js';

const DIR = new URL('../assets/', import.meta.url).href;
export const loader = new GLTFLoader(); loader.setMeshoptDecoder(MeshoptDecoder);

// outfit -> [male model, female model] — anime trainers built in Blender (tools/blender_chars.py) on the Quaternius rigs,
// so they keep all 10 animations. Old Quaternius models stay in chars/men|women for reference only.
const OUTFIT = {
  tee: ['m_tee', 'f_tee'], hoodie: ['m_hoodie', 'f_hoodie'], jacket: ['m_jacket', 'f_jacket'], ranger: ['m_vest', 'f_vest'],
  labcoat: ['m_coat', 'f_coat'], robe: ['m_coat', 'f_coat'], scarf: ['m_jacket', 'f_skirt'], bomber: ['m_jacket', 'f_jacket'],
  crew: ['m_vest', 'f_vest'], relay: ['m_hoodie', 'f_hoodie'], summer: ['m_tee', 'f_skirt'],
};
const HIDE = /Pistol|Sword/i;
const NOT_OUTFIT = /Skin|^Eye|Hair|Eyebrow|Moustache|Earring|Visor|Metal|Gold|Pupil|Mouth|Blush|Inner|Belt|Buckle|Sole|Shoes|Pants|Skirt/i;
export const modelFor = L => { if (L.model) return 'chars/anime/' + L.model; const o = OUTFIT[L.top] || OUTFIT.tee; return 'chars/anime/' + o[L.body === 'f' ? 1 : 0]; };
const ANIME = p => p.startsWith('chars/anime/');

const cache = new Map();
export function loadGLB(path) {
  if (!cache.has(path)) cache.set(path, loader.loadAsync(DIR + path + '.glb').then(g => { g.scene.traverse(o => { if (o.isMesh) { o.castShadow = true; o.frustumCulled = false; } }); return g; })
    .catch(e => { console.warn('[chars] failed', path, e); cache.delete(path); return null; }));
  return cache.get(path);
}
const ready = new Map(); // path -> gltf (resolved)
/* people animations: Quaternius Universal Animation Library 1+2 (CC0, 84 clips), packed to rotations + pelvis motion */
let ualClips = null, ualP = null;
function loadUAL() {
  return ualP ||= Promise.all(['chars/anime/ual1.glb', 'chars/anime/ual2.glb'].map(f => loader.loadAsync(DIR + f).then(g => g.animations).catch(e => { console.warn('[chars] UAL', f, e); return []; })))
    .then(a => { ualClips = a.flat(); });
}
export async function prepare(looks = [], pets = []) {
  loadUAL();
  const paths = [...new Set([...looks.map(modelFor), ...pets.map(p => 'pets/' + p)])];
  const res = await Promise.all(paths.map(loadGLB)); paths.forEach((p, i) => res[i] && ready.set(p, res[i]));
  await loadUAL();
  return res.every(Boolean);
}
export const isReady = path => ready.has(path);
export const kitReady = () => ready.size > 0; // legacy
export const loadKit = () => prepare([{ top: 'tee', body: 'm' }]);

/* ---------- which material is the "main outfit colour" of a model: most triangles on the body mesh that isn't skin/hair/eyes */
const mainMat = new Map();
function outfitMaterial(path, scene) {
  if (mainMat.has(path)) return mainMat.get(path);
  const tally = {};
  scene.traverse(o => {
    if (!o.isMesh || !/Body/i.test(o.name + (o.parent?.name || ''))) return;
    const m = o.material; if (NOT_OUTFIT.test(m.name)) return;
    tally[m.name] = (tally[m.name] || 0) + (o.geometry.index ? o.geometry.index.count : o.geometry.attributes.position.count) / 3;
  });
  if (tally.Outfit || (() => { let f = false; scene.traverse(o => { if (o.material?.name === 'Outfit') f = true; }); return f; })()) { mainMat.set(path, 'Outfit'); return 'Outfit'; }
  const best = Object.entries(tally).sort((a, b) => b[1] - a[1])[0]?.[0] || null; mainMat.set(path, best); return best;
}

/* ---------- headwear & accessories (built in "head units": 1 = head width) */
const RAMP = (() => { const d = new Uint8Array([120, 185, 255]); const t = new THREE.DataTexture(d, 3, 1, THREE.RedFormat); t.minFilter = t.magFilter = THREE.NearestFilter; t.needsUpdate = true; return t; })();
const std = (c, o = {}) => new THREE.MeshStandardMaterial({ color: new THREE.Color(c), roughness: .7, metalness: 0, ...o });
const HAT = {
  cap: c => { const g = new THREE.Group(); const top = new THREE.Mesh(new THREE.SphereGeometry(.56, 22, 10, 0, Math.PI * 2, 0, Math.PI / 2), std(c)); top.scale.y = .78;
    const brim = new THREE.Mesh(new THREE.CylinderGeometry(.42, .42, .05, 20, 1, false, -Math.PI / 2, Math.PI), std(new THREE.Color(c).multiplyScalar(.7))); brim.position.set(0, .02, .36); brim.scale.z = 1.3;
    const logo = new THREE.Mesh(new THREE.CircleGeometry(.12, 16), std('#ffffff')); logo.position.set(0, .26, .48); logo.rotation.x = -.5; g.add(top, brim, logo); return g; },
  beanie: c => { const g = new THREE.Group(); const m = new THREE.Mesh(new THREE.SphereGeometry(.57, 22, 12, 0, Math.PI * 2, 0, Math.PI / 1.9), std(c, { roughness: .95 })); const rim = new THREE.Mesh(new THREE.TorusGeometry(.55, .07, 8, 28), std(new THREE.Color(c).multiplyScalar(.8), { roughness: .95 })); rim.rotation.x = Math.PI / 2; rim.position.y = -.02;
    const b = new THREE.Mesh(new THREE.SphereGeometry(.13, 10, 8), std('#fff', { roughness: 1 })); b.position.y = .58; g.add(m, rim, b); return g; },
  visor: c => { const g = new THREE.Group(); const band = new THREE.Mesh(new THREE.TorusGeometry(.55, .05, 8, 28), std(c)); band.rotation.x = Math.PI / 2; band.position.y = .05;
    const brim = new THREE.Mesh(new THREE.CylinderGeometry(.36, .36, .04, 16, 1, false, -Math.PI / 2, Math.PI), std(c)); brim.position.set(0, .05, .4); g.add(band, brim); return g; },
  phones: c => { const g = new THREE.Group(); const arc = new THREE.Mesh(new THREE.TorusGeometry(.6, .05, 8, 20, Math.PI), std('#2a2a30', { metalness: .4, roughness: .4 })); arc.position.y = -.15;
    for (const s of [-1, 1]) { const cup = new THREE.Mesh(new THREE.CylinderGeometry(.17, .17, .14, 14), std(c)); cup.rotation.z = Math.PI / 2; cup.position.set(s * .6, -.15, 0); g.add(cup); } g.add(arc); return g; },
  beret: c => { const m = new THREE.Mesh(new THREE.SphereGeometry(.62, 20, 10), std(c, { roughness: .95 })); m.scale.set(1, .32, 1); m.position.set(.06, .15, -.02); m.rotation.z = -.2; return m; },
  wide: c => { const g = new THREE.Group(); const brim = new THREE.Mesh(new THREE.CylinderGeometry(1.05, 1.05, .05, 26), std(new THREE.Color(c).multiplyScalar(.75))); brim.position.y = 0;
    const crown = new THREE.Mesh(new THREE.CylinderGeometry(.44, .52, .4, 18), std(c)); crown.position.y = .2; const band = new THREE.Mesh(new THREE.CylinderGeometry(.53, .53, .1, 18), std('#3a2a1a')); band.position.y = .06; g.add(brim, crown, band); return g; },
  crown: () => { const m = new THREE.Mesh(new THREE.TorusGeometry(.5, .07, 8, 26), std('#e7c14a', { metalness: .8, roughness: .3, emissive: new THREE.Color('#3a2a00') })); m.rotation.x = Math.PI / 2; m.position.y = .02; return m; },
};
function accessory(id) {
  const g = new THREE.Group(), dark = std('#2a2430', { metalness: .3, roughness: .4 });
  if (id === 'glasses' || id === 'monocle') for (const s of id === 'monocle' ? [1] : [-1, 1]) { const r = new THREE.Mesh(new THREE.TorusGeometry(.12, .022, 6, 16), id === 'monocle' ? std('#c9a24a', { metalness: .8, roughness: .3 }) : dark); r.position.set(s * .2, 0, .5); g.add(r); }
  if (id === 'goggles') { const gg = new THREE.Mesh(new THREE.TorusGeometry(.56, .06, 8, 28), dark); gg.rotation.x = Math.PI / 2 - .25; gg.position.y = .32; g.add(gg); for (const s of [-1, 1]) { const l = new THREE.Mesh(new THREE.CylinderGeometry(.14, .14, .08, 14), std('#7fd3ff', { metalness: .2, roughness: .1, emissive: new THREE.Color('#10324a') })); l.rotation.x = Math.PI / 2 - .25; l.position.set(s * .21, .42, .45); g.add(l); } }
  if (id === 'mask') { const m = new THREE.Mesh(new THREE.SphereGeometry(.53, 16, 8, -Math.PI / 2, Math.PI, Math.PI * .55, Math.PI * .3), std('#1e2126')); g.add(m); }
  if (id === 'earring') for (const s of [-1, 1]) { const e = new THREE.Mesh(new THREE.OctahedronGeometry(.06), std('#5cf2d6', { emissive: new THREE.Color('#0b6d62') })); e.position.set(s * .5, -.22, 0); g.add(e); }
  return g;
}

/* ---------- animation aliases (old KayKit names -> Quaternius names) */
const ALIAS = { Cheer: 'Wave', PickUp: 'Interact', Spellcast_Shoot: 'Interact', Walking_A: 'Walk', Running_A: 'Run', Unarmed_Idle: 'Idle', Hit_A: 'HitRecieve',
  // Universal Animation Library names (people are built on that skeleton)
  Idle: 'Idle_Loop', Walk: 'Walk_Loop', Run: 'Jog_Fwd_Loop', Sprint: 'Sprint_Loop', Wave: 'Yes', Idle_Neutral: 'Idle_Loop', HitRecieve: 'Hit_Chest', Death: 'Death01', Punch_Right: 'Punch_Cross' };
const tmpV = new THREE.Vector3(), tmpS = new THREE.Vector3();

function rigActor(obj, clips, { height }) {
  const mixer = new THREE.AnimationMixer(obj), acts = {}, byName = Object.fromEntries(clips.map(c => [c.name, c]));
  const act = n => { n = byName[n] ? n : ALIAS[n] || n; return acts[n] ||= byName[n] ? mixer.clipAction(byName[n]) : null; };
  let cur = null, oneShot = false;
  function play(n, fade = .25, { once = false, speed = 1 } = {}) {
    const a = act(n); if (!a || (a === cur && !once)) return false;
    a.reset(); a.setEffectiveTimeScale(speed); a.setEffectiveWeight(1); a.clampWhenFinished = once; a.setLoop(once ? THREE.LoopOnce : THREE.LoopRepeat, Infinity); a.play();
    if (cur && cur !== a) cur.crossFadeTo(a, fade, false); cur = a; oneShot = once; return true;
  }
  mixer.addEventListener('finished', () => { oneShot = false; });
  return { mixer, play, busy: () => oneShot, get current() { return cur; }, has: n => !!act(n) };
}

/* the character pack is low-poly with hard (per-face) normals: under cel shading every face became its own block.
   Averaging the normals of vertices that share a position gives smooth, anime-like light bands (done once per geometry). */
function smoothGeo(geo) {
  if (!geo || geo.userData.smooth || !geo.attributes.normal) return; geo.userData.smooth = true;
  const p = geo.attributes.position, n = geo.attributes.normal, acc = new Map(), key = i => `${Math.round(p.getX(i) * 1e4)},${Math.round(p.getY(i) * 1e4)},${Math.round(p.getZ(i) * 1e4)}`;
  for (let i = 0; i < p.count; i++) { const k = key(i), a = acc.get(k) || [0, 0, 0]; a[0] += n.getX(i); a[1] += n.getY(i); a[2] += n.getZ(i); acc.set(k, a); }
  for (let i = 0; i < p.count; i++) { const a = acc.get(key(i)), l = Math.hypot(a[0], a[1], a[2]) || 1; n.setXYZ(i, a[0] / l, a[1] / l, a[2] / l); }
  n.needsUpdate = true;
}

const mergedCache = new Map();
function mergedGeo(path, meshes) {
  if (mergedCache.has(path)) return mergedCache.get(path);
  let geo = null;
  try {
    const KEEP = ['position', 'normal', 'skinIndex', 'skinWeight'];
    const geos = meshes.map((o, i) => { const g = o.geometry.clone(); for (const k of Object.keys(g.attributes)) if (!KEEP.includes(k)) g.deleteAttribute(k);
      g.setAttribute('mid', new THREE.Float32BufferAttribute(new Float32Array(g.attributes.position.count).fill(i), 1)); g.morphAttributes = {}; return g; });
    geo = mergeGeometries(geos, false); if (geo) geo.computeBoundingSphere();
  } catch (e) { console.warn('[chars] merge failed', path, e); geo = null; }
  mergedCache.set(path, geo); return geo;
}
function mergedMaterial(cols) {
  const m = new THREE.MeshStandardMaterial({ color: '#ffffff', roughness: .85, metalness: 0 }); m.name = 'PersonPalette'; m.userData.actor = true;
  const u = { value: cols };
  m.onBeforeCompile = sh => {
    sh.uniforms.uCols = u;
    sh.vertexShader = 'attribute float mid;\nvarying float vMid;\n' + sh.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\n  vMid = mid;');
    sh.fragmentShader = 'uniform vec3 uCols[16];\nvarying float vMid;\n' + sh.fragmentShader.replace('vec4 diffuseColor = vec4( diffuse, opacity );', 'vec4 diffuseColor = vec4( uCols[int(vMid + .5)], opacity );');
  };
  m.customProgramCacheKey = () => 'pbxPerson';
  return m;
}

/* ---------- people */
const matCache = new Map();
export const STYLE = { head: 1.3, feet: 1.12 };
export function makeRigged(look, { scale = 1, hat, height = 2.0 } = {}) {
  const L = Object.assign({ body: 'm', skin: 'sk2', hairColor: 'hc1', hat: 'none', top: 'tee', topColor: 'tc1', acc: 'none' }, look);
  height *= L.h || 1; // body height: kids, elders, tall athletes
  const path = modelFor(L), gltf = ready.get(path);
  if (!gltf) return null;
  const obj = SkeletonUtils.clone(gltf.scene);
  const skin = P.item('skin', L.skin).c, hair = P.item('hairColor', L.hairColor).c;
  const outfit = L.top === 'labcoat' ? '#f1f1ee' : P.item('topColor', L.topColor).c, main = outfitMaterial(path, gltf.scene);
  const COL = L.colors || {}, key = [path, skin, hair, outfit, COL.Outfit, COL.Inner, COL.Pants, COL.Shoes].join('|');
  obj.traverse(o => {
    if (!o.isMesh) return; if (HIDE.test(o.name + ' ' + (o.parent?.name || ''))) { o.visible = false; return; }
    const src = o.material, mk = key + '|' + src.name;
    let m = matCache.get(mk);
    if (!m) {
      m = src.clone(); m.roughness = Math.max(.55, m.roughness ?? .8); m.metalness = /Metal|Gold|Visor/i.test(src.name) ? .6 : 0;
      // anime palette: clean, slightly pastel colours (no extra saturation — it read as orange skin / plastic clothes)
      if (/^Skin/i.test(src.name)) { m.color.set(skin).multiplyScalar(/Darker/i.test(src.name) ? .92 : 1); m.color.offsetHSL(0, -.04, .02); m.roughness = 1; }
      else if (/Hair|Eyebrow|Moustache/i.test(src.name)) { m.color.set(hair).multiplyScalar(/Eyebrow/i.test(src.name) ? .6 : 1); m.roughness = .5; }
      else if (/^Eye$/i.test(src.name)) { m.color.multiplyScalar(.7); m.roughness = .3; }
      else if (src.name === 'Inner' && COL.Inner && COL.Outfit) { m.color.set(COL.Outfit).lerp(new THREE.Color(COL.Inner), .3); m.roughness = .9; } // the shirt under a vest: a softer tone, never a bright patch
      else if (COL[src.name] && src.name !== 'Hair') { m.color.set(COL[src.name]); m.roughness = /Shoes/.test(src.name) ? .6 : .9; } // a coordinated outfit (role / region wardrobe)
      else if (src.name === main) { m.color.set(outfit); m.color.offsetHSL(0, -.03, .03); m.roughness = .9; }
      else { m.color.offsetHSL(0, -.06, .04); m.roughness = .9; }
      m.flatShading = false; m.userData.actor = true;
      matCache.set(mk, m);
    }
    o.material = m; o.castShadow = true; o.receiveShadow = false;
    smoothGeo(o.geometry);
  });
  // one draw call per person: the anime models are a single node with ~15 primitives (one per colour). Merge them into one
  // skinned geometry with a per-vertex colour slot and give each person a small colour table instead of 15 materials.
  if (ANIME(path)) {
    const parts = []; obj.traverse(o => { if (o.isSkinnedMesh && o.visible) parts.push(o); });
    const geo = parts.length > 1 && mergedGeo(path, parts);
    if (geo) {
      const cols = parts.map(o => o.material.color.clone()); while (cols.length < 16) cols.push(new THREE.Color(1, 1, 1));
      parts.forEach((o, i) => { if (/EyeShine/.test(o.material.name)) cols[i].multiplyScalar(1.6); });
      const keep = parts[0]; keep.geometry = geo; keep.material = mergedMaterial(cols.slice(0, 16)); keep.castShadow = true; keep.frustumCulled = false;
      for (const o of parts.slice(1)) o.parent?.remove(o);
    }
  }
  // normalise height: measure the bind pose once per model
  let hgt = gltf.userData.h; if (!hgt) { const b = new THREE.Box3().setFromObject(gltf.scene, true); hgt = gltf.userData.h = Math.max(.1, b.max.y - b.min.y); }
  const g = new THREE.Group(); const k = height / hgt * scale; obj.scale.setScalar(k); g.add(obj);
  let head = null; obj.traverse(o => { if (!head && o.isBone && /^Head$/i.test(o.name)) head = o; });
  const hatId = hat && hat !== 'model' ? hat : L.hat;
  if (head) {
    obj.updateMatrixWorld(true); head.getWorldScale(tmpS); const an = ANIME(path), hs = .285 * (an ? 1.43 : 1) * height / 2.3 / tmpS.x; // head units -> bone space (1 unit ≈ head width)
    const mount = new THREE.Group(); mount.scale.setScalar(hs); mount.position.set(0, (an ? .29 : .2) * height / 2.3 / tmpS.y, (an ? .02 : .01) / tmpS.z); head.add(mount);
    if (HAT[hatId] && !/King|Witch|Worker|Farmer|Swat|Spacesuit/.test(path)) mount.add(HAT[hatId](L.top === 'labcoat' ? '#3d8fd6' : hatId === 'beanie' && COL.Inner ? COL.Inner : hatId === 'wide' && COL.Pants ? '#d8c08a' : COL.Outfit || outfit));
    if (L.acc && L.acc !== 'none' && !/Spacesuit|Swat/.test(path)) { const a = accessory(L.acc); a.position.y = -.38; mount.add(a); }
  }
  // anime / Pokémon-trainer proportions: bigger head (hats & accessories ride along), slightly bigger feet
  if (ANIME(path) && head && !L.kidHead) head.scale.setScalar(L.model?.startsWith('kid') ? 1.05 : 1.14); // a touch more Pokémon-trainer: bigger, friendlier heads
  if (!ANIME(path)) { // the anime trainers are modelled with these proportions already
    if (head) head.scale.setScalar(STYLE.head);
    obj.traverse(o => { if (o.isBone && /^Foot\./.test(o.name)) o.scale.setScalar(STYLE.feet); });
  }
  applyComic(obj); // no ink hull: the black outline around characters is gone
  const blob = new THREE.Mesh(new THREE.CircleGeometry(.55, 20), new THREE.MeshBasicMaterial({ color: '#000', transparent: true, opacity: .2, depthWrite: false })); blob.rotation.x = -Math.PI / 2; blob.position.y = .03; g.add(blob);
  const R = rigActor(obj, ANIME(path) && ualClips ? ualClips : gltf.animations, { height });
  // state: 'air' (jumping / gliding), 'swim' (deep water), 'climb' (scrambling up a steep slope) — falls back to walking if a clip is missing
  function locomote(speed, state) {
    if (R.busy()) return;
    if (state === 'air' && R.has('Jump_Loop')) { R.play('Jump_Loop', .18); return; }
    if (state === 'swim' && R.has('Swim_Fwd_Loop')) { R.play(speed > .35 ? 'Swim_Fwd_Loop' : 'Swim_Idle_Loop', .3); if (speed > .35) R.current.setEffectiveTimeScale(THREE.MathUtils.clamp(speed / 3.5, .8, 1.5)); return; }
    if (state === 'climb' && speed > .35 && R.has('ClimbUp_1m')) { R.play('ClimbUp_1m', .25); R.current.setEffectiveTimeScale(.9); return; }
    if (speed < .35) R.play('Idle', .3);
    else if (speed < 6.4) { R.play('Walk', .22); R.current.setEffectiveTimeScale(THREE.MathUtils.clamp(speed / 3.4, .7, 1.6)); }
    else if (speed > 9.5 && R.has('Sprint')) { R.play('Sprint', .25); R.current.setEffectiveTimeScale(THREE.MathUtils.clamp(speed / 10, .85, 1.3)); }
    else { R.play('Run', .2); R.current.setEffectiveTimeScale(THREE.MathUtils.clamp(speed / 7.8, .85, 1.35)); }
  }
  R.play('Idle', 0); R.mixer.update(Math.random() * 2);
  let hand = null; obj.traverse(o => { if (!hand && o.isBone && /^(Wrist\.R|hand_r)$/.test(o.name)) hand = o; });
  return { group: g, model: path, mixer: R.mixer, play: R.play, locomote, busy: R.busy, update: dt => R.mixer.update(dt), parts: { head: head || g, hand }, rigged: true };
}

/* ---------- pets / Echo shells */
export const PETS = {
  Panda: { type: 'Fighting', name: 'Pandle' }, Penguin: { type: 'Water', name: 'Pengo' }, Crab: { type: 'Water', name: 'Clampy' }, Yeti: { type: 'Water', name: 'Yetling' },
  Cactus: { type: 'Grass', name: 'Spikit' }, Mushroom: { type: 'Grass', name: 'Mossle' }, Tree: { type: 'Grass', name: 'Twiglet' }, Deer: { type: 'Grass', name: 'Fawnlet' }, Bee: { type: 'Lightning', name: 'Buzzbit', fly: true },
  Demon: { type: 'Fire', name: 'Emberimp' }, Cyclops: { type: 'Fighting', name: 'Oculo' }, Chicken: { type: 'Colorless', name: 'Pecklet' }, Pig: { type: 'Colorless', name: 'Oinkle' },
  Alien: { type: 'Psychic', name: 'Glimm' }, Ghost: { type: 'Psychic', name: 'Boolet' }, Alien_Tall: { type: 'Metal', name: 'Antenno' }, Skull: { type: 'Darkness', name: 'Hollowbit' },
  GreenDemon: { type: 'Darkness', name: 'Grimp' }, Bat: { type: 'Darkness', name: 'Flitter', fly: true }, Cthulhu: { type: 'Psychic', name: 'Tentacube', fly: true }, YellowDragon: { type: 'Dragon', name: 'Drakelet', fly: true },
};
export const petsOfType = t => Object.keys(PETS).filter(k => PETS[k].type === t);
const holoMats = new Map();
function echoMaterial(src, tint) { // unstable Echo shell: model colours + type rim glow + scanline shimmer
  const key = src.uuid + tint; if (holoMats.has(key)) return holoMats.get(key);
  const m = src.clone(); m.transparent = true; m.opacity = .92; m.emissive = new THREE.Color(tint); m.emissiveIntensity = .35;
  m.onBeforeCompile = sh => {
    sh.uniforms.uTime = { value: 0 }; m.userData.sh = sh;
    sh.fragmentShader = 'uniform float uTime;\n' + sh.fragmentShader.replace('#include <dithering_fragment>', `#include <dithering_fragment>
      float scan = .5 + .5 * sin(gl_FragCoord.y * .35 - uTime * 6.);
      vec3 V = normalize(vViewPosition); float rim = pow(1. - abs(dot(normalize(vNormal), V)), 2.2);
      gl_FragColor.rgb += emissive * (rim * 1.6 + scan * .08);
      gl_FragColor.a *= .8 + .2 * scan;`);
  };
  holoMats.set(key, m); return m;
}
export function tickEchoMaterials(t) { holoMats.forEach(m => { if (m.userData.sh) m.userData.sh.uniforms.uTime.value = t; }); }
const litCache = new Map();
function litMaterial(src) { // the monster pack ships unlit materials; relight them so they sit in the scene
  if (litCache.has(src.uuid)) return litCache.get(src.uuid);
  const m = new THREE.MeshStandardMaterial({ map: src.map || null, color: src.color?.clone() || new THREE.Color('#fff'), roughness: .62, metalness: 0, side: src.side });
  litCache.set(src.uuid, m); return m;
}
export function makePet(kind, { size = 1.1, echo = null } = {}) {
  const gltf = ready.get('pets/' + kind); if (!gltf) return null;
  const obj = SkeletonUtils.clone(gltf.scene);
  obj.traverse(o => { if (!o.isMesh) return; o.castShadow = true; const base = litMaterial(o.material); o.material = echo ? echoMaterial(base, echo) : base; });
  let hgt = gltf.userData.h; if (!hgt) { const b = new THREE.Box3().setFromObject(gltf.scene, true); hgt = gltf.userData.h = Math.max(.1, b.max.y - b.min.y); gltf.userData.base = b.min.y; }
  if (!echo) applyComic(obj);
  const g = new THREE.Group(), k = size / hgt; obj.scale.setScalar(k); obj.position.y = -gltf.userData.base * k + (PETS[kind]?.fly ? .9 : 0); g.add(obj);
  const blob = new THREE.Mesh(new THREE.CircleGeometry(.45, 18), new THREE.MeshBasicMaterial({ color: '#000', transparent: true, opacity: .22, depthWrite: false })); blob.rotation.x = -Math.PI / 2; blob.position.y = .03; g.add(blob);
  const R = rigActor(obj, gltf.animations, { height: size });
  const fly = !!PETS[kind]?.fly;
  function locomote(speed) { if (R.busy()) return; if (fly) { R.play('Flying', .3); return; } if (speed < .3) R.play('Idle', .3); else { R.play('Walk', .2); R.current?.setEffectiveTimeScale(THREE.MathUtils.clamp(speed / 2.2, .8, 2.2)); } }
  R.play(fly ? 'Flying' : 'Idle', 0); R.mixer.update(Math.random() * 2);
  return { group: g, kind, obj, fly, mixer: R.mixer, play: R.play, locomote, busy: R.busy, update: dt => R.mixer.update(dt) };
}

/* ---------- small turntable preview (Trainer tab). Renders only while its canvas is in the document. */
export function createPreview(canvas) {
  const r = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true }); r.setPixelRatio(Math.min(devicePixelRatio, 1.5)); r.outputColorSpace = THREE.SRGBColorSpace; r.toneMapping = THREE.ACESFilmicToneMapping; r.toneMappingExposure = 1.05;
  const s = new THREE.Scene(), cam = new THREE.PerspectiveCamera(26, 1, .1, 50); cam.position.set(0, 1.6, 7.2); cam.lookAt(0, 1.15, 0);
  s.add(new THREE.HemisphereLight('#ffffff', '#5a4a70', 2.2)); const d = new THREE.DirectionalLight('#fff4e0', 2.6); d.position.set(2, 4, 3); s.add(d); const rim = new THREE.DirectionalLight('#9f7bff', 2); rim.position.set(-3, 2, -3); s.add(rim);
  const disc = new THREE.Mesh(new THREE.CircleGeometry(1.1, 40), new THREE.MeshBasicMaterial({ color: '#7b5cff', transparent: true, opacity: .25 })); disc.rotation.x = -Math.PI / 2; s.add(disc);
  let ch = null, raf = 0, last = 0, yaw = .5, drag = null, key = '';
  canvas.addEventListener('pointerdown', e => { drag = { x: e.clientX, yaw }; canvas.setPointerCapture(e.pointerId); });
  canvas.addEventListener('pointermove', e => { if (drag) yaw = drag.yaw + (e.clientX - drag.x) * .012; });
  canvas.addEventListener('pointerup', () => { drag = null; });
  function loop(now) {
    if (!canvas.isConnected) { raf = 0; return; } raf = requestAnimationFrame(loop);
    const dt = Math.min(.05, Math.max(0, (now - last) / 1000)); last = now;
    const w = canvas.clientWidth, hh = canvas.clientHeight; if (w && canvas.width !== Math.round(w * r.getPixelRatio())) { r.setSize(w, hh, false); cam.aspect = w / hh; cam.updateProjectionMatrix(); }
    if (!drag) yaw += dt * .35; if (ch) { ch.group.rotation.y = yaw; ch.update(dt); ch.locomote(0); } r.render(s, cam);
  }
  async function set(look, { cheer = false } = {}) {
    await prepare([look]);
    const k = JSON.stringify(look); if (k !== key) { const n = makeRigged(look); if (n) { if (ch) s.remove(ch.group); ch = n; s.add(ch.group); key = k; } }
    if (cheer) ch?.play('Wave', .2, { once: true });
    if (!raf) { last = performance.now(); raf = requestAnimationFrame(loop); }
  }
  return { set, attach(c) { if (c !== canvas) return false; if (!raf) { last = performance.now(); raf = requestAnimationFrame(loop); } return true; } };
}

/* ---------- hand props for working people (rod, hammer, broom, book, watering can, clipboard).
   Built along +Y, then turned so that in the idle pose they point the way a person would hold them. */
const PROP_MAT = {};
const pm = c => PROP_MAT[c] ||= new THREE.MeshStandardMaterial({ color: c, roughness: .8 });
function propMesh(kind) {
  const g = new THREE.Group(), add = (geo, c, y = 0, x = 0, z = 0) => { const m = new THREE.Mesh(geo, pm(c)); m.position.set(x, y, z); m.castShadow = true; g.add(m); return m; };
  if (kind === 'rod') { add(new THREE.CylinderGeometry(.012, .02, 2.4, 6), '#6b4a2a', 1.1); add(new THREE.CylinderGeometry(.035, .035, .08, 8), '#2e3440', .15).rotation.z = Math.PI / 2; }
  else if (kind === 'hammer') { add(new THREE.CylinderGeometry(.025, .03, .55, 6), '#7a5634', .2); add(new THREE.BoxGeometry(.18, .07, .07), '#8a8f99', .48); }
  else if (kind === 'broom') { add(new THREE.CylinderGeometry(.022, .022, 1.5, 6), '#a77a48', -.25); add(new THREE.ConeGeometry(.16, .32, 8), '#d8b45a', -1.1).rotation.x = Math.PI; }
  else if (kind === 'book') { add(new THREE.BoxGeometry(.24, .32, .05), '#3d5fa8', .05); add(new THREE.BoxGeometry(.22, .3, .055), '#f1ecdf', .05, .012); }
  else if (kind === 'can') { add(new THREE.CylinderGeometry(.09, .1, .18, 10), '#57c28f', -.05); add(new THREE.CylinderGeometry(.012, .02, .22, 6), '#57c28f', 0, .12).rotation.z = -1; }
  else if (kind === 'clip') { add(new THREE.BoxGeometry(.22, .3, .02), '#c9a064', .05); add(new THREE.BoxGeometry(.18, .22, .022), '#ffffff', .03); }
  return g;
}
const PROP_DIR = { rod: [0, .75, 1], hammer: [0, .2, 1], broom: [0, -1, .45], book: [0, .4, 1], can: [0, -1, .2], clip: [0, .5, 1] };
export function attachProp(ch, kind) {
  const hand = ch?.parts?.hand; if (!hand) return null;
  const prop = propMesh(kind); ch.group.updateMatrixWorld(true);
  const hq = new THREE.Quaternion(); hand.getWorldQuaternion(hq);
  const gq = new THREE.Quaternion(); ch.group.getWorldQuaternion(gq);
  const d = new THREE.Vector3(...PROP_DIR[kind]).normalize().applyQuaternion(gq);
  const want = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), d);
  prop.quaternion.copy(hq.invert().multiply(want));
  const ws = new THREE.Vector3(); hand.getWorldScale(ws); prop.scale.setScalar(1 / ws.x * (ch.group.scale.x || 1));
  prop.position.set(0, .06 / ws.y, 0); hand.add(prop); return prop;
}

/* ---------- a still portrait of a 3D character (HUD, menus): rendered once per look, cached as a data URL */
let pR = null; const pCache = new Map();
export async function portrait(look, size = 112) {
  const k = JSON.stringify(look) + '|' + size; if (pCache.has(k)) return pCache.get(k);
  const job = (async () => {
    await prepare([look]); const ch = makeRigged(look); if (!ch) return null;
    pR ||= new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
    pR.setPixelRatio(1); pR.setSize(size, size, false); pR.outputColorSpace = THREE.SRGBColorSpace; pR.toneMapping = THREE.ACESFilmicToneMapping; pR.setClearColor(0x000000, 0);
    const s = new THREE.Scene(); s.add(new THREE.HemisphereLight('#ffffff', '#5a4a70', 2.4)); const d = new THREE.DirectionalLight('#fff4e0', 2.8); d.position.set(1.5, 3, 3); s.add(d);
    const rim = new THREE.DirectionalLight('#9f7bff', 1.6); rim.position.set(-2, 2, -2); s.add(rim);
    ch.group.rotation.y = .38; s.add(ch.group); ch.locomote?.(0); ch.update?.(0);
    const bb = new THREE.Box3().setFromObject(ch.group), top = bb.max.y, cam = new THREE.PerspectiveCamera(24, 1, .05, 20);
    cam.position.set(.12, top - .28, 1.75); cam.lookAt(0, top - .36, 0); pR.render(s, cam);
    const url = pR.domElement.toDataURL('image/png'); s.remove(ch.group); return url;
  })().catch(() => null);
  pCache.set(k, job); return job;
}
