"""Diálogos de View: duração das notificações (RF42), tamanho do diagrama (RF38) e fonte (RF39)."""
from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

from ..app import diagram_size
from ..app.settings import Settings
from ..notifications import NotificationService
from .theming import restyle


class _Dialog(tk.Toplevel):
    def __init__(self, app, title: str):
        super().__init__(app.root)
        self.app = app
        self.title(title)
        self.transient(app.root)
        self.resizable(False, False)
        self.body = ttk.Frame(self, padding=10)
        self.body.pack(fill="both", expand=True)
        self.buttons = ttk.Frame(self, padding=(10, 0, 10, 10))
        self.buttons.pack(fill="x")
        self.bind("<Escape>", lambda e: self.cancel())
        self.bind("<Return>", lambda e: self.ok())
        self.protocol("WM_DELETE_WINDOW", self.cancel)

    def add_buttons(self, restore_label: str) -> None:
        ttk.Button(self.buttons, text=restore_label, command=self.restore).pack(side="left")
        ttk.Button(self.buttons, text="Cancel", command=self.cancel).pack(side="right")
        ttk.Button(self.buttons, text="OK", command=self.ok).pack(side="right", padx=6)
        restyle(self, self.app.palette)

    def cancel(self) -> None:
        self.destroy()

    def ok(self) -> None: ...
    def restore(self) -> None: ...


class NotificationDurationDialog(_Dialog):
    def __init__(self, app):
        super().__init__(app, "Notification Duration")
        self.var = tk.StringVar(value=str(app.settings.notification_duration).rstrip("0").rstrip("."))
        ttk.Label(self.body, text="Seconds (0 turns notifications off):").grid(row=0, column=0, padx=(0, 8))
        ttk.Spinbox(self.body, from_=NotificationService.MIN_DURATION, to=NotificationService.MAX_DURATION,
                    increment=1, width=6, textvariable=self.var).grid(row=0, column=1)
        self.add_buttons("Restore Default")

    def ok(self) -> None:
        try:
            value = float(self.var.get())
        except ValueError:
            value = -1
        if not NotificationService.MIN_DURATION <= value <= NotificationService.MAX_DURATION:
            self.app.notifier.error("Notification duration must be between 0 and 10 seconds")
            return
        self.app.set_notification_duration(value)
        self.destroy()

    def restore(self) -> None:
        self.app.set_notification_duration(NotificationService.DEFAULT_DURATION)
        self.destroy()


class DiagramSizeDialog(_Dialog):
    def __init__(self, app):
        super().__init__(app, "Set Diagram Size")
        width, height = app.current_diagram_size()
        self.width_var, self.height_var = tk.StringVar(value=str(width)), tk.StringVar(value=str(height))
        for row, (label, var) in enumerate((("Width (px):", self.width_var), ("Height (px):", self.height_var))):
            ttk.Label(self.body, text=label).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=3)
            ttk.Spinbox(self.body, from_=diagram_size.MIN_SIZE, to=diagram_size.MAX_SIZE, increment=50,
                        width=8, textvariable=var).grid(row=row, column=1, pady=3)
        self.add_buttons("Restore Defaults")

    def ok(self) -> None:
        try:
            w, h = int(self.width_var.get()), int(self.height_var.get())
        except ValueError:
            w = h = -1
        error = diagram_size.validate_size(w, h)
        if error:
            self.app.notifier.error(error)
            return
        self.app.set_diagram_size((w, h))
        self.destroy()

    def restore(self) -> None:
        self.app.set_diagram_size(None)
        self.destroy()


class FontDialog(_Dialog):
    def __init__(self, app):
        super().__init__(app, "Change Font")
        family, size = app.settings.font
        self.family_var, self.size_var = tk.StringVar(value=family), tk.StringVar(value=str(size))
        ttk.Label(self.body, text="Font:").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=3)
        families = sorted(set(tkfont.families(app.root)))
        combo = ttk.Combobox(self.body, textvariable=self.family_var, values=families, width=30, state="readonly")
        combo.grid(row=0, column=1, pady=3)
        ttk.Label(self.body, text="Size:").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=3)
        ttk.Spinbox(self.body, from_=6, to=48, width=6, textvariable=self.size_var).grid(row=1, column=1, sticky="w")
        self.preview = tk.Label(self.body, text="AaBbYyZz «UML» 0123")
        self.preview.grid(row=2, column=0, columnspan=2, pady=(8, 0))
        combo.bind("<<ComboboxSelected>>", lambda e: self._update_preview())
        self.size_var.trace_add("write", lambda *_: self._update_preview())
        self._update_preview()
        self.add_buttons("Restore Default")

    def _update_preview(self) -> None:
        try:
            self.preview.configure(font=(self.family_var.get(), -int(self.size_var.get())))
        except (ValueError, tk.TclError):
            pass

    def ok(self) -> None:
        try:
            self.app.set_font(self.family_var.get(), int(self.size_var.get()))
        except ValueError:
            self.app.notifier.error("Font size must be a whole number between 6 and 48")
            return
        self.destroy()

    def restore(self) -> None:
        self.app.set_font(*Settings.DEFAULT_FONT)
        self.destroy()
