# Contexto estruturado dos Draws

## Nível 1 — Arquitetura do sistema de especificação Looper
Draw: `looper-system-architecture` · papel: architecture
Resumo: O próprio Looper documentado pelo método que ele oferece aos agentes

### Nó 9 — Draw Server e viewer embutido
Servidor HTTP local que entrega o viewer React Flow empacotado e a API de desenhos. Ao trocar de Draw, o canvas remonta a instância do React Flow por identificador do desenho para descartar estados internos antigos de nós e arestas, evitando que elementos ou setas fiquem ocultos por reutilização de IDs.
então[O viewer acessa desenhos pela API local.] -> Nó 7 — .looper/draws (lê e salva)
### Código
- `src/looper/draw.py::looper.draw.serve_draw`
- `src/looper/cli.py::looper.cli.draw_serve`
- `draw-editor/src/App.tsx::App`

### Nó 10 — Codebase Python e pytest
Runtime Python >= 3.11, Typer, setuptools e pytest; sem banco ou serviço externo obrigatório.
então[O núcleo é implementado em Python e executado pelos runners configurados.] -> Nó 3 — Núcleo de execução (implementa)
### Código
- `src/looper/core.py::looper.core.execute_test_suite`

### Nó 11 — Agentes Looper e integrações
Skills especializadas que conduzem o ciclo de especificação, desenho, análise e implementação; instaladas nas integrações Codex, Claude e Gemini.
então[As skills orientam o comportamento do agente no projeto.] -> Nó 1 — Agente de código (instrui)
então[Os agentes transformam pedidos em jornadas documentadas e entregáveis verificáveis.] -> Nó 8 — Jornadas do usuário do Looper (conduz jornadas)
Draws descendentes: `looper-agent-journeys`
### Código
- `src/looper/reviews.py::looper.reviews.run_review`

### Nó 1 — Agente de código
Consumidor das skills instaladas, responsável por especificar, desenhar, implementar e relatar o trabalho.
então[O agente usa a CLI como superfície de controle.] -> Nó 2 — CLI looper (opera por)
### Código
- `src/looper/reviews.py::looper.reviews._run_agent`

### Nó 2 — CLI looper
Interface operacional para init, setup, test, log e draw. O init sincroniza as skills do template atual e remove apenas os nomes legados conhecidos pelo framework, preservando skills específicas do projeto.
então[Os subcomandos delegam ao núcleo Python.] -> Nó 3 — Núcleo de execução (despacha para)
então[Os comandos e skills são detalhados no nível de jornada.] -> Nó 8 — Jornadas do usuário do Looper (abre jornadas)
### Código
- `src/looper/cli.py::looper.cli.app`
- `src/looper/core.py::looper.core.init_project`

### Nó 3 — Núcleo de execução
Coordena inicialização, runners, contratos, análise estática, rastreabilidade e registro de execuções.
então[A execução é orientada pela configuração do projeto.] -> Nó 5 — .looper/config.json (lê e atualiza)
então[Resultados, snapshots e fatos ficam em .looper/.] -> Nó 6 — .looper/runs e facts (registra evidências)
se[Contratos e testes bloqueiam a conclusão quando falham.] -> Nó 4 — Contrato e testes do framework (se houver gate)
então[Desenhos são JSONs versionáveis.] -> Nó 7 — .looper/draws (persiste desenhos)
### Código
- `src/looper/core.py::looper.core.run_tests`
- `src/looper/core.py::looper.core.record_run_entry`

### Nó 4 — Contrato e testes do framework
Suítes pytest e regras de contrato que protegem o comportamento do próprio Looper.
### Código
- `src/looper/draw.py::looper.draw.validate_draw_payload`
- `src/looper/static_analysis.py::looper.static_analysis.validate_static_analysis_result`

### Nó 5 — .looper/config.json
Configuração de runners, stack detectada, contrato e adapter de análise estática.
### Código
- `src/looper/setup.py::looper.setup.configure_project`
- `src/looper/reviews.py::looper.reviews.load_review_config`

### Nó 6 — .looper/runs e facts
Estado versionável de execuções, snapshots, KPIs de análise e fatos de rastreabilidade.
### Código
- `src/looper/runs.py::looper.runs.update_runs_index`
- `src/looper/traceability.py::looper.traceability.refresh_traceability`

