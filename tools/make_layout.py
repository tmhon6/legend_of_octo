"""Draw the whole game layout as pictures and a PDF, so it can be reviewed without playing.

    .venv/bin/python tools/make_layout.py

Writes docs/layout.pdf plus one PNG per page in docs/layout/. Everything is drawn from the
real game data (world.py, temples.py, entities.py), so re-run it after changing the map.
"""
import os
import sys

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'octo'))

import pygame  # noqa: E402

pygame.init()
pygame.display.set_mode((8, 8))

import entities  # noqa: E402
import gfx  # noqa: E402
import temples  # noqa: E402
import world  # noqa: E402
from settings import TILE  # noqa: E402

gfx.load()
OUT = os.path.join(ROOT, 'docs')
PAGES = []
INK = (255, 255, 255)
BG = (12, 16, 40)


# ---------------------------------------------------------------- drawing helpers
def label(surf, s, x, y, color=INK, scale=2, center=True, box=True):
    w = gfx.text_width(s.upper()) + 2
    tmp = pygame.Surface((w, 9), pygame.SRCALPHA)
    gfx.text(tmp, s, 0, 0, color)
    tmp = pygame.transform.scale(tmp, (w * scale, 9 * scale))
    x = x - tmp.get_width() // 2 if center else x
    if box:
        r = pygame.Rect(x - 3, y - 2, tmp.get_width() + 4, tmp.get_height() + 2)
        shade = pygame.Surface(r.size, pygame.SRCALPHA)
        shade.fill((0, 0, 0, 170))
        surf.blit(shade, r)
    surf.blit(tmp, (x, y))
    return tmp.get_width()


def sprite(kind):
    v = gfx.SPR.get(kind)
    if isinstance(v, dict):
        v = next(iter(v.values()))
    if isinstance(v, list):
        v = v[0]
    return v


