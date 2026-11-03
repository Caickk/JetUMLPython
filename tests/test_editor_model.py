import json
import tempfile
import unittest
from pathlib import Path

from jetuml_py.model.diagram import DiagramType as DT
from jetuml_py.notifications import NotificationService
from jetuml_py.persistence import (DiagramFormatError, diagram_to_dict, duplicate, load, save)
from jetuml_py.tools import TOOLBARS, shortcut_map
from tests.helpers import make_editor, tool


def snapshot(ed):
    return json.dumps(diagram_to_dict(ed.diagram), sort_keys=True)


class UndoRedo(unittest.TestCase):
    def test_undo_all_returns_to_initial_state_and_redo_replays(self):
        ed = make_editor(DT.CLASS)
        states = [snapshot(ed)]
        a = ed.add_node("Class", 0, 0); states.append(snapshot(ed))
        b = ed.add_node("Class", 300, 0); states.append(snapshot(ed))
        e = ed.connect(tool(ed, "Composition"), a, b); states.append(snapshot(ed))
        ed.set_property(e, "aggregation_type", "Aggregation"); states.append(snapshot(ed))
        ed.move([a], 15, 5); states.append(snapshot(ed))
        ed.delete(nodes=[b]); states.append(snapshot(ed))
        for expected in reversed(states[:-1]):
            self.assertTrue(ed.undo())
            self.assertEqual(snapshot(ed), expected)
        self.assertFalse(ed.undo())
        for expected in states[1:]:
            self.assertTrue(ed.redo())
            self.assertEqual(snapshot(ed), expected)

    def test_new_action_clears_redo(self):
        ed = make_editor(DT.CLASS)
        ed.add_node("Class", 0, 0)
        ed.undo()
        ed.add_node("Class", 10, 10)
        self.assertFalse(ed.redo())

    def test_composite_call_is_a_single_undo_step(self):
        ed = make_editor(DT.SEQUENCE)
        l1, l2 = ed.add_node("ImplicitParameter", 0, 0), ed.add_node("ImplicitParameter", 200, 0)
        ed.connect(tool(ed, "Call"), l1, l2)
        self.assertEqual(len(list(ed.diagram.all_nodes())), 4)
        ed.undo()
        self.assertEqual(len(list(ed.diagram.all_nodes())), 2)
        self.assertEqual(ed.diagram.edges, [])


class Containment(unittest.TestCase):
    def test_package_children_move_delete_and_restore(self):
        ed = make_editor(DT.CLASS)
        pkg = ed.add_node("Package", 0, 0)
        c = ed.add_node("Class", 10, 10)
        other = ed.add_node("Class", 500, 500)
        self.assertIs(c.parent, pkg)
        ed.connect(tool(ed, "Dependency"), c, other)
        note = ed.add_node("Note", 600, 0)
        ed.anchor_note(note, 700, 100)
        before = snapshot(ed)
        ed.move([pkg], 20, 30)
        self.assertEqual((c.x, c.y), (30, 40))
        ed.undo()
        ed.delete(nodes=[pkg])
        self.assertEqual([n.TYPE for n in ed.diagram.roots], ["Class", "Note", "Point"])
        self.assertEqual(len(ed.diagram.edges), 1)  # só o conector da nota
        ed.undo()
        self.assertEqual(snapshot(ed), before)
        ed.delete(nodes=[note])  # remove também conector e âncora
        self.assertEqual(ed.diagram.edges and [e.kind for e in ed.diagram.edges], ["Dependency"])
        self.assertNotIn("Point", [n.TYPE for n in ed.diagram.roots])

    def test_attach_and_detach_with_undo(self):
        ed = make_editor(DT.CLASS)
        pkg = ed.add_node("Package", 0, 0)
        c = ed.add_node("Class", 600, 600)
        self.assertIsNotNone(ed.attach(c, pkg))
        self.assertIs(c.parent, pkg)
        ed.detach(c)
        self.assertIsNone(c.parent)
        ed.undo()
        self.assertIs(c.parent, pkg)

    def test_field_cannot_be_detached(self):
        ed = make_editor(DT.OBJECT)
        ed.add_node("Object", 0, 0)
        f = ed.add_node("Field", 5, 5)
        self.assertIsNone(ed.detach(f))


