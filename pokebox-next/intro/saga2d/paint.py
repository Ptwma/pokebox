# Sigil & Spark — 2D illustrated intro pages (anime-cold-open style), painted in code as layered SVG.
# Every page = several transparent layers (sky / far / mid / near / fx) for 2.5D parallax in Unreal, plus a flat preview.
# Rendering: Chromium (Playwright) → PNG with alpha. All art is original and procedural.
import math, random, os, json

W, H = 2560, 1440

def defs(seed=1):
    return f'''
<defs>
  <filter id="water" x="-10%" y="-10%" width="120%" height="120%">
    <feTurbulence type="fractalNoise" baseFrequency="0.012" numOctaves="3" seed="{seed}" result="n"/>
    <feDisplacementMap in="SourceGraphic" in2="n" scale="14" xChannelSelector="R" yChannelSelector="G" result="d"/>
    <feGaussianBlur in="d" stdDeviation="0.6"/>
  </filter>
  <filter id="soft" x="-20%" y="-20%" width="140%" height="140%">
    <feTurbulence type="fractalNoise" baseFrequency="0.02" numOctaves="2" seed="{seed+3}" result="n"/>
    <feDisplacementMap in="SourceGraphic" in2="n" scale="22" xChannelSelector="R" yChannelSelector="G" result="d"/>
    <feGaussianBlur in="d" stdDeviation="3"/>
  </filter>
  <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
    <feGaussianBlur stdDeviation="14" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <filter id="bigglow" x="-100%" y="-100%" width="300%" height="300%">
    <feGaussianBlur stdDeviation="60"/>
  </filter>
  <filter id="ink" x="-5%" y="-5%" width="110%" height="110%">
    <feTurbulence type="fractalNoise" baseFrequency="0.08" numOctaves="2" seed="{seed+7}" result="n"/>
    <feDisplacementMap in="SourceGraphic" in2="n" scale="3.5" xChannelSelector="R" yChannelSelector="G"/>
  </filter>
  <filter id="grain">
    <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="{seed+11}" result="g"/>
    <feColorMatrix in="g" type="matrix" values="0 0 0 0 0.35  0 0 0 0 0.28  0 0 0 0 0.2  0 0 0 0.55 0"/>
  </filter>
  <filter id="stain">
    <feTurbulence type="fractalNoise" baseFrequency="0.0035" numOctaves="4" seed="{seed+13}" result="g"/>
    <feColorMatrix in="g" type="matrix" values="0 0 0 0 0.45  0 0 0 0 0.32  0 0 0 0 0.18  0 0 0 0.6 -0.12"/>
  </filter>
  <radialGradient id="vign" cx="50%" cy="50%" r="75%">
    <stop offset="55%" stop-color="#000" stop-opacity="0"/><stop offset="100%" stop-color="#1a0d06" stop-opacity="0.75"/>
  </radialGradient>
</defs>'''

def svg(body, seed=1, bg=None):
    b = f'<rect width="{W}" height="{H}" fill="{bg}"/>' if bg else ''
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{defs(seed)}{b}{body}</svg>'

def grad(gid, stops, x1=0, y1=0, x2=0, y2=1):
    s = ''.join(f'<stop offset="{o}" stop-color="{c}" stop-opacity="{a}"/>' for o, c, a in stops)
    return f'<linearGradient id="{gid}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">{s}</linearGradient>'

def rgrad(gid, stops, cx=.5, cy=.5, r=.5):
    s = ''.join(f'<stop offset="{o}" stop-color="{c}" stop-opacity="{a}"/>' for o, c, a in stops)
    return f'<radialGradient id="{gid}" cx="{cx}" cy="{cy}" r="{r}">{s}</radialGradient>'

def ridge(rnd, y0, amp, rough=.55, n=9, x0=-100, x1=W + 100):
    """fractal mountain/hill line (midpoint displacement) → list of points"""
    pts = [(x0, y0 + rnd.uniform(-amp, amp) * .3), (x1, y0 + rnd.uniform(-amp, amp) * .3)]
    a = amp
    for _ in range(n):
        new = [pts[0]]
        for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
            new += [((xa + xb) / 2, (ya + yb) / 2 + rnd.uniform(-a, a)), (xb, yb)]
        pts = new; a *= rough
    return pts

def poly(pts, close_to=None):
    d = 'M' + ' L'.join(f'{x:.1f},{y:.1f}' for x, y in pts)
    if close_to is not None: d += f' L{pts[-1][0]:.1f},{close_to} L{pts[0][0]:.1f},{close_to} Z'
    return d

def brush(rnd, x0, y0, x1, y1, w, color, op=1.0, wob=6):
    """a tapered brush stroke as a filled path"""
    n = 10; pts_l, pts_r = [], []
    dx, dy = x1 - x0, y1 - y0; L = math.hypot(dx, dy) or 1; nx, ny = -dy / L, dx / L
    for i in range(n + 1):
        t = i / n; ww = w * math.sin(math.pi * min(1, t * 1.1 + .02)) ** .7
        cx = x0 + dx * t + rnd.uniform(-wob, wob) * .3; cy = y0 + dy * t + rnd.uniform(-wob, wob) * .3
        pts_l.append((cx + nx * ww / 2, cy + ny * ww / 2)); pts_r.append((cx - nx * ww / 2, cy - ny * ww / 2))
    d = 'M' + ' L'.join(f'{x:.1f},{y:.1f}' for x, y in pts_l + pts_r[::-1]) + 'Z'
    return f'<path d="{d}" fill="{color}" opacity="{op}"/>'

