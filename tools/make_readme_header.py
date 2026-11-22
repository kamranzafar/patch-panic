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

"""Render the README ASCII-art header as a coloured SVG.

Usage: python tools/make_readme_header.py  (writes .github/header.svg)
Edit the art in TITLE/SCENE, colours in the constants below.
"""
import re
import sys
from xml.sax.saxutils import escape

TITLE = [  # figlet -f big "PATCH PANIC"
    r' _____     _______ _____ _    _   _____        _   _ _____ _____',
    r'|  __ \ /\|__   __/ ____| |  | | |  __ \ /\   | \ | |_   _/ ____|',
    r'| |__) /  \  | | | |    | |__| | | |__) /  \  |  \| | | || |',
    r'|  ___/ /\ \ | | | |    |  __  | |  ___/ /\ \ | . ` | | || |',
    r'| |  / ____ \| | | |____| |  | | | |  / ____ \| |\  |_| || |____',
    r'|_| /_/    \_\_|  \_____|_|  |_| |_| /_/    \_\_| \_|_____\_____|',
]
SCENE = [
    r"      .-----------------.                 /\          /\ ",
    r"      |  .-----------.  |                /  \________/  \ ",
    r"      |  |  BloatOS  |  |               |    O      O    |",
    r"      |  |   (x_x)   |  |   ~*zzzt*~    |    \______/    |  \"just one quick",
    r"      |  | [#####  ] |  |  ===/\/\===   |                |   update...\"",
    r"      |  '-----------'  |                \______________/",
    r"      '-------..--------'                  /|        |\ ",
    r"         [===========]                    /_|        |_\ ",
]
SCENE = [l.replace('\\"', '"') for l in SCENE]
TAGLINE = "defend your workstations from bloatware gremlins"

GREY, GREEN, RED, YELLOW, PINK, WHITE, MUTED = (
    "#aab2c5", "#9bd23c", "#ff6b6b", "#ffd23f", "#ff5c9a", "#f4f4f8", "#8b93a7")

# column ranges of the scene: monitor | spark | gremlin | speech bubble
REGIONS = [(0, 26, GREY), (26, 39, YELLOW), (39, 57, PINK), (57, 200, WHITE)]
HIGHLIGHTS = [  # (regex, colour) applied inside the monitor region
    (r"BloatOS|\(x_x\)", GREEN),
    (r"#####", RED),
]
EYES = r"O(?=\s{6}O)|(?<=O\s{6})O"

FONT, CHAR_W, LINE_H, PAD_X, PAD_Y = 15, 0.62 * 15, 19, 28, 26


def spans(line):
    """Split a scene line into (text, colour) runs."""
    colours = []
    for i in range(len(line)):
        colours.append(next(c for start, end, c in REGIONS if start <= i < end))
    for pattern, colour in HIGHLIGHTS:
        for m in re.finditer(pattern, line[:26]):
            colours[m.start():m.end()] = [colour] * (m.end() - m.start())
    for m in re.finditer(EYES, line):
        colours[m.start()] = WHITE
    runs, cur, buf = [], None, ""
    for ch, col in zip(line, colours):
        if col != cur and buf:
            runs.append((buf, cur))
            buf = ""
        cur = col
        buf += ch
    if buf:
        runs.append((buf, cur))
    return runs


def main(out):
    lines = TITLE + [""] + SCENE + [""] + [TAGLINE]
    cols = max(len(l.rstrip()) for l in lines)
    width = round(cols * CHAR_W + 2 * PAD_X)
    height = round(len(lines) * LINE_H + 2 * PAD_Y)
    y0 = PAD_Y + LINE_H * 0.8
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
         f'viewBox="0 0 {width} {height}" role="img" aria-label="Patch Panic">',
         '<defs><linearGradient id="title" x1="0" y1="0" x2="1" y2="0">'
         '<stop offset="0" stop-color="#ffd23f"/><stop offset="0.55" stop-color="#ff8c42"/>'
         '<stop offset="1" stop-color="#ff5c9a"/></linearGradient>'
         '<style>'
         'text{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;'
         f'font-size:{FONT}px;white-space:pre}}'
         '.spark{animation:flicker 0.9s steps(2) infinite}'
         '@keyframes flicker{0%{opacity:1}50%{opacity:.35}100%{opacity:1}}'
         '</style></defs>',
         f'<rect width="{width}" height="{height}" rx="14" fill="#141821"/>',
         f'<rect x="1" y="1" width="{width-2}" height="{height-2}" rx="13" fill="none" stroke="#2c3344"/>']
    for i, line in enumerate(lines):
        y = round(y0 + i * LINE_H, 1)
        block = TITLE if i < len(TITLE) else SCENE if line in SCENE else [line]
        block_cols = max(len(l.rstrip()) for l in block) if line else 0
        x = round(PAD_X + (cols - block_cols) / 2 * CHAR_W, 1)
        attrs = f'x="{x}" y="{y}" xml:space="preserve"'
        if i < len(TITLE):
            o.append(f'<text {attrs} fill="url(#title)" font-weight="bold">{escape(line)}</text>')
        elif line == TAGLINE:
            o.append(f'<text {attrs} fill="{MUTED}" font-style="italic">{escape(line)}</text>')
        elif line:
            parts = []
            for text, colour in spans(line):
                cls = ' class="spark"' if colour == YELLOW and text.strip() else ""
                parts.append(f'<tspan fill="{colour}"{cls}>{escape(text)}</tspan>')
            o.append(f'<text {attrs}>{"".join(parts)}</text>')
    o.append("</svg>")
    open(out, "w").write("\n".join(o) + "\n")
    print(f"wrote {out} ({width}x{height})")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".github/header.svg")
