// Pokebox premium pack artwork — procedural (Canvas2D), original designs inspired by the MyAssets references.
// Pre-rendered to assets/premium/<id>.webp by tools/render_packs.mjs; drawn live as a fallback.
export const PACK_W = 1000, PACK_H = 1400;

function rng(seed) { let s = seed >>> 0; return () => ((s = (Math.imul(s, 1664525) + 1013904223) >>> 0) / 4294967296); }
const TAU = Math.PI * 2;

/* ---------- shared helpers ---------- */
function crimp(g, w, h, y0, y1, c1, c2) {
  const grd = g.createLinearGradient(0, y0, 0, y1); grd.addColorStop(0, c1); grd.addColorStop(.5, c2); grd.addColorStop(1, c1);
  g.fillStyle = grd; g.fillRect(0, y0, w, y1 - y0);
  g.save(); g.globalAlpha = .35; g.strokeStyle = '#000';
  for (let x = 0; x < w; x += 9) { g.beginPath(); g.moveTo(x, y0); g.lineTo(x, y1); g.lineWidth = 2; g.stroke(); }
  g.globalAlpha = .45; g.strokeStyle = '#fff'; for (let x = 4; x < w; x += 9) { g.beginPath(); g.moveTo(x, y0); g.lineTo(x, y1); g.lineWidth = 1.2; g.stroke(); }
  g.restore();
}
function sheen(g, w, h, a = .35, ang = -.5) {
  g.save(); g.globalCompositeOperation = 'screen';
  const grd = g.createLinearGradient(0, 0, w, h * .6);
  grd.addColorStop(0, 'rgba(255,255,255,0)'); grd.addColorStop(.32, `rgba(255,255,255,${a * .15})`); grd.addColorStop(.42, `rgba(255,255,255,${a})`);
  grd.addColorStop(.5, `rgba(255,255,255,${a * .1})`); grd.addColorStop(.7, `rgba(255,255,255,${a * .5})`); grd.addColorStop(.78, 'rgba(255,255,255,0)');
  g.fillStyle = grd; g.fillRect(0, 0, w, h); g.restore();
}
function grain(g, w, h, amt = 10, seed = 3) {
  const d = g.getImageData(0, 0, w, h), p = d.data, R = rng(seed);
  for (let i = 0; i < p.length; i += 4) { const n = (R() - .5) * amt; p[i] += n; p[i + 1] += n; p[i + 2] += n; }
  g.putImageData(d, 0, 0);
}
function bolt(g, pts) { g.beginPath(); g.moveTo(pts[0][0], pts[0][1]); for (let i = 1; i < pts.length; i++) g.lineTo(pts[i][0], pts[i][1]); g.closePath(); g.fill(); }
function wordmark(g, x, y, size, fill, stroke, text = 'POKEBOX', rot = -.06) {
  g.save(); g.translate(x, y); g.rotate(rot); g.font = `900 ${size}px "Anton", "Impact", "Arial Black", sans-serif`; g.textAlign = 'center'; g.textBaseline = 'middle';
  g.lineJoin = 'round'; g.lineWidth = size * .22; g.strokeStyle = 'rgba(0,0,0,.85)'; g.strokeText(text, 0, size * .05);
  g.lineWidth = size * .12; g.strokeStyle = stroke; g.strokeText(text, 0, 0); g.fillStyle = fill; g.fillText(text, 0, 0); g.restore();
}
function burstBadge(g, x, y, r, spikes, fill, stroke) {
  g.save(); g.beginPath();
  for (let i = 0; i <= spikes * 2; i++) { const a = i / (spikes * 2) * TAU - Math.PI / 2, rr = i % 2 ? r * .74 : r * (1 + (i % 4 ? .0 : .08)); g.lineTo(x + Math.cos(a) * rr * 1.45, y + Math.sin(a) * rr * .72); }
  g.closePath(); g.fillStyle = fill; g.fill(); g.lineWidth = 8; g.strokeStyle = stroke; g.stroke(); g.restore();
}

