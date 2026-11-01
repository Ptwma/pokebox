# Pact Battle: design v1 (for approval before building)

> Status: **paper design, 2026-11-01.** Nothing is built yet. It replaces the current turn-based `DoRound/PickMove` battle.
> Tone: the dark Sigil & Spark tone (red / black / white, ink and blood, no cute UI).
> Rule for this doc: every number is a starting value to tune in playtests. It is not final.

## 1. One-line pitch
Your Spark fights **on its own in real time**. You are the **Scribe**: you call the Arts, read the enemy's red warnings,
dodge at the right moment and write the finishing glyph. **Skill = timing, not menus.**

## 2. Controls

| Action | Keyboard / mouse | Gamepad | Notes |
|---|---|---|---|
| Move the Spark (strafe in the arena) | WASD | Left stick | It moves on a ring around the foe. It never walks out of the arena. |
| Spark Art 1 / 2 / 3 | 1 / 2 / 3 | X / Y / B | Each Art has its own cooldown. No mana. |
| Codex Glyph | Q | LB | Charges per battle (2 by default). |
| Dodge | Space | A | 0.35 s of i-frames. 0.9 s cooldown. |
| Rewrite-Sync | F | LT + RT | Only works when the Sync gauge is full. |
| Write (catch) | Hold E | Hold RB | Wild Sparks only, under 25% HP. |
| Switch Spark | Tab | D-pad left/right | 2 s cooldown. The incoming Spark gets 0.5 s of i-frames. |
| Run away | Esc, then "Flee" | Start | Wild battles only. Fails 1 in 4 against Blanked Sparks. |

The basic attack is automatic: one hit every **1.6 s** while the foe is in range. The player never presses a button for it.

## 3. The loop (one fight ≈ 45–90 s)
1. **Open.** The Spark auto-attacks. The player uses Arts as they come off cooldown.
2. **Telegraph.** The foe winds up a big Art. A **red ink ring** or **red line** is drawn on the ground. It fills over **0.8–1.2 s**.
3. **Read and dodge.**
   - Dodge in the **last 0.25 s** of the fill = **PERFECT**: slow motion for 0.3 s, a white impact frame, an automatic counter-hit (150% of the basic attack) and +15 Sync.
   - Dodge too early = a normal dodge with no bonus.
   - Getting hit = full damage and a 0.4 s stagger.
4. **Sync.** The gauge fills from hits dealt (+3), Perfects (+15) and damage taken (+2).
   - When it is full: **F**. The camera cuts close, a page of the Codex burns red and the Spark **Rewrites** into its Evolved model for **20 s**.
   - The Rewrite gives +35% damage, Arts cooling down 2× faster, and one **Finisher Art** (key 4 / RB).
5. **End.**
   - **Trainer battle:** KO all of the opponent's Sparks.
   - **Wild battle:** KO it, or **Write** it (§6).
   - **Blanked Spark:** it can *only* be Written back. A KO makes it dissolve into white paper, with no reward. This is the hero's special power and the moral hook.

## 4. Arts (3 per Spark + 1 Finisher)
Each **Ink** (type) gets three Art templates. A Spark draws its three from its Ink, plus one secondary.

| Template | Role | Cooldown | Example (Ember) | Example (Tide) |
|---|---|---|---|---|
| **Strike** | fast single hit, 140% | 4 s | Cinder Script | Undertow |
| **Burst** | AoE around itself or a cone, 220%, 0.4 s wind-up | 9 s | Wyrmfire | Riptide Page |
| **Utility** | Shield / slow / pull / bleed | 12 s | Scorch (a burning bleed for 4 s) | Hush (slows the foe for 3 s) |
| **Finisher** (Rewrite only) | cinematic hit, 500%, one per Rewrite | n/a | Ash Chapter | Drowned Verse |

Ink advantages stay as they are now (×1.5 / ×0.66), shown as **red** (strong) or **grey** (weak) damage numbers.
Status effects:
- **Bleed**: red drips on the HP bar.
- **Slow**: ink chains.
- **Blank**: the foe's Arts are greyed out for 3 s. It is the White Page's own move and the bosses use it.

## 5. Codex Glyphs (Q)
These are collected from the glowing stones found in the world. You equip one; it has 2 charges per battle.

| Glyph | Effect | Unlock |
|---|---|---|
| **Mend** | heals 30% of max HP over 3 s | start |
| **Ward** | blocks the next hit completely (a white page shield) | Route 1 stone |
| **Snare** | roots the foe for 2.5 s. Writing is easier while it is snared. | Mistvale |
| **Surge** | the next Art does ×2 and adds +20 Sync | Chapter 2 |

## 6. Writing (= catching)
- Available when a wild Spark is **under 25% HP** (its HP bar shows a white quill icon).
- **Hold E** and time slows to 30%. The Spark's glyph appears as **3 strokes**.
- Each stroke is a moving dot along a path. Trace it with the mouse or the right stick. Keyboard fallback: press the 3 arrows in the order shown.
- Success chance = base by rarity (60 / 45 / 30 %) + 25% if Snared + 10% per stroke traced cleanly. It costs **1 Binding Ink**.
- Failure: the Spark breaks free, gets +10% HP back and can't be Written again for 8 s.
- **Blanked Spark:** the strokes are drawn in **white on black** and success is guaranteed (story). Its colour floods back. That is the "page" reward.

