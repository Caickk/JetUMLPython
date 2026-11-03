"""Mede o custo das operações que rodam a cada movimento do mouse (RNF01). Uso: python tools/benchmark.py"""
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jetuml_py.editor import DiagramEditor
from jetuml_py.model.diagram import Diagram, DiagramType as DT
from jetuml_py.geometry import Point
from jetuml_py.rendering.edge_paths import compute_edge_paths
from jetuml_py.rendering.hit import hit_element
from jetuml_py.rendering.layout import apply_layout
from jetuml_py.rendering.painter import DiagramPainter, LIGHT, content_bounds, render_svg
from jetuml_py.rendering.renderer import SvgRenderer
from jetuml_py.tools import tool_by_name


def build(n_nodes: int, seed: int = 1) -> Diagram:
    rnd = random.Random(seed)
    ed = DiagramEditor(Diagram(DT.CLASS))
    cols = max(1, int(n_nodes ** 0.5))
    nodes = [ed.add_node("Class", 40 + (i % cols) * 160, 40 + (i // cols) * 120) for i in range(n_nodes)]
    for i, n in enumerate(nodes):
        ed.set_property(n, "name", f"Class{i}")
    assoc = tool_by_name(DT.CLASS, "Association")
    made = 0
    while made < int(n_nodes * 1.5):
        a, b = rnd.sample(nodes, 2)
        made += 1 if ed.connect(assoc, a, b) else 0
    ed.notifier.duration = 0
    return ed.diagram


def timed(fn, repeat=5):
    best = float("inf")
    for _ in range(repeat):
        t = time.perf_counter()
        fn()
        best = min(best, time.perf_counter() - t)
    return best * 1000


def main() -> None:
    print(f"{'nodes':>6} {'edges':>6} | {'layout':>8} {'paths':>8} {'bounds':>8} {'paint':>8} {'hit':>8} | {'per mouse-move':>14}")
    for n in (50, 150, 400, 1000):
        d = build(n)
        apply_layout(d)
        layout = timed(lambda: apply_layout(d))
        paths = timed(lambda: compute_edge_paths(d))
        bounds = timed(lambda: content_bounds(d))

        def paint():
            DiagramPainter(SvgRenderer(), LIGHT).paint(d)
        paint_ms = timed(paint)
        hit = timed(lambda: hit_element(d, Point(5, 5)))
        frame = layout + bounds + paint_ms + paths   # um redesenho completo (como no arraste)
        print(f"{n:>6} {len(d.edges):>6} | {layout:7.1f}ms {paths:7.1f}ms {bounds:7.1f}ms {paint_ms:7.1f}ms {hit:7.1f}ms | {frame:11.1f} ms")


if __name__ == "__main__":
    main()
