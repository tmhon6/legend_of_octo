"""Player, enemies, projectiles, pickups and effects."""
import math
import random

import pygame

import gfx
import sound
from settings import PLAYER_SPEED

DIRS = {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}


JET_FRAMES = 12          # speed-burst length
JET_SPEED = 4            # px per frame while jetting
JET_COOLDOWN = 40
SLAP_AIM_RANGE = 32      # px between centres: about the slap's real reach
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
        if self.mood in ('zap', 'ice', 'ghost', 'bubble', 'spiky', 'glow', 'air'):
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
            for e in game.enemies:
                if e.active and game.view_rect.colliderect(e.rect):
                    e.hit(game, 1, 'glow', (cx, cy))
                    if not e.dead:
                        e.frozen = max(e.frozen, 30 if isinstance(e, Shark) else 100)
            self.shoot_cd = 110
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
            self.shoot_cd = 26
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

    def jet(self, game, move_dir):
        """Speed burst: shoot backwards out of a puff of ink."""
        if self.dash_t or self.dash_cd or self.flip_t or self.knock_t:
            return
        self.attack_t = 0           # a jet cancels a slap or squirt
        d = move_dir or self.facing
        self.facing = d
        self.dash_dir = DIRS[d]
        self.dash_t = JET_FRAMES + (4 if 'fins' in self.items else 0)
        self.dash_cd = JET_COOLDOWN
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

    def speed(self):
        return PLAYER_SPEED * (1.35 if 'fins' in self.items else 1.0)

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
        if self.invuln or self.dash_t or self.bubble_t or self.tumble or dmg <= 0:
            return
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
        self.invuln = 70
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
        if self.invuln:
            self.invuln -= 1
        if self.shoot_cd:
            self.shoot_cd -= 1
        if self.fog_cd:
            self.fog_cd -= 1
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
        if move_dir:
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
        if move_dir:
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
        if self.frozen:
            self.frozen -= 1
            return
        self.t += 1
        if self.kb_t:
            self.kb_t -= 1
            for _ in range(3):
                self.move(self.kb[0], self.kb[1], game.level)
            return
        self.ai(game)

    def ai(self, game):
        pass

    def hit(self, game, dmg, kind, src):
        if not self.active or self.hurt_t:
            return False
        if kind in self.immune:
            sound.play('tink')
            game.spark(self.rect.center)
            return False
        self.hp -= dmg
        self.hurt_t = 18
        sound.play('hit')
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
        surf.blit(img, (round(self.x) + ox + jx, round(self.y) + oy))
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


SHELLY_TALK = [
    "OLD SHELLY: OCTO! GRIMFIN THE SHARK STOLE THE GOLDEN PEARL AND HID IN THE SUNKEN SHRINE TO THE NORTH!",
    "YOU'RE A REVERSIBLE OCTOPUS, REMEMBER? PRESS X TO FLIP YOUR MOOD.",
    "HAPPY BLUE OCTO SQUIRTS INK - PRESS C TO SWAP A LONG LINE FOR A SHORT WIDE BURST. GRUMPY BLACK OCTO SLAPS HARD AND CUTS KELP.",
    "INK PASSES RIGHT THROUGH JELLIES, AND SLAPPING AN URCHIN... OUCH. CHOOSE YOUR MOOD WISELY!",
    "IN A PINCH, PRESS V TO JET AWAY IN A PUFF OF INK. NOTHING CAN TOUCH YOU MID-JET, AND THE INK STINGS!",
    "GLOWING PORTALS LEAD TO TRIALS. BEAT ONE TO LEARN A NEW FORM - AND THE PORTAL BECOMES A WARP POINT (PRESS T).",
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
                    e.frozen = 45 if isinstance(e, Shark) else 170
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
            if 'shield' in p.items and self.vx * fx + self.vy * fy < 0 and not p.dash_t:
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
        if self.kind in ('container', 'golden', 'key', 'halfpearl'):
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
