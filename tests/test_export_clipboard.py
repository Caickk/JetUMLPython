import os
import stat
import tempfile
import unittest
from pathlib import Path

from jetuml_py.app import diagram_size as ds
from jetuml_py.app.exporter import ExportError, export_diagram, supported_extensions
from jetuml_py.app.image_clipboard import ClipboardUnavailable, _copy_with_command, image_to_dib, image_to_png
from jetuml_py.app.settings import Settings
from jetuml_py.clipboard import extract
from jetuml_py.model.diagram import DiagramType as DT
from jetuml_py.rendering.layout import apply_layout
from jetuml_py.rendering.painter import LIGHT, content_bounds, render_image, render_svg
from jetuml_py.rendering.text import TextMetrics
from tests.helpers import errors, make_editor, tool

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def sample_diagram():
    ed = make_editor(DT.CLASS)
    a, b = ed.add_node("Class", 20, 20), ed.add_node("Interface", 320, 20)
    ed.set_properties(a, {"name": "/Shape/", "methods": "area()"})
    ed.set_properties(b, {"name": "Drawable"})
    ed.connect(tool(ed, "Realization"), a, b)
    return ed.diagram


class FontMetrics(unittest.TestCase):
    def test_metrics_scale_with_font_size_and_default_is_unchanged(self):
        small, default, big = TextMetrics(8), TextMetrics(12), TextMetrics(24)
        self.assertEqual((default.width("abcd"), default.line_height), (28, 16))
        self.assertLess(small.width("abcd"), default.width("abcd"))
        self.assertEqual(big.width("abcd"), 2 * default.width("abcd"))
        self.assertGreater(big.line_height, default.line_height)

    def test_font_size_changes_layout_and_svg(self):
        d = sample_diagram()
        d.roots[0].props["name"] = "AVeryLongClassNameToForceGrowth"
        apply_layout(d, TextMetrics(12))
        w12 = d.roots[0].width
        svg = render_svg(d, metrics=TextMetrics(20), font_family="Courier New")
        self.assertGreater(d.roots[0].width, w12)
        self.assertIn('font-size="20"', svg)
        self.assertIn("Courier New", svg)


@unittest.skipUnless(HAS_PIL, "Pillow indisponível")
class Raster(unittest.TestCase):
    def test_image_has_content_bounds_size_and_draws_something(self):
        d = sample_diagram()
        image = render_image(d)
        apply_layout(d)
        _, _, w, h = content_bounds(d)
        self.assertEqual(image.size, (w, h))
        self.assertGreater(len({image.getpixel((x, y)) for x in range(0, w, 3) for y in range(0, h, 3)}), 2)

    def test_export_every_format_and_grid_is_never_exported(self):
        d = sample_diagram()
        with tempfile.TemporaryDirectory() as tmp:
            for ext in (".svg", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"):
                path = Path(tmp) / f"d{ext}"
                export_diagram(d, path)
                self.assertGreater(path.stat().st_size, 100, ext)
            with Image.open(Path(tmp) / "d.png") as png_file, Image.open(Path(tmp) / "d.jpg") as jpg_file:
                self.assertEqual((png_file.format, jpg_file.format), ("PNG", "JPEG"))
            self.assertNotIn(LIGHT.grid, (Path(tmp) / "d.svg").read_text(encoding="utf-8"))
            with Image.open(Path(tmp) / "d.png") as png_file:
                png = png_file.convert("RGB")
            margin = {png.getpixel((x, y)) for x in range(png.width) for y in range(15)}
            self.assertEqual(margin, {(255, 255, 255)})                # margem sem conteúdo: se houvesse grade, apareceria aqui

    def test_unsupported_extension_and_supported_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ExportError):
                export_diagram(sample_diagram(), Path(tmp) / "x.pdf")
            with self.assertRaises(ExportError):
                export_diagram(sample_diagram(), Path(tmp) / "noext")
        self.assertIn(".png", supported_extensions())
        self.assertEqual(supported_extensions()[0], ".svg")

    def test_dib_has_bitmapinfoheader_and_matches_size(self):
        import struct
        image = render_image(sample_diagram())
        dib = image_to_dib(image)
        size, width, height = struct.unpack("<Iii", dib[:12])
        self.assertEqual((size, width, abs(height)), (40, image.width, image.height))   # sem os 14 bytes do arquivo BMP
        self.assertTrue(image_to_png(image).startswith(b"\x89PNG"))

    def test_command_backend_pipes_png_to_clipboard_tool(self):
        image = render_image(sample_diagram())
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "captured.png"
            tool_path = Path(tmp) / "xclip"
            tool_path.write_text(f"#!/bin/sh\n/bin/cat > '{out}'\n")
            tool_path.chmod(tool_path.stat().st_mode | stat.S_IEXEC)
            old = os.environ["PATH"]
            os.environ["PATH"] = tmp
            try:
                _copy_with_command(image_to_png(image))
            finally:
                os.environ["PATH"] = old
            self.assertTrue(out.read_bytes().startswith(b"\x89PNG"))
            os.environ["PATH"] = tmp + os.pathsep + "/nonexistent"
            tool_path.unlink()
            try:
                with self.assertRaises(ClipboardUnavailable):
                    _copy_with_command(b"x")
            finally:
                os.environ["PATH"] = old


