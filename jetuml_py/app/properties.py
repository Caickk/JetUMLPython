"""Campos editáveis de cada elemento (RF20, RF22, RF31) e aplicação das mudanças. Independente de Tk."""
from __future__ import annotations

from dataclasses import dataclass

from ..model.edges import CHOICES, EDGE_KINDS, Edge

STEREOTYPE = "«»"                       # RF23: Ctrl+Q insere os dois delimitadores
MULTILINE = {"attributes", "methods", "contents", "text"}
LABELS = {
    "start_label": "Start Label", "middle_label": "Middle Label", "end_label": "End Label",
    "directionality": "Directionality", "aggregation_type": "Aggregation Type",
    "generalization_type": "Generalization Type", "dependency_type": "Dependency Type",
    "open_bottom": "Open Bottom",
}


@dataclass(frozen=True)
class FieldSpec:
    name: str
    label: str
    kind: str                            # "line" | "text" | "choice" | "bool"
    choices: tuple = ()


def _label(name: str) -> str:
    return LABELS.get(name) or name.replace("_", " ").title()


def fields_for(element) -> list[FieldSpec]:
    """Campos do painel de propriedades; vazio quando o elemento não tem propriedades editáveis."""
    if isinstance(element, Edge):
        specs = []
        for name in EDGE_KINDS[element.kind]:
            choices = CHOICES.get((element.kind, name))
            specs.append(FieldSpec(name, _label(name), "choice", choices) if choices
                         else FieldSpec(name, _label(name), "line"))
        return specs
    specs = []
    for name, default in element.PROPS.items():
        if isinstance(default, bool):
            specs.append(FieldSpec(name, _label(name), "bool"))
        else:
            specs.append(FieldSpec(name, _label(name), "text" if name in MULTILINE else "line"))
    return specs


def insert_stereotype(text: str, cursor: int) -> tuple[str, int]:
    """Insere « » na posição do cursor e devolve o novo texto e o cursor entre os delimitadores."""
    return text[:cursor] + STEREOTYPE + text[cursor:], cursor + 1


class PropertiesModel:
    def __init__(self, editor, element):
        self.editor, self.element = editor, element
        self.fields = fields_for(element)

    def values(self) -> dict:
        return {f.name: self.element.props[f.name] for f in self.fields}

    def commit(self, values: dict) -> bool:
        """Aplica só o que mudou, em um único passo de desfazer. False se nada mudou ou algo foi rejeitado."""
        current = self.element.props
        changes = {f.name: values[f.name] for f in self.fields
                   if f.name in values and values[f.name] != current[f.name]}
        return self.editor.set_properties(self.element, changes)
