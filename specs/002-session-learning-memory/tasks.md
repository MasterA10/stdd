---

description: "Dependency-ordered implementation tasks for incremental learning, handoff and quiz"
---

# Tasks: Incremental Session Learning and Agent Handoff

**Input**: Design documents from `/specs/002-session-learning-memory/`
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), `contracts/`, [quickstart.md](./quickstart.md)

**Tests**: Tests are included before behavior implementation because the constitution
requires test-first changes, protected approved behavior and redaction coverage.

**Organization**: Tasks are grouped by user story. US1 and US2 are P1; US3 is P2.
The shared foundation is blocking for all stories.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Parallelizable when file ownership and dependencies permit it.
- **[Story]**: Required on user-story tasks (`[US1]`, `[US2]`, `[US3]`).
- Every task includes the exact file or directory it creates or modifies.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish storage directories, configuration, fixtures and test
conventions for optional learning without changing application code.

- [X] T001 Create `.framework/learn/events/`, `.framework/learn/lessons/`, `.framework/learn/handoffs/` and `.framework/learn/quiz/` path configuration in `src/framework_cli/config/model.py` and `src/framework_cli/config/loader.py`.
- [X] T002 [P] Add learn/quiz feature flags, retention, provider and redaction settings to `.framework/project.yml` examples in `specs/002-session-learning-memory/quickstart.md`.
- [X] T003 [P] Create session, handoff and quiz fixtures under `tests/fixtures/sessions/`, `tests/fixtures/handoffs/` and `tests/fixtures/quiz/`.
- [X] T004 [P] Add package markers and fixture loaders in `tests/unit/`, `tests/integration/` and `tests/contract/` for the new learn/quiz modules.
- [X] T005 [P] Add `learn` and `quiz` command entry points to `src/framework_cli/commands/registry.py` and `src/framework_cli/cli.py` help metadata without enabling behavior yet.
- [X] T006 [P] Add CI invocation examples for optional learn/quiz tests to `.github/workflows/ci.yml` and `.github/workflows/release.yml`.

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build contracts and safe persistence primitives required by every
user story.

### Foundation tests first

- [X] T007 [P] Add event schema and lifecycle contract tests in `tests/contract/test_learn_events.py` for append-only records and session states.
- [X] T008 [P] Add redaction and tombstone tests in `tests/unit/test_learn_redaction.py` for `.env`, credentials, prompts, PII and non-reversible fingerprints.
- [X] T009 [P] Add SQLite relationship tests in `tests/unit/test_learn_index.py` for sessions, events, lessons, handoffs, questions, providers and attempts.
- [X] T010 [P] Add handoff envelope/checksum tests in `tests/contract/test_handoff_contract.py` for structured/Markdown parity and invalid imports.
- [X] T011 [P] Add external-generation acknowledgment tests in `tests/contract/test_external_generation_contract.py` proving the principal agent receives only status and opaque job ID.
- [X] T012 [P] Add common result/disabled-mode tests in `tests/contract/test_learn_result_envelope.py` for text, JSON, disabled and partial coverage states.

### Foundation implementation

- [X] T013 Implement typed session/event/coverage models in `src/framework_cli/learn/events.py` following `data-model.md` and `contracts/learn-events.md`.
- [X] T014 Implement append-only JSONL storage, atomic writes and tombstone handling in `src/framework_cli/learn/store.py`.
- [X] T015 Implement shared redaction pipeline using `src/framework_cli/security/scanner.py`, `src/framework_cli/security/redaction.py` and `src/framework_cli/security/fingerprint.py`.
- [X] T016 Implement SQLite migrations and repositories for learn/quiz entities in `src/framework_cli/index/schema.py`, `src/framework_cli/index/db.py` and `src/framework_cli/index/repository.py`.
- [X] T017 Implement session identity, event append and partial host coverage in `src/framework_cli/learn/lifecycle.py`.
- [X] T018 Implement applicable instruction-chain loading and conflict blocking for learn/handoff/provider operations in `src/framework_cli/agents/instructions.py`.
- [X] T019 Implement shared learn/quiz command metadata, disabled behavior and safe result rendering in `src/framework_cli/commands/registry.py` and `src/framework_cli/reporting/render.py`.
- [X] T020 Add foundation integration coverage in `tests/integration/test_learn_foundation.py` for redaction, append-only writes, SQLite relations, instructions and disabled mode.

**Checkpoint**: A project can record a redacted append-only event, index it, report
partial hook coverage and remain fully operational when learning is disabled.

## Phase 3: User Story 1 - Register and Review Session Learning (Priority: P1)

