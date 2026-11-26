"""All pixel art is generated in code so there are no external image assets.

Call gfx.load() once after the display is created; afterwards the module-level
dicts (OCTO, TILES, SPR, ...) hold ready-to-blit surfaces.
"""
import math
import random

import pygame

from settings import TILE

# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def from_strings(rows, pal):
    w = max(len(r) for r in rows)
    s = pygame.Surface((w, len(rows)), pygame.SRCALPHA)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            c = pal.get(ch)
            if c:
                s.set_at((x, y), c)
    return s


_flash_cache = {}


def flash(img):
    """White-ish silhouette used for hurt flashes."""
    k = id(img)
    hit = _flash_cache.get(k)
    if hit is None or hit[0] is not img:
        f = img.copy()
        f.fill((190, 190, 190, 0), special_flags=pygame.BLEND_RGBA_ADD)
        hit = (img, f)
        _flash_cache[k] = hit
    return hit[1]


_flip_cache = {}


def flipped(img):
    k = id(img)
    hit = _flip_cache.get(k)
    if hit is None or hit[0] is not img:
        hit = (img, pygame.transform.flip(img, True, False))
        _flip_cache[k] = hit
    return hit[1]


_icy_cache = {}


def icy(img):
    """Frozen-solid look for an enemy caught by Chilly Octo's ice."""
    key = id(img)
    if key not in _icy_cache:
        f = img.copy()
        f.fill((120, 200, 255, 255), special_flags=pygame.BLEND_RGBA_MULT)
        f.fill((70, 90, 110, 0), special_flags=pygame.BLEND_RGBA_ADD)
        _icy_cache[key] = (img, f)
    return _icy_cache[key][1]


def tint(img, color):
    f = img.copy()
    f.fill(color + (255,), special_flags=pygame.BLEND_RGBA_MULT)
    return f


# --------------------------------------------------------------------------
# Octo (the reversible plush!)
# --------------------------------------------------------------------------

OCTO_PAL = {
    'blue': {'k': (14, 22, 60), 'B': (46, 98, 216), 'H': (124, 174, 255),
             'D': (28, 60, 150), 'P': (238, 56, 150), 'e': (8, 8, 20),
             'w': (255, 255, 255), 'c': (238, 110, 170)},
    'mad': {'k': (0, 0, 0), 'B': (40, 40, 48), 'H': (92, 92, 110),
            'D': (22, 22, 28), 'P': (46, 98, 216), 'e': (235, 40, 40),
            'w': (255, 255, 255), 'c': (60, 60, 70), 'm': (170, 170, 185)},
    'zap': {'k': (70, 48, 0), 'B': (250, 204, 40), 'H': (255, 246, 160),
            'D': (206, 140, 10), 'P': (70, 160, 255), 'e': (20, 16, 0),
            'w': (255, 255, 255), 'c': (255, 140, 70)},
    'ice': {'k': (30, 70, 116), 'B': (184, 228, 255), 'H': (255, 255, 255),
            'D': (116, 176, 230), 'P': (70, 130, 230), 'e': (16, 40, 86),
            'w': (255, 255, 255), 'c': (140, 196, 255)},
    'ghost': {'k': (40, 10, 70), 'B': (150, 100, 222), 'H': (214, 186, 255),
              'D': (98, 58, 170), 'P': (240, 224, 255), 'e': (24, 0, 44),
              'w': (255, 255, 255), 'c': (196, 140, 255)},
    'bubble': {'k': (110, 20, 70), 'B': (255, 150, 200), 'H': (255, 220, 240),
               'D': (220, 90, 150), 'P': (120, 220, 255), 'e': (60, 0, 30),
               'w': (255, 255, 255), 'c': (255, 90, 140)},
    'spiky': {'k': (90, 30, 0), 'B': (250, 130, 40), 'H': (255, 200, 120),
              'D': (200, 80, 20), 'P': (255, 240, 120), 'e': (40, 10, 0),
              'w': (255, 255, 255), 'c': (230, 60, 40), 'm': (255, 230, 170)},
    'glow': {'k': (0, 60, 40), 'B': (80, 230, 150), 'H': (200, 255, 220),
             'D': (40, 170, 110), 'P': (240, 255, 140), 'e': (0, 40, 20),
             'w': (255, 255, 255), 'c': (160, 255, 120)},
}
OCTO_PAL['air'] = {'k': (50, 66, 96), 'B': (226, 236, 248), 'H': (255, 255, 255),
                   'D': (170, 190, 215), 'P': (150, 220, 255), 'e': (16, 24, 56),
                   'w': (255, 255, 255), 'c': (180, 210, 240)}
def _pal(k, B, H, D, P, e, c, m=None):
    p = {'k': k, 'B': B, 'H': H, 'D': D, 'P': P, 'e': e, 'w': (255, 255, 255), 'c': c}
    if m:
        p['m'] = m
    return p


# fused forms
OCTO_PAL.update({
    'stormy': _pal((20, 40, 90), (110, 170, 240), (220, 240, 255), (70, 110, 200), (255, 240, 120),
                   (10, 20, 60), (180, 230, 255)),
    'whippy': _pal((10, 6, 40), (80, 60, 190), (150, 140, 240), (50, 36, 130), (30, 220, 220),
                   (0, 0, 20), (150, 110, 255)),
    'prickly': _pal((100, 30, 30), (250, 120, 110), (255, 200, 180), (200, 70, 70), (255, 240, 140),
                    (60, 0, 0), (255, 90, 140), (255, 230, 170)),
    'quaky': _pal((50, 30, 10), (160, 110, 60), (220, 180, 120), (110, 70, 30), (250, 170, 60),
                  (30, 10, 0), (200, 90, 50), (240, 210, 160)),
    'wispy': _pal((20, 60, 50), (150, 240, 200), (230, 255, 240), (90, 190, 150), (255, 250, 180),
                  (10, 40, 30), (200, 255, 220)),
    'breezy': _pal((20, 70, 80), (120, 220, 220), (220, 255, 255), (70, 170, 180), (250, 250, 255),
                   (10, 40, 50), (160, 240, 240)),
    'frosty': _pal((40, 70, 110), (190, 225, 255), (250, 255, 255), (130, 180, 230), (255, 160, 220),
                   (20, 40, 80), (170, 220, 255)),
    'sparky': _pal((90, 70, 0), (250, 230, 70), (255, 255, 190), (210, 170, 20), (120, 200, 255),
                   (60, 40, 0), (255, 180, 60)),
})

# the newer base forms the temple altar teaches
OCTO_PAL.update({
    'magnet': _pal((60, 10, 20), (220, 60, 60), (255, 150, 150), (160, 30, 40), (205, 205, 215),
                   (30, 0, 0), (240, 240, 255), (255, 200, 200)),
    'clammy': _pal((90, 50, 40), (230, 170, 140), (255, 222, 204), (180, 110, 90), (255, 244, 224),
                   (50, 20, 10), (255, 140, 150)),
    'starry': _pal((10, 10, 40), (44, 44, 124), (96, 96, 196), (22, 22, 84), (255, 220, 90),
                   (255, 236, 150), (255, 220, 90)),
    'wobbly': _pal((90, 30, 110), (230, 140, 240), (255, 212, 255), (180, 90, 200), (140, 240, 255),
                   (60, 0, 70), (255, 120, 220)),
    'stony': _pal((50, 48, 44), (140, 135, 125), (190, 185, 175), (100, 96, 90), (220, 200, 140),
                  (20, 20, 20), (170, 160, 150), (200, 195, 185)),
})


