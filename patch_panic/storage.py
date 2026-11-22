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

"""The save file: leaderboard, achievements, settings and last initials.

Everything lives in one small JSON file. Version 1 files (just a high score)
are migrated on load. Not being able to read or write the file never crashes
the game: a broken file is treated as empty, a failed write is ignored.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .config import DEFAULT_INITIALS, LEADERBOARD_SIZE, GameMode

DEFAULT_PATH = Path.home() / ".patch_panic.json"
SAVE_VERSION = 2


@dataclass(frozen=True)
class ScoreEntry:
    score: int
    level: int
    mode: str = GameMode.CLASSIC.name
    initials: str = DEFAULT_INITIALS
    date: str = ""  # ISO date the game was played

    @classmethod
    def from_dict(cls, data: object) -> ScoreEntry | None:
        try:
            return cls(int(data["score"]), int(data["level"]), str(data["mode"]),
                       str(data["initials"]), str(data["date"]))
        except (KeyError, TypeError, ValueError):
            return None


class SaveStore:
    def __init__(self, path: Path = DEFAULT_PATH) -> None:
        self.path = path
        self.leaderboard: list[ScoreEntry] = []
        self.achievements: set[str] = set()
        self.settings: dict = {}
        self.initials = DEFAULT_INITIALS
        self._load()

    # --------------------------------------------------------------- queries
    @property
    def best(self) -> int:
        return self.leaderboard[0].score if self.leaderboard else 0

    def qualifies(self, score: int) -> bool:
        """Would `score` make it onto the leaderboard?"""
        if score <= 0:
            return False
        return len(self.leaderboard) < LEADERBOARD_SIZE or score > self.leaderboard[-1].score

    def entries_for(self, mode: GameMode, date: str | None = None) -> list[ScoreEntry]:
        return [e for e in self.leaderboard if e.mode == mode.name and (date is None or e.date == date)]

    # ------------------------------------------------------------- changes
    def record(self, entry: ScoreEntry) -> int | None:
        """Add `entry` to the leaderboard and save; returns its rank (0 = best) or None."""
        if not self.qualifies(entry.score):
            return None
        board = sorted(self.leaderboard + [entry], key=lambda e: e.score, reverse=True)
        self.leaderboard = board[:LEADERBOARD_SIZE]
        self.initials = entry.initials
        self.save()
        return self.leaderboard.index(entry)

    def unlock(self, achievement_id: str) -> bool:
        """Mark an achievement as unlocked and save; returns True if it is new."""
        if achievement_id in self.achievements:
            return False
        self.achievements.add(achievement_id)
        self.save()
        return True

    def save(self) -> None:
        data = {
            "version": SAVE_VERSION,
            "leaderboard": [asdict(e) for e in self.leaderboard],
            "achievements": sorted(self.achievements),
            "settings": self.settings,
            "initials": self.initials,
        }
        try:
            self.path.write_text(json.dumps(data, indent=1))
        except OSError:
            pass  # not being able to save shouldn't crash the game

    # ---------------------------------------------------------------- loading
    def _load(self) -> None:
        try:
            data = json.loads(self.path.read_text())
        except (OSError, ValueError):
            return
        if not isinstance(data, dict):
            return
        if "version" not in data:  # version 1: {"highscore": N}
            self._migrate_v1(data)
            return
        entries = (ScoreEntry.from_dict(e) for e in data.get("leaderboard") or [])
        self.leaderboard = sorted((e for e in entries if e), key=lambda e: e.score,
                                  reverse=True)[:LEADERBOARD_SIZE]
        achievements = data.get("achievements")
        if isinstance(achievements, list):
            self.achievements = {a for a in achievements if isinstance(a, str)}
        if isinstance(data.get("settings"), dict):
            self.settings = data["settings"]
        if isinstance(data.get("initials"), str):
            self.initials = data["initials"]

    def _migrate_v1(self, data: dict) -> None:
        try:
            score = int(data.get("highscore", 0))
        except (TypeError, ValueError):
            return
        if score > 0:
            self.leaderboard = [ScoreEntry(score, level=0, initials="---")]
