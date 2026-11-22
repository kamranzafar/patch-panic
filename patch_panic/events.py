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

"""A minimal publish/subscribe event bus (Observer pattern).

The game rules in `World` announce what happened (a gremlin was squashed, a
computer got fried...) without knowing who cares. Audio and visual effects
subscribe to the events they want to react to.
"""
from __future__ import annotations

from collections import defaultdict
from enum import Enum, auto
from typing import Callable


class Event(Enum):
    SCORED = auto()              # points, x, y
    COMBO = auto()               # count, x, y
    CLICK_MISSED = auto()        # x, y
    CLOSE_CALL = auto()          # x, y
    GREMLIN_SQUASHED = auto()    # x, y, carrier, kind
    GREMLIN_HIT = auto()         # x, y (an armored gremlin lost its armour)
    GREMLIN_SPLIT = auto()       # x, y
    GREMLIN_ZAPPED = auto()      # x, y
    NEW_THREAT = auto()          # kind (first appearance of a gremlin kind)
    CABLE_SABOTAGED = auto()     # x, y
    COMPUTER_INFECTED = auto()   # computer
    COMPUTER_FRIED = auto()      # computer
    OS_EJECTED = auto()          # computer
    OS_RESTORED = auto()         # computer
    DISK_PICKED_UP = auto()      # disk
    DISK_DROPPED = auto()        # disk
    DISK_STOLEN = auto()         # x, y (a scavenger picked up a disk from the floor)
    DISK_REJECTED = auto()       # computer, reason
    SURGE_WARNING = auto()       # src, dst
    SURGE_ZAPPED = auto()        # x, y, chained
    SURGE_CLEARED = auto()       # x, y
    POWERUP_COLLECTED = auto()   # x, y, text
    LEVEL_STARTED = auto()       # level
    PERFECT_LEVEL = auto()       # bonus
    LEVEL_CLEARED = auto()       # bonus
    GAME_OVER = auto()           # score
    ACHIEVEMENT_UNLOCKED = auto()  # achievement


Handler = Callable[..., None]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[Event, list[Handler]] = defaultdict(list)

    def subscribe(self, event: Event, handler: Handler) -> None:
        self._handlers[event].append(handler)

    def unsubscribe(self, event: Event, handler: Handler) -> None:
        if handler in self._handlers[event]:
            self._handlers[event].remove(handler)

    def emit(self, event: Event, **data) -> None:
        for handler in list(self._handlers[event]):
            handler(**data)
