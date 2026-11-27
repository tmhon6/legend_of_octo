"""3D models for Octo's house: the house itself (a round blue dome with Octo's face, its door is
his mouth), its mailbox, and everything inside -- the walls, the bed, the trophy shelf, the
desk with Octo's diary, the fish tank, the tea table, Pebble's basket, the hat stand, a
jellyfish lamp, a sea anemone in a pot and a round rug.

Built like every other model in props3d (world pixels, origin at the footprint's north-west
corner) and registered in props3d.BUILDERS.
"""
import math

from props3d import Model, dk, lt
from settings import HI

BODY = (64, 116, 232)                   # Octo blue, a touch brighter than his pixel art
PINK = (244, 104, 172)
BLUSH = (246, 126, 180)
WOOD = (196, 140, 92)
WOOD_D = (150, 100, 62)
WOOD_L = (228, 184, 132)
PAPER = (134, 194, 220)                  # the wallpaper: soft sea blue with paler stripes
STRIPE = (150, 206, 228)
WAINSCOT = (176, 122, 80)
TRIM = (230, 190, 132)
TAU = math.tau


def _ellipse(cx, cy, rx, ry, z, n=24):
    return [(cx + rx * math.cos(i / n * TAU), cy + ry * math.sin(i / n * TAU), z) for i in range(n)]


def _shadow(m, cx, cy, rx, ry, a=64):
    """A soft shadow on the floor, drawn before everything else in the model."""
    m.face(_ellipse(cx, cy, rx, ry, 0.05, 20), (0, 0, 24, a), (0, 0, 1), lit=False, bias=-500)


def _shadow_rect(m, x0, y0, x1, y1, a=64):
    m.face([(x0, y0, 0.05), (x1, y0, 0.05), (x1, y1, 0.05), (x0, y1, 0.05)], (0, 0, 24, a), (0, 0, 1), lit=False,
           bias=-500)


# ======================================================================
# outside: the house and its mailbox
# ======================================================================
def octo_home(blink=False):
    """Octo's house: a dome shaped like his head, big round eye windows, pink cheeks, an arched
    door for a mouth, stubby tentacles round its base and a coral chimney puffing bubbles."""
    m = Model()
    body = BODY
    cx, cy, rx, ry, rz, z0 = 40, 31, 30, 21, 46, 10
    _shadow(m, cx, cy + 4, rx + 6, ry + 7, 80)
    m.cyl(cx, cy, rx, 0, z0, dk(body, 0.86), n=32, ry=ry, lid=False)
    m.dome(cx, cy, rx, ry, rz, z0, body, n=32, rings=12)
    for deg in (8, 36, 62, 118, 144, 172):                       # stubby tentacles, pink-tipped
        a = math.radians(deg)
        ca, sa = math.cos(a), math.sin(a)
        m.dome(cx + (rx - 1) * ca, cy + (ry - 1) * sa, 7.5, 6, 8, 0, dk(body, 0.94), n=14, rings=4)
        m.dome(cx + (rx + 5) * ca, cy + (ry + 4.5) * sa, 4.6, 4, 5, 0, body, n=12, rings=3)
        m.dome(cx + (rx + 8.5) * ca, cy + (ry + 7.5) * sa, 2.6, 2.4, 3, 0, PINK, n=10, rings=2)

    def on_dome(az, el, out=0.8):
        a, t = math.radians(az), math.radians(el)
        return (cx + (rx + out) * math.cos(t) * math.cos(a), cy + (ry + out) * math.cos(t) * math.sin(a),
                z0 + (rz + out) * math.sin(t))
    for side in (-1, 1):
        x, y, z = on_dome(90 - side * 21, 30)
        if blink:                                                # eyes shut: happy little arcs
            pts = [(x + 3.8 * math.cos(th), y + 0.4, z + 1.2 + 2.8 * math.sin(th))
                   for th in [math.pi + 0.3 + i * (math.pi - 0.6) / 8 for i in range(9)]]
            for a_, b_ in zip(pts, pts[1:]):
                m.line(a_, b_, (14, 22, 60), w=1.7, bias=6.6)
        else:
            m.disc_v(x, y, z, 5.8, (24, 44, 110), rz=7.2, n=18, lit=False, bias=6)
            m.disc_v(x, y + 0.2, z, 4.8, (16, 20, 46), rz=6.2, n=18, lit=False, bias=6.2)
            m.disc_v(x - 1.6, y + 0.4, z + 2.1, 1.7, (255, 255, 255), n=10, lit=False, bias=6.4)
            m.disc_v(x + 1.5, y + 0.4, z - 2.0, 0.8, (150, 190, 255), n=8, lit=False, bias=6.4)
        bx, by, bz = on_dome(90 - side * 36, 17)
        m.disc_v(bx, by, bz, 4.2, BLUSH, rz=2.4, n=14, lit=False, bias=6)
    yf = cy + ry + 0.6                                           # the door: his mouth
    m.face([(31, yf + 1.4, 0.15), (49, yf + 1.4, 0.15), (49, yf + 8, 0.15), (31, yf + 8, 0.15)], (236, 206, 130),
           (0, 0, 1), lines=[((33, yf + 3, 0.2), (47, yf + 3, 0.2), (214, 176, 100)),
                             ((33, yf + 6.4, 0.2), (47, yf + 6.4, 0.2), (214, 176, 100))])
    m.quad_s(32.5, 47.5, yf, 0, 21, PINK, arch=True, bias=6)
    m.quad_s(34.5, 45.5, yf + 0.3, 0, 19, (54, 26, 70), arch=True, bias=6.3)
    m.disc_v(43.4, yf + 0.6, 8.5, 0.95, (255, 220, 120), bias=6.6)
    # a coral chimney at the back of his head
    m.cyl(53, 22, 3.6, 40, 55, (238, 118, 150), n=12, top=(120, 50, 70))
    m.cyl(53, 22, 4.5, 54, 57, (250, 150, 176), n=12, top=(120, 50, 70))
    return m


