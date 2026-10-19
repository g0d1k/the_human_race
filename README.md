# THE HUMAN RACE

An 8-bit, NES-style horizontally scrolling space shooter for 1 or 2 players
(simultaneous co-op), written in Python with pygame.

**Everything is generated in code.** There are no image, audio or font files:
sprites are text grids, the font is an 8x8 bitmap table, planets are dithered
procedurally, and the music and sound effects are synthesized by a small NES
APU emulator (2 pulse voices, triangle, noise) at startup.

> YEAR 2291. Six sectors. Six Vexari champions. One finish line.
> The Human Race has begun.

---

## Quick start

**Already installed?** Open **The Human Race** from your applications menu, or run:

```bash
~/.local/bin/the-human-race
```

**Using the AppImage directly** (no install, no Python needed):

```bash
./dist/TheHumanRace-*-x86_64.AppImage
```

**From source** (any OS with Python), see [Requirements](#requirements) below.

At the title screen press Start (or Enter), choose **START GAME** and then
**1 PLAYER** or **2 PLAYERS**.

---

## Requirements

- Python 3.8 or newer
- pygame-ce 2.1+ **or** pygame 2.1+ (the only dependency; no numpy)
- Windows, Linux or macOS

## Install and run

```bash
cd the_human_race
python -m pip install -r requirements.txt
python main.py
```

(If you prefer classic pygame: `pip install pygame` works too.)

Settings, key bindings and high scores are stored in `~/.the_human_race/`
(`config.json`, `highscores.json`). Missing or corrupt files are replaced
with defaults automatically.

---

## Controls

### Keyboard (both players can share one keyboard)

| Action | Player 1 | Player 2 |
|---|---|---|
| Move | W A S D (arrows too, while P2 is not playing) | Arrow keys |
| Fire (hold for autofire) | Space | Right Ctrl or Numpad 0 |
| Bomb | Left Shift | Right Shift or Numpad 1 |
| Pause | P | P |

Menus: arrows / WASD to move, Enter / Space to select, Esc / Backspace to go back.
**F11** or **Alt+Enter** toggles fullscreen anywhere.

### Controllers

Any gamepad works: Xbox, PlayStation, Switch Pro, 8BitDo and others via SDL's
GameController mappings, plus generic USB pads through the raw joystick API.

- Move: D-pad **or** left stick
- A / Cross = Fire, B / Circle = Bomb, Start = Pause
- First controller connected is Player 1, second is Player 2.
  Controllers can be plugged in or out at any time; unplugging one mid-game
  pauses the game.

Every action can be rebound per player, for keyboard and controller, on the
**CONTROLS** screen (also reachable from the pause menu). Bindings are saved.

### Story intro

The story plays when the game starts, one page at a time:

- **Any key or button** shows the rest of the page if it is still typing,
  then turns to the next page.
- **Esc** (keyboard) or **B / Back** (controller) skips the whole story.

If you leave the title screen idle for 30 seconds, the story replays by itself
(pages turn automatically). Press anything to return to the title.

### Joining

- In a 1-player game, Player 2 can join at any time: press **Start** on
  their pad or their **Fire** key.
- In 2-player mode, if one player runs out of lives they can rejoin by
  pressing Start, borrowing one life from a partner who has 2 or more.

---

## How to play

Fly through 6 sectors of scripted enemy waves (about 2.5 minutes each).
Each sector ends with a multi-phase boss. Clear Sector 6 to reach the ending,
then the race loops as **LAP 2** with tougher enemies (score and lives carry over).

| Sector | Name | Boss |
|---|---|---|
| 1 | Lunar Outskirts | SENTINEL |
| 2 | Asteroid Belt | HIVE MOTHER |
| 3 | Jovian Storm | TEMPEST |
| 4 | Ice Rings | CRYO-LANCER |
| 5 | Nebula Graveyard | REVENANT |
| 6 | The Finish Line | THE ARBITER |

Only the cockpit of your ship can be hit (small hitbox). After losing a life
you respawn from the left with about 2 seconds of invincibility.

### Pickups

| Pickup | Effect |
|---|---|
| **P** Power | Weapon level up: single, double, spread, spread + rear (max 4) |
| **L** Laser | Switch to a piercing laser (keeps weapon level) |
| **S** Speed | Ship speed up, up to 3 levels (S3 is about twice as fast). Your engine flame grows with each level |
| **B** Bomb | +1 bomb (max 5). Bombs clear bullets and damage everything |
| **O** Shield | Absorbs one hit |
| **1UP** | Extra life (rare) |

Destroying a whole formation guarantees a pickup. Losing a life costs one
weapon level and all speed upgrades.

### Scoring

- Extra life every 20,000 points (10k / 20k / 30k in Settings)
- Boss bonus: 5,000 x sector number; no-miss sector bonus: 2,000 x sector
- 3 continues per game. Continuing resets your score but keeps your progress.
  Your best score before continuing still counts for the high-score table.

### Settings

Music / SFX volume (0-10), window scale (2x/3x/4x), fullscreen, difficulty
(EASY / NORMAL / HARD), extra-life threshold, CRT scanlines, screen shake.

---

## Linux: AppImage and install

Build a single-file AppImage (about 16 MB, with Python and pygame bundled inside):

```bash
./packaging/build_appimage.sh
```

The first build needs internet access. It downloads PyInstaller, pygame-ce
and `appimagetool` into `build/`. The result is
`dist/TheHumanRace-<version>-x86_64.AppImage`, which you can run directly or copy to
another PC.

To install it for your user, with an application-menu entry and icon (no root needed):

```bash
./packaging/install.sh
```

Uninstall with `./packaging/install.sh --uninstall`. This keeps your scores
and settings in `~/.the_human_race`.

An AppImage only runs on distros whose glibc is the same age as, or newer
than, the system it was built on. To support older distros, build on an
older system (for example an older Ubuntu LTS VM or container).

## Build a standalone executable

This creates a single executable that runs on PCs without Python installed.
Build on the OS you are targeting: build on Windows for a `.exe`, on macOS
for a `.app`.

```bash
python -m pip install pyinstaller
python build_exe.py
```

The output goes to `dist/`, for example `dist/TheHumanRace.exe` on Windows.
No data files need to be shipped alongside it.

---

## Troubleshooting

- **Controller not detected.** Plug it in and look for "CONNECTED: ..." at the
  bottom of the screen. The CONTROLS screen shows which pad belongs to each
  player. Pads can be plugged in at any time. The first one is Player 1.
- **No sound.** The game runs silently if no audio device is available. Check
  MUSIC and SFX volume under SETTINGS.
- **Window too big or too small.** Change WINDOW SCALE in SETTINGS, or press
  F11 for fullscreen.
- **Reset everything.** Delete `~/.the_human_race/`. Settings, bindings and
  the high-score table go back to defaults.
- **The AppImage will not start on another PC.** That PC's Linux is older
  than the one the AppImage was built on (see the glibc note above). Build it
  on an older distro, or run from source.

---

## Project layout

```
the_human_race/
  main.py              entry point, fixed-timestep loop, scene stack
  config.py            constants, NES master palette, settings load/save
  highscores.py        top-10 table (JSON)
  graphics/            sprite grids, sprite builder, 8x8 font, scaling, backgrounds
  audio/               APU synth, MML compiler, songs, sound effects, mixer front-end
  entities/            players, enemies, bosses, bullets/particle pools, power-ups, world
  levels/              sector wave scripts, difficulty scaling
  scenes/              intro, title, menus, gameplay, pause, game over, high scores, ending
  input/               keyboard + controller handling, hot-plug, rebinding
  build_exe.py         PyInstaller build script (Windows / macOS / Linux single file)
  packaging/           AppImage build script, desktop entry, icon generator, installer
```

### Technical notes

- Renders to a 256x240 surface, then scales it to the window with integer
  nearest-neighbour scaling and letterboxing.
- Uses only colours from the NES master palette. The pause screen is dimmed
  by swapping palette entries, not with alpha.
- Sprites keep NES limits (3 colours + transparency). Bosses are built from
  several sprites.
- Game logic runs at a fixed 60 Hz. On slow machines frames are skipped
  (up to 4 logic steps per drawn frame) before the game slows down.
- Bullets, particles, explosions, enemies and beams use fixed-size object
  pools, so nothing is allocated per frame and on-screen counts are capped.
- Audio buffers match the mixer's actual rate, format and channel count. If
  no audio device is available, the game runs silently.
