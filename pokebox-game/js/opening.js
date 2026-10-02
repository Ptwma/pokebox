// Pokebox — pack opening scene (step 1)
// Timeline recreated frame-by-frame from the reference GIF (141 frames @ 25fps = 5.64s).
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

/* ---------------------------------------------------------------- config */
const Q = new URLSearchParams(location.search);
const THEME = Q.get('theme') === 'dark' ? 'dark' : 'studio';
const FREEZE = Q.has('t') ? parseFloat(Q.get('t')) : null;   // ?t=3.5 freezes the timeline (debug)
const CFG = {
  pack: { art: 'assets/packs/pfl-charizard-x.png', set: 'Phantasmal Flames', code: 'PFL', data: 'data/pfl.json' },
  cardDir: '../pokemon-card-scraper/pokemon_cards/images/',
  mystery: Q.get('mystery') !== '0',
};

// Timeline (seconds) — mapped from GIF frame numbers (frame / 25)
const T = {
  spin0: 0.20, spin1: 1.36,     // f5–f34   full 360° turn, white pack → design
  tilt1: 1.76,                  // f34–f44  settle into 3/4 hover
  zoom1: 2.24,                  // f44–f56  fast push-in to the crimp
  tear: 3.20,                   // f80      spark runs along the tear line
  strip: 3.42,                  // f85      top strip flies off, light burst
  card0: 3.84,                  // f96      card starts to rise out of the pack
  rise0: 4.04, rise1: 4.46,     // f101–f112 camera follows card up, pack drops away
  end: 5.64,
};

// Pack dimensions in world units (1 unit = 1000 texture px of the 780×1426 wrap)
const PW = 0.78, PH = 1.426, BULGE = 0.07;
const CRIMP = 0.042;                       // crimp height as fraction of pack height
const TEAR_V = 1 - 0.056;                  // tear just below the top crimp
const TEAR_Y = (TEAR_V - 0.5) * PH;
// Card case (mauve frame + white rim like the GIF)
const CARD_W = 0.46, CARD_H = CARD_W / 0.716, BORDER = 0.034;
const CASE_W = CARD_W + BORDER * 2, CASE_H = CARD_H + BORDER * 2;

const COL = THEME === 'studio'
  ? { bgC: '#f7e6ef', bgM: '#e1ccd6', bgE: '#bfb1b6', flat: '#bdadb5', flatLow: '#cdc5c6', frame: '#634a63', rim: '#f6eff3', ray: [1.9, 1.75, 1.85], spark: [2.2, 2.1, 2.2] }
  : { bgC: '#2a241d', bgM: '#15120f', bgE: '#050505', flat: '#0d0c0b', flatLow: '#1a1714', frame: '#2a2722', rim: '#f7ebc3', ray: [2.0, 1.8, 1.3], spark: [2.3, 2.1, 1.6] };

/* ---------------------------------------------------------------- helpers */
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const lerp = (a, b, k) => a + (b - a) * k;
const seg = (t, a, b) => clamp((t - a) / (b - a));
const ease = {
  io3: k => k < .5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2,
  io2: k => k < .5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2,
  o3: k => 1 - Math.pow(1 - k, 3),
  i2: k => k * k,
  oBack: (k, s = 1.4) => 1 + (s + 1) * Math.pow(k - 1, 3) + s * Math.pow(k - 1, 2),
};
const smooth = (a, b, x) => { const k = clamp((x - a) / (b - a)); return k * k * (3 - 2 * k); };
const env = (t, a, b, c, d) => smooth(a, b, t) * (1 - smooth(c, d, t)); // rise a→b, fall c→d
function rng(seed) { let s = seed >>> 0; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }

function canvasTex(w, h, draw, srgb = true) {
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  draw(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c);
  if (srgb) t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8;
  return t;
}
const loadImg = src => new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = () => rej(new Error('Missing image: ' + src)); i.src = src; });

/* ---------------------------------------------------------------- renderer */
const canvas = document.getElementById('scene');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: FREEZE !== null });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.NeutralToneMapping;
renderer.toneMappingExposure = 1.0;

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(30, 1, 0.01, 100);
scene.add(camera);
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
scene.environmentIntensity = 0.55;

const key = new THREE.DirectionalLight(0xffffff, 0.9); key.position.set(-2, 3, 4); scene.add(key);
const rim = new THREE.DirectionalLight(THEME === 'studio' ? 0xffd9e8 : 0xffe3b0, 1.1); rim.position.set(3, 1.5, -2); scene.add(rim);
scene.add(new THREE.AmbientLight(0xffffff, 0.15));

