"""Title screen: logo, parallax stars, drifting planet, main menu."""
from config import rgb, BLACK
from scenes.base import Scene, Menu
from graphics.background import Starfield, make_planet
from graphics.font import build_logo_text, GLYPHS

IDLE_ATTRACT = 30 * 60

_logo_cache = {}


def get_logo():
    if "big" not in _logo_cache:
        _logo_cache["big"] = build_logo_text(GLYPHS, "HUMAN RACE", 3, [0x16, 0x26, 0x27, 0x28], 0x06, 0x0F)
        _logo_cache["the"] = build_logo_text(GLYPHS, "THE", 2, [0x31, 0x21, 0x11], 0x01, 0x0F)
    return _logo_cache["the"], _logo_cache["big"]


class Title(Scene):
    MAIN = ("START GAME", "HOW TO PLAY", "HIGH SCORES", "SETTINGS", "CONTROLS", "QUIT")

    def __init__(self, game, skip_press=False):
        Scene.__init__(self, game)
        self.state = "menu" if skip_press else "press"
        self.menu = Menu(self.MAIN, 134, 12, x=88)
        self.sub = Menu(("1 PLAYER", "2 PLAYERS", "BACK"), 146, 12, x=92)
        self.stars = Starfield(seed=21)
        self.planet = make_planet(34, "ice", 23)
        self.px = 300.0
        self.idle = 0
        self.the_logo, self.logo = get_logo()

    def enter(self):
        self.game.audio.play_music("title")

    def resume(self):
        self.game.audio.play_music("title")
        self.idle = 0

    def update(self):
        self.t += 1
        self.stars.speed = 0.8
        self.stars.update()
        self.px -= 0.08
        if self.px < -self.planet.get_width():
            self.px = 300.0
        inp = self.game.input
        if inp.any_pressed or inp.menu:
            self.idle = 0
        else:
            self.idle += 1
        if self.idle > IDLE_ATTRACT:
            from scenes.intro import Intro
            self.game.switch(Intro(self.game, attract=True))
            return
        if self.state == "press":
            if self.t > 20 and ("confirm" in inp.menu or inp.any_pressed):
                self.state = "menu"
                self.game.audio.play("menu_select")
            return
        if self.state == "menu":
            r = self.menu.update(self.game)
            if r == "confirm":
                self._choose(self.menu.index)
            elif r == "back":
                self.state = "press"
        elif self.state == "players":
            r = self.sub.update(self.game)
            if r == "confirm":
                if self.sub.index == 2:
                    self.state = "menu"
                else:
                    self._start(self.sub.index + 1)
            elif r == "back":
                self.state = "menu"

    def _choose(self, i):
        g = self.game
        if i == 0:
            self.state = "players"
            self.sub.index = 0
        elif i == 1:
            from scenes.howto import HowToPlay
            g.push(HowToPlay(g))
        elif i == 2:
            from scenes.highscore_view import HighScoreView
            g.push(HighScoreView(g))
        elif i == 3:
            from scenes.settings_menu import SettingsMenu
            g.push(SettingsMenu(g))
        elif i == 4:
            from scenes.controls_menu import ControlsMenu
            g.push(ControlsMenu(g))
        elif i == 5:
            g.quit()

    def _start(self, players):
        from scenes.gameplay import Session, Gameplay
        session = Session(self.game, players)
        self.game.switch(Gameplay(self.game, session))

    def draw(self, surf):
        surf.fill(rgb(BLACK))
        surf.blit(self.planet, (int(self.px), 150))
        self.stars.draw(surf)
        font = self.game.font
        lw = self.logo.get_width()
        bob = 0
        surf.blit(self.the_logo, (128 - self.the_logo.get_width() // 2, 34 + bob))
        surf.blit(self.logo, (128 - lw // 2, 58 + bob))
        font.draw_center(surf, "6 SECTORS. 1 FINISH LINE.", 96, 0x3C)
        if self.state == "press":
            if (self.t >> 5) & 1 == 0:
                font.draw_center(surf, "PRESS START", 150, 0x30, shadow=BLACK)
        elif self.state == "menu":
            self.menu.draw(surf, font, self.t)
        else:
            font.draw_center(surf, "START GAME", 130, 0x28)
            self.sub.draw(surf, font, self.t)
        hi = self.game.highscores.top_score()
        font.draw_center(surf, "HI %07d" % hi, 12, 0x30)
        font.draw_center(surf, "@2026 HUMAN RACE PROJECT", 222, 0x00)
