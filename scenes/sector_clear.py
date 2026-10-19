"""SECTOR CLEAR screen with an animated score tally."""
from config import rgb, BLACK, P1_COLOR, P2_COLOR
from scenes.base import Scene
from graphics.background import Starfield

NO_MISS_BONUS = 2000


class SectorClear(Scene):
    def __init__(self, game, session, boss_bonus, boss_name):
        Scene.__init__(self, game)
        self.session = session
        self.boss_bonus = boss_bonus
        self.boss_name = boss_name
        self.stars = Starfield(seed=session.sector * 5)
        self.stars.speed = 3.0
        self.rows = []
        mult = 1 + (session.lap - 1)
        for p in session.players:
            if p.joined:
                nm = NO_MISS_BONUS * session.sector * mult if p.deaths_this_sector == 0 and p.active_in_game else 0
                self.rows.append([p, nm, 0])
        self.done = False
        self.awarded = False

    def update(self):
        self.t += 1
        self.stars.update()
        g = self.game
        inp = g.input
        if self.t > 80 and not self.awarded:
            # count the no-miss bonus up into each score
            busy = False
            step = g.settings["extra_life"]
            for row in self.rows:
                p, bonus, shown = row
                if shown < bonus:
                    inc = min(bonus - shown, 250)
                    row[2] += inc
                    busy = True
            if self.t % 4 == 0 and busy:
                g.audio.play("tally")
            if not busy:
                self.awarded = True
                for p, bonus, _ in self.rows:
                    if bonus:
                        p.score = min(9999999, p.score + bonus)
                        while p.score >= p.next_extra:
                            p.next_extra += step
                            if p.lives < 9:
                                p.lives += 1
                            g.audio.play("oneup")
        if self.awarded and (self.t > 420 or (self.t > 120 and ("confirm" in inp.menu or inp.any_pressed))):
            self.next()

    def next(self):
        g = self.game
        s = self.session
        if s.sector >= 6:
            from scenes.ending import Ending
            g.switch(Ending(g, s))
        else:
            s.sector += 1
            from scenes.gameplay import Gameplay
            g.switch(Gameplay(g, s))

    def draw(self, surf):
        surf.fill(rgb(BLACK))
        self.stars.draw(surf)
        font = self.game.font
        s = self.session
        font.draw_center(surf, "SECTOR %d CLEAR!" % s.sector, 40, 0x28, shadow=BLACK)
        font.draw_center(surf, self.boss_name + " DESTROYED", 58, 0x30, shadow=BLACK)
        font.draw_center(surf, "BOSS BONUS  %6d" % self.boss_bonus, 82, 0x3C, shadow=BLACK)
        y = 108
        for p, bonus, shown in self.rows:
            col = P1_COLOR if p.idx == 0 else P2_COLOR
            font.draw(surf, p.name, 40, y, col, shadow=BLACK)
            score = p.score + (0 if self.awarded else shown)
            font.draw(surf, "%07d" % score, 160, y, 0x30, shadow=BLACK)
            if bonus and self.t > 80:
                font.draw(surf, "NO MISS BONUS", 40, y + 12, 0x2A, shadow=BLACK)
                font.draw(surf, "%6d" % bonus, 168, y + 12, 0x2A, shadow=BLACK)
            y += 32
        if self.awarded and (self.t >> 4) & 1:
            nxt = "NEXT: SECTOR %d" % (s.sector + 1) if s.sector < 6 else "THE FINISH LINE..."
            font.draw_center(surf, nxt, 200, 0x30, shadow=BLACK)
