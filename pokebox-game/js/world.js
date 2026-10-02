// Pokebox — Veyra as ONE continuous open world (~1 km across), streamed around the player.
// Terrain comes from terrain.js (computed in a worker, 128 m chunks), towns are the hand-built area layouts placed on
// the ring, vegetation is scattered per chunk, grass and water read one island-wide height/grass texture.
// Story (quests.js) drives NPCs, gates and the objective beacon; battles happen right here in the world (fieldbattle.js).
import * as THREE from 'three';
import * as P from './progress.js';
import * as QS from './quests.js';
import * as C from './core.js';
import * as RK from './rank.js';
import { prepare, makeRigged, tickEchoMaterials, attachProp } from './chars.js';
import { loadKits, place, instances, house, has, hasToon, wind, bounds } from './world_kit.js';
import { createComicPost, applyComic, CU } from './comic.js';
import { makeCardPet } from './cardpet.js';
import { createFieldBattle } from './fieldbattle.js';
import { GFX, clamp, lerp, smooth, rng, fbm, col, makeSky, makeWater, grassField as grassFieldImpl, particles, makePost, envFromSky } from './world_env.js';
import { H, REGIONS, ROUTES, GATES, TOWN_PATHS, BIOMES, BIOME_LIST, regionWeights, nearestRegion, roadDist, routePoint, WORLD, segDist } from './terrain.js';

export const TYPE_COL = { Grass: '#5fae4f', Fire: '#ff6a3c', Water: '#3d9fff', Lightning: '#ffd23c', Psychic: '#d86bff', Fighting: '#d8844a', Darkness: '#8a6ae8', Metal: '#b8c6d4', Dragon: '#e0b040', Colorless: '#f0ece0' };
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

/* ------------------------------------------------------------------ people */
const npcLook = id => P.CAST[id]?.look;
const npcName = id => P.CAST[id]?.name || id;
const TOPS = ['tee', 'hoodie', 'jacket', 'ranger', 'summer', 'crew', 'scarf'], TC = ['tc0', 'tc1', 'tc2', 'tc3', 'tc4', 'tc5', 'tc6', 'tc7', 'tc8'], HC = ['hc0', 'hc1', 'hc2', 'hc3', 'hc4'];
function villagerLook(R, top) { return { body: R() < .5 ? 'm' : 'f', skin: 'sk' + (R() * 6 | 0), hairColor: HC[R() * HC.length | 0], hat: R() < .25 ? ['cap', 'beanie', 'wide', 'beret'][R() * 4 | 0] : 'none', top: top || TOPS[R() * TOPS.length | 0], topColor: TC[R() * TC.length | 0], acc: R() < .15 ? 'glasses' : 'none' }; }
/* people of Veyra: who they are decides their body (Blender models chars/anime/*), height, job and what they say */
const ARCH = {
  fisher:     { model: 'm_dock', h: 1.02, hat: ['cap', 'wide', 'none'], job: 'fish', names: ['Fisher Hal', 'Old Bram', 'Fisher Nico'], lines: ['Tide brings the Water Echoes in at dawn. Bring a strong card.', 'Thirty years on this dock and I never saw the sea glow like last week.'] },
  docker:     { model: 'm_dock', h: 1.06, hat: ['cap', 'beanie'], job: 'hammer', names: ['Dockhand Tor', 'Crewman Ivo'], lines: ['Crates of blank Lattice cards, every morning. Somebody is buying a lot of them.', 'Mind the planks, Ranger. I just nailed that one.'] },
  elder_m:    { model: 'm_elder', h: .94, hair: ['hc4', 'hc4', 'hc0'], acc: ['none', 'glasses'], job: 'chat', names: ['Grandpa Odo', 'Elder Fen', 'Mr. Pell'], lines: ['In my day the cards stayed in the binder. Now they walk around!', 'Sit down a minute, youngster. The Echoes are not going anywhere.'] },
  elder_f:    { model: 'f_elder', h: .9, hair: ['hc4', 'hc4', 'hc2'], acc: ['none', 'glasses'], job: 'chat', names: ['Granny Mae', 'Mrs. Ilsa', 'Aunt Rosa'], lines: ['My grandson wants to be a Ranger too. Keep an eye out for him, will you?', 'The Relay Center nurse makes the best tea in town.'] },
  merchant:   { model: 'm_heavy', h: .97, hat: ['none', 'cap'], job: 'sell', names: ['Trader Gus', 'Merchant Abe'], lines: ['Fresh berries! Sealed packs! Everything a Ranger needs!', 'For you, a special price. Well, the normal price, but with a smile.'] },
  merchant_f: { model: 'f_heavy', h: .95, job: 'sell', names: ['Trader Lina', 'Madame Oda'], lines: ['Glass from the dunes, polished by hand. Look how it catches the light!', 'Buy two, the third is still full price. I am not a charity.'] },
  scholar:    { model: 'm_scholar', h: 1.0, acc: ['glasses', 'none'], job: 'read', names: ['Archivist Rel', 'Researcher Amos'], lines: ['This glyph appears in every relay log since the first transfer. Fascinating.', 'Please keep your voice down. The signal is very faint tonight.'] },
  worker_f:   { model: 'f_worker', h: .98, hat: ['none', 'beanie'], job: 'sweep', names: ['Caretaker Jo', 'Sweeper Nell'], lines: ['Sand everywhere, every day. The wind never gives up and neither do I.', 'The plaza does not clean itself, Ranger.'] },
  gardener:   { model: 'f_elder', h: .9, hair: ['hc4', 'hc1'], hat: ['wide', 'none'], job: 'garden', names: ['Gardener Viv', 'Mrs. Holt'], lines: ['Grass Echoes love my flowerbeds. I let them stay, they keep the bugs away.', 'Water in the morning, never at noon. Remember that.'] },
  smith:      { model: 'm_athlete', h: 1.06, job: 'hammer', names: ['Smith Barro', 'Mechanic Volk'], lines: ['Pylon brackets, forty a day. My arms are made of steel by now.', 'If your gear breaks, bring it here. If your heart breaks, the bar is next door.'] },
  athlete:    { model: 'm_athlete', h: 1.06, walker: 1.7, names: ['Runner Kip', 'Ace Dario'], lines: ['Morning run around the whole town. Echoes cannot keep up with me!', 'Train every day and your partner trains with you.'] },
  athlete_f:  { model: 'f_athlete', h: 1.0, walker: 1.7, names: ['Runner Saya', 'Ace Mira-Lyn'], lines: ['Race you to the Relay Center! ...No? Fine.', 'My partner card and I run five kilometres every morning.'] },
  bearded:    { model: 'm_beard', h: 1.02, walker: 1.2, hat: ['none', 'beanie', 'cap'], names: ['Courier Ozan', 'Mr. Brann'], lines: ['Delivering cards all over Veyra. The roads are safer since the Rangers came.', 'Nice weather for a walk. For a battle too, I suppose.'] },
  kid_m:      { model: 'kid_m', h: .64, walker: 2.3, kid: true, hat: ['cap', 'none'], names: ['Timmy', 'Leo', 'Pip'], lines: ['When I grow up I will have ALL the cards. All of them!', 'Did you see that? A wild Echo! Over there! ...It ran away.'] },
  kid_f:      { model: 'kid_f', h: .6, walker: 2.3, kid: true, names: ['Lily', 'Mina', 'Rae'], lines: ['My big sister is a Ranger. She is way stronger than you.', 'Can I see your partner? Please please please?'] },
};
const JOBS = { // loop: Blender job animation; work/rest seconds give natural pauses; prop in the right hand
  fish: { prop: 'rod', loop: 'Job_Fish', work: [14, 30], rest: [3, 6] },
  hammer: { prop: 'hammer', loop: 'Job_Hammer', work: [5, 10], rest: [2, 5], speed: .9 },
  sweep: { prop: 'broom', loop: 'Job_Sweep', work: [6, 12], rest: [2, 4], speed: .9 },
  read: { prop: 'book', loop: 'Job_Read', work: [20, 40], rest: [3, 6] },
  sell: { loop: 'Job_Talk', work: [4, 8], rest: [4, 8], alt: 'Wave' },
  chat: { loop: 'Job_Talk', work: [5, 10], rest: [2, 5] },
  garden: { prop: 'can', loop: 'Job_Water', work: [6, 12], rest: [3, 6] },
};
function archLook(a, R) {
  const A = ARCH[a], pick = (arr, d) => arr ? arr[R() * arr.length | 0] : d;
  return { model: A.model, h: A.h * (.97 + R() * .06), body: /^f_|kid_f/.test(A.model) ? 'f' : 'm', skin: 'sk' + (R() * 6 | 0), hairColor: pick(A.hair, HC[R() * HC.length | 0]),
    hat: pick(A.hat, 'none'), top: 'tee', topColor: TC[R() * TC.length | 0], acc: pick(A.acc, 'none') };
}
const TOWN_FOLK = { // who walks around each town
  harbor: ['kid_m', 'kid_f', 'elder_m', 'bearded', 'athlete_f', 'kid_m'], mistvale: ['elder_f', 'kid_f', 'bearded', 'elder_m'], starfall: ['bearded', 'athlete', 'kid_m'],
  frostline: ['athlete', 'bearded', 'kid_f'], voltspire: ['athlete_f', 'bearded', 'kid_m'], sandreach: ['kid_m', 'kid_f', 'elder_m', 'bearded'],
};
const BLD_JOB = { MV_Cottage_A: 'gardener', MV_Cottage_B: 'elder_f', MV_Stilt: 'fisher', MV_Lookout: null, SF_Archive: 'scholar', SF_House: 'scholar', FL_Lodge: 'docker', FL_Chalet_A: 'worker_f', FL_Chalet_B: 'elder_m',
  VS_Station: 'smith', VS_Block_A: 'smith', VS_Block_B: 'scholar', VS_Block_C: 'worker_f', SR_Market_A: 'merchant', SR_Market_B: 'merchant_f', SR_Workshop: 'smith', SR_Adobe_A: 'worker_f', SR_Adobe_B: 'elder_m', SR_Adobe_C: 'gardener' };
const VILLAGER_LINES = [
  'The ferry from the mainland is late again. Something in the relay water, they say.', 'My deck sparked in my pocket this morning. Is that normal?',
  'Dr. Vale bought my whole catch of glass-sand. Who needs that much sand?', 'Have you seen the lights over Starfall? Beautiful. Creepy, but beautiful.',
  'Echoes love the tall grass. Walk slowly and they come to you.', 'Best pulls come at night, trust me. Moonlight packs never miss.',
  'I caught a little Pecklet last week. It follows me everywhere now.', 'Careful near the Rift. The air tastes like a battery.',
  'Follow the roads. The hills eat people who wander at night.', 'The Circuit Wardens are tough, but fair. Mostly.',
];

/* ------------------------------------------------------------------ regional looks (blended as you walk between regions) */
export const AREAS = {
  harbor: { name: 'Lumen Harbor', sub: 'Pokébox Labs HQ', echo: ['Water', 'Colorless', 'Grass'], spawn: [0, 17],
    sky: ['#2a78e0', '#bfe0fb'], fog: ['#b4d4f2', 120, 420], sunColor: '#fff3dc', clouds: .42, cloud: '#ffffff', exposure: 1.05, hemi: 1.35, sunI: 2.9, sat: 1.16, tint: [1.02, 1, .98], fx: ['pollen', { color: '#fff6c8', n: 220, size: 4 }] },
  mistvale: { name: 'Mistvale', sub: 'Wetlands', echo: ['Water', 'Grass', 'Psychic'], spawn: [0, 22],
    sky: ['#7fb0b4', '#e2efe8'], fog: ['#cadcd4', 45, 210], sunColor: '#f6f2e0', clouds: .75, cloud: '#eef2ee', exposure: 1.05, hemi: 1.45, sunI: 2.1, sat: 1.1, tint: [.98, 1.02, 1], fx: ['firefly', { color: '#d8ff8a', n: 140, size: 7, hmax: 5 }] },
  starfall: { name: 'Starfall', sub: 'Signal cliffs', echo: ['Metal', 'Psychic', 'Darkness'], spawn: [0, 24], night: true, aurora: true,
    sky: ['#101a4a', '#3a3a7a'], fog: ['#2a2c5c', 70, 260], sunColor: '#c4d0ff', clouds: .3, cloud: '#8a8ec0', exposure: 1.25, hemi: 1.5, sunI: 2, sat: 1.1, tint: [.97, .99, 1.06], bloom: .5, fx: ['mote', { color: '#c6b8ff', n: 200, size: 5 }] },
  frostline: { name: 'Frostline', sub: 'Glacier peaks', echo: ['Water', 'Metal', 'Colorless'], spawn: [0, 26], aurora: true,
    sky: ['#5d9be6', '#e6f2ff'], fog: ['#d6e6f8', 90, 320], sunColor: '#fff8ee', clouds: .5, cloud: '#ffffff', exposure: .98, hemi: 1.3, sunI: 2.6, sat: 1.04, tint: [.97, 1, 1.04], fx: ['snow', { color: '#ffffff', n: 520, size: 6, hmax: 16 }] },
  voltspire: { name: 'Voltspire', sub: 'Storm plateau', echo: ['Lightning', 'Metal', 'Fighting'], spawn: [0, 24], storm: true,
    sky: ['#4a5670', '#b8b6a4'], fog: ['#8c8a80', 60, 230], sunColor: '#f0eee0', clouds: .9, cloud: '#a8aab4', exposure: 1.05, hemi: 1.45, sunI: 2.1, sat: 1.02, tint: [.99, 1, 1.02], fx: ['spark', { color: '#fff2a0', n: 90, size: 5, hmax: 6 }] },
  sandreach: { name: 'Sandreach', sub: 'Glass dunes', echo: ['Fighting', 'Fire', 'Dragon'], spawn: [0, 26],
    sky: ['#e8913f', '#fde5bc'], fog: ['#f0d0a0', 110, 380], sunColor: '#ffdcae', clouds: .12, cloud: '#fff4e0', exposure: 1.02, hemi: 1.2, sunI: 3.1, sat: 1.14, tint: [1.04, 1, .94], fx: ['dust', { color: '#f6d9a8', n: 260, size: 5, hmax: 4 }] },
  rift: { name: 'The Obsidian Rift', sub: 'Beneath Relay Node 7', echo: ['Dragon', 'Fire', 'Darkness'], spawn: [0, 26], night: true,
    sky: ['#061418', '#1b4a44'], fog: ['#12302c', 40, 200], sunColor: '#8affe8', clouds: .5, cloud: '#2a5a54', exposure: 1.3, hemi: 1.5, sunI: 1.8, sat: 1.1, tint: [.96, 1.03, 1.02], bloom: .7, fx: ['mote', { color: '#5cf2d6', n: 280, size: 6 }] },
};
const WEATHER = {
  harbor: ['clear', 'clear', 'clear', 'cloudy', 'rain'], mistvale: ['fog', 'rain', 'cloudy', 'clear'], starfall: ['clear', 'clear', 'cloudy'],
  frostline: ['snow', 'clear', 'snow', 'fog'], voltspire: ['storm', 'rain', 'cloudy', 'storm'], sandreach: ['clear', 'clear', 'dust'], rift: ['clear', 'fog'],
};
const DEFAULT_SPAWN = { x: REGIONS.harbor.x + 16, z: REGIONS.harbor.z + 22 }; // the harbor pier

/* ------------------------------------------------------------------ small shared pieces */
let _cobble = null;
function cobbleTex() {
  if (_cobble) return _cobble;
  const c = document.createElement('canvas'); c.width = c.height = 512; const g = c.getContext('2d'); g.fillStyle = '#6d665c'; g.fillRect(0, 0, 512, 512); const R = rng(5);
  for (let y = 0; y < 512; y += 32) for (let x = (y / 32) % 2 ? -16 : 0; x < 512; x += 32) {
    const v = 150 + R() * 50 | 0, w = 28 + R() * 3, hh = 28 + R() * 3; g.fillStyle = `rgb(${v},${v - 8},${v - 20})`;
    g.beginPath(); g.roundRect(x + 2 + R() * 2, y + 2 + R() * 2, w - 3, hh - 3, 7); g.fill();
    g.fillStyle = 'rgba(255,255,255,.08)'; g.beginPath(); g.roundRect(x + 5, y + 4, w - 12, 5, 3); g.fill();
  }
  const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(6, 6); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; _cobble = t; return t;
}
const grainTex = (() => {
  const c = document.createElement('canvas'); c.width = c.height = 256; const g = c.getContext('2d'); const img = g.createImageData(256, 256), R = rng(9);
  for (let i = 0; i < 256 * 256; i++) { const v = 226 + R() * 29 - (R() < .03 ? 20 : 0); img.data.set([v, v, v, 255], i * 4); }
  g.putImageData(img, 0, 0); const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t;
})();
function label(text, sub, color = '#ffd257') {
  const c = document.createElement('canvas'); c.width = 512; c.height = 128; const g = c.getContext('2d');
  g.font = '700 54px "Barlow Condensed", Arial, sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
  g.lineWidth = 10; g.strokeStyle = 'rgba(0,0,0,.75)'; g.strokeText(text, 256, sub ? 46 : 64); g.fillStyle = '#fff'; g.fillText(text, 256, sub ? 46 : 64);
  if (sub) { g.font = '600 34px "Barlow Condensed", Arial, sans-serif'; g.strokeText(sub, 256, 100); g.fillStyle = color; g.fillText(sub, 256, 100); }
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace;
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: t, depthWrite: false, transparent: true, fog: false })); s.scale.set(2.2, .55, 1); s.renderOrder = 10; return s;
}
function projector(tint) {
  const g = new THREE.Group(), c = new THREE.Color(tint);
  const ring = new THREE.Mesh(new THREE.RingGeometry(.3, .38, 32), new THREE.MeshBasicMaterial({ color: c, transparent: true, opacity: .85, depthWrite: false, side: THREE.DoubleSide, fog: false })); ring.rotation.x = -Math.PI / 2; ring.position.y = .03;
  const cone = new THREE.Mesh(new THREE.CylinderGeometry(.8, .32, 1.2, 24, 1, true), new THREE.MeshBasicMaterial({ color: c, transparent: true, opacity: .12, depthWrite: false, side: THREE.DoubleSide, blending: THREE.AdditiveBlending, fog: false })); cone.position.y = .6;
  g.add(ring, cone); return g;
}
/* flora per biome for the streamed chunks */
// vegetation: toon_flora kit made in Blender (tools/blender_flora.py) — one consistent style for every plant
const TREES = ['FL_Tree_A', 'FL_Tree_B', 'FL_Tree_C', 'FL_Tree_A', 'FL_Tree_B'], BIRCH = ['FL_Birch'];
const PINES = ['FL_Pine_A', 'FL_Pine_B', 'FL_Pine_A'], DEAD = ['FL_Dead'], TWIST = ['FL_Tree_C', 'FL_Birch'];
const ROCKS = ['FL_Rock_A', 'FL_Rock_B', 'FL_Rock_A'];
const BUSH = ['FL_Bush_A', 'FL_Bush_B', 'FL_Bush_Flower', 'FL_Bush_Berry'], FLOWERS = ['FL_Flowers_Y', 'FL_Flowers_W', 'FL_Flowers_P', 'FL_Flowers_B'], PLANTS = ['FL_Fern', 'FL_Bush_B', 'FL_Fern', 'FL_TallGrass'];
const PALMS = ['FL_Palm', 'FL_Palm', 'FL_Cactus'], CLIFFS = ['Environment_Cliff1', 'Environment_Cliff2', 'Environment_Cliff3', 'Environment_Cliff4'];
const FLORA = {
  meadow: { trees: ['FL_Tree_A', 'FL_Tree_B', 'FL_Tree_C', 'FL_Birch', 'FL_Tree_A'], forest: .5, rocks: ['FL_Rock_A', 'FL_Rock_B'], bush: ['FL_Bush_A', 'FL_Bush_B', 'FL_Bush_Berry', 'FL_Bush_Flower'], flowers: ['FL_Flowers_Y', 'FL_Flowers_W', 'FL_Flowers_P', 'FL_Flowers_B'], tall: ['FL_TallGrass'] },
  marsh: { trees: ['FL_Pine_A', 'FL_Tree_B', 'FL_Birch', 'FL_Pine_B'], forest: .45, rocks: ['FL_Rock_A', 'FL_Stump', 'FL_Log'], bush: ['FL_Fern', 'FL_Reeds', 'FL_Bush_B', 'FL_Fern'], flowers: ['FL_Mushrooms', 'FL_Flowers_W', 'FL_Fern'], tall: ['FL_Reeds', 'FL_TallGrass'] },
  cliffs: { trees: ['FL_Pine_A', 'FL_Pine_B', 'FL_Birch'], forest: .55, rocks: ['FL_Rock_A', 'FL_Rock_B'], bush: ['FL_Bush_A', 'FL_Fern'], flowers: ['FL_Flowers_B', 'FL_Flowers_W'], tint: { leaf: '#c4d0f4', other: '#c8c8dc' } },
  snow: { trees: ['FL_Pine_Snow', 'FL_Pine_Snow', 'FL_Pine_A'], forest: .55, rocks: ['FL_Rock_A', 'FL_Rock_B'], bush: [], flowers: [] },
  plateau: { trees: ['FL_Dead', 'FL_Tree_C', 'FL_Pine_A'], forest: .62, rocks: ['FL_Rock_A', 'FL_Rock_B'], bush: ['FL_Bush_A', 'FL_TallGrass_Dry'], flowers: ['FL_Flowers_Y'], tall: ['FL_TallGrass_Dry'] },
  dunes: { trees: ['FL_Palm', 'FL_Palm', 'FL_Cactus', 'FL_Cactus_B'], forest: .66, rocks: ['FL_Rock_Sand'], bush: ['FL_TallGrass_Dry', 'FL_Cactus_B'], flowers: [] },
  volcanic: { trees: ['FL_Dead'], forest: .6, rocks: ['FL_Rock_Dark', 'FL_Rock_B'], bush: [], flowers: [], tint: { all: '#6a5a5a' } },
};

