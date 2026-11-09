# Sigil & Spark — period clothes on the MetaHuman cast (owner 2026-11-09: "you make the clothes"). Round trip:
#   export_bodies()  → SigilAndSpark_src/clothes/<id>_body.fbx   (each character's body skeletal mesh, LOD0)
#   (Blender: tools/clothes_mh.py makes <id>_clothes.fbx + .json from the body)
#   import_all()     → /Game/PBX/Clothes/<id>/SKM_<id>_Clothes on the body's own skeleton, fabric materials (Poly Haven
#                      scans + tint), and a "Clothes" part in mh_manifest.json (the C++ drives it with the body as leader)
import unreal, os, json

SRC = r"E:\GAME-APP-DEV\POKEMON\SigilAndSpark_src"
OUT = os.path.join(SRC, 'clothes')
G = '/Game/PBX'; DST = G + '/Clothes'; TEX = G + '/Tex/PH'
AT = unreal.AssetToolsHelpers.get_asset_tools(); EAL = unreal.EditorAssetLibrary; MEL = unreal.MaterialEditingLibrary
CAST = ['player_m', 'rho', 'fisher', 'vale', 'aide', 'merchant', 'gardener', 'guard', 'kid']
UVS = {'rough_linen': 6.0, 'hessian_230': 5.0, 'caban': 5.0, 'poly_wool_herringbone': 7.0, 'brown_leather': 3.0, 'fabric_leather_01': 3.0,
       'ribbed_corduroy': 6.0, 'wool_boucle': 5.0, 'velour_velvet': 5.0, 'cotton_jersey': 7.0}
def log(*a): print('[clothes]', *a)

def _manifest_path():
    return unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()) + 'PBX/Data/mh_manifest.json'

def manifest():
    return json.load(open(_manifest_path(), encoding='utf-8'))

def export_bodies(ids=None):
    os.makedirs(OUT, exist_ok=True); man = manifest(); n = 0
    for cid in ids or CAST:
        e = man.get(cid)
        if not e or not e.get('body'): log('no body', cid); continue
        # the MetaHuman body has NO torso / hips under its default garment (hidden faces are removed): the garment mesh
        # ("..._Outfits") is exported too and Blender uses both as the surface to tailor on
        outfit = next((x['mesh'] for x in e.get('parts', []) if x.get('mesh', '').endswith('_Outfits')), None)
        for tag, path in (('body', e['body']), ('outfit', outfit)):
            if not path: continue
            sk = unreal.load_asset(path)
            t = unreal.AssetExportTask()
            t.set_editor_property('object', sk); t.set_editor_property('filename', os.path.join(OUT, f'{cid}_{tag}.fbx'))
            t.set_editor_property('automated', True); t.set_editor_property('prompt', False); t.set_editor_property('replace_identical', True)
            o = unreal.FbxExportOption(); o.set_editor_property('level_of_detail', False); o.set_editor_property('collision', False)
            o.set_editor_property('export_morph_targets', False); t.set_editor_property('options', o)
            ok = unreal.Exporter.run_asset_export_task(t); n += ok; log('export', cid, tag, ok)
    return n

def _import_albedo(fabric):
    """some Poly Haven sets name the colour map _albedo (brown_leather): import it as PH_<fabric>_diff"""
    import glob
    f = sorted(glob.glob(os.path.join(SRC, 'polyhaven', 'textures', fabric, f'{fabric}_albedo_*.jpg')) + glob.glob(os.path.join(SRC, 'polyhaven', 'textures', fabric, f'{fabric}_diff_*.jpg')))
    if not f: return None
    t = unreal.AssetImportTask()
    for k, v in (('filename', f[-1]), ('destination_path', TEX), ('destination_name', f'PH_{fabric}_diff'), ('automated', True), ('replace_existing', True), ('save', True)): t.set_editor_property(k, v)
    AT.import_asset_tasks([t]); log('imported albedo', fabric)
    return unreal.load_asset(f'{TEX}/PH_{fabric}_diff')

def refresh_materials(ids=None):
    """re-make every garment material from the json and assign it to its slot (no mesh import)"""
    for cid in ids or CAST:
        js = os.path.join(OUT, cid + '_clothes.json'); path = f'{DST}/{cid}/SKM_{cid}_Clothes'
        if not os.path.exists(js) or not EAL.does_asset_exist(path): continue
        info = json.load(open(js, encoding='utf-8'))['garments']; sk = unreal.load_asset(path)
        mats = sk.get_editor_property('materials')
        for i, m in enumerate(mats):
            slot = str(m.get_editor_property('material_slot_name'))
            g = next((x for x in info if slot.endswith(x['kind'])), None) or next((x for x in info if x['kind'] in slot), None)
            if g: m.set_editor_property('material_interface', _fabric_mi(cid, g['kind'], g['fabric'], g['tint'])); mats[i] = m
        sk.set_editor_property('materials', mats); EAL.save_asset(path)
        log('materials', cid, [str(x.get_editor_property('material_interface').get_name()) for x in sk.get_editor_property('materials')][:3])

