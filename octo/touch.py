"""On-screen touch controls for phones and tablets.

Portrait: the game sits at the top of the screen and a controller panel fills the space below it.
Landscape (or a touchscreen laptop): translucent buttons are drawn over the edges of the game.
Buttons simply send the same key presses the keyboard would, so the game logic doesn't change.
"""
import math
import sys

import pygame

import gfx
from settings import HUD_H, SCREEN_H, SCREEN_W

WEB = sys.platform == 'emscripten'
PANEL_H = 176

# name, label, key sent
PILLS = [('pause', "II", pygame.K_p), ('map', "MAP", pygame.K_m), ('warp', "WARP", pygame.K_t),
         ('bomb', "BOMB", pygame.K_b), ('ink', "INK", pygame.K_c), ('save', "SAVE", pygame.K_LSHIFT),
         ('mute', "MUTE", pygame.K_n)]
ARROW = {'up': pygame.K_UP, 'down': pygame.K_DOWN, 'left': pygame.K_LEFT, 'right': pygame.K_RIGHT}


def touch_device():
    """True when the browser reports a touch screen as its main pointer."""
    if not WEB:
        return False
    try:
        import platform
        w = platform.window
        return bool(w.matchMedia("(pointer: coarse)").matches) or int(w.navigator.maxTouchPoints) > 0
    except Exception:
        return False


def panel_height():
    """Make the controller panel tall enough that the whole page fills the phone screen."""
    try:
        import platform
        w, h = int(platform.window.innerWidth), int(platform.window.innerHeight)
        return max(150, min(380, int(SCREEN_W * h / w) - SCREEN_H))
    except Exception:
        return PANEL_H


def fit_canvas():
    """Size the browser canvas to fill the screen without stretching the pixels."""
    if not WEB:
        return
    try:
        import platform
        win = platform.window
        surf = pygame.display.get_surface()
        if surf is None:
            return
        sw, sh = surf.get_size()
        vw, vh = float(win.innerWidth), float(win.innerHeight)
        k = min(vw / sw, vh / sh)
        cw, ch = int(sw * k), int(sh * k)
        st = win.document.getElementById("canvas").style
        st.width, st.height = f"{cw}px", f"{ch}px"
        st.left, st.top = f"{int((vw - cw) / 2)}px", f"{int((vh - ch) / 2)}px"
        st.position, st.margin = "fixed", "0"
    except Exception as e:
        print("fit_canvas:", e)


def portrait():
    if not WEB:
        return False
    try:
        import platform
        return int(platform.window.innerHeight) > int(platform.window.innerWidth)
    except Exception:
        return False


