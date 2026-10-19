"""Parallax starfield and procedurally drawn, dithered NES-style planets."""
import math
import random

import pygame

from config import rgb, SCREEN_W, SCREEN_H, BLACK

KEY = (255, 0, 255)

# 4x4 ordered (Bayer) dither matrix, values 0..15
BAYER = (
    (0, 8, 2, 10),
    (12, 4, 14, 6),
    (3, 11, 1, 9),
    (15, 7, 13, 5),
)


def _hash(x, y, seed):
    n = (x * 374761393 + y * 668265263 + seed * 2147483647) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return (n & 0xFFFF) / 65535.0


def _smooth_noise(x, y, seed, scale):
    """Cheap value noise (bilinear) used for continents, clouds and bands."""
    fx = x / scale
    fy = y / scale
    ix = int(math.floor(fx))
    iy = int(math.floor(fy))
    tx = fx - ix
    ty = fy - iy
    a = _hash(ix, iy, seed)
    b = _hash(ix + 1, iy, seed)
    c = _hash(ix, iy + 1, seed)
    d = _hash(ix + 1, iy + 1, seed)
    top = a + (b - a) * tx
    bot = c + (d - c) * tx
    return top + (bot - top) * ty


def _shade_pick(shades, value, x, y):
    """Quantise value (0..1) to the shade list using ordered dithering."""
    n = len(shades)
    v = max(0.0, min(0.999, value)) * (n - 1)
    base = int(v)
    frac = v - base
    if base < n - 1 and frac * 16 > BAYER[y & 3][x & 3]:
        base += 1
    return shades[base]


PLANET_STYLES = {
    # shades go dark -> light (NES palette indices)
    "moon": {"shades": (0x2D, 0x00, 0x10, 0x3D), "craters": True},
    "earth": {"shades": (0x01, 0x11, 0x21, 0x31), "land": (0x09, 0x19, 0x29), "clouds": True},
    "desert": {"shades": (0x07, 0x17, 0x27, 0x37), "bands": (0x06, 0x17, 0x27)},
    "gas": {"shades": (0x07, 0x07, 0x17, 0x27), "stripes": (0x07, 0x17, 0x07, 0x27, 0x06, 0x16)},
    "gasmoon": {"shades": (0x08, 0x18, 0x28, 0x38), "craters": True},
    "ice": {"shades": (0x01, 0x11, 0x21, 0x31), "stripes": (0x11, 0x21, 0x31, 0x3C, 0x2C, 0x21),
            "rings": (0x0C, 0x1C, 0x2C, 0x3C)},
    "violet": {"shades": (0x03, 0x13, 0x23, 0x33), "bands": (0x04, 0x14, 0x24)},
    "redgiant": {"shades": (0x06, 0x06, 0x16, 0x16, 0x26), "star": True},
    "vexari": {"shades": (0x04, 0x14, 0x24, 0x34), "land": (0x0A, 0x1A, 0x2A), "rings": (0x05, 0x15, 0x25, 0x35)},
}


_PLANET_CACHE = {}


def make_planet(radius, style, seed=1):
    """Render a dithered planet (cached) to a colour-keyed Surface."""
    key = (radius, style, seed)
    surf = _PLANET_CACHE.get(key)
    if surf is None:
        surf = _render_planet(radius, style, seed)
        _PLANET_CACHE[key] = surf
    return surf


