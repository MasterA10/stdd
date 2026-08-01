# STDD

STDD é um framework de controle de desenvolvimento orientado por testes. Ele instala skills para agentes de código, detecta a stack do repositório, configura os runners disponíveis e registra evidências em `.stdd/`.

## Instalação

O pacote atual é a versão `0.1.0`. Como ainda não há uma tag publicada, instale o CLI da branch de desenvolvimento disponível usando [`uv`](https://docs.astral.sh/uv/):

```bash
uv tool install stdd --from git+https://github.com/MasterA10/stdd.git@v0.1.0
```

Em desenvolvimento local, dentro deste repositório:

```bash
uv tool install --editable .
```

Confirme a instalação:

```bash
stdd --help
```

## Inicializar um repositório

Entre no diretório onde o projeto deve ser criado e execute:

```bash
stdd init meu-projeto
cd meu-projeto
```

Em um terminal interativo, o STDD oferece uma seleção múltipla numerada:

```text
Selecione as integrações do agente (ex.: 1,3 ou 4 para todos):
  1. Codex
  2. Claude
  3. Gemini
  4. Todos
```

Depois da escolha, o CLI pergunta se deve executar o setup da stack. O setup não instala dependências nem inicia serviços sem autorização; ele apenas detecta arquivos e comandos locais.

Para automação sem perguntas:

```bash
stdd init meu-projeto --integration codex
stdd init meu-projeto --integration claude --integration gemini
stdd init meu-projeto --all-integrations
```

As skills são instaladas em:

- Codex: `.agents/skills/`
- Claude: `.claude/skills/`
- Gemini: `.gemini/skills/`

Além das skills, o init instala no topo do projeto as instruções operacionais do STDD no arquivo lido pelo agente selecionado:

- Codex: `AGENTS.md`
- Claude: `CLAUDE.md` (ou um `CLAUDE.md` existente em `.claude/`)
- Gemini: `GEMINI.md`

O bloco é marcado, idempotente e preserva o conteúdo existente. Ele orienta o agente a registrar o trabalho com `stdd log`, executar `stdd test` e guardar evidências em `.stdd/`. O STDD só manipula arquivos de instrução dentro do projeto; não altera prompts ou configurações globais do usuário. O framework permanece em uma única pasta `.stdd/`, e o setup escreve o `.gitignore` na raiz do projeto.

## Usar as skills no Codex

Depois de inicializar o projeto, abra o Codex dentro do repositório. As skills ficam em `.agents/skills/<skill>/SKILL.md` e podem ser chamadas diretamente pelo nome, no formato de skills do Codex:

```text
$setup Detecte a stack deste repositório e configure os runners sem instalar dependências.
$feature Quero implementar autenticação por sessão; transforme o pedido em uma feature testável.
$draw-feature Desenhe o fluxo de autenticação, incluindo falhas e subfluxos.
$draw-improve Revise o desenho atual e acrescente somente o próximo detalhe arquitetural relevante.
$static-analysis Analise dependências, complexidade, funções longas e segredos hardcoded.
$implement Execute a implementação aprovada e rode os gates do STDD.
```

Também é possível chamar a skill sem instrução adicional quando o objetivo já estiver claro:

```text
$setup
$feature
$draw-improve
$implement
```

O agente deve ler o `SKILL.md` correspondente antes de agir. A skill define o contrato, os diretórios permitidos, os testes e os gates; a mensagem enviada no terminal fornece o contexto da tarefa. O processo recomendado é:

```text
$setup
$feature Descreva aqui o que o produto precisa fazer.
$draw-feature Mostre a arquitetura e os trade-offs dessa feature.
$draw-improve Evolua o desenho em um ciclo curto e pare para minha revisão.
$implement Execute somente depois da aprovação.
```

`$draw-improve` trabalha sobre um JSON existente em `.stdd/draws/`. Cada chamada faz no máximo um incremento pequeno e encerra para revisão; se a arquitetura já estiver suficiente, a resposta correta pode ser `Já está bom`. Quando o desenho estiver aprovado, `$feature` transforma sua lógica em testes. Mesmo que o próximo pedido seja apenas `$implement`, o agente deve passar primeiro pela etapa de feature e confirmar os testes vermelhos antes de alterar produção.

Para Claude e Gemini, as mesmas skills são instaladas em `.claude/skills/` e `.gemini/skills/`; a forma exata de chamada pode ser o comando de skill adotado pelo agente, mas os nomes e contratos permanecem iguais.

## Configurar a stack

Se o setup não foi executado durante o init:

```bash
stdd setup
```

O comando identifica manifests e runners sem presumir Python. Exemplos de runners que podem ser gerados:

- Python: `python -m pytest`
- JavaScript/TypeScript: `npm test`, `pnpm test` ou `yarn test`
- Go: `go test ./...`
- Rust: `cargo test`
- Java: `mvn test` ou `./mvnw test`
- .NET: `dotnet test`

A configuração fica em `.stdd/config.json`. O setup também adiciona padrões de ambiente, dependências, builds e caches ao `.gitignore`, preservando regras existentes.

## Executar testes

```bash
stdd test
```

Esse é o alias global. Ele executa as suítes configuradas, análise estática, contrato e runners da stack. Suítes que exigem aprovação explícita aparecem como `not_executed` quando não autorizadas.

Opções úteis:

```bash
stdd test --suite unit
stdd test --exclude performance
stdd test --profile mvp
stdd test --approve-actions
```

## Abrir e editar o Draw

O Draw Server é o processo responsável por ler e salvar os desenhos. O viewer React Flow compilado vem dentro do pacote Python do STDD; o projeto do usuário não recebe HTML, JavaScript, CSS ou dependências Node. O servidor lê e grava somente os JSONs em `.stdd/draws/`.

No diretório raiz do projeto, execute:

```bash
stdd draw serve --port 8765
```

Depois abra no navegador pela URL do servidor:

```text
http://127.0.0.1:8765/.stdd/draw.html
```

O caminho `/.stdd/draw.html` é uma rota virtual de compatibilidade: nenhum arquivo HTML é criado dentro do projeto. Mantenha `stdd draw serve --port 8765` em execução enquanto o viewer estiver aberto. O Live Server não é necessário.

Os fontes editáveis do viewer ficam em [`draw-editor/`](draw-editor/README.md). Eles são usados apenas para desenvolvimento e recompilação do pacote; não são instalados nos projetos dos usuários.

Ao clicar em `＋ Novo desenho`, o Draw pede o nome do desenho antes de criá-lo. O viewer carrega apenas o desenho selecionado, lê seu JSON em `.stdd/draws/` e salva alterações lógicas pelo endpoint local `/__stdd/api/draws/<id>.json`. Cores e posições são preferências da experiência visual; elas ficam no armazenamento local do navegador e não alteram o contrato JSON.

O Live Server continua opcional para desenvolvimento do próprio editor React, mas não é necessário para usar o viewer instalado.

Atalhos e gestos principais:

- Duplo clique em um bloco: editar nome e descrição diretamente.
- Duplo clique em uma seta: editar seu rótulo diretamente; botão direito: avançar a condição `então` → `ou` → `se`.
- Arrastar a saída roxa de um bloco: criar uma conexão.
- Clicar uma vez na saída roxa: conectar automaticamente ao próximo bloco lógico à frente.
- Arrastar a saída roxa: escolher manualmente qualquer bloco de destino.
- Selecionar uma seta: mostra um botão `×` sobre a própria seta para desconectá-la.
- Duplo clique no fundo: criar um novo bloco naquele ponto.
- `Ctrl/Cmd+D`: duplicar o bloco ou a seta selecionada.
- `Delete`: excluir a seleção.
- `Ctrl/Cmd+S`: salvar.
- `N`, `C`: adicionar bloco e conectar blocos.
- `+`, `-`, `0`: zoom in, zoom out e enquadrar.

O botão `? Atalhos` dentro do Draw mostra a referência completa. O texto é mantido automaticamente em preto ou branco para preservar contraste.

### Blocos autossuficientes

Não existe modo separado de edição: ao selecionar e mover um bloco, ou alterar qualquer controle dentro dele no próprio canvas, a alteração já está acontecendo. Não existe painel inferior direito: o desenho é a própria superfície de visualização e edição.

- campo superior: nome;
- campo de texto: descrição;
- seletor: tipo do bloco;
- dois seletores de cor: fundo e texto.

O cabeçalho do desenho pode ser editado com duplo clique. Setas selecionadas exibem seu próprio controle `×`; duplo clique edita seu rótulo e o botão direito alterna entre `então`, `ou` e `se`. Exclusões pedem confirmação. Movimentos e cores também habilitam o salvamento, mas só são persistidos quando `Salvar alterações` é pressionado; essas preferências ficam fora do JSON lógico. Assim, cada elemento permanece autocontido, inclusive em fluxos complexos.

### Perguntas de esclarecimento no Draw

Um bloco pode declarar opcionalmente `questions` no JSON lógico. Cada pergunta usa `type: "choice"`, `"boolean"` ou `"open"`, e pode manter `answer: null` até uma decisão ser tomada. O badge numérico no bloco mostra quantas perguntas ainda estão sem resposta; quando todas forem respondidas, ele permanece visível com `0` para preservar o histórico. Clique no badge para responder diretamente no bloco. Perguntas respondidas continuam no JSON e no painel, inclusive respostas booleanas `false`.

## Segurança e análise estática

O scanner interno procura credenciais hardcoded, tokens conhecidos e valores copiados de `.env` para o código. O valor nunca é gravado no relatório; ele aparece como `[REDACTED]`. Um vazamento detectado bloqueia o gate de testes.

Arquivos `.env`, `.pyc`, caches, ambientes virtuais e artefatos de build são ignorados pelo Git automaticamente. Variáveis de ambiente sem referência no código geram aviso, não bloqueio automático, porque podem ser utilizadas por infraestrutura ou serviços externos.

## Registrar trabalho

```bash
stdd log "Implementa autenticação" --impl
stdd log "Adiciona testes de autenticação" --test
stdd log "Corrige regressão" --bug
stdd log "Reestrutura código sem planejamento prévio" --refactor
```

Mantenha registros de implementação e testes separados quando forem trabalhos diferentes.

## Artefatos principais

```text
.stdd/
├── config.json
├── draws/
├── runs.html
└── runs/
```

As skills dos agentes ficam fora de `.stdd`, em seus diretórios próprios, e os demais artefatos do framework permanecem dentro de `.stdd`.
