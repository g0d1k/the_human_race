"""Sector definitions and scripted wave timelines.

A script is a list of (delay_seconds, wave, kwargs[, min_density]). Delays are
relative to the previous entry. Entries with a min_density only appear when
the difficulty level is at least that high (harder settings / later laps get
denser waves).
"""
import random

from config import PLAY_TOP, PLAY_BOTTOM

SPAWN_X = 258

SECTOR_INFO = {
    1: ("LUNAR OUTSKIRTS", "level1"),
    2: ("ASTEROID BELT", "level2"),
    3: ("JOVIAN STORM", "level3"),
    4: ("ICE RINGS", "level1"),
    5: ("NEBULA GRAVEYARD", "level2"),
    6: ("THE FINISH LINE", "level3"),
}

D = "drones"
DP = "drones_pair"
G = "gunners"
SP = "spreader"
DV = "divers"
ML = "minelayer"
WD = "warden"
SL = "splitters"
AS = "asteroids"

S1 = [
    (3, D, {"y": 80}), (5, D, {"y": 160}), (5, D, {"y": 120, "pattern": "line"}),
    (4, G, {"n": 2}), (6, D, {"y": 60, "pattern": "arc"}), (3, D, {"y": 190, "pattern": "arc"}),
    (6, G, {"n": 3}), (6, DP, {}), (6, SP, {"y": 120}), (6, D, {"y": 60}),
    (2, D, {"y": 190}, 1.2), (6, G, {"n": 2}), (5, D, {"y": 120, "pattern": "zig"}),
    (6, SP, {"y": 70}), (1, SP, {"y": 180}, 1.1), (7, DP, {}), (6, G, {"n": 4}),
    (7, D, {"y": 90}), (3, D, {"y": 150}), (6, SP, {"y": 120}), (2, G, {"n": 2}),
    (7, DP, {}), (5, D, {"y": 120, "pattern": "zig"}), (6, G, {"n": 3}),
    (5, SP, {"y": 60}), (0, SP, {"y": 190}), (7, D, {"y": 80, "pattern": "arc"}),
    (2, D, {"y": 170, "pattern": "arc"}), (6, G, {"n": 4}), (6, DP, {}),
    (4, D, {"y": 120}, 1.3),
]

S2 = [
    (3, AS, {"n": 4}), (4, D, {"y": 90}), (5, AS, {"n": 5}), (4, G, {"n": 2}),
    (6, DV, {"n": 2}), (6, AS, {"n": 6}), (5, D, {"y": 170, "pattern": "zig"}),
    (5, DV, {"n": 3}), (6, SP, {"y": 120}), (5, AS, {"n": 6}), (3, D, {"y": 60}),
    (6, ML, {"y": 80}), (5, G, {"n": 3}), (6, DV, {"n": 2}), (1, DV, {"n": 2}, 1.3),
    (6, AS, {"n": 8}), (6, DP, {}), (6, SP, {"y": 70}), (0, SP, {"y": 180}),
    (7, DV, {"n": 3}), (6, AS, {"n": 6}), (4, ML, {"y": 170}), (6, G, {"n": 4}),
    (6, D, {"y": 120, "pattern": "arc"}), (5, AS, {"n": 8}), (5, DV, {"n": 4}),
    (7, DP, {}), (6, SP, {"y": 120}), (3, ML, {"y": 60}, 1.25), (6, AS, {"n": 10}),
    (6, G, {"n": 3}),
]

S3 = [
    (3, D, {"y": 70}), (3, D, {"y": 180}), (5, ML, {"y": 100}), (6, G, {"n": 3}),
    (6, DV, {"n": 3}), (6, WD, {"y": 110}), (9, DP, {}), (5, SP, {"y": 60}),
    (0, SP, {"y": 190}), (6, ML, {"y": 160}), (4, D, {"y": 80, "pattern": "zig"}),
    (6, DV, {"n": 4}), (6, G, {"n": 4}), (6, WD, {"y": 70}), (2, D, {"y": 190}, 1.3),
    (8, DP, {}), (5, ML, {"y": 60}), (1, ML, {"y": 190}, 1.4), (6, SP, {"y": 120}),
    (6, DV, {"n": 3}), (5, G, {"n": 3}), (6, D, {"y": 120, "pattern": "arc"}),
    (5, WD, {"y": 160}), (8, DP, {}), (5, SP, {"y": 80}), (1, SP, {"y": 170}),
    (6, DV, {"n": 4}), (6, ML, {"y": 120}), (5, G, {"n": 4}), (6, DP, {}),
]

