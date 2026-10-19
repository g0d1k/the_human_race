"""Render the game icon (the ARES-1 sprite) to a PNG, entirely from code."""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import pygame  # noqa: E402

from config import rgb  # noqa: E402
from graphics.sprites import SpriteBank  # noqa: E402


def main(out_path, size=256):
    pygame.init()
    pygame.display.set_mode((1, 1))
    sp = SpriteBank()
    canvas = pygame.Surface((32, 32))
    canvas.fill(rgb(0x0F))
    # a few stars, the flame and the ship, centred on a 32x32 canvas
    for x, y, c in ((3, 4, 0x30), (27, 6, 0x10), (6, 26, 0x10), (25, 25, 0x30), (14, 2, 0x00)):
        canvas.fill(rgb(c), (x, y, 1, 1))
    canvas.blit(sp["flame0"].img, (2, 14))
    canvas.blit(sp["ares"].img, (9, 8))
    pygame.image.save(pygame.transform.scale(canvas, (size, size)), out_path)
    pygame.quit()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "the-human-race.png")
