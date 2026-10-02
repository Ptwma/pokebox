// Pokebox — living universe background (one full-screen shader: nebula, galaxy band, 3 parallax star layers, shooting stars)
// Cheap by design: rendered at reduced resolution, ~30 fps, and fully paused while a pack opening or battle effect covers it.
const BAKE = `precision highp float;
uniform vec2 uRes; uniform float uTime; uniform vec2 uMouse;
float hash(vec2 p){ p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
float noise(vec2 p){ vec2 i = floor(p), f = fract(p); vec2 u = f*f*(3.-2.*f);
  return mix(mix(hash(i), hash(i+vec2(1,0)), u.x), mix(hash(i+vec2(0,1)), hash(i+vec2(1,1)), u.x), u.y); }
float fbm(vec2 p){ float v = 0., a = .5; for (int i = 0; i < 6; i++){ v += a*noise(p); p = mat2(1.6,1.2,-1.2,1.6)*p + 3.1; a *= .5; } return v; }
vec3 stars(vec2 uv, float scale, float seed, float bright, float dens){
  vec2 g = uv * scale, id = floor(g), f = fract(g) - .5;
  float h = hash(id + seed); if (h < dens) return vec3(0.);
  vec2 off = (vec2(hash(id + seed + 1.3), hash(id + seed + 7.1)) - .5) * .7;
  float d = length(f - off) * uRes.y / scale / (.8 + h * .9);
  float tw = .55 + .45 * sin(uTime * (.8 + h * 2.5) + h * 60.);
  float core = exp(-d * d * .9) + exp(-d * 1.6) * .25;
  vec3 tint = mix(vec3(.72, .8, 1.), vec3(1., .86, .72), hash(id + seed + 3.3));
  return tint * core * tw * bright * smoothstep(dens, 1., h) * 2.2;
}
void main(){
  vec2 uv = (gl_FragCoord.xy - .5 * uRes) / uRes.y;
  vec2 p = uv + uMouse * .015;
  float t = uTime * .012;
  // nebula (domain-warped fbm), purple/magenta with a cold blue arm
  vec2 q = vec2(fbm(p * 1.4 + t), fbm(p * 1.4 + vec2(5.2, 1.3) - t));
  vec2 r = vec2(fbm(p * 1.8 + q * 2. + vec2(1.7, 9.2) + t * .6), fbm(p * 1.8 + q * 2. + vec2(8.3, 2.8)));
  float n = fbm(p * 1.6 + r * 1.6);
  float cloud = smoothstep(.3, .62, n);
  vec3 col = mix(vec3(.015, .01, .035), vec3(.36, .08, .5), cloud);
  col = mix(col, vec3(.8, .2, .55), smoothstep(.6, .9, n) * .75);
  col = mix(col, vec3(.12, .36, .85), smoothstep(.42, .75, r.y) * cloud * .75);
  col *= .3 + 2.2 * cloud * cloud;
  // bright core glow of a distant galaxy (upper right)
  col += vec3(.55, .32, .7) * exp(-length((p - vec2(.62, .26)) * vec2(1., 1.8)) * 3.2) * (.35 + .65 * n);
  // dark dust lanes
  col *= .55 + .45 * smoothstep(.25, .6, fbm(p * 3.2 - q));
  // galaxy band
  vec2 bd = normalize(vec2(.55, 1.));
  float band = exp(-pow(dot(p - vec2(.2, 0.), vec2(bd.y, -bd.x)) * 2.4, 2.));
  col += vec3(.4, .32, .55) * band * pow(fbm(p * 7. + 11.), 2.) * 1.1;
  // faint static star dust (baked)
  col += stars(p, 90., 1., .5, .965) * .8;
  // vignette + a warm glow bottom-left (matches the UI accent)
  col += vec3(.35, .06, .2) * exp(-length(uv - vec2(-.9, -.6)) * 2.2) * .35;
  col *= 1. - .45 * dot(uv * .8, uv * .8);
  gl_FragColor = vec4(pow(col, vec3(.95)), 1.);
}`;


