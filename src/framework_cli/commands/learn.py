from __future__ import annotations

from pathlib import Path
from typing import Any

from ..learn.handoff import export_package, import_package
from ..learn.cli_adapters import send_package
from ..learn.host_hooks import dispatch_event, install as install_hooks
from ..learn.lessons import review as review_lesson
from ..learn.lifecycle import record, resume, start
from ..learn.query import history
from ..learn.rework import rework
from ..learn.summarize import summary


def run_learn(root: Path, args: Any):
    command = getattr(args, "learn_command", None)
    if command == "quiz": return _run_quiz(root, args)
    if command == "hooks": return _run_hooks(root, args)
    if command == "handoff": return _run_handoff(root, args)
    return _run_session_command(root, args, command)


def _run_quiz(root: Path, args: Any):
    from .quiz import run as run_quiz_command
    args.quiz_command = getattr(args, "learn_quiz_command", None)
    if args.quiz_command == "generate": args.agent = args.learn_provider; args.scope = args.learn_scope
    if args.quiz_command == "run": args.category = args.learn_category; args.count = args.learn_count; args.answers = args.learn_answers
    if args.quiz_command == "export": args.quiz_format = args.learn_quiz_format
    return run_quiz_command(root, args)


def _run_session_command(root: Path, args: Any, command: str | None):
    facts = {"observations": getattr(args, "observations", []) or [], "inferences": getattr(args, "inferences", []) or [],
             "files": getattr(args, "files", []) or [], "symbols": getattr(args, "symbols", []) or [],
             "tasks": getattr(args, "tasks", []) or [], "gates": getattr(args, "gates", []) or [],
             "evidence": getattr(args, "evidence", []) or []}
    if command is None: return history(root, local_date=getattr(args, "date", None))
    if command == "start": return start(root, agent=getattr(args, "agent", "framework"), host=getattr(args, "host", "framework-cli"))
    if command == "resume": return resume(root, getattr(args, "session_id", None), **facts)
    actions = {"checkpoint": lambda: record(root, "checkpoint", session_id=getattr(args, "session_id", None), **facts),
               "compact": lambda: record(root, "compacted", session_id=getattr(args, "session_id", None), **facts),
               "close": lambda: record(root, "close", session_id=getattr(args, "session_id", None), **facts),
               "summary": lambda: summary(root, getattr(args, "session_id", None)),
               "rework": lambda: rework(root, getattr(args, "session_id", None)),
               "review": lambda: review_lesson(root, args.lesson_id, args.decision, content=getattr(args, "content", None))}
    return actions.get(command, lambda: history(root))()


def _run_handoff(root: Path, args: Any):
    if args.handoff_command == "send":
        return send_package(root, args.target, Path(args.package), dry_run=args.dry_run)
    if args.handoff_command == "export":
        scope = {"sessions": getattr(args, "scope_sessions", []), "categories": getattr(args, "scope_categories", []),
                 "files": getattr(args, "scope_files", []), "symbols": getattr(args, "scope_symbols", []),
                 "statuses": getattr(args, "scope_statuses", ["approved"])}
        return export_package(root, session_id=getattr(args, "session_id", None), target=getattr(args, "target", "generic"), scope=scope)
    return import_package(root, Path(args.package))


def _run_hooks(root: Path, args: Any):
    if args.hooks_command == "install": return install_hooks(root, getattr(args, "hosts", None))
    facts = {}
    if getattr(args, "facts", None):
        import json
        try: facts = json.loads(args.facts)
        except json.JSONDecodeError:
            return dispatch_event(root, args.event, host=args.host, session_id=args.session_id,
                                  facts={"observations": ["invalid hook facts payload"]})
    return dispatch_event(root, args.event, host=args.host, session_id=args.session_id, facts=facts)
