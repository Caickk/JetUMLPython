"""Backend Pillow do Renderer: gera imagens PNG/JPEG etc. (RF04) e a imagem copiada (RF05).

Desenha em escala 2x e reduz ao final (suavização). Pillow é a única dependência externa do projeto.
"""
from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

from .renderer import Renderer

SCALE = 2
_ANCHOR = {"start": "lm", "middle": "mm", "end": "rm"}
# Arquivos de fonte procurados (regular, negrito, itálico, negrito+itálico); o Pillow consulta as pastas do sistema.
_FONT_FILES = {
    "regular": ["arial.ttf", "Arial.ttf", "LiberationSans-Regular.ttf", "DejaVuSans.ttf", "Helvetica.ttc"],
    "bold": ["arialbd.ttf", "Arial Bold.ttf", "LiberationSans-Bold.ttf", "DejaVuSans-Bold.ttf"],
    "italic": ["ariali.ttf", "Arial Italic.ttf", "LiberationSans-Italic.ttf", "DejaVuSans-Oblique.ttf"],
    "bolditalic": ["arialbi.ttf", "Arial Bold Italic.ttf", "LiberationSans-BoldItalic.ttf", "DejaVuSans-BoldOblique.ttf"],
}


class PilRenderer(Renderer):
    def __init__(self, font_family: str = "Helvetica", font_px: int = 12):
        self.font_family, self.font_px = font_family, font_px
        self._fonts: dict[str, ImageFont.ImageFont] = {}
        self.image = None

    def _font(self, bold: bool, italic: bool):
        key = ("bold" if bold else "") + ("italic" if italic else "") or "regular"
        if key not in self._fonts:
            size = self.font_px * SCALE
            names = [f"{self.font_family}.ttf"] if key == "regular" and self.font_family not in ("Helvetica", "Arial") else []
            for name in names + _FONT_FILES[key] + _FONT_FILES["regular"]:
                try:
                    self._fonts[key] = ImageFont.truetype(name, size)
                    break
                except OSError:
                    continue
            else:
                self._fonts[key] = ImageFont.load_default(size)   # sem negrito/itálico reais
        return self._fonts[key]

    def _pt(self, x, y):
        return (x - self._ox) * SCALE, (y - self._oy) * SCALE

    def _flat(self, points):
        return [v for p in points for v in self._pt(p.x, p.y)]

    def begin(self, x, y, width, height, background):
        self._ox, self._oy, self._w, self._h = x, y, int(width), int(height)
        self.image = Image.new("RGB", (self._w * SCALE, self._h * SCALE), background)
        self.draw = ImageDraw.Draw(self.image)

    def line(self, points, stroke, dashed=False):
        pts = self._flat(points)
        if not dashed:
            self.draw.line(pts, fill=stroke, width=SCALE)
            return
        on, off = 6 * SCALE, 4 * SCALE
        for (x1, y1), (x2, y2) in zip(zip(pts[0::2], pts[1::2]), zip(pts[2::2], pts[3::2])):
            length = max(((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5, 1e-9)
            ux, uy, pos = (x2 - x1) / length, (y2 - y1) / length, 0.0
            while pos < length:
                end = min(pos + on, length)
                self.draw.line([x1 + ux * pos, y1 + uy * pos, x1 + ux * end, y1 + uy * end], fill=stroke, width=SCALE)
                pos += on + off

    def polygon(self, points, fill, stroke):
        pts = self._flat(points)
        self.draw.polygon(pts, fill=fill)
        self.draw.line(pts + pts[:2], fill=stroke, width=SCALE)

    def rect(self, x, y, w, h, fill, stroke, radius=0):
        (x1, y1), (x2, y2) = self._pt(x, y), self._pt(x + w, y + h)
        if radius:
            self.draw.rounded_rectangle([x1, y1, x2, y2], radius * SCALE, fill=fill, outline=stroke, width=SCALE)
        else:
            self.draw.rectangle([x1, y1, x2, y2], fill=fill, outline=stroke, width=SCALE)

    def ellipse(self, cx, cy, rx, ry, fill, stroke):
        x, y = self._pt(cx, cy)
        self.draw.ellipse([x - rx * SCALE, y - ry * SCALE, x + rx * SCALE, y + ry * SCALE],
                          fill=fill, outline=stroke, width=SCALE)

    def text(self, x, y, text, color, anchor="middle", bold=False, italic=False, underline=False):
        font = self._font(bold, italic)
        px, py = self._pt(x, y)
        self.draw.text((px, py), text, font=font, fill=color, anchor=_ANCHOR[anchor])
        if underline:
            width = self.draw.textlength(text, font=font)
            left = {"start": px, "middle": px - width / 2, "end": px - width}[anchor]
            base = py + self.font_px * SCALE * 0.55
            self.draw.line([left, base, left + width, base], fill=color, width=SCALE)

    def finish(self):
        """Imagem final no tamanho do diagrama (reduz o supersampling)."""
        return self.image.resize((self._w, self._h), Image.LANCZOS)
