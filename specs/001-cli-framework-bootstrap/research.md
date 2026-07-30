# Research: CLI Framework Foundation

## Decision 1: Python 3.11+ with uv

**Decision**: Implement the core CLI as a Python 3.11+ package managed and
distributed with `uv`.

**Rationale**: This matches the installation choice in the specification, works
on macOS/Linux, provides mature filesystem, subprocess, AST, SQLite and JSON
support in the standard library, and allows one-time or persistent execution.

**Alternatives considered**:

- Node.js/TypeScript: viable, but not selected because the project already chose
  the Python/uv distribution model.
- Rust/Go: strong standalone distribution, but increases initial implementation
  and adapter integration cost.
- Shell-only CLI: insufficient for structured indexing, AST analysis and portable
  reports.

## Decision 2: Small dependency surface

**Decision**: Use `argparse`, `pathlib`, `subprocess`, `sqlite3`, `json`, `tomllib`
and `ast` from Python where applicable. Use `PyYAML` for the human-editable
project configuration and `pytest` as a development dependency.

**Rationale**: Deterministic commands should remain available without an agent or
large runtime. Native subprocess execution lets each adapter use the project’s
own test runner and analyzer.

**Alternatives considered**:

- A full CLI framework: deferred until command help/validation complexity proves
  it necessary.
- A mandatory external scanner binary: rejected for the foundation because it
  would make installation and CI less portable; adapters may add optional tools.

## Decision 3: YAML configuration and SQLite index

**Decision**: Store the user-facing project profile in `.framework/project.yml`
and the queryable symbol/quality index in `.framework/index.db`.

**Rationale**: YAML is reviewable and editable; SQLite supports relationships,
incremental scans and deterministic local queries without a service dependency.

**Alternatives considered**:

- JSON-only configuration: less readable for the nested project profile.
- A remote database: out of scope for a local developer tool.
- YAML-only index: insufficient for efficient symbol and finding queries.

## Decision 4: Adapter boundary

**Decision**: Define a common adapter protocol for detection, symbol extraction,
test commands, script generation and static rules. The foundation ships generic,
Python and JavaScript/TypeScript adapters; other stacks use the generic detector
until their adapters are added.

**Rationale**: The core orchestrator remains stable while stack-specific behavior
stays isolated. The foundation can recognize more technologies than it can deeply
analyze without pretending that all detections have equal confidence.

**Alternatives considered**:

- Implement every listed language immediately: rejected as too broad for the
  foundation and likely to produce shallow or inconsistent analyzers.
- Let agents infer stack behavior: rejected for predictable detection and quality
  gates.

## Decision 5: Layered security scanning

**Decision**: Combine effective `.gitignore` checks, Git tracked/staged/remotable
file inspection, known provider patterns, sensitive assignment names, private-key
headers and entropy checks. Store only redacted findings and non-reversible
fingerprints.

**Rationale**: No single pattern catches all secrets. Layering improves coverage
while preserving deterministic behavior and allowing adapter-specific rules.

**Alternatives considered**:

- Regex-only scanning: insufficient for entropy and provider-specific formats.
- Agent-only review: nondeterministic and unsafe for secret handling.
- Ignore `.env` only: does not catch hardcoded keys or secrets in arbitrary files.

## Decision 6: Canonical agent projections

**Decision**: Keep canonical commands and instructions in `.framework/agents` and
project them into Codex CLI and Claude Code formats. Every generated file records
its source, target, version and checksum.

**Rationale**: One source prevents drift while allowing each agent to receive its
native file layout. Conflicts or locally modified projections must be reported
before replacement.

**Alternatives considered**:

- Maintain independent prompts per agent: rejected because behavior would drift.
- Install only one universal Markdown file: insufficient for agent-specific
  command discovery and invocation.

## Decision 7: Git hook enforcement

**Decision**: When initializing a Git repository, ask whether to install
`pre-commit` and `pre-push` wrappers that invoke the deterministic security and
quality commands. Existing hooks are never overwritten; a conflict is reported
and the user receives the manual command to run.

**Rationale**: A CLI command alone cannot reliably prevent a user or CI job from
committing an unsafe `.env` file. Hooks provide local enforcement while the same
commands remain available for CI. Preserving existing hooks avoids silently
changing a project’s workflow.

**Alternatives considered**:

- Replace existing hooks: rejected because it can discard project-specific checks.
- Only document `framework security scan`: insufficient for the requested commit
  protection.
- Set a global Git hooks path: rejected because it changes repositories outside the
  project scope.
