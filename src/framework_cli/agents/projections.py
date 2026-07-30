from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .integrations import incompatible_integrations, resolve_integration


VERSION = "0.2.0"


def _canonical(root: Path, name: str, template: Path) -> Path:
    target = root / ".framework" / "agents" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_text(template.read_text())
    return target


def _skill_content(content: str, name: str, agent: str) -> str:
    """Add the portable skill envelope expected by skills-based agents."""
    if content.startswith("---\n"):
        return content
    description = f"Run framework {name.replace('-', ' ')} with the local project agent."
    return f"---\nname: {name}\ndescription: {description}\n---\n\n{content.lstrip()}"


def _targets(root: Path, spec, name: str, content: str) -> list[tuple[Path, str]]:
    targets: list[tuple[Path, str]] = []
    skill = spec.skill_path(root, name)
    if skill:
        targets.append((skill, _skill_content(content, name, spec.key)))
    legacy = spec.legacy_path(root, name)
    if legacy:
        targets.append((legacy, content))
    return targets


def _read_manifest(root: Path) -> dict:
    path = root / ".framework" / "agents" / "manifest.json"
    if not path.exists():
        return {"version": VERSION, "projections": [], "conflicts": [], "installed_integrations": []}
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {"version": VERSION, "projections": [], "conflicts": [], "installed_integrations": []}
    return value if isinstance(value, dict) else {"version": VERSION, "projections": [], "conflicts": [], "installed_integrations": []}


def _write_state(root: Path, manifest: dict) -> None:
    directory = root / ".framework" / "agents"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    state = {"version": VERSION, "default_integration": manifest.get("installed_integrations", [None])[0],
             "installed_integrations": manifest.get("installed_integrations", [])}
    (directory / "integration.json").write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")


def install_projections(root: Path, integrations: list[str]) -> dict:
    root = root.resolve()
    template_root = Path(__file__).parent / "templates"
    requested = []
    unsupported = []
    for value in integrations:
        spec = resolve_integration(value)
        if not spec or (not spec.skills_root and not spec.legacy_commands_root):
            unsupported.append(value)
        elif spec.key not in requested:
            requested.append(spec.key)
    conflicts: list[str] = []
    if unsupported:
        return {"created_or_updated": [], "conflicts": [], "unsupported": unsupported,
                "manifest": None}
    manifest = _read_manifest(root)
    installed_before = manifest.get("installed_integrations", [])
    incompatible = incompatible_integrations([*installed_before, *requested])
    if incompatible:
        return {"created_or_updated": [], "conflicts": [f"incompatible:{a}+{b}" for a, b in incompatible],
                "unsupported": [], "manifest": None}
    projections = [item for item in manifest.get("projections", []) if item.get("agent") not in requested]
    files: list[str] = []
    for key in requested:
        spec = resolve_integration(key)
        assert spec is not None
        for template in sorted(template_root.glob("*.md")):
            name = template.stem
            canonical = _canonical(root, name + ".md", template)
            for target, rendered in _targets(root, spec, name, canonical.read_text()):
                target.parent.mkdir(parents=True, exist_ok=True)
                checksum = "sha256:" + hashlib.sha256(rendered.encode()).hexdigest()
                if target.exists():
                    current = "sha256:" + hashlib.sha256(target.read_bytes()).hexdigest()
                    if current != checksum:
                        conflicts.append(str(target.relative_to(root)))
                        continue
                else:
                    target.write_text(rendered)
                files.append(str(target.relative_to(root)))
                projections.append({"source": str(canonical.relative_to(root)), "agent": key,
                                    "path": str(target.relative_to(root)), "version": VERSION,
                                    "checksum": checksum})
    installed = sorted({*manifest.get("installed_integrations", []), *requested})
    manifest = {"version": VERSION, "projections": projections, "conflicts": conflicts,
                "installed_integrations": installed}
    _write_state(root, manifest)
    return {"created_or_updated": files, "conflicts": conflicts, "unsupported": [],
            "installed_integrations": installed,
            "manifest": str((root / ".framework" / "agents" / "manifest.json").relative_to(root))}


def integration_status(root: Path) -> dict:
    root = root.resolve()
    manifest = _read_manifest(root)
    modified: list[str] = []
    missing: list[str] = []
    for item in manifest.get("projections", []):
        path = root / item["path"]
        if not path.exists():
            missing.append(item["path"])
        elif "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest() != item.get("checksum"):
            modified.append(item["path"])
    return {"installed_integrations": manifest.get("installed_integrations", []),
            "modified": modified, "missing": missing,
            "conflicts": manifest.get("conflicts", []), "manifest": manifest}
