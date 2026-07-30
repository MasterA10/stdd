# Feature Specification: CLI Framework Foundation

**Feature Branch**: `001-cli-framework-bootstrap`  
**Created**: 2026-07-30  
**Status**: Draft  
**Input**: User description: "Criar a especificação do framework CLI-first, semelhante ao GitHub Spec Kit, com CLI, instalação, scripts determinísticos, adaptadores, agentes e quality gates"

## Clarifications

### Session 2026-07-30

- Q: Qual deve ser o escopo da primeira entrega? → A: Fundação: CLI, inicialização,
  instalação, detecção, scripts e quality gates básicos.
- Q: Em quais sistemas o CLI deve funcionar na primeira entrega? → A: macOS e Linux.
- Q: Como a pessoa deve instalar o CLI na primeira versão? → D: Instalação
  persistente por release/pacote e execução temporária por bootstrap direto do GitHub.
- Q: Qual runtime deve ser usada pelo núcleo do CLI na primeira versão? → A: Python
  com uv.
- Q: Qual integração de agente deve fazer parte da primeira entrega? → B: Codex CLI
  e Claude Code.
- Q: Como o `framework check` deve tratar violações de qualidade? → C: Política
  configurável por perfil e baseline.
- Q: Como o scanner deve agir diante de credenciais? → C3: Bloquear commits com
  arquivos `.env` ou credenciais detectadas.
- Q: Como o CLI deve escolher entre Codex CLI e Claude Code durante a instalação? →
  A: Sempre perguntar interativamente.
- Q: O Git deve ser obrigatório para o funcionamento completo do framework? → A: Git
  obrigatório para recursos completos.
- Q: Qual formato o CLI deve oferecer para resultados de testes, análises e quality
  gates? → A: Texto humano e JSON estruturado.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Inicializar e entender um projeto (Priority: P1)

Como pessoa responsável por um projeto novo ou existente, quero instalar e inicializar
o framework pelo CLI para obter uma visão confirmável da codebase e uma configuração
inicial utilizável.

**Why this priority**: Sem uma inicialização confiável, os demais fluxos não têm
contexto suficiente para operar com segurança.

**Independent Test**: Executar a inicialização em um projeto vazio e em uma codebase
existente, revisar o diagnóstico apresentado, corrigir uma detecção e confirmar a
configuração sem alterar o código da aplicação.

**Acceptance Scenarios**:

1. **Given** um diretório vazio, **When** a pessoa executa a inicialização, **Then**
   o CLI solicita o contexto mínimo e cria uma configuração validável.
2. **Given** uma codebase existente, **When** a pessoa executa a inicialização no
   diretório, **Then** o CLI identifica linguagens, frameworks, testes, dados e
   infraestrutura detectáveis e apresenta um resumo antes de salvá-lo.
3. **Given** uma detecção incorreta, **When** a pessoa edita a proposta, **Then** a
   configuração salva reflete a correção sem tratar a detecção automática como
   verdade absoluta.
4. **Given** uma pessoa que ainda não possui o CLI instalado, **When** ela usa a
   instalação persistente ou o bootstrap temporário, **Then** consegue inicializar
   um projeto sem copiar manualmente os arquivos do framework.
5. **Given** mais de uma integração de agente disponível, **When** a instalação é
   executada em terminal interativo, **Then** o CLI solicita uma escolha explícita.

### User Story 2 - Executar o fluxo de desenvolvimento pelo CLI (Priority: P1)

Como pessoa desenvolvedora, quero usar uma interface única para executar testes,
análises, sincronizações, revisões e verificações, sem precisar memorizar comandos
específicos de cada tecnologia.

**Why this priority**: O valor central do framework é transformar ferramentas
heterogêneas em um fluxo previsível, reproduzível e verificável.

**Independent Test**: Configurar dois conjuntos de testes e duas análises em um
projeto de teste, executar o comando unificado e verificar que o CLI consolida os
resultados, informa os comandos usados e retorna um status coerente.