class ElementClipboard(unittest.TestCase):
    def setUp(self):
        self.ed = make_editor(DT.CLASS)
        self.a, self.b = self.ed.add_node("Class", 0, 0), self.ed.add_node("Class", 300, 0)
        self.ed.set_property(self.a, "name", "A")
        self.edge = self.ed.connect(tool(self.ed, "Association"), self.a, self.b)

    def test_copy_paste_creates_independent_offset_copies_with_internal_edges(self):
        data = self.ed.copy_elements([self.a, self.b], [self.edge])
        nodes, edges = self.ed.paste(data, 20, 20)
        self.assertEqual(len(nodes), 2)
        self.assertEqual(len(edges), 1)
        na = next(n for n in nodes if n.props["name"] == "A")
        self.assertEqual((na.x, na.y), (20, 20))
        self.assertIsNot(na, self.a)
        self.assertNotIn(na.id, {self.a.id, self.b.id})
        self.assertIs(edges[0].start, na)
        self.ed.set_property(na, "name", "Z")
        self.assertEqual(self.a.props["name"], "A")                       # cópia independente
        self.assertEqual(len(self.ed.diagram.edges), 2)

    def test_paste_is_one_undo_step_and_edge_needs_both_ends_copied(self):
        data = self.ed.copy_elements([self.a], [self.edge])               # aresta sem a outra ponta: fica de fora
        self.assertEqual(data.edges, [])
        data = self.ed.copy_elements([self.a, self.b], [self.edge])
        before = len(list(self.ed.diagram.all_nodes()))
        self.ed.paste(data)
        self.assertEqual(len(list(self.ed.diagram.all_nodes())), before + 2)
        self.ed.undo()
        self.assertEqual((len(list(self.ed.diagram.all_nodes())), len(self.ed.diagram.edges)), (before, 1))

    def test_cut_removes_and_paste_restores_elsewhere(self):
        data = self.ed.cut_elements([self.a, self.b], [self.edge])
        self.assertEqual((self.ed.diagram.roots, self.ed.diagram.edges), ([], []))
        other = make_editor(DT.CLASS)
        nodes, edges = other.paste(data, 0, 0)
        self.assertEqual((len(nodes), len(edges)), (2, 1))

    def test_package_copies_children_and_notes_copy_their_anchor(self):
        ed = make_editor(DT.CLASS)
        pkg = ed.add_node("Package", 0, 0)
        child = ed.add_node("Class", 20, 40)
        note = ed.add_node("Note", 400, 0)
        anchor = ed.anchor_note(note, 600, 200)
        data = ed.copy_elements([pkg, child, note], [anchor])
        nodes, edges = ed.paste(data, 10, 10)
        newpkg = next(n for n in nodes if n.TYPE == "Package")
        self.assertEqual(len(newpkg.children), 1)
        self.assertIs(newpkg.children[0].parent, newpkg)
        self.assertEqual(edges[0].end.TYPE, "Point")
        self.assertEqual((edges[0].end.x, edges[0].end.y), (610, 210))

    def test_incompatible_paste_into_other_diagram_type_is_rejected_with_notification(self):
        data = self.ed.copy_elements([self.a], [])
        state = make_editor(DT.STATE)
        self.assertIsNone(state.paste(data))
        self.assertEqual(errors(state), 1)
        self.assertEqual(state.diagram.roots, [])
        note_only = self.ed.copy_elements([self.ed.add_node("Note", 0, 300)], [])
        self.assertIsNotNone(state.paste(note_only))                       # nota é compatível com qualquer tipo

    def test_paste_into_sequence_diagram_is_never_allowed(self):
        seq = make_editor(DT.SEQUENCE)
        l1, l2 = seq.add_node("ImplicitParameter", 0, 0), seq.add_node("ImplicitParameter", 200, 0)
        seq.add_call(l1, l2)
        data = seq.copy_elements(list(seq.diagram.all_nodes()), seq.diagram.edges)
        self.assertIsNone(seq.paste(data))
        self.assertIsNone(seq.paste(self.ed.copy_elements([self.ed.add_node("Note", 0, 300)], [])))
        self.assertEqual(errors(seq), 2)

    def test_lone_field_cannot_be_pasted_but_object_with_fields_can(self):
        ed = make_editor(DT.OBJECT)
        obj = ed.add_node("Object", 0, 0)
        field = ed.add_node("Field", 10, 10)
        self.assertIsNone(ed.paste(ed.copy_elements([field], [])))        # RF25: campo solto
        self.assertEqual(errors(ed), 1)
        nodes, _ = ed.paste(ed.copy_elements([obj], []))
        self.assertEqual(len(nodes[0].children), 1)

    def test_empty_selection_copies_nothing(self):
        self.assertIsNone(self.ed.copy_elements([], [self.edge]))


