// Pokebox — progression layer: trainer look + cosmetics, Journey (story chapters), challenges, activity tracking.
// Design source of truth: design/STORY_BIBLE.md
import * as C from './core.js';
import { DB } from './core.js';

/* ================================================================== state */
const S = () => C.S;
export function ensure() {
  const s = S();
  s.name ||= 'Ranger';
  s.look = Object.assign({ body: 'm', skin: 'sk2', hair: 'short', hairColor: 'hc1', eyes: 'round', hat: 'none', top: 'tee', topColor: 'tc1', acc: 'none', frame: 'fr0', title: 'ti0' }, s.look || {});
  s.story = Object.assign({ ch: 0, done: {}, choice: null, seen: {}, areas: { harbor: true } }, s.story || {});
  s.cnt = Object.assign({ packs: s.packs || 0, cards: 0, wins: s.battle?.wins || 0, rares: 0, vault: 0, sold: 0, bought: 0, streak: 0, bestStreak: 0, glyphs: 0, echoes: 0, talks: 0, typeWins: {}, vaultBy: {} }, s.cnt || {});
  s.chal = Object.assign({ day: -1, week: -1, base: {}, wbase: {}, claimed: {} }, s.chal || {});
  s.stars ||= 0; s.unlocks ||= {}; s.world ||= { found: {}, pos: null };
  return s;
}

