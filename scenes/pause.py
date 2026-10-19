"""Pause overlay: palette-dimmed snapshot of the game plus a small menu."""
from scenes.base import Scene, Menu, draw_box
from graphics.display import dim_surface


class Pause(Scene):
    def __init__(self, game, gameplay):
        Scene.__init__(self, game)
        self.gameplay = gameplay
        self.menu = Menu(("RESUME", "CONTROLS", "SETTINGS", "QUIT TO TITLE"), 108, 12, x=80)
        self.confirm = None
        self.snapshot = None

    def enter(self):
        g = self.game
        g.audio.pause_all()
        g.audio.play("pause")
        self._snap()

    def _snap(self):
        surf = self.game.display.surface.copy()
        self.gameplay.draw(surf)
        self.snapshot = dim_surface(surf, 2)

    def resume(self):
        # returning from CONTROLS / SETTINGS: refresh the snapshot
        self._snap()

    def _resume_game(self):
        self.game.audio.play("pause")
        self.game.pop()

    def update(self):
        self.t += 1
        g = self.game
        inp = g.input
        if self.confirm is not None:
            r = self.confirm.update(g)
            if r == "confirm":
                if self.confirm.index == 0:
                    g.audio.resume_all()
                    g.audio.stop_music()
                    g.audio.stop_sfx()
                    from scenes.title import Title
                    g.switch(Title(g, skip_press=True))
                else:
                    self.confirm = None
            elif r == "back":
                self.confirm = None
            return
        if self.t > 2 and any("pause" in inp.pressed[i] for i in range(2)):
            self._resume_game()
            return
        r = self.menu.update(g)
        if r == "back":
            self._resume_game()
        elif r == "confirm":
            i = self.menu.index
            if i == 0:
                self._resume_game()
            elif i == 1:
                from scenes.controls_menu import ControlsMenu
                g.push(ControlsMenu(g))
            elif i == 2:
                from scenes.settings_menu import SettingsMenu
                g.push(SettingsMenu(g))
            elif i == 3:
                self.confirm = Menu(("YES", "NO"), 130, 12, x=112)
                self.confirm.index = 1

    def draw(self, surf):
        surf.blit(self.snapshot, (0, 0))
        font = self.game.font
        draw_box(surf, 56, 78, 144, 88)
        font.draw_center(surf, "PAUSED", 88, 0x28)
        if self.confirm is not None:
            font.draw_center(surf, "QUIT TO TITLE?", 112, 0x30)
            self.confirm.draw(surf, font, self.t)
        else:
            self.menu.draw(surf, font, self.t)
