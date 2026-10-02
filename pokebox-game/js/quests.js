// Pokebox — the main story of Veyra as data + a small quest engine.
// 10 chapters (prologue + 8 Circuit Trials + the Rift). Every step says WHERE to go (the world shows a beacon,
// the HUD compass and the minimap point there), and the land itself is gated so you follow the routes in order.
// Design notes: claude/pokebox-story-bible.md (v2).
import * as C from './core.js';
import * as P from './progress.js';
import { REGIONS, ROUTES, routePoint, K } from './terrain.js';

/* ------------------------------------------------------------------ cast (joins the existing P.CAST used by story scenes) */
export const CAST2 = {
  maren: { name: 'Captain Maren', role: 'Circuit Warden · Tide Trial', look: { body: 'f', skin: 'sk3', hair: 'ponytail', hairColor: 'hc0', eyes: 'sharp', hat: 'wide', top: 'jacket', topColor: 'tc3', acc: 'none' } },
  mira: { name: 'Lass Mira', role: 'Circuit Warden · Bloom Trial', look: { body: 'f', skin: 'sk0', hair: 'ponytail', hairColor: 'hc7', eyes: 'happy', hat: 'none', top: 'tee', topColor: 'tc4', acc: 'none' } },
  orin: { name: 'Elite Orin', role: 'Circuit Warden · Rime Trial', look: { body: 'm', skin: 'sk1', hair: 'short', hairColor: 'hc4', eyes: 'sharp', hat: 'beanie', top: 'scarf', topColor: 'tc8', acc: 'none' } },
  vera: { name: 'Warden Vera', role: 'Circuit Warden · Surge Trial', look: { body: 'f', skin: 'sk3', hair: 'long', hairColor: 'hc3', eyes: 'sharp', hat: 'none', top: 'bomber', topColor: 'tc1', acc: 'earring' } },
  dom: { name: 'Hiker Dom', role: 'Circuit Warden · Glass Trial', look: { body: 'm', skin: 'sk4', hair: 'buzz', hairColor: 'hc0', eyes: 'round', hat: 'wide', top: 'ranger', topColor: 'tc5', acc: 'bandaid' } },
  lyra: { name: 'Champion Lyra', role: 'Circuit Champion', look: { body: 'f', skin: 'sk2', hair: 'braids', hairColor: 'hc9', eyes: 'sharp', hat: 'crown', top: 'jacket', topColor: 'tc6', acc: 'earring' } },
  clerk: { name: 'Card Shop Clerk', role: 'Lumen Card Shop', look: { body: 'f', skin: 'sk3', hair: 'bob', hairColor: 'hc2', eyes: 'happy', hat: 'cap', top: 'tee', topColor: 'tc6', acc: 'none' } },
  kest: { name: 'Director Kest', role: 'Static Syndicate', look: { body: 'm', skin: 'sk1', hair: 'short', hairColor: 'hc9', eyes: 'sharp', hat: 'none', top: 'jacket', topColor: 'tc0', acc: 'glasses' } },
  vex: { name: 'Admin Vex', role: 'Static Syndicate', look: { body: 'f', skin: 'sk2', hair: 'bob', hairColor: 'hc8', eyes: 'sharp', hat: 'beanie', top: 'bomber', topColor: 'tc0', acc: 'mask' } },
  grunt: { name: 'Syndicate Grunt', role: 'Static Syndicate', look: { body: 'm', skin: 'sk2', hair: 'buzz', hairColor: 'hc0', eyes: 'round', hat: 'beanie', top: 'hoodie', topColor: 'tc0', acc: 'mask' } },
  grunt2: { name: 'Syndicate Grunt', role: 'Static Syndicate', look: { body: 'f', skin: 'sk4', hair: 'bob', hairColor: 'hc0', eyes: 'sharp', hat: 'beanie', top: 'hoodie', topColor: 'tc0', acc: 'mask' } },
  deckA: { name: 'Dockhand Pim', role: 'Tide Trial', look: { body: 'm', skin: 'sk3', hair: 'short', hairColor: 'hc2', eyes: 'round', hat: 'cap', top: 'crew', topColor: 'tc3', acc: 'none' } },
  deckB: { name: 'Dockhand Sol', role: 'Tide Trial', look: { body: 'f', skin: 'sk1', hair: 'ponytail', hairColor: 'hc3', eyes: 'happy', hat: 'cap', top: 'crew', topColor: 'tc3', acc: 'none' } },
  ranger: { name: 'Ranger Tomas', role: 'Mistvale Rangers', look: { body: 'm', skin: 'sk4', hair: 'short', hairColor: 'hc1', eyes: 'round', hat: 'wide', top: 'ranger', topColor: 'tc5', acc: 'none' } },
  archivist: { name: 'Archivist Nell', role: 'The Archivists', look: { body: 'f', skin: 'sk2', hair: 'long', hairColor: 'hc4', eyes: 'sharp', hat: 'none', top: 'robe', topColor: 'tc9', acc: 'glasses' } },
};
Object.assign(P.CAST, CAST2);

