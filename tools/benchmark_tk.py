"""Tempo de redesenho na tela (Tk) com diagramas grandes. Precisa de display: python tools/benchmark_tk.py"""
import sys
import tempfile
import time
import tkinter as tk
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from jetuml_py.app.settings import Settings
from jetuml_py.model.diagram import DiagramType as DT
from jetuml_py.persistence import diagram_from_dict, diagram_to_dict
from jetuml_py.ui.app import App
from tools.benchmark import build


def main() -> None:
    root = tk.Tk()
    app = App(root, Settings(tempfile.mktemp()))
    print(f"{'nodes':>6} {'edges':>6} | {'redraw (ms)':>12} {'canvas items':>13} | {'zoom 1.56x (ms)':>16}")
    for n in (50, 150, 400, 1000):
        doc = app.new_diagram(DT.CLASS)
        doc.diagram.roots[:] = build(n).roots
        doc.diagram.edges[:] = []
        src = build(n)
        doc.diagram.roots[:] = diagram_from_dict(diagram_to_dict(src)).roots
        doc.diagram.edges[:] = diagram_from_dict(diagram_to_dict(src)).edges
        root.update()
        view = app.view
        best = min(_time(view.redraw) for _ in range(5))
        items = len(view.canvas.find_all())
        doc.zoom.level = 2
        zoomed = min(_time(view.redraw) for _ in range(3))
        print(f"{n:>6} {len(doc.diagram.edges):>6} | {best:12.1f} {items:13d} | {zoomed:16.1f}")
        app.workspace.close(doc, force=True)
    root.destroy()


def _time(fn) -> float:
    t = time.perf_counter()
    fn()
    return (time.perf_counter() - t) * 1000


if __name__ == "__main__":
    main()
