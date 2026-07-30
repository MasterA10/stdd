from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

from .model import ProjectConfig
from .validator import validate_config


def load_config(root: Path) -> ProjectConfig:
    path = root / ".framework" / "project.yml"
    if not path.exists():
        raise FileNotFoundError(path)
    raw = yaml.safe_load(path.read_text()) if yaml else json.loads(path.read_text())
    if not isinstance(raw, dict):
        raise ValueError("project configuration must be a mapping")
    config = ProjectConfig.from_dict(root, raw)
    config.warnings = validate_config(raw, root)
    return config


def save_config(root: Path, config: ProjectConfig) -> Path:
    validate_config(config)
    path = root / ".framework" / "project.yml"
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = config.to_dict()
    path.write_text(yaml.safe_dump(raw, sort_keys=False) if yaml else json.dumps(raw, indent=2))
    return path
