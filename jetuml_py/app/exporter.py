"""Exportação do diagrama como imagem (RF04): SVG sem dependências; PNG/JPEG e outros via Pillow."""
from __future__ import annotations

from pathlib import Path

from ..rendering.painter import LIGHT, render_image, render_svg
from ..rendering.text import TextMetrics

RASTER = {".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG", ".gif": "GIF", ".bmp": "BMP",
          ".tif": "TIFF", ".tiff": "TIFF", ".webp": "WEBP"}


class ExportError(Exception):
    pass


def pillow_available() -> bool:
    try:
        import PIL  # noqa: F401
        return True
    except ImportError:
        return False


def supported_extensions() -> list[str]:
    """Extensões oferecidas em 'Save as type' (RF04)."""
    return [".svg"] + (list(RASTER) if pillow_available() else [])


def export_diagram(diagram, path, metrics: TextMetrics | None = None, font_family: str = "Helvetica") -> None:
    """O formato é definido pela extensão. Sempre em tema claro, sem grade, ajustado ao conteúdo."""
    path = Path(path)
    ext = path.suffix.lower()
    if ext == ".svg":
        path.write_text(render_svg(diagram, LIGHT, metrics, font_family=font_family), encoding="utf-8")
        return
    if ext not in RASTER:
        raise ExportError(f"Unsupported image format: {ext or '(no extension)'}")
    if not pillow_available():
        raise ExportError("Exporting PNG/JPEG requires the Pillow package (pip install pillow); SVG works without it")
    image = render_image(diagram, LIGHT, metrics, font_family)
    try:
        image.save(path, format=RASTER[ext])
    except OSError as exc:
        raise ExportError(f"Cannot write {path.name}: {exc}") from exc
