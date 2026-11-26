"""Townsfolk you can talk to (octopuses in Octo City, turtles in Turtle Town), the Living Legend
statue, and the little floating score numbers."""
import math
import random

import pygame

import folk
import gfx
import style
import townart
from entities import Entity

_turtles = {}


def _turtle_frames(shell, skin, small):
    key = (shell, skin, small)
    if key not in _turtles:
        _turtles[key] = townart.turtle_folk(shell, skin, small)
    return _turtles[key]


def _solid(level, rect):
    if not level.bounds.contains(rect):
        return True
    for _, _, ch in level.tiles_in(rect):
        if level.solid(ch, 'walker'):
            return True
    return False


class Citizen(Entity):
    hb = (1, 2, 14, 13)

    def __init__(self, nid, x, y):
        super().__init__(x, y)
        self.id = nid
        self.d = folk.NPCS[nid]
        self.name = self.d['name']
        self.kind = self.d['kind']
        self.small = self.d.get('small', False)
        self.hat = self.d.get('hat')
        self.home = (float(x), float(y))
        self.t = random.randint(0, 300)
        self.facing = 'down'
        self.target = None
        self.wait = random.randint(40, 200)
        self.icon = None                   # set by the game: 'new', 'ready', 'busy', 'shop'
        self.hidden = bool(self.d.get('hidden'))
        self.moving = False
        self.talks = 0

    def place(self, x, y):
        self.x, self.y = float(x), float(y)
        self.home = (self.x, self.y)
        self.target = None

    def update(self, game):
        self.t += 1
        if self.hidden:
            return
        p = game.player
        dx = p.rect.centerx - self.rect.centerx
        dy = p.rect.centery - self.rect.centery
        self.moving = False
        if abs(dx) < 40 and abs(dy) < 32:               # stop and look at Octo
            self.target = None
            self.facing = ('right' if dx > 0 else 'left') if abs(dx) > abs(dy) else ('down' if dy > 0 else 'up')
            return
        if self.target is None:
            self.wait -= 1
            if self.wait <= 0:
                a = random.uniform(0, math.tau)
                r = random.uniform(6, 26)
                self.target = (self.home[0] + math.cos(a) * r, self.home[1] + math.sin(a) * r)
                self.wait = random.randint(90, 260)
            return
        tx, ty = self.target
        vx, vy = tx - self.x, ty - self.y
        d = math.hypot(vx, vy)
        if d < 1:
            self.target = None
            return
        sp = 0.22 if self.kind == 'turtle' else 0.34
        mx, my = vx / d * sp, vy / d * sp
        self.facing = ('right' if mx > 0 else 'left') if abs(mx) > abs(my) else ('down' if my > 0 else 'up')
        self.moving = True
        for ax in ('x', 'y'):
            old = getattr(self, ax)
            setattr(self, ax, old + (mx if ax == 'x' else my))
            r = self.rect
            if _solid(game.level, r) or r.colliderect(p.rect):
                setattr(self, ax, old)
                self.target = None

    def image(self):
        if self.kind == 'turtle':
            fr = _turtle_frames(tuple(self.d['shell']), tuple(self.d['skin']), self.small)
            return fr[1 if (self.t % 220) > 210 else 0]
        frames = gfx.OCTO['cit_' + self.id][self.facing]
        img = frames[(self.t // 14) % 2 if self.moving else (self.t // 40) % 2]
        if self.small:
            img = pygame.transform.scale(img, (12, 12))
        return img

    def draw(self, surf, ox=0, oy=0):
        if self.hidden:
            return
        img = self.image()
        bob = 0 if self.moving else (1 if (self.t // 30) % 2 else 0)
        x = round(self.x) + ox + (16 - img.get_width()) // 2
        y = round(self.y) + oy + (16 - img.get_height()) + bob
        surf.blit(img, (x, y))
        if self.hat:
            hy = y if not self.small else y - 3
            style.draw_hat(surf, self.hat, x + (img.get_width() - 16) // 2, hy, self.facing, self.t)
        if self.icon:
            self._icon(surf, round(self.x) + ox + 8, y - (14 if self.hat else 8))

    def _icon(self, surf, cx, cy):
        bob = round(math.sin(self.t * 0.12) * 1.5)
        cy += bob
        if self.icon == 'shop':
            pygame.draw.circle(surf, (120, 80, 0), (cx, cy), 4)
            pygame.draw.circle(surf, (255, 210, 60), (cx, cy), 3)
            surf.set_at((cx - 1, cy - 1), (255, 255, 220))
            return
        ch, col = {'new': ("!", (255, 220, 60)), 'ready': ("?", (255, 220, 60)),
                   'busy': ("?", (170, 170, 190)), 'chain': ("!", (120, 230, 255))}[self.icon]
        pygame.draw.rect(surf, (20, 20, 40), (cx - 4, cy - 5, 9, 11), border_radius=3)
        pygame.draw.rect(surf, col, (cx - 4, cy - 5, 9, 11), 1, border_radius=3)
        gfx.text(surf, ch, cx - 2, cy - 3, col, shadow=False)


class LegendStatue(Entity):
    """The plinth in Octo City's plaza. Pass the last milestone and a golden Octo stands on it."""
    hb = (0, 4, 16, 12)

    def __init__(self, x, y):
        super().__init__(x, y)
        self.t = 0
        self.lit = False
        self.hat = 'champion'
        self.name = "THE LIVING LEGEND"
        self._gold = None

    def update(self, game):
        self.t += 1
        self.lit = 'u_legend' in game.player.items
        self.hat = game.player.hat if game.player.hat not in (None, 'none') else 'champion'

    def draw(self, surf, ox=0, oy=0):
        x, y = round(self.x) + ox, round(self.y) + oy
        pygame.draw.rect(surf, (90, 80, 110), (x - 2, y + 8, 20, 9))
        pygame.draw.rect(surf, (200, 190, 220), (x - 1, y + 8, 18, 7))
        pygame.draw.line(surf, (255, 255, 255), (x - 1, y + 8), (x + 16, y + 8))
        if not self.lit:
            gfx.text(surf, "?", x + 6, y + 1, (150, 140, 170))
            return
        if self._gold is None:
            g = gfx.OCTO['blue']['down'][0].copy()
            g.fill((255, 215, 90, 255), special_flags=pygame.BLEND_RGBA_MULT)
            g.fill((60, 40, 0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            self._gold = g
        surf.blit(self._gold, (x, y - 6))
        style.draw_hat(surf, self.hat, x, y - 6, 'down', self.t)
        if (self.t // 8) % 6 == 0:
            sx, sy = x + 3 + (self.t // 16) % 10, y - 4 + (self.t // 7) % 9
            pygame.draw.line(surf, (255, 255, 255), (sx - 2, sy), (sx + 2, sy))
            pygame.draw.line(surf, (255, 255, 255), (sx, sy - 2), (sx, sy + 2))


class ScorePop:
    """A little "+50" that floats up from where points were earned."""

    def __init__(self, x, y, pts, col=(255, 230, 120)):
        self.x, self.y = x, y
        self.text = f"+{pts}"
        self.col = col
        self.t = 0
        self.dead = False

    def update(self, game):
        self.t += 1
        self.y -= 0.5
        if self.t > 40:
            self.dead = True

    def draw(self, surf, ox=0, oy=0):
        if self.t > 30 and self.t % 4 < 2:
            return
        gfx.text(surf, self.text, int(self.x) + ox - gfx.text_width(self.text) // 2, int(self.y) + oy, self.col)
