# Research: Incremental Session Learning and Agent Handoff

## Decision 1: Append-only project memory with redacted files

**Decision**: Persist session facts as redacted JSONL under
`.framework/learn/events/`, with derived summaries and approved lessons in nearby
versionable files. Keep relationships and fingerprints in the existing SQLite
index.

**Rationale**: JSONL is append-friendly, reviewable in Git and recoverable after a
partial session. SQLite remains the query/index layer rather than the only source
of truth. The project-local scope avoids cross-project contamination.

**Alternatives considered**:

- Global user memory: rejected because lessons could leak between unrelated projects.
- SQLite-only events: rejected because append-only review and Git diffs become less
  transparent.
- External memory service: deferred; it would add credentials, availability and
  synchronization requirements outside this feature.

## Decision 2: Security scan before persistence and versioning

**Decision**: Redact before writing any event, summary, lesson or handoff. Run the
existing deterministic security scanner over generated files before they are
reported as ready for review. Sensitive discoveries create a tombstone and a
rotation/history-cleanup action; Git history is never rewritten automatically.

**Rationale**: The memory is intentionally versionable, so prevention must happen
before the file reaches the working tree. Tombstones preserve auditability without
retaining the secret.

**Alternatives considered**:

- Redact only during export: rejected because the secret could already be committed.
- Automatically rewrite Git history: rejected as destructive and unsafe without
  human approval.
- Allow literal allowlists: rejected by the constitution's fingerprint-only policy.

## Decision 3: Event lifecycle and session identity

**Decision**: Use stable `session_id` and append-only `event_id` values. Normal
start/checkpoint/compaction/resume/close events remain in one session. Importing a
handoff creates a new session linked to the source; only confirmed compaction/resume
continues the original identity.

**Rationale**: This preserves chronology and prevents concurrent agents from
silently writing to the same session. Host adapters can report partial coverage.

**Alternatives considered**:

- Reuse source identity for every import: rejected because audit and concurrency
  become ambiguous.
- Create a new identity for every checkpoint: rejected because it loses session
  continuity.

## Decision 4: Canonical handoff package

**Decision**: Export a package containing a structured document as the import source
and an equivalent Markdown view for people. Include scope, origin, destination,
format version, checksum, redaction report, event coverage and linked evidence.

**Rationale**: A file works with native integrations and generic external agents,
can be reviewed before transfer and remains reproducible without a live API.

**Alternatives considered**:

- Clipboard/stdout-only transfer: rejected because it lacks durable integrity and
  reliable large-context handling.
- Separate native format as canonical for each agent: rejected because it creates
  drift and prevents generic destinations.

## Decision 5: Hybrid quiz generation

**Decision**: `quiz run`, `quiz sync`, schema validation, provenance checks and
storage are deterministic and do not require AI. `quiz generate` may invoke a
configured local command with an explicitly scoped, redacted request package. The
command returns a generation acknowledgment/opaque job identifier to the principal
agent; question content is stored for the quiz command and is not returned in that
orchestration response. A local deterministic fallback can create template-based
questions when no command is available.

**Rationale**: Inference benefits from a configured local agent's contextual reasoning,
while execution and safety must remain predictable and testable. The ack-only
boundary limits context propagation to the principal agent.

**Alternatives considered**:

- AI required for all quiz behavior: rejected by the constitution and offline/CI
  requirements.
- Deterministic generation only: insufficient for nuanced trade-off and business
  rule questions requested by the user.
- Return generated questions to the principal agent: rejected because the requested
  delegation boundary says it only needs creation confirmation.

## Decision 6: Source fingerprints and quiz invalidation

**Decision**: Store source identifiers and fingerprints for every question. Quiz sync
compares current source fingerprints and marks affected questions `needs_review`
without deleting prior attempts.

**Rationale**: This keeps old learning evidence while preventing stale answers from
being treated as current knowledge.

**Alternatives considered**:

- Delete questions on source change: rejected because it loses audit and learning
  history.
- Never invalidate: rejected because it creates false confidence.

## Decision 7: Short lessons and review gate

**Decision**: Store lessons as atomic proposed/approved/rejected revisions with
source evidence, confidence, scope and review metadata. Promotion to permanent
instructions or quality policy always requires an explicit human action.

**Rationale**: Small lessons are easier to study and review; explicit promotion
prevents agent hypotheses from silently changing project governance.
