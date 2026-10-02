@echo off
title Pokebox HD cards
echo Fast (2x, about 1-3 hours) or Max (4x, much slower)?
choice /c FM /n /m "Press F for Fast or M for Max: "
if errorlevel 2 (set Q=max) else (set Q=fast)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0upscale.ps1" -Quality %Q%
