from __future__ import annotations

from typing import Any

from .models import CommandResult


def aggregate_children(command: str, children: list[dict[str, Any]], project: dict[str, Any] | None = None) -> CommandResult:
    result = CommandResult(command=command, project=project or {}, children=children)
    for child in children:
        if child.get("status") in {"failed", "blocked", "error"} or child.get("exit_code", 0) != 0:
            result.status, result.exit_code = "blocked", 1
        elif child.get("status") in {"unavailable", "degraded"} and result.status == "passed":
            result.status = "degraded"
    return result
