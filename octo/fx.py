"""Visual polish that makes the sea feel real: caustic light, soft shadows, depth shading,
impact rings, swim bubbles and elemental auras. All drawn in code."""
import math
import random

import pygame

from settings import PLAY_H, PLAY_W

_cache = {}


# ---------------------------------------------------------------------------- caustics
def _caustic_tile(phase):
    """A 64x64 tile of rippling light, like sunlight through waves on the sea floor."""
    s = pygame.Surface((64, 64))
    for y in range(64):
        for x in range(64):
            v = (math.sin((x + phase * 3) * 0.29 + math.sin(y * 0.21 + phase) * 1.6) +
                 math.sin((y - phase * 2) * 0.33 + math.sin(x * 0.17 - phase) * 1.4))
            v = max(0.0, v - 1.15) * 30         # only the bright crests show
            s.set_at((x, y), (int(v * 0.8), int(v), int(v * 0.9)))
    return s


def caustics(ps, cam, t):
    """Shimmering light patterns drifting over the sea floor."""
    if 'caustic' not in _cache:
        _cache['caustic'] = [_caustic_tile(i * math.tau / 8) for i in range(8)]
    frames = _cache['caustic']
    tile = frames[(t // 9) % len(frames)]
    ox = -int(cam[0] * 0.9 + t * 0.15) % 64
    oy = -int(cam[1] * 0.9 + t * 0.1) % 64
    for y in range(oy - 64, PLAY_H, 64):
        for x in range(ox - 64, PLAY_W, 64):
            ps.blit(tile, (x, y), special_flags=pygame.BLEND_RGB_ADD)


# ---------------------------------------------------------------------------- shadows
def shadow(ps, rect, ox, oy, lift=0):
    """A soft oval shadow under something; lift raises the thing (flyers cast smaller, fainter shadows)."""
    w = max(8, rect.w + 2 - lift // 2)
    key = ('sh', w, lift > 0)
    img = _cache.get(key)
    if img is None:
        img = pygame.Surface((w, 6), pygame.SRCALPHA)
        a = 55 if lift else 80
        pygame.draw.ellipse(img, (0, 8, 24, a), (0, 0, w, 6))
        pygame.draw.ellipse(img, (0, 8, 24, a // 2), (1, 1, w - 2, 4))
        _cache[key] = img
    ps.blit(img, (rect.centerx - w // 2 + ox, rect.bottom - 3 + oy + lift))


# ---------------------------------------------------------------------------- depth shading
def depth_vignette(ps, strength=1.0):
    """Edges fall away into deeper, darker water."""
    key = ('vig', round(strength, 2))
    img = _cache.get(key)
    if img is None:
        img = pygame.Surface((PLAY_W, PLAY_H), pygame.SRCALPHA)
        cx, cy = PLAY_W / 2, PLAY_H / 2
        for i in range(18):
            k = 1 - i / 18
            a = int(70 * strength * k * k)
            pygame.draw.rect(img, (0, 6, 24, a), (i * 2, i * 2, PLAY_W - i * 4, PLAY_H - i * 4), 2)
        # a little more gloom towards the bottom: deeper water
        grad = pygame.Surface((PLAY_W, PLAY_H // 3), pygame.SRCALPHA)
        for y in range(PLAY_H // 3):
            pygame.draw.line(grad, (0, 6, 24, int(28 * strength * y / (PLAY_H // 3))), (0, y), (PLAY_W, y))
        img.blit(grad, (0, PLAY_H - PLAY_H // 3))
        _cache[key] = img
    ps.blit(img, (0, 0))


# ---------------------------------------------------------------------------- effects
class ImpactRing:
    """A quick white ring + spray where a hit lands."""

    def __init__(self, x, y, big=False, col=(255, 255, 255)):
        self.x, self.y = x, y
        self.t = 0
        self.big = big
        self.col = col
        self.dead = False
        self.sparks = [(random.uniform(0, math.tau), random.uniform(1.2, 2.6)) for _ in range(6 if big else 4)]

    def update(self, game):
        self.t += 1
        if self.t > (14 if self.big else 9):
            self.dead = True

    def draw(self, surf, ox=0, oy=0):
        x, y = int(self.x + ox), int(self.y + oy)
        r = 3 + self.t * (2 if self.big else 1.4)
        a = max(0, 255 - self.t * (18 if self.big else 26))
        ring = pygame.Surface((int(r) * 2 + 4, int(r) * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(ring, self.col + (a,), (int(r) + 2, int(r) + 2), int(r), 2 if self.t < 4 else 1)
        surf.blit(ring, (x - int(r) - 2, y - int(r) - 2))
        if self.t < 3:
            pygame.draw.circle(surf, (255, 255, 255), (x, y), 4 - self.t)
        for ang, sp in self.sparks:
            d = self.t * sp
            surf.set_at((int(x + math.cos(ang) * d), int(y + math.sin(ang) * d)), (255, 255, 230))


class SwimBubble:
    """A tiny bubble that wobbles up from Octo as he swims."""

    def __init__(self, x, y):
        self.x, self.y = x, y
        self.t = 0
        self.r = random.choice((1, 1, 2))
        self.ph = random.uniform(0, 6)
        self.dead = False

    def update(self, game):
        self.t += 1
        self.y -= 0.45
        self.x += math.sin(self.t * 0.2 + self.ph) * 0.25
        if self.t > 40:
            self.dead = True

    def draw(self, surf, ox=0, oy=0):
        x, y = int(self.x + ox), int(self.y + oy)
        pygame.draw.circle(surf, (200, 235, 255), (x, y), self.r, 1)
        if self.r > 1:
            surf.set_at((x - 1, y - 1), (255, 255, 255))


class AuraMote:
    """An elemental mote drifting off a fused form: frost sparkles, embers, sparks, glints..."""
    STYLE = {
        'freeze': ((210, 240, 255), (0, -0.25), 'spark'),
        'burn': ((255, 150, 60), (0, -0.55), 'dot'),
        'stun': ((255, 250, 150), (0, -0.3), 'star'),
        'heavy': ((170, 140, 100), (0, 0.35), 'dot'),
        'drain': ((255, 120, 170), (0, -0.35), 'heart'),
        'loot': ((255, 220, 90), (0, -0.25), 'spark'),
        'spark': ((255, 255, 130), (0, 0), 'zig'),
        'pull': ((230, 80, 80), (0, 0), 'dot'),
    }

    def __init__(self, x, y, elem):
        self.x, self.y = x, y
        self.col, (self.vx, self.vy), self.kind = self.STYLE.get(elem, ((200, 200, 255), (0, -0.3), 'dot'))
        self.vx += random.uniform(-0.25, 0.25)
        self.t = 0
        self.life = random.randint(18, 30)
        self.dead = False

    def update(self, game):
        self.t += 1
        self.x += self.vx
        self.y += self.vy
        if self.t > self.life:
            self.dead = True

    def draw(self, surf, ox=0, oy=0):
        x, y = int(self.x + ox), int(self.y + oy)
        c = self.col
        if self.kind == 'spark':
            if (self.t // 3) % 2:
                surf.set_at((x, y), (255, 255, 255))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    surf.set_at((x + dx, y + dy), c)
        elif self.kind == 'star':
            surf.set_at((x, y), c)
            surf.set_at((x + 1, y), c)
            surf.set_at((x, y + 1), c)
        elif self.kind == 'heart':
            for dx, dy in ((0, 0), (1, 0), (-1, -1), (2, -1), (0, 1), (1, 1)):
                surf.set_at((x + dx, y + dy), c)
        elif self.kind == 'zig':
            pygame.draw.line(surf, c, (x - 2, y - 2), (x, y))
            pygame.draw.line(surf, c, (x, y), (x + 1, y - 3))
        else:
            surf.set_at((x, y), c)
            if self.t < self.life // 2:
                surf.set_at((x + 1, y), c)


def element_of(mood):
    import forms
    if mood in forms.FUSIONS:
        return forms.FUSIONS[mood]['element']
    return {'magnet': 'pull', 'starry': 'loot', 'wobbly': 'stun', 'stony': 'heavy', 'clammy': None}.get(mood)
