"""Cinematics drawn in code: the 3D opening and the mini-boss "versus" entrance.

A tiny software 3D renderer (voxels + painter's sort, flat shading) builds Octo and the
logo out of little cubes, and a mode-7 style ocean sweeps under the camera.
Everything is plain pygame so it runs in the browser too.
"""
import math
import random

import pygame

import gfx
from settings import AUTHOR, SCREEN_H, SCREEN_W

W, H = SCREEN_W, SCREEN_H
F = 210                                  # focal length (pixels)
LIGHT = (-0.35, -0.65, -0.68)            # light comes from above-left-front


def _norm(v):
    d = math.sqrt(sum(c * c for c in v)) or 1
    return tuple(c / d for c in v)


LIGHT = _norm(LIGHT)
_FACES = {          # normal -> corner signs (sx, sy, sz) in loop order
    (1, 0, 0): ((1, -1, -1), (1, 1, -1), (1, 1, 1), (1, -1, 1)),
    (-1, 0, 0): ((-1, -1, -1), (-1, -1, 1), (-1, 1, 1), (-1, 1, -1)),
    (0, 1, 0): ((-1, 1, -1), (1, 1, -1), (1, 1, 1), (-1, 1, 1)),
    (0, -1, 0): ((-1, -1, -1), (-1, -1, 1), (1, -1, 1), (1, -1, -1)),
    (0, 0, 1): ((-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)),
    (0, 0, -1): ((-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1)),
}


def _rot(yaw, pitch, roll=0.0):
    """Rotation matrix rows for yaw (around y), then pitch (around x), then roll (around z)."""
    cy, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cr, sr = math.cos(roll), math.sin(roll)
    # R = Rz * Rx * Ry
    ry = ((cy, 0, sy), (0, 1, 0), (-sy, 0, cy))
    rx = ((1, 0, 0), (0, cp, -sp), (0, sp, cp))
    rz = ((cr, -sr, 0), (sr, cr, 0), (0, 0, 1))

    def mul(a, b):
        return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))
    return mul(rz, mul(rx, ry))


def _apply(m, v):
    return (m[0][0] * v[0] + m[0][1] * v[1] + m[0][2] * v[2],
            m[1][0] * v[0] + m[1][1] * v[1] + m[1][2] * v[2],
            m[2][0] * v[0] + m[2][1] * v[1] + m[2][2] * v[2])


class Voxels:
    """A model made of cubes. Each voxel: home position (model units), colour, exposed faces."""

    def __init__(self, cells, depth=1.0):
        """cells: {(x, y, z): colour}. The model is centred on its bounding box."""
        xs = [c[0] for c in cells]
        ys = [c[1] for c in cells]
        zs = [c[2] for c in cells]
        cx, cy, cz = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (min(zs) + max(zs)) / 2
        self.depth = depth
        self.vox = []
        for (x, y, z), col in cells.items():
            faces = [n for n in _FACES if (x + n[0], y + n[1], z + n[2]) not in cells]
            self.vox.append({'home': (x - cx, y - cy, (z - cz) * depth), 'col': col, 'faces': faces})
        self.w = max(xs) - min(xs) + 1
        self.h = max(ys) - min(ys) + 1


def voxels_from_surface(img, depth=2.5):
    cells = {}
    w, h = img.get_size()
    for y in range(h):
        for x in range(w):
            c = img.get_at((x, y))
            if c.a > 128:
                cells[(x, y, 0)] = (c.r, c.g, c.b)
    return Voxels(cells, depth)


def voxels_from_text(s, cols, depth=1.6):
    """Block letters from the 5x7 bitmap font. cols(x, y) -> colour."""
    cells = {}
    for i, ch in enumerate(s.upper()):
        rows = gfx.FONT.get(ch)
        if not rows:
            continue
        for y, row in enumerate(rows.split('|')):
            for x, c in enumerate(row):
                if c == '#':
                    cells[(i * 6 + x, y, 0)] = cols(i * 6 + x, y)
    return Voxels(cells, depth)


