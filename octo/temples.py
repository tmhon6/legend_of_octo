"""The six deep temples: multi-room dungeons that sit below the trial rooms.

Each temple is a grid of one-screen rooms (16x11 tiles, like the trial rooms), built here
from a fixed seed so every player gets the same layout. The builder makes sure every
temple can be finished:
  * the rooms form a tree grown out from the entrance; the boss waits in the deepest room
  * locked doors sit on the main path, and each one's key lies in a room you can reach
    before that door
  * one door on the main path is a "gate" that only a certain form (or bombs) gets through
  * secret cracked walls only ever link rooms you could already reach, so they never skip
    a locked door
world.py stitches the rooms onto the bottom of the map and adds their arenas, enemies
and items. The boss of each temple guards a Tide Bell.
"""
import random

RW, RH = 16, 11            # one room = one screen
GW, GH = 5, 3              # room grid of a temple
TEMPLE_W, TEMPLE_H = GW * RW, GH * RH
ENTRY_ROOM = (2, GH - 1)   # bottom middle

# id, banner title, overworld door tile, gate tile on the main path, enemy pool, boss, size, locks, tier
SPECS = [
    dict(id='snarl', title='SNARLWOOD TEMPLE', door=(18, 1), gate='K', rooms=9, locks=2, tier=1, seed=11,
         pool=['jelly', 'crab', 'puffer'], boss='tanglemaw', color=(90, 200, 110)),
    dict(id='bloom', title='BLOOM TEMPLE', door=(74, 12), gate='R', rooms=10, locks=2, tier=2, seed=22,
         pool=['urchin', 'puffer', 'crab'], boss='bramble', color=(255, 130, 190)),
    dict(id='tidepool', title='TIDEPOOL TEMPLE', door=(17, 26), gate=None, rooms=11, locks=3, tier=2, seed=33,
         pool=['puffer', 'crab', 'jelly', 'urchin'], boss='bellows', color=(140, 220, 255)),
    dict(id='gloam', title='GLOAM TEMPLE', door=(75, 24), gate='G', rooms=12, locks=2, tier=3, seed=44,
         pool=['jelly', 'puffer', 'urchin', 'jelly'], boss='deepeye', color=(190, 110, 255), dark=True),
    dict(id='rime', title='RIME TEMPLE', door=(139, 2), gate='I', rooms=13, locks=3, tier=4, seed=55,
         pool=['icecrab', 'icecrab', 'urchin', 'jelly', 'puffer'], boss='hoarclaw', color=(200, 235, 255)),
    dict(id='cinder', title='CINDER TEMPLE', door=(118, 50), gate='l', rooms=14, locks=3, tier=5, seed=66,
         pool=['lavacrab', 'lavacrab', 'puffer', 'urchin', 'crab'], boss='slagjaw', color=(255, 120, 60)),
]
GATE_HINT = {
    'K': "THICK KELP BLOCKS A DOORWAY HERE. GRUMPY OCTO'S SLAP CAN CUT IT.",
    'R': "A CRACKED WALL... A BUBBLE BOMB COULD BLAST IT OPEN.",
    'G': "A GHOSTLY WALL. ONLY SPOOKY OCTO CAN SLIP THROUGH.",
    'I': "A WALL OF ICE. ZAPPY OCTO'S SHOCK WOULD SHATTER IT.",
    'l': "A RIVER OF LAVA. CHILLY OCTO'S ICE COULD COOL IT.",
}

LAYOUTS = {
    'pillars': ["................",
                "................",
                "...W........W...",
                "................",
                "......W..W......",
                "................",
                "......W..W......",
                "................",
                "...W........W...",
                "................",
                "................"],
    'lanes':   ["................",
                "................",
                "..WWWWW..WWWWW..",
                "................",
                "................",
                "................",
                "................",
                "................",
                "..WWWWW..WWWWW..",
                "................",
                "................"],
    'pits':    ["................",
                "................",
                "..vv........vv..",
                "..vv........vv..",
                "................",
                "................",
                "................",
                "..vv........vv..",
                "..vv........vv..",
                "................",
                "................"],
    'cross':   ["................",
                "................",
                ".......WW.......",
                ".......WW.......",
                "................",
                "..WW........WW..",
                "................",
                ".......WW.......",
                ".......WW.......",
                "................",
                "................"],
    'maze':    ["................",
                "................",
                "..W..W....W..W..",
                "..W..W....W..W..",
                "................",
                "...WW......WW...",
                "................",
                "..W..W....W..W..",
                "..W..W....W..W..",
                "................",
                "................"],
    'ring':    ["................",
                "................",
                "....vvvvvvvv....",
                "...v........v...",
                "................",
                "................",
                "................",
                "...v........v...",
                "....vvvvvvvv....",
                "................",
                "................"],
    'statues': ["................",
                "................",
                "..S..........S..",
                "................",
                "................",
                "................",
                "................",
                "................",
                "..S..........S..",
                "................",
                "................"],
    'moat':    ["................",
                "................",
                "...vvvv..vvvv...",
                "...v........v...",
                "...v...SS...v...",
                "................",
                "...v...SS...v...",
                "...v........v...",
                "...vvvv..vvvv...",
                "................",
                "................"],
}
PLAIN = 'statues'
DIRS = {'n': (0, -1), 's': (0, 1), 'w': (-1, 0), 'e': (1, 0)}
DOOR_CELLS = {'n': [(7, 0), (8, 0)], 's': [(7, 10), (8, 10)], 'w': [(0, 5)], 'e': [(15, 5)]}
ITEM_SPOT = (7.5, 5)