### Nó 7 — .looper/draws
Fonte de verdade JSON dos desenhos, com índice e relações hierárquicas.
### Código
- `src/looper/draw.py::looper.draw.create_draw`
- `src/looper/draw.py::looper.draw.collect_draw_context`

### Nó 8 — Jornadas do usuário do Looper
Entrada para o desenho de nível 2: como agente e desenvolvedor usam o sistema.
Draws descendentes: `looper-user-journeys`
### Código
- `src/looper/cli.py::looper.cli.init`


## Nível 1 — Demonstração: perguntas, respostas e loop
Draw: `demo-perguntas-respostas` · papel: architecture
Resumo: Fluxo para validar perguntas respondidas, pendências e retorno ao início

### Nó 1 — Escolher plano
Cliente seleciona a opção de assinatura.
então[O cliente confirmou a escolha.] -> Nó 2 — Validar pagamento (inicia validação)
### Decisões
- Qual plano foi escolhido? — 2
- Precisa de aprovação manual? — False
- Qual observação falta confirmar? — em aberto

### Nó 2 — Validar pagamento
Confere dados e disponibilidade do meio de pagamento.
se[Ativa somente com autorização confirmada.] -> Nó 3 — Aprovar assinatura (pagamento aprovado)
ou[Permite corrigir os dados e repetir a tentativa.] -> Nó 4 — Revisar dados (pagamento rejeitado)
### Decisões
- Qual observação deve acompanhar a validação? — Usar tokenização e registrar a chave idempotente.

### Nó 3 — Aprovar assinatura
Ativa a assinatura e registra a confirmação.

### Nó 4 — Revisar dados
Corrige dados antes de tentar novamente.
então[Depois da correção, o fluxo retorna para validar a escolha novamente.] -> Nó 1 — Escolher plano (volta ao início)
### Decisões
- Os dados foram corrigidos? — em aberto


## Nível 1 — Exemplo inicial do Looper
Draw: `demo-inicial` · papel: architecture
Resumo: Fluxo de demonstração para começar a explorar o viewer

### Nó 1 — Escolher plano
Cliente seleciona a opção de assinatura.
então[O cliente confirmou a escolha.] -> Nó 2 — Validar pagamento (inicia validação)
### Decisões
- Qual plano foi escolhido? — 2
- Precisa de aprovação manual? — False
- Qual observação falta confirmar? — em aberto

### Nó 2 — Validar pagamento
Confere dados e disponibilidade do meio de pagamento.
se[Ativa somente com autorização confirmada.] -> Nó 3 — Aprovar assinatura (pagamento aprovado)
ou[Permite corrigir os dados e repetir a tentativa.] -> Nó 4 — Revisar dados (pagamento rejeitado)
### Decisões
- Qual observação deve acompanhar a validação? — Usar tokenização e registrar a chave idempotente.

### Nó 3 — Aprovar assinatura
Ativa a assinatura e registra a confirmação.

### Nó 4 — Revisar dados
Corrige dados antes de tentar novamente.
então[Depois da correção, o fluxo retorna para validar a escolha novamente.] -> Nó 1 — Escolher plano (volta ao início)
### Decisões
- Os dados foram corrigidos? — em aberto


## Nível 2 — Agentes e responsabilidades do Looper
Draw: `looper-agent-journeys` · papel: journey
Pai: `looper-system-architecture` · nó 11
Resumo: As skills que conduzem o ciclo de especificação orientada por testes

### Nó 1 — Pedido do usuário
Intenção, problema, mudança arquitetural ou necessidade de documentação recebida pelo agente hospedeiro.
então[A stack e os gates precisam ser conhecidos antes da execução.] -> Nó 2 — $setup (então prepara)
se[O agente cria ou amplia a arquitetura completa.] -> Nó 3 — $draw-system (se o escopo é um sistema)
se[O agente desenha somente o fluxo relacionado.] -> Nó 4 — $draw-feature (se o escopo é uma feature)
### Código
- `src/looper/cli.py::looper.cli.app`

