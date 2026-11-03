import unittest
import xml.etree.ElementTree as ET

from jetuml_py.geometry import Point
from jetuml_py.model.diagram import DiagramType as DT
from jetuml_py.rendering.edge_paths import compute_edge_paths
from jetuml_py.rendering.layout import apply_layout
from jetuml_py.rendering.painter import DARK, LIGHT, content_bounds, render_svg
from jetuml_py.rendering.text import parse_markup
from tests.helpers import make_editor, tool

NS = "{http://www.w3.org/2000/svg}"


def svg_root(d, **kw):
    return ET.fromstring(render_svg(d, **kw).encode("utf-8"))


class Markup(unittest.TestCase):
    def test_italic_underline_and_plain(self):
        self.assertEqual(parse_markup("/Shape/").italic, True)
        self.assertEqual(parse_markup("/Shape/").text, "Shape")
        self.assertTrue(parse_markup("_count_").underline)
        self.assertEqual(parse_markup("a/b/").text, "a/b/")
        self.assertFalse(parse_markup("/").italic)


class Layout(unittest.TestCase):
    def test_class_grows_with_content(self):
        ed = make_editor(DT.CLASS)
        c = ed.add_node("Class", 0, 0)
        apply_layout(ed.diagram)
        w0, h0 = c.width, c.height
        ed.set_property(c, "name", "AVeryLongClassNameForTheLayoutTest")
        ed.set_property(c, "methods", "a()\nb()\nc()")
        apply_layout(ed.diagram)
        self.assertGreater(c.width, w0)
        self.assertGreater(c.height, h0)

    def test_package_grows_to_contain_children_and_layout_is_idempotent(self):
        ed = make_editor(DT.CLASS)
        pkg = ed.add_node("Package", 0, 0)
        c = ed.add_node("Class", 10, 10)
        ed.move([c], 300, 200)
        apply_layout(ed.diagram)
        self.assertGreaterEqual(pkg.x + pkg.width, c.x + c.width)
        self.assertGreaterEqual(pkg.y + pkg.height, c.y + c.height)
        before = (pkg.width, pkg.height)
        apply_layout(ed.diagram)
        self.assertEqual(before, (pkg.width, pkg.height))

    def test_object_stacks_fields(self):
        ed = make_editor(DT.OBJECT)
        o = ed.add_node("Object", 0, 0)
        f1, f2 = ed.add_node("Field", 5, 5), ed.add_node("Field", 5, 5)
        ed.set_property(f1, "name", "a")
        apply_layout(ed.diagram)
        self.assertLess(f1.y, f2.y)
        self.assertGreaterEqual(o.y + o.height, f2.y + f2.height)

    def test_sequence_layout_order_alignment_and_nesting(self):
        ed = make_editor(DT.SEQUENCE)
        l1, l2, l3 = (ed.add_node("ImplicitParameter", x, 0) for x in (0, 200, 400))
        e1 = ed.connect(tool(ed, "Call"), l1, l2)
        b1, b2 = e1.start, e1.end
        selfcall = ed.add_call(b2, b2)
        ed.connect(tool(ed, "Return"), selfcall.end, b2)
        ctor = ed.add_call(b2, l3, constructor=True)
        ed.connect(tool(ed, "Return"), b2, b1)
        apply_layout(ed.diagram)
        self.assertLess(b1.y, b2.y)
        self.assertLessEqual(b2.y + 15, selfcall.end.y)
        self.assertEqual(selfcall.end.x, b2.x + 8)            # caixa aninhada deslocada
        self.assertEqual(l3.y + l3.height // 2, compute_edge_paths(ed.diagram)[ctor.id][0].y)  # RF29
        self.assertGreaterEqual(b1.y + b1.height, b2.y + b2.height)
        ret = [e for e in ed.diagram.edges if e.kind == "Return" and e.start is b2][0]
        self.assertEqual(compute_edge_paths(ed.diagram)[ret.id][0].y, b2.y + b2.height)


class EdgePaths(unittest.TestCase):
    def setUp(self):
        self.ed = make_editor(DT.STATE)
        self.s1, self.s2 = self.ed.add_node("State", 0, 0), self.ed.add_node("State", 300, 0)
        apply_layout(self.ed.diagram)

    def test_endpoints_on_borders(self):
        e = self.ed.connect(tool(self.ed, "Transition"), self.s1, self.s2)
        p = compute_edge_paths(self.ed.diagram)[e.id]
        self.assertEqual((p[0].x, p[1].x), (self.s1.width, 300))

    def test_path_follows_node_movement(self):
        e = self.ed.connect(tool(self.ed, "Transition"), self.s1, self.s2)
        before = compute_edge_paths(self.ed.diagram)[e.id]
        self.ed.move([self.s2], 0, 200)
        self.assertNotEqual(before, compute_edge_paths(self.ed.diagram)[e.id])   # RF17

    def test_parallel_and_self_edges_do_not_overlap(self):
        t = tool(self.ed, "Transition")
        a = self.ed.connect(t, self.s1, self.s2)
        b = self.ed.connect(t, self.s2, self.s1)
        s = self.ed.connect(t, self.s1, self.s1)
        paths = compute_edge_paths(self.ed.diagram)
        self.assertNotEqual(paths[a.id][0].y, paths[b.id][1].y)
        self.assertGreater(len(paths[s.id]), 2)

    def test_note_anchor_ends_at_point(self):
        note = self.ed.add_node("Note", 0, 200)
        edge = self.ed.anchor_note(note, 500, 500)
        self.assertEqual(compute_edge_paths(self.ed.diagram)[edge.id][-1], Point(500, 500))


class SvgOutput(unittest.TestCase):
    def build_class_diagram(self):
        ed = make_editor(DT.CLASS)
        a, b, i = ed.add_node("Class", 0, 0), ed.add_node("Class", 300, 0), ed.add_node("Interface", 300, 200)
        ed.set_property(a, "name", "/Shape/")
        ed.set_property(a, "attributes", "_count_\nname")
        ed.set_property(b, "name", "A & B <x>")
        ed.connect(tool(ed, "Composition"), a, b)
        ed.connect(tool(ed, "Realization"), b, i)
        ed.anchor_note(ed.add_node("Note", 0, 300), 200, 450)
        return ed.diagram

    def test_well_formed_with_expected_primitives(self):
        root = svg_root(self.build_class_diagram())
        texts = [t for t in root.iter(f"{NS}text")]
        self.assertTrue(any(t.get("font-style") == "italic" and t.text == "Shape" for t in texts))
        self.assertTrue(any(t.get("text-decoration") == "underline" and t.text == "count" for t in texts))
        self.assertTrue(any(t.text == "A & B <x>" for t in texts))      # escapado corretamente
        self.assertTrue(any(t.text == "«interface»" for t in texts))
        self.assertGreaterEqual(len(list(root.iter(f"{NS}polygon"))), 3)   # losango, triângulo, nota
        self.assertTrue(any(p.get("stroke-dasharray") for p in root.iter(f"{NS}polyline")))

    def test_composition_filled_aggregation_hollow(self):
        for kind, filled in (("Composition", True), ("Aggregation", False)):
            ed = make_editor(DT.CLASS)
            a, b = ed.add_node("Class", 0, 0), ed.add_node("Class", 300, 0)
            ed.connect(tool(ed, kind), a, b)
            polys = list(svg_root(ed.diagram).iter(f"{NS}polygon"))
            self.assertEqual(polys[0].get("fill") == LIGHT.foreground, filled, kind)

    def test_grid_only_when_requested_and_dark_theme(self):
        d = self.build_class_diagram()
        self.assertNotIn(LIGHT.grid, render_svg(d))
        self.assertIn(LIGHT.grid, render_svg(d, show_grid=True))
        self.assertIn(DARK.background, render_svg(d, theme=DARK))

    def test_content_bounds_enclose_everything(self):
        d = self.build_class_diagram()
        apply_layout(d)
        x, y, w, h = content_bounds(d)
        for n in d.all_nodes():
            self.assertTrue(x <= n.x and n.x + n.width <= x + w and y <= n.y and n.y + n.height <= y + h)

    def test_every_diagram_type_renders(self):
        for dtype, nodes in ((DT.OBJECT, ["Object", "Field"]), (DT.USE_CASE, ["Actor", "UseCase"]),
                             (DT.STATE, ["InitialState", "State", "FinalState"]),
                             (DT.SEQUENCE, ["ImplicitParameter"])):
            ed = make_editor(dtype)
            for i, n in enumerate(nodes):
                ed.add_node(n, 20 + i * 5, 20 + i * 120) if n == "Field" else ed.add_node(n, i * 200, 0)
            self.assertEqual(svg_root(ed.diagram).tag, f"{NS}svg", dtype)

    def test_sequence_and_object_diagrams_with_edges(self):
        ed = make_editor(DT.SEQUENCE)
        l1, l2 = ed.add_node("ImplicitParameter", 0, 0), ed.add_node("ImplicitParameter", 200, 0)
        e = ed.connect(tool(ed, "Call"), l1, l2)
        ed.set_property(e, "middle_label", "doIt()")
        ed.connect(tool(ed, "Return"), e.end, e.start)
        root = svg_root(ed.diagram)
        self.assertTrue(any(t.text == "doIt()" for t in root.iter(f"{NS}text")))
        oed = make_editor(DT.OBJECT)
        o1, o2 = oed.add_node("Object", 0, 0), oed.add_node("Object", 300, 0)
        f = oed.add_node("Field", 20, 20)
        oed.connect(tool(oed, "Reference"), f, o2)
        self.assertEqual(svg_root(oed.diagram).tag, f"{NS}svg")


if __name__ == "__main__":
    unittest.main()
