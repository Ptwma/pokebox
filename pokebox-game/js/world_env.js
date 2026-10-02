// Pokebox world — environment building blocks: sky, terrain, water, grass, particles, post-processing.
// All procedural (shaders + instancing) so they cost no downloads.
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { N8AOPass } from 'three/addons/n8ao/N8AO.js';

export const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
export const lerp = (a, b, k) => a + (b - a) * k;
export const smooth = (a, b, x) => { const t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
export function rng(seed) { let s = seed >>> 0; return () => ((s = (Math.imul(s, 1664525) + 1013904223) >>> 0) / 4294967296); }
export function hash2(x, z) { let h = Math.imul(x | 0, 374761393) + Math.imul(z | 0, 668265263); h = Math.imul(h ^ (h >>> 13), 1274126177); return ((h ^ (h >>> 16)) >>> 0) / 4294967296; }
export function vnoise(x, z) { const xi = Math.floor(x), zi = Math.floor(z), xf = x - xi, zf = z - zi, u = xf * xf * (3 - 2 * xf), v = zf * zf * (3 - 2 * zf);
  return lerp(lerp(hash2(xi, zi), hash2(xi + 1, zi), u), lerp(hash2(xi, zi + 1), hash2(xi + 1, zi + 1), u), v); }
export const fbm = (x, z, o = 4) => { let s = 0, a = .5, f = 1; for (let i = 0; i < o; i++) { s += a * vnoise(x * f, z * f); f *= 2.03; a *= .5; } return s; };
export const col = c => new THREE.Color(c);
export const SIZE = 300, HALF = SIZE / 2; // terrain footprint (walkable radius ~112)

/* distance from point to a polyline (for paths) */
export function segDist(px, pz, pts) {
  let best = 1e9;
  for (let i = 0; i < pts.length - 1; i++) {
    const [ax, az] = pts[i], [bx, bz] = pts[i + 1], dx = bx - ax, dz = bz - az, l = dx * dx + dz * dz || 1;
    const t = clamp(((px - ax) * dx + (pz - az) * dz) / l, 0, 1), qx = ax + dx * t - px, qz = az + dz * t - pz;
    best = Math.min(best, Math.hypot(qx, qz));
  }
  return best;
}

/* ================================================================== sky: gradient + sun + 2 cloud layers + stars/aurora */
export function makeSky(A) {
  const u = {
    top: { value: col(A.sky[0]) }, bot: { value: col(A.sky[1]) }, fogc: { value: col(A.fog[0]) }, sunDir: { value: new THREE.Vector3(...(A.sun || [.45, .55, .35])).normalize() },
    sunCol: { value: col(A.sunColor || '#fff2d6') }, cloudCol: { value: col(A.cloud || '#ffffff') }, cloudAmt: { value: A.clouds ?? .5 }, night: { value: A.night ? 1 : 0 },
    aurora: { value: A.aurora ? 1 : 0 }, time: { value: 0 },
  };
  const m = new THREE.ShaderMaterial({
    side: THREE.BackSide, depthWrite: false, uniforms: u,
    vertexShader: `varying vec3 vDir; void main(){ vDir = normalize(position); vec4 p = projectionMatrix * modelViewMatrix * vec4(position,1.); gl_Position = p.xyww; }`,
    fragmentShader: `uniform vec3 top, bot, fogc, sunDir, sunCol, cloudCol; uniform float cloudAmt, night, aurora, time; varying vec3 vDir;
      float h(vec2 p){ return fract(sin(dot(p, vec2(127.1,311.7))) * 43758.5453); }
      float n(vec2 p){ vec2 i = floor(p), f = fract(p); f = f*f*(3.-2.*f); return mix(mix(h(i),h(i+vec2(1,0)),f.x), mix(h(i+vec2(0,1)),h(i+vec2(1,1)),f.x), f.y); }
      float fbm(vec2 p){ float s = 0., a = .5; for (int i = 0; i < 4; i++) { s += a * n(p); p = p * 2.02 + 7.1; a *= .5; } return s; }
      void main(){
        vec3 d = normalize(vDir); float y = d.y;
        float yb = smoothstep(-.02, .55, y); yb = yb + (fract(sin(dot(floor(vec2(atan(d.z, d.x) * 40., y * 260.)), vec2(12.9,78.2))) * 43758.5) - .5) * .025; vec3 c = mix(bot, top, yb);
        c = mix(c, fogc, 1. - smoothstep(-.05, .16, y));                                  // horizon haze
        float sd = max(dot(d, sunDir), 0.);
        c += sunCol * (pow(sd, 900.) * 6. + pow(sd, 12.) * .35 * (1. - night) + pow(sd, 3.) * .08);  // disc + glow
        if (y > 0.) {                                                                  // clouds on a dome projection
          vec2 uv = d.xz / (y + .12);
          // big soft cumulus (anime sky): large shapes, bright sunlit tops, blue-grey bellies, soft edges, silver lining toward the sun
          float c1 = fbm(uv * .62 + vec2(time * .010, time * .003));
          float c2 = fbm(uv * 1.9 - vec2(time * .016, 0.));
          float cv = c1 * .8 + c2 * .32, th = 1.0 - max(cloudAmt, .55) * .78;
          float cl = smoothstep(th, th + .1, cv) * smoothstep(0., .2, y);
          float lit = smoothstep(.25, .85, c2 * .5 + (cv - th) * 2.6 + .15);
          vec3 cc = mix(mix(cloudCol, vec3(.62, .7, .86), .45) * .82, cloudCol * 1.07, lit);
          cc += sunCol * pow(sd, 5.) * (1. - smoothstep(0., .14, cv - th)) * .55;
          c = mix(c, cc, cl * .92);
          if (night > .02) {                                                           // stars
            vec2 sp = d.xz / (y + .6) * 180.; float st = step(.9965, h(floor(sp))) * (.6 + .4 * sin(time * 3. + h(floor(sp)) * 40.));
            c += vec3(st) * (1. - cl) * smoothstep(0., .3, y) * night;
          }
          if (aurora > .5) {
            float band = sin(d.x * 5. + fbm(d.xz * 3. + time * .05) * 4.) * .5 + .5;
            float a = smoothstep(.15, .5, y) * (1. - smoothstep(.5, .9, y)) * pow(band, 3.) * fbm(vec2(d.x * 8., time * .1));
            c += vec3(.2, 1., .7) * a * .9 + vec3(.5, .2, 1.) * a * .35 * smoothstep(.4, .7, y);
          }
        }
        gl_FragColor = vec4(c, 1.);
        #include <colorspace_fragment>
      }`,
  });
  const mesh = new THREE.Mesh(new THREE.SphereGeometry(400, 48, 24), m); mesh.renderOrder = -10; mesh.frustumCulled = false;
  mesh.userData.tick = t => { u.time.value = t; };
  return mesh;
}

/* distant islands/mountains ring so the horizon is never empty */
export function horizonRing(A, seed = 3) {
  const R = rng(seed), g = new THREE.Group(), mat = new THREE.MeshStandardMaterial({ color: col(A.far || '#6f8f7a'), roughness: 1, flatShading: true, fog: true });
  for (let i = 0; i < 18; i++) {
    const a = i / 18 * Math.PI * 2 + R() * .2, r = 280 + R() * 80, hgt = 22 + R() * (A.peaks || 38) * 1.6, w = 50 + R() * 60;
    const geo = new THREE.ConeGeometry(w, hgt, 7 + (R() * 4 | 0), 3); const p = geo.attributes.position;
    for (let k = 0; k < p.count; k++) { const y = p.getY(k); if (y < hgt / 2 - .1) { p.setX(k, p.getX(k) * (.8 + R() * .5)); p.setZ(k, p.getZ(k) * (.8 + R() * .5)); p.setY(k, y + (R() - .5) * hgt * .15); } }
    geo.computeVertexNormals(); const m = new THREE.Mesh(geo, mat); m.position.set(Math.cos(a) * r, hgt / 2 - 6, Math.sin(a) * r); m.rotation.y = R() * 6; g.add(m);
  }
  return g;
}

/* ================================================================== terrain: vertex-coloured by height/slope/paths + grain texture */
const grainTex = (() => {
  const c = document.createElement('canvas'); c.width = c.height = 256; const g = c.getContext('2d'); const img = g.createImageData(256, 256), R = rng(9);
  for (let i = 0; i < 256 * 256; i++) { const v = 228 + R() * 27 - (R() < .03 ? 18 : 0); img.data.set([v, v, v, 255], i * 4); }
  g.putImageData(img, 0, 0); const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(80, 80); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t;
})();
export function makeTerrain(A, h, paths = []) {
  const N = 240, g = new THREE.PlaneGeometry(SIZE, SIZE, N, N); g.rotateX(-Math.PI / 2);
  const p = g.attributes.position, colors = new Float32Array(p.count * 3);
  const G = A.ground.map(col), sand = col(A.sand || '#d9c89a'), rock = col(A.rock || '#7c7a74'), path = col(A.path || '#b59a6c'), wet = col(A.ground[1]).multiplyScalar(.62), tmp = new THREE.Color();
  const e = .6;
  for (let i = 0; i < p.count; i++) {
    const x = p.getX(i), z = p.getZ(i), y = h(x, z); p.setY(i, y);
    const slope = Math.min(1, Math.hypot(h(x + e, z) - h(x - e, z), h(x, z + e) - h(x, z - e)) / (2 * e));
    const n = fbm(x * .12, z * .12), n2 = vnoise(x * .6, z * .6);
    tmp.copy(G[0]).lerp(G[1], clamp(n * 1.5 - .25, 0, 1)).lerp(G[2], clamp((y - (A.highY ?? 3)) * .35, 0, 1));
    tmp.multiplyScalar(.9 + n2 * .18);
    if (y < (A.beach ?? .55)) tmp.lerp(sand, smooth(A.beach ?? .55, (A.beach ?? .55) - .5, y));
    if (y < .05) tmp.lerp(wet, smooth(.05, -.6, y));
    tmp.lerp(rock, smooth(.45, .85, slope));
    let pd = 1e9; for (const pt of paths) pd = Math.min(pd, segDist(x, z, pt.pts) - (pt.w || 1.4));
    if (pd < 1.2) tmp.lerp(path, smooth(1.2, -.2, pd) * (.85 + n2 * .15));
    colors.set([tmp.r, tmp.g, tmp.b], i * 3);
  }
  g.setAttribute('color', new THREE.BufferAttribute(colors, 3)); g.computeVertexNormals();
  const m = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ vertexColors: true, map: grainTex, roughness: .96, metalness: 0 }));
  m.receiveShadow = true; m.name = 'terrain'; return m;
}

