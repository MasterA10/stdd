# External Quiz Generation Projection

Before delegating question generation, load the complete applicable instruction
chain (`AGENTS.md`, `CLAUDE.md`, `CLOUD.md`, `GEMINI.md` and local projections).
Only explicitly scoped, redacted context may be sent to the provider. Never send
`.env` values, credentials, raw prompts or provider credentials.

The principal agent receives only `{status, job_id}`. It must not receive the
context, generated questions, answers or provider output in the orchestration
response. Quiz storage, validation, synchronization and execution remain local
and deterministic when the provider is unavailable.
