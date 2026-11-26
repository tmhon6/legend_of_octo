"""Hi-fi 3D for the cinematics: smooth, shiny shapes drawn at a higher resolution than the game.

The pixel-art game is drawn at 256x232 and scaled up; the 3D scenes are drawn straight onto a
canvas settings.HI times bigger, so they get real detail instead of big pixels.

* Spheres are "impostors": one sphere is shaded once (soft light, a specular glint and a rim of
  light), then tinted and resized for every ball that's needed. Because the light stays put
  relative to the camera, a shaded ball looks right from any angle.
* Models are built from balls and sorted back-to-front: a squishy 3D Octo, turtles, and
  "bead figures" that turn any sprite into a puffy 3D toy (used for the bosses).
* Smooth text uses the TrueType font bundled with pygame, with an extruded, bevelled 3D look.
"""
import math

import pygame

from settings import HI, SCREEN_H, SCREEN_W

W, H = SCREEN_W * HI, SCREEN_H * HI          # the hi-res canvas
F = 210 * HI                                 # focal length (hi-res pixels)
_L = (-0.42, -0.68, -0.6)                    # towards the light: up, left and in front
_LN = math.sqrt(sum(c * c for c in _L))
LIGHT = tuple(c / _LN for c in _L)
R0 = 64                                      # radius of the master shaded sphere


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def ease(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_io(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def mix(c1, c2, t):
    t = clamp(t)
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def rot(yaw, pitch=0.0, roll=0.0):
    """Rotation matrix: yaw about y, then pitch about x, then roll about z."""
    cy, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cr, sr = math.cos(roll), math.sin(roll)
    # Rz * Rx * Ry
    a = ((cy, 0, sy), (sp * sy, cp, -sp * cy), (-cp * sy, sp, cp * cy))
    return ((cr * a[0][0] - sr * a[1][0], cr * a[0][1] - sr * a[1][1], cr * a[0][2] - sr * a[1][2]),
            (sr * a[0][0] + cr * a[1][0], sr * a[0][1] + cr * a[1][1], sr * a[0][2] + cr * a[1][2]),
            a[2])


def apply(m, x, y, z):
    return (m[0][0] * x + m[0][1] * y + m[0][2] * z,
            m[1][0] * x + m[1][1] * y + m[1][2] * z,
            m[2][0] * x + m[2][1] * y + m[2][2] * z)


def project(x, y, z, cx=W / 2, cy=H / 2):
    z = max(z, 1.0)
    k = F / z
    return cx + x * k, cy + y * k, k


# ======================================================================
# the master sphere (built a few rows at a time so nothing ever stalls)
# ======================================================================
_maps = None
_build = None


def _builder():
    size = R0 * 2
    dif = pygame.Surface((size, size), pygame.SRCALPHA)
    spec = pygame.Surface((size, size))
    lx, ly, lz = LIGHT
    hx, hy, hz = lx, ly, lz - 1.0
    hn = math.sqrt(hx * hx + hy * hy + hz * hz)
    hx, hy, hz = hx / hn, hy / hn, hz / hn
    for py in range(size):
        v = (py + 0.5 - R0) / R0
        for px in range(size):
            u = (px + 0.5 - R0) / R0
            d2 = u * u + v * v
            cover = clamp((1 - math.sqrt(d2)) * R0 + 0.5)
            if cover <= 0:
                continue
            nz = -math.sqrt(max(0.0, 1 - min(1.0, d2)))
            ndl = u * lx + v * ly + nz * lz
            diff = 0.26 + 0.74 * max(0.0, ndl) + 0.12 * max(0.0, v)      # + a little bounce from below
            g = int(255 * clamp(diff))
            dif.set_at((px, py), (g, g, g, int(255 * cover)))
            ndh = max(0.0, u * hx + v * hy + nz * hz)
            s = ndh ** 42 * 0.95 + ndh ** 9 * 0.16
            rim = (1 - abs(nz)) ** 3 * 0.30
            k = int(255 * clamp(s + rim) * cover)
            if k:
                spec.set_at((px, py), (k, k, k))
        if py % 8 == 7:
            yield None
    yield (dif, spec)


def warm(rows=24):
    """Do a slice of the one-off sphere shading. Returns True once it's done."""
    global _maps, _build
    if _maps:
        return True
    if _build is None:
        _build = _builder()
    for _ in range(max(1, rows // 8)):
        out = next(_build)
        if out:
            _maps = out
            return True
    return False


def maps():
    while not warm(10 ** 6):
        pass
    return _maps


_col_cache = {}
_ball_cache = {}


def _colored(color, gloss):
    key = (color, gloss)
    s = _col_cache.get(key)
    if s is None:
        dif, spec = maps()
        s = dif.copy()
        s.fill((color[0], color[1], color[2], 255), special_flags=pygame.BLEND_RGBA_MULT)
        if gloss > 0:
            sp = spec
            if gloss != 1:
                sp = spec.copy()
                g = int(255 * clamp(gloss))
                sp.fill((g, g, g), special_flags=pygame.BLEND_RGB_MULT)
            s.blit(sp, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        _col_cache[key] = s
    return s


def ball(color, rx, ry=None, gloss=1.0):
    """A shaded ball (or squashed ellipsoid) of radius rx (x ry) hi-res pixels."""
    rx = max(1, int(rx + 0.5))
    ry = rx if ry is None else max(1, int(ry + 0.5))
    key = (color, gloss, rx, ry)
    s = _ball_cache.get(key)
    if s is None:
        s = pygame.transform.smoothscale(_colored(color, gloss), (rx * 2, ry * 2))
        if len(_ball_cache) > 2400:
            _ball_cache.clear()
        _ball_cache[key] = s
    return s


def blit_ball(surf, color, x, y, rx, ry=None, gloss=1.0):
    img = ball(color, rx, ry, gloss)
    surf.blit(img, (int(x - img.get_width() / 2), int(y - img.get_height() / 2)))


_glow_cache = {}


def glow(color, r):
    """A soft additive glow (blit it with BLEND_RGB_ADD)."""
    r = max(2, int(r))
    key = (color, r)
    s = _glow_cache.get(key)
    if s is None:
        base = _glow_cache.get(('base', color))
        if base is None:
            base = pygame.Surface((64, 64))
            for i in range(32, 0, -1):
                k = (1 - i / 32) ** 2
                pygame.draw.circle(base, mix((0, 0, 0), color, k), (32, 32), i)
            _glow_cache[('base', color)] = base
        s = pygame.transform.smoothscale(base, (r * 2, r * 2))
        if len(_glow_cache) > 400:
            _glow_cache.clear()
        _glow_cache[key] = s
    return s


def add_glow(surf, color, x, y, r):
    g = glow(color, r)
    surf.blit(g, (int(x - g.get_width() / 2), int(y - g.get_height() / 2)), special_flags=pygame.BLEND_RGB_ADD)


_bubble_base = None


def bubble(r):
    """A see-through bubble with a bright rim and a glint."""
    global _bubble_base
    r = max(2, int(r))
    key = ('bubble', r)
    s = _ball_cache.get(key)
    if s is None:
        if _bubble_base is None:
            b = pygame.Surface((96, 96), pygame.SRCALPHA)
            for i in range(48, 0, -1):
                k = (i / 48) ** 6
                pygame.draw.circle(b, (190, 235, 255, int(20 + 170 * k)), (48, 48), i)
            pygame.draw.circle(b, (230, 250, 255, 210), (48, 48), 47, 3)
            pygame.draw.ellipse(b, (255, 255, 255, 235), (26, 20, 20, 13))
            pygame.draw.circle(b, (255, 255, 255, 200), (66, 68), 4)
            _bubble_base = b
        s = pygame.transform.smoothscale(_bubble_base, (r * 2, r * 2))
        _ball_cache[key] = s
    return s


_shadow_cache = {}


def shadow(w, h, alpha=90):
    w, h = max(2, int(w)), max(2, int(h))
    key = (w, h, alpha)
    s = _shadow_cache.get(key)
    if s is None:
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        for i in range(10, 0, -1):
            k = i / 10
            a = int(alpha * (1 - k) ** 0.7)
            rw, rh = w * k, h * k
            pygame.draw.ellipse(s, (0, 0, 0, a), ((w - rw) / 2, (h - rh) / 2, rw, rh))
        if len(_shadow_cache) > 200:
            _shadow_cache.clear()
        _shadow_cache[key] = s
    return s


# ======================================================================
# eyes
# ======================================================================
_eye_cache = {}


def eye(pupil, w, h):
    """A glossy cartoon eye (white, coloured pupil, two glints), w x h hi-res pixels."""
    w, h = max(2, int(w)), max(1, int(h))
    key = (pupil, w, h)
    s = _eye_cache.get(key)
    if s is None:
        base = _eye_cache.get(('base', pupil))
        if base is None:
            base = pygame.Surface((64, 76), pygame.SRCALPHA)
            pygame.draw.ellipse(base, (16, 18, 40), (0, 0, 64, 76))
            pygame.draw.ellipse(base, (255, 255, 255), (4, 4, 56, 68))
            pygame.draw.ellipse(base, (222, 228, 245), (6, 44, 52, 28))
            pygame.draw.ellipse(base, (255, 255, 255), (6, 6, 52, 52))
            pygame.draw.ellipse(base, pupil, (15, 18, 36, 46))
            dark = tuple(max(0, c - 60) for c in pupil)
            pygame.draw.ellipse(base, dark, (21, 28, 24, 32))
            pygame.draw.ellipse(base, (255, 255, 255), (22, 22, 14, 14))
            pygame.draw.ellipse(base, (255, 255, 255), (38, 46, 7, 7))
            _eye_cache[('base', pupil)] = base
        s = pygame.transform.smoothscale(base, (w, h))
        if len(_eye_cache) > 300:
            _eye_cache.clear()
        _eye_cache[key] = s
    return s


# ======================================================================
# smooth text
# ======================================================================
_fonts = {}


def font(px):
    px = max(6, int(px))
    f = _fonts.get(px)
    if f is None:
        try:
            if not pygame.font.get_init():
                pygame.font.init()
            f = pygame.font.Font(None, px)
        except Exception as e:                 # no TrueType support: fall back to the pixel font
            print("font:", e)
            f = False
        _fonts[px] = f
    return f or None


def _mask(s, px):
    """White text with soft (anti-aliased) edges in its alpha."""
    f = font(px)
    if f is not None:
        return f.render(s, True, (255, 255, 255))
    import gfx                                  # fallback: the game's 5x7 font, smoothly enlarged
    w = gfx.text_width(s) + 1
    tmp = pygame.Surface((w, 8), pygame.SRCALPHA)
    gfx.text(tmp, s, 0, 0, (255, 255, 255), shadow=False)
    k = px / 9
    return pygame.transform.smoothscale(tmp, (max(1, int(w * k)), max(1, int(8 * k))))


def _tinted(mask, col):
    m = mask.copy()
    m.fill((col[0], col[1], col[2], 255), special_flags=pygame.BLEND_RGBA_MULT)
    return m


def text(s, px, color, outline=(10, 12, 30), ow=None, shadow=True):
    """Smooth text with an outline and a soft drop shadow."""
    mask = _mask(s, px)
    ow = ow if ow is not None else max(1, px // 14)
    w, h = mask.get_size()
    pad = ow + 3
    out = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
    if shadow:
        sh = _tinted(mask, (0, 0, 0))
        sh.set_alpha(110)
        out.blit(sh, (pad + ow + 1, pad + ow + 2))
    if outline:
        ol = _tinted(mask, outline)
        for a in range(12):
            ang = a / 12 * math.tau
            out.blit(ol, (pad + round(math.cos(ang) * ow), pad + round(math.sin(ang) * ow)))
    out.blit(_tinted(mask, color), (pad, pad))
    return out


def text3d(s, px, top, bottom, side, outline=(20, 12, 8), depth=None, bevel=True):
    """Big extruded letters: a gradient face, a deep shaded side and a dark outline."""
    mask = _mask(s, px)
    w, h = mask.get_size()
    depth = depth if depth is not None else max(2, px // 8)
    ow = max(2, px // 16)
    pad = ow + 2
    out = pygame.Surface((w + pad * 2 + depth, h + pad * 2 + depth), pygame.SRCALPHA)
    ol = _tinted(mask, outline)
    for k in range(depth, -1, -2):
        for a in range(8):
            ang = a / 8 * math.tau
            out.blit(ol, (pad + k * 0.5 + round(math.cos(ang) * ow), pad + k + round(math.sin(ang) * ow)))
    for k in range(depth, 0, -1):
        c = mix(side, (0, 0, 0), k / depth * 0.55)
        out.blit(_tinted(mask, c), (pad + k * 0.5, pad + k))
    face = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(h):
        c = mix(top, bottom, y / max(1, h - 1))
        pygame.draw.line(face, (c[0], c[1], c[2], 255), (0, y), (w, y))
    face.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    out.blit(face, (pad, pad))
    if bevel:                                   # a bright lip along the top edges
        lip = mask.copy()
        lip.blit(mask, (0, max(1, px // 24)), special_flags=pygame.BLEND_RGBA_SUB)
        lip.fill((255, 255, 255, 170), special_flags=pygame.BLEND_RGBA_MULT)
        out.blit(lip, (pad, pad))
    return out


def shine(img, x0, width=None, alpha=150):
    """A diagonal glint sweeping across img (only where img is opaque). Returns a new surface."""
    w, h = img.get_size()
    width = width or max(8, h // 2)
    band = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.polygon(band, (255, 255, 255, alpha),
                        [(x0, 0), (x0 + width, 0), (x0 + width - h * 0.6, h), (x0 - h * 0.6, h)])
    m = img.copy()
    m.fill((255, 255, 255, 255), special_flags=pygame.BLEND_RGB_MAX)     # white, img's alpha
    band.blit(m, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    out = img.copy()
    out.blit(band, (0, 0))
    return out


def gradient(w, h, stops, alpha=False):
    """Vertical gradient through (fraction, colour) stops."""
    s = pygame.Surface((w, h), pygame.SRCALPHA if alpha else 0)
    for y in range(h):
        f = y / max(1, h - 1)
        c = stops[-1][1]
        for (f0, c0), (f1, c1) in zip(stops, stops[1:]):
            if f0 <= f <= f1:
                c = mix(c0, c1, (f - f0) / ((f1 - f0) or 1))
                break
        pygame.draw.line(s, c, (0, y), (w, y))
    return s


_soft_cache = {}


def soft_sprite(img, scale):
    """Enlarge pixel art for the hi-res canvas with softened edges (no big jaggy pixels)."""
    w, h = max(2, int(img.get_width() * scale)), max(2, int(img.get_height() * scale))
    key = (id(img), w, h)
    s = _soft_cache.get(key)
    if s is None:
        big = pygame.transform.scale(img, (img.get_width() * 4, img.get_height() * 4))
        s = pygame.transform.smoothscale(big, (w, h))
        if len(_soft_cache) > 300:
            _soft_cache.clear()
        _soft_cache[key] = s
    return s


# ======================================================================
# models
# ======================================================================
def render(surf, items):
    """Draw (depth, fn) items back to front."""
    items.sort(key=lambda it: -it[0])
    for _, fn in items:
        fn(surf)


def _ballfn(col, x, y, rx, ry=None, gloss=1.0):
    def fn(surf):
        img = ball(col, rx, ry, gloss)
        surf.blit(img, (int(x - img.get_width() / 2), int(y - img.get_height() / 2)))
    return fn


class Turtle3D:
    """A round, friendly turtle: a patterned shell dome, a head, four flippers and a stubby tail."""
    _shells = {}

    def __init__(self, shell=(80, 150, 90), skin=(150, 210, 140), scute=None, hat=None, beard=False, specs=False):
        self.shell, self.skin = tuple(shell), tuple(skin)
        self.scute = scute or mix(self.shell, (0, 0, 0), 0.4)
        self.hat = hat
        self.beard = beard
        self.specs = specs

    def _shell_img(self, rx, ry):
        key = (self.shell, self.scute)
        base = Turtle3D._shells.get(key)
        if base is None:
            base = _colored(self.shell, 0.8).copy()
            pat = pygame.Surface(base.get_size(), pygame.SRCALPHA)
            c = (*self.scute, 170)
            n = R0 * 2
            for row in range(-2, 3):                  # a honeycomb of scutes, bulging with the dome
                for col in range(-3, 4):
                    hx = n / 2 + col * 26 + (13 if row % 2 else 0)
                    hy = n / 2 + row * 22
                    pts = [(hx + math.cos(a) * 12, hy + math.sin(a) * 11) for a in
                           (i / 6 * math.tau + math.pi / 6 for i in range(6))]
                    pygame.draw.polygon(pat, c, pts, 3)
            pat.blit(base, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            base.blit(pat, (0, 0))
            Turtle3D._shells[key] = base
        k = ('turtleshell', key, int(rx), int(ry))
        s = _ball_cache.get(k)
        if s is None:
            s = pygame.transform.smoothscale(base, (max(2, int(rx) * 2), max(2, int(ry) * 2)))
            _ball_cache[k] = s
        return s

    def items(self, pos, yaw=0.0, pitch=0.0, t=0.0, size=1.0, walk=0.0, blink=False, cx=W / 2, cy=H / 2):
        m = rot(yaw, pitch)
        px, py, pz = pos
        out = []
        sx, sy, k = project(px, py, pz, cx, cy)
        rx, ry = size * 1.25 * k, size * 0.82 * k
        belly = mix(self.skin, (255, 240, 190), 0.5)

        def shellfn(surf, sx=sx, sy=sy, rx=rx, ry=ry):
            b = ball(belly, rx * 0.98, ry * 0.42, 0.4)
            surf.blit(b, (sx - b.get_width() / 2, sy + ry * 0.48 - b.get_height() / 2))
            img = self._shell_img(rx, ry)
            surf.blit(img, (sx - img.get_width() / 2, sy - img.get_height() / 2))
        out.append((pz, shellfn))
        # flippers
        for fx_, fz_, ph in ((-1, -1, 0.0), (1, -1, math.pi), (-1, 1, math.pi), (1, 1, 0.0)):
            paddle = math.sin(t * 0.18 + ph) * walk
            lx, ly, lz = apply(m, fx_ * 1.0 * size, (0.55 + 0.08 * paddle) * size, (fz_ * 0.62 + 0.12 * paddle) * size)
            x3, y3, z3 = px + lx, py + ly, pz + lz
            qx, qy, kk = project(x3, y3, z3, cx, cy)
            out.append((z3, _ballfn(self.skin, qx, qy, size * 0.34 * kk, size * 0.22 * kk, 0.6)))
        # tail
        tx, ty, tz = apply(m, 0, 0.45 * size, 1.15 * size)
        qx, qy, kk = project(px + tx, py + ty, pz + tz, cx, cy)
        out.append((pz + tz, _ballfn(self.skin, qx, qy, size * 0.14 * kk)))
        # head, poking out at the front
        bob = math.sin(t * 0.07) * 0.04 * size
        hx, hy, hz = apply(m, 0, (0.05 * size + bob), -1.18 * size)
        x3, y3, z3 = px + hx, py + hy, pz + hz
        qx, qy, kk = project(x3, y3, z3, cx, cy)
        hr = size * 0.44 * kk
        out.append((z3, _ballfn(self.skin, qx, qy, hr, hr * 0.95, 0.7)))
        # the face looks the way the head points
        fwd = apply(m, 0, 0, -1)
        if fwd[2] < -0.15:
            fore = -fwd[2]
            side = fwd[0]
            pupil = (14, 14, 26)
            ew, eh = hr * 0.42 * fore, hr * 0.5
            if blink:
                eh *= 0.12
            spots = [(qx + (dx * hr * 0.42) * fore + side * hr * 0.4, qy - hr * 0.15) for dx in (-1, 1)]
            beard, specs, lw = self.beard, self.specs, max(1, int(hr * 0.08))

            def face(surf, spots=spots, ew=ew, eh=eh, qx=qx, qy=qy, hr=hr, side=side):
                for ex, ey in spots:
                    img = eye(pupil, ew, eh)
                    surf.blit(img, (ex - img.get_width() / 2, ey - img.get_height() / 2))
                    if specs:
                        pygame.draw.circle(surf, (40, 30, 20), (int(ex), int(ey)), int(max(ew, eh) * 0.62), lw)
                if specs:
                    pygame.draw.line(surf, (40, 30, 20), spots[0], spots[1], lw)
                mx = qx + side * hr * 0.4
                pygame.draw.arc(surf, (40, 26, 20), (mx - hr * 0.32, qy + hr * 0.05, hr * 0.64, hr * 0.42),
                                math.pi * 1.1, math.pi * 1.9, lw)
                if beard:
                    pts = [(mx - hr * 0.35, qy + hr * 0.45), (mx + hr * 0.35, qy + hr * 0.45), (mx, qy + hr * 1.25)]
                    pygame.draw.polygon(surf, (240, 240, 236), pts)
            out.append((z3 - size * 0.5, face))
        if self.hat is not None:
            tx, ty, tz = apply(m, 0, -0.42 * size + bob, -1.18 * size)
            qx2, qy2, kk2 = project(px + tx, py + ty, pz + tz, cx, cy)
            img = soft_sprite(self.hat, size * kk2 * 1.0 / 12)

            def hatfn(surf, img=img, qx2=qx2, qy2=qy2):
                surf.blit(img, (qx2 - img.get_width() / 2, qy2 - img.get_height() + img.get_height() * 0.35))
            out.append((pz + tz - size, hatfn))
        return out
