# Pokebox.exe launcher (Go, standard library only)

Rebuild (any OS with Go 1.24+), from this folder:

    GOOS=windows GOARCH=amd64 go build -trimpath -ldflags "-s -w -H windowsgui" -o ../../Pokebox.exe .

(on Windows cmd: `set GOOS=windows& set GOARCH=amd64& go build -trimpath -ldflags "-s -w -H windowsgui" -o ..\..\Pokebox.exe .`)

`rsrc_windows_amd64.syso` holds the icon; Go links it in automatically.

Behaviour: serves the POKEMON folder on http://localhost:5173 (fixed port = saves stay in the same origin),
reuses a running copy, opens Edge/Chrome in app mode (profile %LOCALAPPDATA%\PokeboxApp) straight into the game
(`?launch`), stops 3 min after the window is closed. `Pokebox.exe -debug` prints every request; log in
%LOCALAPPDATA%\PokeboxApp\launcher.log.
