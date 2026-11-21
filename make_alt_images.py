"""Draws a picture of every alternative protein used on the plant-based menu.

Run:  python make_alt_images.py
Writes images/alt/<slug>.svg  (one per ingredient).

Want real photos instead? Drop a file called <slug>.jpg (or .png / .webp) into images/alt/.
The site always prefers a real photo over the drawing, no code change needed.
Example: images/alt/tofu.jpg  replaces the drawn awara.
"""
import math, os, random

W, H = 480, 360
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images", "alt")


# ---------- tiny drawing helpers ----------
def ell(cx, cy, rx, ry, fill, rot=0, stroke=None, sw=1, op=1):
    s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    t = f' transform="rotate({rot:.1f} {cx:.1f} {cy:.1f})"' if rot else ""
    return f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="{fill}" opacity="{op}"{s}{t}/>'


def rr(cx, cy, w, h, r, fill, rot=0, stroke=None, sw=1, op=1):
    s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    t = f' transform="rotate({rot:.1f} {cx:.1f} {cy:.1f})"' if rot else ""
    return (f'<rect x="{cx - w / 2:.1f}" y="{cy - h / 2:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{r:.1f}" '
            f'fill="{fill}" opacity="{op}"{s}{t}/>')


def path(d, fill="none", stroke=None, sw=1, cap="round", op=1):
    s = f' stroke="{stroke}" stroke-width="{sw}" stroke-linecap="{cap}" stroke-linejoin="round"' if stroke else ""
    return f'<path d="{d}" fill="{fill}" opacity="{op}"{s}/>'


def shade(cx, cy, rx, ry, op=.22):
    return ell(cx + 3, cy + ry * .55, rx * .95, ry * .5, "#000", op=op)


def scatter(rng, n, cx=240, cy=198, rx=128, ry=70, gap=0.0, size=16):
    """Random points inside an ellipse, not too close together, back-to-front."""
    pts = []
    tries = 0
    while len(pts) < n and tries < 4000:
        tries += 1
        a, r = rng.uniform(0, math.tau), math.sqrt(rng.random())
        x, y = cx + rx * r * math.cos(a), cy + ry * r * math.sin(a)
        if all((x - px) ** 2 + ((y - py) * 1.5) ** 2 > (size * (1 - gap)) ** 2 for px, py in pts):
            pts.append((x, y))
    return sorted(pts, key=lambda p: p[1])


def plate():
    return (ell(240, 222, 205, 122, "#000", op=.16) +
            ell(240, 212, 200, 122, "url(#rim)") +
            ell(240, 212, 200, 122, "none", stroke="#d9d2c6", sw=2) +
            ell(240, 208, 160, 92, "url(#well)") +
            ell(240, 208, 160, 92, "none", stroke="#e4ddd2", sw=1.5))


ZOOM = {"oyster-mushroom": 1.05, "moi-moi": 1.2, "seitan": 1.12, "tempeh": 1.18, "banana-blossom": 1.12, "king-oyster": 1.2,
        "akara": 1.2, "egusi": 1.3, "jackfruit": 1.3, "tofu": 1.6, "tsp": 1.55}


