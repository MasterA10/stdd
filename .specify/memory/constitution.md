<!--
Sync Impact Report
- Version change: 1.2.0 -> 1.3.0
- Modified principles: VI. Evidence-Based Learning Loop clarified as a learning-only
  signal, not a parallelization criterion
- Added sections: Knowledge Assessment
- Removed sections: none
- Artifacts requiring updates: ✅ plan.md; ✅ .specify/templates/plan-template.md;
  ✅ .specify/templates/spec-template.md; ✅ .specify/templates/tasks-template.md;
  ✅ AGENTS.md; ⚠ .specify/templates/commands/ (directory absent)
- Follow-up TODOs: implement the scanner, learning/session hooks and quiz script in
  the core CLI and their stack adapters
-->

# Framework CLI-First Constitution

## Core Principles

### I. CLI-Orchestrated, Script-First

O CLI é a interface principal do framework e MUST orquestrar configuração,
adaptadores, scripts, agentes, testes, relatórios, Git e quality gates. Operações
previsíveis MUST ser resolvidas por scripts determinísticos, ferramentas nativas ou
analisadores AST antes de recorrer a um agente de IA. Cada comando MUST declarar sua
natureza, permissões e arquivos que pode modificar. O framework MUST escolher o
adaptador e o script compatíveis com a stack e o sistema operacional detectados, sem
impor uma runtime desnecessária ao projeto.

Rationale: comportamento determinístico reduz custo, latência e risco de alterações
imprevisíveis, mantendo o fluxo reproduzível no terminal e no CI.

### II. Instruction-Chain Compliance

O agente principal MUST carregar e cumprir todos os documentos Markdown de instrução
aplicáveis antes de planejar, analisar ou modificar qualquer arquivo. Isso inclui o
`AGENTS.md` e arquivos equivalentes reconhecidos pelo agente, como `CLAUDE.md`,
`GEMINI.md`, `CLOUD.md` ou instruções locais de subdiretórios. A instrução mais
específica prevalece sobre a mais ampla quando não houver conflito com esta
constituição. Agentes delegados MUST receber a mesma cadeia de instruções e não podem
contorná-la. Em caso de conflito, o fluxo MUST parar e registrar o conflito; nenhuma
regra aplicável pode ser ignorada silenciosamente. Cada execução agentic MUST
registrar quais arquivos de instrução foram carregados.

Rationale: a automação só é segura quando o agente respeita o contexto e as regras
do repositório em que está operando.

### III. Test-First and Protected Approved Behavior

Toda mudança de comportamento MUST possuir um teste reproduzível antes da
implementação, com falha confirmada pelo motivo esperado. Em perfis MVP e Produto,
testes de negócio aprovados MUST ser tratados como contratos protegidos e não podem
ser alterados por um agente para fazer a implementação passar. Se o teste estiver
incorreto ou impossível de satisfazer, o agente MUST interromper e apresentar o
conflito. Os testes, explicações geradas e resultados relevantes MUST ser
rastreáveis no índice e no histórico do framework.

Rationale: o comportamento aprovado é a especificação executável e protege contra
regressões durante alterações assistidas por agentes.

### IV. Deterministic Static Quality Gates

Toda alteração de código MUST passar por análise estática adequada à linguagem,
preferencialmente baseada em AST e no índice de símbolos. O `framework check` MUST
verificar, no mínimo, duplicação textual ou estrutural, tamanho e complexidade de
funções/métodos, sinais de classes Deus, tipos não resolvidos, símbolos públicos
sem descrição quando exigido pelo perfil e inconsistências do índice.

O analisador MUST emitir arquivo, linha, métrica, limiar, severidade e regra para
cada achado. Como baseline inicial, um bloco repetido de seis ou mais instruções
lógicas em dois locais, uma função com mais de 50 linhas lógicas ou complexidade
cognitiva acima de 15, e uma classe com mais de 300 linhas lógicas combinada com
mais de 20 métodos ou mais de 10 dependências externas MUST bloquear código novo ou
alterado. Os limiares MUST ser configuráveis por perfil, e exceções MUST conter
justificativa, escopo e data de revisão. Código legado não alterado pode ser
baselineado, mas qualquer nova violação em código criado ou modificado MUST ser
reportada e tratada pelo quality gate.

