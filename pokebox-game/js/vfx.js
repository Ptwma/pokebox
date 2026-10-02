// Pokebox — premium pack-opening VFX, real-time recreations of the three MyAssets reference videos.
//   electric  : 7.1 s  comic speed-ray burst → crackling thunder pack → streak/ray bursts → red-gold flow field → white wipe → ray collapse
//   candy     : 6.0 s  pack drops → sparkle burst → physics rain of glossy pearls, then gold rings, pile up → floor opens
//   legendary : 11.8 s fire aura → lightning X → pack burns → vortex → energy ball → star flash → white → UPGRADED pack → lightning
//               → orbit arcs → ray burst → blue sigil → cyan shockwave → dark
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

export const DURATION = { electric: 7.1, candy: 6.0, legendary: 11.8 };

const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const lerp = (a, b, k) => a + (b - a) * k;
const smooth = (a, b, x) => { const k = clamp((x - a) / (b - a)); return k * k * (3 - 2 * k); };
const env = (t, a, b, c, d) => smooth(a, b, t) * (1 - smooth(c, d, t));
const pulse = (t, a, len) => (t >= a && t < a + len ? 1 - (t - a) / len : 0);
const oBack = (k, s = 1.6) => 1 + (s + 1) * Math.pow(k - 1, 3) + s * Math.pow(k - 1, 2);
const o3 = k => 1 - Math.pow(1 - k, 3);
function rng(seed) { let s = seed >>> 0; return () => ((s = (Math.imul(s, 1664525) + 1013904223) >>> 0) / 4294967296); }
const CK = .55, C = (r, g, b) => new THREE.Vector3(r * CK, g * CK, b * CK);

/* ------------------------------------------------------------------ GLSL */
const NOISE = /* glsl */`
float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 p){ vec2 i = floor(p), f = fract(p); vec2 u = f*f*(3.-2.*f);
  return mix(mix(hash(i), hash(i+vec2(1,0)), u.x), mix(hash(i+vec2(0,1)), hash(i+vec2(1,1)), u.x), u.y); }
float fbm(vec2 p){ float v = 0., a = .5; for (int i = 0; i < 5; i++){ v += a*noise(p); p = p*2.03 + vec2(1.7, 9.2); a *= .5; } return v; }
`;
const VERT = /* glsl */`
uniform float uAspect, uHalfH; uniform vec2 uCenter;
varying vec2 vP; varying vec2 vUv;
void main(){
  vUv = uv;
#ifdef SCREEN
  gl_Position = vec4(position.xy, BACK, 1.);
  vP = position.xy * vec2(uAspect, 1.) * uHalfH - uCenter;
#else
  vP = position.xy;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.);
#endif
}`;
const HEAD = `uniform float uTime, uAlpha; varying vec2 vP; varying vec2 vUv;\n` + NOISE;

const FRAG = {
  // comic speed rays / starburst (thick hard-edged rays, white core, coloured rim)
  rays: `uniform float uCount, uWidth, uR0, uR1, uSpin, uSeed, uDensity, uInvert; uniform vec3 uColA, uColB;
  void main(){
    float r = length(vP), a = atan(vP.y, vP.x) + uSpin;
    float k = (a / 6.2831853 + .5) * uCount, id = floor(k), f = fract(k) - .5;
    float h1 = hash(vec2(id, uSeed)), h2 = hash(vec2(id + 17.3, uSeed)), h3 = hash(vec2(id + 3.1, uSeed + 5.));
    float w = uWidth * (.35 + h1 * .9) * clamp((r + .25) / 2.2, .12, 1.);
    float body = smoothstep(w, w * .82, abs(f)) * step(h2, uDensity);
    float core = smoothstep(w * .55, w * .25, abs(f));
    float rs = uR0 * (.55 + .9 * h3), re = uR1 * (.7 + .6 * h1);
    float m = body * smoothstep(rs, rs + .12, r) * (1. - smoothstep(re, re + .25, r));
    if (uInvert > .5) {
      vec3 bg = vec3(1.6);
      vec3 ray = mix(uColB, vec3(.02, .015, 0.), smoothstep(w * .92, w * .62, abs(f)));
      gl_FragColor = vec4(mix(bg, ray, m), uAlpha);
    } else {
      vec3 col = mix(uColB, uColA, core);
      gl_FragColor = vec4(col, m * uAlpha);
    }
  }`,
  // hyperspace streaks flying outward from the centre
  streaks: `uniform float uSpeed, uDensity, uLen; uniform vec3 uColA, uColB;
  float layer(vec2 p, float cells, float seed){
    float r = length(p), a = atan(p.y, p.x);
    float k = (a / 6.2831853 + .5) * cells, id = floor(k), f = fract(k) - .5;
    float h = hash(vec2(id, seed)); if (h > uDensity) return 0.;
    float pos = fract(h * 13.7 + uTime * uSpeed * (.5 + h));
    float R0 = .4 + pos * pos * 9., L = (.2 + pos * 2.2) * uLen;
    float along = smoothstep(R0, R0 + .08, r) * (1. - smoothstep(R0 + L * .5, R0 + L, r));
    float wf = (.012 + pos * .03) / max(r, .15) * cells / 6.2831853;
    return along * smoothstep(wf, 0., abs(f)) * (.35 + pos);
  }
  void main(){
    float a = layer(vP, 70., 1.) + layer(vP, 110., 2.) * .8 + layer(vP, 170., 3.) * .6;
    float h = hash(floor(vP * 3.));
    gl_FragColor = vec4(mix(uColA, uColB, h), clamp(a, 0., 1.5) * uAlpha);
  }`,
  // flowing energy threads (domain-warped fbm contour lines) + smoke haze
  flow: `uniform vec3 uColA, uColB; uniform float uFreq, uScale, uHaze;
  void main(){
    vec2 p = vP * uScale * vec2(.55, 1.25); float t = uTime * .22;
    vec2 q = vec2(fbm(p + vec2(0., t)), fbm(p + vec2(5.2, 1.3) - t * .6));
    float n = fbm(p * 1.3 + 2.4 * q + vec2(t * .7, -t * .35));
    float fr = abs(fract(n * uFreq) - .5), fr2 = abs(fract(n * uFreq * 2.7 + .3) - .5);
    float l = smoothstep(.44, .495, fr) + smoothstep(.46, .5, fr2) * .6;
    float mask = smoothstep(.42, .72, fbm(p * .8 + q * 1.8 + 3.));
    float haze = smoothstep(.45, .95, fbm(p * .55 - q + t)) * uHaze;
    vec3 col = uColA * l * mask * 1.3 + uColB * haze * .6;
    gl_FragColor = vec4(col, uAlpha);
  }`,
  // spiral energy vortex
  vortex: `uniform vec3 uColA, uColB; uniform float uArms, uTwist, uR0, uR1;
  void main(){
    float r = length(vP), a = atan(vP.y, vP.x);
    float n = fbm(vec2(a * 2., r * 1.5 - uTime * 2.)), n2 = noise(vP * 9. + uTime * 4.);
    float s = sin(a * uArms - log(r + .05) * uTwist + uTime * 7. + (n - .5) * .8);
    float arm = smoothstep(.95, .998, s) * (.6 + n) + smoothstep(.97, 1., sin(a * uArms * 2. - log(r + .05) * uTwist * 1.3 + uTime * 5. + n2)) * .6;
    float spark = 0.;
    float m = smoothstep(uR0, uR0 + .3, r) * (1. - smoothstep(uR1 - .6, uR1, r));
    vec3 col = mix(uColB, uColA, arm) * (arm * 1.4 + spark * .5);
    gl_FragColor = vec4(col, m * uAlpha);
  }`,
  // plasma ball (uMode 0) or shockwave ring (uMode 1)
  plasma: `uniform vec3 uColA, uColB; uniform float uR, uThick, uHole, uMode, uDark;
  void main(){
    float r = length(vP);
    float n = fbm(vP * 1.6 + vec2(uTime * .7, -uTime * .5));
    float e = fbm(vP * 5. - vec2(uTime * 1.8, uTime * 1.1));
    float veins = smoothstep(.41, .49, abs(fract(fbm(vP * 2.2 + n * 2. + uTime * .4) * 6.) - .5));
    vec3 col; float a;
    if (uMode < .5) {
      float d = uR - r + (n - .5) * uR * .35;
      float body = smoothstep(0., .1 * uR + .02, d);
      float rim = exp(-abs(d) * 9.) * .7;
      float hole = smoothstep(uHole * .7, uHole, r);
      float I = body * (.1 + 3.8 * pow(e, 3.) + veins * 1.6 + exp(-r * 2.5 / max(uR, .3)) * .9);
      col = (mix(uColB, uColA, clamp(I * .6, 0., 1.)) * I + uColA * rim * 1.1) * hole;
      a = clamp(body + rim, 0., 1.) * uAlpha;
    } else {
      float d = abs(r - uR + (n - .5) * .6);
      float body = exp(-d / uThick) * (.25 + 1.6 * pow(e, 2.)) + veins * exp(-d / (uThick * 2.5)) * .8;
      float fog = uDark * smoothstep(uR, 0., r) * pow(fbm(vP * 1.2 + uTime), 2.) * .6;
      col = mix(uColB, uColA, clamp(body, 0., 1.)) * body * 1.6 + uColB * fog * .5 + uColA * veins * fog * 1.1;
      a = clamp(body + fog, 0., 1.) * uAlpha;
    }
    gl_FragColor = vec4(col, a);
  }`,
  // anamorphic star flare
  flare: `uniform vec3 uColA;
  void main(){
    vec2 p = vP; float c = exp(-length(p) * 2.6) * 2.5;
    float h = exp(-abs(p.y) * 30.) * exp(-abs(p.x) * .45);
    float v = exp(-abs(p.x) * 30.) * exp(-abs(p.y) * .9);
    vec2 d = mat2(.707, -.707, .707, .707) * p;
    float x = (exp(-abs(d.y) * 40.) * exp(-abs(d.x) * 1.4) + exp(-abs(d.x) * 40.) * exp(-abs(d.y) * 1.4)) * .6;
    gl_FragColor = vec4(uColA * (c + h + v + x), uAlpha);
  }`,
  // solid flash / jagged diagonal wipe
  flash: `uniform vec3 uColA; uniform float uWipe; uniform vec2 uDir;
  void main(){
    float a = uAlpha;
    if (uWipe > -50.) { float s = dot(vP, normalize(uDir)) + (noise(vP * 2.5) - .5) * .5; a *= 1. - smoothstep(uWipe - .03, uWipe + .03, s); }
    gl_FragColor = vec4(uColA, a);
  }`,
  // glow / fire aura around the pack (world plane behind the pack, vP in pack-local units)
  aura: `uniform vec2 uHalf; uniform float uGlow, uFire; uniform vec3 uColA, uColB, uFireA, uFireB;
  float sdBox(vec2 p, vec2 b, float r){ vec2 q = abs(p) - b + r; return length(max(q, 0.)) + min(max(q.x, q.y), 0.) - r; }
  void main(){
    float d = sdBox(vP, uHalf, .1);
    float glow = uGlow * (exp(-max(d, 0.) * 16.) * 1.3 + exp(-max(d, 0.) * 4.) * .35) * smoothstep(-.03, .0, d);
    vec2 fp = vP * vec2(1.9, 1.3);
    float f1 = fbm(fp * 1.7 - vec2(0., uTime * 2.4)), f2 = fbm(fp * 3.8 - vec2(uTime * .3, uTime * 3.4));
    float up = clamp(vP.y / uHalf.y * .5 + .5, 0., 1.);
    float heat = (f1 * .95 + f2 * .45) - max(d, 0.) * (2.1 - 1.1 * up) - .22;
    float fire = uFire * smoothstep(0., .45, heat) * step(-.02, d);
    vec3 col = uColA * glow + mix(uFireB, uFireA, smoothstep(.2, .7, heat)) * fire * 1.6;
    gl_FragColor = vec4(col, clamp(glow + fire, 0., 1.) * uAlpha);
  }`,
  // falling motion smear (vertical streaks)
  smear: `uniform vec3 uColA;
  void main(){
    float s = noise(vec2(vP.x * 14., 0.)) * noise(vec2(vP.x * 37., 3.));
    float fade = smoothstep(-2.2, 0., vP.y) * (1. - smoothstep(0., 2.2, vP.y));
    gl_FragColor = vec4(uColA * s * 2., s * fade * uAlpha);
  }`,
};