class Properties(unittest.TestCase):
    def test_invalid_property_value_rejected(self):
        ed = make_editor(DT.CLASS)
        a, b = ed.add_node("Class", 0, 0), ed.add_node("Class", 300, 0)
        e = ed.connect(tool(ed, "Association"), a, b)
        self.assertTrue(ed.set_property(e, "directionality", "Bidirectional"))
        self.assertFalse(ed.set_property(e, "directionality", "Sideways"))
        self.assertFalse(ed.set_property(a, "nonexistent", 1))
        self.assertTrue(ed.set_property(a, "name", "Foo"))


class Persistence(unittest.TestCase):
    def test_round_trip_and_duplicate(self):
        ed = make_editor(DT.CLASS)
        pkg = ed.add_node("Package", 0, 0)
        a = ed.add_node("Class", 10, 10)
        b = ed.add_node("Interface", 400, 0)
        ed.set_property(a, "name", "Â «x» /abstract/")
        ed.connect(tool(ed, "Realization"), a, b)
        ed.anchor_note(ed.add_node("Note", 0, 300), 100, 400)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "d.json"
            save(ed.diagram, path)
            loaded = load(path)
            self.assertEqual(diagram_to_dict(loaded), diagram_to_dict(ed.diagram))
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["diagram"], "ClassDiagram")
        self.assertEqual(diagram_to_dict(duplicate(ed.diagram)), diagram_to_dict(ed.diagram))
        self.assertIsNot(duplicate(ed.diagram), ed.diagram)

    def test_invalid_files_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.json"
            bad.write_text("{not json", encoding="utf-8")
            with self.assertRaises(DiagramFormatError):
                load(bad)
        orphan_field = {"version": 1, "diagram": "ObjectDiagram", "edges": [],
                        "nodes": [{"type": "Field", "id": "f", "x": 0, "y": 0, "properties": {}, "children": []}]}
        from jetuml_py.persistence import diagram_from_dict
        with self.assertRaises(DiagramFormatError):
            diagram_from_dict(orphan_field)  # RF25: campo solto
        with self.assertRaises(DiagramFormatError):
            diagram_from_dict({"version": 1, "diagram": "Nope", "nodes": [], "edges": []})


class Toolbars(unittest.TestCase):
    def test_order_and_shortcuts(self):
        names = [t.name for t in TOOLBARS[DT.CLASS]]
        self.assertEqual(names, ["Select", "Class", "Interface", "Package", "Package Description", "Note",
                                 "Dependency", "Inheritance", "Realization", "Association", "Aggregation",
                                 "Composition", "Note Connector", "To Clipboard"])
        keys = shortcut_map(DT.CLASS)
        self.assertEqual(keys["1"].name, "Select")
        self.assertEqual(keys["0"].name, "Association")
        self.assertEqual(list(keys)[-1], "D")
        self.assertEqual(keys["D"].name, "To Clipboard")
        self.assertEqual([t.name for t in TOOLBARS[DT.SEQUENCE]],
                         ["Select", "Implicit Parameter", "Note", "Call", "Return", "Note Connector", "To Clipboard"])
        self.assertEqual(len(TOOLBARS[DT.USE_CASE]), 10)
        self.assertEqual(shortcut_map(DT.USE_CASE)["0"].name, "To Clipboard")


class Notifications(unittest.TestCase):
    def test_duration_range_zero_disables_and_expiry(self):
        now = [0.0]
        svc = NotificationService(clock=lambda: now[0])
        self.assertEqual(svc.duration, 5)
        svc.error("boom"); svc.success("ok")
        self.assertEqual([n.kind for n in svc.active()], ["error", "success"])
        now[0] = 5.0
        self.assertEqual(svc.active(), [])
        svc.duration = 0
        self.assertIsNone(svc.error("hidden"))
        self.assertEqual(svc.active(), [])
        for bad in (-1, 11):
            with self.assertRaises(ValueError):
                svc.duration = bad
        svc.duration = 10
        svc.restore_default()
        self.assertEqual(svc.duration, 5)


if __name__ == "__main__":
    unittest.main()
