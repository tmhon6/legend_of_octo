"""Player two: Pebble, Octo's pet snail.

Pebble joins on the same screen: arrow keys (or a gamepad) to slide about, Right Ctrl / . / 0 on
the number pad (or button A) to spit slime, / or Right Shift (button B) to tuck into his shell and
spin. Slime slows what it hits; a spinning shell can't be hurt and bowls enemies over. If Pebble
loses all his hearts he hides in his shell for a few seconds, then pops back out next to Octo.
He never leaves the screen: if Octo goes somewhere new, Pebble comes along.

Coop is mixed into Game.
"""
import math
import random

import pygame

import gfx
import sound
from entities import Entity, Particle
from settings import PLAYER_SPEED

P2_DIRS = {pygame.K_UP: 'up', pygame.K_DOWN: 'down', pygame.K_LEFT: 'left', pygame.K_RIGHT: 'right'}
P2_SPIT = {pygame.K_RCTRL, pygame.K_PERIOD, pygame.K_KP0, pygame.K_KP_ENTER}
P2_SPIN = {pygame.K_SLASH, pygame.K_RSHIFT, pygame.K_KP_PERIOD}
DIRV = {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}
NAME = "PEBBLE"

SHELL, SHELL_D, SHELL_L = (236, 146, 72), (160, 82, 40), (255, 214, 150)
BODY, BODY_D, BODY_L = (186, 214, 104), (112, 150, 64), (226, 244, 168)
INK = (52, 32, 30)


# ======================================================================
# Pebble's pixel art
# ======================================================================
def _shell(s, cx, cy, r):
    pygame.draw.circle(s, INK, (cx, cy), r + 1)
    pygame.draw.circle(s, SHELL, (cx, cy), r)
    pygame.draw.circle(s, SHELL_D, (cx + 1, cy + 1), max(1, r - 2), 1)       # the spiral
    pygame.draw.circle(s, SHELL_D, (cx + 1, cy + 1), max(1, r - 4), 1)
    s.set_at((cx + 1, cy + 1), SHELL_D)
    s.set_at((cx - r + 2, cy - r + 2), SHELL_L)
    s.set_at((cx - r + 3, cy - r + 2), SHELL_L)
    s.set_at((cx - r + 2, cy - r + 3), SHELL_L)


def _eye(s, x, y_top, y_base):
    pygame.draw.line(s, INK, (x, y_base), (x, y_top + 1))
    s.set_at((x, y_top), (255, 255, 255))
    s.set_at((x, y_top + 1), (20, 20, 30))


def _side(frame):
    s = pygame.Surface((16, 16), pygame.SRCALPHA)
    st = frame                                            # the foot stretches as he slides
    pygame.draw.rect(s, INK, (0, 10, 15, 5), border_radius=2)
    pygame.draw.rect(s, BODY_D, (1, 11, 13, 3), border_radius=1)
    pygame.draw.line(s, BODY, (2, 11), (12, 11))
    pygame.draw.rect(s, INK, (10 + st, 4, 5, 10), border_radius=2)          # head and neck
    pygame.draw.rect(s, BODY, (11 + st, 5, 3, 8))
    s.set_at((12 + st, 5), BODY_L)
    s.set_at((13 + st, 9), INK)                                             # a little smile
    _eye(s, 11 + st, 0 + frame, 5)
    _eye(s, 13 + st, 1 - frame + 1, 5)
    _shell(s, 6, 7, 5)
    return s


def _front(frame):
    s = pygame.Surface((16, 16), pygame.SRCALPHA)
    _shell(s, 8, 6, 5)                                    # his shell peeks up behind him
    pygame.draw.rect(s, INK, (4, 7, 8, 8), border_radius=3)
    pygame.draw.rect(s, BODY, (5, 8, 6, 6), border_radius=2)
    pygame.draw.line(s, BODY_L, (6, 8), (9, 8))
    pygame.draw.line(s, BODY_D, (5, 13), (10, 13))
    s.set_at((7, 11), INK)
    s.set_at((8, 11), INK)
    s.set_at((6, 10), (250, 150, 160))
    s.set_at((9, 10), (250, 150, 160))
    _eye(s, 5 - frame, 1, 8)
    _eye(s, 10 + frame, 1, 8)
    return s


