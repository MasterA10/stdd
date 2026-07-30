from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import KnowledgeQuestion
from ..learn.store import write_json, read_json, repository


class QuizRepository:
    def __init__(self, store): self.store = store

    def questions(self) -> list[dict[str, Any]]:
        path = self.store.base / "quiz" / "questions"
        rows = []
        for item in sorted(path.glob("*.json")):
            try: rows.append(read_json(item))
            except Exception: continue
        return rows

    def save_attempt(self, attempt: dict[str, Any]) -> None:
        write_json(self.store, self.store.base / "quiz" / "attempts" / f"{attempt['attempt_id']}.json", attempt)
        repository(self.store).attempt(attempt)
