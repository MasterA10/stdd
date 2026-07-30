from __future__ import annotations

from pathlib import Path

from ..config.model import ProjectConfig
from ..reporting.models import CommandResult
from .baseline import load_baseline
from .complexity import find_complexity
from .duplication import find_duplicates
from .god_class import find_god_classes
from .rules import configured_rules
from ..testing.approval import approval_findings


class QualityEngine:
    def __init__(self, root: Path, config: ProjectConfig | None = None):
        self.root = root.resolve()
        self.config = config

    def run(self) -> CommandResult:
        raw = self.config.quality if self.config else {}
        rules = {r.id: r for r in configured_rules(raw)}
        result = CommandResult("framework check", project={"root": str(self.root), "profile": self.config.profile if self.config else "mvp"})
        findings = []
        findings.extend(find_duplicates(self.root, int(rules["duplicate_block_statements"].threshold)))
        findings.extend(find_complexity(self.root, int(rules["function_logical_lines"].threshold), int(rules["cognitive_complexity"].threshold)))
        findings.extend(find_god_classes(self.root, int(rules["god_class"].threshold)))
        baseline_path = self.root / (raw.get("baseline", ".framework/quality/baseline.json") if raw else ".framework/quality/baseline.json")
        baseline = load_baseline(baseline_path)
        for finding in findings:
            if finding.fingerprint in baseline:
                finding.status, finding.severity = "baseline", "warning"
            result.add(finding)
        for finding in approval_findings(self.root):
            result.add(finding)
        return result
