"""Ícones 32x32 das ferramentas, descritos como primitivas simples (sem arquivos de imagem)."""
from __future__ import annotations

_CALL = [("l", 4, 16, 24, 16), ("p", 29, 16, 21, 11, 21, 21)]
_RETURN = [("d", 28, 16, 6, 16), ("l", 13, 11, 6, 16, 13, 21)]
_ASSOC = [("l", 4, 28, 28, 4)]
_OPEN_ARROW = [("l", 23, 16, 27, 5, 16, 9)]
_TITLE_BOX = [("r", 4, 8, 17, 13), ("r", 4, 13, 28, 27)]

ICONS: dict[str, list] = {
    "Select": [("p", 8, 4, 8, 25, 13, 20, 17, 28, 20, 27, 16, 19, 23, 18)],
    "Class": [("r", 5, 5, 27, 27), ("l", 5, 12, 27, 12), ("l", 5, 19, 27, 19)],
    "Interface": [("r", 5, 5, 27, 27), ("l", 5, 16, 27, 16), ("l", 12, 10, 20, 10)],
    "Package": _TITLE_BOX,
    "Package Description": _TITLE_BOX + [("l", 8, 19, 24, 19), ("l", 8, 23, 20, 23)],
    "Note": [("h", 5, 5, 21, 5, 27, 11, 27, 27, 5, 27), ("l", 21, 5, 21, 11, 27, 11)],
    "Dependency": [("d", 4, 28, 27, 5)] + _OPEN_ARROW,
    "Inheritance": [("l", 4, 28, 20, 12), ("h", 27, 5, 23, 16, 16, 9)],
    "Realization": [("d", 4, 28, 20, 12), ("h", 27, 5, 23, 16, 16, 9)],
    "Association": _ASSOC,
    "Aggregation": [("h", 9, 17, 15, 23, 9, 29, 3, 23), ("l", 13, 19, 28, 4)],
    "Composition": [("p", 9, 17, 15, 23, 9, 29, 3, 23), ("l", 13, 19, 28, 4)],
    "Note Connector": [("d", 4, 28, 22, 10), ("h", 21, 3, 29, 3, 29, 11, 21, 11)],
    "To Clipboard": [("r", 8, 7, 24, 28), ("r", 12, 3, 20, 9), ("l", 12, 15, 20, 15), ("l", 12, 20, 20, 20)],
    "Implicit Parameter": [("r", 6, 4, 26, 12), ("d", 16, 12, 16, 29)],
    "Call": _CALL,
    "Return": _RETURN,
    "State": [("r", 4, 9, 28, 23)],
    "Initial State": [("O", 9, 9, 23, 23)],
    "Final State": [("o", 6, 6, 26, 26), ("O", 11, 11, 21, 21)],
    "Transition": _CALL,
    "Object": [("r", 4, 6, 28, 26), ("l", 4, 13, 28, 13), ("l", 10, 10, 22, 10)],
    "Field": [("r", 5, 11, 27, 21), ("l", 11, 16, 21, 16)],
    "Reference": [("O", 3, 14, 8, 19), ("l", 8, 16, 24, 16), ("p", 29, 16, 21, 11, 21, 21)],
    "Collaboration": _CALL,
    "Actor": [("o", 12, 3, 20, 11), ("l", 16, 11, 16, 20), ("l", 8, 14, 24, 14), ("l", 8, 29, 16, 20, 24, 29)],
    "Use Case": [("o", 3, 8, 29, 24)],
    "Include": [("d", 4, 28, 27, 5)] + _OPEN_ARROW,
    "Extend": [("d", 4, 28, 27, 5)] + _OPEN_ARROW,
    "Generalization": [("l", 4, 28, 20, 12), ("h", 27, 5, 23, 16, 16, 9)],
}


def draw_icon(canvas, name: str, fg: str = "#222222") -> None:
    for op, *c in ICONS.get(name, []):
        if op == "r":
            canvas.create_rectangle(*c, outline=fg)
        elif op == "l":
            canvas.create_line(*c, fill=fg)
        elif op == "d":
            canvas.create_line(*c, fill=fg, dash=(3, 2))
        elif op == "o":
            canvas.create_oval(*c, outline=fg)
        elif op == "O":
            canvas.create_oval(*c, outline=fg, fill=fg)
        elif op == "p":
            canvas.create_polygon(*c, outline=fg, fill=fg)
        elif op == "h":
            canvas.create_polygon(*c, outline=fg, fill="")
