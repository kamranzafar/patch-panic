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

Menu screens share `MenuScene`, which handles a list of clickable buttons.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING, Callable

import pygame

from .achievements import ACHIEVEMENTS
from . import __version__
from .config import (BLOAT, COPYRIGHT, GAME_OVER_CLICK_DELAY, INITIALS_LENGTH, LEVEL_DONE_CLICK_DELAY, TITLE, WIDTH, Color,
                     Difficulty, GameMode)
from .entities import Computer, Gremlin, GremlinState
from .render import Renderer
from .run import Run
from .settings import Action
from .storage import ScoreEntry
from .world import Outcome, World

if TYPE_CHECKING:
    from .app import App


def is_left_click(event: pygame.event.Event) -> bool:
    return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1


def is_key(event: pygame.event.Event, *keys: int) -> bool:
    return event.type == pygame.KEYDOWN and event.key in keys


def on_off(value: bool) -> str:
    return "On" if value else "Off"


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

    @property
    def captures_keys(self) -> bool:
        """True while the scene wants every key itself (typing, rebinding), so global keys don't fire."""
        return False

    def on_focus_lost(self) -> None:
        """The window lost focus (e.g. the player switched apps)."""

    def on_exit(self) -> None:
        """Called when the app switches to another scene."""


# ---------------------------------------------------------------------- menus
@dataclass
class Button:
    rect: pygame.Rect
    label: Callable[[], str]
    action: Callable[[], None]
    hotkey: int | None = None
    selected: Callable[[], bool] = lambda: False

    @property
    def hot(self) -> bool:
        return self.rect.collidepoint(pygame.mouse.get_pos())


class MenuScene(Scene):
    """A scene with clickable buttons (and optional number-key shortcuts)."""

    def __init__(self, app: App) -> None:
        super().__init__(app)
        self.buttons: list[Button] = []

    def add_button(self, rect: tuple[int, int, int, int], label: str | Callable[[], str],
                   action: Callable[[], None], hotkey: int | None = None,
                   selected: Callable[[], bool] = lambda: False) -> Button:
        text = label if callable(label) else (lambda: label)
        button = Button(pygame.Rect(rect), text, action, hotkey, selected)
        self.buttons.append(button)
        return button

    def handle_event(self, event):
        if is_left_click(event):
            for button in self.buttons:
                if button.rect.collidepoint(event.pos):
                    button.action()
                    return
        elif event.type == pygame.KEYDOWN:
            for button in self.buttons:
                if button.hotkey is not None and event.key == button.hotkey:
                    button.action()
                    return

    def draw_buttons(self, renderer: Renderer) -> None:
        for button in self.buttons:
            renderer.draw_button(button.rect, button.label(), button.hot, button.selected())


def button_row(count: int, width: int, gap: int, y: int, height: int) -> list[tuple[int, int, int, int]]:
    """Rects for `count` buttons centred in a row."""
    left = (WIDTH - (count * width + (count - 1) * gap)) // 2
    return [(left + i * (width + gap), y, width, height) for i in range(count)]


