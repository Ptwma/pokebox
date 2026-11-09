# one-off fix for clothes FBX exported with the armature object named 'Armature' (Unreal dropped it → root bone missing):
# re-export each with the armature object named 'root'.   blender -b --factory-startup --python clothes_reroot.py -- <dir> id,id,...
import bpy, sys, os
argv = sys.argv[sys.argv.index('--') + 1:]; D = argv[0]
for cid in argv[1].split(','):
    f = os.path.join(D, cid + '_clothes.fbx')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=f, use_anim=False, ignore_leaf_bones=False, automatic_bone_orientation=False)
    arm = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE'); arm.name = 'root'
    for o in bpy.context.scene.objects: o.select_set(o.type in ('ARMATURE', 'MESH'))
    bpy.ops.export_scene.fbx(filepath=f, use_selection=True, object_types={'ARMATURE', 'MESH'}, add_leaf_bones=False, use_armature_deform_only=False,
                             apply_unit_scale=True, apply_scale_options='FBX_SCALE_ALL', bake_anim=False, mesh_smooth_type='FACE', use_mesh_modifiers=True,
                             primary_bone_axis='Y', secondary_bone_axis='X')
    print('REROOT', cid, len(arm.data.bones))