/* ------------------------------------------------------------------ helpers for positions */
const at = (region, x, z) => ({ x: REGIONS[region].x + x, z: REGIONS[region].z + z, region });
const onRoute = (id, k, side = 0) => { const r = ROUTES.find(q => q.id === id), p = routePoint(r, k); return { x: p.x - p.dz * side, z: p.z + p.dx * side, route: id }; };
export const T = (types, r = [0, 2], n = 2, lvl = 1) => ({ types, r, n, lvl }); // trainer team spec

/* ------------------------------------------------------------------ story NPCs: where they stand and in which chapters */
// from/to = chapter indexes (inclusive) in which the NPC is present
export const ROSTER = [
  { id: 'vale', pos: at('harbor', -10, -6.2), face: 0, from: 0, to: 7 },
  { id: 'clerk', pos: at('harbor', 9.6, -8), face: 0, from: 0, to: 99, shop: true },
  { id: 'rho', pos: at('harbor', 3, 22), face: 3.1, from: 0, to: 0, trainer: T(['Colorless', 'Water'], [0, 1], 1, .8) },
  { id: 'joey', pos: at('harbor', 7, 9), face: 2.4, from: 0, to: 99, trainer: T(['Colorless'], [0, 1], 2, .85) },
  { id: 'deckA', pos: at('harbor', 21, 28), face: 1.6, from: 1, to: 99, trainer: T(['Water'], [0, 1], 2, .88), dock: true },
  { id: 'deckB', pos: at('harbor', 21, 41), face: 1.6, from: 1, to: 99, trainer: T(['Water', 'Colorless'], [0, 1], 2, .9), dock: true },
  { id: 'maren', pos: at('harbor', 29.5, 36), face: -1.6, from: 1, to: 99, trainer: T(['Water'], [1, 2], 3, .95) },
  { id: 'grunt', pos: onRoute('r1', .45, 3), face: 0, from: 2, to: 2, trainer: T(['Darkness', 'Colorless'], [0, 2], 2, .95) },
  { id: 'rho', pos: at('mistvale', 6, 10), face: 2, from: 2, to: 2 },
  { id: 'grunt2', pos: at('mistvale', 10, 1.5), face: -1, from: 2, to: 2, trainer: T(['Darkness', 'Water'], [0, 2], 2, 1) },
  { id: 'mira', pos: at('mistvale', -10, 2), face: 1.2, from: 2, to: 99, trainer: T(['Grass'], [1, 3], 3, 1.02) },
  { id: 'ranger', pos: onRoute('r2', .35, 3), face: 0, from: 3, to: 99, trainer: T(['Grass', 'Water'], [1, 2], 2, 1.02) },
  { id: 'archivist', pos: at('starfall', 10, 14), face: 3.2, from: 3, to: 99 },
  { id: 'sable', pos: at('starfall', 4, -4), face: 3, from: 3, to: 99, trainer: T(['Psychic', 'Metal'], [2, 3], 3, 1.08) },
  { id: 'rho', pos: at('frostline', -10, 12), face: 1.4, from: 4, to: 4 },
  { id: 'vex', pos: at('frostline', 10, 10), face: -2, from: 4, to: 4, trainer: T(['Darkness', 'Water'], [2, 3], 3, 1.1) },
  { id: 'orin', pos: at('frostline', 2, -6), face: 0, from: 4, to: 99, trainer: T(['Water'], [2, 4], 3, 1.14) },
  { id: 'kai', pos: at('voltspire', -4, 6), face: .5, from: 5, to: 5 },
  { id: 'vera', pos: at('voltspire', 12, -12), face: -.6, from: 5, to: 99, trainer: T(['Lightning'], [2, 4], 3, 1.18) },
  { id: 'dom', pos: at('sandreach', -6, 4), face: .8, from: 6, to: 99, trainer: T(['Fighting'], [2, 4], 3, 1.22) },
  { id: 'vale', pos: at('sandreach', 10, 12), face: -2, from: 6, to: 7 },
  { id: 'kest', pos: at('sandreach', -18, -22), face: .6, from: 7, to: 7, trainer: T(['Darkness', 'Dragon', 'Fire'], [3, 5], 3, 1.28) },
  { id: 'kai', pos: at('sandreach', 14, -14), face: -.8, from: 7, to: 99, trainer: T(['Fire'], [3, 5], 3, 1.26) },
  { id: 'vale', pos: at('harbor', -10, -6.2), face: 0, from: 8, to: 99 },
  { id: 'lyra', pos: onRoute('cw', .1, 0), face: 3.14, from: 8, to: 99, trainer: T(['Dragon', 'Psychic', 'Fire'], [4, 6], 3, 1.34) },
  { id: 'glyph', pos: at('rift', 0, -8), face: 0, from: 9, to: 99, mirror: true },
];
/* optional route trainers (Pokémon style: they spot you and walk up) */
const RT = (id, name, route, k, side, types, r, n, lvl, line) => ({ id, name, pos: onRoute(route, k, side), types, trainer: T(types, r, n, lvl), line, route: true });
export const ROUTE_TRAINERS = [
  RT('rt1a', 'Bug Catcher Wes', 'r1', .25, 5, ['Grass'], [0, 1], 2, .88, 'My net has caught three Echoes today! Your turn!'),
  RT('rt1b', 'Lass Juno', 'r1', .68, -5, ['Colorless', 'Water'], [0, 1], 2, .9, 'Eyes met — that means a battle!'),
  RT('rt1c', 'Fisher Abe', 'r1', .86, 6, ['Water'], [0, 2], 2, .92, 'Nothing bites today. Maybe you will!'),
  RT('rt2a', 'Ranger Ila', 'r2', .2, -5, ['Grass', 'Water'], [1, 2], 2, 1, 'The fog hides the strong ones. Show me yours.'),
  RT('rt2b', 'Hiker Bo', 'r2', .6, 5, ['Fighting', 'Metal'], [1, 2], 2, 1.02, 'Hup! Mountain legs, mountain cards!'),
  RT('rt2c', 'Mystic Rue', 'r2', .82, -5, ['Psychic'], [1, 3], 2, 1.04, 'The stars whispered your name. Badly.'),
  RT('rt3a', 'Skier Pia', 'r3', .3, 5, ['Water'], [1, 3], 2, 1.08, 'Too cold to stand still. Battle to warm up!'),
  RT('rt3b', 'Scientist Ode', 'r3', .7, -5, ['Metal', 'Psychic'], [2, 3], 3, 1.1, 'Your Echo signatures are fascinating. For science!'),
  RT('rt4a', 'Worker Hal', 'r4', .3, 5, ['Lightning', 'Metal'], [2, 3], 2, 1.14, 'Pylon crew. Break time means battle time.'),
  RT('rt4b', 'Ace Rana', 'r4', .7, -5, ['Lightning', 'Dragon'], [2, 4], 3, 1.16, 'Storm chaser. Let\'s see if you keep up.'),
  RT('rt5a', 'Glassblower Ty', 'r5', .3, 5, ['Fire'], [2, 4], 2, 1.2, 'Hot sand, hot cards!'),
  RT('rt5b', 'Brawler Kim', 'r5', .7, -5, ['Fighting'], [2, 4], 3, 1.22, 'No tricks. Just power.'),
  RT('rt6a', 'Sailor Jem', 'r6', .3, 5, ['Water', 'Fighting'], [3, 4], 3, 1.26, 'The ferry\'s back! Celebrate with a battle!'),
  RT('rt6b', 'Veteran Ash', 'r6', .7, -5, ['Dragon', 'Fire'], [3, 5], 3, 1.3, 'I\'ve seen eight Trials. Let\'s see yours.'),
];

