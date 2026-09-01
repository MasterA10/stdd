# Contexto estruturado dos Draws

## Nível 1 — Arquitetura do sistema de especificação Looper
Draw: `looper-system-architecture` · papel: architecture
Resumo: O próprio Looper documentado pelo método que ele oferece aos agentes

### Nó 9 — Draw Server e viewer embutido
Servidor HTTP local que entrega o viewer React Flow empacotado e a API de desenhos.
Conecta: então → Nó 7 — .looper/draws (lê e salva)
  Contexto da conexão: O viewer acessa desenhos pela API local.

### Nó 10 — Codebase Python e pytest
Runtime Python >= 3.11, Typer, setuptools e pytest; sem banco ou serviço externo obrigatório.
Conecta: então → Nó 3 — Núcleo de execução (implementa)
  Contexto da conexão: O núcleo é implementado em Python e executado pelos runners configurados.

### Nó 11 — Agentes Looper e integrações
Skills especializadas que conduzem o ciclo de especificação, desenho, análise e implementação; instaladas nas integrações Codex, Claude e Gemini.
Conecta: então → Nó 1 — Agente de código (instrui)
  Contexto da conexão: As skills orientam o comportamento do agente no projeto.
Conecta: então → Nó 8 — Jornadas do usuário do Looper (conduz jornadas)
  Contexto da conexão: Os agentes transformam pedidos em jornadas documentadas e entregáveis verificáveis.
Draws descendentes: `looper-agent-journeys`

### Nó 1 — Agente de código
Consumidor das skills instaladas, responsável por especificar, desenhar, implementar e relatar o trabalho.
Conecta: então → Nó 2 — CLI looper (opera por)
  Contexto da conexão: O agente usa a CLI como superfície de controle.

### Nó 2 — CLI looper
Interface operacional para init, setup, test, log e draw.
Conecta: então → Nó 3 — Núcleo de execução (despacha para)
  Contexto da conexão: Os subcomandos delegam ao núcleo Python.
Conecta: então → Nó 8 — Jornadas do usuário do Looper (abre jornadas)
  Contexto da conexão: Os comandos e skills são detalhados no nível de jornada.

### Nó 3 — Núcleo de execução
Coordena inicialização, runners, contratos, análise estática, rastreabilidade e registro de execuções.
Conecta: então → Nó 5 — .looper/config.json (lê e atualiza)
  Contexto da conexão: A execução é orientada pela configuração do projeto.
Conecta: então → Nó 6 — .looper/runs e facts (registra evidências)
  Contexto da conexão: Resultados, snapshots e fatos ficam em .looper/.
Conecta: se → Nó 4 — Contrato e testes do framework (se houver gate)
  Contexto da conexão: Contratos e testes bloqueiam a conclusão quando falham.
Conecta: então → Nó 7 — .looper/draws (persiste desenhos)
  Contexto da conexão: Desenhos são JSONs versionáveis.

### Nó 4 — Contrato e testes do framework
Suítes pytest e regras de contrato que protegem o comportamento do próprio Looper.

### Nó 5 — .looper/config.json
Configuração de runners, stack detectada, contrato e adapter de análise estática.

### Nó 6 — .looper/runs e facts
Estado versionável de execuções, snapshots, KPIs de análise e fatos de rastreabilidade.

### Nó 7 — .looper/draws
Fonte de verdade JSON dos desenhos, com índice e relações hierárquicas.

### Nó 8 — Jornadas do usuário do Looper
Entrada para o desenho de nível 2: como agente e desenvolvedor usam o sistema.
Draws descendentes: `looper-user-journeys`


## Nível 1 — Cadastro incorporado de WhatsApp
Draw: `cadastro-incorporado-whatsapp` · papel: architecture
Resumo: O caminho principal cria uma tentativa server-side por tenant, abre a jornada Meta, recebe code e reconcilia WABA e número antes de ativar a conexão.

### Nó 0 — Administrador
Usuário autenticado que informa o número e conclui as telas da Meta.
Conecta: então → Nó 1 — Tela WhatsApp Setup (inicia)
  Contexto da conexão: Administrador informa o telefone e aciona o cadastro.
Pergunta: O administrador tem permissão de WABA Manager na Meta?
Resposta: True

