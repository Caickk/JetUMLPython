"""Tamanho da área do diagrama (RF38, RNF01). Os valores padrão são relativos ao tamanho da tela."""
from __future__ import annotations

MIN_SIZE, MAX_SIZE = 250, 4000


def clamp(value: float) -> int:
    return int(max(MIN_SIZE, min(MAX_SIZE, round(value))))


def default_size(screen_width: int, screen_height: int) -> tuple[int, int]:
    """RNF01: o tamanho inicial acompanha a tela, evitando áreas enormes (desempenho) em telas pequenas."""
    return clamp(screen_width), clamp(screen_height)


def configured_size(settings, screen_width: int, screen_height: int) -> tuple[int, int]:
    return settings.diagram_size or default_size(screen_width, screen_height)


def effective_area(configured: tuple[int, int], content_right: float, content_bottom: float) -> tuple[int, int]:
    """Ao abrir um diagrama maior que a área configurada, a área cresce para comportá-lo (RF38)."""
    return max(configured[0], int(content_right)), max(configured[1], int(content_bottom))


def validate_size(width: float, height: float) -> str | None:
    """Mensagem de erro, ou None se válido."""
    if not (MIN_SIZE <= width <= MAX_SIZE and MIN_SIZE <= height <= MAX_SIZE):
        return f"Diagram size must be between {MIN_SIZE} and {MAX_SIZE} pixels"
    return None
