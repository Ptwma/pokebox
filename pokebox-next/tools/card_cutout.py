# Pokebox Next — card art -> die-cut "paper Echo" PNG (port of pokebox-game/js/cutout.worker.js).
# U^2-Net-small (u2netp, Apache-2.0) segments the Pokemon in the card's art window; the result gets a white border
# and an ink line (sticker look) and is trimmed. Card images are copyrighted: inputs/outputs stay on the user's PC,
# never in git.  Usage: python card_cutout.py MODEL.onnx OUT_DIR card1.jpg card2.jpg ...
import sys, os
import numpy as np
import onnxruntime as ort
from PIL import Image, ImageFilter
from scipy import ndimage

N = 320

def run_model(sess, img):
    a = np.asarray(img.resize((N, N), Image.BILINEAR), dtype=np.float32) / 255.0
    a = (a - [.485, .456, .406]) / [.229, .224, .225]
    inp = a.transpose(2, 0, 1)[None].astype(np.float32)
    m = sess.run(None, {sess.get_inputs()[0].name: inp})[0][0, 0]
    return (m - m.min()) / (m.max() - m.min() + 1e-6)

def clean(mn):
    lab, n = ndimage.label(mn > .5)
    if n == 0: return None
    areas = ndimage.sum(np.ones_like(mn), lab, range(1, n + 1)); big = areas.max()
    keep = np.isin(lab, [i + 1 for i, a in enumerate(areas) if a >= big * .12 and a > 60])
    keep = ndimage.binary_fill_holes(keep)
    frac = keep.mean(); edge = np.concatenate([keep[0], keep[-1], keep[:, 0], keep[:, -1]]).mean()
    ok = .045 < frac < .58 and edge < .36 and big / keep.sum() > .62
    return keep if ok else None

def attempt(sess, im, box, oval=False):
    W, H = im.size; x, y, w, h = box[0] * W, box[1] * H, box[2] * W, box[3] * H
    win = im.crop((int(x), int(y), int(x + w), int(y + h)))
    mn = run_model(sess, win); keep = clean(mn)
    if keep is None and oval:
        yy, xx = np.mgrid[0:N, 0:N]; keep = ((xx / N - .5) / .47) ** 2 + ((yy / N - .52) / .47) ** 2 < 1; mn = np.where(keep, np.maximum(mn, .75), 0)
    if keep is None: return None
    grown = ndimage.binary_dilation(keep, iterations=1)
    a = np.clip((mn - .3) / .4, 0, 1) * grown; a = np.where(keep, np.maximum(a, .85), a)
    outW = 512; outH = round(outW * h / w)
    art = win.convert('RGB').resize((outW, outH), Image.LANCZOS)
    alpha = Image.fromarray((a * 255).astype(np.uint8)).resize((outW, outH), Image.BILINEAR)
    P = 22; cw, ch = outW + 2 * P, outH + 2 * P
    A = np.zeros((ch, cw), np.float32); A[P:P + outH, P:P + outW] = np.asarray(alpha, np.float32) / 255
    solid = A > .35
    white = ndimage.binary_dilation(solid, iterations=10); ink = ndimage.binary_dilation(solid, iterations=14)
    out = np.zeros((ch, cw, 4), np.float32)
    out[ink] = [.08, .06, .11, 1]; out[white] = [1, .98, .94, 1]
    rgb = np.zeros((ch, cw, 3), np.float32); rgb[P:P + outH, P:P + outW] = np.asarray(art, np.float32) / 255
    k = A[..., None]; out[..., :3] = out[..., :3] * (1 - k) + rgb * k; out[..., 3] = np.maximum(out[..., 3], A)
    img = Image.fromarray((out * 255).astype(np.uint8), 'RGBA').filter(ImageFilter.SMOOTH)
    bb = img.getbbox(); img = img.crop(bb)
    # square power-of-two canvas, creature standing on the bottom edge (pivot = feet)
    S = 1024; s = min(S / img.width, S / img.height) * .98
    img = img.resize((max(1, round(img.width * s)), max(1, round(img.height * s))), Image.LANCZOS)
    canvas = Image.new('RGBA', (S, S), (0, 0, 0, 0)); canvas.paste(img, ((S - img.width) // 2, S - img.height))
    return canvas, img.width / S, img.height / S

def make(sess, path):
    im = Image.open(path).convert('RGB')
    for box, oval in (((.075, .095, .85, .42), False), ((.04, .05, .92, .62), False), ((.075, .095, .85, .42), True)):
        r = attempt(sess, im, box, oval)
        if r: return r

if __name__ == '__main__':
    model, out = sys.argv[1], sys.argv[2]; os.makedirs(out, exist_ok=True)
    sess = ort.InferenceSession(model, providers=['CPUExecutionProvider'])
    for p in sys.argv[3:]:
        img, fw, fh = make(sess, p); name = os.path.splitext(os.path.basename(p))[0]
        img.save(os.path.join(out, 'T_Echo_' + name + '.png')); print(name, round(fw, 3), round(fh, 3))
