"""The two towns: Octo City under the sea and Turtle Town on Sunny Beach.

Each town is a 3x3-screen map stitched onto the bottom of the big level (below the temples) and
reached through a gate in the overworld. Buildings are solid 'O' tiles whose look comes from a
big picture (see gfx.make_city_art); ART maps each of those tiles to its piece of the picture.

Tile legend (on top of the usual ones): 'O' building, '=' paving / boardwalk, 'E' town gate.
"""
CW, CH = 48, 33          # tiles per town (3 x 3 screens)


class _Canvas:
    def __init__(self, floor='.'):
        self.g = [[floor] * CW for _ in range(CH)]
        self.art = {}            # (x, y) -> (picture, column, row)
        self.spots = {}          # who stands where: name -> (x, y)

    def rect(self, x0, y0, x1, y1, ch):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.g[y][x] = ch

    def put(self, x, y, ch, art=None):
        self.g[y][x] = ch
        if art:
            self.art[(x, y)] = (art, 0, 0)

    def building(self, key, x, y, w, h):
        for j in range(h):
            for i in range(w):
                self.g[y + j][x + i] = 'O'
                self.art[(x + i, y + j)] = (key, i, j)

    def border(self):
        self.rect(0, 0, CW - 1, 0, '#')
        self.rect(0, CH - 1, CW - 1, CH - 1, '#')
        self.rect(0, 0, 0, CH - 1, '#')
        self.rect(CW - 1, 0, CW - 1, CH - 1, '#')

    def gate(self, key):
        """The way out: two gate tiles in the middle of the bottom wall, framed by pillars."""
        for i, x in enumerate(range(22, 26)):
            self.art[(x, CH - 1)] = (key, i, 0)
        self.g[CH - 1][23] = self.g[CH - 1][24] = 'E'


# ======================================================================
# Octo City
# ======================================================================
def _octo_city():
    c = _Canvas('.')
    c.border()
    c.rect(1, 7, 46, 7, '=')                       # Shell Street, past the houses and the hall
    c.rect(15, 8, 32, 20, '=')                     # the plaza
    c.rect(21, 21, 26, 31, '=')                    # the avenue down to the gate
    c.rect(1, 22, 46, 22, '=')                     # Current Lane
    c.building('o_house_a', 2, 2, 5, 4)
    c.building('o_house_b', 9, 2, 5, 4)
    c.building('o_hall', 18, 1, 12, 6)
    c.building('o_museum', 33, 1, 10, 5)
    c.building('o_tower', 44, 1, 3, 5)
    c.building('o_stall_ink', 3, 11, 4, 2)
    c.building('o_stall_hat', 9, 11, 4, 2)
    c.building('o_stall_bank', 3, 17, 4, 2)
    c.building('o_stall_food', 9, 17, 4, 2)
    c.building('o_fountain', 22, 12, 4, 4)
    c.building('o_board', 29, 9, 4, 3)
    c.building('o_house_c', 37, 9, 5, 4)
    c.building('o_house_d', 40, 25, 5, 4)
    c.building('o_house_e', 2, 25, 5, 4)
    c.building('o_house_f', 9, 25, 5, 4)
    c.building('o_house_g', 31, 25, 5, 4)
    # the park: sea grass, a pond, coral and kelp hedges
    c.rect(34, 14, 45, 20, ',')
    c.rect(38, 16, 41, 18, 'v')
    for x, y in ((35, 14), (44, 14), (35, 20), (44, 20), (42, 17)):
        c.put(x, y, 'C')
    for x in range(14, 21):
        if x != 17:
            c.put(x, 24, 'K')
    for x in range(27, 31):
        c.put(x, 29, 'K')
    # coral lamps along the avenue and round the plaza
    for x, y in ((20, 24), (27, 24), (20, 28), (27, 28), (15, 8), (32, 8), (15, 20), (32, 20), (8, 8), (40, 8)):
        c.put(x, y, 'C')
    for x, y in ((16, 27), (17, 30), (30, 27), (29, 31), (5, 22 - 1), (44, 23), (13, 15), (2, 14), (12, 30)):
        if c.g[y][x] == '.':
            c.put(x, y, ',')
    c.gate('o_gate')
    c.spots.update({
        'octavia': (23.5, 8.5), 'inky': (4.5, 13.5), 'tenta': (10.5, 13.5), 'bubbles': (4.5, 19.5),
        'barnaby': (10.5, 19.5), 'octagon': (37.5, 6.5), 'coraline': (36.5, 16.5), 'pips': (42.5, 23.5),
        'ollie': (17.5, 26.5), 'granny': (4.5, 29.5), 'ziggy': (29.5, 17.5), 'tally': (30.5, 12.5),
        'statue': (23.5, 18.5),
    })
    return c