def wrap(body, bg, zoom=1.38):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img">
<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{bg[0]}"/><stop offset="1" stop-color="{bg[1]}"/></linearGradient>
<radialGradient id="rim" cx=".4" cy=".3" r=".9"><stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="#ece6db"/></radialGradient>
<radialGradient id="well" cx=".45" cy=".35" r=".9"><stop offset="0" stop-color="#fbf9f5"/><stop offset="1" stop-color="#e9e2d6"/></radialGradient>
</defs>
<rect width="{W}" height="{H}" fill="url(#bg)"/>
<circle cx="70" cy="60" r="150" fill="#fff" opacity=".18"/>
{plate()}
<g transform="translate(240 205) scale({zoom}) translate(-240 -205)">{body}</g>
</svg>'''


# ---------- the foods ----------
def cubes(rng, base, edge, seared=True, n=8):
    o = ""
    for x, y in scatter(rng, n, size=46, rx=120, ry=58):
        r, w, h = rng.uniform(-14, 14), rng.uniform(40, 52), rng.uniform(30, 38)
        o += shade(x, y, w / 2, h / 2) + rr(x, y, w, h, 7, edge, r)
        o += rr(x, y - 1, w - 5, h - 6, 6, base, r)
        if seared:
            o += rr(x, y + 2, w - 12, h - 14, 4, "#e6c27a", r, op=.45)
        for _ in range(4):
            o += ell(x + rng.uniform(-w / 3, w / 3), y + rng.uniform(-h / 3, h / 3), 1.6, 1.2, "#c9a95e", op=.7)
        o += rr(x - 4, y - h * .28, w * .5, 4, 2, "#fff", r, op=.45)
    return o


def tofu(rng):
    return cubes(rng, "#f6e6bb", "#d9b45e")


def tsp(rng):
    o = ""
    for x, y in scatter(rng, 11, size=40, rx=122, ry=60):
        pts = []
        for i in range(9):
            a = i / 9 * math.tau
            rad = rng.uniform(15, 24)
            pts.append((x + rad * math.cos(a), y + rad * .72 * math.sin(a)))
        d = "M" + " L".join(f"{px:.1f},{py:.1f}" for px, py in pts) + "Z"
        o += shade(x, y, 22, 17) + path(d, "#b98a54", "#8a6234", 5) + path(d, "#d2a468")
        for _ in range(9):
            o += ell(x + rng.uniform(-14, 14), y + rng.uniform(-9, 9), rng.uniform(1.2, 2.6), rng.uniform(1, 2), "#7a5427", op=.65)
    return o


def tempeh(rng):
    o = ""
    for x, y, rot in [(185, 175, -8), (285, 190, 6), (225, 235, 3)]:
        o += shade(x, y, 56, 24) + rr(x, y, 104, 46, 9, "#c99f66", rot, "#a47c45", 2)
        for _ in range(60):
            px, py = x + rng.uniform(-48, 48), y + rng.uniform(-19, 19)
            o += ell(px, py, rng.uniform(3, 4.6), rng.uniform(2.4, 3.4), rng.choice(["#f3e5c3", "#ead7ab", "#fbf1d8"]), rng.uniform(0, 180), op=.95)
    return o


def seitan(rng):
    o = ""
    for i in range(7):
        x, y, rot = 240 + rng.uniform(-70, 70), 150 + i * 14 + rng.uniform(-4, 4), rng.uniform(-12, 12)
        o += shade(x, y, 70, 13) + rr(x, y, 138, 24, 11, "#9a5a3a", rot, "#764328", 2)
        o += rr(x, y, 132, 18, 9, "#bd7c53", rot)
        for k in range(-3, 4):
            o += rr(x + k * 17, y, 3, 14, 1.5, "#a0623f", rot, op=.7)
        o += rr(x - 14, y - 5, 80, 3, 1.5, "#e0a67d", rot, op=.7)
    return o


def mushroom_oyster(rng, col=("#d8d0c3", "#bdb2a2", "#a69b8a")):
    o = ""
    for cx, cy, s, rot in [(190, 190, 1.0, -12), (280, 185, 1.05, 10), (235, 230, .95, 0), (232, 160, .85, 4), (150, 225, .8, -22), (320, 232, .8, 18)]:
        a = f'<g transform="translate({cx} {cy}) rotate({rot}) scale({s})">'
        a += ell(4, 32, 40, 9, "#000", op=.2)
        a += path("M-6,34 Q-4,10 0,-2 L10,-2 Q12,12 14,34Z", "#efe9dc", "#cfc5b2", 1.5)
        a += path("M-52,-8 Q-50,-48 0,-52 Q52,-48 56,-6 Q40,10 4,8 Q-36,10 -52,-8Z", col[1], col[2], 2)
        a += path("M-46,-10 Q-44,-42 2,-46 Q46,-42 50,-8 Q30,2 2,0 Q-28,2 -46,-10Z", col[0])
        for k in range(-5, 6):
            a += path(f"M{k * 3.5},6 L{k * 9.5},-34", stroke="#fff", sw=1.4, op=.55)
        a += "</g>"
        o += a
    return o


def mushroom_button(rng):
    o = ""
    for x, y in scatter(rng, 8, size=48, rx=118, ry=56):
        s = rng.uniform(.9, 1.15)
        o += ell(x + 3, y + 22, 30 * s, 8 * s, "#000", op=.18)
        o += path(f"M{x - 7 * s},{y + 22 * s} Q{x - 4 * s},{y} {x - 5 * s},{y - 4} L{x + 6 * s},{y - 4} Q{x + 7 * s},{y + 4} {x + 9 * s},{y + 22 * s}Z", "#f3ece0", "#d5c9b5", 1.2)
        o += path(f"M{x - 28 * s},{y - 4} Q{x - 28 * s},{y - 34 * s} {x},{y - 36 * s} Q{x + 28 * s},{y - 34 * s} {x + 29 * s},{y - 4} Q{x},{y + 4} {x - 28 * s},{y - 4}Z", "#efe6d6", "#cbbca3", 1.5)
        o += path(f"M{x - 20 * s},{y - 22 * s} Q{x - 8 * s},{y - 33 * s} {x + 6},{y - 30 * s}", stroke="#fff", sw=4, op=.7)
    return o


def mushroom_shiitake(rng):
    o = ""
    for x, y in scatter(rng, 8, size=50, rx=118, ry=56):
        s = rng.uniform(.9, 1.1)
        o += ell(x + 3, y + 10, 32 * s, 8 * s, "#000", op=.18)
        o += rr(x, y + 4, 9 * s, 24 * s, 4, "#e5d5ae")
        o += path(f"M{x - 32 * s},{y} Q{x - 33 * s},{y - 32 * s} {x},{y - 33 * s} Q{x + 33 * s},{y - 32 * s} {x + 33 * s},{y} Q{x},{y + 9} {x - 32 * s},{y}Z", "#6b4630", "#4a2d1b", 2)
        o += path(f"M{x - 24 * s},{y - 8} Q{x - 20 * s},{y - 25 * s} {x},{y - 27 * s} Q{x + 22 * s},{y - 25 * s} {x + 25 * s},{y - 8} Q{x},{y - 2} {x - 24 * s},{y - 8}Z", "#8a5d3d")
        o += path(f"M{x - 16 * s},{y - 22 * s} L{x + 14 * s},{y - 8 * s} M{x + 14 * s},{y - 22 * s} L{x - 14 * s},{y - 8 * s}", stroke="#e9d8b8", sw=2.4, op=.9)
    return o


def mushroom_king(rng):
    o = ""
    for x, y, rot in [(190, 170, 20), (260, 160, -15), (320, 190, 25), (215, 225, -10), (285, 235, 12), (150, 215, 0)]:
        o += shade(x, y, 32, 26) + rr(x, y, 44, 58, 16, "#f1e7d3", rot, "#d3c3a2", 2)
        o += rr(x - 4, y - 10, 12, 34, 6, "#fff", rot, op=.5)
        for k in (-14, -4, 6, 16):
            o += rr(x + k, y + 4, 2, 40, 1, "#e0d2b4", rot, op=.8)
        o += rr(x, y - 28, 52, 12, 6, "#c9a57a", rot, "#a98458", 1.5)
    return o


def jackfruit(rng):
    o = ""
    for i in range(70):
        x, y = scatter(rng, 1, size=1, rx=120, ry=58)[0]
        a = rng.uniform(0, math.tau)
        L = rng.uniform(28, 52)
        x2, y2 = x + L * math.cos(a), y + L * .6 * math.sin(a)
        cx, cy = (x + x2) / 2 + rng.uniform(-16, 16), (y + y2) / 2 + rng.uniform(-10, 10)
        col = rng.choice(["#e9d27f", "#f0dd97", "#d9bd62", "#f4e7ae"])
        o += path(f"M{x:.1f},{y:.1f} Q{cx:.1f},{cy:.1f} {x2:.1f},{y2:.1f}", stroke=col, sw=rng.uniform(5, 8))
        o += path(f"M{x:.1f},{y - 2:.1f} Q{cx:.1f},{cy - 2:.1f} {x2:.1f},{y2 - 2:.1f}", stroke="#fff8d8", sw=1.6, op=.6)
    return o


def banana_blossom(rng):
    o = ""
    for x, y, rot, s in [(200, 190, -30, 1), (290, 195, 25, 1)]:
        a = f'<g transform="translate({x} {y}) rotate({rot}) scale({s})">'
        a += ell(0, 40, 36, 9, "#000", op=.2)
        a += path("M0,-62 Q38,-30 28,34 Q0,48 -28,34 Q-38,-30 0,-62Z", "#6d1f4a", "#4c1233", 2)
        a += path("M0,-52 Q26,-26 18,28 Q0,38 -18,28 Q-26,-26 0,-52Z", "#8e2f63")
        a += path("M0,-46 Q-8,-10 -2,30", stroke="#b24d83", sw=3, op=.7)
        a += path("M-14,-20 Q-4,-6 -10,24", stroke="#5a1840", sw=2, op=.7)
        a += "</g>"
        o += a
    for x, y in scatter(rng, 9, size=26, rx=110, ry=40, cy=240):
        o += rr(x, y, 34, 11, 5, "#f1e1b4", rng.uniform(-30, 30), "#d9c389", 1.2)
    return o


def beans(rng, fill, shade_c, shape="oval", n=60, size=1.0, eye=False, mottle=None):
    o = ""
    for x, y in scatter(rng, n, size=15 * size, gap=.25, rx=128, ry=66):
        rot = rng.uniform(0, 180)
        rx_, ry_ = (8.5 * size, 5.6 * size) if shape == "oval" else (7.5 * size, 7.2 * size) if shape == "round" else (9 * size, 5 * size)
        if shape == "disc":
            rx_, ry_ = 6.5 * size, 5 * size
        o += ell(x + 1.5, y + 3, rx_, ry_, "#000", rot, op=.22)
        o += ell(x, y, rx_, ry_, fill, rot, shade_c, 1.1)
        o += ell(x - rx_ * .25, y - ry_ * .3, rx_ * .45, ry_ * .35, "#fff", rot, op=.38)
        if eye:
            o += ell(x + rx_ * .35, y + ry_ * .1, 2.9 * size, 2.4 * size, "#fff") + ell(x + rx_ * .35, y + ry_ * .1, 1.7 * size, 1.4 * size, "#2a2420")
        if mottle and rng.random() < .8:
            o += ell(x + rng.uniform(-3, 3), y + rng.uniform(-2, 2), 2.6 * size, 2 * size, mottle, rng.uniform(0, 180), op=.7)
    return o


def cowpea(rng): return beans(rng, "#f1e6c6", "#c9b98b", "oval", 62, eye=True)
def bambara(rng): return beans(rng, "#ecd9bd", "#bfa079", "round", 54, 1.05, mottle="#a9744b")
def soybean(rng): return beans(rng, "#ead999", "#c4ad62", "round", 70, .9)
def chickpea(rng): return beans(rng, "#dcb878", "#b38d4c", "round", 56, 1.1, mottle="#c59a58")
def lentil(rng): return beans(rng, "#d9803a", "#a85a21", "disc", 90, .95, mottle="#b8662a")
def pigeon_pea(rng): return beans(rng, "#cdb27b", "#9c8250", "round", 56, 1.0, mottle="#6e4f2c")
def lima_bean(rng): return beans(rng, "#dfe6b8", "#a9b47b", "oval", 34, 1.7)
def yam_bean(rng): return beans(rng, "#a8896a", "#7b5f43", "oval", 70, .9, mottle="#5e4630")


def maize(rng):
    o = ""
    for x, y in scatter(rng, 90, size=13, rx=128, ry=66):
        o += ell(x + 1, y + 2, 6, 6.5, "#000", op=.2) + ell(x, y, 6, 6.5, "#f2c43b", stroke="#cf9d1e", sw=1) + ell(x - 1.5, y - 2, 2.6, 2, "#fff4b8", op=.8)
    return o


def egusi(rng):
    o = ""
    for x, y in scatter(rng, 70, size=14, rx=130, ry=66):
        rot = rng.uniform(0, 180)
        o += ell(x + 1, y + 2, 7.5, 4.6, "#000", rot, op=.2) + ell(x, y, 7.5, 4.6, "#efe4c3", rot, "#c9b684", 1)
        o += ell(x - 1, y - 1, 3, 1.6, "#fff", rot, op=.7)
    for x, y in [(190, 196), (260, 214), (300, 190)]:
        o += shade(x, y, 22, 20) + ell(x, y, 22, 21, "#b9a05c", stroke="#8a7438", sw=2) + ell(x - 4, y - 5, 17, 14, "#d3bd7a")
        for _ in range(12):
            o += ell(x + rng.uniform(-14, 14), y + rng.uniform(-12, 12), 3.2, 2, "#efe4c3", rng.uniform(0, 180), op=.85)
    return o


def akara(rng):
    o = ""
    for x, y in [(190, 185), (265, 175), (325, 205), (225, 232), (155, 225), (290, 245)]:
        o += shade(x, y, 29, 26) + ell(x, y, 29, 26, "#a85d1e") + ell(x - 2, y - 3, 26, 22, "#cf8a34") + ell(x - 7, y - 10, 12, 6, "#f0c070", op=.7)
        for _ in range(14):
            o += ell(x + rng.uniform(-20, 20), y + rng.uniform(-16, 16), rng.uniform(1.4, 2.8), rng.uniform(1.2, 2), "#8a4812", op=.55)
    return o


def moi_moi(rng):
    o = ""
    o += shade(240, 200, 100, 40)
    o += path("M130,215 Q130,150 240,140 Q350,150 350,215 Q350,248 240,252 Q130,248 130,215Z", "#2f6b3a", "#1d4a27", 3)
    o += path("M146,212 Q148,164 240,156 Q332,164 334,212 Q330,238 240,241 Q150,238 146,212Z", "#e8a65a")
    o += path("M146,212 Q148,164 240,156 Q332,164 334,212", stroke="#f6c680", sw=4, op=.6)
    for _ in range(40):
        o += ell(240 + rng.uniform(-90, 90), 200 + rng.uniform(-34, 34), rng.uniform(1.5, 3), rng.uniform(1.2, 2.2), "#c9812f", op=.6)
    o += ell(240, 196, 36, 20, "#fffaf0", stroke="#e2d8bc", sw=2) + ell(240, 196, 14, 10, "#f3b52c")
    return o


def groundnut(rng):
    o = ""
    for x, y in scatter(rng, 18, size=34, rx=122, ry=60):
        rot = rng.uniform(-40, 40)
        g = f'<g transform="translate({x:.1f} {y:.1f}) rotate({rot:.1f})">'
        g += ell(2, 5, 24, 11, "#000", op=.2)
        g += path("M-22,0 Q-24,-11 -10,-11 Q-3,-9 0,-4 Q3,-9 10,-11 Q24,-11 22,0 Q24,11 10,11 Q3,9 0,4 Q-3,9 -10,11 Q-24,11 -22,0Z", "#d9b783", "#a8864f", 1.8)
        for k in range(-3, 4):
            g += ell(k * 6.5, 0, 1.4, 1, "#b8945c", op=.8)
        g += "</g>"
        o += g
    for x, y in [(190, 200), (290, 215), (250, 170)]:
        o += ell(x + 2, y + 4, 11, 8, "#000", op=.2) + ell(x, y, 11, 8, "#c4623c", stroke="#9a4326", sw=1.2, rot=20) + ell(x - 3, y - 3, 4, 2.4, "#e8987a", op=.8)
    return o


def kuli_kuli(rng):
    o = ""
    for x, y in scatter(rng, 14, size=44, rx=122, ry=60):
        rot = rng.uniform(-60, 60)
        o += shade(x, y, 38, 9) + rr(x, y, 62, 14, 7, "#7a4a1f", rot, "#5b3513", 1.5) + rr(x - 2, y - 2, 56, 8, 4, "#a8692e", rot)
        for _ in range(8):
            o += ell(x + rng.uniform(-24, 24), y + rng.uniform(-3, 3), 1.4, 1, "#e0b074", rng.uniform(0, 180), op=.8)
    return o


def pumpkin_seed(rng):
    o = ""
    for x, y in scatter(rng, 52, size=19, rx=130, ry=66):
        rot = rng.uniform(0, 180)
        o += ell(x + 1.5, y + 2.5, 10, 6, "#000", rot, op=.2) + ell(x, y, 10, 6, "#7da646", rot, "#e7efc9", 2.2) + ell(x - 1.5, y - 1.5, 5.5, 2.4, "#b6d676", rot, op=.8)
    return o


def sunflower_seed(rng):
    o = ""
    for x, y in scatter(rng, 56, size=18, rx=130, ry=66):
        rot = rng.uniform(0, 180)
        o += ell(x + 1.5, y + 2.5, 10, 5.4, "#000", rot, op=.2) + ell(x, y, 10, 5.4, "#e7e1d3", rot, "#4b443a", 1.2)
        for k in (-3, 0, 3):
            o += ell(x, y + k * .8, 8, .8, "#3d372e", rot, op=.8)
    return o


def tiger_nut(rng):
    o = ""
    for x, y in scatter(rng, 40, size=22, rx=130, ry=66):
        rot = rng.uniform(0, 180)
        o += ell(x + 1.5, y + 3, 11, 8, "#000", rot, op=.2) + ell(x, y, 11, 8, "#c79a5d", rot, "#8e6a37", 1.4)
        for _ in range(3):
            o += path(f"M{x - 6 + rng.uniform(-2, 2):.1f},{y + rng.uniform(-4, 4):.1f} q4,-2 9,0", stroke="#8e6a37", sw=1, op=.7)
        o += ell(x - 3, y - 2, 4, 2, "#e6c595", rot, op=.7)
    return o


def cashew(rng):
    o = ""
    for x, y in scatter(rng, 26, size=30, rx=124, ry=60):
        rot = rng.uniform(-50, 50)
        g = f'<g transform="translate({x:.1f} {y:.1f}) rotate({rot:.1f})">'
        g += ell(2, 5, 17, 7, "#000", op=.2)
        g += path("M-16,2 Q-18,-12 -2,-11 Q14,-10 17,3 Q10,0 6,6 Q-6,12 -16,2Z", "#efd9a6", "#c9ab6c", 1.6)
        g += path("M-10,-4 Q0,-9 10,-3", stroke="#fff", sw=2.4, op=.7)
        g += "</g>"
        o += g
    return o


def ugba(rng):
    o = ""
    for x, y in scatter(rng, 36, size=34, rx=124, ry=60):
        rot = rng.uniform(-60, 60)
        g = f'<g transform="translate({x:.1f} {y:.1f}) rotate({rot:.1f})">'
        g += path("M-22,0 Q-8,-9 4,-1 Q14,6 24,-3", stroke="#000", sw=9, op=.15)
        g += path("M-22,-2 Q-8,-11 4,-3 Q14,4 24,-5", stroke="#9b6e3c", sw=8)
        g += path("M-22,-3 Q-8,-12 4,-4 Q14,3 24,-6", stroke="#c89a60", sw=4)
        g += "</g>"
        o += g
    return o


def ukwa(rng):
    o = ""
    for x, y in scatter(rng, 34, size=26, rx=126, ry=62):
        rot = rng.uniform(0, 180)
        o += ell(x + 2, y + 3, 12, 9, "#000", rot, op=.2) + ell(x, y, 12, 9, "#8a5a32", rot, "#5f3b1c", 1.4)
        o += path(f"M{x - 9:.1f},{y:.1f} Q{x:.1f},{y - 5:.1f} {x + 9:.1f},{y:.1f}", stroke="#c89363", sw=1.4, op=.8)
        o += ell(x - 4, y - 3, 4.5, 2.4, "#c4966b", rot, op=.7)
    return o


def african_walnut(rng):
    o = ""
    for x, y in scatter(rng, 22, size=34, rx=122, ry=60):
        rot = rng.uniform(0, 180)
        o += ell(x + 2, y + 4, 16, 13, "#000", rot, op=.2) + ell(x, y, 16, 13, "#c99a60", rot, "#8f6a36", 1.6)
        o += path(f"M{x - 13:.1f},{y:.1f} Q{x:.1f},{y - 10:.1f} {x + 13:.1f},{y:.1f}", stroke="#8f6a36", sw=1.4)
        o += path(f"M{x - 9:.1f},{y + 5:.1f} Q{x:.1f},{y - 3:.1f} {x + 9:.1f},{y + 5:.1f}", stroke="#a67c45", sw=1.2)
        o += ell(x - 5, y - 5, 5, 2.6, "#ecc994", rot, op=.7)
    return o


def jackfruit_seed(rng):
    o = ""
    for x, y in scatter(rng, 20, size=40, rx=122, ry=60):
        rot = rng.uniform(-40, 40)
        o += ell(x + 2, y + 4, 19, 11, "#000", rot, op=.2) + ell(x, y, 19, 11, "#f1e3c2", rot, "#c9b78e", 1.6)
        o += ell(x - 2, y - 1, 15, 7.5, "#fbf3dc", rot) + ell(x - 6, y - 3, 6, 2.4, "#fff", rot, op=.8)
    return o


def plantain(rng):
    o = ""
    for x, y in scatter(rng, 18, size=44, rx=122, ry=58):
        o += shade(x, y, 22, 14) + ell(x, y, 23, 15, "#c4a92f", stroke="#8e7d1d", sw=1.6, rot=rng.uniform(-30, 30)) + ell(x, y, 17, 10, "#e9d466", rot=rng.uniform(-30, 30))
        o += ell(x, y, 3, 2, "#9a8420", op=.8)
    return o


SLUGS = {  # slug: (drawing function, background colours, label, what it is)
    "tofu": (tofu, ("#fdf3dc", "#f3dfae"), "Awara (tofu)", "Soft soy curd, the same awara sold fried on Nigerian streets. Mild, so it soaks up pepper and yaji."),
    "tsp": (tsp, ("#f8e9d2", "#e8c99a"), "Soya chunks (TSP)", "Dried soy protein chunks soaked in seasoned stock. Chewy, and the closest bite to beef."),
    "tempeh": (tempeh, ("#f6ead2", "#e3c796"), "Tempeh", "A firm cake of fermented soybeans. Nutty, dense and very filling."),
    "seitan": (seitan, ("#f6e4d8", "#e6bf9f"), "Seitan (wheat meat)", "Chewy slices made from wheat gluten. High in protein, but it contains gluten."),
    "oyster-mushroom": (mushroom_oyster, ("#eef0e6", "#d4dcc4"), "Oyster mushroom", "Pulled into strands that chew like shredded meat. Soaks up smoky spices."),
    "button-mushroom": (mushroom_button, ("#f3efe6", "#ddd3bf"), "Button mushroom", "Meaty, mild mushrooms cooked down in pepper sauce."),
    "shiitake": (mushroom_shiitake, ("#f1e7dc", "#d8c0a6"), "Shiitake mushroom", "Deeply savoury, almost smoky mushrooms. A premium, rich-tasting swap."),
    "king-oyster": (mushroom_king, ("#f4eee2", "#dccfb4"), "King oyster mushroom", "Thick, firm stems that slice and sear like scallops or thick beef strips."),
    "jackfruit": (jackfruit, ("#fbf3cf", "#ecd98f"), "Young jackfruit", "Unripe jackfruit shredded and roasted. Pulls apart like meat and carries any sauce."),
    "banana-blossom": (banana_blossom, ("#f6e6ee", "#dcb4c8"), "Banana blossom", "Flaky, tender petals that break into fillets, like fish."),
    "cowpea": (cowpea, ("#faf1d8", "#ead8a8"), "Beans (cowpea)", "Brown or white beans (ewa), ground and cooked into a firm, filling protein."),
    "bambara": (bambara, ("#f8ead6", "#e3c7a0"), "Bambara groundnut", "A traditional Nigerian bean (okpa), earthy and rich, naturally high in protein."),
    "soybean": (soybean, ("#fbf1cc", "#ecd98c"), "Soybeans", "Whole soybeans, the most protein-dense bean you can buy cheaply."),
    "chickpea": (chickpea, ("#f9ecd0", "#e8c98e"), "Chickpeas", "Nutty chickpeas, used in falafel balls and shawarma-style strips."),
    "lentil": (lentil, ("#fbe6d2", "#eab98a"), "Lentils", "Small, quick-cooking lentils that make a hearty minced topping."),
    "pigeon-pea": (pigeon_pea, ("#f4ead3", "#dcc89e"), "Pigeon pea (fio-fio)", "Earthy pigeon peas, boiled or pressed into patties."),
    "lima-bean": (lima_bean, ("#f0f4dc", "#d0dca4"), "Lima (butter) bean", "Big, creamy beans that go soft and rich in stew."),
    "yam-bean": (yam_bean, ("#f0e4d6", "#d3b99b"), "African yam bean (otili)", "A traditional bean with a firm bite, boiled or steamed as moi moi."),
    "egusi": (egusi, ("#f7f1d6", "#e4d79e"), "Melon seed (egusi)", "The same egusi seeds from your soup, shaped into rich, filling balls."),
    "akara": (akara, ("#f9e8cf", "#e8bf8a"), "Akara (bean fritters)", "Golden, crispy bean fritters, deep-fried and loved across Nigeria."),
    "moi-moi": (moi_moi, ("#f1f1dc", "#cdd6a4"), "Moi moi", "Steamed bean pudding wrapped in leaf, soft and peppery."),
    "groundnut": (groundnut, ("#faeed7", "#e8cc9a"), "Groundnut (peanut)", "Roasted groundnuts, crunchy and rich. Contains peanuts."),
    "kuli-kuli": (kuli_kuli, ("#f4e3cf", "#d9b184"), "Kuli-kuli", "Crunchy pressed groundnut sticks, the base of yaji spice. Contains peanuts."),
    "pumpkin-seed": (pumpkin_seed, ("#eef3d8", "#c9db95"), "Pumpkin (ugu) seed", "Green pumpkin seeds, ground into rich, nutty crumbles."),
    "sunflower-seed": (sunflower_seed, ("#f3f0e6", "#d6cfbb"), "Sunflower seed", "Mild, nutty seeds that add protein and bite."),
    "tiger-nut": (tiger_nut, ("#f6ead7", "#e0c291"), "Tiger nut (aya)", "Sweet, chewy tiger nuts, a traditional northern Nigerian snack."),
    "cashew": (cashew, ("#fbf1da", "#ecd5a2"), "Cashew nut", "Creamy cashews that make a mix richer. Contains tree nuts."),
    "ugba": (ugba, ("#f3e6d3", "#d8b78a"), "Ugba (oil bean)", "Fermented oil-bean slices, savoury and slightly smoky."),
    "ukwa": (ukwa, ("#f2e3d2", "#d4ae85"), "Ukwa (breadfruit seed)", "Soft, nutty African breadfruit seeds, cooked and tossed in pepper."),
    "african-walnut": (african_walnut, ("#f5e8d4", "#ddbf8f"), "African walnut (ukpa)", "Rich, oily walnuts boiled until tender. Contains tree nuts."),
    "jackfruit-seed": (jackfruit_seed, ("#f8f0dc", "#e5d3a6"), "Jackfruit seeds", "Boiled jackfruit seeds, starchy and chestnut-like."),
    "plantain": (plantain, ("#f6f0c8", "#e2d686"), "Unripe plantain", "Firm unripe plantain that helps hold patties together."),
    "maize": (maize, ("#fcf2c4", "#efd77a"), "Sweet corn (maize)", "Sweet corn kernels, mixed with beans in adalu."),
}

def render(slug):
    """The picture as SVG text (the website draws it on request, so no image files are needed)."""
    if slug not in SLUGS:
        return None
    fn, bg = SLUGS[slug][0], SLUGS[slug][1]
    return wrap(fn(random.Random(slug)), bg, ZOOM.get(slug, 1.38))


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for slug, (fn, bg, _label, _what) in SLUGS.items():
        rng = random.Random(slug)  # same drawing every run
        with open(os.path.join(OUT, slug + ".svg"), "w", encoding="utf-8") as f:
            f.write(wrap(fn(rng), bg, ZOOM.get(slug, 1.38)))
    print(f"wrote {len(SLUGS)} pictures to {OUT}")