"""Testes da interface Tk. São ignorados quando não há Tkinter ou display (ex.: servidor sem tela)."""
import tempfile
import unittest
from pathlib import Path

try:
    import tkinter as tk
    _probe = tk.Tk()
    _probe.destroy()
    HAS_TK = True
except Exception:  # sem tkinter ou sem display
    HAS_TK = False

if HAS_TK:
    from jetuml_py.app.settings import Settings
    from jetuml_py.model.diagram import DiagramType as DT
    from jetuml_py.rendering.painter import DARK, LIGHT
    from jetuml_py.ui.app import App


@unittest.skipUnless(HAS_TK, "Tkinter/display indisponível")
class AppTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.root = tk.Tk()
        self.app = App(self.root, Settings(self.dir / "settings.json"))
        self.app._show_error = lambda msg: self.errors.append(msg)
        self.errors = []
        self.root.update()

    def tearDown(self):
        try:
            self.root.destroy()
        except tk.TclError:
            pass
        self._tmp.cleanup()

    def settle(self):
        self.root.update_idletasks()
        self.root.update()

    def items(self):
        return len(self.app.view.canvas.find_all())

    def test_welcome_screen_then_new_diagram_opens_tab(self):
        self.assertTrue(self.app.welcome.winfo_ismapped())
        self.assertFalse(self.app.notebook.winfo_ismapped())
        self.app.new_diagram(DT.USE_CASE)
        self.settle()
        self.assertFalse(self.app.welcome.winfo_ismapped())
        self.assertEqual(len(self.app.notebook.tabs()), 1)
        self.assertEqual(self.app.notebook.tab(self.app.notebook.tabs()[0], "text"), "Untitled 1")

    def test_menus_offer_all_five_diagram_types_and_state_follows_document(self):
        new_menu = self.app.file_menu.nametowidget(self.app.file_menu.entrycget("New", "menu"))
        labels = [new_menu.entrycget(i, "label") for i in range(new_menu.index("end") + 1)]
        self.assertEqual(labels, ["Class Diagram", "Sequence Diagram", "State Diagram", "Object Diagram", "Use Case Diagram"])
        self.assertEqual(self.app.file_menu.entrycget("Save", "state"), "disabled")
        self.app.new_diagram(DT.CLASS)
        self.settle()
        self.assertEqual(self.app.file_menu.entrycget("Save", "state"), "normal")
        self.assertEqual(self.app.edit_menu.entrycget("Undo", "state"), "disabled")
        self.app.doc.editor.add_node("Class", 20, 20)
        self.settle()
        self.assertEqual(self.app.edit_menu.entrycget("Undo", "state"), "normal")

    def test_diagram_is_drawn_and_redrawn_on_changes(self):
        self.app.new_diagram(DT.CLASS)
        self.settle()
        base = self.items()                      # grade
        self.assertGreater(base, 0)
        self.app.doc.editor.add_node("Class", 40, 40)
        self.settle()
        self.assertGreater(self.items(), base)
        self.app.doc.editor.undo()
        self.settle()
        self.assertEqual(self.items(), base)

    def test_zoom_levels_limits_and_scroll_region(self):
        self.app.new_diagram(DT.CLASS)
        self.app.doc.editor.add_node("Class", 2000, 100)   # conteúdo mais largo que a janela
        self.settle()
        region = lambda: float(str(self.app.view.canvas.cget("scrollregion")).split()[2])
        w0 = region()
        self.app.zoom_in(); self.app.zoom_in(); self.app.zoom_in()
        self.settle()
        self.assertEqual(self.app.doc.zoom.level, 2)
        self.assertEqual(self.app.view_menu.entrycget("Zoom In", "state"), "disabled")
        self.assertGreater(region(), w0)
        self.app.reset_zoom()
        self.settle()
        self.assertAlmostEqual(region(), w0, delta=1)
        self.app.zoom_out(); self.app.zoom_out(); self.app.zoom_out()
        self.assertEqual(self.app.doc.zoom.level, -2)

    def test_zoom_is_per_document(self):
        self.app.new_diagram(DT.CLASS)
        self.app.zoom_in()
        self.app.new_diagram(DT.STATE)
        self.assertEqual(self.app.doc.zoom.level, 0)

    def test_dark_mode_and_grid_toggle_persist(self):
        self.app.new_diagram(DT.CLASS)
        self.settle()
        self.assertEqual(self.app.view.canvas.cget("bg"), LIGHT.background)
        self.app.dark_var.set(True)
        self.app.toggle_dark_mode()
        self.settle()
        self.assertEqual(self.app.view.canvas.cget("bg"), DARK.background)
        with_grid = self.items()
        self.app.grid_var.set(False)
        self.app.toggle_grid()
        self.settle()
        self.assertLess(self.items(), with_grid)
        reloaded = Settings(self.dir / "settings.json")
        self.assertTrue(reloaded.dark_mode)
        self.assertFalse(reloaded.show_grid)

    def test_save_open_recent_and_dirty_marker(self):
        self.app.new_diagram(DT.CLASS)
        self.app.doc.editor.add_node("Class", 20, 20)
        self.settle()
        tab = lambda: self.app.notebook.tab(self.app.notebook.tabs()[0], "text")
        self.assertTrue(tab().endswith("*"))
        target = self.dir / "meu.json"
        self.app._ask_save_path = lambda doc: str(target)
        self.assertTrue(self.app.save_current())
        self.settle()
        self.assertEqual(tab(), "meu.json")
        self.assertTrue(target.exists())
        self.app.close_current()
        self.settle()
        self.assertTrue(self.app.welcome.winfo_ismapped())
        self.app._rebuild_recent()
        self.assertEqual(self.app.recent_menu.entrycget(0, "label"), str(target.resolve()))
        self.app._ask_open_path = lambda: str(target)
        self.app.open_file()
        self.settle()
        self.assertEqual(len(self.app.doc.diagram.roots), 1)
        self.assertGreater(self.items(), 0)

    def test_open_invalid_file_shows_error(self):
        bad = self.dir / "bad.json"
        bad.write_text("nope", encoding="utf-8")
        self.assertIsNone(self.app.open_path(bad))
        self.assertEqual(len(self.errors), 1)

    def test_close_asks_to_save_changes(self):
        self.app.new_diagram(DT.CLASS)
        self.app.doc.editor.add_node("Class", 0, 0)
        self.app._ask_save_changes = lambda doc: None            # cancelar
        self.assertFalse(self.app.close_current())
        self.assertEqual(len(self.app.workspace.documents), 1)
        self.app._ask_save_changes = lambda doc: False           # descartar
        self.assertTrue(self.app.close_current())
        self.assertEqual(len(self.app.workspace.documents), 0)

    def test_duplicate_opens_new_tab(self):
        self.app.new_diagram(DT.OBJECT)
        self.app.doc.editor.add_node("Object", 0, 0)
        self.app.duplicate_current()
        self.settle()
        self.assertEqual(len(self.app.notebook.tabs()), 2)
        self.assertEqual(self.app.doc.title, "Copy of Untitled 1")

    def test_switching_tabs_changes_active_document(self):
        first = self.app.new_diagram(DT.CLASS)
        self.app.new_diagram(DT.STATE)
        self.settle()
        self.app.notebook.select(self.app.notebook.tabs()[0])
        self.settle()
        self.assertIs(self.app.doc, first)

    def test_keyboard_shortcuts_are_bound_and_work(self):
        for seq in ("<Control-o>", "<Control-w>", "<Control-s>", "<Control-d>", "<Control-q>",
                    "<Control-z>", "<Control-y>", "<Control-equal>", "<Control-minus>", "<Control-Key-0>"):
            self.assertTrue(self.root.bind_all(seq), seq)
        self.app.new_diagram(DT.CLASS)
        self.settle()
        self.root.focus_force()
        self.settle()
        self.root.event_generate("<Control-equal>")
        self.settle()
        self.assertEqual(self.app.doc.zoom.level, 1)
        self.root.event_generate("<Control-Key-0>")
        self.settle()
        self.assertEqual(self.app.doc.zoom.level, 0)

    def test_undo_redo_via_app(self):
        self.app.new_diagram(DT.CLASS)
        self.app.doc.editor.add_node("Class", 0, 0)
        self.app.undo()
        self.assertEqual(self.app.doc.diagram.roots, [])
        self.app.redo()
        self.assertEqual(len(self.app.doc.diagram.roots), 1)

    def test_exit_checks_unsaved_then_closes_window(self):
        self.app.new_diagram(DT.CLASS)
        self.app.doc.editor.add_node("Class", 0, 0)
        self.app._ask_save_changes = lambda doc: None
        self.assertFalse(self.app.exit())
        self.assertTrue(self.root.winfo_exists())
        self.app._ask_save_changes = lambda doc: False
        self.assertTrue(self.app.exit())



