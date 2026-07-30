from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class KnowledgeQuestion:
    question_id: str
    revision: int
    category: str
    prompt: str
    options: list[str]
    correct_option: str
    explanation: str
    difficulty: str = "medium"
    sources: list[dict[str, Any]] = field(default_factory=list)
    status: str = "current"
    provenance: dict[str, Any] = field(default_factory=lambda: {"provider": "local", "version": "1", "scope": {}})
    fingerprint: str = ""

    def to_dict(self, *, hide_answer: bool = False) -> dict[str, Any]:
        data = asdict(self)
        data["schema_version"] = 1
        if hide_answer: data.pop("correct_option", None)
        return data


@dataclass
class QuizAttempt:
    attempt_id: str
    session_id: str
    question_revision: str
    answer: str
    correct: bool
    confidence: float | None = None
    submitted_at: str = ""

    def to_dict(self) -> dict[str, Any]: return asdict(self)
