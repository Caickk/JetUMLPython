"""Controlador de interação (RF11, RF14–RF16, RF32, RF33, RF35): converte gestos do mouse em operações do editor.

Não depende de Tk: recebe coordenadas do modelo (já sem zoom) e expõe 'overlay' (linha elástica, laço) e
'selection' para a interface desenhar. Máquina de estados: nenhum gesto → (press) → arrasto/laço/linha elástica → (release).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .app.selection import Selection
from .editor import LAYOUT_OWNED
from .geometry import Point
from .model.edges import Edge
from .rendering.hit import edge_at, elements_in_rect, hit_element
from .rendering.layout import apply_layout, package_extent
from .rendering.text import TextMetrics
from .tools import Tool, tool_by_name

DRAG_THRESHOLD = 3
GRID = 10


@dataclass
class Overlay:
    rubber: tuple | None = None   # (x1, y1, x2, y2)
    lasso: tuple | None = None


@dataclass
class _Drag:
    origin: Point
    hit: object
    pending_deselect: bool
    moved: bool = False
    nodes: list | None = None
    ref_start: tuple = (0, 0)
    applied: tuple = (0, 0)


@dataclass
class _Lasso:
    origin: Point
    ctrl: bool
    moved: bool = False


@dataclass
class _Rubber:
    start: object
    origin: Point
    moved: bool = False


def snap(value: float, grid: int = GRID) -> int:
    return int(round(value / grid) * grid)


class InteractionController:
    def __init__(self, document, on_change=None, on_node_created=None, metrics: TextMetrics | None = None):
        self.document = document
        self.editor = document.editor
        self.diagram = document.diagram
        self.metrics = metrics or TextMetrics()
        self.selection = Selection()
        self.overlay = Overlay()
        self.tool: Tool = tool_by_name(self.diagram.type, "Select")
        self.on_change = on_change or (lambda: None)
        self.on_node_created = on_node_created or (lambda node: None)
        self._state = None

    # ------------------------------------------------------------------ ferramenta
    def set_tool(self, tool: Tool) -> None:
        if tool.action == "clipboard":  # ação pontual, não um modo (tratada pela interface)
            return
        self.cancel()
        self.tool = tool
        self.on_change()

    @property
    def has_gesture(self) -> bool:
        return self._state is not None

    def _geometry(self) -> None:
        apply_layout(self.diagram, self.metrics)  # hit-test usa o mesmo layout que a pintura

    # ------------------------------------------------------------------ gestos
    def press(self, x: float, y: float, ctrl: bool = False, shift: bool = False) -> None:
        self.cancel()
        self._geometry()
        p = Point(x, y)
        action = self.tool.action
        if action == "select":
            self._press_select(p, ctrl)
        elif action == "node":
            self._create_node(p)
        elif action == "edge":
            start = self.diagram.node_at(p)
            if start is not None:
                self._state = _Rubber(start, p)
                self.overlay.rubber = (x, y, x, y)
        self.on_change()

    def drag(self, x: float, y: float, shift: bool = False) -> None:
        st, p = self._state, Point(x, y)
        if isinstance(st, _Drag):
            self._drag_selection(st, p)
        elif isinstance(st, _Lasso):
            st.moved = st.moved or math.hypot(x - st.origin.x, y - st.origin.y) >= DRAG_THRESHOLD
            self.overlay.lasso = (st.origin.x, st.origin.y, x, y)
        elif isinstance(st, _Rubber):
            st.moved = st.moved or math.hypot(x - st.origin.x, y - st.origin.y) >= DRAG_THRESHOLD
            self.overlay.rubber = (st.origin.x, st.origin.y, x, y)
        else:
            return
        self.on_change()

    def release(self, x: float, y: float, ctrl: bool = False, shift: bool = False) -> None:
        st, p = self._state, Point(x, y)
        self._state = None
        self.overlay = Overlay()
        if isinstance(st, _Drag):
            self._finish_drag(st, p, shift)
        elif isinstance(st, _Lasso):
            if st.moved:
                nodes, edges = elements_in_rect(self.diagram, st.origin.x, st.origin.y, x, y)
                if st.ctrl:
                    for e in (*nodes, *edges):
                        self.selection.add(e)
                else:
                    self.selection.set(nodes, edges)
        elif isinstance(st, _Rubber) and st.moved:
            self._finish_edge(st, p)
        self.on_change()

    def cancel(self) -> None:
        """Esc: aborta o gesto em andamento, restaurando posições temporárias."""
        st = self._state
        if isinstance(st, _Drag) and st.moved and st.nodes:
            for n in st.nodes:
                n.move_by(-st.applied[0], -st.applied[1])
        self._state = None
        self.overlay = Overlay()

    # ------------------------------------------------------------------ seleção e arrasto
    def _press_select(self, p: Point, ctrl: bool) -> None:
        hit = hit_element(self.diagram, p)
        sel = self.selection
        if hit is None:
            if not ctrl:
                sel.clear()
            self._state = _Lasso(p, ctrl)
            self.overlay.lasso = (p.x, p.y, p.x, p.y)
            return
        already = sel.contains(hit)
        if ctrl:
            sel.toggle(hit)
            if already:
                return
        elif not already:
            sel.set(*(([hit], []) if not isinstance(hit, Edge) else ([], [hit])))
        self._state = _Drag(p, hit, pending_deselect=already and not ctrl)

    def _movable(self) -> list:
        chosen = [n for n in self.selection.nodes if n.TYPE not in LAYOUT_OWNED and n.TYPE != "Point"]
        ids = {n.id for n in chosen}
        return [n for n in chosen if not any(a.id in ids for a in n.ancestors())]

    def _drag_selection(self, st: _Drag, p: Point) -> None:
        dx, dy = p.x - st.origin.x, p.y - st.origin.y
        if not st.moved:
            if math.hypot(dx, dy) < DRAG_THRESHOLD:
                return
            st.moved = True
            st.nodes = self._movable()
            if st.nodes:
                st.ref_start = (st.nodes[0].x, st.nodes[0].y)
        if not st.nodes:
            return
        ref_x, ref_y = st.ref_start
        sdx, sdy = snap(ref_x + dx) - ref_x, snap(ref_y + dy) - ref_y   # RF36: encaixe na grade
        step = (sdx - st.applied[0], sdy - st.applied[1])
        if step != (0, 0):
            for n in st.nodes:
                n.move_by(*step)
            st.applied = (sdx, sdy)

    def _finish_drag(self, st: _Drag, p: Point, shift: bool) -> None:
        if not st.moved:
            if st.pending_deselect:
                self.selection.remove(st.hit)
            return
        nodes = st.nodes or []
        for n in nodes:  # desfaz o deslocamento provisório e confirma como um único comando
            n.move_by(-st.applied[0], -st.applied[1])
        self.editor.move(nodes, *st.applied)
        if shift:
            for n in nodes:
                self._reparent(n, p)

    def _package_under(self, p: Point, node):
        banned = {node.id} | {d.id for d in node.descendants()}
        ancestors = list(node.ancestors())

        def inside(pkg) -> bool:
            # o pacote que já contém o nó cresce junto com ele: avalia-se sem a contribuição do nó
            if any(pkg is a for a in ancestors):
                return package_extent(pkg, self.metrics, exclude=node).contains(p)
            return pkg.contains(p)

        cands = [n for n in self.diagram.all_nodes() if n.TYPE == "Package" and n.id not in banned and inside(n)]
        return max(cands, key=lambda n: len(list(n.ancestors())), default=None)

    def _reparent(self, node, p: Point) -> None:
        """Shift ao soltar (RF15): sobre um pacote anexa; fora de pacote, desanexa."""
        package = self._package_under(p, node)
        if package is not None:
            self.editor.attach(node, package)
        elif node.parent is not None and node.parent.TYPE == "Package":
            self.editor.detach(node)

    # ------------------------------------------------------------------ criação de nós
    def _create_node(self, p: Point) -> None:
        hit = self.diagram.node_at(p)
        allowed = ("Package", "Object") + (("Field",) if self.tool.target == "Field" else ())
        if hit is not None and hit.TYPE not in allowed:
            return  # só cria em espaço vazio (ou dentro de pacote/objeto)
        node = self.editor.add_node(self.tool.target, snap(p.x), snap(p.y), pick=p)
        if node is not None:
            self.selection.set([node])
            self.on_node_created(node)

    # ------------------------------------------------------------------ criação de arestas
    def _finish_edge(self, st: _Rubber, p: Point) -> None:
        start, end, tool = st.start, self.diagram.node_at(p), self.tool
        if tool.target == "NoteConnector" and start.TYPE == "Note":
            edge = self.editor.anchor_note(start, int(p.x), int(p.y))        # RF14: ponto fixo
        elif end is None:
            return
        elif tool.target == "Call":
            ctor = (end.TYPE == "ImplicitParameter" and end.y <= p.y <= end.y + end.height
                    and not (start.TYPE == "Call" and start.parent is end))
            edge = self.editor.add_call(start, end, constructor=ctor)         # RF27–RF29
        else:
            edge = self.editor.connect(tool, start, end)                      # RF16, RF19
        if edge is not None:
            self.selection.set([], [edge])

    # ------------------------------------------------------------------ comandos de edição
    def select_all(self) -> None:
        self.selection.select_all(self.diagram)
        self.on_change()

    def delete_selection(self) -> bool:
        self.selection.prune(self.diagram)
        done = self.editor.delete(self.selection.nodes, self.selection.edges)
        self.selection.clear()
        self.on_change()
        return done