**Acceptance Scenarios**:

1. **Given** uma configuração com múltiplos conjuntos de testes, **When** a pessoa
   executa o comando unificado, **Then** todos os conjuntos aplicáveis são
   executados e o resultado identifica sucesso, falha ou indisponibilidade.
2. **Given** uma alteração de código, **When** a pessoa executa a verificação,
   **Then** o CLI apresenta arquivos, linhas, regras, métricas, severidade e ações
   recomendadas para cada achado.
3. **Given** um comando que pode alterar arquivos, **When** a pessoa consulta sua
   ajuda ou o executa, **Then** o CLI informa natureza, permissões, pré-condições e
   arquivos afetados.

### User Story 3 - Instalar agentes respeitando as instruções do projeto (Priority: P1)

Como pessoa desenvolvedora que utiliza agentes diferentes, quero instalar comandos
e instruções compatíveis com meu agente sem duplicar a fonte de verdade e sem que o
agente principal ignore as regras Markdown do repositório.

**Why this priority**: A automação só é confiável quando todos os agentes recebem o
mesmo contexto e obedecem as regras aplicáveis ao local em que atuam.

**Independent Test**: Instalar as instruções em um projeto com `AGENTS.md` e uma
instrução mais específica em um subdiretório, executar uma tarefa de leitura e
verificar que a cadeia carregada, a precedência e os arquivos modificados são
registrados.

**Acceptance Scenarios**:

1. **Given** um projeto com instruções Markdown aplicáveis, **When** um comando
   agentic é iniciado, **Then** a cadeia de instruções é carregada antes da análise
   e fica registrada no resultado.
2. **Given** instruções gerais e específicas sem conflito, **When** o agente opera
   em um subdiretório, **Then** a instrução mais específica é aplicada nesse escopo.
3. **Given** instruções conflitantes, **When** o conflito é detectado, **Then** o
   fluxo é interrompido e o conflito é apresentado sem alteração silenciosa.
4. **Given** mais de um formato de agente instalado, **When** a pessoa atualiza os
   comandos, **Then** as projeções continuam rastreáveis à fonte canônica.

### Edge Cases

- O projeto não possui Git: a inicialização informa o modo degradado e mantém os
  recursos locais que não dependem de histórico ou remoto.
- A detecção identifica tecnologias conflitantes ou um monorepo: o CLI apresenta
  as alternativas por aplicação e exige confirmação antes de salvar.
- Uma análise encontra um segredo: o valor nunca aparece no terminal, relatório,
  ou contexto entregue ao agente.
- Um comando falha no meio do fluxo: o resultado informa o último estágio concluído,
  arquivos tocados e uma forma segura de retomar.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O CLI MUST inicializar projetos novos, analisar codebases existentes e
  aceitar uma descrição externa de requisitos para propor uma configuração.
- **FR-002**: O sistema MUST detectar, quando possível, linguagens, versões,
  frameworks, ferramentas de teste, armazenamento, infraestrutura e estrutura de
  monorepo, permitindo correção humana antes de salvar.
- **FR-003**: O sistema MUST manter uma configuração do projeto com perfil,
  aplicações, adaptadores, comandos, políticas de documentação, segurança e
  extensões futuras.
- **FR-004**: O sistema MUST instalar e atualizar comandos, prompts, scripts e
  instruções no formato do agente escolhido, preservando uma fonte canônica e
  projeções rastreáveis.
- **FR-005**: O CLI MUST oferecer uma execução unificada de testes, diagnósticos,
  revisões, sincronizações e quality gates, consolidando saída humana e estruturada.
- **FR-006**: O sistema MUST executar análise estática adequada à stack para detectar
  duplicação, funções extensas, complexidade excessiva, classes Deus, tipos não
  resolvidos e inconsistências do índice.