class TouchControls:
    def __init__(self, game):
        self.game = game
        self.mode = 'none'          # 'none' | 'panel' | 'overlay'
        self.fingers = {}           # finger id -> what it is pressing
        self.dir = None             # direction held on the D-pad
        self.lit = {}               # button -> frames left to show it pressed
        self.ph = PANEL_H
        self.layout()

    # ---- setup -------------------------------------------------------------
    @property
    def active(self):
        return self.mode != 'none'

    def activate(self, mode=None):
        mode = mode or ('panel' if portrait() else 'overlay')
        if mode == self.mode:
            return
        self.mode = mode
        g = self.game
        self.ph = panel_height() if WEB else PANEL_H
        size = (SCREEN_W, SCREEN_H + self.ph) if mode == 'panel' else (SCREEN_W, SCREEN_H)
        if mode == 'panel' or WEB:
            g.display = pygame.display.set_mode(size)
        else:
            g.display = pygame.display.get_surface()
        if g.screen is g.display or g.screen.get_size() != (SCREEN_W, SCREEN_H):
            g.screen = pygame.Surface((SCREEN_W, SCREEN_H))
        self.layout()
        fit_canvas()

    def check_orientation(self):
        """Switch between panel and overlay when the phone is turned."""
        if self.active and WEB and self.game.t % 30 == 0:
            want = 'panel' if portrait() else 'overlay'
            if want != self.mode:
                self.activate(want)
            else:
                fit_canvas()            # the page may have resized (address bar, rotation)

    def layout(self):
        if self.mode == 'panel':
            y0 = SCREEN_H
            self.pill_rects = [pygame.Rect(2 + i * 36, y0 + 10, 34, 16) for i in range(len(PILLS))]
            cy = y0 + 30 + (self.ph - 30) // 2          # middle of the space under the buttons row
            self.dpad = (64, cy, 46)
            self.buttons = {'atk': (206, cy - 18, 24, pygame.K_z, "ATTACK"),
                            'form': (158, cy + 22, 18, pygame.K_x, "FORM"),
                            'jet': (222, cy + 38, 16, pygame.K_v, "JET")}
        else:
            self.pill_rects = [pygame.Rect(SCREEN_W - 4 - (len(PILLS) - i) * 31, HUD_H + 3, 29, 12)
                               for i in range(len(PILLS))]
            self.dpad = (40, SCREEN_H - 40, 32)
            self.buttons = {'atk': (226, SCREEN_H - 40, 18, pygame.K_z, "ATK"),
                            'form': (194, SCREEN_H - 20, 13, pygame.K_x, "FORM"),
                            'jet': (196, SCREEN_H - 62, 13, pygame.K_v, "JET")}

    # ---- input -------------------------------------------------------------
    def handle(self, ev):
        """Returns True when the event was a touch and has been dealt with."""
        if ev.type in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
            if not self.active:
                self.activate()
            disp = pygame.display.get_surface()
            w, h = disp.get_size() if disp else (SCREEN_W, SCREEN_H)
            pos = (ev.x * w, ev.y * h)
            if ev.type == pygame.FINGERDOWN:
                self.down(ev.finger_id, pos)
            elif ev.type == pygame.FINGERMOTION:
                self.move(ev.finger_id, pos)
            else:
                self.up(ev.finger_id)
            return True
        # the browser also turns each touch into a fake mouse click: ignore those
        if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION) \
                and getattr(ev, 'touch', False):
            if not self.active:
                self.activate()
            return True
        return False

    def press(self, key):
        g = self.game
        g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode='', scancode=0))

    def down(self, fid, pos):
        g = self.game
        x, y = pos
        st = g.state
        # D-pad
        dx, dy, r = self.dpad
        if math.hypot(x - dx, y - dy) <= r + 10 and st != 'title':
            self.fingers[fid] = 'dpad'
            self.move(fid, pos)
            return
        for name, (bx, by, br, key, _) in self.buttons.items():
            if math.hypot(x - bx, y - by) <= br + 6 and st != 'title':
                self.fingers[fid] = name
                self.lit[name] = 8
                self.press(key)
                return
        for (name, _, key), rect in zip(PILLS, self.pill_rects):
            if rect.inflate(2, 6).collidepoint(x, y) and st not in ('title',):
                self.fingers[fid] = name
                self.lit[name] = 8
                self.press(key)
                return
        # a tap anywhere else
        self.fingers[fid] = 'tap'
        if st == 'title':
            for i, rect in enumerate(getattr(g.title_scene, 'menu_rects', [])):
                if rect.collidepoint(x, y):
                    g.title_sel = i
            g.on_key(pygame.K_RETURN)
        elif st in ('dialog',):
            g.on_key(pygame.K_z)
        elif st == 'map':
            g.on_key(pygame.K_m)
        elif st == 'pause':
            g.on_key(pygame.K_p)
        elif st in ('gameover', 'win'):
            g.on_key(pygame.K_RETURN)
        elif st == 'warp':
            g.on_key(pygame.K_z)

    def move(self, fid, pos):
        if self.fingers.get(fid) != 'dpad':
            return
        dx, dy, r = self.dpad
        vx, vy = pos[0] - dx, pos[1] - dy
        if math.hypot(vx, vy) < 6:
            new = None
        elif abs(vx) > abs(vy):
            new = 'right' if vx > 0 else 'left'
        else:
            new = 'down' if vy > 0 else 'up'
        if new != self.dir:
            self.dir = new
            if new and self.game.state not in ('play',):
                self.game.on_key(ARROW[new])     # menus step once per push

    def up(self, fid):
        if self.fingers.pop(fid, None) == 'dpad':
            self.dir = None

    # ---- drawing -----------------------------------------------------------
    def present(self, disp):
        """Put the game picture and the controls on the real display."""
        g = self.game
        disp.blit(g.screen, (0, 0))
        for k in list(self.lit):
            self.lit[k] -= 1
            if self.lit[k] <= 0:
                del self.lit[k]
        if g.state == 'title':
            if self.mode == 'panel':
                self._panel_bg(disp)
            return
        if self.mode == 'panel':
            self._panel_bg(disp)
            self._draw_controls(disp, alpha=255)
        else:
            layer = pygame.Surface(disp.get_size(), pygame.SRCALPHA)
            self._draw_controls(layer, alpha=110)
            disp.blit(layer, (0, 0))

    def _panel_bg(self, disp):
        y0 = SCREEN_H
        for i in range(self.ph):
            c = 34 - i // 12
            pygame.draw.line(disp, (c, c + 6, c + 24), (0, y0 + i), (SCREEN_W, y0 + i))
        pygame.draw.line(disp, (90, 110, 170), (0, y0), (SCREEN_W, y0))
        if self.game.state == 'title':
            gfx.text(disp, "TAP THE SCREEN TO PLAY", SCREEN_W // 2, y0 + self.ph // 2 - 10, (200, 215, 255), center=True)
            gfx.text(disp, "TURN SIDEWAYS FOR A BIGGER VIEW", SCREEN_W // 2, y0 + self.ph // 2 + 10, (120, 135, 180),
                     center=True)

    def _draw_controls(self, s, alpha):
        def col(c, lit=False):
            c = tuple(min(255, v + 70) for v in c) if lit else c
            return c + (alpha,)
        # pills
        for (name, label, _), rect in zip(PILLS, self.pill_rects):
            lit = name in self.lit
            pygame.draw.rect(s, col((50, 60, 100), lit), rect, border_radius=6)
            pygame.draw.rect(s, col((140, 160, 220)), rect, 1, border_radius=6)
            if name == 'mute' and not __import__('sound').music_on:
                label = "SOUND"
            gfx.text(s, label, rect.centerx, rect.centery - 3, (230, 235, 255), center=True)
        # D-pad
        dx, dy, r = self.dpad
        arm = r * 2 // 3
        for d, (ux, uy) in {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}.items():
            cx, cy = dx + ux * (r - arm // 2), dy + uy * (r - arm // 2)
            rect = pygame.Rect(0, 0, arm, arm)
            rect.center = (cx, cy)
            lit = self.dir == d
            pygame.draw.rect(s, col((60, 66, 96), lit), rect, border_radius=4)
            pygame.draw.rect(s, col((150, 160, 210)), rect, 1, border_radius=4)
            tip = (cx + ux * arm // 4, cy + uy * arm // 4)
            perp = (uy, ux)
            pygame.draw.polygon(s, col((220, 225, 255)), [
                (tip[0] + ux * 3, tip[1] + uy * 3),
                (tip[0] - ux * 3 + perp[0] * 4, tip[1] - uy * 3 + perp[1] * 4),
                (tip[0] - ux * 3 - perp[0] * 4, tip[1] - uy * 3 - perp[1] * 4)])
        pygame.draw.rect(s, col((60, 66, 96)), (dx - arm // 2, dy - arm // 2, arm, arm))
        # action buttons
        colours = {'atk': (200, 60, 80), 'form': (60, 120, 220), 'jet': (40, 150, 120)}
        for name, (bx, by, br, _, label) in self.buttons.items():
            lit = name in self.lit
            pygame.draw.circle(s, col((0, 0, 0)), (bx + 1, by + 2), br)
            pygame.draw.circle(s, col(colours[name], lit), (bx, by), br)
            pygame.draw.circle(s, col((255, 255, 255)), (bx, by), br, 1)
            gfx.text(s, label, bx, by - 3, (255, 255, 255), center=True)
