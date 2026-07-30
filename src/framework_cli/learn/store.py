from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from ..config.loader import load_config
from ..git.repository import GitRepository
from ..index.db import IndexDB
from ..index.repository import Repository
from ..security.fingerprint import fingerprint
from .events import LearningEvent, Session, now_iso, opaque
from .redaction import redact_record


class LearnStore:
    """Project-local append-only store. It never stages or commits files."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.base = self.root / ".framework" / "learn"
        self.base.joinpath("events").mkdir(parents=True, exist_ok=True)
        for name in ("lessons", "handoffs", "quiz"):
            (self.base / name).mkdir(parents=True, exist_ok=True)
        self.git = GitRepository(self.root)
        self._repo: Repository | None = None

    def enabled(self) -> bool:
        try:
            return bool(load_config(self.root).learn.get("enabled", False))
        except (FileNotFoundError, ValueError):
            return False

    def save_session(self, session: Session) -> Session:
        clean = append_jsonl(self.base / "sessions.jsonl", session.to_dict())
        repository(self).learn_session(clean)
        return session

    def append_event(self, event: LearningEvent | dict[str, Any]) -> dict[str, Any]:
        record = event.to_dict() if isinstance(event, LearningEvent) else event
        record.setdefault("fingerprint", fingerprint(str(record.get("session_id", "")), str(record.get("event_id", "")), str(record.get("type", "")), str(record.get("observed_at", ""))))
        clean = append_jsonl(self.base / "events" / "events.jsonl", record)
        repository(self).learn_event(clean)
        return clean

    def sessions(self) -> list[dict[str, Any]]:
        return read_jsonl(self.base / "sessions.jsonl")

    def events(self, session_id: str | None = None) -> list[dict[str, Any]]:
        rows = read_jsonl(self.base / "events" / "events.jsonl")
        return [x for x in rows if session_id is None or x.get("session_id") == session_id]

    def current_session(self) -> Session | None:
        rows = self.sessions()
        for row in reversed(rows):
            if row.get("status") in {"active", "checkpointed", "compacted", "resumed"}:
                return Session(**{k: row[k] for k in Session.__dataclass_fields__ if k in row})
        return None

    def get_session(self, session_id: str) -> Session | None:
        for row in reversed(self.sessions()):
            if row.get("session_id") == session_id:
                return Session(**{k: row[k] for k in Session.__dataclass_fields__ if k in row})
        return None

    def start_session(self, *, parent_session_id: str | None = None, agent: str = "framework",
                      host: str = "framework-cli") -> Session:
        branch = self.git.branch
        session = Session(session_id=opaque("session"), local_date=date.today().isoformat(),
                          started_at=now_iso(), parent_session_id=parent_session_id,
                          agent=agent, host=host, branch=branch,
                          coverage={"hooks": "partial", "git": "complete" if self.git.available else "missing"})
        self.save_session(session)
        self.append_event(LearningEvent.create(session, "start"))
        return session

    def update_session(self, session: Session, *, status: str | None = None, ended: bool = False) -> Session:
        if status: session.status = status
        if ended: session.ended_at = now_iso()
        self.save_session(session)
        return session

    def tombstone(self, path: Path, *, reason: str = "sensitive data found after persistence") -> dict[str, Any]:
        """Remove a local record and retain only a redacted audit marker."""
        relative = str(path.resolve().relative_to(self.root.resolve())) if path.exists() else str(path)
        if path.exists(): path.unlink()
        session = self.current_session()
        marker = {"schema_version": 1, "event_id": opaque("tombstone"), "session_id": session.session_id if session else "unknown",
                  "type": "tombstone", "local_date": date.today().isoformat(), "observed_at": now_iso(),
                  "agent": "framework", "host": "framework-cli", "payload": {"path": relative, "reason": reason},
                  "redaction": {"count": 0, "types": []}, "coverage": {"hooks": "partial"}}
        return self.append_event(marker)

    def close(self) -> None:
        if self._repo and self._repo.db: self._repo.db.close()


def repository(store: LearnStore) -> Repository:
    if store._repo is None:
        store._repo = Repository(IndexDB(store.root / ".framework" / "index.db"))
    return store._repo


def append_jsonl(path: Path, record: dict[str, Any]) -> dict[str, Any]:
    clean, _ = redact_record(record)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(clean, ensure_ascii=False, sort_keys=True) + "\n")
    return clean


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists(): return []
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try: rows.append(json.loads(line))
        except json.JSONDecodeError: continue
    return rows


def write_json(store: LearnStore, path: Path, data: dict[str, Any]) -> Path:
    clean, _ = redact_record(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(clean, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)
    return path


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
