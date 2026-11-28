"""Kelp, coral and geysers that stand up off the sea floor, drawn smooth at full resolution.

The ground under kelp and coral is plain floor (world.Level._blit_tile asks style()), and the
3D pass (scene3d) draws each one over it, sorted with everything else, so Octo swims behind
them. Kelp sways in the swell; each coral is one of four kinds (branching, sea fan, brain coral,
tube sponges) in its tile's colour. Their pictures are made at twice full resolution and
smoothed down, a few milliseconds' worth per frame (or during the opening: warm()), and kept.
Geysers are drawn fresh every frame (draw_geyser): water gushing up out of a vent in the sea,
or clouds swirling far below a hole in a sky island. The other worlds' trees, palms, cacti,
crystals, mushrooms and the rest (and the temples' statues) are pictures made by decor3d, kept
here with the kelp and coral.
"""
import math
import random
import time

import pygame

import decor3d
import gfx
from settings import HI, TILE

MX, MY = 8, 14            # room round the tile in each picture: either side, and above it
KELP_FRAMES = 24          # pictures in one sway of the kelp
KELP_TICKS = 8            # game frames each one is shown
GROUND = 13.5             # where things stand in their tile (from its top)
DEFAULT_CORALS = ((250, 110, 96), (250, 160, 70), (210, 100, 220))    # (gfx.make_tiles)
_special = ('frost', 'vents', 'city', 'sky')                         # (gfx.make_themes: not coral)

_pics = {}                # what -> (image, (dx, dy)) from the tile's top-left, in full-resolution pixels
_styles = {}
_spent = [0.0, -1]        # (time spent building this frame, which frame)
BUDGET = 0.004


def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def coral_colours(theme):
    """The coral colours a theme's coral tiles come in, or None if its 'coral' is something else."""
    if theme in gfx.THEME_DECOR and gfx.THEME_DECOR[theme][0] != 'coral':
        return None
    if theme in _special:
        return None
    spec = gfx.THEME_SPECS.get(theme)
    if spec and spec[5]:
        return tuple(spec[5])
    return DEFAULT_CORALS


