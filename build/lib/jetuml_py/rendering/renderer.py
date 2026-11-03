"""Interface de desenho (Strategy). O mesmo pintor alimenta tela (Tk), SVG e imagem (Pillow)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from xml.sax.saxutils import escape, quoteattr


class Renderer(ABC):
    @abstractmethod
    def begin(self, x: int, y: int, width: int, height: int, background: str) -> None: ...

    @abstractmethod
    def line(self, points, stroke: str, dashed: bool = False) -> None: ...

    @abstractmethod
    def polygon(self, points, fill: str, stroke: str) -> None: ...

    @abstractmethod
    def rect(self, x, y, w, h, fill: str, stroke: str, radius: int = 0) -> None: ...

    @abstractmethod
    def ellipse(self, cx, cy, rx, ry, fill: str, stroke: str) -> None: ...

    @abstractmethod
    def text(self, x, y, text: str, color: str, anchor: str = "middle", bold: bool = False,
             italic: bool = False, underline: bool = False) -> None: ...


class SvgRenderer(Renderer):
    def __init__(self, font_family: str = "Helvetica", font_px: int = 12):
        self.font_family, self.font_px = font_family, font_px

    @property
    def FONT(self) -> str:
        return f"font-family={quoteattr(self.font_family + ', Helvetica, Arial, sans-serif')} font-size=\"{self.font_px}\""

    def begin(self, x, y, width, height, background):
        self._box = (x, y, width, height)
        self._parts = [f'<rect x="{x}" y="{y}" width="{width}" height="{height}" fill={quoteattr(background)}/>']

    def line(self, points, stroke, dashed=False):
        pts = " ".join(f"{p.x},{p.y}" for p in points)
        dash = ' stroke-dasharray="6 4"' if dashed else ""
        self._parts.append(f'<polyline points="{pts}" fill="none" stroke={quoteattr(stroke)}{dash}/>')

    def polygon(self, points, fill, stroke):
        pts = " ".join(f"{p.x},{p.y}" for p in points)
        self._parts.append(f'<polygon points="{pts}" fill={quoteattr(fill)} stroke={quoteattr(stroke)}/>')

    def rect(self, x, y, w, h, fill, stroke, radius=0):
        rx = f' rx="{radius}"' if radius else ""
        self._parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}"{rx} '
                           f'fill={quoteattr(fill)} stroke={quoteattr(stroke)}/>')

    def ellipse(self, cx, cy, rx, ry, fill, stroke):
        self._parts.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" '
                           f'fill={quoteattr(fill)} stroke={quoteattr(stroke)}/>')

    def text(self, x, y, text, color, anchor="middle", bold=False, italic=False, underline=False):
        extra = (' font-weight="bold"' if bold else "") + (' font-style="italic"' if italic else "") \
                + (' text-decoration="underline"' if underline else "")
        self._parts.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" dominant-baseline="central" '
                           f'{self.FONT} fill={quoteattr(color)}{extra}>{escape(text)}</text>')

    def to_string(self) -> str:
        x, y, w, h = self._box
        body = "\n  ".join(self._parts)
        return (f'<?xml version="1.0" encoding="UTF-8"?>\n'
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="{x} {y} {w} {h}">\n'
                f'  {body}\n</svg>\n')