def blit_c(surf, img, cx, cy, scale=1):
    if scale != 1:
        img = pygame.transform.scale(img, (img.get_width() * scale, img.get_height() * scale))
    surf.blit(img, (cx - img.get_width() // 2, cy - img.get_height() // 2))


def ring(surf, cx, cy, r, color, w=3):
    pygame.draw.circle(surf, (0, 0, 0), (cx, cy), r + 2, w + 2)
    pygame.draw.circle(surf, color, (cx, cy), r, w)


def page(title, body, subtitle=None):
    w = max(body.get_width(), 1200)
    head = 70 if subtitle else 50
    out = pygame.Surface((w, body.get_height() + head + 10))
    out.fill(BG)
    label(out, title, w // 2, 10, (255, 220, 120), scale=3, box=False)
    if subtitle:
        label(out, subtitle, w // 2, 44, (190, 200, 240), scale=2, box=False)
    out.blit(body, ((w - body.get_width()) // 2, head))
    PAGES.append((title, out))


def px(tx, ty, ox=0, oy=0):
    return int(tx * TILE + TILE // 2 - ox), int(ty * TILE + TILE // 2 - oy)


FULL = world.Level().render(gfx.TILES)
CREATURE_OF = {k: r for r, k in [('CORAL REEF', 'eel'), ('KELP WOODS', 'clam'), ('CORAL GARDENS', 'lionfish'),
                                 ('THE LAGOON', 'ray'), ('THE ABYSS', 'angler'), ('SHIP GRAVEYARD', 'bilge'),
                                 ('FROZEN SHELF', 'squid'), ('EMBER VENTS', 'slug'), ('SUNKEN CITY', 'wisp'),
                                 ('SKY ISLANDS', 'cloud'), ('SKY ISLANDS', 'gull'),
                                 ('FROZEN SHELF', 'icecrab'), ('EMBER VENTS', 'lavacrab')]}
NAME = {d: ('SUNKEN SHRINE' if d == 'shrine' else world.TEMPLES[d]['title']) for d, _ in world.QUEST}


def boss_name(bid):
    return entities.MINIBOSS_STYLES[bid]['name']


def draw_things(surf, rect, enemies=True):
    """Spawns, items, portals and landmarks inside a tile rect, onto a crop of the map."""
    x0, y0 = rect[0] * TILE, rect[1] * TILE

    def inside(tx, ty):
        return rect[0] <= tx <= rect[2] and rect[1] <= ty <= rect[3]
    if enemies:
        for kind, tx, ty in world.ENEMIES:
            if inside(tx, ty) and not kind.startswith('tboss:') and kind in gfx.SPR:
                blit_c(surf, sprite(kind), *px(tx, ty, x0, y0))
    for kind, tx, ty in world.ITEMS:
        if inside(tx, ty):
            img = gfx.SPR['heart']['container'] if kind == 'container' else sprite(kind)
            if img is not None:
                cx, cy = px(tx, ty, x0, y0)
                blit_c(surf, img, cx, cy)
                if kind in ('container', 'key'):
                    ring(surf, cx, cy, 11, (255, 120, 150) if kind == 'container' else (255, 220, 80), 2)


# ---------------------------------------------------------------- pages: the four worlds
WORLD_SUB = {'sea': "REGIONS, DUNGEON DOORS, GUARDIANS, TRIAL PORTALS, PASSAGES, HEART SHELLS AND ENEMIES",
             'sky': "REACHED BY GEYSERS. OCTO ROLLS IN A BALL OF WATER UP HERE",
             'land': "THE SURFACE: REACHED BY THE WHITE SHORE STEPS",
             'under': "THE UNDERDEEP: REACHED BY THE PURPLE SINKHOLES"}


def world_page(wld):
    rect = world.WORLD_RECTS[wld]
    x0, y0, x1, y1 = rect
    surf = FULL.subsurface((x0 * TILE, y0 * TILE, (x1 - x0 + 1) * TILE, (y1 - y0 + 1) * TILE)).copy()
    ox, oy = x0 * TILE, y0 * TILE
    shade = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 50))
    surf.blit(shade, (0, 0))
    draw_things(surf, rect)

    def here(tx, ty):
        return world.in_rect(tx, ty, rect)
    for name, r in world.REGIONS:                     # region names
        if name.startswith(('TRIAL', 'BOSS')) or name in ('PEARL SHOP',) or not here(r[0], r[1]):
            continue
        cx = (r[0] + r[2] + 1) * TILE // 2 - ox
        y = r[1] * TILE + 22 - oy
        if any(world.in_rect(*t['door'], (r[0], r[1], r[2], r[1] + 4)) for t in world.TEMPLES.values()):
            y = (r[3] - 2) * TILE - oy
        label(surf, name, cx, y, (150, 220, 255), scale=3)
    if wld == 'sea':
        label(surf, 'CORAL REEF', 34 * TILE, 38 * TILE, (150, 220, 255), scale=3)
    for name, t in world.TRIALS.items():
        if here(*t['portal']):
            cx, cy = px(*t['portal'], ox, oy)
            ring(surf, cx, cy, 10, t.get('color', INK))
            label(surf, name.upper(), cx, cy + 12, t.get('color', INK), scale=1)
    for a, b in world.GEYSERS:
        for (gx, gy), txt in ((a, 'GEYSER UP'), (b, 'GEYSER DOWN')):
            if here(gx, gy):
                cx, cy = px(gx, gy, ox, oy)
                ring(surf, cx, cy, 10, (200, 240, 255))
                label(surf, txt, cx, cy + 12, (200, 240, 255), scale=1)
    for a, b, kind in world.PASSAGES:
        for (gx, gy), other in ((a, b), (b, a)):
            if here(gx, gy):
                cx, cy = px(gx, gy, ox, oy)
                col = (255, 255, 255) if kind == 'shore' else (200, 140, 255)
                ring(surf, cx, cy, 12, col)
                dest = world.WORLD_NAMES[world.world_at(*other)]
                label(surf, ('SHORE STEPS TO ' if kind == 'shore' else 'SINKHOLE TO ') + dest, cx, cy + 14, col, scale=1)
    for bid, tx, ty in world.MINIBOSSES:
        if not here(tx, ty):
            continue
        cx, cy = px(tx, ty, ox, oy)
        st = entities.MINIBOSS_STYLES[bid]
        blit_c(surf, gfx.tint(sprite(st['base']), st['tint']), cx, cy, 2)
        ring(surf, cx, cy, 20, (255, 80, 80))
        opens = world.SIGIL_OF.get(bid)
        reward = f" - SIGIL FOR {NAME[opens]}" if opens else \
            (" - SPIRIT PEARL" if bid in world.NEW_WORLD_GUARDIANS else " - HEART SHELL")
        label(surf, boss_name(bid) + reward, cx, cy + 24, (255, 140, 140), scale=1)
    for tid, t in world.TEMPLES.items():
        if here(*t['door']):
            cx, cy = px(*t['door'], ox, oy)
            blit_c(surf, gfx.SPR['bell'], cx, cy - 2, 2)
            ring(surf, cx, cy, 18, (255, 210, 90))
            label(surf, t['title'], cx, cy + 22, (255, 220, 120), scale=2)
    if wld == 'sea':
        for (tx, ty), what in (((47.5, 20), 'SUNKEN SHRINE GATE (BIG PINCH SIGIL)'),
                               ((148.5, 77), 'MURK PALACE DOOR (7 TIDE BELLS)'),
                               ((141.5, 60), 'MURK + THE GOLDEN PEARL'),
                               ((47.5, 5), 'GRIMFIN + TIDE BELL 1'),
                               (world.START, 'START (OCTO TEMPLE)'),
                               ((30, 46), "HERMIE'S SHOP"), ((37, 46), 'FUSION MACHINE')):
            cx, cy = px(tx, ty)
            ring(surf, cx, cy, 14, (120, 255, 160))
            label(surf, what, cx, cy + 16, (160, 255, 190), scale=2 if 'MURK' in what or 'START' in what else 1)
    if wld == 'sky':
        surf = pygame.transform.smoothscale(surf, (surf.get_width() * 3 // 2, surf.get_height() * 3 // 2))
    page(world.WORLD_NAMES[wld], surf, WORLD_SUB[wld])


def trials_page():
    rooms = sorted(world.TRIALS.items(), key=lambda kv: (kv[1]['room'][1], kv[1]['room'][0]))
    cols = 6
    cw, ch = 16 * TILE, 11 * TILE
    rows = (len(rooms) + cols - 1) // cols
    surf = pygame.Surface((cols * (cw + 12), rows * (ch + 40)))
    surf.fill(BG)
    for i, (name, t) in enumerate(rooms):
        x0, y0, x1, y1 = t['room']
        crop = FULL.subsurface((x0 * TILE, y0 * TILE, (x1 - x0 + 1) * TILE, (y1 - y0 + 1) * TILE)).copy()
        for k in ('entry', 'boss_at', 'thief_at', 'clam_at'):
            if k in t:
                cx, cy = int(t[k][0] * TILE + 8), int(t[k][1] * TILE + 8)
                ring(crop, cx, cy, 7, {'entry': (120, 255, 160)}.get(k, (255, 80, 80)), 2)
        for ox_, oy_ in t.get('orbs', []):
            blit_c(crop, gfx.SPR['orb'], ox_ * TILE + 8, oy_ * TILE + 8)
        gx, gy = (i % cols) * (cw + 12), (i // cols) * (ch + 40)
        surf.blit(crop, (gx, gy + 30))
        kind = t['kind'] + (' / DARK' if t.get('dark') else '') + (' / CURRENT' if t.get('current') else '')
        label(surf, f"{t['title'][9:]} - {kind}", gx + cw // 2, gy + 6, t.get('color', INK), scale=2, box=False)
    page(f"THE {len(world.TRIALS)} TRIAL ROOMS", surf, "EACH WIN GIVES A SPIRIT PEARL. 3 PEARLS AT THE ALTAR TEACH A NEW FORM. GREEN RING = WHERE OCTO LANDS")


# ---------------------------------------------------------------- pages: temples
def temple_page(tid):
    t = world.TEMPLES[tid]
    x0, y0, x1, y1 = t['rect']
    rect = t['rect']
    surf = FULL.subsurface((x0 * TILE, y0 * TILE, (x1 - x0 + 1) * TILE, (y1 - y0 + 1) * TILE)).copy()
    ox, oy = x0 * TILE, y0 * TILE
    for gx in range(temples.GW):                    # grey out unused grid slots
        for gy in range(temples.GH):
            if (gx, gy) not in t['rooms']:
                pygame.draw.rect(surf, (8, 8, 16), (gx * temples.RW * TILE, gy * temples.RH * TILE,
                                                    temples.RW * TILE, temples.RH * TILE))
    draw_things(surf, rect)
    for name, a in t['arenas'].items():             # sealed rooms and their rewards
        ax0, ay0, ax1, ay1 = a['rect']
        r = pygame.Rect((ax0 - x0) * TILE, (ay0 - y0) * TILE, (ax1 - ax0 + 1) * TILE, (ay1 - ay0 + 1) * TILE)
        pygame.draw.rect(surf, (255, 90, 90) if a.get('boss') else (200, 160, 255), r, 3)
        kind, rx, ry = a['reward']
        cx, cy = px(rx, ry, ox, oy)
        img = gfx.SPR['heart']['container'] if kind == 'container' else sprite(kind)
        if img is not None:
            blit_c(surf, img, cx, cy, 2 if kind in ('bell', 'key') else 1)
        txt = {'bell': 'TIDE BELL', 'key': 'KEY (CLEAR ROOM)', 'container': 'HEART SHELL'}.get(kind, '')
        if a.get('boss'):
            label(surf, 'GUARDIAN: ' + boss_name(t['boss']), r.centerx, r.y + 6, (255, 140, 140), scale=2)
            bx, by = px(*next((x, y) for k, x, y in t['enemies'] if k.startswith('tboss:')), ox, oy)
            st = entities.MINIBOSS_STYLES[t['boss']]
            blit_c(surf, gfx.tint(sprite(st['base']), st['tint']), bx, by, 2)
        elif txt:
            label(surf, txt, cx, cy + 14, (255, 230, 150), scale=2)
        else:
            label(surf, 'SEALED ROOM', r.centerx, r.y + 6, (210, 190, 255), scale=2)
    for kind, tx, ty in t['items']:
        if kind == 'key':
            cx, cy = px(tx, ty, ox, oy)
            label(surf, 'KEY', cx, cy + 14, (255, 230, 150), scale=2)
    for e, kind in t['edges'].items():              # doors
        a, b = tuple(e)
        if kind == 'open':
            continue
        cells = []
        for r_, o in ((a, b), (b, a)):
            d = next(k for k, (dx, dy) in temples.DIRS.items() if (r_[0] + dx, r_[1] + dy) == o)
            cells += [(r_[0] * temples.RW + cx, r_[1] * temples.RH + cy) for cx, cy in temples.DOOR_CELLS[d]]
        mx = sum(c[0] for c in cells) / len(cells) * TILE + 8
        my = sum(c[1] for c in cells) / len(cells) * TILE + 8
        txt = {'lock': 'LOCKED', 'bomb': 'CRACKED (BOMB)',
               'gate': {'K': 'KELP (SLAP)', 'R': 'CRACKED (BOMB)', 'G': 'GHOST WALL (SPOOKY)',
                        'I': 'ICE WALL (ZAPPY)', 'l': 'LAVA (CHILLY)'}.get(t['gate'], 'BARRIER')}[kind]
        col = {'lock': (255, 210, 80), 'bomb': (180, 180, 200), 'gate': (200, 140, 255)}[kind]
        label(surf, txt, int(mx), int(my) - 10, col, scale=2)
    ex, ey = px(*t['entry'], ox, oy)
    label(surf, 'ENTRANCE / STAIRS OUT', ex, ey + 18, (160, 255, 190), scale=2)
    gid = world.GUARDIAN_OF[tid]
    region = world.region_at(*t['door'])
    page(t['title'], surf,
         f"DOOR IN {region} - UNSEALED BY BEATING {boss_name(gid)} - {len(t['rooms'])} ROOMS")


def shrine_page():
    x0, y0, x1, y1 = world.SHRINE_RECT
    surf = FULL.subsurface((x0 * TILE, y0 * TILE, (x1 - x0 + 1) * TILE, (y1 - y0 + 1) * TILE)).copy()
    draw_things(surf, world.SHRINE_RECT)
    for name, a in world.ARENAS.items():
        if world.in_rect(a['rect'][0], a['rect'][1], world.SHRINE_RECT):
            kind, rx, ry = a['reward']
            cx, cy = px(rx, ry, x0 * TILE, y0 * TILE)
            label(surf, {'bell': 'GRIMFIN + TIDE BELL', 'key': 'KEY (CLEAR ROOM)',
                         'container': 'HEART SHELL (CLEAR ROOM)'}.get(kind, kind), cx, cy + 14, (255, 230, 150), scale=2)
    label(surf, 'GATE: NEEDS BIG PINCH SIGIL', (47.5 - x0) * TILE + 8, (21 - y0) * TILE - 18, (160, 255, 190), scale=2)
    page("THE SUNKEN SHRINE", pygame.transform.scale2x(surf), "DUNGEON 1 - GRIMFIN GUARDS THE FIRST TIDE BELL")


# ---------------------------------------------------------------- page: story
def story_page():
    lines = [
        ("THE GOAL", (255, 220, 120)),
        ("GRIMFIN AND MURK STOLE THE GOLDEN PEARL. MURK LOCKED IT IN HER PALACE AND", INK),
        ("SEALED THE DOOR WITH SEVEN TIDE BELLS. RING ALL SEVEN, BEAT MURK, WIN.", INK),
        ("", INK),
        ("THE LOOP, SEVEN TIMES", (255, 220, 120)),
        ("1. BEAT THE REGION'S GUARDIAN (A MINI-BOSS)  ->  IT DROPS A SIGIL", INK),
        ("2. THE SIGIL UNSEALS THAT REGION'S DUNGEON", INK),
        ("3. FIND KEYS, PASS THE BARRIER, BEAT THE DUNGEON BOSS, RING THE TIDE BELL (+1 HEART)", INK),
        ("", INK),
        ("SUGGESTED ORDER", (255, 220, 120)),
    ]
    for i, (did, gid) in enumerate(world.QUEST, 1):
        where = 'NORTH OF THE START' if did == 'shrine' else world.region_at(*world.TEMPLES[did]['door'])
        need = ''
        if did != 'shrine' and world.TEMPLES[did]['gate']:
            need = {'K': 'GRUMPY SLAP', 'R': 'BOMBS', 'G': 'SPOOKY FORM', 'I': 'ZAPPY FORM',
                    'l': 'CHILLY FORM'}[world.TEMPLES[did]['gate']]
            need = '  - NEEDS ' + need
        boss = 'GRIMFIN' if did == 'shrine' else boss_name(world.TEMPLES[did]['boss'])
        lines.append((f"{i}. {boss_name(gid)} -> {NAME[did]} ({where}) -> {boss}{need}", INK))
    lines += [
        ("8. MURK PALACE OPENS (SUNKEN CITY: NEEDS SPOOKY FOR THE GHOST WALL, GLOWY HELPS IN THE DARK)", INK),
        ("   -> BEAT MURK -> GOLDEN PEARL -> VICTORY. THEN: DEEP TIDE (HARDER REPLAY)", INK),
        ("", INK),
        ("SIDE GUARDIANS", (255, 220, 120)),
        ("CAPTAIN CLAW (SHIP GRAVEYARD), HOLLOW WARDEN (SUNKEN CITY), STORM GULL (SKY):", INK),
        ("EACH HOARDS A HEART SHELL AND SAYS SOMETHING ABOUT MURK.", INK),
        ("", INK),
        ("GETTING STRONGER", (255, 220, 120)),
        ("TRIALS (41 PORTALS) -> SPIRIT PEARLS -> 3 AT THE ALTAR -> A NEW FORM (NEEDED FOR BARRIERS)", INK),
        ("FUSION MACHINE: TWO FORMS -> ONE STRONGER FORM.  HERMIE'S SHOP: BOMBS, POTIONS, ARMOR...", INK),
        ("HEART SHELLS: OVERWORLD + SIDE GUARDIANS + ONE PER TIDE BELL.  OLD SHELLY ALWAYS KNOWS THE NEXT STEP.", INK),
    ]
    surf = pygame.Surface((1500, len(lines) * 30 + 20))
    surf.fill(BG)
    for i, (l, c) in enumerate(lines):
        label(surf, l, 20, 10 + i * 30, c, scale=2, center=False, box=False)
    page("STORY AND PROGRESSION", surf)


# ---------------------------------------------------------------- page: creatures
def creatures_page():
    rows = []
    for kind, cls in entities.ENEMY_TYPES.items():
        if kind in ('shark', 'murk'):
            continue
        if kind in entities.CRITTERS:
            c = entities.CRITTERS[kind]
            rows.append((sprite(kind), f"{c['name']}  HP {c['hp']}  DMG {c['dmg']}  - {c['region']}", c['doc']))
            continue
        doc = (cls.__doc__ or '').strip().split('\n')[0]
        where = CREATURE_OF.get(kind, 'EVERYWHERE')
        rows.append((sprite(kind), f"{kind.upper()}  HP {cls.max_hp}  DMG {cls.damage}  - {where}", doc))
    rows.append((None, "", ""))
    for bid, st in entities.MINIBOSS_STYLES.items():
        role = ('GUARDIAN - SIGIL FOR ' + NAME[world.SIGIL_OF[bid]]) if bid in world.SIGIL_OF else \
            ('TEMPLE BOSS' if bid in [t['boss'] for t in world.TEMPLES.values()] else
             'GUARDIAN - SPIRIT PEARL' if bid in world.NEW_WORLD_GUARDIANS else 'GUARDIAN - HEART SHELL')
        where = next((x for b, *_r in world.MINIBOSSES if b == bid for x in [world.region_at(*_r)]), '')
        role += f"  ({where})" if where and 'TEMPLE' not in role else ''
        rows.append((gfx.tint(sprite(st['base']), st['tint']), f"{st['name']}  HP {st['hp']}", role))
    half = (len(rows) + 1) // 2
    surf = pygame.Surface((1800, half * 40 + 20))
    surf.fill(BG)
    for i, (img, a, b) in enumerate(rows):
        y = 10 + (i % half) * 40
        x_off = 0 if i < half else 900
        if img is not None:
            blit_c(surf, img, 30 + x_off, y + 14, 2)
        label(surf, a, 64 + x_off, y + 2, (255, 220, 120), scale=2, center=False, box=False)
        label(surf, b.upper()[:80], 64 + x_off, y + 22, (200, 210, 240), scale=1, center=False, box=False)
    page("CREATURES AND BOSSES", surf, "HP AND DAMAGE ARE BASE VALUES - THEY GROW IN LATER REGIONS AND TEMPLES")


def _unused_creature_rows(surf, rows):
    for i, (img, a, b) in enumerate(rows):
        y = 10 + i * 40
        if img is not None:
            blit_c(surf, img, 30, y + 14, 2)
        label(surf, a, 64, y + 2, (255, 220, 120), scale=2, center=False, box=False)
        label(surf, b.upper()[:110], 64, y + 22, (200, 210, 240), scale=1, center=False, box=False)
    page("CREATURES AND BOSSES", surf, "HP AND DAMAGE ARE BASE VALUES - THEY GROW IN LATER REGIONS AND TEMPLES")


# ---------------------------------------------------------------- page: forms and fusions
def forms_page():
    import forms
    base = forms.BASE
    cell = 64
    surf = pygame.Surface((cell * (len(base) + 1) + 20, cell * (len(base) + 1) + 20 + 40 * 11))
    surf.fill(BG)
    for i, f in enumerate(base):
        img = gfx.OCTO[f]['down'][0]
        blit_c(surf, img, cell * (i + 1) + cell // 2 + 10, cell // 2 + 4, 2)
        blit_c(surf, img, cell // 2 + 10, cell * (i + 1) + cell // 2 + 4, 2)
        label(surf, forms.NAMES[f][:7], cell * (i + 1) + cell // 2 + 10, cell - 10, INK, scale=1, box=False)
    for i, a in enumerate(base):
        for j, b in enumerate(base):
            if i == j:
                continue
            fid = forms.fusion_of(a, b)
            d = forms.FUSIONS[fid]
            x, y = cell * (j + 1) + 10, cell * (i + 1) + 4
            pygame.draw.rect(surf, forms.ELEMENTS[d['element']][2], (x + 2, y + 2, cell - 4, cell - 4), 1)
            label(surf, d['name'], x + cell // 2, y + 14, INK, scale=1, box=False)
            label(surf, d['label'], x + cell // 2, y + 30, forms.ELEMENTS[d['element']][2], scale=1, box=False)
    y = cell * (len(base) + 1) + 30
    label(surf, "BASE FORMS: Z ATTACK - STRENGTH", 20, y, (255, 220, 120), scale=2, center=False, box=False)
    for k, f in enumerate(base):
        yy = y + 30 + (k % 10) * 36
        xx = 20 + (k // 10) * (surf.get_width() // 2)
        label(surf, f"{forms.NAMES[f]}: {forms.ATTACKS[f]} - {forms.STRENGTHS[f][0]}", xx, yy, INK, scale=2,
              center=False, box=False)
    page("FORMS AND ALL 190 FUSIONS", surf, "ROW + COLUMN = THE FUSED FORM, ITS ATTACK SHAPE, AND ITS ELEMENT COLOUR")


# ---------------------------------------------------------------- PDF (JPEG pages, no extra libraries)
def write_pdf(path, images):
    objs = []

    def add(b):
        objs.append(b)
        return len(objs)
    kids = []
    pages_id = 2 + 0       # placeholder, fixed below
    add(b'')               # 1: catalog
    add(b'')               # 2: pages
    for jpg, (w, h) in images:
        pw, ph = 612, 612 * h / w            # every page 8.5 inches wide
        img = add(b'<< /Type /XObject /Subtype /Image /Width %d /Height %d /ColorSpace /DeviceRGB '
                  b'/BitsPerComponent 8 /Filter /DCTDecode /Length %d >>\nstream\n' % (w, h, len(jpg))
                  + jpg + b'\nendstream')
        content = b'q %.2f 0 0 %.2f 0 0 cm /Im0 Do Q' % (pw, ph)
        cs = add(b'<< /Length %d >>\nstream\n' % len(content) + content + b'\nendstream')
        pg = add(b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %.2f %.2f] /Resources << /XObject << /Im0 %d 0 R >> >> '
                 b'/Contents %d 0 R >>' % (pw, ph, img, cs))
        kids.append(pg)
    objs[0] = b'<< /Type /Catalog /Pages 2 0 R >>'
    objs[1] = b'<< /Type /Pages /Kids [%s] /Count %d >>' % (b' '.join(b'%d 0 R' % k for k in kids), len(kids))
    out = bytearray(b'%PDF-1.4\n')
    offs = []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += b'%d 0 obj\n' % i + o + b'\nendobj\n'
    xref = len(out)
    out += b'xref\n0 %d\n0000000000 65535 f \n' % (len(objs) + 1)
    for o in offs:
        out += b'%010d 00000 n \n' % o
    out += b'trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (len(objs) + 1, xref)
    with open(path, 'wb') as f:
        f.write(out)


def main():
    story_page()
    world_page('sea')
    shrine_page()
    for tid in world.TEMPLES:
        temple_page(tid)
    world_page('sky')
    world_page('land')
    world_page('under')
    trials_page()
    forms_page()
    creatures_page()
    pics = os.path.join(OUT, 'layout')
    os.makedirs(pics, exist_ok=True)
    images = []
    for i, (title, surf) in enumerate(PAGES, 1):
        slug = ''.join(c if c.isalnum() else '_' for c in title.lower()).strip('_')
        png = os.path.join(pics, f"{i:02d}_{slug}.png")
        pygame.image.save(surf, png)
        jpg = png[:-4] + '.tmp.jpg'
        pygame.image.save(surf, jpg)
        with open(jpg, 'rb') as f:
            images.append((f.read(), surf.get_size()))
        os.remove(jpg)
        print("wrote", os.path.relpath(png, ROOT))
    write_pdf(os.path.join(OUT, 'layout.pdf'), images)
    print("wrote docs/layout.pdf")


if __name__ == '__main__':
    main()
