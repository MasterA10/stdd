# Agent Projection Contract

Canonical content lives under `.framework/agents/`. Each projection manifest records:

```yaml
source:
  path: .framework/agents/framework-check/SKILL.md
  version: 0.1.0
  checksum: sha256:...
targets:
  - agent: codex
    path: .agents/skills/framework-check/SKILL.md
  - agent: claude
    path: .claude/commands/framework-check.md
```

Projection rules:

1. The canonical source is the only file edited by framework generation.
2. Target adapters translate front matter, command names and invocation syntax.
3. Existing target files with a mismatched checksum are reported as locally
   modified and are not overwritten silently.
4. Codex and Claude projections MUST preserve the instruction-chain requirement and
   reference the active project plan.
5. Every install/update reports created, updated, skipped, modified and conflicted
   files in both output formats.
