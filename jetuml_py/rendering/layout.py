"""Layout: tamanho dos nós a partir do conteúdo, campos de objeto, pacotes e diagrama de sequência.

O layout altera apenas coordenadas/tamanhos derivados; ele NÃO entra na pilha de desfazer
(as posições escolhidas pelo usuário continuam sendo desfeitas pelos comandos).
É idempotente: aplicar duas vezes produz o mesmo resultado.
"""
from __future__ import annotations

from .. import sequence_flow as sf
from ..geometry import Rect
from .text import TextMetrics

HEADER_H = 40


def _lines(text: str) -> list[str]:
    return text.split("\n") if text else []


def section_height(m: TextMetrics, n_lines: int) -> int:
    return max(20, n_lines * m.line_height + 10)


def sections(node) -> list[list[str]]:
    """Seções textuais separadas por linha horizontal (classe, interface, descrição de pacote)."""
    p = node.props
    if node.TYPE == "Class":
        return [_lines(p["name"]) or [""], _lines(p["attributes"]), _lines(p["methods"])]
    if node.TYPE == "Interface":
        return [["«interface»"] + (_lines(p["name"]) or [""]), _lines(p["methods"])]
    if node.TYPE == "PackageDescription":
        return [_lines(p["name"]) or [""], _lines(p["contents"])]
    return []


def field_text(field) -> str:
    name, value = field.props["name"], field.props["value"]
    return f"{name} = {value}" if value else name


def _widest(m, lines) -> int:
    return max((m.width(x) for x in lines), default=0)


def fit_node(node, m: TextMetrics) -> None:
    t, p = node.TYPE, node.props
    min_w, min_h = node.SIZE
    if t in ("Class", "Interface", "PackageDescription"):
        secs = sections(node)
        node.width = max(min_w, _widest(m, [x for s in secs for x in s]) + 20)
        node.height = sum(section_height(m, len(s)) for s in secs)
    elif t == "Note":
        ls = _lines(p["text"])
        node.width = max(min_w, _widest(m, ls) + 20)
        node.height = max(min_h, len(ls) * m.line_height + 16)
    elif t in ("State", "ImplicitParameter", "Actor"):
        node.width = max(min_w, _widest(m, _lines(p["name"])) + 20)
    elif t == "UseCase":
        node.width = max(min_w, _widest(m, _lines(p["name"])) + 40)
    elif t == "Field":
        node.width = max(min_w, m.width(field_text(node)) + 10)


def _layout_object(obj, m: TextMetrics) -> None:
    header = 24
    for i, f in enumerate(obj.children):
        f.x, f.y = obj.x + 10, obj.y + header + i * f.height
    widest = max((f.width for f in obj.children), default=0)
    obj.width = max(obj.SIZE[0], widest + 20, m.width(obj.props["name"]) + 20)
    obj.height = max(60, header + sum(f.height for f in obj.children) + 10)


def package_extent(pkg, m: TextMetrics, exclude=None) -> Rect:
    """Retângulo do pacote a partir de seus filhos; 'exclude' ignora um filho (usado ao arrastar com Shift)."""
    w, h = pkg.SIZE
    for c in pkg.children:
        if c is exclude:
            continue
        r = package_extent(c, m, exclude) if c.TYPE == "Package" else c.bounds
        w = max(w, r.x + r.width - pkg.x + 15)
        h = max(h, r.y + r.height - pkg.y + 15)
    return Rect(pkg.x, pkg.y, max(w, m.width(pkg.props["name"]) + 40), h)


def _layout_package(pkg, m: TextMetrics) -> None:
    r = package_extent(pkg, m)
    pkg.width, pkg.height = r.width, r.height


def layout_sequence(d, m: TextMetrics) -> None:
    lifelines = [n for n in d.roots if n.TYPE == "ImplicitParameter"]
    constructed = {e.end.id for e in d.edges if e.kind == "Call" and e.end.TYPE == "ImplicitParameter"}
    plain = [l for l in lifelines if l.id not in constructed]
    base_y = min((l.y for l in plain), default=0)
    for l in plain:
        l.y = base_y

    def cx(lifeline) -> int:
        return lifeline.x + lifeline.width // 2

    def place(box, top: int, x: int) -> int:
        box.x, box.y = x, top
        cursor = top + 15
        for call in sf.calls_from(d, box):
            callee = call.end
            if callee.TYPE == "Call":
                same = callee.parent is box.parent
                bottom = place(callee, cursor, box.x + 8 if same else cx(callee.parent) - callee.width // 2)
                cursor = bottom + 15
            else:  # construtor: cabeçalho alinhado verticalmente à seta (RF29)
                callee.y = cursor - callee.height // 2
                roots = [c for c in callee.children if sf.incoming_call(d, c) is None]
                cursor += callee.height // 2 + 10
                for r in roots:
                    cursor = place(r, callee.y + callee.height, cx(callee) - r.width // 2) + 15
        box.height = max(40, cursor - top)
        return box.y + box.height

    for root in sf.orphan_roots(d):
        place(root, base_y + HEADER_H + 20, cx(root.parent) - root.width // 2)


def stem_end(lifeline) -> int:
    return lifeline.stem_end()


def apply_layout(d, m: TextMetrics | None = None) -> None:
    m = m or TextMetrics()
    nodes = list(d.all_nodes())
    for n in nodes:
        fit_node(n, m)
    for n in reversed(nodes):  # filhos antes dos pais
        if n.TYPE == "Object":
            _layout_object(n, m)
        elif n.TYPE == "Package":
            _layout_package(n, m)
    if d.type.value == "SequenceDiagram":
        layout_sequence(d, m)
