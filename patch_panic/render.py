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

"""All drawing. Reads game state; never changes it."""
from __future__ import annotations

import math
import random

import pygame

from . import sprites
from .config import (ATTENTION_RADIUS, BLOAT, DISK_BLINK_TIME, DYING_TIME, HEIGHT, HUD_HEIGHT, INSTALL_WARN_TIME,
                     OS_COLORS, WIDTH, Color, Gremlins)
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
        self._shake_layer = pygame.Surface((WIDTH, HEIGHT))
        self.colourblind = False  # stamp a shape on disks and computers (a player setting)

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
        strength = effects.shake_strength
        if strength <= 0:
            self._draw_world(world, effects, t)
            return
        screen, self.surface = self.surface, self._shake_layer
        try:
            self._draw_world(world, effects, t)
        finally:
            self.surface = screen
        offset = (round(math.sin(t * 91) * strength), round(math.cos(t * 67) * strength))
        screen.fill(Color.BLACK)
        screen.blit(self._shake_layer, offset)

    def _draw_world(self, world: World, effects: Effects, t: float) -> None:
        self.surface.blit(self._level_background(world), (0, 0))
        if world.is_shielded and (world.shield_timer > 2 or int(t * 6) % 2):
            for a, b in world.cables:
                pygame.draw.line(self.surface, Color.ICE, a.cable_anchor(), b.cable_anchor(), 3)
        for surge in world.surges:
            pygame.draw.line(self.surface, Color.SURGE_PATH, surge.pos, surge.dst.cable_anchor(), 4)
        for warning in world.surge_warnings:
            color = Color.SURGE if int(t * 16) % 2 else Color.SURGE_PATH
            pygame.draw.line(self.surface, color, warning.src.cable_anchor(), warning.dst.cable_anchor(), 4)

        # computers and live gremlins, back to front
        standing = world.computers + world.alive_gremlins
        for obj in sorted(standing, key=lambda o: (o.y, isinstance(o, Gremlin))):
            if isinstance(obj, Gremlin):
                self.draw_gremlin(obj, t)
            else:
                self.draw_computer(obj, t)
        for gremlin in world.alive_gremlins:
            if gremlin.state is GremlinState.INSTALL and gremlin.target is not None:
                self.draw_progress_ring(gremlin, gremlin.target.install, world.config.install_time, t)
        if world.dragging is not None:
            self.draw_snap_targets(world, world.dragging.kind, t)

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
        if self.colourblind:
            self.blit_center(self.art[f"glyph_{c.native}"], (x, y + 6))  # on the colour stripe

    def draw_progress_ring(self, g: Gremlin, progress: float, duration: float, t: float) -> None:
        """A ring around an installing gremlin that fills up, flashing red near the end."""
        progress = min(1.0, progress)
        center = (g.x, g.y + Gremlin.BODY_OFFSET_Y)
        rect = pygame.Rect(0, 0, 60, 60)
        rect.center = (round(center[0]), round(center[1]))
        warn = (1 - progress) * duration < INSTALL_WARN_TIME
        color = (Color.RED if int(t * 12) % 2 else Color.WHITE) if warn else Color.INSTALL_RING
        pygame.draw.circle(self.surface, Color.INSTALL_RING_BACK, rect.center, 30, 2)
        if progress > 0:
            top = math.pi / 2  # pygame arcs run anticlockwise, so clockwise fill ends at the top
            pygame.draw.arc(self.surface, color, rect, top - progress * math.tau, top, 4)

    def draw_snap_targets(self, world: World, kind: int, t: float) -> None:
        """Outline every computer that would accept the disk being dragged."""
        color = OS_COLORS[kind] if int(t * 4) % 2 else Color.SNAP_HIGHLIGHT
        for computer in world.computers:
            if computer.accepts(kind):
                pygame.draw.rect(self.surface, color, computer.rect.inflate(10, 10), 2, border_radius=8)

    @staticmethod
    def gremlin_prefix(g: Gremlin) -> str:
        if g.kind is Gremlins.ARMORED and g.is_damaged:
            return "armored_cracked"
        return g.kind.name

    def draw_gremlin(self, g: Gremlin, t: float) -> None:
        x, y = g.x, g.y
        prefix = self.gremlin_prefix(g)
        if g.state is GremlinState.DYING:
            image = self.art[f"{prefix}_squashed"]
            progress = min(1.0, g.timer / DYING_TIME)
            if progress > 0.5:
                image = image.copy()
                image.set_alpha(int(255 * (1 - progress) * 2))
            self.surface.blit(image, (x - image.get_width() / 2, y + 16 - image.get_height()))
            return
        pygame.draw.ellipse(self.surface, Color.SHADOW, (x - 16, y + 11, 32, 9))
        if g.state is GremlinState.INSTALL:
            name, bob = f"{prefix}_type{int(t * 10) % 2}", 0
        else:
            frame = int(t * 8 + g.phase) % 2
            pose = "carry" if g.carry is not None else "walk"
            name, bob = f"{prefix}_{pose}{frame}", (-3 if frame else 0)
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
        if self.colourblind:
            self.blit_center(self.art[f"glyph_{kind}"], (center[0], center[1] + 6))  # on the label

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
    def draw_hud(self, world: World, best: int, muted: bool, tags: tuple[str, ...] = ()) -> None:
        pygame.draw.rect(self.surface, Color.HUD_BG, (0, 0, WIDTH, HUD_HEIGHT))
        pygame.draw.line(self.surface, Color.HUD_LINE, (0, HUD_HEIGHT - 1), (WIDTH, HUD_HEIGHT - 1))
        clean, total = world.clean_count, len(world.computers)
        cy = HUD_HEIGHT // 2
        f = self.fonts
        self.text(f"Level {world.level}", f.normal, Color.WHITE, (16, cy), "midleft", False)
        self.text(f"Score {world.score}", f.normal, Color.YELLOW, (130, cy), "midleft", False)
        clean_text = f"Clean {clean}/{total}" + (" +" if world.safety else "")  # '+': safety net active
        self.text(clean_text, f.normal, Color.WHITE if clean >= world.required_clean else Color.RED,
                  (300, cy), "midleft", False)
        self.text(f"Gremlins {world.remaining_gremlins}", f.normal, Color.GREMLIN, (450, cy), "midleft", False)
        if world.combo > 1:
            self.text(f"x{world.combo}", f.normal, Color.COMBO, (600, cy), "midleft", False)
        status = self.powerup_status(world)
        if status:
            self.text(status, f.small, Color.ICE, (650, cy), "midleft", False)
        right = self.text(f"Best {best}", f.normal, Color.GREY, (WIDTH - 16, cy), "midright", False).left
        for tag in tags + (("muted",) if muted else ()):
            right = self.text(tag, f.small, Color.GREY, (right - 14, cy), "midright", False).left

    @staticmethod
    def powerup_status(world: World) -> str:
        """Short HUD text for whichever power-up is running."""
        if world.is_frozen:
            return f"Firewall {world.freeze_timer:.0f}s"
        if world.is_shielded:
            return f"Guard {world.shield_timer:.0f}s"
        if world.sweep_clicks:
            return f"Sweep x{world.sweep_clicks}"
        return ""

    def draw_button(self, rect: pygame.Rect, label: str, hot: bool, selected: bool = False) -> None:
        """A rounded menu button; `hot` when under the mouse, `selected` for the active tab."""
        fill = Color.BUTTON_HOT if hot else (Color.BUTTON_SELECTED if selected else Color.HUD_BG)
        pygame.draw.rect(self.surface, fill, rect, border_radius=10)
        border = Color.YELLOW if hot or selected else Color.PANEL_BORDER
        pygame.draw.rect(self.surface, border, rect, 2, border_radius=10)
        self.text(label, self.fonts.normal, Color.WHITE, rect.center)

    def draw_attention(self, pos: Point, t: float) -> None:
        """A pulsing ring and a bouncing arrow that point the player at `pos` (used by the tutorial)."""
        x, y = round(pos[0]), round(pos[1])
        pulse = math.sin(t * 8)
        pygame.draw.circle(self.surface, Color.YELLOW, (x, y), ATTENTION_RADIUS + round(4 * pulse), 3)
        tip = y - ATTENTION_RADIUS - 8 - round(5 * abs(pulse))
        arrow = [(x, tip), (x - 11, tip - 14), (x - 4, tip - 14), (x - 4, tip - 26), (x + 4, tip - 26),
                 (x + 4, tip - 14), (x + 11, tip - 14)]
        pygame.draw.polygon(self.surface, Color.YELLOW, arrow)
        pygame.draw.polygon(self.surface, Color.BLACK, arrow, 2)

    def draw_hint(self, text: str) -> None:
        """A persistent instruction box along the bottom of the play area."""
        image = self.fonts.normal.render(text, True, Color.WHITE)
        rect = image.get_rect(center=(WIDTH // 2, HEIGHT - 34))
        back = rect.inflate(32, 18)
        pygame.draw.rect(self.surface, Color.HUD_BG, back, border_radius=10)
        pygame.draw.rect(self.surface, Color.YELLOW, back, 2, border_radius=10)
        self.surface.blit(image, rect)

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
