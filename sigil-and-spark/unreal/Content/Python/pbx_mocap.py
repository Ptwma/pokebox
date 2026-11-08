# Sigil & Spark — mocap clips (GENEA 2022 / Talking With Hands, Bandai Namco Research Motion Dataset; both CC BY-NC 4.0,
# local only, personal use, credited) → Unreal → MetaHumans. tools/mocap/bvh_to_fbx.py makes the FBX files; here:
#   import_rig(tag, fbx)        first FBX of a source rig (with the proxy mesh) → Skeleton + Skeletal Mesh + its clip
#   import_clips(tag, [fbx..])  more clips onto that Skeleton
#   retarget(tag)               IK Rig (auto chains) + IK Retargeter → IK_MH (the MetaHuman body), batch retarget of every
#                               clip of the rig into /Game/PBX/Mocap/MH as <clip>_MH
import unreal, os
import pbx_retarget as R

AT = unreal.AssetToolsHelpers.get_asset_tools(); EAL = unreal.EditorAssetLibrary
ROOT = '/Game/PBX/Mocap'
MH_MESH = '/Game/PBX/MH/Built/MH_kid/Body/SKM_MH_kid_BodyMesh'

def log(*a): print('[mocap]', *a)

def _task(fbx, dest, skeleton=None, mesh=True):
    t = unreal.AssetImportTask(); t.filename = fbx; t.destination_path = dest; t.automated = True; t.replace_existing = True; t.save = True
    o = unreal.FbxImportUI(); o.import_mesh = mesh; o.import_animations = True; o.import_as_skeletal = True; o.import_materials = False; o.import_textures = False
    o.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH
    if skeleton: o.skeleton = skeleton
    o.anim_sequence_import_data.set_editor_property('import_bone_tracks', True)
    o.anim_sequence_import_data.set_editor_property('animation_length', unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    t.options = o
    AT.import_asset_tasks([t])
    return list(t.imported_object_paths)

def import_rig(tag, fbx):
    paths = _task(fbx, f'{ROOT}/{tag}')
    log(tag, 'imported', paths); return paths

def _mesh(tag):
    for p in EAL.list_assets(f'{ROOT}/{tag}', recursive=False):
        d = EAL.find_asset_data(p)
        if str(d.asset_class_path.asset_name) == 'SkeletalMesh': return unreal.load_asset(p)

def import_clips(tag, fbxs):
    m = _mesh(tag); sk = m.skeleton if hasattr(m, 'skeleton') else m.get_editor_property('skeleton')
    out = []
    for f in fbxs: out += _task(f, f'{ROOT}/{tag}', skeleton=sk, mesh=False)
    log(tag, 'clips', len(out)); return out

GEN_CHAINS = [('Spine', 'b_spine0', 'b_spine3'), ('Neck', 'b_neck0', 'b_neck0'), ('Head', 'b_head', 'b_head'),
              ('LeftClavicle', 'b_l_shoulder', 'b_l_shoulder'), ('RightClavicle', 'b_r_shoulder', 'b_r_shoulder'),
              ('LeftArm', 'b_l_arm', 'b_l_wrist'), ('RightArm', 'b_r_arm', 'b_r_wrist'),
              ('LeftLeg', 'b_l_upleg', 'b_l_foot'), ('RightLeg', 'b_r_upleg', 'b_r_foot')] + \
             [(f'{S}{F.capitalize()}', f'b_{s}_{F}1', f'b_{s}_{F}3') for S, s in (('Left', 'l'), ('Right', 'r')) for F in ('index', 'middle', 'ring', 'pinky', 'thumb')]

def gen_rig(name, mesh_path):
    """GENEA (Talking With Hands) bone names are b_spine0.., so the auto chains find nothing: chains by hand, same names as IK_MH"""
    rig = R._fresh(name, unreal.IKRigDefinition, unreal.IKRigDefinitionFactory())
    c = unreal.IKRigController.get_controller(rig); c.set_skeletal_mesh(unreal.load_asset(mesh_path))
    c.set_retarget_root('b_root')
    for ch, a, b in GEN_CHAINS:
        try: c.add_retarget_chain(ch, a, b, '')
        except Exception as ex: log('chain', ch, ex)
    EAL.save_loaded_asset(rig); return rig

def retarget(tag, only=None):
    R.OUT = f'{ROOT}/Retarget'
    m = _mesh(tag); mesh_path = m.get_path_name().split('.')[0]
    src = gen_rig('IK_' + tag, mesh_path) if tag.startswith('GEN') else R.ik_rig('IK_' + tag, mesh_path)
    tgt = unreal.load_asset('/Game/PBX/Characters/Retarget/IK_MH')
    rtg = R.retargeter(f'RTG_{tag}_to_MH', src, tgt)
    assets = [EAL.find_asset_data(p) for p in EAL.list_assets(f'{ROOT}/{tag}', recursive=False)
              if str(EAL.find_asset_data(p).asset_class_path.asset_name) == 'AnimSequence']
    if only: assets = [a for a in assets if any(o in str(a.asset_name) for o in only)]
    res = unreal.IKRetargetBatchOperation.duplicate_and_retarget(assets, m, unreal.load_asset(MH_MESH), rtg, suffix='_MH',
                                                                  target_path=f'{ROOT}/MH', use_source_path=False, include_referenced_assets=False, overwrite_existing_files=True)
    log(tag, 'retargeted', len(res), [str(r.asset_name) if hasattr(r, 'asset_name') else str(r) for r in res][:6]); return res
