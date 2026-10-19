"""Window management: 256x240 internal surface, integer nearest-neighbour
scaling, letterboxing, fullscreen, optional CRT scanlines and screen shake."""
import pygame

from config import SCREEN_W, SCREEN_H, TITLE, rgb, BLACK, dim_index, NES_PALETTE


class Display:
    def __init__(self, settings):
        self.settings = settings
        self.surface = pygame.Surface((SCREEN_W, SCREEN_H))
        self.window = None
        self.scaled = None
        self.scale = 1
        self.dest = (0, 0)
        self.scanline_overlay = None
        pygame.display.set_caption(TITLE)
        self.apply_mode()
        self.surface = self.surface.convert()

    def apply_mode(self):
        fullscreen = self.settings["fullscreen"]
        try:
            if fullscreen:
                self.window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            else:
                s = self.settings["scale"]
                # don't open a window larger than the desktop
                try:
                    sizes = pygame.display.get_desktop_sizes()
                    if sizes:
                        dw, dh = sizes[0]
                        while s > 1 and (SCREEN_W * s > dw or SCREEN_H * s > dh - 40):
                            s -= 1
                except (AttributeError, pygame.error):
                    pass
                self.window = pygame.display.set_mode((SCREEN_W * s, SCREEN_H * s))
        except pygame.error:
            self.settings["fullscreen"] = False
            self.window = pygame.display.set_mode((SCREEN_W * 2, SCREEN_H * 2))
        w, h = self.window.get_size()
        self.scale = max(1, min(w // SCREEN_W, h // SCREEN_H))
        sw, sh = SCREEN_W * self.scale, SCREEN_H * self.scale
        self.dest = ((w - sw) // 2, (h - sh) // 2)
        self.scaled = pygame.Surface((sw, sh)).convert()
        self._build_scanlines()
        self.window.fill(rgb(BLACK))

    def _build_scanlines(self):
        self.scanline_overlay = None
        if self.scale < 2:
            return
        sw, sh = self.scaled.get_size()
        key = (255, 0, 255)
        ov = pygame.Surface((sw, sh)).convert()
        ov.fill(key)
        ov.set_colorkey(key)
        dark = rgb(BLACK)
        thick = max(1, self.scale // 3)
        for y in range(self.scale - thick, sh, self.scale):
            ov.fill(dark, (0, y, sw, thick))
        self.scanline_overlay = ov

    def toggle_fullscreen(self):
        self.settings["fullscreen"] = not self.settings["fullscreen"]
        self.apply_mode()
        self.settings.save()

    def present(self, shake_x=0, shake_y=0):
        pygame.transform.scale(self.surface, self.scaled.get_size(), self.scaled)
        dx, dy = self.dest
        if shake_x or shake_y or dx or dy:
            self.window.fill(rgb(BLACK))
        self.window.blit(self.scaled, (dx + shake_x * self.scale, dy + shake_y * self.scale))
        if self.settings["scanlines"] and self.scanline_overlay is not None:
            self.window.blit(self.scanline_overlay, (dx + shake_x * self.scale, dy + shake_y * self.scale))
        pygame.display.flip()


def dim_surface(src, steps=1):
    """Return a copy of `src` darkened through the NES palette (no alpha).

    Each palette colour is swapped for the colour one row darker. Rows are
    processed darkest-first so that replaced pixels are never re-replaced.
    """
    out = src.copy()
    for _ in range(steps):
        try:
            pa = pygame.PixelArray(out)
        except (pygame.error, ValueError):
            return out
        done = set()
        black = rgb(BLACK)
        for row in range(4):
            for col in range(16):
                idx = row * 16 + col
                c = NES_PALETTE[idx]
                if c in done or c == black:
                    continue
                done.add(c)
                target = NES_PALETTE[dim_index(idx)]
                # colours already produced this pass belong to lower rows,
                # which have been processed, so this is safe.
                pa.replace(c, target)
        del pa
    return out
