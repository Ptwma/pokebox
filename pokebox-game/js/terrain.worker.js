// Pokebox — terrain worker: builds terrain chunk data and the island-wide height/grass grid off the main thread.
import { sample, H, colorAt, BIOME_LIST, REGIONS, WORLD } from './terrain.js';
const BIO_OF = Object.fromEntries(Object.entries(REGIONS).map(([k, v]) => [k, v.biome]));

function chunk({ cx, cz, size, segs }) {
  const n = segs + 1, step = size / segs, x0 = cx * size, z0 = cz * size;
  // heights with a 1-vertex border for slopes/normals
  const nb = n + 2, hb = new Float32Array(nb * nb);
  for (let j = 0; j < nb; j++) for (let i = 0; i < nb; i++) hb[j * nb + i] = H(x0 + (i - 1) * step, z0 + (j - 1) * step);
  const pos = new Float32Array(n * n * 3), col = new Float32Array(n * n * 3), nor = new Float32Array(n * n * 3);
  const grass = new Float32Array(n * n), bio = new Uint8Array(n * n), road = new Float32Array(n * n), town = new Float32Array(n * n), mnt = new Float32Array(n * n);
  for (let j = 0; j < n; j++) for (let i = 0; i < n; i++) {
    const x = x0 + i * step, z = z0 + j * step, k = j * n + i, b = (j + 1) * nb + (i + 1);
    const hl = hb[b - 1], hr = hb[b + 1], hd = hb[b - nb], hu = hb[b + nb];
    const s = sample(x, z), y = s.y, slope = Math.min(1, Math.hypot(hr - hl, hu - hd) / (2 * step));
    pos[k * 3] = i * step; pos[k * 3 + 1] = y; pos[k * 3 + 2] = j * step;
    let nx = hl - hr, ny = 2 * step, nz = hd - hu; const l = Math.hypot(nx, ny, nz); nor[k * 3] = nx / l; nor[k * 3 + 1] = ny / l; nor[k * 3 + 2] = nz / l;
    const c = colorAt(x, z, s, slope); col[k * 3] = c[0] ** 2.2; col[k * 3 + 1] = c[1] ** 2.2; col[k * 3 + 2] = c[2] ** 2.2; // sRGB palette -> linear vertex colours
    grass[k] = s.grass * (slope < .7 ? 1 : 0); road[k] = s.rd; town[k] = s.town; mnt[k] = s.mountain;
    let best = 0, bw = -1; for (const id in s.w) if (s.w[id] > bw) { bw = s.w[id]; best = BIOME_LIST.indexOf(BIO_OF[id]); } bio[k] = best;
  }
  return { pos, col, nor, grass, bio, road, town, mnt };
}
function grid({ n }) { // island-wide height + grass grid (RG float) for grass blades, water depth and the map
  const out = new Float32Array(n * n * 2), m = n >> 1, map = new Uint8ClampedArray(m * m * 4);
  for (let j = 0; j < n; j++) {
    for (let i = 0; i < n; i++) {
      const x = (i / (n - 1) - .5) * WORLD, z = (j / (n - 1) - .5) * WORLD, s = sample(x, z); out[(j * n + i) * 2] = s.y; out[(j * n + i) * 2 + 1] = s.grass;
      if (!(i & 1) && !(j & 1) && (i >> 1) < m && (j >> 1) < m) {
        const k = ((j >> 1) * m + (i >> 1)) * 4;
        let c; if (s.y < 0) { const d = Math.min(1, -s.y / 4); c = [.25 - d * .12, .55 - d * .2, .72 - d * .12]; } else c = colorAt(x, z, s, s.mountain * .6);
        map[k] = Math.pow(c[0], 1 / 1.25) * 255; map[k + 1] = Math.pow(c[1], 1 / 1.25) * 255; map[k + 2] = Math.pow(c[2], 1 / 1.25) * 255; map[k + 3] = 255;
      }
    }
    if (j % 64 === 0) postMessage({ progress: j / n });
  }
  // hillshade the map from the height grid
  for (let j = 1; j < m; j++) for (let i = 1; i < m; i++) { const a = out[((j * 2) * n + i * 2) * 2], b = out[(((j - 1) * 2) * n + (i - 1) * 2) * 2]; if (a < 0) continue; const sh = Math.max(.6, Math.min(1.35, 1 + (a - b) * .06)); const k = (j * m + i) * 4; map[k] *= sh; map[k + 1] *= sh; map[k + 2] *= sh; }
  return { grid: out, n, map, m };
}
onmessage = e => {
  const { id, type } = e.data;
  try {
    const r = type === 'chunk' ? chunk(e.data) : grid(e.data);
    const tr = Object.values(r).filter(v => v && v.buffer).map(v => v.buffer);
    postMessage({ id, ...r }, tr);
  } catch (err) { postMessage({ id, error: String(err?.stack || err) }); }
};
