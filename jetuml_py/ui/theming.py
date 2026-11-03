"""Modo claro/escuro de TODA a interface (RF40): estilos ttk + widgets tk clássicos (menus, textos, quadros)."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

LIGHT_UI = {"bg": "#f0f0f0", "fg": "#000000", "field": "#ffffff", "select": "#cde6ff", "button": "#e1e1e1"}
DARK_UI = {"bg": "#2b2b2b", "fg": "#e6e6e6", "field": "#3c3f41", "select": "#365880", "button": "#3c3f41"}


def palette(dark: bool) -> dict:
    return DARK_UI if dark else LIGHT_UI


def apply_theme(root: tk.Tk, dark: bool) -> dict:
    style = ttk.Style(root)
    native = getattr(root, "_native_ttk_theme", None) or style.theme_use()
    root._native_ttk_theme = native
    p = palette(dark)
    if dark:
        style.theme_use("clam")        # o tema nativo do Windows ignora cores; o clam respeita
        style.configure(".", background=p["bg"], foreground=p["fg"], fieldbackground=p["field"],
                        bordercolor=p["button"], lightcolor=p["bg"], darkcolor=p["bg"], troughcolor=p["bg"])
        style.configure("TNotebook", background=p["bg"])
        style.configure("TNotebook.Tab", background=p["button"], foreground=p["fg"])
        style.map("TNotebook.Tab", background=[("selected", p["select"])])
        style.configure("TButton", background=p["button"], foreground=p["fg"])
        style.map("TButton", background=[("active", p["select"])])
        style.configure("TEntry", fieldbackground=p["field"], foreground=p["fg"], insertcolor=p["fg"])
        style.configure("TSpinbox", fieldbackground=p["field"], foreground=p["fg"], arrowcolor=p["fg"])
        style.configure("TCombobox", fieldbackground=p["field"], foreground=p["fg"], background=p["button"],
                        arrowcolor=p["fg"])
        style.map("TCombobox", fieldbackground=[("readonly", p["field"])], foreground=[("readonly", p["fg"])])
        style.configure("TScrollbar", background=p["button"], arrowcolor=p["fg"])
    else:
        style.theme_use(native)
    root.configure(bg=p["bg"])
    restyle(root, p)
    return p


def restyle(widget, p: dict) -> None:
    """Aplica a paleta aos widgets tk clássicos de uma árvore (os ttk seguem o estilo global)."""
    from .toolbar import Toolbar
    if getattr(widget, "_no_theme", False):
        return
    if isinstance(widget, Toolbar):
        widget.apply_theme(p)
        return
    kind = widget.winfo_class()
    try:
        if kind in ("Frame", "Toplevel", "Tk"):
            widget.configure(bg=p["bg"])
        elif kind == "Label":
            widget.configure(bg=p["bg"], fg=p["fg"])
        elif kind == "Text":
            widget.configure(bg=p["field"], fg=p["fg"], insertbackground=p["fg"])
        elif kind == "Menu":
            widget.configure(bg=p["bg"], fg=p["fg"], activebackground=p["select"], activeforeground=p["fg"])
    except tk.TclError:
        pass
    for child in widget.winfo_children():
        restyle(child, p)