### Nó 2 — $setup
Descobre a stack, runners, bancos, provedores e configura o Looper sem inventar capacidades. Encaminha para $draw-system quando falta uma raiz de sistema.
### Código
- `src/looper/setup.py::looper.setup.detect_stack`
- `src/looper/setup.py::looper.setup.configure_project`

### Nó 4 — $draw-feature
Desenha uma feature, fluxo, decisão ou trade-off como JSON navegável, respeitando a árvore do sistema quando existir.
então[O desenho da feature vira contrato de testes.] -> Nó 6 — $create-tests (então especifica)
### Código
- `src/looper/draw.py::looper.draw.create_draw`

### Nó 5 — $draw-improve
Revisa um Draw existente e acrescenta apenas o próximo detalhe arquitetural relevante, preservando intenção, escopo e vínculos.
se[A melhoria retorna ao contexto arquitetural sem duplicar o filho.] -> Nó 3 — $draw-system (se revelar lacuna sistêmica)
então[Após a revisão, o desenho aprovado pode gerar testes.] -> Nó 6 — $create-tests (então encaminha)
### Código
- `src/looper/cli.py::looper.cli.draw_improve`
- `src/looper/draw.py::looper.draw.format_draw_answers`

### Nó 8 — $static-analysis
Implementa ou conecta adapters agnósticos e produz fatos determinísticos sobre símbolos, dependências, complexidade, estrutura e alterações.
então[A análise alimenta rastreabilidade e gates, não inventa associações.] -> Nó 9 — looper test e looper log (fornece fatos para)
### Código
- `src/looper/static_analysis.py::looper.static_analysis.run_static_analysis`
- `src/looper/static_analysis.py::looper.static_analysis.apply_static_analysis_policy`

### Nó 10 — Codex
Integração padrão: instala as skills em .agents/skills/ e fornece o AGENTS.md compartilhado para qualquer agente compatível.
então[Codex disponibiliza as skills ao agente.] -> Nó 3 — $draw-system (hospeda)
### Código
- `src/looper/reviews.py::looper.reviews._command`
- `src/looper/reviews.py::looper.reviews.load_review_config`

### Nó 11 — Claude
Integração de agente que instala as skills em .claude/skills/.
então[Claude disponibiliza as skills ao agente.] -> Nó 3 — $draw-system (hospeda)
### Código
- `src/looper/reviews.py::looper.reviews._command`

### Nó 12 — Gemini
Integração de agente que instala as skills em .gemini/skills/.
então[Gemini disponibiliza as skills ao agente.] -> Nó 3 — $draw-system (hospeda)
### Código
- `src/looper/reviews.py::looper.reviews._command`

### Nó 3 — $draw-system
Modela o sistema completo em arquitetura, jornadas, implementação e codebase quando necessário; mantém a árvore hierárquica sem órfãos.
então[Jornadas implementáveis viram testes executáveis.] -> Nó 6 — $create-tests (então especifica)
### Código
- `src/looper/draw.py::looper.draw.create_draw`
- `src/looper/draw.py::looper.draw.collect_draw_context`

### Nó 6 — $create-tests
Transforma jornadas e desenhos em testes executáveis vermelhos, sem alterar código de produção; trata folhas não implementadas como escopo ausente.
se[A implementação só começa depois da especificação testável.] -> Nó 7 — $implement (se os testes vermelhos foram aprovados)
então[Uma especificação também produz evidência do trabalho realizado.] -> Nó 9 — looper test e looper log (então verifica e registra)
### Código
- `src/looper/core.py::looper.core.run_tests`

### Nó 7 — $implement
Implementa o comportamento de produção guiado pelos testes aprovados, preservando contratos, segurança e qualidade estrutural; depois atualiza o Draw correspondente. Detalhes sem mudança de comportamento viram perguntas no nível L2/L3 correto, e mudanças de fluxo também atualizam as conexões dos nós.
então[Toda implementação passa por looper test e looper log.] -> Nó 9 — looper test e looper log (então verifica e registra)
### Código
- `src/looper/core.py::looper.core.init_project`
- `src/looper/traceability.py::looper.traceability.associate_node_reference`

