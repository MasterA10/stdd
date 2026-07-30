# Quiz Contract

Commands:

```text
framework learn quiz generate [--provider local|external] [--scope SCOPE]
framework learn quiz run [--category CATEGORY] [--count N]
framework learn quiz sync
framework learn quiz export --format yaml|json|markdown
```

Question shape:

```json
{
  "question_id": "question-opaque",
  "revision": 1,
  "category": "trade-off",
  "prompt": "Which boundary protects this rule?",
  "options": ["A", "B", "C"],
  "correct_option": "B",
  "explanation": "Short explanation under 80 words.",
  "sources": [{"kind": "symbol", "id": "module.function", "fingerprint": "sha256:..."}],
  "status": "current",
  "provenance": {"provider": "external", "job_id": "job-opaque", "version": "1"}
}
```

`quiz run` does not require a provider and does not reveal the answer before
submission. `quiz sync` marks changed sources as `needs_review` while preserving
attempt history.
