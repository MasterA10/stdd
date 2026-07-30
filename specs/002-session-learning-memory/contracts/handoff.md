# Handoff Contract

`framework learn handoff export` creates a directory or archive with:

```text
handoff.json       # canonical import source
handoff.md         # equivalent human-readable rendering
manifest.json      # version, scope, checksum, source and target
```

The structured envelope is:

```json
{
  "schema_version": 1,
  "handoff_id": "handoff-opaque",
  "source_session_id": "session-opaque",
  "target": "codex|claude|antigravity|generic|new-session",
  "scope": {"sessions": [], "categories": [], "files": [], "symbols": [], "statuses": ["approved"]},
  "context": {"summary": {}, "lessons": [], "decisions": [], "tasks": [], "evidence": []},
  "redaction": {"count": 0, "types": []},
  "coverage": {"events": "complete", "missing": []},
  "source_checksum": "sha256:...",
  "created_at": "2026-07-30T12:00:00Z"
}
```

Import verifies format, checksum, redaction, applicable instruction chain and
scope before creating a new linked session. Modified packages are rejected or
reported as conflicts. Markdown is never allowed to expand the structured scope.