def _fabric_mi(cid, kind, fabric, tint):
    path = f'{DST}/{cid}/MI_{cid}_{kind}'
    mi = unreal.load_asset(path) if EAL.does_asset_exist(path) else AT.create_asset(path.split('/')[-1], f'{DST}/{cid}', unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    parent = unreal.load_asset(G + '/Materials/M_PBX_Surface')
    if not parent.get_editor_property('used_with_skeletal_mesh'):
        # the usage flag must be SAVED on the parent, or the game shows the default grid material on every garment (QA)
        parent.set_editor_property('used_with_skeletal_mesh', True); MEL.recompile_material(parent); EAL.save_asset(G + '/Materials/M_PBX_Surface')
    mi.set_editor_property('parent', parent)
    for k, suf in (('BaseTex', '_diff'), ('NormalTex', '_nor'), ('ArmTex', '_arm')):
        tx = unreal.load_asset(f'{TEX}/PH_{fabric}{suf}')
        if not tx and suf == '_diff': tx = _import_albedo(fabric)
        if tx: MEL.set_material_instance_texture_parameter_value(mi, k, tx)
        else: log('missing texture', fabric + suf)
    MEL.set_material_instance_scalar_parameter_value(mi, 'UVScale', UVS.get(fabric, 5.0))
    MEL.set_material_instance_vector_parameter_value(mi, 'Tint', unreal.LinearColor(*[min(1.0, c * 1.25) for c in tint], 1))
    MEL.update_material_instance(mi); EAL.save_asset(path); return mi

def import_one(cid):
    fbx = os.path.join(OUT, cid + '_clothes.fbx'); js = os.path.join(OUT, cid + '_clothes.json')
    if not os.path.exists(fbx): log('no clothes fbx', cid); return None
    man = manifest(); body = unreal.load_asset(man[cid]['body'])
    skel = body.get_editor_property('skeleton')
    ui = unreal.FbxImportUI()
    ui.set_editor_property('import_mesh', True); ui.set_editor_property('import_as_skeletal', True); ui.set_editor_property('import_materials', False)
    ui.set_editor_property('import_textures', False); ui.set_editor_property('import_animations', False); ui.set_editor_property('skeleton', skel)
    ui.set_editor_property('mesh_type_to_import', unreal.FBXImportType.FBXIT_SKELETAL_MESH)
    sm = ui.get_editor_property('skeletal_mesh_import_data')
    sm.set_editor_property('import_morph_targets', False); sm.set_editor_property('convert_scene', True)
    sm.set_editor_property('import_meshes_in_bone_hierarchy', True); sm.set_editor_property('use_t0_as_ref_pose', False)
    t = unreal.AssetImportTask()
    for k, v in (('filename', fbx), ('destination_path', f'{DST}/{cid}'), ('destination_name', f'SKM_{cid}_Clothes'), ('automated', True), ('replace_existing', True), ('save', True), ('options', ui)):
        t.set_editor_property(k, v)
    AT.import_asset_tasks([t])
    path = f'{DST}/{cid}/SKM_{cid}_Clothes'
    sk = unreal.load_asset(path)
    if not sk: log('import failed', cid); return None
    info = json.load(open(js, encoding='utf-8'))['garments'] if os.path.exists(js) else []
    mats = sk.get_editor_property('materials')
    for i, m in enumerate(mats):
        slot = str(m.get_editor_property('material_slot_name'))
        g = next((x for x in info if slot.endswith(x['kind'])), None) or next((x for x in info if x['kind'] in slot), info[i] if i < len(info) else None)
        if g: m.set_editor_property('material_interface', _fabric_mi(cid, g['kind'], g['fabric'], g['tint'])); mats[i] = m   # the loop variable is a COPY of the struct (QA: every slot stayed WorldGrid)
    sk.set_editor_property('materials', mats); EAL.save_asset(path)
    log('imported', cid, len(mats), 'garments')
    return path

def import_all(ids=None):
    import shutil, time
    shutil.copy(_manifest_path(), _manifest_path() + time.strftime('.bak_%Y%m%d_%H%M'))
    man = manifest(); done = []
    for cid in ids or CAST:
        p = import_one(cid)
        if not p: continue
        # our clothes replace the MetaHuman default garment (it is thicker than our shells and would come through them);
        # the old entry is kept in 'parts_default' so the swap can be undone
        man[cid].setdefault('parts_default', [x for x in man[cid]['parts'] if x.get('name') != 'Clothes'])
        parts = [x for x in man[cid]['parts_default'] if not x.get('mesh', '').endswith('_Outfits')]
        parts.append({'name': 'Clothes', 'mesh': p, 'face': False})
        man[cid]['parts'] = parts; done.append(cid)
    open(_manifest_path(), 'w', encoding='utf-8').write(json.dumps(man, indent=1))
    log('manifest updated', done)
    return done
