# Sigil & Spark — legend intro textures (generated, original): Codex page script (an invented calligraphic alphabet in
# sepia ink, margins + ruled double frame + a caption under the drawing), and ink splatter overlays for the screen.
#   python legend_tex.py <out_dir>
import sys, os, math, random
from PIL import Image, ImageDraw, ImageFilter
import numpy as np

def stroke(dr, pts, w0, w1, col):
    """a calligraphic stroke: polyline whose width tapers w0 → peak → w1 (drawn as overlapping discs)"""
    n = len(pts)
    for i in range(n - 1):
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        seg = max(1, int(math.hypot(x1 - x0, y1 - y0) / 0.8))
        for k in range(seg):
            t = (i + k / seg) / (n - 1)
            w = w0 + (w1 - w0) * t + math.sin(t * math.pi) * (max(w0, w1) * 1.2)
            x = x0 + (x1 - x0) * k / seg; y = y0 + (y1 - y0) * k / seg
            dr.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=col)

def glyph(dr, rnd, x, y, s, col):
    """one invented letter: 1–3 strokes (stems, hooks, arcs, a dot); returns its width"""
    w = s * rnd.uniform(0.55, 0.95)
    for _ in range(rnd.randint(1, 3)):
        kind = rnd.choice(['stem', 'hook', 'arc', 'arc', 'sweep', 'dot'])
        if kind == 'stem':
            xx = x + rnd.uniform(0.2, 0.8) * w
            pts = [(xx, y - s * rnd.uniform(0.3, 0.6)), (xx + rnd.uniform(-2, 2), y + s * 0.15), (xx + rnd.uniform(-3, 1), y + s * 0.35)]
        elif kind == 'hook':
            xx = x + rnd.uniform(0.1, 0.5) * w
            pts = [(xx, y - s * 0.3), (xx + w * 0.4, y - s * 0.35), (xx + w * 0.55, y), (xx + w * 0.3, y + s * 0.3)]
        elif kind == 'arc':
            cx, cy, r = x + w * 0.5, y, s * rnd.uniform(0.18, 0.32); a0 = rnd.uniform(0, 6.28); sp = rnd.uniform(2.0, 4.5)
            pts = [(cx + r * math.cos(a0 + sp * t / 6), cy + r * 0.9 * math.sin(a0 + sp * t / 6)) for t in range(7)]
        elif kind == 'sweep':
            pts = [(x, y + s * 0.25), (x + w * 0.4, y + s * rnd.uniform(-0.1, 0.3)), (x + w, y + s * rnd.uniform(-0.3, 0.1))]
        else:
            xx, yy = x + w * rnd.uniform(0.3, 0.7), y - s * rnd.uniform(0.45, 0.65)
            dr.ellipse([xx - s * .06, yy - s * .06, xx + s * .06, yy + s * .06], fill=col); continue
        stroke(dr, pts, s * 0.03, s * 0.05, col)
    return w

def text_block(dr, rnd, x0, y0, x1, y1, s, col, line_gap=1.55, ragged=True):
    y = y0 + s
    while y < y1 - s * 0.3:
        x = x0 + (rnd.uniform(0, s * 1.5) if ragged and rnd.random() < 0.15 else 0)
        end = x1 - (rnd.uniform(0, s * 4) if ragged else 0)
        while x < end - s:
            n = rnd.randint(2, 7)
            for _ in range(n):
                if x > end - s: break
                x += glyph(dr, rnd, x, y, s, col) + s * 0.08
            x += s * 0.55
        y += s * line_gap

