# python build_story.py ep1 [out_dir]  → <out_dir>/ep1.json (default: ./out) and runs the branch bot on it
import sys, os, importlib, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ep = sys.argv[1]; out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
os.makedirs(out, exist_ok=True)
S = importlib.import_module(ep).S
# voice ids: every spoken line gets <scene>_<nnn>; lines naming the hero get _m/_f takes, lines naming the Spark _p1.._p3
import re, json
lines = []
for sid, sc in S.d['scenes'].items():
    n = [0]
    def walk(x):
        if isinstance(x, dict):
            if 'say' in x and x['say'] not in ('spark', 'codex'):
                n[0] += 1; x['vo'] = f"{sid}_{n[0]:03d}"
                t = x['line']; g = bool(re.search(r'\{(hero|lad|he)\}', t)) or x['say'] == 'hero'; sp = '{spark}' in t
                if g: x['vg'] = True
                if sp: x['vs'] = True
                lines.append({'id': x['vo'], 'who': x['say'], 'text': t, 'g': g, 's': sp})
            for v in x.values(): walk(v)
        elif isinstance(x, list):
            for v in x: walk(v)
    walk(sc['nodes'])
p = os.path.join(out, ep + '.json'); open(p, 'w', encoding='utf-8').write(S.json()); print('wrote', p)
lp = os.path.join(out, ep + '_lines.json'); json.dump(lines, open(lp, 'w', encoding='utf-8'), indent=0, ensure_ascii=False); print('lines', len(lines), '->', lp)
import story_bot; sys.exit(story_bot.Bot(S.d).run().report())
