"""Cinematics in hi-fi 3D, drawn on the hi-res canvas (see hifi.py).

* Intro3D     the opening: a dawn ocean, a dive, Octo swimming up and the logo flying together
* VersusCut   the entrance to every 1-on-1 boss fight
* CityIntro   a welcome fly-over the first time you reach Octo City or Turtle Town
* MedalCut    a spinning medal when your score passes a milestone

Each scene has draw(hr, t) (hr: the SRCALPHA hi-res canvas) and cues(t) (sound effects to play).
"""
import math
import random

import pygame

import gfx
import hifi
import townart
import voxel
from hifi import F, H, HI, W, clamp, ease, ease_io, mix
from settings import AUTHOR

_VEIL = {}


def veil(surf, col, a):
    if a <= 0:
        return
    v = _VEIL.get(surf.get_size())
    if v is None:
        v = _VEIL[surf.get_size()] = pygame.Surface(surf.get_size())
    v.fill(col)
    v.set_alpha(int(clamp(a, 0, 255)))
    surf.blit(v, (0, 0))


def _row_profile(w, h, color, power=2.0, fade=1.2, strength=0.16):
    """A soft vertical light shaft (for additive blending)."""
    row = pygame.Surface((w, 1))
    for x in range(w):
        k = math.sin((x + 0.5) / w * math.pi) ** power * strength
        row.set_at((x, 0), (int(color[0] * k), int(color[1] * k), int(color[2] * k)))
    ray = pygame.transform.scale(row, (w, h))
    col = pygame.Surface((1, h))
    for y in range(h):
        g = int(255 * (1 - y / h) ** fade)
        col.set_at((0, y), (g, g, g))
    ray.blit(pygame.transform.scale(col, (w, h)), (0, 0), special_flags=pygame.BLEND_RGB_MULT)
    return ray