/* ================================================================== cosmetics */
// unlock: {t:'free'} | {t:'level',n} | {t:'chapter',n} (chapter index completed) | {t:'stars',n} | {t:'ladder',n} (trainer tier beaten)
//         {t:'sets',n} (set bonuses claimed) | {t:'vault'} (opened any vault pack) | {t:'choice',v} (chapter-4 choice)
const F = { t: 'free' };
export const SLOTS = [
  { id: 'body', name: 'Body' }, { id: 'skin', name: 'Skin' }, { id: 'hair', name: 'Hair' }, { id: 'hairColor', name: 'Hair colour' }, { id: 'eyes', name: 'Eyes' },
  { id: 'hat', name: 'Headwear' }, { id: 'top', name: 'Outfit' }, { id: 'topColor', name: 'Outfit colour' }, { id: 'acc', name: 'Accessory' },
  { id: 'frame', name: 'Card frame' }, { id: 'title', name: 'Title' },
];
export const ITEMS = [
  // body type (3D model family) — free
  { id: 'm', slot: 'body', name: 'Build A', u: F }, { id: 'f', slot: 'body', name: 'Build B', u: F },
  // skin — always free
  ...['#ffe0c7', '#f6cfa9', '#e4b48a', '#c68b62', '#9a6442', '#6e4630'].map((c, i) => ({ id: 'sk' + i, slot: 'skin', name: 'Tone ' + (i + 1), c, u: F })),
  // hair styles
  { id: 'short', slot: 'hair', name: 'Short', u: F }, { id: 'bob', slot: 'hair', name: 'Bob', u: F }, { id: 'long', slot: 'hair', name: 'Long', u: F },
  { id: 'spiky', slot: 'hair', name: 'Spiky', u: { t: 'level', n: 3 } }, { id: 'ponytail', slot: 'hair', name: 'Ponytail', u: { t: 'level', n: 5 } },
  { id: 'messy', slot: 'hair', name: 'Courier mess', u: { t: 'chapter', n: 1 } }, { id: 'braids', slot: 'hair', name: 'Twin braids', u: { t: 'stars', n: 10 } },
  { id: 'buzz', slot: 'hair', name: 'Buzz', u: { t: 'ladder', n: 2 } },
  // hair colours
  ...[['hc0', '#2b2522', 'Ink', F], ['hc1', '#5a3a26', 'Chestnut', F], ['hc2', '#c9a064', 'Sand', F], ['hc3', '#a23c2a', 'Ember', { t: 'level', n: 4 }],
    ['hc4', '#e8e4dc', 'Silver', { t: 'chapter', n: 3 }], ['hc5', '#3c6fd6', 'Relay blue', { t: 'stars', n: 5 }], ['hc6', '#e05a9c', 'Festival pink', { t: 'vault' }],
    ['hc7', '#57c28f', 'Mistvale green', { t: 'chapter', n: 2 }], ['hc8', '#f2c230', 'Voltspire gold', { t: 'chapter', n: 5 }], ['hc9', '#7d4bd8', 'Glyph violet', { t: 'chapter', n: 7 }]]
    .map(([id, c, name, u]) => ({ id, slot: 'hairColor', name, c, u })),
  // eyes
  { id: 'round', slot: 'eyes', name: 'Round', u: F }, { id: 'sharp', slot: 'eyes', name: 'Sharp', u: F }, { id: 'happy', slot: 'eyes', name: 'Cheerful', u: { t: 'level', n: 2 } },
  { id: 'glyph', slot: 'eyes', name: 'Glyph-lit', u: { t: 'chapter', n: 7 } },
  // headwear
  { id: 'none', slot: 'hat', name: 'None', u: F }, { id: 'cap', slot: 'hat', name: 'Ranger cap', u: F }, { id: 'beanie', slot: 'hat', name: 'Beanie', u: { t: 'level', n: 6 } },
  { id: 'visor', slot: 'hat', name: 'Sport visor', u: { t: 'stars', n: 15 } }, { id: 'phones', slot: 'hat', name: 'Relay headset', u: { t: 'chapter', n: 1 } },
  { id: 'beret', slot: 'hat', name: 'Observatory beret', u: { t: 'chapter', n: 4 } }, { id: 'wide', slot: 'hat', name: 'Dune hat', u: { t: 'chapter', n: 3 } },
  { id: 'crown', slot: 'hat', name: 'Champion laurel', u: { t: 'ladder', n: 8 } },
  // outfits
  { id: 'tee', slot: 'top', name: 'Tee', u: F }, { id: 'hoodie', slot: 'top', name: 'Hoodie', u: F }, { id: 'jacket', slot: 'top', name: 'Field jacket', u: { t: 'level', n: 4 } },
  { id: 'ranger', slot: 'top', name: 'Lattice Ranger vest', u: { t: 'chapter', n: 1 } }, { id: 'labcoat', slot: 'top', name: 'Lab coat', u: { t: 'choice', v: 'vale' } },
  { id: 'robe', slot: 'top', name: 'Archivist mantle', u: { t: 'choice', v: 'sable' } }, { id: 'scarf', slot: 'top', name: 'Frostline scarf', u: { t: 'chapter', n: 6 } },
  { id: 'bomber', slot: 'top', name: 'Warden tactical', u: { t: 'ladder', n: 5 } },
  { id: 'summer', slot: 'top', name: 'Harbor summer', u: { t: 'level', n: 8 } }, { id: 'crew', slot: 'top', name: 'Relay crew', u: { t: 'chapter', n: 5 } },
  { id: 'relay', slot: 'top', name: 'Relay suit', u: { t: 'chapter', n: 7 } },
  // outfit colours
  ...[['tc0', '#2e3440', 'Graphite', F], ['tc1', '#d8483c', 'Signal red', F], ['tc2', '#3d8fd6', 'Harbor blue', F], ['tc3', '#e9e2cf', 'Bone', { t: 'level', n: 2 }],
    ['tc4', '#5fae4f', 'Reed', { t: 'chapter', n: 2 }], ['tc5', '#e8903c', 'Dune', { t: 'chapter', n: 3 }], ['tc6', '#7b5cff', 'Pokebox violet', { t: 'stars', n: 20 }],
    ['tc7', '#f2c230', 'Volt', { t: 'chapter', n: 5 }], ['tc8', '#9fd8f0', 'Ice', { t: 'chapter', n: 6 }], ['tc9', '#161218', 'Obsidian', { t: 'chapter', n: 7 }]]
    .map(([id, c, name, u]) => ({ id, slot: 'topColor', name, c, u })),
  // accessories
  { id: 'none', slot: 'acc', name: 'None', u: F }, { id: 'glasses', slot: 'acc', name: 'Round glasses', u: F }, { id: 'goggles', slot: 'acc', name: 'Courier goggles', u: { t: 'chapter', n: 2 } },
  { id: 'bandaid', slot: 'acc', name: 'Bandage', u: { t: 'level', n: 3 } }, { id: 'earring', slot: 'acc', name: 'Lattice earring', u: { t: 'stars', n: 25 } },
  { id: 'paint', slot: 'acc', name: 'Volt face paint', u: { t: 'vaultCode', code: 'PX-THUNDER' } }, { id: 'monocle', slot: 'acc', name: 'Echo lens', u: { t: 'sets', n: 1 } },
  { id: 'mask', slot: 'acc', name: 'Relay mask', u: { t: 'chapter', n: 7 } },
  // trainer card frames
  ...[['fr0', 'Standard', 'linear-gradient(135deg,#3a3448,#1a1622)', F], ['fr1', 'Harbor', 'linear-gradient(135deg,#1c4b7a,#3d8fd6,#1c4b7a)', { t: 'level', n: 5 }],
    ['fr2', 'Mistvale', 'linear-gradient(135deg,#1f4d50,#57c28f,#1f4d50)', { t: 'chapter', n: 2 }], ['fr3', 'Sandreach', 'linear-gradient(135deg,#7a3a12,#e8903c,#7a3a12)', { t: 'chapter', n: 3 }],
    ['fr4', 'Gold foil', 'linear-gradient(135deg,#6b4a12,#ffe08a,#c9a24a,#6b4a12)', { t: 'stars', n: 30 }], ['fr5', 'Holo', 'linear-gradient(135deg,#b7f0ff,#d6b8ff,#ffc4e8,#b8ffd9)', { t: 'ladder', n: 6 }],
    ['fr6', 'Obsidian', 'linear-gradient(135deg,#0b0b0e,#2b2f33,#5cf2d6,#0b0b0e)', { t: 'chapter', n: 7 }], ['fr7', 'Glyph', 'repeating-linear-gradient(45deg,#2a1450 0 8px,#4b2a8a 8px 16px)', { t: 'stars', n: 50 }]]
    .map(([id, name, bg, u]) => ({ id, slot: 'frame', name, bg, u })),
  // titles
  ...[['ti0', 'Rookie Ranger', F], ['ti1', 'Pack Ripper', { t: 'level', n: 5 }], ['ti2', 'Fog Walker', { t: 'chapter', n: 2 }], ['ti3', 'Glass Reader', { t: 'chapter', n: 3 }],
    ['ti4', 'Signal Hunter', { t: 'chapter', n: 4 }], ['ti5', 'Stormbound', { t: 'chapter', n: 5 }], ['ti6', 'Echo Warden', { t: 'chapter', n: 7 }], ['ti7', 'Set Master', { t: 'sets', n: 1 }],
    ['ti8', 'Champion', { t: 'ladder', n: 8 }], ['ti9', 'Challenge Addict', { t: 'stars', n: 40 }]]
    .map(([id, name, u]) => ({ id, slot: 'title', name, u })),
];
export const item = (slot, id) => ITEMS.find(x => x.slot === slot && x.id === id) || ITEMS.find(x => x.slot === slot);

