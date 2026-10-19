"""Top-10 high score table."""
from config import rgb, BLACK
from scenes.base import Scene
from graphics.background import Starfield

RANK_COLORS = (0x28, 0x30, 0x27, 0x3C, 0x3C, 0x3C, 0x3C, 0x3C, 0x3C, 0x3C)


class HighScoreView(Scene):
    def __init__(self, game, highlight=None, then_title=False):
        Scene.__init__(self, game)
        self.highlight = highlight
        self.then_title = then_title
        self.stars = Starfield(seed=9)

    def enter(self):
        if self.then_title:
            if self.game.audio.current_music != "highscore":
                self.game.audio.play_music("title")

    def update(self):
        self.t += 1
        self.stars.update()
        inp = self.game.input
        if self.t > 6 and (inp.menu & {"confirm", "back"} or (self.then_title and self.t > 60 * 12)):
            if self.then_title:
                from scenes.title import Title
                self.game.switch(Title(self.game, skip_press=True))
            else:
                self.game.pop()

    def draw(self, surf):
        surf.fill(rgb(BLACK))
        self.stars.draw(surf)
        font = self.game.font
        font.draw_center(surf, "HIGH SCORES", 20, 0x28, shadow=BLACK)
        font.draw(surf, "RANK NAME   SCORE  SECTOR", 24, 44, 0x3C)
        for i, e in enumerate(self.game.highscores.entries):
            y = 60 + i * 14
            col = RANK_COLORS[i]
            if i == self.highlight:
                col = 0x2A if (self.t >> 3) & 1 else 0x30
            sec = "%d" % e["sector"] if e.get("lap", 1) <= 1 else "%d-%d" % (e["lap"], e["sector"])
            font.draw(surf, "%2d." % (i + 1), 24, y, col)
            font.draw(surf, e["name"], 64, y, col)
            font.draw(surf, "%07d" % e["score"], 104, y, col)
            font.draw(surf, sec, 184, y, col)
        if (self.t >> 5) & 1:
            font.draw_center(surf, "PRESS START", 212, 0x30)
