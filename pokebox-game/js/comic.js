// Pokebox — graphic-novel renderer ("dark cinematic comic" look).
// Three layers designed together:
//   1) comicify(): patches every lit MeshStandardMaterial with a custom light model — 3 hard cel bands
//      (light / mid / deep dark), brushy terminator, flat crisp cast shadows, crosshatching in the mid/dark
//      bands, painted albedo breakup, stepped highlights and a light-aligned rim.
//   2) addInkHull(): inverted-hull ink outlines on characters & pets (thick, pixel-sized, fade with distance).
//   3) createComicPost(): one full-screen pass — depth silhouettes + depth creases + colour edges with
//      hand-drawn line weight and a slow "boil", filmic tone curve with crushed blacks, desaturation,
//      warm/cool split toning, paper grain and vignette.
// Shading ideas (ToonSharpen, light-aligned rim, hatching thresholds, zero ambient in shadow) adapted from
// "Dark Comic Master" by Andicraft (CC-BY 4.0) — see assets/LICENSE-DarkComic.txt.
import * as THREE from 'three';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';

/* ---------------------------------------------------------------- shared uniforms (one set for every material) */
export const CU = {
  cTime: { value: 0 }, cRes: { value: new THREE.Vector2(1280, 720) },
  cShadow: { value: new THREE.Color('#2c2a52') },   // colour of the dark band (multiplied with albedo)
  cMid: { value: new THREE.Color('#8a7fa8') },      // colour of the mid band
  cLit: { value: new THREE.Color('#ffe8cc') },      // warm key light tint
  cRim: { value: new THREE.Color('#ffd7a0') },
  cDark: { value: .3 }, cMidK: { value: .6 }, cSunK: { value: .38 },
  cHatch: { value: 1 }, cPaint: { value: 1 }, cOn: { value: 1 }, cToon: { value: 1 },
};

const COMMON = /* glsl */`
  uniform float cTime, cDark, cMidK, cSunK, cHatch, cPaint, cOn, cToon; uniform vec2 cRes; uniform vec3 cShadow, cMid, cLit, cRim;
  varying vec3 vCW; varying vec3 vCC;
  float cH3(vec3 p){ p = fract(p * .3183099 + .1); p *= 17.; return fract(p.x * p.y * p.z * (p.x + p.y + p.z)); }
  float cN3(vec3 x){ vec3 i = floor(x), f = fract(x); f = f * f * (3. - 2. * f);
    return mix(mix(mix(cH3(i), cH3(i + vec3(1,0,0)), f.x), mix(cH3(i + vec3(0,1,0)), cH3(i + vec3(1,1,0)), f.x), f.y),
               mix(mix(cH3(i + vec3(0,0,1)), cH3(i + vec3(1,0,1)), f.x), mix(cH3(i + vec3(0,1,1)), cH3(i + vec3(1,1,1)), f.x), f.y), f.z); }
  float cSharp(float x, float e){ float w = max(fwidth(x) * .75, .012); return smoothstep(e - w, e + w, x); }
  // one family of ink hatch lines; coverage grows as the tone darkens, fades out when lines get sub-pixel
  float cLines(vec2 p, float dens, float cover){ float f = abs(fract(p.x * dens) - .5) * 2.; float w = fwidth(p.x * dens) * 2.;
    return (1. - smoothstep(cover - w, cover + w, f)) * (1. - smoothstep(.35, .6, w)); }
`;

