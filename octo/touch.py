"""On-screen touch controls for phones and tablets.

Landscape (the best way to play): the game sits in the middle and the controls fill the space on
  either side of it -- D-pad on the left, action buttons on the right.
Portrait: the game sits at the top and a controller panel fills the space below it.
Squarish screens (tablets) or a touchscreen laptop: see-through buttons over the edges of the game.

Buttons simply send the same key presses the keyboard would, so the game logic doesn't change.
On a phone the first tap also asks the browser for full screen, locked to landscape where allowed.
"""
import math
import sys

import pygame

import gfx
from settings import HI, HUD_H, SCREEN_H, SCREEN_W

WEB = sys.platform == 'emscripten'
PANEL_H = 176
STICK_R = 30                    # how far the joystick knob can travel
MIN_SIDE = 70                   # narrowest side panel worth using in landscape

# name, label, key sent (None = handled specially)
PILLS = [('pause', "II", pygame.K_p), ('map', "MAP", pygame.K_m), ('warp', "WARP", pygame.K_t),
         ('forms', "FORMS", pygame.K_f),
         ('bomb', "BOMB", pygame.K_b), ('ink', "INK", pygame.K_c), ('save', "SAVE", pygame.K_LSHIFT),
         ('mute', "MUTE", pygame.K_n), ('hat', "HAT", pygame.K_h), ('quest', "QUEST", pygame.K_q),
         ('full', "FULL", None)]
ARROW = {'up': pygame.K_UP, 'down': pygame.K_DOWN, 'left': pygame.K_LEFT, 'right': pygame.K_RIGHT}


def _window():
    import platform
    return platform.window


def touch_device():
    """True when the browser reports a touch screen as its main pointer."""
    if not WEB:
        return False
    try:
        w = _window()
        return bool(w.matchMedia("(pointer: coarse)").matches) or int(w.navigator.maxTouchPoints) > 0
    except Exception:
        return False


def viewport():
    try:
        w = _window()
        return int(w.innerWidth), int(w.innerHeight)
    except Exception:
        return None


def toggle_fullscreen():
    """Enter or leave full screen (entering only works right after a tap).
    Returns False when the browser can't do full screen at all (iPhone Safari)."""
    try:
        w = _window()
        if not w.octoCanFullscreen():
            return False
        w.octoToggleFullscreen()
        return True
    except Exception as e:
        print("fullscreen:", e)
        return True


def is_fullscreen():
    try:
        return bool(_window().document.fullscreenElement)
    except Exception:
        return False


def fit_canvas():
    """Size the browser canvas to fill the screen without stretching the pixels."""
    if not WEB:
        return
    try:
        win = _window()
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