S4 = [
    (3, D, {"y": 80, "pattern": "zig"}), (4, SL, {"n": 2}), (6, G, {"n": 3}),
    (6, SP, {"y": 120}), (6, SL, {"n": 3}), (5, DV, {"n": 3}), (6, WD, {"y": 80}),
    (8, DP, {}), (5, ML, {"y": 170}), (5, SL, {"n": 3}), (6, SP, {"y": 60}),
    (0, SP, {"y": 190}), (6, G, {"n": 4}), (6, D, {"y": 120, "pattern": "arc"}),
    (3, SL, {"n": 2}, 1.4), (6, DV, {"n": 4}), (6, WD, {"y": 160}), (8, DP, {}),
    (5, SL, {"n": 4}), (6, ML, {"y": 70}), (1, ML, {"y": 180}), (6, SP, {"y": 120}),
    (5, G, {"n": 3}), (5, DV, {"n": 3}), (6, SL, {"n": 3}), (6, DP, {}),
    (5, WD, {"y": 120}), (8, SP, {"y": 70}), (0, SP, {"y": 180}), (6, G, {"n": 4}),
]

S5 = [
    (3, SL, {"n": 2}), (4, ML, {"y": 90}), (5, D, {"y": 160, "pattern": "zig"}),
    (5, DV, {"n": 3}), (6, WD, {"y": 120}), (8, SL, {"n": 3}), (5, ML, {"y": 60}),
    (1, ML, {"y": 190}), (6, G, {"n": 4}), (6, DP, {}), (5, SP, {"y": 120}),
    (5, DV, {"n": 4}), (6, SL, {"n": 4}), (6, WD, {"y": 70}), (2, WD, {"y": 170}, 1.6),
    (9, D, {"y": 80, "pattern": "arc"}), (2, D, {"y": 170, "pattern": "arc"}),
    (5, ML, {"y": 120}), (5, SP, {"y": 60}), (0, SP, {"y": 190}), (6, SL, {"n": 3}),
    (5, DV, {"n": 4}), (6, G, {"n": 4}), (6, WD, {"y": 120}), (8, DP, {}),
    (5, SL, {"n": 4}), (6, ML, {"y": 80}), (1, ML, {"y": 170}), (6, DV, {"n": 4}),
]

S6 = [
    (3, DP, {}), (4, G, {"n": 4}), (5, SL, {"n": 3}), (5, DV, {"n": 4}),
    (6, WD, {"y": 80}), (2, WD, {"y": 170}), (9, ML, {"y": 120}), (4, SP, {"y": 60}),
    (0, SP, {"y": 190}), (6, DP, {}), (4, SL, {"n": 4}), (5, DV, {"n": 4}),
    (6, G, {"n": 4}), (4, ML, {"y": 70}), (1, ML, {"y": 180}), (6, WD, {"y": 120}),
    (7, D, {"y": 70, "pattern": "zig"}), (1, D, {"y": 180, "pattern": "zig"}),
    (5, SP, {"y": 120}), (4, SL, {"n": 4}), (5, DV, {"n": 4}), (6, WD, {"y": 70}),
    (1, WD, {"y": 170}), (9, DP, {}), (4, G, {"n": 4}), (5, ML, {"y": 120}),
    (5, SL, {"n": 4}), (5, SP, {"y": 60}), (0, SP, {"y": 190}), (6, DV, {"n": 4}),
    (6, DP, {}),
]

SCRIPTS = {1: S1, 2: S2, 3: S3, 4: S4, 5: S5, 6: S6}


