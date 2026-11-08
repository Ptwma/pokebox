# Sigil & Spark — SET QA (review gate for the set scripts). Run a set script with the camera name 'qa':
#   blender -b --python set_scriptorium.py -- <SRC> <OUTDIR>/scriptorium.png qa
# Writes <OUTDIR>/<set>_qa.json and review images:
#   <set>_qa_top.png         top-down ortho, one random colour per object (detached / misplaced pieces stand out)
#   <set>_qa_<cam>.png       every story camera in Workbench (material colours + cavity + outlines)
#   <set>_qa_props.png       contact sheet: every dressing prop seen from the audience side (facing / scale check)
# Checks (numbers first, then look — the asset-QA gate from EL4CTEO/blender-skills, MIT, adapted for whole sets):
#   in_wall     a prop's triangles intersect a wall piece           → move it out / turn it
#   floating    a prop's lowest point hangs > 4 cm above what is under it (hanging things excepted)
#   sunk        a prop sits > 5 cm into the surface under it
#   zfight      coplanar same-facing overlapping faces of two different objects (< 2 mm apart)
#   inside_out  closed parts whose normals point inward; inconsistent winding
#   orphan      a kit/wall piece touching nothing at all
import bpy, bmesh, json, math, os, random
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

HANG = ('lantern', 'lamp', 'banner', 'sign', 'net', 'chandelier', 'rope', 'laundry', 'cloth', 'flag', 'sconce', 'torch', 'shelf', 'mast',
        'boat', 'bird', 'gull', 'poster', 'board', 'hook', 'bell', 'beam')

def _world_bm(objs):
    dg = bpy.context.evaluated_depsgraph_get(); bm = bmesh.new()
    for o in objs:
        if o.type != 'MESH': continue
        t = bmesh.new(); t.from_object(o, dg); t.transform(o.matrix_world)
        me = bpy.data.meshes.new('_qa'); t.to_mesh(me); t.free(); bm.from_mesh(me); bpy.data.meshes.remove(me)
    return bm

def _bvh(objs):
    bm = _world_bm(objs)
    if not bm.faces: bm.free(); return None, None
    tree = BVHTree.FromBMesh(bm); return tree, bm

def _bbox(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs if o.type == 'MESH' for c in o.bound_box]
    if not pts: return None
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))

def _ov(a, b, pad=0.0):
    return all(a[0][i] - pad < b[1][i] and b[0][i] - pad < a[1][i] for i in range(3))

def _ray_down(x, y, z, ignore):
    dg = bpy.context.evaluated_depsgraph_get(); o = Vector((x, y, z)); d = Vector((0, 0, -1))
    for _ in range(12):
        hit, loc, nrm, idx, ob, mw = bpy.context.scene.ray_cast(dg, o, d, distance=50)
        if not hit: return None, None
        if ob.name not in ignore and ob.original.name not in ignore and not ob.original.name.startswith(globals().get('NOSUPPORT', ('Prop_Vine',))): return loc.z, ob.name
        o = loc + d * 0.002
    return None, None

def _normals(o):
    bm = bmesh.new(); bm.from_mesh(o.data); bm.transform(o.matrix_world)
    par = list(range(len(bm.verts)))
    def f(i):
        while par[i] != i: par[i] = par[par[i]]; i = par[i]
        return i
    for e in bm.edges:
        a, b = f(e.verts[0].index), f(e.verts[1].index)
        if a != b: par[a] = b
    isl = [f(i) for i in range(len(bm.verts))]
    closed, vol, ref = {}, {}, {}
    for v in bm.verts: ref.setdefault(isl[v.index], v.co.copy())
    for e in bm.edges:
        if len(e.link_faces) != 2: closed[isl[e.verts[0].index]] = False
    for fc in bm.faces:
        g = isl[fc.verts[0].index]; c0 = ref[g]; vs = [v.co - c0 for v in fc.verts]
        for k in range(1, len(vs) - 1): vol[g] = vol.get(g, 0) + vs[0].dot(vs[k].cross(vs[k + 1])) / 6
    from collections import Counter
    dirs = Counter((l.vert.index, l.link_loop_next.vert.index) for fc in bm.faces for l in fc.loops)
    inv = sum(1 for g, v in vol.items() if closed.get(g, True) and v < -1e-9)
    inc = sum(1 for k, c in dirs.items() if c > 1)
    bm.free(); return inv, inc

