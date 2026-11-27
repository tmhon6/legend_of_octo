"""3D buildings: the Octo Temple pyramid, every house and stall in the towns, the town gates,
Hermie's shop, the temple statues and all the trial portals.

Models are built in world pixels (x east, y south, z up) from boxes, cylinders, domes, cones,
roofs and rings, and drawn in a three-quarter view that matches the game's top-down art: height
lifts a point up the screen (and a little to the left, so east walls show). Each model is
rendered once at the hi-res scale, anti-aliased and cached; the game draws them in depth order
together with 3D Octo.
"""
import math

import pygame

import gfx
from settings import HI, TILE

KZ, KX = 0.78, 0.22                      # screen px up / left per px of height


def _norm(v):
    d = math.sqrt(sum(c * c for c in v)) or 1.0
    return tuple(c / d for c in v)


LIGHT = _norm((-0.55, 0.38, 0.76))       # towards the light: high, from the upper left
VIEW = _norm((KX, KZ, 1.0))              # towards the viewer


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def dk(c, k=0.7):
    return tuple(max(0, int(v * k)) for v in c)


def lt(c, k=0.35):
    return tuple(min(255, int(v + (255 - v) * k)) for v in c)


def project(x, y, z):
    return x - KX * z, y - KZ * z


class Model:
    def __init__(self):
        self.faces = []        # (depth, kind, data)

    # ---- raw faces -------------------------------------------------------
    def face(self, pts, col, normal, lines=(), lit=True, amb=0.45, bias=0.0):
        if _dot(normal, VIEW) <= 0.02:
            return
        if lit:
            lam = max(0.0, _dot(normal, LIGHT))
            k = amb + (1.12 - amb) * lam
            c = tuple(min(255, int(v * k)) for v in col)
        else:
            c = col
        n = len(pts)
        cen = (sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n, sum(p[2] for p in pts) / n)
        self.faces.append((_dot(cen, VIEW) + bias, 'poly', (pts, c, list(lines))))

    def line(self, a, b, col, w=1.0, bias=0.05):
        cen = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2)
        self.faces.append((_dot(cen, VIEW) + bias, 'line', (a, b, col, w)))

    def image(self, img, at, anchor, bias=0.0):
        """Blit a ready-made hi-res image (e.g. a voxel statue) with its anchor at 3D point at."""
        self.faces.append((_dot(at, VIEW) + bias, 'img', (img, at, anchor)))

    def text(self, s, at, col, size=1, bias=0.3, back=None):
        w = gfx.text_width(s) + 2
        img = pygame.Surface((w + 2, 10), pygame.SRCALPHA)
        if back:
            img.fill(back)
        gfx.text(img, s, 2, 2, col, shadow=False)
        k = size * HI
        img = pygame.transform.scale(img, ((w + 2) * k, 10 * k))
        self.faces.append((_dot(at, VIEW) + bias, 'img', (img, at, (img.get_width() / 2, img.get_height() / 2))))

    # ---- solids ----------------------------------------------------------
    def box(self, x0, y0, z0, x1, y1, z1, col, top=None, side=None, bricks=0, mortar=None, amb=0.45):
        top = top or lt(col, 0.12)
        side = side or col
        m = mortar or dk(col, 0.72)
        P = lambda x, y, z: (x, y, z)        # noqa: E731
        faces = [
            ([P(x0, y0, z1), P(x1, y0, z1), P(x1, y1, z1), P(x0, y1, z1)], top, (0, 0, 1)),
            ([P(x0, y1, z0), P(x1, y1, z0), P(x1, y1, z1), P(x0, y1, z1)], side, (0, 1, 0)),
            ([P(x1, y0, z0), P(x1, y1, z0), P(x1, y1, z1), P(x1, y0, z1)], side, (1, 0, 0)),
            ([P(x0, y0, z0), P(x0, y1, z0), P(x0, y1, z1), P(x0, y0, z1)], side, (-1, 0, 0)),
            ([P(x0, y0, z0), P(x1, y0, z0), P(x1, y0, z1), P(x0, y0, z1)], side, (0, -1, 0)),
        ]
        for pts, c, n in faces:
            lines = []
            if bricks and n[2] == 0:
                lines = self._bricks(pts, n, bricks, m)
            elif bricks and n[2] == 1:                       # paving slabs on top
                g = bricks * 4
                xx = x0 + g
                while xx < x1 - 0.5:
                    lines.append(((xx, y0, z1 + 0.1), (xx, y1, z1 + 0.1), dk(top, 0.85)))
                    xx += g
                yy = y0 + g
                while yy < y1 - 0.5:
                    lines.append(((x0, yy, z1 + 0.1), (x1, yy, z1 + 0.1), dk(top, 0.85)))
                    yy += g
            self.face(pts, c, n, lines, amb=amb)

    @staticmethod
    def _bricks(pts, n, course, col):
        """Mortar lines across a vertical wall face."""
        (ax, ay, _), (bx, by, _) = pts[0], pts[1]
        z0, z1 = pts[0][2], pts[2][2]
        off = 0.25 * (n[0] or n[1])
        out = []
        z = z0 + course
        row = 0
        length = math.hypot(bx - ax, by - ay)
        while z < z1 - 0.5:
            out.append(((ax + n[0] * off, ay + n[1] * off, z), (bx + n[0] * off, by + n[1] * off, z), col))
            z += course
        z = z0
        while z < z1 - 0.5:
            zt = min(z1, z + course)
            step = course * 2.2
            s = (step / 2 if row % 2 else 0) + step
            while s < length - 1:
                f = s / length
                x, y = ax + (bx - ax) * f + n[0] * off, ay + (by - ay) * f + n[1] * off
                out.append(((x, y, z), (x, y, zt), col))
                s += step
            z = zt
            row += 1
        return out

    def cyl(self, cx, cy, r, z0, z1, col, n=20, top=None, ry=None, bands=None, amb=0.45, lid=True):
        ry = ry or r
        for i in range(n):
            a0, a1 = i / n * math.tau, (i + 1) / n * math.tau
            p0 = (cx + r * math.cos(a0), cy + ry * math.sin(a0))
            p1 = (cx + r * math.cos(a1), cy + ry * math.sin(a1))
            am = (a0 + a1) / 2
            nn = _norm((math.cos(am) / r, math.sin(am) / ry, 0))
            if bands:
                zz = z0
                for j, (h, c) in enumerate(bands):
                    zt = min(z1, zz + h)
                    self.face([(p0[0], p0[1], zz), (p1[0], p1[1], zz), (p1[0], p1[1], zt), (p0[0], p0[1], zt)], c, nn,
                              amb=amb)
                    zz = zt
                    if zz >= z1:
                        break
            else:
                self.face([(p0[0], p0[1], z0), (p1[0], p1[1], z0), (p1[0], p1[1], z1), (p0[0], p0[1], z1)], col, nn,
                          amb=amb)
        if lid:
            pts = [(cx + r * math.cos(i / n * math.tau), cy + ry * math.sin(i / n * math.tau), z1) for i in range(n)]
            self.face(pts, top or lt(col, 0.1), (0, 0, 1), amb=amb)

    def cone(self, cx, cy, r, z0, z1, col, n=20, ry=None):
        ry = ry or r
        for i in range(n):
            a0, a1 = i / n * math.tau, (i + 1) / n * math.tau
            am = (a0 + a1) / 2
            nn = _norm((math.cos(am) * (z1 - z0) / r, math.sin(am) * (z1 - z0) / ry, 1.0))
            self.face([(cx + r * math.cos(a0), cy + ry * math.sin(a0), z0), (cx + r * math.cos(a1), cy + ry * math.sin(a1), z0),
                       (cx, cy, z1)], col, nn)

    def dome(self, cx, cy, rx, ry, rz, z0, col, n=22, rings=8, plates=None, ridges=None):
        """Upper half of an ellipsoid. plates: (colour, line colour) for a shell's patchwork."""
        for i in range(rings):
            t0, t1 = i / rings * math.pi / 2, (i + 1) / rings * math.pi / 2
            for j in range(n):
                a0, a1 = j / n * math.tau, (j + 1) / n * math.tau

                def P(t, a):
                    return (cx + rx * math.cos(t) * math.cos(a), cy + ry * math.cos(t) * math.sin(a), z0 + rz * math.sin(t))
                pts = [P(t0, a0), P(t0, a1), P(t1, a1), P(t1, a0)] if i < rings - 1 else [P(t0, a0), P(t0, a1), P(t1, a0)]
                tm, am = (t0 + t1) / 2, (a0 + a1) / 2
                nn = _norm((math.cos(tm) * math.cos(am) / rx, math.cos(tm) * math.sin(am) / ry, math.sin(tm) / rz))
                c = col
                lines = []
                if plates:
                    pc, lc = plates
                    if (i // 2 + j // 3) % 2:
                        c = pc
                    if i % 2 == 1 and i < rings - 1:
                        lines.append((pts[2], pts[3], lc))
                    if j % 3 == 0:
                        lines.append((pts[0], pts[3] if len(pts) == 4 else pts[2], lc))
                if ridges and j % ridges == 0 and i < rings - 1:
                    lines.append((pts[0], pts[3], lt(col, 0.45)))
                self.face(pts, c, nn, [(a, b, lc_) for a, b, lc_ in lines])

    def gable(self, x0, y0, x1, y1, z0, z1, col, end=None):
        """A pitched roof with its ridge running east-west."""
        ym = (y0 + y1) / 2
        hgt = z1 - z0
        self.face([(x0, y0, z0), (x1, y0, z0), (x1, ym, z1), (x0, ym, z1)], col, _norm((0, -hgt, (ym - y0))))
        self.face([(x0, y1, z0), (x1, y1, z0), (x1, ym, z1), (x0, ym, z1)], col, _norm((0, hgt, (y1 - ym))))
        e = end or dk(col, 0.9)
        self.face([(x0, y0, z0), (x0, y1, z0), (x0, ym, z1)], e, (-1, 0, 0))
        self.face([(x1, y0, z0), (x1, y1, z0), (x1, ym, z1)], e, (1, 0, 0))

    def gable_ns(self, x0, y0, x1, y1, z0, z1, col, end=None, lines=None):
        """A pitched roof with its ridge running north-south: the triangle end faces you."""
        xm = (x0 + x1) / 2
        hgt = z1 - z0
        self.face([(x0, y0, z0), (x0, y1, z0), (xm, y1, z1), (xm, y0, z1)], col, _norm((-hgt, 0, xm - x0)))
        self.face([(x1, y0, z0), (x1, y1, z0), (xm, y1, z1), (xm, y0, z1)], col, _norm((hgt, 0, x1 - xm)))
        self.face([(x0, y1, z0), (x1, y1, z0), (xm, y1, z1)], end or lt(col, 0.1), (0, 1, 0), lines=lines or [])
        self.face([(x0, y0, z0), (x1, y0, z0), (xm, y0, z1)], end or lt(col, 0.1), (0, -1, 0))

    def hip(self, x0, y0, x1, y1, z0, z1, col):
        """A four-sided pointed roof."""
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        ap = (cx, cy, z1)
        h = z1 - z0
        self.face([(x0, y1, z0), (x1, y1, z0), ap], col, _norm((0, h, cy - y0)))
        self.face([(x1, y0, z0), (x1, y1, z0), ap], col, _norm((h, 0, cx - x0)))
        self.face([(x0, y0, z0), (x0, y1, z0), ap], col, _norm((-h, 0, cx - x0)))
        self.face([(x0, y0, z0), (x1, y0, z0), ap], col, _norm((0, -h, cy - y0)))

    def disc_v(self, cx, y, cz, r, col, n=12, lit=False, rz=None, bias=0.4):
        """A round thing on a south-facing wall (a porthole, a sign)."""
        rz = rz or r
        pts = [(cx + r * math.cos(i / n * math.tau), y, cz + rz * math.sin(i / n * math.tau)) for i in range(n)]
        self.face(pts, col, (0, 1, 0), lit=lit, bias=bias)

    def quad_s(self, x0, x1, y, z0, z1, col, lit=True, bias=0.4, arch=False):
        """A flat rectangle on a south-facing wall (a door, a window); arch rounds its top."""
        if arch:
            r = (x1 - x0) / 2
            pts = [(x0, y, z0), (x1, y, z0), (x1, y, z1 - r)]
            for i in range(1, 8):
                a = i / 8 * math.pi
                pts.append(((x0 + x1) / 2 + r * math.cos(a), y, z1 - r + r * math.sin(a)))
            pts.append((x0, y, z1 - r))
        else:
            pts = [(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)]
        self.face(pts, col, (0, 1, 0), lit=lit, bias=bias)

    def ring(self, cx, cy, cz, R, r, col, n=24, m=6, glow=None):
        """A standing ring (a portal) in the x-z plane, facing south."""
        for i in range(n):
            a0, a1 = i / n * math.tau, (i + 1) / n * math.tau
            for j in range(m):
                b0, b1 = j / m * math.tau, (j + 1) / m * math.tau

                def P(a, b):
                    rr = R + r * math.cos(b)
                    return (cx + rr * math.cos(a), cy + r * math.sin(b), cz + rr * math.sin(a))
                am, bm = (a0 + a1) / 2, (b0 + b1) / 2
                nn = (math.cos(bm) * math.cos(am), math.sin(bm), math.cos(bm) * math.sin(am))
                c = col
                if glow and j in (1, 2) and i % 3 == 0:
                    c = glow
                self.face([P(a0, b0), P(a1, b0), P(a1, b1), P(a0, b1)], c, nn, lit=(c is col))

    # ---- drawing ---------------------------------------------------------
    def render(self, ss=2):
        """Rendered image and the pixel where the model's origin (0, 0, 0) lands."""
        S = HI * ss
        items = sorted(self.faces, key=lambda f: f[0])
        xs, ys = [], []
        for _, kind, data in items:
            if kind == 'poly':
                for p in data[0]:
                    sx, sy = project(*p)
                    xs.append(sx)
                    ys.append(sy)
            elif kind == 'line':
                for p in data[:2]:
                    sx, sy = project(*p)
                    xs.append(sx)
                    ys.append(sy)
            else:
                img, at, (ax, ay) = data
                sx, sy = project(*at)
                xs += [sx - ax / HI, sx + (img.get_width() - ax) / HI]
                ys += [sy - ay / HI, sy + (img.get_height() - ay) / HI]
        minx, miny = min(xs) - 2, min(ys) - 2
        w = int((max(xs) - minx + 2) * S) + 2
        h = int((max(ys) - miny + 2) * S) + 2
        surf = pygame.Surface((w, h), pygame.SRCALPHA)

        def to(p):
            sx, sy = project(*p)
            return (sx - minx) * S, (sy - miny) * S
        for _, kind, data in items:
            if kind == 'poly':
                pts, c, lines = data
                q = [to(p) for p in pts]
                pygame.draw.polygon(surf, c, q)
                pygame.draw.polygon(surf, c, q, 1)              # no seams between neighbours
                for a, b, lc in lines:
                    pygame.draw.line(surf, lc, to(a), to(b), max(1, ss))
            elif kind == 'line':
                a, b, c, lw = data
                pygame.draw.line(surf, c, to(a), to(b), max(1, int(lw * S)))
            else:
                img, at, (ax, ay) = data
                x, y = to(at)
                big = pygame.transform.scale(img, (img.get_width() * ss, img.get_height() * ss)) if ss > 1 else img
                surf.blit(big, (x - ax * ss, y - ay * ss))
        out = pygame.transform.smoothscale(surf, (w // ss, h // ss)) if ss > 1 else surf
        return out, (-minx * HI, -miny * HI)


# ======================================================================
# the models (each in world pixels, origin at the footprint's north-west corner)
# ======================================================================
def octo_house(body, trim, w=80, d=64):
    m = Model()
    cx, cy, rx, ry = w / 2, d / 2 + 4, w / 2 - 4, d / 2 - 8
    m.cyl(cx, cy, rx, 0, 12, dk(body, 0.82), n=26, ry=ry, lid=False)
    m.dome(cx, cy, rx, ry, 30, 12, body, ridges=4)
    yf = cy + ry
    m.quad_s(cx - 8, cx + 8, yf + 0.3, 0, 17, lt(trim, 0.1), arch=True)
    m.quad_s(cx - 6, cx + 6, yf + 0.5, 0, 15, (70, 36, 60), arch=True, bias=0.6)
    for side in (-1, 1):
        px = cx + side * rx * 0.6
        yy = cy + ry * math.sqrt(max(0.0, 1 - (0.6) ** 2))
        m.disc_v(px, yy + 0.4, 7, 4.5, (90, 70, 60))
        m.disc_v(px, yy + 0.6, 7, 3.2, (255, 226, 140))
    m.cyl(cx + rx * 0.45, cy - 4, 3.5, 28, 40, dk(body, 0.6), n=10)
    m.cyl(cx + rx * 0.45, cy - 4, 2.5, 40, 43, (200, 240, 255), n=10)
    return m


def octo_hall():
    m = Model()
    cream, gold = (238, 228, 238), (250, 196, 70)
    m.box(0, 84, 0, 192, 96, 3, (220, 210, 226))                  # steps
    m.box(6, 80, 0, 186, 90, 6, (232, 224, 238))
    m.box(14, 26, 0, 178, 80, 30, cream, bricks=6)
    m.quad_s(84, 108, 80.2, 0, 26, gold, arch=True)
    m.quad_s(87, 105, 80.4, 0, 23, (60, 40, 80), arch=True, bias=0.6)
    for i in range(8):
        x = 22 + i * 21
        if 80 < x < 112:
            continue
        m.cyl(x, 86, 4, 6, 34, (250, 248, 252), n=10, lid=False)
    m.box(8, 78, 34, 184, 92, 41, (246, 240, 248))
    m.text("CITY HALL", (96, 92.5, 37.5), (120, 80, 20), back=(255, 236, 160, 255))
    m.cyl(96, 52, 34, 30, 44, lt(cream, 0.2), n=26)
    m.dome(96, 52, 34, 30, 30, 44, gold, ridges=3)
    m.cyl(96, 52, 4, 74, 82, gold, n=10)
    for x in (24, 168):
        m.cyl(x, 40, 1.2, 30, 66, (120, 90, 60), n=6)
        m.face([(x, 40, 66), (x + 16, 40, 61), (x, 40, 56)], (240, 90, 140), (0, 1, 0))
    return m


def octo_museum():
    m = Model()
    stone = (226, 222, 210)
    m.box(0, 70, 0, 160, 80, 4, (210, 206, 196))
    m.box(10, 22, 0, 150, 66, 32, (205, 200, 190), bricks=6)
    m.quad_s(70, 90, 66.2, 0, 24, (60, 40, 50))
    for i in range(7):
        x = 16 + i * 21.3
        m.cyl(x, 72, 4, 4, 34, (252, 250, 244), n=10, lid=False)
    m.box(6, 64, 34, 154, 78, 42, stone)
    m.text("MUSEUM", (80, 78.5, 38), (255, 230, 150), back=(90, 70, 120, 255))
    m.gable_ns(4, 20, 156, 78, 42, 70, (196, 190, 178), end=(240, 236, 226),
               lines=[((14, 78.2, 43), (146, 78.2, 43), (200, 196, 186))])
    m.disc_v(80, 78.6, 52, 6, (120, 170, 230), lit=False)
    return m


def octo_tower():
    m = Model()
    cx, cy = 24, 58
    shells = [(240, 200, 170), (252, 224, 200)]
    z = 0
    for i, (r, h) in enumerate(((18, 14), (15, 12), (12, 10), (9, 9))):
        m.cyl(cx, cy, r, z, z + h, shells[i % 2], n=18)
        m.disc_v(cx, cy + r + 0.3, z + h / 2, 2.6, (255, 230, 150))
        z += h
    m.cone(cx, cy, 7, z, z + 18, (250, 150, 170))
    m.cyl(cx, cy, 2.5, z + 18, z + 22, (255, 200, 220), n=8)
    return m


def stall(label, a1, a2, goods, thatch=False):
    m = Model()
    wood = (150, 104, 60)
    m.box(4, 18, 0, 60, 30, 11, wood, top=(190, 140, 86))
    for x in (6, 56):
        m.box(x, 8, 0, x + 3, 11, 26, dk(wood, 0.8))
    for i in range(8):
        x0, x1 = i * 8, i * 8 + 8
        c = (a1 if i % 2 == 0 else a2) if not thatch else ((200, 170, 90) if i % 2 else (220, 190, 110))
        m.face([(x0, 4, 28), (x1, 4, 28), (x1, 20, 19), (x0, 20, 19)], c, _norm((0, 9, 16)))
        m.face([(x0, 20, 19), (x1, 20, 19), (x1, 20.5, 16), (x0, 20.5, 16)], dk(c, 0.85), (0, 1, 0))
    m.text(label, (32, 21, 23), (255, 245, 210), back=(70, 44, 30, 255))
    for i, c in enumerate(goods):
        m.dome(14 + i * 12, 24, 3.5, 3.5, 4, 11, c, n=10, rings=3)
    return m


def fountain():
    import voxel
    m = Model()
    cx, cy = 32, 34
    m.cyl(cx, cy, 28, 0, 8, (200, 194, 216), n=28, top=(226, 222, 240))
    m.cyl(cx, cy, 24, 7.9, 8.1, (70, 150, 220), n=28, top=(70, 150, 220), lid=True)
    m.cyl(cx, cy, 6, 8, 20, (180, 172, 198), n=12)
    img, anchor = voxel.render(voxel.octo_model('blue', 0), max(1, HI * 0.9), 0.3, 0.6, tint=(200, 200, 215))
    m.image(img, (cx, cy + 1, 20), anchor, bias=2)
    return m


def scoreboard():
    m = Model()
    wood = (110, 76, 46)
    for x in (8, 52):
        m.box(x, 38, 0, x + 4, 42, 22, wood)
    m.box(0, 34, 18, 64, 39, 48, dk(wood, 0.9))
    m.quad_s(3, 61, 39.3, 21, 45, (20, 26, 56), lit=False)
    m.text("TOP SCORES", (32, 39.6, 41), (255, 220, 120))
    for i, c in enumerate(((255, 220, 120), (210, 220, 240), (230, 160, 110))):
        m.line((8, 39.8, 36 - i * 5), (56, 39.8, 36 - i * 5), c, 0.5)
    return m


def gate_pillars(x0, x1, y0, y1, h, col, cap, between=None, arch_col=None, sign=None, sign_col=None,
                 lamps=None, door=None):
    """Two pillars (x0..x0+16 and x1-16..x1) with an arch between them."""
    m = Model()
    for px in (x0, x1 - 16):
        m.box(px + 1, y0, 0, px + 15, y1, h, col, bricks=5)
        m.box(px, y0 - 1, h, px + 16, y1 + 1, h + 3, cap)
        if lamps:
            m.dome(px + 8, (y0 + y1) / 2, 4, 4, 5, h + 3, lamps, n=10, rings=3)
    if door:
        m.quad_s(x0 + 16, x1 - 16, y0 + 1, 0, h - 2, door, lit=False, bias=-0.5)
    ac = arch_col or col
    n = 10
    span = (x1 - 16) - (x0 + 16)
    for i in range(n):
        a0, a1 = i / n * math.pi, (i + 1) / n * math.pi
        xa, xb = x0 + 16 + span / 2 - span / 2 * math.cos(a0), x0 + 16 + span / 2 - span / 2 * math.cos(a1)
        za, zb = h - 8 + 8 * math.sin(a0), h - 8 + 8 * math.sin(a1)
        m.face([(xa, y1, za), (xb, y1, zb), (xb, y1, h + 3), (xa, y1, h + 3)], ac, (0, 1, 0))
        m.face([(xa, y0, za), (xb, y0, zb), (xb, y1, zb), (xa, y1, za)], dk(ac, 0.7), (0, 0, -1), lit=False)
    m.face([(x0 + 16, y0 - 1, h + 3), (x1 - 16, y0 - 1, h + 3), (x1 - 16, y1 + 1, h + 3), (x0 + 16, y1 + 1, h + 3)], cap,
           (0, 0, 1))
    if sign:
        m.box(x0 + 4, y1 - 3, h + 3, x1 - 4, y1, h + 13, dk(cap, 0.55))
        m.text(sign, ((x0 + x1) / 2, y1 + 0.5, h + 8), sign_col or (255, 240, 200))
    return m


def turtle_house(shell, trim, w=80, d=64):
    m = Model()
    cx, cy, rx, ry = w / 2, d / 2 + 4, w / 2 - 4, d / 2 - 8
    m.cyl(cx, cy, rx, 0, 10, (226, 206, 160), n=26, ry=ry, lid=False)
    m.dome(cx, cy, rx, ry, 30, 10, shell, plates=(lt(shell, 0.12), trim))
    yf = cy + ry
    m.quad_s(cx - 8, cx + 8, yf + 0.3, 0, 16, (240, 220, 170), arch=True)
    m.quad_s(cx - 6, cx + 6, yf + 0.5, 0, 14, (80, 50, 30), arch=True, bias=0.6)
    px = cx + rx * 0.55
    yy = cy + ry * math.sqrt(max(0.0, 1 - 0.55 ** 2))
    m.disc_v(px, yy + 0.4, 6, 4, (110, 80, 50))
    m.disc_v(px, yy + 0.6, 6, 2.8, (255, 230, 150))
    return m


def turtle_elder():
    m = Model()
    shell = (120, 150, 80)
    cx, cy = 96, 52
    m.cyl(cx, cy, 86, 0, 14, (226, 206, 150), n=32, ry=40, lid=False)
    m.dome(cx, cy, 86, 40, 46, 14, shell, n=28, rings=9, plates=(lt(shell, 0.14), dk(shell, 0.55)))
    m.quad_s(cx - 14, cx + 14, cy + 40.3, 0, 26, (250, 220, 120), arch=True)
    m.quad_s(cx - 11, cx + 11, cy + 40.5, 0, 23, (70, 40, 20), arch=True, bias=0.6)
    m.text("ELDER", (cx, cy + 41, 31), (255, 236, 160), back=(90, 60, 30, 255))
    for x in (40, 152):
        m.cyl(x, 90, 1.5, 0, 26, (90, 60, 30), n=6)
        m.dome(x, 90, 4, 4, 5, 26, (255, 200, 90), n=10, rings=3)
    return m


def lighthouse():
    m = Model()
    cx, cy = 24, 80
    bands = [(10, (245, 245, 245) if i % 2 == 0 else (220, 60, 60)) for i in range(8)]
    m.cyl(cx, cy, 14, 0, 72, (245, 245, 245), n=18, bands=bands)
    m.cyl(cx, cy, 16, 72, 74, (60, 60, 70), n=18)
    m.cyl(cx, cy, 11, 74, 86, (255, 236, 150), n=16, amb=0.9)
    m.cone(cx, cy, 14, 86, 100, (200, 50, 50))
    m.quad_s(cx - 4, cx + 4, cy + 14.4, 0, 11, (70, 50, 40), arch=True)
    return m


def tiki_hut():
    m = Model()
    m.box(6, 14, 0, 58, 44, 16, (160, 112, 64), top=(140, 96, 52))
    for x in range(8, 58, 5):
        m.line((x, 44.3, 0), (x, 44.3, 16), (120, 80, 44), 0.4)
    m.quad_s(26, 38, 44.4, 0, 12, (60, 36, 20))
    m.hip(0, 8, 64, 48, 16, 40, (214, 182, 100))
    for i in range(1, 8):                                # thatch
        f = i / 8
        m.line((0 + 32 * f, 48 - 20 * f, 16 + 24 * f), (64 - 32 * f, 48 - 20 * f, 16 + 24 * f), (170, 140, 70), 0.4, bias=0.3)
    return m


def campfire():
    m = Model()
    for i in range(9):
        a = i / 9 * math.tau
        m.dome(16 + math.cos(a) * 11, 18 + math.sin(a) * 8, 3.5, 3, 3, 0, (130, 120, 110), n=8, rings=2)
    m.box(8, 16, 0, 24, 19, 3, (100, 60, 30))
    m.box(14, 10, 0, 17, 26, 3, (110, 66, 34))
    return m


def nest():
    m = Model()
    m.dome(8, 10, 8, 5.5, 4, 0, (220, 190, 130), n=14, rings=3)
    for x, y in ((5, 9), (9, 8), (11, 11)):
        m.dome(x, y, 2.6, 2.4, 4.5, 3, (250, 248, 236), n=10, rings=3)
    return m


def pyramid():
    """The Octo Temple: a stepped sandstone pyramid (8 x 8 tiles) with stairs up the south side."""
    m = Model()
    P, Q, T = (176, 150, 106), (200, 178, 132), (230, 212, 168)
    h1, h2, h3 = TIER
    m.box(0, 0, 0, 128, 112, h1, P, bricks=5)
    m.box(0, 112, 0, 48, 128, h1, P, bricks=5)
    m.box(80, 112, 0, 128, 128, h1, P, bricks=5)
    m.box(16, 16, h1, 112, 96, h2, Q, bricks=5)
    m.box(16, 96, h1, 48, 112, h2, Q, bricks=5)
    m.box(80, 96, h1, 112, 112, h2, Q, bricks=5)
    m.box(32, 32, h2, 96, 96, h3, T, top=(238, 224, 186), bricks=4)
    n = 8
    for i in range(n):                                   # the stairs
        y1 = 128 - i * 32 / n
        m.box(48, y1 - 32 / n, 0, 80, y1, h3 * (i + 1) / n, lt(T, 0.1), top=lt(T, 0.3))
    for x in (45, 80):                                   # stair walls
        for i in range(n):
            y1 = 128 - i * 32 / n
            m.box(x, y1 - 32 / n, 0, x + 3, y1, h3 * (i + 1) / n + 3, dk(P, 0.92))
    for x in (24, 32, 96, 104):                          # glowing runes on each tier
        m.quad_s(x - 2, x + 2, 112.4, h1 + 3, h1 + 8, (120, 240, 255), lit=False)
    for x in (8, 16, 112, 120):
        m.quad_s(x - 2, x + 2, 128.4, 3, 7, (120, 240, 255), lit=False)
    m.quad_s(40, 88, 96.4, h2 + 2, h3 - 2, (150, 120, 80))   # a carved band under the top
    for x in range(44, 88, 8):
        m.quad_s(x, x + 4, 96.6, h2 + 3, h3 - 3, (120, 240, 255), lit=False, bias=0.8)
    for x, y in ((38, 38), (90, 38), (38, 90), (90, 90)):    # braziers on the corners of the top
        m.cyl(x, y, 3.5, h3, h3 + 5, (110, 90, 70), n=10)
        m.dome(x, y, 3, 3, 4, h3 + 5, (255, 180, 60), n=8, rings=2)
    return m


def temple_statue():
    import voxel
    m = Model()
    m.box(1, 6, 0, 15, 16, 6, (150, 146, 160), bricks=3)
    img, anchor = voxel.render(voxel.octo_model('mad', 0), max(1, HI * 0.75), -0.25, 0.6, tint=(190, 190, 205))
    m.image(img, (8, 11, 6), anchor, bias=2)
    return m


def pearl_shop():
    """Hermie's shop: coral walls round the counter room, with a sign over the door."""
    m = Model()
    wall, cap = (226, 130, 150), (255, 220, 228)
    h = 13
    m.box(0, 0, 0, 144, 16, h, wall, top=cap, bricks=4)                 # north
    m.box(0, 16, 0, 16, 80, h, wall, top=cap, bricks=4)                 # west
    m.box(128, 16, 0, 144, 80, h, wall, top=cap, bricks=4)              # east
    m.box(0, 80, 0, 64, 96, h, wall, top=cap, bricks=4)                 # south, left of the door
    m.box(80, 80, 0, 144, 96, h, wall, top=cap, bricks=4)               # and right of it
    for x in (0, 128):
        m.box(x - 1, 79, h, x + 17, 97, h + 4, cap)
    m.box(60, 86, h, 84, 92, h + 10, (110, 76, 46))
    m.text("PEARL SHOP", (72, 92.5, h + 5), (255, 240, 200), back=(110, 60, 80, 255))
    for i in range(9):                                                   # an awning along the back wall
        c = (240, 120, 150) if i % 2 == 0 else (255, 240, 245)
        m.face([(16 + i * 12.4, 16, h + 2), (28.4 + i * 12.4, 16, h + 2), (28.4 + i * 12.4, 26, h - 4),
                (16 + i * 12.4, 26, h - 4)], c, _norm((0, 6, 10)))
    return m


def portal(col, done=False):
    m = Model()
    stone = (150, 146, 166) if not done else (120, 120, 130)
    m.box(0, 9, 0, 16, 16, 3, dk(stone, 0.9), top=stone)
    m.ring(8, 12.5, 16, 11, 2.8, stone, glow=None if done else col)
    return m


# which picture each town building uses (footprint in tiles comes from the map)
BUILDERS = {
    'o_house_a': lambda: octo_house((240, 150, 180), (255, 220, 230)),
    'o_house_b': lambda: octo_house((170, 140, 230), (230, 210, 255)),
    'o_house_c': lambda: octo_house((120, 200, 210), (220, 250, 255)),
    'o_house_d': lambda: octo_house((250, 190, 110), (255, 240, 200)),
    'o_house_e': lambda: octo_house((150, 210, 150), (230, 255, 220)),
    'o_house_f': lambda: octo_house((250, 140, 120), (255, 220, 200)),
    'o_house_g': lambda: octo_house((200, 170, 240), (245, 230, 255)),
    'o_hall': octo_hall, 'o_museum': octo_museum, 'o_tower': octo_tower,
    'o_stall_ink': lambda: stall("INK", (40, 60, 140), (250, 250, 255), [(30, 30, 60), (240, 90, 120), (90, 170, 255)]),
    'o_stall_hat': lambda: stall("HATS", (230, 90, 150), (255, 230, 240), [(240, 90, 90), (90, 90, 230), (250, 220, 80)]),
    'o_stall_bank': lambda: stall("BANK", (240, 190, 50), (255, 250, 220), [(255, 230, 120), (220, 230, 245), (170, 120, 255)]),
    'o_stall_food': lambda: stall("FOOD", (230, 110, 50), (255, 240, 210), [(255, 150, 120), (250, 210, 90), (120, 200, 90)]),
    'o_fountain': fountain, 'o_board': scoreboard,
    'o_gate': lambda: gate_pillars(0, 64, 2, 14, 26, (200, 110, 140), (255, 210, 225), lamps=(255, 230, 140),
                                   sign="OCTO CITY", sign_col=(255, 230, 150)),
    'ow_octo_gate': lambda: gate_pillars(0, 48, 18, 30, 30, (210, 120, 150), (255, 214, 228), lamps=(255, 230, 140),
                                         door=(30, 70, 140)),
    't_house_a': lambda: turtle_house((130, 170, 90), (70, 110, 50)),
    't_house_b': lambda: turtle_house((190, 140, 80), (120, 80, 40)),
    't_house_c': lambda: turtle_house((120, 150, 190), (60, 90, 130)),
    't_house_d': lambda: turtle_house((200, 170, 100), (140, 110, 50)),
    't_elder': turtle_elder, 't_lighthouse': lighthouse, 't_hut': tiki_hut, 't_fire': campfire, 't_nest': nest,
    't_stall_hat': lambda: stall("HATS", (230, 200, 90), (255, 250, 220), [(240, 200, 100), (240, 120, 150), (120, 190, 240)],
                                 thatch=True),
    't_stall_swap': lambda: stall("SWAP", (90, 170, 120), (230, 255, 230), [(250, 230, 140), (170, 120, 255), (90, 170, 255)],
                                  thatch=True),
    't_stall_clinic': lambda: stall("HEAL", (240, 240, 245), (230, 80, 80), [(255, 120, 140), (130, 220, 200), (250, 250, 250)],
                                    thatch=True),
    't_gate': lambda: gate_pillars(0, 64, 2, 14, 22, (150, 104, 60), (190, 140, 86), lamps=(255, 200, 90),
                                   sign="TURTLE TOWN", sign_col=(255, 240, 200)),
    'ow_turtle_gate': lambda: gate_pillars(0, 48, 2, 14, 24, (150, 104, 60), (190, 140, 86), lamps=(255, 200, 90),
                                           door=(60, 40, 24)),
}

_images = {}


def image(key, builder=None):
    """The rendered picture for a model (built and rendered the first time it's needed)."""
    out = _images.get(key)
    if out is None:
        mdl = (builder or BUILDERS[key])()
        out = _images[key] = mdl.render()
    return out


# ======================================================================
# what stands where
# ======================================================================
class Prop:
    __slots__ = ('key', 'x', 'y', 'w', 'h', 'base', 'kind', 'data', 'builder')

    def __init__(self, key, x, y, w, h, kind='static', data=None, builder=None):
        self.key, self.x, self.y, self.w, self.h = key, x, y, w, h     # world px of the footprint
        self.base = y + h                                                # sorting: the south edge
        self.kind, self.data, self.builder = kind, data, builder

    def rect(self):
        return pygame.Rect(self.x, self.y - 110, self.w, self.h + 110)


TIER = (10, 20, 30)          # pyramid tier heights: lower, middle, the top platform
PROPS = []
FLAT = set()           # tiles a 3D model stands on (the tile map draws plain ground there)
NOSHADE = set()        # ... and of those, the ones that don't get a dark footprint (models with their own shadow)
KINDS = {'t_fire': 'fire', 'o_fountain': 'fountain', 'o_home': 'home', 'o_mail': 'mail', 'h_wall_back': 'wall',
         'h_bed': 'bed', 'h_shelf': 'shelf', 'h_tank': 'tank', 'h_table': 'tea', 'h_basket': 'basket',
         'h_hats': 'hats', 'h_lamp': 'lamp', 'h_rug': 'floor'}
PYRAMID = (43, 46, 50, 53)


def build_props(world):
    PROPS.clear()
    FLAT.clear()
    NOSHADE.clear()
    groups = {}
    for (tx, ty), (key, i, j) in world.CITY_ART.items():
        if key == 't_nest':
            PROPS.append(Prop(key, tx * TILE, ty * TILE, TILE, TILE))
            FLAT.add((tx, ty))
            continue
        groups.setdefault(key, []).append((tx, ty))
    for key, tiles in groups.items():
        xs, ys = [t[0] for t in tiles], [t[1] for t in tiles]
        x0, y0 = min(xs), min(ys)
        prop = Prop(key, x0 * TILE, y0 * TILE, (max(xs) - x0 + 1) * TILE, (max(ys) - y0 + 1) * TILE,
                    kind=KINDS.get(key, 'static'))
        if prop.kind == 'floor':                    # a rug: under everything, and you walk on it
            prop.base = -10 ** 6
            NOSHADE.update(tiles)
            PROPS.append(prop)
            continue
        PROPS.append(prop)
        FLAT.update(tiles)
        if key.startswith('h_') or key == 'o_mail':
            NOSHADE.update(tiles)
    x0, y0, x1, y1 = PYRAMID
    PROPS.append(Prop('pyramid', x0 * TILE, y0 * TILE, (x1 - x0 + 1) * TILE, (y1 - y0 + 1) * TILE, builder=pyramid))
    FLAT.update((x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1))
    for sx, sy in ((45, 54), (48, 54)):                   # the stone Octos in front of the temple
        if world.LEVEL[sy][sx] == 'S':
            PROPS.append(Prop('statue', sx * TILE, sy * TILE, TILE, TILE, builder=temple_statue))
            FLAT.add((sx, sy))
    PROPS.append(Prop('pearl_shop', 26 * TILE, 46 * TILE, 9 * TILE, 6 * TILE, builder=pearl_shop))
    FLAT.update((x, y) for x in range(26, 35) for y in range(46, 52) if world.LEVEL[y][x] == 'W')
    for name, t in world.TRIALS.items():
        px, py = t['portal']
        PROPS.append(Prop('portal', px * TILE, py * TILE, TILE, TILE, kind='portal', data=name))


def height_at(wx, wy):
    """How high the ground is at world pixel (wx, wy): the pyramid's tiers, top and stairs."""
    x0, y0, x1, y1 = PYRAMID
    lx, ly = wx - x0 * TILE, wy - y0 * TILE
    if not (0 <= lx < 128 and 0 <= ly < 128):
        return 0.0
    h1, h2, h3 = TIER
    if 48 <= lx < 80 and ly >= 96:                       # the stairs
        return max(0.0, min(float(h3), (128 - ly) / 32 * h3))
    if 32 <= lx < 96 and 32 <= ly < 96:
        return float(h3)
    if 16 <= lx < 112 and 16 <= ly < 112:
        return float(h2)
    return float(h1)


# ---- trial portals: a stone ring with a swirling vortex ------------------------------------------
_swirls = {}


import home3d as _home3d  # noqa: E402  (Octo's house and everything in it)
BUILDERS.update(_home3d.BUILDERS)


def swirl(col, r):
    key = (col, r)
    s = _swirls.get(key)
    if s is None:
        d = r * 2
        s = pygame.Surface((d, d), pygame.SRCALPHA)
        for i in range(r, 0, -1):
            k = i / r
            pygame.draw.circle(s, (int(col[0] * (1 - k) + 255 * k * 0.15), int(col[1] * (1 - k * 0.6)),
                                   int(col[2] * (1 - k * 0.3) + 40 * k), int(255 * (1 - k ** 3))), (r, r), i)
        for arm in range(4):                              # spiral arms
            pts = []
            for j in range(30):
                t = j / 30
                a = arm / 4 * math.tau + t * 4.5
                pts.append((r + math.cos(a) * r * t, r + math.sin(a) * r * t))
            pygame.draw.lines(s, (255, 255, 255, 170), False, pts, max(1, r // 8))
        pygame.draw.circle(s, (255, 255, 255, 230), (r, r), max(2, r // 5))
        _swirls[key] = s
    return s
