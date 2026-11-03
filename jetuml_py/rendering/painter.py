"""Pintor de diagramas: traduz o modelo em chamadas ao Renderer (independente do backend)."""
from __future__ import annotations

from dataclasses import dataclass

from ..geometry import Point
from ..model.diagram import Diagram
from .edge_paths import compute_edge_paths
from .layout import apply_layout, field_text, section_height, sections, stem_end
from .renderer import Renderer, SvgRenderer
from .text import TextMetrics, parse_markup


@dataclass(frozen=True)
class Theme:
    background: str
    foreground: str
    fill: str
    note_fill: str
    grid: str


LIGHT = Theme("#ffffff", "#222222", "#ffffff", "#fff8c4", "#e6e6e6")
DARK = Theme("#1e1e1e", "#e6e6e6", "#2b2b2b", "#4a4528", "#333333")

# decoração de cada kind: (tracejada, enfeite_inicial, enfeite_final)
def edge_style(e) -> tuple[bool, str, str]:
    k, p = e.kind, e.props
    bi = p.get("directionality") == "Bidirectional"
    uni = p.get("directionality") == "Unidirectional"
    if k == "Dependency":
        return True, "open_arrow" if bi else "", "open_arrow"
    if k == "Generalization":
        return p["generalization_type"] == "Implementation", "open_arrow" if bi else "", "triangle"
    if k == "Association":
        return False, "open_arrow" if bi else "", "open_arrow" if (uni or bi) else ""
    if k == "Aggregation":
        diamond = "filled_diamond" if p["aggregation_type"] == "Composition" else "diamond"
        return False, diamond, "open_arrow" if (uni or bi) else ""
    if k == "NoteConnector":
        return True, "", ""
    if k == "Return":
        return True, "", "open_arrow"
    if k == "Reference":
        return False, "dot", "filled_arrow"
    if k in ("Call", "Transition", "Collaboration"):
        return False, "", "filled_arrow"
    if k == "UseCaseDependency":
        return p["dependency_type"] != "None", "", "open_arrow" if p["dependency_type"] != "None" else ""
    if k == "UseCaseGeneralization":
        return False, "", "triangle"
    return False, "", ""


def _unit(a: Point, b: Point) -> tuple[float, float]:
    dx, dy = b.x - a.x, b.y - a.y
    n = max((dx * dx + dy * dy) ** 0.5, 1)
    return dx / n, dy / n


