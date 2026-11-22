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
