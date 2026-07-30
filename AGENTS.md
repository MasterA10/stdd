<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan:
`specs/002-session-learning-memory/plan.md` and the root architecture plan
`plan.md`.
<!-- SPECKIT END -->

## Instruções obrigatórias do projeto

O agente principal MUST carregar este arquivo e todos os arquivos Markdown de
instrução aplicáveis ao diretório antes de planejar ou alterar qualquer arquivo.
Isso inclui arquivos equivalentes reconhecidos pelo agente, como `CLAUDE.md`,
`GEMINI.md` e `CLOUD.md`, além de instruções mais específicas em subdiretórios.
Agentes delegados MUST receber a mesma cadeia. Em conflito, a instrução mais
específica prevalece; conflitos não resolvidos interrompem a execução.

Toda alteração de código MUST executar `framework check` (ou os analisadores
determinísticos equivalentes enquanto o CLI estiver em construção), incluindo
detecção de duplicação, funções extensas, classes Deus e segredos hardcoded. Antes
de commit, push ou CI, o agente MUST executar `framework security scan` (ou o
equivalente determinístico), verificando `.gitignore`, arquivos `.env`, diffs e
histórico Git. Valores encontrados nunca podem ser exibidos no relatório.

O agente MUST registrar os arquivos de instrução carregados, os comandos
executados e os quality gates aprovados. Operações previsíveis devem usar scripts
antes de agentes, e nenhum teste aprovado pode ser alterado para mascarar uma
falha de implementação.

O recurso `framework learn` é opcional e não é um quality gate. Quando estiver
habilitado, o agente pode registrar checkpoints, decisões e retrabalho, sempre
redigindo dados sensíveis e submetendo lições a revisão antes de promovê-las para
instruções permanentes.

Quando habilitado, `framework learn quiz` é um script opcional de avaliação da
codebase. A geração pode delegar inferência a um executável local autorizado, como
Codex, Claude, Cloud ou Antigravity, com contexto previamente redigido, mas
execução, sincronização, validação e aplicação da prova devem funcionar sem esse
comando. Não há provider HTTP/API no core. O agente principal recebe apenas a
confirmação do job, não o contexto ou o conteúdo gerado. As perguntas devem ser curtas, associadas a
símbolos ou regras estáveis e marcadas para revisão quando o código mudar. O
resultado é educacional e não é critério automático de paralelização nem quality gate.
