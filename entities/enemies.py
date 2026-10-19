"""The Vexari fleet: seven enemy types (plus splitter fragments and asteroids).

Every enemy fires back with its own pattern. Behaviour is a small state
machine per type; all speeds, fire rates and HP scale with Difficulty.
"""
import math

from config import SCREEN_W, PLAY_TOP, PLAY_BOTTOM

# kind: (sprite, base hp, points, hitbox inset)
ENEMY_DEFS = {
    "drone": ("drone", 1, 100, 1),
    "gunner": ("gunner", 4, 300, 2),
    "spreader": ("spreader", 6, 400, 2),
    "diver": ("diver", 3, 350, 2),
    "minelayer": ("minelayer", 5, 500, 2),
    "warden": ("warden", 30, 1500, 2),
    "splitter": ("splitter", 6, 300, 3),
    "splitlet": ("splitlet", 1, 150, 1),
    "asteroid": ("asteroid", 4, 50, 2),
    "asteroid_s": ("asteroid_s", 1, 25, 1),
}

# Shown in HOW TO PLAY: (kind, display name, description)
GALLERY = (
    ("drone", "DRONE", "FLIES IN WAVES OF 5"),
    ("gunner", "GUNNER", "STOPS AND AIMS AT YOU"),
    ("spreader", "SPREADER", "FIRES A SPREAD FAN"),
    ("diver", "DIVER", "FLASHES, THEN DIVES"),
    ("minelayer", "MINELAYER", "MINES BURST INTO 8"),
    ("warden", "WARDEN", "ARMORED. LASER BEAM"),
    ("splitter", "SPLITTER", "SPLITS IN TWO"),
    ("splitlet", "SPLITLET", "FAST AIMED SHOTS"),
)


class Enemy:
    __slots__ = ("active", "kind", "x", "y", "vx", "vy", "hp", "t", "state", "st",
                 "flash", "cd", "spr", "w", "h", "points", "formation", "base_y",
                 "amp", "freq", "pattern", "tx", "ty", "shots", "cycles", "inset",
                 "laser_cd", "speed", "dead", "beam", "index")

    def __init__(self, index):
        self.index = index
        self.active = False
        self.beam = None


class EnemyPool:
    def __init__(self, cap, sprites):
        self.items = [Enemy(i) for i in range(cap)]
        self.sprites = sprites

    def spawn(self, kind, x, y, world, **kw):
        for e in self.items:
            if not e.active:
                self._reset(e, kind, x, y, world, kw)
                return e
        return None

    def _reset(self, e, kind, x, y, world, kw):
        sprname, hp, pts, inset = ENEMY_DEFS[kind]
        spr = self.sprites[sprname]
        d = world.diff
        e.active = True
        e.dead = False
        e.kind = kind
        e.spr = spr
        e.w = spr.w
        e.h = spr.h
        e.x = float(x)
        e.y = float(y)
        e.vx = kw.get("vx", 0.0)
        e.vy = kw.get("vy", 0.0)
        e.hp = d.enemy_hp(hp) if kind not in ("asteroid_s", "splitlet", "drone") else hp
        e.points = pts
        e.inset = inset
        e.t = 0
        e.state = 0
        e.st = 0
        e.flash = -5
        e.laser_cd = 0
        e.shots = 0
        e.cycles = 0
        e.base_y = float(y)
        e.amp = kw.get("amp", 24.0)
        e.freq = kw.get("freq", 0.045)
        e.pattern = kw.get("pattern", "sine")
        e.tx = kw.get("tx", 190.0)
        e.ty = kw.get("ty", y)
        e.speed = kw.get("speed", 1.0)
        e.formation = kw.get("formation")
        e.beam = None
        rng = world.rng
        e.cd = d.cooldown(rng.randint(40, 110))

    def clear(self):
        for e in self.items:
            e.active = False

    def count(self):
        n = 0
        for e in self.items:
            if e.active:
                n += 1
        return n


def hitbox(e):
    i = e.inset
    return (e.x + i, e.y + i, e.w - 2 * i, e.h - 2 * i)


def center(e):
    return e.x + e.w * 0.5, e.y + e.h * 0.5


