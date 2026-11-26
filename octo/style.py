"""Octo's wardrobe: hats to wear and the colour of the ink jet's puff.

Hats are just for fun (no powers). Some Octo starts with, Hermie sells some, and the rest are
earned. Press H (or tap HAT) to open the wardrobe.
"""
import math

import pygame

# id: (name, how to get it)
HATS = {
    'none': ("NO HAT", None),
    'cap': ("SEA CAP", None),
    'bow': ("BIG BOW", None),
    'party': ("PARTY HAT", None),
    'beanie': ("BEANIE", 'shop'),
    'chef': ("CHEF HAT", 'shop'),
    'cowboy': ("COWBOY HAT", 'shop'),
    'tophat': ("TOP HAT", 'shop'),
    'sombrero': ("SOMBRERO", 'shop'),
    'flower': ("FLOWER CROWN", 'trials10'),
    'pirate': ("PIRATE HAT", 'captain'),
    'propeller': ("PROPELLER CAP", 'worlds'),
    'wizard': ("WIZARD HAT", 'forms10'),
    'viking': ("VIKING HELM", 'guardians10'),
    'crown': ("GOLD CROWN", 'bells'),
    'halo': ("HALO", 'alltrials'),
    # from the towns: sold at the stalls, or given as side-quest rewards
    'beret': ("BERET", 'item'),
    'fez': ("FEZ", 'item'),
    'tiara': ("TIARA", 'item'),
    'sunhat': ("SUN HAT", 'item'),
    'straw': ("STRAW HAT", 'item'),
    'snorkel': ("SNORKEL MASK", 'item'),
    'headphones': ("HEADPHONES", 'item'),
    'gradcap': ("GRAD CAP", 'item'),
    'shellhelm': ("SHELL HELMET", 'item'),
    'bandana': ("LUCKY BANDANA", 'item'),
    'champion': ("CHAMPION CROWN", 'item'),
}
ITEM_HOW = {
    'beret': "MADAME TENTA SELLS IT IN OCTO CITY.", 'fez': "MADAME TENTA SELLS IT IN OCTO CITY.",
    'tiara': "MADAME TENTA SELLS IT IN OCTO CITY.", 'sunhat': "MYRTLE SELLS IT IN TURTLE TOWN.",
    'straw': "MYRTLE SELLS IT IN TURTLE TOWN.", 'snorkel': "HELP LITTLE OLLIE IN OCTO CITY.",
    'headphones': "HELP ZIGGY IN OCTO CITY.", 'gradcap': "HELP PROFESSOR OCTAGON IN OCTO CITY.",
    'shellhelm': "HELP ELDER TORTUGA IN TURTLE TOWN.", 'bandana': "HELP SPEEDY IN TURTLE TOWN.",
    'champion': "REACH THE 100,000 POINT MILESTONE.",
}
HAT_PRICES = {'beanie': 30, 'chef': 40, 'cowboy': 50, 'sombrero': 50, 'tophat': 60}
HOW = {
    None: "YOURS FROM THE START.",
    'shop': "SOLD AT HERMIE'S CATALOGUE.",
    'trials10': "WIN 10 TRIALS.",
    'captain': "BEAT CAPTAIN CLAW IN THE SHIP GRAVEYARD.",
    'worlds': "VISIT ALL FOUR WORLDS.",
    'forms10': "LEARN 10 BASE FORMS.",
    'guardians10': "BEAT 10 GUARDIANS.",
    'bells': "RING ALL SEVEN TIDE BELLS.",
    'alltrials': "WIN EVERY TRIAL.",
}

# name, colour (None = a rainbow, 'sparkle' = shimmering gold), and what unlocks it (None = free)
DASH_COLORS = [("INK", (24, 18, 56), None), ("CORAL", (240, 90, 120), None), ("GOLD", (240, 190, 40), None),
               ("MINT", (80, 220, 160), None), ("SKY", (90, 170, 255), None), ("VIOLET", (150, 80, 230), None),
               ("FIRE", (255, 110, 30), None), ("SNOW", (235, 240, 255), None), ("RAINBOW", None, None),
               # bought from Inky in Octo City, or earned
               ("OCEAN", (20, 140, 210), 'ink_ocean'), ("CANDY", (255, 150, 220), 'ink_candy'),
               ("TOXIC", (130, 255, 60), 'ink_toxic'), ("SHADOW", (50, 20, 70), 'ink_shadow'),
               ("PEARL", 'pearl', 'ink_pearl'), ("STORM", 'storm', 'ink_storm'),
               ("LEGEND GOLD", 'sparkle', 'ink_legend')]


def ink_unlocked(player, index):
    need = DASH_COLORS[index % len(DASH_COLORS)][2]
    return need is None or need in player.items


