"""DiagramEditor: fachada de edição usada pela interface (padrão Facade).

Cada operação valida (validation.py), cria comandos (commands.py) e notifica erros
(notifications.py). Rejeições 'silent' não geram notificação (RF30).
"""
from __future__ import annotations

from . import clipboard as elements
from .commands import (AddEdgeCommand, AddNodeCommand, CompositeCommand, MoveCommand,
                       RemoveCommand, ReparentCommand, SetPropertyCommand, UndoManager)
from .geometry import Point
from .model.diagram import Diagram
from .model.edges import Edge
from .model.nodes import create_node
from .notifications import NotificationService
from . import sequence_flow as sf
from .sequence_flow import check_lifeline_origin
from .tools import Tool
from .validation import EDGES_BY_DIAGRAM, validate_add_node, validate_edge, validate_placement
from .validation_result import reject


LAYOUT_OWNED = ("Field", "Call")  # posição calculada pelo layout; não é movida pelo usuário


class DiagramEditor:
    def __init__(self, diagram: Diagram, notifier: NotificationService | None = None):
        self.diagram = diagram
        self.notifier = notifier or NotificationService()
        self.undo_manager = UndoManager()

    def _reject(self, result):
        if not result.silent:
            self.notifier.error(result.message)
        return None

    # ------------------------------------------------------------------- nós
    def add_node(self, type_name: str, x: int, y: int, parent=None, pick=None):
        """'pick' é o ponto exato do clique (antes do snap), usado para achar o pacote/objeto pai."""
        if parent is None:  # clicar dentro de pacote/objeto cria o nó como filho (RF15, RF25)
            wanted = {"Object"} if type_name == "Field" else {"Package"}
            parent = self.diagram.node_at(pick or Point(x, y), wanted)
        result = validate_add_node(self.diagram, type_name, parent)
        if not result:
            return self._reject(result)
        node = create_node(type_name, x, y)
        self.undo_manager.execute(AddNodeCommand(self.diagram, node, parent))
        return node

    def attach(self, node, package):
        """Shift + soltar sobre o pacote (RF15)."""
        if package.TYPE != "Package" or node.TYPE not in package.ACCEPTS:
            return self._reject(reject(f"A {package.TYPE} cannot contain a {node.TYPE}"))
        if node is package or any(d is package for d in node.descendants()):
            return self._reject(reject("A package cannot be moved into itself"))
        if node.parent is not None and node.parent.TYPE != "Package":
            return self._reject(reject(f"A {node.TYPE} cannot be moved out of its parent"))
        if node.parent is package:
            return node
        self.undo_manager.execute(ReparentCommand(self.diagram, node, package))
        return node

    def detach(self, node):
        if node.parent is None or node.parent.TYPE != "Package":
            return self._reject(reject(f"A {node.TYPE} cannot be detached from its parent"))
        self.undo_manager.execute(ReparentCommand(self.diagram, node, None))
        return node

    def delete(self, nodes=(), edges=()) -> bool:
        nodes = [n for n in nodes if n.TYPE != "Point"]
        if not nodes and not edges:
            return False
        nodes = self._expand_sequence_deletion(nodes, edges)
        self.undo_manager.execute(RemoveCommand(self.diagram, nodes, edges))
        return True

    def _expand_sequence_deletion(self, nodes, edges):
        """No diagrama de sequência, apagar uma caixa leva junto tudo que ela chamou (e o que ela construiu),
        para não deixar chamadas órfãs que violariam a regra de uma única raiz."""
        d = self.diagram
        if d.type.value != "SequenceDiagram":
            return list(nodes)
        queue = []
        for n in nodes:
            queue += [n] if n.TYPE == "Call" else list(n.children)
        queue += [e.end for e in edges if e.kind == "Call" and e.end.TYPE == "Call"]
        result, seen = list(nodes), {n.id for n in nodes}
        while queue:
            box = queue.pop()
            if box.id not in seen:
                seen.add(box.id)
                result.append(box)
            for call in sf.calls_from(d, box):
                if call.end.TYPE == "Call":
                    if call.end.id not in seen:
                        queue.append(call.end)
                else:  # linha de vida construída por esta caixa: suas caixas também saem
                    queue += [c for c in call.end.children if c.id not in seen]
        return result

    def move(self, nodes, dx: int, dy: int) -> bool:
        nodes = [n for n in nodes if n.TYPE not in LAYOUT_OWNED and n.TYPE != "Point"]
        if nodes and (dx or dy):
            self.undo_manager.execute(MoveCommand(self.diagram, nodes, dx, dy))
            return True
        return False

    def set_property(self, target, name: str, value) -> bool:
        return self.set_properties(target, {name: value})

    def set_properties(self, target, changes: dict) -> bool:
        """Altera várias propriedades de um elemento em UM passo de desfazer (valida tudo antes)."""
        if not changes:
            return False
        try:
            commands = [SetPropertyCommand(self.diagram, target, n, v) for n, v in changes.items()]
        except (KeyError, ValueError) as exc:
            self._reject(reject(str(exc)))
            return False
        self.undo_manager.execute(commands[0] if len(commands) == 1 else CompositeCommand(commands, "properties"))
        return True

    # --------------------------------------------------------------- copiar/colar (RF34)
    def copy_elements(self, nodes, edges):
        return elements.extract(self.diagram, nodes, edges)

    def cut_elements(self, nodes, edges):
        data = elements.extract(self.diagram, nodes, edges)
        if data is not None:
            self.delete(nodes, edges)
        return data

    def paste(self, data, dx: int = 20, dy: int = 20):
        """Cola em um único passo de desfazer. Só se TODOS os elementos forem compatíveis com este diagrama;
        no diagrama de sequência nunca (geraria fluxo de controle inválido). Devolve (nós, arestas) ou None."""
        d = self.diagram
        if d.type.value == "SequenceDiagram":
            return self._reject(reject("Pasting into a sequence diagram is not allowed"))
        roots, edges = elements.instantiate(data, dx, dy)
        for root in roots:
            for n in (root, *root.descendants()):
                result = validate_placement(d.type, n.TYPE, n.parent)
                if not result:
                    return self._reject(reject(f"Cannot paste: {result.message}"))
        for e in edges:
            if e.kind not in EDGES_BY_DIAGRAM[d.type]:
                return self._reject(reject(f"Cannot paste: {e.kind} edges are not available in a {d.type.label}"))
        commands = [AddNodeCommand(d, n) for n in roots] + [AddEdgeCommand(d, e) for e in edges]
        self.undo_manager.execute(CompositeCommand(commands, "paste"))
        return [n for n in roots if n.TYPE != "Point"], edges

    # ----------------------------------------------------------------- arestas
    def connect(self, tool: Tool, start, end):
        if tool.action != "edge":
            raise ValueError("Not an edge tool")
        if tool.target == "Call":
            return self.add_call(start, end)
        return self._add_edge(tool.target, tool.preset, start, end)

    def _add_edge(self, kind, preset, start, end):
        result = validate_edge(self.diagram, kind, preset, start, end)
        if not result:
            return self._reject(result)
        edge = Edge(kind, start, end, **preset)
        self.undo_manager.execute(AddEdgeCommand(self.diagram, edge))
        return edge

    def anchor_note(self, note, x: int, y: int):
        """Arrastar a partir da nota até um ponto livre ancora a extremidade (RF14)."""
        point = create_node("Point", x, y)
        result = validate_edge(self.diagram, "NoteConnector", {}, note, point)
        if not result:
            return self._reject(result)
        edge = Edge("NoteConnector", note, point)
        self.undo_manager.execute(CompositeCommand(
            [AddNodeCommand(self.diagram, point), AddEdgeCommand(self.diagram, edge)], "anchor note"))
        return edge

    # --------------------------------------------------------------- sequência
    def add_call(self, start, end, constructor: bool = False, y: int | None = None):
        """RF27-RF29: cria chamada, caixas de ativação, autochamada ou chamada de construtor."""
        d = self.diagram
        if start.TYPE not in ("ImplicitParameter", "Call") or end.TYPE not in ("ImplicitParameter", "Call"):
            return self._reject(reject("Calls must connect lifelines or activation boxes"))
        target = end.parent if end.TYPE == "Call" else end
        commands = []
        if start.TYPE == "ImplicitParameter":
            result = check_lifeline_origin(d, start)
            if not result:
                return self._reject(result)
            caller = create_node("Call", start.x + start.SIZE[0] // 2 - 8,
                                 y if y is not None else start.y + start.SIZE[1] + 20)
            commands.append(AddNodeCommand(d, caller, start))
        else:
            caller = start
        if constructor:
            preset = {"middle_label": "«create»"}
            callee = target
        else:
            preset = {}
            callee = create_node("Call", target.x + target.SIZE[0] // 2 - 8,
                                 y if y is not None else caller.y + 20)
            commands.append(AddNodeCommand(d, callee, target))
        result = validate_edge(d, "Call", preset, caller, callee)
        if not result:
            return self._reject(result)
        edge = Edge("Call", caller, callee, **preset)
        commands.append(AddEdgeCommand(d, edge))
        self.undo_manager.execute(CompositeCommand(commands, "call"))
        return edge

    # ---------------------------------------------------------------- histórico
    def undo(self) -> bool:
        return self.undo_manager.undo()

    def redo(self) -> bool:
        return self.undo_manager.redo()
