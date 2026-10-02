# Pokebox — Tech & Quality Roadmap ("toward Palworld feel")

> Researched Sept 2026. Owner: Icon. Status of each item: ✅ done · 🔜 next · 🧊 later / needs a decision.

## 1. The honest gap
Palworld is a UE5 game made by a studio of ~40–60 people over years, with custom-modelled, rigged and animated creatures,
full physics, AI, base building and co-op servers. A browser game written in plain JS by one person + Claude cannot reach
that *scope*. What it **can** reach is the *feel* of the first 10 minutes: a stylised world that moves, animated
characters, a creature companion following you, readable combat, satisfying feedback, and a progression loop.
The two things that decide visual quality are **(a) art assets** and **(b) animation** — not the engine.

Hard limits that no library fixes:
- **No 3D Pokémon models.** Official models are Nintendo/Game Freak IP; ripped models are illegal to distribute and
  fan models need per-model permission. That is why Pokémon appear as Lattice holograms (card art projections) —
  it is also canon in our Story Bible (Echo projections).
- **One artist-less team.** Everything visual must come from CC0 packs (KayKit, Quaternius, Kenney, Poly Haven) or be procedural.

## 2. Library stack (researched)
| Need | Pick | Why / status |
|---|---|---|
| Renderer | **three.js r170 (WebGL2)** | ✅ in use. WebGPU renderer + TSL is production-usable in 2026, but WebGL2 is safer on older GPUs; revisit 🧊 when we need GPU-compute grass/particles. |
| Model loading | **GLTFLoader + SkeletonUtils** (three addons) | ✅ vendored (`vendor/three/addons/loaders`, `utils`). |
| Asset pipeline | **gltf-transform** (CLI, Node) | ✅ used to strip 75 animations → 16 shared clips, drop weapons, dedup: 18 MB → 1.7 MB. Add meshopt/KTX2 compression 🔜 when assets grow past ~10 MB. |
| Characters | **KayKit Adventurers (CC0)** — 5 rigged chibi bodies, one shared rig | ✅ player + all NPCs; trainer look repaints skin/hair/outfit atlas cells + hats on the head bone. |
| Animation | **THREE.AnimationMixer** crossfades (Idle/Walk/Run speed-matched, Interact, PickUp, Cheer, Spellcast) | ✅ |
| Physics / controller | **Rapier** (`@dimforge/rapier3d-compat`, WASM) — kinematic character controller | 🧊 only needed for jumping, slopes, climbing, throwing objects. Our heightfield + circle colliders are cheaper and enough for walking. |
| Raycasts on big meshes | **three-mesh-bvh** | 🧊 needed once we import large glTF environments (camera collision, click-to-walk on props). |
| Post-processing | **pmndrs/postprocessing** (SMAA, SSAO/N8AO, bloom, tone mapping) | 🔜 the next biggest visual jump in the world (ambient occlusion + outline). Cost: 2–4 ms/frame; must be optional. |
| Grass / foliage | custom instanced shader | ✅ wind + player push, one draw call per area (6k–26k blades). |
| Shadows | three.js directional shadow following the player | ✅ auto-disabled by the adaptive-quality loop and in Settings. |
| Creature/NPC AI | **Yuka** (steering, FSM, pathfinding) | 🔜 for Echoes that wander, flee and chase instead of drifting on sine waves. |
| Audio | **Howler.js** (sprites, 3D panning) + CC0 SFX (Kenney, Sonniss GDC bundles) | 🔜 our Web Audio synth is fine for UI but ambience/footsteps need real samples. |
| Environment art | **Quaternius Stylized Nature MegaKit**, **KayKit Forest/City bits**, **Kenney** | 🔜 replace primitive trees/houses. Quaternius files are on quaternius.com / itch (manual download by Icon, then Claude converts). |
| Creatures (non-Pokémon) | **Quaternius Ultimate Monsters (CC0, 45 rigged, animated)** | 🧊 could become "wild Echo husks" (data creatures) — story-consistent, but a style decision. |
| Sky / light | Poly Haven HDRIs (CC0) | 🧊 only if we move to PBR; toon look doesn't need it. |
| Engine switch | **Godot 4** (free, exports to web/desktop) | 🧊 the realistic path if the goal becomes a real open-world game (capture, base building, co-op). Big rewrite. |

## 3. Done in this pass
1. Rigged, animated characters (player + 11 NPCs) with speed-matched locomotion and gestures.
2. Trainer look → 3D: outfit picks the body, colours repaint the model; hats/accessories on the head bone; 3D turntable in the Trainer tab.
3. **Partner projection**: your team lead follows you as a Lattice hologram (Palworld-style companion), leans toward nearby Echoes.
4. **Wild Echoes show the actual card** you will fight (glitched projection) — the battle uses that exact card and you win that card.
5. Wind-swept instanced grass + tall reeds, soft real-time shadows, camera-follow shadow frustum.

## 4. Next steps, in order of impact per hour
1. 🔜 Environment kit: Icon downloads *Stylized Nature MegaKit* (Quaternius) → Claude converts & swaps trees/rocks/houses.
2. 🔜 Post FX in the world: N8AO + SMAA + subtle outline (toggle).
3. 🔜 Echo behaviour with Yuka: wander / notice / approach; partner reacts; a short "capture" minigame (stabilise the Echo) before the card battle.
4. 🔜 Real-time in-world battle intro: camera swings, partner hologram and Echo face off, then transition to the card battle.
5. 🔜 Audio pass with Howler + CC0 ambience per area.
6. 🧊 Day/night cycle tied to the Moonlight pack event.
7. 🧊 Decide: stay in the browser (stylised, personal) or port to Godot (real game scope).
