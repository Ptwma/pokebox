# SIGIL & SPARK — story, systems and intro (v1 draft, 2026-10-31)

> Replaces the Pokébox / Pokémon-card story. Same world (Veyra, Lumen Harbor, the lighthouse island, Route 1 → Mistvale), same
> MetaHuman cast, same 41 creatures (Quaternius CC0) — new story, names, battle, UI, intro and tutorial. All names and designs
> are original. The *feeling* borrows from Black Clover (an underdog with a strange magic book), Pokémon (bond, collect,
> evolve) and Digimon (evolution inside the fight) — nothing is copied.
> User decisions (2026-10-31): story **C — Sigil & Spark**, battle **Pact Battle** (semi-real-time), intro **live in-engine**,
> narration **offline TTS (Piper)**.

---

## 1. Pitch
The world was *written*. Every wave, stone and living thing is a word in the **Script**, a language older than memory.
Some words became so full of meaning that they woke up: the **Sparks**. People learned to bond with them in a **Codex**,
half spellbook, half instrument, whose pages write themselves when a bond is made.
On the day every eleven-year-old receives a Codex, yours opens **blank**. That same day the **White Page** comes to Lumen
Harbor to erase the Script. Your blank book is not broken: it is a **First Page**, the only kind of book that can write *new*
words.

## 2. Lore (the rules of the world)
| Thing | What it is | Gameplay |
|---|---|---|
| **The Script** | The world's source language; glyphs glow faintly on old stones and ruins | collectible glyph stones = new Codex spells |
| **Sparks** | Living words; each has an **Ink** (element) | creatures you bond with, fight beside, evolve |
| **Codex** | A book bound to its owner; a bond writes a page | your team (3 active) + the Spark box |
| **Glyphs** | Single Script letters you can trace in battle | spells (heal, shield, trap, buff) |
| **Rewrite** | A Spark's page re-written with rare glyphs | evolution (the *_Evolved* / Big models) |
| **Sync** | During a fight, bond energy overflows | temporary evolution for ~20 s + a finisher |
| **The Blanking** | White light that unwrites a Spark: it turns grey and forgets itself | "Blanked" enemies; you can re-write them |
| **The White Page** | An order that believes words are wounds; masked **Erasers** | the antagonists |

Why the White Page exists (they are not cartoon villains): 30 years ago a **Script Surge** woke hundreds of wild Sparks at
once and drowned the town of Hollowmere. Its only survivor, **Mother Blanc**, founded the order: *no words, no wounds*.

## 3. Cast (the existing MetaHumans, re-cast)
| Model | Character | Role |
|---|---|---|
| player_m / player_f | **Mateo / Aoi** (you choose), 11 | the hero with the blank Codex |
| rho | **Rho Calder**, 12 | rival-friend: three pages on day one, loud, secretly scared of failing |
| mom | **Grace** | your mother, harbour lantern-keeper; knows more about your father's Codex than she says |
| vale | **Archivist Vivian Vale** | keeper of the **Scriptorium** (the old lab); runs the Rite of Pages |
| aide | **Scribe Kelvin** | Vale's assistant, comic relief, terrified of Sparks |
| fisher | **Old Walter "Gus"** | saw the White Page ships 30 years ago; the first to warn |
| kid | **Omari**, 9 | the village kid who follows you everywhere |
| merchant / gardener / conductor / guard | Zuri, Sunita, Jelena, **Captain Bruce** (harbour watch) | village life, side quests |
| crew_* | the **Pelling** fishing family, **Wren** and **Pip** (sailing) | the living harbour |
| (new) | **Mother Blanc** + **Erasers** | the White Page (white robes; masks later) |

## 4. Inks (elements) and type chart
Ember · Tide · Bloom · Volt · Stone · Gale · Wisp · Dusk.
Ember > Bloom > Tide > Ember; Volt > Tide, Gale; Stone > Volt, Ember; Gale > Bloom, Stone; Wisp > Stone; Dusk > Wisp; Wisp > Dusk (mutual).

## 5. The Sparks (41 models → original names)
| Model | Name → Rewrite | Ink |
|---|---|---|
| Flying/Dragon → Dragon_Evolved | **Cindril → Pyrevane** | Ember (starter) |
| Flying/Glub → Glub_Evolved | **Glublet → Gulfmaw** | Tide (starter) |
| Blob/Mushnub → Mushnub_Evolved | **Sporrow → Capsire** | Bloom (starter) |
| Flying/Armabee → Armabee_Evolved | **Zumblet → Voltqueen** | Volt |
| Flying/Goleling → Goleling_Evolved | **Pebblit → Bastolith** | Stone |
| Flying/Alpaking → Alpaking_Evolved | **Alpuff → Alpacrest** | Gale |
| Flying/Ghost → Ghost_Skull | **Wispet → Hollowisp** | Wisp |
| Big/Dino | **Rexmor** | Ember |
| Big/Demon | **Hornox** | Ember / Dusk |
| Blob/Fish → Big/Fish | **Finnip → Fangfin** | Tide |
| Big/Frog | **Croakra** | Tide |
| Flying/Squidle | **Tentra** | Tide |
| Blob/Cactoro → Big/Cactoro | **Pricklet → Saguardo** | Bloom |
| Blob/GreenBlob | **Mossle** | Bloom |
| Big/MushroomKing | **Myconarch** | Bloom |
| Blob/Chicken | **Sparkcluck** | Volt |
| Big/Birb | **Stormbill** | Volt / Gale |
| Flying/Hywirl | **Mindwhirl** | Wisp |
| Blob/Alien → Big/Alien | **Glimmo → Glimmaxx** | Wisp |
| Blob/Yeti → Big/Yeti | **Frostub → Yetrok** | Stone |
| Big/Monkroose | **Thumpkin** | Stone |
| Blob/GreenSpikyBlob | **Burrhook** | Stone |
| Flying/Pigeon | **Duskwing** | Dusk |
| Big/BlueDemon | **Gloomhorn** | Dusk |
| Blob/Cat | **Purrsk** | Gale |
| Blob/Dog | **Barklet** | Gale |
| Blob/Pigeon | **Coobit** | Gale |
| Blob/Birb | **Puffchirp** | Gale |
| Blob/PinkBlob | **Blushy** | Wisp |
| Big/Bunny | **Lopkin** | Gale |

