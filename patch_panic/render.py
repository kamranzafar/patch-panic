"""All drawing. Reads game state; never changes it."""
from __future__ import annotations

import math
import random

import pygame

from . import sprites
from .config import BLOAT, DISK_BLINK_TIME, DYING_TIME, HEIGHT, HUD_HEIGHT, OS_COLORS, WIDTH, Color
from .effects import Effects
from .entities import Computer, Disk, Gremlin, GremlinState, Point, PowerUp, Surge
from .world import World


class Fonts:
    def __init__(self) -> None:
        self.big = pygame.font.Font(None, 96)
        self.medium = pygame.font.Font(None, 44)
        self.normal = pygame.font.Font(None, 30)
        self.small = pygame.font.Font(None, 22)


class Renderer:
    def __init__(self, surface: pygame.Surface, art: dict[str, pygame.Surface]) -> None:
        self.surface = surface
        self.art = art
        self.fonts = Fonts()
        self._flipped: dict[str, pygame.Surface] = {}
        self._floor = self._build_floor()
        self._ice = self._build_ice_bubble()
        self._level_bg: pygame.Surface | None = None
        self._level_bg_world: World | None = None

    # -------------------------------------------------------------- helpers
    def sprite(self, name: str, flip: bool = False) -> pygame.Surface:
        if not flip:
            return self.art[name]
        if name not in self._flipped:
            self._flipped[name] = pygame.transform.flip(self.art[name], True, False)
        return self._flipped[name]

    def blit_center(self, image: pygame.Surface, center: Point) -> None:
        self.surface.blit(image, image.get_rect(center=(round(center[0]), round(center[1]))))

    def text(self, text: str, font: pygame.font.Font, color, pos: Point,
             anchor: str = "center", shadow: bool = True) -> pygame.Rect:
        image = font.render(text, True, color)
        rect = image.get_rect(**{anchor: pos})
        if shadow:
            self.surface.blit(font.render(text, True, Color.BLACK), rect.move(2, 2))
        self.surface.blit(image, rect)
        return rect

    def _build_floor(self) -> pygame.Surface:
        floor = pygame.Surface((WIDTH, HEIGHT))
        tile = self.art["floor"]
        for ty in range(0, HEIGHT, tile.get_height()):
            for tx in range(0, WIDTH, tile.get_width()):
                floor.blit(tile, (tx, ty))
        return floor

    @staticmethod
    def _build_ice_bubble() -> pygame.Surface:
        ice = pygame.Surface((64, 64), pygame.SRCALPHA)
        pygame.draw.circle(ice, (*Color.ICE, 100), (32, 32), 30)
        pygame.draw.circle(ice, (*Color.WHITE, 190), (32, 32), 30, 2)
        pygame.draw.arc(ice, (*Color.WHITE, 220), (10, 10, 30, 30), 1.7, 2.8, 3)
        return ice

    def _level_background(self, world: World) -> pygame.Surface:
        """Floor plus network cables, cached per level."""
        if self._level_bg_world is not world:
            self._level_bg = self._floor.copy()
            for a, b in world.cables:
                pygame.draw.line(self._level_bg, Color.CABLE, a.cable_anchor(), b.cable_anchor(), 3)
            self._level_bg_world = world
        return self._level_bg

    # ---------------------------------------------------------------- world
    def draw_floor(self) -> None:
        self.surface.blit(self._floor, (0, 0))

    def draw_world(self, world: World, effects: Effects, t: float) -> None:
        self.surface.blit(self._level_background(world), (0, 0))
        if world.is_shielded and (world.shield_timer > 2 or int(t * 6) % 2):
            for a, b in world.cables:
                pygame.draw.line(self.surface, Color.ICE, a.cable_anchor(), b.cable_anchor(), 3)
        for surge in world.surges:
            pygame.draw.line(self.surface, Color.SURGE_PATH, surge.pos, surge.dst.cable_anchor(), 4)

        # computers and live gremlins, back to front
        standing = world.computers + world.alive_gremlins
        for obj in sorted(standing, key=lambda o: (o.y, isinstance(o, Gremlin))):
            if isinstance(obj, Gremlin):
                self.draw_gremlin(obj, t)
            else:
                self.draw_computer(obj, t)

        for disk in world.disks:
            self.draw_disk(disk, t)
        for gremlin in world.gremlins:
            if not gremlin.is_alive:
                self.draw_gremlin(gremlin, t)
        for surge in world.surges:
            self.draw_surge(surge)
        if world.is_frozen:
            for gremlin in world.alive_gremlins:
                self.surface.blit(self._ice, (gremlin.x - 32, gremlin.y - 44))
        if world.powerup:
            self.draw_powerup(world.powerup, t)
        self.draw_effects(effects)

    def draw_computer(self, c: Computer, t: float) -> None:
        x, y = c.x, c.y
        pygame.draw.ellipse(self.surface, Color.SHADOW, (x - 38, y + 25, 76, 16))
        self.surface.blit(self.art[f"computer_{c.native}"], (x - 36, y - 38))
        screen = pygame.Rect(x - 27, y - 32, 54, 33)
        if c.is_rebooting:
            self.surface.blit(self.art[f"static{int(t * 14) % 2}"], screen)
            if int(t * 10) % 2:
                self.blit_center(self.art["bolt"], screen.center)
        elif c.os is None:
            if int(t * 2) % 2:
                self.blit_center(self.art["no_os"], screen.center)
        elif c.os == BLOAT:
            self.surface.fill(Color.BLOAT_SCREEN if int(t * 3) % 2 else Color.BLOAT_SCREEN_ALT, screen)
            self.blit_center(self.art["logo_bloat"], screen.center)
        else:
            r, g, b = OS_COLORS[c.os]
            self.surface.fill((r // 5, g // 5, b // 5), screen)
            self.blit_center(self.art[f"logo_{c.os}"], screen.center)
        if c.install > 0:
            bar = pygame.Rect(screen.x + 3, screen.bottom - 6, screen.w - 6, 4)
            self.surface.fill(Color.BLACK, bar)
            self.surface.fill(Color.RED, (bar.x, bar.y, bar.w * c.install, bar.h))
        if c.flash > 0:
            overlay = pygame.Surface(screen.size, pygame.SRCALPHA)
            overlay.fill((255, 255, 255, int(200 * c.flash)))
            self.surface.blit(overlay, screen)

    def draw_gremlin(self, g: Gremlin, t: float) -> None:
        x, y = g.x, g.y
        if g.state is GremlinState.DYING:
            image = self.art["gremlin_squashed"]
            progress = min(1.0, g.timer / DYING_TIME)
            if progress > 0.5:
                image = image.copy()
                image.set_alpha(int(255 * (1 - progress) * 2))
            self.surface.blit(image, (x - image.get_width() / 2, y + 16 - image.get_height()))
            return
        pygame.draw.ellipse(self.surface, Color.SHADOW, (x - 16, y + 11, 32, 9))
        if g.state is GremlinState.INSTALL:
            name, bob = f"gremlin_type{int(t * 10) % 2}", 0
        else:
            frame = int(t * 8 + g.phase) % 2
            pose = "carry" if g.carry is not None else "walk"
            name, bob = f"gremlin_{pose}{frame}", (-3 if frame else 0)
        image = self.sprite(name, flip=g.facing < 0)
        top = y - 32 + bob
        self.surface.blit(image, (x - image.get_width() / 2, top))
        if g.carry is not None:
            self.draw_disk_icon(g.carry, (x, top - 15))

    def draw_surge(self, surge: Surge) -> None:
        image = self.sprite(f"spark{random.randrange(2)}", flip=random.random() < 0.5)
        self.blit_center(image, surge.pos)

    def draw_disk(self, disk: Disk, t: float) -> None:
        if disk.remaining < DISK_BLINK_TIME and int(t * 8) % 2:
            return
        self.draw_disk_icon(disk.kind, (disk.x, disk.y))

    def draw_disk_icon(self, kind: int, center: Point) -> None:
        self.blit_center(self.art[f"disk_{kind}"], center)

    def draw_powerup(self, powerup: PowerUp, t: float) -> None:
        pulse = 0.5 + 0.5 * math.sin(t * 8)
        glow = pygame.Surface((80, 80), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*Color.YELLOW, int(60 + 60 * pulse)), (40, 40), 28 + 6 * pulse)
        self.surface.blit(glow, (powerup.x - 40, powerup.y - 40))
        self.blit_center(self.art[f"star{int(t * 5) % 2}"], (powerup.x, powerup.y))

    def draw_effects(self, effects: Effects) -> None:
        for p in effects.particles:
            pygame.draw.circle(self.surface, p.color, (p.x, p.y), max(1, int(p.life * 7)))
        for p in effects.popups:
            image = self.fonts.normal.render(p.text, True, p.color)
            image.set_alpha(int(255 * min(1.0, p.life * 2)))
            self.surface.blit(image, image.get_rect(center=(p.x, p.y)))
        if effects.banner:
            alpha = min(1.0, effects.banner.life * 2)
            image = self.fonts.medium.render(effects.banner.text, True, Color.YELLOW)
            image.set_alpha(int(255 * alpha))
            rect = image.get_rect(center=(WIDTH // 2, HUD_HEIGHT + 50))
            back = pygame.Surface(rect.inflate(30, 16).size, pygame.SRCALPHA)
            back.fill((0, 0, 0, int(140 * alpha)))
            self.surface.blit(back, rect.inflate(30, 16))
            self.surface.blit(image, rect)

    # ------------------------------------------------------------------- UI
    def draw_hud(self, world: World, best: int, muted: bool) -> None:
        pygame.draw.rect(self.surface, Color.HUD_BG, (0, 0, WIDTH, HUD_HEIGHT))
        pygame.draw.line(self.surface, Color.HUD_LINE, (0, HUD_HEIGHT - 1), (WIDTH, HUD_HEIGHT - 1))
        clean, total = world.clean_count, len(world.computers)
        cy = HUD_HEIGHT // 2
        f = self.fonts
        self.text(f"Level {world.level}", f.normal, Color.WHITE, (16, cy), "midleft", False)
        self.text(f"Score {world.score}", f.normal, Color.YELLOW, (150, cy), "midleft", False)
        self.text(f"Clean {clean}/{total}", f.normal, Color.WHITE if clean * 2 >= total else Color.RED,
                  (340, cy), "midleft", False)
        self.text(f"Gremlins {world.remaining_gremlins}", f.normal, Color.GREMLIN, (520, cy), "midleft", False)
        if world.is_frozen:
            self.text(f"Firewall {world.freeze_timer:.0f}s", f.small, Color.ICE, (680, cy), "midleft", False)
        elif world.is_shielded:
            self.text(f"Guard {world.shield_timer:.0f}s", f.small, Color.ICE, (680, cy), "midleft", False)
        self.text(f"Best {best}", f.normal, Color.GREY, (WIDTH - 16, cy), "midright", False)
        if muted:
            self.text("muted", f.small, Color.GREY, (WIDTH - 140, cy), "midright", False)

    def draw_panel(self, lines: list[str]) -> None:
        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 150))
        self.surface.blit(shade, (0, 0))
        panel = pygame.Rect(0, 0, 520, 60 + 46 * len(lines))
        panel.center = (WIDTH // 2, HEIGHT // 2)
        pygame.draw.rect(self.surface, Color.HUD_BG, panel, border_radius=12)
        pygame.draw.rect(self.surface, Color.PANEL_BORDER, panel, 2, border_radius=12)
        y = panel.y + 50
        for i, line in enumerate(lines):
            font, color = (self.fonts.medium, Color.YELLOW) if i == 0 else (self.fonts.normal, Color.WHITE)
            self.text(line, font, color, (WIDTH // 2, y))
            y += 46

    def draw_cursor(self, pos: Point, dragging_kind: int | None, swatting: bool) -> None:
        if dragging_kind is not None:
            self.draw_disk_icon(dragging_kind, pos)
            return
        scale = sprites.CURSOR_SCALE
        hx, hy = (c * scale + scale // 2 for c in sprites.CURSOR_HOTSPOT)
        x, y = pos
        if swatting:
            self.surface.blit(self.art["cursor_hit"], (x - hx + 2, y - hy + 2))
        else:
            self.surface.blit(self.art["cursor"], (x - hx, y - hy))
