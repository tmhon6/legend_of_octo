"""Player, enemies, projectiles, pickups and effects."""
import math
import random

import pygame

import forms
import fx
import gfx
import sound
import style
from settings import PLAYER_SPEED, TILE


def world_of(px, py):
    import world
    return world.world_at(int(px) // TILE, int(py) // TILE)

DIRS = {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}


JET_FRAMES = 12          # speed-burst length
JET_SPEED = 4            # px per frame while jetting
JET_COOLDOWN = 40
SLAP_AIM_RANGE = 32      # px between centres: about the slap's real reach
# attacks that STRONG forms (and fused forms) power up
PLAYER_HIT_KINDS = {'ink', 'slap', 'zap', 'ice', 'wisp', 'spike', 'glow', 'bubble', 'bomb', 'thorns',
                    'hail', 'whip', 'roll', 'quake', 'lantern', 'whirl', 'trap', 'chain', 'nova', 'shell',
                    'star', 'mine', 'boulder', 'beam', 'orb', 'rain',
                    'geyser', 'harpoon', 'saw', 'spray', 'sonar', 'mortar', 'swarm', 'grab', 'glitch'}
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
        self.hat = 'none'          # wardrobe: the hat Octo wears
        self.dash_col = 0          # wardrobe: ink jet colour
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
        if self.mood == forms.CORRUPT:
            # Corrupted's glitch wave: a square of static spreads out and corrupts every enemy it passes
            game.shots.append(GlitchWave(cx, cy))
            game.glitch_t = max(getattr(game, 'glitch_t', 0), 8)
            self.shoot_cd = 55
            self.attack_t = 10
            sound.play('glitch')
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
        if forms.is_mega(self.mood):
            m = forms.register_mega(self.mood)
            self.mega_cast(game, m['shape'], m['elements'], cx, cy)
            return
        if self.mood in forms.FUSIONS:
            f = forms.FUSIONS[self.mood]
            self.cast(game, f['shape'], f['element'], cx, cy)
        else:
            self.cast(game, forms.OWN_SHAPE[self.mood], forms.OWN_ELEMENT.get(self.mood), cx, cy)

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
        elif shape == 'beam':
            dx, dy = self.aim(game, cx, cy, 220)
            game.shots.append(Beam(cx, cy, dx, dy, elem))
            self.shoot_cd = 45
            sound.play('zap')
        elif shape == 'orbit':
            if any(isinstance(s, Orb) for s in game.shots):
                sound.play('nope')
                return
            for i in range(3):
                game.shots.append(Orb(self, i * math.tau / 3, elem))
            self.shoot_cd = 40
            sound.play('wisp')
        elif shape == 'rain':
            if any(isinstance(s, RainCloud) for s in game.shots):
                sound.play('nope')
                return
            game.shots.append(RainCloud(self, elem))
            self.shoot_cd = 40
            sound.play('whoosh')
        elif shape == 'boulder':
            if any(isinstance(s, Boulder) for s in game.shots):
                sound.play('nope')
                return
            dx, dy = DIRS[self.facing] if not game.nearest_enemy((cx, cy), 120) else self.aim(game, cx, cy)
            game.shots.append(Boulder(cx, cy, dx, dy, elem))
            self.shoot_cd = 50
            sound.play('shut')
        elif shape == 'geyser':
            seen = [e for e in game.enemies if e.active and game.view_rect.colliderect(e.rect)]
            seen.sort(key=lambda e: math.hypot(e.rect.centerx - cx, e.rect.centery - cy))
            for i, e in enumerate(seen[:3]):
                game.shots.append(GeyserSpout(e, e.rect.centerx, e.rect.bottom - 2, delay=i * 5, elem=elem))
            if not seen:
                dx, dy = DIRS[self.facing]
                game.shots.append(GeyserSpout(None, cx + dx * 34, cy + 6 + dy * 34, elem=elem))
            self.shoot_cd = 60
            sound.play('bubble')
        elif shape == 'harpoon':
            if any(isinstance(s, Harpoon) for s in game.shots):
                sound.play('nope')
                return
            dx, dy = self.aim(game, cx, cy, 160)
            game.shots.append(Harpoon(self, dx, dy, elem))
            self.shoot_cd = 30
            sound.play('harpoon')
        elif shape == 'saw':
            if sum(isinstance(s, SawBlade) for s in game.shots) >= 2:
                sound.play('nope')
                return
            dx, dy = self.aim(game, cx, cy)
            if abs(dx) < 0.05 or abs(dy) < 0.05:          # straight along: tilt it, so it ricochets about
                a = math.atan2(dy, dx) + 0.4
                dx, dy = math.cos(a), math.sin(a)
            game.shots.append(SawBlade(cx, cy, dx, dy, elem))
            self.shoot_cd = 30
            sound.play('saw')
        elif shape == 'spray':
            dx, dy = self.aim(game, cx, cy)
            base = math.atan2(dy, dx)
            for i in range(10):
                game.shots.append(SprayDrop(self, base + (-0.14, 0.0, 0.14, 0.07, -0.07)[i % 5], i * 3, i, elem))
            self.shoot_cd = 50
            sound.play('ink')
        elif shape == 'sonar':
            dx, dy = self.aim(game, cx, cy, 120)
            game.shots.append(SonarBlast(cx, cy, math.atan2(dy, dx), elem))
            self.shoot_cd = 50
            sound.play('sonar')
        elif shape == 'mortar':
            target = game.nearest_enemy((cx, cy), 170)
            if target:
                tx, ty = target.rect.center
            else:
                dx, dy = DIRS[self.facing]
                tx, ty = cx + dx * 70, cy + dy * 70
            game.shots.append(MortarShell(cx, cy, tx, ty, elem))
            self.shoot_cd = 55
            sound.play('shoot')
        elif shape == 'swarm':
            if any(isinstance(s, SwarmFish) for s in game.shots):
                sound.play('nope')
                return
            for i in range(6):
                game.shots.append(SwarmFish(self, i, elem))
            self.shoot_cd = 60
            sound.play('bubble')
        elif shape == 'grab':
            near = [e for e in game.enemies if e.active and math.hypot(e.rect.centerx - cx, e.rect.centery - cy) < 84]
            near.sort(key=lambda e: math.hypot(e.rect.centerx - cx, e.rect.centery - cy))
            for i, e in enumerate(near[:5]):
                game.shots.append(GrabTentacle(e, e.rect.centerx, e.rect.bottom, delay=i * 3, elem=elem))
            if not near:                                    # nobody near: three burst up round Octo anyway
                for i in range(3):
                    a = i / 3 * math.tau + 0.5
                    game.shots.append(GrabTentacle(None, cx + math.cos(a) * 20, cy + 6 + math.sin(a) * 14,
                                                   delay=i * 3, elem=elem))
            self.shoot_cd = 60
            sound.play('slap')

    def mega_cast(self, game, shape, elems, cx, cy):
        """The six mega attacks (from the secret Mega Machine). elems is a pair of elements."""
        self.attack_t = 12
        game.shake = max(game.shake, 8)
        if shape == 'supernova':
            game.shots.append(Nova(cx, cy, elems, max_r=150, dmg=4))
            self.shoot_cd = 80
            sound.play('boom')
        elif shape == 'tsunami':
            dx, dy = self.aim(game, cx, cy)
            px, py = -dy, dx
            for off in (-18, 0, 18):
                game.shots.append(Quake(cx + px * off, cy + py * off, (round(dx) or 0, round(dy) or 0)
                                        if abs(dx) + abs(dy) else DIRS[self.facing], elems))
            self.shoot_cd = 70
            sound.play('whoosh')
        elif shape == 'meteor':
            seen = [e for e in game.enemies if e.active and game.view_rect.colliderect(e.rect)]
            spots = [e.rect.center for e in seen[:12]] or \
                [(cx + math.cos(a) * 50, cy + math.sin(a) * 50) for a in (0.3, 1.9, 3.5, 5.1)]
            for i, (tx, ty) in enumerate(spots):
                game.shots.append(Hail(tx, ty, delay=i * 4, elem=elems))
                game.shots.append(Hail(tx + 6, ty - 4, delay=i * 4 + 10, elem=elems))
            self.shoot_cd = 90
            sound.play('boom')
        elif shape == 'blackhole':
            dx, dy = self.aim(game, cx, cy)
            game.shots.append(Whirlpool(cx, cy, dx, dy, elems))
            game.shots.append(Nova(cx + dx * 40, cy + dy * 40, 'pull', max_r=90, dmg=1))
            self.shoot_cd = 80
            sound.play('whoosh')
        elif shape == 'prism':
            dx, dy = self.aim(game, cx, cy, 220)
            base = math.atan2(dy, dx)
            for k in range(-3, 4):
                a = base + k * 0.22
                game.shots.append(Beam(cx, cy, math.cos(a), math.sin(a), elems))
            self.shoot_cd = 70
            sound.play('zap')
        elif shape == 'titan':
            for e in list(game.enemies):
                if e.active and math.hypot(e.rect.centerx - cx, e.rect.centery - cy) < 80:
                    strike(game, e, 4, 'quake', (cx, cy), elems)
            for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                game.shots.append(Quake(cx, cy, d, elems))
            game.effects.append(fx.ImpactRing(cx, cy, big=True, col=(255, 215, 80)))
            game.shake = 18
            self.shoot_cd = 75
            sound.play('boom')

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
        self.dash_cd = int(JET_COOLDOWN * self.stat('jet', 1.0) * (0.6 if 'jetink' in self.items else 1.0) *
                           (0.5 if 'u_quickjet' in self.items else 1.0))
        cx, cy = self.rect.center
        game.shots.append(InkCloud(cx - self.dash_dir[0] * 4, cy - self.dash_dir[1] * 4, self.dash_col))
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
        return PLAYER_SPEED * (1.35 if 'fins' in self.items else 1.0) * self.stat('speed', 1.0) * \
            (1.12 if 'u_turbo' in self.items else 1.0)

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
        if self.stat('dodge', 0) and random.random() < self.stat('dodge', 0):
            self.invuln = 30                      # Sandy side-steps the hit
            if self.mood == forms.CORRUPT:        # Corrupted glitches right through it
                game.toast = ("GLITCHED!", 40)
                game.glitch_t = max(getattr(game, 'glitch_t', 0), 6)
                game.burst(self.rect.center, (255, 50, 220), 6)
                return
            game.toast = ("DODGED!", 40)
            game.burst(self.rect.center, (240, 220, 160), 6)
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
        if moving and not self.in_sky and self.idle_t % 22 == 0 and \
                world_of(cx, cy) not in __import__('world').DRY_WORLDS:   # no bubbles on dry land
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
                game.effects.append(JetInk(cx - dx * 6 + random.uniform(-2, 2), cy - dy * 6 + random.uniform(-2, 2),
                                           -dx * 0.5, -dy * 0.5, self.dash_col))
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
            if ch == 'U':
                game.sigil_bump('shrine')
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
        self._draw_slap(surf, ox, oy)
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
        if not self.dash_t and not self.flip_t:
            style.draw_hat(surf, getattr(self, 'hat', 'none'), x, y, self.facing, self.idle_t)
        self._draw_aura(surf, x, y)

    def _draw_slap(self, surf, ox, oy):
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

    def _draw_aura(self, surf, x, y):
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
        if getattr(self, 'poison', 0):
            self.poison -= 1
            if self.poison % 50 == 0:
                self.hurt_t = 0
                self.hit(game, 1, 'poison', (self.rect.centerx, self.rect.bottom))
                game.effects.append(Particle(self.rect.centerx, self.rect.top, 0, -0.5, (150, 230, 80), 16))
                if self.dead:
                    return
        if getattr(self, 'corrupt', 0):            # Corrupted: it glitches, and now and then that hurts
            self.corrupt -= 1
            if self.corrupt % 40 == 0:
                self.hurt_t = 0
                self.hit(game, 1, 'corrupt', (self.rect.centerx, self.rect.bottom))
                game.effects.append(Particle(self.rect.centerx + random.uniform(-4, 4), self.rect.top, 0, -0.4,
                                             random.choice(GLITCH_COLS), 14))
                if self.dead:
                    return
        if getattr(self, 'weak', 0):
            self.weak -= 1
        if getattr(self, 'slow', 0):
            self.slow -= 1
            if self.slow % 2:
                return                              # sludge: it only acts every other frame
        if getattr(self, 'dizzy', 0) and not getattr(self, 'boss', False):
            self.dizzy -= 1
            if self.dizzy % 40 == 0:
                self.dizzy_dir = random.choice(list(DIRS.values()))
            dx, dy = getattr(self, 'dizzy_dir', (1, 0))
            if not self.move(dx * 0.5, dy * 0.5, game.level):
                self.dizzy_dir = (-dx, -dy)
            if self.t % 10 == 0:
                game.effects.append(Particle(self.rect.centerx, self.rect.top, random.uniform(-0.5, 0.5), -0.4,
                                             (255, 160, 230), 12))
            return
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
            if game.player.stat('crit', 0) and random.random() < game.player.stat('crit', 0):
                dmg *= 2                             # Crysty: a sharp, critical hit
                game.spark(self.rect.center)
            if 'u_megaink' in game.player.items and random.random() < 0.25:
                dmg += 1                             # the Mega Ink milestone
                game.spark(self.rect.center)
        if getattr(self, 'weak', 0):
            dmg += 1
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
        if getattr(self, 'corrupt', 0):            # the corruption jumps to its neighbours
            game.shots.append(GlitchWave(*self.rect.center, max_r=48, dmg=0))

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
# guardians of the new regions: big, fierce versions of each region's own creature
#   (each drops a spirit pearl -- see Game.guardian_beaten)
_G = lambda name, base, tint, hp, dmg, speed, moves, minion, shot, **kw: dict(
    name=name, base=base, tint=tint, hp=hp, dmg=dmg, speed=speed, moves=moves, minion=minion, shot=shot, **kw)
MINIBOSS_STYLES.update({
    'glassking': _G("GLASS KING", 'glassfish', (220, 245, 255), 22, 2, 1.0, ('charge', 'spread', 'ring'), 'glassfish', 'spine', fly=True),
    'sirenqueen': _G("SIREN QUEEN", 'seahorse', (255, 190, 230), 22, 2, 0.8, ('teleport', 'spread', 'summon'), 'seahorse', 'bubble', fly=True),
    'gulper': _G("THE GULPER", 'hagfish', (200, 150, 170), 26, 3, 0.7, ('charge', 'summon', 'charge'), 'hagfish', 'bubble'),
    'thunderhawk': _G("THUNDERHAWK", 'sparkbird', (180, 200, 255), 24, 2, 1.1, ('charge', 'spread', 'ring'), 'sparkbird', 'spine', fly=True),
    'prismlord': _G("PRISM LORD", 'prism', (255, 220, 255), 24, 2, 0.7, ('ring', 'teleport', 'ring'), 'prism', 'spine', fly=True),
    'comet': _G("COMET", 'starling', (255, 240, 170), 24, 2, 1.0, ('teleport', 'ring', 'charge'), 'starling', 'spine', fly=True),
    'hopperking': _G("SAND KING", 'sandhopper', (255, 230, 170), 20, 2, 0.9, ('charge', 'summon', 'charge'), 'sandhopper', 'spine'),
    'stagbeetle': _G("STAG BEETLE", 'beetle', (170, 255, 200), 26, 2, 0.8, ('charge', 'ring', 'charge'), 'beetle', 'spine'),
    'kingkong': _G("BIG BANANA", 'monkey', (255, 210, 160), 24, 2, 0.9, ('spread', 'summon', 'spread'), 'monkey', 'spine'),
    'deathstalker': _G("DUNE STALKER", 'scorpion', (255, 200, 120), 26, 3, 0.8, ('charge', 'spread', 'charge'), 'scorpion', 'spine'),
    'lavaboss': _G("MAGMA MAW", 'magmite', (255, 170, 120), 28, 3, 0.8, ('charge', 'ring', 'summon'), 'magmite', 'spine'),
    'geode': _G("GEODE", 'crystalbug', (190, 230, 255), 28, 2, 0.7, ('ring', 'summon', 'ring'), 'crystalbug', 'spine'),
    'mushking': _G("KING TOADSTOOL", 'sporeling', (255, 170, 210), 28, 2, 0.6, ('summon', 'spread', 'ring'), 'sporeling', 'bubble'),
    'bonelord': _G("BONE LORD", 'skullfish', (240, 235, 220), 30, 3, 0.8, ('charge', 'teleport', 'spread'), 'skullfish', 'spine', phase=True),
    'colossus': _G("COLOSSUS", 'golem', (170, 255, 230), 36, 3, 0.6, ('charge', 'ring', 'charge'), 'golem', 'spine'),
    'pyrosaur': _G("PYROSAUR", 'salamander', (255, 160, 90), 32, 3, 0.9, ('charge', 'spread', 'ring'), 'salamander', 'spine'),
})


class MiniBoss(Enemy):
    """A big, tough cousin of a regular enemy that guards one region (or a temple, or a trial).

    It fights in three stages (it breaks apart and gets fiercer as it's hurt). Besides the moves
    every boss knows (charge, ring, spread, summon, teleport) each kind has signature moves of its
    own - crabs and golems leap and slam down, jellies and crystals spin spirals, birds fire
    barrages, puffers burst, fish dash, storm and fire bosses call strikes down from above - and
    every attack is warned on the floor first, in red. When it's beaten it doesn't just vanish: it
    shudders, cracks with little blasts and bursts apart."""
    knockback = False
    spawn_time = 50
    boss = True
    hb = (4, 6, 24, 22)
    _frames = {}
    _accents = {}

    STAGE_SPEED = {1: 1.0, 2: 1.3, 3: 1.6}
    STAGE_REST = {1: (80, 120), 2: (55, 85), 3: (35, 60)}
    CRABS = ('crab', 'icecrab', 'lavacrab')
    # each kind's two signature moves (the second joins in once the boss breaks)
    SIGNATURE = {
        'crab': ('slam', 'slam'), 'icecrab': ('slam', 'rain'), 'lavacrab': ('slam', 'rain'), 'golem': ('slam', 'nova'),
        'beetle': ('slam', 'dash'), 'sandhopper': ('slam', 'dash'), 'monkey': ('slam', 'barrage'),
        'magmite': ('rain', 'nova'), 'jelly': ('spiral', 'nova'), 'urchin': ('spiral', 'nova'),
        'prism': ('spiral', 'barrage'), 'crystalbug': ('spiral', 'rain'), 'sporeling': ('nova', 'spiral'),
        'starling': ('rain', 'spiral'), 'gull': ('barrage', 'rain'), 'sparkbird': ('rain', 'barrage'),
        'scorpion': ('barrage', 'dash'), 'salamander': ('barrage', 'rain'), 'skullfish': ('dash', 'spiral'),
        'puffer': ('nova', 'barrage'), 'glassfish': ('dash', 'barrage'), 'seahorse': ('dash', 'spiral'),
        'hagfish': ('dash', 'nova'),
    }
    RAIN = {'icecrab': 'ice', 'lavacrab': 'fire', 'magmite': 'fire', 'salamander': 'fire', 'gull': 'bolt',
            'sparkbird': 'bolt', 'starling': 'rock', 'crystalbug': 'ice'}
    WINDUP = {'charge': 36, 'ring': 30, 'spread': 34, 'summon': 30, 'teleport': 40, 'slam': 34, 'spiral': 22,
              'barrage': 30, 'nova': 44, 'dash': 1, 'rain': 36}
    FURY = (255, 70, 50)

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
        self.lift = 0.0           # how high it is in the air (leaping)
        self.swell = 0.0          # 0..1 as it gathers itself for a burst (its aura grows)
        self.dying_t = 0          # beaten: counting down its last moments
        self.warn = None          # the warning on the floor for the attack it's winding up
        self.aura = None
        self.spin_a = random.uniform(0, math.tau)
        self.spin_dir = random.choice((-1, 1))
        self.trail = 1.0          # the health bar's "just lost" part, draining after a hit
        self.sub, self.sub_t = 0, 0   # (a step within a move: the dashes)

    # ---- looks -------------------------------------------------------------------------------
    @property
    def accent(self):
        """The boss's own colour (from its sprite's brightest pixels): its orbs and aura."""
        c = MiniBoss._accents.get(self.bid)
        if c is None:
            src = gfx.SPR[self.cfg['base']][0]
            src = gfx.tint(src, self.cfg['tint']) if self.cfg.get('tint') else src
            px = [src.get_at((x, y)) for y in range(src.get_height()) for x in range(src.get_width())]
            px = [p for p in px if p.a > 128 and p.r + p.g + p.b > 200] or [pygame.Color(255, 120, 120)]
            avg = [sum(p[i] for p in px) / len(px) for i in range(3)]
            hi = max(avg) or 1
            c = MiniBoss._accents[self.bid] = tuple(min(255, int(v / hi * 255 * 0.9 + 25)) for v in avg)
        return c

    @property
    def orb_col(self):
        return self.FURY if self.stage >= 3 else self.accent

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
                out.append(pygame.transform.scale2x(f))    # (doubled with smoothed edges, not blocks)
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
        game.effects.append(Debris(pygame.transform.scale2x(piece), self.x, self.y,
                                   -1.5 if self.stage == 2 else 1.5))
        self._calm()
        self.hurt_t = 40
        self.frozen = 0
        self.state, self.state_t = 'roam', 50
        game.shake = 18
        game.hitstop = 10
        sound.play('roar')
        game.toast = (f"{self.name} {'BREAKS' if self.stage == 2 else 'IS FURIOUS'}!", 90)
        cx, cy = self.rect.center
        game.effects.append(Shock(cx, cy, self.orb_col, 1.3))
        for i in range(18):
            a = i / 18 * math.tau
            game.effects.append(Particle(cx, cy, math.cos(a) * 2.4, math.sin(a) * 2.4,
                                         self.orb_col if i % 2 else (255, 240, 210), 24, size=2))

    # ---- moving ------------------------------------------------------------------------------
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

    def _fits(self, x, y, room):
        r = pygame.Rect(x + self.hb[0], y + self.hb[1], self.hb[2], self.hb[3])
        if not room.bounds.contains(r):
            return False
        return self.who == 'flyer' or self.cfg.get('phase') or not room.blocked(r, self.who)

    def _landing(self, tx, ty, room):
        """Where a leap ends: on Octo if there's room, else as near him as it can get."""
        sx, sy = self.x, self.y
        gx, gy = tx - 16, ty - 18
        for k in (1.0, 0.8, 0.6, 0.4, 0.2):
            x, y = sx + (gx - sx) * k, sy + (gy - sy) * k
            if self._fits(x, y, room):
                return x, y
        return sx, sy

    def _orb(self, game, x, y, a, speed, r=4, spin=0.0, accel=0.0):
        game.shots.append(BossOrb(x, y, math.cos(a) * speed, math.sin(a) * speed, self.orb_col, r, spin, accel))

    def _calm(self):
        """Stop whatever it was winding up (its warning goes too)."""
        if self.warn is not None:
            self.warn.dead = True
            self.warn = None
        self.lift = 0.0
        self.swell = 0.0

    def _aim_line(self, game, cx, cy, ux, uy, length, life):
        if self.warn is None or self.warn.dead:
            self.warn = Warn(cx, cy, 0, life, cx, cy)
            game.effects.append(self.warn)
        self.warn.x, self.warn.y = cx, cy
        self.warn.x1, self.warn.y1 = cx + ux * length, cy + uy * length

    # ---- fighting ----------------------------------------------------------------------------
    def ai(self, game):
        room = game.level
        if self.aura is None or self.aura.dead:
            self.aura = BossAura(self)
            game.effects.append(self.aura)
        if self.dying_t:
            self._dying(game)
            return
        if self.lurk:                                # waiting: just drift about its lair
            self.y += math.sin(self.t * 0.05) * 0.2
            return
        stage = 1 if self.hp > self.max_hp * 2 / 3 else 2 if self.hp > self.max_hp / 3 else 3
        if stage > self.stage:
            self._break(game, stage)
            return
        if self.stage >= 3 and self.t % 7 == 0:       # furious: steam rising off it
            r = self.rect
            game.effects.append(Particle(random.uniform(r.left + 4, r.right - 4), r.top + 4, random.uniform(-0.2, 0.2),
                                         -0.7, (255, 120, 90), 22, -0.01))
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
                self.state_t = self.WINDUP[self.state]
                self.sub = 0
        elif st == 'charge':
            if self.state_t > 0:                    # wind-up: shudder in place, the path shown in red
                self._aim_line(game, cx, cy, ux, uy, 90, self.state_t + 2)
                return
            if self.state_t == 0:
                self._calm()
                s = 3.6 if enraged else 3.0
                self.v = (ux * s, uy * s)
                sound.play('jet')
            if self.t % 3 == 0:
                game.effects.append(Particle(cx, cy, -self.v[0] * 0.3, -self.v[1] * 0.3, self.orb_col, 14, size=2))
            if not self._step(self.v[0], self.v[1], room) or self.state_t < -40:
                if self.state_t >= -40:
                    game.shake = 6
                    sound.play('shut')
                    if enraged:                     # furious: it bursts on hitting the wall
                        for i in range(6):
                            self._orb(game, cx, cy, i / 6 * math.tau + self.spin_a, 1.4)
                self._end(enraged)
        elif st == 'ring':
            if self.state_t == 0:
                n = 12 if enraged else 8
                off = random.random()
                for i in range(n):
                    self._orb(game, cx, cy, (i + off) / n * math.tau, 1.6)
                game.effects.append(Shock(cx, cy, self.orb_col, 0.8))
                sound.play('shoot')
                self._end(enraged)
            else:
                self.swell = 1 - self.state_t / 30
        elif st == 'spread':
            if self.state_t in (20, 10, 0):
                base = math.atan2(uy, ux)
                for da in ((-0.5, -0.25, 0, 0.25, 0.5) if enraged else (-0.35, 0, 0.35)):
                    self._orb(game, cx, cy, base + da, 2.0, r=3)
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
        elif st == 'slam':
            self._slam(game, room, tx, ty, enraged)
        elif st == 'spiral':
            self._spiral(game, cx, cy, enraged)
        elif st == 'barrage':
            self._barrage(game, cx, cy, ux, uy, enraged)
        elif st == 'nova':
            self._nova(game, cx, cy, ux, uy, enraged)
        elif st == 'dash':
            self._dash(game, room, cx, cy, ux, uy, enraged)
        elif st == 'rain':
            self._rain(game, room, tx, ty, enraged)

    def _slam(self, game, room, tx, ty, enraged):
        """Crouch (the landing spot glows red under Octo), leap high and crash down, throwing out a
        ring of orbs."""
        if self.state_t == self.WINDUP['slam'] - 1:
            self.target = self._landing(tx, ty, room)
            x, y = self.target
            self.warn = Warn(x + 16, y + 18, 20, self.WINDUP['slam'] + 30)
            game.effects.append(self.warn)
        if self.state_t > 0:
            return
        if self.state_t == 0:
            self.jump_from = (self.x, self.y)
            sound.play('jet')
        k = min(1.0, -self.state_t / 28)
        (sx, sy), (gx, gy) = self.jump_from, self.target
        self.x, self.y = sx + (gx - sx) * k, sy + (gy - sy) * k
        self.lift = math.sin(math.pi * k) * 38
        if k >= 1.0:
            self._calm()
            cx, cy = self.rect.center
            n = 16 if self.stage >= 3 else 12 if enraged else 10
            off = random.random()
            for i in range(n):
                self._orb(game, cx, cy + 4, (i + off) / n * math.tau, 1.5)
            game.effects.append(Shock(cx, cy + 6, (255, 235, 200), 1.6))
            for i in range(12):
                a = i / 12 * math.tau
                game.effects.append(Particle(cx + math.cos(a) * 10, cy + 8 + math.sin(a) * 5, math.cos(a) * 1.6,
                                             math.sin(a) * 0.8 - 0.4, (220, 210, 190), 20, 0.06, size=2))
            game.shake = 10
            sound.play('boom')
            self._end(enraged)

    def _spiral(self, game, cx, cy, enraged):
        """Spin in place, glowing, then pour out a spiral of orbs."""
        if self.state_t > 0:
            self.swell = 1 - self.state_t / self.WINDUP['spiral']
            return
        i = -self.state_t
        self.swell = 1.0
        if i % (4 if self.stage >= 3 else 5) == 0:
            arms = 1 + self.stage
            for j in range(arms):
                self._orb(game, cx, cy, self.spin_a + j * math.tau / arms, 1.25, r=3)
            self.spin_a += 0.3 * self.spin_dir
            if i % 15 == 0:
                sound.play('shoot')
        if i >= 70 + 20 * self.stage:
            self.spin_dir = -self.spin_dir
            self._end(enraged)

    def _barrage(self, game, cx, cy, ux, uy, enraged):
        """Take aim (a red line to Octo), then fire a rapid stream at him."""
        if self.state_t > 0:
            self._aim_line(game, cx, cy, ux, uy, 120, self.state_t + 2)
            return
        if self.state_t == 0:
            self._calm()
        i = -self.state_t
        if i % 4 == 0:
            a = math.atan2(uy, ux) + random.uniform(-0.1, 0.1)
            for da in ((-0.28, 0.0, 0.28) if self.stage >= 3 else (0.0,)):
                self._orb(game, cx, cy, a + da, 2.3, r=3)
            if i % 8 == 0:
                sound.play('shoot')
        if i >= 40:
            self._end(enraged)

    def _nova(self, game, cx, cy, ux, uy, enraged):
        """Swell up, flashing, then burst into a ring of orbs with one gap to slip through (and,
        once broken, a second slower ring)."""
        if self.state_t > 0:
            self.swell = 1 - self.state_t / self.WINDUP['nova']
            if self.state_t % 12 == 0:
                sound.play('tick')
            return
        if self.state_t == 0:
            self.swell = 0.0
            n = 26
            gap = math.atan2(uy, ux) + random.uniform(-1.2, 1.2)
            for i in range(n):
                a = i / n * math.tau
                if abs((a - gap + math.pi) % math.tau - math.pi) > 0.42:
                    self._orb(game, cx, cy, a, 1.7)
            game.effects.append(Shock(cx, cy, self.orb_col, 1.4))
            game.shake = 6
            sound.play('boom')
        if self.state_t == -20 and enraged:
            n = 16
            for i in range(n):
                self._orb(game, cx, cy, (i + 0.5) / n * math.tau, 1.05, r=3)
            sound.play('shoot')
        if self.state_t <= -22:
            self._end(enraged)

    def _dash(self, game, room, cx, cy, ux, uy, enraged):
        """Three quick dashes at Octo, each shown first with a red line."""
        if self.sub == 0:                             # (just started)
            self.dash_n, self.sub, self.sub_t = 2 + (self.stage >= 2), 1, 16
        self.sub_t -= 1
        if self.sub == 1:                             # aim
            self._aim_line(game, cx, cy, ux, uy, 100, self.sub_t + 2)
            if self.sub_t <= 0:
                self._calm()
                s = 4.2 if enraged else 3.6
                self.v = (ux * s, uy * s)
                self.sub, self.sub_t = 2, 24
                sound.play('jet')
        elif self.sub == 2:                           # dash
            if self.t % 2 == 0:
                game.effects.append(Particle(cx, cy, -self.v[0] * 0.25, -self.v[1] * 0.25, self.orb_col, 12, size=2))
            if not self._step(self.v[0], self.v[1], room) or self.sub_t <= 0:
                self.dash_n -= 1
                self.sub, self.sub_t = 3, 10
        elif self.sub_t <= 0:                         # a breath, then the next one
            if self.dash_n <= 0:
                self.sub = 0
                self._end(enraged)
            else:
                self.sub, self.sub_t = 1, 14

    def _rain(self, game, room, tx, ty, enraged):
        """Rear up, glowing, and call things crashing down: on Octo, and all round him (each spot
        is ringed in red first)."""
        self.swell = 1 - max(0, self.state_t) / self.WINDUP['rain']
        if self.state_t == 18:
            kind = self.RAIN.get(self.cfg['base'], 'rock')
            n = (5, 8, 11)[self.stage - 1]
            b = room.bounds
            for j in range(n):
                if j == 0:
                    x, y = tx, ty
                else:
                    a = random.uniform(0, math.tau)
                    rr = random.uniform(22, 80)
                    x, y = tx + math.cos(a) * rr, ty + math.sin(a) * rr
                x = max(b.left + 10, min(b.right - 10, x))
                y = max(b.top + 10, min(b.bottom - 10, y))
                game.effects.append(Strike(x, y, 44 + j * 7, kind, dmg=2 if self.stage >= 3 else 1, loud=j % 2 == 0))
            sound.play('wisp')
        if self.state_t <= 0:
            self.swell = 0.0
            self._end(enraged)

    def _end(self, enraged):
        self._calm()
        self.state = 'roam'
        self.state_t = random.randint(*self.STAGE_REST[self.stage])

    def moveset(self):
        """Its routine: its own moves and its signature move; later stages add more."""
        moves = list(self.cfg['moves'])
        sig = self.SIGNATURE.get(self.cfg['base'], ('slam', 'slam'))
        moves.insert(1, sig[0])
        if self.stage >= 2:
            moves += [sig[1]]
            moves += ['spread'] if self.cfg['base'] in self.CRABS else ['ring']
        if self.stage >= 3:
            moves += [sig[0]]
            moves += ['charge', 'summon'] if self.cfg['base'] in self.CRABS else ['spread', 'summon']
        return moves

    @property
    def active(self):
        return self.spawn_t == 0 and not self.dead and self.fade > 120 and not self.dying_t and self.lift < 8

    # ---- the end -----------------------------------------------------------------------------
    def die(self, game):
        """Beaten: it doesn't vanish straight away - it shudders, cracks with little blasts and
        bursts apart (see _dying), and only then is it gone."""
        if self.dying_t or self.dead:
            return
        self._calm()
        self.dying_t = 64
        self.hp = 0
        self.damage = 0
        self.frozen = self.kb_t = self.trapped = 0
        self.state = 'dying'
        for m in self.minions:
            if not m.dead:
                m.dead = True
                game.effects.append(Puff(m.x, m.y))
        game.shots = [s for s in game.shots if not isinstance(s, EnemyShot)]
        game.hitstop = max(getattr(game, 'hitstop', 0), 16)
        game.shake = 14
        sound.play('roar')

    def _dying(self, game):
        self.dying_t -= 1
        r = self.rect
        if self.dying_t % 7 == 0 and self.dying_t > 10:          # little blasts all over it
            x, y = random.uniform(r.left, r.right), random.uniform(r.top, r.bottom)
            game.effects.append(fx.ImpactRing(x, y, big=True))
            for i in range(5):
                a = random.uniform(0, math.tau)
                game.effects.append(Particle(x, y, math.cos(a) * 1.5, math.sin(a) * 1.5,
                                             random.choice((self.accent, (255, 240, 200), (255, 180, 80))), 16, size=2))
            game.shake = max(game.shake, 4)
            sound.play('hit')
        if self.dying_t <= 0:
            self._burst(game)

    def _burst(self, game):
        """The final blast: it flies apart in pieces, and the fight is won."""
        cx, cy = self.rect.center
        img = self.frames()[0]
        w, h = img.get_size()
        for i, (px, py) in enumerate(((0, 0), (w // 2, 0), (0, h // 2), (w // 2, h // 2))):
            piece = img.subsurface((px, py, w // 2, h // 2)).copy()
            game.effects.append(Debris(piece, self.x + px, self.y + py, (-1.8, 1.8, -1.2, 1.2)[i]))
        game.effects.append(Shock(cx, cy, (255, 240, 200), 2.2))
        game.effects.append(Shock(cx, cy, self.accent, 1.5))
        for i in range(36):
            a = i / 36 * math.tau
            sp = random.uniform(1.5, 3.4)
            game.effects.append(Particle(cx, cy, math.cos(a) * sp, math.sin(a) * sp,
                                         random.choice((self.accent, (255, 245, 220), (255, 200, 90))), 30, size=2))
        game.flash_t = max(getattr(game, 'flash_t', 0), 14)
        sound.play('boom')
        self.dying_t = 0
        self.dead = True
        game.shake = 16
        for i in range(6):
            game.effects.append(Puff(self.x + random.randint(0, 20), self.y + random.randint(0, 20), delay=i * 5))
        game.miniboss_defeated(self)

    # ---- drawing -----------------------------------------------------------------------------
    def draw(self, surf, ox=0, oy=0):
        if self.spawn_t:
            frames = gfx.SPR['puff']
            i = min(3, (self.spawn_time - min(self.spawn_t, self.spawn_time)) * 4 // self.spawn_time)
            img = pygame.transform.scale(frames[3 - i], (32, 32))
            surf.blit(img, (round(self.x) + ox, round(self.y) + oy))
            return
        fr = self.frames()
        if self.cfg['base'] == 'puffer':
            img = fr[2] if self.state in ('ring', 'spread', 'nova') else fr[(self.t // 12) % 2]
        else:
            img = fr[(self.t // 10) % 2]
        if self.face < 0 and self.cfg['base'] in ('puffer', 'gull'):
            img = gfx.flipped(img)
        if self.frozen:
            img = gfx.icy(img)
        if self.hurt_t and (self.hurt_t // 2) % 2:
            img = gfx.flash(img)
        jx = jy = 0
        winding = self.state in ('charge', 'slam', 'nova') and self.state_t > 0
        if winding or self.dying_t:
            jx = random.choice((-1, 0, 1))
            jy = random.choice((0, 1)) if self.state == 'slam' else 0
            if (self.state_t if winding else self.dying_t) % 8 < 4:
                img = gfx.flash(img)
        if self.fade < 255:
            img = img.copy()
            img.set_alpha(self.fade)
        lift = round(self.lift)
        surf.blit(img, (round(self.x) + ox + jx, round(self.y) + oy + jy - lift))
        # a little crown so it reads as a boss
        cx, top = round(self.x) + ox + 16 + jx, round(self.y) + oy - 3 - lift
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



# ---------------------------------------------------------------------------
# Regional enemies: every part of the sea has its own creature
# ---------------------------------------------------------------------------
def _aim(e, game, speed):
    px, py = game.player.seen_pos()
    cx, cy = e.rect.center
    d = math.hypot(px - cx, py - cy) or 1
    return (px - cx) / d * speed, (py - cy) / d * speed, d


def _fire(game, e, vx, vy, kind, life=None):
    cx, cy = e.rect.center
    size = 10 if kind in ('bubble', 'ember') else 6
    game.shots.append(EnemyShot(cx - size // 2, cy - size // 2, vx, vy, kind, life=life))


class SandEel(Enemy):
    """Coral Reef: hides under the sand as a ripple, then bursts up to bite."""
    max_hp = 3
    sprite = 'eel'
    hb = (3, 1, 10, 14)

    def __init__(self, x, y):
        super().__init__(x, y)
        self.up = 0
        self.cool = random.randint(40, 100)

    @property
    def active(self):
        return self.spawn_t == 0 and not self.dead and self.up > 0

    def ai(self, game):
        if self.up:
            self.up -= 1
            if self.up > 60:
                vx, vy, _ = _aim(self, game, 0.9)
                self.move(vx, vy, game.level)
            if self.up == 0:
                self.cool = random.randint(60, 120)
                game.splat(self.rect.center, (220, 200, 150))
            return
        vx, vy, d = _aim(self, game, 0.45)
        if d < 130:
            self.move(vx, vy, game.level)
        self.cool -= 1
        if self.cool <= 0 and d < 40:
            self.up = 90
            sound.play('shoot')
            game.splat(self.rect.center, (220, 200, 150))

    def draw(self, surf, ox=0, oy=0):
        if self.spawn_t or self.up:
            return super().draw(surf, ox, oy)
        cx, cy = self.rect.centerx + ox, self.rect.bottom + oy - 3
        w = 8 + int(math.sin(self.t * 0.2) * 2)
        pygame.draw.ellipse(surf, (170, 150, 100), (cx - w // 2, cy - 2, w, 4), 1)
        surf.set_at((cx, cy - 3), (240, 230, 200))


class SnapjawClam(Enemy):
    """Kelp Woods: shut tight, nothing hurts it. It opens to spit pearls -- strike then!"""
    max_hp = 4
    sprite = 'clam'
    knockback = False
    hb = (0, 4, 16, 12)

    def __init__(self, x, y):
        super().__init__(x, y)
        self.phase = random.randint(0, 150)

    def is_open(self):
        return self.phase % 190 >= 120

    def hit(self, game, dmg, kind, src):
        if self.active and not self.is_open() and kind != 'bomb':
            if not self.hurt_t:
                sound.play('tink')
                game.spark(self.rect.center)
                self.hurt_t = 10
            return False
        return super().hit(game, dmg, kind, src)

    def ai(self, game):
        self.phase += 1
        if self.phase % 190 == 140:
            vx, vy, d = _aim(self, game, 1.6)
            if d < 150:
                for a in (-0.25, 0, 0.25):
                    c, sn = math.cos(a), math.sin(a)
                    _fire(game, self, vx * c - vy * sn, vx * sn + vy * c, 'bubble')
                sound.play('bubble')

    def die(self, game):
        super().die(game)
        game.drop_loot(self.rect.center, 2.0)

    def image(self):
        return gfx.SPR['clam'][1 if self.is_open() else 0]


class Lionfish(Enemy):
    """Coral Gardens: venomous spines -- slaps bounce off, and it fans out spines."""
    max_hp = 3
    damage = 2
    sprite = 'lionfish'
    immune = ('slap',)
    hb = (3, 3, 11, 10)

    def __init__(self, x, y):
        super().__init__(x, y)
        self.vx, self.vy = random.choice((-0.3, 0.3)), 0.0
        self.shot_t = random.randint(80, 160)

    def ai(self, game):
        self.shot_t -= 1
        if self.shot_t <= 0:
            self.shot_t = 150
            vx, vy, d = _aim(self, game, 1.5)
            if d < 140:
                for a in (-0.5, -0.25, 0, 0.25, 0.5):
                    c, sn = math.cos(a), math.sin(a)
                    _fire(game, self, vx * c - vy * sn, vx * sn + vy * c, 'spine')
                sound.play('shoot')
            return
        if self.t % 80 == 0:
            self.vy = random.choice((-0.25, 0, 0.25))
        if not self.move(self.vx, 0, game.level):
            self.vx = -self.vx
        if not self.move(0, self.vy, game.level):
            self.vy = -self.vy

    def image(self):
        img = gfx.SPR['lionfish'][(self.t // 14) % 2]
        return gfx.flipped(img) if self.vx < 0 else img


class Stingray(Enemy):
    """The Lagoon: glides fast in long straight lines, over trenches too."""
    max_hp = 3
    damage = 2
    sprite = 'ray'
    who = 'flyer'
    hb = (2, 3, 12, 9)

    def __init__(self, x, y):
        super().__init__(x, y)
        a = random.choice((0.6, 2.5, 3.8, 5.6))
        self.vx, self.vy = math.cos(a) * 1.4, math.sin(a) * 1.4
        self.rest = 0

    def ai(self, game):
        if self.rest:
            self.rest -= 1
            return
        bounced = False
        if not self.move(self.vx, 0, game.level):
            self.vx = -self.vx
            bounced = True
        if not self.move(0, self.vy, game.level):
            self.vy = -self.vy
            bounced = True
        if bounced and random.random() < 0.4:
            self.rest = 24
            vx, vy, _ = _aim(self, game, 1.5)
            self.vx, self.vy = vx, vy

    def image(self):
        return gfx.SPR['ray'][(self.t // 10) % 2]


class Anglerfish(Enemy):
    """The Abyss: creeps after you behind its glowing lure, then lunges with a mouth full of teeth."""
    max_hp = 5
    damage = 2
    sprite = 'angler'
    who = 'flyer'
    hb = (2, 5, 12, 10)

    def __init__(self, x, y):
        super().__init__(x, y)
        self.state, self.state_t = 'creep', 60
        self.v = (0.0, 0.0)

    def ai(self, game):
        self.state_t -= 1
        vx, vy, d = _aim(self, game, 0.3)
        if self.state == 'creep':
            if d < 150:
                self.move(vx, vy, game.level)
            if d < 52 and self.state_t <= 0:
                self.state, self.state_t = 'tell', 26
                self.v = (vx / 0.3 * 2.9, vy / 0.3 * 2.9)
        elif self.state == 'tell':
            self.x += random.choice((-1, 1)) * 0.5
            if self.state_t <= 0:
                self.state, self.state_t = 'lunge', 18
                sound.play('shoot')
        elif self.state == 'lunge':
            self.move(*self.v, game.level)
            if self.state_t <= 0:
                self.state, self.state_t = 'creep', 70

    def draw(self, surf, ox=0, oy=0):
        if not self.spawn_t:
            glow = pygame.Surface((24, 24), pygame.SRCALPHA)
            pygame.draw.circle(glow, (255, 255, 160, 60 + int(math.sin(self.t * 0.15) * 30)), (12, 12), 10)
            surf.blit(glow, (round(self.x) + ox + 12 - 12, round(self.y) + oy + 2 - 12))
        super().draw(surf, ox, oy)

    def image(self):
        img = gfx.SPR['angler'][(self.t // 16) % 2]
        return gfx.flipped(img) if self.v[0] < 0 else img


class BilgeGhost(Enemy):
    """Ship Graveyard: a drowned sailor's ghost that drifts through walls, fading in and out."""
    max_hp = 3
    sprite = 'bilge'
    who = 'flyer'
    knockback = False
    hb = (3, 2, 10, 12)

    def __init__(self, x, y):
        super().__init__(x, y)
        self.cycle = random.randint(0, 200)

    def solid_now(self):
        return self.cycle % 220 < 150

    @property
    def active(self):
        return self.spawn_t == 0 and not self.dead and self.solid_now()

    def ai(self, game):
        self.cycle += 1
        vx, vy, d = _aim(self, game, 0.45 if self.solid_now() else 0.8)
        if d < 170:
            nx, ny = self.x + vx, self.y + vy
            if game.level.bounds.contains(pygame.Rect(nx + 3, ny + 2, 10, 12)):
                self.x, self.y = nx, ny

    def draw(self, surf, ox=0, oy=0):
        if self.spawn_t:
            return super().draw(surf, ox, oy)
        c = self.cycle % 220
        a = 255 if c < 140 else 60 if c >= 160 and c < 210 else 140
        img = self.image().copy()
        if self.hurt_t and (self.hurt_t // 2) % 2:
            img = gfx.flash(img)
        img.set_alpha(a)
        surf.blit(img, (round(self.x) + ox, round(self.y) + oy + round(math.sin(self.t * 0.07) * 2)))
        if a == 255:
            self.draw_hp(surf, ox, oy)

    def image(self):
        return gfx.SPR['bilge'][(self.t // 15) % 2]


class IceSquid(Enemy):
    """Frozen Shelf: jets about in pulses and fires ice shards in four directions."""
    max_hp = 4
    sprite = 'squid'
    who = 'flyer'
    hb = (3, 1, 10, 12)

    def __init__(self, x, y):
        super().__init__(x, y)
        self.v = [0.0, 0.0]
        self.shot_t = random.randint(60, 140)

    def ai(self, game):
        if self.t % 70 == 0:
            vx, vy, d = _aim(self, game, 2.0)
            if d > 140:
                a = random.uniform(0, math.tau)
                vx, vy = math.cos(a) * 1.6, math.sin(a) * 1.6
            self.v = [vx, vy]
        self.v[0] *= 0.95
        self.v[1] *= 0.95
        if not self.move(self.v[0], 0, game.level):
            self.v[0] = -self.v[0]
        if not self.move(0, self.v[1], game.level):
            self.v[1] = -self.v[1]
        self.shot_t -= 1
        if self.shot_t <= 0:
            self.shot_t = 130
            diag = (self.t // 130) % 2
            for a in range(4):
                ang = a * math.pi / 2 + (math.pi / 4 if diag else 0)
                _fire(game, self, math.cos(ang) * 1.7, math.sin(ang) * 1.7, 'ice')
            sound.play('shoot')

    def image(self):
        return gfx.SPR['squid'][1 if abs(self.v[0]) + abs(self.v[1]) > 0.8 else 0]


class CinderSlug(Enemy):
    """Ember Vents: oozes after Octo, leaving patches of fire that linger."""
    max_hp = 5
    damage = 2
    sprite = 'slug'
    immune = ('burn',)
    hb = (1, 7, 14, 9)

    def ai(self, game):
        vx, vy, d = _aim(self, game, 0.35)
        self.face = -1 if vx < 0 else 1
        if d < 160:
            if not self.move(vx, 0, game.level):
                self.move(0, vy * 1.5 or 0.35, game.level)
            self.move(0, vy, game.level)
        if self.t % 45 == 0 and d < 200:
            cx, cy = self.rect.center
            game.shots.append(EnemyShot(cx - 5, cy - 3, 0, 0, 'ember', life=170))

    def image(self):
        img = gfx.SPR['slug'][(self.t // 20) % 2]
        return gfx.flipped(img) if getattr(self, 'face', 1) < 0 else img


class LanternWisp(Enemy):
    """Sunken City: blinks out, reappears beside Octo, and bursts a ring of bubbles."""
    max_hp = 3
    sprite = 'wisp'
    who = 'flyer'
    knockback = False
    hb = (3, 3, 10, 10)

    def __init__(self, x, y):
        super().__init__(x, y)
        self.cycle = random.randint(0, 120)

    @property
    def active(self):
        return self.spawn_t == 0 and not self.dead and not (150 <= self.cycle % 200 < 175)

    def ai(self, game):
        self.cycle += 1
        c = self.cycle % 200
        if c == 162:                           # reappear somewhere near Octo
            px, py = game.player.rect.center
            for _ in range(12):
                a = random.uniform(0, math.tau)
                nx, ny = px + math.cos(a) * 52 - 8, py + math.sin(a) * 52 - 8
                r = pygame.Rect(nx + 3, ny + 3, 10, 10)
                if not game.level.blocked(r, 'flyer') and game.view_rect.contains(r):
                    self.x, self.y = nx, ny
                    break
        elif c == 185:
            for a in range(6):
                ang = a * math.tau / 6 + self.t * 0.1
                _fire(game, self, math.cos(ang) * 1.3, math.sin(ang) * 1.3, 'bubble')
            sound.play('bubble')
        elif c < 150:
            vx, vy, _ = _aim(self, game, 0.3)
            self.move(vx, vy, game.level)

    def draw(self, surf, ox=0, oy=0):
        c = self.cycle % 200
        if not self.spawn_t and 150 <= c < 175:
            if c < 158:
                pygame.draw.circle(surf, (200, 170, 255), (self.rect.centerx + ox, self.rect.centery + oy), 158 - c, 1)
            return
        super().draw(surf, ox, oy)

    def image(self):
        return gfx.SPR['wisp'][(self.t // 8) % 2]


class CloudPuff(Enemy):
    """Sky Islands: a grumpy little cloud. Pop it and it splits in two!"""
    max_hp = 3
    sprite = 'cloud'
    who = 'flyer'
    hb = (2, 3, 12, 10)

    def __init__(self, x, y, small=False):
        super().__init__(x, y)
        self.small = small
        if small:
            self.max_hp = self.hp = 1
            self.spawn_t = 0
            self.hb = (4, 5, 8, 7)

    def ai(self, game):
        vx, vy, d = _aim(self, game, 0.8 if self.small else 0.45)
        wob = math.sin(self.t * 0.06) * 0.4
        if d < 160:
            self.move(vx - vy * wob, vy + vx * wob, game.level)

    def die(self, game):
        if not self.small:
            for dx in (-6, 6):
                kid = CloudPuff(self.x + dx, self.y, small=True)
                kid.damage = self.damage
                kid.spawn = {'kind': 'cloud', 'arena': 'trial', 'inst': None, 'killed': False}
                kid.kb, kid.kb_t = (sign(dx), 0), 6
                game.enemies.append(kid)
        super().die(game)

    def image(self):
        return gfx.SPR['cloudlet' if self.small else 'cloud'][(self.t // 18) % 2]



# ---------------------------------------------------------------------------
# Creatures of the new regions: one configurable class, sixteen kinds
# ---------------------------------------------------------------------------
#   move:   wander | chase | hop | glide | orbit | burrow | phase | blink | crawl
#   attack: None | aimed | spread | ring | trail | lunge | split
CRITTERS = {
    # the eastern sea
    'glassfish': dict(name="GLASSFISH", region='GLASS REEF', hp=3, dmg=2, move='glide', speed=1.2, attack='aimed',
                      shot='ice', every=110, fly=True, doc="DARTS IN STRAIGHT LINES AND SPITS GLASS SHARDS."),
    'seahorse': dict(name="SEAHORSE", region='SIREN SHOALS', hp=3, dmg=1, move='hop', speed=1.6, attack='spread',
                     shot='bubble', every=130, fly=True, doc="BOUNCES ABOUT AND BLOWS FANS OF BUBBLES."),
    'hagfish': dict(name="HAGFISH", region='WHALE FALL', hp=5, dmg=2, move='burrow', speed=0.5, attack='lunge',
                    doc="SLITHERS UNDER THE MUD, THEN LUNGES OUT WITH ITS SLIMY JAWS."),
    # the sky
    'sparkbird': dict(name="SPARKBIRD", region='THUNDERHEADS', hp=3, dmg=2, move='orbit', speed=1.0, attack='aimed',
                      shot='spine', every=90, fly=True, doc="CIRCLES YOU AND FIRES CRACKLING SPARKS."),
    'prism': dict(name="PRISM", region='RAINBOW REACH', hp=4, dmg=1, move='glide', speed=0.8, attack='ring',
                  shot='ice', every=150, fly=True, immune=('slap',), doc="A FLOATING CRYSTAL THAT SPLITS LIGHT INTO RINGS."),
    'starling': dict(name="STARLING", region='STARFALL PEAKS', hp=3, dmg=2, move='blink', speed=0.4, attack='ring',
                     shot='spine', every=200, fly=True, doc="BLINKS ACROSS THE SKY AND BURSTS INTO STAR SHARDS."),
    # the surface
    'sandhopper': dict(name="SANDHOPPER", region='SUNNY BEACH', hp=2, dmg=1, move='hop', speed=2.0, attack=None,
                       doc="A JUMPY BEACH BUG THAT LEAPS AT YOU."),
    'beetle': dict(name="SHELL BEETLE", region='TIDE MEADOWS', hp=4, dmg=2, move='wander', speed=0.6, attack='lunge',
                   immune=('ink',), doc="INK SLIDES OFF ITS SHELL. IT CHARGES WHEN IT SPOTS YOU."),
    'monkey': dict(name="COCONUT MONKEY", region='PALM JUNGLE', hp=3, dmg=1, move='wander', speed=0.8, attack='aimed',
                   shot='spine', every=100, doc="SCAMPERS ABOUT, LOBBING COCONUTS."),
    'scorpion': dict(name="SCORPION", region='DUNE DESERT', hp=4, dmg=2, move='chase', speed=0.55, attack='lunge',
                     immune=('slap',), doc="STALKS YOU ACROSS THE DUNES, THEN STRIKES WITH ITS STINGER."),
    'magmite': dict(name="MAGMITE", region='VOLCANO RIDGE', hp=4, dmg=2, move='hop', speed=1.4, attack='trail',
                    immune=('burn',), doc="A HOPPING BLOB OF LAVA THAT LEAVES FIRE WHERE IT LANDS."),
    # the underdeep
    'crystalbug': dict(name="CRYSTAL BUG", region='CRYSTAL CAVES', hp=4, dmg=1, move='wander', speed=0.7,
                       attack='ring', shot='ice', every=140, immune=('ink',), doc="SHOOTS SHARDS IN A RING. INK BOUNCES OFF."),
    'sporeling': dict(name="SPORELING", region='FUNGUS GROTTO', hp=3, dmg=1, move='chase', speed=0.45, attack='split',
                      doc="A WADDLING MUSHROOM. POP IT AND IT SPLITS INTO TWO."),
    'skullfish': dict(name="SKULLFISH", region='BONE TRENCH', hp=4, dmg=2, move='phase', speed=0.6, attack='lunge',
                      fly=True, doc="A BONY FISH THAT SWIMS THROUGH WALLS AND SNAPS."),
    'golem': dict(name="RUIN GOLEM", region='ANCIENT RUINS', hp=9, dmg=3, move='crawl', speed=0.35, attack='lunge',
                  knockback=False, doc="SLOW, HUGE AND HARD-HITTING. KEEP YOUR DISTANCE."),
    'salamander': dict(name="SALAMANDER", region='MAGMA CORE', hp=5, dmg=2, move='glide', speed=1.0, attack='trail',
                       immune=('burn',), doc="SWIMS THROUGH THE HEAT, LEAVING FLAMES IN ITS WAKE."),
}

# fused creatures: each moves like the first and attacks like the second
HYBRID_PAIRS = [('glassfish', 'scorpion'), ('seahorse', 'sparkbird'), ('hagfish', 'skullfish'),
                ('sparkbird', 'salamander'), ('prism', 'crystalbug'), ('starling', 'sporeling'),
                ('sandhopper', 'magmite'), ('beetle', 'prism'), ('monkey', 'seahorse'), ('scorpion', 'glassfish'),
                ('magmite', 'starling'), ('crystalbug', 'golem'), ('sporeling', 'monkey'), ('skullfish', 'beetle'),
                ('golem', 'sparkbird'), ('salamander', 'sandhopper')]


def hybrid_kind(a, b):
    return f"h_{a}_{b}"


def _make_hybrids():
    for a, b in HYBRID_PAIRS:
        ca, cb = CRITTERS[a], CRITTERS[b]
        wa, wb = ca['name'].split()[0], cb['name'].split()[-1]
        name = (wa[:(len(wa) + 1) // 2] + wb[len(wb) // 2:]).upper()
        cfg = dict(name=name + " (FUSED)", region=ca['region'], hp=round((ca['hp'] + cb['hp']) * 0.75),
                   dmg=max(ca['dmg'], cb['dmg']), move=ca['move'], speed=ca['speed'],
                   attack=cb['attack'] or ca['attack'], shot=cb.get('shot', ca.get('shot', 'spine')),
                   every=min(ca.get('every', 140), cb.get('every', 140)), fly=ca.get('fly') or cb.get('fly'),
                   immune=tuple(set(ca.get('immune', ())) | set(cb.get('immune', ()))),
                   knockback=ca.get('knockback', True) and cb.get('knockback', True),
                   hybrid=(a, b),
                   doc=f"A FUSED CREATURE: MOVES LIKE A {ca['name']}, ATTACKS LIKE A {cb['name']}.")
        CRITTERS[hybrid_kind(a, b)] = cfg


_make_hybrids()


class Critter(Enemy):
    """A creature built from its CRITTERS entry: how it moves and how it attacks."""
    hb = (2, 3, 12, 12)

    def __init__(self, x, y, kind, small=False):
        super().__init__(x, y)
        cfg = CRITTERS[kind]
        self.kind, self.cfg, self.small = kind, cfg, small
        self.sprite = kind
        self.max_hp = self.hp = 1 if small else cfg['hp']
        self.damage = cfg['dmg']
        self.immune = cfg.get('immune', ())
        self.who = 'flyer' if cfg.get('fly') else 'walker'
        self.knockback = cfg.get('knockback', True)
        self.v = [random.choice((-1, 1)) * cfg['speed'], random.choice((-1, 1)) * cfg['speed'] * 0.7]
        self.timer = random.randint(30, cfg.get('every', 120))
        self.state, self.state_t = 'move', 0
        self.ang = random.uniform(0, math.tau)
        self.cycle = random.randint(0, 150)
        if small:
            self.spawn_t = 0
            self.hb = (4, 6, 8, 8)

    # hiding and phasing creatures can't be hit while they're away
    @property
    def active(self):
        if self.spawn_t or self.dead:
            return False
        m = self.cfg['move']
        if m == 'burrow':
            return self.state != 'hidden'
        if m == 'phase':
            return self.cycle % 220 < 150
        if m == 'blink':
            return not (150 <= self.cycle % 200 < 172)
        return True

    def ai(self, game):
        cfg = self.cfg
        sp = cfg['speed'] * (1.3 if self.small else 1)
        self.cycle += 1
        vx, vy, d = _aim(self, game, 1.0)
        # --- attacks that interrupt movement
        if self.state == 'tell':
            self.state_t -= 1
            self.x += random.choice((-0.5, 0.5))
            if self.state_t <= 0:
                self.state, self.state_t = 'lunge', 16
                sound.play('shoot')
            return
        if self.state == 'lunge':
            self.state_t -= 1
            self.move(self.v[0], self.v[1], game.level)
            if self.state_t <= 0:
                self.state, self.state_t = 'move', 60
            return
        if cfg['attack'] == 'lunge' and d < 56 and self.state_t <= 0 and self.active:
            self.state, self.state_t = 'tell', 22
            self.v = [vx * 2.8, vy * 2.8]
            return
        if self.state_t > 0:
            self.state_t -= 1
        self.timer -= 1
        if self.timer <= 0 and self.active and d < 170:
            self.timer = cfg.get('every', 120)
            self.shoot(game, vx, vy)
        if cfg['attack'] == 'trail' and self.t % 40 == 0 and d < 200:
            cx, cy = self.rect.center
            game.shots.append(EnemyShot(cx - 5, cy - 3, 0, 0, 'ember', life=160))
        # --- movement
        m = cfg['move']
        if m == 'wander':
            if self.t % 70 == 0:
                a = random.uniform(0, math.tau)
                self.v = [math.cos(a) * sp, math.sin(a) * sp]
            if d < 90:
                self.v = [vx * sp, vy * sp] if cfg['attack'] in ('lunge', None) else self.v
            self._bounce(game)
        elif m in ('chase', 'crawl'):
            if d < 180:
                self.move(vx * sp, 0, game.level) or self.move(0, (vy or 1) * sp, game.level)
                self.move(0, vy * sp, game.level)
        elif m == 'hop':
            if self.t % 50 == 0:
                if d < 160:
                    self.v = [vx * sp, vy * sp]
                else:
                    a = random.uniform(0, math.tau)
                    self.v = [math.cos(a) * sp, math.sin(a) * sp]
            if self.t % 50 < 18:                      # mid-hop
                self._bounce(game)
        elif m == 'glide':
            self._bounce(game)
        elif m == 'orbit':
            px, py = game.player.seen_pos()
            self.ang += 0.03 * sp
            tx, ty = px + math.cos(self.ang) * 56 - 8, py + math.sin(self.ang) * 40 - 8
            self.move((tx - self.x) * 0.05, (ty - self.y) * 0.05, game.level)
        elif m == 'burrow':
            if self.state == 'hidden':
                if d < 140:
                    self.move(vx * sp, vy * sp, game.level)
                if d < 36:
                    self.state = 'move'
                    self.cycle = 0
                    game.splat(self.rect.center, (160, 140, 110))
            elif self.cycle > 110:
                self.state = 'hidden'
            else:
                self.move(vx * sp * 0.6, vy * sp * 0.6, game.level)
        elif m == 'phase':
            if d < 170:
                nx, ny = self.x + vx * sp, self.y + vy * sp
                if game.level.bounds.contains(pygame.Rect(nx + 3, ny + 3, 10, 10)):
                    self.x, self.y = nx, ny
        elif m == 'blink':
            c = self.cycle % 200
            if c == 160:
                px, py = game.player.rect.center
                for _ in range(10):
                    a = random.uniform(0, math.tau)
                    nx, ny = px + math.cos(a) * 60 - 8, py + math.sin(a) * 60 - 8
                    r = pygame.Rect(nx + 3, ny + 3, 10, 10)
                    if not game.level.blocked(r, 'flyer') and game.view_rect.contains(r):
                        self.x, self.y = nx, ny
                        break
            elif c == 180:
                self.shoot(game, vx, vy)
            elif c < 150:
                self.move(vx * sp, vy * sp, game.level)

    def _bounce(self, game):
        if not self.move(self.v[0], 0, game.level):
            self.v[0] = -self.v[0]
        if not self.move(0, self.v[1], game.level):
            self.v[1] = -self.v[1]

    def shoot(self, game, vx, vy):
        cfg = self.cfg
        kind = cfg.get('shot', 'spine')
        a = cfg['attack']
        if a == 'aimed':
            _fire(game, self, vx * 1.8, vy * 1.8, kind)
        elif a == 'spread':
            for t in (-0.35, 0, 0.35):
                c, sn = math.cos(t), math.sin(t)
                _fire(game, self, (vx * c - vy * sn) * 1.6, (vx * sn + vy * c) * 1.6, kind)
        elif a == 'ring':
            n = 6
            for i in range(n):
                t = i * math.tau / n + self.t * 0.05
                _fire(game, self, math.cos(t) * 1.4, math.sin(t) * 1.4, kind)
        else:
            return
        sound.play('shoot')

    def die(self, game):
        if self.cfg['attack'] == 'split' and not self.small:
            for dx in (-6, 6):
                kid = Critter(self.x + dx, self.y, self.kind, small=True)
                kid.damage = self.damage
                kid.spawn = {'kind': self.kind, 'arena': 'trial', 'inst': None, 'killed': False}
                kid.kb, kid.kb_t = (sign(dx), 0), 6
                game.enemies.append(kid)
        super().die(game)

    def image(self):
        frames = gfx.SPR[self.kind]
        img = frames[(self.t // 12) % 2]
        if self.small:
            img = pygame.transform.scale(img, (10, 10))
        return gfx.flipped(img) if self.v[0] < 0 else img

    def draw(self, surf, ox=0, oy=0):
        m = self.cfg['move']
        if not self.spawn_t and not self.active:
            if m == 'burrow':
                cx, cy = self.rect.centerx + ox, self.rect.bottom + oy - 3
                w = 8 + int(math.sin(self.t * 0.2) * 2)
                pygame.draw.ellipse(surf, (120, 110, 90), (cx - w // 2, cy - 2, w, 4), 1)
            elif m == 'blink' and self.cycle % 200 < 158:
                pygame.draw.circle(surf, (255, 240, 160), (self.rect.centerx + ox, self.rect.centery + oy),
                                   max(1, 158 - self.cycle % 200), 1)
            elif m == 'phase':
                img = self.image().copy()
                img.set_alpha(70)
                surf.blit(img, (round(self.x) + ox, round(self.y) + oy))
            return
        if self.state == 'tell' and (self.t // 3) % 2:
            img = gfx.flash(self.image())
            surf.blit(img, (round(self.x) + ox, round(self.y) + oy))
            return
        super().draw(surf, ox, oy)


def _critter_factory(kind):
    return lambda x, y: Critter(x, y, kind)


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
               'murk': Murk, 'icecrab': IceCrab, 'lavacrab': LavaCrab,
               # one creature of its own for every region
               'eel': SandEel, 'clam': SnapjawClam, 'lionfish': Lionfish, 'ray': Stingray, 'angler': Anglerfish,
               'bilge': BilgeGhost, 'squid': IceSquid, 'slug': CinderSlug, 'wisp': LanternWisp, 'cloud': CloudPuff}
ENEMY_TYPES.update({k: _critter_factory(k) for k in CRITTERS})


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
HAT_WARES = [('hat_' + h, style.HATS[h][0], price, "A HAT FOR OCTO, JUST FOR FUN. WEAR IT IN THE WARDROBE (PRESS H).",
              True) for h, price in style.HAT_PRICES.items()]
CATALOGUE = SHOP_WARES + [
    ('potion', "SEA POTION", 20, "IF YOU FALL, IT SAVES YOU ONCE AND REFILLS HALF YOUR HEARTS. CARRY UP TO 2.", False),
    ('bigbag', "BIG BOMB BAG", 30, "CARRY 20 BUBBLE BOMBS INSTEAD OF 10.", True),
    ('compass', "TRIAL COMPASS", 25, "EVERY TRIAL PORTAL SHOWS ON YOUR MAP, EVEN WHERE YOU HAVEN'T BEEN.", True),
    ('charm', "LUCKY CHARM", 40, "ENEMIES DROP TREASURE 50% MORE OFTEN.", True),
    ('goggles', "DEEP GOGGLES", 35, "SEE MUCH FARTHER IN DARK PLACES.", True),
    ('jetink', "JET INK", 30, "YOUR INK JET RECHARGES FASTER.", True),
    ('armor', "CORAL ARMOR", 60, "BIG HITS HURT HALF A HEART LESS - IN EVERY FORM.", True),
    ('pmagnet', "PEARL MAGNET", 30, "PEARLS AND HEARTS NEARBY FLY STRAIGHT TO YOU.", True),
    *HAT_WARES,
    ('spiritpearl', "SPIRIT PEARL", 120, "A SPIRIT PEARL FOR THE TEMPLE ALTAR. PRICEY, BUT NO TRIAL NEEDED.", False),
]


def max_bombs(p):
    return 20 if 'bigbag' in p.items else MAX_BOMBS


SHELLY_TALK = [
    "OLD SHELLY: OCTO! GRIMFIN THE SHARK AND HIS BIG SISTER MURK STOLE THE GOLDEN PEARL - THE HEART OF THE "
    "WHOLE REEF. WITHOUT IT THE SEA WILL SLOWLY GO DARK!",
    "MURK LOCKED THE PEARL IN HER PALACE IN THE SUNKEN CITY, FAR TO THE SOUTHEAST, AND SEALED THE DOOR WITH "
    "SEVEN TIDE BELLS. RING ALL SEVEN AND THE SEAL BREAKS.",
    "THE BELLS ARE HIDDEN IN THE SUNKEN SHRINE AND IN SIX DEEP TEMPLES. MURK PUT A GUARDIAN IN EVERY REGION, "
    "AND EACH ONE CARRIES THE SIGIL THAT UNSEALS ITS DUNGEON. BEAT THE GUARDIAN, OPEN THE DUNGEON, RING THE BELL!",
    "IT WON'T BE EASY. TRAIN IN THE TRIALS TO LEARN NEW FORMS, HUNT FOR HEART SHELLS, AND CARRY SEA POTIONS!",
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
    "THERE ARE FOUR WORLDS, OCTO: THE SEA, THE SKY ABOVE IT, THE SURFACE AND THE UNDERDEEP BELOW. PRESS M AND "
    "LEFT/RIGHT TO FLIP BETWEEN THE MAPS OF THE ONES YOU'VE SEEN.",
    "WHITE SHORE STEPS IN THE LAGOON, THE REEF AND THE SIREN SHOALS LEAD UP ONTO THE SURFACE. PURPLE SINKHOLES "
    "IN THE ABYSS, THE SHIP GRAVEYARD AND WHALE FALL DROP DOWN INTO THE UNDERDEEP.",
    "FAR EAST, PAST THE FROZEN SHELF, THE EMBER VENTS AND THE SUNKEN CITY, THE SEA GOES ON: GLASS REEF, THE SIREN "
    "SHOALS AND DARK WHALE FALL.",
    "THE GUARDIANS OF THE NEW LANDS EACH CARRY A SPIRIT PEARL, AND THE NEW TRIALS TEACH NEW FORMS: SANDY, LEAFY, "
    "CRYSTY, CLOUDY, SHROOMY AND MAGMY. CLOUDY FLOATS OVER GAPS, MAGMY WALKS ON LAVA!",
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

    def __init__(self, cx, cy, color=0):
        self.x, self.y = cx, cy
        self.t = 0
        self.color = color          # the ink colour picked in the wardrobe
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
            pygame.draw.circle(s, style.dash_rgb(self.color, self.t + int(bx * 3)) + (int(190 * fade),),
                               (int(c + bx * r / 16), int(c + by * r / 16)), rr)
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

    def __init__(self, x, y, vx, vy, kind, life=None):
        super().__init__(x, y)
        self.vx, self.vy = vx, vy
        self.kind = kind
        self.damage = 1
        self.t = 0
        self.life = life
        size = 10 if kind in ('bubble', 'ember') else 6
        self.hb = (1, 1, size - 2, size - 2)

    def update(self, game):
        self.t += 1
        if self.life is not None:
            self.life -= 1
            if self.life <= 0:
                self.dead = True
                return
        self.x += self.vx
        self.y += self.vy
        r = self.rect
        if self.kind == 'ember':                 # a patch of fire on the floor: only hurts if touched
            if r.colliderect(game.player.rect) and self.t > 20 and not game.player.stat('heatproof', 0):
                game.player.hurt(game, self.damage, r.center)
            if self.t > 20 and getattr(game, 'snail', None) is not None:
                game.coop_hit_by_shot(self)
            return
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
        elif getattr(game, 'snail', None) is not None and game.coop_hit_by_shot(self):
            self.dead = True                    # Pebble took it

    def draw(self, surf, ox=0, oy=0):
        img = gfx.SPR['shots'][self.kind]
        if self.kind == 'ember' and self.life is not None and self.life < 40 and (self.t // 3) % 2:
            return
        wob = int(math.sin(self.t * 0.3) * 1) if self.kind == 'bubble' else 0
        surf.blit(img, (round(self.x) + ox + wob, round(self.y) + oy))


# the mini-bosses' own attacks (see MiniBoss)
class BossOrb(EnemyShot):
    """A glowing orb a mini-boss fires: bigger and brighter than a creature's shot, in the boss's
    own colour. It can curve as it flies (spin) or speed up (accel)."""

    def __init__(self, x, y, vx, vy, col, r=4, spin=0.0, accel=0.0):
        super().__init__(x - r, y - r, vx, vy, 'orb')
        self.col, self.r, self.spin, self.accel = col, r, spin, accel
        self.hb = (2, 2, 2 * r - 4, 2 * r - 4)

    def update(self, game):
        if self.spin:
            c, s = math.cos(self.spin), math.sin(self.spin)
            self.vx, self.vy = self.vx * c - self.vy * s, self.vx * s + self.vy * c
        if self.accel:
            sp = math.hypot(self.vx, self.vy) or 1.0
            k = min(3.0, sp + self.accel) / sp
            self.vx, self.vy = self.vx * k, self.vy * k
        super().update(game)

    def draw(self, surf, ox=0, oy=0):                # (flat: the 3D layer normally draws it)
        c = (round(self.x) + self.r + ox, round(self.y) + self.r + oy)
        pygame.draw.circle(surf, self.col, c, self.r)
        pygame.draw.circle(surf, (255, 255, 255), c, max(1, self.r // 2))


class Warn:
    """A warning on the floor before a boss's attack arrives: a red ring that fills in where something
    will land, or a line along the way a boss is about to dash or fire. Its boss can move it."""

    def __init__(self, x, y, r=12, life=40, x1=None, y1=None, col=(255, 70, 60)):
        self.x, self.y, self.r, self.life = x, y, r, life
        self.x1, self.y1, self.col = x1, y1, col
        self.t = 0
        self.dead = False

    def update(self, game):
        self.t += 1
        if self.t >= self.life:
            self.dead = True

    def draw(self, surf, ox=0, oy=0):
        if (self.t // 4) % 2:
            return
        if self.x1 is None:
            pygame.draw.circle(surf, self.col, (round(self.x) + ox, round(self.y) + oy), round(self.r), 1)
        else:
            pygame.draw.line(surf, self.col, (round(self.x) + ox, round(self.y) + oy),
                             (round(self.x1) + ox, round(self.y1) + oy))


class Strike:
    """Something crashing down from above onto a warned spot: a meteor ('rock'), lightning ('bolt'),
    a gob of lava ('fire') or an icicle ('ice'). It hurts Octo if he's still in the ring when it lands."""
    FALL = 18                                   # frames after landing that the blast is shown

    def __init__(self, x, y, delay, kind, r=13, dmg=1, loud=True):
        self.x, self.y, self.delay, self.kind, self.r, self.dmg, self.loud = x, y, delay, kind, r, dmg, loud
        self.t = 0
        self.dead = False

    def update(self, game):
        self.t += 1
        if self.t == self.delay:
            p = game.player
            if math.hypot(p.rect.centerx - self.x, p.rect.centery - self.y) < self.r + 3:
                p.hurt(game, self.dmg, (self.x, self.y - 4))
            game.shake = max(game.shake, 3)
            if self.loud:
                sound.play({'bolt': 'zap', 'ice': 'ice', 'fire': 'boom'}.get(self.kind, 'shut'))
            col = {'bolt': (200, 220, 255), 'ice': (200, 240, 255), 'fire': (255, 150, 60)}.get(self.kind, (230, 200, 160))
            for i in range(8):
                a = i / 8 * math.tau + random.uniform(0, 0.4)
                game.effects.append(Particle(self.x, self.y, math.cos(a) * 1.8, math.sin(a) * 1.8 - 0.6, col, 16, 0.08))
        if self.t > self.delay + self.FALL:
            self.dead = True

    def draw(self, surf, ox=0, oy=0):
        if self.t < self.delay:
            pygame.draw.circle(surf, (255, 70, 60), (round(self.x) + ox, round(self.y) + oy), self.r, 1)


class Shock:
    """The ring that races out along the floor when a boss lands or bursts (it's the orbs that hurt)."""

    def __init__(self, x, y, col, size=1.0):
        self.x, self.y, self.col, self.size = x, y, col, size
        self.t = 0
        self.dead = False

    def update(self, game):
        self.t += 1
        if self.t >= 22:
            self.dead = True

    def draw(self, surf, ox=0, oy=0):
        pygame.draw.circle(surf, self.col, (round(self.x) + ox, round(self.y) + oy), round(4 + self.t * 3 * self.size), 1)


class BossAura:
    """The glow on the floor under a mini-boss: its own colour while it's calm, red once it's furious,
    swelling while it gathers itself for a big attack."""

    def __init__(self, boss):
        self.boss = boss
        self.t = 0
        self.dead = False

    def update(self, game):
        self.t += 1
        if self.boss.dead or self.boss not in game.enemies:
            self.dead = True

    def draw(self, surf, ox=0, oy=0):
        pass


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


class JetInk:
    """A blob of ink squirted out behind Octo as he jets, in his ink jet colour. It drifts back
    and shrinks away."""

    def __init__(self, x, y, vx, vy, color=0, life=18):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.color, self.life, self.life0 = color, life, life
        self.dead = False

    def update(self, game):
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.9
        self.vy *= 0.9
        self.life -= 1
        if self.life <= 0:
            self.dead = True

    def radius(self):
        return 1.2 + 2.3 * self.life / self.life0

    def draw(self, surf, ox=0, oy=0):
        pygame.draw.circle(surf, style.dash_rgb(self.color, self.life), (round(self.x) + ox, round(self.y) + oy),
                           max(1, round(self.radius())))


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
    """Hit an enemy with a shaped attack and apply its element (mega attacks carry two)."""
    elems = elem if isinstance(elem, tuple) else (elem,)
    if 'heavy' in elems:
        dmg += 1
    if not e.hit(game, dmg, kind, src):
        return
    for el in elems:
        _element_effect(game, e, el, src)


def _element_effect(game, e, elem, src):
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
    elif elem == 'poison' and not e.dead:
        e.poison = 200
    elif elem == 'slow' and not e.dead:
        e.slow = 120 if boss else 240
    elif elem == 'push' and not e.dead and not boss:
        d = math.hypot(cx - src[0], cy - src[1]) or 1
        for _ in range(10):
            e.move((cx - src[0]) / d * 2.4, (cy - src[1]) / d * 2.4, game.level)
    elif elem == 'confuse' and not e.dead:
        e.dizzy = 60 if boss else 200
    elif elem == 'weaken' and not e.dead:
        e.weak = 300
    elif elem == 'loot' and random.random() < 0.4:
        it = Pickup(cx - 4, cy - 4, 'pearl', life=420)
        game.pickups.append(it)
    elif elem == 'corrupt' and not e.dead:
        corrupt(e)
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


class Beam:
    """Beam: a piercing line of light straight out from Octo, hitting every enemy along it."""

    def __init__(self, cx, cy, dx, dy, elem=None):
        self.x0, self.y0 = cx, cy
        self.dx, self.dy = dx, dy
        self.t = 0
        self.elem = elem
        self.col = forms.ELEMENTS.get(elem, (0, 0, (220, 240, 255)))[2]
        self.dead = False
        self.length = 0
        self.hit = set()

    def update(self, game):
        self.t += 1
        if self.t == 1:
            # find where the beam stops: a wall, or 220px away
            for step in range(0, 220, 4):
                x, y = self.x0 + self.dx * step, self.y0 + self.dy * step
                if game.level.blocked(pygame.Rect(x - 1, y - 1, 2, 2), 'shot'):
                    break
                self.length = step
        if self.t <= 6:
            for e in list(game.enemies):
                if not e.active or e in self.hit:
                    continue
                ex, ey = e.rect.center
                along = (ex - self.x0) * self.dx + (ey - self.y0) * self.dy
                off = abs((ex - self.x0) * self.dy - (ey - self.y0) * self.dx)
                if 0 <= along <= self.length + 6 and off < 10:
                    self.hit.add(e)
                    strike(game, e, 2, 'beam', (self.x0, self.y0), self.elem)
        if self.t > 14:
            self.dead = True

    def draw(self, surf, ox=0, oy=0):
        x0, y0 = self.x0 + ox, self.y0 + oy
        x1, y1 = x0 + self.dx * self.length, y0 + self.dy * self.length
        w = max(1, 6 - self.t // 3)
        pygame.draw.line(surf, self.col, (x0, y0), (x1, y1), w + 2)
        pygame.draw.line(surf, (255, 255, 255), (x0, y0), (x1, y1), max(1, w - 2))


class Orb(Entity):
    """Orbs: three glowing orbs that circle Octo for a few seconds."""
    hb = (0, 0, 10, 10)

    def __init__(self, owner, ang, elem=None):
        super().__init__(owner.x, owner.y)
        self.owner, self.ang, self.elem = owner, ang, elem
        self.life = 300
        self.col = forms.ELEMENTS.get(elem, (0, 0, (255, 160, 80)))[2]

    def update(self, game):
        self.life -= 1
        self.ang += 0.09
        cx, cy = self.owner.rect.center
        self.x = cx + math.cos(self.ang) * 22 - 5
        self.y = cy + math.sin(self.ang) * 22 - 5
        if self.life <= 0:
            self.dead = True
            return
        for e in list(game.enemies):
            if e.active and not e.hurt_t and self.rect.colliderect(e.rect):
                strike(game, e, 1, 'orb', self.owner.rect.center, self.elem)

    def draw(self, surf, ox=0, oy=0):
        x, y = round(self.x) + ox + 5, round(self.y) + oy + 5
        _glow(surf, x, y, 8, self.col, 60)
        pygame.draw.circle(surf, self.col, (x, y), 4)
        pygame.draw.circle(surf, (255, 255, 240), (x - 1, y - 1), 1)


class RainCloud(Entity):
    """Rain: a little cloud drifts over Octo and rains on the nearest enemies."""
    hb = (0, 0, 24, 10)

    def __init__(self, owner, elem=None):
        super().__init__(owner.x - 4, owner.y - 22)
        self.owner, self.elem = owner, elem
        self.life = 360
        self.drops = []
        self.col = forms.ELEMENTS.get(elem, (0, 0, (150, 200, 255)))[2]

    def update(self, game):
        self.life -= 1
        cx, cy = self.owner.rect.center
        self.x += (cx - 12 - self.x) * 0.1
        self.y += (cy - 34 - self.y) * 0.1
        if self.life <= 0:
            self.dead = True
            return
        if self.life % 20 == 0:
            target = game.nearest_enemy((cx, cy), 90)
            if target:
                tx, ty = target.rect.center
                self.drops.append([tx + random.uniform(-4, 4), ty - 40, ty, target])
        for d in self.drops:
            d[1] += 5
        for d in [d for d in self.drops if d[1] >= d[2]]:
            self.drops.remove(d)
            e = d[3]
            if e.active and not e.dead:
                e.hurt_t = 0
                strike(game, e, 1, 'rain', (d[0], d[1] - 10), self.elem)
            game.splat((d[0], d[2]), self.col)

    def draw(self, surf, ox=0, oy=0):
        x, y = round(self.x) + ox, round(self.y) + oy
        for dx, r in ((5, 5), (12, 7), (19, 5)):
            pygame.draw.circle(surf, (120, 130, 160), (x + dx, y + 6), r)
            pygame.draw.circle(surf, (230, 235, 250), (x + dx, y + 5), r - 1)
        for d in self.drops:
            pygame.draw.line(surf, self.col, (d[0] + ox, d[1] + oy), (d[0] + ox, d[1] + oy + 4))


class Nova:
    """Nova: a ring of force that rings out around Octo. Magnety's version also drags things in."""

    def __init__(self, cx, cy, elem=None, max_r=80, dmg=2):
        self.x, self.y = cx, cy
        self.r = 6
        self.max_r, self.dmg = max_r, dmg
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
                        strike(game, e, self.dmg, 'nova', (self.x, self.y), self.elem)
        if self.r > self.max_r:
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
# The eight newer fused attacks, and Corrupted's glitch wave
# ===========================================================================
GLITCH_COLS = ((255, 50, 220), (60, 240, 255), (255, 255, 255))


def corrupt(e, frames=240):
    """Corrupt an enemy: it glitches, and every so often the glitch hurts it (Enemy.update), and
    when it's beaten the corruption spreads (Enemy.die)."""
    if e.active:
        e.corrupt = max(getattr(e, 'corrupt', 0), frames)


class GeyserSpout(Entity):
    """Geyser: water bubbles up under an enemy (following it about), then a spout bursts up out of
    the sea floor beneath it."""
    WAIT, BURST = 16, 20

    def __init__(self, target, x, y, delay=0, elem=None):
        super().__init__(x, y)
        self.target = target
        self.t = -delay
        self.elem = elem
        self.col = forms.ELEMENTS.get(elem, (0, 0, (170, 225, 255)))[2]

    @property
    def rect(self):
        return pygame.Rect(round(self.x) - 11, round(self.y) - 14, 22, 20)

    def update(self, game):
        self.t += 1
        e = self.target
        if 0 <= self.t < self.WAIT and e is not None and e.active:
            self.x, self.y = e.rect.centerx, e.rect.bottom - 2
        if self.t == self.WAIT:
            sound.play('whoosh')
            for o in list(game.enemies):
                if o.active and self.rect.colliderect(o.rect):
                    strike(game, o, 2, 'geyser', (self.x, self.y + 8), self.elem)
            for i in range(10):
                a = i / 10 * math.tau
                game.effects.append(Particle(self.x, self.y - 6, math.cos(a) * 1.4, math.sin(a) * 0.7 - 1.2,
                                             (220, 245, 255), 20, grav=0.08))
        if self.t > self.WAIT + self.BURST:
            self.dead = True

    def draw(self, surf, ox=0, oy=0):
        if self.t < 0:
            return
        x, y = round(self.x) + ox, round(self.y) + oy
        if self.t < self.WAIT:
            r = 3 + self.t * 0.4
            pygame.draw.ellipse(surf, (200, 240, 255), (x - r, y - r * 0.5, r * 2, r), 1)
            return
        k = min(1.0, (self.t - self.WAIT) / self.BURST)
        h = int(28 * math.sin(k * math.pi))
        pygame.draw.rect(surf, (150, 210, 250), (x - 3, y - h, 6, h))
        pygame.draw.circle(surf, (240, 250, 255), (x, y - h), 4)


class Harpoon(Entity):
    """Harpoon: flies straight out on its line, spears the first enemy it meets and reels it in to
    Octo, dazed (a boss is too heavy: the harpoon just bites and comes back)."""
    hb = (0, 0, 6, 6)
    who = 'shot'
    REACH, SPEED = 150, 5.0

    def __init__(self, owner, dx, dy, elem=None):
        cx, cy = owner.rect.center
        super().__init__(cx - 3 + dx * 6, cy - 3 + dy * 6)
        self.owner = owner
        self.dx, self.dy = dx, dy
        self.t = 0
        self.caught = None
        self.back = False
        self.elem = elem
        self.col = forms.ELEMENTS.get(elem, (0, 0, (230, 230, 240)))[2]

    def update(self, game):
        self.t += 1
        ox, oy = self.owner.rect.center
        cx, cy = self.rect.center
        if self.t > 120:
            self.dead = True
            return
        if self.caught is not None:
            e = self.caught
            if not e.active:
                self.caught, self.back = None, True
                return
            ex, ey = e.rect.center
            d = math.hypot(ox - ex, oy - ey) or 1
            if d < 22 or self.t > 90:
                e.frozen = max(e.frozen, 45)               # it lands at Octo's feet, dazed
                game.effects.append(Daze(e))
                self.dead = True
                return
            moved = False
            for _ in range(4):
                moved = bool(e.move((ox - ex) / d, (oy - ey) / d, game.level)) or moved
            e.frozen = max(e.frozen, 2)
            self.x, self.y = e.rect.centerx - 3, e.rect.centery - 3
            if not moved:                                  # stuck behind something: let it go
                self.caught, self.back = None, True
            return
        if self.back:
            d = math.hypot(ox - cx, oy - cy)
            if d < 8:
                self.dead = True
                return
            self.x += (ox - cx) / d * 6.5
            self.y += (oy - cy) / d * 6.5
            return
        self.x += self.dx * self.SPEED
        self.y += self.dy * self.SPEED
        if game.level.blocked(self.rect, 'shot') or math.hypot(cx - ox, cy - oy) > self.REACH:
            self.back = True
            return
        for e in list(game.enemies):
            if e.active and self.rect.inflate(4, 4).colliderect(e.rect):
                strike(game, e, 2, 'harpoon', self.rect.center, self.elem)
                if e.active and not getattr(e, 'boss', False):
                    self.caught = e
                else:
                    self.back = True
                return

    def draw(self, surf, ox=0, oy=0):
        px, py = self.owner.rect.center
        cx, cy = self.rect.center
        pygame.draw.line(surf, (90, 70, 50), (px + ox, py + oy), (cx + ox, cy + oy))
        pygame.draw.circle(surf, (230, 230, 240), (cx + ox, cy + oy), 2)


class SawBlade(Entity):
    """Saw: a spinning saw blade that ricochets off the walls, cutting every enemy it passes (each
    one again after a moment)."""
    hb = (0, 0, 10, 10)
    who = 'shot'
    BOUNCES, LIFE = 4, 150

    def __init__(self, cx, cy, dx, dy, elem=None):
        super().__init__(cx - 5 + dx * 8, cy - 5 + dy * 8)
        self.vx, self.vy = dx * 3.4, dy * 3.4
        self.t = 0
        self.bounces = 0
        self.cool = {}
        self.elem = elem
        self.col = forms.ELEMENTS.get(elem, (0, 0, (220, 226, 240)))[2]

    def update(self, game):
        self.t += 1
        wall = False
        self.x += self.vx
        if game.level.blocked(self.rect, 'shot'):
            self.x -= self.vx
            self.vx = -self.vx
            wall = True
        self.y += self.vy
        if game.level.blocked(self.rect, 'shot'):
            self.y -= self.vy
            self.vy = -self.vy
            wall = True
        if wall:
            self.bounces += 1
            sound.play('tink')
            game.spark(self.rect.center)
        if self.bounces > self.BOUNCES or self.t > self.LIFE:
            self.dead = True
            return
        for e in list(game.enemies):
            if e.active and self.cool.get(e, 0) <= self.t and self.rect.inflate(2, 2).colliderect(e.rect):
                self.cool[e] = self.t + 20
                strike(game, e, 2, 'saw', self.rect.center, self.elem)

    def draw(self, surf, ox=0, oy=0):
        cx, cy = self.rect.centerx + ox, self.rect.centery + oy
        a = self.t * 0.7
        pygame.draw.circle(surf, (150, 156, 176), (cx, cy), 5)
        for i in range(6):
            b = a + i / 6 * math.tau
            surf.set_at((int(cx + math.cos(b) * 6), int(cy + math.sin(b) * 6)), (240, 244, 255))
        pygame.draw.circle(surf, self.col, (cx, cy), 2)


class SprayDrop(Entity):
    """Spray: one pellet of a rapid stream of ink, squirted from wherever Octo is when its turn comes."""
    hb = (0, 0, 4, 4)
    who = 'shot'

    def __init__(self, owner, ang, wait, i=0, elem=None):
        super().__init__(-100, -100)
        self.owner, self.ang, self.wait, self.i = owner, ang, wait, i
        self.life = 32
        self.live = False
        self.elem = elem
        self.col = forms.ELEMENTS.get(elem, (0, 0, (90, 70, 200)))[2]

    def update(self, game):
        if not self.live:
            self.wait -= 1
            if self.wait > 0:
                return
            cx, cy = self.owner.rect.center
            self.x, self.y = cx - 2 + math.cos(self.ang) * 9, cy - 2 + math.sin(self.ang) * 9
            self.live = True
            if self.i % 3 == 2:
                sound.play('shoot')
        self.x += math.cos(self.ang) * 4.8
        self.y += math.sin(self.ang) * 4.8
        self.life -= 1
        if self.life <= 0 or game.level.blocked(self.rect, 'shot'):
            self.dead = True
            return
        for e in list(game.enemies):
            if e.active and self.rect.inflate(4, 4).colliderect(e.rect):
                strike(game, e, 2, 'spray', self.rect.center, self.elem)
                self.dead = True
                return

    def draw(self, surf, ox=0, oy=0):
        if not self.live:
            return
        cx, cy = self.rect.centerx + ox, self.rect.centery + oy
        pygame.draw.circle(surf, self.col, (cx, cy), 2)
        surf.set_at((cx - 1, cy - 1), (255, 255, 255))


class SonarBlast:
    """Sonar: three waves of sound sweep out in a cone ahead of Octo. Each enemy in the cone is hit
    once, by the first wave to reach it."""
    HALF, REACH, SPEED, GAP = 0.6, 104, 4.4, 20

    def __init__(self, x, y, ang, elem=None):
        self.x, self.y, self.ang = x, y, ang
        self.t = 0
        self.hit = set()
        self.dead = False
        self.elem = elem
        self.col = forms.ELEMENTS.get(elem, (0, 0, (170, 230, 255)))[2]

    def radii(self):
        return [r for r in (self.t * self.SPEED - i * self.GAP for i in range(3)) if 8 <= r <= self.REACH]

    def update(self, game):
        self.t += 1
        rs = self.radii()
        for e in list(game.enemies):
            if not e.active or e in self.hit:
                continue
            ex, ey = e.rect.center
            d = math.hypot(ex - self.x, ey - self.y)
            rel = (math.atan2(ey - self.y, ex - self.x) - self.ang + math.pi) % math.tau - math.pi
            if abs(rel) < self.HALF + 8 / max(d, 8) and any(abs(d - r) < 9 for r in rs):
                self.hit.add(e)
                strike(game, e, 2, 'sonar', (self.x, self.y), self.elem)
        if self.t * self.SPEED - 2 * self.GAP > self.REACH:
            self.dead = True

    def draw(self, surf, ox=0, oy=0):
        for r in self.radii():
            pts = [(self.x + ox + math.cos(self.ang + a) * r, self.y + oy + math.sin(self.ang + a) * r)
                   for a in (-self.HALF + i * self.HALF / 4 for i in range(9))]
            pygame.draw.lines(surf, self.col, False, pts, 2)


class MortarShell:
    """Mortar: a big fizzing bomb lobbed high over walls; it bursts on whatever is where it lands
    (a red ring on the floor shows where), cracking rock like a bomb."""
    FLIGHT, RADIUS, HIGH = 34, 30, 44

    def __init__(self, x0, y0, x1, y1, elem=None):
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1
        self.x, self.y, self.z = x0, y0, 0.0
        self.t = 0
        self.dead = False
        self.elem = elem
        self.col = forms.ELEMENTS.get(elem, (0, 0, (255, 170, 80)))[2]

    @property
    def rect(self):
        return pygame.Rect(round(self.x) - 5, round(self.y - self.z) - 5, 10, 10)

    def update(self, game):
        self.t += 1
        k = self.t / self.FLIGHT
        self.x = self.x0 + (self.x1 - self.x0) * k
        self.y = self.y0 + (self.y1 - self.y0) * k
        self.z = self.HIGH * 4 * k * (1 - k)
        if self.t < self.FLIGHT:
            return
        self.dead = True
        sound.play('boom')
        game.shake = max(game.shake, 6)
        game.blast_tiles(self.x1, self.y1, 18)
        for e in list(game.enemies):
            if e.active and math.hypot(e.rect.centerx - self.x1, e.rect.centery - self.y1) < self.RADIUS:
                strike(game, e, 3, 'mortar', (self.x1, self.y1), self.elem)
        game.effects.append(fx.ImpactRing(self.x1, self.y1, big=True, col=self.col))
        for i in range(14):
            a = i / 14 * math.tau
            game.effects.append(Particle(self.x1, self.y1, math.cos(a) * 2.2, math.sin(a) * 2.2, self.col, 20, size=2))

    def draw(self, surf, ox=0, oy=0):
        tx, ty = round(self.x1) + ox, round(self.y1) + oy
        pygame.draw.circle(surf, (255, 80, 60), (tx, ty), max(2, int(self.RADIUS * min(1, self.t / self.FLIGHT))), 1)
        x, y = round(self.x) + ox, round(self.y) + oy
        pygame.draw.ellipse(surf, (0, 0, 20), (x - 4, y - 2, 8, 4))
        pygame.draw.circle(surf, (40, 40, 50), (x, round(y - self.z)), 5)
        pygame.draw.circle(surf, self.col, (x + 2, round(y - self.z) - 5), 1)


class SwarmFish(Entity):
    """Swarm: one of a school of little fish that dart round the nearest enemies, nibbling them (the
    school spreads out: no more than three go after one enemy if there are others)."""
    hb = (0, 0, 5, 4)
    who = 'shot'
    LIFE = 210

    def __init__(self, owner, i, elem=None):
        cx, cy = owner.rect.center
        super().__init__(cx - 2, cy - 2)
        self.owner, self.i = owner, i
        a = i / 6 * math.tau
        self.vx, self.vy = math.cos(a) * 2.4, math.sin(a) * 2.4
        self.life = self.LIFE
        self.target = None
        self.bite = 12 + i * 3
        self.elem = elem
        self.col = forms.ELEMENTS.get(elem, (0, 0, (255, 160, 80)))[2]

    def update(self, game):
        self.life -= 1
        if self.life <= 0:
            self.dead = True
            return
        if self.bite:
            self.bite -= 1
        cx, cy = self.rect.center
        if self.target is not None and not self.target.active:
            self.target = None
        if self.target is None and self.life % 6 == self.i % 6:
            self.target = self._pick(game, cx, cy)
        if self.target is not None:
            tx, ty = self.target.rect.center
            a = self.life * 0.16 + self.i * 1.05
            gx, gy = tx + math.cos(a) * 8, ty + math.sin(a) * 6
        else:
            ox, oy = self.owner.rect.center
            a = self.life * 0.09 + self.i * 1.05
            gx, gy = ox + math.cos(a) * 16, oy + math.sin(a) * 11
        dx, dy = gx - cx, gy - cy
        d = math.hypot(dx, dy) or 1
        self.vx += (dx / d * 2.8 - self.vx) * 0.2
        self.vy += (dy / d * 2.8 - self.vy) * 0.2
        self.x += self.vx
        self.y += self.vy
        e = self.target
        if e is not None and not self.bite and self.rect.inflate(6, 6).colliderect(e.rect):
            self.bite = 26
            strike(game, e, 1, 'swarm', self.rect.center, self.elem)

    def _pick(self, game, cx, cy):
        busy = {}
        for s in game.shots:
            if isinstance(s, SwarmFish) and s.target is not None:
                busy[s.target] = busy.get(s.target, 0) + 1
        best = None
        for e in game.enemies:
            if e.active and game.view_rect.colliderect(e.rect):
                d = math.hypot(e.rect.centerx - cx, e.rect.centery - cy) + (60 if busy.get(e, 0) >= 3 else 0)
                if d < 220 and (best is None or d < best[0]):
                    best = (d, e)
        return best[1] if best else None

    def draw(self, surf, ox=0, oy=0):
        cx, cy = self.rect.centerx + ox, self.rect.centery + oy
        f = 1 if self.vx >= 0 else -1
        pygame.draw.ellipse(surf, self.col, (cx - 3, cy - 2, 6, 4))
        pygame.draw.polygon(surf, self.col, [(cx - 3 * f, cy), (cx - 5 * f, cy - 2), (cx - 5 * f, cy + 2)])
        surf.set_at((cx + f, cy - 1), (20, 20, 30))


class GrabTentacle:
    """Tentacles: a tentacle bursts up out of the sea floor beside an enemy, wraps round it and holds
    it tight for a moment (a boss only for a blink)."""
    RISE, HOLD, SINK = 9, 50, 8

    def __init__(self, target, x, y, delay=0, elem=None):
        self.target = target
        self.x, self.y = x, y
        self.t = -delay
        self.dead = False
        self.side = random.choice((-1, 1))
        self.elem = elem
        self.col = forms.ELEMENTS.get(elem, (0, 0, (255, 200, 240)))[2]

    @property
    def rect(self):
        return pygame.Rect(round(self.x) - 8, round(self.y) - 14, 16, 16)

    def height(self):
        """How far up it is (0 to 1): rising, holding, then sinking back down."""
        if self.t < 0:
            return 0.0
        if self.t <= self.RISE:
            return self.t / self.RISE
        return max(0.0, min(1.0, 1 - (self.t - self.RISE - self.HOLD) / self.SINK))

    def update(self, game):
        self.t += 1
        e = self.target
        if e is not None and not e.active:
            self.target = e = None
        if e is not None and self.t <= self.RISE:
            self.x, self.y = e.rect.centerx, e.rect.bottom
        if self.t == self.RISE:
            sound.play('slap')
            for o in ([e] if e is not None else [o for o in game.enemies if o.active and self.rect.colliderect(o.rect)]):
                strike(game, o, 2, 'grab', (self.x, self.y + 6), self.elem)
                if o.active:
                    o.frozen = max(o.frozen, 18 if getattr(o, 'boss', False) else self.HOLD)
        if self.t > self.RISE + self.HOLD + self.SINK:
            self.dead = True

    def draw(self, surf, ox=0, oy=0):
        h = int(16 * self.height())
        x, y = round(self.x) + ox, round(self.y) + oy
        for i in range(0, h, 2):
            pygame.draw.circle(surf, (200, 90, 190), (x + self.side * (5 - i // 3), y - i), max(1, 3 - i // 6))


class GlitchWave:
    """Corrupted Octo's glitch wave: a jagged square of static spreads out and corrupts every enemy
    it passes. A small one (no damage) carries the corruption on when a corrupted enemy is beaten."""

    def __init__(self, cx, cy, max_r=88, dmg=2):
        self.x, self.y = cx, cy
        self.r = 4.0
        self.max_r, self.dmg = max_r, dmg
        self.hit = set()
        self.t = 0
        self.dead = False

    def update(self, game):
        self.t += 1
        self.r += 3.6
        for e in list(game.enemies):
            if e.active and e not in self.hit:
                ex, ey = e.rect.center
                if max(abs(ex - self.x), abs(ey - self.y)) < self.r + 6:      # a square wave
                    self.hit.add(e)
                    if self.dmg:
                        strike(game, e, self.dmg, 'glitch', (self.x, self.y), 'corrupt')
                    else:
                        corrupt(e)
        if self.r > self.max_r:
            self.dead = True

    def draw(self, surf, ox=0, oy=0):
        rnd = random.Random(self.t * 7 + int(self.x))
        r = int(self.r)
        x, y = round(self.x) + ox, round(self.y) + oy
        for col, dx in ((GLITCH_COLS[0], -1), (GLITCH_COLS[1], 1)):
            pygame.draw.rect(surf, col, (x - r + dx + rnd.randint(-1, 1), y - r + rnd.randint(-1, 1), 2 * r, 2 * r), 1)


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


class MegaMachine(FusionMachine):
    """The secret Mega Machine: asleep under moss until Octo has made every fusion."""

    def update(self, game):
        self.t += 1
        if self.t % 30 == 1:
            self.awake = game.mega_awake()

    def draw(self, surf, ox=0, oy=0):
        import forms
        game_awake = getattr(self, 'awake', False)
        x, y = round(self.x) + ox, round(self.y) + oy
        t = self.t
        body = (70, 40, 110) if game_awake else (60, 62, 58)
        pygame.draw.rect(surf, (20, 14, 30), (x, y + 23, 32, 9))
        pygame.draw.rect(surf, body, (x + 2, y + 6, 28, 19))
        pygame.draw.rect(surf, (200, 160, 60) if game_awake else (90, 92, 86), (x + 2, y + 6, 28, 19), 1)
        for i in range(3):                      # three tanks
            tx = x + 4 + i * 9
            pygame.draw.rect(surf, (10, 10, 20), (tx, y - 2, 6, 12))
            if game_awake:
                lvl = 5 + int(math.sin(t * 0.06 + i * 2) * 2)
                pygame.draw.rect(surf, ((255, 120, 200), (255, 215, 80), (120, 220, 255))[i],
                                 (tx + 1, y + 10 - lvl, 4, lvl))
            pygame.draw.rect(surf, (200, 210, 230) if game_awake else (110, 110, 110), (tx, y - 2, 6, 12), 1)
        if game_awake:
            r = 4 + (t // 6) % 3
            pygame.draw.circle(surf, (255, 215, 80), (x + 16, y + 17), r)
            pygame.draw.circle(surf, (255, 255, 230), (x + 16, y + 17), 2)
        else:                                   # asleep: moss and a faint ember of light
            for mx, my in ((5, 8), (12, 20), (22, 9), (27, 18), (18, 13)):
                pygame.draw.circle(surf, (60, 110, 60), (x + mx, y + my), 3)
            if (t // 40) % 2:
                surf.set_at((x + 16, y + 17), (255, 200, 120))