def render(surf, items, ambient=0.42, glow=None):
    """items: list of (model, matrix, origin, scale, per-voxel offset fn or None, solid_faces).
    Collects every visible face, sorts far-to-near and fills them."""
    polys = []
    for model, m, (ox, oy, oz), scale, offset, tint in items:
        axes = [_apply(m, (scale / 2, 0, 0)), _apply(m, (0, scale / 2, 0)),
                _apply(m, (0, 0, scale * model.depth / 2))]
        # light each face direction once per model
        shade = {}
        nrot = {}
        for n in _FACES:
            rn = _apply(m, n)
            nrot[n] = rn
            lam = max(0.0, rn[0] * LIGHT[0] + rn[1] * LIGHT[1] + rn[2] * LIGHT[2])
            shade[n] = ambient + (1 - ambient) * lam
        for i, v in enumerate(model.vox):
            hx, hy, hz = v['home']
            spin = None
            if offset:
                dx, dy, dz, spin = offset(i, v)
                hx, hy, hz = hx + dx, hy + dy, hz + dz
            c = _apply(m, (hx * scale, hy * scale, hz * scale))
            cx, cy, cz = c[0] + ox, c[1] + oy, c[2] + oz
            if cz < 2:
                continue
            ax = axes
            faces = v['faces']
            nr = nrot
            sh = shade
            if spin is not None:                  # a voxel tumbling on its own on the way in
                m2 = _rot(spin, spin * 0.7)
                ax = [_apply(m2, a) for a in axes]
                faces = _FACES.keys()
                nr = {n: _apply(m2, nrot[n]) for n in _FACES}
                sh = {}
                for n in _FACES:
                    rn = nr[n]
                    lam = max(0.0, rn[0] * LIGHT[0] + rn[1] * LIGHT[1] + rn[2] * LIGHT[2])
                    sh[n] = ambient + (1 - ambient) * lam
            for n in faces:
                rn = nr[n]
                # face centre
                fx = cx + ax[0][0] * n[0] + ax[1][0] * n[1] + ax[2][0] * n[2]
                fy = cy + ax[0][1] * n[0] + ax[1][1] * n[1] + ax[2][1] * n[2]
                fz = cz + ax[0][2] * n[0] + ax[1][2] * n[1] + ax[2][2] * n[2]
                if rn[0] * fx + rn[1] * fy + rn[2] * fz >= 0:
                    continue                      # facing away from the camera
                pts = []
                for sx, sy, sz in _FACES[n]:
                    px = cx + ax[0][0] * sx + ax[1][0] * sy + ax[2][0] * sz
                    py = cy + ax[0][1] * sx + ax[1][1] * sy + ax[2][1] * sz
                    pz = cz + ax[0][2] * sx + ax[1][2] * sy + ax[2][2] * sz
                    if pz < 1:
                        pz = 1
                    pts.append((W / 2 + px * F / pz, H / 2 + py * F / pz))
                k = sh[n]
                col = v['col']
                if tint:
                    col = tint(i, v, col)
                polys.append((fz, (min(255, int(col[0] * k)), min(255, int(col[1] * k)),
                                   min(255, int(col[2] * k))), pts))
    polys.sort(key=lambda p: -p[0])
    for _, col, pts in polys:
        pygame.draw.polygon(surf, col, pts)
    return len(polys)


def _gradient(stops, w=W, h=H):
    s = pygame.Surface((w, h))
    for y in range(h):
        f = y / (h - 1)
        for (f0, c0), (f1, c1) in zip(stops, stops[1:]):
            if f0 <= f <= f1:
                k = (f - f0) / ((f1 - f0) or 1)
                c = tuple(int(c0[i] + (c1[i] - c0[i]) * k) for i in range(3))
                break
        pygame.draw.line(s, c, (0, y), (w, y))
    return s


