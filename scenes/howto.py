"""HOW TO PLAY: objective, pickups, scoring, and the enemy gallery."""
from config import rgb, BLACK
from scenes.base import Scene, wrap
from graphics.background import Starfield
from entities.enemies import ENEMY_DEFS, GALLERY
from entities.powerups import DESCRIPTIONS


class HowToPlay(Scene):
    def __init__(self, game):
        Scene.__init__(self, game)
        self.page = 0
        self.stars = Starfield(seed=31)
        self.pages = [self._objective, self._pickups, self._scoring,
                      lambda s: self._gallery(s, 0), lambda s: self._gallery(s, 4)]

    def update(self):
        self.t += 1
        self.stars.update()
        m = self.game.input.menu
        n = len(self.pages)
        if "right" in m or "confirm" in m:
            if "confirm" in m and self.page == n - 1:
                self.game.pop()
                return
            self.page = (self.page + 1) % n
            self.game.audio.play("menu_move")
        elif "left" in m:
            self.page = (self.page - 1) % n
            self.game.audio.play("menu_move")
        elif "back" in m:
            self.game.pop()

    def draw(self, surf):
        surf.fill(rgb(BLACK))
        self.stars.draw(surf)
        font = self.game.font
        font.draw_center(surf, "HOW TO PLAY", 8, 0x28, shadow=BLACK)
        self.pages[self.page](surf)
        font.draw_center(surf, "{ PAGE %d/%d }" % (self.page + 1, len(self.pages)), 224, 0x3C)

    def _text(self, surf, text, y, color=0x30, x=12, width=29):
        for line in wrap(text, width):
            self.game.font.draw(surf, line, x, y, color, shadow=BLACK)
            y += 10
        return y

    def _objective(self, surf):
        font = self.game.font
        font.draw_center(surf, "OBJECTIVE", 26, 0x26)
        y = self._text(surf, "SURVIVE SIX SECTORS OF THE VEXARI RACE AND DEFEAT EACH SECTOR'S "
                             "CHAMPION. CLEAR SECTOR 6 TO CROSS THE FINISH LINE.", 42)
        y = self._text(surf, "TWO PLAYERS CAN FLY TOGETHER. THERE IS NO FRIENDLY FIRE.", y + 6)
        y = self._text(surf, "HOLD FIRE FOR AUTOFIRE. BOMBS CLEAR ALL ENEMY BULLETS AND DAMAGE "
                             "EVERY ENEMY ON SCREEN.", y + 6)
        y = self._text(surf, "ONLY THE COCKPIT OF YOUR SHIP CAN BE HIT.", y + 6, 0x3C)
        self._text(surf, "P2 JOINS ANY TIME WITH START (PAD) OR FIRE (KEYBOARD).", y + 6, 0x2A)

    def _pickups(self, surf):
        font = self.game.font
        sp = self.game.sprites
        font.draw_center(surf, "PICKUPS", 26, 0x26)
        y = 44
        for kind, name, desc in DESCRIPTIONS:
            spr = sp["pu_" + kind]
            surf.blit(spr.img, (12, y))
            font.draw(surf, name, 44, y, 0x28)
            font.draw(surf, desc[:26], 44, y + 10, 0x30)
            y += 26
        self._text(surf, "PICKUPS BLINK BEFORE THEY VANISH.", y + 2, 0x3C)

    def _scoring(self, surf):
        font = self.game.font
        font.draw_center(surf, "SCORING & LIVES", 26, 0x26)
        step = self.game.settings["extra_life"]
        y = self._text(surf, "EACH PLAYER HAS 3 LIVES, 2 BOMBS AND THEIR OWN SCORE AND WEAPON.", 42)
        y = self._text(surf, "EXTRA LIFE EVERY %d POINTS." % step, y + 6, 0x28)
        y = self._text(surf, "DESTROY A WHOLE FORMATION FOR A GUARANTEED PICKUP.", y + 6)
        y = self._text(surf, "BOSS BONUS: 5000 X SECTOR. NO-MISS BONUS IF YOU CLEAR A SECTOR "
                             "WITHOUT DYING.", y + 6)
        y = self._text(surf, "DYING COSTS 1 WEAPON LEVEL AND ALL SPEED-UPS.", y + 6, 0x3C)
        self._text(surf, "OUT IN 2P? PRESS START TO TAKE A LIFE FROM YOUR PARTNER (IF THEY HAVE 2+).",
                   y + 6, 0x2A)

    def _gallery(self, surf, start):
        font = self.game.font
        sp = self.game.sprites
        font.draw_center(surf, "THE VEXARI FLEET", 26, 0x26)
        y = 44
        for kind, name, desc in GALLERY[start:start + 4]:
            sprname, hp, pts, _ = ENEMY_DEFS[kind]
            spr = sp[sprname]
            surf.blit(spr.img, (12 + (32 - spr.w) // 2, y + (24 - spr.h) // 2))
            font.draw(surf, name, 52, y, 0x28)
            font.draw(surf, "%d PTS" % pts, 256 - 8 - len("%d PTS" % pts) * 8, y, 0x30)
            font.draw(surf, desc, 52, y + 11, 0x3C)
            y += 42