def page_script(W, H, seed, out):
    """ink in ALPHA (black), so the page shader can tint/drain it. Margin text, a double ruled frame, a caption line,
    a drawing window left empty in the middle."""
    rnd = random.Random(seed)
    im = Image.new('L', (W, H), 0); dr = ImageDraw.Draw(im)
    a = 210; m = int(W * 0.07)
    # double frame
    for k, wd in ((0, 5), (14, 2)):
        dr.rectangle([m + k, m + k, W - m - k, H - m - k], outline=a, width=wd)
    # header band
    text_block(dr, rnd, m + 40, m + 30, W - m - 40, int(H * 0.17), 34, 200)
    dr.line([m + 30, int(H * 0.18), W - m - 30, int(H * 0.18)], fill=a, width=3)
    # side columns + bottom block, leaving the drawing window (centre) empty
    win = (int(W * 0.31), int(H * 0.21), int(W * 0.69), int(H * 0.70))
    text_block(dr, rnd, m + 34, int(H * 0.21), win[0] - 30, int(H * 0.72), 26, 185)
    text_block(dr, rnd, win[2] + 30, int(H * 0.21), W - m - 34, int(H * 0.72), 26, 185)
    dr.line([m + 30, int(H * 0.74), W - m - 30, int(H * 0.74)], fill=a, width=3)
    text_block(dr, rnd, m + 40, int(H * 0.76), W - m - 40, H - m - 40, 30, 200)
    # caption under the drawing: a larger word with a flourish
    x = int(W * 0.38); y = int(H * 0.715)
    for _ in range(5): x += glyph(dr, rnd, x, y, 44, 230) + 6
    stroke(dr, [(int(W * 0.33), y + 34), (int(W * 0.5), y + 44), (int(W * 0.67), y + 30)], 2, 5, 230)
    # a drop-cap ornament at the header start
    cx, cy = m + 70, m + 80
    for r in (46, 38): dr.ellipse([cx - r, cy - r, cx + r, cy + r], outline=a, width=3)
    glyph(dr, rnd, cx - 28, cy + 6, 64, 240)
    im = im.filter(ImageFilter.GaussianBlur(0.7))
    # ink absorbed by fibres: slightly irregular density
    arr = np.asarray(im).astype(np.float32)
    nz = np.random.default_rng(seed).random((H // 8 + 1, W // 8 + 1)).astype(np.float32)
    nz = np.asarray(Image.fromarray((nz * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)).astype(np.float32) / 255
    arr *= 0.75 + 0.35 * nz
    rgba = np.zeros((H, W, 4), np.uint8); rgba[..., 3] = np.clip(arr, 0, 255).astype(np.uint8)
    Image.fromarray(rgba, 'RGBA').save(out)

def splatter(W, H, seed, out, n_big=5):
    """screen ink splatter: organic blots (clusters of discs, blurred + thresholded = liquid edges), a few drips,
    satellite droplets with tails; black ink in alpha"""
    rnd = random.Random(seed); S = 2
    im = Image.new('L', (W * S, H * S), 0); dr = ImageDraw.Draw(im)
    for _ in range(n_big):
        cx = rnd.choice([rnd.uniform(-.05, .22), rnd.uniform(.78, 1.05)]) * W * S; cy = rnd.uniform(0, 1) * H * S
        R = rnd.uniform(50, 130) * S
        for _ in range(26):
            a = rnd.uniform(0, 2 * math.pi); d = R * rnd.random() ** 1.5; r = R * rnd.uniform(0.25, 0.6)
            x, y = cx + d * math.cos(a), cy + d * math.sin(a); dr.ellipse([x - r, y - r, x + r, y + r], fill=255)
        for _ in range(rnd.randint(4, 9)):        # splash arms: chains of shrinking discs
            a = rnd.uniform(0, 2 * math.pi); r = R * 0.3; d = R * 0.8
            while r > 2 * S:
                x, y = cx + d * math.cos(a), cy + d * math.sin(a); dr.ellipse([x - r, y - r, x + r, y + r], fill=255)
                d += r * 1.3; r *= rnd.uniform(0.6, 0.82); a += rnd.uniform(-0.12, 0.12)
        for _ in range(rnd.randint(1, 3)):        # drips running down
            x = cx + rnd.uniform(-R, R) * 0.6; y = cy + R * 0.4; ln = rnd.uniform(1.0, 3.5) * R; w = rnd.uniform(5, 12) * S
            dr.rounded_rectangle([x - w / 2, y, x + w / 2, y + ln], radius=w / 2, fill=255)
            dr.ellipse([x - w * 0.9, y + ln - w, x + w * 0.9, y + ln + w * 0.7], fill=255)
        for _ in range(rnd.randint(14, 30)):
            a = rnd.uniform(0, 2 * math.pi); d = R * rnd.uniform(1.4, 3.8); r = rnd.uniform(2, 9) * S
            x, y = cx + d * math.cos(a), cy + d * math.sin(a); dr.ellipse([x - r, y - r, x + r, y + r], fill=255)
    im = im.filter(ImageFilter.GaussianBlur(5 * S)).point(lambda v: 255 if v > 120 else (0 if v < 90 else (v - 90) * 8))
    im = im.resize((W, H), Image.LANCZOS)
    rgba = np.zeros((H, W, 4), np.uint8); rgba[..., 0] = 4; rgba[..., 1] = 2; rgba[..., 2] = 2; rgba[..., 3] = np.asarray(im)
    Image.fromarray(rgba, 'RGBA').save(out)

def mask(W, H, out, seed=3):
    """the White Page: a blank white mask — smooth oval, two narrow eye slits, no mouth; faint brush texture"""
    S = 2; im = Image.new('L', (W * S, H * S), 0); dr = ImageDraw.Draw(im)
    dr.ellipse([W * S * 0.12, H * S * 0.04, W * S * 0.88, H * S * 0.98], fill=255)
    dr.polygon([(W * S * 0.12, H * S * 0.45), (W * S * 0.5, H * S * 0.33), (W * S * 0.88, H * S * 0.45), (W * S * 0.5, H * S * 0.20)], fill=255)
    for sx in (-1, 1):
        cx = W * S * (0.5 + sx * 0.17); cy = H * S * 0.43
        dr.polygon([(cx - sx * W * S * 0.11, cy + H * S * 0.012), (cx + sx * W * S * 0.08, cy - H * S * 0.03), (cx + sx * W * S * 0.1, cy + H * S * 0.01),
                    (cx - sx * W * S * 0.06, cy + H * S * 0.035)], fill=0)
    im = im.filter(ImageFilter.GaussianBlur(1.2 * S)).resize((W, H), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    shade = 0.82 + 0.18 * np.clip(1 - np.hypot((xx - W * 0.42) / W, (yy - H * 0.38) / H) * 1.6, 0, 1)
    rgba = np.zeros((H, W, 4), np.uint8); v = np.clip(shade * 255, 0, 255).astype(np.uint8)
    rgba[..., 0] = v; rgba[..., 1] = v; rgba[..., 2] = (v * 0.98).astype(np.uint8); rgba[..., 3] = a.astype(np.uint8)
    Image.fromarray(rgba, 'RGBA').save(out)

if __name__ == '__main__':
    out = sys.argv[1]; os.makedirs(out, exist_ok=True)
    for i in range(8):
        page_script(1400, 1960, 100 + i, os.path.join(out, f'script_{i}.png'))
    splatter(1920, 1080, 7, os.path.join(out, 'splatter_a.png'), 4)
    splatter(1920, 1080, 11, os.path.join(out, 'splatter_b.png'), 6)
    mask(512, 680, os.path.join(out, 'mask.png'))
    print('ok')