def mailbox(flag_up=False):
    m = Model()
    _shadow(m, 8, 11.5, 6, 3.6, 60)
    m.cyl(8, 10, 1.3, 0, 12, WOOD_D, n=8)
    m.box(3.5, 5.5, 11.5, 12.5, 13, 16, BODY)
    m.cyl(8, 9.25, 4.5, 15.9, 16.1, BODY, n=14, ry=3.75)
    m.dome(8, 9.25, 4.5, 3.75, 3.2, 16, BODY, n=14, rings=3)
    m.quad_s(5.4, 10.6, 13.15, 13.6, 14.8, (20, 30, 70), bias=0.8)
    m.disc_v(8, 13.2, 17.2, 1.3, (255, 255, 255), bias=1.0)
    red = (236, 56, 70)
    if flag_up:                                     # you've got mail!
        m.line((12.7, 9, 13), (12.7, 9, 27), (90, 64, 40), w=0.8, bias=1)
        m.face([(12.8, 9, 27), (12.8, 15, 26), (12.8, 15, 22), (12.8, 9, 22.4)], red, (1, 0, 0), lit=False, bias=1.2)
        m.face([(12.85, 9, 27), (12.85, 15, 26), (12.85, 15, 25.2), (12.85, 9, 26.2)], (255, 120, 130), (1, 0, 0),
               lit=False, bias=1.3)
    else:
        m.face([(12.8, 6.2, 13.2), (12.8, 11.8, 13.2), (12.8, 11.8, 15.4), (12.8, 6.2, 15.4)], dk(red, 0.8), (1, 0, 0),
               lit=False, bias=1.2)
    return m


# ======================================================================
# inside: the walls
# ======================================================================
def _porthole(m, x, y, z, r, b=60):
    brass = (214, 172, 90)
    m.disc_v(x, y + 0.2, z, r + 1.8, dk(brass, 0.8), n=20, bias=b)
    m.disc_v(x, y + 0.3, z, r + 1.2, brass, n=20, bias=b + 0.1)
    m.disc_v(x, y + 0.45, z, r, (40, 96, 166), n=20, bias=b + 0.3)
    m.disc_v(x - r * 0.35, y + 0.6, z + r * 0.4, r * 0.32, (150, 210, 250), n=10, bias=b + 0.5)
    for i in range(6):
        a = i / 6 * TAU + 0.5
        m.disc_v(x + (r + 0.6) * math.cos(a), y + 0.55, z + (r + 0.6) * math.sin(a), 0.45, lt(brass, 0.4), n=6,
                 bias=b + 0.4)


