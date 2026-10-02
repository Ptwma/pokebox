' Old launcher kept for existing shortcuts: it now just starts Pokebox.exe (the new one-click launcher).
Dim sh, fso: Set sh = CreateObject("WScript.Shell"): Set fso = CreateObject("Scripting.FileSystemObject")
sh.Run """" & fso.GetParentFolderName(WScript.ScriptFullName) & "\Pokebox.exe""", 1, False