### Nó 1 — Tela WhatsApp Setup
Valida o telefone, abre SDK ou popup e acompanha o status.
Conecta: então → Nó 2 — onboarding/start (start)
  Contexto da conexão: Tela chama o backend autenticado.
Conecta: então → Nó 4 — Embedded Signup Meta (SDK)
  Contexto da conexão: Modo SDK inicia FB.login diretamente na ação do usuário.
Conecta: se → Nó 11 — Status da tentativa (polla status)
  Contexto da conexão: Acompanha o andamento assíncrono.
Conecta: ou → Nó 13 — session_uuid legado (fluxo legado)
  Contexto da conexão: Fallback para chamadas legadas.
Pergunta: Como é tratada a falha de renderização do SDK?
Resposta: Fallbacks com redirect OAuth caso o bloqueador de anúncios impeça a inicialização.

### Nó 2 — onboarding/start
Cria a tentativa, deriva o tenant da sessão e devolve dados públicos.
Conecta: então → Nó 3 — Tentativa + state (registra)
  Contexto da conexão: Tentativa fica vinculada ao tenant e recebe validade.
Conecta: então → Nó 4 — Embedded Signup Meta (abre)
  Contexto da conexão: Backend monta URL ou dados SDK com app, config, callback e state.
Pergunta: Qual a expiração padrão do state gerado?
Resposta: 15 minutos.

### Nó 4 — Embedded Signup Meta
Jornada oficial de autorização e configuração da conta WhatsApp.
Conecta: então → Nó 5 — Retorno SDK ou OAuth (retorna)
  Contexto da conexão: Meta devolve code e metadados da jornada.

### Nó 5 — Retorno SDK ou OAuth
SDK entrega code e IDs por postMessage; redirect entrega code e state no callback.
Conecta: então → Nó 6 — complete ou callback (conclui)
  Contexto da conexão: SDK envia attempt_id e code; redirect chega ao callback OAuth.

### Nó 6 — complete ou callback
Entrada autenticada do SDK ou callback server-side que valida e consome a tentativa.
Conecta: então → Nó 3 — Tentativa + state (valida tentativa)
  Contexto da conexão: Consome a tentativa para impedir reutilização.
Conecta: então → Nó 7 — Reconciliação server-side (inicia reconciliação)
  Contexto da conexão: Garante segurança e chama apis externas.

### Nó 7 — Reconciliação server-side
Troca code, consulta Graph API, valida ownership, aplica retry e idempotência.
Conecta: então → Nó 8 — Graph API Meta (consulta WABA)
  Contexto da conexão: Chama as APIs da Meta para pegar dados do telefone e WABA.
Conecta: então → Nó 9 — Conexão WhatsApp (cria conexão)
  Contexto da conexão: Grava dados e token na base.
Conecta: então → Nó 10 — Assinatura de webhooks (inscreve webhooks)
  Contexto da conexão: Garante recebimento de mensagens e eventos de status.
Pergunta: Política de Retry para APIs Meta:
Resposta: 1

### Nó 8 — Graph API Meta
Troca authorization code por token e descobre WABA e phone_number_id.

### Nó 10 — Assinatura de webhooks
Inscreve a WABA para eventos futuros após a conexão ser confirmada.

### Nó 11 — Status da tentativa
Polling tenant-scoped; pode avançar job pendente e retorna apenas dados seguros.
Conecta: então → Nó 3 — Tentativa + state (lê estado)
  Contexto da conexão: Verifica se backend já terminou.
Conecta: então → Nó 12 — Resultado na tela (renderiza status)
  Contexto da conexão: Atualiza interface com sucesso ou erro.

### Nó 3 — Tentativa + state
Guarda attempt_id, hash do state, telefone, redirect_uri, validade e status.
Pergunta: O state é deletado após o consumo único?
Resposta: True

### Nó 12 — Resultado na tela
Exibe completed, processamento, falha, expiração ou cancelamento.

### Nó 13 — session_uuid legado
Rotas antigas de compatibilidade que fazem persistência direta.
Conecta: então → Nó 9 — Conexão WhatsApp (grava direto)
  Contexto da conexão: Conexão direta na base antiga.

### Nó 9 — Conexão WhatsApp
Upsert de WABA, número e token criptografado, com vínculo ao tenant.


## Nível 1 — Demonstração: perguntas, respostas e loop
Draw: `demo-perguntas-respostas` · papel: architecture
Resumo: Fluxo para validar perguntas respondidas, pendências e retorno ao início