/* ---------- designs ---------- */
const DESIGNS = {
  // Yellow foil with a black jagged thunder band + red side bolts (video 1 + KLUTCH yellow pack)
  thunder(g, w, h) {
    const bg = g.createLinearGradient(0, 0, w, h); bg.addColorStop(0, '#fff36b'); bg.addColorStop(.35, '#ffd400'); bg.addColorStop(.7, '#f5c400'); bg.addColorStop(1, '#ffe24a');
    g.fillStyle = bg; g.fillRect(0, 0, w, h);
    // radial highlight (pillow)
    const rg = g.createRadialGradient(w * .42, h * .42, 40, w * .5, h * .5, w * .9); rg.addColorStop(0, 'rgba(255,255,210,.55)'); rg.addColorStop(1, 'rgba(160,110,0,.35)');
    g.fillStyle = rg; g.fillRect(0, 0, w, h);
    // black top band with a jagged thunder edge running down the middle
    g.fillStyle = '#141414';
    bolt(g, [[w * .18, 0], [w * .86, 0], [w * .78, h * .12], [w * .62, h * .19], [w * .7, h * .26], [w * .5, h * .41], [w * .56, h * .3], [w * .44, h * .27], [w * .52, h * .17], [w * .34, h * .12]]);
    g.fillStyle = '#2b2b2b'; bolt(g, [[w * .86, 0], [w, 0], [w, h * .06], [w * .9, h * .1]]);
    // dark grey secondary bolts
    g.fillStyle = '#3a3a3a';
    bolt(g, [[w * .3, h * .35], [w * .42, h * .44], [w * .37, h * .46], [w * .47, h * .6], [w * .31, h * .47], [w * .36, h * .45]]);
    bolt(g, [[w * .66, h * .4], [w * .6, h * .52], [w * .66, h * .52], [w * .56, h * .66], [w * .74, h * .5], [w * .68, h * .5]]);
    bolt(g, [[w * .46, h * .5], [w * .54, h * .62], [w * .5, h * .63], [w * .56, h * .74], [w * .43, h * .61], [w * .48, h * .6]]);
    // red side bolts
    g.fillStyle = '#ff2d4b';
    for (const s of [-1, 1]) {
      const x = s < 0 ? w * .06 : w * .94, d = s;
      bolt(g, [[x, h * .44], [x + d * w * .12, h * .5], [x + d * w * .05, h * .52], [x + d * w * .16, h * .6], [x + d * w * .06, h * .62], [x + d * w * .12, h * .72], [x - d * w * .02, h * .6], [x + d * w * .05, h * .58], [x - d * w * .03, h * .5]]);
    }
    g.fillStyle = '#c8102e'; bolt(g, [[w * .1, h * .7], [w * .2, h * .74], [w * .14, h * .76], [w * .22, h * .82], [w * .06, h * .76]]);
    burstBadge(g, w * .5, h * .86, w * .17, 11, '#ff2d4b', '#ffd400'); wordmark(g, w * .5, h * .86, 92, '#fff', '#c8102e');
    sheen(g, w, h, .45); crimp(g, w, h, 0, h * .05, '#8c7000', '#fff7a8'); crimp(g, w, h, h * .96, h, '#8c7000', '#fff7a8');
  },
  // Purple candy pack with gold rings + pink pearls (video 2)
  sugar(g, w, h) {
    const bg = g.createLinearGradient(0, 0, 0, h); bg.addColorStop(0, '#2a1a33'); bg.addColorStop(.45, '#5a2f63'); bg.addColorStop(1, '#b4658e');
    g.fillStyle = bg; g.fillRect(0, 0, w, h);
    const R = rng(21);
    for (let i = 0; i < 46; i++) {
      const x = R() * w, y = h * .06 + R() * h * .62, r = 16 + R() * 26, t = R() * TAU;
      g.save(); g.translate(x, y); g.rotate(t); g.scale(1, .45 + R() * .45);
      g.lineWidth = r * .32; const gg = g.createLinearGradient(-r, -r, r, r); gg.addColorStop(0, '#fff2a8'); gg.addColorStop(.5, '#e0a922'); gg.addColorStop(1, '#8a5a06');
      g.strokeStyle = gg; g.beginPath(); g.arc(0, 0, r, 0, TAU); g.stroke(); g.restore();
    }
    for (let i = 0; i < 38; i++) {
      const x = R() * w, y = h * .45 + R() * h * .5, r = 8 + R() * 16;
      const pg = g.createRadialGradient(x - r * .35, y - r * .35, r * .1, x, y, r); pg.addColorStop(0, '#ffd1e6'); pg.addColorStop(.4, '#ff3d8b'); pg.addColorStop(1, '#8e0f45');
      g.fillStyle = pg; g.beginPath(); g.arc(x, y, r, 0, TAU); g.fill();
    }
    const v = g.createRadialGradient(w / 2, h / 2, w * .2, w / 2, h / 2, w * .85); v.addColorStop(0, 'rgba(0,0,0,0)'); v.addColorStop(1, 'rgba(0,0,0,.45)'); g.fillStyle = v; g.fillRect(0, 0, w, h);
    wordmark(g, w * .5, h * .88, 88, '#ffe8f3', '#ff3d8b', 'POKEBOX', 0);
    sheen(g, w, h, .3); crimp(g, w, h, 0, h * .05, '#3a2340', '#b98fc4'); crimp(g, w, h, h * .96, h, '#6a2f50', '#f0b6d2');
  },
  // Dark geometric → crimson with gold chevrons (video 3, before upgrade)
  ascension(g, w, h) {
    const bg = g.createLinearGradient(0, 0, 0, h); bg.addColorStop(0, '#2c2c30'); bg.addColorStop(.42, '#232026'); bg.addColorStop(.72, '#5b1224'); bg.addColorStop(1, '#b3163c');
    g.fillStyle = bg; g.fillRect(0, 0, w, h);
    g.save(); g.strokeStyle = 'rgba(210,180,120,.55)'; g.lineWidth = 3;
    g.strokeRect(w * .1, h * .08, w * .8, h * .3);
    g.beginPath(); g.moveTo(w * .1, h * .2); g.lineTo(w * .9, h * .2); g.stroke();
    g.strokeStyle = 'rgba(255,255,255,.08)'; g.lineWidth = 26;
    for (let i = -4; i < 8; i++) { g.beginPath(); g.moveTo(w * (i * .18), h * .95); g.lineTo(w * (i * .18 + .7), h * .3); g.stroke(); }
    g.restore();
    g.fillStyle = 'rgba(255,255,255,.18)'; g.font = '600 26px "Barlow Condensed", sans-serif'; g.fillText('✦  POKEBOX  ASCENSION  SERIES', w * .14, h * .15);
    for (const s of [-1, 1]) {
      const x = w / 2 + s * w * .3; g.save(); g.translate(x, h * .86); g.scale(s, 1);
      const cg = g.createLinearGradient(-60, -60, 60, 60); cg.addColorStop(0, '#fff2c0'); cg.addColorStop(.5, '#c9a45a'); cg.addColorStop(1, '#6b4e1c');
      g.fillStyle = cg; g.beginPath(); g.moveTo(-70, 40); g.lineTo(10, -70); g.lineTo(40, -70); g.lineTo(-30, 40); g.closePath(); g.fill(); g.restore();
    }
    sheen(g, w, h, .22); crimp(g, w, h, 0, h * .05, '#2a2a2a', '#8a8a90'); crimp(g, w, h, h * .96, h, '#4a0b1a', '#e05070'); grain(g, w, h, 8);
  },
  // Upgraded obsidian pack with teal crystal stripe (video 3, after upgrade)
  obsidian(g, w, h) {
    const bg = g.createLinearGradient(0, 0, w, h); bg.addColorStop(0, '#2e3438'); bg.addColorStop(.5, '#15191c'); bg.addColorStop(1, '#262b2f');
    g.fillStyle = bg; g.fillRect(0, 0, w, h);
    g.strokeStyle = 'rgba(255,255,255,.12)'; g.lineWidth = 3;
    for (const x of [.12, .36, .64, .88]) { g.beginPath(); g.moveTo(w * x, h * .05); g.lineTo(w * x, h * .95); g.stroke(); }
    g.strokeStyle = 'rgba(214,180,110,.7)'; g.lineWidth = 4;
    g.beginPath(); g.moveTo(w * .1, h * .12); g.lineTo(w * .9, h * .12); g.stroke();
    g.beginPath(); g.moveTo(w * .4, h * .12); g.lineTo(w * .4, h * .74); g.lineTo(w * .5, h * .84); g.lineTo(w * .6, h * .74); g.lineTo(w * .6, h * .12); g.stroke();
    const tg = g.createLinearGradient(w * .44, 0, w * .56, 0); tg.addColorStop(0, '#0b6d62'); tg.addColorStop(.45, '#5cf2d6'); tg.addColorStop(.55, '#1fcfb2'); tg.addColorStop(1, '#075a50');
    g.fillStyle = tg; bolt(g, [[w * .445, h * .14], [w * .555, h * .14], [w * .555, h * .72], [w * .5, h * .79], [w * .445, h * .72]]);
    g.fillStyle = 'rgba(255,255,255,.55)'; g.fillRect(w * .488, h * .15, w * .012, h * .55);
    g.fillStyle = 'rgba(92,242,214,.9)'; g.font = '700 30px "Barlow Condensed", sans-serif'; g.textAlign = 'center'; g.fillText('OBSIDIAN  ·  ASCENDED', w / 2, h * .9);
    sheen(g, w, h, .3); crimp(g, w, h, 0, h * .05, '#1a1d20', '#7c868c'); crimp(g, w, h, h * .96, h, '#1a1d20', '#7c868c'); grain(g, w, h, 7);
  },
  // Pearl holo pack with lace scallops (KLUTCH white pack)
  frost(g, w, h) {
    const bg = g.createLinearGradient(0, 0, w, h); bg.addColorStop(0, '#f4fbff'); bg.addColorStop(.5, '#dff1f4'); bg.addColorStop(1, '#eef4ff');
    g.fillStyle = bg; g.fillRect(0, 0, w, h);
    const hol = g.createLinearGradient(0, 0, w, h * .8); ['rgba(170,235,255,.5)', 'rgba(220,190,255,.35)', 'rgba(255,200,235,.45)', 'rgba(190,255,220,.35)', 'rgba(170,235,255,.5)'].forEach((c, i, a) => hol.addColorStop(i / (a.length - 1), c));
    g.fillStyle = hol; g.fillRect(0, 0, w, h);
    g.save(); g.globalAlpha = .22; g.strokeStyle = '#3aa3a0'; g.lineWidth = 2.5; const R = rng(5);
    for (let i = 0; i < 90; i++) { const x = R() * w, y = R() * h * .75, r = 10 + R() * 30; g.beginPath(); for (let k = 0; k < 6; k++) { const a = k / 6 * TAU; g.moveTo(x, y); g.lineTo(x + Math.cos(a) * r, y + Math.sin(a) * r); } g.stroke(); }
    g.restore();
    const ir = g.createLinearGradient(0, h * .7, w, h); ['#b7f0ff', '#d6b8ff', '#ffc4e8', '#b8ffd9', '#b7f0ff'].forEach((c, i, a) => ir.addColorStop(i / (a.length - 1), c));
    g.fillStyle = ir; g.beginPath(); g.moveTo(0, h); g.lineTo(0, h * .74);
    for (let i = 0; i <= 6; i++) { const x = i / 6 * w; g.quadraticCurveTo(x - w / 12, h * .64, x, h * .74); }
    g.lineTo(w, h); g.closePath(); g.fill();
    g.fillStyle = 'rgba(80,140,200,.5)'; for (let i = 0; i < 7; i++) { g.beginPath(); g.ellipse(w * (.08 + i * .14), h * .78, 9, 26, .3, 0, TAU); g.fill(); }
    wordmark(g, w * .5, h * .88, 86, '#eaf6ff', '#6e88d8', 'POKEBOX', -.08);
    sheen(g, w, h, .5); crimp(g, w, h, 0, h * .05, '#9fb6c0', '#ffffff'); crimp(g, w, h, h * .96, h, '#9fb6c0', '#ffffff');
  },
  // Royal blue night pack with crescent moon + red eyes (KLUTCH blue pack)
  moon(g, w, h) {
    const bg = g.createRadialGradient(w / 2, h * .4, 40, w / 2, h / 2, w); bg.addColorStop(0, '#2d63ff'); bg.addColorStop(.6, '#1333b8'); bg.addColorStop(1, '#0a1a66');
    g.fillStyle = bg; g.fillRect(0, 0, w, h);
    const R = rng(9); g.fillStyle = '#fff5c8';
    for (let i = 0; i < 26; i++) { const x = R() * w, y = R() * h * .6, r = 2 + R() * 4; g.beginPath(); for (let k = 0; k < 8; k++) { const a = k / 8 * TAU, rr = k % 2 ? r * .35 : r * 1.6; g.lineTo(x + Math.cos(a) * rr, y + Math.sin(a) * rr); } g.fill(); }
    g.save(); g.shadowColor = '#fff3b0'; g.shadowBlur = 50; g.fillStyle = '#fff4c4';
    const cres = new Path2D(); cres.arc(w * .5, h * .3, w * .15, 0, TAU); cres.arc(w * .565, h * .265, w * .13, 0, TAU);
    const disc = new Path2D(); disc.arc(w * .5, h * .3, w * .15, 0, TAU); g.clip(disc); g.fill(cres, 'evenodd'); g.restore();
    for (const s of [-1, 1]) { g.save(); g.translate(w / 2 + s * w * .22, h * .5); g.scale(s, 1); g.fillStyle = '#e8202e';
      g.beginPath(); g.moveTo(-90, -40); g.quadraticCurveTo(30, -60, 70, 30); g.quadraticCurveTo(-10, 40, -90, -40); g.fill();
      g.fillStyle = '#0a0d2a'; g.beginPath(); g.ellipse(20, 0, 12, 26, .2, 0, TAU); g.fill(); g.restore(); }
    g.strokeStyle = '#d9b25a'; g.lineWidth = 10;
    for (const [x, y, a] of [[0, 0, 0], [w, 0, 1], [0, h, 3], [w, h, 2]]) { g.beginPath(); g.arc(x, y, w * .16, a * Math.PI / 2, a * Math.PI / 2 + Math.PI / 2); g.stroke(); }
    wordmark(g, w * .5, h * .86, 86, '#dfe8ff', '#2d63ff', 'POKEBOX', 0);
    sheen(g, w, h, .35); crimp(g, w, h, 0, h * .05, '#0a1a66', '#7fa0ff'); crimp(g, w, h, h * .96, h, '#0a1a66', '#7fa0ff');
  },
};

