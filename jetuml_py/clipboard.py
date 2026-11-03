"""Recortar, copiar e colar elementos (RF34).

Os elementos copiados viram dados serializados (mesmo formato do arquivo), então a colagem cria elementos NOVOS
(ids novos, nunca compartilhados) no mesmo diagrama ou em outro.
"""
from __future__ import annotations

from dataclasses import dataclass

from .model.diagram import DiagramType
from .model.edges import Edge
from .model.nodes import create_node
from .persistence import node_to_dict


@dataclass
class ClipboardData:
    diagram_type: DiagramType
    nodes: list[dict]
    edges: list[dict]


def extract(diagram, nodes, edges) -> ClipboardData | None:
    """Copia os nós (com todos os filhos) e as arestas selecionadas cujas pontas também foram copiadas.
    Âncoras de conectores de nota (Point) acompanham a aresta."""
    chosen = [n for n in nodes if n.TYPE != "Point"]
    ids = {n.id for n in chosen}
    tops = [n for n in chosen if not any(a.id in ids for a in n.ancestors())]
    if not tops:
        return None
    inside = set()
    for t in tops:
        inside.add(t.id)
        inside.update(d.id for d in t.descendants())
    node_dicts = [node_to_dict(t) for t in tops]
    edge_dicts = []
    for e in edges:
        end_ok = e.end.id in inside or e.end.TYPE == "Point"
        if e.start.id in inside and end_ok:
            if e.end.TYPE == "Point" and not any(nd["id"] == e.end.id for nd in node_dicts):
                node_dicts.append(node_to_dict(e.end))
            edge_dicts.append({"kind": e.kind, "start": e.start.id, "end": e.end.id, "properties": dict(e.props)})
    return ClipboardData(diagram.type, node_dicts, edge_dicts)


def instantiate(data: ClipboardData, dx: int, dy: int):
    """Constrói elementos novos a partir dos dados, deslocados em (dx, dy). Devolve (nós raiz, arestas)."""
    mapping: dict[str, object] = {}

    def build(nd, parent):
        node = create_node(nd["type"], nd["x"] + dx, nd["y"] + dy, **nd.get("properties", {}))
        node.parent = parent
        mapping[nd["id"]] = node
        node.children = [build(c, node) for c in nd.get("children", [])]
        return node

    roots = [build(nd, None) for nd in data.nodes]
    edges = [Edge(ed["kind"], mapping[ed["start"]], mapping[ed["end"]], **ed["properties"]) for ed in data.edges]
    return roots, edges
