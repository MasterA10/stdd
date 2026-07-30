# Quickstart: Incremental Session Learning and Agent Handoff

## Enable and capture a session

Learning is optional. Enable it in the project profile, then use explicit commands
or host hooks:

```yaml
# .framework/project.yml
learn:
  enabled: true
  retention_days: 365
  provider: local
  redaction:
    enabled: true
```

```bash
framework learn start
framework learn checkpoint
framework learn
framework learn close
```

The command writes redacted append-only records under `.framework/learn/` and shows
the files changed. It never creates a Git commit. Review the diff and run the
security gate before committing:

```bash
framework security scan
git diff -- .framework/learn/
git add .framework/learn/
git commit -m "docs: record reviewed learning"
```

Events are associated with local date, normalized timestamp, session, branch,
worktree, agent, tasks, files/symbols and evidence. If a host lacks hooks, the
summary reports partial coverage and uses explicit checkpoints, commits and gates.

## Review lessons

```bash
framework learn review
```

Approve, reject or edit individual short lessons. Promotion to `AGENTS.md`,
quality policy or other permanent project rules is always explicit.

## Export and import a handoff

```bash
framework learn handoff export --target generic --format package
framework learn handoff import .framework/learn/handoffs/<handoff-id>/handoff.json
```

The package contains `handoff.json` as the import source and `handoff.md` as the
review view. It is scoped, checksummed and redacted. Importing it creates a new
session linked to the source; compact/resume events retain the original session ID.

## Generate and run the knowledge quiz

```bash
framework learn quiz generate --provider external --scope session
framework learn quiz run --count 10
framework learn quiz sync
framework learn quiz export --format yaml
```

Run the deterministic verification suite before reviewing a commit:

```bash
uv run pytest
uv run framework check --format json
uv run framework security scan --format json
```

The equivalent nested form is `framework learn quiz ...`; `framework quiz ...` is
also accepted for scripts that prefer a top-level command.

An external provider may infer questions from redacted session context. The
principal agent receives only `created|partial|failed` and an opaque job ID. The
questions remain in the local quiz store for `quiz run`. The quiz can be run and
synchronized without any provider; a local fallback may create candidate questions.

Questions are short, have 3–5 options, one correct answer, a brief explanation and
source fingerprints. Source changes mark questions `needs_review` without deleting
past attempts.

## Safety and failure behavior

- `.env`, credentials, prompts and sensitive values are redacted before persistence.
- A secret found after persistence is removed from the working tree and produces a
  redacted tombstone with rotation and history-cleanup guidance.
- Handoff conflicts, invalid checksums and instruction conflicts stop import.
- Learn/quiz failure never blocks tests, quality gates, commits, pushes or CI.
