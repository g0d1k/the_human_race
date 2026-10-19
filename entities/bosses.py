"""The six Vexari champions. Each boss is a composite of several sprites,
has a health bar and changes attack patterns as its HP drops."""
import math

from config import SCREEN_W, PLAY_TOP, PLAY_BOTTOM

MID_Y = (PLAY_TOP + PLAY_BOTTOM) // 2


class Boss:
    name = "BOSS"
    hull = "sentinel"
    base_hp = 400
    phases = 2
    eye = "eye_red"
    eye_pos = (0, 0)
    turret = None
    turret_pos = None     # (dx, dy_top, dy_bottom)
    # Per-boss intensity curve: tempo stretches (<1) or compresses (>1) the
    # attack timings; speed_mult scales this boss's bullet speed.
    tempo = 1.0
    speed_mult = 1.0

    def __init__(self, world):
        self.world = world
        spr = world.sprites[self.hull]
        self.hull_spr = spr
        self.w = spr.w
        self.h = spr.h
        self.x = float(SCREEN_W + 10)
        self.home_y = float(MID_Y - self.h // 2)
        self.y = self.home_y
        self.home_x = float(SCREEN_W - self.w - 8)
        self.max_hp = max(50, int(self.base_hp * world.diff.boss_hp))
        self.hp = self.max_hp
        self.t = 0
        self.ft = 0
        self.state = "enter"
        self.phase = 0
        self.flash = 0
        self.flash_cd = 0
        self.invuln = 0
        self.visible = True
        self.active = True
        self.laser_cd = 0
        self.warn = False
        self.dying_t = 0
        # teleport helpers (Revenant / Arbiter)
        self.mode = "show"
        self.mt = 0

    # ------------------------------------------------------------------
    @property
    def cx(self):
        return self.x + self.w * 0.5

    @property
    def cy(self):
        return self.y + self.h * 0.5

    @property
    def hittable(self):
        return (self.state == "fight" and self.invuln <= 0 and self.visible
                and self.x < SCREEN_W - 8)

    def hit_rect(self):
        return (self.x + 6, self.y + 6, self.w - 12, self.h - 12)

    def body_rect(self):
        return (self.x + 8, self.y + 8, self.w - 16, self.h - 16)

    def P(self, frames):
        """An attack period/duration adjusted by this boss's tempo."""
        return max(1, int(round(frames / self.tempo)))

    def ratio(self):
        return self.hp / float(self.max_hp)

    def damage(self, n):
        if not self.hittable:
            return False
        self.hp -= n
        if self.flash_cd <= 0:
            self.flash = 2
            self.flash_cd = 7
        if self.t % 4 == 0:
            self.world.audio.play("boss_hit")
        if self.hp <= 0:
            self.hp = 0
            self.state = "dying"
            self.dying_t = 0
            self.world.beams.clear_owner(self)
            return True
        return False

    def _phase_for(self, r):
        if self.phases >= 3:
            return 2 if r <= 1 / 3.0 else (1 if r <= 2 / 3.0 else 0)
        return 1 if r <= 0.5 else 0

    def update(self):
        self.t += 1
        if self.flash > 0:
            self.flash -= 1
        if self.flash_cd > 0:
            self.flash_cd -= 1
        if self.invuln > 0:
            self.invuln -= 1
        if self.laser_cd > 0:
            self.laser_cd -= 1
        if self.state == "enter":
            self.x -= max(0.5, (self.x - self.home_x) * 0.03)
            if self.x - self.home_x < 1:
                self.x = self.home_x
                self.state = "fight"
                self.ft = 0
        elif self.state == "fight":
            self.ft += 1
            p = self._phase_for(self.ratio())
            if p != self.phase:
                self.phase = p
                self.ft = 0
                self.on_phase()
            self.fight()
        elif self.state == "dying":
            self.dying_t += 1

    def on_phase(self):
        w = self.world
        self.invuln = 60
        w.ebullets.clear()
        w.beams.clear_owner(self)
        w.audio.play("explode_big")
        w.shake(20, 2)
        for i in range(6):
            w.explosions.spawn(self.x + w.rng.randint(4, self.w - 4),
                               self.y + w.rng.randint(4, self.h - 4), big=(i % 2 == 0), delay=i * 4)
        self.mode = "show"
        self.mt = 0
        self.visible = True

    def fight(self):
        pass

    # ------------------------------------------------------------------
    # Movement & attack helpers
    # ------------------------------------------------------------------
    def sway(self, amp, freq, max_step=1.6):
        target = self.home_y + amp * math.sin(self.ft * freq)
        dy = max(-max_step, min(max_step, target - self.y))
        self.y += dy
        self.clamp()

    def clamp(self):
        self.y = max(PLAY_TOP + 2.0, min(PLAY_BOTTOM - self.h - 2.0, self.y))

    def track_player(self, speed):
        p = self.world.nearest_player(self.cx, self.cy)
        if p is not None:
            ty = p.y + 8 - self.h * 0.5
            self.y += max(-speed, min(speed, ty - self.y))
            self.clamp()

    def turret_points(self):
        dx, dt, db = self.turret_pos
        return ((self.x + dx, self.y + dt + 3), (self.x + dx, self.y + db + 4))

    def eye_point(self):
        ex, ey = self.eye_pos
        es = self.world.sprites[self.eye]
        return self.x + ex + es.w // 2, self.y + ey + es.h // 2

    def wall(self, gap_h, speed):
        w = self.world
        gy = w.rng.randint(PLAY_TOP + 12, PLAY_BOTTOM - gap_h - 12)
        y = PLAY_TOP + 3
        while y < PLAY_BOTTOM - 3:
            if not (gy <= y <= gy + gap_h):
                w.fire("shard", SCREEN_W + 2, y, -speed, 0)
            y += 9

    def mine_field(self, count):
        w = self.world
        for i in range(count):
            mx = w.rng.randint(40, 210)
            my = w.rng.randint(PLAY_TOP + 10, PLAY_BOTTOM - 20)
            w.drop_mine(mx, my, -0.25, 0.0, 60 + i * 12)

    def spawn_drone(self, x, y, pattern="sine"):
        self.world.spawn_enemy("drone", x, y, pattern=pattern, amp=18)

    # Teleport cycle shared by Revenant and the Arbiter's final phase
    def teleport_cycle(self, show_len, attacks):
        self.mt += 1
        if self.mode == "show":
            self.visible = True
            attacks(self.mt)
            if self.mt >= show_len:
                self.mode = "fade_out"
                self.mt = 0
                self.world.audio.play("teleport")
        elif self.mode == "fade_out":
            self.visible = (self.mt % 4) < 2
            self.invuln = 2
            if self.mt >= 24:
                self.mode = "hidden"
                self.mt = 0
                self.visible = False
        elif self.mode == "hidden":
            self.visible = False
            self.invuln = 2
            if self.mt >= 18:
                self._pick_spot()
                self.mode = "fade_in"
                self.mt = 0
                self.world.audio.play("teleport")
        elif self.mode == "fade_in":
            self.visible = (self.mt % 4) < 2
            self.invuln = 2
            if self.mt >= 24:
                self.mode = "show"
                self.mt = 0
                self.visible = True

    def _pick_spot(self):
        w = self.world
        for _ in range(12):
            x = w.rng.randint(110, int(SCREEN_W - self.w - 6))
            y = w.rng.randint(PLAY_TOP + 4, int(PLAY_BOTTOM - self.h - 4))
            ok = True
            for p in w.players:
                if p.in_play and abs(p.x + 8 - (x + self.w / 2)) < self.w * 0.5 + 24 \
                        and abs(p.y + 8 - (y + self.h / 2)) < self.h * 0.5 + 24:
                    ok = False
            if ok:
                break
        self.x = float(x)
        self.y = float(y)

    # ------------------------------------------------------------------
    def draw(self, surf, frame):
        if not self.visible or self.state == "gone":
            return
        sp = self.world.sprites
        white = self.flash > 0
        x = int(self.x)
        y = int(self.y)
        if self.turret:
            t = sp[self.turret]
            dx, dt, db = self.turret_pos
            surf.blit(t.white if white else t.img, (x + dx, y + dt))
            fb = t.flip_y
            surf.blit(fb.white if white else fb.img, (x + dx, y + db))
        surf.blit(self.hull_spr.white if white else self.hull_spr.img, (x, y))
        eye = sp[self.eye]
        ex, ey = self.eye_pos
        if self.warn and (frame >> 2) & 1:
            surf.blit(eye.white, (x + ex, y + ey))
        else:
            surf.blit(eye.white if white else eye.img, (x + ex, y + ey))


# ---------------------------------------------------------------------------
class Sentinel(Boss):
    name = "SENTINEL"
    tempo = 0.65
    speed_mult = 0.85
    hull = "sentinel"
    base_hp = 360
    eye = "eye_red"
    eye_pos = (21, 12)
    turret = "turret"
    turret_pos = (14, -6, 38)

    def fight(self):
        w = self.world
        d = w.diff
        bs = d.bullet_speed * self.speed_mult
        ft = self.ft
        t1, t2 = self.turret_points()
        nose = (self.x + 2, self.cy)
        if self.phase == 0:
            self.sway(56, 0.012)
            # two-shot bursts, alternating turrets
            if ft % self.P(80) in (20, 30):
                t = t1 if (ft // self.P(80)) % 2 == 0 else t2
                w.fire_aimed("aimed", t[0], t[1], 2.0 * bs)
            if ft % self.P(140) == 90:
                w.fire_fan("big", nose[0], nose[1], 3, 18.0, 1.5 * bs, None)
        else:
            self.sway(72, 0.02, 2.0)
            if ft % self.P(50) in (10, 18, 26):
                t = t1 if (ft // 8) % 2 == 0 else t2
                w.fire_aimed("aimed", t[0], t[1], 2.2 * bs)
            if ft % self.P(100) == 60:
                w.fire_fan("big", nose[0], nose[1], 5, 15.0, 1.6 * bs, None)
            if ft % self.P(180) == 120:
                ex, ey = self.eye_point()
                w.fire_ring("ring", ex, ey, 10, 1.2 * bs, w.rng.random() * 6.28)


class HiveMother(Boss):
    name = "HIVE MOTHER"
    tempo = 0.78
    speed_mult = 0.92
    hull = "hive"
    base_hp = 520
    eye = "eye_green"
    eye_pos = (25, 16)

    def fight(self):
        w = self.world
        d = w.diff
        bs = d.bullet_speed * self.speed_mult
        ft = self.ft
        mouth = (self.x + 4, self.cy - 4)
        ex, ey = self.eye_point()
        if self.phase == 0:
            self.sway(44, 0.008)
            if ft % self.P(240) in (60, 74, 88, 102):
                self.spawn_drone(mouth[0], mouth[1])
            if ft % self.P(90) == 40:
                w.fire_ring("ring", ex, ey, 12, 1.2 * bs, w.rng.random() * 6.28)
        else:
            self.sway(64, 0.014)
            if ft % self.P(60) == 0:
                w.fire_ring("ring", ex, ey, 14, 1.25 * bs, (ft // 60 % 2) * 0.224)
            if ft % self.P(320) < 120 and ft % 6 == 3:
                a = math.radians(ft * 9)
                for k in (0, math.pi):
                    w.fire("small", ex, ey, math.cos(a + k) * 1.4 * bs, math.sin(a + k) * 1.4 * bs)
            if ft % self.P(200) in (140, 152, 164, 176, 188):
                self.spawn_drone(mouth[0], mouth[1], "zig")


class Tempest(Boss):
    name = "TEMPEST"
    tempo = 0.88
    speed_mult = 0.97
    hull = "tempest"
    base_hp = 600
    eye = "eye_yellow"
    eye_pos = (19, 14)

    def fight(self):
        w = self.world
        d = w.diff
        bs = d.bullet_speed * self.speed_mult
        ft = self.ft
        top = (self.x + 26, self.y + 2)
        bot = (self.x + 26, self.y + self.h - 4)
        ex, ey = self.eye_point()
        colors = (0x28, 0x38, 0x30)
        if self.phase == 0:
            self.sway(78, 0.011, 1.4)
            if ft % self.P(320) == 30:
                w.add_beam(self, 0, self.h // 2, 10, 50, 120, colors)
                w.audio.play("laser_charge")
            self.warn = 30 <= ft % self.P(320) < 80
            if ft % self.P(110) == 55:
                w.fire_homing(top[0], top[1], 1.3 * bs, 90)
                w.fire_homing(bot[0], bot[1], 1.3 * bs, 90)
            if ft % self.P(70) == 10:
                w.fire_fan("aimed", ex - 10, ey, 3, 14.0, 1.7 * bs, None)
        else:
            self.sway(84, 0.017, 2.0)
            if ft % self.P(240) == 20:
                w.add_beam(self, 0, self.h // 2, 12, 40, 130, colors)
                w.audio.play("laser_charge")
            self.warn = 20 <= ft % self.P(240) < 60
            if ft % self.P(75) == 30:
                w.fire_homing(top[0], top[1], 1.4 * bs, 100)
                w.fire_homing(bot[0], bot[1], 1.4 * bs, 100)
                w.fire_homing(ex - 10, ey, 1.4 * bs, 100)
            if ft % self.P(45) == 40:
                w.fire_fan("aimed", ex - 10, ey, 5, 12.0, 2.0 * bs, None)


class CryoLancer(Boss):
    name = "CRYO-LANCER"
    tempo = 0.96
    speed_mult = 1.0
    hull = "cryo"
    base_hp = 680
    eye = "eye_cyan"
    eye_pos = (46, 8)
    turret = "turret_ice"
    turret_pos = (40, -6, 30)

    def __init__(self, world):
        Boss.__init__(self, world)
        self.mode = "idle"
        self.vx = 0.0

    def on_phase(self):
        Boss.on_phase(self)
        if self.x < self.home_x - 2 or self.x > self.home_x + 2:
            self.mode = "return"
        else:
            self.mode = "idle"
        self.mt = 0

    def body_rect(self):
        # the lance tip is deadly too
        return (self.x + 4, self.y + 10, self.w - 10, self.h - 20)

    def fight(self):
        w = self.world
        d = w.diff
        bs = d.bullet_speed * self.speed_mult
        self.mt += 1
        mt = self.mt
        p1 = self.phase == 1
        if self.mode == "idle":
            self.warn = False
            self.track_player(0.5)
            gap = 36 if p1 else 46
            if mt % self.P(90 if p1 else 110) == 20:
                self.wall(gap, 1.3 * bs)
            if p1 and mt % self.P(90) == 65:
                self.wall(gap, 1.3 * bs)
            if mt % self.P(70) == 35:
                t1, t2 = self.turret_points()
                w.fire_aimed("shard", t1[0], t1[1], 2.0 * bs)
                w.fire_aimed("shard", t2[0], t2[1], 2.0 * bs)
            if mt > self.P(200 if p1 else 280):
                self.mode = "aim"
                self.mt = 0
                w.audio.play("warn_beep")
        elif self.mode == "aim":
            self.warn = True
            self.track_player(2.2)
            if mt > (34 if p1 else 46):
                self.mode = "charge"
                self.mt = 0
                self.vx = -(6.5 if p1 else 5.5) * d.speed
                w.audio.play("laser_fire")
                w.shake(10, 1)
        elif self.mode == "charge":
            self.warn = False
            self.x += self.vx
            if mt % 4 == 0:
                w.particles.burst(self.x + self.w, self.cy, 3, 1.2, (0x31, 0x21, 0x30), w.rng, 16)
            if self.x < -self.w - 20:
                self.mode = "return"
                self.mt = 0
                self.x = float(SCREEN_W + 30)
                self.y = float(w.rng.randint(PLAY_TOP + 4, int(PLAY_BOTTOM - self.h - 4)))
        elif self.mode == "return":
            self.x -= max(0.8, (self.x - self.home_x) * 0.05)
            if p1 and mt % self.P(30) == 15:
                w.fire_fan("shard", self.x + 4, self.cy, 5, 16.0, 1.6 * bs, None)
            if self.x - self.home_x < 1:
                self.x = self.home_x
                self.mode = "idle"
                self.mt = 0


class Revenant(Boss):
    name = "REVENANT"
    tempo = 1.05
    speed_mult = 1.04
    hull = "revenant"
    base_hp = 760
    eye = "eye_violet"
    eye_pos = (31, 16)

    def fight(self):
        p1 = self.phase == 1
        self.teleport_cycle(self.P(100 if p1 else 130), self._attacks1 if p1 else self._attacks0)

    def _attacks0(self, mt):
        w = self.world
        bs = w.diff.bullet_speed * self.speed_mult
        ex, ey = self.eye_point()
        if mt == 10:
            self.mine_field(5)
        elif mt == 50:
            w.spawn_enemy("splitter", self.x, self.cy - 20)
            w.spawn_enemy("splitter", self.x, self.cy + 8)
        elif mt == 90:
            w.fire_fan("big", ex - 8, ey, 5, 15.0, 1.5 * bs, None)

    def _attacks1(self, mt):
        w = self.world
        bs = w.diff.bullet_speed * self.speed_mult
        ex, ey = self.eye_point()
        if mt == 8:
            self.mine_field(7)
        elif mt in (30, 38, 46):
            w.fire_aimed("aimed", ex - 8, ey, 2.2 * bs)
            w.fire_aimed("aimed", ex - 8, ey - 10, 2.2 * bs)
        elif mt == 60:
            w.spawn_enemy("splitter", self.x, self.cy - 20)
            w.spawn_enemy("splitter", self.x, self.cy + 8)
        elif mt == 80:
            w.fire_ring("ring", ex, ey, 16, 1.3 * bs, w.rng.random() * 6.28)


class Arbiter(Boss):
    name = "THE ARBITER"
    tempo = 1.15
    speed_mult = 1.08
    hull = "arbiter"
    base_hp = 1500
    phases = 3
    eye = "eye_arbiter"
    eye_pos = (31, 16)
    turret = "turret"
    turret_pos = (18, -5, 53)

    def body_rect(self):
        return (self.x + 12, self.y + 10, self.w - 20, self.h - 20)

    def fight(self):
        w = self.world
        d = w.diff
        bs = d.bullet_speed * self.speed_mult
        ft = self.ft
        ex, ey = self.eye_point()
        if self.phase == 0:
            # Sentinel + Hive Mother styles
            self.sway(58, 0.012)
            t1, t2 = self.turret_points()
            if ft % self.P(70) in (20, 26, 32):
                w.fire_aimed("aimed", t1[0], t1[1], 2.1 * bs)
                w.fire_aimed("aimed", t2[0], t2[1], 2.1 * bs)
            if ft % self.P(130) == 65:
                w.fire_fan("big", self.x + 4, self.cy, 7, 12.0, 1.6 * bs, None)
            if ft % self.P(110) == 30:
                w.fire_ring("ring", ex, ey, 16, 1.25 * bs, w.rng.random() * 6.28)
            if ft % self.P(300) in (150, 162, 174, 186):
                self.spawn_drone(self.x, self.cy - 4)
        elif self.phase == 1:
            # Tempest + Cryo-Lancer styles
            self.sway(80, 0.016, 1.8)
            if ft % self.P(260) == 20:
                w.add_beam(self, 0, self.h // 2, 12, 45, 120, (0x16, 0x26, 0x30))
                w.audio.play("laser_charge")
            self.warn = 20 <= ft % self.P(260) < 65
            if ft % self.P(90) == 45:
                t1, t2 = self.turret_points()
                w.fire_homing(t1[0], t1[1], 1.4 * bs, 100)
                w.fire_homing(t2[0], t2[1], 1.4 * bs, 100)
            if ft % self.P(170) == 100:
                self.wall(40, 1.4 * bs)
        else:
            # Revenant style plus everything, faster
            self.warn = False
            self.teleport_cycle(self.P(120), self._final_attacks)

    def _final_attacks(self, mt):
        w = self.world
        bs = w.diff.bullet_speed * self.speed_mult
        ex, ey = self.eye_point()
        if mt == 10:
            self.mine_field(6)
        if 20 <= mt <= 100 and mt % 5 == 0:
            a = math.radians(mt * 11)
            for k in (0, 2.094, 4.189):
                w.fire("small", ex, ey, math.cos(a + k) * 1.5 * bs, math.sin(a + k) * 1.5 * bs)
        if mt == 60:
            w.spawn_enemy("splitter", self.x, self.cy - 24)
            w.spawn_enemy("splitter", self.x, self.cy + 10)
        if mt == 90:
            w.fire_fan("big", ex - 10, ey, 7, 13.0, 1.7 * bs, None)
        if mt == 100:
            w.fire_ring("ring", ex, ey, 18, 1.35 * bs, w.rng.random() * 6.28)


BOSSES = {
    1: Sentinel,
    2: HiveMother,
    3: Tempest,
    4: CryoLancer,
    5: Revenant,
    6: Arbiter,
}