/* clear-sleeve collector packs (qhp reference): scenic art under a crinkled transparent wrapper */
function scene(g, w, h, sky, sun, ground, seed) {
  const bg = g.createLinearGradient(0, 0, 0, h); sky.forEach((c, i) => bg.addColorStop(i / (sky.length - 1), c)); g.fillStyle = bg; g.fillRect(0, 0, w, h);
  const R = rng(seed); g.fillStyle = 'rgba(255,255,255,.7)'; for (let i = 0; i < 120; i++) g.fillRect(R() * w, R() * h * .5, 1.5, 1.5);
  if (sun) { const pg = g.createRadialGradient(sun.x * w - sun.r * .3, sun.y * h - sun.r * .3, 5, sun.x * w, sun.y * h, sun.r); sun.c.forEach((c, i) => pg.addColorStop(i / (sun.c.length - 1), c)); g.fillStyle = pg; g.beginPath(); g.arc(sun.x * w, sun.y * h, sun.r, 0, TAU); g.fill(); }
  ground.forEach(([c, y0, amp, f]) => { g.fillStyle = c; g.beginPath(); g.moveTo(0, h); for (let x = 0; x <= w; x += 10) g.lineTo(x, y0 * h + Math.sin(x * f + seed) * amp + Math.sin(x * f * 2.7) * amp * .3); g.lineTo(w, h); g.fill(); });
}
function figure(g, x, y, s, c = '#0a0a0e') { g.fillStyle = c; g.beginPath(); g.moveTo(x, y - 70 * s); g.quadraticCurveTo(x + 16 * s, y - 64 * s, x + 14 * s, y - 40 * s); g.lineTo(x + 24 * s, y); g.lineTo(x - 24 * s, y); g.lineTo(x - 14 * s, y - 40 * s); g.quadraticCurveTo(x - 16 * s, y - 64 * s, x, y - 70 * s); g.fill(); }
function sleeve(g, w, h, code, seed) {
  g.save(); g.strokeStyle = 'rgba(255,255,255,.5)'; g.lineWidth = 2;
  g.beginPath(); g.moveTo(w * .08, h * .12); g.lineTo(w * .55, h * .12); g.lineTo(w * .6, h * .1); g.lineTo(w * .92, h * .1); g.lineTo(w * .92, h * .82); g.lineTo(w * .86, h * .9); g.lineTo(w * .08, h * .9); g.closePath(); g.stroke();
  // TRADING CARDS tag
  const tg = g.createLinearGradient(w * .6, 0, w * .92, 0); tg.addColorStop(0, '#fff'); tg.addColorStop(.5, '#ffe89a'); tg.addColorStop(1, '#fff');
  g.fillStyle = tg; g.fillRect(w * .6, h * .12, w * .3, 34); g.fillStyle = '#111'; g.font = '700 24px "Barlow Condensed", sans-serif'; g.textAlign = 'center'; g.fillText('T R A D I N G   C A R D S', w * .75, h * .12 + 25);
  // QR-style code (random, not scannable)
  const R = rng(seed), qx = w * .11, qy = h * .8, q = 7;
  g.fillStyle = '#fff'; g.fillRect(qx - 6, qy - 6, 21 * q + 12, 21 * q + 12); g.fillStyle = '#111';
  for (let i = 0; i < 21; i++) for (let j = 0; j < 21; j++) { const f = (i < 7 && j < 7) || (i > 13 && j < 7) || (i < 7 && j > 13); if (f ? ((i % 6 === 0 || j % 6 === 0 || (i % 7 > 1 && i % 7 < 5 && j % 7 > 1 && j % 7 < 5)) && !(i === 7 || j === 7)) : R() > .5) g.fillRect(qx + i * q, qy + j * q, q, q); }
  g.textAlign = 'right'; g.fillStyle = 'rgba(255,255,255,.75)'; g.font = '500 26px "Barlow Condensed", sans-serif'; g.fillText('COLLECTION', w * .88, h * .845); g.font = '700 30px "Barlow Condensed", sans-serif'; g.fillStyle = '#fff'; g.fillText(code, w * .88, h * .875);
  wordmark(g, w * .2, h * .16, 44, '#fff', '#6b7bff', 'PKB', -.12);
  // plastic wrinkles: soft white blobs + streaks
  g.globalCompositeOperation = 'screen'; const W = rng(seed * 7);
  for (let i = 0; i < 9; i++) {
    const x = W() * w, y = W() * h, rx = 60 + W() * 160, ry = 20 + W() * 70, a = W() * Math.PI;
    const wg = g.createRadialGradient(0, 0, 0, 0, 0, 1); wg.addColorStop(0, 'rgba(255,255,255,.55)'); wg.addColorStop(.5, 'rgba(255,255,255,.18)'); wg.addColorStop(1, 'rgba(255,255,255,0)');
    g.save(); g.translate(x, y); g.rotate(a); g.scale(rx, ry); g.fillStyle = wg; g.beginPath(); g.arc(0, 0, 1, 0, TAU); g.fill(); g.restore();
  }
  g.strokeStyle = 'rgba(255,255,255,.35)'; g.lineWidth = 3;
  for (let i = 0; i < 16; i++) { g.beginPath(); const x = W() * w, y = W() * h; g.moveTo(x, y); g.bezierCurveTo(x + 60 - W() * 120, y + 80, x + 90 - W() * 180, y + 160, x + 40 - W() * 80, y + 260); g.stroke(); }
  g.restore();
  // side seams
  g.fillStyle = 'rgba(255,255,255,.18)'; for (let y = 0; y < h; y += 6) { g.fillRect(0, y, 18, 2); g.fillRect(w - 18, y, 18, 2); }
  crimp(g, w, h, 0, h * .05, 'rgba(90,90,100,.9)', 'rgba(240,240,250,.9)'); crimp(g, w, h, h * .96, h, 'rgba(90,90,100,.9)', 'rgba(240,240,250,.9)');
}
DESIGNS.dusk = (g, w, h) => {
  scene(g, w, h, ['#1b1636', '#4a2b5c', '#a3445a', '#e0774a'], { x: .62, y: .28, r: 240, c: ['#ffc7a3', '#c9573c', '#5a1f2a'] },
    [['#3a1a24', .74, 16, .01], ['#1a0c12', .82, 10, .02]], 11);
  g.fillStyle = '#0b0710'; g.fillRect(w * .47, h * .42, 24, h * .34); g.beginPath(); g.moveTo(w * .47 - 20, h * .42); g.lineTo(w * .47 + 44, h * .42); g.lineTo(w * .47 + 12, h * .36); g.fill();
  figure(g, w * .3, h * .8, 1.1); wordmark(g, w * .5, h * .7, 70, '#fff', '#a3445a', 'STARFALL', 0);
  sleeve(g, w, h, 'SF0012026', 11);
};
DESIGNS.mist = (g, w, h) => {
  scene(g, w, h, ['#0c2229', '#1c4a52', '#4d8a8a', '#a8cfc6'], null, [['#0e2a2e', .6, 40, .006], ['#123238', .7, 22, .012], ['#1f4d50', .8, 6, .03]], 17);
  g.fillStyle = 'rgba(255,255,255,.08)'; for (let i = 0; i < 6; i++) g.fillRect(0, h * (.55 + i * .05), w, 18);
  figure(g, w * .5, h * .76, 1.4); wordmark(g, w * .5, h * .68, 70, '#e8fff9', '#1c4a52', 'MISTVALE', 0);
  sleeve(g, w, h, 'MV0012026', 17);
};
DESIGNS.dune = (g, w, h) => {
  scene(g, w, h, ['#3a1f0e', '#9c4f1c', '#e08a3a', '#f3c27a'], { x: .3, y: .3, r: 120, c: ['#fff1c9', '#ffb458', '#c46a20'] },
    [['#a8541b', .58, 30, .004], ['#7a3a12', .7, 26, .006], ['#4a200a', .84, 14, .01]], 23);
  figure(g, w * .7, h * .7, .9); g.font = '300 64px "Barlow Condensed", sans-serif'; g.textAlign = 'center'; g.fillStyle = '#fff'; g.fillText('S  A  N  D  R  E  A  C  H', w * .5, h * .66);
  sleeve(g, w, h, 'SR0012026', 23);
};