### Nó 1 — Escolher plano
Cliente seleciona a opção de assinatura.
Conecta: então → Nó 2 — Validar pagamento (inicia validação)
  Contexto da conexão: O cliente confirmou a escolha.
Pergunta: Qual plano foi escolhido?
Resposta: 2
Pergunta: Precisa de aprovação manual?
Resposta: False
Pergunta: Qual observação falta confirmar?
Resposta: em aberto

### Nó 2 — Validar pagamento
Confere dados e disponibilidade do meio de pagamento.
Conecta: se → Nó 3 — Aprovar assinatura (pagamento aprovado)
  Contexto da conexão: Ativa somente com autorização confirmada.
Conecta: ou → Nó 4 — Revisar dados (pagamento rejeitado)
  Contexto da conexão: Permite corrigir os dados e repetir a tentativa.
Pergunta: Qual observação deve acompanhar a validação?
Resposta: Usar tokenização e registrar a chave idempotente.

### Nó 3 — Aprovar assinatura
Ativa a assinatura e registra a confirmação.

### Nó 4 — Revisar dados
Corrige dados antes de tentar novamente.
Conecta: então → Nó 1 — Escolher plano (volta ao início)
  Contexto da conexão: Depois da correção, o fluxo retorna para validar a escolha novamente.
Pergunta: Os dados foram corrigidos?
Resposta: em aberto


## Nível 1 — Exemplo inicial do Looper
Draw: `demo-inicial` · papel: architecture
Resumo: Fluxo de demonstração para começar a explorar o viewer

### Nó 1 — Escolher plano
Cliente seleciona a opção de assinatura.
Conecta: então → Nó 2 — Validar pagamento (inicia validação)
  Contexto da conexão: O cliente confirmou a escolha.
Pergunta: Qual plano foi escolhido?
Resposta: 2
Pergunta: Precisa de aprovação manual?
Resposta: False
Pergunta: Qual observação falta confirmar?
Resposta: em aberto

### Nó 2 — Validar pagamento
Confere dados e disponibilidade do meio de pagamento.
Conecta: se → Nó 3 — Aprovar assinatura (pagamento aprovado)
  Contexto da conexão: Ativa somente com autorização confirmada.
Conecta: ou → Nó 4 — Revisar dados (pagamento rejeitado)
  Contexto da conexão: Permite corrigir os dados e repetir a tentativa.
Pergunta: Qual observação deve acompanhar a validação?
Resposta: Usar tokenização e registrar a chave idempotente.

### Nó 3 — Aprovar assinatura
Ativa a assinatura e registra a confirmação.

### Nó 4 — Revisar dados
Corrige dados antes de tentar novamente.
Conecta: então → Nó 1 — Escolher plano (volta ao início)
  Contexto da conexão: Depois da correção, o fluxo retorna para validar a escolha novamente.
Pergunta: Os dados foram corrigidos?
Resposta: em aberto


## Nível 2 — Agentes e responsabilidades do Looper
Draw: `looper-agent-journeys` · papel: journey
Pai: `looper-system-architecture` · nó 11
Resumo: As skills que conduzem o ciclo de especificação orientada por testes

### Nó 1 — Pedido do usuário
Intenção, problema, mudança arquitetural ou necessidade de documentação recebida pelo agente hospedeiro.
Conecta: então → Nó 2 — $setup (então prepara)
  Contexto da conexão: A stack e os gates precisam ser conhecidos antes da execução.
Conecta: se → Nó 3 — $draw-system (se o escopo é um sistema)
  Contexto da conexão: O agente cria ou amplia a arquitetura completa.
Conecta: se → Nó 4 — $draw-feature (se o escopo é uma feature)
  Contexto da conexão: O agente desenha somente o fluxo relacionado.

### Nó 2 — $setup
Descobre a stack, runners, bancos, provedores e configura o Looper sem inventar capacidades. Encaminha para $draw-system quando falta uma raiz de sistema.

### Nó 4 — $draw-feature
Desenha uma feature, fluxo, decisão ou trade-off como JSON navegável, respeitando a árvore do sistema quando existir.
Conecta: então → Nó 6 — $create-tests (então especifica)
  Contexto da conexão: O desenho da feature vira contrato de testes.

