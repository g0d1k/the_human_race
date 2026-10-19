"""Keyboard + controller input with hot-plugging and rebinding support.

Controllers recognised by SDL's GameController database (Xbox, PlayStation,
Switch Pro, 8BitDo, ...) are opened through pygame._sdl2.controller so their
buttons have consistent names. Anything else falls back to the raw joystick
API (buttons by index, hat 0, axes 0/1).

Pad state is polled once per update and edges are derived from the previous
frame, so a device disappearing mid-game can never leave a stuck button.
"""
import pygame

from config import KEY_ACTIONS

try:
    from pygame._sdl2 import controller as sdl_controller
except Exception:          # pragma: no cover - depends on the pygame build
    sdl_controller = None

DEADZONE = 0.45
REPEAT_DELAY = 18
REPEAT_RATE = 6

_CTRL_BUTTON_NAMES = (
    ("a", "CONTROLLER_BUTTON_A"), ("b", "CONTROLLER_BUTTON_B"),
    ("x", "CONTROLLER_BUTTON_X"), ("y", "CONTROLLER_BUTTON_Y"),
    ("back", "CONTROLLER_BUTTON_BACK"), ("guide", "CONTROLLER_BUTTON_GUIDE"),
    ("start", "CONTROLLER_BUTTON_START"),
    ("leftstick", "CONTROLLER_BUTTON_LEFTSTICK"), ("rightstick", "CONTROLLER_BUTTON_RIGHTSTICK"),
    ("lb", "CONTROLLER_BUTTON_LEFTSHOULDER"), ("rb", "CONTROLLER_BUTTON_RIGHTSHOULDER"),
    ("dpup", "CONTROLLER_BUTTON_DPAD_UP"), ("dpdown", "CONTROLLER_BUTTON_DPAD_DOWN"),
    ("dpleft", "CONTROLLER_BUTTON_DPAD_LEFT"), ("dpright", "CONTROLLER_BUTTON_DPAD_RIGHT"),
)
CTRL_BUTTONS = []
for _name, _const in _CTRL_BUTTON_NAMES:
    if hasattr(pygame, _const):
        CTRL_BUTTONS.append((_name, getattr(pygame, _const)))
_AX_LX = getattr(pygame, "CONTROLLER_AXIS_LEFTX", 0)
_AX_LY = getattr(pygame, "CONTROLLER_AXIS_LEFTY", 1)
_AX_LT = getattr(pygame, "CONTROLLER_AXIS_TRIGGERLEFT", 4)
_AX_RT = getattr(pygame, "CONTROLLER_AXIS_TRIGGERRIGHT", 5)

_controller_ready = False


def _init_controller_module():
    global _controller_ready
    if sdl_controller is None:
        return False
    if not _controller_ready:
        try:
            sdl_controller.init()
            _controller_ready = True
        except Exception:
            return False
    return True


class Pad:
    """One connected game pad (GameController or raw Joystick)."""

    def __init__(self, device_index):
        self.ctrl = None
        self.joy = None
        self.dead = False
        self.name = "PAD"
        if _init_controller_module():
            try:
                if sdl_controller.is_controller(device_index):
                    self.ctrl = sdl_controller.Controller(device_index)
                    self.instance_id = self.ctrl.as_joystick().get_instance_id()
                    self.name = getattr(self.ctrl, "name", None) or "CONTROLLER"
            except Exception:
                self.ctrl = None
        if self.ctrl is None:
            self.joy = pygame.joystick.Joystick(device_index)
            try:
                self.joy.init()
            except Exception:
                pass
            self.instance_id = self.joy.get_instance_id()
            self.name = self.joy.get_name() or "JOYSTICK"
        self.buttons = set()
        self.prev_buttons = set()
        self.dirs = set()
        self.prev_dirs = set()

    @property
    def is_controller(self):
        return self.ctrl is not None

    def poll(self):
        self.prev_buttons = self.buttons
        self.prev_dirs = self.dirs
        btns = set()
        dirs = set()
        try:
            if self.ctrl is not None:
                c = self.ctrl
                for name, const in CTRL_BUTTONS:
                    if c.get_button(const):
                        btns.add(name)
                ax = c.get_axis(_AX_LX) / 32768.0
                ay = c.get_axis(_AX_LY) / 32768.0
                if c.get_axis(_AX_LT) > 16000:
                    btns.add("lt")
                if c.get_axis(_AX_RT) > 16000:
                    btns.add("rt")
                if "dpup" in btns:
                    dirs.add("up")
                if "dpdown" in btns:
                    dirs.add("down")
                if "dpleft" in btns:
                    dirs.add("left")
                if "dpright" in btns:
                    dirs.add("right")
            else:
                j = self.joy
                for i in range(min(j.get_numbuttons(), 32)):
                    if j.get_button(i):
                        btns.add(i)
                ax = ay = 0.0
                if j.get_numaxes() >= 2:
                    ax = j.get_axis(0)
                    ay = j.get_axis(1)
                if j.get_numhats() > 0:
                    hx, hy = j.get_hat(0)
                    if hx < 0:
                        dirs.add("left")
                    elif hx > 0:
                        dirs.add("right")
                    if hy > 0:
                        dirs.add("up")
                    elif hy < 0:
                        dirs.add("down")
            if ax < -DEADZONE:
                dirs.add("left")
            elif ax > DEADZONE:
                dirs.add("right")
            if ay < -DEADZONE:
                dirs.add("up")
            elif ay > DEADZONE:
                dirs.add("down")
        except (pygame.error, AttributeError, ValueError):
            self.dead = True
            btns = set()
            dirs = set()
        self.buttons = btns
        self.dirs = dirs

    def pressed_buttons(self):
        return self.buttons - self.prev_buttons

    def pressed_dirs(self):
        return self.dirs - self.prev_dirs

    def matches(self, binding, button_set):
        """Does any button in button_set satisfy a {'ctrl': [...], 'joy': [...]} binding?"""
        if self.ctrl is not None:
            return any(b in button_set for b in binding.get("ctrl", ()))
        return any(b in button_set for b in binding.get("joy", ()))

    def close(self):
        try:
            if self.ctrl is not None:
                self.ctrl.quit()
            elif self.joy is not None:
                self.joy.quit()
        except Exception:
            pass