/* ------------------------------------------------------------------ lightning ribbons */
function boltPath(ax, ay, bx, by, disp, R, n = 32) {
  const P = new Array(n + 1); P[0] = [ax, ay]; P[n] = [bx, by];
  for (let step = n; step > 1; step >>= 1) {
    for (let i = 0; i < n; i += step) {
      const a = P[i], b = P[i + step], m = i + step / 2, dx = b[0] - a[0], dy = b[1] - a[1], len = Math.hypot(dx, dy) || 1;
      const o = (R() - .5) * disp * len; P[m] = [(a[0] + b[0]) / 2 - dy / len * o, (a[1] + b[1]) / 2 + dx / len * o];
    }
  }
  return P;
}
class Lightning {
  constructor(maxPts = 6000, depthTest = false) {
    this.max = maxPts;
    this.pos = new Float32Array(maxPts * 2 * 3); this.v = new Float32Array(maxPts * 2); this.col = new Float32Array(maxPts * 2 * 4);
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(this.pos, 3).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute('aV', new THREE.BufferAttribute(this.v, 1).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute('aCol', new THREE.BufferAttribute(this.col, 4).setUsage(THREE.DynamicDrawUsage));
    const idx = new Uint32Array(maxPts * 6); g.setIndex(new THREE.BufferAttribute(idx, 1).setUsage(THREE.DynamicDrawUsage)); this.idx = idx;
    this.geo = g;
    this.mesh = new THREE.Mesh(g, new THREE.ShaderMaterial({
      vertexShader: `attribute float aV; attribute vec4 aCol; varying float vV; varying vec4 vC; void main(){ vV = aV; vC = aCol; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.); }`,
      fragmentShader: `varying float vV; varying vec4 vC; void main(){ float d = abs(vV); float core = smoothstep(.34, 0., d); float glow = pow(1. - d, 2.2);
        gl_FragColor = vec4(mix(vC.rgb * .6 * glow, vC.rgb * .45 + vec3(.75), core), (glow * .8 + core) * vC.a); }`,
      transparent: true, depthWrite: false, depthTest, blending: THREE.AdditiveBlending, side: THREE.DoubleSide,
    }));
    this.mesh.frustumCulled = false; this.n = 0; this.ni = 0;
  }
  begin() { this.n = 0; this.ni = 0; }
  // add a polyline ribbon; w = half-width (world), col = [r,g,b] (HDR), a = alpha
  line(P, w, col, a = 1, z = 0, taper = true) {
    const n = P.length; if (this.n + n > this.max) return;
    const base = this.n;
    for (let i = 0; i < n; i++) {
      const p = P[i], q = P[Math.min(n - 1, i + 1)], o = P[Math.max(0, i - 1)];
      let dx = q[0] - o[0], dy = q[1] - o[1]; const l = Math.hypot(dx, dy) || 1; dx /= l; dy /= l;
      const tw = taper ? Math.pow(Math.sin(Math.PI * (i / (n - 1)) * .98 + .01), .35) : 1, ww = w * tw;
      const k = (base + i) * 2;
      this.pos.set([p[0] - dy * ww, p[1] + dx * ww, z, p[0] + dy * ww, p[1] - dx * ww, z], k * 3);
      this.v[k] = -1; this.v[k + 1] = 1;
      this.col.set([col[0], col[1], col[2], a, col[0], col[1], col[2], a], k * 4);
      if (i < n - 1) { const j = this.ni; this.idx.set([k, k + 1, k + 2, k + 1, k + 3, k + 2], j); this.ni += 6; }
    }
    this.n += n;
  }
  bolt(ax, ay, bx, by, o = {}) {
    const R = o.R || Math.random, P = boltPath(ax, ay, bx, by, o.disp ?? .35, R, o.seg || 32);
    this.line(P, o.w ?? .04, o.col || [2, 1.6, .4], o.a ?? 1, o.z ?? 0);
    for (let b = 0; b < (o.branches || 0); b++) {
      const i = 4 + Math.floor(R() * (P.length - 8)), s = P[i], ang = Math.atan2(by - ay, bx - ax) + (R() - .5) * 1.8, L = Math.hypot(bx - ax, by - ay) * (.12 + R() * .25);
      this.line(boltPath(s[0], s[1], s[0] + Math.cos(ang) * L, s[1] + Math.sin(ang) * L, .5, R, 8), (o.w ?? .04) * .5, o.col || [2, 1.6, .4], (o.a ?? 1) * .8, o.z ?? 0);
    }
  }
  end() {
    this.geo.setDrawRange(0, this.ni);
    for (const k of ['position', 'aV', 'aCol']) this.geo.attributes[k].needsUpdate = true;
    this.geo.index.needsUpdate = true;
  }
}

/* ------------------------------------------------------------------ particles (analytic bursts) */
class Sparks {
  constructor(max = 900) {
    this.max = max; const g = new THREE.BufferGeometry();
    this.p = new Float32Array(max * 3); this.c = new Float32Array(max * 4); this.s = new Float32Array(max);
    g.setAttribute('position', new THREE.BufferAttribute(this.p, 3).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute('aCol', new THREE.BufferAttribute(this.c, 4).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute('aSize', new THREE.BufferAttribute(this.s, 1).setUsage(THREE.DynamicDrawUsage));
    this.mat = new THREE.ShaderMaterial({
      uniforms: { uPR: { value: 1 } },
      vertexShader: `attribute vec4 aCol; attribute float aSize; uniform float uPR; varying vec4 vC;
        void main(){ vC = aCol; vec4 mv = modelViewMatrix * vec4(position, 1.); gl_PointSize = aSize * uPR * 900. / -mv.z; gl_Position = projectionMatrix * mv; }`,
      fragmentShader: `varying vec4 vC; void main(){ vec2 p = gl_PointCoord - .5; float d = length(p);
        float star = exp(-abs(p.x) * 40.) * exp(-abs(p.y) * 5.) + exp(-abs(p.y) * 40.) * exp(-abs(p.x) * 5.) + exp(-d * 14.) * 1.4;
        gl_FragColor = vec4(vC.rgb * star, clamp(star, 0., 1.) * vC.a); }`,
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    });
    this.pts = new THREE.Points(g, this.mat); this.pts.frustumCulled = false; this.geo = g; this.bursts = []; this.n = 0;
  }
  clear() { this.bursts = []; }
  // o: {t0, n, x, y, z, speed, life, cols:[[r,g,b]], size, spread (z), drag, grav, seed, shape:'radial'|'rect', hw, hh}
  add(o) { this.bursts.push(Object.assign({ n: 60, x: 0, y: 0, z: .3, speed: 3, life: 1, size: .12, spread: .6, drag: 2.2, grav: 0, seed: 1 }, o)); }
  update(t) {
    let n = 0;
    for (const b of this.bursts) {
      const dt = t - b.t0; if (dt < 0 || dt > b.life + .6) continue;
      const R = rng(b.seed * 9973);
      for (let i = 0; i < b.n && n < this.max; i++) {
        const ang = R() * Math.PI * 2, sp = b.speed * (.3 + R() * .9), life = b.life * (.5 + R() * .6), z = (R() - .5) * b.spread, tw = R() * 6.28, col = b.cols[Math.floor(R() * b.cols.length)];
        let ox = 0, oy = 0; if (b.shape === 'rect') { const e = R() * 4, s = e % 1; [ox, oy] = e < 1 ? [(s - .5) * 2 * b.hw, b.hh] : e < 2 ? [b.hw, (s - .5) * 2 * b.hh] : e < 3 ? [(s - .5) * 2 * b.hw, -b.hh] : [-b.hw, (s - .5) * 2 * b.hh]; }
        const lt = dt / life; if (lt > 1 || dt < 0) continue;
        const d = (1 - Math.exp(-b.drag * dt)) / b.drag;
        this.p.set([b.x + ox + Math.cos(ang) * sp * d, b.y + oy + Math.sin(ang) * sp * d + b.grav * dt * dt * .5, b.z + z], n * 3);
        const fl = .6 + .4 * Math.sin(dt * 30 + tw);
        this.c.set([col[0], col[1], col[2], (1 - lt) * fl], n * 4); this.s[n] = b.size * (.5 + R()) * (1 - lt * .5); n++;
      }
    }
    this.geo.setDrawRange(0, n); this.n = n;
    for (const k of ['position', 'aCol', 'aSize']) this.geo.attributes[k].needsUpdate = true;
  }
}

/* ------------------------------------------------------------------ main */
export function createVfx(canvas, hooks = {}) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.25));
  renderer.outputColorSpace = THREE.SRGBColorSpace; renderer.toneMapping = THREE.NeutralToneMapping; renderer.toneMappingExposure = 1.0;
  renderer.setClearColor(0x000000, 1);
  const scene = new THREE.Scene(); scene.background = new THREE.Color(0x050505);
  const camera = new THREE.PerspectiveCamera(35, 16 / 9, .1, 100); camera.position.set(0, 0, 10);
  const HALF_H = 10 * Math.tan(THREE.MathUtils.degToRad(17.5));
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), .04).texture; scene.environmentIntensity = .6;
  const key = new THREE.DirectionalLight(0xffffff, .95); key.position.set(-3, 5, 6); scene.add(key);
  const fill = new THREE.DirectionalLight(0xffe0b0, .8); fill.position.set(4, -2, 5); scene.add(fill);
  const amb = new THREE.AmbientLight(0xffffff, .12); scene.add(amb);

  const composer = new EffectComposer(renderer, new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, samples: 2 }));
  composer.addPass(new RenderPass(scene, camera));
  const bloom = new UnrealBloomPass(new THREE.Vector2(1, 1), .35, 0, 1.25); composer.addPass(bloom); bloom.compositeMaterial.uniforms.bloomFactors.value = [1, .55, .22, .06, .01];
  composer.addPass(new OutputPass());

  /* layer factory */
  const layers = [];
  function layer(kind, uniforms = {}, { screen = true, order = 0, additive = true, size = 1, z = 0, parent = scene, depthTest = false } = {}) {
    const u = { uTime: { value: 0 }, uAlpha: { value: 0 }, uAspect: { value: 16 / 9 }, uHalfH: { value: HALF_H }, uCenter: { value: new THREE.Vector2() } };
    for (const k in uniforms) u[k] = { value: uniforms[k] };
    const mat = new THREE.ShaderMaterial({
      uniforms: u, vertexShader: VERT, fragmentShader: HEAD + FRAG[kind], defines: screen ? { SCREEN: 1, BACK: order < 0 ? '0.9999' : '0.' } : {},
      transparent: true, depthWrite: false, depthTest: depthTest || (screen && order < 0), blending: additive ? THREE.AdditiveBlending : THREE.NormalBlending,
    });
    const m = new THREE.Mesh(new THREE.PlaneGeometry(screen ? 2 : size, screen ? 2 : size), mat);
    m.frustumCulled = false; m.renderOrder = order; m.position.z = z; m.visible = false; parent.add(m);
    const L = { m, u, screen, set(a, extra) { u.uAlpha.value = a; m.visible = a > .002; if (extra) for (const k in extra) { const v = extra[k]; if (v && v.isVector3 || v && v.isVector2) u[k].value.copy(v); else u[k].value = v; } return L; } };
    layers.push(L); return L;
  }

  /* pack */
  let pack = null, packW = 2.9, packH = 4.06;
  const packU = { uBurn: { value: 0 }, uGlint: { value: -2 }, uEmis: { value: 0 }, uEmisCol: { value: new THREE.Color(1, .8, .3) } };
  function packMaterial(tex, back = false) {
    const m = new THREE.MeshPhysicalMaterial({ map: tex, metalness: .3, roughness: .32, clearcoat: .35, clearcoatRoughness: .3, envMapIntensity: .42, color: back ? 0x999999 : 0xffffff });
    m.onBeforeCompile = sh => {
      Object.assign(sh.uniforms, packU);
      sh.fragmentShader = 'uniform float uBurn, uGlint, uEmis; uniform vec3 uEmisCol;\n' + NOISE + sh.fragmentShader
        .replace('#include <map_fragment>', `#include <map_fragment>
          float bn = fbm(vMapUv * vec2(4., 5.6) + 3.) * .8 + fbm(vMapUv * 18.) * .2;
          float burnt = smoothstep(bn - .02, bn + .02, uBurn * 1.15);
          float edge = uBurn > 0. ? exp(-abs(bn - uBurn * 1.15) * 28.) : 0.;
          diffuseColor.rgb = mix(diffuseColor.rgb, vec3(.05, .03, .025) * (.6 + fbm(vMapUv * 30.)), burnt * .92);`)
        .replace('#include <emissivemap_fragment>', `#include <emissivemap_fragment>
          totalEmissiveRadiance += vec3(3.2, 1.3, .25) * edge * 1.4 + vec3(1.2, .35, .05) * burnt * pow(fbm(vMapUv * 12. + uBurn * 3.), 3.) * 1.1;
          float gl = exp(-pow((vMapUv.x + (1. - vMapUv.y) * .6 - uGlint) * 9., 2.));
          totalEmissiveRadiance += vec3(2.) * gl * .7 + uEmisCol * uEmis;`);
    };
    return m;
  }
  function pillow(w, h, back = false) {
    const g = new THREE.PlaneGeometry(w, h, 40, 56), p = g.attributes.position;
    for (let i = 0; i < p.count; i++) {
      const x = p.getX(i) / (w / 2), y = p.getY(i) / (h / 2);
      const crimpY = 1 - smooth(.9, .96, Math.abs(y));
      let z = .2 * (1 - Math.pow(Math.abs(x), 3.5)) * (1 - Math.pow(Math.abs(y), 6)) * crimpY;
      z += Math.sin(x * 9 + y * 5) * .006 + Math.sin(y * 23) * .004 * crimpY;
      p.setZ(i, back ? z : z);
    }
    g.computeVertexNormals(); return g;
  }
  const auraHalf = new THREE.Vector2();
  let aura, face;
  function buildPack(tex) {
    if (pack) { scene.remove(pack); pack.traverse(o => { o.geometry?.dispose(); if (o.material && o.material !== aura?.m.material) o.material.dispose?.(); }); }
    const ar = tex.image.width / tex.image.height; packH = 4.1; packW = packH * ar;
    pack = new THREE.Group();
    const front = new THREE.Mesh(pillow(packW, packH), packMaterial(tex));
    const back = new THREE.Mesh(pillow(packW, packH, true), packMaterial(tex, true)); back.rotation.y = Math.PI;
    pack.add(front, back); scene.add(pack); face = front;
    auraHalf.set(packW / 2, packH / 2);
    aura = layer('aura', { uHalf: auraHalf, uGlow: 0, uFire: 0, uColA: C(2.4, 1.9, .6), uColB: C(1, 1, 1), uFireA: C(2.6, 2.1, .6), uFireB: C(1.4, .35, .05) }, { screen: false, size: 9, z: -.25, parent: pack, order: -1, depthTest: true });
    return pack;
  }

  /* shared effect instances */
  const L = {
    flowBg: layer('flow', { uColA: C(2.2, 1.35, .35), uColB: C(.9, .05, .02), uFreq: 5, uScale: .38, uHaze: .9 }, { order: -20 }),
    streaks: layer('streaks', { uSpeed: .5, uDensity: .55, uLen: 1, uColA: C(2.5, .9, .2), uColB: C(2.4, 1.6, .5) }, { order: -15 }),
    raysBack: layer('rays', { uCount: 22, uWidth: .22, uR0: .4, uR1: 12, uSpin: 0, uSeed: 1, uDensity: 1, uInvert: 0, uColA: C(3, 3, 2.8), uColB: C(2.6, 1.2, .2) }, { order: -12 }),
    vortex: layer('vortex', { uColA: C(3, 2.6, 1.4), uColB: C(2.2, 1.4, .2), uArms: 3, uTwist: 3, uR0: .6, uR1: 5.5 }, { order: -11 }),
    raysFront: layer('rays', { uCount: 14, uWidth: .3, uR0: .2, uR1: 14, uSpin: 0, uSeed: 4, uDensity: 1, uInvert: 0, uColA: C(3, 3, 3), uColB: C(2.8, 2, .3) }, { order: 20, additive: false }),
    raysInv: layer('rays', { uCount: 9, uWidth: .2, uR0: .15, uR1: 14, uSpin: .3, uSeed: 9, uDensity: .9, uInvert: 1, uColA: C(0, 0, 0), uColB: C(2.4, 1.6, .1) }, { order: 30, additive: false }),
    ball: layer('plasma', { uColA: C(3.2, 2.8, 1.2), uColB: C(2.4, 1.5, .2), uR: 1, uThick: .2, uHole: 0, uMode: 0, uDark: 0 }, { order: 15 }),
    ring: layer('plasma', { uColA: C(1.2, 2.8, 3.2), uColB: C(.05, .35, 1.2), uR: 1, uThick: .25, uHole: 0, uMode: 1, uDark: 0 }, { order: 16 }),
    flare: layer('flare', { uColA: C(1.6, 2.2, 3.4) }, { order: 25 }),
    flash: layer('flash', { uColA: C(1.5, 1.5, 1.5), uWipe: -99, uDir: new THREE.Vector2(1, 1) }, { order: 40, additive: false }),
    smear: layer('smear', { uColA: C(2, .4, 1.2) }, { screen: false, size: 5, z: -.1, order: -2 }),
    faceRays: layer('rays', { uCount: 9, uWidth: .42, uR0: .0, uR1: .9, uSpin: 0, uSeed: 3, uDensity: 1, uInvert: 0, uColA: C(3, 3, 3), uColB: C(3, 3, 3) }, { screen: false, size: 4, z: .4, order: 10 }),
    faceRing: layer('plasma', { uColA: C(3.2, 2.4, 2.4), uColB: C(2.4, .8, .8), uR: .3, uThick: .06, uHole: 0, uMode: 1, uDark: 0 }, { screen: false, size: 3, z: .3, order: 10 }),
  };
  const bolts = new Lightning(); bolts.mesh.renderOrder = 12; scene.add(bolts.mesh);
  const boltsBack = new Lightning(6000, true); boltsBack.mesh.renderOrder = -8; scene.add(boltsBack.mesh);
  const sparks = new Sparks(); sparks.pts.renderOrder = 14; scene.add(sparks.pts);

  /* candy physics (instanced) */
  const SPH_R = .4, TOR_R = .4, NS = 340, NT = 340, BAKE_HZ = 60, BAKE_T = 6.0;
  const sphMesh = new THREE.InstancedMesh(new THREE.SphereGeometry(SPH_R, 28, 18), new THREE.MeshPhysicalMaterial({ color: 0xe0004a, roughness: .28, metalness: 0, clearcoat: 1, clearcoatRoughness: .04, envMapIntensity: .55 }), NS);
  const torMesh = new THREE.InstancedMesh(new THREE.TorusGeometry(TOR_R * .72, TOR_R * .3, 18, 40), new THREE.MeshStandardMaterial({ color: 0xe0a020, metalness: 1, roughness: .2, envMapIntensity: .95 }), NT);
  sphMesh.visible = torMesh.visible = false; sphMesh.frustumCulled = torMesh.frustumCulled = false; scene.add(sphMesh, torMesh);
  let phys = null;
  function physInit(seed) {
    const R = rng(seed), aspect = camera.aspect, bodies = [];
    const XW = HALF_H * aspect + .6;
    for (let i = 0; i < NS; i++) bodies.push({ k: 0, i, r: SPH_R, t0: .85 + Math.pow(R(), 1.1) * 2.0, x0: (R() * 2 - 1) * (XW - .4), z0: -1.2 + R() * 3.6, vy0: -2 - R() * 3 });
    for (let i = 0; i < NT; i++) bodies.push({ k: 1, i, r: TOR_R, t0: 2.85 + Math.pow(R(), .9) * 2.15, x0: (R() * 2 - 1) * (XW - .4), z0: -1.2 + R() * 3.6, vy0: -3 - R() * 3, ax: R() - .5, ay: R() - .5, az: R() - .5, rs: R() });
    for (const b of bodies) { b.on = false; b.p = new THREE.Vector3(); b.v = new THREE.Vector3(); b.q = new THREE.Quaternion().setFromEuler(new THREE.Euler(R() * 6, R() * 6, R() * 6)); b.w = new THREE.Vector3((R() - .5) * 8, (R() - .5) * 8, (R() - .5) * 8); }
    phys = { bodies, t: 0, XW, floor: -HALF_H - .25, floorOn: true, seed };
  }
  const _q = new THREE.Quaternion(), _m = new THREE.Matrix4(), _s = new THREE.Vector3(1, 1, 1), _z = new THREE.Vector3(0, 0, 0), _ax = new THREE.Vector3();
  function physStep(dt) {
    const P = phys, t = P.t + dt; P.t = t; const G = -21;
    if (t > 5.08) P.floorOn = false;
    const act = [];
    for (const b of P.bodies) {
      if (!b.on && t >= b.t0) { b.on = true; const top = HALF_H * (10 - b.z0) / 10 + .6; b.p.set(b.x0, top + (t - b.t0) * -b.vy0, b.z0); b.v.set(0, b.vy0, 0); }
      if (!b.on) continue; act.push(b);
      b.v.y += G * dt; b.v.multiplyScalar(.998); b.p.addScaledVector(b.v, dt);
      if (b.k === 1) { const wl = b.w.length(); if (wl > 1e-4) { _ax.copy(b.w).divideScalar(wl); _q.setFromAxisAngle(_ax, wl * dt); b.q.premultiply(_q); } }
    }
    // spatial hash collisions
    const cell = .82, grid = new Map(), key = (x, y, z) => ((x + 512) * 1024 + (y + 512)) * 1024 + (z + 512);
    for (const b of act) { const k = key(Math.floor(b.p.x / cell), Math.floor(b.p.y / cell), Math.floor(b.p.z / cell)); let a = grid.get(k); if (!a) grid.set(k, a = []); a.push(b); }
    for (let it = 0; it < 2; it++) for (const b of act) {
      const cx = Math.floor(b.p.x / cell), cy = Math.floor(b.p.y / cell), cz = Math.floor(b.p.z / cell);
      for (let dx = -1; dx <= 1; dx++) for (let dy = -1; dy <= 1; dy++) for (let dz = -1; dz <= 1; dz++) {
        const a = grid.get(key(cx + dx, cy + dy, cz + dz)); if (!a) continue;
        for (const o of a) {
          if (o === b || o.i + o.k * 1000 < b.i + b.k * 1000) continue;
          const nx = o.p.x - b.p.x, ny = o.p.y - b.p.y, nz = o.p.z - b.p.z, d2 = nx * nx + ny * ny + nz * nz, rr = b.r + o.r;
          if (d2 >= rr * rr || d2 < 1e-8) continue;
          const d = Math.sqrt(d2), pen = (rr - d) * .5, ux = nx / d, uy = ny / d, uz = nz / d;
          b.p.x -= ux * pen; b.p.y -= uy * pen; b.p.z -= uz * pen; o.p.x += ux * pen; o.p.y += uy * pen; o.p.z += uz * pen;
          const vn = (o.v.x - b.v.x) * ux + (o.v.y - b.v.y) * uy + (o.v.z - b.v.z) * uz;
          if (vn < 0) { const j = -(1 + .25) * vn * .5; b.v.x -= ux * j; b.v.y -= uy * j; b.v.z -= uz * j; o.v.x += ux * j; o.v.y += uy * j; o.v.z += uz * j; b.w.multiplyScalar(.97); o.w.multiplyScalar(.97); }
        }
      }
    }
    const pw = packW / 2, ph = packH / 2, py = candyPackY(t);
    for (const b of act) {
      if (P.floorOn && b.p.y - b.r < P.floor) { b.p.y = P.floor + b.r; if (b.v.y < 0) b.v.y *= -.25; b.v.x *= .96; b.v.z *= .96; b.w.multiplyScalar(.9); }
      if (Math.abs(b.p.x) > P.XW - b.r) { b.p.x = Math.sign(b.p.x) * (P.XW - b.r); b.v.x *= -.3; }
      if (b.p.z < -1.6 + b.r) { b.p.z = -1.6 + b.r; b.v.z *= -.3; } if (b.p.z > 2.5 - b.r) { b.p.z = 2.5 - b.r; b.v.z *= -.3; }
      if (P.floorOn) { // pack slab collider
        const cx = clamp(b.p.x, -pw, pw), cy = clamp(b.p.y, py - ph, py + ph), cz = clamp(b.p.z, -.22, .22);
        const dx = b.p.x - cx, dy = b.p.y - cy, dz = b.p.z - cz, d2 = dx * dx + dy * dy + dz * dz;
        if (d2 < b.r * b.r && d2 > 1e-8) { const d = Math.sqrt(d2), k = (b.r - d) / d; b.p.x += dx * k; b.p.y += dy * k; b.p.z += dz * k; const vn = (b.v.x * dx + b.v.y * dy + b.v.z * dz) / d; if (vn < 0) { b.v.x -= dx / d * vn * 1.3; b.v.y -= dy / d * vn * 1.3; b.v.z -= dz / d * vn * 1.3; } }
      }
    }
  }
  // the whole 6 s simulation is baked once before the effect starts (in small chunks, so the page never freezes),
  // then played back by interpolation — zero physics cost while it is on screen, identical result every time
  let baked = null;
  async function physBake(seed) {
    physInit(seed); const N = phys.bodies.length, F = Math.ceil(BAKE_T * BAKE_HZ) + 1, sub = 2, dt = 1 / (BAKE_HZ * sub);
    const P = new Float32Array(F * N * 3), Q = new Float32Array(F * NT * 4);
    for (let f = 0; f < F; f++) {
      if (f) for (let k = 0; k < sub; k++) physStep(dt);
      for (let j = 0; j < N; j++) { const b = phys.bodies[j], o = (f * N + j) * 3; if (b.on && b.p.y > -HALF_H - 4) { P[o] = b.p.x; P[o + 1] = b.p.y; P[o + 2] = b.p.z; } else P[o + 1] = -999;
        if (b.k) { const q = (f * NT + b.i) * 4; Q[q] = b.q.x; Q[q + 1] = b.q.y; Q[q + 2] = b.q.z; Q[q + 3] = b.q.w; } }
      if (f % 20 === 19) await new Promise(r => setTimeout(r, 0));
    }
    baked = { P, Q, F, N };
  }
  const _p = new THREE.Vector3(), _qa = new THREE.Quaternion(), _qb = new THREE.Quaternion(), _zero = new THREE.Vector3(0, 0, 0);
  function physTo(t) {
    if (!baked) return; const { P, Q, F, N } = baked, x = clamp(t * BAKE_HZ, 0, F - 1), f0 = Math.floor(x), f1 = Math.min(F - 1, f0 + 1), a = x - f0;
    for (let j = 0; j < N; j++) {
      const b = phys.bodies[j], M = b.k ? torMesh : sphMesh, o0 = (f0 * N + j) * 3, o1 = (f1 * N + j) * 3;
      if (P[o0 + 1] < -900 || P[o1 + 1] < -900) { _m.compose(_zero, _q.identity(), _zero); M.setMatrixAt(b.i, _m); continue; }
      _p.set(lerp(P[o0], P[o1], a), lerp(P[o0 + 1], P[o1 + 1], a), lerp(P[o0 + 2], P[o1 + 2], a));
      if (b.k) { const q0 = (f0 * NT + b.i) * 4, q1 = (f1 * NT + b.i) * 4; _qa.set(Q[q0], Q[q0 + 1], Q[q0 + 2], Q[q0 + 3]); _qb.set(Q[q1], Q[q1 + 1], Q[q1 + 2], Q[q1 + 3]); _qa.slerp(_qb, a); }
      _m.compose(_p, b.k ? _qa : _q.identity(), _s); M.setMatrixAt(b.i, _m);
    }
    sphMesh.instanceMatrix.needsUpdate = torMesh.instanceMatrix.needsUpdate = true;
  }
  function candyPackY(t) {
    let y = t < .3 ? lerp(5.5, 0, (t / .3) ** 2) : Math.abs(Math.sin((t - .3) * 14)) * .12 * Math.exp(-(t - .3) * 7);
    if (t > 5.08) y -= .5 * 21 * (t - 5.08) ** 2; return y;
  }

  /* ------------------------------------------------------------------ timelines */
  const TL = {};
  let cues = [], cueI = 0;
  const cue = (t, fn) => cues.push({ t, fn });
  let texA = null, texB = null;

  TL.electric = (t, R) => {
    const pos = new THREE.Vector3(), rot = new THREE.Euler();
    // pack pose
    const pop = clamp((t - .18) / .3);
    let s = t < .18 ? lerp(.18, .26, t / .18) : lerp(.26, 1, oBack(pop, 1.3));
    s *= 1 + pulse(t, 1.74, .22) * .06 + smooth(2.9, 5.5, t) * .34;
    rot.set(Math.sin(t * .9) * .06, Math.sin(t * 1.3 + .5) * .16, t < .2 ? (1 - t / .2) * 2.5 + Math.sin(t * 2) * .05 : Math.sin(t * 1.1) * .07 - .03);
    pos.set(Math.sin(t * .7) * .06, Math.sin(t * 1.4) * .05 + .05, 0);
    if (t > 6.1) { const k = smooth(6.1, 6.3, t); pos.x -= k * 2.2; pos.y += k * 1.6; }
    pack.visible = t < 6.32;
    // starburst ring around the tiny pack (0 - .2)
    L.raysBack.set(t < .2 ? 1 : 0, { uCount: 16, uWidth: .3, uR0: .55, uR1: .95, uSeed: 2, uDensity: 1, uColA: C(3, 3, 2.6), uColB: C(2.8, 1.3, .15), uSpin: t * 3 });
    // comic speed-ray burst (.2 - .55)
    if (t >= .2 && t < 6.4) L.raysFront.set(env(t, .2, .23, .38, .55), { uCount: 18, uWidth: .34, uR0: .9 - smooth(.2, .5, t) * .2, uR1: 14, uSeed: 4, uDensity: .95, uColA: C(2, 2, 2), uColB: C(1.9, .8, .05), uSpin: 0 });
    // speed rays second burst (2.4 - 2.65) thin, yellow; then big comic shard burst 2.7 - 2.95
    if (t >= 2.35 && t < 2.7) L.raysFront.set(env(t, 2.35, 2.4, 2.58, 2.68), { uCount: 34, uWidth: .09, uR0: .6, uR1: 14, uSeed: 6, uDensity: .6, uColA: C(2, 2, 1.5), uColB: C(2, 1.3, .1) });
    if (t >= 2.7 && t < 3.05) L.raysFront.set(env(t, 2.7, 2.73, 2.9, 3.02), { uCount: 12, uWidth: .45, uR0: .3, uR1: 14, uSeed: 12, uDensity: 1, uColA: C(2, 2, 2), uColB: C(1.9, 1.4, .1) });
    // hyperspace red/yellow streaks (2.0 - 3.3)
    L.streaks.set(env(t, 1.95, 2.1, 2.9, 3.3) * 1.2, { uSpeed: .9, uDensity: .35, uLen: 1.6, uColA: C(3, .5, .3), uColB: C(3, 2.2, .6) });
    // red/gold flowing energy background (3.0 →)
    L.flowBg.set(env(t, 2.9, 3.4, 6.1, 6.25), { uColA: C(2.4, 1.3, .3), uColB: C(1.5, .08, .02), uFreq: 8, uScale: .34, uHaze: 1.1 + smooth(4, 6, t) * .8 });
    // pack aura: electric glow outline, brighter toward the end
    aura.set(pack.visible ? 1 : 0, { uGlow: .55 + smooth(5.2, 6, t) * 1.4 + pulse(t, 1.74, .3) * 1.5, uFire: 0, uColA: C(2.6, 2.2, .6) });
    // 'POW' splat on the pack face at 1.75
    L.faceRays.set(env(t, 1.72, 1.74, 1.86, 1.95), { uCount: 9, uWidth: .45, uR0: 0, uR1: .8, uSeed: 3 });
    // white wipe (6.1 - 6.35), inverted ray tunnel (6.3 - 6.62), then glowing rays collapse into the centre (6.6 - 7.0)
    L.flash.set(t >= 6.08 && t < 6.4 ? 1 : 0, { uColA: C(1.6, 1.6, 1.6), uWipe: lerp(-9, 5, smooth(6.08, 6.36, t)), uDir: new THREE.Vector2(-1, -1.3) });
    L.raysInv.set(t >= 6.4 && t < 6.62 ? 1 : 0, { uCount: 7, uWidth: .3 + smooth(6.4, 6.6, t) * .12, uR0: .1, uR1: 14, uSeed: 9, uDensity: .95, uColB: C(3, 2.2, .1), uSpin: .2 });
    if (t >= 6.6) L.raysFront.set(1 - smooth(6.85, 7.05, t), { uCount: 11, uWidth: .07, uR0: .2 + smooth(6.6, 6.95, t) * 0, uR1: lerp(9, .6, smooth(6.6, 6.98, t)), uSeed: 21, uDensity: .75, uColA: C(3, 3, 2.4), uColB: C(3, 2, .1) });
    // lightning
    const fr = Math.floor(t * 18), Rb = rng(1000 + fr);
    bolts.begin(); boltsBack.begin();
    if (pack.visible && t > .2) { // crackling outline
      const hw = packW / 2 * s, hh = packH / 2 * s, per = [[-hw, hh, hw, hh], [hw, hh, hw, -hh], [hw, -hh, -hw, -hh], [-hw, -hh, -hw, hh]];
      for (let i = 0; i < 12; i++) { const e = per[Math.floor(Rb() * 4)], a = Rb(), b = Math.min(1, a + .1 + Rb() * .25); bolts.bolt(pos.x + lerp(e[0], e[2], a), pos.y + lerp(e[1], e[3], a), pos.x + lerp(e[0], e[2], b), pos.y + lerp(e[1], e[3], b), { R: Rb, disp: .5, w: .022, col: [2.6, 2.2, .7], a: .9, z: .25, seg: 16 }); }
    }
    if (t > .55 && t < 1.25) { // arcs across the screen
      const k = env(t, .55, .6, 1.1, 1.25);
      for (let i = 0; i < 4; i++) { const a = Rb() * 6.28, r0 = 1.8 + Rb() * 1.5, r1 = 5 + Rb() * 3; boltsBack.bolt(Math.cos(a) * r0, Math.sin(a) * r0, Math.cos(a + (Rb() - .5)) * r1, Math.sin(a + (Rb() - .5)) * r1 * .7, { R: Rb, disp: .6, w: .05, col: [2.6, 2.1, .6], a: k, z: -.4, branches: 3 }); }
    }
    if (t > .9 && t < 1.6) for (let i = 0; i < 6; i++) { const x = (Rb() - .5) * 11, y = (Rb() - .5) * 6; boltsBack.bolt(x, y, x + (Rb() - .5) * 1.2, y + (Rb() - .5) * .8, { R: Rb, disp: .9, w: .012, col: [2, 2, 2], a: env(t, .9, 1, 1.4, 1.6) * .8, z: -.5, seg: 8 }); }
    if (t > 2.4 && t < 2.7) for (let i = 0; i < 3; i++) { const a = Rb() * 6.28; boltsBack.bolt(Math.cos(a) * 1.4, Math.sin(a) * 1.4, Math.cos(a) * 3.2, Math.sin(a) * 3.2, { R: Rb, disp: .6, w: .02, col: [.6, 2.6, 3], a: 1, z: .3, seg: 16 }); }
    // cyan-white slashes swooping around the pack (3.6 - 4.9)
    if (t > 3.6 && t < 4.95) {
      for (let j = 0; j < 2; j++) {
        const ph = (t - 3.6) * 2.4 + j * 3.1, P = [];
        for (let i = 0; i <= 20; i++) { const a = ph + i * .045; P.push([Math.cos(a) * (2.1 + j * .5), Math.sin(a * 1.3) * 2.6]); }
        bolts.line(P, .035, [1.4, 2.8, 3], env(t, 3.6, 3.7, 4.8, 4.95), .5, true);
      }
    }
    bolts.end(); boltsBack.end();
    // flecks
    return { pos, rot, s };
  };
  function electricCues() {
    cue(0, () => hooks.sfx?.('zap')); cue(.2, () => hooks.sfx?.('boom', .6)); cue(.6, () => hooks.sfx?.('zap')); cue(1.74, () => hooks.sfx?.('pop'));
    cue(2.0, () => hooks.sfx?.('whoosh', .8)); cue(2.72, () => hooks.sfx?.('boom', 1)); cue(3.0, () => hooks.sfx?.('charge', 3)); cue(6.08, () => hooks.sfx?.('whoosh', .5)); cue(6.35, () => hooks.sfx?.('burst'));
    sparks.add({ t0: .45, n: 50, speed: 7, life: .5, cols: [[3, 3, 3], [3, 1.6, .3]], size: .09, drag: 4, seed: 3 });
    sparks.add({ t0: 1.74, n: 40, speed: 5, life: .45, cols: [[3, 3, 3]], size: .08, drag: 5, seed: 4, z: .5 });
    sparks.add({ t0: 2.72, n: 90, speed: 9, life: .8, cols: [[3, 3, 3], [3, 2.4, .4]], size: .1, drag: 3, seed: 5 });
    sparks.add({ t0: 3.1, n: 160, speed: 1.2, life: 3, cols: [[3, 1.6, .3], [3, .6, .2]], size: .05, drag: .4, seed: 6, spread: 3, shape: 'rect', hw: packW / 2, hh: packH / 2 });
  }

  TL.candy = (t) => {
    const pos = new THREE.Vector3(), rot = new THREE.Euler();
    pos.set(0, candyPackY(t), 0);
    let s = t < .3 ? .82 : lerp(.82, 1, oBack(clamp((t - .3) / .35), 1.2));
    rot.set(Math.sin(t * 1.1) * .05, Math.sin(t * .8) * .12, 0);
    pack.visible = t < 5.3;
    L.smear.set(t < .33 ? (1 - t / .33) : 0); L.smear.m.position.set(0, 2.2, -.2); L.smear.m.scale.set(packW / 5, 1.2, 1);
    aura.set(pack.visible ? .6 : 0, { uGlow: .2, uFire: 0, uColA: C(1.6, .5, 1.1) });
    physTo(t);
    sphMesh.visible = t > .8; torMesh.visible = t > 2.8;
    bolts.begin(); boltsBack.begin(); bolts.end(); boltsBack.end();
    return { pos, rot, s };
  };
  function candyCues() {
    cue(0, () => hooks.sfx?.('whoosh', .3)); cue(.3, () => hooks.sfx?.('thud')); cue(.45, () => hooks.sfx?.('sparkle'));
    for (let k = 0; k < 26; k++) cue(.9 + k * .078, () => hooks.sfx?.('plink'));
    for (let k = 0; k < 28; k++) cue(2.9 + k * .076, () => hooks.sfx?.('clink'));
    cue(5.22, () => hooks.sfx?.('whoosh', .6));
    sparks.add({ t0: .42, n: 140, speed: 8, life: .8, cols: [[3, 2.6, .6], [3, .6, 1.6], [3, 3, 2]], size: .2, drag: 2.5, seed: 11, spread: 1.2, z: .4 });
    sparks.add({ t0: .55, n: 60, speed: 2, life: .7, cols: [[3, 2.6, .6]], size: .16, drag: 2, seed: 12, spread: 1, z: .4, shape: 'rect', hw: 1.4, hh: 2 });
  }

  TL.legendary = (t) => {
    const pos = new THREE.Vector3(), rot = new THREE.Euler(); const Rj = rng(77 + Math.floor(t * 30));
    let s = t < .3 ? lerp(.75, 1, o3(t / .3)) : 1;
    const shake = env(t, 1.2, 1.4, 2.7, 3) * .05 + env(t, 6.5, 6.7, 8, 8.2) * .035;
    rot.set(Math.sin(t * .8) * .06 + (t > 1.4 && t < 2.9 ? Math.sin(t * 2.3) * .15 : 0), Math.sin(t * 1.1) * .18, Math.sin(t * .9) * .08 + (t > 1.4 && t < 3 ? Math.sin(t * 1.7) * .08 : 0));
    pos.set((Rj() - .5) * shake, (Rj() - .5) * shake, 0);
    // swap to the upgraded texture during the white-out
    const up = t >= 5.2; face.material.map = up ? texB : texA; face.parent.children[1].material.map = up ? texB : texA;
    if (t > 5.2) s = lerp(1.12, 1, o3(clamp((t - 5.2) / .5)));
    pack.visible = t < 4.3 || (t > 5.2 && t < 10.36);
    packU.uBurn.value = env(t, 1.7, 2.9, 2.92, 3.05) * .5;
    packU.uGlint.value = t > 7.2 && t < 8.3 ? lerp(-.3, 1.9, smooth(7.2, 8.2, t)) : -2;
    packU.uEmis.value = smooth(3.6, 4.4, t) * (t < 5.2 ? 1.2 : 0) + pulse(t, 9.72, .3) * .15;
    // aura: gold outline + fire
    const fire = env(t, .2, .4, 1.1, 1.35) + env(t, 5.55, 5.7, 6.3, 6.6) * .9 + env(t, 1.7, 1.9, 2.8, 3) * .6;
    aura.set(pack.visible ? 1 : 0, { uGlow: .7 + pulse(t, 9.72, .4) * .6, uFire: fire * 1.2, uColA: C(2.8, 2.2, .7), uFireA: C(3, 2.5, .8), uFireB: C(1.6, .6, .05) });
    // hyperspace streaks almost always
    L.streaks.set((env(t, .2, .5, 4.3, 4.6) + env(t, 5.5, 5.8, 10.2, 10.4)) * .6, { uSpeed: .55, uDensity: .22, uLen: 1, uColA: C(3, 1, .25), uColB: C(3, 1.9, .5) });
    // vortex (3.2 - 4.4) yellow; blue swirl after the whiteout (5.2 - 5.9)
    if (t < 5) L.vortex.set(env(t, 3.15, 3.4, 4.2, 4.5), { uColA: C(3, 2.6, .9), uColB: C(2.6, 1.5, .1), uArms: 3, uTwist: 2.4, uR0: 1.2, uR1: 5.5 });
    else L.vortex.set(env(t, 5.2, 5.25, 5.7, 6), { uColA: C(1.8, 2.6, 3.4), uColB: C(.2, .6, 2), uArms: 5, uTwist: 1.2, uR0: 2.6, uR1: 8 });
    // pink-white fire ring on the pack face (3.2 - 4.1)
    L.faceRing.set(env(t, 3.2, 3.35, 3.95, 4.15), { uR: .35 + smooth(3.2, 4, t) * .2, uThick: .07 });
    // energy ball (4.0 - 5.0), then burst ring (4.7 - 5.2)
    L.ball.set(env(t, 3.85, 3.95, 4.9, 5.15), { uColA: C(2.3, 2.1, .9), uColB: C(1.9, 1.2, .1), uR: lerp(.4, 3.6, smooth(3.85, 4.5, t)), uHole: 0, uMode: 0 });
    // star flare 4.85 - 5.2 (blue-white)
    L.flare.set(env(t, 4.85, 4.95, 5.05, 5.2) * 1.2, { uColA: C(1.6, 2.3, 3.5) });
    // white-out 5.1 - 5.35
    L.flash.set(env(t, 5.08, 5.18, 5.28, 5.45), { uColA: t < 8 ? C(1.7, 1.7, 1.7) : C(2, 1.5, .6), uWipe: -99 });
    // orange/white comic ray burst 9.7 - 10.0
    L.raysFront.set(env(t, 9.66, 9.72, 9.9, 10.02), { uCount: 30, uWidth: .1, uR0: 1.6, uR1: 14, uSeed: 31, uDensity: .6, uColA: C(2, 1.9, 1.6), uColB: C(2, .55, .1), uSpin: 0 });
    // gold electric web 9.95 - 10.4
    L.flowBg.set(env(t, 9.9, 10, 10.3, 10.45), { uColA: C(2.8, 2, .5), uColB: C(.5, .25, 0), uFreq: 9, uScale: .6, uHaze: .5 });
    // cyan plasma sphere (10.35 - 10.65) → shockwave ring expanding (10.55 - 11.2) with dark-blue fog → fade
    if (t > 10.3) L.ball.set(env(t, 10.3, 10.4, 10.55, 10.7), { uColA: C(1.5, 2.9, 3.1), uColB: C(.2, 1.1, 2.6), uR: lerp(1.2, 4.6, smooth(10.3, 10.55, t)), uHole: .5, uMode: 0 });
    L.ring.set(env(t, 10.5, 10.6, 11.0, 11.35), { uR: lerp(2.5, 9, smooth(10.5, 11.2, t)), uThick: .8, uDark: 1.4 * (1 - smooth(11, 11.4, t)) });
    // lightning
    const fr = Math.floor(t * 16), Rb = rng(500 + fr); bolts.begin(); boltsBack.begin();
    const xBolts = env(t, 1.15, 1.3, 2.75, 2.95) + env(t, 6.45, 6.6, 8.1, 8.3);
    if (xBolts > 0) for (let i = 0; i < 8; i++) {
      const sx = i % 2 ? 1 : -1, sy = (i >> 1) % 2 ? 1 : -1, ex = sx * (7 + Rb() * 2), ey = sy * (1.5 + Rb() * 3.5);
      boltsBack.bolt(ex, ey, -ex * .1 + (Rb() - .5), -ey * .1, { R: Rb, disp: .4, w: .13 + Rb() * .1, col: [3, 2.1, .3], a: xBolts, z: -.6, branches: 3 });
    }
    if (t > .45 && t < .6) bolts.bolt(-packW * .35, packH * .35, packW * .1, -packH * .25, { R: Rb, disp: .8, w: .03, col: [1.8, 1.2, 3], a: 1, z: .3, branches: 3 });
    if (t > .72 && t < .85) bolts.bolt(-packW * .5, -packH * .47, packW * .5, -packH * .45, { R: Rb, disp: .15, w: .03, col: [3, 2.4, 2], a: 1, z: .3 });
    if (t > 1.45 && t < 1.6) bolts.bolt(-packW * .55, -packH * .1, packW * .5, -packH * .2, { R: Rb, disp: .2, w: .03, col: [3, 3, 3], a: 1, z: .3 });
    if (t > 5.95 && t < 6.3) bolts.bolt(-packW * .45, -packH * .42, -packW * .1, -packH * .38, { R: Rb, disp: .5, w: .025, col: [1.8, 1.2, 3], a: 1, z: .3, branches: 2 });
    // orange electric orbit arcs around the pack (8.3 - 9.6)
    if (t > 8.3 && t < 9.65) { const k = env(t, 8.3, 8.45, 9.45, 9.65); for (let j = 0; j < 2; j++) { const a0 = t * 3.2 + j * 3.14, P = []; for (let i = 0; i <= 16; i++) { const a = a0 + i * .09; P.push([Math.cos(a) * (packW * .62) + (Rb() - .5) * .08, Math.sin(a) * packH * .58 + (Rb() - .5) * .08]); } bolts.line(P, .05, [3, 1.5, .3], k, .35, true); } }
    // blue sigil on the pack (10.15 - 10.45)
    if (t > 10.12 && t < 10.5) for (let i = 0; i < 6; i++) { const a = i / 6 * 6.28 + t; bolts.bolt(0, 0, Math.cos(a) * .8, Math.sin(a) * .8, { R: Rb, disp: .5, w: .035, col: [.5, 1.8, 3.4], a: env(t, 10.12, 10.18, 10.4, 10.5), z: .4, seg: 8 }); }
    bolts.end(); boltsBack.end();
    return { pos, rot, s };
  };
  function legendaryCues() {
    cue(0, () => hooks.sfx?.('flame', 1.2)); cue(.45, () => hooks.sfx?.('zap')); cue(1.15, () => hooks.sfx?.('thunder')); cue(1.7, () => hooks.sfx?.('flame', 1.4));
    cue(3.0, () => hooks.sfx?.('sparkle')); cue(3.15, () => hooks.sfx?.('charge', 1.8)); cue(4.85, () => hooks.sfx?.('boom', 1.2)); cue(5.2, () => hooks.sfx?.('rare', 3));
    cue(6.45, () => hooks.sfx?.('thunder')); cue(7.3, () => hooks.sfx?.('sparkle')); cue(8.3, () => hooks.sfx?.('zap')); cue(9.7, () => hooks.sfx?.('boom', .8)); cue(10.3, () => hooks.sfx?.('burst')); cue(10.55, () => hooks.sfx?.('whoosh', .8));
    sparks.add({ t0: 3.0, n: 30, speed: 1.5, life: .5, cols: [[3, 3, 3]], size: .12, drag: 3, seed: 21, x: -.4, y: -.3, z: .5 });
    sparks.add({ t0: 4.9, n: 180, speed: 8, life: 1, cols: [[2.6, 3, 3.4], [3, 2.6, 1]], size: .09, drag: 2.5, seed: 22, spread: 2 });
    sparks.add({ t0: 5.6, n: 120, speed: 1.4, life: 1.2, cols: [[3, 2.2, .5]], size: .06, drag: .8, seed: 23, shape: 'rect', hw: packW / 2, hh: packH / 2 });
    sparks.add({ t0: 9.72, n: 100, speed: 7, life: .8, cols: [[3, 2.2, .5], [3, 3, 3]], size: .09, drag: 3, seed: 24 });
    sparks.add({ t0: 10.55, n: 160, speed: 10, life: 1, cols: [[1.2, 2.8, 3.4]], size: .08, drag: 2, seed: 25, spread: 2 });
  }

  /* ------------------------------------------------------------------ run */
  let kind = null, t0 = 0, raf = 0, running = false, resolveP = null, frozen = null;
  function resize() {
    const w = canvas.clientWidth || innerWidth, h = canvas.clientHeight || innerHeight;
    renderer.setSize(w, h, false); composer.setSize(w, h); { const pr = renderer.getPixelRatio(); bloom.setSize(Math.round(w * pr / 2), Math.round(h * pr / 2)); } // half-res glow: same look, ~4x cheaper
    camera.aspect = w / h;
    // keep the pack framed on portrait screens
    camera.position.z = camera.aspect < 1 ? 10 / Math.max(camera.aspect * 1.25, .55) : 10; camera.updateProjectionMatrix();
    const halfH = camera.position.z * Math.tan(THREE.MathUtils.degToRad(17.5));
    for (const l of layers) { l.u.uAspect.value = camera.aspect; l.u.uHalfH.value = halfH; }
    sparks.mat.uniforms.uPR.value = renderer.getPixelRatio() * h / 400;
  }
  function frame(t) {
    const R = rng(1);
    for (const l of layers) { l.u.uTime.value = t; l.m.visible = false; l.u.uAlpha.value = 0; }
    while (cueI < cues.length && cues[cueI].t <= t) { if (frozen == null) cues[cueI].fn(); cueI++; }
    const { pos, rot, s } = TL[kind](t, R);
    pack.position.copy(pos); pack.rotation.copy(rot); pack.scale.setScalar(s);
    for (const l of layers) if (l.screen) l.u.uCenter.value.set(pos.x, pos.y);
    sparks.update(t);
    composer.render();
  }
  let clock = 0, last = 0;
  const q = { n: 0, sum: 0 };
  function loop() {
    if (!running) return;
    const now = performance.now(), dt = (now - last) / 1000; clock += Math.min(.05, dt); last = now; // hitch-safe clock: slow down instead of skipping
    const t = clock;
    // adaptive resolution: a weak GPU renders the effect smaller rather than stuttering
    q.sum += dt; if (++q.n === 24) { const avg = q.sum / q.n; q.n = 0; q.sum = 0; const pr = renderer.getPixelRatio();
      if (avg > .02 && pr > .6) { renderer.setPixelRatio(Math.max(.6, pr - .2)); resize(); } }
    if (t >= DURATION[kind]) { finish(); return; }
    frame(t); raf = requestAnimationFrame(loop);
  }
  function finish() { running = false; cancelAnimationFrame(raf); renderer.setClearColor(0, 1); renderer.clear(); const r = resolveP; resolveP = null; hooks.onEnd?.(); r?.(); }
  const loader = new THREE.TextureLoader();
  const loadTex = url => new Promise((res, rej) => loader.load(url, t => { t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = renderer.capabilities.getMaxAnisotropy(); res(t); }, undefined, rej));

  async function play(k, { art, upgrade, freeze = null } = {}) {
    stop(); kind = DURATION[k] ? k : 'electric';
    texA?.dispose(); texB?.dispose();
    texA = await loadTex(art); texB = upgrade ? await loadTex(upgrade) : texA;
    buildPack(texA);
    cues = []; cueI = 0; sparks.clear(); packU.uBurn.value = 0; packU.uGlint.value = -2; packU.uEmis.value = 0;
    resize(); if (kind === 'candy' && (!baked || Math.abs(baked.aspect - camera.aspect) > .05)) { await physBake(4242); baked.aspect = camera.aspect; }
    bloom.enabled = kind !== 'candy'; bloom.strength = .35;
    if (kind === 'candy') { key.position.set(-2, 8, 1.5); fill.intensity = .35; } else { key.position.set(-3, 5, 6); fill.intensity = .8; }
    ({ electric: electricCues, candy: candyCues, legendary: legendaryCues })[kind]();
    cues.sort((a, b) => a.t - b.t);
    sphMesh.visible = torMesh.visible = false;
    resize();
    if (freeze != null) { frozen = freeze; frame(freeze); return; }
    // warm-up: compile every shader the effect will use *before* the clock starts (a mid-effect compile is a visible freeze)
    const hidden = []; scene.traverse(o => { if (!o.visible) { hidden.push(o); o.visible = true; } });
    try { await renderer.compileAsync(scene, camera); } catch { renderer.compile(scene, camera); }
    hidden.forEach(o => (o.visible = false));
    frozen = 0; frame(0); composer.render(); await new Promise(r => requestAnimationFrame(r));
    frozen = null; running = true; clock = 0; last = performance.now(); cueI = 0;
    return new Promise(res => { resolveP = res; raf = requestAnimationFrame(loop); });
  }
  function seek(t) { frozen = t; cueI = 0; frame(t); }
  function skip() { if (running) finish(); }
  function stop() { running = false; cancelAnimationFrame(raf); if (resolveP) { const r = resolveP; resolveP = null; r(); } }
  addEventListener('resize', () => { if (running || frozen != null) resize(); });
  return { play, skip, stop, seek, resize, get active() { return running; }, _dbg: { L, layers, bloom, scene, bolts, boltsBack, sparks, get aura() { return aura; }, get pack() { return pack; } } };
}
