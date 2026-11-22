#!/usr/bin/env bash
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

# Build, launch-test and package a standalone executable for the current OS.
#
# Usage:  tools/build_executable.sh <target>     e.g. macos-intel, linux-x64
# Needs:  pip install ".[build]"   (Linux also needs binutils for PyInstaller)
# Output: out/PatchPanic-<version>-<target>.zip  (.tar.gz on Linux)
#
# Used by .github/workflows/build.yml, and works the same locally.

set -euo pipefail

TARGET="${1:?usage: tools/build_executable.sh <target, e.g. macos-intel>}"
PYTHON="${PYTHON:-python}"
cd "$(dirname "$0")/.."

VERSION=$("$PYTHON" -c "import patch_panic; print(patch_panic.__version__)")
PKG="PatchPanic-$VERSION-$TARGET"

case "$(uname -s)" in
  Darwin)                # .app bundle (PyInstaller needs --onedir for that)
    MODE=--onedir; APP=dist/PatchPanic.app; EXE=$APP/Contents/MacOS/PatchPanic
    ICON_ARGS="--icon build/icon.png" ;;
  MINGW*|MSYS*|CYGWIN*)  # Windows (Git Bash)
    MODE=--onefile; APP=dist/PatchPanic.exe; EXE=$APP
    ICON_ARGS="--icon build/icon.png" ;;
  *)                     # Linux: executables don't embed icons
    MODE=--onefile; APP=dist/PatchPanic; EXE=$APP
    ICON_ARGS="" ;;
esac

echo "==> Building $PKG"
rm -rf build dist stage "out/$PKG".*
"$PYTHON" tools/make_icon.py build/icon.png
# shellcheck disable=SC2086  # ICON_ARGS is intentionally word-split
"$PYTHON" -m PyInstaller --noconfirm --clean --windowed $MODE \
  --name PatchPanic $ICON_ARGS \
  --add-data "patch_panic/assets:patch_panic/assets" \
  --log-level WARN \
  run_game.py

echo "==> Launch test"
"$PYTHON" tools/smoke_test.py "$EXE" 10

echo "==> Packaging"
mkdir -p "stage/$PKG" out
cp -R "$APP" README.md LICENSE "stage/$PKG/"
case "$(uname -s)" in
  Darwin)               ditto -c -k --norsrc --keepParent "stage/$PKG" "out/$PKG.zip" ;;
  MINGW*|MSYS*|CYGWIN*) (cd stage && 7z a -tzip "../out/$PKG.zip" "$PKG" > /dev/null) ;;
  *)                    tar -czf "out/$PKG.tar.gz" -C stage "$PKG" ;;
esac
rm -rf stage
ls -la out/"$PKG".*
