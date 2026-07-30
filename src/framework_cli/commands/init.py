from __future__ import annotations

from pathlib import Path

from ..adapters.registry import detect_project
from ..agents.projections import install_projections
from ..config.project import create_profile
from ..git.hooks import install_hooks
from ..git.repository import GitRepository
from ..reporting.models import CommandResult


def init_project(root: Path, *, integration: str | None = None, interactive: bool = False,
                 install_git_hooks: bool = False) -> CommandResult:
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    detection = detect_project(root)
    result = CommandResult("framework init", project={"root": str(root), "detections": detection}, metadata={})
    if interactive and integration is None:
        result.status, result.exit_code = "error", 2
        result.actions.append("Choose an integration with --integration codex or --integration claude")
        return result
    if integration not in {None, "codex", "claude"}:
        result.status, result.exit_code = "error", 2
        result.actions.append("Integration must be codex or claude")
        return result
    config = create_profile(root, detection, integration=integration)
    result.project.update(config.to_dict())
    result.actions.append("Created .framework/project.yml")
    if integration:
        projection = install_projections(root, [integration])
        result.metadata["projections"] = projection
        if projection["conflicts"]:
            result.status, result.exit_code = "error", 4
            result.actions.append("Resolve locally modified projections before reinstalling")
    git = GitRepository(root)
    if git.available:
        result.metadata["git"] = git.snapshot()
        if install_git_hooks:
            result.metadata["hooks"] = install_hooks(root)
    else:
        result.status = "degraded"
        result.metadata["degraded"] = ["history", "diff", "commit protection", "full secret scan"]
    return result
