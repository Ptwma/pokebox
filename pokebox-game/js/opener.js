// Pokebox — 3D pack opening (GIF-matched intro + multi-card reveal)
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

/* timeline, seconds — from the reference GIF (141 frames @ 25 fps) */
const T = { spin0: .2, spin1: 1.36, tilt1: 1.76, zoom1: 2.24, tear: 3.2, strip: 3.42, card0: 3.84, rise0: 4.04, rise1: 4.46 };
const PH = 1.426, BULGE = .085, CRIMP = .042, TEAR_V = 1 - .056, TEAR_Y = (TEAR_V - .5) * PH;
const CARD_W = .46, CARD_H = CARD_W / .716, BORDER = .034, CASE_W = CARD_W + BORDER * 2, CASE_H = CARD_H + BORDER * 2;
const FRAME = ['#4e364e', '#4e364e', '#35405a', '#22585a', '#452d8a', '#8c3669', '#9a6c14'];
const THEMES = {
  studio: { bgC: '#f7e6ef', bgM: '#e1ccd6', bgE: '#bfb1b6', flat: '#bdadb5', flatLow: '#cdc5c6', rim: '#f6eff3', ray: [1.9, 1.75, 1.85], spark: [2.2, 2.1, 2.2], light: 0xffd9e8 },
  dark: { bgC: '#2a241d', bgM: '#15120f', bgE: '#050505', flat: '#0d0c0b', flatLow: '#1a1714', rim: '#f7ebc3', ray: [2.0, 1.8, 1.3], spark: [2.3, 2.1, 1.6], light: 0xffe3b0 },
};

const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const lerp = (a, b, k) => a + (b - a) * k;
const seg = (t, a, b) => clamp((t - a) / (b - a));
const smooth = (a, b, x) => { const k = clamp((x - a) / (b - a)); return k * k * (3 - 2 * k); };
const env = (t, a, b, c, d) => smooth(a, b, t) * (1 - smooth(c, d, t));
const E = {
  io3: k => k < .5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2,
  io2: k => k < .5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2,
  o3: k => 1 - Math.pow(1 - k, 3),
  oBack: (k, s = 1.4) => 1 + (s + 1) * Math.pow(k - 1, 3) + s * Math.pow(k - 1, 2),
};
const spinE = k => .78 * k + .22 * E.io2(k);
const T_SWAP = (() => { let a = 0, b = 1; for (let i = 0; i < 30; i++) { const m = (a + b) / 2; spinE(m) < .25 ? a = m : b = m; } return T.spin0 + a * (T.spin1 - T.spin0); })();
function rng(seed) { let s = seed >>> 0; return () => ((s = (Math.imul(s, 1664525) + 1013904223) >>> 0) / 4294967296); }
function canvasTex(w, h, draw, srgb = true) {
  const c = document.createElement('canvas'); c.width = w; c.height = h; draw(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c); if (srgb) t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t;
}
const loader = new THREE.TextureLoader();
const MAX_TEX_H = 1400;
const loadTex = url => new Promise((res, rej) => loader.load(url, t => { t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; res(t); }, undefined, () => rej(new Error('Missing image: ' + decodeURIComponent(url)))));
// card faces: decode + downscale off the main thread (no mid-animation decode hitches), cap at 1400px tall
async function loadCardTex(url) {
  if (typeof createImageBitmap !== 'function') return loadTex(url);
  const r = await fetch(url); if (!r.ok) throw new Error('Missing image: ' + decodeURIComponent(url));
  const blob = await r.blob(), probe = await createImageBitmap(blob), k = Math.min(1, MAX_TEX_H / probe.height);
  const w = Math.round(probe.width * k), h = Math.round(probe.height * k); probe.close();
  const bmp = await createImageBitmap(blob, { imageOrientation: 'flipY', resizeWidth: w, resizeHeight: h, resizeQuality: 'high' });
  const t = new THREE.Texture(bmp); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; t.flipY = false; t.needsUpdate = true; return t;
}

