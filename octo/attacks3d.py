"""Attacks in 3D, in the same pixel style as 3D Octo and Pebble.

Solid things (ink drops, slime, spines, ice shards, stars, shells, lanterns, bombs, enemy shots,
smoke puffs, Octo's slap...) are their pixel art turned into little lit cubes, the way Octo himself
is made. They fly at body height with a soft shadow on the sea floor beneath them, and they sort in
front of or behind Octo, Pebble and the buildings like everything else in 3D.

Rings, beams, bolts, the whip and whirlpools are drawn as glowing bands and tubes with height: a lit
part up in the water and a faint copy on the floor beneath it.

Positions: a flying thing is drawn where its flat pixel art was (so hits still land where they look
like they do); its shadow falls KZ * FLY further down the screen, where its spot on the floor is.
"""
import math

import pygame

import forms
import gfx
import hifi
import props3d
import voxel
from settings import HI

KX, KZ = props3d.KX, props3d.KZ
FLY = 6.0                       # how high shots fly above the floor (about Octo's middle)
TAU = math.tau
_cache = {}                     # quick-to-make images: shadows, glows, balls, fire
_arts = {}                      # the cube renders, kept apart so the quick ones never push them out


def _keep(key, val):
    if len(_cache) > 2500:
        _cache.clear()
    _cache[key] = val
    return val


