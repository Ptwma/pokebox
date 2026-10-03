// Pokebox — card creatures: your companion (and wild Echoes) ARE the Pokémon printed on the card.
// The card art is cut out into a die-cut paper sticker (see cutout.js) and brought to life Paper-Mario style:
// it always faces the camera, flips like paper when it changes direction, hops when it walks, breathes when idle,
// and carries a type aura (embers, bubbles, leaves, sparks...). Wild Echoes use the same sticker with a glitch shader
// until you beat them — then they "stabilise". Cards that can't be cut out cleanly become a living, floating card.
import * as THREE from 'three';
import { sticker } from './cutout.js';

export const TYPE_COL = { Fire: '#ff6a3d', Water: '#3fa7ff', Grass: '#5fcf5a', Lightning: '#ffd23f', Psychic: '#c46bff', Fighting: '#e0763a',
  Darkness: '#8a6ae8', Metal: '#b8c6d4', Dragon: '#e0b040', Colorless: '#f0ece0', Fairy: '#ff8fd0' };

const VS = /* glsl */`varying vec2 vUv; varying float vFogDepth;
  void main(){ vUv = uv; vec4 mv = modelViewMatrix * vec4(position, 1.); vFogDepth = -mv.z; gl_Position = projectionMatrix * mv; }`;
const FS = /* glsl */`uniform sampler2D map; uniform float time, echo, back, flash, round, ready; uniform vec3 tint, fogColor; uniform float fogNear, fogFar; varying vec2 vUv; varying float vFogDepth;
  float hs(float x){ return fract(sin(x * 91.7) * 43758.5); }
  void main(){
    vec2 uv = vUv;
    if (echo > .01) { float row = floor(uv.y * 40.), g = step(.92, hs(row + floor(time * 12.))) * echo; uv.x += (hs(row * 3.1 + floor(time * 20.)) - .5) * .12 * g; }
    if (back > .5) uv.x = 1. - uv.x;
    vec4 t = texture2D(map, uv);
    float a = t.a;
    if (round > .5) { vec2 q = abs(vUv - .5) - vec2(.5 - .06, .5 - .045); a *= step(length(max(q, 0.)) , .045); }
    if (a < .5) discard;
    vec3 c = t.rgb;
    if (back > .5) { c = mix(vec3(.9, .87, .8), tint * .8 + .15, .18) * (.92 + .08 * hs(floor(vUv.x * 60.) + floor(vUv.y * 60.) * 7.)); }
    if (echo > .01) {
      float r = texture2D(map, uv + vec2(.012, 0.) * echo).r, b = texture2D(map, uv - vec2(.012, 0.) * echo).b; c = mix(c, vec3(r, c.g, b), echo);
      float scan = .78 + .22 * sin(gl_FragCoord.y * 1.4 - time * 9.); c = mix(c, (c * .4 + tint * .75) * scan, echo * .62);
      c *= .85 + .3 * step(.97, hs(floor(time * 15.))) * echo;
    }
    if (back < .5) {
      // light the paper like an object in the scene: soft top-to-bottom falloff + a rim of key light on the upper-left
      // edges (sampled from the cut-out's alpha) so the creature separates from busy grass and reads as a shape
      vec2 o = vec2(.014, .011);
      float aL = texture2D(map, uv + vec2(-o.x, 0.)).a, aU = texture2D(map, uv + vec2(0., o.y)).a, aR = texture2D(map, uv + vec2(o.x, 0.)).a, aD = texture2D(map, uv - vec2(0., o.y)).a;
      float key = clamp((1. - aL) * .8 + (1. - aU), 0., 1.), fill = clamp((1. - aR) + (1. - aD), 0., 1.) * .35;
      c *= mix(.84, 1.05, smoothstep(0., 1., vUv.y));
      c += (key * mix(vec3(1., .96, .86), tint, .25) * .34 + fill * tint * .22) * (1. - round);
    }
    c = mix(c, vec3(1.), flash);
    float f = smoothstep(fogNear, fogFar, vFogDepth); c = mix(c, fogColor, f * .85);
    gl_FragColor = vec4(c, 1.);
    #include <colorspace_fragment>
  }`;

