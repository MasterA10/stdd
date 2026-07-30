from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Rule:
    id: str
    category: str
    threshold: float
    severity: str = "block_new"

    def severity_for(self, baseline: bool) -> str:
        if baseline: return "warning"
        return "block" if self.severity in {"block", "block_new"} else self.severity


def configured_rules(config: dict[str, Any] | None = None) -> list[Rule]:
    raw = (config or {}).get("rules", {})
    defaults = {
        "duplicate_block_statements": ("duplication", 6),
        "function_logical_lines": ("complexity", 50),
        "cognitive_complexity": ("complexity", 15),
        "god_class": ("god_class", 15),
    }
    rules = []
    for rule_id, (category, default) in defaults.items():
        value = raw.get(rule_id, {}) or {}
        threshold = value.get("threshold", default)
        if not isinstance(threshold, (int, float)): threshold = default
        rules.append(Rule(rule_id, category, float(threshold), value.get("severity", "block_new")))
    return rules
