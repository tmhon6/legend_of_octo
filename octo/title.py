"""The title screen: a layered undersea scene drawn in code.

Static layers (water gradient, distant rocks, sea floor, vignette) are built once, at full resolution;
light rays, kelp, the anemone, fish, drifting specks and Octo are animated every frame, all drawn at
full resolution so everything moves smoothly. The logo and Octo are 3D (draw_hifi).
"""
import math
import random

import pygame

import gfx
from settings import AUTHOR, HI, SCREEN_H, SCREEN_W, VERSION

W, H = SCREEN_W, SCREEN_H
FLOOR_Y = 192              # where the sand starts


def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _gradient(stops, h=H, w=W):
    """Vertical gradient through (y_fraction, colour) stops."""
    s = pygame.Surface((w, h))
    for y in range(h):
        f = y / (h - 1)
        for (f0, c0), (f1, c1) in zip(stops, stops[1:]):
            if f0 <= f <= f1:
                c = _lerp(c0, c1, (f - f0) / ((f1 - f0) or 1))
                break
        pygame.draw.line(s, c, (0, y), (w, y))
    return s


class TitleScene:
    def __init__(self):
        rnd = random.Random(7)
        self.rnd = rnd
        self.bg = self._backdrop(rnd)
        self.rays = [self._ray(rnd.randint(10, 26), rnd.uniform(0.18, 0.32)) for _ in range(5)]
        self.ray_x = [rnd.randint(-20, W) for _ in self.rays]
        self.vignette = self._vignette()
        self.snow = [[rnd.uniform(0, W), rnd.uniform(0, FLOOR_Y), rnd.uniform(0.05, 0.25), rnd.random()]
                     for _ in range(55)]
        self.fish = self._schools(rnd)
        self.kelp = [(x, h, rnd.uniform(0, 6), far) for x, h, far in
                     ((6, 120, False), (20, 96, False), (34, 70, True), (222, 80, True),
                      (236, 112, False), (249, 90, False), (60, 50, True), (196, 58, True))]
        self.shark = self._shark_silhouette()
        self._octo_cache = {}
        self._hi_cache = {}

    # ---- static layers -----------------------------------------------------
    def _backdrop(self, rnd):
        s = _gradient([(0.0, (70, 170, 210)), (0.06, (34, 112, 172)), (0.45, (14, 52, 112)),
                       (1.0, (4, 14, 40))])
        # far rock ridges, fading into the blue
        for depth, col, base, amp in ((0, (18, 52, 100), 150, 22), (1, (12, 38, 80), 168, 18),
                                      (2, (8, 28, 62), 180, 14)):
            pts = [(0, H)]
            for x in range(0, W + 8, 8):
                y = base - amp * (0.5 + 0.5 * math.sin(x * 0.021 + depth * 2.1)) \
                    - rnd.randint(0, 6) - 10 * math.sin(x * 0.007 + depth)
                pts.append((x, y))
            pts.append((W, H))
            pygame.draw.polygon(s, col, pts)
        # a far-off sunken arch on the ridge
        pygame.draw.rect(s, (16, 46, 92), (166, 128, 6, 30))
        pygame.draw.rect(s, (16, 46, 92), (190, 132, 6, 26))
        pygame.draw.rect(s, (16, 46, 92), (162, 122, 38, 7))
        pygame.draw.rect(s, (20, 56, 104), (162, 122, 38, 2))
        return s

    def _build_floor(self):
        """The sand with its ripples, rocks, corals, shells and a starfish, drawn at twice full
        resolution and smoothed down, so every edge is soft. A generator: it pauses between parts
        (Game.warm_up builds it during the opening). Coordinates are title pixels from the top of
        the sand."""
        rnd = random.Random(5)
        S = HI * 2
        top = FLOOR_Y - 12
        h = H - top
        s = pygame.Surface((W * S, h * S), pygame.SRCALPHA)

        def R(x, y, w, hh):
            return pygame.Rect(round(x * S), round(y * S), max(1, round(w * S)), max(1, round(hh * S)))

        def soft(rect, rgba):                     # a see-through ellipse, blended onto the sand
            tmp = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.ellipse(tmp, rgba, tmp.get_rect())
            s.blit(tmp, rect.topleft)

        # the sand, under a wavy dune edge with a sunlit crest
        edge = [(x, 10 + 4 * math.sin(x * 0.05) + 3 * math.sin(x * 0.13 + 1)) for x in range(0, W + 3, 2)]
        pygame.draw.polygon(s, (255, 255, 255, 255), [(0, h * S)] + [(x * S, y * S) for x, y in edge] + [(W * S, h * S)])
        s.blit(_gradient([(0, (206, 184, 130)), (0.3, (156, 134, 94)), (1, (72, 56, 42))], h=h * S, w=W * S),
               (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        pygame.draw.lines(s, (236, 220, 172, 255), False, [(x * S, (y + 0.55) * S) for x, y in edge], max(1, S // 2))
        yield

        def sand(x, y):
            c = s.get_at((min(W * S - 1, int(x * S)), min(h * S - 1, int(y * S))))
            return c if c.a == 255 else None

        def shift(c, d):
            return (max(0, min(255, c.r + d)), max(0, min(255, c.g + int(d * 0.9))), max(0, min(255, c.b + int(d * 0.7))), 255)

        # ripples: a lit crest with its shadow just below
        for i in range(7):
            y = 18.5 + i * 4.6
            x = rnd.uniform(-4, 16)
            while x < W:
                w = rnd.uniform(11, 16)
                c = sand(x + w / 2, y + 1)
                if c:
                    pygame.draw.arc(s, shift(c, -26), R(x, y + 0.7, w, 4), 0.4, 2.75, max(1, S // 2))
                    pygame.draw.arc(s, shift(c, 22), R(x, y, w, 4), 0.55, 2.6, max(1, S // 3))
                x += rnd.uniform(24, 38)
        yield
        # grains of sand
        for k in range(1500):
            x, y = rnd.uniform(0, W), rnd.uniform(6, h)
            c = sand(x, y)
            if c:
                pygame.draw.circle(s, shift(c, rnd.choice((-24, -14, 12, 20))), (x * S, y * S), S * rnd.uniform(0.22, 0.42))
            if k % 500 == 499:
                yield
        # rocks, each with a shadow, a lit top, a glint and a few tufts of weed
        for x, y, rw, rh in ((40, 18, 26, 14), (196, 14, 34, 18), (120, 30, 14, 7), (226, 30, 16, 8)):
            soft(R(x - 2, y + rh - 4.5, rw + 6, 7), (24, 16, 10, 95))
            pygame.draw.ellipse(s, (34, 44, 68), R(x, y, rw, rh))
            pygame.draw.ellipse(s, (56, 70, 100), R(x + 1, y + 0.5, rw - 3.5, rh * 0.74))
            pygame.draw.ellipse(s, (80, 96, 128), R(x + 2.5, y + 1.1, rw * 0.5, rh * 0.4))
            pygame.draw.ellipse(s, (124, 140, 170), R(x + 4, y + 1.8, rw * 0.2, rh * 0.15))
            for _ in range(rw // 7):
                gx = x + rnd.uniform(3, rw - 3)
                for d in (-0.7, 0, 0.7):
                    pygame.draw.line(s, (70, 130, 76, 255), (gx * S, (y + 1.6) * S), ((gx + d * 1.6) * S, (y - 0.8 + abs(d)) * S), max(1, S // 3))
            yield
        self._coral_branchy(s, S, 33, 24, (240, 98, 116), rnd)
        yield
        self._coral_fan(s, S, 72, 22, (250, 140, 64), rnd)
        yield
        self._coral_brain(s, S, 211, 32, (218, 176, 98), rnd)
        self._coral_branchy(s, S, 228, 24, (196, 104, 228), rnd, 0.8)
        yield
        # the anemone's stalk (its waving arms are drawn every frame)
        ax, ay = 182, 26
        soft(R(ax - 5.5, ay - 0.5, 11, 3.5), (24, 16, 10, 80))
        pygame.draw.ellipse(s, (150, 52, 92), R(ax - 3.2, ay - 3.5, 6.4, 5))
        pygame.draw.ellipse(s, (190, 82, 124), R(ax - 2.2, ay - 3.2, 3, 3.6))
        # a starfish and some shells
        self._starfish(s, S, 104, 37)
        for x, y, col in ((58, 35, (244, 228, 204)), (150, 38, (236, 196, 200)), (192, 41, (240, 222, 190))):
            soft(R(x - 0.5, y + 2.2, 7, 2.2), (24, 16, 10, 70))
            base = (x + 3, y + 3.4)
            fan = [(base[0] * S, base[1] * S)]
            for k in range(9):
                a = math.pi + k / 8 * math.pi
                fan.append(((base[0] + math.cos(a) * 3.4) * S, (base[1] + math.sin(a) * 3.0) * S))
            pygame.draw.polygon(s, col, fan)
            for k in range(1, 8):                 # the ridges
                a = math.pi + k / 8 * math.pi
                pygame.draw.line(s, _lerp(col, (150, 110, 90), 0.5), (base[0] * S, base[1] * S),
                                 ((base[0] + math.cos(a) * 3.2) * S, (base[1] + math.sin(a) * 2.8) * S), max(1, S // 4))
            pygame.draw.rect(s, _lerp(col, (150, 110, 90), 0.35), R(base[0] - 1.2, base[1] - 0.4, 2.4, 1.2))
        yield
        self._hi_cache['floor'] = pygame.transform.smoothscale(s, (W * HI, h * HI))

    @staticmethod
    def _coral_branchy(s, S, x, y, col, rnd, size=1.0):
        """Branching coral: rounded limbs, shaded on the side away from the light, with pale polyps
        at the tips."""
        segs, tips = [], []

        def grow(x0, y0, a, ln, w, depth):
            x1, y1 = x0 + math.cos(a) * ln, y0 + math.sin(a) * ln
            segs.append((x0, y0, x1, y1, w))
            if depth <= 1:
                tips.append((x1, y1, w))
                return
            spread = ((-0.5, 0.74), (0.4, 0.7)) if depth % 2 else ((-0.36, 0.72), (0.52, 0.74))
            for da, k in spread:
                grow(x1, y1, a + da + rnd.uniform(-0.12, 0.12), ln * k, w * 0.76, depth - 1)

        grow(x, y, -math.pi / 2 + rnd.uniform(-0.12, 0.12), 6.5 * size, 2.5 * size, 4)
        dark, light = _lerp(col, (40, 12, 40), 0.5), _lerp(col, (255, 244, 236), 0.45)

        def stroke(c, dx, dy, k):
            for x0, y0, x1, y1, w in segs:
                r = max(1.0, w * k * S / 2)
                a, b = ((x0 + dx) * S, (y0 + dy) * S), ((x1 + dx) * S, (y1 + dy) * S)
                pygame.draw.line(s, c, a, b, max(1, int(r * 2)))
                pygame.draw.circle(s, c, a, r)
                pygame.draw.circle(s, c, b, r)

        stroke(dark, 0.45, 0.25, 1.3)
        stroke(col, 0, 0, 1.0)
        stroke(light, -0.3 * size, -0.25, 0.4)
        for x1, y1, w in tips:
            pygame.draw.circle(s, light, (x1 * S, y1 * S), max(1, w * 0.6 * S))
            pygame.draw.circle(s, (255, 252, 246), ((x1 - 0.2) * S, (y1 - 0.25) * S), max(1, w * 0.25 * S))

    @staticmethod
    def _coral_fan(s, S, x, y, col, rnd):
        """A sea fan: a lacy fan of fine branches joined into a net."""
        lines, ends = [], {}

        def grow(x0, y0, a, ln, depth):
            x1, y1 = x0 + math.cos(a) * ln, y0 + math.sin(a) * ln
            lines.append((x0, y0, x1, y1, depth))
            ends.setdefault(depth, []).append((a, x1, y1))
            if depth:
                grow(x1, y1, a - 0.26 + rnd.uniform(-0.06, 0.06), ln * 0.82, depth - 1)
                grow(x1, y1, a + 0.26 + rnd.uniform(-0.06, 0.06), ln * 0.82, depth - 1)

        pygame.draw.ellipse(s, (60, 40, 30), (int((x - 2) * S), int((y - 0.6) * S), 4 * S, int(1.6 * S)))
        for a in (-2.25, -1.85, -1.45, -1.05):
            grow(x, y, a, 4.2, 4)
        dark, light = _lerp(col, (60, 16, 20), 0.45), _lerp(col, (255, 236, 210), 0.4)
        for depth in (1, 2):                      # the net between neighbouring twigs
            row = sorted(ends.get(depth, []))
            for (a0, x0, y0), (a1, x1, y1) in zip(row, row[1:]):
                pygame.draw.line(s, _lerp(col, dark, 0.3), (x0 * S, y0 * S), (x1 * S, y1 * S), max(1, S // 4))
        for x0, y0, x1, y1, depth in lines:
            w = max(1, int(S * (0.35 + depth * 0.18)))
            pygame.draw.line(s, dark, ((x0 + 0.25) * S, (y0 + 0.2) * S), ((x1 + 0.25) * S, (y1 + 0.2) * S), w)
        for x0, y0, x1, y1, depth in lines:
            w = max(1, int(S * (0.25 + depth * 0.14)))
            pygame.draw.line(s, col if depth else light, (x0 * S, y0 * S), (x1 * S, y1 * S), w)

    @staticmethod
    def _coral_brain(s, S, x, y, col, rnd):
        """A brain coral: a squat dome with winding grooves, lit from above."""
        rw, rh = 17, 10
        rect = pygame.Rect(int((x - rw / 2) * S), int((y - rh) * S), rw * S, int(rh * 1.25 * S))
        tmp = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.ellipse(tmp, (24, 16, 10, 90), (0, int(rh * 0.55 * S), rw * S, int(rh * 0.7 * S)))
        body = pygame.Surface(rect.size, pygame.SRCALPHA)
        dome = (int(0.5 * S), 0, int((rw - 1) * S), int(rh * 1.15 * S))
        pygame.draw.ellipse(body, _lerp(col, (60, 36, 20), 0.45) + (255,), dome)
        pygame.draw.ellipse(body, col + (255,), (int(1.2 * S), int(0.3 * S), int((rw - 3) * S), int(rh * 0.95 * S)))
        pygame.draw.ellipse(body, _lerp(col, (255, 246, 220), 0.35) + (255,), (int(3 * S), int(0.8 * S), int(rw * 0.5 * S), int(rh * 0.45 * S)))
        groove = _lerp(col, (70, 40, 20), 0.55) + (255,)
        ridge = _lerp(col, (255, 246, 220), 0.4) + (255,)
        for k in range(9):                        # winding grooves that follow the dome, with lit ridges
            yy = 0.9 + k * 1.2
            pts = []
            for i in range(rw * 3 + 1):
                u = i / 3
                bend = ((u - rw / 2) / (rw / 2)) ** 2 * 1.3
                pts.append((u, yy + bend + 0.42 * math.sin(u * 1.15 + k * 0.55) + 0.14 * math.sin(u * 2.7 + k * 0.8)))
            pygame.draw.lines(body, ridge, False, [(u * S, (v - 0.35) * S) for u, v in pts], max(1, S // 4))
            pygame.draw.lines(body, groove, False, [(u * S, v * S) for u, v in pts], max(1, S // 3))
        mask = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.ellipse(mask, (255, 255, 255, 255), dome)
        body.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        tmp.blit(body, (0, 0))
        s.blit(tmp, rect.topleft)

    @staticmethod
    def _starfish(s, S, x, y):
        def star(r_out, r_in, dx=0.0, dy=0.0):
            pts = []
            for i in range(10):
                a = i / 10 * math.tau - math.pi / 2 + 0.25
                r = r_out if i % 2 == 0 else r_in
                pts.append(((x + dx + math.cos(a) * r) * S, (y + dy + math.sin(a) * r * 0.78) * S))
            return pts
        pygame.draw.polygon(s, (120, 50, 26), star(6.2, 2.6, 0.4, 0.4))
        pygame.draw.polygon(s, (236, 116, 58), star(6.0, 2.5))
        pygame.draw.polygon(s, (250, 162, 96), star(3.8, 1.6, -0.25, -0.3))
        for i in range(5):                        # bumps along each arm
            a = i / 5 * math.tau - math.pi / 2 + 0.25
            for r in (1.8, 3.2, 4.5):
                pygame.draw.circle(s, (255, 214, 160), ((x + math.cos(a) * r) * S, (y + math.sin(a) * r * 0.78) * S), max(1, S * 0.3))

    def _ray(self, width, slant):
        """A soft sunbeam: brightest near the surface, fading out with depth."""
        h = FLOOR_Y + 10
        s = pygame.Surface((W + 120, h))
        s.fill((0, 0, 0))
        for y in range(h):
            fade = (1 - y / h) ** 1.6
            x0 = 20 + y * slant
            wv = width + y * 0.12
            c = int(34 * fade)
            pygame.draw.line(s, (c // 2, c, c), (x0, y), (x0 + wv, y))
            pygame.draw.line(s, (c // 4, c // 2, c // 2), (x0 - 3, y), (x0 + wv + 3, y))
        return s

    def _vignette(self):
        v = pygame.Surface((W, H), pygame.SRCALPHA)
        for i in range(26):
            a = int(110 * (1 - i / 26) ** 2)
            pygame.draw.rect(v, (0, 0, 10, a), (i, i, W - 2 * i, H - 2 * i), 1)
        return v

    def _schools(self, rnd):
        schools = []
        for far, col, y, n, speed in ((True, (20, 60, 110), 70, 9, 0.25), (True, (24, 70, 120), 112, 7, -0.3),
                                      (False, (250, 170, 60), 150, 6, 0.45)):
            members = [(rnd.uniform(-18, 18), rnd.uniform(-8, 8), rnd.uniform(0, 6)) for _ in range(n)]
            schools.append({'x': rnd.uniform(0, W), 'y': y, 'speed': speed, 'col': col, 'far': far,
                            'members': members})
        return schools

    def _shark_silhouette(self):
        img = gfx.SPR['shark']['swim'][0]
        img = pygame.transform.scale(img, (img.get_width() * 2 // 3, img.get_height() * 2 // 3))
        sil = img.copy()
        sil.fill((14, 40, 82, 255), special_flags=pygame.BLEND_RGBA_MIN)
        sil.fill((0, 0, 0, 150), special_flags=pygame.BLEND_RGBA_MULT)
        return sil

    # ---- per frame, at full resolution ---------------------------------------
    def _hi(self, key, surf):
        """A static layer, smoothly scaled up to the full-resolution canvas once."""
        img = self._hi_cache.get(key)
        if img is None:
            w, h = surf.get_size()
            img = self._hi_cache[key] = pygame.transform.smoothscale(surf, (w * HI, h * HI))
        return img

    def _ray_hi(self, i):
        """A sunbeam at full resolution, trimmed to where it shines (most of its picture is black,
        which adds nothing): (image, its left edge in title pixels)."""
        img = self._hi_cache.get(('ray', i))
        if img is None:
            ray = self.rays[i]
            ray.set_colorkey((0, 0, 0))
            box = ray.get_bounding_rect()
            ray.set_colorkey(None)
            part = ray.subsurface(box)
            img = self._hi_cache[('ray', i)] = (pygame.transform.smoothscale(part, (box.w * HI, box.h * HI)), box.x)
        return img

    def _floor_img(self):
        if 'floor' not in self._hi_cache:
            for _ in self._build_floor():
                pass
        return self._hi_cache['floor']

    def warm(self):
        """Build the full-resolution layers a piece at a time (Game.warm_up runs this during the opening)."""
        for key, surf in (('bg', self.bg), ('vignette', self.vignette), ('shark', self.shark)):
            self._hi(key, surf)
            yield
        for i in range(len(self.rays)):
            self._ray_hi(i)
            yield
        if 'floor' not in self._hi_cache:
            yield from self._build_floor()

    def draw_full(self, c, t, menu, sel, mood, flip_w):
        """The whole title, straight onto the full-resolution canvas c: the undersea scene, the
        lettering and menu, then the 3D logo and Octo. Nothing is drawn at pixel-art size and
        scaled up, so everything moves smoothly, and there are no layers to merge afterwards."""
        c.blit(self._hi('bg', self.bg), (0, 0))
        st = t % 1500                                    # a shark patrols far away now and then
        if st < 700:
            c.blit(self._hi('shark', self.shark), ((-60 + st * 0.5) * HI, (104 + math.sin(st * 0.02) * 3) * HI))
        for x, h, ph, far in self.kelp:
            if far:
                self._kelp_hi(c, x, h, ph, t, True)
        for i in range(len(self.rays)):                  # sunbeams
            img, rx = self._ray_hi(i)
            x = (self.ray_x[i] + math.sin(t * 0.004 + i * 1.7) * 14) - 40 + rx
            c.blit(img, (x * HI, 0), special_flags=pygame.BLEND_RGB_ADD)
        pts = [(x * HI, (5 + math.sin(x * 0.09 + t * 0.05) * 1.5 + math.sin(x * 0.031 - t * 0.03)) * HI)
               for x in range(0, W + 3, 3)]              # the rippling surface far above
        pygame.draw.lines(c, (200, 240, 255), False, pts, max(1, HI // 2 + 1))
        for x in range(0, W, 23):
            gx = (x + t * 0.35) % W
            gy = 5 + math.sin(gx * 0.09 + t * 0.05) * 1.5 + math.sin(gx * 0.031 - t * 0.03)
            pygame.draw.circle(c, (255, 255, 255), (gx * HI, gy * HI + HI * 0.6), max(1, HI * 0.6))
        for sc in self.fish:                             # fish schools
            sc['x'] += sc['speed']
            if sc['x'] > W + 30:
                sc['x'] = -30
            elif sc['x'] < -30:
                sc['x'] = W + 30
            d = 1 if sc['speed'] > 0 else -1
            for ox, oy, ph in sc['members']:
                fx = sc['x'] + ox + math.sin(t * 0.05 + ph) * 2
                fy = sc['y'] + oy + math.sin(t * 0.07 + ph) * 1.5
                self._fish_hi(c, fx, fy, d, sc['col'], sc['far'], t + ph * 10)
        for p in self.snow:                              # marine snow
            p[1] += p[2]
            p[0] += math.sin(t * 0.01 + p[3] * 6) * 0.08
            if p[1] > FLOOR_Y:
                p[1], p[0] = 8, self.rnd.uniform(0, W)
            k = 90 + int(p[3] * 80)
            pygame.draw.circle(c, (k - 30, k, k + 30), ((p[0] % W) * HI, p[1] * HI), max(1, HI * 0.45))
        c.blit(self._floor_img(), (0, (FLOOR_Y - 12) * HI))
        if getattr(self, '_caustic_hi', None) is None:
            self._caustic_hi = pygame.Surface((W * HI, 30 * HI), pygame.SRCALPHA)
        cs = self._caustic_hi
        cs.fill((0, 0, 0, 0))
        for i in range(10):                              # light rippling over the sand
            cx = (i * 29 + math.sin(t * 0.02 + i) * 10) % W
            cy = 10 + math.sin(t * 0.03 + i * 2) * 5
            pygame.draw.ellipse(cs, (255, 240, 200, 22), (cx * HI, cy * HI, 16 * HI, 5 * HI))
        c.blit(cs, (0, (FLOOR_Y - 2) * HI))
        self._anemone_hi(c, t)
        for x, h, ph, far in self.kelp:
            if not far:
                self._kelp_hi(c, x, h, ph, t, False)
        bob = math.sin(t * 0.05) * 4                     # Octo's shadow on the sand
        sw = int((46 - bob * 2) * HI)
        sh = pygame.Surface((sw, 8 * HI), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 70), sh.get_rect())
        c.blit(sh, (W * HI // 2 - sw // 2, (FLOOR_Y + 6) * HI))
        v = self._hi('vignette', self.vignette)          # darker towards the edges (only the edges are drawn)
        b, (vw, vh) = 26 * HI, v.get_size()
        for r in ((0, 0, vw, b), (0, vh - b, vw, b), (0, b, b, vh - 2 * b), (vw - b, b, b, vh - 2 * b)):
            c.blit(v, r[:2], r)
        self._ui_hi(c, t, menu, sel)
        self.draw_hifi(c, t, mood, flip_w)

    def _label(self, text, col, under=None):
        """A line of pixel lettering, scaled up once (crisp, not blurred) and kept."""
        key = ('label', text, col, under)
        img = self._hi_cache.get(key)
        if img is None:
            small = pygame.Surface((gfx.text_width(text) + 3, 10), pygame.SRCALPHA)
            if under:
                gfx.text(small, text, 1, 1, under)
            gfx.text(small, text, 0, 0, col)
            img = self._hi_cache[key] = pygame.transform.scale(small, (small.get_width() * HI, 10 * HI))
        return img

    def _put(self, c, text, x, y, col, under=None, center=False):
        img = self._label(text, col, under)
        if center:
            x -= (img.get_width() // HI - 3) // 2
        c.blit(img, (x * HI, y * HI))

    def _ui_hi(self, c, t, menu, sel):
        """The subtitles and the menu, in crisp pixel lettering."""
        self._put(c, "A REVERSIBLE UNDERSEA ADVENTURE", W // 2, 88, (200, 230, 255), (0, 10, 30), True)
        self._put(c, "A FAN TRIBUTE TO 8-BIT ADVENTURES", W // 2, 99, (140, 160, 200), (0, 10, 30), True)
        # the menu box, sized to fit its words, sitting clear of the credit line
        inner = max(gfx.text_width(m) for m in menu)
        pw = inner + 34
        ph = 11 * len(menu) + 8
        px, py = W // 2 - pw // 2, H - 13 - ph
        box = self._hi_cache.get(('box', pw, ph))
        if box is None:
            box = self._hi_cache[('box', pw, ph)] = pygame.Surface((pw * HI, ph * HI), pygame.SRCALPHA)
            pygame.draw.rect(box, (4, 10, 30, 175), box.get_rect(), border_radius=3 * HI)
            pygame.draw.rect(box, (120, 160, 230, 220), box.get_rect(), max(1, HI - 1), border_radius=3 * HI)
        c.blit(box, (px * HI, py * HI))
        self.menu_rects = []
        for i, item in enumerate(menu):
            y = py + 6 + i * 11
            self.menu_rects.append(pygame.Rect(px, y - 2, pw, 11))
            tx = W // 2 - gfx.text_width(item) // 2
            on = i == sel
            if on:
                self._put(c, ">", tx - 9 + (1 if (t // 20) % 2 else 0), y, (255, 220, 120))
            self._put(c, item, tx, y, (255, 255, 255) if on else (140, 160, 200))
        if (t // 25) % 2:
            self._put(c, "TAP TO PLAY" if getattr(self, 'touch', False) else "PRESS ENTER OR CLICK TO PLAY",
                      W // 2, py - 10, (255, 255, 255), center=True)
        self._put(c, "BY " + AUTHOR, W // 2, H - 9, (150, 165, 200), center=True)
        self._put(c, VERSION.upper(), 4, H - 9, (100, 115, 150))

    # stem, stem highlight, blade at the root, blade at the top, blade highlight, gas floats
    KELP_NEAR = ((30, 84, 44), (96, 160, 76), (38, 112, 54), (128, 186, 76), (176, 220, 116), (178, 168, 66))
    KELP_FAR = ((14, 52, 62), None, (16, 64, 70), (28, 88, 86), None, None)

    @staticmethod
    def _curve_table(samples):
        """For points along a blade's curve: the weights of its root, bend and tip, and of the two
        halves of its direction, worked out once."""
        return [((1 - u) ** 2, 2 * (1 - u) * u, u * u, 2 * (1 - u), 2 * u) for u, _ in samples]

    _NEAR_SAMPLES = ((0.0, 0.2), (0.16, 0.8), (0.33, 1.0), (0.5, 0.95), (0.67, 0.8), (0.84, 0.5), (1.0, 0.0))
    _FAR_SAMPLES = ((0.0, 0.2), (0.33, 1.0), (0.67, 0.75), (1.0, 0.0))

    def _kelp_plan(self, h, ph, far):
        """What stays the same in a frond from frame to frame: its blades' sizes, colours and ruffles."""
        plan = self._hi_cache.get(('kelp', h, ph, far))
        if plan is None:
            stem, stem_hi, blade0, blade1, blade_hi, floatc = self.KELP_FAR if far else self.KELP_NEAR
            samples = self._FAR_SAMPLES if far else self._NEAR_SAMPLES
            n = max(8, h // 4)
            blades = []
            for i in range(2, n + 1, 2):
                f = i / n
                side = 1 if (i // 2) % 2 else -1
                if i == n:                       # the curled tip
                    side, length, half = 0, 5.0, 1.1
                else:
                    length, half = 12.0 - 5.0 * f, 1.45 - 0.35 * f
                if far:
                    length, half = length * 0.8, half * 0.85
                widths = [half * w * HI * (1 + 0.16 * math.sin(u * 17 + (i + ph) * 2.3)) for u, w in samples]
                col = _lerp(blade0, blade1, f)
                lit = _lerp(col, blade_hi, 0.45) if not far else None
                edge = _lerp(col, (10, 40, 20), 0.35) if not far else None
                blades.append((i, f, side, length, widths, col, lit, edge))
            plan = self._hi_cache[('kelp', h, ph, far)] = (n, blades, self._curve_table(samples))
        return plan

    def _kelp_hi(self, s, x, h, ph, t, far):
        """A kelp frond in the swell: a tapering stem with a wave running up it (so it bends like the
        real thing), long ruffled blades on alternate sides that float up and trail as it sways,
        each held up by a little gas float, and a curled tip. Soft edges, at full resolution. Far
        fronds are plainer and fade into the blue."""
        stem, stem_hi, blade0, blade1, blade_hi, floatc = self.KELP_FAR if far else self.KELP_NEAR
        n, blades, table = self._kelp_plan(h, ph, far)
        base = FLOOR_Y + 8
        pts = []
        for i in range(n + 1):
            f = i / n
            sway = (math.sin(t * 0.03 + ph - f * 2.2) * f ** 1.3 * h * 0.075
                    + math.sin(t * 0.017 + ph * 1.7 - f * 1.3) * f * h * 0.025)
            pts.append((x + sway, base - f * h))
        for i, f, side, length, widths, col, lit, edge in blades:     # (under the stem, which crosses their roots)
            px, py = pts[i]
            drift = (px - pts[i - 1][0]) * 2.0 + math.sin(t * 0.05 + ph * 3 + i * 0.8) * 0.3
            # buoyant blades float up and out, and their tips trail in the swell
            a0 = -math.pi / 2 + side * (0.62 - 0.2 * f) + drift * 0.2
            a1 = a0 + side * 0.32 + drift * 0.45
            c0, s0 = math.cos(a0) * length * 0.5, math.sin(a0) * length * 0.5
            cx, cy = px + c0, py + s0
            tx, ty = cx + math.cos(a1) * length * 0.55, cy + math.sin(a1) * length * 0.55
            poly, half_a, half_b = self._blade(px * HI, py * HI, cx * HI, cy * HI, tx * HI, ty * HI, widths, table)
            pygame.draw.polygon(s, col, poly)
            if not far:
                pygame.draw.polygon(s, lit, half_b if side > 0 else half_a)
                pygame.draw.aalines(s, edge, True, poly)
                if side:
                    fx, fy = px + c0 * 0.26, py + s0 * 0.26
                    pygame.draw.circle(s, floatc, (fx * HI, fy * HI), 1.15 * HI)
                    pygame.draw.circle(s, (236, 226, 150), ((fx - 0.35) * HI, (fy - 0.4) * HI), max(1, 0.4 * HI))
        left, right = [], []                     # the stem: a ribbon, narrower at the top
        for i, (px, py) in enumerate(pts):
            ax, ay = pts[i - 1] if i else pts[0]
            bx, by = pts[i + 1] if i < n else pts[n]
            dx, dy = bx - ax, by - ay
            k = (1.2 if far else 1.55) * (1 - 0.55 * i / n) / (math.hypot(dx, dy) or 1.0)
            nx, ny = -dy * k, dx * k
            left.append(((px + nx) * HI, (py + ny) * HI))
            right.append(((px - nx) * HI, (py - ny) * HI))
        ribbon = left + right[::-1]
        pygame.draw.polygon(s, stem, ribbon)
        if not far:
            pygame.draw.aalines(s, stem, True, ribbon)
            pygame.draw.aalines(s, stem_hi, False, [((px - 0.5) * HI, py * HI) for px, py in pts[1:-1]])

    @staticmethod
    def _blade(x0, y0, cx, cy, x2, y2, widths, table):
        """A long kelp blade along a curve from its root (x0, y0), bending through (cx, cy) to its tip
        (x2, y2), with the given (ruffled) widths along it: its outline and its two halves either
        side of the midrib (one is lit). All in full-resolution pixels."""
        side_a, side_b, mid = [], [], []
        ax, ay, bx, by = cx - x0, cy - y0, x2 - cx, y2 - cy
        for (k0, k1, k2, d0, d1), w in zip(table, widths):
            px = k0 * x0 + k1 * cx + k2 * x2
            py = k0 * y0 + k1 * cy + k2 * y2
            dx, dy = d0 * ax + d1 * bx, d0 * ay + d1 * by
            k = w / (math.hypot(dx, dy) or 1.0)
            nx, ny = -dy * k, dx * k
            side_a.append((px + nx, py + ny))
            side_b.append((px - nx, py - ny))
            mid.append((px, py))
        back = mid[-2::-1]
        return side_a + side_b[-2::-1], side_a + back, side_b + back

    def _anemone_hi(self, s, t):
        """The sea anemone on the sand, waving its arms."""
        bx, by = 182, FLOOR_Y + 11.5
        for i in range(11):
            a = -math.pi / 2 + (i - 5) * 0.22
            x, y = bx + (i - 5) * 0.42, by
            pts = [(x * HI, y * HI)]
            for k in range(1, 5):
                f = k / 4
                a += math.sin(t * 0.045 + i * 0.8 - f * 1.6) * 0.17 * f + (i - 5) * 0.025
                x += math.cos(a) * 2.0
                y += math.sin(a) * 2.0
                pts.append((x * HI, y * HI))
            pygame.draw.lines(s, (226, 112, 162), False, pts, max(1, int(HI * 0.95)))
            pygame.draw.aalines(s, (255, 178, 208), False, pts)
            pygame.draw.circle(s, (255, 216, 232), pts[-1], 0.7 * HI)
        pygame.draw.ellipse(s, (176, 66, 112), ((bx - 4) * HI, (by - 1.1) * HI, 8 * HI, 2.8 * HI))
        pygame.draw.ellipse(s, (214, 104, 146), ((bx - 2.6) * HI, (by - 0.8) * HI, 5.2 * HI, 1.4 * HI))

    def _fish_hi(self, s, x, y, d, col, small, t):
        x, y = x * HI, y * HI
        if small:
            k = HI * 0.6
            pygame.draw.polygon(s, col, [(x - 2 * d * k, y), (x, y - k), (x + 2 * d * k, y), (x, y + k)])
            return
        tail = math.sin(t * 0.3) * HI * 0.6                # a flicking tail
        body = [(x - 3 * d * HI, y), (x, y - 2 * HI), (x + 3 * d * HI, y), (x, y + 2 * HI)]
        pygame.draw.polygon(s, col, [(x - 3 * d * HI, y), (x - 6 * d * HI, y - 2 * HI + tail),
                                     (x - 6 * d * HI, y + 2 * HI + tail)])
        pygame.draw.polygon(s, col, body)
        pygame.draw.line(s, _lerp(col, (255, 255, 255), 0.5), (x - d * HI, y - HI), (x + d * HI, y - HI), max(1, HI // 2))
        pygame.draw.circle(s, (20, 20, 30), (x + 2 * d * HI, y - HI * 0.6), max(1, HI * 0.45))

    # ---- per frame ----------------------------------------------------------
    def _hifi_parts(self):
        """The hi-res logo and 3D Octos (built the first time the title is shown in hi-res)."""
        if getattr(self, '_hifi', None) is None:
            import hifi
            HI = hifi.HI
            words = []
            for word, px, top, bot, side, y in (("LEGEND OF", 24 * HI, (240, 248, 255), (130, 180, 240), (40, 70, 150), 13),
                                                ("OCTO", 62 * HI, (255, 244, 150), (250, 140, 40), (150, 60, 10), 28)):
                img = hifi.text3d(word, px, top, bot, side)
                words.append((img, hifi.W / 2 - img.get_width() / 2, y * HI))
            import voxel
            self._hifi = {'words': words, 'blue': voxel.VoxelFigure('blue'), 'mad': voxel.VoxelFigure('mad'),
                          'tmp': None}
        return self._hifi

    def draw_hifi(self, hr, t, mood, flip_w):
        """The smooth 3D logo and Octo, drawn on the hi-res canvas over the pixel-art scene."""
        import hifi
        HI = hifi.HI
        parts = self._hifi_parts()
        dest = hr
        for img, x, y in parts['words']:
            dest.blit(img, (x, y + math.sin(t * 0.03) * 1.5 * HI))
        spin = (1 - flip_w) * math.pi
        z = 400 * HI
        k = hifi.F / z
        bob = math.sin(t * 0.05) * 4 * HI
        cy = 134 * HI + bob
        items = parts[mood].items((0, (cy - hifi.H / 2) / k, z), yaw=math.sin(t * 0.02) * 0.45 + spin, pitch=0.18,
                                  t=t, size=26 * HI / k)
        hifi.render(dest, items)
        if t < 60:                                   # fade in from black (over everything)
            veil = pygame.Surface(hr.get_size(), pygame.SRCALPHA)
            veil.fill((0, 0, 0, int(255 * (1 - t / 60))))
            hr.blit(veil, (0, 0))
