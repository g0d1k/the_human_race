"""Scene base class and shared menu / drawing helpers."""
from config import rgb, BLACK


class Scene:
    def __init__(self, game):
        self.game = game
        self.t = 0

    def enter(self):
        pass

    def exit(self):
        pass

    def resume(self):
        pass

    def update(self):
        self.t += 1

    def draw(self, surf):
        pass

    def shake_offset(self):
        return 0, 0


class Menu:
    """Vertical list with a blinking cursor. Items are strings or callables."""

    def __init__(self, items, y, spacing=12, x=None, color=0x30, sel_color=0x28):
        self.items = list(items)
        self.index = 0
        self.y = y
        self.spacing = spacing
        self.x = x
        self.color = color
        self.sel_color = sel_color
        self.disabled = set()

    def label(self, i):
        it = self.items[i]
        return it() if callable(it) else it

    def update(self, game):
        """Returns 'confirm', 'back', 'left', 'right' or None."""
        m = game.input.menu
        audio = game.audio
        n = len(self.items)
        if "up" in m:
            self.index = (self.index - 1) % n
            while self.index in self.disabled:
                self.index = (self.index - 1) % n
            audio.play("menu_move")
        if "down" in m:
            self.index = (self.index + 1) % n
            while self.index in self.disabled:
                self.index = (self.index + 1) % n
            audio.play("menu_move")
        if "confirm" in m:
            audio.play("menu_select")
            return "confirm"
        if "back" in m:
            return "back"
        if "left" in m:
            return "left"
        if "right" in m:
            return "right"
        return None

    def draw(self, surf, font, frame):
        for i in range(len(self.items)):
            text = self.label(i)
            y = self.y + i * self.spacing
            if self.x is None:
                x = 128 - len(text) * 4
            else:
                x = self.x
            col = self.sel_color if i == self.index else self.color
            if i in self.disabled:
                col = 0x00
            font.draw(surf, text, x, y, col, shadow=BLACK)
            if i == self.index and (frame >> 4) & 1 == 0:
                font.draw(surf, "~", x - 12, y, 0x26)


def draw_box(surf, x, y, w, h, fill=BLACK, border=0x30):
    surf.fill(rgb(border), (x, y, w, h))
    surf.fill(rgb(fill), (x + 1, y + 1, w - 2, h - 2))
    surf.fill(rgb(border), (x + 2, y + 2, w - 4, 1))
    surf.fill(rgb(fill), (x + 3, y + 3, w - 6, h - 6))


def wrap(text, width):
    """Word-wrap text to lines of at most `width` characters."""
    lines = []
    for para in text.split("\n"):
        words = para.split(" ")
        line = ""
        for w in words:
            if not line:
                line = w
            elif len(line) + 1 + len(w) <= width:
                line += " " + w
            else:
                lines.append(line)
                line = w
        lines.append(line)
    return lines