def _q(c, step=8):
    """A colour rounded, so slowly changing colours don't fill the caches."""
    return tuple(min(255, int(v) // step * step) for v in c[:3])


# ======================================================================
# building blocks
# ======================================================================
def art(key, make, depth=3.0, ball=True, yaw=0.3):
    """A small pixel sprite (made by make()) as 3D cubes: (image, (cx, cy), (w, h)) where (cx, cy)
    is the middle of the sprite in the image and (w, h) the sprite's size in game pixels."""
    out = _arts.get(key)
    if out is None:
        spr = make()
        w, h = spr.get_size()
        cells = voxel._profile_cells(spr, None, depth=depth, ball=ball)
        img, (ax, ay) = voxel.render(voxel.VoxelModel(cells), HI, yaw, 0.6)
        cx = ax - (HI / 2 if w % 2 == 0 else 0)
        if len(_arts) > 900:
            _arts.clear()
        out = _arts[key] = (img, (cx, ay - h * HI / 2), (w, h))
    return out


def _canvas(w, h):
    return pygame.Surface((w, h), pygame.SRCALPHA)


def _shadow_img(w, a):
    key = ('sh', w, a)
    img = _cache.get(key)
    if img is None:
        W, H = max(2, int(w * HI)), max(2, int(w * HI * 0.42))
        img = _canvas(W, H)
        for i, k in enumerate((1.0, 0.78, 0.55)):          # soft edge: darker towards the middle
            pygame.draw.ellipse(img, (0, 4, 18, int(a * (0.4 + 0.3 * i))),
                                (W * (1 - k) / 2, H * (1 - k) / 2, W * k, H * k))
        img = _keep(key, img)
    return img


def _glow_img(col, r):
    key = ('gl', col, r)
    img = _cache.get(key)
    if img is None:
        img = _canvas(r * 2 + 2, r * 2 + 2)
        steps = max(3, min(10, r // 2))
        for i in range(steps):
            rr = int(r * (1 - i / steps))
            a = int(110 * ((i + 1) / steps) ** 1.6)
            pygame.draw.circle(img, col + (a,), (r + 1, r + 1), max(1, rr))
        img = _keep(key, img)
    return img


def _fire_img(r):
    """A ball of fire: glowing all through, white-hot in the middle, soft at the edge."""
    key = ('fire', r)
    img = _cache.get(key)
    if img is None:
        img = _canvas(r * 2 + 2, r * 2 + 2)
        steps = max(4, min(14, r // 2))
        for i in range(steps):
            k = i / (steps - 1)                                   # 0 at the edge, 1 in the middle
            col = tuple(int(a + (b - a) * k) for a, b in zip((255, 96, 24), (255, 248, 210)))
            pygame.draw.circle(img, col + (int(110 + 145 * k),), (r + 1, r + 1), max(1, int(r * (1 - 0.85 * k))))
        img = _keep(key, img)
    return img


def _ball_img(col, r, alpha=255):
    """A smooth shaded ball (for soft round things: the rain cloud, fog, ink-jet puffs)."""
    key = ('ball', col, r, alpha)
    img = _cache.get(key)
    if img is None:
        img = hifi.ball(col, r)
        if alpha < 255:
            img = img.copy()
            img.set_alpha(alpha)
        img = _keep(key, img)
    return img


class Ctx:
    """Where to draw this frame: the game, the hi-res layer, screen shake and how high the
    pyramid lifts the thing being drawn."""

    def __init__(self, g, hr, shake):
        self.g, self.hr, self.shake, self.h = g, hr, shake, 0.0
        self.half = None                # 'back' / 'front': only that half of a ring round Octo

    def wants(self, s):
        """Is a piece of ring at sin(angle) = s in the half being drawn? (back = the north side)"""
        return self.half is None or (s < 0) == (self.half == 'back')

    def at(self, x, y, z=0.0):
        """Hi-res point for the flat-art point (x, y), raised z (and by the pyramid, if on it)."""
        zz = z + self.h
        return self.g._hr(x - KX * zz, y - KZ * zz, self.shake)

    def floor(self, x, y, fly=FLY):
        """Where the shadow of something drawn at (x, y) and flying fly up falls."""
        return self.at(x + KX * fly, y + KZ * fly)

    def put(self, a, x, y, alpha=None, sx=1.0, sy=1.0):
        img, (cx, cy), _ = a
        if sx != 1.0 or sy != 1.0:
            img = pygame.transform.scale(img, (max(1, int(img.get_width() * sx)), max(1, int(img.get_height() * sy))))
            cx, cy = cx * sx, cy * sy
        if alpha is not None and alpha < 255:
            img = img.copy()
            img.set_alpha(max(0, int(alpha)))
        self.hr.blit(img, (round(x - cx), round(y - cy)))

    def stand(self, a, x, y, **kw):
        """Put a sprite-art thing standing on the floor point (x, y) (its bottom there)."""
        self.put(a, x, y - a[2][1] * HI / 2, **kw)

    def shadow(self, x, y, w, fly=FLY, a=85):
        sx, sy = self.floor(x, y, fly)
        img = _shadow_img(max(2, int(w)), a)
        self.hr.blit(img, (round(sx - img.get_width() / 2), round(sy - img.get_height() / 2)))

    def glow(self, col, x, y, r):
        img = _glow_img(_q(col), max(2, int(r * HI)))
        self.hr.blit(img, (round(x - img.get_width() / 2), round(y - img.get_height() / 2)))

    def ball(self, col, x, y, r, alpha=255):
        img = _ball_img(_q(col), max(1, int(r * HI)), int(alpha) // 16 * 16 if alpha < 255 else 255)
        self.hr.blit(img, (round(x - img.get_width() / 2), round(y - img.get_height() / 2)))

    def fire(self, x, y, r, alpha=255):
        img = _fire_img(max(2, int(r * HI)))
        if alpha < 255:
            img = img.copy()
            img.set_alpha(max(0, int(alpha)))
        self.hr.blit(img, (round(x - img.get_width() / 2), round(y - img.get_height() / 2)))

    def cube(self, col, x, y, size=1):
        s = max(1, int(HI * size))
        img = voxel._cube(_q(col, 4), s, s, max(1, s // 3), 0)
        self.hr.blit(img, (round(x - s / 2), round(y - s / 2 - max(1, s // 3))))

    def line(self, col, a, b, w=1.0):
        pygame.draw.line(self.hr, col, a, b, max(1, int(w * HI)))

    def lines(self, col, pts, w=1.0, closed=False):
        if len(pts) > 1:
            pygame.draw.lines(self.hr, col, closed, pts, max(1, int(w * HI)))


def _light(c, k=0.45):
    return tuple(min(255, int(v + (255 - v) * k)) for v in c)


def _dark(c, k=0.55):
    return tuple(int(v * k) for v in c)


# ======================================================================
# sprites for the solid things (pixel art, turned into cubes by art())
# ======================================================================
def _dot_spr(r, rim, fill, glint=None, w=None):
    w = w or r * 2 + 1
    s = _canvas(w, w)
    c = w // 2
    pygame.draw.circle(s, rim, (c, c), r)
    pygame.draw.circle(s, fill, (c, c), max(1, r - 1))
    if glint:
        s.set_at((c - max(1, r // 2), c - max(1, r // 2)), glint)
    return s


def _dir(vx, vy, n=16):
    """A direction rounded to one of n."""
    return round(math.atan2(vy, vx) / TAU * n) % n


def _shard_spr(i):
    a = i / 16 * TAU
    ux, uy = math.cos(a), math.sin(a)
    s = _canvas(13, 13)
    c = 6
    side = (-uy * 2.5, ux * 2.5)
    pts = [(c + ux * 5, c + uy * 5), (c + side[0], c + side[1]), (c - ux * 5, c - uy * 5), (c - side[0], c - side[1])]
    pygame.draw.polygon(s, (190, 236, 255), pts)
    pygame.draw.polygon(s, (255, 255, 255), pts, 1)
    return s


def _spine_spr(i):
    a = i / 16 * TAU
    ux, uy = math.cos(a), math.sin(a)
    s = _canvas(11, 11)
    c = 5
    pygame.draw.line(s, (120, 50, 0), (c - ux * 4, c - uy * 4), (c + ux * 3, c + uy * 3), 2)
    pygame.draw.line(s, (255, 220, 120), (c, c), (c + ux * 4, c + uy * 4))
    return s


def _star_spr(step, col):
    s = _canvas(13, 13)
    a = step / 6 * (TAU / 5)
    pts = [(6 + math.cos(a + i * math.pi / 5) * (5.5 if i % 2 == 0 else 2.2),
            6 + math.sin(a + i * math.pi / 5) * (5.5 if i % 2 == 0 else 2.2)) for i in range(10)]
    pygame.draw.polygon(s, (255, 255, 230), pts)
    pygame.draw.polygon(s, col, pts, 1)
    return s


def _shell_spr(step, col):
    s = _canvas(15, 15)
    a = step / 8 * (TAU / 3)
    pts = [(7 + math.cos(a + i * TAU / 3) * 6.5, 7 + math.sin(a + i * TAU / 3) * 6.5) for i in range(3)]
    pygame.draw.polygon(s, (120, 70, 50), pts)
    pygame.draw.polygon(s, col, pts, 2)
    pygame.draw.circle(s, (255, 240, 220), (7, 7), 2)
    return s


def _lantern_spr(col):
    s = _canvas(10, 13)
    pygame.draw.rect(s, (60, 40, 90), (1, 2, 8, 10))
    pygame.draw.rect(s, col, (2, 3, 6, 8))
    pygame.draw.rect(s, (255, 255, 240), (4, 5, 2, 4))
    pygame.draw.line(s, (60, 40, 90), (3, 0), (6, 0))
    pygame.draw.line(s, (60, 40, 90), (4, 0), (4, 2))
    return s


def _mine_spr(col, blink):
    s = _canvas(12, 9)
    pygame.draw.ellipse(s, (60, 20, 80), (0, 0, 12, 9))
    pygame.draw.ellipse(s, col, (1, 0, 10, 7))
    if blink:
        s.set_at((6, 3), (255, 255, 255))
    return s


def _crystal_spr(col):
    s = _canvas(9, 11)
    pts = [(4, 0), (8, 5), (4, 10), (0, 5)]
    pygame.draw.polygon(s, (240, 250, 255), pts)
    pygame.draw.polygon(s, col, pts, 1)
    return s


def _rock_spr(r, col=(110, 90, 60)):
    return _dot_spr(r, _dark(col, 0.75), col, _light(col, 0.3))


def _slap_spr(facing, cut):
    """Octo's slapping tentacle, as far out as it has reached (cut: how many pixels show)."""
    t = gfx.SLAP['mad'][facing]
    tw, th = t.get_size()
    if facing == 'right':
        return t.subsurface((tw - cut, 0, cut, th)).copy()
    if facing == 'left':
        return t.subsurface((0, 0, cut, th)).copy()
    if facing == 'down':
        return t.subsurface((0, th - cut, tw, cut)).copy()
    return t.subsurface((0, 0, tw, cut)).copy()


# ======================================================================
# the drawers: each takes the drawing context and the thing
# ======================================================================
def _ink(c, o):
    if o.wait:
        return
    x, y = o.x + 4, o.y + 4
    c.shadow(x, y, 6)
    c.put(art('ink', lambda: gfx.SPR['shots']['ink'], 3.2), *c.at(x, y))


def _slime(c, o):
    x, y = o.x + 3, o.y + 3
    c.shadow(x, y, 6)
    c.put(art('slime', lambda: _dot_spr(4, (90, 140, 50), (190, 235, 120), (250, 255, 230)), 3.2), *c.at(x, y))


def _shard(c, o):
    i = _dir(o.vx, o.vy)
    x, y = o.x + 4, o.y + 4
    c.shadow(x, y, 7)
    px, py = c.at(x, y)
    c.glow((150, 220, 255), px, py, 6)
    c.put(art(('shard', i), lambda: _shard_spr(i), 2.0, ball=False), px, py)


def _spine(c, o):
    i = _dir(o.vx, o.vy)
    x, y = o.x + 3, o.y + 3
    c.shadow(x, y, 4, a=55)
    c.put(art(('spine', i), lambda: _spine_spr(i), 1.6, ball=False), *c.at(x, y))


def _wisp(c, o):
    fl = 1 if (o.t // 3) % 2 else 0
    x, y = o.x + 4, o.y + 4
    c.shadow(x, y, 6, a=45)
    px, py = c.at(x, y)
    c.glow((170, 110, 255), px, py, 9 + fl)
    c.put(art(('wisp', fl), lambda: _dot_spr(4 + fl, (120, 70, 210), (160, 110, 240), (230, 210, 255), w=11), 3.0),
          px, py)


def _trap(c, o):
    x, y = o.x + 6, o.y + 6
    c.shadow(x, y, 10)
    px, py = c.at(x, y)
    c.put(art('trap', lambda: _dot_spr(6, (240, 250, 255), (180, 230, 255), (255, 255, 255)), 4.0), px, py, alpha=170)
    c.cube((255, 255, 255), px - 2.5 * HI, py - 2.5 * HI)


def _enemy_shot(c, o):
    k = o.kind
    if k == 'ember':
        if o.life is not None and o.life < 40 and (o.t // 3) % 2:
            return
        x, y = o.x + 5, o.y + 9                         # a little fire on the floor
        c.shadow(x, y, 9, fly=0, a=55)
        px, py = c.at(x, y)
        c.glow((255, 120, 40), px, py - 4 * HI, 9)
        yaw = 0.35 if (o.t // 4) % 2 else -0.35         # it flickers
        c.stand(art(('ember', yaw), lambda: gfx.SPR['shots']['ember'], 2.5, ball=False, yaw=yaw), px, py)
        return
    size = 10 if k == 'bubble' else 6
    x, y = o.x + size / 2, o.y + size / 2
    c.shadow(x, y, size)
    px, py = c.at(x, y)
    if k == 'bubble':
        wob = math.sin(o.t * 0.3) * HI
        c.put(art('ebubble', lambda: _dot_spr(5, (240, 220, 255), (200, 120, 255), (255, 255, 255)), 3.5),
              px + wob, py, alpha=175)
        return
    if k == 'ice':
        c.glow((150, 210, 255), px, py, 5)
    c.put(art(('eshot', k), lambda: gfx.SPR['shots'][k], 2.6), px, py)


def _bomb(c, o):
    x, y = o.x, o.y
    if o.t < o.FUSE:
        fast = o.t > 50
        lit = (o.t // (3 if fast else 8)) % 2
        c.shadow(x + 4.5, y + 10.5, 10, fly=0)
        px, py = c.at(x + 4.5, y + 11)
        if lit:
            c.glow((255, 120, 60), px, py - 6 * HI, 7)
        c.stand(art(('bomb', lit), lambda: gfx.SPR['items']['bomb_lit' if lit else 'bomb'], 3.4), px, py)
        return
    k = (o.t - o.FUSE) / 16
    cx, cy = x + 4, y + 5
    r = 8 + k * (o.RADIUS - 6)
    gx, gy = c.at(cx, cy + 4)                                 # the blast racing out along the floor
    pygame.draw.circle(c.hr, _light((255, 200, 100), 0.4 * (1 - k)), (gx, gy), int(r * HI), max(1, int(4 * (1 - k) * HI)))
    px, py = c.at(cx, cy, 4)
    if k < 0.8:                                               # a fireball, white-hot in the middle
        fr = r * 0.6 * (1 - k * 0.3)
        c.glow((255, 150, 60), px, py, fr * 1.8)
        c.fire(px, py, fr, alpha=255 * min(1.0, 1.7 * (1 - k)))


def _seeker(c, o):
    x, y = o.rect.center
    for i, (tx, ty) in enumerate(o.trail):
        px, py = c.at(tx, ty)
        c.cube(o.col, px, py, 1 if i < 3 else 1.5)
    c.shadow(x, y, 6, a=50)
    step = int(((o.life * 0.3) % (TAU / 5)) / (TAU / 5) * 6) % 6
    px, py = c.at(x, y)
    c.glow(o.col, px, py, 7)
    col = _q(o.col)
    c.put(art(('star', step, col), lambda: _star_spr(step, col), 2.2), px, py)


def _boomerang(c, o):
    x, y = o.rect.center
    c.shadow(x, y, 11)
    step = int(((o.t * 0.6) % (TAU / 3)) / (TAU / 3) * 8) % 8
    col = _q(o.col)
    c.put(art(('shell', step, col), lambda: _shell_spr(step, col), 2.6), *c.at(x, y))


def _orb(c, o):
    x, y = o.x + 5, o.y + 5
    c.shadow(x, y, 7, a=55)
    px, py = c.at(x, y)
    c.glow(o.col, px, py, 9)
    col = _q(o.col)
    c.put(art(('orb', col), lambda: _dot_spr(4, _dark(col, 0.7), col, (255, 255, 240)), 3.4), px, py)


def _lantern(c, o):
    x, y = o.x + 6, o.y + 6
    flick = 1 if (o.life // 4) % 2 else 0
    c.shadow(x, y, 9, a=55)
    px, py = c.at(x, y)
    c.glow(o.col, px, py, 12 + flick)
    col = _q(o.col)
    c.put(art(('lantern', col), lambda: _lantern_spr(col), 3.0, ball=False, yaw=0.35), px, py)


def _mine(c, o):
    x, y = o.x + 5, o.y + 10
    wob = math.sin(o.t * 0.15)
    blink = (o.t // 12) % 2
    c.shadow(x, y - 1, 12, fly=0, a=60)
    px, py = c.at(x, y)
    col = _q(o.col)
    c.stand(art(('mine', col, blink), lambda: _mine_spr(col, blink), 3.2), px, py, sx=1 - wob * 0.05, sy=1 + wob * 0.08)


def _boulder(c, o):
    x, y = o.rect.center
    c.shadow(x, y + 6, 18, fly=0, a=95)
    px, py = c.at(x, y)
    c.put(art('boulder', lambda: _rock_spr(8, (150, 135, 112)), 5.0), px, py)
    a = o.t * 0.25 * (1 if o.vx >= 0 else -1)              # cracks turning as it rolls
    for i in range(3):
        ex, ey = math.cos(a + i * 2.1), math.sin(a + i * 2.1)
        c.line((96, 84, 70), (px + ex * 1.5 * HI, py + ey * 1.5 * HI), (px + ex * 6 * HI, py + ey * 6 * HI), 0.6)
    if isinstance(o.elem, str) and o.elem in forms.ELEMENTS:
        pygame.draw.circle(c.hr, forms.ELEMENTS[o.elem][2], (px, py), int(8 * HI), max(1, HI // 2))


def _hail(c, o):
    if o.t < 0:
        return
    k = min(1.0, o.t / o.FALL)
    c.shadow(o.x, o.y, 4 + 10 * k, fly=0, a=int(40 + 70 * k))
    if o.t < o.FALL:
        px, py = c.at(o.x, o.y)
        py -= (1 - k) * 70 * HI
        c.glow(o.col, px, py, 8)
        c.line(o.col, (px - HI, py - 14 * HI), (px, py - 6 * HI), 0.7)
        col = _q(o.col)
        c.put(art(('hail', col), lambda: _crystal_spr(col), 2.2, ball=False, yaw=0.5), px, py)


def _cloud(c, o):
    x, y = o.x, o.y
    under = o.owner.rect.bottom
    c.shadow(x + 12, under, 26, fly=0, a=45)
    for d in o.drops:                                       # drops falling to their target
        px, py = c.at(d[0], d[1])
        c.line(_dark(o.col, 0.6), (px, py), (px, py + 4 * HI), 0.7)
        c.line(_light(o.col), (px - HI / 2, py), (px - HI / 2, py + 2 * HI), 0.4)
    for dx, r in ((5, 5), (19, 5), (12, 7)):
        px, py = c.at(x + dx, y + 5)
        c.ball((220, 226, 244), px, py, r)


def _quake(c, o):
    r = o.rect
    for i in (2, 1, 0):
        x, y = r.centerx - o.d[0] * i * 5, r.centery - o.d[1] * i * 5
        c.shadow(x, y + 3, 9 - i * 2, fly=0, a=60)
        rr = 5 - i
        c.stand(art(('rock', rr), lambda rr=rr: _rock_spr(rr), 2.6), *c.at(x, y + rr))
    px, py = c.at(r.centerx, r.centery)
    c.glow(o.col, px, py, 6)


def _particle(c, o):
    c.cube(o.color, *c.at(o.x, o.y), size=max(1, o.size) * (0.8 if o.size > 1 else 1))


def _puff(c, o):
    if o.t < 0:
        return
    f = min(3, o.t // 6)
    x, y = o.x + 8, o.y + 8
    c.put(art(('puff', f), lambda: gfx.SPR['puff'][f], 3.0), *c.at(x, y))


def _daze(c, o):
    r = o.e.rect
    for i in range(3):
        a = o.t * 0.2 + i * 2.1
        c.cube((255, 250, 150), *c.at(r.centerx + math.cos(a) * 7, r.top - 2 + math.sin(a) * 2))


def _ring_pts(cx, cy, r, n, jag=0.0, spin=0.0):
    return [(cx + math.cos(i / n * TAU + spin) * (r + (jag if i % 2 else -jag)),
             cy + math.sin(i / n * TAU + spin) * (r + (jag if i % 2 else -jag))) for i in range(n)]


def _zap(c, o):
    k = o.t / 14
    r = 8 + k * (o.RADIUS - 8)
    col = (255, 250, 160) if o.t % 4 < 2 else (120, 200, 255)
    n, spin = 24, o.t * 0.3
    pts = _ring_pts(o.x, o.y, r, n, 3, spin)
    low = [c.at(x + KX * FLY, y + KZ * FLY) for x, y in pts]     # on the floor
    high = [c.at(x, y) for x, y in pts]                         # up at Octo's middle
    w = 2 if k < 0.6 else 1
    for i in range(n):
        if not c.wants(math.sin((i + 0.5) / n * TAU + spin)):
            continue
        j = (i + 1) % n
        c.line(_dark(col, 0.5), low[i], low[j], 1)
        if i % 3 == 0 and math.sin(i / n * TAU + spin) > -0.3:   # sparks between the two
            c.line(_dark(col, 0.8), low[i], high[i], 0.5)
        c.line(col, high[i], high[j], w)
    if o.t < 4 and c.half != 'back':
        px, py = c.at(o.x, o.y)
        c.glow((255, 255, 200), px, py, 10)


def _nova(c, o):
    f = max(0.0, 1 - o.r / max(1, o.max_r))
    if f <= 0.02:
        return
    col = o.col
    gx, gy = o.x + KX * FLY, o.y + KZ * FLY
    n = max(24, int(o.r * 0.6))
    ring = [(gx + math.cos(i / n * TAU) * o.r, gy + math.sin(i / n * TAU) * o.r) for i in range(n)]
    low = [c.at(x, y) for x, y in ring]
    high = [c.at(x, y, 10) for x, y in ring]
    lo_col, hi_col = _dark(col, 0.4 + 0.4 * f), _light(col, 0.5 * f)
    walls = (_dark(col, 0.55 + 0.35 * f), _light(_dark(col, 0.8 + 0.2 * f), 0.15))
    for i in range(n):
        if not c.wants(math.sin((i + 0.5) / n * TAU)):
            continue
        j = (i + 1) % n
        c.line(lo_col, low[i], low[j], 1 + 2 * f)
        if math.sin(i / n * TAU) > -0.25:                         # the wall of force: a curtain of light
            c.line(walls[i % 2], low[i], high[i], 0.5 + 0.3 * f)
        c.line(hi_col, high[i], high[j], 1 + f)


def _whirl(c, o):
    cx, cy = o.rect.center
    px, py = c.at(cx, cy + 4)
    c.glow(o.col, px, py, 14)
    c.shadow(cx, cy + 6, 26, fly=0, a=40)
    for i in range(4):                                          # a spinning funnel, wider at the top
        r = 6 + i * 3
        z = i * 4
        qx, qy = c.at(cx, cy + 4, z)
        rect = pygame.Rect(qx - r * HI, qy - r * HI * 0.55, r * 2 * HI, r * 1.1 * HI)
        a = o.t * (0.25 + i * 0.1)
        pygame.draw.arc(c.hr, (220, 245, 255), rect, a, a + 3.6, max(1, HI if i < 3 else HI // 2 + 1))
        pygame.draw.arc(c.hr, o.col, rect, a + 3.14, a + 5.5, max(1, HI // 2 + 1))


def _beam(c, o):
    L = o.length
    x1, y1 = o.x0 + o.dx * L, o.y0 + o.dy * L
    w = max(1, 6 - o.t // 3)
    a0, a1 = c.at(o.x0 + KX * FLY, o.y0 + KZ * FLY), c.at(x1 + KX * FLY, y1 + KZ * FLY)
    c.line(_dark(o.col, 0.45), a0, a1, w * 0.6)                 # its light on the floor
    b0, b1 = c.at(o.x0, o.y0), c.at(x1, y1)
    c.line(_dark(o.col, 0.6), (b0[0], b0[1] + HI), (b1[0], b1[1] + HI), (w + 2) / 1.0)    # the tube's underside
    c.line(o.col, b0, b1, w + 1)
    c.line((255, 255, 255), (b0[0], b0[1] - HI * 0.6), (b1[0], b1[1] - HI * 0.6), max(0.5, w - 2.5))
    c.glow(o.col, b1[0], b1[1], 4 + w)
    c.glow((255, 255, 255), b0[0], b0[1], 3 + w)


def _bolt(c, o):
    for (x0, y0), (x1, y1) in zip(o.points, o.points[1:]):
        pts = [(x0, y0)]
        for i in range(1, 5):
            k = i / 5
            pts.append((x0 + (x1 - x0) * k + (math.sin(o.t * 7.1 + i * 3.3) * 4),
                        y0 + (y1 - y0) * k + (math.cos(o.t * 5.3 + i * 2.7) * 4)))
        pts.append((x1, y1))
        c.lines(_dark(o.col, 0.4), [c.at(x + KX * FLY, y + KZ * FLY) for x, y in pts], 1)
        hp = [c.at(x, y) for x, y in pts]
        c.lines(o.col, hp, 3 if o.t > 8 else 1.5)
        c.lines((255, 255, 255), hp, 0.7)


def _whip(c, o):
    cx, cy = o.owner.rect.center
    a = o.tip_angle()
    pts = []
    for i in range(9):
        r = o.REACH * i / 8
        bend = math.sin(i / 8 * math.pi) * 0.35
        pts.append((cx + math.cos(a - bend) * r, cy + math.sin(a - bend) * r))
    for x, y in pts[2::2]:
        c.shadow(x, y, 6, a=45)
    hp = [c.at(x, y, 2 * math.sin(i / 8 * math.pi)) for i, (x, y) in enumerate(pts)]   # it arcs up a little
    for i in range(8):                                          # thick at the root, thin at the tip
        w = 5 - i * 0.45
        c.line((20, 16, 50), hp[i], hp[i + 1], w)
    for i in range(8):
        w = 3.4 - i * 0.32
        c.line((70, 60, 150), hp[i], hp[i + 1], w)
    c.lines(_light(o.col, 0.3), [(x, y - HI * 0.7) for x, y in hp[3:]], 0.6)
    for x, y in hp[2::2]:                                       # suckers on the underside
        c.cube((230, 220, 255), x, y + HI)


def _impact(c, o):
    r = 3 + o.t * (2 if o.big else 1.4)
    f = max(0.0, 1 - o.t / (14 if o.big else 9))
    px, py = c.at(o.x, o.y)
    col = tuple(int(v * (0.5 + 0.5 * f)) for v in o.col)
    pygame.draw.circle(c.hr, col, (px, py), int(r * HI), max(1, int((2 if o.t < 4 else 1) * HI * 0.7)))
    if o.t < 3:
        c.glow((255, 255, 255), px, py, 6 - o.t)
    for ang, sp in o.sparks:
        d = o.t * sp
        c.cube((255, 255, 230), px + math.cos(ang) * d * HI, py + math.sin(ang) * d * HI)


def _inkcloud(c, o):
    import style
    r = o.radius()
    fade = 1 - max(0, o.t - 30) / 20
    c.shadow(o.x, o.y, r * 1.6, fly=0, a=int(50 * fade))
    for bx, by, k in sorted(o.blobs, key=lambda b: b[1]):
        rr = max(2, r * k * 0.7)
        px, py = c.at(o.x + bx * r / 16, o.y + by * r / 16, rr * 0.4)
        c.ball(style.dash_rgb(o.color, o.t + int(bx * 3)), px, py, rr, alpha=200 * fade)


DRAW = {
    'Ink': _ink, 'Slime': _slime, 'IceShard': _shard, 'Spine': _spine, 'Wisp': _wisp, 'TrapBubble': _trap,
    'EnemyShot': _enemy_shot, 'Bomb': _bomb, 'Seeker': _seeker, 'Boomerang': _boomerang, 'Orb': _orb,
    'Lantern': _lantern, 'Mine': _mine, 'Boulder': _boulder, 'Hail': _hail, 'RainCloud': _cloud,
    'Quake': _quake, 'Particle': _particle, 'Puff': _puff, 'Daze': _daze, 'ZapRing': _zap, 'Nova': _nova,
    'Whirlpool': _whirl, 'Beam': _beam, 'Bolt': _bolt, 'InkWhip': _whip, 'ImpactRing': _impact,
    'InkCloud': _inkcloud,
}


HALVES = ('ZapRing', 'Nova')


class Half:
    """The back or front half of a ring round Octo, so it can pass behind him and in front of him."""

    def __init__(self, o, back):
        self.o, self.back = o, back


def handles(o):
    return type(o).__name__ in DRAW


def halves(o):
    return type(o).__name__ in HALVES


def ground(o):
    """The thing's spot on the sea floor: where the pyramid would lift it, and (for most things)
    how it sorts among everything else in 3D."""
    n = type(o).__name__
    if n == 'Beam':
        return o.x0, o.y0 + KZ * FLY
    if n == 'Bolt':
        return o.points[0][0], o.points[0][1] + KZ * FLY
    if n == 'InkWhip':
        return o.owner.rect.centerx, o.owner.rect.bottom + 0.5
    if n == 'RainCloud':
        return o.x + 12, o.owner.rect.bottom + 0.5
    if n in ('Hail', 'InkCloud'):
        return o.x, o.y
    if n == 'Puff':
        return o.x + 8, o.y + 14
    if n in ('Bomb', 'Mine', 'Boulder', 'Quake', 'Whirlpool'):
        return o.rect.centerx, o.rect.bottom
    if n == 'Daze':
        x, y = o.e.rect.midtop
        return x, y + KZ * 3
    if n in ('ZapRing', 'Nova', 'ImpactRing', 'Particle'):
        return o.x, o.y + KZ * (FLY if n in ('ZapRing', 'Nova') else 3)
    if n == 'EnemyShot' and o.kind == 'ember':
        return o.x + 5, o.y + 9
    r = o.rect
    return r.centerx + KX * FLY, r.centery + KZ * FLY


def sort_y(o, gy):
    """How far down the floor it sorts: beams and bolts by the far end, so they cross over
    whatever they reach."""
    n = type(o).__name__
    if n == 'Beam':
        return max(o.y0, o.y0 + o.dy * o.length) + KZ * FLY
    if n == 'Bolt':
        return max(p[1] for p in o.points) + KZ * FLY
    return gy


# ======================================================================
# Octo's own attack bits: the slap, the bubble shield and fog, his shell shield, the spike roll
# ======================================================================
class Piece:
    """One of Octo's attack bits for this frame (sorted in with everything else)."""

    def __init__(self, kind, p):
        self.kind, self.p = kind, p


def octo_pieces(p):
    """What Octo shows besides himself this frame: [(sort key, Piece)]."""
    if p.invuln and (p.invuln // 3) % 2 and not p.knock_t:
        return []
    out = []
    b = p.rect.bottom
    if p.attack_t and p.mood == 'mad':
        out.append((b + {'down': 8, 'up': -8}.get(p.facing, 0.2), Piece('slap', p)))
    if p.fog_t:
        out.append((b + 0.4, Piece('fog', p)))
    if p.bubble_t and (p.bubble_t > 40 or (p.bubble_t // 4) % 2):
        out.append((b + 0.5, Piece('bubble', p)))
    if 'shield' in p.items and not p.dash_t and not p.flip_t and p.facing != 'up':
        out.append((b + 0.3, Piece('shield', p)))
    return out


def _piece(c, pc):
    p = pc.p
    x, y = round(p.x), round(p.y)
    if pc.kind == 'slap':                                    # placed exactly like the flat slap
        r = p.slap_rect()
        tw, th = gfx.SLAP['mad'][p.facing].get_size()
        ext = min(1.0, (16 - p.attack_t) / 4) if p.attack_t > 8 else p.attack_t / 8
        f = p.facing
        if f in ('left', 'right'):
            cut = max(1, int(tw * ext))
            tx, ty, w, h = (r.x - 2 if f == 'right' else r.right + 2 - cut), r.y + 13, cut, th
        else:
            cut = max(1, int(th * ext))
            tx, ty, w, h = r.x + 12, (r.y - 2 if f == 'down' else r.bottom + 2 - cut), tw, cut
        a = art(('slap', f, cut), lambda: _slap_spr(f, cut), 2.2, ball=False, yaw=0.25)
        c.put(a, *c.at(tx + w / 2, ty + h / 2))
    elif pc.kind == 'fog':
        t = p.fog_t
        for i in range(7):
            a = i / 7 * TAU + t * 0.03
            rr = 10 + math.sin(t * 0.07 + i) * 2
            px, py = c.at(x + 8 + math.cos(a) * rr, y + 9 + math.sin(a) * rr)
            c.ball((235, 240, 250), px, py, 6.5, alpha=120)
    elif pc.kind == 'bubble':
        px, py = c.at(x + 8, y + 9)
        img = hifi.bubble(13 * HI)
        c.hr.blit(img, (round(px - img.get_width() / 2), round(py - img.get_height() / 2)))
    elif pc.kind == 'shield':
        sx, sy = {'down': (3, 8), 'left': (-4, 5), 'right': (9, 5)}[p.facing]
        a = art(('shieldi', p.facing), lambda: gfx.SPR['items']['shield'], 2.0, ball=False, yaw=0.2)
        w, h = a[2]
        c.put(a, *c.at(x + sx + w / 2, y + sy + h / 2))


def draw_roll(c, p):
    """Prickly's spike roll: a spiky ball rolling along."""
    x, y = round(p.x) + 8, round(p.y) + 8
    px, py = c.at(x, y)
    spin = p.roll_t * 0.6
    for i in range(8):
        a = spin + i / 8 * TAU
        e0 = (px + math.cos(a) * 6 * HI, py + math.sin(a) * 6 * HI)
        e1 = (px + math.cos(a) * 11 * HI, py + math.sin(a) * 11 * HI)
        c.line((120, 60, 20), e0, e1, 2.4)
        c.line((255, 230, 150), e0, e1, 1.2)
    c.put(art('rollball', lambda: _dot_spr(8, (120, 60, 20), (250, 150, 60), (255, 220, 170)), 5.0), px, py)


def draw(g, hr, o, shake):
    c = Ctx(g, hr, shake)
    if isinstance(o, Piece):
        c.h = g.ground_height(o.p)
        _piece(c, o)
        return
    if isinstance(o, Half):
        c.half = 'back' if o.back else 'front'
        o = o.o
    gx, gy = ground(o)
    c.h = props3d.height_at(gx, gy)
    DRAW[type(o).__name__](c, o)
