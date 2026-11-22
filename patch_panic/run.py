# Patch Panic - defend your workstations from bloatware gremlins.
# Copyright (C) 2026 Kamran Zafar
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""What kind of game is being played: mode, difficulty and random seed.

A `Run` is created on the title screen and handed from level to level, so
every level of a Daily Challenge is built from the same seed and every level
of a Classic game uses the chosen difficulty.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date

from .config import Difficulty, GameMode, LevelConfig


@dataclass(frozen=True)
class Run:
    mode: GameMode = GameMode.CLASSIC
    difficulty: Difficulty = Difficulty.NORMAL
    seed: int | None = None  # None: a fresh random game

    @classmethod
    def classic(cls, difficulty: Difficulty = Difficulty.NORMAL) -> Run:
        return cls(GameMode.CLASSIC, difficulty)

    @classmethod
    def daily(cls, today: date | None = None) -> Run:
        """Same seed for everyone on the same day; difficulty is fixed so scores compare."""
        today = today or date.today()
        return cls(GameMode.DAILY, Difficulty.NORMAL, int(today.strftime("%Y%m%d")))

    def level_config(self, level: int) -> LevelConfig:
        return LevelConfig.for_level(level, self.difficulty)

    def level_rng(self, level: int) -> random.Random:
        if self.seed is None:
            return random.Random()
        return random.Random(self.seed * 1000 + level)