**Goal**: Capture incremental session facts, summaries, rework signals and reviewed
lessons without overwriting previous sessions or creating commits automatically.

**Independent Test**: Start a fixture session, append checkpoints and failures,
close/resume it, query today and historical sessions, review a proposed lesson and
verify redacted files, immutable events and manual-commit behavior.

### Tests for User Story 1

- [X] T021 [P] [US1] Add lifecycle command tests in `tests/integration/test_learn_lifecycle.py` for start, checkpoint, compacted, resumed, close and incomplete sessions.
- [X] T022 [P] [US1] Add session/date query tests in `tests/integration/test_learn_history.py` for today, a specific session, branch/worktree and accumulated history.
- [X] T023 [P] [US1] Add summary tests in `tests/integration/test_learn_summary.py` for successes, failures, decisions, trade-offs, rework, evidence and next experiments with short lessons.
- [X] T024 [P] [US1] Add rework-signal tests in `tests/integration/test_rework_detection.py` for repeated symbols, revert/reapply, reopened tasks and retries after failed gates.
- [X] T025 [P] [US1] Add lesson-review tests in `tests/integration/test_lesson_review.py` for proposed, approved, rejected, edited and promoted lessons with evidence.
- [X] T026 [P] [US1] Add safety tests in `tests/integration/test_learn_manual_commit.py` proving auto-write does not create Git commits and blocks sensitive records.

### Implementation for User Story 1

- [X] T027 [US1] Implement `framework learn start|checkpoint|resume|close` orchestration in `src/framework_cli/commands/learn.py` and `src/framework_cli/learn/lifecycle.py`.
- [X] T028 [US1] Implement local-date/session/branch/worktree history queries in `src/framework_cli/learn/store.py` and `src/framework_cli/learn/query.py`.
- [X] T029 [US1] Implement short session and accumulated summaries in `src/framework_cli/learn/summarize.py` with observed/inferred separation and evidence links.
- [X] T030 [US1] Implement confidence-based rework detection in `src/framework_cli/learn/rework.py` using Git history, diffs, tasks and gate evidence.
- [X] T031 [US1] Implement atomic lesson revisions and human review/promotion in `src/framework_cli/learn/lessons.py` and `src/framework_cli/commands/learn.py`.
- [X] T032 [US1] Implement host event adapter hooks and fallback coverage reporting in `src/framework_cli/learn/hooks.py` and `src/framework_cli/learn/lifecycle.py`.
- [X] T033 [US1] Add end-to-end session fixtures and expected redacted records under `tests/fixtures/sessions/expected/`.
- [X] T034 [US1] Document session capture, review, retention and manual commit workflow in `specs/002-session-learning-memory/quickstart.md`.

**Checkpoint**: `framework learn` provides incremental, date-separated, redacted
session learning and human-reviewed lessons without blocking normal development.

## Phase 4: User Story 2 - Transfer Context to Another Agent or Session (Priority: P1)

**Goal**: Export/import a scoped, redacted and checksummed handoff, preserving source
identity while creating a new linked session on import.

**Independent Test**: Export a fixture session to structured and Markdown files,
modify or inject a secret into a package, verify rejection, then import a valid
package into a new linked session for generic and named targets.

### Tests for User Story 2

- [X] T035 [P] [US2] Add scope-selection tests in `tests/integration/test_handoff_scope.py` for sessions, categories, tasks, files, symbols, statuses and approved/proposed lessons.
- [X] T036 [P] [US2] Add package parity/checksum tests in `tests/integration/test_handoff_export.py` for `handoff.json`, `handoff.md` and `manifest.json`.
- [X] T037 [P] [US2] Add redaction/security tests in `tests/integration/test_handoff_redaction.py` for `.env`, prompts, credentials, PII and post-persistence tombstones.
- [X] T038 [P] [US2] Add import conflict tests in `tests/integration/test_handoff_import.py` for invalid version, checksum mismatch, instruction conflict, changed branch and duplicate import.
- [X] T039 [P] [US2] Add linked-session tests in `tests/integration/test_handoff_session_link.py` proving imported sessions receive a new identity and parent reference.
- [X] T040 [P] [US2] Add generic/Codex/Claude/Antigravity target tests in `tests/contract/test_handoff_targets.py` for supported and unsupported host coverage.

### Implementation for User Story 2

