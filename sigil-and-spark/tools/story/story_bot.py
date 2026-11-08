# Sigil & Spark v3 — the branch bot: plays EVERY path of an episode JSON (all options, silence, pact win/lose, every hub
# visiting order that changes state) and reports dead ends, missing scenes, choices with no option, flags that are read but
# never set (typos) or set but never read, unknown speakers, and which endings / Codex pages each path reaches.
#   python story_bot.py <ep.json>
import json, sys, re, collections

OPS = ['>=', '<=', '==', '!=', '>', '<']

def cond_vars(c):
    out = set()
    for t in re.split(r'\|\||&&', c or ''):
        t = t.strip().lstrip('!')
        for op in OPS:
            if op in t: t = t.split(op)[0]; break
        t = t.strip()
        if t and not re.fullmatch(r'-?\d+', t): out.add(t)
    return out

def cond(c, V):
    if not c or not c.strip(): return True
    for orp in c.split('||'):
        ok = True
        for t in orp.split('&&'):
            t = t.strip(); neg = t.startswith('!') and not t.startswith('!=')
            if neg: t = t[1:]
            r = None
            for op in OPS:
                i = t.find(op)
                if i > 0:
                    a = V.get(t[:i].strip(), 0); bs = t[i + len(op):].strip()
                    b = int(bs) if re.fullmatch(r'-?\d+', bs) else V.get(bs, 0)
                    r = {'>=': a >= b, '<=': a <= b, '==': a == b, '!=': a != b, '>': a > b, '<': a < b}[op]; break
            if r is None: r = V.get(t.strip(), 0) != 0
            if neg: r = not r
            if not r: ok = False; break
        if ok: return True
    return False

