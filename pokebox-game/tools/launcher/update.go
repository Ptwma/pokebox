package main

// In-game updates for the PC version. The game (js/updater.js) talks to these endpoints:
//   GET  /__update/check  → {current, latest, newer, notes, size, page} (asks GitHub for releases/latest/download/latest.json)
//   POST /__update/apply  → starts download + install in the background
//   GET  /__update/status → {state: idle|downloading|installing|done|error, pct, msg}
// The release zip is verified with SHA-256, extracted to a staging folder, then copied over pokebox-game\.
// version.json is written last, so an interrupted update is simply offered again. Saves are not files here
// (they live in the browser's Local Storage), so they are never touched. Pokebox.exe updates itself by renaming
// the running exe to Pokebox.exe.old (Windows allows that) and putting the new one in its place.

import (
	"archive/zip"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"path"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"
)

type localVersion struct {
	Version  string   `json:"version"`
	Launcher string   `json:"launcher"`
	MinApk   int      `json:"minApk"`
	Repo     string   `json:"repo"`
	Notes    []string `json:"notes"`
}

type asset struct {
	Name   string `json:"name"`
	Size   int64  `json:"size"`
	Sha256 string `json:"sha256"`
}

type latestJSON struct {
	Version  string   `json:"version"`
	Launcher string   `json:"launcher"`
	MinApk   int      `json:"minApk"`
	Notes    []string `json:"notes"`
	Zip      asset    `json:"zip"`
	Exe      asset    `json:"exe"`
}

type updState struct {
	State string  `json:"state"`
	Pct   float64 `json:"pct"`
	Msg   string  `json:"msg"`
}

var (
	updMu     sync.Mutex
	upd       = updState{State: "idle"}
	updLatest *latestJSON
	updRepo   string
	// UpdateBase lets tests point at a local fake "GitHub"; normally https://github.com
	UpdateBase = "https://github.com"
	httpc      = &http.Client{Timeout: 10 * time.Minute}
)

func setState(state string, pct float64, msg string) {
	updMu.Lock()
	upd = updState{State: state, Pct: pct, Msg: msg}
	updMu.Unlock()
}

func readLocal() (localVersion, error) {
	var v localVersion
	b, err := os.ReadFile(filepath.Join(gameDir, "version.json"))
	if err != nil {
		return v, err
	}
	err = json.Unmarshal(b, &v)
	return v, err
}

// newer reports whether version a > b (dotted numbers, e.g. 2.10.1 > 2.9.3)
func newer(a, b string) bool {
	pa, pb := strings.Split(a, "."), strings.Split(b, ".")
	for i := 0; i < len(pa) || i < len(pb); i++ {
		var x, y int
		if i < len(pa) {
			x, _ = strconv.Atoi(pa[i])
		}
		if i < len(pb) {
			y, _ = strconv.Atoi(pb[i])
		}
		if x != y {
			return x > y
		}
	}
	return false
}

func releaseURL(repo, file string) string {
	return fmt.Sprintf("%s/%s/releases/latest/download/%s", UpdateBase, repo, file)
}
func assetURL(repo, version, file string) string {
	return fmt.Sprintf("%s/%s/releases/download/v%s/%s", UpdateBase, repo, version, file)
}

func handleUpdate(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.Header().Set("Cache-Control", "no-store")
	switch r.URL.Path {
	case "/__update/check":
		json.NewEncoder(w).Encode(checkUpdate())
	case "/__update/apply":
		if r.Method != http.MethodPost {
			http.Error(w, "POST only", http.StatusMethodNotAllowed)
			return
		}
		updMu.Lock()
		busy := upd.State == "downloading" || upd.State == "installing"
		lat := updLatest
		updMu.Unlock()
		if busy {
			json.NewEncoder(w).Encode(map[string]string{"state": "busy"})
			return
		}
		if lat == nil {
			http.Error(w, "check for updates first", http.StatusConflict)
			return
		}
		setState("downloading", 0, "")
		go func() {
			if err := applyUpdate(lat); err != nil {
				log.Printf("update failed: %v", err)
				setState("error", 0, err.Error())
			}
		}()
		json.NewEncoder(w).Encode(map[string]string{"state": "started"})
	case "/__update/status":
		updMu.Lock()
		s := upd
		updMu.Unlock()
		json.NewEncoder(w).Encode(s)
	default:
		http.NotFound(w, r)
	}
}

