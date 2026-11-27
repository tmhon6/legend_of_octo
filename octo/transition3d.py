"""Changing scene in 3D: diving through one picture into the next.

The picture we're leaving rushes towards the camera and fades as we swim through it, with bubbles
streaming past. The new scene comes up out of the deep water behind it; when the game itself starts,
the sea floor is first seen tilted away in 3D and swings up flat under us.

Used from the opening into the title screen, and from the title screen into the game. A Dive is
drawn over the finished frame in Game.present(). A GeyserRide is drawn the same way, when a geyser
blasts Octo up to the sky islands (or he drops back down to the sea).
"""
import math
import random

import pygame

_bg = {}


def _smooth(k):
    return k * k * (3 - 2 * k)


def _deep(w, h):
    """Deep water behind the new scene while it's still far off."""
    img = _bg.get((w, h))
    if img is None:
        img = pygame.Surface((w, h))
        for y in range(h):
            f = y / max(1, h - 1)
            c = (int(8 + 14 * (1 - f)), int(26 + 40 * (1 - f)), int(60 + 50 * (1 - f)))
            pygame.draw.line(img, c, (0, y), (w, y))
        _bg[(w, h)] = img
    return img


class Dive:
    def __init__(self, old, length=50, tilt=False, hi=3):
        # In the browser (hi 2) the work is done at the pixel art's own size, a quarter of the
        # pixels, and scaled up once at the end: the ground art loses nothing and it stays smooth.
        self.q = 2 if hi <= 2 else 1
        w, h = old.get_size()
        self.old = old if self.q == 1 else pygame.transform.scale(old, (w // self.q, h // self.q))
        self.length, self.tilt, self.hi = length, tilt, hi
        self.t = 0
        rnd = random.Random()
        self.bubbles = [(rnd.uniform(0, math.tau), rnd.uniform(0.25, 1.25), rnd.uniform(0.6, 1.1))
                        for _ in range(12)]

    @property
    def done(self):
        return self.t >= self.length

    def apply(self, area):
        """Draw this frame of the dive over the finished picture in area (a window subsurface)."""
        k = min(1.0, self.t / self.length)
        self.t += 1
        if self.q == 1:
            self._frame(area, k)
        else:
            W, H = area.get_size()
            small = pygame.transform.scale(area, (W // self.q, H // self.q))
            self._frame(small, k)
            pygame.transform.scale(small, (W, H), area)

    def _frame(self, area, k):
        W, H = area.get_size()
        if self.tilt:
            new = area.copy()
            area.blit(_deep(W, H), (0, 0))
            self._tilted(area, new, _smooth(k))                 # (still well tilted once the old picture's gone)
        if k < 0.42:                                        # the old picture rushing past us
            f = k / 0.42
            s = 1 + 2.2 * f * f
            w, h = int(W / s), int(H / s)
            part = self.old.subsurface(((W - w) // 2, (H - h) // 2, w, h))
            img = pygame.transform.scale(part, (W, H))
            img.set_alpha(int(255 * (1 - f) ** 1.4))
            area.blit(img, (0, 0))
        self._bubbles(area, k)

    def _tilted(self, area, new, e):
        """The new picture as a slab tilted back in 3D (top far away), swinging up flat as e goes to 1."""
        W, H = area.get_size()
        th = (1 - e) * 1.05                                 # tilt: about 60 degrees at the start
        d = 1.7 * H                                         # how far the camera is
        back = (1 - e) * 0.55 * H                           # and how far back the slab starts
        cy = H / 2 + (1 - e) * 0.12 * H
        bands = 44
        edges = []
        for i in range(bands + 1):
            y = i * H / bands - H / 2
            z = back - y * math.sin(th)
            s = d / (d + z)
            edges.append((cy + y * math.cos(th) * s, s))
        for i in range(bands):
            y0, y1 = int(i * H / bands), int((i + 1) * H / bands)
            (t0, s0), (t1, s1) = edges[i], edges[i + 1]
            top, bot = int(t0), int(t1 + 1)
            if bot - top < 1 or y1 <= y0:
                continue
            s = (s0 + s1) / 2
            w = max(1, int(W * s))
            band = pygame.transform.scale(new.subsurface((0, y0, W, y1 - y0)), (w, bot - top))
            fog = int(255 * min(1.0, 0.45 + 0.55 * s))      # far rows fade into the water
            if fog < 255:
                band.fill((fog, fog, min(255, fog + 18)), special_flags=pygame.BLEND_RGB_MULT)
            area.blit(band, ((W - w) // 2, top))

    def _bubbles(self, area, k):
        """Bubbles streaming past the camera as we swim forwards."""
        W, H = area.get_size()
        cx, cy = W / 2, H / 2
        fade = 1 - k
        hi = self.hi / self.q
        n = int(len(self.bubbles) * min(1.0, 1.2 - k))       # fewer and fewer as we arrive
        for a, z0, size in self.bubbles[:n]:
            z = (z0 - k * 1.5) % 1.25 + 0.06                 # how far off: getting closer all the time
            r = size * hi * 1.4 / z
            if r > 16 * hi:
                continue
            dist = W * 0.07 / z
            x, y = cx + math.cos(a) * dist, cy + math.sin(a) * dist * 0.8
            if not (-r < x < W + r and -r < y < H + r):
                continue
            c = (int(170 + 70 * fade), int(215 + 35 * fade), 255)
            pygame.draw.circle(area, c, (x, y), max(1, r), max(1, int(hi * 0.6)))
            pygame.draw.circle(area, (255, 255, 255), (x - r * 0.35, y - r * 0.35), max(1, r * 0.22))


def _grad(key, w, h, top, bottom):
    """A top-to-bottom gradient (one column worked out, then stretched: quick)."""
    img = _bg.get((key, w, h))
    if img is None:
        strip = pygame.Surface((1, h))
        for y in range(h):
            f = y / max(1, h - 1)
            strip.set_at((0, y), tuple(int(a + (b - a) * f) for a, b in zip(top, bottom)))
        img = _bg[(key, w, h)] = pygame.transform.scale(strip, (w, h))
    return img


def _cloud(r):
    """A soft cloud puff (see-through at the edges)."""
    img = _bg.get(('cloud', r))
    if img is None:
        img = pygame.Surface((r * 4, r * 2), pygame.SRCALPHA)
        for cx, cy, k in ((r * 1.2, r * 1.15, 0.75), (r * 2.0, r * 0.95, 0.95), (r * 2.8, r * 1.2, 0.7)):
            for i in range(6, 0, -1):
                rr = r * k * i / 6
                pygame.draw.circle(img, (255, 255, 255, 42), (cx, cy), rr)
        _bg[('cloud', r)] = img
    return img


class GeyserRide:
    """Riding a geyser. Going up: the sea floor drops away as the water blasts Octo upwards past
    streaming bubbles, he bursts out through the bright surface in a spray of water, clouds rush
    past, and the sky island comes down to meet him. Going down, the same the other way: falling
    through the clouds, a splash, and down through the water onto the sea floor."""

    def __init__(self, old, up=True, hi=3, length=84):
        self.q = 2 if hi <= 2 else 1
        w, h = old.get_size()
        self.old = old if self.q == 1 else pygame.transform.scale(old, (w // self.q, h // self.q))
        self.up, self.length, self.hi = up, length, hi
        self.t = 0
        rnd = random.Random()
        self.streaks = [(rnd.random(), rnd.random(), rnd.uniform(0.5, 1.0)) for _ in range(28)]
        self.clouds = [(rnd.random(), rnd.random(), rnd.uniform(0.7, 1.3)) for _ in range(8)]
        self.spray = [(rnd.uniform(-1, 1), rnd.uniform(0.4, 1.0), rnd.uniform(0.6, 1.4)) for _ in range(26)]

    @property
    def done(self):
        return self.t >= self.length

    def apply(self, area):
        k = min(1.0, self.t / self.length)
        self.t += 1
        if self.q == 1:
            self._frame(area, k)
        else:
            W, H = area.get_size()
            small = pygame.transform.scale(area, (W // self.q, H // self.q))
            self._frame(small, k)
            pygame.transform.scale(small, (W, H), area)

    def _frame(self, area, k):
        W, H = area.get_size()
        d = 1 if self.up else -1                  # which way the world streams past (down when rising)
        hi = self.hi / self.q
        water = _grad('water', W, H, (96, 196, 240), (8, 36, 86))
        sky = _grad('sky', W, H, (84, 156, 236), (206, 232, 255))
        first, then = (water, sky) if self.up else (sky, water)
        if k < 0.45:                              # leaving: the old place streams away
            f = k / 0.45
            area.blit(first, (0, 0))
            if self.up:                           # up through the water on the geyser's jet
                self._streaks(area, f, d, hi, bubbles=True)
            else:                                 # down through the clouds
                self._clouds(area, f, d, hi)
            off = int(H * 1.15 * f * f) * d
            area.blit(self.old, (0, off))
            if self.up:
                self._column(area, hi, 0.4 + 0.6 * f)
        elif k < 0.6:                             # through the surface
            g = (k - 0.45) / 0.15
            y = int(H * g) if self.up else int(H * (1 - g))
            top, bot = (then, first) if self.up else (first, then)
            area.blit(top, (0, 0), (0, 0, W, y))
            area.blit(bot, (0, y), (0, y, W, H - y))
            pygame.draw.rect(area, (240, 252, 255), (0, y - 3 * hi, W, 6 * hi))
            self._spray(area, g, y, hi)
            flash = int(110 * max(0.0, 1 - abs(g - 0.5) * 3))
            if flash:
                veil = pygame.Surface((W, H))
                veil.fill((255, 255, 255))
                veil.set_alpha(flash)
                area.blit(veil, (0, 0))
        else:                                     # arriving: the new place comes to meet us
            h = (k - 0.6) / 0.4
            e = 1 - (1 - h) ** 3
            new = area.copy()
            area.blit(then, (0, 0))
            if self.up:
                self._clouds(area, 1 - e, d, hi)
            else:
                self._streaks(area, 1 - e, d, hi, bubbles=True)
            area.blit(new, (0, int(-H * (1 - e)) * d))

    def _streaks(self, area, speed, d, hi, bubbles):
        """Bubbles (or wisps of cloud) streaming past, faster and longer the faster we go."""
        W, H = area.get_size()
        for x, y, sp in self.streaks:
            yy = ((y + self.t * 0.02 * sp * (1 + 4 * speed) * d) % 1.0) * H
            ln = (6 + 34 * speed) * hi * sp
            xx = x * W
            c = (200, 236, 255) if bubbles else (255, 255, 255)
            pygame.draw.line(area, c, (xx, yy), (xx, yy - ln * d), max(1, int(hi * 0.8)))
            if bubbles:
                pygame.draw.circle(area, (236, 250, 255), (xx, yy), max(1, hi * 1.2 * sp), max(1, int(hi * 0.5)))

    def _column(self, area, hi, strength):
        """The geyser's water rushing up the middle of the view."""
        W, H = area.get_size()
        band = _bg.get(('column', W, H))
        if band is None:
            bw = int(W * 0.24)
            row = pygame.Surface((bw, 1), pygame.SRCALPHA)
            for x in range(bw):
                f = 1 - abs(x - bw / 2) / (bw / 2)
                row.set_at((x, 0), (230, 248, 255, int(140 * f ** 1.5)))
            band = _bg[('column', W, H)] = pygame.transform.scale(row, (bw, H))
        band.set_alpha(int(255 * strength))
        area.blit(band, ((W - band.get_width()) // 2, 0))

    def _spray(self, area, g, y, hi):
        W, H = area.get_size()
        for sx, sp, sz in self.spray:
            r = g * W * 0.5 * sp
            px = W / 2 + sx * r
            py = y - (1 - (sx * sx)) * r * 0.5 * (1 if self.up else -1)
            pygame.draw.circle(area, (236, 250, 255), (px, py), max(1, hi * 1.6 * sz))

    def _clouds(self, area, speed, d, hi):
        W, H = area.get_size()
        for x, y, sc in self.clouds:
            img = _cloud(max(4, int(14 * hi * sc)))
            yy = ((y + self.t * 0.012 * sc * (0.2 + 3 * speed) * d) % 1.3 - 0.15) * H
            area.blit(img, (x * W - img.get_width() / 2, yy - img.get_height() / 2))