@unittest.skipUnless(HAS_TK, "Tkinter/display indisponível")
class InteractionUiTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.root = tk.Tk()
        self.app = App(self.root, Settings(self.dir / "settings.json"))
        self.root.update()

    def tearDown(self):
        try:
            self.root.destroy()
        except tk.TclError:
            pass
        self._tmp.cleanup()

    def settle(self):
        self.root.update_idletasks()
        self.root.update()

    def open(self, dtype):
        self.app.new_diagram(dtype)
        self.settle()
        self.root.focus_force()
        self.app.view.canvas.focus_force()
        self.settle()
        return self.app.view

    def mouse(self, view, kind, x, y):
        state = {"<ButtonPress-1>": 0, "<B1-Motion>": 0x100, "<ButtonRelease-1>": 0x100}[kind]
        view.canvas.event_generate(kind, x=x, y=y, state=state)
        self.settle()

    def select_tool(self, view, name):
        tool = next(t for t in view.toolbar.tools if t.name == name)
        view.activate_tool(tool)
        return tool

    def test_toolbar_lists_tools_in_order_for_each_diagram_type(self):
        from jetuml_py.tools import TOOLBARS
        for dtype in DT:
            view = self.open(dtype)
            self.assertEqual([t.name for t, *_ in view.toolbar.rows], [t.name for t in TOOLBARS[dtype]])
            self.assertEqual(view.toolbar.rows[0][1].cget("relief"), "sunken")   # Select ativo

    def test_clicking_toolbar_and_keyboard_shortcuts_change_tool(self):
        view = self.open(DT.CLASS)
        view.toolbar.rows[1][1].event_generate("<Button-1>")
        self.settle()
        self.assertEqual(view.controller.tool.name, "Class")
        view.canvas.event_generate("<KeyPress>", keysym="0")
        self.settle()
        self.assertEqual(view.controller.tool.name, "Association")               # RF08: "0" = décima
        view.canvas.event_generate("<KeyPress>", keysym="a")
        self.settle()
        self.assertEqual(view.controller.tool.name, "Aggregation")               # RF08: "A" = 11ª ferramenta
        view.canvas.event_generate("<KeyPress>", keysym="Escape")
        self.settle()
        self.assertEqual(view.controller.tool.name, "Select")

    def test_clipboard_tool_is_an_action_not_a_mode(self):
        view = self.open(DT.STATE)
        self.select_tool(view, "State")
        self.select_tool(view, "To Clipboard")
        self.assertEqual(view.controller.tool.name, "State")

    def test_context_menu_lists_toolbar_tools(self):
        view = self.open(DT.SEQUENCE)
        menu = view.build_context_menu()
        labels = [menu.entrycget(i, "label") for i in range(menu.index("end") + 1)]
        self.assertEqual(labels, ["Select", "Implicit Parameter", "Note", "Call", "Return", "Note Connector", "To Clipboard"])
        menu.invoke(1)
        self.assertEqual(view.controller.tool.name, "Implicit Parameter")

    def test_mouse_creates_node_respecting_zoom(self):
        view = self.open(DT.CLASS)
        self.select_tool(view, "Class")
        self.mouse(view, "<ButtonPress-1>", 203, 57)
        self.mouse(view, "<ButtonRelease-1>", 203, 57)
        node = view.doc.diagram.roots[0]
        self.assertEqual((node.x, node.y), (200, 60))
        self.app.zoom_in()                                   # 1.25x: pixel (250, 125) -> modelo (200, 100)
        self.settle()
        self.mouse(view, "<ButtonPress-1>", 250, 375)
        self.mouse(view, "<ButtonRelease-1>", 250, 375)
        second = view.doc.diagram.roots[1]
        self.assertEqual((second.x, second.y), (200, 300))

    def test_mouse_drag_creates_edge_and_selection_overlay_follows(self):
        view = self.open(DT.CLASS)
        a = view.doc.editor.add_node("Class", 50, 50)
        b = view.doc.editor.add_node("Class", 350, 50)
        self.settle()
        self.select_tool(view, "Association")
        self.mouse(view, "<ButtonPress-1>", 80, 80)
        self.mouse(view, "<B1-Motion>", 200, 80)
        self.assertTrue(view.canvas.find_withtag("overlay"))             # linha elástica
        self.mouse(view, "<ButtonRelease-1>", 380, 80)
        self.assertEqual(len(view.doc.diagram.edges), 1)
        self.assertTrue(view.canvas.find_withtag("overlay"))             # aresta selecionada: alças
        self.select_tool(view, "Select")
        self.mouse(view, "<ButtonPress-1>", 600, 400)
        self.mouse(view, "<ButtonRelease-1>", 600, 400)
        self.assertFalse(view.canvas.find_withtag("overlay"))

    def test_drag_node_with_mouse_and_delete_key(self):
        view = self.open(DT.CLASS)
        node = view.doc.editor.add_node("Class", 50, 50)
        self.settle()
        self.mouse(view, "<ButtonPress-1>", 80, 80)
        self.mouse(view, "<B1-Motion>", 130, 130)
        self.mouse(view, "<ButtonRelease-1>", 130, 130)
        self.assertEqual((node.x, node.y), (100, 100))
        view.canvas.focus_force()
        self.settle()
        view.canvas.event_generate("<Delete>")
        self.settle()
        self.assertEqual(view.doc.diagram.roots, [])
        self.assertEqual(self.app.edit_menu.entrycget("Delete", "state"), "disabled")

    def test_edit_menu_select_all_and_delete(self):
        view = self.open(DT.OBJECT)
        view.doc.editor.add_node("Object", 20, 20)
        view.doc.editor.add_node("Object", 300, 20)
        self.settle()
        self.assertEqual(self.app.edit_menu.entrycget("Delete", "state"), "disabled")
        self.app.select_all()
        self.settle()
        self.assertEqual(len(view.controller.selection.nodes), 2)
        self.assertEqual(self.app.edit_menu.entrycget("Delete", "state"), "normal")
        self.app.delete_selection()
        self.settle()
        self.assertEqual(view.doc.diagram.roots, [])

    def test_tooltips_and_tool_hint_options(self):
        view = self.open(DT.CLASS)
        tip = view.toolbar.tooltips[4]
        tip.show()
        self.assertEqual(tip.window.winfo_children()[0].cget("text"), "Package Description")
        tip.hide()
        self.app.verbose_var.set(True)
        self.app.toggle_verbose_tooltips()
        tip.show()
        self.assertIn("describing the contents of a package", tip.window.winfo_children()[0].cget("text"))
        tip.hide()
        label = view.toolbar.rows[1][3]
        self.assertFalse(label.winfo_ismapped())
        self.app.hint_var.set(True)
        self.app.toggle_tool_hint()
        self.settle()
        self.assertTrue(label.winfo_ismapped())
        reloaded = Settings(self.dir / "settings.json")
        self.assertTrue(reloaded.show_tool_hint and reloaded.verbose_tooltips)


