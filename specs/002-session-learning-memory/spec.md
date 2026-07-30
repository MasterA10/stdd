# Feature Specification: Incremental Session Learning and Agent Handoff

**Feature Branch**: `002-session-learning-memory`  
**Created**: 2026-07-30  
**Status**: Draft  
**Input**: User description: "Implementar o framework learn com memória incremental por sessão, preservando o que foi aprendido em cada dia e permitindo transferir o contexto para outro agente externo ou uma nova sessão do Codex, Claude, Cloud Code ou Antigravity."

## Clarifications

### Session 2026-07-30

- Q: Onde a memória incremental deve ser armazenada? → A: Em um armazenamento
  local por projeto, com registros redigidos versionados no Git; arquivos `.env`,
  credenciais e valores sensíveis nunca podem ser expostos.
- Q: Como os registros redigidos devem entrar no Git? → A: O `learn` grava os
  registros redigidos automaticamente no working tree, mas a pessoa revisa e faz
  o commit manualmente depois do scanner de segurança.
- Q: Qual deve ser o formato principal do handoff? → A: Um pacote de arquivo
  redigido com representação estruturada e uma versão Markdown legível, importado
  explicitamente pelo agente ou pela nova sessão.
- Q: O que acontece com a identidade da sessão ao importar um handoff? → A: A
  importação cria uma nova sessão vinculada à sessão de origem; apenas retomadas de
  compactação preservam a mesma identidade.
- Q: Como remover um registro sensível descoberto depois? → A: Remover o conteúdo
  do working tree, registrar um tombstone redigido e orientar rotação da credencial
  e limpeza do histórico, sem reescrever o Git automaticamente.
- Q: Quem pode gerar as perguntas do quiz e o que o agente principal recebe? → A:
  Um agente ou modelo externo pode receber o contexto redigido da sessão e criar as
  perguntas; o agente principal recebe somente a confirmação de que elas foram
  criadas, sem receber o contexto usado nem o conteúdo das perguntas nesse retorno.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Registrar e revisar o aprendizado da sessão (Priority: P1)

Como pessoa desenvolvedora, quero registrar o que funcionou, o que falhou, as
decisões e o retrabalho de cada sessão para aprender com o processo sem perder o
histórico anterior.

**Why this priority**: A memória incremental é o núcleo do recurso e permite que
as melhorias sejam baseadas em evidências, não apenas em lembranças vagas.

**Independent Test**: Iniciar uma sessão, registrar checkpoints e encerrá-la com
sucesso e falhas simuladas; depois consultar o resumo e confirmar que fatos,
evidências, lições propostas e incertezas estão separados e associados à sessão
correta.

**Acceptance Scenarios**:

1. **Given** uma sessão ativa, **When** ocorre um checkpoint, **Then** o sistema
   registra a sessão, data, branch/worktree, tarefas, arquivos afetados, comandos e
   quality gates sem armazenar segredos ou prompts brutos.
2. **Given** uma sessão encerrada com sucessos e falhas, **When** a pessoa consulta
   o aprendizado, **Then** recebe um resumo curto separado em funcionou, falhou,
   decisões, trade-offs, retrabalho, evidências e próximos experimentos.
3. **Given** uma nova sessão em outro dia, **When** ela registra novos aprendizados,
   **Then** os fatos da sessão anterior permanecem imutáveis e os novos registros
   aparecem como uma sequência posterior, sem sobrescrever a memória existente.
4. **Given** uma sessão compactada e retomada pelo mesmo ou por outro agente,
   **When** o checkpoint é recuperado, **Then** a nova atividade mantém o mesmo
   contexto de origem e deixa explícito o ponto de retomada.

### User Story 2 - Transferir contexto para outro agente ou sessão (Priority: P1)

Como pessoa desenvolvedora, quero exportar uma parte segura e verificável do
aprendizado para outro agente externo, outro host ou uma nova sessão, para continuar
o desenvolvimento sem repetir toda a explicação.

**Why this priority**: A continuidade entre Codex, Claude/Cloud Code, Antigravity e
novas sessões é essencial quando o trabalho muda de ferramenta ou de contexto.

**Independent Test**: Criar uma sessão com decisões, lições e evidências, exportar
um pacote de handoff para cada tipo de destino, importar o pacote em uma nova sessão
e confirmar que o contexto aparece com origem, escopo, integridade e redaction.

**Acceptance Scenarios**:

