package com.pokebox.game;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.res.AssetManager;
import android.graphics.Color;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.view.Window;
import android.view.WindowInsets;
import android.view.WindowInsetsController;
import android.view.WindowManager;
import android.webkit.RenderProcessGoneDetail;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.InputStream;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;

/**
 * Pokebox for Android: the whole game runs offline from the APK's assets/www folder.
 * Files are served on https://appassets.androidplatform.net/ (a real https origin, so ES modules, module workers,
 * WebAssembly, fetch() and localStorage all work like on the PC). Opens straight into the game (no start screen).
 */
public class MainActivity extends Activity {
    private static final String HOST = "appassets.androidplatform.net";
    private static final String START = "https://" + HOST + "/pokebox-game/index.html?launch";
    private WebView web;
    private static final String CARDS = "/pokemon-card-scraper/pokemon_cards/images/";
    private CardCache cards;
    private volatile File override; // downloaded newer game files (Updater), served before the APK copy

    private static final Map<String, String> MIME = new HashMap<>();
    static {
        String[][] m = {
            {"html", "text/html"}, {"htm", "text/html"}, {"js", "text/javascript"}, {"mjs", "text/javascript"}, {"css", "text/css"},
            {"json", "application/json"}, {"webmanifest", "application/manifest+json"}, {"png", "image/png"}, {"jpg", "image/jpeg"},
            {"jpeg", "image/jpeg"}, {"webp", "image/webp"}, {"gif", "image/gif"}, {"svg", "image/svg+xml"}, {"ico", "image/x-icon"},
            {"mp3", "audio/mpeg"}, {"wav", "audio/wav"}, {"ogg", "audio/ogg"}, {"glb", "model/gltf-binary"}, {"gltf", "model/gltf+json"},
            {"bin", "application/octet-stream"}, {"wasm", "application/wasm"}, {"onnx", "application/octet-stream"},
            {"woff2", "font/woff2"}, {"woff", "font/woff"}, {"ktx2", "image/ktx2"}, {"txt", "text/plain"}
        };
        for (String[] e : m) MIME.put(e[0], e[1]);
    }

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        Window w = getWindow();
        w.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        w.setStatusBarColor(Color.BLACK);
        w.setNavigationBarColor(Color.BLACK);

        WebView.setWebContentsDebuggingEnabled(true); // chrome://inspect from the PC
        web = new WebView(this);
        web.setBackgroundColor(Color.BLACK);
        web.setLayerType(View.LAYER_TYPE_HARDWARE, null);
        setContentView(web);
        refreshOverride(); cards = new CardCache(this);
        web.addJavascriptInterface(new Updater(this, web), "PokeboxNative"); // in-app updates (js/updater.js)

        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setAllowFileAccess(false);
        s.setAllowContentAccess(false);
        s.setLoadWithOverviewMode(true);
        s.setUseWideViewPort(true);
        s.setSupportZoom(false);
        s.setBuiltInZoomControls(false);
        s.setDisplayZoomControls(false);
        s.setTextZoom(100);
        s.setCacheMode(WebSettings.LOAD_NO_CACHE); // assets come from the APK anyway; never serve stale code after an update
        s.setUserAgentString(s.getUserAgentString() + " PokeboxAndroid/1.1");

        web.setWebChromeClient(new WebChromeClient());
        web.setWebViewClient(new WebViewClient() {
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest req) {
                if (!HOST.equals(req.getUrl().getHost())) return null;
                return serveAsset(req.getUrl().getPath());
            }

            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest req) {
                return !HOST.equals(req.getUrl().getHost()); // stay inside the game; ignore outside links
            }

            @Override
            public boolean onRenderProcessGone(WebView view, RenderProcessGoneDetail detail) {
                // the GPU/renderer process died (low memory): rebuild the WebView instead of crashing the app
                ((android.view.ViewGroup) view.getParent()).removeView(view);
                view.destroy();
                web = null;
                recreate();
                return true;
            }
        });

        if (state == null || web.restoreState(state) == null || web.getUrl() == null) web.loadUrl(START);
    }

    private WebResourceResponse serveAsset(String path) {
        if (path == null || path.isEmpty() || path.equals("/")) path = "/pokebox-game/index.html";
        if (path.endsWith("/")) path += "index.html";
        if (path.contains("..")) return notFound();
        String rel = "www" + path;
        String name = rel.substring(rel.lastIndexOf('/') + 1);
        int dot = name.lastIndexOf('.');
        String ext = dot >= 0 ? name.substring(dot + 1).toLowerCase(Locale.ROOT) : "";
        String mime = MIME.containsKey(ext) ? MIME.get(ext) : "application/octet-stream";
        try {
            File o = override;
            File f = o != null && path.startsWith("/pokebox-game/") ? new File(o, path.substring(1)) : null;
            InputStream in;
            if (f != null && f.isFile()) in = new FileInputStream(f);
            else {
                try { in = getAssets().open(rel, AssetManager.ACCESS_STREAMING); }
                catch (Exception missing) { // card pictures are not inside GitHub-built APKs: fetch + cache them (CardCache)
                    if (!path.startsWith(CARDS)) throw missing;
                    in = cards.open(path.substring(CARDS.length()), o);
                    if (in == null) return notFound();
                }
            }
            Map<String, String> h = new HashMap<>();
            h.put("Access-Control-Allow-Origin", "*");
            h.put("Cache-Control", "no-cache");
            boolean text = mime.startsWith("text/") || mime.endsWith("json") || mime.endsWith("javascript");
            return new WebResourceResponse(mime, text ? "utf-8" : null, 200, "OK", h, in);
        } catch (Exception e) {
            return notFound();
        }
    }

    /** called at start and after an update was installed */
    void refreshOverride() { override = Updater.activeOverride(this); }

    private static WebResourceResponse notFound() {
        Map<String, String> h = new HashMap<>();
        h.put("Access-Control-Allow-Origin", "*");
        return new WebResourceResponse("text/plain", "utf-8", 404, "Not Found", h, new ByteArrayInputStream(new byte[0]));
    }

    private void immersive() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            WindowInsetsController c = getWindow().getInsetsController();
            if (c != null) {
                c.hide(WindowInsets.Type.statusBars() | WindowInsets.Type.navigationBars());
                c.setSystemBarsBehavior(WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE);
            }
        } else {
            getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY | View.SYSTEM_UI_FLAG_FULLSCREEN
                | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION | View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION);
        }
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) immersive();
    }

    @Override
    protected void onResume() {
        super.onResume();
        immersive();
        if (web != null) { web.onResume(); web.resumeTimers(); }
    }

    @Override
    protected void onPause() {
        if (web != null) {
            web.evaluateJavascript("try{window.dispatchEvent(new Event('pagehide'))}catch(e){}", null); // lets the game save
            web.onPause();
        }
        super.onPause();
    }

    @Override
    protected void onSaveInstanceState(Bundle out) {
        super.onSaveInstanceState(out);
        if (web != null) web.saveState(out);
    }

    @SuppressWarnings("deprecation")
    @Override
    public void onBackPressed() {
        // Android Back = Esc (opens/closes the game menu)
        if (web != null) web.evaluateJavascript("window.__androidBack ? (window.__androidBack(), 1) : 0", null);
    }

    @Override
    protected void onDestroy() {
        if (web != null) { web.destroy(); web = null; }
        super.onDestroy();
    }
}
