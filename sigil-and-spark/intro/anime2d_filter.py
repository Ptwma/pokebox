"""Sigil & Spark — '2D anime' look as a post filter over the crimson frames (prototype, option A).
cel fills (posterize in Lab with hard bands) + ink outlines with brush pressure + manga screentone in the
mid-shadows + hard-ringed sun/glow halos + paper grain. Deterministic per (frame, seed) so lines 'boil' on twos."""
import cv2, numpy as np, sys, os

def paper(h, w, seed=3):
    r = np.random.default_rng(seed)
    n = r.normal(0, 1, (h // 4, w // 4)).astype(np.float32)
    n = cv2.resize(cv2.GaussianBlur(n, (0, 0), 1.2), (w, h), interpolation=cv2.INTER_CUBIC)
    f = r.normal(0, 1, (h, w)).astype(np.float32)
    g = 0.5 * n + 0.25 * cv2.GaussianBlur(f, (0, 0), 0.7)
    return 1.0 + 0.035 * g  # multiplicative grain

def cel(img, levels=5):
    """flat fills: smooth, then quantise luminance into hard bands while keeping hue/chroma"""
    sm = img
    for _ in range(2): sm = cv2.bilateralFilter(sm, 9, 40, 9)
    lab = cv2.cvtColor(sm, cv2.COLOR_BGR2LAB).astype(np.float32)
    L = lab[..., 0] / 255.0
    Lq = np.floor(L * levels) / levels + (L > 0.9) * (1.0 / levels)   # floor: blacks stay black, whites stay white
    Lq = np.clip(0.85 * Lq + 0.15 * L, 0, 1)
    Lq[L < 0.12] = L[L < 0.12] * 0.6                      # crush the darks to ink
    lab[..., 0] = Lq * 255
    # push chroma a bit (anime colour) and flatten it
    ab = lab[..., 1:] - 128
    ab = cv2.medianBlur(np.clip(ab * 1.15 + 128, 0, 255).astype(np.uint8), 5).astype(np.float32)
    lab[..., 1:] = ab
    return cv2.cvtColor(np.clip(lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR), Lq

def ink_lines(img, seed, thick=2.2):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    g = cv2.bilateralFilter(g, 7, 30, 7)
    e = cv2.Canny(g, 30, 85)
    # drop tiny noise specks
    n, lab, st, _ = cv2.connectedComponentsWithStats(e, 8)
    keep = np.zeros(n, bool); keep[1:] = st[1:, cv2.CC_STAT_AREA] > 40
    e = (keep[lab] * 255).astype(np.uint8)
    # brush pressure: thickness varies smoothly across the frame (noise field), lines boil per seed
    r = np.random.default_rng(seed)
    h, w = e.shape
    fld = cv2.resize(r.random((h // 64 + 2, w // 64 + 2)).astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)
    d1 = cv2.dilate(e, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2)))
    d2 = cv2.dilate(e, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(thick * 2) | 1, int(thick * 2) | 1)))
    line = np.where(fld > 0.55, d2, d1).astype(np.float32) / 255.0
    # wobble (hand-drawn): small displacement field
    dx = cv2.GaussianBlur(r.normal(0, 1, (h, w)).astype(np.float32), (0, 0), 18) * 60
    dy = cv2.GaussianBlur(r.normal(0, 1, (h, w)).astype(np.float32), (0, 0), 18) * 60
    xx, yy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    line = cv2.remap(line, xx + dx, yy + dy, cv2.INTER_LINEAR)
    return cv2.GaussianBlur(line, (0, 0), 0.6)

def screentone(Lq, h, w, cell=7):
    """manga dots in the mid-dark band only"""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    a = np.deg2rad(45)
    u = (xx * np.cos(a) + yy * np.sin(a)) / cell; v = (-xx * np.sin(a) + yy * np.cos(a)) / cell
    d = np.hypot(u - np.floor(u) - .5, v - np.floor(v) - .5)
    band = ((Lq > 0.15) & (Lq < 0.38)).astype(np.float32)
    band = cv2.GaussianBlur(band, (0, 0), 1.5)
    dots = (d < 0.28).astype(np.float32)
    return band * dots

def halo_rings(img):
    """anime light: 2 hard rings in the light's own colour around very bright spots (not a grey bloom)"""
    f = img.astype(np.float32) / 255
    g = f.max(2)
    m = (g > 0.92).astype(np.float32)
    col = cv2.GaussianBlur(f * m[..., None], (0, 0), 6) / np.maximum(cv2.GaussianBlur(m, (0, 0), 6)[..., None], 1e-3)
    out = np.zeros_like(f)
    for sig, thr, a in ((10, 0.18, 0.55), (26, 0.10, 0.28)):
        b = cv2.GaussianBlur(m, (0, 0), sig)
        ring = cv2.GaussianBlur((b > thr).astype(np.float32), (0, 0), 1.0)
        c2 = cv2.GaussianBlur(col, (0, 0), sig)
        out = np.maximum(out, ring[..., None] * a * np.clip(c2 * np.array([0.8, 0.9, 1.25], np.float32), 0, 1))
    return out

def frame(img, seed=0, levels=5):
    h, w = img.shape[:2]
    c, Lq = cel(img, levels)
    out = c.astype(np.float32) / 255
    # halos (warm)
    out = out + halo_rings(img) * (1 - out)
    # screentone darkens
    st = screentone(Lq, h, w)[..., None]
    out *= 1 - 0.22 * st
    # ink: near-black warm ink; on dark areas draw a thin red rim instead so the line still reads
    ln = ink_lines(img, seed)[..., None]
    lum = cv2.cvtColor(c, cv2.COLOR_BGR2GRAY).astype(np.float32)[..., None] / 255
    ln = ln * np.clip((lum - 0.06) / 0.1, 0, 1)            # no lines inside the black masses (they were noise)
    ink = np.array([0.04, 0.03, 0.06], np.float32)
    out = out * (1 - ln) + ink * ln
    out *= paper(h, w)[..., None]
    return np.clip(out * 255, 0, 255).astype(np.uint8)

if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    im = cv2.imread(src)
    cv2.imwrite(dst, frame(im, seed=int(sys.argv[3]) if len(sys.argv) > 3 else 0))