def _leave_check(e, world):
    if e.x < -e.w - 12 or e.x > SCREEN_W + 40 or e.y < -40 or e.y > 280:
        world.enemy_escaped(e)


def _can_fire(e):
    return 16 < e.x < SCREEN_W - 12


# ---------------------------------------------------------------------------
# Behaviours
# ---------------------------------------------------------------------------
def u_drone(e, w):
    d = w.diff
    e.x -= 1.05 * d.speed * e.speed
    if e.pattern == "sine":
        e.y = e.base_y + e.amp * math.sin(e.t * e.freq)
    elif e.pattern == "arc":
        # swoop: descend/ascend toward the centre line then level out
        k = min(1.0, e.t / 120.0)
        e.y = e.base_y + (120 - e.base_y) * (1 - (1 - k) ** 2) * 0.7
    elif e.pattern == "zig":
        e.y = e.base_y + (e.amp if (e.t // 40) & 1 else -e.amp) * min(1.0, (e.t % 40) / 20.0)
    e.cd -= 1
    if e.cd <= 0:
        e.cd = d.cooldown(w.rng.randint(110, 220))
        if _can_fire(e) and w.rng.random() < 0.55:
            cx, cy = center(e)
            if w.rng.random() < d.aim * 0.35:
                w.fire_aimed("small", cx - 4, cy, 1.4 * d.bullet_speed)
            else:
                w.fire("small", cx - 4, cy, -1.5 * d.bullet_speed, 0)
    _leave_check(e, w)


def u_gunner(e, w):
    d = w.diff
    cx, cy = center(e)
    if e.state == 0:          # enter and brake
        dist = e.x - e.tx
        e.x -= max(0.5, dist * 0.06) * d.speed
        if dist <= 1:
            e.state = 1
            e.st = 0
            e.shots = 3 + int(d.level)
    elif e.state == 1:        # stop and aim
        e.st += 1
        gap = max(14, int(34 / d.fire_rate))
        if e.st % gap == 0 and e.shots > 0:
            w.fire_aimed("aimed", cx - 6, cy, 1.9 * d.bullet_speed)
            e.shots -= 1
        if e.shots <= 0 and e.st % gap == gap // 2:
            e.state = 2
            e.vy = -0.6 if cy > 120 else 0.6
    else:                     # retreat
        e.x += 1.3 * d.speed
        e.y += e.vy
    _leave_check(e, w)


def u_spreader(e, w):
    d = w.diff
    e.x -= 0.55 * d.speed * e.speed
    e.y = e.base_y + 10 * math.sin(e.t * 0.03)
    e.cd -= 1
    if e.cd <= 0:
        e.cd = d.cooldown(120)
        if _can_fire(e):
            cx, cy = center(e)
            n = d.spread_count
            aimed = w.rng.random() < d.aim
            w.fire_fan("big", cx - 6, cy, n, 15.0, 1.4 * d.bullet_speed, None if aimed else 180.0)
    _leave_check(e, w)


def u_diver(e, w):
    d = w.diff
    cx, cy = center(e)
    if e.state == 0:          # fly to hover point
        e.x -= max(0.6, (e.x - e.tx) * 0.05) * d.speed
        e.y += (e.ty - e.y) * 0.05
        if e.x - e.tx < 2:
            e.state = 1
            e.st = 0
    elif e.state == 1:        # hover
        e.st += 1
        e.y += math.sin(e.t * 0.1) * 0.3
        if e.st > 24:
            e.state = 2
            e.st = 0
            w.audio.play("warn_beep")
    elif e.state == 2:        # warning flash
        e.st += 1
        if e.st > max(22, int(44 / d.speed)):
            e.state = 3
            e.st = 0
            e.shots = 3 if d.level < 1.6 else 4
    elif e.state == 3:        # short burst
        e.st += 1
        if e.st % 6 == 1 and e.shots > 0:
            w.fire_aimed("aimed", cx - 6, cy, 2.0 * d.bullet_speed)
            e.shots -= 1
        if e.shots <= 0:
            e.state = 4
            dx, dy = w.aim(cx, cy)
            sp = 3.0 * d.speed
            e.vx = dx * sp
            e.vy = dy * sp
            if e.vx > -0.8:
                e.vx = -0.8
    else:                     # dive
        e.x += e.vx
        e.y += e.vy
    _leave_check(e, w)


def u_minelayer(e, w):
    d = w.diff
    e.x -= 0.5 * d.speed * e.speed
    e.y = e.base_y + 16 * math.sin(e.t * 0.02)
    e.cd -= 1
    if e.cd <= 0:
        e.cd = d.cooldown(95)
        if 24 < e.x < SCREEN_W - 20:
            cx, cy = center(e)
            w.drop_mine(cx - 4, cy - 4, -0.35, 0.0, 80 + w.rng.randint(0, 30))
    _leave_check(e, w)


def u_warden(e, w):
    d = w.diff
    cx, cy = center(e)
    if e.state == 0:          # enter
        e.x -= max(0.4, (e.x - e.tx) * 0.04) * d.speed
        if e.x - e.tx < 1:
            e.state = 1
            e.st = 0
    elif e.state == 1:        # track the nearest player's height
        e.st += 1
        p = w.nearest_player(cx, cy)
        if p is not None:
            py = p.y + 8
            step = 0.7 * d.speed
            if py > cy + 1:
                e.y += step
            elif py < cy - 1:
                e.y -= step
        e.y = max(PLAY_TOP + 4.0, min(PLAY_BOTTOM - e.h - 4.0, e.y))
        if e.st > 50:
            e.state = 2
            e.st = 0
            warn = max(30, int(56 / d.speed))
            e.beam = w.add_beam(e, 0, e.h // 2, 8, warn, 46, (0x16, 0x26, 0x30))
            w.audio.play("laser_charge")
            e.shots = warn + 46
    elif e.state == 2:        # telegraph + beam (beam object handles timing)
        e.st += 1
        if e.st >= e.shots:
            e.state = 3
            e.st = 0
            e.cycles += 1
    elif e.state == 3:        # cool down; pepper with aimed shots on higher levels
        e.st += 1
        if d.level > 1.2 and e.st in (10, 22):
            w.fire_aimed("aimed", cx - 14, cy, 1.8 * d.bullet_speed)
        if e.st > 45:
            if e.cycles >= 3:
                e.state = 4
            else:
                e.state = 1
                e.st = 0
    else:                     # retreat
        e.x += 0.9
    _leave_check(e, w)


def u_splitter(e, w):
    d = w.diff
    e.x -= 0.8 * d.speed * e.speed
    e.y = e.base_y + 18 * math.sin(e.t * 0.04)
    e.cd -= 1
    if e.cd <= 0:
        e.cd = d.cooldown(140)
        if _can_fire(e):
            cx, cy = center(e)
            w.fire_aimed("small", cx - 6, cy, 1.6 * d.bullet_speed)
    _leave_check(e, w)


def u_splitlet(e, w):
    d = w.diff
    e.x += e.vx * d.speed
    e.y += e.vy
    e.vy *= 0.97
    if e.t in (22, 62) and (e.t == 22 or d.level > 1.3) and _can_fire(e):
        cx, cy = center(e)
        w.fire_aimed("aimed", cx - 2, cy, 2.1 * d.bullet_speed)
    _leave_check(e, w)


def u_asteroid(e, w):
    e.x += e.vx
    e.y += e.vy
    _leave_check(e, w)


UPDATERS = {
    "drone": u_drone, "gunner": u_gunner, "spreader": u_spreader, "diver": u_diver,
    "minelayer": u_minelayer, "warden": u_warden, "splitter": u_splitter,
    "splitlet": u_splitlet, "asteroid": u_asteroid, "asteroid_s": u_asteroid,
}


def update_enemy(e, w):
    e.t += 1
    if e.flash > -5:
        e.flash -= 1
    if e.laser_cd > 0:
        e.laser_cd -= 1
    UPDATERS[e.kind](e, w)


def draw_enemy(e, surf, sprites, frame):
    x = int(e.x)
    y = int(e.y)
    if e.flash > 0:
        surf.blit(e.spr.white, (x, y))
        return
    if e.kind == "diver" and e.state == 2 and (e.st >> 2) & 1:
        surf.blit(sprites["diver_warn"].img, (x, y))
        return
    surf.blit(e.spr.img, (x, y))