class DiagramPainter:
    def __init__(self, renderer: Renderer, theme: Theme = LIGHT, metrics: TextMetrics | None = None):
        self.r, self.t, self.m = renderer, theme, metrics or TextMetrics()

    # --------------------------------------------------------------- texto
    def _text(self, x, y, line, anchor="middle", bold=False, underline=False):
        st = parse_markup(line)
        self.r.text(x, y, st.text, self.t.foreground, anchor, bold, st.italic, st.underline or underline)

    def _lines(self, x, top, lines, anchor="start", **kw):
        for i, ln in enumerate(lines):
            self._text(x, top + i * self.m.line_height + self.m.line_height // 2 + 4, ln, anchor, **kw)

    # --------------------------------------------------------------- nós
    def _boxed(self, n):
        self.r.rect(n.x, n.y, n.width, n.height, self.t.fill, self.t.foreground)
        y = n.y
        for i, lines in enumerate(sections(n)):
            h = section_height(self.m, len(lines))
            if i:
                self.r.line([Point(n.x, y), Point(n.x + n.width, y)], self.t.foreground)
            if i == 0:
                self._lines(n.x + n.width // 2, y, lines, "middle", bold=True)
            else:
                self._lines(n.x + 8, y + 2, lines)
            y += h

    _node_Class = _node_Interface = _node_PackageDescription = _boxed

    def _node_Note(self, n):
        x, y, w, h, f = n.x, n.y, n.width, n.height, 10
        pts = [Point(x, y), Point(x + w - f, y), Point(x + w, y + f), Point(x + w, y + h), Point(x, y + h)]
        self.r.polygon(pts, self.t.note_fill, self.t.foreground)
        self.r.line([Point(x + w - f, y), Point(x + w - f, y + f), Point(x + w, y + f)], self.t.foreground)
        self._lines(x + 6, y + 4, n.props["text"].split("\n") if n.props["text"] else [])

    def _node_Package(self, n):
        tab_w = max(60, self.m.width(n.props["name"]) + 20)
        self.r.rect(n.x, n.y, tab_w, 20, self.t.fill, self.t.foreground)
        self.r.rect(n.x, n.y + 20, n.width, n.height - 20, self.t.fill, self.t.foreground)
        self._text(n.x + tab_w // 2, n.y + 10, n.props["name"])

    def _node_Object(self, n):
        self.r.rect(n.x, n.y, n.width, n.height, self.t.fill, self.t.foreground)
        self._text(n.x + n.width // 2, n.y + 12, n.props["name"], bold=True, underline=True)
        self.r.line([Point(n.x, n.y + 24), Point(n.x + n.width, n.y + 24)], self.t.foreground)

    def _node_Field(self, n):
        self._text(n.x, n.y + n.height // 2, field_text(n), "start")

    def _node_Actor(self, n):
        cx, y, fg = n.x + n.width // 2, n.y, self.t.foreground
        self.r.ellipse(cx, y + 10, 8, 8, self.t.fill, fg)
        self.r.line([Point(cx, y + 18), Point(cx, y + 40)], fg)
        self.r.line([Point(cx - 14, y + 26), Point(cx + 14, y + 26)], fg)
        self.r.line([Point(cx - 12, y + 56), Point(cx, y + 40), Point(cx + 12, y + 56)], fg)
        self._text(cx, y + n.height - 10, n.props["name"])

    def _node_UseCase(self, n):
        self.r.ellipse(n.x + n.width // 2, n.y + n.height // 2, n.width // 2, n.height // 2, self.t.fill, self.t.foreground)
        self._text(n.x + n.width // 2, n.y + n.height // 2, n.props["name"])

    def _node_State(self, n):
        self.r.rect(n.x, n.y, n.width, n.height, self.t.fill, self.t.foreground, radius=12)
        self._text(n.x + n.width // 2, n.y + n.height // 2, n.props["name"])

    def _node_InitialState(self, n):
        self.r.ellipse(n.x + n.width // 2, n.y + n.height // 2, n.width // 2, n.height // 2,
                       self.t.foreground, self.t.foreground)

    def _node_FinalState(self, n):
        cx, cy = n.x + n.width // 2, n.y + n.height // 2
        self.r.ellipse(cx, cy, n.width // 2, n.height // 2, self.t.fill, self.t.foreground)
        self.r.ellipse(cx, cy, n.width // 2 - 4, n.height // 2 - 4, self.t.foreground, self.t.foreground)

    def _node_ImplicitParameter(self, n):
        self.r.rect(n.x, n.y, n.width, n.height, self.t.fill, self.t.foreground)
        self._text(n.x + n.width // 2, n.y + n.height // 2, n.props["name"], bold=True)
        cx = n.x + n.width // 2
        self.r.line([Point(cx, n.y + n.height), Point(cx, stem_end(n))], self.t.foreground, dashed=True)

    def _node_Call(self, n):
        self.r.rect(n.x, n.y, n.width, n.height, self.t.fill, self.t.foreground)
        if n.props["open_bottom"]:  # sequência incompleta: borda inferior apagada
            self.r.line([Point(n.x + 1, n.y + n.height), Point(n.x + n.width - 1, n.y + n.height)], self.t.fill)

    def _node_Point(self, n):
        pass

    # --------------------------------------------------------------- arestas
    def _decorate(self, kind: str, tip: Point, frm: Point):
        if not kind:
            return
        fg, bg = self.t.foreground, self.t.fill
        ux, uy = _unit(frm, tip)
        if kind == "dot":
            self.r.ellipse(tip.x, tip.y, 3, 3, fg, fg)
            return
        length, half = (16, 6) if "diamond" in kind else (10, 5)
        bx, by = tip.x - ux * length, tip.y - uy * length
        px, py = -uy * half, ux * half
        left, right = Point(round(bx + px), round(by + py)), Point(round(bx - px), round(by - py))
        if "diamond" in kind:
            tail = Point(round(tip.x - ux * length), round(tip.y - uy * length))
            mid = Point(round(tip.x - ux * length / 2), round(tip.y - uy * length / 2))
            pts = [tip, Point(round(mid.x + px), round(mid.y + py)), tail, Point(round(mid.x - px), round(mid.y - py))]
            self.r.polygon(pts, fg if kind == "filled_diamond" else bg, fg)
        elif kind == "open_arrow":
            self.r.line([left, tip, right], fg)
        else:
            self.r.polygon([tip, left, right], fg if kind == "filled_arrow" else bg, fg)

    def _paint_edge(self, e, pts: list[Point]):
        dashed, start_deco, end_deco = edge_style(e)
        self.r.line(pts, self.t.foreground, dashed)
        self._decorate(start_deco, pts[0], pts[1])
        self._decorate(end_deco, pts[-1], pts[-2])
        p = e.props
        mid_label = p.get("middle_label", "")
        if e.kind == "UseCaseDependency" and p["dependency_type"] != "None":
            mid_label = f"«{p['dependency_type'].lower()}»"
        i = (len(pts) - 1) // 2
        mx, my = (pts[i].x + pts[i + 1].x) // 2, (pts[i].y + pts[i + 1].y) // 2
        if mid_label:
            self._text(mx, my - 9, mid_label)
        if p.get("start_label"):
            self._text(pts[0].x + 6, pts[0].y - 9, p["start_label"], "start")
        if p.get("end_label"):
            self._text(pts[-1].x - 6, pts[-1].y - 9, p["end_label"], "end")

    # --------------------------------------------------------------- diagrama
    def paint(self, d: Diagram, show_grid: bool = False, grid_size: int = 10, area=None):
        x0, y0, w, h = area or content_bounds(d)
        self.r.begin(x0, y0, w, h, self.t.background)
        if show_grid:
            for gx in range(x0 - x0 % grid_size, x0 + w + 1, grid_size):
                self.r.line([Point(gx, y0), Point(gx, y0 + h)], self.t.grid)
            for gy in range(y0 - y0 % grid_size, y0 + h + 1, grid_size):
                self.r.line([Point(x0, gy), Point(x0 + w, gy)], self.t.grid)
        for n in d.all_nodes():
            getattr(self, f"_node_{n.TYPE}")(n)
        paths = compute_edge_paths(d)
        for e in d.edges:
            self._paint_edge(e, paths[e.id])


def content_bounds(d: Diagram, margin: int = 20):
    """Retângulo que envolve todo o conteúdo (sem grade), usado na exportação e na cópia (RF04, RF05)."""
    xs, ys = [], []
    for n in d.all_nodes():
        xs += [n.x, n.x + n.width]
        ys += [n.y, n.y + n.height + (stem_end(n) - n.y - n.height if n.TYPE == "ImplicitParameter" else 0)]
    for pts in compute_edge_paths(d).values():
        xs += [p.x for p in pts]
        ys += [p.y for p in pts]
    if not xs:
        return 0, 0, 2 * margin, 2 * margin
    x0, y0 = min(xs) - margin, min(ys) - margin
    return x0, y0, max(xs) + margin - x0, max(ys) + margin - y0


def render_svg(d: Diagram, theme: Theme = LIGHT, metrics: TextMetrics | None = None, show_grid: bool = False,
               font_family: str = "Helvetica") -> str:
    """Exportação SVG (RF04): aplica o layout e pinta o diagrama inteiro, ajustado ao conteúdo."""
    metrics = metrics or TextMetrics()
    apply_layout(d, metrics)
    svg = SvgRenderer(font_family, metrics.font_size)
    DiagramPainter(svg, theme, metrics).paint(d, show_grid=show_grid)
    return svg.to_string()


def render_image(d: Diagram, theme: Theme = LIGHT, metrics: TextMetrics | None = None,
                 font_family: str = "Helvetica"):
    """Imagem raster (Pillow) do diagrama inteiro, sem grade e ajustada ao conteúdo (RF04, RF05)."""
    from .pil_renderer import PilRenderer      # Pillow é opcional: só importado quando necessário
    metrics = metrics or TextMetrics()
    apply_layout(d, metrics)
    renderer = PilRenderer(font_family, metrics.font_size)
    DiagramPainter(renderer, theme, metrics).paint(d)
    return renderer.finish()