/* ------------------------------------------------------------------ the story */
// step kinds: scene (auto), goto {pos,r}, talk {npc}, battle {npc}, capture {n,type?}, find {ids}, starter
const S = (text, o) => ({ text, ...o });
export const STORY = [
  { title: 'A Licence to Remember', region: 'harbor', color: '#3d8fd6',
    steps: [
      S('Arrive in Lumen Harbor', { kind: 'scene', lines: [['rho', 'Hey! You must be the new Lattice Ranger. I\'m Rho — relay courier, tour guide, part-time panic.'], ['rho', 'Dr. Vale is waiting at Pokébox Labs. Big building, satellite dish, can\'t miss it. Follow the beacon!']] }),
      S('Meet Dr. Vale at Pokébox Labs', { kind: 'talk', npc: 'vale', lines: [['vale', 'Welcome to Veyra, Ranger. Every Lattice card holds an Echo — the trace a Pokémon leaves in a storage relay.'], ['vale', 'Lately the Echoes have started walking out of their cards. They hold the shape of the Pokémon printed on them.'], ['vale', 'You will need a partner. Choose one of these three cards — its Echo will walk with you.']] }),
      S('Choose your partner card', { kind: 'starter' }),
      S('Catch your first wild Echo in the tall grass north of town', { kind: 'capture', n: 1, pos: onRoute('r1', .17, 0), r: 40, lines: [['vale', 'Wild Echoes gather in tall grass. Weaken one in battle, then press CAPTURE to bind it to a blank Lattice card.']] }),
      S('Rho wants a battle — meet him at the north gate', { kind: 'battle', npc: 'rho', lines: [['rho', 'You caught one already? Okay, okay. Let\'s see if it can take a hit. Rival battle!']] }),
    ],
    outro: [['rho', 'Not bad, Ranger. Not bad at all.'], ['vale', 'The Circuit Wardens certify every Ranger. Eight Trials, eight seals. The first Warden is right here: Captain Maren, on the docks.']],
    reward: { coins: 300, xp: 150, flag: 'gate-r1' } },

  { title: 'The Tide Trial', region: 'harbor', color: '#3fa7ff',
    steps: [
      S('Find Captain Maren on the docks', { kind: 'talk', npc: 'maren', lines: [['maren', 'A new Ranger! My Trial is simple: beat my two dockhands, then show me you can catch a Water Echo. Then you face me.']] }),
      S('Beat Dockhand Pim', { kind: 'battle', npc: 'deckA' }),
      S('Beat Dockhand Sol', { kind: 'battle', npc: 'deckB' }),
      S('Catch a Water Echo on the west beach', { kind: 'capture', n: 1, type: 'Water', pos: at('harbor', -90, 20), r: 50, lines: [['maren', 'Water Echoes wash up on the beach west of town. Weaken one, then CAPTURE it.']] }),
      S('Tide Trial: battle Captain Maren', { kind: 'battle', npc: 'maren', lines: [['maren', 'The sea keeps nothing still. Neither will I!']] }),
    ],
    outro: [['maren', 'The Tide Seal is yours. Take Route 1 west to Mistvale — the fog there has been acting strange.'], ['vale', 'Strange how?'], ['maren', 'It follows people.']],
    reward: { coins: 500, xp: 250, seal: 'Tide Seal' } },

  { title: 'What the Fog Keeps', region: 'mistvale', color: '#57c28f',
    steps: [
      S('Travel west along Route 1', { kind: 'goto', pos: onRoute('r1', .45, 0), r: 16 }),
      S('Someone in black is siphoning Echoes — stop the grunt', { kind: 'battle', npc: 'grunt', lines: [['grunt', 'Static Syndicate business. Every Echo we pump full of relay power prints a rare card. Scram!']] }),
      S('Reach Mistvale and find Rho at the waterwheel', { kind: 'talk', npc: 'rho', lines: [['rho', 'The Syndicate hooked a siphon into the waterwheel. They overcharge Echoes so the cards come out as "hits".'], ['rho', 'And look at these stones. Unown script, older than the relay. Record them — Dr. Vale needs to see this.']] }),
      S('Record 2 glyph stones in Mistvale', { kind: 'find', ids: ['mistvale:0', 'mistvale:1'] }),
      S('Unplug the siphon: beat the grunt at the waterwheel', { kind: 'battle', npc: 'grunt2' }),
      S('Bloom Trial: battle Lass Mira', { kind: 'battle', npc: 'mira', lines: [['mira', 'You cleared the siphon? Then the fog owes you one. And so do I — a battle!']] }),
    ],
    outro: [['mira', 'The Bloom Seal. The fog will let you pass north now — Route 2 climbs to Starfall.'], ['rho', 'Starfall. The observatory people. The Archivists. They think the Echoes are memories.']],
    reward: { coins: 700, xp: 350, seal: 'Bloom Seal', flag: 'gate-r2' } },

  { title: 'Signal at Starfall', region: 'starfall', color: '#8e9aa6',
    steps: [
      S('Climb Route 2 to the ranger checkpoint', { kind: 'battle', npc: 'ranger', lines: [['ranger', 'Checkpoint! Nobody reaches Starfall without proving they can handle the night Echoes.']] }),
      S('Enter Starfall — the Archivist at the edge of town knows the way', { kind: 'talk', npc: 'archivist', lines: [['archivist', 'You carry a Lattice licence. Warden Sable will want words. She is at the observatory, reading the signal.']] }),
      S('Record 2 glyph stones around Starfall', { kind: 'find', ids: ['starfall:0', 'starfall:1'] }),
      S('Catch a Psychic or Metal Echo under the Starfall sky', { kind: 'capture', n: 1, type: ['Psychic', 'Metal'], pos: at('starfall', -60, 20), r: 70 }),
      S('Meet Warden Sable at the observatory', { kind: 'talk', npc: 'sable', lines: [['sable', 'Tonight the relay spelled a word in Unown: REMEMBER. The Echoes are not copies, Ranger. They are memories of Pokémon that passed through Node 7.'], ['sable', 'The Syndicate burns those memories for foil. Your Lab sells them. Show me what you are before I decide which side you stand on.']] }),
      S('Night Trial: battle Warden Sable', { kind: 'battle', npc: 'sable' }),
    ],
    outro: [['sable', 'The Night Seal. The pass to Frostline is open. Something in the ice is combining Echoes — two memories, one shape.']],
    reward: { coins: 900, xp: 450, seal: 'Night Seal', flag: 'gate-r3' } },

  { title: 'Rime and Memory', region: 'frostline', color: '#9fd8f0',
    steps: [
      S('Cross Signal Pass to Frostline', { kind: 'goto', pos: at('frostline', 0, 30), r: 20 }),
      S('Find Rho near the ice caverns', { kind: 'talk', npc: 'rho', lines: [['rho', 'Two Echoes fused down there. Half Lapras, half something no Pokédex knows. And a Syndicate admin is herding them.']] }),
      S('Stop Admin Vex', { kind: 'battle', npc: 'vex', lines: [['vex', 'Fused Echoes print cards worth a fortune. You are bad for business, Ranger.']] }),
      S('Record 2 glyph stones in the snow', { kind: 'find', ids: ['frostline:0', 'frostline:1'] }),
      S('Rime Trial: battle Elite Orin', { kind: 'battle', npc: 'orin', lines: [['orin', 'The ice keeps what the relay throws away. So do I. Show me what you keep.']] }),
    ],
    outro: [['orin', 'The Rime Seal — and the thaw-key. The Stormrise Road east to Voltspire is yours.']],
    reward: { coins: 1100, xp: 550, seal: 'Rime Seal', flag: 'gate-r4' } },

  { title: 'Voltspire Blackout', region: 'voltspire', color: '#f2c230',
    steps: [
      S('Follow the Stormrise Road to Voltspire', { kind: 'goto', pos: at('voltspire', 0, 30), r: 20 }),
      S('Talk to Kai at the relay tower', { kind: 'talk', npc: 'kai', lines: [['kai', 'Every pylon on the plateau is overloading. The Syndicate is draining the storm into their siphons. Stabilise the pylons — three of them!']] }),
      S('Stabilise 3 relay pylons', { kind: 'find', ids: ['voltspire:0', 'voltspire:1', 'voltspire:2'] }),
      S('Catch a Lightning Echo', { kind: 'capture', n: 1, type: 'Lightning', pos: at('voltspire', 50, 30), r: 70 }),
      S('Surge Trial: battle Warden Vera', { kind: 'battle', npc: 'vera', lines: [['vera', 'You stood in my storm and kept your cards dry. Now hold a real charge!']] }),
    ],
    outro: [['vera', 'The Surge Seal. The Syndicate trucks went south, to the Sandreach vents. Glassburn Steps will take you there.']],
    reward: { coins: 1300, xp: 650, seal: 'Surge Seal', flag: 'gate-r5' } },

  { title: 'Glass Under Sand', region: 'sandreach', color: '#e8903c',
    steps: [
      S('Descend the Glassburn Steps to Sandreach', { kind: 'goto', pos: at('sandreach', 0, -30), r: 22 }),
      S('Meet Dr. Vale at the dig site', { kind: 'talk', npc: 'vale', lines: [['vale', 'The dunes fused into glass in the shape of Pokémon. Every silhouette matches a transfer through Node 7… thirty years ago.'], ['vale', 'Sable was right. They are memories. I have been printing memories.']] }),
      S('Record 3 glass silhouettes', { kind: 'find', ids: ['sandreach:0', 'sandreach:1', 'sandreach:2'] }),
      S('Glass Trial: battle Hiker Dom', { kind: 'battle', npc: 'dom', lines: [['dom', 'Sand remembers heat, kid. Let\'s see what your deck remembers.']] }),
    ],
    outro: [['dom', 'The Glass Seal. The Syndicate dug into the vents west of town. Their Director is down there.']],
    reward: { coins: 1500, xp: 750, seal: 'Glass Seal' } },

  { title: 'The Syndicate Vents', region: 'sandreach', color: '#ff6a3d',
    steps: [
      S('Confront Director Kest at the vents', { kind: 'battle', npc: 'kest', lines: [['kest', 'Memories? Echoes are ore, Ranger. The relay is a mine. I am simply the only one honest enough to dig.']] }),
      S('Ember Trial: battle Kai at the vent rim', { kind: 'battle', npc: 'kai', lines: [['kai', 'You shut down the Syndicate. Now finish your seventh Trial — fire against fire!']] }),
    ],
    outro: [['kai', 'The Ember Seal. The old ferry bridge on Route 6 is rebuilt — go home to Lumen Harbor.'], ['vale', 'Come to the Lab. There is a choice I cannot make alone.']],
    reward: { coins: 1800, xp: 900, seal: 'Ember Seal', flag: 'gate-r6' } },

  { title: 'Champion\'s Causeway', region: 'harbor', color: '#c46bff',
    steps: [
      S('Take Route 6 home and talk to Dr. Vale', { kind: 'talk', npc: 'vale', lines: [['vale', 'Node 7 is waking up. The Echoes are merging into one mind under the relay — Sable calls it GLYPH.'], ['vale', 'The Archivists want it left alone. I want it shielded. Whoever reaches it first decides. That will be you, Ranger.'], ['vale', 'Only a Champion may cross the causeway. Lyra waits at Frostline.']] }),
      S('Go to the Relay Causeway at Frostline', { kind: 'goto', pos: onRoute('cw', .06, 0), r: 16 }),
      S('Champion Trial: battle Champion Lyra', { kind: 'battle', npc: 'lyra', lines: [['lyra', 'Seven seals. Everyone who reaches Node 7 gets one match with me. Make it count.']] }),
    ],
    outro: [['lyra', 'The Crown Seal. The causeway is yours. Whatever waits in the Rift… it has been waiting for someone like you.']],
    reward: { coins: 2500, xp: 1200, seal: 'Crown Seal', flag: 'gate-cw' } },

  { title: 'The Obsidian Rift', region: 'rift', color: '#5cf2d6',
    steps: [
      S('Cross the causeway to the Obsidian Rift', { kind: 'goto', pos: at('rift', 0, 30), r: 22 }),
      S('Face GLYPH under Relay Node 7', { kind: 'battle', npc: 'glyph', lines: [['glyph', '…S H O W …'], ['glyph', '…W H A T  Y O U  R E M E M B E R …']] }),
    ],
    outro: [['glyph', '…YOU REMEMBER THEM. SO WE STAY.'], ['vale', 'GLYPH will guard the relay now. And from today, any card can be returned — its Echo goes home.'], ['rho', 'So the sell button is canon now. Cool. Cool cool cool.']],
    reward: { coins: 5000, xp: 2500, seal: 'Echo Seal', flag: 'story-done' } },
];