1. **Given** uma sessão com registros aprovados e propostas pendentes, **When** a
   pessoa solicita um handoff, **Then** o sistema permite escolher escopo, destino
   e inclusão de propostas, exibindo o que será transferido antes da exportação.
2. **Given** um handoff exportado, **When** outro agente ou uma nova sessão o
   importa, **Then** recebe contexto estruturado com sessão de origem, timestamp,
   branch/worktree, evidências, decisões, lições e tarefas abertas.
3. **Given** um pacote alterado ou incompatível, **When** ele é importado, **Then**
   a operação é recusada ou marcada como conflito sem misturar fatos silenciosamente.
4. **Given** registros que contenham uma credencial, prompt sensível ou dado
   pessoal, **When** o handoff é preparado, **Then** o conteúdo é redigido e o
   relatório informa apenas a existência, o tipo e a ação necessária.
5. **Given** um agente que não possui integração nativa, **When** a pessoa exporta
   o handoff, **Then** o sistema oferece um formato interoperável legível e informa
   quais eventos ou metadados não puderam ser reconectados automaticamente.

### User Story 3 - Avaliar conhecimento da codebase (Priority: P2)

Como pessoa desenvolvedora, quero responder perguntas curtas sobre arquitetura,
modularização, boas práticas, trade-offs e regras de negócio para verificar se
realmente entendi o código que estou alterando.

**Why this priority**: A avaliação transforma o aprendizado em prática verificável
e ajuda a identificar áreas que ainda exigem estudo antes de mudanças maiores.

**Independent Test**: Gerar perguntas para uma codebase de referência, executar a
prova, responder corretamente e incorretamente, e confirmar que o resultado mostra
categorias, explicações, fontes e itens que precisam de revisão.

**Acceptance Scenarios**:

1. **Given** uma codebase com símbolos, testes, documentação e decisões, **When** a
   pessoa gera um quiz, **Then** recebe perguntas de múltipla escolha curtas,
   categorizadas e vinculadas às fontes de conhecimento correspondentes.
2. **Given** uma pergunta vinculada a uma função, regra ou decisão, **When** essa
   fonte é alterada, **Then** a pergunta é marcada para revisão e não é tratada como
   conhecimento atual sem validação.
3. **Given** uma prova em andamento, **When** a pessoa a conclui, **Then** o
   resultado apresenta pontuação por categoria, respostas, explicações e fontes,
   sem alterar código, configuração de qualidade ou instruções do projeto.
4. **Given** conhecimento não confirmado, **When** a pessoa encerra a prova, **Then**
   o resultado pode propor uma lição curta, mas não a promove automaticamente para
   uma regra permanente.
5. **Given** uma sessão com contexto redigido, **When** a geração é delegada a um
   comando local de Codex, Claude, Cloud, Antigravity ou destino compatível, **Then** esse comando cria e armazena as perguntas, e o
   agente principal recebe somente a confirmação de criação, sem o contexto de
   geração ou o conteúdo das perguntas no retorno.

### Edge Cases

- A sessão termina abruptamente: o último checkpoint disponível é recuperável e é
  marcado como incompleto, sem ser apresentado como encerramento confirmado.
- O host não fornece eventos de compactação, retomada ou encerramento: o sistema
  registra cobertura parcial e usa checkpoints explícitos, comandos e commits como
  evidência disponível.
- Duas sessões tentam atualizar a mesma memória: cada fato mantém sua sessão de
  origem; conflitos são apresentados para revisão e não são mesclados em silêncio.
- O relógio local muda ou a sessão atravessa a meia-noite: a ordenação usa um
  timestamp normalizado e mantém também a data local informada ao usuário.
- O handoff é importado em outra branch, worktree ou versão do projeto: o sistema
  mantém o contexto, sinaliza divergências e não afirma que os símbolos ainda são
  válidos.
- Não há registros aprovados para exportar: o sistema informa que o handoff está
  vazio e não cria um pacote enganoso.
- Um registro sensível é descoberto depois de salvo: o conteúdo é removido do
  working tree, um tombstone sem o valor é criado, a credencial é marcada para
  rotação e a limpeza do histórico é orientada sem alteração automática do Git.
- Uma pergunta perde sua fonte ou aponta para um símbolo alterado: ela fica
  pendente de revisão e não entra como resposta válida até ser atualizada.
