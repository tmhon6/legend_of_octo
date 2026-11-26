"""Pixel art for the two towns, drawn in code: street tiles, buildings, gates, townsfolk and the
little things side quests send you looking for."""
import math

import pygame

TILE = 16


def _dk(c, k=0.6):
    return tuple(max(0, int(v * k)) for v in c)


def _lt(c, k=0.45):
    return tuple(min(255, int(v + (255 - v) * k)) for v in c)


def _text(s, x, y, col, surf, center=True):
    import gfx
    if center:
        x -= gfx.text_width(s) // 2
    gfx.text(surf, s, x, y, col, shadow=False)


# ======================================================================
# street tiles
# ======================================================================
def _stone(rnd, base):
    s = pygame.Surface((TILE, TILE))
    s.fill(base)
    pygame.draw.rect(s, _dk(base, 0.85), (0, 0, 16, 16), 1)
    for _ in range(6):
        s.set_at((rnd.randrange(1, 15), rnd.randrange(1, 15)), _lt(base, 0.25))
    for _ in range(4):
        s.set_at((rnd.randrange(1, 15), rnd.randrange(1, 15)), _dk(base, 0.9))
    return s


def _mosaic(rnd, cols, base=(206, 188, 214)):
    """Pale paving stones with now and then a coloured tile set in."""
    s = pygame.Surface((TILE, TILE))
    s.fill(_dk(base, 0.82))
    for y in range(0, 16, 8):
        for x in range(0, 16, 8):
            c = rnd.choice(cols) if rnd.random() < 0.18 else _lt(base, rnd.uniform(0, 0.12))
            pygame.draw.rect(s, c, (x, y, 7, 7))
            pygame.draw.line(s, _lt(c, 0.35), (x, y), (x + 6, y))
    return s


def _coral_brick(rnd, base):
    s = pygame.Surface((TILE, TILE))
    s.fill(_dk(base, 0.55))
    for row, y in enumerate(range(0, 16, 5)):
        off = 4 if row % 2 else 0
        for x in range(-off, 16, 8):
            c = base if rnd.random() < 0.7 else _lt(base, 0.15)
            pygame.draw.rect(s, c, (x + 1, y + 1, 6, 3))
            pygame.draw.line(s, _lt(c, 0.35), (x + 1, y + 1), (x + 6, y + 1))
    return s


def _lamp(rnd, base_tile):
    s = base_tile.copy()
    pygame.draw.rect(s, (90, 60, 110), (7, 5, 2, 10))
    pygame.draw.rect(s, (150, 110, 170), (7, 5, 1, 10))
    pygame.draw.ellipse(s, (70, 40, 90), (5, 13, 6, 3))
    pygame.draw.circle(s, (255, 230, 140), (8, 4), 4)
    pygame.draw.circle(s, (255, 250, 210), (7, 3), 2)
    pygame.draw.circle(s, (240, 120, 170), (8, 4), 4, 1)
    return s


def _kelp_hedge(rnd, base_tile):
    s = base_tile.copy()
    for x in (3, 8, 12):
        h = rnd.randint(9, 13)
        for y in range(15, 15 - h, -1):
            dx = int(round(math.sin(y * 0.6 + x) * 1.2))
            pygame.draw.line(s, (30, 110, 60), (x + dx - 1, y), (x + dx + 1, y))
            s.set_at((x + dx, y), (80, 170, 90))
    return s


def _boardwalk(rnd, base_tile):
    s = base_tile.copy()
    wood = (160, 112, 64)
    for i, y in enumerate(range(0, 16, 4)):
        c = wood if i % 2 else _lt(wood, 0.12)
        pygame.draw.rect(s, c, (0, y, 16, 3))
        pygame.draw.line(s, _dk(wood, 0.7), (0, y + 3), (15, y + 3))
        s.set_at((rnd.randrange(16), y + 1), _dk(wood, 0.8))
    return s


def _fence(rnd, base_tile):
    s = base_tile.copy()
    wood = (130, 96, 60)
    for x in (2, 8, 13):
        pygame.draw.rect(s, _dk(wood, 0.6), (x - 1, 3, 3, 13))
        pygame.draw.rect(s, wood, (x - 1, 3, 2, 12))
        s.set_at((x - 1, 3), _lt(wood, 0.4))
    pygame.draw.line(s, _dk(wood, 0.6), (0, 7), (15, 7), 2)
    pygame.draw.line(s, _dk(wood, 0.6), (0, 12), (15, 12), 2)
    pygame.draw.line(s, _lt(wood, 0.2), (0, 6), (15, 6))
    return s