function patch(sh, m) {
  if (sh.vertexShader.includes('varying vec3 vCW;')) return; // already patched (shared/copied onBeforeCompile)
  Object.assign(sh.uniforms, CU);
  const world = m.userData.comicWorld ? 1 : 0, fol = m.userData.foliage ? 1 : 0, act = m.userData.actor ? 1 : 0;
  sh.vertexShader = 'varying vec3 vCW; varying vec3 vCC;\n' + sh.vertexShader.replace('#include <project_vertex>', `
    { vec4 cw = vec4(transformed, 1.); vec4 co = vec4(0., 0., 0., 1.);
      #ifdef USE_INSTANCING
        cw = instanceMatrix * cw; co = instanceMatrix * co;
      #endif
      cw = modelMatrix * cw; vCW = cw.xyz;
      vec4 cc = projectionMatrix * viewMatrix * modelMatrix * co; vCC = vec3(cc.xy / max(cc.w, .001), cc.w); }
    #include <project_vertex>`);
  sh.fragmentShader = COMMON + sh.fragmentShader.replace('#include <opaque_fragment>', `
    if (cOn > .5 && cToon > .5) {
      // ---- Pokémon-style toon: one soft cel step, bright sky-filled shadows, gentle rim, clean colours
      vec3 alb = diffuseColor.rgb, N = normal, V = normalize(vViewPosition), L = vec3(0., 1., 0.), sunC = vec3(1.);
      #if NUM_DIR_LIGHTS > 0
        L = directionalLights[0].direction; sunC = directionalLights[0].color * cSunK;
      #endif
      float sh = 1.;
      #if defined(USE_SHADOWMAP) && NUM_DIR_LIGHT_SHADOWS > 0
        if (receiveShadow) { DirectionalLightShadow dls = directionalLightShadows[0];
          sh = getShadow(directionalShadowMap[0], dls.shadowMapSize, dls.shadowIntensity, dls.shadowBias, dls.shadowRadius, vDirectionalShadowCoord[0]); }
      #endif
      float ndl = ${fol ? 'dot(normalize(N * .4 + (viewMatrix * vec4(0., 1., 0., 0.)).xyz), L) * .7 + .35' : 'dot(N, L)'};
      float shT = smoothstep(.2, .8, sh); ${fol ? 'shT = .55 + .45 * shT;' : ''}
      // anime ramp: crisp terminator, a thin warm transition band, saturated cool shadows that keep their hue
      float lit = ${act ? 'smoothstep(-.32, -.2, ndl) * mix(1., shT, .65)' : 'smoothstep(-.015, .045, ndl) * shT'};
      float band = smoothstep(-.06, .0, ndl) * (1. - smoothstep(.0, .08, ndl)) * shT;
      vec3 sky = vec3(.55, .62, .8);
      #if NUM_HEMI_LIGHTS > 0
        sky = getHemisphereLightIrradiance(hemisphereLights[0], N) * .42;
      #endif
      vec3 tintN = cShadow / max(max(cShadow.r, cShadow.g), max(cShadow.b, .001));
      vec3 shade = alb * mix(vec3(1.), tintN, .55) * cDark * .92 + alb * sky * .16;
      float sl = dot(shade, vec3(.2126, .7152, .0722)); shade = max(mix(vec3(sl), shade, 1.28), 0.);     // shadows stay colourful
      ${act ? 'shade = alb * mix(vec3(.84, .72, .78), sky * 1.3, .2);   // characters: light, rosy anime shadow (no muddy blue on skin)' : ''}
      vec3 col = mix(shade, alb * sunC * cLit, lit);
      col += alb * vec3(1., .55, .4) * band * ${act ? '.0' : '.22'};                                                    // warm "subsurface" edge of the terminator
      vec3 H = normalize(L + V); float gloss = 1. - clamp(roughnessFactor, 0., 1.);
      col += sunC * smoothstep(.95, .975, dot(N, H)) * gloss * .3 * lit;
      float fres = pow(1. - abs(dot(N, V)), 3.);
      col += (sky * .5 + alb * .3) * fres * .22 * (.4 + .6 * lit);
      ${world || fol ? '' : `
      #ifndef USE_INSTANCING
        // characters & props: thin bright rim (anime key-light rim)
        float rimE = smoothstep(.62, .74, 1. - abs(dot(N, V)));
        col += mix(cLit, vec3(1.), .4) * rimE * .32 * (.35 + .65 * lit);
      #endif`}
      outgoingLight = col + totalEmissiveRadiance;
    } else if (cOn > .5) {
      vec3 alb = diffuseColor.rgb;
      vec3 N = normal, V = normalize(vViewPosition);
      vec3 L = vec3(0., 1., 0.), sunC = vec3(1.);
      #if NUM_DIR_LIGHTS > 0
        L = directionalLights[0].direction; sunC = directionalLights[0].color * cSunK;
      #endif
      float sh = 1.;
      #if defined(USE_SHADOWMAP) && NUM_DIR_LIGHT_SHADOWS > 0
        if (receiveShadow) { DirectionalLightShadow dls = directionalLightShadows[0];
          sh = getShadow(directionalShadowMap[0], dls.shadowMapSize, dls.shadowIntensity, dls.shadowBias, dls.shadowRadius, vDirectionalShadowCoord[0]); }
      #endif
      // anchor for screen-stable strokes: relative to the object's screen centre, so they ride with it
      vec2 ndc = gl_FragCoord.xy / cRes * 2. - 1.;
      vec2 sp = (ndc - vCC.xy) * vec2(cRes.x / cRes.y, 1.) * (cRes.y / 7.5);
      ${world ? 'vec2 hp = vCW.xz * 1.6;' : 'vec2 hp = sp;'}
      float n1 = cN3(vCW * 1.9), n2 = cN3(vCW * 7.3 + 3.1);
      float ndl = ${fol ? 'dot(normalize(N * .5 + (viewMatrix * vec4(0., 1., 0., 0.)).xyz), L) * .6 + .3' : 'dot(N, L)'} + (n1 - .5) * .28 + (n2 - .5) * .1;               // brushy, irregular terminator
      float shs = smoothstep(.34 + (n2 - .5) * .3, .62 + (n2 - .5) * .3, sh);   // flat, crisp, ragged cast shadow
      ${fol ? 'shs = .45 + .55 * shs;' : ''}
      float kL = cSharp(ndl, .06) * shs;                                      // light band
      float kM = cSharp(ndl, -.42);                                           // mid band
      float tone = kL + kM * .5 * (1. - kL) * mix(.7, 1., shs);
      // painted albedo: low-freq value breakup + directional stroke streaks
      float stroke = cN3(vec3(hp.x * .02, hp.y * .16, n1 * 2.));
      alb *= 1. + cPaint * ((n1 - .5) * .22 + (stroke - .5) * .14);
      vec3 amb = vec3(0.);
      #if NUM_HEMI_LIGHTS > 0
        amb = getHemisphereLightIrradiance(hemisphereLights[0], N) * .13;
      #endif
      vec3 tintN = mix(vec3(1.), cShadow / max(max(cShadow.r, cShadow.g), max(cShadow.b, .001)), .5);
      alb = mix(alb, vec3(dot(alb, vec3(.3, .59, .11))), .35 * (1. - kL));   // shadows lose chroma
      vec3 cD = alb * (tintN * cDark * ${fol ? '1.6' : '1.'} + amb);
      vec3 cMd = alb * mix(tintN * .5, sunC * cMid, .6) * cMidK * 1.5;
      vec3 cL = alb * sunC * cLit;
      vec3 col = mix(cD, cMd, kM * mix(.55, 1., shs));
      col = mix(col, cL, kL);
      // crosshatching: first family in the mid band, second family crossing it in the dark band
      float lt = clamp((dot(N, L) * .5 + .5) * mix(.45, 1., shs), 0., 1.);
      vec2 r1 = vec2(hp.x * .7071 + hp.y * .7071, 0.), r2 = vec2(hp.x * .7071 - hp.y * .7071, 0.);
      float fade = 1. - smoothstep(22., 60., vCC.z);
      float h1 = cLines(r1 + (n2 - .5) * .5, .5, (1. - smoothstep(.25, .62, lt)) * .34) * (1. - kL);
      float h2 = cLines(r2 + (n1 - .5) * .5, .5, (1. - smoothstep(.12, .42, lt)) * .3) * (1. - kM);
      float hatch = max(h1, h2) * cHatch * fade * ${fol ? '0.' : '1.'};
      col = mix(col, col * .18, hatch * .8);
      // stepped small highlight (never glossy) + light-aligned rim
      vec3 H = normalize(L + V); float gloss = 1. - clamp(roughnessFactor, 0., 1.);
      col += sunC * cLit * cSharp(dot(N, H), .985 - gloss * .06) * gloss * .45 * shs;
      float fres = 1. - pow(abs(dot(N, V)), 4.), align = clamp(-dot(V, L) * .5 + .5, 0., 1.);
      col += alb * cRim * cSharp(fres, mix(1.01, .72, align)) * align * .55;
      outgoingLight = col + totalEmissiveRadiance;
    }
    #include <opaque_fragment>
    gl_FragColor.a = ${fol ? '.3' : '1.'};`);
}

/** Patch a material for the comic light model (idempotent, keeps any existing onBeforeCompile). */
const seen = new WeakSet();
export function comicify(m) {
  if (!m || seen.has(m)) return m; seen.add(m);
  const ok = m.isMeshStandardMaterial && !m.isMeshPhysicalMaterial && !(m.transparent && m.opacity < .999) && m.blending === THREE.NormalBlending && !m.wireframe;
  if (!ok) return m;
  const prev = m.onBeforeCompile, prevKey = m.customProgramCacheKey;
  m.onBeforeCompile = (sh, r) => { if (prev && prev !== THREE.Material.prototype.onBeforeCompile) prev.call(m, sh, r); patch(sh, m); };
  const base = prevKey && prevKey !== THREE.Material.prototype.customProgramCacheKey ? prevKey.call(m) : '';
  m.customProgramCacheKey = () => base + '|comic' + (m.userData.comicWorld ? 'W' : '') + (m.userData.foliage ? 'F' : '') + (m.userData.actor ? 'A' : '');
  m.envMapIntensity = 0; m.needsUpdate = true;
  return m;
}
export function applyComic(root) {
  root.traverse(o => { if (!o.material || o.userData.inkHull) return; (Array.isArray(o.material) ? o.material : [o.material]).forEach(comicify); });
}

/* ---------------------------------------------------------------- inverted-hull ink outlines for actors */
const hullMat = new THREE.ShaderMaterial({
  uniforms: { cRes: CU.cRes, cW: { value: 2.2 }, cInk: { value: new THREE.Color('#0d0a14') } },
  side: THREE.BackSide,
  vertexShader: /* glsl */`
    #include <common>
    #include <skinning_pars_vertex>
    attribute vec3 inkN; uniform vec2 cRes; uniform float cW; varying float vF;
    void main(){
      vec3 objectNormal = inkN;
      #include <skinbase_vertex>
      #include <skinnormal_vertex>
      #include <begin_vertex>
      #include <skinning_vertex>
      vec4 mv = modelViewMatrix * vec4(transformed, 1.);
      vec4 p = projectionMatrix * mv;
      vec3 vn = normalize(normalMatrix * objectNormal);
      vec2 d = (projectionMatrix * vec4(vn, 0.)).xy; d = d / max(length(d), 1e-4);
      float dist = -mv.z; vF = 1. - smoothstep(18., 30., dist); if (vF < .01) { gl_Position = vec4(2., 2., 2., 1.); return; }
      float w = cW * (cRes.y / 720.) * mix(.55, 1.15, clamp(8. / dist, 0., 1.)) * vF;
      p.xy += d * w * 2. / cRes * p.w;
      p.z += .0008 * p.w;
      gl_Position = p;
    }`,
  fragmentShader: `uniform vec3 cInk; varying float vF; void main(){ if (vF < .02) discard; gl_FragColor = vec4(cInk, 1.); }`,
});
export const INK = hullMat.uniforms;
function smoothNormals(geo) { // averaged normals so the hull does not crack on hard edges
  if (geo.attributes.inkN) return;
  const p = geo.attributes.position, n = geo.attributes.normal, map = new Map(), out = new Float32Array(p.count * 3);
  if (!n) { geo.computeVertexNormals(); }
  const nn = geo.attributes.normal, key = i => `${Math.round(p.getX(i) * 1e4)},${Math.round(p.getY(i) * 1e4)},${Math.round(p.getZ(i) * 1e4)}`;
  for (let i = 0; i < p.count; i++) { const k = key(i); const a = map.get(k) || [0, 0, 0]; a[0] += nn.getX(i); a[1] += nn.getY(i); a[2] += nn.getZ(i); map.set(k, a); }
  for (let i = 0; i < p.count; i++) { const a = map.get(key(i)), l = Math.hypot(...a) || 1; out.set([a[0] / l, a[1] / l, a[2] / l], i * 3); }
  geo.setAttribute('inkN', new THREE.BufferAttribute(out, 3));
}
export function addInkHull(root) {
  const add = [];
  root.traverse(o => { if (!o.isMesh || o.userData.inkHull || o.userData.hasHull || o.material?.transparent) return; add.push(o); });
  for (const o of add) {
    smoothNormals(o.geometry);
    let h;
    if (o.isSkinnedMesh) { h = new THREE.SkinnedMesh(o.geometry, hullMat); h.bind(o.skeleton, o.bindMatrix); h.bindMode = o.bindMode; }
    else h = new THREE.Mesh(o.geometry, hullMat);
    h.userData.inkHull = true; h.castShadow = false; h.receiveShadow = false; h.frustumCulled = o.frustumCulled; h.renderOrder = -1;
    o.userData.hasHull = true; o.add(h);
  }
  return root;
}

/* ---------------------------------------------------------------- final full-screen pass */
const FINAL = {
  uniforms: {
    tCol: { value: null }, tDepth: { value: null }, res: { value: new THREE.Vector2(1, 1) }, cNear: { value: .1 }, cFar: { value: 400 }, time: { value: 0 },
    lineW: { value: 1 }, ink: { value: 1 }, inkCol: { value: new THREE.Color('#0d0a14') }, inkFar: { value: 110 },
    exposure: { value: .95 }, sat: { value: .72 }, contrast: { value: 1.12 }, crush: { value: .035 },
    shTint: { value: new THREE.Color('#2e3a6a') }, hiTint: { value: new THREE.Color('#ffd9a8') }, split: { value: .3 },
    vig: { value: .42 }, grain: { value: .045 }, boil: { value: 1 }, paper: { value: new THREE.Color('#f4ead8') }, toon: { value: 1 },
    sunUv: { value: new THREE.Vector2(.5, .8) }, sunVis: { value: 0 }, sunCol: { value: new THREE.Color('#fff2d0') }, rays: { value: 1 },
  },
  vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = vec4(position.xy, 0., 1.); }`,
  fragmentShader: /* glsl */`
    #include <packing>
    uniform sampler2D tCol, tDepth; uniform vec2 res, sunUv; uniform float cNear, cFar, time, lineW, ink, inkFar, exposure, sat, contrast, crush, split, vig, grain, boil, toon, sunVis, rays;
    uniform vec3 inkCol, shTint, hiTint, paper, sunCol; varying vec2 vUv;
    float lin(vec2 uv){ return -perspectiveDepthToViewZ(texture2D(tDepth, uv).x, cNear, cFar); }
    float hs(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
    float vn(vec2 p){ vec2 i = floor(p), f = fract(p); f = f * f * (3. - 2. * f); return mix(mix(hs(i), hs(i + vec2(1,0)), f.x), mix(hs(i + vec2(0,1)), hs(i + vec2(1,1)), f.x), f.y); }
    vec3 film(vec3 x){ x *= exposure; vec3 a = x * (2.51 * x + .03), b = x * (2.43 * x + .59) + .14; return clamp(a / b, 0., 1.); }
    float lum(vec3 c){ return dot(c, vec3(.2126, .7152, .0722)); }
    void main(){
      float fr = floor(time * 7.) * (1. - toon);                                        // line "boil" at 7 fps like hand-inked frames
      vec2 j = (vec2(vn(vUv * 9. + fr * 1.7), vn(vUv * 9. - fr * 2.3)) - .5) * boil / res * 1.4;
      vec2 uv = vUv + j;
      float c = lin(uv); float sky = step(cFar * .985, c);
      float wv = .75 + .6 * vn(vUv * res / 38. + fr * .31);               // pressure variation along strokes
      float wd = mix(1.35, .75, smoothstep(4., 40., c));                  // nearer = heavier line
      vec2 px = lineW * wv * wd / res;
      float l = lin(uv - vec2(px.x, 0.)), r = lin(uv + vec2(px.x, 0.)), u = lin(uv + vec2(0., px.y)), d = lin(uv - vec2(0., px.y));
      float a1 = lin(uv + px), a2 = lin(uv - px), a3 = lin(uv + vec2(px.x, -px.y)), a4 = lin(uv + vec2(-px.x, px.y));
      float cc = max(c, .5);
      float dmax = max(max(max(abs(l - c), abs(r - c)), max(abs(u - c), abs(d - c))), .7 * max(max(abs(a1 - c), abs(a2 - c)), max(abs(a3 - c), abs(a4 - c))));
      float sil = smoothstep(.035, .08, dmax / cc);
      float lap = abs(l + r + u + d - 4. * c) + .5 * abs(a1 + a2 + a3 + a4 - 4. * c);
      float crease = smoothstep(.03, .07, lap / cc) * (1. - sky);
      vec4 c0 = texture2D(tCol, vUv); vec3 col = c0.rgb;
      vec4 Tl = texture2D(tCol, uv - vec2(px.x, 0.)), Tr = texture2D(tCol, uv + vec2(px.x, 0.)), Tu = texture2D(tCol, uv + vec2(0., px.y)), Td = texture2D(tCol, uv - vec2(0., px.y));
      vec3 tl = film(Tl.rgb), tr = film(Tr.rgb), tu = film(Tu.rgb), td = film(Td.rgb);
      float iw = min(min(c0.a, min(Tl.a, Tr.a)), min(Tu.a, Td.a));
      float ce = smoothstep(.3, .55, abs(lum(tr) - lum(tl)) + abs(lum(tu) - lum(td)) + .35 * (length(tr - tl) + length(tu - td))) * (1. - sky);
      float fade = 1. - smoothstep(inkFar * .3, inkFar, c);
      float e = clamp(max(sil, max(crease * mix(.75, .35, toon), ce * .45 * (1. - toon))) * fade * ink * clamp(iw, 0., 1.), 0., 1.) * (1. - toon); // anime look: no black ink lines
      if (toon > .5) { // cheap edge AA on the colour (FXAA-like blend along luminance edges)
        float ed = smoothstep(.04, .2, abs(lum(Tl.rgb) - lum(Tr.rgb)) + abs(lum(Tu.rgb) - lum(Td.rgb)));
        col = mix(col, (Tl.rgb + Tr.rgb + Tu.rgb + Td.rgb + col * 2.) / 6., ed * .55); }
      // sun shafts: march toward the sun on screen and gather open sky (light shining past trees, roofs and hills)
      if (sunVis > .01 && rays > .5) {
        vec2 dlt = (sunUv - vUv) * (.75 / 14.); vec2 p = vUv + dlt * hs(gl_FragCoord.xy); float acc = 0., wgt = 1.;
        for (int i = 0; i < 14; i++) { p += dlt; acc += step(cFar * .985, lin(clamp(p, 0., 1.))) * wgt; wgt *= .93; }
        float fall = 1. - smoothstep(0., .85, length((vUv - sunUv) * vec2(res.x / res.y, 1.)));
        col += sunCol * acc / 9.2 * fall * fall * sunVis * .22 * (1. - sky * .6);
      }
      // grade: filmic curve (toon: softer shoulder so skies & grass keep their colour), contrast, split toning
      col = toon > .5 ? clamp(1. - exp(-col * exposure * 1.18), 0., 1.) * 1.04 : film(col);
      float L = lum(col);
      col = mix(vec3(L), col, sat);
      col = mix(col, col * shTint * 2.2, split * (1. - smoothstep(.05, .5, L)));
      col = mix(col, col * hiTint * 1.25, split * .8 * smoothstep(.45, 1., L));
      col = clamp((col - crush) / (1. - crush), 0., 1.);
      col = clamp((col - .5) * contrast + .5, 0., 1.);
      col = mix(col, toon > .5 ? mix(col * .22, inkCol, .35) : inkCol, e * mix(1., .85, toon));
      // paper: fibre grain + subtle warm cast, vignette (comic only)
      if (toon < .5) { float g = hs(gl_FragCoord.xy + fr) * .6 + vn(gl_FragCoord.xy * .35) * .4;
      col *= 1. - grain + grain * 2. * g * mix(.6, 1., L);
      col = mix(col, col * paper, .12); }
      vec2 q = vUv - .5; col *= 1. - vig * smoothstep(.3, .85, length(q * vec2(1.15, 1.)));
      col = sRGBTransferOETF(vec4(col, 1.)).rgb;
      gl_FragColor = vec4(col, 1.);
    }`,
};

