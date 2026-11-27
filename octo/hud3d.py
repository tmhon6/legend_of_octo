"""The top of the screen in 3D: a raised panel with shiny pearls, voxel hearts that bob,
a slowly turning 3D Octo in the form box, and smooth lettering -- drawn on the hi-res layer
over the pixel-art HUD (whose minimap it borrows).

Hud3D is mixed into Game.
"""
import math

import pygame

import gfx
import hifi
import voxel
from settings import HI, HUD_H, SCREEN_W

_cache = {}


def _text(s, px, col, outline=(6, 8, 20)):
    key = ('t', s, px, col)
    img = _cache.get(key)
    if img is None:
        if len(_cache) > 600:
            _cache.clear()
        img = _cache[key] = hifi.text(s, px, col, outline=outline, shadow=False)
    return img


def _panel():
    img = _cache.get('panel')
    if img is None:
        W, Hh = SCREEN_W * HI, HUD_H * HI
        img = hifi.gradient(W, Hh, [(0, (26, 32, 66)), (0.55, (12, 15, 34)), (1, (6, 7, 18))])
        pygame.draw.line(img, (70, 84, 150), (0, Hh - 2 * HI), (W, Hh - 2 * HI), HI)
        pygame.draw.line(img, (0, 0, 0), (0, Hh - HI), (W, Hh - HI), HI)
        pygame.draw.line(img, (60, 70, 120), (0, 0), (W, 0), max(1, HI // 2))
        _cache['panel'] = img
    return img


def _inset(surf, rect, radius=3):
    """A sunken frame (for the minimap)."""
    x, y, w, h = (v * HI for v in rect)
    r = pygame.Rect(x, y, w, h)
    pygame.draw.rect(surf, (4, 5, 12), r.inflate(4 * HI, 4 * HI), border_radius=radius * HI)
    pygame.draw.rect(surf, (90, 104, 170), r.inflate(4 * HI, 4 * HI), max(1, HI // 2), border_radius=radius * HI)
    pygame.draw.line(surf, (0, 0, 0), (r.x - HI, r.y - HI), (r.right + HI, r.y - HI), HI)


def _raised(surf, rect, col):
    """A raised, bevelled box (for the form box)."""
    x, y, w, h = (v * HI for v in rect)
    key = ('box', tuple(col), w, h)
    img = _cache.get(key)
    if img is None:
        img = hifi.gradient(w, h, [(0, hifi.mix(col, (255, 255, 255), 0.35)), (0.5, col),
                                   (1, hifi.mix(col, (0, 0, 0), 0.45))])
        pygame.draw.rect(img, (255, 255, 255), img.get_rect(), max(1, HI // 2 + 1), border_radius=2 * HI)
        pygame.draw.line(img, hifi.mix(col, (255, 255, 255), 0.7), (2 * HI, HI), (w - 2 * HI, HI), HI)
        _cache[key] = img
    surf.blit(img, (x, y))


def _tube(surf, x, y, w, h, col):
    """A lit tube lying on its side: bright along the top, dark underneath, round at the ends."""
    r = h / 2
    for i in range(h):
        k = (i + 0.5) / h                                  # 0 at the top, 1 at the bottom
        if k < 0.3:
            c = hifi.mix(col, (255, 255, 255), 0.55 - k)
        else:
            c = hifi.mix(col, (0, 0, 0), max(0.0, (k - 0.45) * 0.9))
        inset = r - math.sqrt(max(0.0, r * r - (i + 0.5 - r) ** 2))
        x0, x1 = x + inset, x + w - 1 - inset
        if x1 > x0:
            pygame.draw.line(surf, c, (x0, y + i), (x1, y + i))


def _ball(surf, col, x, y, r, gloss=1.0):
    hifi.blit_ball(surf, col, x * HI, y * HI, r * HI, None, gloss)


def _vox(img, s, yaw=0.25, key=None):
    """A small sprite as a 3D voxel icon (cached)."""
    k = key or ('v', id(img), s, round(yaw, 2))
    out = _cache.get(k)
    if out is None:
        m = voxel.sprite_model(img, depth=2.0)
        out = _cache[k] = voxel.render(m, s, yaw, 0.6, outline=(8, 6, 16))
    return out


class Hud3D:
    def draw_hud3d(self, hr):
        p = self.player
        H_ = HI
        hr.blit(_panel(), (0, 0))
        # the minimap, framed, borrowed from the pixel-art HUD
        _inset(hr, (4, 8, 52, 26))
        mini = self.screen.subsurface((4, 8, 52, 26))
        hr.blit(pygame.transform.scale(mini, (52 * H_, 26 * H_)), (4 * H_, 8 * H_))
        # score: a 3D star and the number
        cx, cy = 7.5 * H_, 41.5 * H_
        pts = [(cx + math.cos(-math.pi / 2 + j * math.pi / 5) * (r * H_), cy + math.sin(-math.pi / 2 + j * math.pi / 5) * (r * H_))
               for j, r in enumerate([4.2, 1.8] * 5)]
        pygame.draw.polygon(hr, (150, 90, 0), [(x + H_ // 2, y + H_ // 2) for x, y in pts])
        pygame.draw.polygon(hr, (255, 214, 70), pts)
        pygame.draw.polygon(hr, (255, 250, 200), [pts[0], pts[1], (cx, cy), pts[9]])
        sc = getattr(self, '_hud_score', self.score())
        img = _text(f"{sc:06d}" if sc < 1000000 else str(sc), 9 * H_, (255, 226, 130))
        hr.blit(img, (13 * H_, 36.5 * H_))
        bar = pygame.Rect(4 * H_, 48 * H_, 48 * H_, 2 * H_)
        pygame.draw.rect(hr, (30, 34, 64), bar, border_radius=H_)
        import score as _score
        nxt, _ = _score.next_milestone(self.score())
        prev = max([q for q, *_ in _score.MILESTONES if q <= self.score()], default=0)
        k = 1.0 if not nxt else (self.score() - prev) / max(1, nxt - prev)
        if k > 0:
            pygame.draw.rect(hr, (255, 200, 70), (bar.x, bar.y, max(H_, int(bar.w * k)), bar.h), border_radius=H_)
        # pearls, keys, spirit pearls, bombs and items
        _ball(hr, (236, 236, 250), 63.5, 15.5, 3.6)
        hr.blit(_text(f"X{p.pearls:03d}", 9 * H_, (255, 255, 255)), (69 * H_, 10.5 * H_))
        key_img, (ax, ay) = _vox(gfx.SPR['key'], max(1, H_ - 1))
        hr.blit(key_img, (63.5 * H_ - ax, 33 * H_ - ay))
        hr.blit(_text(f"X{p.keys}", 9 * H_, (255, 255, 255)), (69 * H_, 23.5 * H_))
        _ball(hr, (150, 100, 230), 102, 28, 3.6)
        hr.blit(_text(f"X{p.spirit}", 9 * H_, (215, 190, 255)), (107 * H_, 23.5 * H_))
        if 'bombbag' in p.items:
            _ball(hr, (60, 70, 110), 102, 14.5, 3.8)
            pygame.draw.line(hr, (200, 160, 90), (103 * H_, 10.5 * H_), (105 * H_, 8.5 * H_), max(1, H_ // 2 + 1))
            if (self.t // 6) % 2:
                pygame.draw.circle(hr, (255, 220, 120), (int(105.5 * H_), int(8 * H_)), max(1, H_))
            hr.blit(_text(f"X{p.bombs:02d}", 9 * H_, (255, 255, 255)), (108 * H_, 10.5 * H_))
        ix = 92
        for wid in ('fins', 'shield', 'deepink'):
            if wid in p.items:
                icon = gfx.SPR['items'][wid]
                img, (ax, ay) = _vox(icon, max(1, H_ - 1), 0.3)
                hr.blit(img, ((ix + 4) * H_ - ax, 39.5 * H_ - ay))
                ix += 10
        name = self.region or ''
        if gfx.text_width(name) > 84:
            name = name.replace('TRIAL OF ', '').replace(' TEMPLE', '').replace('THE ', '')
        hr.blit(_text(name, 8 * H_, (160, 185, 240)), (55 * H_, 40.5 * H_))
        if p.dash_cd and not p.dash_t:                    # the ink jet recharging: a 3D tube filling up
            w = int(28 * H_ * (1 - p.dash_cd / 40))
            groove = pygame.Rect(144 * H_, 50 * H_, 28 * H_, 2 * H_)
            pygame.draw.rect(hr, (10, 10, 24), groove.inflate(H_, H_), border_radius=H_ + 1)
            pygame.draw.rect(hr, (34, 34, 62), groove, border_radius=H_)
            pygame.draw.line(hr, (6, 6, 16), (groove.x + H_, groove.y), (groove.right - H_, groove.y))
            _tube(hr, groove.x, groove.y, max(2 * H_, w), 2 * H_, (140, 130, 255))
        # the form box, with Octo turning slowly inside it
        from game import FORM_BOX, FORM_LABEL
        _raised(hr, (143, 7, 30, 30), FORM_BOX.get(p.mood, (40, 60, 140)))
        frame = (self.t // 20) % 2
        img, (ax, ay) = voxel.octo_image(p.mood, frame, 0.25 + math.sin(self.t * 0.02) * 0.7, H_, 0.6,
                                         getattr(p, 'hat', 'none'))
        hr.blit(img, (158 * H_ - ax, 33 * H_ - ay))
        label = p.ink_mode.upper() if p.mood == 'blue' else FORM_LABEL.get(p.mood, '')
        img = _text(label, 7 * H_, (255, 255, 255))
        hr.blit(img, (158 * H_ - img.get_width() / 2, 38.5 * H_))
        hr.blit(_text("X", 7 * H_, (150, 160, 190)), (175 * H_, 7 * H_))
        hr.blit(_text("Z", 7 * H_, (150, 160, 190)), (175 * H_, 23 * H_))
        # life: voxel hearts that bob, and a beat when you're low
        img = _text("-LIFE-", 9 * H_, (240, 70, 90))
        hr.blit(img, (214 * H_ - img.get_width() / 2, 6 * H_))
        hearts = p.max_hp // 2
        per = 7 if hearts <= 14 else 10
        low = p.hp <= 2
        for i in range(hearts):
            if p.hp >= (i + 1) * 2:
                kind = 'full'
            elif p.hp == i * 2 + 1:
                kind = 'half'
            else:
                kind = 'empty'
            src = gfx.SPR['heart'][kind]
            img, (ax, ay) = _vox(src, max(1, H_ - 1) if per == 10 else H_ - 0.0, 0.2 + 0.15 * math.sin(self.t * 0.05 + i * 0.6),
                                 key=('heart', kind, per, round(0.2 + 0.15 * math.sin(self.t * 0.05 + i * 0.6), 1)))
            hx = (188 + (i % 7) * 9) if per == 7 else (186 + (i % 10) * 7)
            hy = 24 + (i // per) * 9
            bob = math.sin(self.t * 0.08 + i * 0.7) * 0.6
            if low and kind != 'empty' and (self.t // 8) % 4 == 0:
                bob -= 1
            hr.blit(img, ((hx + 3.5) * H_ - ax, (hy + 6.5 + bob) * H_ - ay))
        # Pebble, when he's playing
        s = getattr(self, 'snail', None)
        if s is not None:
            import coop
            icon, (ax, ay) = _vox(coop.frames()['right'][0], max(1, H_ - 1), -0.3, key=('snailicon',))
            hr.blit(icon, (190 * H_ - ax, 52 * H_ - ay))
            for i in range(s.max_hp // 2):
                kind = 'full' if s.hp >= (i + 1) * 2 else 'half' if s.hp == i * 2 + 1 else 'empty'
                img, (ax, ay) = _vox(gfx.SPR['heart'][kind], max(1, H_ - 1), 0.2, key=('sheart', kind))
                hr.blit(img, ((200 + i * 8 + 3) * H_ - ax, 51.5 * H_ - ay))