class DiagramSize(unittest.TestCase):
    def test_default_follows_screen_and_is_clamped(self):
        self.assertEqual(ds.default_size(1920, 1080), (1920, 1080))
        self.assertEqual(ds.default_size(5120, 100), (4000, 250))         # RNF01

    def test_area_grows_to_fit_larger_diagrams(self):
        self.assertEqual(ds.effective_area((1000, 800), 600, 500), (1000, 800))
        self.assertEqual(ds.effective_area((1000, 800), 2500, 500), (2500, 800))

    def test_validation_range_and_settings_persistence(self):
        self.assertIsNone(ds.validate_size(250, 4000))
        for bad in ((249, 500), (500, 4001)):
            self.assertIsNotNone(ds.validate_size(*bad))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.json"
            s = Settings(path)
            self.assertIsNone(s.diagram_size)
            self.assertEqual(ds.configured_size(s, 1366, 768), (1366, 768))
            s.diagram_size = (800, 600)
            self.assertEqual(Settings(path).diagram_size, (800, 600))
            with self.assertRaises(ValueError):
                s.diagram_size = (100, 600)
            s.diagram_size = None                                          # Restore Defaults
            self.assertIsNone(Settings(path).diagram_size)

    def test_font_and_notification_settings_validate_and_persist(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.json"
            s = Settings(path)
            self.assertEqual((s.font, s.notification_duration), (("Helvetica", 12), 5))
            s.font = ("Courier New", 16)
            s.notification_duration = 0
            again = Settings(path)
            self.assertEqual((again.font, again.notification_duration), (("Courier New", 16), 0))
            for bad in (("", 12), ("X", 5), ("X", 99)):
                with self.assertRaises(ValueError):
                    s.font = bad
            for bad in (-1, 11):
                with self.assertRaises(ValueError):
                    s.notification_duration = bad


if __name__ == "__main__":
    unittest.main()