/* heightmap texture for the water shader (depth colour + shore foam) */
export function heightTexture(h) {
  const N = 256, d = new Float32Array(N * N);
  for (let j = 0; j < N; j++) for (let i = 0; i < N; i++) d[j * N + i] = h((i / (N - 1) - .5) * SIZE * 1.6, (j / (N - 1) - .5) * SIZE * 1.6);
  const t = new THREE.DataTexture(d, N, N, THREE.RedFormat, THREE.FloatType); t.magFilter = t.minFilter = THREE.LinearFilter; t.needsUpdate = true; return t;
}

/* ================================================================== water: depth-tinted, animated normals, fresnel, sun glints, shore foam */
export function makeWater(A, h, { ice = false, hm = null, span = SIZE * 1.6, size = SIZE * 1.6 } = {}) {
  const u = {
    time: { value: 0 }, hm: { value: hm || heightTexture(h) }, span: { value: span }, shallow: { value: col(A.shallow || '#3fc1c9') }, deep: { value: col(A.water) },
    sky: { value: col(A.sky[1]) }, sunDir: { value: new THREE.Vector3(...(A.sun || [.45, .55, .35])).normalize() }, sunCol: { value: col(A.sunColor || '#fff2d6') },
    ice: { value: ice ? 1 : 0 }, fogColor: { value: col(A.fog[0]) }, fogNear: { value: A.fog[1] }, fogFar: { value: A.fog[2] },
  };
  const m = new THREE.ShaderMaterial({
    uniforms: u, transparent: true, depthWrite: true, fog: false,
    vertexShader: `uniform float time; varying vec3 vW; varying float vFogDepth;
      void main(){ vec3 p = position; vec4 w = modelMatrix * vec4(p,1.);
        w.y += sin(w.x * .35 + time * 1.1) * .045 + sin(w.z * .5 - time * .9) * .04;
        vW = w.xyz; vec4 mv = viewMatrix * w; vFogDepth = -mv.z; gl_Position = projectionMatrix * mv; }`,
    fragmentShader: `uniform float time, span, ice, fogNear, fogFar; uniform sampler2D hm; uniform vec3 shallow, deep, sky, sunDir, sunCol, fogColor; varying vec3 vW; varying float vFogDepth;
      float h(vec2 p){ return fract(sin(dot(p, vec2(12.9898,78.233))) * 43758.5453); }
      float n(vec2 p){ vec2 i = floor(p), f = fract(p); f = f*f*(3.-2.*f); return mix(mix(h(i),h(i+vec2(1,0)),f.x), mix(h(i+vec2(0,1)),h(i+vec2(1,1)),f.x), f.y); }
      void main(){
        float ground = texture2D(hm, vW.xz / span + .5).r; float depth = max(0., -ground);
        vec2 q = vW.xz;
        float e = .15, a = n(q * .45 + time * .25) + n(q * 1.3 - time * .35) * .5 + n(q * 3.7 + vec2(time * .6, -time * .2)) * .25;
        float ax = n((q + vec2(e,0.)) * .45 + time * .25) + n((q + vec2(e,0.)) * 1.3 - time * .35) * .5 + n((q + vec2(e,0.)) * 3.7 + vec2(time * .6, -time * .2)) * .25;
        float az = n((q + vec2(0.,e)) * .45 + time * .25) + n((q + vec2(0.,e)) * 1.3 - time * .35) * .5 + n((q + vec2(0.,e)) * 3.7 + vec2(time * .6, -time * .2)) * .25;
        vec3 N = normalize(vec3((a - ax) * (ice > .5 ? .25 : 1.6), 1., (a - az) * (ice > .5 ? .25 : 1.6)));
        vec3 V = normalize(cameraPosition - vW);
        float fres = pow(1. - max(dot(N, V), 0.), 4.) * .85 + .05;
        vec3 water = mix(shallow, deep, floor(smoothstep(0., 3.5, depth) * 3. + .5) / 3.);
        vec3 c = mix(water, sky * 1.05, step(.45, fres) * .6 + fres * .25);
        vec3 H = normalize(sunDir + V); c += sunCol * step(ice > .5 ? .93 : .985, max(dot(N, H), 0.)) * (ice > .5 ? .5 : 1.4);
        float foam = smoothstep(.55, 0., depth) * (.55 + .45 * sin(depth * 18. - time * 2.4 + n(q * 2.) * 6.));
        foam = clamp(foam + smoothstep(.12, 0., depth), 0., 1.) * (1. - ice);
        c = mix(c, vec3(.96, .98, 1.), step(.5, foam) * .85);
        if (ice > .5) c = mix(c, vec3(.86, .94, 1.), .55) + n(q * 6.) * .04;
        float alpha = clamp(.55 + depth * .35 + fres * .3 + foam, 0., ice > .5 ? .96 : .93);
        float f = smoothstep(fogNear, fogFar, vFogDepth); c = mix(c, fogColor, f);
        gl_FragColor = vec4(c, alpha);
        #include <colorspace_fragment>
      }`,
  });
  const w = new THREE.Mesh(new THREE.PlaneGeometry(size, size, 96, 96), m); w.userData.u = u; w.rotation.x = -Math.PI / 2; w.position.y = 0; w.renderOrder = 2;
  w.userData.tick = t => { u.time.value = t; }; return w;
}

