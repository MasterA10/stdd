from __future__ import annotations

import hashlib
import json
from pathlib import Path


VERSION = "0.1.0"


def _canonical(root: Path, name: str, template: Path) -> Path:
    target = root / ".framework" / "agents" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists(): target.write_text(template.read_text())
    return target


def install_projections(root: Path, integrations: list[str]) -> dict:
    root = root.resolve()
    template_root = Path(__file__).parent / "templates"
    mapping = {"codex": (root / ".agents" / "skills", "SKILL.md"),
               "claude": (root / ".claude" / "commands", "command.md")}
    files, conflicts = [], []
    manifest = []
    for integration in integrations:
        destination, filename = mapping[integration]
        destination.mkdir(parents=True, exist_ok=True)
        for template in sorted(template_root.glob("*.md")):
            name = template.stem
            canonical = _canonical(root, name + ".md", template)
            content = template.read_text()
            checksum = hashlib.sha256(content.encode()).hexdigest()
            target = destination / name / filename if integration == "codex" else destination / f"{name}.md"
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() != checksum:
                conflicts.append(str(target.relative_to(root)))
                continue
            target.write_text(content)
            files.append(str(target.relative_to(root)))
            manifest.append({"source": str(canonical.relative_to(root)), "agent": integration, "path": str(target.relative_to(root)), "version": VERSION, "checksum": "sha256:" + checksum})
    manifest_path = root / ".framework" / "agents" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({"version": VERSION, "projections": manifest, "conflicts": conflicts}, indent=2))
    return {"created_or_updated": files, "conflicts": conflicts, "manifest": str(manifest_path.relative_to(root))}