func checkUpdate() map[string]any {
	loc, err := readLocal()
	out := map[string]any{"current": loc.Version, "launcher": Version, "newer": false, "platform": "pc"}
	if err != nil {
		out["error"] = "version.json missing"
		return out
	}
	if loc.Repo == "" || strings.HasPrefix(loc.Repo, "OWNER/") {
		out["error"] = "no update repository configured"
		return out
	}
	c := http.Client{Timeout: 8 * time.Second}
	resp, err := c.Get(releaseURL(loc.Repo, "latest.json"))
	if err != nil {
		out["error"] = "offline"
		return out
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		out["error"] = fmt.Sprintf("no release yet (HTTP %d)", resp.StatusCode)
		return out
	}
	var lat latestJSON
	if err := json.NewDecoder(io.LimitReader(resp.Body, 1<<20)).Decode(&lat); err != nil {
		out["error"] = "bad latest.json"
		return out
	}
	updMu.Lock()
	updLatest, updRepo = &lat, loc.Repo
	updMu.Unlock()
	isNewer := newer(lat.Version, loc.Version)
	out["latest"], out["newer"], out["notes"], out["size"] = lat.Version, isNewer, lat.Notes, lat.Zip.Size
	out["page"] = fmt.Sprintf("%s/%s/releases/latest", UpdateBase, loc.Repo)
	if lat.Exe.Name != "" && newer(lat.Launcher, Version) {
		out["size"] = lat.Zip.Size + lat.Exe.Size
		out["launcherUpdate"] = true
	}
	return out
}

