@echo off
powershell -NoProfile -ExecutionPolicy Bypass -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\Pokebox.lnk'); $s.TargetPath='%~dp0Pokebox.exe'; $s.WorkingDirectory='%~dp0'; $s.IconLocation='%~dp0Pokebox.exe,0'; $s.Description='Pokebox'; $s.Save()"
echo Pokebox shortcut (Pokebox.exe) created on your Desktop.
pause
