// Pokebox — anime characters in the VRM format (VRoid Studio models, MToon toon shading, @pixiv/three-vrm).
// The game's animation library (Quaternius UAL, 84 clips) is retargeted once per model onto the model's RAW bones, so
// every instance is a plain SkeletonUtils clone driven by an AnimationMixer — same API as the old rigged actors.
import * as THREE from 'three';
import * as SkeletonUtils from 'three/addons/utils/SkeletonUtils.js';
import { VRMLoaderPlugin, VRMUtils } from '../vendor/three-vrm/three-vrm.module.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';

const DIR = new URL('../assets/', import.meta.url).href;
const loader = new GLTFLoader(); loader.setMeshoptDecoder(MeshoptDecoder);
const vloader = new GLTFLoader(); vloader.setMeshoptDecoder(MeshoptDecoder); vloader.register(p => new VRMLoaderPlugin(p));

/* UAL bone → VRM humanoid bone */
const MAP = { pelvis: 'hips', spine_01: 'spine', spine_02: 'chest', spine_03: 'upperChest', neck_01: 'neck', Head: 'head',
  clavicle_l: 'leftShoulder', upperarm_l: 'leftUpperArm', lowerarm_l: 'leftLowerArm', hand_l: 'leftHand', clavicle_r: 'rightShoulder', upperarm_r: 'rightUpperArm', lowerarm_r: 'rightLowerArm', hand_r: 'rightHand',
  thigh_l: 'leftUpperLeg', calf_l: 'leftLowerLeg', foot_l: 'leftFoot', ball_l: 'leftToes', thigh_r: 'rightUpperLeg', calf_r: 'rightLowerLeg', foot_r: 'rightFoot', ball_r: 'rightToes' };
for (const s of ['l', 'r']) { const S = s === 'l' ? 'left' : 'right';
  Object.assign(MAP, { [`thumb_01_${s}`]: S + 'ThumbMetacarpal', [`thumb_02_${s}`]: S + 'ThumbProximal', [`thumb_03_${s}`]: S + 'ThumbDistal' });
  for (const [f, F] of [['index', 'Index'], ['middle', 'Middle'], ['ring', 'Ring'], ['pinky', 'Little']]) Object.assign(MAP, { [`${f}_01_${s}`]: S + F + 'Proximal', [`${f}_02_${s}`]: S + F + 'Intermediate', [`${f}_03_${s}`]: S + F + 'Distal' }); }

let ualP = null;
const loadUAL = () => ualP ||= Promise.all(['chars/anime/ual1.glb', 'chars/anime/ual2.glb'].map(f => loader.loadAsync(DIR + f).catch(() => null)))
  .then(gs => gs.filter(Boolean).map(g => { g.scene.updateMatrixWorld(true); return g; }));

export let HIPS_K = 0; export const setHipsK = k => { HIPS_K = k; };
const models = new Map(); // name -> Promise<{ vrm, scene, clips, h, v0 }>
export const vrmReady = new Map();

/** load + prepare one VRM model (assets/chars/vrm/<name>.vrm) */
export function loadVRM(name) {
  if (models.has(name)) return models.get(name);
  const p = Promise.all([vloader.loadAsync(DIR + 'chars/vrm/' + name + '.vrm'), loadUAL()]).then(([g, uals]) => {
    const vrm = g.userData.vrm; VRMUtils.removeUnnecessaryVertices?.(g.scene);
    const v0 = vrm.meta?.metaVersion === '0';
    vrm.scene.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; o.frustumCulled = false; } });
    vrm.scene.updateMatrixWorld(true);
    // rest data of the raw rig (model space: VRM0 models face -Z, VRM1 +Z)
    const rest = {}; const q = new THREE.Quaternion();
    for (const vb of new Set(Object.values(MAP))) { const raw = vrm.humanoid.getRawBoneNode(vb); if (!raw) continue;
      const P = raw.parent ? raw.parent.getWorldQuaternion(new THREE.Quaternion()) : new THREE.Quaternion(); rest[vb] = { raw, P, Pi: P.clone().invert(), B: raw.quaternion.clone(), pos: raw.position.clone() }; }
    const hipsRaw = vrm.humanoid.getRawBoneNode('hips'), hipsY = hipsRaw.getWorldPosition(new THREE.Vector3()).y;
    const clips = [];
    for (const u of uals) {
      const src = u.scene, pel = src.getObjectByName('pelvis'), hs = pel ? hipsY / Math.max(1e-3, pel.position.y) : 1;
      for (const clip of u.animations) {
        const tracks = [];
        for (const tr of clip.tracks) {
          const [bn, prop] = tr.name.split('.'), vb = MAP[bn], R = vb && rest[vb], sb = vb && src.getObjectByName(bn); if (!R || !sb) continue;
          if (prop === 'quaternion') {
            const qr = sb.getWorldQuaternion(new THREE.Quaternion()).invert(), qp = sb.parent.getWorldQuaternion(new THREE.Quaternion()), v = new Float32Array(tr.values.length);
            for (let i = 0; i < v.length; i += 4) { q.fromArray(tr.values, i).premultiply(qp).multiply(qr); /* normalised (world-aligned) rotation, character facing +Z */
              if (v0) { q.x = -q.x; q.z = -q.z; } /* into the model's own frame */
              q.multiply(R.P).premultiply(R.Pi).multiply(R.B); /* normalised → raw (what three-vrm's humanoid rig does each frame) */
              q.toArray(v, i); }
            tracks.push(new THREE.QuaternionKeyframeTrack(R.raw.name + '.quaternion', tr.times, v));
          } else if (prop === 'position' && vb === 'hips') {
            const v = new Float32Array(tr.values.length), p0 = pel.position;
            for (let i = 0; i < v.length; i += 3) { const dx = (tr.values[i] - p0.x) * hs, dy = (tr.values[i + 1] - p0.y) * hs, dz = (tr.values[i + 2] - p0.z) * hs;
              v[i] = R.pos.x + (v0 ? -dx : dx) * .0; v[i + 1] = R.pos.y + dy * HIPS_K; v[i + 2] = R.pos.z + (v0 ? -dz : dz) * .0; } /* vertical bob only: no root drift */
            tracks.push(new THREE.VectorKeyframeTrack(R.raw.name + '.position', tr.times, v));
          }
        }
        clips.push(new THREE.AnimationClip(clip.name, clip.duration, tracks));
      }
    }
    const b = new THREE.Box3().setFromObject(vrm.scene, true), h = Math.max(.1, b.max.y - b.min.y);
    const M = { vrm, scene: vrm.scene, clips, h, v0 }; vrmReady.set(name, M); return M;
  }).catch(e => { console.warn('[vrm] failed', name, e); models.delete(name); return null; });
  models.set(name, p); return p;
}

