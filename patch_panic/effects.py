"""Short-lived visual feedback: particles, floating text and the banner.

`Effects` subscribes to game events, so the game rules never need to know
that a squash makes particles fly.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

from .config import BANNER_TIME, OS_COLORS, Color
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

    # ----------------------------------------------------------- subscriptions
    def connect(self, bus: EventBus) -> None:
        bus.subscribe(Event.SCORED, self._on_scored)
        bus.subscribe(Event.GREMLIN_SQUASHED, lambda x, y: self.burst(x, y, Color.GREMLIN))
        bus.subscribe(Event.GREMLIN_ZAPPED, self._on_gremlin_zapped)
        bus.subscribe(Event.COMPUTER_INFECTED, lambda computer: self._burst_at(computer, Color.BLOAT, 10))
        bus.subscribe(Event.COMPUTER_FRIED, lambda computer: self._burst_at(computer, Color.SURGE, 20))
        bus.subscribe(Event.OS_RESTORED, lambda computer: self._burst_at(computer, OS_COLORS[computer.native], 20))
        bus.subscribe(Event.OS_EJECTED, lambda computer: self._popup_at(computer, "OS ejected!"))
        bus.subscribe(Event.DISK_REJECTED, lambda computer, reason: self._popup_at(computer, reason))
        bus.subscribe(Event.SURGE_ZAPPED, lambda x, y: self.burst(x, y, Color.SURGE, 12))
        bus.subscribe(Event.SURGE_CLEARED, lambda x, y: self.burst(x, y, Color.ICE, 8))
        bus.subscribe(Event.POWERUP_COLLECTED, self._on_powerup)

    def _on_scored(self, points, x, y):
        self.popup(x, y - 20, f"+{points}", Color.YELLOW)

    def _on_gremlin_zapped(self, x, y):
        self.burst(x, y, Color.GREMLIN)
        self.popup(x, y - 20, "ZAP!", Color.SURGE)

    def _on_powerup(self, x, y, text):
        self.burst(x, y, Color.YELLOW, 24)
        self.banner = Banner(text)

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

    def popup(self, x: float, y: float, text: str, color) -> None:
        self.popups.append(Popup(x, y, text, color))

    def clear(self) -> None:
        self.particles.clear()
        self.popups.clear()
        self.banner = None

    def update(self, dt: float) -> None:
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