/* ================================================================== grass (instanced blades, wind + player push) */
export const GFX = { density: 1, grassFar: 45 }; // set by the world from the quality level
export function grassField(hf, test, { n = 22000, r = 60, base = '#4f7d3d', tip = '#b9d77a', hgt = .7, seed = 5, w = .06, hmask = null, span: spanIn = null } = {}) {
  // Blades live in a square of side 2R that wraps around the player (world-stable pattern, constant cost at any map size).
  // A baked texture over the whole island gives each blade its ground height (R) and whether grass may grow there (G).
  const R = GFX.grassFar, dens = n / (Math.PI * r * r); n = Math.round(dens * 4 * R * R * GFX.density);
  const M = hmask ? 0 : 384, span = spanIn || SIZE, data = new Float32Array(Math.max(1, M * M * 2));
  for (let j = 0; j < M; j++) for (let i = 0; i < M; i++) {
    const x = (i / (M - 1) - .5) * span, z = (j / (M - 1) - .5) * span, y = hf(x, z), k = (j * M + i) * 2;
    data[k] = y; data[k + 1] = i && j && i < M - 1 && j < M - 1 && test(x, z, y) ? 1 : 0;
  }
  let hm = hmask; if (!hm) { hm = new THREE.DataTexture(data, M, M, THREE.RGFormat, THREE.FloatType); hm.magFilter = hm.minFilter = THREE.LinearFilter; hm.needsUpdate = true; }
  const blade = new THREE.BufferGeometry();
  // a tuft of 4 soft blades (different heights, leaning outwards) instead of one stiff spike: reads as a lawn, not as needles
  const P = [], I = [];
  [[0, 1, 0], [2.1, .78, .18], [4.2, .86, -.12], [1.1, .62, .3]].forEach(([a, hh, lean], b) => {
    const ca = Math.cos(a), sa = Math.sin(a), o = P.length / 3, ox = sa * .05, oz = ca * .05;
    const pt = (x, y, z) => P.push(ox + x * ca + z * sa, y * hh, oz - x * sa + z * ca);
    pt(-w * 1.3, 0, 0); pt(w * 1.3, 0, 0); pt(-w * .85, .45, .04 + lean * .2); pt(w * .85, .45, .04 + lean * .2); pt(0, 1, .12 + lean * .35);
    I.push(o, o + 1, o + 2, o + 1, o + 3, o + 2, o + 2, o + 3, o + 4);
  });
  blade.setAttribute('position', new THREE.Float32BufferAttribute(P, 3)); blade.setIndex(I);
  const geo = new THREE.InstancedBufferGeometry(); geo.index = blade.index; geo.attributes.position = blade.attributes.position;
  const Rg = rng(seed), off = new Float32Array(n * 4), rot = new Float32Array(n * 2);
  for (let i = 0; i < n; i++) { off.set([(Rg() * 2 - 1) * R, 0, (Rg() * 2 - 1) * R, (.55 + Rg() * .8) * hgt], i * 4); rot.set([Rg() * 6.2832, Rg()], i * 2); }
  geo.setAttribute('ofs', new THREE.InstancedBufferAttribute(off, 4)); geo.setAttribute('rot', new THREE.InstancedBufferAttribute(rot, 2)); geo.instanceCount = n;
  const mat = new THREE.ShaderMaterial({ fog: true, side: THREE.DoubleSide,
    uniforms: THREE.UniformsUtils.merge([THREE.UniformsLib.fog, { time: { value: 0 }, player: { value: new THREE.Vector3(0, -99, 0) }, cBase: { value: col(base) }, cTip: { value: col(tip) }, gFar: { value: GFX.grassFar }, R: { value: R }, span: { value: span } }]),
    vertexShader: `attribute vec4 ofs; attribute vec2 rot; uniform float time, gFar, R, span; uniform vec3 player; uniform sampler2D hmask; varying float vH; varying float vShade; varying float vVar;
      #include <fog_pars_vertex>
      void main(){
        vec2 wxz = player.xz + mod(ofs.xz - player.xz + R, 2. * R) - R;          // wrap the patch around the player
        vec2 hmv = texture2D(hmask, wxz / span + .5).rg;
        float cd = distance(cameraPosition.xz, wxz);
        if (hmv.g < .15 + rot.y * .75 || cd > gFar) { gl_Position = vec4(2., 2., 2., 1.); return; }
        vec3 base = vec3(wxz.x, hmv.r - .02, wxz.y);
        vec3 p = position; float s = ofs.w * (1. - smoothstep(gFar * .75, gFar, cd)) * (.55 + .45 * smoothstep(.2, 1., hmv.g)); p.y *= s; float cr = cos(rot.x), sr = sin(rot.x); p = vec3(p.x*cr - p.z*sr, p.y, p.x*sr + p.z*cr);
        vec3 wp = base + p; float bend = position.y*position.y;
        float gust = sin(time * .6 + base.x * .05) * .5 + .5;
        float wv = sin(time*1.7 + base.x*.35 + base.z*.21) * (.4 + gust * .5) + sin(time*3.1 + base.x*.9) * .15;
        wp.x += wv * .3 * bend * s; wp.z += wv * .13 * bend * s;
        vec2 away = base.xz - player.xz; float pd = length(away); float push = (1. - smoothstep(.2, 1.4, pd)) * bend;
        wp.xz += normalize(away + 1e-4) * push * .55; wp.y -= push * .25 * s;
        vH = position.y; vShade = .78 + .22*rot.y;
        vVar = sin(base.x * .043 + sin(base.z * .021) * 2.) * .5 + sin(base.z * .037 + base.x * .019) * .5;   // large meadow patches: sunny yellow-green vs deep green
        vec4 mvPosition = viewMatrix * vec4(wp, 1.); gl_Position = projectionMatrix * mvPosition;
        #include <fog_vertex>
      }`,
    fragmentShader: `uniform vec3 cBase, cTip; varying float vH; varying float vShade; varying float vVar;
      #include <fog_pars_fragment>
      void main(){
        // soft root→tip gradient (dark roots blend into the ground), per-blade hue drift between teal and sun-yellow
        float k = smoothstep(0., 1., vH); float hue = (vShade - .78) / .22;
        vec3 tip = mix(cTip * vec3(.86, 1., .95), cTip * vec3(1.08, 1.04, .78), hue);
        vec3 c = mix(cBase * .96, tip, .22 + .78 * k) * (.92 + .08 * hue);   // roots match the ground: reads as a lawn, not as dark spikes
        c *= mix(vec3(.84, .94, .86), vec3(1.1, 1.05, .8), smoothstep(-.8, .8, vVar));
        gl_FragColor = vec4(c, .15);
        #include <colorspace_fragment>
        #include <fog_fragment>
      }` });
  mat.uniforms.hmask = { value: hm };
  mat.depthWrite = false; const m = new THREE.Mesh(geo, mat); m.frustumCulled = false; m.renderOrder = 1; m.userData.grass = mat.uniforms; return m;
}