def _render_planet(radius, style, seed):
    st = PLANET_STYLES[style]
    rings = st.get("rings")
    ring_outer = radius * 1.9 if rings else radius
    w = int(ring_outer * 2) + 4
    h = int(radius * 2) + 4
    if rings:
        h = max(h, int(ring_outer * 0.55 * 2) + 4)
    surf = pygame.Surface((w, h))
    surf.fill(KEY)
    cx = w / 2.0
    cy = h / 2.0
    shades = st["shades"]
    lx, ly, lz = -0.55, -0.45, 0.70   # light from the upper-left
    craters = []
    if st.get("craters"):
        rnd = random.Random(seed)
        for _ in range(int(radius * 0.5) + 3):
            craters.append((rnd.uniform(-0.8, 0.8) * radius, rnd.uniform(-0.8, 0.8) * radius,
                            rnd.uniform(0.06, 0.2) * radius))
    pa = pygame.PixelArray(surf)
    ring_tilt = 0.28

    def ring_color(x, y):
        dx = x - cx
        dy = (y - cy) / ring_tilt
        d = math.sqrt(dx * dx + dy * dy)
        if radius * 1.25 <= d <= ring_outer:
            t = (d - radius * 1.25) / (ring_outer - radius * 1.25)
            band = int(t * 7)
            if band in (2, 5):
                return None   # gaps in the ring
            if _hash(int(d), 0, seed) < 0.15:
                return None
            idx = 3 - min(3, int(abs(math.sin(t * 9.0)) * 3.2))
            return rings[max(0, min(3, idx))]
        return None

    for y in range(h):
        for x in range(w):
            dx = (x + 0.5 - cx)
            dy = (y + 0.5 - cy)
            d2 = dx * dx + dy * dy
            in_planet = d2 <= radius * radius
            if rings and not in_planet:
                rc = ring_color(x + 0.5, y + 0.5)
                if rc is not None:
                    pa[x, y] = rgb(rc)
                continue
            if not in_planet:
                continue
            if rings and dy > 0:
                rc = ring_color(x + 0.5, y + 0.5)
                if rc is not None:      # front half of the ring passes over the planet
                    pa[x, y] = rgb(rc)
                    continue
            nx = dx / radius
            ny = dy / radius
            nz = math.sqrt(max(0.0, 1.0 - nx * nx - ny * ny))
            light = nx * lx + ny * ly + nz * lz
            light = max(0.0, light)
            if st.get("star"):
                value = 0.35 + 0.65 * nz + (_smooth_noise(x, y, seed, 6) - 0.5) * 0.35
                pa[x, y] = rgb(_shade_pick(shades, value, x, y))
                continue
            palette = shades
            value = light
            if "stripes" in st:
                stripes = st["stripes"]
                wob = math.sin(nx * 5 + seed) * 0.05 + (_smooth_noise(x, y, seed, 7) - 0.5) * 0.12
                band = int(((ny + wob) * 0.5 + 0.5) * len(stripes) * 2.0) % len(stripes)
                base = stripes[band]
                if light < 0.25:
                    c = shades[0] if _shade_pick((0, 1), light * 4, x, y) == 0 else base
                elif light > 0.9:
                    c = shades[-1] if (x + y) & 1 else base
                else:
                    c = base
                pa[x, y] = rgb(c)
                continue
            if "bands" in st:
                bands = st["bands"]
                bv = _smooth_noise(x * 0.4, y * 3, seed, 9)
                if bv > 0.62:
                    palette = (shades[0],) + tuple(bands)
            if "land" in st:
                lv = _smooth_noise(x, y, seed, max(4, radius / 3.0)) * 0.7 + _smooth_noise(x, y, seed + 7, 3) * 0.3
                if lv > 0.55:
                    palette = (shades[0],) + tuple(st["land"])
                if st.get("clouds") and _smooth_noise(x * 0.5, y * 2, seed + 3, 5) > 0.72:
                    palette = (shades[1], 0x10, 0x30)
            if craters:
                for (ccx, ccy, cr) in craters:
                    ex = dx - ccx
                    ey = dy - ccy
                    dd = ex * ex + ey * ey
                    if dd < cr * cr:
                        value *= 0.55 if dd > (cr * 0.6) ** 2 else 0.8
                        break
            pa[x, y] = rgb(_shade_pick(palette, value, x, y))
    del pa
    if pygame.display.get_surface() is not None:
        surf = surf.convert()
    surf.set_colorkey(KEY)
    return surf


_NEBULA_CACHE = {}


def make_nebula(w, h, seed, shades=(0x03, 0x03, 0x04, 0x13)):
    """Dithered purple nebula cloud layer (colour-keyed, cached)."""
    key = (w, h, seed, shades)
    if key not in _NEBULA_CACHE:
        _NEBULA_CACHE[key] = _render_nebula(w, h, seed, shades)
    return _NEBULA_CACHE[key]


def _render_nebula(w, h, seed, shades):
    surf = pygame.Surface((w, h))
    surf.fill(KEY)
    pa = pygame.PixelArray(surf)
    for y in range(h):
        for x in range(w):
            # tileable horizontally: blend noise with its wrapped neighbour
            t = x / float(w)
            v1 = _smooth_noise(x, y, seed, 22) * 0.6 + _smooth_noise(x, y, seed + 5, 9) * 0.4
            v2 = _smooth_noise(x + w, y, seed, 22) * 0.6 + _smooth_noise(x + w, y, seed + 5, 9) * 0.4
            v = v1 * (1 - t) + v2 * t
            edge = min(y, h - 1 - y) / (h * 0.25)
            v *= min(1.0, edge)
            if v > 0.5:
                val = (v - 0.5) / 0.3
                if val < 0.3 and BAYER[y & 3][x & 3] > val * 40:
                    continue
                pa[x, y] = rgb(_shade_pick(shades, val, x, y))
    del pa
    if pygame.display.get_surface() is not None:
        surf = surf.convert()
    surf.set_colorkey(KEY)
    return surf