class InputManager:
    MENU_CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_z)
    MENU_BACK_KEYS = (pygame.K_ESCAPE, pygame.K_BACKSPACE, pygame.K_x)
    MENU_DIR_KEYS = {
        pygame.K_UP: "up", pygame.K_DOWN: "down", pygame.K_LEFT: "left", pygame.K_RIGHT: "right",
        pygame.K_w: "up", pygame.K_s: "down", pygame.K_a: "left", pygame.K_d: "right",
    }

    def __init__(self, settings):
        self.settings = settings
        self.pads = {}            # instance_id -> Pad
        self.slots = [None, None]  # instance_id assigned to player 1 / player 2
        self.key_events = []
        self.held = [set(), set()]
        self.pressed = [set(), set()]
        self.pad_pressed = [set(), set()]   # presses that came from the player's pad
        self.menu = set()
        self.any_pressed = False
        self.disconnected = []    # player indices whose pad was unplugged this frame
        self.connected = []       # names of newly connected pads (for on-screen notice)
        self._menu_hold = {}
        self.p2_active = False    # when False, player 1 may also use player 2's direction keys
        self.capture = None       # None | ("key", player) | ("pad", player)
        self.captured = None
        try:
            pygame.joystick.init()
        except pygame.error:
            pass
        _init_controller_module()
        # Open pads that are already plugged in (duplicate "added" events are ignored)
        try:
            for i in range(pygame.joystick.get_count()):
                self._add_device(i)
        except pygame.error:
            pass

    # ------------------------------------------------------------------
    # Device management
    # ------------------------------------------------------------------
    def _add_device(self, device_index):
        try:
            iid = pygame.joystick.Joystick(device_index).get_instance_id()
            if iid in self.pads:
                return
            pad = Pad(device_index)
        except (pygame.error, IndexError, ValueError, AttributeError):
            return
        if pad.instance_id in self.pads:
            return
        self.pads[pad.instance_id] = pad
        for i in range(2):
            if self.slots[i] is None:
                self.slots[i] = pad.instance_id
                break
        self.connected.append(pad.name)

    def _remove_device(self, instance_id):
        pad = self.pads.pop(instance_id, None)
        if pad is None:
            return
        pad.close()
        for i in range(2):
            if self.slots[i] == instance_id:
                self.slots[i] = None
                self.disconnected.append(i)
        # give a free slot to any unassigned pad
        for iid in self.pads:
            if iid not in self.slots:
                for i in range(2):
                    if self.slots[i] is None:
                        self.slots[i] = iid
                        break

    def pad_for(self, player):
        iid = self.slots[player]
        return self.pads.get(iid) if iid is not None else None

    def pad_name(self, player):
        pad = self.pad_for(player)
        return pad.name if pad else None

    # ------------------------------------------------------------------
    def process_event(self, e):
        t = e.type
        if t == pygame.KEYDOWN:
            self.key_events.append(e.key)
        elif t == pygame.JOYDEVICEADDED:
            self._add_device(e.device_index)
        elif t == pygame.JOYDEVICEREMOVED:
            self._remove_device(e.instance_id)

    def begin_capture(self, kind, player):
        self.capture = (kind, player)
        self.captured = None

    def update(self):
        """Call once per fixed update step."""
        for iid, pad in list(self.pads.items()):
            pad.poll()
            if pad.dead:
                self._remove_device(iid)
        keys = pygame.key.get_pressed()
        binds = self.settings.bindings
        events = self.key_events
        self.key_events = []
        self.any_pressed = bool(events)

        # --- rebinding capture mode -----------------------------------
        if self.capture is not None:
            kind, player = self.capture
            if kind == "key":
                for k in events:
                    self.captured = "cancel" if k == pygame.K_ESCAPE else k
                    break
            else:
                if pygame.K_ESCAPE in events:
                    self.captured = "cancel"
                pads = [self.pad_for(player)] if self.pad_for(player) else list(self.pads.values())
                for pad in pads:
                    pb = pad.pressed_buttons()
                    pb = {b for b in pb if b not in ("dpup", "dpdown", "dpleft", "dpright")}
                    if pb:
                        b = sorted(pb, key=str)[0]
                        self.captured = ("ctrl", b) if pad.is_controller else ("joy", b)
                        break
            if self.captured is not None:
                self.capture = None
            for p in range(2):
                self.held[p] = set()
                self.pressed[p] = set()
                self.pad_pressed[p] = set()
            self.menu = set()
            return

        # --- per-player actions ---------------------------------------
        for p in range(2):
            kb = binds[p]["keys"]
            held = set()
            pressed = set()
            for act in KEY_ACTIONS:
                codes = kb[act]
                if p == 0 and not self.p2_active and act in ("up", "down", "left", "right"):
                    codes = codes + binds[1]["keys"][act]
                for c in codes:
                    try:
                        if keys[c]:
                            held.add(act)
                    except IndexError:
                        pass
                    if c in events:
                        pressed.add(act)
            padp = set()
            pad = self.pad_for(p)
            if pad is not None:
                pdirs = pad.dirs
                held |= pdirs
                pressed |= pad.pressed_dirs()
                pb = pad.pressed_buttons()
                for act, binding in binds[p]["pad"].items():
                    if pad.matches(binding, pad.buttons):
                        held.add(act)
                    if pad.matches(binding, pb):
                        pressed.add(act)
                        padp.add(act)
                if pb:
                    self.any_pressed = True
            self.held[p] = held
            self.pressed[p] = pressed
            self.pad_pressed[p] = padp

        # --- menu navigation (any device) -----------------------------
        menu = set()
        for k in events:
            if k in self.MENU_DIR_KEYS:
                menu.add(self.MENU_DIR_KEYS[k])
            if k in self.MENU_CONFIRM_KEYS:
                menu.add("confirm")
            if k in self.MENU_BACK_KEYS:
                menu.add("back")
            for p in range(2):
                kb = binds[p]["keys"]
                if k in kb["fire"]:
                    menu.add("confirm")
                if k in kb["up"]:
                    menu.add("up")
                if k in kb["down"]:
                    menu.add("down")
                if k in kb["left"]:
                    menu.add("left")
                if k in kb["right"]:
                    menu.add("right")
        held_dirs = set()
        for k, d in self.MENU_DIR_KEYS.items():
            try:
                if keys[k]:
                    held_dirs.add(d)
            except IndexError:
                pass
        for pad in self.pads.values():
            menu |= pad.pressed_dirs()
            held_dirs |= pad.dirs
            pb = pad.pressed_buttons()
            if pad.is_controller:
                if pb & {"a", "start"}:
                    menu.add("confirm")
                if pb & {"b", "back"}:
                    menu.add("back")
            else:
                if 0 in pb or 9 in pb or 7 in pb:
                    menu.add("confirm")
                if 1 in pb or 8 in pb or 6 in pb:
                    menu.add("back")
        # auto-repeat for held directions
        for d in ("up", "down", "left", "right"):
            if d in held_dirs:
                n = self._menu_hold.get(d, 0) + 1
                self._menu_hold[d] = n
                if n > REPEAT_DELAY and (n - REPEAT_DELAY) % REPEAT_RATE == 0:
                    menu.add(d)
            else:
                self._menu_hold[d] = 0
        self.menu = menu

    def end_frame(self):
        self.disconnected = []
        self.connected = []

    def consume(self):
        """Discard this frame's presses (used when switching scenes)."""
        for p in range(2):
            self.pressed[p] = set()
            self.pad_pressed[p] = set()
        self.menu = set()
        self.any_pressed = False


def key_label(code):
    try:
        name = pygame.key.name(code)
    except Exception:
        name = "?"
    name = (name or "?").upper()
    repl = {"LEFT SHIFT": "LSHIFT", "RIGHT SHIFT": "RSHIFT", "LEFT CTRL": "LCTRL",
            "RIGHT CTRL": "RCTRL", "LEFT ALT": "LALT", "RIGHT ALT": "RALT",
            "RETURN": "ENTER", "BACKSPACE": "BKSP", "[0]": "KP0", "[1]": "KP1"}
    name = repl.get(name, name)
    if name.startswith("[") and name.endswith("]"):
        name = "KP" + name[1:-1]
    if name.startswith("KEYPAD "):
        name = "KP" + name[7:]
    out = "".join(ch for ch in name if ch.isalnum() or ch in " -+.,/")
    return out[:7] if out else "?"


def pad_label(binding, is_controller):
    if is_controller:
        names = binding.get("ctrl", [])
        return names[0].upper()[:7] if names else "-"
    idx = binding.get("joy", [])
    return ("BTN%d" % idx[0]) if idx else "-"
