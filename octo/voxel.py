"""Octo in 3D, still in his pixel style: every pixel of his sprite becomes a little cube.

A model is built from a sprite's front view (and its back view, for when he turns round); the
cubes bulge out where his body is round, so he's a chunky 3D figurine rather than a flat card.
Each cube is drawn as a small lit block (a front face and a brighter top), sorted back to front,
with lighting that follows him as he turns. Renders are cached, so the game can afford a 3D Octo
every frame, and the cinematics use the same models at any size.
"""
import math

import pygame

import gfx

_L = (-0.5, 0.62, 0.62)                 # towards the light, in view space (x right, y to the viewer, z up)
_LN = math.sqrt(sum(c * c for c in _L))
LIGHT = tuple(c / _LN for c in _L)


class VoxelModel:
    """Surface voxels of a figure: (x, y, z, colour, normal). x right, y towards the viewer, z up,
    in voxel units, with the feet at z = 0 and the middle at x = y = 0."""

    def __init__(self, cells, normals=None):
        occ = set(cells)
        normals = normals or {}
        self.vox = []
        dirs = [(dx, dy, dz) for dx in (-1, 0, 1) for dy in (-1, 0, 1) for dz in (-1, 0, 1) if dx or dy or dz]
        for (x, y, z), col in cells.items():
            if all((x + d[0], y + d[1], z + d[2]) in occ for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0),
                                                                   (0, 0, 1), (0, 0, -1))):
                continue                                    # buried inside: never seen
            if (x, y, z) in normals:                        # a smooth, known shape (Octo's round head)
                self.vox.append((x, y, z, col, normals[(x, y, z)]))
                continue
            nx = ny = nz = 0.0
            for dx, dy, dz in dirs:                         # points out of the body, towards empty space
                if (x + dx, y + dy, z + dz) not in occ:
                    w = 1.0 / math.sqrt(dx * dx + dy * dy + dz * dz)
                    nx += dx * w
                    ny += dy * w
                    nz += dz * w
            n = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            self.vox.append((x, y, z, col, (nx / n, ny / n, nz / n)))
        zs = [v[2] for v in self.vox] or [0]
        self.top = max(zs) + 1


