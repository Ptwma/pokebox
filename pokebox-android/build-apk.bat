@echo off
setlocal
title Pokebox - build Android APK
cd /d "%~dp0"
echo ============================================================
echo  Pokebox for Android - building the APK
echo ============================================================

rem --- Java: the one bundled with Android Studio
set "JAVA_HOME=%ProgramFiles%\Android\Android Studio\jbr"
if not exist "%JAVA_HOME%\bin\java.exe" set "JAVA_HOME=%LOCALAPPDATA%\Programs\Android Studio\jbr"
if not exist "%JAVA_HOME%\bin\java.exe" (
  echo [!] Android Studio was not found. Install it from https://developer.android.com/studio and open it once.
  pause & exit /b 1
)
rem --- Android SDK (installed by Android Studio's first-run wizard)
if "%ANDROID_HOME%"=="" set "ANDROID_HOME=%LOCALAPPDATA%\Android\Sdk"
if not exist "%ANDROID_HOME%\platforms" (
  echo [!] Android SDK not found in %ANDROID_HOME%. Open Android Studio once so it installs the SDK.
  pause & exit /b 1
)
set "SDKESC=%ANDROID_HOME:\=\\%"
> local.properties echo sdk.dir=%SDKESC%

echo.
echo [1/3] Preparing game files and phone-sized card images...
powershell -NoProfile -ExecutionPolicy Bypass -File "tools\prepare-android.ps1"
if errorlevel 1 goto fail
if not exist "app\src\main\assets\www\pokebox-game\index.html" (
  echo [!] The game files were not copied into the app. Check that ..\pokebox-game exists.
  goto fail
)

echo.
echo [2/3] Building (the first build downloads Gradle and libraries, needs internet)...
call gradlew.bat assembleRelease --no-daemon --warning-mode=summary
if errorlevel 1 goto fail

echo.
echo [3/3] Copying the APK...
if not exist "app\build\outputs\apk\release\app-release.apk" goto fail
copy /y "app\build\outputs\apk\release\app-release.apk" "..\Pokebox.apk" >nul
for %%A in ("..\Pokebox.apk") do echo  APK size: %%~zA bytes
echo.
echo  DONE:  %~dp0..\Pokebox.apk
echo  Copy it to your phone (USB, Drive, Quick Share...) and open it to install.
echo  Android will ask to allow "install unknown apps" for the app you open it with - allow it once.
pause
exit /b 0
:fail
echo.
echo [!] Build failed - scroll up for the error, or send a screenshot to Claude.
pause
exit /b 1
