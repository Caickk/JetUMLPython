# JetUML Python — Acompanhamento de requisitos

Legenda: ✅ atendido e testado · 🟡 parcial (lógica pronta e testada, falta interface/renderização) · ⬜ pendente
Última atualização: **Fase 7 concluída** (160 testes: 118 de lógica + 42 de interface Tk sob Xvfb; 324 mil passos aleatórios de estresse sem violar regras).

## Requisitos funcionais
| ID | Requisito | Como será atendido | Fase | Status |
|---|---|---|---|---|
| RF01 | Criar novo diagrama (5 tipos, nova aba) | `create_diagram`; tela de boas-vindas e File > New | 1/3 | ✅ |
| RF02 | Abrir/salvar/fechar em JSON | `persistence.save/load`; menus e atalhos | 1/3 | ✅ |
| RF03 | Duplicar diagrama | `persistence.duplicate`; Ctrl+D abre nova aba | 1/3 | ✅ |
| RF04 | Exportar imagem (SVG/PNG/JPEG) | `Renderer` com backends SVG (`render_svg`) e Pillow (`render_image`); File > Export Image, formato pela extensão | 2/6 | ✅ |
| RF05 | Copiar para a área de transferência | Render sem grade, ajustado ao conteúdo; Windows via `ctypes` | 6 | 🟡 |
| RF06 | Encerrar aplicação (Ctrl+Q) | Menu File > Exit e Ctrl+Q; pergunta sobre alterações não salvas | 3 | ✅ |
| RF07 | Barra de ferramentas por tipo de diagrama | `tools.TOOLBARS` (ordem do Anexo II) | 1/4 | ✅ |
| RF08 | Atalhos 1–9, 0, A, B… | `tools.shortcut_map` | 1/4 | ✅ |
| RF09 | Menu de contexto com as ferramentas | Popup do Tk a partir de `TOOLBARS` | 4 | ✅ |
| RF10 | Tooltips, Show Tool Hint, Verbose Tooltips | Opções do menu View | 4 | ✅ |
| RF11 | Criar nós por clique | `DiagramEditor.add_node` | 1/4 | ✅ |
| RF12 | Auto Edit Node | Abrir painel após `add_node` quando ativo | 5 | ✅ |
| RF13 | Criar notas | Tipo `Note` em todos os diagramas | 1/4 | ✅ |
| RF14 | Conectar notas / ancorar em ponto | `connect` (nó→nota) e `anchor_note` (nota→ponto) | 1/4 | ✅ |
| RF15 | Nós filhos em pacotes (clique, Shift) | `add_node` detecta pacote; `attach`/`detach` | 1/4 | ✅ |
| RF16 | Criar arestas (rubber band) | `DiagramEditor.connect`; linha elástica na UI | 1/4 | ✅ |
| RF17 | Layout automático das arestas | `edge_paths.compute_edge_paths`, recalculado a cada pintura (teste de movimentação) | 2 | ✅ |
| RF18 | Validação das conexões e infrações estruturais | `validation.validate_edge` + notificação de erro | 1 | ✅ |
| RF19 | Autoarestas e limites de transições | Regras de self-edge e `rule_state_transitions` | 1 | ✅ |
| RF20 | Propriedades das arestas | `EDGE_KINDS`/`CHOICES` + `set_property`; painel na UI | 1/5 | ✅ |
| RF21 | Desfazer/refazer | `UndoManager` + comandos; Edit > Undo/Redo | 1/3 | ✅ |
| RF22 | Painel de propriedades dos elementos | `PROPS` por tipo; painel (duplo clique, Ctrl+Enter, Tab, Esc) | 1/5 | ✅ |
| RF23 | Estereótipos «» (Ctrl+Q) | Atalho no campo de texto do painel | 5 | ✅ |
| RF24 | Itálico `/x/` e sublinhado `_x_` | `parse_markup`; itálico/sublinhado no SVG e no canvas Tk (linha inteira) | 2/5 | ✅ |
| RF25 | Campo nunca solto (sempre em objeto) | `validate_placement`; também na carga do arquivo | 1 | ✅ |
| RF26 | Criar referências (Value → objeto) | Aresta `Reference` Field→Object | 1/4 | ✅ |
| RF27 | Criar chamadas e caixas de ativação | `DiagramEditor.add_call` (comando composto) | 1/4 | ✅ |
| RF28 | Autochamadas | `add_call(caixa, mesma linha de vida)` | 1/4 | ✅ |
| RF29 | Chamadas de construtor («create») | `add_call(..., constructor=True)`; alinhamento vertical no layout | 1/2 | ✅ |
| RF30 | Validar sequência (falha silenciosa e estrutural) | `sequence_flow` + `Result.silent` | 1 | ✅ |
| RF31 | Open Bottom | Propriedade `open_bottom` de `Call`; checkbox no painel | 1/5 | ✅ |
| RF32 | Seleção (clique, Ctrl, laço) | Hit-test `Diagram.node_at` + laço no canvas | 4 | ✅ |
| RF33 | Selecionar tudo (Ctrl+A) | Edit > Select All | 4 | ✅ |
| RF34 | Recortar/copiar/colar com compatibilidade | Serialização de seleção; bloqueio em sequência | 6 | ✅ |
| RF35 | Excluir elementos | `DiagramEditor.delete` (restaura tudo ao desfazer) | 1/4 | ✅ |
| RF36 | Grade com snap | Grade no pintor (`show_grid`); falta menu e snap | 2/6 | ✅ |
| RF37 | Zoom (2 níveis, Ctrl+=, Ctrl+-, Ctrl+0) | `ZoomModel` (±2 níveis, por documento); View e Ctrl+=, Ctrl+-, Ctrl+0 | 3 | ✅ |
| RF38 | Tamanho do diagrama (250–4000 px) | View > Set Diagram Size; padrão proporcional à tela | 6 | ✅ |
| RF39 | Alterar fonte | View > Change Font | 6 | ✅ |
| RF40 | Modo escuro | `Theme` LIGHT/DARK no pintor; falta alternar na UI | 2/3 | ✅ |
| RF41 | Notificações (erro vermelho, confirmação verde) | `NotificationService`; desenho no canto inferior esquerdo | 1/6 | ✅ |
| RF42 | Duração das notificações (0–10 s, padrão 5) | `NotificationService.duration`; diálogo no View | 1/6 | ✅ |

