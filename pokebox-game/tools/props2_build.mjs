// Pokebox — builds assets/world/props2.glb from Quaternius Fantasy Props MegaKit + Stylized Nature MegaKit (CC0).
// Same look as the Blender version (tools/blender_props2.py) but runs anywhere with Node, so a Blender crash can't block it:
//   every triangle gets ONE colour = base-colour texture (sampled at the triangle's UV centre, from a 256 px copy)
//   × the pack's vertex tint (glTF COLOR_0), saturation pushed a little; textures/UVs dropped; one mesh per prop "PR_<Name>".
// usage: node props2_build.mjs <srcDir with Exports/glTF + nature/glTF> <dir with 256px .rgb textures> <out.glb>
import fs from 'fs';
import path from 'path';
import { Document, NodeIO } from '@gltf-transform/core';
import { weld, simplifyPrimitive } from '@gltf-transform/functions';
import { MeshoptSimplifier } from 'meshoptimizer';

const [SRC, TEX, OUT] = process.argv.slice(2);
const PROPS = ['Anvil', 'Anvil_Log', 'Barrel', 'Barrel_Apples', 'Barrel_Holder', 'Bench', 'Bucket_Wooden_1', 'Bucket_Metal', 'Cage_Small', 'Cauldron',
  'Crate_Wooden', 'Crate_Metal', 'Dummy', 'FarmCrate_Apple', 'FarmCrate_Carrot', 'FarmCrate_Empty', 'Lantern_Wall', 'Pot_1', 'Rope_1',
  'Shield_Wooden', 'Stall_Cart_Empty', 'Stall_Empty', 'Stool', 'Table_Large', 'Torch_Metal', 'Vase_2', 'Vase_4', 'Vase_Rubble_Medium', 'WeaponStand',
  'Whetstone', 'Workbench', 'Banner_1', 'Banner_2', 'Bag', 'Pouch_Large', 'Chair_1', 'Pickaxe_Bronze', 'Axe_Bronze', 'Coin_Pile'];
const NATURE = ['RockPath_Round_Small_1', 'RockPath_Round_Small_2', 'Pebble_Round_1', 'Pebble_Round_2',
  'Pebble_Square_1', 'Mushroom_Laetiporus', 'Rock_Medium_1', 'Rock_Medium_2'];
const MAXTRI = { default: 1200, nature: 600 };

const texCache = {};
function tex(uri) { const f = path.join(TEX, path.basename(uri) + '.rgb'); if (!fs.existsSync(f)) return null; return texCache[f] ||= fs.readFileSync(f); }
function sample(img, u, v) { u = ((u % 1) + 1) % 1; v = ((v % 1) + 1) % 1; const x = Math.min(255, (u * 256) | 0), y = Math.min(255, (v * 256) | 0); let r = 0, g = 0, b = 0, n = 0;
  for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) { const xx = Math.max(0, Math.min(255, x + dx)), yy = Math.max(0, Math.min(255, y + dy)), i = (yy * 256 + xx) * 3; r += img[i]; g += img[i + 1]; b += img[i + 2]; n++; }
  return [r / n / 255, g / n / 255, b / n / 255]; }
const srgb2lin = c => c <= .04045 ? c / 12.92 : ((c + .055) / 1.055) ** 2.4;
function toon([r, g, b]) { // HSV: saturation ×1.18 +.04, value ×1.08 +.03 (same as the Blender script)
  const mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn; let h = 0;
  if (d) h = mx === r ? ((g - b) / d) % 6 : mx === g ? (b - r) / d + 2 : (r - g) / d + 4; h /= 6; if (h < 0) h += 1;
  let s = mx ? d / mx : 0, v = mx; s = Math.min(1, s * 1.18 + .04); v = Math.min(1, v * 1.08 + .03);
  const i = Math.floor(h * 6), f = h * 6 - i, p = v * (1 - s), q = v * (1 - f * s), t = v * (1 - (1 - f) * s);
  return [[v, t, p], [q, v, p], [p, v, t], [p, q, v], [t, p, v], [v, p, q]][i % 6]; }

