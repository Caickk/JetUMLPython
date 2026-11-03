"""Regras de validação do modelo (RF13, RF15, RF18, RF19, RF25, RF30).

Estratégia: uma lista de regras (funções puras) por tipo de diagrama. A interface nunca
decide legalidade; ela consulta este módulo através do editor (mesma ideia de RNF03).
"""
from __future__ import annotations

from dataclasses import dataclass

from . import sequence_flow as sf
from .model.diagram import Diagram, DiagramType as DT
from .validation_result import OK, Result, reject

NODES_BY_DIAGRAM = {
    DT.CLASS: {"Class", "Interface", "Package", "PackageDescription", "Note"},
    DT.SEQUENCE: {"ImplicitParameter", "Call", "Note"},
    DT.STATE: {"State", "InitialState", "FinalState", "Note"},
    DT.OBJECT: {"Object", "Field", "Note"},
    DT.USE_CASE: {"Actor", "UseCase", "Note"},
}

EDGES_BY_DIAGRAM = {
    DT.CLASS: {"Dependency", "Generalization", "Association", "Aggregation", "NoteConnector"},
    DT.SEQUENCE: {"Call", "Return", "NoteConnector"},
    DT.STATE: {"Transition", "NoteConnector"},
    DT.OBJECT: {"Reference", "Collaboration", "NoteConnector"},
    DT.USE_CASE: {"UseCaseAssociation", "UseCaseDependency", "UseCaseGeneralization", "NoteConnector"},
}

_CI = {"Class", "Interface"}
_STATES = {"State", "InitialState", "FinalState"}
_AU = {"Actor", "UseCase"}
ENDPOINTS = {
    "Dependency": ({"Class", "Interface", "Package"},) * 2,
    "Generalization": (_CI, _CI),
    "Association": (_CI, _CI),
    "Aggregation": (_CI, _CI),
    "Transition": (_STATES, _STATES),
    "Reference": ({"Field"}, {"Object"}),
    "Collaboration": ({"Object"}, {"Object"}),
    "UseCaseAssociation": (_AU, _AU),
    "UseCaseDependency": ({"UseCase"}, {"UseCase"}),
    "UseCaseGeneralization": (_AU, _AU),
    "Call": ({"Call"}, {"Call", "ImplicitParameter"}),
    "Return": ({"Call"}, {"Call"}),
}


# ----------------------------------------------------------------------------- nós
def validate_placement(dtype: DT, type_name: str, parent) -> Result:
    """Tipo permitido no diagrama, pai compatível e filhos obrigatórios (RF15, RF25)."""
    if type_name != "Point" and type_name not in NODES_BY_DIAGRAM[dtype]:
        return reject(f"{type_name} cannot be used in a {dtype.label}")
    if parent is None:
        if type_name == "Field":
            return reject("A field must belong to an object")
        if type_name == "Call":
            return reject("An activation box must belong to a lifeline")
        return OK
    if type_name not in parent.ACCEPTS:
        return reject(f"A {parent.TYPE} cannot contain a {type_name}")
    return OK


def validate_add_node(diagram: Diagram, type_name: str, parent=None) -> Result:
    if type_name == "Call":
        return reject("Activation boxes are created through calls")
    if type_name == "Point":
        return reject("Anchor points are created by note connectors")
    return validate_placement(diagram.type, type_name, parent)


# --------------------------------------------------------------------------- arestas
@dataclass
class Ctx:
    diagram: Diagram
    kind: str
    props: dict
    start: object
    end: object


def _pair(e, a, b) -> bool:
    return (e.start is a and e.end is b) or (e.start is b and e.end is a)


def rule_duplicate(c: Ctx) -> Result:
    for e in c.diagram.edges:
        if e.kind == c.kind and _pair(e, c.start, c.end):
            return reject(f"Only one {c.kind} edge is allowed between the same two nodes")
    return OK


def rule_class_self(c: Ctx) -> Result:
    if c.start is c.end and c.kind in ("Dependency", "Generalization"):
        what = "dependency" if c.kind == "Dependency" else "inheritance"
        return reject(f"A node cannot have a self-{what}")
    return OK


def rule_class_cycle(c: Ctx) -> Result:
    if c.start is c.end or c.kind not in ("Dependency", "Association", "Aggregation", "Generalization"):
        return OK
    for e in c.diagram.edges:
        if e.kind == c.kind and e.start is c.end and e.end is c.start:
            if c.kind == "Generalization" and not (
                    e.props["generalization_type"] == "Inheritance"
                    and c.props.get("generalization_type", "Inheritance") == "Inheritance"):
                continue
            return reject(f"Back-and-forth {c.kind} edges are not allowed")
    return OK