### Nó 5 — $draw-improve
Revisa um Draw existente e acrescenta apenas o próximo detalhe arquitetural relevante, preservando intenção, escopo e vínculos.
Conecta: se → Nó 3 — $draw-system (se revelar lacuna sistêmica)
  Contexto da conexão: A melhoria retorna ao contexto arquitetural sem duplicar o filho.
Conecta: então → Nó 6 — $create-tests (então encaminha)
  Contexto da conexão: Após a revisão, o desenho aprovado pode gerar testes.

### Nó 8 — $static-analysis
Implementa ou conecta adapters agnósticos e produz fatos determinísticos sobre símbolos, dependências, complexidade, estrutura e alterações.
Conecta: então → Nó 9 — looper test e looper log (fornece fatos para)
  Contexto da conexão: A análise alimenta rastreabilidade e gates, não inventa associações.

### Nó 10 — Codex
Integração padrão: instala as skills em .agents/skills/ e fornece o AGENTS.md compartilhado para qualquer agente compatível.
Conecta: então → Nó 3 — $draw-system (hospeda)
  Contexto da conexão: Codex disponibiliza as skills ao agente.

### Nó 11 — Claude
Integração de agente que instala as skills em .claude/skills/.
Conecta: então → Nó 3 — $draw-system (hospeda)
  Contexto da conexão: Claude disponibiliza as skills ao agente.

### Nó 12 — Gemini
Integração de agente que instala as skills em .gemini/skills/.
Conecta: então → Nó 3 — $draw-system (hospeda)
  Contexto da conexão: Gemini disponibiliza as skills ao agente.

### Nó 3 — $draw-system
Modela o sistema completo em arquitetura, jornadas, implementação e codebase quando necessário; mantém a árvore hierárquica sem órfãos.
Conecta: então → Nó 6 — $create-tests (então especifica)
  Contexto da conexão: Jornadas implementáveis viram testes executáveis.

### Nó 6 — $create-tests
Transforma jornadas e desenhos em testes executáveis vermelhos, sem alterar código de produção; trata folhas não implementadas como escopo ausente.
Conecta: se → Nó 7 — $implement (se os testes vermelhos foram aprovados)
  Contexto da conexão: A implementação só começa depois da especificação testável.
Conecta: então → Nó 9 — looper test e looper log (então verifica e registra)
  Contexto da conexão: Uma especificação também produz evidência do trabalho realizado.

### Nó 7 — $implement
Implementa o comportamento de produção guiado pelos testes aprovados, preservando contratos, segurança e qualidade estrutural; depois atualiza o Draw correspondente. Detalhes sem mudança de comportamento viram perguntas no nível L2/L3 correto, e mudanças de fluxo também atualizam as conexões dos nós.
Conecta: então → Nó 9 — looper test e looper log (então verifica e registra)
  Contexto da conexão: Toda implementação passa por looper test e looper log.

### Nó 9 — looper test e looper log
Não são agentes: são gates e evidências operacionais que verificam e registram o trabalho conduzido pelas skills. O comando looper draw context organiza todos os níveis, conexões, perguntas, respostas e símbolos em texto para consumo do agente.
Conecta: se → Nó 13 — Entrega documentada (se os gates passam)
  Contexto da conexão: A entrega fica rastreável e pronta para revisão.
Conecta: se → Nó 6 — $create-tests (se algum gate falha)
  Contexto da conexão: O fluxo retorna à especificação ou implementação; não declara sucesso falso.
Símbolo: `looper.cli.draw_context` · arquivo: src/looper/cli.py
Símbolo: `looper.draw.collect_draw_context` · arquivo: src/looper/draw.py
Símbolo: `looper.draw.format_draw_context` · arquivo: src/looper/draw.py

### Nó 13 — Entrega documentada
Estado final esperado: comportamento especificado, implementado quando aplicável, verificado, desenhado e registrado.


## Nível 2 — Jornadas de uso do Looper
Draw: `looper-user-journeys` · papel: journey
Pai: `looper-system-architecture` · nó 8
Resumo: Como agente e desenvolvedor especificam, verificam e documentam o sistema

### Nó 1 — Entrada: projeto e pedido
O usuário abre o agente em um projeto e descreve o que precisa ser especificado ou alterado.
Conecta: então → Nó 2 — Inicializar e instalar skills (então prepara)
  Contexto da conexão: O agente inicializa o projeto quando a estrutura ainda não está disponível.