## Requisitos não funcionais
| ID | Requisito | Como será atendido | Fase | Status |
|---|---|---|---|---|
| RNF01 | Desempenho / tamanho inicial proporcional à tela | Padrão derivado da resolução; renderização incremental | 6/7 | ✅ |
| RNF02 | Formato JSON aberto e documentado | Esquema em `docs/PLANO.md` §5 | 1 | ✅ |
| RNF03 | Múltiplas formas de interação | Menu, barra, atalho e mouse chamam o mesmo `DiagramEditor`; menus e atalhos de arquivo/edição/zoom prontos | 3/4 | ✅ |

**Resumo:** 44 ✅ · 1 🟡 · 0 ⬜ (total 45).

## Intercorrências registradas
1. **Sem ambiente gráfico no ambiente de desenvolvimento**: a UI Tkinter só poderá ser exercitada na sua máquina Windows; o núcleo foi validado headless.
2. **Ambiguidades do Anexo II** resolvidas por interpretação documentada (`PLANO.md` §6).
3. **Pillow** será a única dependência externa (PNG/JPEG); SVG não depende dela.
4. ~~Exclusão em sequência~~ — **resolvida na Fase 4**: apagar uma caixa (ou uma aresta Call) remove em cascata tudo que ela chamou e construiu, evitando raízes órfãs.
5. **Layout não entra na pilha de desfazer** (Fase 2): `apply_layout` recalcula tamanhos, campos de objeto, pacotes e posições verticais da sequência a partir do conteúdo; só as ações do usuário são desfeitas.
6. **Métricas de texto estimadas** (largura fixa de 7 px/caractere): o backend Tk deverá injetar medidas reais, e os tamanhos mudam levemente.
7. **Detalhe visual pendente**: a seta de retorno de uma autochamada fica curta e encostada na caixa; ajuste fino na Fase 4.
8. O SVG foi conferido visualmente (diagramas de classe e de sequência); o sublinhado `_x_` está no atributo `text-decoration` e alguns visualizadores (cairosvg) não o desenham.
9. **Interface testada só no Linux (Xvfb)** na Fase 3: obtive o Tk extraindo pacotes `.deb` sem root. Os 14 testes de interface passam lá, mas ainda não foram executados no Windows; rode `py -m unittest discover -s tests -t .` e `py -m jetuml_py` aí.
10. ~~Modo escuro só na área de desenho~~ — **resolvida na Fase 6** (veja o item 29 para a única exceção: a barra de menus nativa do Windows).
11. ~~Notificações fora da tela~~ — **resolvida na Fase 6**. Erros de abrir, salvar e exportar arquivos continuam também em caixa de diálogo, para não passarem em branco quando a duração é 0 (que desativa as notificações, RF42).
12. ~~Ctrl+Q global × estereótipos~~ — **resolvida na Fase 5**: o campo do painel consome o evento (`break`) antes do atalho global de sair (teste confirma que a janela não fecha).
13. **Atualização da interface agrupada** (`after_idle`): menus e títulos se atualizam logo depois do comando terminar, pois no meio dele o comando ainda não está na pilha de desfazer (bug encontrado e corrigido nos testes).
14. **Detach com Shift era impossível** (bug achado nos testes da Fase 4): o pacote cresce com o filho arrastado, então o cursor nunca saía dele. Agora a decisão avalia o pacote sem a contribuição do nó arrastado (`package_extent(exclude=…)`).
15. **Interpretações de interação** (o Anexo II não detalha): clicar em elemento já selecionado o desseleciona (leitura literal do RF32); o laço seleciona elementos *totalmente contidos*; a ferramenta de criação **permanece ativa** após criar (Esc ou tecla 1 volta ao Select); criar nó só funciona em espaço vazio, dentro de pacote ou dentro de objeto (campo).
16. **Campos e caixas de ativação não são movidos pelo usuário**: suas posições vêm do layout (empilhamento/fluxo de chamadas). Arrastá-los não faz nada.
17. **Shift com várias seleções** anexa/desanexa nó a nó (um passo de desfazer por nó), não em um único passo.
18. ~~To Clipboard sem ação; auto edit pendente~~ — **resolvidas** (Fases 5 e 6).
19. **Eventos de mouse testados com eventos sintéticos do Tk (Xvfb)**: Ctrl+clique, Shift+arrastar e botão direito devem ser conferidos à mão no Windows. Atalhos de ferramenta (1–9, 0, A…) exigem foco na área de desenho (clique nela antes).
20. **O painel aplica por campo, ao confirmar** (sair do campo, Enter, escolher na lista, marcar/desmarcar), cada confirmação em um único passo de desfazer. Por isso **Esc fecha e mantém** o que já foi digitado (não descarta), como num painel de aplicação imediata. O painel também acompanha Ctrl+Z (atualiza os campos) e fecha sozinho se o elemento for removido.
21. **Marcação de texto (RF24) vale para a linha inteira**: `/Shape/` vira itálico e `_count_` sublinhado; algo como `_count_: int` **não** é formatado (o Anexo diz "entre barras/sublinhados" em uma linha).
22. **Auto Edit Node vem desligado por padrão** (o Anexo não define) e abre o painel só para nós que têm propriedades (estados inicial/final não abrem).
23. **Painel não modal**: abre perto do elemento; as capturas feitas no Linux (sem gerenciador de janelas) não mostram a barra de título, que existirá no Windows.
24. **Duplo clique** só abre o painel com a ferramenta Select ativa (evita abrir ao criar nós). O Tk não permite gerar duplo clique sintético; os testes usam dois cliques rápidos. Confirme à mão no Windows.
25. **Pillow é dependência opcional** (`requirements.txt`): sem ele, só SVG; exportar PNG/JPEG e copiar imagem mostram um erro claro pedindo `pip install pillow`.
26. **RF05 no Windows não pôde ser executado aqui.** O código usa a API do Windows via `ctypes` (formato CF_DIB). Foram testados: a conversão para DIB (cabeçalho de 40 bytes, dimensões), o caminho de linha de comando no Linux (com uma ferramenta falsa que recebe o PNG) e o tratamento de falhas. **Cole no Paint/Word para conferir** — por isso o RF05 está 🟡 e não ✅.
27. **Exportações e imagem copiada usam sempre o tema claro, sem grade, ajustadas ao conteúdo**, mesmo com o modo escuro ligado. A fonte é a configurada se existir no sistema; senão cai em Arial/Liberation/DejaVu (negrito e itálico reais dependem do que estiver instalado).
28. **RF38, interpretação**: a área do diagrama é `max(tamanho configurado, conteúdo)` também durante a edição (não só ao abrir), para que nenhum elemento fique inalcançável. O padrão é o tamanho da tela (RNF01), limitado a 250–4000. O tamanho configurado vale para todos os diagramas (novos e abertos) e fica nas preferências, não no arquivo do diagrama.
29. **RF40, limitação do sistema**: no Windows a barra de menus *nativa* (File/Edit/View) ignora cores e continua clara. Todo o resto (menus suspensos, abas, barra de ferramentas e ícones, painéis, diálogos e a área de desenho) troca de tema.
30. **RF34, regras de colagem**: deslocamento de +20 px por colagem; uma aresta só é copiada se estiver selecionada e as duas pontas também forem copiadas (a âncora de um conector de nota acompanha); campo solto, tipos incompatíveis e qualquer colagem em diagrama de sequência são recusados com notificação de erro. Recortar = copiar + excluir.
31. **Fonte (RF39)**: a tela mede o texto com a fonte real do Tk; as imagens exportadas usam uma estimativa proporcional ao tamanho, então a largura de caixas pode variar levemente entre a tela e o arquivo exportado.
32. **O teste de estresse achou dois defeitos reais** (Fase 7), ambos corrigidos e com teste de regressão: (a) uma *seleção obsoleta* — mover/anexar com Shift um nó que acabara de ser desfeito derrubava o programa; agora o gesto limpa a seleção ao começar e o editor ignora elementos que não estão mais no diagrama; (b) *apagar a aresta de construtor* deixava a caixa da linha de vida criada sem chamador, gerando uma segunda raiz órfã (viola o RF30); agora apagar uma chamada apaga também o que ela criou.
33. **Desempenho (RNF01)**: o gargalo era medir texto no Tk a cada redesenho (80% do tempo). Com memória de larguras, o redesenho completo caiu de 48 → 6 ms (50 nós), 145 → 13 ms (150), 375 → 32 ms (400) e 1022 → 76 ms (1000 nós / 1500 arestas). Medido no Linux/Xvfb (CPU de servidor); no seu computador rode `tools/benchmark_tk.py`.
34. **Zoom no teclado numérico**: além de Ctrl+= / Ctrl+- / Ctrl+0, Ctrl com `+`, `-` e `0` do teclado numérico também funcionam (útil no ABNT2).
35. **Empacotamento**: `pip install .` foi verificado (instala, abre a janela a partir do pacote instalado). `build_windows.bat` (PyInstaller) **não** foi testado. O que depende do Windows está em `docs/ROTEIRO_VERIFICACAO_WINDOWS.md`.
36. **Rastreabilidade**: `docs/RASTREABILIDADE.md` liga cada um dos 45 requisitos a testes que existem de fato (101 referências, conferidas por `tools/traceability.py` e por um teste).