/* ------------------------------------------------------------------ engine */
export function Q() {
  const s = P.ensure();
  s.q ||= { ch: 0, step: 0, flags: {}, beaten: {}, caught: 0, stepCaught: 0, seals: [], starter: null, visited: { harbor: 1 } };
  s.q.flags ||= {}; s.q.beaten ||= {}; s.q.seals ||= []; s.q.visited ||= { harbor: 1 };
  return s.q;
}
export const chapterNow = () => STORY[Math.min(Q().ch, STORY.length - 1)];
export const done = () => Q().ch >= STORY.length;
export function stepNow() { const q = Q(); if (done()) return null; return STORY[q.ch].steps[q.step] || null; }
export const flag = f => !!Q().flags[f];
const listeners = new Set();
export const onQuest = fn => (listeners.add(fn), () => listeners.delete(fn));
const emit = (type, d) => listeners.forEach(fn => fn(type, d));

/** where the current objective is (world coords) — used by the beacon, compass and minimap */
export function target() {
  const st = stepNow(); if (!st) return null;
  if (st.pos) return { ...st.pos, label: st.text };
  if (st.npc) { const n = npcNow(st.npc); if (n) return { x: n.pos.x, z: n.pos.z, label: st.text }; }
  if (st.kind === 'find') { const left = st.ids.filter(id => !P.ensure().world.found[id]); if (left.length) return { findIds: left, label: st.text }; }
  if (st.kind === 'starter' || st.kind === 'talk') { const n = npcNow('vale'); if (n) return { x: n.pos.x, z: n.pos.z, label: st.text }; }
  return null;
}
/** the NPC entry (ROSTER) for an id in the current chapter */
export function npcNow(id) { const ch = Q().ch; return ROSTER.find(r => r.id === id && ch >= r.from && ch <= r.to) || null; }
export function rosterNow() { const ch = Q().ch; const seen = new Set(); return ROSTER.filter(r => ch >= r.from && ch <= r.to && !seen.has(r.id) && seen.add(r.id)); }