export const T_ZOOMED = T.zoom1; // pack centred and close to camera, just before the tear
export function createOpener(canvas, hooks = {}) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  // supersample: never render below 1.5x, cap at 2x for performance
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5)); // adaptive loop below lowers it further on weak GPUs
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.NeutralToneMapping;
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(30, 1, .01, 100); scene.add(camera);
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), .04).texture; scene.environmentIntensity = .55;
  const key = new THREE.DirectionalLight(0xffffff, .9); key.position.set(-2, 3, 4); scene.add(key);
  const rimL = new THREE.DirectionalLight(0xffd9e8, 1.1); rimL.position.set(3, 1.5, -2); scene.add(rimL);
  scene.add(new THREE.AmbientLight(0xffffff, .15));
  const TANH = Math.tan(THREE.MathUtils.degToRad(15));

  /* textures */
  function crinkleNormal(size = 256, seed = 7) {
    const R = rng(seed), H = new Float32Array(size * size);
    for (const [n, amp] of [[8, 1], [16, .5], [32, .25], [64, .12]]) {
      const g = Array.from({ length: n * n }, R);
      for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
        const fx = x / size * n, fy = y / size * n, x0 = Math.floor(fx), y0 = Math.floor(fy), sx = fx - x0, sy = fy - y0;
        const ux = sx * sx * (3 - 2 * sx), uy = sy * sy * (3 - 2 * sy);
        const a = g[(y0 % n) * n + x0 % n], b = g[(y0 % n) * n + (x0 + 1) % n], c = g[((y0 + 1) % n) * n + x0 % n], d = g[((y0 + 1) % n) * n + (x0 + 1) % n];
        H[y * size + x] += amp * lerp(lerp(a, b, ux), lerp(c, d, ux), uy);
      }
    }
    for (let i = 0; i < 40; i++) {
      const x0 = R() * size, y0 = R() * size, ang = R() * Math.PI, len = 10 + R() * 70, w = .7 + R() * 1.4, dep = (R() - .5) * .9, dx = Math.cos(ang), dy = Math.sin(ang);
      for (let s = -len; s < len; s++) for (let o = -w * 3; o <= w * 3; o++) {
        const X = ((Math.round(x0 + dx * s - dy * o) % size) + size) % size, Y = ((Math.round(y0 + dy * s + dx * o) % size) + size) % size;
        H[Y * size + X] += dep * Math.exp(-(o * o) / (w * w)) * (1 - Math.abs(s) / len);
      }
    }
    const data = new Uint8Array(size * size * 4), h = (X, Y) => H[(((Y % size) + size) % size) * size + ((X % size) + size) % size];
    for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
      let nx = (h(x - 1, y) - h(x + 1, y)) * 2.2, ny = (h(x, y - 1) - h(x, y + 1)) * 2.2, nz = 1; const l = Math.hypot(nx, ny, nz);
      const i = (y * size + x) * 4; data[i] = (nx / l * .5 + .5) * 255; data[i + 1] = (ny / l * .5 + .5) * 255; data[i + 2] = (nz / l * .5 + .5) * 255; data[i + 3] = 255;
    }
    const t = new THREE.DataTexture(data, size, size); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(1.3, 2.4); t.needsUpdate = true; return t;
  }
  const crinkle = crinkleNormal();
  const STAR = canvasTex(256, 256, (g, w) => {
    const c = w / 2, r = g.createRadialGradient(c, c, 0, c, c, c * .45); r.addColorStop(0, '#fff'); r.addColorStop(.25, 'rgba(255,255,255,.85)'); r.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = r; g.fillRect(0, 0, w, w); g.fillStyle = '#fff'; g.shadowColor = '#fff'; g.shadowBlur = 6;
    const ray = (rot) => { g.save(); g.translate(c, c); g.rotate(rot); g.beginPath(); g.moveTo(0, -c * .98); g.lineTo(5, 0); g.lineTo(0, c * .98); g.lineTo(-5, 0); g.closePath(); g.fill(); g.restore(); };
    ray(0); ray(Math.PI / 2);
  }, false);
  const GLOW = canvasTex(128, 128, (g, w) => { const r = g.createRadialGradient(w / 2, w / 2, 0, w / 2, w / 2, w / 2); r.addColorStop(0, '#fff'); r.addColorStop(.35, 'rgba(255,255,255,.6)'); r.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = r; g.fillRect(0, 0, w, w); }, false);
  const BEAM = canvasTex(64, 512, (g, w, h) => { for (let x = 0; x < w; x++) { const k = Math.exp(-Math.pow((x - w / 2) / (w * .18), 2)); const l = g.createLinearGradient(0, h, 0, 0); l.addColorStop(0, `rgba(255,255,255,${k})`); l.addColorStop(.35, `rgba(255,255,255,${k * .55})`); l.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = l; g.fillRect(x, 0, 1, h); } }, false);
  const BAR = canvasTex(16, 256, (g, w, h) => { const l = g.createLinearGradient(0, 0, 0, h); l.addColorStop(0, 'rgba(255,255,255,0)'); l.addColorStop(.5, '#fff'); l.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = l; g.fillRect(0, 0, w, h); }, false);
  const MASK = canvasTex(256, 358, (g, w, h) => { g.fillStyle = '#000'; g.fillRect(0, 0, w, h); g.fillStyle = '#fff'; g.beginPath(); g.roundRect(0, 0, w, h, 12); g.fill(); }, false);
  const CARDBACK = canvasTex(512, 714, (g, w, h) => {
    const r = g.createRadialGradient(w / 2, h / 2, 10, w / 2, h / 2, h * .7); r.addColorStop(0, '#3d6fd6'); r.addColorStop(.6, '#1f3f99'); r.addColorStop(1, '#0d1f55');
    g.fillStyle = '#e8b93a'; g.beginPath(); g.roundRect(0, 0, w, h, 26); g.fill(); g.fillStyle = r; g.beginPath(); g.roundRect(22, 22, w - 44, h - 44, 18); g.fill();
    g.save(); g.translate(w / 2, h / 2); for (let i = 0; i < 18; i++) { g.rotate(Math.PI / 9); g.fillStyle = 'rgba(255,255,255,.05)'; g.beginPath(); g.moveTo(0, 0); g.lineTo(-40, -h); g.lineTo(40, -h); g.fill(); } g.restore();
    g.fillStyle = '#d33'; g.beginPath(); g.arc(w / 2, h / 2, 110, Math.PI, 0); g.fill(); g.fillStyle = '#f4f4f4'; g.beginPath(); g.arc(w / 2, h / 2, 110, 0, Math.PI); g.fill();
    g.fillStyle = '#111'; g.fillRect(w / 2 - 110, h / 2 - 9, 220, 18); g.beginPath(); g.arc(w / 2, h / 2, 38, 0, 7); g.fill(); g.fillStyle = '#f4f4f4'; g.beginPath(); g.arc(w / 2, h / 2, 24, 0, 7); g.fill();
    g.fillStyle = 'rgba(255,255,255,.9)'; g.font = '900 42px "Arial Black", Impact, sans-serif'; g.textAlign = 'center'; g.fillText('POKEBOX', w / 2, h * .2);
  });
  const WHITE = canvasTex(780, 1426, (g, w, h) => {
    const l = g.createLinearGradient(0, 0, w, h); l.addColorStop(0, '#e9e9ea'); l.addColorStop(.5, '#d6d6d8'); l.addColorStop(1, '#e4e4e6'); g.fillStyle = l; g.fillRect(0, 0, w, h);
    for (const top of [true, false]) for (let i = 0; i < 9; i++) { g.fillStyle = i % 2 ? '#d8d8d8' : '#fdfdfd'; g.fillRect(0, top ? i * 6.6 : h - 60 + i * 6.6, w, 3.3); }
    const tg = g.createLinearGradient(0, h * .36, 0, h * .64); tg.addColorStop(0, '#1d1d1f'); tg.addColorStop(.45, '#8d8d92'); tg.addColorStop(.55, '#2a2a2d'); tg.addColorStop(1, '#5a5a5e');
    g.fillStyle = tg; g.textAlign = 'center'; g.textBaseline = 'middle'; g.font = '900 150px "Arial Black", Impact, sans-serif';
    ['RIP', 'THE', 'PACK'].forEach((s, i) => g.fillText(s, w / 2, h * .41 + i * 150));
    g.font = '700 26px Arial, sans-serif'; g.fillStyle = '#9a9aa0'; g.fillText('P O K E B O X', w / 2, h * .87);
  });
  function wrapFromLogo(logoImg, name) {
    return canvasTex(780, 1426, (g, w, h) => {
      const hue = [...name].reduce((a, c) => a + c.charCodeAt(0), 0) % 360;
      const l = g.createLinearGradient(0, 0, w, h); l.addColorStop(0, `hsl(${hue},45%,22%)`); l.addColorStop(.5, `hsl(${(hue + 40) % 360},55%,38%)`); l.addColorStop(1, `hsl(${hue},45%,14%)`);
      g.fillStyle = l; g.fillRect(0, 0, w, h);
      for (const top of [true, false]) for (let i = 0; i < 9; i++) { g.fillStyle = i % 2 ? 'rgba(0,0,0,.25)' : 'rgba(255,255,255,.18)'; g.fillRect(0, top ? i * 6.6 : h - 60 + i * 6.6, w, 3.3); }
      g.fillStyle = '#fff'; g.textAlign = 'center'; g.font = '900 64px "Arial Black", Impact, sans-serif'; g.fillText('POKÉMON', w / 2, h * .16);
      if (logoImg) { const s = Math.min((w * .8) / logoImg.width, 300 / logoImg.height); g.drawImage(logoImg, (w - logoImg.width * s) / 2, h * .42 - logoImg.height * s / 2, logoImg.width * s, logoImg.height * s); }
      else { g.font = '900 70px Impact, sans-serif'; g.fillText(name.toUpperCase(), w / 2, h * .45); }
      g.font = '700 26px Arial'; g.fillText('10 ADDITIONAL GAME CARDS', w / 2, h * .9);
    });
  }
  function backTex(img) {
    return canvasTex(780, 1426, (g, w, h) => {
      g.save(); g.translate(w, 0); g.scale(-1, 1); g.filter = 'blur(10px) saturate(1.2)'; g.drawImage(img, -20, -20, w + 40, h + 40); g.restore(); g.filter = 'none';
      g.fillStyle = 'rgba(12,10,18,.62)'; g.fillRect(0, 0, w, h);
      g.fillStyle = '#f2f2f2'; g.textAlign = 'center'; g.font = '900 44px "Arial Black", Impact, sans-serif'; g.fillText('POKÉMON', w / 2, h * .2);
      g.font = '700 24px Arial'; g.fillText('TRADING CARD GAME', w / 2, h * .2 + 40);
      g.fillStyle = '#fff'; g.fillRect(w - 250, h - 190, 180, 90); for (let x = 0; x < 160; x += 4) { g.fillStyle = '#111'; g.fillRect(w - 240 + x, h - 180, (x * 7 % 3) + 1, 60); }
    });
  }

  /* background (camera-locked) */
  let theme = THEMES.studio;
  const bgA = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ depthWrite: false, transparent: true, toneMapped: false }));
  const bgB = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ depthWrite: false, transparent: true, toneMapped: false }));
  bgA.position.z = -30; bgB.position.z = -29.9; bgA.renderOrder = bgB.renderOrder = -10; camera.add(bgA, bgB);
  function setTheme(name) {
    theme = THEMES[name] || THEMES.studio;
    bgA.material.map?.dispose(); bgB.material.map?.dispose();
    bgA.material.map = canvasTex(1024, 576, (g, w, h) => { const r = g.createRadialGradient(w / 2, h * .48, 0, w / 2, h * .5, w * .62); r.addColorStop(0, theme.bgC); r.addColorStop(.45, theme.bgM); r.addColorStop(1, theme.bgE); g.fillStyle = r; g.fillRect(0, 0, w, h); });
    bgB.material.map = canvasTex(512, 512, (g, w, h) => { const l = g.createLinearGradient(0, 0, 0, h); l.addColorStop(0, theme.flat); l.addColorStop(.7, theme.flat); l.addColorStop(1, theme.flatLow); g.fillStyle = l; g.fillRect(0, 0, w, h); });
    bgA.material.needsUpdate = bgB.material.needsUpdate = true;
    rimL.color.set(theme.light); partMat.uniforms.uCol.value.setRGB(...theme.spark); partMat2.uniforms.uCol.value.setRGB(...theme.spark);
  }

  /* pack geometry */
  function packZ(u, v) {
    if (v < CRIMP || v > 1 - CRIMP) return .0016 * (Math.sin(v * PH * 840) * .5 + .5);
    const e = smooth(CRIMP, CRIMP + .1, v) * (1 - smooth(1 - CRIMP - .1, 1 - CRIMP, v));
    let z = BULGE * Math.pow(Math.sin(Math.PI * u), .55) * Math.pow(e, .8);
    const wz = Math.exp(-Math.pow((v - (1 - CRIMP - .045)) / .028, 2)) + Math.exp(-Math.pow((v - (CRIMP + .045)) / .028, 2));
    return z + .0038 * Math.sin(v * PH * 150 + u * 7) * wz * Math.sin(Math.PI * u);
  }
  const packE = v => smooth(CRIMP, CRIMP + .1, v) * (1 - smooth(1 - CRIMP - .1, 1 - CRIMP, v));
  const jag = u => (.0045 * Math.sin(u * 97) + .003 * Math.sin(u * 231 + 1.3) + .002 * Math.sin(u * 511)) / PH;
  function faceGeo(PW, v0, v1, jagEdge, mirror) {
    const sx = 60, sy = Math.max(4, Math.round(120 * (v1 - v0))), pos = [], uv = [], idx = [];
    for (let j = 0; j <= sy; j++) for (let i = 0; i <= sx; i++) {
      const u = i / sx; let v = v0 + (v1 - v0) * j / sy;
      if (jagEdge === 'top' && j === sy) v += jag(u); if (jagEdge === 'bottom' && j === 0) v += jag(u);
      pos.push((u - .5) * PW * (1 - .03 * packE(v) * Math.sin(Math.PI * v)), (v - .5) * PH, packZ(u, v)); uv.push(mirror ? 1 - u : u, v);
    }
    for (let j = 0; j < sy; j++) for (let i = 0; i < sx; i++) { const a = j * (sx + 1) + i, b = a + 1, c = a + sx + 1, d = c + 1; idx.push(a, b, d, a, d, c); }
    const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2)); g.setIndex(idx); g.computeVertexNormals(); return g;
  }
  const foilMat = map => new THREE.MeshPhysicalMaterial({ map, normalMap: crinkle, normalScale: new THREE.Vector2(.22, .22), roughness: .3, metalness: .3, clearcoat: 1, clearcoatRoughness: .16, iridescence: .18, iridescenceIOR: 1.3 });

  /* particles */
  const partMat = new THREE.ShaderMaterial({
    uniforms: { uTime: { value: 0 }, uTex: { value: STAR }, uPR: { value: renderer.getPixelRatio() }, uCol: { value: new THREE.Color(2.2, 2.1, 2.2) } },
    vertexShader: `attribute vec3 vel; attribute float t0; attribute float life; attribute float sz; attribute float seed;
      uniform float uTime; uniform float uPR; varying float vA; varying float vRot;
      void main(){ float age=uTime-t0; float k=age/life; float alive=step(0.0,age)*step(age,life);
        vec3 p=position+vel*age+vec3(0.0,-0.35,0.0)*age*age*0.5; vec4 mv=modelViewMatrix*vec4(p,1.0); gl_Position=projectionMatrix*mv;
        float tw=0.55+0.45*sin(age*28.0+seed*40.0); vA=alive*(1.0-k)*tw*smoothstep(0.0,0.06,k);
        gl_PointSize=alive*sz*uPR*320.0*(1.0-0.4*k)/-mv.z; vRot=seed*6.2831; }`,
    fragmentShader: `uniform sampler2D uTex; uniform vec3 uCol; varying float vA; varying float vRot;
      void main(){ vec2 p=gl_PointCoord-0.5; float c=cos(vRot), s=sin(vRot); p=mat2(c,-s,s,c)*p+0.5; vec4 t=texture2D(uTex,p); gl_FragColor=vec4(uCol*t.rgb,t.a*vA); }`,
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  });
  const partMat2 = partMat.clone(); partMat2.uniforms.uTime.value = 99;
  function particles(list, mat = partMat) {
    const g = new THREE.BufferGeometry(), n = list.length, f = k => new Float32Array(n * k);
    const P = f(3), V = f(3), T0 = f(1), L = f(1), SZ = f(1), SE = f(1);
    list.forEach((p, i) => { P.set(p.p, i * 3); V.set(p.v, i * 3); T0[i] = p.t0; L[i] = p.life; SZ[i] = p.sz; SE[i] = p.seed; });
    for (const [k, a, s] of [['position', P, 3], ['vel', V, 3], ['t0', T0, 1], ['life', L, 1], ['sz', SZ, 1], ['seed', SE, 1]]) g.setAttribute(k, new THREE.BufferAttribute(a, s));
    const pts = new THREE.Points(g, mat); pts.frustumCulled = false; return pts;
  }

  /* post */
  // 4x MSAA in the post-processing chain (renderer antialias does not apply to render targets)
  const composer = new EffectComposer(renderer, new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, samples: 2 }));
  composer.addPass(new RenderPass(scene, camera));
  const blurPass = new ShaderPass({
    uniforms: { tDiffuse: { value: null }, uStrength: { value: 0 }, uDir: { value: new THREE.Vector2(0, 1) }, uRadial: { value: 0 } },
    vertexShader: `varying vec2 vUv; void main(){ vUv=uv; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0); }`,
    fragmentShader: `uniform sampler2D tDiffuse; uniform float uStrength; uniform vec2 uDir; uniform float uRadial; varying vec2 vUv;
      void main(){ if(uStrength<0.0005){ gl_FragColor=texture2D(tDiffuse,vUv); return; }
        vec2 d=mix(uDir,(vUv-vec2(0.5,0.45))*2.0,uRadial)*uStrength; vec4 acc=vec4(0.0);
        for(int i=0;i<24;i++){ float t=float(i)/23.0-0.5; acc+=texture2D(tDiffuse,vUv+d*t); } gl_FragColor=acc/24.0; }`,
  });
  composer.addPass(blurPass);
  const bloom = new UnrealBloomPass(new THREE.Vector2(1, 1), .38, .35, 1.05); composer.addPass(bloom);
  composer.addPass(new OutputPass());

  /* card object (case + card face + holo + back + glow) */
  function rounded(w, h, r) { const s = new THREE.Shape(), x = -w / 2, y = -h / 2; s.moveTo(x + r, y); s.lineTo(x + w - r, y); s.quadraticCurveTo(x + w, y, x + w, y + r); s.lineTo(x + w, y + h - r); s.quadraticCurveTo(x + w, y + h, x + w - r, y + h); s.lineTo(x + r, y + h); s.quadraticCurveTo(x, y + h, x, y + h - r); s.lineTo(x, y + r); s.quadraticCurveTo(x, y, x + r, y); return s; }
  const ex = { depth: .03, bevelEnabled: true, bevelThickness: .003, bevelSize: .003, bevelSegments: 3, curveSegments: 10 };
  const holoMat = () => new THREE.ShaderMaterial({
    uniforms: { uT: { value: 0 }, uA: { value: 0 }, uTilt: { value: new THREE.Vector2() } },
    vertexShader: `varying vec2 vUv; void main(){ vUv=uv; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0); }`,
    fragmentShader: `uniform float uT; uniform float uA; uniform vec2 uTilt; varying vec2 vUv;
      vec3 hue(float h){ return clamp(abs(mod(h*6.0+vec3(0,4,2),6.0)-3.0)-1.0,0.0,1.0); }
      void main(){ float d=vUv.x*0.8+vUv.y*1.2+uTilt.x*1.5+uTilt.y*0.8+uT*0.05; float band=pow(0.5+0.5*sin(d*9.0),3.0);
        float glare=smoothstep(0.35,0.0,abs(vUv.x-0.5-uTilt.x*1.2+ (vUv.y-0.5)*0.6)); vec3 c=hue(fract(d*0.6))*band*0.8+vec3(glare)*0.5;
        gl_FragColor=vec4(c*uA,1.0); }`,
    transparent: true, blending: THREE.AdditiveBlending, depthWrite: false,
  });
  // card face: sRGB texture + rounded mask + contrast-adaptive sharpening (keeps small print crisp when upscaled)
  const faceMat = () => new THREE.ShaderMaterial({
    uniforms: { map: { value: null }, mask: { value: MASK }, texel: { value: new THREE.Vector2(1 / 733, 1 / 1024) }, amount: { value: .55 } },
    vertexShader: `varying vec2 vUv; void main(){ vUv=uv; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0); }`,
    fragmentShader: `uniform sampler2D map; uniform sampler2D mask; uniform vec2 texel; uniform float amount; varying vec2 vUv;
      void main(){
        vec3 c=texture2D(map,vUv).rgb, n=texture2D(map,vUv+vec2(0.,texel.y)).rgb, s=texture2D(map,vUv-vec2(0.,texel.y)).rgb,
             e=texture2D(map,vUv+vec2(texel.x,0.)).rgb, w=texture2D(map,vUv-vec2(texel.x,0.)).rgb;
        vec3 mn=min(c,min(min(n,s),min(e,w))), mx=max(c,max(max(n,s),max(e,w)));
        vec3 amp=clamp(min(mn,1.0-mx)/max(mx,1e-4),0.0,1.0); amp=sqrt(amp);
        vec3 wgt=-amp*mix(0.125,0.2,amount);
        vec3 col=clamp((c+(n+s+e+w)*wgt)/(1.0+4.0*wgt),0.0,1.0);
        gl_FragColor=vec4(col, texture2D(mask,vUv).r);
      }`,
    transparent: true,
  });
  function makeCard() {
    const g = new THREE.Group();
    const caseM = new THREE.Mesh(new THREE.ExtrudeGeometry(rounded(CASE_W, CASE_H, .02), ex), new THREE.MeshPhysicalMaterial({ color: FRAME[0], roughness: .5, clearcoat: .35, clearcoatRoughness: .3, envMapIntensity: .35 })); caseM.position.z = -.03;
    const rimM = new THREE.Mesh(new THREE.ExtrudeGeometry(rounded(CASE_W + .014, CASE_H + .014, .026), { ...ex, depth: .006 }), new THREE.MeshStandardMaterial({ color: '#f6eff3', roughness: .5, emissive: '#f6eff3', emissiveIntensity: .35 })); rimM.position.z = -.034;
    const face = new THREE.Mesh(new THREE.PlaneGeometry(CARD_W, CARD_H), faceMat()); face.position.z = .0035;
    const holo = new THREE.Mesh(new THREE.PlaneGeometry(CARD_W, CARD_H), holoMat()); holo.position.z = .004;
    const back = new THREE.Mesh(new THREE.PlaneGeometry(CARD_W, CARD_H), new THREE.MeshBasicMaterial({ map: CARDBACK, alphaMap: MASK, transparent: true, toneMapped: false })); back.position.z = -.037; back.rotation.y = Math.PI;
    const glow = new THREE.Mesh(new THREE.PlaneGeometry(CASE_W * 1.02, CASE_H * 1.02), new THREE.MeshBasicMaterial({ color: new THREE.Color(2.2, 2.1, 2.15), transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false })); glow.position.z = .006;
    const halo = new THREE.Sprite(new THREE.SpriteMaterial({ map: GLOW, color: new THREE.Color(1.6, 1.5, 1.55), blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, opacity: 0 })); halo.scale.set(CASE_W * 2.4, CASE_H * 1.8, 1); halo.position.z = -.08;
    const glass = new THREE.Mesh(new THREE.PlaneGeometry(CASE_W - .01, CASE_H - .01), new THREE.MeshPhysicalMaterial({ color: '#ffffff', transparent: true, opacity: .06, roughness: .05, metalness: 0, clearcoat: 1, clearcoatRoughness: .02, envMapIntensity: 2.2, depthWrite: false })); glass.position.z = .0065;
    g.add(halo, rimM, caseM, face, holo, glass, back, glow);
    g.userData = { caseM, rimM, face, holo, glow, halo };
    return g;
  }
  const RGLOW = [null, null, null, [1.2, 2.0, 2.4], [2.0, 1.4, 2.6], [2.6, 1.5, 2.0], [2.8, 2.1, .9]]; // halo colour hinting the rarity before the reveal
  const RAINBOW = [[2.2, 1.2, 1.4], [2.2, 1.9, 1.0], [1.2, 2.2, 1.5], [1.1, 1.7, 2.3], [1.9, 1.2, 2.3]];
  function dressCard(g, tex, r) {
    const u = g.userData; u.face.material.uniforms.map.value = tex; const im = tex.image; if (im && im.width) u.face.material.uniforms.texel.value.set(1 / im.width, 1 / im.height); u.face.material.uniforms.amount.value = im && im.width > 1200 ? .25 : .6;
    u.caseM.material.color.set(FRAME[r] || FRAME[0]);
    u.caseM.material.metalness = r >= 6 ? .8 : r >= 4 ? .4 : 0; u.caseM.material.roughness = r >= 6 ? .25 : .42;
    u.rimM.material.color.set(theme.rim); u.rimM.material.emissive.set(theme.rim);
    u.holo.material.uniforms.uA.value = [0, 0, .06, .16, .22, .26, .34][r] || 0;
  }

  /* per-open state */
  let S = null, running = false, raf = 0, t0 = 0, view = { dWide: 3.6, dClose: 1.55, yClose: .67 };
  const mouse = { x: 0, y: 0, sx: 0, sy: 0 };
  canvas.addEventListener('pointermove', e => { const r = canvas.getBoundingClientRect(); mouse.x = (e.clientX - r.left) / r.width * 2 - 1; mouse.y = (e.clientY - r.top) / r.height * 2 - 1; });

  function fit() {
    const w = canvas.clientWidth || innerWidth, h = canvas.clientHeight || innerHeight, a = w / h, PW = S ? S.PW : .78;
    renderer.setSize(w, h, false); composer.setSize(w, h); { const pr = renderer.getPixelRatio(); bloom.setSize(Math.round(w * pr / 2), Math.round(h * pr / 2)); } // half-res glow: same look, ~4x cheaper
    camera.aspect = a; camera.updateProjectionMatrix();
    const dH = (x, f) => (x / f) / 2 / TANH, dW = (x, f) => (x / f) / 2 / (TANH * a);
    view.dWide = Math.max(dH(PH, .73), dW(PW, .62));
    view.dClose = Math.max(dH(CASE_H, .8), dW(CASE_W, .8));
    view.yClose = PH / 2 - .05 * 2 * view.dClose * TANH;
    for (const [m, d] of [[bgA, 30], [bgB, 29.9]]) { const hh = 2 * d * TANH * 1.3; m.scale.set(hh * a, hh, 1); }
  }
  addEventListener('resize', () => running && fit());

  function dispose() {
    if (!S) return; scene.remove(S.root);
    S.root.traverse(o => { if (o.geometry) o.geometry.dispose(); if (o.material && o.material !== partMat && o.material !== partMat2) { const m = o.material; if (m.map && !S.keep.has(m.map)) m.map.dispose(); m.dispose?.(); } });
    S.cardTex.forEach(t => t !== CARDBACK && t.dispose()); S.own.forEach(t => t.dispose()); S = null;
  }

  async function play({ packUrl, logoUrl, setName, cards, mystery = true, themeName = 'studio', startAt = 0 }) {
    dispose(); setTheme(themeName);
    let art, own = [];
    try { art = await loadTex(packUrl); }
    catch { let logo = null; if (logoUrl) try { logo = await new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = logoUrl; }); } catch {} art = wrapFromLogo(logo, setName || 'Pokebox'); own.push(art); }
    if (!own.includes(art)) own.push(art);
    const PW = PH * (art.image.width / art.image.height);
    const back = backTex(art.image); own.push(back);
    const cardTex = await Promise.all(cards.map(c => (c.hd ? loadCardTex(c.hd).catch(() => loadCardTex(c.img)) : loadCardTex(c.img)).catch(() => loadTex(c.img)).catch(() => CARDBACK)));
    cardTex.forEach(t => { t.generateMipmaps = true; t.minFilter = THREE.LinearMipmapLinearFilter; t.anisotropy = renderer.capabilities.getMaxAnisotropy(); });
    const R = rng((Math.random() * 1e9) | 0);
    const root = new THREE.Group(); scene.add(root);
    const matF = foilMat(mystery ? WHITE : art), matB = foilMat(mystery ? WHITE : back);
    const pack = new THREE.Group(); root.add(pack);
    const bodyF = new THREE.Mesh(faceGeo(PW, 0, TEAR_V, 'top'), matF), bodyB = new THREE.Mesh(faceGeo(PW, 0, TEAR_V, 'top', true), matB); bodyB.rotation.y = Math.PI;
    const strip = new THREE.Group(), sy0 = (TEAR_V + 1) / 2 * PH - PH / 2; strip.position.y = sy0;
    const stripF = new THREE.Mesh(faceGeo(PW, TEAR_V, 1, 'bottom'), matF), stripB = new THREE.Mesh(faceGeo(PW, TEAR_V, 1, 'bottom', true), matB);
    stripF.position.y = stripB.position.y = -sy0; stripB.rotation.y = Math.PI; strip.add(stripF, stripB); pack.add(bodyF, bodyB, strip);

    const A = makeCard(), B = makeCard(); root.add(A, B); B.visible = false;
    dressCard(A, cardTex[0], cards[0].r);

    const burst = new THREE.Group(); burst.position.set(0, TEAR_Y, 0); root.add(burst);
    const lip = new THREE.Sprite(new THREE.SpriteMaterial({ map: GLOW, color: new THREE.Color(2.4, 2.3, 2.35), blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, opacity: 0 })); lip.position.z = .02; burst.add(lip);
    const mkRays = (n, spread, lenMin, lenMax) => Array.from({ length: n }, () => {
      const len = lenMin + R() * (lenMax - lenMin), w = .006 + R() * .026, geo = new THREE.PlaneGeometry(w, len); geo.translate(0, len / 2, 0);
      const m = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ map: BEAM, color: new THREE.Color(...theme.ray), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, opacity: 0 }));
      const a = (R() - .5) * 2; m.rotation.z = -Math.sign(a) * Math.pow(Math.abs(a), .8) * spread; m.userData = { seed: R() * 10, base: .22 + R() * .5 }; return m;
    });
    const rays = mkRays(32, 1.3, 1.1, 3); rays.forEach(m => { m.position.set((R() - .5) * PW * .75, 0, -.03 - R() * .02); burst.add(m); });
    // radial burst used behind rare reveals
    const rareBurst = new THREE.Group(); root.add(rareBurst);
    const rareRays = Array.from({ length: 28 }, (_, i) => { const len = 1.2 + R() * 1.4, geo = new THREE.PlaneGeometry(.03 + R() * .05, len); geo.translate(0, len / 2, 0);
      const m = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ map: BEAM, color: new THREE.Color(1.8, 1.7, 1.6), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, opacity: 0 }));
      m.rotation.z = i / 28 * Math.PI * 2 + R() * .1; m.position.z = -.08; m.userData = { seed: R() * 10, col: RAINBOW[i % RAINBOW.length] }; rareBurst.add(m); return m; });
    const bars = Array.from({ length: 46 }, () => { const h = .04 + Math.pow(R(), 2) * .36, m = new THREE.Mesh(new THREE.PlaneGeometry(.003 + R() * .01, h), new THREE.MeshBasicMaterial({ map: BAR, color: new THREE.Color(2, 1.95, 2), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, opacity: 0 }));
      m.position.set((R() - .5) * 1.2, TEAR_Y + .05 + R() * .3, .04); m.userData = { d: R() * .12, seed: R() * 10 }; root.add(m); return m; });
    const L = [];
    for (let i = 0; i < 170; i++) { const s = i / 170; L.push({ p: [-PW / 2 + s * PW, TEAR_Y + (R() - .5) * .012, .05], v: [(R() - .3) * .5, R() * .45 + .05, R() * .25], t0: T.tear + s * (T.strip - T.tear) + R() * .03, life: .2 + R() * .35, sz: .012 + R() * .04, seed: R() }); }
    for (let i = 0; i < 420; i++) { const a = (R() - .5) * 2.4, sp = .35 + R() * 1.4, big = R() < .06; L.push({ p: [(R() - .5) * PW * .8, TEAR_Y, (R() - .5) * .06], v: [Math.sin(a) * sp, Math.cos(a) * sp, R() * .3], t0: T.strip - .02 + Math.pow(R(), 2) * .75, life: .5 + R(), sz: big ? .12 + R() * .08 : .018 + R() * .06, seed: R() }); }
    for (let i = 0; i < 90; i++) L.push({ p: [(R() - .5) * CASE_W * 1.2, TEAR_Y + R() * .2, .05], v: [(R() - .5) * .2, .6 + R() * 1.2, .05], t0: T.card0 + R() * .5, life: .4 + R() * .6, sz: .01 + R() * .035, seed: R() });
    const parts = particles(L); root.add(parts);
    const bars2 = Array.from({ length: 40 }, () => { const h = .04 + Math.pow(R(), 2) * .36, m = new THREE.Mesh(new THREE.PlaneGeometry(.003 + R() * .01, h), new THREE.MeshBasicMaterial({ map: BAR, color: new THREE.Color(2, 1.95, 2), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, opacity: 0 }));
      m.position.set((R() - .5) * 1.2, 0, .04); m.userData = { d: R() * .12, seed: R() }; root.add(m); return m; });
    const L2 = []; for (let i = 0; i < 160; i++) { const a = (R() - .5) * 1.6, sp = .4 + R() * 1.2; L2.push({ p: [(R() - .5) * CASE_W, R() * .1, .05], v: [Math.sin(a) * sp * .5, Math.cos(a) * sp, R() * .2], t0: .15 + Math.pow(R(), 2) * .6, life: .5 + R() * .8, sz: R() < .06 ? .1 : .012 + R() * .045, seed: R() }); }
    const parts2 = particles(L2, partMat2); root.add(parts2);
    const flare = new THREE.Sprite(new THREE.SpriteMaterial({ map: STAR, color: new THREE.Color(2.6, 2.5, 2.6), blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, opacity: 0 })); root.add(flare);
    const tw = [[-.13, .2, .9], [.36, -.02, 1.25], [-.3, 0, .35], [.21, -.24, .8], [-.15, -.27, .55], [.33, .3, .7], [-.34, .26, .45]].map(([x, y, s], i) => {
      const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: STAR, color: new THREE.Color(2.2, 2.2, 2.2), blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, opacity: 0 }));
      sp.userData = { x, y, s: s * .17, off: .12 + i * .17, rot: .3 + R() * .2 }; root.add(sp); return sp;
    });
    // extra glitter burst for rare reveals (spawned on demand at time uRare)
    S = { bars2, parts2, root, pack, strip, sy0, matF, matB, art, back, PW, A, B, lip, rays, rareRays, rareBurst, bars, parts, flare, tw, cards, cardTex, own, mystery, keep: new Set([STAR, GLOW, BEAM, BAR, MASK, CARDBACK, WHITE, crinkle]),
      idx: 0, phase: 'intro', trans: null, revealT: T.rise1, rareT: -9, rareLv: 0, flipT: -9, done: false };
    fit();
    cardTex.forEach(t => renderer.initTexture(t)); renderer.initTexture(art); renderer.initTexture(back);
    try { await renderer.compileAsync(scene, camera); } catch { renderer.compile(scene, camera); }
    update(startAt); composer.render(); await new Promise(r => requestAnimationFrame(r));
    running = true; clock = startAt; last = performance.now(); perf.n = 0; perf.sum = 0; cancelAnimationFrame(raf); raf = requestAnimationFrame(loop);
    hooks.onStart?.();
  }

  function next() {
    if (!S) return;
    const t = clock;
    if (S.phase === 'intro') { if (t < T.rise1) clock = T.rise1; return; } // tap during intro = skip to first card
    if (S.trans) return;
    if (S.idx >= S.cards.length - 1) { hooks.onFinish?.(); return; }
    const k = S.idx + 1, c = S.cards[k];
    dressCard(S.B, S.cardTex[k], c.r);
    const big = k === S.cards.length - 1 && c.r >= 4;
    S.trans = { t: t, k, big, r: c.r };
    const hc = RGLOW[c.r]; S.B.userData.halo.material.color.setRGB(...(hc || [1.6, 1.5, 1.55]));
    hooks.onSwap?.(k, big, c.r);
  }
  function revealAll() { if (S) hooks.onFinish?.(); }

  function stop() { running = false; cancelAnimationFrame(raf); dispose(); renderer.clear(); }

  // clock advances by real time but never jumps more than 1/20 s, so a hitch slows the shot instead of skipping frames
  let clock = 0, last = 0; const perf = { n: 0, sum: 0, pr: renderer.getPixelRatio() };
  function loop(now) {
    if (!running) return;
    raf = requestAnimationFrame(loop);
    const dt = Math.max(0, (now - last) / 1000); last = now; clock += Math.min(dt, .05);
    update(clock); composer.render();
    // adaptive resolution: if the GPU can't hold ~50 fps, step the render scale down (never below 1x)
    perf.sum += dt; if (++perf.n === 40) {
      const avg = perf.sum / perf.n; perf.n = 0; perf.sum = 0;
      if (avg > .019 && perf.pr > .75) { perf.pr = Math.max(.75, perf.pr - .25); renderer.setPixelRatio(perf.pr); fit(); }
    }
  }

  function update(t) {
    const { pack, strip, A, B } = S;
    partMat.uniforms.uTime.value = t;
    let rotY = 0, rotZ = 0, rotX = 0, blur = 0, dir = [1, 0], radial = 0;
    if (t >= T.spin0 && t < T.spin1) {
      const k = seg(t, T.spin0, T.spin1); rotY = spinE(k) * Math.PI * 2; rotX = .07 * Math.sin(k * Math.PI);
      blur = .012 * Math.abs(spinE(clamp(k + .01)) - spinE(clamp(k - .01))) / .02;
    } else if (t >= T.spin1 && t < T.tilt1) { const k = E.o3(seg(t, T.spin1, T.tilt1)); rotY = .35 * k; rotZ = -.06 * k; }
    else if (t >= T.tilt1 && t < T.zoom1) { const k = E.io2(seg(t, T.tilt1, T.zoom1)); rotY = .35 * (1 - k); rotZ = -.06 * (1 - k); blur = .09 * Math.sin(Math.PI * k); radial = 1; }
    else if (t >= T.zoom1) { rotY = .012 * Math.sin(t * 1.4); rotX = .006 * Math.sin(t * 1.1); }
    S.matF.map = S.mystery && t < T_SWAP ? WHITE : S.art;
    S.matB.map = S.mystery && t < T.spin0 + .02 ? WHITE : S.back;
    pack.rotation.set(rotX, rotY, rotZ); pack.position.y = t < T.tilt1 ? .012 * Math.sin(t * 2.2) : 0;
    if (S.lastSwap !== (t < T_SWAP) && t > T.spin0) { S.lastSwap = t < T_SWAP; }
    // sound cues (fire once)
    cue('spin', t >= T.spin0, () => hooks.sfx?.('whoosh'));
    cue('zoom', t >= T.tilt1, () => hooks.sfx?.('whoosh'));
    cue('rip', t >= T.tear, () => hooks.sfx?.('rip'));
    cue('burst', t >= T.strip, () => hooks.sfx?.('burst'));
    cue('rise', t >= T.rise0, () => hooks.sfx?.('whoosh'));
    cue('first', t >= T.rise1, () => { S.phase = 'cards'; S.revealT = t; hooks.onReveal?.(0); fxForReveal(0, t); });

    // camera
    const zk = E.io2(seg(t, T.tilt1, T.zoom1));
    let cy = lerp(0, view.yClose, zk), cz = lerp(view.dWide, view.dClose, zk);
    if (t > T.zoom1 && t < T.tear) cz -= .02 * seg(t, T.zoom1, T.tear);
    const yFinal = view.yClose + 1.45;
    cy = lerp(cy, yFinal, E.io3(seg(t, T.rise0, T.rise1)));
    camera.position.set(0, cy, cz); camera.lookAt(0, cy, 0);
    bgB.material.opacity = smooth(T.tilt1 + .1, T.zoom1, t);

    // strip
    if (t < T.tear) { strip.position.set(0, S.sy0, 0); strip.rotation.set(0, 0, 0); strip.visible = true; }
    else { const pre = seg(t, T.tear, T.strip), s = Math.max(0, t - T.strip);
      strip.position.set(.18 * s + .5 * s * s, S.sy0 + .01 * pre + .75 * s + 1.1 * s * s, .2 * s);
      strip.rotation.set(-.08 * pre - 1.3 * s, .45 * s, .12 * pre - .3 * s - .6 * s * s); strip.visible = s < 1.1; }
    const burstA = env(t, T.strip - .04, T.strip + .12, T.rise0 - .02, T.rise0 + .16);
    S.lip.material.opacity = Math.max(burstA * (.85 + .15 * Math.sin(t * 40)), env(t, T.tear - .02, T.tear + .04, T.strip, T.strip + .1) * .7);
    S.lip.scale.set(S.PW * (1.05 + .12 * burstA), .07 + .04 * burstA, 1);
    for (const r of S.rays) { r.material.opacity = burstA * r.userData.base * (.55 + .45 * Math.sin(t * 17 + r.userData.seed * 7)); r.scale.y = .6 + .4 * smooth(T.strip, T.strip + .25, t); }
    const fk = seg(t, T.tear, T.strip + .05);
    S.flare.position.set(lerp(-S.PW / 2, S.PW / 2 + .02, E.io2(fk)), TEAR_Y + .005, .07); S.flare.material.opacity = env(t, T.tear - .03, T.tear + .03, T.strip, T.strip + .12); S.flare.scale.setScalar(.22 + .06 * Math.sin(t * 50));
    for (const b of S.bars) { b.material.opacity = env(t, T.rise0 - .02 + b.userData.d, T.rise0 + .08 + b.userData.d, T.rise1 - .05, T.rise1 + .15) * (.5 + .5 * Math.sin(t * 30 + b.userData.seed * 9)); b.scale.y = .6 + 1.4 * seg(t, T.rise0, T.rise1); }
    pack.visible = t < T.rise1 + .2;

    // first card rise
    const emergeY = TEAR_Y - CASE_H / 2 - .02, outY = TEAR_Y + CASE_H * .08;
    const Au = A.userData;
    if (S.phase === 'intro') {
      let y = emergeY, sc = .74;
      if (t >= T.card0) y = lerp(emergeY, outY, E.o3(seg(t, T.card0, T.rise0)));
      if (t >= T.rise0) { const k = seg(t, T.rise0, T.rise1), visH = 2 * view.dClose * TANH;
        y = cy + lerp(outY - view.yClose, 0, E.io2(k)) + .26 * visH * Math.sin(Math.PI * Math.pow(k, .8)) * (1 - k * .3); sc = lerp(.74, 1, E.o3(k));
        blur = .07 * Math.sin(Math.PI * Math.min(1, k * 1.15)); dir = [0, 1]; radial = 0; }
      A.visible = t >= T.card0 - .05; A.position.set(0, y, 0); A.scale.setScalar(sc); A.rotation.set(0, 0, 0);
      const glow = 1 - smooth(T.card0 + .12, T.rise0 + .22, t); Au.glow.material.opacity = glow; Au.halo.material.opacity = .55 * glow;
    } else {
      mouse.sx += (mouse.x - mouse.sx) * .06; mouse.sy += (mouse.y - mouse.sy) * .06;
      const base = yFinal, hover = .006 * Math.sin((t - S.revealT) * 1.6);
      if (S.trans) {
        // GIF-style reveal for every card: current card shoots up out of frame, next rises glowing from below
        const T0 = S.trans.t, D = .95, k = seg(t, T0, T0 + .38);
        A.position.set(0, base + hover + E.io2(k) * 1.7, 0); A.rotation.set(-.25 * k, 0, 0);
        B.visible = true;
        const kr = seg(t, T0 + .18, T0 + D), vis = 2 * view.dClose * TANH;
        const yB = base - 1.25 + (1.25 + .22 * vis * Math.sin(Math.PI * Math.pow(kr, .75)) * (1 - kr * .35)) * E.io2(kr);
        B.position.set(0, kr >= 1 ? base : yB, 0); B.scale.setScalar(lerp(.8, 1, E.o3(kr)));
        B.rotation.set(0, S.trans.big ? Math.PI : 0, 0);
        const Bu = B.userData; Bu.glow.material.opacity = 1 - smooth(T0 + .4, T0 + D + .1, t); const rb = S.trans.r >= 3 ? (S.trans.r - 2) * .22 : 0; Bu.halo.material.opacity = .6 * (1 - kr) + (S.trans.big ? .35 : 0) + rb * (.6 + .4 * Math.sin(t * (10 + S.trans.r * 3))); Bu.halo.scale.set(CASE_W * (2.4 + rb * 1.4), CASE_H * (1.8 + rb), 1);
        if (S.trans.r >= 5 && kr < 1) { camera.position.x += (Math.random() - .5) * .006 * (S.trans.r - 4); camera.position.y += (Math.random() - .5) * .006 * (S.trans.r - 4); }
        blur = .065 * Math.sin(Math.PI * seg(t, T0, T0 + D)); dir = [0, 1];
        for (const b of S.bars2) { b.position.y = base - .5 + b.userData.d * 3; b.material.opacity = env(t, T0 + .15 + b.userData.d, T0 + .3 + b.userData.d, T0 + D - .1, T0 + D + .2) * (.5 + .5 * Math.sin(t * 30 + b.userData.seed * 9)); b.scale.y = .6 + 1.4 * kr; }
        S.parts2.position.set(0, base - .45, 0); partMat2.uniforms.uTime.value = t - T0;
        if (t > T0 + D) { // swap roles
          const tmp = S.A; S.A = S.B; S.B = tmp; S.B.visible = false; S.idx = S.trans.k;
          if (S.trans.big) { S.flipT = t; hooks.sfx?.('whoosh'); } else { hooks.onReveal?.(S.idx); fxForReveal(S.idx, t); }
          S.revealT = t; S.trans = null;
        }
      } else {
        for (const b of S.bars2) b.material.opacity = 0; if (partMat2.uniforms.uTime.value < 5) partMat2.uniforms.uTime.value += 1 / 60;
        let ry = mouse.sx * .22, rx = mouse.sy * .16;
        if (S.flipT > 0) { // dramatic flip for the chase card
          const k = seg(t, S.flipT + .35, S.flipT + 1.05); ry += Math.PI * (1 - E.io3(k));
          A.userData.glow.material.opacity = .9 * (1 - k); A.userData.halo.material.opacity = .35 + .4 * (1 - k);
          if (k >= 1) { S.flipT = -9; hooks.onReveal?.(S.idx); fxForReveal(S.idx, t); }
        } else { A.userData.glow.material.opacity *= .92; A.userData.halo.material.opacity = S.rareLv >= 1 ? .22 + .08 * Math.sin(t * 3) : A.userData.halo.material.opacity * .94; }
        A.position.set(0, base + hover, 0); A.rotation.set(rx, ry, 0); A.scale.setScalar(1);
      }
      A.userData.holo.material.uniforms.uT.value = t; A.userData.holo.material.uniforms.uTilt.value.set(mouse.sx * .3, mouse.sy * .3);
    }
    // twinkles around the current card
    const cardY = S.phase === 'intro' ? yFinal : S.A.position.y;
    for (const s of S.tw) {
      const u = s.userData, st = S.revealT + u.off; if (S.phase === 'intro' && t < T.rise1 + u.off) { s.material.opacity = 0; continue; }
      if (t < st || S.trans) { s.material.opacity = 0; continue; }
      const k = ((t - st) % 1.9) / .5, a = k < 1 ? Math.sin(Math.PI * k) : 0;
      s.material.opacity = a * (S.rareLv >= 1 ? 1 : .8); s.scale.setScalar(u.s * (.4 + .6 * a) * (1 + S.rareLv * .25)); s.position.set(u.x, cardY + u.y, .03); s.material.rotation = u.rot + (t - st) * .6;
    }
    // rare burst behind the card
    const ra = env(t, S.rareT, S.rareT + .12, S.rareT + .9, S.rareT + 2.2) * (S.rareLv ? 1 : 0);
    S.rareBurst.position.set(0, cardY, -.1); S.rareBurst.rotation.z = t * .15;
    for (const m of S.rareRays) { m.material.opacity = ra * (.35 + .35 * Math.sin(t * 9 + m.userData.seed * 5)) * (.6 + S.rareLv * .2); if (S.rareLv >= 3) m.material.color.setRGB(...m.userData.col); else m.material.color.setRGB(1.8, 1.7, 1.6); m.scale.y = .7 + .5 * seg(t, S.rareT, S.rareT + .4); }

    blurPass.uniforms.uStrength.value = blur; blurPass.uniforms.uDir.value.set(dir[0], dir[1]); blurPass.uniforms.uRadial.value = radial;
  }
  function cue(name, cond, fn) { S.cues ||= {}; if (cond && !S.cues[name]) { S.cues[name] = 1; fn(); } }
  function fxForReveal(k, t) {
    const r = S.cards[k].r; S.rareLv = r >= 6 ? 3 : r >= 5 ? 2 : r >= 4 ? 1 : 0;
    if (r >= 4) { S.rareT = t; hooks.sfx?.('rare', S.rareLv); } else if (r >= 3) hooks.sfx?.('sparkle');
  }

  return { play, next, stop, revealAll, get active() { return running; }, resize: fit };
}
