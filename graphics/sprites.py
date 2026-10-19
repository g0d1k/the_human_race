"""Converts text-grid sprite data into pre-rendered Surfaces (once, at startup)."""
import pygame

from config import rgb, WHITE
from graphics import sprite_data as D
from graphics.font import GLYPHS

KEY = (255, 0, 255)   # colour key (not an NES colour, so black can be used in art)


class Sprite:
    """A pre-rendered sprite with its white hit-flash silhouette."""
    __slots__ = ("img", "white", "w", "h", "flip_y", "flip_x")

    def __init__(self, img, white):
        self.img = img
        self.white = white
        self.w, self.h = img.get_size()
        self.flip_y = None
        self.flip_x = None


def _finish(surf):
    if pygame.display.get_surface() is not None:
        surf = surf.convert()
    surf.set_colorkey(KEY)
    return surf


def grid_surface(rows, colors):
    w = max(len(r) for r in rows)
    h = len(rows)
    surf = pygame.Surface((w, h))
    surf.fill(KEY)
    cols = [rgb(c) for c in colors]
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch in "123":
                surf.set_at((x, y), cols[ord(ch) - 49])
    return _finish(surf)


def silhouette(rows, color=WHITE):
    w = max(len(r) for r in rows)
    surf = pygame.Surface((w, len(rows)))
    surf.fill(KEY)
    c = rgb(color)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch in "123":
                surf.set_at((x, y), c)
    return _finish(surf)


def make(rows, colors, flips=False):
    spr = Sprite(grid_surface(rows, colors), silhouette(rows))
    if flips:
        spr.flip_y = Sprite(pygame.transform.flip(spr.img, False, True),
                            pygame.transform.flip(spr.white, False, True))
        spr.flip_x = Sprite(pygame.transform.flip(spr.img, True, False),
                            pygame.transform.flip(spr.white, True, False))
    return spr


POWERUP_TYPES = ("P", "L", "S", "B", "O", "1UP")
POWERUP_COLORS = {
    "P": (0x16, 0x30, 0x06),
    "L": (0x1C, 0x30, 0x0C),
    "S": (0x1A, 0x30, 0x0A),
    "B": (0x17, 0x30, 0x07),
    "O": (0x12, 0x30, 0x02),
    "1UP": (0x28, 0x30, 0x08),
}


def capsule(text, colors):
    """A pickup capsule with a font letter stamped in colour 2."""
    w = 8 * len(text) + 4
    rows = [list(r) for r in D.capsule_grid(w, 12)]
    for i, ch in enumerate(text):
        glyph = GLYPHS[ch]
        for gy in range(7):
            bits = glyph[gy]
            for gx in range(8):
                if bits & (0x80 >> gx):
                    rows[gy + 2][2 + i * 8 + gx] = "2"
    rows = ["".join(r) for r in rows]
    return make(rows, colors)


