# Sigil & Spark — Poly Haven models made of several parts (ships: hull + masts + sails + rigging; the modular fort) lose
# their part placement when Unreal imports the glTF mesh by mesh. This joins every part into ONE mesh (transforms applied,
# materials kept) and writes <name>_merged.glb next to the original; pbx_harbour imports the merged file when it exists.
#   blender -b --factory-startup --python ph_merge.py -- <polyhaven models dir> name1,name2,...
import bpy, os, sys
argv = sys.argv[sys.argv.index('--') + 1:]
ROOT, NAMES = argv[0], argv[1].split(',')
for n in NAMES:
    d = os.path.join(ROOT, n)
    g = [f for f in os.listdir(d) if f.endswith('.gltf')] if os.path.isdir(d) else []
    if not g: print('MERGE skip (no gltf)', n); continue
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=os.path.join(d, g[0]))
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    print('MERGE', n, 'parts', len(meshes))
    if len(meshes) < 2: continue
    for o in bpy.context.scene.objects: o.select_set(False)
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active; o.name = n
    for x in [x for x in bpy.context.scene.objects if x is not o]: bpy.data.objects.remove(x)
    out = os.path.join(d, n + '_merged.glb')
    bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', use_selection=False, export_apply=True)
    print('MERGE wrote', out, len(o.data.polygons), 'faces', len(o.data.materials), 'materials')
