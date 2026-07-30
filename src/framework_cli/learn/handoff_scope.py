from __future__ import annotations

from typing import Any


def select_scope(events: list[dict[str, Any]], scope: dict[str, Any] | None = None) -> dict[str, Any]:
    scope = scope or {"sessions": [], "categories": [], "files": [], "symbols": [], "statuses": ["approved"]}
    wanted_sessions = set(scope.get("sessions", []))
    wanted_files = set(scope.get("files", []))
    wanted_symbols = set(scope.get("symbols", []))
    selected = []
    for event in events:
        if wanted_sessions and event.get("session_id") not in wanted_sessions: continue
        if wanted_files and not wanted_files.intersection(event.get("files", [])): continue
        if wanted_symbols and not wanted_symbols.intersection(event.get("symbols", [])): continue
        selected.append(event)
    return {"events": selected, "scope": scope, "files": sorted({x for e in selected for x in e.get("files", [])}),
            "symbols": sorted({x for e in selected for x in e.get("symbols", [])})}
