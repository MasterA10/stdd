# Command-Line Question Generation Contract

Question generation is delegated only to an explicitly configured local command
such as Codex, Claude, Cloud or Antigravity. There is no network provider/API in
the core. The framework writes a redacted request package and invokes the command
without a shell; the executable receives the package path.

The request package contains a redacted, explicitly scoped request:

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

It MUST NOT contain the original context, prompt, question text, answers, command
stdout or command stderr. The command adapter validates and stores generated
questions behind the job. A local deterministic fallback may create candidate
questions when the executable is unavailable. Credentials are never placed in the
request, response, command arguments or learn memory.
