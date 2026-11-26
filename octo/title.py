"""The title screen: a layered undersea scene drawn in code.

Static layers (water gradient, distant rocks, sea floor, vignette, logo) are built once;
light rays, kelp, fish, drifting specks and Octo are animated every frame.
"""
import math
import random

import pygame

import gfx
from settings import SCREEN_H, SCREEN_W

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
        self.floor = self._sea_floor(rnd)
        self.rays = [self._ray(rnd.randint(10, 26), rnd.uniform(0.18, 0.32)) for _ in range(5)]
        self.ray_x = [rnd.randint(-20, W) for _ in self.rays]
        self.vignette = self._vignette()
        self.logo = self._logo()
        self.snow = [[rnd.uniform(0, W), rnd.uniform(0, FLOOR_Y), rnd.uniform(0.05, 0.25), rnd.random()]
                     for _ in range(55)]
        self.fish = self._schools(rnd)
        self.kelp = [(x, h, rnd.uniform(0, 6), far) for x, h, far in
                     ((6, 120, False), (20, 96, False), (34, 70, True), (222, 80, True),
                      (236, 112, False), (249, 90, False), (60, 50, True), (196, 58, True))]
        self.shark = self._shark_silhouette()
        self._octo_cache = {}

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

    def _sea_floor(self, rnd):
        s = pygame.Surface((W, H - FLOOR_Y + 12), pygame.SRCALPHA)
        h = s.get_height()
        sand = _gradient([(0, (196, 172, 120)), (0.3, (150, 128, 88)), (1, (78, 62, 46))], h=h)
        # wavy dune edge
        mask = pygame.Surface((W, h), pygame.SRCALPHA)
        pts = [(0, h)]
        for x in range(0, W + 4, 4):
            pts.append((x, 10 + 4 * math.sin(x * 0.05) + 3 * math.sin(x * 0.13 + 1)))
        pts.append((W, h))
        pygame.draw.polygon(mask, (255, 255, 255, 255), pts)
        sand = sand.convert_alpha() if pygame.display.get_surface() else sand.copy()
        sand.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        s.blit(sand, (0, 0))
        # grain and ripples
        for _ in range(260):
            x, y = rnd.randrange(W), rnd.randrange(14, h)
            c = s.get_at((x, y))
            if c.a:
                d = rnd.choice((-18, 14))
                s.set_at((x, y), (max(0, min(255, c.r + d)), max(0, min(255, c.g + d)), max(0, min(255, c.b + d))))
        for i in range(7):
            y = 20 + i * 5
            for x in range(rnd.randint(0, 20), W, rnd.randint(26, 40)):
                pygame.draw.arc(s, (120, 100, 70), (x, y, 14, 4), 0.3, 2.8)
        # rocks
        for x, y, rw, rh in ((40, 18, 26, 14), (196, 14, 34, 18), (120, 30, 14, 7), (226, 30, 16, 8)):
            pygame.draw.ellipse(s, (40, 52, 78), (x, y, rw, rh))
            pygame.draw.ellipse(s, (66, 82, 112), (x + 2, y + 1, rw - 8, rh // 2))
            pygame.draw.ellipse(s, (26, 32, 50), (x + 2, y + rh - 3, rw - 4, 4))
        # coral
        def branch(x, y, a, length, col, depth):
            if depth == 0 or length < 2:
                return
            x2, y2 = x + math.cos(a) * length, y + math.sin(a) * length
            pygame.draw.line(s, col, (x, y), (x2, y2), max(1, depth - 1))
            branch(x2, y2, a - 0.45, length * 0.72, col, depth - 1)
            branch(x2, y2, a + 0.4, length * 0.7, col, depth - 1)
        for x, col in ((26, (232, 96, 110)), (78, (250, 150, 70)), (170, (220, 90, 180)), (212, (240, 110, 90))):
            branch(x, 22, -math.pi / 2, 9, col, 4)
            hi = _lerp(col, (255, 255, 255), 0.4)
            branch(x + 1, 22, -math.pi / 2 - 0.1, 7, hi, 2)
        # sea anemone, starfish and shells
        for i in range(9):
            a = -math.pi / 2 + (i - 4) * 0.22
            pygame.draw.line(s, (255, 170, 200), (140, 26), (140 + math.cos(a) * 9, 26 + math.sin(a) * 9), 2)
        pygame.draw.ellipse(s, (180, 70, 110), (135, 24, 11, 5))
        cx, cy = 100, 36
        for i in range(5):
            a = i / 5 * math.tau - math.pi / 2
            pygame.draw.line(s, (240, 120, 60), (cx, cy), (cx + math.cos(a) * 5, cy + math.sin(a) * 5), 2)
        pygame.draw.circle(s, (250, 170, 90), (cx, cy), 2)
        for x, y in ((60, 34), (186, 38), (152, 36)):
            pygame.draw.ellipse(s, (240, 225, 200), (x, y, 6, 4))
            pygame.draw.line(s, (200, 170, 140), (x + 3, y), (x + 3, y + 3))
        return s

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

    def _logo(self):
        def outlined(text, scale, top, bottom, outline=(14, 26, 66)):
            w = gfx.text_width(text) + 4
            small = pygame.Surface((w, 11), pygame.SRCALPHA)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    gfx.text(small, text, 2 + dx, 1 + dy, outline)
            fill = pygame.Surface((w, 11), pygame.SRCALPHA)
            gfx.text(fill, text, 2, 1, (255, 255, 255))
            grad = _gradient([(0, top), (1, bottom)], h=11, w=w).convert_alpha() \
                if pygame.display.get_surface() else _gradient([(0, top), (1, bottom)], h=11, w=w)
            fill.blit(grad, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            small.blit(fill, (0, 0))
            return pygame.transform.scale(small, (w * scale, 11 * scale))
        top = outlined("LEGEND OF", 2, (255, 240, 170), (230, 150, 40))
        big = outlined("OCTO", 4, (190, 225, 255), (40, 100, 230))
        shadow = big.copy()
        shadow.fill((0, 0, 20, 90), special_flags=pygame.BLEND_RGBA_MULT)
        w = max(top.get_width(), big.get_width()) + 8
        logo = pygame.Surface((w, top.get_height() + big.get_height() + 4), pygame.SRCALPHA)
        logo.blit(top, ((w - top.get_width()) // 2, 0))
        y = top.get_height() - 2
        logo.blit(shadow, ((w - big.get_width()) // 2 + 4, y + 4))
        logo.blit(big, ((w - big.get_width()) // 2, y))
        return logo

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

    # ---- per frame ----------------------------------------------------------
    def draw(self, scr, t, menu, sel, mood, flip_w):
        scr.blit(self.bg, (0, 0))
        # a shark patrols far away now and then
        st = t % 1500
        if st < 700:
            sx = -60 + st * 0.5
            scr.blit(self.shark, (sx, 104 + math.sin(st * 0.02) * 3))
        # far kelp
        for x, h, ph, far in self.kelp:
            if far:
                self._kelp(scr, x, h, ph, t, (14, 58, 64), (18, 70, 70))
        # sunbeams
        for i, ray in enumerate(self.rays):
            x = (self.ray_x[i] + math.sin(t * 0.004 + i * 1.7) * 14) - 40
            scr.blit(ray, (x, 0), special_flags=pygame.BLEND_RGB_ADD)
        # rippling surface
        for x in range(0, W, 2):
            y = 5 + math.sin(x * 0.09 + t * 0.05) * 1.5 + math.sin(x * 0.031 - t * 0.03)
            scr.set_at((x, int(y)), (200, 240, 255))
            if (x + t // 3) % 23 == 0:
                scr.set_at((x, int(y) + 1), (255, 255, 255))
        # fish schools
        for sc in self.fish:
            sc['x'] += sc['speed']
            if sc['x'] > W + 30:
                sc['x'] = -30
            elif sc['x'] < -30:
                sc['x'] = W + 30
            d = 1 if sc['speed'] > 0 else -1
            for ox, oy, ph in sc['members']:
                fx = sc['x'] + ox + math.sin(t * 0.05 + ph) * 2
                fy = sc['y'] + oy + math.sin(t * 0.07 + ph) * 1.5
                self._fish(scr, fx, fy, d, sc['col'], small=sc['far'])
        # marine snow
        for p in self.snow:
            p[1] += p[2]
            p[0] += math.sin(t * 0.01 + p[3] * 6) * 0.08
            if p[1] > FLOOR_Y:
                p[1], p[0] = 8, self.rnd.uniform(0, W)
            c = 90 + int(p[3] * 80)
            scr.set_at((int(p[0]) % W, int(p[1])), (c - 30, c, c + 30))
        # sea floor + shimmering light patches on the sand
        scr.blit(self.floor, (0, FLOOR_Y - 12))
        caustic = pygame.Surface((W, 30), pygame.SRCALPHA)
        for i in range(10):
            cx = (i * 29 + math.sin(t * 0.02 + i) * 10) % W
            cy = 10 + math.sin(t * 0.03 + i * 2) * 5
            pygame.draw.ellipse(caustic, (255, 240, 200, 22), (cx, cy, 16, 5))
        scr.blit(caustic, (0, FLOOR_Y - 2))
        # near kelp
        for x, h, ph, far in self.kelp:
            if not far:
                self._kelp(scr, x, h, ph, t, (24, 110, 60), (60, 160, 80))
        # Octo
        bob = math.sin(t * 0.05) * 4
        size = 64
        oy = 112 + bob
        shadow_w = int(46 - bob * 2)
        sh = pygame.Surface((shadow_w, 8), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 70), (0, 0, shadow_w, 8))
        scr.blit(sh, (W // 2 - shadow_w // 2, FLOOR_Y + 6))
        w = max(4, int(size * flip_w))
        key = (mood, (t // 16) % 2, w)
        img = self._octo_cache.get(key)
        if img is None:
            img = pygame.transform.scale(gfx.OCTO[mood]['down'][(t // 16) % 2], (w, size))
            if len(self._octo_cache) > 80:
                self._octo_cache.clear()
            self._octo_cache[key] = img
        scr.blit(img, (W // 2 - w // 2, oy))
        # logo
        lx = W // 2 - self.logo.get_width() // 2
        scr.blit(self.logo, (lx, 16 + math.sin(t * 0.03) * 1.5))
        gfx.text(scr, "A REVERSIBLE UNDERSEA ADVENTURE", W // 2 + 1, 89, (0, 10, 30), center=True)
        gfx.text(scr, "A REVERSIBLE UNDERSEA ADVENTURE", W // 2, 88, (200, 230, 255), center=True)
        scr.blit(self.vignette, (0, 0))
        # menu panel
        ph = 10 + len(menu) * 11
        panel = pygame.Surface((112, ph), pygame.SRCALPHA)
        panel.fill((4, 10, 30, 170))
        pygame.draw.rect(panel, (120, 160, 230, 200), panel.get_rect(), 1)
        px, py = W // 2 - 56, FLOOR_Y + 2 - ph // 2 + 10
        scr.blit(panel, (px, py))
        self.menu_rects = []
        for i, item in enumerate(menu):
            y = py + 6 + i * 11
            self.menu_rects.append(pygame.Rect(px, y - 2, 112, 11))
            on = i == sel
            if on:
                arrow = ">" if (t // 20) % 2 else " >"
                gfx.text(scr, arrow, px + 10, y, (255, 220, 120))
            gfx.text(scr, item, W // 2 + 4, y, (255, 255, 255) if on else (140, 160, 200), center=True)
        if (t // 25) % 2:
            gfx.text(scr, "TAP TO PLAY" if getattr(self, 'touch', False) else "PRESS ENTER OR CLICK TO PLAY", W // 2, py - 10, (255, 255, 255), center=True)
        gfx.text(scr, "A FAN TRIBUTE", W // 2, H - 8, (110, 120, 150), center=True)
        # fade in from black when the game starts
        if t < 60:
            veil = pygame.Surface((W, H))
            veil.set_alpha(int(255 * (1 - t / 60)))
            scr.blit(veil, (0, 0))

    def _kelp(self, scr, x, h, ph, t, dark, light):
        px, py = x, FLOOR_Y + 8
        segs = h // 6
        for i in range(segs):
            sway = math.sin(t * 0.03 + ph + i * 0.35) * (i * 0.35)
            nx, ny = x + sway, FLOOR_Y + 8 - (i + 1) * 6
            pygame.draw.line(scr, dark, (px, py), (nx, ny), 3)
            pygame.draw.line(scr, light, (px - 1, py), (nx - 1, ny), 1)
            if i % 2 and i < segs - 1:
                side = 1 if (i // 2) % 2 else -1
                pygame.draw.ellipse(scr, dark, (nx + (1 if side > 0 else -7), ny - 1, 7, 3))
            px, py = nx, ny
        pygame.draw.circle(scr, light, (int(px), int(py)), 2)

    def _fish(self, scr, x, y, d, col, small):
        x, y = int(x), int(y)
        if small:
            scr.set_at((x, y), col)
            scr.set_at((x + d, y), col)
            scr.set_at((x - d, y - 1), col)
            scr.set_at((x - d, y + 1), col)
            return
        body = [(x - 3 * d, y), (x, y - 2), (x + 3 * d, y), (x, y + 2)]
        pygame.draw.polygon(scr, col, body)
        pygame.draw.polygon(scr, col, [(x - 3 * d, y), (x - 6 * d, y - 2), (x - 6 * d, y + 2)])
        scr.set_at((x + 2 * d, y - 1), (20, 20, 30))
        pygame.draw.line(scr, _lerp(col, (255, 255, 255), 0.5), (x - 1 * d, y - 1), (x + 1 * d, y - 1))