A mesma análise MUST detectar segredos hardcoded, chaves de API, tokens, senhas,
certificados e credenciais de provedores em arquivos do workspace, no índice, no
diff staged e no histórico alcançável do Git. O detector MUST combinar padrões de
provedores, nomes de variáveis sensíveis, análise de entropia e regras específicas
dos adaptadores; referências a variáveis de ambiente ou secret managers são o
padrão permitido. Valores encontrados MUST ser redigidos e nunca podem aparecer
em logs, relatórios ou mensagens do agente.

Rationale: métricas objetivas detectam duplicação, concentração excessiva de
responsabilidades e funções extensas antes que esses problemas se espalhem.

### V. Explicit Scope, Traceability, and Progressive Adoption

Nenhuma ferramenta ou agente pode fazer alteração silenciosa: o CLI MUST apresentar
o escopo, os arquivos afetados, o diff relevante, os comandos executados e o
resultado dos gates. O conteúdo canônico de instruções e comandos agentic MUST viver
em `.framework/agents`, enquanto projeções específicas de cada agente permanecem
rastreáveis à fonte canônica. Tipos e comportamentos não resolvidos MUST ser
marcados como não resolvidos, nunca inventados. Codebases legadas podem adotar as
regras progressivamente, desde que o baseline e as exceções estejam registrados e
as regras completas sejam aplicadas a código novo ou modificado.

Rationale: transparência e adoção incremental permitem usar o framework em projetos
existentes sem perder controle sobre a evolução da qualidade.

### VI. Evidence-Based Learning Loop

O framework MUST oferecer um ciclo opcional de aprendizado baseado em evidências.
Quando habilitado pelo projeto ou solicitado explicitamente, o `framework learn`
deve registrar o que foi tentado, o que funcionou, o que falhou, quais decisões
foram tomadas e onde ocorreu retrabalho. Ele MUST distinguir observações diretas,
inferências e lições revisadas; não pode inventar causas, resultados ou explicações
que não estejam apoiados por eventos, diffs, testes, quality gates, issues ou
decisões registradas.

Quando o recurso estiver habilitado, eventos de ciclo de vida (`session.start`,
`session.checkpoint`,
`session.compacted`, `session.resumed` e `session.close`) MUST ser capturados por
hooks quando o host do agente oferecer essa capacidade. Sem hooks, o CLI MUST usar
checkpoints em comandos, commits e encerramentos detectáveis como fallback. Cada
evento MUST preservar a identidade da sessão, branch, worktree, commit-base,
agente, tarefas, arquivos/símbolos afetados e resultados dos gates, sem armazenar
prompts brutos, segredos ou dados sensíveis desnecessários.

O detector MUST sinalizar retrabalho por evidências como alterações repetidas no
mesmo símbolo, revert/reaplicação, tarefas reabertas, falhas seguidas de novas
tentativas ou correções que desfazem uma decisão anterior. Esses sinais MUST ser
apresentados como indícios, não como culpabilização ou causalidade certa. Lições só
podem virar regra permanente, instrução de agente ou mudança de processo após
revisão explícita; o comando não pode modificar `AGENTS.md`, `CLAUDE.md` ou código
silenciosamente.

A ausência do recurso, de hooks ou de lições MUST nunca bloquear desenvolvimento,
testes, commits, pushes, CI ou quality gates. Retrabalho é somente um sinal para
aprender e evitar a repetição do erro; não é, por si só, evidência de prontidão ou
critério para paralelizar. Paralelização exige arquitetura, plano, limites de
responsabilidade, contratos e método explícitos. Rationale: aprender com o caminho
percorrido melhora o método sem transformar hipóteses do agente em falsa
documentação.

## Architecture and Technical Constraints

O framework MUST manter separação entre núcleo do CLI, adaptadores de stack,
scripts determinísticos, integrações com agentes e persistência de índice/histórico.
Adaptadores ensinam ao núcleo como detectar tecnologias, analisar arquivos, resolver
símbolos e executar testes; não devem duplicar a orquestração central. O arquivo
`.framework/project.yml` MUST ser a fonte configurável do mapa tecnológico,
comandos de teste, perfil e política de documentação. A detecção automática MUST
ser apresentada ao usuário para validação antes de ser salva.

