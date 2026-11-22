"""Game-wide constants and difficulty tuning.

Everything that is a "magic number" lives here so the rest of the code reads
in terms of names, and balancing the game only means editing this file.
"""
from __future__ import annotations

from dataclasses import dataclass

# --- Window -------------------------------------------------------------------
WIDTH, HEIGHT = 960, 640
HUD_HEIGHT = 40
FPS = 60
MAX_FRAME_TIME = 0.05  # clamp dt so a stalled frame can't teleport objects
TITLE = "Patch Panic"

# --- Operating systems ----------------------------------------------------------
OS_NAMES = ("Orbix", "Delta", "Cubix", "Prism")
OS_COLORS = ((70, 140, 255), (255, 150, 50), (170, 90, 230), (60, 200, 160))
BLOAT = -1  # Computer.os value for a machine infected with BloatOS
# Computer.os is None when a power surge has ejected the OS disk.

# --- Timings (seconds) ------------------------------------------------------------
FIRST_SPAWN_DELAY = 1.2
FRY_TIME = 4.0
FREEZE_TIME = 5.0
SHIELD_TIME = 8.0
DISK_LIFETIME = 15.0
DISK_BLINK_TIME = 4.0
DYING_TIME = 0.5
BANNER_TIME = 2.0
SWAT_FLASH_TIME = 0.12
LEVEL_DONE_CLICK_DELAY = 0.6
GAME_OVER_CLICK_DELAY = 1.0

# --- Layout -------------------------------------------------------------------------
GRID_COLS, GRID_ROWS = 6, 3        # computers are placed in jittered grid cells
CABLES_PER_COMPUTER = 2            # each computer links to its N nearest neighbours
AUTO_PATCH_MAX = 2                 # computers restored by the Auto-Patch power-up


class Points:
    SQUASH = 10
    SQUASH_CARRIER = 25
    ZAP_SURGE = 15
    RESTORE_OS = 50
    POWERUP_PER_LEVEL = 100
    CLEAN_PER_LEVEL = 10


class Color:
    WHITE = (240, 240, 245)
    BLACK = (10, 10, 14)
    GREY = (190, 195, 205)
    SHADOW = (18, 20, 28)
    HUD_BG = (16, 18, 26)
    HUD_LINE = (60, 66, 86)
    PANEL_BORDER = (80, 88, 115)
    YELLOW = (255, 214, 70)
    RED = (235, 70, 70)
    GREMLIN = (200, 60, 110)
    BLOAT = (130, 180, 40)
    BLOAT_SCREEN = (50, 70, 15)
    BLOAT_SCREEN_ALT = (65, 90, 20)
    SURGE = (255, 210, 60)
    SURGE_PATH = (105, 95, 40)
    CABLE = (55, 62, 82)
    ICE = (140, 210, 255)


@dataclass(frozen=True)
class LevelConfig:
    """Difficulty parameters for one level."""

    level: int
    computers: int
    gremlins: int
    max_alive: int
    spawn_interval: float
    gremlin_speed: float
    install_time: float
    surge_interval: float
    max_surges: int
    surge_speed: float
    surge_chain: float  # probability a surge jumps on to the next cable

    @classmethod
    def for_level(cls, level: int) -> LevelConfig:
        if level < 1:
            raise ValueError("level must be >= 1")
        return cls(
            level=level,
            computers=min(5 + level, 16),
            gremlins=3 + 3 * level,
            max_alive=min(1 + level, 9),
            spawn_interval=max(0.45, 2.6 - 0.2 * level),
            gremlin_speed=min(70 + 9 * level, 170),
            install_time=max(1.1, 3.2 - 0.18 * level),
            surge_interval=max(3.0, 13.0 - 1.0 * level),
            max_surges=1 + level // 3,
            surge_speed=min(45 + 6 * level, 130),
            surge_chain=min(0.5, 0.1 + 0.04 * level),
        )
