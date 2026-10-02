// Pokebox — in-game updater. New versions are published as GitHub Releases (see .github/workflows/release.yml).
// The game itself only asks and shows progress; the platform does the download + install:
//   PC      → Pokebox.exe local server:  GET /__update/check · POST /__update/apply · GET /__update/status
//   Android → window.PokeboxNative bridge (MainActivity): startCheck() / startApply() / status() / reload() / openUrl()
// Saves are never touched (they live in the browser's Local Storage), card images are never downloaded.
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const wait = ms => new Promise(r => setTimeout(r, ms));
const N = () => window.PokeboxNative;

/* ---------- platform backends: both expose check() and apply(onProgress) */
const pc = {
  async check() {
    const r = await fetch('/__update/check', { cache: 'no-store' });
    if (!r.ok) throw new Error('no updater');
    return r.json();
  },
  async apply(onProgress) {
    const r = await fetch('/__update/apply', { method: 'POST' });
    if (!r.ok) throw new Error((await r.text()) || 'could not start the update');
    return poll(async () => (await fetch('/__update/status', { cache: 'no-store' })).json(), onProgress);
  },
  restart() { location.reload(); },
};
const android = {
  async check() {
    N().startCheck();
    for (let i = 0; i < 120; i++) { await wait(250); const s = JSON.parse(N().status() || '{}'); if (s.check) return s.check; if (s.state === 'error') throw new Error(s.msg); }
    throw new Error('timeout');
  },
  async apply(onProgress) { N().startApply(); return poll(async () => JSON.parse(N().status() || '{}'), onProgress); },
  restart() { N().reload(); },
};
async function poll(get, onProgress) {
  for (;;) {
    await wait(300);
    const s = await get();
    onProgress?.(s);
    if (s.state === 'done') return s;
    if (s.state === 'error') throw new Error(s.msg || 'update failed');
  }
}
export function backend() {
  if (N()?.startCheck) return android;
  if (location.hostname === 'localhost' || location.hostname === '127.0.0.1') return pc;
  return null;
}

/* ---------- UI */
let box = null;
function overlay(html) {
  box?.remove(); box = document.createElement('div'); box.className = 'upd'; box.innerHTML = `<div class="updbox">${html}</div>`;
  document.body.append(box); return box;
}
const close = () => { box?.remove(); box = null; };
const mb = n => n ? (n / 1048576).toFixed(n > 10485760 ? 0 : 1) + ' MB' : '';

/** shows the "update available" dialog; resolves when the user closed it (or the update restarted the game) */
async function offer(info, be) {
  const notes = (info.notes || []).slice(0, 8).map(n => `<li>${esc(n)}</li>`).join('');
  if (info.needApk) {
    overlay(`<div class="eyebrow">New version ${esc(info.latest)}</div><h3 class="display">A new app is needed</h3>
      <p>This update changes the Android app itself. Download the new Pokebox APK and install it over this one — your saves stay.</p>
      ${notes ? `<ul>${notes}</ul>` : ''}<div class="row"><button class="btn gold" id="updGo" type="button">Open download page</button><button class="btn ghost" id="updNo" type="button">Later</button></div>`);
    box.querySelector('#updGo').onclick = () => { N()?.openUrl?.(info.page); close(); };
    box.querySelector('#updNo').onclick = close;
    return;
  }
  overlay(`<div class="eyebrow">Pokebox ${esc(info.current)} → <b>${esc(info.latest)}</b></div><h3 class="display">Update available</h3>
    ${notes ? `<ul>${notes}</ul>` : ''}<p class="muted small">Download ${mb(info.size)}. Your progress and cards are kept.</p>
    <div class="row"><button class="btn gold" id="updGo" type="button">Update now</button><button class="btn ghost" id="updNo" type="button">Later</button></div>`);
  return new Promise(res => {
    box.querySelector('#updNo').onclick = () => { try { sessionStorage.setItem('pbxUpdSkip', info.latest); } catch {} close(); res(false); };
    box.querySelector('#updGo').onclick = async () => {
      overlay(`<div class="eyebrow">Updating to ${esc(info.latest)}</div><h3 class="display" id="updT">Downloading…</h3><div class="updbar"><i id="updBar"></i></div><p class="muted small" id="updM"></p>`);
      try {
        window.__pbxFlush?.(); // save before the files change
        await be.apply(s => {
          const bar = box?.querySelector('#updBar'); if (bar) bar.style.width = Math.round((s.pct || 0) * 100) + '%';
          const t = box?.querySelector('#updT'); if (t) t.textContent = s.state === 'installing' ? 'Installing…' : s.state === 'done' ? 'Done!' : 'Downloading…';
          const m = box?.querySelector('#updM'); if (m) m.textContent = s.msg || '';
        });
        box.querySelector('#updT').textContent = 'Restarting…'; await wait(700); be.restart(); res(true);
      } catch (e) {
        overlay(`<h3 class="display">Update failed</h3><p>${esc(e.message)}</p><p class="muted small">The game still works on the current version. Try again later.</p><div class="row"><button class="btn" id="updOk" type="button">OK</button></div>`);
        box.querySelector('#updOk').onclick = () => { close(); res(false); };
      }
    };
  });
}

/** automatic check after start (quiet when offline or up to date) */
export async function autoCheck() {
  const be = backend(); if (!be) return;
  try {
    const info = await be.check(); window.__pbxVersion = info.current;
    if (!info.newer) return;
    let skip = null; try { skip = sessionStorage.getItem('pbxUpdSkip'); } catch {}
    if (skip === info.latest) return;
    await offer(info, be);
  } catch { /* offline / no release yet: play normally */ }
}
/** Settings → "Check for updates" */
export async function manualCheck(toast) {
  const be = backend(); if (!be) { toast?.('Updates work when the game is started with Pokebox.exe or the Android app.'); return; }
  try {
    const info = await be.check(); window.__pbxVersion = info.current;
    if (info.error) { toast?.('Could not reach GitHub: ' + esc(info.error)); return; }
    if (!info.newer) { toast?.(`You have the latest version (${esc(info.current)}).`); return; }
    try { sessionStorage.removeItem('pbxUpdSkip'); } catch {}
    await offer(info, be);
  } catch (e) { toast?.('Update check failed: ' + esc(e.message)); }
}