def _cloud(rnd, w, h, col):
    """A soft, puffy cloud: overlapping see-through puffs, blurred by shrinking and growing."""
    lw, lh = max(8, w // 3), max(4, h // 3)
    lo = pygame.Surface((lw, lh), pygame.SRCALPHA)
    for _ in range(16):
        r = rnd.uniform(lh * 0.22, lh * 0.42)
        x = rnd.uniform(r, lw - r)
        y = rnd.uniform(lh * 0.45, lh * 0.62) - (r - lh * 0.22) * 0.6
        for k in range(4, 0, -1):
            pygame.draw.circle(lo, col + (int(60 * (5 - k) / 4),), (int(x), int(y)), int(r * k / 4 + 1))
    lo = pygame.transform.smoothscale(lo, (max(4, lw // 2), max(2, lh // 2)))
    return pygame.transform.smoothscale(lo, (w, h))


class Ocean:
    """A mode-7 sea (or sand): every screen row below the horizon is a stretched strip of texture."""

    def __init__(self, rnd, base, light, glint, haze, sand=False):
        tex = pygame.Surface((256, 256))
        for y in range(256):
            k = 0.5 + 0.5 * math.sin(y / 256 * math.tau * 6 + math.sin(y / 256 * math.tau * 2) * 1.5)
            pygame.draw.line(tex, mix(base, light, k * (0.25 if sand else 0.5)), (0, y), (255, y))
        for _ in range(520):
            x, y = rnd.randrange(256), rnd.randrange(256)
            w = rnd.randint(4, 20) if not sand else rnd.randint(2, 6)
            pygame.draw.ellipse(tex, mix(base, light, rnd.uniform(0.45, 1.0)), (x, y, w, 2))
        for _ in range(140 if sand else 300):
            x, y = rnd.randrange(256), rnd.randrange(256)
            pygame.draw.line(tex, glint, (x, y), (x + rnd.randint(1, 3), y))
        self.tex = pygame.Surface((256 * 3, 256))
        for i in range(3):
            self.tex.blit(tex, (i * 256, 0))
        fog_h = 120 * HI
        self.fog = pygame.Surface((W, fog_h), pygame.SRCALPHA)
        for y in range(fog_h):
            a = int(235 * (1 - y / fog_h) ** 2.2)
            pygame.draw.line(self.fog, haze + (a,), (0, y), (W, y))

    def draw(self, surf, horizon, cam_h, travel, sway=0.0):
        hz = int(horizon)
        y = max(0, hz + 1)
        while y < H:
            dy = y - horizon
            step = 1 if dy < 30 * HI else 2 if dy < 90 * HI else 3
            z = cam_h * F / dy
            span = min(z * W / F * 3.0, 510.0)
            v = int(travel + z * 3.0) % 256
            u = (256 + sway - span / 2) % 256
            sub = self.tex.subsurface((int(u), v, max(1, int(span)), 1))
            if span < W / 3:
                strip = pygame.transform.smoothscale(sub.copy(), (W, step))
            else:
                strip = pygame.transform.scale(sub, (W, step))
            surf.blit(strip, (0, y))
            y += step
        surf.blit(self.fog, (0, hz - 2))


def _streak(w, h, col):
    """A soft horizontal streak of light (for additive or subtractive blending): drawn big, then
    shrunk, so its edges are smooth."""
    big = pygame.Surface((w * 4, max(4, h * 4)))
    bw, bh = big.get_size()
    for i in range(12, 0, -1):
        k = (1 - i / 12) ** 1.6
        rx, ry = bw / 2 * i / 12, bh / 2 * i / 12
        pygame.draw.ellipse(big, mix((0, 0, 0), col, k), (bw / 2 - rx, bh / 2 - ry, rx * 2, ry * 2))
    return pygame.transform.smoothscale(big, (w, max(1, h)))


class Sea:
    """The dawn sea the opening glides over, drawn smooth: every pixel row gets its own colour (the
    sky's glow near the horizon, deep blue close by) with long swells rolling in, soft streaks of
    light and shade glide towards the camera in true perspective, and the sun's path glitters with
    sparkles that twinkle on and off. Nothing is a stretched texture, so nothing jumps or turns to
    blocks as the camera glides and dives."""
    STREAKS, NEAR, SPARKS = 340, 210, 190
    BANDS = ((18, 330), (330, 2400))        # where the near and far streaks glide (camera units, times HI)

    def __init__(self, rnd):
        self.rnd = rnd
        # the water's colour by how far down the sea a row is (0 at the horizon, 1 at the bottom)
        stops = [(0.0, (255, 216, 182)), (0.05, (240, 172, 152)), (0.16, (150, 118, 160)),
                 (0.38, (66, 96, 162)), (0.7, (34, 72, 138)), (1.0, (18, 52, 112))]
        self.ramp = []
        for i in range(257):
            f = i / 256
            for (f0, c0), (f1, c1) in zip(stops, stops[1:]):
                if f <= f1:
                    self.ramp.append(mix(c0, c1, (f - f0) / (f1 - f0)))
                    break
        sizes = (3, 4, 6, 8, 11, 15, 20, 27, 36, 48, 64)
        self.light = {w * HI // 2: [_streak(w * HI // 2, max(1, w * HI // 14), mix((0, 0, 0), (120, 110, 90), b))
                                    for b in (0.35, 0.6, 1.0)] for w in sizes}
        self.dark = {w * HI // 2: [_streak(w * HI // 2, max(1, w * HI // 12), mix((0, 0, 0), (34, 26, 14), b))
                                   for b in (0.5, 1.0)] for w in sizes}
        self.widths = sorted(self.light)
        self.dots = [_streak(n * HI // 2 + 1, n * HI // 4 + 1, (255, 236, 190)) for n in (2, 3, 4, 6)]
        self.glow = {}                      # the sun's path, one soft row at a time: (half-width, level) -> row
        self.streaks = [self._new_streak(i < self.NEAR, True) for i in range(self.STREAKS)]
        self.sparks = [[rnd.uniform(0, 1), rnd.gauss(0, 0.45), rnd.uniform(0, math.tau), rnd.uniform(0.06, 0.16),
                        rnd.randrange(4)] for _ in range(self.SPARKS)]
        fog_h = 90 * HI
        self.fog = pygame.Surface((W, fog_h), pygame.SRCALPHA)
        for y in range(fog_h):
            a = int(200 * (1 - y / fog_h) ** 2.4)
            pygame.draw.line(self.fog, (255, 214, 184, a), (0, y), (W, y))

    def _new_streak(self, near, anywhere):
        """A streak of light or shade, somewhere in its band (or at the band's far edge, where it
        fades in), across the width that's in view there."""
        rnd = self.rnd
        z0, z1 = (v * HI for v in self.BANDS[0 if near else 1])
        z = rnd.uniform(z0, z1) if anywhere else z1
        x = rnd.uniform(-1.15, 1.15) * z * W / (2 * F)
        return [x, z, rnd.uniform(9, 26) * HI, rnd.random() < 0.62, rnd.uniform(0, math.tau), near]

    def _glow_row(self, half, lvl):
        """One row of the sun's path: a soft bell of light, half wide, at brightness lvl of 24. Made
        by stretching one small bell and dimming it (quick, so no frame waits for it)."""
        key = (half, lvl)
        row = self.glow.get(key)
        if row is None:
            bell = self.glow.get('bell')
            if bell is None:
                bell = self.glow['bell'] = pygame.Surface((64, 1))
                for x in range(64):
                    g = math.exp(-((x + 0.5 - 32) / (32 * 0.45)) ** 2)
                    bell.set_at((x, 0), (int(170 * g), int(128 * g), int(80 * g)))
            row = pygame.transform.smoothscale(bell, (half * 2, 1))
            m = int(255 * lvl / 24)
            row.fill((m, m, m), special_flags=pygame.BLEND_RGB_MULT)
            self.glow[key] = row
        return row

    def draw(self, surf, horizon, cam_h, travel, sway, sun_x, t):
        hz = max(-1, int(horizon))
        top = hz + 1
        span = max(1.0, H - horizon)
        cam = travel * HI / 3                         # how far the camera has come
        ramp, fill, blit, add = self.ramp, surf.fill, surf.blit, pygame.BLEND_RGB_ADD
        k1, k2, k3 = math.tau / (70 * HI), math.tau / (29 * HI), math.tau / (12 * HI)
        for y in range(max(0, top), H):                # 1. the water, one smooth row at a time
            dy = y - horizon
            z = cam_h * F / dy
            f = min(1.0, dy / span)
            c = ramp[int(f * 256)]
            zz = z + cam
            per = cam_h * F / (z * z) * HI             # (how many pixels one unit of swell covers here)
            w = 0.0
            if per * 29 > 2.5:                         # long swells and shorter ripples, each only where
                w = 0.55 * math.sin(zz * k1) * min(1.0, (per * 70 - 2.5) / 6) \
                    + 0.3 * math.sin(zz * k2 + 1.3) * min(1.0, (per * 29 - 2.5) / 6)    # it's big enough
                if per * 12 > 2.5:                     # to see (any smaller would just flicker)
                    w += 0.15 * math.sin(zz * k3 + 4.0) * min(1.0, (per * 12 - 2.5) / 6)
                m = 1 + 0.2 * w
                c = (min(255, int(c[0] * m)), min(255, int(c[1] * m)), min(255, int(c[2] * m)))
            fill(c, (0, y, W, 1))
            # the sun's path: wider close by, brightest where a swell catches the light
            half = int((3 + f * 52) * HI) // 2 * 2 + 2
            lvl = int((0.62 * (1 - f) ** 1.3 + 0.1) * (0.6 + 0.7 * max(-0.2, w)) * 24 + 0.5)
            if lvl > 0:
                blit(self._glow_row(half, min(24, lvl)), (sun_x - half, y), special_flags=add)
        # 2. streaks of light and shade, gliding in
        step = getattr(self, '_cam', cam)
        moved = max(0.0, cam - step)
        self._cam = cam
        zfar = cam_h * F / 1.5
        for s in self.streaks:
            s[1] -= moved
            z0, z1 = (v * HI for v in self.BANDS[0 if s[5] else 1])
            if s[1] < z0:
                s[:] = self._new_streak(s[5], False)
            x, z, ln, lit, ph, near_band = s
            fade_in = min(1.0, (z1 - z) / ((z1 - z0) * 0.3))
            if fade_in < 0.34:
                continue
            if z > zfar:
                continue
            k = F / z
            px = W / 2 + (x - sway * HI / 6) * k
            py = horizon + cam_h * k
            wpx = ln * k
            if wpx < 2 or py >= H + 4 or py < 0:
                continue
            i = min(len(self.widths) - 1, max(0, sum(1 for v in self.widths if v <= wpx) - 1))
            wid = self.widths[i]
            near = min(1.0, (py - horizon) / (span * 0.5))
            if lit:
                lvl = 2 if near > 0.55 else 1 if near > 0.2 else 0
                if math.sin(t * 0.05 + ph) < -0.6:
                    lvl = max(0, lvl - 1)
                if fade_in < 0.67:
                    lvl = 0
                img = self.light[wid][lvl]
                blit(img, (px - wid / 2, py - img.get_height() / 2), special_flags=pygame.BLEND_RGB_ADD)
            else:
                img = self.dark[wid][1 if near > 0.3 else 0]
                surf.blit(img, (px - wid / 2, py - img.get_height() / 2), special_flags=pygame.BLEND_RGB_SUB)
        # 3. the sun's glitter: sparkles twinkling along its path
        for sp in self.sparks:
            f = (sp[0] + cam / (900 * HI)) % 1.0       # (how far down the path: glides in like the rest)
            dy = span * f * f
            if dy < 1:
                continue
            y = horizon + dy
            if y >= H:
                continue
            tw = math.sin(t * sp[3] * 2.2 + sp[2])
            if tw < 0.55:
                continue
            x = sun_x + sp[1] * (5 + dy * 0.42)
            img = self.dots[min(3, int(sp[4] * (0.4 + f)))]
            surf.blit(img, (x - img.get_width() / 2, y - img.get_height() / 2), special_flags=pygame.BLEND_RGB_ADD)
            if tw > 0.92:                              # (now and then one flashes brighter)
                surf.blit(img, (x - img.get_width() / 2, y - img.get_height() / 2), special_flags=pygame.BLEND_RGB_ADD)
        surf.blit(self.fog, (0, hz - 2))


class Sparkles:
    def __init__(self):
        self.p = []

    def burst(self, x, y, n, col=(255, 240, 180), speed=3.0):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            v = random.uniform(0.3, 1.0) * speed * HI
            self.p.append([x, y, math.cos(a) * v, math.sin(a) * v, random.randint(18, 34), col])

    def twinkle(self, x, y, col=(255, 255, 230)):
        self.p.append([x, y, 0, 0, 24, col])

    def draw(self, surf):
        for s in self.p:
            s[0] += s[2]
            s[1] += s[3]
            s[2] *= 0.92
            s[3] = s[3] * 0.92 + 0.04 * HI
            s[4] -= 1
            r = max(1, int(s[4] / 34 * 4 * HI))
            hifi.add_glow(surf, s[5], s[0], s[1], r * 2.2)
            pygame.draw.line(surf, s[5], (s[0] - r, s[1]), (s[0] + r, s[1]), max(1, HI // 2))
            pygame.draw.line(surf, s[5], (s[0], s[1] - r), (s[0], s[1] + r), max(1, HI // 2))
        self.p = [s for s in self.p if s[4] > 0]


# ======================================================================
# the opening
# ======================================================================
def _spaced(s, px, color, track):
    """Smooth capitals with extra space between the letters (track: a fraction of the size)."""
    f = hifi.font(px)
    if f is None:
        return hifi.text(s, px, color, outline=None, shadow=False)
    glyphs = [f.render(ch, True, color) for ch in s]
    gap = px * track
    w = sum(g.get_width() for g in glyphs) + gap * (len(glyphs) - 1)
    out = pygame.Surface((int(w) + 2, max(g.get_height() for g in glyphs)), pygame.SRCALPHA)
    x = 0.0
    for g in glyphs:
        out.blit(g, (int(x), 0))
        x += g.get_width() + gap
    return out


class Intro3D:
    """About ten seconds: skim a dawn ocean, dive in, Octo swims up out of the deep and the
    logo flies together letter by letter. Any key skips it. Then the game dives on through the
    logo into the title screen (transition3d)."""
    LENGTH = 600
    DIVE = 150
    SPLASH = 200
    LOGO = 340
    FLASH = 600

    def __init__(self):
        rnd = random.Random(11)
        self.rnd = rnd
        self.done = False
        self.t = 0
        self.sky = hifi.gradient(W, H, [(0, (30, 26, 90)), (0.4, (170, 80, 130)), (0.66, (255, 150, 96)),
                                        (0.84, (255, 206, 150)), (1, (255, 232, 190))])
        self.sea = Sea(rnd)
        self.deep = hifi.gradient(W, H, [(0, (44, 150, 205)), (0.3, (16, 78, 150)), (1, (3, 12, 42))])
        self.rays = [(_row_profile(rnd.randint(40, 90) * HI, H, (130, 210, 255)), rnd.uniform(0, W),
                      rnd.uniform(0.4, 1.0)) for _ in range(6)]
        self.clouds = [(_cloud(rnd, rnd.randint(70, 130) * HI, 36 * HI, (255, 210, 210)),
                        rnd.uniform(0, W), rnd.uniform(6, 60) * HI, rnd.uniform(0.15, 0.5) * HI) for _ in range(7)]
        self.bubbles = [[rnd.uniform(-160, 160) * HI, rnd.uniform(-140, 140) * HI, rnd.uniform(40, 900) * HI,
                         rnd.uniform(2, 6)] for _ in range(70)]
        self.snow = [[rnd.uniform(-200, 200) * HI, rnd.uniform(-180, 180) * HI, rnd.uniform(60, 900) * HI]
                     for _ in range(120)]
        self.octo = voxel.VoxelFigure('blue')
        self.sparkles = Sparkles()
        self.letters = None
        self.landed = set()
        self.card = None
        self.press = hifi.text("PRESS ANY KEY", 9 * HI, (150, 175, 220), shadow=False)

    # ---- pieces --------------------------------------------------------
    def prepare(self):
        """Make everything the opening would otherwise make while it plays (in a browser each piece is
        a visible stall): the logo and its letters, the credit, Octo's 3D figure, the splash. A
        generator: the game runs it a few milliseconds at a time behind its loading bar."""
        if self.letters is None:
            yield from self._logo_steps()
        if self.card is None:
            self.card = self._make_card()
            yield
        scratch = pygame.Surface((W, H), pygame.SRCALPHA)
        for t in (0, 1, 2, 3, 30, 150, *range(184, 203), 205, 210, 215, 217, 218, 219, 220, 225,
                  240, 260, 290, 320):
            self.draw(scratch, t)               # a throwaway frame: makes what that moment needs
            yield
        self.t, self.done = 0, False

    def _make_card(self):
        """The opening credit, made once: the author's name in clean, well-spaced white capitals over
        a small "PRESENTS" between two fine rules, on a soft dark glow (no hard outline)."""
        name = _spaced(AUTHOR.upper(), 18 * HI, (255, 255, 255), 0.16)
        sub = _spaced("PRESENTS", 9 * HI, (255, 240, 218), 0.55)
        gap = 5 * HI
        w = max(name.get_width(), sub.get_width() + 40 * HI)
        pad = 16 * HI
        h = name.get_height() + gap + sub.get_height()
        card = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
        words = pygame.Surface(card.get_size(), pygame.SRCALPHA)
        nx = pad + (w - name.get_width()) // 2
        sx, sy = pad + (w - sub.get_width()) // 2, pad + name.get_height() + gap
        words.blit(name, (nx, pad))
        words.blit(sub, (sx, sy))
        ry = sy + sub.get_height() // 2
        for x0, x1 in ((sx - 26 * HI, sx - 8 * HI), (sx + sub.get_width() + 8 * HI, sx + sub.get_width() + 26 * HI)):
            pygame.draw.line(words, (255, 238, 214), (x0, ry), (x1, ry), max(1, HI // 2 + 1))
        glow = words.copy()                      # the glow: the words' shapes, dark and blurred
        glow.fill((40, 14, 30, 255), special_flags=pygame.BLEND_RGBA_MULT)
        cw, ch = glow.get_size()
        for k in (6, 3):
            small = pygame.transform.smoothscale(glow, (max(1, cw // k), max(1, ch // k)))
            soft = pygame.transform.smoothscale(small, (cw, ch))
            soft.set_alpha(175 if k == 6 else 130)
            card.blit(soft, (0, HI))
        card.blit(words, (0, 0))
        return card

    def _build_logo(self):
        for _ in self._logo_steps():
            pass

    def _logo_steps(self):
        words = [("LEGEND OF", 27 * HI, (240, 248, 255), (130, 180, 240), (40, 70, 150), 38 * HI, 10, 6, 42),
                 ("OCTO", 70 * HI, (255, 244, 150), (250, 140, 40), (150, 60, 10), 64 * HI, 80, 11, 52)]
        self.letters, self.words = [], []
        rnd = self.rnd
        for word, px, top, bot, side, y, start, gap, dur in words:
            f = hifi.font(px)
            full = hifi.text3d(word, px, top, bot, side)
            total = f.size(word)[0] if f else full.get_width()
            x0 = W / 2 - total / 2
            pad = max(2, px // 16) + 2
            self.words.append((full, x0 - pad, y - pad))
            n = 0
            for i, ch in enumerate(word):
                if ch == ' ':
                    continue
                img = hifi.text3d(ch, px, top, bot, side)
                adv = f.size(word[:i])[0] if f else i * px * 0.6
                fx, fy = x0 + adv - pad + img.get_width() / 2, y - pad + img.get_height() / 2
                a = rnd.uniform(0, math.tau)
                self.letters.append({
                    'img': img, 'fx': fx, 'fy': fy, 't0': self.LOGO + start + n * gap, 'dur': dur,
                    'sx': math.cos(a) * rnd.uniform(500, 900) * HI, 'sy': math.sin(a) * rnd.uniform(300, 600) * HI,
                    'sz': rnd.uniform(2200, 3600) * HI, 'spin': rnd.uniform(-540, 540), 'big': px > 40 * HI})
                n += 1
                yield
        self.sub = hifi.text("A REVERSIBLE UNDERSEA ADVENTURE", 13 * HI, (205, 232, 255))

    def cues(self, t):
        out = []
        if t == self.SPLASH - 4:
            out.append('boom')
        if t == self.SPLASH + 2:
            out.append('bubble')
        if t == self.LOGO:
            out.append('whoosh')
        if self.letters:
            for L in self.letters:
                if t == L['t0'] + L['dur']:
                    out.append('tink' if not L['big'] else 'hit')
        if t == self.LOGO + 150:
            out.append('item')
        return out

    # ---- per frame -----------------------------------------------------
    def draw(self, hr, t):
        self.t = t
        if t >= self.LENGTH:
            self.done = True
        hifi.warm(48)
        if t < self.SPLASH:
            self._above(hr, t)
        else:
            self._below(hr, t)
        if t > 40 and (t // 30) % 2 and t < self.FLASH:
            hr.blit(self.press, (W - self.press.get_width() - 4 * HI, H - self.press.get_height() - 2 * HI))

    def _above(self, hr, t):
        dive = max(0.0, (t - self.DIVE) / 50)
        horizon = H * 0.56 - dive * dive * H * 1.1
        cam_h = (36 - min(1.0, dive) * 30) * HI
        hr.blit(self.sky, (0, int(horizon - H)))
        sx, sy = W * 0.6, horizon - 26 * HI
        hifi.add_glow(hr, (120, 80, 40), sx, sy, 120 * HI)
        hifi.add_glow(hr, (160, 120, 60), sx, sy, 50 * HI)
        pygame.draw.circle(hr, (255, 250, 225), (int(sx), int(sy)), 12 * HI)
        for img, x, y, sp in self.clouds:
            cx = (x - t * sp) % (W + img.get_width()) - img.get_width()
            hr.blit(img, (cx, horizon - 120 * HI + y))
        self.sea.draw(hr, horizon, cam_h, t * (2.2 + t * 0.012), math.sin(t * 0.01) * 30, sx, t)
        for f_, r, c in ((0.5, 10, (60, 40, 20)), (0.9, 18, (30, 50, 60)), (1.3, 7, (60, 40, 50))):   # lens flare
            hifi.add_glow(hr, c, sx + (W / 2 - sx) * f_ * 2, sy + (H / 2 - sy) * f_ * 2, r * HI)
        if t < 150:                              # the credit fades in, rises a touch, fades out
            a = clamp(min((t - 20) / 34, (142 - t) / 30))
            if a > 0:
                if self.card is None:
                    self.card = self._make_card()
                a = a * a * (3 - 2 * a)
                self.card.set_alpha(int(255 * a))
                hr.blit(self.card, (W / 2 - self.card.get_width() / 2,
                                    H * 0.24 - self.card.get_height() / 2 - (t - 20) * 0.05 * HI))
        if t < 30:
            veil(hr, (0, 0, 0), 255 * (1 - t / 30))
        if t > self.SPLASH - 16:
            k = (t - (self.SPLASH - 16)) / 16
            for i in range(30):                         # the splash: soft spray thrown up and out
                a = i / 30 * math.pi + 0.1
                r = k * (60 + (i * 37) % 90) * HI
                x = W / 2 + math.cos(a + math.pi) * r * 1.6
                y = H * 0.9 - math.sin(a) * r * 1.4 + k * k * 120 * HI
                rr = (5 + i % 4) * HI * (1 - k * 0.5)
                hifi.add_glow(hr, (150, 190, 215), x, y, rr * 2.2)
                hifi.add_glow(hr, (110, 110, 105), x, y, rr)
            veil(hr, (235, 248, 255), k * 255)

    def _below(self, hr, t):
        u = t - self.SPLASH
        hr.blit(self.deep, (0, 0))
        for img, x, sp in self.rays:
            hr.blit(img, (x + math.sin(t * 0.008 * sp + x) * 40 * HI - img.get_width() / 2, 0),
                    special_flags=pygame.BLEND_RGB_ADD)
        speed = (9.0 if u < 50 else max(1.2, 9.0 - (u - 50) * 0.08)) * HI
        for s in self.snow:
            s[2] -= speed * 0.6
            if s[2] < 30 * HI:
                s[0], s[1], s[2] = self.rnd.uniform(-200, 200) * HI, self.rnd.uniform(-180, 180) * HI, 900 * HI
            x, y, k = hifi.project(s[0], s[1], s[2])
            if 0 <= x < W and 0 <= y < H:
                c = int(90 + 120 * clamp(200 * HI / s[2]))
                pygame.draw.circle(hr, (c // 2, c, min(255, c + 40)), (int(x), int(y)), max(1, int(k * 1.2)))
        items = []
        # Octo swims up out of the deep, spinning, then hangs below the logo
        k = ease(u / 130)
        settle = ease((t - self.LOGO - 40) / 110)
        z = (1500 - 1180 * k) * HI + settle * 120 * HI
        oy = (60 * (1 - k) + math.sin(t * 0.05) * 6 + settle * 66) * HI
        yaw = (1 - k) * math.tau * 2.2 + math.sin(t * 0.03) * 0.35
        wave = clamp((u - 115) / 15) * clamp((self.LOGO + 30 - t) / 15)
        blink = 100 < u < 106 or ((t // 150) % 5 == 4 and t % 150 < 6)
        items += self.octo.items((0, oy, z), yaw=yaw, pitch=0.15 + (1 - k) * 0.5, t=t, size=70 * HI, wave=wave,
                                 blink=blink, swim=(1 - k) * 0.8)
        for b in self.bubbles:                       # bubbles rushing past
            b[2] -= speed * 0.9
            b[1] -= b[3] * 0.4 * HI
            if b[2] < 20 * HI or b[1] < -300 * HI:
                b[0], b[1], b[2] = self.rnd.uniform(-160, 160) * HI, self.rnd.uniform(-40, 180) * HI, 900 * HI
            x, y, kk = hifi.project(b[0], b[1], b[2])
            r = b[3] * kk
            if -r < x < W + r and -r < y < H + r and r >= 1:
                items.append((b[2], lambda s, x=x, y=y, r=r: s.blit(hifi.bubble(r), (x - r, y - r))))
        hifi.render(hr, items)
        # the logo
        if t > self.LOGO - 30 and self.letters is None:
            self._build_logo()
        if self.letters and t > self.LOGO:
            if all(t > L['t0'] + L['dur'] for L in self.letters):
                sweep = (t - self.LOGO - 150) * 14 * HI
                for full, x, y in self.words:
                    img = hifi.shine(full, sweep - 300 * HI) if 0 < sweep < W + 600 * HI else full
                    hr.blit(img, (x, y))
            else:
                for i, L in enumerate(self.letters):
                    p = (t - L['t0']) / L['dur']
                    if p <= 0:
                        continue
                    if p >= 1:
                        if i not in self.landed:
                            self.landed.add(i)
                            self.sparkles.burst(L['fx'], L['fy'], 14 if L['big'] else 6,
                                                (255, 230, 140) if L['big'] else (200, 230, 255))
                        img = L['img']
                        hr.blit(img, (L['fx'] - img.get_width() / 2, L['fy'] - img.get_height() / 2))
                        continue
                    e = ease_io(p)
                    zz = L['sz'] + (F - L['sz']) * e
                    wx = L['sx'] + (L['fx'] - W / 2 - L['sx']) * e
                    wy = L['sy'] + (L['fy'] - H / 2 - L['sy']) * e
                    x, y, kk = hifi.project(wx, wy, zz)
                    img = pygame.transform.rotozoom(L['img'], L['spin'] * (1 - e), clamp(kk, 0.02, 6))
                    hr.blit(img, (x - img.get_width() / 2, y - img.get_height() / 2))
            if t > self.LOGO + 160 and self.rnd.random() < 0.3:
                full, x, y = self.words[1]
                self.sparkles.twinkle(x + self.rnd.uniform(0.1, 0.9) * full.get_width(),
                                      y + self.rnd.uniform(0.2, 0.8) * full.get_height())
        self.sparkles.draw(hr)
        if t > self.LOGO + 180:
            img = self.sub.copy()
            img.set_alpha(int(255 * clamp((t - self.LOGO - 180) / 30)))
            hr.blit(img, (W / 2 - img.get_width() / 2, H - 34 * HI))
        if u < 34:
            veil(hr, (235, 248, 255), 255 * (1 - u / 34))


# ======================================================================
# the versus entrance for 1-on-1 boss fights
# ======================================================================
class VersusCut:
    """The world shatters, Octo and the guardian face off across a slash of light, VS slams in,
    then the panels split apart to reveal the arena."""
    LENGTH = 200
    SHATTER = 34
    VS_AT = 62
    OPEN = 160

    def __init__(self, snapshot, mood, boss_img, name, subtitle, accent=(255, 80, 90), hat=None):
        self.accent = accent
        self.name, self.subtitle = name, subtitle
        big = pygame.transform.scale(snapshot, (W, H))
        rnd = random.Random()
        self.rnd = rnd
        cw, ch = W // 8, H // 8
        self.shards = []
        for gy in range(8):
            for gx in range(8):
                r = pygame.Rect(gx * cw, gy * ch, cw, ch)
                cx, cy = r.centerx - W / 2, r.centery - H / 2
                d = math.hypot(cx, cy) or 1
                self.shards.append({'img': big.subsurface(r).copy(), 'x': r.centerx, 'y': r.centery,
                                    'vx': cx / d * rnd.uniform(1.5, 4) * HI, 'vy': (cy / d * rnd.uniform(1.5, 4) - 1) * HI,
                                    'spin': rnd.uniform(-9, 9), 'delay': int(d / (14 * HI))})
        self.cracks = []
        for _ in range(10):
            a = rnd.uniform(0, math.tau)
            pts = [(W / 2, H / 2)]
            r = 0
            while r < 220 * HI:
                r += rnd.uniform(14, 26) * HI
                a += rnd.uniform(-0.4, 0.4)
                pts.append((W / 2 + math.cos(a) * r, H / 2 + math.sin(a) * r))
            self.cracks.append(pts)
        self.lines = [[rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(6, 14) * HI, rnd.uniform(10, 40) * HI]
                      for _ in range(46)]
        self.slope, self.mid = 40 * HI, H / 2
        self.top = self._panel([(0, 0), (W, 0), (W, self.mid - self.slope), (0, self.mid + self.slope)],
                               (16, 30, 90), (40, 90, 190))
        dark = tuple(c // 3 for c in accent)
        self.bot = self._panel([(0, self.mid + self.slope), (W, self.mid - self.slope), (W, H), (0, H)],
                               mix(dark, (60, 10, 20), 0.3), mix(accent, (90, 20, 30), 0.45))
        self.octo = voxel.VoxelFigure(mood, hat)
        self.boss = voxel.VoxelFigure(sprite=boss_img)
        self.vs = hifi.text3d("VS", 50 * HI, (255, 252, 190), (255, 170, 40), (150, 40, 20), outline=(60, 0, 0))
        self.tag = hifi.text("OCTO", 22 * HI, (175, 220, 255))
        n = 22 if len(name) <= 10 else 17 if len(name) <= 14 else 13
        self.name_img = hifi.text(name, n * HI, (255, 226, 120))
        self.sub_img = hifi.text(subtitle, 9 * HI, (240, 214, 214))
        self.done = False

    @staticmethod
    def _panel(poly, c0, c1):
        g = hifi.gradient(W, H, [(0, c0), (1, c1)], alpha=True)
        m = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.polygon(m, (255, 255, 255, 255), poly)
        g.blit(m, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        return g

    def cues(self, t):
        return {0: ['whoosh'], self.SHATTER + 2: ['whoosh'], self.VS_AT: ['boom', 'roar'],
                self.OPEN: ['door']}.get(t, [])

    def draw(self, hr, t):
        if t >= self.LENGTH:
            self.done = True
            return
        acc = self.accent
        opening = t >= self.OPEN
        gap = ease((t - self.OPEN) / 30) * (W + 80 * HI) if opening else 0
        if not opening:
            hr.fill((6, 4, 16, 255))
            for ln in self.lines:
                a = math.atan2(ln[1] - H / 2, ln[0] - W / 2) + t * 0.01
                r0 = (ln[3] + t * ln[2]) % (230 * HI)
                p0 = (W / 2 + math.cos(a) * r0, H / 2 + math.sin(a) * r0)
                p1 = (W / 2 + math.cos(a) * (r0 + 18 * HI), H / 2 + math.sin(a) * (r0 + 18 * HI))
                pygame.draw.line(hr, mix((0, 0, 0), acc, 0.45), p0, p1, HI)
        # ---- 1: the world shatters
        if t < self.SHATTER + 30:
            for s in self.shards:
                u = max(0, t - 6 - s['delay'])
                if t < 6:
                    hr.blit(s['img'], s['img'].get_rect(center=(s['x'], s['y'])))
                    continue
                z = 1 + u * 0.05
                x = s['x'] + s['vx'] * u * z
                y = s['y'] + s['vy'] * u * z + 0.08 * u * u * HI
                img = pygame.transform.rotozoom(s['img'], s['spin'] * u, z)
                if u > 10:
                    img.set_alpha(max(0, 255 - (u - 10) * 10))
                hr.blit(img, img.get_rect(center=(x, y)))
            if t < 10:
                for pts in self.cracks:
                    n = min(len(pts), 2 + t)
                    pygame.draw.lines(hr, (255, 255, 255), False, pts[:n], 2 * HI)
                    pygame.draw.lines(hr, acc, False, pts[:n], HI)
            if t < 4:
                veil(hr, (255, 255, 255), 200 - t * 50)
        if t < self.SHATTER - 6:
            return
        # ---- 2: the two panels sweep in along a diagonal slash
        p_in = ease((t - self.SHATTER + 6) / 22)
        off = (1 - p_in) * (W + 40 * HI)
        tx, ty = -off - gap, -gap * 0.3
        bx, by = off + gap, gap * 0.3
        hr.blit(self.top, (tx, ty))
        hr.blit(self.bot, (bx, by))
        mid, slope = self.mid, self.slope
        for i, ln in enumerate(self.lines):          # streaks inside each panel
            on_top = i % 2 == 0
            x = (ln[0] + t * ln[2] * (1 if on_top else -1)) % (W + 80 * HI) - 40 * HI
            if on_top:
                y = ln[1] * (mid - slope - 4 * HI) / H
                pygame.draw.line(hr, (90, 140, 240), (x + tx, y + ty), (x + tx + ln[3], y + ty), max(1, HI // 2))
            else:
                y = mid + slope + 4 * HI + ln[1] * (H - mid - slope - 4 * HI) / H
                pygame.draw.line(hr, mix(acc, (255, 255, 255), 0.25), (x + bx, y + by), (x + bx + ln[3], y + by),
                                 max(1, HI // 2))
        # fighters
        items = []
        bob = math.sin(t * 0.15) * 3 * HI
        z = 420 * HI
        k = F / z
        ox, oy = 66 * HI + tx, 78 * HI + ty + bob
        items += self.octo.items(((ox - W / 2) / k, (oy - H / 2) / k, z), yaw=0.45 + math.sin(t * 0.05) * 0.25,
                                 pitch=0.12, t=t, size=27 * HI / k)
        reveal = t - (self.VS_AT - 4)
        dark = 1.0 if reveal < 0 else 0.0
        lit = clamp(1 - reveal / 10) if reveal >= 0 else 0.0
        sz = 500 * HI
        kb = F / sz
        bxs, bys = 176 * HI + bx, 156 * HI + by + math.sin(t * 0.11) * 3 * HI
        shake = self.rnd.uniform(-2, 2) * HI if reveal >= 0 and (t // 3) % 8 == 0 else 0
        items += self.boss.items(((bxs + shake - W / 2) / kb, (bys - H / 2) / kb, sz),
                                 yaw=-0.45 + math.sin(t * 0.04) * 0.2, pitch=0.1, scale=4.9 * HI / kb,
                                 dark=dark, lit=lit)
        hifi.render(hr, items)
        if dark:                                     # glowing eyes in the dark
            for ex in (-10, 10):
                hifi.add_glow(hr, acc, bxs + ex * HI, bys - 8 * HI, 7 * HI)
        hr.blit(self.tag, (124 * HI + tx, 50 * HI + ty + bob))
        if t > self.VS_AT + 6:
            kk = ease((t - self.VS_AT - 6) / 16)
            hr.blit(self.name_img, (10 * HI - (1 - kk) * 220 * HI + bx, H - 70 * HI + by))
            if t > self.VS_AT + 18:
                n = (t - self.VS_AT - 18) * 2
                img = hifi.text(self.subtitle[:n], 9 * HI, (240, 214, 214)) if n < len(self.subtitle) else self.sub_img
                hr.blit(img, (12 * HI + bx, H - 40 * HI + by))
        # the glowing slash between the panels
        if not opening:
            a = p_in
            pygame.draw.line(hr, mix((0, 0, 0), (255, 255, 255), a), (0, mid + slope), (W, mid - slope), 3 * HI)
            pygame.draw.line(hr, mix((0, 0, 0), acc, a), (0, mid + slope + 3 * HI), (W, mid - slope + 3 * HI), 2 * HI)
            pygame.draw.line(hr, mix((0, 0, 0), (120, 170, 255), a), (0, mid + slope - 3 * HI), (W, mid - slope - 3 * HI),
                             2 * HI)
        # ---- 3: VS slams down
        if t >= self.VS_AT - 6 and not opening:
            u = t - (self.VS_AT - 6)
            sc = max(1.0, 3.2 - u * 0.4)
            img = pygame.transform.rotozoom(self.vs, (1 - min(1, u / 6)) * -25, sc)
            if u < 6:
                img.set_alpha(90 + u * 28)
            hr.blit(img, img.get_rect(center=(W / 2, mid)))
            ring = t - self.VS_AT
            if 0 <= ring < 10:
                pygame.draw.circle(hr, (255, 255, 255), (W // 2, int(mid)), (10 + ring * 14) * HI, 2 * HI)
                hifi.add_glow(hr, (120, 90, 40), W / 2, mid, (60 - ring * 4) * HI)
                if ring < 3:
                    veil(hr, (255, 255, 255), 160 - ring * 50)
        # cinema bars
        bar = int(14 * HI * min(1.0, t / 20) * ((1 - ease((t - self.OPEN) / 30)) if opening else 1))
        if bar:
            pygame.draw.rect(hr, (0, 0, 0), (0, 0, W, bar))
            pygame.draw.rect(hr, (0, 0, 0), (0, H - bar, W, bar))


_BIG_WORDS = {}


def big_word(word, px, top, bottom, side, outline=(60, 0, 0)):
    key = (word, px, top)
    img = _BIG_WORDS.get(key)
    if img is None:
        img = _BIG_WORDS[key] = hifi.text3d(word, px, top, bottom, side, outline=outline)
    return img


def draw_fight(hr, t, cy):
    """FIGHT! zooming in, t counting up from 0."""
    if t >= 50:
        return
    img = big_word("FIGHT!", 40 * HI, (255, 250, 200), (255, 140, 40), (140, 30, 10))
    sc = max(1.0, 2.6 - t * 0.12)
    out = pygame.transform.rotozoom(img, 0, sc) if sc != 1 else img.copy()
    if t > 36:
        out.set_alpha(255 - (t - 36) * 18)
    hr.blit(out, out.get_rect(center=(W / 2, cy)))


def draw_victory(hr, t, name, cy):
    """The VICTORY! banner after a boss falls (t counts up from 0 to about 110)."""
    if t < 6:
        veil(hr, (255, 255, 255), 200 - t * 34)
    if 20 <= t < 104:
        u = t - 20
        band_h = int(34 * HI * min(1.0, u / 10)) if u < 74 else int(34 * HI * (104 - t) / 10)
        band = pygame.Surface((W, max(1, band_h)), pygame.SRCALPHA)
        band.fill((0, 0, 0, 180))
        for i in range(0, W + 40 * HI, 14 * HI):
            x = (i + u * 3 * HI) % (W + 40 * HI) - 20 * HI
            pygame.draw.line(band, (255, 200, 60, 46), (x, 0), (x - 12 * HI, band_h), 4 * HI)
        hr.blit(band, (0, cy - band_h // 2))
        if band_h > 24 * HI:
            img = big_word("VICTORY!", 26 * HI, (255, 246, 170), (250, 170, 40), (120, 60, 0), outline=(50, 20, 0))
            x = W / 2 + max(0, 30 - u * 3) * 8 * HI
            hr.blit(img, img.get_rect(center=(x, cy - 3 * HI)))
            sub = hifi.text(name, 9 * HI, (255, 255, 255), shadow=False)
            hr.blit(sub, sub.get_rect(center=(W / 2, cy + 13 * HI)))


# ======================================================================
# city fly-overs
# ======================================================================
def _cylinder(w, h, col, stripes=None):
    """A shaded upright cylinder (light from the left), optionally with coloured bands."""
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    for x in range(w):
        u = (x + 0.5) / w * 2 - 1
        nz = math.sqrt(max(0.0, 1 - u * u))
        k = 0.3 + 0.7 * max(0.0, -u * 0.55 + nz * 0.8)
        pygame.draw.line(s, mix((0, 0, 0), col, k), (x, 0), (x, h))
    if stripes:
        band = max(2, h // 8)
        for i in range(0, h, band * 2):
            hh = min(band, h - i)
            st = pygame.Surface((w, hh), pygame.SRCALPHA)
            st.fill(stripes + (255,))
            st.blit(s.subsurface((0, i, w, hh)), (0, 0), special_flags=pygame.BLEND_RGB_MULT)
            s.blit(st, (0, i))
    return s


class CityIntro:
    """A short welcome fly-over: glide down the main street as the city's name drops in."""
    LENGTH = 300

    def __init__(self, kind):
        self.kind = kind
        rnd = random.Random(5 if kind == 'octo' else 6)
        self.rnd = rnd
        self.done = False
        self.sparkles = Sparkles()
        self.cyl = {}
        if kind == 'octo':
            self.bg = hifi.gradient(W, H, [(0, (60, 170, 210)), (0.45, (20, 90, 150)), (1, (8, 30, 70))])
            self.ground = Ocean(rnd, (196, 150, 170), (236, 200, 210), (255, 240, 250), (40, 110, 160), sand=True)
            self.rays = [(_row_profile(rnd.randint(40, 80) * HI, H, (150, 220, 255)), rnd.uniform(0, W),
                          rnd.uniform(0.4, 1.0)) for _ in range(5)]
            cols = [(240, 130, 160), (180, 120, 230), (110, 200, 220), (250, 180, 110), (150, 220, 160)]
            self.things = []
            for i in range(14):
                side = -1 if i % 2 else 1
                self.things.append({'k': rnd.choice(('dome', 'dome', 'tower')), 'x': side * rnd.uniform(110, 190),
                                    'z': 260 + i * 120, 'r': rnd.uniform(40, 70), 'h': rnd.uniform(110, 190),
                                    'c': rnd.choice(cols)})
            self.things.append({'k': 'hall', 'x': 0, 'z': 2000, 'r': 230, 'h': 120, 'c': (255, 200, 80)})
            pals = ['cit_octavia', 'cit_inky', 'cit_tenta', 'cit_bubbles', 'cit_ollie', 'cit_ziggy', 'cit_coraline']
            for i in range(9):
                side = -1 if i % 2 else 1
                self.things.append({'k': 'octo', 'x': side * rnd.uniform(35, 80), 'z': 300 + i * 160,
                                    'm': voxel.VoxelFigure(rnd.choice(pals)), 'ph': rnd.uniform(0, 6)})
            self.title = hifi.text3d("OCTO CITY", 40 * HI, (255, 245, 170), (250, 150, 60), (140, 60, 20))
            self.sub = hifi.text("HOME OF THE FRIENDLIEST OCTOPUSES IN THE SEA", 9 * HI, (220, 240, 255))
            self.cam_h = 46
        else:
            self.bg = hifi.gradient(W, H, [(0, (80, 160, 240)), (0.5, (170, 220, 255)), (1, (240, 250, 255))])
            self.sea = hifi.gradient(W, 40 * HI, [(0, (40, 130, 200)), (1, (90, 180, 220))])
            self.ground = Ocean(rnd, (230, 206, 150), (250, 232, 186), (255, 250, 230), (250, 240, 220), sand=True)
            self.things = []
            shells = [(110, 160, 90), (190, 130, 80), (120, 140, 190), (200, 170, 90), (170, 110, 150)]
            for i in range(12):
                side = -1 if i % 2 else 1
                self.things.append({'k': rnd.choice(('shell', 'shell', 'palm')), 'x': side * rnd.uniform(120, 200),
                                    'z': 260 + i * 130, 'r': rnd.uniform(45, 70), 'c': rnd.choice(shells),
                                    'h': rnd.uniform(140, 200)})
            self.things.append({'k': 'lighthouse', 'x': 170, 'z': 1900, 'r': 34, 'h': 330, 'c': (240, 240, 240)})
            for i in range(8):
                side = -1 if i % 2 else 1
                self.things.append({'k': 'turtle', 'x': side * rnd.uniform(40, 90), 'z': 320 + i * 170,
                                    'm': voxel.VoxelFigure(sprite=townart.turtle_folk(rnd.choice(shells), (150, 210, 140))[0]),
                                    'ph': rnd.uniform(0, 6)})
            self.title = hifi.text3d("TURTLE TOWN", 38 * HI, (255, 255, 200), (120, 210, 110), (40, 100, 50))
            self.sub = hifi.text("SLOW DOWN AND STAY A WHILE", 10 * HI, (60, 90, 60), outline=(255, 255, 240))
            self.cam_h = 50

    def cues(self, t):
        return {1: ['whoosh'], 150: ['item']}.get(t, [])

    def _cyl(self, w, h, col, stripes=None):
        key = (int(w) // 3 * 3, int(h) // 3 * 3, col, stripes)
        s = self.cyl.get(key)
        if s is None:
            if len(self.cyl) > 200:
                self.cyl.clear()
            s = self.cyl[key] = _cylinder(max(2, key[0]), max(2, key[1]), col, stripes)
        return s

    def draw(self, hr, t):
        if t >= self.LENGTH:
            self.done = True
        hifi.warm(10 ** 6)
        travel = ease_io(t / self.LENGTH) * 1500
        horizon = H * 0.46
        hr.blit(self.bg, (0, 0))
        if self.kind == 'turtle':
            hr.blit(self.sea, (0, horizon - self.sea.get_height() + 2))
            hifi.add_glow(hr, (120, 100, 60), W * 0.75, H * 0.12, 70 * HI)
            pygame.draw.circle(hr, (255, 252, 230), (int(W * 0.75), int(H * 0.12)), 14 * HI)
        else:
            for img, x, sp in self.rays:
                hr.blit(img, (x + math.sin(t * 0.008 * sp + x) * 40 * HI - img.get_width() / 2, 0),
                        special_flags=pygame.BLEND_RGB_ADD)
        cam_h = self.cam_h * HI
        self.ground.draw(hr, horizon, cam_h, travel * 3.0, 0)
        cx, cy = W / 2, horizon
        items = []
        for th in self.things:
            zr = th['z'] * HI - travel * HI
            if zr < 40 * HI:
                continue
            k = F / zr
            sx = cx + th['x'] * HI * k
            gy = cy + cam_h * k                      # where it meets the ground
            kind = th['k']
            if kind in ('dome', 'shell'):
                r = th['r'] * HI * k

                def fn(s, sx=sx, gy=gy, r=r, col=th['c'], shell=(kind == 'shell')):
                    img = hifi.Turtle3D(shell=col)._shell_img(r, r * 0.85) if shell else hifi.ball(col, r)
                    hgt = img.get_height()
                    s.blit(img, (sx - img.get_width() / 2, gy - hgt / 2 - 2), (0, 0, img.get_width(), hgt / 2 + 2))
                    dr = r * 0.32
                    pygame.draw.ellipse(s, (40, 20, 30), (sx - dr / 2, gy - dr * 1.1, dr, dr * 1.1))
                    if not shell:
                        for wx in (-0.5, 0.5):
                            hifi.add_glow(s, (120, 100, 50), sx + wx * r, gy - r * 0.5, r * 0.25)
                            pygame.draw.circle(s, (255, 240, 170), (int(sx + wx * r), int(gy - r * 0.5)),
                                               max(1, int(r * 0.09)))
                items.append((zr, fn))
            elif kind == 'tower':
                w_, h_ = th['r'] * 0.9 * HI * k, th['h'] * HI * k

                def fn(s, sx=sx, gy=gy, w_=w_, h_=h_, col=th['c']):
                    img = self._cyl(w_, h_, col)
                    s.blit(img, (sx - img.get_width() / 2, gy - img.get_height()))
                    cap = hifi.ball(mix(col, (255, 255, 255), 0.3), w_ * 0.62)
                    s.blit(cap, (sx - cap.get_width() / 2, gy - h_ - cap.get_height() * 0.5),
                           (0, 0, cap.get_width(), cap.get_height() * 0.5))
                    for j in range(1, 4):
                        y = gy - h_ * j / 4
                        hifi.add_glow(s, (110, 90, 40), sx, y, w_ * 0.2)
                        pygame.draw.circle(s, (255, 236, 160), (int(sx), int(y)), max(1, int(w_ * 0.08)))
                items.append((zr, fn))
            elif kind == 'hall':
                r = th['r'] * HI * k

                def fn(s, sx=sx, gy=gy, r=r):
                    base = self._cyl(r * 2.2, r * 0.55, (230, 220, 240))
                    s.blit(base, (sx - base.get_width() / 2, gy - base.get_height()))
                    for c in range(-4, 5):
                        x = sx + c * r * 0.24
                        pygame.draw.line(s, (255, 255, 255), (x, gy - r * 0.55), (x, gy), max(1, int(r * 0.05)))
                    dome = hifi.ball((255, 200, 80), r * 0.9)
                    s.blit(dome, (sx - dome.get_width() / 2, gy - r * 0.55 - dome.get_height() / 2),
                           (0, 0, dome.get_width(), dome.get_height() / 2))
                    hifi.add_glow(s, (90, 70, 20), sx, gy - r, r * 0.6)
                items.append((zr, fn))
            elif kind == 'palm':
                h_ = th['h'] * HI * k

                def fn(s, sx=sx, gy=gy, h_=h_, ph=th['r']):
                    pts = [(sx + math.sin(j / 8 * 1.2 + ph) * h_ * 0.12 * j / 8, gy - h_ * j / 8) for j in range(9)]
                    for j, (x, y) in enumerate(pts[:-1]):
                        hifi.blit_ball(s, (150, 110, 60), x, y, max(1, h_ * 0.05 * (1 - j / 14)), None, 0.3)
                    tx, ty = pts[-1]
                    for a in range(7):
                        ang = a / 7 * math.tau + t * 0.01
                        lx = tx + math.cos(ang) * h_ * 0.4
                        ly = ty + math.sin(ang) * h_ * 0.16 + h_ * 0.1
                        pygame.draw.polygon(s, (60, 150, 60), [(tx, ty), (lx, ly), ((tx + lx) / 2, (ty + ly) / 2 - h_ * 0.06)])
                        pygame.draw.line(s, (40, 110, 40), (tx, ty), (lx, ly), max(1, int(h_ * 0.012)))
                    for a in range(3):
                        hifi.blit_ball(s, (130, 90, 40), tx + (a - 1) * h_ * 0.04, ty + h_ * 0.03, h_ * 0.03)
                items.append((zr, fn))
            elif kind == 'lighthouse':
                w_, h_ = th['r'] * HI * k, th['h'] * HI * k

                def fn(s, sx=sx, gy=gy, w_=w_, h_=h_):
                    img = self._cyl(w_, h_, (245, 245, 245), (230, 60, 60))
                    s.blit(img, (sx - img.get_width() / 2, gy - img.get_height()))
                    hifi.add_glow(s, (160, 140, 60), sx, gy - h_, w_ * 1.6)
                    pygame.draw.circle(s, (255, 250, 200), (int(sx), int(gy - h_)), max(2, int(w_ * 0.35)))
                items.append((zr, fn))
            elif kind == 'octo':
                size = 13 * HI
                items += th['m'].items((th['x'] * HI, cam_h - size * 1.1 + math.sin(t * 0.08 + th['ph']) * 3 * HI, zr),
                                       yaw=math.sin(t * 0.03 + th['ph']) * 0.5, t=t + th['ph'] * 20, size=size,
                                       wave=0.5 + 0.5 * math.sin(t * 0.1 + th['ph']), cx=cx, cy=cy)
            elif kind == 'turtle':
                size = 12 * HI
                items += th['m'].items((th['x'] * HI, cam_h - size * 0.85, zr), yaw=math.sin(t * 0.02 + th['ph']) * 0.8,
                                       t=t + th['ph'] * 10, size=size, walk=1.0, cx=cx, cy=cy)
        hifi.render(hr, items)
        if t > 40:                                   # the name drops in
            u = t - 40
            y = H * 0.2 - (1 - ease(u / 40)) * 120 * HI + math.sin(t * 0.05) * 2 * HI
            hr.blit(self.title, (W / 2 - self.title.get_width() / 2, y))
            if u == 40:
                self.sparkles.burst(W / 2, y + self.title.get_height() / 2, 26)
            if u > 50:
                img = self.sub.copy()
                img.set_alpha(int(255 * clamp((u - 50) / 30)))
                hr.blit(img, (W / 2 - img.get_width() / 2, y + self.title.get_height() + 2 * HI))
        self.sparkles.draw(hr)
        bar = int(12 * HI * min(1.0, t / 20, (self.LENGTH - t) / 20))
        if bar > 0:
            pygame.draw.rect(hr, (0, 0, 0), (0, 0, W, bar))
            pygame.draw.rect(hr, (0, 0, 0), (0, H - bar, W, bar))
        if t < 16:
            veil(hr, (0, 0, 0), 255 * (1 - t / 16))
        if t > self.LENGTH - 20:
            veil(hr, (0, 0, 0), (t - self.LENGTH + 20) * 13)


# ======================================================================
# milestone medal
# ======================================================================
def _medal_face(d, label, back=False):
    s = pygame.Surface((d, d), pygame.SRCALPHA)
    r = d // 2
    for i in range(r, 0, -1):                        # a domed, metallic disc
        k = i / r
        pygame.draw.circle(s, mix((255, 248, 200), (190, 120, 20), k ** 1.6),
                           (r - int((1 - k) * r * 0.25), r - int((1 - k) * r * 0.3)), i)
    pygame.draw.circle(s, (150, 90, 10), (r, r), r, max(2, d // 30))
    pygame.draw.circle(s, (255, 240, 170), (r, r), int(r * 0.82), max(1, d // 60))
    for a in range(36):                               # ridged rim
        ang = a / 36 * math.tau
        pygame.draw.line(s, (200, 140, 30), (r + math.cos(ang) * r * 0.86, r + math.sin(ang) * r * 0.86),
                         (r + math.cos(ang) * r * 0.97, r + math.sin(ang) * r * 0.97), max(1, d // 80))
    if back:
        txt = hifi.text3d("OCTO", d // 5, (255, 250, 210), (230, 160, 40), (140, 80, 10), outline=(90, 50, 0))
    else:
        pts = []
        for i in range(10):
            ang = -math.pi / 2 + i / 10 * math.tau
            rr = r * (0.5 if i % 2 == 0 else 0.22)
            pts.append((r + math.cos(ang) * rr, r * 0.86 + math.sin(ang) * rr))
        pygame.draw.polygon(s, (255, 236, 150), pts)
        pygame.draw.polygon(s, (170, 100, 10), pts, max(1, d // 70))
        txt = hifi.text(label, d // 7, (120, 60, 0), outline=(255, 240, 190), shadow=False)
    s.blit(txt, txt.get_rect(center=(r, r * (1.0 if back else 1.42))))
    return s


class MedalCut:
    """A gold medal spins in on a sunburst when the score passes a milestone."""
    LENGTH = 210

    def __init__(self, points, title, desc):
        d = 110 * HI
        self.front = _medal_face(d, f"{points:,}")
        self.back = _medal_face(d, "", back=True)
        self.edge = (170, 110, 20)
        rays = pygame.Surface((W, W), pygame.SRCALPHA)
        for i in range(16):
            a0, a1 = i / 16 * math.tau, (i + 0.5) / 16 * math.tau
            pygame.draw.polygon(rays, (255, 220, 120, 46),
                                [(W / 2, W / 2), (W / 2 + math.cos(a0) * W, W / 2 + math.sin(a0) * W),
                                 (W / 2 + math.cos(a1) * W, W / 2 + math.sin(a1) * W)])
        self.rays = rays
        self.head = hifi.text3d("MILESTONE!", 28 * HI, (255, 250, 200), (255, 170, 50), (140, 60, 10))
        self.title = hifi.text("UNLOCKED: " + title, 12 * HI, (170, 255, 190))
        self.desc = [hifi.text(line, 8 * HI, (235, 240, 255), shadow=False) for line in gfx.wrap(desc, 40)[:3]]
        self.sparkles = Sparkles()
        self.done = False

    def cues(self, t):
        return {1: ['item'], 60: ['key']}.get(t, [])

    def draw(self, hr, t):
        if t >= self.LENGTH:
            self.done = True
            return
        fade = min(1.0, t / 14, (self.LENGTH - t) / 16)
        hr.fill((4, 6, 20, int(190 * fade)))
        cx, cy = W / 2, H * 0.42
        rays = pygame.transform.rotozoom(self.rays, t * 0.6, 1.0)
        rays.set_alpha(int(255 * fade))
        hr.blit(rays, rays.get_rect(center=(cx, cy)))
        spin = (1 - ease(t / 90)) * math.tau * 3       # spins fast, slows, settles facing us
        c = math.cos(spin)
        face = self.front if c >= 0 else self.back
        d = face.get_width()
        drop = (1 - ease(t / 30)) * -H * 0.6
        w = max(2, int(d * abs(c)))
        th = int(d * 0.06 * (1 - abs(c)) + 2 * HI)
        y = cy - d / 2 + drop + math.sin(t * 0.06) * 3 * HI
        for k in range(th, 0, -1):                     # the coin's edge, seen as it turns
            pygame.draw.ellipse(hr, mix(self.edge, (0, 0, 0), 0.3 * k / th),
                                (cx - w / 2 + (k if c >= 0 else -k), y, w, d))
        img = pygame.transform.smoothscale(face, (w, d))
        img.set_alpha(int(255 * fade))
        hr.blit(img, (cx - w / 2, y))
        if t == 60:
            self.sparkles.burst(cx, cy, 34, (255, 230, 140), 4)
        if t > 60 and random.random() < 0.4:
            self.sparkles.twinkle(cx + random.uniform(-d / 2, d / 2), y + random.uniform(0, d))
        self.sparkles.draw(hr)
        if t > 20:
            img = self.head.copy()
            img.set_alpha(int(255 * fade * clamp((t - 20) / 16)))
            hr.blit(img, img.get_rect(center=(cx, 18 * HI + img.get_height() / 2)))
        if t > 70:
            a = int(255 * fade * clamp((t - 70) / 20))
            yy = cy + d / 2 + 10 * HI
            for img in [self.title] + self.desc:
                im = img.copy()
                im.set_alpha(a)
                hr.blit(im, im.get_rect(center=(cx, yy + im.get_height() / 2)))
                yy += im.get_height() + HI
