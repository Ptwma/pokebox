# Pokebox for Android

The whole game runs **offline** inside the app (WebView + WebGL2). Landscape, fullscreen, touch controls.

## Build the APK (Windows, Android Studio installed)
1. Double-click `build-apk.bat`.
2. First run: converts the 20,731 card images to phone size (a few minutes) and downloads Gradle (internet needed).
3. Result: `..\Pokebox.apk` (next to this folder). Copy it to the phone and open it to install.

Re-run `build-apk.bat` after any game change — only changed files are re-copied.

## What the app does
- Opens straight into the game (no start screen), fullscreen landscape, offline.
- Files are served from the APK on `https://appassets.androidplatform.net/` (ES modules, workers, WASM all work).
- Saves live in the app's WebView storage; they are flushed when the app goes to the background.
- The activity source is in `src-java\com\pokebox\game\MainActivity.java` (the old `app\src\main\java` copy is no longer used).

## Notes
- Card images are 320 px JPEG q70 (~350-450 MB total). Change with `tools\prepare-android.ps1 -Width 360 -Quality 75`.
- Debug from the PC: phone on USB -> Chrome -> `chrome://inspect`.
- Android Back button = Esc (menu).
