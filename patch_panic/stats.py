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

"""Statistics for the current game, collected from game events.

`RunStats` is another event-bus subscriber, like the sounds and effects: the
game rules don't count anything themselves. The game-over screen and the
achievements read these numbers.
"""
from __future__ import annotations

from .config import GameMode, Gremlins
from .events import Event, EventBus


class RunStats:
    def __init__(self) -> None:
        self.reset(GameMode.CLASSIC)

    def reset(self, mode: GameMode) -> None:
        self.mode = mode
        self.level = 0
        self.hits = 0
        self.misses = 0
        self.swats = 0
        self.armored_swats = 0
        self.zaps = 0
        self.chain_zaps = 0
        self.restores = 0
        self.level_restores = 0
        self.best_combo = 0
        self.perfect_levels = 0

    @property
    def accuracy(self) -> float:
        clicks = self.hits + self.misses
        return self.hits / clicks if clicks else 0.0

    def summary_lines(self) -> list[str]:
        return [f"Accuracy {self.accuracy:.0%}   Swats {self.swats}   Zaps {self.zaps}",
                f"Disks restored {self.restores}   Best combo x{max(1, self.best_combo)}"]

    # ----------------------------------------------------------- subscriptions
    def connect(self, bus: EventBus) -> None:
        bus.subscribe(Event.LEVEL_STARTED, self._on_level_started)
        bus.subscribe(Event.CLICK_MISSED, self._on_missed)
        bus.subscribe(Event.GREMLIN_SQUASHED, self._on_squashed)
        bus.subscribe(Event.GREMLIN_HIT, self._on_hit)
        bus.subscribe(Event.SURGE_ZAPPED, self._on_zapped)
        bus.subscribe(Event.DISK_PICKED_UP, self._on_hit)
        bus.subscribe(Event.POWERUP_COLLECTED, self._on_hit)
        bus.subscribe(Event.OS_RESTORED, self._on_restored)
        bus.subscribe(Event.COMBO, self._on_combo)
        bus.subscribe(Event.PERFECT_LEVEL, self._on_perfect)

    def _on_level_started(self, level):
        self.level = level
        self.level_restores = 0

    def _on_missed(self, **_):
        self.misses += 1

    def _on_hit(self, **_):
        self.hits += 1

    def _on_squashed(self, kind, **_):
        self.hits += 1
        self.swats += 1
        if kind is Gremlins.ARMORED:
            self.armored_swats += 1

    def _on_zapped(self, chained, **_):
        self.hits += 1
        self.zaps += 1
        if chained:
            self.chain_zaps += 1

    def _on_restored(self, **_):
        self.restores += 1
        self.level_restores += 1

    def _on_combo(self, count, **_):
        self.best_combo = max(self.best_combo, count)

    def _on_perfect(self, **_):
        self.perfect_levels += 1
