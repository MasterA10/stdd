# STDD

STDD é um framework de controle de desenvolvimento orientado por testes. Ele instala skills para agentes de código, detecta a stack do repositório, configura os runners disponíveis e registra evidências em `.stdd/`.

## Instalação

Use [`uv`](https://docs.astral.sh/uv/) para instalar a versão publicada. O mesmo comando, executado novamente, força a atualização do CLI instalado:

```bash
uv tool install --force --refresh stdd --from git+https://github.com/MasterA10/stdd.git@v0.1.2
```

Para acompanhar as próximas modificações já disponíveis na branch principal, use:

```bash
uv tool install --force --refresh stdd --from git+https://github.com/MasterA10/stdd.git@main
```

Em desenvolvimento local, dentro deste repositório, a instalação editável acompanha automaticamente as próximas alterações do checkout; não é necessário reinstalar a cada edição:

```bash
uv tool install --force --editable .
```

Confirme a instalação:

```bash
stdd --help
```

Antes de qualquer commit ou push na branch main, confirme que as fontes, templates, skills, assets empacotados, README e testes necessários para essa instalação estão no diff publicado. Depois de alterar o framework, valide localmente com uv tool install --force --editable . e stdd init; assim, o comando remoto do README poderá reproduzir a mesma versão a partir da main.

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

O `stdd init` sempre sincroniza as skills já instaladas com os templates desta versão, adicionando agentes novos e atualizando instruções existentes. Se o comando ainda não reconhecer `draw-system`, reinstale o CLI a partir deste checkout com `uv tool install --force --editable .` e execute o init novamente.

Para substituir as skills de um projeto já existente pela versão mais recente publicada na `main`:

```bash
uv tool install --force --refresh stdd --from git+https://github.com/MasterA10/stdd.git@main
cd meu-projeto
stdd init . --all-integrations
```

Se o projeto usa somente Codex, substitua a última linha por `stdd init . --integration codex`. O init é idempotente: atualiza as skills e instruções existentes sem duplicá-las e não altera o código de produção.

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
$draw-system Desenhe o sistema completo em arquitetura, jornadas do usuário por papel (incluindo cliente e administrador) e níveis de implementação.
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
$draw-system Modele a arquitetura, as jornadas do usuário por papel — separando cliente, administrador e permissões — e os subfluxos de implementação.
$draw-feature Mostre a arquitetura e os trade-offs dessa feature.
$draw-improve Evolua o desenho em um ciclo curto e pare para minha revisão.
$implement Execute somente depois da aprovação.
```

`$draw-improve` trabalha sobre um JSON existente em `.stdd/draws/`. Cada chamada faz no máximo um incremento pequeno e encerra para revisão; se a arquitetura já estiver suficiente, a resposta correta pode ser `Já está bom`. Quando o desenho estiver aprovado, `$feature` transforma sua lógica em testes. Mesmo que o próximo pedido seja apenas `$implement`, o agente deve passar primeiro pela etapa de feature e confirmar os testes vermelhos antes de alterar produção.

Perguntas de um Draw só devem ser respondidas automaticamente pelo agente quando o `prompt` contiver `@STDD` e `answer` estiver ausente, `null` ou vazio. Nesse caso, o agente responde e grava o resultado no próprio `answer`. Sem `@STDD`, a pergunta pertence ao usuário ou a um revisor humano; se o marcador for removido, ela deixa de ser responsabilidade do agente. Respostas já preenchidas, inclusive `false` e `0`, não geram nova ação.

`$draw-system` cria uma árvore sem fluxos órfãos: nível 1 contém somente arquitetura macro, nível 2 acompanha as jornadas e a navegação do cliente, nível 3 detalha a implementação e nível 4 liga a codebase quando necessário. Cada filho declara seu pai e cada pai aponta para o filho com `draw_ref`; caminhos ainda não implementados terminam no próprio nó, sem continuação fictícia.

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

### Adapter de análise estática

Quando a codebase tiver uma linguagem e uma ferramenta local comprovadas, o agente `setup` constrói um adapter específico para aquela linguagem dentro do próprio projeto, preferencialmente em `.stdd/adapters/`. O adapter é versionado junto com a aplicação e o caminho em `static_analysis.adapter_command` é relativo à raiz do projeto. O núcleo do STDD permanece agnóstico: símbolos, dependências, complexidade e métricas são coletados por parser, tokenizer, AST, compiler API ou ferramenta local da própria stack, sem depender de serviço externo ou de um adapter instalado globalmente. Se a ferramenta necessária não existir, a capacidade fica explicitamente `unavailable`.

O `stdd log` registra diffs incrementais e ignora snapshots AppleDouble `._*` e arquivos históricos que não sejam UTF-8, evitando que metadados binários gerados pelo macOS interrompam o registro de uma execução.

Para revisar somente as alterações atuais dos JSONs lógicos dos Draws desde o último log, use:

```bash
stdd draw diff
stdd draw diff --run-id <run-id>
```

Sem `--run-id`, o comando compara o estado atual com o último checkpoint salvo em `.stdd/runs/`; com `--run-id`, ele reexibe o diff histórico daquela interação. Em ambos os casos, considera apenas JSONs diretos de `.stdd/draws/`, exclui `index.json` e não consulta GitHub, `git diff` nem arquivos da codebase.

Logs sem linhas adicionadas ou removidas no código são mantidos como checkpoints, com `checkpoint: true` no `*_summary.json`. O detalhamento dos JSONs alterados fica no `*_snapshot.json`; a aba `Runs` do Draw permite ocultar esses checkpoints de 0 linhas.

Cada execução de `stdd test` também atualiza `.stdd/adapters/static-analysis-kpis.json` com os indicadores agregados e os detalhes dos símbolos, dependências, métricas, arquivos e achados de qualidade. O Draw Server expõe esse JSON e o viewer o apresenta na aba lateral `Análise`, ao lado de `Desenhos`; os Draws continuam separados em `.stdd/draws/` e os facts de rastreabilidade em `.stdd/facts/`.

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

O Draw Server é o processo responsável por ler e salvar os desenhos. O viewer React Flow compilado vem dentro do pacote Python do STDD; o projeto do usuário não recebe HTML, JavaScript, CSS ou dependências Node. O servidor mantém os Draws em `.stdd/draws/` e os relatórios derivados da análise em `.stdd/facts/`.

No diretório raiz do projeto, execute:

```bash
stdd draw serve --port 8765
```

Depois abra no navegador pela URL do servidor:

```text
http://127.0.0.1:8765/.stdd/draw.html
```

O caminho `/.stdd/draw.html` é uma rota virtual de compatibilidade: nenhum arquivo HTML é criado dentro do projeto. Mantenha `stdd draw serve --port 8765` em execução enquanto o viewer estiver aberto. O Live Server não é necessário.

O `stdd init` instala um JSON de exemplo em `.stdd/draws/demo-inicial.json`, para que o viewer sempre tenha um fluxo inicial visível. A instalação é idempotente e não duplica esse exemplo.

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

Fixtures de teste que usam credenciais sintéticas, CEDs, INVs ou tokens fictícios podem ser marcadas explicitamente na própria linha (ou na linha anterior):

```python
PASSWORD = "ced-ficticia"  # stdd:allow-credential
```

Em arquivos de teste, o achado continua visível como `warning` e não bloqueia. Fora de arquivos de teste, o marcador é ignorado e o achado continua bloqueante. Para exigir bloqueio mesmo em fixtures marcadas, configure `"allow_marked_test_credentials": false` dentro de `static_analysis` em `.stdd/config.json`.

Arquivos `.env`, `.pyc`, caches, ambientes virtuais e artefatos de build são ignorados pelo Git automaticamente. Variáveis de ambiente sem referência no código geram aviso, não bloqueio automático, porque podem ser utilizadas por infraestrutura ou serviços externos.

### Rastreabilidade entre nós e símbolos

O vínculo entre um nó do Draw e um símbolo da codebase é feito pelo agente, de forma explícita e determinística. A responsabilidade é dividida assim:

- o adapter de análise estática descobre fatos reais: símbolos, dependências, arquivos, testes e métricas;
- o agente analisa o desenho e os fatos do adapter para identificar a correspondência correta;
- o agente executa `stdd draw associate-reference` para gravar a associação no nó;
- o STDD recalcula os fatos derivados e informa se o vínculo está `resolved`, `unresolved` ou em `drift`;
- o usuário intervém quando houver ambiguidade, símbolo ausente ou alteração que exija decisão arquitetural.

O adapter não deve alterar desenhos automaticamente. Ele fornece os fatos; o agente decide qual símbolo representa o nó e persiste a referência declarada. O vínculo mínimo exige o desenho, o `node_id`, o nome qualificado do símbolo e pelo menos uma dependência de origem:

```bash
stdd draw associate-reference \
  --draw-id nome-do-desenho \
  --node-id 42 \
  --qualified-name 'orders.OrderService.create' \
  --source-dependency 'orders.OrderRepository.save' \
  --source-dependency 'tests.orders.test_create_order'
```

O comando valida o desenho e o nó e grava a referência no JSON lógico. Em uma nova análise estática, o STDD cruza essa referência com `symbols` e `dependencies` e gera o relatório derivado em `.stdd/facts/<draw-id>.facts.json`, incluindo arquivos, testes relacionados e possíveis dependências para revisão. Para subfluxos, repetir a associação nos nós do subfluxo e manter a referência ao nó chamador.

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