- O comando local está indisponível ou falha parcialmente: o quiz registra a
  tentativa, informa falha ou cobertura parcial e o agente principal recebe apenas
  esse status, sem receber contexto sensível ou perguntas incompletas no retorno.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST oferecer um recurso `learn` opcional que possa ser
  ativado ou desativado sem bloquear inicialização, testes, quality gates, commits,
  pushes ou CI.
- **FR-002**: O sistema MUST criar um identificador estável para cada sessão e
  registrar início, checkpoint, compactação, retomada e encerramento quando esses
  eventos estiverem disponíveis.
- **FR-003**: Cada registro MUST manter sessão de origem, data local, timestamp
  normalizado, agente/host, branch, worktree, commit-base, tarefas, arquivos e
  símbolos afetados, comandos e gates relacionados quando conhecidos.
- **FR-004**: O sistema MUST armazenar fatos de sessões anteriores de forma
  incremental e append-only; novos aprendizados não podem sobrescrever fatos
  anteriores.
- **FR-004a**: A memória persistente MUST pertencer ao projeto e seus registros
  redigidos MUST poder ser versionados no Git, mas nenhum arquivo `.env`, credencial,
  prompt bruto ou valor sensível pode ser incluído na memória, commit ou handoff.
- **FR-004b**: O `learn` MUST poder gravar registros redigidos automaticamente no
  working tree, mas MUST NOT criar commits automáticos; a pessoa deve revisar e
  confirmar o conteúdo antes de versioná-lo.
- **FR-005**: O sistema MUST separar fatos observados, inferências, decisões,
  trade-offs, retrabalho, lições propostas e lições aprovadas.
- **FR-006**: O sistema MUST gerar resumos curtos por sessão e resumos acumulados,
  preservando links para as evidências que justificam cada afirmação.
- **FR-007**: O sistema MUST detectar sinais de retrabalho, como alterações
  repetidas no mesmo símbolo, revert/reaplicação, tarefas reabertas e tentativas
  após falhas, informando confiança e evidências sem atribuir culpa.
- **FR-008**: O sistema MUST permitir revisão humana de uma lição antes de promovê-la
  para instrução permanente, regra de processo, baseline ou configuração de
  qualidade.
- **FR-009**: O sistema MUST permitir selecionar sessões, categorias, tarefas,
  arquivos, símbolos e status ao preparar um handoff.
- **FR-010**: O sistema MUST permitir exportar e importar handoffs para agentes
  suportados, hosts externos e novas sessões, incluindo um formato interoperável
  para destinos sem integração nativa.
- **FR-010a**: O pacote de handoff MUST conter uma representação estruturada e uma
  versão Markdown legível, com o mesmo escopo, redaction, origem, destino,
  integridade e cobertura de eventos.
- **FR-010b**: A importação de um handoff MUST criar uma nova sessão com referência
  à origem; eventos de compactação e retomada MUST permanecer na mesma sessão
  original quando a continuidade for confirmada.
- **FR-011**: Cada handoff MUST informar origem, destino, versão do formato,
  escopo, integridade, data de exportação e cobertura de eventos, e MUST rejeitar
  ou marcar alterações incompatíveis.
- **FR-012**: O sistema MUST carregar a cadeia de instruções aplicável ao escopo
  antes de preparar ou importar contexto para outro agente; conflitos não resolvidos
  devem interromper a operação.
- **FR-013**: O sistema MUST redigir segredos, prompts brutos, dados pessoais e
  valores sensíveis antes de persistir, exportar, importar ou exibir aprendizado.
- **FR-013a**: Quando um valor sensível for descoberto após a persistência, o
  sistema MUST remover o conteúdo do working tree, criar um tombstone redigido,
  orientar rotação da credencial e apresentar instruções para limpeza do histórico;
  não deve reescrever o Git automaticamente.
- **FR-014**: O sistema MUST informar quando a cobertura de eventos for parcial e
  quais evidências alternativas foram usadas para reconstruir uma sessão.
- **FR-015**: O sistema MUST gerar perguntas curtas de múltipla escolha sobre
  arquitetura, modularização, práticas, decisões, trade-offs, regras de negócio,
  testes e relações entre módulos.
- **FR-015a**: A geração de perguntas MUST poder ser delegada a um comando local
  autorizado, incluindo Codex, Claude, Cloud, Antigravity ou destinos compatíveis
  futuros, usando como entrada somente um pacote de contexto previamente redigido e
  autorizado. O core MUST NOT require a provider HTTP/API.
