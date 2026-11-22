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

"""Pixel-art sprites for Patch Panic.

Every sprite is authored here as a character grid + palette, at 1x size.
Run `python -m patch_panic.sprites` to export them as PNGs into assets/sprites/.

At runtime `load_sprites()` builds every sprite from these grids, but if a PNG
with the same name exists in assets/sprites/ it is used instead -- so artists
can replace any sprite by editing/dropping in a PNG (keep the 1x pixel size;
sprites are scaled up with nearest-neighbour filtering).
"""
import random
from pathlib import Path

import pygame

from .config import OS_COLORS

ASSET_DIR = Path(__file__).resolve().parent / "assets" / "sprites"
SCALE = 3
CURSOR_SCALE = 3



def shade(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c)


# --------------------------------------------------------------------------
# Gremlin (17 x 16): body 13 wide with 2px padding each side for arms
# --------------------------------------------------------------------------
GREMLIN_PAL = {
    "k": (24, 14, 30), "r": (205, 62, 112), "R": (140, 34, 78), "p": (245, 120, 160),
    "h": (250, 222, 150), "w": (245, 245, 250), "b": (15, 10, 20), "m": (95, 20, 50),
    "f": (70, 20, 45),
}
GREMLIN_BODY = [
    ".k.........k.",
    "khk.......khk",
    "khhkkkkkkkhhk",
    ".kkpprrrrrkk.",
    ".kpprrrrrrrk.",
    "kprwwwrwwwrrk",
    "krrwwbrwwbrrk",
    "krrwwbrwwbrrk",
    "krrrrrrrrrrRk",
    "krrmrrrrrmrRk",
    "kRrrmmmmmrRRk",
    ".kRrrrrrrrRk.",
    "..kRRRRRRRk..",
]
GREMLIN_LEGS = {
    "stand": ["...kfk.kfk...", "...kfk.kfk...", "...kffkkffk.."],
    "stride": ["...kfk.kfk...", "..kfk...kfk..", ".kffk...kffk."],
    "close": ["....kfkfk....", "....kfkfk....", "....kffffk..."],
}
GREMLIN_SQUASHED = [
    "...kkkkkkkkkkk...",
    ".kkrrrrrrrrrrrkk.",
    "krrrbrrrrrrrbrrrk",
    "kRRrrrrrrrrrrrRRk",
    ".kkkkkkkkkkkkkkk.",
]


def gremlin_frame(legs, arms=None, arm_row=8):
    grid = [list(".." + row + "..") for row in GREMLIN_BODY + GREMLIN_LEGS[legs]]
    if arms == "type":  # arm reaching out to the keyboard (sprite faces right)
        grid[arm_row][15:17] = list("kk")
        grid[arm_row + 1][14:17] = list("rrk")
        grid[arm_row + 2][15:17] = list("kk")
    elif arms == "carry":  # both arms raised to hold a disk overhead
        for y in range(1, 7):
            grid[y][0], grid[y][1] = "k", "r"
            grid[y][16], grid[y][15] = "k", "r"
        grid[0][1] = grid[0][15] = "k"
    return ["".join(r) for r in grid]


# --------------------------------------------------------------------------
# Computer (24 x 24). Screen area: cols 3-20, rows 2-12. 's' = OS stripe colour
# --------------------------------------------------------------------------
COMPUTER_PAL = {
    "k": (22, 24, 32), "l": (236, 238, 245), "g": (196, 200, 210), "G": (140, 145, 158),
    "d": (16, 18, 24), "n": (110, 115, 128),
}
SCREEN_ROW = "klgddddddddddddddddddgGk"
COMPUTER = (
    [".kkkkkkkkkkkkkkkkkkkkkk.",
     "klllllllllllllllllllllgk"]
    + [SCREEN_ROW] * 11
    + ["klggggggggggggggggggggGk",
       "klgssssssssssssssssssgGk",
       "kGGGGGGGGGGGGGGGGGGGGGGk",
       ".kkkkkkkkkkkkkkkkkkkkkk.",
       "..........kGGk..........",
       ".........kGGGGk.........",
       "...kkkkkkkkkkkkkkkkkk...",
       "..kllllllllllllllllllk..",
       "..klnlnlnlnlnlnlnlnllk..",
       "..kggggggggggggggggggk..",
       "...kkkkkkkkkkkkkkkkkk..."]
)
SCREEN_OFFSET = (3, 2)   # in 1x pixels
SCREEN_SIZE = (18, 11)

