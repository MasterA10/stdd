from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config.loader import load_config
from ..reporting.models import CommandResult, Finding


def _path(root: Path) -> Path:
    return root / ".framework" / "quality" / "test-approvals.json"


def _read(root: Path) -> dict[str, Any]:
    path = _path(root)
    if not path.exists():
        return {"version": 1, "approvals": {}}
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "approvals": {}}
    return data if isinstance(data, dict) else {"version": 1, "approvals": {}}


def content_hash(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def approve_test(root: Path, test: str, *, behavior: str | None = None) -> CommandResult:
    root = root.resolve()
    path = (root / test).resolve()
    if root not in path.parents or not path.is_file():
        result = CommandResult("framework test approve", status="error", exit_code=2)
        result.actions.append("Test file does not exist inside project root")
        return result
    try:
        config = load_config(root)
        profile = config.profile.lower()
    except FileNotFoundError:
        profile = "mvp"
    data = _read(root)
    rel = str(path.relative_to(root))
    data.setdefault("version", 1); data.setdefault("approvals", {})
    data["approvals"][rel] = {"path": rel, "hash": content_hash(path),
                               "profile": profile, "behavior": behavior or "",
                               "approved_at": datetime.now(timezone.utc).isoformat()}
    target = _path(root); target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    return CommandResult("framework test approve", metadata={"path": rel, "profile": profile,
                                                               "hash": data["approvals"][rel]["hash"]})


def approval_findings(root: Path) -> list[Finding]:
    root = root.resolve(); data = _read(root); findings: list[Finding] = []
    try:
        profile = load_config(root).profile.lower()
    except FileNotFoundError:
        profile = "mvp"
    severity = "warning" if profile in {"experiment", "experimental"} else "block"
    for rel, record in data.get("approvals", {}).items():
        path = root / rel
        if not path.exists():
            findings.append(Finding("TEST-APPROVAL-MISSING", "tests", severity, "open", rel, None,
                                    "approved-test-missing", "An approved test was removed",
                                    "Restore the test or explicitly update the approval", {}, rel))
            continue
        current = content_hash(path)
        if current != record.get("hash"):
            findings.append(Finding("TEST-APPROVAL-CHANGED", "tests", severity, "open", rel, None,
                                    "approved-test-modified", "An approved test changed after approval",
                                    "Review the behavior and run framework test approve again", {"expected": record.get("hash"), "actual": current}, rel))
    return findings


def approved_paths(root: Path) -> list[Path]:
    """Return approved test files that an agent must treat as read-only."""
    root = root.resolve()
    data = _read(root)
    return [root / rel for rel in data.get("approvals", {}) if (root / rel).is_file()]


def approved_hashes(root: Path) -> dict[str, str]:
    """Snapshot approved test hashes for agent preflight and postflight checks."""
    root = root.resolve()
    data = _read(root)
    return {rel: content_hash(root / rel) for rel in data.get("approvals", {})
            if (root / rel).is_file()}
