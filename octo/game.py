"""Game loop and state machine: one big level with a following camera."""
import asyncio
import json
import math
import os
import random
import sys

import pygame

import forms
import gfx
import sound
import world
from title import TitleScene
from touch import TouchControls, touch_device
from entities import (Altar, DIRS, ENEMY_TYPES, FusionMachine, MiniBoss, Patroller, Thief, make_enemy, HERMIE_TALK, MAX_BOMBS, SHELLY_TALK, SHOP_WARES, Bubble,
                      EnemyShot, Hermie, Jelly, Particle, Pickup, Player, Puff, Shelly, Urchin)
from settings import SAVE_SLOT, FPS, HUD_H, PLAY_H, PLAY_W, SCREEN_H, SCREEN_W, TILE
from world import ARENAS, Level

DIR_KEYS = {
    pygame.K_UP: 'up', pygame.K_w: 'up',
    pygame.K_DOWN: 'down', pygame.K_s: 'down',
    pygame.K_LEFT: 'left', pygame.K_a: 'left',
    pygame.K_RIGHT: 'right', pygame.K_d: 'right',
}
ACTION_KEYS = {pygame.K_z, pygame.K_SPACE, pygame.K_j}
FLIP_KEYS = {pygame.K_x, pygame.K_k, pygame.K_RSHIFT}
SAVE_KEYS = {pygame.K_LSHIFT}
INK_MODE_KEYS = {pygame.K_c, pygame.K_l}
JET_KEYS = {pygame.K_v}
PAUSE_KEYS = {pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_p, pygame.K_ESCAPE}
WARP_KEYS = {pygame.K_t}
FORM_KEYS = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2, pygame.K_4: 3, pygame.K_5: 4,
             pygame.K_6: 5, pygame.K_7: 6, pygame.K_8: 7, pygame.K_9: 8, pygame.K_0: 9}
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAVE_PATH = os.path.join(_ROOT, f'savegame_{SAVE_SLOT}.json')     # one save per version
LEGACY_SAVE_PATH = os.path.join(_ROOT, 'savegame.json')            # saves from before versions existed
WEB = sys.platform == 'emscripten'      # running in a browser (pygbag build)
WEB_SAVE_KEY = f'legend_of_octo_save_{SAVE_SLOT}'
LEGACY_WEB_SAVE_KEY = 'legend_of_octo_save'


def _storage():
    import platform                     # pygbag's platform module exposes the browser window
    return platform.window.localStorage


def save_exists():
    if WEB:
        try:
            return bool(_storage().getItem(WEB_SAVE_KEY) or _storage().getItem(LEGACY_WEB_SAVE_KEY))
        except Exception:
            return False
    return os.path.exists(SAVE_PATH) or os.path.exists(LEGACY_SAVE_PATH)


def write_save(text):
    if WEB:
        _storage().setItem(WEB_SAVE_KEY, text)
    else:
        with open(SAVE_PATH, 'w') as f:
            f.write(text)


def read_save():
    if WEB:
        text = _storage().getItem(WEB_SAVE_KEY) or _storage().getItem(LEGACY_WEB_SAVE_KEY)
        if not text:
            raise OSError("no saved game")
        return str(text)
    path = SAVE_PATH if os.path.exists(SAVE_PATH) else LEGACY_SAVE_PATH
    with open(path) as f:
        return f.read()


def quit_game():
    if WEB:
        return                          # a browser tab can't close itself; just keep running
    pygame.quit()
    sys.exit()
BOMB_KEYS = {pygame.K_b}
MAP_KEYS = {pygame.K_m}
FORMS_KEYS = {pygame.K_f}
CONFIRM_KEYS = {pygame.K_RETURN, pygame.K_KP_ENTER}

AREA_INFO = {
    'overworld': {'name': 'CORAL REEF', 'music': 'reef'},
    'dungeon': {'name': 'SUNKEN SHRINE', 'music': 'shrine'},
    'trial': {'name': 'TRIAL', 'music': 'trial'},
    'sky': {'name': 'SKY ISLANDS', 'music': 'sky'},
}
FORM_COLORS = {'zap': (250, 204, 40), 'ice': (184, 228, 255), 'ghost': (150, 100, 222),
               'bubble': (255, 150, 200), 'spiky': (250, 130, 40), 'glow': (80, 230, 150),
               'air': (230, 238, 250)}
FORM_BOX = {'blue': (30, 60, 160), 'mad': (44, 44, 56), 'zap': (150, 110, 10), 'ice': (70, 130, 190),
            'ghost': (70, 40, 120), 'bubble': (170, 70, 120), 'spiky': (160, 70, 10), 'glow': (20, 120, 80),
            'air': (110, 130, 160)}
FORM_LABEL = {'mad': "SLAP", 'zap': "ZAP", 'ice': "ICE", 'ghost': "WISP", 'bubble': "BUBBLE",
              'spiky': "SPINES", 'glow': "FLASH", 'air': "FOG"}
# per-theme screen tint (colour, alpha) and floating particles
THEME_FX = {
    'abyss': ((0, 4, 30), 80, None), 'frost': ((200, 230, 255), 36, 'snow'),
    'vents': ((120, 20, 0), 46, 'embers'), 'city': ((10, 0, 30), 40, 'dust'),
    'kelp': ((0, 40, 10), 30, None), 'garden': ((255, 120, 170), 18, None),
    'lagoon': ((120, 230, 255), 22, None), 'wreck': ((40, 30, 10), 40, 'dust'),
    'sky': ((255, 250, 220), 20, 'wind'),
}
THEME_MINI = {'reef': (196, 178, 128), 'kelp': (160, 170, 110), 'garden': (226, 186, 170),
              'lagoon': (230, 224, 200), 'abyss': (100, 106, 142), 'wreck': (140, 130, 108),
              'frost': (220, 234, 244), 'vents': (90, 74, 72), 'city': (120, 122, 142)}
FORM_INFO = {
    'zap': ["YOU UNLOCKED ZAPPY OCTO!", "PRESS X TO CYCLE YOUR FORMS. ZAPPY'S Z SENDS OUT A SHOCK RING "
            "THAT HITS EVERYTHING AROUND YOU - EVEN URCHINS AND JELLIES - AND FRIES ENEMY SHOTS."],
    'ice': ["YOU UNLOCKED CHILLY OCTO!", "PRESS X TO CYCLE YOUR FORMS. CHILLY'S Z FIRES AN ICE SHARD THAT "
            "FREEZES ENEMIES SOLID. FROZEN ENEMIES CAN'T HURT YOU."],
    'ghost': ["YOU UNLOCKED SPOOKY OCTO!", "PRESS X TO CYCLE YOUR FORMS. SPOOKY'S Z RELEASES TWO WISPS THAT "
              "DRIFT THROUGH WALLS AND HUNT DOWN ENEMIES. SPOOKY OCTO CAN ALSO SLIP THROUGH GHOSTLY PURPLE WALLS."],
    'bubble': ["YOU UNLOCKED BUBBLY OCTO!", "BUBBLY'S Z BLOWS A BUBBLE SHIELD: NOTHING CAN HURT YOU FOR A FEW "
               "SECONDS, AND ENEMIES THAT BUMP INTO IT GET STUNG."],
    'spiky': ["YOU UNLOCKED SPIKY OCTO!", "SPIKY'S Z FLINGS SPINES IN ALL EIGHT DIRECTIONS AT ONCE."],
    'glow': ["YOU UNLOCKED GLOWY OCTO!", "GLOWY LIGHTS UP DARK PLACES LIKE THE SUNKEN CITY. ITS Z IS A "
             "BLINDING FLASH THAT STUNS EVERY ENEMY ON SCREEN."],
    'air': ["YOU UNLOCKED AIRY OCTO!", "AIRY'S Z WRAPS YOU IN A CLOUD OF FOG FOR FIVE SECONDS. ENEMIES LOSE "
            "SIGHT OF YOU AND ATTACK THE SPOT WHERE YOU VANISHED. SWITCH FORMS INSIDE THE FOG TO STRIKE UNSEEN!"],
}
# the newer base forms (taught by the temple altar)
FORM_COLORS.update({'blue': (70, 120, 230), 'mad': (60, 60, 72), 'magnet': (230, 70, 70), 'clammy': (240, 180, 150), 'starry': (255, 220, 90),
                    'wobbly': (230, 140, 240), 'stony': (150, 145, 135)})
FORM_BOX.update({'magnet': (140, 30, 40), 'clammy': (150, 100, 80), 'starry': (30, 30, 100),
                 'wobbly': (130, 60, 150), 'stony': (80, 76, 70)})
FORM_LABEL.update({'magnet': "PULSE", 'clammy': "SHELL", 'starry': "STARS", 'wobbly': "MINES", 'stony': "ROCK"})
_NEW_ATTACK_TEXT = {
    'magnet': "MAGNETY'S Z SENDS OUT A MAGNET PULSE: IT YANKS ENEMIES IN, STUNS THEM, AND PULLS EVERY PEARL "
              "AND HEART ON SCREEN STRAIGHT TO YOU.",
    'clammy': "CLAMMY'S Z THROWS A SPINNING SHELL THAT FLIES OUT AND COMES BACK, HITTING ENEMIES BOTH WAYS.",
    'starry': "STARRY'S Z LAUNCHES THREE SEEKER STARS THAT CURVE TOWARDS THE NEAREST ENEMIES.",
    'wobbly': "WOBBLY'S Z DROPS A STING MINE (UP TO THREE). ENEMIES THAT BUMP INTO ONE GET BLASTED.",
    'stony': "STONY'S Z ROLLS A BOULDER THAT CRUSHES EVERYTHING IN ITS PATH AND CRACKS ROCK WALLS.",
}
for _f, _t in _NEW_ATTACK_TEXT.items():
    FORM_INFO[_f] = [f"YOU LEARNED {forms.NAMES[_f]} OCTO!", _t,
                     f"STRENGTH - {forms.STRENGTHS[_f][0]}: {forms.STRENGTHS[_f][1]}"]
