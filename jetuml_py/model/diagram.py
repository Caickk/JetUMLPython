"""Diagrama: raiz do modelo. Notifica observadores a cada mudança (padrão Observer)."""
from __future__ import annotations

from enum import Enum

from ..geometry import Point
from .edges import Edge
from .nodes import Node


class DiagramType(Enum):
    CLASS = "ClassDiagram"
    SEQUENCE = "SequenceDiagram"
    STATE = "StateDiagram"
    OBJECT = "ObjectDiagram"
    USE_CASE = "UseCaseDiagram"

    @property
    def label(self) -> str:
        return {
            "ClassDiagram": "Class Diagram", "SequenceDiagram": "Sequence Diagram",
            "StateDiagram": "State Diagram", "ObjectDiagram": "Object Diagram",
            "UseCaseDiagram": "Use Case Diagram",
        }[self.value]


class Diagram:
    def __init__(self, dtype: DiagramType):
        self.type = dtype
        self.roots: list[Node] = []
        self.edges: list[Edge] = []
        self._listeners = []

    # --- observer
    def subscribe(self, callback) -> None:
        self._listeners.append(callback)

    def unsubscribe(self, callback) -> None:
        if callback in self._listeners:
            self._listeners.remove(callback)

    def contains(self, element) -> bool:
        """True se o nó ou a aresta (por identidade) ainda pertence ao diagrama."""
        pool = self.edges if isinstance(element, Edge) else self.all_nodes()
        return any(x is element for x in pool)

    def notify(self, event: str, subject=None) -> None:
        for cb in list(self._listeners):
            cb(event, subject)

    # --- consultas (somente leitura)
    def all_nodes(self):
        for root in self.roots:
            yield root
            yield from root.descendants()

    def find_node(self, node_id: str):
        return next((n for n in self.all_nodes() if n.id == node_id), None)

    def node_at(self, point: Point, types=None):
        """Nó mais interno sob o ponto (filhos têm prioridade), opcionalmente filtrado por tipo."""
        def search(nodes):
            for n in reversed(nodes):
                if n.TYPE == "Point":
                    continue
                hit = search(n.children)
                if hit is not None:
                    return hit
                if n.contains(point) and (types is None or n.TYPE in types):
                    return n
            return None
        return search(self.roots)

    # --- mutações de baixo nível (usadas apenas pelos comandos)
    def insert_node(self, node: Node, parent: Node | None = None, index: int | None = None) -> None:
        siblings = parent.children if parent is not None else self.roots
        siblings.insert(len(siblings) if index is None else index, node)
        node.parent = parent
        self.notify("node_added", node)

    def detach_node(self, node: Node):
        parent = node.parent
        siblings = parent.children if parent is not None else self.roots
        index = next(i for i, n in enumerate(siblings) if n is node)
        del siblings[index]
        node.parent = None
        self.notify("node_removed", node)
        return parent, index

    def insert_edge(self, edge: Edge, index: int | None = None) -> None:
        self.edges.insert(len(self.edges) if index is None else index, edge)
        self.notify("edge_added", edge)

    def remove_edge(self, edge: Edge) -> None:
        self.edges.remove(edge)
        self.notify("edge_removed", edge)
