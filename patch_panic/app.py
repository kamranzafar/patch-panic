"""Application shell: window, main loop and scene management."""
from __future__ import annotations

import pygame

from . import sprites
from .audio import MIXER_SETTINGS, SoundBank
from .config import FPS, HEIGHT, MAX_FRAME_TIME, SWAT_FLASH_TIME, TITLE, WIDTH
from .effects import Effects
from .events import EventBus
from .render import Renderer
from .scenes import PlayScene, Scene, TitleScene
from .storage import HighScoreStore


class App:
    def __init__(self) -> None:
        pygame.mixer.pre_init(**MIXER_SETTINGS)
        pygame.init()
        pygame.display.set_caption(TITLE)
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.SCALED | pygame.RESIZABLE)
        pygame.mouse.set_visible(False)

        art = sprites.load_sprites()  # needs the display to exist (convert_alpha)
        pygame.display.set_icon(art["logo_bloat"])
        self.renderer = Renderer(self.screen, art)

        # Observers: sound and visual effects react to game events.
        self.bus = EventBus()
        self.sounds = SoundBank()
        self.sounds.connect(self.bus)
        self.effects = Effects()
        self.effects.connect(self.bus)

        self.highscores = HighScoreStore()
        self.clock = pygame.time.Clock()
        self.time = 0.0
        self.swat_flash = 0.0
        self.running = True
        self.scene: Scene = TitleScene(self)

    # ----------------------------------------------------- scene management
    def change_scene(self, scene: Scene) -> None:
        self.scene = scene

    def start_game(self) -> None:
        self.change_scene(PlayScene(self, level=1, score=0))

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
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_m:
                self.sounds.toggle_mute()
                return True
            if event.key in (pygame.K_f, pygame.K_F11):
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
