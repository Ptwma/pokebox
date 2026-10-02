// Pokebox — card-art "sticker" cutout worker.
// Runs U^2-Net-small (u2netp, Apache-2.0) with onnxruntime-web (WASM, single thread) on the card's art window,
// cleans the mask, and composes a die-cut sticker (ink line + white border + art). Result: a WebP blob.
import * as ort from '../vendor/ort/ort.wasm.bundle.min.mjs';

ort.env.wasm.numThreads = 1;
ort.env.wasm.wasmPaths = new URL('../vendor/ort/', import.meta.url).href;
const MODEL = new URL('../assets/models/u2netp.onnx', import.meta.url).href;
const N = 320;
let sessP = null;
const session = () => sessP ||= fetch(MODEL).then(r => { if (!r.ok) throw new Error('model ' + r.status); return r.arrayBuffer(); })
  .then(buf => ort.InferenceSession.create(new Uint8Array(buf), { executionProviders: ['wasm'], graphOptimizationLevel: 'all' }));

function clean(m) { // m: Float32Array N*N in 0..1 -> {keep: Uint8Array, ok, frac}
  const bin = new Uint8Array(N * N); for (let i = 0; i < N * N; i++) bin[i] = m[i] > .5 ? 1 : 0;
  const lab = new Int32Array(N * N).fill(-1), comps = [], q = new Int32Array(N * N);
  for (let s = 0; s < N * N; s++) {
    if (!bin[s] || lab[s] >= 0) continue;
    let h = 0, t = 0, area = 0, sx = 0, sy = 0; q[t++] = s; lab[s] = comps.length;
    while (h < t) { const p = q[h++], x = p % N, y = (p / N) | 0; area++; sx += x; sy += y;
      if (x > 0 && bin[p - 1] && lab[p - 1] < 0) { lab[p - 1] = comps.length; q[t++] = p - 1; }
      if (x < N - 1 && bin[p + 1] && lab[p + 1] < 0) { lab[p + 1] = comps.length; q[t++] = p + 1; }
      if (y > 0 && bin[p - N] && lab[p - N] < 0) { lab[p - N] = comps.length; q[t++] = p - N; }
      if (y < N - 1 && bin[p + N] && lab[p + N] < 0) { lab[p + N] = comps.length; q[t++] = p + N; } }
    comps.push({ area, cx: sx / area, cy: sy / area });
  }
  if (!comps.length) return { ok: false };
  const big = Math.max(...comps.map(c => c.area));
  const good = comps.map(c => c.area >= big * .12 && c.area > 60);
  const keep = new Uint8Array(N * N); let area = 0;
  for (let i = 0; i < N * N; i++) if (lab[i] >= 0 && good[lab[i]]) { keep[i] = 1; area++; }
  // fill holes: background = what the border can reach through non-kept pixels
  const reach = new Uint8Array(N * N); let h = 0, t = 0;
  const push = p => { if (!keep[p] && !reach[p]) { reach[p] = 1; q[t++] = p; } };
  for (let i = 0; i < N; i++) { push(i); push(N * (N - 1) + i); push(i * N); push(i * N + N - 1); }
  while (h < t) { const p = q[h++], x = p % N, y = (p / N) | 0; if (x > 0) push(p - 1); if (x < N - 1) push(p + 1); if (y > 0) push(p - N); if (y < N - 1) push(p + N); }
  for (let i = 0; i < N * N; i++) if (!keep[i] && !reach[i]) { keep[i] = 1; area++; }
  let edge = 0; for (let i = 0; i < N; i++) edge += keep[i] + keep[N * (N - 1) + i] + keep[i * N] + keep[i * N + N - 1];
  const frac = area / (N * N), edgeFrac = edge / (4 * N), share = big / area;
  const ok = frac > .045 && frac < .58 && edgeFrac < .36 && share > .62;
  return { ok, keep, frac, edgeFrac };
}

function silhouette(src, w, h, color) { const c = new OffscreenCanvas(w, h), g = c.getContext('2d'); g.drawImage(src, 0, 0); g.globalCompositeOperation = 'source-in'; g.fillStyle = color; g.fillRect(0, 0, w, h); return c; }

