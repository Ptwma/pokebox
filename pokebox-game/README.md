# Pokebox — local collector game

**Start:** double-click `start.bat`. A small window (the local server) opens and the game loads in your browser at
http://localhost:5173/pokebox-game/index.html. Close that window to stop the game. Your progress is saved in the browser automatically.

Keep this folder inside `POKEMON` next to `pokemon-card-scraper` — the game reads all 20,731 card images straight from there.

## What's in it
- **Shop** – 128 real sets with their booster art. 7 cards per pack (3 common, 2 uncommon, 1 bonus, 1 hit — the hit is always last).
  Hit odds: Rare 60% · Holo 22% · Ultra 10.5% · Illustration 5% · Secret 2.5%. "×5 quick" opens five packs instantly.
- **3D opening** – the animation recreated from your GIF (mystery pack spin, push-in, tear, light burst, card rise).
  Tap / Space for each next card. Ultra Rare+ hits get a card-back flip, light burst and sound. "Skip to results" anytime.
- **Binder** – every set, missing cards as silhouettes, set-completion bonus coins.
- **Collection** – filter by rarity / type / name, sort by value, sell duplicates.
- **Market** – daily prices move per card (30-day chart on every card), 12 new singles for sale each day, portfolio chart.
- **Battle** – 3 Pokémon vs 8 trainers (Youngster → Champion). Speed decides who hits first, type weakness ×1.5,
  attacks build energy, 2 energy = Power move (×1.9), Guard halves damage. Wins pay coins and free packs.
- **Daily reward** – coins (grows with your streak) + 1 free pack. Achievements pay coins.
- **Profile** – settings (sound, mystery intro, skip animation, pink/dark studio), export / import / reset save.

## Honest notes
- Rarity, HP, attack and prices are *generated* (the scraper has no rarity or stats): rarity from card number position,
  name tags (ex, V, GX, VMAX…) and era; values from rarity × popularity × era. It's consistent, not official.
- Pack art exists for 128 sellable sets; promo/kit sets have no packs and show up on the Market instead.
- Don't publish the card images or pack art in a public repo — keep the GitHub repo private or exclude `assets/sets`
  and the scraper folder.

`opening.html` is the standalone step-1 animation demo.
