from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from ..reporting.models import CommandResult
from ..agents.instructions import discover_instruction_chain
from .lifecycle import record, resume, session_boundary, start
from .store import LearnStore

HOSTS = ("codex", "claude", "cloud", "antigravity", "generic")
EVENTS = {"start": "start", "session-start": "start", "checkpoint": "checkpoint",
          "compact": "compacted", "compacted": "compacted", "resume": "resume",
          "session-end": "close", "end": "close", "close": "close", "new-session": "boundary"}


def _script(host: str, event: str) -> str:
    return f"#!/bin/sh\n# framework-managed-session-hook host={host} event={event}\nexec framework learn hooks event --host {host} --event {event} \"${{FRAMEWORK_PROJECT_ROOT:-$PWD}}\"\n"


def install(root: Path, hosts: list[str] | None = None) -> CommandResult:
    root = root.resolve(); selected = hosts or list(HOSTS)
    result = CommandResult("framework learn hooks install", project={"root": str(root)})
    chain = discover_instruction_chain(root)
    result.metadata["instruction_chain"] = [item.path for item in chain.files]
    if not chain.valid:
        result.status, result.exit_code = "blocked", 1; result.actions.append("Instruction-chain conflict blocks hook installation"); return result
    if not LearnStore(root).enabled():
        result.status = "disabled"; return result
    invalid = sorted(set(selected) - set(HOSTS))
    if invalid:
        result.status, result.exit_code = "error", 2; result.actions.append("Unsupported host: " + ", ".join(invalid)); return result
    base = root / ".framework" / "hooks"; created = []
    for host in selected:
        for event in ("start", "checkpoint", "compact", "resume", "session-end", "new-session"):
            path = base / host / f"{event}.sh"; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(_script(host, event), encoding="utf-8"); path.chmod(0o755); created.append(str(path.relative_to(root)))
    manifest = {"schema_version": 1, "hosts": selected, "events": sorted(EVENTS), "scripts": created}
    (base / "manifest.json").parent.mkdir(parents=True, exist_ok=True)
    (base / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    result.metadata.update({"hosts": selected, "scripts": created, "manifest": str((base / "manifest.json").relative_to(root))})
    result.actions.append("Configure each host to invoke the generated scripts at its lifecycle events")
    return result


def dispatch_event(root: Path, event: str, *, host: str = "generic", session_id: str | None = None,
                   facts: dict[str, Any] | None = None) -> CommandResult:
    if host not in HOSTS: return CommandResult("framework learn hooks event", status="error", exit_code=2, actions=["Unsupported host"])
    facts = facts or {}
    normalized = EVENTS.get(event)
    if normalized == "boundary": return session_boundary(root, agent=host, host=host, **facts)
    if normalized == "start":
        if LearnStore(root).current_session(): return session_boundary(root, agent=host, host=host)
        return start(root, agent=host, host=host)
    if normalized == "resume": return resume(root, session_id, **facts)
    if normalized in {"checkpoint", "compacted", "close"}: return record(root, normalized, session_id=session_id, **facts)
    return CommandResult("framework learn hooks event", status="error", exit_code=2, actions=["Unsupported session event"])
