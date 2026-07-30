---

description: "Dependency-ordered implementation tasks for the CLI Framework Foundation"
---

# Tasks: CLI Framework Foundation

**Input**: Design documents from `/specs/001-cli-framework-bootstrap/`
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), `contracts/`, [quickstart.md](./quickstart.md)

**Tests**: Behavior-changing work includes tests before implementation. Every user
story is independently testable; integration tests use fixtures under
`tests/fixtures/`.

**Organization**: Tasks are grouped by user story in priority order. User Stories
1, 2 and 3 are P1 and depend on the shared foundation.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel when it uses different files and has no incomplete
  dependency.
- **[Story]**: Required for user story tasks (`[US1]`, `[US2]`, `[US3]`).
- Every task names the exact file or directory it creates or changes.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the distributable Python package, test layout and CI baseline.

- [X] T001 Create `pyproject.toml` with Python 3.11+, `uv` metadata, the `framework` console entry point, `PyYAML` runtime dependency and `pytest` development dependency.
- [X] T002 Create the package tree under `src/framework_cli/` with `__init__.py` and `__main__.py` entry points.
- [X] T003 [P] Create test directories `tests/unit/`, `tests/integration/`, `tests/contract/` and `tests/fixtures/` with package markers where needed.
- [X] T004 [P] Add repository secret exclusions for `.env`, `.env.*`, private keys and framework local state to `.gitignore`.
- [X] T005 [P] Configure test, coverage and lint commands in `pyproject.toml`.
- [X] T006 [P] Create the macOS/Linux CI workflow in `.github/workflows/ci.yml` with `uv`, unit tests and the framework quality commands.
- [X] T007 [P] Add package version metadata and `framework version` fixture expectations in `src/framework_cli/version.py` and `tests/unit/test_version.py`.
- [X] T008 Create reference codebases for greenfield, brownfield and monorepo detection under `tests/fixtures/projects/`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement shared contracts that every user story depends on. No user
story implementation can begin until this phase is complete.

### Foundation tests first

- [X] T009 [P] Add configuration validation tests in `tests/unit/test_config.py` for profiles, paths, adapters, policies and unknown-key warnings.
- [X] T010 [P] Add SQLite schema and migration tests in `tests/unit/test_index.py` for project, application, adapter, finding and generated-artifact records.
- [X] T011 [P] Add command result and JSON envelope tests in `tests/contract/test_result_envelope.py` for success, warning, blocked, error and degraded states.
- [X] T012 [P] Add safe subprocess execution tests in `tests/unit/test_script_runner.py` for arguments, allowed paths, timeouts and exit-code mapping.

### Foundation implementation

- [X] T013 Implement configuration models and validation in `src/framework_cli/config/model.py`, `src/framework_cli/config/loader.py` and `src/framework_cli/config/validator.py`.
- [X] T014 Implement versioned SQLite schema and repositories in `src/framework_cli/index/schema.py`, `src/framework_cli/index/db.py` and `src/framework_cli/index/repository.py`.
- [X] T015 Implement shared command result models and text/JSON rendering in `src/framework_cli/reporting/models.py` and `src/framework_cli/reporting/render.py`.
- [X] T016 Implement the deterministic subprocess runner in `src/framework_cli/scripts/runner.py` with argument lists, environment filtering, timeout handling and allowed-path checks.
- [X] T017 Implement the adapter protocol in `src/framework_cli/adapters/base.py` for detection, symbols, tests, scripts and quality rules.
- [X] T018 [P] Implement the generic filesystem/manifests adapter in `src/framework_cli/adapters/generic.py`.
- [X] T019 [P] Implement the Python adapter in `src/framework_cli/adapters/python.py` using `ast` and Python project manifests.
- [X] T020 [P] Implement the JavaScript/TypeScript adapter in `src/framework_cli/adapters/javascript.py` using package manifests and native runner discovery.
- [X] T021 Implement adapter discovery and capability registration in `src/framework_cli/adapters/registry.py`.
- [X] T022 Implement Git repository access, snapshots, staged/remotable diffs and history queries in `src/framework_cli/git/repository.py`.
- [X] T023 Implement instruction-chain discovery, scope precedence and conflict records in `src/framework_cli/agents/instructions.py`.
- [X] T024 Implement redaction and non-reversible fingerprint utilities in `src/framework_cli/security/redaction.py` and `src/framework_cli/security/fingerprint.py`.
- [X] T025 Implement the root CLI parser and command registry in `src/framework_cli/cli.py` and `src/framework_cli/commands/registry.py`.
- [X] T026 Add shared foundation integration tests in `tests/integration/test_foundation.py` covering configuration, SQLite, Git degraded mode, command envelopes and instruction loading.

