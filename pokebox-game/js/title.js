// Pokebox — title screen / main menu (handheld-console style intro): logo drop, PRESS START, chiptune theme, menu,
// and on phones a "turn your phone" step before the game (the Android app then locks landscape).
import { music, sfx } from './audio.js';

const $ = s => document.querySelector(s);
const isPortrait = () => matchMedia('(orientation: portrait)').matches;

export function runTitle({ touch = false, hasProgress = false, ready = Promise.resolve(), onStart, onCards, onSettings }) {
  const el = $('#title'); if (!el) { onStart?.(); return; }
  el.hidden = false; document.body.classList.add('at-title');
  el.innerHTML = `
    <div class="ti-sky"><i class="ti-sun"></i><i class="ti-cloud c1"></i><i class="ti-cloud c2"></i><i class="ti-cloud c3"></i></div>
    <svg class="ti-hills" viewBox="0 0 1600 400" preserveAspectRatio="none" aria-hidden="true">
      <path class="h1" d="M0 230 C200 150 380 170 560 210 C760 255 900 140 1120 160 C1300 175 1440 240 1600 200 V400 H0Z"/>
      <path class="h2" d="M0 290 C240 230 420 260 640 280 C860 300 1020 230 1240 250 C1400 262 1500 300 1600 285 V400 H0Z"/>
      <path class="h3" d="M0 340 C300 310 520 330 800 345 C1080 360 1300 320 1600 335 V400 H0Z"/>
    </svg>
    <div class="ti-sparks">${Array.from({ length: 18 }, (_, i) => `<i style="--x:${(i * 53) % 100}%;--d:${(i % 7) * .7}s;--s:${.6 + (i % 4) * .25}"></i>`).join('')}</div>
    <div class="ti-center">
      <div class="ti-orb"><i></i></div>
      <h1 class="ti-logo" data-text="POKEBOX">POKEBOX</h1>
      <div class="ti-sub">An Echo Ranger adventure</div>
      <div class="ti-press" id="tiPress">${touch ? 'TAP TO START' : 'PRESS START'}</div>
      <nav class="ti-menu" id="tiMenu" hidden>
        <button type="button" data-a="start">${hasProgress ? 'Continue journey' : 'Start journey'}</button>
        <button type="button" data-a="cards">Echo cards</button>
        <button type="button" data-a="settings">Settings</button>
      </nav>
      <div class="ti-load" id="tiLoad">Loading Veyra…</div>
    </div>
    <div class="ti-rotate" id="tiRotate" hidden><i>📱</i><b>Turn your phone sideways</b><span>Veyra is played in landscape.</span></div>
    <div class="ti-foot">© fan project · not affiliated with Nintendo / The Pokémon Company</div>`;
  ready.then(() => { const l = $('#tiLoad'); if (l) { l.textContent = ''; l.classList.add('done'); } });
  let stage = 'press', sel = 0;
  const items = () => [...el.querySelectorAll('#tiMenu button')];
  const focus = i => { const b = items(); sel = (i + b.length) % b.length; b.forEach((x, k) => x.classList.toggle('on', k === sel)); };
  const showMenu = () => {
    if (stage !== 'press') return; stage = 'menu'; sfx.coin(); music.title();
    $('#tiPress').hidden = true; const m = $('#tiMenu'); m.hidden = false; focus(0);
  };
  const finish = () => { stage = 'done'; removeEventListener('keydown', key, true); music.stop(1.2); el.classList.add('out'); document.body.classList.remove('at-title'); setTimeout(() => { el.hidden = true; el.classList.remove('out'); }, 700); };
  const goPlay = async () => {
    await ready;
    if (touch && isPortrait()) { // ask to rotate, lock landscape in the app, continue as soon as the phone is sideways
      stage = 'rotate'; $('#tiRotate').hidden = false; try { window.PokeboxNative?.landscape?.(); } catch {}
      await new Promise(res => { const mq = matchMedia('(orientation: landscape)'); const f = () => { if (mq.matches) { mq.removeEventListener?.('change', f); res(); } }; mq.addEventListener?.('change', f); setTimeout(function poll() { mq.matches ? res() : setTimeout(poll, 400); }, 400); });
    } else { try { window.PokeboxNative?.landscape?.(); } catch {} }
    sfx.burst(); finish(); onStart?.();
  };
  const act = a => { if (stage !== 'menu') return; sfx.click(); if (a === 'start') goPlay(); else if (a === 'cards') { finish(); onCards?.(); } else if (a === 'settings') { finish(); onSettings?.(); } };
  el.onclick = e => { const b = e.target.closest('#tiMenu button'); if (b) act(b.dataset.a); else if (stage === 'press') showMenu(); };
  const key = e => {
    if (stage !== 'done') e.stopPropagation(); // the world behind the title must not move
    if (stage === 'press') { e.preventDefault(); showMenu(); return; }
    if (stage !== 'menu') return;
    if (e.code === 'ArrowDown' || e.code === 'KeyS') { e.preventDefault(); focus(sel + 1); sfx.tick(); }
    else if (e.code === 'ArrowUp' || e.code === 'KeyW') { e.preventDefault(); focus(sel - 1); sfx.tick(); }
    else if (e.code === 'Enter' || e.code === 'Space' || e.code === 'KeyE') { e.preventDefault(); act(items()[sel].dataset.a); }
  };
  addEventListener('keydown', key, true);
  window.__titleSkip = () => { if (stage !== 'done') { finish(); onStart?.(); } };
}
