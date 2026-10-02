package com.pokebox.game;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageInfo;
import android.net.Uri;
import android.os.Build;
import android.webkit.JavascriptInterface;
import android.webkit.WebView;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedInputStream;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.security.MessageDigest;
import java.util.Locale;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

/**
 * In-app updates from GitHub Releases (same release files as the PC version, see .github/workflows/release.yml).
 * The game code (pokebox-game) is downloaded into filesDir/www/pokebox-game and served INSTEAD of the copy inside
 * the APK — but only while it is newer than the APK's own copy. Card images always come from the APK.
 * JS side: js/updater.js (window.PokeboxNative).
 */
public class Updater {
    private final Activity act;
    private final WebView web;
    private final File root;     // filesDir/www  (contains pokebox-game/…)
    private volatile String state = "idle", msg = "";
    private volatile double pct = 0;
    private volatile JSONObject check = null, latest = null;
    private volatile boolean busy = false;

    Updater(Activity act, WebView web) {
        this.act = act;
        this.web = web;
        this.root = new File(act.getFilesDir(), "www");
    }

    /* ------------------------------------------------------------------ which copy of the game to serve */

    /** folder with the downloaded game if it is newer than the APK's copy, else null (and stale downloads are removed) */
    static File activeOverride(Context c) {
        File dir = new File(c.getFilesDir(), "www");
        File vf = new File(dir, "pokebox-game/version.json");
        if (!vf.isFile()) return null;
        try {
            String dl = new JSONObject(readAll(new FileInputStream(vf))).optString("version", "0");
            String apk = bundledVersion(c);
            if (newer(dl, apk)) return dir;
        } catch (Exception ignored) { }
        deleteTree(dir); // the APK is newer (the app was reinstalled/updated): drop the old download
        return null;
    }

    static String bundledVersion(Context c) {
        try { return new JSONObject(readAll(c.getAssets().open("www/pokebox-game/version.json"))).optString("version", "0"); }
        catch (Exception e) { return "0"; }
    }

    private String currentVersion() {
        File o = activeOverride(act);
        if (o != null) {
            try { return new JSONObject(readAll(new FileInputStream(new File(o, "pokebox-game/version.json")))).optString("version", "0"); }
            catch (Exception ignored) { }
        }
        return bundledVersion(act);
    }

    private String repo() {
        try {
            File o = activeOverride(act);
            InputStream in = o != null ? new FileInputStream(new File(o, "pokebox-game/version.json")) : act.getAssets().open("www/pokebox-game/version.json");
            return new JSONObject(readAll(in)).optString("repo", "");
        } catch (Exception e) { return ""; }
    }

    private int apkVersionCode() {
        try {
            PackageInfo pi = act.getPackageManager().getPackageInfo(act.getPackageName(), 0);
            return Build.VERSION.SDK_INT >= 28 ? (int) pi.getLongVersionCode() : pi.versionCode;
        } catch (Exception e) { return 0; }
    }

    /* ------------------------------------------------------------------ JS bridge */

    @JavascriptInterface
    public String status() {
        try {
            JSONObject o = new JSONObject();
            o.put("state", state);
            o.put("pct", pct);
            o.put("msg", msg);
            if (check != null) o.put("check", check);
            return o.toString();
        } catch (Exception e) { return "{}"; }
    }

