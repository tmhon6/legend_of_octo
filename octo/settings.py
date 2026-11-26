"""Global constants for Legend of Octo."""

TILE = 16
ROOM_W, ROOM_H = 16, 11                 # tiles per room
PLAY_W, PLAY_H = ROOM_W * TILE, ROOM_H * TILE   # 256 x 176
HUD_H = 56
SCREEN_W, SCREEN_H = PLAY_W, PLAY_H + HUD_H     # 256 x 232 (scaled up by SDL)
FPS = 60

PLAYER_SPEED = 1.3
SCROLL_FRAMES = 44
FADE_FRAMES = 24

START_HEARTS = 3          # in whole hearts; hp is stored in half-hearts
