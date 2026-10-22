# Pokebox Next — fetches the CC0 Poly Haven assets + the real Grindelwald/Eiger elevation tiles used for the realistic
# world pass (2026-10-22, approved by the user). Files land in PokeboxNext_src/polyhaven (local only, never committed).
# Run from the Blender MCP:  exec(open(r"...\PokeboxNext_src\tools\ph_download.py").read()); PH_START()
# Progress: PokeboxNext_src/polyhaven/_status.txt  (DONE / ERROR at the end)
import os, json, threading, urllib.request, traceback, math

ROOT = r"E:\GAME-APP-DEV\POKEMON\PokeboxNext_src\polyhaven"
MODELS = ['rock_moss_set_01', 'rock_moss_set_02', 'boulder_01', 'mountainside', 'namaqualand_cliff_02', 'shrub_01', 'shrub_02',
          'shrub_04', 'grass_medium_01', 'grass_medium_02', 'fern_02', 'dandelion_01', 'celandine_01', 'tree_stump_01', 'stone_fire_pit',
          'Barrel_01', 'planter_box_01', 'painted_wooden_bench', 'outdoor_table_chair_set_01', 'wooden_crate_01', 'Lantern_01',
          'wooden_bucket_01',
          # 2026-10-23 b (approved): harbour, realistic forest, island shore
          'modular_wooden_pier', 'fir_tree_01', 'fir_sapling_medium', 'coast_rocks_05', 'coast_land_rocks_04', 'lifebuoy', 'ocean_buoy',
          'lateral_sea_marker', 'old_tyre', 'wooden_barrels_01', 'wooden_crate_02', 'grass_bermuda_01', 'moss_01', 'street_lamp_01']
TEX = ['aerial_rocks_02', 'aerial_grass_rock', 'rock_face_03', 'snow_02', 'forest_ground_04', 'leafy_grass', 'stony_dirt_path',
       'cobblestone_floor_01', 'plastered_wall_02', 'clay_roof_tiles_02', 'brown_planks_05', 'stacked_stone_wall', 'mossy_rock', 'cliff_side',
       # boats (painted / weathered planks), harbour arms
       'blue_painted_planks', 'distressed_painted_planks', 'wood_peeling_paint_weathered', 'weathered_planks', 'green_rough_planks', 'rubble', 'concrete_moss']
# Grindelwald (46.624 N, 8.034 E) — Eiger/Mönch/Wetterhorn ring. Terrarium tiles, zoom 12 (~38 m/px), 5x5 around the village.
DEM_LAT, DEM_LON, DEM_Z, DEM_R = 46.624, 8.034, 12, 2
UA = {'User-Agent': 'pokebox-dev (personal project)'}

def _get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read()

def _save(u, p):
    if os.path.exists(p) and os.path.getsize(p) > 0: return 0
    os.makedirs(os.path.dirname(p), exist_ok=True)
    b = _get(u); open(p + '.part', 'wb').write(b); os.replace(p + '.part', p); return len(b)

def _tile(lat, lon, z):
    n = 2 ** z; x = int((lon + 180) / 360 * n)
    y = int((1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n)
    return x, y

def _job():
    st = os.path.join(ROOT, '_status.txt'); os.makedirs(ROOT, exist_ok=True)
    log = lambda s: open(st, 'a', encoding='utf-8').write(s + '\n')
    open(st, 'w').write('running\n'); total = 0
    try:
        for m in MODELS:
            f = json.loads(_get('https://api.polyhaven.com/files/' + m))['gltf']['2k']['gltf']
            d = os.path.join(ROOT, 'models', m)
            total += _save(f['url'], os.path.join(d, os.path.basename(f['url'])))
            for rel, v in f.get('include', {}).items(): total += _save(v['url'], os.path.join(d, rel.replace('/', os.sep)))
            log('model %s  %.0f MB' % (m, total / 2**20))
        for t in TEX:
            f = json.loads(_get('https://api.polyhaven.com/files/' + t))
            for k in ('Diffuse', 'nor_gl', 'arm'):
                if k in f: u = f[k]['2k']['jpg']['url']; total += _save(u, os.path.join(ROOT, 'textures', t, os.path.basename(u)))
            log('tex %s  %.0f MB' % (t, total / 2**20))
        cx, cy = _tile(DEM_LAT, DEM_LON, DEM_Z)
        for dy in range(-DEM_R, DEM_R + 1):
            for dx in range(-DEM_R, DEM_R + 1):
                x, y = cx + dx, cy + dy
                total += _save('https://s3.amazonaws.com/elevation-tiles-prod/terrarium/%d/%d/%d.png' % (DEM_Z, x, y),
                               os.path.join(ROOT, 'dem', '%d_%d_%d.png' % (DEM_Z, x, y)))
        json.dump({'z': DEM_Z, 'cx': cx, 'cy': cy, 'r': DEM_R, 'lat': DEM_LAT, 'lon': DEM_LON}, open(os.path.join(ROOT, 'dem', 'dem.json'), 'w'))
        log('dem ok  %.0f MB' % (total / 2**20)); log('DONE')
    except Exception:
        log('ERROR\n' + traceback.format_exc())

def PH_START():
    threading.Thread(target=_job, daemon=True).start(); print('ph download started')
