"""The things that stand in the other worlds, in 3D: trees, palms, bushes, cacti, crystals, ice
spikes, mushrooms, glowing toadstools, bones, rock spires, old statues, Octo City's lamp posts
and kelp hedges, and the stone Octo statues in the temples.

The sea's kelp and coral already stand up in 3D (blocks3d). This does the same for the 'C' and 'K'
tiles of every other world, and for the 'S' statues: blocks3d.style() asks kind() which thing a
tile is, blocks3d.picture() asks build() for its picture, and scene3d draws it sorted with
everything else, so Octo walks behind a palm and in front of it. The flat tile map draws just the
ground under them.

Each picture is drawn once, at twice full resolution, in tile pixels (x east, y south, z up),
then smoothed down and kept. Height lifts a point straight up the screen, as the kelp and Octo
stand (stone and crystal also lean a little to the left with height, as the buildings do, so their
sides show), and the light comes from the upper left. Leafy and soft things are made of shaded
balls (hifi's sphere impostors) and round, shaded stems; stone, crystal and ice are faceted solids
lit like the buildings (props3d.Model).
"""
import math
import random

import pygame

import hifi
import props3d
from props3d import KX, KZ, Model, dk, lt
from settings import HI, TILE

S = HI * 2                 # pictures are drawn at twice full resolution, then smoothed down
MX, MY = 12, 34            # room round the tile in a picture: either side, and above it
GROUND = 13.5              # where things stand in their tile (from its top), as blocks3d.GROUND
_LD = (-0.6, -0.8)         # towards the light, on the screen: up and to the left

# which thing a 'C' or 'K' tile is in each theme (themes not listed keep their kelp and coral)
C_KIND = {'meadow': 'tree', 'sky': 'tree', 'rainbow': 'tree', 'beach': 'palm', 'jungle': 'palm',
          'turtletown': 'palm', 'desert': 'cactus', 'crystal': 'crystal', 'starfall': 'crystal',
          'frost': 'ice', 'fungus': 'mushroom', 'bone': 'bones', 'whale': 'bones', 'thunder': 'spire',
          'volcano': 'spire', 'magma': 'spire', 'ruins': 'idol', 'city': 'broken', 'octocity': 'lamp'}
K_KIND = {'meadow': 'bush', 'jungle': 'bush', 'beach': 'bush', 'desert': 'bush', 'turtletown': 'bush',
          'crystal': 'shrooms', 'fungus': 'shrooms', 'octocity': 'hedge'}
VARIANTS = {'tree': 3, 'palm': 3, 'cactus': 3, 'crystal': 3, 'ice': 2, 'mushroom': 3, 'bones': 2, 'spire': 2,
            'idol': 2, 'broken': 2, 'lamp': 1, 'bush': 2, 'shrooms': 2, 'hedge': 2, 'statue': 1}
# how far each tall thing reaches up over the tiles behind it (Octo shows through it there)
TALL = {'tree': 30, 'palm': 30, 'cactus': 20, 'crystal': 14, 'ice': 14, 'mushroom': 18, 'spire': 24,
        'idol': 18, 'broken': 10, 'lamp': 24, 'statue': 20, 'bones': 12}


def kind(theme, ch):
    """The style key ('decor', kind, theme) of a 'C', 'K' or 'S' tile, or None if it isn't one of these."""
    if ch == 'S':
        return ('decor', 'statue', None)
    k = (C_KIND if ch == 'C' else K_KIND if ch == 'K' else {}).get(theme)
    return ('decor', k, theme) if k else None


