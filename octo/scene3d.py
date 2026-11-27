"""The world's 3D layer.

Octo as a pixel-style 3D figure, the 3D buildings, the Octo Temple pyramid and the trial
portals are drawn sharp on a hi-res layer, in depth order, over the pixel-art ground: things
behind a building disappear behind it, and Octo walks up the pyramid's stairs onto its top.
Also: the animation of Octo being pulled into a trial portal, and popping out of it.

Scene3D is mixed into Game.
"""
import math
import random
import time

import pygame

import attacks3d
import gfx
import props3d
import sound
import voxel
import world
from settings import HI, HUD_H, PLAY_H, PLAY_W, TILE

FACING_YAW = {'down': 0.22, 'up': math.pi + 0.22, 'left': 0.62, 'right': -0.62}
FOLK = ('Citizen', 'Shelly', 'Hermie', 'LegendStatue')               # the friendlies drawn as 3D figures
TURTLE_TURN = {'up': 0, 'left': 90, 'down': 180, 'right': -90}      # turtles are drawn from above, head up
_folk = {}                                                           # turned sprites and their cube models


def _figure(key, spr, depth=4.0, ball=True, yaw=0.25):
    """A small sprite as a cube figure, like Pebble: (render, feet anchor), cached under key."""
    m = _folk.get(key)
    if m is None:
        m = _folk[key] = voxel.VoxelModel(voxel._profile_cells(spr, None, depth=depth, ball=ball))
    return voxel.cached(key, m, HI, yaw, 0.6)


def _turned(img, ang):
    key = ('turn', id(img), ang)
    s = _folk.get(key)
    if s is None:
        s = _folk[key] = pygame.transform.rotate(img, ang) if ang else img
    return s


def _turtle(img, facing):
    """A turtle (seen from above, head up in its sprite) turned to face the way it's going."""
    ang = TURTLE_TURN.get(facing, 0)
    return _figure(('turtle', id(img), ang), _turned(img, ang))


class _Recorder(pygame.Surface):
    """Stands in for the screen while an enemy draws itself: the sprites it stamps are noted, to be
    drawn as 3D figures; anything else (its health bar, a boss's crown, a trap bubble's ring) lands
    on this surface, to go over the 3D layer."""

    def __init__(self, size):
        super().__init__(size, pygame.SRCALPHA)
        self.blits = []

    def blit(self, src, dest, area=None, special_flags=0):
        if area is None and not special_flags:
            self.blits.append((src, (int(dest[0]), int(dest[1]))))
            return pygame.Rect(dest[0], dest[1], *src.get_size())
        return super().blit(src, dest, area, special_flags)


_ENEMY_PAD = 48                  # where an enemy's (x, y) lands on the recorder
_rec = []
_shapes = {}                     # enemy sprite (by content) -> its cube model, or None if see-through
_built = [0.0, -1]               # time spent making new enemy figures this frame, and which frame


def _enemy_figure(src, frame):
    """The 3D cube figure for an enemy's sprite, as long as it isn't see-through glow."""
    key = (src.get_size(), hash(pygame.image.tobytes(src, 'RGBA')))
    if key not in _shapes or ('enemy', key) not in voxel._renders:
        if _built[1] != frame:
            _built[:] = [0.0, frame]
        if _built[0] > 0.005:                 # about 5 ms of new figures a frame: the rest wait (shown flat)
            return None, False
        t0 = time.perf_counter()
        if key not in _shapes:
            w, h = src.get_size()
            cells = voxel._profile_cells(src, None, depth=max(2.5, min(6.0, min(w, h) * 0.26)))
            if len(_shapes) > 500:
                _shapes.clear()
            _shapes[key] = voxel.VoxelModel(cells) if cells else None
        m = _shapes[key]
        out = voxel.cached(('enemy', key), m, HI, 0.25, 0.6) if m is not None else None
        _built[0] += time.perf_counter() - t0
        return out, True
    m = _shapes[key]
    if m is None:
        return None, True
    return voxel.cached(('enemy', key), m, HI, 0.25, 0.6), True


def _plinth():
    s = _folk.get('plinth_spr')
    if s is None:
        s = _folk['plinth_spr'] = pygame.Surface((20, 9), pygame.SRCALPHA)
        s.fill((90, 80, 110))
        pygame.draw.rect(s, (200, 190, 220), (1, 0, 18, 7))
        pygame.draw.line(s, (255, 255, 255), (1, 0), (18, 0))
    return s