### Nó 2 — Inicializar e instalar skills
O agente prepara .looper/, instruções e skills para o projeto.
Conecta: então → Nó 3 — Especificar e desenhar (então especifica)
  Contexto da conexão: Skills instaladas orientam a especificação e o desenho.
Draws descendentes: `looper-journey-init`

### Nó 3 — Especificar e desenhar
O pedido vira feature testável ou árvore Draw; o desenho registra caminhos implementados e folhas ausentes.
Conecta: então → Nó 4 — Executar gates (então verifica)
  Contexto da conexão: A implementação ou documentação passa pelos gates do Looper.

### Nó 4 — Executar gates
O agente executa testes, contrato e análise estática antes de declarar conclusão.
Conecta: então → Nó 5 — Registrar evidência (se aprovado, registra)
  Contexto da conexão: Somente após os gates passarem o trabalho é registrado como concluído.
Conecta: se → Nó 7 — Bloqueado ou pendente (se algum gate falhar)
  Contexto da conexão: A tarefa não pode ser declarada concluída.
Draws descendentes: `looper-journey-test`

### Nó 5 — Registrar evidência
O trabalho concluído recebe log com tipo e diff incremental. Após o intervalo configurado de tasks, um agente externo é chamado pelo terminal ou tmux para revisar a entrega; lacunas viram changes no Draw.
Conecta: então → Nó 6 — Revisar no Draw (então revisa)
  Contexto da conexão: A evidência e o desenho ficam disponíveis para revisão humana.
Draws descendentes: `looper-journey-log`

### Nó 6 — Revisar no Draw
O usuário abre o viewer local, navega pela árvore e revisa decisões, perguntas e trade-offs.
Conecta: se → Nó 8 — Entrega rastreável (se não houver pendência)
  Contexto da conexão: A revisão confirma a entrega rastreável.
Draws descendentes: `looper-journey-draw`

### Nó 7 — Bloqueado ou pendente
Falha de teste, símbolo não resolvido ou decisão em aberto permanece visível e impede uma conclusão falsa.
Conecta: então → Nó 3 — Especificar e desenhar (corrige e repete)
  Contexto da conexão: O agente retorna à especificação ou implementação após resolver o bloqueio.

### Nó 8 — Entrega rastreável
A mudança termina com fontes, testes, desenho e evidências coerentes no repositório.


## Nível 3 — Implementação da jornada de documentação visual
Draw: `looper-journey-draw` · papel: implementation
Pai: `looper-user-journeys` · nó 6
Resumo: Como looper draw cria, serve e persiste a árvore de desenhos

### Nó 1 — Receber JSON lógico
O comando draw create recebe o payload sem layout, cores ou HTML.
Conecta: então → Nó 2 — Validar contrato e hierarquia (então valida)
  Contexto da conexão: A criação rejeita payload inválido.
Símbolo: `looper.cli.draw_create`
Dependências: looper.draw.create_draw

### Nó 2 — Validar contrato e hierarquia
Confere IDs, relações, fluxos, perguntas e pai explícito antes de persistir.
Conecta: então → Nó 3 — Persistir desenho e índice (se válido, grava)
  Contexto da conexão: O desenho vira fonte de verdade.

### Nó 3 — Persistir desenho e índice
Grava o JSON em .looper/draws e atualiza o índice.
Conecta: então → Nó 4 — Servir viewer e API local (então serve)
  Contexto da conexão: O viewer lê o estado persistido.
Símbolo: `looper.draw.create_draw`
Dependências: looper.draw.validate_draw_payload, looper.draw.validate_hierarchy_parent

### Nó 4 — Servir viewer e API local
O servidor embutido entrega o viewer e endpoints GET/PUT dos desenhos.
Conecta: então → Nó 5 — Árvore navegável (então permite revisar)
  Contexto da conexão: A árvore é explorada visualmente.
Símbolo: `looper.cli.draw_serve`
Dependências: looper.draw.serve_draw
Símbolo: `looper.draw.serve_draw`
Dependências: looper.draw.create_draw

### Nó 5 — Árvore navegável
O usuário navega da arquitetura às jornadas e implementações, mantendo perguntas e trade-offs visíveis.