/* ---------------------------------------------------------------- background (camera-locked) */
const TANH = Math.tan(THREE.MathUtils.degToRad(15));
const bgWide = canvasTex(1024, 576, (g, w, h) => {
  const r = g.createRadialGradient(w / 2, h * .48, 0, w / 2, h * .5, w * .62);
  r.addColorStop(0, COL.bgC); r.addColorStop(.45, COL.bgM); r.addColorStop(1, COL.bgE);
  g.fillStyle = r; g.fillRect(0, 0, w, h);
});
const bgFlat = canvasTex(512, 512, (g, w, h) => {
  const l = g.createLinearGradient(0, 0, 0, h); l.addColorStop(0, COL.flat); l.addColorStop(.7, COL.flat); l.addColorStop(1, COL.flatLow);
  g.fillStyle = l; g.fillRect(0, 0, w, h);
});
function bgPlane(tex, z) {
  const m = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ map: tex, depthWrite: false, transparent: true, toneMapped: false }));
  m.position.z = -z; m.renderOrder = -10; camera.add(m); return m;
}
const bgA = bgPlane(bgWide, 30), bgB = bgPlane(bgFlat, 29.9);

/* ---------------------------------------------------------------- textures */
function crinkleNormal(size = 512, seed = 7) {
  const R = rng(seed), H = new Float32Array(size * size);
  // periodic value noise, a few octaves
  const oct = [[8, 1], [16, .5], [32, .25], [64, .12]];
  for (const [n, amp] of oct) {
    const g = Array.from({ length: n * n }, R);
    for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
      const fx = x / size * n, fy = y / size * n, x0 = Math.floor(fx), y0 = Math.floor(fy);
      const sx = fx - x0, sy = fy - y0, ux = sx * sx * (3 - 2 * sx), uy = sy * sy * (3 - 2 * sy);
      const a = g[(y0 % n) * n + x0 % n], b = g[(y0 % n) * n + (x0 + 1) % n], c = g[((y0 + 1) % n) * n + x0 % n], d = g[((y0 + 1) % n) * n + (x0 + 1) % n];
      H[y * size + x] += amp * lerp(lerp(a, b, ux), lerp(c, d, ux), uy);
    }
  }
  // sharp foil creases
  for (let i = 0; i < 70; i++) {
    const x0 = R() * size, y0 = R() * size, ang = R() * Math.PI, len = 20 + R() * 140, w = 1 + R() * 2.5, dep = (R() - .5) * .9;
    const dx = Math.cos(ang), dy = Math.sin(ang);
    for (let s = -len; s < len; s++) for (let o = -w * 3; o <= w * 3; o++) {
      const px = Math.round(x0 + dx * s - dy * o), py = Math.round(y0 + dy * s + dx * o);
      const X = ((px % size) + size) % size, Y = ((py % size) + size) % size;
      H[Y * size + X] += dep * Math.exp(-(o * o) / (w * w)) * (1 - Math.abs(s) / len);
    }
  }
  const data = new Uint8Array(size * size * 4), k = 2.2;
  for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
    const h = (X, Y) => H[(((Y % size) + size) % size) * size + ((X % size) + size) % size];
    let nx = (h(x - 1, y) - h(x + 1, y)) * k, ny = (h(x, y - 1) - h(x, y + 1)) * k, nz = 1;
    const l = Math.hypot(nx, ny, nz); nx /= l; ny /= l; nz /= l;
    const i = (y * size + x) * 4; data[i] = (nx * .5 + .5) * 255; data[i + 1] = (ny * .5 + .5) * 255; data[i + 2] = (nz * .5 + .5) * 255; data[i + 3] = 255;
  }
  const t = new THREE.DataTexture(data, size, size); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(1.3, 2.4); t.needsUpdate = true;
  return t;
}
const crinkle = crinkleNormal();