## 6. Pact Battle (replaces turn-based card battles)
- Arena = where you meet the enemy (as now). Your Spark **auto-attacks** (basic hit every ~1.6 s).
- **3 Spark Arts** (keys 1/2/3 · gamepad X/Y/B), each with a cooldown; costs nothing — timing is the skill.
- **1 Codex Glyph** (Q): the glyph you equipped (Mend, Ward, Snare, Surge…), charges per battle.
- **Dodge** (Space): your Spark sidesteps; a dodge inside the enemy's red **telegraph** window = *Perfect* → counter-hit.
- **Sync gauge** fills with hits and Perfect dodges → **F = Rewrite-Sync**: the Spark becomes its evolved form for ~20 s and
  unlocks a **Finisher Art** (the evolved models we already have).
- **Writing a wild Spark** (= catching): weaken it, then hold E and trace its glyph (3-stroke QTE). Blanked (grey) Sparks can be
  re-written too — the hero's special power.
- Team of 3, **Tab** switches (2 s cooldown). Enemies telegraph their big Arts (red ring / line).
- Reuses what exists: arena placement, creature clips (attack / hit / death / happy), FX bursts, floaters, HP bars.

## 7. UI / GUI — "the Codex"
Parchment + ink + glowing glyph lines (gold for you, white for the White Page). HUD: Spark portrait in a round glyph frame,
Arts as glyph tiles with an ink cool-down sweep, Sync as ink filling a quill nib, dialogue on a torn page, menus as Codex pages
(Sparks · Glyphs · Map · Journal). The current glass/gold restyle becomes the base.

## 8. The intro (~3 min, live in-engine, Piper narration + orchestral music)
**Part I — The First Words** (stylised "ink myth", no faces needed)
1. Black. One glowing glyph draws itself. — *"Before the sea had a name, there was the Script."*
2. Glyph lines spread like ink over dark water; the islands appear as an ink map. — *"Every wave, every stone, every living thing… a word, in a language older than memory."*
3. Glyphs lift off the page and become silhouettes of Sparks (Cindril, Glublet, Zumblet). — *"Some words held so much meaning… that they woke up. We call them Sparks."*
4. A child's hand on a book; a silhouette curls around it. — *"And people learned to write beside them, in books that remember a bond."*
5. A white light sweeps across the ink; the silhouettes fade. — *"But some believe every word is a wound, waiting to open. They call themselves… the White Page."*
6. Title: **SIGIL & SPARK**.

**Part II — Lumen Harbor, dawn**
7. Dawn flight over the bay; the fishing boats head out (the real harbour simulation). — *"Lumen Harbor. Thirty years without a Blanking."*
8. Across the roofs and the turning windmills to the plaza. Caption: *The Rite of Pages.* — *"Today, every eleven-year-old receives a Codex."*
9. Rho's Codex flares gold, pages flutter. Vale: *"Rho Calder — three pages on the first day!"*
10. Your Codex opens… blank. A murmur. — *"And then there was you."*

**Part III — The White Page**
11. Fog rolls in; a white-sailed ship slides past the lighthouse. The harbour bell rings.
12. White light pulses on the pier; Sparks flee across the plaza; Gus shouts *"Not again…"*
13. In the Scriptorium the three starter Sparks break free; a white beam hits one; it falls at your feet.
14. Close-up: your blank Codex glows — the first glyph writes itself. — *"Some books are blank… because they haven't been written yet."*
15. → **Gameplay.**

## 9. Tutorial (gentle, step by step)
1. **Move** to the fallen Spark (WASD / stick).
2. **Choose** which starter to shield (Cindril / Glublet / Sporrow) — the bond writes your first page.
3. **First Pact Battle** vs a Blanked Spark: auto-attack, then *"Press 1 — Spark Art"*, then *"Space when the ring turns red — Dodge"*.
4. **Sync** prompt when the gauge fills → first Rewrite.
5. **Write** the Blanked Spark back (trace the glyph) — your second page.
6. Vale: the White Page took the Scriptorium's Codex archive → the journey begins (Route 1 → Mistvale).

## 10. Production plan (honest)
| Phase | Work | Size |
|---|---|---|
| 1 | narration with Piper (wav per line), intro engine (ink myth overlay + in-engine shots + fog/ship/white-light FX), title | ~1 day |
| 2 | Spark roster data (names, Inks, stats, Arts) replaces the card database in world, battle and UI | ~1 day |
| 3 | Pact Battle (real-time core, Arts, dodge, Sync, writing QTE) + tutorial | ~1–2 days |
| 4 | Codex UI/GUI restyle, Journal, menus | ~1 day |
Limits: MetaHuman faces have no expressions / lip-sync (JOINTS_ONLY rig) → the intro avoids talking close-ups; clothes still
the default garment until an outfit pack is added.

## 11. Open questions for the user
- Hero names: keep **Mateo / Aoi**, or let the player type a name?
- Starters: Cindril / Glublet / Sporrow OK?
- Tone: hopeful-adventurous (my pick) or darker?
- Anything from Pokébox to keep (e.g. the card binder as a collectible "Glyph cards")?