Blocos e metadados gerados MUST ter marcadores estáveis, ser atualizáveis por
comandos do CLI e não exigir edição manual. O framework MUST suportar execução local
e em CI, incluindo Git e GitHub quando configurados, sem depender de um agente para
operações determinísticas. Comandos que modificam código MUST possuir pré-condições
explícitas e executar os gates aplicáveis ao perfil antes de concluir.

## Security and Secret Management

O core MUST fornecer `framework security scan` como comando determinístico, somente
de leitura, e `framework check` MUST executá-lo para alterações de código ou
configuração. O scanner MUST verificar se existe `.gitignore` efetivo para `.env`,
`.env.*` e arquivos equivalentes de credenciais, preservando exceções explícitas
como `.env.example`, `.env.sample` e `.env.template`. A existência de uma regra no
arquivo não basta: um arquivo sensível já rastreado pelo Git MUST bloquear o gate.

O scanner MUST inspecionar o workspace, arquivos staged, o diff que será enviado
ao remoto e, por padrão, todos os objetos alcançáveis do histórico local. Ele MUST
identificar pelo menos cabeçalhos de chaves privadas, tokens conhecidos, JWTs,
credenciais de cloud, strings de alta entropia e atribuições suspeitas a nomes como
`API_KEY`, `SECRET`, `PASSWORD`, `TOKEN` e `ACCESS_KEY`, reduzindo falsos positivos
por placeholders conhecidos. `.env.example` pode ser versionado somente com valores
fictícios e o scanner MUST validar isso.

Cada achado MUST informar apenas caminho, linha, tipo, fingerprint não reversível e
ação recomendada. O valor secreto MUST ser mascarado inclusive para o agente
principal. Allowlist MUST usar fingerprint e justificativa, nunca o valor literal;
exceções devem ter escopo e data de expiração. O gate MUST falhar antes de commit,
push ou execução de CI quando um segredo novo for detectado. O scanner pode oferecer
um modo de revogação orientada, mas não pode presumir que remover o valor do código
resolve um segredo já exposto no histórico.

## Learning and Session Memory

O core MUST fornecer `framework learn` para resumir a sessão atual ou a última
sessão, e `framework lessons` será um alias equivalente. O recurso deve ser
desabilitável por configuração e não pode ser requisito de execução. Quando
habilitado ou solicitado explicitamente, o comando MUST produzir,
no mínimo, as seções: resultados positivos, falhas, decisões e trade-offs,
retrabalho detectado, causa provável, evidências, lições propostas e próximos
experimentos. Cada lição MUST ser atômica: uma ideia ou comportamento por item,
título curto, no máximo três bullets ou 80 palavras, e links para evidências. O
comando MUST evitar relatórios monolíticos e permitir consultar lições por símbolo,
módulo, regra ou decisão. `framework learn review` MUST permitir aceitar, rejeitar
ou editar lições antes de promovê-las para conhecimento do projeto. `framework
learn readiness --worktrees` MUST apenas diagnosticar sobreposição de
arquivos/símbolos, dependências e riscos; não autoriza paralelização por si só.

O formato de eventos MUST ser estável e extensível. Cada registro deve conter
`session_id`, `event_id`, tipo, timestamp, worktree, branch, commit-base, agente,
referências de tarefas, arquivos/símbolos, comandos/gates e referências às
evidências. O armazenamento deve ser append-only para eventos e pode manter
resumos derivados separados. Dados sensíveis MUST ser redigidos antes da
persistência, e a retenção deve ser configurável pelo projeto.

Integrações com Codex, Claude/Cloud Code e outros hosts MUST usar um contrato de
hooks comum, com adaptadores específicos somente para traduzir eventos do host.
Quando um host não suportar compactação ou encerramento observável, o framework
deve recuperar o máximo possível por checkpoints e Git, marcando o resultado como
parcial em vez de simular uma sessão completa. Quando o recurso estiver
desabilitado, nenhum hook de aprendizado deve ser instalado ou executado.