function advance() {
  const q = Q(), ch = STORY[q.ch]; q.step++; q.stepCaught = 0;
  if (q.step >= ch.steps.length) {
    const rw = ch.reward || {}; if (rw.flag) q.flags[rw.flag] = Date.now(); if (rw.seal && !q.seals.includes(rw.seal)) q.seals.push(rw.seal);
    if (rw.coins) C.addCoins(rw.coins); q.ch++; q.step = 0; C.save(true);
    emit('chapter', { ch, reward: rw });
  } else { C.save(true); emit('step', { step: stepNow() }); }
}
/** feed game events in; returns true if the story moved on */
export function event(type, d = {}) {
  const st = stepNow(); if (!st) return false; const q = Q();
  if (type === 'capture') { q.caught++; if (st.kind === 'capture' && (!st.type || [].concat(st.type).includes(d.card?.t))) { q.stepCaught++; if (q.stepCaught >= (st.n || 1)) { advance(); return true; } } C.save(); return false; }
  if (type === 'reach' && st.kind === 'goto' && Math.hypot(d.x - st.pos.x, d.z - st.pos.z) < (st.r || 12)) { advance(); return true; }
  if (type === 'talk' && st.kind === 'talk' && st.npc === d.id) { advance(); return true; }
  if (type === 'win' && st.kind === 'battle' && st.npc === d.id) { advance(); return true; }
  if (type === 'find' && st.kind === 'find' && st.ids.every(id => P.ensure().world.found[id])) { advance(); return true; }
  if (type === 'starter' && st.kind === 'starter') { q.starter = d.i; advance(); return true; }
  if (type === 'scene' && st.kind === 'scene') { advance(); return true; }
  return false;
}
/** lines an NPC says right now (story first, then idle chatter) */
export function npcLines(id) {
  const st = stepNow();
  if (st && st.npc === id && st.lines) return st.lines;
  const IDLE = {
    vale: [['vale', 'Every Echo in Veyra passes through Node 7 sooner or later. Keep going, Ranger.']],
    rho: [['rho', 'The Echoes are getting bolder. They follow the relay lines like fish follow warm water.']],
    clerk: [['clerk', 'Vault stock refreshes every night!']],
    joey: [['joey', 'My Rattata-tier cards are top percentage! Rematch any time.']],
    maren: [['maren', 'Tide goes out, tide comes in. Keep your deck wet, Ranger.']],
    mira: [['mira', 'The fog is calm now. Thank you.']], sable: [['sable', 'REMEMBER. That was the word. I have not stopped hearing it.']],
    orin: [['orin', 'Cold keeps things. Remember that.']], vera: [['vera', 'The storm hums differently since you came.']], dom: [['dom', 'Glass remembers. So should you.']],
    kai: [['kai', 'My cards are sparking in my pocket. Perfect battle weather.']], lyra: [['lyra', 'The causeway is quiet today.']],
    archivist: [['archivist', 'The script on the stones is older than the relay.']], ranger: [['ranger', 'Stay on the trail. The fog eats people who wander.']],
    glyph: [['glyph', '…W E  R E M E M B E R …']], kest: [['kest', 'Ore is ore.']], vex: [['vex', 'Business will recover.']],
    grunt: [['grunt', 'I am on a break. A long one.']], grunt2: [['grunt2', 'The siphon was not my idea!']], deckA: [['deckA', 'Maren trains us hard.']], deckB: [['deckB', 'Good battle!']],
  };
  return IDLE[id] || [];
}
export function markBeaten(id) { Q().beaten[id] = Date.now(); C.save(); }
export const beaten = id => !!Q().beaten[id];
/** starter choices: the first printing of the three classics we can find */
export function starterCards() {
  const pick = n => C.DB.cards.filter(c => c.n === n && c.r <= 1).sort((a, b) => a.r - b.r || a.i - b.i)[0] || C.DB.cards.find(c => c.n === n);
  return ['Bulbasaur', 'Charmander', 'Squirtle'].map(pick).filter(Boolean);
}
/**
 * How far along the ring you may walk. The ring is measured clockwise from Lumen Harbor (u = 0°) through
 * Mistvale (59°), Starfall (121°), Frostline (180°), Voltspire (239°), Sandreach (301°) and back (360°).
 */