- **FR-007**: O sistema MUST verificar arquivos de ambiente, regras efetivas de
  ignore, arquivos sensíveis rastreados, segredos hardcoded, diffs enviados ao
  remoto e histórico Git, redigindo qualquer valor secreto. O sistema MUST bloquear
  commits, pushes ou CI quando um arquivo `.env` não permitido ou uma credencial
  for detectado no conteúdo que será versionado.
- **FR-008**: Todo comando MUST declarar natureza, permissões, pré-condições e
  arquivos que pode modificar; alterações não podem ser silenciosas.
- **FR-009**: O agente principal e agentes delegados MUST carregar as instruções
  Markdown aplicáveis, registrar a cadeia e interromper em conflitos não resolvidos.
- **FR-010**: Mudanças de comportamento MUST seguir fluxo orientado por testes, e
  testes aprovados MUST permanecer protegidos contra alterações não autorizadas.
- **FR-011**: O sistema MUST permitir adoção progressiva em código legado, aplicando
  política configurável por perfil: violações novas ou modificadas podem bloquear,
  enquanto achados baselineados geram alerta e permanecem rastreáveis.
- **FR-012**: A primeira entrega MUST funcionar em macOS e Linux e MUST informar de
  forma explícita quando for executada em uma plataforma ainda não suportada.
- **FR-013**: O CLI MUST oferecer uma instalação persistente a partir de uma versão
  publicada e uma execução temporária por bootstrap direto de uma release no
  GitHub, com verificação da versão utilizada.
- **FR-014**: A primeira entrega MUST instalar projeções compatíveis com Codex CLI e
  Claude Code a partir de uma fonte canônica, registrando a origem e a versão de
  cada arquivo projetado.
- **FR-015**: O sistema MUST permitir apenas arquivos de exemplo de ambiente com
  valores fictícios, como `.env.example`, e MUST rejeitar valores reais mesmo nesses
  arquivos.
- **FR-016**: A instalação interativa MUST solicitar explicitamente a integração do
  agente; execuções não interativas MUST exigir uma seleção explícita e falhar com
  orientação clara quando ela não for fornecida.
- **FR-017**: O sistema MUST exigir Git para histórico, diffs, rastreabilidade,
  bloqueio de commits e secret scanning completos, mas MUST permitir inicialização
  básica sem Git e informar quais recursos ficaram degradados.
- **FR-018**: Resultados de testes, análises e quality gates MUST estar disponíveis
  em formato legível para pessoas e em JSON estruturado para CI, scripts e
  integrações.

### Quality, Governance & Operational Constraints *(mandatory for code changes)*

- **QG-001**: A implementação MUST obedecer à constituição e a todos os arquivos
  Markdown de instrução aplicáveis ao diretório de trabalho.
- **QG-002**: Operações previsíveis MUST usar scripts ou ferramentas determinísticas
  antes de agentes; comandos agentic MUST declarar escopo e permissões.
- **QG-003**: O quality gate MUST produzir achados acionáveis e executar localmente
  e no CI, sem exibir segredos.
- **QG-004**: Baselines e exceções de qualidade MUST possuir justificativa, escopo,
  evidência e condição de revisão.
- **QG-005**: A fundação MUST manter pontos de extensão para módulos futuros sem
  exigir sua implementação ou ativação nesta entrega.
- **QG-006**: O bloqueio de segurança MUST ocorrer antes de commit, push ou CI e
  MUST redigir o valor detectado em toda saída humana ou estruturada.

### Key Entities *(include if feature involves data)*

- **Project Profile**: Mapa validado de aplicações, tecnologias, comandos,
  integrações, políticas, baselines e recursos opcionais.
- **Adapter**: Conhecimento específico usado para detectar, analisar e operar uma
  tecnologia ou ferramenta.
- **Deterministic Script**: Operação reproduzível com entradas, permissões, saída e
  código de retorno conhecidos.
