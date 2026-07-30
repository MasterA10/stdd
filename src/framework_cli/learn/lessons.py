from __future__ import annotations

from pathlib import Path
from typing import Any

from ..reporting.models import CommandResult
from .events import opaque, now_iso
from .redaction import redact_record
from .store import LearnStore, write_json, read_json, repository


def propose(root: Path, title: str, content: list[str] | str, source_events: list[str], *, scope: dict[str, Any] | None = None) -> dict[str, Any]:
    store = LearnStore(root)
    lesson = {"lesson_id": opaque("lesson"), "revision": 1, "status": "proposed", "title": title,
              "content": content if isinstance(content, list) else [content], "source_events": source_events,
              "confidence": 0.5, "scope": scope or {}, "review": {"decision": None}, "created_at": now_iso()}
    clean, _ = redact_record(lesson)
    path = store.base / "lessons" / f"{clean['lesson_id']}.json"
    write_json(store, path, clean)
    repository(store).lesson(clean)
    return clean


def review(root: Path, lesson_id: str, decision: str, *, content: list[str] | None = None) -> CommandResult:
    store = LearnStore(root); result = CommandResult("framework learn review", metadata={"enabled": store.enabled()})
    if not store.enabled(): result.status = "disabled"; return result
    if decision not in {"approved", "rejected", "edited"}:
        result.status, result.exit_code = "error", 2; result.actions.append("Decision must be approved, rejected or edited"); return result
    path = store.base / "lessons" / f"{lesson_id}.json"
    if not path.exists():
        result.status, result.exit_code = "error", 2; result.actions.append("Lesson not found"); return result
    lesson = read_json(path); lesson["revision"] = int(lesson.get("revision", 1)) + 1
    lesson["status"] = "approved" if decision in {"approved", "edited"} else "rejected"
    if content is not None: lesson["content"] = content
    lesson["review"] = {"decision": decision, "reviewed_at": now_iso()}
    write_json(store, path, lesson); repository(store).lesson(lesson)
    result.metadata["lesson"] = lesson
    result.actions.append("Promotion to permanent instructions requires explicit human action")
    return result
