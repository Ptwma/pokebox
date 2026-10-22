# Pokebox Next — tileable ripple normal map for the sea / stream materials (2026-10-23).
# Sum of ~40 random sine waves whose frequencies are whole numbers of cycles per tile (so it tiles perfectly),
# biased to short wavelengths; height -> normal by central differences. OpenGL convention (green up).
# Run inside Blender (numpy): exec(open(r"...\PokeboxNext_src\tools\water_normal.py").read())
import os, math
import numpy as np
import bpy

OUT = os.path.join(os.environ.get('PBX_OUT', r"E:\GAME-APP-DEV\POKEMON\PokeboxNext_src"), 'tex', 'T_WaterNormal.png')
N = 512; rng = np.random.default_rng(11)
y, x = np.mgrid[0:N, 0:N] / N
h = np.zeros((N, N))
for i in range(44):
    kx, ky = rng.integers(-14, 15, 2)
    if kx == 0 and ky == 0: continue
    k = math.hypot(kx, ky); amp = 1.0 / (k ** 1.25)
    h += amp * np.sin(2 * math.pi * (kx * x + ky * y) + rng.random() * 6.283)
h /= np.abs(h).max()
s = 6.0
dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * s; dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * s
n = np.stack([-dx, -dy, np.ones_like(h)], -1); n /= np.linalg.norm(n, axis=-1, keepdims=True)
rgba = np.ones((N, N, 4), np.float32); rgba[..., :3] = n * .5 + .5
im = bpy.data.images.new('T_WaterNormal', N, N, alpha=True, float_buffer=False); im.colorspace_settings.name = 'Non-Color'
im.pixels.foreach_set(rgba.ravel()); im.filepath_raw = OUT; im.file_format = 'PNG'; im.save(); bpy.data.images.remove(im)
print('water normal ->', OUT)
