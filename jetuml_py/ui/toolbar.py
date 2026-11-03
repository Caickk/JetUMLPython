"""Barra lateral de ferramentas (RF07, RF08, RF10) e tooltips."""
from __future__ import annotations

import tkinter as tk

from ..tools import tooltip_text
from .icons import draw_icon

from .theming import LIGHT_UI


class Tooltip:
    def __init__(self, widget, text_fn, delay: int = 500):
        self.widget, self.text_fn, self.delay = widget, text_fn, delay
        self.window: tk.Toplevel | None = None
        self._job = None
        for w in (widget, *widget.winfo_children()):
            w.bind("<Enter>", self._enter, add="+")
            w.bind("<Leave>", self._leave, add="+")
            w.bind("<ButtonPress>", self._leave, add="+")

    def _enter(self, _e=None):
        if self._job is None and self.window is None:
            self._job = self.widget.after(self.delay, self.show)

    def _leave(self, _e=None):
        if self._job is not None:
            self.widget.after_cancel(self._job)
            self._job = None
        self.hide()

    def show(self):
        self._job = None
        self.hide()
        self.window = tk.Toplevel(self.widget)
        self.window.wm_overrideredirect(True)
        tk.Label(self.window, text=self.text_fn(), bg="#ffffe1", relief="solid", bd=1,
                 padx=4, pady=2, justify="left", wraplength=320).pack()
        x = self.widget.winfo_rootx() + self.widget.winfo_width() + 4
        y = self.widget.winfo_rooty() + 4
        self.window.wm_geometry(f"+{x}+{y}")

    def hide(self):
        if self.window is not None:
            self.window.destroy()
            self.window = None


class Toolbar(tk.Frame):
    def __init__(self, master, tools, keys: dict, on_select, show_hint: bool = False, verbose: bool = False,
                 palette: dict | None = None):
        p = palette or LIGHT_UI
        self.normal_bg, self.selected_bg, self.fg = p["bg"], p["select"], p["fg"]
        super().__init__(master, bg=self.normal_bg, bd=1, relief="groove")
        self.tools, self.on_select, self.verbose = tools, on_select, verbose
        self._selected = None
        self.rows: list[tuple] = []        # (tool, row, icon, label)
        self.tooltips: list[Tooltip] = []
        key_of = {id(t): k for k, t in keys.items()}
        for tool in tools:
            row = tk.Frame(self, bg=self.normal_bg, bd=1, relief="flat")
            icon = tk.Canvas(row, width=32, height=32, bg=self.normal_bg, highlightthickness=0)
            draw_icon(icon, tool.name, self.fg)
            label = tk.Label(row, text=f"{tool.name}  [{key_of.get(id(tool), '')}]", bg=self.normal_bg,
                             fg=self.fg, anchor="w")
            icon.grid(row=0, column=0)
            label.grid(row=0, column=1, sticky="w", padx=(2, 6))
            row.pack(fill="x", padx=1, pady=1)
            for w in (row, icon, label):
                w.bind("<Button-1>", lambda e, t=tool: self.on_select(t))
            self.tooltips.append(Tooltip(row, lambda t=tool: tooltip_text(t, self.verbose)))
            self.rows.append((tool, row, icon, label))
        self.set_hint(show_hint)

    def set_hint(self, show: bool) -> None:
        """Show Tool Hint: nome da ferramenta ao lado do ícone."""
        self.show_hint = show
        for _, _row, _icon, label in self.rows:
            label.grid() if show else label.grid_remove()

    def set_verbose(self, verbose: bool) -> None:
        self.verbose = verbose

    def select(self, tool) -> None:
        self._selected = tool
        for t, row, icon, label in self.rows:
            on = t is tool
            bg = self.selected_bg if on else self.normal_bg
            row.configure(bg=bg, relief="sunken" if on else "flat")
            icon.configure(bg=bg)
            label.configure(bg=bg)

    def apply_theme(self, p: dict) -> None:
        """RF40: cores da barra seguem o tema; os ícones são redesenhados na cor do texto."""
        self.normal_bg, self.selected_bg, self.fg = p["bg"], p["select"], p["fg"]
        self.configure(bg=self.normal_bg)
        for tool, _row, icon, label in self.rows:
            icon.delete("all")
            draw_icon(icon, tool.name, self.fg)
            label.configure(fg=self.fg)
        self.select(self._selected)
