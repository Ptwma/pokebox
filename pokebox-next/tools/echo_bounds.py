# Pokebox Next — measures the opaque box of every Echo cut-out (PokeboxNext_src/echo/T_Echo_<CardId>.png, local only)
# and writes PokeboxNext/Content/PBX/Data/echo_bounds.json: { "<CardId>": [u0, v0, u1, v1] } (0..1, v from the TOP).
# APBXEcho::Setup uses it to size every Echo by its visible art and to stand its lowest pixel on the ground.
# Run inside Blender (no PIL needed):  exec(open(r"...\PokeboxNext_src\tools\echo_bounds.py").read())
import os, json, glob
import numpy as np
import bpy

SRC = r"E:\GAME-APP-DEV\POKEMON\PokeboxNext_src"
OUT = r"E:\GAME-APP-DEV\POKEMON\PokeboxNext\Content\PBX\Data\echo_bounds.json"

def bounds(path, thr=0.35):
    im = bpy.data.images.load(path, check_existing=False)
    try:
        w, h = im.size
        px = np.empty(w * h * 4, np.float32); im.pixels.foreach_get(px)
        a = px.reshape(h, w, 4)[::-1, :, 3]          # Blender rows run bottom-up -> flip so row 0 is the top
        ys, xs = np.nonzero(a > thr)
        if not len(xs): return None
        return [round(xs.min() / w, 4), round(ys.min() / h, 4), round((xs.max() + 1) / w, 4), round((ys.max() + 1) / h, 4)]
    finally:
        bpy.data.images.remove(im)

res = {}
for p in sorted(glob.glob(os.path.join(SRC, 'echo', 'T_Echo_*.png'))):
    cid = os.path.basename(p)[len('T_Echo_'):-4]
    b = bounds(p)
    if b: res[cid] = b
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(res, open(OUT, 'w'), indent=0)
print('echo bounds', len(res), '->', OUT)
