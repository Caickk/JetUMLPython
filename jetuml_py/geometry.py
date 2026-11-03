"""Tipos geométricos básicos, independentes de qualquer toolkit gráfico."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Point:
    x: int
    y: int


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    width: int
    height: int

    def contains(self, p: Point) -> bool:
        return self.x <= p.x <= self.x + self.width and self.y <= p.y <= self.y + self.height
