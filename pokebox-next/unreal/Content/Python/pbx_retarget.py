# Pokebox Next — retargets the Universal Animation Library clips (Quaternius rig) onto the Fab "Free Stylized Boy"
# (CC rig with UE-mannequin bone names). IK Rigs with auto-generated retarget chains on both sides, an IK Retargeter
# with fuzzy chain mapping + auto-aligned retarget pose, then a batch duplicate-and-retarget: the new clips keep the
# UAL name with the suffix "_Boy" (C++ PBXAssets::Anim looks them up through UPBXAnimInstance::AnimSuffix).
import unreal

AT = unreal.AssetToolsHelpers.get_asset_tools(); EAL = unreal.EditorAssetLibrary
OUT = '/Game/PBX/Characters/Retarget'
BOY = '/Game/Fab/Free_Stylized_Boy_Character/boy1'
SOURCES = {'UAL1': '/Game/PBX/Characters/Anim/UAL1_Standard/SkeletalMeshes/UAL1_Standard',
           'UAL2': '/Game/PBX/Characters/Anim/UAL2_Standard/SkeletalMeshes/UAL2_Standard'}

def log(*a): print('[rtg]', *a)

def _fresh(name, cls, factory):
    full = f'{OUT}/{name}'
    if EAL.does_asset_exist(full): EAL.delete_asset(full)
    return AT.create_asset(name, OUT, cls, factory)

def ik_rig(name, mesh_path):
    rig = _fresh(name, unreal.IKRigDefinition, unreal.IKRigDefinitionFactory())
    c = unreal.IKRigController.get_controller(rig)
    c.set_skeletal_mesh(unreal.load_asset(mesh_path))
    c.apply_auto_generated_retarget_definition()
    log(name, 'chains', [str(ch.get_editor_property('chain_name')) if hasattr(ch, 'get_editor_property') else str(ch) for ch in c.get_retarget_chains()][:30])
    EAL.save_loaded_asset(rig); return rig

def retargeter(name, src_rig, tgt_rig):
    r = _fresh(name, unreal.IKRetargeter, unreal.IKRetargetFactory())
    c = unreal.IKRetargeterController.get_controller(r)
    try: c.add_default_ops()
    except Exception as ex: log('default ops', ex)
    c.set_ik_rig(unreal.RetargetSourceOrTarget.SOURCE, src_rig)
    c.set_ik_rig(unreal.RetargetSourceOrTarget.TARGET, tgt_rig)
    try: c.assign_ik_rig_to_all_ops(unreal.RetargetSourceOrTarget.SOURCE, src_rig); c.assign_ik_rig_to_all_ops(unreal.RetargetSourceOrTarget.TARGET, tgt_rig)
    except Exception as ex: log('assign rigs', ex)
    c.auto_map_chains(unreal.AutoMapChainType.FUZZY, True)
    for side in (unreal.RetargetSourceOrTarget.TARGET,):
        try: c.auto_align_all_bones(side)
        except Exception as ex: log('auto align', ex)
    EAL.save_loaded_asset(r); return r

def run(only=None):
    tgt = ik_rig('IK_Boy', BOY)
    made = []
    for tag, mesh in SOURCES.items():
        src = ik_rig('IK_' + tag, mesh)
        rtg = retargeter(f'RTG_{tag}_to_Boy', src, tgt)
        folder = mesh.rsplit('/', 1)[0]
        assets = [EAL.find_asset_data(p) for p in EAL.list_assets(folder, recursive=False)
                  if str(EAL.find_asset_data(p).asset_class_path.asset_name) == 'AnimSequence' and not p.split('.')[-1].endswith('_Boy')]
        if only: assets = [a for a in assets if any(str(a.asset_name).endswith(o) for o in only)]
        res = unreal.IKRetargetBatchOperation.duplicate_and_retarget(assets, unreal.load_asset(mesh), unreal.load_asset(BOY), rtg, suffix='_Boy',
                                                                      target_path=OUT + '/Anim', use_source_path=False, include_referenced_assets=False, overwrite_existing_files=True)
        log(tag, 'retargeted', len(res)); made += res
    return made
