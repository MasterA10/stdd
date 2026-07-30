# Quickstart: CLI Framework Foundation

## Persistent Installation

Install a released version into the user tool environment:

```bash
uv tool install framework-cli==0.1.0
framework version
```

The release process may also install the package directly from a pinned GitHub
release reference:

```bash
uv tool install framework-cli \
  --from git+https://github.com/ORG/REPOSITORY.git@v0.1.0
```

## One-Time Bootstrap

To try a release without changing the persistent installation:

```bash
uvx --from git+https://github.com/ORG/REPOSITORY.git@v0.1.0 \
  framework init --here
```

The repository URL is supplied by the project release metadata. Always pin a
release in CI and automation.

## Initialize a Project

```bash
framework init --here
```

The interactive flow:

1. Detects the project and presents the proposed configuration.
2. Lets the user correct detections.
3. Asks whether to install Codex CLI or Claude Code projections.
4. Writes only approved `.framework` and agent projection files.

For automation, provide the integration explicitly:

```bash
framework init --here --non-interactive --integration codex --format json
```

## Inspect and Check

```bash
framework doctor
framework scan
framework test
framework check
framework security scan
framework check --format json > framework-check.json
```

If Git is unavailable, `init` can create a basic configuration but reports the
history, diff, commit protection and full secret-scanning capabilities as degraded.

## Development Setup

```bash
git clone <repository-url>
cd <repository-directory>
uv sync
uv run pytest
uv run framework version
```

Before a commit or push, run `framework security scan`; any `.env` file or detected
credential in the versioned content must be removed or replaced by a fictitious
example value. In a Git repository, `framework init` can install pre-commit and
pre-push wrappers that enforce these checks automatically without overwriting
existing hooks.