**Checkpoint**: The package can start, validate configuration, discover adapters,
load instruction files, query Git and emit safe structured results.

---

## Phase 3: User Story 1 - Initialize and Understand a Project (Priority: P1) 🎯 MVP

**Goal**: Initialize new and existing projects, confirm detection, persist the
profile and report degraded environments safely.

**Independent Test**: Run initialization against the greenfield, brownfield and
monorepo fixtures, correct a detected value, confirm the profile and verify that
only framework artifacts are written.

### Tests for User Story 1

- [X] T027 [P] [US1] Add CLI contract tests for `framework init`, `--here`, `--from`, `--non-interactive` and exit codes in `tests/contract/test_init_cli.py`.
- [X] T028 [P] [US1] Add detection integration tests for languages, manifests, test runners, datastores and monorepo applications in `tests/integration/test_detection.py`.
- [X] T029 [P] [US1] Add confirmation-flow tests for corrected detections and cancellation in `tests/integration/test_init_confirmation.py`.
- [X] T030 [P] [US1] Add degraded-mode tests for missing Git and unsupported platforms in `tests/integration/test_init_degraded.py`.

### Implementation for User Story 1

- [X] T031 [US1] Implement detection orchestration and confidence records in `src/framework_cli/commands/init.py` and `src/framework_cli/commands/scan.py`.
- [X] T032 [US1] Implement greenfield, brownfield and monorepo profile creation in `src/framework_cli/config/project.py`.
- [X] T033 [US1] Implement interactive correction and confirmation prompts in `src/framework_cli/commands/init.py` with text and JSON result modes.
- [X] T034 [US1] Implement `framework doctor` environment, Git, `uv`, adapter, permission and generated-artifact checks in `src/framework_cli/commands/doctor.py`.
- [X] T035 [US1] Implement degraded capability reporting in `src/framework_cli/git/repository.py` and `src/framework_cli/reporting/models.py`.
- [X] T036 [US1] Add initialization fixture snapshots and expected profiles under `tests/fixtures/expected_profiles/`.
- [X] T037 [US1] Document persistent installation, GitHub bootstrap and initialization flow in `specs/001-cli-framework-bootstrap/quickstart.md`.

**Checkpoint**: A user can install or bootstrap the CLI, initialize a project,
correct detection, select a profile and understand any degraded capabilities.

---

## Phase 4: User Story 2 - Execute Development Workflow and Quality Gates (Priority: P1)

**Goal**: Run tests, static analysis, secret scanning and Git hooks with actionable
text/JSON reports and profile-aware blocking behavior.

**Independent Test**: Run the workflow on fixtures containing a duplicate block, a
long function, a God-class signal, a baseline finding, a safe `.env.example` and an
unsafe staged `.env`; verify findings, severities, redaction and exit codes.

### Tests for User Story 2

- [X] T038 [P] [US2] Add configured test aggregation tests in `tests/integration/test_test_command.py` for multiple suites, unavailable runners and child results.
- [X] T039 [P] [US2] Add static quality rule tests in `tests/integration/test_quality_rules.py` for duplication, function length, cognitive complexity and God-class thresholds.
- [X] T040 [P] [US2] Add baseline/severity tests in `tests/integration/test_quality_baseline.py` for new, modified, baseline and suppressed findings.
- [X] T041 [P] [US2] Add secret scanning tests in `tests/integration/test_security_scan.py` for `.gitignore`, tracked `.env`, staged diff, private keys, provider patterns, entropy and redaction.
- [X] T042 [P] [US2] Add report contract tests in `tests/contract/test_quality_report.py` for text/JSON equivalence and absence of secret values.
- [X] T043 [P] [US2] Add Git hook tests in `tests/integration/test_git_hooks.py` for installation, preservation of existing hooks, conflict reporting and blocked commits.

