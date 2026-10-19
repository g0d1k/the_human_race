"""Story intro: typewriter text over pixel-art scenes. Any input skips it."""
import math

from config import rgb, BLACK
from scenes.base import Scene, wrap
from graphics.background import Starfield, make_planet

PAGES = [
    ("stars", "YEAR 2291.\n\nFOR A MILLION YEARS, THE ELDER SPECIES OF THE GALAXY HAVE HELD "
              "THE RACE: A BRUTAL GAUNTLET ACROSS THE STARS."),
    ("earth", "EVERY YOUNG CIVILIZATION IS ENTERED WHETHER IT WANTS TO BE OR NOT. "
              "FINISH, AND YOUR WORLD EARNS ITS PLACE AMONG THE STARS. "
              "FAIL, AND YOUR WORLD IS HARVESTED."),
    ("fleet", "THE RACE'S KEEPERS, THE VEXARI, HAVE NEVER LOST A CONTENDER THEY "
              "DIDN'T WANT TO LOSE.\n\nTODAY, EARTH RECEIVED ITS INVITATION."),
    ("ships", "HUMANITY'S FLEETS WERE SCATTERED IN THE FIRST HOUR. ONLY TWO "
              "EXPERIMENTAL FIGHTERS REMAIN: THE CRIMSON ARES-1 AND THE EMERALD GAIA-2."),
    ("launch", "SIX SECTORS. SIX VEXARI CHAMPIONS. ONE FINISH LINE.\n\n"
               "THE HUMAN RACE HAS BEGUN."),
]

HIGHLIGHTS = {
    "YEAR": 0x28, "2291.": 0x28, "VEXARI": 0x24, "VEXARI,": 0x24, "ARES-1": 0x26,
    "GAIA-2": 0x2A, "GAIA-2.": 0x2A, "RACE:": 0x28, "HARVESTED.": 0x16,
    "HUMAN": 0x28, "BEGUN.": 0x28,
}

TEXT_COLS = 30
TEXT_X = 8
TEXT_Y = 150
CHAR_FRAMES = 2
HOLD_FRAMES = 150


def _rich_lines(text):
    lines = []
    for line in wrap(text, TEXT_COLS):
        segs = []
        for wi, word in enumerate(line.split(" ")):
            col = HIGHLIGHTS.get(word, 0x30)
            if wi > 0:
                segs.append((" ", 0x30))
            for ch in word:
                segs.append((ch, col))
        lines.append(segs)
    # "THE HUMAN RACE HAS BEGUN." highlights the whole phrase
    return lines


class Intro(Scene):
    def __init__(self, game, attract=False):
        Scene.__init__(self, game)
        self.attract = attract
        self.page = 0
        self.pt = 0
        self.revealed = False
        self.stars = Starfield(seed=3)
        self.earth = make_planet(40, "earth", 5)
        self.moon = make_planet(9, "moon", 3)
        self.pages = [(kind, _rich_lines(text)) for kind, text in PAGES]
        self.page_len = [sum(len(l) for l in lines) for _, lines in self.pages]

    def enter(self):
        self.game.audio.play_music("story", restart=True)

    def update(self):
        self.t += 1
        self.pt += 1
        inp = self.game.input
        kind = self.pages[self.page][0]
        self.stars.speed = 4.0 if kind == "launch" else 0.6
        self.stars.update()
        if self.pt // CHAR_FRAMES >= self.page_len[self.page]:
            self.revealed = True
        pressed = self.t > 5 and (inp.any_pressed or inp.menu)
        if self.attract:
            # replaying by itself: pages turn on their own; any input exits
            if pressed:
                self.finish()
            elif self.revealed and self.pt >= self.page_len[self.page] * CHAR_FRAMES + HOLD_FRAMES:
                self._next_page()
            return
        if not pressed:
            return
        if "back" in inp.menu:
            self.finish()               # Esc / B / Back skips the whole story
        elif not self.revealed:
            self.revealed = True        # first press: show the rest of the page
        else:
            self._next_page()           # next press: turn the page
            self.game.audio.play("menu_move")

    def _next_page(self):
        self.page += 1
        self.pt = 0
        self.revealed = False
        if self.page >= len(self.pages):
            self.finish()

    def finish(self):
        from scenes.title import Title
        self.game.switch(Title(self.game, skip_press=False))

    def draw(self, surf):
        surf.fill(rgb(BLACK))
        self.stars.draw(surf)
        if self.page >= len(self.pages):
            return
        kind, lines = self.pages[self.page]
        sp = self.game.sprites
        t = self.pt
        if kind == "stars":
            # a distant spiral of stars
            for i in range(60):
                a = i * 0.45 + t * 0.003
                r = 4 + i * 0.9
                x = 128 + int(math.cos(a) * r * 1.4)
                y = 72 + int(math.sin(a) * r * 0.6)
                c = (0x30, 0x3C, 0x31, 0x24)[i % 4]
                surf.fill(rgb(c), (x, y, 1, 1))
            surf.fill(rgb(0x38), (127, 71, 3, 3))
        elif kind == "earth":
            surf.blit(self.earth, (128 - self.earth.get_width() // 2, 30))
            mx = 128 + int(math.cos(t * 0.01) * 60) - 9
            my = 70 + int(math.sin(t * 0.01) * 14) - 9
            surf.blit(self.moon, (mx, my))
        elif kind == "fleet":
            boss = sp["arbiter"]
            bx = 256 - min(t, 160) * 0.6
            surf.blit(boss.img, (int(bx), 50))
            for row in range(3):
                for col in range(4):
                    kinds = ("drone", "gunner", "diver", "spreader")
                    s = sp[kinds[(row + col) % 4]]
                    x = int(bx) - 20 - col * 24 + (row % 2) * 10
                    y = 34 + row * 34 + int(math.sin((t + col * 20) * 0.05) * 3)
                    surf.blit(s.img, (x, y))
        elif kind in ("ships", "launch"):
            fast = kind == "launch"
            for i, name in enumerate(("ares", "gaia")):
                s = sp[name]
                base_x = 70 + i * 40 if not fast else 60 + i * 40 + min(t, 200) * 0.3
                x = int(base_x)
                y = 56 + i * 40 + int(math.sin((t + i * 30) * 0.06) * 3)
                fl = sp["flame%d" % ((t >> 2) & 1)]
                surf.blit(fl.img, (x - 7, y + 6))
                surf.blit(s.img, (x, y))
                if not fast:
                    label = "ARES-1" if i == 0 else "GAIA-2"
                    self.game.font.draw(surf, label, x + 24, y + 4, 0x26 if i == 0 else 0x2A)
        # typewriter text
        shown = self.page_len[self.page] if self.revealed else self.pt // CHAR_FRAMES
        y = TEXT_Y if len(lines) <= 9 else 140
        font = self.game.font
        for segs in lines:
            if shown <= 0:
                break
            font.draw_rich(surf, segs, TEXT_X, y, limit=shown)
            shown -= len(segs)
            y += 9
        if not self.attract:
            font.draw_right(surf, "ESC/B: SKIP", 250, 2, 0x00)
            if self.revealed and (self.t >> 5) & 1 == 0:
                last = self.page == len(self.pages) - 1
                font.draw_right(surf, "PRESS START }" if last else "NEXT }", 250, 230, 0x28)
