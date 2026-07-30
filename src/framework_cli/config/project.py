from __future__ import annotations

from pathlib import Path
from typing import Any

from .model import ProjectConfig
from .loader import save_config


def create_profile(root: Path, detections: dict[str, Any], *, profile: str = "mvp",
                   integration: str | None = None) -> ProjectConfig:
    mode = "greenfield" if not any(root.iterdir()) else "brownfield"
    config = ProjectConfig.default(root, mode=mode)
    config.profile = profile
    config.applications = detections.get("applications", {})
    if integration:
        config.agent_integrations = [integration]
    config.security["secret_scan"] = True
    config.quality["rules"] = config.quality.get("rules", {})
    save_config(root, config)
    return config
