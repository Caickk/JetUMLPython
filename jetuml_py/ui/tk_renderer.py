"""Backend Tk do Renderer: desenha em um Canvas aplicando o fator de zoom."""
from __future__ import annotations

import tkinter.font as tkfont

from ..rendering.renderer import Renderer
from ..rendering.text import TextMetrics, parse_markup

FAMILY = "Helvetica"
BASE_FONT_PX = 12
_ANCHOR = {"start": "w", "middle": "center", "end": "e"}


class TkTextMetrics(TextMetrics):
    """Larguras reais medidas pelo Tk (precisa existir uma janela raiz)."""

    def __init__(self, family: str = FAMILY, size: int = BASE_FONT_PX):
        super().__init__(size)
        self.family = family
        self._font = tkfont.Font(family=family, size=-size)

    def width(self, line: str) -> int:
        return self._font.measure(parse_markup(line).text)


class TkRenderer(Renderer):
    def __init__(self, canvas, scale: float = 1.0, family: str = FAMILY, size: int = BASE_FONT_PX):
        self.c, self.s = canvas, scale
        self.family, self.size = family, size
        self._ox = self._oy = 0

    def _xy(self, x, y):
        return (x - self._ox) * self.s, (y - self._oy) * self.s

    def _flat(self, points):
        return [v for p in points for v in self._xy(p.x, p.y)]

    @property
    def _w(self) -> int:
        return max(1, round(self.s))

    def begin(self, x, y, width, height, background):
        self._ox, self._oy = x, y
        self.c.delete("all")
        self.c.configure(bg=background, scrollregion=(0, 0, width * self.s, height * self.s))

    def line(self, points, stroke, dashed=False):
        self.c.create_line(*self._flat(points), fill=stroke, width=self._w,
                           dash=(6, 4) if dashed else ())

    def polygon(self, points, fill, stroke):
        self.c.create_polygon(*self._flat(points), fill=fill, outline=stroke, width=self._w)

    def rect(self, x, y, w, h, fill, stroke, radius=0):
        x1, y1 = self._xy(x, y)
        x2, y2 = self._xy(x + w, y + h)
        if not radius:
            self.c.create_rectangle(x1, y1, x2, y2, fill=fill, outline=stroke, width=self._w)
            return
        r = radius * self.s
        pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2, x2 - r, y2,
               x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        self.c.create_polygon(pts, smooth=True, fill=fill, outline=stroke, width=self._w)

    def ellipse(self, cx, cy, rx, ry, fill, stroke):
        x, y = self._xy(cx, cy)
        self.c.create_oval(x - rx * self.s, y - ry * self.s, x + rx * self.s, y + ry * self.s,
                           fill=fill, outline=stroke, width=self._w)

    def text(self, x, y, text, color, anchor="middle", bold=False, italic=False, underline=False):
        style = " ".join(n for n, on in (("bold", bold), ("italic", italic), ("underline", underline)) if on)
        px = -max(1, round(self.size * self.s))
        font = (self.family, px, style) if style else (self.family, px)
        px, py = self._xy(x, y)
        self.c.create_text(px, py, text=text, fill=color, anchor=_ANCHOR[anchor], font=font)
