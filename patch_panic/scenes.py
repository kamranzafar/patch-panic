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

"""Game screens (State pattern).

Each screen is a `Scene` with the same three methods. The `App` forwards
events/updates/draws to whichever scene is current, and scenes switch by
calling `app.change_scene(...)`. This replaces a tangle of
`if state == "..."` checks with one small class per screen.
"""
from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING

import pygame

from .config import (BLOAT, GAME_OVER_CLICK_DELAY, LEVEL_DONE_CLICK_DELAY, TITLE, WIDTH, Color)
from .entities import Computer, Gremlin, GremlinState
from .render import Renderer
from .world import Outcome, World

if TYPE_CHECKING:
    from .app import App


def is_left_click(event: pygame.event.Event) -> bool:
    return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1


def is_key(event: pygame.event.Event, *keys: int) -> bool:
    return event.type == pygame.KEYDOWN and event.key in keys


class Scene:
    def __init__(self, app: App) -> None:
        self.app = app
        self.elapsed = 0.0

    def handle_event(self, event: pygame.event.Event) -> None:
        pass

    def update(self, dt: float) -> None:
        self.elapsed += dt

    def draw(self, renderer: Renderer, t: float) -> None:
        pass

    def dragging_kind(self) -> int | None:
        """OS kind of the disk being dragged (the cursor shows it)."""
        return None


class TitleScene(Scene):
    HELP = (
        "Click gremlins to swat them before their install finishes.",
        "Swat a fleeing gremlin to make it drop the OS disk it stole,",
        "then drag the disk onto a computer with the matching colour stripe.",
        "Click power surges on the cables before they fry a machine and eject its OS.",
        "Grab the golden patch that flies past mid-level for a power-up.",
        "Keep at least half your computers clean to survive each level.",
    )
    DEMO_Y = 404
    DEMO_INSTALL_TIME = 2.5

    def __init__(self, app: App) -> None:
        super().__init__(app)
        self.demo_computer = Computer(WIDTH // 2 - 60, 400, 0)
        self.demo_gremlin: Gremlin | None = None

    def handle_event(self, event):
        if is_left_click(event):
            self.app.start_game()
        elif is_key(event, pygame.K_ESCAPE):
            self.app.quit()

    def update(self, dt):
        super().update(dt)
        self._run_demo(dt)

    def _run_demo(self, dt: float) -> None:
        """A scripted gremlin infecting a computer, looping forever."""
        computer, g = self.demo_computer, self.demo_gremlin
        if g is None:
            computer.os, computer.targeted = computer.native, None
            g = self.demo_gremlin = Gremlin(WIDTH + 30, self.DEMO_Y, speed=90)
            g.assign(computer)
        if g.state is GremlinState.WALK_IN and g.move_toward(*computer.work_spot(), dt):
            g.start_install()
        elif g.state is GremlinState.INSTALL:
            g.timer += dt
            computer.install = min(1.0, g.timer / self.DEMO_INSTALL_TIME)
            if g.timer > self.DEMO_INSTALL_TIME:
                g.carry, computer.os, computer.install = computer.os, BLOAT, 0.0
                g.leave((WIDTH + 30, self.DEMO_Y))
        elif g.state is GremlinState.WALK_OUT and g.move_toward(*g.exit, dt):
            self.demo_gremlin = None

    def draw(self, renderer, t):
        f = renderer.fonts
        renderer.draw_floor()
        renderer.text(TITLE, f.big, Color.YELLOW, (WIDTH // 2, 120 + math.sin(t * 2) * 4))
        renderer.text("Defend your workstations from bloatware gremlins!", f.normal, Color.WHITE, (WIDTH // 2, 185))
        for i, line in enumerate(self.HELP):
            renderer.text(line, f.small, Color.GREY, (WIDTH // 2, 232 + i * 23))
        renderer.draw_computer(self.demo_computer, t)
        if self.demo_gremlin:
            renderer.draw_gremlin(self.demo_gremlin, t)
        if int(t * 2) % 2:
            renderer.text("Click to start", f.medium, Color.WHITE, (WIDTH // 2, 520))
        renderer.text(f"High score: {self.app.highscores.best}", f.normal, Color.YELLOW, (WIDTH // 2, 570))
        renderer.text("P pause   M mute   F fullscreen   Esc quit", f.small, Color.GREY, (WIDTH // 2, 610))


class PlayScene(Scene):
    def __init__(self, app: App, level: int, score: int) -> None:
        super().__init__(app)
        self.world = World(level, score, app.bus, random.Random())
        self.paused = False
        app.effects.clear()

    def handle_event(self, event):
        if is_key(event, pygame.K_ESCAPE):
            self.app.show_title()
        elif is_key(event, pygame.K_p):
            self.paused = not self.paused
        elif is_left_click(event):
            if self.paused:
                self.paused = False
            else:
                self.world.click(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.world.release(event.pos)

    def update(self, dt):
        super().update(dt)
        if self.paused:
            return
        self.world.update(dt)
        if self.world.outcome is Outcome.CLEARED:
            self.app.change_scene(LevelCompleteScene(self.app, self.world))
        elif self.world.outcome is Outcome.FAILED:
            new_high = self.app.highscores.submit(self.world.score)
            self.app.change_scene(GameOverScene(self.app, self.world, new_high))

    def draw(self, renderer, t):
        renderer.draw_world(self.world, self.app.effects, t)
        renderer.draw_hud(self.world, self.app.highscores.best, self.app.sounds.muted)
        if self.paused:
            renderer.draw_panel(["PAUSED", "", "Press P or click to resume"])

    def dragging_kind(self):
        return self.world.dragging.kind if self.world.dragging else None


class ResultScene(Scene):
    """Base for the screens shown over a finished level."""

    CLICK_DELAY = 0.0  # ignore clicks briefly so a frantic swat doesn't skip the screen

    def __init__(self, app: App, world: World) -> None:
        super().__init__(app)
        self.world = world

    def handle_event(self, event):
        if is_key(event, pygame.K_ESCAPE):
            self.app.show_title()
        elif is_left_click(event) and self.elapsed > self.CLICK_DELAY:
            self.on_continue()

    def on_continue(self) -> None:
        raise NotImplementedError

    def panel_lines(self) -> list[str]:
        raise NotImplementedError

    def draw(self, renderer, t):
        renderer.draw_world(self.world, self.app.effects, t)
        renderer.draw_hud(self.world, self.app.highscores.best, self.app.sounds.muted)
        renderer.draw_panel(self.panel_lines())


class LevelCompleteScene(ResultScene):
    CLICK_DELAY = LEVEL_DONE_CLICK_DELAY

    def on_continue(self):
        self.app.change_scene(PlayScene(self.app, self.world.level + 1, self.world.score))

    def panel_lines(self):
        return [
            f"Level {self.world.level} cleared!",
            f"Clean computers: {self.world.clean_count}/{len(self.world.computers)}",
            f"Bonus: +{self.world.level_bonus}",
            "Click to continue",
        ]


class GameOverScene(ResultScene):
    CLICK_DELAY = GAME_OVER_CLICK_DELAY

    def __init__(self, app: App, world: World, new_high: bool) -> None:
        super().__init__(app, world)
        self.new_high = new_high

    def on_continue(self):
        self.app.show_title()

    def panel_lines(self):
        lines = ["SYSTEM FAILURE", "Too many machines are running BloatOS.",
                 f"Final score: {self.world.score}  (level {self.world.level})"]
        if self.new_high:
            lines.append("New high score!")
        lines.append("Click to return to title")
        return lines
