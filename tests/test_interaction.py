import unittest

from jetuml_py.model.diagram import DiagramType as DT
from jetuml_py.rendering.hit import edge_at
from jetuml_py.rendering.layout import apply_layout
from jetuml_py import sequence_flow as sf
from jetuml_py.geometry import Point
from tests.helpers import click, drag, make_controller, use


def mid(n):
    return n.x + n.width // 2, n.y + n.height // 2


class SelectionAndMove(unittest.TestCase):
    def setUp(self):
        self.c = make_controller(DT.CLASS)
        self.ed = self.c.editor
        self.a = self.ed.add_node("Class", 0, 0)
        self.b = self.ed.add_node("Class", 300, 0)
        self.ed.connect(self.c.tool and __import__("tests.helpers", fromlist=["tool_by_name"]).tool_by_name(DT.CLASS, "Association"), self.a, self.b)

    def test_click_selects_toggles_and_ctrl_adds(self):
        click(self.c, 50, 30)
        self.assertEqual(self.c.selection.nodes, [self.a])
        click(self.c, 50, 30)                                  # clicar de novo desseleciona (RF32)
        self.assertEqual(self.c.selection.nodes, [])
        click(self.c, 50, 30)
        click(self.c, 350, 30, ctrl=True)
        self.assertEqual(len(self.c.selection.nodes), 2)
        click(self.c, 50, 30, ctrl=True)                       # Ctrl+clique remove
        self.assertEqual(self.c.selection.nodes, [self.b])
        click(self.c, 200, 300)                                # espaço vazio limpa
        self.assertTrue(self.c.selection.is_empty)

    def test_click_on_edge_selects_it(self):
        click(self.c, 200, 30)
        self.assertEqual(len(self.c.selection.edges), 1)

    def test_lasso_selects_contained_elements_only(self):
        drag(self.c, -20, -20, 150, 100)
        self.assertEqual(self.c.selection.nodes, [self.a])
        self.assertEqual(self.c.selection.edges, [])
        drag(self.c, -20, -20, 500, 100)
        self.assertEqual((len(self.c.selection.nodes), len(self.c.selection.edges)), (2, 1))

    def test_lasso_overlay_exists_only_during_gesture(self):
        self.c.press(-20, -20)
        self.c.drag(100, 100)
        self.assertEqual(self.c.overlay.lasso, (-20, -20, 100, 100))
        self.c.release(100, 100)
        self.assertIsNone(self.c.overlay.lasso)

    def test_drag_moves_with_snap_live_and_is_one_undo_step(self):
        click(self.c, 50, 30)
        self.c.press(50, 30)
        self.c.drag(84, 63)
        self.assertEqual((self.a.x, self.a.y), (30, 30))       # visível durante o arrasto
        self.c.release(84, 63)
        self.assertEqual((self.a.x, self.a.y), (30, 30))
        self.assertTrue(self.ed.undo())
        self.assertEqual((self.a.x, self.a.y), (0, 0))

    def test_press_release_without_movement_does_not_move(self):
        before = len(self.ed.undo_manager._undo)
        click(self.c, 50, 30)
        self.assertEqual(len(self.ed.undo_manager._undo), before)

    def test_cancel_restores_positions(self):
        click(self.c, 50, 30)
        self.c.press(50, 30)
        self.c.drag(150, 130)
        self.assertNotEqual(self.a.x, 0)
        self.c.cancel()
        self.assertEqual((self.a.x, self.a.y), (0, 0))

    def test_children_move_once_and_layout_owned_nodes_stay(self):
        c = make_controller(DT.CLASS)
        pkg = c.editor.add_node("Package", 0, 0)
        child = c.editor.add_node("Class", 20, 20)
        c.selection.set([pkg, child])
        c.press(5, 5); c.drag(5 + 40, 5); c.release(45, 5)
        self.assertEqual((pkg.x, child.x), (40, 60))
        o = make_controller(DT.OBJECT)
        obj = o.editor.add_node("Object", 0, 0)
        field = o.editor.add_node("Field", 5, 5)
        apply_layout(o.diagram)
        fx, fy = mid(field)
        click(o, fx, fy)
        self.assertEqual(o.selection.nodes, [field])
        before = (field.x, field.y)
        o.press(fx, fy); o.drag(fx + 50, fy + 50); o.release(fx + 50, fy + 50)
        self.assertEqual((field.x, field.y), before)


class ShiftContainment(unittest.TestCase):
    def test_shift_drop_attaches_and_detaches(self):
        c = make_controller(DT.CLASS)
        pkg = c.editor.add_node("Package", 0, 0)
        x = c.editor.add_node("Class", 400, 400)
        click(c, 450, 430)
        drag(c, 450, 430, 80, 60)                                # sem Shift: só move
        self.assertIsNone(x.parent)
        drag(c, 80, 60, 90, 70, shift=True)                      # Shift sobre o pacote: anexa
        self.assertIs(x.parent, pkg)
        drag(c, x.x + 10, x.y + 10, 560, 560)                    # sem Shift: continua filho
        self.assertIs(x.parent, pkg)
        drag(c, x.x + 10, x.y + 10, 300, 300, shift=True)       # Shift fora do pacote (sem o filho): desanexa
        self.assertIsNone(x.parent)


