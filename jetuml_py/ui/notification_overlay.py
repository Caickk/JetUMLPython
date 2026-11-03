"""Notificações temporárias no canto inferior esquerdo da janela (RF41): erros em vermelho, confirmações em verde.

Cada notificação é um rótulo posicionado direto na janela (sem quadro de fundo), empilhado a partir do canto.
"""
from __future__ import annotations

import tkinter as tk

COLORS = {"error": "#c62828", "success": "#2e7d32"}
MARGIN, GAP = 10, 4


class NotificationOverlay:
    def __init__(self, root, notifier):
        self.root = root
        self.labels: list[tk.Label] = []          # do mais antigo (embaixo) ao mais novo (em cima)
        notifier.subscribe(self._show)

    def _show(self, notification) -> None:
        label = tk.Label(self.root, text=notification.message, bg=COLORS[notification.kind], fg="#ffffff",
                         padx=12, pady=6, anchor="w", justify="left", wraplength=480)
        label._no_theme = True                    # cores próprias, independentes do tema
        self.labels.append(label)
        self._layout()
        label.after(max(1, int(notification.duration * 1000)), lambda: self._remove(label))

    def _remove(self, label) -> None:
        if label in self.labels:
            self.labels.remove(label)
            label.destroy()
            self._layout()

    def _layout(self) -> None:
        offset = MARGIN
        for label in self.labels:
            label.update_idletasks()
            label.place(relx=0.0, rely=1.0, anchor="sw", x=MARGIN, y=-offset)
            offset += label.winfo_reqheight() + GAP
        self.lift()

    def lift(self) -> None:
        for label in self.labels:
            label.lift()
