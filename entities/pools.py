"""Fixed-size object pools: bullets, explosions, particles, beams, pop-up text.

Objects are allocated once and recycled, so the per-frame hot path never
allocates. Each pool caps how many objects can be alive at once, which keeps
performance stable on slow machines.
"""
import math

from config import rgb, SCREEN_W, SCREEN_H


class Bullet:
    __slots__ = ("active", "x", "y", "vx", "vy", "spr", "hw", "hh", "owner", "dmg",
                 "pierce", "kind", "timer", "homing", "speed", "index")

    def __init__(self, index):
        self.index = index
        self.active = False
        self.x = self.y = self.vx = self.vy = 0.0
        self.spr = None
        self.hw = self.hh = 1
        self.owner = 0
        self.dmg = 1
        self.pierce = False
        self.kind = ""
        self.timer = 0
        self.homing = 0
        self.speed = 0.0


# enemy bullet kinds: sprite name, hit half-width, hit half-height
ENEMY_BULLETS = {
    "small": ("b_small", 1, 1),
    "aimed": ("b_aimed", 1, 1),
    "ring": ("b_ring", 1, 1),
    "big": ("b_big", 2, 2),
    "homing": ("b_homing", 2, 2),
    "shard": ("b_shard", 3, 1),
    "mine": ("mine", 3, 3),
}


class BulletPool:
    def __init__(self, cap):
        self.items = [Bullet(i) for i in range(cap)]
        self.free = list(range(cap - 1, -1, -1))
        self.cap = cap

    def spawn(self):
        if not self.free:
            return None
        b = self.items[self.free.pop()]
        b.active = True
        b.timer = 0
        b.homing = 0
        b.pierce = False
        b.dmg = 1
        return b

    def kill(self, b):
        if b.active:
            b.active = False
            self.free.append(b.index)

    def clear(self):
        for b in self.items:
            if b.active:
                self.kill(b)

    def count(self):
        return self.cap - len(self.free)


class Explosion:
    __slots__ = ("active", "x", "y", "frame", "timer", "big", "delay", "index")

    def __init__(self, index):
        self.index = index
        self.active = False
        self.x = self.y = 0
        self.frame = 0
        self.timer = 0
        self.big = False
        self.delay = 0


