# Quality and Security Report Contract

Every finding uses the same shape in text and JSON:

```json
{
  "id": "SEC-0001",
  "category": "security|duplication|complexity|god_class|type|test|instruction",
  "severity": "info|warning|block|error",
  "status": "open|baseline|suppressed|resolved",
  "path": "src/example.py",
  "line": 42,
  "rule": "secret-provider-token",
  "metric": {"name": "entropy", "value": 4.9, "threshold": 4.5},
  "fingerprint": "sha256:...",
  "message": "Sensitive value detected; value redacted",
  "remediation": "Move the value to a secret manager and rotate it",
  "evidence": {"git_ref": "HEAD", "source": "staged_diff"}
}
```

The report MUST never include the matched secret, full assignment value, private key
body or a reversible encoding of it. A `block` finding produces exit code `1`.
Baseline findings remain visible and follow the profile severity policy.