function mysteryTex() {
  return canvasTex(780, 1426, (g, w, h) => {
    const l = g.createLinearGradient(0, 0, w, h); l.addColorStop(0, '#e9e9ea'); l.addColorStop(.5, '#d6d6d8'); l.addColorStop(1, '#e4e4e6');
    g.fillStyle = l; g.fillRect(0, 0, w, h);
    for (const top of [true, false]) for (let i = 0; i < 9; i++) {
      const y = top ? i * 6.6 : h - 60 + i * 6.6;
      g.fillStyle = i % 2 ? '#d8d8d8' : '#fdfdfd'; g.fillRect(0, y, w, 3.3);
    }
    const tg = g.createLinearGradient(0, h * .36, 0, h * .64);
    tg.addColorStop(0, '#1d1d1f'); tg.addColorStop(.45, '#8d8d92'); tg.addColorStop(.55, '#2a2a2d'); tg.addColorStop(1, '#5a5a5e');
    g.fillStyle = tg; g.textAlign = 'center'; g.textBaseline = 'middle';
    g.font = '900 150px "Arial Black", Impact, sans-serif';
    ['RIP', 'THE', 'PACK'].forEach((s, i) => g.fillText(s, w / 2, h * .41 + i * 150));
    g.font = '700 26px Arial, sans-serif'; g.fillStyle = '#9a9aa0'; g.fillText('P O K E B O X', w / 2, h * .87);
  });
}
function backTex(img) {
  return canvasTex(780, 1426, (g, w, h) => {
    g.save(); g.translate(w, 0); g.scale(-1, 1); g.filter = 'blur(10px) saturate(1.2)'; g.drawImage(img, -20, -20, w + 40, h + 40); g.restore();
    g.filter = 'none';
    g.fillStyle = 'rgba(12,10,18,.62)'; g.fillRect(0, 0, w, h);
    g.save(); g.globalAlpha = .9; g.drawImage(img, 0, 0, w, 64, 0, 0, w, 64); g.drawImage(img, 0, h - 64, w, 64, 0, h - 64, w, 64); g.restore();
    g.fillStyle = '#f2f2f2'; g.textAlign = 'center'; g.font = '900 44px "Arial Black", Impact, sans-serif';
    g.fillText('POKÉMON', w / 2, h * .2); g.font = '700 24px Arial'; g.fillText('TRADING CARD GAME', w / 2, h * .2 + 40);
    g.font = '600 22px Arial'; g.fillStyle = '#cfcfd6';
    ['10 ADDITIONAL GAME CARDS', 'PHANTASMAL FLAMES', 'OPENED AT POKEBOX'].forEach((s, i) => g.fillText(s, w / 2, h * .74 + i * 34));
    g.fillStyle = '#fff'; g.fillRect(w - 250, h - 190, 180, 90);
    for (let x = 0; x < 160; x += 4) { g.fillStyle = '#111'; g.fillRect(w - 240 + x, h - 180, (x * 7 % 3) + 1, 60); }
  });
}
function starTex() {
  return canvasTex(256, 256, (g, w, h) => {
    const c = w / 2;
    const r = g.createRadialGradient(c, c, 0, c, c, c * .45); r.addColorStop(0, 'rgba(255,255,255,1)'); r.addColorStop(.25, 'rgba(255,255,255,.85)'); r.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = r; g.fillRect(0, 0, w, h);
    g.fillStyle = '#fff'; g.shadowColor = '#fff'; g.shadowBlur = 6;
    const ray = (rot, len, th) => { g.save(); g.translate(c, c); g.rotate(rot); g.beginPath(); g.moveTo(0, -len); g.lineTo(th, 0); g.lineTo(0, len); g.lineTo(-th, 0); g.closePath(); g.fill(); g.restore(); };
    ray(0, c * .98, 5); ray(Math.PI / 2, c * .98, 5);
  }, false);
}
function glowTex() {
  return canvasTex(128, 128, (g, w, h) => {
    const r = g.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, w / 2); r.addColorStop(0, 'rgba(255,255,255,1)'); r.addColorStop(.35, 'rgba(255,255,255,.6)'); r.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = r; g.fillRect(0, 0, w, h);
  }, false);
}
function beamTex() {
  return canvasTex(64, 512, (g, w, h) => {
    for (let x = 0; x < w; x++) {
      const k = Math.exp(-Math.pow((x - w / 2) / (w * .18), 2));
      const l = g.createLinearGradient(0, h, 0, 0);
      l.addColorStop(0, `rgba(255,255,255,${k})`); l.addColorStop(.35, `rgba(255,255,255,${k * .55})`); l.addColorStop(1, 'rgba(255,255,255,0)');
      g.fillStyle = l; g.fillRect(x, 0, 1, h);
    }
  }, false);
}
function barTex() {
  return canvasTex(16, 256, (g, w, h) => {
    const l = g.createLinearGradient(0, 0, 0, h); l.addColorStop(0, 'rgba(255,255,255,0)'); l.addColorStop(.5, 'rgba(255,255,255,1)'); l.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = l; g.fillRect(0, 0, w, h);
  }, false);
}
const STAR = starTex(), GLOW = glowTex(), BEAM = beamTex(), BAR = barTex();

/* ---------------------------------------------------------------- pack geometry */
function packZ(u, v) {
  if (v < CRIMP || v > 1 - CRIMP) return 0.0016 * (Math.sin(v * PH * 840) * .5 + .5);   // crimp ridges
  const e = smooth(CRIMP, CRIMP + .1, v) * (1 - smooth(1 - CRIMP - .1, 1 - CRIMP, v));
  let z = BULGE * Math.pow(Math.sin(Math.PI * u), .55) * Math.pow(e, .8);
  const wz = Math.exp(-Math.pow((v - (1 - CRIMP - .045)) / .028, 2)) + Math.exp(-Math.pow((v - (CRIMP + .045)) / .028, 2));
  z += 0.0038 * Math.sin(v * PH * 150 + u * 7) * wz * Math.sin(Math.PI * u);           // pull wrinkles under the crimps
  return z;
}
function packE(v) { return smooth(CRIMP, CRIMP + .1, v) * (1 - smooth(1 - CRIMP - .1, 1 - CRIMP, v)); }
const jag = u => (0.0045 * Math.sin(u * 97) + 0.003 * Math.sin(u * 231 + 1.3) + 0.002 * Math.sin(u * 511)) / PH;

