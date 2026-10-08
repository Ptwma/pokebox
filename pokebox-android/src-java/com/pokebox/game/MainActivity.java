package com.pokebox.game;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.app.ActivityOptions;
import android.content.Intent;
import android.hardware.display.DisplayManager;
import android.view.Display;
import android.view.InputDevice;
import android.view.InputEvent;
import android.view.KeyEvent;
import android.view.MotionEvent;
import android.webkit.JavascriptInterface;
import org.json.JSONArray;
import org.json.JSONObject;
import java.lang.ref.WeakReference;
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
    static WeakReference<MainActivity> current = new WeakReference<>(null);
    private DisplayManager dm;
    private boolean resumed = false;
    private final float[] axes = new float[8];
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

        setupSettings(web);
        web.addJavascriptInterface(new Dual(), "PokeboxDual"); // dual-screen bridge + controller info (AYN Thor & co.)

        web.setWebChromeClient(new WebChromeClient());
        web.setWebViewClient(makeClient(true));
        current = new WeakReference<>(this);
        dm = (DisplayManager) getSystemService(DISPLAY_SERVICE);
        dm.registerDisplayListener(displays, null);
        if (Build.MANUFACTURER != null && Build.MANUFACTURER.toUpperCase(Locale.ROOT).contains("AYN")) setRefresh(60); // dual-screen handheld: even 60 Hz pacing instead of a juddery 70-90 on the 120 Hz panel

        if (state == null || web.restoreState(state) == null || web.getUrl() == null) web.loadUrl(START);
    }

    static void setupSettings(WebView web) {
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
        s.setUserAgentString(s.getUserAgentString() + " PokeboxAndroid/1.2");
    }

    WebViewClient makeClient(final boolean main) {
        return new WebViewClient() {
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
                if (!main) { BottomActivity.closeAll(); return true; }
                ((android.view.ViewGroup) view.getParent()).removeView(view);
                view.destroy();
                web = null;
                recreate();
                return true;
            }
        };
    }

    WebResourceResponse serveAsset(String path) {
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
        if (web != null) { web.onResume(); web.resumeTimers(); web.evaluateJavascript("try{window.dispatchEvent(new Event('pageshow'))}catch(e){}", null); }
        resumed = true;
        if (web != null) web.postDelayed(this::openBottom, 1200); // after the game page is up
    }

    @Override
    protected void onStop() {
        resumed = false;
        BottomActivity.closeAll(); // the bottom screen never outlives the game on the top screen
        super.onStop();
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
        try { if (dm != null) dm.unregisterDisplayListener(displays); } catch (Exception ignored) { }
        BottomActivity.closeAll();
        if (web != null) { web.destroy(); web = null; }
        super.onDestroy();
    }

    /* ================================================================== second screen (AYN Thor, AYANEO Pocket DS, …)
       The bottom panel is its own Activity launched onto the other display (a Presentation is refused on internal
       secondary displays on Android 13). Its window is NOT focusable, so the built-in controller keeps driving the game. */
    Display secondDisplay() {
        if (dm == null) return null;
        for (Display d : dm.getDisplays()) {
            if (d.getDisplayId() == Display.DEFAULT_DISPLAY) continue;
            if (d.getState() == Display.STATE_OFF) continue;
            if ((d.getFlags() & Display.FLAG_PRIVATE) != 0) continue;
            return d;
        }
        return null;
    }

    void openBottom() {
        if (!resumed || isFinishing() || BottomActivity.isOpen() || !prefDual()) return;
        Display d = secondDisplay(); if (d == null) return;
        try {
            Intent i = new Intent(this, BottomActivity.class);
            i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_MULTIPLE_TASK | Intent.FLAG_ACTIVITY_NO_ANIMATION);
            ActivityOptions o = ActivityOptions.makeBasic(); o.setLaunchDisplayId(d.getDisplayId());
            startActivity(i, o.toBundle());
        } catch (Exception e) { lastError = String.valueOf(e); }
    }
    volatile String lastError = "";
    boolean prefDual() { return getSharedPreferences("pbx", MODE_PRIVATE).getBoolean("dual", true); }

    final DisplayManager.DisplayListener displays = new DisplayManager.DisplayListener() {
        @Override public void onDisplayAdded(int id) { if (web != null) web.postDelayed(MainActivity.this::openBottom, 600); }
        @Override public void onDisplayRemoved(int id) { BottomActivity.closeAll(); }
        @Override public void onDisplayChanged(int id) {
            Display d = dm.getDisplay(id); if (d == null || id == Display.DEFAULT_DISPLAY) return;
            if (d.getState() == Display.STATE_OFF) BottomActivity.closeAll(); else if (web != null) web.postDelayed(MainActivity.this::openBottom, 600);
        }
    };

    /** lock the top panel to a refresh rate (keeps the frame pacing even); 0 = system default */
    void setRefresh(float hz) {
        try {
            Display d = getWindowManager().getDefaultDisplay(); Display.Mode cur = d.getMode(), best = null;
            if (hz > 0) for (Display.Mode m : d.getSupportedModes()) {
                if (m.getPhysicalWidth() != cur.getPhysicalWidth() || m.getPhysicalHeight() != cur.getPhysicalHeight()) continue;
                if (best == null || Math.abs(m.getRefreshRate() - hz) < Math.abs(best.getRefreshRate() - hz)) best = m;
            }
            WindowManager.LayoutParams lp = getWindow().getAttributes();
            lp.preferredDisplayModeId = best != null ? best.getModeId() : 0;
            getWindow().setAttributes(lp);
        } catch (Exception ignored) { }
    }

    /* the game page → bottom page and back (JSON strings) */
    void toGame(String json) { WebView w = web; if (w != null) w.post(() -> w.evaluateJavascript("window.__fromBottom&&window.__fromBottom(" + JSONObject.quote(json) + ")", null)); }
    void js(String code) { WebView w = web; if (w != null) w.post(() -> w.evaluateJavascript(code, null)); }

    class Dual {
        @JavascriptInterface public boolean has() { return BottomActivity.isOpen(); }
        @JavascriptInterface public void toBottom(String json) { BottomActivity.send(json); }
        @JavascriptInterface public void setEnabled(boolean on) { getSharedPreferences("pbx", MODE_PRIVATE).edit().putBoolean("dual", on).apply(); runOnUiThread(() -> { if (on) openBottom(); else BottomActivity.closeAll(); }); }
        @JavascriptInterface public void setRefresh(float hz) { runOnUiThread(() -> MainActivity.this.setRefresh(hz)); }
        @JavascriptInterface public String info() {
            try {
                JSONObject o = new JSONObject();
                o.put("maker", Build.MANUFACTURER); o.put("model", Build.MODEL); o.put("device", Build.DEVICE); o.put("android", Build.VERSION.RELEASE); o.put("sdk", Build.VERSION.SDK_INT);
                o.put("handheld", Build.MANUFACTURER != null && Build.MANUFACTURER.toUpperCase(Locale.ROOT).contains("AYN"));
                JSONArray ds = new JSONArray();
                if (dm != null) for (Display d : dm.getDisplays()) {
                    Display.Mode m = d.getMode(); JSONObject j = new JSONObject();
                    j.put("id", d.getDisplayId()); j.put("name", d.getName()); j.put("w", m.getPhysicalWidth()); j.put("h", m.getPhysicalHeight()); j.put("hz", m.getRefreshRate());
                    j.put("state", d.getState()); j.put("flags", d.getFlags()); ds.put(j);
                }
                o.put("displays", ds); o.put("bottomOpen", BottomActivity.isOpen()); o.put("dual", prefDual()); o.put("error", lastError);
                JSONArray pads = new JSONArray();
                for (int id : InputDevice.getDeviceIds()) { InputDevice dev = InputDevice.getDevice(id); if (dev == null) continue; int src = dev.getSources();
                    if ((src & InputDevice.SOURCE_GAMEPAD) == InputDevice.SOURCE_GAMEPAD || (src & InputDevice.SOURCE_JOYSTICK) == InputDevice.SOURCE_JOYSTICK) pads.put(dev.getName()); }
                o.put("pads", pads);
                return o.toString();
            } catch (Exception e) { return "{\"error\":" + JSONObject.quote(String.valueOf(e)) + "}"; }
        }
    }

    /* ================================================================== built-in / Bluetooth controllers
       Read natively (reliable in a WebView, also while the bottom screen is touched) and pushed to js/pad.js. */
    static String padName(int code) {
        switch (code) {
            case KeyEvent.KEYCODE_BUTTON_A: return "A"; case KeyEvent.KEYCODE_BUTTON_B: return "B";
            case KeyEvent.KEYCODE_BUTTON_X: return "X"; case KeyEvent.KEYCODE_BUTTON_Y: return "Y";
            case KeyEvent.KEYCODE_BUTTON_L1: return "LB"; case KeyEvent.KEYCODE_BUTTON_R1: return "RB";
            case KeyEvent.KEYCODE_BUTTON_L2: return "LT"; case KeyEvent.KEYCODE_BUTTON_R2: return "RT";
            case KeyEvent.KEYCODE_BUTTON_SELECT: return "SELECT"; case KeyEvent.KEYCODE_BUTTON_START: case KeyEvent.KEYCODE_BUTTON_MODE: return "START";
            case KeyEvent.KEYCODE_BUTTON_THUMBL: return "L3"; case KeyEvent.KEYCODE_BUTTON_THUMBR: return "R3";
            case KeyEvent.KEYCODE_DPAD_UP: return "UP"; case KeyEvent.KEYCODE_DPAD_DOWN: return "DOWN";
            case KeyEvent.KEYCODE_DPAD_LEFT: return "LEFT"; case KeyEvent.KEYCODE_DPAD_RIGHT: return "RIGHT";
            default: return null;
        }
    }
    static boolean fromPad(InputEvent e) { int s = e.getSource(); return (s & InputDevice.SOURCE_GAMEPAD) == InputDevice.SOURCE_GAMEPAD || (s & InputDevice.SOURCE_JOYSTICK) == InputDevice.SOURCE_JOYSTICK || (s & InputDevice.SOURCE_DPAD) == InputDevice.SOURCE_DPAD; }

    boolean padKey(KeyEvent e) {
        String n = padName(e.getKeyCode());
        if (n == null || !(fromPad(e) || KeyEvent.isGamepadButton(e.getKeyCode()))) return false;
        if (e.getAction() == KeyEvent.ACTION_MULTIPLE) return true;
        if (e.getRepeatCount() == 0) js("window.__padKey&&window.__padKey('" + n + "'," + (e.getAction() == KeyEvent.ACTION_DOWN ? 1 : 0) + ")");
        return true;
    }
    boolean padMotion(MotionEvent e) {
        if ((e.getSource() & InputDevice.SOURCE_JOYSTICK) != InputDevice.SOURCE_JOYSTICK || e.getAction() != MotionEvent.ACTION_MOVE) return false;
        float[] v = { e.getAxisValue(MotionEvent.AXIS_X), e.getAxisValue(MotionEvent.AXIS_Y), e.getAxisValue(MotionEvent.AXIS_Z), e.getAxisValue(MotionEvent.AXIS_RZ),
            Math.max(e.getAxisValue(MotionEvent.AXIS_LTRIGGER), e.getAxisValue(MotionEvent.AXIS_BRAKE)), Math.max(e.getAxisValue(MotionEvent.AXIS_RTRIGGER), e.getAxisValue(MotionEvent.AXIS_GAS)),
            e.getAxisValue(MotionEvent.AXIS_HAT_X), e.getAxisValue(MotionEvent.AXIS_HAT_Y) };
        boolean ch = false; for (int i = 0; i < 8; i++) if (Math.abs(v[i] - axes[i]) > .01f) { ch = true; axes[i] = v[i]; }
        if (ch) js(String.format(Locale.ROOT, "window.__padAxes&&window.__padAxes(%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.0f,%.0f)", v[0], v[1], v[2], v[3], v[4], v[5], v[6], v[7]));
        return true;
    }
    @Override public boolean dispatchKeyEvent(KeyEvent e) { return padKey(e) || super.dispatchKeyEvent(e); }
    @Override public boolean dispatchGenericMotionEvent(MotionEvent e) { return padMotion(e) || super.dispatchGenericMotionEvent(e); }
}