const CT = { 5120: Int8Array, 5121: Uint8Array, 5122: Int16Array, 5123: Uint16Array, 5125: Uint32Array, 5126: Float32Array };
const NC = { SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4, MAT4: 16 };
function accessor(g, bins, i) {
  const a = g.accessors[i], bv = g.bufferViews[a.bufferView], T = CT[a.componentType], n = NC[a.type], buf = bins[bv.buffer];
  const stride = bv.byteStride || T.BYTES_PER_ELEMENT * n, off = (bv.byteOffset || 0) + (a.byteOffset || 0), out = new Float32Array(a.count * n);
  const dv = new DataView(buf.buffer, buf.byteOffset, buf.byteLength);
  const rd = { 5126: o => dv.getFloat32(o, true), 5125: o => dv.getUint32(o, true), 5123: o => dv.getUint16(o, true), 5121: o => dv.getUint8(o), 5122: o => dv.getInt16(o, true), 5120: o => dv.getInt8(o) }[a.componentType];
  const norm = a.normalized ? { 5121: 255, 5123: 65535, 5120: 127, 5122: 32767 }[a.componentType] : 1;
  for (let k = 0; k < a.count; k++) for (let c = 0; c < n; c++) out[k * n + c] = rd(off + k * stride + c * T.BYTES_PER_ELEMENT) / norm;
  return { data: out, n };
}
function mat4(node) {
  if (node.matrix) return node.matrix;
  const [tx, ty, tz] = node.translation || [0, 0, 0], [x, y, z, w] = node.rotation || [0, 0, 0, 1], [sx, sy, sz] = node.scale || [1, 1, 1];
  return [(1 - 2 * (y * y + z * z)) * sx, (2 * (x * y + z * w)) * sx, (2 * (x * z - y * w)) * sx, 0, (2 * (x * y - z * w)) * sy, (1 - 2 * (x * x + z * z)) * sy, (2 * (y * z + x * w)) * sy, 0,
    (2 * (x * z + y * w)) * sz, (2 * (y * z - x * w)) * sz, (1 - 2 * (x * x + y * y)) * sz, 0, tx, ty, tz, 1];
}
const mul = (a, b) => { const o = new Array(16).fill(0); for (let r = 0; r < 4; r++) for (let c = 0; c < 4; c++) for (let k = 0; k < 4; k++) o[c * 4 + r] += a[k * 4 + r] * b[c * 4 + k]; return o; };

function loadProp(file, maxTri) {
  const g = JSON.parse(fs.readFileSync(file, 'utf8')), dir = path.dirname(file), bins = g.buffers.map(b => fs.readFileSync(path.join(dir, b.uri)));
  const P = [], N = [], C = [];
  // triangle budget: simplify the original (indexed, connected) geometry first, then colour the triangles
  let total = 0; for (const me of g.meshes) for (const pr of me.primitives) total += (pr.indices != null ? g.accessors[pr.indices].count : g.accessors[pr.attributes.POSITION].count) / 3;
  const keep = Math.min(1, maxTri / total);
  const walk = (ni, parent) => { const node = g.nodes[ni], m = mul(parent, mat4(node));
    if (node.mesh != null) for (const pr of g.meshes[node.mesh].primitives) {
      const pos = accessor(g, bins, pr.attributes.POSITION), nor = pr.attributes.NORMAL != null ? accessor(g, bins, pr.attributes.NORMAL) : null;
      const uv = pr.attributes.TEXCOORD_0 != null ? accessor(g, bins, pr.attributes.TEXCOORD_0) : null, col = pr.attributes.COLOR_0 != null ? accessor(g, bins, pr.attributes.COLOR_0) : null;
      let idx = pr.indices != null ? accessor(g, bins, pr.indices).data : Float32Array.from({ length: pos.data.length / 3 }, (_, i) => i);
      if (keep < 1) { const target = Math.max(3, Math.floor(idx.length * keep / 3) * 3);
        const [ni] = MeshoptSimplifier.simplify(Uint32Array.from(idx), pos.data, 3, target, .02, []); idx = ni; }
      const mat = pr.material != null ? g.materials[pr.material] : null, pbr = mat?.pbrMetallicRoughness || {}, bt = pbr.baseColorTexture;
      const img = bt ? tex(g.images[g.textures[bt.index].source].uri) : null, fac = pbr.baseColorFactor || [1, 1, 1, 1];
      for (let t = 0; t < idx.length; t += 3) {
        const ids = [idx[t], idx[t + 1], idx[t + 2]];
        let rgb = [1, 1, 1];
        if (img && uv) { const u = ids.reduce((s, i) => s + uv.data[i * 2], 0) / 3, v = ids.reduce((s, i) => s + uv.data[i * 2 + 1], 0) / 3; rgb = sample(img, u, v).map(srgb2lin); }
        rgb = rgb.map((c, k) => c * fac[k]);
        if (col) { const vc = [0, 1, 2].map(k => ids.reduce((s, i) => s + col.data[i * col.n + k], 0) / 3); rgb = rgb.map((c, k) => c * vc[k]); }
        // toonify in sRGB space (how it is seen), store linear (glTF vertex colours are linear)
        const lin2srgb = c => c <= .0031308 ? c * 12.92 : 1.055 * c ** (1 / 2.4) - .055;
        rgb = toon(rgb.map(lin2srgb)).map(srgb2lin);
        for (const i of ids) {
          const x = pos.data[i * 3], y = pos.data[i * 3 + 1], z = pos.data[i * 3 + 2];
          P.push(m[0] * x + m[4] * y + m[8] * z + m[12], m[1] * x + m[5] * y + m[9] * z + m[13], m[2] * x + m[6] * y + m[10] * z + m[14]);
          if (nor) { const a = nor.data[i * 3], b = nor.data[i * 3 + 1], c = nor.data[i * 3 + 2]; let nx = m[0] * a + m[4] * b + m[8] * c, ny = m[1] * a + m[5] * b + m[9] * c, nz = m[2] * a + m[6] * b + m[10] * c; const l = Math.hypot(nx, ny, nz) || 1; N.push(nx / l, ny / l, nz / l); }
          else N.push(0, 1, 0);
          C.push(rgb[0], rgb[1], rgb[2], 1);
        }
      }
    }
    for (const c of node.children || []) walk(c, m); };
  const I = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1];
  for (const r of g.scenes[g.scene || 0].nodes) walk(r, I);
  return { P: new Float32Array(P), N: new Float32Array(N), C: new Float32Array(C) };
}

