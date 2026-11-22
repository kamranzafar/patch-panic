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

"""Short-lived visual feedback: particles, floating text, banner, shake and hit-stop.

`Effects` subscribes to game events, so the game rules never need to know
that a squash makes particles fly.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

from .config import BANNER_TIME, HITSTOP_TIME, OS_COLORS, SHAKE_AMPLITUDE, SHAKE_TIME, Color
from .events import Event, EventBus


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    color: tuple[int, int, int]


@dataclass
class Popup:
    x: float
    y: float
    text: str
    color: tuple[int, int, int]
    life: float = 1.0


@dataclass
class Banner:
    text: str
    life: float = BANNER_TIME


class Effects:
    GRAVITY = 400
    POPUP_RISE = 40

    def __init__(self, rng: random.Random | None = None) -> None:
        self.rng = rng or random.Random()
        self.particles: list[Particle] = []
        self.popups: list[Popup] = []
        self.banner: Banner | None = None
        self.motion = True     # screen shake and hit-stop (a player setting)
        self.shake = 0.0       # seconds of screen shake left
        self.hitstop = 0.0     # seconds the world stays paused for impact

    @property
    def shake_strength(self) -> float:
        """Current shake amplitude in pixels; fades out as the shake ends."""
        return SHAKE_AMPLITUDE * self.shake / SHAKE_TIME

    # ----------------------------------------------------------- subscriptions
    def connect(self, bus: EventBus) -> None:
        bus.subscribe(Event.SCORED, self._on_scored)
        bus.subscribe(Event.GREMLIN_SQUASHED, self._on_squashed)
        bus.subscribe(Event.GREMLIN_ZAPPED, self._on_gremlin_zapped)
        bus.subscribe(Event.COMPUTER_INFECTED, lambda computer: self._burst_at(computer, Color.BLOAT, 10))
        bus.subscribe(Event.COMPUTER_FRIED, self._on_fried)
        bus.subscribe(Event.OS_RESTORED, lambda computer: self._burst_at(computer, OS_COLORS[computer.native], 20))
        bus.subscribe(Event.OS_EJECTED, lambda computer: self._popup_at(computer, "OS ejected!"))
        bus.subscribe(Event.DISK_REJECTED, lambda computer, reason: self._popup_at(computer, reason))
        bus.subscribe(Event.SURGE_ZAPPED, lambda x, y, chained: self.burst(x, y, Color.SURGE, 12))
        bus.subscribe(Event.SURGE_CLEARED, lambda x, y: self.burst(x, y, Color.ICE, 8))
        bus.subscribe(Event.POWERUP_COLLECTED, self._on_powerup)
        bus.subscribe(Event.GREMLIN_HIT, self._on_gremlin_hit)
        bus.subscribe(Event.GREMLIN_SPLIT, lambda x, y: self.burst(x, y, Color.SPLITTER, 10))
        bus.subscribe(Event.DISK_STOLEN, lambda x, y: self.popup(x, y - 30, "Disk stolen!", Color.RED))
        bus.subscribe(Event.CABLE_SABOTAGED, lambda x, y: self.burst(x, y, Color.SURGE, 10))
        bus.subscribe(Event.NEW_THREAT, lambda kind: self.show_banner(f"NEW THREAT: {kind.label}! {kind.hint}"))
        bus.subscribe(Event.COMBO, lambda count, x, y: self.popup(x, y - 44, f"x{count} COMBO", Color.COMBO))
        bus.subscribe(Event.CLOSE_CALL, lambda x, y: self.popup(x, y - 64, "Close call!", Color.WHITE))
        bus.subscribe(Event.PERFECT_LEVEL, lambda bonus: self.show_banner(f"PERFECT! +{bonus}"))
        bus.subscribe(Event.ACHIEVEMENT_UNLOCKED,
                      lambda achievement: self.show_banner(f"ACHIEVEMENT: {achievement.title}"))

    def _on_scored(self, points, x, y):
        self.popup(x, y - 20, f"+{points}", Color.YELLOW)

    def _on_squashed(self, x, y, carrier, kind):
        self.burst(x, y, Color.GREMLIN)
        if carrier:
            self.impact(hitstop=HITSTOP_TIME)

    def _on_fried(self, computer):
        self._burst_at(computer, Color.SURGE, 20)
        self.impact(shake=SHAKE_TIME)

    def _on_gremlin_hit(self, x, y):
        self.burst(x, y - 12, Color.GREY, 8)
        self.popup(x, y - 40, "CLANK!", Color.GREY)

    def _on_gremlin_zapped(self, x, y):
        self.burst(x, y, Color.GREMLIN)
        self.popup(x, y - 20, "ZAP!", Color.SURGE)

    def _on_powerup(self, x, y, text):
        self.burst(x, y, Color.YELLOW, 24)
        self.show_banner(text)

    def _burst_at(self, computer, color, count):
        self.burst(computer.x, computer.y - 10, color, count)

    def _popup_at(self, computer, text):
        self.popup(computer.x, computer.y - 50, text, Color.RED)

    # ------------------------------------------------------------------ API
    def burst(self, x: float, y: float, color, count: int = 14) -> None:
        for _ in range(count):
            angle = self.rng.uniform(0, math.tau)
            speed = self.rng.uniform(60, 220)
            self.particles.append(Particle(x, y, math.cos(angle) * speed, math.sin(angle) * speed,
                                           self.rng.uniform(0.3, 0.6), color))

    def impact(self, shake: float = 0.0, hitstop: float = 0.0) -> None:
        if self.motion:
            self.shake = max(self.shake, shake)
            self.hitstop = max(self.hitstop, hitstop)

    def show_banner(self, text: str) -> None:
        self.banner = Banner(text)

    def popup(self, x: float, y: float, text: str, color) -> None:
        self.popups.append(Popup(x, y, text, color))

    def clear(self) -> None:
        self.particles.clear()
        self.popups.clear()
        self.banner = None
        self.shake = self.hitstop = 0.0

    def update(self, dt: float) -> None:
        self.shake = max(0.0, self.shake - dt)
        self.hitstop = max(0.0, self.hitstop - dt)
        for p in self.particles:
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.vy += self.GRAVITY * dt
            p.life -= dt
        self.particles = [p for p in self.particles if p.life > 0]
        for p in self.popups:
            p.y -= self.POPUP_RISE * dt
            p.life -= dt
        self.popups = [p for p in self.popups if p.life > 0]
        if self.banner:
            self.banner.life -= dt
            if self.banner.life <= 0:
                self.banner = None
