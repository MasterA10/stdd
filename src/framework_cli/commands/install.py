from __future__ import annotations

from pathlib import Path

from ..agents.projections import install_projections
from ..reporting.models import CommandResult


def install(root: Path, integration: str) -> CommandResult:
    if integration not in {"codex", "claude"}:
        return CommandResult("framework install", "error", 2, actions=["Use --integration codex or --integration claude"])
    data = install_projections(root.resolve(), [integration])
    if data["conflicts"]:
        return CommandResult("framework install", "error", 4, metadata=data, actions=["Resolve locally modified projections before reinstalling"])
    return CommandResult("framework install", metadata=data)
