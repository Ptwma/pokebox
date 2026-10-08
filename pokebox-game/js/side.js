// Pokebox — side stories: small optional quests around the towns of Veyra (not needed for the main story).
// Each quest: a giver in a town, a few steps (find a spot, catch an Echo of a type, deliver to someone, beat someone) and a
// little story told in the dialogue. State lives in the save (s.side[id] = { s: step, done }); progress never blocks.
import * as C from './core.js';
import * as P from './progress.js';

const L = (body, skin, hairColor, top, topColor, hat = 'none') => ({ body, skin, hairColor, top, topColor, hat, acc: 'none', colors: { Outfit: null } });

export const SIDE = [
  { id: 'nia', title: "Nia's Lost Pecklet", town: 'harbor', minCh: 0, at: [-22, 18], giver: { id: 'sq_nia', name: 'Little Nia', look: L('f', 'sk1', 'hc6', 'tee', 'tc3') },
    intro: [['sq_nia', "Ranger! Ranger! My Pecklet card fell out of my pocket when the seagulls chased me…"], ['sq_nia', "It was by the rocks on the beach, I think. Pecklet is scared of seagulls. And of water. And of me sometimes."], ['sq_nia', 'Can you find it? Please please please?']],
    steps: [
      { kind: 'find', text: 'Find the lost card on the beach rocks', at: [30, 30], lines: [['you', 'A Lattice card, half buried in the sand. The little Echo on it is shivering.']] },
      { kind: 'talk', text: 'Bring the card back to Nia', npc: 'sq_nia', lines: [['sq_nia', 'PECKLET! You found her! Look, she stopped shaking!'], ['sq_nia', 'Here — Mom says Rangers get paid. This is my whole piggy bank. Okay, half of it.']] } ],
    reward: { coins: 250, xp: 80 } },

  { id: 'letter', title: "The Ferryman's Letter", town: 'harbor', minCh: 1, at: [16, 6], giver: { id: 'sq_bram', name: 'Old Bram', look: L('m', 'sk2', 'hc4', 'jacket', 'tc8', 'cap'), model: 'm_elder' },
    intro: [['sq_bram', 'Thirty years I ran the ferry between here and Mistvale. Thirty years I carried a letter I never sent.'], ['sq_bram', "It's for Mae. Granny Mae, they call her now. We were going to be married, before the storm night."], ['sq_bram', "You're heading west anyway. Would you… give it to her? Don't read it. Well. You can read it. It's not very good."]],
    steps: [
      { kind: 'talk', text: 'Deliver the letter to Granny Mae in Mistvale', npc: 'sq_mae', where: { town: 'mistvale', at: [-14, 10], name: 'Granny Mae', look: L('f', 'sk3', 'hc4', 'robe', 'tc9'), model: 'f_elder' },
        lines: [['sq_mae', 'A letter? From… Bram? That old fool. That sweet, slow old fool.'], ['sq_mae', '"The relay ate my courage the night of the storm. I hope it gives it back." Hm.'], ['sq_mae', 'Tell him the ferry still runs. Tell him I still take my tea at four. He knows where.']] },
      { kind: 'talk', text: "Tell Bram what Mae said", npc: 'sq_bram', lines: [['sq_bram', 'Four o\'clock. She remembered.'], ['sq_bram', 'I owe you more than coins, Ranger. But coins are what I have. Thank you.']] } ],
    reward: { coins: 400, xp: 160 } },

  { id: 'lanterns', title: 'Lanterns in the Fog', town: 'mistvale', minCh: 2, at: [12, -12], giver: { id: 'sq_ivo', name: 'Lantern-keeper Ivo', look: L('m', 'sk4', 'hc1', 'ranger', 'tc5', 'wide') },
    intro: [['sq_ivo', 'The fog came back thicker after the siphon. My lanterns keep the little Echoes from getting lost at night.'], ['sq_ivo', 'Three of them went out around the pond. Light them for me? Just press the wick — they remember the flame.']],
    steps: [
      { kind: 'find', text: 'Light the lantern by the reeds', at: [-26, -20], lines: [['you', 'The lantern flickers… and catches. Three tiny Echoes drift toward the light.']] },
      { kind: 'find', text: 'Light the lantern on the boardwalk', at: [24, 20], lines: [['you', 'Another lantern glows. Somewhere in the fog, something sighs with relief.']] },
      { kind: 'find', text: 'Light the lantern under the willow', at: [-4, 34], lines: [['you', 'The last lantern burns blue for a moment, then gold.']] },
      { kind: 'talk', text: 'Go back to Ivo', npc: 'sq_ivo', lines: [['sq_ivo', 'You see that? The fog parted. The Echoes are going home.'], ['sq_ivo', 'Take this. And come back on a clear night — the pond shows the stars twice.']] } ],
    reward: { coins: 450, xp: 200 } },

  { id: 'meteor', title: 'The Star That Fell', town: 'starfall', minCh: 3, at: [-10, 8], giver: { id: 'sq_ada', name: 'Astronomer Ada', look: L('f', 'sk0', 'hc9', 'labcoat', 'tc6') },
    intro: [['sq_ada', 'Last night a star fell on the hill. A real one! Well — a rock. A rock that hums.'], ['sq_ada', 'I can\'t leave my telescope. Could you find the fragment? And if anything… comes out of it, please don\'t panic.']],
    steps: [
      { kind: 'find', text: 'Find the fallen star on the hill', at: [34, -26], lines: [['you', 'A warm, humming stone. As you touch it, something Psychic stirs in the grass nearby.']] },
      { kind: 'capture', text: 'Catch the Psychic Echo that came out of the star', type: 'Psychic', n: 1 },
      { kind: 'talk', text: 'Show Ada the star and the Echo', npc: 'sq_ada', lines: [['sq_ada', 'It was IN the meteor? Then the relay isn\'t the only thing that remembers…'], ['sq_ada', 'Keep the Echo. It clearly likes you. I\'ll keep the rock. And thank you!']] } ],
    reward: { coins: 600, xp: 260 } },

  { id: 'blankets', title: 'Frozen Delivery', town: 'frostline', minCh: 4, at: [8, 14], giver: { id: 'sq_tilda', name: 'Innkeeper Tilda', look: L('f', 'sk2', 'hc2', 'jacket', 'tc2', 'beanie') },
    intro: [['sq_tilda', 'A Syndicate straggler stole the blankets for the shelter — forty of them! He\'s hiding by the frozen lake, selling them to Rangers.'], ['sq_tilda', 'The little ones at the shelter are cold tonight. Get them back?']],
    steps: [
      { kind: 'battle', text: 'Make the blanket thief give them back', npc: 'sq_thief', where: { town: 'frostline', at: [-30, -22], name: 'Syndicate Straggler', look: L('m', 'sk1', 'hc0', 'hoodie', 'tc0', 'beanie') }, types: ['Darkness', 'Water'],
        lines: [['sq_thief', 'Blankets! Warm blankets! Five hundred coins each — oh. It\'s you. The one who beat Vex.'], ['sq_thief', 'I mean — battle for them? Winner keeps the blankets?']] },
      { kind: 'talk', text: 'Bring the blankets back to Tilda', npc: 'sq_tilda', lines: [['sq_tilda', 'All forty! You\'re a hero, Ranger. Soup\'s on the house — forever.']] } ],
    reward: { coins: 700, xp: 300 } },

  { id: 'robot', title: 'Spark for an Old Robot', town: 'voltspire', minCh: 5, at: [-12, 10], giver: { id: 'sq_gus', name: 'Engineer Gus', look: L('m', 'sk3', 'hc8', 'crew', 'tc7', 'cap') },
    intro: [['sq_gus', 'See this old relay robot? Built it when I was your age. It ran on a Lightning Echo until the storm night.'], ['sq_gus', 'Bring me a Lightning Echo that wants to help — I mean, catch one — and I\'ll show you what it can do.']],
    steps: [
      { kind: 'capture', text: 'Catch a Lightning Echo for Gus', type: 'Lightning', n: 1 },
      { kind: 'talk', text: 'Bring the Echo to Gus', npc: 'sq_gus', lines: [['sq_gus', 'Here goes… CONTACT!'], ['sq_gus', '…It\'s waving. It\'s WAVING! Thirty years! Ranger, you just made an old man very loud.']] } ],
    reward: { coins: 800, xp: 340 } },

  { id: 'mirage', title: 'The Mirage Merchant', town: 'sandreach', minCh: 6, at: [6, -10], giver: { id: 'sq_zara', name: 'Merchant Zara', look: L('f', 'sk4', 'hc0', 'robe', 'tc1') },
    intro: [['sq_zara', 'Every evening a merchant appears in the dunes, sells one glass shard, and vanishes. A mirage, they say.'], ['sq_zara', 'I say mirages don\'t take money. Find his shards in the sand — two of them — and let\'s see what he is.']],
    steps: [
      { kind: 'find', text: 'Find the first glass shard in the dunes', at: [40, 26], lines: [['you', 'A shard of glass in the shape of a Pokémon\'s paw. It is warm.']] },
      { kind: 'find', text: 'Find the second glass shard', at: [-38, 30], lines: [['you', 'The second shard fits the first one perfectly. Together they hum a tune.']] },
      { kind: 'talk', text: 'Bring the shards to Zara', npc: 'sq_zara', lines: [['sq_zara', 'A paw… and a tail. It\'s a Vulpix. The mirage is an Echo! A lonely one, trading its own memory for company.'], ['sq_zara', 'I\'ll set a lantern out for it tonight. Thank you, Ranger. Take this — it\'s real money. Probably.']] } ],
    reward: { coins: 900, xp: 380 } },
];

