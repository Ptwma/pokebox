# Sigil & Spark — mocap BVH → FBX for Unreal (then pbx_mocap.py retargets it onto the MetaHumans with an IK Retargeter).
#   blender -b --python bvh_to_fbx.py -- <out.fbx> <clip.bvh> [start_s end_s] [--mesh]
# The datasets stay LOCAL (PokeboxNext_src\mocap): GENEA 2022 / Talking With Hands (CC BY-NC 4.0) and the Bandai Namco
# Research Motion Dataset (CC BY-NC 4.0) — personal, non-commercial use, credited in the end titles. Never in the repo.
# --mesh adds a tiny skinned box so Unreal can make a Skeleton + Skeletal Mesh for this source rig (needed once per rig).
import bpy, sys, os, re

argv = sys.argv[sys.argv.index('--') + 1:]
OUT, BVH = argv[0], argv[1]
rest = [a for a in argv[2:] if not a.startswith('--')]
T0, T1 = (float(rest[0]), float(rest[1])) if len(rest) >= 2 else (None, None)
MESH = '--mesh' in argv

bpy.ops.wm.read_factory_settings(use_empty=True)
ft = float(re.search(r'Frame Time:\s*([\d.]+)', open(BVH, encoding='utf-8', errors='replace').read(200000)).group(1))
fps = round(1.0 / ft)
sc = bpy.context.scene; sc.render.fps = fps
# both datasets are in centimetres: Blender works in metres, the FBX writes the unit, Unreal reads cm back
bpy.ops.import_anim.bvh(filepath=BVH, global_scale=0.01, frame_start=1, use_fps_scale=False, update_scene_fps=True,
                        update_scene_duration=True, rotate_mode='NATIVE', axis_forward='-Z', axis_up='Y')
sc.render.fps = fps; sc.render.fps_base = 1.0   # GENEA's 0.0333333 frame time made a 29.99999 fps FBX that Unreal refused
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
arm.name = 'root' if 'root' not in [b.name for b in arm.data.bones] else 'MocapRig'
act = arm.animation_data.action
f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
if T0 is not None:
    f0, f1 = max(f0, 1 + int(T0 * fps)), min(f1, 1 + int(T1 * fps))
sc.frame_start, sc.frame_end = f0, f1
act.name = os.path.splitext(os.path.basename(OUT))[0]
objs = [arm]
if MESH:
    bpy.ops.mesh.primitive_cube_add(size=0.05, location=(0, 0, 1.0)); box = bpy.context.object; box.name = 'MocapProxy'
    root_bone = arm.data.bones[0].name
    vg = box.vertex_groups.new(name=root_bone); vg.add(list(range(len(box.data.vertices))), 1.0, 'REPLACE')
    box.parent = arm; m = box.modifiers.new('Armature', 'ARMATURE'); m.object = arm
    objs.append(box)
bpy.ops.object.select_all(action='DESELECT')
for o in objs: o.select_set(True)
bpy.context.view_layer.objects.active = arm
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.export_scene.fbx(filepath=OUT, use_selection=True, object_types={'ARMATURE', 'MESH'}, apply_unit_scale=True,
                         apply_scale_options='FBX_SCALE_UNITS', add_leaf_bones=False, primary_bone_axis='Y', secondary_bone_axis='X',
                         bake_anim=True, bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False, bake_anim_force_startend_keying=True,
                         bake_anim_step=1.0, bake_anim_simplify_factor=0.0, armature_nodetype='NULL', use_armature_deform_only=False)
bpy.context.view_layer.update(); hz = max((arm.matrix_world @ b.head_local).z for b in arm.data.bones)
print('MOCAP FBX', OUT, 'rest height %.2f m' % hz, 'frames', f0, f1, 'fps', fps, 'bones', len(arm.data.bones), flush=True)