export function unlockReason(u) {
  switch (u.t) {
    case 'free': return 'Available';
    case 'level': return `Reach trainer level ${u.n}`;
    case 'chapter': return `Finish Journey chapter ${u.n}`;
    case 'stars': return `Earn ${u.n} challenge stars`;
    case 'ladder': return `Beat ${C.S.battle && ['Youngster Joey', 'Lass Mira', 'Hiker Dom', 'Ace Trainer Kai', 'Gym Leader Vera', 'Elite Sable', 'Elite Orin', 'Champion Lyra'][u.n - 1] || 'the ladder'}`;
    case 'sets': return `Complete ${u.n} binder set${u.n > 1 ? 's' : ''}`;
    case 'vault': return 'Open any Vault pack';
    case 'vaultCode': return 'Open a Thunder Surge pack';
    case 'choice': return u.v === 'vale' ? 'Side with Dr. Vale in chapter 4' : 'Side with Warden Sable in chapter 4';
  }
  return '';
}
export function isUnlocked(it) {
  const s = ensure(), u = it.u;
  switch (u.t) {
    case 'free': return true;
    case 'level': return C.levelInfo().lv >= u.n;
    case 'chapter': return (s.story.ch || 0) >= u.n;
    case 'stars': return s.stars >= u.n;
    case 'ladder': return !!s.battle.beaten[u.n - 1];
    case 'sets': return Object.keys(s.claimed || {}).length >= u.n;
    case 'vault': return Object.keys(s.cnt.vaultBy).length > 0;
    case 'vaultCode': return (s.cnt.vaultBy[u.code] || 0) > 0;
    case 'choice': return s.story.choice === u.v;
  }
  return false;
}
export function newlyUnlocked() { // items unlocked since the player last looked (for the red dot + toast)
  const s = ensure(), seen = s.unlocks, fresh = [];
  for (const it of ITEMS) { const k = it.slot + ':' + it.id; if (it.u.t !== 'free' && isUnlocked(it) && !seen[k]) { seen[k] = Date.now(); fresh.push(it); } }
  if (fresh.length) C.save();
  return fresh;
}

