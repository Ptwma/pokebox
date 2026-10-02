package com.pokebox.game;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;

import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Card pictures for APKs built without them (the GitHub build): the game asks for
 * /pokemon-card-scraper/pokemon_cards/images/<file> as always; if the APK has no copy, the picture is downloaded once
 * from its original pkmncards.com address (data/card_urls.json), shrunk to phone size (360 px wide JPEG) and kept in
 * the app's storage — after that it works offline. Served to the WebView as a same-origin file, so WebGL can use it.
 */
public class CardCache {
    private static final int WIDTH = 360;
    private final Context ctx;
    private final File dir;
    private volatile Map<String, String> urls;
    private String base = "";
    private final ConcurrentHashMap<String, Object> locks = new ConcurrentHashMap<>();

    CardCache(Context ctx) {
        this.ctx = ctx;
        this.dir = new File(ctx.getFilesDir(), "cards");
        dir.mkdirs();
    }

    private synchronized Map<String, String> urls(File override) {
        if (urls != null) return urls;
        Map<String, String> m = new HashMap<>();
        try {
            File f = override != null ? new File(override, "pokebox-game/data/card_urls.json") : null;
            InputStream in = f != null && f.isFile() ? new FileInputStream(f) : ctx.getAssets().open("www/pokebox-game/data/card_urls.json");
            JSONObject o = new JSONObject(Updater.readAll(in));
            base = o.optString("base", "");
            JSONObject files = o.getJSONObject("files");
            for (java.util.Iterator<String> it = files.keys(); it.hasNext(); ) { String k = it.next(); m.put(k, files.getString(k)); }
        } catch (Exception ignored) { }
        urls = m;
        return m;
    }

    /** a stream for the card picture, downloading it the first time; null if unknown/offline */
    InputStream open(String name, File override) {
        if (name == null || name.contains("/") || name.contains("..")) return null;
        File f = new File(dir, name);
        try {
            if (f.isFile() && f.length() > 0) return new FileInputStream(f);
            Object lock = locks.computeIfAbsent(name, k -> new Object());
            synchronized (lock) { // the same card can be asked for several times at once (binder grid + 3D pet)
                if (!(f.isFile() && f.length() > 0)) {
                    String tail = urls(override).get(name);
                    if (tail == null || base.isEmpty()) return null;
                    byte[] raw = fetch(base + tail);
                    if (raw == null) return null;
                    writeSmall(raw, f);
                }
            }
            locks.remove(name);
            return f.isFile() ? new FileInputStream(f) : null;
        } catch (Exception e) {
            return null;
        }
    }

    private static byte[] fetch(String url) throws IOException {
        HttpURLConnection c = (HttpURLConnection) new URL(url).openConnection();
        c.setConnectTimeout(10000); c.setReadTimeout(20000); c.setInstanceFollowRedirects(true);
        c.setRequestProperty("User-Agent", "Mozilla/5.0 (Linux; Android) PokeboxAndroid");
        try {
            if (c.getResponseCode() != 200) return null;
            try (InputStream in = c.getInputStream()) {
                ByteArrayOutputStream b = new ByteArrayOutputStream(); byte[] buf = new byte[32768];
                for (int k; (k = in.read(buf)) > 0; ) { b.write(buf, 0, k); if (b.size() > 8 << 20) return null; }
                return b.toByteArray();
            }
        } finally { c.disconnect(); }
    }

    private static void writeSmall(byte[] raw, File dst) throws IOException {
        BitmapFactory.Options o = new BitmapFactory.Options(); o.inJustDecodeBounds = true;
        BitmapFactory.decodeByteArray(raw, 0, raw.length, o);
        File tmp = new File(dst.getPath() + ".part");
        if (o.outWidth <= 0) return;
        if (o.outWidth <= WIDTH * 1.2) { // already small: keep the original bytes
            try (FileOutputStream out = new FileOutputStream(tmp)) { out.write(raw); }
        } else {
            BitmapFactory.Options d = new BitmapFactory.Options();
            d.inSampleSize = Math.max(1, Integer.highestOneBit(o.outWidth / WIDTH));
            Bitmap b = BitmapFactory.decodeByteArray(raw, 0, raw.length, d);
            if (b == null) return;
            int h = Math.round(b.getHeight() * (WIDTH / (float) b.getWidth()));
            Bitmap s = b.getWidth() > WIDTH ? Bitmap.createScaledBitmap(b, WIDTH, h, true) : b;
            try (FileOutputStream out = new FileOutputStream(tmp)) { s.compress(Bitmap.CompressFormat.JPEG, 80, out); }
            if (s != b) s.recycle(); b.recycle();
        }
        if (!tmp.renameTo(dst)) tmp.delete();
    }
}