## 7. Enemy AI (simple, readable)
- **Wild:** basic attack, plus one telegraphed Art every 6–9 s.
- **Trainer:** two Arts plus a switch when at 30% HP. One telegraphed Art every 5–7 s.
- **Blanked:** its telegraphs are **white**, not red, and **faster** (0.6 s). It also uses *Blank* once per fight.
- **Bosses (Eraser captains):**
  - Phase 2 at 50% HP: the arena edge burns red and the ring shrinks.
  - Two overlapping telegraphs, so the player has to choose which one to dodge.

## 8. HUD (crimson style, matching the intro)
```
 ┌──────────────────────────────────────────────────────────────────────┐
 │  FOE NAME  Lv 7  [██████████░░░░░] ✒ (writable)          ◢ BLANKED ◣│  top: foe bar, red ink on black
 │                                                                      │
 │                     (arena, red telegraph rings on the ground)        │
 │                                                                      │
 │ ◯ portrait   CINDRIL Lv 8                                            │
 │ [████████████░░░] HP     ▲ SYNC (quill nib filling with red ink)     │  bottom left: your Spark
 │  [1 Cinder] [2 Wyrmfire] [3 Scorch]  [Q Mend ●●]   [Space]  [F]      │  Art tiles: black, white glyph,
 │                                                                      │  red cooldown sweep
 └──────────────────────────────────────────────────────────────────────┘
```
- Damage numbers: white. Red for advantage, grey for resisted. PERFECT is a big white brush word with a red slash, like the intro title.
- Every big moment uses an impact frame (one inverted frame) and a screen shake. The Finisher gets the intro's bloom and ink border.

## 9. Tutorial (Chapter 1, the first fight vs the Blanked Spark at the Scriptorium)
Each step waits until the player does the action. No walls of text, one line at a time:
1. *"Your Spark fights on its own. Watch."* The auto-attack runs for 3 s.
2. *"Press 1: Cinder Script."* It is the only key that works until the player presses it.
3. *"The ink turns red: it is about to strike. Space, now."* The first telegraph is slowed down. A dodge at any point counts as a Perfect.
4. *"The Sync is full. Press F: Rewrite."* The gauge is pre-filled for the tutorial.
5. *"It is Blank, not dead. Hold E and write it back."* A guaranteed Write. The Spark's colour returns and you get your 2nd page.

## 10. What we reuse (keeps it buildable)
- The arena staging (`SetupStage`, `ClearStage`, cinematic camera), creature clips (attack / hit / death / happy), FX bursts (`HitFX`), the blood bursts, floaters and HP plates.
- The Evolved / Big models already in creatures.json are the Rewrite forms.
- The data: `FPBXCardDef` HP / Atk / Spd → HP, damage and basic-attack interval.

## 11. Build plan (phase 3)
| Step | Work | Est. |
|---|---|---|
| 3a | Real-time core: a battle tick, auto-attack, the 3 Arts with cooldowns, damage and Ink, KO. The turn system is switched off. | 3–4 h |
| 3b | Telegraphs (ground decal rings and lines), dodge and i-frames, PERFECT with slow-mo and an impact frame, the counter. | 3 h |
| 3c | Sync gauge, Rewrite (swap to the Evolved model, 20 s timer), Finisher | 2 h |
| 3d | Writing QTE (3 strokes, mouse / stick / arrows) and Glyphs (Q) | 3 h |
| 3e | Crimson HUD (Slate) | 2–3 h |
| 3f | Tutorial script and **autotest bot** (it dodges on telegraph, uses Arts on cooldown, Writes under 25%) | 2 h |
| | **Total** | **~1.5–2 days** |

## 12. Risks (the hard truth)
- **Creature animations are thin.** Most models have only attack, hit, death and idle clips. Arts will look alike unless the FX carry them: a different burst, colour and camera move per Art. I'd rather fake it with FX than promise unique animations.
- **Real-time breaks the autotest.** The turn-based autotest passes today (75/76). Without the bot in 3f the whole chapter can't be tested automatically. The bot is mandatory, not optional.
- **The difficulty curve is a playtest job.** I can set sane numbers, but only playing it tells whether 0.25 s for a Perfect is too hard on a gamepad.
- **Writing with the mouse vs a gamepad.** Tracing with a stick is awkward. That is why the arrow and D-pad fallback exists. If it feels bad, it becomes a 3-button timing QTE.

## 13. Questions for you (answer and I build)
1. **Speed:** the 1.6 s auto-attack with fights of ~60 s, or faster (1.1 s, ~35 s fights)?
2. **Movement:** can the player move the Spark (WASD strafe), or does it stand still and only dodge? Standing still is simpler and more readable; moving is more action.
3. **Team switching (Tab)** in Chapter 1, or locked until you have 2+ Sparks?
4. **Writing QTE:** tracing strokes (cooler, harder), or 3 timed button presses (simpler)?
5. **Blanked KO:** OK that it gives *nothing* and dissolves? This is a moral choice the game punishes softly.
