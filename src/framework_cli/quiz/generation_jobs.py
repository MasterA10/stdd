from __future__ import annotations

from pathlib import Path
from typing import Any

from ..learn.events import opaque, now_iso
from ..learn.redaction import redact_record
from ..reporting.models import CommandResult
from ..learn.store import write_json, repository
from .models import KnowledgeQuestion
from .validation import validate_question


def create_job(store, session_id: str, provider: str, scope: dict[str, Any]) -> dict[str, Any]:
    job = {"job_id": opaque("job"), "session_id": session_id, "provider": provider, "status": "created",
           "scope": scope, "question_ids": [], "created_at": now_iso(), "error": None}
    clean, _ = redact_record(job); write_json(store, store.base / "quiz" / "jobs" / f"{job['job_id']}.json", clean); repository(store).job(clean)
    return clean


def store_questions(store, questions: list[KnowledgeQuestion]) -> list[str]:
    ids = []
    for question in questions:
        errors = validate_question(question.to_dict())
        if errors: continue
        clean = question.to_dict(); write_json(store, store.base / "quiz" / "questions" / f"{question.question_id}-v{question.revision}.json", clean); repository(store).question(clean); ids.append(question.question_id)
    return ids
