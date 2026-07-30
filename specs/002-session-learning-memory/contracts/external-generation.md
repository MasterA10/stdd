# External Question Generation Contract

The provider receives a redacted, explicitly scoped request:

```json
{
  "schema_version": 1,
  "job_id": "job-opaque",
  "session_id": "session-opaque",
  "scope": {"files": [], "symbols": [], "categories": []},
  "redacted_context": {},
  "question_constraints": {"options": 3, "max_options": 5, "explanation_words": 80}
}
```

The orchestration response to the principal agent is acknowledgment-only:

```json
{"status": "created|failed|partial", "job_id": "job-opaque"}
```

It MUST NOT contain the original context, prompt, question text, answers or
provider output. The provider adapter validates and stores generated questions
behind the job. A local deterministic fallback may create candidate questions when
the provider is unavailable. Provider credentials are never placed in the request,
response or learn memory.