### Implementation for User Story 2

- [X] T044 [US2] Implement configured test execution and aggregation in `src/framework_cli/commands/test.py` and `src/framework_cli/reporting/children.py`.
- [X] T045 [US2] Implement quality rule models, thresholds, profiles and baseline loading in `src/framework_cli/quality/rules.py` and `src/framework_cli/quality/baseline.py`.
- [X] T046 [US2] Implement adapter-driven quality orchestration in `src/framework_cli/quality/engine.py`.
- [X] T047 [US2] Implement duplicate-block detection using normalized source/token sequences in `src/framework_cli/quality/duplication.py`.
- [X] T048 [US2] Implement function, method and class metrics in `src/framework_cli/quality/complexity.py` and `src/framework_cli/quality/god_class.py`.
- [X] T049 [US2] Implement `.gitignore` effectiveness and Git scope collection in `src/framework_cli/security/git_scope.py`.
- [X] T050 [US2] Implement provider patterns, sensitive assignment detection and entropy rules in `src/framework_cli/security/patterns.py`.
- [X] T051 [US2] Implement redacted security scanning and block decisions in `src/framework_cli/security/scanner.py`.
- [X] T052 [US2] Implement `framework check` orchestration in `src/framework_cli/commands/check.py` with profile severity and baseline behavior.
- [X] T053 [US2] Implement `framework security scan` in `src/framework_cli/commands/security.py` with text/JSON output and safe exit codes.
- [X] T054 [US2] Implement Git `pre-commit` and `pre-push` wrapper installation, conflict detection and preservation in `src/framework_cli/git/hooks.py`.
- [X] T055 [US2] Add CI invocation and blocked-security examples to `.github/workflows/ci.yml` and `specs/001-cli-framework-bootstrap/quickstart.md`.

**Checkpoint**: `framework check` and `framework security scan` produce equivalent
human/JSON reports, block unsafe staged content and distinguish new findings from
legacy baseline findings.

---

## Phase 5: User Story 3 - Install Agent Projections and Instruction Compliance (Priority: P1)

**Goal**: Install Codex CLI and Claude Code projections from one canonical source,
preserve instruction precedence and report modified/conflicted target files.

**Independent Test**: Initialize a fixture with root and nested Markdown
instructions, install both integrations, modify one target projection and verify
precedence, checksums and conflict behavior.

### Tests for User Story 3

- [X] T056 [P] [US3] Add instruction-chain precedence tests in `tests/contract/test_instruction_chain.py` for root, nested and conflicting files.
- [X] T057 [P] [US3] Add Codex projection tests in `tests/integration/test_codex_projection.py` for `.agents/skills/` output, source metadata and checksums.
- [X] T058 [P] [US3] Add Claude projection tests in `tests/integration/test_claude_projection.py` for `.claude/commands/` output, source metadata and checksums.
- [X] T059 [P] [US3] Add locally modified and conflict tests in `tests/integration/test_projection_conflicts.py` ensuring no silent overwrite.

### Implementation for User Story 3

- [X] T060 [US3] Add canonical command and instruction templates under `src/framework_cli/agents/templates/` for initialization, check, security scan and project context.
- [X] T061 [US3] Implement projection manifest, source version and checksum handling in `src/framework_cli/agents/projections.py`.
- [X] T062 [US3] Implement Codex target rendering in `src/framework_cli/agents/codex.py`.
- [X] T063 [US3] Implement Claude Code target rendering in `src/framework_cli/agents/claude.py`.
- [X] T064 [US3] Implement locally modified/conflicted target detection and user-facing resolution reports in `src/framework_cli/agents/conflicts.py`.
- [X] T065 [US3] Integrate interactive Codex/Claude selection and projection installation into `src/framework_cli/commands/init.py`.
- [X] T066 [US3] Add agent projection version checks and update reporting in `src/framework_cli/commands/install.py`.
- [X] T067 [US3] Add end-to-end agent installation coverage to `tests/integration/test_agent_install.py`.

