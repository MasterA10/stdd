from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from ..reporting.models import CommandResult
from .store import LearnStore


def build_summary(events: list[dict[str, Any]], *, max_words: int = 80) -> dict[str, Any]:
    observations, inferences, evidence = [], [], []
    files, symbols, tasks = set(), set(), set()
    types = Counter()
    for event in events:
        types[event.get("type", "unknown")] += 1
        observations.extend(event.get("observations", []))
        inferences.extend(event.get("inferences", []))
        evidence.extend(event.get("evidence", []))
        files.update(event.get("files", [])); symbols.update(event.get("symbols", [])); tasks.update(event.get("tasks", []))
    def short(items: list[str]) -> list[str]:
        return [str(x)[:240] for x in items[:3]]
    return {"events": sum(types.values()), "types": dict(types), "observations": short(observations),
            "inferences": short(inferences), "evidence": short(evidence),
            "files": sorted(files), "symbols": sorted(symbols), "tasks": sorted(tasks),
            "lesson": short(observations + inferences)[:3], "max_words": max_words}


def summary(root: Path, session_id: str | None = None) -> CommandResult:
    store = LearnStore(root); result = CommandResult("framework learn summary", metadata={"enabled": store.enabled()})
    if not store.enabled(): result.status = "disabled"; return result
    session = store.get_session(session_id) if session_id else store.current_session()
    if not session:
        result.status, result.exit_code = "error", 2; result.actions.append("No session found"); return result
    result.metadata["session_id"] = session.session_id
    result.metadata["summary"] = build_summary(store.events(session.session_id))
    return result
