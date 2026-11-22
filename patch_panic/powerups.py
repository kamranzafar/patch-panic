"""Mid-level power-ups (Strategy pattern).

Each power-up is a small class with the same interface, so the world can pick
one at random and apply it without knowing what it does. Adding a new
power-up means writing one class and adding it to `ALL_POWERUPS`.
"""
from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from .config import AUTO_PATCH_MAX, FREEZE_TIME, SHIELD_TIME

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


ALL_POWERUPS: tuple[PowerUpEffect, ...] = (Firewall(), SurgeGuard(), AutoPatch())


def choose_powerup(world: World, rng: random.Random) -> PowerUpEffect:
    return rng.choice([p for p in ALL_POWERUPS if p.is_available(world)])
