from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from ..reporting.models import CommandResult
from .store import LearnStore


def detect_rework(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    symbols = Counter(symbol for event in events for symbol in event.get("symbols", []))
    files = Counter(file for event in events for file in event.get("files", []))
    signals = []
    for value, count in (*symbols.items(), *files.items()):
        if count >= 2:
            signals.append({"kind": "repeated-evidence", "target": value, "count": count,
                            "confidence": min(1.0, 0.5 + count / 10)})
    for event in events:
        observations = " ".join(str(x).lower() for x in event.get("observations", []))
        if any(term in observations for term in ("retry", "revert", "reapply", "failed", "retrabalho")):
            signals.append({"kind": "gate-or-retry", "event_id": event.get("event_id"), "confidence": 0.7})
    return signals


def rework(root: Path, session_id: str | None = None) -> CommandResult:
    store = LearnStore(root); result = CommandResult("framework learn rework", metadata={"enabled": store.enabled()})
    if not store.enabled(): result.status = "disabled"; return result
    session = store.get_session(session_id) if session_id else store.current_session()
    if not session:
        result.status, result.exit_code = "error", 2; result.actions.append("No session found"); return result
    result.metadata["signals"] = detect_rework(store.events(session.session_id))
    result.metadata["session_id"] = session.session_id
    return result
