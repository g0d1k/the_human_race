"""Difficulty scaling per sector, lap and the EASY/NORMAL/HARD setting."""

BASE = (0.72, 1.0, 1.32)   # EASY, NORMAL, HARD


class Difficulty:
    def __init__(self, sector, lap, setting, players=1):
        self.sector = sector
        self.lap = lap
        self.setting = setting
        lvl = BASE[max(0, min(2, setting))] + 0.14 * (sector - 1) + 0.6 * (lap - 1)
        self.level = lvl
        self.speed = 0.85 + 0.15 * lvl            # enemy movement speed multiplier
        self.bullet_speed = 0.80 + 0.20 * lvl     # enemy bullet speed multiplier
        self.fire_rate = 0.55 + 0.45 * lvl        # higher = shoots more often
        self.hp = 0.75 + 0.25 * lvl               # enemy HP multiplier
        self.aim = min(0.95, 0.15 + 0.15 * lvl)   # chance a "simple" shot is aimed
        self.density = lvl                        # gates the optional extra waves
        self.spread_count = 5 if (sector >= 4 or lap > 1 or setting == 2) else 3
        self.boss_hp = (0.8 + 0.2 * lvl) * (1.45 if players > 1 else 1.0)
        self.score_mult = 1 + (lap - 1)

    def cooldown(self, frames):
        """Scale a firing cooldown (in frames) by the fire-rate multiplier."""
        return max(8, int(frames / self.fire_rate))

    def enemy_hp(self, base):
        return max(1, int(round(base * self.hp)))