class ExplosionPool:
    FRAME_TICKS = 5

    def __init__(self, cap, sprites):
        self.items = [Explosion(i) for i in range(cap)]
        self.small = [sprites["exp_s%d" % i] for i in range(4)]
        self.big = [sprites["exp_b%d" % i] for i in range(4)]

    def spawn(self, x, y, big=False, delay=0):
        for e in self.items:
            if not e.active:
                e.active = True
                e.x = int(x)
                e.y = int(y)
                e.big = big
                e.frame = 0
                e.timer = 0
                e.delay = delay
                return e
        return None

    def update(self):
        for e in self.items:
            if e.active:
                if e.delay > 0:
                    e.delay -= 1
                    continue
                e.timer += 1
                if e.timer >= self.FRAME_TICKS:
                    e.timer = 0
                    e.frame += 1
                    if e.frame >= 4:
                        e.active = False

    def draw(self, surf):
        for e in self.items:
            if e.active and e.delay <= 0:
                spr = (self.big if e.big else self.small)[e.frame]
                surf.blit(spr.img, (e.x - spr.w // 2, e.y - spr.h // 2))

    def clear(self):
        for e in self.items:
            e.active = False

    def any_active(self):
        return any(e.active for e in self.items)


class Particle:
    __slots__ = ("active", "x", "y", "vx", "vy", "life", "color")

    def __init__(self):
        self.active = False
        self.x = self.y = self.vx = self.vy = 0.0
        self.life = 0
        self.color = (0, 0, 0)


class ParticlePool:
    def __init__(self, cap):
        self.items = [Particle() for _ in range(cap)]
        self.next = 0
        self.cap = cap

    def spawn(self, x, y, vx, vy, life, color_index):
        # round-robin: when full, the oldest particle is recycled
        p = self.items[self.next]
        self.next = (self.next + 1) % self.cap
        p.active = True
        p.x = x
        p.y = y
        p.vx = vx
        p.vy = vy
        p.life = life
        p.color = rgb(color_index)

    def burst(self, x, y, count, speed, colors, rng, life=24):
        for i in range(count):
            a = rng.random() * math.tau
            s = speed * (0.4 + rng.random() * 0.8)
            self.spawn(x, y, math.cos(a) * s, math.sin(a) * s, life + rng.randint(-6, 6),
                       colors[i % len(colors)])

    def update(self):
        for p in self.items:
            if p.active:
                p.x += p.vx
                p.y += p.vy
                p.vx *= 0.96
                p.vy *= 0.96
                p.life -= 1
                if p.life <= 0:
                    p.active = False

    def draw(self, surf):
        for p in self.items:
            if p.active and (p.life > 6 or p.life & 1):
                surf.fill(p.color, (int(p.x), int(p.y), 1, 1))

    def clear(self):
        for p in self.items:
            p.active = False


class Beam:
    """A horizontal laser. Warns (thin blinking line), then fires (thick beam).
    It is anchored to an owner so it follows the emitter as it moves."""
    __slots__ = ("active", "owner", "ox", "oy", "thick", "warn", "fire", "timer",
                 "colors", "x_end", "y", "firing", "length")

    def __init__(self):
        self.active = False
        self.owner = None
        self.ox = self.oy = 0
        self.thick = 6
        self.warn = 0
        self.fire = 0
        self.timer = 0
        self.colors = (0x26, 0x38, 0x30)
        self.x_end = 0
        self.y = 0
        self.firing = False
        self.length = 0

    def hit_rect(self):
        h = self.thick // 2
        return (0, self.y - h, self.x_end, self.thick)


class BeamPool:
    def __init__(self, cap):
        self.items = [Beam() for _ in range(cap)]

    def spawn(self, owner, ox, oy, thick, warn, fire, colors=(0x26, 0x38, 0x30)):
        for b in self.items:
            if not b.active:
                b.active = True
                b.owner = owner
                b.ox = ox
                b.oy = oy
                b.thick = thick
                b.warn = warn
                b.fire = fire
                b.timer = 0
                b.colors = colors
                b.firing = False
                b.length = 0
                self._follow(b)
                return b
        return None

    @staticmethod
    def _follow(b):
        o = b.owner
        b.x_end = int(o.x + b.ox)
        b.y = int(o.y + b.oy)

    def update(self, audio):
        for b in self.items:
            if not b.active:
                continue
            o = b.owner
            if o is None or not o.active:
                b.active = False
                continue
            self._follow(b)
            b.timer += 1
            if b.timer == b.warn:
                b.firing = True
                audio.play("laser_fire")
            if b.firing:
                b.length = min(b.x_end, b.length + 24)
            if b.timer >= b.warn + b.fire:
                b.active = False
                b.firing = False

    def draw(self, surf, frame):
        for b in self.items:
            if not b.active:
                continue
            if not b.firing:
                if (b.timer // 3) & 1:
                    # dotted warning line
                    c = rgb(b.colors[0])
                    for x in range(b.x_end - 2, 0, -4):
                        surf.fill(c, (x, b.y, 2, 1))
            else:
                x0 = b.x_end - b.length
                h = b.thick
                y0 = b.y - h // 2
                outer, mid, core = (rgb(c) for c in b.colors)
                wob = (frame >> 1) & 1
                surf.fill(outer, (x0, y0 + wob, b.length, h - wob * 2))
                surf.fill(mid, (x0, y0 + 1 + wob, b.length, max(1, h - 2 - wob * 2)))
                surf.fill(core, (x0, b.y - 1, b.length, 2))

    def clear(self):
        for b in self.items:
            b.active = False
            b.firing = False

    def clear_owner(self, owner):
        for b in self.items:
            if b.owner is owner:
                b.active = False
                b.firing = False


class Popup:
    __slots__ = ("active", "text", "x", "y", "timer", "color")

    def __init__(self):
        self.active = False
        self.text = ""
        self.x = self.y = 0
        self.timer = 0
        self.color = 0x30


class PopupPool:
    def __init__(self, cap):
        self.items = [Popup() for _ in range(cap)]

    def spawn(self, text, x, y, color=0x30, frames=60):
        for p in self.items:
            if not p.active:
                p.active = True
                p.text = text
                p.x = max(0, min(SCREEN_W - len(text) * 8, int(x - len(text) * 4)))
                p.y = int(y)
                p.timer = frames
                p.color = color
                return

    def update(self):
        for p in self.items:
            if p.active:
                p.timer -= 1
                if p.timer % 3 == 0:
                    p.y -= 1
                if p.timer <= 0:
                    p.active = False

    def draw(self, surf, font):
        for p in self.items:
            if p.active and (p.timer > 20 or p.timer & 2):
                font.draw(surf, p.text, p.x, max(18, p.y), p.color, shadow=0x0F)

    def clear(self):
        for p in self.items:
            p.active = False


def offscreen(x, y, margin=24):
    return x < -margin or x > SCREEN_W + margin or y < -margin or y > SCREEN_H + margin