# every fused form (the Fusion Machine can make one from any two base forms)
for _f, _d in forms.FUSIONS.items():
    _a, _b = _d['parents']
    _ca, _cb = FORM_COLORS.get(_a, (200, 200, 200)), FORM_COLORS.get(_b, (200, 200, 200))
    FORM_COLORS.setdefault(_f, tuple((x + y) // 2 for x, y in zip(_ca, _cb)))
    _ba, _bb = FORM_BOX.get(_a, (60, 60, 90)), FORM_BOX.get(_b, (60, 60, 90))
    FORM_BOX.setdefault(_f, tuple((x + y) // 2 for x, y in zip(_ba, _bb)))
    FORM_LABEL[_f] = _d['label']
    FORM_INFO[_f] = [f"THE MACHINE WHIRS AND BUBBLES... YOU MADE {_d['name']} OCTO!",
                     f"{_d['attack']}: {_d['desc']}",
                     f"STRENGTH - {forms.STRENGTHS[_f][0]}: {forms.STRENGTHS[_f][1]}"]
CLAM_HP = 12
ALTAR_FORMS = forms.ALTAR_FORMS        # what the temple altar teaches
FUSE_KEYS_CLOSE = {pygame.K_ESCAPE, pygame.K_t, pygame.K_m, pygame.K_x, pygame.K_p}

MINIMAP_COLORS = {
    '.': (196, 178, 128), ',': (176, 172, 112), '#': (86, 90, 128), 'C': (226, 110, 100),
    'K': (50, 150, 80), '=': (72, 82, 132), 'd': (100, 106, 142), 'W': (30, 34, 64), 'S': (120, 120, 140),
    'L': (220, 170, 40), 'X': (150, 150, 170), 'R': (86, 90, 128),
    'I': (170, 220, 255), 'G': (150, 100, 220), 'l': (240, 110, 30),
    'P': (150, 128, 92), 'Q': (184, 162, 118), 'H': (196, 176, 132),
}
MINIMAP_SIZE = (52, 26)


def tile_to_px(tx, ty):
    """Tile coords of a 16px sprite's centre -> its top-left pixel."""
    return tx * TILE + TILE / 2 - 8, ty * TILE + TILE / 2 - 8


class Game:
    def __init__(self):
        problems = world.validate()
        if problems:
            raise SystemExit("Map errors:\n  " + "\n  ".join(problems))
        pygame.init()
        pygame.display.set_caption("Legend of Octo")
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), 0 if WEB else pygame.SCALED)
        gfx.load()
        sound.init()
        self.clock = pygame.time.Clock()
        self.play_surf = pygame.Surface((PLAY_W, PLAY_H))
        self.rays = self._make_rays()
        self.title_bg = self._make_gradient((10, 30, 90), (2, 8, 30))
        self.title_scene = TitleScene()
        self.display = self.screen
        self.touch = TouchControls(self)
        if touch_device():
            self.touch.activate()
        self.title_sel = 0
        self.state = 'title'
        sound.music('title')
        self.t = 0
        self.held = []
        self.bubbles = []
        self.shake = 0
        self.banner_t = 0
        self.area = 'overworld'
        self.region = 'CORAL REEF'
        self.abyss_veil = pygame.Surface((PLAY_W, PLAY_H))
        self.abyss_veil.fill((0, 4, 30))
        self.abyss_veil.set_alpha(80)
        self.player = None
        self.level = None
        self.trial = None
        self.flash_t = 0
        self.glow_flash = 0
        self.motes = []
        self.theme_veil = (None, None)
        self.light_mask = (0, None)

    # ======================================================================
    # setup
    # ======================================================================

    def _make_gradient(self, top, bottom):
        s = pygame.Surface((SCREEN_W, SCREEN_H))
        for y in range(SCREEN_H):
            k = y / SCREEN_H
            c = tuple(int(a + (b - a) * k) for a, b in zip(top, bottom))
            pygame.draw.line(s, c, (0, y), (SCREEN_W, y))
        return s

    def _make_rays(self):
        s = pygame.Surface((PLAY_W + 120, PLAY_H), pygame.SRCALPHA)
        for x0, w in ((20, 26), (110, 14), (170, 34), (300, 20)):
            pygame.draw.polygon(s, (255, 255, 230, 20),
                                [(x0, 0), (x0 + w, 0), (x0 + w - 70, PLAY_H), (x0 - 70, PLAY_H)])
        return s

    def new_game(self):
        self.player = Player(0, 0)
        self.opened = set()
        self.cleared = set()
        self.collected = set()
        self.flags = {}
        self.frames = 0
        self.level = Level()
        lv = self.level
        self.seen = [[False] * lv.w for _ in range(lv.h)]
        self.minimap = pygame.Surface((lv.w, world.WORLD_H))
        self.minimap.fill((0, 0, 0))
        self.spawns = []
        for kind, tx, ty in world.ENEMIES:
            x, y = tile_to_px(tx, ty)
            self.spawns.append({'kind': kind, 'x': x, 'y': y, 'killed': False, 'inst': None,
                                'arena': world.arena_of(int(tx), int(ty))})
        for bid, tx, ty in world.MINIBOSSES:
            x, y = tile_to_px(tx, ty)
            self.spawns.append({'kind': 'mini:' + bid, 'x': x, 'y': y, 'killed': False, 'inst': None,
                                'arena': None})
        self.enemies, self.shots, self.pickups, self.effects = [], [], [], []
        for i, (kind, tx, ty) in enumerate(world.ITEMS):
            self.place_item(kind, tx, ty, ('item', i))
        _, tx, ty = world.NPC
        hx, hy = world.SHOPKEEPER
        mx, my = world.FUSION_MACHINE
        ax, ay = world.ALTAR
        self.npcs = [Shelly(tx * TILE, ty * TILE), Hermie(hx * TILE, hy * TILE), FusionMachine(mx * TILE, my * TILE),
                     Altar(ax * TILE, ay * TILE)]
        self.bought = set()
        self.shop_focus = None
        self.trial = None
        self.trials_done = set()
        self.portal_armed = True
        self.geyser_armed = True
        self.wares = []
        for i, ware in enumerate(SHOP_WARES):
            cx = 27 * TILE + 11 + i * 18
            cy = world.SHOP_ROW * TILE + 8
            self.wares.append((ware, pygame.Rect(cx - 7, cy - 7, 14, 14)))
        lv.blockers = [n.rect for n in self.npcs]
        self.active_arena = None
        self.checkpoint = world.START
        self.banner_t = 0
        self.respawn_player()
        self.area = self.region = None
        self.update_area()
        self.banner_t = 0
        self.state = 'play'
        self.say([SHELLY_TALK[0], SHELLY_TALK[1],
                  "COME TALK TO ME (PRESS Z NEXT TO ME) IF YOU NEED MORE ADVICE."])

    def respawn_player(self):
        p = self.player
        p.x, p.y = tile_to_px(*self.checkpoint)
        p.facing = 'up'
        p.invuln = p.knock_t = p.attack_t = p.flip_t = 0
        self.update_camera()

    def place_item(self, kind, tx, ty, item_id=None):
        p = Pickup(0, 0, kind, item_id)
        w, h = p._img().get_size()
        p.x = tx * TILE + TILE / 2 - w / 2
        p.y = ty * TILE + TILE / 2 - h / 2
        self.pickups.append(p)
        return p

    # ======================================================================
    # helpers used by entities
    # ======================================================================

    def say(self, pages):
        self.dialog = {'pages': pages, 'i': 0, 'chars': 0.0, 'back': 'play'}
        self.state = 'dialog'

    def burst(self, center, color, n=8):
        cx, cy = center
        for i in range(n):
            a = i / n * math.tau
            self.effects.append(Particle(cx, cy, math.cos(a) * 1.6, math.sin(a) * 1.6, color, 16))

    def spark(self, center):
        cx, cy = center
        for _ in range(6):
            self.effects.append(Particle(cx, cy, random.uniform(-2, 2), random.uniform(-2, 2),
                                         (255, 255, 200), 10))

    def splat(self, center, color):
        cx, cy = center
        for _ in range(5):
            self.effects.append(Particle(cx, cy, random.uniform(-1.2, 1.2), random.uniform(-1.2, 1.2),
                                         color, 14, size=2))

    def miniboss_defeated(self, boss):
        if getattr(boss, 'in_trial', False):          # a trial duel, not the region's guardian
            self.burst(boss.rect.center, (255, 220, 120), 20)
            return
        beaten = self.flags.setdefault('minis', [])
        if boss.bid not in beaten:
            beaten.append(boss.bid)
        cx, cy = boss.rect.center
        for i, kind in enumerate(('bluepearl', 'bluepearl', 'bluepearl', 'heart', 'heart')):
            a = i / 5 * math.tau
            it = Pickup(0, 0, kind, life=900)
            w, h = it._img().get_size()
            it.x, it.y = cx + math.cos(a) * 14 - w / 2, cy + math.sin(a) * 14 - h / 2
            self.pickups.append(it)
        self.burst((cx, cy), (255, 220, 120), 20)
        self.toast = (f"{boss.name} DEFEATED!  {len(beaten)}/{len(world.MINIBOSSES)}", 180)

    def drop_loot(self, center, chance=1.0):
        if self.trial:
            chance *= 0.5           # trials are meant to be hard
        chance *= self.player.stat('luck', 1.0)
        r = random.random() / chance
        kind = None
        if r < 0.30:
            kind = 'pearl'
        elif r < 0.36:
            kind = 'bluepearl'
        elif r < 0.44:
            kind = 'heart' if self.player.hp < self.player.max_hp else 'pearl'
        elif r < 0.58:
            kind = 'shrimp' if self.player.hp < self.player.max_hp else 'pearl'
        if kind:
            p = Pickup(0, 0, kind, life=480)
            w, h = p._img().get_size()
            p.x, p.y = center[0] - w / 2, center[1] - h / 2
            self.pickups.append(p)

    def nearest_enemy(self, pos, max_dist):
        best, best_d = None, max_dist
        for e in self.enemies:
            if not e.active or not self.view_rect.colliderect(e.rect):
                continue
            ex, ey = e.rect.center
            d = math.hypot(ex - pos[0], ey - pos[1])
            if d <= best_d:
                best, best_d = e, d
        return best

    def unlock_at(self, tx, ty):
        lv = self.level
        locks = lv.flood(tx, ty, 'L')
        for x, y in locks:
            lv.set_tile(x, y, world.floor_for(x, y))
            self.burst((x * TILE + 8, y * TILE + 8), (240, 200, 60), 10)
        self.opened.update(locks)
        sound.play('door')

    def blast_tiles(self, cx, cy, radius):
        """A bomb went off: crack open 'R' rock and shred kelp nearby."""
        lv = self.level
        for ty in range(int(cy - radius) // TILE, int(cy + radius) // TILE + 1):
            for tx in range(int(cx - radius) // TILE, int(cx + radius) // TILE + 1):
                ch = lv.tile(tx, ty)
                if ch not in ('R', 'K'):
                    continue
                if math.hypot(tx * TILE + 8 - cx, ty * TILE + 8 - cy) > radius + 6:
                    continue
                lv.set_tile(tx, ty, world.floor_for(tx, ty))
                self.opened.add((tx, ty))
                if ch == 'R':
                    sound.play('door')
                for _ in range(10):
                    self.effects.append(Particle(tx * TILE + 8, ty * TILE + 8,
                                                 random.uniform(-2, 2), random.uniform(-2.5, 0.5),
                                                 (120, 126, 168) if ch == 'R' else (46, 156, 78),
                                                 24, grav=0.1, size=2))

    # ---- save / load -----------------------------------------------------
    def save_game(self):
        p = self.player
        if self.trial:
            px, py = world.TRIALS[self.trial['name']]['portal']
            pos = (px, py + 1)
        elif self.active_arena:
            pos = self.checkpoint
        else:
            pos = ((p.x + 8) / TILE - 0.5, (p.y + 8) / TILE - 0.5)
        data = {
            'version': 1,
            'pos': pos,
            'player': {k: getattr(p, k) for k in ('hp', 'max_hp', 'pearls', 'keys', 'bombs', 'mood', 'ink_mode',
                                                       'sphere', 'spirit')},
            'items': sorted(p.items), 'forms': p.forms,
            'opened': sorted(self.opened), 'cleared': sorted(self.cleared),
            'collected': [list(i) for i in self.collected], 'bought': sorted(self.bought),
            'trials_done': sorted(self.trials_done), 'checkpoint': list(self.checkpoint),
            'flags': self.flags, 'frames': self.frames,
            'seen': [''.join('1' if c else '0' for c in row) for row in self.seen],
        }
        try:
            write_save(json.dumps(data))
            self.has_save = True
            self.pause_msg = 'GAME SAVED!'
            sound.play('key')
        except Exception as e:
            self.pause_msg = 'COULD NOT SAVE'
            print("Save failed:", e)
        self.toast = (self.pause_msg, 100)

    def load_game(self):
        try:
            data = json.loads(read_save())
        except Exception as e:
            print("Load failed:", e)
            sound.play('nope')
            return
        self.new_game()
        p = self.player
        for k, v in data['player'].items():
            setattr(p, k, v)
        p.items = set(data['items'])
        p.forms = list(data['forms'])
        if p.mood not in p.forms:
            p.mood = 'blue'
        self.bought = set(data['bought'])
        self.trials_done = set(data['trials_done'])
        self.flags = data['flags']
        self.frames = data['frames']
        self.checkpoint = tuple(data['checkpoint'])
        for tx, ty in data['opened']:
            if self.level.tile(tx, ty) in world.OPENABLE:
                self.level.set_tile(tx, ty, world.floor_for(tx, ty))
            self.opened.add((tx, ty))
        self.cleared = set(data['cleared'])
        for sp in self.spawns:
            if sp['arena'] in self.cleared:
                sp['killed'] = True
        self.collected = {tuple(i) for i in data['collected']}
        self.pickups = [i for i in self.pickups if i.item_id not in self.collected]
        for name in self.cleared:
            if ('reward', name) not in self.collected:
                kind, tx, ty = ARENAS[name]['reward']
                self.place_item(kind, tx, ty, ('reward', name))
        for y, row in enumerate(data.get('seen', [])[:len(self.seen)]):
            for x, c in enumerate(row[:len(self.seen[y])]):
                self.seen[y][x] = c == '1'
        p.x, p.y = tile_to_px(*data['pos'])
        if self.level.blocked(p.rect, 'player'):     # the map changed under an old save
            p.x, p.y = tile_to_px(*world.START)
        p.facing = 'down'
        self.update_camera()
        self.area = self.region = None
        self.update_area()
        self.state = 'play'
        self.say(["WELCOME BACK, OCTO!"])

    # ---- warping between completed trial portals ---------------------------
    def warp_spots(self):
        spots = [('OCTO TEMPLE', world.START)]
        for name, t in world.TRIALS.items():
            if name in self.trials_done:
                px, py = t['portal']
                spots.append((t['title'].replace('TRIAL OF ', '') + ' PORTAL', (px, py + 1)))
        return spots

    # ---- the spirit altar (temple) -------------------------------------------
    ALTAR_COST = 3

    def altar_rows(self):
        rows = [(f, 'owned' if f in self.player.forms else 'ready') for f in ALTAR_FORMS]
        rows.append(('heart', 'ready'))
        return rows

    def open_altar(self):
        self.altar_i = 0
        self.altar_msg = ''
        rows = self.altar_rows()
        for i, (f, status) in enumerate(rows):
            if status == 'ready':
                self.altar_i = i
                break
        self.state = 'altar'
        sound.play('pause')

    def altar_take(self, row):
        f, status = row
        p = self.player
        if status == 'owned':
            self.altar_msg = "YOU ALREADY KNOW THAT FORM."
            sound.play('nope')
        elif p.spirit < self.ALTAR_COST:
            self.altar_msg = f"THE ALTAR NEEDS {self.ALTAR_COST} SPIRIT PEARLS. YOU HAVE {p.spirit}. BEAT TRIALS TO EARN MORE!"
            sound.play('nope')
        else:
            p.spirit -= self.ALTAR_COST
            self.state = 'play'
            sound.play('item')
            if f == 'heart':
                p.max_hp += 2
                p.hp = p.max_hp
                self.burst(p.rect.center, (255, 90, 110), 18)
                self.say(["THE ALTAR GLOWS... YOU GAINED A HEART!"])
            else:
                p.forms.append(f)
                p.next_mood = f
                p.flip_t = 14
                self.burst(p.rect.center, FORM_COLORS[f], 18)
                self.say(["THE ALTAR GLOWS... " + FORM_INFO[f][0]] + FORM_INFO[f][1:])

    def draw_altar(self, scr):
        rows = self.altar_rows()
        p = self.player
        box = pygame.Rect(10, HUD_H + 4, SCREEN_W - 20, PLAY_H - 8)
        self.draw_box(scr, box)
        gfx.text(scr, "SPIRIT ALTAR", SCREEN_W // 2, box.y + 6, (210, 180, 255), center=True)
        gfx.text(scr, f"3 SPIRIT PEARLS EACH - YOU HAVE {p.spirit}", SCREEN_W // 2, box.y + 16,
                 (170, 180, 220), center=True)
        top = max(0, min(self.altar_i - 3, len(rows) - 8))
        for j, (f, status) in enumerate(rows[top:top + 8]):
            i = top + j
            y = box.y + 30 + j * 11
            if i == self.altar_i:
                gfx.text(scr, ">", box.x + 5, y, (255, 220, 120))
            col = (120, 200, 140) if status == 'owned' else (255, 255, 255) if p.spirit >= 3 else (150, 150, 175)
            name = "+1 HEART" if f == 'heart' else gfx.MOOD_NAMES[f]
            gfx.text(scr, name, box.x + 14, y, col)
            if f != 'heart':
                gfx.text(scr, forms.STRENGTHS[f][0], box.x + 14 + 6 * 9, y, (150, 160, 200))
            tag = "OWNED" if status == 'owned' else "3"
            gfx.text(scr, tag, box.right - 6 - gfx.text_width(tag), y, col)
        f, status = rows[self.altar_i]
        info = self.altar_msg or ("ONE MORE HEART OF LIFE." if f == 'heart' else
                                  f"Z: {FORM_LABEL[f]}. {forms.STRENGTHS[f][0]}: {forms.STRENGTHS[f][1]}")
        for j, line in enumerate(gfx.wrap(info, 36)[:2]):
            gfx.text(scr, line, box.x + 8, box.bottom - 33 + j * 10,
                     (255, 220, 120) if self.altar_msg else (200, 210, 240))
        gfx.text(scr, "Z: TAKE   ESC: LEAVE", SCREEN_W // 2, box.bottom - 10, (140, 150, 190), center=True)

    # ---- the Fusion Machine ------------------------------------------------
    def fuse_base(self):
        return [f for f in forms.BASE if f in self.player.forms]

    def open_fuse(self):
        self.fuse_i = 0
        self.fuse_a = None
        self.fuse_msg = ''
        self.state = 'fuse'
        sound.play('pause')

    def fuse_key(self, k):
        base = self.fuse_base()
        n = len(base)
        if k in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s, pygame.K_LEFT, pygame.K_a,
                 pygame.K_RIGHT, pygame.K_d) and n:
            step = {pygame.K_UP: -1, pygame.K_w: -1, pygame.K_DOWN: 1, pygame.K_s: 1,
                    pygame.K_LEFT: -7, pygame.K_a: -7, pygame.K_RIGHT: 7, pygame.K_d: 7}[k]
            self.fuse_i = (self.fuse_i + step) % n
            self.fuse_msg = ''
            sound.play('text')
        elif k in ACTION_KEYS or k in CONFIRM_KEYS:
            if n < 2:
                self.fuse_msg = "YOU NEED AT LEAST TWO FORMS TO FUSE."
                sound.play('nope')
                return
            cur = base[self.fuse_i]
            if self.fuse_a is None:
                self.fuse_a = cur
                sound.play('text')
            elif cur == self.fuse_a:
                self.fuse_a = None
                sound.play('text')
            else:
                self.fuse(self.fuse_a, cur)
        elif k in FUSE_KEYS_CLOSE:
            if self.fuse_a:
                self.fuse_a = None
            else:
                self.state = 'play'
            sound.play('pause')

    def fuse(self, a, b):
        p = self.player
        f = forms.fusion_of(a, b)
        if f in p.forms:
            self.fuse_msg = "YOU ALREADY MADE THAT ONE."
            sound.play('nope')
        elif p.pearls < forms.FUSION_COST:
            self.fuse_msg = f"FUSING COSTS {forms.FUSION_COST} PEARLS. YOU HAVE {p.pearls}."
            sound.play('nope')
        else:
            p.pearls -= forms.FUSION_COST
            p.forms.append(f)
            p.next_mood = f
            p.flip_t = 14
            self.state = 'play'
            sound.play('item')
            self.burst(p.rect.center, FORM_COLORS[f], 18)
            self.say(FORM_INFO[f])

    def draw_fuse(self, scr):
        base = self.fuse_base()
        p = self.player
        box = pygame.Rect(8, HUD_H + 3, SCREEN_W - 16, PLAY_H - 6)
        self.draw_box(scr, box)
        made = sum(1 for f in p.forms if forms.is_fused(f))
        gfx.text(scr, "FUSION MACHINE", SCREEN_W // 2, box.y + 5, (255, 220, 120), center=True)
        gfx.text(scr, f"ANY TWO FORMS - {forms.FUSION_COST} PEARLS - MADE {made}/{len(forms.FUSIONS)}",
                 SCREEN_W // 2, box.y + 15, (170, 180, 220), center=True)
        for i, f in enumerate(base):
            col, row = divmod(i, 7)
            x, y = box.x + 10 + col * 118, box.y + 28 + row * 11
            on = i == self.fuse_i
            picked = f == self.fuse_a
            if on:
                gfx.text(scr, ">", x - 6, y, (255, 220, 120))
            colr = (255, 220, 120) if picked else (255, 255, 255) if on else (170, 175, 205)
            gfx.text(scr, forms.NAMES[f] + (" *" if picked else ""), x + 2, y, colr)
        # preview
        y = box.bottom - 43
        if not base:
            return
        cur = base[self.fuse_i]
        if self.fuse_msg:
            lines = gfx.wrap(self.fuse_msg, 38)
            colr = (255, 220, 120)
        elif self.fuse_a is None:
            lines = ["PICK THE FIRST FORM WITH Z."]
            colr = (200, 210, 240)
        elif cur == self.fuse_a:
            lines = ["NOW PICK A DIFFERENT SECOND FORM."]
            colr = (200, 210, 240)
        else:
            fid = forms.fusion_of(self.fuse_a, cur)
            d = forms.FUSIONS[fid]
            owned = " (MADE)" if fid in p.forms else ""
            lines = [f"{forms.NAMES[self.fuse_a]}+{forms.NAMES[cur]} > {d['name']}{owned}"] + \
                gfx.wrap(f"{d['attack']}: {d['desc']}", 38)
            colr = (200, 210, 240)
        for j, line in enumerate(lines[:3]):
            gfx.text(scr, line, box.x + 6, y + j * 10, (255, 220, 120) if j == 0 and self.fuse_a and not
                     self.fuse_msg else colr)
        gfx.text(scr, "Z: PICK / FUSE   ESC: BACK", SCREEN_W // 2, box.bottom - 9, (140, 150, 190), center=True)

    # ---- choosing a form from the whole list ---------------------------------
    def open_forms(self):
        self.forms_i = max(0, self.player.forms.index(self.player.mood)) if self.player.mood in self.player.forms else 0
        self.state = 'forms'
        sound.play('pause')

    def forms_key(self, k):
        fl = self.player.forms
        if k in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s, pygame.K_LEFT, pygame.K_a,
                 pygame.K_RIGHT, pygame.K_d):
            step = {pygame.K_UP: -2, pygame.K_w: -2, pygame.K_DOWN: 2, pygame.K_s: 2,
                    pygame.K_LEFT: -1, pygame.K_a: -1, pygame.K_RIGHT: 1, pygame.K_d: 1}[k]
            self.forms_i = (self.forms_i + step) % len(fl)
            sound.play('text')
        elif k in ACTION_KEYS or k in CONFIRM_KEYS:
            self.state = 'play'
            self.player.pick_form(self.forms_i)
        elif k in FUSE_KEYS_CLOSE or k in FORMS_KEYS:
            self.state = 'play'
            sound.play('pause')

    def draw_forms(self, scr):
        fl = self.player.forms
        box = pygame.Rect(8, HUD_H + 3, SCREEN_W - 16, PLAY_H - 6)
        self.draw_box(scr, box)
        gfx.text(scr, f"YOUR FORMS ({len(fl)})", SCREEN_W // 2, box.y + 5, (255, 220, 120), center=True)
        rows_shown = 10
        row = self.forms_i // 2
        top = max(0, min(row - rows_shown // 2, (len(fl) + 1) // 2 - rows_shown))
        for i in range(top * 2, min(len(fl), (top + rows_shown) * 2)):
            f = fl[i]
            col, r = i % 2, i // 2 - top
            x, y = box.x + 12 + col * 118, box.y + 17 + r * 11
            on = i == self.forms_i
            pygame.draw.rect(scr, FORM_COLORS.get(f, (200, 200, 200)), (x, y + 1, 5, 5))
            if on:
                gfx.text(scr, ">", x - 8, y, (255, 220, 120))
            cur = f == self.player.mood
            gfx.text(scr, forms.NAMES[f], x + 8, y, (255, 220, 120) if cur else (255, 255, 255) if on else (170, 175, 205))
        f = fl[self.forms_i]
        gfx.text(scr, f"Z: {forms.ATTACKS[f]}", box.x + 6, box.bottom - 22, (200, 210, 240))
        gfx.text(scr, forms.STRENGTHS[f][0], box.x + 6, box.bottom - 10, (150, 160, 200))

    def open_warp(self):
        if self.trial or self.active_arena:
            sound.play('nope')
            return
        if len(self.warp_spots()) < 2:
            sound.play('nope')
            self.say(["FINISH A TRIAL FIRST: COMPLETED TRIAL PORTALS BECOME WARP POINTS (PRESS T)."])
            return
        self.warp_i = 0
        self.state = 'warp'
        sound.play('pause')

    def warp_to(self, spot):
        name, (tx, ty) = spot
        for sp in self.spawns:
            sp['inst'] = None
        self.enemies, self.shots = [], []
        self.pickups = [i for i in self.pickups if i.life is None]
        p = self.player
        p.x, p.y = tile_to_px(tx, ty)
        p.facing = 'down'
        p.knock_t = p.attack_t = p.dash_t = 0
        self.portal_armed = False
        self.geyser_armed = False
        self.flash_t = 20
        sound.play('portal')
        self.update_camera()
        self.area = self.region = None
        self.update_area()
        self.state = 'play'

    def draw_warp(self, scr):
        spots = self.warp_spots()
        show = 10
        top = max(0, min(self.warp_i - show // 2, len(spots) - show))
        box = pygame.Rect(40, HUD_H + 8, SCREEN_W - 80, 30 + min(show, len(spots)) * 12)
        self.draw_box(scr, box)
        gfx.text(scr, "WARP TO...", SCREEN_W // 2, box.y + 8, (255, 220, 120), center=True)
        if top > 0:
            gfx.text(scr, "^", box.right - 12, box.y + 8, (150, 160, 200))
        if top + show < len(spots):
            gfx.text(scr, "V", box.right - 12, box.bottom - 10, (150, 160, 200))
        for i, (name, _) in list(enumerate(spots))[top:top + show]:
            y = box.y + 22 + (i - top) * 12
            if i == self.warp_i:
                gfx.text(scr, ">", box.x + 8, y, (255, 220, 120))
            gfx.text(scr, name, box.x + 18, y, (255, 255, 255) if i == self.warp_i else (170, 170, 190))

    # ---- trials ----------------------------------------------------------
    def room_px(self, name):
        x0, y0, x1, y1 = world.TRIALS[name]['room']
        return pygame.Rect(x0 * TILE, y0 * TILE, (x1 - x0 + 1) * TILE, (y1 - y0 + 1) * TILE)

    def check_portals(self):
        p = self.player
        touching = None
        for name, t in world.TRIALS.items():
            px, py = t['portal']
            r = pygame.Rect(px * TILE + 2, py * TILE + 2, TILE - 4, TILE - 4)
            if r.colliderect(p.rect):
                touching = name
        if touching is None:
            self.portal_armed = True
        elif self.portal_armed and touching not in self.trials_done:
            self.enter_trial(touching)

    def check_geysers(self):
        p = self.player
        tx, ty = p.rect.centerx // TILE, p.rect.centery // TILE
        if self.level.tile(tx, ty) != 'Y':
            self.geyser_armed = True
            return
        if not self.geyser_armed:
            return
        for a, b in world.GEYSERS:
            if (tx, ty) in (a, b):
                dest = b if (tx, ty) == a else a
                going_up = dest == b
                p.sphere = p.SPHERE_MAX if going_up else 0
                p.roll_v = [0.0, 0.0]
                for sp in self.spawns:
                    sp['inst'] = None
                self.enemies, self.shots = [], []
                self.pickups = [i for i in self.pickups if i.life is None]
                p.x, p.y = tile_to_px(dest[0], dest[1] + 1)
                p.facing = 'down'
                p.knock_t = p.attack_t = p.dash_t = 0
                self.geyser_armed = False
                self.flash_t = 20
                sound.play('whoosh')
                self.update_camera()
                self.area = self.region = None
                self.update_area()
                if going_up and not self.flags.get('sky_intro'):
                    self.flags['sky_intro'] = True
                    self.say(["WHOOSH! THE GEYSER BLASTED OCTO RIGHT OUT OF THE SEA, UP TO THE FLOATING SKY ISLANDS!",
                              "OCTO CAN'T BREATHE AIR, SO HE ROLLS AROUND INSIDE A BALL OF SEAWATER. HITS CRACK THE "
                              "BALL INSTEAD OF HURTING YOU, BUT IF IT BREAKS, OCTO TUMBLES BACK DOWN INTO THE SEA!",
                              "JUMP BACK INTO A CLOUD HOLE TO DROP DOWN TO THE SEA ANY TIME."])
                return

    def pop_sphere(self):
        """The water sphere shattered: Octo tumbles out of the sky."""
        p = self.player
        p.tumble = 1
        p.fog_t = p.bubble_t = p.dash_t = p.attack_t = p.knock_t = 0
        cx, cy = p.rect.center
        for i in range(18):
            a = i / 18 * math.tau
            self.effects.append(Particle(cx, cy, math.cos(a) * 2.2, math.sin(a) * 2.2, (120, 190, 255), 30,
                                         grav=0.08, size=2))
        sound.play('boom')
        self.shake = 10

    def update_tumble(self):
        p = self.player
        p.tumble += 1
        for fx in self.effects:
            fx.update(self)
        self.effects = [f for f in self.effects if not f.dead]
        if p.tumble < 80:
            return
        # splash down beside the geyser nearest to where Octo fell
        cx, cy = p.rect.centerx / TILE, p.rect.centery / TILE
        sea, _ = min(world.GEYSERS, key=lambda g: math.hypot(g[1][0] - cx, g[1][1] - cy))
        p.tumble = 0
        p.sphere = 0
        p.roll_v = [0.0, 0.0]
        for sp in self.spawns:
            sp['inst'] = None
        self.enemies, self.shots = [], []
        self.pickups = [i for i in self.pickups if i.life is None]
        p.x, p.y = tile_to_px(sea[0], sea[1] + 1)
        p.facing = 'down'
        p.invuln = 60
        self.geyser_armed = False
        self.flash_t = 20
        self.update_camera()
        self.area = self.region = None
        self.update_area()
        self.burst(p.rect.center, (150, 210, 255), 16)
        sound.play('bubble')
        if not self.flags.get('fell_msg'):
            self.flags['fell_msg'] = True
            self.say(["SPLASH! THE WATER BALL BURST AND OCTO TUMBLED ALL THE WAY BACK DOWN INTO THE SEA.",
                      "RIDE THE GEYSER AGAIN FOR A FRESH BALL OF WATER."])

    def enter_trial(self, name):
        t = world.TRIALS[name]
        sound.play('portal')
        # world enemies go home while Octo is away
        for sp in self.spawns:
            sp['inst'] = None
        self.enemies, self.shots = [], []
        self.pickups = [i for i in self.pickups if i.life is None]
        if self.active_arena:
            self.level.set_doors(self.active_arena, False)
            self.active_arena = None
        x0, y0 = t['room'][:2]
        p = self.player
        p.x, p.y = tile_to_px(x0 + t['entry'][0], y0 + t['entry'][1])
        p.facing = 'up'
        p.knock_t = p.attack_t = p.dash_t = 0
        p.hp = p.max_hp
        self.trial = {'name': name, 't': -120, 'wave': 0, 'got': 0, 'between': 0, 'eye_angle': 0.0,
                      'clam': CLAM_HP}
        self.flash_t = 20
        self.update_camera()
        self.area = self.region = None
        self.update_area()
        self.say([t['title'] + ": " + (t.get('goal_text') or t['goal']),
                  "IF YOU FALL, YOU'LL BE SENT BACK OUTSIDE - YOU CAN ALWAYS TRY AGAIN."])

    def trial_spawn(self, kind, tx, ty):
        x0, y0 = world.TRIALS[self.trial['name']]['room'][:2]
        x, y = tile_to_px(x0 + tx, y0 + ty)
        e = ENEMY_TYPES[kind](x, y)
        e.spawn = {'kind': kind, 'arena': 'trial', 'inst': e, 'killed': False}
        self.enemies.append(e)
        return e

    def update_trial(self):
        tr = self.trial
        t = world.TRIALS[tr['name']]
        tr['t'] += 1
        if tr['t'] < 0:
            if tr['t'] % 40 == 0:
                sound.play('tick')
            return
        kind = t['kind']
        x0, y0 = t['room'][:2]
        p = self.player
        cur = t.get('current')
        if cur and not p.dash_t and not p.roll_t:             # the current keeps pushing Octo
            p.move(cur[0], cur[1], self.level)
            if tr['t'] % 4 == 0:
                rx = random.uniform(x0, x0 + 16) * TILE
                ry = random.uniform(y0, y0 + 11) * TILE
                self.effects.append(Particle(rx, ry, cur[0] * 5, cur[1] * 5, (200, 230, 255), 16))
        if tr['t'] == 0 and kind in ('duel', 'chase', 'defend', 'race'):
            sound.play('roar')
            if kind == 'duel':
                bx, by = t['boss_at']
                e = MiniBoss(t['boss'], *tile_to_px(x0 + bx, y0 + by))
                e.in_trial = True
                e.home = (e.x, e.y)
                e.spawn = {'kind': 'mini', 'arena': 'trial', 'inst': e, 'killed': False}
                self.enemies.append(e)
            elif kind == 'chase':
                tx, ty = t['thief_at']
                e = Thief(*tile_to_px(x0 + tx, y0 + ty))
                e.spawn = {'kind': 'thief', 'arena': 'trial', 'inst': e, 'killed': False}
                self.enemies.append(e)
            elif kind == 'race':
                for i, (px_, py_) in enumerate(t['sentries']):
                    e = Patroller(*tile_to_px(x0 + px_, y0 + py_), speed=t.get('sentry_speed', 1.2) * (1 if i % 2 else -1))
                    e.spawn = {'kind': 'sentry', 'arena': 'trial', 'inst': e, 'killed': False}
                    self.enemies.append(e)
            for ek, gx, gy in t.get('guards', []):
                self.trial_spawn(ek, gx, gy)
        if kind == 'duel':
            if tr['t'] > 0 and not any(isinstance(e, MiniBoss) and not e.dead for e in self.enemies) \
                    and not any(isinstance(f, Puff) and f.loud for f in self.effects):
                self.finish_trial(True)
            return
        if kind == 'chase':
            left = t['time'] * 60 - tr['t']
            if tr['got'] >= 3:
                self.finish_trial(True)
            elif left <= 0:
                self.finish_trial(False, "THE THIEF GOT AWAY!")
            elif left <= 300 and left % 60 == 0:
                sound.play('tick')
            return
        if kind == 'race':
            left = t['time'] * 60 - tr['t']
            gx, gy = t['goal']
            goal = pygame.Rect((x0 + gx) * TILE - 6, (y0 + gy) * TILE - 6, 12, 12)
            if goal.colliderect(p.rect):
                self.finish_trial(True)
            elif left <= 0:
                self.finish_trial(False, "TOO SLOW!")
            elif left <= 300 and left % 60 == 0:
                sound.play('tick')
            return
        if kind == 'defend':
            left = t['time'] * 60 - tr['t']
            cx, cy = (x0 + t['clam_at'][0]) * TILE, (y0 + t['clam_at'][1]) * TILE
            clam = pygame.Rect(cx - 12, cy - 9, 24, 18)
            if tr['t'] > 0 and tr['t'] % t['every'] == 0 and left > 120:
                sx, sy = random.choice(t['spots'])
                e = self.trial_spawn(random.choice(t['raiders']), sx, sy)
                e.goal = (cx, cy)
            for e in self.enemies:
                if e.goal and e.active and e.rect.colliderect(clam):
                    tr['clam'] -= max(1, e.damage)
                    e.dead = True
                    self.effects.append(Puff(e.x, e.y))
                    self.shake = 6
                    sound.play('hurt')
            if tr['clam'] <= 0:
                self.finish_trial(False, "THE CLAM WAS CRACKED!")
            elif left <= 0:
                self.finish_trial(True)
            elif left <= 300 and left % 60 == 0:
                sound.play('tick')
            return
        if tr['t'] == 0:
            sound.play('roar')
            if kind == 'collect':
                x0, y0 = t['room'][:2]
                for ox, oy in t['orbs']:
                    self.place_item('orb', x0 + ox, y0 + oy, None)
            for ek, gx, gy in t.get('guards', []):
                e = self.trial_spawn(ek, gx, gy)
                if t.get('fast'):
                    if hasattr(e, 'vx'):
                        e.vx *= t['fast']
                        e.vy *= t['fast']
                    if hasattr(e, 'speed'):
                        e.speed *= t['fast']
        if kind == 'waves':
            if not self.enemies and not any(isinstance(f, Puff) and f.loud for f in self.effects):
                if tr['between'] == 0:
                    if tr['wave'] >= len(t['waves']):
                        self.finish_trial(True)
                        return
                    tr['between'] = 60 if tr['wave'] else 1
                tr['between'] -= 1
                if tr['between'] == 0:
                    spots = list(t['spots'])
                    random.shuffle(spots)
                    pc = self.player.rect.center
                    x0, y0 = t['room'][:2]
                    spots.sort(key=lambda sp: -math.hypot((x0 + sp[0]) * TILE - pc[0], (y0 + sp[1]) * TILE - pc[1]))
                    for i, ek in enumerate(t['waves'][tr['wave']]):
                        sx, sy = spots[i % len(spots)]
                        self.trial_spawn(ek, sx, sy)
                    tr['wave'] += 1
                    sound.play('shut')
        elif kind == 'collect':
            left = t['time'] * 60 - tr['t']
            if tr['got'] >= len(t['orbs']):
                self.finish_trial(True)
            elif left <= 0:
                self.finish_trial(False, "TIME'S UP!")
            elif left <= 300 and left % 60 == 0:
                sound.play('tick')
        elif kind == 'survive':
            left = t['time'] * 60 - tr['t']
            if left <= 0:
                self.finish_trial(True)
                return
            if left <= 300 and left % 60 == 0:
                sound.play('tick')
            if tr['t'] == 900:          # halfway: a heart floats in to help
                x0, y0 = t['room'][:2]
                self.place_item('heart', x0 + 7.5, y0 + 2, None)
            if t['eyes']:
                self.fire_eyes(tr, t)

    def fire_eyes(self, tr, t):
        """The Trial of Shadows' barrage: a slow spinning ring from the centre, aimed shots from the corners."""
        x0, y0 = t['room'][:2]
        k = tr['t']
        late = k > 60 * 15          # second half gets a little busier
        (cx, cy), corners = t['eyes'][0], t['eyes'][1:]
        cx, cy = (x0 + cx) * TILE, (y0 + cy) * TILE
        if k % (84 if late else 100) == 0:
            n = 6
            tr['eye_angle'] += 0.4
            for i in range(n):
                a = tr['eye_angle'] + i / n * math.tau
                self.shots.append(EnemyShot(cx - 3 + math.cos(a) * 10, cy - 3 + math.sin(a) * 10,
                                            math.cos(a) * 1.1, math.sin(a) * 1.1, 'spine'))
            sound.play('shoot')
        gap = 170 if late else 220
        for i, (ex, ey) in enumerate(corners):
            if (k + i * gap // 4) % gap == 0:
                ex, ey = (x0 + ex) * TILE, (y0 + ey) * TILE
                px, py = self.player.rect.center
                d = math.hypot(px - ex, py - ey) or 1
                self.shots.append(EnemyShot(ex - 3, ey - 3, (px - ex) / d * 1.6, (py - ey) / d * 1.6, 'spine'))

    def finish_trial(self, won, why=None):
        name = self.trial['name']
        t = world.TRIALS[name]
        p = self.player
        self.trial = None
        self.enemies, self.shots = [], []
        self.pickups = [i for i in self.pickups if i.life is None and i.kind != 'orb']
        px, py = t['portal']
        p.x, p.y = tile_to_px(px, py + 1)
        p.facing = 'down'
        p.knock_t = p.attack_t = p.dash_t = 0
        p.invuln = 60
        self.portal_armed = False
        self.flash_t = 20
        self.update_camera()
        self.area = self.region = None
        self.update_area()
        if won:
            first = name not in self.trials_done
            self.trials_done.add(name)
            sound.play('item')
            p.hp = p.max_hp
            self.burst(p.rect.center, (190, 140, 255), 16)
            if first:
                p.spirit += 1
                left = len(world.TRIALS) - len(self.trials_done)
                tip = ("TAKE THEM TO THE ALTAR ON TOP OF THE OCTO TEMPLE TO LEARN A NEW FORM!" if p.spirit >= 3 else
                       f"{3 - p.spirit} MORE AND THE TEMPLE ALTAR WILL TEACH YOU A NEW FORM.")
                self.say([t['title'] + " COMPLETE!  YOU EARNED A SPIRIT PEARL!",
                          f"YOU HAVE {p.spirit} SPIRIT PEARL{'S' if p.spirit != 1 else ''}. " + tip,
                          f"{left} TRIAL{'S' if left != 1 else ''} LEFT TO FIND."])
            else:
                self.say([t['title'] + " COMPLETE AGAIN!", "YOU ALREADY HAVE THIS TRIAL'S SPIRIT PEARL."])
        else:
            p.hp = max(p.hp, max(2, p.max_hp // 2))
            sound.play('warp')
            self.say([(why + " " if why else "") + "TRIAL FAILED... YOU WERE SWEPT BACK OUT OF THE PORTAL.",
                      "STEP BACK INTO THE PORTAL WHENEVER YOU'RE READY TO TRY AGAIN."])

    def shatter_ice(self, cx, cy, radius):
        lv = self.level
        for ty in range(int(cy - radius) // TILE, int(cy + radius) // TILE + 1):
            for tx in range(int(cx - radius) // TILE, int(cx + radius) // TILE + 1):
                if lv.tile(tx, ty) == 'I' and math.hypot(tx * TILE + 8 - cx, ty * TILE + 8 - cy) < radius + 8:
                    lv.set_tile(tx, ty, world.floor_for(tx, ty))
                    self.opened.add((tx, ty))
                    sound.play('tink')
                    for _ in range(8):
                        self.effects.append(Particle(tx * TILE + 8, ty * TILE + 8, random.uniform(-2, 2),
                                                     random.uniform(-2.5, 0.5), (200, 240, 255), 22,
                                                     grav=0.1, size=2))

    def cool_lava(self, tx, ty):
        self.level.set_tile(tx, ty, world.floor_for(tx, ty))
        self.opened.add((tx, ty))
        sound.play('cut')
        for _ in range(8):
            self.effects.append(Particle(tx * TILE + 8, ty * TILE + 8, random.uniform(-0.6, 0.6),
                                         random.uniform(-1.4, -0.4), (230, 230, 240), 26, size=2))

    def buy(self, ware):
        wid, name, price, desc, once = ware
        p = self.player
        if p.pearls < price:
            sound.play('nope')
            self.say([f"HERMIE: THE {name} COSTS {price} PEARLS. YOU'VE ONLY GOT {p.pearls}. COME BACK SOON!"])
            return
        if wid == 'shrimp' and p.hp >= p.max_hp:
            sound.play('nope')
            self.say(["HERMIE: YOU LOOK WELL FED ALREADY! SAVE IT FOR WHEN YOU'RE HURT."])
            return
        if wid == 'bombs' and p.bombs >= MAX_BOMBS:
            sound.play('nope')
            self.say([f"HERMIE: YOUR BOMB BAG IS FULL ({MAX_BOMBS} BOMBS)."])
            return
        p.pearls -= price
        sound.play('buy')
        self.burst(self.player.rect.center, (255, 240, 160), 12)
        first = wid not in self.bought
        if once:
            self.bought.add(wid)
        if wid == 'shrimp':
            p.hp = p.max_hp
            sound.play('munch')
        elif wid == 'bombs':
            p.bombs = min(MAX_BOMBS, p.bombs + 5)
            if 'bombbag' not in p.items:
                p.items.add('bombbag')
                self.say(["YOU GOT BUBBLE BOMBS!", "PRESS B TO DROP ONE. STAND BACK - IT BLASTS ENEMIES "
                          "AND CRACKED ROCK."])
        elif wid == 'heart':
            p.max_hp += 2
            p.hp = p.max_hp
            self.say(["YOU BOUGHT A HEART SHELL! YOUR LIFE GREW BY ONE HEART."])
        else:
            p.items.add(wid)
            if first:
                self.say([f"YOU GOT THE {name}!", desc])

    def slap_hits(self, p):
        r = p.slap_rect()
        for e in self.enemies:
            if e.active and e.last_slap != p.slap_id and r.colliderect(e.rect):
                e.last_slap = p.slap_id
                e.hit(self, 2, 'slap', p.rect.center)
                if isinstance(e, Urchin) and not p.stat('stingproof', 0):
                    p.hurt(self, 1, e.rect.center)      # ouch, spikes!
        for s in self.shots:
            if isinstance(s, EnemyShot) and r.colliderect(s.rect):
                s.dead = True
                self.spark(s.rect.center)
        for tx, ty, ch in list(self.level.tiles_in(r)):
            if ch == 'K':
                self.level.set_tile(tx, ty, world.floor_for(tx, ty))
                self.opened.add((tx, ty))
                sound.play('cut')
                for _ in range(10):
                    self.effects.append(Particle(tx * TILE + 8, ty * TILE + 8,
                                                 random.uniform(-1.5, 1.5), random.uniform(-2, 0.5),
                                                 random.choice(((46, 156, 78), (130, 214, 120))),
                                                 22, grav=0.08, size=2))
                self.drop_loot((tx * TILE + 8, ty * TILE + 8), chance=0.5)

    # ======================================================================
    # main loop
    # ======================================================================

    async def run(self):
        while True:
            for ev in pygame.event.get():
                self.handle_event(ev)
            self.update()
            self.draw()
            if self.touch.active:
                self.touch.present(self.display)
            pygame.display.flip()
            self.clock.tick(FPS)
            await asyncio.sleep(0)      # lets the browser breathe (pygbag); harmless on desktop

    def handle_event(self, ev):
        if ev.type == pygame.QUIT:
            quit_game()
        if self.touch.handle(ev):
            return
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and self.state == 'title':
            # clicking a menu item picks it; clicking anywhere else starts the highlighted one
            for i, r in enumerate(getattr(self.title_scene, 'menu_rects', [])):
                if r.collidepoint(ev.pos):
                    self.title_sel = i
            self.on_key(pygame.K_RETURN)
            return
        if ev.type == pygame.KEYDOWN:
            k = ev.key
            if k == pygame.K_ESCAPE and self.state in ('title', 'gameover', 'win'):
                quit_game()
            if k == pygame.K_F11:
                try:
                    pygame.display.toggle_fullscreen()
                except pygame.error:
                    pass
            if k == pygame.K_n:
                sound.toggle_music()        # mutes music and sound effects together
                self.toast = ('SOUND ON' if sound.music_on else 'MUTED', 90)
            if k in DIR_KEYS:
                d = DIR_KEYS[k]
                if d in self.held:
                    self.held.remove(d)
                self.held.append(d)
            self.on_key(k)
        elif ev.type == pygame.KEYUP and ev.key in DIR_KEYS:
            d = DIR_KEYS[ev.key]
            if d in self.held and not any(pygame.key.get_pressed()[kk] for kk, dd in DIR_KEYS.items()
                                          if dd == d):
                self.held.remove(d)

    def on_key(self, k):
        st = self.state
        if st == 'title':
            menu = self.title_menu()
            if k in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s) and len(menu) > 1:
                self.title_sel = (self.title_sel + 1) % len(menu)
                sound.play('text')
            elif k in CONFIRM_KEYS or k in ACTION_KEYS:
                if menu[self.title_sel] == 'CONTINUE':
                    self.load_game()
                else:
                    self.new_game()
            elif k == pygame.K_l and save_exists():
                self.load_game()
        elif st == 'play':
            if k in ACTION_KEYS:
                if self.try_talk():
                    pass
                elif self.shop_focus:
                    self.buy(self.shop_focus)
                else:
                    self.player.action(self)
            elif k in SAVE_KEYS:
                self.save_game()
            elif k in JET_KEYS:
                self.player.jet(self, self.held[-1] if self.held else self.touch.dir)
            elif k in BOMB_KEYS:
                self.player.drop_bomb(self)
            elif (k in FLIP_KEYS or k in FORM_KEYS) and self.inside_ghost_wall():
                sound.play('nope')
            elif k in FLIP_KEYS:
                self.player.flip()
            elif k in INK_MODE_KEYS:
                self.player.toggle_ink()
            elif k in PAUSE_KEYS:
                self.state = 'pause'
                self.pause_msg = ''
                sound.play('pause')
            elif k in WARP_KEYS:
                self.open_warp()
            elif k in MAP_KEYS:
                self.open_map()
            elif k in FORMS_KEYS:
                self.open_forms()
            elif k in FORM_KEYS:
                self.player.pick_form(FORM_KEYS[k])
        elif st == 'pause':
            if k in PAUSE_KEYS:
                self.state = 'play'
                sound.play('pause')
            elif k == pygame.K_s or k in SAVE_KEYS:
                self.save_game()
            elif k == pygame.K_q:
                quit_game()
        elif st == 'altar':
            rows = self.altar_rows()
            if k in (pygame.K_UP, pygame.K_w):
                self.altar_i = (self.altar_i - 1) % len(rows)
                self.altar_msg = ''
                sound.play('text')
            elif k in (pygame.K_DOWN, pygame.K_s):
                self.altar_i = (self.altar_i + 1) % len(rows)
                self.altar_msg = ''
                sound.play('text')
            elif k in ACTION_KEYS or k in CONFIRM_KEYS:
                self.altar_take(rows[self.altar_i])
            elif k in FUSE_KEYS_CLOSE:
                self.state = 'play'
                sound.play('pause')
        elif st == 'fuse':
            self.fuse_key(k)
        elif st == 'forms':
            self.forms_key(k)
        elif st == 'map':
            if k in MAP_KEYS or k in PAUSE_KEYS:
                self.state = 'play'
                sound.play('pause')
            elif k in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_a, pygame.K_d) and self.sky_seen():
                self.map_page = 'sky' if self.map_page == 'sea' else 'sea'
                self.map_cache = None
                sound.play('text')
        elif st == 'warp':
            spots = self.warp_spots()
            if k in (pygame.K_UP, pygame.K_w):
                self.warp_i = (self.warp_i - 1) % len(spots)
                sound.play('text')
            elif k in (pygame.K_DOWN, pygame.K_s):
                self.warp_i = (self.warp_i + 1) % len(spots)
                sound.play('text')
            elif k in ACTION_KEYS or k in CONFIRM_KEYS:
                self.warp_to(spots[self.warp_i])
            elif k in WARP_KEYS or k == pygame.K_ESCAPE or k in FLIP_KEYS:
                self.state = 'play'
        elif st == 'dialog':
            if k in ACTION_KEYS or k in CONFIRM_KEYS:
                d = self.dialog
                page = d['pages'][d['i']]
                if d['chars'] < len(page):
                    d['chars'] = len(page)
                else:
                    d['i'] += 1
                    d['chars'] = 0
                    if d['i'] >= len(d['pages']):
                        self.state = d['back']
        elif st == 'gameover':
            if k in CONFIRM_KEYS:
                self.continue_game()
        elif st == 'win':
            if k in CONFIRM_KEYS and self.t > 120:
                self.state = 'title'
                sound.music('title')

    def inside_ghost_wall(self):
        return any(ch == 'G' for _, _, ch in self.level.tiles_in(self.player.rect))

    def try_talk(self):
        p = self.player
        dx, dy = DIRS[p.facing]
        probe = p.rect.inflate(4, 4).move(dx * 6, dy * 6)
        for npc in self.npcs:
            if probe.colliderect(npc.rect):
                if isinstance(npc, FusionMachine):
                    self.open_fuse()
                    return True
                if isinstance(npc, Altar):
                    self.open_altar()
                    return True
                self.say(HERMIE_TALK if isinstance(npc, Hermie) else SHELLY_TALK[1:])
                return True
        return False

    def continue_game(self):
        """Back to the last checkpoint: roaming enemies return, cleared arenas stay cleared."""
        p = self.player
        p.hp = min(p.max_hp, 6)
        self.trial = None
        if self.active_arena:
            self.level.set_doors(self.active_arena, False)
            self.active_arena = None
        for sp in self.spawns:
            sp['inst'] = None
            if not sp['arena']:
                sp['killed'] = False
        self.enemies, self.shots, self.effects = [], [], []
        self.pickups = [i for i in self.pickups if i.life is None]
        self.respawn_player()
        self.state = 'play'
        self.area = self.region = None
        self.update_area()

    # ======================================================================
    # update
    # ======================================================================

    def update(self):
        self.t += 1
        self.touch.check_orientation()
        if self.shake:
            self.shake -= 1
        if self.banner_t:
            self.banner_t -= 1
        if self.state in ('play', 'dialog', 'pause', 'title', 'win'):
            self.update_bubbles()
        st = self.state
        if st == 'play':
            self.frames += 1
            self.update_play()
        elif st == 'dialog':
            d = self.dialog
            page = d['pages'][d['i']]
            if d['chars'] < len(page):
                d['chars'] += 0.75
                if int(d['chars']) % 3 == 0:
                    sound.play('text')
            for n in self.npcs:
                n.update(self)
        elif st == 'dying':
            self.die_t += 1
            if self.die_t % 6 == 0 and self.die_t < 80:
                order = ['down', 'left', 'up', 'right']
                self.player.facing = order[(self.die_t // 6) % 4]
            if self.die_t == 80:
                self.player.mood = 'mad'
                self.burst(self.player.rect.center, (255, 255, 255), 16)
            for fx in self.effects:
                fx.update(self)
            self.effects = [f for f in self.effects if not f.dead]
            if self.die_t > 150:
                self.state = 'gameover'

    def update_bubbles(self):
        rate = 0.06 if self.state == 'title' else (0.03 if self.area == 'overworld' else
                                                   0 if self.area == 'sky' else 0.012)
        if random.random() < rate:
            h = SCREEN_H if self.state == 'title' else PLAY_H
            self.bubbles.append(Bubble(random.randrange(SCREEN_W), h + 2))
        for b in self.bubbles:
            b.update()
        self.bubbles = [b for b in self.bubbles if not b.dead]

    def update_camera(self):
        lv = self.level
        cx, cy = self.player.rect.center
        if self.trial:
            r = self.room_px(self.trial['name'])
            x, y = r.x, r.y
        elif cy >= world.SKY_Y * TILE:
            x0, y0, x1, y1 = world.SKY_RECT
            x = max(x0 * TILE, min((x1 + 1) * TILE - PLAY_W, cx - PLAY_W // 2))
            y = max(y0 * TILE, min((y1 + 1) * TILE - PLAY_H, cy - PLAY_H // 2))
        else:
            x = max(0, min(lv.px_w - PLAY_W, cx - PLAY_W // 2))
            y = max(0, min(world.WORLD_H * TILE - PLAY_H, cy - PLAY_H // 2))
        self.cam = (x, y)
        self.view_rect = pygame.Rect(x, y, PLAY_W, PLAY_H)
        # reveal the minimap
        for ty in range(y // TILE, min(lv.h, (y + PLAY_H) // TILE + 1)):
            if world.WORLD_H <= ty < world.SKY_Y:
                continue                # trial rooms aren't on the map
            row = self.seen[ty]
            for tx in range(x // TILE, min(lv.w, (x + PLAY_W) // TILE + 1)):
                if not row[tx]:
                    row[tx] = True

    def update_area(self):
        cx, cy = self.player.rect.center
        tx, ty = cx // TILE, cy // TILE
        area = world.area_at(tx, ty)
        region = world.region_at(tx, ty)
        if region != self.region:
            self.region = region
            self.banner_t = 150
            if area in ('overworld', 'sky'):
                sound.music(world.REGION_MUSIC.get(region, 'reef'))
        if area != self.area:
            self.area = area
            if area in ('overworld', 'sky'):
                sound.music(world.REGION_MUSIC.get(region, 'reef'))
            else:
                sound.music(AREA_INFO[area]['music'])
            if area == 'dungeon':
                self.checkpoint = world.SHRINE_CHECKPOINT

    def update_spawns(self):
        view = self.view_rect
        near = view.inflate(48, 48)
        far = view.inflate(PLAY_W, PLAY_H)
        pc = self.player.rect.center
        for sp in self.spawns:
            if sp['killed'] or sp['arena']:
                continue
            e = sp['inst']
            if e is None:
                pt = pygame.Rect(sp['x'], sp['y'], 16, 16)
                if near.colliderect(pt) and math.hypot(pt.centerx - pc[0], pt.centery - pc[1]) > 56:
                    if sp['kind'].startswith('mini:') and sp['kind'][5:] in self.flags.get('minis', []):
                        continue
                    e = make_enemy(sp['kind'], sp['x'], sp['y'])
                    e.spawn = sp
                    sp['inst'] = e
                    self.enemies.append(e)
            elif not far.colliderect(e.rect):
                # wandered far off-screen: send it home, it will reappear later
                e.dead = True
                sp['inst'] = None

    def spawn_arena(self, name):
        for sp in self.spawns:
            if sp['arena'] == name and not sp['killed'] and sp['inst'] is None:
                e = make_enemy(sp['kind'], sp['x'], sp['y'])
                e.spawn = sp
                sp['inst'] = e
                self.enemies.append(e)

    def update_arenas(self):
        p = self.player
        lv = self.level
        if self.active_arena is None:
            for name, a in ARENAS.items():
                if name in self.cleared:
                    continue
                if world.arena_tile_rect(a).contains(p.rect):
                    self.active_arena = name
                    self.spawn_arena(name)
                    lv.set_doors(name, True)
                    sound.play('shut')
                    self.shake = 6
                    break
            return
        name = self.active_arena
        alive = any(sp['inst'] for sp in self.spawns if sp['arena'] == name)
        if not alive and not any(isinstance(f, Puff) and f.loud for f in self.effects):
            lv.set_doors(name, False)
            self.cleared.add(name)
            self.active_arena = None
            sound.play('door')
            kind, tx, ty = ARENAS[name]['reward']
            it = self.place_item(kind, tx, ty, ('reward', name))
            self.burst(it.rect.center, (255, 240, 160), 14)
            sound.play('key')

    def update_play(self):
        p = self.player
        move_dir = self.held[-1] if self.held else self.touch.dir
        self.level.ghost_ok = p.mood == 'ghost'
        if p.tumble:
            self.update_tumble()
            return
        p.in_sky = self.area == 'sky'
        if p.in_sky and p.sphere <= 0:
            p.sphere = p.SPHERE_MAX         # e.g. loading a save made up in the sky
        p.analog = self.touch.vec if not self.held else None
        p.update(self, move_dir)
        self.update_camera()
        self.update_area()
        if self.trial:
            self.update_trial()
            if self.trial is None:
                return
        else:
            self.update_spawns()
            self.check_portals()
            self.check_geysers()
            if self.trial:
                return

        awake = self.view_rect.inflate(32, 32)
        for e in self.enemies:
            if e.spawn['arena'] is None and not awake.colliderect(e.rect):
                continue            # frozen while off-screen
            e.update(self)
            if e.active and not e.frozen and e.rect.colliderect(p.rect):
                thorns = p.stat('thorns', 0)
                if thorns and not e.hurt_t:
                    e.hit(self, thorns, 'thorns', p.rect.center)
                if not (p.stat('stingproof', 0) and isinstance(e, (Jelly, Urchin))):
                    p.hurt(self, e.damage, e.rect.center)
        for s in self.shots:
            s.update(self)
        for n in self.npcs:
            n.update(self)
        mag = p.stat('magnet', 0)
        pcx, pcy = p.rect.center
        for it in self.pickups:
            it.update(self)
            if it.kind in ('pearl', 'bluepearl', 'heart', 'shrimp') and not it.item_id:
                ix, iy = it.rect.center
                d = math.hypot(pcx - ix, pcy - iy)
                if d > 2 and (it.pulled or d < mag):
                    it.x += (pcx - ix) / d * 2.5
                    it.y += (pcy - iy) / d * 2.5
            if not it.dead and it.rect.colliderect(p.rect):
                self.collect(it)
        for fx in self.effects:
            fx.update(self)
        self.shop_focus = None
        if world.region_at(p.rect.centerx // TILE, p.rect.centery // TILE) == 'PEARL SHOP':
            for ware, r in self.wares:
                if ware[0] not in self.bought and r.colliderect(p.rect.inflate(4, 4)):
                    self.shop_focus = ware
                    break
        for e in self.enemies:
            if e.dead and e.spawn['arena'] == 'trial':
                continue
            if e.dead and e.spawn['inst'] is e:
                e.spawn['killed'] = True
                e.spawn['inst'] = None
        self.enemies = [e for e in self.enemies if not e.dead]
        self.shots = [s for s in self.shots if not s.dead]
        self.pickups = [i for i in self.pickups if not i.dead]
        self.effects = [f for f in self.effects if not f.dead]
        self.update_arenas()

        if self.state != 'play':
            return
        if p.hp <= 0 and self.trial:
            self.finish_trial(False)
            return
        if p.hp <= 0:
            self.state = 'dying'
            self.die_t = 0
            sound.music(None)
            sound.play('die')
            return
        if p.hp <= 2 and self.t % 48 == 0:
            sound.play('lowhp')

    def collect(self, it):
        p = self.player
        it.dead = True
        if it.item_id:
            self.collected.add(it.item_id)
        k = it.kind
        if k == 'pearl':
            p.pearls += int(1 * p.stat('pearls', 1))
            sound.play('pearl')
        elif k == 'bluepearl':
            p.pearls += int(5 * p.stat('pearls', 1))
            sound.play('pearl')
        elif k == 'heart':
            p.hp = min(p.max_hp, p.hp + 2)
            sound.play('heart')
        elif k == 'shrimp':
            p.hp = min(p.max_hp, p.hp + 1)       # half a heart
            sound.play('munch')
            self.burst(it.rect.center, (255, 160, 120), 6)
        elif k == 'key':
            p.keys += 1
            sound.play('key')
            self.say(["YOU FOUND A SHRINE KEY!", "IT SHOULD OPEN THE SEALED DOOR IN THE GREAT HALL."])
        elif k == 'container':
            p.max_hp += 2
            p.hp = p.max_hp
            sound.play('item')
            self.say(["YOU FOUND A HEART SHELL! YOUR LIFE GREW BY ONE HEART."])
        elif k == 'orb':
            if self.trial:
                self.trial['got'] += 1
            sound.play('pearl')
            self.burst(it.rect.center, (120, 255, 200), 8)
        elif k == 'halfpearl':
            self.flags['halves'] = self.flags.get('halves', 0) + 1
            sound.play('item')
            if self.flags['halves'] >= 2:
                sound.music('victory', loops=0)
                self.state = 'win'
                self.t = 0
            else:
                self.say(["YOU FOUND HALF OF THE GOLDEN PEARL!",
                          "THE OTHER HALF IS WITH MURK, GRIMFIN'S GLOOMY BIG SISTER, DEEP IN THE DARK SUNKEN CITY "
                          "FAR TO THE SOUTHEAST.",
                          "A GHOSTLY WALL GUARDS THE WAY FROM THE SHIP GRAVEYARD... ONLY SPOOKY OCTO CAN PASS."])
        elif k == 'golden':
            sound.play('item')
            sound.music('victory', loops=0)
            self.state = 'win'
            self.t = 0

    # ======================================================================
    # drawing
    # ======================================================================

    def draw(self):
        scr = self.screen
        st = self.state
        if st == 'title':
            self.draw_title(scr)
            return
        if st == 'gameover':
            self.draw_gameover(scr)
            return
        if st == 'win':
            self.draw_win(scr)
            return

        self.draw_world(self.play_surf)
        scr.fill((0, 0, 0))
        sx = sy = 0
        if self.shake:
            sx, sy = random.randint(-2, 2), random.randint(-2, 2)
        scr.blit(self.play_surf, (sx, HUD_H + sy))
        self.draw_hud(scr)

        if self.banner_t and st == 'play':
            name = self.region
            w = gfx.text_width(name) + 20
            box = pygame.Rect(SCREEN_W // 2 - w // 2, HUD_H + 14, w, 20)
            self.draw_box(scr, box)
            gfx.text(scr, name, SCREEN_W // 2, box.y + 7, (255, 220, 120), center=True)
        if not sound.music_on and st not in ('title',):
            self.draw_mute_icon(scr, SCREEN_W - 17, HUD_H - 13)
        if st in ('play', 'pause', 'title') and getattr(self, 'toast', None) and self.toast[1] > 0:
            msg, t = self.toast
            self.toast = (msg, t - 1)
            w = gfx.text_width(msg) + 16
            box = pygame.Rect(SCREEN_W // 2 - w // 2, SCREEN_H - 26, w, 18)
            self.draw_box(scr, box)
            gfx.text(scr, msg, SCREEN_W // 2, box.y + 6, (160, 230, 160), center=True)
        if st == 'play' and self.shop_focus:
            self.draw_shop_info(scr)
        if st == 'play' and not self.trial:
            self.draw_boss_bar(scr)
        if self.trial and st in ('play', 'pause'):
            self.draw_trial_hud(scr)
        if self.flash_t:
            self.flash_t -= 1
            veil = pygame.Surface((PLAY_W, PLAY_H))
            veil.fill((255, 255, 255))
            veil.set_alpha(int(255 * self.flash_t / 20))
            scr.blit(veil, (0, HUD_H))
        if st in ('warp', 'map', 'fuse', 'altar', 'forms'):
            veil = pygame.Surface((PLAY_W, PLAY_H))
            veil.fill((0, 0, 16))
            veil.set_alpha(150)
            scr.blit(veil, (0, HUD_H))
        if st == 'warp':
            self.draw_warp(scr)
            gfx.text(scr, "PAUSED", SCREEN_W // 2, SCREEN_H - 10, (150, 160, 200), center=True)
        elif st == 'map':
            self.draw_map(scr)
        elif st == 'fuse':
            self.draw_fuse(scr)
        elif st == 'altar':
            self.draw_altar(scr)
        elif st == 'forms':
            self.draw_forms(scr)
        if st == 'dialog':
            self.draw_dialog(scr)
        elif st == 'pause':
            self.draw_pause(scr)
        elif st == 'dying':
            a = min(1.0, self.die_t / 100)
            veil = pygame.Surface((PLAY_W, PLAY_H))
            veil.fill((120, 0, 30))
            veil.set_alpha(int(170 * a))
            scr.blit(veil, (0, HUD_H))
            ox, oy = -self.cam[0], -self.cam[1]
            self.player.draw(scr, ox, HUD_H + oy)

    def draw_world(self, ps):
        ps.blit(self.level.render(gfx.TILES), (0, 0), self.view_rect)
        ox, oy = -self.cam[0], -self.cam[1]
        vis = self.view_rect.inflate(32, 32)
        for it in self.pickups:
            if vis.colliderect(it.rect):
                it.draw(ps, ox, oy)
        if vis.colliderect(self.wares[0][1].union(self.wares[-1][1])):
            for ware, r in self.wares:
                if ware[0] in self.bought:
                    continue            # sold out: an empty spot on the counter
                img = self.ware_icon(ware[0])
                bob = round(math.sin(self.t * 0.08 + r.x) * 1) if ware is self.shop_focus else 0
                ps.blit(img, (r.centerx - img.get_width() // 2 + ox, r.centery - img.get_height() // 2 + oy + bob))
                gfx.text(ps, str(ware[2]), r.centerx + ox, r.bottom + 3 + oy,
                         (255, 220, 120) if self.player.pearls >= ware[2] else (200, 120, 120), center=True)
        self.draw_portals(ps, ox, oy)
        if self.trial and world.TRIALS[self.trial['name']].get('eyes'):
            t = world.TRIALS[self.trial['name']]
            x0, y0 = t['room'][:2]
            for i, (ex, ey) in enumerate(t['eyes']):
                cx, cy = int((x0 + ex) * TILE) + ox, int((y0 + ey) * TILE) + oy
                r = 6 if i == 0 else 4
                pygame.draw.circle(ps, (40, 10, 60), (cx, cy), r + 2)
                pygame.draw.circle(ps, (200, 60, 230), (cx, cy), r)
                pygame.draw.circle(ps, (255, 240, 255), (cx, cy), r // 2)
        for n in self.npcs:
            n.draw(ps, ox, oy)
        for e in sorted(self.enemies, key=lambda e: e.y):
            if vis.colliderect(e.rect):
                e.draw(ps, ox, oy)
        if self.state != 'dying':
            self.player.draw(ps, ox, oy)
        for s in self.shots:
            s.draw(ps, ox, oy)
        for fx in self.effects:
            fx.draw(ps, ox, oy)
        for b in self.bubbles:
            b.draw(ps)
        theme = world.THEMES.get(self.region, 'reef') if self.area in ('overworld', 'sky') else None
        fx = THEME_FX.get(theme)
        if fx:
            col, alpha, parts = fx
            if self.theme_veil[0] != (col, alpha):
                v = pygame.Surface((PLAY_W, PLAY_H))
                v.fill(col)
                v.set_alpha(alpha)
                self.theme_veil = ((col, alpha), v)
            ps.blit(self.theme_veil[1], (0, 0))
            if parts and self.state == 'play':
                self.ambient(parts)
        for a in self.motes:
            a[0] += a[2]
            a[1] += a[3]
            a[4] -= 1
            c = a[5]
            ps.set_at((int(a[0]), int(a[1])), c)
            if a[6]:
                ps.set_at((int(a[0]) + 1, int(a[1])), c)
        self.motes = [a for a in self.motes if a[4] > 0 and -2 < a[1] < PLAY_H + 2]
        if self.area in ('overworld', 'sky') and theme not in ('abyss', 'vents', 'city'):
            off = int(math.sin(self.t * 0.01) * 30) - 60
            ps.blit(self.rays, (off, 0))
        if self.trial:
            self.draw_trial_props(ps, ox, oy)
        if (self.region in world.DARK_REGIONS and self.area == 'overworld' and not self.trial) or \
                (self.trial and world.TRIALS[self.trial['name']].get('dark')):
            self.draw_darkness(ps, ox, oy)
            if self.trial:                           # orbs still glint in the dark
                for it in self.pickups:
                    if it.kind == 'orb' and not it.dead and (self.t // 10) % 2:
                        c = it.rect.center
                        pygame.draw.circle(ps, (150, 255, 210), (c[0] + ox, c[1] + oy), 2)
        if self.glow_flash:
            self.glow_flash -= 1
            v = pygame.Surface((PLAY_W, PLAY_H))
            v.fill((220, 255, 220))
            v.set_alpha(int(200 * self.glow_flash / 14))
            ps.blit(v, (0, 0))

    def draw_portals(self, ps, ox, oy):
        for name, t in world.TRIALS.items():
            px, py = t['portal']
            cx, cy = px * TILE + 8, py * TILE + 8
            if not self.view_rect.inflate(32, 32).collidepoint(cx, cy):
                continue
            sx, sy = cx + ox, cy + oy
            pygame.draw.ellipse(ps, (40, 40, 60), (sx - 10, sy - 7, 20, 16))
            if name in self.trials_done:
                pygame.draw.ellipse(ps, (110, 110, 130), (sx - 8, sy - 5, 16, 12), 2)
                continue
            col = self.portal_color(t)
            for i in range(3):
                ph = self.t * 0.12 + i * 2.1
                w = 16 - i * 5
                pygame.draw.ellipse(ps, col if i != 1 else (255, 255, 255),
                                    (sx - w // 2 + int(math.cos(ph) * 1.5), sy - w * 3 // 8 - 1 + int(math.sin(ph) * 1.5),
                                     w, max(2, w * 3 // 4)), 1 if i else 2)
            if self.state == 'play' and self.t % 6 == 0:
                a = random.uniform(0, math.tau)
                self.effects.append(Particle(cx + math.cos(a) * 9, cy + math.sin(a) * 7,
                                             -math.cos(a) * 0.4, -math.sin(a) * 0.4 - 0.2, col, 18))

    def portal_color(self, t):
        return t.get('color', (255, 255, 255))

    def draw_boss_bar(self, scr):
        """Name and health of a mini-boss that's on screen."""
        for e in self.enemies:
            if isinstance(e, MiniBoss) and not e.dead and not e.spawn_t and self.view_rect.colliderect(e.rect):
                w = 120
                x, y = SCREEN_W // 2 - w // 2, SCREEN_H - 14
                gfx.text(scr, e.name, SCREEN_W // 2, y - 9, (255, 220, 120), center=True)
                pygame.draw.rect(scr, (0, 0, 0), (x - 1, y - 1, w + 2, 6))
                pygame.draw.rect(scr, (90, 20, 30), (x, y, w, 4))
                pygame.draw.rect(scr, (230, 60, 80), (x, y, int(w * max(0, e.hp) / e.max_hp), 4))
                return

    def draw_trial_hud(self, scr):
        tr = self.trial
        t = world.TRIALS[tr['name']]
        if tr['t'] < 0:
            n = (-tr['t']) // 40 + 1
            self.big_text(scr, str(n), SCREEN_W // 2, HUD_H + 70, (255, 220, 120))
            return
        if tr['t'] < 40:
            self.big_text(scr, "GO!", SCREEN_W // 2, HUD_H + 70, (160, 255, 160))
        left = max(0, t.get('time', 0) * 60 - tr['t'])
        secs = (left + 59) // 60
        if t['kind'] == 'waves':
            s = f"WAVE {max(1, tr['wave'])}/{len(t['waves'])}  FOES LEFT {len(self.enemies)}"
        elif t['kind'] == 'duel':
            boss = next((e for e in self.enemies if isinstance(e, MiniBoss)), None)
            s = f"DEFEAT {boss.name}" if boss else "DEFEAT THE GUARDIAN"
        elif t['kind'] == 'chase':
            s = f"TAG THE THIEF {tr['got']}/3  0:{secs:02d}"
        elif t['kind'] == 'defend':
            s = f"CLAM {max(0, tr['clam'])}/{CLAM_HP}  HOLD ON 0:{secs:02d}"
        elif t['kind'] == 'race':
            s = f"REACH THE GOAL  0:{secs:02d}"
        else:
            left = max(0, t['time'] * 60 - tr['t'])
            secs = (left + 59) // 60
            s = (f"ORBS {tr['got']}/{len(t['orbs'])}  " if t['kind'] == 'collect' else "SURVIVE  ") + f"0:{secs:02d}"
        w = gfx.text_width(s) + 12
        box = pygame.Rect(SCREEN_W // 2 - w // 2, HUD_H + 2, w, 13)
        pygame.draw.rect(scr, (0, 0, 0), box)
        gfx.text(scr, s, SCREEN_W // 2, box.y + 3, (255, 220, 120), center=True)

    def ware_icon(self, wid):
        if wid == 'shrimp':
            return gfx.SPR['shrimp']
        if wid == 'bombs':
            return gfx.SPR['items']['bomb']
        if wid == 'heart':
            return gfx.SPR['heart']['container']
        return gfx.SPR['items'][wid]

    def draw_shop_info(self, scr):
        wid, name, price, desc, once = self.shop_focus
        lines = gfx.wrap(desc, 38)
        box = pygame.Rect(8, SCREEN_H - 30 - len(lines) * 10, SCREEN_W - 16, 24 + len(lines) * 10)
        self.draw_box(scr, box)
        gfx.text(scr, f"{name} - {price} PEARLS", box.x + 8, box.y + 7, (255, 220, 120))
        for i, l in enumerate(lines):
            gfx.text(scr, l, box.x + 8, box.y + 17 + i * 10)
        gfx.text(scr, "Z:BUY", box.right - 36, box.y + 7, (160, 230, 160))

    def ambient(self, kind):
        if kind == 'snow' and random.random() < 0.5:
            self.motes.append([random.uniform(0, PLAY_W), -1, random.uniform(-0.3, 0.3), random.uniform(0.4, 0.8),
                               400, (245, 250, 255), random.random() < 0.3])
        elif kind == 'embers' and random.random() < 0.35:
            self.motes.append([random.uniform(0, PLAY_W), PLAY_H + 1, random.uniform(-0.2, 0.2),
                               -random.uniform(0.4, 0.9), 300, random.choice(((255, 160, 40), (255, 90, 30))),
                               False])
        elif kind == 'wind' and random.random() < 0.12:
            y = random.uniform(0, PLAY_H)
            for i in range(random.randint(4, 9)):
                self.motes.append([-i * 1.0, y, 2.2, 0, 140, (255, 255, 255), False])
        elif kind == 'dust' and random.random() < 0.15:
            self.motes.append([random.uniform(0, PLAY_W), random.uniform(0, PLAY_H), random.uniform(-0.15, 0.15),
                               random.uniform(-0.1, 0.1), 160, (170, 160, 190), False])

    def draw_trial_props(self, ps, ox, oy):
        t = world.TRIALS[self.trial['name']]
        x0, y0 = t['room'][:2]
        if t['kind'] == 'defend':
            cx, cy = (x0 + t['clam_at'][0]) * TILE + ox, (y0 + t['clam_at'][1]) * TILE + oy
            hp = max(0, self.trial['clam'])
            open_ = (self.t // 40) % 3 == 0
            pygame.draw.ellipse(ps, (20, 30, 60), (cx - 13, cy + 4, 26, 8))
            pygame.draw.ellipse(ps, (230, 190, 200), (cx - 12, cy - 4, 24, 12))
            pygame.draw.ellipse(ps, (250, 220, 230), (cx - 12, cy - 9 - (3 if open_ else 0), 24, 12))
            for i in range(5):
                pygame.draw.line(ps, (200, 150, 170), (cx, cy - 4), (cx - 10 + i * 5, cy - 9), 1)
            if open_:
                pygame.draw.circle(ps, (255, 255, 255), (cx, cy - 2), 3)
            for i in range(CLAM_HP - hp):            # cracks
                pygame.draw.line(ps, (90, 40, 60), (cx - 8 + i * 3, cy - 6), (cx - 6 + i * 3, cy), 1)
        elif t['kind'] == 'race':
            gx, gy = t['goal']
            cx, cy = (x0 + gx) * TILE + ox, (y0 + gy) * TILE + oy
            r = 7 + (self.t // 6) % 3
            pygame.draw.circle(ps, (255, 220, 120), (cx, cy), r, 2)
            pygame.draw.line(ps, (240, 240, 255), (cx, cy - 10), (cx, cy + 6), 1)
            pygame.draw.polygon(ps, (255, 90, 110), [(cx, cy - 10), (cx + 8, cy - 7), (cx, cy - 4)])

    def draw_darkness(self, ps, ox, oy):
        """The Sunken City is pitch dark: Octo only sees a little circle - unless Glowy lights it up."""
        p = self.player
        r = p.stat('light', 44)
        if self.light_mask[0] != r:
            m = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            m.fill((0, 0, 12, 230))
            for i in range(r, 0, -2):
                a = int(230 * max(0.0, (i - r * 0.55) / (r * 0.45)))
                pygame.draw.circle(m, (0, 0, 12, a), (r, r), i)
            self.light_mask = (r, m)
        dark = pygame.Surface((PLAY_W, PLAY_H), pygame.SRCALPHA)
        dark.fill((0, 0, 12, 230))
        cx, cy = p.rect.centerx + ox, p.rect.centery + oy
        dark.blit(self.light_mask[1], (cx - r, cy - r), special_flags=pygame.BLEND_RGBA_MIN)
        for name, t in world.TRIALS.items():      # portals glow through the dark
            px, py = t['portal']
            pr = pygame.Rect(px * TILE + ox - 10, py * TILE + oy - 10, 36, 36)
            if pr.colliderect(dark.get_rect()):
                dark.fill((0, 0, 12, 60), pr, special_flags=pygame.BLEND_RGBA_MIN)
        ps.blit(dark, (0, 0))

    # ---- full map (M) -----------------------------------------------------
    def tile_color(self, tx, ty):
        lv = self.level
        ch = lv.tiles[ty][tx]
        if ch == 'v':
            if ty >= world.SKY_Y:
                return (150, 200, 245)
            return (10, 10, 20) if world.area_at(tx, ty) == 'dungeon' else (30, 52, 112)
        if ch in '.,':
            return THEME_MINI.get(lv.themes[ty][tx], (196, 178, 128))
        if ch == '=' and ty >= world.SKY_Y:
            return (150, 110, 60)          # sky bridges
        return MINIMAP_COLORS.get(ch, (0, 0, 0))

    def sky_seen(self):
        x0, y0, x1, y1 = world.SKY_RECT
        return any(any(self.seen[ty][x0:x1 + 1]) for ty in range(y0, y1 + 1))

    def open_map(self):
        if self.trial:
            sound.play('nope')
            return
        self.map_page = 'sky' if self.area == 'sky' else 'sea'
        self.map_cache = None
        self.state = 'map'
        sound.play('pause')

    def map_layout(self):
        if self.map_page == 'sky':
            x0, y0, x1, y1 = world.SKY_RECT
            return x0, y0, x1 - x0 + 1, y1 - y0 + 1, 4
        return 0, 0, self.level.w, world.WORLD_H, 1.5

    def draw_map(self, scr):
        x0, y0, w, h, k = self.map_layout()
        mw, mh = int(w * k), int(h * k)
        ox, oy = (SCREEN_W - mw) // 2, HUD_H + 16 + (PLAY_H - 30 - mh) // 2
        if self.map_cache is None:
            surf = pygame.Surface((w, h))
            surf.fill((6, 8, 22))
            for ty in range(y0, y0 + h):
                row = self.seen[ty]
                for tx in range(x0, x0 + w):
                    if row[tx]:
                        surf.set_at((tx - x0, ty - y0), self.tile_color(tx, ty))
            self.map_cache = pygame.transform.scale(surf, (mw, mh))
        title = "SKY ISLANDS" if self.map_page == 'sky' else "THE SEA"
        gfx.text(scr, "MAP - " + title, SCREEN_W // 2, HUD_H + 4, (255, 220, 120), center=True)
        pygame.draw.rect(scr, (90, 100, 150), (ox - 2, oy - 2, mw + 4, mh + 4), 1)
        scr.blit(self.map_cache, (ox, oy))

        def spot(tx, ty):
            return ox + int((tx - x0 + 0.5) * k), oy + int((ty - y0 + 0.5) * k)

        def inside(tx, ty):
            return x0 <= tx < x0 + w and y0 <= ty < y0 + h and self.seen[int(ty)][int(tx)]
        blink = (self.t // 15) % 2
        # trial portals
        for name, t in world.TRIALS.items():
            px, py = t['portal']
            if inside(px, py):
                c = (120, 120, 130) if name in self.trials_done else self.portal_color(t)
                sx, sy = spot(px, py)
                pygame.draw.circle(scr, c, (sx, sy), 2)
        # geysers
        for a, b in world.GEYSERS:
            for gx, gy in (a, b):
                if inside(gx, gy):
                    sx, sy = spot(gx, gy)
                    pygame.draw.line(scr, (220, 250, 255), (sx, sy + 2), (sx, sy - 2))
                    pygame.draw.line(scr, (220, 250, 255), (sx - 2, sy - 1), (sx, sy - 3))
                    pygame.draw.line(scr, (220, 250, 255), (sx + 2, sy - 1), (sx, sy - 3))
        # mini-bosses (crowns), red while still undefeated
        beaten = self.flags.get('minis', [])
        for bid, bx, by in world.MINIBOSSES:
            if inside(bx, by):
                sx, sy = spot(bx, by)
                c = (110, 110, 120) if bid in beaten else (255, 80, 80)
                pygame.draw.polygon(scr, c, [(sx - 3, sy + 2), (sx - 3, sy - 2), (sx - 1, sy),
                                             (sx, sy - 3), (sx + 1, sy), (sx + 3, sy - 2), (sx + 3, sy + 2)])
        # big bosses
        for boss in ('throne', 'murk'):
            bx0, by0, bx1, by1 = ARENAS[boss]['rect']
            bx, by = (bx0 + bx1) // 2, (by0 + by1) // 2
            if inside(bx, by) and boss not in self.cleared:
                sx, sy = spot(bx, by)
                pygame.draw.circle(scr, (230, 40, 60), (sx, sy), 3)
                pygame.draw.circle(scr, (255, 255, 255), (sx, sy), 3, 1)
        # Octo
        cx, cy = self.player.rect.center
        ptx, pty = cx / TILE, cy / TILE
        if x0 <= ptx < x0 + w and y0 <= pty < y0 + h and blink:
            sx, sy = ox + int((ptx - x0) * k), oy + int((pty - y0) * k)
            pygame.draw.rect(scr, (255, 255, 255), (sx - 2, sy - 2, 5, 5))
            pygame.draw.rect(scr, (40, 90, 220), (sx - 1, sy - 1, 3, 3))
        # legend
        ly = SCREEN_H - 11
        pygame.draw.rect(scr, (255, 255, 255), (8, ly, 4, 4))
        gfx.text(scr, "YOU", 15, ly - 1, (220, 220, 230))
        pygame.draw.circle(scr, (180, 120, 255), (44, ly + 2), 2)
        gfx.text(scr, "TRIAL", 49, ly - 1, (220, 220, 230))
        pygame.draw.polygon(scr, (255, 80, 80), [(82, ly + 4), (82, ly), (84, ly + 2), (85, ly - 1),
                                                 (86, ly + 2), (88, ly), (88, ly + 4)])
        gfx.text(scr, f"BOSS {len(beaten)}/{len(world.MINIBOSSES)}", 92, ly - 1, (220, 220, 230))
        hint = "<> SKY/SEA" if self.sky_seen() else "M: CLOSE"
        gfx.text(scr, hint, SCREEN_W - 6 - gfx.text_width(hint), ly - 1, (150, 160, 200))

    def draw_minimap(self, scr, x, y):
        lv = self.level
        if self.t % 20 == 0 or not hasattr(self, '_mini_scaled'):
            mm = self.minimap
            for ty in range(world.WORLD_H):
                row = self.seen[ty]
                for tx in range(lv.w):
                    if row[tx]:
                        ch = lv.tiles[ty][tx]
                        if ch == 'v':
                            c = (10, 10, 20) if world.area_at(tx, ty) == 'dungeon' else (30, 52, 112)
                        elif ch in '.,':
                            c = THEME_MINI.get(lv.themes[ty][tx], (196, 178, 128))
                        else:
                            c = MINIMAP_COLORS.get(ch, (0, 0, 0))
                        mm.set_at((tx, ty), c)
            self._mini_scaled = pygame.transform.smoothscale(mm, MINIMAP_SIZE)
        pygame.draw.rect(scr, (40, 44, 70), (x - 1, y - 1, MINIMAP_SIZE[0] + 2, MINIMAP_SIZE[1] + 2), 1)
        scr.blit(self._mini_scaled, (x, y))
        kx, ky = MINIMAP_SIZE[0] / lv.w, MINIMAP_SIZE[1] / world.WORLD_H
        for name, t in world.TRIALS.items():
            px, py = t['portal']
            if py < world.WORLD_H and self.seen[py][px]:
                c = (120, 120, 130) if name in self.trials_done else self.portal_color(t)
                pygame.draw.rect(scr, c, (x + int((px + 0.5) * kx) - 1, y + int((py + 0.5) * ky) - 1, 2, 2))
        if (self.t // 12) % 2 and not self.trial and self.area != 'sky':
            cx, cy = self.player.rect.center
            pygame.draw.rect(scr, (255, 255, 255), (x + int(cx / TILE * kx) - 1, y + int(cy / TILE * ky) - 1, 3, 3))
        for boss in ('throne', 'murk'):
            if boss not in self.cleared and (self.t // 20) % 2:
                x0, y0, x1, y1 = ARENAS[boss]['rect']
                bx, by = (x0 + x1 + 1) / 2, (y0 + y1 + 1) / 2
                pygame.draw.rect(scr, (230, 60, 60), (x + int(bx * kx) - 1, y + int(by * ky) - 1, 2, 2))

    def draw_hud(self, scr):
        pygame.draw.rect(scr, (0, 0, 0), (0, 0, SCREEN_W, HUD_H))
        p = self.player
        self.draw_minimap(scr, 4, 8)

        # counters
        scr.blit(gfx.SPR['pearl'], (60, 12))
        gfx.text(scr, f"X{p.pearls:03d}", 70, 12)
        scr.blit(pygame.transform.scale(gfx.SPR['key'], (5, 10)), (61, 24))
        gfx.text(scr, f"X{p.keys}", 70, 25)
        # spirit pearls (from trials)
        pygame.draw.circle(scr, (110, 70, 170), (102, 28), 4)
        pygame.draw.circle(scr, (190, 140, 255), (102, 28), 3)
        scr.set_at((101, 27), (255, 255, 255))
        gfx.text(scr, f"X{p.spirit}", 108, 25, (210, 180, 255))
        gfx.text(scr, self.region, 56, 41, (150, 170, 220))
        if 'bombbag' in p.items:
            scr.blit(gfx.SPR['items']['bomb'], (98, 10))
            gfx.text(scr, f"X{p.bombs:02d}", 109, 12)
        ix = 98
        for wid in ('fins', 'shield', 'deepink'):
            if wid in p.items:
                img = gfx.SPR['items'][wid]
                scr.blit(img, (ix, 24))
                ix += img.get_width() + 3
        if p.dash_cd and not p.dash_t:     # jet recharging
            w = int(28 * (1 - p.dash_cd / 40))
            pygame.draw.rect(scr, (40, 40, 60), (144, 50, 28, 2))
            pygame.draw.rect(scr, (120, 110, 220), (144, 50, w, 2))

        # mood box
        bx, by = 144, 8
        pygame.draw.rect(scr, FORM_BOX[p.mood], (bx, by, 28, 28))
        pygame.draw.rect(scr, (255, 255, 255), (bx, by, 28, 28), 1)
        scr.blit(gfx.OCTO[p.mood]['down'][(self.t // 20) % 2], (bx + 6, by + 6))
        label = p.ink_mode.upper() if p.mood == 'blue' else FORM_LABEL[p.mood]
        gfx.text(scr, label, bx + 14, by + 32, (255, 255, 255), center=True)
        gfx.text(scr, "X", bx + 32, by + 2, (160, 160, 160))
        gfx.text(scr, "Z", bx + 32, by + 18, (160, 160, 160))

        # life
        gfx.text(scr, "-LIFE-", 200, 10, (232, 60, 80))
        hearts = p.max_hp // 2
        for i in range(hearts):
            if p.hp >= (i + 1) * 2:
                img = gfx.SPR['heart']['full']
            elif p.hp == i * 2 + 1:
                img = gfx.SPR['heart']['half']
            else:
                img = gfx.SPR['heart']['empty']
            hx = 188 + (i % 7) * 9
            hy = 24 + (i // 7) * 9
            scr.blit(img, (hx, hy))

    def draw_box(self, scr, rect):
        pygame.draw.rect(scr, (0, 0, 0), rect)
        pygame.draw.rect(scr, (255, 255, 255), rect, 1)
        pygame.draw.rect(scr, (90, 120, 220), rect.inflate(-4, -4), 1)

    def draw_dialog(self, scr):
        d = self.dialog
        page = d['pages'][d['i']]
        shown = page[:int(d['chars'])]
        lines = gfx.wrap(page, 38)
        box = pygame.Rect(8, HUD_H + 8, SCREEN_W - 16, 16 + len(lines) * 10)
        self.draw_box(scr, box)
        n = len(shown)
        for i, line in enumerate(lines):
            gfx.text(scr, line[:max(0, n)], box.x + 8, box.y + 8 + i * 10)
            n -= len(line) + 1
        if d['chars'] >= len(page) and (self.t // 20) % 2:
            gfx.text(scr, ">", box.right - 12, box.bottom - 10, (255, 220, 120))

    def draw_pause(self, scr):
        box = pygame.Rect(24, HUD_H + 2, SCREEN_W - 48, 172)
        self.draw_box(scr, box)
        lines = ["PAUSED", "ARROWS/WASD  MOVE", "Z / SPACE    ATTACK / TALK / BUY",
                 "X / 1-9      CHANGE FORM", "C            INK: LINE/BURST",
                 "V            INK JET (DASH)", "B            BUBBLE BOMB", "T            WARP TO PORTALS",
                 "M            WORLD MAP", "N            MUTE", "P/ENTER/ESC  RESUME"]
        for i, l in enumerate(lines):
            gfx.text(scr, l, box.x + 10 if i else SCREEN_W // 2, box.y + 6 + i * 10,
                     (255, 220, 120) if i == 0 else (255, 255, 255), center=(i == 0))
        y = box.y + 6 + len(lines) * 10 + 3
        gfx.text(scr, "S/L-SHIFT  SAVE" if WEB else "S/L-SHIFT  SAVE    Q  QUIT", SCREEN_W // 2, y, (160, 230, 160), center=True)
        forms = "  ".join(f"{i + 1}:{gfx.MOOD_NAMES[f]}" for i, f in enumerate(self.player.forms))
        for j, line in enumerate(gfx.wrap("FORMS  " + forms, 36)):
            gfx.text(scr, line, SCREEN_W // 2, y + 13 + j * 10, (190, 200, 255), center=True)
        if getattr(self, 'pause_msg', ''):
            gfx.text(scr, self.pause_msg, SCREEN_W // 2, box.bottom - 11, (255, 220, 120), center=True)

    def draw_mute_icon(self, scr, x, y):
        """A little crossed-out speaker."""
        c = (230, 90, 90)
        pygame.draw.rect(scr, c, (x, y + 3, 3, 4))
        pygame.draw.polygon(scr, c, [(x + 3, y + 3), (x + 6, y), (x + 6, y + 10), (x + 3, y + 7)])
        pygame.draw.line(scr, c, (x + 8, y + 2), (x + 12, y + 8))
        pygame.draw.line(scr, c, (x + 12, y + 2), (x + 8, y + 8))

    def big_text(self, scr, s, cx, y, color, scale=2):
        w = gfx.text_width(s) + 2
        tmp = pygame.Surface((w, 9), pygame.SRCALPHA)
        gfx.text(tmp, s, 0, 0, color)
        tmp = pygame.transform.scale(tmp, (w * scale, 9 * scale))
        scr.blit(tmp, (cx - w * scale // 2, y))

    def title_menu(self):
        if self.t % 30 == 1 or not hasattr(self, 'has_save'):
            self.has_save = save_exists()
        return ['CONTINUE', 'NEW GAME'] if self.has_save else ['NEW GAME']

    def draw_title(self, scr):
        menu = self.title_menu()
        self.title_sel = min(self.title_sel, len(menu) - 1)
        cycle = (self.t // 240) % 2
        mood = 'blue' if cycle == 0 else 'mad'
        phase = self.t % 240
        w = 1.0
        if phase > 225:
            w = abs(math.cos((phase - 225) / 15 * math.pi / 2))
        elif phase < 15 and self.t > 15:
            w = abs(math.sin(phase / 15 * math.pi / 2))
        self.title_scene.touch = self.touch.active
        self.title_scene.draw(scr, self.t, menu, self.title_sel, mood, w)

    def draw_title_old(self, scr):
        scr.blit(self.title_bg, (0, 0))
        for b in self.bubbles:
            b.draw(scr)
        pygame.draw.rect(scr, (60, 50, 40), (0, 196, SCREEN_W, 36))
        for x in range(0, SCREEN_W, 16):
            scr.blit(gfx.TILES['overworld']['.'][x // 16 % 4], (x, 198))
        for x, ch in ((10, 'K'), (34, 'C'), (204, 'C'), (228, 'K')):
            scr.blit(gfx.TILES['overworld'][ch][0], (x, 182))
            scr.blit(gfx.TILES['overworld'][ch][-1], (x, 198))
        cycle = (self.t // 150) % 2
        mood = 'blue' if cycle == 0 else 'mad'
        phase = self.t % 150
        img = gfx.OCTO[mood]['down'][(self.t // 16) % 2]
        size = 96
        w = size
        if phase > 135:
            w = max(4, int(size * abs(math.cos((phase - 135) / 15 * math.pi / 2))))
        elif phase < 15 and self.t > 15:
            w = max(4, int(size * abs(math.sin(phase / 15 * math.pi / 2))))
        bob = int(math.sin(self.t * 0.05) * 4)
        big = pygame.transform.scale(img, (w, size))
        scr.blit(big, (SCREEN_W // 2 - w // 2, 92 + bob))
        self.big_text(scr, "LEGEND OF", SCREEN_W // 2 + 2, 22, (0, 0, 0))
        self.big_text(scr, "LEGEND OF", SCREEN_W // 2, 20, (255, 220, 120))
        self.big_text(scr, "OCTO", SCREEN_W // 2 + 3, 43, (0, 0, 0), 4)
        self.big_text(scr, "OCTO", SCREEN_W // 2, 40, (110, 170, 255) if mood == 'blue' else (190, 190, 205), 4)
        gfx.text(scr, "A REVERSIBLE UNDERSEA ADVENTURE", SCREEN_W // 2, 78, (200, 220, 255), center=True)
        if (self.t // 30) % 2:
            gfx.text(scr, "PRESS ENTER: NEW GAME", SCREEN_W // 2, 204, (255, 255, 255), center=True)
        if self.t % 30 == 1 or not hasattr(self, 'has_save'):
            self.has_save = save_exists()
        if self.has_save:
            gfx.text(scr, "PRESS L: LOAD SAVED GAME", SCREEN_W // 2, 213, (160, 230, 160), center=True)
        gfx.text(scr, "A FAN TRIBUTE", SCREEN_W // 2, 223, (140, 150, 180), center=True)

    def draw_gameover(self, scr):
        scr.fill((0, 0, 0))
        self.big_text(scr, "GAME OVER", SCREEN_W // 2, 70, (232, 60, 80))
        img = pygame.transform.scale(gfx.OCTO['mad']['down'][0], (48, 48))
        scr.blit(img, (SCREEN_W // 2 - 24, 100))
        if (self.t // 30) % 2:
            gfx.text(scr, "PRESS ENTER TO CONTINUE", SCREEN_W // 2, 170, center=True)
        gfx.text(scr, "ESC TO QUIT", SCREEN_W // 2, 186, (140, 140, 160), center=True)

    def draw_win(self, scr):
        scr.blit(self.title_bg, (0, 0))
        for b in self.bubbles:
            b.draw(scr)
        p = self.player
        pearl = pygame.transform.scale(gfx.SPR['golden'], (48, 48))
        bob = int(math.sin(self.t * 0.06) * 4)
        glow = pygame.Surface((90, 90), pygame.SRCALPHA)
        r = 40 + int(math.sin(self.t * 0.1) * 4)
        pygame.draw.circle(glow, (255, 220, 120, 50), (45, 45), r)
        scr.blit(glow, (SCREEN_W // 2 - 45, 46 + bob))
        scr.blit(pearl, (SCREEN_W // 2 - 24, 67 + bob))
        for i, mood in enumerate(('blue', 'mad')):
            img = pygame.transform.scale(gfx.OCTO[mood]['down'][(self.t // 12 + i) % 2], (32, 32))
            hop = abs(int(math.sin(self.t * 0.12 + i * 1.5) * 8))
            scr.blit(img, (SCREEN_W // 2 - 70 + i * 108, 82 - hop))
        self.big_text(scr, "VICTORY!", SCREEN_W // 2, 14, (255, 220, 120))
        lines = ["OCTO RECLAIMED THE GOLDEN PEARL", "AND THE REEF IS AT PEACE AGAIN.", "",
                 f"PEARLS: {p.pearls}", f"TIME: {self.frames // 3600}:{(self.frames // 60) % 60:02d}",
                 "", "THANKS FOR PLAYING!"]
        for i, l in enumerate(lines):
            gfx.text(scr, l, SCREEN_W // 2, 130 + i * 11, center=True)
        if self.t > 120 and (self.t // 30) % 2:
            gfx.text(scr, "PRESS ENTER", SCREEN_W // 2, 216, (255, 220, 120), center=True)
