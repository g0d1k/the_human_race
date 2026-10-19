"""THE HUMAN RACE - an 8-bit NES-style horizontal space shooter.

Entry point: sets up pygame, pre-renders all graphics and audio, then runs a
fixed-timestep (60 Hz) game loop driving a stack-based scene machine.
"""
import os
import sys

# Make the package importable no matter where we're launched from
# (also handles PyInstaller's one-file extraction directory).
_HERE = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import pygame

import config
from config import FPS, rgb, BLACK
from graphics.display import Display
from graphics.font import Font
from graphics.sprites import SpriteBank
from audio.manager import Audio
from input.manager import InputManager
from highscores import HighScores

STEP = 1.0 / FPS
MAX_STEPS = 4      # below 15 fps the game slows down instead of skipping logic


class Game:
    def __init__(self):
        try:
            pygame.mixer.pre_init(22050, -16, 1, 512)
        except pygame.error:
            pass
        pygame.init()
        self.settings = config.Settings()
        self.display = Display(self.settings)
        self.font = Font()
        self.sprites = SpriteBank()
        self.audio = Audio(self.settings)
        self.input = InputManager(self.settings)
        self.highscores = HighScores()
        self.scenes = []
        self.running = True
        self.frame = 0
        self.notice = None
        self.notice_t = 0
        self._set_icon()

    def _set_icon(self):
        try:
            icon = pygame.Surface((32, 32))
            icon.fill(rgb(BLACK))
            img = pygame.transform.scale(self.sprites["ares"].img, (32, 32))
            icon.blit(img, (0, 0))
            pygame.display.set_icon(icon)
        except pygame.error:
            pass

    # ------------------------------------------------------------------
    # Scene stack
    # ------------------------------------------------------------------
    @property
    def scene(self):
        return self.scenes[-1] if self.scenes else None

    def push(self, scene):
        self.scenes.append(scene)
        self.input.consume()
        scene.enter()

    def pop(self):
        if self.scenes:
            self.scenes.pop().exit()
        self.input.consume()
        if self.scenes:
            self.scenes[-1].resume()

    def switch(self, scene):
        while self.scenes:
            self.scenes.pop().exit()
        self.push(scene)

    def quit(self):
        self.running = False

    def show_notice(self, text, frames=150):
        self.notice = text[:32]
        self.notice_t = frames

    # ------------------------------------------------------------------
    def _loading(self):
        """Render all audio while showing a progress bar."""
        surf = self.display.surface
        for frac in self.audio.build():
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.running = False
                    return
                self.input.process_event(e)   # keep controller hot-plug events
            surf.fill(rgb(BLACK))
            self.font.draw_center(surf, "THE HUMAN RACE", 96, 0x26)
            self.font.draw_center(surf, "LOADING", 116, 0x30)
            surf.fill(rgb(0x00), (64, 132, 128, 8))
            surf.fill(rgb(0x2A), (65, 133, int(126 * frac), 6))
            self.display.present()
        # pre-render every sector's planets and the nebula so sector loads don't hitch
        from graphics import background
        for defs in background.SECTOR_PLANETS.values():
            for style, r, _, seed in defs:
                background.make_planet(r, style, seed)
                for e in pygame.event.get():
                    self._handle_event(e)
        background.make_nebula(256, 200, 99)

    def _handle_event(self, e):
        if e.type == pygame.QUIT:
            self.running = False
            return
        if e.type == pygame.KEYDOWN:
            alt = e.mod & pygame.KMOD_ALT
            if e.key == pygame.K_F11 or (alt and e.key in (pygame.K_RETURN, pygame.K_KP_ENTER)):
                self.display.toggle_fullscreen()
                return
        self.input.process_event(e)

    def run(self):
        self._loading()
        if not self.running:
            return
        from scenes.intro import Intro
        self.switch(Intro(self, attract=False))
        clock = pygame.time.Clock()
        acc = 0.0
        while self.running and self.scenes:
            dt = clock.tick(FPS) / 1000.0
            acc += min(dt, 0.25)
            for e in pygame.event.get():
                self._handle_event(e)
            if not self.running:
                break
            for name in self.input.connected:
                self.show_notice("CONNECTED: " + str(name).upper())
            for i in self.input.disconnected:
                self.show_notice("P%d CONTROLLER DISCONNECTED" % (i + 1))
            steps = 0
            while acc >= STEP and steps < MAX_STEPS and self.running and self.scenes:
                self.input.update()
                self.scenes[-1].update()
                self.input.end_frame()
                self.frame += 1
                if self.notice_t > 0:
                    self.notice_t -= 1
                acc -= STEP
                steps += 1
            if steps >= MAX_STEPS:
                acc = 0.0
            if not self.scenes or not self.running:
                break
            scene = self.scenes[-1]
            surf = self.display.surface
            scene.draw(surf)
            if self.notice_t > 0 and self.notice:
                surf.fill(rgb(BLACK), (0, 228, 256, 12))
                self.font.draw_center(surf, self.notice, 230, 0x38)
            sx, sy = scene.shake_offset()
            self.display.present(sx, sy)
        self.settings.save()


def main():
    game = Game()
    try:
        game.run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
