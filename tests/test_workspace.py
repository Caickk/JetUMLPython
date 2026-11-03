import json
import tempfile
import unittest
from pathlib import Path

from jetuml_py.app.settings import Settings
from jetuml_py.app.workspace import Workspace
from jetuml_py.app.zoom import ZoomModel
from jetuml_py.model.diagram import DiagramType as DT
from jetuml_py.persistence import diagram_to_dict


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.settings = Settings(self.dir / "settings.json")
        self.ws = Workspace(self.settings)

    def tearDown(self):
        self._tmp.cleanup()

    def test_new_creates_each_type_and_activates(self):
        for i, dtype in enumerate(DT, 1):
            doc = self.ws.new(dtype)
            self.assertIs(self.ws.active, doc)
            self.assertEqual(doc.title, f"Untitled {i}")
            self.assertEqual(doc.diagram.type, dtype)
        self.assertEqual(len(self.ws.documents), 5)

    def test_dirty_follows_undo_stack_and_save(self):
        doc = self.ws.new(DT.CLASS)
        self.assertFalse(doc.dirty)
        doc.editor.add_node("Class", 0, 0)
        self.assertTrue(doc.dirty)
        doc.editor.undo()
        self.assertFalse(doc.dirty)          # voltou ao estado salvo (inicial)
        doc.editor.redo()
        self.assertTrue(self.ws.save_as(doc, self.dir / "a"))   # sem extensão: ganha .json
        self.assertEqual(doc.title, "a.json")
        self.assertFalse(doc.dirty)
        doc.editor.add_node("Class", 300, 0)
        self.assertTrue(doc.dirty)
        doc.editor.undo()
        self.assertFalse(doc.dirty)

    def test_save_without_path_requires_save_as(self):
        with self.assertRaises(ValueError):
            self.ws.save(self.ws.new(DT.STATE))

    def test_open_roundtrip_recent_files_and_reuse_of_open_document(self):
        doc = self.ws.new(DT.CLASS)
        doc.editor.add_node("Class", 10, 10)
        path = self.dir / "d.json"
        self.ws.save_as(doc, path)
        other = Workspace(self.settings)
        opened = other.open(path)
        self.assertEqual(diagram_to_dict(opened.diagram), diagram_to_dict(doc.diagram))
        self.assertIs(other.open(path), opened)                 # não abre duas vezes
        self.assertEqual(len(other.documents), 1)
        self.assertEqual(Settings(self.dir / "settings.json").recent_files, [str(path.resolve())])

    def test_open_invalid_file_reports_error_and_drops_recent(self):
        bad = self.dir / "bad.json"
        bad.write_text("{oops", encoding="utf-8")
        self.settings.add_recent(bad)
        self.assertIsNone(self.ws.open(bad))
        self.assertIn("Cannot open", self.ws.last_error)
        self.assertEqual(self.settings.recent_files, [])
        self.assertTrue(any(n.kind == "error" for n in self.ws.notifier.active()))
        self.assertIsNone(self.ws.open(self.dir / "missing.json"))

    def test_close_refuses_dirty_unless_forced_and_picks_neighbour(self):
        a, b, c = (self.ws.new(DT.CLASS) for _ in range(3))
        self.ws.activate(b)
        b.editor.add_node("Class", 0, 0)
        self.assertFalse(self.ws.close(b))
        self.assertIn(b, self.ws.documents)
        self.assertTrue(self.ws.close(b, force=True))
        self.assertIs(self.ws.active, c)
        self.ws.close(c); self.ws.close(a)
        self.assertIsNone(self.ws.active)

    def test_duplicate_is_independent_and_unsaved(self):
        doc = self.ws.new(DT.OBJECT)
        doc.editor.add_node("Object", 0, 0)
        copy = self.ws.duplicate(doc)
        self.assertEqual(copy.title, "Copy of Untitled 1")
        self.assertTrue(copy.dirty)                              # conteúdo ainda não salvo
        copy.editor.add_node("Object", 300, 0)
        self.assertEqual(len(doc.diagram.roots), 1)
        self.assertEqual(len(copy.diagram.roots), 2)

    def test_events(self):
        events = []
        self.ws.subscribe(lambda e, d: events.append(e))
        doc = self.ws.new(DT.CLASS)
        self.ws.save_as(doc, self.dir / "x.json")
        self.ws.close(doc)
        self.assertEqual(events, ["opened", "saved", "closed"])


class SettingsAndZoom(unittest.TestCase):
    def test_settings_persist_limit_recent_and_survive_corruption(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.json"
            s = Settings(path)
            for i in range(15):
                s.add_recent(Path(tmp) / f"f{i}.json")
            s.dark_mode = True
            s.show_grid = False
            again = Settings(path)
            self.assertEqual(len(again.recent_files), 10)
            self.assertTrue(again.recent_files[0].endswith("f14.json"))
            self.assertTrue(again.dark_mode)
            self.assertFalse(again.show_grid)
            path.write_text("garbage", encoding="utf-8")
            self.assertEqual(Settings(path).recent_files, [])
            path.write_text(json.dumps({"recent_files": "x", "dark_mode": True}), encoding="utf-8")
            self.assertEqual(Settings(path).recent_files, [])

    def test_zoom_two_levels_each_direction(self):
        z = ZoomModel()
        self.assertEqual(z.factor, 1)
        self.assertTrue(z.zoom_in() and z.zoom_in())
        self.assertFalse(z.zoom_in())
        self.assertGreater(z.factor, 1)
        self.assertTrue(z.reset())
        self.assertFalse(z.reset())
        self.assertTrue(z.zoom_out() and z.zoom_out())
        self.assertFalse(z.zoom_out())
        self.assertLess(z.factor, 1)


if __name__ == "__main__":
    unittest.main()