def _dir(a, b):
    for d, (dx, dy) in DIRS.items():
        if (a[0] + dx, a[1] + dy) == b:
            return d
    raise ValueError((a, b))


def _plan(spec, rnd):
    """Room tree, main path, locks, gate, keys and treasure for one temple (or None to retry)."""
    entry = ENTRY_ROOM
    parent = {entry: None}
    order = [entry]
    while len(order) < spec['rooms']:
        opts = [(r, (r[0] + dx, r[1] + dy)) for r in order for dx, dy in DIRS.values()
                if 0 <= r[0] + dx < GW and 0 <= r[1] + dy < GH and (r[0] + dx, r[1] + dy) not in parent]
        r, nb = rnd.choice(opts)
        parent[nb] = r
        order.append(nb)

    def chain(r):
        out = []
        while r is not None:
            out.append(r)
            r = parent[r]
        return out[::-1]
    boss = max((r for r in order if r != entry), key=lambda r: (len(chain(r)), rnd.random()))
    path = chain(boss)
    need = spec['locks'] + (1 if spec['gate'] else 0) + 2
    if len(path) < need + 1:
        return None
    edges = {}
    for r in order:
        if parent[r] is not None:
            edges[frozenset((r, parent[r]))] = 'open'
    # barriers on the main path: the boss door is always locked; the others are spread out
    path_edges = [frozenset((path[i], path[i + 1])) for i in range(len(path) - 1)]
    inner = list(range(1, len(path_edges) - 1))
    rnd.shuffle(inner)
    picks = inner[:spec['locks'] - 1 + (1 if spec['gate'] else 0)]
    if len(picks) < spec['locks'] - 1 + (1 if spec['gate'] else 0):
        return None
    lock_idx = sorted(picks[:spec['locks'] - 1]) + [len(path_edges) - 1]
    gate_idx = picks[spec['locks'] - 1] if spec['gate'] else None
    for i in lock_idx:
        edges[path_edges[i]] = 'lock'
    if gate_idx is not None:
        edges[path_edges[gate_idx]] = 'gate'
    barrier_at = sorted(lock_idx + ([gate_idx] if gate_idx is not None else []))

    def zone(r):
        """How many main-path barriers lie between the entrance and this room."""
        c = chain(r)
        k = 0
        for a, b in zip(c, c[1:]):
            if edges[frozenset((a, b))] in ('lock', 'gate'):
                k += 1
        return k
    zones = {r: zone(r) for r in order}
    # a key for every lock, each in a room reachable before that lock
    on_path = set(path)
    keys = {}
    for n, i in enumerate(lock_idx):
        z_need = barrier_at.index(i)          # rooms in zones < this barrier's ordinal+1
        cands = [r for r in order if zones[r] <= z_need and r not in keys and r not in (entry, boss)]
        side = [r for r in cands if r not in on_path]
        pool = [r for r in side if zones[r] == z_need] or side or [r for r in cands if zones[r] == z_need] or cands
        if not pool:
            return None
        keys[rnd.choice(pool)] = True
    # a heart shell in a side room, behind a cracked wall when it's a dead end
    treasure = None
    side_free = [r for r in order if r not in on_path and r not in keys and r != entry]
    if side_free:
        treasure = rnd.choice(side_free)
        if sum(1 for e in edges if treasure in e) == 1:
            edges[frozenset((treasure, parent[treasure]))] = 'bomb'
    # secret cracked walls between neighbouring rooms of the same zone
    for r in order:
        for d, (dx, dy) in DIRS.items():
            nb = (r[0] + dx, r[1] + dy)
            e = frozenset((r, nb))
            if nb in zones and e not in edges and boss not in e and treasure not in e \
                    and zones[nb] == zones[r] and rnd.random() < 0.22:
                edges[e] = 'bomb'
    return dict(order=order, parent=parent, entry=entry, boss=boss, path=path, edges=edges, keys=keys,
                treasure=treasure, zones=zones)


def _room_ok(grid):
    """Every door cell of the room connects through floor."""
    floor = {(x, y) for y in range(RH) for x in range(RW) if grid[y][x] != 'W' and grid[y][x] not in 'Sv'}
    start = (7, 9)
    seen, todo = {start}, [start]
    while todo:
        x, y = todo.pop()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (nx, ny) in floor and (nx, ny) not in seen:
                seen.add((nx, ny))
                todo.append((nx, ny))
    inner = {(x, y) for (x, y) in floor if 0 < x < RW - 1 and 0 < y < RH - 1}
    return inner <= seen