/* ================================================================== avatar (layered SVG portrait) */
const shade = (hex, k) => { const n = parseInt(hex.slice(1), 16), f = v => Math.max(0, Math.min(255, Math.round(v * k))); return '#' + [(n >> 16) & 255, (n >> 8) & 255, n & 255].map(f).map(v => v.toString(16).padStart(2, '0')).join(''); };
const HAIR_BACK = {
  short: '', spiky: '', buzz: '', messy: '',
  bob: '<path d="M56 96 C50 46 150 46 144 96 L148 134 C132 144 68 144 52 134 Z" fill="H"/>',
  long: '<path d="M56 92 C48 40 152 40 144 92 L152 178 C130 188 70 188 48 178 Z" fill="H"/>',
  ponytail: '<path d="M140 78 C168 84 172 124 158 158 C150 140 150 110 140 98 Z" fill="H"/>',
  braids: '<path d="M60 108 C50 130 52 160 58 176 L68 176 C66 150 66 130 70 112 Z M140 108 C150 130 148 160 142 176 L132 176 C134 150 134 130 130 112 Z" fill="H"/><g fill="HD"><circle cx="61" cy="178" r="5"/><circle cx="139" cy="178" r="5"/></g>',
};
const HAIR_FRONT = {
  short: '<path d="M59 94 C54 48 146 48 141 94 C134 76 118 70 100 72 C84 70 70 74 59 94 Z" fill="H"/><path d="M72 76 C84 66 104 64 120 70 C108 70 90 74 80 84 Z" fill="HL" opacity=".5"/>',
  bob: '<path d="M58 98 C52 44 148 44 142 98 C140 86 136 80 128 78 L72 78 C64 80 60 86 58 98 Z" fill="H"/><path d="M70 60 C90 50 116 50 132 60" stroke="HL" stroke-width="4" fill="none" opacity=".5"/>',
  long: '<path d="M58 100 C50 44 150 44 142 100 C136 80 122 70 104 72 C112 80 110 86 96 88 C86 80 74 82 58 100 Z" fill="H"/>',
  spiky: '<path d="M58 92 L56 62 L70 70 L72 44 L88 60 L100 36 L112 60 L128 44 L130 70 L144 62 L142 92 C132 74 68 74 58 92 Z" fill="H"/>',
  ponytail: '<path d="M59 94 C54 46 146 46 141 94 C132 78 116 72 98 74 C82 74 68 80 59 94 Z" fill="H"/><circle cx="140" cy="80" r="6" fill="HD"/>',
  messy: '<path d="M57 96 C50 46 150 46 143 96 L136 80 L128 90 L122 74 L110 86 L102 72 L92 86 L84 74 L74 88 L66 78 Z" fill="H"/>',
  braids: '<path d="M59 96 C54 46 146 46 141 96 C136 82 124 76 100 76 C76 76 64 82 59 96 Z" fill="H"/><path d="M100 50 L100 76" stroke="HD" stroke-width="2"/>',
  buzz: '<path d="M62 86 C60 52 140 52 138 86 C126 72 74 72 62 86 Z" fill="H" opacity=".85"/>',
};
const EYES = {
  round: '<g fill="#221a1a"><ellipse cx="85" cy="100" rx="5" ry="6.5"/><ellipse cx="115" cy="100" rx="5" ry="6.5"/></g><g fill="#fff"><circle cx="87" cy="98" r="1.8"/><circle cx="117" cy="98" r="1.8"/></g>',
  sharp: '<g fill="#221a1a"><path d="M77 100 Q85 93 93 99 Q85 104 77 100Z"/><path d="M107 99 Q115 93 123 100 Q115 104 107 99Z"/></g><g stroke="#221a1a" stroke-width="2.5" stroke-linecap="round"><path d="M77 91 L92 94"/><path d="M108 94 L123 91"/></g>',
  happy: '<g stroke="#221a1a" stroke-width="3.2" fill="none" stroke-linecap="round"><path d="M79 101 Q85 94 91 101"/><path d="M109 101 Q115 94 121 101"/></g>',
  glyph: '<g fill="#7d4bd8"><ellipse cx="85" cy="100" rx="5.5" ry="7"/><ellipse cx="115" cy="100" rx="5.5" ry="7"/></g><g fill="#e6d6ff"><path d="M85 95 L87 100 L85 105 L83 100Z"/><path d="M115 95 L117 100 L115 105 L113 100Z"/></g>',
};
const HATS = {
  none: '',
  cap: '<path d="M58 80 C58 44 142 44 142 80 Z" fill="T"/><path d="M58 80 C80 74 120 74 142 80 C150 82 162 86 164 92 C140 86 90 84 58 86 Z" fill="TD"/><circle cx="100" cy="60" r="8" fill="#fff"/><path d="M92 60 L108 60" stroke="T" stroke-width="3"/>',
  beanie: '<path d="M56 84 C54 36 146 36 144 84 Z" fill="T"/><rect x="54" y="76" width="92" height="14" rx="6" fill="TD"/><circle cx="100" cy="36" r="8" fill="TL"/>',
  visor: '<path d="M58 78 C80 70 120 70 142 78 L142 86 C120 80 80 80 58 86 Z" fill="T"/><path d="M60 84 C90 80 130 80 160 92 C130 90 90 90 60 90 Z" fill="TD"/>',
  phones: '<path d="M60 92 C56 38 144 38 140 92" stroke="#2a2a30" stroke-width="7" fill="none"/><rect x="50" y="86" width="16" height="26" rx="6" fill="T"/><rect x="134" y="86" width="16" height="26" rx="6" fill="T"/><path d="M58 108 C60 124 76 130 86 128" stroke="#2a2a30" stroke-width="3" fill="none"/><circle cx="87" cy="128" r="3" fill="T"/>',
  beret: '<path d="M54 76 C50 50 100 38 142 58 C152 64 150 76 140 80 C112 72 84 72 54 80 Z" fill="T"/><circle cx="104" cy="44" r="4" fill="TD"/>',
  wide: '<ellipse cx="100" cy="80" rx="68" ry="12" fill="TD"/><path d="M66 80 C66 44 134 44 134 80 Z" fill="T"/><rect x="66" y="70" width="68" height="8" fill="TL" opacity=".7"/>',
  crown: '<g fill="#e7c14a" stroke="#8a6a12" stroke-width="1.5"><path d="M60 76 C70 64 80 60 88 62 C82 66 78 70 74 78 Z"/><path d="M140 76 C130 64 120 60 112 62 C118 66 122 70 126 78 Z"/><path d="M78 66 C86 56 94 54 100 54 C106 54 114 56 122 66 C112 62 88 62 78 66 Z"/></g>',
};
const ACC = {
  none: '',
  glasses: '<g stroke="#2a2430" stroke-width="2.5" fill="rgba(255,255,255,.15)"><circle cx="85" cy="100" r="10"/><circle cx="115" cy="100" r="10"/><path d="M95 100 L105 100" fill="none"/></g>',
  goggles: '<g><rect x="66" y="64" width="68" height="16" rx="8" fill="#2a2a30"/><circle cx="86" cy="72" r="8" fill="#7fd3ff" stroke="#e8a33c" stroke-width="2"/><circle cx="114" cy="72" r="8" fill="#7fd3ff" stroke="#e8a33c" stroke-width="2"/></g>',
  bandaid: '<g transform="rotate(-20 118 116)"><rect x="108" y="112" width="20" height="8" rx="3" fill="#f3d2a8" stroke="#c9a37a"/></g>',
  earring: '<circle cx="62" cy="114" r="3.5" fill="#5cf2d6" stroke="#0b6d62"/>',
  paint: '<g fill="#f2c230"><path d="M70 110 L80 106 L76 112 L86 110 L72 118 Z"/><path d="M130 110 L120 106 L124 112 L114 110 L128 118 Z"/></g>',
  monocle: '<circle cx="115" cy="100" r="11" fill="rgba(92,242,214,.2)" stroke="#c9a24a" stroke-width="2.5"/><path d="M126 102 C132 116 132 130 126 140" stroke="#c9a24a" stroke-width="1.5" fill="none"/>',
  mask: '<path d="M70 110 C80 106 120 106 130 110 L128 124 C116 134 84 134 72 124 Z" fill="#1e2126"/><path d="M78 118 L122 118" stroke="#5cf2d6" stroke-width="2"/>',
};
function topSVG(style, c) {
  const d = shade(c, .72), l = shade(c, 1.2);
  const base = `<path d="M26 222 C26 176 58 154 100 154 C142 154 174 176 174 222 Z" fill="${c}"/>`;
  switch (style) {
    case 'hoodie': return `<path d="M60 160 C60 140 140 140 140 160 L130 170 C110 158 90 158 70 170 Z" fill="${d}"/>${base}<path d="M92 158 L90 196 M108 158 L110 196" stroke="#fff" stroke-width="2.5"/><path d="M70 205 L130 205 L126 222 L74 222 Z" fill="${d}" opacity=".6"/>`;
    case 'jacket': return `${base}<path d="M86 154 L100 222 L114 154 Z" fill="#eee9dc"/><path d="M86 154 L78 190 L100 222 M114 154 L122 190 L100 222" stroke="${d}" stroke-width="3" fill="none"/>`;
    case 'ranger': return `${base}<path d="M80 156 L100 222 L120 156" fill="#3a3f36"/><rect x="58" y="178" width="22" height="16" rx="3" fill="${d}"/><rect x="120" y="178" width="22" height="16" rx="3" fill="${d}"/><circle cx="128" cy="170" r="6" fill="#ffd257" stroke="#8a6a12"/>`;
    case 'labcoat': return `<path d="M26 222 C26 176 58 154 100 154 C142 154 174 176 174 222 Z" fill="#f4f4f2"/><path d="M84 154 L100 200 L116 154 Z" fill="${c}"/><path d="M84 154 L74 196 L92 222 M116 154 L126 196 L108 222" stroke="#cfcfca" stroke-width="3" fill="none"/>`;
    case 'robe': return `${base}<path d="M62 158 C80 148 120 148 138 158 L130 176 C112 166 88 166 70 176 Z" fill="${d}"/><path d="M76 170 L124 170" stroke="#e7c14a" stroke-width="2" stroke-dasharray="5 3"/>`;
    case 'scarf': return `${base}<path d="M64 150 C82 164 118 164 136 150 L140 166 C116 180 84 180 60 166 Z" fill="#d8483c"/><path d="M118 168 L124 206 L110 206 Z" fill="#b8382e"/>`;
    case 'bomber': return `${base}<rect x="60" y="150" width="80" height="12" rx="6" fill="${d}"/><path d="M100 160 L100 222" stroke="${l}" stroke-width="3"/><path d="M40 206 L160 206" stroke="${d}" stroke-width="6"/>`;
    default: return `${base}<path d="M86 156 Q100 170 114 156" stroke="${d}" stroke-width="4" fill="none"/>`;
  }
}
export function avatarSVG(look, { size = 160, bg = true } = {}) {
  const L = Object.assign({}, ensureLookDefaults(), look);
  const skin = item('skin', L.skin).c, hair = item('hairColor', L.hairColor).c, top = item('topColor', L.topColor).c;
  const sd = shade(skin, .86), hd = shade(hair, .7), hl = shade(hair, 1.35);
  const hatC = L.top === 'labcoat' ? '#3d8fd6' : top;
  const fill = s => s.replace(/"HD"/g, `"${hd}"`).replace(/"HL"/g, `"${hl}"`).replace(/"H"/g, `"${hair}"`);
  const hatFill = s => s.replace(/"TD"/g, `"${shade(hatC, .7)}"`).replace(/"TL"/g, `"${shade(hatC, 1.3)}"`).replace(/"T"/g, `"${hatC}"`);
  return `<svg class="av" viewBox="0 0 200 222" style="width:${size}px;height:${Math.round(size * 1.11)}px" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    ${bg ? `<defs><radialGradient id="ab" cx="50%" cy="40%" r="70%"><stop offset="0" stop-color="#3a2a5a"/><stop offset="1" stop-color="#140f20"/></radialGradient></defs><rect width="200" height="222" rx="18" fill="url(#ab)"/>` : ''}
    ${fill(HAIR_BACK[L.hair] || '')}
    ${topSVG(L.top, top)}
    <rect x="88" y="126" width="24" height="32" rx="10" fill="${sd}"/>
    <ellipse cx="61" cy="104" rx="6" ry="9" fill="${sd}"/><ellipse cx="139" cy="104" rx="6" ry="9" fill="${sd}"/>
    <ellipse cx="100" cy="98" rx="40" ry="44" fill="${skin}"/>
    <ellipse cx="80" cy="114" rx="7" ry="4" fill="#ff8a8a" opacity=".25"/><ellipse cx="120" cy="114" rx="7" ry="4" fill="#ff8a8a" opacity=".25"/>
    ${EYES[L.eyes] || EYES.round}
    <path d="M92 121 Q100 127 108 121" stroke="#7a3b32" stroke-width="2.6" fill="none" stroke-linecap="round"/>
    ${fill(HAIR_FRONT[L.hair] || HAIR_FRONT.short)}
    ${ACC[L.acc] || ''}
    ${hatFill(HATS[L.hat] || '')}
  </svg>`;
}
function ensureLookDefaults() { return { skin: 'sk2', hair: 'short', hairColor: 'hc1', eyes: 'round', hat: 'none', top: 'tee', topColor: 'tc1', acc: 'none' }; }

