from __future__ import annotations

from pathlib import Path

from .base import Adapter, Detection
from .generic import GenericAdapter
from .javascript import JavaScriptAdapter
from .python import PythonAdapter


IGNORED_PARTS = {".git", ".venv", "venv", "node_modules", ".framework"}


def _has_files(root: Path, pattern: str) -> bool:
    return any(path.is_file() and not IGNORED_PARTS.intersection(path.parts)
               for path in root.rglob(pattern))


def discover_adapters(root: Path) -> list[Adapter]:
    adapters: list[Adapter] = [GenericAdapter()]
    if (root / "pyproject.toml").exists() or _has_files(root, "*.py"):
        adapters.append(PythonAdapter())
    if (root / "package.json").exists() or _has_files(root, "package.json"):
        adapters.append(JavaScriptAdapter())
    return adapters


def detect_project(root: Path) -> dict:
    detections: list[Detection] = []
    adapters = discover_adapters(root)
    for adapter in adapters: detections.extend(adapter.detect(root))
    applications = {"root": {"path": ".", "languages": sorted({d.value for d in detections if d.kind == "language"}),
                              "frameworks": sorted({d.value for d in detections if d.kind == "framework"}),
                              "detections": [d.__dict__ for d in detections]}}
    app_dirs = [p.parent for p in root.rglob("pyproject.toml")
                if p.parent != root and not IGNORED_PARTS.intersection(p.parts)]
    app_dirs += [p.parent for p in root.rglob("package.json")
                 if p.parent != root and not IGNORED_PARTS.intersection(p.parts)]
    for path in sorted(set(app_dirs)):
        if any(path == existing for existing in app_dirs):
            applications.setdefault(path.name, {"path": str(path.relative_to(root)), "languages": [], "frameworks": []})
    return {"adapters": [a.id for a in adapters], "applications": applications,
            "detections": [d.__dict__ for d in detections]}
