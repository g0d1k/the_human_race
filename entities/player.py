"""Player ships: ARES-1 (player 1, red) and GAIA-2 (player 2, green)."""
from config import PLAY_TOP, PLAY_BOTTOM, SCREEN_W

SPEEDS = (1.25, 1.6, 1.95, 2.3)
START_LIVES = 3
START_BOMBS = 2
MAX_BOMBS = 5
MAX_LIVES = 9
RESPAWN_DELAY = 80
INVULN_FRAMES = 120
NAMES = ("ARES-1", "GAIA-2")


class Player:
    def __init__(self, idx):
        self.idx = idx
        self.name = NAMES[idx]
        self.sprite_name = "ares" if idx == 0 else "gaia"
        self.state = "absent"        # absent | entering | alive | dead | out
        self.score = 0
        self.best_score = 0          # best score banked before a continue
        self.lives = 0
        self.bombs = 0
        self.weapon = 1
        self.laser = False
        self.speed_level = 0
        self.shield = False
        self.next_extra = 0
        self.x = -16.0
        self.y = 120.0
        self.timer = 0
        self.invuln = 0
        self.fire_cd = 0
        self.anim = 0
        self.deaths_this_sector = 0
        self.joined = False

    # ------------------------------------------------------------------
    def join(self, extra_life_step):
        """Start (or restart after a continue) with fresh lives."""
        self.joined = True
        self.lives = START_LIVES
        self.bombs = START_BOMBS
        self.weapon = 1
        self.laser = False
        self.speed_level = 0
        self.shield = False
        self.next_extra = self.score - (self.score % extra_life_step) + extra_life_step
        self.spawn()

    def spawn(self):
        self.state = "entering"
        self.x = -18.0
        self.y = float(60 + self.idx * 90)
        self.invuln = INVULN_FRAMES
        self.fire_cd = 10
        self.timer = 0

    def reset_position(self):
        """Fly back in at the start of a new sector."""
        if self.state in ("alive", "entering", "dead") and self.lives > 0:
            self.spawn()

    @property
    def in_play(self):
        return self.state in ("alive", "entering")

    @property
    def can_be_hit(self):
        return self.state == "alive" and self.invuln <= 0

    @property
    def active_in_game(self):
        """Still has ships left (alive, flying in, or waiting to respawn)."""
        return self.state in ("alive", "entering", "dead")

    def hitbox(self):
        # small hitbox around the cockpit (standard shmup convention)
        return (self.x + 6, self.y + 6, 4, 4)

    def body_rect(self):
        return (self.x + 1, self.y + 3, 14, 10)

    def center(self):
        return self.x + 8, self.y + 8

    # ------------------------------------------------------------------
    def update(self, held, pressed, world):
        self.anim += 1
        if self.invuln > 0:
            self.invuln -= 1
        if self.fire_cd > 0:
            self.fire_cd -= 1
        if self.state == "entering":
            self.x += 2.0
            if self.x >= 20:
                self.state = "alive"
            # allow firing while flying in
            if "fire" in held and self.fire_cd <= 0:
                world.player_fire(self)
            return
        if self.state == "dead":
            self.timer -= 1
            if self.timer <= 0:
                if self.lives > 0:
                    self.spawn()
                else:
                    self.state = "out"
            return
        if self.state != "alive":
            return
        sp = SPEEDS[self.speed_level]
        dx = dy = 0.0
        if "left" in held:
            dx -= 1
        if "right" in held:
            dx += 1
        if "up" in held:
            dy -= 1
        if "down" in held:
            dy += 1
        if dx and dy:
            dx *= 0.7071
            dy *= 0.7071
        self.x = max(0.0, min(SCREEN_W - 16.0, self.x + dx * sp))
        self.y = max(float(PLAY_TOP), min(PLAY_BOTTOM - 16.0, self.y + dy * sp))
        if "fire" in held and self.fire_cd <= 0:
            world.player_fire(self)
        if "bomb" in pressed and self.bombs > 0:
            self.bombs -= 1
            world.bomb(self)

    def add_score(self, pts, world, step):
        if pts <= 0:
            return
        self.score = min(9999999, self.score + pts)
        while self.score >= self.next_extra:
            self.next_extra += step
            if self.lives < MAX_LIVES:
                self.lives += 1
            world.extra_life(self)

    def kill(self, world):
        """Called when hit. Returns True if the ship was destroyed."""
        if not self.can_be_hit:
            return False
        if self.shield:
            self.shield = False
            self.invuln = 60
            world.audio.play("shield_break")
            return False
        self.state = "dead"
        self.timer = RESPAWN_DELAY
        self.lives -= 1
        self.deaths_this_sector += 1
        self.weapon = max(1, self.weapon - 1)
        self.speed_level = 0
        world.player_died(self)
        return True

    def draw(self, surf, sprites):
        if not self.in_play:
            return
        if self.invuln > 0 and (self.invuln >> 2) & 1 and self.state == "alive":
            return
        x = int(self.x)
        y = int(self.y)
        spr = sprites[self.sprite_name]
        flame = sprites["flame%d" % ((self.anim >> 2) & 1)]
        surf.blit(flame.img, (x - 7, y + 6))
        surf.blit(spr.img, (x, y))
        if self.shield:
            sh = sprites["shield%d" % ((self.anim >> 3) & 1)]
            surf.blit(sh.img, (x - 2, y - 2))
