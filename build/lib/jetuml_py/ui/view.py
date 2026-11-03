"""Área de um diagrama: barra de ferramentas + Canvas (rolagem, zoom, tema, mouse, teclado, menu de contexto)."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..app.properties import fields_for
from ..interaction import InteractionController
from ..rendering.edge_paths import compute_edge_paths
from ..rendering.layout import apply_layout
from ..rendering.painter import DARK, LIGHT, DiagramPainter, content_bounds
from ..tools import TOOLBARS, shortcut_map
from .tk_renderer import TkRenderer
from ..geometry import Point
from ..model.edges import Edge
from ..rendering.edge_paths import compute_edge_paths
from ..rendering.hit import hit_element
from .properties_dialog import PropertiesDialog
from .toolbar import Toolbar

ACCENT = "#0078d7"
HANDLE = 3


class DiagramView(ttk.Frame):
    def __init__(self, master, doc, app):
        super().__init__(master)
        self.doc, self.app = doc, app
        self.keys = shortcut_map(doc.diagram.type)
        self.dialog: PropertiesDialog | None = None
        self.controller = InteractionController(doc, on_change=self._controller_changed,
                                                on_node_created=self._node_created, metrics=app.metrics)
        s = app.settings
        self.toolbar = Toolbar(self, TOOLBARS[doc.diagram.type], self.keys, self.activate_tool,
                               s.show_tool_hint, s.verbose_tooltips, app.palette)
        self.toolbar.select(self.controller.tool)
        self.canvas = tk.Canvas(self, highlightthickness=0, takefocus=True)
        vbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        hbar = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)
        self.toolbar.grid(row=0, column=0, rowspan=2, sticky="ns")
        self.canvas.grid(row=0, column=1, sticky="nsew")
        vbar.grid(row=0, column=2, sticky="ns")
        hbar.grid(row=1, column=1, sticky="ew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self._pending = None
        doc.diagram.subscribe(lambda *_: self.schedule_redraw())  # Observer: o modelo não conhece a UI
        c = self.canvas
        c.bind("<Configure>", lambda e: self.schedule_redraw())
        c.bind("<MouseWheel>", lambda e: c.yview_scroll(-1 if e.delta > 0 else 1, "units"))
        c.bind("<Shift-MouseWheel>", lambda e: c.xview_scroll(-1 if e.delta > 0 else 1, "units"))
        c.bind("<Button-4>", lambda e: c.yview_scroll(-1, "units"))
        c.bind("<Button-5>", lambda e: c.yview_scroll(1, "units"))
        c.bind("<ButtonPress-1>", self._on_press)
        c.bind("<B1-Motion>", self._on_motion)
        c.bind("<ButtonRelease-1>", self._on_release)
        c.bind("<Double-Button-1>", self._on_double_click)
        c.bind("<Control-Return>", lambda e: (self.open_selected_properties(), "break")[1])
        c.bind("<Button-3>", self._on_context_menu)
        c.bind("<Button-2>", self._on_context_menu)
        c.bind("<Key>", self._on_key)
        c.bind("<Delete>", lambda e: self.controller.delete_selection())
        c.bind("<Escape>", self._on_escape)
        for keys, action in ((("<Control-x>", "<Control-X>"), app.cut), (("<Control-c>", "<Control-C>"), app.copy),
                             (("<Control-v>", "<Control-V>"), app.paste)):
            for seq in keys:
                c.bind(seq, lambda e, f=action: (f(), "break")[1])
        for seq in ("<Control-a>", "<Control-A>"):
            c.bind(seq, lambda e: (self.controller.select_all(), "break")[1])

    # ------------------------------------------------------------------ ferramentas
    def activate_tool(self, tool) -> None:
        if tool.action == "clipboard":
            self.app.copy_diagram_image()      # ação pontual: não troca a ferramenta ativa
            return
        self.controller.set_tool(tool)
        self.toolbar.select(self.controller.tool)

    def _on_key(self, event) -> None:
        tool = self.keys.get(event.char.upper()) if event.char and event.char.isprintable() else None
        if tool is not None:
            self.activate_tool(tool)           # RF08: 1–9, 0, A, B…

    def _on_escape(self, _event) -> None:
        if self.controller.has_gesture:
            self.controller.cancel()
            self.controller.on_change()
        else:
            self.activate_tool(TOOLBARS[self.doc.diagram.type][0])

    def build_context_menu(self) -> tk.Menu:
        menu = tk.Menu(self.canvas, tearoff=False)
        for tool in TOOLBARS[self.doc.diagram.type]:
            key = next((k for k, t in self.keys.items() if t is tool), "")
            menu.add_command(label=tool.name, accelerator=key, command=lambda t=tool: self.activate_tool(t))
        return menu

    def _on_context_menu(self, event) -> None:
        """RF09: botão direito mostra as ferramentas da barra."""
        self.context_menu = self.build_context_menu()
        self.context_menu.tk_popup(event.x_root, event.y_root)

    # ------------------------------------------------------------------ mouse
    def _model_xy(self, event) -> tuple[float, float]:
        s = self.doc.zoom.factor
        return self.canvas.canvasx(event.x) / s, self.canvas.canvasy(event.y) / s

    def _on_press(self, event) -> None:
        self.canvas.focus_set()
        x, y = self._model_xy(event)
        self.controller.press(x, y, ctrl=bool(event.state & 0x4), shift=bool(event.state & 0x1))

    def _on_motion(self, event) -> None:
        x, y = self._model_xy(event)
        self.controller.drag(x, y, shift=bool(event.state & 0x1))

    def _on_release(self, event) -> None:
        x, y = self._model_xy(event)
        self.controller.release(x, y, ctrl=bool(event.state & 0x4), shift=bool(event.state & 0x1))

    # ------------------------------------------------------------------ propriedades (RF12, RF22)
    def open_properties(self, element) -> bool:
        if not fields_for(element):
            return False                       # ex.: estados inicial/final não têm propriedades textuais
        if self.dialog is not None:
            self.dialog.close()
        self.update_idletasks()
        s = self.doc.zoom.factor
        if isinstance(element, Edge):          # aresta: perto do início do caminho
            p = compute_edge_paths(self.doc.diagram)[element.id][0]
            ex, ey = p.x, p.y
        else:
            ex, ey = element.x + element.width, element.y
        at = (self.canvas.winfo_rootx() + int(ex * s) - int(self.canvas.canvasx(0)) + 12,
              self.canvas.winfo_rooty() + int(ey * s) - int(self.canvas.canvasy(0)))
        self.dialog = PropertiesDialog(self, element, at)
        return True

    def selected_element(self):
        sel = self.controller.selection
        items = [*sel.nodes, *sel.edges]
        return items[0] if len(items) == 1 else None

    def open_selected_properties(self) -> bool:
        element = self.selected_element()
        return self.open_properties(element) if element is not None else False

    def _on_double_click(self, event) -> None:
        if self.controller.tool.action != "select":
            return
        x, y = self._model_xy(event)
        element = hit_element(self.doc.diagram, Point(x, y))
        if element is None:
            return
        self.controller.selection.set(*(([], [element]) if isinstance(element, Edge) else ([element], [])))
        self.controller.on_change()
        self.open_properties(element)

    def _node_created(self, node) -> None:
        """RF12: com Auto Edit Node ativo, o painel abre ao criar um nó (nunca para arestas)."""
        if self.app.settings.auto_edit_node:
            self.open_properties(node)

    def _controller_changed(self) -> None:
        self.schedule_redraw()
        self.app._schedule_refresh()

    # ------------------------------------------------------------------ desenho
    def schedule_redraw(self) -> None:
        if self._pending is None:  # agrupa várias mudanças em uma única pintura
            self._pending = self.after_idle(self.redraw)

    def destroy(self) -> None:
        if self._pending is not None:
            self.after_cancel(self._pending)
            self._pending = None
        super().destroy()

    def redraw(self) -> None:
        self._pending = None
        d, s = self.doc.diagram, self.doc.zoom.factor
        self.controller.selection.prune(d)
        apply_layout(d, self.app.metrics)
        x0, y0, w, h = content_bounds(d)
        width, height = self.app.diagram_area(x0 + w, y0 + h)       # tamanho fixo, ampliado se o conteúdo exigir (RF38)
        theme = DARK if self.app.settings.dark_mode else LIGHT
        family, size = self.app.settings.font
        painter = DiagramPainter(TkRenderer(self.canvas, s, family, size), theme, self.app.metrics)
        painter.paint(d, show_grid=self.app.settings.show_grid, area=(0, 0, int(width), int(height)))
        self._draw_overlay(s)

    def _draw_overlay(self, s: float) -> None:
        """Destaque da seleção, linha elástica e laço (não fazem parte do modelo nem da exportação)."""
        c, sel, ov = self.canvas, self.controller.selection, self.controller.overlay

        def square(x, y):
            c.create_rectangle(x * s - HANDLE, y * s - HANDLE, x * s + HANDLE, y * s + HANDLE,
                               fill=ACCENT, outline=ACCENT, tags="overlay")
        for n in sel.nodes:
            c.create_rectangle(n.x * s, n.y * s, (n.x + n.width) * s, (n.y + n.height) * s,
                               outline=ACCENT, dash=(4, 3), tags="overlay")
            for px in (n.x, n.x + n.width):
                for py in (n.y, n.y + n.height):
                    square(px, py)
        if sel.edges:
            paths = compute_edge_paths(self.doc.diagram)
            for e in sel.edges:
                for p in paths[e.id]:
                    square(p.x, p.y)
        if ov.rubber:
            x1, y1, x2, y2 = ov.rubber
            c.create_line(x1 * s, y1 * s, x2 * s, y2 * s, fill=ACCENT, dash=(5, 3), width=2, tags="overlay")
        if ov.lasso:
            x1, y1, x2, y2 = ov.lasso
            c.create_rectangle(x1 * s, y1 * s, x2 * s, y2 * s, outline=ACCENT, dash=(4, 3), tags="overlay")
