"""Player, enemies, projectiles, pickups and effects."""
import math
import random

import pygame

import forms
import fx
import gfx
import sound
from settings import PLAYER_SPEED

DIRS = {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}


JET_FRAMES = 12          # speed-burst length
JET_SPEED = 4            # px per frame while jetting
JET_COOLDOWN = 40
SLAP_AIM_RANGE = 32      # px between centres: about the slap's real reach
# attacks that STRONG forms (and fused forms) power up
PLAYER_HIT_KINDS = {'ink', 'slap', 'zap', 'ice', 'wisp', 'spike', 'glow', 'bubble', 'bomb', 'thorns',
                    'hail', 'whip', 'roll', 'quake', 'lantern', 'whirl', 'trap', 'chain', 'nova', 'shell',
                    'star', 'mine', 'boulder'}
INK_AIM_RANGE = 200      # px: ink homes its launch angle on enemies this close (on screen)


def sign(v):
    return (v > 0) - (v < 0)


def cardinal(dx, dy):
    if abs(dx) >= abs(dy):
        return 'right' if dx >= 0 else 'left'
    return 'down' if dy >= 0 else 'up'


class Entity:
    hb = (2, 2, 12, 12)          # hitbox offset x, y, w, h
    who = 'walker'

    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.dead = False

    @property
    def rect(self):
        return pygame.Rect(math.floor(self.x) + self.hb[0], math.floor(self.y) + self.hb[1],
                           self.hb[2], self.hb[3])

    @property
    def center(self):
        return self.rect.center

    def move(self, dx, dy, room):
        ok = True
        if dx:
            self.x += dx
            if room.blocked(self.rect, self.who):
                self.x -= dx
                ok = False
        if dy:
            self.y += dy
            if room.blocked(self.rect, self.who):
                self.y -= dy
                ok = False
        return ok


# ===========================================================================
# Player
# ===========================================================================

