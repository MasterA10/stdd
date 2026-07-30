from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from ..reporting.models import CommandResult
from .store import LearnStore


def history(root: Path, *, session_id: str | None = None, local_date: str | None = None,
            branch: str | None = None, worktree: str | None = None) -> CommandResult:
    store = LearnStore(root)
    result = CommandResult("framework learn", metadata={"enabled": store.enabled()})
    if not store.enabled(): result.status = "disabled"; return result
    sessions = store.sessions()
    if local_date is None and session_id is None and branch is None and worktree is None:
        local_date = date.today().isoformat()
    rows = [x for x in sessions if (not session_id or x.get("session_id") == session_id)
            and (not local_date or x.get("local_date") == local_date)
            and (not branch or x.get("branch") == branch)
            and (not worktree or x.get("worktree") == worktree)]
    result.metadata["sessions"] = rows
    result.metadata["events"] = [e for e in store.events() if not session_id or e.get("session_id") == session_id]
    return result