# --------------------------------------------------------------------------
# Screen logos (9 x 9). 'c' main colour, 'C' shadow, 'w' white
# --------------------------------------------------------------------------
LOGOS = [
    ["...ccc...", ".ccccccc.", ".ccwwwcc.", "ccwcccwcc", "ccwcccwcc",
     "ccwcccwcc", ".ccwwwcc.", ".cccccCC.", "...CCC..."],          # Orbix
    ["....c....", "...ccc...", "...ccc...", "..ccwcc..", "..cwwwc..",
     ".ccwwwcc.", ".cwwwwwc.", "ccccccccc", "CCCCCCCCC"],          # Delta
    ["ccccccccc", "ccccccccc", "ccwwwwwcc", "ccwcccwcc", "ccwcccwcc",
     "ccwcccwcc", "ccwwwwwcc", "ccccccccc", "CCCCCCCCC"],          # Cubix
    ["....c....", "...ccc...", "..ccccc..", ".ccccccc.", "cwwwwwwwc",
     ".ccccccc.", "..cCCCc..", "...CCC...", "....C...."],          # Prism
]
LOGO_BLOAT = ["..ggggg..", ".ggggggg.", "gkgkgkgkg", "ggkgggkgg", "gkgkgkgkg",
              "ggggggggg", "ggkgkgkgg", ".ggkgkgg.", "..GGGGG.."]
BLOAT_PAL = {"g": (140, 195, 45), "G": (70, 110, 20), "k": (15, 20, 5)}
BOLT = ["..yy.", ".yy..", ".yy..", "yyyyy", "..yy.", ".yy..", ".y...", "y...."]
NO_OS = [".rrr.", "r...r", "....r", "..rr.", "..r..", ".....", "..r.."]

# --------------------------------------------------------------------------
# OS disk (11 x 11). 's' = OS colour
# --------------------------------------------------------------------------
DISK = [
    "kkkkkkkkkk.",
    "kbbmmmmMbbk",
    "kbbmMmmmbbk",
    "kbbmmmmmbbk",
    "kbbbbbbbbbk",
    "kbsssssssbk",
    "kbslllllsbk",
    "kbsssssssbk",
    "kbslllllsbk",
    "kbsssssssbk",
    "kkkkkkkkkkk",
]
DISK_PAL = {"k": (18, 18, 26), "b": (48, 52, 66), "m": (175, 180, 190), "M": (110, 115, 128),
            "l": (245, 245, 250)}

# --------------------------------------------------------------------------
# Spark (9 x 9), power-up star (13 x 13 + outline), cursor
# --------------------------------------------------------------------------
SPARK_PAL = {"y": (255, 210, 60), "o": (245, 140, 30), "w": (255, 255, 215)}
SPARKS = [
    ["....y....", ".y..y..y.", "..yyoyy..", "..yowoy..", "yyowwwoyy",
     "..yowoy..", "..yyoyy..", ".y..y..y.", "....y...."],
    ["y.......y", ".y.....y.", "..yyoyy..", "..ywwwy..", "..owwwo..",
     "..ywwwy..", "..yyoyy..", ".y.....y.", "y.......y"],
]
STAR = [
    "......Y......",
    ".....YYY.....",
    ".....YYY.....",
    "....YYYYY....",
    "YYYYYYwYYYYYY",
    ".YYYYYwYYYYY.",
    "..YYwwwwwYY..",
    "...YYYwYYY...",
    "...YYYwYYY...",
    "..YYYYYYYYY..",
    "..YYYO.OYYY..",
    ".YYO.....OYY.",
    ".YO.......OY.",
]
STAR_PAL = {"Y": (255, 214, 70), "O": (200, 135, 25), "w": (255, 255, 240), "K": (120, 70, 10)}
CURSOR = [
    "RRRRRRRRR...",
    "RrRrRrRrR...",
    "RRRRRRRRR...",
    "RrRrRrRrR...",
    "RRRRRRRRR...",
    "RrRrRrRrR...",
    "RRRRRRRRR...",
    "RrRrRrRrR...",
    "RRRRRRRRR...",
    ".......Hh...",
    "........Hh..",
    ".........Hh.",
    "..........Hh",
]
CURSOR_PAL = {"R": (150, 40, 30), "r": (240, 95, 60), "H": (80, 50, 25), "h": (140, 95, 50)}
CURSOR_HIT_PAL = {**CURSOR_PAL, "r": (255, 220, 150)}
CURSOR_HOTSPOT = (4, 4)  # 1x pixels: centre of the swatter mesh


# --------------------------------------------------------------------------
# Builders
# --------------------------------------------------------------------------
def grid_to_surface(rows, palette):
    w = len(rows[0])
    assert all(len(r) == w for r in rows), f"ragged sprite grid: {[len(r) for r in rows]}"
    surf = pygame.Surface((w, len(rows)), pygame.SRCALPHA)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch != ".":
                surf.set_at((x, y), palette[ch])
    return surf


def outlined(rows, ch):
    """Pad a grid by 1px and draw an outline of `ch` around opaque pixels."""
    h, w = len(rows), len(rows[0])
    grid = [["."] * (w + 2) for _ in range(h + 2)]
    for y in range(h):
        for x in range(w):
            if rows[y][x] != ".":
                grid[y + 1][x + 1] = rows[y][x]
    for y in range(h + 2):
        for x in range(w + 2):
            if grid[y][x] == "." and any(
                    0 <= y + dy < h + 2 and 0 <= x + dx < w + 2 and grid[y + dy][x + dx] not in (".", ch)
                    for dy in (-1, 0, 1) for dx in (-1, 0, 1)):
                grid[y][x] = ch
    return ["".join(r) for r in grid]