PORTHOLES = [(32, 33, 6.5), (184, 30, 5)]        # (x, z, radius) on the back wall
PICTURE = (146, 174, 20, 38)                     # x0, x1, z0, z1 (above the desk)


def wall_back():
    """The back wall: striped wallpaper over wood panelling, two portholes looking out to sea,
    a picture of Octo and Pebble, and a string of little flags for a house-warming."""
    import coop
    import voxel
    m = Model()
    W, D, H = 256, 32, 56
    lines = [((x, D, 14.5), (x, D, H), STRIPE) for x in range(6, W, 12)]
    m.face([(0, D, 0), (W, D, 0), (W, D, H), (0, D, H)], PAPER, (0, 1, 0), lines=lines, lit=False)
    panels = [((x, D + 0.15, 1), (x, D + 0.15, 14), dk(WAINSCOT, 0.82)) for x in range(16, W, 16)]
    m.face([(0, D + 0.15, 0), (W, D + 0.15, 0), (W, D + 0.15, 14.5), (0, D + 0.15, 14.5)], WAINSCOT, (0, 1, 0),
           lines=panels, lit=False, bias=40)
    m.line((0, D + 0.3, 14.5), (W, D + 0.3, 14.5), TRIM, w=1.5, bias=45)
    m.line((0, D + 0.3, 0.7), (W, D + 0.3, 0.7), dk(WAINSCOT, 0.66), w=1.2, bias=45)
    m.face([(0, 0, H), (W, 0, H), (W, D, H), (0, D, H)], TRIM, (0, 0, 1))
    m.face([(W, 0, 0), (W, D, 0), (W, D, H), (W, 0, H)], (30, 36, 70), (1, 0, 0), lit=False)
    for x, z, r in PORTHOLES:
        _porthole(m, x, D, z, r)
    # the family picture: Octo and Pebble
    x0, x1, z0, z1 = PICTURE
    m.quad_s(x0, x1, D + 0.2, z0, z1, (150, 96, 56), bias=60)
    m.quad_s(x0 + 2, x1 - 2, D + 0.35, z0 + 2, z1 - 2, (252, 238, 206), bias=60.2)
    octo, (ax, ay) = voxel.octo_image('blue', 0, 0.3, HI * 0.62, 0.55, 'party')
    m.image(octo, (x0 + 10, D + 0.5, z0 + 2.6), (ax, ay), bias=75)
    snail = voxel.render(voxel.sprite_model(coop.frames()['left'][0], 3.0), HI * 0.5, -0.4, 0.55)
    m.image(snail[0], (x1 - 7.5, D + 0.5, z0 + 2.6), snail[1], bias=75)
    # house-warming bunting along the top
    cols = [(240, 90, 120), (250, 210, 90), (110, 200, 140), (120, 160, 250), (250, 150, 90)]
    k = 0
    for xs in range(0, W, 64):
        pts = [(xs + i * 8, 39.5 - 2.5 * math.sin(math.pi * i / 8)) for i in range(9)]
        for (xa, za), (xb, zb) in zip(pts, pts[1:]):
            m.line((xa, D + 0.5, za), (xb, D + 0.5, zb), (90, 70, 60), w=0.6, bias=70)
        for (xa, za), (xb, zb) in zip(pts[:-1:1], pts[1::1]):
            xm = (xa + xb) / 2
            m.face([(xa + 1, D + 0.6, za - 0.2), (xb - 1, D + 0.6, zb - 0.2), (xm, D + 0.6, (za + zb) / 2 - 5)],
                   cols[k % len(cols)], (0, 1, 0), lit=False, bias=71)
            k += 1
    return m