### Nó 9 — looper test e looper log
Não são agentes: são gates e evidências operacionais que verificam e registram o trabalho conduzido pelas skills. O comando looper draw context organiza todos os níveis, conexões, perguntas, respostas e símbolos em texto para consumo do agente. Revisões e correções delegadas a subagentes usam exclusivamente sessões tmux após autorização do usuário.
se[A entrega fica rastreável e pronta para revisão.] -> Nó 13 — Entrega documentada (se os gates passam)
se[O fluxo retorna à especificação ou implementação; não declara sucesso falso.] -> Nó 6 — $create-tests (se algum gate falha)
### Código
- `src/looper/cli.py::looper.cli.draw_context`
- `src/looper/draw.py::looper.draw.collect_draw_context`
- `src/looper/draw.py::looper.draw.format_draw_context`
- `src/looper/reviews.py::looper.reviews.load_review_config`
- `src/looper/reviews.py::looper.reviews._run_agent`
- `src/looper/cli.py::looper.cli.test_all`
- `src/looper/cli.py::looper.cli.log_work`

### Nó 13 — Entrega documentada
Estado final esperado: comportamento especificado, implementado quando aplicável, verificado, desenhado e registrado.
### Código
- `src/looper/core.py::looper.core.record_run_entry`
- `src/looper/draw.py::looper.draw.collect_draw_context`


## Nível 2 — Jornadas de uso do Looper
Draw: `looper-user-journeys` · papel: journey
Pai: `looper-system-architecture` · nó 8
Resumo: Como agente e desenvolvedor especificam, verificam e documentam o sistema

### Nó 1 — Entrada: projeto e pedido
O usuário abre o agente em um projeto e descreve o que precisa ser especificado ou alterado.
então[O agente inicializa o projeto quando a estrutura ainda não está disponível.] -> Nó 2 — Inicializar e instalar skills (então prepara)
### Código
- `src/looper/cli.py::looper.cli.init`

### Nó 2 — Inicializar e instalar skills
O agente prepara .looper/, instruções e skills para o projeto.
então[Skills instaladas orientam a especificação e o desenho.] -> Nó 3 — Especificar e desenhar (então especifica)
Draws descendentes: `looper-journey-init`
### Código
- `src/looper/core.py::looper.core.init_project`
Dependências: looper.core.ensure_agent_instructions, looper.draw.ensure_draw_workspace

### Nó 3 — Especificar e desenhar
O pedido vira feature testável ou árvore Draw; o desenho registra caminhos implementados e folhas ausentes.
então[A implementação ou documentação passa pelos gates do Looper.] -> Nó 4 — Executar gates (então verifica)
### Código
- `src/looper/draw.py::looper.draw.create_draw`
- `src/looper/cli.py::looper.cli.draw_create`
Dependências: looper.draw.validate_draw_payload

### Nó 4 — Executar gates
O agente executa testes, contrato e análise estática antes de declarar conclusão.
então[Somente após os gates passarem o trabalho é registrado como concluído.] -> Nó 5 — Registrar evidência (se aprovado, registra)
se[A tarefa não pode ser declarada concluída.] -> Nó 7 — Bloqueado ou pendente (se algum gate falhar)
Draws descendentes: `looper-journey-test`
### Código
- `src/looper/core.py::looper.core.run_tests`
- `src/looper/cli.py::looper.cli.test_all`
Dependências: looper.core.execute_test_suite, looper.static_analysis.run_static_analysis

### Nó 5 — Registrar evidência
O trabalho concluído recebe log com tipo e diff incremental. Após o intervalo configurado de tasks, um agente externo é chamado pelo terminal ou tmux para revisar a entrega; lacunas viram changes no Draw.
então[A evidência e o desenho ficam disponíveis para revisão humana.] -> Nó 6 — Revisar no Draw (então revisa)
Draws descendentes: `looper-journey-log`
### Código
- `src/looper/core.py::looper.core.record_run_entry`
- `src/looper/cli.py::looper.cli.log_work`
Dependências: looper.core.get_incremental_diff_stats

