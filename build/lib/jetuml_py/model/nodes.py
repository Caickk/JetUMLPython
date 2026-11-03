"""Nós do modelo UML.

Padrão Composite: um nó pode conter nós filhos (Package, Object, ImplicitParameter).
Cada tipo de nó declara suas propriedades editáveis (PROPS) e quais filhos aceita (ACCEPTS).
As coordenadas são sempre absolutas (relativas ao diagrama).
"""
from __future__ import annotations

import uuid
from typing import Iterator

from ..geometry import Rect

NODE_TYPES: dict[str, type] = {}


def node_type(cls):
    """Registra a classe no registro de tipos (usado por fábrica e persistência)."""
    NODE_TYPES[cls.TYPE] = cls
    return cls


class Node:
    TYPE = "Node"
    SIZE = (100, 60)
    PROPS: dict = {}
    ACCEPTS: tuple = ()

    def __init__(self, x: int = 0, y: int = 0, node_id: str | None = None, **props):
        unknown = set(props) - set(self.PROPS)
        if unknown:
            raise KeyError(f"Unknown properties for {self.TYPE}: {sorted(unknown)}")
        self.id = node_id or uuid.uuid4().hex
        self.x = x
        self.y = y
        self.parent: Node | None = None
        self.children: list[Node] = []
        self.props = {**self.PROPS, **props}
        self.width, self.height = self.SIZE  # ajustados pelo layout (derivados do conteúdo)

    @property
    def bounds(self) -> Rect:
        return Rect(self.x, self.y, self.width, self.height)

    def contains(self, point) -> bool:
        """Área sensível ao mouse (a linha de vida estende-se para baixo)."""
        return self.bounds.contains(point)

    def check_property(self, name: str, value) -> None:
        if name not in self.PROPS:
            raise KeyError(f"{self.TYPE} has no property '{name}'")
        if isinstance(self.PROPS[name], bool) and not isinstance(value, bool):
            raise ValueError(f"Property '{name}' expects a boolean")

    def descendants(self) -> Iterator[Node]:
        for child in self.children:
            yield child
            yield from child.descendants()

    def ancestors(self) -> Iterator[Node]:
        node = self.parent
        while node is not None:
            yield node
            node = node.parent

    def move_by(self, dx: int, dy: int) -> None:
        for n in (self, *self.descendants()):
            n.x += dx
            n.y += dy

    def __repr__(self) -> str:
        return f"<{self.TYPE} {self.props.get('name', '')!r} @({self.x},{self.y})>"


@node_type
class NoteNode(Node):
    TYPE = "Note"
    SIZE = (60, 40)
    PROPS = {"text": ""}


@node_type
class ClassNode(Node):
    TYPE = "Class"
    PROPS = {"name": "", "attributes": "", "methods": ""}


@node_type
class InterfaceNode(Node):
    TYPE = "Interface"
    PROPS = {"name": "", "methods": ""}


@node_type
class PackageNode(Node):
    TYPE = "Package"
    SIZE = (200, 140)
    PROPS = {"name": ""}
    ACCEPTS = ("Class", "Interface", "Package", "PackageDescription", "Note")


@node_type
class PackageDescriptionNode(Node):
    TYPE = "PackageDescription"
    PROPS = {"name": "", "contents": ""}


@node_type
class ObjectNode(Node):
    TYPE = "Object"
    SIZE = (120, 80)
    PROPS = {"name": ""}
    ACCEPTS = ("Field",)


@node_type
class FieldNode(Node):
    TYPE = "Field"
    SIZE = (100, 20)
    PROPS = {"name": "", "value": ""}


@node_type
class ActorNode(Node):
    TYPE = "Actor"
    SIZE = (50, 80)
    PROPS = {"name": ""}


@node_type
class UseCaseNode(Node):
    TYPE = "UseCase"
    SIZE = (110, 40)
    PROPS = {"name": ""}


@node_type
class StateNode(Node):
    TYPE = "State"
    SIZE = (80, 60)
    PROPS = {"name": ""}


@node_type
class InitialStateNode(Node):
    TYPE = "InitialState"
    SIZE = (20, 20)


@node_type
class FinalStateNode(Node):
    TYPE = "FinalState"
    SIZE = (20, 20)


@node_type
class ImplicitParameterNode(Node):
    """Linha de vida do diagrama de sequência; contém as caixas de ativação."""
    TYPE = "ImplicitParameter"
    SIZE = (80, 40)
    PROPS = {"name": ""}
    ACCEPTS = ("Call",)

    def stem_end(self) -> int:
        """Fim da linha tracejada: abaixo da última caixa de ativação."""
        bottoms = [c.y + c.height for c in self.children]
        return max([self.y + self.height + 40] + [b + 30 for b in bottoms])

    def contains(self, point) -> bool:
        if self.bounds.contains(point):
            return True
        cx = self.x + self.width // 2
        return abs(point.x - cx) <= 6 and self.y + self.height <= point.y <= self.stem_end()


@node_type
class CallNode(Node):
    """Caixa de ativação."""
    TYPE = "Call"
    SIZE = (16, 40)
    PROPS = {"open_bottom": False}


@node_type
class PointNode(Node):
    """Ponto fixo e invisível: extremidade ancorada de um conector de nota."""
    TYPE = "Point"
    SIZE = (0, 0)


def create_node(type_name: str, x: int = 0, y: int = 0, **kwargs) -> Node:
    """Fábrica de nós a partir do nome do tipo."""
    return NODE_TYPES[type_name](x, y, **kwargs)
