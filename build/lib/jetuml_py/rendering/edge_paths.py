"""Caminho automático das arestas (RF17). Recalculado a cada pintura a partir das posições dos nós,
portanto acompanha qualquer movimentação sem estado extra."""
from __future__ import annotations

from collections import defaultdict

from ..geometry import Point
from ..model.diagram import Diagram


def center(n) -> tuple[float, float]:
    return n.x + n.width / 2, n.y + n.height / 2


def rect_anchor(n, toward: tuple[float, float]) -> Point:
    """Ponto da borda do nó na direção de 'toward' (a partir do centro)."""
    cx, cy = center(n)
    dx, dy = toward[0] - cx, toward[1] - cy
    if dx == 0 and dy == 0:
        return Point(round(cx), round(cy))
    sx = (n.width / 2) / abs(dx) if dx else float("inf")
    sy = (n.height / 2) / abs(dy) if dy else float("inf")
    s = min(sx, sy)
    return Point(round(cx + dx * s), round(cy + dy * s))


def _loop(n, index: int) -> list[Point]:
    r, t, s = n.x + n.width, n.y, 20 + 12 * index
    return [Point(r - 20, t), Point(r - 20, t - s), Point(r + s, t - s), Point(r + s, t + 20), Point(r, t + 20)]


def _sequence_path(e) -> list[Point]:
    if e.kind == "Call":
        caller, callee = e.start, e.end
        if callee.TYPE == "ImplicitParameter":  # construtor
            y = callee.y + callee.height // 2
            if center(caller)[0] < center(callee)[0]:
                return [Point(caller.x + caller.width, y), Point(callee.x, y)]
            return [Point(caller.x, y), Point(callee.x + callee.width, y)]
        y = callee.y
        if callee.parent is caller.parent:  # autochamada
            r = callee.x + callee.width
            return [Point(caller.x + caller.width, y), Point(r + 25, y), Point(r + 25, y + 10), Point(r, y + 10)]
        if center(callee)[0] > center(caller)[0]:
            return [Point(caller.x + caller.width, y), Point(callee.x, y)]
        return [Point(caller.x, y), Point(callee.x + callee.width, y)]
    callee, caller = e.start, e.end  # Return
    y = callee.y + callee.height
    if callee.parent is caller.parent:
        return [Point(callee.x + callee.width, y), Point(caller.x + caller.width, y)]
    if center(callee)[0] > center(caller)[0]:
        return [Point(callee.x, y), Point(caller.x + caller.width, y)]
    return [Point(callee.x + callee.width, y), Point(caller.x, y)]


def _reference_path(e) -> list[Point]:
    f, obj = e.start, e.end
    start = Point(f.x + f.width, f.y + f.height // 2)
    if obj is f.parent:  # referência para o próprio objeto
        return [start, Point(start.x + 20, start.y), Point(start.x + 20, obj.y + obj.height + 15),
                Point(obj.x + obj.width // 2, obj.y + obj.height + 15), Point(obj.x + obj.width // 2, obj.y + obj.height)]
    return [start, rect_anchor(obj, (start.x, start.y))]


def compute_edge_paths(d: Diagram) -> dict[str, list[Point]]:
    paths: dict[str, list[Point]] = {}
    groups = defaultdict(list)
    loops = defaultdict(int)
    for e in d.edges:
        if e.kind in ("Call", "Return"):
            paths[e.id] = _sequence_path(e)
        elif e.kind == "Reference":
            paths[e.id] = _reference_path(e)
        elif e.start is e.end:
            paths[e.id] = _loop(e.start, loops[e.start.id])
            loops[e.start.id] += 1
        else:
            groups[frozenset((e.start.id, e.end.id))].append(e)
    for edges in groups.values():
        a, b = sorted((edges[0].start, edges[0].end), key=lambda n: n.id)  # referência comum aos dois sentidos
        (ax, ay), (bx, by) = center(a), center(b)
        length = max(((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5, 1)
        nx, ny = -(by - ay) / length, (bx - ax) / length
        for i, e in enumerate(edges):
            off = (i - (len(edges) - 1) / 2) * 14
            sc = (center(e.start)[0] + nx * off, center(e.start)[1] + ny * off)
            ec = (center(e.end)[0] + nx * off, center(e.end)[1] + ny * off)
            paths[e.id] = [rect_anchor(e.start, ec), rect_anchor(e.end, sc)]
    return paths
