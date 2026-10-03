// Pokebox.exe — one-click launcher for the PC version of Pokebox.
//
// What it does:
//  1. serves the POKEMON folder (the folder that contains pokebox-game\ and pokemon-card-scraper\) on
//     http://localhost:5173 — ALWAYS this port, because the browser keeps the saves (localStorage) per origin;
//     a different port would open the game with an empty save.
//  2. if Pokebox is already running (port answers /__ping), it just opens another window instead of failing.
//  3. opens the game straight in (no start screen: ?launch) in an app window: Edge → Chrome → default browser,
//     with its own profile in %LOCALAPPDATA%\PokeboxApp (same profile as the old Pokebox.vbs → same saves).
//  4. shuts itself down when the game window is closed (no request for IdleTimeout; the game pings every 20 s).
//
// Build (from this folder):  GOOS=windows GOARCH=amd64 go build -trimpath -ldflags "-s -w -H windowsgui" -o Pokebox.exe
// Debug: run `Pokebox.exe -debug` from a terminal (prints every request) — start-debug.bat does this.
package main

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"io"
	"log"
	"mime"
	"net"
	"net/http"
	"os"
	"os/exec"
	"path"
	"path/filepath"
	"runtime"
	"strings"
	"sync/atomic"
	"time"
)

const (
	Port        = 5173
	StartPath   = "/pokebox-game/index.html?launch"
	IdleTimeout = 3 * time.Minute // background tabs may throttle the 20 s ping to once a minute
)

// Version of the launcher; release builds set it from version.json ("launcher") with -ldflags "-X main.Version=…"
var Version = "2.1"

var (
	debug    = flag.Bool("debug", false, "log every request to the console")
	noOpen   = flag.Bool("noopen", false, "only run the server, don't open a window")
	lastHit  atomic.Int64
	logFile  io.Writer = io.Discard
	gameRoot string    // ...\POKEMON
	gameDir  string    // ...\POKEMON\pokebox-game
	exePath  string
)

var types = map[string]string{
	".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".mjs": "text/javascript; charset=utf-8",
	".css": "text/css; charset=utf-8", ".json": "application/json; charset=utf-8", ".webmanifest": "application/manifest+json",
	".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif", ".avif": "image/avif",
	".svg": "image/svg+xml", ".ico": "image/x-icon", ".mp3": "audio/mpeg", ".wav": "audio/wav", ".ogg": "audio/ogg",
	".glb": "model/gltf-binary", ".gltf": "model/gltf+json", ".bin": "application/octet-stream", ".ktx2": "image/ktx2",
	".hdr": "application/octet-stream", ".wasm": "application/wasm", ".onnx": "application/octet-stream",
	".woff2": "font/woff2", ".woff": "font/woff", ".txt": "text/plain; charset=utf-8", ".md": "text/plain; charset=utf-8",
}