class Starfield:
    """Three star layers scrolling right-to-left at different speeds."""
    LAYERS = (
        (40, 0.25, (0x2D, 0x00)),
        (28, 0.6, (0x10, 0x00)),
        (14, 1.4, (0x30, 0x3D)),
    )

    def __init__(self, seed=7):
        rnd = random.Random(seed)
        self.layers = []
        for count, speed, colors in self.LAYERS:
            stars = [[rnd.uniform(0, SCREEN_W), rnd.randint(0, SCREEN_H - 1), rnd.choice(colors)]
                     for _ in range(count)]
            self.layers.append((stars, speed))
        self.speed = 1.0
        self.rnd = rnd
        self.frame = 0

    def update(self):
        self.frame += 1
        for stars, speed in self.layers:
            s = speed * self.speed
            for st in stars:
                st[0] -= s
                if st[0] < 0:
                    st[0] += SCREEN_W
                    st[1] = self.rnd.randint(0, SCREEN_H - 1)

    def draw(self, surf):
        for li, (stars, speed) in enumerate(self.layers):
            for x, y, c in stars:
                col = rgb(c)
                if li == 2:
                    streak = 1 + int(self.speed > 1.5) * 3
                    surf.fill(col, (int(x), y, 1 + streak, 1))
                else:
                    surf.fill(col, (int(x), y, 1, 1))


# Per-sector background definitions: list of (style, radius, y, seed) planets
SECTOR_PLANETS = {
    1: [("moon", 46, 170, 3), ("earth", 13, 60, 5)],
    2: [("desert", 38, 70, 9), ("moon", 10, 180, 11)],
    3: [("gas", 64, 120, 13), ("gasmoon", 9, 40, 17), ("gasmoon", 6, 200, 19)],
    4: [("ice", 30, 110, 23), ("moon", 8, 40, 29)],
    5: [("violet", 26, 80, 31)],
    6: [("redgiant", 76, 150, 37), ("vexari", 20, 60, 41)],
}


class SectorBackground:
    """Starfield + slowly drifting far-layer planets (+ nebula / wrecks)."""

    def __init__(self, sector, sprites=None):
        self.stars = Starfield(seed=sector * 11)
        self.sector = sector
        self.planets = []
        self.queue = []
        defs = SECTOR_PLANETS.get(sector, SECTOR_PLANETS[1])
        for i, (style, r, y, seed) in enumerate(defs):
            surf = make_planet(r, style, seed)
            self.queue.append([surf, y, 0.06 + 0.035 * i])
        # the first planet starts partly on screen so sectors have instant character
        self.active = []
        first = True
        for item in self.queue:
            surf, y, speed = item
            x = SCREEN_W * (0.55 if first else 1.15) + (0 if first else 40)
            self.active.append([surf, float(x), y, speed])
            first = False
        self.nebula = None
        self.nebula_x = 0.0
        self.wrecks = []
        self.sprites = sprites
        if sector == 5:
            self.nebula = make_nebula(256, 200, 99)
            rnd = random.Random(5)
            for _ in range(4):
                self.wrecks.append([rnd.uniform(0, 400), rnd.randint(30, 210), rnd.uniform(0.3, 0.5), rnd.random() < 0.5])
        self.frame = 0

    def update(self):
        self.frame += 1
        self.stars.update()
        for p in self.active:
            p[1] -= p[3] * self.stars.speed
            w = p[0].get_width()
            if p[1] < -w:
                # planet has drifted past: bring it back after a long gap
                p[1] = SCREEN_W + 120 + (self.frame % 7) * 30
        if self.nebula is not None:
            self.nebula_x -= 0.3 * self.stars.speed
            if self.nebula_x <= -256:
                self.nebula_x += 256
        for wr in self.wrecks:
            wr[0] -= wr[2] * self.stars.speed
            if wr[0] < -40:
                wr[0] = SCREEN_W + 60 + (self.frame % 5) * 25
                wr[1] = 30 + (self.frame * 37) % 180

    def draw(self, surf):
        surf.fill(rgb(BLACK))
        for p in self.active:
            img = p[0]
            surf.blit(img, (int(p[1]), int(p[2] - img.get_height() / 2)))
        if self.nebula is not None:
            x = int(self.nebula_x)
            surf.blit(self.nebula, (x, 24))
            surf.blit(self.nebula, (x + 256, 24))
        self.stars.draw(surf)
        if self.wrecks and self.sprites is not None:
            spr = self.sprites["wreck"]
            for x, y, sp, flip in self.wrecks:
                img = spr.flip_y.img if flip else spr.img
                surf.blit(img, (int(x), int(y)))