/* ---- rare / strong creature: a pulsing neon rim that follows the sticker's silhouette */
const GLOW_FS = /* glsl */`uniform sampler2D map; uniform vec3 col; uniform float time, on; varying vec2 vUv; varying float vFogDepth;
  void main(){ vec2 uv = vec2((vUv.x - .5) * 1.12 + .5, vUv.y * 1.08); float a = 0.;
    for (int i = 0; i < 12; i++) { float t = float(i) / 12. * 6.2832; a = max(a, texture2D(map, uv + vec2(cos(t), sin(t)) * .028).a); }
    float inner = texture2D(map, uv).a; float rim = clamp(a - inner * .85, 0., 1.);
    float pulse = .65 + .35 * sin(time * 3.2); if (rim * on < .02) discard; gl_FragColor = vec4(col * (1.6 + pulse), rim * on * pulse); }`;
/* ---- type aura: a few dozen additive points with per-type motion */
const AURA = { Fire: [0, '#ffb04a'], Water: [1, '#9fdcff'], Grass: [2, '#9df07a'], Lightning: [3, '#fff27a'], Psychic: [4, '#e1a6ff'], Fighting: [5, '#ffc08a'],
  Darkness: [6, '#b49aff'], Metal: [7, '#ffffff'], Dragon: [4, '#ffd780'], Colorless: [5, '#fff6e0'], Fairy: [7, '#ffc2ea'] };
function aura(type, n = 26) {
  const [mode, color] = AURA[type] || AURA.Colorless, seed = new Float32Array(n), pos = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) seed[i] = Math.random();
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(pos, 3)); g.setAttribute('seed', new THREE.BufferAttribute(seed, 1));
  const m = new THREE.ShaderMaterial({ transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    uniforms: { time: { value: 0 }, c: { value: new THREE.Color(color) }, mode: { value: mode }, H: { value: 1.2 }, W: { value: .7 }, k: { value: 1 } },
    vertexShader: `attribute float seed; uniform float time, mode, H, W, k; varying float vA;
      void main(){ float s = seed, t = time * (.6 + s * .6) + s * 20.; vec3 p;
        float ph = fract(t * .35);
        if (mode < .5) { p = vec3(sin(s * 40. + t) * W * .6, ph * H * 1.3, cos(s * 30.) * .3); vA = 1. - ph; }                       // embers rise
        else if (mode < 1.5) { p = vec3(sin(s * 50.) * W * .7 + sin(t * 2.) * .05, ph * H * 1.2, cos(s * 20.) * .3); vA = sin(ph * 3.14); }  // bubbles
        else if (mode < 2.5) { p = vec3(sin(t * .9 + s * 9.) * W, H * (1. - ph) * 1.1, cos(t * .7 + s * 5.) * .4); vA = sin(ph * 3.14); }   // leaves fall & sway
        else if (mode < 3.5) { p = vec3((s - .5) * W * 1.6, fract(s * 7.) * H, sin(s * 13.) * .3); vA = step(.8, fract(t * 1.7 + s)); }    // sparks flicker
        else if (mode < 4.5) { float a = t * 1.6 + s * 6.28; p = vec3(cos(a) * W * .9, H * (.2 + .6 * fract(s * 3.)), sin(a) * W * .5); vA = .8; } // orbit
        else if (mode < 5.5) { p = vec3(sin(s * 44.) * W * .9, ph * .5, cos(s * 17.) * .4); vA = (1. - ph) * .6; }                     // ground dust
        else if (mode < 6.5) { p = vec3(sin(s * 40. + t * .5) * W * .8, ph * H, cos(s * 30.) * .35); vA = sin(ph * 3.14) * .7; }        // shadow wisps
        else { p = vec3((fract(s * 11.) - .5) * W * 1.6, fract(s * 5.) * H, (fract(s * 3.) - .5) * .4); vA = pow(max(0., sin(t * 3. + s * 30.)), 12.); } // glints
        vA *= k; vec4 mv = modelViewMatrix * vec4(p, 1.); gl_PointSize = min((mode > 5.5 && mode < 6.5 ? 60. : 26.) * (.5 + s) / max(-mv.z, .5), 34.); gl_Position = projectionMatrix * mv; }`,
    fragmentShader: `uniform vec3 c; uniform float mode; varying float vA; void main(){ vec2 q = gl_PointCoord - .5; float d = length(q);
      float a = mode > 6.5 ? max(1. - smoothstep(0., .05, abs(q.x)) , 1. - smoothstep(0., .05, abs(q.y))) * (1. - d * 2.) : smoothstep(.5, 0., d);
      if (a * vA < .01) discard; gl_FragColor = vec4(c * (mode > 5.5 && mode < 6.5 ? .35 : 1.), a * vA); }` });
  const p = new THREE.Points(g, m); p.frustumCulled = false; p.renderOrder = 7; return p;
}

