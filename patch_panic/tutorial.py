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

"""The tutorial: a guided level that introduces one mechanic at a time.

`TutorialScene` is a `PlayScene` over a scripted `World` (nothing spawns by
itself and the level never ends). It walks through a list of steps (State
pattern): each step sets up a situation, says what to do, finishes when a
particular game event arrives, and can be retried if the player misses it.
"""
from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from .config import BLOAT, GameMode, LevelConfig
from .entities import Computer, Point, nearest_exit
from .events import Event
from .run import Run
from .scenes import PlayScene, is_left_click
from .world import World

if TYPE_CHECKING:
    from .app import App

STEP_PAUSE = 1.2  # seconds of "Nice!" between steps


class TutorialStep(ABC):
    hint = ""
    done_on: Event

    @abstractmethod
    def start(self, world: World) -> None:
        """Set up the situation for this step."""

    def failed(self, world: World) -> bool:
        """Has the player missed the chance, so the step should be retried?"""
        return False

    def handoff(self, world: World) -> bool:
        """Should the next step start right now, on the board as it is (no reset)?"""
        return False

    def focus(self, world: World) -> list[Point]:
        """Places the player should look at; the scene points at them."""
        return []


class SwatStep(TutorialStep):
    hint = "Click the gremlin to swat it before its ring fills up!"
    done_on = Event.GREMLIN_SQUASHED

    def start(self, world):
        world.spawn_gremlin(world.computers[0])

    def failed(self, world):
        return any(c.os == BLOAT for c in world.computers)


class RescueStep(TutorialStep):
    hint = "A gremlin stole an OS! Swat it, then drag the disk back to its computer."
    done_on = Event.OS_RESTORED

    def start(self, world):
        computer = world.computers[1]
        gremlin = world.spawn_gremlin(computer)
        gremlin.x, gremlin.y = computer.work_spot()
        gremlin.release_target()
        gremlin.carry, computer.os = computer.native, BLOAT
        gremlin.leave(nearest_exit(gremlin.x, gremlin.y))

    def failed(self, world):
        return not (world.gremlins or world.disks or world.dragging)  # it got away with the disk

    def focus(self, world):
        return [(d.x, d.y) for d in world.disks]


class SurgeStep(TutorialStep):
    hint = "A cable is flashing: click the spark before it reaches a computer!"
    done_on = Event.SURGE_ZAPPED

    def start(self, world):
        src, dst = world.cables[0]
        world.warn_surge(src, dst, 0.1)

    def handoff(self, world):
        # Missed the spark: the machine is fried and its disk is out, which is exactly the next lesson.
        return any(c.is_rebooting for c in world.computers)


class FryStep(TutorialStep):
    """A surge gets through: the machine reboots and ejects its OS disk, which has to go back."""

    done_on = Event.OS_RESTORED

    def __init__(self) -> None:
        self.computer: Computer | None = None

    @property
    def hint(self) -> str:
        if self.computer is None or self.computer.is_clean:
            return "Watch out: a surge is about to hit a computer!"
        if self.computer.is_rebooting:
            return "A surge fried this computer and ejected its OS disk. Wait for the reboot..."
        return "Rebooted! Drag the disk back before it blinks out."

    def start(self, world):
        self.computer = next((c for c in world.computers if c.is_rebooting), None)  # handed over from a miss
        if self.computer is None:
            src, dst = world.cables[0]
            self.computer = dst
            world.spawn_surge(src, dst, 0.999)  # lands on the next tick

    def focus(self, world):
        return [(d.x, d.y) for d in world.disks]

    def failed(self, world):
        stranded = self.computer.is_broken and not self.computer.is_rebooting
        return stranded and not (world.surges or world.disks or world.dragging)  # the disk expired


class PatchStep(TutorialStep):
    hint = "Grab the golden patch for bonus points and a power-up!"
    done_on = Event.POWERUP_COLLECTED

    def start(self, world):
        world.spawn_powerup()

    def failed(self, world):
        return world.powerup is None


def tutorial_steps() -> list[TutorialStep]:
    return [SwatStep(), RescueStep(), SurgeStep(), FryStep(), PatchStep()]


class TutorialScene(PlayScene):
    DONE_HINT = "Tutorial complete! Click to return to the title."

    def __init__(self, app: App) -> None:
        self.steps = tutorial_steps()
        self.index = 0
        self.step_done = False
        self.pause = 0.0
        super().__init__(app, Run(GameMode.TUTORIAL))
        self._handlers = {event: (lambda _event=event, **_: self._on_event(_event))
                          for event in {step.done_on for step in self.steps}}
        for event, handler in self._handlers.items():
            app.bus.subscribe(event, handler)
        self.steps[0].start(self.world)

    def make_world(self, level, score, safety):
        return World(level, score, self.app.bus, random.Random(7), LevelConfig.tutorial(), scripted=True)

    @property
    def step(self) -> TutorialStep | None:
        return self.steps[self.index] if self.index < len(self.steps) else None

    @property
    def finished(self) -> bool:
        return self.step is None

    def hint(self) -> str:
        if self.finished:
            return self.DONE_HINT
        return "Nice!" if self.step_done else self.step.hint

    # ---------------------------------------------------------------- events
    def _on_event(self, event: Event) -> None:
        if self.step is not None and not self.step_done and event is self.step.done_on:
            self.step_done = True
            self.pause = STEP_PAUSE

    def on_exit(self):
        for event, handler in self._handlers.items():
            self.app.bus.unsubscribe(event, handler)

    def handle_event(self, event):
        if self.finished and is_left_click(event):
            self.app.show_title()
        else:
            super().handle_event(event)

    def update(self, dt):
        super().update(dt)
        if self.paused or self.finished:
            return
        if self.step_done:
            self.pause -= dt
            if self.pause <= 0:
                self._next_step()
        elif self.step.handoff(self.world):
            self._next_step(reset=False)
        elif self.step.failed(self.world):
            self.world.reset_board()
            self.step.start(self.world)

    def _next_step(self, reset: bool = True) -> None:
        self.index += 1
        self.step_done = False
        if reset:
            self.world.reset_board()
        if self.step is not None:
            self.step.start(self.world)

    def draw(self, renderer, t):
        super().draw(renderer, t)
        if self.paused:
            return
        if self.finished:
            renderer.draw_hint(self.hint())
            return
        if not self.step_done:
            for pos in self.step.focus(self.world):
                renderer.draw_attention(pos, t)
        renderer.draw_hint(f"{self.index + 1}/{len(self.steps)}  {self.hint()}")