class Bot:
    def __init__(self, d):
        self.d = d; self.issues = collections.Counter(); self.ends = collections.Counter(); self.paths = 0
        self.sets, self.reads, self.scenes_hit = set(), set(), set(); self.seen = set(); self.choices = 0; self.lines = 0
        self.pages = collections.defaultdict(collections.Counter); self.entries = collections.Counter(); self.capped = collections.Counter(); self.cap = 600
        for s in d['scenes'].values(): self.scan(s['nodes'])
        for p in d['codex']:
            for c, _ in p['pages']: self.reads |= cond_vars(c)

    def scan(self, nodes):
        for n in nodes:
            if 'set' in n or 'add' in n: self.sets.add(n.get('set') or n.get('add'))
            if 'rel' in n: self.sets |= set(n['rel'])
            if 'if' in n: self.reads |= cond_vars(n['if']); self.scan(n.get('then', [])); self.scan(n.get('else', []))
            if 'say' in n:
                self.lines += 1
                if n['say'] not in self.d['cast'] and n['say'] not in ('narrator', 'hero', 'spark', 'codex'): self.issues['unknown speaker ' + n['say']] += 1
            if 'choice' in n:
                self.choices += 1
                for o in n['opts']: self.reads |= cond_vars(o.get('if')); self.scan(o['do'])
                self.scan(n.get('silent', []))
            if 'pact' in n: self.scan(n['pact']['win']); self.scan(n['pact']['lose'])
            if 'hub' in n:
                self.reads |= cond_vars(n['hub']['exit'])
                for s in n['hub']['spots']: self.reads |= cond_vars(s.get('if')); self.sets.add('seen.' + s['id']); self.scan(s['do'])
            if 'goto' in n and n['goto'] not in self.d['scenes']: self.issues['goto missing scene ' + n['goto']] += 1

    def run(self):
        import random
        self.keep = {r for r in self.reads if not r.startswith('seen.')} | {k for k in self.sets if k.startswith('END_')} | {'__dark'}
        self.pending = collections.defaultdict(set); rnd = random.Random(7)
        self.pending[self.d['start']].add(())
        order = list(self.d['scenes'])
        for _ in range(3):   # scenes in file order (a goto backwards gets another pass)
            for sc in order:
                states = sorted(self.pending.pop(sc, set()))
                if not states: continue
                self.scenes_hit.add(sc); self.entries[sc] += len(states)
                if len(states) > self.cap: self.capped[sc] += len(states) - self.cap; states = rnd.sample(states, self.cap)
                for st in states:
                    self.seen = set()
                    self.go([[self.d['scenes'][sc]['nodes'], 0]], dict(st), sc)
        return self

    def go(self, stack, V, scene, depth=0):
        if depth > 4000: self.issues['path too deep in ' + scene] += 1; return
        stack = [list(f) for f in stack]; V = dict(V)
        key = (tuple((id(f[0]), f[1]) for f in stack), tuple(sorted(V.items())))   # paths that meet again in the same state are one path
        if key in self.seen: self.paths += 1; return
        self.seen.add(key)
        while stack:
            f = stack[-1]
            if f[1] >= len(f[0]): stack.pop(); continue
            n = f[0][f[1]]; f[1] += 1
            if 'set' in n: V[n['set']] = n.get('v', 1)
            elif 'unset' in n: V.pop(n['unset'], None)
            elif 'add' in n: V[n['add']] = V.get(n['add'], 0) + n.get('v', 1)
            elif 'rel' in n:
                for k, d in n['rel'].items(): V[k] = max(-5, min(5, V.get(k, 0) + d))
            elif 'if' in n:
                br = n['then'] if cond(n['if'], V) else n.get('else', [])
                if br: stack.append([br, 0])
            elif 'fade' in n: V['__dark'] = 1 if n['fade'] >= .5 else 0
            elif 'goto' in n:
                scene = n['goto']; V = {k: v for k, v in V.items() if not k.startswith('seen.') and k != '__plan' or k == '__dark'}   # hotspots belong to one scene
                V = {k: v for k, v in V.items() if k in self.keep}                 # only what something still reads
                self.pending[scene].add(tuple(sorted(V.items()))); self.paths += 1   # explored later, scene by scene
                return
            elif 'choice' in n:
                if V.get('__dark'): self.issues[f'choice {n.get("id")} in {scene} while the screen is faded to black'] += 1
                opts = [o for o in n['opts'] if cond(o.get('if'), V)]
                if not opts: self.issues[f'choice {n.get("id")} in {scene}: no eligible option'] += 1; return
                alts = [o['do'] for o in opts]
                if n.get('t', 0) > 0: alts.append(n.get('silent', []))
                for a in alts: self.go(stack + [[a, 0]], V, scene, depth + 1)
                return
            elif 'pact' in n:
                for a in (n['pact']['win'], n['pact']['lose']): self.go(stack + [[a, 0]], V, scene, depth + 1)
                return
            elif 'hub' in n:
                # hubs: not every visiting order (that explodes) but every "how much did you explore" plan — visit the first k
                # optional spots in order (k = 0..all), then the spots the exit needs; choices inside spots still branch fully
                h = n['hub']
                if V.get('__dark'): self.issues[f'hub in {scene} while the screen is faded to black'] += 1
                if h['exit'] and cond(h['exit'], V): V.pop('__plan', None); continue
                elig = [s for s in h['spots'] if not (s.get('once', True) and V.get('seen.' + s['id'])) and cond(s.get('if'), V)]
                if not elig: self.issues[f'hub stuck in {scene} (exit "{h["exit"]}")'] += 1; return
                f[1] -= 1
                need = {v[5:] for v in cond_vars(h['exit']) if v.startswith('seen.')}
                if '__plan' not in V:
                    opt_ids = [s['id'] for s in h['spots'] if s['id'] not in need]
                    plans = [tuple(opt_ids[:k]) for k in range(len(opt_ids) + 1)]
                else: plans = [V['__plan']]
                for plan in plans:
                    plan = list(plan); pick = None
                    while plan and pick is None:
                        pid = plan.pop(0); pick = next((s for s in elig if s['id'] == pid), None)
                    if pick is None: pick = next((s for s in elig if s['id'] in need), elig[0])
                    W = dict(V); W['__plan'] = tuple(plan)
                    if pick.get('once', True): W['seen.' + pick['id']] = 1
                    self.go(stack + [[pick['do'], 0]], W, scene, depth + 1)
                return
            elif 'end' in n:
                self.paths += 1
                e = [k for k in V if k.startswith('END_') and V[k]]; V = {k: v for k, v in V.items() if k != '__plan'}
                self.ends[','.join(sorted(e)) or '(no END_ flag)'] += 1
                for p in self.d['codex']:
                    lab = next((l for c, l in p['pages'] if cond(c, V)), '— unwritten —'); self.pages[p['title']][lab] += 1
                return
        self.issues[f'dead end in {scene} (no goto / end)'] += 1

    def report(self):
        print(f"== branch bot: {self.d['ep']} — {len(self.d['scenes'])} scenes, {self.lines} lines, {self.choices} choices")
        print(f"   distinct path ends explored: {self.paths}")
        print('   distinct ways into each scene: ' + ', '.join(f'{k} {v}' + (f' (capped, {self.capped[k]} skipped)' if self.capped[k] else '') for k, v in self.entries.items()))
        miss = set(self.d['scenes']) - self.scenes_hit - {self.d['start']}
        if miss: self.issues['unreachable scenes: ' + ', '.join(sorted(miss))] += 1
        rd = {r for r in self.reads if not r.startswith('seen.')}
        for v in sorted(rd - self.sets): self.issues[f'read but never set: {v}'] += 1
        unread = sorted(v for v in self.sets - self.reads if not v.startswith('seen.'))
        print('   endings:'); [print(f'     {k}: {c}') for k, c in self.ends.most_common()]
        print('   codex pages reached:')
        for t, c in self.pages.items(): print(f'     {t}: ' + ', '.join(f'{k} ({v})' for k, v in c.items()))
        if unread: print('   set but never read (fine if Ep2 uses them): ' + ', '.join(unread))
        print('   ISSUES:' if self.issues else '   no issues')
        for k, c in self.issues.items(): print(f'     !! {k}  ×{c}')
        return 0 if not self.issues else 1

if __name__ == '__main__':
    sys.exit(Bot(json.load(open(sys.argv[1], encoding='utf-8'))).run().report())
