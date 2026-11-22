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

"""Game objects: plain state plus the behaviour that belongs to each object.

Nothing here draws or plays sounds -- see render.py and audio.py.
"""
from __future__ import annotations

import math
import random
from enum import Enum, auto

import pygame

from .config import BLOAT, DISK_LIFETIME, HEIGHT, HUD_HEIGHT, WIDTH

Point = tuple[float, float]


def distance(a: Point, b: Point) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def random_edge_point(rng: random.Random) -> Point:
    """A spawn point just outside a random edge of the play area."""
    side = rng.randrange(4)
    if side == 0:
        return -25, rng.uniform(HUD_HEIGHT + 30, HEIGHT - 30)
    if side == 1:
        return WIDTH + 25, rng.uniform(HUD_HEIGHT + 30, HEIGHT - 30)
    if side == 2:
        return rng.uniform(30, WIDTH - 30), HUD_HEIGHT - 25
    return rng.uniform(30, WIDTH - 30), HEIGHT + 25


def nearest_exit(x: float, y: float) -> Point:
    options = [(-30, y), (WIDTH + 30, y), (x, HUD_HEIGHT - 30), (x, HEIGHT + 30)]
    return min(options, key=lambda p: distance((x, y), p))


class Computer:
    def __init__(self, x: int, y: int, native: int) -> None:
        self.x, self.y = x, y
        self.native = native          # the OS this machine is built for
        self.os: int | None = native  # current OS, BLOAT, or None (ejected)
        self.targeted: Gremlin | None = None
        self.install = 0.0            # BloatOS install progress 0..1
        self.flash = 0.0              # white flash after a restore, 1..0
        self.fried = 0.0              # seconds until reboot after a surge

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(self.x - 36, self.y - 38, 72, 72)

    @property
    def is_rebooting(self) -> bool:
        return self.fried > 0

    @property
    def is_broken(self) -> bool:
        return self.os is None or self.os == BLOAT

    @property
    def is_clean(self) -> bool:
        return not self.is_broken and not self.is_rebooting

    def accepts(self, kind: int) -> bool:
        """Can an OS disk of `kind` be installed right now?"""
        return self.is_broken and not self.is_rebooting and self.native == kind

    def restore(self) -> None:
        self.os = self.native
        self.flash = 1.0

    def cable_anchor(self) -> Point:
        return self.x, self.y + 28

    def work_spot(self) -> Point:
        """Where a gremlin stands while installing BloatOS."""
        return self.x + 46, self.y + 4

    def tick(self, dt: float) -> None:
        self.flash = max(0.0, self.flash - dt * 2)
        self.fried = max(0.0, self.fried - dt)


class GremlinState(Enum):
    WALK_IN = auto()
    INSTALL = auto()
    WALK_OUT = auto()
    DYING = auto()


class Gremlin:
    HIT_RADIUS = 24
    BODY_OFFSET_Y = -12  # sprite body centre relative to the feet position

    def __init__(self, x: float, y: float, speed: float, phase: float = 0.0) -> None:
        self.x, self.y = x, y
        self.speed = speed
        self.phase = phase            # animation offset so gremlins don't march in sync
        self.state = GremlinState.WALK_IN
        self.target: Computer | None = None
        self.carry: int | None = None  # stolen OS kind
        self.timer = 0.0
        self.facing = 1
        self.exit: Point | None = None

    @property
    def is_alive(self) -> bool:
        return self.state is not GremlinState.DYING

    def assign(self, computer: Computer) -> None:
        self.target = computer
        computer.targeted = self

    def release_target(self) -> None:
        if self.target is not None and self.target.targeted is self:
            self.target.targeted = None
            self.target.install = 0.0

    def start_install(self) -> None:
        self.state = GremlinState.INSTALL
        self.facing = -1  # computer is to the left of the work spot
        self.timer = 0.0

    def leave(self, exit_point: Point) -> None:
        self.state = GremlinState.WALK_OUT
        self.exit = exit_point

    def die(self) -> None:
        self.release_target()
        self.state = GremlinState.DYING
        self.timer = 0.0

    def move_toward(self, tx: float, ty: float, dt: float) -> bool:
        """Step towards (tx, ty); returns True on arrival."""
        dx, dy = tx - self.x, ty - self.y
        d = math.hypot(dx, dy)
        step = self.speed * dt
        if abs(dx) > 1:
            self.facing = 1 if dx > 0 else -1
        if d <= step:
            self.x, self.y = tx, ty
            return True
        self.x += dx / d * step
        self.y += dy / d * step
        return False

    def hit(self, pos: Point) -> bool:
        return distance(pos, (self.x, self.y + self.BODY_OFFSET_Y)) < self.HIT_RADIUS


class Surge:
    """A power surge travelling along the cable from `src` to `dst`."""

    HIT_RADIUS = 18

    def __init__(self, src: Computer, dst: Computer, progress: float, speed: float) -> None:
        self.src, self.dst = src, dst
        self.progress = progress  # 0 at src, 1 at dst
        self.speed = speed
        self.length = max(1.0, distance((src.x, src.y), (dst.x, dst.y)))

    @property
    def pos(self) -> Point:
        (ax, ay), (bx, by) = self.src.cable_anchor(), self.dst.cable_anchor()
        return ax + (bx - ax) * self.progress, ay + (by - ay) * self.progress

    def advance(self, dt: float) -> bool:
        """Move along the cable; returns True when it reaches `dst`."""
        self.progress += self.speed * dt / self.length
        return self.progress >= 1.0

    def hit(self, pos: Point) -> bool:
        return distance(pos, self.pos) < self.HIT_RADIUS


class Disk:
    """An OS disk lying on the floor, waiting to be dragged home."""

    def __init__(self, kind: int, x: float, y: float, age: float = 0.0) -> None:
        self.kind = kind
        self.x = max(24, min(WIDTH - 24, x))
        self.y = max(HUD_HEIGHT + 24, min(HEIGHT - 24, y))
        self.age = age

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(self.x - 18, self.y - 18, 36, 36)

    @property
    def remaining(self) -> float:
        return DISK_LIFETIME - self.age

    @property
    def expired(self) -> bool:
        return self.remaining <= 0


class PowerUp:
    """The golden patch that flies across the screen mid-level."""

    HIT_RADIUS = 26
    SPEED = 150
    WAVE_HEIGHT = 45

    def __init__(self, rng: random.Random) -> None:
        self.direction = rng.choice((-1, 1))
        self.x = -30 if self.direction > 0 else WIDTH + 30
        self.base_y = rng.uniform(HUD_HEIGHT + 90, HEIGHT - 90)
        self.y = self.base_y
        self.age = 0.0

    def advance(self, dt: float) -> bool:
        """Move; returns False once it has left the screen."""
        self.age += dt
        self.x += self.direction * self.SPEED * dt
        self.y = self.base_y + math.sin(self.age * 3) * self.WAVE_HEIGHT
        return -40 <= self.x <= WIDTH + 40

    def hit(self, pos: Point) -> bool:
        return distance(pos, (self.x, self.y)) < self.HIT_RADIUS