def variant(st, tx, ty):
    """Which of its kind's pictures a tile shows (picked by where it is, like the flat tiles)."""
    return (tx * 7 + ty * 13 + tx * ty + (tx // 3) * 5) % VARIANTS[st[1]]


def every():
    """Every picture there is (for the warm-up): (kind, theme, variant)."""
    out = [('statue', None, 0)]
    for table in (C_KIND, K_KIND):
        for theme, k in table.items():
            out += [(k, theme, v) for v in range(VARIANTS[k])]
    return out


# ---- drawing helpers (tile pixels, on a canvas twice full resolution) ------------------------
def _lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def P(x, y, z=0.0):
    """Where a point in tile pixels (z up) lands on the canvas: straight up, as the kelp and coral
    and Octo himself stand."""
    return ((MX + x) * S, (MY + y - KZ * z) * S)


def PL(x, y, z=0.0):
    """The same for stone and crystal, which lean a little to the left with height, as the
    buildings do (so their east sides show)."""
    return ((MX + x - KX * z) * S, (MY + y - KZ * z) * S)


def _canvas():
    return pygame.Surface(((TILE + 2 * MX) * S, (TILE + MY + 3) * S), pygame.SRCALPHA)


def _finish(s, after=None):
    """Smooth the picture down to full resolution, and trim it to what's drawn: (image, offset of
    its top-left from the tile's top-left, in full-resolution pixels)."""
    w, h = s.get_size()
    img = pygame.transform.smoothscale(s, (w // 2, h // 2))
    if after:
        after(img)
    box = img.get_bounding_rect()
    return img.subsurface(box).copy(), (box.x - MX * HI, box.y - MY * HI)


def _shadow(s, x, y, w, h, alpha=85):
    sh = hifi.shadow(w * S, h * S, alpha)
    cx, cy = P(x, y)
    s.blit(sh, (cx - sh.get_width() / 2, cy - sh.get_height() / 2))


def _ball(s, col, x, y, z, r, ry=None, gloss=0.2):
    cx, cy = P(x, y, z)
    hifi.blit_ball(s, col, cx, cy, r * S, (r if ry is None else ry) * S, gloss)


def _halo(s, col, x, y, z, r, alpha=60):
    """A soft glow round something bright (a lamp, a glowing cap)."""
    cx, cy = P(x, y, z)
    rr = int(r * S)
    g = pygame.Surface((rr * 2, rr * 2), pygame.SRCALPHA)
    for i in range(12, 0, -1):
        k = i / 12
        pygame.draw.circle(g, col + (int(alpha * (1 - k) ** 1.6),), (rr, rr), max(1, int(rr * k)))
    s.blit(g, (cx - rr, cy - rr))


def _tube(s, pts, r0, r1, dark, light, rim=None, bands=7):
    """A round stem through 3D points, r0 thick at the first and r1 at the last, shaded like a
    cylinder lit from the upper left: bands from the dark side to a highlight near the lit side."""
    q = [P(*p) for p in pts]
    n = len(q)
    perps = []
    for i in range(n):
        ax, ay = q[max(0, i - 1)]
        bx, by = q[min(n - 1, i + 1)]
        dx, dy = bx - ax, by - ay
        d = math.hypot(dx, dy) or 1.0
        px, py = -dy / d, dx / d
        if px * _LD[0] + py * _LD[1] < 0:
            px, py = -px, -py
        perps.append((px, py))
    rs = [(r0 + (r1 - r0) * i / max(1, n - 1)) * S for i in range(n)]

    def band(k, shift):
        left, right = [], []
        for (x, y), (px, py), r in zip(q, perps, rs):
            c = shift * r
            left.append((x + px * (c + r * k), y + py * (c + r * k)))
            right.append((x + px * (c - r * k), y + py * (c - r * k)))
        return left + right[::-1]
    for j in range(bands):
        f = j / (bands - 1)
        k = 1 - 0.8 * f
        pygame.draw.polygon(s, _lerp(dark, light, f ** 0.9), band(k, 0.52 * (1 - k)))
    if rim:
        pygame.draw.polygon(s, rim, band(1.0, 0.0), max(1, S // 3))
    return q, perps, rs


def _normal(pts, inside):
    """A flat face's outward normal (Newell's method), pointing away from the point inside."""
    nx = ny = nz = 0.0
    for i in range(len(pts)):
        x0, y0, z0 = pts[i]
        x1, y1, z1 = pts[(i + 1) % len(pts)]
        nx += (y0 - y1) * (z0 + z1)
        ny += (z0 - z1) * (x0 + x1)
        nz += (x0 - x1) * (y0 + y1)
    d = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    c = [sum(p[i] for p in pts) / len(pts) for i in range(3)]
    if (c[0] - inside[0]) * nx + (c[1] - inside[1]) * ny + (c[2] - inside[2]) * nz < 0:
        d = -d
    return (nx / d, ny / d, nz / d)


def _draw_model(s, m):
    """Draw a props3d Model straight onto the canvas (it's smoothed down with everything else)."""
    for _, what, data in sorted(m.faces, key=lambda f: f[0]):
        if what == 'poly':
            pts, c, lines = data
            q = [PL(*p) for p in pts]
            pygame.draw.polygon(s, c, q)
            pygame.draw.polygon(s, c, q, 1)              # no seams between neighbours
            for a, b, lc in lines:
                pygame.draw.line(s, lc, PL(*a), PL(*b), max(1, S // 3))
        elif what == 'line':
            a, b, c, w = data
            pygame.draw.line(s, c, PL(*a), PL(*b), max(1, int(w * S)))


# ---- trees, palms, bushes and hedges ---------------------------------------------------------
TREE_LEAVES = {'meadow': ((46, 118, 52), (98, 184, 76), (190, 240, 130)),
               'sky': ((52, 130, 58), (110, 196, 84), (200, 246, 140)),
               'rainbow': ((196, 110, 170), (250, 170, 214), (255, 232, 246))}


def _leaves(s, balls, cx, cy, cz, deep, leaf, light, gloss=0.1):
    """A leafy mass of shaded balls, back ones first: darker underneath, bright on top."""
    balls.sort(key=lambda b: 0.78 * b[1] + b[2])
    lo = min(b[2] for b in balls)
    hi = max(b[2] for b in balls)
    for bx, by, bz, r in balls:
        t = (bz - lo) / ((hi - lo) or 1) * 0.75 + 0.12 * max(-1.0, min(1.0, by / 4)) - 0.04 * bx / 4 + 0.15
        col = _lerp(deep, leaf, t / 0.55) if t < 0.55 else _lerp(leaf, light, (t - 0.55) * 0.8)
        _ball(s, col, cx + bx, cy + by, cz + bz, r, gloss=gloss)


def _tree(s, theme, v):
    rnd = random.Random(v * 41 + 3)
    deep, leaf, light = TREE_LEAVES[theme]
    bark, bark_hi = (92, 60, 36), (184, 136, 88)
    x0, y0 = 8.0, GROUND - 1.4
    _shadow(s, 8.4, GROUND + 0.2, 17, 5.5, 95)
    for a in (-0.5, 0.6, 2.7):                                     # roots
        _tube(s, [(x0 + math.cos(a) * 2.6, y0 + math.sin(a) * 1.4, 0), (x0, y0, 2.0)], 0.6, 1.0, dk(bark, 0.7),
              bark_hi, rim=dk(bark, 0.45), bands=4)
    lean = rnd.uniform(-0.6, 0.6)
    _tube(s, [(x0, y0, 0), (x0 + lean * 0.4, y0, 4), (x0 + lean, y0, 9)], 1.7, 1.25, dk(bark, 0.62), bark_hi,
          rim=dk(bark, 0.45))
    cx, cy, cz = x0 + lean, y0 - 0.3, 13.6 + v * 0.7
    R = 7.4 + rnd.uniform(-0.3, 0.4)
    balls = [(0.0, 0.0, 0.0, R * 0.8)]
    for i in range(8):                                             # a lumpy ring round the middle
        a = i / 8 * math.tau + rnd.uniform(-0.25, 0.25)
        balls.append((math.cos(a) * R * 0.6, math.sin(a) * R * 0.42, rnd.uniform(-1.8, 0.8), R * rnd.uniform(0.44, 0.54)))
    for i in range(5):                                             # and on top
        a = i / 5 * math.tau + rnd.uniform(0, 1)
        balls.append((math.cos(a) * R * 0.34, math.sin(a) * R * 0.26, R * 0.5 + rnd.uniform(-0.4, 0.6), R * rnd.uniform(0.4, 0.48)))
    balls.append((-R * 0.12, 0.3, R * 0.78, R * 0.38))
    _leaves(s, balls, cx, cy, cz, deep, leaf, light)
    if theme == 'rainbow':                                         # blossoms
        for i in range(14):
            a = rnd.uniform(0, math.tau)
            rr = rnd.uniform(0.2, 0.95) * R
            px, py = P(cx + math.cos(a) * rr, cy + math.sin(a) * rr * 0.6, cz + R * 0.35 + rnd.uniform(-2, 2))
            c = rnd.choice(((255, 255, 255), (255, 240, 120), (255, 200, 236)))
            pygame.draw.circle(s, dk(c, 0.75), (px + S * 0.15, py + S * 0.15), S * 0.55)
            pygame.draw.circle(s, c, (px, py), S * 0.5)
    else:                                                          # a few bright leaves catching the light
        for i in range(10):
            a = rnd.uniform(math.pi * 0.9, math.pi * 1.7)
            rr = rnd.uniform(0.35, 0.9) * R
            px, py = P(cx + math.cos(a) * rr, cy + math.sin(a) * rr * 0.55, cz + R * 0.3 + rnd.uniform(-1, 2))
            pygame.draw.ellipse(s, light, (px - S * 0.6, py - S * 0.35, S * 1.2, S * 0.7))
        if theme == 'sky' and v == 1:                              # apples
            for i in range(4):
                a = rnd.uniform(0, math.pi)
                _ball(s, (220, 50, 50), cx + math.cos(a) * R * 0.7, cy + math.sin(a) * R * 0.45 + 1, cz - 1.5, 0.9,
                      gloss=0.7)


PALM_LEAVES = {'beach': ((40, 110, 44), (86, 170, 66), (176, 226, 120)),
               'jungle': ((20, 80, 36), (50, 136, 52), (130, 200, 96)),
               'turtletown': ((40, 110, 44), (86, 170, 66), (176, 226, 120))}


def _frond(s, c, a, length, width, deep, leaf, light, droop=1.0):
    """One palm frond: from the crown c out the way of angle a, arching up then drooping, with a
    jagged edge for its leaflets and its upper half catching the light."""
    cx, cy, cz = c
    n = 10
    ca, sa = math.cos(a), math.sin(a) * 0.85
    spine, top, bot = [], [], []
    for i in range(n + 1):
        t = i / n
        x, y = cx + ca * length * t, cy + sa * length * t
        z = cz + length * (0.38 * t - droop * 0.95 * t * t)
        spine.append(P(x, y, z))
        w = width * math.sin(math.pi * min(1.0, t * 1.08)) ** 0.7 * (1.0 if i % 2 else 0.62)
        px, py = -sa, ca                                   # across the frond, flat
        top.append(P(x + px * w, y + py * w, z))
        bot.append(P(x - px * w, y - py * w, z))
    # which edge faces the light (up and left on the screen)
    (x0, y0), (x1, y1) = top[n // 2], bot[n // 2]
    if (x0 - x1) * _LD[0] + (y0 - y1) * _LD[1] < 0:
        top, bot = bot, top
    back = math.sin(a) < 0
    base = _lerp(deep, leaf, 0.35 if back else 0.8)
    pygame.draw.polygon(s, dk(base, 0.62), top + bot[::-1])
    pygame.draw.polygon(s, base, [((p[0] + q[0]) / 2, (p[1] + q[1]) / 2) for p, q in zip(top, bot)][::-1] + top)
    pygame.draw.lines(s, _lerp(base, light, 0.6), False, spine, max(1, S // 3))
    pygame.draw.lines(s, dk(base, 0.45), False, top + bot[::-1], max(1, S // 4))


def _palm(s, theme, v):
    rnd = random.Random(v * 59 + 11)
    deep, leaf, light = PALM_LEAVES[theme]
    bark, bark_hi = (110, 78, 44), (196, 158, 104)
    x0, y0 = 7.4, GROUND - 1.4
    lean = (1, -1, 0.6)[v] * rnd.uniform(3.0, 4.5)
    H = 20.5 + rnd.uniform(-1, 1.5)
    _shadow(s, 8.6 + lean * 0.3, GROUND + 0.4, 18, 5.5, 85)
    pts = [(x0 + lean * f ** 1.7, y0 - f * 0.6, f * H) for f in (0, 0.2, 0.4, 0.6, 0.8, 1.0)]
    q, perps, rs = _tube(s, pts, 1.75, 1.05, dk(bark, 0.62), bark_hi, rim=dk(bark, 0.42))
    for i in range(1, 12):                                         # the ringed bark
        f = i / 12
        j = min(len(q) - 2, int(f * (len(q) - 1)))
        u = f * (len(q) - 1) - j
        x = q[j][0] + (q[j + 1][0] - q[j][0]) * u
        y = q[j][1] + (q[j + 1][1] - q[j][1]) * u
        px, py = perps[j]
        r = rs[j] + (rs[j + 1] - rs[j]) * u
        arc = [(x + px * r * k, y + py * r * k + (1 - k * k) * r * 0.3) for k in (-1, -0.5, 0, 0.5, 1)]
        pygame.draw.lines(s, dk(bark, 0.5), False, arc, max(1, S // 4))
    crown = pts[-1]
    fronds = []
    for i in range(8):
        a = i / 8 * math.tau + v * 0.4 + rnd.uniform(-0.15, 0.15)
        fronds.append((math.sin(a), a, rnd.uniform(8.5, 10.5), rnd.uniform(0.85, 1.15)))
    fronds.sort()                                                  # the ones reaching back first
    for k, (_, a, ln, dr) in enumerate(fronds):
        if k == 3:                                                 # coconuts, among the fronds
            for dx, dy in ((-0.9, 0.7), (0.8, 0.9), (0.0, 1.5)):
                _ball(s, (112, 74, 36), crown[0] + dx, crown[1] + dy, crown[2] - 1.0, 1.15, gloss=0.5)
        _frond(s, crown, a, ln, 1.9, deep, leaf, light, dr)
    _ball(s, _lerp(deep, leaf, 0.6), crown[0], crown[1], crown[2] + 0.3, 1.2, gloss=0.1)


BUSH_LEAVES = {'meadow': ((40, 110, 48), (92, 176, 72), (186, 238, 128)),
               'jungle': ((26, 92, 40), (62, 150, 62), (150, 218, 110)),
               'beach': ((60, 128, 52), (118, 190, 84), (200, 240, 144)),
               'desert': ((96, 112, 52), (156, 172, 88), (220, 228, 156)),
               'turtletown': ((40, 112, 50), (92, 178, 74), (184, 236, 128)),
               'octocity': ((24, 98, 54), (56, 160, 88), (140, 226, 146))}


def _bush(s, theme, v, hedge=False):
    rnd = random.Random(v * 17 + 5 + len(theme))
    deep, leaf, light = BUSH_LEAVES[theme]
    _shadow(s, 8.4, GROUND + 0.2, 17, 5, 85)
    balls = []
    if hedge:                                                      # a trimmed hedge: a rounded block
        for i in range(4):
            for j in range(2):
                balls.append((-5.4 + i * 3.6, -1.4 + j * 3.0, rnd.uniform(-0.3, 0.3), 3.1))
        for i in range(3):
            balls.append((-3.6 + i * 3.6, 0.0, 3.2 + rnd.uniform(-0.3, 0.3), 2.9))
    else:
        for i in range(5):
            a = i / 5 * math.tau + v * 0.6
            balls.append((math.cos(a) * 4.0, math.sin(a) * 2.0, rnd.uniform(-0.4, 0.6), rnd.uniform(3.0, 3.6)))
        balls.append((rnd.uniform(-1, 1), 0.0, 3.0, 3.6))
    _leaves(s, balls, 8.0, 11.0, 3.0 if not hedge else 3.4, deep, leaf, light, gloss=0.08)
    if hedge:                                                      # kelp leaves poking out of the top
        for i in range(5):
            x = 2.5 + i * 2.8 + rnd.uniform(-0.5, 0.5)
            pts = [(x, 11, 7.5), (x + 0.6, 11, 10 + rnd.uniform(0, 1.5)), (x - 0.2, 11, 12 + rnd.uniform(0, 1.5))]
            _tube(s, pts, 0.9, 0.2, deep, light, bands=4)
        return
    for i in range(4 + v):                                         # flowers
        a = rnd.uniform(math.pi * 0.8, math.pi * 2.2)
        px, py = P(8 + math.cos(a) * 3.5, 11 + math.sin(a) * 2, 5 + rnd.uniform(-1, 1.5))
        c = ((250, 120, 160), (250, 230, 110), (255, 255, 255))[i % 3]
        if theme == 'desert':
            c = ((250, 200, 90), (240, 140, 170))[i % 2]
        pygame.draw.circle(s, dk(c, 0.7), (px + S * 0.2, py + S * 0.2), S * 0.75)
        pygame.draw.circle(s, c, (px, py), S * 0.68)
        pygame.draw.circle(s, (255, 250, 210), (px - S * 0.2, py - S * 0.2), S * 0.25)


# ---- desert, caves and mushrooms -------------------------------------------------------------
def _cactus(s, theme, v):
    """A tall ribbed cactus with its arms held up (and a flower on some)."""
    deep, green, light = (34, 96, 48), (76, 160, 80), (164, 220, 132)
    x0, y0 = 8.0, GROUND - 1.6
    H = (16.5, 14.5, 18.0)[v]
    _shadow(s, 8.4, GROUND + 0.3, 14, 4.6, 85)
    arms = ((-1, 6.5, 4.8, 5.0), (1, 9.0, 4.6, 4.4)) if v == 0 else \
        ((1, 6.0, 4.8, 5.5),) if v == 1 else ((-1, 9.5, 4.4, 4.0), (1, 6.0, 5.0, 6.0))

    def arm(side, z, reach, up):
        pts = [(x0, y0, z), (x0 + side * (reach - 1.4), y0, z + 0.1), (x0 + side * reach, y0, z + 1.3),
               (x0 + side * reach, y0, z + up)]
        _tube(s, pts, 1.45, 1.35, deep, light, rim=dk(deep, 0.6))
        _ball(s, green, *pts[-1], 1.35, gloss=0.15)
        q = [P(*p) for p in pts[2:]]
        for k in (-0.5, 0.45):
            pygame.draw.lines(s, deep, False, [(x + k * 1.35 * S, y) for x, y in q], max(1, S // 4))
    for side, z, reach, up in arms:                                # (an arm on the left is a bit further away)
        if side < 0:
            arm(side, z, reach, up)
    q_main, perps, rs = _tube(s, [(x0, y0, 0), (x0, y0, H * 0.5), (x0, y0, H)], 2.4, 2.2, deep, light, rim=dk(deep, 0.6))
    _ball(s, green, x0, y0, H, 2.2, gloss=0.15)
    for k in (-0.62, -0.2, 0.22, 0.64):                            # ribs, with spines along them
        line = [(x + k * r, y) for (x, y), r in zip(q_main, rs)]
        pygame.draw.lines(s, deep, False, line, max(1, S // 4))
        for i in range(1, 8):
            f = i / 8
            x = line[0][0] + (line[-1][0] - line[0][0]) * f
            y = line[0][1] + (line[-1][1] - line[0][1]) * f
            pygame.draw.circle(s, (250, 246, 210), (x + S * 0.3, y), max(1, S // 5))
    for side, z, reach, up in arms:
        if side > 0:
            arm(side, z, reach, up)
    if v != 1:                                                     # a flower on top
        for a in range(5):
            ang = a / 5 * math.tau
            px, py = P(x0 + math.cos(ang) * 0.9, y0 + math.sin(ang) * 0.6, H + 2.0)
            pygame.draw.circle(s, (240, 90, 140) if v == 0 else (250, 200, 70), (px, py), S * 0.7)
        px, py = P(x0, y0, H + 2.1)
        pygame.draw.circle(s, (255, 236, 140), (px, py), S * 0.45)


def _prism(m, bx, by, r, h, tip, lean, col, sides=6, turn=0.0, amb=0.55, ridge=None):
    """A crystal: a many-sided prism with a pointed tip, standing at (bx, by), leaning lean (x, y)
    per unit of height."""
    lx, ly = lean

    def V(a, rad, z):
        return (bx + rad * math.cos(a) + lx * z, by + rad * math.sin(a) * 0.85 + ly * z, z)
    angs = [turn + i / sides * math.tau for i in range(sides)]
    bot = [V(a, r, -1.0) for a in angs]
    top = [V(a, r, h) for a in angs]
    apex = (bx + lx * (h + tip), by + ly * (h + tip), h + tip)
    mid = (bx + lx * h / 2, by + ly * h / 2, h / 2)
    for i in range(sides):
        j = (i + 1) % sides
        side = [bot[i], bot[j], top[j], top[i]]
        lines = [(bot[i], top[i], ridge)] if ridge else []
        m.face(side, col, _normal(side, mid), lines, amb=amb)
        tri = [top[i], top[j], apex]
        m.face(tri, lt(col, 0.2), _normal(tri, mid), [(top[i], apex, ridge)] if ridge else [], amb=amb)
    return apex


CRYSTALS = {'crystal': ((150, 200, 255), (200, 170, 255), (140, 240, 230)),
            'starfall': ((255, 232, 150), (255, 250, 220), (200, 214, 255))}


def _crystals(s, theme, v, ice=False):
    rnd = random.Random(v * 31 + (7 if ice else 2))
    m = Model()
    if ice:
        cols = ((120, 186, 240), (176, 220, 252), (96, 160, 226))
        spec = [(8, 11.5, 1.2, 8 + v * 2, 4.0, (0.02, 0.0)), (5.0, 12.8, 0.95, 5, 3.0, (-0.2, 0.04)),
                (11.2, 12.6, 1.0, 6, 3.2, (0.22, 0.06)), (6.6, 14.2, 0.8, 3, 2.2, (-0.1, 0.25)),
                (10.0, 9.8, 0.85, 5, 2.6, (0.12, -0.18)), (3.6, 10.6, 0.7, 3.4, 2.0, (-0.3, -0.1))]
        _shadow(s, 8.4, GROUND + 0.3, 15, 4.6, 60)
        sn = pygame.Rect(0, 0, 13 * S, 4.4 * S)                    # snow drifted round the foot
        sn.center = P(8.2, 12.4)
        pygame.draw.ellipse(s, (226, 236, 248), sn)
        pygame.draw.ellipse(s, (250, 252, 255), sn.inflate(-3 * S, -1.6 * S).move(-0.8 * S, -0.5 * S))
    else:
        cols = CRYSTALS[theme]
        spec = [(8, 11.2, 1.9, 7 + v * 1.5, 3.4, (0.0, 0.04)), (4.8, 12.6, 1.5, 4.5, 2.6, (-0.3, 0.06)),
                (11.4, 12.4, 1.45, 4.2 + v, 2.4, (0.32, 0.1)), (7.4, 14.0, 1.1, 2.4, 1.8, (-0.08, 0.32)),
                (10.2, 9.4, 1.2, 4, 2.2, (0.16, -0.22))]
        _shadow(s, 8.4, GROUND + 0.3, 15, 4.6, 70)
        for i, (bx, by, r, h, tip, lean) in enumerate(spec[:3]):  # their glow on the ground
            _halo(s, cols[i % 3], bx + lean[0] * h * 0.5, by + 0.6, 0, 4.2 + r, 70)
    tips = []
    k = 1.18 if not ice else 1.1                                   # (a little bigger than the flat ones)
    order = sorted(range(len(spec)), key=lambda i: spec[i][1])
    for i in order:
        bx, by, r, h, tip, lean = spec[i]
        c = cols[(i + v) % len(cols)]
        tips.append(_prism(m, bx, by, r * k, h * k, tip * k, lean, c, sides=6 if not ice else 5,
                           turn=rnd.uniform(0, 1), amb=0.6, ridge=lt(c, 0.7)))
    _draw_model(s, m)
    hx, hy = PL(*max(tips, key=lambda p: p[2]))                     # a sparkle on the tallest tip
    for dx, dy, ln in ((1, 0, 2.2), (0, 1, 2.6)):
        pygame.draw.line(s, (255, 255, 255), (hx - dx * ln * S, hy - dy * ln * S), (hx + dx * ln * S, hy + dy * ln * S),
                         max(1, S // 3))
    pygame.draw.circle(s, (255, 255, 255), (hx, hy), S * 0.5)


MUSHROOM_CAPS = ((214, 64, 84), (150, 92, 222), (238, 152, 58))


def _mushroom(s, theme, v):
    rnd = random.Random(v * 13 + 9)
    cap = MUSHROOM_CAPS[v]
    stem_d, stem_l = (150, 132, 118), (240, 232, 214)
    x0, y0 = 8.0, GROUND - 1.8
    _shadow(s, 8.6, GROUND + 0.2, 15, 5, 90)
    if v == 1:                                                     # a little one beside it
        _tube(s, [(12.6, GROUND - 0.6, 0), (12.8, GROUND - 0.6, 3.2)], 0.8, 0.7, stem_d, stem_l, rim=dk(stem_d, 0.6))
        _ball(s, cap, 12.9, GROUND - 0.6, 3.9, 2.0, 1.25, gloss=0.5)
    _tube(s, [(x0, y0, 0), (x0 - 0.3, y0, 4), (x0 - 0.5, y0, 9)], 2.0, 1.4, stem_d, stem_l, rim=dk(stem_d, 0.6))
    sx, sy = P(x0 - 0.8, y0, 5.6)                                  # a ring round the stem
    pygame.draw.ellipse(s, stem_l, (sx - 2.2 * S, sy - 0.6 * S, 4.4 * S, 1.5 * S))
    pygame.draw.ellipse(s, stem_d, (sx - 2.2 * S, sy - 0.6 * S, 4.4 * S, 1.5 * S), max(1, S // 4))
    cxy = (x0 - 0.6, y0, 11.0)
    gx, gy = P(*cxy)
    pygame.draw.ellipse(s, dk(cap, 0.45), (gx - 7.0 * S, gy - 0.6 * S, 14 * S, 4.2 * S))      # the gills underneath
    _ball(s, cap, *cxy, 7.2, 4.9, gloss=0.45)
    for i in range(6):                                             # white spots
        a = rnd.uniform(math.pi * 0.95, math.pi * 2.05)
        rr = rnd.uniform(0.15, 0.75)
        px = gx + math.cos(a) * rr * 6.4 * S
        py = gy + math.sin(a) * rr * 3.4 * S - (1 - rr) * 1.0 * S
        w = (1.5 - rr * 0.6) * S
        pygame.draw.ellipse(s, (255, 248, 236), (px - w, py - w * 0.6, 2 * w, 1.2 * w))


SHROOM_GLOW = {'fungus': ((120, 230, 160), (190, 255, 200)), 'crystal': ((110, 210, 240), (190, 240, 255))}


def _shrooms(s, theme, v):
    cap, glow = SHROOM_GLOW[theme]
    stem_d, stem_l = (150, 150, 140), (232, 236, 220)
    spots = [(4.2, 11.0, 4.6, 2.6), (11.2, 10.0, 5.8, 2.9), (7.8, 13.6, 3.2, 2.1)]
    if v:
        spots = [(5.0, 10.2, 5.6, 2.8), (11.6, 11.6, 3.8, 2.3), (8.4, 13.8, 4.2, 2.4), (2.8, 13.4, 2.6, 1.7)]
    _shadow(s, 8.0, GROUND, 15, 4.4, 55)
    for x, y, h, r in spots:
        _halo(s, glow, x, y, h, r * 2.8, 90)
    for x, y, h, r in sorted(spots, key=lambda p: p[1]):
        _tube(s, [(x, y, 0), (x + 0.2, y, h)], 0.75, 0.6, stem_d, stem_l, bands=4)
        _ball(s, cap, x + 0.2, y, h + 0.3, r, r * 0.62, gloss=0.7)
        px, py = P(x - 0.4, y, h + 0.6)
        pygame.draw.circle(s, (255, 255, 255), (px, py), S * 0.35)


# ---- bones and rocks -------------------------------------------------------------------------
def _bones(s, theme, v):
    """A ribcage half buried in the sand, seen from its front: each rib an arch out of the sand,
    the spine along their tops, the biggest ribs at the back (a whale's are huge)."""
    whale = theme == 'whale'
    ivory_d, ivory, ivory_l = (134, 124, 104), (216, 208, 188), (252, 248, 236)
    rim = (74, 66, 54)
    cx = 8.0
    if whale:
        ribs = [(6.4, 6.4, 11.0), (9.6, 6.6, 10.4), (12.8, 6.0, 8.8)]
        thick = 1.05
    else:
        ribs = [(7.4, 5.0, 8.2), (9.6, 5.2, 7.6), (11.8, 4.8, 6.6), (14.0, 4.0, 5.2)]
        thick = 0.78
    if v:
        ribs = ribs[:-1] if whale else ribs[1:]
    _shadow(s, 8.2, (ribs[0][0] + ribs[-1][0]) / 2 + 0.6, 16, 7.5, 85)
    tops = []
    for y, w, h in ribs:                                           # back to front
        pts = []
        for i in range(11):
            a = (0.04 + i / 10 * 0.92) * math.pi
            pts.append((cx + w * math.cos(a), y, h * math.sin(a) ** 0.8))
        _tube(s, pts, thick, thick, ivory_d, ivory_l, rim=rim, bands=5)
        tops.append((cx, y, h))
    _tube(s, [(cx, tops[0][1] - 1.2, tops[0][2] - 0.4)] + tops, thick * 1.15, thick, ivory_d, ivory_l, rim=rim,
          bands=5)                                                 # the spine
    for x, y, z in tops:
        _ball(s, ivory, x, y, z + 0.3, thick * 1.35, gloss=0.3)
    if not whale and v == 0:                                       # a skull in front
        sx, sy = 12.8, 14.8
        _ball(s, ivory, sx, sy, 1.8, 2.3, 1.9, gloss=0.3)
        for dx in (-0.9, 0.8):
            px, py = P(sx + dx, sy, 2.2)
            pygame.draw.ellipse(s, (40, 34, 30), (px - 0.65 * S, py - 0.5 * S, 1.3 * S, 1.1 * S))
        px, py = P(sx, sy, 0.8)
        pygame.draw.line(s, rim, (px - 1.1 * S, py), (px + 1.1 * S, py), max(1, S // 4))


SPIRE_ROCK = {'thunder': ((70, 76, 98), (124, 130, 158), (172, 178, 204), (220, 226, 246)),
              'volcano': ((40, 32, 30), (84, 66, 62), (120, 98, 92), (168, 112, 84)),
              'magma': ((46, 24, 18), (92, 52, 40), (130, 76, 56), (178, 98, 60))}


def _rock(m, cx, cy, R, H, lean, rnd, mid, light, top, k=7, rings=((0.0, 1.0), (0.42, 0.66), (0.76, 0.34))):
    """A faceted, lumpy rock rising to a point. Returns its faces that face you (for cracks)."""
    rr = []
    for zf, rf in rings:
        ring = []
        for i in range(k):
            a = i / k * math.tau + rnd.uniform(-0.22, 0.22)
            rad = R * rf * rnd.uniform(0.8, 1.14)
            ring.append((cx + lean[0] * zf + rad * math.cos(a), cy + lean[1] * zf + rad * math.sin(a) * 0.8, H * zf))
        rr.append(ring)
    apex = (cx + lean[0] + rnd.uniform(-0.4, 0.4), cy + lean[1], H)
    inside = (cx + lean[0] * 0.4, cy, H * 0.35)
    front = []
    for r0, r1 in zip(rr, rr[1:]):
        for i in range(k):
            j = (i + 1) % k
            f = [r0[i], r0[j], r1[j], r1[i]]
            nrm = _normal(f, inside)
            m.face(f, _lerp(mid, light, rnd.uniform(0, 0.55)), nrm, amb=0.45)
            if nrm[1] > 0.35:
                front.append(f)
    for i in range(k):
        f = [rr[-1][i], rr[-1][(i + 1) % k], apex]
        m.face(f, _lerp(mid, top, rnd.uniform(0.3, 0.6)), _normal(f, inside), amb=0.45)
    return front


def _spire(s, theme, v):
    """A jagged rock spire with a couple of boulders at its foot (cracks glowing near the lava)."""
    rnd = random.Random(v * 19 + len(theme))
    dark, mid, light, hi_ = SPIRE_ROCK[theme]
    lava = theme in ('volcano', 'magma')
    cx, cy = 8.0, 11.2
    H = 17 + v * 3 + rnd.uniform(-1, 1)
    _shadow(s, 8.4, GROUND, 17, 5.5, 95)
    if lava:
        _halo(s, (255, 110, 30), cx, cy + 1.5, 0, 9, 50)
    m = Model()
    front = _rock(m, cx, cy, 5.0, H, (rnd.uniform(-1.4, 1.4), rnd.uniform(-0.5, 0.3)), rnd, mid, light, hi_)
    for bx, by, br in ((3.4, 13.2, 2.4), (12.6, 13.6, 2.0 + v * 0.5)):     # boulders at its foot
        _rock(m, bx, by, br, br * 1.3, (0, 0), rnd, mid, light, hi_, k=6, rings=((0.0, 1.0), (0.6, 0.7)))
    _draw_model(s, m)
    for f in rnd.sample(front, min(len(front), 3 if lava else 2)):  # cracks (glowing, near lava)
        u, w = rnd.uniform(0.25, 0.75), rnd.uniform(0.25, 0.6)
        x = f[0][0] + (f[1][0] - f[0][0]) * u
        y = f[0][1] + (f[1][1] - f[0][1]) * u
        z = f[0][2] + (f[3][2] - f[0][2]) * w
        pts = [PL(x, y + 0.1, z)]
        for _ in range(4):
            x += rnd.uniform(-0.8, 0.8)
            z -= rnd.uniform(0.9, 1.6)
            pts.append(PL(x, y + 0.1, max(0.2, z)))
        if lava:
            pygame.draw.lines(s, (255, 110, 30), False, pts, max(1, int(S * 0.7)))
            pygame.draw.lines(s, (255, 230, 120), False, pts, max(1, S // 3))
        else:
            pygame.draw.lines(s, dark, False, pts, max(1, S // 3))


def _idol(s, theme, v):
    """An ancient stone head on a plinth, its eyes and rune still glowing."""
    stone, dark, light = (150, 146, 120), (88, 84, 68), (196, 190, 160)
    glow = (90, 230, 180)
    rnd = random.Random(v * 3 + 1)
    _shadow(s, 8.4, GROUND, 15, 5, 90)
    m = Model()
    m.box(2.6, 8.6, 0, 13.4, 15.0, 2.0, dark, top=stone)
    m.box(4.0, 9.6, 2.0, 12.0, 14.0, 9.0 + v, stone, top=light)
    hz = 9.0 + v
    m.box(4.4, 10.0, hz, 11.6, 13.6, hz + 6.4, stone, top=light)
    m.box(4.0, 13.4, hz + 3.6, 12.0, 14.2, hz + 4.6, dark)          # the brow
    m.quad_s(5.4, 7.2, 13.65, hz + 1.9, hz + 3.0, glow, lit=False, bias=0.6)
    m.quad_s(8.8, 10.6, 13.65, hz + 1.9, hz + 3.0, glow, lit=False, bias=0.6)
    m.quad_s(6.0, 10.0, 14.05, 4.0, 4.6, glow, lit=False, bias=0.6)      # a rune band
    m.quad_s(7.6, 8.4, 14.05, 4.6, 7.0, glow, lit=False, bias=0.6)
    m.line((5.0, 14.02, 8.0 + v), (6.2, 14.02, 6.5), dark, w=0.35, bias=0.7)    # cracks
    m.line((11.0, 13.62, hz + 5.8), (10.2, 13.62, hz + 4.8), dark, w=0.35, bias=0.7)
    _draw_model(s, m)
    for i in range(5):                                             # moss on top
        x, y = rnd.uniform(4.8, 11.2), rnd.uniform(10.4, 13.0)
        px, py = PL(x, y, hz + 6.4)
        pygame.draw.ellipse(s, (70, 130, 60), (px - 1.2 * S, py - 0.6 * S, 2.4 * S, 1.2 * S))
        pygame.draw.ellipse(s, (110, 170, 80), (px - 0.8 * S, py - 0.6 * S, 1.4 * S, 0.8 * S))
    for x0 in (6.3, 9.7):
        _halo(s, glow, x0 - KX * (hz + 2.4), 13.7, hz + 2.4, 2.4, 80)


def _broken(s, theme, v):
    """A toppled statue in the sunken city: its legs still on the plinth, its head in the sand."""
    stone, dark, light = (140, 146, 170), (74, 78, 98), (186, 192, 214)
    _shadow(s, 8.4, GROUND, 16, 5, 90)
    m = Model()
    m.box(3.0, 8.4, 0, 12.6, 13.8, 4.0, dark, top=stone, bricks=2)
    m.box(4.4, 9.4, 4.0, 7.4, 12.6, 9.5 - v, stone, top=light)
    m.box(8.2, 9.4, 4.0, 11.2, 12.6, 7.6 + v, stone, top=light)
    m.line((4.6, 12.62, 8.4 - v), (7.2, 12.62, 9.2 - v), dark, w=0.3, bias=0.5)
    _draw_model(s, m)
    hx, hy = (13.4, 14.6) if v == 0 else (2.6, 14.4)
    _ball(s, stone, hx, hy, 2.2, 2.6, 2.3, gloss=0.2)
    px, py = P(hx + (0.6 if v == 0 else -0.6), hy + 1.2, 2.4)
    pygame.draw.line(s, dark, (px - 0.9 * S, py), (px + 0.9 * S, py), max(1, S // 3))
    pygame.draw.circle(s, dark, (px - 0.8 * S, py - 0.9 * S), S * 0.4)
    pygame.draw.circle(s, dark, (px + 0.8 * S, py - 0.9 * S), S * 0.4)


# ---- Octo City's lamp posts, and the temples' statues ---------------------------------------
def _lamp(s, theme, v):
    """Octo City's street lamp: a slim pole with a glowing jellyfish for its lamp."""
    pole_d, pole_l = (70, 40, 90), (176, 136, 196)
    globe, rim = (255, 228, 140), (240, 120, 170)
    x0, y0 = 8.0, GROUND - 1.6
    _shadow(s, 8.4, GROUND, 9, 3.4, 90)
    m = Model()
    m.cyl(x0, y0, 2.2, 0, 1.0, pole_d, n=14, top=lt(pole_d, 0.25))
    _draw_model(s, m)
    _tube(s, [(x0, y0, 0.9), (x0, y0, 15.5)], 0.85, 0.7, pole_d, pole_l, rim=dk(pole_d, 0.6), bands=5)
    gz = 19.0
    _halo(s, globe, x0, y0, gz, 10, 80)
    for i in range(6):                                             # its frills, hanging down
        a = (i + 0.5) / 6 * math.pi
        bx = x0 - 3.4 * math.cos(a)
        pts = [P(bx, y0, gz - 2.2 - k * 1.2 - (0.4 if i % 2 else 0)) for k in range(4)]
        pts = [(x + math.sin(j * 1.8 + i) * 0.5 * S, y) for j, (x, y) in enumerate(pts)]
        pygame.draw.lines(s, rim, False, pts, max(1, S // 2))
    _ball(s, globe, x0, y0, gz, 4.4, 3.6, gloss=0.9)
    gx, gy = P(x0, y0, gz)
    pygame.draw.arc(s, rim, (gx - 4.4 * S, gy - 1.6 * S, 8.8 * S, 5.6 * S), math.pi * 1.04, math.pi * 1.96, max(1, S // 2))
    for k in (-2, 0, 2):                                           # the bell's ribs
        pygame.draw.line(s, _lerp(globe, rim, 0.5), (gx + k * 0.9 * S, gy - 3.2 * S), (gx + k * 1.6 * S, gy + 1.6 * S),
                         max(1, S // 4))
    pygame.draw.circle(s, (255, 255, 244), (gx - 1.4 * S, gy - 1.4 * S), S * 1.0)


def _statue_pic():
    """A stone Octo on a plinth, like the two in front of the Octo Temple (props3d.temple_statue)."""
    img, (ax, ay) = props3d.temple_statue().render()
    return img, (-int(ax), -int(ay))


BUILDERS = {'tree': _tree, 'palm': _palm, 'bush': _bush, 'hedge': lambda s, th, v: _bush(s, th, v, hedge=True),
            'cactus': _cactus, 'crystal': _crystals, 'ice': lambda s, th, v: _crystals(s, th, v, ice=True),
            'mushroom': _mushroom, 'shrooms': _shrooms, 'bones': _bones, 'spire': _spire, 'idol': _idol,
            'broken': _broken, 'lamp': _lamp}


def build(what, theme, v):
    """The picture of one thing: (image, (dx, dy) from its tile's top-left in full-resolution pixels)."""
    if what == 'statue':
        return _statue_pic()
    s = _canvas()
    BUILDERS[what](s, theme, v)
    return _finish(s)
