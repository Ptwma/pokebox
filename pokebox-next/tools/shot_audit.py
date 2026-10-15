# Pokebox Next — checks every autotest screenshot for frames a human would call broken:
#   BLACK  mean luminance < 12 (blank / black screen)      FLAT  > 92 % of pixels within 6 levels of one colour
# usage: python shot_audit.py <pbx_auto dir>   -> prints one line per bad shot, exit code 1 if any
import sys, os, glob
from PIL import Image, ImageStat

def check(p):
    im = Image.open(p).convert('L').resize((320, 180))
    mean = ImageStat.Stat(im).mean[0]
    if mean < 12: return 'BLACK (mean %.1f)' % mean
    h = im.histogram(); top = max(sum(h[max(0, i - 6):i + 7]) for i in range(256))
    if top > .92 * 320 * 180: return 'FLAT (%.0f%% one tone)' % (100.0 * top / (320 * 180))
    return None

if __name__ == '__main__':
    bad = 0
    for p in sorted(glob.glob(os.path.join(sys.argv[1], '*.png'))):
        r = check(p)
        if r: bad += 1; print('FAIL', os.path.basename(p), r)
    print('shots checked, bad:', bad); sys.exit(1 if bad else 0)
