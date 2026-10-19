"""The play-field: owns every pool and implements firing, collisions, bombs,
scoring and drops. Enemies and bosses talk to the game only through this."""
import math
import random

from config import SCREEN_W, PLAY_TOP, PLAY_BOTTOM
from entities.pools import (BulletPool, ExplosionPool, ParticlePool, BeamPool,
                            PopupPool, ENEMY_BULLETS, offscreen)
from entities.enemies import EnemyPool, update_enemy, draw_enemy, hitbox as enemy_hitbox, center as enemy_center
from entities.powerups import PowerUpPool

MAX_PLAYER_BULLETS = 28     # per player
ENEMY_BULLET_CAP = 220
DROP_CHANCE = 0.07
BOMB_DAMAGE = 12
BOMB_BOSS_DAMAGE = 30
CONTACT_DAMAGE = 6


def overlap(ax, ay, aw, ah, bx, by, bw, bh):
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


class Formation:
    __slots__ = ("size", "killed", "gone")

    def __init__(self, size):
        self.size = size
        self.killed = 0
        self.gone = 0


class World:
    def __init__(self, game, session, diff):
        self.game = game
        self.session = session
        self.sprites = game.sprites
        self.audio = game.audio
        self.settings = game.settings
        self.players = session.players
        self.diff = diff
        self.rng = random.Random()
        self.pbullets = BulletPool(MAX_PLAYER_BULLETS * 2 + 8)
        self.ebullets = BulletPool(ENEMY_BULLET_CAP)
        self.enemies = EnemyPool(48, self.sprites)
        self.explosions = ExplosionPool(40, self.sprites)
        self.particles = ParticlePool(180)
        self.beams = BeamPool(8)
        self.popups = PopupPool(12)
        self.powerups = PowerUpPool(10, self.sprites)
        self.boss = None
        self.boss_killed_by = None
        self.frame = 0
        self.shake_t = 0
        self.shake_mag = 0
        self.flash_t = 0
        self.flash_color = 0x30
        self.enemy_shot_cd = 0
        self._ebs = {k: self.sprites[v[0]] for k, v in ENEMY_BULLETS.items()}
        self._mine_lit = self.sprites["mine_lit"]

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def nearest_player(self, x, y):
        best = None
        bd = 1e9
        for p in self.players:
            if p.in_play:
                dx = p.x + 8 - x
                dy = p.y + 8 - y
                d = dx * dx + dy * dy
                if d < bd:
                    bd = d
                    best = p
        return best

    def aim(self, x, y):
        p = self.nearest_player(x, y)
        if p is None:
            return -1.0, 0.0
        dx = p.x + 8 - x
        dy = p.y + 8 - y
        d = math.hypot(dx, dy) or 1.0
        return dx / d, dy / d

    # ------------------------------------------------------------------
    # Enemy fire
    # ------------------------------------------------------------------
    def fire(self, kind, x, y, vx, vy):
        b = self.ebullets.spawn()
        if b is None:
            return None
        spr = self._ebs[kind]
        b.kind = kind
        b.spr = spr
        hw, hh = ENEMY_BULLETS[kind][1], ENEMY_BULLETS[kind][2]
        b.hw = hw
        b.hh = hh
        # x, y are the bullet centre
        b.x = x - spr.w * 0.5
        b.y = y - spr.h * 0.5
        b.vx = vx
        b.vy = vy
        if self.enemy_shot_cd <= 0:
            self.audio.enemy_shot()
            self.enemy_shot_cd = 5
        return b

    def fire_aimed(self, kind, x, y, speed, angle_offset=0.0):
        dx, dy = self.aim(x, y)
        if angle_offset:
            a = math.atan2(dy, dx) + angle_offset
            dx, dy = math.cos(a), math.sin(a)
        return self.fire(kind, x, y, dx * speed, dy * speed)

    def fire_fan(self, kind, x, y, count, step_deg, speed, center_deg=None):
        if center_deg is None:
            dx, dy = self.aim(x, y)
            base = math.atan2(dy, dx)
        else:
            base = math.radians(center_deg)
        step = math.radians(step_deg)
        start = base - step * (count - 1) / 2.0
        for i in range(count):
            a = start + step * i
            self.fire(kind, x, y, math.cos(a) * speed, math.sin(a) * speed)

    def fire_ring(self, kind, x, y, count, speed, offset=0.0):
        step = math.tau / count
        for i in range(count):
            a = offset + step * i
            self.fire(kind, x, y, math.cos(a) * speed, math.sin(a) * speed)

    def fire_homing(self, x, y, speed, frames):
        dx, dy = self.aim(x, y)
        b = self.fire("homing", x, y, dx * speed, dy * speed)
        if b is not None:
            b.homing = frames
            b.speed = speed
        return b

    def drop_mine(self, x, y, vx, vy, timer):
        b = self.fire("mine", x + 4, y + 4, vx, vy)
        if b is not None:
            b.timer = timer
        return b

    def add_beam(self, owner, ox, oy, thick, warn, fire, colors=(0x16, 0x26, 0x30)):
        return self.beams.spawn(owner, ox, oy, thick, warn, fire, colors)

    def spawn_enemy(self, kind, x, y, **kw):
        return self.enemies.spawn(kind, x, y, self, **kw)

    # ------------------------------------------------------------------
    # Effects
    # ------------------------------------------------------------------
    def shake(self, frames, mag):
        if self.settings["shake"]:
            self.shake_t = max(self.shake_t, frames)
            self.shake_mag = max(self.shake_mag, mag)

    def flash(self, frames, color=0x30):
        self.flash_t = frames
        self.flash_color = color

    def explode(self, x, y, big=False):
        self.explosions.spawn(x, y, big)
        self.particles.burst(x, y, 10 if big else 5, 1.6 if big else 1.0,
                             (0x27, 0x38, 0x16, 0x30), self.rng, 28 if big else 18)

    def shake_offset(self):
        if self.shake_t <= 0:
            return 0, 0
        m = self.shake_mag
        return self.rng.randint(-m, m), self.rng.randint(-m, m)

    # ------------------------------------------------------------------
    # Player actions
    # ------------------------------------------------------------------
    def _player_bullet_count(self, idx):
        n = 0
        for b in self.pbullets.items:
            if b.active and b.owner == idx:
                n += 1
        return n

    def _pshot(self, p, sprname, x, y, vx, vy, dmg, pierce):
        b = self.pbullets.spawn()
        if b is None:
            return
        spr = self.sprites[sprname]
        b.spr = spr
        b.x = x
        b.y = y
        b.vx = vx
        b.vy = vy
        b.owner = p.idx
        b.dmg = dmg
        b.pierce = pierce
        b.hw = spr.w // 2
        b.hh = 2

    def player_fire(self, p):
        if self._player_bullet_count(p.idx) >= MAX_PLAYER_BULLETS:
            return
        x = p.x + 10
        y = p.y + 7
        lvl = p.weapon
        tag = "1" if p.idx == 0 else "2"
        if p.laser:
            spr = "laser" + tag
            if lvl == 2:
                self._pshot(p, spr, x - 4, y - 4, 7.0, 0, 2, True)
                self._pshot(p, spr, x - 4, y + 4, 7.0, 0, 2, True)
            else:
                self._pshot(p, spr, x, y, 7.0, 0, 2, True)
            if lvl >= 3:
                self._pshot(p, spr, x - 6, y - 4, 6.6, -1.6, 2, True)
                self._pshot(p, spr, x - 6, y + 4, 6.6, 1.6, 2, True)
            if lvl >= 4:
                self._pshot(p, spr, p.x - 14, y, -7.0, 0, 2, True)
            p.fire_cd = 10
            self.audio.shot(p.idx, "shot_laser")
        else:
            spr = "shot" + tag
            if lvl == 1:
                self._pshot(p, spr, x, y, 5.5, 0, 1, False)
            else:
                self._pshot(p, spr, x, y - 3, 5.5, 0, 1, False)
                self._pshot(p, spr, x, y + 3, 5.5, 0, 1, False)
            if lvl >= 3:
                self._pshot(p, spr, x - 2, y - 4, 5.2, -1.3, 1, False)
                self._pshot(p, spr, x - 2, y + 4, 5.2, 1.3, 1, False)
            if lvl >= 4:
                self._pshot(p, "rear" + tag, p.x - 6, y, -5.5, 0, 1, False)
            p.fire_cd = 7
            self.audio.shot(p.idx, "shot_spread" if lvl >= 3 else "shot")

    def bomb(self, p):
        self.audio.play("bomb")
        self.flash(8, 0x30)
        self.shake(24, 3)
        p.invuln = max(p.invuln, 90)
        n = 0
        for b in self.ebullets.items:
            if b.active:
                if n < 40 and n % 2 == 0:
                    self.particles.spawn(b.x + 2, b.y + 2, self.rng.uniform(-1, 1),
                                         self.rng.uniform(-1, 1), 20, 0x30)
                n += 1
                self.ebullets.kill(b)
        self.beams.clear()
        for e in self.enemies.items:
            if e.active and e.x < SCREEN_W:
                self.hit_enemy(e, BOMB_DAMAGE, p)
        if self.boss is not None and self.boss.hittable:
            if self.boss.damage(BOMB_BOSS_DAMAGE):
                self.boss_killed_by = p
        cx, cy = p.center()
        for i in range(8):
            a = i * math.tau / 8
            self.explosions.spawn(cx + math.cos(a) * 40, cy + math.sin(a) * 30, big=True, delay=i * 2)

    def extra_life(self, p):
        self.audio.play("oneup")
        cx, cy = p.center()
        self.popups.spawn("1UP!", cx, cy - 12, 0x26 if p.idx == 0 else 0x2A, 90)

    def player_died(self, p):
        cx, cy = p.center()
        self.explode(cx, cy, True)
        self.explosions.spawn(cx - 6, cy + 4, False, 6)
        self.explosions.spawn(cx + 6, cy - 4, False, 10)
        self.particles.burst(cx, cy, 16, 2.2, (0x30, 0x16 if p.idx == 0 else 0x1A, 0x10), self.rng, 40)
        self.audio.play("death")
        self.shake(20, 3)

    def collect(self, p, pu):
        k = pu.kind
        self.audio.play("powerup")
        cx, cy = p.center()
        label = k
        if k == "P":
            if p.weapon < 4:
                p.weapon += 1
                label = "POWER UP"
            else:
                p.add_score(1000, self, self.settings["extra_life"])
                label = "1000"
        elif k == "L":
            if p.laser:
                p.add_score(1000, self, self.settings["extra_life"])
                label = "1000"
            else:
                p.laser = True
                label = "LASER"
        elif k == "S":
            if p.speed_level < 3:
                p.speed_level += 1
                label = "SPEED UP"
            else:
                p.add_score(500, self, self.settings["extra_life"])
                label = "500"
        elif k == "B":
            if p.bombs < 5:
                p.bombs += 1
                label = "BOMB"
            else:
                p.add_score(500, self, self.settings["extra_life"])
                label = "500"
        elif k == "O":
            p.shield = True
            label = "SHIELD"
            self.audio.play("shield")
        elif k == "1UP":
            if p.lives < 9:
                p.lives += 1
            self.extra_life(p)
            label = None
        if label:
            self.popups.spawn(label, cx, cy - 12, 0x30, 50)

    # ------------------------------------------------------------------
    # Enemies
    # ------------------------------------------------------------------
    def hit_enemy(self, e, dmg, p):
        if not e.active or e.dead:
            return
        e.hp -= dmg
        if e.flash <= -5:
            e.flash = 2
        if e.hp <= 0:
            self.enemy_killed(e, p)
        elif e.kind == "warden":
            self.audio.play("hit")

    def enemy_killed(self, e, p):
        e.dead = True
        e.active = False
        cx, cy = enemy_center(e)
        big = e.kind in ("warden",)
        self.explode(cx, cy, big)
        if big:
            self.explosions.spawn(cx - 10, cy, False, 4)
            self.explosions.spawn(cx + 10, cy, False, 8)
            self.audio.play("explode_big")
            self.shake(12, 2)
        else:
            self.audio.play("explode_small")
        if e.beam is not None:
            self.beams.clear_owner(e)
        if p is not None:
            p.add_score(e.points * self.diff.score_mult, self, self.settings["extra_life"])
        # drops
        drop = False
        f = e.formation
        if f is not None:
            f.killed += 1
            if f.killed == f.size:
                drop = True
        if e.kind == "warden" and self.rng.random() < 0.6:
            drop = True
        if not drop and e.kind not in ("asteroid_s", "splitlet") and self.rng.random() < DROP_CHANCE:
            drop = True
        if drop:
            self.powerups.spawn(self.powerups.roll(self.rng), cx - 6, cy - 6)
        # splitting
        if e.kind == "splitter":
            for vy in (-1.3, 1.3):
                self.spawn_enemy("splitlet", cx - 4, cy - 4, vx=-1.9, vy=vy)
        elif e.kind == "asteroid":
            for vy in (-0.6, 0.6):
                self.spawn_enemy("asteroid_s", cx - 4, cy - 4, vx=e.vx - 0.3, vy=vy)

    def enemy_escaped(self, e):
        e.active = False
        if e.formation is not None:
            e.formation.gone += 1
        if e.beam is not None:
            self.beams.clear_owner(e)

    def enemies_alive(self):
        return self.enemies.count() > 0

    def clear_hostiles(self, explode=True):
        for e in self.enemies.items:
            if e.active:
                if explode:
                    cx, cy = enemy_center(e)
                    self.explode(cx, cy)
                e.active = False
        self.ebullets.clear()
        self.beams.clear()

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------
    def update(self):
        self.frame += 1
        if self.shake_t > 0:
            self.shake_t -= 1
            if self.shake_t == 0:
                self.shake_mag = 0
        if self.flash_t > 0:
            self.flash_t -= 1
        if self.enemy_shot_cd > 0:
            self.enemy_shot_cd -= 1

        for b in self.pbullets.items:
            if b.active:
                b.x += b.vx
                b.y += b.vy
                if b.x > SCREEN_W + 4 or b.x < -20 or b.y < PLAY_TOP - 8 or b.y > PLAY_BOTTOM + 8:
                    self.pbullets.kill(b)

        for e in self.enemies.items:
            if e.active:
                update_enemy(e, self)

        if self.boss is not None:
            self.boss.update()

        self._update_enemy_bullets()
        self.beams.update(self.audio)
        self.powerups.update()
        self.explosions.update()
        self.particles.update()
        self.popups.update()
        self._collisions()

    def _update_enemy_bullets(self):
        for b in self.ebullets.items:
            if not b.active:
                continue
            if b.homing > 0:
                b.homing -= 1
                p = self.nearest_player(b.x, b.y)
                if p is not None:
                    want = math.atan2(p.y + 8 - b.y, p.x + 8 - b.x)
                    cur = math.atan2(b.vy, b.vx)
                    diff = (want - cur + math.pi) % math.tau - math.pi
                    cur += max(-0.045, min(0.045, diff))
                    b.vx = math.cos(cur) * b.speed
                    b.vy = math.sin(cur) * b.speed
            b.x += b.vx
            b.y += b.vy
            if b.kind == "mine":
                b.timer -= 1
                if b.timer <= 0:
                    cx = b.x + 4
                    cy = b.y + 4
                    self.ebullets.kill(b)
                    self.fire_ring("ring", cx, cy, 8, 1.2 * self.diff.bullet_speed, self.rng.random())
                    self.explosions.spawn(cx, cy, False)
                    continue
            if offscreen(b.x, b.y, 12):
                self.ebullets.kill(b)

    def _collisions(self):
        players = self.players
        boss = self.boss
        # player bullets -> enemies / boss
        for b in self.pbullets.items:
            if not b.active:
                continue
            bx, by = b.x, b.y + 0.0
            bw = b.spr.w
            bh = 3
            owner = players[b.owner]
            hit = False
            for e in self.enemies.items:
                if not e.active or e.x > SCREEN_W - 2:
                    continue
                i = e.inset
                if bx < e.x + e.w - i and e.x + i < bx + bw and by < e.y + e.h - i and e.y + i < by + bh:
                    if b.pierce:
                        if e.laser_cd <= 0:
                            e.laser_cd = 6
                            self.hit_enemy(e, b.dmg, owner)
                    else:
                        self.hit_enemy(e, b.dmg, owner)
                        hit = True
                        break
            if hit:
                self.pbullets.kill(b)
                continue
            if boss is not None and boss.hittable:
                rx, ry, rw, rh = boss.hit_rect()
                if overlap(bx, by, bw, bh, rx, ry, rw, rh):
                    if b.pierce:
                        if boss.laser_cd <= 0:
                            boss.laser_cd = 5
                            if boss.damage(b.dmg):
                                self.boss_killed_by = owner
                    else:
                        if boss.damage(b.dmg):
                            self.boss_killed_by = owner
                        self.pbullets.kill(b)
                        self.particles.spawn(bx + bw, by + 1, -0.5, self.rng.uniform(-0.6, 0.6), 8, 0x38)

        # hazards -> players
        for p in players:
            if not p.can_be_hit:
                if p.in_play:
                    self._pickups(p)
                continue
            hx, hy, hw, hh = p.hitbox()
            dead = False
            for b in self.ebullets.items:
                if b.active:
                    bcx = b.x + b.spr.w * 0.5
                    bcy = b.y + b.spr.h * 0.5
                    if (abs(bcx - (hx + 2)) < b.hw + 2) and (abs(bcy - (hy + 2)) < b.hh + 2):
                        self.ebullets.kill(b)
                        if p.kill(self):
                            dead = True
                        break
            if not dead:
                for bm in self.beams.items:
                    if bm.active and bm.firing:
                        half = bm.thick // 2
                        if overlap(hx, hy, hw, hh, bm.x_end - bm.length, bm.y - half, bm.length, bm.thick):
                            if p.kill(self):
                                dead = True
                            break
            if not dead and p.can_be_hit:
                for e in self.enemies.items:
                    if e.active:
                        rx, ry, rw, rh = enemy_hitbox(e)
                        if overlap(hx - 2, hy - 2, hw + 4, hh + 4, rx, ry, rw, rh):
                            if p.kill(self):
                                dead = True
                            self.hit_enemy(e, CONTACT_DAMAGE, p)
                            break
            if not dead and p.can_be_hit and boss is not None and boss.visible and boss.state in ("fight", "enter"):
                rx, ry, rw, rh = boss.body_rect()
                if overlap(hx, hy, hw, hh, rx, ry, rw, rh):
                    p.kill(self)
            if p.in_play:
                self._pickups(p)

    def _pickups(self, p):
        if p.state != "alive":
            return
        bx, by, bw, bh = p.body_rect()
        for pu in self.powerups.items:
            if pu.active and overlap(bx, by, bw, bh, pu.x, pu.y, pu.spr.w, pu.spr.h):
                pu.active = False
                self.collect(p, pu)

    # ------------------------------------------------------------------
    def draw(self, surf):
        frame = self.frame
        self.beams.draw(surf, frame)
        self.powerups.draw(surf)
        sp = self.sprites
        for e in self.enemies.items:
            if e.active:
                draw_enemy(e, surf, sp, frame)
        if self.boss is not None:
            self.boss.draw(surf, frame)
        for b in self.pbullets.items:
            if b.active:
                surf.blit(b.spr.img, (int(b.x), int(b.y)))
        for p in self.players:
            p.draw(surf, sp)
        self.explosions.draw(surf)
        self.particles.draw(surf)
        lit = self._mine_lit
        for b in self.ebullets.items:
            if b.active:
                if b.kind == "mine" and (b.timer < 30 and (b.timer >> 1) & 1 or (b.timer >> 3) & 1):
                    surf.blit(lit.img, (int(b.x), int(b.y)))
                else:
                    surf.blit(b.spr.img, (int(b.x), int(b.y)))
        self.popups.draw(surf, self.game.font)
