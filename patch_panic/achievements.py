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

"""Achievements: small goals that stay unlocked across games.

Each `Achievement` is plain data plus a test on the current `RunStats`. The
`AchievementTracker` re-checks them whenever a game event happens, saves new
unlocks and announces them on the event bus. Adding an achievement means
adding one entry to `ACHIEVEMENTS` (and, if it needs a new number, a counter
in `RunStats`).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .config import COMBO_MAX, GameMode
from .events import Event, EventBus
from .stats import RunStats
from .storage import SaveStore


@dataclass(frozen=True)
class Achievement:
    id: str
    title: str
    description: str
    earned: Callable[[RunStats], bool]


ACHIEVEMENTS: tuple[Achievement, ...] = (
    Achievement("first_swat", "First Swat", "Swat your first gremlin", lambda s: s.swats >= 1),
    Achievement("combo_max", "Combo Master", f"Reach a x{COMBO_MAX} combo", lambda s: s.best_combo >= COMBO_MAX),
    Achievement("disk_saver", "Disk Saver", "Restore 5 disks in one level", lambda s: s.level_restores >= 5),
    Achievement("chain_breaker", "Chain Breaker", "Zap a surge that jumped on", lambda s: s.chain_zaps >= 1),
    Achievement("flawless", "Flawless", "Finish a level with every machine clean", lambda s: s.perfect_levels >= 1),
    Achievement("heavy_metal", "Heavy Metal", "Swat an armored gremlin", lambda s: s.armored_swats >= 1),
    Achievement("sysadmin", "Sysadmin", "Reach level 10", lambda s: s.level >= 10),
    Achievement("daily_driver", "Daily Driver", "Reach level 5 in a Daily Challenge",
                lambda s: s.mode is GameMode.DAILY and s.level >= 5),
)

# Events after which some achievement might have become true.
WATCHED_EVENTS = (Event.LEVEL_STARTED, Event.GREMLIN_SQUASHED, Event.SURGE_ZAPPED, Event.OS_RESTORED,
                  Event.COMBO, Event.PERFECT_LEVEL)


class AchievementTracker:
    def __init__(self, stats: RunStats, save: SaveStore) -> None:
        self.stats = stats
        self.save = save
        self.enabled = True  # off for the tutorial

    def connect(self, bus: EventBus) -> None:
        """Subscribe after `RunStats` so the stats are already updated when we check."""
        for event in WATCHED_EVENTS:
            bus.subscribe(event, lambda **_: self.check(bus))

    def check(self, bus: EventBus) -> None:
        if not self.enabled:
            return
        for achievement in ACHIEVEMENTS:
            if achievement.id not in self.save.achievements and achievement.earned(self.stats):
                self.save.unlock(achievement.id)
                bus.emit(Event.ACHIEVEMENT_UNLOCKED, achievement=achievement)
