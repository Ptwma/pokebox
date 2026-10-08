package com.pokebox.game;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.graphics.Color;
import android.os.Build;
import android.os.Bundle;
import android.view.KeyEvent;
import android.view.MotionEvent;
import android.view.View;
import android.view.Window;
import android.view.WindowInsets;
import android.view.WindowInsetsController;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebView;

import org.json.JSONObject;

import java.lang.ref.WeakReference;

/**
 * The bottom screen of dual-screen handhelds (AYN Thor): a light companion page (bottom.html: map, objective, party,
 * battle buttons, dialogue log, quick menu) in its own WebView. The window can never take focus, so the built-in
 * controller always drives the game on the top screen; any key that still lands here is handed to the game.
 */
public class BottomActivity extends Activity {
    private static WeakReference<BottomActivity> current = new WeakReference<>(null);
    private WebView web;

    static boolean isOpen() { BottomActivity b = current.get(); return b != null && !b.isFinishing() && b.web != null; }
    static void closeAll() { BottomActivity b = current.get(); if (b != null) b.runOnUiThread(b::finish); }
    static void send(String json) {
        BottomActivity b = current.get(); if (b == null || b.web == null) return; WebView w = b.web;
        w.post(() -> w.evaluateJavascript("window.__fromGame&&window.__fromGame(" + JSONObject.quote(json) + ")", null));
    }

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        MainActivity main = MainActivity.current.get();
        if (main == null) { finish(); return; }
        Window w = getWindow();
        w.addFlags(WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE | WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        w.setStatusBarColor(Color.BLACK); w.setNavigationBarColor(Color.BLACK);
        web = new WebView(this);
        web.setBackgroundColor(Color.parseColor("#0e0b18"));
        web.setFocusable(false); web.setFocusableInTouchMode(false);
        setContentView(web);
        MainActivity.setupSettings(web);
        web.addJavascriptInterface(new Object() {
            @JavascriptInterface public void toGame(String json) { MainActivity m = MainActivity.current.get(); if (m != null) m.toGame(json); }
        }, "PokeboxDual");
        web.setWebChromeClient(new WebChromeClient());
        web.setWebViewClient(main.makeClient(false));
        current = new WeakReference<>(this);
        web.loadUrl("https://appassets.androidplatform.net/pokebox-game/bottom.html");
        main.js("window.__dualChanged&&window.__dualChanged(true)");
    }

    private void immersive() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            WindowInsetsController c = getWindow().getInsetsController();
            if (c != null) { c.hide(WindowInsets.Type.statusBars() | WindowInsets.Type.navigationBars()); c.setSystemBarsBehavior(WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE); }
        } else {
            getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY | View.SYSTEM_UI_FLAG_FULLSCREEN | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                | View.SYSTEM_UI_FLAG_LAYOUT_STABLE | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION);
        }
    }

    @Override protected void onResume() { super.onResume(); immersive(); if (web != null) { web.onResume(); web.resumeTimers(); } }
    @Override protected void onPause() { if (web != null) web.onPause(); super.onPause(); } /* no pauseTimers(): that would freeze the game's WebView too */

    // controller input that reaches this window anyway goes to the game
    @Override public boolean dispatchKeyEvent(KeyEvent e) { MainActivity m = MainActivity.current.get(); if (m != null && m.padKey(e)) return true; return super.dispatchKeyEvent(e); }
    @Override public boolean dispatchGenericMotionEvent(MotionEvent e) { MainActivity m = MainActivity.current.get(); if (m != null && m.padMotion(e)) return true; return super.dispatchGenericMotionEvent(e); }
    @SuppressWarnings("deprecation") @Override public void onBackPressed() { MainActivity m = MainActivity.current.get(); if (m != null) m.js("window.__androidBack&&window.__androidBack()"); }

    @Override
    protected void onDestroy() {
        if (current.get() == this) current = new WeakReference<>(null);
        MainActivity m = MainActivity.current.get(); if (m != null) m.js("window.__dualChanged&&window.__dualChanged(false)");
        if (web != null) { web.destroy(); web = null; }
        super.onDestroy();
    }
}