def cloud(rnd, cx, cy, s, top, bottom, op=.9):
    gid = f'cg{rnd.randint(0, 1 << 30)}'
    g = grad(gid, [(0, top, 1), (1, bottom, 1)])
    blobs = ''.join(f'<ellipse cx="{cx + rnd.uniform(-1, 1) * s}" cy="{cy + rnd.uniform(-.25, .2) * s}" rx="{rnd.uniform(.3, .65) * s}" ry="{rnd.uniform(.16, .3) * s}" fill="url(#{gid})"/>' for _ in range(9))
    return f'<defs>{g}</defs><g filter="url(#soft)" opacity="{op}">{blobs}</g>'

def house(rnd, x, y, s, wall, roof, lit=False, ink='#2a1a12', night=False):
    w = s * rnd.uniform(.9, 1.3); h = s * rnd.uniform(.7, 1.0); rh = s * rnd.uniform(.45, .7)
    o = f'<g filter="url(#ink)">'
    o += f'<rect x="{x - w / 2:.1f}" y="{y - h:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{wall}" stroke="{ink}" stroke-width="{s * .04:.1f}"/>'
    o += f'<path d="M{x - w / 2 - s * .12:.1f},{y - h:.1f} L{x:.1f},{y - h - rh:.1f} L{x + w / 2 + s * .12:.1f},{y - h:.1f} Z" fill="{roof}" stroke="{ink}" stroke-width="{s * .045:.1f}" stroke-linejoin="round"/>'
    if rnd.random() < .6:
        cx = x + w * rnd.uniform(.1, .3)
        o += f'<rect x="{cx:.1f}" y="{y - h - rh * .8:.1f}" width="{s * .12:.1f}" height="{rh * .5:.1f}" fill="{roof}" stroke="{ink}" stroke-width="{s * .03:.1f}"/>'
    win = '#ffcf6b' if lit else ('#6b88a0' if not night else '#1d2333')
    for k in range(rnd.randint(1, 3)):
        wx = x - w / 2 + w * (k + .5) / 3 - s * .07
        o += f'<rect x="{wx:.1f}" y="{y - h * .7:.1f}" width="{s * .14:.1f}" height="{s * .18:.1f}" fill="{win}" stroke="{ink}" stroke-width="{s * .025:.1f}"/>'
        if lit: o += f'<rect x="{wx - s * .1:.1f}" y="{y - h * .7 - s * .1:.1f}" width="{s * .34:.1f}" height="{s * .38:.1f}" fill="#ffb347" opacity=".35" filter="url(#glow)"/>'
    o += f'<rect x="{x - s * .08:.1f}" y="{y - s * .32:.1f}" width="{s * .16:.1f}" height="{s * .32:.1f}" fill="{ink}" opacity=".75"/>'
    return o + '</g>'

def paper_overlay(op=1.0):
    return (f'<rect width="{W}" height="{H}" filter="url(#stain)" opacity="{.8 * op}"/>'
            f'<rect width="{W}" height="{H}" filter="url(#grain)" opacity="{.5 * op}"/>'
            f'<rect width="{W}" height="{H}" fill="url(#vign)"/>')

def glyph_path(rnd, cx, cy, s):
    """a Script glyph as calligraphic strokes (SVG)"""
    out = ''
    for _ in range(rnd.randint(2, 4)):
        k = rnd.choice(['arc', 'hook', 'stem', 'sweep'])
        if k == 'arc':
            r = rnd.uniform(.2, .45) * s; a0 = rnd.uniform(0, 6.28); a1 = a0 + rnd.uniform(1.8, 3.6)
            x0, y0 = cx + r * math.cos(a0), cy + r * math.sin(a0); x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
            d = f'M{x0:.1f},{y0:.1f} A{r:.1f},{r:.1f} 0 {1 if a1 - a0 > math.pi else 0} 1 {x1:.1f},{y1:.1f}'
        elif k == 'hook':
            x0, y0 = cx + rnd.uniform(-.4, .4) * s, cy - .4 * s
            d = f'M{x0:.1f},{y0:.1f} Q{cx:.1f},{cy:.1f} {cx + rnd.uniform(-.3, .3) * s:.1f},{cy + .35 * s:.1f} q{.12 * s:.1f},{.1 * s:.1f} {.2 * s:.1f},{-.05 * s:.1f}'
        elif k == 'stem':
            x0 = cx + rnd.uniform(-.3, .3) * s
            d = f'M{x0:.1f},{cy - .45 * s:.1f} C{x0 + .1 * s:.1f},{cy - .1 * s:.1f} {x0 - .1 * s:.1f},{cy + .2 * s:.1f} {x0 + .05 * s:.1f},{cy + .45 * s:.1f}'
        else:
            y0 = cy + rnd.uniform(-.3, .3) * s
            d = f'M{cx - .45 * s:.1f},{y0:.1f} C{cx - .1 * s:.1f},{y0 - .3 * s:.1f} {cx + .1 * s:.1f},{y0 + .3 * s:.1f} {cx + .45 * s:.1f},{y0:.1f}'
        out += f'<path d="{d}" fill="none" stroke-linecap="round"/>'
    return out

# ------------------------------------------------------------------ render
def render(pages, outdir):
    """pages: {name: svg_string} → PNG with alpha via headless Chromium"""
    from playwright.sync_api import sync_playwright
    os.makedirs(outdir, exist_ok=True); done = []
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': W, 'height': H})
        for name, s in pages.items():
            pg.set_content(f'<html><body style="margin:0;background:transparent">{s}</body></html>')
            f = os.path.join(outdir, name + '.png'); pg.screenshot(path=f, omit_background=True, full_page=False); done.append(f)
        b.close()
    return done
