# Pokebox Next — paints clothes onto the Quaternius Universal Base Characters (which are bare "superhero" bodies).
# Input: <tag>_uvpos.json (per triangle: UVs, world positions, head/hand/body label — dumped from Blender) and the
# body's base-colour texture. Every texel gets its 3D position by rasterising the triangles in UV space, then simple
# rules on height / arm reach decide what it is wearing (jacket, sleeves, trousers, skirt, boots...). The original
# texture's shading stays underneath, garment borders get a comic ink seam.
# Usage: python outfits.py <dir with jsons + textures> <out dir>
import sys, os, json
import numpy as np
from PIL import Image
from scipy import ndimage

S = 2048

def raster(tag, d):
    T = json.load(open(os.path.join(d, tag + '_uvpos.json')))
    P = np.zeros((S, S, 3), np.float32); L = np.zeros((S, S), np.uint8); M = np.zeros((S, S), bool)
    lab = {'body': 0, 'head': 1, 'neck': 2, 'hand': 3}
    for uvs, pos, regs in T:
        uv = np.array(uvs, np.float64) * [S, -S] + [0, S]; pp = np.array(pos, np.float32)
        x0, y0 = np.floor(uv.min(0)).astype(int); x1, y1 = np.ceil(uv.max(0)).astype(int)
        x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, S - 1), min(y1, S - 1)
        if x1 < x0 or y1 < y0: continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + .5, np.arange(y0, y1 + 1) + .5)
        (ax, ay), (bx, by), (cx, cy) = uv
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-9: continue
        w0 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / den
        w1 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / den
        w2 = 1 - w0 - w1
        ins = (w0 >= -.01) & (w1 >= -.01) & (w2 >= -.01)
        if not ins.any(): continue
        W = np.stack([w0, w1, w2], -1)[ins]
        ys, xs = np.nonzero(ins); ys += y0; xs += x0
        P[ys, xs] = W @ pp
        best = np.argmax(W, 1); L[ys, xs] = np.array([lab[r] for r in regs])[best]; M[ys, xs] = True
    # grow the islands a few texels so seams never show the fallback colour
    idx = ndimage.distance_transform_edt(~M, return_distances=False, return_indices=True)
    P = P[idx[0], idx[1]]; L = L[idx[0], idx[1]]
    return P, L, M

# outfit = dict(top, sleeves: long|short|none, bottom, legs: long|shorts|skirt|knee, shoes, belt, skin tint, extras)
OUTFITS = {   # body paint under the 3D clothes (clothes.py) — same palette, so gaps between garments never show bare skin
    'player_m': dict(body='male', top=(.80, .13, .10), sleeves='long', sleeve_col=(.12, .12, .14), bottom=(.14, .18, .34), legs='long', shoes=(.95, .95, .95), boots_z=.085, belt=(.18, .12, .08)),
    'player_f': dict(body='female', top=(.97, .97, .97), sleeves='none', bottom=(.85, .2, .32), legs='skirt', skirt_z=.36, shoes=(.85, .2, .32), boots_z=.30),
    'mom': dict(body='female', top=(.62, .5, .78), sleeves='long', bottom=(.86, .78, .6), legs='skirt', skirt_z=.18, shoes=(.35, .2, .12), boots_z=.085, skin=1.12),
    'vale': dict(body='female', top=(.96, .96, .95), sleeves='long', bottom=(.25, .26, .3), legs='long', coat_z=.30, shoes=(.28, .16, .1), boots_z=.085, skin=1.08),
    'aide': dict(body='male', top=(.93, .95, .97), sleeves='short', bottom=(.75, .66, .45), legs='long', coat_z=.47, shoes=(.25, .15, .08), boots_z=.085, skin=1.15),
    'rho': dict(body='male', top=(.15, .40, .80), sleeves='long', bottom=(.12, .12, .14), legs='shorts', shoes=(.97, .97, .97), boots_z=.17, skin=.95),
    'fisher': dict(body='male', top=(.97, .80, .12), sleeves='long', bottom=(.2, .35, .22), legs='long', coat_z=.42, shoes=(.12, .25, .14), boots_z=.27, skin=1.05),
    'gardener': dict(body='female', top=(.95, .93, .88), sleeves='short', bottom=(.30, .52, .28), legs='long', shoes=(.4, .25, .12), boots_z=.2, skin=1.0),
    'merchant': dict(body='female', top=(.92, .50, .15), sleeves='short', bottom=(.45, .2, .3), legs='skirt', skirt_z=.10, shoes=(.45, .3, .15), boots_z=.085, skin=.9),
    'kid': dict(body='male', top=(.95, .82, .2), stripes=(.85, .2, .15), sleeves='short', bottom=(.25, .4, .7), legs='shorts', shoes=(.97, .97, .97), boots_z=.17, skin=1.1),
    'conductor': dict(body='female', top=(.14, .18, .34), sleeves='long', bottom=(.14, .18, .34), legs='skirt', skirt_z=.22, shoes=(.06, .06, .06), boots_z=.09, skin=1.05),
    'guard': dict(body='male', top=(.2, .3, .22), sleeves='long', bottom=(.18, .26, .2), legs='long', coat_z=.47, shoes=(.06, .06, .06), boots_z=.24, belt=(.08, .07, .06), skin=.85),
}

