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

"""High score persistence."""
from __future__ import annotations

import json
from pathlib import Path

DEFAULT_PATH = Path.home() / ".patch_panic.json"


class HighScoreStore:
    def __init__(self, path: Path = DEFAULT_PATH) -> None:
        self.path = path
        self.best = self._load()

    def submit(self, score: int) -> bool:
        """Record `score`; returns True if it's a new high score."""
        if score <= self.best:
            return False
        self.best = score
        self._save()
        return True

    def _load(self) -> int:
        try:
            return int(json.loads(self.path.read_text()).get("highscore", 0))
        except (OSError, ValueError, AttributeError):
            return 0

    def _save(self) -> None:
        try:
            self.path.write_text(json.dumps({"highscore": self.best}))
        except OSError:
            pass  # not being able to save a high score shouldn't crash the game