### Nó 6 — Revisar no Draw
O usuário abre o viewer local, navega pela árvore e revisa decisões, perguntas e trade-offs.
se[A revisão confirma a entrega rastreável.] -> Nó 8 — Entrega rastreável (se não houver pendência)
Draws descendentes: `looper-journey-draw`
### Código
- `src/looper/draw.py::looper.draw.serve_draw`
- `src/looper/cli.py::looper.cli.draw_serve`
Dependências: looper.draw.create_server

### Nó 7 — Bloqueado ou pendente
Falha de teste, símbolo não resolvido ou decisão em aberto permanece visível e impede uma conclusão falsa.
então[O agente retorna à especificação ou implementação após resolver o bloqueio.] -> Nó 3 — Especificar e desenhar (corrige e repete)
### Código
- `src/looper/static_analysis.py::looper.static_analysis.blocked_result`

### Nó 8 — Entrega rastreável
A mudança termina com fontes, testes, desenho e evidências coerentes no repositório.
### Código
- `src/looper/traceability.py::looper.traceability.refresh_traceability`
Dependências: looper.traceability.build_traceability_report


## Nível 3 — Implementação da jornada de documentação visual
Draw: `looper-journey-draw` · papel: implementation
Pai: `looper-user-journeys` · nó 6
Resumo: Como looper draw cria, serve e persiste a árvore de desenhos

### Nó 1 — Receber JSON lógico
O comando draw create recebe o payload sem layout, cores ou HTML.
então[A criação rejeita payload inválido.] -> Nó 2 — Validar contrato e hierarquia (então valida)
### Código
- `src/looper/cli.py::looper.cli.draw_create`
Dependências: looper.draw.create_draw

### Nó 2 — Validar contrato e hierarquia
Confere IDs, relações, fluxos, perguntas e pai explícito antes de persistir.
então[O desenho vira fonte de verdade.] -> Nó 3 — Persistir desenho e índice (se válido, grava)
### Código
- `src/looper/draw.py::looper.draw.validate_draw_payload`
Dependências: looper.draw.validate_hierarchy_parent

### Nó 3 — Persistir desenho e índice
Grava o JSON em .looper/draws e atualiza o índice.
então[O viewer lê o estado persistido.] -> Nó 4 — Servir viewer e API local (então serve)
### Código
- `src/looper/draw.py::looper.draw.create_draw`
Dependências: looper.draw.validate_draw_payload, looper.draw.validate_hierarchy_parent

### Nó 4 — Servir viewer e API local
O servidor embutido entrega o viewer e endpoints GET/PUT dos desenhos.
então[A árvore é explorada visualmente.] -> Nó 5 — Árvore navegável (então permite revisar)
### Código
- `src/looper/cli.py::looper.cli.draw_serve`
- `src/looper/draw.py::looper.draw.serve_draw`
Dependências: looper.draw.serve_draw
Dependências: looper.draw.create_draw

### Nó 5 — Árvore navegável
O usuário navega da arquitetura às jornadas e implementações, mantendo decisões agrupadas, referências de código e conexões autocontidas.
### Código
- `src/looper/draw.py::looper.draw.collect_draw_context`
Dependências: looper.draw.format_draw_context, looper.draw._context_question_lines, looper.draw._context_reference_lines


## Nível 3 — Implementação da jornada de evidência
Draw: `looper-journey-log` · papel: implementation
Pai: `looper-user-journeys` · nó 5
Resumo: Como looper log registra o trabalho e o diff incremental

### Nó 1 — Receber descrição e tipo
Aceita descrição curta e tipo implementacao, teste, bug ou refactor.
então[A descrição é acompanhada por estatísticas do Git.] -> Nó 2 — Coletar diff e snapshot (então mede)
### Código
- `src/looper/cli.py::looper.cli.log_work`
Dependências: looper.core.record_run_entry

### Nó 2 — Coletar diff e snapshot
Compara o estado atual com o checkpoint e salva resumo e snapshot em .looper/runs.
então[O registro é salvo nos artefatos internos.] -> Nó 3 — Registrar execução (então persiste)
### Código
- `src/looper/core.py::looper.core.get_incremental_diff_stats`
Dependências: looper.core.get_workspace_snapshot

### Nó 3 — Registrar execução
Persiste o registro sem incluir segredos e marca retrabalho quando aplicável.
então[A evidência fica disponível para revisão.] -> Nó 4 — Evidência disponível (então expõe)
### Código
- `src/looper/core.py::looper.core.record_run_entry`
Dependências: looper.runs.update_runs_index

