"""Janela principal: abas, boas-vindas, menus File/Edit/View, atalhos e ações (RF01–06, 21, 33–42, RNF03)."""
from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ..app import diagram_size, image_clipboard
from ..app.exporter import ExportError, export_diagram, pillow_available, supported_extensions
from ..app.properties import fields_for
from ..app.settings import Settings
from ..app.workspace import Workspace
from ..model.diagram import DiagramType
from ..notifications import NotificationService
from ..rendering.painter import LIGHT, render_image
from . import theming
from .dialogs import DiagramSizeDialog, FontDialog, NotificationDurationDialog
from .notification_overlay import NotificationOverlay
from .tk_renderer import TkTextMetrics
from .view import DiagramView

FILETYPES = [("JetUML diagrams", "*.json"), ("All files", "*.*")]
IMAGE_TYPES = {".svg": "SVG image", ".png": "PNG image", ".jpg": "JPEG image", ".jpeg": "JPEG image",
               ".gif": "GIF image", ".bmp": "BMP image", ".tif": "TIFF image", ".tiff": "TIFF image",
               ".webp": "WebP image"}


class App:
    def __init__(self, root: tk.Tk, settings: Settings | None = None):
        self.root = root
        self.settings = settings or Settings()
        self.notifier = NotificationService()
        self.notifier.duration = self.settings.notification_duration
        self.workspace = Workspace(self.settings, self.notifier)
        self.metrics = TkTextMetrics(*self.settings.font)
        self.palette = theming.palette(self.settings.dark_mode)
        self.views: dict[int, DiagramView] = {}
        self.clipboard_data = None          # elementos copiados (RF34), compartilhados entre diagramas
        self._paste_count = 0
        self._refresh_job = None
        root.title("JetUML (Python)")
        root.geometry("1000x700")
        self._build_menus()
        self.notebook = ttk.Notebook(root)
        self.welcome = self._build_welcome()
        self.overlay = NotificationOverlay(root, self.notifier)
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        self.workspace.subscribe(self._on_workspace_event)
        self._bind_shortcuts()
        root.protocol("WM_DELETE_WINDOW", self.exit)
        root.bind("<Destroy>", self._on_root_destroy)
        self.palette = theming.apply_theme(root, self.settings.dark_mode)
        self._refresh()

    # ----------------------------------------------------------------- caixas de diálogo (substituíveis em testes)
    def _ask_open_path(self):
        return filedialog.askopenfilename(title="Open", filetypes=FILETYPES)

    def _ask_save_path(self, doc):
        return filedialog.asksaveasfilename(title="Save As", defaultextension=".json", filetypes=FILETYPES,
                                            initialfile=os.path.splitext(doc.title)[0])

    def _ask_export_path(self, doc):
        exts = supported_extensions()
        types = [(IMAGE_TYPES[e], f"*{e}") for e in exts if e not in (".jpeg", ".tif")]
        return filedialog.asksaveasfilename(title="Export Image", defaultextension=exts[-1] if len(exts) > 1 else ".svg",
                                            filetypes=types, initialfile=os.path.splitext(doc.title)[0])

    def _ask_save_changes(self, doc):
        return messagebox.askyesnocancel("Unsaved changes", f"Save changes to {doc.title}?")

    def _show_error(self, message: str):
        messagebox.showerror("JetUML", message)

    def _copy_image(self, image):
        image_clipboard.copy_image(image)

    # ----------------------------------------------------------------- construção
    def _build_menus(self):
        bar = tk.Menu(self.root)
        self.file_menu = tk.Menu(bar, tearoff=False, postcommand=self._rebuild_recent)
        new_menu = tk.Menu(self.file_menu, tearoff=False)
        for dtype in DiagramType:
            new_menu.add_command(label=dtype.label, command=lambda t=dtype: self.new_diagram(t))
        self.file_menu.add_cascade(label="New", menu=new_menu)
        self.file_menu.add_command(label="Open...", accelerator="Ctrl+O", command=self.open_file)
        self.recent_menu = tk.Menu(self.file_menu, tearoff=False)
        self.file_menu.add_cascade(label="Recent Files", menu=self.recent_menu)
        self.file_menu.add_command(label="Close", accelerator="Ctrl+W", command=self.close_current)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Save", accelerator="Ctrl+S", command=self.save_current)
        self.file_menu.add_command(label="Save As...", command=self.save_as_current)
        self.file_menu.add_command(label="Duplicate", accelerator="Ctrl+D", command=self.duplicate_current)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Export Image...", command=self.export_image)
        self.file_menu.add_command(label="Copy to Clipboard", accelerator="Ctrl+B", command=self.copy_diagram_image)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", accelerator="Ctrl+Q", command=self.exit)
        bar.add_cascade(label="File", menu=self.file_menu)

        self.edit_menu = tk.Menu(bar, tearoff=False)
        self.edit_menu.add_command(label="Undo", accelerator="Ctrl+Z", command=self.undo)
        self.edit_menu.add_command(label="Redo", accelerator="Ctrl+Y", command=self.redo)
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label="Cut", accelerator="Ctrl+X", command=self.cut)
        self.edit_menu.add_command(label="Copy", accelerator="Ctrl+C", command=self.copy)
        self.edit_menu.add_command(label="Paste", accelerator="Ctrl+V", command=self.paste)
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label="Select All", accelerator="Ctrl+A", command=self.select_all)
        self.edit_menu.add_command(label="Delete", accelerator="Delete", command=self.delete_selection)
        self.edit_menu.add_command(label="Properties", accelerator="Ctrl+Enter", command=self.open_properties)
        bar.add_cascade(label="Edit", menu=self.edit_menu)

        self.view_menu = tk.Menu(bar, tearoff=False)
        self.view_menu.add_command(label="Zoom In", accelerator="Ctrl+=", command=self.zoom_in)
        self.view_menu.add_command(label="Zoom Out", accelerator="Ctrl+-", command=self.zoom_out)
        self.view_menu.add_command(label="Reset Zoom", accelerator="Ctrl+0", command=self.reset_zoom)
        self.view_menu.add_separator()
        self.grid_var = tk.BooleanVar(value=self.settings.show_grid)
        self.view_menu.add_checkbutton(label="Show Grid", variable=self.grid_var, command=self.toggle_grid)
        self.dark_var = tk.BooleanVar(value=self.settings.dark_mode)
        self.view_menu.add_checkbutton(label="Dark Mode", variable=self.dark_var, command=self.toggle_dark_mode)
        self.view_menu.add_separator()
        self.auto_edit_var = tk.BooleanVar(value=self.settings.auto_edit_node)
        self.view_menu.add_checkbutton(label="Auto Edit Node", variable=self.auto_edit_var,
                                       command=self.toggle_auto_edit)
        self.hint_var = tk.BooleanVar(value=self.settings.show_tool_hint)
        self.view_menu.add_checkbutton(label="Show Tool Hint", variable=self.hint_var, command=self.toggle_tool_hint)
        self.verbose_var = tk.BooleanVar(value=self.settings.verbose_tooltips)
        self.view_menu.add_checkbutton(label="Verbose Tooltips", variable=self.verbose_var,
                                       command=self.toggle_verbose_tooltips)
        self.view_menu.add_separator()
        self.view_menu.add_command(label="Set Diagram Size...", command=lambda: DiagramSizeDialog(self))
        self.view_menu.add_command(label="Change Font...", command=lambda: FontDialog(self))
        self.view_menu.add_command(label="Notification Duration...", command=lambda: NotificationDurationDialog(self))
        bar.add_cascade(label="View", menu=self.view_menu)
        self.root.configure(menu=bar)

    def _build_welcome(self) -> ttk.Frame:
        frame = ttk.Frame(self.root)
        inner = ttk.Frame(frame)
        inner.place(relx=0.5, rely=0.45, anchor="center")
        ttk.Label(inner, text="JetUML", font=("Helvetica", 28, "bold")).pack(pady=(0, 4))
        ttk.Label(inner, text="Create a new diagram").pack(pady=(0, 12))
        for dtype in DiagramType:
            ttk.Button(inner, text=dtype.label, width=24,
                       command=lambda t=dtype: self.new_diagram(t)).pack(pady=2)
        ttk.Button(inner, text="Open...", width=24, command=self.open_file).pack(pady=(12, 2))
        self.welcome_recent = ttk.Frame(inner)
        self.welcome_recent.pack(pady=(8, 0))
        return frame

    def _bind_shortcuts(self):
        def bind(keys, func):
            for k in keys:
                self.root.bind_all(k, lambda e, f=func: (f(), "break")[1])
        bind(("<Control-o>", "<Control-O>"), self.open_file)
        bind(("<Control-w>", "<Control-W>"), self.close_current)
        bind(("<Control-s>", "<Control-S>"), self.save_current)
        bind(("<Control-d>", "<Control-D>"), self.duplicate_current)
        bind(("<Control-b>", "<Control-B>"), self.copy_diagram_image)
        bind(("<Control-q>", "<Control-Q>"), self.exit)
        bind(("<Control-z>", "<Control-Z>"), self.undo)
        bind(("<Control-y>", "<Control-Y>"), self.redo)
        bind(("<Control-equal>", "<Control-plus>", "<Control-KP_Add>"), self.zoom_in)
        bind(("<Control-minus>", "<Control-KP_Subtract>"), self.zoom_out)
        bind(("<Control-Key-0>", "<Control-KP_0>"), self.reset_zoom)

    # ----------------------------------------------------------------- estado
    @property
    def doc(self):
        return self.workspace.active

    @property
    def view(self) -> DiagramView | None:
        return self.views.get(id(self.doc)) if self.doc else None

    def current_diagram_size(self) -> tuple[int, int]:
        return diagram_size.configured_size(self.settings, self.root.winfo_screenwidth(), self.root.winfo_screenheight())

    def diagram_area(self, content_right: float, content_bottom: float) -> tuple[int, int]:
        """Área do diagrama: o tamanho configurado, ampliado se o conteúdo (ex.: arquivo aberto) não couber (RF38)."""
        return diagram_size.effective_area(self.current_diagram_size(), content_right, content_bottom)

    def _rebuild_recent(self):
        self.recent_menu.delete(0, "end")
        recent = self.settings.recent_files
        for path in recent:
            self.recent_menu.add_command(label=path, command=lambda p=path: self.open_path(p))
        if not recent:
            self.recent_menu.add_command(label="(none)", state="disabled")

    def _refresh(self):
        """Sincroniza menus, títulos e a tela de boas-vindas com o estado do workspace."""
        has = self.doc is not None
        state = lambda ok: "normal" if ok else "disabled"
        for label in ("Close", "Save", "Save As...", "Duplicate", "Export Image...", "Copy to Clipboard"):
            self.file_menu.entryconfigure(label, state=state(has))
        undo_manager = self.doc.editor.undo_manager if has else None
        self.edit_menu.entryconfigure("Undo", state=state(has and undo_manager.can_undo))
        self.edit_menu.entryconfigure("Redo", state=state(has and undo_manager.can_redo))
        view = self.view
        has_sel = has and view is not None and not view.controller.selection.is_empty
        element = view.selected_element() if has and view is not None else None
        self.edit_menu.entryconfigure("Select All", state=state(has))
        self.edit_menu.entryconfigure("Delete", state=state(has_sel))
        self.edit_menu.entryconfigure("Cut", state=state(has_sel))
        self.edit_menu.entryconfigure("Copy", state=state(has_sel))
        self.edit_menu.entryconfigure("Paste", state=state(has and self.clipboard_data is not None))
        self.edit_menu.entryconfigure("Properties", state=state(element is not None and bool(fields_for(element))))
        for label in ("Zoom In", "Zoom Out", "Reset Zoom"):
            self.view_menu.entryconfigure(label, state=state(has))
        if has:
            self.view_menu.entryconfigure("Zoom In", state=state(self.doc.zoom.level < self.doc.zoom.MAX_LEVEL))
            self.view_menu.entryconfigure("Zoom Out", state=state(self.doc.zoom.level > self.doc.zoom.MIN_LEVEL))
        for doc in self.workspace.documents:
            v = self.views.get(id(doc))
            if v is not None:
                self.notebook.tab(v, text=doc.title + (" *" if doc.dirty else ""))
        self.root.title(f"JetUML (Python) - {self.doc.title}{' *' if self.doc.dirty else ''}" if has else "JetUML (Python)")
        if has:
            self.welcome.pack_forget()
            self.notebook.pack(fill="both", expand=True)
        else:
            self.notebook.pack_forget()
            self._fill_welcome_recent()
            self.welcome.pack(fill="both", expand=True)
        self.overlay.lift()

    def _fill_welcome_recent(self):
        for child in self.welcome_recent.winfo_children():
            child.destroy()
        for path in self.settings.recent_files[:5]:
            ttk.Button(self.welcome_recent, text=os.path.basename(path), width=24,
                       command=lambda p=path: self.open_path(p)).pack(pady=1)

    def _on_root_destroy(self, event):
        if event.widget is self.root and self._refresh_job is not None:
            self.root.after_cancel(self._refresh_job)
            self._refresh_job = None

    def _schedule_refresh(self):
        """Atualiza depois que o comando terminou de entrar na pilha de desfazer (e agrupa notificações)."""
        if self._refresh_job is None:
            self._refresh_job = self.root.after_idle(self._run_scheduled_refresh)

    def _run_scheduled_refresh(self):
        self._refresh_job = None
        self._refresh()

    def _on_workspace_event(self, event, doc):
        if event == "opened":
            view = DiagramView(self.notebook, doc, self)
            self.views[id(doc)] = view
            self.notebook.add(view, text=doc.title)
            doc.diagram.subscribe(lambda *_: self._schedule_refresh())
            self.notebook.select(view)
        elif event == "closed":
            view = self.views.pop(id(doc), None)
            if view is not None:
                self.notebook.forget(view)
                view.destroy()
        self._refresh()

    def _on_tab_changed(self, _event=None):
        selected = self.notebook.select()
        for doc in self.workspace.documents:
            view = self.views.get(id(doc))
            if view is not None and str(view) == selected:
                self.workspace.activate(doc)
        self._refresh()

    # ----------------------------------------------------------------- arquivos
    def new_diagram(self, dtype: DiagramType):
        return self.workspace.new(dtype)

    def open_file(self):
        path = self._ask_open_path()
        if path:
            return self.open_path(path)

    def open_path(self, path):
        doc = self.workspace.open(path)
        if doc is None:
            self._show_error(self.workspace.last_error)
        self._refresh()
        return doc

    def save_current(self) -> bool:
        if self.doc is None:
            return False
        if self.doc.path is None:
            return self.save_as_current()
        ok = self.workspace.save(self.doc)
        if not ok:
            self._show_error(self.workspace.last_error)
        self._refresh()
        return ok

    def save_as_current(self) -> bool:
        if self.doc is None:
            return False
        path = self._ask_save_path(self.doc)
        if not path:
            return False
        ok = self.workspace.save_as(self.doc, path)
        if not ok:
            self._show_error(self.workspace.last_error)
        self._refresh()
        return ok

    def _confirm_close(self, doc) -> bool:
        """True se o documento pode ser fechado (salvando ou descartando as alterações)."""
        if not doc.dirty:
            return True
        self.workspace.activate(doc)
        answer = self._ask_save_changes(doc)
        if answer is None:
            return False
        if answer:
            return self.save_current()
        return True

    def close_current(self) -> bool:
        doc = self.doc
        if doc is None or not self._confirm_close(doc):
            return False
        return self.workspace.close(doc, force=True)

    def duplicate_current(self):
        if self.doc is not None:
            return self.workspace.duplicate(self.doc)

    def exit(self) -> bool:
        for doc in list(self.workspace.documents):
            if not self._confirm_close(doc):
                return False
        if self._refresh_job is not None:
            self.root.after_cancel(self._refresh_job)
            self._refresh_job = None
        self.root.destroy()
        return True

    # ----------------------------------------------------------------- imagem (RF04, RF05)
    def export_image(self) -> bool:
        """File > Export Image: o formato vem da extensão escolhida em 'Save as type'."""
        if self.doc is None:
            return False
        path = self._ask_export_path(self.doc)
        if not path:
            return False
        try:
            export_diagram(self.doc.diagram, path, self.metrics, self.settings.font[0])
        except ExportError as exc:
            self._show_error(str(exc))
            return False
        self.notifier.success(f"Exported {os.path.basename(path)}")
        return True

    def copy_diagram_image(self) -> bool:
        """Copia o diagrama inteiro, sem grade e ajustado ao conteúdo; confirma por notificação (RF05)."""
        if self.doc is None:
            return False
        if not pillow_available():
            self.notifier.error("Copying an image requires the Pillow package (pip install pillow)")
            return False
        try:
            self._copy_image(render_image(self.doc.diagram, LIGHT, self.metrics, self.settings.font[0]))
        except image_clipboard.ClipboardUnavailable as exc:
            self.notifier.error(str(exc))
            return False
        self.notifier.success("Diagram copied to the clipboard")
        return True

    # ----------------------------------------------------------------- edição
    def undo(self):
        if self.doc is not None:
            self.doc.editor.undo()
            self._refresh()

    def redo(self):
        if self.doc is not None:
            self.doc.editor.redo()
            self._refresh()

    def select_all(self):
        if self.view is not None:
            self.view.controller.select_all()

    def delete_selection(self):
        if self.view is not None:
            self.view.controller.delete_selection()
            self.view.canvas.focus_set()

    def open_properties(self):
        if self.view is not None:
            self.view.open_selected_properties()

    def copy(self) -> bool:
        view = self.view
        if view is None:
            return False
        sel = view.controller.selection
        data = self.doc.editor.copy_elements(sel.nodes, sel.edges)
        if data is None:
            return False
        self.clipboard_data, self._paste_count = data, 0
        self._refresh()
        return True

    def cut(self) -> bool:
        view = self.view
        if view is None:
            return False
        sel = view.controller.selection
        data = self.doc.editor.cut_elements(sel.nodes, sel.edges)
        if data is None:
            return False
        self.clipboard_data, self._paste_count = data, 0
        sel.clear()
        view.controller.on_change()
        return True

    def paste(self) -> bool:
        """RF34: cola no diagrama ativo (pode ser outro); incompatibilidades geram notificação de erro."""
        view = self.view
        if view is None or self.clipboard_data is None:
            return False
        offset = 20 * (self._paste_count + 1)
        result = self.doc.editor.paste(self.clipboard_data, offset, offset)
        if result is None:
            return False
        self._paste_count += 1
        view.controller.selection.set(*result)
        view.controller.on_change()
        return True

    # ----------------------------------------------------------------- visualização
    def _zoom(self, change: bool):
        if change and self.view is not None:
            self.view.schedule_redraw()
        self._refresh()

    def zoom_in(self):
        if self.doc is not None:
            self._zoom(self.doc.zoom.zoom_in())

    def zoom_out(self):
        if self.doc is not None:
            self._zoom(self.doc.zoom.zoom_out())

    def reset_zoom(self):
        if self.doc is not None:
            self._zoom(self.doc.zoom.reset())

    def toggle_grid(self):
        self.settings.show_grid = self.grid_var.get()
        self._redraw_all()

    def toggle_dark_mode(self):
        self.settings.dark_mode = self.dark_var.get()
        self.palette = theming.apply_theme(self.root, self.settings.dark_mode)
        self._redraw_all()

    def toggle_auto_edit(self):
        self.settings.auto_edit_node = self.auto_edit_var.get()

    def toggle_tool_hint(self):
        self.settings.show_tool_hint = self.hint_var.get()
        for view in self.views.values():
            view.toolbar.set_hint(self.settings.show_tool_hint)

    def toggle_verbose_tooltips(self):
        self.settings.verbose_tooltips = self.verbose_var.get()
        for view in self.views.values():
            view.toolbar.set_verbose(self.settings.verbose_tooltips)

    def set_notification_duration(self, seconds: float) -> None:
        self.settings.notification_duration = seconds
        self.notifier.duration = seconds

    def set_diagram_size(self, size) -> None:
        self.settings.diagram_size = size          # None = padrão relativo à tela
        self._redraw_all()

    def set_font(self, family: str, size: int) -> None:
        """RF39: só a aparência do diagrama muda; o layout é recalculado com as novas medidas."""
        self.settings.font = (family, size)
        self.metrics = TkTextMetrics(family, size)
        for view in self.views.values():
            view.controller.metrics = self.metrics
        self._redraw_all()

    def _redraw_all(self):
        for view in self.views.values():
            view.schedule_redraw()


def main() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()
