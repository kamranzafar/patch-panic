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
    GREMLIN_SQUASHED = auto()    # x, y
    GREMLIN_ZAPPED = auto()      # x, y
    COMPUTER_INFECTED = auto()   # computer
    COMPUTER_FRIED = auto()      # computer
    OS_EJECTED = auto()          # computer
    OS_RESTORED = auto()         # computer
    DISK_PICKED_UP = auto()      # disk
    DISK_DROPPED = auto()        # disk
    DISK_REJECTED = auto()       # computer, reason
    SURGE_ZAPPED = auto()        # x, y
    SURGE_CLEARED = auto()       # x, y
    POWERUP_COLLECTED = auto()   # x, y, text
    LEVEL_CLEARED = auto()       # bonus
    GAME_OVER = auto()           # score


Handler = Callable[..., None]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[Event, list[Handler]] = defaultdict(list)

    def subscribe(self, event: Event, handler: Handler) -> None:
        self._handlers[event].append(handler)

    def emit(self, event: Event, **data) -> None:
        for handler in list(self._handlers[event]):
            handler(**data)