/* story cast (same renderer) */
export const CAST = {
  vale: { name: 'Dr. Ione Vale', role: 'Head of Pokébox Labs', look: { body: 'f', skin: 'sk1', hair: 'bob', hairColor: 'hc4', eyes: 'sharp', hat: 'none', top: 'labcoat', topColor: 'tc6', acc: 'glasses' } },
  rho: { name: 'Rho', role: 'Relay courier', look: { body: 'm', skin: 'sk3', hair: 'messy', hairColor: 'hc3', eyes: 'happy', hat: 'none', top: 'hoodie', topColor: 'tc5', acc: 'goggles' } },
  sable: { name: 'Warden Sable', role: 'The Archivists', look: { body: 'f', skin: 'sk4', hair: 'long', hairColor: 'hc0', eyes: 'sharp', hat: 'none', top: 'robe', topColor: 'tc9', acc: 'monocle' } },
  joey: { name: 'Youngster Joey', role: 'Circuit Warden · Route 1', look: { body: 'm', skin: 'sk0', hair: 'short', hairColor: 'hc1', eyes: 'round', hat: 'cap', topColor: 'tc2', top: 'tee', acc: 'none' } },
  kai: { name: 'Ace Trainer Kai', role: 'Circuit Warden · Voltspire', look: { body: 'm', skin: 'sk2', hair: 'spiky', hairColor: 'hc8', eyes: 'sharp', hat: 'none', top: 'bomber', topColor: 'tc7', acc: 'paint' } },
  glyph: { name: 'GLYPH', role: '???', look: { body: 'm', skin: 'sk5', hair: 'buzz', hairColor: 'hc9', eyes: 'glyph', hat: 'none', top: 'robe', topColor: 'tc9', acc: 'mask' } },
};