- **FR-015b**: O agente principal que iniciar uma geração externa MUST receber
  somente uma confirmação mínima de criação ou falha e um identificador opaco do
  job; não deve receber nesse retorno o contexto enviado, o prompt de geração ou o
  conteúdo das perguntas.
- **FR-015c**: As perguntas geradas MUST ficar disponíveis no armazenamento do
  quiz para consulta pela pessoa ou pelo comando de prova, independentemente de o
  agente principal ter recebido seu conteúdo no retorno da delegação.
- **FR-016**: Cada pergunta MUST estar associada a uma ou mais fontes estáveis,
  como função, classe, módulo, teste, contrato, regra, documento ou decisão, com
  explicação e resposta correta versionadas.
- **FR-017**: O sistema MUST marcar perguntas para revisão quando uma fonte,
  regra de negócio, contrato ou decisão associada for alterada, removida ou ficar
  incompatível com a branch atual.
- **FR-018**: O sistema MUST registrar resultados de provas por sessão e categoria,
  sem alterar automaticamente código, instruções permanentes ou políticas.
- **FR-019**: Os comandos de learn e quiz MUST disponibilizar resultados humanos e
  estruturados, incluindo status, evidências, redaction, ações e cobertura.
- **FR-020**: O sistema MUST preservar a separação por sessão e data, permitindo
  consultar o aprendizado de hoje, de uma sessão específica ou do histórico
  acumulado sem misturar cronologias.

### Quality, Governance & Operational Constraints *(mandatory for code changes)*

- **QG-001**: A implementação MUST obedecer a todos os arquivos Markdown de
  instrução aplicáveis, registrar a cadeia carregada e interromper conflitos não
  resolvidos.
- **QG-002**: O armazenamento de aprendizado MUST ser append-only para fatos de
  sessão, com correções representadas como novos eventos ou revisões rastreáveis.
- **QG-003**: O recurso MUST ser opt-in e não bloqueante quando desabilitado ou
  quando um host não oferecer hooks de sessão.
- **QG-004**: Toda lição promovida MUST possuir revisão, origem, evidência, escopo
  e condição de reavaliação.
- **QG-005**: Handoffs MUST possuir redaction, integridade verificável e escopo
  explícito antes de atravessar a fronteira de um agente ou sessão.
- **QG-005c**: A representação estruturada deve ser a fonte de importação; a versão
  Markdown é uma visualização equivalente e não pode ampliar o escopo transferido.
- **QG-005d**: A identidade da sessão de origem MUST permanecer imutável; relações
  entre sessões importadas devem ser registradas como vínculos explícitos.
- **QG-005e**: Tombstones de segurança MUST conter somente tipo, localização,
  fingerprint não reversível, data e ação recomendada, nunca o valor removido.
- **QG-005a**: Antes de persistir ou versionar qualquer registro de aprendizado, o
  scanner de segurança MUST verificar o conteúdo e bloquear a operação quando
  detectar `.env`, credenciais ou valores sensíveis.
- **QG-005b**: A gravação automática de aprendizado MUST ser separada da criação
  de commits e MUST exibir os arquivos alterados para revisão humana.
- **QG-006**: Perguntas e respostas MUST ser curtas, revisáveis e invalidadas por
  mudança de fonte; resultados educacionais não são quality gates nem critério
  automático de paralelização.
- **QG-006a**: Contexto enviado a um comando gerador MUST passar por redaction e
  escopo explícito; a resposta de orquestração ao agente principal MUST conter
  somente status e identificador opaco, nunca contexto, prompt ou perguntas.
- **QG-007**: Mudanças comportamentais MUST ter testes reproduzíveis, e os gates
  existentes de duplicação, funções extensas, classes Deus e segredos continuam
  obrigatórios para código alterado.

## Key Entities *(include if feature involves data)*

- **Session**: Unidade temporal de trabalho com identificador, agente/host, branch,
  worktree, estado, eventos e cobertura de hooks.
- **Learning Event**: Fato append-only observado em uma sessão, com tipo, timestamp,
  dados redigidos e referências de evidência.
- **Lesson**: Conhecimento curto proposto ou aprovado, com origem, confiança,
  escopo, revisão e condição de expiração.
- **Handoff Package**: Contexto selecionado para outro agente ou sessão, com origem,
  destino, versão, checksum, escopo, redaction e cobertura.
