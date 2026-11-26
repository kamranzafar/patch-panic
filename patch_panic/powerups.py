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

"""Mid-level power-ups (Strategy pattern).

Each power-up is a small class with the same interface, so the world can pick
one at random and apply it without knowing what it does. Adding a new
power-up means writing one class and adding it to `ALL_POWERUPS`.
"""
from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from .config import AUTO_PATCH_MAX, FREEZE_TIME, HONEYPOT_TIME, SHIELD_TIME, SWEEP_CLICKS

if TYPE_CHECKING:
    from .world import World


class PowerUpEffect(ABC):
    def is_available(self, world: World) -> bool:
        return True

    @abstractmethod
    def apply(self, world: World) -> str:
        """Apply the effect and return the banner text to show."""


class Firewall(PowerUpEffect):
    def apply(self, world: World) -> str:
        world.freeze_gremlins(FREEZE_TIME)
        return "FIREWALL! Gremlins frozen"


class SurgeGuard(PowerUpEffect):
    def apply(self, world: World) -> str:
        world.shield_cables(SHIELD_TIME)
        return "SURGE GUARD! Cables protected"


class AutoPatch(PowerUpEffect):
    def is_available(self, world: World) -> bool:
        return bool(world.repairable_computers())

    def apply(self, world: World) -> str:
        candidates = world.repairable_computers()
        fixed = world.rng.sample(candidates, min(AUTO_PATCH_MAX, len(candidates)))
        for computer in fixed:
            world.restore_computer(computer)
        world.discard_unneeded_disks()
        return f"AUTO-PATCH! {len(fixed)} restored"


class AntivirusSweep(PowerUpEffect):
    def apply(self, world: World) -> str:
        world.activate_sweep(SWEEP_CLICKS)
        return f"ANTIVIRUS SWEEP! {SWEEP_CLICKS} power swats"


class Rollback(PowerUpEffect):
    def is_available(self, world: World) -> bool:
        disks = world.disks + ([world.dragging] if world.dragging else [])
        return any(c.accepts(d.kind) for d in disks for c in world.computers)

    def apply(self, world: World) -> str:
        return f"ROLLBACK! {world.rollback_disks()} restored"


class HoneypotLure(PowerUpEffect):
    def apply(self, world: World) -> str:
        world.place_honeypot(HONEYPOT_TIME)
        return "HONEYPOT! Gremlins lured away"


ALL_POWERUPS: tuple[PowerUpEffect, ...] = (Firewall(), SurgeGuard(), AutoPatch(), AntivirusSweep(), Rollback(),
                                           HoneypotLure())


def choose_powerup(world: World, rng: random.Random) -> PowerUpEffect:
    return rng.choice([p for p in ALL_POWERUPS if p.is_available(world)])
