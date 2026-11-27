"""The world's 3D layer.

Octo as a pixel-style 3D figure, the 3D buildings, the Octo Temple pyramid and the trial
portals are drawn sharp on a hi-res layer, in depth order, over the pixel-art ground: things
behind a building disappear behind it, and Octo walks up the pyramid's stairs onto its top.
Also: the animation of Octo being pulled into a trial portal, and popping out of it.

Scene3D is mixed into Game.
"""
import math
import random

import pygame

import props3d
import sound
import voxel
import world
from settings import HI, HUD_H, PLAY_H, PLAY_W, TILE

FACING_YAW = {'down': 0.22, 'up': math.pi + 0.22, 'left': 0.62, 'right': -0.62}
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
        return p is not None and not (p.tumble or p.roll_t or (p.in_sky and p.sphere > 0))

    def ground_height(self, ent):
        return props3d.height_at(ent.rect.centerx, ent.rect.bottom - 1)

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
        p = self.player
        if self.portal_anim is not None:
            a = self.portal_anim
            items.append((a['ring'][1] + 1, 2, 'portal_octo'))
        elif self.state not in ('dying', 'sleep') and self.player_in_3d():
            h = self.ground_height(p)
            key = (pyr_base + 1) if h > 0 and pyr_base is not None else p.rect.bottom
            items.append((key, 2, 'player'))
        sn = getattr(self, 'snail', None)
        if sn is not None and self.state not in ('dying',) and self.portal_anim is None:
            h = self.ground_height(sn)
            key = (pyr_base + 1.2) if h > 0 and pyr_base is not None else sn.rect.bottom
            items.append((key, 2, 'snail'))
        for n in self.npcs:                                   # someone standing up on the pyramid
            if getattr(n, 'hidden', False) or not view.colliderect(n.rect):
                continue
            if self.ground_height(n) > 0 and pyr_base is not None:
                items.append((pyr_base + 0.5, 1, n))
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
        if p.dash_t:
            dx, dy = p.dash_dir
            sx, sy = (1.25, 0.75) if dx else (0.75, 1.25)
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
        if p.fog_t:
            img = img.copy()
            img.set_alpha(110 if p.fog_t > 50 or (p.fog_t // 4) % 2 else 220)
        hr.blit(img, (x - ax, y - ay))
        if self.arrive_t:                                     # rings bursting out as he lands
            k = 1 - self.arrive_t / ARRIVE_LEN
            col = tuple(world.TRIALS[self.trial['name']].get('color', (255, 255, 255))) if self.trial else (255, 255, 255)
            for i in range(2):
                r = int((6 + k * 30 + i * 8) * HI)
                pygame.draw.ellipse(hr, col, (x - r, y - 8 * HI - r * 0.6, r * 2, r * 1.2), max(1, HI))

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
