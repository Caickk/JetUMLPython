# Roteiro de verificação no Windows

Tudo foi testado automaticamente no Linux (display virtual). Os itens abaixo dependem do Windows ou de uma pessoa olhando a tela;
faça-os antes de entregar e anote o resultado.

## 1. Preparação (5 min)
1. `py --version` (precisa de 3.10 ou superior) e `py -m tkinter` (deve abrir uma janelinha de teste).
2. Na pasta do projeto: `pip install -r requirements.txt` (Pillow, opcional) e `py -m unittest discover -s tests -t .`
   - Esperado: **160 testes, `OK`**, sem `skipped` (a interface roda porque há tela). Se algum teste de interface falhar só no Windows, é achado importante: anote o nome do teste.
3. `py tools/traceability.py` → "ok: 45 requisitos…". `py tools/benchmark.py` e `py tools/benchmark_tk.py` mostram os tempos na sua máquina.

## 2. Itens que só o Windows confirma
| # | O que fazer | Esperado | OK? |
|---|---|---|---|
| 1 | Criar um diagrama de classes com 2–3 classes; **Ctrl+B**; colar no Paint e no Word | A imagem aparece, sem grade, ajustada ao desenho (RF05, caminho `ctypes`/CF_DIB) | |
| 2 | File > Export Image: salvar `.png`, `.jpg` e `.svg`; abrir cada um | Os três abrem e se parecem com o diagrama (tema claro, sem grade) | |
| 3 | Duplo clique em uma classe | Abre o painel de propriedades (RF22) | |
| 4 | No painel: Tab, **Shift+Tab**, Ctrl+Q num campo, Esc | Navega entre campos, insere « », Esc fecha; o programa **não** fecha com Ctrl+Q | |
| 5 | **Ctrl+clique** em dois elementos; arrastar com o laço; arrastar um filho de pacote soltando com **Shift** | Seleção múltipla; laço seleciona o que está dentro; anexa/desanexa do pacote | |
| 6 | **Botão direito** no diagrama | Menu com as ferramentas da barra (RF09) | |
| 7 | Zoom: Ctrl+= , Ctrl+- , Ctrl+0 e as teclas `+`/`-` do teclado numérico com Ctrl | Dois níveis para cada lado (RF37). No teclado ABNT2 `=` fica na tecla ao lado do `-` | |
| 8 | View > Dark Mode | Tudo escuro, **exceto a barra File/Edit/View**, que o Windows não deixa recolorir (limitação conhecida, RF40) | |
| 9 | Tela com escala de 125% ou 150% | Textos e caixas continuam legíveis; se algo ficar cortado, anote | |
| 10 | View > Change Font: escolher uma fonte diferente e tamanho 16 | Diagrama se reorganiza; Restore Default volta ao normal | |
| 11 | Provocar um erro (ex.: ligar duas classes duas vezes com Association) | Notificação vermelha no canto inferior esquerdo, some em ~5 s | |
| 12 | Salvar, fechar o programa, abrir de novo, File > Recent Files | O arquivo aparece e abre igual | |

## 3. Executável (opcional)
`build_windows.bat` → `dist\JetUML.exe`. **Não foi testado** (foi escrito no Linux). Se falhar, o programa continua rodando com `py -m jetuml_py`.

## 4. O que NÃO foi verificado de forma alguma neste ambiente
- Aparência real no Windows (fontes, DPI, barra de título dos painéis).
- Colar a imagem em outros programas (item 1).
- O `.exe` do PyInstaller.