/* ================================================================== activity tracking */
const listeners = new Set();
export const onProgress = fn => (listeners.add(fn), () => listeners.delete(fn));
export function track(ev, d = {}) {
  const s = ensure(), c = s.cnt;
  if (ev === 'pack') { c.packs++; c.cards += d.cards.length; c.rares += d.cards.filter(x => x.r >= 4).length; if (d.vault) { c.vault++; c.vaultBy[d.code] = (c.vaultBy[d.code] || 0) + 1; } }
  else if (ev === 'battle') { if (d.win) { c.wins++; c.streak++; c.bestStreak = Math.max(c.bestStreak, c.streak); for (const t of d.types || []) c.typeWins[t] = (c.typeWins[t] || 0) + 1; } else c.streak = 0; }
  else if (ev === 'sell') c.sold += d.n || 1;
  else if (ev === 'buy') c.bought++;
  else if (ev === 'glyph') { if (!s.world.found[d.id]) { s.world.found[d.id] = Date.now(); c.glyphs++; } }
  else if (ev === 'echo') c.echoes++;
  else if (ev === 'talk') { s.story.seen['talk:' + d.id] = Date.now(); c.talks++; }
  else if (ev === 'explore') s.story.seen['area:' + d.area] = Date.now();
  else if (ev === 'flag') s.story.seen[d.id] = Date.now();
  C.save(); listeners.forEach(fn => fn(ev, d));
}

/* ================================================================== Journey: chapters */
const ownedTypeCount = types => Object.keys(C.S.owned).reduce((n, i) => { const c = DB.cards[+i]; return n + (c && types.includes(c.t) ? 1 : 0); }, 0);
const ownedRare = r => Object.keys(C.S.owned).reduce((n, i) => n + (DB.cards[+i]?.r >= r ? 1 : 0), 0);
const bestSetPct = () => DB.sets.reduce((m, st) => { const p = C.setProgress(st.code); return p.total ? Math.max(m, p.have / p.total) : m; }, 0);
const seen = k => C.S.story.seen[k] ? 1 : 0;
const glyphsIn = area => Object.keys(C.S.world?.found || {}).filter(k => k.startsWith(area + ':')).length;
const beaten = n => C.S.battle.beaten[n] ? 1 : 0;
const O = (id, text, need, cur, go) => ({ id, text, need, cur: () => Math.min(need, cur()), go });