def rule_assoc_aggr(c: Ctx) -> Result:
    if c.kind not in ("Association", "Aggregation"):
        return OK
    other = "Aggregation" if c.kind == "Association" else "Association"
    if any(e.kind == other and _pair(e, c.start, c.end) for e in c.diagram.edges):
        return reject("Association and aggregation cannot be combined between the same two classes")
    return OK


def rule_object_self(c: Ctx) -> Result:
    if c.kind == "Collaboration" and c.start is c.end:
        return reject("An object cannot collaborate with itself")
    return OK


def rule_object_cycle(c: Ctx) -> Result:
    if c.kind == "Collaboration" and c.start is not c.end:
        if any(e.kind == "Collaboration" and e.start is c.end and e.end is c.start for e in c.diagram.edges):
            return reject("Collaboration cycles between two objects are not allowed")
    return OK


def rule_usecase_self(c: Ctx) -> Result:
    if c.kind != "NoteConnector" and c.start is c.end:
        return reject("Actors and use cases cannot have self-associations, self-inheritance or self-dependencies")
    return OK


def rule_usecase_generalization(c: Ctx) -> Result:
    if c.kind == "UseCaseGeneralization" and c.start.TYPE != c.end.TYPE:
        return reject("Generalization must connect two actors or two use cases")
    return OK


def rule_state_transitions(c: Ctx) -> Result:
    if c.kind != "Transition":
        return OK
    if c.start.TYPE == "FinalState":
        return reject("A final state cannot have outgoing transitions")
    if c.end.TYPE == "InitialState":
        return reject("An initial state cannot have incoming transitions")
    same = [e for e in c.diagram.edges
            if e.kind == "Transition" and e.start is c.start and e.end is c.end]
    if c.start is c.end:
        if len(same) >= 2:
            return reject("A state accepts at most two self-transitions")
    elif len(same) >= 2:
        return reject("At most two transitions are allowed in each direction between two states")
    return OK


def rule_sequence(c: Ctx) -> Result:
    d, s, e = c.diagram, c.start, c.end
    if c.kind == "Call":
        if e.TYPE == "Call":
            if s is e:
                return reject("An activation box cannot call itself directly")
            if sf.incoming_call(d, e) is not None:
                return reject("An activation box cannot receive calls from several callers")
        else:  # chamada de construtor
            if s.parent is e:
                return reject("A lifeline cannot construct itself")
            if e.children or any(x.kind == "Call" and x.end is e for x in d.edges):
                return reject("This lifeline already exists in the control flow")
        return sf.check_call_source(d, s)
    if c.kind == "Return":
        call = sf.incoming_call(d, s)
        if call is None or call.start is not e or not sf.is_active(d, s):
            return reject("Return would break the control flow", silent=True)
    return OK


RULES = {
    DT.CLASS: [rule_class_self, rule_class_cycle, rule_duplicate, rule_assoc_aggr],
    DT.OBJECT: [rule_object_self, rule_object_cycle, rule_duplicate],
    DT.USE_CASE: [rule_usecase_self, rule_usecase_generalization, rule_duplicate],
    DT.STATE: [rule_state_transitions],
    DT.SEQUENCE: [rule_sequence, rule_duplicate],
}


def _check_endpoints(kind: str, s, e) -> Result:
    if kind == "NoteConnector":
        if s.TYPE == "Note" and e.TYPE == "Point":
            return OK
        if e.TYPE == "Note" and s.TYPE not in ("Note", "Point"):
            return OK
        return reject("A note connector must link a node to a note")
    starts, ends = ENDPOINTS[kind]
    if s.TYPE not in starts or e.TYPE not in ends:
        if kind in ("Call", "Return"):
            return reject("Call and return edges must connect activation boxes")
        return reject(f"A {kind} edge cannot connect a {s.TYPE} to a {e.TYPE}")
    return OK


def validate_edge(diagram: Diagram, kind: str, props: dict, start, end) -> Result:
    if kind not in EDGES_BY_DIAGRAM[diagram.type]:
        return reject(f"{kind} edges are not available in a {diagram.type.label}")
    result = _check_endpoints(kind, start, end)
    if not result:
        return result
    ctx = Ctx(diagram, kind, props, start, end)
    for rule in RULES[diagram.type]:
        result = rule(ctx)
        if not result:
            return result
    return OK