def _water(rnd, base, line):
    s = pygame.Surface((TILE, TILE))
    s.fill(base)
    for y in (3, 9, 14):
        for x in range(16):
            yy = y + int(round(math.sin(x * 0.7 + y) * 1))
            s.set_at((x, yy % 16), line)
    s.set_at((rnd.randrange(16), rnd.randrange(16)), (255, 255, 255))
    return s


def _grass_on(rnd, base_tile, col):
    s = base_tile.copy()
    for _ in range(10):
        x, y = rnd.randrange(1, 15), rnd.randrange(3, 15)
        pygame.draw.line(s, col, (x, y), (x + rnd.choice((-1, 0, 1)), y - 3))
    return s


def _palm(rnd, base):
    s = base.copy()
    pygame.draw.line(s, (90, 60, 30), (8, 15), (9, 5), 3)
    pygame.draw.line(s, (150, 110, 60), (8, 15), (9, 5), 1)
    for a in (-2.6, -1.9, -1.2, -0.5, 0.2):
        ex, ey = 9 + math.cos(a) * 7, 5 + math.sin(a) * 4 + 2
        pygame.draw.line(s, (30, 100, 40), (9, 5), (ex, ey), 3)
        pygame.draw.line(s, (80, 170, 70), (9, 5), (ex, ey), 1)
    pygame.draw.circle(s, (100, 70, 30), (8, 6), 1)
    return s


def _bush(rnd, base):
    s = base.copy()
    for x, y, r in ((5, 10, 5), (11, 10, 5), (8, 6, 5)):
        pygame.draw.circle(s, (30, 90, 40), (x, y), r)
        pygame.draw.circle(s, (70, 150, 60), (x - 1, y - 1), r - 2)
    s.set_at((7, 5), (250, 120, 160))
    s.set_at((11, 8), (250, 230, 110))
    return s


def make_town_themes(rnd):
    """Themed tiles for the two towns (merged into gfx.TILES['themes'])."""
    oc = {}
    floor = (186, 166, 196)
    oc['.'] = [_stone(rnd, floor) for _ in range(3)] + [_stone(rnd, (176, 158, 190))]
    oc[','] = [_grass_on(rnd, oc['.'][i], (70, 160, 120)) for i in range(2)]
    oc['='] = [_mosaic(rnd, [(240, 170, 190), (170, 210, 240), (250, 220, 150), (200, 170, 240)]) for _ in range(4)]
    oc['#'] = [_coral_brick(rnd, (220, 120, 140)) for _ in range(3)]
    oc['C'] = [_lamp(rnd, oc['.'][i]) for i in range(2)]
    oc['K'] = [_kelp_hedge(rnd, oc['.'][i]) for i in range(2)]
    oc['v'] = [_water(rnd, (50, 110, 190), (110, 170, 230)) for _ in range(2)]
    tt = {}
    sand = (240, 222, 168)
    tt['.'] = [_stone(rnd, sand) for _ in range(2)] + [_stone(rnd, (234, 214, 158)) for _ in range(2)]
    for s in tt['.']:
        pygame.draw.rect(s, sand, (0, 0, 16, 16), 1)
    tt[','] = [_grass_on(rnd, tt['.'][i], (120, 180, 80)) for i in range(2)]
    tt['='] = [_boardwalk(rnd, tt['.'][i]) for i in range(2)]
    tt['#'] = [_fence(rnd, tt['.'][i]) for i in range(2)]
    tt['C'] = [_palm(rnd, tt['.'][i]) for i in range(2)]
    tt['K'] = [_bush(rnd, tt['.'][i]) for i in range(2)]
    tt['v'] = [_water(rnd, (60, 150, 210), (130, 200, 240)) for _ in range(3)]
    return {'octocity': oc, 'turtletown': tt}


# ======================================================================
# buildings
# ======================================================================
def _surf(w, h):
    return pygame.Surface((w * TILE, h * TILE), pygame.SRCALPHA)


