# Sigil & Spark — realistic harbour set for the video-mode vertical slice (owner 2026-11-08 21:07: "download whatever you
# think is necessary"). CC0 Poly Haven: the Smugglers Cove / Project Lighthouse collections (ships, fort, coast, props),
# harbour PBR textures and harbour/dusk HDRIs. Files land in SigilAndSpark_src/polyhaven (local only, never committed).
# Run from the Blender MCP:  exec(open(r"...\SigilAndSpark_src\tools\ph_harbour.py").read()); PHH_START()
# Progress: SigilAndSpark_src/polyhaven/_status_harbour.txt  (DONE at the end; a failed asset is logged and skipped)
import os, json, threading, urllib.request, traceback

ROOT = r"E:\GAME-APP-DEV\POKEMON\SigilAndSpark_src\polyhaven"
MODELS = ['dutch_ship_medium', 'ship_pinnace', 'modular_fort_01', 'coastal_cliff_01', 'coastal_cliff_04', 'coast_line_01',
          'coast_rocks_01', 'coast_land_rocks_02', 'sand_rocks_small_01', 'wooden_lantern_01', 'wooden_bucket_02', 'wooden_stool_01',
          'folding_wooden_stool', 'wicker_basket_01', 'wicker_basket_02', 'wine_barrel_01', 'Barrel_02', 'barrel_03', 'fishermans_hat',
          'life_jacket', 'rubber_boots', 'seadogs_compass', 'vintage_oil_lamp', 'wooden_ladder', 'wooden_picnic_table']
TEX = ['seaworn_sandstone_brick', 'mossy_cobblestone', 'cobblestone_floor_08', 'weathered_plank_siding', 'weathered_peeling_timber',
       'worn_planks', 'roof_slates_02', 'red_slate_roof_tiles_01', 'low_tide_rocks', 'damp_beach_sand', 'wood_floor_deck',
       'old_stone_wall', 'castle_brick_07', 'white_plaster_rough_02', 'worn_mossy_plasterwall']
HDRI = ['small_harbour_sunset', 'small_harbor_01', 'small_harbour_morning', 'petit_port', 'simons_town_harbour', 'belfast_sunset', 'kiara_9_dusk']
UA = {'User-Agent': 'pokebox-dev (personal project)'}

def _get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=120).read()

def _save(u, p):
    if os.path.exists(p) and os.path.getsize(p) > 0: return 0
    os.makedirs(os.path.dirname(p), exist_ok=True)
    b = _get(u); open(p + '.part', 'wb').write(b); os.replace(p + '.part', p); return len(b)

def _job():
    st = os.path.join(ROOT, '_status_harbour.txt'); os.makedirs(ROOT, exist_ok=True)
    log = lambda s: open(st, 'a', encoding='utf-8').write(s + '\n')
    open(st, 'w').write('running\n'); total = 0
    for m in MODELS:
        try:
            f = json.loads(_get('https://api.polyhaven.com/files/' + m))['gltf']['2k']['gltf']
            d = os.path.join(ROOT, 'models', m)
            total += _save(f['url'], os.path.join(d, os.path.basename(f['url'])))
            for rel, v in f.get('include', {}).items(): total += _save(v['url'], os.path.join(d, rel.replace('/', os.sep)))
            log('model %s  %.0f MB' % (m, total / 2**20))
        except Exception: log('FAIL model %s %s' % (m, traceback.format_exc(limit=1).strip().splitlines()[-1]))
    for t in TEX:
        try:
            f = json.loads(_get('https://api.polyhaven.com/files/' + t))
            for k in ('Diffuse', 'nor_gl', 'arm', 'Displacement'):
                if k in f: u = f[k]['2k']['jpg' if k != 'Displacement' else 'png']['url']; total += _save(u, os.path.join(ROOT, 'textures', t, os.path.basename(u)))
            log('tex %s  %.0f MB' % (t, total / 2**20))
        except Exception: log('FAIL tex %s %s' % (t, traceback.format_exc(limit=1).strip().splitlines()[-1]))
    for h in HDRI:
        try:
            u = json.loads(_get('https://api.polyhaven.com/files/' + h))['hdri']['4k']['exr']['url']
            total += _save(u, os.path.join(ROOT, 'hdri', os.path.basename(u)))
            log('hdri %s  %.0f MB' % (h, total / 2**20))
        except Exception: log('FAIL hdri %s %s' % (h, traceback.format_exc(limit=1).strip().splitlines()[-1]))
    log('DONE  %.0f MB' % (total / 2**20))

def PHH_START():
    threading.Thread(target=_job, daemon=True).start(); print('harbour download started')
