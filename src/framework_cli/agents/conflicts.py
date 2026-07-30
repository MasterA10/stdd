from __future__ import annotations

from pathlib import Path

from .projections import install_projections


def detect_conflicts(root: Path) -> list[str]:
    manifest = root / ".framework" / "agents" / "manifest.json"
    if not manifest.exists(): return []
    import json, hashlib
    data = json.loads(manifest.read_text())
    conflicts = []
    for item in data.get("projections", []):
        path = root / item["path"]
        if path.exists() and "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest() != item["checksum"]:
            conflicts.append(item["path"])
    return conflicts