def dash_rgb(index, t=0):
    name, col, _need = DASH_COLORS[index % len(DASH_COLORS)]
    if col is None:
        h = (t * 7) % 360
        c = pygame.Color(0)
        c.hsva = (h, 80, 100, 100)
        return (c.r, c.g, c.b)
    if col == 'pearl':
        k = (math.sin(t * 0.2) + 1) / 2
        return (int(230 + 25 * k), int(225 + 20 * k), int(240 + 15 * k))
    if col == 'storm':
        return (255, 250, 120) if (t // 3) % 3 == 0 else (90, 120, 230)
    if col == 'sparkle':
        k = (math.sin(t * 0.3) + 1) / 2
        return (255, int(190 + 60 * k), int(40 + 150 * k))
    return col


def unlocked(game, hat):
    import forms
    import world
    p = game.player
    how = HATS[hat][1]
    if how is None:
        return True
    if how == 'shop':
        return 'hat_' + hat in p.items
    if how == 'trials10':
        return len(game.trials_done) >= 10
    if how == 'alltrials':
        return len(game.trials_done) >= len(world.TRIALS)
    if how == 'captain':
        return 'captain' in game.flags.get('minis', [])
    if how == 'guardians10':
        return len(game.flags.get('minis', [])) >= 10
    if how == 'forms10':
        return sum(1 for f in p.forms if f in forms.BASE) >= 10
    if how == 'bells':
        return len(game.flags.get('bells', [])) >= world.BELLS_NEEDED
    if how == 'worlds':
        return all(game.flags.get(k) for k in ('sky_intro', 'intro_land', 'intro_under'))
    if how == 'item':
        return 'hat_' + hat in p.items
    return False


def how_text(hat):
    how = HATS[hat][1]
    return ITEM_HOW.get(hat, "") if how == 'item' else HOW[how]


# ---------------------------------------------------------------------- hat art (drawn in code)
_cache = {}


def _hat(hat):
    if hat in _cache:
        return _cache[hat]
    s = pygame.Surface((18, 12), pygame.SRCALPHA)
    k = (20, 20, 30)
    if hat == 'cap':
        pygame.draw.ellipse(s, k, (3, 4, 12, 8))
        pygame.draw.ellipse(s, (40, 90, 220), (4, 5, 10, 7))
        pygame.draw.rect(s, k, (9, 9, 9, 3))
        pygame.draw.rect(s, (30, 70, 190), (10, 9, 7, 2))
        s.set_at((9, 5), (255, 255, 255))
    elif hat == 'bow':
        for side in (-1, 1):
            pts = [(9, 8), (9 + side * 7, 4), (9 + side * 7, 11)]
            pygame.draw.polygon(s, (150, 30, 80), pts)
            pygame.draw.polygon(s, (250, 90, 160), [(9, 8), (9 + side * 6, 5), (9 + side * 6, 10)])
        pygame.draw.circle(s, (255, 150, 200), (9, 8), 2)
    elif hat == 'party':
        pygame.draw.polygon(s, k, [(4, 12), (14, 12), (9, 0)])
        pygame.draw.polygon(s, (255, 200, 60), [(5, 11), (13, 11), (9, 1)])
        for y, c in ((4, (240, 80, 120)), (8, (80, 180, 255))):
            pygame.draw.line(s, c, (9 - y // 2, y), (9 + y // 2, y))
        pygame.draw.circle(s, (255, 255, 255), (9, 1), 1)
    elif hat == 'beanie':
        pygame.draw.ellipse(s, k, (3, 3, 12, 11))
        pygame.draw.ellipse(s, (220, 60, 60), (4, 4, 10, 9))
        pygame.draw.rect(s, (240, 240, 240), (3, 9, 12, 3))
        pygame.draw.circle(s, (250, 250, 250), (9, 3), 2)
    elif hat == 'chef':
        for cx in (6, 9, 12):
            pygame.draw.circle(s, (200, 200, 210), (cx, 4), 3)
            pygame.draw.circle(s, (255, 255, 255), (cx, 4), 2)
        pygame.draw.rect(s, (200, 200, 210), (5, 5, 9, 7))
        pygame.draw.rect(s, (255, 255, 255), (6, 5, 7, 6))
    elif hat == 'cowboy':
        pygame.draw.ellipse(s, (70, 40, 20), (0, 8, 18, 4))
        pygame.draw.rect(s, (70, 40, 20), (4, 2, 10, 8))
        pygame.draw.rect(s, (150, 100, 50), (5, 3, 8, 6))
        pygame.draw.rect(s, (60, 30, 20), (5, 7, 8, 1))
    elif hat == 'tophat':
        pygame.draw.rect(s, k, (1, 9, 16, 3))
        pygame.draw.rect(s, k, (4, 0, 10, 10))
        pygame.draw.rect(s, (60, 60, 70), (5, 1, 8, 8))
        pygame.draw.rect(s, (200, 40, 60), (5, 7, 8, 2))
    elif hat == 'sombrero':
        pygame.draw.ellipse(s, (120, 80, 20), (0, 7, 18, 5))
        pygame.draw.ellipse(s, (230, 190, 90), (1, 7, 16, 4))
        pygame.draw.ellipse(s, (230, 190, 90), (5, 1, 8, 8))
        pygame.draw.line(s, (220, 60, 60), (5, 7), (13, 7))
    elif hat == 'flower':
        for i, c in enumerate(((255, 120, 160), (255, 230, 100), (180, 140, 255), (255, 160, 80))):
            cx = 3 + i * 4
            pygame.draw.circle(s, c, (cx, 8), 2)
            s.set_at((cx, 8), (255, 255, 220))
        pygame.draw.line(s, (60, 160, 60), (1, 10), (17, 10))
    elif hat == 'pirate':
        pygame.draw.polygon(s, k, [(0, 10), (18, 10), (14, 2), (9, 4), (4, 2)])
        pygame.draw.polygon(s, (50, 40, 50), [(2, 9), (16, 9), (13, 3), (9, 5), (5, 3)])
        pygame.draw.circle(s, (240, 240, 230), (9, 7), 1)
        pygame.draw.line(s, (220, 180, 60), (2, 9), (16, 9))
    elif hat == 'propeller':
        pygame.draw.ellipse(s, k, (3, 5, 12, 8))
        for i, c in enumerate(((240, 80, 80), (255, 220, 80), (80, 160, 255), (80, 200, 120))):
            pygame.draw.arc(s, c, (4, 6, 10, 10), math.pi / 4 * i + 0.1, math.pi / 4 * (i + 1), 4)
        pygame.draw.line(s, k, (9, 1), (9, 5))
        pygame.draw.line(s, (240, 240, 250), (4, 1), (14, 1), 2)
    elif hat == 'wizard':
        pygame.draw.polygon(s, k, [(2, 12), (16, 12), (11, 0), (7, 3)])
        pygame.draw.polygon(s, (90, 50, 180), [(3, 11), (15, 11), (10, 1), (8, 4)])
        s.set_at((9, 6), (255, 240, 120))
        s.set_at((11, 9), (255, 240, 120))
        pygame.draw.line(s, (255, 220, 90), (3, 11), (15, 11))
    elif hat == 'viking':
        pygame.draw.ellipse(s, k, (3, 4, 12, 9))
        pygame.draw.ellipse(s, (160, 160, 170), (4, 5, 10, 8))
        for side in (-1, 1):
            pygame.draw.polygon(s, (240, 230, 200), [(9 + side * 5, 8), (9 + side * 8, 1), (9 + side * 6, 6)])
        pygame.draw.line(s, (200, 160, 60), (4, 10), (14, 10))
    elif hat == 'crown':
        pygame.draw.polygon(s, (120, 80, 0), [(3, 11), (15, 11), (15, 3), (12, 7), (9, 2), (6, 7), (3, 3)])
        pygame.draw.polygon(s, (250, 210, 60), [(4, 10), (14, 10), (14, 5), (12, 8), (9, 4), (6, 8), (4, 5)])
        for x, c in ((6, (220, 40, 60)), (9, (60, 160, 255)), (12, (60, 200, 100))):
            s.set_at((x, 9), c)
    elif hat == 'halo':
        pygame.draw.ellipse(s, (180, 140, 20), (2, 1, 14, 5), 2)
        pygame.draw.ellipse(s, (255, 240, 140), (3, 1, 12, 4), 1)
    elif hat == 'beret':
        pygame.draw.ellipse(s, k, (2, 5, 14, 7))
        pygame.draw.ellipse(s, (200, 40, 60), (3, 5, 12, 6))
        pygame.draw.ellipse(s, (240, 90, 110), (5, 6, 6, 2))
        pygame.draw.line(s, k, (9, 5), (10, 3), 2)
    elif hat == 'fez':
        pygame.draw.polygon(s, k, [(4, 12), (14, 12), (13, 3), (5, 3)])
        pygame.draw.polygon(s, (210, 40, 40), [(5, 11), (13, 11), (12, 4), (6, 4)])
        pygame.draw.line(s, (250, 110, 110), (6, 5), (6, 10))
        pygame.draw.line(s, (20, 20, 20), (9, 3), (13, 6))
        pygame.draw.circle(s, (250, 200, 60), (13, 7), 1)
    elif hat == 'tiara':
        pygame.draw.line(s, (150, 150, 170), (3, 11), (15, 11), 2)
        pygame.draw.polygon(s, (220, 225, 240), [(4, 10), (6, 6), (8, 9), (9, 4), (10, 9), (12, 6), (14, 10)])
        pygame.draw.polygon(s, (120, 120, 150), [(4, 10), (6, 6), (8, 9), (9, 4), (10, 9), (12, 6), (14, 10)], 1)
        s.set_at((9, 6), (240, 80, 160))
        s.set_at((6, 8), (90, 200, 255))
        s.set_at((12, 8), (90, 200, 255))
    elif hat == 'sunhat':
        pygame.draw.ellipse(s, (170, 130, 60), (0, 7, 18, 5))
        pygame.draw.ellipse(s, (250, 226, 150), (1, 7, 16, 4))
        pygame.draw.ellipse(s, (250, 226, 150), (5, 3, 8, 7))
        pygame.draw.line(s, (240, 110, 160), (5, 8), (13, 8), 2)
        s.set_at((14, 9), (255, 160, 200))
    elif hat == 'straw':
        pygame.draw.rect(s, (160, 120, 50), (0, 9, 18, 3))
        pygame.draw.rect(s, (240, 210, 130), (1, 9, 16, 2))
        pygame.draw.rect(s, (160, 120, 50), (4, 3, 10, 7))
        pygame.draw.rect(s, (240, 210, 130), (5, 4, 8, 5))
        pygame.draw.line(s, (60, 90, 180), (5, 8), (12, 8))
    elif hat == 'snorkel':
        pygame.draw.rect(s, k, (2, 7, 14, 5), border_radius=2)
        pygame.draw.rect(s, (120, 210, 255), (3, 8, 12, 3), border_radius=1)
        s.set_at((5, 8), (255, 255, 255))
        pygame.draw.line(s, (250, 140, 40), (15, 10), (15, 1), 2)
        pygame.draw.line(s, (250, 140, 40), (15, 1), (13, 1), 2)
    elif hat == 'headphones':
        pygame.draw.arc(s, k, (2, 1, 14, 18), 0, math.pi, 2)
        for x in (1, 13):
            pygame.draw.rect(s, k, (x, 7, 4, 5), border_radius=1)
            pygame.draw.rect(s, (60, 200, 190), (x + 1, 8, 2, 3))
    elif hat == 'gradcap':
        pygame.draw.polygon(s, (10, 10, 20), [(1, 6), (9, 3), (17, 6), (9, 9)])
        pygame.draw.rect(s, (30, 30, 40), (5, 7, 8, 5))
        pygame.draw.line(s, (250, 200, 60), (9, 6), (14, 8))
        pygame.draw.line(s, (250, 200, 60), (14, 8), (14, 11))
    elif hat == 'shellhelm':
        pygame.draw.ellipse(s, (40, 70, 30), (2, 3, 14, 10))
        pygame.draw.ellipse(s, (110, 160, 80), (3, 4, 12, 8))
        for x, y in ((6, 6), (10, 6), (8, 9)):
            pygame.draw.rect(s, (60, 100, 40), (x - 1, y - 1, 3, 3), 1)
        pygame.draw.line(s, (220, 200, 140), (3, 11), (15, 11))
    elif hat == 'bandana':
        pygame.draw.ellipse(s, (120, 10, 20), (2, 5, 14, 8))
        pygame.draw.ellipse(s, (220, 40, 50), (3, 6, 12, 6))
        for x, y in ((5, 8), (9, 7), (12, 9)):
            s.set_at((x, y), (255, 255, 255))
        pygame.draw.polygon(s, (220, 40, 50), [(15, 8), (18, 6), (18, 11)])
    elif hat == 'champion':
        pygame.draw.polygon(s, (120, 70, 0), [(1, 12), (17, 12), (17, 2), (13, 7), (9, 0), (5, 7), (1, 2)])
        pygame.draw.polygon(s, (255, 214, 60), [(2, 11), (16, 11), (16, 4), (13, 8), (9, 2), (5, 8), (2, 4)])
        for x, c in ((5, (220, 40, 60)), (9, (60, 160, 255)), (13, (60, 200, 100))):
            pygame.draw.circle(s, c, (x, 9), 1)
        s.set_at((9, 3), (255, 255, 255))
    _cache[hat] = s
    return s


def draw_hat(surf, hat, x, y, facing='down', t=0):
    """Draw a hat on an Octo whose 16x16 sprite has its top-left at (x, y)."""
    if not hat or hat == 'none':
        return
    img = _hat(hat)
    if facing == 'left':
        img = pygame.transform.flip(img, True, False)
    lift = 4 + (round(math.sin(t * 0.1) * 1) if hat == 'halo' else 0)
    if hat == 'propeller' and (t // 4) % 2:
        img = pygame.transform.flip(img, True, False)
    surf.blit(img, (x + 8 - img.get_width() // 2, y - img.get_height() + lift))


def icon(hat):
    return _hat(hat) if hat != 'none' else None
