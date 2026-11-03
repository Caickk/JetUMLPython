"""Marcação de texto (RF24) e métricas de texto injetáveis (o backend Tk fornecerá as reais)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class StyledText:
    text: str
    italic: bool = False
    underline: bool = False


def parse_markup(line: str) -> StyledText:
    """/texto/ -> itálico (abstrato); _texto_ -> sublinhado (estático). Vale para a linha inteira."""
    if len(line) >= 2 and line[0] == "/" and line[-1] == "/":
        return StyledText(line[1:-1], italic=True)
    if len(line) >= 2 and line[0] == "_" and line[-1] == "_":
        return StyledText(line[1:-1], underline=True)
    return StyledText(line)


class TextMetrics:
    """Estimativa proporcional ao tamanho da fonte (7 px por caractere e linha de 16 px a 12 px);
    o backend Tk substitui a largura por medidas reais."""

    def __init__(self, font_size: int = 12):
        self.font_size = font_size
        self.char_width = font_size * 7 / 12
        self.line_height = round(font_size * 4 / 3)

    def width(self, line: str) -> int:
        return round(len(parse_markup(line).text) * self.char_width)
