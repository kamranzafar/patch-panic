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

"""Render the application icon (512x512 PNG) from the gremlin sprite.

Usage: python tools/make_icon.py [output.png]   (default: build/icon.png)
PyInstaller converts the PNG to .ico / .icns when Pillow is installed.
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pygame  # noqa: E402

from patch_panic import sprites  # noqa: E402

SIZE = 512


def main(out: Path) -> None:
    pygame.init()
    gremlin = sprites.build_all()["gremlin_walk0"]
    scale = (SIZE * 3 // 4) // max(gremlin.get_size())
    gremlin = pygame.transform.scale(gremlin, (gremlin.get_width() * scale, gremlin.get_height() * scale))

    icon = pygame.Surface((SIZE, SIZE), pygame.SRCALPHA)
    pygame.draw.rect(icon, (20, 24, 33), icon.get_rect(), border_radius=SIZE // 5)
    pygame.draw.rect(icon, (255, 140, 66), icon.get_rect(), width=SIZE // 32, border_radius=SIZE // 5)
    icon.blit(gremlin, gremlin.get_rect(center=(SIZE // 2, SIZE // 2 + SIZE // 32)))

    out.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(icon, str(out))
    print(f"wrote {out} ({SIZE}x{SIZE})")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("build/icon.png"))
