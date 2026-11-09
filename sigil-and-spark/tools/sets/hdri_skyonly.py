# Sigil & Spark — keeps only the SKY of a Poly Haven HDRI: below ~14 deg of elevation the photo's own ground (hills, houses,
# trees) is replaced by the sky colour just above that line, blurred along the horizon, so our own 3D coast, fort and ships
# stand on the horizon instead of a stretched photo. Writes <name>_skyonly.exr next to the original.
#   blender -b --factory-startup --python hdri_skyonly.py -- <in.exr> [cut_deg=14] [band_deg=8]
import bpy, sys, os
import numpy as np
argv = sys.argv[sys.argv.index('--') + 1:]
src = argv[0]; cut = float(argv[1]) if len(argv) > 1 else 14.0; band = float(argv[2]) if len(argv) > 2 else 8.0
img = bpy.data.images.load(src); W, H = img.size
px = np.array(img.pixels[:], dtype=np.float32).reshape(H, W, 4)      # Blender rows go bottom → top
elev = (np.arange(H) + 0.5) / H * 180.0 - 90.0                         # row → elevation in degrees
r0 = int(np.searchsorted(elev, cut)); r1 = int(np.searchsorted(elev, cut + 4.0))
ref = px[r0:r1].mean(axis=0)                                           # the sky just above the cut, per column
k = max(3, W // 64); ker = np.ones(k) / k
for c in range(3): ref[:, c] = np.convolve(np.concatenate([ref[-k:, c], ref[:, c], ref[:k, c]]), ker, 'same')[k:-k]
w = np.clip((elev - (cut - band)) / band, 0.0, 1.0)[:, None, None]     # 1 above the cut, 0 below cut - band
out = px.copy(); out[..., :3] = px[..., :3] * w + ref[None, :, :3] * (1.0 - w)
dst = os.path.splitext(src)[0].replace('_4k', '') + '_skyonly.exr'
o = bpy.data.images.new('skyonly', W, H, float_buffer=True, alpha=False)
o.pixels[:] = out.ravel(); o.filepath_raw = dst; o.file_format = 'OPEN_EXR'; o.save()
print('SKYONLY', dst, W, H)