## Knowledge Assessment

Quando habilitado ou solicitado explicitamente, o core MUST fornecer os scripts
determinísticos `framework learn quiz generate`, `framework learn quiz run` e
`framework learn quiz sync` para avaliar o conhecimento da codebase sem depender de
um agente de IA. O quiz MUST gerar e aplicar perguntas de múltipla
escolha sobre arquitetura, modularização, boas práticas, decisões, trade-offs,
regras de negócio, testes, segurança e operação, usando o índice AST, specs,
contratos, testes explicados, decisões e histórico como fontes.

Cada pergunta MUST possuir um objetivo de conhecimento, enunciado curto, de três a
cinco alternativas, exatamente uma resposta correta, explicação curta, dificuldade,
versão e evidências. Perguntas e explicações MUST ser pequenas o suficiente para
serem estudadas em uma unidade; a explicação não deve exceder 80 palavras. O
resultado deve registrar resposta, acerto, tentativa, confiança e data, sem expor a
resposta antes da submissão. A avaliação é educacional e não é quality gate.

Perguntas MUST ser associáveis a um ou mais identificadores estáveis de função,
método, classe, módulo, regra de negócio, teste, contrato ou decisão. O vínculo
deve guardar o fingerprint da fonte. Quando uma função, regra ou decisão vinculada
for alterada, `framework learn quiz sync` MUST marcar a pergunta como
`needs_review`, atualizar suas evidências e impedir que a versão antiga seja
tratada como conhecimento atual, sem apagar o histórico das tentativas.

O SQLite local (`.framework/index.db`) será a fonte de relacionamento entre
perguntas, conhecimento e símbolos; YAML poderá ser exportado para revisão humana e
versionamento. A geração deve ser reproduzível por script e perguntas rejeitadas ou
alteradas devem permanecer auditáveis. Perguntas propostas não podem alterar código,
testes, instruções ou regras do projeto sem revisão explícita.

## Development Workflow and Quality Gates

O fluxo padrão para uma mudança de comportamento é: especificar, localizar o
contexto respeitando a cadeia de instruções, criar o teste, confirmar o estado
vermelho, aprovar quando o perfil exigir, implementar a menor mudança, executar
testes relacionados, sincronizar o índice e explicações, rodar análise estática,
revisar o diff e executar `framework check`. Comandos somente de leitura, como
trade-offs e revisão, não podem modificar código.

Um quality gate bloqueador MUST falhar quando houver teste aprovado modificado sem
autorização, explicação gerada desatualizada, duplicação ou complexidade acima dos
limiares aplicáveis, tipo inventado, erro de análise estática, teste relacionado
falhando ou instrução obrigatória não carregada. O relatório MUST separar erros,
avisos, baseline legado e exceções aprovadas. O CI MUST poder executar os mesmos
gates usados localmente.

## Governance

Esta constituição define as regras de governança do framework. Instruções de agente,
templates, scripts e documentação operacional MUST permanecer compatíveis com ela;
em conflito interno, esta constituição prevalece, sem substituir instruções de
usuário, sistema ou plataforma que tenham autoridade superior.

Qualquer alteração constitucional MUST atualizar a versão, a data de emenda, o
relatório de impacto no topo deste arquivo e os templates dependentes. Versões usam
SemVer: MAJOR para remoção ou redefinição incompatível de princípio, MINOR para novo
princípio ou seção normativa, e PATCH para esclarecimentos sem mudança de obrigação.
Uma mudança MUST registrar motivação, impacto sobre fluxos existentes, migração
necessária e resultado da validação dos artefatos sincronizados.

Toda implementação e revisão MUST verificar conformidade com os princípios,
especialmente a cadeia de instruções e os quality gates estáticos. Exceções devem ser
locais, justificadas, temporárias e visíveis no relatório; não podem virar uma forma
permanente de contornar a constituição. A adoção progressiva de código legado não
dispensa os gates para arquivos novos ou modificados.

**Version**: 1.3.0 | **Ratified**: 2026-07-30 | **Last Amended**: 2026-07-30