@unittest.skipUnless(HAS_TK, "Tkinter/display indisponível")
class PropertiesUiTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.root = tk.Tk()
        self.app = App(self.root, Settings(self.dir / "settings.json"))
        self.root.update()

    def tearDown(self):
        try:
            self.root.destroy()
        except tk.TclError:
            pass
        self._tmp.cleanup()

    def settle(self):
        self.root.update_idletasks()
        self.root.update()

    def open(self, dtype):
        self.app.new_diagram(dtype)
        self.settle()
        self.root.focus_force()
        self.settle()
        return self.app.view

    def double_click(self, view, x, y):
        """O Tk não permite gerar <Double-...>: dois cliques seguidos, rápidos, formam o duplo clique."""
        c = view.canvas
        for kind, state in (("<ButtonPress-1>", 0), ("<ButtonRelease-1>", 0x100),
                            ("<ButtonPress-1>", 0), ("<ButtonRelease-1>", 0x100)):
            c.event_generate(kind, x=x, y=y, state=state)
        self.settle()

    def mouse(self, view, kind, x, y):
        state = {"<ButtonPress-1>": 0, "<B1-Motion>": 0x100, "<ButtonRelease-1>": 0x100}[kind]
        view.canvas.event_generate(kind, x=x, y=y, state=state)
        self.settle()

    def test_double_click_opens_panel_and_changes_are_undoable(self):
        view = self.open(DT.CLASS)
        node = view.doc.editor.add_node("Class", 50, 50)
        self.settle()
        self.double_click(view, 80, 80)
        dlg = view.dialog
        self.assertIsNotNone(dlg)
        self.assertEqual(list(dlg.widgets), ["name", "attributes", "methods"])
        dlg.widgets["name"][2].set("Foo")
        dlg.widgets["name"][1].event_generate("<Return>")
        self.settle()
        self.assertEqual(node.props["name"], "Foo")
        dlg.widgets["attributes"][1].insert("1.0", "x: int")
        dlg.event_generate("<Escape>")                          # Esc fecha e confirma o que foi digitado
        self.settle()
        self.assertIsNone(view.dialog)
        self.assertEqual(node.props["attributes"], "x: int")
        view.doc.editor.undo()
        self.assertEqual(node.props["attributes"], "")
        view.doc.editor.undo()
        self.assertEqual(node.props["name"], "")

    def test_ctrl_enter_and_edit_menu_follow_selection(self):
        view = self.open(DT.STATE)
        ini = view.doc.editor.add_node("InitialState", 20, 20)
        st = view.doc.editor.add_node("State", 200, 20)
        self.settle()
        state = lambda: self.app.edit_menu.entrycget("Properties", "state")
        self.assertEqual(state(), "disabled")
        view.controller.selection.set([ini]); self.app._refresh()
        self.assertEqual(state(), "disabled")                   # sem propriedades textuais
        self.assertFalse(view.open_selected_properties())
        view.controller.selection.set([st]); self.app._refresh()
        self.assertEqual(state(), "normal")
        view.controller.select_all(); self.app._refresh()
        self.assertEqual(state(), "disabled")                   # mais de um elemento
        view.controller.selection.set([st]); self.settle()
        view.canvas.focus_force(); self.settle()
        view.canvas.event_generate("<Control-Return>")
        self.settle()
        self.assertEqual(list(view.dialog.widgets), ["name"])

    def test_ctrl_q_inserts_stereotype_without_quitting(self):
        view = self.open(DT.CLASS)
        view.doc.editor.add_node("Class", 50, 50)
        self.settle()
        self.double_click(view, 80, 80)
        entry = view.dialog.widgets["name"][1]
        entry.focus_force(); self.settle()
        entry.event_generate("<Control-q>")
        self.settle()
        self.assertEqual(view.dialog.widgets["name"][2].get(), "«»")
        self.assertEqual(entry.index("insert"), 1)
        text = view.dialog.widgets["methods"][1]
        text.focus_force(); self.settle()
        text.event_generate("<Control-q>")
        self.assertEqual(text.get("1.0", "end-1c"), "«»")
        self.assertEqual(text.index("insert"), "1.1")
        self.assertTrue(self.root.winfo_exists())               # o atalho global de sair não disparou

    def test_tab_moves_between_fields_in_a_cycle(self):
        view = self.open(DT.CLASS)
        view.doc.editor.add_node("Class", 50, 50)
        self.settle()
        self.double_click(view, 80, 80)
        dlg = view.dialog
        name, attrs, methods = (dlg.widgets[n][1] for n in ("name", "attributes", "methods"))
        dlg.focus_force(); name.focus_force(); self.settle()
        name.event_generate("<Tab>"); self.settle()
        self.assertIs(dlg.focus_get(), attrs)
        attrs.event_generate("<Tab>"); self.settle()
        self.assertIs(dlg.focus_get(), methods)
        self.assertEqual(attrs.get("1.0", "end-1c"), "")        # Tab não insere tabulação
        methods.event_generate("<Tab>"); self.settle()
        self.assertIs(dlg.focus_get(), name)
        methods.focus_force(); self.settle()
        methods.event_generate("<Shift-Tab>"); self.settle()     # Shift+Tab volta ao campo anterior
        self.assertIs(dlg.focus_get(), attrs)

    def test_auto_edit_node_opens_panel_only_for_nodes_with_properties(self):
        view = self.open(DT.STATE)
        tool = lambda n: next(t for t in view.toolbar.tools if t.name == n)
        view.activate_tool(tool("State"))
        self.mouse(view, "<ButtonPress-1>", 100, 100); self.mouse(view, "<ButtonRelease-1>", 100, 100)
        self.assertIsNone(view.dialog)                          # desligado por padrão
        self.app.auto_edit_var.set(True)
        self.app.toggle_auto_edit()
        self.assertTrue(Settings(self.dir / "settings.json").auto_edit_node)
        self.mouse(view, "<ButtonPress-1>", 300, 100); self.mouse(view, "<ButtonRelease-1>", 300, 100)
        self.assertIsNotNone(view.dialog)
        view.dialog.close()
        view.activate_tool(tool("Initial State"))
        self.mouse(view, "<ButtonPress-1>", 100, 300); self.mouse(view, "<ButtonRelease-1>", 100, 300)
        self.assertIsNone(view.dialog)                          # inicial não tem propriedades
        view.activate_tool(tool("Transition"))
        a, b = [n for n in view.doc.diagram.roots if n.TYPE == "State"]
        self.mouse(view, "<ButtonPress-1>", a.x + 10, a.y + 10)
        self.mouse(view, "<B1-Motion>", b.x + 10, b.y + 10)
        self.mouse(view, "<ButtonRelease-1>", b.x + 10, b.y + 10)
        self.assertEqual(len(view.doc.diagram.edges), 1)
        self.assertIsNone(view.dialog)                          # vale só para nós

    def test_panel_closes_when_element_disappears_and_follows_undo(self):
        view = self.open(DT.SEQUENCE)
        l1, l2 = view.doc.editor.add_node("ImplicitParameter", 0, 0), view.doc.editor.add_node("ImplicitParameter", 200, 0)
        box = view.doc.editor.add_call(l1, l2).end
        self.settle()
        view.open_properties(box)
        kind, check, var = view.dialog.widgets["open_bottom"]
        self.assertEqual(kind, "bool")
        check.invoke(); self.settle()
        self.assertIs(box.props["open_bottom"], True)           # RF31
        view.doc.editor.undo(); self.settle()
        self.assertIs(box.props["open_bottom"], False)
        self.assertFalse(var.get())                             # painel acompanhou o desfazer
        view.doc.editor.undo()                                  # remove a chamada e as caixas
        self.settle()
        self.assertIsNone(view.dialog)

    def test_edge_panel_swaps_composition_for_aggregation(self):
        from jetuml_py.tools import tool_by_name
        view = self.open(DT.CLASS)
        a, b = view.doc.editor.add_node("Class", 50, 50), view.doc.editor.add_node("Class", 350, 50)
        edge = view.doc.editor.connect(tool_by_name(DT.CLASS, "Composition"), a, b)
        self.settle()
        view.open_properties(edge)
        dlg = view.dialog
        self.assertEqual(list(dlg.widgets), ["start_label", "middle_label", "end_label", "directionality", "aggregation_type"])
        dlg.widgets["aggregation_type"][2].set("Aggregation")
        dlg.widgets["aggregation_type"][1].event_generate("<<ComboboxSelected>>")
        self.settle()
        self.assertEqual(edge.props["aggregation_type"], "Aggregation")
        self.assertEqual(len(view.doc.diagram.edges), 1)

    def test_italic_and_underline_markup_are_drawn_in_canvas(self):
        view = self.open(DT.CLASS)
        c = view.doc.editor.add_node("Class", 50, 50)
        view.doc.editor.set_properties(c, {"name": "/Shape/", "attributes": "_count_"})
        self.settle()
        fonts = {view.canvas.itemcget(i, "text"): str(view.canvas.itemcget(i, "font"))
                 for i in view.canvas.find_all() if view.canvas.type(i) == "text"}
        self.assertIn("italic", fonts["Shape"])
        self.assertIn("underline", fonts["count"])


