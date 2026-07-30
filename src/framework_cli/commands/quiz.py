from __future__ import annotations

from pathlib import Path
from typing import Any

from ..learn.events import opaque
from ..learn.store import LearnStore, write_json, repository
from ..agents.instructions import discover_instruction_chain
from ..quiz.export import export_quiz
from ..quiz.generator import generate_local
from ..quiz.generation_jobs import create_job, store_questions
from ..quiz.models import KnowledgeQuestion
from ..quiz.command_generation import generate_with_command
from ..quiz.runner import run_quiz
from ..quiz.sync import sync_quiz


def _command_questions(response: dict) -> list[KnowledgeQuestion]:
    questions = []
    for raw in response.get("questions", []) if isinstance(response, dict) else []:
        try:
            data = dict(raw); data.setdefault("revision", 1); data.setdefault("status", "current")
            data.setdefault("difficulty", "medium"); data.setdefault("provenance", {"command": "local", "version": "1", "scope": {}})
            data.setdefault("fingerprint", "")
            questions.append(KnowledgeQuestion(**{key: data[key] for key in KnowledgeQuestion.__dataclass_fields__}))
        except (TypeError, KeyError):
            continue
    return questions


def generate(root: Path, *, agent: str = "local", scope: str = "project", command_callback=None):
    store = LearnStore(root)
    from ..reporting.models import CommandResult
    result = CommandResult("framework learn quiz generate", metadata={"enabled": store.enabled()})
    chain = discover_instruction_chain(store.root)
    result.metadata["instruction_chain"] = [item.path for item in chain.files]
    if not chain.valid:
        result.status, result.exit_code = "blocked", 1; result.actions.append("Instruction-chain conflict blocks quiz generation"); return result
    if not store.enabled(): result.status = "disabled"; return result
    session = store.current_session()
    session_id = session.session_id if session else "quiz-session"
    job = create_job(store, session_id, agent, {"scope": scope, "categories": []})
    if agent == "local":
        questions = generate_local(root, scope=scope)
        ids = store_questions(store, questions)
        job["status"], job["question_ids"] = "completed", ids
        write_json(store, store.base / "quiz" / "jobs" / f"{job['job_id']}.json", job); repository(store).job(job)
        result.metadata.update({"status": "completed", "job_id": job["job_id"], "count": len(ids), "agent": "local"})
        return result
    request = {"schema_version": 1, "job_id": job["job_id"], "session_id": session_id,
               "scope": {"categories": [], "files": [], "symbols": []},
               "redacted_context": {"session_id": session_id, "scope": scope, "events": store.events(session_id) if session else []},
               "question_constraints": {"options": 3, "max_options": 5, "explanation_words": 80}}
    if command_callback is not None:
        response = command_callback(request)
        status = response.get("status", "failed") if isinstance(response, dict) else "failed"
    else:
        status, response = generate_with_command(store, agent, request)
    ids = store_questions(store, _command_questions(response))
    if status in {"failed", "partial"} or not ids:
        fallback_ids = store_questions(store, generate_local(root, scope=scope, limit=5))
        ids.extend(fallback_ids)
        if fallback_ids and status == "failed": status = "partial"
    job["question_ids"] = ids
    job["status"] = status
    write_json(store, store.base / "quiz" / "jobs" / f"{job['job_id']}.json", job); repository(store).job(job)
    # Deliberately return only the acknowledgment boundary to the principal agent.
    result.metadata = {"status": status, "job_id": job["job_id"]}
    return result


def run(root: Path, args: Any):
    command = getattr(args, "quiz_command", None)
    if command == "generate": return generate(root, agent=args.agent, scope=args.scope)
    if command == "run": return run_quiz(root, category=getattr(args, "category", None), count=args.count, answers=getattr(args, "answers", None))
    if command == "sync": return sync_quiz(root)
    if command == "export": return export_quiz(root, args.quiz_format)
    return generate(root)
