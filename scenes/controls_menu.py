"""CONTROLS: show and rebind keyboard + controller bindings per player."""
from config import rgb, BLACK, KEY_ACTIONS, PAD_ACTIONS, P1_COLOR, P2_COLOR
from scenes.base import Scene, Menu, draw_box
from graphics.background import Starfield
from input.manager import key_label, pad_label

ROWS = (["PLAYER"] + [("key", a) for a in KEY_ACTIONS] + [("pad", a) for a in PAD_ACTIONS]
        + ["RESET TO DEFAULTS", "BACK"])


class ControlsMenu(Scene):
    def __init__(self, game):
        Scene.__init__(self, game)
        self.player = 0
        self.menu = Menu([self._label(i) for i in range(len(ROWS))], 40, 13, x=24)
        self.menu.items = [lambda i=i: self._label(i) for i in range(len(ROWS))]
        self.waiting = None
        self.wait_t = 0
        self.stars = Starfield(seed=51)

    def _label(self, i):
        r = ROWS[i]
        if r == "PLAYER":
            return "PLAYER %d" % (self.player + 1)
        if isinstance(r, tuple):
            kind, act = r
            return ("KEY " if kind == "key" else "PAD ") + act.upper()
        return r

    def _binding_text(self, i):
        r = ROWS[i]
        if not isinstance(r, tuple):
            return ""
        kind, act = r
        b = self.game.settings.bindings[self.player]
        if kind == "key":
            codes = b["keys"][act]
            return "/".join(key_label(c) for c in codes[:2])
        pad = self.game.input.pad_for(self.player)
        is_ctrl = pad.is_controller if pad is not None else True
        return pad_label(b["pad"][act], is_ctrl)

    def update(self):
        self.t += 1
        self.stars.update()
        g = self.game
        inp = g.input
        if self.waiting is not None:
            self.wait_t += 1
            if inp.captured is not None:
                self._apply(inp.captured)
                inp.captured = None
                self.waiting = None
            elif self.wait_t > 60 * 8:
                inp.capture = None
                self.waiting = None
            return
        r = self.menu.update(g)
        i = self.menu.index
        row = ROWS[i]
        if r == "back":
            g.settings.save()
            g.pop()
            return
        if row == "PLAYER" and r in ("left", "right", "confirm"):
            self.player = 1 - self.player
            g.audio.play("menu_move")
        elif r == "confirm":
            if isinstance(row, tuple):
                kind, act = row
                self.waiting = row
                self.wait_t = 0
                inp.begin_capture(kind, self.player)
            elif row == "RESET TO DEFAULTS":
                g.settings.reset_bindings(self.player)
                g.settings.save()
            elif row == "BACK":
                g.settings.save()
                g.pop()

    def _apply(self, value):
        if value == "cancel":
            return
        kind, act = self.waiting
        b = self.game.settings.bindings[self.player]
        if kind == "key":
            b["keys"][act] = [value]
        else:
            src, button = value
            entry = b["pad"][act]
            if src == "ctrl":
                entry["ctrl"] = [button]
            else:
                entry["joy"] = [button]
        self.game.settings.save()
        self.game.audio.play("menu_select")

    def draw(self, surf):
        surf.fill(rgb(BLACK))
        self.stars.draw(surf)
        font = self.game.font
        col = P1_COLOR if self.player == 0 else P2_COLOR
        font.draw_center(surf, "CONTROLS", 12, 0x28, shadow=BLACK)
        pad = self.game.input.pad_name(self.player)
        font.draw_center(surf, ("PAD: " + pad.upper())[:30] if pad else "PAD: NOT CONNECTED", 24, 0x00)
        self.menu.draw(surf, font, self.t)
        for i in range(len(ROWS)):
            txt = self._binding_text(i)
            if txt:
                font.draw_right(surf, txt, 240, 40 + i * 13, col)
        font.draw(surf, "{ }", 216, 40, col)
        font.draw_center(surf, "PAD MOVE: D-PAD / LEFT STICK", 222, 0x00)
        if self.waiting is not None:
            kind, act = self.waiting
            draw_box(surf, 24, 92, 208, 56)
            what = "KEY" if kind == "key" else "BUTTON"
            font.draw_center(surf, "PRESS A %s FOR" % what, 104, 0x30)
            font.draw_center(surf, act.upper(), 116, 0x28)
            font.draw_center(surf, "ESC TO CANCEL", 132, 0x00)