class SpriteBank:
    def __init__(self):
        s = {}
        s["ares"] = make(D.ARES, D.ARES_COLORS)
        s["gaia"] = make(D.GAIA, D.GAIA_COLORS)
        s["flame0"] = make(D.FLAME[0], D.FLAME_COLORS)
        s["flame1"] = make(D.FLAME[1], D.FLAME_COLORS)
        # longer flames for speed levels 1-3 (level 0 uses flame0/flame1)
        for lvl, length in ((1, 12), (2, 16), (3, 21)):
            for f in range(2):
                s["flame%d_%d" % (lvl, f)] = make(D.flame_grid(length, f), D.FLAME_COLORS)
        s["life1"] = make(D.LIFE_ICON, (0x16, 0x30, 0x10))
        s["life2"] = make(D.LIFE_ICON, (0x1A, 0x30, 0x10))
        s["bomb_icon"] = make(D.BOMB_ICON, D.BOMB_ICON_COLORS)
        s["shield0"] = make(D.SHIELD, (0x21, 0x31, 0x30))
        s["shield1"] = make(D.SHIELD, (0x31, 0x21, 0x30))

        s["drone"] = make(D.DRONE, D.DRONE_COLORS)
        s["gunner"] = make(D.GUNNER, D.GUNNER_COLORS)
        s["spreader"] = make(D.SPREADER, D.SPREADER_COLORS)
        s["diver"] = make(D.DIVER, D.DIVER_COLORS)
        s["diver_warn"] = make(D.DIVER, D.DIVER_WARN_COLORS)
        s["minelayer"] = make(D.MINELAYER, D.MINELAYER_COLORS)
        s["warden"] = make(D.WARDEN, D.WARDEN_COLORS)
        s["splitter"] = make(D.SPLITTER, D.SPLITTER_COLORS)
        s["splitlet"] = make(D.SPLITLET, D.SPLITLET_COLORS)
        s["asteroid"] = make(D.ASTEROID, D.ASTEROID_COLORS)
        s["asteroid_s"] = make(D.ASTEROID_SMALL, D.ASTEROID_COLORS)
        s["wreck"] = make(D.WRECK, D.WRECK_COLORS, flips=True)

        s["mine"] = make(D.MINE, D.MINE_COLORS)
        s["mine_lit"] = make(D.MINE, D.MINE_LIT_COLORS)
        s["b_small"] = make(D.BULLET_SMALL, (0x25, 0x30, 0x30))
        s["b_aimed"] = make(D.BULLET_SMALL, (0x27, 0x38, 0x38))
        s["b_ring"] = make(D.BULLET_SMALL, (0x2C, 0x30, 0x30))
        s["b_big"] = make(D.BULLET_BIG, (0x27, 0x38, 0x30))
        s["b_homing"] = make(D.BULLET_BIG, (0x2A, 0x30, 0x30))
        s["b_shard"] = make(D.BULLET_SHARD, (0x31, 0x30, 0x30))
        s["shot1"] = make(D.PLAYER_SHOT, (0x26, 0x30, 0x30))
        s["shot2"] = make(D.PLAYER_SHOT, (0x2A, 0x30, 0x30))
        s["rear1"] = make(D.PLAYER_SHOT_REAR, (0x26, 0x30, 0x30))
        s["rear2"] = make(D.PLAYER_SHOT_REAR, (0x2A, 0x30, 0x30))
        s["laser1"] = make(D.PLAYER_LASER, (0x2C, 0x30, 0x30))
        s["laser2"] = make(D.PLAYER_LASER, (0x3B, 0x30, 0x30))

        # Boss parts
        s["sentinel"] = make(D.SENTINEL, D.SENTINEL_COLORS)
        s["hive"] = make(D.HIVE, D.HIVE_COLORS)
        s["tempest"] = make(D.TEMPEST, D.TEMPEST_COLORS)
        s["cryo"] = make(D.CRYO, D.CRYO_COLORS)
        s["revenant"] = make(D.REVENANT, D.REVENANT_COLORS)
        s["arbiter"] = make(D.ARBITER, D.ARBITER_COLORS)
        s["eye_red"] = make(D.EYE16, (0x16, 0x30, 0x06))
        s["eye_green"] = make(D.EYE16, (0x1A, 0x38, 0x0A))
        s["eye_yellow"] = make(D.EYE16, (0x28, 0x30, 0x07))
        s["eye_cyan"] = make(D.EYE16, (0x2C, 0x30, 0x01))
        s["eye_violet"] = make(D.EYE16, (0x2A, 0x23, 0x0F))
        s["eye_arbiter"] = make(D.EYE24, (0x27, 0x38, 0x06))
        s["turret"] = make(D.TURRET_TOP, (0x17, 0x27, 0x07), flips=True)
        s["turret_ice"] = make(D.TURRET_TOP, (0x11, 0x31, 0x01), flips=True)

        # Pickups
        for t in POWERUP_TYPES:
            s["pu_" + t] = capsule(t, POWERUP_COLORS[t])

        # Explosions (small 16x16, big 32x32)
        pal = [(0x27, 0x38, 0x30), (0x16, 0x27, 0x38), (0x06, 0x16, 0x27), (0x00, 0x10, 0x10)]
        small = [D.explosion_grid(16, 3.5, 1, 11), D.explosion_grid(16, 6, 1.5, 23),
                 D.explosion_grid(16, 7.5, 2, 37), D.hollow_explosion_grid(16, 7.5, 2.5, 41)]
        big = [D.explosion_grid(32, 7, 2, 53), D.explosion_grid(32, 12, 3, 67),
               D.explosion_grid(32, 15, 4, 71), D.hollow_explosion_grid(32, 15.5, 4, 83)]
        for i in range(4):
            s["exp_s%d" % i] = make(small[i], pal[i])
            s["exp_b%d" % i] = make(big[i], pal[i])
        self.s = s

    def __getitem__(self, name):
        return self.s[name]