class TitleScene(MenuScene):
    HELP = (
        "Swat gremlins before they install BloatOS, and drag stolen disks back home.",
        "Zap power surges on the cables and grab the golden patch for a power-up.",
        "Keep half your computers clean to survive. New? Try the Tutorial!",
    )
    DEMO_Y = 404
    DEMO_INSTALL_TIME = 2.5

    def __init__(self, app: App) -> None:
        super().__init__(app)
        self.demo_computer = Computer(WIDTH // 2 - 60, 400, 0)
        self.demo_gremlin: Gremlin | None = None
        entries = (
            ("Classic", lambda: app.start_game(Run.classic(app.settings.difficulty))),
            ("Daily", lambda: app.start_game(Run.daily())),
            ("Tutorial", app.start_tutorial),
            ("Scores", lambda: app.change_scene(LeaderboardScene(app))),
            ("Settings", lambda: app.change_scene(SettingsScene(app))),
        )
        for i, (rect, (label, action)) in enumerate(zip(button_row(len(entries), 160, 14, 486, 50), entries)):
            self.add_button(rect, f"{i + 1}  {label}", action, hotkey=pygame.K_1 + i)

    def handle_event(self, event):
        if is_key(event, pygame.K_ESCAPE):
            self.app.quit()
        else:
            super().handle_event(event)

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
        f, settings = renderer.fonts, self.app.settings
        renderer.draw_floor()
        renderer.text(TITLE, f.big, Color.YELLOW, (WIDTH // 2, 120 + math.sin(t * 2) * 4))
        renderer.text("Defend your workstations from bloatware gremlins!", f.normal, Color.WHITE, (WIDTH // 2, 185))
        for i, line in enumerate(self.HELP):
            renderer.text(line, f.small, Color.GREY, (WIDTH // 2, 240 + i * 26))
        renderer.draw_computer(self.demo_computer, t)
        if self.demo_gremlin:
            renderer.draw_gremlin(self.demo_gremlin, t)
        self.draw_buttons(renderer)
        renderer.text(f"High score: {self.app.save.best}      Difficulty: {settings.difficulty.label}",
                      f.normal, Color.YELLOW, (WIDTH // 2, 560))
        keys = "   ".join(f"{settings.key_name(a)} {a.label.lower()}" for a in Action)
        renderer.text(f"{keys}   Esc quit", f.small, Color.GREY, (WIDTH // 2, 592))
        renderer.text(f"v{__version__}   {COPYRIGHT}", f.small, Color.GREY, (WIDTH // 2, 620), shadow=False)


class SettingsScene(MenuScene):
    def __init__(self, app: App) -> None:
        super().__init__(app)
        self.rebinding: Action | None = None
        settings = app.settings
        rows = [
            (lambda: f"Difficulty: {settings.difficulty.label}", self._cycle_difficulty),
            (lambda: f"Colourblind shapes: {on_off(settings.colourblind)}", lambda: self._toggle("colourblind")),
            (lambda: f"Screen shake: {on_off(settings.screen_shake)}", lambda: self._toggle("screen_shake")),
            (lambda: f"Pause when window loses focus: {on_off(settings.auto_pause)}",
             lambda: self._toggle("auto_pause")),
        ]
        for action in Action:
            rows.append((lambda a=action: self._key_label(a), lambda a=action: self._start_rebind(a)))
        rows.append((lambda: "Back", self._close))
        for i, (label, callback) in enumerate(rows):
            self.add_button(((WIDTH - 460) // 2, 120 + i * 58, 460, 46), label, callback)

    @property
    def captures_keys(self) -> bool:
        return self.rebinding is not None

    def _key_label(self, action: Action) -> str:
        if self.rebinding is action:
            return f"{action.label} key: press a key..."
        return f"{action.label} key: {self.app.settings.key_name(action)}"

    def _cycle_difficulty(self) -> None:
        self.app.settings.difficulty = self.app.settings.difficulty.next()
        self.app.save_settings()

    def _toggle(self, name: str) -> None:
        setattr(self.app.settings, name, not getattr(self.app.settings, name))
        self.app.save_settings()

    def _start_rebind(self, action: Action) -> None:
        self.rebinding = action

    def _close(self) -> None:
        self.app.save_settings()
        self.app.show_title()

    def handle_event(self, event):
        if self.rebinding is not None and event.type == pygame.KEYDOWN:
            if event.key != pygame.K_ESCAPE:  # Esc cancels; it is always "back"
                self.app.settings.rebind(self.rebinding, event.key)
                self.app.save_settings()
            self.rebinding = None
        elif is_key(event, pygame.K_ESCAPE):
            self._close()
        else:
            self.rebinding = None
            super().handle_event(event)

    def draw(self, renderer, t):
        renderer.draw_floor()
        renderer.text("Settings", renderer.fonts.medium, Color.YELLOW, (WIDTH // 2, 70))
        self.draw_buttons(renderer)


class LeaderboardScene(MenuScene):
    TABS = ("All-time", "Today's Daily")

    def __init__(self, app: App) -> None:
        super().__init__(app)
        self.tab = 0
        for i, (rect, label) in enumerate(zip(button_row(2, 200, 14, 100, 42), self.TABS)):
            self.add_button(rect, label, lambda i=i: self._select(i), selected=lambda i=i: self.tab == i)
        self.add_button((60, 572, 160, 44), "Back", app.show_title)

    def _select(self, tab: int) -> None:
        self.tab = tab

    def entries(self) -> list[ScoreEntry]:
        if self.tab == 0:
            return self.app.save.leaderboard
        return self.app.save.entries_for(GameMode.DAILY, date.today().isoformat())

    def handle_event(self, event):
        if is_key(event, pygame.K_ESCAPE):
            self.app.show_title()
        elif is_key(event, pygame.K_TAB, pygame.K_LEFT, pygame.K_RIGHT):
            self.tab = 1 - self.tab
        else:
            super().handle_event(event)

    def draw(self, renderer, t):
        f = renderer.fonts
        renderer.draw_floor()
        renderer.text("Hall of Fame", f.medium, Color.YELLOW, (WIDTH // 2, 60))
        self.draw_buttons(renderer)

        entries = self.entries()
        if not entries:
            renderer.text("No scores yet", f.normal, Color.GREY, (250, 190))
        for i, e in enumerate(entries):
            y = 180 + i * 34
            mode = GameMode[e.mode].label if e.mode in GameMode.__members__ else e.mode
            color = Color.YELLOW if i == 0 else Color.WHITE
            renderer.text(f"{i + 1:>2}.", f.normal, Color.GREY, (60, y), "midleft")
            renderer.text(e.initials, f.normal, color, (110, y), "midleft")
            renderer.text(str(e.score), f.normal, color, (270, y), "midright")
            level = f"L{e.level}" if e.level else ""
            renderer.text(f"{level}  {mode}", f.small, Color.GREY, (290, y), "midleft")

        unlocked = self.app.save.achievements
        renderer.text(f"Achievements {len(unlocked & {a.id for a in ACHIEVEMENTS})}/{len(ACHIEVEMENTS)}",
                      f.normal, Color.YELLOW, (520, 180), "midleft")
        for i, a in enumerate(ACHIEVEMENTS):
            y = 218 + i * 44
            got = a.id in unlocked
            renderer.text(("* " if got else "- ") + a.title, f.normal, Color.WHITE if got else Color.LOCKED,
                          (520, y), "midleft")
            renderer.text(a.description, f.small, Color.GREY if got else Color.LOCKED, (545, y + 19), "midleft")


# ---------------------------------------------------------------------- play
class PlayScene(Scene):
    def __init__(self, app: App, run: Run, level: int = 1, score: int = 0, safety: int = 0) -> None:
        super().__init__(app)
        self.run = run
        self.world = self.make_world(level, score, safety)
        self.paused = False
        app.effects.clear()

    def make_world(self, level: int, score: int, safety: int) -> World:
        run = self.run
        return World(level, score, self.app.bus, run.level_rng(level), run.level_config(level), safety)

    def handle_event(self, event):
        if is_key(event, pygame.K_ESCAPE):
            self.app.show_title()
        elif self.app.settings.is_action(event, Action.PAUSE):
            self.paused = not self.paused
        elif is_left_click(event):
            if self.paused:
                self.paused = False
            else:
                self.world.click(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.world.release(event.pos)

    def on_focus_lost(self):
        if self.app.settings.auto_pause:
            self.paused = True

    def update(self, dt):
        super().update(dt)
        if self.paused or self.app.effects.hitstop > 0:
            return
        self.world.update(dt)
        if self.world.outcome is Outcome.CLEARED:
            self.on_cleared()
        elif self.world.outcome is Outcome.FAILED:
            self.on_failed()

    def on_cleared(self) -> None:
        self.app.change_scene(LevelCompleteScene(self.app, self.world, self.run))

    def on_failed(self) -> None:
        if self.app.save.qualifies(self.world.score):
            self.app.change_scene(InitialsScene(self.app, self.world, self.run))
        else:
            self.app.change_scene(GameOverScene(self.app, self.world, self.run, new_high=False))

    def hud_tags(self) -> tuple[str, ...]:
        if self.run.mode is not GameMode.CLASSIC:
            return (self.run.mode.label,)
        if self.run.difficulty is not Difficulty.NORMAL:
            return (self.run.difficulty.label,)
        return ()

    def draw(self, renderer, t):
        renderer.draw_world(self.world, self.app.effects, t)
        renderer.draw_hud(self.world, self.app.save.best, self.app.sounds.muted, self.hud_tags())
        if self.paused:
            key = self.app.settings.key_name(Action.PAUSE)
            renderer.draw_panel(["PAUSED", "", f"Press {key} or click to resume"])

    def dragging_kind(self):
        return self.world.dragging.kind if self.world.dragging else None


class ResultScene(Scene):
    """Base for the screens shown over a finished level."""

    CLICK_DELAY = 0.0  # ignore clicks briefly so a frantic swat doesn't skip the screen

    def __init__(self, app: App, world: World, run: Run) -> None:
        super().__init__(app)
        self.world = world
        self.run = run

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
        renderer.draw_hud(self.world, self.app.save.best, self.app.sounds.muted)
        renderer.draw_panel(self.panel_lines())


class LevelCompleteScene(ResultScene):
    CLICK_DELAY = LEVEL_DONE_CLICK_DELAY

    def on_continue(self):
        world = self.world
        self.app.change_scene(PlayScene(self.app, self.run, world.level + 1, world.score, world.earned_safety))

    def panel_lines(self):
        world = self.world
        lines = [f"Level {world.level} cleared!",
                 f"Clean computers: {world.clean_count}/{len(world.computers)}",
                 f"Bonus: +{world.level_bonus}"]
        if world.perfect_bonus:
            lines += [f"Perfect level: +{world.perfect_bonus}", "Safety net for the next level!"]
        lines.append("Click to continue")
        return lines


class InitialsScene(ResultScene):
    """Arcade-style name entry for a score that makes the leaderboard."""

    CLICK_DELAY = GAME_OVER_CLICK_DELAY

    def __init__(self, app: App, world: World, run: Run) -> None:
        super().__init__(app, world, run)
        self.letters = ""
        self.new_best = world.score > app.save.best

    @property
    def captures_keys(self) -> bool:
        return True

    @property
    def initials(self) -> str:
        return self.letters or self.app.save.initials

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.on_continue()
            elif event.key == pygame.K_BACKSPACE:
                self.letters = self.letters[:-1]
            elif event.key == pygame.K_ESCAPE:
                self.on_continue()  # still record the score, with the default initials
            elif event.unicode.isascii() and event.unicode.isalpha() and len(self.letters) < INITIALS_LENGTH:
                self.letters += event.unicode.upper()
        elif is_left_click(event) and self.elapsed > self.CLICK_DELAY:
            self.on_continue()

    def on_continue(self):
        world, save = self.world, self.app.save
        entry = ScoreEntry(world.score, world.level, self.run.mode.name, self.initials.ljust(INITIALS_LENGTH, "A"),
                           date.today().isoformat())
        rank = save.record(entry)
        self.app.change_scene(GameOverScene(self.app, world, self.run, new_high=rank == 0))

    def panel_lines(self):
        slots = " ".join(self.letters.ljust(INITIALS_LENGTH, "_"))
        return ["NEW HIGH SCORE!" if self.new_best else "TOP 10 SCORE!",
                f"Score {self.world.score}   (level {self.world.level})",
                "Enter your initials:", slots,
                f"Type A-Z, Enter to save (blank = {self.app.save.initials})"]


class GameOverScene(ResultScene):
    CLICK_DELAY = GAME_OVER_CLICK_DELAY

    def __init__(self, app: App, world: World, run: Run, new_high: bool) -> None:
        super().__init__(app, world, run)
        self.new_high = new_high

    def on_continue(self):
        self.app.show_title()

    def panel_lines(self):
        lines = ["SYSTEM FAILURE", "Too many machines are running BloatOS.",
                 f"Final score: {self.world.score}  (level {self.world.level})"]
        if self.new_high:
            lines.append("New high score!")
        lines += self.app.stats.summary_lines()
        lines.append("Click to return to title")
        return lines
