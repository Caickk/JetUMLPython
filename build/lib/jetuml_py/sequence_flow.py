"""Consultas sobre o fluxo de controle do diagrama de sequência (somente leitura).

Uma caixa de ativação (Call) está 'ativa' quando ainda não retornou e todas as chamadas
que fez já retornaram. Só caixas ativas podem emitir novas chamadas ou retornar; qualquer
outra tentativa causaria um 'salto' no fluxo de controle (RF30).
"""
from .validation_result import OK, reject


def calls_from(d, box):
    return [e for e in d.edges if e.kind == "Call" and e.start is box]


def incoming_call(d, box):
    return next((e for e in d.edges if e.kind == "Call" and e.end is box), None)


def has_returned(d, box) -> bool:
    return any(e.kind == "Return" and e.start is box for e in d.edges)


def pending_calls(d, box):
    return [c for c in calls_from(d, box)
            if c.end.TYPE == "Call"
            and not any(r.kind == "Return" and r.start is c.end and r.end is box for r in d.edges)]


def is_active(d, box) -> bool:
    return not has_returned(d, box) and not pending_calls(d, box)


def caller_of(d, box):
    call = incoming_call(d, box)
    if call is not None:
        return call.start
    # primeira caixa de uma linha de vida criada por chamada de construtor
    for e in d.edges:
        if e.kind == "Call" and e.end is box.parent:
            return e.start
    return None


def orphan_roots(d):
    return [n for n in d.all_nodes() if n.TYPE == "Call" and caller_of(d, n) is None]


def check_call_source(d, box):
    if not is_active(d, box):
        return reject("Call would break the control flow", silent=True)
    return OK


def check_lifeline_origin(d, lifeline):
    """Início de chamada a partir de uma linha de vida (sem caixa de ativação)."""
    if lifeline.children:
        return reject("Start calls from an activation box")
    if any(e.kind == "Call" and e.end is lifeline for e in d.edges):
        return OK  # linha de vida criada por construtor: a caixa terá chamador
    if orphan_roots(d):
        return reject("Only one root call is allowed per diagram")
    return OK