- [X] T041 [US2] Implement scoped context selection and approved/proposed filtering in `src/framework_cli/learn/handoff_scope.py`.
- [X] T042 [US2] Implement structured handoff package creation, manifest and checksums in `src/framework_cli/learn/handoff.py`.
- [X] T043 [US2] Implement equivalent Markdown rendering in `src/framework_cli/learn/handoff_render.py` without expanding structured scope.
- [X] T044 [US2] Implement pre-export redaction, security scanning and tombstone guidance in `src/framework_cli/learn/handoff.py` and `src/framework_cli/security/scanner.py`.
- [X] T045 [US2] Implement package validation, instruction-chain checks and conflict-safe import in `src/framework_cli/learn/handoff_import.py`.
- [X] T046 [US2] Implement new linked-session creation for handoff imports in `src/framework_cli/learn/lifecycle.py` and `src/framework_cli/learn/store.py`.
- [X] T047 [US2] Implement `framework learn handoff export|import` command parsing, permissions and text/JSON envelopes in `src/framework_cli/commands/learn.py`.
- [X] T048 [US2] Add target adapter registry and generic destination fallback in `src/framework_cli/agents/handoff_targets.py`.
- [X] T049 [US2] Document handoff review, target selection, import conflicts and partial coverage in `specs/002-session-learning-memory/quickstart.md`.

**Checkpoint**: A person can safely transfer reviewed context to another agent or
session, with explicit scope, integrity, redaction and lineage.

## Phase 5: User Story 3 - Evaluate Knowledge of the Codebase (Priority: P2)

**Goal**: Generate, validate, store, synchronize and run short multiple-choice
questions linked to stable sources; allow external inference without exposing the
context or question content to the principal agent.

**Independent Test**: Generate local and external-provider fixture questions, verify
the acknowledgment-only boundary, run a quiz without a provider, change a source,
sync `needs_review`, and inspect attempts and exports.

### Tests for User Story 3

- [X] T050 [P] [US3] Add question schema tests in `tests/contract/test_quiz_contract.py` for 3–5 options, one correct answer, short explanations, provenance and source fingerprints.
- [X] T051 [P] [US3] Add deterministic fallback generation tests in `tests/integration/test_quiz_fallback.py` for AST/spec/test/decision source extraction without an agent.
- [X] T052 [P] [US3] Add external provider request tests in `tests/integration/test_quiz_external_provider.py` proving scoped redacted context and no provider credentials in payloads.
- [X] T053 [P] [US3] Add acknowledgment-only tests in `tests/integration/test_quiz_ack_boundary.py` proving the principal agent receives only status and opaque job ID.
- [X] T054 [P] [US3] Add provider failure/partial tests in `tests/integration/test_quiz_provider_failure.py` for unavailable, timeout, malformed and partial responses.
- [X] T055 [P] [US3] Add quiz run tests in `tests/integration/test_quiz_run.py` for hidden answers, scoring, confidence, categories and provider-free execution.
- [X] T056 [P] [US3] Add source invalidation tests in `tests/integration/test_quiz_sync.py` for changed, removed and unchanged symbols/rules with preserved attempts.
- [X] T057 [P] [US3] Add quiz export tests in `tests/integration/test_quiz_export.py` for JSON, YAML, Markdown, redaction and versioned provenance.

### Implementation for User Story 3

- [X] T058 [US3] Implement question, source, provenance, attempt and generation-job models in `src/framework_cli/quiz/models.py`.
- [X] T059 [US3] Implement question validation and source fingerprint checks in `src/framework_cli/quiz/validation.py`.
- [X] T060 [US3] Implement deterministic local candidate generation in `src/framework_cli/quiz/generator.py` from AST symbols, specs, contracts, tests and decisions.
- [X] T061 [US3] Implement external provider protocol, scoped request and acknowledgment-only response in `src/framework_cli/quiz/providers.py`.
- [X] T062 [US3] Implement provider registry, permission declaration and external/local selection in `src/framework_cli/quiz/provider_registry.py`.
- [X] T063 [US3] Implement provider output validation, provenance storage and job status transitions in `src/framework_cli/quiz/generation_jobs.py`.
- [X] T064 [US3] Implement SQLite/file repositories for questions, sources, jobs and attempts in `src/framework_cli/quiz/repository.py`.
- [X] T065 [US3] Implement provider-free quiz runner with hidden answers, scoring and category reporting in `src/framework_cli/quiz/runner.py`.
- [X] T066 [US3] Implement source fingerprint synchronization and `needs_review` transitions in `src/framework_cli/quiz/sync.py`.
- [X] T067 [US3] Implement quiz export rendering and safe structured/text reports in `src/framework_cli/quiz/export.py` and `src/framework_cli/reporting/render.py`.
- [X] T068 [US3] Implement `framework learn quiz generate|run|sync|export` in `src/framework_cli/commands/quiz.py` with disabled/non-blocking behavior.
- [X] T069 [US3] Add agent projection instructions for external quiz delegation and acknowledgment-only boundaries in `src/framework_cli/agents/templates/quiz-generation.md`.
- [X] T070 [US3] Document local fallback, external generation, agent boundary and quiz synchronization in `specs/002-session-learning-memory/quickstart.md`.

