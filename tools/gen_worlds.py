"""Build the four worlds: the (wider) Sea, the (much bigger) Sky, the Surface and the Underdeep.

    .venv/bin/python tools/gen_worlds.py

Reads the hand-made map rows of octo/base_level.py (the original sea, trial rooms and sky islands)
and writes:
  octo/level_data.py   every map row (240 wide): sea, trial rooms, sky, surface, underdeep
  octo/worlds_data.py  the new regions, themes, music, trials, guardians, enemies, items and passages
Everything comes from fixed seeds, so running it again gives the same worlds.
"""
import math
import os
import random
import sys
from collections import deque

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'octo'))
from base_level import BASE_ROWS  # noqa: E402

W = 240
SEA = (0, 0, 239, 79)
SKY = (0, 153, 159, 212)
LAND = (0, 214, 199, 283)
UNDER = (0, 285, 199, 354)
OLD_SKY = (0, 92, 59, 127)
SKY_SHIFT = SKY[1] - OLD_SKY[1]          # old sky rows move down by this much
H = UNDER[3] + 1
FLOOR = set('.,=d')
WALKABLE = FLOOR | set('KAD')            # what the generator treats as passable

rnd = random.Random(20261126)
grid = [list(r + '#' * (W - len(r))) for r in BASE_ROWS]
while len(grid) < H:
    grid.append(['#'] * W)

# ------------------------------------------------------------------ move the old sky into the big sky
old = [grid[y][OLD_SKY[0]:OLD_SKY[2] + 1] for y in range(OLD_SKY[1], OLD_SKY[3] + 1)]
for y in range(OLD_SKY[1], OLD_SKY[3] + 1):
    for x in range(OLD_SKY[0], OLD_SKY[2] + 1):
        grid[y][x] = '#'
for y in range(SKY[1], SKY[3] + 1):
    for x in range(SKY[0], SKY[2] + 1):
        grid[y][x] = 'v'
for j, row in enumerate(old):
    for i, ch in enumerate(row):
        grid[SKY[1] + j][i] = ch


# ------------------------------------------------------------------ helpers
def inside(x, y, r, pad=0):
    return r[0] + pad <= x <= r[2] - pad and r[1] + pad <= y <= r[3] - pad


def fill(r, ch):
    for y in range(r[1], r[3] + 1):
        for x in range(r[0], r[2] + 1):
            grid[y][x] = ch


def blob(cx, cy, rad, ch, r, only=None):
    for y in range(cy - rad, cy + rad + 1):
        for x in range(cx - rad, cx + rad + 1):
            if inside(x, y, r, 1) and (x - cx) ** 2 + (y - cy) ** 2 <= rad * rad * rnd.uniform(0.55, 1.0):
                if only is None or grid[y][x] in only:
                    grid[y][x] = ch


def scatter(r, n, ch, rad=(1, 2), only=None):
    for _ in range(n):
        blob(rnd.randint(r[0] + 2, r[2] - 2), rnd.randint(r[1] + 2, r[3] - 2), rnd.randint(*rad), ch, r, only)


def components(r, ok):
    seen, comps = set(), []
    for y in range(r[1], r[3] + 1):
        for x in range(r[0], r[2] + 1):
            if (x, y) in seen or grid[y][x] not in ok:
                continue
            comp, q = [], deque([(x, y)])
            seen.add((x, y))
            while q:
                cx, cy = q.popleft()
                comp.append((cx, cy))
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if inside(nx, ny, r) and (nx, ny) not in seen and grid[ny][nx] in ok:
                        seen.add((nx, ny))
                        q.append((nx, ny))
            comps.append(comp)
    return comps


def connect(r, ok=WALKABLE, carve='.'):
    """Join every walkable pocket of a region to the biggest one by carving a corridor."""
    while True:
        comps = sorted(components(r, ok), key=len, reverse=True)
        if len(comps) <= 1:
            return
        main = set(comps[0])
        for comp in comps[1:]:
            if len(comp) < 4:
                for x, y in comp:
                    grid[y][x] = '#' if carve == '.' else 'v'
                continue
            a = min(comp, key=lambda p: min(abs(p[0] - q[0]) + abs(p[1] - q[1]) for q in rnd.sample(list(main), min(60, len(main)))))
            b = min(main, key=lambda q: abs(a[0] - q[0]) + abs(a[1] - q[1]))
            x, y = a
            while (x, y) != b:
                if x != b[0] and (y == b[1] or rnd.random() < 0.5):
                    x += 1 if b[0] > x else -1
                else:
                    y += 1 if b[1] > y else -1
                if grid[y][x] not in ok:
                    grid[y][x] = carve
            break


