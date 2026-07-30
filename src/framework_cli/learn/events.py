from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any
import uuid

from ..security.fingerprint import fingerprint


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def opaque(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:16]}"


@dataclass
class Session:
    session_id: str
    status: str = "active"
    local_date: str = ""
    parent_session_id: str | None = None
    started_at: str | None = None
    ended_at: str | None = None
    agent: str = "framework"
    host: str = "framework-cli"
    branch: str | None = None
    worktree: str = "."
    commit_base: str | None = None
    coverage: dict[str, Any] = field(default_factory=lambda: {"hooks": "partial"})

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LearningEvent:
    event_id: str
    session_id: str
    type: str
    local_date: str
    observed_at: str
    agent: str
    host: str
    branch: str | None = None
    worktree: str = "."
    tasks: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    symbols: list[str] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)
    gates: list[str] = field(default_factory=list)
    observations: list[str] = field(default_factory=list)
    inferences: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    payload: dict[str, Any] = field(default_factory=dict)
    redaction: dict[str, Any] = field(default_factory=lambda: {"count": 0, "types": []})
    coverage: dict[str, Any] = field(default_factory=lambda: {"hooks": "partial"})
    fingerprint: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["schema_version"] = 1
        return data

    @classmethod
    def create(cls, session: Session, event_type: str, **facts: Any) -> "LearningEvent":
        event = cls(event_id=opaque("event"), session_id=session.session_id, type=event_type,
                    local_date=session.local_date, observed_at=now_iso(), agent=session.agent,
                    host=session.host, branch=session.branch, worktree=session.worktree,
                    coverage=dict(session.coverage), **{k: v for k, v in facts.items() if k in {
                        "tasks", "files", "symbols", "commands", "gates", "observations",
                        "inferences", "evidence", "payload"}})
        event.fingerprint = fingerprint(event.session_id, event.event_id, event.type, event.observed_at)
        return event
