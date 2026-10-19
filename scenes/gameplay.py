"""In-game scene: runs the sector script, the boss fight, HUD, joins and
game-over detection. A Session carries players and progress between sectors."""
from config import rgb, BLACK, SCREEN_W, P1_COLOR, P2_COLOR
from scenes.base import Scene
from entities.player import Player
from entities.world import World, Formation
from entities.bosses import BOSSES
from levels.difficulty import Difficulty
from levels.sectors import LevelScript, SECTOR_INFO
from graphics.background import SectorBackground

WARNING_FRAMES = 200
BOSS_DEATH_FRAMES = 150
CLEAR_FRAMES = 260
MAX_WAIT_AFTER_SCRIPT = 540


class Session:
    def __init__(self, game, num_players):
        self.game = game
        self.players = [Player(0), Player(1)]
        self.sector = 1
        self.lap = 1
        self.continues = 3
        step = game.settings["extra_life"]
        for i in range(num_players):
            self.players[i].join(step)

    @property
    def joined_count(self):
        return sum(1 for p in self.players if p.joined)


class Gameplay(Scene):
    def __init__(self, game, session):
        Scene.__init__(self, game)
        self.session = session
        s = session
        self.sector = s.sector
        self.name, self.music = SECTOR_INFO[s.sector]
        self.diff = Difficulty(s.sector, s.lap, game.settings["difficulty"], max(1, s.joined_count))
        self.world = World(game, s, self.diff)
        self.bg = SectorBackground(s.sector, game.sprites)
        self.script = LevelScript(s.sector, self.diff, Formation)
        self.phase = "waves"
        self.pt = 0
        self.after_script = 0
        self.banner = 200
        for p in s.players:
            p.deaths_this_sector = 0
            p.reset_position()

    def enter(self):
        self.game.audio.play_music(self.music, restart=True)
        self.game.input.p2_active = self.session.players[1].active_in_game

    def exit(self):
        self.game.input.p2_active = False

    def resume(self):
        self.game.audio.resume_all()

    # ------------------------------------------------------------------
    def _spawn(self, ev):
        self.world.spawn_enemy(ev.kind, ev.x, ev.y, **ev.kw)

    def _try_join(self, p):
        s = self.session
        other = s.players[1 - p.idx]
        step = self.game.settings["extra_life"]
        if p.state == "absent":
            p.join(step)
            self.game.audio.play("join")
            return True
        if p.state == "out" and other.lives >= 2 and other.active_in_game:
            other.lives -= 1
            p.lives = 1
            p.bombs = max(p.bombs, 2)
            p.spawn()
            self.game.audio.play("join")
            self.world.popups.spawn("JOINED!", 128, 120, P1_COLOR if p.idx == 0 else P2_COLOR, 60)
            return True
        return False

    def update(self):
        self.t += 1
        g = self.game
        inp = g.input
        players = self.session.players
        w = self.world
        # arrows steer player 1 too, unless player 2 is flying
        inp.p2_active = players[1].active_in_game

        # A controller was unplugged: pause so nobody dies while reconnecting.
        if inp.disconnected:
            if self.phase not in ("clear",):
                self._pause()
                return

        # Joining / rejoining with START (pad) or FIRE (keyboard)
        for p in players:
            if not p.active_in_game:
                if "fire" in inp.pressed[p.idx] or "pause" in inp.pad_pressed[p.idx]:
                    if self._try_join(p):
                        inp.pressed[p.idx].discard("pause")

        # Pause
        for p in players:
            if p.active_in_game and "pause" in inp.pressed[p.idx]:
                self._pause()
                return

        for p in players:
            if p.state != "absent" and p.state != "out":
                p.update(inp.held[p.idx], inp.pressed[p.idx], w)

        self._phase_logic()
        w.update()
        self.bg.update()
        if self.banner > 0:
            self.banner -= 1

        # Game over: nobody left with ships
        if not any(p.active_in_game for p in players):
            self._game_over()

    def _pause(self):
        from scenes.pause import Pause
        self.game.push(Pause(self.game, self))

    def _game_over(self):
        s = self.session
        if s.continues > 0:
            from scenes.gameover import ContinueScreen
            self.game.push(ContinueScreen(self.game, self))
        else:
            from scenes.gameover import GameOver
            self.game.switch(GameOver(self.game, s))

    def _phase_logic(self):
        w = self.world
        g = self.game
        self.pt += 1
        if self.phase == "waves":
            self.script.update(self._spawn)
            if self.script.done:
                self.after_script += 1
                if not w.enemies_alive() or self.after_script > MAX_WAIT_AFTER_SCRIPT:
                    self.phase = "warning"
                    self.pt = 0
                    g.audio.stop_music()
                    g.audio.siren(True)
        elif self.phase == "warning":
            if self.pt % 40 == 1:
                w.flash(4, 0x16)
            if self.pt >= WARNING_FRAMES:
                g.audio.siren(False)
                g.audio.play_music("boss", restart=True)
                w.boss = BOSSES[self.sector](w)
                self.phase = "boss"
                self.pt = 0
        elif self.phase == "boss":
            b = w.boss
            if b is not None and b.state == "dying":
                self.phase = "boss_dying"
                self.pt = 0
                w.ebullets.clear()
                w.beams.clear()
                g.audio.stop_music()
        elif self.phase == "boss_dying":
            b = w.boss
            if self.pt % 5 == 0 and b is not None:
                w.explosions.spawn(b.x + w.rng.randint(0, b.w), b.y + w.rng.randint(0, b.h), big=self.pt % 15 == 0)
                g.audio.play("explode_small" if self.pt % 15 else "explode_big")
                w.shake(6, 2)
            if self.pt % 20 == 0:
                w.flash(2, 0x30)
            # stray enemies (drones, splitters) go down with their champion
            if self.pt == 10:
                w.clear_hostiles(explode=True)
            if self.pt >= BOSS_DEATH_FRAMES and b is not None:
                cx, cy = b.cx, b.cy
                for i in range(8):
                    w.explosions.spawn(cx + w.rng.randint(-24, 24), cy + w.rng.randint(-20, 20), True, i * 3)
                w.particles.burst(cx, cy, 40, 2.6, (0x30, 0x38, 0x27, 0x16), w.rng, 50)
                w.flash(6, 0x30)
                w.shake(30, 4)
                g.audio.play("explode_big")
                w.boss = None
                self.bonus = 5000 * self.sector * self.diff.score_mult
                step = g.settings["extra_life"]
                for p in self.session.players:
                    if p.active_in_game:
                        p.add_score(self.bonus, w, step)
                w.popups.spawn("BONUS %d" % self.bonus, 128, 110, 0x28, 120)
                g.audio.play_music("victory", restart=True)
                self.phase = "clear"
                self.pt = 0
        elif self.phase == "clear":
            if self.pt >= CLEAR_FRAMES:
                from scenes.sector_clear import SectorClear
                g.switch(SectorClear(g, self.session, self.bonus, BOSSES[self.sector].name))

    # ------------------------------------------------------------------
    def shake_offset(self):
        return self.world.shake_offset()

    def draw(self, surf):
        w = self.world
        self.bg.draw(surf)
        w.draw(surf)
        if w.flash_t > 0 and w.flash_t & 1:
            # whole-screen flash using a palette colour (no alpha blending)
            if w.flash_color == 0x16:
                surf.fill(rgb(0x06), (0, 16, SCREEN_W, 224))
                w.draw(surf)
            else:
                surf.fill(rgb(w.flash_color), (0, 16, SCREEN_W, 224))
        self.draw_overlays(surf)
        self.draw_hud(surf)

    def draw_overlays(self, surf):
        font = self.game.font
        if self.banner > 0 and self.phase == "waves" and (self.banner > 30 or self.banner & 2):
            s = self.session
            title = "SECTOR %d - %s" % (self.sector, self.name)
            if len(title) > 30:
                font.draw_center(surf, "SECTOR %d" % self.sector, 100, 0x30, shadow=BLACK)
                font.draw_center(surf, self.name, 112, 0x28, shadow=BLACK)
            else:
                font.draw_center(surf, title, 106, 0x30, shadow=BLACK)
            if s.lap > 1:
                font.draw_center(surf, "LAP %d" % s.lap, 92, 0x26, shadow=BLACK)
            font.draw_center(surf, "GET READY!", 128, 0x38, shadow=BLACK)
        if self.phase == "warning":
            if (self.pt >> 4) & 1 == 0:
                surf.fill(rgb(0x16), (0, 96, SCREEN_W, 2))
                surf.fill(rgb(0x16), (0, 126, SCREEN_W, 2))
                font.draw_center(surf, "WARNING", 104, 0x26, shadow=BLACK)
                font.draw_center(surf, "VEXARI CHAMPION APPROACHING", 116, 0x30, shadow=BLACK)
        b = self.world.boss
        if b is not None and self.phase in ("boss", "boss_dying"):
            self.draw_boss_bar(surf, b)
        if self.phase == "clear" and self.pt > 20:
            font.draw_center(surf, "SECTOR CLEAR!", 96, 0x28, shadow=BLACK)

    def draw_boss_bar(self, surf, b):
        font = self.game.font
        font.draw(surf, b.name, 4, 18, 0x30, shadow=BLACK)
        x0 = 4 + len(b.name) * 8 + 6
        width = SCREEN_W - x0 - 6
        surf.fill(rgb(0x30), (x0, 19, width, 6))
        surf.fill(rgb(BLACK), (x0 + 1, 20, width - 2, 4))
        fill = int((width - 2) * b.hp / float(b.max_hp))
        col = (0x2A, 0x28, 0x16)[min(2, b.phase)] if b.phases == 3 else (0x28 if b.phase == 0 else 0x16)
        if fill > 0:
            surf.fill(rgb(col), (x0 + 1, 20, fill, 4))
            surf.fill(rgb(0x30), (x0 + 1, 20, fill, 1))

    def draw_hud(self, surf):
        font = self.game.font
        sp = self.game.sprites
        surf.fill(rgb(BLACK), (0, 0, SCREEN_W, 16))
        players = self.session.players
        hi = max(self.game.highscores.top_score(), players[0].score, players[1].score)
        # Player 1 (left)
        p1 = players[0]
        font.draw(surf, "1P", 0, 0, P1_COLOR)
        font.draw(surf, "%07d" % p1.score, 18, 0, 0x30)
        self._draw_stock(surf, p1, 0, sp, font)
        # High score (centre)
        font.draw(surf, "HI", 96, 0, 0x28)
        font.draw(surf, "%07d" % hi, 114, 0, 0x30)
        font.draw(surf, "S%d" % self.sector, 120, 8, 0x3C)
        if self.session.lap > 1:
            font.draw(surf, "L%d" % self.session.lap, 140, 8, 0x26)
        # Player 2 (right)
        p2 = players[1]
        font.draw(surf, "2P", 184, 0, P2_COLOR)
        if p2.state == "absent" or (p2.state == "out" and (players[0].lives >= 2 and players[0].active_in_game)):
            if (self.t >> 5) & 1 == 0:
                font.draw(surf, "PUSH", 202, 0, 0x30)
                font.draw(surf, "START", 194, 8, 0x30)
        elif p2.state == "out":
            font.draw(surf, "%07d" % p2.score, 200, 0, 0x30)
            font.draw(surf, "OUT", 210, 8, 0x00)
        else:
            font.draw(surf, "%07d" % p2.score, 200, 0, 0x30)
            self._draw_stock(surf, p2, 184, sp, font)
        if p1.state == "out":
            surf.fill(rgb(BLACK), (0, 8, 80, 8))
            if players[1].lives >= 2 and players[1].active_in_game and (self.t >> 5) & 1 == 0:
                font.draw(surf, "PUSH START", 0, 8, 0x30)
            else:
                font.draw(surf, "OUT", 18, 8, 0x00)

    def _draw_stock(self, surf, p, x, sp, font):
        icon = sp["life1" if p.idx == 0 else "life2"]
        surf.blit(icon.img, (x, 8))
        font.draw(surf, "%d" % max(0, min(9, p.lives)), x + 8, 8, 0x30)
        surf.blit(sp["bomb_icon"].img, (x + 18, 8))
        font.draw(surf, "%d" % p.bombs, x + 26, 8, 0x30)
        # weapon indicator
        wl = ("L" if p.laser else "W") + str(p.weapon)
        font.draw(surf, wl, x + 36, 8, 0x2C if p.laser else 0x27)
        if p.speed_level:
            font.draw(surf, "S%d" % p.speed_level, x + 54, 8, 0x2A)
