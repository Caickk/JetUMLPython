"""Invariantes que NENHUMA sequência de operações pode violar (usadas pelo teste de estresse)."""
from collections import Counter

from jetuml_py import sequence_flow as sf
from jetuml_py.validation import EDGES_BY_DIAGRAM, validate_placement


def check_consistency(d) -> list[str]:
    problems = []
    nodes = list(d.all_nodes())
    ids = [n.id for n in nodes]
    if len(ids) != len(set(ids)):
        problems.append("duplicate node ids")
    if len({e.id for e in d.edges}) != len(d.edges):
        problems.append("duplicate edge ids")
    for r in d.roots:
        if r.parent is not None:
            problems.append(f"root {r} has a parent")
    for n in nodes:
        for c in n.children:
            if c.parent is not n:
                problems.append(f"child {c} has wrong parent")
        res = validate_placement(d.type, n.TYPE, n.parent)
        if not res:
            problems.append(f"bad placement of {n}: {res.message}")
    alive = {id(n) for n in nodes}
    used_points = Counter()
    for e in d.edges:
        if id(e.start) not in alive or id(e.end) not in alive:
            problems.append(f"{e} has an endpoint outside the diagram")
        if e.kind not in EDGES_BY_DIAGRAM[d.type]:
            problems.append(f"{e.kind} not allowed in {d.type}")
        if e.end.TYPE == "Point":
            used_points[id(e.end)] += 1
    for n in nodes:
        if n.TYPE == "Point" and used_points[id(n)] != 1:
            problems.append("orphan or shared anchor point")
    kind = d.type.value
    pairs = Counter()
    for e in d.edges:
        if kind != "StateDiagram":
            pairs[(e.kind, frozenset((e.start.id, e.end.id)))] += 1
    problems += [f"duplicate {k[0]} edge" for k, n in pairs.items() if n > 1]
    if kind == "ClassDiagram":
        for e in d.edges:
            if e.start is e.end and e.kind in ("Dependency", "Generalization"):
                problems.append("forbidden self edge")
            if e.kind in ("Association", "Aggregation"):
                other = "Aggregation" if e.kind == "Association" else "Association"
                if any(x.kind == other and {x.start.id, x.end.id} == {e.start.id, e.end.id} for x in d.edges):
                    problems.append("association combined with aggregation")
            if e.kind in ("Dependency", "Association", "Aggregation") and e.start is not e.end:
                if any(x.kind == e.kind and x.start is e.end and x.end is e.start for x in d.edges):
                    problems.append(f"back-and-forth {e.kind}")
    if kind == "ObjectDiagram":
        for e in d.edges:
            if e.kind == "Collaboration" and (e.start is e.end or any(
                    x.kind == "Collaboration" and x.start is e.end and x.end is e.start for x in d.edges)):
                problems.append("collaboration self/cycle")
    if kind == "UseCaseDiagram":
        problems += ["use case self edge" for e in d.edges if e.kind != "NoteConnector" and e.start is e.end]
    if kind == "StateDiagram":
        cnt = Counter((e.start.id, e.end.id) for e in d.edges if e.kind == "Transition")
        problems += ["too many transitions" for k, n in cnt.items() if n > 2]
        for e in d.edges:
            if e.kind == "Transition" and (e.start.TYPE == "FinalState" or e.end.TYPE == "InitialState"):
                problems.append("transition from final / to initial")
    if kind == "SequenceDiagram":
        boxes = [n for n in nodes if n.TYPE == "Call"]
        if boxes and len(sf.orphan_roots(d)) > 1:
            problems.append("more than one orphan root call")
        incoming = Counter(e.end.id for e in d.edges if e.kind == "Call" and e.end.TYPE == "Call")
        problems += ["box with several callers" for n in incoming.values() if n > 1]
        for e in d.edges:
            if e.kind == "Return":
                call = sf.incoming_call(d, e.start)
                if call is None or call.start is not e.end:
                    problems.append("return without matching call")
    return problems
