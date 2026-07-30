# Implementation Plan: Incremental Session Learning and Agent Handoff

**Branch**: `002-session-learning-memory` | **Date**: 2026-07-30 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-session-learning-memory/spec.md`

## Summary

Implementar o módulo opcional `framework learn` com memória append-only por sessão,
resumos curtos, detecção de retrabalho, revisão de lições, handoffs redigidos e
quiz associado a fontes da codebase. A memória será local por projeto e poderá ser
versionada em registros redigidos; commits continuam manuais. A geração do quiz
poderá delegar inferência a um executável local autorizado (Codex, Claude, Cloud,
Antigravity ou outro comando configurado) usando contexto autorizado e redigido.
Não haverá provider HTTP/API no core; validação, sincronização, execução da prova e
fallback permanecem determinísticos e independentes de IA.

## Technical Context


**Language/Version**: Python 3.11+, gerenciado por `uv`  
**Primary Dependencies**: biblioteca padrão, `PyYAML`, SQLite existente, AST e subprocessos controlados; integrações por linha de comando são adaptadores opcionais
**Storage**: JSONL append-only redigido em `.framework/learn/events/`, lições e perguntas versionáveis em `.framework/learn/`, relações no `.framework/index.db`  
**Testing**: `pytest`, testes de contrato, fixtures de sessões, testes de redaction, integração de subprocessos e testes de comando local simulado
**Target Platform**: macOS e Linux, terminal local e CI  
**Project Type**: extensão de CLI/devtool existente  
**Performance Goals**: resumo de sessão em até 10 segundos; exportação/importação de handoff em até 30 segundos; geração/sincronização local incremental sem varrer a codebase inteira quando não houver fontes alteradas  
**Constraints**: opt-in e não bloqueante; nenhum segredo ou prompt bruto persistido; commit manual; Git pode estar indisponível com cobertura parcial; nenhum provider HTTP/API é dependência de execução
**Scale/Scope**: sessões incrementais por projeto/branch/worktree, até 10.000 eventos por sessão, quizzes versionados por codebase e handoffs selecionáveis por escopo

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] Applicable Markdown instruction files (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`,
      `CLOUD.md` and local instructions) were loaded; the active chain is recorded
      by the implementation and agent projection contracts.
- [x] Predictable capture, redaction, persistence, sync and quiz execution use
      deterministic scripts/AST/index operations before optional agentic generation.
- [x] Test-first flow, protected approved behavior and command permissions are
      defined for learn, handoff and quiz commands.
- [x] Existing static-analysis gates remain mandatory for all changed code, with
      thresholds, baseline and exception policy inherited from the framework.
- [x] Existing secret scanning is required before persistence, versioning and
      handoff; generated records are scanned and redacted.
- [x] Session events, append-only retention, redaction, tombstones, handoff and
      lesson review are defined; learning remains optional and non-blocking.
- [x] Questions are short, versioned and linked to stable sources; command-line
      inference is optional while validation, sync and quiz run remain independent.
- [x] `framework check` and security gates continue to report actionable findings
      and run locally/CI; learn outputs use the same safe envelopes.
- [x] No constitutional violation remains after the 1.5.0 amendment allowing
      optional command-assisted question generation without making the core depend on it.

## Project Structure

### Documentation (this feature)

```text
specs/002-session-learning-memory/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
```

### Source Code (repository root)
```text
src/framework_cli/
├── commands/
│   ├── learn.py
│   └── quiz.py
├── learn/
│   ├── events.py
│   ├── store.py
│   ├── summarize.py
│   ├── lessons.py
│   ├── rework.py
│   └── handoff.py
├── quiz/
│   ├── models.py
│   ├── generator.py
│   ├── command_generation.py
│   ├── repository.py
│   ├── sync.py
│   └── runner.py
├── agents/
│   ├── instructions.py
│   └── projections.py
├── security/
│   └── scanner.py
└── reporting/
    └── render.py

tests/
├── unit/
├── integration/
├── contract/
└── fixtures/
    ├── sessions/
    ├── handoffs/
    └── quiz/
```

**Structure Decision**: Estender o pacote CLI existente com módulos separados para
eventos/memória, handoff e quiz. O armazenamento de fatos fica em arquivos JSONL
redigidos para manter histórico legível e append-only; SQLite mantém relações e
fingerprints. Comandos locais ficam atrás de adaptadores de subprocesso e não entram
no core obrigatório. Os testes isolam persistência, redaction, delegação e invalidação.

## Phase 0: Research

As decisões estão registradas em [research.md](./research.md). Não há
`NEEDS CLARIFICATION` restante: o único conflito aparente entre geração assistida
e constituição foi resolvido pela emenda 1.5.0, mantendo quiz run/sync/validation
independentes de agentes.

## Phase 1: Design

O modelo de entidades e estados está em [data-model.md](./data-model.md). Os
contratos estão em `contracts/` e o fluxo executável está em [quickstart.md](./quickstart.md).

## Phase 1: Agent Context Update

`AGENTS.md` aponta para este plano ativo e para `plan.md` da arquitetura raiz. As
projeções Codex/Claude devem carregar a cadeia de instruções antes de qualquer
delegação de geração ou importação de handoff.

## Complexity Tracking

Não há violações constitucionais. A fronteira de comando local adiciona uma
interface necessária para inferência opcional, mas o fallback local mantém o core
executável sem IA; a complexidade é limitada aos adaptadores CLI e aos contratos de
redaction/ack.