export const ringU = (x, z) => ((-Math.atan2(x, z) * 180 / Math.PI) + 360) % 360;
export function ringLimit() {
  const f = Q().flags;
  return f['gate-r6'] ? 360 : f['gate-r5'] ? 314 : f['gate-r4'] ? 252 : f['gate-r3'] ? 193 : f['gate-r2'] ? 133 : f['gate-r1'] ? 72 : 14;
}
/** may the player stand here? Veyra is fully open — nothing blocks you; areas ahead of the story are only dangerous. */
export function blockedAt() { return null; }
/** the chapter in which the story reaches each part of the ring (u in degrees) — used for danger */
const TIER = [[0, 0], [30, 1], [59, 2], [121, 3], [180, 4], [239, 5], [301, 6], [340, 3], [360, 0]];
const RIFT_TIER = 8;
export function tierAt(x, z) {
  const r = Math.hypot(x, z); if (r < 300 * K) return RIFT_TIER - (r / (300 * K)) * 2; // the Rift and its causeway: endgame danger
  const u = ringU(x, z);
  for (let i = 1; i < TIER.length; i++) { const [u1, t1] = TIER[i], [u0, t0] = TIER[i - 1]; if (u <= u1) return t0 + (t1 - t0) * (u - u0) / (u1 - u0); }
  return 0;
}
/** 0 = matches your progress; 1+ = this area is ahead of the story (stronger wild Echoes) */
export const dangerAt = (x, z) => Math.max(0, Math.round(tierAt(x, z) - Q().ch));