def open_spot(r, used, gap=5, need=1, free='.,d', avoid_edges=3):
    """A random tile with open ground around it (and below it), far from everything in `used`."""
    cands = []
    for y in range(r[1] + avoid_edges, r[3] - avoid_edges):
        for x in range(r[0] + avoid_edges, r[2] - avoid_edges):
            if all(grid[y + dy][x + dx] in free for dy in range(-need, need + 2) for dx in range(-need, need + 1)):
                cands.append((x, y))
    rnd.shuffle(cands)
    cands.sort(key=lambda p: -min([math.hypot(p[0] - a, p[1] - b) for a, b in used] or [99]))
    for p in cands[:40]:
        if not used or min(math.hypot(p[0] - a, p[1] - b) for a, b in used) >= gap:
            used.append(p)
            return p
    p = cands[0]
    used.append(p)
    return p


def door(x0, y0, x1, y1, ch='.'):
    for y in range(min(y0, y1), max(y0, y1) + 1):
        for x in range(min(x0, x1), max(x0, x1) + 1):
            grid[y][x] = ch


# ------------------------------------------------------------------ region specs
# name, world, rect, theme, music, tier, dark, terrain recipe, creature, guardian
REGIONS = [
    # the eastern sea
    ('GLASS REEF', 'sea', (160, 1, 238, 25), 'glass', 4, False, dict(rock=0.008, decor=0.03, grass=0.01, pool=0.0), 'glassfish', 'glassking'),
    ('SIREN SHOALS', 'sea', (160, 27, 238, 52), 'siren', 4, False, dict(rock=0.01, decor=0.025, grass=0.012, kelp=0.004), 'seahorse', 'sirenqueen'),
    ('WHALE FALL', 'sea', (160, 54, 238, 78), 'whale', 5, True, dict(rock=0.014, decor=0.02, pool=0.003), 'hagfish', 'gulper'),
    # the sky (the old Sky Islands sit in the top-left corner)
    ('THUNDERHEADS', 'sky', (60, 153, 159, 181), 'thunder', 3, False, None, 'sparkbird', 'thunderhawk'),
    ('RAINBOW REACH', 'sky', (60, 182, 159, 212), 'rainbow', 3, False, None, 'prism', 'prismlord'),
    ('STARFALL PEAKS', 'sky', (0, 189, 59, 212), 'starfall', 4, False, None, 'starling', 'comet'),
    # the surface
    ('TIDE MEADOWS', 'land', (1, 215, 68, 262), 'meadow', 3, False, dict(rock=0.008, decor=0.03, grass=0.03, pool=0.003, kelp=0.006), 'beetle', 'stagbeetle'),
    ('PALM JUNGLE', 'land', (70, 215, 138, 262), 'jungle', 4, False, dict(rock=0.006, decor=0.06, grass=0.03, pool=0.003, kelp=0.012), 'monkey', 'kingkong'),
    ('DUNE DESERT', 'land', (140, 215, 198, 238), 'desert', 4, False, dict(rock=0.01, decor=0.02, grass=0.004, pool=0.002), 'scorpion', 'deathstalker'),
    ('VOLCANO RIDGE', 'land', (140, 240, 198, 262), 'volcano', 5, False, dict(rock=0.02, decor=0.02, lava=0.006), 'magmite', 'lavaboss'),
    ('SUNNY BEACH', 'land', (1, 264, 198, 282), 'beach', 3, False, dict(rock=0.006, decor=0.02, grass=0.006, pool=0.004), 'sandhopper', 'hopperking'),
    # the underdeep
    ('CRYSTAL CAVES', 'under', (1, 286, 78, 318), 'crystal', 5, False, dict(rock=0.03, decor=0.03, pool=0.004, kelp=0.004), 'crystalbug', 'geode'),
    ('FUNGUS GROTTO', 'under', (80, 286, 198, 318), 'fungus', 5, False, dict(rock=0.02, decor=0.04, pool=0.004, kelp=0.012), 'sporeling', 'mushking'),
    ('BONE TRENCH', 'under', (1, 320, 78, 353), 'bone', 6, True, dict(rock=0.025, decor=0.02, pool=0.006), 'skullfish', 'bonelord'),
    ('ANCIENT RUINS', 'under', (80, 320, 138, 353), 'ruins', 6, True, dict(rock=0.02, decor=0.03), 'golem', 'colossus'),
    ('MAGMA CORE', 'under', (140, 320, 198, 353), 'magma', 6, False, dict(rock=0.02, decor=0.015, lava=0.01), 'salamander', 'pyrosaur'),
]
OTHERS = {'sea': ['crab', 'puffer', 'jelly', 'urchin'], 'sky': ['gull', 'cloud'],
          'land': ['crab', 'urchin', 'puffer'], 'under': ['icecrab', 'lavacrab', 'jelly', 'urchin']}


