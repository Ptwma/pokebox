#!/usr/bin/env python3
"""Pokebox — slim a VRM (GLB) for the game without touching its VRM extensions:
every embedded image is downscaled (max side MAX) and re-encoded — JPEG when it has no transparency, PNG otherwise.
Usage: python3 vrm_slim.py in.vrm out.vrm [MAX=1024]"""
import io, json, struct, sys
from PIL import Image

def read_glb(path):
    b = open(path, 'rb').read()
    magic, ver, length = struct.unpack_from('<4sII', b, 0); assert magic == b'glTF', 'not a GLB'
    off, js, binb = 12, None, b''
    while off < length:
        clen, ctype = struct.unpack_from('<II', b, off); data = b[off + 8: off + 8 + clen]
        if ctype == 0x4E4F534A: js = json.loads(data.decode('utf8'))
        elif ctype == 0x004E4942: binb = data
        off += 8 + clen
    return js, binb

def write_glb(path, js, binb):
    j = json.dumps(js, separators=(',', ':')).encode('utf8'); j += b' ' * ((4 - len(j) % 4) % 4)
    binb += b'\0' * ((4 - len(binb) % 4) % 4)
    out = struct.pack('<4sII', b'glTF', 2, 12 + 8 + len(j) + 8 + len(binb)) + struct.pack('<II', len(j), 0x4E4F534A) + j + struct.pack('<II', len(binb), 0x004E4942) + binb
    open(path, 'wb').write(out)

def main(src, dst, mx=1024):
    js, binb = read_glb(src)
    views = js['bufferViews']; img_views = {im['bufferView']: i for i, im in enumerate(js.get('images', [])) if 'bufferView' in im}
    new_bin = bytearray(); remap = {}
    for vi, v in enumerate(views):
        data = binb[v.get('byteOffset', 0): v.get('byteOffset', 0) + v['byteLength']]
        if vi in img_views:
            im = Image.open(io.BytesIO(data)); im.load()
            if max(im.size) > mx: k = mx / max(im.size); im = im.resize((max(1, round(im.size[0] * k)), max(1, round(im.size[1] * k))), Image.LANCZOS)
            alpha = im.mode in ('RGBA', 'LA', 'P') and im.convert('RGBA').getextrema()[3][0] < 250
            buf = io.BytesIO()
            if alpha: im.convert('RGBA').save(buf, 'PNG', optimize=True); mime = 'image/png'
            else: im.convert('RGB').save(buf, 'JPEG', quality=86, optimize=True); mime = 'image/jpeg'
            data = buf.getvalue(); js['images'][img_views[vi]]['mimeType'] = mime
        while len(new_bin) % 4: new_bin.append(0)
        v['byteOffset'] = len(new_bin); v['byteLength'] = len(data); new_bin += data
    js['buffers'][0]['byteLength'] = len(new_bin)
    write_glb(dst, js, bytes(new_bin))

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 1024)
