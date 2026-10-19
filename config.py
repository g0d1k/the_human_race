"""Global constants, the NES master palette, and settings load/save."""
import os
import json
import copy

import pygame

TITLE = "THE HUMAN RACE"
VERSION = "1.1"
SCREEN_W = 256
SCREEN_H = 240
FPS = 60
HUD_H = 16          # height of the top status bar
PLAY_TOP = 18       # top of the playfield (below the HUD)
PLAY_BOTTOM = 236   # bottom of the playfield

# ---------------------------------------------------------------------------
# Standard NES (2C02) master palette, indexed $00-$3F.
# Entries $0D/$0E/$0F, $1D-$1F, $2E/$2F, $3E/$3F are blacks; $0F is the
# canonical "black" used everywhere in this game.
# ---------------------------------------------------------------------------
NES_PALETTE = (
    (84, 84, 84), (0, 30, 116), (8, 16, 144), (48, 0, 136),
    (68, 0, 100), (92, 0, 48), (84, 4, 0), (60, 24, 0),
    (32, 42, 0), (8, 58, 0), (0, 64, 0), (0, 60, 0),
    (0, 50, 60), (0, 0, 0), (0, 0, 0), (0, 0, 0),
    (152, 150, 152), (8, 76, 196), (48, 50, 236), (92, 30, 228),
    (136, 20, 176), (160, 20, 100), (152, 34, 32), (120, 60, 0),
    (84, 90, 0), (40, 114, 0), (8, 124, 0), (0, 118, 40),
    (0, 102, 120), (0, 0, 0), (0, 0, 0), (0, 0, 0),
    (236, 238, 236), (76, 154, 236), (120, 124, 236), (176, 98, 236),
    (228, 84, 236), (236, 88, 180), (236, 106, 100), (212, 136, 32),
    (160, 170, 0), (116, 196, 0), (76, 208, 32), (56, 204, 108),
    (56, 180, 204), (60, 60, 60), (0, 0, 0), (0, 0, 0),
    (236, 238, 236), (168, 204, 236), (188, 188, 236), (212, 178, 236),
    (236, 174, 236), (236, 174, 212), (236, 180, 176), (228, 196, 144),
    (204, 210, 120), (180, 222, 120), (168, 226, 144), (152, 226, 180),
    (160, 214, 228), (160, 162, 160), (0, 0, 0), (0, 0, 0),
)

# The usable (non-duplicate, non-"blacker than black") colours.
_UNUSABLE = {0x0D, 0x0E, 0x1D, 0x1E, 0x1F, 0x2E, 0x2F, 0x3E, 0x3F, 0x20}
USABLE_COLORS = tuple(i for i in range(64) if i not in _UNUSABLE)

BLACK = 0x0F
WHITE = 0x30
GRAY_D = 0x00
GRAY = 0x10
GRAY_L = 0x3D
RED = 0x16
GREEN = 0x1A
P1_COLOR = 0x26     # HUD colour for player 1 (bright red)
P2_COLOR = 0x2A     # HUD colour for player 2 (bright green)
YELLOW = 0x28
ORANGE = 0x27
CYAN = 0x2C
BLUE = 0x21
PURPLE = 0x24


def rgb(index):
    """Return the RGB tuple for an NES palette index."""
    return NES_PALETTE[index]


def dim_index(index):
    """Map a palette index to the next darker row (used for pause dimming)."""
    if index >= 0x10:
        return index - 0x10
    return BLACK


# ---------------------------------------------------------------------------
# Per-user data folder
# ---------------------------------------------------------------------------
def data_dir():
    path = os.path.join(os.path.expanduser("~"), ".the_human_race")
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        pass
    return path


CONFIG_FILE = "config.json"
SCORES_FILE = "highscores.json"


def load_json(name):
    """Load a JSON file from the data folder; return None on any failure."""
    try:
        with open(os.path.join(data_dir(), name), "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError, TypeError):
        return None


def save_json(name, data):
    """Atomically write JSON to the data folder; failures are ignored."""
    path = os.path.join(data_dir(), name)
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)
        return True
    except (OSError, TypeError, ValueError):
        return False


# ---------------------------------------------------------------------------
# Settings and bindings
# ---------------------------------------------------------------------------
KEY_ACTIONS = ("up", "down", "left", "right", "fire", "bomb", "pause")
PAD_ACTIONS = ("fire", "bomb", "pause")
DIFFICULTY_NAMES = ("EASY", "NORMAL", "HARD")
EXTRA_LIFE_OPTIONS = (10000, 20000, 30000)
SCALE_OPTIONS = (2, 3, 4)


