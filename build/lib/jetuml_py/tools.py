"""Ferramentas da barra lateral por tipo de diagrama (RF07) e atalhos (RF08)."""
from __future__ import annotations

from dataclasses import dataclass, field

from .model.diagram import DiagramType as DT


@dataclass
class Tool:
    name: str
    action: str            # "select" | "node" | "edge" | "clipboard"
    target: str = ""       # tipo de nó ou kind de aresta
    preset: dict = field(default_factory=dict)


def _node(name: str) -> Tool:
    return Tool(name, "node", name.replace(" ", ""))


def _edge(name: str, kind: str, **preset) -> Tool:
    return Tool(name, "edge", kind, preset)


_SELECT = Tool("Select", "select")
SELECT_TOOL = _SELECT
_CLIP = Tool("To Clipboard", "clipboard")
_NOTE = _node("Note")
_CONNECTOR = _edge("Note Connector", "NoteConnector")

TOOLBARS: dict[DT, list[Tool]] = {
    DT.CLASS: [
        _SELECT, _node("Class"), _node("Interface"), _node("Package"), _node("Package Description"), _NOTE,
        _edge("Dependency", "Dependency"),
        _edge("Inheritance", "Generalization", generalization_type="Inheritance"),
        _edge("Realization", "Generalization", generalization_type="Implementation"),
        _edge("Association", "Association"),
        _edge("Aggregation", "Aggregation", aggregation_type="Aggregation"),
        _edge("Composition", "Aggregation", aggregation_type="Composition"),
        _CONNECTOR, _CLIP,
    ],
    DT.SEQUENCE: [_SELECT, _node("Implicit Parameter"), _NOTE, _edge("Call", "Call"),
                  _edge("Return", "Return"), _CONNECTOR, _CLIP],
    DT.STATE: [_SELECT, _node("State"), _node("Initial State"), _node("Final State"), _NOTE,
               _edge("Transition", "Transition"), _CONNECTOR, _CLIP],
    DT.OBJECT: [_SELECT, _node("Object"), _node("Field"), _NOTE, _edge("Reference", "Reference"),
                _edge("Collaboration", "Collaboration"), _CONNECTOR, _CLIP],
    DT.USE_CASE: [_SELECT, _node("Actor"), _node("Use Case"), _NOTE,
                  _edge("Association", "UseCaseAssociation"),
                  _edge("Include", "UseCaseDependency", dependency_type="Include"),
                  _edge("Extend", "UseCaseDependency", dependency_type="Extend"),
                  _edge("Generalization", "UseCaseGeneralization"), _CONNECTOR, _CLIP],
}

SHORTCUT_KEYS = "1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def shortcut_map(dtype: DT) -> dict[str, Tool]:
    """'1' para a primeira ferramenta, ..., '9', '0', 'A', 'B'... de cima para baixo."""
    return dict(zip(SHORTCUT_KEYS, TOOLBARS[dtype]))


def tool_by_name(dtype: DT, name: str) -> Tool:
    return next(t for t in TOOLBARS[dtype] if t.name == name)


DESCRIPTIONS = {
    "Select": "select, move and lasso elements; Shift on drop attaches/detaches package children",
    "Class": "UML class with name, attributes and methods",
    "Interface": "UML interface with name and methods",
    "Package": "package that can contain classes, interfaces, packages and notes",
    "Package Description": "box describing the contents of a package",
    "Note": "free-text note",
    "Dependency": "dependency between classes, interfaces or packages (dashed arrow)",
    "Inheritance": "inheritance between classes or interfaces (hollow triangle)",
    "Realization": "interface realization (dashed line, hollow triangle)",
    "Association": "association between two elements",
    "Aggregation": "aggregation (hollow diamond)",
    "Composition": "composition (filled diamond)",
    "Note Connector": "links a node to a note; drag from a note to anchor it at a point",
    "To Clipboard": "copy the whole diagram as an image",
    "Implicit Parameter": "object lifeline in a sequence diagram",
    "Call": "call between lifelines or activation boxes (drop on a lifeline header to construct)",
    "Return": "return from an activation box to its caller",
    "State": "state of a state machine",
    "Initial State": "initial pseudo-state",
    "Final State": "final state",
    "Transition": "transition between states",
    "Object": "object with fields",
    "Field": "field inside an object (click inside the object)",
    "Reference": "reference from a field's value to an object",
    "Collaboration": "collaboration between two objects",
    "Actor": "actor of a use case diagram",
    "Use Case": "use case",
    "Include": "include dependency between use cases",
    "Extend": "extend dependency between use cases",
    "Generalization": "generalization between actors or between use cases",
}


def tooltip_text(tool: Tool, verbose: bool = False) -> str:
    """Tooltip do RF10: tipo do elemento; no modo verboso, com descrição estendida."""
    if verbose and tool.name in DESCRIPTIONS:
        return f"{tool.name}: {DESCRIPTIONS[tool.name]}"
    return tool.name
