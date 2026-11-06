# Sigil & Spark v3 — a tiny Python DSL for episode scripts → Content/PBX/Story/<ep>.json (read by PBXStory.cpp).
# Write an episode as ep1.py with these helpers, then:  python build_story.py ep1 [<out_dir>]   (also runs the branch bot)
import json

def _flat(items):
    out = []
    for x in items:
        if x is None: continue
        if isinstance(x, (list, tuple)): out += _flat(x)
        else: out.append(x)
    return out

def say(who, line, vo=None):
    d = {'say': who, 'line': line}
    if vo: d['vo'] = vo
    return d
def nar(line): return say('narrator', line)
def spark(c=None, g=None, s=None, all=None):
    """your Spark writes in your Codex — one line per Spark (Cindril / Glublet / Sporrow), or the same line for all"""
    if all: return say('spark', all)
    return if_('partner==1', say('spark', c), if_('partner==2', say('spark', g), say('spark', s)))
def note(line): return say('codex', line)
def setf(*flags, v=1): return [{'set': f, 'v': v} for f in flags]
def unset(f): return {'unset': f}
def add(var, v=1): return {'add': var, 'v': v}
def rel(**kw): return {'rel': kw}
def toast(t): return {'toast': t}
def remember(who): return toast(f'{who} will remember that.')
def if_(cond, then, els=None):
    d = {'if': cond, 'then': _flat([then])}
    if els is not None: d['else'] = _flat([els])
    return d
def goto(s): return {'goto': s}
def wait(s): return {'wait': s}
def fade(to, secs=.6): return {'fade': to, 'secs': secs}
def flash(r=1, g=1, b=1): return {'flash': [r, g, b]}
def sfx(n): return {'sfx': n}
def music(n): return {'music': n}
def title(t, sub=''): return {'title': t, 'sub': sub}
def panel(desc): return {'panel': desc}
def objective(t): return {'objective': t}
def blanked(b): return {'blanked': b}
def log(t): return {'log': t}
def end(): return {'end': True}

def opt(text, *do, cond=None, hint=None):
    d = {'text': text, 'do': _flat(do)}
    if cond: d['if'] = cond
    if hint: d['hint'] = hint
    return d
def choice(prompt, t, opts, silent=None, id=None):
    d = {'choice': prompt, 't': t, 'opts': opts}
    if silent is not None: d['silent'] = _flat([silent])
    if id: d['id'] = id
    return d
def spot(id, label, at, *do, cond=None, once=True):
    d = {'id': id, 'label': label, 'at': at, 'do': _flat(do), 'once': once}
    if cond: d['if'] = cond
    return d
def hub(spots, exit, objective=None):
    d = {'hub': {'spots': spots, 'exit': exit}}
    if objective: d['hub']['objective'] = objective
    return d
def pact(prompt, win, lose, steps=3, window=1.8):
    return {'pact': {'prompt': prompt, 'steps': steps, 'window': window, 'win': _flat([win]), 'lose': _flat([lose])}}

class Story:
    def __init__(self, ep, start, title):
        self.d = {'ep': ep, 'start': start, 'title': title, 'cast': {}, 'scenes': {}, 'codex': []}
    def cast(self, id, name, npc=None, color=(1, .82, .2)):
        self.d['cast'][id] = {'name': name, 'npc': npc or id, 'color': list(color)}
    def scene(self, id, title, *nodes):
        self.d['scenes'][id] = {'title': title, 'nodes': _flat(nodes)}
    def codex(self, title, *pages):   # pages: (cond, label) — the first that holds is inked
        self.d['codex'].append({'title': title, 'pages': [list(p) for p in pages]})
    def json(self): return json.dumps(self.d, indent=1, ensure_ascii=False)
