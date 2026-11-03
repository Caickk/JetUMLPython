# JetUML em Python — Planejamento

Editor de diagramas UML (Class, Sequence, State, Object, Use Case) conforme o Anexo II de `DescricaoProjeto.pdf`.
Desenvolvido **sem consulta ao código padrão ouro**: todas as decisões abaixo vêm apenas dos requisitos.

## 1. Escolhas tecnológicas
- **Python 3.10+**, interface em **Tkinter** (biblioteca padrão; Canvas atende grade, zoom, arraste e laço). Sem dependências para o núcleo.
- **Pillow** como única dependência opcional (`requirements.txt`; exportar PNG/JPEG e copiar imagem, RF04/RF05). SVG é gerado sem dependências.
- Testes com `unittest` (stdlib). O núcleo é testável sem janela gráfica.

## 2. Arquitetura em camadas (dependências apontam para baixo)
```
ui/ app/      Tkinter: janela, abas, menus, canvas, painel de propriedades      (Fase 3-5)
rendering/     Renderer abstrato, pintor, layout, caminhos; backends SVG, Tk e Pillow  ✅
editor.py      DiagramEditor (Facade): valida → cria comando → notifica           ✅ Fase 1
commands.py    Command + Composite + UndoManager                                  ✅ Fase 1
validation.py  Regras por tipo de diagrama (+ sequence_flow.py)                   ✅ Fase 1
model/         Node, Edge, Diagram (Composite + Observer)                         ✅ Fase 1
persistence.py JSON aberto e documentado                                          ✅ Fase 1
notifications.py, tools.py, geometry.py                                           ✅ Fase 1
```
Regra de ouro (RNF03): **a UI não contém regra de negócio**; ela só chama o `DiagramEditor`, que consulta `validation`.

## 3. Padrões de projeto e onde atendem requisitos
| Padrão | Onde | Motivo / requisitos |
|---|---|---|
| Composite | `Node` (pacote/objeto/linha de vida com filhos); `CompositeCommand` | RF15, RF25, RF27; várias alterações = um Ctrl+Z |
| Command | `commands.py` + `UndoManager` | RF21 (desfazer/refazer até o estado inicial) |
| Observer | `Diagram.subscribe`, `NotificationService.subscribe` | UI redesenha sem o modelo conhecer a UI; RF41 |
| Facade | `DiagramEditor` | ponto único de entrada para a UI (RNF03) |
| Strategy | lista de regras por diagrama; `Renderer` com backends; ferramentas | RF18/RF19/RF30; RF04/RF05 reaproveitam o desenho |
| Máquina de estados | `InteractionController` (arrasto, laço, linha elástica), sem Tk e 100% testável | RF11, RF14–16, RF32, RF35 |
| Registro/Fábrica | `NODE_TYPES`, `create_node` | persistência e criação sem `if/elif` por tipo |
| Orientado a dados | `EDGE_KINDS`, `CHOICES`, `TOOLBARS` | evita 13 classes de aresta; trocar Composição↔Agregação é mudar uma propriedade (RF20) |

Decisão registrada: **Memento foi descartado** para o desfazer — comandos com operação inversa ocupam menos memória e preservam a ordem do histórico.

## Como executar
```
py -m jetuml_py                                   # abre o editor
py -m unittest discover -s tests -t .             # roda os testes (os de interface exigem display)
```