**Checkpoint**: The quiz is executable without AI, while external inference can
create stored questions through a redacted, acknowledgment-only provider boundary.

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T071 [P] Add performance fixtures for 10,000 events, 30-second handoffs and incremental quiz sync in `tests/integration/test_learn_performance.py`.
- [X] T072 [P] Add security regression fixtures for generated memory, handoffs, provider payloads and history in `tests/integration/test_learn_security.py`.
- [X] T073 [P] Add macOS/Linux subprocess and provider timeout coverage in `tests/integration/test_learn_platforms.py`.
- [X] T074 [P] Update `.github/workflows/ci.yml` and `.github/workflows/release.yml` with learn/quiz tests, `framework check` and `framework security scan` over generated artifacts.
- [X] T075 [P] Add configuration and command-help documentation for feature flags, permissions and modified files in `specs/002-session-learning-memory/quickstart.md`.
- [X] T076 Run `uv run pytest` for unit, contract and integration suites and record coverage in `specs/002-session-learning-memory/quickstart.md`.
- [X] T077 Run `framework check --format json`, resolve new duplication/complexity findings and confirm generated learn/quiz files are in scope.
- [X] T078 Run `framework security scan --format json` against workspace, generated records, staged diff and reachable history; confirm no sensitive value appears.
- [X] T079 Review the final diff, task completion, instruction-chain evidence and constitution alignment in `AGENTS.md`, `plan.md` and `specs/002-session-learning-memory/`.

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No feature dependencies; prepares paths and fixtures.
- **Foundation (Phase 2)**: Depends on Setup and blocks all user stories.
- **US1 (Phase 3)**: Depends on Foundation; delivers the first usable learning MVP.
- **US2 (Phase 4)**: Depends on Foundation and US1 event/store contracts.
- **US3 (Phase 5)**: Depends on Foundation and source/index contracts; can begin
  local generation after Foundation but integrates session context from US1.
- **Polish (Phase 6)**: Depends on the completed target stories.

### User Story Dependencies

- **US1**: Independent after Foundation.
- **US2**: Requires US1 session/event persistence and instruction-chain behavior.
- **US3**: Requires Foundation source/index contracts and uses US1 redacted context;
  its provider adapter remains independently testable.

### Parallel Opportunities

- T002-T006 can run in parallel after T001.
- T007-T012 can run in parallel before Foundation implementation.
- T013-T019 can be split by module after the contracts are approved; T020 integrates.
- T021-T026 can run in parallel because each test file owns a distinct concern.
- T035-T040 can run in parallel before handoff implementation.
- T041-T044 can run in parallel after T013-T016; T045-T049 integrate import/CLI.
- T050-T057 can run in parallel before provider/runner implementation.
- T060-T063 can run in parallel after T058-T059; T064-T068 integrate persistence and CLI.
- T071-T075 can run in parallel after target stories; T076-T079 are sequential gates.

## Parallel Example: External Quiz Generation

```text
After T058-T059:
  Worker A: T060 deterministic candidate generator + fallback tests
  Worker B: T061-T063 external provider protocol, validation and job state tests
  Worker C: T064 repository and provenance tests
  Worker D: T065-T066 quiz runner and source-sync tests

Integration:
  T067 export/reporting -> T068 CLI -> T069 agent projection -> T070 docs
```

## Implementation Strategy

### MVP First

1. Complete Setup and Foundation (T001-T020).
2. Complete US1 session capture, summary and lesson review (T021-T034).
3. Demonstrate `framework learn start`, `checkpoint`, `close`, `review` and a
   redacted versionable event stream without external providers.

### Incremental Delivery

1. Add US2 handoff export/import and linked sessions.
2. Add US3 deterministic quiz run/sync and local fallback.
3. Add optional external generation with acknowledgment-only boundary.
4. Run security, static quality, performance and CI gates.

### Definition of Done

- Target story tests pass and approved tests remain unchanged without authorization.
- Learn facts are append-only, redacted and manually commit-controlled.
- Handoff packages have structured/Markdown parity, checksum and conflict protection.
- Quiz run/sync work without an external agent; provider generation is optional.
- External provider responses to the principal agent contain only status and opaque ID.
- `framework check` and `framework security scan` pass without exposing values.
- All applicable Markdown instructions were loaded and recorded.