class NodeCreation(unittest.TestCase):
    def test_click_creates_snapped_selected_node_and_notifies(self):
        c = make_controller(DT.CLASS)
        made = []
        c.on_node_created = made.append
        use(c, "Class")
        click(c, 203, 57)
        node = c.diagram.roots[0]
        self.assertEqual((node.x, node.y), (200, 60))
        self.assertEqual(c.selection.nodes, [node])
        self.assertEqual(made, [node])

    def test_no_creation_on_top_of_other_node_but_inside_package(self):
        c = make_controller(DT.CLASS)
        use(c, "Package"); click(c, 0, 0)
        use(c, "Class"); click(c, 50, 50)
        pkg, cls = c.diagram.roots[0], c.diagram.roots[0].children[0]
        self.assertIs(cls.parent, pkg)
        click(c, cls.x + 10, cls.y + 10)                         # em cima de uma classe: nada
        self.assertEqual(len(pkg.children), 1)
        use(c, "Note"); click(c, 400, 400)
        self.assertEqual(len(c.diagram.roots), 2)

    def test_field_only_inside_object(self):
        c = make_controller(DT.OBJECT)
        use(c, "Object"); click(c, 10, 10)
        use(c, "Field"); click(c, 400, 400)
        self.assertEqual(len(list(c.diagram.all_nodes())), 1)
        self.assertEqual(len(c.editor.notifier.active()), 1)     # erro notificado (RF25)
        click(c, 30, 30)
        self.assertEqual(len(c.diagram.roots[0].children), 1)
        click(c, 30, 30)                                         # sobre o campo existente: outro campo
        self.assertEqual(len(c.diagram.roots[0].children), 2)


class EdgeCreation(unittest.TestCase):
    def setUp(self):
        self.c = make_controller(DT.CLASS)
        self.a = self.c.editor.add_node("Class", 0, 0)
        self.b = self.c.editor.add_node("Class", 300, 0)

    def test_rubber_band_creates_edge_and_overlay_is_temporary(self):
        use(self.c, "Association")
        self.c.press(50, 30)
        self.assertEqual(self.c.overlay.rubber, (50, 30, 50, 30))
        self.c.drag(200, 30)
        self.assertEqual(self.c.overlay.rubber, (50, 30, 200, 30))
        self.c.release(350, 30)
        self.assertIsNone(self.c.overlay.rubber)
        edge = self.c.diagram.edges[0]
        self.assertEqual((edge.start, edge.end), (self.a, self.b))
        self.assertEqual(self.c.selection.edges, [edge])

    def test_click_without_drag_or_release_in_empty_space_does_nothing(self):
        use(self.c, "Association")
        click(self.c, 50, 30)
        drag(self.c, 50, 30, 200, 300)
        self.assertEqual(self.c.diagram.edges, [])
        self.assertEqual(len(self.c.editor.notifier.active()), 0)

    def test_self_edge_by_dragging_inside_node_and_blocked_self_inheritance(self):
        use(self.c, "Association")
        drag(self.c, 30, 20, 70, 45)
        self.assertIs(self.c.diagram.edges[0].start, self.c.diagram.edges[0].end)
        use(self.c, "Inheritance")
        drag(self.c, 30, 20, 70, 45)
        self.assertEqual(len(self.c.diagram.edges), 1)
        self.assertEqual(len(self.c.editor.notifier.active()), 1)

    def test_invalid_connection_reports_error(self):
        use(self.c, "Association")
        drag(self.c, 50, 30, 350, 30)
        drag(self.c, 350, 30, 50, 30)                            # duplicada (qualquer sentido)
        self.assertEqual(len(self.c.diagram.edges), 1)
        self.assertEqual(len(self.c.editor.notifier.active()), 1)

    def test_note_connector_node_to_note_and_note_to_point(self):
        use(self.c, "Note"); click(self.c, 500, 300)
        note = self.c.diagram.roots[-1]
        use(self.c, "Note Connector")
        drag(self.c, 50, 30, note.x + 10, note.y + 10)
        self.assertEqual(self.c.diagram.edges[0].end, note)
        drag(self.c, note.x + 10, note.y + 10, 700, 500)
        anchored = self.c.diagram.edges[1]
        self.assertEqual((anchored.end.TYPE, anchored.end.x, anchored.end.y), ("Point", 700, 500))
        click(self.c, 700, 500)                                  # âncora não é selecionável
        self.assertEqual(self.c.selection.nodes, [])


