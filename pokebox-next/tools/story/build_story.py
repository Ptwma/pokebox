# python build_story.py ep1 [out_dir]  → <out_dir>/ep1.json (default: ./out) and runs the branch bot on it
import sys, os, importlib, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ep = sys.argv[1]; out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
os.makedirs(out, exist_ok=True)
S = importlib.import_module(ep).S
p = os.path.join(out, ep + '.json'); open(p, 'w', encoding='utf-8').write(S.json()); print('wrote', p)
import story_bot; sys.exit(story_bot.Bot(S.d).run().report())