def _profile_cells(front, back=None, depth=4.0, legs_from=None, z0=0, x_off=0.0, ball=False, fill=None,
                   outline=None, normals=None):
    """Extrude a sprite into voxels, round in the middle. legs_from: rows from here down stay thin.
    ball: the body is a true ellipsoid, as deep as it is wide (round from every side)."""
    w, h = front.get_size()
    cells = {}
    rows = []
    for py in range(h):
        xs = [px for px in range(w) if front.get_at((px, py)).a > 128]
        rows.append((min(xs), max(xs)) if xs else None)
    filled = [i for i, r in enumerate(rows) if r]
    if not filled:
        return cells
    top, bottom = filled[0], filled[-1]
    body_bottom = (legs_from - 1) if legs_from is not None else bottom
    cy = (top + body_bottom) / 2
    ry = max(1.0, (body_bottom - top) / 2 + 0.5)
    if ball:
        bx0 = min(r[0] for r in rows[top:body_bottom + 1] if r)
        bx1 = max(r[1] for r in rows[top:body_bottom + 1] if r)
        bcx, brx = (bx0 + bx1) / 2, (bx1 - bx0) / 2 + 0.5
    for py in range(h):
        r = rows[py]
        if not r:
            continue
        x0, x1 = r
        mid, half = (x0 + x1) / 2, (x1 - x0) / 2 + 0.5
        for px in range(x0, x1 + 1):
            c = front.get_at((px, py))
            if c.a <= 128:
                continue
            if legs_from is not None and py >= legs_from:
                t = 2 if ball else 1
                if ball:                                      # tentacles curl round the body
                    u = (px - bcx) / brx
                    t = max(1, int(round(depth * 0.55 * math.sqrt(max(0.0, 1 - u * u)))))
            elif ball:
                u = (px - bcx) / brx
                v = (py - cy) / ry
                t = int(round(depth * math.sqrt(max(0.0, 1 - u * u - v * v * 0.85))))
            else:
                u = (px - mid) / half
                v = (py - cy) / ry
                t = int(round(depth * math.sqrt(max(0.0, 1 - u * u)) * math.sqrt(max(0.0, 1 - (v * 0.75) ** 2))))
            front_col = (c.r, c.g, c.b)
            legs = legs_from is not None and py >= legs_from
            if ball and front_col == outline:
                if legs:
                    continue                              # gaps between tentacles are just water
                front_col = fill                          # a round head's outline is its edge, drawn later
            inside = fill if (fill is not None and not legs and (outline is None or front_col == outline or ball)) \
                else front_col
            for d in range(-t, t + 1):
                if d == t:
                    col = front_col                       # his face, exactly as the pixel art
                elif d == -t and back is not None:
                    b = back.get_at((w - 1 - px, py))
                    col = (b.r, b.g, b.b) if b.a > 128 and (b.r, b.g, b.b) != outline else inside
                else:
                    col = inside if fill is not None else front_col
                pos = (px - w // 2 + int(x_off), d, z0 + (h - 1 - py))
                cells[pos] = col
                if ball and normals is not None and not legs:
                    nx_, ny_, nz_ = (px - bcx) / brx, d / max(1.0, depth), -(py - cy) / ry
                    nn = math.sqrt(nx_ * nx_ + ny_ * ny_ + nz_ * nz_) or 1.0
                    normals[pos] = (nx_ / nn, ny_ / nn, nz_ / nn)
    return cells


_models = {}


def octo_model(mood, frame, hat=None):
    """Octo (any form) as voxels, wearing a voxel hat."""
    key = ('octo', mood, frame, hat)
    m = _models.get(key)
    if m is None:
        front = gfx.OCTO[mood]['down'][frame]
        back = gfx.OCTO[mood]['up'][frame]
        pal = gfx.OCTO_PAL[mood]
        normals = {}
        cells = _profile_cells(front, back, depth=7.0, legs_from=11, ball=True, fill=tuple(pal['B']),
                               outline=tuple(pal['k']), normals=normals)
        if hat and hat != 'none':
            import style
            # where draw_hat puts it: the hat's bottom rows sit on the top of his head
            cells.update(_profile_cells(style._hat(hat), None, depth=3.0, z0=12))
        m = _models[key] = VoxelModel(cells, normals)
    return m


def sprite_model(img, depth=4.0, key=None):
    """Any sprite (a boss, a turtle) as a puffy voxel figure."""
    key = key or ('spr', id(img))
    m = _models.get(key)
    if m is None:
        m = _models[key] = VoxelModel(_profile_cells(img, None, depth=depth))
    return m


# ---- the little cubes -------------------------------------------------------------------------
_cubes = {}


def _cube(col, s, fh, th, side):
    """A cube seen from the front and a little above: a front face s x fh, a brighter top s x th,
    and (when turned) a darker side face |side| wide on the left (side < 0) or right."""
    key = (col, s, fh, th, side)
    img = _cubes.get(key)
    if img is None:
        sw = abs(side)
        img = pygame.Surface((s + sw, fh + th), pygame.SRCALPHA)
        fx = sw if side < 0 else 0
        top = tuple(min(255, int(c * 1.22 + 18)) for c in col)
        if sw:
            dark = tuple(int(c * 0.62) for c in col)
            img.fill(dark, (0 if side < 0 else s, th, sw, fh))
            if th:
                img.fill(top, (0 if side < 0 else s, 0, sw, th))
        if th:
            img.fill(top, (fx, 0, s, th))
        img.fill(col, (fx, th, s, fh))
        if s >= 8 and th:                                 # a bright lip along each cube's top edge
            pygame.draw.line(img, tuple(min(255, int(c * 1.4 + 30)) for c in col), (fx, 0), (fx + s - 1, 0))
        if len(_cubes) > 8000:
            _cubes.clear()
        _cubes[key] = img
    return img


def render(model, s, yaw=0.0, pitch=0.6, tint=None, flash=False, outline=None):
    """Draw a model with cubes of s pixels. Returns (surface, (ax, ay)): the point where the
    figure's feet touch the ground, in the surface's pixels.

    Depth never moves a cube up or down the screen, so from the front the figure is exactly its
    pixel art; turning it shows how round it is, and the tops and sides of the cubes show."""
    cy, sy_ = math.cos(yaw), math.sin(yaw)
    sp = math.sin(pitch)
    si = max(1, int(round(s)))
    fh = si                                               # figures stand up: no squashing
    th = int(round(s * sp * 0.55)) if s >= 4 else 0       # tiny cubes: smooth, no stair-step tops
    side = 0                                              # (light and shade show which way he's turned)
    if s >= 5:
        si += 1                                           # overlap a hair: no gaps between turned cubes
    lx, ly, lz = LIGHT
    pts = []
    for x, y, z, col, (nx, ny, nz) in model.vox:
        X = x * cy - y * sy_
        Y = x * sy_ + y * cy
        rnx = nx * cy - ny * sy_
        rny = nx * sy_ + ny * cy
        lam = rnx * lx + rny * ly + nz * lz
        if s >= 6:
            k = 0.6 + 0.55 * max(0.0, lam) + 0.1 * max(0.0, rny)
        else:                                             # small: smooth, like a shaded ball
            k = 0.66 + 0.48 * max(0.0, lam) - 0.12 * max(0.0, -rny)
        if flash:
            c = (255, 255, 255)
        else:
            k = round(k * 16) / 16
            c = (min(255, int(col[0] * k)), min(255, int(col[1] * k)), min(255, int(col[2] * k)))
            if tint:                                      # one colour (stone, gold): keep the shading
                lum = (c[0] * 30 + c[1] * 59 + c[2] * 11) // 100
                lum = min(255, 50 + lum * 4 // 5)
                c = (lum * tint[0] // 255, lum * tint[1] // 255, lum * tint[2] // 255)
        pts.append((Y, z, X * s, -z * s, c))
    if not pts:
        return pygame.Surface((1, 1), pygame.SRCALPHA), (0, 0)
    pts.sort(key=lambda p: (p[0], p[1]))
    sw = abs(side)
    minx = min(p[2] for p in pts) - si - sw
    maxx = max(p[2] for p in pts) + si + sw
    miny = min(p[3] for p in pts) - fh - th
    maxy = max(p[3] for p in pts) + fh
    w, h = int(maxx - minx) + 2, int(maxy - miny) + 2
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    off = sw if side < 0 else 0
    for _, _, px, py, c in pts:
        surf.blit(_cube(c, si, fh, th, side), (int(px - minx - si / 2) - off, int(py - miny - fh / 2 - th)))
    ax = -minx
    ay = -miny + fh / 2                                   # the bottom of the lowest cubes
    if outline is not None and not flash:                 # a crisp outline round the whole figure
        ow = max(1, int(round(s / 4)))
        sil = surf.copy()
        sil.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
        sil.fill(tuple(outline) + (0,), special_flags=pygame.BLEND_RGBA_ADD)
        out = pygame.Surface((w + ow * 2, h + ow * 2), pygame.SRCALPHA)
        for dx, dy in ((-ow, 0), (ow, 0), (0, -ow), (0, ow)):
            out.blit(sil, (ow + dx, ow + dy))
        out.blit(surf, (ow, ow))
        return out, (ax + ow, ay + ow)
    return surf, (ax, ay)


_renders = {}


def cached(key, model, s, yaw, pitch, tint=None, flash=False, outline=None):
    out = _renders.get(key)
    if out is None:
        if len(_renders) > 900:
            _renders.clear()
        out = _renders[key] = render(model, s, yaw, pitch, tint, flash, outline)
    return out


def octo_image(mood, frame, yaw, s, pitch=0.6, hat=None, flash=False, tint=None):
    """A cached render of Octo. Angles are rounded so turning reuses earlier renders."""
    yq = round(yaw / (math.pi / 24)) % 48
    pq = round(pitch * 20)
    sq = round(s * 4) / 4
    key = ('o', mood, frame, hat, yq, pq, sq, flash, tint)
    edge = tuple(gfx.OCTO_PAL[mood]['k']) if not tint else None
    return cached(key, octo_model(mood, frame, hat), sq, yq * math.pi / 24, pq / 20, tint, flash, edge)


REFS = (2, 3, 4, 6, 9, 13, 19, 28, 40)              # sizes renders are made at, then shrunk to fit


class VoxelFigure:
    """Drop-in for hifi's 3D models in the cinematics: items() returns depth-sorted draw calls."""

    def __init__(self, mood=None, hat=None, sprite=None, depth=4.0, tint=None):
        self.mood, self.hat, self.sprite, self.depth, self.tint = mood, hat, sprite, depth, tint

    def model(self, frame):
        if self.sprite is not None:
            return sprite_model(self.sprite, self.depth)
        return octo_model(self.mood, frame, self.hat)

    def image(self, s, yaw, pitch, frame=0, flash=False, tint=None):
        """A render with cubes of about s pixels (made at the next size up and shrunk smoothly)."""
        tint = tint or self.tint
        ref = next((r for r in REFS if r >= s - 0.01), REFS[-1])
        steps = 48 if self.sprite is None else 72
        yq = round(yaw / (math.tau / steps)) % steps
        pq = round(pitch * 20)
        key = ('f', id(self.sprite) if self.sprite is not None else (self.mood, self.hat, frame), self.depth,
               ref, yq, pq, flash, tint)
        edge = tuple(gfx.OCTO_PAL[self.mood]['k']) if self.sprite is None and not tint else None
        img, (ax, ay) = cached(key, self.model(frame), ref, yq * math.tau / steps, pq / 20, tint, flash, edge)
        if abs(s - ref) > 0.05:
            k = s / ref
            img = pygame.transform.smoothscale(img, (max(1, int(img.get_width() * k)), max(1, int(img.get_height() * k))))
            ax, ay = ax * k, ay * k
        return img, (ax, ay)

    def items(self, pos, yaw=0.0, pitch=0.0, t=0.0, size=1.0, cx=None, cy=None, frame=None, flash=False,
              scale=None, dark=0.0, lit=0.0, **_ignored):
        """pos: the figure's middle in camera space. size: about half its height in world units
        (or scale: world units per pixel of the sprite). dark: a silhouette, lit: a white flash."""
        import hifi
        cx = hifi.W / 2 if cx is None else cx
        cy = hifi.H / 2 if cy is None else cy
        px, py, pz = pos
        sx, sy, k = hifi.project(px, py, pz, cx, cy)
        s = max(1.0, scale * k if scale is not None else size * k / 8.0)
        fr = frame if frame is not None else (int(t) // 16) % 2
        img, (ax, ay) = self.image(s, yaw, 0.45 + pitch, fr, flash or lit > 0.5,
                                   tint=(26, 20, 44) if dark > 0.5 else None)
        half = (8 if self.sprite is None else self.sprite.get_height() / 2) * s
        x = sx - ax
        y = sy - ay + half                                  # pos is the middle; the anchor is the feet

        def fn(surf, img=img, x=x, y=y):
            surf.blit(img, (int(x), int(y)))
        return [(pz, fn)]