func main() {
	flag.Parse()
	if *debug {
		attachConsole()
	}
	exe, _ := os.Executable()
	exe, _ = filepath.EvalSymlinks(exe)
	exePath = exe
	gameDir = filepath.Dir(exe)
	// the exe normally sits in POKEMON\pokebox-game; also accept being placed in POKEMON itself
	if fileExists(filepath.Join(gameDir, "index.html")) {
		gameRoot = filepath.Dir(gameDir)
	} else if fileExists(filepath.Join(gameDir, "pokebox-game", "index.html")) {
		gameRoot = gameDir
		gameDir = filepath.Join(gameDir, "pokebox-game")
	} else {
		fatal("Pokebox.exe must stay inside the pokebox-game folder (next to index.html).\n\nIt is now in:\n" + gameDir)
	}

	prof := filepath.Join(os.Getenv("LOCALAPPDATA"), "PokeboxApp")
	_ = os.MkdirAll(prof, 0o755)
	if f, err := os.OpenFile(filepath.Join(prof, "launcher.log"), os.O_CREATE|os.O_WRONLY|os.O_TRUNC, 0o644); err == nil {
		logFile = f
		defer f.Close()
	}
	var w io.Writer = logFile
	if *debug {
		w = io.MultiWriter(logFile, os.Stdout)
	}
	log.SetOutput(w)
	log.SetFlags(log.Ltime)
	log.Printf("Pokebox launcher %s (%s) root=%s", Version, runtime.Version(), gameRoot)
	cleanupOldExe()
	if v := os.Getenv("POKEBOX_UPDATE_BASE"); v != "" { // tests only: a local fake GitHub
		UpdateBase = v
	}

	url := fmt.Sprintf("http://localhost:%d%s", Port, StartPath)
	lns, err := listen()
	if err != nil {
		// already running? then just open a window on the running copy
		if pokeboxRunning() {
			log.Printf("Pokebox is already running on port %d — opening a window", Port)
			if !*noOpen {
				openWindow(url, prof)
			}
			return
		}
		fatal(fmt.Sprintf("Pokebox needs port %d, but another program is using it.\n\nClose that program (or restart the PC) and start Pokebox again.\n\nDetails: %v", Port, err))
	}

	srv := &http.Server{Handler: http.HandlerFunc(handle), ReadHeaderTimeout: 10 * time.Second}
	for _, ln := range lns {
		go func(ln net.Listener) {
			if err := srv.Serve(ln); err != nil && !errors.Is(err, http.ErrServerClosed) {
				log.Printf("serve %s: %v", ln.Addr(), err)
			}
		}(ln)
	}
	lastHit.Store(time.Now().UnixNano())
	log.Printf("serving on %v", addrs(lns))

	if !*noOpen {
		// a newer game on GitHub? install it before the window opens, so the player always plays the latest version
		// without having to click anything (the window shows a small progress page meanwhile)
		target := url
		if os.Getenv("POKEBOX_NO_AUTOUPDATE") == "" {
			if info := checkUpdate(); info["newer"] == true {
				updMu.Lock()
				lat := updLatest
				updMu.Unlock()
				if lat != nil {
					log.Printf("auto-update %v -> %s", info["current"], lat.Version)
					setState("downloading", 0, "")
					go func() {
						if err := applyUpdate(lat); err != nil {
							log.Printf("auto-update failed: %v", err)
							setState("error", 0, err.Error())
						}
					}()
					target = fmt.Sprintf("http://localhost:%d/__updating", Port)
				}
			}
		}
		openWindow(target, prof)
	}
	// stay alive while the game talks to us; stop once the window has been closed for IdleTimeout
	for {
		time.Sleep(5 * time.Second)
		if time.Since(time.Unix(0, lastHit.Load())) > IdleTimeout && !*noOpen {
			log.Printf("no requests for %v — the game window was closed, stopping", IdleTimeout)
			ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
			_ = srv.Shutdown(ctx)
			cancel()
			return
		}
	}
}

// listen on both IPv4 and IPv6 loopback so "localhost" works whichever one the browser picks
func listen() ([]net.Listener, error) {
	ln4, err := net.Listen("tcp4", fmt.Sprintf("127.0.0.1:%d", Port))
	if err != nil {
		return nil, err
	}
	lns := []net.Listener{ln4}
	if ln6, err := net.Listen("tcp6", fmt.Sprintf("[::1]:%d", Port)); err == nil {
		lns = append(lns, ln6)
	}
	return lns, nil
}

func addrs(lns []net.Listener) []string {
	var out []string
	for _, l := range lns {
		out = append(out, l.Addr().String())
	}
	return out
}

func pokeboxRunning() bool {
	c := http.Client{Timeout: 1500 * time.Millisecond}
	r, err := c.Get(fmt.Sprintf("http://127.0.0.1:%d/__ping", Port))
	if err != nil {
		return false
	}
	r.Body.Close()
	return r.StatusCode == 204 || r.StatusCode == 200 // 204 also comes from the old server.ps1 — serves the same folder
}

