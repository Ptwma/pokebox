@echo off
rem Pokebox - starts the game with a visible log, so any error can be read.
echo Starting Pokebox in debug mode (every file request is listed below)...
echo Close the game window, then this window, to stop.
"%~dp0Pokebox.exe" -debug
echo.
echo Log file: %LOCALAPPDATA%\PokeboxApp\launcher.log
pause
