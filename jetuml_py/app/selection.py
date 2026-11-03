"""Seleção de elementos (RF32, RF33). Guarda nós e arestas por identidade."""
from __future__ import annotations

from ..model.edges import Edge


def _has(items, x) -> bool:
    return any(i is x for i in items)


class Selection:
    def __init__(self):
        self.nodes: list = []
        self.edges: list = []

    @property
    def is_empty(self) -> bool:
        return not self.nodes and not self.edges

    def clear(self) -> None:
        self.nodes, self.edges = [], []

    def set(self, nodes=(), edges=()) -> None:
        self.nodes, self.edges = list(nodes), list(edges)

    def contains(self, element) -> bool:
        return _has(self.edges if isinstance(element, Edge) else self.nodes, element)

    def add(self, element) -> None:
        if not self.contains(element):
            (self.edges if isinstance(element, Edge) else self.nodes).append(element)

    def remove(self, element) -> None:
        target = self.edges if isinstance(element, Edge) else self.nodes
        target[:] = [x for x in target if x is not element]

    def toggle(self, element) -> None:
        self.remove(element) if self.contains(element) else self.add(element)

    def select_all(self, diagram) -> None:
        self.set([n for n in diagram.all_nodes() if n.TYPE != "Point"], diagram.edges)

    def prune(self, diagram) -> None:
        """Descarta elementos que não estão mais no diagrama (apagados ou desfeitos)."""
        alive_nodes = list(diagram.all_nodes())
        self.nodes = [n for n in self.nodes if _has(alive_nodes, n)]
        self.edges = [e for e in self.edges if _has(diagram.edges, e)]
