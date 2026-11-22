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

"""Player settings, kept in the save file.

`Settings` is plain data with `to_dict` / `from_dict`, so it can be stored as
JSON by `SaveStore` and unit-tested without pygame. Unknown or broken values
fall back to the defaults instead of failing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import pygame

from .config import Difficulty


class Action(Enum):
    """Rebindable keyboard actions (Esc and left click stay fixed)."""

    PAUSE = "Pause"
    MUTE = "Mute"
    FULLSCREEN = "Fullscreen"

    @property
    def label(self) -> str:
        return self.value


DEFAULT_KEYS: dict[Action, int] = {
    Action.PAUSE: pygame.K_p,
    Action.MUTE: pygame.K_m,
    Action.FULLSCREEN: pygame.K_f,
}


@dataclass
class Settings:
    difficulty: Difficulty = Difficulty.NORMAL
    colourblind: bool = False
    screen_shake: bool = True
    auto_pause: bool = True
    keys: dict[Action, int] = field(default_factory=lambda: dict(DEFAULT_KEYS))

    def is_action(self, event: pygame.event.Event, action: Action) -> bool:
        return event.type == pygame.KEYDOWN and event.key == self.keys[action]

    def key_name(self, action: Action) -> str:
        return pygame.key.name(self.keys[action]).upper()

    def rebind(self, action: Action, key: int) -> None:
        """Bind `key` to `action`; an action that already used it gets the old key instead."""
        for other, other_key in self.keys.items():
            if other_key == key and other is not action:
                self.keys[other] = self.keys[action]
        self.keys[action] = key

    def to_dict(self) -> dict:
        return {
            "difficulty": self.difficulty.name,
            "colourblind": self.colourblind,
            "screen_shake": self.screen_shake,
            "auto_pause": self.auto_pause,
            "keys": {action.name: key for action, key in self.keys.items()},
        }

    @classmethod
    def from_dict(cls, data: object) -> Settings:
        settings = cls()
        if not isinstance(data, dict):
            return settings
        difficulty = data.get("difficulty")
        if isinstance(difficulty, str) and difficulty in Difficulty.__members__:
            settings.difficulty = Difficulty[difficulty]
        for name in ("colourblind", "screen_shake", "auto_pause"):
            if isinstance(data.get(name), bool):
                setattr(settings, name, data[name])
        keys = data.get("keys")
        if isinstance(keys, dict):
            for action in Action:
                if type(keys.get(action.name)) is int:  # not bool, which is an int too
                    settings.keys[action] = keys[action.name]
        return settings