def wall_front():
    """A low front wall with the way out: a gap with a doormat, between two posts."""
    m = Model()
    top, side = (216, 172, 118), (150, 100, 62)
    for x0, x1 in ((0, 110), (146, 256)):
        m.box(x0, 0, 0, x1, 16, 7, side, top=top)
    for x in (106, 146):
        m.box(x, 0.5, 0, x + 4, 15.5, 12, dk(side, 0.9), top=lt(top, 0.12))
    m.face([(113, 2, 0.15), (143, 2, 0.15), (143, 14, 0.15), (113, 14, 0.15)], (214, 92, 124), (0, 0, 1), lit=False,
           lines=[((115, 4, 0.2), (141, 4, 0.2), (244, 170, 190)), ((115, 12, 0.2), (141, 12, 0.2), (244, 170, 190))])
    return m


# ======================================================================
# inside: the furniture
# ======================================================================
def bed(blanket_only=False):
    """Octo's bed. blanket_only: just the covers and the footboard (drawn over a sleeping Octo)."""
    m = Model()
    blanket = (90, 138, 240)
    if not blanket_only:
        _shadow_rect(m, 1, 2, 31.5, 48, 70)
        m.box(1.5, 3, 0, 30.5, 46, 9, WOOD_D, top=WOOD)
        for x in (0, 28):
            m.box(x, 0, 0, x + 4, 4, 26, WOOD, top=WOOD_L)
            m.dome(x + 2, 2, 2.5, 2.5, 2.4, 26, WOOD_L, n=10, rings=3)
        m.box(4, 0.6, 8, 28, 3.4, 23, WOOD, top=WOOD_L)
        m.disc_v(16, 3.5, 16, 3.2, PINK, rz=2.8, bias=1)
        m.box(2.5, 4, 9, 29.5, 45, 13, (246, 244, 250))
        m.dome(16, 9.5, 10, 4.5, 4.5, 13, (255, 255, 255), n=16, rings=4)
    stripes = [((2.4, y, 15.06), (29.6, y, 15.06), lt(blanket, 0.25)) for y in (25, 32, 39)]
    m.box(2.2, 17, 13, 29.8, 45.4, 15, blanket, top=lt(blanket, 0.06))
    m.face([(2.2, 17, 15.05), (29.8, 17, 15.05), (29.8, 45.4, 15.05), (2.2, 45.4, 15.05)], lt(blanket, 0.06), (0, 0, 1),
           lines=stripes, bias=0.1)
    m.box(29.8, 17, 8.5, 30.6, 45.4, 15, blanket)
    m.box(2.2, 16.6, 15, 29.8, 20.5, 16, (250, 250, 255))
    m.box(0, 44, 0, 32, 48, 17, WOOD, top=WOOD_L)
    return m


SHELVES = (2.2, 15.2, 28.2)                      # heights of the trophy shelf's three shelves


def trophy_shelf():
    m = Model()
    _shadow_rect(m, 0, 0, 64, 16, 60)
    m.face([(0, 1.5, 0), (64, 1.5, 0), (64, 1.5, 40), (0, 1.5, 40)], (124, 84, 54), (0, 1, 0), lit=False)
    for x0 in (0, 61):
        m.box(x0, 0, 0, x0 + 3, 15, 41, WOOD, top=WOOD_L)
    for z in SHELVES:
        m.box(3, 0, z - 2.2, 61, 15, z, WOOD, top=WOOD_L)
    m.box(-1, -0.5, 39, 65, 15.8, 42, WOOD, top=WOOD_L)
    return m