def set_qa(cams):
    bpy.context.view_layer.update()
    outdir = os.path.dirname(OUT); name = globals().get('SETNAME') or os.path.splitext(os.path.basename(OUT))[0]; os.makedirs(outdir, exist_ok=True)
    rep = {'set': name, 'in_wall': [], 'floating': [], 'sunk': [], 'zfight': [], 'inside_out': [], 'orphan': [], 'props': 0}
    meshes = [o for o in bpy.data.objects if o.type == 'MESH' and o.visible_get()]
    walls = [o for o in meshes if o.name.startswith(('Wall', 'Sill')) and 'Arch' not in o.name]
    roots = [o for o in bpy.data.objects if o.name.startswith('P_') and o.parent is None]
    kitprops = [o for o in meshes if o.name.startswith('Prop_') and not o.name.startswith('Prop_Vine')]
    rep['props'] = len(roots); rep['where'] = {}
    for r in roots:
        b = _bbox([o for o in r.children_recursive if o.type == 'MESH'])
        if b: rep['where'][r.name] = {'min': [round(v, 2) for v in b[0]], 'max': [round(v, 2) for v in b[1]], 'rz': round(math.degrees(r.rotation_euler.z) % 360)}
    wtrees = []
    for w in walls:
        t, bm = _bvh([w]); bb = _bbox([w])
        if t: wtrees.append((w.name, t, bb)); bm.free()
    for kp in kitprops:   # kit props (Prop_Wagon, Prop_Crate...) against the walls too
        bb = _bbox([kp]); t, bm = _bvh([kp])
        if not t: continue
        hits = [(wn, len(t.overlap(wt))) for wn, wt, wbb in wtrees if _ov(bb, wbb)]
        hits = [h for h in hits if h[1]]
        if hits: rep['in_wall'].append({'prop': kp.name, 'at': [round(v, 2) for v in kp.location], 'walls': sorted(hits, key=lambda h: -h[1])[:3]})
        bm.free()
    print('QA step props', flush=True)
    # --- props: walls, support
    for r in roots:
        kids = [o for o in r.children_recursive if o.type == 'MESH']
        if not kids: continue
        bb = _bbox(kids); t, bm = _bvh(kids)
        if not t: continue
        hits = []
        for wn, wt, wbb in wtrees:
            if not _ov(bb, wbb): continue
            n = len(t.overlap(wt))
            if n: hits.append((wn, n))
        if hits:
            hits.sort(key=lambda h: -h[1])
            rep['in_wall'].append({'prop': r.name, 'at': [round(v, 2) for v in r.location], 'walls': hits[:3]})
        bm.free()
        low = r.name.lower()
        if any(h in low for h in HANGING): continue
        veg = any(v in low for v in VEG)
        ign = {o.name for o in kids}
        cx, cy = (bb[0].x + bb[1].x) / 2, (bb[0].y + bb[1].y) / 2
        zs = []
        for dx, dy in ((0, 0), (-.3, -.3), (.3, -.3), (-.3, .3), (.3, .3)):
            x = cx + dx * (bb[1].x - bb[0].x); y = cy + dy * (bb[1].y - bb[0].y)
            hz, hob = _ray_down(x, y, bb[0].z + min(0.35, 0.5 * (bb[1].z - bb[0].z)), ign)
            if hz is not None: zs.append((hz, hob))
        if not zs: rep['floating'].append({'prop': r.name, 'at': [round(v, 2) for v in r.location], 'gap': 'nothing below'}); continue
        top = max(zs, key=lambda z: z[0])
        gap = bb[0].z - top[0]
        if gap > 0.04: rep['floating'].append({'prop': r.name, 'at': [round(v, 2) for v in r.location], 'gap': round(gap, 3), 'over': top[1]})
        elif not veg and gap < -0.05 and top[0] < bb[1].z - 0.02:
            rep['sunk'].append({'prop': r.name, 'at': [round(v, 2) for v in r.location], 'depth': round(-gap, 3), 'into': top[1]})
    print('QA step zfight', flush=True)
    # --- z-fighting between different objects (bbox-overlapping pairs only)
    info = []
    for o in meshes:
        bb = _bbox([o])
        if bb and len(o.data.polygons) < 60000: info.append((o, bb))
    trees = {}
    def tree(o):
        if o.name not in trees:
            bm = _world_bm([o]); bm.faces.ensure_lookup_table(); trees[o.name] = (BVHTree.FromBMesh(bm), bm)
        return trees[o.name]
    zf = {}; zfw = {}
    for i in range(len(info)):
        for j in range(i + 1, len(info)):
            (a, ba), (b, bbb) = info[i], info[j]
            if not _ov(ba, bbb, 0.003): continue
            if a.data == b.data and (a.matrix_world.translation - b.matrix_world.translation).length < 1e-4: zf[(a.name, b.name)] = 'DUPLICATE'; continue
            small, big = (a, b) if len(a.data.polygons) <= len(b.data.polygons) else (b, a)
            ts, bms = tree(small); tb, bmb = tree(big)
            n = 0; step = max(1, len(bms.faces) // 1500); where = None
            for fc in list(bms.faces)[::step]:
                if fc.calc_area() < 1e-4: continue
                c = fc.calc_center_median()
                loc, nrm, idx, dist = tb.find_nearest(c, 0.002)
                if loc is None: continue
                g = bmb.faces[idx]
                if fc.normal.dot(g.normal) <= 0.995: continue
                if abs((c - g.verts[0].co).dot(g.normal)) > 0.002: continue
                inside = all(((g.verts[(k + 1) % len(g.verts)].co - g.verts[k].co).cross(c - g.verts[k].co)).dot(g.normal) > 0.003 * (g.verts[(k + 1) % len(g.verts)].co - g.verts[k].co).length
                             for k in range(len(g.verts)))   # the face centre must lie INSIDE the other face (3 mm in), not on a shared seam
                if inside: n += 1; where = [round(v, 3) for v in c]
            if n >= 2: zf[(a.name, b.name)] = n * step; zfw[(a.name, b.name)] = (where, [round(v, 3) for v in a.location], round(math.degrees(a.rotation_euler.z)), [round(v, 3) for v in b.location], round(math.degrees(b.rotation_euler.z)))
    rep['zfight'] = [{'a': k[0], 'b': k[1], 'faces': v, 'detail': zfw.get(k)} for k, v in sorted(zf.items(), key=lambda kv: -(kv[1] if isinstance(kv[1], int) else 1e9))][:60]
    for t, bm in trees.values(): bm.free()
    print('QA step normals', flush=True)
    # --- normals of generated geometry (Details, boxes, cylinders: everything that is not an imported kit piece)
    for o in meshes:
        if o.name.startswith(('Wall', 'Floor', 'Roof')) or (o.parent and o.parent.name.startswith('P_')): continue
        if len(o.data.polygons) > 400000: continue
        inv, inc = _normals(o)
        if inv or inc: rep['inside_out'].append({'obj': o.name, 'inside_out_parts': inv, 'bad_winding_edges': inc})
    json.dump(rep, open(os.path.join(outdir, name + '_qa.json'), 'w'), indent=1)
    print('QA', name, {k: (len(v) if isinstance(v, list) else v) for k, v in rep.items() if k != 'where'})
    print('QA step images', flush=True)
    # --- review images (Workbench)
    for o in [o for o in bpy.data.objects if o.type == 'CAMERA']: bpy.data.objects.remove(o)
    s = bpy.context.scene; s.render.engine = 'BLENDER_WORKBENCH'; sh = s.display.shading
    sh.light = 'STUDIO'; sh.show_cavity = True; sh.cavity_type = 'BOTH'; sh.show_object_outline = True; sh.show_shadows = True
    s.view_settings.view_transform = 'Standard'; s.view_settings.exposure = 0
    s.render.resolution_percentage = 100; s.render.film_transparent = False
    def shoot(path, w, h):
        s.render.resolution_x, s.render.resolution_y = w, h; s.render.filepath = path; bpy.ops.render.render(write_still=True)
    def cam(p, t, lens=30, ortho=None):
        bpy.ops.object.camera_add(location=p); c = bpy.context.object
        c.rotation_euler = (Vector(t) - Vector(p)).to_track_quat('-Z', 'Y').to_euler(); c.data.lens = lens; c.data.clip_end = 2000
        if ortho: c.data.type = 'ORTHO'; c.data.ortho_scale = ortho
        s.camera = c; return c
    allbb = _bbox([o for o in meshes if max(o.dimensions) < 70 and not o.name.lower().startswith(('fog', 'beam', 'water', 'sea'))])
    sh.color_type = 'RANDOM'
    hidden = [o for o in meshes if o.name.startswith(globals().get('NOSUPPORT', ())) or o.name.lower().startswith(('fog', 'beam', 'water', 'sea')) or max(o.dimensions) > 70]
    for o in hidden: o.hide_render = True
    ctr = (allbb[0] + allbb[1]) / 2; ext = max(allbb[1].x - allbb[0].x, allbb[1].y - allbb[0].y)
    zcut = 2.6 if allbb[1].z - allbb[0].z > 3.0 else allbb[1].z + 30   # cut away roofs/ceilings
    c = cam((ctr.x, ctr.y, zcut), (ctr.x, ctr.y + 0.001, zcut - 10), ortho=min(ext * 1.05, 120)); c.data.clip_start = 0.01
    shoot(os.path.join(outdir, name + '_qa_top.png'), 1600, 1600); bpy.data.objects.remove(c)
    for o in hidden: o.hide_render = False
    sh.color_type = 'MATERIAL'
    for k, (p, t, lens) in cams.items():
        c = cam(p, t, lens); shoot(os.path.join(outdir, '%s_qa_%s.png' % (name, k)), 1280, 720); bpy.data.objects.remove(c)
    # contact sheet of props, each from the audience side (mean camera), framed on its bbox
    ref = sum((Vector(cv[0]) for cv in cams.values()), Vector()) / max(1, len(cams))
    tiles = []; tdir = os.path.join(outdir, name + '_qa_tiles'); os.makedirs(tdir, exist_ok=True)
    for i, r in enumerate(roots[:120]):
        kids = [o for o in r.children_recursive if o.type == 'MESH']; bb = _bbox(kids)
        if not bb: continue
        ctr = (bb[0] + bb[1]) / 2; size = max((bb[1] - bb[0]).length, 0.2)
        d = (ref - ctr); d.z = 0
        d = d.normalized() if d.length > 1e-3 else Vector((0, -1, 0))
        p = ctr + d * size * 1.6 + Vector((0, 0, size * 0.45))
        c = cam(p, ctr, 35); pth = os.path.join(tdir, '%03d.png' % i); shoot(pth, 256, 256); bpy.data.objects.remove(c)
        tiles.append((pth, r.name))
    if tiles:
        cols = 10; rows = (len(tiles) + cols - 1) // cols
        sheet = bpy.data.images.new('sheet', cols * 256, rows * 276); import array
        px = array.array('f', [0.08, 0.08, 0.09, 1.0] * (cols * 256 * rows * 276))
        for n, (pth, nm) in enumerate(tiles):
            im = bpy.data.images.load(pth); src = array.array('f', [0.0] * (256 * 256 * 4)); im.pixels.foreach_get(src)
            cx, cy = (n % cols) * 256, (rows - 1 - n // cols) * 276 + 20
            for yy in range(256):
                a = ((cy + yy) * cols * 256 + cx) * 4; px[a:a + 1024] = src[yy * 1024:(yy + 1) * 1024]
            bpy.data.images.remove(im)
        sheet.pixels.foreach_set(px); sheet.filepath_raw = os.path.join(outdir, name + '_qa_props.png'); sheet.file_format = 'PNG'; sheet.save()
        json.dump([t[1] for t in tiles], open(os.path.join(outdir, name + '_qa_props.json'), 'w'))
    print('QA DONE', name, flush=True)
