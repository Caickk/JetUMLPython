"""Padrão Command + Composite: toda alteração do modelo é um comando reversível.

CompositeCommand agrupa vários comandos em uma única ação do usuário (um Ctrl+Z).
Os comandos não revalidam: a legalidade é decidida antes, pelo editor (validation.py).
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class Command(ABC):
    @abstractmethod
    def do(self) -> None: ...

    @abstractmethod
    def undo(self) -> None: ...


class CompositeCommand(Command):
    def __init__(self, commands, description: str = ""):
        self.commands = list(commands)
        self.description = description

    def do(self) -> None:
        for c in self.commands:
            c.do()

    def undo(self) -> None:
        for c in reversed(self.commands):
            c.undo()


class AddNodeCommand(Command):
    def __init__(self, diagram, node, parent=None, index=None):
        self.diagram, self.node, self.parent, self.index = diagram, node, parent, index

    def do(self) -> None:
        self.diagram.insert_node(self.node, self.parent, self.index)

    def undo(self) -> None:
        self.diagram.detach_node(self.node)


class AddEdgeCommand(Command):
    def __init__(self, diagram, edge):
        self.diagram, self.edge = diagram, edge

    def do(self) -> None:
        self.diagram.insert_edge(self.edge)

    def undo(self) -> None:
        self.diagram.remove_edge(self.edge)


class RemoveCommand(Command):
    """Remove nós (com descendentes), arestas e âncoras órfãs, restaurando posições ao desfazer."""

    def __init__(self, diagram, nodes=(), edges=()):
        self.diagram = diagram
        explicit = {n.id: n for n in nodes}
        doomed = set(explicit)
        for n in nodes:
            doomed.update(x.id for x in n.descendants())
        edge_map = {e.id: e for e in edges}
        for e in diagram.edges:
            if e.start.id in doomed or e.end.id in doomed:
                edge_map[e.id] = e
        for e in edge_map.values():
            if e.end.TYPE == "Point":
                explicit.setdefault(e.end.id, e.end)
        self._edge_ids = set(edge_map)
        self._tops = [n for n in explicit.values()
                      if not any(a.id in explicit for a in n.ancestors())]
        self._removed_edges = []
        self._removed_nodes = []

    def do(self) -> None:
        d = self.diagram
        ordered = [(i, e) for i, e in enumerate(d.edges) if e.id in self._edge_ids]
        for _, e in reversed(ordered):
            d.remove_edge(e)
        self._removed_edges = ordered
        self._removed_nodes = []
        for n in self._tops:
            parent, index = d.detach_node(n)
            self._removed_nodes.append((n, parent, index))

    def undo(self) -> None:
        d = self.diagram
        for n, parent, index in reversed(self._removed_nodes):
            d.insert_node(n, parent, index)
        for i, e in self._removed_edges:
            d.insert_edge(e, i)


class MoveCommand(Command):
    def __init__(self, diagram, nodes, dx: int, dy: int):
        ids = {n.id for n in nodes}
        self.diagram, self.dx, self.dy = diagram, dx, dy
        self.nodes = [n for n in nodes if not any(a.id in ids for a in n.ancestors())]

    def do(self) -> None:
        for n in self.nodes:
            n.move_by(self.dx, self.dy)
        self.diagram.notify("moved", self.nodes)

    def undo(self) -> None:
        for n in self.nodes:
            n.move_by(-self.dx, -self.dy)
        self.diagram.notify("moved", self.nodes)


class SetPropertyCommand(Command):
    def __init__(self, diagram, target, name: str, value):
        target.check_property(name, value)
        self.diagram, self.target, self.name = diagram, target, name
        self.new, self.old = value, target.props[name]

    def do(self) -> None:
        self.target.props[self.name] = self.new
        self.diagram.notify("property_changed", self.target)

    def undo(self) -> None:
        self.target.props[self.name] = self.old
        self.diagram.notify("property_changed", self.target)


class ReparentCommand(Command):
    def __init__(self, diagram, node, new_parent):
        self.diagram, self.node, self.new_parent = diagram, node, new_parent
        self._old = (node.parent, None)

    def do(self) -> None:
        self._old = self.diagram.detach_node(self.node)
        self.diagram.insert_node(self.node, self.new_parent)

    def undo(self) -> None:
        self.diagram.detach_node(self.node)
        self.diagram.insert_node(self.node, *self._old)


class UndoManager:
    def __init__(self):
        self._undo: list[Command] = []
        self._redo: list[Command] = []

    def execute(self, command: Command) -> None:
        command.do()
        self._undo.append(command)
        self._redo.clear()

    @property
    def top(self):
        """Último comando aplicado (marcador do estado salvo)."""
        return self._undo[-1] if self._undo else None

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    def undo(self) -> bool:
        if not self._undo:
            return False
        command = self._undo.pop()
        command.undo()
        self._redo.append(command)
        return True

    def redo(self) -> bool:
        if not self._redo:
            return False
        command = self._redo.pop()
        command.do()
        self._undo.append(command)
        return True

    def clear(self) -> None:
        self._undo.clear()
        self._redo.clear()
