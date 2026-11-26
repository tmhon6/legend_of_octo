"""Legend of Octo.

Desktop:  python3 main.py
Browser:  python3 build_web.py   (builds a pygbag web version into build/web)
"""
import asyncio
import os
import sys

import pygame  # noqa: F401  (pygbag only loads pygame for the browser when main.py imports it)

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'octo'))

from game import Game  # noqa: E402


async def main():
    await Game().run()


asyncio.run(main())
