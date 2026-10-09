@echo off
rem Pokebox Next - plays the latest version of the project directly (no packaging). Put next to PokeboxNext.uproject.
start "" "C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe" "%~dp0PokeboxNext.uproject" -game -windowed -ResX=1600 -ResY=900