/* ================================================================== particles (pollen, fireflies, snow, dust, sparks, data motes, rain) */
export function particles(kind, { n = 400, r = 40, color = '#ffffff', size = 6, hmin = .3, hmax = 12 } = {}) {
  const R = rng(kind.length * 31), pos = new Float32Array(n * 3), seed = new Float32Array(n);
  for (let i = 0; i < n; i++) { pos.set([(R() - .5) * 2 * r, hmin + R() * (hmax - hmin), (R() - .5) * 2 * r], i * 3); seed[i] = R(); }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(pos, 3)); g.setAttribute('seed', new THREE.BufferAttribute(seed, 1));
  const K = { pollen: 0, firefly: 1, snow: 2, dust: 3, spark: 4, mote: 5, rain: 6 }[kind] ?? 0;
  const m = new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, blending: K === 6 || K === 2 ? THREE.NormalBlending : THREE.AdditiveBlending,
    uniforms: { amt: { value: 1 }, time: { value: 0 }, center: { value: new THREE.Vector3() }, r: { value: r }, c: { value: col(color) }, size: { value: size * Math.min(devicePixelRatio, 1.5) }, kind: { value: K }, hr: { value: new THREE.Vector2(hmin, hmax) } },
    vertexShader: `uniform float time, r, size, kind, amt; uniform vec3 center; uniform vec2 hr; attribute float seed; varying float vA;
      void main(){ vec3 p = position; float t = time;
        float fall = kind == 2. ? t * (.8 + seed) : kind == 6. ? t * (14. + seed * 6.) : 0.;
        p.y = hr.x + mod(p.y - hr.x - fall + (kind == 3. || kind == 0. ? sin(t * .3 + seed * 20.) * .6 : 0.), hr.y - hr.x);
        p.x += sin(t * (.3 + seed * .5) + seed * 30.) * (kind == 1. ? 1.4 : kind == 6. ? 0. : .8) + (kind == 3. ? t * 1.6 : 0.);
        p.z += cos(t * (.25 + seed * .4) + seed * 17.) * (kind == 1. ? 1.4 : .8);
        p.xz = center.xz + mod(p.xz - center.xz + r, 2. * r) - r;           // wrap around the player
        vec4 mv = modelViewMatrix * vec4(p, 1.);
        vA = kind == 1. ? (.35 + .65 * pow(.5 + .5 * sin(t * (1.5 + seed * 2.) + seed * 40.), 3.)) : kind == 4. ? step(.93, fract(t * .7 + seed * 5.)) : 1.;
        vA *= smoothstep(r, r * .6, length(p.xz - center.xz)) * step(seed, amt);
        gl_PointSize = size * (kind == 6. ? .8 : 1.) * (18. / -mv.z) * (.6 + seed * .8); gl_Position = projectionMatrix * mv; }`,
    fragmentShader: `uniform vec3 c; uniform float kind; varying float vA;
      void main(){ vec2 q = gl_PointCoord - .5; float d = length(q);
        float a = kind == 6. ? (1. - smoothstep(.02, .06, abs(q.x))) * (1. - smoothstep(.3, .5, abs(q.y))) * .5 : smoothstep(.5, .0, d);
        if (a < .01) discard; gl_FragColor = vec4(c, a * vA * (kind == 2. ? .9 : kind == 3. ? .35 : .85)); }`,
  });
  const pts = new THREE.Points(g, m); pts.frustumCulled = false; pts.renderOrder = 5;
  pts.userData.amt = m.uniforms.amt; pts.userData.kind = kind; pts.userData.tick = (t, center) => { m.uniforms.time.value = t; if (center) m.uniforms.center.value.copy(center); };
  return pts;
}