func handle(w http.ResponseWriter, r *http.Request) {
	lastHit.Store(time.Now().UnixNano())
	if *debug {
		log.Printf("%s %s", r.Method, r.URL.Path)
	}
	h := w.Header()
	h.Set("X-Content-Type-Options", "nosniff")
	if r.URL.Path == "/__ping" {
		h.Set("X-Pokebox", Version)
		w.WriteHeader(http.StatusNoContent)
		return
	}
	if r.URL.Path == "/__updating" {
		h.Set("Content-Type", "text/html; charset=utf-8")
		h.Set("Cache-Control", "no-store")
		fmt.Fprint(w, updatingPage)
		return
	}
	if strings.HasPrefix(r.URL.Path, "/__update/") {
		handleUpdate(w, r)
		return
	}
	if r.URL.Path == "/" {
		http.Redirect(w, r, StartPath, http.StatusFound)
		return
	}
	if r.Method != http.MethodGet && r.Method != http.MethodHead {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	// URL.Path is already unescaped: refuse Windows separators / drive letters, then Clean removes any ../
	if strings.ContainsAny(r.URL.Path, "\\:\x00") {
		http.NotFound(w, r)
		return
	}
	rel := path.Clean("/" + r.URL.Path)
	file := filepath.Join(gameRoot, filepath.FromSlash(rel))
	if !strings.HasPrefix(strings.ToLower(file)+string(filepath.Separator), strings.ToLower(gameRoot)+string(filepath.Separator)) {
		http.NotFound(w, r)
		return
	}
	st, err := os.Stat(file)
	if err == nil && st.IsDir() {
		file = filepath.Join(file, "index.html")
		st, err = os.Stat(file)
	}
	if err != nil || st.IsDir() {
		http.NotFound(w, r)
		return
	}
	ext := strings.ToLower(filepath.Ext(file))
	ct := types[ext]
	if ct == "" {
		ct = mime.TypeByExtension(ext)
	}
	if ct == "" {
		ct = "application/octet-stream"
	}
	h.Set("Content-Type", ct)
	switch ext {
	case ".html", ".js", ".mjs", ".css", ".json", ".webmanifest":
		h.Set("Cache-Control", "no-store, must-revalidate") // code/data: an update must always load
	default:
		h.Set("Cache-Control", "no-cache") // images/models: revalidate (304 on localhost is instant), so updated art shows at once
	}
	f, err := os.Open(file)
	if err != nil {
		http.NotFound(w, r)
		return
	}
	defer f.Close()
	http.ServeContent(w, r, "", st.ModTime(), f) // handles HEAD and Range requests
}

func openWindow(url, prof string) {
	// clear the app window's web cache so a game update always loads (saves live in Local Storage and are kept)
	for _, c := range []string{`Default\Cache`, `Default\Code Cache`, `Default\GPUCache`, `Default\Service Worker\CacheStorage`} {
		_ = os.RemoveAll(filepath.Join(prof, c))
	}
	args := []string{
		"--app=" + url, "--user-data-dir=" + prof, "--window-size=1600,940", "--start-maximized",
		"--no-first-run", "--no-default-browser-check", "--disable-features=Translate,msEdgeSidebar",
		"--autoplay-policy=no-user-gesture-required", "--ignore-gpu-blocklist", "--enable-gpu-rasterization",
	}
	for _, b := range browsers() {
		cmd := exec.Command(b, args...)
		if err := cmd.Start(); err == nil {
			log.Printf("opened %s", b)
			go cmd.Wait()
			return
		} else {
			log.Printf("could not start %s: %v", b, err)
		}
	}
	log.Printf("no Edge/Chrome found — opening the default browser")
	if runtime.GOOS == "windows" {
		_ = exec.Command("rundll32", "url.dll,FileProtocolHandler", url).Start()
	} else {
		_ = exec.Command("xdg-open", url).Start()
	}
}

func browsers() []string {
	var out []string
	roots := []string{os.Getenv("ProgramFiles(x86)"), os.Getenv("ProgramFiles"), os.Getenv("LOCALAPPDATA")}
	for _, rel := range []string{`Microsoft\Edge\Application\msedge.exe`, `Google\Chrome\Application\chrome.exe`} {
		for _, root := range roots {
			if root == "" {
				continue
			}
			if p := filepath.Join(root, rel); fileExists(p) {
				out = append(out, p)
			}
		}
	}
	for _, n := range []string{"msedge", "chrome"} {
		if p, err := exec.LookPath(n); err == nil {
			out = append(out, p)
		}
	}
	return out
}

func fileExists(p string) bool { st, err := os.Stat(p); return err == nil && !st.IsDir() }

func fatal(msg string) {
	log.Print("FATAL: " + msg)
	messageBox("Pokebox", msg)
	os.Exit(1)
}

// shown while the launcher installs a new version at start-up; continues to the game when done (or if it fails)
const updatingPage = `<!doctype html><html><head><meta charset="utf-8"><title>Pokebox — updating</title><style>
html,body{margin:0;height:100%;background:#0b0916;color:#fff;font:600 16px system-ui,sans-serif;display:grid;place-items:center}
.b{width:min(460px,86vw);text-align:center}h1{font:800 34px system-ui;letter-spacing:.06em;margin:0 0 6px;color:#ffd257}
p{opacity:.75;margin:0 0 18px}.bar{height:12px;border-radius:8px;background:rgba(255,255,255,.12);overflow:hidden}
.bar i{display:block;height:100%;width:0;background:linear-gradient(90deg,#5cf2d6,#ffd257);transition:width .3s}small{display:block;margin-top:10px;opacity:.6}</style></head>
<body><div class="b"><h1>POKEBOX</h1><p id="t">Downloading the new version…</p><div class="bar"><i id="i"></i></div><small id="m">Your saves and cards are kept.</small></div>
<script>const go=()=>location.replace("` + StartPath + `");
async function poll(){try{const s=await (await fetch("/__update/status",{cache:"no-store"})).json();
document.getElementById("i").style.width=Math.round((s.pct||0)*100)+"%";
document.getElementById("t").textContent=s.state==="installing"?"Installing…":s.state==="done"?"Done!":"Downloading the new version…";
if(s.state==="done"){setTimeout(go,500);return}if(s.state==="error"){document.getElementById("t").textContent="Update failed — starting the current version";document.getElementById("m").textContent=s.msg||"";setTimeout(go,2500);return}}catch(e){}
setTimeout(poll,400)}poll();</script></body></html>`
