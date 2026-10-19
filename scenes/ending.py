"""Ending sequence and credits, then on to the next lap."""
import math

from config import rgb, BLACK
from scenes.base import Scene, wrap
from graphics.background import Starfield, make_planet

STORY = (
    "THE ARBITER FALLS. FOR THE FIRST TIME IN A MILLION YEARS, A CONTENDER "
    "HAS CROSSED THE FINISH LINE THAT THE VEXARI DID NOT CHOOSE.\n\n"
    "EARTH HAS EARNED ITS PLACE AMONG THE STARS.\n\n"
    "BUT THE VEXARI ARE SORE LOSERS..."
)

CREDITS = [
    ("THE HUMAN RACE", 0x28),
    ("", 0),
    ("A PYGAME TRIBUTE TO", 0x3C),
    ("THE 8-BIT SHOOTERS", 0x3C),
    ("", 0),
    ("PILOTS", 0x28),
    ("ARES-1 ..... YOU", 0x26),
    ("GAIA-2 ..... A FRIEND", 0x2A),
    ("", 0),
    ("VEXARI CHAMPIONS", 0x28),
    ("SENTINEL", 0x30),
    ("HIVE MOTHER", 0x30),
    ("TEMPEST", 0x30),
    ("CRYO-LANCER", 0x30),
    ("REVENANT", 0x30),
    ("THE ARBITER", 0x30),
    ("", 0),
    ("EVERY PIXEL, NOTE AND GLYPH", 0x3C),
    ("GENERATED IN CODE", 0x3C),
    ("", 0),
    ("THANK YOU FOR PLAYING!", 0x28),
    ("", 0),
    ("", 0),
    ("LAP 2 BEGINS...", 0x26),
]


class Ending(Scene):
    def __init__(self, game, session):
        Scene.__init__(self, game)
        self.session = session
        self.stars = Starfield(seed=77)
        self.earth = make_planet(30, "earth", 5)
        self.lines = wrap(STORY, 30)
        self.stage = "story"
        self.st = 0

    def enter(self):
        self.game.audio.play_music("title", restart=True)

    def update(self):
        self.t += 1
        self.st += 1
        self.stars.speed = 0.6 if self.stage == "story" else 1.5
        self.stars.update()
        inp = self.game.input
        if self.stage == "story":
            total = sum(len(l) for l in self.lines) * 2 + 180
            if self.st > total or (self.st > 60 and "confirm" in inp.menu):
                self.stage = "credits"
                self.st = 0
        else:
            end = len(CREDITS) * 14 * 2 + 360
            if self.st > end or (self.st > 60 and "confirm" in inp.menu):
                self.next_lap()

    def next_lap(self):
        s = self.session
        s.lap += 1
        s.sector = 1
        from scenes.gameplay import Gameplay
        self.game.switch(Gameplay(self.game, s))

    def draw(self, surf):
        surf.fill(rgb(BLACK))
        self.stars.draw(surf)
        font = self.game.font
        sp = self.game.sprites
        if self.stage == "story":
            surf.blit(self.earth, (128 - self.earth.get_width() // 2, 24))
            for i, name in enumerate(("ares", "gaia")):
                x = 40 + i * 140 + int(math.sin(self.t * 0.03 + i) * 4)
                y = 60 + int(math.cos(self.t * 0.04 + i) * 3)
                surf.blit(sp["flame%d" % ((self.t >> 2) & 1)].img, (x - 7, y + 6))
                surf.blit(sp[name].img, (x, y))
            shown = self.st // 2
            y = 120
            for line in self.lines:
                if shown <= 0:
                    break
                font.draw(surf, line[:shown], 8, y, 0x30)
                shown -= len(line)
                y += 10
        else:
            y0 = 240 - self.st // 2
            for i, (text, col) in enumerate(CREDITS):
                y = y0 + i * 14
                if -8 < y < 240 and text:
                    font.draw_center(surf, text, y, col)
