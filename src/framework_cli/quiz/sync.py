from __future__ import annotations

import ast
from pathlib import Path

from ..security.fingerprint import fingerprint
from ..reporting.models import CommandResult
from .generator import source_catalog
from .repository import QuizRepository
from ..learn.store import write_json, repository


def sync_quiz(root: Path) -> CommandResult:
    from ..learn.store import LearnStore
    store = LearnStore(root); result = CommandResult("framework learn quiz sync", metadata={"enabled": store.enabled()})
    if not store.enabled(): result.status = "disabled"; return result
    sources = {x["id"]: x["fingerprint"] for x in source_catalog(root)}; changed = []
    for question in QuizRepository(store).questions():
        source_changed = any(s.get("fingerprint") != sources.get(s.get("id")) for s in question.get("sources", []))
        if source_changed and question.get("status") == "current":
            question["status"] = "needs_review"; write_json(store, store.base / "quiz" / "questions" / f"{question['question_id']}-v{question.get('revision', 1)}.json", question); repository(store).question(question); changed.append(question["question_id"])
    result.metadata["needs_review"] = changed
    return result
