"""Power-up capsules: float left slowly, blink before expiring."""
import math

from config import PLAY_TOP, PLAY_BOTTOM

LIFETIME = 600
BLINK_AT = 420

# drop weights
WEIGHTS = (("P", 34), ("L", 10), ("S", 14), ("B", 16), ("O", 14), ("1UP", 2))
TOTAL_WEIGHT = sum(w for _, w in WEIGHTS)

DESCRIPTIONS = (
    ("P", "POWER", "WEAPON LEVEL UP (MAX 4)"),
    ("L", "LASER", "PIERCING LASER WEAPON"),
    ("S", "SPEED", "SHIP SPEED UP (MAX 3)"),
    ("B", "BOMB", "+1 BOMB (MAX 5)"),
    ("O", "SHIELD", "ABSORBS ONE HIT"),
    ("1UP", "1UP", "EXTRA LIFE (RARE)"),
)


class PowerUp:
    __slots__ = ("active", "kind", "x", "y", "t", "base_y", "spr")

    def __init__(self):
        self.active = False


class PowerUpPool:
    def __init__(self, cap, sprites):
        self.items = [PowerUp() for _ in range(cap)]
        self.sprites = sprites

    def roll(self, rng):
        r = rng.random() * TOTAL_WEIGHT
        for kind, w in WEIGHTS:
            r -= w
            if r < 0:
                return kind
        return "P"

    def spawn(self, kind, x, y):
        for p in self.items:
            if not p.active:
                p.active = True
                p.kind = kind
                p.spr = self.sprites["pu_" + kind]
                p.x = float(min(232, x))
                p.y = float(max(PLAY_TOP + 8, min(PLAY_BOTTOM - 16, y)))
                p.base_y = p.y
                p.t = 0
                return p
        return None

    def update(self):
        for p in self.items:
            if p.active:
                p.t += 1
                p.x -= 0.35
                p.y = p.base_y + 4 * math.sin(p.t * 0.06)
                if p.t > LIFETIME or p.x < -24:
                    p.active = False

    def draw(self, surf):
        for p in self.items:
            if p.active:
                if p.t > BLINK_AT and (p.t >> 2) & 1:
                    continue
                surf.blit(p.spr.img, (int(p.x), int(p.y)))

    def clear(self):
        for p in self.items:
            p.active = False