/** Replaces the old EffectComposer chain: scene -> RT(colour+depth) -> [bloom on high] -> one comic pass -> screen. */
export function createComicPost(renderer, scene, camera, quality) {
  const size = renderer.getDrawingBufferSize(new THREE.Vector2());
  const rt = new THREE.WebGLRenderTarget(size.x, size.y, { type: THREE.HalfFloatType, samples: 0, depthBuffer: true });
  rt.depthTexture = new THREE.DepthTexture(size.x, size.y); rt.depthTexture.type = THREE.UnsignedIntType;
  const mat = new THREE.ShaderMaterial({ ...FINAL, uniforms: THREE.UniformsUtils.clone(FINAL.uniforms), depthTest: false, depthWrite: false });
  const U = mat.uniforms; U.tCol.value = rt.texture; U.tDepth.value = rt.depthTexture;
  const quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), mat); quad.frustumCulled = false;
  const qScene = new THREE.Scene(); qScene.add(quad); const qCam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  const bloom = quality === 'high' ? new UnrealBloomPass(new THREE.Vector2(size.x / 2, size.y / 2), .28, .4, .95) : null;
  let t = 0, n = 0;
  function toonLook(A) { // bright Pokémon look: saturated, clean, soft cool shadows, thin warm-dark lines
    const T = A.toon || {};
    U.inkCol.value.set(T.ink || '#2b2236'); INK.cInk.value.set(T.ink || '#2b2236'); U.inkFar.value = 90;
    U.shTint.value.set(T.cool || '#6f8cd8'); U.hiTint.value.set(T.warm || '#fff1d6');
    U.sat.value = T.sat ?? 1.08; U.split.value = T.split ?? .14; U.vig.value = .2; U.exposure.value = T.exposure ?? (A.night ? 1.15 : 1.02);
    U.contrast.value = 1.07; U.crush.value = .01; U.grain.value = 0;
    CU.cShadow.value.set(T.shadow || (A.night ? '#4a4fa8' : '#6f78d6')); CU.cLit.value.set(T.lit || A.sunColor || '#fff6e8');
    CU.cSunK.value = (T.key ?? (A.night ? .9 : 1.05)) / Math.max(.5, A.sunI || 2.6); CU.cDark.value = T.dark ?? (A.night ? .5 : .62);
    CU.cHatch.value = 0; CU.cPaint.value = 0;
    if (bloom) bloom.strength = (A.bloom ?? .3) * .6;
  }
  const api = {
    U, bloom,
    setSize(w, h) {
      const s = renderer.getDrawingBufferSize(new THREE.Vector2()); rt.setSize(s.x, s.y); U.res.value.set(s.x, s.y); CU.cRes.value.set(s.x, s.y);
      U.lineW.value = Math.max(1, s.y / 720); INK.cW.value = U.toon.value > .5 ? 1.25 : 2.1; bloom?.setSize(Math.round(s.x / 2), Math.round(s.y / 2));
    },
    look(A) {
      if (CU.cToon.value > .5) return toonLook(A);
      const C = A.comic || {};
      CU.cHatch.value = 1; CU.cPaint.value = 1; U.grain.value = .045;
      U.inkCol.value.set(A.ink || '#0d0a14'); INK.cInk.value.set(A.ink || '#0d0a14'); U.inkFar.value = A.inkFar || 110;
      U.shTint.value.set(C.cool || A.shTint || '#2e3a6a'); U.hiTint.value.set(C.warm || A.hiTint || '#ffd9a8');
      U.sat.value = C.sat ?? .66; U.split.value = C.split ?? .38; U.vig.value = C.vig ?? .45; U.exposure.value = C.exposure ?? .95;
      U.contrast.value = C.contrast ?? 1.08; U.crush.value = C.crush ?? .018;
      CU.cShadow.value.set(C.shadow || A.shTint || '#2c2a52'); CU.cMid.value.set(C.mid || '#a497b8'); CU.cLit.value.set(C.lit || A.hiTint || '#ffe8cc');
      CU.cRim.value.set(C.rim || A.hiTint || '#ffd7a0'); CU.cSunK.value = (C.key ?? (A.night ? .95 : 1.08)) / Math.max(.5, A.sunI || 2.6); CU.cDark.value = C.dark ?? (A.night ? .5 : .42);
      if (bloom) bloom.strength = (A.bloom ?? .3) * .8;
    },
    setComic(v) { U.ink.value = v ? 1 : 0; CU.cOn.value = v ? 1 : 0; },
    setStyle(st) { const t = st !== 'comic' ? 1 : 0; CU.cToon.value = t; U.toon.value = t; U.boil.value = 1 - t; },
    render(dt) {
      t += dt; n++; CU.cTime.value = t; U.time.value = t; U.cNear.value = camera.near; U.cFar.value = camera.far;
      if (n % 30 === 1) applyComic(scene);
      renderer.setRenderTarget(rt); renderer.render(scene, camera); const ri = renderer.info.render; api.info = { calls: ri.calls, triangles: ri.triangles };
      if (bloom) bloom.render(renderer, null, rt, dt, false);
      renderer.setRenderTarget(null); renderer.render(qScene, qCam);
    },
    dispose() { rt.dispose(); rt.depthTexture.dispose(); mat.dispose(); quad.geometry.dispose(); bloom?.dispose(); },
  };
  return api;
}