    @JavascriptInterface
    public void startCheck() {
        if (busy) return;
        check = null;
        state = "checking";
        new Thread(() -> {
            try {
                String repo = repo();
                JSONObject out = new JSONObject();
                String cur = currentVersion();
                out.put("current", cur);
                out.put("platform", "android");
                out.put("newer", false);
                if (repo.isEmpty() || repo.startsWith("OWNER/")) { out.put("error", "no update repository configured"); check = out; state = "idle"; return; }
                JSONObject lat = new JSONObject(new String(get("https://github.com/" + repo + "/releases/latest/download/latest.json", 1 << 20), "UTF-8"));
                latest = lat;
                String v = lat.optString("version", "0");
                out.put("latest", v);
                out.put("newer", newer(v, cur));
                out.put("notes", lat.optJSONArray("notes") != null ? lat.optJSONArray("notes") : new JSONArray());
                out.put("size", lat.optJSONObject("zip") != null ? lat.optJSONObject("zip").optLong("size") : 0);
                out.put("page", "https://github.com/" + repo + "/releases/latest");
                out.put("needApk", newer(v, cur) && lat.optInt("minApk", 0) > apkVersionCode());
                check = out;
                state = "idle";
            } catch (Exception e) {
                try { JSONObject out = new JSONObject(); out.put("current", currentVersion()); out.put("newer", false); out.put("error", "offline"); check = out; } catch (Exception ignored) { }
                state = "idle";
            }
        }, "pokebox-check").start();
    }

    @JavascriptInterface
    public void startApply() {
        if (busy || latest == null) { if (latest == null) { state = "error"; msg = "check for updates first"; } return; }
        busy = true;
        state = "downloading"; pct = 0; msg = "";
        new Thread(() -> {
            try { apply(latest); state = "done"; pct = 1; msg = ""; }
            catch (Exception e) { state = "error"; msg = e.getMessage() != null ? e.getMessage() : e.toString(); }
            finally { busy = false; }
        }, "pokebox-update").start();
    }

    @JavascriptInterface
    public void reload() { act.runOnUiThread(() -> { if (act instanceof MainActivity) ((MainActivity) act).refreshOverride(); web.reload(); }); }

    /** the title screen may be portrait; the game itself is played sideways */
    @JavascriptInterface
    public void landscape() { act.runOnUiThread(() -> act.setRequestedOrientation(android.content.pm.ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE)); }

    @JavascriptInterface
    public void anyOrientation() { act.runOnUiThread(() -> act.setRequestedOrientation(android.content.pm.ActivityInfo.SCREEN_ORIENTATION_FULL_USER)); }