// per-frame shader: sample the baked nebula (slight parallax) + twinkling stars + shooting stars — a handful of ALU ops per pixel
const LIVE = `precision highp float;
uniform sampler2D uNeb; uniform vec2 uRes; uniform float uTime; uniform vec2 uMouse;
float hash(vec2 p){ p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
vec3 stars(vec2 uv, float scale, float seed, float bright, float dens){
  vec2 g = uv * scale, id = floor(g), f = fract(g) - .5;
  float h = hash(id + seed); if (h < dens) return vec3(0.);
  vec2 off = (vec2(hash(id + seed + 1.3), hash(id + seed + 7.1)) - .5) * .7;
  float d = length(f - off) * uRes.y / scale / (.8 + h * .9);
  float tw = .55 + .45 * sin(uTime * (.8 + h * 2.5) + h * 60.);
  return mix(vec3(.72, .8, 1.), vec3(1., .86, .72), fract(h * 13.1)) * (exp(-d * d * .9) + exp(-d * 1.6) * .25) * tw * bright * smoothstep(dens, 1., h) * 2.2;
}
void main(){
  vec2 q = gl_FragCoord.xy / uRes;
  vec3 col = texture2D(uNeb, q * .96 + .02 + uMouse * .012).rgb;
  vec2 uv = (gl_FragCoord.xy - .5 * uRes) / uRes.y;
  col += stars(uv + uMouse * .012, 45., 2., .8, .955);
  col += stars(uv + uMouse * .025, 18., 3., 1.2, .94);
  float cyc = 9., k = floor(uTime / cyc), st = mod(uTime, cyc);
  if (st < 1.1) {
    vec2 s0 = vec2(hash(vec2(k, 1.)) * 1.6 - .5, .55 + hash(vec2(k, 2.)) * .2);
    vec2 dir = normalize(vec2(-1., -.45 - hash(vec2(k, 3.)) * .4));
    vec2 rel = uv - (s0 + dir * st * 1.4);
    float along = dot(rel, -dir), across = abs(dot(rel, vec2(-dir.y, dir.x)));
    col += vec3(.9, .85, 1.) * (smoothstep(.35, 0., along) * step(0., along) * exp(-across * 900.) * (1. - st / 1.1) * 1.6 + exp(-length(rel) * 260.) * 2.);
  }
  gl_FragColor = vec4(col, 1.);
}`;

export function startSpace(canvas, isPaused = () => false) {
  const gl = canvas.getContext('webgl', { antialias: false, alpha: false, powerPreference: 'low-power', preserveDrawingBuffer: false });
  if (!gl) return null;
  const sh = (type, src) => { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s); if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s)); return s; };
  const VS = 'attribute vec2 a; void main(){ gl_Position = vec4(a, 0., 1.); }';
  const mk = frag => { const p = gl.createProgram(); gl.attachShader(p, sh(gl.VERTEX_SHADER, VS)); gl.attachShader(p, sh(gl.FRAGMENT_SHADER, frag)); gl.linkProgram(p); return p; };
  const bakeP = mk(BAKE), liveP = mk(LIVE);
  const buf = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, buf); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
  gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
  gl.bindAttribLocation(bakeP, 0, 'a'); gl.bindAttribLocation(liveP, 0, 'a'); gl.linkProgram(bakeP); gl.linkProgram(liveP);
  const tex = gl.createTexture(), fb = gl.createFramebuffer();
  let W = 0, H = 0, TW = 0, TH = 0;
  function bake() {
    TW = Math.max(2, Math.round(innerWidth * .5)); TH = Math.max(2, Math.round(innerHeight * .5));
    gl.bindTexture(gl.TEXTURE_2D, tex); gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, TW, TH, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.bindFramebuffer(gl.FRAMEBUFFER, fb); gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
    gl.viewport(0, 0, TW, TH); gl.useProgram(bakeP);
    gl.uniform2f(gl.getUniformLocation(bakeP, 'uRes'), TW, TH); gl.uniform1f(gl.getUniformLocation(bakeP, 'uTime'), 30); gl.uniform2f(gl.getUniformLocation(bakeP, 'uMouse'), 0, 0);
    gl.drawArrays(gl.TRIANGLES, 0, 3); gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  }
  const uRes = gl.getUniformLocation(liveP, 'uRes'), uTime = gl.getUniformLocation(liveP, 'uTime'), uMouse = gl.getUniformLocation(liveP, 'uMouse'), uNeb = gl.getUniformLocation(liveP, 'uNeb');
  const reduce = matchMedia('(prefers-reduced-motion: reduce)');
  let rt;
  const size = () => { W = canvas.width = Math.max(2, Math.round(innerWidth * .75)); H = canvas.height = Math.max(2, Math.round(innerHeight * .75)); bake(); frame(performance.now(), true); };
  addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(size, 200); });
  const m = { x: 0, y: 0, sx: 0, sy: 0 };
  addEventListener('pointermove', e => { m.x = e.clientX / innerWidth - .5; m.y = .5 - e.clientY / innerHeight; }, { passive: true });
  const t0 = performance.now() - 20000; let last = 0;
  function frame(now, force) {
    if (!force && (document.hidden || isPaused() || now - last < 40)) return; // ~25 fps is plenty for a slow background
    last = now; m.sx += (m.x - m.sx) * .08; m.sy += (m.y - m.sy) * .08;
    gl.viewport(0, 0, W, H); gl.useProgram(liveP);
    gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, tex); gl.uniform1i(uNeb, 0);
    gl.uniform2f(uRes, W, H); gl.uniform1f(uTime, reduce.matches ? 30 : (now - t0) / 1000); gl.uniform2f(uMouse, m.sx, m.sy);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
  }
  size();
  (function loop(now) { requestAnimationFrame(loop); frame(now); })(performance.now());
  return { size };
}