def build(spec, ox, oy):
    """Carve one temple. Returns (rows, data) where rows is TEMPLE_H strings of TEMPLE_W tiles."""
    rnd = random.Random(spec['seed'])
    plan = None
    while plan is None:
        plan = _plan(spec, rnd)
    rows = [['#'] * TEMPLE_W for _ in range(TEMPLE_H)]
    edges, zones = plan['edges'], plan['zones']
    arenas, enemies, items = {}, [], []
    names = list(LAYOUTS)
    tid = spec['id']
    shut_rooms = set()
    for r in plan['order']:
        if r in (plan['entry'],):
            continue
        if r == plan['boss'] or (r in plan['keys'] and rnd.random() < 0.6) or rnd.random() < 0.25:
            shut_rooms.add(r)
    for r in plan['order']:
        gx, gy = r
        if r == plan['entry']:
            lay = PLAIN
        elif r == plan['boss']:
            lay = 'pillars'
        else:
            lay = rnd.choice(names)
        grid = [['W' if x in (0, RW - 1) or y in (0, RH - 1) else ('=' if LAYOUTS[lay][y][x] == '.'
                 else LAYOUTS[lay][y][x]) for x in range(RW)] for y in range(RH)]
        if not _room_ok(grid):
            grid = [['W' if x in (0, RW - 1) or y in (0, RH - 1) else '=' for x in range(RW)] for y in range(RH)]
        for d, (dx, dy) in DIRS.items():
            e = frozenset((r, (gx + dx, gy + dy)))
            if e not in edges:
                continue
            kind = edges[e]
            ch = {'open': '=', 'lock': 'L', 'bomb': 'R', 'gate': spec['gate']}[kind]
            if kind == 'open' and r in shut_rooms:
                ch = 'X'
            for (cx, cy) in DOOR_CELLS[d]:
                grid[cy][cx] = ch
                # keep the tile just inside every door clear
                ix, iy = cx + (1 if cx == 0 else -1 if cx == RW - 1 else 0), cy + (1 if cy == 0 else -1 if cy == RH - 1 else 0)
                grid[iy][ix] = '='
        if r == plan['entry']:
            for x in range(6, 10):
                grid[9][x] = 'E'                   # stairs back up to the sea
        bx, by = ox + gx * RW, oy + gy * RH
        for y in range(RH):
            for x in range(RW):
                rows[gy * RH + y][gx * RW + x] = grid[y][x]
        floor = [(x, y) for y in range(2, RH - 2) for x in range(2, RW - 2)
                 if grid[y][x] == '=' and abs(x - 7.5) + abs(y - 5) > 2.5]
        # what lives in the room
        tier = spec['tier']
        name = f"{tid}{gx}{gy}"
        if r == plan['boss']:
            enemies.append(('tboss:' + spec['boss'], bx + 7.5, by + 3))
            arenas[name] = {'rect': (bx + 1, by + 1, bx + RW - 2, by + RH - 2), 'reward': ('bell', bx + 7.5, by + 6),
                            'boss': True}
            continue
        if r == plan['entry']:
            continue
        n = rnd.randint(2, 3) + tier // 2 + (1 if r in shut_rooms else 0)
        for (x, y) in rnd.sample(floor, min(n, len(floor))):
            enemies.append((rnd.choice(spec['pool']), bx + x, by + y))
        reward = None
        if r in plan['keys']:
            reward = 'key'
        elif r == plan['treasure']:
            reward = 'container'
        if r in shut_rooms:
            arenas[name] = {'rect': (bx + 1, by + 1, bx + RW - 2, by + RH - 2),
                            'reward': (reward or rnd.choice(('bluepearl', 'bluepearl', 'heart')),
                                       bx + ITEM_SPOT[0], by + ITEM_SPOT[1])}
        elif reward:
            items.append((reward, bx + ITEM_SPOT[0], by + ITEM_SPOT[1]))
        elif rnd.random() < 0.3:
            items.append((rnd.choice(('shrimp', 'bluepearl')), bx + ITEM_SPOT[0], by + ITEM_SPOT[1]))
    ex, ey = plan['entry']
    data = dict(spec, origin=(ox, oy), rect=(ox, oy, ox + TEMPLE_W - 1, oy + TEMPLE_H - 1),
                entry=(ox + ex * RW + 7.5, oy + ey * RH + 7), exit_tiles=[(ox + ex * RW + x, oy + ey * RH + 9) for x in range(6, 10)],
                rooms=set(plan['order']), boss_room=plan['boss'], arenas=arenas, enemies=enemies, items=items,
                edges=plan['edges'])
    return [''.join(r) for r in rows], data


def build_all(width, top):
    """All temples, two side by side per band. Returns (extra rows, {id: data})."""
    bands = (len(SPECS) + 1) // 2
    rows = [['#'] * width for _ in range(bands * TEMPLE_H)]
    out = {}
    for i, spec in enumerate(SPECS):
        ox, oy = (i % 2) * TEMPLE_W, top + (i // 2) * TEMPLE_H
        trows, data = build(spec, ox, oy)
        for y, line in enumerate(trows):
            rows[oy - top + y][ox:ox + TEMPLE_W] = list(line)
        out[spec['id']] = data
    return [''.join(r) for r in rows], out
