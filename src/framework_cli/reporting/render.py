from __future__ import annotations

import json

from .models import CommandResult


def render(result: CommandResult, fmt: str = "text") -> str:
    if fmt == "json":
        return json.dumps(result.to_dict(), indent=2, sort_keys=True)
    lines = [f"{result.command}: {result.status} (exit {result.exit_code})"]
    for finding in result.findings:
        data = finding.to_dict() if hasattr(finding, "to_dict") else finding
        location = f"{data.get('path') or '<project>'}:{data.get('line') or 0}"
        lines.append(f"- [{data.get('severity')}] {location} {data.get('rule')}: {data.get('message')}")
    lines.extend(f"Action: {x}" for x in result.actions)
    return "\n".join(lines)
