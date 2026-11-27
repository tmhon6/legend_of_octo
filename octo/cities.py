"""The two towns: Octo City under the sea and Turtle Town on Sunny Beach.

Each town is a 3x3-screen map stitched onto the bottom of the big level (below the temples) and
reached through a gate in the overworld. Buildings are solid 'O' tiles whose look comes from a
big picture (see gfx.make_city_art); ART maps each of those tiles to its piece of the picture.

Octo's own house is a third little map, one screen big, entered through its door in Octo City.

Tile legend (on top of the usual ones): 'O' building, '=' paving / boardwalk, 'E' town gate or door.
"""
CW, CH = 48, 33          # tiles per town (3 x 3 screens)
HW, HH = 16, 11          # Octo's house: one screen


class _Canvas:
    def __init__(self, floor='.', w=CW, h=CH):
        self.w, self.h = w, h
        self.g = [[floor] * w for _ in range(h)]
        self.art = {}            # (x, y) -> (picture, column, row)
        self.spots = {}          # who stands where: name -> (x, y)
        self.things = {}         # things to use (a bed, a mailbox): name -> (x0, y0, x1, y1) in tiles
        self.entry = (23.5, h - 2.6)

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

    def thing(self, name, key, x, y, w, h, solid=True):
        """A piece of furniture (or a mailbox): a 3D model you can walk up to and use."""
        if solid:
            self.building(key, x, y, w, h)
        else:
            for j in range(h):
                for i in range(w):
                    self.art[(x + i, y + j)] = (key, i, j)
        self.things[name] = (x, y, x + w - 1, y + h - 1)

    def border(self):
        self.rect(0, 0, self.w - 1, 0, '#')
        self.rect(0, self.h - 1, self.w - 1, self.h - 1, '#')
        self.rect(0, 0, 0, self.h - 1, '#')
        self.rect(self.w - 1, 0, self.w - 1, self.h - 1, '#')

    def gate(self, key):
        """The way out: two gate tiles in the middle of the bottom wall, framed by pillars."""
        for i, x in enumerate(range(22, 26)):
            self.art[(x, self.h - 1)] = (key, i, 0)
        self.g[self.h - 1][23] = self.g[self.h - 1][24] = 'E'


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
    # Octo's own house, by the gate: round and blue like him, its door is its mouth
    c.building('o_home', HOME_AT[0], HOME_AT[1], 5, 4)
    c.g[HOME_DOOR[1]][HOME_DOOR[0]] = 'E'
    c.thing('mail', 'o_mail', HOME_DOOR[0] - 2, HOME_DOOR[1] + 1, 1, 1)
    # the park: sea grass, a pond, coral and kelp hedges
    c.rect(34, 14, 45, 20, ',')
    c.rect(38, 16, 41, 18, 'v')
    for x, y in ((35, 14), (44, 14), (35, 20), (44, 20), (42, 17)):
        c.put(x, y, 'C')
    for x in range(14, 20):
        c.put(x, 24, 'K')
    for x in range(27, 31):
        c.put(x, 29, 'K')
    # coral lamps along the avenue and round the plaza
    for x, y in ((20, 24), (27, 24), (20, 28), (27, 28), (15, 8), (32, 8), (15, 20), (32, 20), (8, 8), (40, 8)):
        c.put(x, y, 'C')
    for x, y in ((14, 27), (19, 31), (30, 27), (29, 31), (5, 22 - 1), (44, 23), (13, 15), (2, 14), (10, 30)):
        if c.g[y][x] == '.':
            c.put(x, y, ',')
    c.gate('o_gate')
    c.spots.update({
        'octavia': (23.5, 8.5), 'inky': (4.5, 13.5), 'tenta': (10.5, 13.5), 'bubbles': (4.5, 19.5),
        'barnaby': (10.5, 19.5), 'octagon': (37.5, 6.5), 'coraline': (36.5, 16.5), 'pips': (42.5, 23.5),
        'ollie': (12.5, 30.5), 'granny': (4.5, 29.5), 'ziggy': (29.5, 17.5), 'tally': (30.5, 12.5),
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


# ======================================================================
# Octo's house (inside)
# ======================================================================
HOME_AT = (15, 25)                 # the house's corner in Octo City
HOME_DOOR = (17, 28)               # its door (the middle of its front)


def _octo_home():
    c = _Canvas('.', HW, HH)
    c.building('h_wall_back', 0, 0, HW, 2)          # the back and front walls are 3D models
    c.building('h_wall_front', 0, HH - 1, HW, 1)
    c.rect(0, 2, 0, HH - 2, '#')                     # the side walls are plain wall tiles
    c.rect(HW - 1, 2, HW - 1, HH - 2, '#')
    c.g[HH - 1][7] = c.g[HH - 1][8] = 'E'            # the front door: a gap in the front wall
    c.thing('rug', 'h_rug', 5, 4, 5, 4, solid=False)
    c.thing('bed', 'h_bed', 1, 2, 2, 3)
    c.thing('shelf', 'h_shelf', 4, 2, 4, 1)
    c.thing('desk', 'h_desk', 9, 2, 2, 1)
    c.thing('tank', 'h_tank', 12, 2, 3, 1)
    c.thing('table', 'h_table', 6, 5, 3, 2)
    c.thing('hats', 'h_hats', 14, 5, 1, 1)
    c.thing('lamp', 'h_lamp', 1, 6, 1, 1)
    c.thing('basket', 'h_basket', 1, 9, 2, 1)
    c.thing('plant', 'h_plant', 14, 9, 1, 1)
    c.entry = (7.5, 8.4)
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
    ('home', "OCTO'S HOUSE", _octo_home, 'octohome', 'home', 100, 'octocity', True),
]


def build_all(width, top):
    """Both towns side by side. Returns (extra level rows, {id: town data})."""
    rows = [['#'] * width for _ in range(CH)]
    out = {}
    for tid, title, builder, theme, music, ox, outside, wet in TOWNS:
        c = builder()
        for y in range(c.h):
            rows[y][ox:ox + c.w] = c.g[y]
        if tid == 'home':                       # its door is in Octo City
            dx, dy = HOME_DOOR[0] + out['octo']['rect'][0], HOME_DOOR[1] + top
            gate = {'door': (dx, dy), 'exit_to': (dx, dy + 1.5)}
        else:
            gate = OVERWORLD_GATES[tid]
        out[tid] = {
            'id': tid, 'title': title, 'theme': theme, 'music': music, 'outside': outside, 'wet': wet,
            'rect': (ox, top, ox + c.w - 1, top + c.h - 1),
            'entry': (ox + c.entry[0], top + c.entry[1]),
            'art': {(ox + x, top + y): a for (x, y), a in c.art.items()},
            'spots': {k: (ox + x, top + y) for k, (x, y) in c.spots.items()},
            'things': {k: (ox + x0, top + y0, ox + x1, top + y1) for k, (x0, y0, x1, y1) in c.things.items()},
            'door': gate['door'], 'exit_to': gate['exit_to'],
        }
    return [''.join(r) for r in rows], out
