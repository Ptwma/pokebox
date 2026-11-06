# Sigil & Spark — FILM MODE prototype (owner 2026-11-06 22:58: "everything is animation like the intro; every choice is
# animated, like Telltale"). One clip per story beat: the beat's set (the exported set FBX), the stylised cast (Quaternius
# characters + UAL clips on 12 fps), three shots per beat (speaker close-up, listener reaction, establishing) composed on an
# inked comic page in the sequencer, with the beat's voice. Live staging stays the fallback for beats without a clip.
#   blender -b --python film_beats.py -- <SRC> <OUTDIR> <beat_id,beat_id,...> [preview]
import bpy, os, sys, json, math, wave, random
argv = sys.argv[sys.argv.index('--') + 1:]
SRC, OUTDIR, BEATS = argv[0], argv[1], argv[2].split(',')
PRJ = os.path.join(os.path.dirname(SRC), 'PokeboxNext')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.argv = [sys.argv[0], '--', SRC, os.path.join(OUTDIR, '_kit.png'), 'film']
exec(open(os.path.join(HERE, '..', 'sets', 'kit.py')).read())
from mathutils import Vector, Matrix
FPS = 12   # stepped like a drawn film: characters AND camera on 12 (the page itself is still)

lines = {l['id']: l for l in json.load(open(os.path.join(HERE, '..', 'story', 'out', 'ep1_lines.json')))}
STAGE = {'s1_harbour': ('Pier', {'hero': ((-420, 340), 'Male_Peasant', 'Hair_SimpleParted', (0.36, 0.30, 0.22)),
                                 'gus': ((-250, 430), 'Male_Ranger', 'Hair_Beard', (0.42, 0.40, 0.38))},
                        (0.32, 0.20, 0.24), (1.0, 0.58, 0.36))}

# ------------------------------------------------------------------ the set: the same FBX the game uses + its lights
scene_id = BEATS[0].rsplit('_', 1)[0]
SETNAME, CAST, WORLD_RGB, SUN_RGB = STAGE[scene_id]
fbx = os.path.join(SRC, 'sets', SETNAME.lower(), f'SM_Set_{SETNAME}.fbx')
bpy.ops.import_scene.fbx(filepath=fbx)
info = json.load(open(os.path.splitext(fbx)[0] + '.json'))
for L in info['lights']:
    if L.get('type') == 'SPOT': continue
    point((L['pos'][0] / 100, -L['pos'][1] / 100, L['pos'][2] / 100), L['energy'], tuple(L['color'][:3]), 0.2)
sea = box('Sea', (400, 400, 0.05), (0, -150, -0.45), mat('SeaFilm', (0.05, 0.10, 0.13), 0.15))
bpy.ops.object.light_add(type='SUN', location=(0, 0, 10)); sun = bpy.context.object
sun.data.energy = 2.2; sun.data.color = SUN_RGB; sun.rotation_euler = (math.radians(78), 0, math.radians(-110))

