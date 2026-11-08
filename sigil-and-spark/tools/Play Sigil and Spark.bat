@echo off
rem Sigil & Spark - plays the latest version of the project directly (no packaging). Put next to SigilAndSpark.uproject.
start "" "C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe" "%~dp0SigilAndSpark.uproject" -game -windowed -ResX=1600 -ResY=900
