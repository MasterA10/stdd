# Looper

Looper é um framework de controle de desenvolvimento orientado por testes. Ele instala skills para agentes de código, detecta a stack do repositório, configura os runners disponíveis e registra evidências em `.looper/`.

## Instalação

Use [`uv`](https://docs.astral.sh/uv/) para instalar a versão publicada. O mesmo comando, executado novamente, força a atualização do CLI instalado:

```bash
uv tool install --force --refresh looper --from git+https://github.com/MasterA10/looper.git@main
```

Em desenvolvimento local, dentro deste repositório, a instalação editável acompanha automaticamente as próximas alterações do checkout; não é necessário reinstalar a cada edição:

```bash
uv tool install --force --editable .
```

Confirme a instalação:

```bash
looper --help
```

Antes de qualquer commit ou push na branch main, confirme que as fontes, templates, skills, assets empacotados, README e testes necessários para essa instalação estão no diff publicado. Depois de alterar o framework, valide localmente com uv tool install --force --editable . e looper init; assim, o comando remoto do README poderá reproduzir a mesma versão a partir da main.

## Inicializar um repositório

Entre no diretório onde o projeto deve ser criado e execute:

```bash
looper init meu-projeto
cd meu-projeto
```

O `looper init` usa Codex como integração padrão e não pergunta qual agente deve ser usado. Codex e os demais agentes compatíveis consumirão as instruções compartilhadas em `AGENTS.md`. Integrações adicionais podem ser instaladas explicitamente por flags, quando necessário.

Depois da escolha, o CLI pergunta se deve executar o setup da stack. O setup não instala dependências nem inicia serviços sem autorização; ele apenas detecta arquivos e comandos locais. Os níveis têm semântica fixa: L1 é Arquitetura, L2 é Tela/experiência do usuário, L3 é Use case e L4 é informação de baixo nível. O backlog aceita presets de loop (`task_order`, `node_complete`, `node_then_children` e `all_level2_then_level3`) e pode manter filas L2/L3 independentes para agentes paralelos. `--l2-children-mode none|context|owned` controla se o L2 recebe os filhos L3, se os recebe apenas como contexto ou se assume também sua conclusão; em `owned`, o loop L3 é desabilitado nessa fase. `--l3-parent-context/--no-l3-parent-context` controla a inclusão do pai L2 no contexto do L3. Os loops de testes e implementação têm modo e tamanho de lote próprios; essas escolhas ficam em `.looper/config.yaml` e podem ser atualizadas com `looper backlog config`. Quando o loop de testes é desabilitado, `looper backlog test` informa que foi desativado e `looper backlog task` libera somente implementação. O init injeta no bloco gerenciado do `AGENTS.md` a estratégia correspondente, atualizando-a sem duplicar nem apagar as regras próprias do projeto.

Para automação sem perguntas:

```bash
looper init meu-projeto --integration codex
looper init meu-projeto --integration claude --integration gemini
looper init meu-projeto --all-integrations
```

O `looper init` sempre sincroniza as skills já instaladas com os templates desta versão, adicionando agentes novos e atualizando instruções existentes. Se o comando ainda não reconhecer `draw-system-level-1` até `draw-system-level-4`, reinstale o CLI a partir deste checkout com `uv tool install --force --editable .` e execute o init novamente.

O init instala a skill `$playwright-testing` em `.agents/skills/playwright-testing/`. Ela documenta como criar testes E2E com Playwright, explorar e diagnosticar a aplicação com `npx playwright-cli`, confirmar a estrutura antes de automatizar e executar a regressão com `looper test --playwright`.

O init também instala a skill-guia `$system-design` em `.agents/skills/system-design/`. Ela mantém o design system do projeto, incluindo tokens de cor, tipografia, espaçamento, estados e acessibilidade, no `.looper/design.html`.

O init cria `.agents/conventions/` com um índice inicial. Uma convenção é uma orientação técnica específica, confirmada e reutilizável sobre como implementar ou manter código e infraestrutura, normalmente aprendida ao resolver um bug difícil ou uma implementação incomum. Documentações técnicas específicas e reutilizáveis, como contratos de APIs/apps externos e pré-condições de integrações, também ficam nessa pasta. Linguagem geral do sistema e regras de negócio não são convenções. Use a pasta por assunto, mantendo o `AGENTS.md` curto; o bloco gerenciado do `AGENTS.md` injeta automaticamente somente o catálogo de nomes, sem copiar caminhos ou conteúdo. O índice aponta para os arquivos, que o agente deve ler somente quando o assunto for relevante. Arquivos existentes são preservados pelo init. Quando uma convenção ou documentação alterar comportamento documentado, os Draws também devem ser atualizados.

### Configuração por YAML

Use `.looper/config.yaml` para editar as configurações do Looper. O arquivo único reúne opções operacionais, revisão e o campo `instructions` com as orientações persistentes dos loops. Projetos existentes são migrados automaticamente de `.looper/config.json`, `.looper/review-agents.json` e `.looper/loop-instructions.md` na próxima inicialização.

Para substituir as skills de um projeto já existente pela versão mais recente publicada na `main`:

```bash
uv tool install --force --refresh looper --from git+https://github.com/MasterA10/looper.git@main
cd meu-projeto
looper init . --all-integrations
```

Se o projeto usa somente Codex, substitua a última linha por `looper init . --integration codex`. O init é idempotente: atualiza as skills e instruções existentes sem duplicá-las e não altera o código de produção.

O comando `looper test` exibe um único relatório YAML no terminal, com os checks de contrato, Draws, análise estática, backlog e suítes separados. Quando um Draw falha, `checks.draws.issues` mostra o desenho, título, arquivo, nó, rótulo do nó, regra, severidade e mensagem do erro. O relatório completo continua sendo persistido em `.looper/runs/`.

As skills são instaladas em:

- Codex: `.agents/skills/`
- Claude: `.claude/skills/`
- Gemini: `.gemini/skills/`

Além das skills, o init instala no topo do projeto as instruções operacionais do Looper no arquivo lido pelo agente selecionado:

- Codex: `AGENTS.md`
- Claude: `CLAUDE.md` (ou um `CLAUDE.md` existente em `.claude/`)
- Gemini: `GEMINI.md`

O bloco é marcado, idempotente e preserva o conteúdo existente. Ele orienta o agente a registrar o trabalho com `looper log`, executar `looper test`, guardar evidências em `.looper/` e manter os Draws como documentação oficial: toda mudança de comportamento feita diretamente deve atualizar o Draw e suas conexões; detalhes sem mudança de comportamento devem virar perguntas no nível L2/L3 correto. O Looper só manipula arquivos de instrução dentro do projeto; não altera prompts ou configurações globais do usuário. O framework permanece em uma única pasta `.looper/`, e o setup escreve o `.gitignore` na raiz do projeto.

Ao executar `looper init` em um projeto que ainda usa a estrutura legada, o
comando migra `.looper/` para `.looper/` e atualiza referências textuais a `looper`
em arquivos do projeto. A migração é idempotente, preserva arquivos existentes
e não altera dependências vendorizadas, caches ou arquivos de segredo `.env`.

## Usar as skills no Codex

Depois de inicializar o projeto, abra o Codex dentro do repositório. As skills ficam em `.agents/skills/<skill>/SKILL.md` e podem ser chamadas diretamente pelo nome, no formato de skills do Codex. A skill `$test-application` atende interações comuns e lê o Draw completo para propor e implementar uma suíte transversal, usando `playwright-cli`/Playwright e testes reais de persistência quando aplicáveis. `$implement-frontend` e `$implement-backend` continuam exclusivos dos loops de implementação do backlog.

```text
$setup Detecte a stack deste repositório e configure os runners sem instalar dependências.
$test-application Leia o fluxo completo, proponha um plano de testes, peça aprovação e implemente a suíte aprovada.
$draw-feature Desenhe o fluxo de autenticação, incluindo falhas e subfluxos.
$draw-improve Revise o desenho atual e acrescente somente o próximo detalhe arquitetural relevante.
$draw-interaction Investigue marcações do Draw; responda perguntas e execute tarefas na codebase.
$draw-system-level-1 Desenhe somente a arquitetura macro do sistema.
$draw-system-level-2 Desenhe jornadas, telas e navegação por papel a partir da arquitetura existente.
$draw-system-level-3 Detalhe o comportamento completo de uma tela ou nó, em lotes aprovados.
$draw-system-level-4 Rastreie sob demanda uma decisão até a codebase real.
$static-analysis Analise dependências, complexidade, funções longas e segredos hardcoded.
$system-design Consulte e mantenha o design system, tokens visuais, estados e componentes reutilizáveis no `.looper/design.html`.
$playwright-testing Crie e diagnostique testes Playwright, explorando a aplicação com `npx playwright-cli` antes da automação quando possível.
$modern-web-guidance Consulte padrões modernos da web para interface, layouts, animações e CSS.
$backend-developer Implemente backend modular com logging transversal e integrações externas testadas.
$implement-change Execute em loop as changes pendentes entregues por `looper backlog change`, leia o contexto real, implemente, teste e conclua cada ID.
$implement-frontend Construa a tela/view (Nível 2) entregue por looper backlog frontend.
$implement-backend Implemente controllers, models, regras e integrações (Nível 3) entregues por looper backlog backend.
```

Também é possível chamar a skill sem instrução adicional quando o objetivo já estiver claro:

```text
$setup
$test-application
$draw-improve
$draw-interaction
$implement-change
$implement-frontend
$implement-backend
```

O agente deve ler o `SKILL.md` correspondente antes de agir. A skill define o contrato, os diretórios permitidos, os testes e os gates; a mensagem enviada no terminal fornece o contexto da tarefa. O processo recomendado é:

```text
$setup
$test-application Proponha e implemente a cobertura completa do fluxo, incluindo navegação, Playwright e persistência quando aplicável.
$draw-system-level-1 Modele a arquitetura macro do sistema.
$draw-system-level-2 Modele as jornadas por papel — separando cliente, administrador e permissões.
$draw-system-level-3 Modele de ponta a ponta o comportamento das telas que exigem regras, validações ou autorização.
$draw-system-level-4 Abra somente o recorte de codebase que exija rastreabilidade técnica.
$draw-feature Mostre a arquitetura e as decisões dessa feature.
$draw-improve Evolua o desenho em um ciclo curto e pare para minha revisão.
$implement-frontend Construa a view/tela da task entregue por looper backlog frontend.
$implement-backend Implemente o controller/model da task entregue por looper backlog backend.
```

`$draw-improve` trabalha em duas fases sobre um JSON existente em `.looper/draws/`. A primeira revisa o Draw e cria exatamente dez perguntas em uma sessão separada de `.looper/improvements/`, sem alterar o fluxo. Responda as perguntas no viewer e salve a sessão; em uma nova chamada, o agente executa `looper draw improve --pending`, consome somente sessões completas e, antes de alterar o fluxo, procura lacunas arquiteturais abertas pelas respostas. Se surgir uma nova decisão, regra, exceção ou caminho incompleto, cria outra sessão com somente a quantidade necessária de perguntas e aguarda; não aplica uma alteração parcial nem marca a sessão anterior como `applied`. Somente quando não houver nova lacuna aplica um único incremento coerente no Draw. Depois de salvar o fluxo, a sessão recebe status `applied` e permanece imutável como histórico. Quando o desenho estiver aprovado, `$test-application` transforma sua lógica em um plano e em testes aprovados. A produção continua nos loops específicos de implementação.

O `$draw-interaction` lê as marcações do Draw e identifica se cada uma é uma pergunta ou uma tarefa. Para perguntas com `@looper` e `answer` ausente, executa `looper draw questions`, consulta a codebase e os símbolos associados; se houver evidência, grava a resposta, marca os símbolos relevantes e remove o marcador. Para pedidos de alteração, consulta `looper backlog change`; o `$implement-change` lê os símbolos e testes, implementa a change e conclui o ID reservado depois da validação. Sem `@looper`, a pergunta pertence ao usuário ou a um revisor humano; respostas já preenchidas, inclusive `false` e `0`, não geram nova ação. O `$draw-improve` preserva essa responsabilidade separada.

As skills `$draw-system-level-1` a `$draw-system-level-4` criam uma árvore sem fluxos órfãos: nível 1 contém somente arquitetura macro, nível 2 acompanha jornadas e navegação por papel, nível 3 detalha de ponta a ponta as ações possíveis de cada tela em dois ou mais lotes aprovados e nível 4 liga a codebase sob demanda. Durante a especificação e enquanto a implementação estiver pendente, os nós podem permanecer sem `code_refs`; não invente símbolos ou use placeholders. Depois que a task estiver concluída no backlog, `looper test` exige os símbolos reais e bloqueia com `draw.level2_missing_code_ref`, `draw.level3_missing_code_ref`, `draw.level4_missing_code_ref` ou `draw.empty_node_symbol`. No nível 3, cada ação comprovada da tela inicia um nó próprio conectado ao comportamento de caso de uso; a tela não é substituída por um fluxo genérico. A análise estática avisa quando um subfluxo de nível 3 tem menos de quatro nós ou quando alguma descrição tem menos de 80 caracteres; esses avisos continuam informativos. Cada filho declara seu pai e cada pai aponta para o filho com `draw_ref`; caminhos ainda não implementados terminam no próprio nó, sem continuação fictícia.

Para Claude e Gemini, as mesmas skills são instaladas em `.claude/skills/` e `.gemini/skills/`; a forma exata de chamada pode ser o comando de skill adotado pelo agente, mas os nomes e contratos permanecem iguais.

## Configurar a stack

Se o setup não foi executado durante o init:

```bash
looper setup
```

O comando identifica manifests e runners sem presumir Python. Exemplos de runners que podem ser gerados:

- Python: `python -m pytest`
- JavaScript/TypeScript: `npm test`, `pnpm test` ou `yarn test`
- Go: `go test ./...`
- Rust: `cargo test`
- Java: `mvn test` ou `./mvnw test`
- .NET: `dotnet test`

A configuração fica em `.looper/config.yaml`. O setup também adiciona padrões de ambiente, dependências, builds e caches ao `.gitignore`, preservando regras existentes.

### Adapter de análise estática

Quando a codebase tiver uma linguagem e uma ferramenta local comprovadas, o agente `setup` constrói um adapter específico para aquela linguagem dentro do próprio projeto, preferencialmente em `.looper/adapters/`. O adapter é versionado junto com a aplicação e o caminho em `static_analysis.adapter_command` é relativo à raiz do projeto. O núcleo do Looper permanece agnóstico: símbolos, dependências, complexidade e métricas são coletados por parser, tokenizer, AST, compiler API ou ferramenta local da própria stack, sem depender de serviço externo ou de um adapter instalado globalmente. Se a ferramenta necessária não existir, a capacidade fica explicitamente `unavailable`.

O suporte nativo inicial cobre Python, JavaScript/TypeScript (incluindo JSX/TSX) e PHP. Em projetos híbridos ou monorepos, `looper setup` instala um dispatcher em `.looper/adapters/static_adapter.py`, com módulos específicos por linguagem; `package.json` é descoberto recursivamente fora de `node_modules`, `vendor` e artefatos de build. Python usa `ast`, PHP usa `token_get_all` e JavaScript/TypeScript usa a Compiler API do pacote `typescript` local. O relatório mantém capacidades e limitações por parser; Go, Rust, Java e C# continuam detectados, mas `unavailable` até receberem adapters próprios.

Exceções devem ser específicas e temporárias. Cada item precisa informar uma `rule`, exatamente um alvo (`file`, `symbol_id` ou `lines`), `action` (`warning` ou `ignore`), `reason` e data `expires`. `warning` preserva o achado sem bloquear; `ignore` o retira dos indicadores ativos, mas mantém a evidência da exceção. Exceções expiradas bloqueiam a análise. Falhas do adapter, do contrato e segredos hardcoded não podem ser liberados por essa lista.

O `looper log` registra diffs incrementais e ignora snapshots AppleDouble `._*` e arquivos históricos que não sejam UTF-8, evitando que metadados binários gerados pelo macOS interrompam o registro de uma execução.

As runs relêem o `.gitignore` em tempo real em toda criação de snapshot. As
regras atuais são aplicadas tanto aos arquivos presentes quanto à snapshot
anterior, evitando falsos deletes quando um arquivo passa a ser ignorado. Se a
regra for removida em uma execução posterior, o arquivo volta a ser considerado
automaticamente.

Para revisar somente as alterações atuais dos JSONs lógicos dos Draws desde o último log, use:

```bash
looper draw diff
looper draw diff --run-id <run-id>
```

Sem `--run-id`, o comando compara o estado atual com o último checkpoint salvo em `.looper/runs/`; com `--run-id`, ele reexibe o diff histórico daquela interação. Em ambos os casos, considera apenas JSONs diretos de `.looper/draws/`, exclui `index.json` e não consulta GitHub, `git diff` nem arquivos da codebase.

Para entregar todo o contexto dos Draws em uma leitura textual ordenada por nível, com conexões, decisões e símbolos:

```bash
looper draw context
looper draw context --draw <draw-id> --level <1-4>
looper draw context --node <node-id>
looper draw context --save
```

Sem filtros, o comando percorre a árvore completa. A saída é exibida no terminal; `--save` grava a mesma representação em `.looper/draw-context.md`. O comando reconstrói a ordem pelas arestas e relações hierárquicas, e aponta ambiguidades quando os JSONs não determinam uma sequência única. As conexões usam o formato `condição[contexto] -> Nó — destino (ação)`.

Para entregar as perguntas pendentes do Draw Interaction em uma leitura humana, agrupadas por desenho e nó, use:

```bash
looper draw answer
```

A saída mostra a pergunta sem `@looper`, o nó, o símbolo associado ao nó, o arquivo, as evidências e as limitações. O comando é somente leitura; `looper draw questions` continua disponível para o JSON operacional consumido pela skill.

Para criar, consultar e concluir uma sessão de perguntas do Draw Improve, use:

```bash
looper draw improve --create --data-json '<JSON_DA_SESSAO>'
looper draw improve --pending
looper draw improve --mark-applied --id <improvement-id>
```

As sessões ficam em `.looper/improvements/` e possuem índice próprio. O viewer mostra essas sessões separadamente dos desenhos; salvar respostas nunca sobrescreve `.looper/draws/<draw-id>.json`.

Logs sem linhas adicionadas ou removidas no código são mantidos como checkpoints, com `checkpoint: true` no `*_summary.json`. O detalhamento dos JSONs alterados fica no `*_snapshot.json`; a aba `Runs` do Draw permite ocultar esses checkpoints de 0 linhas.

Cada execução de `looper test` também atualiza `.looper/adapters/static-analysis-kpis.json` com os indicadores agregados e os detalhes dos símbolos, dependências, métricas, arquivos e achados de qualidade. O Draw Server expõe esse JSON e o viewer o apresenta na aba lateral `Análise`, ao lado de `Desenhos`; os Draws continuam separados em `.looper/draws/` e os facts de rastreabilidade em `.looper/facts/`.

## Executar o backlog

O backlog é derivado dos Draws e fica consolidado em `.looper/backlog.json`. Cada task operacional corresponde a um nó de nível 2 ou a uma etapa de subfluxo associado e inclui perguntas, respostas, símbolos associados, arquivos e dependências. A task pai mantém `draw_ref`, `child_backlog_id` e a relação com as tasks internas.

O campo `.looper/config.yaml:instructions` é a informação crítica persistente dos loops. Todo conteúdo não vazio é repetido em linguagem natural em cada entrega de teste, implementação, L2, L3, alteração, bootstrap, verificação, bloqueio ou resposta de fila vazia. O arquivo é relido a cada comando; não coloque senhas, tokens ou credenciais nele.

### Revisão automática por subagente

Após o intervalo configurado de tasks concluídas, a revisão opcional chama Agy por padrão (`agy -p ... --dangerously-skip-permissions`), ou Codex CLI (`codex exec`) quando selecionado na seção `review` de `.looper/config.yaml`. Configure `enabled`, `interval_tasks`, `execution_mode: tmux`, o agente, os gatilhos por fase (`test`, `implementation`, `change`) e escopo (`l2`, `l3`, `l2_and_l3`, `all`), além do modelo, reasoning, prompt e comando. Revisões e correções executadas por subagentes usam somente Tmux; em uma interação comum, pergunte antes de iniciar um subagente, salvo quando o usuário já tiver solicitado isso claramente. A revisão é executada com `looper backlog complete` ou manualmente:

```bash
looper backlog review task:meu-draw:node:1 --agent codex --scope l2_and_l3
```

O agente deve criar changes diretamente no nó correspondente quando encontrar lacunas, usando `looper draw change add --draw-id ... --node-id ... --prompt ...`. A antiga task injetada de verificação deixa de ser usada quando a revisão automática está ativa. Se nenhuma change for criada, a task é considerada aprovada. Cada revisão fica registrada em `.looper/reviews/`; uma falha não reabre a task e pode ser repetida.

Para desligar ou religar o acionamento automático sem editar JSON, use `looper backlog config --no-review` ou `looper backlog config --review`. Com a opção desligada, o `backlog complete` não chama nenhum agente de revisão.

Gere ou atualize o documento agregado:

```bash
looper backlog generate
```

Consulte todas as tasks ainda não concluídas:

```bash
looper backlog missing
```

O ciclo interativo entrega uma task por vez, percorre cada ramificação até seu terminal e depois avança para a próxima. Uma etapa compartilhada por mais de um caminho continua sendo uma única task operacional, mas aparece em todas as branches e só deixa os caminhos dependentes concluídos quando seu status foi concluído. Quando o nó possui `draw_ref`, ele permanece no backlog pai e abre um backlog interno com as tasks do subfluxo antes da continuação da branch:

```bash
looper backlog task
looper backlog complete <task-id>
```

O padrão é uma task por interação. Para fluxos maiores, configure de 1 a 5 itens e o escopo do lote (`task` ou `node`) em `.looper/config.json` ou com `looper backlog config --task-batch-size 2 --task-batch-scope node`. O escopo geral de entrega (`task_delivery_scope`) vale para as duas fases: `task` entrega cada item separadamente; `node` entrega o nó L2 com seus subfluxos internos juntos e conclui esse conjunto pelo ID do nó pai. No modo `node`, o loop de testes exige cobertura do nó e de todos os subfluxos, e o loop de implementação exige a tela e o funcionamento completo do pacote. “Tela” classifica o nível do nó, mas não limita a implementação ao frontend; endpoints, regras, persistência, hooks e integrações descritos no Draw também pertencem à entrega. Cada item continua exigindo seu próprio `backlog complete` no modo `task`; no modo `node`, a conclusão do pai conclui o conjunto entregue.

`backlog.development_mode` controla a arquitetura do loop. O padrão `sequential` mantém tela e comportamento na sequência original. Em `separated`, o cursor libera primeiro todos os nós L2 como frontend/view e só depois os nós L3 como backend/controller/model, independentemente da ordem entre branches. A task L2 inclui estados, interações e links/transições entre telas, mas não implementa regra de negócio, controller, model, persistência ou integrações de backend. Nesse modo, o loop de testes entrega somente L3; L2 fica com `test_status: not-required`. Configure pelo init (`--development-mode separated`) ou por `looper backlog config --development-mode separated`. O cursor usa lease e respeita a janela mínima configurada (`min_task_interval_seconds`, nunca menor que 3 quando habilitada), bloqueando chamadas fora de ordem ou tentativas de avançar várias tasks em um único script.

Para consumir somente uma camada, use `looper backlog task --frontend` ou `looper backlog task --backend`; `--layer frontend|backend|all` é a forma equivalente explícita. Os mesmos filtros existem em `looper backlog test`. Eles afetam apenas a consulta atual, preservam a ordem e o cursor, e retornam uma mensagem específica quando não há mais tasks daquela camada sem declarar o backlog completo.

O bootstrap é a primeira task por padrão e é agnóstico de framework: prepara o ponto de entrada, arquivos raiz, configuração, dependências, convenções e comandos necessários para receber as próximas tasks. O agente interpreta as evidências locais da stack e não deve inventar arquivos ou implementar funcionalidade de produto nessa etapa. A task também audita Draw System nível 1, `.looper/design.md`, ambiente, `.env.example` e a estrutura mínima de armazenamento; `--no-bootstrap` continua disponível para projetos que optarem explicitamente por não executar essa preparação. Após cada nó L2 e seus subfluxos, o backlog pode injetar uma task de verificação obrigatória: o agente deve ler o Draw, carregar e ler os arquivos indicados, analisar símbolos e dependências, executar os testes aplicáveis e declarar se o comportamento está implementado, parcial, ausente ou bloqueado, sempre com evidências. A associação de símbolos, arquivos de implementação e testes pode ser uma task separada. A task final valida inicialização, renderização, uso básico e lacunas funcionais com o mesmo critério de auditoria real.

`looper backlog task` e `looper backlog test` mostram somente o contexto acionável em linguagem humana: task, fluxo, nó, uma decisão respondida, os símbolos associados e a diretriz do nível. Não há saída JSON nesses comandos. Tasks de nível 2 recebem a definição escolhida para classificar o nó como tela; quando o escopo é `node`, a saída também exige o nó inteiro e todos os subfluxos, incluindo as camadas não visuais descritas neles. Tasks de nível 3 recebem a definição escolhida para orientar regras de negócio e/ou detalhes da tela.

O ícone de loop em cada nó abre pedidos de alteração (`changes`). Registre uma mudança que possa alcançar vários arquivos ou nós e execute `looper backlog change`; ele reserva um pedido por vez com o contexto e os símbolos do nó. Use também `--frontend`, `--backend` ou `--layer` para filtrar alterações L2/L3. Depois de implementar, testar e registrar as evidências, conclua pelo mesmo `looper backlog complete <task-id>`. Esse cursor é independente das fases de teste e implementação para permitir correções incrementais sem reordenar o backlog de produto.

O contexto de navegação agora identifica explicitamente a tela de destino e todas as entradas possíveis. Para cada entrada, a saída mostra a tela de origem, sua descrição, a condição (`então`, `ou`, `se`), a ação registrada e a transição completa (`origem → destino`). O primeiro nó não recebe uma origem artificial: ele informa que é o início do fluxo. Em subtasks de nível 3, a saída separa a tela relacionada da etapa interna. Os estados distinguem testes ausentes, testes prontos, implementação em andamento e backlog concluído.

Quando o loop de testes está habilitado, antes da implementação crie incrementalmente o teste da jornada:

```bash
looper backlog test
looper backlog complete <task-id>
```

Um nó de nível 2 pode declarar `test_ref` — ou `test_refs` compatíveis — com um único arquivo e as funções que cobrem o nó e todos os seus subfluxos. Quando essa referência existir, a análise estática será exibida como evidência complementar; ela não é obrigatória para marcar o checklist. Com o loop habilitado, `backlog test` entrega primeiro a preparação agnóstica (`backlog-bootstrap-task`) e, depois de concluída, a task reservada para criar os testes sem alterar produção; fluxos de sistemas já existentes também podem ser marcados manualmente no viewer. Com o loop desabilitado, `backlog test` não cria nem reserva tasks e o cursor de implementação segue diretamente para as tasks de implementação.

O backlog mantém dois checklists centrais em `phase_checklists`: `test` vem antes de `implementation`, e os itens são derivados das tasks e subfluxos. No Draw, ao selecionar um nó, a Sidebar permite marcar ou desmarcar esses itens. A marcação é persistida no `.looper/backlog.json` pelo servidor local, sem validação obrigatória de análise estática; a implementação continua bloqueada enquanto o checklist de teste do nó e de seus subfluxos estiver pendente.

Se `backlog task` for chamado antes da marcação do checklist de teste, ele mostra o bloqueio em linguagem humana e não reserva a implementação. `$implement-frontend` e `$implement-backend` devem atender essa resposta com a etapa de testes ou com a marcação manual do fluxo já existente. Changes criadas por revisão ou interação seguem o cursor separado `looper backlog change` e a skill `$implement-change`. Com `backlog.test_loop_enabled: false`, essa barreira é removida intencionalmente e o cursor entrega somente tasks de implementação. Self-loops são terminais; ciclos diferentes de self-loop são bloqueados para evitar execução infinita. A aba `Backlog` do viewer mostra a task atual, perguntas, respostas, símbolos e a evidência opcional do teste quando o Draw Server está ativo.

Quando uma task possui subfluxo, a saída humana mostra o contexto do pai e a task atual. Pai e subtasks são independentes e devem ser concluídos pelos seus próprios IDs; a resposta mantém o contexto do pai enquanto avança pela primeira, segunda e demais subtasks.

## Executar testes

Para conferir somente os símbolos associados aos nós dos Draws, sem executar os testes do sistema:

```bash
looper draw symbols
```

O comando lista os símbolos por nó e termina com código diferente de zero quando encontra uma associação ausente em um Draw de nível 2, 3 ou 4.

```bash
looper test
```

Esse é o alias global. Ele executa os testes de regressão da codebase, as demais suítes configuradas, análise estática, contrato e runners da stack. Suítes que exigem aprovação explícita aparecem como `not_executed` quando não autorizadas.
Testes Playwright são separados dos testes de regressão: declare a suíte com `type: playwright` em `test_commands`. Eles não rodam por padrão e aparecem como `not_executed`; use a flag explícita para incluí-los:

```bash
looper test --playwright
```
Se `.looper/backlog.json` existir, o alias também executa o gate do backlog e bloqueia enquanto houver task sem `backlog complete` ou nó de nível 2 sem teste comprovado; a saída do terminal mostra somente status e contagens, mantendo os detalhes no relatório estruturado.
Quando a análise encontrar um nó já concluído no backlog sem símbolo, a saída inclui o `kind`, o arquivo do Draw e o `node_id` do achado bloqueante (`draw.level*_missing_code_ref` ou `draw.empty_node_symbol`). Nós ainda em especificação ou implementação pendente não geram bloqueio por ausência de símbolo.

Opções úteis:

```bash
looper test --suite unit
looper test --exclude performance
looper test --profile mvp
looper test --approve-actions
looper test --playwright
```

## Abrir e editar o Draw

O Draw Server é o processo responsável por ler e salvar os desenhos. O viewer React Flow compilado vem dentro do pacote Python do Looper; o projeto do usuário não recebe HTML, JavaScript, CSS ou dependências Node. O servidor mantém os Draws em `.looper/draws/` e os relatórios derivados da análise em `.looper/facts/`.

O editor consulta `GET /.looper/api/draws/<draw-id>/revision` a cada 2 segundos
quando está conectado ao Draw Server. A consulta retorna somente a revisão leve
do JSON; o fluxo completo é recarregado automaticamente quando a revisão muda.
Alterações locais não salvas nunca são sobrescritas: nesse caso, a interface
mostra que existe uma atualização pendente e só recarrega depois que o rascunho
for salvo ou descartado.

O botão `Observar` ativa o modo Observador. Ele consulta o backlog a cada 2
segundos, identifica a implementação em andamento e navega automaticamente para
o Draw e o nó correspondentes, inclusive quando a task muda para outro fluxo ou
subfluxo. Nesse modo o canvas, os atalhos e as ações de edição ficam somente para
leitura; o modo não salva nem altera o desenho.

No diretório raiz do projeto, execute:

```bash
looper draw serve --port 8765
```

Depois abra no navegador pela URL do servidor:

```text
http://127.0.0.1:8765/.looper/draw.html
```

O caminho `/.looper/draw.html` é uma rota virtual de compatibilidade: nenhum arquivo HTML é criado dentro do projeto. Mantenha `looper draw serve --port 8765` em execução enquanto o viewer estiver aberto. O Live Server não é necessário.

O `looper init` instala um JSON de exemplo em `.looper/draws/demo-inicial.json`, para que o viewer sempre tenha um fluxo inicial visível. A instalação é idempotente e não duplica esse exemplo.

O comando `looper draw create` rejeita qualquer desenho que contenha um nó sem edge incidente; a relação é considerada não direcionada, então basta o nó participar de `from` ou `to`. Um desenho vazio continua válido para iniciar a edição visual. O mesmo comando também executa uma análise estrutural em memória: títulos, fluxos, subfluxos, sequências de nós e conexões repetidos ou muito próximos aparecem como warnings no terminal. Essa análise nunca bloqueia a criação e não prova que o desenho foi gerado por script; ela apenas indica uma possível estrutura automatizada que deve ser revisada.

Os fontes editáveis do viewer ficam em [`draw-editor/`](draw-editor/README.md). Eles são usados apenas para desenvolvimento e recompilação do pacote; não são instalados nos projetos dos usuários.

Ao clicar em `＋ Novo desenho`, o Draw pede o nome do desenho antes de criá-lo. O viewer carrega apenas o desenho selecionado, lê seu JSON em `.looper/draws/` e salva alterações lógicas pelo endpoint local `/__looper/api/draws/<id>.json`. Cores e posições são preferências da experiência visual; elas ficam no armazenamento local do navegador e não alteram o contrato JSON.

O Live Server continua opcional para desenvolvimento do próprio editor React, mas não é necessário para usar o viewer instalado.

Na aba `Backlog`, o viewer usa o Draw Server local para separar as fases do ciclo: `POST /__looper/api/backlog/test` reserva a task de testes, `POST /__looper/api/backlog/tasks/<task-id>/complete` conclui a fase atual e `POST /__looper/api/backlog/refresh` regenera as evidências exibidas. A implementação só fica disponível depois que o teste da task e de seus subfluxos estiver concluído.

Atalhos e gestos principais:

- Duplo clique em um bloco: editar nome e descrição diretamente.
- Duplo clique em uma seta: editar seu rótulo diretamente; botão direito: avançar a condição `então` → `ou` → `se`.
- Arrastar a saída roxa de um bloco: criar uma conexão.
- Clicar uma vez na saída roxa: conectar automaticamente ao próximo bloco lógico à frente.
- Arrastar a saída roxa: escolher manualmente qualquer bloco de destino.
- Selecionar uma seta: mostra um botão `×` sobre a própria seta para desconectá-la.
- Duplo clique no fundo: criar um novo bloco naquele ponto.
- `Ctrl/Cmd+C`: copiar o nó selecionado como JSON do contrato lógico.
- `Ctrl/Cmd+V`: colar um JSON de nó e criar um novo bloco com novo ID.
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

As tags são case-insensitive: `@looper` representa ação do agente, `@developer` representa resposta humana e `@obs` registra contexto que o agente deve consumir. `@looper` não é somente uma solicitação de resposta: se o texto ordenar uma mudança concreta, o agente deve executá-la, validá-la e registrar o resultado. O comando canônico para pendências é:

```bash
looper draw questions
looper draw questions --tag developer
looper draw questions --tag obs --answered
looper draw consume-observation --draw-id <draw-id> --question-id <id> [--node-id <node-id>]
```

Respostas removem automaticamente somente `@looper` e `@developer`; `@obs` permanece até o consumo explícito, que devolve pergunta e resposta e remove apenas a tag. Perguntas gerais, sem `node_id`, pertencem ao painel de melhorias; perguntas de nó permanecem associadas ao nó.

## Segurança e análise estática

O scanner interno procura credenciais hardcoded, tokens conhecidos e valores copiados de `.env` para o código. O valor nunca é gravado no relatório; ele aparece como `[REDACTED]`. Um vazamento detectado bloqueia o gate de testes.

Fixtures de teste que usam credenciais sintéticas, CEDs, INVs ou tokens fictícios podem ser marcadas explicitamente na própria linha (ou na linha anterior):

```python
PASSWORD = "ced-ficticia"  # looper:allow-credential
```

Em arquivos de teste, o achado continua visível como `warning` e não bloqueia. Fora de arquivos de teste, o marcador é ignorado e o achado continua bloqueante. Para exigir bloqueio mesmo em fixtures marcadas, configure `"allow_marked_test_credentials": false` dentro de `static_analysis` em `.looper/config.json`.

Arquivos `.env`, `.pyc`, caches, ambientes virtuais e artefatos de build são ignorados pelo Git automaticamente. Variáveis de ambiente sem referência no código geram aviso, não bloqueio automático, porque podem ser utilizadas por infraestrutura ou serviços externos.

### Rastreabilidade entre nós e símbolos

O vínculo entre um nó do Draw e um símbolo da codebase é feito pelo agente, de forma explícita e determinística. A responsabilidade é dividida assim:

- o adapter de análise estática descobre fatos reais: símbolos, dependências, arquivos, testes e métricas;
- o agente analisa o desenho e os fatos do adapter para identificar a correspondência correta;
- o agente executa `looper draw associate-reference` para gravar a associação no nó;
- o Looper recalcula os fatos derivados e informa se o vínculo está `resolved`, `unresolved` ou em `drift`;
- o usuário intervém quando houver ambiguidade, símbolo ausente ou alteração que exija decisão arquitetural.

O adapter não deve alterar desenhos automaticamente. Ele fornece os fatos; o agente decide qual símbolo representa o nó e persiste a referência declarada. O vínculo mínimo exige o desenho, o `node_id`, o nome qualificado do símbolo e pelo menos uma dependência de origem:

```bash
looper draw associate-reference \
  --draw-id nome-do-desenho \
  --node-id 42 \
  --qualified-name 'orders.OrderService.create' \
  --source-dependency 'orders.OrderRepository.save' \
  --source-dependency 'tests.orders.test_create_order'
```

O comando valida o desenho e o nó e grava a referência no JSON lógico. Em uma nova análise estática, o Looper cruza essa referência com `symbols` e `dependencies` e gera o relatório derivado em `.looper/facts/<draw-id>.facts.json`, incluindo arquivos, testes relacionados e possíveis dependências para revisão. Para subfluxos, repetir a associação nos nós do subfluxo e manter a referência ao nó chamador.

## Registrar trabalho

```bash
looper log "Implementa autenticação" --impl
looper log "Adiciona testes de autenticação" --test
looper log "Corrige regressão" --bug
looper log "Reestrutura código sem planejamento prévio" --refactor
```

Mantenha registros de implementação e testes separados quando forem trabalhos diferentes.

## Artefatos principais

```text
.looper/
├── config.json
├── draws/
├── runs.html
└── runs/
```

As skills dos agentes ficam fora de `.looper`, em seus diretórios próprios, e os demais artefatos do framework permanecem dentro de `.looper`.
