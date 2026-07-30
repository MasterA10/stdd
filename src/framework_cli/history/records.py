from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..learn.redaction import redact_record


def _identifier(prefix: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{prefix}-{stamp}"


def _write(root: Path, identifier: str, payload: dict[str, Any]) -> Path:
    clean, _ = redact_record(payload)
    directory = root / ".framework" / "history"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{identifier}.json"
    if path.exists():
        suffix = 2
        while (directory / f"{identifier}-{suffix}.json").exists():
            suffix += 1
        path = directory / f"{identifier}-{suffix}.json"
    path.write_text(json.dumps(clean, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return path


def record_bug(root: Path, *, description: str, regression_test: str | None,
               symbols: list[str] | None = None, evidence: dict[str, Any] | None = None,
               status: str = "recorded", git_context: dict[str, Any] | None = None) -> Path:
    identifier = _identifier("BUG")
    payload = {"schema_version": 1, "id": identifier, "type": "bug",
               "status": status, "created_at": datetime.now(timezone.utc).isoformat(),
               "problem": description, "symbols": symbols or [],
               "regression_test": regression_test, "evidence": evidence or {},
               "git": git_context or {}}
    return _write(root.resolve(), identifier, payload)


def record_change(root: Path, *, operation: str, description: str,
                  tests: list[str] | None = None, status: str = "recorded",
                  git_context: dict[str, Any] | None = None,
                  behavior_before: str | None = None,
                  behavior_after: str | None = None) -> Path:
    identifier = _identifier("CHANGE")
    payload = {"schema_version": 1, "id": identifier, "type": "behavior-change",
               "status": status, "created_at": datetime.now(timezone.utc).isoformat(),
               "operation": operation, "description": description,
               "tests": tests or [], "behavior_before": behavior_before,
               "behavior_after": behavior_after, "git": git_context or {}}
    return _write(root.resolve(), identifier, payload)


def record_tradeoff(root: Path, *, description: str, analysis: dict[str, Any],
                    agent: str | None, status: str, git_context: dict[str, Any] | None = None) -> Path:
    identifier = _identifier("DECISION")
    payload = {"schema_version": 1, "id": identifier, "type": "tradeoff",
               "status": status, "created_at": datetime.now(timezone.utc).isoformat(),
               "description": description, "analysis": analysis, "agent": agent,
               "git": git_context or {}}
    return _write(root.resolve(), identifier, payload)
