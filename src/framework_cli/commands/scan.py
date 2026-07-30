from __future__ import annotations

from pathlib import Path

from ..adapters.registry import detect_project
from ..reporting.models import CommandResult


def scan_project(root: Path) -> CommandResult:
    detection = detect_project(root.resolve())
    return CommandResult("framework scan", project={"root": str(root.resolve()), "detections": detection})