- **Instruction Chain**: Conjunto ordenado de instruções Markdown aplicáveis ao
  agente e ao diretório de uma operação.
- **Quality Finding**: Achado de análise com regra, severidade, localização, métrica
  e ação recomendada.
- **Security Finding**: Indício redigido de arquivo, credencial ou segredo exposto,
  identificado por tipo e fingerprint não reversível.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Uma pessoa consegue inicializar um projeto novo ou existente e revisar
  a configuração proposta em até 5 minutos, sem editar arquivos de código.
- **SC-002**: Em projetos de referência, pelo menos 95% dos artefatos de stack,
  testes e scripts previamente conhecidos são apresentados no diagnóstico para
  confirmação ou correção.
- **SC-003**: Toda execução de quality gate retorna status de processo e achados
  localizáveis por arquivo, linha, regra e severidade, sem revelar valores secretos.
- **SC-004**: Em uma alteração de código, 100% dos arquivos novos ou modificados
  entram no escopo de análise estática e de segurança antes da conclusão do gate.
- **SC-005**: Uma instalação ou atualização do framework pode ser validada por um
  diagnóstico reproduzível sem exigir cópia manual de comandos entre agentes.
- **SC-006**: O fluxo de qualidade identifica e localiza 100% dos arquivos novos ou
  modificados incluídos nos projetos de referência.
- **SC-007**: Uma pessoa consegue instalar uma versão persistente ou executar o
  bootstrap temporário e iniciar um projeto de referência sem copiar arquivos
  manualmente.
- **SC-008**: Em um projeto com baseline legado, uma nova violação é distinguida de
  um achado antigo e recebe a severidade definida pelo perfil, sem perder sua
  localização ou evidência.
- **SC-009**: Em todos os projetos de referência, um `.env` rastreado ou uma
  credencial detectada no conteúdo a ser commitado impede o commit e informa uma
  ação de correção sem revelar o valor.
- **SC-010**: Uma instalação interativa com duas integrações disponíveis sempre
  apresenta a escolha antes de criar projeções específicas de agente.
- **SC-011**: Em um projeto sem Git, a inicialização básica informa explicitamente o
  modo degradado e não apresenta os recursos dependentes de histórico como
  concluídos.
- **SC-012**: Cada execução de teste ou quality gate de um projeto de referência
  produz uma saída humana e uma representação JSON equivalente, com o mesmo status
  e os mesmos achados.

## Assumptions

- O projeto pode usar Git local; quando Git ou histórico remoto não estiverem
  disponíveis, o sistema informa claramente quais verificações ficaram degradadas.
- A pessoa responsável valida as detecções de inicialização antes de salvá-las.
- O perfil define limiares de qualidade, baselines e políticas de exceção.
- O aprendizado, o quiz, hooks de sessão e suporte à paralelização serão definidos
  em especificações posteriores e não fazem parte da primeira entrega.
- O índice local é mantido pelo framework e oferece uma fonte de relações persistente;
  o formato de armazenamento e exportação será definido no plano.
- A fundação deve preservar pontos de integração para futuros hooks e módulos de
  conhecimento sem ativá-los nesta entrega.
- A primeira entrega terá macOS e Linux como plataformas suportadas; Windows fica
  fora do escopo até uma especificação de compatibilidade própria.
- As releases do CLI serão identificáveis e verificáveis; o uso temporário não
  altera a instalação persistente da pessoa.
- Arquivos `.env` reais e credenciais nunca são considerados conteúdo aceitável para
  versionamento; apenas exemplos com placeholders fictícios podem ser versionados.
- O núcleo do CLI será distribuído como uma ferramenta Python gerenciada por uv;
  scripts e adaptadores de outras stacks podem usar seus runtimes nativos.
- Codex CLI e Claude Code são os primeiros agentes suportados; outros agentes serão
  adicionados por especificações de integração posteriores.
