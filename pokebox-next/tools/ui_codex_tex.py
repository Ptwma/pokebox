# Sigil & Spark — "Codex" UI textures (generated, original): parchment panels with a deckled edge and a hand-ruled ink
# double frame (9-slice), the selected variant with a crimson frame + corner flourishes, a dark ink-wash panel, a dry
# brush stroke (banners, HP bars, ribbons — tinted in Slate), a wax seal disc (type badges, key badges, energy pips) and
# a screen vignette for menus. Loaded by PBXUI.cpp from Content/PBX/UI/*.png (file paths, like the fonts).
#   python ui_codex_tex.py <out_dir>
import sys, os, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

def noise(h, w, cell, seed):
    r = np.random.default_rng(seed).random((h // cell + 2, w // cell + 2)).astype(np.float32)
    return np.asarray(Image.fromarray((r * 255).astype(np.uint8)).resize((w + cell * 2, h + cell * 2), Image.BICUBIC))[cell:cell + h, cell:cell + w].astype(np.float32) / 255

def fbm(h, w, seed, octaves=((64, .5), (24, .25), (8, .15), (3, .1))):
    return sum(noise(h, w, c, seed + i) * a for i, (c, a) in enumerate(octaves))

def deckle(h, w, inset, seed, rough=6.0):
    """alpha mask: a rectangle whose edge is torn/deckled (noise-displaced), soft 1-2 px"""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.minimum(np.minimum(xx, w - 1 - xx), np.minimum(yy, h - 1 - yy))          # distance to the border
    n = fbm(h, w, seed, ((40, .6), (12, .3), (4, .1)))
    edge = inset + (n - .5) * 2 * rough
    return np.clip((d - edge) / 1.6, 0, 1)

def wobble_rect(dr, x0, y0, x1, y1, col, width, rnd, amp=1.2, step=14):
    pts = []
    for (ax, ay, bx, by) in ((x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)):
        n = max(2, int(math.hypot(bx - ax, by - ay) / step))
        for k in range(n):
            t = k / n; pts.append((ax + (bx - ax) * t + rnd.uniform(-amp, amp), ay + (by - ay) * t + rnd.uniform(-amp, amp)))
    pts.append(pts[0])
    dr.line(pts, fill=col, width=width, joint='curve')

def flourish(dr, cx, cy, sx, sy, s, col, w):
    """a small corner scroll: a curl + a leaf, mirrored by (sx, sy)"""
    pts = [(cx + sx * s * (0.15 + 0.85 * t) + sx * s * 0.25 * math.sin(t * 6.3) * (1 - t), cy + sy * s * 0.25 * math.cos(t * 6.3) * (1 - t)) for t in np.linspace(0, 1, 30)]
    dr.line(pts, fill=col, width=w, joint='curve')
    pts = [(cx + sx * s * 0.25 * math.cos(t * 6.3) * (1 - t), cy + sy * s * (0.15 + 0.85 * t) + sy * s * 0.25 * math.sin(t * 6.3) * (1 - t)) for t in np.linspace(0, 1, 30)]
    dr.line(pts, fill=col, width=w, joint='curve')
    r = s * 0.11; dr.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)

def parchment(W, H, seed, out, frame=(46, 34, 30), frame_w=(3, 1), crimson=False):
    rnd = random.Random(seed)
    n = fbm(H, W, seed, ((max(8, W // 8), .5), (max(4, W // 20), .25), (4, .15), (2, .1)))
    base = np.array([236, 223, 192], np.float32)                  # warm parchment
    rgb = base[None, None, :] * (0.86 + 0.22 * n[..., None])
    fib = noise(H, W, 2, seed + 9)                                 # fibres: fine streaks
    fib = np.asarray(Image.fromarray((fib * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur((6, 0.6)) if False else ImageFilter.BoxBlur(1))).astype(np.float32) / 255
    rgb *= (0.96 + 0.06 * fib[..., None])
    # stains / foxing
    st = np.clip((fbm(H, W, seed + 30, ((90, .7), (30, .3))) - .62) * 4, 0, 1)
    rgb *= (1 - 0.10 * st[..., None]); rgb[..., 2] *= (1 - 0.06 * st)
    # burnt, darker edges
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.minimum(np.minimum(xx, W - 1 - xx), np.minimum(yy, H - 1 - yy))
    burn = np.clip(1 - d / max(10, W * 0.07), 0, 1) ** 1.6 * (0.7 + 0.6 * n)
    rgb *= (1 - 0.42 * burn[..., None]); rgb[..., 2] *= (1 - 0.12 * burn)
    a = deckle(H, W, max(2, W // 100), seed + 50, rough=max(2.0, W / 90))
    im = Image.fromarray(np.dstack([np.clip(rgb, 0, 255), a * 255]).astype(np.uint8), 'RGBA')
    # the ruled frame: drawn on a separate layer, then multiplied so the ink sits IN the paper
    ink = Image.new('L', (W, H), 0); dr = ImageDraw.Draw(ink)
    for k, (m, w) in enumerate(zip(frame[:2], frame_w)):
        wobble_rect(dr, m, m, W - 1 - m, H - 1 - m, 235 if k == 0 else 170, w, rnd, amp=0.5 if W < 300 else 1.2)
    if crimson:
        for (cx, cy, sx, sy) in ((frame[0], frame[0], 1, 1), (W - 1 - frame[0], frame[0], -1, 1), (frame[0], H - 1 - frame[0], 1, -1), (W - 1 - frame[0], H - 1 - frame[0], -1, -1)):
            flourish(dr, cx, cy, sx, sy, max(10, W * 0.066), 240, 2 if W < 300 else 3)
    ink = ink.filter(ImageFilter.GaussianBlur(0.6))
    ia = np.asarray(ink).astype(np.float32) / 255 * (0.8 + 0.3 * noise(H, W, 3, seed + 70))
    col = np.array([150, 22, 18] if crimson else [40, 26, 18], np.float32)
    arr = np.asarray(im).astype(np.float32)
    arr[..., :3] = arr[..., :3] * (1 - ia[..., None]) + col * ia[..., None]
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGBA').save(out)

def ink_wash(W, H, seed, out):
    """dark sumi wash: near-black, uneven density, brushy torn edges"""
    n = fbm(H, W, seed)
    a = deckle(H, W, 10, seed + 5, rough=9) * (0.80 + 0.2 * n)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    streak = noise(H, W, 6, seed + 3); streak = np.asarray(Image.fromarray((streak * 255).astype(np.uint8)).resize((W // 8, H), Image.BILINEAR).resize((W, H), Image.BICUBIC)).astype(np.float32) / 255
    a *= 0.88 + 0.12 * streak
    rgb = np.dstack([14 + 10 * n, 11 + 8 * n, 10 + 8 * n])
    Image.fromarray(np.dstack([rgb, np.clip(a, 0, 1) * 238]).astype(np.uint8), 'RGBA').save(out)

def brush_stroke(W, H, seed, out):
    """one horizontal dry-brush stroke, white (tinted in Slate): tapered ends, bristle streaks, dry gaps near the tail"""
    rnd = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    t = xx / (W - 1)
    half = (H * 0.42) * np.clip(np.minimum(t / 0.06, (1 - t) / 0.14), 0, 1) ** 0.6 * (1 + 0.06 * np.sin(t * 9 + 1))
    centre = H * 0.5 + H * 0.05 * np.sin(t * 3.1)
    body = np.clip((half - np.abs(yy - centre)) / 2.0, 0, 1)
    # bristles: per-row streak density that dries out towards the tail
    rows = rnd.random(H).astype(np.float32)
    rows = np.asarray(Image.fromarray((rows * 255).astype(np.uint8)[:, None]).resize((1, H), Image.BILINEAR)).astype(np.float32)[:, 0] / 255
    dry = np.clip((t - 0.55) / 0.45, 0, 1)
    gaps = noise(H, W, 5, seed + 1)
    gaps = np.asarray(Image.fromarray((gaps * 255).astype(np.uint8)).resize((W // 16, H), Image.BILINEAR).resize((W, H), Image.BICUBIC)).astype(np.float32) / 255
    keep = np.clip((gaps + rows[:, None] * 0.6 - dry * 0.9 - 0.15) * 6, 0, 1)
    a = body * (0.25 + 0.75 * keep) * (0.85 + 0.15 * noise(H, W, 3, seed + 2))
    Image.fromarray(np.dstack([np.full((H, W), 255), np.full((H, W), 255), np.full((H, W), 255), np.clip(a, 0, 1) * 255]).astype(np.uint8), 'RGBA').save(out)

def wax_seal(S, seed, out):
    """a wax seal disc, white/grey (tinted in Slate): irregular blob rim, a pressed inner ring, soft relief"""
    rnd = random.Random(seed); K = 2; s = S * K
    im = Image.new('L', (s, s), 0); dr = ImageDraw.Draw(im)
    c = s / 2; R = s * 0.43
    pts = [(c + (R + rnd.uniform(-s * .03, s * .03)) * math.cos(a), c + (R + rnd.uniform(-s * .03, s * .03)) * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 22, endpoint=False)]
    dr.polygon(pts, fill=255)
    im = im.filter(ImageFilter.GaussianBlur(s * 0.012)).point(lambda v: 255 if v > 128 else 0).filter(ImageFilter.GaussianBlur(1.2)).resize((S, S), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32) / 255
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32); r = np.hypot(xx - S / 2, yy - S / 2) / (S * 0.43)
    ring = np.exp(-((r - 0.74) / 0.05) ** 2)                    # pressed ring (darker groove + highlight)
    light = 0.82 + 0.18 * np.clip(1 - np.hypot(xx - S * 0.38, yy - S * 0.34) / (S * 0.6), 0, 1)
    v = np.clip(light - 0.25 * ring + 0.10 * np.exp(-((r - 0.80) / 0.04) ** 2), 0, 1) * 255
    Image.fromarray(np.dstack([v, v, v, a * 255]).astype(np.uint8), 'RGBA').save(out)

def vignette(W, H, out):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.hypot((xx - W / 2) / (W / 2), (yy - H / 2) / (H / 2))
    a = np.clip((r - 0.35) / 0.95, 0, 1) ** 1.4 * 0.92 + 0.38
    n = fbm(H, W, 4, ((60, .7), (20, .3)))
    a = np.clip(a * (0.9 + 0.2 * n), 0, 1)
    rgb = np.dstack([np.full((H, W), 12), np.full((H, W), 9), np.full((H, W), 8)])
    Image.fromarray(np.dstack([rgb, a * 255]).astype(np.uint8), 'RGBA').save(out)

if __name__ == '__main__':
    out = sys.argv[1]; os.makedirs(out, exist_ok=True)
    # r59: drawn at native size (Slate's 9-slice margins follow the texture's own pixels): 192 px, frame 15 px in, margin 24 px
    parchment(192, 192, 1, os.path.join(out, 'ui_parchment.png'), frame=(15, 10, 8), frame_w=(2, 1))
    parchment(192, 192, 2, os.path.join(out, 'ui_parchment_sel.png'), frame=(14, 9, 8), frame_w=(3, 1), crimson=True)
    ink_wash(512, 256, 3, os.path.join(out, 'ui_inkwash.png'))
    brush_stroke(1024, 128, 4, os.path.join(out, 'ui_stroke.png'))
    wax_seal(128, 5, os.path.join(out, 'ui_seal.png'))
    vignette(960, 540, os.path.join(out, 'ui_vignette.png'))
    print('ok')
