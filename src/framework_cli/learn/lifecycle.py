from __future__ import annotations

from pathlib import Path
from typing import Any

from ..agents.instructions import discover_instruction_chain
from ..reporting.models import CommandResult
from .events import LearningEvent, Session
from .store import LearnStore


def _result(command: str, store: LearnStore, *, session: Session | None = None) -> CommandResult:
    result = CommandResult(command, project={"root": str(store.root)}, metadata={"enabled": store.enabled()})
    chain = discover_instruction_chain(store.root)
    result.metadata["instruction_chain"] = [item.path for item in chain.files]
    if not chain.valid:
        result.status, result.exit_code = "blocked", 1
        result.actions.append("Instruction-chain conflict blocks learn operation")
        return result
    if session:
        result.metadata["session_id"] = session.session_id
    if not store.enabled():
        result.status, result.exit_code = "disabled", 0
    return result


def start(root: Path, *, agent: str = "framework", host: str = "framework-cli",
          parent_session_id: str | None = None) -> CommandResult:
    store = LearnStore(root); result = _result("framework learn start", store)
    if result.status in {"disabled", "blocked"}: return result
    session = store.start_session(agent=agent, host=host, parent_session_id=parent_session_id)
    result.metadata["session_id"] = session.session_id
    result.metadata["session"] = session.to_dict()
    result.actions.append("Review redacted files; no Git commit was created")
    return result


def _active_or_incomplete(store: LearnStore, session_id: str | None) -> Session | None:
    return store.get_session(session_id) if session_id else store.current_session()


def record(root: Path, event_type: str, *, session_id: str | None = None, **facts: Any) -> CommandResult:
    store = LearnStore(root); result = _result(f"framework learn {event_type}", store)
    session = _active_or_incomplete(store, session_id)
    if result.status == "disabled": return result
    if session is None:
        result.status, result.exit_code = "error", 2
        result.actions.append("Start or resume a session first")
        return result
    allowed = {"checkpoint": "checkpointed", "compacted": "compacted", "resume": "resumed", "close": "closed"}
    target = allowed.get(event_type, event_type)
    event = LearningEvent.create(session, event_type, **facts)
    from .rework import detect_rework
    signals = detect_rework([*store.events(session.session_id), event.to_dict()])
    event.payload["rework_signals"] = signals
    store.append_event(event)
    store.update_session(session, status=target, ended=event_type == "close")
    result.metadata["session"] = session.to_dict()
    result.metadata["rework_signals"] = signals
    result.actions.append("Review redacted files; no Git commit was created")
    return result


def resume(root: Path, session_id: str | None = None, **facts: Any) -> CommandResult:
    return record(root, "resume", session_id=session_id, **facts)


def session_boundary(root: Path, *, agent: str = "framework", host: str = "framework-cli",
                     **facts: Any) -> CommandResult:
    store = LearnStore(root)
    previous = store.current_session()
    closed = record(root, "close", session_id=previous.session_id, **facts) if previous else None
    result = start(root, agent=agent, host=host, parent_session_id=previous.session_id if previous else None)
    if closed and result.status == "passed":
        result.metadata["closed_session_id"] = previous.session_id
        result.metadata["rework_signals"] = closed.metadata.get("rework_signals", [])
    result.command = "framework learn hooks session-start"
    return result


def incomplete(root: Path, session_id: str | None = None) -> CommandResult:
    store = LearnStore(root); result = _result("framework learn incomplete", store)
    session = _active_or_incomplete(store, session_id)
    if result.status == "disabled": return result
    if session:
        store.append_event(LearningEvent.create(session, "tombstone", payload={"reason": "incomplete session detected"}))
        store.update_session(session, status="incomplete")
        result.metadata["session"] = session.to_dict()
    else:
        result.status = "warned"
        result.actions.append("No active session found")
    return result


def check_instruction_chain(root: Path, target: Path | None = None) -> tuple[bool, list[str]]:
    chain = discover_instruction_chain(root, target)
    return chain.valid, chain.conflicts