def _back(frame):
    s = pygame.Surface((16, 16), pygame.SRCALPHA)
    pygame.draw.rect(s, INK, (4, 10, 8, 5), border_radius=2)
    pygame.draw.rect(s, BODY_D, (5, 11, 6, 3))
    _eye(s, 5 - frame, 1, 7)
    _eye(s, 10 + frame, 1, 7)
    _shell(s, 8, 8, 6)
    return s


_frames = None


def frames():
    global _frames
    if _frames is None:
        right = [_side(0), _side(1)]
        _frames = {'right': right, 'left': [pygame.transform.flip(f, True, False) for f in right],
                   'down': [_front(0), _front(1)], 'up': [_back(0), _back(1)],
                   'shell': _shell_only()}
    return _frames


def _shell_only():
    s = pygame.Surface((16, 16), pygame.SRCALPHA)
    _shell(s, 8, 9, 6)
    return s


# ======================================================================
# Pebble
# ======================================================================
class Snail(Entity):
    hb = (3, 6, 10, 9)
    who = 'player'
    MAX_HP = 6
    SPIN_FRAMES = 22
    SPIN_COOLDOWN = 70

    def __init__(self, x, y):
        super().__init__(x, y)
        self.facing = 'down'
        self.hp = self.max_hp = self.MAX_HP
        self.invuln = 60
        self.knock_t = 0
        self.knock = (0, 0)
        self.t = 0
        self.walk_t = 0
        self.moving = False
        self.shoot_cd = 0
        self.spin_t = 0
        self.spin_cd = 0
        self.spin_dir = (0, 1)
        self.spin_hits = set()
        self.down_t = 0                 # hiding in his shell after losing all his hearts
        self.anim = 0

    @property
    def resting(self):
        return self.down_t > 0

    def hurt(self, game, dmg, src):
        if self.invuln or self.spin_t or self.down_t or dmg <= 0:
            return
        self.hp = max(0, self.hp - dmg)
        self.invuln = 70
        sx, sy = src
        cx, cy = self.rect.center
        dx, dy = cx - sx, cy - sy
        self.knock = ((3 if dx > 0 else -3), 0) if abs(dx) > abs(dy) else (0, (3 if dy > 0 else -3))
        self.knock_t = 8
        sound.play('hurt')
        if self.hp <= 0:
            self.down_t = 300
            game.toast = (f"{NAME} HIDES IN HIS SHELL... BACK SOON!", 120)
            game.burst(self.rect.center, SHELL, 10)

    def spit(self, game):
        if self.shoot_cd or self.spin_t or self.down_t:
            return
        dx, dy = DIRV[self.facing]
        cx, cy = self.rect.center
        game.shots.append(Slime(cx - 3 + dx * 7, cy - 4 + dy * 7, dx * 3.2, dy * 3.2))
        self.shoot_cd = 20
        sound.play('bubble')

    def spin(self, game):
        if self.spin_cd or self.spin_t or self.down_t:
            return
        self.spin_t = self.SPIN_FRAMES
        self.spin_cd = self.SPIN_COOLDOWN
        self.spin_dir = DIRV[self.facing]
        self.spin_hits = set()
        sound.play('jet')

    def update(self, game, move, vec=None):
        self.t += 1
        for k in ('invuln', 'shoot_cd', 'spin_cd'):
            if getattr(self, k):
                setattr(self, k, getattr(self, k) - 1)
        lv = game.level
        if self.down_t:
            self.down_t -= 1
            if self.down_t == 0:
                self.hp = self.max_hp
                self.invuln = 90
                game.coop_regroup(force=True)
                sound.play('heart')
            return
        if self.knock_t:
            self.knock_t -= 1
            self.move(self.knock[0], self.knock[1], lv)
            return
        if self.spin_t:                                   # shell spin: a bowling ball nothing can hurt
            self.spin_t -= 1
            dx, dy = self.spin_dir
            if not self.move(dx * 3.4, dy * 3.4, lv):
                self.spin_t = 0
                sound.play('tink')
            for e in game.enemies:
                if e.active and e not in self.spin_hits and self.rect.inflate(4, 4).colliderect(e.rect):
                    self.spin_hits.add(e)
                    e.hurt_t = 0
                    e.hit(game, 2, 'shell', self.rect.center)
            if self.t % 3 == 0:
                game.effects.append(Particle(*self.rect.center, -dx * 0.5, -dy * 0.5, SHELL_L, 12))
            return
        mx, my = 0.0, 0.0
        if vec:
            mx, my = vec
        elif move:
            mx, my = DIRV[move]
        self.moving = bool(mx or my)
        if self.moving:
            if abs(mx) > abs(my):
                self.facing = 'right' if mx > 0 else 'left'
            else:
                self.facing = 'down' if my > 0 else 'up'
            sp = PLAYER_SPEED * 0.95
            self.move(mx * sp, my * sp, lv)
            self.walk_t += 1
            if self.walk_t % 9 == 0:                     # a little slime trail
                cx, cy = self.rect.midbottom
                game.effects.append(Particle(cx + random.uniform(-3, 3), cy - 1, 0, 0, (200, 235, 170), 26))
        self.anim = (self.walk_t // 10) % 2 if self.moving else (self.t // 40) % 2

    def image(self):
        f = frames()
        if self.down_t or self.spin_t:
            return f['shell']
        return f[self.facing][self.anim]

    def draw(self, surf, ox=0, oy=0):
        """The flat pixel-art Pebble (used when the 3D layer can't draw him)."""
        if self.invuln and (self.invuln // 3) % 2 and not self.knock_t and not self.down_t:
            return
        img = self.image()
        if self.spin_t:
            img = pygame.transform.rotate(img, self.t * 40 % 360)
        surf.blit(img, (round(self.x) + ox + 8 - img.get_width() // 2, round(self.y) + oy + 8 - img.get_height() // 2))


class Slime(Entity):
    """A glob of sticky slime: it stings a little and slows what it hits."""
    who = 'shot'
    hb = (0, 0, 7, 7)

    def __init__(self, x, y, vx, vy):
        super().__init__(x, y)
        self.vx, self.vy = vx, vy
        self.life = 50
        self.t = 0

    def update(self, game):
        self.t += 1
        self.life -= 1
        self.x += self.vx
        self.y += self.vy
        r = self.rect
        if self.life <= 0 or game.level.blocked(r, 'shot') or not game.view_rect.colliderect(r):
            self.dead = True
            game.splat(r.center, (190, 230, 120))
            return
        for e in game.enemies:
            if e.active and r.colliderect(e.rect):
                e.hurt_t = 0
                if e.hit(game, 1, 'slime', r.center):
                    e.slow = max(getattr(e, 'slow', 0), 90 if getattr(e, 'boss', False) else 200)
                game.splat(r.center, (190, 230, 120))
                self.dead = True
                return

    def draw(self, surf, ox=0, oy=0):
        x, y = round(self.x) + ox, round(self.y) + oy
        pygame.draw.circle(surf, (90, 140, 50), (x + 3, y + 3), 4)
        pygame.draw.circle(surf, (190, 235, 120), (x + 3, y + 3), 3)
        surf.set_at((x + 2, y + 2), (250, 255, 230))


# ======================================================================
# the game side of co-op
# ======================================================================
class Coop:
    def coop_setup(self):
        self.snail = None
        self.p2_held = []
        self.joys = {}
        try:
            pygame.joystick.init()
            for i in range(pygame.joystick.get_count()):
                j = pygame.joystick.Joystick(i)
                self.joys[j.get_instance_id()] = j
        except Exception as e:
            print("joystick:", e)

    @property
    def coop(self):
        return self.snail is not None

    def coop_join(self, quiet=False):
        if self.snail is not None or self.player is None:
            return
        p = self.player
        self.snail = Snail(p.x, p.y)
        self.flags['coop'] = True
        self.coop_regroup(force=True)
        if not quiet:
            sound.play('item')
            self.burst(self.snail.rect.center, BODY_L, 12)
            self.toast = (f"{NAME} JOINS! ARROWS + RIGHT CTRL", 180)

    def coop_leave(self):
        if self.snail is None:
            return
        self.burst(self.snail.rect.center, BODY_L, 10)
        self.snail = None
        self.flags['coop'] = False
        self.p2_held = []
        self.toast = (f"{NAME} WAVES BYE-BYE", 100)
        sound.play('pause')

    def coop_event(self, ev):
        """Player two's keys and gamepads. Returns True when the event was Pebble's."""
        t = ev.type
        if t == pygame.JOYDEVICEADDED:
            try:
                j = pygame.joystick.Joystick(ev.device_index)
                self.joys[j.get_instance_id()] = j
            except Exception as e:
                print("joystick:", e)
            return True
        if t == pygame.JOYDEVICEREMOVED:
            self.joys.pop(getattr(ev, 'instance_id', None), None)
            return True
        if t == pygame.JOYBUTTONDOWN:
            if self.state == 'play':
                if self.snail is None and ev.button in (0, 7, 9):
                    self.coop_join()
                elif self.snail is not None and ev.button == 0:
                    self.snail.spit(self)
                elif self.snail is not None and ev.button == 1:
                    self.snail.spin(self)
            elif ev.button == 0:
                self.on_key(pygame.K_RETURN)
            return True
        if t not in (pygame.KEYDOWN, pygame.KEYUP):
            return False
        k = ev.key
        if t == pygame.KEYUP:
            if k in P2_DIRS and self.snail is not None:
                d = P2_DIRS[k]
                if d in self.p2_held:
                    self.p2_held.remove(d)
                return True
            return False
        if self.state != 'play':
            return False
        if self.snail is None:
            if k in P2_SPIT:
                self.coop_join()
                return True
            return False
        if k in P2_DIRS:
            d = P2_DIRS[k]
            if d in self.p2_held:
                self.p2_held.remove(d)
            self.p2_held.append(d)
            return True
        if k in P2_SPIT:
            self.snail.spit(self)
            return True
        if k in P2_SPIN:
            self.snail.spin(self)
            return True
        return False

    def _joy_vec(self):
        for j in self.joys.values():
            try:
                x, y = j.get_axis(0), j.get_axis(1)
                if j.get_numhats():
                    hx, hy = j.get_hat(0)
                    if hx or hy:
                        x, y = hx, -hy
                if math.hypot(x, y) > 0.3:
                    d = math.hypot(x, y)
                    k = min(1.0, d)
                    return x / d * k, y / d * k
            except Exception:
                continue
        return None

    def coop_update(self):
        s = self.snail
        if s is None:
            return
        move = self.p2_held[-1] if self.p2_held else None
        s.update(self, move, self._joy_vec())
        if not s.resting:
            # stay on screen with Octo: pushed along at the edges, or brought back if left behind
            view = self.view_rect.inflate(-8, -8)
            r = s.rect
            if not self.view_rect.inflate(48, 48).colliderect(r):
                self.coop_regroup(force=True)
            elif not view.contains(r):
                nx = min(max(r.x, view.left), view.right - r.w) - r.x
                ny = min(max(r.y, view.top), view.bottom - r.h) - r.y
                s.x += nx
                s.y += ny
                if self.level.blocked(s.rect, 'player'):
                    self.coop_regroup(force=True)
            # enemies bump him, and he picks things up too
            for e in self.enemies:
                if e.active and not e.frozen and e.rect.colliderect(s.rect):
                    s.hurt(self, e.damage, e.rect.center)
            for it in self.pickups:
                if not it.dead and it.rect.colliderect(s.rect) and it.kind not in ('bell', 'golden', 'halfpearl'):
                    self.collect(it, by=s)

    def coop_regroup(self, force=False):
        """Put Pebble on a free spot right next to Octo."""
        s, p = self.snail, self.player
        if s is None:
            return
        for dx, dy in ((-16, 0), (16, 0), (0, 14), (0, -14), (-16, 14), (16, 14), (-16, -14), (16, -14), (0, 0)):
            s.x, s.y = p.x + dx, p.y + dy
            if not self.level.blocked(s.rect, 'player') and self.view_rect.contains(s.rect):
                break
        s.knock_t = s.spin_t = 0
        self.p2_held = [d for d in self.p2_held]

    def coop_hit_by_shot(self, shot):
        """Called by enemy shots: did one hit Pebble?"""
        s = self.snail
        if s is None or s.resting:
            return False
        if shot.rect.colliderect(s.rect):
            s.hurt(self, shot.damage, shot.rect.center)
            return True
        return False

    def draw_snail_2d(self, ps, ox, oy):
        s = self.snail
        if s is None:
            return
        import fx
        if not s.resting:
            fx.shadow(ps, s.rect, ox, oy)

    def draw_snail_hud(self, scr, x, y):
        s = self.snail
        if s is None:
            return
        scr.blit(pygame.transform.scale(frames()['right'][0], (10, 10)), (x, y - 1))
        for i in range(s.max_hp // 2):
            if s.hp >= (i + 1) * 2:
                img = gfx.SPR['heart']['full']
            elif s.hp == i * 2 + 1:
                img = gfx.SPR['heart']['half']
            else:
                img = gfx.SPR['heart']['empty']
            scr.blit(img, (x + 12 + i * 8, y))

