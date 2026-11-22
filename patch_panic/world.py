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

"""The game rules for one level.

`World` owns every game object and decides what happens each tick. It has no
knowledge of drawing or audio: it reports what happened through the event
bus, which keeps it easy to test (see tests/test_world.py).
"""
from __future__ import annotations

import random
from enum import Enum, auto

from .config import (BLOAT, CABLES_PER_COMPUTER, DYING_TIME, FIRST_SPAWN_DELAY, FRY_TIME, GRID_COLS,
                     GRID_ROWS, HEIGHT, HUD_HEIGHT, OS_NAMES, WIDTH, LevelConfig, Points)
from .entities import (Computer, Disk, Gremlin, GremlinState, Point, PowerUp, Surge, distance,
                       nearest_exit, random_edge_point)
from .events import Event, EventBus
from .powerups import choose_powerup


class Outcome(Enum):
    IN_PROGRESS = auto()
    CLEARED = auto()
    FAILED = auto()


class World:
    def __init__(self, level: int = 1, score: int = 0, bus: EventBus | None = None,
                 rng: random.Random | None = None) -> None:
        self.level = level
        self.score = score
        self.config = LevelConfig.for_level(level)
        self.bus = bus or EventBus()
        self.rng = rng or random.Random()

        self.computers = self._place_computers()
        self.cables = self._wire_network()
        self.gremlins: list[Gremlin] = []
        self.surges: list[Surge] = []
        self.disks: list[Disk] = []
        self.powerup: PowerUp | None = None
        self.dragging: Disk | None = None

        self.to_spawn = self.config.gremlins
        self.spawn_timer = FIRST_SPAWN_DELAY
        self.surge_timer = self.config.surge_interval * 0.6
        self.powerup_spawned = False
        self.freeze_timer = 0.0
        self.shield_timer = 0.0
        self.outcome = Outcome.IN_PROGRESS
        self.level_bonus = 0

    # ------------------------------------------------------------------ setup
    def _place_computers(self) -> list[Computer]:
        n = self.config.computers
        assert n <= GRID_COLS * GRID_ROWS, "not enough grid cells for computers"
        left, top = 60, HUD_HEIGHT + 60
        cell_w = (WIDTH - 160) / GRID_COLS
        cell_h = (HEIGHT - HUD_HEIGHT - 110) / GRID_ROWS
        cells = self.rng.sample([(c, r) for c in range(GRID_COLS) for r in range(GRID_ROWS)], n)
        kinds = [i % len(OS_NAMES) for i in range(n)]
        self.rng.shuffle(kinds)
        computers = []
        for (col, row), kind in zip(cells, kinds):
            x = left + cell_w * (col + 0.5 + self.rng.uniform(-0.15, 0.15))
            y = top + cell_h * (row + 0.5 + self.rng.uniform(-0.12, 0.12))
            computers.append(Computer(int(x), int(y), kind))
        return computers

    def _wire_network(self) -> list[tuple[Computer, Computer]]:
        """Link each computer to its nearest neighbours (no duplicate cables)."""
        pairs = set()
        for i, c in enumerate(self.computers):
            others = sorted((j for j in range(len(self.computers)) if j != i),
                            key=lambda j: distance((c.x, c.y), (self.computers[j].x, self.computers[j].y)))
            pairs.update(tuple(sorted((i, j))) for j in others[:CABLES_PER_COMPUTER])
        return [(self.computers[i], self.computers[j]) for i, j in sorted(pairs)]

    # ---------------------------------------------------------------- queries
    @property
    def clean_count(self) -> int:
        return sum(c.is_clean for c in self.computers)

    @property
    def alive_gremlins(self) -> list[Gremlin]:
        return [g for g in self.gremlins if g.is_alive]

    @property
    def remaining_gremlins(self) -> int:
        return self.to_spawn + len(self.alive_gremlins)

    @property
    def is_frozen(self) -> bool:
        return self.freeze_timer > 0

    @property
    def is_shielded(self) -> bool:
        return self.shield_timer > 0

    def available_targets(self) -> list[Computer]:
        return [c for c in self.computers if c.is_clean and c.targeted is None]

    def repairable_computers(self) -> list[Computer]:
        return [c for c in self.computers if c.is_broken and not c.is_rebooting and c.targeted is None]

    def neighbours(self, computer: Computer) -> list[Computer]:
        return [b if a is computer else a for a, b in self.cables if computer in (a, b)]

    def _disk_is_needed(self, disk: Disk) -> bool:
        return any(c.native == disk.kind and c.is_broken for c in self.computers)

    # ------------------------------------------------------------------ input
    def click(self, pos: Point) -> bool:
        """Handle a click; returns True if it hit something."""
        if self.powerup and self.powerup.hit(pos):
            self._collect_powerup()
            return True
        for g in sorted(self.alive_gremlins, key=lambda g: g.y, reverse=True):  # front-most first
            if g.hit(pos):
                self._squash(g)
                return True
        for surge in self.surges:
            if surge.hit(pos):
                self._zap(surge)
                return True
        for disk in reversed(self.disks):
            if disk.rect.collidepoint(pos):
                self.disks.remove(disk)
                self.dragging = disk
                self.bus.emit(Event.DISK_PICKED_UP, disk=disk)
                return True
        return False

    def release(self, pos: Point) -> None:
        """Drop the dragged disk, installing it if it's over a matching computer."""
        disk, self.dragging = self.dragging, None
        if disk is None:
            return
        target = next((c for c in self.computers if c.rect.collidepoint(pos)), None)
        if target is not None and target.accepts(disk.kind):
            self.restore_computer(target)
            self._award(Points.RESTORE_OS, target.x, target.y - 30)
            return
        if target is not None:
            self.bus.emit(Event.DISK_REJECTED, computer=target, reason=self._rejection_reason(target))
        else:
            self.bus.emit(Event.DISK_DROPPED, disk=disk)
        self.disks.append(Disk(disk.kind, *pos, age=disk.age))

    @staticmethod
    def _rejection_reason(computer: Computer) -> str:
        if computer.is_rebooting:
            return "Rebooting..."
        if computer.is_clean:
            return "Already clean"
        return f"Needs {OS_NAMES[computer.native]}"

    # ----------------------------------------------- actions (used by power-ups)
    def freeze_gremlins(self, seconds: float) -> None:
        self.freeze_timer = seconds

    def shield_cables(self, seconds: float) -> None:
        self.shield_timer = seconds
        for surge in self.surges:
            self.bus.emit(Event.SURGE_CLEARED, x=surge.pos[0], y=surge.pos[1])
        self.surges.clear()

    def restore_computer(self, computer: Computer) -> None:
        computer.restore()
        self.bus.emit(Event.OS_RESTORED, computer=computer)

    def discard_unneeded_disks(self) -> None:
        self.disks = [d for d in self.disks if self._disk_is_needed(d)]

    def spawn_gremlin(self, target: Computer) -> Gremlin:
        x, y = random_edge_point(self.rng)
        gremlin = Gremlin(x, y, self.config.gremlin_speed * self.rng.uniform(0.85, 1.15),
                          phase=self.rng.uniform(0, 6.28))
        gremlin.assign(target)
        self.gremlins.append(gremlin)
        return gremlin

    # ----------------------------------------------------------------- update
    def update(self, dt: float) -> None:
        if self.outcome is not Outcome.IN_PROGRESS:
            return
        self.freeze_timer = max(0.0, self.freeze_timer - dt)
        self.shield_timer = max(0.0, self.shield_timer - dt)
        self._update_spawning(dt)
        self._update_powerup(dt)
        self._update_gremlins(dt)
        self._update_surges(dt)
        self._update_disks(dt)
        for computer in self.computers:
            computer.tick(dt)
        self._check_outcome()

    def _update_spawning(self, dt: float) -> None:
        self.spawn_timer -= dt
        if (self.to_spawn <= 0 or self.spawn_timer > 0 or self.is_frozen
                or len(self.alive_gremlins) >= self.config.max_alive):
            return
        targets = self.available_targets()
        if targets:
            self.spawn_gremlin(self.rng.choice(targets))
            self.to_spawn -= 1
            self.spawn_timer = self.config.spawn_interval * self.rng.uniform(0.6, 1.3)

    def _update_powerup(self, dt: float) -> None:
        if not self.powerup_spawned and self.to_spawn <= self.config.gremlins // 2:
            self.powerup_spawned = True
            self.powerup = PowerUp(self.rng)
        if self.powerup and not self.powerup.advance(dt):
            self.powerup = None

    def _update_gremlins(self, dt: float) -> None:
        for g in list(self.gremlins):
            if g.state is GremlinState.DYING:
                g.timer += dt
                if g.timer > DYING_TIME:
                    self.gremlins.remove(g)
            elif self.is_frozen:
                continue
            elif g.state is GremlinState.WALK_IN:
                self._walk_in(g, dt)
            elif g.state is GremlinState.INSTALL:
                self._install(g, dt)
            elif g.state is GremlinState.WALK_OUT and g.move_toward(*g.exit, dt):
                self.gremlins.remove(g)  # escaped with whatever it was carrying

    def _walk_in(self, g: Gremlin, dt: float) -> None:
        if g.target.targeted is not g:  # target was fried on the way: find another
            targets = self.available_targets()
            if not targets:
                g.leave(nearest_exit(g.x, g.y))
                return
            g.assign(self.rng.choice(targets))
        if g.move_toward(*g.target.work_spot(), dt):
            g.start_install()

    def _install(self, g: Gremlin, dt: float) -> None:
        g.timer += dt
        computer = g.target
        computer.install = min(1.0, g.timer / self.config.install_time)
        if g.timer >= self.config.install_time:
            g.carry = computer.os
            computer.os = BLOAT
            computer.install = 0.0
            computer.targeted = None
            g.leave(nearest_exit(g.x, g.y))
            self.bus.emit(Event.COMPUTER_INFECTED, computer=computer)

    def _update_surges(self, dt: float) -> None:
        self.surge_timer -= dt
        wave_active = self.to_spawn > 0 or bool(self.alive_gremlins)
        if (self.cables and wave_active and self.surge_timer <= 0 and not self.is_shielded
                and len(self.surges) < self.config.max_surges):
            src, dst = self.rng.choice(self.cables)
            if self.rng.random() < 0.5:
                src, dst = dst, src
            self.surges.append(Surge(src, dst, self.rng.uniform(0.1, 0.35), self.config.surge_speed))
            self.surge_timer = self.config.surge_interval * self.rng.uniform(0.7, 1.3)
        for surge in list(self.surges):
            if surge.advance(dt):
                self.surges.remove(surge)
                self._fry(surge.dst)
                self._maybe_chain(surge)

    def _maybe_chain(self, surge: Surge) -> None:
        if self.rng.random() >= self.config.surge_chain or len(self.surges) >= self.config.max_surges + 2:
            return
        onward = [c for c in self.neighbours(surge.dst) if c is not surge.src]
        if onward:
            self.surges.append(Surge(surge.dst, self.rng.choice(onward), 0.05, self.config.surge_speed))

    def _update_disks(self, dt: float) -> None:
        for disk in self.disks:
            disk.age += dt
        self.disks = [d for d in self.disks if not d.expired]

    def _check_outcome(self) -> None:
        clean = self.clean_count
        restorable = any(self._disk_is_needed(d) for d in self.disks)
        rebooting = any(c.is_rebooting for c in self.computers)
        if clean == 0 and not restorable and not rebooting:
            self._fail()
            return
        busy = self.gremlins or self.surges or self.dragging or restorable or rebooting
        if self.to_spawn == 0 and not busy:
            if clean * 2 < len(self.computers):
                self._fail()
            else:
                self._clear(clean)

    def _clear(self, clean: int) -> None:
        self.level_bonus = clean * Points.CLEAN_PER_LEVEL * self.level
        self.score += self.level_bonus
        self.outcome = Outcome.CLEARED
        self.bus.emit(Event.LEVEL_CLEARED, bonus=self.level_bonus)

    def _fail(self) -> None:
        self.outcome = Outcome.FAILED
        self.bus.emit(Event.GAME_OVER, score=self.score)

    # ---------------------------------------------------------------- outcomes
    def _award(self, points: int, x: float, y: float) -> None:
        self.score += points
        self.bus.emit(Event.SCORED, points=points, x=x, y=y)

    def _squash(self, g: Gremlin) -> None:
        carried = g.carry
        g.carry = None
        g.die()
        if carried is not None:
            self.disks.append(Disk(carried, g.x, g.y - 10))
        self.bus.emit(Event.GREMLIN_SQUASHED, x=g.x, y=g.y)
        self._award(Points.SQUASH_CARRIER if carried is not None else Points.SQUASH, g.x, g.y)

    def _zap(self, surge: Surge) -> None:
        self.surges.remove(surge)
        x, y = surge.pos
        self.bus.emit(Event.SURGE_ZAPPED, x=x, y=y)
        self._award(Points.ZAP_SURGE, x, y)

    def _collect_powerup(self) -> None:
        powerup, self.powerup = self.powerup, None
        self._award(Points.POWERUP_PER_LEVEL * self.level, powerup.x, powerup.y)
        text = choose_powerup(self, self.rng).apply(self)
        self.bus.emit(Event.POWERUP_COLLECTED, x=powerup.x, y=powerup.y, text=text)

    def _fry(self, computer: Computer) -> None:
        was_clean = computer.is_clean
        computer.fried = FRY_TIME
        self.bus.emit(Event.COMPUTER_FRIED, computer=computer)
        gremlin = computer.targeted
        if gremlin is not None:
            gremlin.release_target()
            if gremlin.state is GremlinState.INSTALL:  # caught mid-install
                gremlin.die()
                self.bus.emit(Event.GREMLIN_ZAPPED, x=gremlin.x, y=gremlin.y)
        if was_clean:
            side = self.rng.choice((-1, 1))
            self.disks.append(Disk(computer.os, computer.x + side * self.rng.uniform(30, 55), computer.y + 52))
            computer.os = None
            self.bus.emit(Event.OS_EJECTED, computer=computer)
