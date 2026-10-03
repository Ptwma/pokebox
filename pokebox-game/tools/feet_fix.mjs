// Pokebox — close the ankle gap: pants hem reaches into the shoe, chunkier anime sneakers.
import { NodeIO } from '@gltf-transform/core'; import { ALL_EXTENSIONS } from '@gltf-transform/extensions'; import { MeshoptDecoder, MeshoptEncoder } from 'meshoptimizer';
await MeshoptDecoder.ready; await MeshoptEncoder.ready;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ 'meshopt.decoder': MeshoptDecoder, 'meshopt.encoder': MeshoptEncoder });
const DIR = '/home/claude/pokebox/pokebox-game/assets/chars/anime/';
for (const f of process.argv.slice(2)) {
  const doc = await io.read(DIR + f), prims = doc.getRoot().listMeshes().flatMap(m => m.listPrimitives());
  const by = n => prims.filter(p => p.getMaterial()?.getName() === n);
  const all = (p, fn) => { const P = p.getAttribute('POSITION'), v = []; for (let i = 0; i < P.getCount(); i++) { P.getElement(i, v); const r = fn([...v]); if (r) P.setElement(i, r); } };
  // shoe extents per side
  const S = { l: null, r: null }; for (const p of [...by('Shoes'), ...by('Sole')]) all(p, ([x, y, z]) => { const k = x > 0 ? 'l' : 'r'; const s = S[k] ||= { x0: 1e9, x1: -1e9, z0: 1e9, z1: -1e9, y1: -1e9 }; s.x0 = Math.min(s.x0, x); s.x1 = Math.max(s.x1, x); s.z0 = Math.min(s.z0, z); s.z1 = Math.max(s.z1, z); s.y1 = Math.max(s.y1, y); });
  if (!S.l || !S.r) { console.log(f, 'no shoes'); continue; }
  const top = Math.max(S.l.y1, S.r.y1);
  // pants: stretch the bottom 9 cm so the hem tucks 3 cm into the shoe, and flare it a touch
  let hem = 1e9; for (const p of by('Pants')) all(p, ([, y]) => { hem = Math.min(hem, y); });
  const y0 = hem + .09, target = top - .03, k = (y0 - target) / (y0 - hem);
  for (const p of by('Pants')) all(p, ([x, y, z]) => { if (y >= y0) return null; const t = (y0 - y) / (y0 - hem), s = S[x > 0 ? 'l' : 'r'], cx = (s.x0 + s.x1) / 2, cz = (s.z0 + s.z1) / 2 - .005, fl = 1 + .1 * t * t;
    return [cx + (x - cx) * fl, y0 - (y0 - y) * k, cz + (z - cz) * fl]; });
  // shoes: 18% wider/longer, 30% taller from the sole
  for (const p of [...by('Shoes'), ...by('Sole')]) all(p, ([x, y, z]) => { const s = S[x > 0 ? 'l' : 'r'], cx = (s.x0 + s.x1) / 2, cz = (s.z0 + s.z1) / 2; return [cx + (x - cx) * 1.18, -1 + (y + 1) * 1.3, cz + (z - cz) * 1.16 + .006]; });
  await io.write(DIR + f, doc); console.log(f, 'hem', hem.toFixed(3), '->', target.toFixed(3));
}