// odds: hit-slot rarity table [rarity, p] for the last 3 of 10 cards
const HIT_STD = [[2, .35], [3, .3], [4, .2], [5, .1], [6, .05]];
// types: the pack's theme — ~90% of its cards are Pokémon of these types (Trainer/Energy cards never appear in vault packs)
export const PREMIUM = [
  { code: 'PX-THUNDER', types: ['Lightning'], name: 'Thunder Surge Pack', art: 'thunder', fx: 'electric', price: 500, tags: ['VAULT', 'HOLO+ HITS'], stock: 500, odds: [[3, .45], [4, .35], [5, .13], [6, .07]], blurb: 'Comic-burst thunder opening. Three Holo Rare or better hits in every pack.' },
  { code: 'PX-SUGAR', types: ['Psychic', 'Colorless'], name: 'Sugar Rush Pack', art: 'sugar', fx: 'candy', price: 640, tags: ['VAULT', 'CANDY RAIN'], stock: 500, odds: [[3, .4], [4, .3], [5, .2], [6, .1]], blurb: 'Pearls and gold rings pour in until the pack is buried. Boosted Illustration Rares.' },
  { code: 'PX-ASCEND', types: ['Dragon', 'Fire', 'Darkness'], name: 'Ascension Pack', art: 'ascension', upgrade: 'obsidian', fx: 'legendary', price: 1200, tags: ['LEGENDARY', 'UPGRADE'], stock: 250, odds: [[4, .5], [5, .3], [6, .2]], blurb: 'Burns, charges and ascends into an Obsidian pack. Three Ultra Rare or better hits.' },
  { code: 'PX-FROST', types: ['Water'], name: 'Frost Holo Pack', art: 'frost', fx: 'classic', price: 470, tags: ['VAULT', 'HOLO'], stock: 500, odds: [[3, .6], [4, .2], [5, .12], [6, .08]], blurb: 'Pearl-holo wrapper. Boosted Holo Rare odds.' },
  { code: 'PX-MOON', types: ['Darkness', 'Psychic'], name: 'Moonlight Pack', art: 'moon', fx: 'classic', price: 740, tags: ['VAULT', 'NIGHT'], stock: 500, odds: [[3, .2], [4, .55], [5, .15], [6, .1]], blurb: 'Night-sky foil. Boosted Ultra Rare odds.' },
  { code: 'PX-SLEEVE-SF', types: ['Metal', 'Psychic'], name: 'Starfall Collection', art: 'dusk', fx: 'classic', price: 430, tags: ['CLEAR SLEEVE', 'SF0012026'], stock: 500, odds: HIT_STD, blurb: 'Collector series in a clear crinkle sleeve.' },
  { code: 'PX-SLEEVE-MV', types: ['Water', 'Grass'], name: 'Mistvale Collection', art: 'mist', fx: 'classic', price: 360, tags: ['CLEAR SLEEVE', 'MV0012026'], stock: 500, odds: HIT_STD, blurb: 'Collector series in a clear crinkle sleeve.' },
  { code: 'PX-SLEEVE-SR', types: ['Fighting', 'Fire'], name: 'Sandreach Collection', art: 'dune', fx: 'classic', price: 460, tags: ['CLEAR SLEEVE', 'SR0012026'], stock: 500, odds: HIT_STD, blurb: 'Collector series in a clear crinkle sleeve.' },
];
export function drawPack(id, canvas) {
  canvas.width = PACK_W; canvas.height = PACK_H; const g = canvas.getContext('2d');
  (DESIGNS[id] || DESIGNS.thunder)(g, PACK_W, PACK_H); return canvas;
}
const cache = {};
export function packURL(id) {
  if (cache[id]) return cache[id];
  return (cache[id] = 'assets/premium/' + id + '.webp');
}
export function packDataURL(id) { const c = drawPack(id, document.createElement('canvas')); return c.toDataURL('image/webp', .92); }
