# Data Model: Incremental Session Learning and Agent Handoff

## Session

| Field | Type | Rules |
|---|---|---|
| `session_id` | string | Stable unique identifier; imported sessions receive a new ID |
| `parent_session_id` | string/null | Source session for handoff imports |
| `status` | enum | `active`, `checkpointed`, `compacted`, `resumed`, `closed`, `incomplete` |
| `local_date` | date | User-facing local calendar date |
| `started_at` / `ended_at` | timestamp/null | Normalized timestamps |
| `agent` / `host` | string | Provider/host identity, never raw prompt |
| `branch` / `worktree` | string | Git context when available |
| `commit_base` | string/null | Base commit or degraded marker |
| `coverage` | object | Event capabilities and partial fallback evidence |

## LearningEvent

| Field | Type | Rules |
|---|---|---|
| `event_id` | string | Unique, append-only |
| `session_id` | string | Required parent |
| `type` | enum | `start`, `checkpoint`, `compacted`, `resumed`, `close`, `tombstone` |
| `observed_at` | timestamp | Normalized event time |
| `payload` | object | Redacted facts only |
| `tasks` / `files` / `symbols` | lists | Evidence references, paths are project-relative |
| `commands` / `gates` | lists | Redacted command/result metadata |
| `evidence` | list | Commit, diff, test, gate or decision references |
| `fingerprint` | string | Non-reversible event identity |

Events are append-only. Corrections and removals create a later event; no event is
silently overwritten.

## Lesson

| Field | Type | Rules |
|---|---|---|
| `lesson_id` | string | Stable across revisions |
| `revision` | integer | Increases on review/edit |
| `status` | enum | `proposed`, `approved`, `rejected`, `expired` |
| `title` | string | Short atomic idea |
| `content` | string/list | Maximum three bullets or 80 words |
| `source_events` | list | Required evidence |
| `confidence` | number | 0..1 and explicitly marked inference when applicable |
| `scope` | object | Project, branch, symbol, rule or process scope |
| `review` | object | Reviewer, date, decision and re-evaluation condition |

## HandoffPackage

| Field | Type | Rules |
|---|---|---|
| `handoff_id` | string | Unique package identity |
| `format_version` | string | Compatible import version |
| `source_session_id` | string | Immutable source |
| `target` | string | Agent/host/new-session/generic |
| `scope` | object | Selected sessions, categories, files, symbols and statuses |
| `structured_path` / `markdown_path` | paths | Structured source plus equivalent view |
| `checksum` | string | Integrity of structured content |
| `redaction` | object | Counts/types/actions, never raw values |
| `coverage` | object | Captured and missing events |
| `created_at` | timestamp | Export timestamp |

Import creates a new Session with `parent_session_id`; checksum, version, scope and
instruction-chain conflicts must be checked before persistence.

## KnowledgeQuestion

| Field | Type | Rules |
|---|---|---|
| `question_id` | string | Stable opaque identity |
| `revision` | integer | New source/question revision |
| `category` | enum | Architecture, modularization, practice, trade-off, business rule, test, security or operation |
| `prompt` | string | Short question |
| `options` | list | 3..5 choices |
| `correct_option` | string | Exactly one; hidden until submission |
| `explanation` | string | At most 80 words |
| `difficulty` | enum | `easy`, `medium`, `hard` |
| `sources` | list | Stable symbol/rule/test/decision IDs and fingerprints |
| `status` | enum | `current`, `needs_review`, `rejected`, `archived` |
| `provenance` | object | deterministic/external provider, job ID, version and scope |

## QuestionGenerationJob

| Field | Type | Rules |
|---|---|---|
| `job_id` | string | Opaque ID returned to principal agent |
| `session_id` | string | Redacted source context |
| `provider` | string | External adapter or local fallback |
| `status` | enum | `created`, `running`, `completed`, `partial`, `failed` |
| `scope` | object | Authorized context only |
| `question_ids` | list | Stored questions, not returned in principal-agent acknowledgment |
| `error` | object/null | Redacted failure metadata |

## QuizAttempt

| Field | Type | Rules |
|---|---|---|
| `attempt_id` | string | Unique attempt |
| `session_id` | string | Session in which proof runs |
| `question_revision` | string | Exact revision presented |
| `answer` / `correct` | value/bool | Stored after submission |
| `confidence` | number/null | Optional self-assessment |
| `submitted_at` | timestamp | Required |

## State Transitions

```text
Session active -> checkpointed -> compacted -> resumed -> closed
Session active/checkpointed -> incomplete (abrupt termination)
Handoff exported -> validated -> imported as new linked session
Lesson proposed -> approved/rejected -> expired
Question current -> needs_review -> current (new revision) / archived
Generation job created -> running -> completed/partial/failed
```