class SpawnEvent:
    __slots__ = ("t", "kind", "x", "y", "kw")

    def __init__(self, t, kind, x, y, kw):
        self.t = t
        self.kind = kind
        self.x = x
        self.y = y
        self.kw = kw


def _spread_ys(n, rng):
    lo = PLAY_TOP + 16
    hi = PLAY_BOTTOM - 32
    if n == 1:
        return [rng.randint(lo + 30, hi - 30)]
    step = (hi - lo) / float(n - 1)
    return [int(lo + step * i + rng.randint(-6, 6)) for i in range(n)]


def expand(wave, kw, t0, rng, make_formation):
    ev = []
    if wave in (D, DP):
        rows = [(kw.get("y", 120), kw.get("pattern", "sine"), 1)]
        if wave == DP:
            rows = [(70, "sine", 1), (180, "sine", -1)]
        for y, pattern, sign in rows:
            f = make_formation(5)
            for i in range(5):
                ev.append(SpawnEvent(t0 + i * 16, "drone", SPAWN_X, y,
                                     {"pattern": pattern, "amp": 22.0 * sign, "formation": f}))
    elif wave == G:
        n = kw.get("n", 2)
        ys = _spread_ys(n, rng)
        for i, y in enumerate(ys):
            ev.append(SpawnEvent(t0 + i * 30, "gunner", SPAWN_X, y, {"tx": 214 - (i % 2) * 34}))
    elif wave == SP:
        ev.append(SpawnEvent(t0, "spreader", SPAWN_X, kw.get("y", 120) - 7, {}))
    elif wave == DV:
        n = kw.get("n", 2)
        ys = _spread_ys(n, rng)
        rng.shuffle(ys)
        for i, y in enumerate(ys):
            ev.append(SpawnEvent(t0 + i * 45, "diver", SPAWN_X, y,
                                 {"tx": 196 - (i % 3) * 18, "ty": y}))
    elif wave == ML:
        ev.append(SpawnEvent(t0, "minelayer", SPAWN_X, kw.get("y", 120) - 7, {}))
    elif wave == WD:
        ev.append(SpawnEvent(t0, "warden", SPAWN_X, kw.get("y", 120) - 8, {"tx": 214}))
    elif wave == SL:
        n = kw.get("n", 2)
        ys = _spread_ys(n, rng)
        for i, y in enumerate(ys):
            ev.append(SpawnEvent(t0 + i * 40, "splitter", SPAWN_X, y, {}))
    elif wave == AS:
        n = kw.get("n", 4)
        for i in range(n):
            y = rng.randint(PLAY_TOP + 4, PLAY_BOTTOM - 20)
            ev.append(SpawnEvent(t0 + i * 22 + rng.randint(0, 10), "asteroid", SPAWN_X, y,
                                 {"vx": -rng.uniform(0.6, 1.3), "vy": rng.uniform(-0.25, 0.25)}))
    return ev


class LevelScript:
    """Turns a sector's script into a time-sorted list of spawn events."""

    def __init__(self, sector, diff, make_formation, seed=None):
        self.sector = sector
        self.frame = 0
        rng = random.Random(seed if seed is not None else sector * 1000 + 7)
        events = []
        t = 0
        for entry in SCRIPTS[sector]:
            delay, wave, kw = entry[0], entry[1], entry[2]
            min_density = entry[3] if len(entry) > 3 else 0
            # higher difficulty compresses the timeline slightly
            t += int(delay * 60 / (0.92 + 0.08 * diff.level))
            if diff.density < min_density:
                continue
            events.extend(expand(wave, kw, t, rng, make_formation))
        events.sort(key=lambda e: e.t)
        self.events = events
        self.index = 0
        self.length = events[-1].t if events else 0

    def update(self, spawn):
        self.frame += 1
        ev = self.events
        while self.index < len(ev) and ev[self.index].t <= self.frame:
            e = ev[self.index]
            self.index += 1
            spawn(e)

    @property
    def done(self):
        return self.index >= len(self.events)

    def skip_to_end(self):
        self.index = len(self.events)
