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
import math
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


# Other gremlin kinds reuse the same pixels with their own colours.
VARIANT_PALS = {
    "sprinter": {"r": (60, 190, 220), "R": (25, 115, 150), "p": (160, 235, 250), "m": (15, 60, 85),
                 "f": (15, 70, 95)},
    "armored": {"r": (150, 156, 172), "R": (92, 98, 114), "p": (215, 220, 232), "m": (60, 64, 76),
                "f": (55, 58, 70), "h": (255, 214, 70)},
    "splitter": {"r": (240, 175, 50), "R": (170, 110, 20), "p": (255, 225, 130), "m": (110, 60, 10),
                 "f": (100, 60, 15)},
}
ARMOR_CRACKS = [(8, 3), (9, 4), (10, 4), (10, 5), (12, 9), (13, 10)]  # (x, y) pixels in a 17-wide frame


def cracked(rows):
    grid = [list(r) for r in rows]
    for x, y in ARMOR_CRACKS:
        if grid[y][x] != ".":
            grid[y][x] = "k"
    return ["".join(r) for r in grid]


def gremlin_set(prefix, palette, transform=lambda rows: rows):
    """All animation frames for one gremlin kind, named `{prefix}_{pose}{n}`."""
    frames = {
        "walk0": gremlin_frame("stride"), "walk1": gremlin_frame("close"),
        "type0": gremlin_frame("stand", "type", 8), "type1": gremlin_frame("stand", "type", 9),
        "carry0": gremlin_frame("stride", "carry"), "carry1": gremlin_frame("close", "carry"),
    }
    sprites = {f"{prefix}_{name}": grid_to_surface(transform(rows), palette) for name, rows in frames.items()}
    sprites[f"{prefix}_squashed"] = grid_to_surface(GREMLIN_SQUASHED, palette)
    return sprites


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
# Colourblind glyphs (5 x 5, outlined): one shape per OS, echoing its logo
# --------------------------------------------------------------------------
OS_GLYPHS = [
    [".www.", "w...w", "w...w", "w...w", ".www."],   # Orbix: ring
    ["..w..", ".w.w.", ".w.w.", "w...w", "wwwww"],   # Delta: triangle
    ["wwwww", "w...w", "w...w", "w...w", "wwwww"],   # Cubix: square
    ["..w..", ".w.w.", "w...w", ".w.w.", "..w.."],   # Prism: diamond
]
GLYPH_PAL = {"w": (250, 250, 255), "k": (12, 12, 18)}

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
    s.update(gremlin_set("gremlin", GREMLIN_PAL))
    for prefix, colours in VARIANT_PALS.items():
        s.update(gremlin_set(prefix, {**GREMLIN_PAL, **colours}))
    s.update(gremlin_set("armored_cracked", {**GREMLIN_PAL, **VARIANT_PALS["armored"]}, cracked))
    for i, color in enumerate(OS_COLORS):
        s[f"computer_{i}"] = grid_to_surface(COMPUTER, {**COMPUTER_PAL, "s": color})
        s[f"logo_{i}"] = grid_to_surface(LOGOS[i], {"c": color, "C": shade(color, 0.6), "w": (250, 250, 255)})
        s[f"disk_{i}"] = grid_to_surface(DISK, {**DISK_PAL, "s": color})
        s[f"glyph_{i}"] = grid_to_surface(outlined(OS_GLYPHS[i], "k"), GLYPH_PAL)
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


# --------------------------------------------------------------------------
# App icon (24 x 24): the gremlin on an arcade sunburst. One subject, so it
# still reads at 16-32 px.
# --------------------------------------------------------------------------
ICON_SIZE = 24
ICON_CORNER = 5
ICON_WINDOW_SCALE = 5                      # window/taskbar icon: 120 x 120
ICON_RAYS = ((70, 32, 112), (46, 21, 80))  # alternating sunburst sectors (subtle)
ICON_EDGE = (16, 10, 30)                   # rays fade to this towards the rim
ICON_BORDER = (255, 140, 66)


def icon_mask():
    """Rows of the rounded-square silhouette: '#' inside, 'o' on the border."""
    n, r = ICON_SIZE, ICON_CORNER

    def inside(x, y):
        cx = min(max(x, r - 0.5), n - r - 0.5)
        cy = min(max(y, r - 0.5), n - r - 0.5)
        return (x - cx) ** 2 + (y - cy) ** 2 <= r * r

    rows = []
    for y in range(n):
        row = ""
        for x in range(n):
            if not inside(x, y):
                row += "."
            elif not all(inside(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                row += "o"
            else:
                row += "#"
        rows.append(row)
    return rows


def build_icon():
    """Return the 1x icon surface (scale it with nearest-neighbour)."""
    n = ICON_SIZE
    icon = pygame.Surface((n, n), pygame.SRCALPHA)
    cx, cy = n / 2, n / 2
    for y, row in enumerate(icon_mask()):
        for x, ch in enumerate(row):
            if ch == "o":
                icon.set_at((x, y), ICON_BORDER)
            elif ch == "#":
                angle = math.atan2(y + 0.5 - cy, x + 0.5 - cx)
                ray = ICON_RAYS[int((angle + math.pi) / (math.tau / 12)) % 2]
                fade = min(1.0, math.hypot(x + 0.5 - cx, y + 0.5 - cy) / (n * 0.75)) ** 1.5
                icon.set_at((x, y), tuple(int(c + (e - c) * fade) for c, e in zip(ray, ICON_EDGE)))

    gremlin = grid_to_surface(gremlin_frame("stand"), GREMLIN_PAL)
    icon.blit(gremlin, ((n - gremlin.get_width()) // 2, (n - gremlin.get_height()) // 2 + 1))
    return icon


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
