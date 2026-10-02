# Pokebox

A Pokémon-style card collecting game with an open 3D world (three.js), for **Windows** and **Android**.

## Play
- **PC:** download `Pokebox.exe` and `pokebox-game-<version>.zip` from the [latest release](../../releases/latest), unzip into a folder named `pokebox-game`, put `Pokebox.exe` inside it and double-click it. The card images (`pokemon-card-scraper/pokemon_cards/images/`) are **not** part of this repository and must sit next to the `pokebox-game` folder.
- **Android:** build the APK with `pokebox-android/build-apk.bat` (needs Android Studio and the card images).

## Updates
Both apps check this repository's latest release on start and **ask** before updating. Saves are never touched.

To publish an update: change the code, raise `"version"` in `pokebox-game/version.json` (and add `"notes"`), push to `main`.
GitHub Actions (`.github/workflows/release.yml`) builds the zip, `Pokebox.exe` and `latest.json` and creates the release.
- Changed the launcher (`pokebox-game/tools/launcher`)? Also raise `"launcher"` — PCs then replace their `Pokebox.exe`.
- Changed the Android Java code? Raise `versionCode` in `pokebox-android/app/build.gradle` and `"minApk"` to the same number — the app then asks for a new APK instead of a silent content update.

## Layout
| Folder | What |
|---|---|
| `pokebox-game/` | the game (HTML/JS/CSS, three.js, assets) |
| `pokebox-game/tools/launcher/` | `Pokebox.exe` source (Go, stdlib only) — local server + updater |
| `pokebox-android/` | Android WebView app + in-app updater (`src-java/`) |

Not affiliated with Nintendo, Creatures, GAME FREAK or The Pokémon Company. Fan project, no commercial use.
Third-party asset licences are in `pokebox-game/assets/LICENSE-*.txt`.