# ------------------------------------------------------------------ the cast (Quaternius bodies + outfit + hair, tinted)
CHB = os.path.join(SRC, 'characters', 'quaternius', 'Universal Base Characters[Standard]')
OUTF = os.path.join(SRC, 'characters', 'quaternius', 'Modular Character Outfits - Fantasy[Standard]', 'Exports', 'glTF (Godot-Unreal)', 'Outfits')
def actor(name, outfit, hair, loc, face_to, tint):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(CHB, 'Base Characters', 'Godot - UE', 'Superhero_Male_FullBody.gltf'))
    new = [o for o in bpy.data.objects if o not in before]
    arm = next(o for o in new if o.type == 'ARMATURE')
    for o in new:
        if o.type == 'MESH' and o.name.startswith('Icosphere'): bpy.data.objects.remove(o)
    import bmesh   # the body under the outfit is deleted where clothes cover it (else skin pokes through)
    COVER = ('spine', 'pelvis', 'thigh', 'calf', 'foot', 'ball', 'upperarm', 'clavicle')
    for o in [o for o in bpy.data.objects if o not in before]:
        if o.type == 'MESH' and 'superhero' in o.name.lower():
            me = o.data; gi = {g.index: g.name for g in o.vertex_groups}
            bm = bmesh.new(); bm.from_mesh(me); dl = bm.verts.layers.deform.active; kill = []
            for v in bm.verts:
                if dl is None or not v[dl]: continue
                g = max(v[dl].items(), key=lambda kv: kv[1])[0]
                if any(gi.get(g, '').lower().startswith(c) for c in COVER): kill.append(v)
            bmesh.ops.delete(bm, geom=kill, context='VERTS'); bm.to_mesh(me); bm.free()
    b2 = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(OUTF, outfit + '.gltf'))
    for o in [o for o in bpy.data.objects if o not in b2]:
        if o.type == 'MESH' and o.name.startswith('Icosphere'): bpy.data.objects.remove(o); continue
        if o.type == 'MESH':
            o.parent = arm
            for md in o.modifiers:
                if md.type == 'ARMATURE': md.object = arm
            for i, m in enumerate(o.data.materials):
                if m: mm = m.copy(); mm['tint'] = tint; o.data.materials[i] = mm
        elif o is not arm: bpy.data.objects.remove(o)
    hb = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(CHB, 'Hairstyles', 'Rigged to Head Bone', 'glTF (Godot -Unreal)', hair + '.gltf'))
    for o in [o for o in bpy.data.objects if o not in hb]:
        if o.type == 'MESH':
            o.parent = arm
            for md in o.modifiers:
                if md.type == 'ARMATURE': md.object = arm
            for i, m in enumerate(o.data.materials):
                if m: mm = m.copy(); mm['tint'] = (0.14, 0.12, 0.12); o.data.materials[i] = mm
        elif o is not arm: bpy.data.objects.remove(o)
    p = Vector((loc[0] / 100, -loc[1] / 100, 0.02)); d = Vector(face_to) - p
    arm.location = p; arm.rotation_mode = 'XYZ'; arm.rotation_euler = (0, 0, math.atan2(d.y, d.x) + math.pi / 2)
    arm.scale = (0.9, 0.9, 0.9); arm.name = 'ACT_' + name
    return arm

# staging: the game's spots are for capsules that physics pushes out of crates; here nobody may stand inside a stall, so
# each actor goes to the nearest free spot (a 0.45 m ring of rays at knee, hip and chest height hits nothing) and the
# pair stands 1.4 m apart facing each other
def free(p):
    dg = bpy.context.evaluated_depsgraph_get()
    def ok(q):
        for z in (0.35, 0.95, 1.5):
            for k in range(10):
                a = k * math.tau / 10; d = Vector((math.cos(a), math.sin(a), 0))
                if sc.ray_cast(dg, Vector((q.x, q.y, z)), d, distance=0.45)[0]: return False
        hit, loc = sc.ray_cast(dg, Vector((q.x, q.y, 2.5)), Vector((0, 0, -1)), distance=3.2)[:2]
        return hit and abs(loc.z) < 0.3
    for r in [0.0] + [0.3 * i for i in range(1, 20)]:
        for k in range(1 if r == 0 else 16):
            a = k * math.tau / 16; q = Vector((p.x + r * math.cos(a), p.y + r * math.sin(a), 0))
            if ok(q): return q
    print('NO FREE SPOT near', p); return p