- **Knowledge Question**: Pergunta de múltipla escolha vinculada a fontes da
  codebase, resposta, explicação, categoria e estado de revisão.
- **Quiz Attempt**: Resultado de uma prova em uma sessão, com respostas, pontuação,
  categorias, fontes consultadas e propostas de aprendizado.
- **Question Generation Job**: Solicitação delegada para gerar perguntas, com
  sessão de origem, escopo autorizado, destino, status, identificador opaco,
  cobertura e referências das perguntas armazenadas.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Uma pessoa consegue consultar o resumo de uma sessão encerrada em até
  10 segundos e identificar pelo menos um sucesso, uma dificuldade, uma decisão e
  um próximo experimento quando esses dados existirem.
- **SC-002**: Em testes de encerramento normal, compactação e retomada, 100% dos
  eventos confirmados permanecem associados à sessão correta e nenhum fato anterior
  é sobrescrito.
- **SC-003**: Um handoff selecionado pode ser exportado e importado em até 30
  segundos, preservando 100% das decisões, tarefas abertas e evidências incluídas.
- **SC-004**: 100% dos handoffs de teste com valores sensíveis removem os valores
  antes da persistência, exibição e transferência, sem reduzir a capacidade de
  identificar a ação de correção.
- **SC-005**: Pelo menos 95% dos registros de sessão conhecidos são reconstruídos
  com agente/host, branch, worktree, timestamp e evidência de origem; ausências são
  marcadas como cobertura parcial.
- **SC-006**: Pelo menos 90% das perguntas geradas para a codebase de referência
  possuem fonte, categoria, resposta correta e explicação revisável.
- **SC-007**: Após a alteração de uma fonte associada, 100% das perguntas de teste
  relacionadas são marcadas para revisão antes de uma nova prova ser considerada
  atualizada.
- **SC-008**: Em avaliação com perguntas conhecidas, a pessoa consegue visualizar
  pontuação por categoria e revisar respostas incorretas sem modificar arquivos de
  aplicação, instruções ou políticas.
- **SC-009**: Quando o recurso está desativado ou o host não fornece hooks, os
  comandos de desenvolvimento mantêm seus resultados e códigos de saída normais,
  informando apenas a cobertura de aprendizado reduzida.
- **SC-010**: Em 100% das delegações de geração de quiz de teste, o agente principal
  recebe somente confirmação e identificador opaco, enquanto o contexto enviado e
  o conteúdo das perguntas permanecem fora do retorno de orquestração.

## Assumptions

- O aprendizado é opcional e inicialmente acionado por comandos, checkpoints e
  integrações disponíveis; ausência de hooks do host não impede seu uso básico.
- A memória de sessões pertence ao projeto, pode ser versionada em forma redigida
  e pode ser consultada por branch, worktree, data e identificador de sessão,
  respeitando permissões locais.
- O `learn` pode atualizar o working tree durante uma sessão, mas não cria commits
  automaticamente; o fluxo de revisão e commit permanece sob controle da pessoa.
- O formato interoperável do handoff é legível por pessoas e máquinas e não exige
  que o agente de destino instale o framework completo.
- O pacote de handoff é o meio principal de transferência; clipboard, stdout e
  integrações nativas podem ser conveniências futuras, mas não substituem o pacote.
- Importar contexto sempre inicia uma nova sessão vinculada; somente eventos de
  compactação e retomada representam continuidade da mesma sessão.
- Um handoff inclui por padrão fatos e lições aprovadas; propostas pendentes exigem
  seleção explícita e são claramente rotuladas.
- A data local serve para consulta humana, enquanto timestamps normalizados e
  identificadores servem para ordenar eventos entre máquinas e fusos horários.
- A primeira versão reconhece Codex, Claude/Cloud Code e Antigravity como destinos
  nomeados, mas mantém um destino genérico para novas sessões e agentes externos.
- A promoção de lições para `AGENTS.md`, `CLAUDE.md`, regras de qualidade ou outros
  arquivos permanentes nunca é automática.
- Agentes ou modelos externos podem gerar perguntas usando contexto redigido e
  autorizado; o agente principal não precisa conhecer o conteúdo gerado para
  iniciar ou acompanhar a prova.
- A remoção de dados sensíveis não reescreve o histórico Git automaticamente; a
  pessoa responsável decide a rotação e a limpeza histórica após receber a orientação.
- Quiz e aprendizado não são gates de segurança, qualidade, commit, CI ou decisão
  automática de paralelização.