const ALIAS = { Cheer: 'Yes', PickUp: 'Interact', Spellcast_Shoot: 'Interact', Walking_A: 'Walk_Loop', Running_A: 'Jog_Fwd_Loop', Unarmed_Idle: 'Idle_Loop', Hit_A: 'Hit_Chest',
  Idle: 'Idle_Loop', Walk: 'Walk_Loop', Run: 'Jog_Fwd_Loop', Sprint: 'Sprint_Loop', Wave: 'Yes', Idle_Neutral: 'Idle_Loop', HitRecieve: 'Hit_Chest', Death: 'Death01', Punch_Right: 'Punch_Cross' };

/** a VRM actor with the same API as chars.makeRigged(): { group, play, locomote, busy, update, parts } */
export function makeVRMActor(name, { height = 2.0, scale = 1, aliases = {} } = {}) {
  const M = vrmReady.get(name); if (!M) return null;
  const obj = SkeletonUtils.clone(M.scene); obj.traverse(o => { if (o.isMesh) { o.frustumCulled = false; o.material.userData = { ...(o.material.userData || {}), actor: true }; } });
  const g = new THREE.Group(), k = height / M.h * scale * .9; obj.scale.setScalar(k); if (M.v0) obj.rotation.y = Math.PI; g.add(obj);
  const mixer = new THREE.AnimationMixer(obj), byName = Object.fromEntries(M.clips.map(c => [c.name, c])), acts = {}, AL = { ...ALIAS, ...aliases };
  const act = n => { n = byName[n] ? n : AL[n] || n; return acts[n] ||= byName[n] ? mixer.clipAction(byName[n]) : null; };
  let cur = null, oneShot = false;
  function play(n, fade = .25, { once = false, speed = 1 } = {}) { const a = act(n); if (!a || (a === cur && !once)) return false;
    a.reset(); a.setEffectiveTimeScale(speed); a.setEffectiveWeight(1); a.clampWhenFinished = once; a.setLoop(once ? THREE.LoopOnce : THREE.LoopRepeat, Infinity); a.play();
    if (cur && cur !== a) cur.crossFadeTo(a, fade, false); cur = a; oneShot = once; return true; }
  mixer.addEventListener('finished', () => { oneShot = false; });
  const R = { play, busy: () => oneShot, has: n => !!act(n), get current() { return cur; } };
  function locomote(speed, state) {
    if (R.busy()) return;
    if (state === 'air' && R.has('Jump_Loop')) { play('Jump_Loop', .18); return; }
    if (state === 'swim' && R.has('Swim_Fwd_Loop')) { play(speed > .35 ? 'Swim_Fwd_Loop' : 'Swim_Idle_Loop', .3); return; }
    if (speed < .35) play('Idle', .3);
    else if (speed < 6.4) { play('Walk', .22); cur?.setEffectiveTimeScale(THREE.MathUtils.clamp(speed / 3.4, .7, 1.6)); }
    else if (speed > 9.5 && R.has('Sprint')) { play('Sprint', .25); cur?.setEffectiveTimeScale(THREE.MathUtils.clamp(speed / 10, .85, 1.3)); }
    else { play('Run', .2); cur?.setEffectiveTimeScale(THREE.MathUtils.clamp(speed / 7.8, .85, 1.35)); }
  }
  play('Idle', 0); mixer.update(Math.random() * 2);
  const blob = new THREE.Mesh(new THREE.CircleGeometry(.5, 20), new THREE.MeshBasicMaterial({ color: '#000', transparent: true, opacity: .18, depthWrite: false })); blob.rotation.x = -Math.PI / 2; blob.position.y = .03; g.add(blob);
  let head = null, hand = null; const hn = M.vrm.humanoid.getRawBoneNode('head')?.name, hdn = M.vrm.humanoid.getRawBoneNode('rightHand')?.name;
  obj.traverse(o => { if (o.name === hn) head = o; if (o.name === hdn) hand = o; });
  return { group: g, model: 'vrm:' + name, mixer, play, locomote, busy: R.busy, update: dt => mixer.update(dt), parts: { head: head || g, hand }, rigged: true, vrm: true };
}