/* comic-book look (The Wolf Among Us style): depth + colour ink lines, soft cel bands, halftone in the shadows */
export const ComicShader = {
  uniforms: { tDiffuse: { value: null }, tDepth: { value: null }, res: { value: new THREE.Vector2(1, 1) }, cNear: { value: .1 }, cFar: { value: 400 },
    ink: { value: 1 }, bands: { value: 4 }, cel: { value: .5 }, halftone: { value: 1 }, lineW: { value: 1 }, inkCol: { value: new THREE.Color('#140c1c') }, inkFar: { value: 120 } },
  vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.); }`,
  fragmentShader: `#include <packing>
    uniform sampler2D tDiffuse, tDepth; uniform vec2 res; uniform float cNear, cFar, ink, bands, cel, halftone, lineW, inkFar; uniform vec3 inkCol; varying vec2 vUv;
    float lin(vec2 uv){ return -perspectiveDepthToViewZ(texture2D(tDepth, uv).x, cNear, cFar); }
    vec3 tm(vec3 x){ return x / (1. + x); }
    void main(){
      vec2 px = lineW / res;
      float c = lin(vUv), l = lin(vUv - vec2(px.x, 0.)), r = lin(vUv + vec2(px.x, 0.)), u = lin(vUv + vec2(0., px.y)), d = lin(vUv - vec2(0., px.y));
      float cc = max(c, .6), sky = step(cFar * .97, c);
      float dmax = max(max(abs(l - c), abs(r - c)), max(abs(u - c), abs(d - c)));
      float sil = smoothstep(.05, .11, dmax / cc);                       // silhouettes (depth jumps)
      float crease = smoothstep(.035, .08, abs(l + r + u + d - 4. * c) / cc) * (1. - sky); // creases / folds
      vec3 col = texture2D(tDiffuse, vUv).rgb;
      vec3 cl = tm(texture2D(tDiffuse, vUv - vec2(px.x, 0.)).rgb), cr = tm(texture2D(tDiffuse, vUv + vec2(px.x, 0.)).rgb);
      vec3 cu = tm(texture2D(tDiffuse, vUv + vec2(0., px.y)).rgb), cd = tm(texture2D(tDiffuse, vUv - vec2(0., px.y)).rgb);
      float ce = smoothstep(.3, .5, length(cr - cl) + length(cu - cd)) * (1. - sky);  // colour edges (clothes, windows, trims)
      float fade = 1. - smoothstep(inkFar * .35, inkFar, c);
      float e = clamp(max(sil, max(crease * .6, ce * .35)) * fade * ink, 0., 1.);
      // soft cel bands on luminance (geometry only, the sky stays smooth)
      float L = dot(col, vec3(.2126, .7152, .0722)), Lt = L / (1. + L);
      float st = Lt * bands, q = (floor(st) + smoothstep(.3, .7, fract(st))) / bands; q = min(q, .94);
      float Lq = q / (1. - q);
      col *= mix(1., Lq / max(L, 1e-4), cel * (1. - sky));
      // halftone dots creeping into the shadows
      vec2 g = gl_FragCoord.xy / (5. * lineW); float dm = length(fract(g) - .5);
      float rad = (1. - smoothstep(.03, .2, Lt)) * .42;
      col *= 1. - halftone * smoothstep(rad + .06, rad - .06, dm) * .3 * fade * (1. - sky);
      col = mix(col, inkCol, e);
      gl_FragColor = vec4(col, 1.);
    }`,
};

/* ================================================================== post-processing chain (quality aware) */
const GradeShader = {
  uniforms: { tDiffuse: { value: null }, res: { value: new THREE.Vector2(1, 1) }, vig: { value: .28 }, sat: { value: 1.12 }, tint: { value: new THREE.Vector3(1, 1, 1) }, fxaa: { value: 1 }, shTint: { value: new THREE.Color('#5a4a8a') }, hiTint: { value: new THREE.Color('#ffe6c8') }, split: { value: .22 } },
  vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.); }`,
  fragmentShader: `uniform sampler2D tDiffuse; uniform vec2 res; uniform float vig, sat, fxaa, split; uniform vec3 tint, shTint, hiTint; varying vec2 vUv;
    vec3 fx(vec2 uv){ // compact FXAA (luma edge blur)
      vec2 px = 1. / res; vec3 m = texture2D(tDiffuse, uv).rgb;
      if (fxaa < .5) return m;
      vec3 nw = texture2D(tDiffuse, uv + vec2(-1.,-1.) * px).rgb, ne = texture2D(tDiffuse, uv + vec2(1.,-1.) * px).rgb, sw = texture2D(tDiffuse, uv + vec2(-1.,1.) * px).rgb, se = texture2D(tDiffuse, uv + vec2(1.,1.) * px).rgb;
      vec3 L = vec3(.299,.587,.114); float lNW = dot(nw,L), lNE = dot(ne,L), lSW = dot(sw,L), lSE = dot(se,L), lM = dot(m,L);
      float lMin = min(lM, min(min(lNW,lNE), min(lSW,lSE))), lMax = max(lM, max(max(lNW,lNE), max(lSW,lSE)));
      vec2 dir = vec2(-((lNW + lNE) - (lSW + lSE)), ((lNW + lSW) - (lNE + lSE)));
      float red = max((lNW + lNE + lSW + lSE) * .03125, 1./128.); float rcp = 1. / (min(abs(dir.x), abs(dir.y)) + red);
      dir = clamp(dir * rcp, -8., 8.) * px;
      vec3 a = .5 * (texture2D(tDiffuse, uv + dir * (1./3. - .5)).rgb + texture2D(tDiffuse, uv + dir * (2./3. - .5)).rgb);
      vec3 b = a * .5 + .25 * (texture2D(tDiffuse, uv - dir * .5).rgb + texture2D(tDiffuse, uv + dir * .5).rgb);
      float lB = dot(b, L); return (lB < lMin || lB > lMax) ? a : b; }
    void main(){ vec3 c = fx(vUv);
      float l = dot(c, vec3(.299,.587,.114)); c = mix(vec3(l), c, sat) * tint;
      vec3 tone = mix(shTint, hiTint, smoothstep(.12, .75, l)); c = mix(c, c * tone * 1.6, split * (1. - abs(l - .5)));
      vec2 q = vUv - .5; c *= 1. - vig * smoothstep(.25, .85, length(q * vec2(1.1, 1.)));
      gl_FragColor = vec4(c, 1.); }`,
};
export function makePost(renderer, scene, camera, quality, { comic = true } = {}) {
  const size = renderer.getDrawingBufferSize(new THREE.Vector2());
  const rt = new THREE.WebGLRenderTarget(size.x, size.y, { type: THREE.HalfFloatType, samples: quality === 'high' ? 4 : 0 });
  rt.depthTexture = new THREE.DepthTexture(size.x, size.y); rt.depthTexture.type = THREE.UnsignedIntType;
  const comp = new EffectComposer(renderer, rt);
  { const d2 = new THREE.DepthTexture(size.x, size.y); d2.type = THREE.UnsignedIntType; comp.renderTarget2.depthTexture = d2; } // own depth per buffer: no sampling/feedback loop
  comp.addPass(new RenderPass(scene, camera));
  let ao = null;
  if (quality === 'high') { try { ao = new N8AOPass(scene, camera, size.x, size.y); ao.configuration.aoRadius = 2.2; ao.configuration.distanceFalloff = 1.2; ao.configuration.intensity = 2.4; ao.configuration.halfRes = true; ao.configuration.gammaCorrection = false; ao.configuration.color = new THREE.Color('#1a1426'); comp.addPass(ao); } catch (e) { console.warn('[post] N8AO unavailable', e); ao = null; } }
  const ink = new ShaderPass(ComicShader); ink.enabled = comic; comp.addPass(ink);
  const bloom = new UnrealBloomPass(new THREE.Vector2(size.x / 2, size.y / 2), .32, .45, .92); bloom.enabled = quality !== 'low'; comp.addPass(bloom);
  comp.addPass(new OutputPass());
  const grade = new ShaderPass(GradeShader); grade.uniforms.fxaa.value = quality === 'high' ? 0 : 1; comp.addPass(grade);
  const syncDepth = () => { ink.uniforms.tDepth.value = comp.readBuffer.depthTexture; ink.uniforms.cNear.value = camera.near; ink.uniforms.cFar.value = camera.far; };
  return {
    comp, bloom, ao, grade, ink,
    setSize(w, h) { comp.setSize(w, h); const s = renderer.getDrawingBufferSize(new THREE.Vector2()); grade.uniforms.res.value.set(s.x, s.y); ink.uniforms.res.value.set(s.x, s.y); ink.uniforms.lineW.value = Math.max(1.2, s.y / 600); bloom.setSize(Math.round(s.x / 2), Math.round(s.y / 2)); ao?.setSize(s.x, s.y); },
    look(A) { const g = grade.uniforms; g.sat.value = A.sat ?? 1.12; g.vig.value = A.vig ?? .3; g.tint.value.set(...(A.tint || [1, 1, 1])); bloom.strength = A.bloom ?? .32;
      g.shTint.value.set(A.shTint || '#5a4a8a'); g.hiTint.value.set(A.hiTint || '#ffe6c8'); g.split.value = A.split ?? .22;
      ink.uniforms.inkCol.value.set(A.ink || '#140c1c'); ink.uniforms.inkFar.value = A.inkFar || 120; },
    setComic(v) { ink.enabled = v; },
    render(dt) { syncDepth(); comp.render(dt); },
    dispose() { rt.dispose(); comp.dispose?.(); },
  };
}

/* sky-based environment light for PBR props (PMREM of a tiny gradient scene) */
export function envFromSky(renderer, A) {
  const pm = new THREE.PMREMGenerator(renderer), s = new THREE.Scene();
  const m = new THREE.ShaderMaterial({ side: THREE.BackSide, uniforms: { a: { value: col(A.sky[0]) }, b: { value: col(A.sky[1]) }, g: { value: col(A.ground[1]) } },
    vertexShader: 'varying vec3 d; void main(){ d = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.); }',
    fragmentShader: 'uniform vec3 a,b,g; varying vec3 d; void main(){ vec3 c = d.y > 0. ? mix(b, a, smoothstep(0.,.6,d.y)) : mix(b, g * .6, smoothstep(0.,-.3,d.y)); gl_FragColor = vec4(c,1.); }' });
  s.add(new THREE.Mesh(new THREE.SphereGeometry(10, 32, 16), m));
  const tex = pm.fromScene(s, 0, .1, 100).texture; pm.dispose(); m.dispose(); return tex;
}
