# Data Model: CLI Framework Foundation

## ProjectProfile

Represents the validated project configuration.

| Field | Type | Rules |
|---|---|---|
| `id` | string | Stable within the project |
| `version` | integer | Schema version, starts at 1 |
| `mode` | enum | `greenfield` or `brownfield` |
| `profile` | enum | `experiment`, `mvp` or `product` |
| `root_path` | path | Absolute path resolved at runtime |
| `platforms` | list | Includes supported target platforms |
| `security_policy` | object | Secret scan and allowlist settings |
| `quality_policy` | object | Thresholds, baseline and severities |
| `agent_integrations` | list | Selected Codex/Claude projections |

One project has one active profile. A new detection result remains proposed until
the user confirms it.

## Application

Represents a project or monorepo application.

| Field | Type | Rules |
|---|---|---|
| `id` | string | Unique within the profile |
| `path` | relative path | Must remain under project root |
| `languages` | list | Detection result with confidence |
| `frameworks` | list | Detection result with confidence |
| `test_suites` | list | Named commands and categories |
| `datastores` | list | Optional detected dependencies |
| `infrastructure` | list | Optional detected tooling |

An application can reference multiple adapters. Paths cannot overlap unless one
application is explicitly declared as a container/monorepo root.

## Adapter

Describes stack-specific capabilities.

| Field | Type | Rules |
|---|---|---|
| `id` | string | Stable adapter identifier |
| `version` | string | Adapter contract version |
| `supported_languages` | list | Detection scope |
| `capabilities` | set | Detection, AST, tests, scripts, static rules |
| `commands` | map | Safe command templates, no shell interpolation by default |

## ScriptDefinition

Represents a deterministic operation.

| Field | Type | Rules |
|---|---|---|
| `id` | string | Stable command identifier |
| `platform` | enum | `macos`, `linux` or `all` |
| `inputs` | schema | Validated arguments/configuration |
| `allowed_paths` | list | Files/directories it may read or write |
| `mutates_code` | boolean | Must be false for check/scan scripts |
| `exit_codes` | map | Contracted result meanings |

## InstructionFile and AgentProjection

`InstructionFile` records an applicable Markdown file, its scope and checksum.
`AgentProjection` records a canonical source, target agent, destination, generated
version, checksum and conflict state. A projection can be `installed`, `outdated`,
`locally_modified` or `conflicted`.

## QualityRule and QualityFinding

`QualityRule` contains an identifier, category, threshold, severity policy and
baseline behavior. `QualityFinding` contains rule, path, line, metric, severity,
fingerprint, status and remediation. Finding states are `open`, `baseline`,
`suppressed`, `resolved` and `error`.

New/modified findings use the active profile severity. Baseline findings remain
visible and cannot silently hide a new finding.

## SecurityScan and SecurityFinding

`SecurityScan` records scan scope, Git commit references, policy version, status and
timestamp. `SecurityFinding` contains path, line, category, non-reversible
fingerprint and remediation state, never the raw secret. A finding in staged or
remote-bound content blocks the safety gate unless it is an explicitly safe example
with a fictitious value.

## GitSnapshot

Records repository availability, branch, base commit, staged commit, remote-bound
diff identity and reachable history scope. It supports degraded mode reporting when
Git is unavailable.

## GeneratedArtifact

Tracks framework-created files such as `.framework/project.yml`, agent projections
and generated reports.

| Field | Type | Rules |
|---|---|---|
| `path` | relative path | Must be inside declared generated destinations |
| `source` | identifier | Canonical template/command source |
| `version` | string | Source version |
| `checksum` | string | Used to detect local edits |
| `state` | enum | `current`, `outdated`, `modified`, `conflict` |

## Core Relationships

```text
ProjectProfile
├── Applications ──> Adapters ──> ScriptDefinitions
├── AgentProjections ──> InstructionFiles
├── QualityPolicy ──> QualityRules ──> QualityFindings
├── SecurityPolicy ──> SecurityScans ──> SecurityFindings
├── GitSnapshots
└── GeneratedArtifacts
```

## Lifecycle

```text
detection proposed -> user confirmed -> profile active
projection installed -> current -> outdated/modified -> conflict or replaced
finding open -> baseline/suppressed/resolved
security finding detected -> blocked -> remediated or explicitly safe example
```
