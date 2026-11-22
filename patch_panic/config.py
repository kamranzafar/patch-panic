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

"""Game-wide constants and difficulty tuning.

Everything that is a "magic number" lives here so the rest of the code reads
in terms of names, and balancing the game only means editing this file.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

# --- Window -------------------------------------------------------------------
WIDTH, HEIGHT = 960, 640
HUD_HEIGHT = 40
FPS = 60
MAX_FRAME_TIME = 0.05  # clamp dt so a stalled frame can't teleport objects
TITLE = "Patch Panic"
COPYRIGHT = "© 2026 Kamran Zafar. Free software under the GNU GPL v3 or later."

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
SURGE_WARNING_TIME = 0.6           # a cable pulses this long before its surge appears
INSTALL_WARN_TIME = 0.5            # install ring turns red when this much time is left
HITSTOP_TIME = 0.06                # world pauses briefly on a satisfying swat
SHAKE_TIME = 0.3
SHAKE_AMPLITUDE = 6                # pixels
COMBO_WINDOW = 1.2                 # swats/zaps this close together build a combo
COMBO_MAX = 5                      # highest score multiplier
SABOTAGE_TIME = 2.5                # a saboteur chews a cable this long before it sparks
HONEYPOT_TIME = 6.0
SWEEP_CLICKS = 3                   # Antivirus Sweep: number of clicks with a bigger reach
SWEEP_RADIUS_SCALE = 2.0

# --- Layout -------------------------------------------------------------------------
GRID_COLS, GRID_ROWS = 6, 3        # computers are placed in jittered grid cells
CABLES_PER_COMPUTER = 2            # each computer links to its N nearest neighbours
AUTO_PATCH_MAX = 2                 # computers restored by the Auto-Patch power-up
DISK_SNAP_RADIUS = 60              # a dropped disk snaps to a matching computer this close
ATTENTION_RADIUS = 26              # tutorial: pulsing ring around something to look at
CARRIER_SPEED_FACTOR = 1.25        # a gremlin carrying a stolen OS runs for it
LATE_CATCH_FRACTION = 1 / 3        # catching a carrier in the last third of its escape is a close call
PERFECT_SAFETY = 1                 # a perfect level lets the next one end with this many fewer clean machines


class Points:
    SQUASH = 10
    SQUASH_CARRIER = 25
    ZAP_SURGE = 15
    RESTORE_OS = 50
    POWERUP_PER_LEVEL = 100
    CLEAN_PER_LEVEL = 10
    PERFECT_PER_LEVEL = 50
    LATE_CATCH = 20


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
    INSTALL_RING = (255, 214, 70)
    INSTALL_RING_BACK = (40, 40, 52)
    SNAP_HIGHLIGHT = (240, 240, 245)
    COMBO = (255, 140, 66)
    SPLITTER = (240, 175, 50)
    HONEYPOT = (255, 190, 60)
    BUTTON_HOT = (60, 52, 30)
    BUTTON_SELECTED = (36, 40, 58)
    LOCKED = (95, 100, 118)


# --- Gremlin kinds -------------------------------------------------------------------
@dataclass(frozen=True)
class GremlinKind:
    """What makes one kind of gremlin different. `name` is also its sprite prefix."""

    name: str
    label: str
    hint: str = ""                   # shown in the banner the first time it appears
    first_level: int = 1             # level it starts to appear in
    weight: float = 1.0              # spawn chance relative to the other kinds in a level
    speed_factor: float = 1.0
    hit_radius_factor: float = 1.0
    hits: int = 1                    # swats needed
    splits: int = 0                  # sprinters it splits into when swatted
    sabotages: bool = False          # goes for a cable instead of a computer


class Gremlins:
    STANDARD = GremlinKind("gremlin", "Gremlin")
    SPRINTER = GremlinKind("sprinter", "Sprinter", "Fast but fragile", first_level=3, weight=0.35,
                           speed_factor=1.5, hit_radius_factor=0.8)
    ARMORED = GremlinKind("armored", "Armored gremlin", "Takes two swats", first_level=7, weight=0.3,
                          speed_factor=0.85, hits=2)
    SPLITTER = GremlinKind("splitter", "Splitter", "Splits in two when swatted", first_level=11, weight=0.25,
                           splits=2)
    SABOTEUR = GremlinKind("saboteur", "Saboteur", "Chews cables to start surges", first_level=13,
                           weight=0.2, sabotages=True)
    ALL = (STANDARD, SPRINTER, ARMORED, SPLITTER, SABOTEUR)


# --- Save file -------------------------------------------------------------------
LEADERBOARD_SIZE = 10
INITIALS_LENGTH = 3
DEFAULT_INITIALS = "AAA"


class GameMode(Enum):
    CLASSIC = "Classic"
    DAILY = "Daily"
    TUTORIAL = "Tutorial"

    @property
    def label(self) -> str:
        return self.value


class Difficulty(Enum):
    """Preset that scales `LevelConfig`: (label, speed, timing, count).

    `speed` multiplies gremlin and surge speed, `timing` multiplies the spawn,
    install and surge intervals (bigger is easier), `count` multiplies the
    number of gremlins per level.
    """

    RELAXED = ("Relaxed", 0.8, 1.25, 0.8)
    NORMAL = ("Normal", 1.0, 1.0, 1.0)
    FRANTIC = ("Frantic", 1.2, 0.8, 1.25)

    def __init__(self, label: str, speed: float, timing: float, count: float) -> None:
        self.label = label
        self.speed = speed
        self.timing = timing
        self.count = count

    def next(self) -> Difficulty:
        members = list(Difficulty)
        return members[(members.index(self) + 1) % len(members)]


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
    kinds: tuple[GremlinKind, ...] = (Gremlins.STANDARD,)  # gremlin kinds that can appear

    @classmethod
    def for_level(cls, level: int, difficulty: Difficulty = Difficulty.NORMAL) -> LevelConfig:
        if level < 1:
            raise ValueError("level must be >= 1")
        return cls._base(level).scaled(difficulty)

    @classmethod
    def _base(cls, level: int) -> LevelConfig:
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
            kinds=tuple(k for k in Gremlins.ALL if k.first_level <= level),
        )

    @classmethod
    def tutorial(cls) -> LevelConfig:
        """A small, slow level; the tutorial spawns everything itself."""
        return cls(level=1, computers=4, gremlins=0, max_alive=3, spawn_interval=1.0, gremlin_speed=70,
                   install_time=6.0, surge_interval=10.0, max_surges=1, surge_speed=40, surge_chain=0.0)

    def scaled(self, difficulty: Difficulty) -> LevelConfig:
        if difficulty is Difficulty.NORMAL:
            return self
        return replace(
            self,
            gremlins=max(1, round(self.gremlins * difficulty.count)),
            spawn_interval=self.spawn_interval * difficulty.timing,
            gremlin_speed=self.gremlin_speed * difficulty.speed,
            install_time=self.install_time * difficulty.timing,
            surge_interval=self.surge_interval * difficulty.timing,
            surge_speed=self.surge_speed * difficulty.speed,
        )