# ======================================================================
# Turtle Town
# ======================================================================
def _turtle_town():
    c = _Canvas('.')
    c.border()
    c.rect(39, 1, 46, 31, 'v')                     # the sea laps the east side of town
    c.rect(37, 1, 38, 31, ',')
    c.rect(30, 19, 45, 20, '=')                    # the pier
    c.rect(1, 7, 36, 7, '=')                       # Sandy Row
    c.rect(15, 9, 32, 17, '=')                     # the boardwalk square
    c.rect(21, 18, 26, 31, '=')
    c.building('t_house_a', 2, 1, 5, 4)
    c.building('t_house_b', 9, 1, 5, 4)
    c.building('t_elder', 18, 1, 12, 6)
    c.building('t_lighthouse', 33, 1, 3, 6)
    c.building('t_stall_hat', 9, 11, 4, 2)
    c.building('t_stall_swap', 3, 18, 4, 2)
    c.building('t_stall_clinic', 9, 18, 4, 2)
    c.building('t_fire', 23, 12, 2, 2)
    c.building('t_house_c', 30, 23, 5, 4)
    c.building('t_house_d', 2, 9, 5, 4)
    c.building('t_hut', 30, 9, 4, 3)
    # the nest nursery: little sand mounds full of eggs, behind a hedge
    for x in range(2, 15):
        c.put(x, 23, 'K')
    for x, y in ((3, 25), (6, 26), (9, 25), (12, 27), (4, 28), (8, 29), (11, 30)):
        c.put(x, y, 'C')
        c.art[(x, y)] = ('t_nest', 0, 0)
    c.put(7, 23, '.')
    # palms and beach grass
    for x, y in ((16, 9), (32, 17), (16, 17), (19, 26), (28, 26), (35, 14), (2, 15), (14, 20), (35, 29), (27, 30)):
        c.put(x, y, 'C')
    for x, y in ((17, 28), (18, 22), (29, 22), (14, 15), (6, 15), (26, 9)):
        if c.g[y][x] == '.':
            c.put(x, y, ',')
    c.gate('t_gate')
    c.spots.update({
        'tortuga': (23.5, 8.5), 'sheldon': (14.5, 11.5), 'myrtle': (10.5, 13.5), 'speedy': (29.5, 28.5),
        'shellby': (31.5, 21.5), 'tim': (17.5, 25.5), 'nana': (4.5, 20.5), 'carapace': (10.5, 20.5),
        'coco': (26.5, 14.5), 'grumble': (7.5, 14.5), 'tilly_home': (18.5, 27.5),
    })
    return c


# where each town's gate stands in the big world, and what it looks like there
OVERWORLD_GATES = {
    'octo': {'door': (53, 45), 'set': {(52, 45): 'O', (54, 45): 'O'},
             'art': {(52 + i, 44 + j): ('ow_octo_gate', i, j) for i in range(3) for j in range(2)},
             'exit_to': (53, 46.5)},
    'turtle': {'door': (84, 263), 'set': {(83, 263): '#', (85, 263): '#'},
               'art': {(83 + i, 263): ('ow_turtle_gate', i, 0) for i in range(3)},
               'exit_to': (84, 264.5)},
}

TOWNS = [
    # id, title, builder, theme, music, x offset, what lies outside, sea floor?
    ('octo', 'OCTO CITY', _octo_city, 'octocity', 'octocity', 0, 'sea', True),
    ('turtle', 'TURTLE TOWN', _turtle_town, 'turtletown', 'turtletown', 50, 'land', False),
]


def build_all(width, top):
    """Both towns side by side. Returns (extra level rows, {id: town data})."""
    rows = [['#'] * width for _ in range(CH)]
    out = {}
    for tid, title, builder, theme, music, ox, outside, wet in TOWNS:
        c = builder()
        for y in range(CH):
            rows[y][ox:ox + CW] = c.g[y]
        gate = OVERWORLD_GATES[tid]
        out[tid] = {
            'id': tid, 'title': title, 'theme': theme, 'music': music, 'outside': outside, 'wet': wet,
            'rect': (ox, top, ox + CW - 1, top + CH - 1),
            'entry': (ox + 23.5, top + CH - 2.6),
            'art': {(ox + x, top + y): a for (x, y), a in c.art.items()},
            'spots': {k: (ox + x, top + y) for k, (x, y) in c.spots.items()},
            'door': gate['door'], 'exit_to': gate['exit_to'],
        }
    return [''.join(r) for r in rows], out