## 4. Ordem de desenvolvimento
1. **Fase 1 — Núcleo** (modelo, validação, comandos, persistência, notificações, ferramentas, editor) — ✅ concluída, 30 testes.
2. **Fase 2 — Renderização** — ✅ concluída, 45 testes: tamanho de nós a partir do texto, caminho das arestas (RF17), layout vertical da sequência (RF29), `Renderer` + backend SVG (testável sem tela).
3. **Fase 3 — Shell** — ✅ concluída, 69 testes: janela, abas, tela de boas-vindas, menus File/Edit/View, atalhos (RF01–03, 06, 21, 37–40, RNF03).
4. **Fase 4 — Interação** — ✅ concluída, 102 testes: barra lateral, criação de nós/arestas, arraste, laço, seleção, menu de contexto, dicas (RF07–16, 32–35).
5. **Fase 5 — Propriedades e texto** — ✅ concluída, 119 testes: painel, auto-edição, estereótipos, itálico/sublinhado (RF12, 20, 22–24).
6. **Fase 6 — Exportação, área de transferência, preferências** — ✅ concluída, 147 testes: RF04, RF05, RF36, RF38, RF39, RF41–42 na UI, copiar/colar (RF34).
7. **Fase 7 — Endurecimento** — ✅ concluída, 160 testes: testes de integração, desempenho (RNF01), empacotamento para Windows.

Critério de pronto de cada fase: testes verdes + `REQUISITOS.md` atualizado.

## 5. Formato do arquivo JSON (RNF02)
```json
{
  "version": 1,
  "diagram": "ClassDiagram | SequenceDiagram | StateDiagram | ObjectDiagram | UseCaseDiagram",
  "nodes": [ { "type": "Package", "id": "<hex>", "x": 0, "y": 0,
               "properties": { "name": "model" },
               "children": [ { "type": "Class", "...": "..." } ] } ],
  "edges": [ { "id": "<hex>", "type": "Aggregation", "start": "<node id>", "end": "<node id>",
               "properties": { "aggregation_type": "Composition", "directionality": "Unspecified" } } ]
}
```
- `type` de nó: Note, Class, Interface, Package, PackageDescription, Object, Field, Actor, UseCase, State, InitialState, FinalState, ImplicitParameter, Call, Point.
- `type` de aresta: Dependency, Generalization, Association, Aggregation, NoteConnector, Call, Return, Transition, Reference, Collaboration, UseCaseAssociation, UseCaseDependency, UseCaseGeneralization.
- Variantes são propriedades: `generalization_type` (Inheritance/Implementation), `aggregation_type` (Aggregation/Composition), `dependency_type` (None/Include/Extend).
- `Point` é a âncora invisível de um conector de nota (RF14). Arquivos inválidos geram `DiagramFormatError`; a gravação é atômica.

## 6. Interpretações adotadas onde o texto é ambíguo
- RF18 "mesmos dois nós": duplicidade = mesmo tipo de aresta entre o mesmo par de nós, **em qualquer sentido** (exceto Estados, que têm limites próprios do RF19).
- RF18 "Associação + Agregação": vale também para Composição (mesmo kind `Aggregation`).
- RF20: dependência recebe *Directionality*; *Generalization Type* fica na herança/realização.
- RF14: arrastar da nota termina sempre em ponto fixo (`Point`); arrastar do nó termina na nota.
- RF29/RF30: chamada de construtor termina na linha de vida; só uma caixa raiz órfã por diagrama.
- Textos de menu e notificações em inglês, como nos rótulos do Anexo II.

## 7. Estado final e verificação
- **Testes** (`py -m unittest discover -s tests -t .`): lógica (modelo, validação, comandos, layout, interação, exportação, colagem), interface Tk e estresse com gestos aleatórios nos 5 tipos de diagrama (invariantes do modelo, desfazer/refazer exatos, salvar/abrir sem perdas).
- **Rastreabilidade**: `docs/RASTREABILIDADE.md` (requisito → testes), gerado e conferido por `tools/traceability.py`.
- **Desempenho**: `tools/benchmark.py` (sem tela) e `tools/benchmark_tk.py` (com tela).
- **Fora do alcance do ambiente de desenvolvimento**: Windows real, colar imagem em outros programas, `.exe`. Roteiro em `docs/ROTEIRO_VERIFICACAO_WINDOWS.md`.
- Nenhuma decisão de projeto consultou o código padrão ouro; qualquer comparação com ele é trabalho de análise do grupo.
