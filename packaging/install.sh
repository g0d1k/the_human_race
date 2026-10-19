#!/usr/bin/env bash
# Install (or remove) The Human Race for the current user, with a menu entry.
#
#   ./packaging/install.sh [path/to/TheHumanRace.AppImage]
#   ./packaging/install.sh --uninstall
#
# Installs to ~/.local (no root needed): the AppImage goes in
# ~/.local/bin/the-human-race, plus a desktop entry and icon.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
BIN="$HOME/.local/bin/the-human-race"
DESKTOP="$HOME/.local/share/applications/the-human-race.desktop"
ICON="$HOME/.local/share/icons/hicolor/256x256/apps/the-human-race.png"

refresh() {
    command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database -q "$HOME/.local/share/applications" || true
    if [ -f "$HOME/.local/share/icons/hicolor/index.theme" ] && command -v gtk-update-icon-cache >/dev/null 2>&1; then
        gtk-update-icon-cache -q -t "$HOME/.local/share/icons/hicolor" || true
    fi
}

if [ "${1:-}" = "--uninstall" ]; then
    rm -f "$BIN" "$DESKTOP" "$ICON"
    refresh
    echo "The Human Race was removed. (Your scores and settings in ~/.the_human_race were kept.)"
    exit 0
fi

APPIMAGE="${1:-}"
if [ -z "$APPIMAGE" ]; then
    APPIMAGE="$(ls -t "$ROOT"/dist/TheHumanRace-*.AppImage 2>/dev/null | head -n1 || true)"
fi
if [ -z "$APPIMAGE" ] || [ ! -f "$APPIMAGE" ]; then
    echo "No AppImage found. Build one first:  ./packaging/build_appimage.sh" >&2
    exit 1
fi

mkdir -p "$(dirname "$BIN")" "$(dirname "$DESKTOP")" "$(dirname "$ICON")"
install -m 755 "$APPIMAGE" "$BIN"
if [ -f "$(dirname "$APPIMAGE")/the-human-race.png" ]; then
    cp "$(dirname "$APPIMAGE")/the-human-race.png" "$ICON"
else
    python3 "$HERE/make_icon.py" "$ICON" >/dev/null 2>&1 || echo "(no icon installed)"
fi
sed "s|^Exec=.*|Exec=$BIN|" "$HERE/the-human-race.desktop" > "$DESKTOP"
refresh
echo "Installed. Look for \"The Human Race\" in your applications menu,"
echo "or run:  $BIN"