class _FusedPalettes(dict):
    """Fused forms are coloured on demand: a blend of both parents with the element as an accent."""

    def __missing__(self, mood):
        import forms
        f = forms.FUSIONS.get(mood)
        if not f:
            raise KeyError(mood)
        pa, pb = self[f['parents'][0]], self[f['parents'][1]]
        accent = forms.ELEMENTS[f['element']][2]
        pal = {}
        for k in set(pa) | set(pb):
            ca, cb = pa.get(k, pb.get(k)), pb.get(k, pa.get(k))
            pal[k] = tuple((x * 3 + y * 2) // 5 for x, y in zip(ca, cb))
        pal['P'] = accent                       # the element shows in the tentacle tips
        pal['c'] = tuple((x + y) // 2 for x, y in zip(pal.get('c', accent), accent))
        pal['w'] = (255, 255, 255)
        self[mood] = pal
        return pal


OCTO_PAL = _FusedPalettes(OCTO_PAL)
import forms as _forms   # noqa: E402  (names for every form, fused ones included)
MOOD_NAMES = _forms.NAMES

OCTO_BODY = [
    "................",
    ".....kkkkkk.....",
    "...kkHHHBBBkk...",
    "..kHHHBBBBBBBk..",
    ".kHHBBBBBBBBBBk.",
    ".kHBBBBBBBBBBBk.",
    "kHBBBBBBBBBBBBBk",
    "kBBBBBBBBBBBBBBk",
    "kBBBBBBBBBBBBBBk",
    "kDBBBBBBBBBBBBDk",
    ".kDBBBBBBBBBBDk.",
]
OCTO_LEGS = [
    [   # frame A - tentacles spread
        "kBBkBBBBBBBBkBBk",
        "kBPkkBBkkBBkkPBk",
        ".kk.kPBkkBPk.kk.",
        "....kkk..kkk....",
        "................",
    ],
    [   # frame B - tentacles curl
        ".kBBkBBBBBBkBBk.",
        "kBPk.kBBBBk.kPBk",
        "kBk.kPBkkBPk.kBk",
        ".k..kkk..kkk..k.",
        "................",
    ],
]


def _octo_face(rows, mood, facing):
    if facing == 'up':
        # back of the head: a little extra highlight
        rows[3][6] = 'H'
        rows[4][5] = 'H'
        return
    shift = {'down': 0, 'left': -2, 'right': 2}[facing]
    eyes = [4 + shift, 10 + shift]
    if mood == 'ghost':
        # hollow white eyes and a little 'o' mouth
        for x0 in eyes:
            for yy in (6, 7):
                rows[yy][x0] = 'w'
                rows[yy][x0 + 1] = 'w'
        mx = 7 + shift
        rows[9][mx] = 'k'
        rows[9][mx + 1] = 'k'
        rows[10][mx] = 'k'
        rows[10][mx + 1] = 'k'
        return
    if '+' in mood:                 # fused: wear a parent's face
        a, b = mood.split('+')
        mood = 'mad' if {'mad', 'spiky', 'stony'} & {a, b} else 'ghost' if 'ghost' in (a, b) else 'blue'
        if mood == 'ghost':
            return _octo_face(rows, 'ghost', facing)
    if mood in ('spiky', 'prickly', 'quaky', 'stony', 'magnet'):
        mood = 'mad'
    for i, x0 in enumerate(eyes):
        if mood != 'mad':
            rows[6][x0] = 'w'
            rows[6][x0 + 1] = 'e'
            rows[7][x0] = 'e'
            rows[7][x0 + 1] = 'e'
            # blush
            cx = x0 - 1 if i == 0 else x0 + 2
            if 1 <= cx <= 14:
                rows[8][cx] = 'c'
        else:
            # grumpy half-lidded eyes + inward brows
            rows[6][x0] = 'm'
            rows[6][x0 + 1] = 'm'
            rows[7][x0] = 'e'
            rows[7][x0 + 1] = 'e'
            bx = x0 + 1 if i == 0 else x0
            rows[5][bx] = 'm'
    mx = 7 + shift
    if mood != 'mad':
        rows[9][mx] = 'k'
        rows[9][mx + 1] = 'k'
        rows[8][mx - 1] = 'k'
        rows[8][mx + 2] = 'k'
    else:
        rows[8][mx] = 'm'
        rows[8][mx + 1] = 'm'
        rows[9][mx - 1] = 'm'
        rows[9][mx + 2] = 'm'


def _octo_frames(mood):
    out = {}
    for facing in ('down', 'up', 'left', 'right'):
        frames = []
        for legs in OCTO_LEGS:
            rows = [list(r) for r in OCTO_BODY + legs]
            _octo_face(rows, mood, facing)
            frames.append(from_strings([''.join(r) for r in rows], OCTO_PAL[mood]))
        out[facing] = frames
    return out


class _LazyOcto(dict):
    """Octo's sprites per form, drawn the first time a form is needed."""

    def __missing__(self, mood):
        self[mood] = _octo_frames(mood)
        return self[mood]


def make_octo():
    out = _LazyOcto()
    for mood in ('blue', 'mad'):
        out[mood] = _octo_frames(mood)
    return out


def make_slap():
    """A slapping tentacle pointing right; rotated for other directions."""
    out = {}
    for mood in ('blue', 'mad'):
        pal = OCTO_PAL[mood]
        rows = [
            "kkkkkkkkkkk....",
            "BBBBBBBBBBBkk..",
            "BBBBBBBBBBBBBk.",
            "PwPPwPPwPPwPPPk",
            "kkkkkkkkkkkkkk.",
        ]
        img = from_strings(rows, pal)
        out[mood] = {
            'right': img,
            'left': pygame.transform.flip(img, True, False),
            'up': pygame.transform.rotate(img, 90),
            'down': pygame.transform.rotate(img, -90),
        }
    return out


# --------------------------------------------------------------------------
# Enemies, NPCs, items
# --------------------------------------------------------------------------

CRAB_PAL = {'k': (60, 10, 10), 'R': (228, 72, 52), 'D': (160, 40, 30),
            'w': (255, 255, 255), 'e': (0, 0, 0)}

CRAB_A = [
    "................",
    ".kk..........kk.",
    "kRRk........kRRk",
    "kR.Rk......kR.Rk",
    "kRRRk......kRRRk",
    ".kRk..kkkk..kRk.",
    "..kRkkRRRRkkRk..",
    "..kkRRRRRRRRkk..",
    ".kRRwekRRkweRRk.",
    ".kRRRRRRRRRRRRk.",
    "kRRRRRRRRRRRRRRk",
    "kDRRRRRRRRRRRRDk",
    ".kDDDDDDDDDDDDk.",
    "..kkkkkkkkkkkk..",
    ".k.k.k....k.k.k.",
    "k.k.k......k.k.k",
]
CRAB_B = [
    "................",
    "................",
    ".kk..........kk.",
    "kRRk........kRRk",
    "kRRRk......kRRRk",
    ".kRRk.kkkk.kRRk.",
    "..kRkkRRRRkkRk..",
    "..kkRRRRRRRRkk..",
    ".kRRwekRRkweRRk.",
    ".kRRRRRRRRRRRRk.",
    "kRRRRRRRRRRRRRRk",
    "kDRRRRRRRRRRRRDk",
    ".kDDDDDDDDDDDDk.",
    "..kkkkkkkkkkkk..",
    "..k.k.k..k.k.k..",
    "..k.k.k..k.k.k..",
]


def make_crab(pal):
    return [from_strings(CRAB_A, pal), from_strings(CRAB_B, pal)]


def make_shark():
    """Grimfin the Shark, side view facing right (48x28). Flip for left."""
    out = {'swim': [], 'bite': []}
    ink, body, light, belly = (24, 32, 52), (104, 124, 156), (150, 170, 200), (226, 230, 240)
    for mode in ('swim', 'bite'):
        for f in range(2):
            s = pygame.Surface((48, 28), pygame.SRCALPHA)
            tip = 3 if f == 0 else 6
            # tail (two lobes) and its stem
            tail = [(11, 14), (1, tip), (5, 14), (1, 27 - tip), (11, 16)]
            pygame.draw.polygon(s, body, tail)
            pygame.draw.polygon(s, ink, tail, 1)
            # dorsal and pectoral fins
            dorsal = [(20, 9), (27, 1), (30, 9)]
            pygame.draw.polygon(s, body, dorsal)
            pygame.draw.polygon(s, ink, dorsal, 1)
            # body
            pygame.draw.ellipse(s, ink, (7, 7, 40, 17))
            pygame.draw.ellipse(s, body, (8, 8, 38, 15))
            pygame.draw.ellipse(s, belly, (14, 15, 30, 8))
            pygame.draw.line(s, light, (16, 9), (36, 9))
            pec = [(24, 19), (21, 26), (29, 20)]
            pygame.draw.polygon(s, body, pec)
            pygame.draw.polygon(s, ink, pec, 1)
            # gills
            for gx in (30, 32, 34):
                pygame.draw.line(s, ink, (gx, 12), (gx - 1, 16))
            # eye + angry brow
            s.set_at((39, 12), (0, 0, 0))
            s.set_at((40, 12), (0, 0, 0))
            s.set_at((39, 11), (255, 255, 255))
            pygame.draw.line(s, ink, (37, 9), (41, 11))
            # mouth
            if mode == 'swim':
                pygame.draw.line(s, ink, (36, 18), (44, 17))
                for tx in (38, 41):
                    s.set_at((tx, 18), (255, 255, 255))
            else:
                gape = 4 if f == 0 else 6
                jaw = [(33, 17), (47, 15 - gape // 2), (47, 17 + gape)]
                pygame.draw.polygon(s, (90, 10, 30), jaw)
                for i in range(4):
                    x = 36 + i * 3
                    pygame.draw.polygon(s, (255, 255, 255), [(x, 16), (x + 2, 16), (x + 1, 18)])
                    pygame.draw.polygon(s, (255, 255, 255), [(x, 19 + gape // 2), (x + 2, 19 + gape // 2),
                                                              (x + 1, 17 + gape // 2)])
            out[mode].append(s)
    return out


def make_urchin():
    frames = []
    for f in range(2):
        s = pygame.Surface((16, 16), pygame.SRCALPHA)
        cx, cy = 8, 9
        for i in range(12):
            a = math.radians(i * 30 + f * 15)
            ex, ey = cx + math.cos(a) * 7.5, cy + math.sin(a) * 6.8
            pygame.draw.line(s, (120, 70, 170), (cx, cy), (ex, ey))
            ix, iy = int(round(ex)), int(round(ey))
            if 0 <= ix < 16 and 0 <= iy < 16:
                s.set_at((ix, iy), (220, 180, 250))
        pygame.draw.circle(s, (40, 16, 64), (cx, cy), 5)
        pygame.draw.circle(s, (78, 40, 116), (cx, cy), 4)
        s.set_at((cx - 2, cy - 2), (150, 110, 200))
        for ex in (cx - 2, cx + 1):
            s.set_at((ex, cy), (255, 255, 255))
            s.set_at((ex + 1, cy), (255, 255, 255))
            s.set_at((ex + (1 if f else 0), cy), (0, 0, 0))
        frames.append(s)
    return frames


def make_jelly():
    frames = []
    for f in range(2):
        s = pygame.Surface((16, 16), pygame.SRCALPHA)
        body, edge, light = (150, 226, 255, 200), (60, 140, 210, 230), (230, 250, 255, 230)
        # tentacles
        for i, tx in enumerate((4, 7, 9, 12)):
            for ty in range(9, 16):
                wob = int(round(math.sin((ty + f * 2 + i) * 0.9)))
                if ty < 15 or i % 2 == f:
                    s.set_at((tx + wob, ty), (180, 120, 230, 210))
        h = 8 if f == 0 else 9
        pygame.draw.ellipse(s, body, (2, 10 - h, 12, h + 1 + 2))
        pygame.draw.ellipse(s, edge, (2, 10 - h, 12, h + 1 + 2), 1)
        pygame.draw.line(s, edge, (3, 10), (12, 10))
        s.set_at((5, 4), light)
        s.set_at((6, 3), light)
        s.set_at((6, 7), (20, 20, 40))
        s.set_at((9, 7), (20, 20, 40))
        frames.append(s)
    return frames


def make_puffer():
    out = []
    yel, dk, lt = (250, 208, 60), (140, 96, 16), (255, 240, 150)
    for f in range(2):   # normal swim frames
        s = pygame.Surface((16, 16), pygame.SRCALPHA)
        tail = [(1, 6 + f), (4, 9), (1, 12 - f)]
        pygame.draw.polygon(s, (230, 150, 40), tail)
        pygame.draw.ellipse(s, yel, (3, 4, 11, 10))
        pygame.draw.ellipse(s, dk, (3, 4, 11, 10), 1)
        s.set_at((10, 7), (0, 0, 0))
        s.set_at((11, 7), (255, 255, 255))
        s.set_at((13, 10), dk)
        s.set_at((6, 6), lt)
        s.set_at((7, 11), dk)
        s.set_at((9, 12), dk)
        out.append(s)
    s = pygame.Surface((16, 16), pygame.SRCALPHA)   # inflated
    for i in range(10):
        a = math.radians(i * 36)
        pygame.draw.line(s, dk, (8, 8), (8 + math.cos(a) * 7.5, 8 + math.sin(a) * 7.5))
    pygame.draw.circle(s, yel, (8, 8), 6)
    pygame.draw.circle(s, dk, (8, 8), 6, 1)
    s.set_at((10, 6), (0, 0, 0))
    s.set_at((6, 6), (0, 0, 0))
    s.set_at((6, 5), lt)
    pygame.draw.line(s, dk, (7, 10), (9, 10))
    out.append(s)
    return out


def make_turtle():
    pal = {'k': (20, 50, 30), 'G': (70, 160, 90), 'g': (40, 110, 60), 'L': (130, 210, 130),
           'S': (210, 196, 130), 's': (160, 140, 80), 'e': (0, 0, 0), 'w': (255, 255, 255)}
    rows = [
        "................",
        "......kkkk......",
        ".....kSSSSk.....",
        ".....kSewSk.....",
        ".....kSSSSk.....",
        "..kk..kssk..kk..",
        ".kSSkkkkkkkkSSk.",
        "..kkkGLGGgGGkk..",
        "...kGLGgGGgGGk..",
        "...kGGgGGgGGGk..",
        "...kGgGGgGGgGk..",
        "...kGGGgGGgGGk..",
        "..kkkGGGGGGGkkk.",
        ".kSSkkkkkkkkkSSk",
        "..kk.........kk.",
        "................",
    ]
    a = from_strings(rows, pal)
    rows2 = list(rows)
    rows2[3] = ".....kSSSSk....."   # blink
    b = from_strings(rows2, pal)
    return [a, b]


HEART_ROWS = [
    ".kk.kk.",
    "kRRkRRk",
    "kRRRRRk",
    "kRRRRRk",
    ".kRRRk.",
    "..kRk..",
    "...k...",
]


def make_hearts():
    full = from_strings(HEART_ROWS, {'k': (0, 0, 0), 'R': (232, 36, 60)})
    empty = from_strings(HEART_ROWS, {'k': (0, 0, 0), 'R': (60, 60, 80)})
    half = empty.copy()
    half.blit(full, (0, 0), (0, 0, 4, 7))
    big = pygame.Surface((16, 16), pygame.SRCALPHA)
    hb = pygame.transform.scale(full, (14, 14))
    big.blit(hb, (1, 1))
    pygame.draw.line(big, (255, 200, 210), (4, 4), (5, 3))
    container = big.copy()
    pygame.draw.rect(container, (255, 230, 120), (0, 0, 16, 16), 1)
    return {'full': full, 'half': half, 'empty': empty, 'pickup': full, 'container': container}


def make_pearl(color, light, size=8):
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    r = size // 2
    pygame.draw.circle(s, (40, 40, 60), (r, r), r)
    pygame.draw.circle(s, color, (r, r), r - 1)
    s.set_at((r - 2, r - 2), light)
    s.set_at((r - 1, r - 2), light)
    s.set_at((r - 2, r - 1), light)
    return s


def make_shrimp():
    pal = {'k': (110, 30, 20), 'O': (255, 128, 90), 'l': (255, 196, 160), 'e': (0, 0, 0),
           'a': (255, 170, 130)}
    rows = [
        "a.a.........",
        ".a.a.kkkk...",
        "..kkkOOOOkk.",
        ".kOOOlOlOOOk",
        "kOeOOOOOOOOk",
        "kOOOOOOOOOk.",
        ".kkOkOkOkkOk",
        "...k.k.k.kOk",
        ".........kk.",
    ]
    return from_strings(rows, pal)


def make_golden():
    s = pygame.Surface((16, 16), pygame.SRCALPHA)
    pygame.draw.circle(s, (120, 80, 0), (8, 8), 7)
    pygame.draw.circle(s, (250, 200, 40), (8, 8), 6)
    pygame.draw.circle(s, (255, 230, 120), (7, 7), 4)
    pygame.draw.circle(s, (255, 250, 220), (6, 6), 2)
    return s


def make_bell():
    """A Tide Bell: a little bronze bell with a pearl clapper."""
    pal = {'k': (70, 40, 10), 'Y': (240, 190, 70), 'y': (190, 130, 40), 'w': (255, 245, 200), 'p': (230, 240, 255)}
    rows = [
        "......kk......",
        ".....kYYk.....",
        "....kkYYkk....",
        "...kYwYYyyk...",
        "...kYwYYyyk...",
        "..kYwYYYYyyk..",
        "..kYwYYYYyyk..",
        "..kYwYYYYyyk..",
        ".kYwYYYYYYyyk.",
        ".kYYYYYYYYyyk.",
        "kYYYYYYYYYYyyk",
        "kkkkkkkkkkkkkk",
        ".....kppk.....",
        "......kk......",
    ]
    return from_strings(rows, pal)


def _sealed(rnd):
    """The bell seal on the Murk Palace door: a purple door with seven gold studs."""
    s = _locked(rnd).copy()
    s = tint(s, (170, 110, 230))
    for i in range(7):
        s.set_at((2 + i * 2 % 12, 3 + (i % 2) * 8), (255, 220, 90))
    return s


def make_key():
    pal = {'k': (60, 40, 0), 'Y': (250, 206, 50), 'y': (190, 140, 20)}
    rows = [
        "..kkk..",
        ".kYYYk.",
        "kYk.kYk",
        "kYk.kYk",
        ".kYYYk.",
        "..kYk..",
        "..kYk..",
        "..kYk..",
        "..kYkk.",
        "..kYYYk",
        "..kYkk.",
        "..kYYYk",
        "..kykk.",
        "...k...",
    ]
    return from_strings(rows, pal)


def make_hermit():
    """Hermie the hermit crab shopkeeper: red claws poking out of a spiral shell."""
    pal = {'k': (40, 20, 10), 'S': (236, 206, 160), 's': (190, 150, 100), 'p': (250, 180, 190),
           'R': (228, 72, 52), 'D': (160, 40, 30), 'e': (0, 0, 0), 'w': (255, 255, 255)}
    rows = [
        "................",
        "......kkkk......",
        "....kkSSSSkk....",
        "...kSSsssSSSk...",
        "..kSSsSSSsSSSk..",
        "..kSsSkkSSsSSk..",
        "..kSsSkSsSsSSk..",
        "..kSSsSSsSSSpk..",
        "..kkSSssSSSppk..",
        ".kRkkkkkkkkkkRk.",
        "kRRRkwekkwekRRRk",
        "kRDRkRRRRRRkRDRk",
        ".kk.kRRRRRRk.kk.",
        "....kRkRRkRk....",
        "....k.k..k.k....",
        "................",
    ]
    a = from_strings(rows, pal)
    rows2 = list(rows)
    rows2[10] = "kRRRkkkkkkkkRRRk"   # blink
    return [a, from_strings(rows2, pal)]


def make_items():
    """Shop wares and inventory icons."""
    out = {}
    # Swift Fins: a pair of teal flippers
    pal = {'k': (10, 50, 60), 'T': (60, 210, 200), 't': (30, 150, 150), 'l': (190, 255, 250)}
    out['fins'] = from_strings([
        "...........",
        ".kk.....kk.",
        "kTlk...kTlk",
        "kTTk...kTTk",
        "kTTTk.kTTTk",
        "ktTTk.ktTTk",
        "kttTk.kttTk",
        ".ktkk..ktkk",
        "..k.k...k.k",
    ], pal)
    # Shell Shield: a scallop shell
    pal = {'k': (80, 40, 30), 'P': (250, 170, 150), 'p': (220, 120, 110), 'l': (255, 230, 220)}
    out['shield'] = from_strings([
        "...kkkkk...",
        "..kPlPlPk..",
        ".kPpPpPpPk.",
        "kPlPpPpPlPk",
        "kPpPpPpPpPk",
        "kPpPpPpPpPk",
        ".kPpPpPpPk.",
        "..kkPpPkk..",
        "....kPk....",
        "...kkkkk...",
    ], pal)
    # Deep Ink: a purple ink sac with a drip
    pal = {'k': (20, 10, 40), 'V': (110, 60, 200), 'v': (70, 30, 140), 'l': (200, 170, 255)}
    out['deepink'] = from_strings([
        "...kkk...",
        "..kVVVk..",
        ".kVlVVVk.",
        "kVlVVVVVk",
        "kVVVVVVvk",
        "kVVVVVvvk",
        ".kVVvvvk.",
        "..kkkkk..",
        "....k....",
        "...kVk...",
        "....k....",
    ], pal)
    # Bubble bomb: a dark sphere with a lit fuse
    pal = {'k': (10, 10, 30), 'B': (50, 60, 120), 'b': (30, 36, 80), 'l': (150, 170, 240),
           'f': (200, 170, 120), 'F': (255, 220, 80), 'r': (255, 120, 40)}
    out['bomb'] = from_strings([
        "......Fr.",
        ".....fF..",
        "....f....",
        "..kkfkk..",
        ".kBBBBBk.",
        "kBlBBBBbk",
        "kBlBBBBbk",
        "kBBBBBbbk",
        "kBBBBbbbk",
        ".kBbbbbk.",
        "..kkkkk..",
    ], pal)
    out['bomb_lit'] = tint(out['bomb'], (255, 90, 60))
    return out


def _cracked(rnd):
    s = _rock(rnd)
    c = (24, 22, 40)
    pygame.draw.lines(s, c, False, [(3, 2), (6, 6), (5, 9), (8, 12), (7, 15)], 2)
    pygame.draw.lines(s, c, False, [(6, 6), (10, 5), (13, 8)], 2)
    pygame.draw.lines(s, c, False, [(8, 12), (12, 13)])
    pygame.draw.line(s, (150, 156, 196), (7, 6), (9, 6))
    return s


def make_puff():
    frames = []
    for i, r in enumerate((3, 5, 7, 6)):
        s = pygame.Surface((16, 16), pygame.SRCALPHA)
        col = (240, 240, 255) if i < 3 else (180, 190, 220)
        for a in range(0, 360, 60):
            ox = 8 + math.cos(math.radians(a + i * 20)) * (r - 2)
            oy = 8 + math.sin(math.radians(a + i * 20)) * (r - 2)
            pygame.draw.circle(s, col, (int(ox), int(oy)), max(1, r // 2))
        if i < 2:
            pygame.draw.circle(s, (255, 255, 255), (8, 8), r - 1)
        frames.append(s)
    return frames


def make_shots():
    ink = pygame.Surface((8, 8), pygame.SRCALPHA)
    pygame.draw.circle(ink, (10, 10, 30), (4, 4), 4)
    pygame.draw.circle(ink, (40, 30, 80), (4, 4), 3)
    ink.set_at((3, 2), (150, 140, 220))
    spine = pygame.Surface((6, 6), pygame.SRCALPHA)
    pygame.draw.circle(spine, (140, 96, 16), (3, 3), 3)
    pygame.draw.circle(spine, (255, 230, 120), (3, 3), 2)
    bubble = pygame.Surface((10, 10), pygame.SRCALPHA)
    pygame.draw.circle(bubble, (200, 120, 255, 120), (5, 5), 5)
    pygame.draw.circle(bubble, (240, 220, 255), (5, 5), 5, 1)
    bubble.set_at((3, 3), (255, 255, 255))
    return {'ink': ink, 'spine': spine, 'bubble': bubble}


# --------------------------------------------------------------------------
# Tiles
# --------------------------------------------------------------------------

SAND = (212, 192, 138)
SAND_D = (188, 166, 114)
SAND_L = (234, 218, 170)


def _sand(rnd, base=SAND):
    s = pygame.Surface((TILE, TILE))
    s.fill(base)
    for _ in range(9):
        s.set_at((rnd.randrange(16), rnd.randrange(16)), SAND_D)
    for _ in range(5):
        s.set_at((rnd.randrange(16), rnd.randrange(16)), SAND_L)
    return s


def _abyss(rnd):
    s = pygame.Surface((TILE, TILE))
    s.fill((92, 98, 132))
    for _ in range(9):
        s.set_at((rnd.randrange(16), rnd.randrange(16)), (74, 78, 112))
    for _ in range(4):
        s.set_at((rnd.randrange(16), rnd.randrange(16)), (130, 138, 176))
    return s


def _rock(rnd):
    s = pygame.Surface((TILE, TILE))
    s.fill((56, 58, 88))
    pygame.draw.ellipse(s, (98, 102, 142), (0, 0, 16, 15))
    pygame.draw.ellipse(s, (120, 126, 168), (2, 1, 10, 8))
    pygame.draw.arc(s, (156, 162, 200), (2, 1, 11, 10), 1.6, 3.0)
    pygame.draw.arc(s, (60, 62, 96), (1, 2, 14, 13), 4.6, 6.0)
    for _ in range(4):
        s.set_at((rnd.randrange(3, 13), rnd.randrange(3, 12)), (80, 84, 120))
    return s


def _coral(rnd, col):
    s = _sand(rnd)
    dark = tuple(max(0, c - 90) for c in col)
    light = tuple(min(255, c + 60) for c in col)

    def branch(x, y, a, ln, depth):
        if depth == 0 or ln < 2:
            return
        ex = x + math.cos(a) * ln
        ey = y + math.sin(a) * ln
        pygame.draw.line(s, dark, (x + 1, y), (ex + 1, ey), 3)
        pygame.draw.line(s, col, (x, y), (ex, ey), 2)
        s.set_at((int(ex), int(ey)), light)
        branch(ex, ey, a - 0.55, ln * 0.7, depth - 1)
        branch(ex, ey, a + 0.55, ln * 0.7, depth - 1)

    branch(8, 15, -math.pi / 2 + rnd.uniform(-0.2, 0.2), 6, 3)
    return s


def _kelp(rnd, offset=0):
    s = _sand(rnd)
    dk, md, lt = (18, 80, 40), (46, 156, 78), (130, 214, 120)
    for i, bx in enumerate((3, 8, 12)):
        pts = []
        for y in range(15, 0, -1):
            x = bx + math.sin(y * 0.6 + i * 2 + offset) * 1.6
            pts.append((x, y))
        pygame.draw.lines(s, dk, False, [(x + 1, y) for x, y in pts], 3)
        pygame.draw.lines(s, md, False, pts, 2)
        for x, y in pts[3::4]:
            s.set_at((int(x), int(y)), lt)
    return s


def _trench(rnd):
    s = pygame.Surface((TILE, TILE))
    s.fill((22, 38, 96))
    for y in (3, 9, 14):
        for x in range(16):
            yy = y + int(round(math.sin(x * 0.8 + y) * 1))
            s.set_at((x, yy % 16), (14, 26, 72))
    for _ in range(3):
        s.set_at((rnd.randrange(16), rnd.randrange(16)), (40, 64, 140))
    return s


def _cave():
    s = pygame.Surface((TILE, TILE))
    s.fill((56, 58, 88))
    pygame.draw.rect(s, (0, 0, 0), (0, 4, 16, 12))
    pygame.draw.ellipse(s, (0, 0, 0), (0, 0, 16, 12))
    return s


def _seagrass(rnd):
    s = _sand(rnd)
    for _ in range(3):
        x, y = rnd.randrange(2, 14), rnd.randrange(5, 15)
        for dx, h in ((-1, 3), (0, 4), (1, 3)):
            pygame.draw.line(s, (70, 150, 80), (x + dx, y), (x + dx * 2, y - h))
    return s


def _dfloor(rnd):
    s = pygame.Surface((TILE, TILE))
    s.fill((60, 68, 112))
    pygame.draw.rect(s, (46, 52, 90), (0, 0, 16, 16), 1)
    pygame.draw.line(s, (78, 88, 136), (1, 1), (14, 1))
    pygame.draw.line(s, (78, 88, 136), (1, 1), (1, 14))
    for _ in range(3):
        s.set_at((rnd.randrange(2, 14), rnd.randrange(2, 14)), (52, 58, 100))
    return s


_pyr_cache = {}
PYR_STONE = {'P': (150, 128, 92), 'Q': (184, 162, 118)}


def pyramid_tile(ch, lower, rail):
    """A block of the stepped Octo Temple. lower = (north, south, west, east) neighbour is lower,
    rail = (left, right) edge of a staircase."""
    key = (ch, lower, rail)
    if key in _pyr_cache:
        return _pyr_cache[key]
    s = pygame.Surface((TILE, TILE))
    n, so, w, e = lower
    if ch == 'T':
        # the sanctuary on top: big pale flagstones
        s.fill((214, 196, 152))
        pygame.draw.rect(s, (188, 168, 124), (0, 0, TILE, TILE), 1)
        pygame.draw.line(s, (236, 222, 186), (1, 1), (TILE - 2, 1))
        pygame.draw.line(s, (236, 222, 186), (1, 1), (1, TILE - 2))
        pygame.draw.circle(s, (200, 180, 136), (8, 8), 2)
        if so:
            pygame.draw.rect(s, (130, 112, 80), (0, 12, TILE, 4))
            pygame.draw.line(s, (240, 228, 196), (0, 11), (TILE, 11))
    elif ch == 'H':
        # stairs: four steps, each a light tread over a dark riser
        for i in range(4):
            y = i * 4
            pygame.draw.rect(s, (196, 176, 132), (0, y, TILE, 3))
            pygame.draw.rect(s, (120, 100, 72), (0, y + 3, TILE, 1))
        if rail[0]:
            pygame.draw.rect(s, (110, 92, 66), (0, 0, 2, TILE))
        if rail[1]:
            pygame.draw.rect(s, (110, 92, 66), (TILE - 2, 0, 2, TILE))
    else:
        base = PYR_STONE[ch]
        dark = tuple(int(c * 0.72) for c in base)
        light = tuple(min(255, int(c * 1.15)) for c in base)
        s.fill(base)
        # masonry: two courses of blocks with staggered joints
        for y, joints in ((0, (5, 13)), (8, (1, 9))):
            pygame.draw.line(s, dark, (0, y + 7), (TILE, y + 7))
            for x in joints:
                pygame.draw.line(s, dark, (x, y), (x, y + 6))
            pygame.draw.line(s, light, (0, y), (TILE, y))
        if so:          # the step's riser faces us
            pygame.draw.rect(s, tuple(int(c * 0.55) for c in base), (0, 11, TILE, 5))
            for x in (3, 9, 15):
                pygame.draw.line(s, tuple(int(c * 0.42) for c in base), (x, 11), (x, 15))
            pygame.draw.line(s, light, (0, 10), (TILE, 10))
        if n:
            pygame.draw.line(s, (240, 226, 190), (0, 0), (TILE, 0))
        if w:
            pygame.draw.line(s, tuple(int(c * 0.8) for c in base), (0, 0), (0, TILE))
        if e:
            pygame.draw.rect(s, tuple(int(c * 0.6) for c in base), (TILE - 2, 0, 2, TILE))
    _pyr_cache[key] = s
    return s


def _dwall(rnd):
    s = pygame.Surface((TILE, TILE))
    s.fill((22, 24, 50))
    for row in range(4):
        off = 4 if row % 2 else 0
        for col in range(-1, 3):
            r = pygame.Rect(col * 8 + off, row * 4, 7, 3)
            pygame.draw.rect(s, (38, 42, 80), r)
            pygame.draw.line(s, (56, 62, 106), r.topleft, (r.right - 1, r.top))
    return s


def _statue():
    s = _dfloor(random.Random(3))
    gray = {'k': (30, 30, 44), 'B': (138, 140, 160), 'H': (190, 192, 210), 'D': (96, 98, 118),
            'P': (110, 112, 132), 'e': (40, 40, 56), 'w': (200, 200, 220), 'c': (138, 140, 160)}
    rows = [list(r) for r in OCTO_BODY + OCTO_LEGS[0]]
    _octo_face(rows, 'blue', 'down')
    s.blit(from_strings([''.join(r) for r in rows], gray), (0, 0))
    return s


def _pit():
    s = pygame.Surface((TILE, TILE))
    s.fill((6, 6, 14))
    pygame.draw.line(s, (30, 32, 56), (0, 0), (15, 0))
    return s


def _locked(rnd):
    s = _dwall(rnd)
    pygame.draw.rect(s, (110, 70, 34), (1, 1, 14, 15))
    pygame.draw.rect(s, (70, 40, 16), (1, 1, 14, 15), 1)
    pygame.draw.line(s, (70, 40, 16), (8, 1), (8, 15))
    pygame.draw.rect(s, (240, 200, 60), (5, 6, 6, 6))
    pygame.draw.rect(s, (0, 0, 0), (7, 8, 2, 3))
    return s


def _shutter(rnd):
    s = _dfloor(rnd)
    for x in (2, 6, 10, 14):
        pygame.draw.line(s, (30, 30, 46), (x + 1, 0), (x + 1, 15))
        pygame.draw.line(s, (170, 172, 196), (x, 0), (x, 15))
    pygame.draw.line(s, (170, 172, 196), (0, 7), (15, 7))
    return s


def _stairs():
    s = pygame.Surface((TILE, TILE))
    s.fill((0, 0, 0))
    for i, y in enumerate((2, 6, 10)):
        c = 90 - i * 25
        pygame.draw.rect(s, (c, c, c + 30), (1, y, 14, 3))
    return s


def _floor(rnd, base, dark, light):
    s = pygame.Surface((TILE, TILE))
    s.fill(base)
    for _ in range(9):
        s.set_at((rnd.randrange(16), rnd.randrange(16)), dark)
    for _ in range(5):
        s.set_at((rnd.randrange(16), rnd.randrange(16)), light)
    return s


def _cobble(rnd, base, dark, light):
    s = _floor(rnd, base, dark, light)
    off = rnd.choice((0, 4))
    for y in (0, 8):
        pygame.draw.line(s, dark, (0, y), (15, y))
        for x in ((off, off + 8) if y == 0 else (off + 4, off + 12)):
            pygame.draw.line(s, dark, (x % 16, y), (x % 16, y + 7))
    s.set_at((rnd.randrange(16), rnd.randrange(16)), light)
    return s


def _rockc(rnd, base, cols):
    dk, md, lt, hi = cols
    s = base.copy()
    pygame.draw.ellipse(s, dk, (0, 1, 16, 15))
    pygame.draw.ellipse(s, md, (0, 0, 16, 15))
    pygame.draw.ellipse(s, lt, (2, 1, 10, 8))
    pygame.draw.arc(s, hi, (2, 1, 11, 10), 1.6, 3.0)
    for _ in range(4):
        s.set_at((rnd.randrange(3, 13), rnd.randrange(3, 12)), dk)
    return s


def _plank(rnd, base):
    """Wrecked ship timbers for the graveyard's walls."""
    s = base.copy()
    wood, dark, light = (120, 82, 50), (70, 44, 26), (160, 116, 72)
    pygame.draw.rect(s, dark, (0, 2, 16, 13))
    for i, y in enumerate((3, 7, 11)):
        pygame.draw.rect(s, wood, (0, y, 16, 3))
        pygame.draw.line(s, light, (0, y), (15, y))
        s.set_at(((i * 5 + 3) % 16, y + 1), dark)
    pygame.draw.line(s, dark, (rnd.randrange(4, 12), 2), (rnd.randrange(4, 12), 14))
    return s


def _pillar(rnd, base):
    s = base.copy()
    pygame.draw.rect(s, (60, 64, 80), (3, 1, 11, 15))
    pygame.draw.rect(s, (130, 136, 160), (3, 0, 10, 15))
    pygame.draw.rect(s, (170, 176, 200), (3, 0, 10, 3))
    for x in (5, 8, 11):
        pygame.draw.line(s, (100, 104, 128), (x, 4), (x, 13))
    if rnd.random() < 0.5:   # broken top
        pygame.draw.polygon(s, base.get_at((0, 0)), [(9, 0), (13, 0), (13, 4)])
    return s


def _grass(rnd, base, col):
    s = base.copy()
    for _ in range(3):
        x, y = rnd.randrange(2, 14), rnd.randrange(5, 15)
        for dx, h in ((-1, 3), (0, 4), (1, 3)):
            pygame.draw.line(s, col, (x + dx, y), (x + dx * 2, y - h))
    return s


def _ice_spike(rnd, base):
    s = base.copy()
    for x, h in ((4, 10), (8, 14), (12, 9)):
        pygame.draw.polygon(s, (120, 180, 230), [(x - 3, 15), (x + 3, 15), (x, 15 - h)])
        pygame.draw.line(s, (240, 250, 255), (x - 1, 14), (x, 15 - h + 2))
    return s


def _vent_coral(rnd, base):
    """Smoking chimney vent."""
    s = base.copy()
    pygame.draw.polygon(s, (40, 30, 30), [(3, 15), (13, 15), (10, 4), (6, 4)])
    pygame.draw.polygon(s, (90, 60, 50), [(4, 15), (12, 15), (9, 5), (7, 5)])
    pygame.draw.ellipse(s, (255, 140, 40), (6, 3, 4, 3))
    return s


def _broken_statue(rnd, base):
    s = base.copy()
    pygame.draw.rect(s, (70, 74, 92), (4, 9, 9, 7))
    pygame.draw.rect(s, (140, 146, 170), (4, 8, 8, 7))
    pygame.draw.circle(s, (140, 146, 170), (8, 5), 3)
    pygame.draw.line(s, (90, 94, 116), (6, 9), (10, 14))
    return s


def _pool(rnd, base, line, spark):
    s = pygame.Surface((TILE, TILE))
    s.fill(base)
    for y in (3, 9, 14):
        for x in range(16):
            yy = y + int(round(math.sin(x * 0.8 + y) * 1))
            s.set_at((x, yy % 16), line)
    for _ in range(3):
        s.set_at((rnd.randrange(16), rnd.randrange(16)), spark)
    return s


def _lava(rnd):
    s = pygame.Surface((TILE, TILE))
    s.fill((230, 90, 20))
    for _ in range(5):
        pygame.draw.circle(s, (255, 180, 60), (rnd.randrange(16), rnd.randrange(16)), rnd.randint(1, 2))
    for y in (4, 11):
        for x in range(16):
            s.set_at((x, (y + int(math.sin(x * 0.7 + y) * 1.5)) % 16), (150, 40, 10))
    return s


def _icewall(rnd):
    s = pygame.Surface((TILE, TILE))
    s.fill((150, 210, 245))
    pygame.draw.rect(s, (90, 150, 210), (0, 0, 16, 16), 1)
    pygame.draw.line(s, (240, 250, 255), (2, 12), (12, 2), 2)
    pygame.draw.line(s, (200, 235, 255), (6, 14), (14, 6))
    return s


def _ghostwall(rnd):
    s = pygame.Surface((TILE, TILE))
    s.fill((50, 30, 80))
    for y in range(0, 16, 4):
        for x in range(16):
            s.set_at((x, (y + int(math.sin(x * 0.6 + y) * 1.5)) % 16), (150, 100, 220))
    pygame.draw.rect(s, (110, 70, 180), (0, 0, 16, 16), 1)
    return s


THEME_SPECS = {
    # floor, floor dark, floor light, rock colours (dark, mid, light, highlight), grass colour, coral colours
    'kelp': ((168, 176, 116), (140, 150, 96), (196, 204, 146),
             ((40, 60, 50), (70, 104, 80), (96, 136, 100), (140, 180, 130)), (40, 120, 60),
             ((120, 200, 90), (90, 170, 120), (170, 210, 80))),
    'garden': ((236, 196, 176), (214, 168, 150), (250, 222, 206),
               ((96, 60, 90), (150, 100, 140), (186, 130, 170), (220, 176, 206)), (220, 110, 150),
               ((250, 90, 140), (255, 170, 60), (180, 110, 255), (90, 210, 220))),
    'lagoon': ((236, 230, 204), (214, 206, 176), (250, 248, 230),
               ((86, 110, 120), (130, 160, 170), (170, 200, 206), (210, 235, 240)), (70, 170, 140),
               ((80, 220, 210), (250, 140, 120), (250, 220, 90))),
    'wreck': ((150, 140, 116), (126, 116, 96), (176, 168, 142),
              None, (100, 110, 70), ((150, 150, 130), (170, 120, 90), (120, 140, 110))),
    'frost': ((222, 236, 246), (196, 216, 232), (250, 252, 255),
              ((70, 110, 160), (130, 180, 225), (176, 214, 245), (235, 248, 255)), (150, 200, 220),
              None),
    'vents': ((84, 70, 70), (64, 52, 52), (112, 92, 86),
              ((24, 18, 20), (46, 36, 38), (70, 56, 56), (110, 80, 70)), (140, 70, 40), None),
    'city': ((118, 120, 140), (92, 94, 112), (148, 150, 172),
             None, (90, 130, 110), None),
    'sky': ((112, 190, 90), (86, 160, 70), (150, 214, 120),
            ((80, 80, 90), (140, 140, 150), (180, 180, 190), (220, 220, 230)), (250, 230, 90), None),
}


def _sky_void(rnd):
    s = pygame.Surface((TILE, TILE))
    s.fill((120, 180, 240))
    for _ in range(2):
        x, y = rnd.randrange(16), rnd.randrange(16)
        pygame.draw.ellipse(s, (200, 228, 255), (x - 5, y - 2, 12, 5))
        pygame.draw.ellipse(s, (235, 245, 255), (x - 3, y - 2, 7, 3))
    return s


def _tree(rnd, base):
    s = base.copy()
    pygame.draw.rect(s, (90, 60, 30), (7, 9, 3, 7))
    pygame.draw.circle(s, (30, 100, 40), (8, 7), 7)
    pygame.draw.circle(s, (60, 150, 60), (7, 6), 6)
    pygame.draw.circle(s, (110, 200, 90), (5, 4), 2)
    return s


def _planks(rnd):
    s = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
    s.blit(_sky_void(rnd), (0, 0))
    pygame.draw.rect(s, (110, 74, 40), (0, 2, 16, 12))
    for x in (0, 5, 10, 15):
        pygame.draw.line(s, (70, 44, 22), (x, 2), (x, 13))
    pygame.draw.line(s, (160, 120, 70), (0, 3), (15, 3))
    pygame.draw.line(s, (60, 40, 20), (0, 14), (15, 14))
    return s


def _geyser(rnd, base, sky=False):
    s = base.copy()
    if sky:   # a hole in the island with clouds swirling below
        pygame.draw.ellipse(s, (60, 40, 20), (1, 3, 14, 11))
        pygame.draw.ellipse(s, (150, 200, 250), (2, 4, 12, 9))
        pygame.draw.arc(s, (255, 255, 255), (4, 5, 8, 6), 0, 4.5, 1)
    else:     # bubbling vent in the sand
        pygame.draw.ellipse(s, (60, 70, 90), (1, 4, 14, 10))
        pygame.draw.ellipse(s, (110, 200, 240), (3, 6, 10, 6))
        for x, y in ((6, 5), (9, 3), (8, 1)):
            pygame.draw.circle(s, (230, 250, 255), (x, y), 1)
    return s


def make_themes(rnd):
    out = {}
    for name, (fl, fd, flt, rock, grass, corals) in THEME_SPECS.items():
        floor = _cobble if name == 'city' else _floor
        t = {'.': [floor(rnd, fl, fd, flt) for _ in range(4)]}
        t[','] = [_grass(rnd, t['.'][i], grass) for i in range(2)]
        if rock:
            t['#'] = [_rockc(rnd, t['.'][i], rock) for i in range(3)]
        elif name == 'wreck':
            t['#'] = [_plank(rnd, t['.'][i]) for i in range(3)]
        else:
            t['#'] = [_pillar(rnd, t['.'][i]) for i in range(3)]
        if name == 'frost':
            t['C'] = [_ice_spike(rnd, t['.'][i]) for i in range(2)]
            t['v'] = [_pool(rnd, (90, 150, 200), (130, 190, 230), (230, 245, 255)) for _ in range(2)]
        elif name == 'vents':
            t['C'] = [_vent_coral(rnd, t['.'][i]) for i in range(2)]
            t['v'] = [_pool(rnd, (30, 20, 24), (60, 30, 30), (200, 90, 40)) for _ in range(2)]
        elif name == 'city':
            t['C'] = [_broken_statue(rnd, t['.'][i]) for i in range(2)]
        elif name == 'sky':
            t['C'] = [_tree(rnd, t['.'][i]) for i in range(2)]
            t['v'] = [_sky_void(rnd) for _ in range(4)]
            t['='] = [_planks(rnd)]
            t['Y'] = [_geyser(rnd, t['.'][0], sky=True)]
        elif corals:
            t['C'] = [_coral_on(rnd, t['.'][i % 4], c) for i, c in enumerate(corals)]
        if name == 'lagoon':
            t['v'] = [_pool(rnd, (40, 140, 170), (30, 110, 140), (140, 230, 240)) for _ in range(2)]
        out[name] = t
    return out


def _coral_on(rnd, base, col):
    s = base.copy()
    dark = tuple(max(0, c - 90) for c in col)
    light = tuple(min(255, c + 60) for c in col)

    def branch(x, y, a, ln, depth):
        if depth == 0 or ln < 2:
            return
        ex = x + math.cos(a) * ln
        ey = y + math.sin(a) * ln
        pygame.draw.line(s, dark, (x + 1, y), (ex + 1, ey), 3)
        pygame.draw.line(s, col, (x, y), (ex, ey), 2)
        s.set_at((int(ex), int(ey)), light)
        branch(ex, ey, a - 0.55, ln * 0.7, depth - 1)
        branch(ex, ey, a + 0.55, ln * 0.7, depth - 1)

    branch(8, 15, -math.pi / 2 + rnd.uniform(-0.2, 0.2), 6, 3)
    return s


def make_tiles():
    rnd = random.Random(1234)
    ow = {
        '.': [_sand(rnd) for _ in range(4)],
        'd': [_abyss(rnd) for _ in range(3)],
        ',': [_seagrass(rnd) for _ in range(2)],
        '#': [_rock(rnd) for _ in range(3)],
        'R': [_cracked(random.Random(77))],
        'C': [_coral(rnd, c) for c in ((250, 110, 96), (250, 160, 70), (210, 100, 220))],
        'K': [_kelp(rnd, o) for o in (0, 1.5)],
        'v': [_trench(rnd) for _ in range(2)],
        'E': [_cave()],
        'I': [_icewall(rnd)],
        'G': [_ghostwall(rnd)],
        'l': [_lava(rnd), _lava(rnd)],
        'Y': [_geyser(rnd, _sand(rnd))],
    }
    dg = {
        '=': [_dfloor(rnd) for _ in range(2)],
        'W': [_dwall(rnd) for _ in range(2)],
        'S': [_statue()],
        'v': [_pit()],
        'L': [_locked(rnd)],
        'X': [_shutter(rnd)],
        'E': [_stairs()],
        'B': [_sealed(rnd)],
    }
    return {'overworld': ow, 'dungeon': dg, 'themes': make_themes(rnd)}


# --------------------------------------------------------------------------
# Bitmap font (5x7, uppercase)
# --------------------------------------------------------------------------

FONT = {
    'A': ".###.|#...#|#...#|#####|#...#|#...#|#...#",
    'B': "####.|#...#|#...#|####.|#...#|#...#|####.",
    'C': ".###.|#...#|#....|#....|#....|#...#|.###.",
    'D': "####.|#...#|#...#|#...#|#...#|#...#|####.",
    'E': "#####|#....|#....|####.|#....|#....|#####",
    'F': "#####|#....|#....|####.|#....|#....|#....",
    'G': ".###.|#...#|#....|#.###|#...#|#...#|.####",
    'H': "#...#|#...#|#...#|#####|#...#|#...#|#...#",
    'I': ".###.|..#..|..#..|..#..|..#..|..#..|.###.",
    'J': "..###|...#.|...#.|...#.|...#.|#..#.|.##..",
    'K': "#...#|#..#.|#.#..|##...|#.#..|#..#.|#...#",
    'L': "#....|#....|#....|#....|#....|#....|#####",
    'M': "#...#|##.##|#.#.#|#.#.#|#...#|#...#|#...#",
    'N': "#...#|#...#|##..#|#.#.#|#..##|#...#|#...#",
    'O': ".###.|#...#|#...#|#...#|#...#|#...#|.###.",
    'P': "####.|#...#|#...#|####.|#....|#....|#....",
    'Q': ".###.|#...#|#...#|#...#|#.#.#|#..#.|.##.#",
    'R': "####.|#...#|#...#|####.|#.#..|#..#.|#...#",
    'S': ".####|#....|#....|.###.|....#|....#|####.",
    'T': "#####|..#..|..#..|..#..|..#..|..#..|..#..",
    'U': "#...#|#...#|#...#|#...#|#...#|#...#|.###.",
    'V': "#...#|#...#|#...#|#...#|#...#|.#.#.|..#..",
    'W': "#...#|#...#|#...#|#.#.#|#.#.#|#.#.#|.#.#.",
    'X': "#...#|#...#|.#.#.|..#..|.#.#.|#...#|#...#",
    'Y': "#...#|#...#|.#.#.|..#..|..#..|..#..|..#..",
    'Z': "#####|....#|...#.|..#..|.#...|#....|#####",
    '0': ".###.|#...#|#..##|#.#.#|##..#|#...#|.###.",
    '1': "..#..|.##..|..#..|..#..|..#..|..#..|.###.",
    '2': ".###.|#...#|....#|...#.|..#..|.#...|#####",
    '3': "#####|...#.|..#..|...#.|....#|#...#|.###.",
    '4': "...#.|..##.|.#.#.|#..#.|#####|...#.|...#.",
    '5': "#####|#....|####.|....#|....#|#...#|.###.",
    '6': "..##.|.#...|#....|####.|#...#|#...#|.###.",
    '7': "#####|....#|...#.|..#..|.#...|.#...|.#...",
    '8': ".###.|#...#|#...#|.###.|#...#|#...#|.###.",
    '9': ".###.|#...#|#...#|.####|....#|...#.|.##..",
    ' ': ".....|.....|.....|.....|.....|.....|.....",
    '.': ".....|.....|.....|.....|.....|.##..|.##..",
    ',': ".....|.....|.....|.....|.##..|..#..|.#...",
    '!': "..#..|..#..|..#..|..#..|..#..|.....|..#..",
    '?': ".###.|#...#|....#|...#.|..#..|.....|..#..",
    '-': ".....|.....|.....|.###.|.....|.....|.....",
    ':': ".....|.##..|.##..|.....|.##..|.##..|.....",
    "'": "..#..|..#..|.#...|.....|.....|.....|.....",
    '/': "....#|...#.|...#.|..#..|.#...|.#...|#....",
    '>': ".#...|..#..|...#.|....#|...#.|..#..|.#...",
    '<': "...#.|..#..|.#...|#....|.#...|..#..|...#.",
    '(': "...#.|..#..|.#...|.#...|.#...|..#..|...#.",
    ')': ".#...|..#..|...#.|...#.|...#.|..#..|.#...",
    '+': ".....|..#..|..#..|#####|..#..|..#..|.....",
    '*': ".....|#.#.#|.###.|#####|.###.|#.#.#|.....",
    '"': ".#.#.|.#.#.|.....|.....|.....|.....|.....",
}
_glyph_cache = {}


def glyph(ch, color):
    key = (ch, color)
    g = _glyph_cache.get(key)
    if g is None:
        rows = FONT.get(ch, FONT['?']).split('|')
        g = from_strings(rows, {'#': color})
        _glyph_cache[key] = g
    return g


def text(surf, s, x, y, color=(255, 255, 255), shadow=True, center=False):
    s = s.upper()
    if center:
        x = x - text_width(s) // 2
    for i, ch in enumerate(s):
        if shadow:
            surf.blit(glyph(ch, (0, 0, 0)), (x + i * 6 + 1, y + 1))
        surf.blit(glyph(ch, color), (x + i * 6, y))


def text_width(s):
    return len(s) * 6 - 1


def wrap(s, max_chars):
    lines = []
    for para in s.split('\n'):
        line = ''
        for word in para.split(' '):
            if line and len(line) + 1 + len(word) > max_chars:
                lines.append(line)
                line = word
            else:
                line = word if not line else line + ' ' + word
        lines.append(line)
    return lines


# --------------------------------------------------------------------------
# public registry
# --------------------------------------------------------------------------

OCTO = SLAP = TILES = SPR = None


ICECRAB_PAL = {'k': (20, 40, 80), 'R': (120, 190, 255), 'D': (60, 120, 200),
               'w': (255, 255, 255), 'e': (0, 0, 0), 'W': (230, 245, 255)}
LAVACRAB_PAL = {'k': (40, 10, 0), 'R': (255, 150, 30), 'D': (200, 60, 10),
                'w': (255, 255, 200), 'e': (0, 0, 0), 'W': (255, 230, 120)}


def make_halfpearl():
    s = make_golden()
    h = pygame.Surface((16, 16), pygame.SRCALPHA)
    h.blit(s, (0, 0), (0, 0, 9, 16))
    pygame.draw.line(h, (120, 80, 0), (8, 2), (7, 5))
    pygame.draw.line(h, (120, 80, 0), (7, 5), (9, 9))
    pygame.draw.line(h, (120, 80, 0), (9, 9), (8, 14))
    return h


def make_gull():
    pal = {'k': (40, 40, 50), 'W': (250, 250, 250), 'g': (190, 196, 210), 'y': (250, 200, 40), 'e': (0, 0, 0)}
    up = [
        "k..............k",
        "Wk............kW",
        "gWk..........kWg",
        ".gWk..kkkk..kWg.",
        "..gWkkWWWWkkWg..",
        "...kWWWeWWWWk...",
        "....kWWWWWWkyy..",
        ".....kkggkk.....",
    ]
    down = [
        "................",
        "................",
        "......kkkk......",
        "....kkWWWWkk....",
        "..kkWWWeWWWWkyy.",
        ".kWWWWWWWWWWWk..",
        "kgWgk.kggk.kgWgk",
        "kk.....kk.....kk",
    ]
    return [from_strings(up, pal), from_strings(down, pal)]


def make_murk():
    out = {}
    for k, frames in make_shark().items():
        out[k] = [tint(f, (170, 120, 240)) for f in frames]
    return out


def load():
    global OCTO, SLAP, TILES, SPR
    OCTO = make_octo()
    SLAP = make_slap()
    TILES = make_tiles()
    hearts = make_hearts()
    SPR = {
        'crab': make_crab(CRAB_PAL),
        'icecrab': make_crab({**CRAB_PAL, **ICECRAB_PAL}),
        'lavacrab': make_crab({**CRAB_PAL, **LAVACRAB_PAL}),
        'murk': make_murk(),
        'gull': make_gull(),
        'halfpearl': make_halfpearl(),
        'shark': make_shark(),
        'urchin': make_urchin(),
        'jelly': make_jelly(),
        'puffer': make_puffer(),
        'turtle': make_turtle(),
        'hermit': make_hermit(),
        'heart': hearts,
        'pearl': make_pearl((236, 236, 246), (255, 255, 255)),
        'bluepearl': make_pearl((90, 170, 255), (220, 240, 255)),
        'golden': make_golden(),
        'bell': make_bell(),
        'shrimp': make_shrimp(),
        'key': make_key(),
        'puff': make_puff(),
        'shots': make_shots(),
        'items': make_items(),
        'orb': make_pearl((120, 255, 200), (230, 255, 245), size=10),
    }
