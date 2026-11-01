from paint import *
from PIL import Image

def layered(name, layers, seed):
    """layers: [(layer_name, svg_body)] → per-layer transparent SVGs + a flat preview with paper"""
    out = {f'{name}_{ln}': svg(body, seed) for ln, body in layers}
    out[f'{name}__preview'] = svg(''.join(b for _, b in layers) + paper_overlay(), seed)
    return out

def p07_harbour(seed=7):
    """a thousand years of peace — Lumen Harbor at golden hour"""
    r = random.Random(seed); hz = 760
    sky = grad('sky', [(0, '#2b1d4a', 1), (.35, '#7a3b6b', 1), (.62, '#e8845a', 1), (.85, '#ffc98a', 1), (1, '#ffe7b8', 1)])
    sun = rgrad('sun', [(0, '#fff6d8', 1), (.25, '#ffd28a', .9), (1, '#ff9a5a', 0)])
    L_sky = f'<defs>{sky}{sun}</defs><rect width="{W}" height="{H}" fill="url(#sky)"/>'
    SX, SY = 1760, 470
    L_sky += f'<circle cx="{SX}" cy="{SY}" r="620" fill="url(#sun)"/><circle cx="{SX}" cy="{SY}" r="78" fill="#fff4d6" filter="url(#glow)"/>'
    for k in range(9):
        cx = r.uniform(-100, W + 100); cy = r.uniform(120, 330); s = r.uniform(180, 420)
        if abs(cx - SX) < 380: cx -= 800
        L_sky += cloud(r, cx, cy, s, '#ffd9b0' if cy > 400 else '#f3a1a1', '#8a4f7a', r.uniform(.55, .9))
    # light rays from the sun
    for k in range(7):
        a = -2.6 + k * .32 + r.uniform(-.05, .05)
        x2, y2 = SX + 2400 * math.cos(a), SY + 2400 * math.sin(a)
        L_sky += f'<path d="M{SX},{SY} L{x2:.0f},{y2:.0f} L{x2 + 260:.0f},{y2 + 120:.0f} Z" fill="#fff0c8" opacity=".07" filter="url(#soft)"/>'
    # far: mountains (atmospheric layers) + the lighthouse island
    L_far = ''
    for i, (y0, amp, c1, c2) in enumerate([(hz - 150, 150, '#c78f96', '#e6ad94'), (hz - 90, 110, '#9a6680', '#c98a84'), (hz - 40, 70, '#6e4c70', '#9a6670')]):
        g = grad(f'mt{i}', [(0, c1, 1), (1, c2, 1)])
        pts = ridge(r, y0, amp, .55, 8)
        L_far += f'<defs>{g}</defs><path d="{poly(pts, hz + 5)}" fill="url(#mt{i})" filter="url(#water)"/>'
        L_far += f'<path d="{poly(pts)}" fill="none" stroke="#3a2338" stroke-width="2.2" opacity=".55" filter="url(#ink)"/>'
    isl = ridge(r, hz - 25, 25, .5, 6, 300, 760)
    L_far += f'<path d="{poly(isl, hz + 4)}" fill="#5a3f5e" filter="url(#water)"/>'
    L_far += ('<g filter="url(#ink)"><path d="M520,{a} L535,{b} L565,{b} L580,{a} Z" fill="#f2e6d2" stroke="#2a1a22" stroke-width="3"/>'
              '<rect x="532" y="{c}" width="36" height="22" fill="#ffcf6b" stroke="#2a1a22" stroke-width="3"/>'
              '<path d="M528,{c} L550,{d} L572,{c} Z" fill="#b8473a" stroke="#2a1a22" stroke-width="3"/></g>'
              '<circle cx="550" cy="{e}" r="40" fill="#ffd27a" opacity=".55" filter="url(#glow)"/>').format(a=hz - 30, b=hz - 190, c=hz - 212, d=hz - 250, e=hz - 200)
    # sea: gradient + sun glitter + wave strokes
    seag = grad('sea', [(0, '#e9a37a', 1), (.25, '#b0707e', 1), (1, '#3d3f6e', 1)])
    L_sea = f'<defs>{seag}</defs><rect y="{hz}" width="{W}" height="{H - hz}" fill="url(#sea)"/>'
    for k in range(420):
        y = hz + 6 + (r.random() ** 1.6) * (H - hz); spread = 80 + (y - hz) * 1.1
        x = SX + r.gauss(0, 1) * spread * .5; w = 10 + (y - hz) * .12 * r.uniform(.5, 1.5)
        L_sea += f'<rect x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{1.5 + (y - hz) * .008:.1f}" fill="#fff1cf" opacity="{r.uniform(.25, .85) * max(.15, 1 - abs(x - SX) / (spread * 1.2)):.2f}"/>'
    for k in range(160):
        y = hz + 20 + r.random() * (H - hz); x = r.uniform(-50, W); w = 40 + (y - hz) * .35
        L_sea += brush(r, x, y, x + w, y + r.uniform(-2, 2), 2 + (y - hz) * .012, '#2b2a55', r.uniform(.2, .5), 2)
    # mid: the harbour town on the hill (rows back to front), breakwater, boats
    L_town = ''
    hill = ridge(r, hz + 140, 45, .5, 7, -100, 1350) + [(1450, hz + 200), (1560, hz + 290), (1640, hz + 420), (1700, H + 10)]
    hg = grad('hill', [(0, '#b5a06e', 1), (.5, '#7d8550', 1), (1, '#4b5a3c', 1)])
    L_town += f'<defs>{hg}</defs><path d="{poly(hill, H + 10)}" fill="url(#hill)" filter="url(#water)"/>'
    L_town += f'<path d="{poly(hill)}" fill="none" stroke="#2a1a12" stroke-width="3" opacity=".6" filter="url(#ink)"/>'
    walls = ['#f3e5c8', '#eed7b4', '#f6eadb', '#e9cfae', '#f1dcc0']; roofs = ['#b8473a', '#3f6f9a', '#5b8a4e', '#a8653a', '#6c5b7b', '#c47a2c']
    for row in range(5):
        y = hz + 170 + row * 85; s = 70 + row * 22
        x = -60 + r.uniform(0, 60)
        while x < 1350 - row * 40:
            L_town += house(r, x, y + r.uniform(-12, 12), s, r.choice(walls), r.choice(roofs), lit=r.random() < .35)
            x += s * r.uniform(1.35, 1.9)
    pier = f'M1560,{hz + 300} Q1800,{hz + 250} 2010,{hz + 290}'
    L_town += f'<path d="{pier}" stroke="#2a1a12" stroke-width="30" fill="none" filter="url(#ink)"/><path d="{pier}" stroke="#cdbb98" stroke-width="22" fill="none" filter="url(#water)"/>'
    L_town += f'<g filter="url(#ink)"><rect x="2000" y="{hz + 215}" width="18" height="80" fill="#f2e6d2" stroke="#2a1a12" stroke-width="3"/><circle cx="2009" cy="{hz + 210}" r="9" fill="#ffcf6b"/></g><circle cx="2009" cy="{hz + 210}" r="30" fill="#ffcf6b" opacity=".5" filter="url(#glow)"/>'
    for k in range(5):
        bx, by = r.uniform(1300, 2300), r.uniform(hz + 90, hz + 260); bs = 30 + (by - hz) * .15
        L_town += (f'<g filter="url(#ink)"><path d="M{bx - bs},{by} Q{bx},{by + bs * .5} {bx + bs},{by} Z" fill="#7a4a2e" stroke="#21150f" stroke-width="3"/>'
                   f'<path d="M{bx},{by - bs * 1.6} L{bx},{by} L{bx + bs * .9},{by - 6} Z" fill="#fff4e0" stroke="#21150f" stroke-width="3"/></g>')
    # near: dark foreground cliff with grass and flowers
    near = ridge(r, H - 170, 70, .55, 7, 1500, W + 100)
    L_near = f'<path d="{poly([(1300, H + 10)] + near, H + 10)}" fill="#2a2234" filter="url(#water)"/>'
    for k in range(260):
        x = r.uniform(1550, W); y = H - 120 - r.uniform(0, 120) + (x - 2000) * -.02
        L_near += brush(r, x, y + 60, x + r.uniform(-25, 25), y - r.uniform(30, 110), r.uniform(3, 7), r.choice(['#3a3048', '#4a3a52', '#56415a']), .95, 3)
    for k in range(40):
        x = r.uniform(1600, W); y = H - r.uniform(60, 240)
        L_near += f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r.uniform(4, 9):.1f}" fill="{r.choice(["#ffb3a7", "#ffe08a", "#f6f0e4"])}" opacity=".9"/>'
    # fx: Sparks gliding over the bay with glowing trails, petals, sun motes
    L_fx = ''
    for k, (col, x, y, s) in enumerate([('#ff9a3c', 1020, 380, 1.0), ('#5fa8ff', 1260, 300, .8), ('#ffd84a', 1450, 430, .7)]):
        L_fx += f'<path d="M{x - 260},{y + 60} Q{x - 120},{y - 40} {x},{y}" stroke="{col}" stroke-width="10" fill="none" opacity=".6" filter="url(#glow)" stroke-linecap="round"/>'
        L_fx += (f'<g transform="translate({x},{y}) scale({s})" filter="url(#ink)"><path d="M-46,0 Q-20,-34 0,-6 Q20,-34 46,0 Q20,-10 0,8 Q-20,-10 -46,0 Z" fill="{col}" stroke="#2a1a12" stroke-width="4"/>'
                 f'<circle cx="0" cy="-2" r="11" fill="{col}" stroke="#2a1a12" stroke-width="4"/><circle cx="4" cy="-4" r="2.5" fill="#2a1a12"/></g>')
    for k in range(70):
        L_fx += f'<circle cx="{r.uniform(0, W):.0f}" cy="{r.uniform(200, H):.0f}" r="{r.uniform(1.5, 5):.1f}" fill="#fff0c0" opacity="{r.uniform(.2, .8):.2f}" filter="url(#glow)"/>'
    return layered('p07', [('sky', L_sky), ('far', L_far), ('sea', L_sea), ('town', L_town), ('near', L_near), ('fx', L_fx)], seed)

if __name__ == '__main__':
    import sys
    pages = p07_harbour()
    files = render(pages, '/home/claude/saga2d/out')
    print(files)
