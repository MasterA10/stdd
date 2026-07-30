from __future__ import annotations

from typing import Any


def select_scope(events: list[dict[str, Any]], scope: dict[str, Any] | None = None) -> dict[str, Any]:
    scope = scope or {"sessions": [], "categories": [], "files": [], "symbols": [], "statuses": ["approved"]}
    wanted_sessions = set(scope.get("sessions", []))
    wanted_files = set(scope.get("files", []))
    wanted_symbols = set(scope.get("symbols", [])); wanted_categories = set(scope.get("categories", []))
    selected = []
    for event in events:
        if wanted_sessions and event.get("session_id") not in wanted_sessions: continue
        if wanted_files and not wanted_files.intersection(event.get("files", [])): continue
        if wanted_symbols and not wanted_symbols.intersection(event.get("symbols", [])): continue
        event_categories = set(event.get("categories", [])) | set((event.get("payload") or {}).get("categories", []))
        if wanted_categories and not wanted_categories.intersection(event_categories): continue
        selected.append(event)
    return {"events": selected, "scope": scope, "files": sorted({x for e in selected for x in e.get("files", [])}),
            "symbols": sorted({x for e in selected for x in e.get("symbols", [])}),
            "categories": sorted({x for e in selected for x in e.get("categories", [])})}


def select_lessons(lessons: list[dict[str, Any]], scope: dict[str, Any]) -> list[dict[str, Any]]:
    statuses = set(scope.get("statuses", ["approved"])); categories = set(scope.get("categories", []))
    files = set(scope.get("files", [])); symbols = set(scope.get("symbols", [])); selected = []
    for lesson in lessons:
        if lesson.get("status") not in statuses: continue
        lesson_scope = lesson.get("scope", {}) or {}
        if categories and lesson_scope.get("category") not in categories: continue
        if files and not files.intersection(lesson_scope.get("files", [])): continue
        if symbols and not symbols.intersection(lesson_scope.get("symbols", [])): continue
        selected.append(lesson)
    return selected