class SequenceInteraction(unittest.TestCase):
    def test_call_constructor_selfcall_and_return_by_dragging(self):
        c = make_controller(DT.SEQUENCE)
        l1, l2, l3 = (c.editor.add_node("ImplicitParameter", x, 0) for x in (0, 200, 400))
        use(c, "Call")
        drag(c, 40, 20, 240, 60)                                 # cabeçalho de L1 -> corpo de L2
        edge = c.diagram.edges[0]
        b1, b2 = edge.start, edge.end
        self.assertEqual(edge.props["middle_label"], "")
        apply_layout(c.diagram)
        x, y = mid(b2)
        drag(c, x, y, 440, 20)                                   # caixa -> cabeçalho de L3: construtor
        ctor = c.diagram.edges[1]
        self.assertEqual((ctor.end, ctor.props["middle_label"]), (l3, "«create»"))
        apply_layout(c.diagram)
        x, y = mid(b2)
        drag(c, x, y - 5, x, y + 15)                             # dentro da caixa: autochamada
        selfcall = c.diagram.edges[2]
        self.assertIs(selfcall.end.parent, l2)
        apply_layout(c.diagram)
        use(c, "Return")
        sx, sy = mid(selfcall.end)
        bx, by = b2.x + 3, b2.y + 5
        drag(c, sx, sy, bx, by)
        self.assertEqual(c.diagram.edges[3].kind, "Return")
        self.assertEqual(len(sf.orphan_roots(c.diagram)), 1)

    def test_second_root_call_from_lifeline_is_rejected(self):
        c = make_controller(DT.SEQUENCE)
        for x in (0, 200, 400, 600):
            c.editor.add_node("ImplicitParameter", x, 0)
        use(c, "Call")
        drag(c, 40, 20, 240, 60)
        drag(c, 440, 20, 640, 60)
        self.assertEqual(len(c.diagram.edges), 1)
        self.assertEqual(len(c.editor.notifier.active()), 1)

    def test_lifeline_stem_is_hit_testable(self):
        c = make_controller(DT.SEQUENCE)
        ll = c.editor.add_node("ImplicitParameter", 0, 0)
        self.assertIs(c.diagram.node_at(Point(40, 60)), ll)
        self.assertIsNone(c.diagram.node_at(Point(60, 60)))


class DeletionAndSelectAll(unittest.TestCase):
    def test_delete_selection_and_undo(self):
        c = make_controller(DT.CLASS)
        a, b = c.editor.add_node("Class", 0, 0), c.editor.add_node("Class", 300, 0)
        use(c, "Association"); drag(c, 50, 30, 350, 30)
        use(c, "Select")
        c.select_all()
        self.assertEqual((len(c.selection.nodes), len(c.selection.edges)), (2, 1))
        self.assertTrue(c.delete_selection())
        self.assertEqual((c.diagram.roots, c.diagram.edges), ([], []))
        self.assertTrue(c.selection.is_empty)
        c.editor.undo()
        self.assertEqual((len(c.diagram.roots), len(c.diagram.edges)), (2, 1))
        self.assertFalse(make_controller(DT.CLASS).delete_selection())

    def test_deleting_a_call_box_removes_everything_it_called(self):
        c = make_controller(DT.SEQUENCE)
        ls = [c.editor.add_node("ImplicitParameter", x, 0) for x in (0, 200, 400, 600)]
        e1 = c.editor.add_call(ls[0], ls[1])
        e2 = c.editor.add_call(e1.end, ls[2])
        ctor = c.editor.add_call(e2.end, ls[3], constructor=True)
        e4 = c.editor.add_call(ls[3], ls[0])
        b1, b2, b3 = e1.start, e1.end, e2.end
        c.editor.delete(nodes=[b2])
        self.assertEqual([n for n in c.diagram.all_nodes() if n.TYPE == "Call"], [b1])
        self.assertEqual(c.diagram.edges, [])
        self.assertEqual(len(sf.orphan_roots(c.diagram)), 1)
        c.editor.undo()
        self.assertEqual(len([n for n in c.diagram.all_nodes() if n.TYPE == "Call"]), 5)
        self.assertEqual(len(c.diagram.edges), 4)

    def test_deleting_call_edge_removes_callee_subtree(self):
        c = make_controller(DT.SEQUENCE)
        l1, l2, l3 = (c.editor.add_node("ImplicitParameter", x, 0) for x in (0, 200, 400))
        e1 = c.editor.add_call(l1, l2)
        e2 = c.editor.add_call(e1.end, l3)
        c.editor.delete(edges=[e1])
        self.assertEqual([n.TYPE for n in c.diagram.all_nodes() if n.TYPE == "Call"], ["Call"])
        self.assertEqual(c.diagram.edges, [])


class Hit(unittest.TestCase):
    def test_edge_hit_tolerance(self):
        c = make_controller(DT.STATE)
        s1, s2 = c.editor.add_node("State", 0, 0), c.editor.add_node("State", 300, 0)
        use(c, "Transition"); drag(c, 40, 30, 340, 30)
        apply_layout(c.diagram)
        self.assertIsNotNone(edge_at(c.diagram, Point(200, 31)))
        self.assertIsNone(edge_at(c.diagram, Point(200, 80)))


if __name__ == "__main__":
    unittest.main()
