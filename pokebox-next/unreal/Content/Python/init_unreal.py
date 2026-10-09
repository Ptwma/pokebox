# Pokebox Next — editor command queue (runs automatically when the Unreal editor starts: Content/Python/init_unreal.py).
# Lets scripts be run in the open editor without touching the keyboard/mouse: drop a .py file into
# <Project>/Saved/pbx_cmd/ and it is executed on the game thread; everything it prints goes to <name>.out next to it.
# A job may define `def tick(dt) -> bool` (return True when finished) for work that needs several frames (screenshots).
import unreal, os, io, sys, traceback, time

ROOT = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), 'pbx_cmd')
os.makedirs(ROOT, exist_ok=True)
_jobs = []          # [(name, globals, out_path, started)]
_poll = [0.0]

def _write(path, text):
    with open(path, 'a', encoding='utf-8') as f: f.write(text)

def _run_file(path):
    name = os.path.basename(path); out = path[:-3] + '.out'
    work = path + '.running'
    try: os.replace(path, work)
    except OSError: return
    g = {'__name__': 'pbx_job', '__file__': work, 'LOG': lambda *a: _write(out, ' '.join(str(x) for x in a) + '\n')}
    buf = io.StringIO(); old = sys.stdout; sys.stdout = buf
    try:
        exec(compile(open(work, encoding='utf-8').read(), name, 'exec'), g)
        if callable(g.get('tick')): _jobs.append((name, g, out, time.time()))
        else: buf.write('\n[pbx] DONE\n')
    except Exception:
        buf.write('\n[pbx] ERROR\n' + traceback.format_exc())
    finally:
        sys.stdout = old; _write(out, buf.getvalue())
        try: os.remove(work)
        except OSError: pass

def _tick(dt):
    _poll[0] += dt
    for job in list(_jobs):
        name, g, out, t0 = job; buf = io.StringIO(); old = sys.stdout; sys.stdout = buf
        try: done = g['tick'](dt)
        except Exception: buf.write('\n[pbx] ERROR in tick\n' + traceback.format_exc()); done = True
        finally: sys.stdout = old
        if buf.getvalue(): _write(out, buf.getvalue())
        if done or time.time() - t0 > 1800:
            _jobs.remove(job); _write(out, '\n[pbx] DONE\n')
    if _poll[0] < 0.5: return
    _poll[0] = 0.0
    try: names = sorted(n for n in os.listdir(ROOT) if n.endswith('.py'))
    except OSError: return
    for n in names: _run_file(os.path.join(ROOT, n))

unreal.register_slate_post_tick_callback(_tick)
_write(os.path.join(ROOT, 'editor_ready.txt'), time.strftime('%Y-%m-%d %H:%M:%S') + ' editor started, command queue live\n')
unreal.log('[pbx] command queue: ' + ROOT)