/* ------------------------------------------------------------------ state */
const S = () => { const s = P.ensure(); s.side ||= {}; return s.side; };
export const stateOf = id => S()[id] || null;
export const available = (ch) => SIDE.filter(q => ch >= q.minCh);
export function current(q) { const st = stateOf(q.id); return st && !st.done ? q.steps[st.s] : null; }
export const byNpc = id => SIDE.find(q => q.giver.id === id || q.steps.some(s => s.npc === id));
export const active = () => SIDE.filter(q => { const st = stateOf(q.id); return st && !st.done; });
export const doneCount = () => SIDE.filter(q => stateOf(q.id)?.done).length;

function finish(q) { const st = S()[q.id]; st.done = Date.now(); if (q.reward.coins) C.addCoins(q.reward.coins); C.save(true); return { reward: q.reward }; }
function step(q) { const st = S()[q.id]; st.s++; if (st.s >= q.steps.length) return finish(q); C.save(true); return null; }

/** talking to a side-quest person: returns { lines, accept?, battle?, finished? } — the caller plays the lines */
export function talk(npcId) {
  const q = byNpc(npcId); if (!q) return null; const st = stateOf(q.id);
  if (!st) { if (npcId !== q.giver.id) return { lines: [[npcId, '…']] }; S()[q.id] = { s: 0, done: 0, t: Date.now() }; C.save(true); return { lines: q.intro, accepted: q }; }
  if (st.done) return { lines: [[npcId, npcId === q.giver.id ? 'Thank you again, Ranger. Veyra is a little warmer because of you.' : 'Good to see you, Ranger.']] };
  const cur = q.steps[st.s];
  if (cur.npc === npcId && cur.kind === 'talk') { const r = step(q); return { lines: cur.lines || [], finished: r ? q : null, reward: r }; }
  if (cur.npc === npcId && cur.kind === 'battle') return { lines: cur.lines || [], battle: cur };
  return { lines: [[npcId, npcId === q.giver.id ? `Any luck? ${cur.text}.` : '…']] };
}
/** a found spot / a won battle / a capture moves a quest on; returns finished quest (or null) */
export function event(type, d = {}) {
  for (const q of active()) { const cur = current(q); if (!cur) continue;
    if (type === 'find' && cur.kind === 'find' && d.id === `${q.id}:${S()[q.id].s}`) { const r = step(q); return { q, cur, finished: r ? q : null, reward: r }; }
    if (type === 'win' && cur.kind === 'battle' && cur.npc === d.id) { const r = step(q); return { q, cur, finished: r ? q : null, reward: r }; }
    if (type === 'capture' && cur.kind === 'capture' && (!cur.type || d.card?.t === cur.type)) { const st = S()[q.id]; st.n = (st.n || 0) + 1; if (st.n >= (cur.n || 1)) { st.n = 0; const r = step(q); return { q, cur, finished: r ? q : null, reward: r }; } C.save(); }
  }
  return null;
}
