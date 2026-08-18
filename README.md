# STDD

STDD é um framework de controle de desenvolvimento orientado por testes. Ele instala skills para agentes de código, detecta a stack do repositório, configura os runners disponíveis e registra evidências em `.stdd/`.

## Instalação

Use [`uv`](https://docs.astral.sh/uv/) para instalar a versão publicada. O mesmo comando, executado novamente, força a atualização do CLI instalado:

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

Depois da escolha, o CLI pergunta se deve executar o setup da stack. O setup não instala dependências nem inicia serviços sem autorização; ele apenas detecta arquivos e comandos locais. Em seguida, no modo interativo, o init pergunta o significado operacional do nível 2 e do nível 3: nível 2 pode ser `Tela` ou uma definição personalizada; nível 3 pode ser `Regra de negócio`, `Detalhes da tela` ou uma definição personalizada. Essas decisões ficam em `.stdd/config.json`.

Para automação sem perguntas:

```bash
stdd init meu-projeto --integration codex
stdd init meu-projeto --integration claude --integration gemini
stdd init meu-projeto --all-integrations
```

O `stdd init` sempre sincroniza as skills já instaladas com os templates desta versão, adicionando agentes novos e atualizando instruções existentes. Se o comando ainda não reconhecer `draw-system-level-1` até `draw-system-level-4`, reinstale o CLI a partir deste checkout com `uv tool install --force --editable .` e execute o init novamente.

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
$create-tests Quero implementar autenticação por sessão; transforme o pedido em uma feature testável.
$draw-feature Desenhe o fluxo de autenticação, incluindo falhas e subfluxos.
$draw-improve Revise o desenho atual e acrescente somente o próximo detalhe arquitetural relevante.
$draw-interaction Investigue marcações do Draw; responda perguntas e execute tarefas na codebase.
$draw-system-level-1 Desenhe somente a arquitetura macro do sistema.
$draw-system-level-2 Desenhe jornadas, telas e navegação por papel a partir da arquitetura existente.
$draw-system-level-3 Detalhe o comportamento completo de uma tela ou nó, em lotes aprovados.
$draw-system-level-4 Rastreie sob demanda uma decisão até a codebase real.
$static-analysis Analise dependências, complexidade, funções longas e segredos hardcoded.
$missing Execute as tasks pendentes do backlog até não haver mais tasks; leia símbolos e testes e corrija o comportamento marcado como ausente.
$implement Execute a implementação aprovada e rode os gates do STDD.
```

Também é possível chamar a skill sem instrução adicional quando o objetivo já estiver claro:

```text
$setup
$create-tests
$draw-improve
$draw-interaction
$missing
$implement
```

O agente deve ler o `SKILL.md` correspondente antes de agir. A skill define o contrato, os diretórios permitidos, os testes e os gates; a mensagem enviada no terminal fornece o contexto da tarefa. O processo recomendado é:

```text
$setup
$create-tests Descreva aqui o que o produto precisa fazer.
$draw-system-level-1 Modele a arquitetura macro do sistema.
$draw-system-level-2 Modele as jornadas por papel — separando cliente, administrador e permissões.
$draw-system-level-3 Modele de ponta a ponta o comportamento das telas que exigem regras, validações ou autorização.
$draw-system-level-4 Abra somente o recorte de codebase que exija rastreabilidade técnica.
$draw-feature Mostre a arquitetura e as decisões dessa feature.
$draw-improve Evolua o desenho em um ciclo curto e pare para minha revisão.
$implement Execute somente depois da aprovação.
```

`$draw-improve` trabalha em duas fases sobre um JSON existente em `.stdd/draws/`. A primeira revisa o Draw e cria exatamente dez perguntas em uma sessão separada de `.stdd/improvements/`, sem alterar o fluxo. Responda as perguntas no viewer e salve a sessão; em uma nova chamada, o agente executa `stdd draw improve --pending`, consome somente sessões completas e aplica um único incremento coerente no Draw. Depois de salvar o fluxo, a sessão recebe status `applied` e permanece imutável como histórico. Quando o desenho estiver aprovado, `$create-tests` transforma sua lógica em testes. Mesmo que o próximo pedido seja apenas `$implement`, o agente deve passar primeiro pela etapa de create-tests e confirmar os testes vermelhos antes de alterar produção.

O `$draw-interaction` lê as marcações do Draw e identifica se cada uma é uma pergunta ou uma tarefa. Para perguntas com `@stdd` e `answer` ausente, executa `stdd draw questions`, consulta a codebase e os símbolos associados; se houver evidência, grava a resposta, marca os símbolos relevantes e remove o marcador. Para tarefas, consulta `stdd backlog missing`, lê os símbolos e testes e implementa o comportamento faltante na codebase, com regressão e gates quando necessário. Sem `@stdd`, a pergunta pertence ao usuário ou a um revisor humano; respostas já preenchidas, inclusive `false` e `0`, não geram nova ação. O `$draw-improve` preserva essa responsabilidade separada.

As skills `$draw-system-level-1` a `$draw-system-level-4` criam uma árvore sem fluxos órfãos: nível 1 contém somente arquitetura macro, nível 2 acompanha jornadas e navegação por papel, nível 3 detalha de ponta a ponta as ações possíveis de cada tela em dois ou mais lotes aprovados e nível 4 liga a codebase sob demanda. No nível 2, cada nó deve ter ao menos um `code_refs`; `stdd draw create` informa a lacuna e `stdd test` bloqueia com `draw.level2_missing_code_ref`. O mesmo gate bloqueia `draw.level3_missing_code_ref`, `draw.level4_missing_code_ref` e `draw.empty_node_symbol`; duplicação de símbolo continua sendo warning. No nível 3, cada ação comprovada da tela inicia um nó próprio conectado ao comportamento de caso de uso; a tela não é substituída por um fluxo genérico. A análise estática avisa quando um subfluxo de nível 3 tem menos de quatro nós ou quando alguma descrição tem menos de 80 caracteres; esses avisos continuam informativos. Cada filho declara seu pai e cada pai aponta para o filho com `draw_ref`; caminhos ainda não implementados terminam no próprio nó, sem continuação fictícia.

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

O suporte nativo inicial cobre Python, JavaScript/TypeScript (incluindo JSX/TSX) e PHP. Em projetos híbridos ou monorepos, `stdd setup` instala um dispatcher em `.stdd/adapters/static_adapter.py`, com módulos específicos por linguagem; `package.json` é descoberto recursivamente fora de `node_modules`, `vendor` e artefatos de build. Python usa `ast`, PHP usa `token_get_all` e JavaScript/TypeScript usa a Compiler API do pacote `typescript` local. O relatório mantém capacidades e limitações por parser; Go, Rust, Java e C# continuam detectados, mas `unavailable` até receberem adapters próprios.

Exceções devem ser específicas e temporárias. Cada item precisa informar uma `rule`, exatamente um alvo (`file`, `symbol_id` ou `lines`), `action` (`warning` ou `ignore`), `reason` e data `expires`. `warning` preserva o achado sem bloquear; `ignore` o retira dos indicadores ativos, mas mantém a evidência da exceção. Exceções expiradas bloqueiam a análise. Falhas do adapter, do contrato e segredos hardcoded não podem ser liberados por essa lista.

O `stdd log` registra diffs incrementais e ignora snapshots AppleDouble `._*` e arquivos históricos que não sejam UTF-8, evitando que metadados binários gerados pelo macOS interrompam o registro de uma execução.

Para revisar somente as alterações atuais dos JSONs lógicos dos Draws desde o último log, use:

```bash
stdd draw diff
stdd draw diff --run-id <run-id>
```

Sem `--run-id`, o comando compara o estado atual com o último checkpoint salvo em `.stdd/runs/`; com `--run-id`, ele reexibe o diff histórico daquela interação. Em ambos os casos, considera apenas JSONs diretos de `.stdd/draws/`, exclui `index.json` e não consulta GitHub, `git diff` nem arquivos da codebase.

Para entregar as perguntas pendentes do Draw Interaction em uma leitura humana, agrupadas por desenho e nó, use:

```bash
stdd draw answer
```

A saída mostra a pergunta sem `@stdd`, o nó, o símbolo associado ao nó, o arquivo, as evidências e as limitações. O comando é somente leitura; `stdd draw questions` continua disponível para o JSON operacional consumido pela skill.

Para criar, consultar e concluir uma sessão de perguntas do Draw Improve, use:

```bash
stdd draw improve --create --data-json '<JSON_DA_SESSAO>'
stdd draw improve --pending
stdd draw improve --mark-applied --id <improvement-id>
```

As sessões ficam em `.stdd/improvements/` e possuem índice próprio. O viewer mostra essas sessões separadamente dos desenhos; salvar respostas nunca sobrescreve `.stdd/draws/<draw-id>.json`.

Logs sem linhas adicionadas ou removidas no código são mantidos como checkpoints, com `checkpoint: true` no `*_summary.json`. O detalhamento dos JSONs alterados fica no `*_snapshot.json`; a aba `Runs` do Draw permite ocultar esses checkpoints de 0 linhas.

Cada execução de `stdd test` também atualiza `.stdd/adapters/static-analysis-kpis.json` com os indicadores agregados e os detalhes dos símbolos, dependências, métricas, arquivos e achados de qualidade. O Draw Server expõe esse JSON e o viewer o apresenta na aba lateral `Análise`, ao lado de `Desenhos`; os Draws continuam separados em `.stdd/draws/` e os facts de rastreabilidade em `.stdd/facts/`.

## Executar o backlog

O backlog é derivado dos Draws e fica consolidado em `.stdd/backlog.json`. Cada task operacional corresponde a um nó de nível 2 ou a uma etapa de subfluxo associado e inclui perguntas, respostas, símbolos associados, arquivos e dependências. A task pai mantém `draw_ref`, `child_backlog_id` e a relação com as tasks internas.

Gere ou atualize o documento agregado:

```bash
stdd backlog generate
```

Consulte todas as tasks ainda não concluídas:

```bash
stdd backlog missing
```

O ciclo interativo entrega uma task por vez, percorre cada ramificação até seu terminal e depois avança para a próxima. Uma etapa compartilhada por mais de um caminho continua sendo uma única task operacional, mas aparece em todas as branches e só deixa os caminhos dependentes concluídos quando seu status foi concluído. Quando o nó possui `draw_ref`, ele permanece no backlog pai e abre um backlog interno com as tasks do subfluxo antes da continuação da branch:

```bash
stdd backlog task
stdd backlog complete <task-id>
```

O padrão é uma task por interação. Para fluxos maiores, configure de 1 a 5 itens e o escopo do lote (`task` ou `node`) em `.stdd/config.json` ou com `stdd backlog config --task-batch-size 2 --task-batch-scope node`. Cada item continua exigindo seu próprio `backlog complete`. O cursor usa lease e respeita a janela mínima configurada (`min_task_interval_seconds`, nunca menor que 3 quando habilitada), bloqueando chamadas fora de ordem ou tentativas de avançar várias tasks em um único script.

O bootstrap é a primeira task por padrão e é agnóstico de framework: prepara o ponto de entrada, arquivos raiz, configuração, dependências, convenções e comandos necessários para receber as próximas tasks. O agente interpreta as evidências locais da stack e não deve inventar arquivos ou implementar funcionalidade de produto nessa etapa. A task também audita Draw System nível 1, `.stdd/design.md`, ambiente, `.env.example` e a estrutura mínima de armazenamento; `--no-bootstrap` continua disponível para projetos que optarem explicitamente por não executar essa preparação. Após cada nó L2 e seus subfluxos, o backlog pode injetar duas tasks separadas: auditoria funcional real (API, persistência, validações, estados e efeitos) e associação de símbolos, arquivos de implementação e testes. A task final valida inicialização, renderização, uso básico e lacunas funcionais.

`stdd backlog task` e `stdd backlog test` mostram somente o contexto acionável em linguagem humana: task, fluxo, nó, uma decisão respondida, os símbolos associados e a diretriz do nível. Não há saída JSON nesses comandos. Tasks de nível 2 recebem a definição escolhida para orientar a implementação da tela/frontend; tasks de nível 3 recebem a definição escolhida para orientar regras de negócio e/ou detalhes da tela.

O contexto também informa o predecessor imediato, descrição anterior, conexão, condição (`então`, `ou`, `se`), origem e caminho de acesso. O primeiro nó não recebe uma origem artificial. Os estados distinguem testes ausentes, testes prontos, implementação em andamento e backlog concluído.

Antes da implementação, crie incrementalmente o teste da jornada:

```bash
stdd backlog test
stdd backlog complete <task-id>
```

Um nó de nível 2 pode declarar `test_ref` — ou `test_refs` compatíveis — com um único arquivo e as funções que cobrem o nó e todos os seus subfluxos. Quando essa referência existir, a análise estática será exibida como evidência complementar; ela não é obrigatória para marcar o checklist. `backlog test` entrega primeiro a preparação agnóstica (`backlog-bootstrap-task`) e, depois de concluída, a task reservada para criar os testes sem alterar produção; fluxos de sistemas já existentes também podem ser marcados manualmente no viewer.

O backlog mantém dois checklists centrais em `phase_checklists`: `test` vem antes de `implementation`, e os itens são derivados das tasks e subfluxos. No Draw, ao selecionar um nó, a Sidebar permite marcar ou desmarcar esses itens. A marcação é persistida no `.stdd/backlog.json` pelo servidor local, sem validação obrigatória de análise estática; a implementação continua bloqueada enquanto o checklist de teste do nó e de seus subfluxos estiver pendente.

Se `backlog task` for chamado antes da marcação do checklist de teste, ele mostra o bloqueio em linguagem humana e não reserva a implementação. O `$missing` e o `$implement` devem atender essa resposta com a etapa de testes ou com a marcação manual do fluxo já existente. Ao desmarcar a implementação, o `$missing` deve ler símbolos, dependências e testes, localizar o comportamento faltante e corrigi-lo antes de concluir a task. Self-loops são terminais; ciclos diferentes de self-loop são bloqueados para evitar execução infinita. A aba `Backlog` do viewer mostra a task atual, perguntas, respostas, símbolos e a evidência opcional do teste quando o Draw Server está ativo.

Quando uma task possui subfluxo, a saída humana mostra o contexto do pai e a task atual. Pai e subtasks são independentes e devem ser concluídos pelos seus próprios IDs; a resposta mantém o contexto do pai enquanto avança pela primeira, segunda e demais subtasks.

## Executar testes

Para conferir somente os símbolos associados aos nós dos Draws, sem executar os testes do sistema:

```bash
stdd draw symbols
```

O comando lista os símbolos por nó e termina com código diferente de zero quando encontra uma associação ausente em um Draw de nível 2, 3 ou 4.

```bash
stdd test
```

Esse é o alias global. Ele executa as suítes configuradas, análise estática, contrato e runners da stack. Suítes que exigem aprovação explícita aparecem como `not_executed` quando não autorizadas.
Se `.stdd/backlog.json` existir, o alias também executa o gate do backlog e bloqueia enquanto houver task sem `backlog complete` ou nó de nível 2 sem teste comprovado; a saída do terminal mostra somente status e contagens, mantendo os detalhes no relatório estruturado.
Quando a análise encontrar um nó de nível 2, 3 ou 4 sem símbolo, a saída inclui o `kind`, o arquivo do Draw e o `node_id` do achado bloqueante (`draw.level*_missing_code_ref` ou `draw.empty_node_symbol`).

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

O comando `stdd draw create` rejeita qualquer desenho que contenha um nó sem edge incidente; a relação é considerada não direcionada, então basta o nó participar de `from` ou `to`. Um desenho vazio continua válido para iniciar a edição visual. O mesmo comando também executa uma análise estrutural em memória: títulos, fluxos, subfluxos, sequências de nós e conexões repetidos ou muito próximos aparecem como warnings no terminal. Essa análise nunca bloqueia a criação e não prova que o desenho foi gerado por script; ela apenas indica uma possível estrutura automatizada que deve ser revisada.

Os fontes editáveis do viewer ficam em [`draw-editor/`](draw-editor/README.md). Eles são usados apenas para desenvolvimento e recompilação do pacote; não são instalados nos projetos dos usuários.

Ao clicar em `＋ Novo desenho`, o Draw pede o nome do desenho antes de criá-lo. O viewer carrega apenas o desenho selecionado, lê seu JSON em `.stdd/draws/` e salva alterações lógicas pelo endpoint local `/__stdd/api/draws/<id>.json`. Cores e posições são preferências da experiência visual; elas ficam no armazenamento local do navegador e não alteram o contrato JSON.

O Live Server continua opcional para desenvolvimento do próprio editor React, mas não é necessário para usar o viewer instalado.

Na aba `Backlog`, o viewer usa o Draw Server local para separar as fases do ciclo: `POST /__stdd/api/backlog/test` reserva a task de testes, `POST /__stdd/api/backlog/tasks/<task-id>/complete` conclui a fase atual e `POST /__stdd/api/backlog/refresh` regenera as evidências exibidas. A implementação só fica disponível depois que o teste da task e de seus subfluxos estiver concluído.

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

As tags são case-insensitive: `@stdd` representa ação do agente, `@developer` representa resposta humana e `@obs` registra contexto que o agente deve consumir. O comando canônico para pendências é:

```bash
stdd draw questions
stdd draw questions --tag developer
stdd draw questions --tag obs --answered
stdd draw consume-observation --draw-id <draw-id> --question-id <id> [--node-id <node-id>]
```

Respostas removem automaticamente somente `@stdd` e `@developer`; `@obs` permanece até o consumo explícito, que devolve pergunta e resposta e remove apenas a tag. Perguntas gerais, sem `node_id`, pertencem ao painel de melhorias; perguntas de nó permanecem associadas ao nó.

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