bpy.context.view_layer.update()
names = list(CAST.keys())
pos = {}
pos[names[0]] = free(Vector((CAST[names[0]][0][0] / 100, -CAST[names[0]][0][1] / 100, 0)))
want = Vector((CAST[names[1]][0][0] / 100, -CAST[names[1]][0][1] / 100, 0)) - pos[names[0]]; want.z = 0
want = want.normalized() if want.length > 0.01 else Vector((1, 0, 0))
for k in range(16):   # the partner: 1.4 m away, turning around the first actor until the spot is free
    a = math.radians(25 * ((k + 1) // 2) * (1 if k % 2 else -1)); d = Vector((want.x * math.cos(a) - want.y * math.sin(a), want.x * math.sin(a) + want.y * math.cos(a), 0))
    q = pos[names[0]] + d * 1.4; f = free(q)
    if (f - q).length < 0.05: pos[names[1]] = f; break
else: pos[names[1]] = free(pos[names[0]] + want * 1.4)
print('STAGING', {k: tuple(round(c, 2) for c in v) for k, v in pos.items()})
ACT = {}
for k, (loc, outfit, hair, tint) in CAST.items():
    other = next(o for o in CAST if o != k)
    ACT[k] = actor(k, outfit, hair, (pos[k].x * 100, -pos[k].y * 100), pos[other], tint)

# ------------------------------------------------------------------ UAL clips (same rig as the Quaternius bodies)
b3 = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=os.path.join(SRC, 'kits', 'q_anim1', 'Universal Animation Library[Standard]', 'Unreal-Godot', 'UAL1_Standard.glb'))
for a in bpy.data.actions: a.use_fake_user = True
for o in [o for o in bpy.data.objects if o not in b3]: bpy.data.objects.remove(o)
def action(key):
    for a in bpy.data.actions:   # exact name first ('Idle_Loop' must not pick 'Crouch_Idle_Loop')
        if a.name.split('|')[-1] == key or a.name == key: return a
    for a in bpy.data.actions:
        if a.name.endswith('|' + key) or a.name.endswith('_' + key) and 'Crouch' not in a.name: return a
    print('NO ACTION', key, [a.name for a in bpy.data.actions][:40]); return None
def play(arm, key, start, frames):
    act = action(key)
    if not act: return
    ad = arm.animation_data_create(); ad.action = None
    for t in list(ad.nla_tracks): ad.nla_tracks.remove(t)
    tr = ad.nla_tracks.new(); st = tr.strips.new(key, int(start), act)
    if hasattr(st, 'action_slot') and getattr(act, 'slots', None) and len(act.slots): st.action_slot = act.slots[0]
    ln = max(1.0, act.frame_range[1] - act.frame_range[0]); st.repeat = max(1.0, frames / ln + 1)

# ------------------------------------------------------------------ the ink: inverted-hull outlines (fast in EEVEE, no Freestyle)
ink = bpy.data.materials.new('InkHull'); ink.use_nodes = True; ink.use_backface_culling = True
nt = ink.node_tree; em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (0.03, 0.02, 0.025, 1); em.inputs['Strength'].default_value = 1
nt.links.new(em.outputs[0], nt.nodes['Material Output'].inputs['Surface']); ink['toon'] = 1
done = set()
for o in bpy.data.objects:
    if o.type != 'MESH' or o.name in ('Sea',) or o.data.name in done: continue
    done.add(o.data.name)
    if ink.name not in [m.name for m in o.data.materials if m]: o.data.materials.append(ink)
    is_char = o.parent is not None and o.parent.name.startswith('ACT_')
    md = o.modifiers.new('Ink', 'SOLIDIFY'); md.thickness = -(0.011 if is_char else 0.022); md.use_flip_normals = True
    md.material_offset = len(o.data.materials) - 1; md.use_rim = False
for o in bpy.data.objects:   # instances that share a mesh still need the modifier
    if o.type == 'MESH' and 'Ink' not in o.modifiers and o.name != 'Sea':
        md = o.modifiers.new('Ink', 'SOLIDIFY'); md.thickness = -0.022; md.use_flip_normals = True; md.material_offset = len(o.data.materials) - 1; md.use_rim = False
for m in bpy.data.materials: toonify(m)

# ------------------------------------------------------------------ render setup
sc.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE'
sc.view_settings.view_transform = 'Standard'; sc.view_settings.exposure = -0.3
w = bpy.data.worlds.new('W'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs['Color'].default_value = (*WORLD_RGB, 1)
sc.render.fps = FPS; sc.render.image_settings.file_format = 'PNG'
cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); sc.collection.objects.link(cam); sc.camera = cam
def head(k):
    bpy.context.view_layer.update(); a = ACT[k]
    pb = a.pose.bones.get('Head') or a.pose.bones.get('head')
    return a.matrix_world @ pb.head if pb else a.location + Vector((0, 0, 1.45))
def look(c, p, t):
    c.location = p; c.rotation_euler = (Vector(t) - Vector(p)).to_track_quat('-Z', 'Y').to_euler()
def voice_secs(bid, who):
    for suf in ('', '_m'):
        f = os.path.join(PRJ, 'Content', 'PBX', 'StoryAudio', 'vo', bid + suf + '.wav')
        if os.path.exists(f):
            with wave.open(f) as wv: return wv.getnframes() / float(wv.getframerate()), f
    return 1.2 + len(lines[bid]['text']) * 0.055, None

SHOTS = {'A': (1180, 960), 'B': (580, 470), 'C': (580, 390)}
plan = []
for bid in BEATS:
    L = lines[bid]; who = L['who'] if L['who'] in ACT else 'narrator'
    secs, wav = voice_secs(bid, who); n = int(math.ceil((secs + 0.5) * FPS))
    spk = who if who in ACT else next(iter(ACT)); lis = next(k for k in ACT if k != spk)
    plan.append((bid, spk, lis, n, wav, L['text']))
frame0 = 1
for bid, spk, lis, n, wav, text in plan:
    play(ACT[spk], 'Idle_Talking_Loop', frame0, n); play(ACT[lis], 'Idle_Loop', frame0, n)
    sc.frame_set(frame0); hs, hl = head(spk), head(lis)
    to = (hl - hs); to.z = 0; to.normalize(); side = Vector((-to.y, to.x, 0))
    # keep every lens clear: try mirrored / closer / higher variants until nothing but characters stands between lens and face
    def clear(p, t):
        dg = bpy.context.evaluated_depsgraph_get(); d = Vector(t) - Vector(p); dist = d.length; d.normalize()
        hit, loc, nrm, idx, obj, mtx = sc.ray_cast(dg, Vector(p), d, distance=dist - 0.15)
        if not hit: return True
        o = obj
        while o is not None and not o.name.startswith('ACT_'): o = o.parent
        return o is not None
    def pick(fn):
        for sx, k, up in ((1, 1.0, 0), (-1, 1.0, 0), (1, 0.75, 0.15), (-1, 0.75, 0.15), (1, 0.55, 0.3), (-1, 0.55, 0.3)):
            def g(t, fn=fn, sx=sx, k=k, up=up):
                p, tg, lens = fn(t, sx, k); return p + Vector((0, 0, up)), tg, lens
            if clear(*g(0.0)[:2]) and clear(*g(1.0)[:2]): return g
        return lambda t: fn(t, 1, 0.5)
    shots = {
        'A': pick(lambda t, sx, k: (hs + to * (1.15 - 0.18 * t) * k + side * 0.32 * sx + Vector((0, 0, 0.04)), hs - Vector((0, 0, 0.06)), 50)),
        'B': pick(lambda t, sx, k: (hl - to * 1.3 * k + side * 0.25 * sx, hl - Vector((0, 0, 0.1)), 45)),
        'C': pick(lambda t, sx, k: ((hs + hl) / 2 + side * (5.5 + 0.3 * t) * sx * k + Vector((0, 0, 0.9)), (hs + hl) / 2 - Vector((0, 0, 0.4)), 28)),
    }
    for sh, f in shots.items():
        sc.render.resolution_x, sc.render.resolution_y = SHOTS[sh]; sc.render.resolution_percentage = 100
        d = os.path.join(OUTDIR, bid, sh); os.makedirs(d, exist_ok=True)
        for i in range(n):
            sc.frame_set(frame0 + i); p, t, lens = f(i / max(1, n - 1)); look(cam, p, t); cam.data.lens = lens
            sc.render.filepath = os.path.join(d, f'{i:04d}.png'); bpy.ops.render.render(write_still=True)
        print('SHOT', bid, sh, n, flush=True)
    frame0 += n + 10
json.dump([{'id': b, 'spk': s, 'lis': l, 'frames': n, 'wav': w, 'text': t} for b, s, l, n, w, t in plan], open(os.path.join(OUTDIR, 'plan.json'), 'w'), indent=1)
print('FILM 3D DONE', flush=True)