export const CHAPTERS = [
  { n: 1, title: 'Static in the Harbor', area: 'harbor', color: '#3d8fd6',
    intro: [['vale', 'Welcome to Veyra, Ranger. Pokébox Labs makes Lattice cards — every card holds an Echo: the data a Pokémon leaves behind in a storage relay.'],
      ['vale', 'Echoes are harmless. They are copies, not Pokémon. But lately cards in the harbor shops have started to… flicker. On their own.'],
      ['rho', 'Flicker is a nice word. One of them hissed at me. I\'m Rho — I fix the relay pylons. Welcome to the weirdest job in the region.']],
    goals: [O('c1a', 'Open 3 packs (Shop)', 3, () => C.S.cnt.packs, '#shop'), O('c1b', 'Talk to Dr. Vale in Lumen Harbor (World)', 1, () => seen('talk:vale'), '#world'),
      O('c1c', 'Beat Youngster Joey (Battle)', 1, () => beaten(0), '#battle')],
    outro: [['vale', 'Good work. Mistvale has been reporting Water Echoes that appear with no pack ever opened. I want you out there.'], ['rho', 'I\'ll drive. Bring boots. The fog up there eats sound.']],
    reward: { coins: 400, xp: 120, unlock: 'mistvale' } },
  { n: 2, title: 'What the Fog Keeps', area: 'mistvale', color: '#57c28f',
    intro: [['rho', 'See the waterwheel? Those marks weren\'t carved by anyone in this century. They look like Unown script.'], ['rho', 'And the Echoes out here only come in two flavours: Water and Grass. Like they\'re soaking up the place.']],
    goals: [O('c2a', 'Own 10 Water or Grass cards', 10, () => ownedTypeCount(['Water', 'Grass']), '#shop'), O('c2b', 'Find 2 glyph stones in Mistvale (World)', 2, () => glyphsIn('mistvale'), '#world'),
      O('c2c', 'Beat Lass Mira (Battle)', 1, () => beaten(1), '#battle')],
    outro: [['vale', 'The relay\'s cooling water runs straight under Mistvale. Echoes gather where it flows. So they are not random — they follow the machine.'], ['rho', '…and the machine is old. Older than the Lab.']],
    reward: { coins: 600, xp: 200, unlock: 'sandreach' } },
  { n: 3, title: 'Glass Under Sand', area: 'sandreach', color: '#e8903c',
    intro: [['rho', 'Sandreach. The vents under the dunes run so hot they turn sand to glass. Look — that shape in the glass. That\'s a Charmander.'], ['vale', 'That is not possible. Glass does not remember.']],
    goals: [O('c3a', 'Reach 25% on any binder set', 25, () => Math.floor(bestSetPct() * 100), '#binder'), O('c3b', 'Win 2 battles with a Fighting or Fire card', 2, () => (C.S.cnt.typeWins.Fighting || 0) + (C.S.cnt.typeWins.Fire || 0), '#battle'),
      O('c3c', 'Find 3 glass silhouettes (World)', 3, () => glyphsIn('sandreach'), '#world')],
    outro: [['vale', 'I checked the transfer logs. Every silhouette matches a Pokémon routed through Relay Node 7… thirty years ago.'], ['sable', 'Then perhaps your "copies" are memories, Doctor. And you have been selling them in foil.']],
    reward: { coins: 800, xp: 300, unlock: 'starfall' } },
  { n: 4, title: 'Signal at Starfall', area: 'starfall', color: '#8e9aa6', choice: true,
    intro: [['sable', 'I am Sable, of the Archivists. Our observatory records the relay\'s bursts. Tonight they spelled a word.'], ['sable', 'READ. Or perhaps: REMEMBER. The script is older than your Lab, Ranger. Help me read it.'], ['vale', 'Or help me shield the relay before something reads *us*. Your choice, Ranger.']],
    goals: [O('c4a', 'Beat Hiker Dom (Battle)', 1, () => beaten(2), '#battle'), O('c4b', 'Open a Starfall Collection or Moonlight pack', 1, () => (C.S.cnt.vaultBy['PX-SLEEVE-SF'] || 0) + (C.S.cnt.vaultBy['PX-MOON'] || 0), '#pack/PX-SLEEVE-SF'),
      O('c4c', 'Choose a side (Journey)', 1, () => (C.S.story.choice ? 1 : 0))],
    outro: [['rho', 'Whatever you picked… the signal just moved. Voltspire. Every Lightning Echo in Veyra woke up at once.']],
    reward: { coins: 1000, xp: 400, unlock: 'voltspire' } },
  { n: 5, title: 'Voltspire Blackout', area: 'voltspire', color: '#f2c230',
    intro: [['kai', 'Voltspire feeds the relay. When the storm spikes, the Echoes spike. Right now they\'re spiking so hard my cards are sparking in my pocket.']],
    goals: [O('c5a', 'Open a Thunder Surge pack', 1, () => C.S.cnt.vaultBy['PX-THUNDER'] || 0, '#pack/PX-THUNDER'), O('c5b', 'Win 3 battles in a row', 3, () => C.S.cnt.bestStreak, '#battle'),
      O('c5c', 'Stabilise 3 relay pylons (World)', 3, () => glyphsIn('voltspire'), '#world')],
    outro: [['vale', 'The pylons are holding. But the relay is venting its heat into Frostline — and inside the ice the Echoes are *combining*.']],
    reward: { coins: 1200, xp: 500, unlock: 'frostline' } },
  { n: 6, title: 'Frostline', area: 'frostline', color: '#9fd8f0',
    intro: [['rho', 'Two Echoes fused into one shape down there. Half Lapras, half something that isn\'t in any Pokédex. It just… watched me.']],
    goals: [O('c6a', 'Reach trainer level 15', 15, () => C.levelInfo().lv, '#shop'), O('c6b', 'Own 3 Ultra Rare or better cards', 3, () => ownedRare(4), '#shop'),
      O('c6c', 'Beat Elite Orin (Battle)', 1, () => beaten(6), '#battle')],
    outro: [['sable', 'All of it leads down. Under Node 7. Whatever the Echoes are becoming, it is waiting in the Rift.']],
    reward: { coins: 1500, xp: 700, unlock: 'rift' } },
  { n: 7, title: 'The Obsidian Rift', area: 'rift', color: '#5cf2d6',
    intro: [['glyph', '…R-E-M-E-M-B-E-R…'], ['vale', 'It is made of millions of Echoes. It is not attacking. It is copying — your cards, Ranger. It wants to see what you are.']],
    goals: [O('c7a', 'Open an Ascension pack', 1, () => C.S.cnt.vaultBy['PX-ASCEND'] || 0, '#pack/PX-ASCEND'), O('c7b', 'Beat Champion Lyra (Battle)', 1, () => beaten(7), '#battle'),
      O('c7c', 'Face GLYPH in the Rift (World)', 1, () => seen('glyph-duel'), '#world')],
    outro: [['glyph', '…YOU REMEMBER THEM. SO WE STAY.'], ['vale', 'Glyph will guard the relay now. And from today, any card can be returned — its Echo goes home.'], ['rho', 'So the sell button is canon now. Cool. Cool cool cool.']],
    reward: { coins: 3000, xp: 1500, unlock: 'epilogue' } },
];
export function chapter() { const s = ensure(); return CHAPTERS[Math.min(s.story.ch, CHAPTERS.length - 1)]; }
export const storyDone = () => ensure().story.ch >= CHAPTERS.length;
export function chapterReady(ch = chapter()) { return ch.goals.every(g => g.cur() >= g.need); }
export function completeChapter() {
  const s = ensure(), ch = chapter(); if (storyDone() || !chapterReady(ch)) return null;
  s.story.done[ch.n] = Date.now(); s.story.ch++; if (ch.reward.unlock) s.story.areas[ch.reward.unlock] = true;
  C.addCoins(ch.reward.coins); C.save(true); return ch;
}