# ======================================================================
# the opening
# ======================================================================
class Intro3D:
    """About ten seconds: skim the ocean at dawn, dive in, Octo swims out of the deep,
    and the logo assembles itself out of tumbling cubes. Any key skips it."""
    LENGTH = 640
    DIVE = 170          # camera plunges into the sea
    SPLASH = 200        # under the surface
    LOGO = 330          # cubes start flying in
    FLASH = 560

    def __init__(self):
        rnd = random.Random(11)
        self.rnd = rnd
        self.sky = _gradient([(0, (40, 40, 110)), (0.35, (200, 90, 120)), (0.55, (255, 170, 90)),
                              (1, (255, 220, 150))], h=H)
        self.deep = _gradient([(0, (30, 110, 170)), (0.4, (10, 50, 110)), (1, (2, 10, 34))])
        self.tex = self._ocean_tex(rnd)
        self.clouds = [(rnd.uniform(0, W * 2), rnd.uniform(10, 60), rnd.uniform(20, 50), rnd.uniform(0.1, 0.35))
                       for _ in range(9)]
        self.bubbles = [[rnd.uniform(-60, 60), rnd.uniform(-50, 50), rnd.uniform(5, 200), rnd.random()]
                        for _ in range(90)]
        self.rays = []
        for _ in range(6):
            wdt = rnd.randint(14, 34)
            r = pygame.Surface((wdt, H))
            for x in range(wdt):
                a = math.sin(x / wdt * math.pi) * 0.13
                pygame.draw.line(r, (int(120 * a), int(200 * a), int(255 * a)), (x, 0), (x, H))
            self.rays.append((r, rnd.uniform(0, W), rnd.uniform(0.15, 0.35)))
        # models
        self.octo = voxels_from_surface(gfx.OCTO['blue']['down'][0], depth=3.0)
        gold = lambda x, y: (255, 200 - y * 10, 60 + y * 6)          # noqa: E731
        ice = lambda x, y: (170 + y * 10, 225, 255)                  # noqa: E731
        self.word_top = voxels_from_text("LEGEND OF", ice, depth=1.4)
        self.word_big = voxels_from_text("OCTO", gold, depth=2.0)
        # where each logo cube starts its flight (a spiral far behind and around the camera)
        self.starts = {}
        for name, model in (('top', self.word_top), ('big', self.word_big)):
            out = []
            for i, v in enumerate(model.vox):
                a = rnd.uniform(0, math.tau)
                r = rnd.uniform(18, 40)
                out.append((math.cos(a) * r, math.sin(a) * r, rnd.uniform(-30, 60), rnd.uniform(0, 1),
                            rnd.uniform(4, 10) * rnd.choice((-1, 1))))
            self.starts[name] = out
        self.fade = pygame.Surface((W, H))
        self.done = False
        self.t = 0
        self.sparkles = []

    def _ocean_tex(self, rnd):
        s = pygame.Surface((256, 256))
        for y in range(256):
            for x in range(0, 256, 2):
                w = math.sin(x / 256 * math.tau * 3 + math.sin(y / 256 * math.tau * 2) * 2) + \
                    math.sin(y / 256 * math.tau * 5 + x / 256 * math.tau)
                k = (w + 2) / 4
                c = (int(20 + 40 * k), int(80 + 70 * k), int(140 + 70 * k))
                s.fill(c, (x, y, 2, 1))
        for _ in range(500):                         # glints of the dawn sun
            x, y = rnd.randrange(256), rnd.randrange(256)
            s.fill((255, 230, 180), (x, y, rnd.randint(1, 3), 1))
        big = pygame.Surface((256 * 3, 256))
        for i in range(3):
            big.blit(s, (i * 256, 0))
        return big

    # ---- helpers ------------------------------------------------------------
    def _ocean(self, scr, t, horizon, cam_h):
        """A mode-7 sea: each screen row below the horizon is a stretched strip of the texture."""
        travel = t * 3.2
        for y in range(max(0, int(horizon) + 1), H):
            dy = y - horizon
            z = cam_h * F / dy
            span = z * W / F
            v = int(travel + z) % 256
            span = min(span, 510.0)
            u = (128 + math.sin(t * 0.01) * 40 - span / 2) % 256
            sub = self.tex.subsurface((int(u), v, max(1, int(span)), 1))
            scr.blit(pygame.transform.scale(sub, (W, 1)), (0, y))
            fog = min(1.0, z / 700)
            if fog > 0.05:
                band = pygame.Surface((W, 1))
                band.fill((255, 190, 140))
                band.set_alpha(int(220 * fog))
                scr.blit(band, (0, y))

    def _sky(self, scr, t, horizon):
        scr.blit(self.sky, (0, int(horizon - H * 0.72)))
        sx, sy = W // 2 + 30, int(horizon - 18)
        for r, a in ((34, 30), (24, 60), (16, 120)):
            g = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(g, (255, 230, 170, a), (r, r), r)
            scr.blit(g, (sx - r, sy - r))
        pygame.draw.circle(scr, (255, 250, 220), (sx, sy), 11)
        for x, y, w, sp in self.clouds:
            cx = (x - t * sp) % (W + 120) - 60
            cy = horizon - 120 + y
            for k in range(3):
                pygame.draw.ellipse(scr, (255, 200, 200), (cx + k * w * 0.3, cy - k % 2 * 4, w, w * 0.35))
            pygame.draw.ellipse(scr, (190, 120, 150), (cx + 2, cy + w * 0.2, w * 1.4, w * 0.18))

    def _underwater(self, scr, t, speed):
        scr.blit(self.deep, (0, 0))
        for r, x, sp in self.rays:
            scr.blit(r, (x + math.sin(t * 0.01 + x) * 20 - 40, 0), special_flags=pygame.BLEND_RGB_ADD)
        for b in self.bubbles:
            b[2] -= speed
            if b[2] < 3:
                b[0], b[1], b[2] = self.rnd.uniform(-60, 60), self.rnd.uniform(-50, 50), 200
            x, y, z = b[0], b[1] - t * 0.02, b[2]
            px, py = W / 2 + x * F / z, H / 2 + y * F / z
            if -10 < px < W + 10 and -10 < py < H + 10:
                r = max(1, int(1.8 * F / z / 6))
                c = int(120 + 135 * min(1.0, 40 / z))
                if speed > 1.5 and z < 80:       # rushing past: streaks
                    pz = z + speed * 3
                    qx, qy = W / 2 + x * F / pz, H / 2 + y * F / pz
                    pygame.draw.line(scr, (c // 2, c, 255), (qx, qy), (px, py), max(1, r // 2))
                pygame.draw.circle(scr, (c // 2, c, 255), (int(px), int(py)), r, 1)

    def _veil(self, scr, col, a):
        if a <= 0:
            return
        self.fade.fill(col)
        self.fade.set_alpha(int(max(0, min(255, a))))
        scr.blit(self.fade, (0, 0))

    @staticmethod
    def _ease(x):
        x = max(0.0, min(1.0, x))
        return 1 - (1 - x) ** 3

    # ---- per frame ----------------------------------------------------------
    def draw(self, scr, t):
        self.t = t
        if t >= self.LENGTH:
            self.done = True
        if t < self.SPLASH:
            # skimming the ocean, then pitching down and diving in
            dive = max(0.0, (t - self.DIVE + 40) / 70)
            horizon = 120 - dive * dive * 260
            cam_h = 36 - min(1.0, dive) * 28
            self._sky(scr, t, horizon)
            self._ocean(scr, t, horizon, cam_h)
            if t < 140:
                a = min(1.0, t / 30) * min(1.0, (140 - t) / 25)
                img = pygame.Surface((W, 12), pygame.SRCALPHA)
                gfx.text(img, AUTHOR.upper() + " PRESENTS", W // 2, 2, (255, 255, 255), center=True)
                img.set_alpha(int(255 * a))
                scr.blit(img, (0, 60))
            if t < 24:
                self._veil(scr, (0, 0, 0), 255 * (1 - t / 24))
            if t > self.SPLASH - 18:
                self._veil(scr, (255, 255, 255), (t - (self.SPLASH - 18)) * 16)
            return
        u = t - self.SPLASH
        speed = 4.0 if u < 60 else max(0.6, 4.0 - (u - 60) * 0.05)
        self._underwater(scr, t, speed)
        items = []
        # Octo swims up out of the deep, spinning, then hangs below the logo
        k = self._ease(u / 120)
        settle = self._ease((t - self.LOGO) / 90)
        oz = 260 - 200 * k
        oy = math.sin(t * 0.06) * 2 + 8 * settle + 10 * (1 - k)
        yaw = (1 - k) * math.tau * 2 + math.sin(t * 0.03) * 0.5
        scale = 1.0 - 0.35 * settle
        items.append((self.octo, _rot(yaw, 0.15 * math.sin(t * 0.05), math.sin(t * 0.04) * 0.08),
                      (0, oy + 8 * settle, oz + 10 * settle), scale * 2.2, None, None))
        # the logo cubes fly in and lock into place
        if t > self.LOGO:
            lt = t - self.LOGO
            sweep = (lt - 120) * 2.2                      # a shine that runs along the letters
            group = _rot(math.sin(lt * 0.025) * 0.35 * (1 - self._ease((lt - 150) / 70)),
                         -0.12 + 0.06 * math.sin(lt * 0.04))

            def mk(name, delay):
                starts = self.starts[name]

                def off(i, v):
                    sx, sy, sz, d, spin = starts[i]
                    p = self._ease((lt - delay - d * 60) / 50)
                    if p >= 1:
                        return 0, 0, 0, None
                    q = 1 - p
                    return sx * q, sy * q, sz * q, spin * q
                return off

            def shine(i, v, col):
                x = v['home'][0] * 3 + v['home'][1] * 2
                d = abs(x - sweep)
                if d < 8:
                    f = 1 + (8 - d) / 8 * 0.9
                    return (min(255, col[0] * f), min(255, col[1] * f), min(255, col[2] * f))
                return col
            items.append((self.word_top, group, (0, -51, 120), 2.2, mk('top', 0), shine))
            items.append((self.word_big, group, (0, -10, 90), 3.6, mk('big', 25), shine))
        render(scr, items)
        # sparkles once the logo locks
        if self.LOGO + 150 < t < self.FLASH:
            if self.rnd.random() < 0.5:
                self.sparkles.append([self.rnd.uniform(40, W - 40), self.rnd.uniform(30, 120), 16])
        for s in self.sparkles:
            s[2] -= 1
            r = s[2] // 4
            pygame.draw.line(scr, (255, 255, 220), (s[0] - r, s[1]), (s[0] + r, s[1]))
            pygame.draw.line(scr, (255, 255, 220), (s[0], s[1] - r), (s[0], s[1] + r))
        self.sparkles = [s for s in self.sparkles if s[2] > 0]
        if u < 30:
            self._veil(scr, (255, 255, 255), 255 * (1 - u / 30))
        if t > self.LOGO + 190:
            a = min(1.0, (t - self.LOGO - 190) / 20)
            img = pygame.Surface((W, 12), pygame.SRCALPHA)
            gfx.text(img, "A REVERSIBLE UNDERSEA ADVENTURE", W // 2, 2, (200, 230, 255), center=True)
            img.set_alpha(int(255 * a))
            scr.blit(img, (0, H - 34))
        if t > self.FLASH:
            f = t - self.FLASH
            self._veil(scr, (255, 255, 255), 255 - abs(f - 14) * 18 if f < 28 else 0)
            if f >= 28:
                self._veil(scr, (0, 0, 0), (f - 28) * 6)
        if t > 40 and (t // 30) % 2:
            gfx.text(scr, "PRESS ANY KEY", W - 4 - gfx.text_width("PRESS ANY KEY"), H - 10, (120, 150, 200))


# ======================================================================
# the versus entrance for 1-on-1 boss fights
# ======================================================================
class VersusCut:
    """The world shatters, Octo and the guardian face off across a slash of light, VS slams in,
    then the panels split apart to reveal the arena."""
    LENGTH = 200
    SHATTER = 34
    VS_AT = 62
    OPEN = 160          # panels pull apart

    def __init__(self, snapshot, octo_img, boss_img, name, subtitle, accent=(255, 80, 90), hat=None):
        self.snap = snapshot
        self.octo = octo_img
        self.boss = boss_img
        self.name = name
        self.subtitle = subtitle
        self.accent = accent
        self.hat = hat
        rnd = random.Random()
        self.rnd = rnd
        cw, ch = W // 8, H // 8
        self.shards = []
        for gy in range(8):
            for gx in range(8):
                r = pygame.Rect(gx * cw, gy * ch, cw, ch)
                cx, cy = r.centerx - W / 2, r.centery - H / 2
                d = math.hypot(cx, cy) or 1
                self.shards.append({'img': snapshot.subsurface(r).copy(), 'x': r.centerx, 'y': r.centery,
                                    'vx': cx / d * rnd.uniform(1.5, 4), 'vy': cy / d * rnd.uniform(1.5, 4) - 1,
                                    'spin': rnd.uniform(-9, 9), 'delay': int(d / 14)})
        self.cracks = []
        for _ in range(9):                          # lightning cracks from the centre
            a = rnd.uniform(0, math.tau)
            pts = [(W / 2, H / 2)]
            r = 0
            while r < 200:
                r += rnd.uniform(14, 26)
                a += rnd.uniform(-0.4, 0.4)
                pts.append((W / 2 + math.cos(a) * r, H / 2 + math.sin(a) * r))
            self.cracks.append(pts)
        self.lines = [[rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(6, 14), rnd.randint(10, 40)]
                      for _ in range(40)]
        self.big_octo = pygame.transform.scale(octo_img, (64, 64))
        bw, bh = boss_img.get_size()
        k = 84 / max(bw, bh)
        self.big_boss = pygame.transform.scale(boss_img, (int(bw * k), int(bh * k)))
        self.boss_shadow = self._silhouette(self.big_boss, (0, 0, 0))
        self.boss_lit = self._silhouette(self.big_boss, (255, 255, 255))
        self.done = False

    @staticmethod
    def _silhouette(img, col):
        s = img.copy()
        s.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
        s.fill(col + (0,), special_flags=pygame.BLEND_RGBA_ADD)
        return s

    @staticmethod
    def _ease(x):
        x = max(0.0, min(1.0, x))
        return 1 - (1 - x) ** 3

    def _big(self, s, scale, col, outline=(0, 0, 0)):
        w = gfx.text_width(s) + 2
        tmp = pygame.Surface((w + 2, 11), pygame.SRCALPHA)
        for ox, oy in ((0, 1), (2, 1), (1, 0), (1, 2), (2, 2)):
            gfx.text(tmp, s, ox, oy, outline, shadow=False)
        gfx.text(tmp, s, 1, 1, col, shadow=False)
        return pygame.transform.scale(tmp, (int((w + 2) * scale), int(11 * scale)))

    def shaking(self, t):
        return 10 if t in (self.VS_AT, self.VS_AT + 1) else 0

    def draw(self, scr, t, under=None):
        """under: the arena, already drawn on scr (shown once the panels open)."""
        if t >= self.LENGTH:
            self.done = True
            return
        acc = self.accent
        opening = t >= self.OPEN
        gap = self._ease((t - self.OPEN) / 32) * (W + 60) if opening else 0
        if not opening:
            scr.fill((6, 4, 16))
            # a vortex of speed lines behind everything
            for ln in self.lines:
                a = math.atan2(ln[1] - H / 2, ln[0] - W / 2) + t * 0.01
                r0 = (ln[3] + t * ln[2]) % 220
                x0, y0 = W / 2 + math.cos(a) * r0, H / 2 + math.sin(a) * r0
                x1, y1 = W / 2 + math.cos(a) * (r0 + 16), H / 2 + math.sin(a) * (r0 + 16)
                pygame.draw.line(scr, (acc[0] // 3, acc[1] // 3, acc[2] // 3), (x0, y0), (x1, y1))
        # ---- 1: the world shatters
        if t < self.SHATTER + 30:
            for s in self.shards:
                u = max(0, t - 6 - s['delay'])
                if t < 6:
                    scr.blit(s['img'], s['img'].get_rect(center=(s['x'], s['y'])))
                    continue
                z = 1 + u * 0.05                     # shards fly toward the camera as they scatter
                x = s['x'] + s['vx'] * u * z
                y = s['y'] + s['vy'] * u * z + 0.08 * u * u
                img = pygame.transform.rotozoom(s['img'], s['spin'] * u, z)
                if u > 10:
                    img.set_alpha(max(0, 255 - (u - 10) * 10))
                scr.blit(img, img.get_rect(center=(x, y)))
            if t < 10:
                for pts in self.cracks:
                    n = min(len(pts), 2 + t)
                    pygame.draw.lines(scr, (255, 255, 255), False, pts[:n], 2)
                    pygame.draw.lines(scr, acc, False, pts[:n], 1)
            if t < 4:
                v = pygame.Surface((W, H))
                v.fill((255, 255, 255))
                v.set_alpha(200 - t * 50)
                scr.blit(v, (0, 0))
        if t < self.SHATTER - 6:
            return
        # ---- 2: the two panels sweep in along a diagonal slash
        p_in = self._ease((t - self.SHATTER + 6) / 22)
        slope = 40
        mid = H / 2
        top = pygame.Surface((W, H), pygame.SRCALPHA)
        bot = pygame.Surface((W, H), pygame.SRCALPHA)
        # top-left: Octo's side (deep blue); bottom-right: the guardian's side
        pygame.draw.polygon(top, (20, 50, 130), [(0, 0), (W, 0), (W, mid - slope), (0, mid + slope)])
        pygame.draw.polygon(bot, (acc[0] // 2, acc[1] // 5, acc[2] // 4),
                            [(0, mid + slope), (W, mid - slope), (W, H), (0, H)])
        for i, ln in enumerate(self.lines):              # streaks rushing across each panel
            x = (ln[0] + t * ln[2] * (1 if i % 2 else -1)) % (W + 60) - 30
            y = ln[1]
            on_top = y < mid + slope - (x / W) * slope * 2
            tgt = top if on_top else bot
            col = (80, 130, 230, 120) if on_top else (min(255, acc[0]), acc[1] // 2 + 40, acc[2] // 2 + 40, 120)
            pygame.draw.line(tgt, col, (x, y), (x + ln[3], y))
        # fighters
        bob = math.sin(t * 0.15) * 2
        top.blit(self.big_octo, (34, 34 + bob))
        if self.hat:
            hat = pygame.transform.scale(self.hat, (self.hat.get_width() * 4, self.hat.get_height() * 4))
            top.blit(hat, (34 + 32 - hat.get_width() // 2, 34 + bob - hat.get_height() + 16))
        bx, by = W - 14 - self.big_boss.get_width(), H - 26 - self.big_boss.get_height()
        reveal = t - (self.VS_AT - 4)
        if reveal < 0:                                     # a dark silhouette until VS lands
            bot.blit(self.boss_shadow, (bx + 3, by + 3))
            bot.blit(self.boss_shadow, (bx, by))
            pygame.draw.rect(bot, acc, (bx + self.big_boss.get_width() // 2 - 8, by + 30, 4, 3))
            pygame.draw.rect(bot, acc, (bx + self.big_boss.get_width() // 2 + 6, by + 30, 4, 3))
        else:
            shake = (self.rnd.randint(-2, 2), self.rnd.randint(-2, 2)) if (t // 3) % 8 == 0 else (0, 0)
            bot.blit(self.boss_shadow, (bx + 4, by + 4))
            bot.blit(self.big_boss, (bx + shake[0], by + shake[1]))
            if reveal < 8:
                lit = self.boss_lit.copy()
                lit.set_alpha(255 - reveal * 32)
                bot.blit(lit, (bx, by))
        # names
        tag = self._big("OCTO", 2, (160, 210, 255))
        top.blit(tag, (112, 50 + bob))
        if t > self.VS_AT + 6:
            tw = gfx.text_width(self.name)
            nm = self._big(self.name, 2 if tw < 54 else 1.5 if tw < 72 else 1, (255, 220, 120))
            k = self._ease((t - self.VS_AT - 6) / 16)
            bot.blit(nm, (12 - (1 - k) * 200, H - 64))
            if t > self.VS_AT + 18:
                n = t - self.VS_AT - 18
                gfx.text(bot, self.subtitle[:n], 12, H - 25, (235, 205, 205))
        off = (1 - p_in) * (W + 40)
        scr.blit(top, (-off - gap, -gap * 0.3))
        scr.blit(bot, (off + gap, gap * 0.3))
        # the glowing slash between the panels
        if not opening:
            sl = pygame.Surface((W, H), pygame.SRCALPHA)
            a = int(255 * p_in)
            pygame.draw.line(sl, (255, 255, 255, a), (0, mid + slope), (W, mid - slope), 3)
            pygame.draw.line(sl, acc + (a // 2,), (0, mid + slope + 3), (W, mid - slope + 3), 2)
            pygame.draw.line(sl, (120, 170, 255, a // 2), (0, mid + slope - 3), (W, mid - slope - 3), 2)
            scr.blit(sl, (0, 0))
        # ---- 3: VS slams down
        if t >= self.VS_AT - 6 and not opening:
            u = t - (self.VS_AT - 6)
            sc = max(3.0, 9 - u * 1.1)
            vs = self._big("VS", sc, (255, 240, 120), outline=(120, 20, 20))
            if u < 6:
                vs.set_alpha(80 + u * 30)
            scr.blit(vs, vs.get_rect(center=(W / 2, mid + math.sin(t * 0.3) * (1 if u > 8 else 0))))
            if t - self.VS_AT in range(0, 8):
                ring = t - self.VS_AT
                pygame.draw.circle(scr, (255, 255, 255), (W // 2, int(mid)), 10 + ring * 12, 2)
                if ring < 3:
                    v = pygame.Surface((W, H))
                    v.fill((255, 255, 255))
                    v.set_alpha(160 - ring * 50)
                    scr.blit(v, (0, 0))
        # cinema bars
        bar = int(14 * min(1.0, t / 20) * (1 - self._ease((t - self.OPEN) / 30) if opening else 1))
        if bar:
            pygame.draw.rect(scr, (0, 0, 0), (0, 0, W, bar))
            pygame.draw.rect(scr, (0, 0, 0), (0, H - bar, W, bar))
