// Pokebox — sticker cutouts of card art (main-thread side): worker queue + IndexedDB cache.
// sticker(card, url) -> Promise<{ ok, bitmap?, w, h }>. ok=false means "use the living-card fallback".
const VER = 'st3'; // st3: full-art retry + oval fallback (no more flat cards)
let worker = null, seq = 0, busy = false; const waiting = new Map(), mem = new Map(), queue = [];
function pump() { if (busy || !queue.length) return; const w = getWorker(); if (!w) { queue.splice(0).forEach(j => j.res({ ok: false })); return; }
  const j = queue.shift(); busy = true; const id = ++seq; waiting.set(id, r => { busy = false; j.res(r); pump(); }); w.postMessage({ id, url: j.url }); }
function getWorker() {
  if (worker !== null) return worker;
  try { worker = new Worker(new URL('./cutout.worker.js', import.meta.url), { type: 'module' });
    worker.onmessage = e => { const w = waiting.get(e.data.id); if (w) { waiting.delete(e.data.id); w(e.data); } };
    worker.onerror = e => { console.warn('[cutout] worker failed', e.message); worker = false; busy = false; for (const w of waiting.values()) w({ ok: false }); waiting.clear(); };
  } catch (e) { console.warn('[cutout] no worker', e); worker = false; }
  return worker;
}
/* ---- tiny IndexedDB cache (blob per card) */
let dbP = null;
function db() {
  return dbP ||= new Promise(res => { try { const r = indexedDB.open('pokebox-stickers', 1); r.onupgradeneeded = () => r.result.createObjectStore('s');
    r.onsuccess = () => res(r.result); r.onerror = () => res(null); } catch { res(null); } });
}
async function idbGet(k) { const d = await db(); if (!d) return undefined; return new Promise(res => { try { const q = d.transaction('s').objectStore('s').get(k); q.onsuccess = () => res(q.result); q.onerror = () => res(undefined); } catch { res(undefined); } }); }
async function idbSet(k, v) { const d = await db(); if (!d) return; try { d.transaction('s', 'readwrite').objectStore('s').put(v, k); } catch { /* quota: ignore */ } }

export function sticker(card, url, { priority = false } = {}) {
  const key = VER + ':' + card.f;
  if (mem.has(key)) return mem.get(key);
  const p = (async () => {
    const hit = await idbGet(key);
    if (hit) return hit.ok ? { ok: true, bitmap: await createImageBitmap(hit.blob), w: hit.w, h: hit.h } : { ok: false };
    const r = await new Promise(res => { const j = { url: new URL(url, location.href).href, res }; priority ? queue.unshift(j) : queue.push(j); pump(); });
    if (r.error) { console.warn('[cutout]', card.n, r.error); return { ok: false }; } // transient: don't cache errors
    await idbSet(key, r.ok ? { ok: true, blob: r.blob, w: r.w, h: r.h } : { ok: false });
    return r.ok ? { ok: true, bitmap: await createImageBitmap(r.blob), w: r.w, h: r.h } : { ok: false };
  })();
  mem.set(key, p); return p;
}
