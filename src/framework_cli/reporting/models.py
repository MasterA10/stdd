from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Finding:
    id: str
    category: str
    severity: str
    status: str
    path: str | None
    line: int | None
    rule: str
    message: str
    remediation: str = ""
    metric: dict[str, Any] = field(default_factory=dict)
    fingerprint: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CommandResult:
    command: str
    status: str = "passed"
    exit_code: int = 0
    project: dict[str, Any] = field(default_factory=dict)
    findings: list[Finding | dict[str, Any]] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    children: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        def convert(item):
            return item.to_dict() if isinstance(item, Finding) else item
        return {"schema_version": 1, "command": self.command, "status": self.status,
                "exit_code": self.exit_code, "project": self.project,
                "findings": [convert(x) for x in self.findings], "actions": self.actions,
                "metadata": self.metadata, "children": self.children}

    def add(self, finding: Finding | dict[str, Any]) -> None:
        self.findings.append(finding)
        severity = finding.severity if isinstance(finding, Finding) else finding.get("severity")
        if severity in {"block", "error"}:
            self.status, self.exit_code = "blocked", 1
        elif severity == "warning" and self.status == "passed":
            self.status = "warned"