/* ================================================================== challenges */
const DAILY = [
  { id: 'd-packs', text: 'Open 3 packs', k: 'packs', n: 3, st: 1, coins: 120 },
  { id: 'd-cards', text: 'Collect 20 cards', k: 'cards', n: 20, st: 1, coins: 100 },
  { id: 'd-win', text: 'Win 2 battles', k: 'wins', n: 2, st: 1, coins: 150 },
  { id: 'd-rare', text: 'Pull an Ultra Rare or better', k: 'rares', n: 1, st: 2, coins: 200 },
  { id: 'd-sell', text: 'Return (sell) 5 cards', k: 'sold', n: 5, st: 1, coins: 80 },
  { id: 'd-buy', text: 'Buy a card on the Market', k: 'bought', n: 1, st: 1, coins: 80 },
  { id: 'd-vault', text: 'Open a Vault pack', k: 'vault', n: 1, st: 2, coins: 150 },
  { id: 'd-glyph', text: 'Find a glyph stone in the World', k: 'glyphs', n: 1, st: 1, coins: 120 },
  { id: 'd-echo', text: 'Defeat 2 wild Echoes in the World', k: 'echoes', n: 2, st: 1, coins: 140 },
];
const WEEKLY = [
  { id: 'w-packs', text: 'Open 20 packs', k: 'packs', n: 20, st: 4, coins: 700 },
  { id: 'w-win', text: 'Win 10 battles', k: 'wins', n: 10, st: 4, coins: 800 },
  { id: 'w-rare', text: 'Pull 5 Ultra Rare or better', k: 'rares', n: 5, st: 5, coins: 900 },
  { id: 'w-vault', text: 'Open 4 Vault packs', k: 'vault', n: 4, st: 4, coins: 600 },
  { id: 'w-echo', text: 'Defeat 10 wild Echoes', k: 'echoes', n: 10, st: 4, coins: 700 },
  { id: 'w-cards', text: 'Collect 150 cards', k: 'cards', n: 150, st: 3, coins: 500 },
];
const weekNum = () => Math.floor((C.dayNum() + 3) / 7);
function pick(list, n, seed) { const R = C.rng(seed * 2654435761 >>> 0), a = list.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(R() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a.slice(0, n); }
function rollover() {
  const s = ensure(), d = C.dayNum(), w = weekNum();
  if (s.chal.day !== d) { s.chal.day = d; s.chal.base = { ...s.cnt }; for (const k in s.chal.claimed) if (k.startsWith('d:')) delete s.chal.claimed[k]; C.save(); }
  if (s.chal.week !== w) { s.chal.week = w; s.chal.wbase = { ...s.cnt }; for (const k in s.chal.claimed) if (k.startsWith('w:')) delete s.chal.claimed[k]; C.save(); }
}
export function challenges() {
  rollover(); const s = ensure();
  const mk = (c, kind) => { const base = (kind === 'd' ? s.chal.base : s.chal.wbase)[c.k] || 0, cur = Math.min(c.n, (s.cnt[c.k] || 0) - base);
    return { ...c, kind, key: kind + ':' + c.id, cur: Math.max(0, cur), done: cur >= c.n, claimed: !!s.chal.claimed[kind + ':' + c.id] }; };
  return { daily: pick(DAILY, 3, C.dayNum()).map(c => mk(c, 'd')), weekly: pick(WEEKLY, 3, weekNum() + 999).map(c => mk(c, 'w')) };
}
export function claimChallenge(key) {
  const s = ensure(), all = challenges(), c = [...all.daily, ...all.weekly].find(x => x.key === key);
  if (!c || !c.done || c.claimed) return null;
  s.chal.claimed[key] = Date.now(); s.stars += c.st; C.addCoins(c.coins); C.save(true); return c;
}
export function readyCount() {
  const a = challenges(); let n = [...a.daily, ...a.weekly].filter(c => c.done && !c.claimed).length;
  if (!storyDone() && chapterReady()) n++; return n;
}
export const STAR_TRACK = ITEMS.filter(i => i.u.t === 'stars').sort((a, b) => a.u.n - b.u.n);
