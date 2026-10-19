"""SETTINGS: volumes, window, difficulty, extra-life threshold, effects."""
from config import rgb, BLACK, DIFFICULTY_NAMES, EXTRA_LIFE_OPTIONS, SCALE_OPTIONS
from scenes.base import Scene, Menu
from graphics.background import Starfield

ITEMS = ("MUSIC VOLUME", "SFX VOLUME", "WINDOW SCALE", "FULLSCREEN", "DIFFICULTY",
         "EXTRA LIFE", "SCANLINES", "SCREEN SHAKE", "BACK")


class SettingsMenu(Scene):
    def __init__(self, game):
        Scene.__init__(self, game)
        self.menu = Menu(ITEMS, 44, 16, x=24)
        self.stars = Starfield(seed=41)

    def _value(self, i):
        s = self.game.settings
        if i == 0:
            return "%2d" % s["music_volume"]
        if i == 1:
            return "%2d" % s["sfx_volume"]
        if i == 2:
            return "%dX" % s["scale"]
        if i == 3:
            return "ON" if s["fullscreen"] else "OFF"
        if i == 4:
            return DIFFICULTY_NAMES[s["difficulty"]]
        if i == 5:
            return "%d" % s["extra_life"]
        if i == 6:
            return "ON" if s["scanlines"] else "OFF"
        if i == 7:
            return "ON" if s["shake"] else "OFF"
        return ""

    def _change(self, i, d):
        g = self.game
        s = g.settings
        if i == 0:
            s["music_volume"] = max(0, min(10, s["music_volume"] + d))
            g.audio.apply_volumes()
        elif i == 1:
            s["sfx_volume"] = max(0, min(10, s["sfx_volume"] + d))
            g.audio.apply_volumes()
            g.audio.play("powerup")
        elif i == 2:
            idx = SCALE_OPTIONS.index(s["scale"])
            s["scale"] = SCALE_OPTIONS[(idx + d) % len(SCALE_OPTIONS)]
            if not s["fullscreen"]:
                g.display.apply_mode()
        elif i == 3:
            g.display.toggle_fullscreen()
        elif i == 4:
            s["difficulty"] = (s["difficulty"] + d) % 3
        elif i == 5:
            idx = EXTRA_LIFE_OPTIONS.index(s["extra_life"])
            s["extra_life"] = EXTRA_LIFE_OPTIONS[(idx + d) % len(EXTRA_LIFE_OPTIONS)]
        elif i == 6:
            s["scanlines"] = not s["scanlines"]
        elif i == 7:
            s["shake"] = not s["shake"]
        if i != 1:
            g.audio.play("menu_move")

    def update(self):
        self.t += 1
        self.stars.update()
        r = self.menu.update(self.game)
        i = self.menu.index
        if r == "back" or (r == "confirm" and i == len(ITEMS) - 1):
            self.game.settings.save()
            self.game.pop()
        elif r == "left":
            self._change(i, -1)
        elif r in ("right", "confirm"):
            self._change(i, 1)

    def draw(self, surf):
        surf.fill(rgb(BLACK))
        self.stars.draw(surf)
        font = self.game.font
        font.draw_center(surf, "SETTINGS", 18, 0x28, shadow=BLACK)
        self.menu.draw(surf, font, self.t)
        for i in range(len(ITEMS) - 1):
            v = self._value(i)
            col = 0x28 if i == self.menu.index else 0x3C
            font.draw_right(surf, "{ " + v + " }" if i == self.menu.index else v, 240, 44 + i * 16, col)
            if i in (0, 1):
                # volume bar
                lvl = int(v)
                for k in range(10):
                    c = 0x2A if k < lvl else 0x00
                    surf.fill(rgb(c), (132 + k * 5, 47 + i * 16, 4, 3))
        g = self.game
        if g.settings["fullscreen"] and self.menu.index == 2:
            font.draw_center(surf, "(APPLIES IN WINDOW MODE)", 196, 0x00)
        font.draw_center(surf, "F11 / ALT+ENTER: FULLSCREEN", 214, 0x00)
