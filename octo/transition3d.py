"""Changing scene in 3D: diving through one picture into the next.

The picture we're leaving rushes towards the camera and fades as we swim through it, with bubbles
streaming past. The new scene comes up out of the deep water behind it; when the game itself starts,
the sea floor is first seen tilted away in 3D and swings up flat under us.

Used from the opening into the title screen, and from the title screen into the game. A Dive is
drawn over the finished frame in Game.present().
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
        self.old = old                  # the picture we're leaving (the game area of the window)
        self.length, self.tilt, self.hi = length, tilt, hi
        self.t = 0
        rnd = random.Random()
        self.bubbles = [(rnd.uniform(0, math.tau), rnd.uniform(0.25, 1.25), rnd.uniform(0.7, 1.5))
                        for _ in range(44)]

    @property
    def done(self):
        return self.t >= self.length

    def apply(self, area):
        """Draw this frame of the dive over the finished picture in area (a window subsurface)."""
        k = min(1.0, self.t / self.length)
        self.t += 1
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
        hi = self.hi
        n = int(len(self.bubbles) * min(1.0, 1.2 - k))       # fewer and fewer as we arrive
        for a, z0, size in self.bubbles[:n]:
            z = (z0 - k * 1.5) % 1.25 + 0.06                 # how far off: getting closer all the time
            r = size * hi * 1.4 / z
            if r > 26 * hi:
                continue
            dist = W * 0.07 / z
            x, y = cx + math.cos(a) * dist, cy + math.sin(a) * dist * 0.8
            if not (-r < x < W + r and -r < y < H + r):
                continue
            c = (int(170 + 70 * fade), int(215 + 35 * fade), 255)
            pygame.draw.circle(area, c, (x, y), max(1, r), max(1, int(hi * 0.6)))
            pygame.draw.circle(area, (255, 255, 255), (x - r * 0.35, y - r * 0.35), max(1, r * 0.22))
