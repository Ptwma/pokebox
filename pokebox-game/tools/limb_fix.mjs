// Pokebox — sturdier anime trainers: thicken arms and legs around each limb bone's axis (T-pose), keeping skin weights.
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { MeshoptDecoder, MeshoptEncoder } from 'meshoptimizer';
await MeshoptDecoder.ready; await MeshoptEncoder.ready;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ 'meshopt.decoder': MeshoptDecoder, 'meshopt.encoder': MeshoptEncoder });
const DIR = '/home/claude/pokebox/pokebox-game/assets/chars/anime/';
const K = { upperarm: 1.32, lowerarm: 1.28, hand: 1.12, thigh: 1.16, calf: 1.2 }; // radial scale per limb part
const files = process.argv.slice(2);
for (const f of files) {
  const doc = await io.read(DIR + f), root = doc.getRoot(), skin = root.listSkins()[0], names = skin.listJoints().map(j => j.getName());
  const part = n => { const m = /^(upperarm|lowerarm|hand|thigh|calf)_(l|r)$/.exec(n); return m ? m[1] + '_' + m[2] : null; };
  const prims = root.listMeshes().flatMap(m => m.listPrimitives());
  // pass 1: per limb part, the axis centre (mean of the two cross-axis coordinates)
  const acc = {};
  const dom = (J, W, i) => { let b = -1, bw = -1; for (let c = 0; c < 4; c++) if (W[i * 4 + c] > bw) { bw = W[i * 4 + c]; b = J[i * 4 + c]; } return { j: b, w: bw }; };
  const read = p => { const P = p.getAttribute('POSITION'), J = p.getAttribute('JOINTS_0'), W = p.getAttribute('WEIGHTS_0'); if (!P || !J || !W) return null;
    const n = P.getCount(), pos = [], jj = new Array(n * 4), ww = new Array(n * 4), e = [], ew = [];
    for (let i = 0; i < n; i++) { pos.push(P.getElement(i, [])); J.getElement(i, e); W.getElement(i, ew); for (let c = 0; c < 4; c++) { jj[i * 4 + c] = e[c]; ww[i * 4 + c] = ew[c]; } }
    return { P, n, pos, jj, ww }; };
  const data = prims.map(read);
  for (const d of data) if (d) for (let i = 0; i < d.n; i++) { const { j, w } = dom(d.jj, d.ww, i); const pn = part(names[j]); if (!pn || w < .5) continue; const arm = /arm|hand/.test(pn), [x, y, z] = d.pos[i];
    const a = acc[pn] ||= { s0: 0, s1: 0, n: 0, arm }; a.s0 += arm ? y : x; a.s1 += z; a.n++; }
  for (const k in acc) { acc[k].c0 = acc[k].s0 / acc[k].n; acc[k].c1 = acc[k].s1 / acc[k].n; }
  // pass 2: push each vertex away from its limb axis, blended by how much that limb owns it
  let moved = 0;
  data.forEach(d => { if (!d) return; for (let i = 0; i < d.n; i++) {
    let dx = 0, dy = 0, dz = 0; const [x, y, z] = d.pos[i];
    for (let c = 0; c < 4; c++) { const w = d.ww[i * 4 + c]; if (w <= 0) continue; const pn = part(names[d.jj[i * 4 + c]]); if (!pn || !acc[pn]) continue; const a = acc[pn], k = K[pn.split('_')[0]] - 1;
      if (a.arm) { dy += (y - a.c0) * k * w; dz += (z - a.c1) * k * w; } else { dx += (x - a.c0) * k * w; dz += (z - a.c1) * k * w; } }
    if (dx || dy || dz) { d.P.setElement(i, [x + dx, y + dy, z + dz]); moved++; } } });
  await io.write(DIR + f, doc); console.log(f, 'limbs', Object.keys(acc).length, 'moved', moved);
}
