from __future__ import annotations

from pathlib import Path
from typing import Any

from .model import ProjectConfig


def validate_config(config: ProjectConfig | dict[str, Any], root: Path | None = None) -> list[str]:
    warnings: list[str] = []
    if isinstance(config, dict):
        known = {"version", "profile", "mode", "root_path", "platforms", "applications", "agent", "security", "quality", "documentation", "scripts", "learn"}
        warnings.extend(f"unknown configuration key: {x}" for x in config.keys() - known)
        config = ProjectConfig.from_dict(root or Path.cwd(), config)
    if config.version != 1:
        raise ValueError("unsupported configuration version")
    if config.profile not in {"experiment", "mvp", "product"}:
        raise ValueError("profile must be experiment, mvp or product")
    if config.mode not in {"greenfield", "brownfield"}:
        raise ValueError("mode must be greenfield or brownfield")
    if not set(config.agent_integrations).issubset({"codex", "claude"}):
        raise ValueError("agent integrations must be codex or claude")
    if not isinstance(config.learn, dict):
        raise ValueError("learn must be a mapping")
    if not isinstance(config.learn.get("enabled", False), bool):
        raise ValueError("learn.enabled must be boolean")
    retention_days = config.learn.get("retention_days", 365)
    if not isinstance(retention_days, int) or isinstance(retention_days, bool) or retention_days < 0:
        raise ValueError("learn.retention_days must be a non-negative integer")
    for name, app in config.applications.items():
        if not isinstance(app, dict) or "path" not in app:
            raise ValueError(f"application {name!r} needs a path")
        app_path = (Path(config.root_path) / app["path"]).resolve()
        if Path(config.root_path).resolve() not in app_path.parents and app_path != Path(config.root_path).resolve():
            raise ValueError(f"application path escapes project root: {name}")
    return warnings