/* ================================================================== world */
export function createWorld(canvas, hooks = {}) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: false, powerPreference: 'high-performance' });
  renderer.outputColorSpace = THREE.SRGBColorSpace; renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  const scene = new THREE.Scene(), camera = new THREE.PerspectiveCamera(58, 16 / 9, .1, 900); scene.fog = new THREE.Fog('#c4dcf2', 90, 300);
  const hemi = new THREE.HemisphereLight('#ffffff', '#5a5040', 1.2), sun = new THREE.DirectionalLight('#fff4e0', 2.6);
  sun.castShadow = true; Object.assign(sun.shadow.camera, { left: -26, right: 26, top: 26, bottom: -26, near: 1, far: 160 }); sun.shadow.bias = -.0004; sun.shadow.normalBias = .035;
  scene.add(hemi, sun, sun.target);
  let style = 'toon', comic = true, quality = 'medium', pr = 1, prMax = 1, prT = 0, post = null, shadows = true, viewFar = 200, frameN = 0, vegR = 150;
  // build-time context (the town BUILD code below uses these names)
  let root = null, areaId = 'harbor', A = AREAS.harbor, h = H;
  let colliders = [], items = [], villagers = [], animated = [], tickers = [], markers = [], lampGlows = [], bolt = null;
  const grass = { push() {} }, grassField = () => null, addEchoes = () => {}, addNPC = () => {};
  // runtime
  let player = null, pet = null, near = null, busy = false, mode = 'explore', built = false, building = null, envTex = null, env = null;
  const worldRoot = new THREE.Group(), terrainRoot = new THREE.Group(), actorsRoot = new THREE.Group(); scene.add(worldRoot, terrainRoot, actorsRoot);
  const towns = {}, npcs = [], wilds = [], allItems = [], allVillagers = [];
  const keys = {}, cam = { yaw: Math.PI, pitch: .26, dist: 5.6, tYaw: Math.PI, tDist: 5.6, idle: 0 }; // Genshin-like: close, chest height, low pitch
  let running = false, paused = false, raf = 0, last = 0, t = 0, flash = 0, snap = true, vy = 0, onGround = true, rollT = 0, autoQ = true, blockMsgT = 0, battleCam = null, cineCam = null;
  const perf = { n: 0, s: 0 };
  function applyQuality() {
    quality = hooks.quality?.() || quality;
    const scale = clamp(hooks.renderScale?.() || 1, .5, 1);
    // sharp image first: phones have dpr 2.5-3.5, rendering below ~1.3 looks smeared. Dynamic resolution (loop) keeps it smooth.
    prMax = (quality === 'high' ? Math.min(devicePixelRatio, 2) : quality === 'medium' ? Math.min(devicePixelRatio, 1.6) : Math.min(devicePixelRatio, 1.3)) * scale;
    pr = prMax;
    GFX.density = quality === 'high' ? 1 : quality === 'medium' ? .8 : .5; GFX.grassFar = quality === 'high' ? 60 : quality === 'medium' ? 46 : 31;
    viewFar = quality === 'high' ? 320 : quality === 'medium' ? 210 : 150; vegR = quality === 'high' ? 230 : quality === 'medium' ? 160 : 110;
    renderer.shadowMap.autoUpdate = true;
    const sc = quality === 'high' ? 30 : 20; Object.assign(sun.shadow.camera, { left: -sc, right: sc, top: sc, bottom: -sc }); sun.shadow.camera.updateProjectionMatrix();
    shadows = quality !== 'low' && hooks.shadows?.() !== false; renderer.shadowMap.enabled = shadows;
    renderer.shadowMap.type = quality === 'high' ? THREE.PCFSoftShadowMap : THREE.PCFShadowMap;
    const ms = quality === 'high' ? 2048 : 1024; if (sun.shadow.mapSize.x !== ms) { sun.shadow.mapSize.set(ms, ms); sun.shadow.map?.dispose(); sun.shadow.map = null; }
    renderer.setPixelRatio(pr); post?.dispose(); comic = hooks.comic?.() !== false; CU.cOn.value = comic ? 1 : 0; style = hooks.style?.() || 'toon'; GFX.style = style;
    post = comic ? createComicPost(renderer, scene, camera, quality) : makePost(renderer, scene, camera, quality, { comic: false }); post.setStyle?.(style);
    renderer.toneMapping = comic ? THREE.NoToneMapping : THREE.ACESFilmicToneMapping; scene.environment = comic ? null : envTex; resize(); if (env) post?.look(env.look);
    scene.traverse(o => { if (o.material) (Array.isArray(o.material) ? o.material : [o.material]).forEach(m => m.needsUpdate = true); });
  }
  applyQuality();

  /* ---------- colliders: spatial hash (16 m cells) */
  const CG = 16, cgrid = new Map(), ck = (i, j) => i * 100003 + j;
  function addCollider(c) { const r = c.box ? Math.hypot(c.hw, c.hd) : c.r; c.cells = [];
    for (let i = Math.floor((c.x - r) / CG); i <= Math.floor((c.x + r) / CG); i++) for (let j = Math.floor((c.z - r) / CG); j <= Math.floor((c.z + r) / CG); j++) { const k = ck(i, j); let a = cgrid.get(k); if (!a) cgrid.set(k, a = []); a.push(c); c.cells.push(k); }
    return c; }
  function removeCollider(c) { for (const k of c.cells || []) { const a = cgrid.get(k); if (a) { const i = a.indexOf(c); if (i >= 0) a.splice(i, 1); } } }
  function nearColliders(x, z, r = 2) { const out = new Set(); for (let i = Math.floor((x - r) / CG); i <= Math.floor((x + r) / CG); i++) for (let j = Math.floor((z - r) / CG); j <= Math.floor((z + r) / CG); j++) { const a = cgrid.get(ck(i, j)); if (a) for (const c of a) out.add(c); } return out; }

  /* ---------- placement helpers (town-local while a town is being built) */
  const put = (obj, x, z, yOff = 0) => { obj.position.set(x, h(x, z) + yOff, z); obj.traverse(o => { if (o.isMesh && !o.material.transparent) { o.castShadow = true; o.receiveShadow = true; } }); root.add(obj); return obj; };
  const block = (x, z, r) => colliders.push({ x, z, r });
  const blockBox = (x, z, hw, hd, rot = 0) => colliders.push({ box: true, x, z, hw, hd, c: Math.cos(rot), s: Math.sin(rot) });
  const kit = (name, x, z, o = {}) => { const y = o.y ?? h(x, z) + (o.yOff || 0); const m = place(root, name, x, y, z, o); if (m && o.block) block(x, z, o.block); return m; };
  function scatter(names, n, seed, test, { rMin = 6, rMax = 54, sMin = .8, sMax = 1.25, yOff = 0, tint = null, shadow = true, blockR = 0, sink = .05 } = {}) {
    names = names.filter(has); if (!names.length) return;
    const R = rng(seed), lists = Object.fromEntries(names.map(k => [k, []])); let tries = 0, got = 0;
    while (got < n && tries++ < n * 40) {
      const a = R() * Math.PI * 2, r = rMin + Math.sqrt(R()) * (rMax - rMin), x = Math.cos(a) * r, z = Math.sin(a) * r, y = h(x, z);
      if (!test(x, z, y)) continue; if (blockR && colliders.some(c => !c.box && Math.hypot(c.x - x, c.z - z) < c.r + blockR * .6)) continue;
      const s = sMin + R() * (sMax - sMin), k = names[(R() * names.length) | 0]; lists[k].push([x, y + yOff - sink, z, R() * 6.28, s]); got++;
      if (blockR) block(x, z, blockR * s);
    }
    const cast = shadow && (quality === 'high' || blockR >= .9);
    for (const k of names) { const full = instances(root, k, lists[k], { shadow: cast, tint }); if (has(k + '_LOD') && curLod) { curLod.full.push(...full); curLod.lod.push(...instances(root, k + '_LOD', lists[k], { shadow: false, tint })); } }
  }
  const nearPath = (x, z, d = 2.2) => (TOWN_PATHS[areaId] || []).some(p => segDist(x, z, p.pts) < d);
  const clearOf = (x, z, d) => !colliders.some(c => Math.hypot(c.x - x, c.z - z) < (c.box ? Math.max(c.hw, c.hd) : c.r) + d);
  const offPath = (x, z) => !nearPath(x, z, 2.6);

  function lamp(x, z) {
    if (has('TT_Lamp')) { const o = kit('TT_Lamp', x, z, { rot: Math.atan2(-x, -z) }); block(x, z, .25);
      const glow = new THREE.Mesh(new THREE.SphereGeometry(.2, 10, 8), new THREE.MeshBasicMaterial({ color: new THREE.Color('#ffd79a').multiplyScalar(1.6) })); glow.position.y = 3.55; o?.add(glow);
      lampGlows.push({ m: glow.material, base: new THREE.Color('#ffd79a') }); return; }
    const g = new THREE.Group(), iron = new THREE.MeshStandardMaterial({ color: '#23262c', roughness: .5, metalness: .7 });
    const p = new THREE.Mesh(new THREE.CylinderGeometry(.06, .1, 3.2, 8), iron); p.position.y = 1.6;
    const arm = new THREE.Mesh(new THREE.BoxGeometry(.06, .06, .6), iron); arm.position.set(0, 3.1, .25);
    const cage = new THREE.Mesh(new THREE.CylinderGeometry(.16, .12, .36, 6), iron); cage.position.set(0, 2.9, .5);
    const glow = new THREE.Mesh(new THREE.SphereGeometry(.12, 10, 8), new THREE.MeshBasicMaterial({ color: new THREE.Color('#ffd79a').multiplyScalar(1.6) })); glow.position.set(0, 2.88, .5);
    lampGlows.push({ m: glow.material, base: new THREE.Color('#ffd79a') }); g.add(p, arm, cage, glow); put(g, x, z); block(x, z, .25); g.rotation.y = Math.atan2(-x, -z);
  }
  function addFind(kind, id, x, z) {
    const done = !!P.ensure().world.found[id], g = new THREE.Group();
    if (kind === 'glyph') {
      const st = new THREE.Mesh(new THREE.BoxGeometry(1.1, 2.2, .45, 1, 3, 1), new THREE.MeshStandardMaterial({ color: '#7a7d86', roughness: .95, flatShading: true }));
      const pp = st.geometry.attributes.position; for (let i = 0; i < pp.count; i++) pp.setX(i, pp.getX(i) * (1 - (pp.getY(i) + 1.1) * .12)); st.geometry.computeVertexNormals(); st.position.y = 1.1; st.rotation.z = .05;
      const rc = document.createElement('canvas'); rc.width = 64; rc.height = 128; const rg = rc.getContext('2d'); rg.strokeStyle = '#fff'; rg.lineWidth = 5; rg.lineCap = 'round'; const RR = rng(id.length * 7 + (x | 0));
      for (let i = 0; i < 5; i++) { rg.beginPath(); const y0 = 14 + i * 22; rg.moveTo(12 + RR() * 12, y0); rg.lineTo(32, y0 + 6 + RR() * 8); rg.lineTo(52 - RR() * 12, y0 + RR() * 10); rg.stroke(); }
      const tex = new THREE.CanvasTexture(rc), runeMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(done ? '#3a3d44' : '#5cf2d6').multiplyScalar(done ? 1 : 2.2), alphaMap: tex, transparent: true, fog: false, depthWrite: false });
      const rune = new THREE.Mesh(new THREE.PlaneGeometry(.6, 1.4), runeMat); rune.position.set(0, 1.15, .235);
      g.add(st, rune); animated.push(k => { if (!P.ensure().world.found[id]) runeMat.opacity = .6 + .4 * Math.sin(k * 3 + x); else runeMat.color.set('#3a3d44'); });
      kit('FL_Rock_B', x + .9, z - .4, { scale: .35, rot: x });
    } else if (kind === 'glass') {
      const m = new THREE.Mesh(new THREE.CapsuleGeometry(.5, .8, 4, 10), new THREE.MeshPhysicalMaterial({ color: done ? '#9aa' : '#bff6ff', transmission: .7, thickness: .6, roughness: .05, metalness: 0, emissive: col(done ? '#000' : '#1d6a78'), emissiveIntensity: .6 }));
      m.position.y = 1; const ears = new THREE.Mesh(new THREE.ConeGeometry(.2, .5, 5), m.material); ears.position.set(.25, 1.9, 0); g.add(m, ears);
    } else if (kind === 'pylon') {
      if (has('Column_Pipes')) place(g, 'Column_Pipes', 0, 0, 0, { scale: 1.05 });
      else { const mast = new THREE.Mesh(new THREE.CylinderGeometry(.12, .18, 5, 8), new THREE.MeshStandardMaterial({ color: '#8a8f9a', metalness: .6, roughness: .4 })); mast.position.y = 2.5; g.add(mast); }
      const orbM = new THREE.MeshBasicMaterial({ color: new THREE.Color(done ? '#5cf2d6' : '#ffd23c').multiplyScalar(2.5), fog: false }); const orb = new THREE.Mesh(new THREE.IcosahedronGeometry(.42, 1), orbM); orb.position.y = 5.6;
      g.add(orb); animated.push(k => { if (!P.ensure().world.found[id]) { orb.scale.setScalar(1 + .25 * Math.sin(k * 12 + x)); orb.rotation.y = k * 2; } else orbM.color.set('#5cf2d6').multiplyScalar(2.5); });
    }
    if (!done) { const beam = new THREE.Mesh(new THREE.CylinderGeometry(.35, .35, 30, 12, 1, true), new THREE.MeshBasicMaterial({ color: '#5cf2d6', transparent: true, opacity: .09, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide, fog: false })); beam.position.y = 15; g.add(beam); g.userData.beam = beam; }
    put(g, x, z); block(x, z, .8); items.push({ kind, id, x, z, g, r: 2.5 });
  }
  function sign(x, z) {
    const g = new THREE.Group(), wood = new THREE.MeshStandardMaterial({ color: '#6b4a2a', roughness: .9 });
    const p = new THREE.Mesh(new THREE.CylinderGeometry(.09, .1, 2.4, 8), wood); p.position.y = 1.2;
    for (const [dy, r, c] of [[2.1, .35, '#d9b36c'], [1.65, -.4, '#c99a58']]) { const b = new THREE.Mesh(new THREE.BoxGeometry(1.5, .38, .08), new THREE.MeshStandardMaterial({ color: c, roughness: .85 })); b.position.set(.5 * Math.sign(r), dy, 0); b.rotation.y = r; g.add(b); }
    g.add(p); const tag = label('Relay Ferry', 'Fast travel'); tag.position.y = 3; g.add(tag); put(g, x, z); block(x, z, .4); items.push({ kind: 'travel', id: 'travel:' + areaId, x, z, g, r: 2.6 });
  }
  function fountain(x, z) {
    const g = new THREE.Group(), stone = new THREE.MeshStandardMaterial({ color: '#b8b0a2', roughness: .9 });
    const basin = new THREE.Mesh(new THREE.CylinderGeometry(3, 3.2, .7, 32, 1, true), stone); basin.position.y = .35;
    const rim = new THREE.Mesh(new THREE.TorusGeometry(3.05, .18, 8, 40), stone); rim.rotation.x = Math.PI / 2; rim.position.y = .7;
    const bottom = new THREE.Mesh(new THREE.CircleGeometry(3, 32), stone); bottom.rotation.x = -Math.PI / 2; bottom.position.y = .05;
    const col1 = new THREE.Mesh(new THREE.CylinderGeometry(.35, .5, 2.2, 12), stone); col1.position.y = 1.1;
    const bowl = new THREE.Mesh(new THREE.CylinderGeometry(1.1, .5, .4, 20), stone); bowl.position.y = 2.2;
    const water = new THREE.Mesh(new THREE.CircleGeometry(2.9, 32), new THREE.MeshStandardMaterial({ color: '#4fb6d8', roughness: .08, metalness: .1, transparent: true, opacity: .82, emissive: new THREE.Color('#0b3c52') })); water.rotation.x = -Math.PI / 2; water.position.y = .55;
    const logo = new THREE.Mesh(new THREE.TorusGeometry(.45, .08, 8, 24), new THREE.MeshBasicMaterial({ color: new THREE.Color('#c9a4ff').multiplyScalar(2) })); logo.position.y = 2.9;
    g.add(basin, rim, bottom, col1, bowl, water, logo); put(g, x, z); block(x, z, 3.3);
    tickers.push(k => { logo.rotation.y = k; water.position.y = .55 + Math.sin(k * 2) * .02; });
  }
  function dockLine(x0, z0, x1, z1, y = -.35) {
    const len = Math.hypot(x1 - x0, z1 - z0), n = Math.ceil(len / 2.55), rot = Math.atan2(x1 - x0, z1 - z0), list = [];
    for (let i = 0; i <= n; i++) { const k = i / n; list.push([lerp(x0, x1, k), y, lerp(z0, z1, k), rot, 1.1]); }
    instances(root, 'Environment_Dock', list, { shadow: true }); return list;
  }
  function addVillagers(n, seed, route) {
    const R = rng(seed); if (quality !== 'high') n = Math.ceil(n * .5);
    for (let i = 0; i < n; i++) {
      const folk = TOWN_FOLK[areaId] || [], a = R() < .7 && folk.length ? folk[(seed + i) % folk.length] : null, A = a && ARCH[a];
      const ch = makeRigged(a ? archLook(a, rng(seed * 7 + i)) : villagerLook(rng(99 + (seed + i) % 10))); if (!ch) continue;
      const pts = route.map(([x, z]) => [x + (R() - .5) * 2, z + (R() - .5) * 2]); if (R() < .5) pts.reverse();
      const k = R() * pts.length | 0; const [x, z] = pts[k]; put(ch.group, x, z);
      villagers.push({ ch, pts, i: (k + 1) % pts.length, wait: R() * 4, speed: (A?.walker || 1.3) + R() * .5, name: A ? A.names[i % A.names.length] : null, line: A ? A.lines[i % A.lines.length] : VILLAGER_LINES[(seed + i) % VILLAGER_LINES.length], x, z });
    }
  }
  /** a person doing their job at a fixed spot (local town coords), facing `face` */
  function addWorker(a, x, z, face, seed) {
    const A = ARCH[a]; if (!A) return null; const R = rng(seed);
    const ch = makeRigged(archLook(a, R)); if (!ch) return null;
    put(ch.group, x, z); ch.group.rotation.y = face; ch.update(0);
    const J = JOBS[A.job]; if (J?.prop) attachProp(ch, J.prop);
    const v = { ch, pts: [[x, z]], i: 0, wait: 0, speed: 0, job: A.job, face, jt: R() * 3, name: A.names[seed % A.names.length], line: A.lines[seed % A.lines.length], x, z };
    villagers.push(v); block(x, z, .45); return v;
  }
  function glyphEntity(g0) {
    const g = new THREE.Group(), R = rng(7), mat = new THREE.MeshBasicMaterial({ color: new THREE.Color('#b48cff').multiplyScalar(2) }), geo = new THREE.OctahedronGeometry(.18);
    const shards = Array.from({ length: 120 }, () => { const m = new THREE.Mesh(geo, mat); m.userData = { a: R() * 6.28, r: .4 + R() * 1.6, y: .4 + R() * 3.2, s: .5 + R() * 1.5 }; g.add(m); return m; });
    const core = new THREE.Mesh(new THREE.IcosahedronGeometry(.6, 1), new THREE.MeshBasicMaterial({ color: '#e6d6ff', wireframe: true })); core.position.y = 2; g.add(core);
    g0.add(g); animated.push(k => { if (!g0.visible) return; shards.forEach(m => { const u = m.userData; m.position.set(Math.cos(u.a + k * u.s * .5) * u.r, u.y + Math.sin(k * u.s + u.a) * .3, Math.sin(u.a + k * u.s * .5) * u.r); m.rotation.y = k * u.s; }); core.rotation.set(k * .3, k * .5, 0); });
  }

  /* ================================================================== towns (the original hand-built areas, placed on the ring) */
  // vegetation: toon_flora kit made in Blender (tools/blender_flora.py) — one consistent style for every plant
