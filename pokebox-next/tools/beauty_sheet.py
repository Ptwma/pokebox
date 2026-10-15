# Pokebox Next — contact sheet of the 12 beauty cams (+ suspect shots) with PASS/FAIL and the "judge:" caption.
# usage: python beauty_sheet.py <pbx_auto dir> <out.jpg> [<previous pbx_auto dir> for a before/after sheet]
import sys, os, glob
from PIL import Image, ImageDraw, ImageFont

ALIAS = {'bc_08_battle_wild': '13_battle_intro', 'bc_10_battle_trainer': '25_trainer_battle'}

def font(sz):
    for f in ('DejaVuSans-Bold.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 'arialbd.ttf'):
        try: return ImageFont.truetype(f, sz)
        except Exception: pass
    return ImageFont.load_default()

def notes(d):
    N = {}
    p = os.path.join(d, 'beauty.txt')
    if os.path.exists(p):
        for l in open(p, encoding='utf-8'):
            parts = l.rstrip('\n').split('\t')
            if len(parts) >= 3: N[parts[0]] = (parts[1], parts[2])
    return N

def shot(d, cid):
    for name in (cid, cid + '_FAIL', ALIAS.get(cid, '')):
        if name and os.path.exists(os.path.join(d, name + '.png')): return os.path.join(d, name + '.png')
    return None

def ids(d, N):
    base = ['bc_%02d' % i for i in range(1, 13)]
    out = []
    for b in base:
        m = [k for k in N if k.startswith(b)] or [os.path.basename(p)[:-4].replace('_FAIL', '') for p in glob.glob(os.path.join(d, b + '_*.png'))]
        out.append(sorted(m)[0] if m else b)
    out += sorted(k for k in N if k.startswith('bc_13'))
    return out

def tile(path, w, h, label, status, judge, F, f):
    t = Image.new('RGB', (w, h + 64), (24, 24, 28))
    if path: im = Image.open(path).convert('RGB'); im.thumbnail((w, h)); t.paste(im, ((w - im.width) // 2, 0))
    else: ImageDraw.Draw(t).text((20, h // 2), 'NO SHOT', fill=(255, 80, 80), font=F)
    d = ImageDraw.Draw(t)
    col = (90, 220, 120) if status.startswith(('PASS', 'ALIAS', 'INFO')) else (255, 90, 90)
    d.rectangle([0, h, w, h + 64], fill=(18, 18, 22))
    d.text((8, h + 4), label, fill=(255, 255, 255), font=F)
    d.text((w - 8 - d.textlength(status[:34], font=F), h + 4), status[:34], fill=col, font=F)
    d.text((8, h + 34), ('judge: ' + judge)[:110], fill=(200, 200, 210), font=f)
    return t

def sheet(d, out, cols=4, w=640, h=360, title='Pokebox Next — beauty cams'):
    N = notes(d); I = ids(d, N); F, f = font(20), font(14)
    rows = (len(I) + cols - 1) // cols
    S = Image.new('RGB', (cols * w, rows * (h + 64) + 50), (10, 10, 12))
    ImageDraw.Draw(S).text((12, 12), title, fill=(255, 255, 255), font=font(24))
    for k, cid in enumerate(I):
        st, jd = N.get(cid, ('?', ''))
        S.paste(tile(shot(d, cid), w, h, cid, st, jd, F, f), ((k % cols) * w, 50 + (k // cols) * (h + 64)))
    S.save(out, quality=86); return out

if __name__ == '__main__':
    d, out = sys.argv[1], sys.argv[2]
    print(sheet(d, out))