async function make(url, { outW = 384 } = {}) {
  const bmp = await createImageBitmap(await (await fetch(url)).blob());
  const W = bmp.width, H = bmp.height, fullArt = false;
  const sx = W * .075, sy = H * .095, sw = W * .85, sh = H * .42;
  const c320 = new OffscreenCanvas(N, N), g = c320.getContext('2d', { willReadFrequently: true });
  g.drawImage(bmp, sx, sy, sw, sh, 0, 0, N, N);
  const px = g.getImageData(0, 0, N, N).data, inp = new Float32Array(3 * N * N);
  const mean = [.485, .456, .406], std = [.229, .224, .225];
  for (let i = 0; i < N * N; i++) for (let k = 0; k < 3; k++) inp[k * N * N + i] = (px[i * 4 + k] / 255 - mean[k]) / std[k];
  const s = await session(), feeds = { [s.inputNames[0]]: new ort.Tensor('float32', inp, [1, 3, N, N]) };
  const out = await s.run(feeds), m = out[s.outputNames[0]].data;
  let lo = 1e9, hi = -1e9; for (let i = 0; i < m.length; i++) { lo = Math.min(lo, m[i]); hi = Math.max(hi, m[i]); }
  const mn = new Float32Array(N * N); for (let i = 0; i < N * N; i++) mn[i] = (m[i] - lo) / (hi - lo + 1e-6);
  const r = clean(mn);
  if (!r.ok) return { ok: false, frac: r.frac, edge: r.edgeFrac };
  // soft alpha mask (N x N), restricted to the kept region (slightly grown so soft edges survive)
  const mask = new OffscreenCanvas(N, N), mg = mask.getContext('2d'), id = mg.createImageData(N, N);
  for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) {
    const i = y * N + x; let k = r.keep[i];
    if (!k) for (let dy = -1; dy <= 1 && !k; dy++) for (let dx = -1; dx <= 1; dx++) { const xx = x + dx, yy = y + dy; if (xx >= 0 && yy >= 0 && xx < N && yy < N && r.keep[yy * N + xx]) { k = 1; break; } }
    const a = k ? Math.min(1, Math.max(0, (mn[i] - .3) / .4)) : 0; id.data[i * 4 + 3] = r.keep[i] ? Math.max(a, .85) * 255 : a * 255;
  }
  mg.putImageData(id, 0, 0);
  // art at output resolution with the mask as alpha
  const aw = outW, ah = Math.round(outW * sh / sw), art = new OffscreenCanvas(aw, ah), ag = art.getContext('2d');
  ag.drawImage(bmp, sx, sy, sw, sh, 0, 0, aw, ah); ag.globalCompositeOperation = 'destination-in'; ag.imageSmoothingQuality = 'high'; ag.drawImage(mask, 0, 0, aw, ah);
  // die-cut sticker: ink line outside a white border
  const P = 16, cw = aw + P * 2, ch = ah + P * 2, st = new OffscreenCanvas(cw, ch), sg = st.getContext('2d');
  const ink = silhouette(art, aw, ah, '#15101c'), white = silhouette(art, aw, ah, '#fffaf0');
  const ring = (img, rad) => { for (let a = 0; a < 24; a++) { const t = a / 24 * Math.PI * 2; sg.drawImage(img, P + Math.cos(t) * rad, P + Math.sin(t) * rad); } };
  ring(ink, 10); ring(white, 7.5); sg.drawImage(art, P, P);
  // trim to content
  const d = sg.getImageData(0, 0, cw, ch).data; let x0 = cw, y0 = ch, x1 = 0, y1 = 0;
  for (let y = 0; y < ch; y += 2) for (let x = 0; x < cw; x += 2) if (d[(y * cw + x) * 4 + 3] > 20) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
  x0 = Math.max(0, x0 - 2); y0 = Math.max(0, y0 - 2); x1 = Math.min(cw - 1, x1 + 2); y1 = Math.min(ch - 1, y1 + 2);
  const fw = x1 - x0 + 1, fh = y1 - y0 + 1, fin = new OffscreenCanvas(fw, fh); fin.getContext('2d').drawImage(st, x0, y0, fw, fh, 0, 0, fw, fh);
  const blob = await fin.convertToBlob({ type: 'image/webp', quality: .9 });
  return { ok: true, blob, w: fw, h: fh, frac: r.frac, fullArt };
}

onmessage = async e => {
  const { id, url, opts } = e.data;
  try { postMessage({ id, ...(await make(url, opts)) }); }
  catch (err) { postMessage({ id, ok: false, error: String(err?.message || err) }); }
};