def default_bindings():
    return [
        {
            "keys": {
                "up": [pygame.K_w], "down": [pygame.K_s],
                "left": [pygame.K_a], "right": [pygame.K_d],
                "fire": [pygame.K_SPACE], "bomb": [pygame.K_LSHIFT],
                "pause": [pygame.K_p],
            },
            "pad": {
                "fire": {"ctrl": ["a"], "joy": [0]},
                "bomb": {"ctrl": ["b"], "joy": [1]},
                "pause": {"ctrl": ["start"], "joy": [7, 9]},
            },
        },
        {
            "keys": {
                "up": [pygame.K_UP], "down": [pygame.K_DOWN],
                "left": [pygame.K_LEFT], "right": [pygame.K_RIGHT],
                "fire": [pygame.K_RCTRL, pygame.K_KP0],
                "bomb": [pygame.K_RSHIFT, pygame.K_KP1],
                "pause": [pygame.K_p],
            },
            "pad": {
                "fire": {"ctrl": ["a"], "joy": [0]},
                "bomb": {"ctrl": ["b"], "joy": [1]},
                "pause": {"ctrl": ["start"], "joy": [7, 9]},
            },
        },
    ]


DEFAULT_SETTINGS = {
    "music_volume": 7,
    "sfx_volume": 8,
    "scale": 3,
    "fullscreen": False,
    "difficulty": 1,
    "extra_life": 20000,
    "scanlines": False,
    "shake": True,
}


def _int_list(value, fallback):
    if isinstance(value, list) and value and all(isinstance(v, int) for v in value):
        return list(value)
    return list(fallback)


def _str_list(value, fallback):
    if isinstance(value, list) and all(isinstance(v, str) for v in value):
        return list(value)
    return list(fallback)


class Settings:
    """Holds all user settings and control bindings; persists to JSON."""

    def __init__(self):
        self.values = dict(DEFAULT_SETTINGS)
        self.bindings = default_bindings()
        self.load()

    def __getitem__(self, key):
        return self.values[key]

    def __setitem__(self, key, value):
        self.values[key] = value

    def load(self):
        data = load_json(CONFIG_FILE)
        if not isinstance(data, dict):
            return
        for key, default in DEFAULT_SETTINGS.items():
            val = data.get(key, default)
            if isinstance(default, bool):
                self.values[key] = bool(val) if isinstance(val, (bool, int)) else default
            elif isinstance(val, int) and not isinstance(val, bool):
                self.values[key] = val
        v = self.values
        v["music_volume"] = max(0, min(10, v["music_volume"]))
        v["sfx_volume"] = max(0, min(10, v["sfx_volume"]))
        if v["scale"] not in SCALE_OPTIONS:
            v["scale"] = 3
        v["difficulty"] = max(0, min(2, v["difficulty"]))
        if v["extra_life"] not in EXTRA_LIFE_OPTIONS:
            v["extra_life"] = 20000
        self._load_bindings(data.get("bindings"))

    def _load_bindings(self, data):
        defaults = default_bindings()
        if not isinstance(data, list) or len(data) != 2:
            return
        result = copy.deepcopy(defaults)
        for p in range(2):
            src = data[p] if isinstance(data[p], dict) else {}
            keys = src.get("keys", {}) if isinstance(src.get("keys"), dict) else {}
            for act in KEY_ACTIONS:
                result[p]["keys"][act] = _int_list(keys.get(act), defaults[p]["keys"][act])
            pad = src.get("pad", {}) if isinstance(src.get("pad"), dict) else {}
            for act in PAD_ACTIONS:
                entry = pad.get(act, {}) if isinstance(pad.get(act), dict) else {}
                d = defaults[p]["pad"][act]
                result[p]["pad"][act] = {
                    "ctrl": _str_list(entry.get("ctrl"), d["ctrl"]),
                    "joy": _int_list(entry.get("joy"), d["joy"]),
                }
        self.bindings = result

    def reset_bindings(self, player=None):
        defaults = default_bindings()
        if player is None:
            self.bindings = defaults
        else:
            self.bindings[player] = defaults[player]

    def save(self):
        data = dict(self.values)
        data["bindings"] = self.bindings
        save_json(CONFIG_FILE, data)
