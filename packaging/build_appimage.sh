#!/usr/bin/env bash
# Build dist/TheHumanRace-<arch>.AppImage (Linux).
#
#   ./packaging/build_appimage.sh
#
# Needs: python3 with venv + pip, and internet access the first time
# (PyInstaller, pygame-ce and appimagetool are fetched into build/).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
BUILD="$ROOT/build/appimage"
DIST="$ROOT/dist"
ARCH="$(uname -m)"
APPDIR="$BUILD/TheHumanRace.AppDir"
VENV="$BUILD/venv"
TOOL="$BUILD/appimagetool-$ARCH.AppImage"
VERSION="$(PYGAME_HIDE_SUPPORT_PROMPT=1 python3 -c "import sys; sys.path.insert(0, '$ROOT'); import config; print(config.VERSION)" 2>/dev/null || echo 1.0)"

mkdir -p "$BUILD" "$DIST"

echo "==> Python build environment"
if [ ! -x "$VENV/bin/python" ]; then
    python3 -m venv "$VENV"
fi
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet "pygame-ce>=2.1" "pyinstaller>=6.0"

echo "==> Bundling with PyInstaller"
rm -rf "$BUILD/pyi" "$APPDIR"
"$VENV/bin/pyinstaller" "$ROOT/main.py" \
    --name the-human-race \
    --onedir --windowed --noconfirm --clean \
    --distpath "$BUILD/pyi/dist" --workpath "$BUILD/pyi/work" --specpath "$BUILD/pyi" \
    --paths "$ROOT" \
    --hidden-import scenes.intro --hidden-import scenes.title --hidden-import scenes.howto \
    --hidden-import scenes.highscore_view --hidden-import scenes.settings_menu \
    --hidden-import scenes.controls_menu --hidden-import scenes.gameplay --hidden-import scenes.pause \
    --hidden-import scenes.gameover --hidden-import scenes.sector_clear --hidden-import scenes.ending \
    --hidden-import pygame._sdl2.controller \
    --log-level WARN

echo "==> Assembling AppDir"
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/share/applications" "$APPDIR/usr/share/icons/hicolor/256x256/apps"
cp -a "$BUILD/pyi/dist/the-human-race/." "$APPDIR/usr/bin/"
SDL_VIDEODRIVER=dummy "$VENV/bin/python" "$HERE/make_icon.py" "$APPDIR/usr/share/icons/hicolor/256x256/apps/the-human-race.png"
cp "$APPDIR/usr/share/icons/hicolor/256x256/apps/the-human-race.png" "$APPDIR/the-human-race.png"
cp "$HERE/the-human-race.desktop" "$APPDIR/usr/share/applications/"
cp "$HERE/the-human-race.desktop" "$APPDIR/"
cat > "$APPDIR/AppRun" <<'RUN'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/bin/the-human-race" "$@"
RUN
chmod +x "$APPDIR/AppRun"

echo "==> Packing AppImage"
if [ ! -x "$TOOL" ]; then
    curl -fL --retry 3 -o "$TOOL" \
        "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-$ARCH.AppImage"
    chmod +x "$TOOL"
fi
OUT="$DIST/TheHumanRace-$VERSION-$ARCH.AppImage"
# --appimage-extract-and-run lets this work even where FUSE isn't available
ARCH="$ARCH" "$TOOL" --appimage-extract-and-run --no-appstream "$APPDIR" "$OUT"
chmod +x "$OUT"
cp "$APPDIR/the-human-race.png" "$DIST/the-human-race.png"
echo
echo "Built: $OUT"
