"""Continue countdown, GAME OVER screen and arcade-style initials entry."""
from config import rgb, BLACK, P1_COLOR, P2_COLOR
from scenes.base import Scene, draw_box
from graphics.display import dim_surface

CONTINUE_SECONDS = 10
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .!-"


class ContinueScreen(Scene):
    def __init__(self, game, gameplay):
        Scene.__init__(self, game)
        self.gameplay = gameplay
        self.session = gameplay.session
        self.frames = CONTINUE_SECONDS * 60 + 59
        self.snapshot = None

    def enter(self):
        surf = self.game.display.surface.copy()
        self.gameplay.draw(surf)
        self.snapshot = dim_surface(surf, 2)
        self.game.audio.stop_music()
        self.game.audio.stop_sfx()

    def update(self):
        self.t += 1
        g = self.game
        inp = g.input
        self.frames -= 1
        if self.frames % 60 == 0 and self.frames > 0:
            g.audio.play("tally")
        pressed = self.t > 30 and (
            "confirm" in inp.menu or any(("pause" in inp.pressed[i] or "fire" in inp.pressed[i]) for i in range(2)))
        if pressed:
            self._continue()
            return
        if self.frames <= 0 or (self.t > 30 and "back" in inp.menu):
            from scenes.gameover import GameOver
            g.switch(GameOver(g, self.session))

    def _continue(self):
        s = self.session
        g = self.game
        s.continues -= 1
        step = g.settings["extra_life"]
        for p in s.players:
            if p.joined:
                p.best_score = max(p.best_score, p.score)
                p.score = 0
                p.join(step)
        g.audio.play("join")
        phase = self.gameplay.phase
        if phase == "boss":
            g.audio.play_music("boss", restart=True)
        elif phase == "warning":
            g.audio.siren(True)
        elif phase == "waves":
            g.audio.play_music(self.gameplay.music, restart=True)
        g.pop()

    def draw(self, surf):
        surf.blit(self.snapshot, (0, 0))
        font = self.game.font
        draw_box(surf, 48, 72, 160, 96)
        font.draw_center(surf, "CONTINUE?", 86, 0x28)
        secs = max(0, self.frames // 60)
        font.draw_center(surf, "%d" % secs, 106, 0x30 if secs > 3 else 0x26)
        font.draw_center(surf, "PRESS START", 126, 0x30 if (self.t >> 4) & 1 else 0x10)
        font.draw_center(surf, "CREDITS LEFT: %d" % self.session.continues, 146, 0x3C)


class GameOver(Scene):
    def __init__(self, game, session):
        Scene.__init__(self, game)
        self.session = session

    def enter(self):
        self.game.audio.stop_sfx()
        self.game.audio.play_music("gameover", restart=True)

    def update(self):
        self.t += 1
        inp = self.game.input
        if (self.t > 90 and ("confirm" in inp.menu or inp.any_pressed)) or self.t > 60 * 9:
            self.finish()

    def finish(self):
        g = self.game
        s = self.session
        queue = []
        for p in s.players:
            if p.joined:
                score = max(p.score, p.best_score)
                if g.highscores.qualifies(score):
                    queue.append((p.idx, score))
        if queue:
            g.switch(InitialsEntry(g, s, queue))
        else:
            from scenes.highscore_view import HighScoreView
            g.switch(HighScoreView(g, then_title=True))

    def draw(self, surf):
        surf.fill(rgb(BLACK))
        font = self.game.font
        from graphics.font import build_logo_text, GLYPHS
        if not hasattr(GameOver, "_logo"):
            GameOver._logo = build_logo_text(GLYPHS, "GAME OVER", 3, [0x16, 0x06, 0x16, 0x26], 0x05, 0x0F)
        lg = GameOver._logo
        y = min(90, -30 + self.t * 2)
        surf.blit(lg, (128 - lg.get_width() // 2, y))
        if self.t > 60:
            s = self.session
            sec = "SECTOR %d" % s.sector + (" LAP %d" % s.lap if s.lap > 1 else "")
            font.draw_center(surf, "REACHED " + sec, 140, 0x3C)
            row = 160
            for p in s.players:
                if p.joined:
                    col = P1_COLOR if p.idx == 0 else P2_COLOR
                    font.draw_center(surf, "%s  %07d" % (p.name, max(p.score, p.best_score)), row, col)
                    row += 12


class InitialsEntry(Scene):
    def __init__(self, game, session, queue):
        Scene.__init__(self, game)
        self.session = session
        self.queue = list(queue)
        self.last_rank = None
        self._start_next()

    def enter(self):
        self.game.audio.play_music("highscore", restart=True)

    def _start_next(self):
        self.player, self.score = self.queue.pop(0)
        self.letters = [0, 0, 0]
        self.pos = 0
        self.t = 0
        self.timeout = 60 * 40

    def update(self):
        self.t += 1
        g = self.game
        inp = g.input
        m = inp.menu
        own = inp.pressed[self.player]
        a = g.audio
        n = len(LETTERS)
        if self.t < 15:
            return
        if "up" in m or "up" in own:
            self.letters[self.pos] = (self.letters[self.pos] + 1) % n
            a.play("menu_move")
        if "down" in m or "down" in own:
            self.letters[self.pos] = (self.letters[self.pos] - 1) % n
            a.play("menu_move")
        if ("back" in m or "bomb" in own or "left" in m) and self.pos > 0:
            self.pos -= 1
            a.play("menu_move")
        elif "confirm" in m or "fire" in own or "right" in m:
            a.play("menu_select")
            self.pos += 1
            if self.pos >= 3:
                self._commit()
                return
            self.letters[self.pos] = self.letters[self.pos - 1]
        self.timeout -= 1
        if self.timeout <= 0:
            self._commit()

    def _commit(self):
        g = self.game
        s = self.session
        name = "".join(LETTERS[i] for i in self.letters)
        self.last_rank = g.highscores.insert(name, self.score, s.sector, s.lap)
        if self.queue:
            # re-check: the first entry may have pushed the second off the table
            self.queue = [(pi, sc) for pi, sc in self.queue if g.highscores.qualifies(sc)]
        if self.queue:
            self._start_next()
        else:
            from scenes.highscore_view import HighScoreView
            g.switch(HighScoreView(g, highlight=self.last_rank, then_title=True))

    def draw(self, surf):
        surf.fill(rgb(BLACK))
        font = self.game.font
        p = self.session.players[self.player]
        col = P1_COLOR if p.idx == 0 else P2_COLOR
        font.draw_center(surf, "NEW HIGH SCORE!", 40, 0x28 if (self.t >> 3) & 1 else 0x38)
        font.draw_center(surf, p.name + " PILOT", 64, col)
        font.draw_center(surf, "%07d" % self.score, 78, 0x30)
        font.draw_center(surf, "ENTER YOUR INITIALS", 104, 0x3C)
        x0 = 128 - 3 * 12 + 2
        for i in range(3):
            ch = LETTERS[self.letters[i]]
            x = x0 + i * 24
            c = 0x30
            if i == self.pos:
                c = 0x28
                if (self.t >> 3) & 1:
                    font.draw(surf, "^", x, 116, 0x26)
                    font.draw(surf, "v", x, 144, 0x26)
            if ch == " ":
                ch = "_"
            font.draw(surf, ch, x, 130, c)
        font.draw_center(surf, "UP/DOWN: LETTER", 176, 0x00)
        font.draw_center(surf, "FIRE: OK  BOMB: BACK", 188, 0x00)
