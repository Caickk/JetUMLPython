"""Persistência em JSON aberto e documentado (RF02, RF03, RNF02). Formato em docs/PLANO.md."""
from __future__ import annotations

import json
import os
from pathlib import Path

from .model.diagram import Diagram, DiagramType
from .model.edges import Edge
from .model.nodes import NODE_TYPES, create_node
from .validation import EDGES_BY_DIAGRAM, validate_placement

FORMAT_VERSION = 1


class DiagramFormatError(ValueError):
    """Arquivo inválido ou incompatível com o tipo de diagrama."""


def create_diagram(dtype: DiagramType) -> Diagram:
    return Diagram(dtype)


def node_to_dict(n) -> dict:
    return {"type": n.TYPE, "id": n.id, "x": n.x, "y": n.y,
            "properties": dict(n.props), "children": [node_to_dict(c) for c in n.children]}


def diagram_to_dict(d: Diagram) -> dict:
    return {
        "version": FORMAT_VERSION,
        "diagram": d.type.value,
        "nodes": [node_to_dict(n) for n in d.roots],
        "edges": [{"id": e.id, "type": e.kind, "start": e.start.id, "end": e.end.id,
                   "properties": dict(e.props)} for e in d.edges],
    }


def diagram_from_dict(data: dict) -> Diagram:
    try:
        dtype = DiagramType(data["diagram"])
        d = Diagram(dtype)
        registry: dict[str, object] = {}

        def build(nd: dict, parent):
            type_name = nd["type"]
            if type_name not in NODE_TYPES:
                raise DiagramFormatError(f"Unknown node type: {type_name}")
            result = validate_placement(dtype, type_name, parent)
            if not result:
                raise DiagramFormatError(result.message)
            node = create_node(type_name, nd["x"], nd["y"], node_id=nd["id"], **nd.get("properties", {}))
            registry[node.id] = node
            d.insert_node(node, parent)
            for child in nd.get("children", []):
                build(child, node)

        for nd in data["nodes"]:
            build(nd, None)
        for ed in data["edges"]:
            if ed["type"] not in EDGES_BY_DIAGRAM[dtype]:
                raise DiagramFormatError(f"Edge type {ed['type']} not valid in {dtype.label}")
            d.insert_edge(Edge(ed["type"], registry[ed["start"]], registry[ed["end"]],
                               edge_id=ed["id"], **ed.get("properties", {})))
        return d
    except DiagramFormatError:
        raise
    except (KeyError, ValueError, TypeError) as exc:
        raise DiagramFormatError(f"Invalid diagram file: {exc}") from exc


def save(diagram: Diagram, path) -> None:
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(diagram_to_dict(diagram), indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)  # escrita atômica: nunca deixa o arquivo pela metade


def load(path) -> Diagram:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DiagramFormatError(f"Not a valid JSON file: {exc}") from exc
    return diagram_from_dict(data)


def duplicate(diagram: Diagram) -> Diagram:
    """File > Duplicate (RF03): cópia independente do diagrama."""
    return diagram_from_dict(diagram_to_dict(diagram))
