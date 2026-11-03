"""Arestas do modelo UML.

Abordagem orientada a dados: cada 'kind' de aresta declara suas propriedades e valores
permitidos. Variantes (Composição/Agregação, Herança/Realização, Include/Extend) são
o mesmo kind com uma propriedade de tipo, o que permite trocá-las no painel (RF20).
"""
from __future__ import annotations

import uuid

_DIR2 = ("Unidirectional", "Bidirectional")
_DIR3 = ("Unspecified", "Unidirectional", "Bidirectional")

EDGE_KINDS: dict[str, dict] = {
    "Dependency": {"directionality": "Unidirectional", "middle_label": ""},
    "Generalization": {"generalization_type": "Inheritance", "directionality": "Unidirectional"},
    "Association": {"start_label": "", "middle_label": "", "end_label": "", "directionality": "Unspecified"},
    "Aggregation": {"start_label": "", "middle_label": "", "end_label": "",
                    "directionality": "Unspecified", "aggregation_type": "Aggregation"},
    "NoteConnector": {},
    "Call": {"middle_label": ""},
    "Return": {"middle_label": ""},
    "Transition": {"middle_label": ""},
    "Reference": {},
    "Collaboration": {"middle_label": ""},
    "UseCaseAssociation": {},
    "UseCaseDependency": {"dependency_type": "None"},
    "UseCaseGeneralization": {},
}

CHOICES: dict[tuple[str, str], tuple] = {
    ("Dependency", "directionality"): _DIR2,
    ("Generalization", "directionality"): _DIR2,
    ("Generalization", "generalization_type"): ("Inheritance", "Implementation"),
    ("Association", "directionality"): _DIR3,
    ("Aggregation", "directionality"): _DIR3,
    ("Aggregation", "aggregation_type"): ("Aggregation", "Composition"),
    ("UseCaseDependency", "dependency_type"): ("None", "Include", "Extend"),
}


class Edge:
    def __init__(self, kind: str, start, end, edge_id: str | None = None, **props):
        if kind not in EDGE_KINDS:
            raise KeyError(f"Unknown edge kind: {kind}")
        unknown = set(props) - set(EDGE_KINDS[kind])
        if unknown:
            raise KeyError(f"Unknown properties for {kind}: {sorted(unknown)}")
        self.id = edge_id or uuid.uuid4().hex
        self.kind = kind
        self.start = start
        self.end = end
        self.props = {**EDGE_KINDS[kind], **props}
        for name, value in self.props.items():
            self.check_property(name, value)

    def check_property(self, name: str, value) -> None:
        if name not in EDGE_KINDS[self.kind]:
            raise KeyError(f"{self.kind} has no property '{name}'")
        allowed = CHOICES.get((self.kind, name))
        if allowed is not None and value not in allowed:
            raise ValueError(f"Invalid value {value!r} for {name}; expected one of {allowed}")

    def __repr__(self) -> str:
        return f"<{self.kind} {self.start!r} -> {self.end!r}>"