    @JavascriptInterface
    public void openUrl(String url) {
        if (url == null || !url.startsWith("https://github.com/")) return; // only the release page
        act.runOnUiThread(() -> act.startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url))));
    }

    /* ------------------------------------------------------------------ download + install */

    private void apply(JSONObject lat) throws Exception {
        String repo = repo(), ver = lat.getString("version");
        JSONObject z = lat.getJSONObject("zip");
        File cache = new File(act.getCacheDir(), "update.zip");
        String url = "https://github.com/" + repo + "/releases/download/v" + ver + "/" + z.getString("name");
        download(url, cache, z.optLong("size"), z.optString("sha256", ""));

        state = "installing"; pct = 0.9; msg = "unpacking";
        File fresh = new File(act.getFilesDir(), "www-new"), old = new File(act.getFilesDir(), "www-old");
        deleteTree(fresh); deleteTree(old);
        File game = new File(fresh, "pokebox-game");
        unzip(cache, game);
        cache.delete();
        if (!new File(game, "index.html").isFile() || !new File(game, "version.json").isFile()) throw new IOException("bad update package");
        // swap folders (old → www-old → deleted)
        if (root.exists() && !root.renameTo(old)) throw new IOException("could not replace the old files");
        if (!fresh.renameTo(root)) { old.renameTo(root); throw new IOException("could not install the new files"); }
        deleteTree(old);
    }

    private void download(String url, File dst, long size, String sha) throws Exception {
        HttpURLConnection c = open(url);
        MessageDigest md = MessageDigest.getInstance("SHA-256");
        long total = size > 0 ? size : c.getContentLengthLong(), n = 0;
        try (InputStream in = new BufferedInputStream(c.getInputStream()); OutputStream out = new FileOutputStream(dst)) {
            byte[] buf = new byte[256 * 1024];
            for (int k; (k = in.read(buf)) > 0; ) {
                out.write(buf, 0, k); md.update(buf, 0, k); n += k;
                if (total > 0) { pct = 0.88 * n / total; msg = String.format(Locale.ROOT, "%.1f / %.1f MB", n / 1048576.0, total / 1048576.0); }
            }
        } finally { c.disconnect(); }
        if (!sha.isEmpty() && !hex(md.digest()).equalsIgnoreCase(sha)) { dst.delete(); throw new IOException("downloaded file is corrupted (checksum mismatch) — try again"); }
    }

    private static void unzip(File zip, File dst) throws IOException {
        String base = dst.getCanonicalPath() + File.separator;
        try (ZipInputStream zin = new ZipInputStream(new BufferedInputStream(new FileInputStream(zip)))) {
            byte[] buf = new byte[256 * 1024];
            for (ZipEntry e; (e = zin.getNextEntry()) != null; ) {
                File f = new File(dst, e.getName());
                if (!f.getCanonicalPath().startsWith(base)) throw new IOException("unsafe path in package: " + e.getName());
                if (e.isDirectory()) { f.mkdirs(); continue; }
                f.getParentFile().mkdirs();
                try (OutputStream out = new FileOutputStream(f)) { for (int k; (k = zin.read(buf)) > 0; ) out.write(buf, 0, k); }
            }
        }
    }

    /* ------------------------------------------------------------------ helpers */

    private static HttpURLConnection open(String url) throws IOException {
        for (int hop = 0; hop < 6; hop++) { // GitHub redirects release downloads to its CDN
            HttpURLConnection c = (HttpURLConnection) new URL(url).openConnection();
            c.setConnectTimeout(10000); c.setReadTimeout(30000); c.setInstanceFollowRedirects(false);
            c.setRequestProperty("User-Agent", "PokeboxAndroid");
            int code = c.getResponseCode();
            if (code >= 300 && code < 400) { url = c.getHeaderField("Location"); c.disconnect(); if (url == null || !url.startsWith("https://")) throw new IOException("bad redirect"); continue; }
            if (code != 200) { c.disconnect(); throw new IOException(code == 404 ? "no release yet" : "HTTP " + code); }
            return c;
        }
        throw new IOException("too many redirects");
    }

    private static byte[] get(String url, int max) throws IOException {
        HttpURLConnection c = open(url);
        try (InputStream in = c.getInputStream()) {
            ByteArrayOutputStream b = new ByteArrayOutputStream(); byte[] buf = new byte[8192];
            for (int k; (k = in.read(buf)) > 0; ) { b.write(buf, 0, k); if (b.size() > max) throw new IOException("response too large"); }
            return b.toByteArray();
        } finally { c.disconnect(); }
    }

    static String readAll(InputStream in) throws IOException {
        try (InputStream i = in) { ByteArrayOutputStream b = new ByteArrayOutputStream(); byte[] buf = new byte[8192]; for (int k; (k = i.read(buf)) > 0; ) b.write(buf, 0, k); return b.toString("UTF-8"); }
    }

    /** dotted version compare: true if a > b */
    static boolean newer(String a, String b) {
        String[] x = a.split("\\."), y = b.split("\\.");
        for (int i = 0; i < Math.max(x.length, y.length); i++) {
            int p = i < x.length ? parse(x[i]) : 0, q = i < y.length ? parse(y[i]) : 0;
            if (p != q) return p > q;
        }
        return false;
    }
    private static int parse(String s) { try { return Integer.parseInt(s.replaceAll("[^0-9]", "")); } catch (Exception e) { return 0; } }

    private static String hex(byte[] d) { StringBuilder s = new StringBuilder(); for (byte b : d) s.append(String.format("%02x", b)); return s.toString(); }

    static void deleteTree(File f) {
        if (f == null || !f.exists()) return;
        File[] kids = f.listFiles();
        if (kids != null) for (File k : kids) deleteTree(k);
        f.delete();
    }
}