def _shadow(s, inset=4):
    w, h = s.get_size()
    sh = pygame.Surface((w, 12), pygame.SRCALPHA)
    pygame.draw.ellipse(sh, (0, 0, 0, 60), (inset, 0, w - inset * 2, 12))
    s.blit(sh, (0, h - 12))


def _round_door(s, cx, bottom, w, h, col=(60, 30, 50), frame=(250, 220, 160)):
    r = pygame.Rect(cx - w // 2, bottom - h, w, h)
    pygame.draw.rect(s, frame, r.inflate(4, 2).move(0, -1), border_top_left_radius=w // 2 + 2,
                     border_top_right_radius=w // 2 + 2)
    pygame.draw.rect(s, col, r, border_top_left_radius=w // 2, border_top_right_radius=w // 2)
    pygame.draw.circle(s, (250, 210, 90), (cx + w // 2 - 3, bottom - h // 2), 1)


def _porthole(s, cx, cy, r=5):
    pygame.draw.circle(s, (90, 70, 60), (cx, cy), r + 1)
    pygame.draw.circle(s, (255, 230, 150), (cx, cy), r - 1)
    pygame.draw.circle(s, (255, 252, 220), (cx - 1, cy - 1), max(1, r // 2))


def octo_house(w, h, body, trim):
    s = _surf(w, h)
    W, Hh = s.get_size()
    _shadow(s)
    dome = pygame.Rect(3, 2, W - 6, Hh - 6)
    pygame.draw.ellipse(s, _dk(body, 0.45), dome)
    pygame.draw.ellipse(s, body, dome.inflate(-4, -4))
    pygame.draw.ellipse(s, _lt(body, 0.35), (12, 8, W // 2 - 6, Hh // 3))
    for i in range(3):
        pygame.draw.arc(s, trim, dome.inflate(-10 - i * 14, -10 - i * 12), 0.25, math.pi - 0.25, 2)
    pygame.draw.rect(s, _dk(body, 0.7), (6, Hh - 12, W - 12, 6), border_radius=3)
    _round_door(s, W // 2, Hh - 7, 14, 20)
    for dx in (-22, 22):
        _porthole(s, W // 2 + dx, Hh - 24)
    pygame.draw.line(s, _dk(body, 0.45), (W // 2, 4), (W // 2, 0))
    pygame.draw.circle(s, (200, 240, 255), (W // 2 + 2, 2), 2, 1)
    return s


def octo_hall():
    s = _surf(12, 6)
    W, Hh = s.get_size()
    _shadow(s, 2)
    cream, gold = (238, 226, 236), (250, 196, 70)
    pygame.draw.rect(s, _dk(cream, 0.5), (6, 38, W - 12, Hh - 44))
    pygame.draw.rect(s, cream, (8, 40, W - 16, Hh - 48))
    pygame.draw.ellipse(s, _dk(gold, 0.5), (50, 2, 92, 62))
    pygame.draw.ellipse(s, gold, (53, 5, 86, 56))
    pygame.draw.ellipse(s, _lt(gold, 0.5), (66, 12, 30, 18))
    pygame.draw.rect(s, _dk(cream, 0.5), (4, 34, W - 8, 8))
    pygame.draw.rect(s, (255, 250, 255), (6, 35, W - 12, 5))
    for i in range(7):
        x = 22 + i * 25
        if 84 < x < 108:
            continue
        pygame.draw.rect(s, _dk(cream, 0.7), (x, 42, 9, Hh - 58))
        pygame.draw.rect(s, (255, 255, 255), (x + 1, 42, 4, Hh - 58))
    pygame.draw.rect(s, _dk(cream, 0.6), (0, Hh - 14, W, 8))
    pygame.draw.rect(s, (220, 210, 224), (2, Hh - 13, W - 4, 3))
    _round_door(s, W // 2, Hh - 14, 22, 30, frame=gold)
    pygame.draw.rect(s, (60, 40, 90), (W // 2 - 30, 24, 60, 11))
    _text("CITY HALL", W // 2, 26, (255, 230, 140), s)
    for x in (10, W - 14):
        pygame.draw.line(s, (120, 90, 60), (x, 40), (x, 10), 2)
        pygame.draw.polygon(s, (240, 90, 140), [(x + 1, 10), (x + 13, 14), (x + 1, 18)])
    return s


def octo_museum():
    s = _surf(10, 5)
    W, Hh = s.get_size()
    _shadow(s, 2)
    stone = (226, 222, 210)
    pygame.draw.polygon(s, _dk(stone, 0.5), [(4, 26), (W // 2, 2), (W - 4, 26)])
    pygame.draw.polygon(s, stone, [(8, 24), (W // 2, 5), (W - 8, 24)])
    pygame.draw.circle(s, (120, 170, 230), (W // 2, 17), 5)
    pygame.draw.rect(s, _dk(stone, 0.5), (4, 25, W - 8, 10))
    pygame.draw.rect(s, (90, 70, 120), (6, 26, W - 12, 8))
    _text("MUSEUM", W // 2, 27, (255, 230, 150), s)
    pygame.draw.rect(s, _dk(stone, 0.6), (8, 35, W - 16, Hh - 44))
    pygame.draw.rect(s, (200, 196, 186), (9, 35, W - 18, Hh - 45))
    for i in range(6):
        x = 14 + i * 26
        pygame.draw.rect(s, _dk(stone, 0.6), (x, 35, 8, Hh - 46))
        pygame.draw.rect(s, (255, 255, 250), (x + 1, 35, 3, Hh - 46))
    pygame.draw.rect(s, _dk(stone, 0.6), (0, Hh - 11, W, 7))
    pygame.draw.rect(s, (60, 40, 50), (W // 2 - 9, Hh - 30, 18, 19))
    return s


def octo_tower():
    s = _surf(3, 5)
    W, Hh = s.get_size()
    _shadow(s, 2)
    shell = (240, 200, 170)
    for i in range(6):
        y0 = Hh - 12 - i * 12
        w = W - 6 - i * 6
        pygame.draw.ellipse(s, _dk(shell, 0.55), ((W - w) // 2, y0 - 10, w, 16))
        pygame.draw.ellipse(s, shell if i % 2 else _lt(shell, 0.25), ((W - w) // 2 + 1, y0 - 9, w - 2, 13))
    pygame.draw.circle(s, (250, 120, 150), (W // 2, 8), 4)
    for y in (30, 50):
        _porthole(s, W // 2, y, 3)
    return s


def stall(label, awning, awning2, goods):
    s = _surf(4, 2)
    W, Hh = s.get_size()
    pygame.draw.rect(s, (110, 76, 46), (4, 6, 3, Hh - 6))
    pygame.draw.rect(s, (110, 76, 46), (W - 7, 6, 3, Hh - 6))
    for i in range(8):
        c = awning if i % 2 == 0 else awning2
        pygame.draw.polygon(s, c, [(i * 8, 2), (i * 8 + 8, 2), (i * 8 + 8, 13), (i * 8 + 4, 16), (i * 8, 13)])
    pygame.draw.line(s, _dk(awning, 0.5), (0, 2), (W - 1, 2), 2)
    pygame.draw.rect(s, (60, 40, 30), (W // 2 - 13, 5, 26, 9))
    _text(label, W // 2, 6, (255, 240, 200), s)
    pygame.draw.rect(s, (90, 60, 36), (2, 20, W - 4, 11))
    pygame.draw.rect(s, (170, 120, 70), (2, 20, W - 4, 4))
    for i, c in enumerate(goods):
        pygame.draw.circle(s, c, (12 + i * 10, 19), 3)
        s.set_at((11 + i * 10, 18), _lt(c, 0.6))
    return s


def fountain():
    import gfx
    s = _surf(4, 4)
    W, Hh = s.get_size()
    _shadow(s, 2)
    pygame.draw.ellipse(s, (120, 110, 140), (2, 16, W - 4, Hh - 20))
    pygame.draw.ellipse(s, (210, 200, 226), (4, 17, W - 8, Hh - 24))
    pygame.draw.ellipse(s, (60, 140, 210), (9, 22, W - 18, Hh - 34))
    for x, y in ((20, 34), (40, 40), (28, 46), (46, 30)):
        pygame.draw.line(s, (180, 230, 255), (x, y), (x + 4, y))
    pygame.draw.rect(s, (170, 160, 186), (W // 2 - 5, 18, 10, 22))
    statue = gfx.OCTO['blue']['down'][0].copy()
    statue.fill((190, 190, 210, 255), special_flags=pygame.BLEND_RGBA_MULT)
    s.blit(statue, (W // 2 - 8, 6))
    for dx in (-10, 10):
        pygame.draw.arc(s, (190, 235, 255), (W // 2 + dx - 8 if dx > 0 else W // 2 + dx, 8, 16, 26), 0.2, 2.9, 1)
    return s


def scoreboard():
    s = _surf(4, 3)
    W, Hh = s.get_size()
    _shadow(s, 4)
    for x in (8, W - 11):
        pygame.draw.rect(s, (90, 60, 40), (x, 26, 4, Hh - 28))
    pygame.draw.rect(s, (110, 76, 46), (0, 0, W, 34), border_radius=3)
    pygame.draw.rect(s, (20, 26, 52), (3, 3, W - 6, 28))
    _text("TOP", W // 2, 5, (255, 220, 120), s)
    for i, c in enumerate(((255, 220, 120), (210, 220, 240), (230, 160, 110))):
        pygame.draw.line(s, c, (8, 15 + i * 5), (W - 9, 15 + i * 5))
        pygame.draw.rect(s, c, (6, 14 + i * 5, 2, 2))
    return s


def octo_gate_inside():
    s = _surf(4, 1)
    W, Hh = s.get_size()
    s.fill((50, 110, 160))
    for x in range(0, W, 6):
        pygame.draw.line(s, (90, 160, 210), (x, 4), (x + 3, 4))
    for x in (0, W - 16):
        pygame.draw.rect(s, (130, 60, 90), (x, 0, 16, 16))
        pygame.draw.rect(s, (230, 130, 160), (x + 2, 0, 12, 15))
        pygame.draw.circle(s, (255, 230, 140), (x + 8, 5), 3)
    return s


def octo_gate_outside():
    import gfx
    s = _surf(3, 2)
    W, Hh = s.get_size()
    body, dark = (230, 130, 160), (130, 60, 90)
    pygame.draw.rect(s, dark, (0, 0, W, Hh))
    pygame.draw.rect(s, body, (2, 2, W - 4, 14))
    for x in (2, W - 16):
        pygame.draw.rect(s, body, (x, 2, 14, Hh - 2))
        pygame.draw.circle(s, (255, 230, 140), (x + 7, 22), 3)
    pygame.draw.rect(s, (20, 40, 90), (16, 14, 16, 18), border_top_left_radius=8, border_top_right_radius=8)
    pygame.draw.rect(s, (60, 140, 220), (19, 18, 10, 14), border_top_left_radius=5, border_top_right_radius=5)
    for y in (20, 25, 30):
        pygame.draw.line(s, (170, 220, 255), (20, y), (27, y))
    emblem = pygame.transform.scale(gfx.OCTO['blue']['down'][0], (12, 12))
    s.blit(emblem, (W // 2 - 6, 1))
    return s


def turtle_house(w, h, shell, trim):
    s = _surf(w, h)
    W, Hh = s.get_size()
    _shadow(s)
    dome = pygame.Rect(3, 4, W - 6, Hh - 8)
    pygame.draw.ellipse(s, _dk(shell, 0.45), dome)
    pygame.draw.ellipse(s, shell, dome.inflate(-4, -4))
    clip = s.get_clip()
    s.set_clip(dome.inflate(-6, -6))
    for row in range(-1, 5):
        for col in range(-1, 7):
            hx = 10 + col * 15 + (7 if row % 2 else 0)
            hy = 10 + row * 12
            pts = [(hx + math.cos(a) * 7, hy + math.sin(a) * 6) for a in (i / 6 * math.tau + math.pi / 6 for i in range(6))]
            pygame.draw.polygon(s, trim, pts, 1)
    s.set_clip(clip)
    pygame.draw.ellipse(s, _lt(shell, 0.35), (14, 9, W // 3, Hh // 5))
    pygame.draw.rect(s, (210, 190, 140), (8, Hh - 14, W - 16, 8), border_radius=3)
    _round_door(s, W // 2, Hh - 7, 14, 18, col=(80, 50, 30), frame=(240, 220, 170))
    _porthole(s, W // 2 + 22, Hh - 22, 4)
    return s


def turtle_elder():
    s = _surf(12, 6)
    W, Hh = s.get_size()
    _shadow(s, 2)
    shell = (120, 150, 80)
    dome = pygame.Rect(6, 2, W - 12, Hh - 8)
    pygame.draw.ellipse(s, _dk(shell, 0.45), dome)
    pygame.draw.ellipse(s, shell, dome.inflate(-4, -4))
    clip = s.get_clip()
    s.set_clip(dome.inflate(-6, -6))
    for row in range(-1, 8):
        for col in range(-1, 14):
            hx = 10 + col * 16 + (8 if row % 2 else 0)
            hy = 8 + row * 13
            pts = [(hx + math.cos(a) * 8, hy + math.sin(a) * 7) for a in (i / 6 * math.tau + math.pi / 6 for i in range(6))]
            pygame.draw.polygon(s, _dk(shell, 0.6), pts, 2)
    s.set_clip(clip)
    pygame.draw.ellipse(s, _lt(shell, 0.4), (30, 10, 60, 18))
    pygame.draw.rect(s, (220, 196, 140), (12, Hh - 16, W - 24, 10), border_radius=4)
    _round_door(s, W // 2, Hh - 8, 24, 30, col=(70, 40, 20), frame=(250, 220, 120))
    pygame.draw.rect(s, (90, 60, 30), (W // 2 - 34, Hh - 54, 68, 12))
    _text("ELDER", W // 2, Hh - 52, (255, 236, 160), s)
    for x in (30, W - 34):
        pygame.draw.line(s, (90, 60, 30), (x, Hh - 10), (x, Hh - 36), 2)
        pygame.draw.circle(s, (255, 200, 90), (x, Hh - 38), 4)
        pygame.draw.circle(s, (255, 250, 200), (x - 1, Hh - 39), 1)
    return s


def lighthouse():
    s = _surf(3, 6)
    W, Hh = s.get_size()
    _shadow(s, 2)
    for i, y in enumerate(range(20, Hh - 8, 10)):
        w = 22 + (y - 20) * 10 // (Hh - 28)
        c = (240, 240, 240) if i % 2 == 0 else (220, 60, 60)
        pygame.draw.rect(s, _dk(c, 0.6), ((W - w) // 2 - 1, y, w + 2, 10))
        pygame.draw.rect(s, c, ((W - w) // 2, y, w, 10))
        pygame.draw.line(s, _lt(c, 0.5), ((W - w) // 2 + 2, y), ((W - w) // 2 + 2, y + 9))
    pygame.draw.rect(s, (60, 60, 70), (W // 2 - 12, 8, 24, 13))
    pygame.draw.rect(s, (255, 236, 150), (W // 2 - 9, 10, 18, 9))
    pygame.draw.circle(s, (255, 255, 230), (W // 2, 14), 3)
    pygame.draw.polygon(s, (200, 50, 50), [(W // 2 - 14, 8), (W // 2, 0), (W // 2 + 14, 8)])
    pygame.draw.rect(s, (70, 50, 40), (W // 2 - 4, Hh - 20, 8, 12))
    return s


def tiki_hut():
    s = _surf(4, 3)
    W, Hh = s.get_size()
    _shadow(s, 4)
    pygame.draw.rect(s, (150, 104, 60), (8, 20, W - 16, Hh - 24))
    for x in range(10, W - 10, 5):
        pygame.draw.line(s, (120, 80, 44), (x, 20), (x, Hh - 5))
    pygame.draw.polygon(s, (120, 90, 40), [(0, 24), (W // 2, 0), (W, 24)])
    pygame.draw.polygon(s, (200, 170, 90), [(4, 22), (W // 2, 3), (W - 4, 22)])
    for i in range(10):
        x = 6 + i * 5
        pygame.draw.line(s, (160, 130, 60), (x, 22), (W // 2 + (x - W // 2) // 3, 6))
    pygame.draw.rect(s, (60, 36, 20), (W // 2 - 6, Hh - 20, 12, 16))
    return s


def campfire():
    s = _surf(2, 2)
    W, Hh = s.get_size()
    for a in range(8):
        ang = a / 8 * math.tau
        pygame.draw.circle(s, (120, 110, 100), (int(W / 2 + math.cos(ang) * 11), int(20 + math.sin(ang) * 7)), 4)
    pygame.draw.line(s, (100, 60, 30), (8, 24), (24, 18), 3)
    pygame.draw.line(s, (100, 60, 30), (8, 18), (24, 24), 3)
    pygame.draw.polygon(s, (240, 90, 30), [(9, 21), (16, 2), (23, 21)])
    pygame.draw.polygon(s, (255, 200, 60), [(12, 21), (16, 8), (20, 21)])
    pygame.draw.polygon(s, (255, 250, 200), [(14, 21), (16, 14), (18, 21)])
    return s


def nest():
    s = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (200, 170, 110), (0, 7, 16, 9))
    pygame.draw.ellipse(s, (226, 200, 140), (1, 7, 14, 6))
    for x, y in ((4, 6), (8, 5), (11, 7)):
        pygame.draw.ellipse(s, (180, 170, 150), (x - 2, y, 6, 7))
        pygame.draw.ellipse(s, (252, 250, 240), (x - 2, y, 5, 6))
    return s


def turtle_gate_inside():
    s = _surf(4, 1)
    W, Hh = s.get_size()
    s.fill((236, 216, 160))
    for x in (0, W - 16):
        pygame.draw.rect(s, (110, 76, 46), (x + 4, 0, 8, 16))
        pygame.draw.circle(s, (255, 200, 90), (x + 8, 4), 3)
    return s


def turtle_gate_outside():
    s = _surf(3, 1)
    W, Hh = s.get_size()
    pygame.draw.rect(s, (110, 76, 46), (0, 0, W, Hh))
    for x in (0, W - 16):
        pygame.draw.rect(s, (160, 112, 64), (x + 2, 0, 12, 16))
        pygame.draw.line(s, (90, 60, 36), (x + 2, 5), (x + 13, 5))
        pygame.draw.line(s, (90, 60, 36), (x + 2, 10), (x + 13, 10))
    pygame.draw.rect(s, (30, 20, 16), (16, 0, 16, 16))
    pygame.draw.rect(s, (236, 216, 160), (18, 3, 12, 13))
    pygame.draw.circle(s, (90, 150, 80), (24, 8), 3)
    return s


def make_city_art():
    return {
        'o_house_a': octo_house(5, 4, (240, 150, 180), (255, 220, 230)),
        'o_house_b': octo_house(5, 4, (170, 140, 230), (230, 210, 255)),
        'o_house_c': octo_house(5, 4, (120, 200, 210), (220, 250, 255)),
        'o_house_d': octo_house(5, 4, (250, 190, 110), (255, 240, 200)),
        'o_house_e': octo_house(5, 4, (150, 210, 150), (230, 255, 220)),
        'o_house_f': octo_house(5, 4, (250, 140, 120), (255, 220, 200)),
        'o_house_g': octo_house(5, 4, (200, 170, 240), (245, 230, 255)),
        'o_hall': octo_hall(),
        'o_museum': octo_museum(),
        'o_tower': octo_tower(),
        'o_stall_ink': stall("INK", (40, 60, 140), (250, 250, 255), [(30, 30, 60), (240, 90, 120), (90, 170, 255)]),
        'o_stall_hat': stall("HATS", (230, 90, 150), (255, 230, 240), [(240, 90, 90), (90, 90, 230), (250, 220, 80)]),
        'o_stall_bank': stall("BANK", (240, 190, 50), (255, 250, 220), [(255, 230, 120), (220, 230, 245), (170, 120, 255)]),
        'o_stall_food': stall("FOOD", (230, 110, 50), (255, 240, 210), [(255, 150, 120), (250, 210, 90), (120, 200, 90)]),
        'o_fountain': fountain(),
        'o_board': scoreboard(),
        'o_gate': octo_gate_inside(),
        'ow_octo_gate': octo_gate_outside(),
        't_house_a': turtle_house(5, 4, (130, 170, 90), (70, 110, 50)),
        't_house_b': turtle_house(5, 4, (190, 140, 80), (120, 80, 40)),
        't_house_c': turtle_house(5, 4, (120, 150, 190), (60, 90, 130)),
        't_house_d': turtle_house(5, 4, (200, 170, 100), (140, 110, 50)),
        't_elder': turtle_elder(),
        't_lighthouse': lighthouse(),
        't_hut': tiki_hut(),
        't_fire': campfire(),
        't_nest': nest(),
        't_stall_hat': stall("HATS", (230, 200, 90), (255, 250, 220), [(240, 200, 100), (240, 120, 150), (120, 190, 240)]),
        't_stall_swap': stall("SWAP", (90, 170, 120), (230, 255, 230), [(250, 230, 140), (170, 120, 255), (90, 170, 255)]),
        't_stall_clinic': stall("HEAL", (240, 240, 245), (230, 80, 80), [(255, 120, 140), (130, 220, 200), (250, 250, 250)]),
        't_gate': turtle_gate_inside(),
        'ow_turtle_gate': turtle_gate_outside(),
    }


# ======================================================================
# townsfolk and quest things
# ======================================================================
TURTLE_ROWS = [
    "................",
    "......kkkk......",
    ".....kSSSSk.....",
    ".....kSewSk.....",
    ".....kSSSSk.....",
    "..kk..kssk..kk..",
    ".kSSkkkkkkkkSSk.",
    "..kkkGLGGgGGkk..",
    "...kGLGgGGgGGk..",
    "...kGGgGGgGGGk..",
    "...kGgGGgGGgGk..",
    "...kGGGgGGgGGk..",
    "..kkkGGGGGGGkkk.",
    ".kSSkkkkkkkkkSSk",
    "..kk.........kk.",
    "................",
]


def turtle_folk(shell, skin, small=False):
    import gfx
    pal = {'k': _dk(shell, 0.3), 'G': shell, 'g': _dk(shell, 0.7), 'L': _lt(shell, 0.4),
           'S': skin, 's': _dk(skin, 0.75), 'e': (0, 0, 0), 'w': (255, 255, 255)}
    a = gfx.from_strings(TURTLE_ROWS, pal)
    rows = list(TURTLE_ROWS)
    rows[3] = ".....kSSSSk....."
    b = gfx.from_strings(rows, pal)
    if small:
        a = pygame.transform.scale(a, (12, 12))
        b = pygame.transform.scale(b, (12, 12))
    return [a, b]


def quest_items():
    import gfx
    out = {}
    hatch = pygame.transform.scale(gfx.OCTO['cit_hatch']['down'][0], (10, 10))
    out['q_hatch'] = hatch
    s = pygame.Surface((10, 10), pygame.SRCALPHA)        # a sea pepper
    pygame.draw.ellipse(s, (120, 10, 20), (1, 2, 8, 8))
    pygame.draw.ellipse(s, (230, 50, 50), (2, 3, 6, 6))
    s.set_at((3, 4), (255, 170, 170))
    pygame.draw.line(s, (40, 140, 50), (5, 3), (6, 0), 2)
    out['q_pepper'] = s
    s = pygame.Surface((10, 10), pygame.SRCALPHA)        # a glowing coral seed
    pygame.draw.circle(s, (120, 40, 90), (5, 5), 4)
    pygame.draw.circle(s, (255, 150, 200), (5, 5), 3)
    pygame.draw.circle(s, (255, 240, 250), (4, 4), 1)
    out['q_seed'] = s
    s = pygame.Surface((10, 10), pygame.SRCALPHA)        # a glass marble
    pygame.draw.circle(s, (40, 90, 140), (5, 5), 4)
    pygame.draw.circle(s, (120, 200, 255), (5, 5), 3)
    pygame.draw.line(s, (255, 120, 160), (3, 6), (7, 4))
    s.set_at((4, 3), (255, 255, 255))
    out['q_marble'] = s
    s = pygame.Surface((10, 10), pygame.SRCALPHA)        # a shiny scallop shell
    pygame.draw.polygon(s, (170, 110, 60), [(5, 9), (0, 4), (2, 1), (8, 1), (9, 4)])
    pygame.draw.polygon(s, (255, 200, 150), [(5, 8), (1, 4), (3, 2), (7, 2), (8, 4)])
    for x in (3, 5, 7):
        pygame.draw.line(s, (220, 150, 100), (5, 8), (x, 2))
    s.set_at((4, 3), (255, 255, 255))
    out['q_shell'] = s
    return out