def paint(name, o, P, L, base):
    H = P[..., 2].max(); x, y, z = P[..., 0] / H, P[..., 1] / H, P[..., 2] / H   # normalised: height 0..1
    ax = np.abs(x)
    hand = L == 3; head = (L == 1); neck = L == 2
    wrist = np.percentile(ax[hand], 5) if hand.any() else .3
    shoulder = .115; elbow = (shoulder + wrist) * .5
    arm = (ax > shoulder) & (z > .55) & ~hand & ~head
    torso = ~arm & ~hand & ~head & ~neck & (z >= .52)
    legs = ~arm & ~hand & ~head & (z < .52)
    out = base.astype(np.float32) / 255.
    lum = out @ [.299, .587, .114]; shade = np.clip(.78 + .45 * (lum - np.median(lum[torso])) / max(1e-3, np.median(lum[torso])), .55, 1.2)
    gid = np.zeros(z.shape, np.int32)   # garment id (for ink seams)
    def put(mask, col, k):
        out[mask] = np.array(col)[None, :] * shade[mask][:, None]; gid[mask] = k
    skin = o.get('skin', 1.0)
    out[head | neck | hand] *= skin
    # top
    top = torso.copy(); put(top, o['top'], 1)
    if 'stripes' in o: put(top & ((np.floor(z * 60) % 2) == 0), o['stripes'], 2)
    sl = o['sleeves']
    if sl == 'long': sleeve = arm & (ax < wrist - .004)
    elif sl == 'short': sleeve = arm & (ax < shoulder + (elbow - shoulder) * .55)
    else: sleeve = arm & False
    put(sleeve, o.get('sleeve_col', o['top']), 3)
    if 'collar' in o: put(neck & (z < .86), o['collar'], 4)
    elif sl != 'none': put(neck & (z < .845), o['top'], 1)
    # bottom
    leg_kind = o['legs']
    if leg_kind == 'long': bot = legs & (z > .04)
    elif leg_kind == 'shorts': bot = legs & (z > .33)
    elif leg_kind == 'skirt': bot = legs & (z > o.get('skirt_z', .28))
    else: bot = legs & (z > .27)
    put(bot, o['bottom'], 5)
    if 'coat_z' in o:  # lab coat over everything down to coat_z, open at the front (inner trousers show between)
        coat = (legs & (z > o['coat_z']) & ~((y < 0) & (ax < .035))) | top
        put(coat, o['top'], 6)
    shoe_z = o.get('boots_z', .065)
    put(legs & (z <= shoe_z), o['shoes'], 7)
    if 'belt' in o: put((top | bot) & (np.abs(z - .555) < .012), o['belt'], 8)
    if 'zip' in o: put(top & (y < 0) & (ax < .004) & (z > .56) & (z < .82), o['zip'], 9)
    # comic ink seams between garments / skin
    edge = np.zeros_like(gid, bool)
    for s in (1, 2, 3):
        edge |= gid != np.roll(gid, s, 0); edge |= gid != np.roll(gid, s, 1)
    out[edge] *= .28
    return (np.clip(out, 0, 1) * 255).astype(np.uint8)

if __name__ == '__main__':
    d, outd = sys.argv[1], sys.argv[2]; os.makedirs(outd, exist_ok=True)
    tex = {'male': 'T_Superhero_Male_Dark.png', 'female': 'T_Superhero_Female_Dark_BaseColor.png'}
    cache = {}
    for name, o in OUTFITS.items():
        b = o['body']
        if b not in cache:
            P, L, M = raster(b, d); base = np.asarray(Image.open(os.path.join(d, tex[b])).convert('RGB').resize((S, S), Image.LANCZOS))
            cache[b] = (P, L, base); print('rasterised', b, round(float(P[..., 2].max()), 3))
        P, L, base = cache[b]
        Image.fromarray(paint(name, o, P, L, base)).save(os.path.join(outd, f'T_Outfit_{name}.png')); print('painted', name)
