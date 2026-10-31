# Pokebox Next — original creatures for the Echoes (user decision 2026-10-31: "3D creatures instead of Pokémon,
# Palworld-like, no copyright problems" → Quaternius "Ultimate Monsters", CC0, 49 rigged + animated monsters).
# The card art stays on the CARD (UI); in the world and in battle every card's Echo takes the shape of an ORIGINAL
# creature of the card's type (deterministic per card, the bigger/evolved form for strong cards).
# Source files stay local: PokeboxNext_src/creatures/ultimate_monsters/<Big|Blob|Flying>/*.gltf (never in the repo).
#   import pbx_creatures as C; C.import_all(); C.manifest()
import unreal, os, json

SRC = r"E:\GAME-APP-DEV\POKEMON\PokeboxNext_src\creatures\ultimate_monsters"
DEST = '/Game/PBX/Creatures'
EAL = unreal.EditorAssetLibrary; AT = unreal.AssetToolsHelpers.get_asset_tools()
def log(*a): print('[cre]', *a)

# card type -> (small forms, big / evolved forms). Humanoid figures (Ninja, Orc, Wizard, Tribal) are left out:
# Echoes are creatures. Flying/Demon only ships an idle clip -> out.
TYPES = {
    'Fire':      (['Flying/Dragon', 'Big/Dino'], ['Flying/Dragon_Evolved', 'Big/Demon']),
    'Water':     (['Flying/Glub', 'Blob/Fish', 'Big/Frog'], ['Flying/Glub_Evolved', 'Flying/Squidle', 'Big/Fish']),
    'Grass':     (['Blob/Mushnub', 'Blob/Cactoro', 'Blob/GreenBlob'], ['Blob/Mushnub_Evolved', 'Big/Cactoro', 'Big/MushroomKing']),
    'Lightning': (['Flying/Armabee', 'Blob/Chicken'], ['Flying/Armabee_Evolved', 'Big/Birb']),
    'Psychic':   (['Flying/Ghost', 'Blob/Alien'], ['Flying/Ghost_Skull', 'Flying/Hywirl', 'Big/Alien']),
    'Fighting':  (['Blob/Yeti'], ['Big/Yeti', 'Big/Monkroose']),
    'Darkness':  (['Flying/Pigeon'], ['Big/BlueDemon', 'Big/Demon']),
    'Metal':     (['Flying/Goleling', 'Blob/GreenSpikyBlob'], ['Flying/Goleling_Evolved']),
    'Dragon':    (['Flying/Dragon'], ['Flying/Dragon_Evolved']),
    'Colorless': (['Blob/Cat', 'Blob/Dog', 'Blob/Pigeon', 'Blob/Birb', 'Blob/PinkBlob', 'Flying/Alpaking'], ['Big/Bunny', 'Flying/Alpaking_Evolved']),
    'Fairy':     (['Blob/PinkBlob'], ['Big/Bunny']),
}
# the clip roles the C++ uses -> candidate clip names in the pack (first match wins)
ROLES = {'idle': ['Idle', 'Flying_Idle'], 'walk': ['Walk', 'Flying_Idle'], 'run': ['Run', 'Fast_Flying', 'Walk'],
         'attack': ['Bite_Front', 'Headbutt', 'Punch'], 'hit': ['HitReact', 'HitRecieve'], 'death': ['Death'],
         'happy': ['Yes', 'Dance', 'Jump']}

def keys():
    out = []
    for small, big in TYPES.values():
        for k in small + big:
            if k not in out: out.append(k)
    return out

def folder(k): g, n = k.split('/'); return f'{DEST}/{g}_{n}'

def import_all(only=None):
    done = 0
    for k in keys():
        if only and k not in only: continue
        g, n = k.split('/'); f = os.path.join(SRC, g, n + '.gltf'); d = folder(k)
        if not os.path.exists(f): log('missing file', f); continue
        if EAL.does_directory_exist(d) and any(str(EAL.find_asset_data(p).asset_class_path.asset_name) == 'SkeletalMesh' for p in EAL.list_assets(d, recursive=True)):
            continue
        t = unreal.AssetImportTask()
        t.set_editor_property('filename', f); t.set_editor_property('destination_path', d)
        t.set_editor_property('automated', True); t.set_editor_property('replace_existing', True); t.set_editor_property('save', True)
        AT.import_asset_tasks([t]); done += 1
        log('imported', k, len(t.get_editor_property('imported_object_paths') or []))
    log('import done', done)

def manifest():
    """Content/PBX/Data/creatures.json: per creature the skeletal mesh, its height (cm) and the clip for each role;
    per type the small / big pools"""
    out = {'creatures': {}, 'types': {t: {'small': s, 'big': b} for t, (s, b) in TYPES.items()}}
    for k in keys():
        d = folder(k)
        if not EAL.does_directory_exist(d): log('not imported', k); continue
        mesh, anims = None, {}
        for p in EAL.list_assets(d, recursive=True):
            ad = EAL.find_asset_data(p); cls = str(ad.asset_class_path.asset_name); nm = str(ad.asset_name)
            if cls == 'SkeletalMesh' and not mesh: mesh = p.split('.')[0]
            elif cls == 'AnimSequence': anims[nm] = p.split('.')[0]
        if not mesh: log('no mesh', k); continue
        stem = mesh.split('/')[-1]          # Interchange names the clips <mesh><clip>, e.g. DragonFlying_Idle
        roles = {}
        for role, cands in ROLES.items():
            for c in cands:
                hit = [v for n, v in anims.items() if n in (stem + c, stem + '_' + c, c, stem + '_Anim_' + c)]
                if hit: roles[role] = hit[0]; break
        sm = unreal.load_asset(mesh); b = sm.get_bounds() if sm else None
        h = round(b.box_extent.z * 2, 1) if b else 100.0
        out['creatures'][k] = {'mesh': mesh, 'height': h, 'fly': k.startswith('Flying/'), 'anims': roles}
        log('creature', k, h, sorted(roles))
    path = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()) + 'PBX/Data/creatures.json'
    open(path, 'w', encoding='utf-8').write(json.dumps(out, indent=1)); log('manifest ->', path, len(out['creatures']))
    return out