## Nível 3 — Implementação da jornada de evidência
Draw: `looper-journey-log` · papel: implementation
Pai: `looper-user-journeys` · nó 5
Resumo: Como looper log registra o trabalho e o diff incremental

### Nó 1 — Receber descrição e tipo
Aceita descrição curta e tipo implementacao, teste, bug ou refactor.
Conecta: então → Nó 2 — Coletar diff e snapshot (então mede)
  Contexto da conexão: A descrição é acompanhada por estatísticas do Git.

### Nó 2 — Coletar diff e snapshot
Compara o estado atual com o checkpoint e salva resumo e snapshot em .looper/runs.
Conecta: então → Nó 3 — Registrar execução (então persiste)
  Contexto da conexão: O registro é salvo nos artefatos internos.

### Nó 3 — Registrar execução
Persiste o registro sem incluir segredos e marca retrabalho quando aplicável.
Conecta: então → Nó 4 — Evidência disponível (então expõe)
  Contexto da conexão: A evidência fica disponível para revisão.

### Nó 4 — Evidência disponível
O usuário pode revisar o log e o diff no painel de runs.


## Nível 3 — Implementação da jornada de inicialização
Draw: `looper-journey-init` · papel: implementation
Pai: `looper-user-journeys` · nó 2
Resumo: Como looper init prepara o projeto para o agente

### Nó 1 — Receber destino com Codex padrão
A CLI valida o diretório e usa Codex como integração padrão, sem perguntar qual agente deve ser usado. Outras integrações só entram quando solicitadas explicitamente por flag.
Conecta: então → Nó 2 — Criar configuração e estado (então cria estado)
  Contexto da conexão: A inicialização materializa a estrutura mínima.

### Nó 2 — Criar configuração e estado
Cria .looper/config.yaml, runs, features, draws e regras de gitignore.
Conecta: então → Nó 3 — Instalar skills e instruções (então instala)
  Contexto da conexão: Skills e instruções são sincronizadas.

### Nó 3 — Instalar skills e instruções
Copia templates atuais e atualiza AGENTS.md; arquivos específicos de outros agentes só são instalados quando a integração é solicitada explicitamente. O AGENTS.md compartilhado instrui todo agente a manter os Draws atualizados.
Conecta: então → Nó 4 — Projeto pronto (então retorna sucesso)
  Contexto da conexão: A CLI informa o projeto inicializado.

### Nó 4 — Projeto pronto
O agente pode usar as skills no projeto inicializado.
Símbolo: `looper.core.init_project`
Dependências: looper.draw.ensure_draw_workspace, looper.core.ensure_gitignore, looper.core.ensure_agent_instructions


## Nível 3 — Implementação da jornada de verificação
Draw: `looper-journey-test` · papel: implementation
Pai: `looper-user-journeys` · nó 4
Resumo: Como looper test transforma configuração em evidência de qualidade

### Nó 1 — Ler perfil e suítes
A execução seleciona suítes, exclusões, perfil e aprovações. Testes de regressão da codebase rodam por padrão; suítes declaradas com type: playwright ficam como not_executed até receberem a flag explícita --playwright.
Conecta: então → Nó 2 — Executar runners e contrato (então executa)
  Contexto da conexão: A configuração determina os comandos.

### Nó 2 — Executar runners e contrato
Subprocessos, contrato e ações aprovadas são executados com captura de resultado. O alias global preserva a regressão como padrão e só inclui E2E Playwright quando solicitado explicitamente.
Conecta: então → Nó 3 — Analisar estática e rastreabilidade (então analisa)
  Contexto da conexão: A análise complementa os runners.

### Nó 3 — Analisar estática e rastreabilidade
O adapter gera símbolos, dependências e métricas; fatos de rastreabilidade são atualizados.
Conecta: se → Nó 4 — Gate aprovado (se todos passarem)
  Contexto da conexão: A execução fica aprovada.
Conecta: se → Nó 5 — Gate bloqueado (se algum falhar)
  Contexto da conexão: O bloqueio é mantido como evidência.
Símbolo: `looper.core.run_tests`
Dependências: looper.static_analysis.run_static_analysis, looper.traceability.refresh_traceability

### Nó 4 — Gate aprovado
Todos os gates passam e a execução pode ser registrada.

### Nó 5 — Gate bloqueado
Falha de teste, contrato, análise ou segurança retorna status bloqueado.