def style(level, tx, ty, ch, area_at):
    """How a tile stands up in 3D: ('kelp', variant), ('coral', colour, kind), ('geyser', sky) or
    ('decor', kind, theme, variant) for the other worlds' things (decor3d); None if it's flat."""
    key = (tx, ty, ch)
    s = _styles.get(key, 0)
    if s != 0:
        return s
    s = None
    a = area_at(tx, ty)
    theme = level.themes[ty][tx] if a not in ('dungeon', 'trial') else None
    n = tx * 7 + ty * 13 + tx * ty                       # (as world.Level._blit_tile picks a variant)
    d = decor3d.kind(theme, ch) if ch in 'CKS' else None
    if (tx, ty) in decor3d.props3d.FLAT:
        pass                                             # a 3D model stands here already (a nest, a statue)
    elif d:
        s = d + (decor3d.variant(d, tx, ty),)
    elif ch == 'Y':
        s = ('geyser', bool(theme) and 'Y' in gfx.TILES['themes'].get(theme, {}))     # (True: a sky island's hole)
    elif ch == 'K':
        if theme is None or 'K' not in gfx.TILES['themes'].get(theme, {}):
            s = ('kelp', n % 2)
    elif ch == 'C':
        cols = coral_colours(theme) if theme else DEFAULT_CORALS
        if cols:
            s = ('coral', cols[n % len(cols)], (tx * 5 + ty * 3 + (tx // 3) * 7) % 4)
    _styles[key] = s
    return s


# ---- drawing (at S = twice full resolution; coordinates in tile pixels) ------------------------
def _canvas():
    S = HI * 2
    return pygame.Surface(((TILE + 2 * MX) * S, (TILE + MY) * S), pygame.SRCALPHA), S


def _finish(s):
    """Smooth the picture down to full resolution and trim it to what's drawn (less to blit)."""
    w, h = s.get_size()
    img = pygame.transform.smoothscale(s, (w // 2, h // 2))
    box = img.get_bounding_rect()
    return img.subsurface(box).copy(), (box.x - MX * HI, box.y - MY * HI)


def _shadow(s, S, x, w, h=3.6):
    tmp = pygame.Surface((int(w * S), int(h * S)), pygame.SRCALPHA)
    pygame.draw.ellipse(tmp, (10, 20, 30, 70), tmp.get_rect())
    s.blit(tmp, ((MX + x - w / 2) * S, (MY + GROUND - h / 2 + 0.6) * S))


def _P(S, x, y):
    return ((MX + x) * S, (MY + y) * S)


# rim, stem, stem highlight, blade at the root, blade at the top, blade highlight, gas floats
KELP = ((14, 54, 30), (34, 108, 54), (128, 206, 110), (44, 138, 66), (108, 200, 94), (182, 238, 144), (214, 194, 92))


def _kelp(variant, frame):
    s, S = _canvas()
    rnd = random.Random(variant * 31 + 7)
    phase = frame / KELP_FRAMES * math.tau
    rim, stem, stem_hi, blade0, blade1, blade_hi, floatc = KELP
    ow = max(1, int(S * 0.5))                    # a dark rim, like the rest of the game's art
    fronds = [(3.6 + rnd.uniform(-0.6, 0.6), 16 + rnd.uniform(-2, 2)), (8.4 + rnd.uniform(-0.6, 0.6), 21 + rnd.uniform(-2, 1)),
              (12.8 + rnd.uniform(-0.6, 0.6), 15 + rnd.uniform(-2, 2))]
    _shadow(s, S, 8.2, 15)
    pygame.draw.ellipse(s, (70, 64, 36), (*_P(S, 4.2, GROUND - 1.4), 8.2 * S, 2.6 * S))      # the holdfast
    pygame.draw.ellipse(s, (104, 96, 52), (*_P(S, 5.2, GROUND - 1.2), 4.8 * S, 1.3 * S))
    for j, (x, h) in enumerate(fronds):
        ph = j * 1.9 + variant * 0.8
        n = 10
        pts = []
        for i in range(n + 1):
            f = i / n
            sway = math.sin(phase + ph - f * 1.8) * f ** 1.3 * 1.7
            pts.append((x + sway, GROUND - f * h))
        for i in range(2, n + 1, 2):             # blades on alternate sides, under the stem
            px, py = pts[i]
            f = i / n
            side = 0 if i == n else (1 if (i // 2 + j) % 2 else -1)
            length = 3.8 if i == n else 7.0 - 2.8 * f
            half = 0.8 if i == n else 1.2 - 0.35 * f
            drift = (px - pts[i - 1][0]) * 2.4
            a0 = -math.pi / 2 + side * (0.7 - 0.2 * f) + drift * 0.25
            a1 = a0 + side * 0.35 + drift * 0.5
            cx, cy = px + math.cos(a0) * length * 0.5, py + math.sin(a0) * length * 0.5
            tx, ty = cx + math.cos(a1) * length * 0.55, cy + math.sin(a1) * length * 0.55
            col = _lerp(blade0, blade1, f)
            a, b, m = [], [], []
            for u, w in ((0, 0.25), (0.25, 0.9), (0.5, 1.0), (0.75, 0.7), (1, 0)):
                v = 1 - u
                qx = v * v * px + 2 * v * u * cx + u * u * tx
                qy = v * v * py + 2 * v * u * cy + u * u * ty
                dx = 2 * v * (cx - px) + 2 * u * (tx - cx)
                dy = 2 * v * (cy - py) + 2 * u * (ty - cy)
                k = half * w / (math.hypot(dx, dy) or 1)
                a.append(_P(S, qx - dy * k, qy + dx * k))
                b.append(_P(S, qx + dy * k, qy - dx * k))
                m.append(_P(S, qx, qy))
            pygame.draw.lines(s, rim, True, a + b[-2::-1], ow)
            pygame.draw.polygon(s, col, a + b[-2::-1])
            lit = (b if side > 0 else a) + m[-2::-1]
            pygame.draw.polygon(s, _lerp(col, blade_hi, 0.45), lit)
            if side:
                fx, fy = px + math.cos(a0) * 0.8, py + math.sin(a0) * 0.8
                pygame.draw.circle(s, floatc, _P(S, fx, fy), 0.7 * S)
        left, right = [], []
        for i, (px, py) in enumerate(pts):
            ax, ay = pts[max(0, i - 1)]
            bx, by = pts[min(n, i + 1)]
            dx, dy = bx - ax, by - ay
            k = 0.8 * (1 - 0.5 * i / n) / (math.hypot(dx, dy) or 1)
            left.append(_P(S, px - dy * k, py + dx * k))
            right.append(_P(S, px + dy * k, py - dx * k))
        pygame.draw.lines(s, rim, True, left + right[::-1], ow)
        pygame.draw.polygon(s, stem, left + right[::-1])
        pygame.draw.lines(s, stem_hi, False, [_P(S, px - 0.3, py) for px, py in pts[1:-1]], max(1, S // 3))
    return _finish(s)


def _branchy(s, S, col, rnd):
    segs, tips = [], []

    def grow(x0, y0, a, ln, w, depth):
        x1, y1 = x0 + math.cos(a) * ln, y0 + math.sin(a) * ln
        segs.append((x0, y0, x1, y1, w))
        if depth <= 1:
            tips.append((x1, y1, w))
            return
        for da, k in (((-0.55, 0.74), (0.45, 0.7)) if depth % 2 else ((-0.4, 0.72), (0.55, 0.74))):
            grow(x1, y1, a + da + rnd.uniform(-0.12, 0.12), ln * k, w * 0.76, depth - 1)

    grow(8, GROUND, -math.pi / 2 + rnd.uniform(-0.12, 0.12), 5.2, 2.2, 4)
    dark, light = _lerp(col, (40, 12, 40), 0.5), _lerp(col, (255, 244, 236), 0.45)
    for c, dx, dy, k in ((dark, 0.4, 0.25, 1.3), (col, 0, 0, 1.0), (light, -0.28, -0.22, 0.4)):
        for x0, y0, x1, y1, w in segs:
            r = max(1.0, w * k * S / 2)
            a, b = _P(S, x0 + dx, y0 + dy), _P(S, x1 + dx, y1 + dy)
            pygame.draw.line(s, c, a, b, max(1, int(r * 2)))
            pygame.draw.circle(s, c, a, r)
            pygame.draw.circle(s, c, b, r)
    for x1, y1, w in tips:
        pygame.draw.circle(s, light, _P(S, x1, y1), max(1, w * 0.6 * S))
        pygame.draw.circle(s, (255, 252, 246), _P(S, x1 - 0.2, y1 - 0.25), max(1, w * 0.25 * S))


def _fan(s, S, col, rnd):
    lines, ends = [], {}

    def grow(x0, y0, a, ln, depth):
        x1, y1 = x0 + math.cos(a) * ln, y0 + math.sin(a) * ln
        lines.append((x0, y0, x1, y1, depth))
        ends.setdefault(depth, []).append((a, x1, y1))
        if depth:
            grow(x1, y1, a - 0.26 + rnd.uniform(-0.06, 0.06), ln * 0.82, depth - 1)
            grow(x1, y1, a + 0.26 + rnd.uniform(-0.06, 0.06), ln * 0.82, depth - 1)

    for a in (-2.25, -1.85, -1.45, -1.05):
        grow(8, GROUND, a, 3.6, 4)
    dark, light = _lerp(col, (60, 16, 20), 0.45), _lerp(col, (255, 236, 210), 0.4)
    for depth in (1, 2):
        row = sorted(ends.get(depth, []))
        for (_, x0, y0), (_, x1, y1) in zip(row, row[1:]):
            pygame.draw.line(s, _lerp(col, dark, 0.3), _P(S, x0, y0), _P(S, x1, y1), max(1, S // 4))
    for x0, y0, x1, y1, depth in lines:
        pygame.draw.line(s, dark, _P(S, x0 + 0.25, y0 + 0.2), _P(S, x1 + 0.25, y1 + 0.2), max(1, int(S * (0.35 + depth * 0.18))))
    for x0, y0, x1, y1, depth in lines:
        pygame.draw.line(s, col if depth else light, _P(S, x0, y0), _P(S, x1, y1), max(1, int(S * (0.25 + depth * 0.14))))
    pygame.draw.ellipse(s, _lerp(col, (50, 30, 20), 0.6), (*_P(S, 6.4, GROUND - 0.7), 3.2 * S, 1.4 * S))


def _brain(s, S, col, rnd):
    rw, rh = 13, 8
    body = pygame.Surface((rw * S, int(rh * 1.2 * S)), pygame.SRCALPHA)
    dome = (0, 0, rw * S, int(rh * 1.15 * S))
    pygame.draw.ellipse(body, _lerp(col, (60, 36, 20), 0.45) + (255,), dome)
    pygame.draw.ellipse(body, col + (255,), (int(0.8 * S), int(0.3 * S), int((rw - 2.2) * S), int(rh * 0.95 * S)))
    pygame.draw.ellipse(body, _lerp(col, (255, 246, 220), 0.35) + (255,), (int(2.2 * S), int(0.7 * S), int(rw * 0.5 * S), int(rh * 0.45 * S)))
    groove, ridge = _lerp(col, (70, 40, 20), 0.55) + (255,), _lerp(col, (255, 246, 220), 0.4) + (255,)
    for k in range(7):
        yy = 0.8 + k * 1.15
        pts = []
        for i in range(rw * 3 + 1):
            u = i / 3
            bend = ((u - rw / 2) / (rw / 2)) ** 2 * 1.1
            pts.append((u, yy + bend + 0.4 * math.sin(u * 1.2 + k * 0.55) + 0.13 * math.sin(u * 2.7 + k * 0.8)))
        pygame.draw.lines(body, ridge, False, [(u * S, (v - 0.32) * S) for u, v in pts], max(1, S // 4))
        pygame.draw.lines(body, groove, False, [(u * S, v * S) for u, v in pts], max(1, S // 3))
    mask = pygame.Surface(body.get_size(), pygame.SRCALPHA)
    pygame.draw.ellipse(mask, (255, 255, 255, 255), dome)
    body.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    s.blit(body, _P(S, 8 - rw / 2, GROUND - rh + 0.6))


def _tubes(s, S, col, rnd):
    dark, light = _lerp(col, (50, 16, 30), 0.5), _lerp(col, (255, 240, 230), 0.4)
    inside = _lerp(col, (20, 6, 14), 0.75)
    for x, h, r in sorted(((5.2, 8.5, 1.7), (9.6, 12.5, 1.9), (12.2, 6.5, 1.5), (7.4, 5.0, 1.3)), key=lambda t: t[1]):
        x += rnd.uniform(-0.3, 0.3)
        top = GROUND - h
        pygame.draw.rect(s, dark, (*_P(S, x - r, top), 2 * r * S, h * S))
        pygame.draw.rect(s, col, (*_P(S, x - r * 0.8, top), 1.4 * r * S, h * S))
        pygame.draw.rect(s, light, (*_P(S, x - r * 0.6, top + 0.4), 0.45 * r * S, (h - 0.8) * S))
        pygame.draw.ellipse(s, light, (*_P(S, x - r, top - 0.7), 2 * r * S, 1.4 * S))
        pygame.draw.ellipse(s, inside, (*_P(S, x - r * 0.7, top - 0.45), 1.4 * r * S, 0.9 * S))
        pygame.draw.ellipse(s, dark, (*_P(S, x - r, GROUND - 0.6), 2 * r * S, 1.2 * S))


def _coral(col, kind):
    s, S = _canvas()
    rnd = random.Random(hash(col) % 1000 + kind)
    _shadow(s, S, 8.4, 15 if kind == 2 else 13)
    (_branchy, _fan, _brain, _tubes)[kind](s, S, col, rnd)
    return _finish(s)


def picture(st, t=0, tx=0, ty=0, build=True):
    """The picture for a style ((image, offset) or None if it isn't built yet and there's no time)."""
    if st[0] == 'kelp':
        frame = (t // KELP_TICKS + tx * 5 + ty * 3) % KELP_FRAMES
        key = ('kelp', st[1], frame)
    else:
        key = st
    pic = _pics.get(key)
    if pic is None and build:
        now = time.perf_counter()
        if _spent[0] < BUDGET:
            pic = _pics[key] = _make(key)
            _spent[0] += time.perf_counter() - now
        elif st[0] == 'kelp':                    # out of time: the nearest sway picture already made
            for d in range(1, KELP_FRAMES):
                pic = _pics.get(('kelp', st[1], (key[2] + d) % KELP_FRAMES))
                if pic:
                    break
    return pic


def _make(key):
    if key[0] == 'kelp':
        return _kelp(key[1], key[2])
    if key[0] == 'decor':
        return decor3d.build(*key[1:])
    return _coral(key[1], key[2])


def new_frame():
    _spent[0] = 0.0


def warm():
    """Make the kelp and the reef's corals a piece at a time (Game.warm_up runs this)."""
    for v in range(2):
        for f in range(KELP_FRAMES):
            if ('kelp', v, f) not in _pics:
                _pics[('kelp', v, f)] = _kelp(v, f)
                yield
    for col in DEFAULT_CORALS:
        for kind in range(4):
            if ('coral', col, kind) not in _pics:
                _pics[('coral', col, kind)] = _coral(col, kind)
                yield


def warm_decor():
    """Make every other world's trees, palms, crystals and the rest, one picture at a time."""
    for what in decor3d.every():
        key = ('decor',) + what
        if key not in _pics:
            _pics[key] = decor3d.build(*what)
            yield


# ---- geysers, drawn fresh every frame --------------------------------------------------------
_gs = []


def _scratch(w, h):
    """A see-through sheet to draw a geyser on (so its parts blend), reused frame to frame."""
    if not _gs or _gs[0].get_size() != (w * HI, h * HI):
        _gs[:] = [pygame.Surface((w * HI, h * HI), pygame.SRCALPHA)]
    _gs[0].fill((0, 0, 0, 0))
    return _gs[0]


def draw_geyser(hr, x, y, t, sky):
    """A geyser at (x, y), the full-resolution point at the middle of its tile (on the ground).
    In the sea: water gushes up out of a stone vent and froths at the top, bubbles stream up it,
    spray falls back and rings ripple out over the sand. On a sky island: a hole, with clouds
    swirling round far below and wisps of mist drifting up out of it."""
    if sky:
        _sky_hole(hr, x, y, t)
        return
    W, H, vx, vy = 34, 62, 17, 54                 # the sheet, and where the vent is on it
    s = _scratch(W, H)

    def P(px, py):
        return (px * HI, py * HI)

    for k in range(3):                            # rings rippling out over the sand
        r = (t * 0.32 + k * 9) % 27
        a = int(130 * (1 - r / 27))
        if r > 5:
            pygame.draw.ellipse(s, (210, 245, 255, a), (*P(vx - r * 0.6, vy - r * 0.26), r * 1.2 * HI, r * 0.52 * HI),
                                max(1, HI // 2 + 1))
    pygame.draw.ellipse(s, (60, 70, 90, 255), (*P(vx - 7.5, vy - 4), 15 * HI, 8 * HI))           # the vent
    pygame.draw.ellipse(s, (96, 108, 130, 255), (*P(vx - 7.5, vy - 4), 15 * HI, 6 * HI))
    pygame.draw.ellipse(s, (30, 46, 66, 255), (*P(vx - 5.2, vy - 3), 10.4 * HI, 4.6 * HI))
    shimmer = 0.5 + 0.5 * math.sin(t * 0.2)
    pygame.draw.ellipse(s, (100 + int(40 * shimmer), 196, 240, 255), (*P(vx - 4.2, vy - 2.6), 8.4 * HI, 3.4 * HI))
    pulse = 0.5 + 0.5 * math.sin(t * 0.09)
    jet = 30 + 12 * pulse                         # how high the water gushes
    layers = ([], [], [])                         # a soft glow, the water, its bright core
    for j in range(13):
        f = j / 12
        yy = vy - 2 - jet * f
        w = 3.2 + 2.2 * f + 0.5 * math.sin(t * 0.33 + j * 1.3)
        cx = vx + 0.8 * math.sin(t * 0.17 + j * 0.9) * f
        for pts, k in zip(layers, (1.45, 1.0, 0.45)):
            pts.append((P(cx - w * k, yy), P(cx + w * k, yy)))
    for pts, col in zip(layers, ((120, 200, 255, 60), (80, 168, 236, 170), (236, 250, 255, 215))):
        pygame.draw.polygon(s, col, [a for a, _ in pts] + [b for _, b in pts][::-1])
    for pts in (layers[1],):                      # light catching the water's edges
        pygame.draw.lines(s, (196, 236, 255, 200), False, [a for a, _ in pts], max(1, HI // 2))
    top = vy - 2 - jet
    for i in range(7):                            # the froth on top
        a = i / 7 * math.tau + t * 0.05
        fx, fy = vx + math.cos(a) * (2.6 + pulse), top + math.sin(a) * 1.4 + 0.5
        pygame.draw.circle(s, (246, 252, 255, 220), P(fx, fy), (1.3 + 0.6 * math.sin(t * 0.2 + i)) * HI)
    for i in range(10):                           # spray falling back
        f = (t * 0.025 + i * 0.1) % 1
        side = 1 if i % 2 else -1
        dx = side * (1.5 + 10 * f) * (0.7 + 0.3 * ((i * 7) % 3))
        dy = -6 * f + 26 * f * f
        if top + dy < vy - 2:
            pygame.draw.circle(s, (220, 244, 255, int(220 * (1 - f))), P(vx + dx, top + dy), max(1, 0.55 * HI))
    for i in range(12):                           # bubbles streaming up
        f = (t * 0.011 + i * 0.083) % 1
        bx = vx + math.sin(t * 0.08 + i * 2.1) * (2.2 + f * 2.5)
        by = vy - 3 - f * (jet + 4)
        r = (0.7 + (i % 3) * 0.35) * HI
        a = int(255 * (1 - f) ** 0.5)
        pygame.draw.circle(s, (255, 255, 255, a), P(bx, by), r, max(1, HI // 2))
        pygame.draw.circle(s, (255, 255, 255, a), P(bx - 0.3, by - 0.3), max(1, r * 0.3))
    hr.blit(s, (x - vx * HI, y - vy * HI))


def _sky_hole(hr, x, y, t):
    W, H, cx, cy = 30, 40, 15, 33
    s = _scratch(W, H)

    def P(px, py):
        return (px * HI, py * HI)

    pygame.draw.ellipse(s, (70, 48, 26, 255), (*P(cx - 8, cy - 5.2), 16 * HI, 10.4 * HI))       # the rim
    pygame.draw.ellipse(s, (40, 26, 14, 255), (*P(cx - 7, cy - 4.2), 14 * HI, 8.6 * HI))
    pygame.draw.ellipse(s, (84, 150, 220, 255), (*P(cx - 6.2, cy - 3.4), 12.4 * HI, 7.2 * HI))    # far below
    pygame.draw.ellipse(s, (44, 104, 190, 255), (*P(cx - 3.4, cy - 1.8), 6.8 * HI, 3.8 * HI))
    for k in range(5):                            # clouds swirling round the hole
        a = t * 0.035 + k * math.tau / 5
        rx, ry = 4.6 - (k % 2) * 1.4, 2.6 - (k % 2) * 0.8
        pygame.draw.arc(s, (250, 252, 255, 230), (*P(cx - rx, cy - ry), 2 * rx * HI, 2 * ry * HI), a, a + 1.4,
                        max(1, int(HI * 0.9)))
    for i in range(5):                            # mist drifting up out of it
        f = (t * 0.007 + i * 0.2) % 1
        mx = cx + math.sin(f * 6 + i * 1.7) * 3
        my = cy - 2 - f * 26
        pygame.draw.circle(s, (255, 255, 255, int(120 * (1 - f) * min(1, f * 6))), P(mx, my), (1.4 + f * 3) * HI)
    hr.blit(s, (x - cx * HI, y - cy * HI))