function faceGeo(v0, v1, jagEdge) {
  const sx = 70, sy = Math.max(4, Math.round(140 * (v1 - v0)));
  const pos = [], uv = [], idx = [];
  for (let j = 0; j <= sy; j++) for (let i = 0; i <= sx; i++) {
    const u = i / sx; let v = v0 + (v1 - v0) * j / sy;
    if (jagEdge === 'top' && j === sy) v += jag(u);
    if (jagEdge === 'bottom' && j === 0) v += jag(u);
    const x = (u - .5) * PW * (1 - .03 * packE(v) * Math.sin(Math.PI * v));
    pos.push(x, (v - .5) * PH, packZ(u, v)); uv.push(u, v);
  }
  for (let j = 0; j < sy; j++) for (let i = 0; i < sx; i++) {
    const a = j * (sx + 1) + i, b = a + 1, c = a + sx + 1, d = c + 1;
    idx.push(a, b, d, a, d, c);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  g.setIndex(idx); g.computeVertexNormals();
  return g;
}
function foilMat(map) {
  return new THREE.MeshPhysicalMaterial({
    map, normalMap: crinkle, normalScale: new THREE.Vector2(.22, .22),
    roughness: .3, metalness: .3, clearcoat: 1, clearcoatRoughness: .16,
    iridescence: .18, iridescenceIOR: 1.3, envMapIntensity: 1.05,
  });
}

/* ---------------------------------------------------------------- card */
function roundedShape(w, h, r) {
  const s = new THREE.Shape(), x = -w / 2, y = -h / 2;
  s.moveTo(x + r, y); s.lineTo(x + w - r, y); s.quadraticCurveTo(x + w, y, x + w, y + r); s.lineTo(x + w, y + h - r);
  s.quadraticCurveTo(x + w, y + h, x + w - r, y + h); s.lineTo(x + r, y + h); s.quadraticCurveTo(x, y + h, x, y + h - r);
  s.lineTo(x, y + r); s.quadraticCurveTo(x, y, x + r, y); return s;
}
const cardMask = canvasTex(256, 358, (g, w, h) => { g.fillStyle = '#000'; g.fillRect(0, 0, w, h); g.fillStyle = '#fff'; g.beginPath(); g.roundRect(0, 0, w, h, 12); g.fill(); }, false);

/* ---------------------------------------------------------------- particles */
const partMat = new THREE.ShaderMaterial({
  uniforms: { uTime: { value: 0 }, uTex: { value: STAR }, uPR: { value: renderer.getPixelRatio() }, uCol: { value: new THREE.Color(...COL.spark) } },
  vertexShader: `
    attribute vec3 vel; attribute float t0; attribute float life; attribute float sz; attribute float seed;
    uniform float uTime; uniform float uPR; varying float vA; varying float vRot;
    void main(){
      float age = uTime - t0; float k = age / life;
      float alive = step(0.0, age) * step(age, life);
      vec3 p = position + vel * age + vec3(0.0, -0.35, 0.0) * age * age * 0.5;
      vec4 mv = modelViewMatrix * vec4(p, 1.0); gl_Position = projectionMatrix * mv;
      float tw = 0.55 + 0.45 * sin(age * 28.0 + seed * 40.0);
      vA = alive * (1.0 - k) * tw * smoothstep(0.0, 0.06, k);
      gl_PointSize = alive * sz * uPR * 320.0 * (1.0 - 0.4 * k) / -mv.z; vRot = seed * 6.2831;
    }`,
  fragmentShader: `
    uniform sampler2D uTex; uniform vec3 uCol; varying float vA; varying float vRot;
    void main(){
      vec2 p = gl_PointCoord - 0.5; float c = cos(vRot), s = sin(vRot);
      p = mat2(c, -s, s, c) * p + 0.5;
      vec4 t = texture2D(uTex, p); gl_FragColor = vec4(uCol * t.rgb, t.a * vA);
    }`,
  transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
});
function particles(list) {
  const g = new THREE.BufferGeometry(), n = list.length;
  const f = k => new Float32Array(n * k);
  const P = f(3), V = f(3), T0 = f(1), L = f(1), S = f(1), SE = f(1);
  list.forEach((p, i) => { P.set(p.p, i * 3); V.set(p.v, i * 3); T0[i] = p.t0; L[i] = p.life; S[i] = p.sz; SE[i] = p.seed; });
  g.setAttribute('position', new THREE.BufferAttribute(P, 3)); g.setAttribute('vel', new THREE.BufferAttribute(V, 3));
  g.setAttribute('t0', new THREE.BufferAttribute(T0, 1)); g.setAttribute('life', new THREE.BufferAttribute(L, 1));
  g.setAttribute('sz', new THREE.BufferAttribute(S, 1)); g.setAttribute('seed', new THREE.BufferAttribute(SE, 1));
  const pts = new THREE.Points(g, partMat); pts.frustumCulled = false; return pts;
}

/* ---------------------------------------------------------------- post */
const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
const blurPass = new ShaderPass({
  uniforms: { tDiffuse: { value: null }, uStrength: { value: 0 }, uDir: { value: new THREE.Vector2(0, 1) }, uRadial: { value: 0 } },
  vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`,
  fragmentShader: `
    uniform sampler2D tDiffuse; uniform float uStrength; uniform vec2 uDir; uniform float uRadial; varying vec2 vUv;
    void main(){
      if (uStrength < 0.0005) { gl_FragColor = texture2D(tDiffuse, vUv); return; }
      vec2 d = mix(uDir, (vUv - vec2(0.5, 0.45)) * 2.0, uRadial) * uStrength;
      vec4 acc = vec4(0.0);
      for (int i = 0; i < 24; i++) { float t = float(i) / 23.0 - 0.5; acc += texture2D(tDiffuse, vUv + d * t); }
      gl_FragColor = acc / 24.0;
    }`,
});
composer.addPass(blurPass);
const bloom = new UnrealBloomPass(new THREE.Vector2(1, 1), 0.38, 0.35, 1.05);
composer.addPass(bloom);
composer.addPass(new OutputPass());

/* ---------------------------------------------------------------- scene build */
let S = null;           // current opening's objects
let startTime = 0;
let view = { dWide: 3.6, dClose: 1.55, yClose: .67 };

function fit() {
  const w = innerWidth, h = innerHeight, a = w / h;
  renderer.setSize(w, h); composer.setSize(w, h); bloom.resolution.set(w, h);
  camera.aspect = a; camera.updateProjectionMatrix();
  const dH = (x, frac) => (x / frac) / 2 / TANH, dW = (x, frac) => (x / frac) / 2 / (TANH * a);
  view.dWide = Math.max(dH(PH, .73), dW(PW, .62));
  view.dClose = Math.max(dH(CASE_H, .86), dW(CASE_W, .82));
  view.yClose = PH / 2 - .05 * 2 * view.dClose * TANH;
  for (const [m, d] of [[bgA, 30], [bgB, 29.9]]) { const hh = 2 * d * TANH * 1.3; m.scale.set(hh * a, hh, 1); }
}
addEventListener('resize', fit);

async function build(card) {
  if (S) { scene.remove(S.root); S.dispose(); }
  const R = rng(card.seed);
  const root = new THREE.Group(); scene.add(root);
  const dispose = [];

  // pack
  const art = S?.artTex || await new THREE.TextureLoader().loadAsync(CFG.pack.art);
  art.colorSpace = THREE.SRGBColorSpace; art.anisotropy = 8;
  const artImg = art.image;
  const back = S?.backArt || backTex(artImg);
  const white = S?.white || mysteryTex();
  const matF = foilMat(CFG.mystery ? white : art), matB = foilMat(CFG.mystery ? white : back);
  const pack = new THREE.Group(); root.add(pack);
  const bodyF = new THREE.Mesh(faceGeo(0, TEAR_V, 'top'), matF);
  const bodyB = new THREE.Mesh(faceGeo(0, TEAR_V, 'top'), matB); bodyB.rotation.y = Math.PI;
  const strip = new THREE.Group(); const sy = (TEAR_V + 1) / 2 * PH - PH / 2; strip.position.y = sy;
  const stripF = new THREE.Mesh(faceGeo(TEAR_V, 1, 'bottom'), matF); stripF.position.y = -sy;
  const stripB = new THREE.Mesh(faceGeo(TEAR_V, 1, 'bottom'), matB); stripB.position.y = -sy; stripB.rotation.y = Math.PI;
  strip.add(stripF, stripB); pack.add(bodyF, bodyB, strip);
  // back-face uv mirror so the back art reads correctly
  for (const m of [bodyB, stripB]) { const uv = m.geometry.attributes.uv; for (let i = 0; i < uv.count; i++) uv.setX(i, 1 - uv.getX(i)); }

  // card
  const cardGroup = new THREE.Group(); root.add(cardGroup);
  const cardTex = await new THREE.TextureLoader().loadAsync(CFG.cardDir + card.f);
  cardTex.colorSpace = THREE.SRGBColorSpace; cardTex.anisotropy = 8; dispose.push(cardTex);
  const ex = { depth: .012, bevelEnabled: true, bevelThickness: .003, bevelSize: .003, bevelSegments: 3, curveSegments: 10 };
  const caseM = new THREE.Mesh(new THREE.ExtrudeGeometry(roundedShape(CASE_W, CASE_H, .02), ex),
    new THREE.MeshPhysicalMaterial({ color: COL.frame, roughness: .42, clearcoat: .7, clearcoatRoughness: .25 }));
  caseM.position.z = -.012;
  const rimM = new THREE.Mesh(new THREE.ExtrudeGeometry(roundedShape(CASE_W + .014, CASE_H + .014, .026), { ...ex, depth: .006 }),
    new THREE.MeshStandardMaterial({ color: COL.rim, roughness: .5, emissive: COL.rim, emissiveIntensity: .35 }));
  rimM.position.z = -.016;
  const face = new THREE.Mesh(new THREE.PlaneGeometry(CARD_W, CARD_H),
    new THREE.MeshBasicMaterial({ map: cardTex, alphaMap: cardMask, transparent: true, toneMapped: false }));
  face.position.z = .0035;
  const glowM = new THREE.Mesh(new THREE.PlaneGeometry(CASE_W * 1.02, CASE_H * 1.02),
    new THREE.MeshBasicMaterial({ color: new THREE.Color(2.2, 2.1, 2.15), transparent: true, opacity: 1, blending: THREE.AdditiveBlending, depthWrite: false }));
  glowM.position.z = .006;
  const halo = new THREE.Sprite(new THREE.SpriteMaterial({ map: GLOW, color: new THREE.Color(1.6, 1.5, 1.55), blending: THREE.AdditiveBlending, depthWrite: false, transparent: true }));
  halo.scale.set(CASE_W * 2.4, CASE_H * 1.8, 1); halo.position.z = -.05;
  cardGroup.add(halo, rimM, caseM, face, glowM);

  // opening glow + rays (light burst)
  const burst = new THREE.Group(); burst.position.set(0, TEAR_Y, 0); root.add(burst);
  const lip = new THREE.Sprite(new THREE.SpriteMaterial({ map: GLOW, color: new THREE.Color(2.4, 2.3, 2.35), blending: THREE.AdditiveBlending, depthWrite: false, transparent: true }));
  lip.scale.set(PW * 1.2, .1, 1); lip.position.z = .02; burst.add(lip);
  const rays = [];
  for (let i = 0; i < 32; i++) {
    const len = 1.1 + R() * 1.9, w = .006 + R() * .026;
    const geo = new THREE.PlaneGeometry(w, len); geo.translate(0, len / 2, 0);
    const m = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ map: BEAM, color: new THREE.Color(...COL.ray), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, opacity: 0 }));
    const a = (R() - .5) * 2; m.rotation.z = -Math.sign(a) * Math.pow(Math.abs(a), .8) * 1.3;
    m.position.set((R() - .5) * PW * .75, 0, -.03 - R() * .02);
    m.userData = { seed: R() * 10, base: .22 + R() * .5 }; burst.add(m); rays.push(m);
  }
  // vertical light bars left behind when the card shoots up (f104–f110)
  const bars = [];
  for (let i = 0; i < 46; i++) {
    const h = .04 + Math.pow(R(), 2) * .36, w = .003 + R() * .01;
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ map: BAR, color: new THREE.Color(2, 1.95, 2), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, opacity: 0 }));
    m.position.set((R() - .5) * 1.2, TEAR_Y + .05 + R() * .3, .04); m.userData = { d: R() * .12, seed: R() * 10 };
    root.add(m); bars.push(m);
  }

  // particles
  const L = [];
  for (let i = 0; i < 170; i++) {           // spark racing along the tear line (f80–f84)
    const s = i / 170;
    L.push({ p: [-PW / 2 + s * PW, TEAR_Y + (R() - .5) * .012, .05], v: [(R() - .3) * .5, R() * .45 + .05, R() * .25], t0: T.tear + s * (T.strip - T.tear) + R() * .03, life: .2 + R() * .35, sz: .012 + R() * .04, seed: R() });
  }
  for (let i = 0; i < 420; i++) {           // burst of glitter from the opening
    const a = (R() - .5) * 2.4, sp = .35 + R() * 1.4, big = R() < .06;
    L.push({ p: [(R() - .5) * PW * .8, TEAR_Y, (R() - .5) * .06], v: [Math.sin(a) * sp, Math.cos(a) * sp, R() * .3], t0: T.strip - .02 + Math.pow(R(), 2) * .75, life: .5 + R() * 1.0, sz: big ? .12 + R() * .08 : .018 + R() * .06, seed: R() });
  }
  for (let i = 0; i < 90; i++) {            // glitter trailing the rising card
    L.push({ p: [(R() - .5) * CASE_W * 1.2, TEAR_Y + R() * .2, .05], v: [(R() - .5) * .2, .6 + R() * 1.2, .05], t0: T.card0 + R() * .5, life: .4 + R() * .6, sz: .01 + R() * .035, seed: R() });
  }
  const parts = particles(L); root.add(parts);
  // bright flare riding the head of the tear (f80–f85)
  const flare = new THREE.Sprite(new THREE.SpriteMaterial({ map: STAR, color: new THREE.Color(2.6, 2.5, 2.6), blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, opacity: 0 }));
  root.add(flare);

  // end twinkles (f112 → end, then loop)
  const tw = [[-.13, .2, .9], [.36, -.02, 1.25], [-.3, 0, .35], [.21, -.24, .8], [-.15, -.27, .55], [.33, .3, .7], [-.34, .26, .45]].map(([x, y, s], i) => {
    const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: STAR, color: new THREE.Color(2.2, 2.2, 2.2), blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, opacity: 0 }));
    sp.userData = { x, y, s: s * .17, t0: T.rise1 + .12 + i * .17, rot: .3 + R() * .2 }; cardGroup.add(sp); return sp;
  });

  S = {
    root, pack, strip, bodyF, bodyB, matF, matB, art, back, white, artTex: art, backArt: back,
    cardGroup, glowM, halo, burst, flare, lip, rays, bars, parts, tw, card, swappedF: !CFG.mystery, swappedB: !CFG.mystery,
    dispose: () => { dispose.forEach(d => d.dispose()); parts.geometry.dispose(); },
  };
}

/* ---------------------------------------------------------------- timeline */
// GIF spin is near-linear: edge-on at f12 (90°), f26 (270°), front again at f33
const spinE = k => .78 * k + .22 * ease.io2(k);
const T_SWAP_F = (() => { let a = 0, b = 1; for (let i = 0; i < 30; i++) { const m = (a + b) / 2; spinE(m) < .25 ? a = m : b = m; } return T.spin0 + a * (T.spin1 - T.spin0); })();
const tmpV = new THREE.Vector3();
const mouse = { x: 0, y: 0, sx: 0, sy: 0 };
addEventListener('pointermove', e => { mouse.x = e.clientX / innerWidth * 2 - 1; mouse.y = e.clientY / innerHeight * 2 - 1; });

function update(t) {
  const { pack, strip, cardGroup } = S;
  partMat.uniforms.uTime.value = t;

  /* --- pack rotation / hover --- */
  let rotY = 0, rotZ = 0, rotX = 0, blur = 0, dir = [1, 0], radial = 0;
  if (t >= T.spin0 && t < T.spin1) {
    const k = seg(t, T.spin0, T.spin1), e = spinE(k);
    rotY = e * Math.PI * 2; rotX = .07 * Math.sin(k * Math.PI);
    const speed = Math.abs(spinE(clamp(k + .01)) - spinE(clamp(k - .01))) / .02;
    blur = .012 * speed; dir = [1, 0];
  } else if (t >= T.spin1 && t < T.tilt1) {
    const k = ease.o3(seg(t, T.spin1, T.tilt1)); rotY = .35 * k; rotZ = -.06 * k;
  } else if (t >= T.tilt1 && t < T.zoom1) {
    const k = ease.io2(seg(t, T.tilt1, T.zoom1)); rotY = .35 * (1 - k); rotZ = -.06 * (1 - k);
    blur = .09 * Math.sin(Math.PI * k); radial = 1;
  } else if (t >= T.zoom1) {
    rotY = .012 * Math.sin(t * 1.4); rotX = .006 * Math.sin(t * 1.1);
  }
  // mystery reveal (deterministic in t): back swaps while hidden, front swaps when the pack is edge-on
  const tSwapF = T_SWAP_F;
  S.matF.map = CFG.mystery && t < tSwapF ? S.white : S.art;
  S.matB.map = CFG.mystery && t < T.spin0 + .02 ? S.white : S.back;
  pack.rotation.set(rotX, rotY, rotZ);
  pack.position.y = t < T.tilt1 ? .012 * Math.sin(t * 2.2) : 0;

  /* --- camera --- */
  const zk = ease.io2(seg(t, T.tilt1, T.zoom1));
  let cy = lerp(0, view.yClose, zk), cz = lerp(view.dWide, view.dClose, zk);
  cz += t > T.zoom1 && t < T.tear ? -.02 * seg(t, T.zoom1, T.tear) : 0;                  // slow creep during hold
  const rk = ease.io3(seg(t, T.rise0, T.rise1));
  const yFinal = view.yClose + 1.45;
  cy = lerp(cy, yFinal, rk);
  if (t > T.zoom1 && t < T.tear) cz -= 0;
  camera.position.set(0, cy, cz); camera.lookAt(0, cy, 0);
  bgB.material.opacity = smooth(T.tilt1 + .1, T.zoom1, t);

  /* --- tear strip --- */
  if (t < T.tear) { strip.position.set(0, (TEAR_V + 1) / 2 * PH - PH / 2, 0); strip.rotation.set(0, 0, 0); strip.visible = true; }
  else {
    const pre = seg(t, T.tear, T.strip), s = Math.max(0, t - T.strip);
    const y0 = (TEAR_V + 1) / 2 * PH - PH / 2;
    strip.position.set(.18 * s + .5 * s * s, y0 + .01 * pre + .75 * s + 1.1 * s * s, .2 * s);
    strip.rotation.set(-.08 * pre - 1.3 * s, .45 * s, .12 * pre - .3 * s - .6 * s * s);
    strip.visible = s < 1.1;
  }

  /* --- light burst --- */
  const burstA = env(t, T.strip - .04, T.strip + .12, T.rise0 - .02, T.rise0 + .16);
  S.lip.material.opacity = burstA * (.85 + .15 * Math.sin(t * 40));
  S.lip.scale.set(PW * (1.05 + .12 * burstA), .07 + .04 * burstA, 1);
  for (const r of S.rays) {
    const f = .55 + .45 * Math.sin(t * 17 + r.userData.seed * 7);
    r.material.opacity = burstA * r.userData.base * f;
    r.scale.y = .6 + .4 * smooth(T.strip, T.strip + .25, t);
  }
  const fk = seg(t, T.tear, T.strip + .05);
  S.flare.position.set(lerp(-PW / 2, PW / 2 + .02, ease.io2(fk)), TEAR_Y + .005, .07);
  S.flare.material.opacity = env(t, T.tear - .03, T.tear + .03, T.strip, T.strip + .12);
  S.flare.scale.setScalar(.22 + .06 * Math.sin(t * 50));
  const tearFlash = env(t, T.tear - .02, T.tear + .04, T.strip, T.strip + .1);
  S.lip.material.opacity = Math.max(S.lip.material.opacity, tearFlash * .7);

  /* --- card --- */
  const emergeY = TEAR_Y - CASE_H / 2 - .02;
  const outY = TEAR_Y + CASE_H * .08;
  let y = emergeY, sc = .74, glow = 1;
  if (t >= T.card0) {
    const k = ease.o3(seg(t, T.card0, T.rise0)); y = lerp(emergeY, outY, k);
  }
  if (t >= T.rise0) {
    const k = seg(t, T.rise0, T.rise1);
    // card screen-offset from camera: leads the camera upward (f104–f106), then settles at centre (f112)
    const visH = 2 * view.dClose * TANH, o0 = outY - view.yClose;
    y = cy + lerp(o0, 0, ease.io2(k)) + .26 * visH * Math.sin(Math.PI * Math.pow(k, .8)) * (1 - k * .3);
    sc = lerp(.74, 1, ease.o3(k));
    blur = .07 * Math.sin(Math.PI * Math.min(1, k * 1.15)); dir = [0, 1]; radial = 0;
  }
  glow = 1 - smooth(T.card0 + .12, T.rise0 + .22, t);
  cardGroup.visible = t >= T.card0 - .05;
  cardGroup.position.set(0, y, 0);
  cardGroup.scale.setScalar(sc);
  S.glowM.material.opacity = glow;
  S.halo.material.opacity = .55 * glow;
  pack.visible = t < T.rise1 + .2;

  // idle after reveal: hover + follow pointer
  if (t > T.rise1) {
    const k = smooth(T.rise1, T.rise1 + .5, t);
    mouse.sx += (mouse.x - mouse.sx) * .06; mouse.sy += (mouse.y - mouse.sy) * .06;
    cardGroup.position.y += .006 * Math.sin((t - T.rise1) * 1.6) * k;
    cardGroup.rotation.set(mouse.sy * .16 * k, mouse.sx * .22 * k, 0);
  } else cardGroup.rotation.set(0, 0, 0);

  /* --- light bars --- */
  for (const b of S.bars) {
    const a = env(t, T.rise0 - .02 + b.userData.d, T.rise0 + .08 + b.userData.d, T.rise1 - .05, T.rise1 + .15);
    b.material.opacity = a * (.5 + .5 * Math.sin(t * 30 + b.userData.seed * 9));
    b.scale.y = .6 + 1.4 * seg(t, T.rise0, T.rise1);
  }

  /* --- twinkles --- */
  for (const s of S.tw) {
    const u = s.userData; if (t < u.t0) { s.material.opacity = 0; continue; }
    const cyc = 1.9, k = ((t - u.t0) % cyc) / .5;
    const a = k < 1 ? Math.sin(Math.PI * k) : 0;
    s.material.opacity = a; s.scale.setScalar(u.s * (.4 + .6 * a)); s.position.set(u.x, u.y, .03); s.material.rotation = u.rot + (t - u.t0) * .6;
  }

  blurPass.uniforms.uStrength.value = blur;
  blurPass.uniforms.uDir.value.set(dir[0], dir[1]);
  blurPass.uniforms.uRadial.value = radial;
}

/* ---------------------------------------------------------------- UI + loop */
const ui = {
  info: document.getElementById('info'), name: document.getElementById('cardName'), meta: document.getElementById('cardMeta'),
  again: document.getElementById('again'), replay: document.getElementById('replay'), loading: document.getElementById('loading'), err: document.getElementById('error'),
};
let cards = [], current = null, busy = false;

function pickCard(forceFile) {
  if (forceFile) return cards.find(c => c.f === forceFile) || { n: forceFile, no: '?', f: forceFile };
  return cards[Math.floor(Math.random() * cards.length)];
}
async function open(card) {
  if (busy) return; busy = true; ui.info.classList.remove('on');
  try {
    await build({ ...card, seed: Math.floor(Math.random() * 1e9) });
    current = card;
    ui.name.textContent = card.n;
    ui.meta.textContent = `${CFG.pack.set} · #${card.no}`;
    startTime = performance.now();
    ui.loading.hidden = true;
  } catch (e) {
    ui.loading.hidden = true; ui.err.hidden = false;
    ui.err.textContent = e.message + ' — start the game with start.bat so the card folder is reachable.';
    console.error(e);
  }
  busy = false;
}
ui.again.onclick = () => open(pickCard());
ui.replay.onclick = () => open(current);
addEventListener('keydown', e => { if (e.code === 'Space') { e.preventDefault(); open(pickCard()); } if (e.key === 'r') open(current); });

function loop(now) {
  requestAnimationFrame(loop);
  if (!S) return;
  const t = FREEZE ?? (now - startTime) / 1000;
  update(t);
  ui.info.classList.toggle('on', t > T.rise1 + .35);
  composer.render();
}

fit();
(async () => {
  try { cards = await (await fetch(CFG.pack.data)).json(); }
  catch { cards = [{ n: 'Mega Charizard X ex', no: '130', f: 'Mega_Charizard_X_ex_PFL_130.jpg' }]; }
  await open(pickCard(Q.get('card')));
  window.__ready = true;
  requestAnimationFrame(loop);
})();
