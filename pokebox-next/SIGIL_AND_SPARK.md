# SIGIL & SPARK — story, systems and intro (v2, 2026-11-01 — DARK)

> **v2 decisions (user 2026-11-01):** cards are GONE completely (pure gameplay game, nothing kept from the card game);
> new hero names (Asta-like but original) → **Rook** (he) / **Vesna** (she), **16**; tone = **adventure with darkness,
> blood, alone** (Expedition 33 mood: loss, melancholy, a cost to every victory). Rho is 16 too.
> What changed in the story: the Blanking is not a threat any more, it HAPPENED — the night of the Rite half of Lumen
> Harbor was Blanked (alive, white, wordless): your mother Grace, little Omari, Sunita, Zuri. Rho's parents too; the
> Erasers tore two pages out of his Codex and he blames your blank book. Vale is wounded. You set out alone.
> In game (r62): Blanked people = chalk-white overlay (M_PBX_Blanked), frozen, they don't turn or answer (narrated
> lines); blood bursts on every hit and a pool on a KO; a closing intro shot + narration (vo_intro_15); all ch.1
> dialogue rewritten in this tone.

> Replaces the Pokébox / Pokémon-card story. Same world (Veyra, Lumen Harbor, the lighthouse island, Route 1 → Mistvale), same
> MetaHuman cast, same 41 creatures (Quaternius CC0) — new story, names, battle, UI, intro and tutorial. All names and designs
> are original. The *feeling* borrows from Black Clover (an underdog with a strange magic book), Pokémon (bond, collect,
> evolve) and Digimon (evolution inside the fight) — nothing is copied.
> User decisions (2026-10-31): story **C — Sigil & Spark**, battle **Pact Battle** (semi-real-time), intro **live in-engine**,
> narration **offline TTS** — final: **Kokoro-82M voice "A" = `am_michael*0.7 + am_onyx*0.3`** (Apache-2.0, local), speed 0.92,
> whole sentences per call, 0.42 s between sentences (the user asked for a calm, solemn *cadence*, not anyone's voice). Tool: `tools/pbx_kokoro.py`.

---

## 1. Pitch
The world was *written*. Every wave, stone and living thing is a word in the **Script**, a language older than memory.
Some words became so full of meaning that they woke up: the **Sparks**. People learned to bond with them in a **Codex**,
half spellbook, half instrument, whose pages write themselves when a bond is made.
On the day every sixteen-year-old receives a Codex, yours opens **blank**. That same day the **White Page** comes to Lumen
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
| player_m / player_f | **Rook / Vesna** (you choose), 16 | the harbour lantern-keeper's child with the blank Codex; mother Blanked; alone |
| rho | **Rho Calder**, 16 | rival: three pages on day one — two torn out by the Erasers, parents Blanked; blames you, fights you for your book, leaves alone |
| mom | **Grace** | your mother — **Blanked** on the first night; pours tea for no one; the reason you go on |
| vale | **Archivist Vivian Vale** | keeper of the **Scriptorium** (the old lab); runs the Rite of Pages |
| aide | **Scribe Kelvin** | Vale's assistant, comic relief, terrified of Sparks |
| fisher | **Old Walter "Gus"** | saw the White Page ships 30 years ago; the first to warn |
| kid | **Omari**, 9 | the village kid who said "blank is cool" — **Blanked** |
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

### 5b. In the game now (phase 2, r61) — card id → Spark
The card ids stay (saves store them); names, Inks, models and Art names are new. Card scans are no longer shown anywhere
(the starter choice and Vale's table show the 3D Sparks).
| Card id (internal) | Spark | Ink | Model |
|---|---|---|---|
| Bulbasaur_MEW_001 / Charmander_MEW_004 / Squirtle_PGO_015 | Sporrow / Cindril / Glublet (starters) | Bloom / Ember / Tide | Blob/Mushnub, Flying/Dragon, Flying/Glub |
| Pidgey_OBF_162, Lechonk_PAF_071, Starly_SVI_148, Jigglypuff_MEW_039, Spearow_MEW_021 | Coobit, Barklet, Puffchirp, Blushy, Purrsk | Gale ×4, Wisp | Blob/Pigeon, Dog, Birb, PinkBlob, Cat |
| Eevee_MEW_133 (Rho) | Alpuff | Gale | Flying/Alpaking |
| Route 1: Pidgey/Pidgeotto/Rattata/Caterpie/Metapod/Weedle/Kakuna/NidoranF/NidoranM/Oddish/Pikachu (MEW) | Duskwing, Stormbill, Frostub, Mossle, Pricklet, Burrhook, Pebblit, Glimmo, Sparkcluck, Croakra, Zumblet | Dusk, Volt, Stone, Bloom, Bloom, Stone, Stone, Wisp, Volt, Tide, Volt | Flying/Pigeon, Big/Birb, Blob/Yeti, Blob/GreenBlob, Blob/Cactoro, Blob/GreenSpikyBlob, Flying/Goleling, Blob/Alien, Blob/Chicken, Big/Frog, Flying/Armabee |
Arts: Cinder Script, Undertow, Rootdrink, Static Sigil, Hush, Rockbreak, Nightquill, Bulwark, Wyrmfire, Gust Rune.
Items: Poké Ball → **Binding Ink**, Potion → **Mending Tea**. Player = **Scribe** (Rook / Vesna). Lab = **the Scriptorium**.
Dialogue rewritten for the day after the intro (the Blanking happened yesterday; Vale reads your First Page; you shield a starter).

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
8. Across the roofs and the turning windmills to the plaza. Caption: *The Rite of Pages.* — *"Today, every sixteen-year-old receives a Codex."*
9. Rho's Codex flares gold, pages flutter. Vale: *"Rho Calder — three pages on the first day!"*
10. Your Codex opens… blank. A murmur. — *"And then there was you."*

**Part III — The White Page**
11. Fog rolls in; a white-sailed ship slides past the lighthouse. The harbour bell rings.
12. White light pulses on the pier; Sparks flee across the plaza; Gus shouts *"Not again…"*
13. In the Scriptorium the three starter Sparks break free; a white beam hits one; it falls at your feet.
14. Close-up: your blank Codex glows — the first glyph writes itself. — *"Some books are blank… because they haven't been written yet."*
14b. (v2) White wipe over black. — *"By morning, half of Lumen Harbor had forgotten its own name. Only you were left… unwritten."*
15. → **Gameplay.**

**Subtitles (user 2026-10-31):** every narrated line and every spoken line in the intro is subtitled at the bottom of the frame
(white on a soft dark band, timed to the narration wav), skippable with E; the tutorial prompts appear as on-screen hints.

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
| 1 ✅ | narration (Kokoro), intro engine (ink myth overlay + in-engine shots + fog/ship/white-light FX), title | ~1 day |
| 2 ✅ (r61, data + text; battle is still turn-based) | Spark roster data (names, Inks, stats, Arts) replaces the card database in world, battle and UI | ~1 day |
| 3 | Pact Battle (real-time core, Arts, dodge, Sync, writing QTE) + tutorial | ~1–2 days |
| 4 | Codex UI/GUI restyle, Journal, menus | ~1 day |
Limits: MetaHuman faces have no expressions / lip-sync (JOINTS_ONLY rig) → the intro avoids talking close-ups; clothes still
the default garment until an outfit pack is added.

## 11. Answered (2026-11-01)
- Hero names → **Rook / Vesna** (16). Starters Cindril / Glublet / Sporrow kept. Tone → **dark adventure, blood, alone**.
- Cards → **nothing kept**.