def desk():
    """The desk, with Octo's diary lying open, an ink pot (of course) and a quill."""
    m = Model()
    _shadow_rect(m, 0.5, 1, 31.5, 15.5, 60)
    for x0 in (0.5, 27.5):
        m.box(x0, 1, 0, x0 + 4, 15, 12.5, WOOD_D, top=WOOD)
    m.box(4.5, 2, 6, 27.5, 14, 12.5, WOOD_D)
    m.quad_s(8, 24, 14.15, 7.4, 11.2, WOOD_L, bias=0.6)
    m.disc_v(16, 14.35, 9.3, 0.9, (250, 210, 90), bias=1)
    m.box(0, 0.5, 12.5, 32, 15.5, 14.5, WOOD, top=WOOD_L)
    m.box(7, 4.5, 14.5, 25, 12.5, 15.1, (190, 48, 72))
    page = (252, 242, 216)
    for xa, xb in ((7.6, 15.8), (16.2, 24.4)):
        lines = [((xa + 1, y, 15.25), (xb - 1, y, 15.25), (170, 160, 150)) for y in (6.6, 8.2, 9.8, 11.4)]
        m.face([(xa, 5, 15.2), (xb, 5, 15.2), (xb, 12, 15.2), (xa, 12, 15.2)], page, (0, 0, 1), lines=lines, bias=0.2)
    m.line((16, 5, 15.3), (16, 12, 15.3), (150, 40, 60), w=0.6, bias=0.3)
    m.cyl(28.5, 6.5, 1.8, 14.5, 17.6, (34, 38, 76), n=10, top=(10, 10, 30))
    m.line((28.4, 6.5, 17.6), (25.5, 3.5, 27.5), (250, 250, 255), w=0.5, bias=0.5)
    m.line((27.6, 5.7, 19.5), (25.7, 3.7, 26.5), (226, 226, 244), w=1.6, bias=0.6)
    return m


TANK = (4, 44, 19.5, 34)                         # where the fish swim: x0, x1, z0, z1 (on the front glass)


def fish_tank():
    m = Model()
    _shadow_rect(m, 0, 1, 48, 16, 60)
    m.box(0, 1, 0, 48, 15, 14, WOOD_D, top=WOOD)
    for xa, xb in ((3, 23), (25, 45)):
        m.quad_s(xa, xb, 15.15, 2, 12, WOOD, bias=0.6)
        m.disc_v(xb - 2.5 if xa == 3 else xa + 2.5, 15.3, 7, 0.8, (250, 210, 90), bias=1)
    water = (70, 158, 214)
    m.box(1.5, 2, 14, 46.5, 14, 37, water, top=(150, 214, 244))
    m.quad_s(1.5, 46.5, 14.1, 14, 18.5, (232, 212, 150), bias=20)
    for x, x2, h, c in ((7, 6, 31, (60, 170, 96)), (9.5, 11.5, 27, (80, 190, 110)), (38, 39.5, 33, (60, 170, 96)),
                        (41, 43, 26, (80, 190, 110))):
        m.line((x, 14.3, 18), (x2, 14.3, h), c, w=1.4, bias=21)
    m.disc_v(24, 14.3, 19.5, 2.6, (240, 120, 160), rz=1.8, bias=21)
    rim = (60, 86, 116)
    for a, b in (((1.5, 14.2, 37), (46.5, 14.2, 37)), ((1.5, 14.2, 14), (46.5, 14.2, 14)),
                 ((1.5, 14.2, 14), (1.5, 14.2, 37)), ((46.5, 14.2, 14), (46.5, 14.2, 37)),
                 ((46.5, 2, 37), (46.5, 14.2, 37)), ((1.5, 2, 37), (46.5, 2, 37))):
        m.line(a, b, rim, w=1.0, bias=25)
    return m


def tea_table():
    """A round table with a teapot and two cups of kelp tea, and two little stools."""
    m = Model()
    _shadow(m, 24, 17, 15, 11, 60)
    for sx in (5.5, 42.5):
        _shadow(m, sx, 19, 5, 3.6, 50)
        m.cyl(sx, 18, 4.4, 0, 8, WOOD_D, n=14, top=(236, 120, 160))
    m.cyl(24, 16, 5, 0, 1.2, WOOD_D, n=14)
    m.cyl(24, 16, 2.2, 1.2, 11, WOOD_D, n=10)
    m.cyl(24, 16, 13, 11, 13, WOOD, n=28, ry=10, top=WOOD_L)
    teal = (110, 200, 190)
    m.dome(21, 14, 4.2, 3.6, 5.5, 13, teal, n=14, rings=4)
    m.dome(21, 14, 1.2, 1.2, 1.2, 18.3, lt(teal, 0.3), n=8, rings=2)
    m.line((24.8, 14.5, 15), (28.6, 14.5, 17.8), teal, w=1.3, bias=0.4)
    m.line((17.1, 14, 14.4), (16.4, 14, 17.6), dk(teal, 0.8), w=1.0, bias=0.4)
    for x, y in ((30, 18.5), (17, 19.5)):
        m.cyl(x, y, 2.0, 13, 15.6, (250, 250, 255), n=12, top=(120, 172, 80))
    return m


