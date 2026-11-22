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

"""Application shell: window, main loop and scene management."""
from __future__ import annotations

import pygame

from . import sprites
from .achievements import AchievementTracker
from .audio import MIXER_SETTINGS, SoundBank
from .config import FPS, HEIGHT, MAX_FRAME_TIME, SWAT_FLASH_TIME, TITLE, WIDTH
from .effects import Effects
from .events import EventBus
from .render import Renderer
from .run import Run
from .scenes import PlayScene, Scene, TitleScene
from .settings import Action, Settings
from .stats import RunStats
from .storage import SaveStore
from .tutorial import TutorialScene


class App:
    def __init__(self) -> None:
        pygame.mixer.pre_init(**MIXER_SETTINGS)
        pygame.init()
        pygame.display.set_caption(TITLE)
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.SCALED | pygame.RESIZABLE)
        pygame.mouse.set_visible(False)

        art = sprites.load_sprites()  # needs the display to exist (convert_alpha)
        pygame.display.set_icon(sprites.scale(sprites.build_icon(), sprites.ICON_WINDOW_SCALE))
        self.renderer = Renderer(self.screen, art)

        # Observers: sound and visual effects react to game events.
        self.bus = EventBus()
        self.sounds = SoundBank()
        self.sounds.connect(self.bus)
        self.effects = Effects()
        self.effects.connect(self.bus)

        self.save = SaveStore()
        self.settings = Settings.from_dict(self.save.settings)
        self.apply_settings()
        # Stats first: achievements read them when the same event arrives.
        self.stats = RunStats()
        self.stats.connect(self.bus)
        self.achievements = AchievementTracker(self.stats, self.save)
        self.achievements.connect(self.bus)
        self.clock = pygame.time.Clock()
        self.time = 0.0
        self.swat_flash = 0.0
        self.running = True
        self.scene: Scene = TitleScene(self)

    # ----------------------------------------------------- scene management
    def change_scene(self, scene: Scene) -> None:
        self.scene.on_exit()
        self.scene = scene

    def start_game(self, run: Run) -> None:
        self.stats.reset(run.mode)
        self.achievements.enabled = True
        self.change_scene(PlayScene(self, run))

    def start_tutorial(self) -> None:
        self.achievements.enabled = False
        self.change_scene(TutorialScene(self))

    def save_settings(self) -> None:
        self.apply_settings()
        self.save.settings = self.settings.to_dict()
        self.save.save()

    def apply_settings(self) -> None:
        self.effects.motion = self.settings.screen_shake
        self.renderer.colourblind = self.settings.colourblind

    def show_title(self) -> None:
        self.change_scene(TitleScene(self))

    def quit(self) -> None:
        self.running = False

    # ------------------------------------------------------------ main loop
    def run(self) -> None:
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, MAX_FRAME_TIME)
            self.time += dt
            for event in pygame.event.get():
                if event.type == pygame.WINDOWFOCUSLOST:
                    self.scene.on_focus_lost()
                if not self._handle_global(event):
                    self.scene.handle_event(event)
            self.scene.update(dt)
            self.effects.update(dt)
            self.swat_flash = max(0.0, self.swat_flash - dt)
            self._draw()
        pygame.quit()

    def _handle_global(self, event: pygame.event.Event) -> bool:
        """Input that works on every screen. Returns True if consumed."""
        if event.type == pygame.QUIT:
            self.quit()
            return True
        if event.type == pygame.KEYDOWN and not self.scene.captures_keys:
            if self.settings.is_action(event, Action.MUTE):
                self.sounds.toggle_mute()
                return True
            if self.settings.is_action(event, Action.FULLSCREEN) or event.key == pygame.K_F11:
                pygame.display.toggle_fullscreen()
                return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.swat_flash = SWAT_FLASH_TIME  # cursor feedback; the scene still handles the click
        return False

    def _draw(self) -> None:
        self.scene.draw(self.renderer, self.time)
        self.renderer.draw_cursor(pygame.mouse.get_pos(), self.scene.dragging_kind(), self.swat_flash > 0)
        pygame.display.flip()


def main() -> None:
    App().run()
