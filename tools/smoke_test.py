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

"""Check that a built executable starts and keeps running.

Usage: python tools/smoke_test.py path/to/executable [seconds]

Runs the game headless (no window, no audio). Passes if the process is still
alive after `seconds`; fails, printing its output, if it exits early.
"""
import os
import subprocess
import sys


def main() -> int:
    exe = sys.argv[1]
    seconds = float(sys.argv[2]) if len(sys.argv) > 2 else 8
    env = {**os.environ, "SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy"}
    proc = subprocess.Popen([exe], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        proc.wait(timeout=seconds)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        print(f"OK: {exe} ran for {seconds:g}s without exiting")
        return 0
    output = proc.stdout.read().decode(errors="replace")
    print(f"FAIL: {exe} exited early with code {proc.returncode}\n{output}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