def static_frame(seed):
    rnd = random.Random(seed)
    w, h = SCREEN_SIZE
    return ["".join(rnd.choice("aabbc") for _ in range(w)) for _ in range(h)]


def floor_tile():
    rows = []
    for y in range(16):
        row = ""
        for x in range(16):
            if x == 0 or y == 0:
                row += "L"
            elif (x, y) in ((3, 3), (12, 3), (3, 12), (12, 12)):
                row += "r"
            elif x == 1 or y == 1:
                row += "b"
            else:
                row += "a"
        rows.append(row)
    return rows


def build_all():
    """Return {name: 1x Surface} for every sprite."""
    s = {}
    s["gremlin_walk0"] = grid_to_surface(gremlin_frame("stride"), GREMLIN_PAL)
    s["gremlin_walk1"] = grid_to_surface(gremlin_frame("close"), GREMLIN_PAL)
    s["gremlin_type0"] = grid_to_surface(gremlin_frame("stand", "type", 8), GREMLIN_PAL)
    s["gremlin_type1"] = grid_to_surface(gremlin_frame("stand", "type", 9), GREMLIN_PAL)
    s["gremlin_carry0"] = grid_to_surface(gremlin_frame("stride", "carry"), GREMLIN_PAL)
    s["gremlin_carry1"] = grid_to_surface(gremlin_frame("close", "carry"), GREMLIN_PAL)
    s["gremlin_squashed"] = grid_to_surface(GREMLIN_SQUASHED, GREMLIN_PAL)
    for i, color in enumerate(OS_COLORS):
        s[f"computer_{i}"] = grid_to_surface(COMPUTER, {**COMPUTER_PAL, "s": color})
        s[f"logo_{i}"] = grid_to_surface(LOGOS[i], {"c": color, "C": shade(color, 0.6), "w": (250, 250, 255)})
        s[f"disk_{i}"] = grid_to_surface(DISK, {**DISK_PAL, "s": color})
    s["logo_bloat"] = grid_to_surface(LOGO_BLOAT, BLOAT_PAL)
    static_pal = {"a": (18, 18, 26), "b": (45, 45, 58), "c": (120, 120, 140)}
    s["static0"] = grid_to_surface(static_frame(1), static_pal)
    s["static1"] = grid_to_surface(static_frame(2), static_pal)
    s["bolt"] = grid_to_surface(BOLT, {"y": (255, 210, 60)})
    s["no_os"] = grid_to_surface(NO_OS, {"r": (235, 70, 70)})
    s["spark0"] = grid_to_surface(SPARKS[0], SPARK_PAL)
    s["spark1"] = grid_to_surface(SPARKS[1], SPARK_PAL)
    star = outlined(STAR, "K")
    s["star0"] = grid_to_surface(star, STAR_PAL)
    twinkle = [list(r) for r in star]
    for x, y in ((1, 1), (13, 1), (2, 13), (13, 12)):
        twinkle[y][x] = "w"
    s["star1"] = grid_to_surface(["".join(r) for r in twinkle], STAR_PAL)
    s["cursor"] = grid_to_surface(CURSOR, CURSOR_PAL)
    s["cursor_hit"] = grid_to_surface(CURSOR, CURSOR_HIT_PAL)
    s["floor"] = grid_to_surface(floor_tile(), {"L": (24, 27, 38), "b": (40, 46, 62),
                                                "a": (33, 38, 52), "r": (58, 64, 84)})
    return s


def scale(surf, factor):
    return pygame.transform.scale(surf, (surf.get_width() * factor, surf.get_height() * factor))


def load_sprites(asset_dir=ASSET_DIR):
    """Build all sprites (PNG overrides win) and return them scaled for the game."""
    sprites = {}
    for name, surf in build_all().items():
        path = asset_dir / f"{name}.png"
        if path.exists():
            try:
                surf = pygame.image.load(str(path)).convert_alpha()
            except pygame.error:
                pass
        sprites[name] = scale(surf, CURSOR_SCALE if name.startswith("cursor") else SCALE)
    return sprites


def export(asset_dir=ASSET_DIR):
    asset_dir.mkdir(parents=True, exist_ok=True)
    for name, surf in build_all().items():
        pygame.image.save(surf, str(asset_dir / f"{name}.png"))
    return asset_dir


if __name__ == "__main__":
    pygame.init()
    out = export()
    print(f"Exported {len(build_all())} sprites to {out}")
    # also write a 4x contact sheet for previewing
    sheet_items = list(build_all().items())
    pad, sc = 8, 4
    w = sum(s.get_width() * sc + pad for _, s in sheet_items) + pad
    h = max(s.get_height() * sc for _, s in sheet_items) + 2 * pad
    sheet = pygame.Surface((w, h))
    sheet.fill((40, 44, 58))
    x = pad
    for _, s in sheet_items:
        sheet.blit(scale(s, sc), (x, pad))
        x += s.get_width() * sc + pad
    sheet_path = out.parent / "contact_sheet.png"
    pygame.image.save(sheet, str(sheet_path))
    print(f"Contact sheet: {sheet_path}")
