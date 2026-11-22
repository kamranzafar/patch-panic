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

"""Render the GitHub social preview image (1280x640) from the game's sprites.

Usage: python tools/make_social_preview.py  (writes .github/social-preview.png)
Then upload it on GitHub: Settings -> General -> Social preview -> Edit.
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pygame  # noqa: E402

from patch_panic import sprites  # noqa: E402
from patch_panic.config import OS_COLORS  # noqa: E402

W, H = 1280, 640
S = 4  # sprite scale
OUT = Path(__file__).resolve().parents[1] / ".github" / "social-preview.png"

TITLE = "PATCH PANIC"
PIXEL_FONT = {  # 5x7 bitmap letters
    "P": ["####.", "#...#", "#...#", "####.", "#....", "#....", "#...."],
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "T": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    "C": [".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."],
    "H": ["#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "N": ["#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"],
    "I": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"],
    " ": ["..."] * 7,
}
GRADIENT = [(255, 210, 63), (255, 140, 66), (255, 92, 154)]
TAGLINE = "Defend your workstations from bloatware gremlins"
FOOTER = "Python  ·  pygame-ce  ·  GPL-3.0  ·  github.com/kamranzafar/patch-panic"


def big(art, name):
    img = art[name]
    return pygame.transform.scale(img, (img.get_width() * S, img.get_height() * S))


def lerp(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def gradient_color(t):
    if t < 0.5:
        return lerp(GRADIENT[0], GRADIENT[1], t * 2)
    return lerp(GRADIENT[1], GRADIENT[2], (t - 0.5) * 2)


def draw_background(surf, art):
    tile = art["floor"]
    tile = pygame.transform.scale(tile, (tile.get_width() * 3, tile.get_height() * 3))
    for y in range(0, H, tile.get_height()):
        for x in range(0, W, tile.get_width()):
            surf.blit(tile, (x, y))
    shade = pygame.Surface((W, H), pygame.SRCALPHA)
    for y in range(H):  # darker at the top so the title pops
        alpha = int(170 * (1 - y / H) + 60)
        pygame.draw.line(shade, (8, 10, 16, alpha), (0, y), (W, y))
    surf.blit(shade, (0, 0))


def title_pixels(text):
    """(col, row) of every lit pixel, plus the total size in pixels."""
    pixels, col = [], 0
    for ch in text:
        glyph = PIXEL_FONT[ch]
        for row, line in enumerate(glyph):
            pixels += [(col + x, row) for x, c in enumerate(line) if c == "#"]
        col += len(glyph[0]) + 1
    return pixels, col - 1, 7


def draw_title(surf, top, block=14):
    """Chunky pixel-art title with a gradient, highlight and drop shadow."""
    pixels, cols, rows = title_pixels(TITLE)
    left = (W - cols * block) // 2
    depth = block // 2
    for x, y in pixels:  # extruded shadow
        surf.fill((60, 14, 40), (left + x * block + depth, top + y * block + depth, block, block))
    for x, y in pixels:
        color = gradient_color(x / cols)
        rect = pygame.Rect(left + x * block, top + y * block, block, block)
        surf.fill(color, rect)
        surf.fill(lerp(color, (255, 255, 255), 0.45), (rect.x, rect.y, block, 3))     # highlight
        surf.fill(lerp(color, (0, 0, 0), 0.25), (rect.x, rect.bottom - 3, block, 3))  # shade
    return top + rows * block + depth


def text_center(surf, text, size, color, y, bold=False, italic=False):
    font = pygame.font.Font(None, size)
    font.set_bold(bold)
    font.set_italic(italic)
    img = font.render(text, True, color)
    surf.blit(font.render(text, True, (0, 0, 0)), img.get_rect(center=(W // 2 + 2, y + 2)))
    surf.blit(img, img.get_rect(center=(W // 2, y)))


def draw_computer(surf, art, cx, top, native, screen):
    """screen: 'os', 'bloat', 'fried' or 'install'."""
    comp = big(art, f"computer_{native}")
    left = cx - comp.get_width() // 2
    pygame.draw.ellipse(surf, (14, 16, 22), (left - 4, top + 84, comp.get_width() + 8, 22))
    surf.blit(comp, (left, top))
    scr = pygame.Rect(left + 3 * S, top + 2 * S, 18 * S, 11 * S)
    if screen == "bloat":
        surf.fill((50, 70, 15), scr)
        logo = big(art, "logo_bloat")
    elif screen == "fried":
        surf.blit(pygame.transform.scale(art["static0"], scr.size), scr)
        logo = big(art, "bolt")
    else:
        r, g, b = OS_COLORS[native]
        surf.fill((r // 5, g // 5, b // 5), scr)
        logo = big(art, f"logo_{native}")
    surf.blit(logo, logo.get_rect(center=scr.center))
    if screen == "install":
        bar = pygame.Rect(scr.x + 4, scr.bottom - 8, scr.w - 8, 5)
        surf.fill((10, 10, 14), bar)
        surf.fill((235, 70, 70), (bar.x, bar.y, int(bar.w * 0.7), bar.h))
    return left + comp.get_width() // 2, top + 22 * S  # cable anchor


def blit_feet(surf, img, cx, feet_y):
    pygame.draw.ellipse(surf, (14, 16, 22), (cx - 22, feet_y - 6, 44, 12))
    surf.blit(img, (cx - img.get_width() // 2, feet_y - img.get_height()))


def main():
    pygame.init()
    pygame.display.set_mode((1, 1))
    art = sprites.build_all()
    surf = pygame.Surface((W, H))

    draw_background(surf, art)
    bottom = draw_title(surf, 64)
    text_center(surf, TAGLINE, 46, (236, 238, 245), bottom + 46, bold=True)

    # --- scene ---------------------------------------------------------------
    top = 318
    xs = [190, 470, 790, 1090]
    states = [(0, "os"), (1, "install"), (2, "bloat"), (3, "fried")]
    anchors = [draw_computer(pygame.Surface((1, 1)), art, x, top, n, s) for x, (n, s) in zip(xs, states)]
    for a, b in zip(anchors, anchors[1:]):  # cables first, under everything
        pygame.draw.line(surf, (70, 80, 104), a, b, 4)
    spark_at = (anchors[0][0] + (anchors[1][0] - anchors[0][0]) * 0.55, anchors[0][1])
    pygame.draw.line(surf, (120, 108, 45), spark_at, anchors[1], 5)
    for x, (native, screen) in zip(xs, states):
        draw_computer(surf, art, x, top, native, screen)

    spark = big(art, "spark0")
    surf.blit(spark, spark.get_rect(center=(round(spark_at[0]), round(spark_at[1]))))

    # gremlin typing at the computer being infected (faces left, towards it)
    typing = pygame.transform.flip(big(art, "gremlin_type0"), True, False)
    blit_feet(surf, typing, xs[1] + 82, top + 96)

    # gremlin running off with the stolen Cubix disk
    carrier = big(art, "gremlin_carry0")
    feet = top + 200
    blit_feet(surf, carrier, xs[2] + 120, feet)
    disk = big(art, "disk_2")
    surf.blit(disk, disk.get_rect(midbottom=(xs[2] + 120, feet - carrier.get_height() + 6)))

    # ejected disk from the fried machine, and the golden patch flying past
    surf.blit(big(art, "disk_3"), (xs[3] - 110, top + 150))
    star = big(art, "star1")
    glow = pygame.Surface((150, 150), pygame.SRCALPHA)
    pygame.draw.circle(glow, (255, 214, 70, 70), (75, 75), 60)
    pygame.draw.circle(glow, (255, 214, 70, 50), (75, 75), 40)
    star_c = (330, top + 175)
    surf.blit(glow, glow.get_rect(center=star_c))
    surf.blit(star, star.get_rect(center=star_c))

    text_center(surf, FOOTER, 28, (150, 158, 178), H - 26)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(surf, str(OUT))
    print(f"wrote {OUT} ({W}x{H}, {OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