PORTAL_LEN = 66                  # frames from stepping in to arriving in the trial
ARRIVE_LEN = 34


def _ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def _ease_in(x):
    x = max(0.0, min(1.0, x))
    return x * x


class Scene3D:
    def scene_setup(self):
        self.p_yaw = FACING_YAW['down']
        self.portal_anim = None
        self.arrive_t = 0
        self.zoom = None

    # ---- where things are ------------------------------------------------
    def player_in_3d(self):
        p = self.player
        return p is not None and not (p.tumble or (p.in_sky and p.sphere > 0))

    def ground_height(self, ent):
        return props3d.height_at(ent.rect.centerx, ent.rect.bottom - 1)

    def pyramid_in_view(self):
        x0, y0 = props3d.PYRAMID[:2]
        return self.view_rect.colliderect((x0 * TILE, y0 * TILE, 128, 128))

    def lift(self, thing):
        """How high the pyramid holds up a shot or a spark: 0 down on flat ground."""
        r = getattr(thing, 'rect', None)
        if isinstance(r, pygame.Rect):
            return props3d.height_at(r.centerx, r.bottom - 1)
        x, y = getattr(thing, 'x', None), getattr(thing, 'y', None)
        return props3d.height_at(x, y) if x is not None and y is not None else 0.0

    def draw_lifted(self, ps, ox, oy):
        """Flat things (score pop-ups, motes) up on the pyramid. The 3D pyramid would cover them in
        the flat layer, so they're drawn over it instead, raised to the height they're at. (Shots and
        sparks are 3D themselves: attacks3d.)"""
        self.draw_slime_trail(ps, ox, oy, lifted=True)
        for thing in self.shots + self.effects:
            if attacks3d.handles(thing):
                continue
            h = self.lift(thing)
            if h > 0:
                thing.draw(ps, round(ox - props3d.KX * h), round(oy - props3d.KZ * h))

    def _hr(self, wx, wy, shake):
        cx, cy = self.cam
        return (wx - cx + shake[0]) * HI, (wy - cy + shake[1] + HUD_H) * HI

    # ---- drawing -------------------------------------------------------------
    def draw_world3d(self, hr, shake=(0, 0)):
        hr.set_clip(pygame.Rect(0, HUD_H * HI, PLAY_W * HI, PLAY_H * HI))
        view = self.view_rect.inflate(64, 64)
        view.height += 120
        items = []
        pyr_base = None
        for prop in props3d.PROPS:
            if view.colliderect(prop.rect()):
                items.append((prop.base, 0, prop))
                if prop.key == 'pyramid':
                    pyr_base = prop.base
                elif prop.key == 'pearl_shop':                 # the wares on its counter, with prices
                    items.append((prop.base + 0.01, 0.5, 'wares'))
        p = self.player
        if self.portal_anim is not None:
            a = self.portal_anim
            items.append((a['ring'][1] + 1, 2, 'portal_octo'))
        elif self.state not in ('dying', 'sleep') and self.player_in_3d():
            h = self.ground_height(p)
            key = (pyr_base + 1) if h > 0 and pyr_base is not None else p.rect.bottom
            items.append((key, 2, 'player'))
            for k, piece in attacks3d.octo_pieces(p):         # his slap, shields and fog
                items.append(((pyr_base + 1.1) if h > 0 and pyr_base is not None else k, 3, piece))
        sn = getattr(self, 'snail', None)
        if sn is not None and self.state not in ('dying',) and self.portal_anim is None:
            h = self.ground_height(sn)
            key = (pyr_base + 1.2) if h > 0 and pyr_base is not None else sn.rect.bottom
            items.append((key, 2, 'snail'))
        for n in self.npcs:
            if getattr(n, 'hidden', False) or not view.colliderect(n.rect):
                continue
            up = self.ground_height(n) > 0 and pyr_base is not None
            if type(n).__name__ in FOLK:                      # friendly folk: 3D figures, like Octo
                items.append((pyr_base + 0.5 if up else n.rect.bottom, 4, n))
            elif up:                                          # anything else standing up on the pyramid
                items.append((pyr_base + 0.5, 1, n))
        for e in self.enemies:                                # enemies: 3D figures too
            if view.colliderect(e.rect):
                up = pyr_base is not None and self.ground_height(e) > 0
                items.append((pyr_base + 1.25 if up else e.rect.bottom, 5, e))
        for o in self.shots + self.effects:                  # every shot, ring and spark, in 3D
            if attacks3d.handles(o):
                gx, gy = attacks3d.ground(o)
                if view.collidepoint(gx, gy):
                    up = pyr_base is not None and props3d.height_at(gx, gy) > 0
                    key = pyr_base + 1.3 if up else attacks3d.sort_y(o, gy)
                    if attacks3d.halves(o):                   # a ring: its far side passes behind Octo
                        items.append((pyr_base + 0.95 if up else key - 2, 3, attacks3d.Half(o, True)))
                        items.append((key + 2, 3, attacks3d.Half(o, False)))
                    else:
                        items.append((key, 3, o))
        items.sort(key=lambda it: (it[0], it[1]))
        for _, kind, what in items:
            if kind == 0:
                self._draw_prop(hr, what, shake)
            elif what == 'player':
                self._draw_player(hr, shake)
            elif what == 'portal_octo':
                self._draw_portal_octo(hr, shake)
            elif what == 'snail':
                self._draw_snail(hr, shake)
            elif what == 'wares':
                self._draw_wares(hr, shake)
            elif kind == 3:
                attacks3d.draw(self, hr, what, shake)
            elif kind == 4:
                self._draw_folk(hr, what, shake)
            elif kind == 5:
                self._draw_enemy(hr, what, shake)
            else:
                self._draw_raised(hr, what, shake)
        hr.set_clip(None)

    HOME_KINDS = ('home', 'mail', 'wall', 'bed', 'shelf', 'tank', 'tea', 'basket', 'hats', 'lamp', 'floor')

    def _draw_prop(self, hr, prop, shake):
        if prop.kind == 'portal':
            return self._draw_portal(hr, prop, shake)
        if prop.kind in self.HOME_KINDS:
            return self.draw_home_prop(hr, prop, shake)
        img, (ax, ay) = props3d.image(prop.key, prop.builder)
        x, y = self._hr(prop.x, prop.y, shake)
        hr.blit(img, (x - ax, y - ay))
        if prop.kind == 'fire':                               # a flickering flame
            fx, fy = self._hr(prop.x + 16 - props3d.KX * 6, prop.y + 18 - props3d.KZ * 6, shake)
            for i, (c, s) in enumerate((((240, 90, 30), 1.0), ((255, 200, 60), 0.65), ((255, 250, 200), 0.35))):
                hgt = (14 + 3 * math.sin(self.t * 0.4 + i)) * s * HI
                w = 7 * s * HI
                sway = math.sin(self.t * 0.25 + i * 1.3) * 2 * HI
                pygame.draw.polygon(hr, c, [(fx - w, fy), (fx + sway * 0.5, fy - hgt), (fx + w, fy)])
        elif prop.kind == 'fountain':                         # glints on the water
            cx, cy = prop.x + 32, prop.y + 34
            for i in range(6):
                a = self.t * 0.03 + i / 6 * math.tau
                r = 14 + 6 * math.sin(self.t * 0.05 + i)
                gx, gy = self._hr(cx + math.cos(a) * r - props3d.KX * 8, cy + math.sin(a) * r * 0.8 - props3d.KZ * 8,
                                  shake)
                pygame.draw.line(hr, (220, 245, 255), (gx - HI * 2, gy), (gx + HI * 2, gy), max(1, HI // 2))

    def _portal_state(self, name):
        t = world.TRIALS[name]
        done = name in self.trials_done
        return tuple(t.get('color', (255, 255, 255))), done

    def _draw_portal(self, hr, prop, shake):
        col, done = self._portal_state(prop.data)
        key = ('portal', col, done)
        img, (ax, ay) = props3d.image(key, lambda: props3d.portal(col, done))
        x, y = self._hr(prop.x, prop.y, shake)
        # the swirling vortex inside the ring
        cx, cy = self._hr(prop.x + 8 - props3d.KX * 16, prop.y + 12.5 - props3d.KZ * 16, shake)
        if not done:
            grow = 1.0
            spin = self.t * 4
            a = self.portal_anim
            if a is not None and a['name'] == prop.data:
                grow = 1.0 + 0.35 * _ease(a['t'] / 40)
                spin = self.t * 4 + a['t'] ** 2 * 0.35
            r = int(8.5 * HI * grow)
            sw = props3d.swirl(col, max(4, r))
            rot = pygame.transform.rotozoom(sw, -spin, 1.0)
            rot = pygame.transform.smoothscale(rot, (rot.get_width(), max(2, int(rot.get_height() * props3d.KZ))))
            hr.blit(rot, (cx - rot.get_width() / 2, cy - rot.get_height() / 2))
        hr.blit(img, (x - ax, y - ay))
        if not done and (self.t // 4) % 2 == 0:              # a spark circling the ring
            ang = self.t * 0.15
            sx = cx + math.cos(ang) * 11 * HI
            sy = cy + math.sin(ang) * 11 * HI * props3d.KZ
            pygame.draw.circle(hr, (255, 255, 255), (int(sx), int(sy)), max(1, HI // 2 + 1))

    def _draw_wares(self, hr, shake):
        """Hermie's counter: each ware, bobbing when Octo is at it, and its price underneath, drawn
        over the 3D stall so the prices can always be read."""
        for ware, r in self.wares:
            if ware[0] in self.bought:
                continue                                      # sold out: an empty spot on the counter
            img = self.ware_icon(ware[0])
            bob = math.sin(self.t * 0.08 + r.x) if ware is self.shop_focus else 0
            big = pygame.transform.scale(img, (img.get_width() * HI, img.get_height() * HI))
            x, y = self._hr(r.centerx - img.get_width() / 2, r.centery - img.get_height() / 2 + bob, shake)
            hr.blit(big, (x, y))
            price = self.shop_price(ware[2])
            label = str(price)
            tmp = pygame.Surface((gfx.text_width(label) + 2, 9), pygame.SRCALPHA)
            gfx.text(tmp, label, 0, 0, (255, 220, 120) if self.player.pearls >= price else (230, 130, 130))
            x, y = self._hr(r.centerx - tmp.get_width() / 2, r.bottom + 2, shake)
            hr.blit(pygame.transform.scale(tmp, (tmp.get_width() * HI, 9 * HI)), (x, y))

    @staticmethod
    def is_folk3d(n):
        return type(n).__name__ in FOLK

    def _draw_folk(self, hr, n, shake):
        """A friendly character as a 3D figure in Octo's own pixel style: the octopus townsfolk are
        Octo's model in their own colours and hats, the turtles (Old Shelly too) have domed shells
        and turn to face the way they go, Hermie is a cube figure, and the statue is a golden Octo."""
        h = self.ground_height(n)
        kind = type(n).__name__
        if kind == 'LegendStatue':
            return self._draw_statue(hr, n, h, shake)
        icon = None
        if kind == 'Citizen':
            bob = 0 if n.moving else (1 if (n.t // 30) % 2 else 0)
            fx, fy = n.x + 8, n.y + 16 + bob
            if n.kind == 'turtle':
                base = n.image()
                img, (ax, ay) = _turtle(base, n.facing)
                top = fy - base.get_height()
            else:
                frame = (n.t // 14) % 2 if n.moving else (n.t // 40) % 2
                img, (ax, ay) = voxel.octo_image('cit_' + n.id, frame, FACING_YAW.get(n.facing, 0.22), HI, 0.6,
                                                 n.hat)
                if n.small:                                   # little Ollie
                    img = pygame.transform.smoothscale(img, (int(img.get_width() * 0.75), int(img.get_height() * 0.75)))
                    ax, ay = ax * 0.75, ay * 0.75
                top = fy - (12 if n.small else 16)
            if n.icon:
                icon = (n.x + 8, top - (14 if n.hat else 8))
        elif kind == 'Shelly':
            base = gfx.SPR['turtle'][1 if (n.t % 200) > 190 else 0]
            fx, fy = n.x + base.get_width() / 2, n.y + base.get_height()
            img, (ax, ay) = _turtle(base, 'up')
        else:                                                 # Hermie
            base = gfx.SPR['hermit'][1 if (n.t % 160) > 150 else 0]
            bob = 1 if (n.t // 30) % 2 else 0
            fx, fy = n.x + base.get_width() / 2, n.y + base.get_height() + bob
            img, (ax, ay) = _figure(('hermit', id(base)), base)
        x, y = self._hr(fx - props3d.KX * h, fy - props3d.KZ * h, shake)
        hr.blit(img, (x - ax, y - ay))
        if icon:                                              # the quest marker over their head
            tmp = pygame.Surface((16, 18), pygame.SRCALPHA)
            n._icon(tmp, 8, 9)
            ix, iy = self._hr(icon[0] - props3d.KX * h, icon[1] - props3d.KZ * h, shake)
            hr.blit(pygame.transform.scale(tmp, (16 * HI, 18 * HI)), (ix - 8 * HI, iy - 9 * HI))

    def _draw_enemy(self, hr, e, shake):
        """An enemy as 3D figures, whatever it is: it draws itself onto a recorder; each sprite it
        stamps becomes a cube figure in the same spot (see-through glows stay flat), and the rest
        of what it drew (health bar, crown, rings) goes over the top."""
        if not _rec:
            _rec.append(_Recorder((160, 140)))
        rec = _rec[0]
        rec.fill((0, 0, 0, 0))
        rec.blits.clear()
        ex, ey = round(e.x), round(e.y)
        e.draw(rec, _ENEMY_PAD - ex, _ENEMY_PAD - ey)
        h = self.ground_height(e)
        lx, ly = -props3d.KX * h, -props3d.KZ * h
        for src, (dx, dy) in rec.blits:
            wx, wy = dx - _ENEMY_PAD + ex + lx, dy - _ENEMY_PAD + ey + ly     # the sprite's top-left, in the world
            fig, ok = _enemy_figure(src, self.t)
            a = src.get_alpha()
            if fig is not None:
                img, (ax, ay) = fig
                if a is not None and a < 255:                 # fading (ghosts, a boss coming in)
                    img = img.copy()
                    img.set_alpha(a)
                x, y = self._hr(wx + src.get_width() / 2, wy + src.get_height(), shake)
                hr.blit(img, (x - ax, y - ay))
            else:                                             # glow, or not built yet: drawn flat
                big = pygame.transform.scale(src, (src.get_width() * HI, src.get_height() * HI))
                if a is not None and a < 255:
                    big.set_alpha(a)
                hr.blit(big, self._hr(wx, wy, shake))
        drawn = rec.get_bounding_rect()
        if drawn.w and drawn.h:                               # health bar, crown, rings
            part = rec.subsurface(drawn)
            big = pygame.transform.scale(part, (drawn.w * HI, drawn.h * HI))
            hr.blit(big, self._hr(drawn.x - _ENEMY_PAD + ex + lx, drawn.y - _ENEMY_PAD + ey + ly, shake))

    def _draw_statue(self, hr, n, h, shake):
        """The Living Legend's stone plinth, and once it's earned a golden 3D Octo standing on it."""
        img, (ax, ay) = _figure('plinth', _plinth(), depth=5.0, ball=False, yaw=0.3)
        x, y = self._hr(n.x + 8 - props3d.KX * h, n.y + 17 - props3d.KZ * h, shake)
        hr.blit(img, (x - ax, y - ay))
        if not n.lit:
            tmp = pygame.Surface((8, 10), pygame.SRCALPHA)
            gfx.text(tmp, "?", 1, 1, (150, 140, 170))
            qx, qy = self._hr(n.x + 5, n.y, shake)
            hr.blit(pygame.transform.scale(tmp, (8 * HI, 10 * HI)), (qx, qy))
            return
        key = ('gold', n.hat)
        if key not in _folk:                                  # a bright, shining gold (as the flat statue was)
            img, anchor = voxel.octo_image('blue', 0, 0.22, HI, 0.6, n.hat, tint=(255, 220, 120))
            img = img.copy()
            img.fill((80, 62, 14), special_flags=pygame.BLEND_RGB_ADD)
            _folk[key] = (img, anchor)
        gold, (gx, gy) = _folk[key]
        x, y = self._hr(n.x + 8, n.y + 10, shake)
        hr.blit(gold, (x - gx, y - gy))
        if (n.t // 8) % 6 == 0:                               # a glint
            sx, sy = self._hr(n.x + 3 + (n.t // 16) % 10, n.y - 4 + (n.t // 7) % 9, shake)
            w = max(1, HI // 2)
            pygame.draw.line(hr, (255, 255, 255), (sx - 2 * HI, sy), (sx + 2 * HI, sy), w)
            pygame.draw.line(hr, (255, 255, 255), (sx, sy - 2 * HI), (sx, sy + 2 * HI), w)

    def _warm_folk(self):
        """Make everyone's standing pose ahead of time (for the warm-up on the title screen)."""
        import folk
        from people import _turtle_frames
        for nid, d in folk.NPCS.items():
            if d.get('hidden'):
                continue
            if d['kind'] == 'octo':
                for f in (0, 1):
                    voxel.octo_image('cit_' + nid, f, FACING_YAW['down'], HI, 0.6, d.get('hat'))
                    yield
            else:
                _turtle(_turtle_frames(tuple(d['shell']), tuple(d['skin']), d.get('small', False))[0], 'down')
                yield
        _turtle(gfx.SPR['turtle'][0], 'up')
        yield
        _figure(('hermit', id(gfx.SPR['hermit'][0])), gfx.SPR['hermit'][0])
        yield

    def _draw_raised(self, hr, n, shake):
        """An entity standing up on the pyramid: draw its pixel art, lifted to the top."""
        h = self.ground_height(n)
        tmp = pygame.Surface((64, 48), pygame.SRCALPHA)
        n.draw(tmp, 16 - round(n.x), 16 - round(n.y))
        big = pygame.transform.scale(tmp, (64 * HI, 48 * HI))
        x, y = self._hr(round(n.x) - 16 - props3d.KX * h, round(n.y) - 16 - props3d.KZ * h, shake)
        hr.blit(big, (x, y))

    def _octo_img(self, yaw, flash=False):
        p = self.player
        frame = 0 if p.attack_t else p.anim
        return voxel.octo_image(p.mood, frame, yaw, HI, 0.6, getattr(p, 'hat', 'none'), flash)

    def update_yaw(self):
        p = self.player
        if p is None:
            return
        target = FACING_YAW.get(p.facing, 0.22)
        if p.facing == 'down' and not getattr(p, 'moving', False):
            target += math.sin(self.t * 0.03) * 0.18            # a gentle idle sway shows he's round
        d = (target - self.p_yaw + math.pi) % math.tau - math.pi
        self.p_yaw += d * 0.3

    def _draw_player(self, hr, shake):
        p = self.player
        if p.invuln and (p.invuln // 3) % 2 and not p.knock_t:
            return
        if p.roll_t:                                          # Prickly's spike roll: a 3D spiky ball
            c = attacks3d.Ctx(self, hr, shake)
            c.h = self.ground_height(p)
            attacks3d.draw_roll(c, p)
            return
        yaw = self.p_yaw
        if p.flip_t:                                          # changing form: a full spin
            yaw += (14 - p.flip_t) / 14 * math.tau
        if self.arrive_t:
            yaw += self.arrive_t * 0.45
        img, (ax, ay) = self._octo_img(yaw, flash=bool(p.knock_t))
        fx, fy = p.x + 8, p.y + 15.5
        h = self.ground_height(p)
        fx -= props3d.KX * h
        fy -= props3d.KZ * h
        sx, sy = 1.0, 1.0
        ghosts = self.__dict__.setdefault('jet_ghosts', [])
        if p.dash_t:
            dx, dy = p.dash_dir
            sx, sy = (1.18, 0.84) if dx else (0.84, 1.18)
            ghosts.append([fx, fy, 9])                        # where he was: the jet leaves copies behind
        elif not (p.flip_t or p.attack_t or p.knock_t):
            if getattr(p, 'moving', False) and (p.walk_t // 6) % 2:
                sx, sy = 1.06, 0.94
            else:
                fy += math.sin(p.idle_t * 0.07)
        if self.arrive_t:
            k = 1 - self.arrive_t / ARRIVE_LEN
            sx, sy = sx * k, sy * k
        x, y = self._hr(fx, fy, shake)
        if h > 0:                                             # a shadow on the pyramid's top
            sw, sh = 12 * HI, 4 * HI
            shadow = pygame.Surface((sw, sh), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow, (40, 30, 20, 90), shadow.get_rect())
            hr.blit(shadow, (x - sw / 2, y - sh / 2))
        if (sx, sy) != (1.0, 1.0):
            w, hh = max(1, int(img.get_width() * sx)), max(1, int(img.get_height() * sy))
            img = pygame.transform.scale(img, (w, hh))
            ax, ay = ax * sx, ay * sy
        for g in ghosts:
            g[2] -= 1
        ghosts[:] = [g for g in ghosts if g[2] > 0][-9:]
        if ghosts:
            self._draw_jet_ghosts(hr, img, ax, ay, ghosts, shake)
        if p.dash_t:
            dx, dy = p.dash_dir
            if dy >= 0:                                       # streaks trailing behind him (north of him)
                self._draw_jet_streaks(hr, x, y - 8 * HI, dx, dy)
            if dx:                                            # leaning into the jet
                cx0, cy0 = x - ax + img.get_width() / 2, y - ay + img.get_height() / 2
                img = pygame.transform.rotate(img, -11 * dx)       # (turning keeps his middle in place)
                ax, ay = x - (cx0 - img.get_width() / 2), y - (cy0 - img.get_height() / 2)
        if p.fog_t:
            img = img.copy()
            img.set_alpha(110 if p.fog_t > 50 or (p.fog_t // 4) % 2 else 220)
        hr.blit(img, (x - ax, y - ay))
        if p.dash_t and p.dash_dir[1] < 0:                    # jetting away: the streaks are in front
            self._draw_jet_streaks(hr, x, y - 8 * HI, *p.dash_dir)
        if self.arrive_t:                                     # rings bursting out as he lands
            k = 1 - self.arrive_t / ARRIVE_LEN
            col = tuple(world.TRIALS[self.trial['name']].get('color', (255, 255, 255))) if self.trial else (255, 255, 255)
            for i in range(2):
                r = int((6 + k * 30 + i * 8) * HI)
                pygame.draw.ellipse(hr, col, (x - r, y - 8 * HI - r * 0.6, r * 2, r * 1.2), max(1, HI))

    def _draw_jet_ghosts(self, hr, img, ax, ay, ghosts, shake):
        """See-through copies of Octo where he just was, washed in his ink jet colour."""
        import style
        p = self.player
        col = style.dash_rgb(p.dash_col, self.t)
        tint = img.copy()
        tint.fill((col[0] // 2, col[1] // 2, col[2] // 2, 0), special_flags=pygame.BLEND_RGBA_ADD)
        n = len(ghosts) - 1
        for i, (gx, gy, life) in enumerate(ghosts[:-1]):
            if (n - i) % 3:                                   # every third spot: three clear copies
                continue
            tint.set_alpha(int(16 * life))
            x, y = self._hr(gx, gy, shake)
            hr.blit(tint, (x - ax, y - ay))

    def _draw_jet_streaks(self, hr, x, y, dx, dy):
        """Dashes of rushing water trailing behind Octo as he jets, bright near him and fading away."""
        import hifi
        for n, (off, k) in enumerate(((-5, 0.8), (5, 1.0))):
            L = (10 + 8 * k + ((self.t + n * 2) % 4) * 2) * HI
            ox, oy = -dy * off * HI, dx * off * HI           # side by side, across the jet
            a = (x + ox - dx * (8 + n % 2 * 3) * HI, y + oy - dy * (8 + n % 2 * 3) * HI)
            for i in range(4):
                f0, f1 = i / 4, (i + 0.65) / 4
                c = hifi.mix((225, 242, 255), (104, 114, 126), i / 4)
                pygame.draw.line(hr, c, (a[0] - dx * L * f0, a[1] - dy * L * f0),
                                 (a[0] - dx * L * f1, a[1] - dy * L * f1), max(1, HI // 2 + 1))

    SNAIL_YAW = {'right': -0.35, 'left': 0.35, 'down': 0.25, 'up': math.pi + 0.25}

    def _draw_snail(self, hr, shake):
        """Pebble, as a little 3D snail in the same pixel style as Octo."""
        import coop
        s = self.snail
        if s.invuln and (s.invuln // 3) % 2 and not s.knock_t and not s.resting:
            return
        img2d = s.image()
        if s.spin_t or s.resting:
            yaw = (self.t * 0.5) if s.spin_t else 0.3
        else:
            yaw = self.SNAIL_YAW[s.facing]
        yq = round(yaw / (math.tau / 48)) % 48
        key = ('snail', id(img2d), yq, bool(s.knock_t))
        model = voxel.sprite_model(img2d, depth=4.0)
        img, (ax, ay) = voxel.cached(key, model, HI, yq * math.tau / 48, 0.6, None, bool(s.knock_t), coop.INK)
        h = self.ground_height(s)
        fx, fy = s.x + 8 - props3d.KX * h, s.y + 15.5 - props3d.KZ * h
        if s.resting:
            fy += math.sin(self.t * 0.2)
        x, y = self._hr(fx, fy, shake)
        hr.blit(img, (x - ax, y - ay))
        if s.resting:                                     # Zzz while he rests
            for i in range(2):
                zy = y - (22 + ((self.t // 2 + i * 15) % 30)) * HI
                pygame.draw.lines(hr, (230, 240, 255), False, [(x + 6 * HI, zy), (x + 9 * HI, zy), (x + 6 * HI, zy + 3 * HI),
                                                              (x + 9 * HI, zy + 3 * HI)], max(1, HI // 2 + 1))

    # ---- the trip into a portal --------------------------------------------------
    def start_portal(self, name):
        t = world.TRIALS[name]
        px, py = t['portal']
        p = self.player
        self.portal_anim = {'name': name, 't': 0, 'from': (p.x + 8, p.y + 15.5), 'yaw': self.p_yaw,
                            'ring': (px * TILE + 8, py * TILE + 12.5),
                            'streaks': [(random.uniform(0, math.tau), random.uniform(0.3, 1.0)) for _ in range(40)]}
        p.attack_t = p.dash_t = p.knock_t = 0
        self.state = 'portal'
        sound.play('whoosh')

    def update_portal(self):
        a = self.portal_anim
        a['t'] += 1
        if a['t'] == 30:
            sound.play('portal')
        if a['t'] == 44:
            sound.play('warp')
        self.zoom = (a['ring'], 1 + 0.75 * _ease_in(a['t'] / PORTAL_LEN))
        if a['t'] >= PORTAL_LEN:
            self.portal_anim = None
            self.zoom = None
            self.state = 'play'
            self.enter_trial(a['name'])
            self.arrive_t = ARRIVE_LEN

    def _draw_portal_octo(self, hr, shake):
        """Octo, spiralling into the vortex and shrinking away."""
        a = self.portal_anim
        u = _ease_in(min(1.0, a['t'] / 44))
        if u >= 1:
            return
        fx, fy = a['from']
        rx, ry = a['ring']
        ang = u * math.tau * 2.5
        rad = (1 - u) * 12
        x = fx + (rx - fx) * u + math.cos(ang) * rad * u
        y = fy + (ry - fy) * u + math.sin(ang) * rad * u * 0.6
        z = 16 * u
        img, (ax, ay) = self._octo_img(a['yaw'] + u * u * math.tau * 4)
        k = max(0.05, 1 - u * 0.95)
        img = pygame.transform.scale(img, (max(1, int(img.get_width() * k)), max(1, int(img.get_height() * k))))
        sx, sy = self._hr(x - props3d.KX * z, y - props3d.KZ * z + 8 * u, shake)
        hr.blit(img, (sx - ax * k, sy - ay * k))

    def draw_portal_fx(self, top):
        """Streaks of light rushing into the portal, then a flash (on the top layer)."""
        a = self.portal_anim
        if a is None:
            return
        t = a['t']
        rx, ry = a['ring']
        cx, cy = self._hr(rx - props3d.KX * 16, ry - props3d.KZ * 16, (0, 0))
        col = tuple(world.TRIALS[a['name']].get('color', (255, 255, 255)))
        if t > 6:
            for ang, sp in a['streaks']:
                d = ((t * sp * 9 + ang * 40) % 140)
                r0 = (150 - d) * HI
                r1 = r0 - 22 * HI * sp
                if r1 <= 4 * HI:
                    continue
                p0 = (cx + math.cos(ang) * r0, cy + math.sin(ang) * r0 * 0.8)
                p1 = (cx + math.cos(ang) * r1, cy + math.sin(ang) * r1 * 0.8)
                pygame.draw.line(top, col, p0, p1, max(1, HI // 2 + 1))
        if t > 48:
            k = (t - 48) / (PORTAL_LEN - 48)
            v = pygame.Surface(top.get_size(), pygame.SRCALPHA)
            v.fill((255, 255, 255, int(255 * min(1.0, k * 1.1))))
            top.blit(v, (0, 0))
