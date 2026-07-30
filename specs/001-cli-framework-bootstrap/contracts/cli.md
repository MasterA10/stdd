# CLI Contract

## Common Options

All commands support, where applicable:

- `--format text|json`: choose human or structured output; default is `text` in
  interactive terminals and `json` in explicit automation.
- `--non-interactive`: disables prompts. Commands requiring a decision MUST fail
  with exit code `2` unless the required option is supplied.
- `--no-color`: disables terminal color.
- `--verbose`: adds diagnostic metadata but never prints secret values.

## Commands

### `framework version`

Returns the installed CLI version, source/release identity and supported platform.

### `framework init [PATH]`

Options:

- `--here`: initialize the current directory.
- `--from PATH`: use a requirements description as an input proposal.
- `--integration codex|claude`: required with `--non-interactive`.

Interactive mode presents detection and agent integration choices before writing
configuration or projections. It may create only declared `.framework` artifacts
and approved agent projections. In a Git repository it also asks to install
`pre-commit` and `pre-push` wrappers that run the security and quality gates. Existing
hooks MUST be preserved and conflicts MUST be reported instead of overwritten.

### `framework scan [PATH]`

Analyzes or refreshes detection and shows a diff before changing project
configuration. It does not modify application source code.

### `framework doctor`

Checks runtime, Git, `uv`, adapter availability, permissions, test commands and
generated artifacts. It is read-only.

### `framework test [run]`

Executes configured test suites and returns the aggregate status. Individual runner
output is preserved as structured child results.

### `framework check`

Runs configured tests and quality/security gates as selected by the profile. It
returns findings with path, line, rule, metric, severity and remediation.

### `framework security scan`

Runs the secret-specific gate over workspace, tracked files, staged content,
remote-bound diff and reachable history. It blocks unsafe commit/push/CI content and
redacts every matched value.

## Exit Codes

| Code | Meaning |
|---:|---|
| 0 | Successful execution; warnings may be present |
| 1 | Tests, quality rules or security policy failed |
| 2 | Invalid usage or missing non-interactive decision |
| 3 | Environment unavailable or unsupported platform |
| 4 | Safety conflict, locally modified generated file or unresolved instruction conflict |

## JSON Envelope

```json
{
  "schema_version": 1,
  "command": "framework check",
  "status": "passed|warned|blocked|error|degraded",
  "exit_code": 0,
  "project": {"root": ".", "profile": "mvp"},
  "findings": [],
  "actions": [],
  "metadata": {"git": {"available": true}}
}
```
