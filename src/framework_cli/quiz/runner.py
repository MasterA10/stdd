from __future__ import annotations

from pathlib import Path
from typing import Any

from ..learn.events import opaque, now_iso
from ..reporting.models import CommandResult
from .repository import QuizRepository


def run_quiz(root: Path, *, category: str | None = None, count: int = 10, answers: list[str] | None = None,
             session_id: str | None = None) -> CommandResult:
    from ..learn.store import LearnStore
    store = LearnStore(root); result = CommandResult("framework quiz run", metadata={"enabled": store.enabled()})
    if not store.enabled(): result.status = "disabled"; return result
    questions = [q for q in QuizRepository(store).questions() if q.get("status") == "current" and (not category or q.get("category") == category)][:count]
    if not questions:
        result.status, result.exit_code = "warned", 0; result.actions.append("No current questions available; run quiz generate first"); result.metadata["questions"] = []; return result
    responses = answers or []
    visible = [{k: v for k, v in q.items() if k != "correct_option"} for q in questions]
    attempts, score = [], 0
    if answers is not None:
        session = store.get_session(session_id) if session_id else store.current_session()
        sid = session.session_id if session else "quiz-session"
        for index, question in enumerate(questions):
            answer = responses[index] if index < len(responses) else ""
            correct = answer == question.get("correct_option")
            score += int(correct)
            attempt = {"attempt_id": opaque("attempt"), "session_id": sid, "question_revision": f"{question['question_id']}:{question.get('revision', 1)}", "answer": answer, "correct": correct, "submitted_at": now_iso()}
            QuizRepository(store).save_attempt(attempt); attempts.append({"question_id": question["question_id"], "correct": correct})
    result.metadata.update({"questions": visible, "attempts": attempts, "score": score, "total": len(questions)})
    return result