def terrain(r, recipe):
    fill(r, '.')
    area = (r[2] - r[0] + 1) * (r[3] - r[1] + 1)
    scatter(r, int(area * recipe.get('grass', 0.01)), ',', (1, 3))
    scatter(r, int(area * recipe.get('rock', 0.01)), '#', (1, 2))
    scatter(r, int(area * recipe.get('pool', 0)), 'v', (2, 3), only='.,')
    scatter(r, int(area * recipe.get('kelp', 0)), 'K', (1, 2), only='.,')
    scatter(r, int(area * recipe.get('lava', 0)), 'l', (1, 2), only='.,')
    for _ in range(int(area * recipe.get('decor', 0.02))):
        x, y = rnd.randint(r[0] + 1, r[2] - 1), rnd.randint(r[1] + 1, r[3] - 1)
        if grid[y][x] in '.,':
            grid[y][x] = 'C'
    connect(r)


for name, wld, r, theme, tier, dark, recipe, critter, guard in REGIONS:
    if recipe:
        terrain(r, recipe)

# borders and openings between neighbouring regions -------------------------
# sea: the east is reached from the Frozen Shelf, the Ember Vents and the Sunken City
for y in (10, 39, 66):
    for yy in (y, y + 1):
        x = 159
        door(x, yy, x, yy)
        x -= 1
        while grid[yy][x] not in FLOOR and x > 100:
            grid[yy][x] = '.'
            x -= 1
        x = 160
        while grid[yy][x] not in FLOOR and x < 200:
            grid[yy][x] = '.'
            x += 1
door(198, 26, 200, 26)
door(198, 53, 200, 53)
door(214, 26, 215, 26)
# land: the beach links everything; the volcano is ringed by lava
door(30, 263, 32, 263)
door(100, 263, 102, 263)
door(69, 236, 69, 238)
door(139, 225, 139, 227)
door(150, 239, 152, 239, 'l')
door(170, 263, 172, 263, 'l')
for x in range(141, 198):                 # a lava moat inside the volcano's edge (Chilly or Magmy only)
    for y in (241, 242):
        if grid[y][x] in '.,':
            grid[y][x] = 'l'
for y in range(241, 262):
    if grid[y][141] in '.,':
        grid[y][141] = 'l'
# underdeep
door(79, 300, 79, 302)
door(30, 319, 32, 319)
door(100, 319, 102, 319)
door(139, 335, 139, 337)
door(170, 319, 172, 319, 'l')
for x in range(141, 198):
    for y in (321, 322):
        if grid[y][x] in '.,':
            grid[y][x] = 'l'

# ------------------------------------------------------------------ the big sky: islands and bridges
islands = []
for name, wld, r, theme, tier, dark, recipe, critter, guard in REGIONS:
    if wld != 'sky':
        continue
    n = (r[2] - r[0]) * (r[3] - r[1]) // 220
    for _ in range(n):
        for _try in range(40):
            cx, cy, rad = rnd.randint(r[0] + 6, r[2] - 6), rnd.randint(r[1] + 5, r[3] - 5), rnd.randint(3, 6)
            if all(math.hypot(cx - a, cy - b) > rad + rr + 3 for a, b, rr in islands):
                break
        islands.append((cx, cy, rad))
        blob(cx, cy, rad, '.', r)
        blob(cx, cy, rad - 1, '.', r)
        for _ in range(rad):
            x, y = cx + rnd.randint(-rad + 1, rad - 1), cy + rnd.randint(-rad + 1, rad - 1)
            if grid[y][x] == '.':
                grid[y][x] = rnd.choice(',,,C#')