**Checkpoint**: Both supported agents receive equivalent canonical instructions,
the active plan is discoverable, and modified projections are protected.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Verify release behavior, performance, documentation and maintainability.

- [X] T068 [P] Add CLI packaging and release validation to `pyproject.toml` and `.github/workflows/release.yml`.
- [X] T069 [P] Add macOS/Linux subprocess, path and executable-permission coverage in `tests/integration/test_platforms.py`.
- [X] T070 [P] Add incremental-scan performance fixtures and measurements in `tests/integration/test_scan_performance.py`.
- [X] T071 [P] Document command help, exit codes, Git degraded mode and hook conflict recovery in `specs/001-cli-framework-bootstrap/quickstart.md`.
- [X] T072 Run `uv run pytest` and record coverage for `tests/unit/`, `tests/integration/` and `tests/contract/`.
- [X] T073 Run `framework check --format json`, resolve new duplication/complexity findings and record approved baselines in `.framework/quality/baseline.json`.
- [X] T074 Run `framework security scan --format json` against workspace, staged diff and Git history; confirm no secret value appears in artifacts or output.
- [X] T075 Review the final diff, generated files and instruction-chain compliance in `AGENTS.md`, `specs/001-cli-framework-bootstrap/plan.md` and `specs/001-cli-framework-bootstrap/quickstart.md`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; creates the package and test baseline.
- **Foundational (Phase 2)**: Depends on Setup and blocks every user story.
- **User Story 1 (Phase 3)**: Depends on Foundation; provides the MVP initialization flow.
- **User Story 2 (Phase 4)**: Depends on Foundation and the project profile/configuration from US1.
- **User Story 3 (Phase 5)**: Depends on Foundation and the initialization flow from US1.
- **Polish (Phase 6)**: Depends on all three user stories.

### User Story Dependencies

- **US1**: Independent after Phase 2; must complete before US2 and US3 integration tasks.
- **US2**: Can develop core analyzers after Phase 2, but configured execution and fixtures use US1 project profiles.
- **US3**: Can develop projection renderers after Phase 2, but selection and installation integrate with US1.

### Parallel Opportunities

- T003-T008 can run in parallel after T001-T002 where file ownership is separate.
- T009-T012 can run in parallel before foundation implementation.
- T018-T020 can run in parallel because each adapter owns a separate file.
- T027-T030 can run in parallel because they use separate test files.
- T038-T043 can run in parallel because each gate/test concern owns a separate test file.
- T047-T051 can run in parallel after quality models and Git scope interfaces exist.
- T056-T059 can run in parallel because each projection/precedence concern owns a separate test file.
- T062-T063 can run in parallel after the projection contract is complete.
- T068-T071 can run in parallel after the user stories are complete.

## Parallel Example: User Story 2

```text
After T045-T046:
  Worker A: T047 duplication detector + tests in test_quality_rules.py
  Worker B: T048 complexity/God-class metrics + tests in test_quality_rules.py
  Worker C: T049-T051 secret scanner + tests in test_security_scan.py

Integration:
  T052 check orchestration -> T053 security command -> T054 Git hooks
```

## Implementation Strategy

### MVP First (User Story 1 only)

1. Complete Setup and Foundational phases.
2. Complete US1 initialization, detection, confirmation and degraded-mode reporting.
3. Validate the greenfield, brownfield and monorepo fixtures independently.
4. Stop and demonstrate `framework init`, `framework scan` and `framework doctor`.

### Incremental Delivery

1. Add US2 test execution and quality/security gates.
2. Validate blocked `.env`/credential commits and baseline behavior.
3. Add US3 Codex/Claude projections and conflict protection.
4. Run the full quickstart, CI and release checks.

### Definition of Done

- All tasks for the target story are checked and independently testable.
- `pytest` passes for unit, integration and contract suites.
- `framework check` passes with no unjustified new findings.
- `framework security scan` passes without exposing a secret.
- Generated agent files have source/version/checksum metadata.
- `AGENTS.md` and all applicable Markdown instructions were loaded and respected.
