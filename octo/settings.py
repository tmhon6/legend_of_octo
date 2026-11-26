"""Global constants for Legend of Octo."""

TILE = 16
ROOM_W, ROOM_H = 16, 11                 # tiles per room
PLAY_W, PLAY_H = ROOM_W * TILE, ROOM_H * TILE   # 256 x 176
HUD_H = 56
SCREEN_W, SCREEN_H = PLAY_W, PLAY_H + HUD_H     # 256 x 232 (scaled up by SDL)
FPS = 60

import sys as _sys
WEB_BUILD = _sys.platform == "emscripten"
HI = 2 if WEB_BUILD else 3           # the 3D scenes are drawn this many times sharper than the pixel art

PLAYER_SPEED = 1.3
SCROLL_FRAMES = 44
FADE_FRAMES = 24

START_HEARTS = 3          # in whole hearts; hp is stored in half-hearts


# ---- who made it, and which version this is ---------------------------------
AUTHOR = "Minu Hong"


def _find_version():
    """The git tag this build came from (e.g. "v1.0.0"), "v1.0.0-3-gabc1234" for work after a tag,
    or "dev". Web builds get it from version.py, which build_web.py writes."""
    try:
        from version import VERSION as v
        return v
    except ImportError:
        pass
    import os
    import subprocess
    import sys
    if sys.platform == 'emscripten':
        return 'dev'
    try:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        out = subprocess.run(['git', 'describe', '--tags', '--always'], cwd=root, capture_output=True,
                             text=True, timeout=3)
        return out.stdout.strip() or 'dev'
    except Exception:
        return 'dev'


VERSION = _find_version()
# each tagged version keeps its own saved game; untagged work shares the save of the tag it came after
SAVE_SLOT = ''.join(c for c in VERSION.split('-')[0] if c.isalnum() or c in '._') if VERSION.startswith('v') else 'dev'