const loader = new THREE.TextureLoader();
/**
 * card: { i, f, n, t } (DB card), url: image url.
 * opts.size: height in world units; opts.echo: glitchy wild Echo; opts.fog: THREE.Fog to follow.
 */
export function makeCardPet(card, url, { size = 1.25, echo = false } = {}) {
  const type = card.t || 'Colorless', tint = new THREE.Color(TYPE_COL[type] || '#fff');
  const g = new THREE.Group(), body = new THREE.Group(); g.add(body);
  const U = { map: { value: new THREE.Texture() }, time: { value: 0 }, echo: { value: echo ? 1 : 0 }, back: { value: 0 }, flash: { value: 0 }, round: { value: 0 }, ready: { value: 0 },
    tint: { value: tint }, fogColor: { value: new THREE.Color('#000') }, fogNear: { value: 1e4 }, fogFar: { value: 2e4 } };
  const mk = back => new THREE.ShaderMaterial({ uniforms: { ...U, back: { value: back } }, vertexShader: VS, fragmentShader: FS, side: THREE.FrontSide });
  const front = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), mk(0)), rear = new THREE.Mesh(front.geometry, mk(1));
  rear.rotation.y = Math.PI; rear.position.z = -.018; front.renderOrder = rear.renderOrder = 3;
  body.add(front, rear); body.visible = false;
  const blob = new THREE.Mesh(new THREE.CircleGeometry(.42, 20), new THREE.MeshBasicMaterial({ color: '#000', transparent: true, opacity: .25, depthWrite: false }));
  blob.rotation.x = -Math.PI / 2; blob.position.y = .03; g.add(blob);
  const au = aura(type); g.add(au);
  const GU = { map: U.map, col: { value: new THREE.Color('#ff2a3a') }, time: U.time, on: { value: 0 } };
  const glow = new THREE.Mesh(front.geometry, new THREE.ShaderMaterial({ uniforms: GU, vertexShader: VS, fragmentShader: GLOW_FS, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
  glow.position.z = -.01; glow.scale.set(1.12, 1.08, 1); glow.renderOrder = 2; glow.visible = false; body.add(glow);
  let w = size * .8, hgt = size, living = false;
  const setMap = (tex, aspect, isCard) => {
    tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 4; U.map.value = tex; living = isCard;
    hgt = isCard ? size * 1.05 : size; w = hgt * aspect; if (w > size * 1.25) { w = size * 1.25; hgt = w / aspect; }
    front.geometry.dispose(); const geo = new THREE.PlaneGeometry(w, hgt); geo.translate(0, hgt / 2, 0); front.geometry = rear.geometry = geo; if (typeof glow !== 'undefined') glow.geometry = geo;
    front.material.uniforms.round.value = rear.material.uniforms.round.value = isCard ? 1 : 0;
    au.material.uniforms.H.value = hgt; au.material.uniforms.W.value = w * .6; blob.scale.setScalar(Math.max(.7, w * .9));
    body.visible = true;
  };
  // show the living card at once, swap to the die-cut sticker when the cutout is ready (cached after the first time)
  // the Pokémon only ever appears as its die-cut figure: until the cutout is ready it stays hidden (it pops in when ready);
  // the flat card is only a last resort when the art can't be cut out at all (or the cutout never arrives)
  let cut = false, cardTex = null, fell = false;
  const fallback = () => { if (cut || fell) return; fell = true; if (cardTex) setMap(cardTex, cardTex.image.width / cardTex.image.height, true); else loader.load(url, t => { if (!cut) setMap(t, t.image.width / t.image.height, true); else t.dispose(); }); };
  loader.load(url, t => { if (cut) t.dispose(); else cardTex = t; });
  const fbT = setTimeout(fallback, 25000);
  const ready = sticker(card, url, { priority: !echo }).then(r => {
    if (!r.ok) { clearTimeout(fbT); fallback(); return; } cut = true; clearTimeout(fbT); if (cardTex && !fell) { cardTex.dispose(); cardTex = null; }
    const c = document.createElement('canvas'); c.width = r.w; c.height = r.h; c.getContext('2d').drawImage(r.bitmap, 0, 0);
    const old = U.map.value; setMap(new THREE.CanvasTexture(c), r.w / r.h, false); if (old !== U.map.value) old.dispose?.();
  }).catch(() => { clearTimeout(fbT); fallback(); });

  // animation state
  let ph = Math.random() * 6, face = 1, faceS = 1, hop = 0, stab = null, lastX = 0;
  const cam = new THREE.Vector3(), tmp = new THREE.Vector3();
  return {
    group: g, card, type, ready, isCardPet: true, get living() { return living; },
    get fly() { return false; },
    /** speed: ground speed; camera: to face; t: time; mv: world-space velocity (for paper flips) */
    update(dt, speed, t, camera, mv) {
      U.time.value = t; au.material.uniforms.time.value = t;
      if (camera) { camera.getWorldPosition(cam); g.getWorldPosition(tmp); body.rotation.y = Math.atan2(cam.x - tmp.x, cam.z - tmp.z) - g.rotation.y;
        if (mv && mv.lengthSq() > .04) { // which way is it walking on screen? flip like paper when that changes
          const right = new THREE.Vector3(Math.cos(Math.atan2(cam.x - tmp.x, cam.z - tmp.z)), 0, -Math.sin(Math.atan2(cam.x - tmp.x, cam.z - tmp.z)));
          const sx = mv.x * right.x + mv.z * right.z; if (Math.abs(sx) > .25) face = sx > 0 ? -1 : 1; } }
      faceS += (face - faceS) * Math.min(1, dt * 10);
      ph += dt * (speed > .3 ? 4 + speed * 1.8 : 1.6);
      const moving = speed > .3; hop += ((moving ? 1 : 0) - hop) * Math.min(1, dt * 6);
      const jump = Math.abs(Math.sin(ph)) * .22 * hop * (living ? .6 : 1), squash = 1 - (1 - Math.abs(Math.sin(ph))) * .08 * hop;
      const breathe = 1 + Math.sin(ph) * .025 * (1 - hop);
      body.position.y = jump + (living ? .35 + Math.sin(t * 1.8 + lastX) * .08 : 0);
      body.scale.set(faceS * (2 - squash) / breathe, squash * breathe, 1);
      body.rotation.z = (living ? Math.sin(t * 1.3) * .06 : Math.sin(ph) * .06 * hop);
      blob.material.opacity = .25 - jump * .4;
      if (stab) this._stab(dt);
    },
    setFlash(v) { U.flash.value = v; },
    /** neon rim for rare / high-level creatures (red by default) */
    setGlow(v, color) { GU.on.value = v ? 1 : 0; glow.visible = !!v; if (color) GU.col.value.set(color); },
    get size() { return { w, h: hgt }; },
    setEcho(v) { U.echo.value = v; front.material.uniforms.echo.value = rear.material.uniforms.echo.value = v; },
    setFog(fog) { if (!fog) return; for (const m of [front.material, rear.material]) { m.uniforms.fogColor.value.copy(fog.color); m.uniforms.fogNear.value = fog.near; m.uniforms.fogFar.value = fog.far; } },
    /** wild Echo -> stable card creature: glitch melts away, white flash, pop */
    stabilise(done) { stab = { t: 0, done }; },
    _stab(dt) {
      stab.t += dt; const k = stab.t;
      const e = Math.max(0, 1 - k / 1.1); front.material.uniforms.echo.value = rear.material.uniforms.echo.value = e;
      const fl = k < 1.1 ? 0 : Math.max(0, 1 - (k - 1.1) / .5); front.material.uniforms.flash.value = fl;
      au.material.uniforms.k.value = 1 + (k < 1.4 ? k * 2 : 0);
      if (k > 1.1 && k < 1.35) body.scale.multiplyScalar(1 + (k - 1.1) * 1.2);
      if (k > 2.2) { const d = stab.done; stab = null; d?.(); }
    },
    dispose() { front.geometry.dispose(); front.material.dispose(); rear.material.dispose(); au.geometry.dispose(); au.material.dispose(); U.map.value?.dispose?.(); },
  };
}