// download fetches url into dst, reporting progress between p0 and p1, and checks size + sha256
func download(url, dst string, a asset, p0, p1 float64) error {
	resp, err := httpc.Get(url)
	if err != nil {
		return fmt.Errorf("download failed: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		return fmt.Errorf("download failed: HTTP %d for %s", resp.StatusCode, path.Base(url))
	}
	f, err := os.Create(dst)
	if err != nil {
		return err
	}
	h := sha256.New()
	total := a.Size
	if total <= 0 {
		total = resp.ContentLength
	}
	var n int64
	buf := make([]byte, 256<<10)
	for {
		k, rerr := resp.Body.Read(buf)
		if k > 0 {
			if _, werr := f.Write(buf[:k]); werr != nil {
				f.Close()
				return werr
			}
			h.Write(buf[:k])
			n += int64(k)
			if total > 0 {
				setState("downloading", p0+(p1-p0)*float64(n)/float64(total), fmt.Sprintf("%.1f / %.1f MB", float64(n)/1048576, float64(total)/1048576))
			}
		}
		if rerr == io.EOF {
			break
		}
		if rerr != nil {
			f.Close()
			return fmt.Errorf("download interrupted: %w", rerr)
		}
	}
	if err := f.Close(); err != nil {
		return err
	}
	if a.Sha256 != "" && !strings.EqualFold(hex.EncodeToString(h.Sum(nil)), a.Sha256) {
		return errors.New("downloaded file is corrupted (checksum mismatch) — try again")
	}
	return nil
}

func applyUpdate(lat *latestJSON) error {
	updMu.Lock()
	repo := updRepo
	updMu.Unlock()
	work := filepath.Join(os.TempDir(), "pokebox-update")
	_ = os.RemoveAll(work)
	if err := os.MkdirAll(work, 0o755); err != nil {
		return err
	}
	defer os.RemoveAll(work)

	exeUpdate := lat.Exe.Name != "" && newer(lat.Launcher, Version)
	zipEnd := 0.85
	if exeUpdate {
		zipEnd = 0.7
	}
	zipPath := filepath.Join(work, "game.zip")
	if err := download(assetURL(repo, lat.Version, lat.Zip.Name), zipPath, lat.Zip, 0, zipEnd); err != nil {
		return err
	}
	var exeNew string
	if exeUpdate {
		exeNew = filepath.Join(work, "Pokebox.exe")
		if err := download(assetURL(repo, lat.Version, lat.Exe.Name), exeNew, lat.Exe, zipEnd, 0.85); err != nil {
			return err
		}
	}

	setState("installing", 0.88, "unpacking")
	stage := filepath.Join(work, "stage")
	if err := unzip(zipPath, stage); err != nil {
		return fmt.Errorf("bad update package: %w", err)
	}
	if _, err := os.Stat(filepath.Join(stage, "index.html")); err != nil {
		return errors.New("bad update package: index.html missing")
	}
	setState("installing", 0.92, "copying files")
	// copy everything except version.json, which goes last (marks the update as complete)
	err := filepath.Walk(stage, func(p string, info os.FileInfo, err error) error {
		if err != nil || info.IsDir() {
			return err
		}
		rel, _ := filepath.Rel(stage, p)
		if strings.EqualFold(rel, "version.json") || strings.EqualFold(filepath.Base(rel), "Pokebox.exe") {
			return nil
		}
		return copyFile(p, filepath.Join(gameDir, rel))
	})
	if err != nil {
		return fmt.Errorf("could not write the game files (is the folder read-only?): %w", err)
	}
	if exeNew != "" {
		setState("installing", 0.97, "updating Pokebox.exe")
		if err := replaceExe(exeNew); err != nil {
			log.Printf("launcher self-update skipped: %v", err) // the game itself is updated; the exe can update next time
		}
	}
	if err := copyFile(filepath.Join(stage, "version.json"), filepath.Join(gameDir, "version.json")); err != nil {
		return err
	}
	log.Printf("updated to %s", lat.Version)
	setState("done", 1, "")
	return nil
}

func unzip(src, dst string) error {
	zr, err := zip.OpenReader(src)
	if err != nil {
		return err
	}
	defer zr.Close()
	for _, f := range zr.File {
		name := strings.ReplaceAll(f.Name, "\\", "/")
		clean := path.Clean("/" + name)
		if strings.Contains(name, "..") || strings.ContainsAny(name, ":") || clean == "/" {
			if f.FileInfo().IsDir() {
				continue
			}
			return fmt.Errorf("unsafe path in package: %q", f.Name)
		}
		out := filepath.Join(dst, filepath.FromSlash(clean))
		if f.FileInfo().IsDir() {
			if err := os.MkdirAll(out, 0o755); err != nil {
				return err
			}
			continue
		}
		if err := os.MkdirAll(filepath.Dir(out), 0o755); err != nil {
			return err
		}
		rc, err := f.Open()
		if err != nil {
			return err
		}
		w, err := os.Create(out)
		if err != nil {
			rc.Close()
			return err
		}
		_, err = io.Copy(w, io.LimitReader(rc, 512<<20))
		rc.Close()
		if cerr := w.Close(); err == nil {
			err = cerr
		}
		if err != nil {
			return err
		}
	}
	return nil
}

// copyFile writes to a temp file next to the target, then renames over it (no half-written files)
func copyFile(src, dst string) error {
	if err := os.MkdirAll(filepath.Dir(dst), 0o755); err != nil {
		return err
	}
	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()
	tmp := dst + ".pbxnew"
	out, err := os.Create(tmp)
	if err != nil {
		return err
	}
	if _, err := io.Copy(out, in); err != nil {
		out.Close()
		os.Remove(tmp)
		return err
	}
	if err := out.Close(); err != nil {
		os.Remove(tmp)
		return err
	}
	_ = os.Chmod(dst, 0o644) // a read-only target would block the rename
	if err := os.Rename(tmp, dst); err != nil {
		os.Remove(tmp)
		return err
	}
	return nil
}

func replaceExe(newExe string) error {
	old := exePath + ".old"
	_ = os.Remove(old)
	if err := os.Rename(exePath, old); err != nil {
		return err
	}
	if err := copyFile(newExe, exePath); err != nil {
		_ = os.Rename(old, exePath) // roll back
		return err
	}
	return nil
}

// cleanupOldExe removes the Pokebox.exe.old left by a previous self-update
func cleanupOldExe() {
	if exePath != "" {
		_ = os.Remove(exePath + ".old")
	}
}