def pet_basket():
    """Pebble's wicker basket with a pink cushion."""
    m = Model()
    cx, cy, rx, ry = 16, 8.5, 13, 6.5
    _shadow(m, cx, cy + 1, rx + 1, ry + 1, 60)
    wick, wick2 = (208, 158, 88), (172, 122, 62)
    n = 24
    for i in range(n // 2, n):                               # the inside of the back wall
        a0, a1 = i / n * TAU, (i + 1) / n * TAU
        am = (a0 + a1) / 2
        p0 = (cx + rx * math.cos(a0), cy + ry * math.sin(a0))
        p1 = (cx + rx * math.cos(a1), cy + ry * math.sin(a1))
        nn = (-math.cos(am) / rx, -math.sin(am) / ry, 0)
        ln = math.hypot(nn[0], nn[1])
        m.face([(p0[0], p0[1], 0), (p1[0], p1[1], 0), (p1[0], p1[1], 7), (p0[0], p0[1], 7)], wick2,
               (nn[0] / ln, nn[1] / ln, 0), bias=-2)
    m.cyl(cx, cy, rx - 1.6, 0, 4.2, (236, 120, 150), n=22, ry=ry - 1.3, top=(248, 152, 178))
    m.cyl(cx, cy, rx, 0, 7, wick, n=n, ry=ry, lid=False, bands=[(1.75, wick), (1.75, wick2)] * 2)
    pts = [(cx + rx * math.cos(i / n * TAU), cy + ry * math.sin(i / n * TAU), 7.1) for i in range(n + 1)]
    for a, b in zip(pts, pts[1:]):
        m.line(a, b, lt(wick, 0.35), w=1.1, bias=0.5)
    return m


HOOKS = ((-1, 31), (1, 27), (-1, 22))            # the hat stand's hooks: side, height


def hat_stand():
    m = Model()
    _shadow(m, 8, 10, 6, 4, 60)
    m.cyl(8, 9, 5, 0, 1.6, WOOD_D, n=14, top=WOOD)
    m.cyl(8, 9, 1.1, 1.6, 36, WOOD, n=8)
    m.dome(8, 9, 1.9, 1.9, 1.9, 36, WOOD_L, n=8, rings=2)
    for side, z in HOOKS:
        m.line((8, 9.5, z), (8 + side * 4.2, 10, z + 2.2), WOOD_D, w=0.8, bias=0.3)
    return m


def jelly_lamp():
    m = Model()
    _shadow(m, 8, 10.5, 5, 3.5, 50)
    m.cyl(8, 10, 3.6, 0, 1.4, (120, 90, 140), n=12)
    m.cyl(8, 10, 0.8, 1.4, 22, (200, 190, 220), n=6)
    for k in range(8):
        a = k / 8 * TAU
        x, y = 8 + 4.3 * math.cos(a), 10 + 3.2 * math.sin(a)
        m.line((x, y, 23), (x + 0.7 * math.sin(a * 3), y, 16 + (k % 3)), (250, 160, 220), w=0.6)
    m.cyl(8, 10, 6.2, 21.8, 22.8, (240, 150, 210), n=16, ry=5, lid=False)
    m.dome(8, 10, 6.2, 5, 7, 22.6, (255, 186, 230), n=16, rings=5)
    return m


def anemone():
    """A sea anemone in a flower pot."""
    m = Model()
    _shadow(m, 8, 10.5, 5.5, 3.6, 50)
    m.cyl(8, 10, 4.6, 0, 6.5, (206, 112, 80), n=14, top=(96, 62, 46))
    m.cyl(8, 10, 5.3, 5.6, 7.2, (226, 132, 96), n=14, lid=False)
    for k in range(12):
        a = k / 12 * TAU
        r = 2.6 if k % 2 else 1.2
        x, y = 8 + r * math.cos(a), 10 + r * 0.8 * math.sin(a)
        h = 13 + 2.5 * ((k * 7) % 3)
        tx, ty = x + 2.0 * math.cos(a), y + 1.6 * math.sin(a)
        m.line((x, y, 6.8), (tx, ty, h), (240, 116, 168), w=1.0)
        m.dome(tx, ty, 0.95, 0.95, 0.9, h - 0.4, (255, 204, 232), n=6, rings=2)
    return m


def rug():
    """A round rug in the middle of the room (it lies under everything)."""
    m = Model()
    for i, (rx, ry, col) in enumerate(((38, 29, (58, 98, 196)), (34.5, 26, (246, 234, 204)), (31, 23, (82, 128, 226)),
                                      (19, 14, (246, 234, 204)), (15, 11, (238, 118, 168)))):
        m.face(_ellipse(40, 32, rx, ry, 0.1, 32), col, (0, 0, 1), lit=False, bias=i * 0.01)
    return m


# ======================================================================
# little things: trophies and the like (each modelled round its base)
# ======================================================================
GOLD = (250, 198, 66)


def cup(col=GOLD):
    m = Model()
    m.cyl(0, 0, 2.3, 0, 1.0, dk(col, 0.75), n=12)
    m.cyl(0, 0, 0.7, 1.0, 3.0, dk(col, 0.85), n=6)
    m.cyl(0, 0, 2.5, 3.0, 6.6, col, n=14, top=dk(col, 0.6))
    for side in (-1, 1):
        m.line((side * 2.4, 0, 6), (side * 3.6, 0, 4.6), col, w=0.6, bias=0.5)
        m.line((side * 3.6, 0, 4.6), (side * 2.4, 0, 3.6), col, w=0.6, bias=0.5)
    return m


def bell():
    m = Model()
    bronze = (226, 168, 70)
    m.cyl(0, 0, 2.9, 0, 0.9, dk(bronze, 0.85), n=14)
    m.dome(0, 0, 2.6, 2.6, 4.6, 0.9, bronze, n=14, rings=4)
    m.dome(0, 0, 0.8, 0.8, 1.2, 5.3, dk(bronze, 0.8), n=6, rings=2)
    return m


def crown():
    m = Model()
    m.cyl(0, 0, 2.6, 0, 1.8, GOLD, n=14, lid=False)
    for i in range(5):
        a = i / 5 * TAU + 0.3
        m.cone(2.2 * math.cos(a), 2.2 * math.sin(a), 0.9, 1.8, 3.8, lt(GOLD, 0.1), n=6)
    m.disc_v(0, 2.7, 0.9, 0.7, (230, 40, 70), bias=1)
    return m


def tooth():
    """Grimfin's tooth, on a little stand."""
    m = Model()
    m.box(-2.5, -2, 0, 2.5, 2, 1.2, (110, 76, 46), top=(150, 104, 60))
    m.cone(0, 0, 2.0, 1.2, 9, (250, 248, 236), n=10)
    return m


def golden_pearl():
    m = Model()
    m.cyl(0, 0, 2.2, 0, 1.2, (110, 76, 46), n=10, top=(150, 104, 60))
    m.dome(0, 0, 3.2, 3.2, -3.2, 4.4, (240, 190, 70), n=14, rings=4)
    m.dome(0, 0, 3.2, 3.2, 3.2, 4.4, (255, 220, 110), n=14, rings=4)
    return m


BUILDERS = {
    'o_home': octo_home, 'o_home_blink': lambda: octo_home(blink=True),
    'o_mail': mailbox, 'o_mail_up': lambda: mailbox(flag_up=True),
    'h_wall_back': wall_back, 'h_wall_front': wall_front,
    'h_bed': bed, 'h_bed_covers': lambda: bed(blanket_only=True),
    'h_shelf': trophy_shelf, 'h_desk': desk, 'h_tank': fish_tank, 'h_table': tea_table,
    'h_basket': pet_basket, 'h_hats': hat_stand, 'h_lamp': jelly_lamp, 'h_plant': anemone, 'h_rug': rug,
    't_cup': cup, 't_cup_silver': lambda: cup((214, 220, 236)), 't_bell': bell, 't_crown': crown,
    't_tooth': tooth, 't_pearl': golden_pearl,
}
