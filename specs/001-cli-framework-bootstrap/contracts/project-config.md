# Project Configuration Contract

The user-facing configuration is YAML at `.framework/project.yml`.

```yaml
version: 1
profile: mvp
mode: brownfield

applications:
  backend:
    path: apps/backend
    languages: [python]
    frameworks: [fastapi]
    tests:
      unit:
        command: pytest tests/unit

agent:
  integrations:
    - id: codex
      enabled: true
    - id: claude
      enabled: false

security:
  secret_scan: true
  scan_history: true
  scan_remote_diff: true
  env_files: [.env, .env.*]
  safe_examples: [.env.example, .env.sample, .env.template]
  allowlist: .framework/security/allowlist.yml

quality:
  baseline: .framework/quality/baseline.json
  rules:
    duplicate_block_statements: {threshold: 6, severity: block_new}
    function_logical_lines: {threshold: 50, severity: block_new}
    cognitive_complexity: {threshold: 15, severity: block_new}
    god_class: {threshold: profile_default, severity: block_new}

scripts:
  preferred: auto
```

The CLI MUST validate paths, commands, adapter identifiers and policy values before
writing this file. Unknown keys may be preserved for forward compatibility but MUST
be reported as warnings.
