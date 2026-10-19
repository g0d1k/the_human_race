"""Build a standalone executable with PyInstaller.

    pip install pyinstaller
    python build_exe.py

The result is written to dist/ (dist/TheHumanRace.exe on Windows,
dist/TheHumanRace on Linux, dist/TheHumanRace.app on macOS). Because the
game has no asset files, nothing else needs to be bundled.
"""
import os
import sys

try:
    import PyInstaller.__main__
except ImportError:
    sys.exit("PyInstaller is not installed. Run:  pip install pyinstaller")

HERE = os.path.dirname(os.path.abspath(__file__))

args = [
    os.path.join(HERE, "main.py"),
    "--name=TheHumanRace",
    "--onefile",
    "--windowed",
    "--noconfirm",
    "--clean",
    "--paths=" + HERE,
    # scene modules are imported lazily, so list them explicitly
    "--hidden-import=scenes.intro",
    "--hidden-import=scenes.title",
    "--hidden-import=scenes.howto",
    "--hidden-import=scenes.highscore_view",
    "--hidden-import=scenes.settings_menu",
    "--hidden-import=scenes.controls_menu",
    "--hidden-import=scenes.gameplay",
    "--hidden-import=scenes.pause",
    "--hidden-import=scenes.gameover",
    "--hidden-import=scenes.sector_clear",
    "--hidden-import=scenes.ending",
    "--hidden-import=pygame._sdl2.controller",
]

if __name__ == "__main__":
    PyInstaller.__main__.run(args)