### Nó 4 — Evidência disponível
O usuário pode revisar o log e o diff no painel de runs.
### Código
- `src/looper/runs.py::looper.runs.runs_directory`


## Nível 3 — Implementação da jornada de inicialização
Draw: `looper-journey-init` · papel: implementation
Pai: `looper-user-journeys` · nó 2
Resumo: Como looper init prepara o projeto para o agente

### Nó 1 — Receber destino com Codex padrão
A CLI valida o diretório e usa Codex como integração padrão, sem perguntar qual agente deve ser usado. Outras integrações só entram quando solicitadas explicitamente por flag.
então[A inicialização materializa a estrutura mínima.] -> Nó 2 — Criar configuração e estado (então cria estado)
### Código
- `src/looper/cli.py::looper.cli.init`
Dependências: looper.core.init_project

### Nó 2 — Criar configuração e estado
Cria .looper/config.yaml, runs, features, draws e regras de gitignore.
então[Skills e instruções são sincronizadas.] -> Nó 3 — Instalar skills e instruções (então instala)
### Código
- `src/looper/setup.py::looper.setup.configure_project`
- `src/looper/core.py::looper.core.looper_dir`

### Nó 3 — Instalar skills e instruções
Copia templates atuais e atualiza AGENTS.md; arquivos específicos de outros agentes só são instalados quando a integração é solicitada explicitamente. O contrato de instruções não orienta a instalação ou atualização do Looper por uv. O AGENTS.md compartilhado instrui todo agente a manter os Draws atualizados.
então[A CLI informa o projeto inicializado.] -> Nó 4 — Projeto pronto (então retorna sucesso)
### Código
- `src/looper/core.py::looper.core.ensure_agent_instructions`
Dependências: looper.core.agent_templates

### Nó 4 — Projeto pronto
O agente pode usar as skills no projeto inicializado.
### Código
- `src/looper/core.py::looper.core.init_project`
Dependências: looper.draw.ensure_draw_workspace, looper.core.ensure_gitignore, looper.core.ensure_agent_instructions


## Nível 3 — Implementação da jornada de verificação
Draw: `looper-journey-test` · papel: implementation
Pai: `looper-user-journeys` · nó 4
Resumo: Como looper test transforma configuração em evidência de qualidade

### Nó 1 — Ler perfil e suítes
A execução seleciona suítes, exclusões, perfil e aprovações. Testes de regressão da codebase rodam por padrão; suítes declaradas com type: playwright ficam como not_executed até receberem a flag explícita --playwright.
então[A configuração determina os comandos.] -> Nó 2 — Executar runners e contrato (então executa)
### Código
- `src/looper/cli.py::looper.cli.test_all`
Dependências: looper.core.run_tests

### Nó 2 — Executar runners e contrato
Subprocessos, contrato e ações aprovadas são executados com captura de resultado. O alias global preserva a regressão como padrão e só inclui E2E Playwright quando solicitado explicitamente.
então[A análise complementa os runners.] -> Nó 3 — Analisar estática e rastreabilidade (então analisa)
### Código
- `src/looper/core.py::looper.core.execute_test_suite`
Dependências: looper.core.run_tests

### Nó 3 — Analisar estática e rastreabilidade
O adapter gera símbolos, dependências e métricas; fatos de rastreabilidade são atualizados.
se[A execução fica aprovada.] -> Nó 4 — Gate aprovado (se todos passarem)
se[O bloqueio é mantido como evidência.] -> Nó 5 — Gate bloqueado (se algum falhar)
### Código
- `src/looper/core.py::looper.core.run_tests`
Dependências: looper.static_analysis.run_static_analysis, looper.traceability.refresh_traceability

### Nó 4 — Gate aprovado
Todos os gates passam e a execução pode ser registrada.
### Código
- `src/looper/core.py::looper.core.run_tests`

### Nó 5 — Gate bloqueado
Falha de teste, contrato, análise ou segurança retorna status bloqueado.
### Código
- `src/looper/static_analysis.py::looper.static_analysis.blocked_result`