const TREES = ['FL_Tree_A', 'FL_Tree_B', 'FL_Tree_C', 'FL_Tree_A', 'FL_Tree_B'], BIRCH = ['FL_Birch'];
  const PINES = ['FL_Pine_A', 'FL_Pine_B', 'FL_Pine_A'], DEAD = ['FL_Dead'], TWIST = ['FL_Tree_C', 'FL_Birch'];
  const ROCKS = ['FL_Rock_A', 'FL_Rock_B', 'FL_Rock_A'];
  const BUSH = ['FL_Bush_A', 'FL_Bush_B', 'FL_Bush_Flower', 'FL_Bush_Berry'], FLOWERS = ['FL_Flowers_Y', 'FL_Flowers_W', 'FL_Flowers_P', 'FL_Flowers_B'], PLANTS = ['FL_Fern', 'FL_Bush_B', 'FL_Fern', 'FL_TallGrass'];
  const PALMS = ['FL_Palm', 'FL_Palm', 'FL_Cactus'], CLIFFS = ['Environment_Cliff1', 'Environment_Cliff2', 'Environment_Cliff3', 'Environment_Cliff4'];

  const BUILD = {
    harbor() {
      const ly = h(-10, -11);
      if (has('TT_Lab')) { kit('TT_Lab', -10, -11, { y: ly - .05, scale: .72 }); blockBox(-10, -11, 4.8, 3.4); }
      else { house(root, -10, ly, -11, { w: 4, d: 3, floors: 2, wall: 'Brick', seed: 11, rot: 0, balcony: true }); blockBox(-10, -11, 4.3, 3.3);
        kit('Prop_SatelliteDish', -6.5, -12.5, { y: ly + 6.2, scale: .7, rot: .6 }); }
      const lt = label('POKÉBOX LABS', 'Research HQ', '#c9a4ff'); lt.scale.set(4.4, 1.1, 1); lt.position.set(-10, ly + (has('TT_Lab') ? 8.6 : 10.5), -8); root.add(lt);
      for (const [x, z, n] of [[-15.2, -6.4, 'Prop_Crate'], [-14, -6.2, 'Prop_Barrel1'], [-5, -6.6, 'Prop_Crate_Tarp'], [-4, -7.2, 'Prop_Barrel2_Closed']]) kit(n, x, z, { rot: x, scale: .75, block: .6 });
      kit('Prop_Light_Floor', -10, -6.8, { scale: .8 });
      const HS = [[10, -12, 3, 3, 2, 'Plaster', 3], [18, -2, 2, 3, 1, 'Plaster', 5], [-20, 6, 3, 3, 1, 'Brick', 7], [5, -23, 3, 4, 2, 'Plaster', 9], [-5, -24, 2, 2, 1, 'Plaster', 13], [-24, -6, 2, 3, 2, 'Brick', 17], [22, 18, 2, 2, 1, 'Plaster', 19]];
      for (const [x, z, w, d, f, wall, seed] of HS) { const rot = Math.atan2(-x, -z + 2);
        if (x === 10 && z === -12 && has('TT_Shop')) { kit('TT_Shop', x, z, { rot, scale: 1.05 }); blockBox(x, z, 3.9, 3.4, rot); continue; } // the card shop
        house(root, x, h(x, z), z, { w, d, floors: f, wall, seed, rot, balcony: f > 1 }); blockBox(x, z, w + .3, d + .3, rot); }
      const shopTag = label('CARD SHOP', 'Packs & Vault', '#ffd257'); shopTag.scale.set(3.2, .8, 1); shopTag.position.set(9.3, h(10, -12) + (has('TT_Shop') ? 5.4 : 7.8), -9.4); root.add(shopTag);
      fountain(0, 2);
      const plaza = new THREE.Mesh(new THREE.CircleGeometry(11.8, 48).rotateX(-Math.PI / 2), new THREE.MeshStandardMaterial({ map: cobbleTex(), roughness: .9, polygonOffset: true, polygonOffsetFactor: -2 }));
      plaza.position.set(0, h(0, 2) + .03, 2); plaza.receiveShadow = true; root.add(plaza);
      for (const [x, z] of [[-6, -4], [6, -4], [-8, 8], [8, 8], [2, 14], [3, 24], [-3, 24], [14, 12], [18, 16.5], [-14, 5.5], [-22, 1.5], [5.6, -12], [12, -18.5], [22, -16]]) lamp(x, z);
      for (const [x, z, r] of [[7, 5, .4], [-7, 6, -.3]]) { kit('Prop_Wagon', x, z, { rot: r, scale: .9, block: 1.6 }); kit('Prop_Crate', x + 1.6, z - 1, { rot: r, scale: .8, block: .6 }); kit('Prop_Barrel', x - 1.4, z + .8, { scale: 1.1 }); }
      for (let i = 0; i < 8; i++) kit('Prop_WoodenFence_Single', -30 + i * 2.05, 16 + Math.sin(i) * .3, { rot: .05 });
      dockLine(21, 22, 21, 44); dockLine(21, 36, 31, 36);
      for (const [x, z] of [[19.6, 26], [22.4, 30], [19.6, 40], [30, 34.6]]) kit('Environment_Dock_Pole', x, z, { y: -.35, scale: 1.1 });
      const boat = kit('Ship_Small', 26.5, 41, { y: -.25, rot: Math.PI / 2, scale: 1.3 }); tickers.push(k => { if (boat) { boat.position.y = -.25 + Math.sin(k * 1.1) * .08; boat.rotation.z = Math.sin(k * .9) * .03; } });
      const ship = kit('Ship_Large', 62, 58, { y: -.6, rot: 2.2, scale: 1.4 }); tickers.push(k => { if (ship) { ship.position.y = -.6 + Math.sin(k * .6) * .15; ship.rotation.x = Math.sin(k * .5) * .02; } });
      for (const [x, z, n] of [[20.2, 27, 'Prop_Barrel'], [21.8, 29.6, 'Prop_Bucket_Fishes'], [20.4, 33, 'Prop_Chest_Closed'], [22, 41, 'Prop_Anchor'], [28, 36.4, 'Prop_Barrel']]) kit(n, x, z, { y: .68, rot: x * 3, scale: 1.2 });
      scatter(PALMS, 26, 12, (x, z, y) => y > .05 && y < .9 && offPath(x, z) && clearOf(x, z, 1.5), { rMin: 30, rMax: 52, sMin: 1.4, sMax: 2.1, blockR: .5 });
      scatter(['FL_Rock_Sand', 'FL_Rock_Sand', 'FL_Rock_Sand'], 30, 14, (x, z, y) => y > -.6 && y < .5, { rMin: 32, rMax: 56, sMin: 1.5, sMax: 3.2 });
      scatter(has('TT_Tree_Round') ? ['TT_Tree_Round', 'TT_Tree_Round2', 'TT_Tree_Round', 'FL_Tree_A', 'FL_Tree_C'] : [...TREES, ...BIRCH, 'FL_Tree_B'], 52, 21, (x, z, y) => y > .9 && offPath(x, z) && clearOf(x, z, 3.5) && Math.hypot(x, z - 2) > 16, { rMin: 16, rMax: 48, sMin: .7, sMax: 1.05, blockR: .6 });
      scatter(BUSH, 60, 22, (x, z, y) => y > .8 && offPath(x, z) && clearOf(x, z, 1.2), { rMin: 8, rMax: 44, sMin: .8, sMax: 1.3, shadow: false });
      scatter(FLOWERS, 90, 23, (x, z, y) => y > .8 && offPath(x, z) && clearOf(x, z, .8) && Math.hypot(x, z - 2) > 11.5, { rMin: 6, rMax: 44, sMin: .7, sMax: 1.2, shadow: false });
      scatter(ROCKS, 16, 24, (x, z, y) => y > .8 && offPath(x, z) && clearOf(x, z, 2), { rMin: 20, rMax: 46, sMin: .4, sMax: .9, blockR: .9 });
         
      addFind('glyph', 'harbor:0', -27, -14); addFind('glyph', 'harbor:1', 25, -19); sign(-2, 20);
      for (const [a, x, z, f, sd] of [['fisher', 20.9, 44.5, 0, 1], ['fisher', 31, 36.5, 1.57, 2], ['docker', -14.6, -5, 3.6, 3], ['merchant', 8.8, 3.6, -2.4, 4], ['elder_m', 3.2, -2.6, -2.2, 5], ['elder_f', 4.4, -3.8, .9, 6], ['scholar', -7.6, -6.4, .3, 7], ['worker_f', -3, 9, 2, 8]]) addWorker(a, x, z, f, sd);
      addVillagers(6, 31, [[0, 12], [6, 6], [4, -3], [-5, -2], [-8, 6], [-2, 14]]); addVillagers(2, 37, [[16, 12], [20, 20], [21, 30], [20, 20]]);
      
    },
    mistvale() {
      scatter(PINES, 55, 21, (x, z, y) => y > .5 && offPath(x, z) && clearOf(x, z, 3), { rMin: 10, rMax: 50, sMin: .7, sMax: 1.1, blockR: .6 });
      scatter(has('TT_Tree_Round2') ? ['TT_Tree_Round2', 'TT_Tree_Pine'] : TWIST, 6, 25, (x, z, y) => y > .6 && offPath(x, z) && clearOf(x, z, 6), { rMin: 22, rMax: 44, sMin: .45, sMax: .6, blockR: 1.2 });
      scatter([...PLANTS, 'FL_Fern', 'FL_Fern'], 180, 22, (x, z, y) => y > -.1 && offPath(x, z), { rMin: 4, rMax: 50, sMin: .7, sMax: 1.3, shadow: false });
      scatter(['FL_Mushrooms', 'FL_Mushrooms'], 40, 26, (x, z, y) => y > .2 && offPath(x, z), { rMin: 6, rMax: 46, sMin: .8, sMax: 1.6, shadow: false });
      scatter(ROCKS, 22, 27, (x, z, y) => y > -.3 && offPath(x, z) && clearOf(x, z, 2), { rMin: 8, rMax: 48, sMin: .35, sMax: .8, blockR: .8 });
      scatter(['FL_TallGrass_Dry', 'FL_TallGrass'], 120, 28, (x, z, y) => y > -.4 && y < .6, { rMin: 4, rMax: 50, sMin: .9, sMax: 1.5, shadow: false });
      house(root, 16, h(16, 5), 5, { w: 2, d: 3, floors: 1, wall: 'Plaster', seed: 3, rot: -1.1 }); blockBox(16, 5, 2.4, 3.3, -1.1);
      const wheel = new THREE.Group(), wood = new THREE.MeshStandardMaterial({ color: '#6b4a2a', roughness: .9 });
      wheel.add(new THREE.Mesh(new THREE.TorusGeometry(2.2, .14, 6, 24), wood)); for (let i = 0; i < 10; i++) { const b = new THREE.Mesh(new THREE.BoxGeometry(.12, 4.4, .6), wood); b.rotation.z = i / 10 * Math.PI; wheel.add(b); }
      wheel.position.set(12.2, 1.5, -1); wheel.rotation.y = .3; wheel.traverse(o => { if (o.isMesh) o.castShadow = true; }); root.add(wheel); animated.push(k => wheel.rotation.z = k * .6);
      house(root, -22, h(-22, -12), -12, { w: 2, d: 2, floors: 1, wall: 'Brick', seed: 8, rot: .8 }); blockBox(-22, -12, 2.3, 2.3, .8);
      const pads = []; const RP = rng(4); for (let i = 0; i < 90; i++) { const a = RP() * 6.28, r = RP() * 10, x = 12 + Math.cos(a) * r, z = -6 + Math.sin(a) * r; if (h(x, z) < -.2) pads.push([x, z]); }
      const padM = new THREE.InstancedMesh(new THREE.CircleGeometry(.45, 10, .3, 5.8).rotateX(-Math.PI / 2), new THREE.MeshStandardMaterial({ color: '#4f8a3a', roughness: .7 }), Math.max(1, pads.length)); const o3 = new THREE.Object3D();
      pads.forEach(([x, z], i) => { o3.position.set(x, .08, z); o3.rotation.set(0, RP() * 6, 0); o3.scale.setScalar(.7 + RP() * .7); o3.updateMatrix(); padM.setMatrixAt(i, o3.matrix); }); padM.count = pads.length; root.add(padM);
      for (let i = 0; i < 6; i++) kit('Prop_WoodenFence_Single', 2 + i * 2.05, 12 + i * .3, { rot: -.15 });
       
      addFind('glyph', 'mistvale:0', 12, -4.5); addFind('glyph', 'mistvale:1', -20, 18); addFind('glyph', 'mistvale:2', 26, 24); sign(5, 30);
      addVillagers(2, 41, [[0, 20], [4, 10], [12, 5], [4, 10]]); 
    },
    sandreach() {
      scatter(CLIFFS, 14, 31, (x, z, y) => offPath(x, z) && clearOf(x, z, 6), { rMin: 26, rMax: 50, sMin: 1.6, sMax: 2.8, blockR: 3, tint: { all: '#e8a36a' } });
      scatter(['FL_Rock_Sand', 'FL_Rock_Sand'], 30, 32, (x, z, y) => offPath(x, z) && clearOf(x, z, 2), { rMin: 8, rMax: 50, sMin: .5, sMax: 1.1, blockR: .9 });
      scatter(PALMS, 14, 33, (x, z, y) => y < 1.4 && offPath(x, z) && clearOf(x, z, 2), { rMin: 14, rMax: 46, sMin: 1.5, sMax: 2.2, blockR: .5 });
      scatter(DEAD, 10, 34, (x, z, y) => offPath(x, z) && clearOf(x, z, 4), { rMin: 12, rMax: 46, sMin: .4, sMax: .6, blockR: .6 });
      scatter(['FL_TallGrass_Dry'], 60, 35, (x, z, y) => offPath(x, z), { rMin: 6, rMax: 48, sMin: .7, sMax: 1.2, shadow: false, tint: null });
      const crys = new THREE.MeshPhysicalMaterial({ color: '#c8f7ff', transmission: .6, thickness: .5, roughness: .05, emissive: col('#1f6c7a'), emissiveIntensity: .4 });
      const RC = rng(36); const cl = []; for (let i = 0; i < 40; i++) { const a = RC() * 6.28, r = 6 + RC() * 44, x = Math.cos(a) * r, z = Math.sin(a) * r; if (nearPath(x, z)) continue; cl.push([x, z, .4 + RC() * .9]); }
      const cm = new THREE.InstancedMesh(new THREE.OctahedronGeometry(.6, 0), crys, cl.length), o3 = new THREE.Object3D(); cl.forEach(([x, z, s], i) => { o3.position.set(x, h(x, z) + .3 * s, z); o3.rotation.set(RC(), RC() * 6, RC()); o3.scale.set(s, s * 1.8, s); o3.updateMatrix(); cm.setMatrixAt(i, o3.matrix); }); cm.castShadow = true; root.add(cm);
      kit('Prop_Wagon', -6, -8, { rot: .8, block: 1.8 }); kit('Prop_Crate', -2.5, -7.5, { scale: .8, block: .6 }); kit('Prop_Barrel', -3.5, -5.5, { scale: 1.2 });
       
      addFind('glass', 'sandreach:0', -22, -10); addFind('glass', 'sandreach:1', 18, -24); addFind('glass', 'sandreach:2', 30, 6); sign(5, 34); 
    },
    starfall() {
      const oy = h(-4, -14);
      if (has('SF_Observatory')) { kit('SF_Observatory', -4, -14, { y: oy - .1, rot: Math.atan2(4, 14), scale: 1.05 }); block(-4, -14, 6.4); }
      else {
      kit('Platform_Round1', -4, -14, { y: oy + .05, scale: 1.6 });
      const dome = new THREE.Mesh(new THREE.SphereGeometry(5.2, 32, 16, 0, Math.PI * 2, 0, Math.PI / 2), new THREE.MeshStandardMaterial({ color: '#dfe3ee', roughness: .35, metalness: .4 })); dome.position.set(-4, oy + 2.8, -14); root.add(dome); dome.castShadow = true;
      const baseC = new THREE.Mesh(new THREE.CylinderGeometry(5.4, 5.8, 2.8, 32), new THREE.MeshStandardMaterial({ color: '#8e9aa6', roughness: .8 })); baseC.position.set(-4, oy + 1.4, -14); root.add(baseC); baseC.castShadow = baseC.receiveShadow = true; block(-4, -14, 6);
      const slit = new THREE.Mesh(new THREE.BoxGeometry(1.4, 5.6, .4), new THREE.MeshBasicMaterial({ color: '#1a1d2e' })); slit.position.set(-4, oy + 5.2, -9.2); slit.rotation.x = -.55; root.add(slit);
      const scope = new THREE.Mesh(new THREE.CylinderGeometry(.55, .8, 6, 16), new THREE.MeshStandardMaterial({ color: '#4a4f63', metalness: .7, roughness: .3 })); scope.rotation.x = .9; scope.position.set(-4, oy + 7, -10); root.add(scope); }
      kit('Prop_SatelliteDish', 8, -4, { scale: .8, rot: 2.5, block: 1 }); kit('Prop_SatelliteDish', 14, -12, { scale: .6, rot: 1.8, block: .8 });
      kit('Prop_Computer', 6.5, -2.5, { scale: .9, rot: 2 }); kit('Prop_Crate', 9.5, -1.5, { scale: .7, block: .6 }); kit('Column_Round', 11, -4, { scale: .7 });
      scatter(PINES, 36, 41, (x, z, y) => offPath(x, z) && clearOf(x, z, 3), { rMin: 14, rMax: 44, sMin: .6, sMax: 1, blockR: .6, tint: { leaf: '#c4d0f4', other: '#c8c8dc' } });
      scatter(ROCKS, 26, 42, (x, z, y) => offPath(x, z) && clearOf(x, z, 2), { rMin: 8, rMax: 46, sMin: .4, sMax: 1.1, blockR: .9, tint: { all: '#8a90b0' } });
      scatter(FLOWERS, 70, 43, (x, z, y) => offPath(x, z) && clearOf(x, z, 1), { rMin: 6, rMax: 42, sMin: .7, sMax: 1.1, shadow: false, tint: { leaf: '#a8b8ff', other: '#c8b8ff' } });
       addFind('glyph', 'starfall:0', 20, 10); addFind('glyph', 'starfall:1', -22, 16); sign(5, 30); 
    },
    voltspire() {
      scatter(DEAD, 20, 51, (x, z, y) => offPath(x, z) && clearOf(x, z, 4), { rMin: 10, rMax: 48, sMin: .45, sMax: .75, blockR: .6 });
      scatter(ROCKS, 40, 52, (x, z, y) => offPath(x, z) && clearOf(x, z, 2), { rMin: 8, rMax: 50, sMin: .5, sMax: 1.4, blockR: 1 });
      scatter(CLIFFS, 10, 53, (x, z, y) => offPath(x, z) && clearOf(x, z, 6), { rMin: 30, rMax: 50, sMin: 1.4, sMax: 2.4, blockR: 3, tint: { all: '#9a9480' } });
      scatter(['FL_TallGrass_Dry'], 80, 54, (x, z, y) => offPath(x, z), { rMin: 6, rMax: 48, sMin: .8, sMax: 1.3, shadow: false, tint: null });
      kit('Platform_Metal', 0, 0, { yOff: .05, scale: 1.5 }); kit('Column_Pipes', 0, 0, { scale: 2.2, block: 1.4 }); kit('Prop_Crate_Large', 4, 3, { scale: .7, rot: .4, block: 1.2 }); kit('Prop_Barrel1', -3.5, 3.5, { scale: .9 });
      const top = new THREE.Mesh(new THREE.IcosahedronGeometry(.9, 1), new THREE.MeshBasicMaterial({ color: new THREE.Color('#fff2a0').multiplyScalar(3) })); top.position.set(0, h(0, 0) + 11.4, 0); root.add(top); animated.push(k => { top.scale.setScalar(1 + Math.sin(k * 9) * .15); });
       
      addFind('pylon', 'voltspire:0', -20, -8); addFind('pylon', 'voltspire:1', 22, 8); addFind('pylon', 'voltspire:2', 0, -30); sign(5, 34); 
    },
    frostline() {
      scatter(['FL_Pine_Snow', 'FL_Pine_Snow', 'FL_Pine_A'], 60, 61, (x, z, y) => offPath(x, z) && clearOf(x, z, 3), { rMin: 10, rMax: 50, sMin: .6, sMax: 1.05, blockR: .6 });
      scatter(ROCKS, 30, 62, (x, z, y) => offPath(x, z) && clearOf(x, z, 2), { rMin: 8, rMax: 48, sMin: .5, sMax: 1.3, blockR: 1 });
      const ice = new THREE.MeshPhysicalMaterial({ color: '#bfe3ff', transmission: .5, thickness: 1, roughness: .1, emissive: col('#2a6a9a'), emissiveIntensity: .25 });
      const RI = rng(63), il = []; for (let i = 0; i < 60; i++) { const a = RI() * 6.28, r = 10 + RI() * 40, x = Math.cos(a) * r, z = Math.sin(a) * r; if (!nearPath(x, z) && clearOf(x, z, 2)) il.push([x, z, .6 + RI()]); }
      const im = new THREE.InstancedMesh(new THREE.ConeGeometry(.7, 4, 6), ice, il.length), o3 = new THREE.Object3D(); il.forEach(([x, z, s], i) => { o3.position.set(x, h(x, z) + 1.6 * s, z); o3.rotation.set((RI() - .5) * .4, RI() * 6, (RI() - .5) * .4); o3.scale.set(s, s, s); o3.updateMatrix(); im.setMatrixAt(i, o3.matrix); block(x, z, .6 * s); }); im.castShadow = true; root.add(im);
      house(root, -14, h(-14, 8), 8, { w: 2, d: 3, floors: 1, wall: 'Brick', seed: 21, rot: 1.2 }); blockBox(-14, 8, 2.3, 3.3, 1.2);
        addFind('glyph', 'frostline:0', 24, -16); addFind('glyph', 'frostline:1', -24, -20); sign(5, 32); 
    },
    rift() {
      const ny = h(0, -18);
      kit('Platform_Round1', 0, -18, { y: ny + .05, scale: 2.2 });
      for (let i = 0; i < 6; i++) { const a = i / 6 * Math.PI * 2; kit('Column_Round', Math.cos(a) * 5, -18 + Math.sin(a) * 5, { y: ny, scale: 1.4, block: .8 }); }
      const node = new THREE.Mesh(new THREE.CylinderGeometry(2.2, 3, 26, 8), new THREE.MeshStandardMaterial({ color: '#1a1d22', metalness: .8, roughness: .35 })); node.position.set(0, ny + 13, -18); root.add(node); node.castShadow = true; block(0, -18, 3.2);
      const seams = new THREE.Mesh(new THREE.CylinderGeometry(2.25, 3.05, 26, 8, 12, true), new THREE.MeshBasicMaterial({ color: new THREE.Color('#5cf2d6').multiplyScalar(2), wireframe: true, transparent: true, opacity: .35 })); seams.position.copy(node.position); root.add(seams);
      const ring = new THREE.Mesh(new THREE.TorusGeometry(4.2, .14, 8, 48), new THREE.MeshBasicMaterial({ color: new THREE.Color('#5cf2d6').multiplyScalar(3) })); ring.rotation.x = Math.PI / 2; ring.position.set(0, ny + 6, -18); root.add(ring); animated.push(k => { ring.position.y = ny + 6 + Math.sin(k) * 5; });
      const cry = new THREE.MeshStandardMaterial({ color: '#5cf2d6', emissive: col('#1fb89c'), emissiveIntensity: 1.2, roughness: .2, metalness: .1 });
      const RC = rng(71), cl = []; for (let i = 0; i < 60; i++) { const a = RC() * 6.28, r = 9 + RC() * 42, x = Math.cos(a) * r, z = Math.sin(a) * r; if (!nearPath(x, z) && clearOf(x, z, 1.5)) cl.push([x, z, .5 + RC() * 1.4]); }
      const cm = new THREE.InstancedMesh(new THREE.OctahedronGeometry(1, 0), cry, cl.length), o3 = new THREE.Object3D(); cl.forEach(([x, z, s], i) => { o3.position.set(x, h(x, z) + s * .8, z); o3.rotation.set(RC() * .5, RC() * 6, RC() * .5); o3.scale.set(s * .6, s * 1.6, s * .6); o3.updateMatrix(); cm.setMatrixAt(i, o3.matrix); if (s > 1) block(x, z, .5 * s); }); root.add(cm);
      scatter(TWIST, 8, 72, (x, z, y) => offPath(x, z) && clearOf(x, z, 6), { rMin: 20, rMax: 46, sMin: .4, sMax: .55, blockR: 1.2, tint: { leaf: '#1f5a50', other: '#3a3a44' } });
      scatter(DEAD, 16, 73, (x, z, y) => offPath(x, z) && clearOf(x, z, 3), { rMin: 12, rMax: 48, sMin: .4, sMax: .7, blockR: .6, tint: { all: '#4a4a55' } });
      scatter(ROCKS, 30, 74, (x, z, y) => offPath(x, z) && clearOf(x, z, 2), { rMin: 8, rMax: 50, sMin: .5, sMax: 1.3, blockR: 1, tint: { all: '#3a3f46' } });
       
      sign(5, 32); 
    },
  };

  let curLod = null;
  function buildTown(id) {
    const R = REGIONS[id]; areaId = id; A = AREAS[id];
    h = (x, z) => H(x + R.x, z + R.z);
    root = new THREE.Group(); root.position.set(R.x, 0, R.z); worldRoot.add(root);
    colliders = []; items = []; villagers = []; curLod = { x: R.x, z: R.z, full: [], lod: [] }; townLods.push(curLod);
    try { BUILD[id](); } catch (e) { console.warn('[world] town build', id, e); }
    try { decorateTown(id); } catch (e) { console.warn('[world] town decor', id, e); }
    if (id === 'rift') { const g0 = new THREE.Group(); g0.position.set(0, h(0, -8), -8); root.add(g0); glyphEntity(g0); }
    for (const c of colliders) { c.x += R.x; c.z += R.z; addCollider(c); }
    for (const it of items) { it.x += R.x; it.z += R.z; allItems.push(it); }
    for (const v of villagers) { v.pts = v.pts.map(([x, z]) => [x + R.x, z + R.z]); v.x += R.x; v.z += R.z; v.ch.group.position.x += R.x; v.ch.group.position.z += R.z; actorsRoot.add(v.ch.group); v.town = id; allVillagers.push(v); }
    towns[id] = { root, x: R.x, z: R.z }; h = H; root = null;
  }

  /* ================================================================== toon-town extras: Relay Center, Trial Hall (gym), benches & flowerbeds
     placed automatically on flat, empty ground so they never collide with the hand-built layout or the story NPCs */
  const decorLog = [];
  const WARDEN_OF = { mistvale: 'mira', starfall: 'sable', frostline: 'orin', voltspire: 'vera', sandreach: 'dom' };
  function findSpot(cx, cz, rad, { rMin = 0, rMax = 30, seed = 1, avoid = [], face = null, slope = 1.1 } = {}) {
    const R = rng(seed);
    for (let t = 0; t < 260; t++) {
      const a = R() * Math.PI * 2, r = rMin + R() * (rMax - rMin), x = cx + Math.cos(a) * r, z = cz + Math.sin(a) * r;
      if (Math.hypot(x, z) < 9 + rad) continue;                                     // keep the plaza free
      const ys = [[0, 0], [rad * .7, 0], [-rad * .7, 0], [0, rad * .7], [0, -rad * .7]].map(([dx, dz]) => h(x + dx, z + dz));
      const lo = Math.min(...ys), hi = Math.max(...ys); if (hi - lo > slope || lo < .7) continue;     // flat, dry land
      if (nearPath(x, z, rad * .75 + 1.2) || !clearOf(x, z, rad * .8)) continue;
      if (avoid.some(([ax, az, ar]) => Math.hypot(ax - x, az - z) < ar + rad)) continue;
      return { x, z, y: lo, rot: face ? Math.atan2(face[0] - x, face[1] - z) : 0 };
    }
    return null;
  }
  function decorateTown(id) {
    if (!has('TT_RelayCenter') || id === 'rift') return;
    const R = REGIONS[id], seed = id.length * 97;
    const npcs = QS.ROSTER.filter(r => r.pos.region === id || Math.hypot(r.pos.x - R.x, r.pos.z - R.z) < 60).map(r => [r.pos.x - R.x, r.pos.z - R.z, 3.5]);
    // Relay Center: near the middle of town, door facing the plaza
    const rc = findSpot(0, 0, 6.8, { rMin: 14, rMax: 36, seed: seed + 1, avoid: npcs, face: [0, 0] });
    if (rc) { decorLog.push(['relay', id, rc.x + R.x, rc.z + R.z]); kit('TT_RelayCenter', rc.x, rc.z, { y: rc.y - .1, rot: rc.rot, scale: .9 }); blockBox(rc.x, rc.z, 5.4, 4.2, rc.rot);
      const tg = label('RELAY CENTER', 'Rest · save · card storage', '#5cf2d6'); tg.position.set(rc.x, rc.y + 8.2, rc.z); tg.scale.multiplyScalar(1.3); root.add(tg);
      npcs.push([rc.x, rc.z, 8]); }
    // Trial Hall next to the town's Warden
    const wid = WARDEN_OF[id], w = wid && QS.ROSTER.find(r => r.id === wid);
    if (w) { const wx = w.pos.x - R.x, wz = w.pos.z - R.z; let gs = findSpot(wx, wz, 7.6, { rMin: 8, rMax: 30, seed: seed + 2, slope: 1.1, avoid: npcs.filter(n => Math.hypot(n[0] - wx, n[1] - wz) > 1), face: [wx, wz] });
      if (!gs) gs = findSpot(wx, wz, 7.6, { rMin: 8, rMax: 48, seed: seed + 5, slope: 1.9, avoid: npcs.filter(n => Math.hypot(n[0] - wx, n[1] - wz) > 1), face: [wx, wz] });
      if (gs) { decorLog.push(['gym', id, gs.x + R.x, gs.z + R.z]); kit('TT_Gym', gs.x, gs.z, { y: gs.y - .1, rot: gs.rot, scale: .82 }); blockBox(gs.x, gs.z, 6.1, 5.3, gs.rot);
        const tg = label(AREAS[id].name.toUpperCase() + ' TRIAL HALL', (P.CAST[wid]?.name || 'Warden') + "'s Trial", '#c9a4ff'); tg.position.set(gs.x, gs.y + 9, gs.z); tg.scale.multiplyScalar(1.3); root.add(tg);
        npcs.push([gs.x, gs.z, 9]); } }
    // regional districts (towns2 kit made in Blender): every town gets its own architecture around the plaza
    const DIST = {
      mistvale: [['MV_Cottage_A', 3], ['MV_Cottage_B', 3], ['MV_Stilt', 2], ['MV_Lookout', 1]],
      starfall: [['SF_Archive', 1], ['SF_House', 5]],
      frostline: [['FL_Lodge', 1], ['FL_Chalet_A', 3], ['FL_Chalet_B', 3]],
      voltspire: [['VS_Station', 1], ['VS_Block_B', 2], ['VS_Block_A', 3], ['VS_Block_C', 3]],
      sandreach: [['SR_Workshop', 1], ['SR_Adobe_B', 2], ['SR_Adobe_A', 3], ['SR_Adobe_C', 3], ['SR_Market_A', 2], ['SR_Market_B', 2]],
      harbor: [['SR_Market_B', 1], ['SR_Market_A', 1]],
    }[id] || [];
    let di = 0;
    for (const [name, n] of DIST) {
      if (!has(name)) continue; const bb = bounds(name), sc = name.includes('Market') ? 1 : .85, rad = Math.max(bb.max.x - bb.min.x, bb.max.z - bb.min.z) / 2 * sc;
      for (let k = 0; k < n; k++) {
        const sp = findSpot(0, 0, rad, { rMin: 12 + rad, rMax: 46, seed: seed + 40 + di++ * 7, avoid: npcs, face: [0, 0], slope: 1.3 });
        if (!sp) continue;
        decorLog.push(['bld', id, name, sp.x + R.x, sp.z + R.z]);
        kit(name, sp.x, sp.z, { y: sp.y - .15, rot: sp.rot, scale: sc }); blockBox(sp.x, sp.z, (bb.max.x - bb.min.x) * sc * .46, (bb.max.z - bb.min.z) * sc * .46, sp.rot);
        npcs.push([sp.x, sp.z, rad + 1.5]);
        const who = BLD_JOB[name], dep = (bb.max.z - bb.min.z) * sc / 2 + 1.7;
        if (who && (di % 3 !== 2)) { const fx = sp.x + Math.sin(sp.rot) * dep, fz = sp.z + Math.cos(sp.rot) * dep;
          if (h(fx, fz) > .3 && !nearPath(fx, fz, .6)) addWorker(who, fx + Math.cos(sp.rot) * 1.2, fz - Math.sin(sp.rot) * 1.2, sp.rot + (ARCH[who].job === 'chat' ? 0 : Math.PI * .1), seed + di * 13); }
      }
    }
    // benches & flowerbeds along the town paths
    const Rr = rng(seed + 3);
    for (const p of TOWN_PATHS[id] || []) for (let i = 0; i < p.pts.length - 1; i++) {
      const [ax, az] = p.pts[i], [bx, bz] = p.pts[i + 1], L = Math.hypot(bx - ax, bz - az), dx = (bx - ax) / L, dz = (bz - az) / L;
      for (let d = 4; d < L - 2; d += 9) {
        const side = Rr() < .5 ? -1 : 1, x = ax + dx * d - dz * side * 2.9, z = az + dz * d + dx * side * 2.9;
        if (Math.hypot(x, z) < 12 || !clearOf(x, z, 1.4) || h(x, z) < .6 || npcs.some(([nx, nz]) => Math.hypot(nx - x, nz - z) < 3)) continue;
        const name = Rr() < .55 ? 'TT_Flowerbed' : 'TT_Bench', rot = Math.atan2(dz * side * -1, -dx * side) ;
        kit(name, x, z, { rot: Math.atan2(-(-dz * side), -(dx * side)), block: .7 });
      }
    }
  }

  /* ================================================================== terrain streaming (worker) */
  const CH = 128, chunks = new Map();
  let worker = null, wseq = 0; const wwait = new Map();
  function ensureWorker() {
    if (worker) return worker;
    worker = new Worker(new URL('./terrain.worker.js', import.meta.url), { type: 'module' });
    worker.onmessage = e => { if (e.data.progress != null) { hooks.loading?.(true, 'Mapping Veyra… ' + Math.round(e.data.progress * 100) + '%'); return; } const f = wwait.get(e.data.id); if (f) { wwait.delete(e.data.id); f(e.data); } };
    return worker;
  }
  const wcall = msg => new Promise(res => { const id = ++wseq; wwait.set(id, res); ensureWorker().postMessage({ ...msg, id }); });
  const terrainMat = new THREE.MeshStandardMaterial({ vertexColors: true, map: grainTex, roughness: .95, metalness: 0 });
  terrainMat.userData.comicWorld = true;
  const idxCache = {};
  function gridIndex(segs) { if (idxCache[segs]) return idxCache[segs]; const n = segs + 1, a = new Uint32Array(segs * segs * 6); let k = 0;
    for (let j = 0; j < segs; j++) for (let i = 0; i < segs; i++) { const v = j * n + i; a.set([v, v + n, v + 1, v + 1, v + n, v + n + 1], k); k += 6; } return idxCache[segs] = new THREE.BufferAttribute(a, 1); }
  let pending = 0;
  function chunkSegs(cx, cz) { const x = (cx + .5) * CH, z = (cz + .5) * CH; for (const id in REGIONS) { const R = REGIONS[id]; if (Math.abs(R.x - x) < CH * .5 + 60 && Math.abs(R.z - z) < CH * .5 + 60) return quality === 'low' ? 80 : 128; } return quality === 'low' ? 44 : 64; }
  function requestChunk(cx, cz) {
    const key = cx + ',' + cz; if (chunks.has(key)) return; const c = { cx, cz, key, state: 'wait', veg: [], cols: [] }; chunks.set(key, c); pending++;
    const segs = chunkSegs(cx, cz);
    wcall({ type: 'chunk', cx, cz, size: CH, segs }).then(d => { pending--; if (!chunks.has(key)) return; if (d.error) { console.warn(d.error); return; } buildChunk(c, d, segs); });
  }
  function buildChunk(c, d, segs) {
    const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(d.pos, 3)); g.setAttribute('normal', new THREE.BufferAttribute(d.nor, 3));
    g.setAttribute('color', new THREE.BufferAttribute(d.col, 3));
    const n = segs + 1, uv = new Float32Array(n * n * 2); for (let k = 0; k < n * n; k++) { uv[k * 2] = (d.pos[k * 3] + c.cx * CH) / 3; uv[k * 2 + 1] = (d.pos[k * 3 + 2] + c.cz * CH) / 3; }
    g.setAttribute('uv', new THREE.BufferAttribute(uv, 2)); g.setIndex(gridIndex(segs)); g.computeBoundingSphere();
    const m = new THREE.Mesh(g, terrainMat); m.position.set(c.cx * CH, 0, c.cz * CH); m.receiveShadow = true; m.name = 'terrain';
    terrainRoot.add(m); c.mesh = m; c.data = d; c.segs = segs; c.state = 'ready';
    vegetate(c);
  }
  function dropChunk(c) {
    if (c.mesh) { terrainRoot.remove(c.mesh); c.mesh.geometry.dispose(); }
    for (const v of c.veg) { v.parent?.remove(v); v.dispose?.(); }
    for (const col of c.cols) removeCollider(col);
    chunks.delete(c.key);
  }
  function streamChunks(px, pz, force) {
    const R = viewFar + CH * .75, i0 = Math.floor((px - R) / CH), i1 = Math.floor((px + R) / CH), j0 = Math.floor((pz - R) / CH), j1 = Math.floor((pz + R) / CH);
    const want = [];
    for (let i = i0; i <= i1; i++) for (let j = j0; j <= j1; j++) { const cxm = (i + .5) * CH, czm = (j + .5) * CH; if (Math.abs(cxm) > WORLD / 2 + CH || Math.abs(czm) > WORLD / 2 + CH) continue;
      const d = Math.hypot(cxm - px, czm - pz); if (d < R) want.push([d, i, j]); }
    want.sort((a, b) => a[0] - b[0]);
    let started = 0; for (const [, i, j] of want) { if (!chunks.has(i + ',' + j)) { if (pending < 3 || force) { requestChunk(i, j); started++; } } }
    for (const c of chunks.values()) { const d = Math.hypot((c.cx + .5) * CH - px, (c.cz + .5) * CH - pz); if (d > R + CH) dropChunk(c); else if (c.vegGroup) { c.vegGroup.visible = d < vegR + CH * .7; lodChunk(c, { x: px, z: pz }); } }
    for (const L of townLods) { const near = Math.hypot(L.x - px, L.z - pz) < lodR() + 50; for (const m of L.full) m.visible = near; for (const m of L.lod) m.visible = !near; }
  }
  /* level of detail: full trees near you, simplified ones further away (distance to the chunk's nearest edge) */
  const lodR = () => quality === 'high' ? 70 : quality === 'medium' ? 45 : 30;
  function lodChunk(c, p) { if (!c.fullIMs || !p) return; const R = lodR(), ox = c.cx * CH, oz = c.cz * CH;
    for (const m of c.fullIMs) { const b = m.boundingSphere; m.visible = Math.hypot(b.center.x + ox - p.x, b.center.z + oz - p.z) - b.radius * .6 < R; }
    for (const m of c.lodIMs) { const b = m.boundingSphere; m.visible = Math.hypot(b.center.x + ox - p.x, b.center.z + oz - p.z) - b.radius * .6 >= R; } }
  const townLods = [];
  /* vegetation per chunk, from the worker's per-vertex data (biome, grass, road, town, mountain) */
  function vegetate(c) {
    const subsets = {}, Rs = rng((c.cx * 131 + c.cz * 977) >>> 0), sub = (l, n) => { const a = l.filter(has); for (let i = a.length - 1; i > 0; i--) { const j = (Rs() * (i + 1)) | 0; [a[i], a[j]] = [a[j], a[i]]; } return a.slice(0, n); };
    const pickFlora = bio => { if (subsets[bio]) return subsets[bio]; const F = FLORA[bio]; if (!F) return null;
      return subsets[bio] = { ...F, trees: sub(F.trees, 2), rocks: sub(F.rocks, 1), bush: sub(F.bush, 1), flowers: sub(F.flowers, 2), tall: F.tall ? sub(F.tall, 1) : null }; };
    const d = c.data, n = c.segs + 1, step = CH / c.segs, R = rng((c.cx * 7349 + c.cz * 9151) >>> 0), grp = new THREE.Group(); grp.position.set(c.cx * CH, 0, c.cz * CH);
    const lists = {}, tints = {}, add = (name, x, y, z, s, tint, block, shadow) => { if (!has(name)) return; const k = name + (tint ? JSON.stringify(tint) : '') + (shadow ? 's' : ''); (lists[k] ||= { name, tint, shadow, list: [] }).list.push([x, y, z, R() * 6.28, s]);
      if (block) c.cols.push(addCollider({ x: x + c.cx * CH, z: z + c.cz * CH, r: block * s })); };
    const at = (x, z) => { const i = Math.min(n - 1, Math.max(0, Math.round(x / step))), j = Math.min(n - 1, Math.max(0, Math.round(z / step))); return j * n + i; };
    const tries = quality === 'low' ? 220 : quality === 'medium' ? 360 : 560;
    for (let k = 0; k < tries; k++) {
      const x = R() * CH, z = R() * CH, v = at(x, z), y = d.pos[v * 3 + 1];
      if (y < .45 || d.road[v] < 5.5 || d.town[v] > .15) continue;
      const bio = BIOME_LIST[d.bio[v]], F = pickFlora(bio); if (!F) continue;
      const wx = x + c.cx * CH, wz = z + c.cz * CH, forest = fbm(wx * .018 + 5, wz * .018), dense = forest > F.forest, r = R(), mnt = d.mnt[v];
      if (r < (dense ? .32 : .04) * (1 - mnt * .5) && F.trees.length) add(F.trees[(R() * F.trees.length) | 0], x, y - .05, z, .75 + R() * .5, F.tint, .55, quality === 'high');
      else if (r < .5 && F.rocks.length && (mnt > .2 || R() < .25)) add(F.rocks[(R() * F.rocks.length) | 0], x, y - .1, z, .4 + R() * (mnt > .2 ? 1.6 : .7), F.tint && F.tint.all ? F.tint : null, .7, quality === 'high');
      else if (r < .64 && F.bush.length && d.grass[v] > .3) add(F.bush[(R() * F.bush.length) | 0], x, y - .05, z, .7 + R() * .6, null, 0, false);
      else if (r < .82 && F.flowers.length && d.grass[v] > .5) add(F.flowers[(R() * F.flowers.length) | 0], x, y - .03, z, .7 + R() * .5, null, 0, false);
      else if (F.tall && d.grass[v] > .6 && r < .9) add(F.tall[(R() * F.tall.length) | 0], x, y - .05, z, .9 + R() * .6, F.tint && F.tint.all ? F.tint : null, 0, false);
    }
    c.fullIMs = []; c.lodIMs = [];
    for (const L of Object.values(lists)) {
      const lod = has(L.name + '_LOD') ? L.name + '_LOD' : null;
      for (const im of instances(grp, L.name, L.list, { shadow: L.shadow, tint: L.tint, cell: lod ? (quality === 'low' ? 999 : 64) : 999 })) { c.veg.push(im); if (lod) c.fullIMs.push(im); }
      if (lod) for (const im of instances(grp, lod, L.list, { shadow: false, tint: L.tint, cell: quality === 'low' ? 999 : 64 })) { c.veg.push(im); c.lodIMs.push(im); }
    }
    if (comic) applyComic(grp);
    terrainRoot.add(grp); c.veg.push(grp); c.vegGroup = grp; lodChunk(c, player?.group.position);
  }

  /* ================================================================== island-wide textures: height+grass (grass blades, water), minimap */
  let gridTex = null, grassMesh = null, water = null, sky = null, mapCanvas = null;
  async function buildGrid() {
    const n = quality === 'low' ? 448 : 640, d = await wcall({ type: 'grid', n });
    gridTex = new THREE.DataTexture(d.grid, d.n, d.n, THREE.RGFormat, THREE.FloatType); gridTex.magFilter = gridTex.minFilter = THREE.LinearFilter; gridTex.needsUpdate = true;
    const m = d.m, cv = document.createElement('canvas'); cv.width = cv.height = m; cv.getContext('2d').putImageData(new ImageData(d.map, m, m), 0, 0); mapCanvas = cv;
  }
  function buildGlobals() {
    sky = makeSky(AREAS.harbor); scene.add(sky);
    water = makeWater({ ...AREAS.harbor, water: '#1d6aab', shallow: '#38c6c4', fog: AREAS.harbor.fog }, H, { hm: gridTex, span: WORLD, size: viewFar * 2.6 + 200 }); scene.add(water);
    grassMesh = grassFieldImpl(H, null, { n: 78000, r: 60, base: '#3b7a34', tip: '#a8dc6a', hgt: .42, w: .085, seed: 5, hmask: gridTex, span: WORLD }); scene.add(grassMesh);
    envTex?.dispose(); envTex = envFromSky(renderer, { ...AREAS.harbor, ground: ['#79a957', '#5a8d45', '#98b868'] }); scene.environment = comic ? null : envTex; scene.environmentIntensity = .7;
  }
  /* ================================================================== landmarks: the wild between towns is not empty
     Camps, old ruins, flower groves, lookout towers and treasure chests (one-time rewards) spread over the whole island. */
  const landmarks = [];
  function buildLandmarks() {
    const R = rng(2024), M = WORLD / 2 - 40, made = [];
    const okSpot = (x, z) => { const y = H(x, z); if (y < 1.2) return false; const nr = nearestRegion(x, z); if (nr.d < 85) return false; if (roadDist(x, z) < 7) return false;
      const sl = Math.abs(H(x + 3, z) - H(x - 3, z)) + Math.abs(H(x, z + 3) - H(x, z - 3)); if (sl > 2.6) return false; return !made.some(([mx, mz]) => Math.hypot(mx - x, mz - z) < 55); };
    const TYPES = ['camp', 'ruin', 'grove', 'chest', 'grove', 'chest', 'lookout', 'ruin', 'camp', 'chest'];
    for (let t = 0; t < 2600 && made.length < 70; t++) {
      const x = (R() * 2 - 1) * M, z = (R() * 2 - 1) * M; if (!okSpot(x, z)) continue;
      const type = TYPES[made.length % TYPES.length], y = H(x, z), g = new THREE.Group(); g.position.set(x, y, z); worldRoot.add(g);
      const P_ = (name, dx, dz, o = {}) => { if (!has(name)) return null; const yy = H(x + dx, z + dz) - y + (o.yOff || 0); const m = place(g, name, dx, yy, dz, o); if (o.block) addCollider({ x: x + dx, z: z + dz, r: o.block }); return m; };
      const lm = { type, x, z, g, id: 'lm' + made.length };
      if (type === 'camp') {
        const tent = new THREE.Mesh(new THREE.ConeGeometry(1.6, 2.2, 4, 1, true), new THREE.MeshStandardMaterial({ color: ['#d8483c', '#3d8fd6', '#e8903c', '#57c28f'][made.length % 4], roughness: .8, side: THREE.DoubleSide }));
        tent.position.set(0, 1.1, -2.2); tent.rotation.y = Math.PI / 4; tent.castShadow = true; g.add(tent); addCollider({ x, z: z - 2.2, r: 1.4 });
        P_('FL_Log', 1.6, .6, { rot: 1.2, scale: .7 }); P_('FL_Stump', -1.5, .9, { scale: .8 });
        const fire = new THREE.Group(); for (let i = 0; i < 4; i++) { const l = new THREE.Mesh(new THREE.CylinderGeometry(.07, .07, .8, 6), new THREE.MeshStandardMaterial({ color: '#5a3a22' })); l.rotation.set(Math.PI / 2, 0, i * Math.PI / 4); l.position.y = .1; fire.add(l); }
        const fl = new THREE.Mesh(new THREE.ConeGeometry(.28, .7, 7), new THREE.MeshBasicMaterial({ color: new THREE.Color('#ffb347').multiplyScalar(2.2), transparent: true, opacity: .9 })); fl.position.y = .45; fire.add(fl); g.add(fire);
        animated.push(k => { if (g.visible) { fl.scale.set(1 + Math.sin(k * 13 + x) * .12, 1 + Math.sin(k * 9.3 + z) * .2, 1 + Math.cos(k * 11) * .12); } });
      } else if (type === 'ruin') {
        const n = 5 + (R() * 3 | 0);
        for (let i = 0; i < n; i++) { const a = i / n * Math.PI * 2, r = 5 + R() * 1.5; const c = P_('Column_Round', Math.cos(a) * r, Math.sin(a) * r, { scale: .9 + R() * .5, rot: R() * 6, block: .6 });
          if (c && R() < .45) { c.rotation.z = (R() - .5) * 1.4; c.position.y -= .4; } }
        P_('FL_Rock_B', 0, 0, { scale: 1.1, rot: R() * 6, block: 1.2 }); P_('FL_Rock_A', 2.4, -1.6, { scale: .8 }); P_('FL_Fern', -2, 2, {}); P_('FL_Fern', 2.5, 2.2, {});
      } else if (type === 'grove') {
        const big = P_(['FL_Tree_A', 'FL_Tree_B', 'FL_Birch'][made.length % 3], 0, 0, { scale: 1.5 + R() * .4, rot: R() * 6, block: .8 });
        for (let i = 0; i < 22; i++) { const a = R() * Math.PI * 2, r = 2.5 + R() * 7; P_(['FL_Flowers_Y', 'FL_Flowers_W', 'FL_Flowers_P', 'FL_Flowers_B'][(i + made.length) % 4], Math.cos(a) * r, Math.sin(a) * r, { scale: .9 + R() * .6, rot: R() * 6, shadow: false }); }
        for (let i = 0; i < 4; i++) { const a = R() * Math.PI * 2, r = 5 + R() * 4; P_(i % 2 ? 'FL_Bush_Flower' : 'FL_Bush_Berry', Math.cos(a) * r, Math.sin(a) * r, { scale: .8 + R() * .4, rot: R() * 6 }); }
      } else if (type === 'lookout') {
        P_('MV_Lookout', 0, 0, { scale: .9, rot: R() * 6, block: 2.2 });
        lm.chest = true;
      }
      if (type === 'chest' || lm.chest) {
        const cx = type === 'chest' ? 0 : 2.6, cz = type === 'chest' ? 0 : 2.6;
        const ch = P_('Prop_Chest_Closed', cx, cz, { scale: 1.3, rot: R() * 6 });
        if (type === 'chest') { P_('FL_Rock_A', 1.6, -1.1, { scale: .7 }); P_('FL_Bush_A', -1.6, -.8, { scale: .8 }); }
        const opened = !!P.ensure().world.found[lm.id];
        const glow = new THREE.Mesh(new THREE.CylinderGeometry(.5, .9, 3.2, 12, 1, true), new THREE.MeshBasicMaterial({ color: new THREE.Color('#ffd257').multiplyScalar(1.6), transparent: true, opacity: .18, depthWrite: false, side: THREE.DoubleSide, blending: THREE.AdditiveBlending }));
        glow.position.set(cx, 1.6, cz); glow.visible = !opened; g.add(glow);
        allItems.push({ kind: 'chest', id: lm.id, x: x + cx, z: z + cz, r: 2.2, g, glow, chest: ch, tier: QS.tierAt(x, z) });
      }
      g.traverse(o => { if (o.isMesh) { o.castShadow = o.castShadow !== false; o.receiveShadow = true; } });
      landmarks.push(lm); made.push([x, z]);
    }
    decorLog.push(['landmarks', made.length]);
  }
  function openChest(it) {
    const s = P.ensure(); if (s.world.found[it.id]) { hooks.toast?.('Empty — you already opened this chest.'); return; }
    s.world.found[it.id] = Date.now(); faceTo(player, it.x, it.z); player.play('Interact', .2, { once: true }); hooks.sfx?.('sparkle');
    const coins = Math.round(60 + it.tier * 45 + Math.random() * 40), xp = Math.round(25 + it.tier * 12);
    C.addCoins(coins); hooks.xp?.(xp); RK.add(RK.RP.chest, 'Treasure'); C.save(); it.glow.visible = false; if (it.chest) it.chest.rotation.x = -.25;
    hooks.toast?.(`Treasure chest! <span class="gold">+${coins} coins · +${xp} XP</span>`);
  }

  /* gate barricades on the routes (shown while closed) */
  const gateObjs = [];
  function buildGates() {
    for (const G of GATES) {
      continue; // the world is fully open: no barricades
      const r = ROUTES.find(q => q.id === G.route), p = routePoint(r, G.at), g = new THREE.Group(), rot = Math.atan2(p.dx, p.dz);
      const wood = new THREE.MeshStandardMaterial({ color: '#7a5634', roughness: .9 }), stripe = new THREE.MeshStandardMaterial({ color: '#f2c230', roughness: .6 });
      for (let k = -3; k <= 3; k++) { const post = new THREE.Mesh(new THREE.CylinderGeometry(.12, .14, 1.6, 8), wood); post.position.set(k * 1.6, .8, 0); g.add(post); }
      for (const y of [.55, 1.15]) { const bar = new THREE.Mesh(new THREE.BoxGeometry(10, .22, .12), y > 1 ? stripe : wood); bar.position.y = y; g.add(bar); }
      const tag = label('ROAD CLOSED', r.name, '#ff9a6a'); tag.position.y = 2.4; tag.scale.multiplyScalar(1.2); g.add(tag);
      g.position.set(p.x, H(p.x, p.z), p.z); g.rotation.y = rot + Math.PI / 2; g.traverse(o => { if (o.isMesh) o.castShadow = true; }); worldRoot.add(g);
      gateObjs.push({ G, g });
    }
  }
  function refreshGates() { for (const o of gateObjs) o.g.visible = !QS.flag(o.G.flag); }

  /* ================================================================== NPCs from the story roster + route trainers */
  const beacon = (() => {
    const g = new THREE.Group();
    const beam = new THREE.Mesh(new THREE.CylinderGeometry(.7, .7, 60, 16, 1, true), new THREE.MeshBasicMaterial({ color: '#ffd257', transparent: true, opacity: .16, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide, fog: false }));
    beam.position.y = 30; const ring = new THREE.Mesh(new THREE.RingGeometry(1.4, 1.8, 40), new THREE.MeshBasicMaterial({ color: new THREE.Color('#ffd257').multiplyScalar(2), transparent: true, opacity: .8, depthWrite: false, side: THREE.DoubleSide, fog: false }));
    ring.rotation.x = -Math.PI / 2; ring.position.y = .08; const gem = new THREE.Mesh(new THREE.OctahedronGeometry(.45), new THREE.MeshBasicMaterial({ color: new THREE.Color('#ffd257').multiplyScalar(2.2), fog: false })); gem.position.y = 4.2;
    g.add(beam, ring, gem); g.visible = false; scene.add(g); g.userData = { beam, ring, gem }; return g;
  })();
  function spawnNPC(id, pos, face, extra = {}) {
    const look = npcLook(id) || villagerLook(rng(id.length * 31 + (pos.x | 0))); const ch = makeRigged(look, id === 'sable' ? { hat: 'model' } : {}); if (!ch) return null;
    ch.group.position.set(pos.x, H(pos.x, pos.z), pos.z); ch.group.rotation.y = face || 0; ch.group.traverse(o => { if (o.isMesh && !o.material.transparent) o.castShadow = true; });
    const isTrainer = !!extra.trainer, tag = label(extra.name || npcName(id), extra.shop ? 'Shop' : isTrainer ? (QS.beaten(extra.key || id) ? 'Trainer · beaten' : 'Trainer') : (P.CAST[id]?.role || ''));
    tag.position.y = 2.75; ch.group.add(tag);
    const mk = new THREE.Mesh(new THREE.OctahedronGeometry(.16), new THREE.MeshBasicMaterial({ color: new THREE.Color(isTrainer ? '#ffd257' : '#5cf2d6').multiplyScalar(2), fog: false })); mk.position.y = 3.25; ch.group.add(mk);
    if (id === 'glyph') { ch.group.visible = false; }
    actorsRoot.add(ch.group);
    const col = addCollider({ x: pos.x, z: pos.z, r: .55 });
    const npc = { id, key: extra.key || id, ch, x: pos.x, z: pos.z, r: 2.6, face: face || 0, tag, mk, col, ...extra }; npcs.push(npc); return npc;
  }
  function refreshNPCs() {
    for (const n of npcs.splice(0)) { actorsRoot.remove(n.ch.group); removeCollider(n.col); }
    for (const r of QS.rosterNow()) spawnNPC(r.id, r.pos, r.face, { trainer: r.trainer, shop: r.shop, mirror: r.mirror });
    for (const rt of QS.ROUTE_TRAINERS) { P.CAST[rt.id] ||= { name: rt.name, role: 'Route trainer', look: villagerLook(rng(rt.id.length * 97 + rt.name.length)) }; spawnNPC(rt.id, rt.pos, 0, { trainer: rt.trainer, name: rt.name, routeTrainer: rt }); }
    if (QS.Q().ch >= 9) { const g = npcs.find(n => n.id === 'glyph'); if (g) { const g0 = new THREE.Group(); g0.position.copy(g.ch.group.position); actorsRoot.add(g0); glyphEntity(g0); g.glyphFx = g0; } }
    refreshGates();
  }

  /* ================================================================== wild Echoes: spawn in tall grass around you */
  let spawnT = 0;
  function gridAt(x, z) { if (!gridTex) return { y: H(x, z), g: 0 }; const n = gridTex.image.width, i = Math.round((x / WORLD + .5) * (n - 1)), j = Math.round((z / WORLD + .5) * (n - 1));
    if (i < 0 || j < 0 || i >= n || j >= n) return { y: -5, g: 0 }; const k = (j * n + i) * 2; return { y: gridTex.image.data[k], g: gridTex.image.data[k + 1] }; }
  function spawnWilds(dt, pp) {
    spawnT -= dt; if (spawnT > 0 || mode !== 'explore') return; spawnT = 1.2;
    for (let i = wilds.length - 1; i >= 0; i--) { const w = wilds[i]; if (Math.hypot(w.x - pp.x, w.z - pp.z) > 80 || w.dead) { actorsRoot.remove(w.g); w.shell.dispose?.(); wilds.splice(i, 1); } }
    const max = quality === 'low' ? 4 : quality === 'medium' ? 6 : 8; if (wilds.length >= max) return;
    const a = cam.yaw + Math.PI + (Math.random() - .5) * 2.2, r = 22 + Math.random() * 30, x = pp.x + Math.sin(a) * r, z = pp.z + Math.cos(a) * r, g = gridAt(x, z);
    if (g.g < .45 || g.y < .4 || QS.blockedAt(x, z)) return;
    const nr = nearestRegion(x, z); if (nr.d < 46) return; // not inside towns
    const Aa = AREAS[nr.id], night = isNight(), qst = QS.stepNow();
    // a typed capture objective nearby: most spawns match it, so the story never stalls on bad luck
    const want = qst?.kind === 'capture' && qst.type && qst.pos && Math.hypot(pp.x - qst.pos.x, pp.z - qst.pos.z) < (qst.r || 40) + 40 && Math.random() < .65 ? [].concat(qst.type) : null;
    const types = want || (night && Math.random() < .35 ? ['Darkness', 'Psychic'] : Aa.echo), type = types[(Math.random() * types.length) | 0];
    const pick = hooks.echoCard?.(type, Math.random); if (!pick) return;
    const cp = makeCardPet({ i: pick.i, f: pick.f, n: pick.n, t: pick.t || type }, pick.img, { size: 1.25, echo: true }); cp.setEcho(.28);
    const ring = projector(TYPE_COL[type] || '#fff'); ring.scale.setScalar(.8); cp.group.add(ring);
    cp.group.position.set(x, H(x, z), z); cp.setFog(scene.fog); actorsRoot.add(cp.group);
    wilds.push({ g: cp.group, shell: cp, type, card: pick, ring, hx: x, hz: z, x, z, tx: x, tz: z, r: 2.2, wait: Math.random() * 3, mood: Math.random() < .5 ? 'shy' : 'bold', state: 'wander', vel: new THREE.Vector3() });
  }
  function updateWilds(dt, pp) {
    for (const e of wilds) {
      if (e.frozen) { e.shell.update(dt, 0, t, camera); continue; }
      const d = Math.hypot(pp.x - e.x, pp.z - e.z) || .01, running = player.vel.length() > 6; let speed = 0;
      if (d < 9) e.state = e.mood === 'shy' && (running || d < 3) ? 'flee' : e.mood === 'bold' && d > 2.6 ? 'approach' : 'watch';
      else if (e.state !== 'wander') { e.state = 'wander'; e.wait = 1; }
      if (e.state === 'wander') {
        e.wait -= dt; if (e.wait <= 0) { const a = Math.random() * 6.28, r = Math.random() * 7; e.tx = e.hx + Math.cos(a) * r; e.tz = e.hz + Math.sin(a) * r; e.wait = 3 + Math.random() * 4; }
        const dx = e.tx - e.x, dz = e.tz - e.z, dd = Math.hypot(dx, dz); if (dd > .3) { speed = 1.4; e.x += dx / dd * speed * dt; e.z += dz / dd * speed * dt; }
      } else if (e.state === 'flee') { const dx = e.x - pp.x, dz = e.z - pp.z; speed = 3.2; e.x += dx / d * speed * dt; e.z += dz / d * speed * dt; if (Math.hypot(e.x - e.hx, e.z - e.hz) > 14) { e.x -= dx / d * speed * dt; e.z -= dz / d * speed * dt; speed = 0; } }
      else if (e.state === 'approach') { const dx = pp.x - e.x, dz = pp.z - e.z; speed = 2; e.x += dx / d * speed * dt; e.z += dz / d * speed * dt; }
      if (H(e.x, e.z) < .2) { e.x = lerp(e.x, e.hx, .2); e.z = lerp(e.z, e.hz, .2); }
      const pos = { x: e.x, z: e.z }; collide(pos, .5); e.x = pos.x; e.z = pos.z;
      e.vel.set((e.x - e.g.position.x) / Math.max(dt, 1e-3), 0, (e.z - e.g.position.z) / Math.max(dt, 1e-3));
      e.g.position.set(e.x, H(e.x, e.z), e.z);
      if (d < 50) e.shell.update(dt, speed, t, camera, e.vel);
      e.ring.rotation.y = t * 1.2;
    }
  }

  /* ================================================================== lifecycle */
  async function build() {
    hooks.loading?.(true, 'Veyra');
    const s = P.ensure(), looks = [s.look, ...Object.values(P.CAST).map(c => c.look).filter(Boolean)];
    for (let i = 0; i < 10; i++) looks.push(villagerLook(rng(99 + i)));
    for (const a in ARCH) looks.push(archLook(a, rng(1)));
    try { await Promise.all([loadKits(), prepare(looks, []), buildGrid()]); } catch (e) { console.warn('[world] asset load', e); }
    buildGlobals();
    for (const id of Object.keys(REGIONS)) buildTown(id);
    buildGates();
    try { buildLandmarks(); } catch (e) { console.warn('[world] landmarks', e); }
    if (comic) applyComic(worldRoot);
    built = true;
  }
  async function enter(id, opts = {}) {
    if (!built) { if (!building) building = build(); await building; }
    const s = P.ensure(); s.world.v2 ||= Date.now();
    let x = opts.x, z = opts.z;
    if (id && id !== 'here' && REGIONS[id] && opts.travel) { const R = REGIONS[id]; x = R.x + (AREAS[id].spawn?.[0] || 0); z = R.z + (AREAS[id].spawn?.[1] || 20); }
    if (x == null || !s.world.pos?.v2) { const p = s.world.pos?.v2 ? s.world.pos : DEFAULT_SPAWN; x = x ?? p.x; z = z ?? p.z; }
    if (QS.blockedAt(x, z)) ({ x, z } = DEFAULT_SPAWN);
    if (!player) { player = makeRigged(s.look); scene.add(player.group); }
    player.group.position.set(x, H(x, z), z); player.vel = new THREE.Vector3(); cam.yaw = cam.tYaw = Math.atan2(x - REGIONS.harbor.x, z - REGIONS.harbor.z + 60) || Math.PI; player.group.rotation.y = cam.yaw + Math.PI; vy = 0;
    streamChunks(x, z, true);
    await new Promise(res => { const tick = () => { const c = chunks.get(Math.floor(x / CH) + ',' + Math.floor(z / CH)); if (c?.state === 'ready' || performance.now() - t0 > 15000) res(); else setTimeout(tick, 60); }; const t0 = performance.now(); tick(); });
    refreshNPCs(); spawnCompanions(); lastRegion = null; snap = true; near = null; hooks.prompt?.(null);
    s.world.pos = { v2: 1, x, z }; envCycle(0, true); hooks.loading?.(false);
    setTimeout(runStoryAuto, 400);
  }
  function refreshLook() { if (!player) return; prepare([P.ensure().look]).then(() => { const p = player.group.position.clone(), r = player.group.rotation.y; scene.remove(player.group); player = makeRigged(P.ensure().look); player.group.position.copy(p); player.group.rotation.y = r; player.vel = new THREE.Vector3(); scene.add(player.group); }); }

  /* ---------- region / route detection, visual blending, time of day, weather */
  let lastRegion = null, lastRoute = null, regT = 0;
  const BL = { top: new THREE.Color(), bot: new THREE.Color(), fog: new THREE.Color(), sunCol: new THREE.Color(), cloud: new THREE.Color(), fogNear: 90, fogFar: 300, sunI: 2.6, hemi: 1.3, clouds: .4, exposure: 1, sat: 1.1, nightW: 0, aurora: 0, bloom: .3 };
  const tc = new THREE.Color(), tc2 = new THREE.Color();
  function blendLooks(pp) {
    const w = regionWeights(pp.x, pp.z);
    BL.top.setRGB(0, 0, 0); BL.bot.setRGB(0, 0, 0); BL.fog.setRGB(0, 0, 0); BL.sunCol.setRGB(0, 0, 0); BL.cloud.setRGB(0, 0, 0);
    let fn = 0, ff = 0, si = 0, he = 0, cl = 0, ex = 0, sa = 0, nw = 0, au = 0, bl = 0;
    for (const id in w) { const k = w[id], a = AREAS[id]; if (k < .002) continue;
      BL.top.add(tc.set(a.sky[0]).multiplyScalar(k)); BL.bot.add(tc.set(a.sky[1]).multiplyScalar(k)); BL.fog.add(tc.set(a.fog[0]).multiplyScalar(k)); BL.sunCol.add(tc.set(a.sunColor).multiplyScalar(k)); BL.cloud.add(tc.set(a.cloud || '#fff').multiplyScalar(k));
      fn += a.fog[1] * k; ff += a.fog[2] * k; si += a.sunI * k; he += a.hemi * k; cl += a.clouds * k; ex += (a.exposure || 1) * k; sa += (a.sat || 1.1) * k; nw += (a.night ? 1 : 0) * k; au += (a.aurora ? 1 : 0) * k; bl += (a.bloom ?? .3) * k; }
    Object.assign(BL, { fogNear: fn, fogFar: ff, sunI: si, hemi: he, clouds: cl, exposure: ex, sat: sa, nightW: nw, aurora: au, bloom: bl });
    const nr = nearestRegion(pp.x, pp.z); A = AREAS[nr.id]; curRegion = nr.id; return nr;
  }
  let curRegion = 'harbor', fxP = null, fxId = null, rainP = null, weather = { state: 'clear', wk: 0, target: 0, timer: 30 };
  const NIGHT_TOP = col('#0a1030'), NIGHT_BOT = col('#23305a'), NIGHT_FOG = col('#1c2446'), DUSK = col('#ff9a5a'), MOON = col('#a8bcff');
  const sunDir = new THREE.Vector3(0, 1, 0); let dayK = 1;
  function isNight() { return dayK < .45; }
  function envCycle(dt, force) {
    if (!player || !sky) return; const pp = player.group.position, S = P.ensure().world;
    regT -= dt; if (regT <= 0 || force) { regT = .25; const nr = blendLooks(pp); detectPlace(pp, nr); }
    if (S.tod == null) S.tod = 10.5; S.tod = (S.tod + dt * 24 / 1200) % 24;
    const tod = S.tod, elev = Math.sin((tod - 6) / 12 * Math.PI), dayRaw = smooth(-.12, .28, elev), dusk = Math.exp(-Math.pow(elev / .2, 2));
    const day = dayRaw * (1 - BL.nightW); dayK = day;
    // weather (per region)
    weather.timer -= dt; if (weather.timer <= 0 || force && !env) { const st = WEATHER[curRegion] || WEATHER.harbor, pick = st[Math.floor(Math.random() * st.length)];
      weather.state = pick; weather.target = { clear: 0, cloudy: .45, rain: .8, storm: 1, fog: .6, snow: .7, dust: .8 }[pick] ?? 0; weather.timer = 150 + Math.random() * 180; }
    weather.wk += (weather.target - weather.wk) * Math.min(1, dt * .08 + (force ? 1 : 0)); const wk = weather.wk, wet = weather.state === 'rain' || weather.state === 'storm', foggy = weather.state === 'fog';
    // sun / moon
    const az = .9, e2 = Math.max(.14, Math.abs(elev)) * .85 + .08, sd = elev >= 0 ? 1 : -1;
    sunDir.set(Math.cos(az) * Math.cos(Math.asin(Math.min(.98, e2))) * sd, e2, Math.sin(az) * Math.cos(Math.asin(Math.min(.98, e2))) * sd).normalize();
    tc.copy(BL.sunCol).lerp(DUSK, dusk * .7 * (1 - BL.nightW)); sun.color.copy(MOON).lerp(tc, day);
    sun.intensity = BL.sunI * lerp(.62, 1, day) * (1 - wk * .38); hemi.intensity = BL.hemi * lerp(.9, 1, day) * (1 - wk * .2) + flash * 2.5;
    hemi.color.copy(tc.set('#ffffff').lerp(tc2.set('#aabcff'), 1 - day)); hemi.groundColor.set('#6a5f48').lerp(tc2.set('#2a2f48'), 1 - day);
    // sky + fog
    const su = sky.material.uniforms;
    su.top.value.copy(NIGHT_TOP).lerp(BL.top, day); tc.copy(BL.bot).lerp(DUSK, dusk * .4 * (1 - BL.nightW)); su.bot.value.copy(NIGHT_BOT).lerp(tc, day);
    tc2.copy(BL.fog).lerp(DUSK, dusk * .22); su.fogc.value.copy(NIGHT_FOG).lerp(tc2, day); su.night.value = 1 - day; su.sunCol.value.copy(sun.color); su.aurora.value = BL.aurora > .4 ? 1 : 0;
    su.sunDir.value.copy(sunDir); su.cloudAmt.value = lerp(BL.clouds, .97, wk); su.cloudCol.value.copy(BL.cloud).multiplyScalar(lerp(.45, 1, day));
    scene.fog ||= new THREE.Fog('#fff', 50, 300);
    tc.copy(su.fogc.value); if (wk > 0) tc.lerp(tc2.set('#8a8f99'), wk * .4); scene.fog.color.copy(tc);
    const fogFar = Math.min(BL.fogFar, viewFar), fogNear = Math.min(BL.fogNear, fogFar * .45);
    scene.fog.near = fogNear * lerp(1, .25, foggy ? wk : wk * .4); scene.fog.far = fogFar * lerp(1, .5, foggy ? wk : wk * .3);
    camera.far = viewFar + 60; camera.updateProjectionMatrix();
    renderer.toneMappingExposure = BL.exposure * lerp(1.25, 1, day);
    if (rainP) rainP.userData.amt.value = wet ? wk : 0;
    if (fxP) { const k = fxP.userData.kind; if (k === 'snow' || k === 'dust') fxP.userData.amt.value = .3 + .7 * wk; }
    for (const L of lampGlows) L.m.color.copy(L.base).multiplyScalar(lerp(3.6, 1.1, day));
    if (wet && weather.state === 'storm' && Math.random() < dt * .04 * wk) { flash = 1; hooks.sfx?.('zap'); }
    if (water) { const wu = water.userData.u; wu.fogColor.value.copy(scene.fog.color); wu.fogNear.value = scene.fog.near; wu.fogFar.value = scene.fog.far; wu.sky.value.copy(su.bot.value); wu.sunCol.value.copy(sun.color); wu.sunDir.value.copy(sunDir); }
    if (grassMesh) { const gu = grassMesh.userData.grass; if (force || frameN % 30 === 0) { const w = regionWeights(pp.x, pp.z); const b = new THREE.Color(0, 0, 0), tp = new THREE.Color(0, 0, 0);
      for (const id in w) { const B = BIOMES[REGIONS[id].biome]; b.add(tc.set(B.grass[0]).multiplyScalar(w[id])); tp.add(tc.set(B.grass[1]).multiplyScalar(w[id])); } gu.cBase.value.copy(b); gu.cTip.value.copy(tp); } }
    env = { look: { ...A, sat: BL.sat, vig: .22, tint: [1, 1, 1], bloom: BL.bloom, shTint: '#4a4a8a', hiTint: '#ffe6c8', split: .12, sunI: BL.sunI, night: BL.nightW > .5, sunColor: '#' + BL.sunCol.getHexString() } };
    if (post && (force || frameN % 60 === 0)) post.look(env.look);
    if (comic && post?.U) { const toon = style !== 'comic'; CU.cDark.value = (toon ? .62 : .42) + (1 - day) * .06; post.U.exposure.value = (toon ? 1.02 : .95) * BL.exposure * lerp(1.15, 1, day); }
    const S2 = hooks.clock && (envCycle.c = (envCycle.c || 0) - dt) <= 0; if (S2 || force) { envCycle.c = 1; hooks.clock?.({ tod, state: weather.state, wk, night: day < .5 }); }
  }
  function detectPlace(pp, nr) {
    const q = QS.Q();
    if (nr.d < 70) { if (!q.visited[nr.id]) { q.visited[nr.id] = Date.now(); } if (lastRegion !== nr.id) { lastRegion = nr.id; lastRoute = null; const a = AREAS[nr.id]; hooks.onArea?.({ name: a.name, sub: a.sub, echo: a.echo, id: nr.id, danger: QS.dangerAt(pp.x, pp.z) }); swapFx(nr.id); } }
    else { let best = null, bd = 16; for (const r of ROUTES) { const d = segDist(pp.x, pp.z, r.pts); if (d < bd) { bd = d; best = r; } }
      if (best && lastRoute !== best.id) { lastRoute = best.id; lastRegion = null; hooks.onArea?.({ name: best.name, sub: best.sub, echo: A.echo, route: true, id: best.id, danger: QS.dangerAt(pp.x, pp.z) }); swapFx(nearestRegion(pp.x, pp.z).id); } }
  }
  function swapFx(id) {
    if (fxId === id) return; fxId = id;
    if (fxP) { scene.remove(fxP); fxP.geometry.dispose(); fxP = null; }
    const a = AREAS[id]; if (a.fx) { fxP = particles(a.fx[0], a.fx[1]); scene.add(fxP); }
    if (!rainP) { rainP = particles('rain', { color: '#c6d2e0', n: 700, size: 10, hmax: 18 }); rainP.userData.amt.value = 0; scene.add(rainP); }
  }

  /* ---------- companion */
  function spawnCompanions() {
    if (pet) { scene.remove(pet.group); pet.dispose?.(); pet = null; }
    if (!player) return; const info = hooks.partner?.(); if (!info?.img) return;
    const pp = player.group.position;
    pet = makeCardPet({ i: info.i, f: info.f, n: info.name, t: info.type }, info.img, { size: 1.3 });
    pet.group.position.set(pp.x + 1.5, H(pp.x + 1.5, pp.z), pp.z); pet.vel = new THREE.Vector3(); pet.setFog(scene.fog); scene.add(pet.group);
    const nm = label(info.name, 'Partner · ' + info.type, TYPE_COL[info.type] || '#5cf2d6'); nm.scale.multiplyScalar(.5); nm.position.y = 2.1; pet.group.add(nm); pet.nm = nm;
  }

  /* ---------- input */
  const down = e => {
    if (!running || paused || mode !== 'explore' || e.target.closest?.('input,textarea,select')) return; keys[e.code] = true;
    if (['KeyE', 'Enter'].includes(e.code) && near && !busy) { e.preventDefault(); interact(near); }
    if (e.code === 'Space' && onGround && !busy) { e.preventDefault(); vy = 6.2; onGround = false; }
    if ((e.code === 'KeyQ' || e.code === 'ControlLeft') && rollT <= 0 && !busy && player) { rollT = .7; player.play('Roll', .1, { once: true, speed: 1.4 }); }
    if (e.code === 'KeyM' || e.code === 'Tab') { e.preventDefault(); hooks.travel?.(); }
  };
  const up = e => { keys[e.code] = false; };
  let drag = null; const stick = new THREE.Vector2(); let touchRun = false; const touches = new Map(); let pinch = 0;
  canvas.addEventListener('pointerdown', e => { touches.set(e.pointerId, { x: e.clientX, y: e.clientY }); if (touches.size === 2) { const [a, b] = [...touches.values()]; pinch = Math.hypot(a.x - b.x, a.y - b.y); drag = null; return; } drag = { x: e.clientX, y: e.clientY, yaw: cam.tYaw, pitch: cam.pitch, moved: false, btn: e.button }; canvas.setPointerCapture(e.pointerId); });
  canvas.addEventListener('pointermove', e => { if (touches.has(e.pointerId)) touches.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (touches.size === 2 && pinch) { const [a, b] = [...touches.values()], d = Math.hypot(a.x - b.x, a.y - b.y); cam.tDist = clamp(cam.tDist - (d - pinch) * .03, 2.6, 14); pinch = d; return; }
    if (!drag) return; const dx = e.clientX - drag.x, dy = e.clientY - drag.y, sens = hooks.sensitivity?.() || 1; if (Math.abs(dx) + Math.abs(dy) > 4) { drag.moved = true; cam.idle = 0; } cam.tYaw = drag.yaw - dx * .006 * sens; cam.pitch = clamp(drag.pitch + dy * .004 * sens * (hooks.invertY?.() ? -1 : 1), .08, 1.15); });
  canvas.addEventListener('pointerup', e => { touches.delete(e.pointerId); if (touches.size < 2) pinch = 0; if (drag && !drag.moved && drag.btn === 0) clickMove(e); drag = null; });
  canvas.addEventListener('pointercancel', e => { touches.delete(e.pointerId); pinch = 0; drag = null; });
  canvas.addEventListener('wheel', e => { cam.tDist = clamp(cam.tDist + Math.sign(e.deltaY) * .8, 2.6, 14); }, { passive: true });
  canvas.addEventListener('contextmenu', e => e.preventDefault());
  let target = null; const ray = new THREE.Raycaster(), ndc = new THREE.Vector2();
  function clickMove(e) {
    if (paused || mode !== 'explore') return; const r = canvas.getBoundingClientRect(); ndc.set((e.clientX - r.left) / r.width * 2 - 1, -(e.clientY - r.top) / r.height * 2 + 1); ray.setFromCamera(ndc, camera);
    const pp = player.group.position, near2 = terrainRoot.children.filter(o => o.name === 'terrain' && o.position.distanceTo(pp) < CH * 1.6);
    const hits = ray.intersectObjects(near2, false);
    if (hits[0]) { target = hits[0].point; if (near && hits[0].point.distanceTo(new THREE.Vector3(near.x, hits[0].point.y, near.z)) < 2.5) interact(near); }
  }

  /* ---------- interaction */
  async function interact(n) {
    busy = true; for (const k of ['KeyW', 'KeyA', 'KeyS', 'KeyD', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight']) keys[k] = false; target = null;
    try {
      if (n.kind === 'npc') await talkTo(n.npc);
      else if (n.kind === 'villager') { faceTo(player, n.v.x, n.v.z); faceTo(n.v.ch, player.group.position.x, player.group.position.z); n.v.ch.play('Wave', .2, { once: true }); if (!n.v.job) n.v.wait = 5; await hooks.talk?.([[n.v.name || 'Villager', n.v.line]]); }
      else if (n.kind === 'find') {
        const s = P.ensure(); if (s.world.found[n.id]) { hooks.toast?.(n.item.kind === 'pylon' ? 'This pylon is already stable.' : 'You already recorded this one.'); return; }
        P.track('glyph', { id: n.id }); hooks.sfx?.('sparkle'); faceTo(player, n.x, n.z); player.play('Interact', .2, { once: true });
        if (n.item.g.userData.beam) n.item.g.remove(n.item.g.userData.beam);
        const msg = { glyph: 'Glyph stone recorded — the script shimmers and goes still.', glass: 'Glass silhouette recorded — it matches a Pokémon from a 30-year-old transfer log.', pylon: 'Relay pylon stabilised — the storm around it quietens.' }[n.item.kind];
        hooks.toast?.(msg + ` <span class="gold">+40 XP</span>`); hooks.xp?.(40); RK.add(RK.RP.find, 'Discovery'); storyEvent('find', { id: n.id });
      } else if (n.kind === 'wild') await wildBattle(n.w);
      else if (n.kind === 'travel') hooks.travel?.();
      else if (n.kind === 'chest') openChest(n.item);
    } finally { busy = false; }
  }
  async function talkTo(np) {
    const id = np.id; faceTo(player, np.x, np.z); faceTo(np.ch, player.group.position.x, player.group.position.z);
    np.ch.play('Wave', .2, { once: true }); player.play('Interact', .2, { once: true });
    const st = QS.stepNow(), isStoryBattle = st?.kind === 'battle' && st.npc === id, isStoryTalk = st?.kind === 'talk' && st.npc === id;
    let lines = np.routeTrainer ? [[id, np.routeTrainer.line]] : QS.npcLines(id);
    if (np.routeTrainer && QS.beaten(np.key)) lines = [[id, 'Good battle earlier! The next town is further along the road.']];
    if (lines.length) await cineTalk(lines);
    if (isStoryTalk) { P.track('talk', { id }); storyEvent('talk', { id }); }
    if (np.shop) { hooks.go?.('#shop'); return; }
    const canFight = np.trainer && (isStoryBattle || (np.routeTrainer && !QS.beaten(np.key)) || (!np.routeTrainer && QS.beaten(np.key)));
    if (np.mirror && isStoryBattle) { await trainerBattle(np, { mirror: true }); return; }
    if (canFight && (isStoryBattle || await hooks.confirm?.(QS.beaten(np.key) ? `Rematch ${npcName(id)}?` : `Battle ${np.name || npcName(id)}?`, 'Battle', 'Later'))) await trainerBattle(np);
  }
  function faceTo(a, x, z) { if (!a) return; const p = a.group.position; a.group.rotation.y = Math.atan2(x - p.x, z - p.z); }
  function savePos() { if (!player) return; const p = player.group.position; P.ensure().world.pos = { v2: 1, x: p.x, z: p.z }; }

  /* ---------- cinematic dialogue (Genshin-style): letterbox, the camera cuts between the people who speak */
  const cv1 = new THREE.Vector3(), cv2 = new THREE.Vector3(), cv3 = new THREE.Vector3();
  async function cineTalk(lines, o = {}) {
    if (!player || mode !== 'explore' || battleCam || !lines?.length) return hooks.talk?.(lines, o);
    const pp = player.group.position, fwdP = new THREE.Vector3(Math.sin(player.group.rotation.y), 0, Math.cos(player.group.rotation.y));
    const actors = { you: player.ch || player }, moved = [];
    const ids = [...new Set(lines.map(l => l[0]).filter(w => w !== 'you'))];
    ids.forEach((id, k) => {
      const cand = npcs.filter(n => n.id === id && id !== 'glyph').sort((a, b) => Math.hypot(a.x - pp.x, a.z - pp.z) - Math.hypot(b.x - pp.x, b.z - pp.z))[0];
      if (!cand) return;
      if (Math.hypot(cand.x - pp.x, cand.z - pp.z) > 4.5) { // the speaker is elsewhere: they walk up for the scene (put back afterwards)
        const g = cand.ch.group, side = ids.length > 1 ? (k % 2 ? -1 : 1) * .9 : 0, nx = pp.x + fwdP.x * 2.8 - fwdP.z * side, nz = pp.z + fwdP.z * 2.8 + fwdP.x * side;
        moved.push({ n: cand, x: cand.x, z: cand.z, ry: g.rotation.y });
        cand.x = nx; cand.z = nz; g.position.set(nx, H(nx, nz), nz); g.visible = true;
      }
      actors[id] = cand.ch;
    });
    const posOf = (w, out) => { const a = actors[w]?.group || player.group; return out.copy(a.position); };
    const cast = Object.keys(actors), mid = new THREE.Vector3(); for (const w of cast) mid.add(posOf(w, cv1)); mid.multiplyScalar(1 / cast.length);
    for (const w of cast) { const a = actors[w]; if (!a?.group) continue; const others = cast.filter(x => x !== w); if (!others.length) continue; posOf(others[0], cv1); faceTo(a, cv1.x, cv1.z); }
    for (const n of npcs) { if (n.tag) n.tag.visible = false; if (n.mk) n.mk.visible = false; } beacon.visible = false;
    const busy0 = busy; busy = true; player.vel?.set(0, 0, 0); player.locomote?.(0); document.body.classList.add('cine-on');
    const cp = new THREE.Vector3().copy(camera.position), ct = new THREE.Vector3(), want = new THREE.Vector3(), wantT = new THREE.Vector3(); let shotT = 0, shot = 'est', cur = 'you', prev = 'you', first = true;
    camera.getWorldDirection(ct); ct.multiplyScalar(6).add(camera.position);
    const baseYaw = Math.atan2(camera.position.x - mid.x, camera.position.z - mid.z);
    const fov0 = camera.fov;
    cineCam = (c, dt) => {
      shotT += dt;
      if (shot === 'est') { // establishing: slow orbit around the group
        const a = baseYaw + shotT * .07, r = 7.5 - Math.min(1.5, shotT * .3);
        want.set(mid.x + Math.sin(a) * r, 0, mid.z + Math.cos(a) * r); want.y = Math.max(H(want.x, want.z) + 1.2, mid.y + 2.6);
        wantT.set(mid.x, mid.y + 1.3, mid.z);
      } else { // over the listener's shoulder, onto the speaker's face; slow push-in
        posOf(cur, cv1); posOf(prev === cur ? (cast.find(w => w !== cur) || 'you') : prev, cv2);
        cv3.subVectors(cv1, cv2).setY(0); const len = cv3.length() || 1; cv3.multiplyScalar(1 / len);
        const sideX = -cv3.z, sideZ = cv3.x, sh = (cast.indexOf(cur) % 2 ? -1 : 1) * .75, back = 1.5 - Math.min(.35, shotT * .06);
        if (cur === prev || cast.length < 2) { want.set(cv1.x + Math.sin(player.group.rotation.y + .6) * 3.2, 0, cv1.z + Math.cos(player.group.rotation.y + .6) * 3.2); }
        else want.set(cv2.x - cv3.x * back + sideX * sh, 0, cv2.z - cv3.z * back + sideZ * sh);
        want.y = Math.max(H(want.x, want.z) + .8, cv2.y + 1.75);
        wantT.set(cv1.x, cv1.y + 1.55, cv1.z);
      }
      const k = first ? 1 : Math.min(1, dt * (shotT < .5 ? 5 : 2)); first = false;
      cp.lerp(want, k); ct.lerp(wantT, k); c.position.copy(cp); c.lookAt(ct);
      if (c.fov !== 42) { c.fov += (42 - c.fov) * Math.min(1, dt * 3); c.updateProjectionMatrix(); }
    };
    try {
      await hooks.talk?.(lines, { ...o, cine: true, onLine: (who, i) => {
        const nw = actors[who] ? who : cur;
        if (i === 0 && (o.title || lines.length > 2)) { shot = 'est'; shotT = 0; cur = nw; setTimeout(() => { if (shot === 'est' && cineCam) { shot = 'ots'; shotT = 0; } }, 2600); }
        else { if (nw !== cur) { prev = cur; cur = nw; } shot = 'ots'; shotT = 0; first = true; }
        const a = actors[nw]; if (a?.play && nw !== 'you' && Math.random() < .5) a.play(Math.random() < .5 ? 'Wave' : 'Interact', .25, { once: true });
      } });
    } finally {
      cineCam = null; camera.fov = fov0; camera.updateProjectionMatrix(); snap = true; document.body.classList.remove('cine-on'); busy = busy0; for (const n of npcs) { if (n.tag) n.tag.visible = true; if (n.mk) n.mk.visible = true; } goalT = 0;
      for (const m of moved) { m.n.x = m.x; m.n.z = m.z; m.n.ch.group.position.set(m.x, H(m.x, m.z), m.z); m.n.ch.group.rotation.y = m.ry; }
    }
  }

  /* ---------- story glue */
  let storyBusy = false;
  function storyEvent(type, d) {
    const before = QS.Q().ch, moved = QS.event(type, d);
    if (moved) { hooks.onStep?.(QS.stepNow()); if (QS.Q().ch !== before) chapterDone(before); else setTimeout(runStoryAuto, 300); }
    return moved;
  }
  async function chapterDone(chIdx) {
    const ch = QS.STORY[chIdx]; hooks.sfx?.('win');
    if (ch.outro) await cineTalk(ch.outro, { title: `Chapter complete — ${ch.title}` });
    hooks.onChapter?.(ch, chIdx); refreshNPCs(); setTimeout(runStoryAuto, 600);
  }
  async function runStoryAuto() { // steps that play by themselves
    if (paused || document.body.classList.contains('at-title')) { clearTimeout(runStoryAuto.t); runStoryAuto.t = setTimeout(runStoryAuto, 700); return; } // menus / Lattice open: story waits
    if (storyBusy || mode !== 'explore') return; const st = QS.stepNow(); if (!st) return;
    if (st.kind === 'scene') { storyBusy = true; await cineTalk(st.lines, { title: QS.chapterNow().title }); storyBusy = false; storyEvent('scene', {}); }
    else if (st.kind === 'starter') { storyBusy = true; const i = await hooks.chooseStarter?.(); storyBusy = false; if (i != null) { storyEvent('starter', { i }); spawnCompanions(); } }
    else if (st.kind === 'capture' && st.lines && !st._told) { st._told = true; await cineTalk(st.lines); }
  }
  /* ---------- battles in the world */
  const FB = createFieldBattle({ THREE, scene, camera, H, hooks, makeCardPet, label,
    player: () => player, pet: () => pet, setCam: fn => { battleCam = fn; }, respawn: () => { const id = lastSafeTown(); const R = REGIONS[id]; teleport(R.x + (AREAS[id].spawn?.[0] || 0), R.z + (AREAS[id].spawn?.[1] || 18)); } });
  function lastSafeTown() { const q = QS.Q(), pp = player.group.position; let best = 'harbor', bd = 1e9; for (const id in q.visited) { const R = REGIONS[id]; if (!R) continue; const d = Math.hypot(R.x - pp.x, R.z - pp.z); if (d < bd && !QS.blockedAt(R.x, R.z)) { bd = d; best = id; } } return best; }
  async function wildBattle(w) {
    if (QS.Q().starter == null) { hooks.toast?.('You have no partner Echo yet — Dr. Vale at Pokébox Labs will give you one.'); w.state = 'flee'; return; }
    mode = 'battle'; w.frozen = true; savePos();
    const res = await FB.start({ kind: 'wild', wild: w, types: [w.type] });
    w.frozen = false; mode = 'explore';
    const caught = res.result === 'caught';
    if (caught || res.result === 'win') { w.dead = true; w.g.visible = false; }
    if (caught) storyEvent('capture', { card: res.card });
    if (res.result === 'win' || caught) setTimeout(runStoryAuto, 400);
  }
  async function trainerBattle(np, { mirror = false } = {}) {
    mode = 'battle'; savePos();
    const res = await FB.start({ kind: 'trainer', npc: np, mirror, name: np.name || npcName(np.id) });
    mode = 'explore';
    if (res.result === 'win') { const first = !QS.beaten(np.key); QS.markBeaten(np.key); np.tag.material.map.dispose(); const t2 = label(np.name || npcName(np.id), 'Trainer · beaten'); np.tag.material.map = t2.material.map;
      if (first) storyEvent('win', { id: np.id }); }
  }
  function teleport(x, z) { const pp = player.group.position; pp.set(x, H(x, z), z); player.vel.set(0, 0, 0); if (pet) pet.group.position.set(x + 1.2, H(x + 1.2, z), z); snap = true; streamChunks(x, z, true); savePos(); }

  /* ---------- collisions: circles + oriented boxes (spatial hash) */
  function collide(p, rad = .42) {
    for (const c of nearColliders(p.x, p.z, 3)) {
      if (c.box) {
        const dx = p.x - c.x, dz = p.z - c.z, lx = dx * c.c - dz * c.s, lz = dx * c.s + dz * c.c;
        if (Math.abs(lx) < c.hw + rad && Math.abs(lz) < c.hd + rad) {
          const ox = c.hw + rad - Math.abs(lx), oz = c.hd + rad - Math.abs(lz); let nx = lx, nz = lz;
          if (ox < oz) nx = Math.sign(lx || 1) * (c.hw + rad); else nz = Math.sign(lz || 1) * (c.hd + rad);
          p.x = c.x + nx * c.c + nz * c.s; p.z = c.z - nx * c.s + nz * c.c;
        }
        continue;
      }
      const dx = p.x - c.x, dz = p.z - c.z, d = Math.hypot(dx, dz), r = c.r + rad; if (d < r && d > 1e-4) { p.x = c.x + dx / d * r; p.z = c.z + dz / d * r; }
    }
  }

  /* ---------- per-frame */
  const fwd = new THREE.Vector3(), right = new THREE.Vector3(), mv = new THREE.Vector3(), camTarget = new THREE.Vector3(), camPos = new THREE.Vector3(), tmp = new THREE.Vector3();
  let streamT = 0, goalT = 0;
  function update(dt) {
    frameN++; t += dt; wind.value = t; tickEchoMaterials(t); const pp = player.group.position;
    if (mode === 'explore') {
      fwd.set(-Math.sin(cam.yaw), 0, -Math.cos(cam.yaw)); right.set(-fwd.z, 0, fwd.x); mv.set(0, 0, 0);
      if (!busy) { if (keys.KeyW || keys.ArrowUp) mv.add(fwd); if (keys.KeyS || keys.ArrowDown) mv.sub(fwd); if (keys.KeyD || keys.ArrowRight) mv.add(right); if (keys.KeyA || keys.ArrowLeft) mv.sub(right); }
      if (stick.lengthSq() > .01 && !busy) { mv.addScaledVector(fwd, -stick.y); mv.addScaledVector(right, stick.x); }
      if (mv.lengthSq()) target = null; else if (target) { mv.set(target.x - pp.x, 0, target.z - pp.z); if (mv.length() < .3) { target = null; mv.set(0, 0, 0); } }
      rollT -= dt; const speed = rollT > 0 ? 10 : (keys.ShiftLeft || keys.ShiftRight || touchRun || stick.length() > .95 ? 8.5 : 4.4);
      if (rollT > 0 && !mv.lengthSq()) mv.set(Math.sin(player.group.rotation.y), 0, Math.cos(player.group.rotation.y));
      if (mv.lengthSq()) { mv.normalize(); const a = Math.atan2(mv.x, mv.z); let d = a - player.group.rotation.y; d = Math.atan2(Math.sin(d), Math.cos(d)); player.group.rotation.y += d * Math.min(1, dt * 12); }
      player.vel.lerp(mv.multiplyScalar(speed), Math.min(1, dt * (onGround ? 10 : 3)));
      const nx = pp.x + player.vel.x * dt, nz = pp.z + player.vel.z * dt, hn = H(nx, nz), ho = H(pp.x, pp.z), st = Math.hypot(nx - pp.x, nz - pp.z) || 1e-4;
      const why = QS.blockedAt(nx, nz);
      if (why) { player.vel.multiplyScalar(0); if (blockMsgT <= 0) { blockMsgT = 3; const G = GATES.find(g => g.route === why); hooks.toast?.(why === 'starter' ? 'Rho: "Whoa — not without a partner Echo! Dr. Vale is at the Lab."' : G ? G.text : 'You can\'t go that way yet.'); } }
      else if (hn > -.55 && (hn - ho) / st < 1.25) { pp.x = nx; pp.z = nz; }
      else if (hn > -.55 && (hn - ho) / st < 4) { pp.x += (nx - pp.x) * .38; pp.z += (nz - pp.z) * .38; } // steep ground: scramble up slowly — every mountain can be climbed
      else player.vel.multiplyScalar(.2);
      blockMsgT -= dt;
      collide(pp);
      const gy = Math.max(H(pp.x, pp.z), -.45);
      vy -= 18 * dt; pp.y += vy * dt; if (pp.y <= gy) { pp.y = gy; vy = 0; onGround = true; }
      player.locomote(onGround ? player.vel.length() : 0);
    }
    player.update(dt);
    { sun.position.set(pp.x + sunDir.x * 60, pp.y + sunDir.y * 60, pp.z + sunDir.z * 60); sun.target.position.copy(pp); }
    if (grassMesh) { grassMesh.userData.grass.time.value = t; grassMesh.userData.grass.player.value.copy(pp); }
    if (water) { water.position.set(Math.round(pp.x / 32) * 32, 0, Math.round(pp.z / 32) * 32); water.userData.tick(t); }
    if (sky) { sky.position.copy(camera.position); sky.userData.tick(t); }
    if (fxP) fxP.userData.tick(t, pp); if (rainP) rainP.userData.tick(t, pp);
    // camera
    if (cineCam) cineCam(camera, dt);
    else if (battleCam) battleCam(camera, dt);
    else {
      // soft auto-follow: when the player runs and the camera has not been touched for a moment, ease in behind them
      cam.idle += dt; const spd = Math.hypot(player.vel.x, player.vel.z);
      if (!drag && cam.idle > 1.2 && spd > 1.5) { const behind = Math.atan2(-player.vel.x, -player.vel.z); let d = behind - cam.tYaw; d = Math.atan2(Math.sin(d), Math.cos(d)); cam.tYaw += d * Math.min(1, dt * .9) * Math.min(1, spd / 6); }
      cam.yaw += (cam.tYaw - cam.yaw) * Math.min(1, dt * 8);
      // camera collision: pull in when a building stands between the player and the camera
      const want = cam.tDist; let clip = want;
      for (let k = 1; k <= 8; k++) { const dd = want * k / 8, qx = pp.x + Math.sin(cam.yaw) * dd, qz = pp.z + Math.cos(cam.yaw) * dd;
        for (const c of nearColliders(qx, qz, 1)) { const inside = c.box ? (() => { const dx = qx - c.x, dz = qz - c.z, lx = dx * c.c - dz * c.s, lz = dx * c.s + dz * c.c; return Math.abs(lx) < c.hw + .3 && Math.abs(lz) < c.hd + .3; })() : c.r > 1.4 && Math.hypot(qx - c.x, qz - c.z) < c.r;
          if (inside) { clip = Math.min(clip, Math.max(1.6, dd - .6)); break; } }
        if (clip < want) break; }
      cam.dist += (clip - cam.dist) * Math.min(1, dt * (clip < cam.dist ? 14 : 4));
      const tY = pp.y + 1.35 + (cam.dist < 3.5 ? .15 : 0);
      camTarget.set(pp.x, tY, pp.z);
      const cx = pp.x + Math.sin(cam.yaw) * Math.cos(cam.pitch) * cam.dist, cz = pp.z + Math.cos(cam.yaw) * Math.cos(cam.pitch) * cam.dist;
      const cy = Math.max(tY + Math.sin(cam.pitch) * cam.dist, H(cx, cz) + .6, .6);
      camPos.set(cx, cy, cz); if (snap) { camera.position.copy(camPos); snap = false; } else camera.position.lerp(camPos, Math.min(1, dt * 7)); camera.lookAt(camTarget);
    }
    const fov = hooks.fov?.() || 58; if (camera.fov !== fov) { camera.fov = fov; camera.updateProjectionMatrix(); }
    streamT -= dt; if (streamT <= 0) { streamT = .35; streamChunks(pp.x, pp.z); for (const o of gateObjs) if (!QS.flag(o.G.flag)) o.g.visible = o.g.position.distanceTo(pp) < 160; for (const id in towns) towns[id].root.visible = Math.hypot(towns[id].x - pp.x, towns[id].z - pp.z) < viewFar + 70; for (const lm of landmarks) lm.g.visible = Math.hypot(lm.x - pp.x, lm.z - pp.z) < viewFar * .85; }
    for (const n of npcs) { const d = Math.hypot(pp.x - n.x, pp.z - n.z); n.ch.group.visible = d < 70 && n.id !== 'glyph'; if (n.glyphFx) n.glyphFx.visible = d < 120; if (d < 45) n.ch.update(dt); n.mk.rotation.y = t * 2; n.mk.position.y = 3.25 + Math.sin(t * 3) * .08;
      if (d < 6) faceSmooth(n.ch, pp.x, pp.z, dt, 4); else { let dd = n.face - n.ch.group.rotation.y; dd = Math.atan2(Math.sin(dd), Math.cos(dd)); n.ch.group.rotation.y += dd * Math.min(1, dt * 1.5); }
      if (n.routeTrainer && !QS.beaten(n.key) && d < 7.5 && mode === 'explore' && !busy && !n.spotted) { n.spotted = true; spotted(n); } }
    for (const v of allVillagers) {
      const g = v.ch.group.position, dPl = Math.hypot(pp.x - g.x, pp.z - g.z); v.ch.group.visible = dPl < 55; if (dPl > 55) continue; v.x = g.x; v.z = g.z;
      if (v.job) { // working people: stay at their spot, loop their work motion with natural pauses, look at you when you come close
        const J = JOBS[v.job];
        if (dPl < 3.4) faceSmooth(v.ch, pp.x, pp.z, dt, 3); else faceSmooth(v.ch, g.x + Math.sin(v.face), g.z + Math.cos(v.face), dt, 1.5);
        v.jt -= dt;
        if (dPl < 3.4) { if (!v.paused) { v.paused = true; v.ch.play('Idle', .4); } }   // stops working to talk to you
        else if (v.jt <= 0 && J) { v.working = !v.working; v.paused = false; const [a, b] = v.working ? J.work : J.rest; v.jt = a + Math.random() * (b - a);
          if (v.working) v.ch.play(J.loop, .5, { speed: (J.speed || 1) * (.9 + Math.random() * .2) }); else if (J.alt && Math.random() < .5) v.ch.play(J.alt, .4, { once: true }); else v.ch.play('Idle', .5); }
        else if (v.paused && dPl >= 3.4) { v.paused = false; v.jt = 0; v.working = false; }
        if (dPl < 40) v.ch.update(dt); continue;
      }
      if (v.wait > 0) { v.wait -= dt; v.ch.locomote(0); if (dPl < 4) faceSmooth(v.ch, pp.x, pp.z, dt); }
      else { const [tx, tz] = v.pts[v.i], dx = tx - g.x, dz = tz - g.z, d = Math.hypot(dx, dz);
        if (d < .4) { v.i = (v.i + 1) % v.pts.length; v.wait = 1 + Math.random() * 4; }
        else if (dPl < 1.6) v.wait = 1.5; else { g.x += dx / d * v.speed * dt; g.z += dz / d * v.speed * dt; faceSmooth(v.ch, tx, tz, dt); v.ch.locomote(v.speed); } }
      g.y = H(g.x, g.z); if (dPl < 40) v.ch.update(dt);
    }
    if (mode === 'explore') { spawnWilds(dt, pp); updatePet(dt, pp); }
    updateWilds(dt, pp); envCycle(dt);
    animated.forEach(f => f(t)); tickers.forEach(f => f(t, pp));
    if (flash > 0) flash = Math.max(0, flash - dt * 4);
    goalT -= dt; if (goalT <= 0) { goalT = .5; updateGoal(pp); }
    FB.update(dt, t);
    if (mode === 'explore') {
      let best = null, bd = 1e9;
      for (const n of npcs) { if (!n.ch.group.visible && n.id !== 'glyph') continue; const d = Math.hypot(pp.x - n.x, pp.z - n.z); if (d < n.r && d < bd) { bd = d; best = { kind: 'npc', npc: n, id: n.key, x: n.x, z: n.z }; } }
      for (const v of allVillagers) { const d = Math.hypot(pp.x - v.x, pp.z - v.z); if (d < 2 && d < bd) { bd = d; best = { kind: 'villager', v, id: 'v' + v.x.toFixed(0), x: v.x, z: v.z }; } }
      for (const it of allItems) { const d = Math.hypot(pp.x - it.x, pp.z - it.z); if (d < it.r && d < bd) { bd = d; best = it.kind === 'travel' ? { kind: 'travel', id: it.id, x: it.x, z: it.z } : it.kind === 'chest' ? { kind: 'chest', id: it.id, item: it, x: it.x, z: it.z } : { kind: 'find', id: it.id, item: it, x: it.x, z: it.z }; } }
      for (const w of wilds) { if (w.dead) continue; const d = Math.hypot(pp.x - w.x, pp.z - w.z); if (d < w.r + .6 && d < bd) { bd = d; best = { kind: 'wild', w, id: 'w' + w.card.i, x: w.x, z: w.z }; } }
      if ((best ? best.kind + best.id : '') !== (near ? near.kind + near.id : '')) { near = best; hooks.prompt?.(best ? promptText(best) : null); }
    } else if (near) { near = null; hooks.prompt?.(null); }
    drawMinimap(pp);
  }
  async function spotted(n) { // route trainer sees you: "!" then walks over
    busy = true; hooks.sfx?.('whoosh', .4); const ex = label('!', null, '#ffd257'); ex.scale.set(1.2, 1.2, 1); ex.position.y = 3.6; n.ch.group.add(ex);
    const pp = player.group.position; faceTo(player, n.x, n.z);
    await new Promise(r => setTimeout(r, 700)); n.ch.group.remove(ex);
    const g = n.ch.group.position, tx = pp.x + (g.x - pp.x) / Math.hypot(g.x - pp.x, g.z - pp.z) * 2.2, tz = pp.z + (g.z - pp.z) / Math.hypot(g.x - pp.x, g.z - pp.z) * 2.2;
    const t0 = performance.now(), x0 = g.x, z0 = g.z; faceTo(n.ch, pp.x, pp.z);
    await new Promise(res => { const step = () => { const k = Math.min(1, (performance.now() - t0) / 700); g.x = lerp(x0, tx, k); g.z = lerp(z0, tz, k); g.y = H(g.x, g.z); n.ch.locomote(k < 1 ? 3 : 0); if (k < 1) requestAnimationFrame(step); else res(); }; step(); });
    n.x = g.x; n.z = g.z; removeCollider(n.col); n.col = addCollider({ x: g.x, z: g.z, r: .55 });
    busy = false; await talkTo(n);
  }
  function updateGoal(pp) {
    const tg = QS.target(); const st = QS.stepNow();
    if (st?.kind === 'goto') storyEvent('reach', { x: pp.x, z: pp.z });
    if (tg && tg.x != null) { beacon.visible = true; beacon.position.set(tg.x, H(tg.x, tg.z), tg.z); const d = Math.hypot(tg.x - pp.x, tg.z - pp.z); beacon.userData.beam.material.opacity = d < 12 ? .05 : .16; }
    else beacon.visible = false;
    if (beacon.visible) { beacon.userData.gem.rotation.y = t * 2; beacon.userData.gem.position.y = 4.2 + Math.sin(t * 2) * .3; }
    let gx = null, gz = null; if (tg?.x != null) { gx = tg.x; gz = tg.z; } else if (tg?.findIds) { let bd = 1e9; for (const it of allItems) if (tg.findIds.includes(it.id)) { const d = Math.hypot(it.x - pp.x, it.z - pp.z); if (d < bd) { bd = d; gx = it.x; gz = it.z; } } }
    hooks.goal?.(st ? { text: st.text, dist: gx != null ? Math.round(Math.hypot(gx - pp.x, gz - pp.z)) : null, ang: gx != null ? Math.atan2(gx - pp.x, gz - pp.z) - cam.yaw - Math.PI : 0, chapter: QS.chapterNow() } : null);
    goalPos = gx != null ? { x: gx, z: gz } : null;
  }
  let goalPos = null;
  function faceSmooth(ch, x, z, dt, k = 5) { const p = ch.group.position, a = Math.atan2(x - p.x, z - p.z); let d = a - ch.group.rotation.y; d = Math.atan2(Math.sin(d), Math.cos(d)); ch.group.rotation.y += d * Math.min(1, dt * k); }
  const pTarget = new THREE.Vector3();
  function updatePet(dt, pp) {
    if (!pet) return;
    const ry = player.group.rotation.y, sp = player.vel.length();
    let ne = null, nd = 9; for (const e of wilds) { const d = Math.hypot(pp.x - e.x, pp.z - e.z); if (d < nd) { nd = d; ne = e; } }
    const back = sp > 4 ? 1.4 : .6, side = 1.6; pTarget.set(pp.x - Math.sin(ry) * back - Math.cos(ry) * side, 0, pp.z - Math.cos(ry) * back + Math.sin(ry) * side);
    const g = pet.group.position, dx = pTarget.x - g.x, dz = pTarget.z - g.z, dist = Math.hypot(dx, dz);
    if (dist > 16) g.set(pTarget.x, H(pTarget.x, pTarget.z), pTarget.z);
    const want = dist > .35 ? Math.min(sp + 1.5, dist * 3.2) : 0; tmp.set(dx, 0, dz); if (tmp.lengthSq() > 1e-6) tmp.normalize(); pet.vel.lerp(tmp.multiplyScalar(want), Math.min(1, dt * 6));
    g.x += pet.vel.x * dt; g.z += pet.vel.z * dt; collide(g, .45); g.y = H(g.x, g.z);
    pet.update(dt, pet.vel.length(), t, camera, pet.vel);
    if (pet.nm) { pet.nm.visible = !!ne || sp < .3; pet.nm.position.y = 2.1 + (ne ? .15 : 0); }
  }
  function promptText(n) {
    if (n.kind === 'npc') { const np = n.npc, st = QS.stepNow(), story = st?.npc === np.id; return `<b>E</b> ${story && st.kind === 'battle' ? 'Battle' : np.shop ? 'Shop with' : np.trainer && !QS.beaten(np.key) ? 'Talk & battle' : 'Talk to'} ${esc(np.name || npcName(np.id))}${story ? ' <span class="gold">★</span>' : ''}`; }
    if (n.kind === 'villager') return '<b>E</b> Chat';
    if (n.kind === 'travel') return '<b>E</b> Relay Ferry — fast travel';
    if (n.kind === 'chest') return P.ensure().world.found[n.id] ? '<b>E</b> Empty chest' : '<b>E</b> Open treasure chest';
    if (n.kind === 'wild') return `<b>E</b> Battle the wild <span style="color:${TYPE_COL[n.w.type]}">${esc(n.w.card?.n || n.w.type)}</span>`;
    const done = P.ensure().world.found[n.id]; return `<b>E</b> ${{ glyph: 'Read glyph stone', glass: 'Inspect glass silhouette', pylon: 'Stabilise relay pylon' }[n.item.kind]}${done ? ' (done)' : ''}`;
  }

  /* ---------- minimap: island map (from the worker) + live markers, rotates with the camera */
  let mmT = 0;
  function drawMinimap(pp) {
    const cv = hooks.minimap?.(); if (!cv || !mapCanvas || (mmT = (mmT + 1) % 3)) return;
    const g = cv.getContext('2d'), W = cv.width, R = W / 2, zoom = 1.9, rot = cam.yaw - Math.PI, k = mapCanvas.width / WORLD;
    g.save(); g.clearRect(0, 0, W, W); g.beginPath(); g.arc(R, R, R - 2, 0, Math.PI * 2); g.clip();
    g.fillStyle = '#1f4f86'; g.fillRect(0, 0, W, W);
    g.translate(R, R); g.rotate(rot); g.translate(-pp.x * zoom, -pp.z * zoom);
    g.imageSmoothingEnabled = true; g.drawImage(mapCanvas, -WORLD / 2 * zoom, -WORLD / 2 * zoom, WORLD * zoom, WORLD * zoom);
    const dot = (x, z, c, r = 4) => { g.fillStyle = c; g.beginPath(); g.arc(x * zoom, z * zoom, r, 0, 7); g.fill(); g.lineWidth = 1.5; g.strokeStyle = 'rgba(0,0,0,.6)'; g.stroke(); };
    const found = P.ensure().world.found;
    for (const it of allItems) if (Math.abs(it.x - pp.x) < 120 && Math.abs(it.z - pp.z) < 120) dot(it.x, it.z, it.kind === 'travel' ? '#ffffff' : found[it.id] ? '#6b7280' : it.kind === 'chest' ? '#ffd257' : '#5cf2d6', it.kind === 'travel' ? 4 : 4.5);
    for (const n of npcs) if (Math.abs(n.x - pp.x) < 120 && Math.abs(n.z - pp.z) < 120) dot(n.x, n.z, n.trainer && !QS.beaten(n.key) ? '#ffd257' : '#c9a4ff', 4.5);
    for (const e of wilds) if (!e.dead) dot(e.x, e.z, TYPE_COL[e.type], 3.5);
    if (goalPos) { g.save(); g.translate(goalPos.x * zoom, goalPos.z * zoom); g.rotate(-rot); g.fillStyle = '#ffd257'; g.strokeStyle = '#1b1530'; g.lineWidth = 2; g.beginPath(); for (let i = 0; i < 10; i++) { const a = i / 10 * Math.PI * 2 - Math.PI / 2, rr = i % 2 ? 4 : 9; g.lineTo(Math.cos(a) * rr, Math.sin(a) * rr); } g.closePath(); g.fill(); g.stroke(); g.restore(); }
    g.restore();
    if (goalPos) { const a = Math.atan2(goalPos.x - pp.x, goalPos.z - pp.z), d = Math.hypot(goalPos.x - pp.x, goalPos.z - pp.z); if (d * zoom > R - 10) { const ang = -(a - rot) + Math.PI; const ex = R + Math.sin(ang) * (R - 12), ey = R - Math.cos(ang) * (R - 12);
      g.save(); g.translate(ex, ey); g.rotate(ang); g.fillStyle = '#ffd257'; g.strokeStyle = '#1b1530'; g.lineWidth = 2; g.beginPath(); g.moveTo(0, -9); g.lineTo(7, 6); g.lineTo(-7, 6); g.closePath(); g.fill(); g.stroke(); g.restore(); } }
    g.save(); g.translate(R, R); g.rotate(-(player.group.rotation.y - cam.yaw)); g.fillStyle = '#fff'; g.strokeStyle = '#1b1530'; g.lineWidth = 2;
    g.beginPath(); g.moveTo(0, -9); g.lineTo(6, 7); g.lineTo(0, 3); g.lineTo(-6, 7); g.closePath(); g.fill(); g.stroke(); g.restore();
    g.strokeStyle = 'rgba(255,255,255,.35)'; g.lineWidth = 3; g.beginPath(); g.arc(R, R, R - 2, 0, 7); g.stroke();
    const nx = R + Math.sin(rot) * (R - 13), ny = R - Math.cos(rot) * (R - 13);
    g.fillStyle = '#ff6a6a'; g.font = '800 14px "Barlow Condensed", sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText('N', nx, ny);
  }

  function loop(now) {
    if (!running) return; raf = requestAnimationFrame(loop);
    const dt = clamp((now - last) / 1000, 0, .05); last = now; if (!player || !built) return;
    if (!paused) update(dt);
    if (post) post.render(dt); else renderer.render(scene, camera);
    perf.s += dt; if (++perf.n === 60) {
      const avg = perf.s / perf.n; perf.n = perf.s = 0; hooks.fps?.(Math.round(1 / Math.max(avg, .001)));
      // dynamic resolution: drop pixel ratio when frames are slow, win it back when there is headroom (target ~55-60 fps)
      if (autoQ && !paused && mode !== 'battle-intro') {
        if (avg > .021 && pr > .7) { pr = Math.max(.7, pr - (avg > .03 ? .15 : .07)); renderer.setPixelRatio(pr); resize(); prT = 0; }
        else if (avg < .0175 && pr < prMax && ++prT >= 3) { pr = Math.min(prMax, pr + .05); renderer.setPixelRatio(pr); resize(); prT = 0; }
      }
    }
  }
  function resize() { const w = canvas.clientWidth || innerWidth, hh = canvas.clientHeight || innerHeight; renderer.setSize(w, hh, false); camera.aspect = w / hh; camera.updateProjectionMatrix(); post?.setSize(w, hh); }
  function start() { if (running) return; running = true; resize(); last = performance.now(); addEventListener('keydown', down); addEventListener('keyup', up); addEventListener('resize', resize); raf = requestAnimationFrame(loop); }
  function stop() { running = false; cancelAnimationFrame(raf); removeEventListener('keydown', down); removeEventListener('keyup', up); removeEventListener('resize', resize); for (const k in keys) keys[k] = false; if (player) savePos(); }
  return {
    setStick(x, y) { stick.set(x, y); }, setRun(v) { touchRun = !!v; },
    key(code, isDown = true) { const ev = { code, key: code, target: document.body, preventDefault() {} }; if (isDown) down(ev); else up(ev); },
    teleport(x, z) { teleport(x, z); },
    setView(yaw, pitch = cam.pitch, dist = cam.tDist) { cam.yaw = cam.tYaw = yaw; cam.pitch = pitch; cam.tDist = cam.dist = dist; cam.idle = 0; snap = true; },
    travelTo(id) { const R = REGIONS[id]; if (!R) return; teleport(R.x + (AREAS[id].spawn?.[0] || 0), R.z + (AREAS[id].spawn?.[1] || 18)); },
    snapshot(w = 960) { if (post) post.render(0); else renderer.render(scene, camera); const src = renderer.domElement, c = document.createElement('canvas'); c.width = w; c.height = Math.round(w * src.height / src.width); c.getContext('2d').drawImage(src, 0, 0, c.width, c.height); return c.toDataURL('image/jpeg', .82); },
    enter, start, stop, resize, refreshLook, refreshPartner: spawnCompanions, refreshPet: spawnCompanions, refreshStory() { refreshNPCs(); runStoryAuto(); },
    setPaused(v) { paused = v; if (v) for (const k in keys) keys[k] = false; }, get paused() { return paused; },
    setQuality() { applyQuality(); for (const c of [...chunks.values()]) dropChunk(c); if (player) streamChunks(player.group.position.x, player.group.position.z, true); }, setAutoQuality(v) { autoQ = v; },
    get pet() { return pet; }, get ready() { return !!player && built; }, cine: (l, o) => cineTalk(l, o), get player() { return player; }, get echoes() { return wilds; }, get area() { return lastRegion || 'harbor'; }, get running() { return running; }, get mode() { return mode; },
    get stats() { return post?.info || renderer.info.render; }, get debug() { return { scene, renderer, camera, quality, pr, post, chunks, npcs, wilds, FB, decorLog, villagers: allVillagers }; },
    get mapCanvas() { return mapCanvas; }, regions: REGIONS, areas: AREAS,
    breakdown() { const out = {}; scene.traverse(o => { if (!o.isMesh || !o.visible) return; const g = o.geometry, tri = (g.index ? g.index.count : g.attributes.position.count) / 3, n = (o.isInstancedMesh ? o.count : 1) * (g.isInstancedBufferGeometry ? g.instanceCount : 1); const key = (o.isInstancedMesh ? 'I:' : o.isSkinnedMesh ? 'S:' : 'M:') + (o.material.name || o.material.type); out[key] = (out[key] || 0) + Math.round(tri * n); }); return Object.entries(out).sort((a, b) => b[1] - a[1]).slice(0, 30); },
  };
}