class Player(Entity):
    hb = (3, 5, 10, 10)
    who = 'player'

    def __init__(self, x, y):
        super().__init__(x, y)
        self.facing = 'down'
        self.mood = 'blue'
        self.forms = ['blue', 'mad']    # trials add 'zap', 'ice' and 'ghost'
        self.next_mood = 'mad'
        self.ink_mode = 'line'      # 'line': long-range stream, 'burst': short wide fan
        self.max_hp = 6
        self.hp = 6
        self.pearls = 0
        self.keys = 0
        self.bombs = 0
        self.items = set()          # passive upgrades: 'fins', 'shield', 'deepink', 'bombbag'
        self.dash_t = 0
        self.dash_cd = 0
        self.bubble_t = 0
        self.fog_t = 0
        self.fog_cd = 0
        self.regen_t = 0
        self.idle_t = 0
        self.spirit = 0          # spirit pearls from trials, traded at the temple altar
        self.potions = 0         # sea potions: save Octo once each when he'd fall
        self.analog = None       # (x, y) from the touch joystick, length up to 1
        self.roll_t = 0
        self.roll_dir = (0, 0)
        self.decoy = (0.0, 0.0)
        self.sphere = 0          # water-sphere strength while in the sky (0 = popped / none)
        self.in_sky = False
        self.roll = 0.0          # how far the sphere has rolled (for drawing)
        self.roll_v = [0.0, 0.0]
        self.tumble = 0          # >0 while falling out of the sky
        self.dash_dir = (0, 0)
        self.anim = 0
        self.walk_t = 0
        self.attack_t = 0
        self.slap_id = 0
        self.shoot_cd = 0
        self.flip_t = 0
        self.invuln = 0
        self.knock_t = 0
        self.knock = (0, 0)

    # -- actions -----------------------------------------------------------
    def action(self, game):
        if self.attack_t or self.flip_t or self.knock_t:
            return
        cx, cy = self.rect.center
        if self.mood not in ('blue', 'mad'):
            self.special(game, cx, cy)
            return
        if self.mood == 'mad':
            # turn to slap the nearest enemy within reach
            target = game.nearest_enemy((cx, cy), SLAP_AIM_RANGE)
            if target:
                tx, ty = target.rect.center
                self.facing = cardinal(tx - cx, ty - cy)
            self.attack_t = 16
            self.slap_id += 1
            sound.play('slap')
        else:
            if self.shoot_cd:
                return
            # squirt straight at the nearest on-screen enemy
            target = game.nearest_enemy((cx, cy), INK_AIM_RANGE)
            if target:
                tx, ty = target.rect.center
                d = math.hypot(tx - cx, ty - cy) or 1
                dx, dy = (tx - cx) / d, (ty - cy) / d
                self.facing = cardinal(dx, dy)
            else:
                dx, dy = DIRS[self.facing]
            sx, sy = cx - 4 + dx * 8, cy - 4 + dy * 8
            if self.ink_mode == 'line':
                if sum(1 for s in game.shots if isinstance(s, Ink)) >= 6:
                    return
                for i in range(3):          # three drops in single file
                    game.shots.append(Ink(sx, sy, dx * 4.0, dy * 4.0, life=60, wait=i * 4))
                self.shoot_cd = 18
            else:
                base = math.atan2(dy, dx)
                for da in (-0.6, -0.3, 0.0, 0.3, 0.6):     # five drops fanned out
                    a = base + da
                    game.shots.append(Ink(sx, sy, math.cos(a) * 3.2, math.sin(a) * 3.2, life=15))
                self.shoot_cd = 24
            self.attack_t = 8
            sound.play('ink')

    def special(self, game, cx, cy):
        """Attacks of the forms won in the trials."""
        if self.mood == 'air':
            # fog cloak: enemies lose sight of Octo and go after the spot where he vanished.
            # It has its own cooldown so other forms can still attack from inside the fog.
            if self.fog_cd:
                sound.play('nope')
                return
            self.fog_t = self.FOG_FRAMES
            self.decoy = (float(cx), float(cy))
            self.fog_cd = self.FOG_FRAMES + 60
            self.attack_t = 10
            for i in range(14):
                a = i / 14 * math.tau
                game.effects.append(Particle(cx, cy, math.cos(a) * 1.4, math.sin(a) * 1.4,
                                             (230, 236, 245), 30))
            sound.play('whoosh')
            return
        if self.shoot_cd:
            return
        if self.mood in forms.FUSIONS or self.mood in forms.OWN_SHAPE:
            self.fusion_attack(game, cx, cy)
            return
        if self.mood == 'bubble':
            # bubble shield: nothing can hurt Octo for a few seconds, and it shoves enemies away
            self.bubble_t = 150
            self.shoot_cd = 260
            sound.play('bubble')
            return
        if self.mood == 'spiky':
            # spines in all eight directions
            for i in range(8):
                a = i / 8 * math.tau
                game.shots.append(Spine(cx - 3 + math.cos(a) * 6, cy - 3 + math.sin(a) * 6,
                                        math.cos(a) * 3.2, math.sin(a) * 3.2))
            self.shoot_cd = 30
            self.attack_t = 8
            sound.play('shoot')
            return
        if self.mood == 'glow':
            # blinding flash: stuns and stings every enemy on screen
            game.glow_flash = 14
            # balance: a short daze for everything on screen, damage only up close, long recharge
            for e in list(game.enemies):
                if e.active and game.view_rect.colliderect(e.rect):
                    if math.hypot(e.rect.centerx - cx, e.rect.centery - cy) < 56:
                        e.hit(game, 1, 'glow', (cx, cy))
                    if not e.dead:
                        e.frozen = max(e.frozen, 15 if getattr(e, 'boss', False) else 45)
            self.shoot_cd = 240
            self.attack_t = 10
            sound.play('warp')
            return
        if self.mood == 'zap':
            # shock ring: hits everything around Octo, even urchins and jellies
            game.shots.append(ZapRing(cx, cy))
            self.shoot_cd = 42
            self.attack_t = 10
            sound.play('zap')
            return
        target = game.nearest_enemy((cx, cy), INK_AIM_RANGE)
        if target:
            tx, ty = target.rect.center
            d = math.hypot(tx - cx, ty - cy) or 1
            dx, dy = (tx - cx) / d, (ty - cy) / d
            self.facing = cardinal(dx, dy)
        else:
            dx, dy = DIRS[self.facing]
        if self.mood == 'ice':
            game.shots.append(IceShard(cx - 4 + dx * 8, cy - 4 + dy * 8, dx * 3.6, dy * 3.6))
            self.shoot_cd = 44
            sound.play('ice')
        else:
            # two wisps curl out to either side, then home in on enemies (through walls!)
            base = math.atan2(dy, dx)
            for da in (-1.1, 1.1):
                a = base + da
                game.shots.append(Wisp(cx - 4, cy - 4, math.cos(a) * 2.0, math.sin(a) * 2.0))
            self.shoot_cd = 40
            sound.play('wisp')
        self.attack_t = 8

    def aim(self, game, cx, cy, reach=None):
        """Unit vector towards the nearest enemy (or the way Octo faces)."""
        target = game.nearest_enemy((cx, cy), reach or INK_AIM_RANGE)
        if target:
            tx, ty = target.rect.center
            d = math.hypot(tx - cx, ty - cy) or 1
            dx, dy = (tx - cx) / d, (ty - cy) / d
            self.facing = cardinal(dx, dy)
            return dx, dy
        return DIRS[self.facing]

    def fusion_attack(self, game, cx, cy):
        """Attacks built from a shape and an element: every fused form, plus the newer base forms."""
        if self.mood in forms.FUSIONS:
            f = forms.FUSIONS[self.mood]
            self.cast(game, f['shape'], f['element'], cx, cy)
        else:
            self.cast(game, forms.OWN_SHAPE[self.mood], 'pull' if self.mood == 'magnet' else None, cx, cy)

    def cast(self, game, shape, elem, cx, cy):
        col = forms.ELEMENTS[elem][2] if elem in forms.ELEMENTS else None
        self.attack_t = 10
        if shape == 'hail':
            seen = [e for e in game.enemies if e.active and game.view_rect.colliderect(e.rect)]
            seen.sort(key=lambda e: math.hypot(e.rect.centerx - cx, e.rect.centery - cy))
            spots = [e.rect.center for e in seen[:6]] or \
                [(cx + math.cos(a) * 40, cy + math.sin(a) * 40) for a in (0.5, 2.6, 4.7)]
            for i, (tx, ty) in enumerate(spots):
                game.shots.append(Hail(tx, ty, delay=i * 6, elem=elem))
            self.shoot_cd = 75
            sound.play('zap')
        elif shape == 'whip':
            dx, dy = self.aim(game, cx, cy, 60)
            game.shots.append(InkWhip(self, math.atan2(dy, dx), elem))
            self.shoot_cd = 26
            sound.play('slap')
        elif shape == 'roll':
            self.roll_dir = self.aim(game, cx, cy)
            self.roll_t = 34
            self.roll_elem = elem
            self.attack_t = 0
            self.roll_hits = set()
            self.shoot_cd = 55
            sound.play('jet')
        elif shape == 'quake':
            for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                game.shots.append(Quake(cx, cy, d, elem))
            game.shake = 10
            self.shoot_cd = 60
            sound.play('boom')
        elif shape == 'lantern':
            if any(isinstance(s, Lantern) for s in game.shots):
                sound.play('nope')
                return
            game.shots.append(Lantern(self, elem))
            self.shoot_cd = 40
            sound.play('wisp')
        elif shape == 'whirl':
            if any(isinstance(s, Whirlpool) for s in game.shots):
                sound.play('nope')
                return
            dx, dy = self.aim(game, cx, cy)
            game.shots.append(Whirlpool(cx, cy, dx, dy, elem))
            self.shoot_cd = 60
            sound.play('whoosh')
        elif shape == 'trap':
            dx, dy = self.aim(game, cx, cy)
            game.shots.append(TrapBubble(cx - 6 + dx * 8, cy - 6 + dy * 8, dx * 2.4, dy * 2.4, elem))
            self.shoot_cd = 40
            sound.play('bubble')
        elif shape == 'chain':
            hit, (px, py) = [], (cx, cy)
            for reach in (130, 90, 90, 90, 90):
                best = None
                for e in game.enemies:
                    if e.active and e not in hit and game.view_rect.colliderect(e.rect):
                        d = math.hypot(e.rect.centerx - px, e.rect.centery - py)
                        if d < reach and (best is None or d < best[0]):
                            best = (d, e)
                if not best:
                    break
                hit.append(best[1])
                px, py = best[1].rect.center
            for e in hit:
                strike(game, e, 2, 'chain', (cx, cy), elem)
            points = [(cx, cy)] + [e.rect.center for e in hit]
            if len(points) == 1:
                points.append((cx + DIRS[self.facing][0] * 24, cy + DIRS[self.facing][1] * 24))
            game.effects.append(Bolt(points, col))
            self.shoot_cd = 45
            sound.play('zap')
        elif shape == 'nova':
            game.shots.append(Nova(cx, cy, elem))
            if elem == 'pull':          # Magnety: every pickup on screen comes flying in
                for it in game.pickups:
                    if it.kind != 'orb' and game.view_rect.colliderect(it.rect):
                        it.pulled = True
            self.shoot_cd = 70
            sound.play('warp')
        elif shape == 'boomerang':
            if sum(isinstance(s, Boomerang) for s in game.shots) >= 1:
                sound.play('nope')
                return
            dx, dy = self.aim(game, cx, cy)
            game.shots.append(Boomerang(self, dx, dy, elem))
            self.shoot_cd = 20
            sound.play('whoosh')
        elif shape == 'seekers':
            dx, dy = self.aim(game, cx, cy)
            base = math.atan2(dy, dx)
            for da in (-0.9, 0, 0.9):
                game.shots.append(Seeker(cx - 3, cy - 3, base + da, elem))
            self.shoot_cd = 50
            sound.play('pearl')
        elif shape == 'mines':
            mines = [s for s in game.shots if isinstance(s, Mine)]
            if len(mines) >= 3:
                mines[0].dead = True
            game.shots.append(Mine(cx - 5, cy - 5, elem))
            self.shoot_cd = 24
            sound.play('bubble')
        elif shape == 'boulder':
            if any(isinstance(s, Boulder) for s in game.shots):
                sound.play('nope')
                return
            dx, dy = DIRS[self.facing] if not game.nearest_enemy((cx, cy), 120) else self.aim(game, cx, cy)
            game.shots.append(Boulder(cx, cy, dx, dy, elem))
            self.shoot_cd = 50
            sound.play('shut')

    def _roll_update(self, game):
        """Prickly's spike roll: barrel along, bounce off walls, spike everything in the way."""
        self.roll_t -= 1
        dx, dy = self.roll_dir
        for _ in range(3):
            if not self.move(dx * 1.2, 0, game.level):
                dx = -dx
            if not self.move(0, dy * 1.2, game.level):
                dy = -dy
        self.roll_dir = (dx, dy)
        r = self.rect.inflate(6, 6)
        for e in game.enemies:
            if e.active and e not in self.roll_hits and r.colliderect(e.rect):
                self.roll_hits.add(e)
                strike(game, e, 2, 'roll', self.rect.center, getattr(self, 'roll_elem', None))
        if self.roll_t % 3 == 0:
            game.effects.append(Particle(*self.rect.center, -dx * 0.6, -dy * 0.6, (255, 200, 120), 14))

    def jet(self, game, move_dir):
        """Speed burst: shoot backwards out of a puff of ink."""
        if self.dash_t or self.dash_cd or self.flip_t or self.knock_t:
            return
        self.attack_t = 0           # a jet cancels a slap or squirt
        d = move_dir or self.facing
        self.facing = d
        self.dash_dir = DIRS[d]
        self.dash_t = JET_FRAMES + (4 if 'fins' in self.items else 0)
        self.dash_cd = int(JET_COOLDOWN * self.stat('jet', 1.0) * (0.6 if 'jetink' in self.items else 1.0))
        cx, cy = self.rect.center
        game.shots.append(InkCloud(cx - self.dash_dir[0] * 4, cy - self.dash_dir[1] * 4))
        sound.play('jet')

    def drop_bomb(self, game):
        if self.attack_t or self.flip_t or self.knock_t:
            return
        if self.bombs <= 0 or any(isinstance(s, Bomb) for s in game.shots):
            sound.play('nope')
            return
        self.bombs -= 1
        dx, dy = DIRS[self.facing]
        cx, cy = self.rect.center
        b = Bomb(cx + dx * 12 - 4, cy + dy * 12 - 5)
        if game.level.blocked(b.rect, 'shot'):
            b.x, b.y = cx - 4, cy - 5
        game.shots.append(b)
        sound.play('shut')

    def stat(self, key, default=0):
        """This form's strength (see forms.py)."""
        return forms.stat(self.mood, key, default)

    def speed(self):
        return PLAYER_SPEED * (1.35 if 'fins' in self.items else 1.0) * self.stat('speed', 1.0)

    def toggle_ink(self):
        self.ink_mode = 'burst' if self.ink_mode == 'line' else 'line'
        sound.play('pause')

    def pick_form(self, i):
        if i < len(self.forms) and self.forms[i] != self.mood and not (self.flip_t or self.attack_t):
            self.next_mood = self.forms[i]
            self.flip_t = 14
            sound.play('flip')

    def flip(self):
        if self.flip_t or self.attack_t:
            return
        i = self.forms.index(self.mood) if self.mood in self.forms else -1
        self.next_mood = self.forms[(i + 1) % len(self.forms)]
        self.flip_t = 14
        sound.play('flip')

    def slap_rect(self):
        x, y = math.floor(self.x), math.floor(self.y)
        return {
            'right': pygame.Rect(x + 12, y - 7, 16, 30),
            'left': pygame.Rect(x - 12, y - 7, 16, 30),
            'down': pygame.Rect(x - 7, y + 12, 30, 16),
            'up': pygame.Rect(x - 7, y - 12, 30, 16),
        }[self.facing]

    FOG_FRAMES = 300
    SPHERE_MAX = 4

    def seen_pos(self):
        """Where enemies think Octo is: his real spot, or the decoy while he hides in fog."""
        return self.decoy if self.fog_t else self.rect.center

    def slap_active(self):
        return self.mood == 'mad' and 3 <= self.attack_t <= 13

    def hurt(self, game, dmg, src):
        if self.invuln or self.dash_t or self.bubble_t or self.tumble or self.roll_t or dmg <= 0:
            return
        dmg = max(1, dmg - self.stat('armor', 0) - (1 if 'armor' in self.items else 0))
        if self.in_sky and self.sphere > 0:
            # the water sphere takes the hit instead of Octo
            self.sphere -= 1
            cx, cy = self.rect.center
            for _ in range(6):
                game.effects.append(Particle(cx + random.uniform(-10, 10), cy + random.uniform(-10, 10),
                                             random.uniform(-1.5, 1.5), random.uniform(-1.5, 1.5),
                                             (190, 230, 255), 22))
            if self.sphere == 0:
                game.pop_sphere()
                return
            sound.play('tink')
            dmg = 0
        else:
            self.hp = max(0, self.hp - dmg)
        self.invuln = int(70 * self.stat('invuln', 1.0))
        sx, sy = src
        cx, cy = self.rect.center
        dx, dy = cx - sx, cy - sy
        if abs(dx) > abs(dy):
            self.knock = (sign(dx) * 3, 0)
        else:
            self.knock = (0, (sign(dy) or 1) * 3)
        self.knock_t = 8
        self.attack_t = 0
        sound.play('hurt')
        game.shake = 6

    # -- update ------------------------------------------------------------
    def update(self, game, move_dir):
        room = game.level
        self.idle_t += 1
        cx, cy = self.rect.center
        moving = bool(move_dir or self.analog or self.dash_t)
        self.moving = moving
        if moving and not self.in_sky and self.idle_t % 11 == 0:
            game.effects.append(fx.SwimBubble(cx + random.uniform(-3, 3), cy - 6))
        elem = fx.element_of(self.mood)
        if elem and self.idle_t % 5 == 0:
            a = random.uniform(0, math.tau)
            game.effects.append(fx.AuraMote(cx + math.cos(a) * 8, cy + math.sin(a) * 7, elem))
        if self.invuln:
            self.invuln -= 1
        if self.shoot_cd:
            self.shoot_cd -= 1
        if self.fog_cd:
            self.fog_cd -= 1
        regen = self.stat('regen', 0)
        if regen and self.hp < self.max_hp and not game.trial:
            self.regen_t += 1
            if self.regen_t >= regen:
                self.regen_t = 0
                self.hp += 1
                game.burst(self.rect.center, (255, 150, 200), 6)
        if self.roll_t:
            self._roll_update(game)
            return
        if self.dash_cd and not self.dash_t:
            self.dash_cd -= 1
        if self.fog_t:
            self.fog_t -= 1
            if self.fog_t % 6 == 0:
                cx, cy = self.rect.center
                game.effects.append(Particle(cx + random.uniform(-9, 9), cy + random.uniform(-9, 9),
                                             random.uniform(-0.3, 0.3), random.uniform(-0.4, 0),
                                             (220, 228, 240), 26))
        if self.bubble_t:
            self.bubble_t -= 1
            for e in game.enemies:
                if e.active and not e.hurt_t and e.rect.colliderect(self.rect.inflate(10, 10)):
                    e.hit(game, 1, 'bubble', self.rect.center)
        if self.dash_t:
            self.dash_t -= 1
            dx, dy = self.dash_dir
            for _ in range(JET_SPEED):
                if not self.move(dx, dy, room):
                    self._assist(dx, dy, room)
                    break
            if self.dash_t % 2 == 0:
                cx, cy = self.rect.center
                game.effects.append(Particle(cx - dx * 6 + random.uniform(-2, 2), cy - dy * 6 + random.uniform(-2, 2),
                                             -dx * 0.5, -dy * 0.5, (30, 24, 70), 18, size=3))
            self.walk_t += 1
            self.anim = (self.walk_t // 3) % 2
            return
        if self.flip_t:
            self.flip_t -= 1
            if self.flip_t == 7:
                self.mood = self.next_mood
                name, _, _ = forms.STRENGTHS.get(self.mood, ("", "", {}))
                if name:
                    game.toast = (f"{gfx.MOOD_NAMES[self.mood]}: {name}", 120)
                game.burst(self.rect.center, gfx.OCTO_PAL[self.mood]['B'], 10)
        if self.knock_t:
            self.knock_t -= 1
            for _ in range(2):
                self.move(self.knock[0] / 2, self.knock[1] / 2, room)
            return
        if self.attack_t:
            self.attack_t -= 1
            if self.slap_active():
                game.slap_hits(self)
            return
        if self.in_sky and self.sphere > 0:
            self._roll(room, move_dir)
            return
        if self.analog:
            # touch joystick: swim at any angle, faster the further the stick is pushed
            ax, ay = self.analog
            self.facing = cardinal(ax, ay)
            sp = self.speed()
            moved = self.move(ax * sp, ay * sp, room)
            if not moved:
                dx, dy = DIRS[self.facing]
                self._assist(dx, dy, room)
                self._try_unlock(game, dx, dy)
            self.walk_t += 1
            if self.walk_t % 9 == 0:
                self.anim ^= 1
        elif move_dir:
            dx, dy = DIRS[move_dir]
            self.facing = move_dir
            sp = self.speed()
            moved = self.move(dx * sp, dy * sp, room)
            if not moved:
                self._assist(dx, dy, room)
                self._try_unlock(game, dx, dy)
            self.walk_t += 1
            if self.walk_t % 9 == 0:
                self.anim ^= 1

    def _roll(self, room, move_dir):
        """Inside the water sphere Octo rolls: he speeds up and slows down gently, and bounces off things."""
        v = self.roll_v
        tx = ty = 0.0
        if self.analog:
            ax, ay = self.analog
            self.facing = cardinal(ax, ay)
            sp = self.speed() * 1.15
            tx, ty = ax * sp, ay * sp
            move_dir = self.facing
        elif move_dir:
            dx, dy = DIRS[move_dir]
            self.facing = move_dir
            sp = self.speed() * 1.15
            tx, ty = dx * sp, dy * sp
        k = 0.09 if move_dir else 0.04
        v[0] += (tx - v[0]) * k
        v[1] += (ty - v[1]) * k
        if abs(v[0]) > 0.01 and not self.move(v[0], 0, room):
            if move_dir and abs(tx) > 0:
                self._assist(sign(tx), 0, room)
            v[0] = -v[0] * 0.4
        if abs(v[1]) > 0.01 and not self.move(0, v[1], room):
            if move_dir and abs(ty) > 0:
                self._assist(0, sign(ty), room)
            v[1] = -v[1] * 0.4
        speed = math.hypot(*v)
        self.roll += (v[0] if abs(v[0]) >= abs(v[1]) else v[1]) / 11 * 57.3
        if speed > 0.2:
            self.walk_t += 1
            if self.walk_t % 9 == 0:
                self.anim ^= 1

    def _assist(self, dx, dy, room):
        """Slide around corners when nearly lined up with a gap."""
        for off in range(1, 7):
            for s in (-1, 1):
                if dx:
                    r = self.rect.move(dx * 2, s * off)
                    if not room.blocked(r, 'player') and not room.blocked(self.rect.move(0, s * off), 'player'):
                        self.move(0, s * 1, room)
                        return
                else:
                    r = self.rect.move(s * off, dy * 2)
                    if not room.blocked(r, 'player') and not room.blocked(self.rect.move(s * off, 0), 'player'):
                        self.move(s * 1, 0, room)
                        return

    def _try_unlock(self, game, dx, dy):
        probe = self.rect.move(dx * 2, dy * 2)
        for tx, ty, ch in game.level.tiles_in(probe):
            if ch == 'B':
                game.seal_bump()
                return
            if ch == 'L':
                if self.keys > 0:
                    self.keys -= 1
                    game.unlock_at(tx, ty)
                elif not game.flags.get('need_key_msg'):
                    game.flags['need_key_msg'] = True
                    game.say(["THE DOOR IS LOCKED.", "SOMEWHERE IN THE SHRINE THERE MUST BE A KEY..."])
                return

    def _draw_sphere(self, surf, img, x, y):
        cx, cy = x + 8, y + 7
        R = 12
        if not (self.invuln and (self.invuln // 3) % 2):
            rot = pygame.transform.rotate(img, -self.roll)
            w, h = rot.get_size()
            surf.blit(rot, (cx - w // 2, cy - h // 2))
        ball = pygame.Surface((R * 2 + 2, R * 2 + 2), pygame.SRCALPHA)
        c = R + 1
        pygame.draw.circle(ball, (70, 150, 230, 80), (c, c), R)
        # sloshing water line
        slosh = math.sin(self.roll * 0.03) * 3
        line = [(c + i, c - 2 + slosh * i / R) for i in range(-R + 2, R - 1, 2)]
        pygame.draw.lines(ball, (190, 230, 255, 140), False, line, 1)
        pygame.draw.circle(ball, (235, 250, 255, 220), (c, c), R, 1)
        # rolling glint
        a = math.radians(self.roll * 0.5) - 2.3
        pygame.draw.circle(ball, (255, 255, 255, 230), (c + math.cos(a) * (R - 4), c + math.sin(a) * (R - 4)), 2)
        pygame.draw.circle(ball, (255, 255, 255, 160), (c - 5, c - 6), 1)
        # cracks as the sphere weakens
        cracks = [((-6, -8), (-2, -3), (-4, 1)), ((7, -6), (3, -1), (6, 3)), ((-8, 5), (-3, 3), (-1, 8)),
                  ((5, 7), (1, 4), (3, 0))]
        for crack in cracks[:self.SPHERE_MAX - self.sphere]:
            pygame.draw.lines(ball, (255, 255, 255, 255), False, [(c + px, c + py) for px, py in crack], 1)
        surf.blit(ball, (cx - c, cy - c))
        if self.bubble_t and (self.bubble_t > 40 or (self.bubble_t // 4) % 2):
            pygame.draw.circle(surf, (255, 200, 240), (cx, cy), R + 3, 1)

    # -- draw --------------------------------------------------------------
    def draw(self, surf, ox=0, oy=0):
        if self.invuln and (self.invuln // 3) % 2 and not self.knock_t and not (self.in_sky and self.sphere):
            return
        frame = self.anim
        if self.attack_t:
            frame = 0
        img = gfx.OCTO[self.mood][self.facing][frame]
        x, y = round(self.x) + ox, round(self.y) + oy
        if self.tumble:
            # falling out of the sky: spin, shrink and drop
            t = self.tumble
            size = max(4, int(16 * (1 - t / 80)))
            img = pygame.transform.rotate(pygame.transform.scale(img, (size, size)), t * 18)
            w, h = img.get_size()
            surf.blit(img, (x + 8 - w // 2, y + 8 - h // 2 + t * t // 40))
            return
        if self.roll_t:
            cx, cy = x + 8, y + 8
            spin = self.roll_t * 0.6
            pygame.draw.circle(surf, (120, 60, 20), (cx, cy), 8)
            pygame.draw.circle(surf, (250, 150, 60), (cx, cy), 7)
            for i in range(8):
                a = spin + i / 8 * math.tau
                pygame.draw.line(surf, (255, 230, 150), (cx + math.cos(a) * 6, cy + math.sin(a) * 6),
                                 (cx + math.cos(a) * 11, cy + math.sin(a) * 11), 2)
            return
        if self.in_sky and self.sphere > 0:
            self._draw_sphere(surf, img, x, y)
            return
        if self.flip_t:
            w = max(2, int(16 * abs(math.cos((14 - self.flip_t) / 14 * math.pi))))
            img = pygame.transform.scale(img, (w, 16))
            x += (16 - w) // 2
        if self.knock_t:
            img = gfx.flash(img)
        if self.dash_t:          # stretch out like a jetting octopus
            dx, dy = self.dash_dir
            img = pygame.transform.scale(img, (20, 12) if dx else (12, 20))
            x -= 2 if dx else -2
            y += 2 if dx else -2
        if self.attack_t and self.mood == 'mad':
            r = self.slap_rect()
            t = gfx.SLAP['mad'][self.facing]
            ext = min(1.0, (16 - self.attack_t) / 4) if self.attack_t > 8 else self.attack_t / 8
            tw, th = t.get_size()
            if self.facing in ('left', 'right'):
                cw = max(1, int(tw * ext))
                if self.facing == 'right':
                    surf.blit(t, (r.x - 2 + ox, r.y + 13 + oy), (tw - cw, 0, cw, th))
                else:
                    surf.blit(t, (r.right + 2 - cw + ox, r.y + 13 + oy), (0, 0, cw, th))
            else:
                ch = max(1, int(th * ext))
                if self.facing == 'down':
                    surf.blit(t, (r.x + 12 + ox, r.y - 2 + oy), (0, th - ch, tw, ch))
                else:
                    surf.blit(t, (r.x + 12 + ox, r.bottom + 2 - ch + oy), (0, 0, tw, ch))
        if self.fog_t:
            img = img.copy()
            img.set_alpha(110 if self.fog_t > 50 or (self.fog_t // 4) % 2 else 220)
        if not (self.dash_t or self.flip_t or self.attack_t or self.knock_t):
            if getattr(self, 'moving', False) and (self.walk_t // 6) % 2:
                img = pygame.transform.scale(img, (17, 15))        # squash on each stroke
                y += 1
            else:
                y += round(math.sin(self.idle_t * 0.07))           # floating in the water
        surf.blit(img, (x, y))
        if self.fog_t:
            fog = pygame.Surface((36, 36), pygame.SRCALPHA)
            t = self.fog_t
            for i in range(7):
                a = i / 7 * math.tau + t * 0.03
                r = 10 + math.sin(t * 0.07 + i) * 2
                pygame.draw.circle(fog, (235, 240, 250, 90), (18 + math.cos(a) * r, 18 + math.sin(a) * r), 7)
            surf.blit(fog, (x - 10, y - 9))
        if self.bubble_t and (self.bubble_t > 40 or (self.bubble_t // 4) % 2):
            pygame.draw.circle(surf, (200, 240, 255), (x + 8, y + 9), 13, 1)
            surf.set_at((x + 3, y + 2), (255, 255, 255))
            surf.set_at((x + 4, y + 2), (255, 255, 255))
        if 'shield' in self.items and not self.dash_t and not self.flip_t and self.facing != 'up':
            sx, sy = {'down': (3, 8), 'left': (-4, 5), 'right': (9, 5)}[self.facing]
            surf.blit(gfx.SPR['items']['shield'], (x + sx, y + sy))


# ===========================================================================
# Enemies
# ===========================================================================

class Enemy(Entity):
    max_hp = 2
    damage = 1
    immune = ()
    sprite = 'crab'
    knockback = True
    spawn_time = 28

    def __init__(self, x, y):
        super().__init__(x, y)
        self.hp = self.max_hp
        self.spawn_t = self.spawn_time + random.randint(0, 12)
        self.hurt_t = 0
        self.kb = (0, 0)
        self.kb_t = 0
        self.last_slap = -1
        self.frozen = 0
        self.trapped = 0
        self.burn = 0
        self.chill_t = 0
        self.goal = None          # (x, y) a raider marches to in a defend trial
        self.t = random.randint(0, 100)

    @property
    def active(self):
        return self.spawn_t == 0 and not self.dead

    def update(self, game):
        if self.spawn_t:
            self.spawn_t -= 1
            return
        if self.hurt_t:
            self.hurt_t -= 1
        if self.chill_t:
            self.chill_t -= 1
        if self.burn:
            self.burn -= 1
            if self.burn % 45 == 0:
                self.hurt_t = 0
                self.hit(game, 1, 'burn', (self.rect.centerx, self.rect.bottom))
                game.effects.append(Particle(self.rect.centerx, self.rect.top, 0, -0.6, (255, 140, 60), 16))
                if self.dead:
                    return
        if self.trapped:
            self.trapped -= 1
            self.frozen = max(self.frozen, 1)
            self.y -= 0.15                       # floats up inside the bubble
            if self.trapped == 0:
                game.splat(self.rect.center, (200, 240, 255))
                sound.play('bubble')
                self.frozen = 0
                strike(game, self, 3, 'trap', (self.rect.centerx, self.rect.bottom), getattr(self, 'trap_elem', None))
                return
        if self.frozen:
            self.frozen -= 1
            return
        self.t += 1
        if self.kb_t:
            self.kb_t -= 1
            for _ in range(3):
                self.move(self.kb[0], self.kb[1], game.level)
            return
        if self.goal:
            self._march(game)
            return
        self.ai(game)

    def _march(self, game):
        """Defend trials: head for the clam, sliding around anything in the way."""
        gx, gy = self.goal
        cx, cy = self.rect.center
        d = math.hypot(gx - cx, gy - cy) or 1
        sp = 0.55
        dx, dy = (gx - cx) / d * sp, (gy - cy) / d * sp
        if not self.move(dx, dy, game.level):
            if not self.move(dx, 0, game.level):
                self.move(0, dy if dy else sp, game.level)

    def ai(self, game):
        pass

    def hit(self, game, dmg, kind, src):
        if not self.active or self.hurt_t:
            return False
        if kind in self.immune:
            sound.play('tink')
            game.spark(self.rect.center)
            return False
        if kind in PLAYER_HIT_KINDS:
            dmg += game.player.stat('power', 0)
        self.hp -= dmg
        self.hurt_t = 18
        sound.play('hit')
        cx, cy = self.rect.center
        game.effects.append(fx.ImpactRing(cx, cy, big=self.hp <= 0))
        game.hitstop = max(getattr(game, 'hitstop', 0), 4 if self.hp <= 0 else 2)
        if self.hp <= 0:
            self.die(game)
        elif self.knockback:
            sx, sy = src
            cx, cy = self.rect.center
            dx, dy = cx - sx, cy - sy
            self.kb = (sign(dx), 0) if abs(dx) > abs(dy) else (0, sign(dy) or 1)
            self.kb_t = 6
        return True

    def die(self, game):
        self.dead = True
        sound.play('die')
        game.effects.append(Puff(self.x, self.y))
        game.drop_loot(self.rect.center)

    def image(self):
        frames = gfx.SPR[self.sprite]
        return frames[(self.t // 12) % 2]

    def draw(self, surf, ox=0, oy=0):
        if self.spawn_t:
            frames = gfx.SPR['puff']
            i = min(3, (self.spawn_time - min(self.spawn_t, self.spawn_time)) * 4 // self.spawn_time)
            surf.blit(frames[3 - i], (round(self.x) + ox, round(self.y) + oy))
            return
        img = self.image()
        if self.frozen:
            img = gfx.icy(img)
        if self.hurt_t and (self.hurt_t // 2) % 2:
            img = gfx.flash(img)
        jx = 1 if self.frozen and self.frozen < 30 and self.frozen % 4 < 2 else 0
        bob = 0 if self.frozen or self.who != 'flyer' else round(math.sin(self.t * 0.09) * 1.5)
        surf.blit(img, (round(self.x) + ox + jx, round(self.y) + oy + bob))
        if self.trapped:
            r = self.rect
            pygame.draw.circle(surf, (200, 240, 255), (r.centerx + ox, r.centery + oy), max(r.w, r.h) // 2 + 4, 1)
        self.draw_hp(surf, ox, oy)

    def draw_hp(self, surf, ox, oy):
        """Little health bar over the enemy's head."""
        r = self.rect
        w = max(10, min(r.w, 34))
        x = r.centerx - w // 2 + ox
        y = round(self.y) + oy - 4
        frac = max(0.0, self.hp / self.max_hp)
        pygame.draw.rect(surf, (0, 0, 0), (x - 1, y - 1, w + 2, 4))
        pygame.draw.rect(surf, (90, 20, 30), (x, y, w, 2))
        col = (90, 230, 110) if frac > 0.5 else (250, 200, 60) if frac > 0.25 else (240, 60, 60)
        pygame.draw.rect(surf, col, (x, y, max(1, round(w * frac)), 2))


class Crab(Enemy):
    max_hp = 2
    sprite = 'crab'
    hb = (1, 5, 14, 10)

    def __init__(self, x, y):
        super().__init__(x, y)
        self.dir = random.choice(list(DIRS))
        self.dir_t = 0
        self.speed = 0.6

    def ai(self, game):
        self.dir_t -= 1
        if self.dir_t <= 0:
            self.dir = random.choice(list(DIRS))
            self.dir_t = random.randint(30, 100)
        dx, dy = DIRS[self.dir]
        if not self.move(dx * self.speed, dy * self.speed, game.level):
            self.dir_t = 0


class Urchin(Enemy):
    """Spiky: slaps bounce off -- use ink!"""
    max_hp = 3
    damage = 2
    sprite = 'urchin'
    immune = ('slap',)
    hb = (2, 3, 12, 12)

    def __init__(self, x, y):
        super().__init__(x, y)
        self.vx = random.choice((-0.5, 0.5))
        self.vy = random.choice((-0.5, 0.5))

    def ai(self, game):
        if not self.move(self.vx, 0, game.level):
            self.vx = -self.vx
        if not self.move(0, self.vy, game.level):
            self.vy = -self.vy

    def image(self):
        return gfx.SPR['urchin'][(self.t // 8) % 2]


class Jelly(Enemy):
    """Squishy: ink passes right through -- slap it in mad mode!"""
    max_hp = 3
    sprite = 'jelly'
    immune = ('ink',)
    who = 'flyer'
    hb = (2, 2, 12, 12)

    def __init__(self, x, y):
        super().__init__(x, y)
        self.vx = self.vy = 0.0

    def ai(self, game):
        p = game.player.seen_pos()
        if self.t % 80 == 0:
            dx, dy = p[0] - 8 - self.x, p[1] - 8 - self.y
            d = math.hypot(dx, dy) or 1
            self.vx, self.vy = dx / d * 1.1, dy / d * 1.1
        self.vx *= 0.985
        self.vy *= 0.985
        bob = math.sin(self.t * 0.15) * 0.25
        if not self.move(self.vx, 0, game.level):
            self.vx = -self.vx
        if not self.move(0, self.vy + bob, game.level):
            self.vy = -self.vy

    def image(self):
        return gfx.SPR['jelly'][1 if (self.t % 80) < 14 else 0]


class Puffer(Enemy):
    max_hp = 2
    sprite = 'puffer'
    hb = (3, 4, 11, 10)

    def __init__(self, x, y):
        super().__init__(x, y)
        self.vx = random.choice((-0.35, 0.35))
        self.vy = 0.0
        self.state_t = random.randint(60, 150)
        self.puffed = 0

    def ai(self, game):
        if self.puffed:
            self.puffed -= 1
            if self.puffed == 10:
                p = game.player.seen_pos()
                cx, cy = self.rect.center
                dx, dy = p[0] - cx, p[1] - cy
                d = math.hypot(dx, dy) or 1
                game.shots.append(EnemyShot(cx - 3, cy - 3, dx / d * 1.8, dy / d * 1.8, 'spine'))
                sound.play('shoot')
            return
        self.state_t -= 1
        if self.state_t <= 0:
            self.puffed = 40
            self.state_t = random.randint(110, 180)
            return
        if self.t % 90 == 0:
            self.vy = random.choice((-0.3, 0, 0.3))
        if not self.move(self.vx, 0, game.level):
            self.vx = -self.vx
        if not self.move(0, self.vy, game.level):
            self.vy = -self.vy

    def image(self):
        f = gfx.SPR['puffer']
        if self.puffed:
            return f[2]
        img = f[(self.t // 10) % 2]
        return pygame.transform.flip(img, True, False) if self.vx < 0 else img


class Shark(Enemy):
    """Grimfin the Shark: patrols, lunges with open jaws, spits bubble volleys."""
    max_hp = 18
    damage = 2
    sprite = 'shark'
    SPEED = (0.8, 1.2)
    CHARGE = (2.8, 3.4)
    SPREAD = (-0.35, 0, 0.35)
    knockback = False
    boss = True
    spawn_time = 60
    hb = (8, 8, 34, 15)

    def __init__(self, x, y):
        super().__init__(x, y)
        self.spawn_t = self.spawn_time
        self.state = 'strafe'
        self.state_t = 120
        self.vx = 0.8
        self.tx = self.ty = 0
        self.face = 1
        self.roared = False
        self.home_y = y

    def update(self, game):
        if self.spawn_t == 1 and not self.roared:
            self.roared = True
            sound.play('roar')
            game.shake = 20
        super().update(game)

    def ai(self, game):
        room = game.level
        enraged = self.hp <= self.max_hp // 2
        sp = self.SPEED[1] if enraged else self.SPEED[0]
        if self.state == 'strafe':
            self.face = sign(self.vx) or 1
            if not self.move(sign(self.vx) * sp, 0, room):
                self.vx = -self.vx
            if self.y > self.home_y - 16:
                self.move(0, -0.6, room)
            self.state_t -= 1
            if self.state_t <= 0:
                self.state = random.choice(('charge', 'bubbles', 'charge' if enraged else 'bubbles'))
                self.state_t = 36
        elif self.state == 'charge':
            self.state_t -= 1
            if self.state_t > 0:
                self.face = sign(game.player.seen_pos()[0] - self.rect.centerx) or self.face
                if self.state_t == 1:
                    p = game.player.seen_pos()
                    cx, cy = self.rect.center
                    d = math.hypot(p[0] - cx, p[1] - cy) or 1
                    s = self.CHARGE[1] if enraged else self.CHARGE[0]
                    self.tx, self.ty = (p[0] - cx) / d * s, (p[1] - cy) / d * s
                return
            if not self.move(self.tx, self.ty, room) or self.state_t < -70:
                game.shake = 8
                sound.play('shut')
                self.state = 'strafe'
                self.state_t = random.randint(80, 140) - (40 if enraged else 0)
        elif self.state == 'bubbles':
            self.state_t -= 1
            if self.state_t in (24, 12, 0) or (enraged and self.state_t in (18, 6)):
                p = game.player.seen_pos()
                self.face = sign(p[0] - self.rect.centerx) or self.face
                cx = self.rect.right - 2 if self.face > 0 else self.rect.left + 2
                cy = self.rect.centery + 2
                base = math.atan2(p[1] - cy, p[0] - cx)
                for da in self.SPREAD:
                    a = base + da
                    game.shots.append(EnemyShot(cx - 5, cy - 5, math.cos(a) * 1.4, math.sin(a) * 1.4,
                                                'bubble'))
                sound.play('bubble')
            if self.state_t <= 0:
                self.state = 'strafe'
                self.state_t = random.randint(90, 150)

    def die(self, game):
        self.dead = True
        sound.play('roar')
        game.shake = 30
        for i in range(10):
            game.effects.append(Puff(self.x + random.randint(0, 32), self.y + random.randint(-2, 12),
                                     delay=i * 5))
        game.flags[self.sprite + '_dead'] = True

    def image(self):
        biting = self.state == 'charge' or (self.state == 'bubbles' and self.state_t % 12 > 6)
        frames = gfx.SPR[self.sprite]['bite' if biting else 'swim']
        img = frames[(self.t // (5 if self.state == 'charge' else 12)) % 2]
        return img if self.face > 0 else gfx.flipped(img)

    def draw(self, surf, ox=0, oy=0):
        if self.spawn_t:
            frames = gfx.SPR['puff']
            i = min(3, (self.spawn_time - self.spawn_t) * 4 // self.spawn_time)
            surf.blit(pygame.transform.scale(frames[3 - i], (40, 28)),
                      (round(self.x) + 4 + ox, round(self.y) + oy))
            return
        img = self.image()
        if self.frozen:
            img = gfx.icy(img)
        if self.hurt_t and (self.hurt_t // 2) % 2:
            img = gfx.flash(img)
        jx = 0
        if self.state == 'charge' and self.state_t > 0:
            jx = 1 if self.state_t % 4 < 2 else -1
        surf.blit(img, (round(self.x) + ox + jx, round(self.y) + oy))
        self.draw_hp(surf, ox, oy + 6)


class Murk(Shark):
    """Murk the Eel-Shark: Grimfin's gloomy big sister, lurking in the dark palace."""
    max_hp = 28
    sprite = 'murk'
    SPEED = (1.0, 1.5)
    CHARGE = (3.2, 3.9)
    SPREAD = (-0.6, -0.3, 0, 0.3, 0.6)


class IceCrab(Crab):
    """Frozen Shelf crab: tougher and quicker."""
    max_hp = 3
    sprite = 'icecrab'

    def __init__(self, x, y):
        super().__init__(x, y)
        self.speed = 0.9


class LavaCrab(Crab):
    """Ember Vents crab: hits hard."""
    max_hp = 3
    damage = 2
    sprite = 'lavacrab'

    def __init__(self, x, y):
        super().__init__(x, y)
        self.speed = 0.75


class Gull(Enemy):
    """Sky Islands raider: circles overhead, then dives at Octo."""
    max_hp = 2
    sprite = 'gull'
    who = 'flyer'
    hb = (2, 1, 12, 7)

    def __init__(self, x, y):
        super().__init__(x, y)
        self.home = (x, y)
        self.ang = random.uniform(0, math.tau)
        self.dive = 0
        self.vx = self.vy = 0.0

    def ai(self, game):
        p = game.player.seen_pos()
        if self.dive:
            self.dive -= 1
            self.move(self.vx, self.vy, game.level)
            if self.dive == 0:
                self.home = (self.x, self.y)
            return
        self.ang += 0.04
        tx = self.home[0] + math.cos(self.ang) * 24
        ty = self.home[1] + math.sin(self.ang) * 12
        self.move((tx - self.x) * 0.1, (ty - self.y) * 0.1, game.level)
        cx, cy = self.rect.center
        d = math.hypot(p[0] - cx, p[1] - cy)
        if d < 110 and self.t % 100 == 0:
            self.dive = 34
            self.vx, self.vy = (p[0] - cx) / (d or 1) * 2.4, (p[1] - cy) / (d or 1) * 2.4
            sound.play('shoot')

    def image(self):
        img = gfx.SPR['gull'][(self.t // 8) % 2]
        return gfx.flipped(img) if self.vx < 0 or (not self.dive and math.sin(self.ang) < 0) else img


# ---------------------------------------------------------------------------
# Mini-bosses: one guards each region of the world
# ---------------------------------------------------------------------------
MINIBOSS_STYLES = {
    # id: name, base sprite, tint, hp, contact damage, speed, moves, minion, shot kind, movement
    'pinch': dict(name="BIG PINCH", base='crab', tint=(255, 200, 190), hp=12, dmg=1, speed=0.7,
                  moves=('charge', 'summon', 'charge'), minion='crab', shot='spine'),
    'wraith': dict(name="KELP WRAITH", base='jelly', tint=(120, 255, 140), hp=12, dmg=1, speed=0.55,
                   moves=('spread', 'teleport', 'ring'), minion='jelly', shot='bubble', phase=True),
    'thorn': dict(name="THORNBACK", base='urchin', tint=(255, 150, 210), hp=14, dmg=2, speed=0.5,
                  moves=('ring', 'charge', 'ring'), minion='urchin', shot='spine'),
    'blowhard': dict(name="BLOWHARD", base='puffer', tint=(255, 240, 150), hp=14, dmg=1, speed=0.6,
                     moves=('ring', 'spread', 'summon'), minion='puffer', shot='spine'),
    'gloom': dict(name="GLOOM JELLY", base='jelly', tint=(150, 100, 255), hp=16, dmg=2, speed=0.6,
                  moves=('teleport', 'ring', 'spread'), minion='jelly', shot='bubble', fly=True),
    'captain': dict(name="CAPTAIN CLAW", base='crab', tint=(200, 160, 90), hp=16, dmg=2, speed=0.8,
                    moves=('charge', 'spread', 'summon'), minion='crab', shot='spine'),
    'frostmaw': dict(name="FROSTMAW", base='icecrab', tint=(220, 240, 255), hp=18, dmg=2, speed=0.85,
                     moves=('charge', 'ring', 'charge'), minion='icecrab', shot='bubble'),
    'magma': dict(name="MAGMA KING", base='lavacrab', tint=(255, 190, 150), hp=18, dmg=2, speed=0.8,
                  moves=('charge', 'summon', 'ring'), minion='lavacrab', shot='spine'),
    'warden': dict(name="HOLLOW WARDEN", base='puffer', tint=(150, 160, 190), hp=20, dmg=2, speed=0.7,
                   moves=('teleport', 'spread', 'ring'), minion='jelly', shot='bubble', fly=True),
    'storm': dict(name="STORM GULL", base='gull', tint=(200, 210, 255), hp=16, dmg=2, speed=1.0,
                  moves=('charge', 'spread', 'summon'), minion='gull', shot='spine', fly=True),
    # the six temple bosses: each guards a Tide Bell
    'tanglemaw': dict(name="TANGLEMAW", base='jelly', tint=(90, 210, 110), hp=16, dmg=1, speed=0.6,
                      moves=('spread', 'teleport', 'summon'), minion='jelly', shot='bubble', phase=True),
    'bramble': dict(name="BRAMBLEBACK", base='urchin', tint=(255, 120, 190), hp=18, dmg=2, speed=0.55,
                    moves=('ring', 'charge', 'summon'), minion='urchin', shot='spine'),
    'bellows': dict(name="OLD BELLOWS", base='puffer', tint=(170, 225, 255), hp=20, dmg=2, speed=0.65,
                    moves=('ring', 'spread', 'summon'), minion='puffer', shot='spine'),
    'deepeye': dict(name="DEEPEYE", base='jelly', tint=(200, 90, 255), hp=22, dmg=2, speed=0.7,
                    moves=('teleport', 'spread', 'ring'), minion='jelly', shot='bubble', fly=True),
    'hoarclaw': dict(name="HOARCLAW", base='icecrab', tint=(190, 225, 255), hp=26, dmg=2, speed=0.9,
                     moves=('charge', 'ring', 'summon'), minion='icecrab', shot='bubble'),
    'slagjaw': dict(name="SLAGJAW", base='lavacrab', tint=(255, 110, 70), hp=28, dmg=3, speed=0.9,
                    moves=('charge', 'spread', 'charge'), minion='lavacrab', shot='spine'),
}
TEMPLE_BOSS_HP = 2.0          # temple bosses are tougher than any mini-boss


class MiniBoss(Enemy):
    """A big, tough cousin of a regular enemy that guards one region."""
    knockback = False
    spawn_time = 50
    boss = True
    hb = (4, 6, 24, 22)
    _frames = {}

    STAGE_SPEED = {1: 1.0, 2: 1.3, 3: 1.6}
    STAGE_REST = {1: (80, 120), 2: (55, 85), 3: (35, 60)}
    CRABS = ('crab', 'icecrab', 'lavacrab')

    def __init__(self, bid, x, y, lurk=False, hp_mult=1.0):
        super().__init__(x - 8, y - 8)
        cfg = MINIBOSS_STYLES[bid]
        self.bid, self.cfg = bid, cfg
        self.name = cfg['name']
        self.max_hp = self.hp = int(cfg['hp'] * hp_mult)
        self.damage = 0 if lurk else cfg['dmg'] + 1
        self.lurk = lurk          # waiting in its region: harmless until Octo comes close
        self.stage = 1            # battle stages: it breaks apart and gets fiercer as it's hurt
        self.who = 'flyer' if cfg.get('fly') else 'walker'
        self.home = (self.x, self.y)
        self.state, self.state_t = 'roam', 90
        self.move_i = 0
        self.v = (0.0, 0.0)
        self.face = 1
        self.minions = []
        self.fade = 255

    def _cuts(self, stage):
        """Which pixels of the 16x16 sprite are gone at this stage (a lost claw, torn fins...)."""
        base = self.cfg['base']
        if base in self.CRABS:
            boxes = [(0, 1, 5, 6)] if stage >= 2 else []
            if stage >= 3:
                boxes.append((10, 1, 15, 6))
            return lambda x, y: any(x0 <= x <= x1 and y0 <= y <= y1 for x0, y0, x1, y1 in boxes)
        if stage == 1:
            return lambda x, y: False
        keep = 0.55 if stage == 2 else 0.1          # ragged edges: tentacles, spines, fins torn away
        rnd = random.Random(sum(map(ord, self.bid)) * 7 + stage)
        torn = {(x, y) for y in range(16) for x in range(16)
                if math.hypot(x - 7.5, y - 7.5) > 5.2 and rnd.random() > keep}
        return lambda x, y: (x, y) in torn

    def frames(self):
        key = (self.bid, self.stage)
        if key not in MiniBoss._frames:
            out = []
            cut = self._cuts(self.stage)
            for f in gfx.SPR[self.cfg['base']]:
                f = gfx.tint(f, self.cfg['tint']) if self.cfg.get('tint') else f.copy()
                if self.stage >= 2:
                    for y in range(f.get_height()):
                        for x in range(f.get_width()):
                            if cut(x, y):
                                f.set_at((x, y), (0, 0, 0, 0))
                if self.stage == 3:                  # bruised and furious
                    f.fill((255, 170, 160, 255), special_flags=pygame.BLEND_RGBA_MULT)
                out.append(pygame.transform.scale(f, (f.get_width() * 2, f.get_height() * 2)))
            MiniBoss._frames[key] = out
        return MiniBoss._frames[key]

    def _break(self, game, new_stage):
        """A stage of the fight ends: a piece breaks off, the boss roars and gets fiercer."""
        old_cut, self.stage = self._cuts(self.stage), new_stage
        new_cut = self._cuts(new_stage)
        src = gfx.SPR[self.cfg['base']][0]
        src = gfx.tint(src, self.cfg['tint']) if self.cfg.get('tint') else src
        w, h = src.get_size()
        piece = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(h):
            for x in range(w):
                if new_cut(x, y) and not old_cut(x, y):
                    piece.set_at((x, y), src.get_at((x, y)))
        game.effects.append(Debris(pygame.transform.scale(piece, (w * 2, h * 2)), self.x, self.y,
                                   -1.5 if self.stage == 2 else 1.5))
        self.hurt_t = 40
        self.frozen = 0
        self.state, self.state_t = 'roam', 50
        game.shake = 18
        game.hitstop = 10
        sound.play('roar')
        game.toast = (f"{self.name} {'BREAKS' if self.stage == 2 else 'IS FURIOUS'}!", 90)
        for i in range(14):
            a = i / 14 * math.tau
            game.effects.append(Particle(self.rect.centerx, self.rect.centery, math.cos(a) * 2.2,
                                         math.sin(a) * 2.2, (255, 230, 200), 22, size=2))

    def _step(self, dx, dy, room):
        if self.cfg.get('phase'):           # drifts straight through kelp and rock
            nx, ny = self.x + dx, self.y + dy
            hx, hy = self.home
            if math.hypot(nx - hx, ny - hy) < 110 and room.bounds.contains(
                    pygame.Rect(nx + self.hb[0], ny + self.hb[1], self.hb[2], self.hb[3])):
                self.x, self.y = nx, ny
                return True
            return False
        return self.move(dx, dy, room)

    def ai(self, game):
        room = game.level
        if self.lurk:                                # waiting: just drift about its lair
            self.y += math.sin(self.t * 0.05) * 0.2
            return
        stage = 1 if self.hp > self.max_hp * 2 / 3 else 2 if self.hp > self.max_hp / 3 else 3
        if stage > self.stage:
            self._break(game, stage)
            return
        enraged = self.stage >= 2
        tx, ty = game.player.seen_pos()
        cx, cy = self.rect.center
        d = math.hypot(tx - cx, ty - cy) or 1
        ux, uy = (tx - cx) / d, (ty - cy) / d
        if abs(ux) > 0.2:
            self.face = sign(ux)
        self.state_t -= 1
        st = self.state
        if st == 'roam':
            sp = self.cfg['speed'] * self.STAGE_SPEED[self.stage]
            wob = math.sin(self.t * 0.05) * 0.6
            if not self._step((ux - uy * wob) * sp, (uy + ux * wob) * sp, room):
                self._step(-uy * sp, ux * sp, room)
            if self.state_t <= 0:
                moves = self.moveset()
                self.state = moves[self.move_i % len(moves)]
                self.move_i += 1
                self.state_t = {'charge': 36, 'ring': 30, 'spread': 34, 'summon': 30, 'teleport': 40}[self.state]
        elif st == 'charge':
            if self.state_t > 0:                    # wind-up: shudder in place
                return
            if self.state_t == 0:
                s = 3.6 if enraged else 3.0
                self.v = (ux * s, uy * s)
                sound.play('jet')
            if not self._step(self.v[0], self.v[1], room) or self.state_t < -40:
                if self.state_t >= -40:
                    game.shake = 6
                    sound.play('shut')
                self._end(enraged)
        elif st == 'ring':
            if self.state_t == 0:
                n = 12 if enraged else 8
                off = random.random()
                for i in range(n):
                    a = (i + off) / n * math.tau
                    game.shots.append(EnemyShot(cx - 4 + math.cos(a) * 12, cy - 4 + math.sin(a) * 12,
                                                math.cos(a) * 1.6, math.sin(a) * 1.6, self.cfg['shot']))
                sound.play('shoot')
                self._end(enraged)
        elif st == 'spread':
            if self.state_t in (20, 10, 0):
                base = math.atan2(uy, ux)
                for da in ((-0.5, -0.25, 0, 0.25, 0.5) if enraged else (-0.35, 0, 0.35)):
                    a = base + da
                    game.shots.append(EnemyShot(cx - 4, cy - 4, math.cos(a) * 2.0, math.sin(a) * 2.0,
                                                self.cfg['shot']))
                sound.play('shoot')
            if self.state_t <= 0:
                self._end(enraged)
        elif st == 'summon':
            if self.state_t == 0:
                self.minions = [m for m in self.minions if not m.dead]
                for _ in range(min(2, 3 - len(self.minions))):
                    for _try in range(8):
                        a = random.uniform(0, math.tau)
                        m = ENEMY_TYPES[self.cfg['minion']](cx - 8 + math.cos(a) * 26, cy - 8 + math.sin(a) * 26)
                        if not room.blocked(m.rect, m.who):
                            m.spawn = {'kind': self.cfg['minion'], 'arena': None, 'inst': None, 'killed': False}
                            game.enemies.append(m)
                            self.minions.append(m)
                            break
                sound.play('bubble')
                self._end(enraged)
        elif st == 'teleport':
            if self.state_t > 20:
                self.fade = max(0, self.fade - 25)
            elif self.state_t == 20:
                for _try in range(12):
                    a = random.uniform(0, math.tau)
                    nx, ny = tx - 16 + math.cos(a) * 64, ty - 16 + math.sin(a) * 64
                    r = pygame.Rect(nx + self.hb[0], ny + self.hb[1], self.hb[2], self.hb[3])
                    if not room.blocked(r, self.who) or self.cfg.get('phase') and room.bounds.contains(r):
                        self.x, self.y = nx, ny
                        if self.cfg.get('phase'):
                            self.home = (nx, ny)
                        break
                sound.play('wisp')
            else:
                self.fade = min(255, self.fade + 25)
            if self.state_t <= 0:
                self.fade = 255
                self._end(enraged)

    def _end(self, enraged):
        self.state = 'roam'
        self.state_t = random.randint(*self.STAGE_REST[self.stage])

    def moveset(self):
        """Later stages add new moves to the boss's routine."""
        moves = list(self.cfg['moves'])
        if self.stage >= 2:
            moves += ['spread'] if self.cfg['base'] in self.CRABS else ['ring']
        if self.stage >= 3:
            moves += ['charge', 'summon'] if self.cfg['base'] in self.CRABS else ['spread', 'summon']
        return moves

    @property
    def active(self):
        return self.spawn_t == 0 and not self.dead and self.fade > 120

    def die(self, game):
        self.dead = True
        sound.play('roar')
        game.shake = 16
        for i in range(6):
            game.effects.append(Puff(self.x + random.randint(0, 20), self.y + random.randint(0, 20), delay=i * 5))
        game.miniboss_defeated(self)

    def draw(self, surf, ox=0, oy=0):
        if self.spawn_t:
            frames = gfx.SPR['puff']
            i = min(3, (self.spawn_time - min(self.spawn_t, self.spawn_time)) * 4 // self.spawn_time)
            img = pygame.transform.scale(frames[3 - i], (32, 32))
            surf.blit(img, (round(self.x) + ox, round(self.y) + oy))
            return
        fr = self.frames()
        if self.cfg['base'] == 'puffer':
            img = fr[2] if self.state in ('ring', 'spread') else fr[(self.t // 12) % 2]
        else:
            img = fr[(self.t // 10) % 2]
        if self.face < 0 and self.cfg['base'] in ('puffer', 'gull'):
            img = gfx.flipped(img)
        if self.frozen:
            img = gfx.icy(img)
        if self.hurt_t and (self.hurt_t // 2) % 2:
            img = gfx.flash(img)
        jx = jy = 0
        if self.state == 'charge' and self.state_t > 0:
            jx = random.choice((-1, 0, 1))
            if self.state_t % 8 < 4:
                img = gfx.flash(img)
        if self.fade < 255:
            img = img.copy()
            img.set_alpha(self.fade)
        surf.blit(img, (round(self.x) + ox + jx, round(self.y) + oy + jy))
        # a little crown so it reads as a boss
        cx, top = round(self.x) + ox + 16, round(self.y) + oy - 3
        pygame.draw.polygon(surf, (255, 210, 60), [(cx - 6, top + 4), (cx - 6, top), (cx - 3, top + 2),
                                                   (cx, top - 2), (cx + 3, top + 2), (cx + 6, top),
                                                   (cx + 6, top + 4)])


class Debris:
    """A piece knocked off a boss (a claw, a fin...) tumbling away and sinking."""

    def __init__(self, img, x, y, vx):
        self.img = img
        self.x, self.y = x, y
        self.vx, self.vy = vx, -2.2
        self.t = 0
        self.dead = False

    def update(self, game):
        self.t += 1
        self.x += self.vx
        self.vy += 0.12
        self.y += self.vy
        if self.t > 70:
            self.dead = True

    def draw(self, surf, ox=0, oy=0):
        img = pygame.transform.rotate(self.img, self.t * 9 * (1 if self.vx > 0 else -1))
        if self.t > 40:
            img.set_alpha(255 - (self.t - 40) * 8)
        surf.blit(img, (self.x + ox, self.y + oy))


class Thief(Enemy):
    """Chase trials: a golden crab that grabbed a pearl and runs. Tag it three times!"""
    max_hp = 99
    damage = 0
    knockback = False
    sprite = 'crab'
    hb = (1, 5, 14, 10)
    _img = None

    def __init__(self, x, y):
        super().__init__(x, y)
        self.tags = 0
        self.wander = (0.0, 0.0)

    def ai(self, game):
        p = game.player.rect.center
        cx, cy = self.rect.center
        d = math.hypot(cx - p[0], cy - p[1]) or 1
        if self.t % 40 == 0:
            a = random.uniform(0, math.tau)
            self.wander = (math.cos(a), math.sin(a))
        fx, fy = (cx - p[0]) / d, (cy - p[1]) / d
        k = 1.0 if d < 90 else 0.3
        vx, vy = fx * k + self.wander[0] * 0.6, fy * k + self.wander[1] * 0.6
        n = math.hypot(vx, vy) or 1
        sp = 1.25 if d < 90 else 0.7
        if not self.move(vx / n * sp, 0, game.level):
            self.wander = (-self.wander[0], self.wander[1])
        if not self.move(0, vy / n * sp, game.level):
            self.wander = (self.wander[0], -self.wander[1])

    def hit(self, game, dmg, kind, src):
        if not self.active or self.hurt_t:
            return False
        self.tags += 1
        self.hurt_t = 30
        sound.play('pearl')
        game.burst(self.rect.center, (255, 220, 90), 10)
        if game.trial:
            game.trial['got'] = self.tags
        # scuttle off to somewhere far away
        x0, y0, x1, y1 = [v * 16 for v in world_room(game)]
        px, py = game.player.rect.center
        for _ in range(30):
            nx, ny = random.uniform(x0 + 16, x1 - 16), random.uniform(y0 + 16, y1 - 16)
            r = pygame.Rect(nx + self.hb[0], ny + self.hb[1], self.hb[2], self.hb[3])
            if math.hypot(nx - px, ny - py) > 80 and not game.level.blocked(r, self.who):
                game.effects.append(Puff(self.x, self.y))
                self.x, self.y = nx, ny
                break
        return True

    def image(self):
        if Thief._img is None:
            Thief._img = [gfx.tint(f, (255, 215, 80)) for f in gfx.SPR['crab']]
        return Thief._img[(self.t // 6) % 2]


class Patroller(Enemy):
    """Race trials: a spiked sentry sweeping up and down a lane. It can't be hurt -- just dodge it."""
    max_hp = 99
    damage = 1
    knockback = False
    sprite = 'urchin'
    who = 'flyer'
    hb = (2, 2, 12, 12)
    spawn_time = 10

    def __init__(self, x, y, speed=1.2):
        super().__init__(x, y)
        self.vy = speed

    def ai(self, game):
        if not self.move(0, self.vy, game.level):
            self.vy = -self.vy

    def hit(self, game, dmg, kind, src):
        if self.active and not self.hurt_t:
            self.hurt_t = 10
            sound.play('tink')
            game.spark(self.rect.center)
        return False

    def draw_hp(self, surf, ox, oy):
        pass


def world_room(game):
    import world
    return world.TRIALS[game.trial['name']]['room'] if game.trial else (0, 0, 1, 1)


def make_enemy(kind, x, y):
    if kind.startswith('mini:'):
        return MiniBoss(kind[5:], x, y, lurk=True)      # waits in its region until Octo comes close
    if kind.startswith('tboss:'):                       # a temple boss, fought in its own room
        b = MiniBoss(kind[6:], x, y, hp_mult=TEMPLE_BOSS_HP)
        b.in_temple = True
        b.home = (b.x, b.y)
        return b
    return ENEMY_TYPES[kind](x, y)


ENEMY_TYPES = {'gull': Gull, 'crab': Crab, 'urchin': Urchin, 'jelly': Jelly, 'puffer': Puffer, 'shark': Shark,
               'murk': Murk, 'icecrab': IceCrab, 'lavacrab': LavaCrab}


# ===========================================================================
# NPC
# ===========================================================================

class Shelly(Entity):
    hb = (1, 1, 14, 14)

    def __init__(self, x, y):
        super().__init__(x, y)
        self.t = 0

    def update(self, game):
        self.t += 1

    def draw(self, surf, ox=0, oy=0):
        f = gfx.SPR['turtle'][1 if (self.t % 200) > 190 else 0]
        surf.blit(f, (round(self.x) + ox, round(self.y) + oy))


class Hermie(Shelly):
    """The hermit crab who runs the Pearl Shop."""

    def draw(self, surf, ox=0, oy=0):
        f = gfx.SPR['hermit'][1 if (self.t % 160) > 150 else 0]
        bob = 1 if (self.t // 30) % 2 else 0
        surf.blit(f, (round(self.x) + ox, round(self.y) + oy + bob))


HERMIE_TALK = [
    "HERMIE: WELCOME TO THE PEARL SHOP! STAND NEXT TO SOMETHING YOU LIKE AND PRESS Z TO BUY IT.",
    "THAT RATTLING CONTRAPTION OUTSIDE? MY FUSION MACHINE! IT FUSES TWO OF YOUR FORMS INTO A NEW, "
    "STRONGER ONE WITH ITS VERY OWN ATTACK. FACE IT AND PRESS Z.",
    "BUBBLE BOMBS GO OFF WITH B. THEY BLAST CRACKED ROCK - I HEAR THERE'S SOME JUST WEST OF HERE...",
    "AND IN THE ABYSS, A HEART SHELL SITS BEHIND A CRACKED WALL. HEH HEH.",
]

# (id, name, price, description, one-time?)
SHOP_WARES = [
    ('shrimp', "SHRIMP PLATTER", 8, "REFILLS ALL OF YOUR HEARTS.", False),
    ('bombs', "BUBBLE BOMBS", 15, "FIVE BOMBS. PRESS B TO DROP ONE. THEY BLAST CRACKED ROCK.", False),
    ('fins', "SWIFT FINS", 25, "SWIM FASTER, AND YOUR INK JET GOES FARTHER.", True),
    ('shield', "SHELL SHIELD", 30, "BLOCKS SPINES AND BUBBLES THAT HIT YOU FROM THE FRONT.", True),
    ('deepink', "DEEP INK", 35, "YOUR INK HITS TWICE AS HARD.", True),
    ('heart', "HEART SHELL", 50, "ONE MORE HEART OF LIFE.", True),
]
MAX_BOMBS = 10
# Hermie's catalogue (talk to him): everything on the counter plus his back room
CATALOGUE = SHOP_WARES + [
    ('potion', "SEA POTION", 20, "IF YOU FALL, IT SAVES YOU ONCE AND REFILLS HALF YOUR HEARTS. CARRY UP TO 2.", False),
    ('bigbag', "BIG BOMB BAG", 30, "CARRY 20 BUBBLE BOMBS INSTEAD OF 10.", True),
    ('compass', "TRIAL COMPASS", 25, "EVERY TRIAL PORTAL SHOWS ON YOUR MAP, EVEN WHERE YOU HAVEN'T BEEN.", True),
    ('charm', "LUCKY CHARM", 40, "ENEMIES DROP TREASURE 50% MORE OFTEN.", True),
    ('goggles', "DEEP GOGGLES", 35, "SEE MUCH FARTHER IN DARK PLACES.", True),
    ('jetink', "JET INK", 30, "YOUR INK JET RECHARGES FASTER.", True),
    ('armor', "CORAL ARMOR", 60, "BIG HITS HURT HALF A HEART LESS - IN EVERY FORM.", True),
    ('pmagnet', "PEARL MAGNET", 30, "PEARLS AND HEARTS NEARBY FLY STRAIGHT TO YOU.", True),
    ('spiritpearl', "SPIRIT PEARL", 120, "A SPIRIT PEARL FOR THE TEMPLE ALTAR. PRICEY, BUT NO TRIAL NEEDED.", False),
]


def max_bombs(p):
    return 20 if 'bigbag' in p.items else MAX_BOMBS


SHELLY_TALK = [
    "OLD SHELLY: OCTO! GRIMFIN THE SHARK AND HIS SISTER MURK STOLE THE GOLDEN PEARL! MURK LOCKED IT IN HER PALACE "
    "IN THE DARK SUNKEN CITY, FAR TO THE SOUTHEAST.",
    "HER PALACE DOOR IS SEALED. ONLY THE PEAL OF ALL SEVEN TIDE BELLS CAN BREAK THE SEAL.",
    "GRIMFIN GUARDS ONE BELL IN THE SUNKEN SHRINE TO THE NORTH. THE OTHER SIX LIE IN DEEP TEMPLES ALL OVER THE "
    "SEA - LOOK FOR DARK CAVE MOUTHS IN THE KELP WOODS, THE CORAL GARDENS, THE LAGOON, THE ABYSS, THE FROZEN "
    "SHELF AND THE EMBER VENTS.",
    "IT WON'T BE EASY. TRAIN IN THE TRIALS, FIND HEART SHELLS, AND DON'T FORGET YOUR SEA POTIONS!",
    "YOU'RE A REVERSIBLE OCTOPUS, REMEMBER? PRESS X TO FLIP YOUR MOOD.",
    "HAPPY BLUE OCTO SQUIRTS INK - PRESS C TO SWAP A LONG LINE FOR A SHORT WIDE BURST. GRUMPY BLACK OCTO SLAPS HARD AND CUTS KELP.",
    "INK PASSES RIGHT THROUGH JELLIES, AND SLAPPING AN URCHIN... OUCH. CHOOSE YOUR MOOD WISELY!",
    "IN A PINCH, PRESS V TO JET AWAY IN A PUFF OF INK. NOTHING CAN TOUCH YOU MID-JET, AND THE INK STINGS!",
    "GLOWING PORTALS LEAD TO TRIALS. BEAT ONE TO EARN A SPIRIT PEARL - AND THE PORTAL BECOMES A WARP POINT (PRESS T).",
    "BRING THREE SPIRIT PEARLS TO THE ALTAR ON TOP OF THE OCTO TEMPLE AND IT WILL TEACH YOU A NEW FORM. "
    "YOU PICK WHICH ONE!",
    "FAR TO THE EAST LIE THE FROZEN SHELF, THE EMBER VENTS AND THE DARK SUNKEN CITY. ICE, LAVA AND GHOSTLY WALLS "
    "BAR THE WAY... ZAPPY, CHILLY AND SPOOKY OCTO COULD GET THROUGH!",
    "SEE THAT BUBBLING GEYSER EAST OF THE TEMPLE? STEP IN AND IT'LL BLAST YOU UP TO THE SKY ISLANDS!",
    "PRESS LEFT SHIFT ANY TIME TO SAVE YOUR GAME. PRESS P TO PAUSE.",
    "HERMIE THE HERMIT CRAB RUNS A PEARL SHOP JUST WEST OF THE TEMPLE. SAVE UP YOUR PEARLS!",
    "THE SHRINE PATH IS CHOKED WITH KELP. GO WEST, THEN NORTH, THEN SLAP YOUR WAY EAST.",
    "THE SEA IS WIDE: KELP WOODS TO THE NORTHWEST, CORAL GARDENS NORTHEAST, THE LAGOON WEST, "
    "THE ABYSS EAST AND A SHIP GRAVEYARD TO THE SOUTH. HEART SHELLS ARE HIDDEN OUT THERE!",
]


# ===========================================================================
# Projectiles
# ===========================================================================

class Ink(Entity):
    hb = (1, 1, 6, 6)
    who = 'shot'
    damage = 1

    def __init__(self, x, y, vx, vy, life=70, wait=0):
        super().__init__(x, y)
        self.vx, self.vy = vx, vy
        self.life = life
        self.wait = wait            # frames to hold before launching (for the line stream)

    def update(self, game):
        if self.wait:
            self.wait -= 1
            return
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        r = self.rect
        if self.life <= 0 or game.level.blocked(r, 'shot') or not game.view_rect.colliderect(r):
            self.dead = True
            game.splat(r.center, (30, 24, 70))
            return
        for e in game.enemies:
            if e.active and r.colliderect(e.rect):
                dmg = 2 if 'deepink' in game.player.items else 1
                e.hit(game, dmg, 'ink', (r.centerx - self.vx * 4, r.centery - self.vy * 4))
                self.dead = True
                game.splat(r.center, (30, 24, 70))
                return

    def draw(self, surf, ox=0, oy=0):
        if not self.wait:
            surf.blit(gfx.SPR['shots']['ink'], (round(self.x) + ox, round(self.y) + oy))


class ZapRing:
    """Zappy Octo's shock: a crackling ring that hits everything close by."""
    RADIUS = 38

    def __init__(self, cx, cy):
        self.x, self.y = cx, cy
        self.t = 0
        self.dead = False

    def update(self, game):
        self.t += 1
        if self.t == 2:
            for e in game.enemies:
                if e.active:
                    ex, ey = e.rect.center
                    if math.hypot(ex - self.x, ey - self.y) < self.RADIUS + min(e.rect.w, e.rect.h) / 2:
                        e.hit(game, 2, 'zap', (self.x, self.y))
            for sh in game.shots:
                if isinstance(sh, EnemyShot) and math.hypot(sh.x - self.x, sh.y - self.y) < self.RADIUS:
                    sh.dead = True
                    game.spark(sh.rect.center)
            game.shatter_ice(self.x, self.y, self.RADIUS)
        if self.t > 14:
            self.dead = True

    def draw(self, surf, ox=0, oy=0):
        k = self.t / 14
        r = 8 + k * (self.RADIUS - 8)
        cx, cy = self.x + ox, self.y + oy
        pts = []
        for i in range(24):
            a = i / 24 * math.tau + self.t * 0.3
            rr = r + (3 if i % 2 else -3)
            pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
        col = (255, 250, 160) if self.t % 4 < 2 else (120, 200, 255)
        pygame.draw.lines(surf, col, True, pts, 2 if k < 0.6 else 1)


class IceShard(Entity):
    """Chilly Octo's shot: freezes whatever it hits solid."""
    hb = (1, 1, 6, 6)
    who = 'shot'

    def __init__(self, x, y, vx, vy):
        super().__init__(x, y)
        self.vx, self.vy = vx, vy
        self.life = 70

    def update(self, game):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        r = self.rect
        tx, ty = r.centerx // 16, r.centery // 16
        if game.level.tile(tx, ty) == 'l':
            game.cool_lava(tx, ty)
            self.dead = True
            return
        if self.life <= 0 or game.level.blocked(r, 'shot') or not game.view_rect.colliderect(r):
            self.dead = True
            game.splat(r.center, (200, 240, 255))
            return
        for e in game.enemies:
            if e.active and r.colliderect(e.rect):
                e.hit(game, 1, 'ice', (r.centerx - self.vx * 4, r.centery - self.vy * 4))
                if not e.dead:
                    freeze(e, 70)
                    e.kb_t = 0
                self.dead = True
                game.splat(r.center, (200, 240, 255))
                return

    def draw(self, surf, ox=0, oy=0):
        cx, cy = round(self.x) + 4 + ox, round(self.y) + 4 + oy
        d = math.hypot(self.vx, self.vy) or 1
        ux, uy = self.vx / d, self.vy / d
        tip = (cx + ux * 5, cy + uy * 5)
        tail = (cx - ux * 5, cy - uy * 5)
        side = (-uy * 2.5, ux * 2.5)
        pts = [tip, (cx + side[0], cy + side[1]), tail, (cx - side[0], cy - side[1])]
        pygame.draw.polygon(surf, (190, 236, 255), pts)
        pygame.draw.polygon(surf, (255, 255, 255), pts, 1)


class Spine(Entity):
    """Spiky Octo's spines, flung out in eight directions."""
    hb = (0, 0, 6, 6)
    who = 'shot'

    def __init__(self, x, y, vx, vy):
        super().__init__(x, y)
        self.vx, self.vy = vx, vy
        self.life = 38

    def update(self, game):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        r = self.rect
        if self.life <= 0 or game.level.blocked(r, 'shot'):
            self.dead = True
            return
        for e in game.enemies:
            if e.active and r.colliderect(e.rect):
                e.hit(game, 1, 'spike', (r.centerx - self.vx * 4, r.centery - self.vy * 4))
                self.dead = True
                return

    def draw(self, surf, ox=0, oy=0):
        cx, cy = round(self.x) + 3 + ox, round(self.y) + 3 + oy
        d = math.hypot(self.vx, self.vy) or 1
        ux, uy = self.vx / d, self.vy / d
        pygame.draw.line(surf, (120, 50, 0), (cx - ux * 4, cy - uy * 4), (cx + ux * 3, cy + uy * 3), 2)
        pygame.draw.line(surf, (255, 220, 120), (cx, cy), (cx + ux * 4, cy + uy * 4))


class Wisp(Entity):
    """Spooky Octo's ghost-flame: drifts through walls and homes in on enemies."""
    hb = (1, 1, 6, 6)
    who = 'shot'

    def __init__(self, x, y, vx, vy):
        super().__init__(x, y)
        self.vx, self.vy = vx, vy
        self.life = 150
        self.t = 0

    def update(self, game):
        self.t += 1
        self.life -= 1
        cx, cy = self.rect.center
        target = game.nearest_enemy((cx, cy), 400) if self.t > 8 else None
        if target:
            tx, ty = target.rect.center
            d = math.hypot(tx - cx, ty - cy) or 1
            self.vx += (tx - cx) / d * 0.28
            self.vy += (ty - cy) / d * 0.28
        sp = math.hypot(self.vx, self.vy) or 1
        if sp > 2.6:
            self.vx, self.vy = self.vx / sp * 2.6, self.vy / sp * 2.6
        self.x += self.vx
        self.y += self.vy
        r = self.rect
        if self.life <= 0 or not game.view_rect.inflate(16, 16).colliderect(r):
            self.dead = True
            return
        for e in game.enemies:
            if e.active and r.colliderect(e.rect):
                e.hit(game, 1, 'ghost', (cx - self.vx * 4, cy - self.vy * 4))
                self.dead = True
                game.splat(r.center, (200, 160, 255))
                return
        if self.t % 3 == 0:
            game.effects.append(Particle(cx, cy, 0, -0.3, (170, 120, 240), 12))

    def draw(self, surf, ox=0, oy=0):
        cx, cy = round(self.x) + 4 + ox, round(self.y) + 4 + oy
        fl = 1 if (self.t // 3) % 2 else 0
        pygame.draw.circle(surf, (120, 70, 210), (cx, cy), 4 + fl)
        pygame.draw.circle(surf, (230, 210, 255), (cx, cy), 2)


class InkCloud:
    """The puff Octo leaves behind when jetting: stings whatever swims into it."""

    def __init__(self, cx, cy):
        self.x, self.y = cx, cy
        self.t = 0
        self.life = 50
        self.dead = False
        self.hit_ids = set()
        rnd = random.Random()
        self.blobs = [(rnd.uniform(-7, 7), rnd.uniform(-7, 7), rnd.uniform(0.6, 1.0)) for _ in range(6)]

    def radius(self):
        return 6 + min(10, self.t * 0.8)

    def update(self, game):
        self.t += 1
        if self.t >= self.life:
            self.dead = True
            return
        r = self.radius()
        dmg = 2 if 'deepink' in game.player.items else 1
        for e in game.enemies:
            if e.active and id(e) not in self.hit_ids:
                ex, ey = e.rect.center
                if math.hypot(ex - self.x, ey - self.y) < r + min(e.rect.w, e.rect.h) / 2:
                    self.hit_ids.add(id(e))
                    e.hit(game, dmg, 'ink', (self.x, self.y))

    def draw(self, surf, ox=0, oy=0):
        r = self.radius()
        fade = 1 - max(0, self.t - 30) / 20
        size = int(r * 2 + 16)
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        c = size // 2
        for bx, by, k in self.blobs:
            rr = max(2, int(r * k * 0.7))
            pygame.draw.circle(s, (24, 18, 56, int(190 * fade)), (int(c + bx * r / 16), int(c + by * r / 16)), rr)
        surf.blit(s, (int(self.x - c) + ox, int(self.y - c) + oy))


class Bomb(Entity):
    """A bubble bomb: fizzes, then pops with a blast that hurts enemies and breaks cracked rock."""
    hb = (0, 0, 9, 11)
    who = 'shot'
    FUSE = 75
    RADIUS = 30

    def __init__(self, x, y):
        super().__init__(x, y)
        self.t = 0

    def update(self, game):
        self.t += 1
        if self.t < self.FUSE:
            if self.t > 40 and self.t % 8 == 0:
                sound.play('fuse')
            return
        if self.t == self.FUSE:
            self.explode(game)
        if self.t > self.FUSE + 16:
            self.dead = True

    def explode(self, game):
        cx, cy = self.rect.center
        sound.play('boom')
        game.shake = 12
        for e in game.enemies:
            if e.active:
                ex, ey = e.rect.center
                if math.hypot(ex - cx, ey - cy) < self.RADIUS + min(e.rect.w, e.rect.h) / 2:
                    e.hurt_t = 0
                    e.hit(game, 4, 'bomb', (cx, cy))
        game.blast_tiles(cx, cy, self.RADIUS)
        for i in range(18):
            a = i / 18 * math.tau
            sp = random.uniform(1.5, 3.0)
            game.effects.append(Particle(cx, cy, math.cos(a) * sp, math.sin(a) * sp,
                                         random.choice(((255, 230, 140), (255, 140, 60), (230, 240, 255))),
                                         20, size=2))

    def draw(self, surf, ox=0, oy=0):
        x, y = round(self.x) + ox, round(self.y) + oy
        if self.t < self.FUSE:
            fast = self.t > 50
            lit = (self.t // (3 if fast else 8)) % 2
            surf.blit(gfx.SPR['items']['bomb_lit' if lit else 'bomb'], (x, y))
            return
        k = (self.t - self.FUSE) / 16
        cx, cy = x + 4, y + 5
        r = int(8 + k * (self.RADIUS - 6))
        pygame.draw.circle(surf, (255, 250, 220), (cx, cy), r, max(1, int(5 * (1 - k))))
        if k < 0.5:
            pygame.draw.circle(surf, (255, 200, 100), (cx, cy), int(r * 0.6))


class EnemyShot(Entity):
    who = 'shot'

    def __init__(self, x, y, vx, vy, kind):
        super().__init__(x, y)
        self.vx, self.vy = vx, vy
        self.kind = kind
        self.damage = 1
        self.t = 0
        size = 10 if kind == 'bubble' else 6
        self.hb = (1, 1, size - 2, size - 2)

    def update(self, game):
        self.t += 1
        self.x += self.vx
        self.y += self.vy
        r = self.rect
        if game.level.blocked(r, 'shot') and self.kind != 'bubble' or not game.view_rect.colliderect(r):
            self.dead = True
            return
        if self.kind == 'bubble' and game.level.blocked(r, 'shot'):
            self.dead = True
            game.splat(r.center, (220, 200, 255))
            return
        p = game.player
        if r.colliderect(p.rect):
            fx, fy = DIRS[p.facing]
            if ('shield' in p.items or p.stat('shield', 0)) and self.vx * fx + self.vy * fy < 0 and not p.dash_t:
                sound.play('tink')          # bounced off the shell shield
                game.spark(r.center)
            else:
                p.hurt(game, self.damage, r.center)
            self.dead = True

    def draw(self, surf, ox=0, oy=0):
        img = gfx.SPR['shots'][self.kind]
        wob = int(math.sin(self.t * 0.3) * 1) if self.kind == 'bubble' else 0
        surf.blit(img, (round(self.x) + ox + wob, round(self.y) + oy))


# ===========================================================================
# Pickups
# ===========================================================================

class Pickup(Entity):
    def __init__(self, x, y, kind, item_id=None, life=None):
        super().__init__(x, y)
        self.kind = kind
        self.item_id = item_id
        self.life = life
        self.t = 0
        self.pulled = False          # flying towards Octo (Magnety)
        w, h = self._img().get_size()
        self.hb = (0, 0, max(w, 8), max(h, 8))

    def _img(self):
        if self.kind == 'heart':
            return gfx.SPR['heart']['pickup']
        if self.kind == 'container':
            return gfx.SPR['heart']['container']
        return gfx.SPR[self.kind]

    def update(self, game):
        self.t += 1
        if self.life is not None:
            self.life -= 1
            if self.life <= 0:
                self.dead = True

    def draw(self, surf, ox=0, oy=0):
        if self.life is not None and self.life < 120 and (self.t // 4) % 2:
            return
        bob = 0
        if self.kind in ('container', 'golden', 'key', 'halfpearl', 'bell'):
            bob = round(math.sin(self.t * 0.08) * 1.5)
        surf.blit(self._img(), (round(self.x) + ox, round(self.y) + oy + bob))
        if self.kind == 'golden' and (self.t // 6) % 3 == 0:
            sx = round(self.x) + ox + 3 + (self.t // 18) % 10
            sy = round(self.y) + oy + bob + 2 + (self.t // 7) % 9
            pygame.draw.line(surf, (255, 255, 255), (sx - 2, sy), (sx + 2, sy))
            pygame.draw.line(surf, (255, 255, 255), (sx, sy - 2), (sx, sy + 2))


# ===========================================================================
# Effects
# ===========================================================================

class Puff:
    def __init__(self, x, y, delay=0):
        self.x, self.y = x, y
        self.t = -delay
        self.loud = delay > 0
        self.dead = False

    def update(self, game):
        self.t += 1
        if self.t == 1 and self.loud:
            sound.play('die')
        if self.t >= 24:
            self.dead = True

    def draw(self, surf, ox=0, oy=0):
        if self.t < 0:
            return
        surf.blit(gfx.SPR['puff'][min(3, self.t // 6)], (round(self.x) + ox, round(self.y) + oy))


class Particle:
    def __init__(self, x, y, vx, vy, color, life=20, grav=0.0, size=1):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.color, self.life, self.grav, self.size = color, life, grav, size
        self.dead = False

    def update(self, game):
        self.x += self.vx
        self.y += self.vy
        self.vy += self.grav
        self.vx *= 0.94
        self.life -= 1
        if self.life <= 0:
            self.dead = True

    def draw(self, surf, ox=0, oy=0):
        if self.size == 1:
            surf.set_at((int(self.x) + ox, int(self.y) + oy), self.color)
        else:
            pygame.draw.rect(surf, self.color, (int(self.x) + ox, int(self.y) + oy, self.size, self.size))


class Bubble:
    """Ambient rising bubble."""

    def __init__(self, x, y):
        self.x, self.y = x, y
        self.r = random.choice((1, 1, 2))
        self.vy = -random.uniform(0.25, 0.6)
        self.ph = random.uniform(0, 6)
        self.dead = False

    def update(self, game=None):
        self.y += self.vy
        self.ph += 0.08
        if self.y < -4:
            self.dead = True

    def draw(self, surf, ox=0, oy=0):
        x = int(self.x + math.sin(self.ph) * 1.5) + ox
        y = int(self.y) + oy
        if self.r == 1:
            surf.set_at((x, y), (200, 230, 255))
        else:
            pygame.draw.circle(surf, (200, 230, 255), (x, y), 2, 1)


# ===========================================================================
# Fused-form attacks (see forms.FUSIONS)
# ===========================================================================

def freeze(e, frames):
    """Freeze an enemy -- but once it thaws it can't be re-frozen for a couple of seconds."""
    if e.chill_t:
        return
    if getattr(e, 'boss', False):
        frames //= 3
    e.frozen = max(e.frozen, frames)
    e.chill_t = frames + 120


def strike(game, e, dmg, kind, src, elem=None):
    """Hit an enemy with a shaped attack and apply its element."""
    if elem == 'heavy':
        dmg += 1
    if not e.hit(game, dmg, kind, src):
        return
    boss = getattr(e, 'boss', False)
    cx, cy = e.rect.center
    if elem == 'freeze' and not e.dead:
        freeze(e, 60)
    elif elem == 'burn' and not e.dead:
        e.burn = 180
    elif elem == 'stun' and not e.dead:
        e.frozen = max(e.frozen, 20 if boss else 60)
        game.effects.append(Daze(e))
    elif elem == 'drain' and random.random() < 0.35:
        p = game.player
        if p.hp < p.max_hp:
            p.hp += 1
            game.burst(p.rect.center, (255, 110, 160), 5)
    elif elem == 'loot' and random.random() < 0.4:
        it = Pickup(cx - 4, cy - 4, 'pearl', life=420)
        game.pickups.append(it)
    elif elem == 'spark':
        best = None
        for o in game.enemies:
            if o is not e and o.active:
                d = math.hypot(o.rect.centerx - cx, o.rect.centery - cy)
                if d < 56 and (best is None or d < best[0]):
                    best = (d, o)
        if best:
            o = best[1]
            o.hurt_t = 0
            o.hit(game, 1, 'chain', (cx, cy))
            game.effects.append(Bolt([(cx, cy), o.rect.center], (255, 255, 140), t=8))
    if elem in forms.ELEMENTS:
        col = forms.ELEMENTS[elem][2]
        for _ in range(4):
            game.effects.append(Particle(cx, cy, random.uniform(-1.4, 1.4), random.uniform(-1.4, 1.4), col, 14))


class Daze:
    """Little stars circling a stunned enemy's head."""

    def __init__(self, e):
        self.e = e
        self.t = 50
        self.dead = False

    def update(self, game):
        self.t -= 1
        if self.t <= 0 or self.e.dead:
            self.dead = True

    def draw(self, surf, ox=0, oy=0):
        r = self.e.rect
        for i in range(3):
            a = self.t * 0.2 + i * 2.1
            x = r.centerx + ox + math.cos(a) * 7
            y = r.top + oy - 2 + math.sin(a) * 2
            pygame.draw.circle(surf, (255, 250, 150), (int(x), int(y)), 1)


def _glow(surf, x, y, r, col, alpha=70):
    g = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
    pygame.draw.circle(g, col + (alpha,), (r + 1, r + 1), r)
    surf.blit(g, (x - r - 1, y - r - 1))


class Hail(Entity):
    """Hail: stones that drop out of the water above onto a target."""
    FALL = 22

    def __init__(self, tx, ty, delay=0, elem='freeze'):
        super().__init__(tx, ty)
        self.t = -delay
        self.elem = elem
        self.col = forms.ELEMENTS.get(elem, (0, 0, (220, 245, 255)))[2]

    @property
    def rect(self):
        return pygame.Rect(self.x - 10, self.y - 10, 20, 20)

    def update(self, game):
        self.t += 1
        if self.t == self.FALL:
            game.shake = max(game.shake, 3)
            sound.play('ice')
            for e in list(game.enemies):
                if e.active and self.rect.colliderect(e.rect):
                    strike(game, e, 2, 'hail', (self.x, self.y - 20), self.elem)
            for i in range(10):
                a = i / 10 * math.tau
                game.effects.append(Particle(self.x, self.y, math.cos(a) * 1.6, math.sin(a) * 1.6, self.col, 16))
        if self.t > self.FALL + 4:
            self.dead = True

    def draw(self, surf, ox=0, oy=0):
        if self.t < 0:
            return
        x, y = round(self.x) + ox, round(self.y) + oy
        k = min(1.0, self.t / self.FALL)
        sh = pygame.Surface((14, 6), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 10, 30, int(40 + 80 * k)), (7 - 7 * k, 0, 14 * k + 1, 6))
        surf.blit(sh, (x - 7, y))
        if self.t < self.FALL:
            hy = y - int((1 - k) * 70)
            _glow(surf, x, hy, 7, self.col, 60)
            pygame.draw.line(surf, self.col, (x - 1, hy - 14), (x, hy - 6))
            pts = [(x, hy - 5), (x + 4, hy), (x, hy + 5), (x - 4, hy)]
            pygame.draw.polygon(surf, (240, 250, 255), pts)
            pygame.draw.polygon(surf, self.col, pts, 1)


class InkWhip:
    """Whip: an inky tentacle that sweeps a wide arc in front of Octo."""
    SWEEP, REACH, TIME = 2.4, 40, 12

    def __init__(self, owner, angle, elem=None):
        self.owner = owner
        self.a0 = angle - self.SWEEP / 2
        self.t = 0
        self.hit = set()
        self.dead = False
        self.elem = elem
        self.col = forms.ELEMENTS.get(elem, (0, 0, (200, 190, 255)))[2]

    def tip_angle(self):
        return self.a0 + self.SWEEP * min(1.0, self.t / self.TIME)

    def update(self, game):
        self.t += 1
        cx, cy = self.owner.rect.center
        swept = self.tip_angle()
        for e in list(game.enemies):
            if not e.active or e in self.hit:
                continue
            ex, ey = e.rect.center
            d = math.hypot(ex - cx, ey - cy)
            rel = (math.atan2(ey - cy, ex - cx) - self.a0) % math.tau
            if d < self.REACH + 8 and rel <= swept - self.a0 + 0.2:
                self.hit.add(e)
                strike(game, e, 2, 'whip', (cx, cy), self.elem)
        if self.t >= self.TIME + 4:
            self.dead = True

    def draw(self, surf, ox=0, oy=0):
        cx, cy = self.owner.rect.center
        a = self.tip_angle()
        pts = []
        for i in range(9):
            r = self.REACH * i / 8
            bend = math.sin(i / 8 * math.pi) * 0.35
            pts.append((cx + ox + math.cos(a - bend) * r, cy + oy + math.sin(a - bend) * r))
        pygame.draw.lines(surf, (20, 16, 50), False, pts, 5)
        pygame.draw.lines(surf, (70, 60, 150), False, pts, 3)
        pygame.draw.lines(surf, self.col, False, pts[3:], 1)
        for p in pts[2::2]:       # suckers
            pygame.draw.circle(surf, (230, 220, 255), (int(p[0]), int(p[1]) + 1), 1)


class Quake(Entity):
    """Quake: a shockwave rumbling along the sea floor. Cracks rock it passes over."""
    hb = (0, 0, 12, 12)
    who = 'shot'

    def __init__(self, cx, cy, d, elem=None):
        super().__init__(cx - 6, cy - 6)
        self.d = d
        self.life = 30
        self.hit = set()
        self.elem = elem
        self.col = forms.ELEMENTS.get(elem, (0, 0, (230, 200, 140)))[2]

    def update(self, game):
        self.life -= 1
        self.x += self.d[0] * 3
        self.y += self.d[1] * 3
        r = self.rect
        game.blast_tiles(r.centerx, r.centery, 8)
        if self.life <= 0 or game.level.blocked(r, 'shot'):
            self.dead = True
            game.effects.append(Puff(self.x - 2, self.y - 2))
            return
        for e in list(game.enemies):
            if e.active and e not in self.hit and r.inflate(8, 8).colliderect(e.rect):
                self.hit.add(e)
                strike(game, e, 2, 'quake', (r.centerx - self.d[0] * 10, r.centery - self.d[1] * 10), self.elem)
        if self.life % 2 == 0:
            game.effects.append(Particle(r.centerx + random.uniform(-4, 4), r.centery + random.uniform(-4, 4),
                                         random.uniform(-0.5, 0.5), -1.0, (150, 120, 80), 14, grav=0.1, size=2))

    def draw(self, surf, ox=0, oy=0):
        r = self.rect.move(ox, oy)
        for i in range(3):
            pygame.draw.circle(surf, (110, 90, 60), (r.centerx - self.d[0] * i * 5, r.centery - self.d[1] * i * 5),
                               5 - i)
        pygame.draw.circle(surf, self.col, r.center, 3)


class Lantern(Entity):
    """Lantern: a spirit lantern that circles Octo for a while, hitting what it touches."""
    hb = (0, 0, 12, 12)

    def __init__(self, owner, elem='burn'):
        super().__init__(owner.x, owner.y)
        self.owner = owner
        self.ang = 0.0
        self.life = 420
        self.elem = elem
        self.col = forms.ELEMENTS.get(elem, (0, 0, (160, 255, 200)))[2]

    def update(self, game):
        self.life -= 1
        self.ang += 0.11
        cx, cy = self.owner.rect.center
        self.x = cx + math.cos(self.ang) * 26 - 6
        self.y = cy + math.sin(self.ang) * 26 - 6
        if self.life <= 0:
            self.dead = True
            game.burst(self.rect.center, self.col, 10)
            return
        for e in list(game.enemies):
            if e.active and not e.hurt_t and self.rect.colliderect(e.rect):
                strike(game, e, 2, 'lantern', self.owner.rect.center, self.elem)
        for sh in game.shots:
            if isinstance(sh, EnemyShot) and self.rect.colliderect(sh.rect):
                sh.dead = True
                game.spark(sh.rect.center)

    def draw(self, surf, ox=0, oy=0):
        x, y = round(self.x) + ox + 6, round(self.y) + oy + 6
        flick = 1 if (self.life // 4) % 2 else 0
        _glow(surf, x, y, 11 + flick, self.col, 55)
        pygame.draw.rect(surf, (60, 40, 90), (x - 4, y - 5, 8, 10))
        pygame.draw.rect(surf, self.col, (x - 3, y - 4, 6, 8))
        pygame.draw.rect(surf, (255, 255, 240), (x - 1, y - 2, 2, 4))
        pygame.draw.line(surf, (60, 40, 90), (x - 2, y - 7), (x + 2, y - 7))


class Whirlpool(Entity):
    """Whirlpool: a slow spinning vortex that drags nearby enemies in and churns them."""
    hb = (0, 0, 16, 16)
    who = 'shot'

    def __init__(self, cx, cy, dx, dy, elem='stun'):
        super().__init__(cx - 8, cy - 8)
        self.vx, self.vy = dx * 0.9, dy * 0.9
        self.life = 210
        self.t = 0
        self.elem = elem
        self.col = forms.ELEMENTS.get(elem, (0, 0, (200, 240, 255)))[2]

    def update(self, game):
        self.t += 1
        self.life -= 1
        if not self.move(self.vx, self.vy, game.level):
            self.vx = self.vy = 0
        if self.life <= 0:
            self.dead = True
            return
        cx, cy = self.rect.center
        for e in list(game.enemies):
            if not e.active:
                continue
            ex, ey = e.rect.center
            d = math.hypot(cx - ex, cy - ey)
            if d < 52 and not getattr(e, 'boss', False) and d > 4:
                e.move((cx - ex) / d * 0.7, (cy - ey) / d * 0.7, game.level)
            if d < 16 and not e.hurt_t:
                strike(game, e, 1, 'whirl', (cx, cy), self.elem)
        if self.t % 3 == 0:
            a = random.uniform(0, math.tau)
            game.effects.append(Particle(cx + math.cos(a) * 16, cy + math.sin(a) * 10,
                                         -math.sin(a) * 1.2, math.cos(a) * 0.8, (200, 235, 255), 12))

    def draw(self, surf, ox=0, oy=0):
        cx, cy = self.rect.center
        cx, cy = cx + ox, cy + oy
        _glow(surf, cx, cy, 15, (120, 190, 240), 35)
        for i in range(3):
            r = 14 - i * 4
            a = self.t * (0.25 + i * 0.1)
            rect = pygame.Rect(cx - r, cy - r * 0.6, r * 2, r * 1.2)
            pygame.draw.arc(surf, (220, 245, 255), rect, a, a + 3.6, 2 if i == 0 else 1)
            pygame.draw.arc(surf, self.col, rect, a + 3.14, a + 5.5, 1)


class TrapBubble(Entity):
    """Trap: a bubble that traps an enemy, which floats helplessly, then pops for big damage."""
    hb = (0, 0, 12, 12)
    who = 'shot'

    def __init__(self, x, y, vx, vy, elem='freeze'):
        super().__init__(x, y)
        self.vx, self.vy = vx, vy
        self.life = 90
        self.elem = elem

    def update(self, game):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        r = self.rect
        if self.life <= 0 or game.level.blocked(r, 'shot'):
            self.dead = True
            game.splat(r.center, (200, 240, 255))
            return
        for e in list(game.enemies):
            if e.active and not e.trapped and r.colliderect(e.rect):
                self.dead = True
                if getattr(e, 'boss', False):
                    strike(game, e, 3, 'trap', r.center, self.elem)
                    if not e.dead:
                        e.frozen = max(e.frozen, 40)
                else:
                    e.trapped = 150
                    e.trap_elem = self.elem
                    e.kb_t = 0
                sound.play('ice')
                return

    def draw(self, surf, ox=0, oy=0):
        x, y = round(self.x) + ox + 6, round(self.y) + oy + 6
        pygame.draw.circle(surf, (180, 230, 255), (x, y), 6)
        pygame.draw.circle(surf, (240, 250, 255), (x, y), 6, 1)
        surf.set_at((x - 2, y - 2), (255, 255, 255))


class Bolt:
    """A jagged lightning bolt between points."""

    def __init__(self, points, col=None, t=14):
        self.points = points
        self.col = col or (255, 255, 160)
        self.t = t
        self.dead = False

    def update(self, game):
        self.t -= 1
        if self.t <= 0:
            self.dead = True

    def draw(self, surf, ox=0, oy=0):
        for (x0, y0), (x1, y1) in zip(self.points, self.points[1:]):
            pts = [(x0 + ox, y0 + oy)]
            for i in range(1, 5):
                k = i / 5
                pts.append((x0 + (x1 - x0) * k + random.uniform(-4, 4) + ox,
                            y0 + (y1 - y0) * k + random.uniform(-4, 4) + oy))
            pts.append((x1 + ox, y1 + oy))
            pygame.draw.lines(surf, self.col, False, pts, 3 if self.t > 8 else 1)
            pygame.draw.lines(surf, (255, 255, 255), False, pts, 1)


class Nova:
    """Nova: a ring of force that rings out around Octo. Magnety's version also drags things in."""

    def __init__(self, cx, cy, elem=None):
        self.x, self.y = cx, cy
        self.r = 6
        self.hit = set()
        self.elem = elem
        self.col = forms.ELEMENTS.get(elem, (0, 0, (180, 200, 255)))[2]
        self.dead = False

    def update(self, game):
        self.r += 4
        for e in list(game.enemies):
            if e.active and e not in self.hit:
                ex, ey = e.rect.center
                d = math.hypot(ex - self.x, ey - self.y)
                if d < self.r + 6:
                    self.hit.add(e)
                    if self.elem == 'pull':
                        if not getattr(e, 'boss', False) and d > 1:
                            for _ in range(8):
                                e.move((self.x - ex) / d * 2, (self.y - ey) / d * 2, game.level)
                            e.frozen = max(e.frozen, 40)
                        strike(game, e, 1, 'nova', (self.x, self.y))
                    else:
                        strike(game, e, 2, 'nova', (self.x, self.y), self.elem)
        if self.r > 80:
            self.dead = True

    def draw(self, surf, ox=0, oy=0):
        a = max(0, 200 - self.r * 2)
        ring = pygame.Surface((self.r * 2 + 4, self.r * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(ring, self.col + (a,), (self.r + 2, self.r + 2), self.r, 3)
        pygame.draw.circle(ring, (255, 255, 255, a), (self.r + 2, self.r + 2), max(1, self.r - 3), 1)
        surf.blit(ring, (self.x - self.r - 2 + ox, self.y - self.r - 2 + oy))


class Boomerang(Entity):
    """Boomerang: a spinning shell that flies out and comes back to Octo, hitting both ways."""
    hb = (0, 0, 12, 12)
    who = 'shot'

    def __init__(self, owner, dx, dy, elem=None):
        cx, cy = owner.rect.center
        super().__init__(cx - 6, cy - 6)
        self.owner = owner
        self.vx, self.vy = dx * 3.6, dy * 3.6
        self.t = 0
        self.back = False
        self.hits = set()
        self.elem = elem
        self.col = forms.ELEMENTS.get(elem, (0, 0, (250, 200, 170)))[2]

    def update(self, game):
        self.t += 1
        if not self.back:
            self.x += self.vx
            self.y += self.vy
            self.vx *= 0.95
            self.vy *= 0.95
            if self.t > 26 or game.level.blocked(self.rect, 'shot'):
                self.back = True
                self.hits = set()
        else:
            ox, oy = self.owner.rect.center
            cx, cy = self.rect.center
            d = math.hypot(ox - cx, oy - cy)
            if d < 10:
                self.dead = True
                return
            self.x += (ox - cx) / d * 4
            self.y += (oy - cy) / d * 4
        for e in list(game.enemies):
            if e.active and e not in self.hits and self.rect.colliderect(e.rect):
                self.hits.add(e)
                strike(game, e, 2, 'shell', self.rect.center, self.elem)
        if self.t > 150:
            self.dead = True

    def draw(self, surf, ox=0, oy=0):
        cx, cy = self.rect.centerx + ox, self.rect.centery + oy
        a = self.t * 0.6
        pts = [(cx + math.cos(a + i * math.tau / 3) * 6, cy + math.sin(a + i * math.tau / 3) * 6) for i in range(3)]
        pygame.draw.polygon(surf, (120, 70, 50), pts)
        pygame.draw.polygon(surf, self.col, pts, 2)
        pygame.draw.circle(surf, (255, 240, 220), (cx, cy), 2)


class Seeker(Entity):
    """Seekers: little stars that curve towards the nearest enemy."""
    hb = (0, 0, 6, 6)
    who = 'shot'

    def __init__(self, x, y, ang, elem=None):
        super().__init__(x, y)
        self.ang = ang
        self.life = 120
        self.elem = elem
        self.col = forms.ELEMENTS.get(elem, (0, 0, (255, 240, 150)))[2]
        self.trail = []

    def update(self, game):
        self.life -= 1
        cx, cy = self.rect.center
        target = game.nearest_enemy((cx, cy), 160)
        if target:
            tx, ty = target.rect.center
            want = math.atan2(ty - cy, tx - cx)
            diff = (want - self.ang + math.pi) % math.tau - math.pi
            self.ang += max(-0.12, min(0.12, diff))
        self.x += math.cos(self.ang) * 2.6
        self.y += math.sin(self.ang) * 2.6
        self.trail = (self.trail + [(cx, cy)])[-6:]
        if self.life <= 0 or game.level.blocked(self.rect, 'shot'):
            self.dead = True
            return
        for e in list(game.enemies):
            if e.active and self.rect.colliderect(e.rect):
                strike(game, e, 2, 'star', self.rect.center, self.elem)
                self.dead = True
                return

    def draw(self, surf, ox=0, oy=0):
        for i, (x, y) in enumerate(self.trail):
            pygame.draw.circle(surf, self.col, (int(x + ox), int(y + oy)), max(1, i // 2))
        cx, cy = self.rect.centerx + ox, self.rect.centery + oy
        a = self.life * 0.3
        pts = []
        for i in range(10):
            r = 5 if i % 2 == 0 else 2
            pts.append((cx + math.cos(a + i * math.pi / 5) * r, cy + math.sin(a + i * math.pi / 5) * r))
        pygame.draw.polygon(surf, (255, 255, 230), pts)
        pygame.draw.polygon(surf, self.col, pts, 1)


class Mine(Entity):
    """Mines: a jelly-blob mine sitting on the sea floor until an enemy bumps it."""
    hb = (0, 0, 10, 10)
    who = 'shot'

    def __init__(self, x, y, elem=None):
        super().__init__(x, y)
        self.t = 0
        self.life = 900
        self.elem = elem
        self.col = forms.ELEMENTS.get(elem, (0, 0, (230, 150, 255)))[2]

    def update(self, game):
        self.t += 1
        self.life -= 1
        if self.life <= 0:
            self.dead = True
            return
        if self.t < 20:
            return
        for e in list(game.enemies):
            if e.active and self.rect.inflate(8, 8).colliderect(e.rect):
                self.dead = True
                cx, cy = self.rect.center
                sound.play('boom')
                game.shake = max(game.shake, 4)
                for o in list(game.enemies):
                    if o.active and math.hypot(o.rect.centerx - cx, o.rect.centery - cy) < 26:
                        strike(game, o, 3, 'mine', (cx, cy), self.elem)
                for i in range(12):
                    a = i / 12 * math.tau
                    game.effects.append(Particle(cx, cy, math.cos(a) * 2, math.sin(a) * 2, self.col, 18, size=2))
                return

    def draw(self, surf, ox=0, oy=0):
        x, y = round(self.x) + ox + 5, round(self.y) + oy + 6
        wob = math.sin(self.t * 0.15)
        pygame.draw.ellipse(surf, (60, 20, 80), (x - 6, y - 4 + wob, 12, 9))
        pygame.draw.ellipse(surf, self.col, (x - 5, y - 4 + wob, 10, 7))
        if (self.t // 12) % 2:
            pygame.draw.circle(surf, (255, 255, 255), (x, int(y - 1 + wob)), 1)


class Boulder(Entity):
    """Boulder: a big rolling rock that crushes everything in its path and cracks rock walls."""
    hb = (0, 0, 14, 14)
    who = 'shot'

    def __init__(self, cx, cy, dx, dy, elem=None):
        super().__init__(cx - 7 + dx * 10, cy - 7 + dy * 10)
        self.vx, self.vy = dx * 2.6, dy * 2.6
        self.t = 0
        self.hits = set()
        self.elem = elem

    def update(self, game):
        self.t += 1
        self.x += self.vx
        self.y += self.vy
        r = self.rect
        game.blast_tiles(r.centerx, r.centery, 10)
        if game.level.blocked(r, 'shot') or self.t > 90:
            self.dead = True
            game.shake = max(game.shake, 6)
            sound.play('shut')
            for _ in range(8):
                game.effects.append(Particle(r.centerx, r.centery, random.uniform(-2, 2), random.uniform(-2, 1),
                                             (140, 120, 100), 20, grav=0.15, size=2))
            return
        for e in list(game.enemies):
            if e.active and e not in self.hits and r.inflate(4, 4).colliderect(e.rect):
                self.hits.add(e)
                strike(game, e, 3, 'boulder', (r.centerx - self.vx * 4, r.centery - self.vy * 4), self.elem)
        if self.t % 4 == 0:
            game.effects.append(Particle(r.centerx, r.bottom, random.uniform(-0.5, 0.5), -0.4,
                                         (170, 150, 110), 14))

    def draw(self, surf, ox=0, oy=0):
        cx, cy = self.rect.centerx + ox, self.rect.centery + oy
        sh = pygame.Surface((18, 6), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 20, 90), (0, 0, 18, 6))
        surf.blit(sh, (cx - 9, cy + 5))
        pygame.draw.circle(surf, (90, 80, 70), (cx, cy), 8)
        pygame.draw.circle(surf, (140, 126, 106), (cx - 1, cy - 1), 7)
        a = self.t * 0.25 * (1 if self.vx >= 0 else -1)
        for i in range(3):
            pygame.draw.line(surf, (90, 80, 70), (cx, cy), (cx + math.cos(a + i * 2.1) * 6, cy + math.sin(a + i * 2.1) * 6))
        pygame.draw.circle(surf, (190, 176, 150), (cx - 3, cy - 3), 2)
        if self.elem in forms.ELEMENTS:
            pygame.draw.circle(surf, forms.ELEMENTS[self.elem][2], (cx, cy), 8, 1)


# ===========================================================================
# The spirit altar (top of the Octo Temple)
# ===========================================================================

class Altar(Entity):
    hb = (0, 2, 32, 22)

    def __init__(self, x, y):
        super().__init__(x, y)
        self.t = 0
        self.lit = 0

    def update(self, game):
        self.t += 1
        self.lit = min(3, game.player.spirit)

    def draw(self, surf, ox=0, oy=0):
        x, y = round(self.x) + ox, round(self.y) + oy
        pygame.draw.rect(surf, (120, 100, 70), (x + 2, y + 6, 28, 10))
        pygame.draw.rect(surf, (200, 180, 136), (x + 2, y + 4, 28, 4))
        pygame.draw.rect(surf, (90, 74, 52), (x + 2, y + 4, 28, 12), 1)
        for i in range(3):
            cx = x + 8 + i * 8
            pygame.draw.circle(surf, (60, 46, 30), (cx, y + 4), 3)
            if i < self.lit:
                glow = 2 + ((self.t // 10 + i) % 2)
                pygame.draw.circle(surf, (190, 140, 255), (cx, y + 4), glow)
                surf.set_at((cx - 1, y + 3), (255, 255, 255))
        if self.lit >= 3 and (self.t // 15) % 2:
            pygame.draw.line(surf, (220, 190, 255), (x + 16, y - 6), (x + 16, y - 2))


# ===========================================================================
# The Fusion Machine (next to the Pearl Shop)
# ===========================================================================

class FusionMachine(Entity):
    hb = (0, 4, 32, 26)

    def __init__(self, x, y):
        super().__init__(x, y)
        self.t = 0

    def update(self, game):
        self.t += 1

    def draw(self, surf, ox=0, oy=0):
        x, y = round(self.x) + ox, round(self.y) + oy
        t = self.t
        # base and body
        pygame.draw.rect(surf, (40, 44, 60), (x + 1, y + 24, 30, 8))
        pygame.draw.rect(surf, (90, 100, 130), (x + 3, y + 10, 26, 16))
        pygame.draw.rect(surf, (140, 150, 180), (x + 3, y + 10, 26, 3))
        pygame.draw.rect(surf, (30, 30, 44), (x + 3, y + 10, 26, 16), 1)
        # two glass tanks bubbling with colour
        for i, col in enumerate(((250, 204, 40), (184, 228, 255))):
            tx = x + 4 + i * 16
            pygame.draw.rect(surf, (20, 30, 50), (tx, y, 8, 14))
            lvl = 6 + int(math.sin(t * 0.05 + i * 2) * 2)
            pygame.draw.rect(surf, col, (tx + 1, y + 14 - lvl, 6, lvl - 1))
            if (t + i * 7) % 14 < 7:
                surf.set_at((tx + 3, y + 14 - lvl - 2 + (t // 3) % 3), (255, 255, 255))
            pygame.draw.rect(surf, (200, 220, 240), (tx, y, 8, 14), 1)
        # mixing funnel and the result light
        pygame.draw.polygon(surf, (70, 78, 100), [(x + 12, y + 4), (x + 20, y + 4), (x + 18, y + 10), (x + 14, y + 10)])
        hue = (t // 8) % 3
        light = ((255, 120, 200), (120, 255, 200), (200, 160, 255))[hue]
        pygame.draw.circle(surf, light, (x + 16, y + 18), 4)
        pygame.draw.circle(surf, (255, 255, 255), (x + 15, y + 17), 1)
        # dials
        for i in range(3):
            pygame.draw.circle(surf, (230, 90, 70) if (t // 20 + i) % 3 == 0 else (60, 60, 70),
                               (x + 7 + i * 9, y + 23), 1)
