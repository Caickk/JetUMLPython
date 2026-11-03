"""Guardas de desempenho (RNF01) com folga grande: pegam regressões de complexidade, não variações de máquina."""
import time
import unittest

from jetuml_py.geometry import Point
from jetuml_py.rendering.edge_paths import compute_edge_paths
from jetuml_py.rendering.hit import hit_element
from jetuml_py.rendering.layout import apply_layout
from jetuml_py.rendering.painter import render_svg
from tools.benchmark import build

try:
    import tkinter as tk
    _probe = tk.Tk()
    _probe.destroy()
    HAS_TK = True
except Exception:
    HAS_TK = False


def elapsed(fn) -> float:
    start = time.perf_counter()
    fn()
    return time.perf_counter() - start


class Headless(unittest.TestCase):
    def test_large_diagram_operations_stay_fast_and_scale_roughly_linearly(self):
        small, large = build(100), build(400)
        for d in (small, large):
            apply_layout(d)
        t_small = min(elapsed(lambda: compute_edge_paths(small)) for _ in range(3))
        t_large = min(elapsed(lambda: compute_edge_paths(large)) for _ in range(3))
        self.assertLess(t_large, 0.5)                          # medido: ~3 ms
        self.assertLess(t_large, 40 * max(t_small, 1e-4))      # 4x os elementos: longe de crescimento quadrático
        self.assertLess(elapsed(lambda: render_svg(large)), 1.5)            # medido: ~25 ms
        self.assertLess(elapsed(lambda: hit_element(large, Point(5, 5))), 0.5)


@unittest.skipUnless(HAS_TK, "Tkinter/display indisponível")
class OnScreen(unittest.TestCase):
    def test_text_width_is_measured_once_per_string(self):
        from jetuml_py.ui.tk_renderer import TkTextMetrics
        root = tk.Tk()
        try:
            m = TkTextMetrics("Helvetica", 12)
            calls = []
            real = m._font.measure
            m._font.measure = lambda text, *a, **k: (calls.append(text), real(text, *a, **k))[1]
            widths = {m.width("hello") for _ in range(50)}
            self.assertEqual(len(widths), 1)
            self.assertEqual(len(calls), 1)                    # as demais vieram da memória
            self.assertEqual(m.width("/hello/"), m.width("hello"))   # marcação não conta na largura
        finally:
            root.destroy()

    def test_redraw_of_400_nodes_is_interactive(self):
        import tempfile
        from jetuml_py.app.settings import Settings
        from jetuml_py.model.diagram import DiagramType as DT
        from jetuml_py.persistence import diagram_from_dict, diagram_to_dict
        from jetuml_py.ui.app import App
        root = tk.Tk()
        try:
            app = App(root, Settings(tempfile.mktemp()))
            doc = app.new_diagram(DT.CLASS)
            copy = diagram_from_dict(diagram_to_dict(build(400)))
            doc.diagram.roots[:] = copy.roots
            doc.diagram.edges[:] = copy.edges
            root.update()
            app.view.redraw()                                  # aquece as medidas de texto
            self.assertLess(min(elapsed(app.view.redraw) for _ in range(3)), 0.5)   # medido: ~30 ms
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
