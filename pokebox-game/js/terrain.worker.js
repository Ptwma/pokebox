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
/* map palette: flat, painted biome colours (no ground noise) so the map reads like an illustrated atlas */
const MAPC = { meadow: [.56, .77, .42], marsh: [.45, .65, .54], cliffs: [.62, .72, .52], snow: [.9, .93, .96], plateau: [.79, .69, .48], dunes: [.9, .81, .56], volcanic: [.45, .37, .35] };
const ROCK = [.6, .56, .5], SNOWCAP = [.97, .97, 1], PLAZA = [.93, .87, .74];
const mix3 = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
function grid({ n }) { // island-wide height + grass grid (RG float) for grass blades, water depth and the map
  const out = new Float32Array(n * n * 2), m = n, map = new Uint8ClampedArray(m * m * 4), base = new Float32Array(m * m * 3);
  for (let j = 0; j < n; j++) {
    for (let i = 0; i < n; i++) {
      const x = (i / (n - 1) - .5) * WORLD, z = (j / (n - 1) - .5) * WORLD, s = sample(x, z), k = j * n + i; out[k * 2] = s.y; out[k * 2 + 1] = s.grass;
      let c;
      if (s.y < 0) { const d = Math.min(1, -s.y / 4.4); c = mix3([.42, .8, .84], [.15, .42, .7], Math.pow(d, .7)); }
      else {
        c = [0, 0, 0]; let tw = 0; for (const id in s.w) { const wt = s.w[id], pc = MAPC[BIO_OF[id]]; if (!pc || wt < .003) continue; c[0] += pc[0] * wt; c[1] += pc[1] * wt; c[2] += pc[2] * wt; tw += wt; }
        if (tw > 0) c = c.map(v => v / tw); else c = MAPC.meadow;
        if (s.y < 1.2 && s.land < 1) c = mix3(c, [.93, .87, .66], .7);                           // beaches
        c = mix3(c, ROCK, Math.min(1, s.mountain * 1.3) * .75);
        c = mix3(c, SNOWCAP, Math.max(0, Math.min(1, (s.y - 26) / 10)) * Math.min(1, s.mountain * 2));
        c = mix3(c, PLAZA, s.town * .55);
      }
      base[k * 3] = c[0]; base[k * 3 + 1] = c[1]; base[k * 3 + 2] = c[2];
    }
    if (j % 64 === 0) postMessage({ progress: j / n });
  }
  // shading pass: NW hillshade from real normals, soft contour lines every 8 m, a dark coastline and a light surf ring
  const hy = (i, j) => out[(Math.max(0, Math.min(n - 1, j)) * n + Math.max(0, Math.min(n - 1, i))) * 2], cell = WORLD / (n - 1);
  for (let j = 0; j < m; j++) for (let i = 0; i < m; i++) {
    const k = j * m + i, y = hy(i, j); let r = base[k * 3], g = base[k * 3 + 1], b = base[k * 3 + 2];
    if (y >= 0) {
      const dx = (hy(i + 1, j) - hy(i - 1, j)) / (2 * cell), dz = (hy(i, j + 1) - hy(i, j - 1)) / (2 * cell);
      const nl = Math.hypot(dx, 1, dz), dot = (dx * .5 + .7 + dz * .5) / nl, sh = Math.max(.6, Math.min(1.3, 1 + (dot - .7) * 1.6));
      r *= sh; g *= sh; b *= sh;
      if (Math.floor(y / 8) !== Math.floor(hy(i + 1, j) / 8) || Math.floor(y / 8) !== Math.floor(hy(i, j + 1) / 8)) { r *= .88; g *= .86; b *= .84; }
      if (hy(i + 1, j) < 0 || hy(i - 1, j) < 0 || hy(i, j + 1) < 0 || hy(i, j - 1) < 0) { r *= .62; g *= .6; b *= .58; }   // coastline ink
    } else if (y > -1.1) { r = r * .45 + .55; g = g * .45 + .55; b = b * .45 + .55; }                                        // surf
    map[k * 4] = Math.pow(Math.min(1, r), 1 / 1.1) * 255; map[k * 4 + 1] = Math.pow(Math.min(1, g), 1 / 1.1) * 255; map[k * 4 + 2] = Math.pow(Math.min(1, b), 1 / 1.1) * 255; map[k * 4 + 3] = 255;
  }
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