class TouchControls:
    def __init__(self, game):
        self.game = game
        self.mode = 'none'          # 'none' | 'sides' | 'panel' | 'overlay'
        self.fingers = {}           # finger id -> what it is pressing
        self.dir = None             # direction held on the D-pad
        self.lit = {}               # button -> frames left to show it pressed
        self.ph = PANEL_H           # height of the portrait panel
        self.side = 0               # width of each landscape side panel
        self.gx = 0                 # where the game picture sits on the display
        self.vp = None
        self.stick = None           # joystick base: where the thumb landed (it follows a long drag)
        self.knob = None            # where the thumb is now
        self.vec = None             # joystick push: (x, y), length up to 1
        self.layout()

    # ---- setup -------------------------------------------------------------
    @property
    def active(self):
        return self.mode != 'none'

    def choose(self, vp):
        """Pick a layout (and display size) for a viewport of vp = (width, height) CSS pixels."""
        if vp is None:
            return 'overlay', (SCREEN_W, SCREEN_H)
        vw, vh = vp
        if vh > vw:
            ph = max(150, min(380, int(SCREEN_W * vh / vw) - SCREEN_H))
            return 'panel', (SCREEN_W, SCREEN_H + ph)
        # sideways: always give the controls their own columns beside the game. On squarer screens
        # (tablets) that makes the game a little smaller, but no button ever covers it.
        side = max((int(SCREEN_H * vw / vh) - SCREEN_W) // 2, 96)
        side = min(side, SCREEN_W)
        return 'sides', (SCREEN_W + 2 * side, SCREEN_H)

    def activate(self, mode=None):
        g = self.game
        self.vp = viewport() if WEB else None
        auto_mode, size = self.choose(self.vp)
        mode = mode or auto_mode
        if mode == 'panel' and size[1] == SCREEN_H:
            size = (SCREEN_W, SCREEN_H + PANEL_H)
        if mode == 'sides' and size[0] == SCREEN_W:
            size = (SCREEN_W + 2 * 96, SCREEN_H)
        if mode == 'overlay':
            size = (SCREEN_W, SCREEN_H)
        self.mode = mode
        self.ph = size[1] - SCREEN_H
        self.side = (size[0] - SCREEN_W) // 2
        self.gx = self.side if mode == 'sides' else 0
        if mode in ('panel', 'sides') or WEB:
            g.window = pygame.display.set_mode((size[0] * HI, size[1] * HI))
        g.display = pygame.Surface(size)           # drawn at game resolution, scaled up into the window
        if g.screen is g.display or g.screen.get_size() != (SCREEN_W, SCREEN_H):
            g.screen = pygame.Surface((SCREEN_W, SCREEN_H))
        self.fingers.clear()
        self.dir = None
        self.layout()
        fit_canvas()

    def check_orientation(self):
        """Re-lay-out when the phone is turned or goes full screen."""
        if self.active and WEB and self.game.t % 20 == 0:
            vp = viewport()
            if vp != self.vp:
                self.activate()

    def layout(self):
        names = [n for n, _, _ in PILLS]
        if self.mode == 'sides':
            s, W = self.side, SCREEN_W + 2 * self.side
            # left: pause / map / warp / full on top, D-pad below.  right: the rest, then buttons
            left, right = ['pause', 'map', 'warp', 'full', 'hat', 'quest'], ['forms', 'bomb', 'ink', 'save', 'mute']
            pw, ph = min(s - 12, 74), 14
            rects = {}
            for col, x0 in ((left, (s - pw) // 2), (right, W - s + (s - pw) // 2)):
                for i, n in enumerate(col):
                    rects[n] = pygame.Rect(x0, 4 + i * 16, pw, ph)
            self.pill_rects = [rects[n] for n in names]
            r = min(46, s // 2 - 6)
            self.dpad = (s // 2, 6 + 4 * 18 + (SCREEN_H - 78) // 2 + 4, r)
            rx = W - s // 2
            k = min(1.0, max(0.88, s / 110))     # never so small the labels don't fit
            cy = 6 + 4 * 18 + (SCREEN_H - 78) // 2
            self.buttons = {'atk': (int(rx + 18 * k), int(cy - 16 * k), int(24 * k), pygame.K_z, "ATTACK"),
                            'form': (int(rx - 24 * k), int(cy + 22 * k), int(17 * k), pygame.K_x, "FORM"),
                            'jet': (int(rx + 22 * k), int(cy + 44 * k), int(15 * k), pygame.K_v, "JET")}
        elif self.mode == 'panel':
            y0 = SCREEN_H
            n = len(PILLS)
            per = (n + 1) // 2                             # two rows of pills
            w = (SCREEN_W - 4) // per
            self.pill_rects = [pygame.Rect(2 + (i % per) * w, y0 + 6 + (i // per) * 18, w - 2, 15) for i in range(n)]
            cy = y0 + 44 + (self.ph - 44) // 2          # middle of the space under the buttons rows
            self.dpad = (64, cy, 46)
            self.buttons = {'atk': (206, cy - 18, 24, pygame.K_z, "ATTACK"),
                            'form': (158, cy + 22, 18, pygame.K_x, "FORM"),
                            'jet': (222, cy + 38, 16, pygame.K_v, "JET")}
        else:
            n = len(PILLS)
            pw = min(28, (SCREEN_W - 8) // n)
            self.pill_rects = [pygame.Rect(SCREEN_W - 4 - (n - i) * pw, HUD_H + 3, pw - 2, 12) for i in range(n)]
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
            w, h = self.game.display.get_size()
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
        if st != 'title':
            for name, (bx, by, br, key, _) in self.buttons.items():
                if math.hypot(x - bx, y - by) <= br + 6:
                    self.fingers[fid] = name
                    self.lit[name] = 8
                    self.press(key)
                    return
            for (name, _, key), rect in zip(PILLS, self.pill_rects):
                if rect.inflate(2, 4).collidepoint(x, y):
                    self.fingers[fid] = name
                    self.lit[name] = 8
                    if name == 'full':
                        if not toggle_fullscreen():
                            g.say(["THIS BROWSER CAN'T GO FULL SCREEN.",
                                   "ON AN IPHONE: TAP SHARE, THEN 'ADD TO HOME SCREEN'. OPEN LEGEND OF OCTO "
                                   "FROM ITS ICON AND IT PLAYS FULL SCREEN."])
                    else:
                        self.press(key)
                    return
            # anywhere else on the left half: a joystick appears under your thumb -- drag to swim
            w = g.display.get_width()
            if st in ('play', 'warp', 'fuse', 'altar', 'forms', 'catalogue', 'wardrobe', 'megafuse', 'journal', 'trade',
                      'name', 'radio', 'museum') and x < w / 2:
                self.fingers[fid] = 'dpad'
                self.stick = (x, y)
                self.knob = (x, y)
                self.dir, self.vec = None, None
                return
        # a tap anywhere else
        self.fingers[fid] = 'tap'
        if st == 'title':
            for i, rect in enumerate(getattr(g.title_scene, 'menu_rects', [])):
                if rect.collidepoint(x - self.gx, y):
                    g.title_sel = i
            g.on_key(pygame.K_RETURN)
        elif st == 'dialog':
            g.on_key(pygame.K_z)
        elif st == 'versus':
            g.on_key(pygame.K_RETURN)
        elif st == 'map':
            g.on_key(pygame.K_m)
        elif st in ('fuse', 'altar', 'forms', 'catalogue', 'wardrobe', 'megafuse', 'journal', 'trade', 'radio', 'museum'):
            g.on_key(pygame.K_ESCAPE)
        elif st in ('name', 'medal', 'cityintro', 'sleep'):
            g.on_key(pygame.K_RETURN)
        elif st == 'pause':
            g.on_key(pygame.K_p)
        elif st in ('gameover', 'win'):
            g.on_key(pygame.K_RETURN)

    def move(self, fid, pos):
        if self.fingers.get(fid) != 'dpad':
            return
        R = STICK_R
        bx, by = self.stick or pos
        vx, vy = pos[0] - bx, pos[1] - by
        d = math.hypot(vx, vy)
        if d > R:                    # dragged past the rim: the base follows the thumb
            bx, by = pos[0] - vx / d * R, pos[1] - vy / d * R
            vx, vy, d = vx / d * R, vy / d * R, R
        self.stick, self.knob = (bx, by), pos
        if d < 5:
            new, self.vec = None, None
        else:
            k = min(1.0, max(0.45, d / R))       # a light push still swims at a decent pace
            self.vec = (vx / d * k, vy / d * k)
            new = ('right' if vx > 0 else 'left') if abs(vx) > abs(vy) else ('down' if vy > 0 else 'up')
        if new != self.dir:
            self.dir = new
            if new and self.game.state not in ('play',):
                self.game.on_key(ARROW[new])     # menus step once per push

    def up(self, fid):
        if self.fingers.pop(fid, None) == 'dpad':
            self.dir = self.vec = None
            self.stick = self.knob = None

    # ---- drawing -----------------------------------------------------------
    def present(self, disp):
        """Put the game picture and the controls on the real display."""
        g = self.game
        for k in list(self.lit):
            self.lit[k] -= 1
            if self.lit[k] <= 0:
                del self.lit[k]
        if self.mode in ('panel', 'sides'):
            self._panel_bg(disp)
        disp.blit(g.screen, (self.gx, 0))
        if g.state in ('title', 'intro'):
            return
        if self.mode in ('panel', 'sides'):
            self._draw_controls(disp, alpha=255)
        else:
            layer = pygame.Surface(disp.get_size(), pygame.SRCALPHA)
            self._draw_controls(layer, alpha=110)
            disp.blit(layer, (0, 0))

    def _panel_bg(self, disp):
        w, h = disp.get_size()
        if self.mode == 'sides':
            for i in range(h):
                c = 30 - i // 14
                pygame.draw.line(disp, (c, c + 6, c + 24), (0, i), (w, i))
            pygame.draw.line(disp, (90, 110, 170), (self.side - 1, 0), (self.side - 1, h))
            pygame.draw.line(disp, (90, 110, 170), (w - self.side, 0), (w - self.side, h))
            if self.game.state == 'title':
                for x0 in (0, w - self.side):
                    gfx.text(disp, "TAP", x0 + self.side // 2, h // 2 - 10, (200, 215, 255), center=True)
                    gfx.text(disp, "TO PLAY", x0 + self.side // 2, h // 2 + 2, (200, 215, 255), center=True)
            return
        y0 = SCREEN_H
        for i in range(self.ph):
            c = 34 - i // 12
            pygame.draw.line(disp, (max(0, c), max(0, c + 6), max(0, c + 24)), (0, y0 + i), (SCREEN_W, y0 + i))
        pygame.draw.line(disp, (90, 110, 170), (0, y0), (SCREEN_W, y0))
        if self.game.state == 'title':
            gfx.text(disp, "TAP THE SCREEN TO PLAY", SCREEN_W // 2, y0 + self.ph // 2 - 10, (200, 215, 255),
                     center=True)
            gfx.text(disp, "TURN SIDEWAYS FOR A BIGGER VIEW", SCREEN_W // 2, y0 + self.ph // 2 + 10,
                     (120, 135, 180), center=True)

    def _draw_controls(self, s, alpha):
        def col(c, lit=False):
            c = tuple(min(255, v + 70) for v in c) if lit else c
            return c + (alpha,)
        # pills
        for (name, label, _), rect in zip(PILLS, self.pill_rects):
            if name == 'full':
                if not WEB:
                    continue
                label = "EXIT" if is_fullscreen() else "FULL"
            lit = name in self.lit
            pygame.draw.rect(s, col((50, 60, 100), lit), rect, border_radius=6)
            pygame.draw.rect(s, col((140, 160, 220)), rect, 1, border_radius=6)
            if name == 'mute' and not __import__('sound').music_on:
                label = "SOUND"
            gfx.text(s, label, rect.centerx, rect.centery - 3, (230, 235, 255), center=True)
        # joystick: under the thumb while held, a faint hint where it usually sits otherwise
        if self.stick:
            bx, by = self.stick
            kx, ky = self.knob
            base = pygame.Surface((STICK_R * 2 + 4, STICK_R * 2 + 4), pygame.SRCALPHA)
            c = STICK_R + 2
            pygame.draw.circle(base, (60, 66, 96, min(alpha, 150)), (c, c), STICK_R)
            pygame.draw.circle(base, (150, 160, 210, min(alpha, 220)), (c, c), STICK_R, 2)
            s.blit(base, (bx - c, by - c))
            pygame.draw.circle(s, col((40, 44, 70)), (int(kx) + 1, int(ky) + 2), 13)
            pygame.draw.circle(s, col((130, 145, 210)), (int(kx), int(ky)), 13)
            pygame.draw.circle(s, col((255, 255, 255)), (int(kx), int(ky)), 13, 1)
        else:
            dx, dy, r = self.dpad
            hint = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            c = r + 2
            pygame.draw.circle(hint, (60, 66, 96, min(alpha, 110)), (c, c), r)
            pygame.draw.circle(hint, (150, 160, 210, min(alpha, 160)), (c, c), r, 1)
            pygame.draw.circle(hint, (150, 160, 210, min(alpha, 160)), (c, c), 12)
            s.blit(hint, (dx - c, dy - c))
            gfx.text(s, "DRAG", dx, dy + r + 4, (150, 160, 210), center=True)
            gfx.text(s, "TO MOVE", dx, dy + r + 13, (150, 160, 210), center=True)
        # action buttons
        colours = {'atk': (200, 60, 80), 'form': (60, 120, 220), 'jet': (40, 150, 120)}
        for name, (bx, by, br, _, label) in self.buttons.items():
            lit = name in self.lit
            pygame.draw.circle(s, col((0, 0, 0)), (bx + 1, by + 2), br)
            pygame.draw.circle(s, col(colours[name], lit), (bx, by), br)
            pygame.draw.circle(s, col((255, 255, 255)), (bx, by), br, 1)
            if gfx.text_width(label) > br * 2 - 2:
                label = label[:3]
            gfx.text(s, label, bx, by - 3, (255, 255, 255), center=True)