# the old sky islands join in: one anchor per pocket of the old sky
sky_r = SKY
old_r = (0, SKY[1], 59, SKY[1] + (OLD_SKY[3] - OLD_SKY[1]))
for comp in components(old_r, FLOOR):
    if len(comp) > 8:
        cx, cy = comp[len(comp) // 2]
        islands.append((cx, cy, 0))


def bridge(a, b):
    (x, y), (tx, ty) = a, b
    horizontal_first = rnd.random() < 0.5
    while (x, y) != (tx, ty):
        if (horizontal_first and x != tx) or y == ty:
            x += 1 if tx > x else -1
        else:
            y += 1 if ty > y else -1
        if grid[y][x] == 'v':
            grid[y][x] = '='


# minimum spanning tree over island centres, plus a few extra loops
pts = [(x, y) for x, y, _ in islands]
linked, todo = {0}, set(range(1, len(pts)))
while todo:
    i, j = min(((i, j) for i in linked for j in todo), key=lambda ij: math.dist(pts[ij[0]], pts[ij[1]]))
    bridge(pts[i], pts[j])
    linked.add(j)
    todo.remove(j)
for _ in range(len(pts) // 4):
    i, j = rnd.sample(range(len(pts)), 2)
    if math.dist(pts[i], pts[j]) < 30:
        bridge(pts[i], pts[j])
connect(sky_r, ok=FLOOR | set('KAYD'), carve='=')

# ------------------------------------------------------------------ places: guardians, portals, passages
used = {'sea': [], 'sky': [], 'land': [], 'under': []}
REGION_RECT = {name: r for name, wld, r, *_ in REGIONS}


def spot_in(name, wld, gap=6, need=1):
    return open_spot(REGION_RECT[name], used[wld], gap=gap, need=need)


def fixed_spot(r, used_list, need=1):
    return open_spot(r, used_list, gap=6, need=need)


# passages between worlds: (sea or land tile, other world tile, kind)
SEA_SPOTS = {'THE LAGOON': (1, 23, 23, 54), 'CORAL REEF': (24, 56, 60, 78), 'THE ABYSS': (72, 23, 94, 54),
             'SHIP GRAVEYARD': (1, 56, 94, 78)}
sea_used = []
passages = []


def sea_spot(region_rect):
    return open_spot(region_rect, sea_used, gap=8, need=1)


# shore steps up to the Surface: two from the old sea, one from the Siren Shoals
for src, dst in ((SEA_SPOTS['THE LAGOON'], 'SUNNY BEACH'), (SEA_SPOTS['CORAL REEF'], 'SUNNY BEACH'),
                 (REGION_RECT['SIREN SHOALS'], 'SUNNY BEACH')):
    a = sea_spot(src)
    b = spot_in(dst, 'land', gap=30)
    grid[a[1]][a[0]] = 'A'
    grid[b[1]][b[0]] = 'A'
    passages.append((a, b, 'shore'))
# sinkholes down to the Underdeep
for src, dst in ((SEA_SPOTS['THE ABYSS'], 'CRYSTAL CAVES'), (SEA_SPOTS['SHIP GRAVEYARD'], 'BONE TRENCH'),
                 (REGION_RECT['WHALE FALL'], 'ANCIENT RUINS')):
    a = sea_spot(src)
    b = spot_in(dst, 'under', gap=10)
    grid[a[1]][a[0]] = 'D'
    grid[b[1]][b[0]] = 'D'
    passages.append((a, b, 'sinkhole'))
# a lava tube from the volcano down to the magma core
a = spot_in('VOLCANO RIDGE', 'land')
b = spot_in('MAGMA CORE', 'under')
grid[a[1]][a[0]] = 'D'
grid[b[1]][b[0]] = 'D'
passages.append((a, b, 'sinkhole'))
# new geysers up to the big sky
geysers = []
for src, dst in ((REGION_RECT['GLASS REEF'], 'THUNDERHEADS'), (REGION_RECT['SIREN SHOALS'], 'RAINBOW REACH'),
                 (SEA_SPOTS['CORAL REEF'], 'STARFALL PEAKS')):
    a = sea_spot(src)
    b = spot_in(dst, 'sky', gap=8)
    grid[a[1]][a[0]] = 'Y'
    grid[b[1]][b[0]] = 'Y'
    geysers.append((a, b))

guardians = []
for name, wld, r, theme, tier, dark, recipe, critter, guard in REGIONS:
    x, y = spot_in(name, wld, gap=10, need=2)
    guardians.append((guard, x, y))

# ------------------------------------------------------------------ trial rooms
LAYOUTS = {
    'pillars': ["...W........W...", "................", "......W..W......", "................",
                "......W..W......", "................", "...W........W..."],
    'lanes': ["..WWWWW..WWWWW..", "................", "................", "................",
              "................", "................", "..WWWWW..WWWWW.."],
    'pits': ["..vv........vv..", "..vv........vv..", "................", "................",
             "................", "..vv........vv..", "..vv........vv.."],
    'cross': [".......WW.......", ".......WW.......", "................", "..WW........WW..",
              "................", ".......WW.......", ".......WW......."],
    'maze': ["..W..W....W..W..", "..W..W....W..W..", "................", "...WW......WW...",
             "................", "..W..W....W..W..", "..W..W....W..W.."],
    'ring': ["....vvvvvvvv....", "...v........v...", "................", "................",
             "................", "...v........v...", "....vvvvvvvv...."],
}


def carve_room(x0, y0, layout):
    lay = LAYOUTS[layout]
    for j in range(11):
        for i in range(16):
            if i in (0, 15) or j in (0, 10):
                ch = 'W'
            elif 2 <= j <= 8:
                ch = lay[j - 2][i]
                ch = '=' if ch == '.' else ch
            else:
                ch = '='
            grid[y0 + j][x0 + i] = ch


SLOTS = [(x, y) for y in (80, 92, 104, 116, 129, 141) for x in (160, 177, 194, 211)] + \
        [(x, y) for y in (92, 104, 116) for x in (0, 17, 34)]
PLAN = [  # region, word, kind, twist
    ('GLASS REEF', 'SHARDS', 'waves', None), ('GLASS REEF', 'MIRAGES', 'race', 'current'),
    ('SIREN SHOALS', 'SONGS', 'chase', None), ('SIREN SHOALS', 'ECHO', 'duel', 'sirenqueen'),
    ('WHALE FALL', 'BLUBBER', 'survive', 'dark'), ('WHALE FALL', 'MARROW', 'defend', None),
    ('THUNDERHEADS', 'BOLTS', 'waves', None), ('THUNDERHEADS', 'GUSTS II', 'race', 'current'),
    ('THUNDERHEADS', 'STATIC', 'duel', 'thunderhawk'), ('RAINBOW REACH', 'COLOURS', 'collect', None),
    ('RAINBOW REACH', 'RAINDROPS', 'chase', None), ('RAINBOW REACH', 'HALOS', 'survive', None),
    ('STARFALL PEAKS', 'COMETS', 'duel', 'comet'), ('STARFALL PEAKS', 'NIGHT', 'collect', 'dark'),
    ('STARFALL PEAKS', 'ORBITS', 'defend', None),
    ('TIDE MEADOWS', 'MEADOWS', 'collect', None), ('TIDE MEADOWS', 'BEETLES', 'waves', None),
    ('PALM JUNGLE', 'VINES', 'chase', 'dark'), ('PALM JUNGLE', 'COCONUTS', 'duel', 'kingkong'),
    ('DUNE DESERT', 'DUNES', 'race', 'current'), ('DUNE DESERT', 'MIRRORS II', 'survive', None),
    ('VOLCANO RIDGE', 'ASH', 'waves', None), ('SUNNY BEACH', 'SANDCASTLES', 'defend', None),
    ('SUNNY BEACH', 'SURF', 'race', None),
    ('CRYSTAL CAVES', 'PRISMS', 'collect', 'dark'), ('CRYSTAL CAVES', 'GEMS', 'waves', None),
    ('FUNGUS GROTTO', 'SPORES', 'survive', None), ('FUNGUS GROTTO', 'TOADSTOOLS', 'duel', 'mushking'),
    ('BONE TRENCH', 'SKULLS', 'chase', 'dark'), ('BONE TRENCH', 'FOSSILS', 'defend', None),
    ('ANCIENT RUINS', 'RELICS', 'race', None), ('ANCIENT RUINS', 'GOLEMS', 'duel', 'colossus'),
    ('MAGMA CORE', 'FURNACE', 'waves', None),
]
assert len(PLAN) <= len(SLOTS), (len(PLAN), len(SLOTS))
COLS = [(255, 150, 120), (140, 210, 255), (255, 110, 110), (120, 200, 140), (150, 140, 230), (255, 170, 220),
        (230, 120, 170), (150, 230, 240), (240, 240, 160), (100, 110, 200), (170, 120, 255), (190, 160, 120),
        (160, 200, 230), (200, 240, 255), (220, 230, 255), (255, 120, 60), (200, 170, 255), (255, 255, 140)]
REGION_OF = {name: (wld, r, critter) for name, wld, r, theme, tier, dark, recipe, critter, guard in REGIONS}
trials = {}
for i, (region, word, kind, twist) in enumerate(PLAN):
    x0, y0 = SLOTS[i]
    wld, r, critter = REGION_OF[region]
    pool = [critter, critter] + OTHERS[wld]
    layout = 'pillars' if kind in ('survive', 'defend', 'duel') else list(LAYOUTS)[i % len(LAYOUTS)]
    carve_room(x0, y0, layout)
    fl = [(x, y) for y in range(1, 10) for x in range(1, 15) if grid[y0 + y][x0 + x] == '=']
    far = [p for p in fl if abs(p[0] - 7.5) + abs(p[1] - 5) >= 5]

    def near(x, y, half=False):
        bx, by = min(fl, key=lambda p: abs(p[0] - x) + abs(p[1] - y))
        return (bx + 0.5 if half and grid[y0 + by][x0 + bx + 1] == '=' else bx, by)
    portal = spot_in(region, wld, gap=6)
    t = {'title': 'TRIAL OF ' + word, 'color': COLS[i % len(COLS)], 'kind': kind, 'room': (x0, y0, x0 + 15, y0 + 10),
         'entry': (7.5, 5), 'portal': portal}
    if twist == 'dark':
        t['dark'] = True
    if twist == 'current':
        t['current'] = rnd.choice([(0.55, 0.0), (-0.55, 0.0), (0.0, 0.45), (0.3, -0.35)])
    if kind == 'waves':
        n = 7 + i // 6
        t['goal'] = "DEFEAT THREE WAVES OF ENEMIES!"
        t['waves'] = [[rnd.choice(pool) for _ in range(n + w * 2)] for w in range(3)]
        t['spots'] = rnd.sample(far, 10)
    elif kind == 'collect':
        n = 11 + i // 8
        t['time'] = 24 + n
        t['goal'] = f"GRAB ALL {n} ORBS IN {t['time']} SECONDS!" + (" IN THE DARK!" if t.get('dark') else "")
        t['orbs'] = rnd.sample([p for p in fl if p != (7, 5)], n)
        t['guards'] = [(rnd.choice(pool), *p) for p in rnd.sample(far, 4)]
    elif kind == 'survive':
        t['time'] = 22
        t['entry'] = near(7.5, 8, True)
        t['eyes'] = [(7.5, 5), (1.5, 1.5), (13.5, 1.5), (1.5, 8.5), (13.5, 8.5)]
        t['goal'] = "SURVIVE 22 SECONDS" + ("... IN THE DARK!" if t.get('dark') else "!")
    elif kind == 'duel':
        t['boss'] = twist
        t['entry'] = near(7.5, 8, True)
        t['boss_at'] = near(7.5, 2, True)
        t['goal'] = "A GUARDIAN BLOCKS THE WAY. DEFEAT IT!"
    elif kind == 'chase':
        t['time'] = 35
        t['thief_at'] = near(13, 2)
        t['guards'] = [(rnd.choice(pool), *near(2, 8))]
        t['goal'] = "A GOLDEN THIEF STOLE A PEARL! TAG IT 3 TIMES IN 35 SECONDS!" + \
            (" (IT'S DARK IN HERE...)" if t.get('dark') else "")
    elif kind == 'defend':
        t['clam_at'] = near(7.5, 5, True)
        t['entry'] = near(7.5, 7, True)
        t['time'] = 30
        t['every'] = 65
        t['raiders'] = pool
        t['spots'] = [p for p in fl if p[0] in (1, 14) or p[1] in (1, 9)]
        t['goal'] = "PROTECT THE GIANT CLAM FOR 30 SECONDS!"
    elif kind == 'race':
        t['time'] = 20
        t['entry'] = near(1.5, 5, True)
        t['goal'] = near(14, 5)
        t['sentries'] = [(c, rnd.choice([y for (x, y) in fl if x == c])) for c in (4, 6, 9, 11, 13)
                         if any(x == c for x, _ in fl)]
        t['sentry_speed'] = 1.4
        t['goal_text'] = "REACH THE FLAG IN 20 SECONDS - DODGE THE SPIKED SENTRIES!"
    trials[word.lower().replace(' ', '')] = t

# ------------------------------------------------------------------ enemies and treasure
enemies, items = [], []
for name, wld, r, theme, tier, dark, recipe, critter, guard in REGIONS:
    area = (r[2] - r[0]) * (r[3] - r[1])
    n = max(8, min(18, area // 110))
    for _ in range(n):
        kind = critter if rnd.random() < 0.6 else rnd.choice(OTHERS[wld])
        x, y = open_spot(r, used[wld], gap=3, need=0)
        enemies.append((kind, x, y))
    for kind in ('bluepearl', 'bluepearl', 'bluepearl', 'shrimp', 'shrimp'):
        x, y = open_spot(r, used[wld], gap=3, need=0)
        items.append((kind, x, y))
    if name in ('GLASS REEF', 'THUNDERHEADS', 'DUNE DESERT', 'CRYSTAL CAVES', 'ANCIENT RUINS', 'STARFALL PEAKS'):
        x, y = open_spot(r, used[wld], gap=4, need=0)
        items.append(('container', x, y))

# ------------------------------------------------------------------ write
with open(os.path.join(ROOT, 'octo', 'level_data.py'), 'w') as f:
    f.write('"""Generated by tools/gen_worlds.py -- every map row (sea, trial rooms, sky, surface, underdeep)."""\n')
    f.write('LEVEL_ROWS = [\n')
    for row in grid:
        f.write(f'    "{"".join(row)}",\n')
    f.write(']\n')

with open(os.path.join(ROOT, 'octo', 'worlds_data.py'), 'w') as f:
    f.write('"""Generated by tools/gen_worlds.py -- the regions and contents of the new parts of the worlds."""\n')
    f.write(f'WORLD_RECTS = {{"sea": {SEA!r}, "sky": {SKY!r}, "land": {LAND!r}, "under": {UNDER!r}}}\n')
    f.write(f'OLD_SKY = {OLD_SKY!r}\nSKY_SHIFT = {SKY_SHIFT}\n')
    f.write('# (name, world, rect, theme, tier, dark, creature, guardian)\nNEW_REGIONS = [\n')
    for name, wld, r, theme, tier, dark, recipe, critter, guard in REGIONS:
        f.write(f'    ({name!r}, {wld!r}, {r!r}, {theme!r}, {tier}, {dark}, {critter!r}, {guard!r}),\n')
    f.write(']\n')
    f.write('NEW_GUARDIANS = ' + repr(guardians) + '\n')
    f.write('NEW_GEYSERS = ' + repr(geysers) + '\n')
    f.write('PASSAGES = ' + repr(passages) + '\n')
    f.write('NEW_TRIALS = {\n' + ''.join(f'    {k!r}: {v!r},\n' for k, v in trials.items()) + '}\n')
    f.write('NEW_ENEMIES = ' + repr(enemies) + '\n')
    f.write('NEW_ITEMS = ' + repr(items) + '\n')
print("worlds written:", len(grid), "rows x", W, "|", len(trials), "new trials |", len(enemies), "enemies |",
      len(guardians), "guardians |", len(passages), "passages")
