"""Painel de propriedades (RF12, RF20, RF22, RF23, RF31).

Aplica as mudanças ao confirmar cada campo (sair do campo, Enter, escolher/ligar) em um passo de desfazer;
Tab/Shift+Tab navegam entre campos, Esc fecha, Ctrl+Q insere « ».
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..app.properties import STEREOTYPE, PropertiesModel
from ..model.edges import Edge
from .theming import restyle


class PropertiesDialog(tk.Toplevel):
    def __init__(self, view, element, at: tuple[int, int] | None = None):
        super().__init__(view)
        self.view, self.element = view, element
        self.model = PropertiesModel(view.doc.editor, element)
        self.widgets: dict[str, tuple[str, tk.Widget, tk.Variable | None]] = {}
        self._committing = False
        self._closed = False
        kind = element.kind if isinstance(element, Edge) else element.TYPE
        self.title(f"{kind} Properties")
        self.transient(view.winfo_toplevel())
        frame = ttk.Frame(self, padding=8)
        frame.pack(fill="both", expand=True)
        for row, spec in enumerate(self.model.fields):
            ttk.Label(frame, text=spec.label).grid(row=row, column=0, sticky="nw", padx=(0, 8), pady=3)
            self.widgets[spec.name] = self._make_widget(frame, spec, row)
        self._order = [w for _, w, _ in self.widgets.values()]
        restyle(self, view.app.palette)
        self.bind("<Escape>", lambda e: self.close())
        self.protocol("WM_DELETE_WINDOW", self.close)
        view.doc.diagram.subscribe(self._on_model_event)
        if at is not None:
            self.geometry(f"+{max(0, at[0])}+{max(0, at[1])}")
        if self._order:
            self.after_idle(self._focus_first)

    # ------------------------------------------------------------------ construção dos campos
    def _make_widget(self, frame, spec, row):
        value = self.element.props[spec.name]
        if spec.kind == "text":
            w = tk.Text(frame, width=36, height=5, wrap="word", undo=True)
            w.insert("1.0", value)
            w.bind("<Tab>", lambda e: self._move_focus(e.widget, +1))
            w.bind("<Shift-Tab>", lambda e: self._move_focus(e.widget, -1))
            w.bind("<ISO_Left_Tab>", lambda e: self._move_focus(e.widget, -1))
            self._bind_stereotype(w)
            w.bind("<FocusOut>", lambda e: self.commit())
            var = None
        elif spec.kind == "choice":
            var = tk.StringVar(value=value)
            w = ttk.Combobox(frame, textvariable=var, values=list(spec.choices), state="readonly", width=34)
            w.bind("<<ComboboxSelected>>", lambda e: self.commit())
        elif spec.kind == "bool":
            var = tk.BooleanVar(value=value)
            w = ttk.Checkbutton(frame, variable=var, command=self.commit)
        else:
            var = tk.StringVar(value=value)
            w = ttk.Entry(frame, textvariable=var, width=38)
            self._bind_stereotype(w)
            w.bind("<Return>", lambda e: self.commit())
            w.bind("<FocusOut>", lambda e: self.commit())
        w.grid(row=row, column=1, sticky="ew", pady=3)
        return spec.kind, w, var

    def _bind_stereotype(self, widget) -> None:
        for seq in ("<Control-q>", "<Control-Q>"):
            widget.bind(seq, self._insert_stereotype)   # "break": não aciona o atalho global de sair

    @staticmethod
    def _insert_stereotype(event):
        w = event.widget
        if isinstance(w, tk.Text):
            w.insert("insert", STEREOTYPE)
            w.mark_set("insert", "insert-1c")
        else:
            w.insert("insert", STEREOTYPE)
            w.icursor(w.index("insert") - 1)
        return "break"

    def _move_focus(self, widget, step: int):
        i = self._order.index(widget)
        self._order[(i + step) % len(self._order)].focus_set()
        return "break"

    def _focus_first(self) -> None:
        if self._closed:
            return
        self.focus_force()
        first = self._order[0]
        first.focus_set()
        if isinstance(first, ttk.Entry):
            first.select_range(0, "end")

    # ------------------------------------------------------------------ valores
    def read(self) -> dict:
        values = {}
        for name, (kind, widget, var) in self.widgets.items():
            values[name] = widget.get("1.0", "end-1c") if kind == "text" else var.get()
        return values

    def commit(self) -> bool:
        if self._closed or self._committing:
            return False
        self._committing = True
        try:
            return self.model.commit(self.read())
        finally:
            self._committing = False

    def _refresh_from_model(self) -> None:
        for name, (kind, widget, var) in self.widgets.items():
            value = self.element.props[name]
            if kind == "text":
                if widget.get("1.0", "end-1c") != value:
                    widget.delete("1.0", "end")
                    widget.insert("1.0", value)
            elif var.get() != value:
                var.set(value)

    def _on_model_event(self, event, subject) -> None:
        if self._closed or self._committing:
            return
        if event == "property_changed" and subject is self.element:
            self._refresh_from_model()                  # ex.: Ctrl+Z com o painel aberto
        else:
            self.after_idle(self._close_if_gone)

    def _close_if_gone(self) -> None:
        if not self._closed and not self.view.doc.diagram.contains(self.element):
            self.close(commit=False)

    # ------------------------------------------------------------------ fechar
    def close(self, commit: bool = True) -> None:
        if self._closed:
            return
        if commit:
            self.commit()
        self._closed = True
        self.view.doc.diagram.unsubscribe(self._on_model_event)
        self.view.dialog = None
        self.destroy()
        try:
            self.view.canvas.focus_set()
        except tk.TclError:
            pass
