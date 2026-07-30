# Learn Event Contract

Commands:

```text
framework learn
framework learn start
framework learn checkpoint
framework learn resume [SESSION_ID]
framework learn close
framework learn review
framework learn export --format json|markdown
```

Every command returns the common result envelope. Learn writes only redacted
project-relative records under `.framework/learn/`, displays changed files and
never creates a Git commit. When disabled, commands return `status=disabled` and
exit code 0.

Event shape:

```json
{
  "schema_version": 1,
  "session_id": "session-opaque",
  "event_id": "event-opaque",
  "type": "checkpoint",
  "local_date": "2026-07-30",
  "observed_at": "2026-07-30T12:00:00Z",
  "agent": "codex",
  "host": "codex-cli",
  "branch": "feature/example",
  "worktree": ".",
  "tasks": [],
  "files": [],
  "symbols": [],
  "commands": [],
  "gates": [],
  "observations": [],
  "inferences": [],
  "evidence": [],
  "redaction": {"count": 0},
  "coverage": {"hooks": "partial"}
}
```

The file is append-only. Corrections use a later event or tombstone.