@unittest.skipUnless(HAS_TK, "Tkinter/display indisponível")
class Phase6UiTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.root = tk.Tk()
        self.app = App(self.root, Settings(self.dir / "settings.json"))
        self.errors = []
        self.app._show_error = self.errors.append
        self.root.update()

    def tearDown(self):
        try:
            self.root.destroy()
        except tk.TclError:
            pass
        self._tmp.cleanup()

    def settle(self, seconds: float = 0.0):
        import time
        end = time.time() + seconds
        while True:
            self.root.update_idletasks()
            self.root.update()
            if time.time() >= end:
                break
            time.sleep(0.01)

    def open(self, dtype):
        self.app.new_diagram(dtype)
        self.settle()
        self.root.focus_force()
        self.app.view.canvas.focus_force()
        self.settle()
        return self.app.view

    def messages(self):
        return [(l.cget("text"), l.cget("bg")) for l in self.app.overlay.labels]

    # ------------------------------------------------------------------ RF41 / RF42
    def test_notifications_appear_bottom_left_with_colors_and_expire(self):
        self.app.set_notification_duration(0.15)
        self.app.notifier.error("boom")
        self.app.notifier.success("done")
        self.settle()
        self.assertEqual(self.messages(), [("boom", "#c62828"), ("done", "#2e7d32")])
        for label in self.app.overlay.labels:
            info = label.place_info()
            self.assertEqual((float(info["relx"]), float(info["rely"]), info["anchor"]), (0.0, 1.0, "sw"))
        ys = [int(label.place_info()["y"]) for label in self.app.overlay.labels]
        self.assertEqual(len(set(ys)), 2)                                      # empilhadas, sem sobreposição
        self.settle(0.4)
        self.assertEqual(self.messages(), [])

    def test_duration_zero_disables_all_notifications(self):
        self.app.set_notification_duration(0)
        self.app.notifier.error("hidden")
        self.settle()
        self.assertEqual(self.messages(), [])

    def test_duration_dialog_range_default_and_persistence(self):
        from jetuml_py.ui.dialogs import NotificationDurationDialog
        dlg = NotificationDurationDialog(self.app)
        self.assertEqual(dlg.var.get(), "5")
        dlg.var.set("11"); dlg.ok(); self.settle()
        self.assertEqual(self.app.settings.notification_duration, 5)          # rejeitado
        self.assertEqual(len(self.messages()), 1)
        dlg.var.set("3"); dlg.ok(); self.settle()
        self.assertEqual((self.app.settings.notification_duration, self.app.notifier.duration), (3, 3))
        self.assertEqual(Settings(self.dir / "settings.json").notification_duration, 3)
        again = NotificationDurationDialog(self.app)
        again.restore()
        self.assertEqual(self.app.notifier.duration, 5)

    # ------------------------------------------------------------------ RF38 / RNF01
    def test_diagram_size_dialog_fixed_area_growth_and_defaults(self):
        from jetuml_py.ui.dialogs import DiagramSizeDialog
        view = self.open(DT.CLASS)
        region = lambda: [float(v) for v in str(self.app.view.canvas.cget("scrollregion")).split()]
        screen = (self.root.winfo_screenwidth(), self.root.winfo_screenheight())
        self.assertEqual(self.app.current_diagram_size(), (min(max(screen[0], 250), 4000), min(max(screen[1], 250), 4000)))
        dlg = DiagramSizeDialog(self.app)
        dlg.width_var.set("100"); dlg.ok(); self.settle()
        self.assertIsNone(self.app.settings.diagram_size)                      # fora da faixa 250–4000
        dlg.width_var.set("800"); dlg.height_var.set("600"); dlg.ok(); self.settle()
        self.assertEqual(self.app.settings.diagram_size, (800, 600))
        self.assertEqual(region()[2:], [800.0, 600.0])                         # vale para o diagrama já aberto
        view.doc.editor.add_node("Class", 1500, 100)
        self.settle()
        self.assertGreater(region()[2], 1500)                                  # cresce para comportar o conteúdo
        self.app.new_diagram(DT.STATE); self.settle()
        self.assertEqual(region()[2:], [800.0, 600.0])                         # e vale para novos diagramas
        DiagramSizeDialog(self.app).restore()
        self.assertIsNone(self.app.settings.diagram_size)

    # ------------------------------------------------------------------ RF39
    def test_font_change_affects_layout_and_drawing_and_restores(self):
        from jetuml_py.ui.dialogs import FontDialog
        view = self.open(DT.CLASS)
        node = view.doc.editor.add_node("Class", 40, 40)
        view.doc.editor.set_property(node, "name", "AVeryLongClassNameForFontTest")
        self.settle()
        w12 = node.width
        self.app.set_font("Courier", 20)
        self.settle()
        self.assertGreater(node.width, w12)
        fonts = {str(view.canvas.itemcget(i, "font")) for i in view.canvas.find_all() if view.canvas.type(i) == "text"}
        self.assertTrue(any("Courier" in f for f in fonts))
        self.assertEqual(Settings(self.dir / "settings.json").font, ("Courier", 20))
        self.assertEqual(self.app.metrics.font_size, 20)
        FontDialog(self.app).restore()
        self.settle()
        self.assertEqual(self.app.settings.font, ("Helvetica", 12))
        self.assertEqual(node.width, w12)
        dlg = FontDialog(self.app)
        dlg.size_var.set("abc"); dlg.ok(); self.settle()
        self.assertEqual(self.app.settings.font, ("Helvetica", 12))

    # ------------------------------------------------------------------ RF04
    def test_export_image_formats_by_extension_and_errors(self):
        view = self.open(DT.CLASS)
        view.doc.editor.add_node("Class", 40, 40)
        for ext in (".png", ".jpg", ".svg"):
            target = self.dir / f"out{ext}"
            self.app._ask_export_path = lambda doc, t=target: str(t)
            self.assertTrue(self.app.export_image())
            self.assertGreater(target.stat().st_size, 100)
        self.assertTrue((self.dir / "out.png").read_bytes().startswith(b"\x89PNG"))
        self.assertTrue((self.dir / "out.jpg").read_bytes().startswith(b"\xff\xd8"))
        self.assertEqual(self.messages()[-1][0], "Exported out.svg")
        self.app._ask_export_path = lambda doc: str(self.dir / "out.pdf")
        self.assertFalse(self.app.export_image())
        self.assertIn("Unsupported image format", self.errors[-1])
        self.app._ask_export_path = lambda doc: ""
        self.assertFalse(self.app.export_image())                              # cancelado

    # ------------------------------------------------------------------ RF05
    def test_copy_to_clipboard_menu_shortcut_toolbar_and_failure(self):
        from jetuml_py.app.image_clipboard import ClipboardUnavailable
        from jetuml_py.rendering.layout import apply_layout
        from jetuml_py.rendering.painter import content_bounds
        view = self.open(DT.CLASS)
        view.doc.editor.add_node("Class", 40, 40)
        self.settle()
        copied = []
        self.app._copy_image = copied.append
        self.app.file_menu.invoke(self.app.file_menu.index("Copy to Clipboard"))
        view.canvas.focus_force(); self.settle()
        self.root.event_generate("<Control-b>"); self.settle()
        tool = next(t for t in view.toolbar.tools if t.name == "To Clipboard")
        view.activate_tool(tool)
        self.assertEqual(len(copied), 3)
        apply_layout(view.doc.diagram, self.app.metrics)
        _, _, w, h = content_bounds(view.doc.diagram)
        self.assertEqual(copied[0].size, (w, h))                               # ajustada ao conteúdo, sem grade
        self.assertEqual(self.messages()[-1][1], "#2e7d32")
        def fail(image):
            raise ClipboardUnavailable("clipboard busy")
        self.app._copy_image = fail
        self.assertFalse(self.app.copy_diagram_image())
        self.assertEqual(self.messages()[-1], ("clipboard busy", "#c62828"))

    # ------------------------------------------------------------------ RF34
    def test_cut_copy_paste_between_diagrams_with_compatibility_errors(self):
        from jetuml_py.tools import tool_by_name
        view = self.open(DT.CLASS)
        a = view.doc.editor.add_node("Class", 40, 40)
        b = view.doc.editor.add_node("Class", 340, 40)
        view.doc.editor.connect(tool_by_name(DT.CLASS, "Association"), a, b)
        view.doc.editor.add_node("Note", 40, 300)
        self.settle()
        menu = lambda name: self.app.edit_menu.entrycget(name, "state")
        self.assertEqual((menu("Cut"), menu("Copy"), menu("Paste")), ("disabled",) * 3)
        view.canvas.focus_force(); view.canvas.event_generate("<Control-a>"); self.settle()
        view.canvas.event_generate("<Control-c>"); self.settle()
        self.assertEqual((menu("Cut"), menu("Copy"), menu("Paste")), ("normal",) * 3)
        view.canvas.event_generate("<Control-v>"); self.settle()
        self.assertEqual((len(view.doc.diagram.roots), len(view.doc.diagram.edges)), (6, 2))
        self.assertEqual(len(view.controller.selection.nodes), 3)              # colados ficam selecionados
        first_paste = (list(view.controller.selection.nodes), list(view.controller.selection.edges))
        pasted = view.controller.selection.nodes[0]
        self.assertEqual((pasted.x, pasted.y), (60, 60))
        self.app.paste(); self.settle()
        self.assertEqual(len(view.doc.diagram.roots), 9)                       # segunda colagem, outro deslocamento
        view.doc.editor.undo(); self.settle()
        self.assertEqual(len(view.doc.diagram.roots), 6)                       # um passo de desfazer por colagem
        view.controller.selection.set(*first_paste)
        self.app.cut(); self.settle()
        self.assertEqual(len(view.doc.diagram.roots), 3)
        other = self.open(DT.CLASS)
        self.assertTrue(self.app.paste())
        self.assertEqual(len(other.doc.diagram.roots), 3)
        state = self.open(DT.STATE)
        before = len(self.messages())
        self.assertFalse(self.app.paste())
        self.assertEqual(self.messages()[-1][1], "#c62828")                    # incompatível: erro notificado
        self.assertGreater(len(self.messages()), before)
        self.assertEqual(state.doc.diagram.roots, [])
        seq = self.open(DT.SEQUENCE)
        self.assertFalse(self.app.paste())
        self.assertIn("sequence", self.messages()[-1][0])

    # ------------------------------------------------------------------ RF40
    def test_dark_mode_themes_the_whole_interface_and_restores(self):
        from jetuml_py.ui.theming import DARK_UI, LIGHT_UI
        style = tk.ttk.Style(self.root) if hasattr(tk, "ttk") else __import__("tkinter.ttk", fromlist=["Style"]).Style(self.root)
        view = self.open(DT.CLASS)
        view.doc.editor.add_node("Class", 40, 40)
        for kind, state in (("<ButtonPress-1>", 0), ("<ButtonRelease-1>", 0x100)) * 2:
            view.canvas.event_generate(kind, x=60, y=60, state=state)
        self.settle()
        native_bg = style.lookup("TFrame", "background")
        self.app.dark_var.set(True)
        self.app.toggle_dark_mode()
        self.settle()
        self.assertEqual(style.lookup("TFrame", "background"), DARK_UI["bg"])
        self.assertEqual(style.lookup("TEntry", "fieldbackground"), DARK_UI["field"])
        self.assertEqual(str(self.root.cget("bg")), DARK_UI["bg"])
        self.assertEqual(str(self.app.file_menu.cget("bg")), DARK_UI["bg"])
        self.assertEqual(str(self.app.recent_menu.cget("fg")), DARK_UI["fg"])
        row = view.toolbar.rows[1]
        self.assertEqual((str(row[1].cget("bg")), str(row[3].cget("fg"))), (DARK_UI["bg"], DARK_UI["fg"]))
        self.assertEqual(str(view.toolbar.cget("bg")), DARK_UI["bg"])
        self.assertEqual(str(view.toolbar.rows[0][1].cget("bg")), DARK_UI["select"])    # ferramenta ativa
        self.assertEqual(view.canvas.cget("bg"), "#1e1e1e")
        view.open_properties(view.doc.diagram.roots[0]); self.settle()
        text = view.dialog.widgets["attributes"][1]
        self.assertEqual(str(text.cget("bg")), DARK_UI["field"])                        # painéis novos já nascem escuros
        view.dialog.close()
        self.app.dark_var.set(False)
        self.app.toggle_dark_mode()
        self.settle()
        self.assertEqual(style.lookup("TFrame", "background"), native_bg)
        self.assertEqual(str(row[1].cget("bg")), LIGHT_UI["bg"])
        self.assertEqual(str(self.app.file_menu.cget("bg")), LIGHT_UI["bg"])
        self.assertEqual(view.canvas.cget("bg"), "#ffffff")
        for w in (self.app.welcome, ):
            self.assertIsNotNone(w)


if __name__ == "__main__":
    unittest.main()

