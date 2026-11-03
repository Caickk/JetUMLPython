"""Teste de acerto (hit-testing) para seleção e laço (RF32). Independente de Tk."""
from __future__ import annotations

from ..geometry import Point
from .edge_paths import compute_edge_paths


def _dist(p: Point, a: Point, b: Point) -> float:
    dx, dy = b.x - a.x, b.y - a.y
    if dx == 0 and dy == 0:
        return ((p.x - a.x) ** 2 + (p.y - a.y) ** 2) ** 0.5
    t = max(0.0, min(1.0, ((p.x - a.x) * dx + (p.y - a.y) * dy) / (dx * dx + dy * dy)))
    return ((p.x - (a.x + t * dx)) ** 2 + (p.y - (a.y + t * dy)) ** 2) ** 0.5


def edge_at(d, point: Point, tol: float = 5, paths=None):
    paths = paths or compute_edge_paths(d)
    for e in reversed(d.edges):
        pts = paths[e.id]
        if any(_dist(point, pts[i], pts[i + 1]) <= tol for i in range(len(pts) - 1)):
            return e
    return None


def hit_element(d, point: Point):
    """Nó sob o ponto (prioridade) ou, se não houver, a aresta mais próxima."""
    return d.node_at(point) or edge_at(d, point)


def elements_in_rect(d, x1, y1, x2, y2):
    """Elementos totalmente contidos no retângulo do laço."""
    left, right, top, bottom = min(x1, x2), max(x1, x2), min(y1, y2), max(y1, y2)
    nodes = [n for n in d.all_nodes() if n.TYPE != "Point"
             and left <= n.x and n.x + n.width <= right and top <= n.y and n.y + n.height <= bottom]
    paths = compute_edge_paths(d)
    edges = [e for e in d.edges
             if all(left <= p.x <= right and top <= p.y <= bottom for p in paths[e.id])]
    return nodes, edges