await MeshoptSimplifier.ready;
const doc = new Document(), buf = doc.createBuffer(), scene = doc.createScene('props2');
const mat = doc.createMaterial('PR_Vcol').setBaseColorFactor([1, 1, 1, 1]).setRoughnessFactor(.85).setMetallicFactor(0);
const list = [...PROPS.map(n => [n, path.join(SRC, 'Exports', 'glTF', n + '.gltf'), MAXTRI.default]), ...NATURE.map(n => [n, path.join(SRC, 'nature', 'glTF', n + '.gltf'), MAXTRI.nature])];
for (const [name, file, maxTri] of list) {
  const { P, N, C } = loadProp(file, maxTri);
  const prim = doc.createPrimitive().setMaterial(mat)
    .setAttribute('POSITION', doc.createAccessor().setType('VEC3').setArray(P).setBuffer(buf))
    .setAttribute('NORMAL', doc.createAccessor().setType('VEC3').setArray(N).setBuffer(buf))
    .setAttribute('COLOR_0', doc.createAccessor().setType('VEC4').setArray(C).setBuffer(buf));
  const mesh = doc.createMesh('PR_' + name).addPrimitive(prim);
  scene.addChild(doc.createNode('PR_' + name).setMesh(mesh).setExtras({ maxTri }));
}
await doc.transform(weld());
for (const node of doc.getRoot().listNodes()) {
  const prim = node.getMesh().listPrimitives()[0]; node.setExtras({});
  // vertex colours as normalized bytes (core glTF allows it) — a quarter of the float size
  const c = prim.getAttribute('COLOR_0'), f = c.getArray(), u8 = new Uint8Array(f.length); for (let i = 0; i < f.length; i++) u8[i] = Math.round(Math.min(1, Math.max(0, f[i])) * 255);
  c.setArray(u8).setNormalized(true);
}
const io = new NodeIO();
await io.write(OUT, doc);
const out = []; for (const n of doc.getRoot().listNodes()) { const p = n.getMesh().listPrimitives()[0]; out.push(n.getName().slice(3) + ':' + (p.getIndices() ? p.getIndices().getCount() / 3 : 0)); }
console.log(out.join(' ')); console.log('bytes', fs.statSync(OUT).size);
