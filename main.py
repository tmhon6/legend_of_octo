"""Legend of Octo.

Desktop:  python3 main.py    (asks which version to play, like the website: see versions.py)
Browser:  python3 build_web.py   (builds a pygbag web version into build/web)
"""
import asyncio
import os
import sys

os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame  # noqa: F401,E402  (pygbag only loads pygame for the browser when main.py imports it)

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'octo'))

if sys.platform != 'emscripten':        # on a computer: which version? (the browser has its own start page)
    versions = __import__('importlib').import_module('versions')    # (hidden from pygbag's import scan)
    other = versions.pick(sys.argv[1:])
    if other is not None:
        sys.exit(versions.play(other))

from game import Game  # noqa: E402


async def main():
    await Game().run()


asyncio.run(main())
